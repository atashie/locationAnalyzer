"""Run from any directory with v2/.venv/Scripts/python.exe; stdlib only."""
from __future__ import annotations

import decimal
import itertools
import json
import math
import pathlib
import random
import sys
from fractions import Fraction as F

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "v2"))
from locfinder.measure import certify as c


def main():
    out = {}
    rng = random.Random(40)
    qs = [F(0), F(1, 2**2148), F(2**4096), F(2**4096 - 1, 3)]
    qs += [F(rng.getrandbits(256), rng.getrandbits(256) + 1) for _ in range(1000)]
    checked = 0
    for q in qs:
        for k in (0, 1, 8, 53, 128, 192, 1074):
            lo, hi = c.sqrt_interval(q, k)
            lo2, hi2 = c.sqrt_interval(q, k + 1)
            assert lo * lo <= q < hi * hi
            assert hi - lo == F(1, 2**k)
            assert lo <= lo2 <= hi2 <= hi
            s, s2 = lo * 2**k, lo2 * 2**(k + 1)
            assert 2*s <= s2 <= 2*s+1
            checked += 1
    out["brackets_width_nesting_checked"] = checked

    signed = c.Interval(F(-1), F(1)).divided_by(c.Interval(F(1), F(2)))
    negative = c.Interval(F(-2), F(-1)).divided_by(c.Interval(F(1), F(2)))
    out["signed_division"] = {"straddling_result": str(signed),
                              "contains_attainable_minus_one": signed.contains(F(-1)),
                              "negative_result": str(negative),
                              "contains_attainable_minus_two": negative.contains(F(-2))}
    try:
        c.Interval(F(-2), F(-1)).divided_by(c.Interval(F(1), F(4)))
    except ValueError as exc:
        out["signed_division"]["valid_division_raises"] = str(exc)

    # All constructor defaults are legal; labels are descriptions, not unique IDs.
    a, b = c.Journey(full_edge_costs=(1.0,)), c.Journey(full_edge_costs=(2.0,))
    out["duplicate_default_labels"] = vars(c.certify_selection([a, b], 0))
    assert c.certify_selection([a, b], 0).status == c.DIFFERS

    # A's exact cost is 1, B's 1 + 2**-150. No exotic geometry or negative cost.
    p = c.Partial(((0., 0.), (1., 0.)), 0, F(0), 0, F(1), 1.)
    a = c.Journey(partials=(p,), label="A")
    b = c.Journey(full_edge_costs=(1., 2.**-150), label="B")
    tried = []
    original = c.Journey.cost_interval
    def record(self, k):
        tried.append(k)
        return original(self, k)
    c.Journey.cost_interval = record
    try:
        default = c.certify_selection([a, b], 1)
    finally:
        c.Journey.cost_interval = original
    out["precision_limit"] = {"default_result": vars(default), "actually_tried": sorted(set(tried)),
                              "separates_at_192": a.cost_interval(192).strictly_below(b.cost_interval(192)),
                              "limit_256_result": vars(c.certify_selection([a, b], 1, max_precision=256)),
                              "limit_7_result": vars(c.certify_selection([a, b], 1, max_precision=7))}

    # Exactly equal costs that the rational recognizer calls unequal/unknown.
    connector_a = c.Journey(connector_sq=(F(1),), label="connector")
    connector_b = c.Journey(connector_sq=(F(1),), label="same connector")
    irrational = c.Partial(((0., 0.), (1., 1.)), 0, F(0), 0, F(1), 1.)
    cancelled = c.Journey(partials=(irrational,), label="sqrt2/sqrt2")
    one = c.Journey(full_edge_costs=(1.,), label="one")
    out["equal_but_not_exactly_tied"] = [vars(c.certify_selection([connector_a, connector_b], 0)),
                                          vars(c.certify_selection([cancelled, one], 0))]
    # A recognized rational tie masks another unequal unresolved alternative.
    tie = c.Journey(full_edge_costs=(1., 2.**-150), label="tie with B")
    out["first_unresolved_masks_unequal"] = {
        "tie_first": vars(c.certify_selection([b, tie, a], 0)),
        "unequal_first": vars(c.certify_selection([b, a, tie], 0))}

    tiny = c.Partial(((0., 0.), (2.**-200, 0.)), 0, F(0), 0, F(1), 1.)
    small = c.Journey(partials=(tiny,), label="tiny length, cost 1")
    two = c.Journey(full_edge_costs=(2.,), label="two")
    out["needs_precision"] = {"default": vars(c.certify_selection([small, two], 0)),
                             "at_256": vars(c.certify_selection([small, two], 0, max_precision=256))}
    # Admissible small residuals can have distinct reported binary64 costs far below 2**-192.
    residual = c.Journey(connector_sq=(F(1e-100)**2,), label="tiny residual")
    twice = c.Journey(full_edge_costs=(2e-100,), label="2e-100")
    out["absolute_width_is_not_a_binary64_gap_bound"] = {
        "rounded_costs": [residual.rounded_cost(), twice.rounded_cost()],
        "default": vars(c.certify_selection([residual, twice], 0)),
        "at_512": vars(c.certify_selection([residual, twice], 0, max_precision=512)),
        "minimum_subnormal_gap_less_than_2_to_minus_192": F(math.ulp(0.)) < F(1, 2**192)}
    zero = c.Partial(((0., 0.), (0., 0.)), 0, F(0), 0, F(1), 100.)
    assert zero.fraction_interval(0) == c.Interval(F(0), F(0))

    # Check reachable arithmetic independently, including negative scaling and permutation.
    decimal.getcontext().prec = 100
    D = decimal.Decimal
    def dec(q):
        return D(q.numerator) / D(q.denominator)
    sound = 0
    for _ in range(400):
        pts = tuple((float(rng.randrange(-20, 21)), float(rng.randrange(-20, 21))) for _ in range(4))
        so, sd = sorted(rng.sample(range(3), 2))
        to, td = F(rng.randrange(101), 100), F(rng.randrange(101), 100)
        cost = float(rng.randrange(-100, 101))
        p = c.Partial(pts, so, to, sd, td, cost)
        lengths = [(D(bx-ax)**2 + D(by-ay)**2).sqrt() for (ax,ay),(bx,by) in itertools.pairwise(pts)]
        span = (1-dec(to))*lengths[so] + sum(lengths[so+1:sd]) + dec(td)*lengths[sd]
        if sum(lengths) == 0:
            continue
        value = span/sum(lengths)*D(cost) + D(2).sqrt()/dec(c.ACCESS_SPEED_MPS)
        j = c.Journey(partials=(p,), connector_sq=(F(2),))
        i = j.cost_interval(128)
        assert dec(i.lo) <= value <= dec(i.hi)
        sound += 1
    terms = (0.1, 0.2, 0.3)
    assert len({c.Journey(full_edge_costs=t).cost_interval(64) for t in itertools.permutations(terms)}) == 1
    out["independent_decimal_cost_containment"] = sound

    # An exact rational proof of W5; Decimal is only a second numeric check.
    b = F(0.4142135623730951)
    assert (1+b)**2 > 2
    out["w5"] = {"exact_squared_gap": str((1+b)**2-2),
                  "real_cost_gap_100_digit_decimal": str(dec(b) - (D(2).sqrt()-1))}
    picked = c.Journey(full_edge_costs=(5.,), label="picked 5")
    first = c.Journey(full_edge_costs=(4.,), label="first cheaper 4")
    cheapest = c.Journey(full_edge_costs=(1.,), label="actual argmin 1")
    out["reported_certified_is_first_witness_not_argmin"] = vars(c.certify_selection([picked, first, cheapest], 0))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
