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

import numpy as np
import pytest
from scipy.optimize import brentq
from scipy.stats import binom

from locfinder.measure.stats import (
    BIT_GENERATOR,
    Verdict,
    acceptance,
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


@pytest.mark.parametrize("n", [8, 60, 150, 400, 500, 628])
@pytest.mark.parametrize("k", [0, 1, 2, 3, 4])
def test_the_upper_bound_matches_an_independently_inverted_binomial_tail(k, n):
    """The decisive fixture. Pass-15's wrong formula and pass-18's one-cell variant both differ from
    this at some (k, n), and 1e-10 leaves no room to hide a difference that could flip a verdict."""
    assert clopper_pearson_upper(k, n) == pytest.approx(
        binomial_tail_inversion_upper(k, n), abs=TOL)


def test_the_pass15_counterexample_is_rejected():
    """The explicit regression: the formula that satisfied every zero-event fixture."""
    def wrong(k, n):
        return k / n + (1 - k / n) * (1 - 0.05 ** (1 / n))

    # it agrees at k = 0 -- which is exactly why the old fixtures passed it
    assert wrong(0, 400) == pytest.approx(clopper_pearson_upper(0, 400), abs=TOL)
    # and disagrees where the verdict is decided
    assert clopper_pearson_upper(1, 400) == pytest.approx(0.01180430445398703, abs=TOL)
    assert wrong(1, 400) == pytest.approx(0.009942702139977564, abs=TOL)
    assert clopper_pearson_upper(1, 400) > 0.01 > wrong(1, 400)   # it flips the 1% decision


def test_the_pass18_single_cell_variant_is_rejected():
    """Pass-18 F9: correct everywhere except n=400, k=1. A 0.002 tolerance accepted it."""
    def wrong(k, n):
        if (k, n) == (1, 400):
            return 0.009942702139977564
        return clopper_pearson_upper(k, n)

    assert wrong(1, 400) == pytest.approx(clopper_pearson_upper(1, 400), abs=0.002)   # the hole
    assert wrong(1, 400) != pytest.approx(clopper_pearson_upper(1, 400), abs=TOL)     # closed


def test_the_zero_failure_closed_form():
    """`1 - (1-c)**(1/n)`, an independent check of this formula at k = 0."""
    for n in (8, 60, 150, 400, 500):
        assert clopper_pearson_upper(0, n) == pytest.approx(1 - 0.05 ** (1 / n), abs=TOL)


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


@pytest.mark.parametrize("k,n", [(1, 150), (1, 500), (3, 500), (10, 500), (250, 500)])
def test_the_lower_bound_matches_an_independently_inverted_binomial_tail(k, n):
    assert clopper_pearson_lower(k, n) == pytest.approx(
        binomial_tail_inversion_lower(k, n), abs=TOL)


def test_the_lower_bound_is_one_sided_not_two_sided():
    """Pass-18 F9's case. The two-sided value passes a zero endpoint check and moves correctly with
    the confidence level, so only a non-zero fixture separates them."""
    assert clopper_pearson_lower(1, 500) == pytest.approx(0.000102581, abs=1e-9)
    two_sided = 1 - 0.975 ** (1 / 500)
    assert two_sided == pytest.approx(0.000050634, abs=1e-9)
    assert clopper_pearson_lower(1, 500) != pytest.approx(two_sided, abs=1e-6)


def test_the_complementary_identity_between_the_two_bounds():
    """`CP_lower(k, n, c) == 1 - CP_upper(n - k, n, c)` by the Beta symmetry. An identity check
    catches a swapped parameter that a one-sided fixture might not."""
    for n in (150, 500):
        for k in range(1, 6):
            assert clopper_pearson_lower(k, n) == pytest.approx(
                1 - clopper_pearson_upper(n - k, n), abs=TOL)


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
    assert clopper_pearson_upper(1, 473) == pytest.approx(0.009989707, abs=1e-8)
    assert clopper_pearson_upper(1, 500) == pytest.approx(0.009452282, abs=1e-8)
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
    assert a.bound_range[0] == pytest.approx(0.009452282, abs=1e-8)
    assert a.bound_range[1] == pytest.approx(0.012537605, abs=1e-8)


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
    assert clopper_pearson_upper(0, 500) == pytest.approx(0.005973552, abs=1e-8)


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
    assert lo == pytest.approx(0.975, abs=TOL)
    assert hi == pytest.approx(1.0, abs=TOL)
    assert np.quantile(stats, 0.025, method="lower") == 0.0
    assert np.quantile(stats, 0.025, method="higher") == 1.0


def test_the_percentile_interval_against_a_hand_computed_case():
    stats = np.arange(101, dtype=np.float64)       # 0..100
    lo, hi = percentile_interval(stats)
    assert (lo, hi) == pytest.approx((2.5, 97.5), abs=TOL)


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
