"""How often is the convention's argmin not the real argmin? Phase 4a.2's reported quantity.

Design §12 amendment **item 5** says the divergence is "unknown rather than small". This measures it,
which is the whole reason the item was opened rather than closed.

**The population, declared because a rate without one is not a measurement.** The quantity of
interest is the behaviour of §2.4's tie rule, so the population is the case where that rule fires: a
**manufactured cost tie**. Each draw builds

* journey **A** — a partial traversal of a random admissible record, so its real cost is
  `span/total * cost` and therefore irrational in general;
* journey **B** — a single full edge whose cost is *exactly* A's rounded cost, so the convention
  computes equal costs and §2.4's travel-time key decides between them;

and B is given the smaller travel time, so **the convention always selects B**. The certified
comparator then says which journey is really cheaper. That is pass 37 F1's witness W5 generalised
from one case to a population.

This is **not** a rate over T4's fixtures or T2's frames. Measuring it over T4's fixtures needs
`toy.evaluate` to expose the candidate journeys it enumerated, which it does not; over T2's frames it
needs a router, which is phase 4b. The step 4 plan asked for both in this phase and the second is a
dependency on a later one — see the scope note in the plan.

    python scripts/measure_certified_argmin.py --draws 2000
"""
from __future__ import annotations

import argparse
import json
import pathlib
import random
import sys
import time
from fractions import Fraction

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from locfinder.measure import certify as c  # noqa: E402

#: Two coordinate regimes, declared rather than blended: the metric magnitudes a projected metro
#: graph actually uses, and small coordinates where a toy fixture lives. A rate measured over one
#: does not transfer to the other, so both are reported.
REGIMES = {
    "utm-like, 1e5 to 1e6 m": (5e5, 8e5, 3.9e6, 4.0e6, 200.0),
    "toy, single digits": (0.0, 10.0, 0.0, 10.0, 5.0),
}


def draw(rng: random.Random, regime: str) -> tuple[c.Journey, c.Journey]:
    """One manufactured tie: a partial traversal, and a full edge at exactly its rounded cost."""
    x0, x1, y0, y1, span = REGIMES[regime]
    n = rng.randint(2, 4)
    ax, ay = rng.uniform(x0, x1), rng.uniform(y0, y1)
    pts = [(ax, ay)]
    for _ in range(n):
        ax += rng.uniform(-span, span)
        ay += rng.uniform(-span, span)
        pts.append((ax, ay))
    geometry = tuple(pts)
    seg_o, seg_d = sorted(rng.sample(range(n), 2)) if n > 1 else (0, 0)
    t_o = Fraction(rng.randrange(0, 1000), 1000)
    t_d = Fraction(rng.randrange(0, 1000), 1000)
    cost = rng.uniform(1.0, 1e4)

    a = c.Journey(partials=(c.Partial(geometry=geometry, seg_o=seg_o, t_o=t_o,
                                      seg_d=seg_d, t_d=t_d, cost=cost),),
                  label="A, the partial traversal")
    # Exactly A's rounded cost, so the convention ties them and the time key decides.
    b = c.Journey(full_edge_costs=(a.rounded_cost(),), label="B, the full edge")
    return a, b


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--draws", type=int, default=2000, help="draws per regime")
    ap.add_argument("--seed", type=int, default=20261112)
    ap.add_argument("--max-precision", type=int, default=c.DEFAULT_MAX_PRECISION)
    ap.add_argument("--out", type=pathlib.Path, default=None,
                    help="write the measured figures as JSON as well as printing them")
    args = ap.parse_args(argv)

    report: dict = {"draws_per_regime": args.draws, "seed": args.seed,
                    "max_precision": args.max_precision,
                    "population": ("a manufactured cost tie: a partial traversal against a full "
                                   "edge at exactly its rounded cost, with the full edge given the "
                                   "smaller time so the convention always selects it"),
                    "regimes": {}}

    for regime in REGIMES:
        rng = random.Random(args.seed)
        counts = {c.AGREES: 0, c.DIFFERS: 0, c.UNRESOLVED: 0}
        unresolved_truly_tied = 0
        unresolved_not_tied = 0
        skipped_degenerate = 0
        worst_k = 0
        started = time.perf_counter()
        for _ in range(args.draws):
            a, b = draw(rng, regime)
            if a.rounded_cost() == 0.0:
                skipped_degenerate += 1
                continue
            # The convention selects B on the time discriminator, by construction.
            got = c.certify_selection([a, b], chosen=1, max_precision=args.max_precision)
            counts[got.status] += 1
            worst_k = max(worst_k, got.precision)
            if got.status == c.UNRESOLVED:
                if got.exactly_tied:
                    unresolved_truly_tied += 1
                else:
                    unresolved_not_tied += 1
        n = sum(counts.values())
        row = {
            "decided_draws": n,
            "skipped_zero_cost": skipped_degenerate,
            "agrees": counts[c.AGREES],
            "differs": counts[c.DIFFERS],
            "unresolved": counts[c.UNRESOLVED],
            "unresolved_exactly_tied": unresolved_truly_tied,
            "unresolved_not_exactly_tied": unresolved_not_tied,
            "differs_rate": (counts[c.DIFFERS] / n) if n else None,
            "worst_precision_exponent": worst_k,
            "seconds": round(time.perf_counter() - started, 2),
        }
        report["regimes"][regime] = row
        print(f"\n{regime}: {n} decided draws in {row['seconds']}s")
        print(f"  AGREES      {row['agrees']:>7,}")
        print(f"  DIFFERS     {row['differs']:>7,}   "
              f"({100 * row['differs_rate']:.2f}% of decided draws)"
              if row["differs_rate"] is not None else "")
        print(f"  UNRESOLVED  {row['unresolved']:>7,}   "
              f"of which exactly tied {unresolved_truly_tied}, NOT tied {unresolved_not_tied}")
        print(f"  worst refinement reached 2**-{worst_k}")
        if unresolved_not_tied:
            print("  *** the phase's invalidation condition has fired: UNRESOLVED on pairs that "
                  "are not exact ties means refinement is not terminating usefully")

    # Plain ASCII in the printed line: this goes to a Windows console whose code page mangles a
    # section sign into a replacement character.
    print("\nWhat this does and does not say. The rate is over a MANUFACTURED tie, which is the "
          "case section 2.4's tie rule exists for and not the frequency of that case on a real "
          "graph. It bounds nothing about T2's frames; it says what happens when the rule fires.")
    if args.out:
        args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
