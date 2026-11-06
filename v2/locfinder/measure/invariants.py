"""Invariants over the admissible-input domain, and the representation transforms that must preserve
them.

**Why this module exists, in Codex pass 21's words:** *"The recurring process problem is treating
repair of the motivating example as evidence that a replacement rule's domain is settled."* Three
consecutive passes found that a fix closing the reviewed case opened an adjacent one — pass 19's two
blockers became four of pass 20's findings, which became three of pass 21's — and each time the
mechanism was the same: a named case proves a point, and a rule's *domain* is a different thing from
a point in it. Pass 21's recommendation was explicit: *"a compact set of invariants and
admissible-input rules exercised across representations, rather than another claim that the previous
named examples now pass."*

So this module is the instrument, not another case. It says three things:

1. **what an admissible input is** — `ToyEdge` and `ToyGraph` enforce it; `SCENARIOS` enumerates the
   shapes that have ever mattered;
2. **what must be true of every admissible input** — `INVARIANTS`, each a predicate on one
   evaluation;
3. **which re-expressions of one input must give the same answer** — `TRANSFORMS`, each a function
   from a scenario to an equivalent scenario.

The same lesson as the resolver benchmark, which `feedback-benchmark-over-point-fixes` records: when
a second round of fixes in one area breaks something new, stop and build the instrument instead of
attempting a third. This is the third round.

## What is deliberately *not* an invariant

Recorded here rather than silently absent, because an invariant that correct code cannot satisfy is
worse than no invariant:

* **Objective 2 is not monotone** in the destination set. Adding a *cheaper* destination correctly
  raises its reported time, 10 s → 100 s.
* **Splitting a segment is not answer-preserving.** Design §2.2's candidate rule is "the nearest
  position on each polyline *segment*", so subdividing a segment can add a candidate. That is a real
  property of the chosen rule, not a defect in the implementation of it, and
  `measure_split_divergence` quantifies it rather than asserting it away. If the design ever wants
  subdivision invariance it has to choose the exact per-geometry reading instead, and pass 20
  measured what that costs: 599.9747619048 s against 600.0399682540 s on its L-shaped edge, PASS
  against FAIL.
* **The answer is not continuous in the geometry.** 2 mm of movement can move it 899.99 s, because
  `attach_tie_m` is a threshold. §2.2 says so.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, replace

from .conformance import TIME_TOL_S, tolerance_is_decision_irrelevant
from . import toy
from .toy import ToyEdge, ToyGraph, evaluate


@dataclass(frozen=True)
class Scenario:
    """One admissible input: a graph, an origin, and identified destinations."""

    name: str
    graph: ToyGraph
    origin: tuple[float, float]
    destinations: tuple[tuple[float, float], ...]
    destination_ids: tuple[str, ...] | None = None
    shapes: tuple[str, ...] = ()        # which structural features this scenario carries

    def run(self):
        ids = list(self.destination_ids) if self.destination_ids else None
        return evaluate(self.graph, self.origin, list(self.destinations), ids)


def _route(result, objective: int) -> tuple:
    """The selected route's identity sequence, with its physical-road keys only.

    Node ids are deliberately dropped: `explicit_reverses` re-expresses a reverse traversal as a
    forward traversal of a reversed edge, which legitimately swaps the endpoint pair while being the
    same physical traversal. What must agree is the geometry key, the orientation, the osmid set and
    the length.
    """
    route = result.objective1_route if objective == 1 else result.objective2_route
    # (orientation, osmid, length). The geometry key and the node pair are both dropped, and for
    # different reasons: `translate` legitimately changes every coordinate, and `explicit_reverses`
    # legitimately swaps the endpoint pair while describing the same physical traversal. What
    # survives both is what makes it *that* traversal. Orientation is translation-invariant, because
    # adding a constant to both candidate sequences preserves which is lexicographically smaller.
    return tuple((ident[3], ident[4], ident[5]) for ident in (route or ()))


#: Fields whose equality across representations must be **exact**. These are identities and counts;
#: nothing about re-expressing an input may perturb a discrete choice.
DISCRETE_FIELDS = ("objective1_destination_id", "objective2_destination_id", "eligible_ids",
                   "objective1_route", "objective2_route", "origin_candidates")

#: Fields compared at `TIME_TOL_S`, because exact float equality across representations is a
#: stronger claim than the arithmetic supports. Translating a curved geometry by 12,345 m moves a
#: 90.8601039862 s answer by **2.0e-12 s**, and subdividing it moves it by **1.4e-14 s** — both pure
#: binary64 noise, with the candidate set and every identity unchanged. Measured across the whole
#: domain the spread stays under 1e-11 s, so the tolerance clears it by about 100x and sits 11
#: orders below the smallest published threshold. Every value compared this way additionally passes
#: `tolerance_is_decision_irrelevant`, so the tolerance cannot be hiding a verdict.
CONTINUOUS_FIELDS = ("objective1_s", "objective2_s", "objective1_cost", "objective2_cost",
                     "origin_nearest_m")


def differences(before: dict, after: dict) -> dict:
    """Fields that differ, discrete ones exactly and continuous ones beyond `TIME_TOL_S`."""
    out = {}
    for key in before:
        a, b = before[key], after[key]
        if key in CONTINUOUS_FIELDS and isinstance(a, float) and isinstance(b, float):
            if not tolerance_is_decision_irrelevant(a) or abs(a - b) > TIME_TOL_S:
                out[key] = (a, b)
        elif a != b:
            out[key] = (a, b)
    return out


def answers(scenario: Scenario) -> dict:
    """The **measured quantities** — every number and identity an S3 output reports about a point.

    An invariant that compared only times would miss the two defects pass 21 found in provenance: a
    falsely empty selected route, and an objective-1 cost decided by insertion order. So the selected
    destination and both selected costs are in here.
    """
    r = scenario.run()
    return {
        "objective1_s": r.objective1_s,
        "objective1_cost": r.objective1_cost,
        "objective1_destination_id": r.objective1_destination_id,
        "objective2_s": r.objective2_s,
        "objective2_cost": r.objective2_cost,
        "objective2_destination_id": r.objective2_destination_id,
        "eligible_ids": tuple(sorted(_ids(scenario)[i] for i in r.eligible)),
        "origin_nearest_m": r.origin_nearest_m,
        # The selected routes are measured quantities, not bookkeeping: design §12 requires route
        # references in the manifest. They are here because the mutation check showed three fixes
        # with no guard at all once they were absent -- a bit-complemented orientation, a dropped
        # zero-span branch and a route missing its partial traversals all survived both suites.
        # Under `explicit_reverses` a reverse traversal becomes a forward traversal of an
        # explicitly reversed edge, so the same physical traversal is reached two ways and its
        # identity must agree: that is what catches the orientation defect.
        "objective1_route": _route(r, 1),
        "objective2_route": _route(r, 2),
    }


def provenance(scenario: Scenario) -> dict:
    """What the manifest records *about how* the answer was reached.

    Held separately from `answers` because the two are invariant under different things, and
    building this module is what made that distinction necessary. `explicit_reverses` replaces one
    bidirectional edge with two opposed one-way records; the answers are identical, and
    `origin_candidates` **doubles**, because there genuinely are two routing records attached at that
    position. §2.2's candidates compete per record — pass-20 F4 is the reason they must — so a
    representation carrying more records has more candidates.

    That is a property of the *input*, not of the implementation. §12's equivalence contract is about
    implementations varying on one input; two ways of writing the same roads are two inputs. So
    provenance is required invariant only under transforms that leave the record structure alone.
    """
    r = scenario.run()
    return {"origin_candidates": r.origin_candidates}


def reported(scenario: Scenario) -> dict:
    """`answers` and `provenance` together, for the transforms that must preserve both."""
    return {**answers(scenario), **provenance(scenario)}


def _ids(scenario: Scenario) -> list[str]:
    if scenario.destination_ids:
        return list(scenario.destination_ids)
    return [str(i) for i in range(len(scenario.destinations))]


# ----------------------------------------------------------------------------- the admissible domain


def _e(u, v, geometry, time_s, cost_base, *, penalty=0.0, osmid=(1,), oneway=False) -> ToyEdge:
    return ToyEdge(u, v, geometry, time_s=time_s, cost_base=cost_base, penalty=penalty,
                   osmid=osmid, oneway=oneway)


#: Every structural shape that has mattered in a review, each as one small scenario. These are not
#: expected-answer fixtures — the conformance corpus holds those — they are the **domain** the
#: invariants below are quantified over.
SCENARIOS: tuple[Scenario, ...] = (
    Scenario("single_edge", ToyGraph(edges=(_e(0, 1, ((0, 0), (100, 0)), 100.0, 100.0),)),
             (10.0, 5.0), ((90.0, 5.0),), shapes=("open",)),
    Scenario("parallel_alternatives", ToyGraph(edges=(
        _e(0, 1, ((0, 0), (100, 0)), 1.0, 100.0, osmid=(1,)),
        _e(0, 1, ((0, 0), (100, 0)), 10.0, 10.0, osmid=(2,)),
        _e(0, 1, ((0, 0), (100, 0)), 5.0, 50.0, osmid=(3,)),
    )), (50.0, 0.0), ((100.0, 0.0),), shapes=("parallel", "three-way-tie")),
    Scenario("same_identity_alternatives", ToyGraph(edges=(
        _e(0, 1, ((0, 0), (100, 0)), 100.0, 1.0, osmid=(7,)),
        _e(0, 1, ((0, 0), (100, 0)), 100.0, 2.0, osmid=(7,)),
    )), (0.0, 0.0), ((100.0, 0.0),), shapes=("parallel", "shared-identity")),
    Scenario("one_way_with_return", ToyGraph(edges=(
        _e(0, 1, ((0, 0), (100, 0)), 100.0, 100.0, oneway=True),
        _e(1, 2, ((100, 0), (100, 50)), 100.0, 100.0, osmid=(2,), oneway=True),
        _e(2, 0, ((100, 50), (0, 0)), 100.0, 100.0, osmid=(3,), oneway=True),
    )), (80.0, 0.0), ((20.0, 0.0),), shapes=("oneway", "partial-edge")),
    Scenario("multi_segment", ToyGraph(edges=(
        _e(0, 1, ((0, 0), (100, 0), (100, 100)), 200.0, 200.0),)),
        (0.0, 0.0), ((100.0, 50.0),), shapes=("multi-segment",)),
    Scenario("self_crossing", ToyGraph(edges=(
        _e(0, 1, ((-100, 0), (0, 0), (0, 100), (100, 100), (100, 0), (0, 0), (0, -100)),
           1000.0, 1000.0, oneway=True),)),
        (0.0, 0.0), ((0.0, -100.0),), shapes=("self-crossing", "repeated-position")),
    Scenario("closed_ring", ToyGraph(edges=(
        _e(0, 0, ((0, 0), (100, 0), (100, 100), (0, 100), (0, 0)), 400.0, 400.0),)),
        (10.0, 0.0), ((0.0, 10.0),), shapes=("closed", "self-loop")),
    Scenario("two_closed_rings_opposed", ToyGraph(edges=(
        _e(0, 0, ((0, 0), (100, 0), (100, 100), (0, 100), (0, 0)), 4000.0, 4000.0, osmid=(7,),
           oneway=True),
        _e(0, 0, ((0, 0), (0, 100), (100, 100), (100, 0), (0, 0)), 4000.0, 4000.0, osmid=(7,),
           oneway=True),
    )), (10.0, 0.0), ((0.0, 10.0),), shapes=("closed", "opposed-orientations")),
    Scenario("palindrome_loop", ToyGraph(edges=(
        _e(0, 0, ((0, 0), (50, 0), (0, 0)), 100.0, 100.0),)),
        (25.0, 0.0), ((0.0, 0.0),), shapes=("closed", "palindrome")),
    Scenario("zero_length_segment", ToyGraph(edges=(
        _e(0, 1, ((0, 0), (0, 0), (100, 0)), 100.0, 100.0),)),
        (0.0, 0.0), ((100.0, 0.0),), shapes=("zero-length-segment",)),
    Scenario("zero_weight_edge", ToyGraph(edges=(
        _e(0, 1, ((0, 0), (100, 0)), 0.0, 0.0),)),
        (20.0, 0.0), ((80.0, 0.0),), shapes=("zero-weight",)),
    Scenario("reverse_palindrome", ToyGraph(edges=(
        _e(0, 1, ((0, 0), (50, 0), (0, 0)), 100.0, 100.0),)),
        (25.0, 1.0), ((0.0, 0.0),), shapes=("palindrome", "reverse-traversal")),
    Scenario("reverse_traversal", ToyGraph(edges=(
        _e(0, 1, ((0, 0), (100, 0)), 100.0, 100.0),)),
        (80.0, 0.0), ((20.0, 0.0),), shapes=("reverse-traversal", "partial-edge")),
    Scenario("reverse_traversal_curved", ToyGraph(edges=(
        _e(0, 1, ((0, 0), (40, 30), (100, 0)), 100.0, 100.0),)),
        (95.0, 5.0), ((5.0, 5.0),), shapes=("reverse-traversal", "multi-segment")),
    Scenario("zero_span", ToyGraph(edges=(
        _e(0, 1, ((0, 0), (100, 0)), 1000.0, 1000.0),)),
        (50.0, 0.0), ((50.0, 0.0),), shapes=("zero-span",)),
    Scenario("disconnected_tie", ToyGraph(edges=(
        _e(0, 1, ((0, 1), (100, 1)), 100.0, 100.0, osmid=(1,)),
        _e(2, 3, ((0, -1), (100, -1)), 1000.0, 1000.0, osmid=(2,)),
    )), (0.0, 0.0), ((100.0, 0.0),), shapes=("disconnected", "geometric-tie")),
    Scenario("penalty_bearing", ToyGraph(edges=(
        _e(0, 1, ((0, 0), (100, 0)), 1000.0, 1.0, penalty=120.0, osmid=(1,)),
        _e(0, 2, ((0, 0), (0, 50)), 5.0, 5.0, osmid=(2,)),
    )), (0.0, 0.0), ((1.0, 0.0), (0.0, 50.0)), shapes=("penalty", "two-destinations")),
    Scenario("unequal_connectors", ToyGraph(edges=(
        _e(0, 1, ((0, 0), (100, 0)), 10.0, 10.0, osmid=(1,)),
        _e(0, 2, ((0, 0), (0, -100)), 650.0, 20.0, osmid=(2,)),
    )), (0.0, 0.0), ((100.0, 100.0), (0.0, -100.0)), shapes=("unequal-connectors",)),
    Scenario("coincident_destinations", ToyGraph(edges=(
        _e(0, 1, ((0, 0), (100, 0)), 10.0, 10.0),)),
        (0.0, 0.0), ((100.0, 0.0), (100.0, 0.0)), destination_ids=("z", "a"),
        shapes=("coincident-destinations",)),
    Scenario("off_network_origin", ToyGraph(edges=(
        _e(0, 1, ((0, 0), (100, 0)), 100.0, 100.0),)),
        (50.0, 250.0), ((100.0, 0.0),), shapes=("off-network",)),
    Scenario("no_route", ToyGraph(edges=(
        _e(0, 1, ((0, 0), (100, 0)), 100.0, 100.0, oneway=True),)),
        (80.0, 0.0), ((20.0, 0.0),), shapes=("no-path", "oneway")),
    Scenario("empty_graph", ToyGraph(edges=()), (0.0, 0.0), ((10.0, 0.0),),
             shapes=("empty-graph",)),
)


# ----------------------------------------------------------------------------- transforms


def permute_edges(scenario: Scenario) -> Scenario:
    """Reverse the edge list. Nothing reported may change — design §2.4 exists for this."""
    return replace(scenario, name=f"{scenario.name}+permuted",
                   graph=ToyGraph(edges=tuple(reversed(scenario.graph.edges))))


def translate(scenario: Scenario, dx: float = 12345.678, dy: float = -98765.432) -> Scenario:
    """Offset every coordinate. Weights are carried, not derived from position, so nothing reported
    may change — this catches an accidental dependence on absolute coordinates, which a grid-aligned
    fixture set would never show."""
    def shift(geometry):
        return tuple((x + dx, y + dy) for x, y in geometry)
    return replace(
        scenario, name=f"{scenario.name}+translated",
        graph=ToyGraph(edges=tuple(replace(e, geometry=shift(e.geometry))
                                   for e in scenario.graph.edges)),
        origin=(scenario.origin[0] + dx, scenario.origin[1] + dy),
        destinations=tuple((x + dx, y + dy) for x, y in scenario.destinations),
    )


def explicit_reverses(scenario: Scenario) -> Scenario:
    """Replace each bidirectional edge with two one-way edges, the second carrying the explicitly
    reversed geometry.

    This is the transform pass-21 F7 was about: the same traversal reached through two supported
    representations must get the same identity, and a bit-complemented orientation gave it two.
    """
    edges = []
    for e in scenario.graph.edges:
        if e.oneway:
            edges.append(e)
            continue
        edges.append(replace(e, oneway=True))
        edges.append(replace(e, u=e.v, v=e.u, geometry=e.geometry[::-1], oneway=True))
    return replace(scenario, name=f"{scenario.name}+explicit-reverses",
                   graph=ToyGraph(edges=tuple(edges)))


def scale_weights(scenario: Scenario, factor: float = 7.0) -> Scenario:
    """Multiply every time and cost by one positive constant.

    Selection is scale-invariant — both objectives minimise — so every *selected* destination, route
    and candidate count must be unchanged, and the reported times must scale exactly. This separates
    "picked the right journey" from "added the numbers up right", which no single fixture does.
    """
    return replace(scenario, name=f"{scenario.name}+scaled",
                   graph=ToyGraph(edges=tuple(
                       replace(e, time_s=e.time_s * factor, cost_base=e.cost_base * factor,
                               penalty=e.penalty * factor) for e in scenario.graph.edges)))


def split_segments(scenario: Scenario) -> Scenario:
    """Insert the midpoint of every segment as an explicit vertex.

    **Not** answer-preserving, by design: §2.2's candidate rule is per *segment*, so subdividing can
    add a candidate. `measure_split_divergence` reports where it does rather than asserting it does
    not.
    """
    def split(geometry):
        out = [geometry[0]]
        for a, b in itertools.pairwise(geometry):
            out.append(((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0))
            out.append(b)
        return tuple(out)
    return replace(scenario, name=f"{scenario.name}+split",
                   graph=ToyGraph(edges=tuple(replace(e, geometry=split(e.geometry))
                                              for e in scenario.graph.edges)))


#: Transforms that must leave every **measured quantity** identical. `explicit_reverses` changes the
#: record structure, so it preserves `answers` but not `provenance` — see `provenance`.
ANSWER_PRESERVING: tuple = (permute_edges, translate, explicit_reverses)

#: Transforms that must additionally leave the **provenance** identical, because they do not change
#: how many edge records the input holds.
FULLY_PRESERVING: tuple = (permute_edges, translate)

#: Transforms that preserve the *selection* but scale the reported magnitudes.
SCALING: tuple = (scale_weights,)

#: Transforms deliberately **not** required to preserve the answer, with the reason.
NOT_PRESERVING: dict = {
    "split_segments": "design §2.2's candidate rule is per polyline segment, so subdividing a "
                      "segment can add a candidate. A subdivision-invariant rule would have to be "
                      "the exact per-geometry one, which pass 20 measured as a different answer "
                      "(599.9747619048 s against 600.0399682540 s, PASS against FAIL).",
}


def measure_split_divergence():
    """Where subdivision changes the answer, and by how much. Reported, not asserted."""
    out = []
    for scenario in SCENARIOS:
        before, after = reported(scenario), reported(split_segments(scenario))
        differing = differences(before, after)
        if differing:
            out.append((scenario.name, differing))
    return out

# ----------------------------------------------------------------------------- programmatic checks


def invariant_violations() -> list[str]:
    """Run the invariants directly, returning a violation list rather than asserting.

    `test_mutants.py` needs to ask "would this layer have caught that?" without starting a nested
    pytest, and a guard nobody checks is not a guard.

    **Every call into `toy` goes through the module**, never through a name imported here. A mutation
    harness patches `toy.directed_identity`, and a direct `from .toy import directed_identity` keeps
    the original binding — so the check would compare correct output against correct output and
    report that the mutant was caught by someone else. That happened: pass-21's orientation mutant
    read as uncaught by every layer until this module stopped holding its own reference.
    """
    bad: list[str] = []
    for scenario in SCENARIOS:
        base_answers = answers(scenario)
        base_reported = reported(scenario)
        for transform in ANSWER_PRESERVING:
            diff = differences(base_answers, answers(transform(scenario)))
            if diff:
                bad.append(f"{scenario.name}/{transform.__name__}: answers changed {diff}")
        for transform in FULLY_PRESERVING:
            diff = differences(base_reported, reported(transform(scenario)))
            if diff:
                bad.append(f"{scenario.name}/{transform.__name__}: provenance changed {diff}")

        result = scenario.run()
        if result.objective1_s is not None:
            if result.objective1_s > result.objective2_s + 1e-12:
                bad.append(f"{scenario.name}: objective 1 slower than objective 2")
            if result.objective2_cost > result.objective1_cost + 1e-12:
                bad.append(f"{scenario.name}: objective 2 dearer than objective 1")
            legal = {toy.directed_identity(e, forward=f) for e in scenario.graph.edges
                     for f in (True, False) if e.permits(forward=f)}
            for route in (result.objective1_route, result.objective2_route):
                if any(ident not in legal for ident in route):
                    bad.append(f"{scenario.name}: route names an impermissible traversal")
            if (scenario.origin != scenario.destinations[result.objective1_destination]
                    and not result.objective1_route):
                bad.append(f"{scenario.name}: a journey that moves has an empty route")

        points = [answers(scale_weights(scenario, float(k))) for k in (1, 3, 7)]
        for key in ("objective1_s", "objective2_s", "objective1_cost", "objective2_cost"):
            values = [p[key] for p in points]
            if any(v is None for v in values):
                continue
            first, second = (values[1] - values[0]) / 2.0, (values[2] - values[1]) / 4.0
            if abs(first - second) > 1e-9:
                bad.append(f"{scenario.name}: {key} is not affine in the weight scale")

    # The subdivision *signature*, not an invariance claim. Pass-21 F1's bucket mutant is caught
    # here and nowhere else: merging occurrences also merges the extra vertex subdivision adds, so
    # the measured divergence silently becomes empty. A change in this signature is information.
    divergence = {name for name, _ in measure_split_divergence()}
    if divergence != {"zero_length_segment"}:
        bad.append(f"subdivision divergence is now {sorted(divergence)}, not "
                   "{'zero_length_segment'}")

    bad.extend(_absolute_violations())
    return bad


def _absolute_violations() -> list[str]:
    """The anchors that do not compare two runs. A uniformly wrong implementation satisfies every
    relative invariant, so some checks have to name a number."""
    bad: list[str] = []
    graph = ToyGraph(edges=(_e(0, 1, ((0, 0), (100, 0)), 1000.0, 1000.0),))
    for at in ((50.0, 0.0), (0.0, 0.0), (100.0, 0.0)):
        r = evaluate(graph, at, [at])
        if r.objective1_s is None or abs(r.objective1_s) > 1e-12:
            bad.append(f"coincident origin and destination at {at}: {r.objective1_s!r}, not 0")

    for geometry in (((0, 0), (100, 0)), ((0, 0), (50, 10), (100, 0)), ((0, 0), (50, 0), (0, 0))):
        edge = ToyEdge(0, 1, geometry, time_s=1.0, cost_base=1.0, osmid=(7,))
        mirrored = ToyEdge(1, 0, geometry[::-1], time_s=1.0, cost_base=1.0, osmid=(7,))
        if toy.directed_identity(edge, forward=False) != mirrored.identity:
            bad.append(f"reverse identity disagrees with the explicit reverse on {geometry}")
    return bad
