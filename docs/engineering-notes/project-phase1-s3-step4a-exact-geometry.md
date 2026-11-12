---
name: project-phase1-s3-step4a-exact-geometry
description: "Phase 4a.1 built the exact/correctly-rounded geometry primitives - and found that an exact projection is not sufficient, because rounding the prefix can throw the gap away again"
metadata:
  type: project
---

# 4a.1: exact projection is necessary and not sufficient

**2026-11-11.** Step 4 phase 4a.1 of `docs/plans/2026-11-11-step4-comparator-plan.md`:
`v2/locfinder/measure/exact.py`, 38 fixtures in `v2/tests/test_exact_geometry.py`, and
`v2/scripts/mutate_exact_geometry.py` with **21 mutations, all caught**. Suite 1,254 passed,
24 skipped.

The module settles all six of §12 item 1's unfrozen quantities. What is worth keeping is not the
code but four things the work turned up, three of them about my own claims.

## 1. The same-edge span rule is necessary, not tidier — and I found out by accident

Codex pass 37 F5 showed two "exactly rounded" readings of the same-edge interval splitting
**666.13 s FAIL against 558.79 s PASS**, and said exact projection could not pick between them. I
adopted a third rule instead: **measure the span directly from the interval**, never as a difference
of two prefixes. The plan called that "removing the choice rather than settling it", which I meant as
an argument from cleanliness.

Then the fixture for it failed, because I had predicted the rejected reading would give
`1.1102230246251565e-16` and it gave **0.0**.

The reason is better than the rule I was defending. On W3's geometry the exact gap to the endpoint
is `1.862645149230957e-9` m, the prefix is `2e7`, and `ulp(2e7)` is `3.725290298461914e-9`. **The
gap is exactly half an ulp**, and `2e7` has an even significand — so rounding the exact prefix to
binary64 rounds it *onto the endpoint* under round-half-to-even, and the traversal disappears.

That is W3's own defect, resurfacing one layer up, **after** the projection has been made exact. So:

> **An exact projection is necessary and not sufficient. The arithmetic that consumes the exact
> parameter can throw away exactly what the exactness bought.**

The span rule never forms the large cancelling prefix, so it is immune. It is required, not
preferred, and `test_w4_same_edge_span_is_measured_as_a_span_not_a_difference_of_prefixes` now
asserts the half-ulp coincidence and the even significand so the reason travels with the rule.

A related improvement fell out of the same thinking: `t * L` is computed as
`sqrt(t**2 * (dx**2 + dy**2))`, a **single** correct rounding, rather than a rounded `t` times a
rounded `L`. Two roundings are never better and the one-rounding form costs nothing.

## 2. Dead defensive code is a permanent mutation survivor

`rational_sqrt` first carried a step-up loop after its integer root: *"`isqrt` of a floored rational
can land one lattice point low; step up while it is too small."* The harness could not make it fire,
and 300,000 random rationals plus a constructed attempt produced no witness.

There is none. `floor(sqrt(floor(x))) == floor(sqrt(x))` for every real `x >= 0`: if
`m = floor(sqrt(x))` then `m**2 <= x` and `m**2` is an integer, so `m**2 <= floor(x)`, while
`sqrt(floor(x)) <= sqrt(x)`. The loop was unreachable.

**A guard that cannot fire is a mutation that cannot be caught, for ever.** It is not harmless: it
reports as an uncaught mutation on every future run and trains whoever reads the output to discount
the list. The loop is gone and the identity is written where it was.

Two mutations were retired from the harness for the same reason, and the harness is what proved them
equivalent rather than uncaught: replacing the degenerate-segment branch with `denom = 1` (the
numerator is zero too, so `t` is zero either way — the branch only prevents `ZeroDivisionError`),
and setting a zero-length record's total to `1.0` (every segment is zero, so the span is zero and
`0/1.0` is still `0.0`). **An uncaught mutation is a question, not a verdict**: it asks whether the
test is missing or the mutation is equivalent, and answering it is the work.

## 3. I made the over-broad claim again, one hour after writing up the ninth instance

The harness found that mutating the integer root to work on a *rounded* scaling changes `k` on 12.8%
of random radicands and changes the answer on **none** of 20,000. I had a bound for why, factored
the decision into `_decide`, and wrote in its docstring: *"This step is self-correcting for an
off-by-one `k`."*

It is not. The test asserting it failed within 300 radicands. `_decide` is a **two-candidate**
choice: hand it `k+1` and it returns a value from the wrong pair, which is wrong whenever the
correct answer was `k*u`.

The measured fact was narrow — *the `k` values a binary64 rounding can actually produce do not
change the answer* — and I restated it as a property of the comparison alone. That is
`feedback-verify-the-shape-of-the-risk` exactly, in my own work, within an hour of my writing the
ninth instance of it into that very file. The docstring now states the narrow property, names the
false broad one, and
`test_decide_does_not_tolerate_an_arbitrary_off_by_one_index` holds the witness so the distinction
cannot collapse again.

**The useful habit, cheaper than the lesson: when a measurement comes back clean, write down what
was varied. Here, what varied was `k` *within the set a rounding can reach*, and the claim dropped
that clause.**

## 4. A correct oracle can be unusable, and the test suite says so by timing out

`rational_sqrt` is cross-checked against an independently written oracle, which is the only reason
to believe it. The first oracle walked `nextafter` from `math.sqrt(float(q))` to the bracketing
pair — correct, and fine for normal radicands.

For a **subnormal** radicand `float(q)` underflows to `0.0`, the walk starts from the fallback `1.0`,
and it has about `2**62` steps to take. The suite hit pytest's timeout instead of failing, which
looks nothing like a wrong answer. The oracle now locates the root with `decimal` at 120 digits and
decides between the two neighbours on **exact rationals** — fast, and still exact where it counts.

**An oracle has to be independent *and* affordable, and the failure mode of an unaffordable one is a
hang rather than a red test.**

## What this phase does not do

It does not make the comparator select what real arithmetic would select. That is pass 37 F1, it is
not closable by arithmetic, and
`test_w5_the_argmin_can_still_differ_from_real_arithmetic` pins the limit as a test. Phase 4a.2
measures how often it bites. Still open from the plan: design revision 13, the T0 re-run as a
labelled refactor-then-adopt, and 4a.2 itself.

Related: [[feedback-verify-the-shape-of-the-risk]],
[[feedback-decide-by-measurement-not-by-argument]], [[project-phase1-s3-design]],
[[project-phase1-s3-step3-attachment-pilot]].
