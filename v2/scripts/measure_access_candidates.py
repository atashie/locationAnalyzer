"""`tree.nearest` takes ONE edge. What does taking the best edge within the access cap cost?

The donut holes are cells whose single nearest edge is a badly connected service way or footway,
while a road 20-45 m further off -- well inside the 200 m access cap the model already allows --
would have given a journey ten to fifteen minutes shorter. The model never looks at it, because
`_snap_network` calls `idx.tree.nearest(pts)` and considers exactly one candidate.

This measures the alternative: for every cell, take the minimum over EVERY edge within the cap,
scoring each candidate the way the production rule already scores the one it picks. Considering
more candidates can only lower a time, so the comparison is one-sided by construction and the
question is how much and where.

Nothing is written. This prices a change; it does not make one.
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
MAX_ACCESS_M = 200.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default="park")
    ap.add_argument("--mode", default="walk")
    ap.add_argument("--thresholds", default="10,15,20,30")
    args = ap.parse_args()
    stem = f"own_triangle_{args.target}_{args.mode}"
    thresholds = [int(t) for t in args.thresholds.split(",")]

    t0 = time.perf_counter()
    G = load_roads_graph()
    G = ox.project_graph(G, to_crs=GRID.crs)
    G = add_travel_times(G, mode=args.mode)
    if args.mode == "walk":
        G = symmetrise(G)
    G.remove_nodes_from([n for n, d in G.degree() if d == 0])
    G, _ = largest_component(G)
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
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
    px, py = xs.ravel(), ys.ravel()
    pts = shapely.points(px, py)
    access_mps = access_speed_mps(args.mode)

    # ---- what the model does now -------------------------------------------------------------
    cur = _snap_network(eidx, Treal, px, py, node_cost=node_cost)
    cur_total = cur.network + cur.access_m / access_mps
    cur_total = np.where(cur.access_m <= MAX_ACCESS_M, cur_total, np.inf)

    # ---- every edge within the cap, scored the same way --------------------------------------
    t1 = time.perf_counter()
    pi, gi = eidx.tree.query(pts, predicate="dwithin", distance=MAX_ACCESS_M)
    print(f"{len(pi):,} (cell, edge) candidate pairs within {MAX_ACCESS_M:.0f} m "
          f"in {time.perf_counter() - t1:.0f}s; "
          f"{len(pi) / len(pts):.1f} candidates per cell", flush=True)

    geoms = eidx.geoms[gi]
    acc = shapely.distance(pts[pi], geoms)
    frac = shapely.line_locate_point(geoms, pts[pi], normalized=True)
    s_i, e_i = eidx.start_idx[gi], eidx.end_idx[gi]
    fwd_t, rev_t = eidx.fwd_time[gi], eidx.rev_time[gi]
    fwd_c, rev_c = eidx.fwd_cost[gi], eidx.rev_cost[gi]

    t_end = np.where(np.isfinite(fwd_t), (1.0 - frac) * fwd_t + Treal[e_i], np.inf)
    t_start = np.where(np.isfinite(rev_t), frac * rev_t + Treal[s_i], np.inf)
    c_end = np.where(np.isfinite(fwd_c), (1.0 - frac) * fwd_c + node_cost[e_i], np.inf)
    c_start = np.where(np.isfinite(rev_c), frac * rev_c + node_cost[s_i], np.inf)
    take_end = np.where(c_end == c_start, t_end <= t_start, c_end < c_start)
    net = np.where(take_end, t_end, t_start)
    cand_total = net + acc / access_mps

    # Several caps from one query: a candidate beyond the cap is simply not eligible. The cap
    # bounds how far the straight-line access assumption is allowed to carry a cell to a BETTER
    # road, which is a bigger claim than carrying it to the NEAREST one.
    CAPS = [25.0, 50.0, 100.0, 200.0]
    bests = {}
    for cap in CAPS:
        b = np.full(len(pts), np.inf)
        elig = acc <= cap
        np.minimum.at(b, pi[elig], cand_total[elig])
        # **Today is the floor.** Without this, a cap smaller than the access limit DROPS every
        # cell whose nearest edge is beyond it -- so the row would show fewer cells in region and
        # MORE holes, and would be comparing a different population rather than a better rule.
        # The variant being priced is "what we do now, plus any better edge within <cap>".
        bests[cap] = np.minimum(b, cur_total)
    best = bests[MAX_ACCESS_M]

    # A rule that does NOT teleport: consider every edge that is nearly as close as the nearest
    # one. The access leg stays honest -- you only ever consider roads about as far away as the
    # road you were already going to walk to -- and it fixes the case the holes are made of, where
    # two edges are almost equidistant and one of them is connected far better than the other.
    nearest_acc = np.minimum.reduceat(
        np.r_[acc, np.inf], np.r_[0]) if False else None
    near_by_cell = np.full(len(pts), np.inf)
    np.minimum.at(near_by_cell, pi, acc)
    DELTAS = [10.0, 25.0, 50.0]
    for d in DELTAS:
        b = np.full(len(pts), np.inf)
        elig = acc <= near_by_cell[pi] + d
        np.minimum.at(b, pi[elig], cand_total[elig])
        bests[("delta", d)] = np.minimum(b, cur_total)

    cur_total = cur_total.reshape(xs.shape)
    best = best.reshape(xs.shape)
    both = np.isfinite(cur_total) & np.isfinite(best)
    gain = np.where(both, cur_total - best, np.nan)

    print(f"\n=== {stem}: nearest edge vs best edge within {MAX_ACCESS_M:.0f} m ===")
    worse = np.nansum(gain < -1e-6)
    print(f"  cells where the current rule is FASTER (must be 0): {int(worse)}")
    improved = np.nansum(gain > 1.0)
    print(f"  cells improved by more than 1 s: {int(improved):,} "
          f"({improved / both.sum() * 100:.2f}% of comparable)")
    g = gain[both & (gain > 1.0)]
    if g.size:
        print(f"  improvement where it happens: median {np.median(g):.0f} s, "
              f"p90 {np.percentile(g, 90):.0f} s, p99 {np.percentile(g, 99):.0f} s, "
              f"max {g.max():.0f} s")
    newly = np.isfinite(best) & ~np.isfinite(cur_total)
    print(f"  cells that gain a finite time at all: {int(newly.sum()):,}")

    reason = np.load(LAYERS / f"{stem}_reason.npy")

    def holes_of(p, finite):
        nb = [np.roll(np.roll(p, dr, 0), dc, 1)
              for dr in (-1, 0, 1) for dc in (-1, 0, 1) if (dr, dc) != (0, 0)]
        ring = np.logical_and.reduce(nb)
        ring[0, :] = ring[-1, :] = ring[:, 0] = ring[:, -1] = False
        return int((~p & ring & finite).sum())

    print()
    print("  --- how far the access leg may reach for a BETTER edge ---")
    print(f"  {'cap':>6} {'improved >1s':>13} {'median':>8} {'p99':>8} "
          + "  ".join(f"{'in@' + str(th):>10} {'holes':>6}" for th in thresholds))
    for cap in list(CAPS) + [("delta", d) for d in DELTAS]:
        b = bests[cap].reshape(xs.shape)
        bo = np.isfinite(cur_total) & np.isfinite(b)
        gn = np.where(bo, cur_total - b, np.nan)
        imp = gn[bo & (gn > 1.0)]
        cells = []
        for th in thresholds:
            nv = encode_minutes(np.where(np.isfinite(b), b, np.inf))
            npass = np.isfinite(b) & (nv <= th)
            cells.append(f"{int(npass.sum()):>10,} {holes_of(npass, np.isfinite(cur_total)):>6}")
        tag = f"{cap:>5.0f}m" if not isinstance(cap, tuple) else f"+{cap[1]:>4.0f}m"
        print(f"  {tag:>6} {int((gn > 1.0).sum()):>13,} "
              f"{np.median(imp) if imp.size else 0:>7.0f}s "
              f"{np.percentile(imp, 99) if imp.size else 0:>7.0f}s  "
              + "  ".join(cells))

    # How far the WINNING edge is, for the cells that improve. The whole credibility of this
    # change rests here: today a long straight access leg is only ever walked to the NEAREST
    # edge, which is at worst a field between you and your own road. Letting a cell pick a
    # BETTER edge 180 m away assumes it can cross whatever lies between, which is a larger claim.
    flat_cur = cur_total.ravel()
    winner = np.full(len(flat_cur), np.inf)
    np.minimum.at(winner, pi, cand_total)
    improved_mask = (flat_cur - winner) > 60.0
    win_acc = np.full(len(flat_cur), np.nan)
    # recover the access distance of the minimising candidate
    order_c = np.lexsort((cand_total, pi))
    first = np.ones(len(pi), dtype=bool)
    first[1:] = pi[order_c][1:] != pi[order_c][:-1]
    win_acc[pi[order_c][first]] = acc[order_c][first]
    sel_acc = win_acc[improved_mask & np.isfinite(win_acc)]
    cur_acc = cur.access_m[improved_mask & np.isfinite(win_acc)]
    if sel_acc.size:
        print()
        print(f"  --- for the {sel_acc.size:,} cells improved by more than 60 s ---")
        print(f"  access leg TODAY (nearest edge):  median {np.median(cur_acc):.0f} m, "
              f"p90 {np.percentile(cur_acc, 90):.0f} m")
        print(f"  access leg to the WINNING edge:   median {np.median(sel_acc):.0f} m, "
              f"p90 {np.percentile(sel_acc, 90):.0f} m, max {sel_acc.max():.0f} m")
        for d in (25, 50, 100, 150, 200):
            print(f"    winning edge within {d:>3} m: {int((sel_acc <= d).sum()):>7,} "
                  f"({(sel_acc <= d).mean() * 100:5.1f}%)")

    print()
    for th in thresholds:
        cur_v = encode_minutes(np.where(reason == OK, cur_total, np.inf))
        new_v = encode_minutes(np.where(np.isfinite(best), best, np.inf))
        cur_pass = (reason == OK) & (cur_v <= th)
        new_pass = np.isfinite(best) & (new_v <= th)
        flipped = new_pass & ~cur_pass
        # holes under each rule
        def holes(p):
            nb = [np.roll(np.roll(p, dr, 0), dc, 1)
                  for dr in (-1, 0, 1) for dc in (-1, 0, 1) if (dr, dc) != (0, 0)]
            ring = np.logical_and.reduce(nb)
            ring[0, :] = ring[-1, :] = ring[:, 0] = ring[:, -1] = False
            return int((~p & ring & np.isfinite(cur_total)).sum())
        print(f"  limit {th:>3} min: in region {int(cur_pass.sum()):,} -> {int(new_pass.sum()):,} "
              f"(+{int(flipped.sum()):,});  holes {holes(cur_pass)} -> {holes(new_pass)}")


if __name__ == "__main__":
    main()
