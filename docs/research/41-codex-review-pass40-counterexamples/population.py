"""Audit the published population, seed dependence, and refinement censoring."""
import collections
import decimal
import json
import math
import pathlib
import random
import sys
from fractions import Fraction as F

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "v2"), str(ROOT / "v2/scripts")]
import measure_certified_argmin as m
from locfinder.measure import certify as c, toy


def sweep(seed, n, regime, precision):
    rng = random.Random(seed)
    counts = collections.Counter()
    for _ in range(n):
        a, b = m.draw(rng, regime)
        assert a.rounded_cost() == b.rounded_cost()
        p = a.partials[0]
        assert p.seg_o != p.seg_d
        toy.ToyEdge(0, 1, p.geometry, 1., p.cost)
        assert any(q > 0 for q in c._radicands(p.geometry))
        counts[c.certify_selection([a, b], 1, max_precision=precision).status] += 1
    return dict(counts)


def main():
    out = {"seed_sweeps_1000_draws": {}, "precision_sweeps_1000_draws": {}}
    for regime in m.REGIMES:
        out["seed_sweeps_1000_draws"][regime] = {
            str(seed): sweep(seed, 1000, regime, 192) for seed in (0, 1, 2, 20261112)}
        out["precision_sweeps_1000_draws"][regime] = {
            str(k): sweep(20261112, 1000, regime, k) for k in (32, 48, 63, 64)}

    # Independent real-cost direction, versus manufactured B, over the published 10000 draws.
    decimal.getcontext().prec = 100
    D = decimal.Decimal
    def dec(q):
        q = F(q)
        return D(q.numerator)/D(q.denominator)
    out["independent_direction_5000_draws"] = {}
    for regime in m.REGIMES:
        rng = random.Random(20261112)
        counts = collections.Counter()
        minimum_segment = math.inf
        for _ in range(5000):
            a, b = m.draw(rng, regime)
            p = a.partials[0]
            toy.ToyEdge(0, 1, p.geometry, 1., p.cost)
            assert p.seg_o != p.seg_d
            assert a.rounded_cost() == b.rounded_cost() > 0
            minimum_segment = min(minimum_segment, *(math.hypot(bx-ax, by-ay)
                for (ax,ay),(bx,by) in zip(p.geometry, p.geometry[1:])))
            roots = [dec(q).sqrt() for q in c._radicands(p.geometry)]
            span = (1-dec(p.t_o))*roots[p.seg_o] + sum(roots[p.seg_o+1:p.seg_d]) + dec(p.t_d)*roots[p.seg_d]
            real = span/sum(roots)*dec(p.cost)
            rounded = b.full_edge_costs[0]
            counts["A_below_rounded_B" if real < dec(rounded) else "A_above_rounded_B"] += 1
            # B's construction puts it on either side of A's rounding error.
            # Moving it a few ulps in either direction destroys the near-half split.
            low, high = rounded, rounded
            for i in range(16):
                low, high = math.nextafter(low, -math.inf), math.nextafter(high, math.inf)
            assert dec(low) < real < dec(high)
        out["independent_direction_5000_draws"][regime] = {
            **dict(counts), "minimum_segment_length": minimum_segment,
            "all_5000_admissible_positive_cost_distinct_segments": True}

    # draw() makes no time assignment at all; Journey has no time field.
    a, b = m.draw(random.Random(20261112), next(iter(m.REGIMES)))
    tied_cost = a.rounded_cost()
    hypothetical_a = toy.Journey(time_s=1., cost=tied_cost, destination=0)
    hypothetical_b = toy.Journey(time_s=2., cost=tied_cost, destination=0)
    out["time_key_is_assumed"] = {"Journey_fields": list(c.Journey.__dataclass_fields__),
        "A_time_1_B_time_2_selects": "A" if hypothetical_a.rank_key < hypothetical_b.rank_key else "B",
        "comment": "The reverse time assignment selects B. Neither is recorded by draw()."}

    class TinySteps(random.Random):
        """All chosen uniform values lie inside their declared ranges."""
        def uniform(self, a, b):
            return 1e-8 if a < 0 < b else (a+b)/2
    a, b = m.draw(TinySteps(0), "toy, single digits")
    try:
        toy.ToyEdge(0, 1, a.partials[0].geometry, 1., a.partials[0].cost)
    except ValueError as exc:
        out["admissibility_not_enforced"] = str(exc)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
