"""T9 — E3 scoring. Design §3.

**The fixture that cannot be satisfied.** Plan revision 2 asserted that a journey 1.6x over but only
3 minutes over does *not* fail. For a single journey of reported 5 min and observed 8 min the
**median limb fires** — the median signed difference is 3 min against a limit of 1.25 min — so no
correct implementation can satisfy that fixture. It is tested here as a **failure**, which is the
point: a disjunction cannot be fixtured one limb at a time.

So each limb is tested in isolation, on inputs where only that limb can fire, and the complete
disjunction is tested on the singleton the old fixture got wrong.
"""

from __future__ import annotations

import pytest

from locfinder.measure.e3 import (
    ABSOLUTE_LIMIT_S,
    MEDIAN_SHARE_LIMIT,
    RATIO_LIMIT,
    E3Outcome,
    Journey,
    score_e3,
)

MIN = 60.0


# ----------------------------------------------------------------------------- limb (i), alone


def test_the_single_journey_limb_needs_both_conditions():
    """Limb (i) is a conjunction: more than 1.5x **and** more than 5 minutes. Each alone is not
    enough, which is the half of the rule the old fixture was reaching for."""
    # 3x over but only 4 minutes: the ratio trips, the absolute does not
    ratio_only = Journey("ratio-only", reported_s=2 * MIN, observed_s=6 * MIN)
    assert ratio_only.ratio == pytest.approx(3.0)
    assert ratio_only.ratio > RATIO_LIMIT
    assert ratio_only.difference_s == pytest.approx(4 * MIN)
    assert ratio_only.difference_s < ABSOLUTE_LIMIT_S
    assert not ratio_only.trips_single_journey_limb

    # 20 minutes over but only 1.33x: the absolute trips, the ratio does not
    absolute_only = Journey("absolute-only", reported_s=60 * MIN, observed_s=80 * MIN)
    assert absolute_only.difference_s == pytest.approx(20 * MIN)
    assert absolute_only.difference_s > ABSOLUTE_LIMIT_S
    assert absolute_only.ratio == pytest.approx(80 / 60)
    assert absolute_only.ratio < RATIO_LIMIT
    assert not absolute_only.trips_single_journey_limb

    # 2x and 10 minutes over: both
    both = Journey("both", reported_s=10 * MIN, observed_s=20 * MIN)
    assert both.trips_single_journey_limb


def test_the_single_journey_limb_is_strict_at_each_boundary():
    """"More than" at both limits, so sitting exactly on one does not fail."""
    on_ratio = Journey("on-ratio", reported_s=20 * MIN, observed_s=30 * MIN)   # exactly 1.5x
    assert on_ratio.ratio == pytest.approx(RATIO_LIMIT)
    assert on_ratio.difference_s == pytest.approx(10 * MIN)
    assert on_ratio.difference_s > ABSOLUTE_LIMIT_S
    assert not on_ratio.trips_single_journey_limb

    on_absolute = Journey("on-absolute", reported_s=4 * MIN, observed_s=9 * MIN)  # exactly 5 min
    assert on_absolute.difference_s == pytest.approx(ABSOLUTE_LIMIT_S)
    assert on_absolute.ratio == pytest.approx(2.25)
    assert on_absolute.ratio > RATIO_LIMIT
    assert not on_absolute.trips_single_journey_limb

    just_past = Journey("just-past", reported_s=4 * MIN, observed_s=9 * MIN + 1.0)
    assert just_past.trips_single_journey_limb


def test_limb_one_alone_fails_a_set_whose_median_is_clean():
    """A set where only limb (i) can fire: one badly wrong journey among many accurate ones, so the
    median signed difference stays well under 25% of the median reported time."""
    journeys = [Journey(f"ok{i}", reported_s=20 * MIN, observed_s=20 * MIN) for i in range(6)]
    journeys.append(Journey("bad", reported_s=10 * MIN, observed_s=25 * MIN))  # 2.5x, 15 min over

    r = score_e3(journeys)
    assert r.outcome is E3Outcome.FAILED
    assert r.offending == ("bad",)
    assert r.median_difference_s == pytest.approx(0.0)
    assert r.median_difference_s <= r.median_limit_s, "the median limb must be quiet here"
    assert len(r.reasons) == 1 and "bad" in r.reasons[0]


# ----------------------------------------------------------------------------- limb (ii), alone


def test_limb_two_alone_fails_a_set_where_no_single_journey_does():
    """The case limb (i) cannot see: a systematic 30% overrun on every journey, where no single one
    is 1.5x over *or* 5 minutes over."""
    journeys = [Journey(f"j{i}", reported_s=10 * MIN, observed_s=13 * MIN) for i in range(6)]
    for j in journeys:
        assert j.ratio == pytest.approx(1.3)
        assert j.ratio < RATIO_LIMIT
        assert j.difference_s == pytest.approx(3 * MIN)
        assert j.difference_s < ABSOLUTE_LIMIT_S
        assert not j.trips_single_journey_limb

    r = score_e3(journeys)
    assert r.outcome is E3Outcome.FAILED
    assert r.offending == ()
    assert r.median_difference_s == pytest.approx(3 * MIN)
    assert r.median_limit_s == pytest.approx(MEDIAN_SHARE_LIMIT * 10 * MIN)
    assert len(r.reasons) == 1 and "median" in r.reasons[0]


def test_the_median_limb_is_strict_at_its_boundary():
    """Exactly 25% of the median reported time does not fail; a second past it does."""
    on = [Journey(f"on{i}", reported_s=20 * MIN, observed_s=25 * MIN) for i in range(5)]
    r = score_e3(on)
    assert r.median_difference_s == pytest.approx(r.median_limit_s)
    assert r.outcome is E3Outcome.UNVERIFIED

    past = [Journey(f"p{i}", reported_s=20 * MIN, observed_s=25 * MIN + 1.0) for i in range(5)]
    assert score_e3(past).outcome is E3Outcome.FAILED


def test_the_median_is_signed_so_fast_journeys_offset_slow_ones():
    """It is the median **signed** difference, not of absolute values. Three journeys 10 minutes
    early and three 10 minutes late give a median near zero and must not fail — whereas a median of
    absolute differences would be 10 minutes and would fail."""
    journeys = ([Journey(f"early{i}", reported_s=30 * MIN, observed_s=20 * MIN) for i in range(3)]
                + [Journey(f"late{i}", reported_s=30 * MIN, observed_s=40 * MIN) for i in range(3)])
    r = score_e3(journeys)
    assert r.median_difference_s == pytest.approx(0.0)
    assert r.outcome is E3Outcome.UNVERIFIED
    assert not any(j.trips_single_journey_limb for j in journeys), (
        "and no single journey trips limb (i): 1.33x and 10 min, so the ratio is under 1.5"
    )


# ----------------------------------------------------------------------------- the whole disjunction


def test_the_impossible_fixture_is_a_failure():
    """Plan revision 2 asserted this singleton does **not** fail. It does.

    Reported 5 min, observed 8 min: 1.6x over but only 3 minutes over, so limb (i) is quiet. But the
    median signed difference over the one walked journey is 3 min and 25% of the median reported time
    is 1.25 min, so **limb (ii) fires**. A fixture written against one limb while the other is live
    cannot be satisfied by any correct implementation.
    """
    one = Journey("the-old-fixture", reported_s=5 * MIN, observed_s=8 * MIN)
    assert one.ratio == pytest.approx(1.6)
    assert one.ratio > RATIO_LIMIT
    assert one.difference_s == pytest.approx(3 * MIN)
    assert one.difference_s < ABSOLUTE_LIMIT_S
    assert not one.trips_single_journey_limb                      # limb (i) is quiet

    r = score_e3([one])
    assert r.median_difference_s == pytest.approx(3 * MIN)
    assert r.median_limit_s == pytest.approx(1.25 * MIN)
    assert r.outcome is E3Outcome.FAILED                          # limb (ii) is not
    assert "median" in r.reasons[0]


def test_both_limbs_can_fire_and_both_reasons_are_reported():
    journeys = [Journey("slow", reported_s=10 * MIN, observed_s=30 * MIN),
                Journey("also-slow", reported_s=10 * MIN, observed_s=30 * MIN)]
    r = score_e3(journeys)
    assert r.outcome is E3Outcome.FAILED
    assert len(r.reasons) == 3, "one per offending journey, plus the median"
    assert r.offending == ("slow", "also-slow")


def test_an_accurate_set_is_unverified_and_never_supported():
    """Absent a failure the outcome is UNVERIFIED. There is no third value, by design: with 8
    observations and no discrepancy the one-sided 95% bound on the population rate is 31.2344%."""
    journeys = [Journey(f"j{i}", reported_s=(10 + i) * MIN, observed_s=(10 + i) * MIN + 15.0)
                for i in range(8)]
    r = score_e3(journeys)
    assert r.outcome is E3Outcome.UNVERIFIED
    assert r.reasons == ()
    assert set(E3Outcome) == {E3Outcome.FAILED, E3Outcome.UNVERIFIED}
    assert not any("support" in v.value.lower() for v in E3Outcome)


# ----------------------------------------------------------------------------- unwalked journeys


def test_an_unwalked_journey_cannot_erase_an_established_failure():
    """Design §3: "A planned journey that was not walked leaves UNVERIFIED and **can never erase a
    failure** established by the journeys that were walked."

    This is the one-way rule. Adding unwalked rows to a failing set keeps it failing, however many
    are added — which a mean over all planned journeys, or a zero difference for a missing
    observation, would not.
    """
    failing = [Journey("bad", reported_s=10 * MIN, observed_s=30 * MIN)]
    assert score_e3(failing).outcome is E3Outcome.FAILED

    for extra in (1, 3, 20):
        padded = failing + [Journey(f"planned{i}", reported_s=10 * MIN) for i in range(extra)]
        r = score_e3(padded)
        assert r.outcome is E3Outcome.FAILED, f"{extra} unwalked journeys erased the failure"
        assert r.walked == 1 and r.planned == extra
        assert r.median_difference_s == pytest.approx(20 * MIN), (
            "the medians are over walked journeys only; counting an unwalked one as zero "
            "difference would dilute the failure away"
        )


def test_no_walked_journey_leaves_both_medians_undefined_not_zero():
    """A median of `None` rather than 0.0, because zero would assert the product was accurate."""
    r = score_e3([Journey("planned", reported_s=10 * MIN)])
    assert r.outcome is E3Outcome.UNVERIFIED
    assert r.walked == 0 and r.planned == 1
    assert r.median_difference_s is None
    assert r.median_reported_s is None
    assert r.median_limit_s is None


def test_an_empty_set_is_unverified():
    r = score_e3([])
    assert r.outcome is E3Outcome.UNVERIFIED
    assert (r.walked, r.planned) == (0, 0)
    assert r.median_difference_s is None


# ----------------------------------------------------------------------------- inputs


def test_a_journey_that_cannot_be_one_is_rejected():
    with pytest.raises(ValueError, match="reported_s"):
        Journey("zero", reported_s=0.0, observed_s=10.0)
    with pytest.raises(ValueError, match="reported_s"):
        Journey("nan", reported_s=float("nan"), observed_s=10.0)
    with pytest.raises(ValueError, match="observed_s"):
        Journey("negative", reported_s=10.0, observed_s=-1.0)
    with pytest.raises(ValueError, match="observed_s"):
        Journey("inf", reported_s=10.0, observed_s=float("inf"))


def test_journeys_must_be_distinguishable():
    """A failure has to be pointable at a journey, so duplicate labels are an error rather than a
    silently merged pair."""
    with pytest.raises(ValueError, match="distinct labels"):
        score_e3([Journey("same", reported_s=10 * MIN, observed_s=10 * MIN),
                  Journey("same", reported_s=20 * MIN, observed_s=40 * MIN)])


def test_the_quantile_convention_is_the_frozen_one():
    """Design §6 freezes linear interpolation, and E3's median uses it. On an even number of
    journeys the median is the midpoint, which other conventions do not give."""
    journeys = [Journey("a", reported_s=10 * MIN, observed_s=10 * MIN),
                Journey("b", reported_s=10 * MIN, observed_s=12 * MIN)]
    r = score_e3(journeys)
    assert r.median_difference_s == pytest.approx(1 * MIN), "midpoint of 0 and 120 s"
    assert r.outcome is E3Outcome.UNVERIFIED       # 60 s against a 150 s limit
