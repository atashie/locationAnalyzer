"""WITHDRAWN 2026-11-04. Replaced by `s2_access_lawfulness_v2.py`.

Codex pass 13 found four High defects here: the cell snap re-admitted restricted travel below the
node level, the "unpenalised" branch still charged access penalties, the restricted filter ran after
parallel-edge collapse and so deleted lawful public alternatives, and — the one that invalidates the
framing rather than the arithmetic — **edge position does not establish lawfulness**, because
splitting a driveway into two ways changes a journey's verdict without changing the journey.

The measurements below reproduce exactly and the conclusions drawn from them are withdrawn. It is
kept, rather than deleted, because it is the clearest record of how an audit can measure three
things and conclude four. The replacement states the policy as a language (`R* O* R*`) and solves it
on a graph x automaton product; see `locfinder/traveltime/policy.py` and the S2.3 section of
`docs/plans/2026-11-03-phase1-plan.md`.

---

S2.3: are the routes the access fix recovered *lawful*?

`access.py` resolved a real coverage hole. Blocking all 126,157 restricted edges made every home on
a private drive unreachable, so a restricted edge now costs extra to **choose** and takes its real
time to **travel**. That is what mainstream engines do, and S2.5 measured its worth: 4,420 of
256,752 reachable cells have a restricted edge as their nearest, 4,178 of them `access=private`.

But "nearest edge is restricted" is not the question. A driveway used to *leave* the house it serves
is lawful and is the whole point of the fix. The same edge used in the *middle* of a journey is
through traffic over private land, which is not lawful and which `access=destination` literally
forbids. A penalty discourages that without forbidding it, so nothing yet establishes that what we
publish stays on the right side of the line. Pass 6 left this open and the plan has carried it as
S2.3 since.

Two numbers, because they answer different questions and I expect them to disagree.

**Descriptive: how many shipped paths are unlawful?** Walk the predecessor forest and mark, for
every node, whether a restricted edge appears anywhere after its own first hop (and not as the final
hop into a destination, which is the destination's own access and equally lawful). That counts paths
we would have to *reroute*.

**Decisive: how much coverage has no lawful path at all?** Build the surface a strict policy would
produce — restricted edges usable only as the first hop out of the origin — and compare. A node can
have an unlawful shipped path and a perfectly good lawful alternative; only the second number is
coverage actually at risk.

The strict surface allows a restricted hop at the **origin** end only. A restricted final hop into
a destination's own parking aisle is equally lawful and is not modelled, so lawful coverage is
understated and the exposure this reports is an **upper bound** on what a strict policy would cost.

Restricted edges are identified from the matrices rather than re-read from tags: `cost - time` is
exactly the access penalty, and `graph_to_cost_time_csr` retains the cost-minimal parallel edge, so
this tests the edges the search actually used.

Run from v2/:  uv run python spikes/s2_access_lawfulness_audit.py grocery walk
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import osmnx as ox
import scipy.sparse as sp
from scipy.sparse.csgraph import dijkstra

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (ACCEPTED_PLACES, GRAPH_CACHE, GRID, LAYERS, METRO,  # noqa: E402
                     append_results, stamp)
from locfinder import profile, status as st  # noqa: E402
from locfinder.places.categories import select_overture  # noqa: E402
from locfinder.status import Reason  # noqa: E402
from locfinder.traveltime.arrival import arrival_seconds_two_weight  # noqa: E402
from locfinder.traveltime.components import largest_component  # noqa: E402
from locfinder.traveltime.csr import graph_to_cost_time_csr  # noqa: E402
from locfinder.traveltime.snap import EdgeIndex, cell_arrival_with_provenance  # noqa: E402
from locfinder.traveltime.speeds import add_travel_times, symmetrise  # noqa: E402

POI_SNAP_MAX_M = 300.0
MAX_ACCESS_M = 200.0
CUTOFF_MIN = 120.0
HORIZON_S = CUTOFF_MIN * 60.0
THRESHOLDS_MIN = (10, 15, 25, 45)
PENALTY_TOL_S = 1e-6
NO_PRED = -9999


def classify_paths(restricted: sp.csr_matrix, dist: np.ndarray,
                   pred: np.ndarray) -> dict[str, np.ndarray]:
    """Mark, per node, where restricted edges sit on its shipped path.

    `pred` is from the search on the **transposed** graph, so `pred[n]` is the next node *towards*
    the destination and the real-graph edge travelled is `n -> pred[n]`. Resolving nodes in
    increasing cost order makes each node's predecessor already final, which is the same topological
    argument `arrival.py` relies on.

    `nonlast` excludes a restricted edge that arrives at a destination: that is the destination's own
    access and is as lawful as the origin's driveway.
    """
    n = dist.size
    # A set of linear indices, not sparse scalar lookups: this loop runs once per reachable node and
    # `restricted[p, node]` inside it cost more than the whole rest of the audit.
    r = restricted.tocoo()
    restricted_pairs = set((r.row.astype(np.int64) * n + r.col.astype(np.int64)).tolist())
    first_restricted = np.zeros(n, dtype=bool)   # the origin's own driveway: lawful
    any_nonlast = np.zeros(n, dtype=bool)        # a restricted edge that is nobody's endpoint
    reachable = np.flatnonzero(np.isfinite(dist))
    order = reachable[np.argsort(dist[reachable], kind="stable")]
    for node in order:
        p = pred[node]
        if p == NO_PRED:
            continue                              # a destination; nothing travelled yet
        is_restricted = (int(node) * n + int(p)) in restricted_pairs
        first_restricted[node] = is_restricted
        arrives_at_destination = pred[p] == NO_PRED
        any_nonlast[node] = (is_restricted and not arrives_at_destination) or any_nonlast[p]
    # A node's path is unlawful when a restricted non-terminal edge appears *after* its first hop.
    through = np.zeros(n, dtype=bool)
    has_pred = (pred != NO_PRED) & np.isfinite(dist)
    through[has_pred] = any_nonlast[pred[has_pred]]
    return {"first_restricted": first_restricted, "through": through,
            "any_nonlast": any_nonlast}


def strict_surface(cost_csr: sp.csr_matrix, time_csr: sp.csr_matrix,
                   restricted: sp.csr_matrix, dest_idx) -> np.ndarray:
    """Node times under the strict policy: restricted edges only as the first hop from the origin.

    Two steps. An arrival search over the **open** subgraph alone, then one relaxation that lets
    each node spend exactly one restricted edge to reach it. Costs equal times on the open subgraph,
    because nothing left in it carries a penalty.
    """
    rows, cols = cost_csr.nonzero()
    if restricted.nnz:
        keep = ~np.asarray(restricted[rows, cols]).ravel().astype(bool)
    else:
        keep = np.ones(cost_csr.nnz, dtype=bool)
    open_csr = sp.coo_matrix((time_csr.data[keep], (rows[keep], cols[keep])),
                             shape=cost_csr.shape).tocsr()
    dest = np.asarray(list(dest_idx), dtype=np.int64)
    t_open = np.asarray(dijkstra(open_csr.transpose().tocsr(), directed=True, indices=dest,
                                 min_only=True), dtype=np.float64)
    # One restricted hop at the origin: time(n->m) + t_open[m].
    t_strict = t_open.copy()
    r = restricted.tocoo()
    if r.nnz:
        via = time_csr[r.row, r.col]
        via = np.asarray(via).ravel() + t_open[r.col]
        np.minimum.at(t_strict, r.row, via)
    return t_strict


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("category")
    ap.add_argument("mode", choices=["walk", "bike", "drive"])
    args = ap.parse_args()
    out: dict = {"metro": METRO.name, "category": args.category, "mode": args.mode}

    t = time.perf_counter()
    G = ox.load_graphml(GRAPH_CACHE)
    G = ox.project_graph(G, to_crs=GRID.crs)
    G = add_travel_times(G, mode=args.mode)
    if args.mode == "walk":
        G = symmetrise(G)
    G.remove_nodes_from([n for n, d in G.degree() if d == 0])
    G, comp = largest_component(G)
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
    eidx = EdgeIndex.from_graph(G, index)
    print(f"graph prepared in {time.perf_counter() - t:.1f}s: {comp.summary}", flush=True)

    # `cost - time` is the access penalty and nothing else: same sparsity, and the retained parallel
    # edge is the same one in both.
    diff = (cost_csr - time_csr).tocsr()
    diff.data[np.abs(diff.data) <= PENALTY_TOL_S] = 0.0
    diff.eliminate_zeros()
    restricted = diff.copy()
    restricted.data = np.ones_like(restricted.data)
    out["edges"] = {"total": int(cost_csr.nnz), "restricted": int(restricted.nnz),
                    "restricted_share": float(restricted.nnz / cost_csr.nnz),
                    "penalties_seen_s": sorted({round(float(v), 3) for v in diff.data})[:8]}
    print(f"restricted edges: {restricted.nnz:,} of {cost_csr.nnz:,} "
          f"({restricted.nnz / cost_csr.nnz:.2%}); penalties {out['edges']['penalties_seen_s']}",
          flush=True)

    places = gpd.read_parquet(ACCEPTED_PLACES).to_crs(GRID.crs)
    sel = select_overture(places, args.category)
    cent = sel.geometry.centroid
    nodes, dists = ox.nearest_nodes(G, cent.x.to_numpy(), cent.y.to_numpy(), return_dist=True)
    dest_idx = sorted({index[n] for n, d in zip(nodes, dists) if d <= POI_SNAP_MAX_M})

    # ---- shipped node times, and the predecessor forest behind them --------------------------
    t = time.perf_counter()
    T_ship = arrival_seconds_two_weight(cost_csr, time_csr, dest_idx=dest_idx)
    cost_t = cost_csr.transpose().tocsr()
    restricted_t = restricted.transpose().tocsr()
    dist, pred, _ = dijkstra(cost_t, directed=True, indices=np.asarray(dest_idx, dtype=np.int64),
                             min_only=True, return_predecessors=True)
    cls = classify_paths(restricted, np.asarray(dist, float), np.asarray(pred, np.int64))
    print(f"paths classified in {time.perf_counter() - t:.1f}s", flush=True)

    reach = np.isfinite(T_ship)
    out["nodes"] = {
        "total": int(T_ship.size), "reachable": int(reach.sum()),
        "first_hop_restricted": int((cls["first_restricted"] & reach).sum()),
        "path_uses_restricted_through": int((cls["through"] & reach).sum()),
    }
    nd = out["nodes"]
    print(f"\nnodes: {nd['reachable']:,} reachable; first hop restricted "
          f"{nd['first_hop_restricted']:,} ({nd['first_hop_restricted'] / nd['reachable']:.4%}); "
          f"shipped path routes THROUGH restricted land "
          f"{nd['path_uses_restricted_through']:,} "
          f"({nd['path_uses_restricted_through'] / nd['reachable']:.4%})", flush=True)

    # ---- the strict policy, and what it would actually cost ----------------------------------
    t = time.perf_counter()
    T_strict = strict_surface(cost_csr, time_csr, restricted, dest_idx)
    print(f"strict surface in {time.perf_counter() - t:.1f}s", flush=True)
    lost = reach & ~np.isfinite(T_strict)
    out["nodes"]["no_lawful_path"] = int(lost.sum())
    both = reach & np.isfinite(T_strict)
    delta = T_strict[both] - T_ship[both]
    out["nodes"]["strict_slower_by_more_than_1s"] = int((delta > 1.0).sum())
    out["nodes"]["strict_median_increase_s"] = float(np.median(delta[delta > 1.0])) \
        if (delta > 1.0).any() else 0.0
    out["nodes"]["strict_max_increase_s"] = float(delta.max()) if delta.size else 0.0
    print(f"strict policy: {lost.sum():,} reachable nodes lose every path; "
          f"{out['nodes']['strict_slower_by_more_than_1s']:,} get slower "
          f"(median +{out['nodes']['strict_median_increase_s']:.1f} s, "
          f"max +{out['nodes']['strict_max_increase_s']:.1f} s)", flush=True)

    # ---- and the same two policies as published cells, weighted by buildings -----------------
    xs, ys = GRID.cell_centers_xy()
    engine = st.ENGINES["own-graph"]
    surfaces = {}
    # `node_cost` is what the snap uses to pick which end of the matched edge a cell enters the
    # network by, and `build_layer_surface` passes the cost array for a two-weight build. Omitting
    # it moved 6 cells, which the raster check below caught — so the shipped branch is given the
    # same cost array the production builder computes. Under the strict policy there is no penalty
    # to apply (a restricted edge is either allowed at the origin or not available at all), so cost
    # and time coincide there and `T_strict` is its own selection cost.
    for name, T, node_cost in (("shipped", T_ship, np.asarray(dist, dtype=np.float64)),
                               ("strict", T_strict, T_strict)):
        node_reason = st.node_reasons(T, engine, search_bounded=False)
        sec, reason, _ = cell_arrival_with_provenance(
            eidx, T, xs.ravel(), ys.ravel(), mode=args.mode, max_access_m=MAX_ACCESS_M,
            horizon_s=HORIZON_S, node_reason=node_reason, node_cost=node_cost)
        surfaces[name] = (sec.reshape(xs.shape), reason.reshape(xs.shape))

    # The "shipped" branch here rebuilds a cell surface outside `build_layer_surface`, so it has to
    # be shown to agree with the one S2.4 cached before anything is concluded from the other branch.
    # A reconstruction that is not checked against the production path is how the expansion adapter
    # went wrong.
    ref = LAYERS / f"own_{METRO.name}_{args.category}_{args.mode}_reason.npy"
    if ref.exists():
        want = np.load(ref)
        same = bool(np.array_equal(want, surfaces["shipped"][1]))
        out["shipped_matches_cached_reason_raster"] = same
        print(f"shipped reason raster matches the cached S2.4 build: {same}", flush=True)
        if not same:
            raise SystemExit(
                f"reconstruction mismatch: the shipped branch disagrees with {ref.name} on "
                f"{int((want != surfaces['shipped'][1]).sum()):,} cells; the strict comparison "
                "would be measuring my reconstruction, not the product")

    counts_path = LAYERS / f"own_{METRO.name}_buildings_per_cell.npy"
    counts = np.load(counts_path) if counts_path.exists() else None
    ok_s, ok_t = surfaces["shipped"][1] == Reason.OK, surfaces["strict"][1] == Reason.OK
    out["cells"] = {"shipped_ok": int(ok_s.sum()), "strict_ok": int(ok_t.sum()),
                    "lost": int((ok_s & ~ok_t).sum()), "gained": int((~ok_s & ok_t).sum())}
    if counts is not None:
        tot_b = int(counts.sum())
        out["cells"].update({
            "buildings_total": tot_b, "buildings_shipped_ok": int(counts[ok_s].sum()),
            "buildings_strict_ok": int(counts[ok_t].sum()),
            "buildings_lost": int(counts[ok_s & ~ok_t].sum())})
    c = out["cells"]
    print(f"\ncells OK: shipped {c['shipped_ok']:,} -> strict {c['strict_ok']:,} "
          f"(lost {c['lost']:,}, gained {c['gained']:,})", flush=True)
    if counts is not None:
        print(f"buildings OK: {c['buildings_shipped_ok']:,} -> {c['buildings_strict_ok']:,} "
              f"of {c['buildings_total']:,}; the strict policy would cost "
              f"{c['buildings_lost']:,} buildings "
              f"({c['buildings_lost'] / c['buildings_total']:.4%})", flush=True)

    out["thresholds"] = {}
    for m in THRESHOLDS_MIN:
        s = m * 60.0
        ps = ok_s & (surfaces["shipped"][0] <= s)
        pt = ok_t & (surfaces["strict"][0] <= s)
        row = {"shipped": int(ps.sum()), "strict": int(pt.sum()), "lost": int((ps & ~pt).sum())}
        if counts is not None:
            row["buildings_lost"] = int(counts[ps & ~pt].sum())
        out["thresholds"][f"{m}min"] = row
    print("\nthresholds, cells passing (shipped -> strict):", flush=True)
    for k, v in out["thresholds"].items():
        extra = f", {v['buildings_lost']:,} buildings" if counts is not None else ""
        print(f"  {k:<6} {v['shipped']:>9,} -> {v['strict']:>9,}  lost {v['lost']:,}{extra}",
              flush=True)

    out["versions"] = {"profile": profile.profile_version(), "grid": profile.grid_version(GRID)}
    append_results("spotcheck-engines.md", render(out, args))
    print("\nappended to docs/experiments/spotcheck-engines.md", flush=True)
    print(json.dumps(out, indent=1, default=str), flush=True)


def render(out: dict, args) -> str:
    e, nd, c = out["edges"], out["nodes"], out["cells"]
    has_b = "buildings_total" in c
    lines = [f"### S2.3 access lawfulness audit: {args.category} / {args.mode} ({stamp()})", "",
             "`access.py` lets a restricted edge be *chosen* at a penalty rather than forbidden, "
             "which is what makes a home on a private drive reachable. The open question was "
             "whether that also lets a published route run **through** private land, which "
             "`access=destination` forbids outright. Restricted edges are identified as "
             "`cost - time > 0` on the retained matrices, so these are the edges the search used.",
             "",
             f"- restricted edges: **{e['restricted']:,} of {e['total']:,}** "
             f"({e['restricted_share']:.2%}); distinct penalties seen "
             f"{e['penalties_seen_s']} s", "",
             "**Descriptive — how many shipped paths are unlawful.** A restricted edge is lawful as "
             "the origin's own first hop and as the final hop into a destination; anywhere else it "
             "is through traffic.", "",
             "| | nodes | share of reachable |", "|---|---|---|",
             f"| reachable | {nd['reachable']:,} | — |",
             f"| first hop restricted (the driveway case, lawful) | {nd['first_hop_restricted']:,} "
             f"| {nd['first_hop_restricted'] / nd['reachable']:.4%} |",
             f"| **shipped path routes through restricted land** | "
             f"**{nd['path_uses_restricted_through']:,}** | "
             f"**{nd['path_uses_restricted_through'] / nd['reachable']:.4%}** |", "",
             "**Decisive — how much coverage has no lawful path at all.** The strict surface allows "
             "a restricted edge only as the first hop out of the origin. A restricted final hop "
             "into a destination's own parking is equally lawful and is *not* modelled, so lawful "
             "coverage is understated and these losses are an **upper bound**.", "",
             f"- reachable nodes with **no lawful path**: **{nd['no_lawful_path']:,}** "
             f"({nd['no_lawful_path'] / nd['reachable']:.4%})",
             f"- nodes that keep a path but get slower: {nd['strict_slower_by_more_than_1s']:,}, "
             f"median +{nd['strict_median_increase_s']:.1f} s, max "
             f"+{nd['strict_max_increase_s']:.1f} s", "",
             "As published cells, both policies through the production snap:", "",
             "| | shipped | strict | lost |", "|---|---|---|---|",
             f"| cells `OK` | {c['shipped_ok']:,} | {c['strict_ok']:,} | {c['lost']:,} |"]
    if has_b:
        lines.append(f"| buildings `OK` | {c['buildings_shipped_ok']:,} | "
                     f"{c['buildings_strict_ok']:,} | **{c['buildings_lost']:,}** "
                     f"({c['buildings_lost'] / c['buildings_total']:.4%}) |")
    lines += ["", "| threshold | cells shipped | cells strict | cells lost |"
                  + (" buildings lost |" if has_b else ""),
              "|---|---|---|---|" + ("---|" if has_b else "")]
    for k, v in out["thresholds"].items():
        row = f"| {k} | {v['shipped']:,} | {v['strict']:,} | {v['lost']:,} |"
        if has_b:
            row += f" {v['buildings_lost']:,} |"
        lines.append(row)
    lines += ["", f"- profile `{out['versions']['profile']}`, grid "
                  f"`{out['versions']['grid']}`"]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
