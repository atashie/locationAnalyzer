"""T4 — the conformance suite.

Three things are tested here, and the third is the one that matters:

1. every case's **hand arithmetic agrees with the exhaustive oracle**, two routes neither of which
   is the reference comparator (which does not exist yet);
2. the corpus **covers every rule** the execution plan's T3 table names, with no silent gaps;
3. **deliberately wrong implementations are caught.** Pass 15 produced a wrong Clopper-Pearson that
   satisfied every fixture then stated; pass 18 produced two more that satisfied the replacements;
   and the first sampling tests admitted a `(u, u)` offset draw with correct marginals and
   correlation 1. A suite that cannot be shown to reject a specific wrong answer is a regression
   baseline, not evidence. So this file builds wrong comparators and shows which case kills each.

**Pass 20 answered "can a wrong comparator pass the whole corpus?" with yes, twice.** A strict-cap
implementation — `< cap` rather than `<= cap` — passed all 78 tests, because no case sat on a
boundary. And the oracle itself omitted both connectors from objective 2's **selection cost**, which
no case separated because none combined unequal connectors with different destinations. Five cases
and the mutants below close those, and the lesson is recorded: the corpus is evidence only of the
dimensions it actually varies.
"""

from __future__ import annotations

import dataclasses
import math

import pytest

from locfinder.measure import conformance as cf
from locfinder.measure import toy
from locfinder.measure.conformance_cases import (
    CASES, RULE_COVERAGE, RULES_TESTED_WITHOUT_A_GRAPH,
)
from locfinder.status import Outcome
from locfinder.traveltime.speeds import access_speed_mps, max_speed_mps

ALL = pytest.mark.parametrize("case", CASES, ids=[c.name for c in CASES])


# ----------------------------------------------------------------------------- the two routes agree


@ALL
def test_hand_arithmetic_and_the_exhaustive_oracle_agree(case):
    """The core obligation. `check` compares the hand-derived value in the case against
    `toy.evaluate`, which enumerates every attachment candidate, entry, exit and simple path.

    Neither route calls the reference comparator. The plan requires this independence to be
    *evidenced*: the evidence is that the two routes are different algorithms and that one of them
    already rejected a hand value — `same_edge_direct_traversal_is_a_candidate_and_loses` was
    written with one origin candidate and has two, because a node origin attaches to every incident
    edge.
    """
    assert cf.check(case) == []


@ALL
def test_each_case_carries_its_derivation_and_a_wrong_answer_it_separates(case):
    """A case without a derivation is an unexplained constant, and a case that names no wrong answer
    separates nothing. `rejects` is prose for the reader; the numbers are checked by `check`."""
    assert len(case.derivation) > 80, "the derivation must show the arithmetic, not restate it"
    assert case.provenance
    assert case.rejects, "name the wrong answer this case excludes"
    pins_a_number = bool(case.expected.rejected_objective1_s
                         or case.expected.rejected_objective2_s)
    pins_a_structure = bool(case.expected.no_finite_time
                            or case.expected.eligible is not None
                            or case.expected.origin_candidates is not None)
    assert pins_a_number or pins_a_structure


@ALL
def test_the_answer_does_not_depend_on_edge_insertion_order(case):
    """Design §2.4 exists because the current code is non-deterministic: with equal-cost coincident
    alternatives of time 10 and 1, reversing insertion order changes the reported time from 10 to 1.

    Reversing every case's edge tuple must change nothing.
    """
    reversed_graph = toy.ToyGraph(edges=tuple(reversed(case.graph.edges)))
    a = case.run()
    b = toy.evaluate(reversed_graph, case.origin, list(case.destinations))
    for field in ("objective1_s", "objective2_s", "objective2_cost"):
        first, second = getattr(a, field), getattr(b, field)
        if first is None or second is None:
            assert first is None and second is None, f"{field}: {first!r} against {second!r}"
        else:
            assert first == pytest.approx(second, rel=0, abs=cf.TIME_TOL_S), field
    assert a.origin_candidates == b.origin_candidates
    assert a.eligible == b.eligible


# ----------------------------------------------------------------------------- coverage, not belief


def test_every_rule_the_plan_names_resolves_to_real_cases():
    names = {c.name for c in CASES}
    for rule, case_names in RULE_COVERAGE.items():
        assert case_names, f"{rule} claims coverage with no case"
        for n in case_names:
            assert n in names, f"{rule} names a case that does not exist: {n}"


def test_every_case_is_claimed_by_a_rule():
    """The other direction: a case nobody claims is a case nobody reviewed against the design."""
    claimed = {n for names in RULE_COVERAGE.values() for n in names}
    orphans = {c.name for c in CASES} - claimed
    assert orphans == set(), f"cases claimed by no rule: {sorted(orphans)}"


def test_the_rules_with_no_graph_case_say_where_they_are_tested():
    """Design §2 rules that a constructed graph cannot express are recorded with their location,
    including the one that is deliberately **not** tested here."""
    assert RULES_TESTED_WITHOUT_A_GRAPH
    for rule, where in RULES_TESTED_WITHOUT_A_GRAPH.items():
        assert where, rule
    untested = [r for r, w in RULES_TESTED_WITHOUT_A_GRAPH.items() if "NOT TESTED" in w]
    assert len(untested) == 1 and "independent engine" in untested[0], (
        "exactly one rule is knowingly untested here — the independent engine's connector charge, "
        "which depends on Valhalla's observed correlation position. A second one appearing means a "
        "gap was opened without a decision."
    )


# ----------------------------------------------------------------------------- pinned constants


def test_the_oracle_speeds_and_caps_are_the_productions():
    """`toy.py` restates the access speed as a literal rather than importing it, so that the oracle
    does not silently move when the production constant does. This test is what makes that safe.

    `max_speed_mps` is deliberately **different** and is not the connector speed: 1.40 against 1.26.
    Confusing them is a recorded error — the off-network bound divides by 1.40, and reasoning about
    it with 1.26 gave proven-over distances that were wrong by 11%.
    """
    assert toy.ACCESS_SPEED_MPS == access_speed_mps("walk") == 1.26
    assert max_speed_mps("walk") == 1.4
    assert toy.ACCESS_SPEED_MPS != max_speed_mps("walk")
    assert toy.MAX_ACCESS_M == 200.0
    assert toy.POI_SNAP_MAX_M == 300.0
    assert toy.ATTACH_TIE_M == 0.01
    assert toy.ROUND_DP == 2


# ----------------------------------------------------------------------------- the tolerance


@ALL
def test_the_tolerance_is_decision_irrelevant_for_every_pinned_time(case):
    for t in (case.expected.objective1_s, case.expected.objective2_s):
        if t is not None:
            assert cf.tolerance_is_decision_irrelevant(t, thresholds_min=case.thresholds_min)


def test_a_time_sitting_on_a_threshold_is_refused_not_admitted():
    """The defect pass 18 found against T1 was a tolerance wide enough to hide a decision flip. The
    protection is not a smaller number; it is checking, per case, that the verdict cannot move.

    At exactly 600 s — ten minutes — it can: `600 - 1e-9 <= 600` is True and `600 + 1e-9 <= 600` is
    False, so the suite refuses the case instead of passing it.
    """
    assert cf.tolerance_is_decision_irrelevant(599.0)
    assert cf.tolerance_is_decision_irrelevant(601.0)
    assert not cf.tolerance_is_decision_irrelevant(600.0)

    on_threshold = dataclasses.replace(
        CASES[0], expected=dataclasses.replace(CASES[0].expected, objective1_s=600.0))
    problems = cf.check(on_threshold)
    assert any("decision-safe" in p for p in problems)


def test_the_tolerance_is_far_above_float_association_and_far_below_a_decision():
    """Both halves of the argument, as numbers. The oracle sums `1/1.26 + 100 + 1/1.26` while the
    hand derivation writes `2/1.26 + 100`; they differ by 1.42e-14 s, so a tolerance is needed."""
    a = 1.0 / 1.26
    spread = abs((a + 100.0 + a) - (2.0 / 1.26 + 100.0))
    assert (a + 100.0 + a) != (2.0 / 1.26 + 100.0)
    assert spread == pytest.approx(1.42e-14, rel=0.05)
    assert spread < cf.TIME_TOL_S / 100.0, "the tolerance must clear float association by a margin"
    assert cf.TIME_TOL_S / 600.0 < 1e-11, "and be negligible against the smallest threshold"


# ----------------------------------------------------------------------------- design §2.5's bounds


def test_a_cost_limit_is_not_a_sound_bound_on_travel_time():
    """Design §2.5's blocking case. One edge of time 1 and cost 121 under a cost limit of 60 returns
    `inf`, while objective 2 returns **1 second**. Revision 3's rule would have failed *T* = 60 for a
    route that passes in one."""
    assert cf.comparator_outcome(
        threshold_s=60.0, time_s=None, search_bounded=True, exhausted=True,
        bound_metric="cost", bound_value=60.0) is cf.ComparatorOutcome.UNRESOLVED

    # the same exhaustion with a *time* bound above the threshold is a known failure
    assert cf.comparator_outcome(
        threshold_s=60.0, time_s=None, search_bounded=True, exhausted=True,
        bound_metric="time", bound_value=61.0) is cf.ComparatorOutcome.FAIL


def test_no_path_may_not_be_reported_from_a_bounded_search():
    """Exhaustiveness is a property of the invocation, not of the engine — which is why
    `status.node_reasons` takes `search_bounded` as a required keyword. A bounded search that
    exhausted its budget knows nothing."""
    assert cf.comparator_outcome(threshold_s=600.0, time_s=None, search_bounded=False,
                                 exhausted=True) is cf.ComparatorOutcome.FAIL
    assert cf.comparator_outcome(threshold_s=600.0, time_s=None, search_bounded=True,
                                 exhausted=True) is cf.ComparatorOutcome.UNRESOLVED


def test_bound_strictness_decides_the_threshold_itself():
    """`t > H` fails *T* = *H*; `t >= H` does not. `BEYOND_HORIZON`'s bound is the strict one."""
    assert cf.comparator_outcome(threshold_s=600.0, time_s=None, search_bounded=True,
                                 exhausted=False, bound_metric="time", bound_value=600.0,
                                 bound_strict=True) is cf.ComparatorOutcome.FAIL
    assert cf.comparator_outcome(threshold_s=600.0, time_s=None, search_bounded=True,
                                 exhausted=False, bound_metric="time", bound_value=600.0,
                                 bound_strict=False) is cf.ComparatorOutcome.UNRESOLVED


def test_a_finite_time_is_decided_before_any_bound_branch():
    """Design §2.5 states the finite-time branch **first**: the others are only reached when nothing
    was found. Revision 3's ordering made a found route unreachable behind a bound rule, so a time
    of 1 s arriving with a stale cost bound must still be PASS."""
    assert cf.comparator_outcome(threshold_s=60.0, time_s=1.0, search_bounded=True, exhausted=True,
                                 bound_metric="cost", bound_value=121.0) is cf.ComparatorOutcome.PASS
    assert cf.comparator_outcome(threshold_s=60.0, time_s=60.0, search_bounded=False,
                                 exhausted=True) is cf.ComparatorOutcome.PASS
    assert cf.comparator_outcome(threshold_s=60.0, time_s=60.001, search_bounded=False,
                                 exhausted=True) is cf.ComparatorOutcome.FAIL


# ----------------------------------------------------------------------------- design §7's accounting


def test_the_cross_tab_covers_all_nine_cells_and_nothing_else():
    cells = {(p, c) for p in Outcome for c in cf.ComparatorOutcome}
    assert set(cf.CROSS_TAB) == cells
    assert len(cf.CROSS_TAB) == 9
    for p in Outcome:
        for c in cf.ComparatorOutcome:
            assert isinstance(cf.classify(p, c), cf.Bucket)


def test_product_abstention_contributes_to_neither_directions_k_nor_u():
    """Revision 5's fix, in executable form. Revision 3 counted product `UNKNOWN` into E1b, which
    made the gate unreachable; abstention is E0's business and nothing else's.

    Three abstaining points — one the comparator passes, one it fails, one it cannot resolve —
    contribute 3 to `n` and `abstentions`, 2 to `unwarranted`, and **zero** to every `k` and `u`.
    """
    t = cf.tally([
        (Outcome.UNKNOWN, cf.ComparatorOutcome.PASS),
        (Outcome.UNKNOWN, cf.ComparatorOutcome.FAIL),
        (Outcome.UNKNOWN, cf.ComparatorOutcome.UNRESOLVED),
    ])
    assert (t.k_e1a, t.u_e1a, t.k_e1b, t.u_e1b) == (0, 0, 0, 0)
    assert t.n == 3 and t.abstentions == 3 and t.unwarranted == 2


def test_the_two_directions_are_counted_separately_and_nothing_is_deleted():
    """Design §7: every sampled point falls in exactly one cell, and agreements are counted —
    revision 3's three buckets omitted them."""
    pairs = [
        (Outcome.PASS, cf.ComparatorOutcome.PASS),            # agreement
        (Outcome.FAIL, cf.ComparatorOutcome.FAIL),            # agreement
        (Outcome.PASS, cf.ComparatorOutcome.FAIL),            # E1b: a false inclusion
        (Outcome.FAIL, cf.ComparatorOutcome.PASS),            # E1a: a false exclusion
        (Outcome.PASS, cf.ComparatorOutcome.UNRESOLVED),      # potential E1b
        (Outcome.FAIL, cf.ComparatorOutcome.UNRESOLVED),      # potential E1a
        (Outcome.UNKNOWN, cf.ComparatorOutcome.UNRESOLVED),   # E0
    ]
    t = cf.tally(pairs)
    assert (t.k_e1b, t.u_e1b) == (1, 1)
    assert (t.k_e1a, t.u_e1a) == (1, 1)
    assert t.agreements == 2
    assert t.n == len(pairs)
    assert t.agreements + t.k_e1a + t.u_e1a + t.k_e1b + t.u_e1b + t.abstentions == t.n


def test_an_e1a_error_is_never_counted_as_an_e1b_error():
    """The two directions have different thresholds — E1a 2.0%, E1b 1.0% — so crossing them would
    move a verdict. A product FAIL that the comparator passes is a false *exclusion*."""
    assert cf.classify(Outcome.FAIL, cf.ComparatorOutcome.PASS) is cf.Bucket.E1A
    assert cf.classify(Outcome.PASS, cf.ComparatorOutcome.FAIL) is cf.Bucket.E1B


# ----------------------------------------------------------------------------- design §2.4's identity


def test_a_reversed_traversal_is_the_same_road_but_a_different_directed_edge():
    """Design §2.4 rule 1. The geometry key is canonicalised so both directions name one physical
    road; the identity still separates them, because a one-way road's two directions are not
    interchangeable."""
    fwd = toy.ToyEdge(0, 1, ((0, 0), (50, 10), (100, 0)), time_s=1.0, cost_base=1.0, osmid=(7,))
    rev = toy.ToyEdge(1, 0, ((100, 0), (50, 10), (0, 0)), time_s=1.0, cost_base=1.0, osmid=(7,))
    assert fwd.geometry_key == rev.geometry_key
    assert fwd.identity != rev.identity


def test_two_roads_sharing_endpoints_osmid_and_length_are_still_distinct():
    """The executed §2.4 defect: `speeds._physical_key` groups by `osmid` plus length rounded to
    2 dp, so two different roads between the same nodes are *identical* to it while the attachment
    index treats them as two. `symmetrise` then suppressed both reverses as duplicates and left
    reverse weight `inf` for each.

    Under the canonical identity they are distinct, which is what stops that.
    """
    straight = toy.ToyEdge(0, 1, ((0, 0), (100, 0)), time_s=100.0, cost_base=100.0, osmid=(7,))
    broken = toy.ToyEdge(0, 1, ((0, 0), (50, 0), (100, 0)), time_s=100.0, cost_base=100.0,
                         osmid=(7,))
    physical_key = (tuple(sorted(straight.osmid)), round(straight.length_m, 2))
    assert physical_key == (tuple(sorted(broken.osmid)), round(broken.length_m, 2))
    assert straight.identity != broken.identity


def test_osmid_is_normalised_so_list_order_cannot_split_a_road():
    a = toy.ToyEdge(0, 1, ((0, 0), (100, 0)), time_s=1.0, cost_base=1.0, osmid=(7, 9))
    b = toy.ToyEdge(0, 1, ((0, 0), (100, 0)), time_s=1.0, cost_base=1.0, osmid=(9, 7))
    assert a.identity == b.identity


# ----------------------------------------------------------------------------- wrong implementations


def test_dropping_all_but_the_first_attachment_candidate_is_caught(monkeypatch):
    """Wrong implementation 1: resolve the geometric tie by taking one minimiser, which is what
    every implementation did before revision 5 and what pass-18 F7 showed is not determined by the
    stated rules.

    On `geometric_attachment_tie_keeps_every_minimiser` the two roads are disconnected, so keeping
    only the first candidate can give 1001.587 s instead of 101.587 s — PASS against FAIL at ten
    minutes.
    """
    real = toy.attachments
    monkeypatch.setattr(toy, "attachments",
                        lambda g, p, *, cap_m: real(g, p, cap_m=cap_m)[:1])

    case = next(c for c in CASES if c.name == "geometric_attachment_tie_keeps_every_minimiser")
    reversed_case = dataclasses.replace(
        case, graph=toy.ToyGraph(edges=tuple(reversed(case.graph.edges))))
    broken = cf.check(case) + cf.check(reversed_case)
    assert broken, "a one-candidate attachment must fail at least one orientation of the tie case"
    assert any("1001" in b or "origin_candidates" in b for b in broken)


def test_the_forbidden_objective2_functional_is_caught():
    """Wrong implementation 2: `min` over the **times** of cost-optimal paths, instead of the time of
    the cost-`argmin` pair. Design §2.1 forbids it: with identical engines it manufactures -9 s of
    disagreement from nothing."""
    def wrong_objective2(case):
        js = toy.journeys(case.graph, case.origin, list(case.destinations))
        best_per_destination = []
        for d in {j.destination for j in js}:
            mine = [j for j in js if j.destination == d]
            cheapest = min(j.cost for j in mine)
            best_per_destination.append(min(j.time_s for j in mine if j.cost == cheapest))
        return min(best_per_destination) if best_per_destination else None

    case = next(c for c in CASES if c.name == "objective2_is_cost_argmin_then_that_pairs_time")
    assert case.run().objective2_s == pytest.approx(10.0)
    assert wrong_objective2(case) == pytest.approx(1.0)
    assert 1.0 in case.expected.rejected_objective2_s, (
        "the case must name 1.0 as rejected, or it does not separate this implementation"
    )


def test_ignoring_the_one_way_flag_is_caught():
    """Wrong implementation 3: symmetrise everything. Design §2.2 — a partial traversal is legal
    only in a direction the edge permits, and bike and drive do not inherit walk's reverse."""
    for name, correct in (("oneway_partial_edge_routes_the_long_way_round", 240.0),
                          ("oneway_with_no_return_is_no_path_not_off_network", None)):
        case = next(c for c in CASES if c.name == name)
        symmetric = toy.ToyGraph(edges=tuple(
            dataclasses.replace(e, oneway=False) for e in case.graph.edges))
        wrong = toy.evaluate(symmetric, case.origin, list(case.destinations))

        # the illegal direct reverse traversal is 0.6 x 100 = 60 s in both graphs
        assert wrong.objective1_s == pytest.approx(60.0)
        got = case.run().objective1_s
        if correct is None:
            assert got is None, "here the wrong implementation invents a route where none exists"
        else:
            assert got == pytest.approx(correct)
            assert abs(got - 60.0) > cf.TIME_TOL_S, (
                "the case separates nothing unless the legal journey differs from the illegal "
                "shortcut: at a 5 + 5 s return the legal answer is 50 s, the shortcut loses, and a "
                "symmetrising implementation returns the correct value"
            )
            assert 60.0 in case.expected.rejected_objective1_s


def test_charging_a_penalty_on_entry_instead_of_apportioning_it_is_caught():
    """Wrong implementation 4: bill the whole restricted-access penalty on touching the edge.

    On `edge_penalties_are_apportioned_not_charged_on_entry` the 1% traversal costs 0.01 x 121 =
    **1.21** apportioned and 0.01 x 1 + 120 = **120.01** on entry. Against the open bypass at cost 5
    the two models select different destinations, so objective 2 reports 10 s or 5 s.
    """
    case = next(c for c in CASES if c.name == "edge_penalties_are_apportioned_not_charged_on_entry")
    restricted = case.graph.edges[0]
    fraction = 0.01
    apportioned = fraction * restricted.total_cost
    on_entry = fraction * restricted.cost_base + restricted.penalty
    assert apportioned == pytest.approx(1.21)
    assert on_entry == pytest.approx(120.01)

    bypass_cost = case.graph.edges[1].total_cost
    assert apportioned < bypass_cost < on_entry, "the two models must select different routes here"

    r = case.run()
    assert r.objective2_s == pytest.approx(10.0) and r.objective2_destination == 0
    assert 5.0 in case.expected.rejected_objective2_s


# ----------------------------------------------------------------------------- the oracle itself


def test_the_oracle_enumerates_rather_than_searches():
    """The oracle's independence rests on it having no shortest-path algorithm. A graph where the
    greedy first step is wrong is answered correctly: the 1 s edge leads nowhere useful and the
    100 s edge is the only route, so a time-greedy walk would report no path."""
    g = toy.ToyGraph(edges=(
        toy.ToyEdge(0, 1, ((0, 0), (1, 0)), time_s=1.0, cost_base=1.0, osmid=(1,)),
        toy.ToyEdge(0, 2, ((0, 0), (0, 100)), time_s=100.0, cost_base=100.0, osmid=(2,)),
        toy.ToyEdge(2, 3, ((0, 100), (100, 100)), time_s=1.0, cost_base=1.0, osmid=(3,)),
    ))
    r = toy.evaluate(g, (0.0, 0.0), [(100.0, 100.0)])
    assert r.objective1_s == pytest.approx(101.0)


def test_a_node_origin_attaches_to_every_incident_edge():
    """Recorded because it corrected a hand value. §2.2's tie rule keeps every minimiser, and at a
    node every incident edge is a minimiser at distance zero — so 'the attachment' is never
    singular at a junction."""
    g = toy.ToyGraph(edges=(
        toy.ToyEdge(0, 1, ((0, 0), (100, 0)), time_s=1.0, cost_base=1.0, osmid=(1,)),
        toy.ToyEdge(0, 2, ((0, 0), (0, 100)), time_s=1.0, cost_base=1.0, osmid=(2,)),
        toy.ToyEdge(0, 3, ((0, 0), (-100, 0)), time_s=1.0, cost_base=1.0, osmid=(3,)),
    ))
    assert len(toy.attachments(g, (0.0, 0.0), cap_m=toy.MAX_ACCESS_M)) == 3
    assert len(toy.attachments(g, (50.0, 0.0), cap_m=toy.MAX_ACCESS_M)) == 1


def test_a_point_outside_the_tie_window_has_one_candidate():
    """The tie window is 0.01 m. Two parallel roads 0.005 m apart in residual are both candidates;
    0.02 m apart, only the nearer is. This is the threshold the design declares, and it relocates
    rather than removes the discontinuity — recorded as a question for the design, not resolved
    here."""
    near = toy.ToyGraph(edges=(
        toy.ToyEdge(0, 1, ((0, 1.000), (100, 1.000)), time_s=1.0, cost_base=1.0, osmid=(1,)),
        toy.ToyEdge(2, 3, ((0, -1.005), (100, -1.005)), time_s=2.0, cost_base=2.0, osmid=(2,)),
    ))
    far = toy.ToyGraph(edges=(
        toy.ToyEdge(0, 1, ((0, 1.000), (100, 1.000)), time_s=1.0, cost_base=1.0, osmid=(1,)),
        toy.ToyEdge(2, 3, ((0, -1.020), (100, -1.020)), time_s=2.0, cost_base=2.0, osmid=(2,)),
    ))
    assert len(toy.attachments(near, (50.0, 0.0), cap_m=toy.MAX_ACCESS_M)) == 2
    assert len(toy.attachments(far, (50.0, 0.0), cap_m=toy.MAX_ACCESS_M)) == 1


def test_the_geometric_tie_band_does_not_let_a_candidate_past_the_cap():
    """Pass 19 asked for this explicitly: "a nearest origin candidate at 199.995 m does not
    authorise a second at 200.004 m merely because it is within the geometric tie band."

    The tie window is taken around the global minimum first and the 200 m cap applied after, so
    every retained candidate is independently inside the cap. The other order would admit the
    second road and could route the journey down it.
    """
    g = toy.ToyGraph(edges=(
        toy.ToyEdge(0, 1, ((0, 199.995), (100, 199.995)), time_s=1000.0, cost_base=1000.0,
                    osmid=(1,)),
        toy.ToyEdge(2, 3, ((0, -200.004), (100, -200.004)), time_s=1.0, cost_base=1.0, osmid=(2,)),
    ))
    kept = toy.attachments(g, (50.0, 0.0), cap_m=toy.MAX_ACCESS_M)
    assert len(kept) == 1
    assert kept[0].edge == 0, "the over-cap road must be dropped even though it is the faster one"
    assert kept[0].residual_m == pytest.approx(199.995)

    # both inside the cap: the band then does retain two
    closer = toy.ToyGraph(edges=(
        toy.ToyEdge(0, 1, ((0, 199.995), (100, 199.995)), time_s=1000.0, cost_base=1000.0,
                    osmid=(1,)),
        toy.ToyEdge(2, 3, ((0, -199.999), (100, -199.999)), time_s=1.0, cost_base=1.0, osmid=(2,)),
    ))
    assert len(toy.attachments(closer, (50.0, 0.0), cap_m=toy.MAX_ACCESS_M)) == 2


def test_the_tie_band_relocates_the_discontinuity_rather_than_removing_it():
    """Design §2.2 claims the retained-minimiser rule makes the answer "a property of the geometry
    rather than of a convention". Pass 19's F1 shows that is overstated, and this records the
    counterexample so the claim cannot be quietly restored.

    Two disconnected roads, 100 s and 1000 s, with the slow one 1 m from the origin and from the
    destination. At a fast-road residual of 1.009 m both roads are candidates and the fast one wins.
    Moving the fast road 2 mm further out — 1.011 m — puts it outside the band and leaves only the
    slow road: the answer jumps by 899.99 s, from PASS to FAIL at ten minutes.
    """
    def answer(fast_offset: float) -> float:
        g = toy.ToyGraph(edges=(
            toy.ToyEdge(0, 1, ((0, -1.0), (100, -1.0)), time_s=1000.0, cost_base=1000.0,
                        osmid=(1,)),
            toy.ToyEdge(2, 3, ((0, fast_offset), (100, fast_offset)), time_s=100.0,
                        cost_base=100.0, osmid=(2,)),
        ))
        return toy.evaluate(g, (0.0, 0.0), [(100.0, 0.0)]).objective1_s

    both_retained = answer(1.009)
    fast_excluded = answer(1.011)
    assert both_retained == pytest.approx(100.0 + 2 * 1.009 / toy.ACCESS_SPEED_MPS, abs=1e-9)
    assert fast_excluded == pytest.approx(1000.0 + 2.0 / toy.ACCESS_SPEED_MPS, abs=1e-9)
    assert fast_excluded - both_retained == pytest.approx(899.9857142857143, abs=1e-9)

    ten_minutes = 600.0
    assert both_retained <= ten_minutes < fast_excluded, (
        "2 mm of geometry decides the verdict, so the retained-minimiser rule makes the answer "
        "well defined without making it continuous"
    )


def test_the_two_caps_are_applied_to_their_own_side_of_the_journey():
    g = toy.ToyGraph(edges=(
        toy.ToyEdge(0, 1, ((0, 0), (100, 0)), time_s=100.0, cost_base=100.0, osmid=(1,)),
    ))
    at_250 = (50.0, 250.0)
    assert toy.attachments(g, at_250, cap_m=toy.MAX_ACCESS_M) == ()       # 250 > 200
    assert len(toy.attachments(g, at_250, cap_m=toy.POI_SNAP_MAX_M)) == 1  # 250 <= 300


# ----------------------------------------------------------------------------- the frozen artifact


def test_the_corpus_digest_is_stable_and_covers_the_derivations():
    """Design §12: the suite is a frozen artifact with a digest. The plan is explicit that a digest
    proves immutability rather than correctness, so this is the weakest of the three guarantees.

    The digest covers `derivation` and `provenance` as well as the numbers, because the obligation it
    protects is that each case *arrived with* its justification.
    """
    first = cf.corpus_digest(CASES)
    assert first == cf.corpus_digest(CASES)
    assert len(first) == 64

    retitled = list(CASES)
    retitled[0] = dataclasses.replace(CASES[0], derivation=CASES[0].derivation + " (reworded)")
    assert cf.corpus_digest(retitled) != first

    renumbered = list(CASES)
    renumbered[0] = dataclasses.replace(
        CASES[0], expected=dataclasses.replace(CASES[0].expected, objective1_s=1.6))
    assert cf.corpus_digest(renumbered) != first


def test_reordering_the_corpus_changes_its_digest():
    """Order is part of the artifact, so a reordering is a new artifact rather than the same one."""
    assert cf.corpus_digest(CASES) != cf.corpus_digest(tuple(reversed(CASES)))


def test_the_corpus_has_no_duplicate_names():
    names = [c.name for c in CASES]
    assert len(names) == len(set(names))


# ----------------------------------------------------------------------------- pass-20's mutants
#
# Every one of these exposed a defect the twelve original cases did not separate. The strict-cap
# mutant is the sharpest: it passed all 78 tests, which is the answer to "construct a wrong
# comparator that passes the entire corpus" — the answer was yes.


def test_a_strict_cap_comparator_is_now_caught(monkeypatch):
    """Wrong implementation 5, and the one that passed everything. `< cap` instead of `<= cap`.

    Pass-20 F5 executed it by replacing each cap with its next float down; all 78 tests passed,
    because every case used 250 m or 350 m and none sat on a boundary. On a destination exactly
    300 m from the network the mutant excludes it and finds no journey at all, where the answer is
    a 338.0952380952 s ten-minute PASS.
    """
    real = toy.nearest_on_graph
    monkeypatch.setattr(toy, "nearest_on_graph",
                        lambda g, p, *, cap_m: real(g, p, cap_m=math.nextafter(cap_m, -math.inf)))

    case = next(c for c in CASES if c.name == "a_destination_exactly_at_the_cap_is_eligible")
    problems = cf.check(case)
    assert problems, "a strict cap must fail the boundary case"
    assert any("no finite time" in p or "eligible" in p for p in problems)


def test_the_caps_are_inclusive_on_both_sides():
    """Exactly at the cap is in; one float past it is out. Both sides, independently."""
    g = toy.ToyGraph(edges=(
        toy.ToyEdge(0, 1, ((0, 0), (100, 0)), time_s=100.0, cost_base=100.0, osmid=(1,)),
    ))
    for cap in (toy.MAX_ACCESS_M, toy.POI_SNAP_MAX_M):
        at = toy.attachments(g, (50.0, cap), cap_m=cap)
        past = toy.attachments(g, (50.0, math.nextafter(cap, math.inf)), cap_m=cap)
        assert len(at) == 1, f"exactly {cap} m must attach"
        assert at[0].residual_m == pytest.approx(cap, rel=0, abs=1e-9)
        assert past == (), f"one float past {cap} m must not"


def test_the_tie_band_is_inclusive_at_exactly_the_tolerance():
    """`<= ATTACH_TIE_M`, not `<`. A second road exactly 0.01 m further is retained."""
    def candidates(second_offset: float) -> int:
        g = toy.ToyGraph(edges=(
            toy.ToyEdge(0, 1, ((0, 1.0), (100, 1.0)), time_s=1.0, cost_base=1.0, osmid=(1,)),
            toy.ToyEdge(2, 3, ((0, -second_offset), (100, -second_offset)), time_s=2.0,
                        cost_base=2.0, osmid=(2,)),
        ))
        return len(toy.attachments(g, (50.0, 0.0), cap_m=toy.MAX_ACCESS_M))

    assert candidates(1.0 + toy.ATTACH_TIE_M) == 2
    assert candidates(1.0 + toy.ATTACH_TIE_M + 1e-9) == 1


def test_the_connector_is_in_objective_2s_cost_not_only_its_time(monkeypatch):
    """Wrong implementation 6: pass-20 F1, the defect that passed all twelve original cases.

    Design §2.1 says both objectives include both connectors and §2.2 says they are part of both
    objectives' totals. Revision 6's time-only connector policy is for the independent engine, where
    seconds share no unit with that engine's generalised cost; it does not repeal §2.2 for ours.
    """
    case = next(c for c in CASES if c.name == "connectors_enter_objective_2s_selection_cost")
    r = case.run()
    assert r.objective2_s == pytest.approx(650.0) and r.objective2_destination == 1
    assert r.objective2_cost == pytest.approx(20.0)
    assert r.objective1_s == pytest.approx(10.0 + 100.0 / toy.ACCESS_SPEED_MPS)
    assert r.objective1_destination == 0, "the two objectives must select different destinations"

    # the mutant: charge the connector to time only
    real = toy.journeys

    def time_only(graph, origin, destinations, destination_ids=None):
        out = []
        for j in real(graph, origin, destinations, destination_ids):
            out.append(dataclasses.replace(j, cost=j.cost - _connector_part(graph, origin,
                                                                           destinations, j)))
        return out

    def _connector_part(graph, origin, destinations, journey):
        oa = toy.attachments(graph, origin, cap_m=toy.MAX_ACCESS_M)
        da = toy.attachments(graph, destinations[journey.destination], cap_m=toy.POI_SNAP_MAX_M)
        return (min(a.residual_m for a in oa) + min(a.residual_m for a in da)) \
            / toy.ACCESS_SPEED_MPS

    monkeypatch.setattr(toy, "journeys", time_only)
    problems = cf.check(case)
    assert problems, "omitting the connector from cost must fail this case"
    assert any("objective2" in p for p in problems)


def test_a_self_crossing_edge_keeps_both_occurrences_of_one_position():
    """Pass-20 F2. Two zero-distance occurrences of `(0,0)` at arclengths 100 m and 500 m: the same
    place, not the same decision. A rounded-XY key merges them and loses 400 m of route."""
    case = next(c for c in CASES if c.name == "two_occurrences_at_one_position_are_two_candidates")
    kept = toy.attachments(case.graph, case.origin, cap_m=toy.MAX_ACCESS_M)
    assert len(kept) == 2
    assert sorted(round(a.arclength_m, 6) for a in kept) == [100.0, 500.0]
    assert all(a.residual_m == pytest.approx(0.0) for a in kept)
    assert {round(a.position[0], 6) for a in kept} == {0.0}, (
        "both occurrences are at the same XY, which is exactly why a position key merges them"
    )
    assert case.run().objective1_s == pytest.approx(1000.0 / 6.0, rel=0, abs=cf.TIME_TOL_S)


def test_the_dedup_representative_is_the_nearest_not_the_first():
    """Pass-20 F2's second half. Two projections round to the same bucket at 200.004 m and
    199.996 m; keeping the first and then applying the 200 m cap returns **zero** candidates where
    one is attached. The representative is the smallest residual."""
    g = toy.ToyGraph(edges=(
        toy.ToyEdge(0, 1, ((-100, -0.004), (100, -0.004), (100, 0.004), (-100, 0.004)),
                    time_s=100.0, cost_base=100.0, osmid=(1,)),
    ))
    found = toy.nearest_on_graph(g, (0.0, 200.0), cap_m=toy.MAX_ACCESS_M)
    assert found.global_min_m == pytest.approx(199.996, rel=0, abs=1e-9)
    assert len(found.candidates) >= 1, "the in-cap representative must survive"
    assert found.candidates[0].residual_m == pytest.approx(199.996, rel=0, abs=1e-9)


def test_the_two_directions_of_a_closed_edge_have_different_identities():
    """Pass-20 F3. For `u == v` the endpoints cannot separate the directions and canonicalising the
    geometry against reversal removes the rest, so revision 6's identity made them equal."""
    fwd = toy.ToyEdge(0, 0, ((0, 0), (100, 0), (100, 100), (0, 100), (0, 0)),
                      time_s=4000.0, cost_base=4000.0, osmid=(7,), oneway=True)
    rev = toy.ToyEdge(0, 0, ((0, 0), (0, 100), (100, 100), (100, 0), (0, 0)),
                      time_s=4000.0, cost_base=4000.0, osmid=(7,), oneway=True)
    assert fwd.geometry_key == rev.geometry_key, "the same physical ring"
    assert fwd.orientation != rev.orientation
    assert fwd.identity != rev.identity, "but not the same directed edge"

    # an open edge needs no orientation help: its endpoints already separate the directions
    open_fwd = toy.ToyEdge(0, 1, ((0, 0), (100, 0)), time_s=1.0, cost_base=1.0, osmid=(1,))
    open_rev = toy.ToyEdge(1, 0, ((100, 0), (0, 0)), time_s=1.0, cost_base=1.0, osmid=(1,))
    assert open_fwd.identity != open_rev.identity


@pytest.mark.parametrize("name,expected", [
    ("the_two_directions_of_a_closed_edge_are_distinct", 200.0),
    ("same_identity_alternatives_still_compete_on_weights", 1.2),
])
def test_the_insertion_order_defects_are_closed(name, expected):
    """Pass-20 F3 and F4 both reported PASS/FAIL flips decided purely by input order — 3800 against
    200, and 802 against 1.2. The general edge-order test covers every case; these two pin the
    numbers, because both are cases where one record was being discarded before either objective
    could compete."""
    case = next(c for c in CASES if c.name == name)
    forward = case.run()
    backward = toy.evaluate(toy.ToyGraph(edges=tuple(reversed(case.graph.edges))),
                            case.origin, list(case.destinations))
    assert forward.objective1_s == pytest.approx(expected, rel=0, abs=1e-9)
    assert backward.objective1_s == pytest.approx(expected, rel=0, abs=1e-9)
    assert forward.origin_candidates == backward.origin_candidates == 2


def test_cost_totals_do_not_depend_on_summation_order():
    """Pass-20 F7. Two routes carrying the **same multiset** of costs in different orders: left
    accumulation gives 0.6000000000000001 and 0.6, so the 1,000 s route wins the cost argmin over
    the 1 s one — a FAIL/PASS flip at ten minutes decided by summation order.

    `math.fsum` is exactly rounded, so the total of a multiset is one number and genuinely equal
    costs compare equal. No epsilon is introduced: §2.4 declares no cost tolerance.
    """
    assert math.fsum((0.1, 0.2, 0.3)) == math.fsum((0.3, 0.2, 0.1))
    assert (0.1 + 0.2 + 0.3) != (0.3 + 0.2 + 0.1), "which is the problem fsum solves"

    def graph(fast, slow):
        return toy.ToyGraph(edges=(
            toy.ToyEdge(0, 1, ((-100, 0), (0, 0)), time_s=0.0, cost_base=0.0, osmid=(1,),
                        oneway=True),
            toy.ToyEdge(1, 2, ((0, 0), (100, 100)), time_s=1 / 3, cost_base=fast[0], osmid=(2,),
                        oneway=True),
            toy.ToyEdge(2, 3, ((100, 100), (200, 100)), time_s=1 / 3, cost_base=fast[1],
                        osmid=(3,), oneway=True),
            toy.ToyEdge(3, 4, ((200, 100), (300, 0)), time_s=1 / 3, cost_base=fast[2], osmid=(4,),
                        oneway=True),
            toy.ToyEdge(1, 5, ((0, 0), (100, -100)), time_s=1000 / 3, cost_base=slow[0],
                        osmid=(5,), oneway=True),
            toy.ToyEdge(5, 6, ((100, -100), (200, -100)), time_s=1000 / 3, cost_base=slow[1],
                        osmid=(6,), oneway=True),
            toy.ToyEdge(6, 4, ((200, -100), (300, 0)), time_s=1000 / 3, cost_base=slow[2],
                        osmid=(7,), oneway=True),
            toy.ToyEdge(4, 7, ((300, 0), (400, 0)), time_s=0.0, cost_base=0.0, osmid=(8,),
                        oneway=True),
        ))

    r = toy.evaluate(graph((0.1, 0.2, 0.3), (0.3, 0.2, 0.1)), (-50.0, 0.0), [(350.0, 0.0)])
    assert r.objective2_cost == pytest.approx(0.6, rel=0, abs=1e-15)
    assert r.objective2_s == pytest.approx(1.0, rel=0, abs=1e-9), (
        "the costs tie, so §2.4's travel-time key selects the fast route"
    )
    # and swapping which route carries which order changes nothing
    swapped = toy.evaluate(graph((0.3, 0.2, 0.1), (0.1, 0.2, 0.3)), (-50.0, 0.0), [(350.0, 0.0)])
    assert swapped.objective2_s == pytest.approx(1.0, rel=0, abs=1e-9)


def test_the_selected_destination_is_ranked_by_id_not_by_input_order():
    """Pass-20 F9 and design §2.4 revision 6's key 5. Two ids at one coordinate reached identically
    tie on every edge key, so without the id key the manifest names whichever came first."""
    g = toy.ToyGraph(edges=(
        toy.ToyEdge(0, 1, ((0, 0), (100, 0)), time_s=1.0, cost_base=1.0, osmid=(1,)),
    ))
    for ids in (["z", "a"], ["a", "z"]):
        r = toy.evaluate(g, (0.0, 0.0), [(100.0, 0.0), (100.0, 0.0)], ids)
        assert r.objective1_destination_id == "a", f"input order {ids} changed the selection"
        assert r.objective2_destination_id == "a"


def test_the_route_rank_compares_structurally_not_as_text():
    """Pass-20 F9's other half: node pairs `(2,3)` and `(10,11)` compare `2 < 10` structurally and
    `'10' < '2'` as text, so the old `repr` key selected the wrong route."""
    a = toy.Journey(time_s=1.0, cost=1.0, destination=0, destination_id="d",
                    route=((2, 3, (), 0, (1,), 1.0),))
    b = toy.Journey(time_s=1.0, cost=1.0, destination=0, destination_id="d",
                    route=((10, 11, (), 0, (1,), 1.0),))
    assert min(a, b, key=lambda j: j.rank_key) is a
    assert repr(a.route[0]) > repr(b.route[0]), "which is what the text key got wrong"


def test_a_non_finite_time_is_not_a_verdict():
    """Pass-20 F11. `inf` is how this repository represents a routing non-result, and it arrived at
    the §2.5 rule as a definitive FAIL while `-inf` arrived as PASS. Ten such points against a
    product PASS move the gate from INCONCLUSIVE (k=0, u=10) to FAIL (k=10) on no established
    failure at all."""
    for bad in (math.inf, -math.inf, math.nan):
        with pytest.raises(ValueError, match="finite"):
            cf.comparator_outcome(threshold_s=600.0, time_s=bad, search_bounded=True,
                                  exhausted=False)
    with pytest.raises(ValueError, match="non-negative"):
        cf.comparator_outcome(threshold_s=600.0, time_s=-1.0, search_bounded=True, exhausted=False)

    # a non-result is `None`, and then the bound branches decide
    assert cf.comparator_outcome(threshold_s=600.0, time_s=None, search_bounded=True,
                                 exhausted=False) is cf.ComparatorOutcome.UNRESOLVED


def test_an_off_network_origin_keeps_the_distance_its_bound_needs():
    """Pass-20: the cap discards the very distance `OFF_NETWORK`'s bound is computed from, so an
    empty candidate tuple is not enough. The bound is `nearest / max_speed_mps` — never the 200 m
    cap, which is a different number, and never invented when there is no nearest distance at all.
    """
    far = toy.ToyGraph(edges=(
        toy.ToyEdge(0, 1, ((0, 0), (100, 0)), time_s=100.0, cost_base=100.0, osmid=(1,)),
    ))
    found = toy.nearest_on_graph(far, (50.0, 200.5), cap_m=toy.MAX_ACCESS_M)
    assert found.candidates == ()
    assert found.global_min_m == pytest.approx(200.5, rel=0, abs=1e-9)

    bound_s = found.global_min_m / max_speed_mps("walk")
    assert bound_s == pytest.approx(143.2142857143, rel=0, abs=1e-9)
    assert bound_s < 600.0, "so this point is UNKNOWN at ten minutes, not a known failure"
    assert toy.MAX_ACCESS_M / max_speed_mps("walk") != pytest.approx(bound_s), (
        "the cap is not the measured distance and would give a different bound"
    )

    # the distance that does prove failure at ten minutes
    further = toy.nearest_on_graph(far, (50.0, 840.5), cap_m=toy.MAX_ACCESS_M)
    assert further.global_min_m / max_speed_mps("walk") > 600.0

    # an empty graph has no nearest distance, and none is invented
    empty = toy.nearest_on_graph(toy.ToyGraph(edges=()), (0.0, 0.0), cap_m=toy.MAX_ACCESS_M)
    assert empty.candidates == () and empty.global_min_m is None
