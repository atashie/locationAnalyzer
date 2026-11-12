"""Fixtures for `measure/exact.py` — design §12 item 1, phase 4a.1.

Written before the module, from the five witnesses in
`docs/plans/2026-11-11-step4-comparator-plan.md`. Each test names the witness it pins and whether it
pins a **repair** (the current code is wrong) or a **convention** (the current code is right and an
alternative rule would change it).

The point of the module under test is that every comparison which *decides* something is made on an
exact value, and every quantity that cannot be exact is **correctly rounded once**. These tests
therefore check exact values with `Fraction` and rounded values against the specific binary64 they
must equal — never with a tolerance, which would hide exactly the defects the witnesses describe.
"""
import decimal
import math
import random
from fractions import Fraction

import pytest

from locfinder.measure import exact


# --------------------------------------------------------------------- correctly rounded sqrt

@pytest.mark.parametrize("q,root", [
    (Fraction(0), 0.0),
    (Fraction(1), 1.0),
    (Fraction(4), 2.0),
    (Fraction(9, 4), 1.5),
    (Fraction(1, 16), 0.25),
    (Fraction(2 ** 100), float(2 ** 50)),
    (Fraction(1, 2 ** 100), float(Fraction(1, 2 ** 50))),
])
def test_rational_sqrt_is_exact_on_perfect_squares(q, root):
    assert exact.rational_sqrt(q) == root


def test_rational_sqrt_beats_math_hypot_on_the_pass37_witness():
    """Pass 37's confirmation: CPython's `hypot` is not correctly rounded here.

    Built from `y = 2**26 + 1`, `x = y*y`, both scaled by `2**-30`, so the exact norm sits strictly
    below the rounding midpoint and `hypot` rounds the wrong way.
    """
    dx, dy = 4194304.125000001, 0.06250000093132257
    q = Fraction(dx) ** 2 + Fraction(dy) ** 2
    correct = exact.rational_sqrt(q)
    assert correct == 4194304.125000001
    assert math.hypot(dx, dy) == 4194304.125000002
    assert correct != math.hypot(dx, dy)
    # And the certificate: the exact norm is strictly below the midpoint between the two.
    midpoint = (Fraction(correct) + Fraction(math.nextafter(correct, math.inf))) / 2
    assert q < midpoint ** 2


def test_rational_sqrt_rounds_a_midpoint_to_even():
    """A rational whose root is exactly a midpoint between two binary64 values."""
    lo = 1.0
    hi = math.nextafter(lo, math.inf)
    mid = (Fraction(lo) + Fraction(hi)) / 2
    assert exact.rational_sqrt(mid ** 2) == lo, "ties must go to the even significand"
    lo2 = hi
    hi2 = math.nextafter(lo2, math.inf)
    mid2 = (Fraction(lo2) + Fraction(hi2)) / 2
    assert exact.rational_sqrt(mid2 ** 2) == hi2, "ties must go to the even significand"


def test_rational_sqrt_rejects_negative():
    with pytest.raises(ValueError):
        exact.rational_sqrt(Fraction(-1, 2))


def _brute_force_root(q: Fraction) -> float:
    """An independent oracle for the nearest binary64 to `sqrt(q)`.

    Deliberately written a different way from `rational_sqrt` — `decimal` rather than a binade
    lattice and `isqrt` — so agreement between the two is evidence rather than a restatement. The
    high-precision decimal only *locates* the answer; which of the two neighbouring binary64 values
    is nearer is then decided on **exact rationals**, so the oracle is exact even though `Decimal`
    is not.

    A first version walked `nextafter` from an initial guess. That is correct and unusable: for a
    subnormal radicand `float(q)` underflows to 0, the walk starts at 1.0, and it has about 2**62
    steps to take. The test suite hit its timeout rather than failing, which is its own small
    lesson about oracles.
    """
    if q == 0:
        return 0.0
    with decimal.localcontext() as ctx:
        ctx.prec = 120
        ctx.Emin, ctx.Emax = -999999, 999999
        approx = (decimal.Decimal(q.numerator) / decimal.Decimal(q.denominator)).sqrt()
        cand = float(approx)
    if not math.isfinite(cand):
        raise AssertionError(f"oracle overflowed on {q}")
    # Settle onto the largest binary64 whose square is <= q, exactly.
    while cand > 0 and Fraction(cand) ** 2 > q:
        cand = math.nextafter(cand, 0.0)
    while Fraction(math.nextafter(cand, math.inf)) ** 2 <= q:
        cand = math.nextafter(cand, math.inf)
    lo, hi = cand, math.nextafter(cand, math.inf)
    # Nearer in value, not in squared value: compare against the exact midpoint.
    mid = (Fraction(lo) + Fraction(hi)) / 2
    if q < mid ** 2:
        return lo
    if q > mid ** 2:
        return hi
    return lo if int(lo / math.ulp(lo)) % 2 == 0 else hi


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_rational_sqrt_agrees_with_an_independent_oracle(seed):
    """Cross-checked against a differently-written oracle over random rationals."""
    rng = random.Random(seed)
    for _ in range(200):
        q = Fraction(rng.getrandbits(60) | 1, rng.getrandbits(60) | 1)
        assert exact.rational_sqrt(q) == _brute_force_root(q), q


def _lattice(q: Fraction) -> tuple[Fraction, Fraction]:
    """`(u, scaled)` for `q`, mirroring `rational_sqrt`'s binade search."""
    exp = (q.numerator.bit_length() - q.denominator.bit_length()) // 2
    while exact._pow2(2 * exp) > q:
        exp -= 1
    while exact._pow2(2 * (exp + 1)) <= q:
        exp += 1
    u = exact._pow2(max(exp - 52, -1074))
    return u, q / (u * u)


@pytest.mark.parametrize("seed", [4, 5])
def test_the_midpoint_comparison_absorbs_a_rounded_integer_root(seed):
    """The algorithm's one non-obvious property, stated as narrowly as the evidence supports.

    Taking the integer root of a *binary64 rounding* of the scaling changes `k` on about 13% of
    random radicands and changes the answer on none, because the comparison that decides is against
    the original rational. This test pins that.

    **It is not a claim that `_decide` tolerates an arbitrary off-by-one `k`** — it does not, and an
    earlier draft of this test asserted that and failed within 300 radicands. `k = K+1` returns
    `(K+1)*u` whatever `q` is, which is wrong whenever the correct answer was `K*u`. The guarantee
    comes from which `k` a rounding can actually produce, not from the comparison alone.
    """
    rng = random.Random(seed)
    changed_k = 0
    for _ in range(300):
        q = Fraction(rng.getrandbits(100) | 1, rng.getrandbits(100) | 1)
        u, scaled = _lattice(q)
        k = math.isqrt(scaled.numerator // scaled.denominator)
        k_rounded = math.isqrt(int(float(scaled)))
        changed_k += k != k_rounded
        assert exact._decide(q, k_rounded, u) == exact._decide(q, k, u), q
    assert changed_k > 0, "the sample must actually exercise a changed index"


def test_decide_does_not_tolerate_an_arbitrary_off_by_one_index():
    """The counter-statement, so the property above is not read as more than it is.

    `_decide` is a two-candidate choice. Hand it the wrong pair and it returns a value from the
    wrong pair, which is why the integer-root step may be cheap but may not be *arbitrary*.
    """
    q = Fraction(879683442691881786678409274839, 91506331205865577578825519785)
    u, scaled = _lattice(q)
    k = math.isqrt(scaled.numerator // scaled.denominator)
    assert exact._decide(q, k + 1, u) != exact._decide(q, k, u)


def test_rational_sqrt_is_correct_in_the_subnormal_range():
    """The lattice unit is floored at the smallest subnormal, so one binade holds every subnormal.

    Without that floor the lattice would be finer than the representable values and the result
    would be rounded a second time by `float()`.
    """
    for q in (Fraction(1, 2 ** 2100),
              Fraction(3, 2 ** 2101),
              Fraction(7, 2 ** 2149),
              Fraction(1, 2 ** 2149)):
        got = exact.rational_sqrt(q)
        assert got == _brute_force_root(q), q
        assert got < 2.0 ** -1022, "the witness must actually land among the subnormals"


def test_subnormal_lattice_floor_prevents_a_double_rounding():
    """The witness that the subnormal floor is load-bearing, found by search.

    Without `max(..., _MIN_SUBNORMAL_EXP)` the lattice is finer than the representable subnormals,
    so `float()` rounds a second time and the answer is one subnormal step out.
    """
    q = Fraction(397655352315, 2 ** 2100)
    assert exact.rational_sqrt(q) == 5.227065821602e-311
    assert exact.rational_sqrt(q) == _brute_force_root(q)
    assert exact.rational_sqrt(q) < 2.0 ** -1022


# --------------------------------------------------------------------- W2, the cancelling dot product

W2_SEGMENT = (0.0, 0.0, 1e-6, 1e-6)
W2_ORIGIN = (122.09, -122.08999999999999)


def test_w2_exact_projection_is_interior_where_binary64_gives_zero():
    """REPAIR. The two terms of the dot product cancel to exactly 0.0 in binary64.

    Current behaviour attaches at the segment start: parameter 0, no network travel, 137.03 s PASS.
    The exact parameter is interior and the journey is 847.58 s FAIL.
    """
    px, py = W2_ORIGIN
    ax, ay, bx, by = W2_SEGMENT
    # the defect, stated as an assertion so the fixture fails if the platform ever changes
    assert (px - ax) * (bx - ax) + (py - ay) * (by - ay) == 0.0
    t = exact.exact_projection(px, py, ax, ay, bx, by)
    assert isinstance(t, Fraction)
    assert t > 0, "the exact parameter is strictly interior"
    assert float(t) == 7.105427357601002e-09
    # the exact dot product, for the record
    dot = (Fraction(px) - Fraction(ax)) * (Fraction(bx) - Fraction(ax)) + \
          (Fraction(py) - Fraction(ay)) * (Fraction(by) - Fraction(ay))
    assert dot == Fraction(1.4210854715202003e-20)


def test_w2_is_not_reachable_by_a_summation_rule_on_the_formed_products():
    """Pass 37 F8, pinned: `fsum` of the already-rounded products cannot reach W2.

    Reassociating *can*, because `dx == dy` in this witness — so W2 excludes a summation
    replacement and does not on its own select exact rationals as the method.
    """
    px, py = W2_ORIGIN
    ax, ay, bx, by = W2_SEGMENT
    dx, dy = bx - ax, by - ay
    assert math.fsum([(px - ax) * dx, (py - ay) * dy]) == 0.0
    assert math.fsum([px - ax, py - ay]) * dx == 1.4210854715202003e-20


# --------------------------------------------------------------------- W3, subtraction at the bound

W3_SEGMENT = (-1e7, 0.0, 1e7, 0.0)


def test_w3_exact_projection_does_not_round_onto_the_endpoint():
    """REPAIR. The origin is 1.86e-9 m before the endpoint; binary64 rounds the projection onto it,
    producing an empty route and 1.48e-9 s where the geometric network time is 931.32 s.
    """
    px = math.nextafter(1e7, 0.0)
    ax, ay, bx, by = W3_SEGMENT
    assert (px - ax) == (bx - ax), "the binary64 subtraction loses the gap"
    t = exact.exact_projection(px, 0.0, ax, ay, bx, by)
    assert t < 1, "the exact parameter is strictly inside the segment"
    assert exact.scaled_segment_length(ax, ay, bx, by, 1 - t) == 1.862645149230957e-09


# --------------------------------------------------------------------- W1, the summation convention

W1_GEOMETRY = ((0.0, 0.0), (0.1, 0.0), (0.1, 0.2), (0.1, 0.5))


def test_w1_total_length_is_the_exactly_rounded_sum():
    """CONVENTION. Lengths 0.1, 0.2, 0.3. `fsum` gives 0.6; naive left accumulation gives
    0.6000000000000001 and is rejected — over the exact rationals 0.6 is nearer the true total by a
    factor of three.
    """
    assert exact.total_length(W1_GEOMETRY) == 0.6
    run = 0.0
    for a, b in zip(W1_GEOMETRY, W1_GEOMETRY[1:]):
        run += exact.segment_length(*a, *b)
    assert run == 0.6000000000000001, "the rejected rule, pinned so the choice stays visible"


def test_w1_first_vertex_fraction_is_the_1000_second_answer():
    """CONVENTION, and pass 37 F2 corrected this one.

    Revision 1 of the plan said W1's required answer was a tie reporting 1 s. Under the adopted
    rule the fraction is 0.16666666666666669, which is the **1,000 s** answer and what the code
    already does. 1 s is reachable only by the rejected left accumulation.
    """
    total = exact.total_length(W1_GEOMETRY)
    prefix = exact.prefix_arclength(W1_GEOMETRY, 0, Fraction(1))
    assert exact.traversal_fraction(prefix, total) == 0.16666666666666669
    assert 0.1 / 0.6000000000000001 == 0.16666666666666666, "the rejected rule's answer"


def test_the_factor_of_three_claim_is_exact():
    """The reason left accumulation is rejected, as an exact statement rather than a reading."""
    lengths = [exact.segment_length(*a, *b)
               for a, b in zip(W1_GEOMETRY, W1_GEOMETRY[1:])]
    true_total = sum((Fraction(x) for x in lengths), Fraction(0))
    err_fsum = abs(Fraction(math.fsum(lengths)) - true_total)
    err_left = abs(Fraction(0.6000000000000001) - true_total)
    assert err_fsum * 3 == err_left


# --------------------------------------------------------------------- W4, the same-edge span

def test_w4_same_edge_span_is_measured_as_a_span_not_a_difference_of_prefixes():
    """REPAIR of an ambiguity rather than of a number — pass 37 F5.

    Two "exactly rounded" readings of the same-edge interval disagree across the published 600 s
    limit: `|RN(s_d/L) - RN(s_o/L)|` gives 666.13 s FAIL and `RN(|s_d-s_o|/L)` gives 558.79 s PASS.
    Neither is adopted. The span is computed **from the interval itself**, which removes the choice:
    the cancelling prefixes never appear, so there is nothing to cancel badly.
    """
    ax, ay, bx, by = W3_SEGMENT
    geom = ((ax, ay), (bx, by))
    t_o = exact.exact_projection(math.nextafter(1e7, 0.0), 0.0, ax, ay, bx, by)
    t_d = Fraction(1)
    f = exact.same_edge_fraction(geom, 0, t_o, 0, t_d)
    assert f == 9.313225746154785e-17
    assert f * 6e18 == 558.7935447692871
    assert f * 6e18 < 600.0, "PASS at the published limit"
    # And the reason the span rule is NECESSARY, not merely tidier. Measured here rather than
    # assumed: the exact gap to the endpoint, 1.862645149230957e-9 m, is **exactly half an ulp**
    # of the 2e7 prefix, and 2e7 has an even significand — so rounding the prefix to binary64 puts
    # it back onto the endpoint under round-half-to-even and the traversal vanishes. That is W3's
    # own defect resurfacing one layer up, AFTER the projection has been made exact.
    total = exact.total_length(geom)
    s_o = exact.prefix_arclength(geom, 0, t_o)
    s_d = exact.prefix_arclength(geom, 0, t_d)
    exact_gap = (1 - t_o) * (Fraction(bx) - Fraction(ax))
    assert exact_gap == Fraction(math.ulp(2e7)) / 2
    assert int(2e7 / math.ulp(2e7)) % 2 == 0, "even significand, so the tie rounds to 2e7"
    assert s_o == s_d == 2e7
    assert abs((s_d / total) - (s_o / total)) == 0.0, "the prefix difference loses the journey"


def test_same_edge_span_spans_whole_intermediate_segments():
    """The span formula over several segments: `(1-t_o)*L_i + L_{i+1} + ... + t_d*L_j`."""
    geom = ((0.0, 0.0), (3.0, 4.0), (3.0, 14.0), (9.0, 22.0))   # lengths 5, 10, 10
    assert exact.total_length(geom) == 25.0
    # from the midpoint of segment 0 to the midpoint of segment 2: 2.5 + 10 + 5 = 17.5
    f = exact.same_edge_fraction(geom, 0, Fraction(1, 2), 2, Fraction(1, 2))
    assert f == 17.5 / 25.0
    # order must not matter to the magnitude
    assert exact.same_edge_fraction(geom, 2, Fraction(1, 2), 0, Fraction(1, 2)) == f


def test_scaled_segment_length_rounds_once_not_twice():
    """`t * L` is computed as `sqrt(t^2 * (dx^2+dy^2))` — one correct rounding, not two.

    Multiplying a rounded length by a rounded parameter rounds twice and is demonstrably worse.
    """
    # Found by search over 400k random admissible segments and parameters. The two rules agree on
    # almost every input, so a witness has to be hunted rather than guessed — which is itself the
    # reason to prefer the one-rounding rule by construction instead of by spot check.
    ax, ay = 0.0, 0.0
    bx, by = 1.150468525493579, 0.6047831353619284
    t = Fraction(93, 1222)
    once = exact.scaled_segment_length(ax, ay, bx, by, t)
    twice = float(t) * exact.segment_length(ax, ay, bx, by)
    assert once == 0.09891686315900601
    assert twice == 0.09891686315900602
    assert once != twice, "the witness must actually separate the two rules"

    radicand = t * t * (Fraction(bx) ** 2 + Fraction(by) ** 2)
    assert once == exact.rational_sqrt(radicand)
    err_once = abs(Fraction(once) ** 2 - radicand)
    err_twice = abs(Fraction(twice) ** 2 - radicand)
    assert err_once < err_twice, "one rounding is nearer the true partial length"


# --------------------------------------------------------------------- the zero-length convention

def test_zero_total_length_gives_a_zero_fraction_and_does_not_divide():
    geom = ((5.0, 5.0), (5.0, 5.0), (5.0, 5.0))
    assert exact.total_length(geom) == 0.0
    assert exact.traversal_fraction(0.0, 0.0) == 0.0
    assert exact.same_edge_fraction(geom, 0, Fraction(0), 1, Fraction(1)) == 0.0


def test_degenerate_segment_projects_to_its_start():
    t = exact.exact_projection(3.0, 4.0, 1.0, 1.0, 1.0, 1.0)
    assert t == 0
    assert exact.exact_segment_sq(3.0, 4.0, 1.0, 1.0, 1.0, 1.0) == Fraction(4 + 9)


def test_segment_length_does_not_fall_back_on_math_hypot():
    """`segment_length` must use the correctly-rounded root, not `math.hypot`.

    The same displacement as the `rational_sqrt` witness, asserted through the public function that
    the rest of the module actually calls.
    """
    dx, dy = 4194304.125000001, 0.06250000093132257
    assert exact.segment_length(0.0, 0.0, dx, dy) == 4194304.125000001
    assert math.hypot(dx, dy) == 4194304.125000002


def test_prefix_arclength_does_not_accumulate_from_the_left():
    """`toy.py` accumulates the prefix with `run += seg` while taking the total with `sum`, which in
    CPython >= 3.12 is compensated — so the two were computed by different rules. Both are `fsum`
    here, and this pins it: three preceding segments of 0.1, 0.2 and 0.3 give 0.6, not
    0.6000000000000001.
    """
    geom = ((0.0, 0.0), (0.1, 0.0), (0.1, 0.2), (0.1, 0.5), (0.1, 1.5))
    assert [exact.segment_length(*a, *b)
            for a, b in zip(geom, geom[1:])] == [0.1, 0.2, 0.3, 1.0]
    assert exact.prefix_arclength(geom, 3, Fraction(0)) == 0.6
    run = 0.0
    for seg in (0.1, 0.2, 0.3):
        run += seg
    assert run == 0.6000000000000001, "the rejected rule, pinned so the choice stays visible"


def test_prefix_arclength_is_unchanged_by_passing_the_lengths_in():
    """The `lengths` argument is a cache, so it must not be able to change an answer.

    It exists because computing the lengths per segment makes `prefix_arclength` quadratic in the
    segment count: the T0 adoption check paid about 135 ms a point for that. A performance argument
    that can alter a measured quantity is not a performance argument, so the equivalence is held
    here over random geometries rather than argued in a docstring.
    """
    rng = random.Random(20261112)
    for _ in range(300):
        n = rng.randint(2, 9)
        geom = tuple((rng.uniform(-1e6, 1e6), rng.uniform(-1e6, 1e6)) for _ in range(n))
        cache = exact.segment_lengths(geom)
        assert len(cache) == n - 1
        for seg in range(n - 1):
            for t in (Fraction(0), Fraction(1), Fraction(rng.randint(1, 999), 1000)):
                assert (exact.prefix_arclength(geom, seg, t)
                        == exact.prefix_arclength(geom, seg, t, cache))


def test_segment_lengths_are_the_exactly_rounded_ones_not_hypot():
    """The public cache is the same list the private helper builds, and it is not `math.hypot`."""
    geom = ((0.0, 0.0), (1.0, 1.0), (2.0, 3.0))
    assert exact.segment_lengths(geom) == [exact.segment_length(0.0, 0.0, 1.0, 1.0),
                                           exact.segment_length(1.0, 1.0, 2.0, 3.0)]
    # the pass-37 radicand, where hypot and a correct rounding differ
    ax, ay, bx, by = 0.0, 0.0, 1.150468525493579, 0.6047831353619284
    assert exact.segment_lengths(((ax, ay), (bx, by))) == [exact.segment_length(ax, ay, bx, by)]


def test_single_point_geometry_has_no_span():
    """A geometry with no segments at all: a span of zero, not an IndexError."""
    assert exact.same_edge_fraction(((1.0, 1.0),), 0, Fraction(0), 0, Fraction(0)) == 0.0


# --------------------------------------------------------------------- the clamp

@pytest.mark.parametrize("px,py,expected", [
    (-5.0, 0.0, Fraction(0)),      # before the start
    (15.0, 0.0, Fraction(1)),      # past the end
    (5.0, 3.0, Fraction(1, 2)),    # alongside the middle
])
def test_clamp_decisions_are_made_on_the_exact_value(px, py, expected):
    assert exact.exact_projection(px, py, 0.0, 0.0, 10.0, 0.0) == expected


def test_clamp_keeps_a_traversal_that_rounding_the_parameter_would_discard():
    """REPAIR. The clamp must compare the **exact** parameter against 1, not its binary64 image.

    On segment `(0,0)->(3,4)` with the origin at `(nextafter(3,0), 4)`, the exact parameter is
    `1 - 5.329070518200751e-17`, and `5.33e-17` is below half an ulp at 1 — so `float(t)` is exactly
    `1.0`. A clamp on the rounded value attaches at the endpoint and discards a 2.66e-16 m
    traversal; small here, and it scales with the edge weight exactly as pass-21 F1 showed.
    """
    px, py = math.nextafter(3.0, 0.0), 4.0
    t = exact.exact_projection(px, py, 0.0, 0.0, 3.0, 4.0)
    assert float(t) == 1.0, "the rounded parameter is indistinguishable from the endpoint"
    assert t < 1, "the exact parameter is not"
    assert float(1 - t) == 5.329070518200751e-17
    assert exact.scaled_segment_length(0.0, 0.0, 3.0, 4.0, 1 - t) == 2.6645352591003756e-16


def test_exact_segment_sq_matches_the_clamped_point():
    px, py = 5.0, 3.0
    got = exact.exact_segment_sq(px, py, 0.0, 0.0, 10.0, 0.0)
    assert got == Fraction(9)


# --------------------------------------------------------------------- W5, the limit that remains

def test_w5_the_argmin_can_still_differ_from_real_arithmetic():
    """THE LIMIT, pinned as a test so it cannot be quietly forgotten — pass 37 F1.

    Record A `(0,0),(1,0),(2,1)` time 2400 cost 1; record B `(0,0),(1,0)` time 1 cost
    0.4142135623730951. A's exact fraction is `1/(1+sqrt(2))`, so over the reals A is strictly
    cheaper by 4.1e-17 and the answer is 994.11 s FAIL. The adopted convention makes the costs
    **tie**, and §2.4's time discriminator reports B's 1 s PASS.

    This is not a defect in the module. It is the limit of any binary64 convention, and 4a.2's
    certified comparator exists to measure how often it bites.
    """
    geom_a = ((0.0, 0.0), (1.0, 0.0), (2.0, 1.0))
    total_a = exact.total_length(geom_a)
    prefix_a = exact.prefix_arclength(geom_a, 0, Fraction(1))
    f_a = exact.traversal_fraction(prefix_a, total_a)
    cost_b = 0.4142135623730951

    assert f_a * 1.0 == cost_b, "the convention ties where the reals do not"

    # the reals, certified without floating point: f = 1/(1+sqrt2) < cost_b  <=>  ((1-c)/c)^2 < 2
    c = Fraction(cost_b)
    assert ((1 - c) / c) ** 2 < 2, "record A is strictly cheaper over the reals"

    # and the composition is not RN(real f), which no amount of per-operand care fixes
    scale = 10 ** 60
    s2_lo = Fraction(math.isqrt(2 * scale * scale), scale)
    s2_hi = Fraction(math.isqrt(2 * scale * scale) + 1, scale)
    rn_lo, rn_hi = float(1 / (1 + s2_hi)), float(1 / (1 + s2_lo))
    assert rn_lo == rn_hi == 0.41421356237309503
    assert f_a != rn_lo
