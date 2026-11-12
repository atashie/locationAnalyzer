"""Sound side claims, exact sqrt rounding, and an in-domain CPython hypot miss."""
import itertools
import math
from fractions import Fraction as F


def rn_sqrt(q):
    """Review-only integer oracle; finite roots below binary64 overflow only.

    Choose the output binade's ulp, take an integer floor root on that lattice,
    then compare the ORIGINAL rational to the exact squared halfway point.
    Rounding floor(q/unit**2) without this last comparison would lose information.
    """
    if q == 0:
        return 0.
    assert q > 0
    k = q.numerator.bit_length() - q.denominator.bit_length()
    power = F(2)**k
    if q < power:
        k -= 1
    unit = F(2)**max(k//2-52, -1074)
    scaled = q / unit**2
    floor_root = math.isqrt(scaled.numerator // scaled.denominator)
    midpoint_sq = ((F(floor_root) + F(1, 2))*unit)**2
    n = floor_root + (q > midpoint_sq or (q == midpoint_sq and floor_root % 2 == 1))
    return float(n*unit)


def main():
    # Both midpoint parity cases, and inputs arbitrarily close on either side.
    for lo in (1., math.nextafter(1., math.inf)):
        hi = math.nextafter(lo, math.inf)
        m = (F(lo)+F(hi))/2
        for delta, expected in ((-F(2)**-300, lo), (F(2)**-300, hi)):
            assert rn_sqrt(m*m+delta) == expected
        expected_tie = lo if int(F(lo)/F(math.ulp(lo))) % 2 == 0 else hi
        assert rn_sqrt(m*m) == expected_tie
    assert rn_sqrt(F(2)**-2150) == 0.  # halfway to smallest subnormal, even zero
    assert rn_sqrt(F(2)**-2148) == math.ulp(0.)
    print("PASS sqrt rational: integer lattice plus exact squared-midpoint comparison handles halfway/sticky cases")

    # x=y*y before exact power-of-two scaling. The true norm is just below
    # (x+1/2)*scale, so the lower float is correct, even though its significand is odd.
    y = 2**26+1
    x = y*y
    scale = F(2)**-30
    a, b = float(x*scale), float(y*scale)
    q = F(a)**2+F(b)**2
    actual, correct = math.hypot(a, b), rn_sqrt(q)
    midpoint = (F(a)+F(math.nextafter(a, math.inf)))/2
    assert q < midpoint**2 and q > F(a)**2
    assert correct == a and actual != correct
    assert abs(a) < 1e7 and abs(b) < 1e7 and correct > 1e-6
    print(f"PASS hypot counterexample: input=({a!r}, {b!r}); CPython={actual!r}, correctly rounded={correct!r}")

    total = F(.1)+F(.2)+F(.3)
    ratio = (F(.6000000000000001)-total)/(total-F(.6))
    assert ratio == 3 and float(total) == .6
    assert {math.fsum(p) for p in itertools.permutations((.1,.2,.3))} == {.6}
    print(f"PASS fsum/order and factor-three claim for stated operands: exact total={total}; error ratio={ratio}")
    # Broad order-independence outside the stated nonnegative finite-aggregate
    # domain is not asserted: intermediate overflow depends on order.
    try:
        math.fsum((1e308, 1e308, -1e308))
    except OverflowError:
        assert math.fsum((1e308, -1e308, 1e308)) == 1e308
        print("ACTUAL unrestricted fsum can depend on order via intermediate overflow; outside reference domain")


if __name__ == "__main__":
    main()
