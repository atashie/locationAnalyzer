"""How much of an audited journey depends on OSM `track` and `path` ways?

The owner walked a sheet row and found it far slower than predicted: band15min_pass-03 is 810.8 s
(13.5 min) in the layer and about 25 minutes on the ground, 1.3 miles. Our walking speed is
1.40 m/s and the route is computed at exactly that, so the speed is not the error -- the route is
roughly half the real distance.

`explain_journey.py` showed why: the cell's nearest network edge is an unnamed `track` 35.5 m away,
and the first 298 m of the route is unnamed `track` and `path` before it reaches a named street.
Every one of the 14 edges within 120 m of the cell centre is a track, path, footway or service way.

This script quantifies the dependence rather than arguing about it:

* how far the cell is from the nearest edge of each OSM highway class, so "is there even a road
  here" has a number;
* the journey recomputed with `track` removed, and with `track` + `path` removed, which is the
  counterfactual the owner's walk is evidence about;
* the same two counterfactuals across every row of the sheet, because one row is an anecdote.

Read-only. Three graph preparations, about 4 minutes.
"""
import argparse
import csv
import math
import pathlib
import sys
import time

import geopandas as gpd
import numpy as np
import osmnx as ox
import shapely

V2 = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V2))
sys.path.insert(1, str(V2 / "spikes"))
from _common import ACCEPTED_PLACES, GRID, load_roads_graph  # noqa: E402

from locfinder.places.categories import select_overture  # noqa: E402
from locfinder.traveltime.arrival import arrival_seconds, arrival_with_selected_destination  # noqa: E402
from locfinder.traveltime.components import largest_component  # noqa: E402
from locfinder.traveltime.csr import graph_to_cost_time_csr  # noqa: E402
from locfinder.traveltime.snap import EdgeIndex, cell_seconds_from_arrival  # noqa: E402
from locfinder.traveltime.speeds import add_travel_times, symmetrise  # noqa: E402

POI_SNAP_MAX_M = 300.0
MAX_ACCESS_M = 200.0
HORIZON_S = 120.0 * 60.0
MODE = "walk"
CATEGORY = "grocery"

# What a pedestrian can be reasonably sure exists and is usable. A `track` is an unpaved
# forestry/agricultural way; a `path` may be an informal trail. Neither is a promise of a usable
# route, and both are what this journey depends on.
SOFT = {"track", "path"}


def classes(data) -> set:
    hw = data.get("highway")
    if isinstance(hw, (list, tuple)):
        return {str(x) for x in hw}
    return {str(hw)} if hw else set()


def prepare(drop: set):
    """The published preparation, optionally without some highway classes."""
    G = load_roads_graph()
    G = ox.project_graph(G, to_crs=GRID.crs)
    if drop:
        doomed = [(u, v, k) for u, v, k, d in G.edges(keys=True, data=True)
                  if classes(d) & drop]
        G.remove_edges_from(doomed)
    G = add_travel_times(G, mode=MODE)
    if MODE == "walk":
        G = symmetrise(G)
    G.remove_nodes_from([n for n, d in G.degree() if d == 0])
    G, _c = largest_component(G)
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
    places = gpd.read_parquet(ACCEPTED_PLACES).to_crs(GRID.crs)
    sel = select_overture(places, CATEGORY)
    cent = sel.geometry.centroid
    nodes, dists = ox.nearest_nodes(G, cent.x.to_numpy(), cent.y.to_numpy(), return_dist=True)
    keep = np.asarray(dists) <= POI_SNAP_MAX_M
    dest_idx = sorted({index[n] for n, k in zip(nodes, keep) if k})
    T, _sel_nodes = arrival_with_selected_destination(cost_csr, time_csr, dest_idx=dest_idx,
                                                     cutoff_s=HORIZON_S)
    node_cost = np.asarray(arrival_seconds(cost_csr, dest_idx=dest_idx))
    # `index` comes back so the geometry->node mapping is explicit rather than relying on
    # list(G.nodes()) happening to match the order csr.py used.
    return G, EdgeIndex.from_graph(G, index), T, node_cost, len(dest_idx), index


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet", type=pathlib.Path)
    ap.add_argument("--focus", default="band15min_pass-03")
    args = ap.parse_args()

    rows = list(csv.DictReader(args.sheet.open(encoding="utf-8-sig")))
    centre_x, centre_y = GRID.cell_centers_xy()
    rc = [(int(r["row"]), int(r["col"])) for r in rows]
    xs = np.array([float(centre_x[r, c]) for r, c in rc])
    ys = np.array([float(centre_y[r, c]) for r, c in rc])

    results = {}
    for label, drop in (("as published", set()), ("no track", {"track"}),
                        ("no track or path", SOFT)):
        t = time.perf_counter()
        G, eidx, T, node_cost, ndest, index = prepare(drop)
        secs = cell_seconds_from_arrival(eidx, T, xs, ys, mode=MODE,
                                         max_access_m=MAX_ACCESS_M, node_cost=node_cost,
                                         cutoff_s=HORIZON_S)
        results[label] = np.asarray(secs, dtype=np.float64)
        print(f"{label:<18} prepared in {time.perf_counter() - t:5.1f}s, "
              f"{G.number_of_edges():>8,} edges, {ndest} destination nodes", flush=True)

        if not drop:
            # how far is this cell from each highway class?
            focus = next(i for i, r in enumerate(rows) if r["journey_id"] == args.focus)
            pt = shapely.points([xs[focus]], [ys[focus]])[0]
            print(f"\n--- {args.focus}: distance from the cell centre to the nearest edge of "
                  f"each class ---")
            best: dict[str, float] = {}
            node_of = {i: n for n, i in index.items()}
            for gi in np.atleast_1d(eidx.tree.query(pt.buffer(600.0))):
                d = float(shapely.distance(pt, eidx.geoms[gi]))
                u = node_of[int(eidx.start_idx[gi])]
                v = node_of[int(eidx.end_idx[gi])]
                for cls in _classes_for(G, u, v):
                    if cls not in best or d < best[cls]:
                        best[cls] = d
            for cls, d in sorted(best.items(), key=lambda kv: kv[1]):
                flag = "  <- soft" if cls in SOFT else ""
                print(f"  {d:8.1f} m  {cls}{flag}")
            print()

    print(f"\n{'journey':<22} {'published':>10} {'no track':>10} {'no trk/path':>12}  change")
    print("-" * 74)
    for i, r in enumerate(rows):
        pub, nt, ntp = (results[k][i] for k in ("as published", "no track", "no track or path"))
        def fmt(v):
            return "UNKNOWN" if not math.isfinite(v) else f"{v:,.0f}"
        worst = max((v for v in (nt, ntp) if math.isfinite(v)), default=math.inf)
        delta = "" if not math.isfinite(pub) else (
            "same" if math.isfinite(ntp) and abs(ntp - pub) < 0.5
            else f"+{ntp - pub:,.0f} s" if math.isfinite(ntp) else "-> UNKNOWN")
        star = "  <<<" if r["journey_id"] == args.focus else ""
        print(f"{r['journey_id']:<22} {fmt(pub):>10} {fmt(nt):>10} {fmt(ntp):>12}  {delta}{star}")

    pub = results["as published"]
    ntp = results["no track or path"]
    moved = sum(1 for a, b in zip(pub, ntp)
                if math.isfinite(a) and (not math.isfinite(b) or abs(b - a) >= 0.5))
    print(f"\n{moved} of {len(rows)} journeys change when track and path are removed")
    for thr in (600.0, 900.0):
        was = sum(1 for v in pub if math.isfinite(v) and v <= thr)
        now = sum(1 for v in ntp if math.isfinite(v) and v <= thr)
        print(f"  passing {thr / 60:.0f} min: {was} as published, {now} without track/path")
    return 0


def _classes_for(G, u, v) -> set:
    """Highway classes on the physical edge between two OSM node ids, either direction."""
    out = set()
    for a, b in ((u, v), (v, u)):
        for d in (G.get_edge_data(a, b) or {}).values():
            out |= classes(d)
    return out


if __name__ == "__main__":
    raise SystemExit(main())
