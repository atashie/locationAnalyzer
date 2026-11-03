"""Verify the two-weight model on the real network, and measure penalty sensitivity.

Three things the earlier write-up asserted without an adequate test:

1. **No penalty leak.** The original check looked for a histogram spike at the penalty value, which
   is the wrong shape: a leak would appear as a per-cell offset, invisible to a histogram. The
   decisive test brackets the reported value between two independently computed bounds:

       time-only Dijkstra   <=   what we report   <=   cost-based Dijkstra
       (fastest real time)       (two-weight)          (what a leak would give)

   A leak makes the upper bound tight everywhere; a correct implementation makes the LOWER bound
   tight wherever the cost-optimal path uses no restricted edge.

2. **Penalty sensitivity.** 450 s drive / 120 s walk are priors from Valhalla's default. Sweeping
   them shows how much the coverage gain and the reported times actually depend on the choice.

3. **Provenance of the recovered cells.** The claim that the newly reachable cells are
   "overwhelmingly homes on driveways" was asserted, not measured. This reports which restricted
   access value each recovered cell's nearest edge carries, so `agricultural`/`forestry` recoveries
   (a stretch for a car) can be told apart from `private`/`driveway` ones.

Run from v2/:  uv run python spikes/verify_two_weight.py [--mode walk] [--category grocery]
"""
from __future__ import annotations

import argparse
import collections
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import osmnx as ox
import shapely

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ACCEPTED_PLACES, GRAPH_CACHE, GRID, append_results, stamp  # noqa: E402
from locfinder.places.categories import select_overture  # noqa: E402
from locfinder.traveltime.access import RESTRICTED_PENALTY_S, classify_access  # noqa: E402
from locfinder.traveltime.arrival import arrival_seconds, arrival_seconds_two_weight  # noqa: E402
from locfinder.traveltime.components import largest_component  # noqa: E402
from locfinder.traveltime.csr import graph_to_cost_time_csr  # noqa: E402
from locfinder.traveltime.snap import EdgeIndex, cell_seconds_from_arrival  # noqa: E402
from locfinder.traveltime.speeds import EXTRA_WAY_TAGS, add_travel_times, symmetrise  # noqa: E402

EPS = 1e-6


def build(mode: str, penalty: float | None = None):
    ox.settings.useful_tags_way = sorted(set(ox.settings.useful_tags_way) | set(EXTRA_WAY_TAGS))
    G = ox.project_graph(ox.load_graphml(GRAPH_CACHE), to_crs=GRID.crs)
    G = add_travel_times(G, mode=mode)
    if penalty is not None:
        for _, _, d in G.edges(data=True):
            if d.get("access_restricted"):
                d["cost"] = d["travel_time"] + penalty
            else:
                d["cost"] = d["travel_time"]
    if mode == "walk":
        G = symmetrise(G)
    G.remove_nodes_from([n for n, d in G.degree() if d == 0])
    G, rep = largest_component(G)
    return G, rep


def destinations(G, index, category: str):
    places = gpd.read_parquet(ACCEPTED_PLACES).to_crs(GRID.crs)
    sel = select_overture(places, category)
    cent = sel.geometry.centroid
    nodes, dists = ox.nearest_nodes(G, cent.x.to_numpy(), cent.y.to_numpy(), return_dist=True)
    keep = np.asarray(dists) <= 300.0
    return sorted({index[n] for n, k in zip(nodes, keep) if k})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="walk", choices=["walk", "bike", "drive"])
    ap.add_argument("--category", default="grocery")
    args = ap.parse_args()
    base_penalty = RESTRICTED_PENALTY_S[args.mode]

    G, rep = build(args.mode)
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
    dest = destinations(G, index, args.category)
    print(f"{args.mode}: {G.number_of_nodes()} nodes, {rep.summary}, {len(dest)} destination nodes")

    # ---- 1. bracket test on node arrival times -------------------------------------------
    lower = arrival_seconds(time_csr, dest_idx=dest)                  # fastest real time
    report = arrival_seconds_two_weight(cost_csr, time_csr, dest_idx=dest)
    upper = arrival_seconds(cost_csr, dest_idx=dest)                  # what a leak would give
    fin = np.isfinite(lower) & np.isfinite(report) & np.isfinite(upper)
    below = int((report[fin] < lower[fin] - EPS).sum())
    above = int((report[fin] > upper[fin] + EPS).sum())
    equal_lower = int(np.isclose(report[fin], lower[fin], atol=1e-6).sum())
    equal_upper = int(np.isclose(report[fin], upper[fin], atol=1e-6).sum())
    diverted = int((report[fin] > lower[fin] + EPS).sum())
    # The leak signature is only meaningful where cost and time actually differ. On the ~88% of
    # nodes untouched by a restricted edge, cost == time and ALL THREE computations coincide, so
    # "reported equals cost-based" there is arithmetic, not evidence (my earlier verdict logic got
    # this wrong and reported a false FAIL).
    bites = fin & (upper > lower + EPS)
    leak = int(np.isclose(report[bites], upper[bites], atol=1e-6).sum()) if bites.any() else 0
    stripped = int((report[bites] < upper[bites] - EPS).sum()) if bites.any() else 0
    lines = [f"### Two-weight verification on the real network ({stamp()}): {args.mode} / {args.category}",
             "", f"{G.number_of_nodes():,} nodes, {len(dest)} destinations, {int(fin.sum()):,} nodes finite in all three computations.",
             "", "**Bracket test.** The reported value must satisfy "
             "`time-only <= reported <= cost-based`; a penalty leak makes the upper bound tight everywhere.",
             "", "| check | nodes | share of finite |", "|---|---|---|",
             f"| reported **below** the time-only lower bound (must be 0) | **{below}** | {below / fin.sum():.4%} |",
             f"| reported **above** the cost-based upper bound (must be 0) | **{above}** | {above / fin.sum():.4%} |",
             f"| reported **equals** the time-only bound (no penalty in effect) | {equal_lower:,} | {equal_lower / fin.sum():.2%} |",
             f"| reported equals the cost-based value **overall** (expected where cost==time) | {equal_upper:,} | {equal_upper / fin.sum():.2%} |",
             f"| reported **above** time-only, i.e. the penalty diverted the path | {diverted:,} | {diverted / fin.sum():.2%} |",
             "", "The decisive rows, restricted to the nodes where cost and time actually differ "
             f"(**{int(bites.sum()):,}** nodes; everywhere else cost == time and all three agree by arithmetic):",
             "", "| check | nodes | share of those |", "|---|---|---|",
             f"| penalty **stripped** from the report (correct) | **{stripped:,}** | {stripped / max(int(bites.sum()), 1):.2%} |",
             f"| report **still carries** the penalty (a leak) | **{leak:,}** | {leak / max(int(bites.sum()), 1):.2%} |"]
    verdict = "PASS" if below == 0 and above == 0 and leak == 0 else "FAIL"
    lines += ["", f"**Verdict: {verdict}.** "
              + ("The reported times sit inside the bracket, and on every node where cost and time differ "
                 "the penalty has been stripped from the reported figure. The penalty is not leaking."
                 if verdict == "PASS" else
                 "The bracket is violated or the reported value tracks the cost-based one: the penalty is "
                 "leaking into reported time.")]

    # ---- 2. penalty sensitivity ------------------------------------------------------------
    xs, ys = GRID.cell_centers_xy()
    eidx = EdgeIndex.from_graph(G, index)
    lines += ["", "**Penalty sensitivity.** Same graph and destinations, penalty varied. "
              f"The adopted value is {base_penalty:.0f} s.", "",
              "| penalty s | cells with a time | median reported min | nodes diverted by the penalty |",
              "|---|---|---|---|"]
    for pen in (0.0, base_penalty / 2, base_penalty, base_penalty * 2, base_penalty * 8):
        Gp, _ = build(args.mode, penalty=pen)
        cp, tp, ip = graph_to_cost_time_csr(Gp)
        dp = destinations(Gp, ip, args.category)
        rp = arrival_seconds_two_weight(cp, tp, dest_idx=dp, cutoff_s=120 * 60)
        lo = arrival_seconds(tp, dest_idx=dp, cutoff_s=120 * 60)
        idxp = EdgeIndex.from_graph(Gp, ip)
        secs = cell_seconds_from_arrival(idxp, rp, xs, ys, mode=args.mode, max_access_m=200.0)
        f = np.isfinite(rp) & np.isfinite(lo)
        div = int((rp[f] > lo[f] + EPS).sum())
        lines.append(f"| {pen:.0f} | {np.isfinite(secs).mean():.2%} | "
                     f"{np.median(secs[np.isfinite(secs)]) / 60:.1f} | {div:,} |")

    # ---- 3. provenance of cells that depend on restricted access --------------------------
    nearest = eidx.tree.nearest(shapely.points(xs.ravel(), ys.ravel()))
    cls_by_geom = {}
    for u, v, d in G.edges(data=True):
        if d.get("access_restricted"):
            a = d.get("access")
            a = a[0] if isinstance(a, list) else a
            cls_by_geom[round(float(d.get("length", 0.0)), 4)] = str(a)
    restricted_len = set(cls_by_geom)
    snapped_len = np.array([round(g.length, 4) for g in eidx.geoms])[nearest]
    on_restricted = np.isin(snapped_len, list(restricted_len))
    secs_base = cell_seconds_from_arrival(eidx, report, xs, ys, mode=args.mode, max_access_m=200.0)
    reach = np.isfinite(secs_base).ravel()
    counts = collections.Counter(cls_by_geom.get(l, "?") for l in snapped_len[on_restricted & reach])
    lines += ["", "**Provenance of reachable cells whose nearest edge is restricted** (by that edge's "
              "`access` value; a length-keyed approximation, so read it as indicative):", "",
              "| access value | reachable cells snapped to it |", "|---|---|"]
    for k, c in counts.most_common(8):
        lines.append(f"| {k} | {c:,} |")
    lines += ["", f"Total reachable cells nearest a restricted edge: {int((on_restricted & reach).sum()):,} "
              f"of {int(reach.sum()):,} reachable."]

    text = "\n".join(lines)
    print("\n" + text)
    append_results("spotcheck-engines.md", text)


if __name__ == "__main__":
    main()
