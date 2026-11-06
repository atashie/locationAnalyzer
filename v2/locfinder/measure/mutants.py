"""Every wrong implementation a review has built, kept executable.

**Why these live in the package rather than in a test.** A guard is only a guard if something checks
that it still guards. `feedback-benchmark-over-point-fixes` records the decisive experiment for this —
*"verify the guard by reverting the fix"* — and pass 14 showed that a benchmark I had claimed was the
guard turned none of its assertions red when the historical fixes were reverted. So each mutant here
is installed and the suites are run against it, and `test_mutants.py` asserts that **every mutant is
caught by at least one layer**.

That check immediately earned its place, and the table it produces is the measured division of
labour rather than a claim about it:

| mutant | invariants | conformance |
|---|---|---|
| pass-20 F1 connector-free cost | **caught** | **caught** |
| pass-20 F5 strict cap | passes | **caught** |
| pass-20 F4 identity-keyed dedup | **caught** | **caught** |
| pass-21 F1 rounded occurrence bucket | **caught** | passes |
| pass-21 F4 dropped zero-span branch | **caught** | passes |
| pass-21 F5 route without partials | **caught** | passes |
| pass-21 F6 rank without cost | **caught** | passes |
| pass-21 F7 bit-complemented orientation | **caught** | passes |
| pass-22 F2 bounded path enumeration | **caught** | passes |
| pass-22 F8 inflated evaluator (sentinel) | **caught** | **caught** |
| pass-23 F1 bounded destinations | **caught** | passes |
| pass-23 F4 coordinate-dependent orientation | **caught** | passes |
| pass-23 F8 connector-free reported cost | **caught** | **caught** |

The two layers are **complementary and neither subsumes the other**: eight mutants escape the corpus
and one escapes the invariants, and every one is caught by the other. The corpus catches boundary and
value defects; the invariants catch domain and representation defects. A uniformly tightened cap
preserves every *relative* property — scaling, translating, permuting and re-expressing all still
agree, because both sides are equally wrong — so only an exact-boundary case sees it.

**Three of these mutants defeated the entire instrument when they were written, and all three for
the same reason.** The bounded path enumeration passed all 423 tests, the bounded destination list
all 1,040, and the coordinate-dependent orientation all 527. None of them recognised a fixture; each
was a *uniform* reduction whose surviving answers were all correct. What each exposed was an
undeclared **dimension** of the input domain:

| mutant | the dimension nobody had declared |
|---|---|
| pass-22 F2 | **hop depth** — no scenario needed a journey more than four edges deep |
| pass-23 F1 | **destination cardinality** — no oracle call anywhere received more than three |
| pass-23 F4 | **absolute-coordinate dependence of identity** — every identity anchor sat near the origin |

And in all three cases the repair had to be an **absolute anchor**, not another relative invariant. A
relative invariant compares two runs, so it cannot see a defect that removes results (`None` equals
`None`), nor a positional truncation (both sides truncated alike), nor a defect that appears only far
from the origin (no near-origin transform reaches it). That is the single most reusable thing this
file has established.

**Getting the table right required fixing the harness three times**, all easy to repeat:

1. A patched module global cannot reach a binding another module imported **by name**, so
   `invariants.py` had to stop holding its own reference to `directed_identity`.
2. Then `evaluate` turned out to be imported by name in **both** layers — the same defect, in the
   bindings I had not looked at. A wrapper adding 1000 s to every finite time left
   `invariant_violations()` returning `[]`. `inflated_evaluate` is the sentinel that fails if either
   layer ever stops seeing an evaluator replacement; without it, every row above measures nothing.
3. The orientation mutant stayed invisible until the domain gained an input whose **selected route
   traverses a palindromic edge backwards**, since the bit flip and the renormalisation agree on
   every other geometry.

Three of these were, at the time the mutation check first ran, defects fixed with **no guard at
all**: the orientation bit, the zero-span branch and the route's partial traversals all survived both
suites. The absolute anchors in `test_invariants.py` were added because this file said so, and
`pass23-F8-connector-free-reported-cost` is there because the anchor that replaced one of them turned
out to assert only half of what it claimed.
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


@contextmanager
def bounded_destinations(limit: int = 4):
    """Pass-23 F1: journey enumeration truncated to the first `limit` destinations.

    The second mutant to defeat the whole instrument, and by the same mechanism as the first: a
    **dimension** nobody had declared. Destination cardinality never exceeded **three** in any oracle
    call across all 1,040 tests, so a cutoff at four never activated. Eligibility still examines
    every destination — the eligible set names all of them — and every surviving journey is correct.

    A positional truncation is also invisible to every relative invariant, because both sides of a
    transform are equally truncated. `five_spokes_best_last` and `five_spokes_best_first` plus the
    absolute anchors in `_absolute_violations` are what see it: five spokes, the 1 s one at the end
    of the list, correct answer 1 s and the mutant's 1000 s — PASS against FAIL at ten minutes.
    """
    original = toy.journeys

    def bounded(graph, origin, destinations, destination_ids=None):
        return original(graph, origin, destinations[:limit],
                        None if destination_ids is None else destination_ids[:limit])

    with _patched(journeys=bounded):
        yield


@contextmanager
def coordinate_dependent_orientation(box: float = 10000.0):
    """Pass-23 F4: a directed identity whose orientation is forced to 0 outside a coordinate box.

    Built to attack the decision to stop comparing orientation under `translate`, and it worked: it
    passed all 527 conformance, invariant and mutation-guard tests. The reasoning that looked sound
    was that orientation is still compared under the two transforms leaving coordinates alone, "so
    this costs no coverage". It does: a defect that only appears *far from the origin* is reachable
    by no near-origin transform, and the route-legality check recomputes identities with the same
    wrong function, so it compares wrong against wrong.

    The dimension is **absolute-coordinate dependence of identity**, and the answer is an absolute
    anchor at several offsets rather than a relative comparison.
    """
    original = toy.directed_identity

    def wrong(edge, *, forward):
        ident = original(edge, forward=forward)
        if max(abs(c) for point in edge.geometry for c in point) > box:
            ident = ident[:3] + (0,) + ident[4:]
        return ident

    with _patched(directed_identity=wrong):
        yield


@contextmanager
def connector_free_reported_cost():
    """Pass-23 F8: connectors stripped from `objective1_cost` and from `objective2_s`.

    Not a historical defect — a probe of the connector anchor, which claimed to establish the
    connectors were in both objectives' time *and* cost and asserted only two of those four
    outputs. Its origin connector was zero and its objective-2 winner had a zero destination
    connector, so this wrapper passed it untouched while turning a 603.8095238095 s FAIL into a
    580 s PASS.
    """
    original = toy.evaluate

    def stripped(*args, **kwargs):
        r = original(*args, **kwargs)
        patch = {}
        if r.objective1_cost is not None and r.objective1_network_s is not None:
            patch["objective1_cost"] = r.objective1_network_s
        if r.objective2_s is not None and r.objective2_network_s is not None:
            patch["objective2_s"] = r.objective2_network_s
        return replace(r, **patch) if patch else r

    with _patched(evaluate=stripped):
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
    # Pass 23's three, two of which defeated the whole instrument as it stood after pass 22.
    "pass23-F1-bounded-destinations": bounded_destinations,
    "pass23-F4-coordinate-dependent-orientation": coordinate_dependent_orientation,
    "pass23-F8-connector-free-reported-cost": connector_free_reported_cost,
}
