You are an adversarial reviewer. Your job is to find what is wrong, not to confirm what is right.

Repository: C:\Users\arikt\documents\github\distanceFinder, branch v2-rethink, HEAD `8d86cc6`.
Python is at v2/.venv/Scripts/python.exe; the suite runs from v2/ with
`.venv/Scripts/python.exe -m pytest -q` and passes 1,300 / 24 skipped here. Run code to check
claims; do not reason about floating point from memory. **Do not create temporary directories
inside the repository** — pass pytest an explicit `--basetemp` outside it, or skip the full suite and
say so.

This project's prior passes found 3–8 real defects each, and passes 38 and 39 each found that a
*repair* carried the same error as the thing it repaired. A pass that finds nothing is more likely to
have missed something.

## What to review: phase 4a.2, the certified cost comparator

New in commits `0829e36` and `8d86cc6`:

* `v2/locfinder/measure/certify.py` — exact rational interval arithmetic over correctly-bracketed
  square roots, and `certify_selection` returning `AGREES` / `DIFFERS` / `UNRESOLVED`.
* `v2/tests/test_certify.py` — 40 fixtures.
* `v2/scripts/mutate_certify.py` — 21 mutations, reported all caught, with `--self-test`.
* `v2/scripts/measure_certified_argmin.py` and `docs/experiments/certified-argmin-divergence.json`.
* the 4a.2 sections of `docs/plans/2026-11-11-step4-comparator-plan.md` and
  `docs/engineering-notes/project-phase1-s3-step4a-exact-geometry.md` (§8).

## The claims I most want attacked

**A. The bracket.** `sqrt_interval(q, k)` claims `s/2**k <= sqrt(q) < (s+1)/2**k` with
`s = isqrt(floor(q * 4**k))`, width exactly `2**-k`, and nesting in `k`.
* Is the bound correct for **every** non-negative rational, including `q = 0`, subnormal-scale `q`,
  enormous `q`, and `k = 0`? Find a counterexample or certify it.
* Is the nesting claim (`s_{k+1} >= 2 s_k` and `s_{k+1} <= 2 s_k + 1`) actually true, and does the
  code depend on it anywhere it is not tested?

**B. Soundness of the certification.** `certify_cheaper` returns a label when one interval is
strictly below the other.
* Can it ever certify the **wrong** journey? Construct a case where the real costs are ordered one
  way and the comparator claims the other. Attack the interval propagation: `scaled` with a negative
  rational, `divided_by` when the numerator interval straddles zero, the connector term, and the
  accumulation order.
* `Partial.fraction_interval` raises `_NeedsPrecision` when `total.lo <= 0`. Can that loop forever,
  or mask a genuine zero-length record, or be reached with `max_precision` already exhausted?
* `_rational_cost` and `_exactly_tied` decide whether an `UNRESOLVED` pair is really equal. Can they
  report `True` for an unequal pair, or `False` for an equal one? Note that `_exactly_tied` returns
  `False` when it cannot tell, and the artifact reports that as "not exactly tied" — is that
  conflation visible in the published figures, and does it weaken the invalidation-condition claim?

**C. The headline rate.** The artifact claims 51.42% and 48.32% `DIFFERS` over 5,000 draws each,
and **zero** `UNRESOLVED`.
* Is the generating population what the write-up says it is? Read `draw()`. Does it ever produce a
  degenerate or inadmissible geometry, a zero-length record, a `seg_o == seg_d` pair, or a cost that
  makes the tie not a tie? Is the claim "the convention always selects B" actually true of every
  draw, given B's time is never set — is `chosen=1` justified, or is it asserted?
* Is ~50% the *right* answer for this population, or an artefact of how B is built? Argue it from
  the construction, then check it.
* Does the rate depend on the seed, the draw count, or `max_precision` in a way the artifact does
  not disclose?

**D. The scope decision.** I declined to sweep T4's fixtures, on the measurement that **0 of 17**
contain a near tie under 1e6 ulps.
* Is that measurement right? `t4_margins()` takes the gap to the next **distinct** cost. Does that
  skip something that matters — for instance a near tie that is not at the argmin, or a pair of
  *irrational* costs that are equal in binary64 but not in reality? The latter would be a `DIFFERS`
  candidate the margin test cannot see. Check whether any T4 fixture has one.
* I also claim the discriminator "fires in 11 of 17 and changes the reported time in 1". Verify both
  counts, and say whether "changes the reported time" is the right test of consequence.

**E. The mutation harness.** 21 mutations, all caught; two retired as equivalent; one anchor was
found matching twice.
* Are any of the 21 equivalent, so "caught" is luck?
* What rule in `certify.py` has **no** mutation attacking it? Earlier passes found such a rule every
  time.
* Does `--self-test` establish what it claims?

**F. The fixtures.** 40 of them.
* Any whose expected value was read off a run rather than derived from the rule?
* `test_w5_real_costs_are_ordered_the_way_the_design_says` uses `decimal` at 60 digits as an
  independent check. Is it independent, and is 60 digits enough?

## How to report

Severity (High / Medium / Low), the claim refuted quoted from the artifact, a **runnable**
reproducer, and the numbers it produces. Put reproducers under
docs/research/41-codex-review-pass40-counterexamples/ with a REPORT.md.

If a claim survives, say so explicitly and say what you ran. A confirmed claim is as useful to me as
a defect — and in this project, more surprising.
