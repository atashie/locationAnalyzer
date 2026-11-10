---
name: project-phase1-s3-step2-conditional-estimand
description: "E1c, the conditional false-inclusion rate, is drafted and NOT in force - its claim denominator is ~37 of 500 on the binding frame rather than 417, and Codex pass 31 withdrew the interval specification because the prescribed bootstrap reports certainty at zero errors"
metadata:
  node_type: memory
  type: project
  originSessionId: 3448970c-7f62-4034-83e7-b7d86efb0261
  modified: 2026-11-10T00:00:00.000Z
---

Plan §0 step 2, phases A and B. Design **revision 12 is a draft awaiting the owner** and is not in
force; nothing in it can fail a layer. Commits `c93df95`, `c6807ca`, and the pass-31 amendment.

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

## State

**Phases C-E are not begun, and now for a sharper reason than caution: there is no interval method
to implement until the owner picks one.** When there is, the first thing to check is whether the
persisted record carries per-observation **product and comparator** verdicts; if it does not, E1c
cannot be recomputed from a stored run, and that is a T6 gap to report rather than a scope to widen.

**Also fixed in phase A: revision 11 had no header block and no §13 row**, so the body referred to
"revision 11" in eight places while both stopped at revision 10 — the same silence pass 30 found in
the plan's step-1 row, one document along. See [[project-phase1-s3-design]] and
[[project-phase1-s3-step0-audit-harness]].
