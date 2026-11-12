"""F5: mathematically equal same-edge formulae give different legal decisions."""
import math
from fractions import Fraction as F


def main():
    # One straight 20,000,000 m edge; positions separated by one coordinate ulp.
    length = 2e7
    origin = math.nextafter(1e7, 0.)
    destination = 1e7
    s_o, s_d = F(origin) + F(1e7), F(destination) + F(1e7)
    f_o, f_d = float(s_o/F(length)), float(s_d/F(length))
    separate = abs(f_d-f_o)
    interval = float(abs(s_d-s_o)/F(length))
    assert separate != interval
    print(f"ACTUAL abs(RN(s_d/L)-RN(s_o/L))={separate!r}")
    print(f"ACTUAL RN(abs(s_d-s_o)/L)={interval!r}")
    print(f"ACTUAL time at edge weight 1e19: {separate*1e19!r} vs {interval*1e19!r} s")
    assert interval*1e19 < 1000 < separate*1e19
    assert interval*6e18 < 600 < separate*6e18
    print(f"ACTUAL published 600 s threshold at weight 6e18: {separate*6e18!r} FAIL vs {interval*6e18!r} PASS")
    print("CLAIM same-edge/zero-total rule 'specified'; ACTUAL table gives neither formula nor zero case")
    print("PASS F5: operation order is consequential even on a rational straight edge")


if __name__ == "__main__":
    main()
