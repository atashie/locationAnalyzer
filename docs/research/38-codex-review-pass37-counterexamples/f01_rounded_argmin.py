"""F1: rounded algebraic fractions do not preserve the real cost argmin."""
import math
import sys
from decimal import Decimal, localcontext
from fractions import Fraction as F
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "v2"))
from locfinder.measure.toy import ToyEdge, ToyGraph, require_query_point


def certifies_sqrt(q, h):
    """Check the rounding cell with exact rational squared midpoints."""
    a, b = math.nextafter(h, -math.inf), math.nextafter(h, math.inf)
    return ((F(a) + F(h)) / 2) ** 2 < q < ((F(h) + F(b)) / 2) ** 2


def main():
    h = math.sqrt(2)
    assert certifies_sqrt(F(2), h)
    length = math.fsum((1., h))
    plan_f = 1. / length
    # No speculative implementation: these are exactly the plan's stated operations.
    graph = ToyGraph((
        ToyEdge(0, 2, ((0., 0.), (1., 0.), (2., 1.)), 2400., 1., oneway=True),
        ToyEdge(0, 1, ((0., 0.), (1., 0.)), 1., plan_f, oneway=True),
    ))
    for p in ((0., 0.), (1., 0.)):
        require_query_point(p, "query")
    # Exact real f = 1/(1+sqrt(2)) = sqrt(2)-1.
    # f < plan_f iff (1/plan_f - 1)^2 < 2; no Decimal rounding in this proof.
    assert (1 / F(plan_f) - 1) ** 2 < 2
    lo = math.nextafter(plan_f, 0.)
    # Prove lo < f < midpoint(lo, plan_f), hence RN(f) = lo.
    assert (F(lo) + 1) ** 2 < 2
    midpoint = (F(lo) + F(plan_f)) / 2
    assert (midpoint + 1) ** 2 > 2
    assert (F(plan_f) + 1) ** 2 > 2
    # 0 < plan_f - f < one ulp, proved by lo < f < plan_f.
    with localcontext() as ctx:
        ctx.prec = 100
        real_f = Decimal(2).sqrt() - 1
        real_time = 2400 * real_f
        assert real_time > 600
        print(f"ACTUAL real fraction={real_f}; real A time={real_time}")
        print(f"ACTUAL fraction error={Decimal.from_float(plan_f) - real_f}")
    assert graph.edges[0].total_cost == 1.
    assert plan_f * 1. == graph.edges[1].total_cost
    assert 2400 * plan_f > 600 > graph.edges[1].time_s
    print(f"CLAIM composition exactly rounds f; ACTUAL plan={plan_f!r}, RN(real f)={lo!r}")
    print("ACTUAL real cost selects A (~994.11 s FAIL); plan ties and selects B (1 s PASS)")

    # Even an oracle returning RN(real f) once cannot preserve every real ordering.
    # B costs lo < real f; A fast, B slow => rounding creates a false cost tie.
    ideal_graph = ToyGraph((
        ToyEdge(0, 2, ((0., 0.), (1., 0.), (2., 1.)), 1., 1., oneway=True),
        ToyEdge(0, 1, ((0., 0.), (1., 0.)), 1000., lo, oneway=True),
    ))
    assert (F(ideal_graph.edges[1].total_cost) + 1) ** 2 < 2
    assert lo * ideal_graph.edges[0].time_s < 600 < ideal_graph.edges[1].time_s
    print("ACTUAL even RN(real f): real selects B (1000 s FAIL); rounded tie selects A (<1 s PASS)")

    # An exactly-rounded sum of rounded lengths need not round the true length sum.
    r10 = math.sqrt(10)
    assert certifies_sqrt(F(10), r10)
    total = math.fsum((1., r10))
    lower = math.nextafter(total, 0.)
    m = (F(lower) + F(total)) / 2
    assert (m - 1) ** 2 > 10
    m0 = (F(math.nextafter(lower, 0.)) + F(lower)) / 2
    assert (m0 - 1) ** 2 < 10
    print(f"ACTUAL prefix 1+sqrt(10): fsum rounded lengths={total!r}, RN(true sum)={lower!r}")
    print("PASS F1: domain accepted; all strict algebraic comparisons certified with Fraction")


if __name__ == "__main__":
    main()
