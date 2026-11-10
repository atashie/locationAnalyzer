"""Tests for the S3 statistical primitives.

**Why these tests look the way they do.** Three successive reviews defeated the obvious ones:

* Pass 15 constructed `k/n + (1 - k/n) * (1 - 0.05 ** (1/n))`, which satisfies every zero-event
  value in the design's table, both endpoints and monotonicity, while returning 0.9943% at
  `k = 1, n = 400` against the correct 1.1804% — enough to flip a 1% verdict.
* Pass 18 then defeated the repair: at an absolute tolerance of 0.002, an implementation correct
  everywhere *except* that one cell still passes everything.
* Pass 18 also showed a mistakenly **two-sided** lower bound passes the zero endpoint and the
  confidence-direction checks.

So: fixtures at **1e-10**, at least one oracle by **binomial-tail inversion** rather than the Beta
inverse the implementation calls, non-zero **lower**-bound fixtures, and the complementary identity.

And one test that is deliberately absent: the interval does **not** have to widen as the sample
shrinks. `[-1, 0, 1]` gives `[-1, 1]` while the smaller `[0, 0]` gives `[0, 0]`, so asserting
monotone width would reject correct code (pass-18 F10).
"""

from __future__ import annotations

import inspect

import numpy as np
import pytest
from scipy.optimize import brentq
from scipy.stats import hypergeom
from scipy.stats import beta, binom

from locfinder.measure.stats import (
    BIT_GENERATOR,
    ConditionalRate,
    Verdict,
    acceptance,
    conditional_rate,
    clopper_pearson_lower,
    clopper_pearson_upper,
    percentile_bootstrap,
    percentile_interval,
    srs_variance,
    tolerated_failures,
    two_stage_variance,
)

TOL = 1e-10


# --------------------------------------------------------------------------- independent oracles


def binomial_tail_inversion_upper(k: int, n: int, confidence: float = 0.95) -> float:
    """The exact upper bound by its *definition* — the `p` at which `P(X <= k | p) = 1 - c`.

    This calls neither `beta.ppf` nor the implementation. It is the independent route pass-18 F9
    asked for: an oracle that agrees with the implementation because both are correct, not because
    both call the same library function.
    """
    if k >= n:
        return 1.0
    alpha = 1.0 - confidence
    return brentq(lambda p: binom.cdf(k, n, p) - alpha, 1e-15, 1.0 - 1e-15, xtol=1e-15, rtol=1e-15)


def binomial_tail_inversion_lower(k: int, n: int, confidence: float = 0.95) -> float:
    """The exact one-sided lower bound: the `p` at which `P(X >= k | p) = 1 - c`."""
    if k <= 0:
        return 0.0
    alpha = 1.0 - confidence
    return brentq(lambda p: binom.sf(k - 1, n, p) - alpha, 1e-15, 1.0 - 1e-15,
                  xtol=1e-15, rtol=1e-15)


# --------------------------------------------------------------------------- upper bound


@pytest.mark.parametrize("confidence", [0.90, 0.95, 0.99])
@pytest.mark.parametrize("n", [8, 60, 150, 400, 500, 628])
@pytest.mark.parametrize("k", [0, 1, 2, 3, 4])
def test_the_upper_bound_matches_an_independently_inverted_binomial_tail(k, n, confidence):
    """The decisive fixture. Pass-15's wrong formula and pass-18's one-cell variant both differ from
    this at some (k, n), and 1e-10 leaves no room to hide a difference that could flip a verdict.

    **Parametrised over the confidence level**, which pass-19 F3 showed is what the fixture was
    missing: every exact comparison used the default 0.95 and the non-default tests checked only
    direction, so a globally miscalibrated level passed all 65 tests. See
    `test_a_globally_miscalibrated_confidence_level_is_now_rejected`.
    """
    assert clopper_pearson_upper(k, n, confidence=confidence) == pytest.approx(
        binomial_tail_inversion_upper(k, n, confidence), rel=0, abs=TOL)


def test_the_pass15_counterexample_is_rejected():
    """The explicit regression: the formula that satisfied every zero-event fixture."""
    def wrong(k, n):
        return k / n + (1 - k / n) * (1 - 0.05 ** (1 / n))

    # it agrees at k = 0 -- which is exactly why the old fixtures passed it
    assert wrong(0, 400) == pytest.approx(clopper_pearson_upper(0, 400), rel=0, abs=TOL)
    # and disagrees where the verdict is decided
    assert clopper_pearson_upper(1, 400) == pytest.approx(0.01180430445398703, rel=0, abs=TOL)
    assert wrong(1, 400) == pytest.approx(0.009942702139977564, rel=0, abs=TOL)
    assert clopper_pearson_upper(1, 400) > 0.01 > wrong(1, 400)   # it flips the 1% decision


def test_the_pass18_single_cell_variant_is_rejected():
    """Pass-18 F9: correct everywhere except n=400, k=1. A 0.002 tolerance accepted it."""
    def wrong(k, n):
        if (k, n) == (1, 400):
            return 0.009942702139977564
        return clopper_pearson_upper(k, n)

    assert wrong(1, 400) == pytest.approx(clopper_pearson_upper(1, 400), abs=0.002)   # the hole
    assert wrong(1, 400) != pytest.approx(clopper_pearson_upper(1, 400), rel=0, abs=TOL)     # closed


def test_the_zero_failure_closed_form():
    """`1 - (1-c)**(1/n)`, an independent check of this formula at k = 0."""
    for n in (8, 60, 150, 400, 500):
        assert clopper_pearson_upper(0, n) == pytest.approx(1 - 0.05 ** (1 / n), rel=0, abs=TOL)


def test_the_designs_published_zero_failure_values():
    """Design §6's table, at its printed precision — four decimal places as percentages, which is
    all the table states. This is a readability cross-check, not the decisive fixture."""
    for n, pct in ((8, 31.2344), (60, 4.8703), (150, 1.9773), (400, 0.7461), (500, 0.5974)):
        assert clopper_pearson_upper(0, n) * 100 == pytest.approx(pct, abs=5e-5)


def test_the_upper_bound_is_monotone_and_hits_its_endpoints():
    assert clopper_pearson_upper(500, 500) == 1.0
    ups = [clopper_pearson_upper(k, 500) for k in range(8)]
    assert ups == sorted(ups)
    assert clopper_pearson_upper(1, 400) > clopper_pearson_upper(1, 500)


# --------------------------------------------------------------------------- lower bound


@pytest.mark.parametrize("confidence", [0.90, 0.95, 0.99])
@pytest.mark.parametrize("k,n", [(1, 150), (1, 500), (3, 500), (10, 500), (250, 500)])
def test_the_lower_bound_matches_an_independently_inverted_binomial_tail(k, n, confidence):
    assert clopper_pearson_lower(k, n, confidence=confidence) == pytest.approx(
        binomial_tail_inversion_lower(k, n, confidence), rel=0, abs=TOL)


def test_a_globally_miscalibrated_confidence_level_is_now_rejected():
    """Pass-19 F3, executed. A single global substitution — halve the distance of the requested
    level from 0.95 — passed **all 65** tests, because every exact comparison used the default and
    the non-default tests checked only direction.

    The mutant is not an exception carved out for one `(k, n)`. It is one wrong formula that
    delivers the 92.5% bound when 90% is asked for and the 97% bound when 99% is asked for, and it
    satisfies both direction assertions because its levels are still ordered.
    """
    def miscalibrated_upper(k, n, *, confidence=0.95):
        if k >= n:
            return 1.0
        return float(beta.ppf(0.95 + (confidence - 0.95) / 2, k + 1, n - k))

    def miscalibrated_lower(k, n, *, confidence=0.95):
        if k <= 0:
            return 0.0
        return float(beta.ppf(0.05 - (confidence - 0.95) / 2, k, n - k + 1))

    # it is invisible at the default level, which is why the old fixtures accepted it
    assert miscalibrated_upper(1, 500) == pytest.approx(
        clopper_pearson_upper(1, 500), rel=0, abs=TOL)
    assert miscalibrated_lower(1, 500) == pytest.approx(
        clopper_pearson_lower(1, 500), rel=0, abs=TOL)

    # and it still moves both bounds in the right direction with the level
    assert (miscalibrated_upper(1, 500, confidence=0.90)
            < miscalibrated_upper(1, 500, confidence=0.95)
            < miscalibrated_upper(1, 500, confidence=0.99))

    # the parametrised oracle above is what separates it
    assert clopper_pearson_upper(1, 500, confidence=0.90) == pytest.approx(
        0.007756994552213629, rel=0, abs=TOL)
    assert miscalibrated_upper(1, 500, confidence=0.90) == pytest.approx(
        0.008468733810849356, rel=0, abs=TOL)
    assert miscalibrated_upper(1, 500, confidence=0.90) != pytest.approx(
        binomial_tail_inversion_upper(1, 500, 0.90), rel=0, abs=TOL)

    assert clopper_pearson_lower(1, 500, confidence=0.90) == pytest.approx(
        0.0002106988311985045, rel=0, abs=TOL)
    assert miscalibrated_lower(1, 500, confidence=0.90) != pytest.approx(
        binomial_tail_inversion_lower(1, 500, 0.90), rel=0, abs=TOL)

    # at a nominal 99% the mutant supplies 97% coverage
    assert miscalibrated_upper(1, 500, confidence=0.99) == pytest.approx(
        clopper_pearson_upper(1, 500, confidence=0.97), rel=0, abs=TOL)


def test_the_confidence_level_reaches_the_acceptance_verdict():
    """F3's downstream consequence. `acceptance` must forward the level, not just accept it: with
    `k` = 1, `n` = 500 and θ = 0.8%, the correct 90% bound is 0.7757% and PASSES, while the mutant's
    0.8469% exceeds θ and `k/n` = 0.2% does not trigger FAIL — **PASS to INCONCLUSIVE**.
    """
    a = acceptance(1, 0, 500, 0.008, confidence=0.90)
    assert a.verdict is Verdict.PASS
    assert a.bound_range[1] == pytest.approx(0.007756994552213629, rel=0, abs=TOL)

    # the same counts at 95% do not pass, which is what shows the level is in use
    assert acceptance(1, 0, 500, 0.008, confidence=0.95).verdict is Verdict.INCONCLUSIVE


def test_tolerated_failures_uses_the_confidence_level_it_is_given():
    """The same forwarding check on the allocation helper, where a miscalibration would silently
    change how many failures an allocation is reported to tolerate.

    At 99.9% the result is **-1**, not 0: at *n* = 500 the zero-failure bound is
    `1 - 0.001 ** (1/500)` = 1.3816%, which already exceeds a 1% threshold, so no observation
    satisfies the gate. That sentinel is the unreachable-gate condition revision 2 shipped
    undetected, and raising the confidence level is one of the ways to reach it.
    """
    assert tolerated_failures(500, 0.01, confidence=0.95) == 1
    assert tolerated_failures(500, 0.01, confidence=0.80) > 1
    assert clopper_pearson_upper(0, 500, confidence=0.999) == pytest.approx(
        1 - 0.001 ** (1 / 500), rel=0, abs=TOL)
    assert clopper_pearson_upper(0, 500, confidence=0.999) > 0.01
    assert tolerated_failures(500, 0.01, confidence=0.999) == -1


def test_the_lower_bound_is_one_sided_not_two_sided():
    """Pass-18 F9's case. The two-sided value passes a zero endpoint check and moves correctly with
    the confidence level, so only a non-zero fixture separates them."""
    assert clopper_pearson_lower(1, 500) == pytest.approx(0.000102581, rel=0, abs=1e-9)
    two_sided = 1 - 0.975 ** (1 / 500)
    assert two_sided == pytest.approx(0.000050634, rel=0, abs=1e-9)
    assert clopper_pearson_lower(1, 500) != pytest.approx(two_sided, abs=1e-6)


def test_the_complementary_identity_between_the_two_bounds():
    """`CP_lower(k, n, c) == 1 - CP_upper(n - k, n, c)` by the Beta symmetry. An identity check
    catches a swapped parameter that a one-sided fixture might not."""
    for n in (150, 500):
        for k in range(1, 6):
            assert clopper_pearson_lower(k, n) == pytest.approx(
                1 - clopper_pearson_upper(n - k, n), rel=0, abs=TOL)


def test_the_lower_bound_is_zero_at_zero_failures():
    assert clopper_pearson_lower(0, 500) == 0.0


def test_confidence_moves_both_bounds_the_right_way():
    assert (clopper_pearson_upper(1, 500, confidence=0.90)
            < clopper_pearson_upper(1, 500, confidence=0.95)
            < clopper_pearson_upper(1, 500, confidence=0.99))
    assert (clopper_pearson_lower(5, 500, confidence=0.90)
            > clopper_pearson_lower(5, 500, confidence=0.95)
            > clopper_pearson_lower(5, 500, confidence=0.99))


# --------------------------------------------------------------------------- tolerance


def test_the_allocation_tolerances_the_design_states():
    """Design §8's stated consequence, pinned in code: at n = 500, E1b admits one observed false
    inclusion and E1a four."""
    assert tolerated_failures(500, 0.01) == 1
    assert tolerated_failures(500, 0.02) == 4


def test_the_cliff_the_design_chose_n_500_to_avoid():
    """n = 400 tolerates zero at a 1% threshold; 473 is the minimum tolerating one, at 0.9990%,
    which is why it was not predeclared; 500 tolerates one at 0.9452%."""
    assert tolerated_failures(400, 0.01) == 0
    assert tolerated_failures(473, 0.01) == 1
    assert clopper_pearson_upper(1, 473) == pytest.approx(0.009989707, rel=0, abs=1e-8)
    assert clopper_pearson_upper(1, 500) == pytest.approx(0.009452282, rel=0, abs=1e-8)
    assert tolerated_failures(628, 0.01) == 2


def test_an_unreachable_gate_returns_minus_one_rather_than_zero():
    """Revision 2 shipped a gate no observation could satisfy (pass-15 H2). A caller that read
    'zero failures tolerated' where in fact *nothing* is tolerated would reintroduce it, so the
    unreachable case is a distinct value."""
    assert tolerated_failures(200, 0.01) == -1          # upper(0, 200) = 1.4867% > 1%
    assert clopper_pearson_upper(0, 200) > 0.01
    assert tolerated_failures(299, 0.01) == 0           # the smallest n that tolerates zero
    assert tolerated_failures(298, 0.01) == -1


# --------------------------------------------------------------------------- acceptance


def test_the_acceptance_rule_is_the_designs_three_branches():
    a = acceptance(0, 0, 500, 0.01)
    assert a.verdict is Verdict.PASS
    assert acceptance(1, 0, 500, 0.01).verdict is Verdict.PASS      # 0.9452% <= 1%
    assert acceptance(2, 0, 500, 0.01).verdict is Verdict.INCONCLUSIVE   # 1.2538%, but 0.4% <= 1%
    assert acceptance(10, 0, 500, 0.01).verdict is Verdict.FAIL     # 2% > 1% identified


def test_the_ambiguity_pass18_found_resolves_to_inconclusive():
    """At n = 500 with k = 1 and u = 1 the completed proportions are 0.2%-0.4%, below 1%, while the
    completed upper bounds are 0.9452%-1.2538%, crossing it. Revision 4 did not say which supplied
    'the point estimate'; the rule returns INCONCLUSIVE."""
    a = acceptance(1, 1, 500, 0.01)
    assert a.verdict is Verdict.INCONCLUSIVE
    assert a.identification_range == pytest.approx((0.002, 0.004))
    assert a.bound_range[0] == pytest.approx(0.009452282, rel=0, abs=1e-8)
    assert a.bound_range[1] == pytest.approx(0.012537605, rel=0, abs=1e-8)


def test_unresolved_cases_cannot_turn_a_pass_into_a_fail():
    """Pass-18 F6: reading the pessimistic completion as 'the point estimate' would FAIL at k=4,
    u=2, where §7 requires INCONCLUSIVE because only four errors are identified."""
    a = acceptance(4, 2, 500, 0.01)
    assert a.verdict is Verdict.INCONCLUSIVE
    assert a.identification_range == pytest.approx((0.008, 0.012))
    assert a.identified / a.n <= 0.01 < a.bound_range[1]


def test_enough_unresolved_cases_block_a_pass():
    """The direction that matters: unresolved cases can only make the verdict weaker, never
    stronger."""
    assert acceptance(0, 0, 500, 0.01).verdict is Verdict.PASS
    assert acceptance(0, 1, 500, 0.01).verdict is Verdict.PASS           # 0.9452% still inside
    assert acceptance(0, 2, 500, 0.01).verdict is Verdict.INCONCLUSIVE   # 1.2538%


def test_the_acceptance_boundary_exactly_at_the_threshold():
    """A verdict at exactly the threshold, which revision 2 had no test for at all."""
    n = 500
    k = tolerated_failures(n, 0.01)
    assert clopper_pearson_upper(k, n) <= 0.01 < clopper_pearson_upper(k + 1, n)
    assert acceptance(k, 0, n, 0.01).verdict is Verdict.PASS
    assert acceptance(k + 1, 0, n, 0.01).verdict is not Verdict.PASS
    # and exactly on the FAIL boundary: k/n > threshold is strict
    assert acceptance(5, 0, 500, 0.01).verdict is Verdict.INCONCLUSIVE   # 5/500 == 1%, not >
    assert acceptance(6, 0, 500, 0.01).verdict is Verdict.FAIL           # 1.2% > 1%


def test_an_all_abstaining_product_passes_e1_which_is_why_coverage_is_a_separate_gate():
    """Pass-18 F7, in code. An all-UNKNOWN product produces zero directional events, so E1 passes
    at 0.5974%. This test exists so nobody re-adds the claim that a diagnostic prevents it: only
    the (separately blocked) coverage requirement bounds abstention."""
    for threshold in (0.01, 0.02):
        assert acceptance(0, 0, 500, threshold).verdict is Verdict.PASS
    assert clopper_pearson_upper(0, 500) == pytest.approx(0.005973552, rel=0, abs=1e-8)


# --------------------------------------------------------------------------- variance


def test_the_exact_finite_population_correction():
    """`(N-n)/(N-1)`, not `(1 - n/N)`. They differ, and at n = N the exact form is exactly zero."""
    p, n, N = 0.01, 500, 512_633
    assert srs_variance(p, n, N) == pytest.approx(p * (1 - p) / n * (N - n) / (N - 1), rel=1e-12)
    assert srs_variance(p, N, N) == 0.0
    approx = p * (1 - p) / n * (1 - n / N)
    assert srs_variance(p, n, N) != pytest.approx(approx, rel=1e-12)


def test_the_two_stage_variance_does_not_vanish_at_a_full_sample():
    """The case revision 3's formula got wrong (pass-16 F9): every cell half erroneous gives
    `0.25/n` even when every cell is sampled once, because the within-cell term takes no
    finite-population correction."""
    N = 1000
    q = np.full(N, 0.5)
    assert two_stage_variance(q, N, N) == pytest.approx(0.25 / N, rel=1e-12)
    assert two_stage_variance(q, 500, N) == pytest.approx(0.25 / 500, rel=1e-12)


def test_the_two_stage_variance_reduces_to_the_binary_case():
    """With every q_i in {0, 1} the within-cell term is zero and only the between-cell term
    remains, which is the one-stage form up to the ddof convention."""
    N, n = 1000, 500
    q = np.zeros(N)
    q[:100] = 1.0
    between = np.var(q, ddof=1)
    assert two_stage_variance(q, n, N) == pytest.approx((1 - n / N) * between / n, rel=1e-12)


# --------------------------------------------------------------------------- bootstrap


def test_the_percentile_convention_on_a_fixed_replicate_vector():
    """Pass-18 F10's case, with no resampling involved: 50 zeros and 1,950 ones. The 0.025 quantile
    is 0.975 by linear interpolation, against 0 by 'lower' and 1 by 'higher' or 'nearest'. This test
    is what pins the convention; it cannot be satisfied by accident."""
    stats = np.concatenate([np.zeros(50), np.ones(1950)])
    lo, hi = percentile_interval(stats)
    assert lo == pytest.approx(0.975, rel=0, abs=TOL)
    assert hi == pytest.approx(1.0, rel=0, abs=TOL)
    assert np.quantile(stats, 0.025, method="lower") == 0.0
    assert np.quantile(stats, 0.025, method="higher") == 1.0


def test_the_percentile_interval_against_a_hand_computed_case():
    stats = np.arange(101, dtype=np.float64)       # 0..100
    lo, hi = percentile_interval(stats)
    assert (lo, hi) == pytest.approx((2.5, 97.5), rel=0, abs=TOL)


def test_the_percentile_intervals_confidence_is_central_two_sided():
    """Pass-19 F3's companion requirement, and a distinction worth pinning rather than inferring:
    the Clopper-Pearson level is **one-sided** and this one is **central two-sided**. Both are
    written `confidence=0.95` and they mean different tails.

    On replicate values 0…100, 95% gives `[2.5, 97.5]` and 90% gives `[5, 95]` — not `[5, 95]` and
    `[10, 90]`. A level forwarded to the wrong convention would halve or double each tail.
    """
    replicates = np.arange(101, dtype=float)
    assert percentile_interval(replicates, confidence=0.95) == pytest.approx(
        (2.5, 97.5), rel=0, abs=TOL)
    assert percentile_interval(replicates, confidence=0.90) == pytest.approx(
        (5.0, 95.0), rel=0, abs=TOL)
    assert percentile_interval(replicates, confidence=0.99) == pytest.approx(
        (0.5, 99.5), rel=0, abs=TOL)

    # a one-sided reading of 0.90 would give [10, 90]; this is what rules it out
    assert percentile_interval(replicates, confidence=0.90) != pytest.approx(
        (10.0, 90.0), rel=0, abs=TOL)

    # and the level reaches the resampling entry point too
    narrow = percentile_bootstrap(replicates, seed=7, replicates=400, confidence=0.50)
    wide = percentile_bootstrap(replicates, seed=7, replicates=400, confidence=0.99)
    assert wide[0] < narrow[0] <= narrow[1] < wide[1]


def test_the_bootstrap_is_reproducible_from_its_recorded_generator_and_seed():
    v = np.array([-3.0, -1.0, 0.0, 2.0, 5.0, 7.0])
    a = percentile_bootstrap(v, seed=12345, replicates=500)
    b = percentile_bootstrap(v, seed=12345, replicates=500)
    c = percentile_bootstrap(v, seed=54321, replicates=500)
    assert a == b
    assert a != c
    # and the generator is the one the design froze, not whatever numpy defaults to later
    assert BIT_GENERATOR is np.random.PCG64


def test_the_bootstrap_preserves_pairing_within_a_resampled_point():
    """Each value is one point's paired difference, so resampling points can never recombine an
    independent-engine time with another point's own time. Verified by construction: every
    bootstrap statistic is a median of values drawn from the input multiset."""
    v = np.array([-10.0, 0.0, 10.0])
    lo, hi = percentile_bootstrap(v, seed=7, replicates=2000)
    assert lo in set(v.tolist()) and hi in set(v.tolist())


def test_a_degenerate_interval_is_a_property_of_the_data_not_a_defect():
    assert percentile_bootstrap(np.zeros(5), seed=1, replicates=200) == (0.0, 0.0)


def test_a_domain_too_small_to_resample_is_not_estimable():
    """Design §6 reports 'not estimable' rather than an interval."""
    assert percentile_bootstrap(np.array([]), seed=1) is None
    assert percentile_bootstrap(np.array([1.0]), seed=1) is None
    assert percentile_bootstrap(np.array([1.0, 2.0]), seed=1) is not None


def test_the_interval_width_is_not_required_to_be_monotone_in_n():
    """Not an assertion about the implementation — a record of why no such assertion exists. Pass-18
    F10: revision 2 required the interval to widen as the sample shrinks, which rejects correct
    code."""
    wide = percentile_bootstrap(np.array([-1.0, 0.0, 1.0]), seed=3, replicates=2000)
    narrow = percentile_bootstrap(np.array([0.0, 0.0]), seed=3, replicates=2000)
    assert wide == (-1.0, 1.0)
    assert narrow == (0.0, 0.0)          # strictly narrower, from a *smaller* sample
    assert (narrow[1] - narrow[0]) < (wide[1] - wide[0])


def test_censored_pairs_may_not_be_passed_in():
    """Design §3 declares E2's domain as the jointly finite pairs, counted in a status
    cross-tabulation rather than silently dropped here (pass-16 F8)."""
    with pytest.raises(ValueError, match="finite"):
        percentile_bootstrap(np.array([1.0, np.nan, 3.0]), seed=1)
    with pytest.raises(ValueError, match="finite"):
        percentile_bootstrap(np.array([1.0, np.inf]), seed=1)


# --------------------------------------------------------------------------- guards


def test_the_guards_reject_impossible_inputs():
    with pytest.raises(ValueError):
        clopper_pearson_upper(-1, 500)
    with pytest.raises(ValueError):
        clopper_pearson_upper(501, 500)
    with pytest.raises(ValueError):
        clopper_pearson_upper(0, 0)
    with pytest.raises(ValueError):
        clopper_pearson_upper(0, 500, confidence=1.0)
    with pytest.raises(ValueError):
        acceptance(1, 500, 500, 0.01)          # k + u > n
    with pytest.raises(ValueError):
        srs_variance(0.1, 600, 500)            # n > N
    with pytest.raises(ValueError):
        two_stage_variance(np.zeros(10), 5, 11)   # q length != N


def test_a_one_sided_confidence_below_a_half_is_refused():
    """Pass-19's observation about the public API: the acceptance rule's three branches are not
    mutually exclusive on all of `(0, 1)`.

    `acceptance(9, 0, 10, 0.8, confidence=0.01)` used to return PASS, because the 1% "upper bound"
    is 0.6310 and sits below theta, while `k/n = 0.9 > 0.8` satisfies FAIL at the same time. A
    Clopper-Pearson upper bound only dominates the observed proportion once the level is at least
    0.5, so below that it is not a bound at all and the helper now refuses it.
    """
    for bad in (0.01, 0.1, 0.499):
        with pytest.raises(ValueError, match=r"\[0.5, 1\)"):
            clopper_pearson_upper(0, 500, confidence=bad)
        with pytest.raises(ValueError, match=r"\[0.5, 1\)"):
            acceptance(9, 0, 10, 0.8, confidence=bad)

    # and on the accepted domain the upper bound always dominates the point estimate, which is what
    # makes PASS and FAIL disjoint
    for confidence in (0.5, 0.75, 0.95, 0.99):
        for k, n in ((0, 10), (1, 10), (9, 10), (1, 500), (250, 500)):
            assert clopper_pearson_upper(k, n, confidence=confidence) >= k / n


# ------------------------------------------------------------------- E1c, the conditional rate


def test_the_conditional_rate_divides_by_the_claims_not_the_frame():
    """E1c's whole point: the denominator is the claimed subset, not the sample.

    One error among 37 claims is the measured shape of the binding case (frame C, T = 10, where
    E[n_claim] = 36.6791). It bounds at 12.1905%, where the same error against the full frame of 500
    bounds at 0.9452% -- a factor of 13, which is the dilution the estimand exists to undo.
    """
    r = conditional_rate(1, 0, 37)
    assert r.claims == 37 and r.identified == 1
    assert r.identification_range == (1 / 37, 1 / 37)
    assert r.bound_range[0] == pytest.approx(0.121905, abs=1e-6)
    assert r.bound_range == (r.bound_range[0], r.bound_range[0]), "no u, so the endpoints coincide"
    assert clopper_pearson_upper(1, 500) == pytest.approx(0.0094518, abs=1e-6)


def test_unresolved_verdicts_inflate_the_numerator_and_never_the_denominator():
    """The property that is the exact opposite of E1b's, and therefore the one to get backwards.

    The product's verdict is known at every sampled point, so the claim denominator carries no
    missingness. `u` can only widen the range upward.
    """
    r = conditional_rate(1, 2, 37)
    assert r.claims == 37, "u must not enter the denominator"
    assert r.identification_range == (1 / 37, 3 / 37)
    assert r.bound_range == (clopper_pearson_upper(1, 37),
                             clopper_pearson_upper(3, 37))
    assert r.bound_range[0] < r.bound_range[1]

    # k + u cannot exceed the claims, because both count product-PASS observations.
    with pytest.raises(ValueError, match="exceeds the claim denominator"):
        conditional_rate(20, 20, 37)


def test_no_claims_is_undefined_and_not_zero():
    """An all-UNKNOWN product passes E1a and E1b at 0.5974% (design §4). E1c's denominator vanishes
    instead of its numerator, so it must report undefined -- collapsing that to 0.0 would restore
    precisely the concealment it was added to expose.

    It is not, by itself, evidence of abstention: an all-FAIL product also makes no claims.
    """
    r = conditional_rate(0, 0, 0)
    assert r.defined is False
    assert r.identification_range is None and r.bound_range is None
    assert r.claims == 0
    # and the full-frame bound that makes the concealment possible is unchanged
    assert clopper_pearson_upper(0, 500) == pytest.approx(0.0059743, abs=1e-6)

    defined = conditional_rate(0, 0, 1)
    assert defined.defined is True
    assert defined.identification_range == (0.0, 0.0)
    assert defined.bound_range[0] > 0.0, "zero observed errors is not zero uncertainty"


def test_the_conditional_rate_carries_no_verdict_and_cannot_be_gated():
    """Owner decision 2 is 'report it, no bar', and the type is how that is enforced.

    `Acceptance` has a `verdict`; `ConditionalRate` deliberately does not, and takes no threshold
    argument, so there is no way to turn E1c into a gate without changing the design.
    """
    r = conditional_rate(1, 0, 37)
    assert isinstance(r, ConditionalRate)
    assert not hasattr(r, "verdict")
    assert "threshold" not in inspect.signature(conditional_rate).parameters
    assert hasattr(acceptance(1, 0, 500, 0.01), "verdict"), "the gated type still has one"

    # The approximation is named in the object, so it reaches every manifest that stores one.
    assert r.interval_method == "clopper-pearson-approximate"


def test_the_bound_is_approximate_and_the_counterexample_is_kept_as_a_test():
    """Codex pass 31 disproved the first draft's claim that one-sided CP is universally conservative.

    At A = 80,051 PASS structures with exactly 57 comparator-correct, conditioning on 72 claims, the
    true rate exceeds the CP upper bound -- so every outcome with at least one correct observation
    misses it. The exception sits beside a 100% error rate and threatens no figure S3 reports; it is
    kept executable because the claim it refutes is the kind that gets rewritten back in.
    """
    true_rate = 79994 / 80051
    assert clopper_pearson_upper(71, 72) < true_rate
    assert clopper_pearson_upper(71, 72) == pytest.approx(0.999287846835, abs=1e-12)

    # Hypergeometric coverage there is below the nominal 95%.
    coverage = hypergeom.pmf(72, 80051, 79994, 72)
    assert coverage < 0.95
    assert coverage == pytest.approx(0.949985703697819, abs=1e-12)

    # At k = 0 -- where these denominators actually put us -- it is conservative by proof, so the
    # zero-error figures the amendment argues from are sound.
    assert clopper_pearson_upper(0, 37) == pytest.approx(0.0777754, abs=1e-6)


def test_a_claim_denominator_too_small_for_a_one_percent_bar_is_reported_as_such():
    """Why E1c is not gated, as an executable fact rather than a sentence.

    `tolerated_failures` returns -1 -- design §4's unreachable-gate condition -- at every one of the
    four short-threshold claim denominators. It does NOT return -1 at frame B's 45-minute
    denominator, which is why the design says four of eight published combinations and not all.
    """
    for m in (37, 72, 78, 160):
        assert tolerated_failures(m, 0.01) == -1
    assert tolerated_failures(414, 0.01) == 0, "reachable at frame B, T = 45"
    assert tolerated_failures(37, 0.08) == 0, "a looser bar is reachable even at 37"
    assert tolerated_failures(299, 0.01) == 0, "299 claims is the smallest that reaches 1%"
    assert tolerated_failures(473, 0.01) == 1, "473 tolerates one, per design §4's own note"
