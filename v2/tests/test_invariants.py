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

from locfinder.grid import encode_minutes
from locfinder.measure import toy
from locfinder.measure.invariants import (
    ANSWER_PRESERVING,
    _chain,
    CHAIN_DEPTHS,
    SCALE_POINTS,
    _scale_allowance,
    compare,
    differences,
    FULLY_PRESERVING,
    NOT_PRESERVING,
    SCENARIOS,
    SUBDIVISION_DIVERGES_ON,
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
        # Pass-23 F1, the same lesson a second time: destination **cardinality**. No oracle call
        # anywhere in the suite ever received more than three destinations, so a
        # `destinations[:4]` truncation never activated. Both list positions of the optimum are
        # carried, because a cutoff keeping the head of the list is a different defect from one
        # keeping the tail.
        "many-destinations", "best-destination-last", "best-destination-first",
        # Design revision 9's candidate-universe amendment: the input whose answer the superseded
        # per-segment band moved under subdivision, and the exact-equidistance case that the
        # amendment had to preserve (and does).
        "subdivision-sensitive", "equidistant-within-record",
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
            # Reachability is weight-independent under a positive finite scaling, so `None` must
            # occur at every scale or none.
            assert all(v is None for v in values), f"{key}: {values}"
            continue
        chord = weight * values[0] + (1.0 - weight) * values[2]
        assert values[1] >= chord - _scale_allowance(values + [chord]), (
            f"{key} is not concave in the scale: {values[1]!r} at scale {mid} is below the "
            f"chord {chord!r} joining {values[0]!r} and {values[2]!r}"
        )


@ALL
def test_a_total_is_affine_in_the_scale_where_only_one_journey_exists(scenario):
    """The affine law, conditioned on something that actually holds the journey fixed.

    A *fixed* journey's total is `scale x network + connector`, so three collinear scales pin both
    coefficients and the slopes must agree. Getting the **condition** right has taken three goes.

    It began unconditional, and pass-22 F3 refuted that: the selection switches, because connectors
    give journeys different intercepts. I then conditioned it on the selected route and destination
    being unchanged, and pass-23 F2 refuted *that*: neither names the attachment occurrence. On
    `(0,0),(50,0),(100,0)` of time/cost 40 with the origin at `(49.995,0)`, the origin's attachment
    switches between its exact projection and the next segment's clamped start while the destination
    stays `"0"` and the route stays one identity — slopes **20.000984126984125 against 20**, nearly a
    million tolerances apart. The check rejected a correct oracle.

    `n_journeys == 1` is the condition the earlier two were reaching for: where the graph admits one
    journey there is nothing to switch to. It is exact rather than inferred.

    All six qualifying scenarios have **zero connectors**, so this exercises the proportional case
    only and cannot tell affine from proportional. `test_the_affine_law_with_its_intercept_pinned`
    names the intercept instead of inferring it from differences.
    """
    if scenario.run().n_journeys != 1:
        pytest.skip("more than one journey exists, so the selected one may legitimately switch")
    points = [answers(scale_weights(scenario, k)) for k in SCALE_POINTS]
    values = [p["objective1_s"] for p in points]
    if any(v is None for v in values):
        assert all(v is None for v in values), values
        return
    lo, mid, hi = SCALE_POINTS
    first = (values[1] - values[0]) / (mid - lo)
    second = (values[2] - values[1]) / (hi - mid)
    assert first == pytest.approx(second, rel=0, abs=_scale_allowance(values)), (
        f"not affine although the graph admits one journey: slopes {first!r} and {second!r}"
    )


def test_the_affine_law_with_its_intercept_pinned():
    """Both coefficients as named numbers, because no relative check in the domain pins the
    intercept: every single-journey scenario has zero connectors.

    One straight 100 m edge of time/cost 580, origin 10 m off one end and destination 20 m off the
    other. Scaling the weight must give exactly `k x 580 + 30/1.26`, so a proportional
    implementation (`k x 603.8095238095`) and a connector-free one (`k x 580`) both fail here while
    satisfying every relative property.
    """
    for k in SCALE_POINTS:
        graph = toy.ToyGraph(edges=(toy.ToyEdge(0, 1, ((0, 0), (100, 0)), time_s=580.0 * k,
                                                cost_base=580.0 * k, osmid=(1,)),))
        got = toy.evaluate(graph, (0.0, 10.0), [(100.0, 20.0)]).objective1_s
        expect = math.fsum((580.0 * k, 30.0 / 1.26))
        assert got == pytest.approx(expect, rel=0, abs=1e-9), (
            f"at scale {k}: {got!r}, not {expect!r}"
        )


def test_the_attachment_can_switch_under_scaling_with_the_route_unchanged():
    """Pass-23 F2's lesson, rebuilt after revision 9 removed its original witness.

    The lesson is that route and destination equality do **not** establish that the selected journey
    held, so they are the wrong condition for the affinity law. That is still true, but the input
    pass 23 used no longer exhibits it: it relied on two candidates **on one record** 0.005 m apart,
    which is exactly the per-segment artefact revision 9 removed —
    `test_subdivision_no_longer_moves_the_answer_on_a_straight_edge` is the other side of that coin.

    The phenomenon is reached instead where the band is **normative**: across records. Two records
    share an `osmid` and a 100 m length, so `_route`'s `(orientation, osmid, length)` reduction is
    identical, while their origin residuals are 0.01 m and 0.0 — both inside the band across records
    — so their connector intercepts differ. One carries the smaller network weight and the larger
    connector, so the two lines **cross** inside the scale range.
    """
    graph = toy.ToyGraph(edges=(
        toy.ToyEdge(0, 1, ((0, 0.01), (100, 0.01)), time_s=1.0, cost_base=1.0, osmid=(7,),
                    oneway=True),
        toy.ToyEdge(2, 3, ((0, 0.0), (100, 0.0)), time_s=1.0025, cost_base=1.0025, osmid=(7,),
                    oneway=True),
    ))
    scenario = Scenario("f2-rebuilt", graph, (0.0, 0.0), ((100.0, 0.005),))
    assert scenario.run().origin_candidates == 2, "two candidates, on two different records"
    assert scenario.run().n_journeys > 1
    points = [answers(scale_weights(scenario, k)) for k in SCALE_POINTS]
    assert len({p["objective1_route"] for p in points}) == 1, "the route reduction is unchanged"
    assert len({p["objective1_destination_id"] for p in points}) == 1, "the destination too"
    lo, mid, hi = SCALE_POINTS
    first = (points[1]["objective1_s"] - points[0]["objective1_s"]) / (mid - lo)
    second = (points[2]["objective1_s"] - points[1]["objective1_s"]) / (hi - mid)
    # Yet the slopes differ, because the attachment switched under a held route and destination.
    assert abs(first - second) > 1e-6, (first, second)


def test_subdivision_moves_this_answer_and_that_is_a_declared_consequence():
    """Design revision 10's convention, pinned as a **disclosure** rather than an invariance claim.

    Inserting a vertex that changes no geometry adds a candidate and moves this answer. One one-way
    edge `(0,0)→(100,0)` of time/cost 1199.95 with the origin at `(49.995,0)`: as drawn it reports
    600.0349975000 s; with the midpoint `(50,0)` inserted, the new segment's clamped start sits
    0.005 m away, inside the band, and it reports 599.9789682540 s. That flips an **exact ten-minute
    comparator** verdict.

    Revision 9 removed this and was reverted, which is the part worth not misremembering: the revert
    was not an improvement on this axis. Revision 9's per-record exact filter discarded genuine
    geometric ties and made the answer depend on record segmentation instead, so revision 10 takes
    this sensitivity back **knowingly**, as the price of a simpler convention whose consequences are
    stated. Which convention is right is a prevalence question on the real graph, unmeasured.

    Pass-26's qualification was that **both values round to the same whole minute**, so the flip
    was a comparator-verdict flip and not necessarily a flip in what the product ships.

    **That qualification died with the encoding change on 2026-11-09, and the honest reading is now
    the harsher one.** `encode_minutes` rounds up, so 600.0349975 s encodes to 11 and 599.9789683 s
    to 10: the convention sensitivity reaches the shipped region. Revision 10 took this sensitivity
    back *knowingly* as the price of a simpler convention, and the price just went up -- it is no
    longer absorbed by rounding. Which convention is right remains a prevalence question on the real
    graph, and it is now a more urgent one.

    The old assertion also used Python's `round` rather than `encode_minutes`, so it was testing a
    reimplementation of the encoder and would have kept passing after the encoder changed. It calls
    the real one now (pass 28).
    """
    def at(geometry):
        graph = toy.ToyGraph(edges=(toy.ToyEdge(0, 1, geometry, time_s=1199.95, cost_base=1199.95,
                                                osmid=(1,), oneway=True),))
        return toy.evaluate(graph, (49.995, 0.0), [(100.0, 0.0)])

    drawn = at(((0, 0), (100, 0)))
    split = at(((0, 0), (50, 0), (100, 0)))
    assert drawn.origin_candidates == 1
    assert split.origin_candidates == 2, "the inserted vertex adds a candidate under this convention"
    assert drawn.objective1_s == pytest.approx(600.0349975000001, rel=0, abs=1e-9)
    assert split.objective1_s == pytest.approx(599.9789682539683, rel=0, abs=1e-9)
    # the exact comparator verdict flips ...
    assert (drawn.objective1_s <= 600.0) != (split.objective1_s <= 600.0)
    # ... and under `ceil` the shipped whole-minute encoding flips with it, where `rint` hid it.
    enc = encode_minutes([drawn.objective1_s, split.objective1_s])
    assert list(enc) == [11, 10], f"the encoded minutes moved: {list(enc)}"
    assert (enc[0] <= 10) != (enc[1] <= 10), "a minute-only client no longer hides the flip"


def test_revision_9_discarded_a_genuine_geometric_tie():
    """Pass-24 F1, as the reason revision 9 was reverted. Verified against exact rational arithmetic.

    One record whose first and last segments lie on `3x + 4y = 5` and `3x + 4y = -5`. Both arms are
    at exact squared distance **1** from the origin — a genuine tie — but `hypot` computes
    0.9999999999999999 and 1.0, one ulp apart. Revision 9's exact per-record filter kept only the
    first and reported **996.7640294933123 s FAIL**; keeping both reports **16.912 s PASS**, because
    the second arm leaves only 8 m of network travel.

    Under revision 10's convention the band admits both, so the tie survives here. That is a
    consequence of the band being 0.01 m and not a guarantee from the arithmetic — the third bullet
    on `nearest_on_graph` says so.
    """
    from fractions import Fraction as F
    geom = ((-1, 2), (195, -145), (189, -143), (-7, 4))
    # exact rational clamped point-to-segment squared distance from (0,0)
    def exact_sq(a, b):
        ax, ay, bx, by = F(a[0]), F(a[1]), F(b[0]), F(b[1])
        dx, dy = bx - ax, by - ay
        t = max(F(0), min(F(1), (-ax * dx - ay * dy) / (dx * dx + dy * dy)))
        return (ax + t * dx) ** 2 + (ay + t * dy) ** 2

    assert exact_sq(geom[0], geom[1]) == 1, "first arm is exactly 1 m away"
    assert exact_sq(geom[2], geom[3]) == 1, "last arm is exactly 1 m away"

    graph = toy.ToyGraph(edges=(toy.ToyEdge(0, 1, geom, time_s=1000.0, cost_base=1000.0,
                                            osmid=(1,), oneway=True),))
    found = toy.nearest_on_graph(graph, (0.0, 0.0), cap_m=200.0)
    # the computed residuals differ by one ulp, which is why an exact filter on them was wrong
    residuals = sorted(c.residual_m for c in found.candidates)
    assert len(found.candidates) == 2, "revision 10's band keeps both arms"
    assert residuals[0] == 0.9999999999999999 and residuals[1] == 1.0
    assert math.nextafter(residuals[0], math.inf) == residuals[1], "adjacent binary64 values"
    r = toy.evaluate(graph, (0.0, 0.0), [(-7.0, 4.0)])
    assert r.objective1_s == pytest.approx(16.912135995005965, rel=0, abs=1e-9)


def test_revision_9_made_the_answer_depend_on_record_segmentation():
    """Pass-24 F2, the second reason revision 9 was reverted.

    A pure degree-two split of one straight road into two records, with weights apportioned
    proportionally and the same legal traversals, changed the answer under revision 9:
    600.0349975000001 s FAIL on one record against 599.9789682539683 s PASS on two. Revision 10's
    convention gives the **same** answer for the one-record-with-midpoint and two-record forms,
    because both expose the clamped start at 50 m — so on this axis the reverted rule is the more
    representation-consistent of the two.
    """
    one = toy.ToyGraph(edges=(toy.ToyEdge(0, 1, ((0, 0), (50, 0), (100, 0)), time_s=1199.95,
                                          cost_base=1199.95, osmid=(1,), oneway=True),))
    two = toy.ToyGraph(edges=(
        toy.ToyEdge(0, 1, ((0, 0), (50, 0)), time_s=599.975, cost_base=599.975, osmid=(1,),
                    oneway=True),
        toy.ToyEdge(1, 2, ((50, 0), (100, 0)), time_s=599.975, cost_base=599.975, osmid=(1,),
                    oneway=True),
    ))
    a = toy.evaluate(one, (49.995, 0.0), [(100.0, 0.0)])
    b = toy.evaluate(two, (49.995, 0.0), [(100.0, 0.0)])
    assert a.objective1_s == pytest.approx(b.objective1_s, rel=0, abs=1e-9), (
        "the two representations of one road must agree under this convention"
    )
    assert a.origin_candidates == b.origin_candidates == 2


def test_exact_equidistance_within_one_record_still_yields_both_positions():
    """The case §2.2 used to cite as its reason for per-segment minima — and the measurement that
    showed the reason was false.

    An exact-minimum filter keeps **every** position achieving the minimum, so genuine equidistance
    survives it. On `(0,1),(200,1),(200,-1),(0,-1)` from `(0,0)` the two arms are both exactly 1 m
    away, at arclengths 0 and 402, and both are retained. The reported answer is the same under the
    amended rule and the superseded one, which is part of why the amendment cost nothing.
    """
    graph = toy.ToyGraph(edges=(
        toy.ToyEdge(0, 1, ((0, 1.0), (200, 1.0), (200, -1.0), (0, -1.0)), time_s=1000.0,
                    cost_base=1000.0, osmid=(1,), oneway=True),))
    found = toy.nearest_on_graph(graph, (0.0, 0.0), cap_m=200.0)
    assert len(found.candidates) == 2, "both exactly-equidistant arms are candidates"
    assert [round(c.arclength_m, 2) for c in found.candidates] == [0.0, 402.0]
    assert all(c.residual_m == pytest.approx(1.0, rel=0, abs=1e-12) for c in found.candidates)
    r = toy.evaluate(graph, (0.0, 0.0), [(0.0, -1.0)])
    assert r.objective1_s == pytest.approx(0.7936507936507936, rel=0, abs=1e-12)


def test_both_connectors_are_in_all_four_reported_numbers():
    """The absolute anchor that does what the intercept check was wrongly credited with — and now
    asserts all four of the outputs it claims to cover.

    Pass-23 F8: the selection anchor below has a **zero origin connector**, and the destination
    objective 2 selects has a **zero destination connector**, so a wrapper replacing
    `objective1_cost` and `objective2_s` with their network-only values passed it untouched. Two of
    the four claimed inclusions were never asserted.

    One straight 100 m edge of time/cost 580, origin 10 m off one end and destination 20 m off the
    other, so both residuals are non-zero and every reported number must be
    `580 + 30/1.26` = **603.8095238095 s**. Network-only would report 580 — objective 2 from a
    ten-minute FAIL to a PASS — and with no alternative destination, selection cannot reveal it
    indirectly.
    """
    graph = toy.ToyGraph(edges=(
        toy.ToyEdge(0, 1, ((0, 0), (100, 0)), time_s=580.0, cost_base=580.0, osmid=(1,)),))
    r = toy.evaluate(graph, (0.0, 10.0), [(100.0, 20.0)])
    want = math.fsum((580.0, 30.0 / 1.26))
    assert want == pytest.approx(603.8095238095238, rel=0, abs=1e-9)
    for name in ("objective1_s", "objective1_cost", "objective2_s", "objective2_cost"):
        assert getattr(r, name) == pytest.approx(want, rel=0, abs=1e-9), name


def test_the_connector_is_in_the_cost_the_second_objective_selects_on():
    """The selection anchor, which is the one the historical connector-free-cost mutant fails.

    Two destinations, one reached over a 100 m connector and one with none. The own costs are
    `10 + 100/1.26` = 89.3650793651 and 20, so objective 2 must select the second and report
    **650 s**; omitting the connector from cost selects the first and reports 89.3650793651 s,
    turning FAIL into PASS at ten minutes.
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
    """Design revision 10's candidate convention is per polyline **segment**, so inserting a vertex
    can add a candidate. Asserting invariance would be asserting a different design.

    So this records the **signature** of where subdivision changes something, and
    `SUBDIVISION_DIVERGES_ON` names it. A change in either direction is information: one more entry
    means a new sensitivity, one fewer means the convention moved.

    Two entries today. `zero_length_segment` perturbs provenance only — its midpoint becomes a third
    vertex at the same position, with the reported time unchanged. `subdivision_sensitive` moves the
    **answer**, 600.0349975000001 s to 599.9789682539683 s, which flips an exact ten-minute
    comparator verdict — and, since the encoder started rounding up, flips the encoded minute with
    it (11 against 10). That one is the input revision 9 was adopted to fix and revision 10
    knowingly took back; see `nearest_on_graph`. Production snapping does not exhibit it, because it
    projects onto the whole edge geometry.
    """
    assert "split_segments" in NOT_PRESERVING
    divergences = dict(measure_split_divergence())
    assert set(divergences) == SUBDIVISION_DIVERGES_ON, (
        f"subdivision now diverges on {sorted(divergences)} — if that is intended, record why in "
        "SUBDIVISION_DIVERGES_ON; if not, it is a finding"
    )
    assert set(divergences["zero_length_segment"]) == {"origin_candidates"}, (
        "the zero-length case must still perturb provenance only"
    )

    # Every other scenario preserves every answer, which is what makes the two entries above a
    # signature rather than a shrug.
    for s in SCENARIOS:
        if s.name in SUBDIVISION_DIVERGES_ON:
            continue
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


def test_the_optimum_is_found_wherever_it_sits_in_the_destination_list():
    """Destination cardinality, the dimension pass-23 F1 walked through.

    A uniform `destinations[:4]` truncation in `journeys` passed every one of the 1,040 tests,
    because the largest destination list any oracle call received was **three**. Eligibility still
    examined all of them, so the eligible set looked right; only enumeration was cut, and every
    journey it did return was correct.

    A positional truncation is invisible to every relative invariant too — both sides of a transform
    are equally truncated — so this is anchored, like hop depth. Five spokes, four of them 1000 s
    and one 1 s, with the fast one at each end of the list in turn.
    """
    for name, want in (("five_spokes_best_last", "e"), ("five_spokes_best_first", "a")):
        scenario = next(s for s in SCENARIOS if s.name == name)
        r = scenario.run()
        assert r.objective1_s == pytest.approx(1.0, rel=0, abs=1e-9), name
        assert r.objective1_destination_id == want, name
        assert len(r.eligible) == 5, f"{name}: eligibility must see all five"


def test_identity_does_not_depend_on_absolute_position():
    """Pass-23 F4, which is the evidence the weakened translate comparison discards.

    An identity rule forcing orientation 0 outside a coordinate box passed all 527 conformance,
    invariant and mutation-guard tests. Every other identity anchor sat near the origin, and the
    route-legality check recomputes identities with the same function, so it compared wrong against
    wrong. Excluding orientation under `translate` was defended as costing no coverage; it does, for
    exactly the defects that only appear far from the origin.

    A reverse traversal of a left-to-right edge has orientation 1 wherever the edge is.
    """
    for dx, dy in ((0.0, 0.0), (12345.678, -98765.432), (-987654.321, 654321.987)):
        edge = toy.ToyEdge(0, 1, ((dx, dy), (dx + 100.0, dy)), time_s=1.0, cost_base=1.0,
                           osmid=(7,))
        assert toy.directed_identity(edge, forward=True)[3] == 0, (dx, dy)
        assert toy.directed_identity(edge, forward=False)[3] == 1, (dx, dy)


def test_a_non_finite_answer_is_never_equal_to_itself():
    """Pass-23 F6: putting exact equality first let equal non-finite values through.

    `differences` was documented as treating a non-finite value as always a difference, and it was
    not: equality caught two infinities and object identity caught a shared NaN, so an
    implementation returning the same non-result across representations passed the helper. An
    infinite reported time is not an unchanged answer, it is not an answer.
    """
    inf, nan = float("inf"), float("nan")
    assert differences({"objective1_s": inf}, {"objective1_s": inf})
    assert differences({"objective1_s": nan}, {"objective1_s": nan})
    assert differences({"objective1_s": 100.0}, {"objective1_s": inf})
    # and the repair for identical finite values at a threshold still holds
    assert not differences({"objective1_s": 600.0}, {"objective1_s": 600.0})
    # `None` is a missing value, not a non-finite one, and two missing values agree
    assert not differences({"objective1_s": None}, {"objective1_s": None})
    assert differences({"objective1_s": None}, {"objective1_s": 100.0})


def test_a_seconds_tolerance_compares_verdicts_rather_than_a_neighbourhood():
    """Pass-23 F7's other half: requiring the whole `+/-tol` neighbourhood to be verdict-clean
    rejects pairs that agree on every verdict.

    600.0000000010021 s and 600.0000000009976 s differ by 4.5e-12 s and are both FAIL at ten
    minutes. Comparing the predicates the two values actually produce accepts them; requiring a
    clean neighbourhood around each refuses them, which is a stronger property than the comparison
    needs.
    """
    a, b = 600.0000000010021, 600.0000000009976
    assert not differences({"objective1_s": a}, {"objective1_s": b})
    # and a pair that genuinely straddles ten minutes is still a difference
    assert differences({"objective1_s": 599.9999999999}, {"objective1_s": 600.0000000001})


# --------------------------------------------------------------------------------------------
# The admissible **numerical** domain, design §12 item 3: "finite constructor fields are not a
# domain". Each of these three was reproduced against the committed oracle before the bounds were
# written, and each produced a wrong answer rather than an error.
# --------------------------------------------------------------------------------------------

def test_the_numerical_domain_rejects_a_segment_whose_square_underflows():
    """A `(0,0) -> (1e-200,0)` segment has a finite, nonzero length whose **square** underflows to
    zero. `_segment_nearest` then took its zero-length branch, attached the destination at the
    segment start, and reported 7.936507936507936e-201 s where the endpoint-to-endpoint 1,000 s is
    required — PASS against FAIL on a graph with one edge."""
    with pytest.raises(ValueError, match="between zero and the smallest admissible"):
        toy.ToyEdge(0, 1, ((0.0, 0.0), (1e-200, 0.0)), time_s=1000.0, cost_base=1000.0,
                    osmid=(1,), oneway=True)

    # Exactly zero stays admissible: §2.2's zero-span traversals are a declared case with their own
    # convention, not a degenerate accident, so the bound must not swallow them.
    toy.ToyEdge(0, 1, ((0.0, 0.0), (0.0, 0.0)), time_s=1.0, cost_base=1.0, osmid=(1,))
    # And the bound is a floor on segments, not on edges: a long edge containing a tiny segment is
    # just as wrong, so the check runs per segment.
    with pytest.raises(ValueError, match="between zero and the smallest admissible"):
        toy.ToyEdge(0, 1, ((0.0, 0.0), (1e-200, 0.0), (100.0, 0.0)), time_s=1.0, cost_base=1.0,
                    osmid=(1,))


def test_the_numerical_domain_bounds_the_formed_cost_term_not_just_the_fields():
    """`cost_base = 1e308` with `penalty = 1e308` passes a per-field finite check and sums to
    `inf`. §2.4 freezes `f * (cost_base + penalty)` as **one term**, so that sum is the quantity the
    arithmetic handles: at a zero-span traversal it reached `0 * inf` and raised from an empty
    `min()` instead of returning the zero §2.4 promises."""
    with pytest.raises(ValueError, match=r"cost_base \+ penalty must be finite"):
        toy.ToyEdge(0, 1, ((0.0, 0.0), (100.0, 0.0)), time_s=1.0, cost_base=1e308, penalty=1e308,
                    osmid=(1,))
    # Each field alone is fine, which is exactly why a per-field check was not a domain.
    toy.ToyEdge(0, 1, ((0.0, 0.0), (100.0, 0.0)), time_s=1.0, cost_base=1e308, osmid=(1,))
    toy.ToyEdge(0, 1, ((0.0, 0.0), (100.0, 0.0)), time_s=1.0, cost_base=0.0, penalty=1e308,
                osmid=(1,))


def test_the_numerical_domain_bounds_coordinate_magnitude():
    """The same squaring that underflows at 1e-200 overflows at the top, so the domain is bounded
    both ways. 1e7 m contains any UTM easting or northing."""
    toy.ToyEdge(0, 1, ((0.0, 0.0), (toy.COORD_ABS_MAX, 0.0)), time_s=1.0, cost_base=1.0,
                osmid=(1,))
    with pytest.raises(ValueError, match="outside the admissible domain"):
        toy.ToyEdge(0, 1, ((0.0, 0.0), (toy.COORD_ABS_MAX * 2, 0.0)), time_s=1.0, cost_base=1.0,
                    osmid=(1,))


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_a_non_finite_query_coordinate_is_rejected_at_every_public_entry(bad):
    """The one that mattered most: query coordinates were not validated at all, so a NaN origin
    returned zero candidates and no objective — **indistinguishable from a genuine absence of any
    route**. An absence that was really a malformed input is the error class this stage exists to
    prevent, and it is the same defect as `GridSpec.cell_for_lonlat` returning `None` for a NaN.
    """
    g = toy.ToyGraph(edges=(toy.ToyEdge(0, 1, ((0.0, 0.0), (100.0, 0.0)), time_s=60.0,
                                        cost_base=60.0, osmid=(1,), oneway=True),))
    for call in (
        lambda: toy.evaluate(g, (bad, 0.0), [(100.0, 0.0)]),
        lambda: toy.journeys(g, (bad, 0.0), [(100.0, 0.0)]),
        lambda: toy.nearest_on_graph(g, (bad, 0.0), cap_m=toy.MAX_ACCESS_M),
        lambda: toy.attachments(g, (bad, 0.0), cap_m=toy.POI_SNAP_MAX_M),
        lambda: toy.evaluate(g, (0.0, 0.0), [(bad, 0.0)]),
        lambda: toy.journeys(g, (0.0, 0.0), [(bad, 0.0)]),
    ):
        with pytest.raises(ValueError, match="must be finite"):
            call()


def test_a_bad_destination_is_named_by_its_index():
    """Because the first version surfaced it as "the query point" from whichever inner call reached
    it first, which does not say which of a list of destinations is wrong."""
    g = toy.ToyGraph(edges=(toy.ToyEdge(0, 1, ((0.0, 0.0), (100.0, 0.0)), time_s=60.0,
                                        cost_base=60.0, osmid=(1,), oneway=True),))
    with pytest.raises(ValueError, match="destination 1 must be finite"):
        toy.evaluate(g, (0.0, 0.0), [(100.0, 0.0), (float("nan"), 0.0)])


def test_an_out_of_domain_query_coordinate_is_rejected_too():
    g = toy.ToyGraph(edges=(toy.ToyEdge(0, 1, ((0.0, 0.0), (100.0, 0.0)), time_s=60.0,
                                        cost_base=60.0, osmid=(1,), oneway=True),))
    with pytest.raises(ValueError, match="outside the admissible domain"):
        toy.evaluate(g, (toy.COORD_ABS_MAX * 2, 0.0), [(100.0, 0.0)])


def test_the_ranking_does_not_select_a_unique_traversal():
    """Design §2.4's weakened uniqueness promise, revision 11 (§12 item 2, pass-22).

    A canonical directed-edge identity is `(start, end, geometry key, orientation, osmid, length)`
    and carries **no arclength interval**, so every partial traversal of one edge shares one
    identity. On a zero-weight edge they also share time 0 and cost 0, so they tie on all six keys —
    including the cost key revision 11 added. Three journeys, one rank key.

    This is pinned because the design now *relies* on it being true: §2.4 promises a unique reported
    answer and a unique route identity and explicitly not a unique traversal, and T10 owes its own
    reconstruction rule as a consequence. If a future change made these keys distinguish the three,
    the promise could be strengthened again — and this test is how anyone would notice.
    """
    # Codex pass 30's witness, which replaces a weaker one of mine. Mine used three *different*
    # origin/destination pairs on a straight edge, so it showed that three separate queries share a
    # key — not that one query has an ambiguous answer. This geometry self-crosses, so a **single**
    # query has three tied traversals and the ambiguity is in one answer.
    edge = toy.ToyEdge(0, 1, ((0, 0), (100, 0), (100, 100), (0, 100), (0, 0), (100, 0)),
                       time_s=0.0, cost_base=0.0, osmid=(1,), oneway=True)
    graph = toy.ToyGraph(edges=(edge,))

    js = toy.journeys(graph, (25.0, 0.0), [(75.0, 0.0)])
    assert len(js) == 3, f"expected three tied traversals of one query, got {len(js)}"
    assert len({j.rank_key for j in js}) == 1, "the keys distinguish the traversals after all"

    # The identity is what lacks the interval, which is the cause rather than the symptom: it has a
    # fixed six-field shape and none of those fields is an arclength or a pair of them.
    identity = toy.directed_identity(edge, forward=True)
    assert len(identity) == 6, f"identity shape changed to {len(identity)} fields; re-check this"
    start, end, geom_key, orientation, osmid, length = identity
    assert (start, end) == (0, 1) and orientation in (0, 1) and osmid == (1,)
    assert isinstance(length, float), "length is the whole edge, not a traversed extent"
    assert isinstance(geom_key, tuple), "the geometry key is the whole geometry, not an interval"


def test_the_domain_bounds_the_graph_aggregate_not_only_each_edge():
    """Bounding each edge's formed cost term still let a journey *total* overflow: one edge with
    `time_s = 1e308` and the origin on the destination made `evaluate` raise
    `OverflowError: intermediate overflow in fsum` where the correct optimum is **zero** (Codex
    pass 30). Per-field finiteness cannot give that guarantee; only the sum can."""
    with pytest.raises(ValueError, match="total time_s"):
        toy.ToyGraph(edges=(toy.ToyEdge(0, 1, ((0.0, 0.0), (1000.0, 0.0)), time_s=1e308,
                                        cost_base=1.0, osmid=(1,)),))
    with pytest.raises(ValueError, match="total cost"):
        toy.ToyGraph(edges=(toy.ToyEdge(0, 1, ((0.0, 0.0), (1000.0, 0.0)), time_s=1.0,
                                        cost_base=1e308, osmid=(1,)),))
    # The bound is on the aggregate, so several edges that are each comfortable can still fail it.
    halves = tuple(toy.ToyEdge(i, i + 1, ((100.0 * i, 0.0), (100.0 * (i + 1), 0.0)),
                               time_s=6e307, cost_base=1.0, osmid=(i + 1,)) for i in range(2))
    with pytest.raises(ValueError, match="total time_s"):
        toy.ToyGraph(edges=halves)
    # And an ordinary graph is unaffected.
    toy.ToyGraph(edges=(toy.ToyEdge(0, 1, ((0.0, 0.0), (100.0, 0.0)), time_s=60.0, cost_base=60.0,
                                    osmid=(1,)),))


def test_a_foreign_numeric_type_cannot_decide_the_domain_check():
    """`abs(numpy.int64(-2**63))` overflows to itself and stays negative, so it passed
    `> COORD_ABS_MAX` and the point reached the geometry as -9.2e18 (Codex pass 30). The domain is
    stated in binary64, so the conversion has to happen **before** the comparison, not after."""
    numpy = pytest.importorskip("numpy")
    worst = numpy.int64(-(2 ** 63))
    with numpy.errstate(over="ignore"):      # the overflow IS the premise, so do not warn on it
        assert abs(worst) < 0, "numpy no longer overflows here; this test's premise is gone"

    with pytest.raises(ValueError, match="outside the admissible domain"):
        toy.require_query_point((worst, numpy.int64(0)), "the origin")
    with pytest.raises(ValueError, match="outside the admissible domain"):
        toy.ToyEdge(0, 1, ((worst, 0), (100.0, 0.0)), time_s=1.0, cost_base=1.0, osmid=(1,))

    # An in-range numpy scalar is still accepted, converted to the declared representation.
    assert toy.require_query_point((numpy.float64(5.0), numpy.int32(7)), "p") == (5.0, 7.0)
    assert all(isinstance(v, float) for v in toy.require_query_point((numpy.int32(1), 2), "p"))


def test_the_ranking_does_not_determine_the_reported_decomposition():
    """The companion to the traversal ambiguity, and the reason §2.4's promise had to be enumerated
    rather than summarised as "every number this design reports".

    Two records sharing an `osmid`, one straight and one imperceptibly curved, carry weights chosen
    so that both winners tie on **every** rank key and report the same total. Reordering the records
    changes the reported **network** seconds — 1.0 against 0.9968253968355556 — because the
    connector/network split depends on which record won, and the keys do not choose between them
    (Codex pass 30).
    """
    straight = toy.ToyEdge(0, 1, ((0, 0), (50, 0), (100, 0)), time_s=2.0, cost_base=2.0,
                           osmid=(7,))
    curved = toy.ToyEdge(0, 1, ((0, 0), (50, 0.004), (100, 0)), time_s=1.9936507809117465,
                         cost_base=1.9936507809117465, osmid=(7,))

    winners = []
    for order in ((straight, curved), (curved, straight)):
        js = toy.journeys(toy.ToyGraph(edges=order), (25.0, 0.0), [(75.0, 0.0)])
        winners.append(min(js, key=lambda j: j.rank_key))

    assert len({w.rank_key for w in winners}) == 1, "the keys do separate them; promise can be raised"
    assert winners[0].time_s == winners[1].time_s == 1.0, "the total is determined, as promised"
    assert winners[0].network_s != winners[1].network_s, "the decomposition is determined after all"
    assert winners[0].network_s == 1.0
    assert winners[1].network_s == pytest.approx(0.9968253968355556, abs=1e-15)
