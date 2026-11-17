"""What would a nearest-EDGE fallback attach the dropped parks to, and what would it cost?

`g1_own_graph_layer.py` snaps a destination to its nearest graph NODE and drops it when that node
is farther than `POI_SNAP_MAX_M` (300 m). Pass 57 found that bound is the wrong instrument: park
record #456 is **356.44 m from the nearest node and 0.17 m from the nearest edge**, so it is
dropped while sitting essentially on a road. Both reviewers reached the same narrow repair --
attach to the nearest EDGE, keeping the existing 300 m bound, and only where the node rule already
failed -- and both measured 6 recoveries with 0 retained records lost.

This script establishes, before any of that is implemented, the four things the implementation
needs and nobody had measured per-record:

1. which park records the node rule drops, and by how far;
2. what their nearest edge is, how far it is, and **where along it** they project;
3. whether that edge is **access-restricted**, because `speeds.py` charges the restricted penalty
   PER EDGE, so splitting one to insert a node DOUBLES its penalty for every journey using it
   (pass 56's finding, and the reason "subdividing changes nothing" was wrong);
4. whether the projection lands close enough to an existing endpoint that no split is needed at
   all, which is the cheapest outcome and changes no edge's cost.

It changes nothing. Run from `v2/`:
    python scripts/measure_park_edge_fallback.py
    python scripts/measure_park_edge_fallback.py --category park --mode walk --cap 300
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import osmnx as ox
import shapely

V2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V2 / "spikes"))
sys.path.insert(0, str(V2))

from _common import ACCEPTED_PLACES, GRID  # noqa: E402
from g1_own_graph_layer import POI_SNAP_MAX_M, load_graph  # noqa: E402
from locfinder.places.categories import select_target  # noqa: E402
from locfinder.traveltime.components import largest_component  # noqa: E402
from locfinder.traveltime.csr import graph_to_cost_time_csr  # noqa: E402
from locfinder.traveltime.snap import EdgeIndex  # noqa: E402
from locfinder.traveltime.speeds import add_travel_times, symmetrise  # noqa: E402

#: Below this, the projection is "at" the endpoint for practical purposes and the fallback can use
#: that node directly rather than splitting the edge. One metre is far inside the 100 m cell.
AT_NODE_M = 1.0


def prepare(mode: str):
    """The same graph the layer builder routes on, prepared the same way."""
    timings: dict = {}
    G = load_graph(timings)
    G = ox.project_graph(G, to_crs=GRID.crs)
    G = add_travel_times(G, mode=mode)
    if mode == "walk":
        G = symmetrise(G)
    G.remove_nodes_from([n for n, d in G.degree() if d == 0])
    G, comp = largest_component(G)
    return G, comp


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--category", action="append", default=None,
                    help="repeatable; default: every category the wedge defines")
    ap.add_argument("--mode", default="walk", choices=["walk", "bike", "drive"])
    ap.add_argument("--cap", type=float, default=POI_SNAP_MAX_M,
                    help="the edge-distance bound for the fallback (default: the node bound)")
    args = ap.parse_args()

    categories = args.category or ["park", "grocery", "school", "coffee"]

    t0 = time.perf_counter()
    G, comp = prepare(args.mode)
    _cost_csr, _time_csr, index = graph_to_cost_time_csr(G)
    eidx = EdgeIndex.from_graph(G, index)
    print(f"graph: {G.number_of_nodes():,} nodes, {G.number_of_edges():,} edges "
          f"({comp.summary}); prepared in {time.perf_counter() - t0:.1f} s")

    places = gpd.read_parquet(ACCEPTED_PLACES).to_crs(GRID.crs)
    for category in categories:
        report_category(G, eidx, index, places, category, args)


def report_category(G, eidx, index, places, category, args) -> None:
    """Everything below was one straight line of `main` until the sweep; the body is unchanged
    apart from taking `category` as a parameter."""
    sel = select_target(places, category)
    geom_types = sel.geometry.geom_type.value_counts().to_dict()
    cent = sel.geometry.centroid
    moved = float((cent.distance(sel.geometry)).max())
    print(f"{category}: {len(sel):,} accepted records, geometry {geom_types}, "
          f"max centroid displacement {moved:.3f} m")

    nodes, ndist = ox.nearest_nodes(G, cent.x.to_numpy(), cent.y.to_numpy(), return_dist=True)
    ndist = np.asarray(ndist, dtype=float)
    kept = ndist <= POI_SNAP_MAX_M
    print(f"node rule at {POI_SNAP_MAX_M:.0f} m: {int(kept.sum()):,} kept, "
          f"{int((~kept).sum())} dropped -> {len({index[n] for n, k in zip(nodes, kept) if k}):,} "
          f"destination nodes")

    pts = shapely.points(cent.x.to_numpy(), cent.y.to_numpy())
    near_e = eidx.tree.nearest(pts)
    edist = shapely.distance(pts, eidx.geoms[near_e])

    print(f"\n--- the {int((~kept).sum())} records the node rule drops ---")
    print(f"  {'#':>4} {'node m':>9} {'edge m':>9} {'frac':>6} {'start m':>9} {'end m':>9} "
          f"{'restricted':>11}  name")
    recoverable = 0
    at_node = 0
    restricted = 0
    for i in np.flatnonzero(~kept):
        g = eidx.geoms[near_e[i]]
        f = float(g.project(pts[i], normalized=True))
        d_start = float(shapely.Point(g.coords[0]).distance(pts[i]))
        d_end = float(shapely.Point(g.coords[-1]).distance(pts[i]))
        flag = False
        if eidx.fwd_flag is not None:
            flag = bool(eidx.fwd_flag[near_e[i]] or eidx.rev_flag[near_e[i]])
        name = str(sel.iloc[i].get("names", {}) or "")[:44]
        ok = edist[i] <= args.cap
        recoverable += ok
        if ok and min(d_start, d_end) <= AT_NODE_M:
            at_node += 1
        if ok and flag:
            restricted += 1
        print(f"  {int(sel.index[i]):>4} {ndist[i]:>9.2f} {edist[i]:>9.2f} {f:>6.3f} "
              f"{d_start:>9.2f} {d_end:>9.2f} {str(flag):>11}  {name}")

    print(f"\n  a {args.cap:.0f} m EDGE bound recovers {recoverable} of {int((~kept).sum())}")
    print(f"  of those, {at_node} project within {AT_NODE_M:.0f} m of an existing endpoint "
          f"(no split needed)")
    print(f"  of those, {restricted} sit on an ACCESS-RESTRICTED edge -- splitting one doubles "
          f"its per-edge penalty")

    # The claim that matters for churn: the fallback must not touch a record the node rule keeps.
    moved_kept = int(((edist < ndist - 1e-9) & kept).sum())
    print(f"\n  records the node rule KEEPS whose nearest edge is nearer than their node: "
          f"{moved_kept:,} of {int(kept.sum()):,}")
    print("  (the fallback fires only where the node rule already failed, so these are "
          "untouched by construction -- reported so the claim is checkable, not asserted)")


if __name__ == "__main__":
    main()
