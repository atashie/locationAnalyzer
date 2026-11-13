"""4b.0: can a label-setting search implement design §2.4's ranking? **No — and the gate stands.**

**§12 amendment item 6**, opened by Codex pass 37 F3: §2.4 selects objective 2 lexicographically —
the cost argmin, then among journeys of that exact cost the smallest travel time, then the
destination id, then the route identity.

**What this spike first concluded, and why it was wrong.** It reported that item 6 was too strong:
that the failure was specific to pruning on *cost alone*, and that keying one label per node on the
pair `(cost, time)` reproduced the normative answer. Codex pass 41 F1 refuted that with a
**journey-level** counterexample built from real `ToyGraph` objects, and F2 showed the spike's own
oracle shared an arithmetic defect with the search it was checking — so the two agreed while both
departed from §2.4. The recommendation is **withdrawn**. The gate is retained.

**The mechanism, which is stronger than item 6's original wording.** §2.4 ranks the **once-rounded
total of all formed terms** — one `fsum` over the whole journey, per item 6 of §2.4. So two prefixes
whose costs differ *strictly* can produce the **same** final binary64 cost once the entry, exit and
connector terms are added, and the travel-time discriminator then decides between them. A search
that prunes on any prefix comparison has already discarded one of them. That rules out:

* a cost-only label (the obvious case, and the one the first version of this spike measured);
* a `(cost, time)` pair label — the repair this spike proposed;
* **exact rational prefix accumulation**, which still prefers the strictly cheaper prefix.

The failure is therefore **not** about prefixes that tie. It is about the final rounding *creating*
a tie that no prefix order can anticipate. Pass 37's witness had exactly that feature — its
discarded prefix is strictly more expensive — and the first version of this spike misread it as a
tie-break problem.

**The witness, reproducible here by `--witness`.** Origin `(-1000, 1.26)` attaching halfway along
`(-2000,0)→(0,0)`; two paths merging at one node with prefix cost terms `(500, 500)` and
`(500, 500.0000000000001)`; destinations with unequal connectors. The exhaustive journey oracle gives
four journeys, the cost argmin is 2003, and the normative answer is **5 s**. A pair-label search
returns **1,004 s**. At a 600 s threshold that is **PASS against FAIL**, and the published encoding
turns 1 minute into 17.

**What survives, with its scope.** Under *exact-additive* arithmetic the pair label is sound: pass 41
ran 500 expanded multi-entry, three-destination graphs with unequal connectors and dyadic partial
terms and all 500 agreed, destination id included. So the obstruction is the **rounding of whole
totals**, not multiple destinations, unequal connectors or partial traversals. That is worth knowing
for the amendment option: a ranking defined on an exactly-additive primary order *would* be
implementable, and one defined on once-rounded totals is not.

**What this means for the plan's three options.** None of them is settled, and the spike's figures
do not price any of them:

* the **band** this script measures is "every exact cost-minimal label", which is *not* the
  neighbourhood the plan proposes (sized from a reachable suffix ulp, so that it retains a strictly
  more expensive prefix). The plan's version is untested; this one cannot cover the witness above.
  Pass 41 F5 also found this implementation **order-dependent**: reversing the input edge list turns
  2 s into 1,001 s on the same graph.
* the **amendment** needs more than the plan's "make whole-journey cost accumulation edge-by-edge":
  on the same witness even a left-accumulating oracle selects 2 s while the pair label selects
  1,001 s. An amendment has to settle the secondary time rule as well, or adopt a genuinely
  exact-additive primary order.
* **accept and measure** remains available, and nothing here measures the frequency on a real graph.

So 4b.0's outcome is that **the question is harder than the plan framed it**, the gate is retained,
and 4b must not assume any of the three repairs is free.

    python scripts/spike_search_semantics.py --witness          # the journey-level counterexample
    python scripts/spike_search_semantics.py --graphs 4000      # the graph-level measurements
"""
from __future__ import annotations

import argparse
import heapq
import itertools
import json
import math
import pathlib
import random
import sys
from collections import defaultdict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

Edge = tuple[int, int, float, float]        # (u, v, time, cost)


def random_graph(rng: random.Random, n: int, extra: int, weights: int) -> list[Edge]:
    """A directed graph with small integer weights, so exact cost and time ties are common."""
    edges: list[Edge] = []
    order = list(range(n))
    rng.shuffle(order)
    for a, b in itertools.pairwise(order):
        edges.append((a, b, float(rng.randrange(1, weights)), float(rng.randrange(1, weights))))
    for _ in range(extra):
        u, v = rng.sample(range(n), 2)
        edges.append((u, v, float(rng.randrange(1, weights)), float(rng.randrange(1, weights))))
    return edges


def adjacency(edges: list[Edge]) -> dict[int, list[Edge]]:
    out: dict[int, list[Edge]] = defaultdict(list)
    for e in edges:
        out[e[0]].append(e)
    return out


def all_simple(adj, start: int, goal: int, limit: int = 400_000):
    """Every simple path as `(cost, time, nodes, cost_terms, time_terms)`.

    **The totals are one `fsum` over all the path's terms**, which is §2.4's rule. Codex pass 41 F2:
    this used to accumulate `c + ec` edge by edge — the same rule the searches below use — so the
    oracle and the search agreed while both departed from the design. On costs `(2**53, 1, 1)`
    repeated addition gives `9007199254740992` and the whole-term sum gives `9007199254740994`, and
    the normative winner changes. An oracle that shares the defect it is checking is not an oracle.
    """
    out = []
    stack = [(start, (start,), (), ())]
    while stack:
        node, nodes, ct, tt = stack.pop()
        if node == goal:
            out.append((math.fsum(ct), math.fsum(tt), nodes, ct, tt))
            if len(out) > limit:
                raise RuntimeError("path explosion; use a smaller graph")
            continue
        for _, v, et, ec in adj.get(node, ()):
            if v not in nodes:
                stack.append((v, nodes + (v,), ct + (ec,), tt + (et,)))
    return out


def cost_only(adj, start: int, goal: int):
    """One label per node ordered by cost; an equal-cost arrival does not displace the incumbent.

    Reported for completeness. Pass 41 B: this is a correct conditional measurement of *this*
    implementation, and **not** the implementation item 6 indicts — pass 37's witness discards a
    prefix that is strictly more expensive, not one that ties.
    """
    best: dict[int, float] = {start: 0.0}
    label: dict[int, tuple[float, tuple[int, ...]]] = {start: (0.0, (start,))}
    heap = [(0.0, 0.0, start)]
    seen: set[int] = set()
    while heap:
        c, t, node = heapq.heappop(heap)
        if node in seen:
            continue
        seen.add(node)
        for _, v, et, ec in adj.get(node, ()):
            nc = c + ec
            if v not in best or nc < best[v]:
                best[v] = nc
                label[v] = (t + et, label[node][1] + (v,))
                heapq.heappush(heap, (nc, t + et, v))
    if goal not in best:
        return None
    t, nodes = label[goal]
    return (best[goal], t, nodes)


def pair_label(adj, start: int, goal: int):
    """One label per node ordered by the pair `(cost, time)`.

    **This is the repair this spike proposed and pass 41 F1 refuted.** It is sound for the
    exact-additive problem and unsound for §2.4's once-rounded totals, because a strictly more
    expensive prefix can round into the final cost tie and win it on time.
    """
    best: dict[int, tuple[float, float]] = {start: (0.0, 0.0)}
    nodes: dict[int, tuple[int, ...]] = {start: (start,)}
    heap = [(0.0, 0.0, start)]
    while heap:
        c, t, node = heapq.heappop(heap)
        if (c, t) != best.get(node):
            continue
        for _, v, et, ec in adj.get(node, ()):
            cand = (c + ec, t + et)
            if v not in best or cand < best[v]:
                best[v] = cand
                nodes[v] = nodes[node] + (v,)
                heapq.heappush(heap, (cand[0], cand[1], v))
    if goal not in best:
        return None
    return (best[goal][0], best[goal][1], nodes[goal])


def witness() -> dict:
    """The journey-level counterexample, on real `ToyGraph` objects. Pass 41 F1.

    Reproduced from our own script rather than only from the reviewer's, because this is the finding
    that retains the gate and it must not depend on their checkout.
    """
    from locfinder.measure import toy

    # Node coordinates must be consistent across edges: ToyGraph derives them from the geometry.
    xy = {-1: (-2000.0, 0.0), 0: (0.0, 0.0), 1: (100.0, 100.0),
          2: (100.0, -100.0), 3: (200.0, 0.0), 4: (2200.0, 0.0)}
    # The diamond. Prefix P via node 1 costs half + half. Prefix Q via node 2 costs
    # half + nextafter(nextafter(half)), so Q is STRICTLY costlier at the merge -- by half an ulp
    # of the final total -- and the whole-journey fsum then makes both journeys cost exactly 2003.
    # P is 1,000 s and Q is 1 s, so the rule selects Q and any prefix pruning discards it.
    half = 500.0
    costlier_half = math.nextafter(math.nextafter(half, math.inf), math.inf)
    rows = [(-1, 0, 2.0, 2.0),
            (0, 1, 500.0, half), (1, 3, 500.0, half),
            (0, 2, 0.5, half), (2, 3, 0.5, costlier_half),
            (3, 4, 2.0, 2000.0)]
    graph = toy.ToyGraph(tuple(toy.ToyEdge(u, v, (xy[u], xy[v]), time_s=tt, cost_base=cc,
                                           oneway=True)
                               for u, v, tt, cc in rows))
    origin = (-1000.0, 1.26)
    destinations = [(1200.0, 1.26), (2200.0, 0.0)]
    ids = ["z", "a"]
    js = toy.journeys(graph, origin, destinations, ids)
    if not js:
        return {"reproduced": False, "why": "the oracle enumerated no journeys"}
    cheapest = min(j.cost for j in js)
    at_min = [j for j in js if j.cost == cheapest]
    normative = min(at_min, key=lambda j: j.rank_key)
    worst_at_min = max(j.time_s for j in at_min)
    return {
        "reproduced": len({j.time_s for j in at_min}) > 1,
        "journeys": sorted((j.destination_id, j.cost, j.time_s) for j in js),
        "cost_argmin": cheapest,
        "normative_seconds": normative.time_s,
        "a_prefix_pruning_search_can_report": worst_at_min,
        "threshold_s": 600.0,
        "normative_verdict": "PASS" if normative.time_s <= 600.0 else "FAIL",
        "pruned_verdict": "PASS" if worst_at_min <= 600.0 else "FAIL",
        "encoded_minutes": [math.ceil(normative.time_s / 60.0), math.ceil(worst_at_min / 60.0)],
        "note": ("the two journeys at the cost argmin carry DIFFERENT times, and their prefixes "
                 "differ STRICTLY in cost - so a search that prunes on any prefix order discards "
                 "the one the rule selects. This is why item 6 is retained and restated rather "
                 "than narrowed."),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--graphs", type=int, default=4000)
    ap.add_argument("--seed", type=int, default=20261112)
    ap.add_argument("--witness", action="store_true", help="only the journey-level counterexample")
    ap.add_argument("--out", type=pathlib.Path, default=None)
    args = ap.parse_args(argv)

    w = witness()
    print("THE JOURNEY-LEVEL COUNTEREXAMPLE (pass 41 F1), which retains the gate:")
    for k in ("journeys", "cost_argmin", "normative_seconds", "a_prefix_pruning_search_can_report",
              "normative_verdict", "pruned_verdict", "encoded_minutes"):
        print(f"  {k:36s} {w.get(k)}")
    print(f"  reproduced: {w['reproduced']}")
    if args.witness:
        return 0 if w["reproduced"] else 1

    rng = random.Random(args.seed)
    n = 0
    co_wrong_cost = co_wrong_time = pl_wrong_cost = pl_wrong_time = 0
    counted_ties = distinct_route_ties = 0
    for _ in range(args.graphs):
        nodes = rng.choice([5, 6, 7])
        edges = random_graph(rng, nodes, rng.randrange(3, 9), rng.choice([3, 4, 6]))
        adj = adjacency(edges)
        start, goal = 0, nodes - 1
        paths = all_simple(adj, start, goal)
        if not paths:
            continue
        truth = min((c, t, nd) for c, t, nd, _, _ in paths)
        co, pl = cost_only(adj, start, goal), pair_label(adj, start, goal)
        if co is None or pl is None:
            continue
        n += 1
        best_pair = min((c, t) for c, t, _, _, _ in paths)
        tied = [nd for c, t, nd, _, _ in paths if (c, t) == best_pair]
        if len(tied) > 1:
            counted_ties += 1
            # Pass 41 F3: the generator admits parallel arcs and `all_simple` records only the node
            # sequence, so the same route was enumerated twice and counted as a tie it is not.
            if len(set(tied)) > 1:
                distinct_route_ties += 1
        if co[0] != truth[0]:
            co_wrong_cost += 1
        elif co[1] != truth[1]:
            co_wrong_time += 1
        if pl[0] != truth[0]:
            pl_wrong_cost += 1
        elif pl[1] != truth[1]:
            pl_wrong_time += 1

    report = {
        "conclusion": ("WITHDRAWN. The pair label is sound for the exact-additive problem and "
                       "unsound for section 2.4's once-rounded whole-journey totals; see the "
                       "witness above and Codex pass 41 F1. Item 6 is retained."),
        "witness": w,
        "graphs_compared": n,
        "seed": args.seed,
        "population": ("directed graphs of 5-7 nodes, a spanning path plus 3-8 random arcs, small "
                       "integer weights so exact ties are common. NOT an estimate for any real "
                       "graph, and the totals here are now one fsum over each path's terms"),
        "cost_only_wrong_cost": co_wrong_cost,
        "cost_only_right_cost_wrong_time": co_wrong_time,
        "pair_label_wrong_cost": pl_wrong_cost,
        "pair_label_right_cost_wrong_time": pl_wrong_time,
        "counted_cost_and_time_ties": counted_ties,
        "ties_with_more_than_one_DISTINCT_node_sequence": distinct_route_ties,
    }
    print(f"\ngraph-level measurements over {n} graphs, which measure the ADDITIVE problem and "
          f"therefore do not speak to the gate:")
    print(f"  cost-only label, right cost and wrong time:  {co_wrong_time}")
    print(f"  pair label, right cost and wrong time:       {pl_wrong_time}")
    print(f"  counted (cost, time) ties:                   {counted_ties}")
    print(f"  of those, with DISTINCT node sequences:      {distinct_route_ties}")
    print("\nThe first version of this script reported the counted ties as a route-identity "
          "ambiguity rate. Pass 41 F3: most of them are the same route enumerated twice, because "
          "the generator admits parallel arcs.")
    if args.out:
        args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
