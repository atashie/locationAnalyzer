"""The suffix-aware band, phase 4b.0 part two.

These are not conformance cases — T4 owns those, and whether it should gain more consequential tie
fixtures is the owner's decision, still open. These pin the two witnesses the band is reported
against, so a later change to the band cannot quietly move them, and the published numbers in
`docs/experiments/suffix-band.json` stay reproducible from the tests rather than only from a run.
"""
from __future__ import annotations

import math
import pathlib
import random
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

import spike_suffix_band as band                       # noqa: E402
from locfinder.measure import toy                      # noqa: E402


def test_the_band_selects_item_6s_witness_where_a_pair_label_does_not():
    """The whole point. §2.4's answer is 5 s; a `(cost, time)` pair label reports 1,004 s; the
    band, whose width is sized from the reachable suffix, keeps the strictly costlier prefix and
    reports 5 s. PASS against FAIL at a ten-minute threshold."""
    w = band.check_witness()
    assert w["oracle_seconds"] == 5.0
    assert w["band_seconds"] == 5.0
    assert w["scalar_seconds"] == 1004.0
    assert w["cost_argmin"] == 2003.0
    assert w["band_agrees_on_the_numbers"] and w["band_agrees_on_the_route"]
    assert not w["scalar_agrees"]
    assert w["verdict_at_600s"] == {"normative": "PASS", "band": "PASS", "scalar": "FAIL"}


def test_one_band_reports_the_right_numbers_and_the_wrong_route():
    """What the plan's single band does **not** settle. Two prefixes with the same exact cost and
    travel times one ulp of 500 apart round to one reported time, so §2.4 falls through to the
    route key — and the per-cost dominance has already dropped the label carrying the smaller
    route. A second band on time, sized the same way, settles it."""
    rw = band.check_route_witness()
    assert rw["one_band_numbers_agree"]
    assert not rw["one_band_route_agrees"]
    assert rw["two_band_route_agrees"]
    assert rw["two_band_labels"] > rw["one_band_labels"]


def test_the_band_width_narrows_with_the_bound_it_is_taken_from():
    """`ulp(U)` for an upper bound `U` on the reachable total. The graph's own total is sound and
    loose; a query ceiling is sound and tight. Both must still select the normative answer — a
    narrower band that lost the witness would be no band at all."""
    ws = band.width_sources()
    assert ws["query_ceiling_bound_width_in_ulps_of_the_total"] == 2.0
    assert ws["graph_total_bound_width_in_ulps_of_the_total"] == 16.0
    assert ws["both_still_select_the_normative_answer"]


def test_the_band_does_not_move_when_the_edge_list_is_permuted():
    """Pass 41 F5 found the first spike's band order-dependent — 2 s against 1,001 s on one graph.
    `first_arrival` is the positive control: without it a zero would only mean the check is blunt.
    """
    graph, origin, dests, ids = band.witness_graph()
    out = band.order_independence(graph, origin, dests, ids, random.Random(11))
    assert out["band_distinct_answers"] == 1
    assert out["first_arrival_control_distinct_answers"] > 1


def test_a_zero_cost_cycle_costs_the_route_key_and_not_the_numbers():
    """The band's precondition. A cycle costing no more than the width makes one route a proper
    prefix of another at a merge, which is what pass 41 F4's dominance argument forbids. It does
    **not** touch cost or travel time: a zero-cost cycle of zero time changes neither total, and
    one of positive time can only raise the time."""
    out = band.zero_cost_cycles(random.Random(3), graphs=60)
    assert out["graphs_compared"] > 30
    assert out["flagged_by_the_precondition_check"] == out["graphs_compared"]
    assert out["band_wrong_numbers"] == 0
    assert out["band_returned_an_unformable_journey"] == 0


def test_the_band_agrees_with_the_exhaustive_oracle_on_planted_near_ties():
    """The population the band exists for: diamonds whose arms differ by a few ulps of cost behind
    a long shared suffix. A generic population does not exercise the band at all, so a zero there
    would say nothing."""
    out = band.sweep(random.Random(5), 25, population="planted", cap=50_000, permutations=2)
    assert out["graphs_compared"] >= 20
    assert out["graphs_with_more_than_one_journey_at_the_cost_argmin"] > 0
    assert out["wrong_quantities"]["two_band"] == {}
    assert out["returned_a_journey_the_model_cannot_form"]["two_band"] == 0
    assert out["answers_that_moved_when_the_edge_list_was_permuted"]["two_band"] == 0
    assert out["wrong_quantities"]["pair_label"], "the pair label must fail here or the population is not planting anything"


def test_the_band_is_free_when_there_is_nothing_to_retain():
    """Price. With weights drawn from a continuum, distinct prefix costs are nowhere near an ulp of
    the total apart, so the band keeps exactly one label per node and costs nothing over a scalar
    search. That is the measurement that makes the band affordable, and it is the one that does
    **not** generalise to a real graph without being run there."""
    out = band.sweep(random.Random(9), 25, population="generic", cap=50_000, permutations=1)
    assert out["two_band_labels_per_node"]["max"] == 1.0


def test_the_retained_count_is_bounded_by_the_width_over_the_smallest_gap():
    """Why the generic result does not settle the price. The band holds every distinct prefix cost
    within `W` of the node minimum, so `k` diamonds one ulp apart give `k + 1` labels per merge —
    growth that stops only at `capacity`, the width measured in ulps of an edge, which here is
    8,192."""
    rows = band.price_chain([1, 2, 4, 8])
    assert all(r["agrees"] for r in rows)
    per_node = [r["labels_per_node"] for r in rows]
    assert per_node == sorted(per_node) and per_node[-1] > per_node[0]
    assert rows[0]["capacity"] >= 1024


def test_the_exact_sum_of_a_journeys_terms_is_the_same_binary64_as_fsum():
    """The band carries exact rational prefix sums and the oracle sums terms with `fsum`. Both are
    the correctly rounded exact sum, so the two must agree bit for bit — otherwise every comparison
    between band and oracle in this module is comparing two different rules."""
    graph, origin, dests, ids = band.witness_graph()
    js = toy.journeys(graph, origin, dests, ids)
    assert js
    for j in js:
        assert math.isfinite(j.cost) and math.isfinite(j.time_s)
    answer = band.band_answer(graph, origin, dests, ids, both_bands=True)
    assert (answer["cost"], answer["time_s"], answer["destination_id"],
            answer["route"]) in band.oracle_answer(graph, origin, dests, ids)["all"]


@pytest.mark.parametrize("both", [False, True])
def test_the_band_never_returns_a_journey_the_model_cannot_form(both):
    """Membership, not agreement. A search whose totals are left-accumulated reports pairs no
    journey has; over the planted population the pair label does exactly that. The band must not.
    """
    rng = random.Random(17)
    for _ in range(15):
        graph, origin, dests, ids = band.planted_graph(rng)
        oracle = band.oracle_answer(graph, origin, dests, ids)
        got = band.band_answer(graph, origin, dests, ids, both_bands=both)
        assert band.is_a_real_journey(got, oracle)
