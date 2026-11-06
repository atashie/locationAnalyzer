"""Invariants over the admissible-input domain, exercised across representations.

This is the instrument pass 21 asked for, and it exists because three consecutive reviews found the
same thing: *"treating repair of the motivating example as evidence that a replacement rule's domain
is settled."* The conformance corpus answers "is this value right?"; this file answers "is this
*rule* right over its whole domain?", which is the question that kept being answered by assumption.

**It has already earned its place twice, both times by rejecting an invariant I wrote rather than the
code.** Separating `answers` from `provenance` was forced by `explicit_reverses`, and the affine
scaling law replaced a plain proportionality that the connector term cannot satisfy. Both are
sharper statements than what they replaced, and neither was reachable from a fixture.
"""

from __future__ import annotations

import math

import pytest

from locfinder.measure import toy
from locfinder.measure.invariants import (
    ANSWER_PRESERVING,
    differences,
    FULLY_PRESERVING,
    NOT_PRESERVING,
    SCENARIOS,
    Scenario,
    answers,
    measure_split_divergence,
    reported,
    scale_weights,
    split_segments,
)

ALL = pytest.mark.parametrize("scenario", SCENARIOS, ids=[s.name for s in SCENARIOS])


def _diff(a: dict, b: dict) -> dict:
    """Discrete fields compared exactly, continuous ones at a decision-irrelevant tolerance.

    Exact equality on the times was too strong, and a curved geometry showed it: translating one by
    12,345 m moves the answer 2.0e-12 s and subdividing it moves it 1.4e-14 s, with every identity
    and the candidate set unchanged. Those are binary64 artefacts of re-expressing the input, not
    changes of answer -- and every axis-aligned geometry in the first version of this domain hid
    them.
    """
    return differences(a, b)


# ----------------------------------------------------------------------------- the domain itself


def test_the_domain_covers_every_shape_a_review_has_turned_up():
    """A scenario list is only as good as the shapes in it, so the shapes are named and checked.

    Every entry here was added because some review pass built an input of that shape and found a
    defect with it. A new shape arriving in a finding is a new entry, not a new one-off case.
    """
    covered = {shape for s in SCENARIOS for shape in s.shapes}
    required = {
        "open", "parallel", "shared-identity", "three-way-tie", "oneway", "partial-edge",
        "multi-segment", "self-crossing", "repeated-position", "closed", "self-loop",
        "opposed-orientations", "palindrome", "zero-length-segment", "zero-weight", "zero-span",
        "disconnected", "geometric-tie", "penalty", "two-destinations", "unequal-connectors",
        "coincident-destinations", "off-network", "no-path", "empty-graph",
        "reverse-traversal",
    }
    assert required <= covered, f"uncovered shapes: {sorted(required - covered)}"
    assert all(s.shapes for s in SCENARIOS), "every scenario says which shapes it carries"


def test_every_scenario_is_an_admissible_input():
    for s in SCENARIOS:
        assert isinstance(s.graph, toy.ToyGraph)
        for e in s.graph.edges:
            assert len(e.geometry) >= 2
            assert all(math.isfinite(c) for xy in e.geometry for c in xy)
            assert math.isfinite(e.time_s) and math.isfinite(e.total_cost)


def test_a_non_finite_input_is_refused():
    """The admissible-input contract. Pass-21: a claim of total ordering over floats needs one, and
    `fsum`, `min` and the geometry arithmetic are all undefined on NaN."""
    for bad_geometry in (((0, 0), (math.inf, 0)), ((0, 0), (math.nan, 0))):
        with pytest.raises(ValueError, match="finite"):
            toy.ToyEdge(0, 1, bad_geometry, time_s=1.0, cost_base=1.0)
    for field in ("time_s", "cost_base", "penalty"):
        with pytest.raises(ValueError, match="finite"):
            toy.ToyEdge(0, 1, ((0, 0), (1, 0)), **{"time_s": 1.0, "cost_base": 1.0,
                                                   field: math.inf})
    with pytest.raises(ValueError, match="non-negative"):
        toy.ToyEdge(0, 1, ((0, 0), (1, 0)), time_s=-1.0, cost_base=1.0)
    with pytest.raises(ValueError, match="at least two"):
        toy.ToyEdge(0, 1, (((0, 0)),), time_s=1.0, cost_base=1.0)


# ----------------------------------------------------------------------------- representation


@ALL
@pytest.mark.parametrize("transform", ANSWER_PRESERVING,
                         ids=[t.__name__ for t in ANSWER_PRESERVING])
def test_re_expressing_the_input_does_not_change_the_answer(scenario, transform):
    """Permuting the edge list, translating every coordinate, and replacing a bidirectional edge
    with two opposed one-way edges all describe the same roads, so every measured quantity must
    agree — times, costs, selected destinations and eligibility.

    `translate` is the one no fixture would have covered: all of them sit on tidy coordinates near
    the origin, so an accidental dependence on absolute position would never have shown.
    """
    before, after = answers(scenario), answers(transform(scenario))
    assert not _diff(before, after), _diff(before, after)


@ALL
@pytest.mark.parametrize("transform", FULLY_PRESERVING,
                         ids=[t.__name__ for t in FULLY_PRESERVING])
def test_the_provenance_also_survives_transforms_that_keep_the_record_structure(scenario, transform):
    """Permuting and translating leave the *number of edge records* alone, so the recorded candidate
    count must agree too.

    `explicit_reverses` is excluded on purpose: it genuinely turns one record into two, and §2.2's
    candidates compete per record — pass-20 F4 is why they must. That is a property of the input, not
    of the implementation, and §12's equivalence contract is about implementations varying on **one**
    input.
    """
    before, after = reported(scenario), reported(transform(scenario))
    assert not _diff(before, after), _diff(before, after)


@ALL
def test_scaling_every_weight_leaves_the_selection_alone(scenario):
    """Both objectives minimise, so multiplying every time and cost by one positive constant cannot
    change *which* journey is selected."""
    base, scaled = answers(scenario), answers(scale_weights(scenario, 7.0))
    for key in ("objective1_destination_id", "objective2_destination_id", "eligible_ids",
                "origin_nearest_m"):
        assert base[key] == scaled[key], key


@ALL
def test_a_total_is_exactly_affine_in_the_weight_scale(scenario):
    """The sharper invariant that a plain proportionality got wrong.

    A journey total is `network terms + connector terms`, and the connector is
    `residual / 1.26` — **it does not scale with the edge weights**. So a total is affine in the
    scale factor, not proportional: on `single_edge`, 87.9365079365 s becomes 567.9365079365 s at
    ×7, which is `7 × 80 + 7.9365079365` and not `7 × 87.9365079365`.

    Three factors pin both coefficients. The slope is the network part and the intercept is the
    connector part, so this single check verifies that the connectors are present in **both**
    objectives' time *and* cost — which is exactly what pass-20 F1 found missing from cost and what
    no fixture separated.
    """
    points = [(k, answers(scale_weights(scenario, float(k)))) for k in (1, 3, 7)]
    for key in ("objective1_s", "objective2_s", "objective1_cost", "objective2_cost"):
        values = [v[key] for _, v in points]
        if any(v is None for v in values):
            assert all(v is None for v in values), f"{key}: {values}"
            continue
        (k1, _), (k2, _), (k3, _) = points
        first = (values[1] - values[0]) / (k2 - k1)
        second = (values[2] - values[1]) / (k3 - k2)
        assert first == pytest.approx(second, rel=0, abs=1e-9), (
            f"{key} is not affine in the scale: slopes {first!r} and {second!r}"
        )
        intercept = values[0] - first
        assert intercept >= -1e-9, f"{key} implies a negative connector term: {intercept!r}"


# ----------------------------------------------------------------------------- what must hold always


@ALL
def test_objective_1_is_never_slower_than_objective_2(scenario):
    """Objective 1 is the minimum over the same journeys objective 2 selects from, so it cannot
    report a larger time. A violation would mean the two were enumerating different sets — which is
    design §2.3's hybrid defect."""
    r = scenario.run()
    if r.objective1_s is None:
        assert r.objective2_s is None
        return
    assert r.objective1_s <= r.objective2_s + 1e-12


@ALL
def test_objective_2_is_never_more_expensive_than_objective_1(scenario):
    """The mirror image, and the one that catches a cost objective minimising the wrong thing."""
    r = scenario.run()
    if r.objective2_cost is None:
        assert r.objective1_cost is None
        return
    assert r.objective2_cost <= r.objective1_cost + 1e-12


@ALL
def test_evaluation_is_deterministic(scenario):
    # determinism is exact: the same input twice must give the identical object, with no
    # tolerance, because nothing has been re-expressed
    assert answers(scenario) == answers(scenario)
    assert reported(scenario) == reported(scenario)


@ALL
def test_adding_a_destination_never_slows_objective_1(scenario):
    """Objective 1 is a minimum over destinations, so enlarging the set can only lower it.

    Deliberately **not** asserted for objective 2, which follows cost: adding a *cheaper*
    destination correctly raises its reported time from 10 s to 100 s, and an implementation
    asserting otherwise would enforce a defect.
    """
    extra = (999.0, 999.0)          # far away; eligible only if something is near it
    wider = Scenario(f"{scenario.name}+extra", scenario.graph, scenario.origin,
                     scenario.destinations + (extra,),
                     destination_ids=(tuple(_names(scenario)) + ("zzz-extra",)),
                     shapes=scenario.shapes)
    before, after = scenario.run(), wider.run()
    if before.objective1_s is None:
        return
    assert after.objective1_s is not None
    assert after.objective1_s <= before.objective1_s + 1e-12


@ALL
def test_eligibility_is_a_property_of_the_destination_alone(scenario):
    """A destination's eligibility depends on its own distance to the graph — not on the origin, and
    not on the other destinations. §2's two caps sit on different sides of the journey."""
    r = scenario.run()
    for i, d in enumerate(scenario.destinations):
        alone = toy.evaluate(scenario.graph, (10_000.0, 10_000.0), [d])
        assert (i in r.eligible) == (0 in alone.eligible), (
            f"destination {i} at {d} changed eligibility when asked about on its own"
        )


def _names(scenario: Scenario) -> list[str]:
    if scenario.destination_ids:
        return list(scenario.destination_ids)
    return [str(i) for i in range(len(scenario.destinations))]


# ----------------------------------------------------------------------------- recorded non-invariants


def test_subdivision_is_not_required_to_preserve_the_answer_and_is_measured_instead():
    """Design §2.2's candidate rule is per polyline **segment**, so inserting a vertex can add a
    candidate. Asserting invariance would be asserting a different design.

    Measured on the whole domain: subdivision preserves every **answer**, and perturbs provenance on
    exactly one input — a zero-length segment, whose midpoint becomes a third vertex. That is a
    useful thing to know and a wrong thing to assume, so it is recorded as a measurement.
    """
    assert "split_segments" in NOT_PRESERVING
    divergences = dict(measure_split_divergence())
    assert set(divergences) == {"zero_length_segment"}, (
        f"subdivision now diverges on {sorted(divergences)} — if that is intended, record why; "
        "if not, it is a finding"
    )
    assert set(divergences["zero_length_segment"]) == {"origin_candidates"}

    for s in SCENARIOS:
        before, after = answers(s), answers(split_segments(s))
        assert not differences(before, after), (
            f"{s.name}: subdivision changed an answer: {_diff(before, after)}")


def test_objective_2_is_recorded_as_not_monotone():
    """The property that must not be asserted, kept executable so it cannot be quietly added."""
    graph = toy.ToyGraph(edges=(
        toy.ToyEdge(0, 1, ((0, 0), (100, 0)), time_s=10.0, cost_base=10.0, osmid=(1,)),
        toy.ToyEdge(0, 2, ((0, 0), (0, 100)), time_s=100.0, cost_base=5.0, osmid=(2,)),
    ))
    one = toy.evaluate(graph, (0.0, 0.0), [(100.0, 0.0)])
    two = toy.evaluate(graph, (0.0, 0.0), [(100.0, 0.0), (0.0, 100.0)])
    assert one.objective2_s == pytest.approx(10.0)
    assert two.objective2_s == pytest.approx(100.0), "adding a cheaper destination raises it"
    assert two.objective1_s == pytest.approx(one.objective1_s), "objective 1 is unaffected"


@ALL
def test_a_selected_route_is_a_legal_traversal_of_this_graph(scenario):
    """Absolute, not relative. Every identity in a selected route must be a legal directed traversal
    of some edge in the graph, and a journey that moves must have a non-empty route.

    This is the invariant the mutation check showed was missing: a route stripped of its partial
    traversals survived both suites, because the relative transforms compared two equally wrong
    answers. On a zero-weight edge the stripped route is the empty tuple — a journey from arclength
    20 to 80 that traverses nothing.
    """
    r = scenario.run()
    if r.objective1_s is None:
        return
    legal = {toy.directed_identity(e, forward=f)
             for e in scenario.graph.edges for f in (True, False) if e.permits(forward=f)}
    for name, route in (("objective1", r.objective1_route), ("objective2", r.objective2_route)):
        for ident in route:
            assert ident in legal, f"{name} route names a traversal this graph does not permit"

    moved = scenario.origin != scenario.destinations[r.objective1_destination]
    if moved:
        assert r.objective1_route, (
            "a journey that goes somewhere traverses something, so its route cannot be empty"
        )


def test_a_coincident_origin_and_destination_cost_nothing():
    """Absolute anchor for the zero-span branch. Both attach at the same position on the same edge
    with zero residuals, so the journey is zero connectors plus zero traversal.

    The mutation check showed why this has to be absolute: dropping the zero-span branch sends the
    journey out to an endpoint and back for 1000 s, and every *relative* invariant still holds,
    because the transforms compare two equally wrong answers.
    """
    graph = toy.ToyGraph(edges=(
        toy.ToyEdge(0, 1, ((0, 0), (100, 0)), time_s=1000.0, cost_base=1000.0, osmid=(1,)),
    ))
    for at in ((50.0, 0.0), (0.0, 0.0), (100.0, 0.0)):
        r = toy.evaluate(graph, at, [at])
        assert r.objective1_s == pytest.approx(0.0, rel=0, abs=1e-12), at
        assert r.objective2_s == pytest.approx(0.0, rel=0, abs=1e-12), at
        assert r.objective1_cost == pytest.approx(0.0, rel=0, abs=1e-12), at

    # with a nonzero residual on one side, the connector is still charged on both objectives
    offset = toy.evaluate(graph, (50.0, 0.0), [(50.0, 10.0)])
    assert offset.objective1_s == pytest.approx(10.0 / toy.ACCESS_SPEED_MPS, rel=0, abs=1e-12)
    assert offset.objective1_cost == pytest.approx(10.0 / toy.ACCESS_SPEED_MPS, rel=0, abs=1e-12)


def test_the_same_physical_traversal_has_one_identity_however_it_is_expressed():
    """Absolute anchor for the orientation rule, and the one `explicit_reverses` turns relative.

    A reverse traversal of an edge and a forward traversal of that edge written out reversed are the
    same physical traversal. Deriving the identity by complementing an orientation bit instead of
    renormalising the reversed geometry gives them two identities — invisibly for ordinary
    geometries, and wrongly for a palindrome, where the two directions trace the same coordinates
    and must share one.
    """
    for geometry in (((0, 0), (100, 0)),                     # straight
                     ((0, 0), (50, 10), (100, 0)),           # curved, not palindromic
                     ((0, 0), (50, 0), (0, 0))):             # palindromic
        edge = toy.ToyEdge(0, 1, geometry, time_s=1.0, cost_base=1.0, osmid=(7,))
        reversed_edge = toy.ToyEdge(1, 0, geometry[::-1], time_s=1.0, cost_base=1.0, osmid=(7,))
        assert toy.directed_identity(edge, forward=False) == reversed_edge.identity, geometry

    palindrome = toy.ToyEdge(0, 0, ((0, 0), (50, 0), (0, 0)), time_s=1.0, cost_base=1.0)
    assert (toy.directed_identity(palindrome, forward=True)
            == toy.directed_identity(palindrome, forward=False)), (
        "a palindromic closed edge's two directions trace the same coordinates in the same order, "
        "so they are interchangeable and must share an identity"
    )
