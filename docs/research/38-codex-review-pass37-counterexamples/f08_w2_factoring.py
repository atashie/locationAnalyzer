"""F8: distinguish already-rounded products from algebraic formulations."""
import math
from fractions import Fraction as F


def main():
    x, y, d = 122.09, -122.08999999999999, 1e-6
    exact = (F(x)+F(y))*F(d)
    naive = math.fsum((x*d, y*d))
    factored = math.fsum((x, y))*d
    # x+y is exactly representable by Sterbenz cancellation; multiplying by a
    # power-of-two sum is exact here. No general projection guarantee follows.
    assert naive == 0. and F(factored) == exact
    t = factored / (d*d+d*d)
    print(f"ACTUAL fsum(already rounded products)={naive!r}; factored fsum(x,y)*d={factored!r}")
    print(f"ACTUAL exact dot={float(exact)!r}; factored parameter={t!r}; network={t*1e11!r} s")
    print("PASS F8: a summation replacement alone fails; this witness does not uniquely require rational arithmetic")


if __name__ == "__main__":
    main()
