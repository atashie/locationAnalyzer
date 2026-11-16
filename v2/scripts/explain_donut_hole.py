"""What makes a donut hole four minutes slower than all eight of its neighbours?

Three candidate mechanisms, and this prints the quantity that separates them for each hole and for
every neighbour:

  A. it snapped to a DIFFERENT edge than its neighbours did, and that edge's endpoints are worse;
  B. its ACCESS LEG is long -- the straight line to the matched edge, at 1.26 m/s, capped at 200 m;
  C. it sits mid-edge and pays `(1 - frac) * edge_time` to reach an endpoint while its neighbours
     sit near a node.

For each hole: the matched way, its length, the access leg, the position along it, the on-edge
seconds, the arrival at the chosen endpoint, and the total. Same for the eight neighbours, so the
difference is read off rather than inferred.
"""
import argparse
import json
import pathlib
import sys
import time

import geopandas as gpd
import numpy as np
import osmnx as ox
import shapely
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
from locfinder.traveltime.speeds import access_speed_mps, add_travel_times, symmetrise  # noqa: E402

OK = 0
POI_SNAP_MAX_M = 300.0


def edge_label(G, idx_rev, eidx, gi):
    s_osm, e_osm = idx_rev[eidx.start_idx[gi]], idx_rev[eidx.end_idx[gi]]
    best = None
    for data in (G.get_edge_data(s_osm, e_osm) or {}).values():
        if best is None or data.get("length", 0) > best.get("length", 0):
            best = data
    if best is None:
        return "(no edge)", float("nan"), None
    name = best.get("name")
    if isinstance(name, list):
        name = "/".join(str(n) for n in name)
    hw = best.get("highway")
    if isinstance(hw, list):
        hw = "/".join(str(h) for h in hw)
    return f"{name or '(unnamed)'} [{hw}]", float(best.get("length", float("nan"))), best.get("osmid")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default="park")
    ap.add_argument("--mode", default="walk")
    ap.add_argument("--threshold", type=int, default=20)
    ap.add_argument("--holes", type=int, default=4)
    args = ap.parse_args()
    stem = f"own_triangle_{args.target}_{args.mode}"

    t = time.perf_counter()
    G = load_roads_graph()
    G = ox.project_graph(G, to_crs=GRID.crs)
    G = add_travel_times(G, mode=args.mode)
    if args.mode == "walk":
        G = symmetrise(G)
    G.remove_nodes_from([n for n, d in G.degree() if d == 0])
    G, _ = largest_component(G)
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
    rev = {v: k for k, v in index.items()}
    print(f"graph ready in {time.perf_counter() - t:.0f}s", flush=True)

    places = gpd.read_parquet(ACCEPTED_PLACES).to_crs(GRID.crs)
    sel = select_target(places, args.target)
    cent = sel.geometry.centroid
    nodes, dists = ox.nearest_nodes(G, cent.x.to_numpy(), cent.y.to_numpy(), return_dist=True)
    keep = np.asarray(dists) <= POI_SNAP_MAX_M
    dest_idx = sorted({index[n] for n, k in zip(nodes, keep) if k})
    print(f"{len(sel)} places -> {len(dest_idx)} destination nodes; "
          f"POI->node displacement: median {np.median(dists[keep]):.0f} m, "
          f"p90 {np.percentile(dists[keep], 90):.0f} m, max {dists[keep].max():.0f} m")

    node_cost = np.asarray(arrival_seconds(cost_csr, dest_idx=dest_idx))
    # Real seconds at each node along the cost-optimal path, same sweep arrival.py uses.
    dist, pred, _src = dijkstra(cost_csr.transpose().tocsr(), directed=True,
                                indices=np.asarray(dest_idx, dtype=np.int64),
                                min_only=True, return_predecessors=True)
    time_t = time_csr.transpose().tocsr()
    Treal = np.full(cost_csr.shape[0], np.inf)
    order = np.flatnonzero(np.isfinite(dist))
    order = order[np.argsort(np.asarray(dist)[order], kind="stable")]
    pred = np.asarray(pred, dtype=np.int64)
    for n in order:
        p = pred[n]
        if p == -9999:
            Treal[n] = 0.0
        else:
            prev = Treal[p]
            Treal[n] = prev + time_t[p, n] if np.isfinite(prev) else np.inf

    eidx = EdgeIndex.from_graph(G, index)
    xs, ys = GRID.cell_centers_xy()

    # the holes, from the published surface
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
    rows, cols = np.where(hole)
    gaps = np.array([secs[r, c] - np.nanmean(np.where(
        np.arange(9) == 4, np.nan, secs[r - 1:r + 2, c - 1:c + 2].ravel()))
        for r, c in zip(rows, cols)])
    order_h = np.argsort(-gaps)[:args.holes]
    print(f"\n{len(rows)} holes at {args.threshold} min; showing the {len(order_h)} largest gaps\n")

    for k in order_h:
        r0, c0 = int(rows[k]), int(cols[k])
        print(f"===== hole at row {r0}, col {c0}: {secs[r0, c0] / 60:.1f} min, "
              f"{gaps[k]:.0f} s slower than its ring =====")
        pts_x, pts_y, labels = [], [], []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                pts_x.append(xs[r0 + dr, c0 + dc])
                pts_y.append(ys[r0 + dr, c0 + dc])
                labels.append("HOLE" if (dr, dc) == (0, 0) else f"{dr:+d}{dc:+d}")
        snapped = _snap_network(eidx, Treal, np.array(pts_x), np.array(pts_y),
                                node_cost=node_cost)
        print(f"  {'cell':>5} {'total':>7} {'access':>8} {'onedge':>7} {'atnode':>8}  "
              f"{'frac':>5} {'edge_m':>7}  matched way")
        for i, lab in enumerate(labels):
            gi = int(snapped.matched_idx[i])
            name, elen, way = edge_label(G, rev, eidx, gi)
            acc = float(snapped.access_m[i])
            net = float(snapped.network[i])
            chosen = int(snapped.chosen_idx[i])
            at_node = Treal[chosen] if chosen >= 0 else float("inf")
            frac = float(shapely.line_locate_point(
                eidx.geoms[gi], shapely.points([pts_x[i]], [pts_y[i]])[0], normalized=True))
            on_edge = net - at_node
            total = net + acc / access_speed_mps(args.mode)
            print(f"  {lab:>5} {total / 60:6.1f}m {acc:7.1f}m {on_edge:6.0f}s {at_node / 60:7.1f}m"
                  f"  {frac:5.2f} {elen:7.0f}  {name} way {way}")
        print()


if __name__ == "__main__":
    main()
