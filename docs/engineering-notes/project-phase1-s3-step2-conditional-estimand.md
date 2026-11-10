---
name: project-phase1-s3-step2-conditional-estimand
description: "E1c, the conditional false-inclusion rate, is ADOPTED 2026-11-10 as reported-never-gated with an approximate Clopper-Pearson bound - its claim denominator is ~37 of 500 on the binding frame rather than 417, and pass 31 killed the bootstrap that reported certainty at zero errors"
metadata:
  node_type: memory
  type: project
  originSessionId: 3448970c-7f62-4034-83e7-b7d86efb0261
  modified: 2026-11-10T00:00:00.000Z
---

Plan §0 step 2, phases A-D. Design **revision 12 was adopted by the owner on 2026-11-10** after
Codex pass 31 amended the draft. Commits `c93df95`, `c6807ca`, `337b635`, and the adoption.

**The owner's three decisions.** (1) **Add E1c.** (2) **Report it, no bar** — no threshold and no
acceptance role; E1c cannot fail a layer. (3) **Clopper-Pearson, declared approximate** — route (a);
exact hypergeometric inversion is deferred and must be revisited in the same §13 row that ever gives
E1c a bar.

**The cheap route to a bar, recorded because my first estimate of it was wrong by an order of
magnitude.** I said a reachable 1.0% bar costs 8.2× the sampling. That is the cost of getting there
by enlarging the *full-frame* draw. Drawing a **conditional sample from the PASS domain** — the exact
pattern §4's four diagnostics already use, each 150-200 observations — needs **299 claims to tolerate
zero errors, 473 for one, 628 for two**. So roughly 300-500 observations per frame, not 4,454. The
PASS domain is a deterministic lookup on the frozen product, so such a sample is directly drawable.
That option is now in the design and is what a future gating decision should cost out against.

**What it adds.** `E1c = Pr(comparator = FAIL | product = PASS)` — of the claims the product made,
the share that are wrong. E1b divides by the whole frame, so every point where the product declined
to answer makes the published rate smaller, and a user is exposed to the error only where a claim was
made. E1a and E1b, their thresholds, §4's allocation and §8's acceptance rule are untouched.

**The denominator correction, which is the part that survived review.** The design's own
illustration — "one error among **417** claim-making observations gives 1.1325%" — is the
**answered** denominator, PASS *and* FAIL: 500 × (1 − 0.166722). E1c conditions on PASS alone.
Measured from the saved arrays, the PASS share at *T* = 10 is **7.3358% of area**, so the claim
denominator (`n_claim`; *m* is already the mode in that section) is about **37** at *n* = 500, a
**13.6×** shrink rather than 1.2×. At 37, zero observed errors still bounds only **7.7775%**, and
`tolerated_failures(n_claim, 0.01)` returns **-1** — §4's unreachable-gate condition, the one
pass-15 H2 found shipped undetected in revision 2.

## What Codex pass 31 took away, having reviewed the draft before any code existed

Eight findings, all reproduced independently before being acted on. **Placing the review before the
implementation was the highest-value decision in this step**, for a concrete rather than rhetorical
reason: the method it killed would otherwise already have been wired into T6's manifest and T11's
report.

**1. The interval specification is withdrawn, not patched.** I prescribed a percentile bootstrap
resampling whole cells for frame C. It is **degenerate at exactly the boundary this measurement lives
on**: with zero identified errors every replicate contains zero errors, so the interval is `[0, 0]` —
*certainty*. Run through `percentile_bootstrap` itself on 463 non-claims and 37 correct claims it
returns **`(0.0, 0.0)`**; with one claim, **`(nan, nan)`**. Worked case on this layer's own frame:
let 243 of the 24,245 PASS cells be erroneous, a true E1c of **1.00227%**, just over the line. An SRS
of 500 misses all 243 with probability **0.6920924**, so **69.2% of samples would report certainty
against a rate above the line.** It also contradicted my own "roughly 8% at best" — under the
prescribed method a zero-error result reports zero.

**2. My reason for preferring it was the wrong distinction.** "Frame C is two-stage, so
Clopper-Pearson cannot apply" does not follow. With **one point per cell, resampling whole cells and
resampling complete rows are the same operation** — "whole cells" adds no cluster information. Where
PASS is constant within a cell, the conditional count is **exactly binomial** if the within-cell
error rates are equal and hypergeometric if they are 0/1; and the **zero-error** CP bound *is*
conservative there, by `Pr(K=0 | m) = e_m(1−q₁,…,1−q_A)/C(A,m) ≤ (1−θ)^m`. So the categorical
prohibition was wrong, and the zero-error figures the amendment argues from are sound.

**3. Frame B's conditional law is hypergeometric, and one-sided CP is not universally conservative
under it.** `CP_upper(71, 72)` = 0.999287846835 against a true 79994/80051 = 0.999287953929 gives
coverage **94.998570%**. Minute, adjacent to a 100% error rate, irrelevant to anything reported near
1% — and it still disproves the unqualified guarantee I wrote. **§6 carried the same overbroad
sentence**, which I inherited and widened; it is now bounded by where it holds.

**4. The constructive consequence I missed.** The PASS domain is **computable from the frozen
product**, so `A` is known rather than estimated — which means estimating *both* numerator and
denominator was an **estimator choice**, and it is the choice that created the ratio problem. Two
routes are now open for the owner: hypergeometric inversion against the known margin, or CP declared
as approximate. Either way three things must be specified that the draft left silent: the ratio
statistic, how unresolved completions `u` enter it, and what a zero-claim replicate contributes.

**5. "Settled by measurement, not preference" is withdrawn.** I had planned to *argue* for
report-only, measured the denominator, and then claimed the measurement settled it. It doesn't.
Insufficient precision for a **1.0%** gate is not an argument against **every** gate —
`tolerated_failures(37, 0.08)` = **0**, so an 8% gate is reachable now. Nor is 8.2× the cost of
gating: a separate sample drawn from the known PASS domain could collect claims without enlarging
every full-frame draw. "Reported, non-gating" is a **recommendation**, and the overreach had been
repeated in four places.

Two more scope errors in the same paragraph. "All four published claim denominators" — there are
**eight** combinations, four thresholds on two frames, and at *T* = 45 on frame B the expected
denominator is 414 where `tolerated_failures(414, 0.01)` = **0**, so the gate is reachable there. And
4,076 is an **expectation, not an assurance**: `hypergeom.sf(298, 330502, 24245, 4076)` = **0.5089**,
a coin toss; 95% assurance of the denominator needs **4,454**.

> **Every figure in this note was measured on the pre-rebuild layer, and is left as measured.** The
> 2026-11-10 rebuild (`ab01ffa`'s `symmetrise` fix, 7,246 cells) moves them slightly: PASS share at
> *T* = 10 is **7.3388%**, PASS cells **24,255**, the reachable-gate *n* **4,074** at **8.1×**,
> `E[n_claim]` **36.6942** with SD **5.8267**, the hypergeometric assurance **0.5083** with 95%
> assurance at **4,452**, the worked degenerate-bootstrap case 243/24,255 = **1.00186%**, and the
> ten-minute FAIL shares **75.2510%** of area and **83.6678%** of structures. The design document
> §3 carries the current values and `v2/scripts/verify_e1c_figures.py` checks them against the
> arrays; this note records the decision and the figures it was taken on. **No conclusion moves**:
> `n_claim` ≈ 37, the 7.7775% zero-error bound, `tolerated_failures` = -1 and the 299/473/628
> conditional-sample costs are all unchanged. Pass 35 found this note still presenting the old
> numbers with nothing saying so.

**6. The inclusion/exclusion asymmetry reverses inside this layer.** I measured one threshold and
wrote "if the FAIL share falls materially in a future layer". At ***T* = 45 on frame B** PASS covers
82.8831% of structures — a shrink of **1.2065×** — while FAIL is 16.4035% and at most 17.1169%, a
shrink of at least **5.84×**. The opposite of the ten-minute case. Pass 31 also noted the shrink
factor is a **proxy I mistook for the thing**: it quantifies the relationship but cannot decide
whether a conditional quantity is useful. A conditional false-exclusion rate is now deferred on
**scope**, and named as deferred rather than dismissed.

**7. Two overstatements about what E1c exposes.** "The first reported number that declines to hide"
an all-`UNKNOWN` product is false — **E0 already reports 100% `UNKNOWN`** by census, as do the
abstention table and the status cross-tabulation. And an **all-FAIL** product also has zero claims,
so an undefined E1c is not evidence of abstention. Also two distinct undefineds that must not be
reported as one: *no PASS in the population* versus *no PASS in this sample*.

**8. The blind-spot paragraph was right about the blind spot and wrong about the remedy.** The shared
error class is broader than a closed grocery: omitted destinations, wrong locations or categories,
shared road and access errors, the speed assumptions, the connector conventions — all survive
agreement between the two sides. And **nothing in this design estimates "the share that would
disappoint on arrival"**, which I claimed the walked audit does. It is 5-16 owner-chosen journeys, a
convenience sample, and E3 explicitly disclaims a population-rate claim; what it supplies is
**existence evidence**, a different kind of claim rather than a smaller version of the same one.
Step 7's truth audit also addresses destination validity, so "only the walk sees it" was wrong
twice. Finally, E1c's populations are structures and ground area — never users or households.

## The verifier was a fourth instance of my recurring failure, and is now self-testing

I built `v2/scripts/verify_e1c_figures.py` to recompute every quoted figure, tested it by perturbing
one digit, watched it fail on that digit, and called it "shaped like the risk". Pass 31 defeated it
with three mutations:

| mutation | first version |
|---|---|
| swap the *T* = 10 and *T* = 15 table rows wholesale | **passed** |
| delete the entire interval-method passage | **passed** |
| flip the conditioning event from product PASS to product FAIL | **passed** |

Every figure was still *present* after the swap — on the wrong row. **Presence is not association.**
I had tested it in the single way I had imagined it failing, which is the same error one level up
from the one [[feedback-verify-the-shape-of-the-risk]] records.

The rewrite does three things: it **parses the table and binds each figure to its row**, it
**asserts the subsection's required claims** so a deletion fails, and it **self-tests** —
`--self-test` applies those three mutations and fails unless each is caught. The ability to fail is
executable now rather than a sentence I wrote about it. 73 checks; all three mutations caught.

What it still cannot do is in its own docstring: it reuses `stats.py` for the CP arithmetic, so that
part is consistency and not validation, and it cannot see a wrong sampling law, inadequate coverage,
a boundary-degenerate interval, an expectation standing in for an assurance, or an invalid inference
from a correct number. Pass 31 found one of each — which is the argument for the review ordering
restated as a measurement.

## What was implemented, and the one rule encoded in a type

`stats.conditional_rate` returns a frozen **`ConditionalRate`** with `identified`, `unresolved`,
`claims`, an `identification_range` of `[k/n_claim, (k+u)/n_claim]`, a `bound_range` of
`[CP_upper(k), CP_upper(k+u)]`, and `interval_method = "clopper-pearson-approximate"` so the
approximation travels into every manifest that stores one.

**It deliberately has no `verdict` field and takes no `threshold` argument.** `Acceptance` is the
type that carries a verdict; this is not it. Owner decision 2 is "report it, no bar", and the way to
make a rule hold is to encode it where violating it would require changing the design rather than
forgetting a convention — the project's own standing practice. A test asserts the absence.

`claims == 0` returns an **undefined** result rather than raising, because an all-`UNKNOWN` *or*
all-`FAIL` product legitimately makes no claims; that is a fact to report, not an error, and not by
itself evidence of abstention.

**Pass 31's CP counterexample is kept as an executable test**, not just a paragraph: at `A` = 80,051
with 57 correct and 72 claims, `clopper_pearson_upper(71, 72)` falls below the true rate and
hypergeometric coverage is 94.998570%. The claim it refutes — "one-sided CP is conservative" — is
the kind that gets rewritten back in by someone reasoning from first principles, so it now fails a
test if it is.

**T6 needs no change.** Its persistence list already carries, per point and per threshold, the
product outcome and the comparator's status — so E1c is recomputable from a stored run, and the gap
I had flagged as a risk does not exist.

**1,147 passed, 24 skipped.** The figure verifier is at **90 checks with 8 mutations**, all caught.

## What Codex pass 32 took off the implementation

Eight findings, every one reproduced before acting. Four were in the **repairs** written for pass 31,
which is the pattern this project keeps producing.

**1. An impossible input produced a reassuring answer.** `conditional_rate(0, 0, float("inf"))`
returned `bound_range = (0.0, 0.0)` — certainty of zero error, the worst output this estimand has
available — and `conditional_rate(float("nan"), 0, 0)` reported `identified = 0`, because the
zero-claim branch discards its arguments before anything reads them. Fractional counts gave
ordinary-looking bounds. The counts are now checked to be `int` (and not `bool`, which is an `int`
subclass) **before any comparison and before the zero-claim return**.

**2. Three contract mutations survived all 146 tests.** Dropping `confidence` from both CP calls
(so a result labelled 99% could carry a 95% bound — 0.1219048982 against 0.1663382150), removing the
non-negativity guard (admitting `u = −1` and an inverted range), and removing `_check_confidence`
(an invalid level recorded on an undefined result). **The guards were present and untested, which is
the same as absent the moment someone simplifies them.** Four tests added, and a mutation harness
confirms each mutation is now caught by the test written for it, with `stats.py` restored
byte-identical.

**3. I widened the conservatism proof from a zero *count* to zero *identified* errors.** They differ
as soon as `u > 0`, because the upper endpoint is computed at `k + u`:
`conditional_rate(0, 71, 72).bound_range[1]` is **0.9992878468350281** with `identified == 0`, and
pass 31's coverage counterexample applies to it directly once its erroneous structures are recast as
unresolved. The design and the docstring now state the condition **per endpoint**. I also wrote that
`k` = 0 is "the case this measurement will actually be in" — at a true 1% rate with 37 claims there
is a **31.1%** chance of at least one error, so the conservative case is the one to hope for, not to
plan on.

**4. I wrote the wrong letter into the design.** The draft lettered the two interval routes with
**(a) = hypergeometric inversion**; the chat that put the choice to the owner lettered them the other
way round, so the owner's "a" meant Clopper-Pearson. I then wrote "decision 3 chose route (a)" into
the design, which said the opposite of both the decision and the implementation. **The letters are
gone and the methods are named** — a lettering that exists in two places with two meanings is a
defect waiting to happen.

**5. Adoption left live contradictions behind.** The plan still said "draft … not in force", the
interval still open, the phases not begun; the design header still argued "measured, not preferred"
and "all four published claim denominators" after both were withdrawn below; §13's row still said the
method was **OPEN** and still carried two claims pass 31 had retired. **Retaining both the assertion
and its withdrawal does not finish a repair** — the normative copy has to say one thing.

**6. The verifier still certified misplaced meanings.** Three more mutations passed all 83 checks:
swapping the frame B and frame C **column labels** (positions bound, meanings not), replacing the
specified bound-range **formula**, and exchanging **7.7775%** and **4.0754%** between their
frame/threshold cases. Its parser also silently overwrote a duplicate threshold row. Now the header
labels are validated, each quoted bound is matched as `**value** (frame, T=minutes)`, the formulas
are required claims, and duplicate rows are reported. Fixing it also exposed a formatting break my
pass-31 edit had caused: the bound list had been absorbed into a block quote.

**7. `--self-test` mutated the tracked document.** It wrote mutations directly to the design and
restored from a fixed shared temporary filename, so two concurrent runs could restore each other's
mutated text and a forced termination could **leave a mutation installed in the repository**. It now
works on a private `TemporaryDirectory` copy — `check()` already took a path, so that was all it
needed. Verified by hashing the document across a run.

**8. "The type forbids gating" was overstated.** `conditional_rate(0, 0, 299).bound_range[1] <= 0.01`
is a gate, and no API can prevent that. The absence of a `verdict` field means nothing here
*computes* one and a stored result cannot be mistaken for a decision — a guard rail, not a wall.
**Actual enforcement belongs where the layer verdict is assembled**, which is §8's rule and
`Acceptance`, and E1c must appear in neither.

**What pass 32 confirmed.** All five implementation mutations I asked it to try were killed by the
tests. The frame C zero-count inequality is correctly transcribed, conditional on `m` > 0 and PASS
constant within original cells. The 299/473/628 minima are right, and **a sample drawn directly from
the frozen PASS domain introduces no selection mismatch for E1c**, provided it stays out of the
full-frame estimates and frame C's two-stage design is preserved. No existing acceptance arithmetic,
threshold or allocation changed.

**§6 needed a third attempt, and the second was wrong in an instructive way.** I first repaired
"binomial bounds are conservative" to "conservative **at the allocations and rates this design
reports**". Pass 32's counterexample is *at* an allocation and a rate this design reports: with
`N` = 2,925, `n` = 150 and one event, `CP_lower(1, 150)` = 0.000341896836 exceeds the true
`1/2925` = 0.000341880342 and coverage is **94.871795%**. So the qualification I added was
insufficient rather than sufficient. The sentence now claims only "usually, not universally" and
**defers to per-bound arguments** — the one this design relies on being §3's zero-count case.

## State

**Also fixed in phase A: revision 11 had no header block and no §13 row**, so the body referred to
"revision 11" in eight places while both stopped at revision 10 — the same silence pass 30 found in
the plan's step-1 row, one document along. See [[project-phase1-s3-design]] and
[[project-phase1-s3-step0-audit-harness]].
