"""S2.3 rebuilt. What a restricted-road policy actually costs, with the policy modelled properly.

The first version (`s2_access_lawfulness_audit.py`) measured three things and concluded four, and
Codex pass 13 found four High defects in it. This is the replacement. The withdrawn claims and why
are in `docs/plans/2026-11-03-phase1-plan.md` under S2.3; the short version:

- **Edge position does not establish lawfulness** (H3). Exempting the journey's *first* restricted
  edge makes the verdict depend on how a driveway happens to be split into OSM ways. Split one
  driveway in two and the same journey changes answer.
- **The strict counterfactual was not the policy it claimed** (H1, H2, H4): the cell snap re-admitted
  restricted travel below the node level, the "unpenalised" branch still charged access penalties
  because both branches shared one `EdgeIndex`, and the restricted filter ran *after*
  `graph_to_cost_time_csr` had collapsed parallel edges — so wherever a restricted edge won that
  contest, removing it removed a lawful public alternative too.

## The policy, stated as a language

A lawful journey leaves a restricted road it is entitled to use, travels on open roads, and enters a
restricted road at the far end. Writing **R** for restricted and **O** for open, the lawful set is

        R* O* R*

— a restricted chain from the origin, an open middle, a restricted chain into the destination, any
of which may be empty. That is the formulation that fixes H3: a *chain* is invariant to how many
ways a driveway is split into, where a single-edge exemption is not.

`R* O* R*` is recognised by a three-state automaton, and running it over the graph is a shortest
path on the **product** of the graph and the automaton. Reading a journey backwards from its
destination gives `R* O* R*` again — the language is its own reverse — so arrival semantics use the
same machine with the two chains swapped:

| reverse state | meaning: the forward path from here to a destination is... | may traverse |
|---|---|---|
| 0 | all restricted — still inside the destination's own chain | R and O (O moves to 1) |
| 1 | `O* R*` — open middle, then the destination's chain | O, and R moves to 2 |
| 2 | `R* O* R*` — the origin's chain, then the rest | R only |

Costs are **times**, not penalised costs: this policy forbids rather than discourages, so there is
nothing to penalise, which is H2's fix. Edge classes come from the **multigraph before parallel-edge
collapse** — the minimum time among open parallels and among restricted parallels, kept separately —
which is H4's fix.

## Why this reports buildings against nodes, and not cells

H1 was a cell-snapping defect: a cell on an open partial edge inherited its node's
restricted-first-hop route, so the policy was lost below the node. Carrying three states through the
production snap is a real change to a tested module and the state rule is subtle — a cell reached
along an *open* partial edge may only continue in states 0 or 1, while one on a *restricted* partial
edge may continue in any state. Rather than ship a second cell-level number I am not sure of, this
reports the node level completely, and weights it by **buildings assigned to their nearest node**.

A building's own access leg is off-network — a driveway or path that need not be in the graph at all
— so all three states are admissible from it, and the subtlety that caused H1 does not arise. That
makes the building figure the one this spike actually supports. **A cell-level strict surface is not
built here, and S2.3 does not claim one.**

The policy itself, its automaton and the product-graph search live in
`locfinder/traveltime/policy.py` with `tests/test_policy.py` — every one of Codex's four
counterexamples is a test there, including the soundness invariant that a lawful journey can never
be faster than an unrestricted one. This script is the measurement over the real metro.

Run from v2/:  uv run python spikes/s2_access_lawfulness_v2.py grocery walk [--split-check]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import geopandas as gpd
import networkx as nx
import numpy as np
import osmnx as ox
import scipy.sparse as sp
from scipy.sparse.csgraph import dijkstra

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (ACCEPTED_PLACES, GRAPH_CACHE, GRID, METRO, METRO_DIR,  # noqa: E402
                     append_results, stamp)
from locfinder import profile  # noqa: E402
from locfinder.places.categories import select_overture  # noqa: E402
from locfinder.traveltime.access import RESTRICTED, classify_access  # noqa: E402
from locfinder.traveltime.arrival import arrival_seconds_two_weight  # noqa: E402
from locfinder.traveltime.components import largest_component  # noqa: E402
from locfinder.traveltime.csr import graph_to_cost_time_csr  # noqa: E402
from locfinder.traveltime.policy import (class_separated_times, lawful_arrival,  # noqa: E402
                                         unrestricted_arrival)
from locfinder.traveltime.speeds import add_travel_times, symmetrise  # noqa: E402

BUILDINGS = METRO_DIR / "overture_buildings_accepted.parquet"
POI_SNAP_MAX_M = 300.0
CUTOFF_MIN = 120.0
HORIZON_S = CUTOFF_MIN * 60.0
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("category")
    ap.add_argument("mode", choices=["walk", "bike", "drive"])
    ap.add_argument("--split-check", action="store_true",
                    help="also subdivide every restricted edge and re-run, to show the result is "
                         "invariant to how a driveway is split (pass-13 H3)")
    args = ap.parse_args()
    out: dict = {"metro": METRO.name, "category": args.category, "mode": args.mode}

    t = time.perf_counter()
    G = ox.load_graphml(GRAPH_CACHE)
    G = ox.project_graph(G, to_crs=GRID.crs)
    G = add_travel_times(G, mode=args.mode)
    if args.mode == "walk":
        G = symmetrise(G)
    G.remove_nodes_from([nd for nd, d in G.degree() if d == 0])
    G, comp = largest_component(G)
    print(f"graph prepared in {time.perf_counter() - t:.1f}s: {comp.summary}", flush=True)

    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
    n = cost_csr.shape[0]
    by_class = class_separated_times(G, index, mode=args.mode)
    out["edges"] = {
        "directed_pairs_total": int(cost_csr.nnz),
        "pairs_with_an_open_edge": int(by_class[False].nnz),
        "pairs_with_a_restricted_edge": int(by_class[True].nnz),
        "pairs_with_both": int((by_class[False].astype(bool).multiply(
            by_class[True].astype(bool))).nnz),
    }
    e = out["edges"]
    print(f"directed pairs {e['directed_pairs_total']:,}: open {e['pairs_with_an_open_edge']:,}, "
          f"restricted {e['pairs_with_a_restricted_edge']:,}, **both** {e['pairs_with_both']:,} — "
          f"the last number is what the CSR hides", flush=True)

    places = gpd.read_parquet(ACCEPTED_PLACES).to_crs(GRID.crs)
    sel = select_overture(places, args.category)
    cent = sel.geometry.centroid
    nodes, dists = ox.nearest_nodes(G, cent.x.to_numpy(), cent.y.to_numpy(), return_dist=True)
    dest_idx = sorted({index[nd] for nd, d in zip(nodes, dists) if d <= POI_SNAP_MAX_M})

    t = time.perf_counter()
    # Three node surfaces, and which is the BASELINE matters. `shipped` reports the time along the
    # *cost*-selected path, so it is an upper bound on the minimum time rather than the minimum
    # itself (pass-8 H2). Measuring the policy against it attributes that bound's effect to the
    # policy: on this graph it made 26,376 nodes look *faster* under the policy than without it,
    # which a subset of journeys can never be. The soundness assertion below caught that. So the
    # policy is measured time-minimum against time-minimum, and `shipped` is reported beside them
    # as what the product currently says.
    shipped = arrival_seconds_two_weight(cost_csr, time_csr, dest_idx=dest_idx)
    baseline = unrestricted_arrival(by_class, dest_idx=dest_idx)
    lawful, state = lawful_arrival(by_class, dest_idx=dest_idx)
    print(f"three searches in {time.perf_counter() - t:.1f}s", flush=True)

    reach = np.isfinite(baseline)
    has_lawful = np.isfinite(lawful)
    slower = reach & has_lawful & (lawful > baseline + 1.0)
    out["nodes"] = {
        "total": int(n),
        "reachable_without_the_policy": int(reach.sum()),
        "shipped_reachable": int(np.isfinite(shipped).sum()),
        "lawful_reachable": int(has_lawful.sum()),
        "no_lawful_journey": int((reach & ~has_lawful).sum()),
        "lawful_more_than_1s_slower": int(slower.sum()),
        "state_of_lawful_best": {int(k): int(c) for k, c in
                                 zip(*np.unique(state[has_lawful], return_counts=True))},
    }
    nd = out["nodes"]
    print(f"\nnodes: reachable without the policy {nd['reachable_without_the_policy']:,} "
          f"(shipped surface finite at {nd['shipped_reachable']:,}); **no lawful journey** "
          f"{nd['no_lawful_journey']:,} "
          f"({nd['no_lawful_journey'] / max(1, nd['reachable_without_the_policy']):.4%}); "
          f"lawful but >1 s slower {nd['lawful_more_than_1s_slower']:,}", flush=True)
    if slower.any():
        d = lawful[slower] - baseline[slower]
        out["nodes"]["slower_median_s"] = float(np.median(d))
        out["nodes"]["slower_p90_s"] = float(np.percentile(d, 90))
        out["nodes"]["slower_max_s"] = float(d.max())
        print(f"  where slower: median +{np.median(d):.1f} s, p90 +{np.percentile(d, 90):.1f} s, "
              f"max +{d.max():.1f} s", flush=True)
    # The lawful set is a subset of all journeys, so it can never be faster. Against the right
    # baseline this is a soundness check on the product construction.
    faster = reach & has_lawful & (lawful < baseline - 1e-6)
    out["nodes"]["lawful_faster_than_baseline_must_be_zero"] = int(faster.sum())
    if faster.any():
        raise SystemExit(f"{faster.sum():,} nodes have a lawful journey faster than the "
                         "unrestricted time minimum, which is impossible; the product graph is "
                         "wrong")
    print(f"  lawful faster than the baseline (must be 0): {int(faster.sum())}", flush=True)

    # ---- buildings, assigned to their nearest node ------------------------------------------
    t = time.perf_counter()
    b = gpd.read_parquet(BUILDINGS, columns=["geometry"]).to_crs(GRID.crs)
    bc = b.geometry.centroid
    bnodes, bdist = ox.nearest_nodes(G, bc.x.to_numpy(), bc.y.to_numpy(), return_dist=True)
    bidx = np.asarray([index[nd] for nd in bnodes], dtype=np.int64)
    print(f"\n{len(b):,} buildings assigned to nodes in {time.perf_counter() - t:.1f}s", flush=True)

    within = np.asarray(bdist) <= 200.0          # the layer's own access bound
    base_served = reach[bidx] & (baseline[bidx] <= HORIZON_S) & within
    lawful_served = has_lawful[bidx] & (lawful[bidx] <= HORIZON_S) & within
    out["buildings"] = {
        "total": int(len(b)),
        "within_access_bound_of_a_node": int(within.sum()),
        "served_without_the_policy": int(base_served.sum()),
        "served_under_the_policy": int(lawful_served.sum()),
        "lost_to_the_policy": int((base_served & ~lawful_served).sum()),
    }
    bs = out["buildings"]
    print(f"buildings served within {CUTOFF_MIN:.0f} min: without the policy "
          f"{bs['served_without_the_policy']:,} -> under it {bs['served_under_the_policy']:,}; "
          f"**the policy costs {bs['lost_to_the_policy']:,}** "
          f"({bs['lost_to_the_policy'] / max(1, bs['served_without_the_policy']):.4%})", flush=True)

    out["thresholds"] = {}
    for m in (10, 15, 25, 45):
        sec = m * 60.0
        pb = reach[bidx] & (baseline[bidx] <= sec) & within
        pl = has_lawful[bidx] & (lawful[bidx] <= sec) & within
        out["thresholds"][f"{m}min"] = {"baseline": int(pb.sum()), "lawful": int(pl.sum()),
                                        "lost": int((pb & ~pl).sum())}
    print("\nbuildings passing a threshold (no policy -> policy):", flush=True)
    for k, v in out["thresholds"].items():
        print(f"  {k:<6} {v['baseline']:>9,} -> {v['lawful']:>9,}  lost {v['lost']:,}", flush=True)

    # ---- H3: the result must not depend on how a driveway is split --------------------------
    if args.split_check:
        print("\nsubdividing every restricted edge and re-running...", flush=True)
        split = split_restricted_edges(G, args.mode)
        s_cost, s_time, s_index = graph_to_cost_time_csr(split)
        s_by_class = class_separated_times(split, s_index, mode=args.mode)
        # The SAME destination nodes, mapped through the new index. Re-snapping would let a grocery
        # attach to one of the midpoint nodes subdivision just created, changing the destination set
        # and confounding the check with a different question — which it did on the first run, as a
        # 223.95 s maximum difference that had nothing to do with the policy.
        node_by_idx = {i: nd for nd, i in index.items()}
        s_dest = sorted({s_index[node_by_idx[i]] for i in dest_idx})
        s_lawful, _ = lawful_arrival(s_by_class, dest_idx=s_dest)
        # compare on the ORIGINAL nodes, which survive subdivision
        common = np.asarray([s_index[nd] for nd in index], dtype=np.int64)
        orig = np.asarray([index[nd] for nd in index], dtype=np.int64)
        a, bb = lawful[orig], s_lawful[common]
        both = np.isfinite(a) & np.isfinite(bb)
        out["split_invariance"] = {
            "nodes_compared": int(len(common)),
            "finiteness_identical": bool(np.array_equal(np.isfinite(a), np.isfinite(bb))),
            "max_abs_diff_s": float(np.abs(a[both] - bb[both]).max()) if both.any() else 0.0,
        }
        si = out["split_invariance"]
        print(f"  split invariance: finiteness identical={si['finiteness_identical']}, "
              f"max abs diff {si['max_abs_diff_s']:.3e} s", flush=True)

    out["versions"] = {"profile": profile.profile_version(), "grid": profile.grid_version(GRID)}
    append_results("spotcheck-engines.md", render(out, args))
    print("\nappended to docs/experiments/spotcheck-engines.md", flush=True)
    print(json.dumps(out, indent=1, default=str), flush=True)


def split_restricted_edges(G: nx.MultiDiGraph, mode: str) -> nx.MultiDiGraph:
    """Subdivide every restricted edge at its midpoint, halving its time.

    The journey set is unchanged, so any measure of *journeys* must be unchanged too. The withdrawn
    first-edge rule was not: it exempted one edge, so splitting a driveway in two left the second
    half unexempted and the journey became "through traffic" (pass-13 H3).
    """
    H = G.copy()
    nxt = max(int(x) for x in H.nodes()) + 1 if H.nodes() else 0
    for u, v, k, data in list(G.edges(keys=True, data=True)):
        if classify_access(data, mode=mode) != RESTRICTED:
            continue
        mid = nxt
        nxt += 1
        H.add_node(mid, x=(H.nodes[u]["x"] + H.nodes[v]["x"]) / 2.0,
                   y=(H.nodes[u]["y"] + H.nodes[v]["y"]) / 2.0)
        half = {kk: vv for kk, vv in data.items()}
        half["travel_time"] = float(data["travel_time"]) / 2.0
        if "cost" in half:
            half["cost"] = float(data["cost"]) / 2.0
        H.remove_edge(u, v, k)
        H.add_edge(u, mid, **half)
        H.add_edge(mid, v, **{kk: vv for kk, vv in half.items()})
    return H


def render(out: dict, args) -> str:
    e, nd, bs = out["edges"], out["nodes"], out["buildings"]
    lines = [f"### S2.3 rebuilt — access policy cost: {args.category} / {args.mode} ({stamp()})", "",
             "Replaces the withdrawn audit (pass-13 H1-H4). The lawful journey set is **`R* O* R*`** "
             "— a restricted chain from the origin, an open middle, a restricted chain into the "
             "destination — recognised by a three-state automaton and solved as a shortest path on "
             "the graph x automaton product. A *chain* is invariant to how a driveway is split into "
             "ways, which is what the withdrawn first-edge rule was not. Costs are times, not "
             "penalised costs, because this policy forbids rather than discourages.", "",
             f"- directed pairs **{e['directed_pairs_total']:,}**: with an open edge "
             f"{e['pairs_with_an_open_edge']:,}, with a restricted edge "
             f"{e['pairs_with_a_restricted_edge']:,}, **with both {e['pairs_with_both']:,}**",
             "- that last number is the one the shipped CSR hides: it keeps the cost-minimal edge "
             "per pair, so deleting a restricted winner also deletes a lawful public alternative. "
             "Classes are separated on the **multigraph**, before any collapse.", "",
             "**The baseline is the unrestricted *time* minimum, not the shipped surface.** The "
             "shipped surface reports the time along the **cost**-selected path, so it is an upper "
             "bound on the minimum time (pass-8 H2); measuring the policy against it credited that "
             "bound to the policy and made 26,376 nodes look faster *with* the policy than without "
             "— which a subset of journeys cannot be. The soundness assertion caught it.", "",
             "| | nodes |", "|---|---|",
             f"| reachable with no policy (time minimum) | "
             f"{nd['reachable_without_the_policy']:,} |",
             f"| the shipped surface is finite at | {nd['shipped_reachable']:,} |",
             f"| **no journey in `R* O* R*`** | **{nd['no_lawful_journey']:,}** "
             f"({nd['no_lawful_journey'] / max(1, nd['reachable_without_the_policy']):.4%}) |",
             f"| lawful but **more than one second** slower | "
             f"{nd['lawful_more_than_1s_slower']:,} |"]
    if "slower_median_s" in nd:
        lines.append(f"| where slower: median / p90 / max | +{nd['slower_median_s']:.1f} s / "
                     f"+{nd['slower_p90_s']:.1f} s / +{nd['slower_max_s']:.1f} s |")
    lines += [f"| lawful faster than the baseline (must be 0) | "
              f"{nd['lawful_faster_than_baseline_must_be_zero']} |", "",
              "**Buildings, assigned to their nearest node.** Not cells: the withdrawn version lost "
              "the policy inside the cell snap (H1), and a building's own access leg is off-network "
              "so all three states are admissible from it, which is the case that does not have "
              "that subtlety. No cell-level strict surface is claimed here.", "",
              "| | buildings |", "|---|---|",
              f"| total | {bs['total']:,} |",
              f"| within the 200 m access bound of a node | {bs['within_access_bound_of_a_node']:,} |",
              f"| served within {int(CUTOFF_MIN)} min, no policy | "
              f"{bs['served_without_the_policy']:,} |",
              f"| served within {int(CUTOFF_MIN)} min, under the policy | "
              f"{bs['served_under_the_policy']:,} |",
              f"| **cost of the policy** | **{bs['lost_to_the_policy']:,}** "
              f"({bs['lost_to_the_policy'] / max(1, bs['served_without_the_policy']):.4%}) |", "",
              "| threshold | buildings, no policy | under the policy | lost |",
              "|---|---|---|---|"]
    for k, v in out["thresholds"].items():
        lines.append(f"| {k} | {v['baseline']:,} | {v['lawful']:,} | {v['lost']:,} |")
    if "split_invariance" in out:
        si = out["split_invariance"]
        lines += ["", f"**Split invariance** (pass-13 H3), subdividing every restricted edge at its "
                      f"midpoint: finiteness identical **{si['finiteness_identical']}**, maximum "
                      f"absolute difference **{si['max_abs_diff_s']:.3e} s** over "
                      f"{si['nodes_compared']:,} shared nodes. The journey set is unchanged by "
                      f"subdivision, so a measure of journeys must be unchanged; the withdrawn "
                      f"first-edge rule was not."]
    lines += ["", f"- profile `{out['versions']['profile']}`, grid `{out['versions']['grid']}`"]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
