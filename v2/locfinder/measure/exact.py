"""Exact and correctly-rounded geometry arithmetic — design §12 item 1, step 4 phase 4a.1.

**What this module settles, and what it cannot.**

§2.4 froze `f * (cost_base + penalty)` as one term and left the **fraction** unfrozen. Six
quantities decide the exact cost argmin before any `fsum` sees a term: segment-length summation,
prefix arclength, the projection parameter, the traversal fraction, the same-edge interval formula
and the zero-total-length convention. This module fixes all six, on this rule:

    exact where the quantity is rational, correctly rounded **once** where it is algebraic, every
    comparison that *decides* something made on the exact value, and the composition order written.

The projection parameter and squared distance have no square root in them, so over binary64 inputs
they are exactly rational and are computed as `Fraction`s. Lengths are irrational, so the best
available is a single correct rounding of an exact rational root.

**It does not mean the selected journey is the one real arithmetic would select.** Codex pass 37
built the witness: two records whose exact costs differ by 4.1e-17, where this convention makes them
tie and §2.4's time discriminator then reports 1 s PASS against a real answer of 994.11 s FAIL.
The traversal fraction is irrational, so two candidates whose exact costs differ by less than one
ulp of it can always be ordered wrongly or tied, and **no binary64 convention avoids that**.
`measure/certify.py` (phase 4a.2) measures how often it happens instead of leaving it unknown.
`tests/test_exact_geometry.py::test_w5_the_argmin_can_still_differ_from_real_arithmetic` pins the
limit so it cannot be quietly forgotten.

**Two rules here differ from `toy.py`'s current arithmetic, deliberately.**

* `toy.py` accumulates the prefix with `run += seg` — naive left accumulation — while taking the
  total with `sum(...)`, which in CPython >= 3.12 is *compensated*. The two were inconsistent. Both
  are `fsum` here.
* The same-edge interval is computed **as a span**, never as a difference of two prefixes. Pass 37
  F5 showed two readings of the difference that split 666.13 s FAIL against 558.79 s PASS at an
  admissible weight. Measuring the span directly removes the choice: the large cancelling prefixes
  never appear, so there is nothing to cancel badly.
"""
from __future__ import annotations

import itertools
import math
from fractions import Fraction

Point = tuple[float, float]
Geometry = tuple[Point, ...] | list[Point]

__all__ = [
    "rational_sqrt",
    "exact_projection",
    "exact_segment_sq",
    "exact_position",
    "segment_length",
    "scaled_segment_length",
    "total_length",
    "prefix_arclength",
    "traversal_fraction",
    "same_edge_fraction",
]

#: Binary64: 53 significand bits, and the smallest normal exponent.
_MANT_BITS = 53
_MIN_SUBNORMAL_EXP = -1074


def rational_sqrt(q: Fraction | int) -> float:
    """The correctly rounded binary64 square root of a non-negative exact rational.

    IEEE-754 requires `sqrt` to be correctly rounded, but only of a *binary64 argument* — and the
    radicands here are exact rationals that are not binary64. `math.sqrt(float(q))` therefore rounds
    twice. `math.hypot` is not an escape either: CPython implements its own compensated
    `vector_norm` and documents "usually correctly rounded", not always. Pass 37 produced the
    witness, which `tests/test_exact_geometry.py` pins: the displacement
    `(4194304.125000001, 0.06250000093132257)` gives `hypot` 4194304.125000002 where the correctly
    rounded answer is 4194304.125000001.

    The algorithm, which pass 37 supplied after the plan had only gestured at "integer square roots
    on a scaled numerator and denominator":

    1. bracket the result's binade to get the lattice unit `u` of the representable values there;
    2. take `k = isqrt(floor(q / u**2))`, so `k*u` is the largest lattice point whose square is
       at most `q`;
    3. decide between `k*u` and `(k+1)*u` by comparing the **original rational** `q` against
       `((k + 1/2) * u)**2`, resolving an exact equality to the even significand.

    Step 3 is the part that matters. Integer scaling alone is **not** a rounding proof: the
    numerator and denominator information discarded in step 2's floor has to survive into the
    midpoint comparison, or a radicand arbitrarily close to a midpoint is decided by the discarded
    part. Because the comparison is on exact rationals it is a proof, not an estimate.
    """
    q = Fraction(q)
    if q < 0:
        raise ValueError(f"rational_sqrt of a negative rational: {q}")
    if q == 0:
        return 0.0

    # A starting approximation, then the binade is found exactly.  float(q) can overflow to inf for
    # a huge rational and underflow to 0 for a tiny one, so the exponent is taken from the integer
    # bit lengths instead, which is exact for every Fraction.
    exp = (q.numerator.bit_length() - q.denominator.bit_length()) // 2
    # Correct the guess until 2**exp <= sqrt(q) < 2**(exp+1), i.e. 4**exp <= q < 4**(exp+1).
    while _pow2(2 * exp) > q:
        exp -= 1
    while _pow2(2 * (exp + 1)) <= q:
        exp += 1

    # The lattice unit of the binade [2**exp, 2**(exp+1)).  Subnormals share one unit.
    unit_exp = max(exp - (_MANT_BITS - 1), _MIN_SUBNORMAL_EXP)
    u = _pow2(unit_exp)

    scaled = q / (u * u)                       # exact
    k = math.isqrt(scaled.numerator // scaled.denominator)
    # `k` is already the largest integer with `(k*u)**2 <= q`, and no correction loop is needed:
    # `floor(sqrt(floor(x))) == floor(sqrt(x))` for every real `x >= 0`, because `m = floor(sqrt(x))`
    # gives an integer `m**2 <= x` hence `m**2 <= floor(x)`, while `sqrt(floor(x)) <= sqrt(x)`. The
    # first draft of this function carried a step-up loop here; the mutation harness could not make
    # it fire, and the identity above is why. Dead defensive code is a mutation survivor forever, so
    # it is gone and the reason is written down instead.
    return float(_decide(q, k, u))


def _decide(q: Fraction, k: int, u: Fraction) -> Fraction:
    """Choose between the lattice points `k*u` and `(k+1)*u` by an exact midpoint comparison.

    Separated out because it carries the algorithm's one non-obvious property, which the mutation
    harness established and which is narrower than it first looks.

    **Taking the integer root of a binary64 *rounding* of the scaling does not change the answer.**
    Measured: it changes `k` on about 13% of random radicands and the result on none of 20,000. The
    reason is a bound rather than luck. With `K` the true index, a wrong `k = K-1` still selects
    `K*u` here and `k = K+1` still selects `(K+1)*u`; either is wrong only if the correct answer lay
    one lattice point further on, which needs `|scaled - K**2| > K + 3/4`, and since `K >= 2**52`
    while half an ulp of `scaled` is at most `2**52`, no rounding of `scaled` can produce that.

    **It is not a tolerance for an arbitrary off-by-one `k`.** This is a two-candidate choice, so a
    `k` from outside the reachable set returns a value from the wrong pair —
    `test_decide_does_not_tolerate_an_arbitrary_off_by_one_index` holds the witness. A first draft of
    this docstring claimed the broader property; it is false, and the test that asserted it failed
    within 300 radicands.

    What must never be weakened is the comparison itself: it is against the **original rational**,
    never against the scaling that the integer step floored.
    """
    lo = k * u
    midpoint = (Fraction(2 * k + 1) * u) / 2
    cmp = q - midpoint * midpoint
    if cmp > 0:
        return lo + u
    if cmp < 0:
        return lo
    # Exactly a midpoint: round half to even on the significand, which is `k` itself.
    return lo if k % 2 == 0 else lo + u


def _pow2(e: int) -> Fraction:
    """`2**e` as an exact Fraction, for any sign of `e`."""
    return Fraction(1 << e, 1) if e >= 0 else Fraction(1, 1 << -e)


def exact_projection(px: float, py: float, ax: float, ay: float,
                     bx: float, by: float) -> Fraction:
    """The clamped projection parameter of `p` onto segment `a->b`, exactly, as a `Fraction`.

    `t = ((p-a).(b-a)) / ||b-a||**2` contains no square root, and every binary64 is a rational, so
    this is exact over binary64 inputs. **The clamp decision is made on the exact value**, which is
    what the two pass-30 witnesses need: in binary64 W2's numerator cancels to exactly 0.0 where the
    exact value is 1.42e-20, and W3's `px - ax` rounds away a 1.86e-9 m gap so the parameter lands
    on the endpoint. Neither is reachable by a summation rule or by a tighter domain.

    A degenerate segment returns 0, matching `toy.py`'s zero-length branch rather than dividing.
    """
    ax_f, ay_f = Fraction(ax), Fraction(ay)
    dx, dy = Fraction(bx) - ax_f, Fraction(by) - ay_f
    denom = dx * dx + dy * dy
    if denom == 0:
        return Fraction(0)
    t = ((Fraction(px) - ax_f) * dx + (Fraction(py) - ay_f) * dy) / denom
    if t <= 0:
        return Fraction(0)
    if t >= 1:
        return Fraction(1)
    return t


def exact_position(ax: float, ay: float, bx: float, by: float,
                   t: Fraction) -> tuple[Fraction, Fraction]:
    """The point at parameter `t` on `a->b`, exactly."""
    ax_f, ay_f = Fraction(ax), Fraction(ay)
    return (ax_f + t * (Fraction(bx) - ax_f), ay_f + t * (Fraction(by) - ay_f))


def exact_segment_sq(px: float, py: float, ax: float, ay: float,
                     bx: float, by: float) -> Fraction:
    """The exact squared distance from `p` to the nearest point of segment `a->b`.

    Squared, because ordering distances never needs the root: `d1 < d2` iff `d1**2 < d2**2` for
    non-negative reals. §2.2's residual ordering and both caps are therefore decided exactly, by
    comparing against the squared cap.
    """
    t = exact_projection(px, py, ax, ay, bx, by)
    qx, qy = exact_position(ax, ay, bx, by, t)
    ex, ey = Fraction(px) - qx, Fraction(py) - qy
    return ex * ex + ey * ey


def segment_length(ax: float, ay: float, bx: float, by: float) -> float:
    """The exactly-rounded length of `a->b`: one correct rounding of an exact rational root."""
    dx, dy = Fraction(bx) - Fraction(ax), Fraction(by) - Fraction(ay)
    return rational_sqrt(dx * dx + dy * dy)


def scaled_segment_length(ax: float, ay: float, bx: float, by: float,
                          t: Fraction) -> float:
    """The exactly-rounded length of the first `t` of `a->b` — **one** rounding, not two.

    `t * ||b-a|| = sqrt(t**2 * (dx**2 + dy**2))`, and `t**2 * (dx**2 + dy**2)` is an exact rational,
    so the partial length is a single correctly-rounded root. Multiplying a rounded length by a
    rounded parameter rounds twice and is never better.
    """
    if t < 0:
        raise ValueError(f"a negative traversal fraction of a segment: {t}")
    dx, dy = Fraction(bx) - Fraction(ax), Fraction(by) - Fraction(ay)
    return rational_sqrt(t * t * (dx * dx + dy * dy))


def _segment_lengths(geometry: Geometry) -> list[float]:
    return [segment_length(a[0], a[1], b[0], b[1])
            for a, b in itertools.pairwise(geometry)]


def total_length(geometry: Geometry) -> float:
    """`fsum` of the exactly-rounded segment lengths.

    Order-independent, which is the property §2.4 already requires of journey totals and which this
    extends downward into the geometry. **It is not `RN` of the real total**, and cannot be: on
    `(0,0),(1,0),(2,3)` this gives 4.16227766016838 where `RN(1 + sqrt(10))` is 4.162277660168379.
    Correctly rounding each operand does not correctly round their sum, and saying otherwise was the
    error Codex pass 37 F1 found in revision 1 of the step 4 plan.

    Left accumulation stays rejected: over the exact rational values of `0.1, 0.2, 0.3`, `0.6` is
    the exactly-rounded total and is nearer the truth than `0.6000000000000001` by a factor of
    three.
    """
    return math.fsum(_segment_lengths(geometry))


def prefix_arclength(geometry: Geometry, seg_index: int, t: Fraction) -> float:
    """Arclength from the record's first vertex to parameter `t` on segment `seg_index`.

    `fsum` of the whole preceding segment lengths, then the partial, in that order and as one
    `fsum` so the result does not depend on the order of accumulation. The partial term is
    `scaled_segment_length`, which rounds once.
    """
    lengths = _segment_lengths(geometry)
    if not 0 <= seg_index < len(lengths):
        raise IndexError(f"segment {seg_index} is not in a geometry of {len(lengths)} segments")
    a, b = geometry[seg_index], geometry[seg_index + 1]
    partial = scaled_segment_length(a[0], a[1], b[0], b[1], t)
    return math.fsum(lengths[:seg_index] + [partial])


def traversal_fraction(prefix: float, total: float) -> float:
    """`RN(prefix / total)`, with the zero-length record normative at 0.0.

    One rounded division of two exactly-rounded quantities. §2.4's frozen term then multiplies this
    by the already-formed `cost_base + penalty`, never by the components apportioned separately.
    """
    if total == 0.0:
        return 0.0
    return prefix / total


def same_edge_fraction(geometry: Geometry, seg_o: int, t_o: Fraction,
                       seg_d: int, t_d: Fraction) -> float:
    """The fraction of a record traversed between two occurrences on it.

    **Measured as a span, not as a difference of two prefixes.** Pass 37 F5 compared two readings of
    the difference — `|RN(s_d/L) - RN(s_o/L)|` and `RN(|s_d - s_o|/L)` — and found they split
    666.13 s FAIL against 558.79 s PASS at an admissible weight, with exact projection unable to
    pick between them. The span removes the choice rather than settling it: when both occurrences
    sit near one end of a long record, the difference of prefixes cancels two large nearly-equal
    quantities and the span never forms them.

    The span is `(1 - t_o) * L_i + L_{i+1} + ... + L_{j-1} + t_d * L_j` for `i < j`, and
    `|t_d - t_o| * L_i` when both are on one segment. Each term is one correct rounding and they are
    combined with `fsum`, so the result is independent of the order of the two occurrences.
    """
    lengths = _segment_lengths(geometry)
    if not lengths:
        return 0.0
    for idx in (seg_o, seg_d):
        if not 0 <= idx < len(lengths):
            raise IndexError(f"segment {idx} is not in a geometry of {len(lengths)} segments")
    total = math.fsum(lengths)
    if total == 0.0:
        return 0.0

    # Orient the span so it runs forward.  The magnitude is symmetric in the two occurrences.
    if (seg_o, t_o) > (seg_d, t_d):
        seg_o, t_o, seg_d, t_d = seg_d, t_d, seg_o, t_o

    def _partial(idx: int, frac: Fraction) -> float:
        a, b = geometry[idx], geometry[idx + 1]
        return scaled_segment_length(a[0], a[1], b[0], b[1], frac)

    if seg_o == seg_d:
        span = _partial(seg_o, abs(t_d - t_o))
        return span / total
    terms = [_partial(seg_o, 1 - t_o)]
    terms.extend(lengths[seg_o + 1:seg_d])
    terms.append(_partial(seg_d, t_d))
    return math.fsum(terms) / total
