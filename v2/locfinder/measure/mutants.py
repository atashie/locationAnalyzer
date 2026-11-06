"""Every wrong implementation a review has built, kept executable.

**Why these live in the package rather than in a test.** A guard is only a guard if something checks
that it still guards. `feedback-benchmark-over-point-fixes` records the decisive experiment for this —
*"verify the guard by reverting the fix"* — and pass 14 showed that a benchmark I had claimed was the
guard turned none of its assertions red when the historical fixes were reverted. So each mutant here
is installed and the suites are run against it, and `test_mutants.py` asserts that **every mutant is
caught by at least one layer**.

That check immediately earned its place. Run against the two suites it showed:

| mutant | invariants | conformance |
|---|---|---|
| pass-20 F1 connector-free cost | passes | **caught** |
| pass-20 F5 strict cap | passes | **caught** |
| pass-20 F4 identity-keyed dedup | **caught** | **caught** |
| pass-21 F1 rounded occurrence bucket | **caught** | passes |
| pass-21 F4 dropped zero-span branch | **caught** | passes |
| pass-21 F5 route without partials | **caught** | passes |
| pass-21 F6 rank without cost | **caught** | passes |
| pass-21 F7 bit-complemented orientation | **caught** | passes |

The two layers are **complementary and neither subsumes the other**: five mutants escape the corpus
and two escape the invariants, and every one is caught by the other. The corpus catches boundary and
value defects; the invariants catch domain and representation defects. A uniformly tightened cap and
a uniformly connector-free cost both preserve every *relative* property — scaling, translating,
permuting and re-expressing all still agree, because both sides are equally wrong — so only an
exact-boundary or exact-value case sees them. Conversely five of the pass-21 mutants escape the
corpus because no named case exercised their shape, which is the whole reason this layer exists.

**Getting this table right required fixing the harness twice.** The orientation mutant read as
uncaught by everything until `invariants.py` stopped importing `directed_identity` by name — a
patched module global cannot reach a binding someone already copied. And it stayed uncaught until the
scenario domain gained an input whose *selected route* traverses a palindromic edge backwards, since
the bit flip and the renormalisation agree on every other geometry.

Three of these were, at the time the mutation check first ran, defects I had **fixed with no guard at
all**: the orientation bit, the zero-span branch and the route's partial traversals all survived both
suites. The absolute anchors in `test_invariants.py` were added because this file said so.
"""

from __future__ import annotations

import math
from contextlib import contextmanager
from dataclasses import replace

from . import toy


@contextmanager
def _patched(**attributes):
    originals = {name: getattr(toy, name) for name in attributes}
    try:
        for name, value in attributes.items():
            setattr(toy, name, value)
        yield
    finally:
        for name, value in originals.items():
            setattr(toy, name, value)


@contextmanager
def strict_cap():
    """Pass-20 F5: `< cap` instead of `<= cap`. Passed all 78 tests of the corpus as it then was."""
    real = toy.nearest_on_graph
    with _patched(nearest_on_graph=lambda g, p, *, cap_m: real(
            g, p, cap_m=math.nextafter(cap_m, -math.inf))):
        yield


@contextmanager
def connector_free_cost():
    """Pass-20 F1: connectors charged to the reported time but not to objective 2's selection cost.

    The oracle's own defect, and it passed all twelve cases then in the corpus.
    """
    real = toy.journeys

    def journeys(graph, origin, destinations, destination_ids=None):
        out = []
        for j in real(graph, origin, destinations, destination_ids):
            origin_atts = toy.attachments(graph, origin, cap_m=toy.MAX_ACCESS_M)
            dest_atts = toy.attachments(graph, destinations[j.destination],
                                        cap_m=toy.POI_SNAP_MAX_M)
            if not origin_atts or not dest_atts:
                out.append(j)
                continue
            connector = (min(a.residual_m for a in origin_atts)
                         + min(a.residual_m for a in dest_atts)) / toy.ACCESS_SPEED_MPS
            out.append(toy.Journey(time_s=j.time_s, cost=j.cost - connector,
                                   destination=j.destination, destination_id=j.destination_id,
                                   route=j.route))
        return out

    with _patched(journeys=journeys):
        yield


@contextmanager
def identity_keyed_dedup():
    """Pass-20 F4: deduplicate candidates by canonical identity, which excludes time and cost, so
    two records differing only in weights collapse before either objective competes."""
    real = toy.nearest_on_graph

    def nearest_on_graph(graph, point, *, cap_m):
        found = real(graph, point, cap_m=cap_m)
        seen, kept = set(), []
        for a in found.candidates:
            key = (graph.edges[a.edge].identity, round(a.arclength_m, toy.ROUND_DP))
            if key not in seen:
                seen.add(key)
                kept.append(a)
        return toy.NearestOnGraph(candidates=tuple(kept), global_min_m=found.global_min_m)

    with _patched(nearest_on_graph=nearest_on_graph):
        yield


@contextmanager
def rounded_occurrence_bucket():
    """Pass-21 F1: key occurrences on a rounded arclength, which merges positions 4 mm apart that
    offer different remaining route."""
    real = toy.nearest_on_graph

    def nearest_on_graph(graph, point, *, cap_m):
        found = real(graph, point, cap_m=cap_m)
        buckets: dict = {}
        for a in found.candidates:
            buckets.setdefault((a.edge, round(a.arclength_m, toy.ROUND_DP)), a)
        return toy.NearestOnGraph(candidates=tuple(buckets.values()),
                                  global_min_m=found.global_min_m)

    with _patched(nearest_on_graph=nearest_on_graph):
        yield


@contextmanager
def bit_complemented_orientation():
    """Pass-21 F7: derive a reverse traversal's orientation by flipping the bit instead of
    renormalising the reversed geometry. Wrong for palindromes, and invisible otherwise."""
    def directed_identity(edge, *, forward):
        rounded = tuple((round(x, toy.ROUND_DP), round(y, toy.ROUND_DP)) for x, y in edge.geometry)
        key = min(rounded, rounded[::-1])
        base = (edge.u, edge.v, key, 0 if rounded == key else 1,
                tuple(sorted(edge.osmid)), round(edge.length_m, toy.ROUND_DP))
        if forward:
            return base
        return (base[1], base[0], base[2], 1 - base[3], base[4], base[5])

    with _patched(directed_identity=directed_identity):
        yield


@contextmanager
def dropped_zero_span():
    """Pass-21 F4: no zero-span same-edge branch, so a destination at the origin's own attachment
    position routes out to an endpoint and back."""
    real = toy._same_edge_direct

    def same_edge_direct(graph, origin, dest):
        if origin.edge == dest.edge and origin.fraction == dest.fraction:
            return None
        return real(graph, origin, dest)

    with _patched(_same_edge_direct=same_edge_direct):
        yield


@contextmanager
def route_without_partials():
    """Pass-21 F5: a route identity sequence carrying only the intervening path, so a journey over
    a single partial edge reports the empty route."""
    with _patched(_partial_route=lambda edge, *, forward, span: ()):
        yield


@contextmanager
def rank_without_cost():
    """Pass-21 F6: no final cost discriminator, so objective 1's reported cost on two same-identity
    equal-time records depends on insertion order."""
    original = toy.Journey.rank_key
    try:
        toy.Journey.rank_key = property(
            lambda self: (self.time_s, self.destination_id, self.route))
        yield
    finally:
        toy.Journey.rank_key = original


@contextmanager
def bounded_path_enumeration(limit: int = 4):
    """Pass-22 F2: path enumeration silently bounded to `limit` edges, so a reachable destination
    beyond that depth is reported as an absence.

    This is the mutant that defeated the whole instrument. It is *uniform* — no branch recognises a
    fixture, every relative invariant is preserved because the surviving journeys are all correct,
    and it passed all 423 conformance, invariant and mutation-guard tests. What it violates is
    design §2.5: `NO_PATH` may never be reported from a bounded search. The gap was a coverage
    **dimension**, hop depth, and `CHAIN_DEPTHS` now names it: a chain of 7 edges spends its first
    and last on entry and exit, leaving five intervening edges, and reports 560 s correctly or
    nothing at all.
    """
    original = toy._simple_paths

    def bounded(graph, start, goal):
        return [p for p in original(graph, start, goal) if len(p[2]) <= limit]

    with _patched(_simple_paths=bounded):
        yield


@contextmanager
def inflated_evaluate(extra_s: float = 1000.0):
    """A sentinel: every finite reported time inflated by `extra_s`, patched on `toy.evaluate`.

    Not a historical defect — a test of the harness itself. Pass-22 F8 installed exactly this and
    found `invariant_violations()` returning `[]` and every corpus `check()` clean, because both
    layers had bound `evaluate` by name at import. A mutation this gross must be caught by both
    layers; if it is not, the harness is measuring nothing and every other row of
    `EXPECTED_COVERAGE` is unsupported.
    """
    original = toy.evaluate

    def inflated(*args, **kwargs):
        r = original(*args, **kwargs)
        patch = {f: getattr(r, f) + extra_s for f in ("objective1_s", "objective2_s")
                 if getattr(r, f) is not None}
        return replace(r, **patch) if patch else r

    with _patched(evaluate=inflated):
        yield


#: Every mutant, by the finding that produced it.
MUTANTS: dict = {
    "pass20-F5-strict-cap": strict_cap,
    "pass20-F1-connector-free-cost": connector_free_cost,
    "pass20-F4-identity-keyed-dedup": identity_keyed_dedup,
    "pass21-F1-rounded-occurrence-bucket": rounded_occurrence_bucket,
    "pass21-F4-dropped-zero-span": dropped_zero_span,
    "pass21-F5-route-without-partials": route_without_partials,
    "pass21-F6-rank-without-cost": rank_without_cost,
    "pass21-F7-bit-complemented-orientation": bit_complemented_orientation,
    "pass22-F2-bounded-path-enumeration": bounded_path_enumeration,
    "pass22-F8-inflated-evaluate": inflated_evaluate,
}
