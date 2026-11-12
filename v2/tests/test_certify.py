"""Does the certified comparator certify? Step 4 phase 4a.2.

Written before the module in the sense that matters: every **expected value** below is derived from
the design and from the step 4 plan's W5 row, not read off a run of `certify.py`. That is the
distinction §12's conformance-suite artifact asks for, and Codex pass 38 F4 is what happens when a
figure is taken from the implementation instead.
"""
import math
import random
from fractions import Fraction

import pytest

from locfinder.measure import certify as c
from locfinder.measure import exact as ex


# ------------------------------------------------------------------ the interval primitive

@pytest.mark.parametrize("k", [0, 1, 8, 53, 100])
def test_sqrt_interval_brackets_the_root_exactly(k):
    """`lo <= sqrt(q) < hi`, checked by squaring so the assertion needs no root of its own."""
    rng = random.Random(20261112)
    for _ in range(200):
        q = Fraction(rng.randrange(1, 10 ** 12), rng.randrange(1, 10 ** 6))
        lo, hi = c.sqrt_interval(q, k)
        assert lo * lo <= q, f"lower bound above the root at k={k}, q={q}"
        assert hi * hi > q, f"upper bound not above the root at k={k}, q={q}"


@pytest.mark.parametrize("k", [0, 1, 2, 3, 8])
def test_sqrt_interval_brackets_a_radicand_just_below_a_lattice_square(k):
    """The hard inputs are the ones that sit just under a perfect square of the lattice.

    Uniform random radicands do not reach them: the mutation harness replaced the floor with a
    **ceiling** and all 34 fixtures passed, because a ceiling only breaks the lower bound when
    rounding the scaled radicand up crosses a perfect square. Witness found by search at `k=1`,
    `q = 130461413/6`, where the ceiling bound is `4663` and `4663**2 > q`. This family is
    constructed to sit there on purpose, so the bound is tested where it can fail.
    """
    rng = random.Random(4663)
    scale = 1 << (2 * k)
    for _ in range(400):
        s = rng.randrange(2, 10 ** 5)
        # just under (s / 2**k)**2, by a fraction of one lattice step of the scaled radicand
        q = Fraction(s * s - 1, scale) + Fraction(1, scale * rng.randrange(2, 7))
        lo, hi = c.sqrt_interval(q, k)
        assert lo * lo <= q, f"lower bound above the root at k={k}, q={q}, lo={lo}"
        assert hi * hi > q, f"upper bound not above the root at k={k}, q={q}, hi={hi}"


@pytest.mark.parametrize("k", [0, 1, 8, 53])
def test_sqrt_interval_width_is_exactly_two_to_the_minus_k(k):
    for q in (Fraction(2), Fraction(1, 3), Fraction(10 ** 20), Fraction(1, 10 ** 20)):
        lo, hi = c.sqrt_interval(q, k)
        assert hi - lo == Fraction(1, 1 << k)


def test_sqrt_interval_is_nested_as_precision_rises():
    """Refinement is only sound if a finer interval sits inside the coarser one."""
    rng = random.Random(7)
    for _ in range(100):
        q = Fraction(rng.randrange(1, 10 ** 9), rng.randrange(1, 10 ** 5))
        prev = c.sqrt_interval(q, 4)
        for k in range(5, 24):
            lo, hi = c.sqrt_interval(q, k)
            assert prev[0] <= lo and hi <= prev[1], f"not nested at k={k}, q={q}"
            prev = (lo, hi)


def test_sqrt_interval_handles_zero_and_perfect_squares():
    assert c.sqrt_interval(0, 10)[0] == 0
    lo, hi = c.sqrt_interval(Fraction(4), 10)
    assert lo == 2 and hi == 2 + Fraction(1, 1024)
    lo, hi = c.sqrt_interval(Fraction(9, 16), 20)
    assert lo == Fraction(3, 4)


def test_sqrt_interval_contains_the_correctly_rounded_root():
    """The two primitives must agree: `rational_sqrt`'s answer lies in a loose enough bracket."""
    rng = random.Random(99)
    for _ in range(200):
        q = Fraction(rng.randrange(1, 10 ** 10), rng.randrange(1, 10 ** 4))
        lo, hi = c.sqrt_interval(q, 20)
        root = ex.rational_sqrt(q)
        assert float(lo) - 1e-6 <= root <= float(hi) + 1e-6


def test_sqrt_interval_refuses_a_negative_radicand():
    with pytest.raises(ValueError):
        c.sqrt_interval(Fraction(-1), 8)


# ------------------------------------------------------------------ interval arithmetic

def test_intervals_contain_the_real_results_they_bracket():
    a = c.Interval(Fraction(1), Fraction(2))
    b = c.Interval(Fraction(10), Fraction(11))
    assert (a + b) == c.Interval(Fraction(11), Fraction(13))
    assert a.scaled(Fraction(3)) == c.Interval(Fraction(3), Fraction(6))
    assert a.scaled(Fraction(-3)) == c.Interval(Fraction(-6), Fraction(-3))
    assert a.divided_by(b) == c.Interval(Fraction(1, 11), Fraction(2, 10))


def test_dividing_by_an_interval_that_reaches_zero_is_refused_not_silent():
    a = c.Interval(Fraction(1), Fraction(2))
    with pytest.raises(ZeroDivisionError):
        a.divided_by(c.Interval(Fraction(0), Fraction(1)))


def test_an_inverted_interval_cannot_be_built():
    with pytest.raises(ValueError):
        c.Interval(Fraction(2), Fraction(1))


# ------------------------------------------------------------------ W5, the reason this exists

def _w5() -> tuple[c.Journey, c.Journey]:
    """Pass 37 F1's witness, from the step 4 plan's W5 row.

    Record A is `(0,0),(1,0),(2,1)` at cost 1 and time 2400; record B is `(0,0),(1,0)` at cost
    `0.4142135623730951`. Origin `(0,0)`, destination `(1,0)`, so each journey traverses from the
    first vertex to the second.

    A's real cost is therefore `1 / (1 + sqrt(2))` = `sqrt(2) - 1` = 0.414213562373095048...,
    and B's is the binary64 `0.4142135623730951`, which is **larger**. A is genuinely cheaper; the
    convention ties them and §2.4's time discriminator then reports B's 1 s.
    """
    a = c.Journey(
        partials=(c.Partial(geometry=((0.0, 0.0), (1.0, 0.0), (2.0, 1.0)),
                            seg_o=0, t_o=Fraction(0), seg_d=0, t_d=Fraction(1),
                            cost=1.0),),
        label="A: the 2400 s record",
    )
    b = c.Journey(
        partials=(c.Partial(geometry=((0.0, 0.0), (1.0, 0.0)),
                            seg_o=0, t_o=Fraction(0), seg_d=0, t_d=Fraction(1),
                            cost=0.4142135623730951),),
        label="B: the 1 s record",
    )
    return a, b


def test_w5_real_costs_are_ordered_the_way_the_design_says():
    """Independent of the comparator: `sqrt(2) - 1` is strictly below the binary64 B carries."""
    # sqrt(2) - 1 to 40 digits, from the decimal expansion and not from this module
    import decimal
    decimal.getcontext().prec = 60
    a_real = decimal.Decimal(2).sqrt() - 1
    b_exact = Fraction(0.4142135623730951)
    assert a_real < decimal.Decimal(b_exact.numerator) / decimal.Decimal(b_exact.denominator)


def test_w5_the_convention_ties_the_two_costs():
    """The premise of the finding: in binary64 these two costs are the same number."""
    a, b = _w5()
    assert a.rounded_cost() == b.rounded_cost()


def test_w5_is_certified_as_differing_and_names_both_selections():
    """The convention picks B on the time discriminator; the real argmin is A."""
    a, b = _w5()
    got = c.certify_selection([a, b], chosen=1)        # the convention selected B
    assert got.status == c.DIFFERS
    assert got.convention == "B: the 1 s record"
    assert got.certified == "A: the 2400 s record"
    assert not got.agrees


def test_w5_certifies_agreement_when_the_convention_picks_the_real_argmin():
    a, b = _w5()
    got = c.certify_selection([a, b], chosen=0)
    assert got.status == c.AGREES
    assert got.agrees


# ------------------------------------------------------------------ the three outcomes

def test_an_exact_tie_is_unresolved_and_is_not_agreement():
    """Two identical rational costs never separate, and `UNRESOLVED` is the correct answer.

    `exactly_tied` is what distinguishes the correct answer from the failure this phase is boxed
    against: `UNRESOLVED` on an exact tie is right, on an unequal pair it is the approach failing.
    """
    a = c.Journey(full_edge_costs=(1.5,), label="a")
    b = c.Journey(full_edge_costs=(1.5,), label="b")
    got = c.certify_selection([a, b], chosen=0, max_precision=64)
    assert got.status == c.UNRESOLVED
    assert got.exactly_tied is True
    assert not got.agrees, "an undecided comparison must never be counted as agreement"


def test_a_plainly_unequal_pair_resolves_at_the_lowest_precision():
    """The common case must not pay for the hard one."""
    a = c.Journey(full_edge_costs=(1.0,), label="a")
    b = c.Journey(full_edge_costs=(2.0,), label="b")
    got = c.certify_selection([a, b], chosen=0)
    assert got.status == c.AGREES
    assert got.precision == 8, "the first precision tried should settle an obvious gap"


def test_unresolved_wins_over_agrees_when_any_pair_is_undecided():
    """Three candidates: one clearly worse, one an exact tie. The tie decides the status."""
    a = c.Journey(full_edge_costs=(1.0,), label="a")
    tie = c.Journey(full_edge_costs=(1.0,), label="tie")
    worse = c.Journey(full_edge_costs=(9.0,), label="worse")
    got = c.certify_selection([a, tie, worse], chosen=0, max_precision=64)
    assert got.status == c.UNRESOLVED


def test_a_differing_candidate_beats_an_undecided_one():
    """A certified cheaper alternative is a `DIFFERS`, whatever else is undecided."""
    picked = c.Journey(full_edge_costs=(5.0,), label="picked")
    tie = c.Journey(full_edge_costs=(5.0,), label="tie")
    cheaper = c.Journey(full_edge_costs=(1.0,), label="cheaper")
    got = c.certify_selection([picked, tie, cheaper], chosen=0, max_precision=64)
    assert got.status == c.DIFFERS
    assert got.certified == "cheaper"


# ------------------------------------------------------------------ the terms §2.4 item 6 names

def test_a_connector_enters_the_cost_at_the_access_speed():
    """`residual / 1.26`, and the residual is a square root — so the term is irrational."""
    j = c.Journey(connector_sq=(Fraction(4),), label="j")
    interval = j.cost_interval(40)
    expected = Fraction(2) / c.ACCESS_SPEED_MPS
    assert interval.contains(expected)
    assert interval.width < Fraction(1, 10 ** 10)


def test_a_full_edge_is_exact_and_needs_no_refinement():
    j = c.Journey(full_edge_costs=(0.1, 0.2, 0.3), label="j")
    interval = j.cost_interval(8)
    assert interval.lo == interval.hi, "a rational cost has a degenerate interval"
    assert interval.lo == Fraction(0.1) + Fraction(0.2) + Fraction(0.3)


def test_the_rounded_cost_is_the_conventions_fsum_and_not_the_real_total():
    """W1's case: the exactly-rounded sum of `0.1, 0.2, 0.3` is `0.6`, and left accumulation is not.

    This pins that `rounded_cost` really is §2.4 item 6's rule and not a convenient re-derivation.
    """
    j = c.Journey(full_edge_costs=(0.1, 0.2, 0.3), label="j")
    assert j.rounded_cost() == 0.6
    run = 0.0
    for t in (0.1, 0.2, 0.3):
        run += t
    assert run == 0.6000000000000001


def test_a_zero_length_record_contributes_the_normative_zero_and_does_not_divide():
    """§2.4 item 7's zero-total rule, reaching the comparator rather than a ZeroDivisionError."""
    p = c.Partial(geometry=((5.0, 5.0), (5.0, 5.0), (5.0, 5.0)),
                  seg_o=0, t_o=Fraction(0), seg_d=1, t_d=Fraction(1), cost=1000.0)
    j = c.Journey(partials=(p,), label="j")
    assert j.cost_interval(32) == c.Interval(Fraction(0), Fraction(0))


def test_a_cross_segment_span_brackets_the_real_fraction():
    """Lengths 10 and 10, origin at t=1/2 on segment 0, destination at t=1/4 on segment 1.

    The span is `5 + 2.5 = 7.5` of a total of 20, so the fraction is exactly `0.375` — a case where
    the real value is rational and can be asserted outright.
    """
    p = c.Partial(geometry=((0.0, 0.0), (10.0, 0.0), (20.0, 0.0)),
                  seg_o=0, t_o=Fraction(1, 2), seg_d=1, t_d=Fraction(1, 4), cost=1.0)
    interval = p.fraction_interval(40)
    assert interval.contains(Fraction(3, 8))
    assert interval.width < Fraction(1, 10 ** 10)


def test_a_span_across_three_segments_includes_the_whole_middle_one():
    """Every other span fixture uses adjacent segments, where there is no middle to drop.

    The mutation harness caught that: removing `qs[seg_o + 1:seg_d]` from the span changed nothing
    in any fixture, because none of them spanned more than two segments. Lengths 5, 10, 10 with the
    origin at the midpoint of segment 0 and the destination at the midpoint of segment 2 give
    `2.5 + 10 + 5 = 17.5` of a total of 25, which is exactly `0.7` — derived from the rule, not run.
    """
    g = ((0.0, 0.0), (3.0, 4.0), (3.0, 14.0), (9.0, 22.0))      # lengths 5, 10, 10
    p = c.Partial(geometry=g, seg_o=0, t_o=Fraction(1, 2), seg_d=2, t_d=Fraction(1, 2), cost=1.0)
    interval = p.fraction_interval(40)
    assert interval.contains(Fraction(7, 10))
    assert interval.width < Fraction(1, 10 ** 10)
    # dropping the middle segment would give 7.5 / 25 = 0.3, which must be outside the bracket
    assert not interval.contains(Fraction(3, 10))


def test_the_span_is_symmetric_in_the_two_occurrences():
    g = ((0.0, 0.0), (3.0, 4.0), (3.0, 14.0))
    one = c.Partial(geometry=g, seg_o=0, t_o=Fraction(1, 3), seg_d=1, t_d=Fraction(2, 3),
                    cost=1.0).fraction_interval(32)
    other = c.Partial(geometry=g, seg_o=1, t_o=Fraction(2, 3), seg_d=0, t_d=Fraction(1, 3),
                      cost=1.0).fraction_interval(32)
    assert one == other


def test_an_irrational_fraction_is_bracketed_and_never_claimed_exact():
    """`1 / (1 + sqrt(2))` has no rational value, so the interval must stay a proper interval."""
    p = c.Partial(geometry=((0.0, 0.0), (1.0, 0.0), (2.0, 1.0)),
                  seg_o=0, t_o=Fraction(0), seg_d=0, t_d=Fraction(1), cost=1.0)
    interval = p.fraction_interval(60)
    assert interval.lo < interval.hi, "an irrational quantity must not collapse to a point"
    import decimal
    decimal.getcontext().prec = 60
    real = 1 / (1 + decimal.Decimal(2).sqrt())
    assert decimal.Decimal(interval.lo.numerator) / decimal.Decimal(interval.lo.denominator) < real
    assert real < decimal.Decimal(interval.hi.numerator) / decimal.Decimal(interval.hi.denominator)


# ------------------------------------------------------------------ guards

def test_certifying_an_empty_candidate_set_is_refused():
    with pytest.raises(ValueError):
        c.certify_selection([], chosen=0)


def test_a_selection_outside_the_candidate_set_is_refused():
    j = c.Journey(full_edge_costs=(1.0,), label="j")
    with pytest.raises(IndexError):
        c.certify_selection([j], chosen=3)


def test_a_non_finite_cost_is_refused_rather_than_propagated():
    j = c.Journey(full_edge_costs=(math.inf,), label="j")
    with pytest.raises(ValueError):
        j.cost_interval(8)
