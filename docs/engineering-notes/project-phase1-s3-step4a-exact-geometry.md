---
name: project-phase1-s3-step4a-exact-geometry
description: "Phase 4a.1 built the exact/correctly-rounded geometry primitives - and found that an exact projection is not sufficient, because rounding the prefix can throw the gap away again"
metadata:
  type: project
---

# 4a.1: exact projection is necessary and not sufficient

**2026-11-11.** Step 4 phase 4a.1 of `docs/plans/2026-11-11-step4-comparator-plan.md`:
`v2/locfinder/measure/exact.py`, 38 fixtures in `v2/tests/test_exact_geometry.py`, and
`v2/scripts/mutate_exact_geometry.py` with **21 mutations, all caught** — figures as this phase
shipped; they are **44 fixtures and 25 mutations** after passes 38 and 39, and sections 5 and 6
below say what each pass added and why. Suite 1,254 passed,
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

## 6. Codex pass 38, the same day: 1 High, 5 Medium, 2 Low against all of the above

Every finding reproduced; the High re-derived independently before being acted on. The full report
and runnable reproducers are `docs/research/39-codex-review-pass38-counterexamples/`. Seven lessons,
and five of them are about claims in sections 1 to 5 of *this note*.

**A mutant that crashes is banked as a catch.** The harness ran each mutation and took a failing
test suite as proof the tests saw it. One mutation referenced `scaled`, a local of `rational_sqrt`,
from inside `_decide`: it raised `NameError`, the subprocess failed, and "22 of 22 caught" counted
it. **It had never once exercised the arithmetic it was named after.** Repaired to compute the floor
locally, it fails three fixtures as it always should have. Generally: *any "N of N caught" claim
needs a validity check on each mutant, not just an exit code.* Every mutant is now smoke-run on
ordinary input first and reported `INVALID` if it raises `NameError`, `AttributeError`, `TypeError`
or the like — and `--self-test` plants such a mutant to prove the detector fires, because a
crash-detector that cannot fire is the same defect one level up.

**I escalated a measured "this is wrong here" into "this cannot be done".** I had the measurement
that settles the same-edge rule: the rounded-prefix subtraction gives `0.0` on W3 and loses the
traversal. I then wrote that the alternative was **not implementable**, because a prefix arclength
is a sum of square roots. Both halves of that are wrong — the plan's own rule defined its prefixes
as the *rounded* ones, which are rational, and a finite sum of rational radicals is exactly
representable anyway, which pass 38 demonstrated by cancelling W3's irrational part symbolically.
This is a **new shape** of the old failure: not over-generalising a measurement, but **reaching past
a sufficient reason for a stronger one**. The measurement was enough. See
[[feedback-verify-the-shape-of-the-risk]].

**A blanket normative clause collects cases nobody checked it against.** Item 7 said "every
comparison that decides something made on the exact value". §2.2's two caps and its 0.01 m band are
comparisons that decide something, and all three are decided in binary64 on a correctly-rounded
residual. Witness: on `(0,-1)→(0,0)` from `(200, 1e-6)` the exact squared distance exceeds `200**2`
while the correctly-rounded residual is exactly `200.0`, so the exact predicate puts the point
outside the 200 m cap and the rounded one lets it in — an **eligibility** difference, not an
intermediate number. The clause is now scoped to the quantities item 7 fixes, and the exact-distance
cap is recorded as a *different convention* rather than quietly adopted or quietly denied.

**A fixture chosen for its roundness tests less than it looks like.** The only multi-segment span
fixture put the destination at a segment **midpoint**, where `t_d` and `1 - t_d` are the same
number. A mutation swapping them therefore passed all 40 fixtures — **625 s against 375 s** at
weight 1000. A second gap of the same kind: every fixture touching `exact_position` used a
horizontal segment or went through a residual, so dropping the `y` interpolation also passed all 40.
*Pick fixture values that make the formula's parts distinguishable, not values that are easy to
check by eye.*

**A counter named for a quantity can be measuring its image — and that one cost a published
result.** `parameter_differs` converted both parameters to `float` before comparing, so it counted
unequal *rounded images* of parameters that differ exactly. And the candidate-level comparison used
a *coarse* occurrence label with the parameter dropped, which I had justified as removing noise.
§2.2's occurrence key carries the **unrounded** parameter, so the coarse label is not the normative
identity. Re-measured: the exact parameter count is 2,142,228 against 1,333,808 rounded images, and
the **exact occurrence identity of the retained candidate changes on 573,107 of 844,685 point
observations — 67.85%** where the coarse reading reported zero. "The adoption changes no candidate
set" was true only of places, counts and vertex/segment structure. Both figures are now reported,
each under its own name.

*And the sentence above said "about three quarters" until pass 39 R4 measured it at 67.85%, which is
7.15 percentage points lower — a rounded-up recollection of a number I had in front of me. It is
also a rate over point **observations across five overlapping sets**, not over candidates and not
over a population.*

**A guard must bind what the measurement actually reads.** `explain_adoption_diff.py` asserted the
design **record count** matched the artifact's 808,433. Two record sets can hold that count and
differ in the geometry of the record being queried — the reproducer moved a measured residual from
1.0 m to 95.005 m without the count moving. The guard is now a digest of every coordinate of every
record plus its forward and reverse times, recorded in the artifact.

**A sentinel has to sit on the path that produces the numbers.** Mine called the projection
directly, so forcing *both* arithmetic requests to the float branch left it passing 2 of 2 while the
census reported zero for every difference — precisely the failed-adoption shape it existed to
reject. It now runs each witness through `adoption_stats`, and carries a **control** that must not
fire, because two witnesses cannot tell a live counter from one stuck at 1.

**And one about the artifact comparator**, which was the evidence for "nothing moved": it flattened
the document to dotted paths, so `{"x": []}` matched `{"x": [{}]}`, `{"x": {}}` matched `{}`, and a
literal `"a.b"` key collided with a nested one; `False` also matched `0`. It is now a recursive
typed comparison with a 13-case self-test, and the historical 610-leaf refactor claim **survives
re-checking under the stronger tool**.

## 7. Codex pass 39, on the repairs: 5 Medium, 2 Low, no High

Pass 38's eight repairs were reviewed the same day, because Codex pass 23 once found a defect in
every one of the four replacement rules written for pass 22. **Three of the seven findings are
defects in the repairs themselves**, and two of those are the repaired sentence overclaiming again.

**A correction can carry the same error as the thing it corrects.** Pass 38 F1 was my saying
"every comparison on the exact value" when §2.2's caps are decided in binary64. My fix said the caps
are decided "on the **correctly-rounded** residual, under both the production path and T0's exact
path". Production does no such thing: its residual is `shapely.distance`, a GEOS computation with no
correct-rounding guarantee, and pass 39 measured it **one ulp out** on an ordinary segment inside the
declared domain. I replaced one overclaim with a smaller one in the same sentence. What is actually
shared is weaker and is now what the design says: both compare a *computed binary64 distance*.

**Then the same thing a third time, in the write-up.** I wrote that the adoption was "a provenance
finding, not an answer finding" and that the manifests would differ "while reporting the same
answers". Pass 39 built the route I had asserted did not exist: feed the two occurrence identities
into the same normative `same_edge_fraction` and the remaining fractions are `0.4` and
`0.39999999999999997`, which at an admissible weight is **512 seconds** apart. The same paragraph
also said "the largest displacement anywhere is half a nanometre", which contradicted a figure three
paragraphs further down in the same document: the retained candidates at C's two swap points move
36 µm and 7 µm. `4.66e-10` m is the largest movement of a position compared *with itself*.

**The lesson is not "be more careful".** It is that a *summary sentence* is where this failure lives.
Each of the three was a short confident clause written to round off a section, over a scope nobody
had enumerated, in a document whose detailed figures were right. **The detail was never wrong; the
summary was.** So: when a section ends with a sentence that generalises its own table, check the
sentence against the table rather than against the intention.

**A crash-classifier cannot separate "invalid" from "wrong".** I had put `TypeError` in the list of
errors meaning a mutant is structurally broken. Replacing an integer floor division with true
division is a *legitimate arithmetic defect* and raises exactly that, so my detector would dismiss a
real mutation as invalid. And the smoke that was supposed to prove validity called
`same_edge_fraction` only across segments, leaving the same-segment branch unprobed — a broken
mutant there would still have been banked. Narrowed the error list to undefined-name, import and
syntax classes, extended the smoke to every branch, and added a **digest comparison**: when a mutant
computes exactly what the clean module computes, the harness now prints `UNSEPARATED` rather than
claiming anything about reachability. Ten of 25 come back `UNSEPARATED`, which is honest and useful —
those mutations are distinguished only by the suite's specific inputs.

**A third `fsum` had no mutation.** The total had one and the prefix had one; the summation that
combines the *span's* terms did not, so left accumulation there passed all 43 fixtures while
returning `1.0000000000000002` for a complete traversal whose fraction is exactly `1.0`. Added, with
a fixture whose expected value follows from the rule rather than from a run.

**And the strengthened sentinel was still defeatable, so this time the fix was tested against the
attack.** Pass 39's patch returned the float result whenever no *coarse* key changed — and the
census records **zero** coarse changes in 36.5 million positions, so that erases the entire signal
while the sentinel passes 3 of 3. Both my positive witnesses were vertex/interior transitions. The
repair adds an **interior-only** witness, where the parameter must move and the structure must not,
and gives every counter its own expectation per witness, because the old control demanded only
`NOT(parameter AND vertex)` — which a counter stuck at 1 satisfies. I then re-ran pass 39's own
attack against the new sentinel and confirmed it is rejected. **Checking a repair against the
specific attack is cheap and I had not been doing it.**

## 8. Phase 4a.2: the divergence is about half, and two scope claims died by measurement

`v2/locfinder/measure/certify.py`, 40 fixtures, 21 mutations all caught,
`scripts/measure_certified_argmin.py`. Suite 1,300 passed, 24 skipped.

**The number item 5 was missing.** When §2.4's tie rule fires on a manufactured cost tie — a partial
traversal against a full edge at exactly its rounded cost, which is W5 generalised from one witness
to a population — the convention selects the wrong journey **51.42%** of the time at UTM-like
magnitudes and **48.32%** at toy magnitudes, over 5,000 draws each. So "unknown rather than small"
becomes "about half, when the rule fires". How often it fires on a real graph is still unmeasured,
and that is 4c.

**The invalidation condition was run, not asserted.** The plan said the approach fails if
`UNRESOLVED` is common rather than confined to exact ties. **Zero** `UNRESOLVED` in 10,000 draws,
worst refinement `2**-64`. Pass 37 F1 was a condition I wrote down and did not execute; this one is
executed and its result is in the artifact.

**The interval primitive's bound is proved by squaring, not inferred from its construction.**
`s = isqrt(floor(q * 4**k))` gives `s/2**k <= sqrt(q) < (s+1)/2**k` because `s**2 <= floor(q*4**k)`
and `(s+1)**2 > floor(q*4**k)` are integer facts. Pass 37's lesson — integer scaling alone is not a
rounding proof — is why that is a test over a constructed family rather than a comment.

**The harness found two real gaps the 34 fixtures missed, and both are about where fixtures were
chosen from.** Replacing the bracket's floor with a **ceiling** passed everything, because a ceiling
breaks the lower bound only when rounding the scaled radicand up crosses a perfect square; uniform
random radicands never land there. Witness found by search: `q = 130461413/6` at `k=1`. And no
fixture spanned **more than two segments**, so deleting the whole middle segment of a span changed
nothing anywhere. Both are the same lesson as pass 38 F3's midpoint destination: *fixtures drawn
from the easy part of the input space test the easy part of the code.*

Two further survivors were **equivalent** mutants — removing the zero-denominator guard still raises
`ZeroDivisionError` from the next statement, and removing the index guard still raises `IndexError`
from the list — so both now mutate to *swallow* the condition instead. And one anchor matched twice,
because `_rational_cost` carries the same orientation lines, so that mutation had been reporting
SKIP and testing nothing. **That is pass 38 F3's defect again, found by the harness itself this time
rather than by a reviewer** — which is what the SKIP report is for.

**Two scope claims in the plan died by measurement rather than by argument**, which is the part of
this phase I would keep if I kept nothing else:

* the rate "over T2's frames" needs a router, and the router is a *later* phase — the plan had a
  dependency after its dependent;
* the rate "over T4's fixtures" would measure nothing: **0 of 17** fixtures has a near tie, the
  tightest margin being `0.8` at 3.6e15 ulps. Threading exact term provenance through the oracle to
  sweep them would have been a day spent certifying foregone conclusions. **Measuring the margins
  first cost four minutes.**

**And that measurement found something better than the sweep.** §2.4's travel-time discriminator
fires in **11 of 17** fixtures, always on an exact tie, and in **10** of those 11 every tied journey
carries the same travel time — so the choice cannot move a reported number. The rule's *consequence*
is covered by **one** fixture. Against a measured ~50% wrong-selection rate when a tie is
manufactured, that is thin cover for a load-bearing rule. **A rule can be exercised often and tested
once.**

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
