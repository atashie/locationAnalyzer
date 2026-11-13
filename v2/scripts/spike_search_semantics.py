"""4b.0: can a label-setting search implement design §2.4's ranking? Measured, not argued.

**§12 amendment item 6**, opened by Codex pass 37 F3: §2.4 selects objective 2 lexicographically —
the cost argmin, then among journeys of that exact cost the smallest travel time, then the
destination id, then the route identity — and a label-setting search pruning on **cost alone** can
discard a prefix that would rejoin the final cost tie and win it on time. The item concluded that
the rule "is not a property any single-scalar shortest-path implementation has".

**That conclusion is too strong, and this spike is what showed it.** The repair is neither of the
three the step 4 plan offered. It is to key the label on the **pair** `(cost, time)` instead of on
cost alone: still one label per node, still Dijkstra-shaped, and free.

Item 6 is a question about the **search**, so the experiment runs on a plain weighted graph. The
geometry, attachment and connector layers contribute terms to a journey's totals and nothing to how
a search prunes; `toy.py`'s own enumeration is exhaustive over simple paths, so "the truth" here is
what it computes, on graphs small enough to enumerate exhaustively.

Four searches over the same graphs:

* **exhaustive** — every simple path, ordered by `(cost, time)`. The normative answer.
* **cost-only scalar** — Dijkstra on cost, one label per node, an equal-cost arrival dropped. The
  implementation item 6 indicts.
* **lexicographic scalar** — Dijkstra with one label per node ordered by `(cost, time)`.
* **band** — every *cost-minimal* label per node retained, time deciding at the end. The plan's
  first repair, measured so it can be priced rather than preferred.

**Why the lexicographic label works**, stated as the reason and not as a proof: costs and times are
both non-negative, and removing a cycle from a walk removes non-negative cost and non-negative time.
So if some prefix to a node beat the retained label lexicographically, that prefix plus the retained
suffix would contain a *simple* path at least as good as the optimum — contradicting optimality. The
evidence for the claim is the measurement below; this paragraph says why to expect it.

**The residual, which no single-label search closes.** The route-identity key is compared
element-wise over sequences, and that is **not** prefix-decomposable: two prefixes of different
lengths can be ordered either way depending on how they are completed. So where two complete
journeys tie on cost *and* time, the recorded route identity depends on the search's tie-break. That
is a **provenance** ambiguity against §12's manifest requirement, not a wrong reported number, and
its frequency is measured here too.
"""
from __future__ import annotations

import argparse
import heapq
import itertools
import json
import pathlib
import random
import sys
from collections import defaultdict

Edge = tuple[int, int, float, float]        # (u, v, time, cost)


def random_graph(rng: random.Random, n: int, extra: int, weights: int) -> list[Edge]:
    """A directed graph with small integer weights, so exact cost and time ties are common.

    A spanning path over a shuffled node order guarantees a route exists; `extra` random arcs supply
    the alternatives that ties need. Small integer weights are deliberate: the rule under test only
    fires on an **exact** tie, so a population of real-valued weights would almost never exercise it.
    """
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
    """Every simple path as `(cost, time, path)`. The oracle, by exhaustion."""
    out = []
    stack = [(start, (start,), 0.0, 0.0)]
    while stack:
        node, path, t, c = stack.pop()
        if node == goal:
            out.append((c, t, path))
            if len(out) > limit:
                raise RuntimeError("path explosion; use a smaller graph")
            continue
        for _, v, et, ec in adj.get(node, ()):
            if v not in path:
                stack.append((v, path + (v,), t + et, c + ec))
    return out


def cost_only(adj, start: int, goal: int):
    """One label per node, ordered by cost. An equal-cost arrival does not displace the incumbent.

    This is the ordinary implementation and the subject of item 6: when two prefixes reach a node at
    the same cost it keeps whichever arrived first, which is insertion order and carries no
    information about the travel time the rule will later use to break the tie.
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
    t, path = label[goal]
    return (best[goal], t, path)


def lexicographic(adj, start: int, goal: int):
    """One label per node, ordered by the PAIR `(cost, time)`. The repair this spike recommends."""
    best: dict[int, tuple[float, float]] = {start: (0.0, 0.0)}
    path: dict[int, tuple[int, ...]] = {start: (start,)}
    heap = [(0.0, 0.0, start)]
    while heap:
        c, t, node = heapq.heappop(heap)
        if (c, t) != best.get(node):
            continue
        for _, v, et, ec in adj.get(node, ()):
            cand = (c + ec, t + et)
            if v not in best or cand < best[v]:
                best[v] = cand
                path[v] = path[node] + (v,)
                heapq.heappush(heap, (cand[0], cand[1], v))
    if goal not in best:
        return None
    return (best[goal][0], best[goal][1], path[goal])


def band(adj, start: int, goal: int, cap: int = 20_000):
    """Every cost-minimal label per node; the time decides at the end. Returns the widest set too."""
    labels: dict[int, list[tuple[float, float, tuple[int, ...]]]] = {start: [(0.0, 0.0, (start,))]}
    queue = [(0.0, 0.0, start, (start,))]
    widest = 1
    while queue:
        c, t, node, p = queue.pop()
        for _, v, et, ec in adj.get(node, ()):
            if v in p:
                continue
            nc, nt, np_ = c + ec, t + et, p + (v,)
            have = labels.get(v, [])
            if have and nc > have[0][0]:
                continue
            if have and nc < have[0][0]:
                labels[v] = [(nc, nt, np_)]
            else:
                if any(nt == ht and np_ == hp for _, ht, hp in have):
                    continue
                labels[v] = have + [(nc, nt, np_)]
            widest = max(widest, len(labels[v]))
            if len(labels[v]) > cap:
                raise RuntimeError("label explosion")
            queue.append((nc, nt, v, np_))
    if goal not in labels:
        return (None, widest)
    return (min(labels[goal]), widest)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--graphs", type=int, default=4000)
    ap.add_argument("--seed", type=int, default=20261112)
    ap.add_argument("--out", type=pathlib.Path, default=None)
    args = ap.parse_args(argv)

    rng = random.Random(args.seed)
    n = 0
    cost_only_wrong_cost = cost_only_wrong_time = 0
    lex_wrong_cost = lex_wrong_time = 0
    band_wrong_cost = band_wrong_time = 0
    route_ambiguous = 0
    widest_band = widest_tie = 0
    examples: list[dict] = []

    for _ in range(args.graphs):
        nodes = rng.choice([5, 6, 7])
        edges = random_graph(rng, nodes, rng.randrange(3, 9), rng.choice([3, 4, 6]))
        adj = adjacency(edges)
        start, goal = 0, nodes - 1
        paths = all_simple(adj, start, goal)
        if not paths:
            continue
        truth = min(paths)
        co, lx = cost_only(adj, start, goal), lexicographic(adj, start, goal)
        bd, w = band(adj, start, goal)
        if co is None or lx is None or bd is None:
            continue
        n += 1
        widest_band = max(widest_band, w)

        # the residual: paths tying on BOTH cost and time, which only the route key separates
        best_pair = min((c, t) for c, t, _ in paths)
        tied = [p for c, t, p in paths if (c, t) == best_pair]
        if len(tied) > 1:
            route_ambiguous += 1
            widest_tie = max(widest_tie, len(tied))

        if co[0] != truth[0]:
            cost_only_wrong_cost += 1
        elif co[1] != truth[1]:
            cost_only_wrong_time += 1
            if len(examples) < 6:
                examples.append({"edges": edges, "truth_cost": truth[0], "truth_time": truth[1],
                                 "cost_only_time": co[1], "truth_path": list(truth[2]),
                                 "cost_only_path": list(co[2])})
        if lx[0] != truth[0]:
            lex_wrong_cost += 1
        elif lx[1] != truth[1]:
            lex_wrong_time += 1
        if bd[0] != truth[0]:
            band_wrong_cost += 1
        elif bd[1] != truth[1]:
            band_wrong_time += 1

    report = {
        "graphs_compared": n,
        "seed": args.seed,
        "population": ("directed graphs of 5-7 nodes, a spanning path plus 3-8 random arcs, "
                       "integer time and cost weights from a small range so EXACT ties are common "
                       "- the rule under test only fires on an exact tie"),
        "cost_only_wrong_cost": cost_only_wrong_cost,
        "cost_only_right_cost_wrong_time": cost_only_wrong_time,
        "lexicographic_wrong_cost": lex_wrong_cost,
        "lexicographic_right_cost_wrong_time": lex_wrong_time,
        "band_wrong_cost": band_wrong_cost,
        "band_right_cost_wrong_time": band_wrong_time,
        "widest_cost_minimal_label_set": widest_band,
        "graphs_where_only_the_route_key_separates_the_winners": route_ambiguous,
        "most_paths_tied_on_cost_and_time": widest_tie,
        "examples_of_the_cost_only_failure": examples,
    }
    print(json.dumps({k: v for k, v in report.items()
                      if k != "examples_of_the_cost_only_failure"}, indent=2))
    if n:
        print(f"\ncost-only scalar reports the wrong TIME on a correct cost: "
              f"{cost_only_wrong_time} of {n} ({100 * cost_only_wrong_time / n:.2f}%)")
        print(f"lexicographic (cost, time) label, one per node:             "
              f"{lex_wrong_time} wrong time, {lex_wrong_cost} wrong cost")
        print(f"band of all cost-minimal labels:                           "
              f"{band_wrong_time} wrong time, up to {widest_band} labels at one node")
        print(f"\nresidual no single-label search closes: {route_ambiguous} of {n} "
              f"({100 * route_ambiguous / n:.2f}%) have two or more winners tied on BOTH cost and "
              f"time, so the recorded ROUTE IDENTITY depends on the tie-break. Up to "
              f"{widest_tie} such paths in one graph.")
    if args.out:
        args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
