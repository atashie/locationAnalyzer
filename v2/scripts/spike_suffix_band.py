"""4b.0, part two: **the plan's suffix-aware band, built and measured.**

The comparator plan's three options for §12 amendment item 6 were never priced. Its first option is
"retain a band — keep every label within a declared neighbourhood of the best, **sized from the
largest reachable suffix ulp**, and prove or measure what it misses". The first spike measured a
different band — every exact cost-minimal label — which cannot cover the item 6 witness at all, and
Codex pass 41 F5 found that implementation order-dependent as well. This script builds the band the
plan actually proposed, on the **journey** model rather than on a plain weighted digraph, and
reports what it costs and what it still misses.

**The rule, and why the width is what it is.** §2.4 ranks the once-rounded total of all the terms a
journey forms. Two prefixes at one node with exact costs `a < b` produce totals `rnd(a + S)` and
`rnd(b + S)` for a suffix of exact cost `S`. If those round to the same binary64 value `T` then both
lie in one rounding interval, whose width is at most `ulp(T)`. So

    b - a > ulp(U)  for an upper bound U on every total reachable through this node
    =>  the two can never share a final cost, whatever the suffix.

That is the band: at node `v`, retain a label whose exact prefix cost exceeds the node's exact
minimum by at most `W(v) = ulp(sigma(v) + Smax)`, and discard the rest. The width is sized from the
*suffix*, which is what makes it able to retain a **strictly more expensive** prefix — the thing
item 6 is about, and the thing the first spike's band could not do.

**What is measured here**

* the band selects item 6's own witness correctly — 5 s, where a pair-label search reports 1,004 s;
* the band agrees with the exhaustive journey oracle on every graph tried, in both a generic
  population and one with ulp-scale near-ties planted on purpose, which is the population where the
  band has to work;
* the band is **order-independent**, because its width comes from a precomputed exact minimum and
  its labels carry exact rational prefix sums, not left-accumulated floats;
* the price: labels retained per node, against the one label a scalar search keeps;
* **what it misses.** The band settles the *reported numbers* — cost and travel time. It does not
  settle **route identity**, §2.4's fourth key, and `--route-witness` is a graph where it names a
  different route from the oracle while reporting the same time. A second band on time, sized the
  same way, settles that one too, at a measured extra cost.
* the **precondition** the soundness argument needs: no cycle may cost less than the band width.
  A zero-cost cycle breaks it, and the check is cheap and is reported per graph.

Exact prefix sums are `fractions.Fraction`, so the comparisons that decide retention are exact, and
`float(Fraction)` of the whole journey's exact sum is the same binary64 as `math.fsum` over its
terms — both are the correctly rounded exact sum.
`tests/test_suffix_band.py::test_the_exact_sum_of_a_journeys_terms_is_the_same_binary64_as_fsum`
reconstructs every journey of the witness from its terms and checks that, rather than assuming it.
Pass 42 F5: an earlier draft of this docstring advertised a `--verify-totals` flag that did not
exist, left behind when the function it named was replaced by the membership check.

    python scripts/spike_suffix_band.py --witness
    python scripts/spike_suffix_band.py --route-witness
    python scripts/spike_suffix_band.py --graphs 300
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
from dataclasses import dataclass
from fractions import Fraction as F

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from locfinder.measure import toy                      # noqa: E402
from spike_search_semantics import witness_graph       # noqa: E402

Arc = tuple[int, F, F, tuple]           # (head, exact cost, exact time, directed identity)


# ----------------------------------------------------------------------------- the journey model


@dataclass(frozen=True)
class Terminal:
    """A start (an entry from the origin's attachment) or an end (an exit at a destination's)."""

    node: int
    cost: F
    time: F
    route: tuple
    dest: int = -1
    dest_id: str = ""


@dataclass(frozen=True)
class Candidate:
    cost: F
    time: F
    dest: int
    dest_id: str
    route: tuple

    def journey(self) -> toy.Journey:
        """`float()` of an exact sum is the correctly rounded exact sum, which is what `fsum` of the
        same terms returns. The exactness test reconstructs every journey and checks it.
        """
        return toy.Journey(time_s=float(self.time), cost=float(self.cost),
                           destination=self.dest, destination_id=self.dest_id, route=self.route)


def arcs_of(graph: toy.ToyGraph) -> dict[int, list[Arc]]:
    """Every permitted directed traversal, keyed by tail node. Index-free, like the identities."""
    out: dict[int, list[Arc]] = {}
    for e in graph.edges:
        for forward in (True, False):
            if not e.permits(forward=forward):
                continue
            a, b = (e.u, e.v) if forward else (e.v, e.u)
            out.setdefault(a, []).append(
                (b, F(e.total_cost), F(e.time_s), toy.directed_identity(e, forward=forward)))
    return out


def terminals(graph: toy.ToyGraph, origin_att: toy.Attachment, dest_points, dest_ids):
    """`(starts, ends, direct)` for one origin attachment.

    The origin connector is carried in the **starts** and the destination connector in the **ends**,
    so a label's exact prefix sum plus an end's exact sum is exactly the journey's term total. The
    grouping is exact arithmetic, so it does not change the number.
    """
    access_o = F(origin_att.residual_m / toy.ACCESS_SPEED_MPS)
    starts = [Terminal(en, access_o + F(ec), access_o + F(et), entry_route)
              for en, et, ec, entry_route in toy._entries(graph, origin_att)]
    ends: list[Terminal] = []
    direct: list[Candidate] = []
    for di, (dxy, did) in enumerate(zip(dest_points, dest_ids)):
        for da in toy.attachments(graph, dxy, cap_m=toy.POI_SNAP_MAX_M):
            access_d = F(da.residual_m / toy.ACCESS_SPEED_MPS)
            same_edge = toy._same_edge_direct(graph, origin_att, da)
            if same_edge is not None:
                e = graph.edges[origin_att.edge]
                direct.append(Candidate(
                    cost=access_o + access_d + F(same_edge[1]),
                    time=access_o + access_d + F(same_edge[0]),
                    dest=di, dest_id=did,
                    route=toy._partial_route(e, forward=da.fraction >= origin_att.fraction,
                                             span=abs(da.fraction - origin_att.fraction))))
            for xn, xt, xc, exit_route in toy._exits(graph, da):
                ends.append(Terminal(xn, access_d + F(xc), access_d + F(xt), exit_route, di, did))
    return starts, ends, direct


# ----------------------------------------------------------------------------- the band itself


def exact_min_costs(arcs, starts) -> dict[int, F]:
    """The exact minimum prefix cost at every reachable node. Dijkstra over `Fraction`.

    This is what makes the band order-independent: the width at a node is measured from a quantity
    that does not depend on the order labels happen to arrive in.
    """
    sigma: dict[int, F] = {}
    tiebreak = itertools.count()
    heap = [(s.cost, next(tiebreak), s.node) for s in starts]
    heapq.heapify(heap)
    while heap:
        c, _, node = heapq.heappop(heap)
        if node in sigma:
            continue
        sigma[node] = c
        for b, ec, _et, _id in arcs.get(node, ()):
            if b not in sigma:
                heapq.heappush(heap, (c + ec, next(tiebreak), b))
    return sigma


def _ceiling(values, extra: float) -> float:
    """A sound upper bound on any suffix, rounded **up** once so it cannot be an underestimate.

    A node-simple suffix can traverse each edge at most once in each direction, so twice the graph
    total bounds it, and the largest terminal term covers the exit and its connector.

    **An admissible graph can overflow this.** Pass 42 F2: `ToyGraph` admits a single edge of cost
    `7e307` and the oracle answers that query, while twice the graph total is infinite. A finite
    journey total does not imply a finite *bound*. The bound then saturates at the largest finite
    binary64, which makes the band as wide as binary64 allows — degenerate, and the right kind of
    degenerate, because a wider band retains more and never fewer.
    """
    try:
        total = math.fsum(list(values) + list(values) + [extra])
    except OverflowError:
        return sys.float_info.max
    if not math.isfinite(total) or total >= sys.float_info.max:
        return sys.float_info.max
    return math.nextafter(total, math.inf)


def _saturating(x: float) -> float:
    """Clamp to the largest finite binary64, so a bound is always a number."""
    if not math.isfinite(x) or x >= sys.float_info.max:
        return sys.float_info.max
    return x


def band_widths(sigma: dict[int, F], ceiling: float) -> dict[int, float]:
    """`W(v) = ulp(B)` for a finite `B` with `B >= sigma(v) + S` for every reachable suffix `S`.

    **Why `B` is enough, which is not the reason an earlier version gave.** Suppose a label `Q` at
    `v` with exact cost `sigma(v) + g` ends up at the final cost argmin `T` through some suffix `S`.
    The minimum label `P` takes the same suffix to `rnd(sigma(v) + S) <= T`, and it cannot be
    strictly below `T` without contradicting `T` being the argmin — so both round to `T`, both lie
    in one rounding interval, and `g <= ulp(T)`. And `sigma(v) + S <= B` with `B` a float gives
    `T = rnd(sigma(v) + S) <= B`, hence `ulp(T) <= ulp(B)`. The bound is on the **value they tie
    at**, never on `Q`'s own total.

    That matters because I got it wrong in the other direction first. Commit `e0c699c` doubled the
    width, reasoning that a retained label's own excess could push *its* total past `B` and across
    a binade. Pass 42 F2 pointed out that `Q`'s total is not what needs bounding, so the doubling
    was never necessary — and it was the direct cause of the overflow above, since `2 * 3e307` is
    infinite on a graph the oracle answers. Withdrawn, with the argument corrected rather than the
    conclusion patched.
    """
    out: dict[int, float] = {}
    for v, c in sigma.items():
        try:
            bound = float(c) + ceiling
        except OverflowError:
            bound = math.inf
        bound = _saturating(bound)
        if bound < sys.float_info.max:
            bound = _saturating(math.nextafter(bound, math.inf))
        out[v] = math.ulp(bound)
    return out


class LabelExplosion(RuntimeError):
    """The band retained more labels than the cap. A result, not a crash — it is the price."""


def band_labels(arcs, starts, sigma, widths, *, cap, tau=None, time_widths=None):
    """Every label the band retains, as `node -> {key: (exact time, route)}`.

    Pass one (`tau is None`) keys on the exact cost and keeps the smallest `(time, route)` for each:
    sound for the reported **numbers**, because once the exact cost is fixed the reported time is
    non-decreasing in the exact prefix time, so a larger prefix time can never produce a smaller
    reported one.

    Pass two keys on `(exact cost, exact time)` and additionally retains any label whose exact time
    is within the **time** band of pass one's minimum for that cost. That is what settles route
    identity, since two prefix times a fraction of an ulp apart can round to one reported time and
    then be separated by section 2.4's route key.

    **Label-setting, not label-correcting.** The queue is ordered by `(cost, time, route)`, which is
    non-decreasing along any path -- costs and times are non-negative and appending an identity
    lengthens a route without changing its prefix -- so a key is final when it is first popped. The
    first version of this used a DFS stack and re-expanded on every improvement; on 16 diamonds
    that cost 655,354 expansions for 442 retained labels. The retained set was identical. An
    exponential figure that an ordinary queue discipline removes is a property of the queue, not a
    price of the band, and reporting it as the band's cost would have been wrong.
    """
    best = {}
    heap = []
    counter = itertools.count()

    def offer(node, c, t, r):
        base = sigma.get(node)
        if base is None or c - base > F(widths[node]):
            return
        if tau is not None:
            floor = tau.get(node, {}).get(c)
            if floor is None or t - floor[0] > F(time_widths[node]):
                return
            key = (c, t)
        else:
            key = c
        slot = best.setdefault(node, {})
        current = slot.get(key)
        if current is None or (t, r) < current:
            slot[key] = (t, r)
            heapq.heappush(heap, (c, t, r, next(counter), node, key))

    for s in starts:
        offer(s.node, s.cost, s.time, s.route)
    pops = 0
    while heap:
        c, t, r, _, node, key = heapq.heappop(heap)
        if best[node].get(key) != (t, r):
            continue
        pops += 1
        if pops > cap:
            raise LabelExplosion(f"the band retained more than {cap} labels")
        for b, ec, et, ident in arcs.get(node, ()):
            offer(b, c + ec, t + et, r + (ident,))
    return best, pops


def scalar_labels(arcs, starts, *, cap: int = 2_000_000):
    """The implementation item 6 indicts: one label per node, ordered by the pair `(cost, time)`,
    accumulated edge by edge in binary64. Present for contrast, not as a candidate."""
    best: dict[int, tuple[float, float, tuple]] = {}
    heap: list = []
    tiebreak = itertools.count()
    for s in starts:
        cand = (float(s.cost), float(s.time), s.route)
        if s.node not in best or cand < best[s.node]:
            best[s.node] = cand
            heapq.heappush(heap, (cand[0], cand[1], next(tiebreak), s.node))
    pops = 0
    while heap:
        c, t, _, node = heapq.heappop(heap)
        if (c, t) != best[node][:2]:
            continue
        pops += 1
        if pops > cap:
            raise LabelExplosion("the scalar search did not settle")
        route = best[node][2]
        for b, ec, et, ident in arcs.get(node, ()):
            cand = (c + float(ec), t + float(et), route + (ident,))
            if b not in best or cand < best[b]:
                best[b] = cand
                heapq.heappush(heap, (cand[0], cand[1], next(tiebreak), b))
    return best, pops


# ----------------------------------------------------------------------------- the two searches


def precondition(graph: toy.ToyGraph, widths: dict) -> dict:
    """**No cycle may cost less than the band width** -- and what that buys is narrower than it
    sounds.

    The dominance that bounds the label count keeps one label per key at a node. Pass 41 F4's
    argument for why that is safe for the **route** key is that two node-simple prefixes from one
    root to one merge cannot be proper prefixes of each other, so their lexicographic order is
    settled at the first differing identity and survives any suffix. A cycle costing at most `W`
    breaks exactly that: the same node is reached again at the same cost, so one route **is** a
    proper prefix of the other, and the shorter one no longer dominates after a suffix is appended.
    A zero-cost edge that permits both directions is already such a cycle.

    **The reported numbers are not at risk, and this was measured rather than assumed.** A cycle of
    zero cost and zero time changes neither total; one of zero cost and positive time can only
    raise the time, so the minimum-time label at a given exact cost still dominates. Over 370
    random graphs each carrying a planted zero-cost two-way edge -- 363 of which the oracle could
    answer, and all 363 flagged by the check below -- the band disagreed **8 times and on the route
    sequence only**. Cost and travel time agreed exactly on every one, and every answer was a
    journey the model can form. `zero_cost_cycles()` is that run, and its numbers are in
    `docs/experiments/suffix-band.json`.

    The check below is **sufficient, not necessary**: it bounds every cycle by its cheapest edge.
    """
    widest = max(widths.values()) if widths else 0.0
    zero = sum(1 for e in graph.edges if e.total_cost == 0.0)
    positive = [e.total_cost for e in graph.edges if e.total_cost > 0.0]
    smallest = min(positive) if positive else math.inf
    return {"zero_cost_edges": zero, "smallest_positive_edge_cost_s": smallest,
            "widest_band_s": widest, "holds": zero == 0 and smallest > widest}


def feasible_cost_bound(graph: toy.ToyGraph, origin, dest_points, dest_ids) -> float:
    """The cost of a journey that **exists**, which is therefore an upper bound on the argmin.

    Pass 42 F1 refuted sizing the band from the query's travel-time threshold: cost is travel time
    plus access penalties, so a threshold on the reported time bounds neither. This is the tight
    bound that is sound. Every value it minimises over is a real journey's exact cost — the exact
    minimum prefix at a node, completed by one terminal — so the argmin cannot exceed it, and a
    width of `ulp` of it covers every tie at the argmin.

    Returns the graph-total fallback when no journey is reachable, so a caller always gets a bound.
    """
    origin = toy.require_query_point(origin, "the origin")
    dest_points = [toy.require_query_point(d, f"destination {i}")
                   for i, d in enumerate(dest_points)]
    arcs = arcs_of(graph)
    best = math.inf
    for oa in toy.attachments(graph, origin, cap_m=toy.MAX_ACCESS_M):
        starts, ends, direct = terminals(graph, oa, dest_points, dest_ids)
        for d in direct:
            best = min(best, float(d.cost))
        if not starts:
            continue
        sigma = exact_min_costs(arcs, starts)
        for end in ends:
            if end.node in sigma:
                best = min(best, float(sigma[end.node] + end.cost))
    if math.isfinite(best):
        return best
    return _ceiling([e.total_cost for e in graph.edges], 0.0)


def band_answer(graph: toy.ToyGraph, origin, dest_points, dest_ids, *,
                both_bands: bool = False, cap: int = 200_000,
                cost_ceiling: float = None) -> dict:
    """Section 2.4's answer as the band search computes it, with the price it paid.

    `cost_ceiling` is an upper bound on the **cost of the cost argmin**, which is what the width
    is taken from. The default is the graph's own total: sound, and very loose.

    **It is not a travel-time threshold.** Pass 42 F1: cost is travel time plus access penalties,
    so a 600-second threshold on the reported time bounds neither. Passing one selects 1,004 s on a
    witness whose normative answer is 5 s — PASS becomes FAIL, from a band sized by a number that
    was never a bound. `feasible_cost_bound()` is the tight bound that *is* valid, because it is
    the cost of a journey that exists.
    """
    origin = toy.require_query_point(origin, "the origin")
    dest_points = [toy.require_query_point(d, f"destination {i}")
                   for i, d in enumerate(dest_points)]
    arcs = arcs_of(graph)
    edge_costs = [e.total_cost for e in graph.edges]
    edge_times = [e.time_s for e in graph.edges]
    cands: list[Candidate] = []
    retained = pops = nodes_seen = 0
    most_at_one_node = 0
    all_widths: dict[int, float] = {}
    for oa in toy.attachments(graph, origin, cap_m=toy.MAX_ACCESS_M):
        starts, ends, direct = terminals(graph, oa, dest_points, dest_ids)
        cands.extend(direct)
        if not ends or not starts:
            continue
        sigma = exact_min_costs(arcs, starts)
        if cost_ceiling is None:
            widths = band_widths(sigma, _ceiling(edge_costs,
                                                 max(float(x.cost) for x in ends)))
        else:
            # A bound on the COST of the cost argmin, not on the suffix, so it is not added
            # to the node minimum.
            widths = {v: math.ulp(_saturating(cost_ceiling)) for v in sigma}
        tau, p1 = band_labels(arcs, starts, sigma, widths, cap=cap)
        pops += p1
        if both_bands:
            # One global time width, from an upper bound on any reachable total time. Sizing it
            # per node from one bucket's minimum would be an **under**estimate for the others, and
            # a band that is too narrow is the one failure mode a band must not have.
            upper = math.nextafter(_ceiling(edge_times, max(float(x.time) for x in ends))
                                   + max(float(s.time) for s in starts), math.inf)
            time_widths = {v: math.ulp(upper) for v in sigma}
            labels, p2 = band_labels(arcs, starts, sigma, widths, cap=cap,
                                     tau=tau, time_widths=time_widths)
            pops += p2
        else:
            labels = tau
        retained += sum(len(v) for v in labels.values())
        nodes_seen += len(labels)
        # Pass 42: the published "max" was the largest graph AVERAGE, not the largest count at any
        # one node. The witness averages 1.4 and has a node holding 2.
        most_at_one_node = max([most_at_one_node] + [len(v) for v in labels.values()])
        for v in labels:
            all_widths[v] = max(all_widths.get(v, 0.0), widths[v])
        for end in ends:
            for key, (t, r) in labels.get(end.node, {}).items():
                cost = key[0] if isinstance(key, tuple) else key
                cands.append(Candidate(cost=cost + end.cost, time=t + end.time,
                                       dest=end.dest, dest_id=end.dest_id,
                                       route=r + end.route))
    pre = precondition(graph, all_widths)
    widest = max(all_widths.values()) if all_widths else 0.0
    if not cands:
        return {"found": False, "labels_retained": retained, "pops": pops,
                "precondition": pre, "candidates": 0, "widest_band_s": widest,
                "labels_per_node": 0.0, "most_labels_at_one_node": most_at_one_node}
    js = [c.journey() for c in cands]
    cheapest = min(j.cost for j in js)
    at_min = [j for j in js if j.cost == cheapest]
    winner = min(at_min, key=lambda j: j.rank_key)
    return {"found": True, "cost": winner.cost, "time_s": winner.time_s,
            "destination_id": winner.destination_id, "route": winner.route,
            "candidates": len(cands), "labels_retained": retained,
            "nodes_with_labels": nodes_seen, "labels_per_node": retained / max(nodes_seen, 1),
            "most_labels_at_one_node": most_at_one_node,
            "pops": pops, "widest_band_s": widest,
            "journeys_at_the_cost_argmin": len(at_min), "precondition": pre}


def scalar_answer(graph: toy.ToyGraph, origin, dest_points, dest_ids) -> dict:
    """The same journey model searched by a `(cost, time)` pair label — item 6's target."""
    origin = toy.require_query_point(origin, "the origin")
    dest_points = [toy.require_query_point(d, f"destination {i}")
                   for i, d in enumerate(dest_points)]
    arcs = arcs_of(graph)
    best: list[tuple[float, float, str, tuple]] = []
    for oa in toy.attachments(graph, origin, cap_m=toy.MAX_ACCESS_M):
        starts, ends, direct = terminals(graph, oa, dest_points, dest_ids)
        for d in direct:
            best.append((float(d.cost), float(d.time), d.dest_id, d.route))
        labels, _ = scalar_labels(arcs, starts)
        for end in ends:
            lab = labels.get(end.node)
            if lab is None:
                continue
            best.append((lab[0] + float(end.cost), lab[1] + float(end.time),
                         end.dest_id, lab[2] + end.route))
    if not best:
        return {"found": False}
    cheapest = min(b[0] for b in best)
    at_min = [b for b in best if b[0] == cheapest]
    winner = min(at_min, key=lambda b: (b[1], b[2], b[3], b[0]))
    return {"found": True, "cost": winner[0], "time_s": winner[1],
            "destination_id": winner[2], "route": winner[3]}


def oracle_answer(graph: toy.ToyGraph, origin, dest_points, dest_ids) -> dict:
    """§2.4 by exhaustive enumeration — `toy.journeys`, which totals each journey with one `fsum`."""
    js = toy.journeys(graph, origin, dest_points, dest_ids)
    if not js:
        return {"found": False}
    cheapest = min(j.cost for j in js)
    at_min = [j for j in js if j.cost == cheapest]
    winner = min(at_min, key=lambda j: j.rank_key)
    return {"found": True, "cost": winner.cost, "time_s": winner.time_s,
            "destination_id": winner.destination_id, "route": winner.route,
            "journeys": len(js), "journeys_at_the_cost_argmin": len(at_min),
            # Every enumerated journey, so a band can be checked for **membership** and not only
            # for agreement on the winner. A search that invents a journey the model cannot form
            # would otherwise pass whenever its invention happened to lose.
            "all": {(j.cost, j.time_s, j.destination_id, j.route) for j in js}}


def agree(a: dict, b: dict, *, with_route: bool) -> bool:
    if a.get("found") != b.get("found"):
        return False
    if not a.get("found"):
        return True
    same = (a["cost"] == b["cost"] and a["time_s"] == b["time_s"]
            and a["destination_id"] == b["destination_id"])
    return same and (a["route"] == b["route"] if with_route else True)


def classify(got: dict, want: dict) -> set:
    """Which of section 2.4's quantities a search got wrong.

    Kept apart on purpose. "Wrong" is not one thing: a cost differing in its last ulp while the
    reported time is right is a different fact from a reported time differing by sixteen minutes,
    and one counter that merges them is the kind of summary sentence passes 38 to 41 kept finding.
    The reported deliverable is the **time**.
    """
    if got.get("found") != want.get("found"):
        return {"found"}
    if not want.get("found"):
        return set()
    out = set()
    if got["cost"] != want["cost"]:
        out.add("cost")
    if got["time_s"] != want["time_s"]:
        out.add("time")
    if got["destination_id"] != want["destination_id"]:
        out.add("destination")
    if got["route"] != want["route"]:
        out.add("route")
    return out


def is_a_real_journey(got: dict, want: dict) -> bool:
    """Membership, not agreement: is the returned answer a journey the model can actually form?

    Agreement on the winner alone would pass a search that invents a journey, whenever the
    invention happens to lose. This is the cheaper half of the check and it is the half that
    catches a label carrying a total its own terms do not produce.
    """
    if not got.get("found"):
        return True
    return (got["cost"], got["time_s"], got["destination_id"], got["route"]) in want["all"]


# ----------------------------------------------------------------------------- the populations


def route_witness():
    """A graph where the **single** cost band reports the right numbers and the wrong route.

    Two prefixes merge with the **same exact cost** and travel times one ulp apart. Their reported
    times round to one value, so §2.4 falls through to the route key — and the band's per-cost
    dominance has already dropped the label with the larger exact time, which is the one carrying
    the smaller route identity. Nothing about the reported seconds is wrong; the named route is.
    """
    xy = {-1: (-2000.0, 0.0), 0: (0.0, 0.0), 1: (100.0, 700.0),
          2: (100.0, -700.0), 3: (900.0, 0.0), 4: (2900.0, 0.0)}
    leg = 500.0
    slower = math.nextafter(leg, math.inf)
    # Equal costs on both arms, so the two arms land in one exact-cost bucket and the band's
    # per-cost dominance keeps the smaller exact time. The arm through node 1 is one ulp of 500
    # SLOWER and carries the smaller route identity, because its first directed identity is
    # (0, 1, ...) against (0, 2, ...). Both totals round to one reported time, so section 2.4 falls
    # through to the route key and selects the arm the band has just dropped.
    rows = [(-1, 0, 2.0, 2.0),
            (0, 1, leg, 500.0), (1, 3, slower, 500.0),
            (0, 2, leg, 500.0), (2, 3, leg, 500.0),
            (3, 4, 2.0, 2000.0)]
    graph = toy.ToyGraph(tuple(toy.ToyEdge(u, v, (xy[u], xy[v]), time_s=tt, cost_base=cc,
                                           oneway=True)
                               for u, v, tt, cc in rows))
    return graph, (-1000.0, 1.26), [(2900.0, 0.0)], ["a"]


def lattice(rng: random.Random, n: int):
    pts = [(150.0 * (i % 4), 150.0 * (i // 4)) for i in range(16)]
    rng.shuffle(pts)
    return {i: pts[i] for i in range(n)}


def generic_graph(rng: random.Random):
    """Realistic magnitudes and no planted structure: seconds drawn from a continuum, so exact
    prefix ties are the exception rather than the rule."""
    n = rng.choice([5, 6])
    xy = lattice(rng, n)
    rows = []
    order = list(range(n))
    rng.shuffle(order)
    for a, b in itertools.pairwise(order):
        rows.append((a, b))
    for _ in range(rng.randrange(2, 6)):
        u, v = rng.sample(range(n), 2)
        rows.append((u, v))
    edges = []
    for u, v in rows:
        t = rng.uniform(5.0, 120.0)
        penalty = rng.choice([0.0, 0.0, 0.0, 120.0])
        edges.append(toy.ToyEdge(u, v, (xy[u], xy[v]), time_s=t, cost_base=t, penalty=penalty,
                                 oneway=rng.random() < 0.3))
    return toy.ToyGraph(tuple(edges)), xy


def planted_graph(rng: random.Random):
    """A diamond whose two arms differ by a **few ulps of cost**, embedded with a long shared
    suffix so the whole-journey rounding can swallow the difference. This is the population the
    band exists for; a generic population does not exercise it at all."""
    xy = {-1: (-2000.0, 0.0), 0: (0.0, 0.0), 1: (200.0, 600.0),
          2: (200.0, -600.0), 3: (1000.0, 0.0), 4: (3000.0, 0.0)}
    leg = rng.choice([125.0, 250.0, 500.0, 1000.0])
    bumps = rng.randrange(0, 4)
    costlier = leg
    for _ in range(bumps):
        costlier = math.nextafter(costlier, math.inf)
    fast, slow = rng.uniform(0.25, 4.0), rng.uniform(400.0, 1200.0)
    tail = rng.choice([500.0, 1000.0, 2000.0, 4000.0])
    rows = [(-1, 0, 2.0, 2.0),
            (0, 1, slow / 2, leg), (1, 3, slow / 2, leg),
            (0, 2, fast / 2, leg), (2, 3, fast / 2, costlier),
            (3, 4, 2.0, tail)]
    graph = toy.ToyGraph(tuple(toy.ToyEdge(u, v, (xy[u], xy[v]), time_s=tt, cost_base=cc,
                                           oneway=True)
                               for u, v, tt, cc in rows))
    return graph, (-1000.0, 1.26), [(1600.0, 1.26), (3000.0, 0.0)], ["z", "a"]


def diamond_chain(k: int, *, leg: float = 1.0, tail: float = 4000.0):
    """`k` diamonds in series, each arm one ulp apart in cost. The band's retained set is bounded by
    the band width divided by the smallest gap, so this is where the price can be made to grow."""
    xy = {-1: (-2000.0, 0.0)}
    rows = [(-1, 0, 2.0, 2.0)]
    xy[0] = (0.0, 0.0)
    for i in range(k):
        a, up, down, b = 3 * i, 3 * i + 1, 3 * i + 2, 3 * i + 3
        xy[up] = (150.0 * (3 * i + 1), 200.0)
        xy[down] = (150.0 * (3 * i + 1), -200.0)
        xy[b] = (150.0 * (3 * i + 3), 0.0)
        bumped = math.nextafter(leg, math.inf)
        rows += [(a, up, 1.0, leg), (up, b, 1.0, leg),
                 (a, down, 2.0, leg), (down, b, 2.0, bumped)]
    last = 3 * k
    xy[last + 1] = (150.0 * (3 * k) + 2000.0, 0.0)
    rows.append((last, last + 1, 2.0, tail))
    graph = toy.ToyGraph(tuple(toy.ToyEdge(u, v, (xy[u], xy[v]), time_s=tt, cost_base=cc,
                                           oneway=True)
                               for u, v, tt, cc in rows))
    return graph, (-1000.0, 1.26), [xy[last + 1]], ["a"]


def equal_cost_chain(k: int, *, step: float = 2.0 ** -20, tail: float = 4000.0):
    """`k` diamonds whose arms cost **exactly** the same and whose times differ by a tiny amount
    that is different in every diamond. Pass 42 F3.

    This is the family the published chain concealed. There, each diamond's two arms differed in
    cost, so a merge held `k + 1` cost buckets each with one time, and the second band added
    nothing. Here every arm costs the same, so there is **one** cost bucket — and `2**k` distinct
    exact times inside it, all within the time band. Pass one keeps one label; pass two keeps
    `2**k`.
    """
    xy = {-1: (-2000.0, 0.0), 0: (0.0, 0.0)}
    rows = [(-1, 0, 2.0, 2.0)]
    for i in range(k):
        a, up, down, b = 3 * i, 3 * i + 1, 3 * i + 2, 3 * i + 3
        xy[up] = (150.0 * (3 * i + 1), 200.0)
        xy[down] = (150.0 * (3 * i + 1), -200.0)
        xy[b] = (150.0 * (3 * i + 3), 0.0)
        bumped = step + 2.0 ** (-45 - i)
        rows += [(a, up, step, 1.0), (up, b, step, 1.0),
                 (a, down, step, 1.0), (down, b, bumped, 1.0)]
    last = 3 * k
    xy[last + 1] = (150.0 * (3 * k) + 2000.0, 0.0)
    rows.append((last, last + 1, tail, 2.0))
    graph = toy.ToyGraph(tuple(toy.ToyEdge(u, v, (xy[u], xy[v]), time_s=tt, cost_base=cc,
                                           oneway=True)
                               for u, v, tt, cc in rows))
    return graph, (-1000.0, 1.26), [xy[last + 1]], ["a"]


def price_equal_cost_chain(ks, cap: int = 200_000) -> list:
    """What the route repair costs when every cost ties exactly. Pass 42 F3.

    The one-band figure stays flat. The two-band figure is `5 * 2**k - 3` while it fits under the
    cap, and then does not fit. **This is the finding that withdraws the recommendation to carry
    the second band by default.**
    """
    rows = []
    for k in ks:
        graph, origin, dests, ids = equal_cost_chain(k)
        one = band_answer(graph, origin, dests, ids, cap=cap)
        row = {"diamonds": k, "one_band_labels": one["labels_retained"],
               "one_band_most_at_one_node": one["most_labels_at_one_node"],
               "precondition_holds": one["precondition"]["holds"],
               "two_band_labels": None, "two_band_exploded": False}
        try:
            two = band_answer(graph, origin, dests, ids, both_bands=True, cap=cap)
            row["two_band_labels"] = two["labels_retained"]
            row["two_band_most_at_one_node"] = two["most_labels_at_one_node"]
        except LabelExplosion:
            row["two_band_exploded"] = True
        rows.append(row)
    return rows


def random_points(rng: random.Random, xy):
    xs = [p[0] for p in xy.values()]
    ys = [p[1] for p in xy.values()]
    def pt():
        return (rng.uniform(min(xs) - 80.0, max(xs) + 80.0),
                rng.uniform(min(ys) - 80.0, max(ys) + 80.0))
    return pt(), [pt(), pt()], ["a", "b"]


# ----------------------------------------------------------------------------- the measurements


def zero_cost_cycles(rng: random.Random, graphs: int = 400, cap: int = 100_000) -> dict:
    """The precondition, violated on purpose: one edge per graph forced to zero cost, two-way.

    Reported as three separate counters, because "disagreed" would hide which quantity moved.
    """
    compared = numbers = route = unformable = flagged = 0
    for _ in range(graphs):
        graph, pts = generic_graph(rng)
        edges = list(graph.edges)
        i = rng.randrange(len(edges))
        e = edges[i]
        # Pass 42: the first version always planted time 0.0 as well, so a whole class went
        # untested — a zero-COST edge with a small positive time, which the reviewer showed can
        # produce an unformable second-band winner. Half the draws now carry one.
        planted_time = 0.0 if rng.random() < 0.5 else rng.choice([2.0 ** -40, 1e-9, 1e-6])
        edges[i] = toy.ToyEdge(e.u, e.v, e.geometry, time_s=planted_time, cost_base=0.0,
                               oneway=False)
        graph = toy.ToyGraph(tuple(edges))
        origin, dests, ids = random_points(rng, pts)
        try:
            oracle = oracle_answer(graph, origin, dests, ids)
            if not oracle["found"]:
                continue
            band = band_answer(graph, origin, dests, ids, both_bands=True, cap=cap)
        except (LabelExplosion, ValueError, RuntimeError):
            continue
        compared += 1
        if not band["precondition"]["holds"]:
            flagged += 1
        wrong = classify(band, oracle)
        if wrong & {"cost", "time", "destination"}:
            numbers += 1
        if "route" in wrong:
            route += 1
        if not is_a_real_journey(band, oracle):
            unformable += 1
    return {"graphs_compared": compared, "flagged_by_the_precondition_check": flagged,
            "band_wrong_numbers": numbers, "band_wrong_route": route,
            "band_returned_an_unformable_journey": unformable,
            "half_the_planted_edges_carry_a_small_positive_time": True}


def width_sources() -> dict:
    """What the bound is worth, and which bounds are actually bounds.

    The width is `ulp(B)` for an upper bound `B` on the cost the argmin can tie at. Three
    candidates, and only two of them are sound:

    * **the graph's own total** — twice the sum of every edge cost. Sound anywhere, and loose by
      whatever ratio the graph bears to one journey.
    * **the cost of a journey that exists** — `feasible_cost_bound()`. The argmin cannot exceed a
      journey that was found, so this is sound and as tight as the rule permits.
    * **the query's travel-time threshold** — **not a bound at all**, and pass 42 F1's reproducer
      is below. Cost is travel time plus access penalties. It is included here so the artifact
      records the refutation rather than only the repair.

    The projection at the end is arithmetic, not a measurement, and is labelled as such.
    """
    graph, origin, dests, ids = witness_graph()
    oracle = oracle_answer(graph, origin, dests, ids)
    loose = band_answer(graph, origin, dests, ids, both_bands=True)
    feasible = feasible_cost_bound(graph, origin, dests, ids)
    tight = band_answer(graph, origin, dests, ids, both_bands=True, cost_ceiling=feasible)

    # F1's reproducer: costs scaled 16x, times untouched, a 600 s "threshold" used as a bound.
    import dataclasses
    scaled = toy.ToyGraph(tuple(dataclasses.replace(e, cost_base=16 * e.cost_base,
                                                    penalty=16 * e.penalty)
                                for e in graph.edges))
    scaled_oracle = oracle_answer(scaled, origin, dests, ids)
    by_threshold = band_answer(scaled, origin, dests, ids, both_bands=True, cost_ceiling=600.0)

    city_total, city_journey = 1.0e7, 2000.0
    return {
        "graph_total_bound_width_s": loose["widest_band_s"],
        "graph_total_bound_width_in_ulps_of_the_total":
            loose["widest_band_s"] / math.ulp(oracle["cost"]),
        "feasible_journey_bound": feasible,
        "feasible_bound_width_s": tight["widest_band_s"],
        "feasible_bound_width_in_ulps_of_the_total":
            tight["widest_band_s"] / math.ulp(oracle["cost"]),
        "both_sound_bounds_select_the_normative_answer":
            agree(loose, oracle, with_route=True) and agree(tight, oracle, with_route=True),
        "labels_retained_loose": loose["labels_retained"],
        "labels_retained_tight": tight["labels_retained"],
        "a_600s_time_threshold_used_as_a_cost_bound": {
            "oracle_cost": scaled_oracle["cost"], "oracle_seconds": scaled_oracle["time_s"],
            "band_seconds": by_threshold["time_s"],
            "verdict_normative": "PASS" if scaled_oracle["time_s"] <= 600 else "FAIL",
            "verdict_from_the_unsound_bound":
                "PASS" if by_threshold["time_s"] <= 600 else "FAIL"},
        "projection_is_arithmetic_not_a_measurement": True,
        "projected_ratio_on_a_graph_of_1e7_s_against_a_2000_s_journey":
            math.ulp(2 * city_total) / math.ulp(city_journey),
    }


def check_witness(both_bands: bool = False) -> dict:
    """Item 6's own witness. The band must report 5 s where the pair label reports 1,004 s."""
    graph, origin, dests, ids = witness_graph()
    oracle = oracle_answer(graph, origin, dests, ids)
    band = band_answer(graph, origin, dests, ids, both_bands=both_bands)
    scalar = scalar_answer(graph, origin, dests, ids)
    return {
        "oracle_seconds": oracle["time_s"], "band_seconds": band["time_s"],
        "scalar_seconds": scalar["time_s"], "cost_argmin": oracle["cost"],
        "band_agrees_on_the_numbers": agree(band, oracle, with_route=False),
        "band_agrees_on_the_route": agree(band, oracle, with_route=True),
        "scalar_agrees": agree(scalar, oracle, with_route=False),
        "band_labels_retained": band["labels_retained"],
        "labels_per_node": round(band["labels_per_node"], 3),
        "widest_band_s": band["widest_band_s"],
        "band_width_in_ulps_of_the_total": band["widest_band_s"] / math.ulp(oracle["cost"]),
        "precondition_holds": band["precondition"]["holds"],
        "verdict_at_600s": {"normative": "PASS" if oracle["time_s"] <= 600 else "FAIL",
                            "band": "PASS" if band["time_s"] <= 600 else "FAIL",
                            "scalar": "PASS" if scalar["time_s"] <= 600 else "FAIL"},
    }


def check_route_witness() -> dict:
    """What the single band misses: §2.4's route key."""
    graph, origin, dests, ids = route_witness()
    oracle = oracle_answer(graph, origin, dests, ids)
    one = band_answer(graph, origin, dests, ids, both_bands=False)
    two = band_answer(graph, origin, dests, ids, both_bands=True)
    return {
        "oracle_seconds": oracle["time_s"], "cost_argmin": oracle["cost"],
        "journeys_at_the_cost_argmin": oracle["journeys_at_the_cost_argmin"],
        "one_band_numbers_agree": agree(one, oracle, with_route=False),
        "one_band_route_agrees": agree(one, oracle, with_route=True),
        "two_band_route_agrees": agree(two, oracle, with_route=True),
        "one_band_labels": one["labels_retained"], "two_band_labels": two["labels_retained"],
        "demonstrated": (agree(one, oracle, with_route=False)
                         and not agree(one, oracle, with_route=True)
                         and agree(two, oracle, with_route=True)),
    }


def first_arrival_answer(graph, origin, dest_points, dest_ids) -> dict:
    """A deliberately order-dependent search: the **first** label to reach a node wins, ties
    unbroken. It exists to give the permutation check power. A check that reports "nothing moved"
    without ever having caught anything is not evidence that nothing can move.
    """
    origin = toy.require_query_point(origin, "the origin")
    dest_points = [toy.require_query_point(d, f"destination {i}")
                   for i, d in enumerate(dest_points)]
    arcs = arcs_of(graph)
    best = []
    for oa in toy.attachments(graph, origin, cap_m=toy.MAX_ACCESS_M):
        starts, ends, direct = terminals(graph, oa, dest_points, dest_ids)
        for d in direct:
            best.append((float(d.cost), float(d.time), d.dest_id, d.route))
        seen = {}
        queue = [(s.node, float(s.cost), float(s.time), s.route) for s in starts]
        while queue:
            node, c, tt, r = queue.pop(0)
            if node in seen:
                continue
            seen[node] = (c, tt, r)
            for b, ec, et, ident in arcs.get(node, ()):
                if b not in seen:
                    queue.append((b, c + float(ec), tt + float(et), r + (ident,)))
        for end in ends:
            lab = seen.get(end.node)
            if lab is not None:
                best.append((lab[0] + float(end.cost), lab[1] + float(end.time),
                             end.dest_id, lab[2] + end.route))
    if not best:
        return {"found": False}
    cheapest = min(b[0] for b in best)
    at_min = [b for b in best if b[0] == cheapest]
    winner = min(at_min, key=lambda b: (b[1], b[2], b[3], b[0]))
    return {"found": True, "cost": winner[0], "time_s": winner[1],
            "destination_id": winner[2], "route": winner[3]}


def order_independence(graph, origin, dests, ids, rng: random.Random, trials: int = 6) -> dict:
    """Permuting the edge list must not move the band's answer.

    Pass 41 F5 found the first spike's band order-dependent -- 2 s against 1,001 s on one graph --
    so this is checked, not asserted. `first_arrival` is the positive control: if it does not move
    either, the check is not discriminating and the band's zero means nothing.
    """
    def key(ans):
        return (ans.get("found"), ans.get("cost"), ans.get("time_s"),
                ans.get("destination_id"), ans.get("route"))
    band_keys, pair_keys, control_keys = set(), set(), set()
    edges = list(graph.edges)
    for _ in range(trials):
        rng.shuffle(edges)
        g = toy.ToyGraph(tuple(edges))
        band_keys.add(key(band_answer(g, origin, dests, ids, both_bands=True)))
        pair_keys.add(key(scalar_answer(g, origin, dests, ids)))
        control_keys.add(key(first_arrival_answer(g, origin, dests, ids)))
    return {"permutations": trials,
            "band_distinct_answers": len(band_keys),
            "pair_label_distinct_answers": len(pair_keys),
            "first_arrival_control_distinct_answers": len(control_keys)}


def sweep(rng: random.Random, graphs: int, *, population: str, cap: int,
          permutations: int = 3) -> dict:
    """Band against the exhaustive oracle over one population, with the one-band and two-band
    variants measured separately and the pair label alongside them."""
    tried = compared = 0
    counts = {"one_band": {}, "two_band": {}, "pair_label": {}}
    not_a_journey = {"one_band": 0, "two_band": 0, "pair_label": 0}
    explosions = precondition_failures = cost_ties = 0
    order_moved = {"two_band": 0, "pair_label": 0}
    labels1, labels2 = [], []
    for _ in range(graphs):
        tried += 1
        if population == "planted":
            graph, origin, dests, ids = planted_graph(rng)
        else:
            graph, xy = generic_graph(rng)
            origin, dests, ids = random_points(rng, xy)
        try:
            oracle = oracle_answer(graph, origin, dests, ids)
            if not oracle["found"]:
                continue
            one = band_answer(graph, origin, dests, ids, both_bands=False, cap=cap)
            two = band_answer(graph, origin, dests, ids, both_bands=True, cap=cap)
            pair = scalar_answer(graph, origin, dests, ids)
        except LabelExplosion:
            explosions += 1
            continue
        except (ValueError, RuntimeError):
            continue
        if not two["precondition"]["holds"]:
            precondition_failures += 1
        compared += 1
        labels1.append(one["labels_per_node"])
        labels2.append(two["labels_per_node"])
        if oracle["journeys_at_the_cost_argmin"] > 1:
            cost_ties += 1
        for name, ans in (("one_band", one), ("two_band", two), ("pair_label", pair)):
            for what in classify(ans, oracle):
                counts[name][what] = counts[name].get(what, 0) + 1
            if not is_a_real_journey(ans, oracle):
                not_a_journey[name] += 1
        edges = list(graph.edges)
        seen_band, seen_pair = set(), set()
        for _ in range(permutations):
            rng.shuffle(edges)
            g = toy.ToyGraph(tuple(edges))
            b = band_answer(g, origin, dests, ids, both_bands=True, cap=cap)
            s = scalar_answer(g, origin, dests, ids)
            seen_band.add((b.get("cost"), b.get("time_s"), b.get("route")))
            seen_pair.add((s.get("cost"), s.get("time_s"), s.get("route")))
        if len(seen_band) > 1:
            order_moved["two_band"] += 1
        if len(seen_pair) > 1:
            order_moved["pair_label"] += 1
    return {"population": population, "graphs_tried": tried, "graphs_compared": compared,
            "wrong_quantities": counts, "returned_a_journey_the_model_cannot_form": not_a_journey,
            "answers_that_moved_when_the_edge_list_was_permuted": order_moved,
            "permutations_per_graph": permutations,
            "graphs_with_more_than_one_journey_at_the_cost_argmin": cost_ties,
            "label_explosions": explosions, "precondition_failures": precondition_failures,
            "one_band_labels_per_node": {
                "mean": round(sum(labels1) / len(labels1), 4) if labels1 else None,
                "max": round(max(labels1), 4) if labels1 else None},
            "two_band_labels_per_node": {
                "mean": round(sum(labels2) / len(labels2), 4) if labels2 else None,
                "max": round(max(labels2), 4) if labels2 else None}}


def price_chain(ks) -> list:
    """The adversarial price: `k` diamonds, each arm one ulp of cost apart.

    What the band retains at a node is bounded by `W / g` -- the band width over the smallest
    non-zero gap between distinct prefix costs. That bound is **data-dependent and not small**:
    with 1-second edges inside a 4,000-second journey the width is thousands of ulps of an edge, so
    the counts below are small because this family supplies only `k` distinct prefix costs, not
    because the band is intrinsically cheap. `capacity` is that bound, in ulps of a 1-second edge.
    """
    rows = []
    for k in ks:
        graph, origin, dests, ids = diamond_chain(k)
        oracle = oracle_answer(graph, origin, dests, ids)
        band = band_answer(graph, origin, dests, ids, both_bands=True, cap=400_000)
        rows.append({"diamonds": k, "oracle_journeys": oracle["journeys"],
                     "band_labels": band["labels_retained"],
                     "labels_per_node": round(band["labels_per_node"], 3),
                     "pops": band["pops"],
                     "agrees": agree(band, oracle, with_route=True),
                     "capacity": round(band["widest_band_s"] / math.ulp(1.0))})
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--graphs", type=int, default=200)
    ap.add_argument("--seed", type=int, default=20261113)
    ap.add_argument("--cap", type=int, default=200_000)
    ap.add_argument("--witness", action="store_true")
    ap.add_argument("--route-witness", action="store_true")
    ap.add_argument("--out", type=pathlib.Path, default=None)
    args = ap.parse_args(argv)

    w = check_witness()
    print("ITEM 6'S WITNESS, against the band the plan proposed:")
    for k, v in w.items():
        print(f"  {k:36s} {v}")
    if args.witness:
        return 0 if w["band_agrees_on_the_numbers"] and not w["scalar_agrees"] else 1

    ws = width_sources()
    print("\nWHAT THE SUFFIX BOUND IS WORTH:")
    for k, v in ws.items():
        print(f"  {k:62s} {v}")

    rw = check_route_witness()
    print("\nWHAT THE SINGLE BAND MISSES -- section 2.4's route key:")
    for k, v in rw.items():
        print(f"  {k:36s} {v}")
    if args.route_witness:
        return 0 if rw["demonstrated"] else 1

    rng = random.Random(args.seed)
    generic = sweep(rng, args.graphs, population="generic", cap=args.cap)
    planted = sweep(rng, args.graphs, population="planted", cap=args.cap)
    print("\nAGAINST THE EXHAUSTIVE ORACLE, by quantity (counts of graphs, not of journeys):")
    for s in (generic, planted):
        print(f"  {s['population']} -- {s['graphs_compared']} compared, "
              f"{s['graphs_with_more_than_one_journey_at_the_cost_argmin']} with a cost tie")
        for name in ("one_band", "two_band", "pair_label"):
            wrong = s["wrong_quantities"][name]
            print(f"      {name:11s} wrong: {wrong if wrong else 'nothing'}"
                  f"   not a formable journey: "
                  f"{s['returned_a_journey_the_model_cannot_form'][name]}"
                  f"   moved on permutation: "
                  f"{s['answers_that_moved_when_the_edge_list_was_permuted'].get(name, 'n/a')}")
        print(f"      labels per node: one band "
              f"{s['one_band_labels_per_node']['mean']} mean / "
              f"{s['one_band_labels_per_node']['max']} max, two bands "
              f"{s['two_band_labels_per_node']['mean']} mean / "
              f"{s['two_band_labels_per_node']['max']} max")

    zc = zero_cost_cycles(random.Random(args.seed + 2))
    print("\nTHE PRECONDITION, VIOLATED ON PURPOSE -- one zero-cost two-way edge per graph:")
    for k, v in zc.items():
        print(f"  {k:42s} {v}")

    gw, go, gd, gi = witness_graph()
    orders = order_independence(gw, go, gd, gi, random.Random(args.seed + 1))
    print(f"\nORDER INDEPENDENCE on the witness graph, 6 permutations: "
          f"band distinct answers {orders['band_distinct_answers']}, "
          f"pair label {orders['pair_label_distinct_answers']}, "
          f"first-arrival control "
          f"{orders['first_arrival_control_distinct_answers']}")

    equal = price_equal_cost_chain([2, 4, 6, 8, 10, 12])
    print("\nTHE ROUTE REPAIR'S PRICE WHEN EVERY COST TIES EXACTLY (pass 42 F3):")
    for row in equal:
        two = "EXPLODED" if row["two_band_exploded"] else row["two_band_labels"]
        print(f"  k={row['diamonds']:3d}  one band {row['one_band_labels']:5d}  "
              f"two bands {two}")

    chain = price_chain([1, 2, 4, 8, 12, 16])
    print("\nTHE ADVERSARIAL PRICE -- k diamonds, arms one ulp of cost apart:")
    for row in chain:
        print(f"  k={row['diamonds']:3d}  band labels {row['band_labels']:6d}  "
              f"labels/node {row['labels_per_node']:8.3f}  pops {row['pops']:7d}  "
              f"capacity {row['capacity']:6d}  agrees {row['agrees']}")

    report = {
        "what_this_is": ("the comparator plan's FIRST option for section 12 amendment item 6 -- a "
                         "band of labels whose width is sized from the largest reachable suffix "
                         "ulp -- built on the JOURNEY model and measured"),
        "witness": w,
        "width_sources": ws,
        "route_key": rw,
        "sweeps": [generic, planted],
        "order_independence": orders,
        "precondition_violated": zc,
        "adversarial_price": chain,
        "route_repair_price_on_exact_cost_ties": equal,
        "soundness_argument": ("two prefixes with exact costs a < b round to one total only if "
                               "b - a <= ulp(T); ulp is non-decreasing in magnitude, so a width of "
                               "ulp(U) for an upper bound U on every reachable total retains every "
                               "prefix that could rejoin the final cost tie, including prefixes "
                               "that are STRICTLY more expensive, which is what item 6 is about"),
        "precondition": ("no cycle may cost less than the band width. Checked per graph by the "
                         "sufficient test that there is no zero-cost edge and the smallest "
                         "positive edge cost exceeds the width. What a violation costs was "
                         "measured, not assumed: the ROUTE SEQUENCE only, never the reported cost "
                         "or time, over 400 graphs with a zero-cost two-way edge planted"),
        "what_it_does_not_settle": ("route identity. The per-cost dominance that bounds the label "
                                    "count drops the label with the larger exact prefix time, and "
                                    "two prefix times under an ulp apart can round to one reported "
                                    "time, after which section 2.4 decides on the route. A second "
                                    "band on time settles it on the hand-built witness and is NOT "
                                    "affordable in general: on k diamonds of equal cost and "
                                    "distinct times it retains 5 * 2**k - 3 labels, 20,477 at "
                                    "k = 12, where one band retains 38 (pass 42 F3)"),
        "withdrawn_after_pass_42": [
            "sizing the width from the query's travel-time threshold -- it is not a bound on cost",
            "the binade of headroom -- never necessary, and it was what overflowed",
            "exact cost ties cost the band nothing -- true for one band, false for two",
            "W / g bounds the retained count -- it is floor(W/g)+1 for one band, and for two "
            "bands the distinct times inside a cost bucket dominate it",
            "the band is not a prefix-pruning search -- it is one, with a suffix-aware threshold",
            "the reported max was a maximum of graph AVERAGES, not labels at one node",
        ],
    }
    if args.out:
        args.out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
