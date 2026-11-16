"""What kind of edge do the donut holes snap to, compared with everywhere else?

One hole was diagnosed by hand: its nearest edge is a `service=parking_aisle` sharing no node with
the secondary road 33 m away, so the model walks that parcel out of a car park the long way round.
If that generalises, the fix is about which edges may serve as an ACCESS candidate at all -- a
much narrower and more defensible change than widening the access cap, which was measured to need
a 169 m median straight-line walk to work.
"""
import argparse
import pathlib
import sys
import time
from collections import Counter

import geopandas as gpd
import numpy as np
import osmnx as ox
from scipy.sparse.csgraph import dijkstra

V2 = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V2))
sys.path.insert(1, str(V2 / "spikes"))
from _common import ACCEPTED_PLACES, GRID, LAYERS, load_roads_graph  # noqa: E402

from locfinder.grid import encode_minutes  # noqa: E402
from locfinder.places.categories import select_target  # noqa: E402
from locfinder.traveltime.arrival import arrival_seconds  # noqa: E402
from locfinder.traveltime.components import largest_component  # noqa: E402
from locfinder.traveltime.csr import graph_to_cost_time_csr  # noqa: E402
from locfinder.traveltime.snap import EdgeIndex, _snap_network  # noqa: E402
from locfinder.traveltime.speeds import add_travel_times, symmetrise  # noqa: E402

OK = 0
POI_SNAP_MAX_M = 300.0


def klass(G, rev, eidx, gi):
    s_osm, e_osm = rev[eidx.start_idx[gi]], rev[eidx.end_idx[gi]]
    best = None
    for data in (G.get_edge_data(s_osm, e_osm) or {}).values():
        if best is None or data.get("length", 0) > best.get("length", 0):
            best = data
    if best is None:
        return "(none)"
    hw = best.get("highway")
    hw = "/".join(str(h) for h in hw) if isinstance(hw, list) else str(hw)
    sv = best.get("service")
    sv = "/".join(str(s) for s in sv) if isinstance(sv, list) else (str(sv) if sv else None)
    return f"{hw}:{sv}" if sv else hw


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default="park")
    ap.add_argument("--mode", default="walk")
    ap.add_argument("--threshold", type=int, default=20)
    args = ap.parse_args()
    stem = f"own_triangle_{args.target}_{args.mode}"

    t0 = time.perf_counter()
    G = load_roads_graph()
    G = ox.project_graph(G, to_crs=GRID.crs)
    G = add_travel_times(G, mode=args.mode)
    if args.mode == "walk":
        G = symmetrise(G)
    G.remove_nodes_from([n for n, d in G.degree() if d == 0])
    G, _ = largest_component(G)
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
    rev = {v: k for k, v in index.items()}
    print(f"graph ready in {time.perf_counter() - t0:.0f}s", flush=True)

    places = gpd.read_parquet(ACCEPTED_PLACES).to_crs(GRID.crs)
    sel = select_target(places, args.target)
    cent = sel.geometry.centroid
    nodes, dists = ox.nearest_nodes(G, cent.x.to_numpy(), cent.y.to_numpy(), return_dist=True)
    keep = np.asarray(dists) <= POI_SNAP_MAX_M
    dest_idx = sorted({index[n] for n, k in zip(nodes, keep) if k})
    node_cost = np.asarray(arrival_seconds(cost_csr, dest_idx=dest_idx))
    dist, pred, _ = dijkstra(cost_csr.transpose().tocsr(), directed=True,
                             indices=np.asarray(dest_idx, dtype=np.int64),
                             min_only=True, return_predecessors=True)
    time_t = time_csr.transpose().tocsr()
    Treal = np.full(cost_csr.shape[0], np.inf)
    order = np.flatnonzero(np.isfinite(dist))
    order = order[np.argsort(np.asarray(dist)[order], kind="stable")]
    pred = np.asarray(pred, dtype=np.int64)
    for n in order:
        p = pred[n]
        Treal[n] = 0.0 if p == -9999 else (Treal[p] + time_t[p, n]
                                           if np.isfinite(Treal[p]) else np.inf)

    eidx = EdgeIndex.from_graph(G, index)
    xs, ys = GRID.cell_centers_xy()
    secs = np.load(LAYERS / f"{stem}.npy").astype(np.float64)
    reason = np.load(LAYERS / f"{stem}_reason.npy")
    value = encode_minutes(secs).astype(np.int32)
    passing = (reason == OK) & (value <= args.threshold)
    failing = (reason == OK) & (value > args.threshold)
    nb = [np.roll(np.roll(passing, dr, 0), dc, 1)
          for dr in (-1, 0, 1) for dc in (-1, 0, 1) if (dr, dc) != (0, 0)]
    ring = np.logical_and.reduce(nb)
    ring[0, :] = ring[-1, :] = ring[:, 0] = ring[:, -1] = False
    hole = failing & ring
    hr, hc = np.where(hole)
    print(f"{len(hr)} holes at {args.threshold} min on {stem}")

    snapped_h = _snap_network(eidx, Treal, xs[hr, hc], ys[hr, hc], node_cost=node_cost)
    hole_classes = Counter(klass(G, rev, eidx, int(g)) for g in snapped_h.matched_idx)

    rng = np.random.default_rng(7)
    sample = rng.choice(xs.size, size=20000, replace=False)
    sx, sy = xs.ravel()[sample], ys.ravel()[sample]
    snapped_s = _snap_network(eidx, Treal, sx, sy, node_cost=node_cost)
    base_classes = Counter(klass(G, rev, eidx, int(g)) for g in snapped_s.matched_idx)

    print(f"\n  {'matched edge class':<34} {'in holes':>9} {'share':>7}   "
          f"{'baseline share':>14}  {'enrichment':>10}")
    for cls, n in hole_classes.most_common(12):
        hs = n / len(hr)
        bs = base_classes.get(cls, 0) / len(sample)
        enr = (hs / bs) if bs else float("inf")
        print(f"  {cls:<34} {n:>9} {hs * 100:>6.1f}%   {bs * 100:>13.2f}%  "
              f"{enr:>9.1f}x")
    print(f"\n  baseline, for comparison (20,000 random cells):")
    for cls, n in base_classes.most_common(8):
        print(f"    {cls:<32} {n / len(sample) * 100:>6.2f}%")


if __name__ == "__main__":
    main()
