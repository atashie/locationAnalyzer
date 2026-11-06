"""Invariants over the admissible-input domain, exercised across representations.

This is the instrument pass 21 asked for, and it exists because three consecutive reviews found the
same thing: *"treating repair of the motivating example as evidence that a replacement rule's domain
is settled."* The conformance corpus answers "is this value right?"; this file answers "is this
*rule* right over its whole domain?", which is the question that kept being answered by assumption.

**Every correction to this file so far has been to an invariant I wrote, not to the code it tests.**
Separating `answers` from `provenance` was forced by `explicit_reverses`; a plain proportionality
became an affine law because the connector term does not scale; and then pass 22 refuted the affine
law too, because the connector term that makes it affine is also what makes the *selection* switch.
What stands in its place is concavity — a minimum of affine functions — plus affinity conditioned on
the selected journey actually holding.

That sequence is the honest summary of this file: it is not a proof that the comparator is right, it
is the thing that keeps finding out my rules are wrong. Pass 22 also showed what it does **not** do.
A uniform `<= 4`-edge bound on path enumeration passed all 423 tests here and in the conformance
corpus, because hop depth was not a dimension of the domain. It is now, anchored to numbers rather
than to a relative property, because a relative invariant cannot see an absence.
"""

from __future__ import annotations

import math

import pytest

from locfinder.measure import toy
from locfinder.measure.invariants import (
    ANSWER_PRESERVING,
    _chain,
    CHAIN_DEPTHS,
    SCALE_POINTS,
    compare,
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


def _diff(a: dict, b: dict, transform: str = "") -> dict:
    """Discrete fields compared exactly, continuous ones in their own unit, through the
    correspondence `transform` actually preserves.

    Exact equality on the times was too strong, and a curved geometry showed it: translating one by
    12,345 m moves the answer 2.0e-12 s and subdividing it moves it 1.4e-14 s, with every identity
    and the candidate set unchanged. Those are binary64 artefacts of re-expressing the input, not
    changes of answer -- and every axis-aligned geometry in the first version of this domain hid
    them.

    Two later corrections, both pass-22 F7. The spread above is an **observation on these
    scenarios**, not a bound over admissible inputs: on one straight edge of 1,000,000 s with the
    origin at (.1,0) and the destination at (99.9,0), translation moves 998000.0000000001 s to
    997999.9999999927 s -- 7.5e-9 s, past this tolerance. And the helper itself used to call two
    identical values of exactly 600.0 s different, because it asked about decision-relevance before
    asking whether anything had moved.
    """
    return compare(a, b, transform)


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
        # Pass-22 F2. Not a geometric shape but a **dimension**: how many edges deep the selected
        # journey is. A uniform bound on path enumeration preserved every other shape and every
        # relative property, and passed all 423 tests.
        "chain",
    }
    assert required <= covered, f"uncovered shapes: {sorted(required - covered)}"
    assert all(s.shapes for s in SCENARIOS), "every scenario says which shapes it carries"
    # The depth dimension is covered at each declared depth, not just at one of them.
    for depth in CHAIN_DEPTHS:
        assert f"hop-depth-{depth}" in covered, depth


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
    name = transform.__name__
    before, after = answers(scenario), answers(transform(scenario))
    assert not _diff(before, after, name), _diff(before, after, name)


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
    name = transform.__name__
    before, after = reported(scenario), reported(transform(scenario))
    assert not _diff(before, after, name), _diff(before, after, name)


@ALL
def test_scaling_every_weight_can_change_the_selection_and_that_is_correct(scenario):
    """The invariant this file used to assert, kept as the refutation of itself.

    It read: "both objectives minimise, so multiplying every time and cost by one positive constant
    cannot change *which* journey is selected." That is false, and pass-22 F3 built the input.
    Connectors do not scale, so two journeys' totals are lines with different intercepts and they
    cross. Only the quantities that are genuinely scale-free may be asserted here, and the selected
    destination is not one of them.
    """
    before, after = reported(scenario), reported(scale_weights(scenario, 7.0))
    # The attachment geometry is untouched by a weight scaling, so these must hold.
    for key in ("eligible_ids", "origin_nearest_m", "origin_candidates"):
        assert before[key] == after[key], key
    # Nothing is asserted about which journey is selected. `test_a_minimum_over_journeys_is_concave`
    # is what constrains the switch.


def test_the_selection_really_does_switch_under_scaling():
    """Pass-22 F3's input, as a regression. If this ever stops switching, the refuted invariant
    would start passing again and someone would be tempted to restore it.

    Two bidirectional edges from `(0,0)`: A to `(100,0)` at time/cost 1, B to `(0,-100)` at 20.
    Destination A sits at `(100,100)`, so it carries a 100 m connector; B's is zero. B wins while
    its flat 20 beats A's `scale + 100/1.26`, and loses once the scale passes about 6.6.
    """
    graph = toy.ToyGraph(edges=(
        toy.ToyEdge(0, 1, ((0, 0), (100, 0)), time_s=1.0, cost_base=1.0, osmid=(1,)),
        toy.ToyEdge(0, 2, ((0, 0), (0, -100)), time_s=20.0, cost_base=20.0, osmid=(2,)),
    ))
    scenario = Scenario("f3", graph, (0.0, 0.0), ((100.0, 100.0), (0.0, -100.0)),
                        destination_ids=("a", "b"))
    picked = [answers(scale_weights(scenario, k))["objective1_destination_id"]
              for k in (1.0, 3.0, 7.0)]
    assert picked == ["b", "b", "a"], picked
    at7 = answers(scale_weights(scenario, 7.0))["objective1_s"]
    assert at7 == pytest.approx(7.0 + 100.0 / 1.26, rel=0, abs=1e-12)
    # The refuted law would have continued B and reported 140 s, which is FAIL at a 100 s
    # threshold where the correct answer, 86.3650793651 s, is PASS.
    assert at7 < 100.0 < 20.0 * 7.0


@ALL
def test_a_minimum_over_journeys_is_concave_in_the_weight_scale(scenario):
    """What replaces the affine law: a minimum of affine functions is **concave**.

    Each journey's total is `scale x network + connector`, affine in the scale. Objective 1 reports
    the minimum of those over journeys and objective 2 the minimum of the cost ones, so both are
    concave in the scale, with equality exactly where the argmin does not switch. This is strictly
    weaker than the affine law it replaces and, unlike it, true.

    Objective 2's reported *time* and objective 1's reported *cost* are the **other** quantity of
    the selected journey, so they are concave in nothing and are not checked here: the argmin can
    switch either way.
    """
    points = [answers(scale_weights(scenario, k)) for k in SCALE_POINTS]
    lo, mid, hi = SCALE_POINTS
    weight = (hi - mid) / (hi - lo)
    for key in ("objective1_s", "objective2_cost"):
        values = [p[key] for p in points]
        if any(v is None for v in values):
            assert all(v is None for v in values), f"{key}: {values}"
            continue
        chord = weight * values[0] + (1.0 - weight) * values[2]
        assert values[1] >= chord - 1e-9, (
            f"{key} is not concave in the scale: {values[1]!r} at scale {mid} is below the "
            f"chord {chord!r} joining {values[0]!r} and {values[2]!r}"
        )


@ALL
def test_a_total_is_affine_in_the_scale_while_the_selected_journey_holds(scenario):
    """The affine law, correctly conditioned.

    A *fixed* journey's total is `scale x network + connector`, so three collinear scales pin both
    coefficients and the slopes must agree. The condition is what the first version lacked: this
    asserts it only where the selected route and destination are identical at all three scales,
    because where they are not, the switch is the correct answer rather than a defect.

    The intercept is no longer offered as evidence that the connectors are present. A zero intercept
    is non-negative and affine, so no check in this family can distinguish a connector from its
    absence. `EXPECTED_COVERAGE` already recorded the connector-free mutant escaping this whole
    layer, and that should have been read as the refutation it was;
    `test_both_connectors_are_in_both_totals` does that job instead.
    """
    points = [answers(scale_weights(scenario, k)) for k in SCALE_POINTS]
    if not all(p["objective1_route"] == points[0]["objective1_route"]
               and p["objective1_destination_id"] == points[0]["objective1_destination_id"]
               for p in points):
        pytest.skip("the selected journey switches under scaling, which is correct")
    values = [p["objective1_s"] for p in points]
    if any(v is None for v in values):
        assert all(v is None for v in values), values
        return
    lo, mid, hi = SCALE_POINTS
    first = (values[1] - values[0]) / (mid - lo)
    second = (values[2] - values[1]) / (hi - mid)
    assert first == pytest.approx(second, rel=0, abs=1e-9), (
        f"not affine although the journey held: slopes {first!r} and {second!r}"
    )


def test_both_connectors_are_in_both_totals():
    """The absolute anchor that does what the intercept check was wrongly credited with.

    Two destinations, one reached over a 100 m connector and one with none. The own costs are
    `10 + 100/1.26` = 89.3650793651 and 20, so objective 2 must select the second and report
    **650 s**; omitting the connector from cost selects the first and reports 89.3650793651 s,
    turning FAIL into PASS at ten minutes. Objective 1 pins the connector in the reported time.
    """
    graph = toy.ToyGraph(edges=(
        toy.ToyEdge(0, 1, ((0, 0), (100, 0)), time_s=10.0, cost_base=10.0, osmid=(1,)),
        toy.ToyEdge(0, 2, ((0, 0), (0, -100)), time_s=650.0, cost_base=20.0, osmid=(2,)),
    ))
    r = toy.evaluate(graph, (0.0, 0.0), [(100.0, 100.0), (0.0, -100.0)])
    assert r.objective2_s == pytest.approx(650.0, rel=0, abs=1e-9)
    assert r.objective1_s == pytest.approx(10.0 + 100.0 / 1.26, rel=0, abs=1e-9)


@pytest.mark.parametrize("depth", CHAIN_DEPTHS)
def test_a_reachable_destination_is_reachable_at_any_hop_depth(depth):
    """Hop depth, the coverage dimension pass-22 F2 walked through.

    A uniform `<= 4`-edge bound on path enumeration passed all 423 tests of this layer and the
    conformance corpus together. It recognised no fixture and preserved every relative property,
    because the journeys it did return were all correct -- it simply stopped looking. What it
    violates is design §2.5: `NO_PATH` may never come from a bounded search.

    Adding the chain *scenarios* was not enough, and the measurement said so. A mutant that removes
    journeys reports `None` everywhere, the transform comparisons find `None` equal to `None`, and
    every per-result check sits behind `objective1_s is not None`. **A relative invariant cannot see
    an absence**, so the depth has to be anchored to a number, exactly as the cap and the connector
    had to be.
    """
    r = _chain(depth).run()
    assert r.objective1_s is not None, f"a chain of {depth} edges reported no journey"
    assert r.objective1_s == pytest.approx(80.0 * depth, rel=0, abs=1e-9)
    assert len(r.objective1_route) == depth


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

    # **An empty route implies zero network seconds**, and only that direction.
    #
    # The previous form asked whether the endpoints differed, and pass-22 F4 showed it rejecting a
    # correct answer: one bidirectional edge of 1000 s from (0,0) to (100,0), origin (50,1) and
    # destination (50,2). Both attach at arclength 50, so the legal answer is 3/1.26 =
    # 2.3809523810 s with an **empty** network route -- the coordinates differ and all movement is
    # in the two connectors. Design 2.2's zero-span convention permits exactly that.
    #
    # Writing the repair as an equivalence was also wrong, and the `zero_weight_edge` scenario said
    # so within the minute: a journey across a 0 s edge has a real one-element route and zero
    # network seconds. The implication still catches what the check was for -- a route stripped of
    # its partial traversals on a weighted edge -- without asserting a converse 2.2 does not give.
    for name, route, network in (("objective1", r.objective1_route, r.objective1_network_s),
                                 ("objective2", r.objective2_route, r.objective2_network_s)):
        if not route:
            assert network == 0.0, (
                f"{name} reports an empty route but {network!r} network seconds, so it traversed "
                f"something it did not name"
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
