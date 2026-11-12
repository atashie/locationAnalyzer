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

## 5. The T0 re-run, 2026-11-12: what a census of the adoption actually showed

Task 5 of the step 4 plan, in the two labelled steps it demanded. The refactor moved nothing — 610
artifact leaves identical outside the build stamp and the durations. The adoption, censused over
**844,685 points and 36,555,718 per-segment positions**, changed **no** candidate set under
conventions A or D and changed `C_exact` on **2** of the 512,633 structure centroids. Six things
worth keeping.

**A prediction that held, made from the rule's text rather than from the data.** C was going to be
the sensitive convention and A and D were not, because A's rule is a 0.01 m band — seven to eight
orders of magnitude wider than anything the arithmetic changes — D's rule was *already* exact, and
C's rule is **equality of the computed residual**, the one predicate in the set that reads the last
bit. That is also why revision 13 reports C under exact arithmetic as a different rule rather than
the same rule computed better. Writing the prediction down before the census ran is what made the
result informative instead of a surprise.

**A defect can be real, demonstrable, and absent from the data.** The W2 and W3 mechanism — a float
projection parameter landing on an endpoint where the exact one does not — is what justified the
exact projection in the first place. Across 36.5 million positions on the Triangle graph it happened
**zero** times. The sentinel proves the mechanism is live; the census says it is not prevalent here.
Both are true and neither replaces the other. A bound built on "this cannot happen" would still be
wrong.

**The exact path was accidentally quadratic, and the accident nearly set the scope of the
measurement.** `prefix_arclength` recomputed every segment length once per segment, so attaching a
point cost 135 ms and a census looked like 30 hours — which would have made the deliverable a
5,000-point subsample. A cache of the record's segment lengths took it to 4.2 ms, a 32× speedup, and
the census became 50 minutes. **Measure the cost of an exact path before letting it decide how much
you are allowed to measure.** The cache is a performance argument that could have changed a measured
quantity, so its equivalence is held by a test over random geometries and by a mutation that
supplies a wrong cache.

**A comparison tool is worthless until it has been shown it can fail.** `compare_t0_artifacts.py`
strips volatile paths and compares the rest; "no difference" from it would have been unfalsifiable,
so it was run first against planted edits — two volatile that it had to ignore, two real that it had
to catch. It also earned its keep immediately: a re-run made without `--census` silently wrote an
artifact **missing both census sets**, and the tool reported it as 238 leaves *removed* rather than
as a changed figure. Nothing else would have noticed, and the rendered write-up would have quietly
lost its census tables.

**When every figure is a count of differences, zeros read as good news, so something must prove the
difference-finder is live.** `adoption_sentinel` runs the two pass-30 witnesses and stops the run if
either stops separating the two arithmetics. This is the same structure as pass 22's sentinel mutant
in the invariant harness, and for the same reason.

**I got a figure wrong by three orders of magnitude and found it by computing rather than reading.**
I wrote that the swapped candidate moved `2.5e-8` m, from eyeballing two coordinates that agree to
ten digits. It is `3.56e-5` m — 36 µm. That mattered: at 2.5e-8 m the claim "the places column
cannot see arithmetic drift, only added or removed candidates" would have been right, and at 36 µm
the column *did* see a moved candidate, 36 times its own `1e-6` m tolerance. The wrong figure
implied a wrong account of what the measurement measures. The check that caught it also confirmed
everything else: a 36 µm move along the road changes the distance to the point by δ²/2*d* =
`2.9e-11` m, which is the measured gap between the two segments' minima to one part in 50.
**Subtract the numbers; do not compare their printed digits.**

A smaller one, worth a line: `--limit` was applied *before* the census sets were appended, so
`--limit 3000 --census` recorded `limited_to: 3000` while running both half-million-point censuses
in full. A shakedown flag that did nothing to the only sets large enough to need it, and said
otherwise in the artifact.

## What this phase does not do

It does not make the comparator select what real arithmetic would select. That is pass 37 F1, it is
not closable by arithmetic, and
`test_w5_the_argmin_can_still_differ_from_real_arithmetic` pins the limit as a test. Phase 4a.2
measures how often it bites.

Design revision 13 and the T0 re-run are **done** (`caacf60`, `df38f99`, and the adoption commit).
Still open from the plan: **4a.2's certified comparator**, and then 4b.0, 4b and 4c. The adoption
census also leaves one question open that it cannot answer: whether the 2 swapped candidates change
a reported journey time, which is routing and therefore phase 4c.

Related: [[feedback-verify-the-shape-of-the-risk]],
[[feedback-decide-by-measurement-not-by-argument]], [[project-phase1-s3-design]],
[[project-phase1-s3-step3-attachment-pilot]].
