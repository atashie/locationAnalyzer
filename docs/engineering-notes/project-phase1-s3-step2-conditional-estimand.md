---
name: project-phase1-s3-step2-conditional-estimand
description: "E1c, the conditional false-inclusion rate, is drafted as reported-not-gated because the measurement forces it - the claim denominator is ~37 of 500 on the binding frame, not the 417 the design's own example implied, so a 1.0% gate is unreachable and reaching it costs 8.2x the sampling"
metadata:
  node_type: memory
  type: project
  originSessionId: 3448970c-7f62-4034-83e7-b7d86efb0261
  modified: 2026-11-09T00:00:00.000Z
---

Plan §0 step 2, phase A. Design **revision 12 is a draft awaiting the owner** and is not in force;
nothing in it can fail a layer.

**What it adds.** `E1c = Pr(comparator = FAIL | product = PASS)` — of the claims the product made,
the share that are wrong. E1b divides by the whole frame, so every point where the product declined
to answer makes the published rate smaller, and a user is exposed to the error only where a claim was
made. E1a and E1b, their thresholds, §4's allocation and §8's acceptance rule are untouched.

**The question "report it or gate it" was settled by measurement, and it is worth recording that it
was not settled by preference.** I had planned to recommend report-only on the grounds that gating
changes the acceptance rule. The measurement made the recommendation unnecessary:

- The design's own illustration — "one error among **417** claim-making observations gives 1.1325%"
  — is the **answered** denominator, PASS *and* FAIL: 500 × (1 − 0.166722). E1c conditions on PASS
  alone. Measured from the saved arrays, the PASS share is **7.3358% of area** at *T* = 10, so the
  claim denominator at *n* = 500 is about **37**, a **13.6×** shrink rather than 1.2×.
- At a claim denominator of 37 — written `n_claim` in the design, because *m* is already the mode
  there — **zero** observed errors still bounds only **7.7775%**, and
  `tolerated_failures(n_claim, 0.01)` returns **-1** at all four published claim denominators — §4's own unreachable-gate condition,
  the one pass-15 H2 found shipped undetected in revision 2.
- A reachable 1.0% gate needs `n_claim` ≥ **299**, i.e. *n* ≈ **4,076** on the binding frame and
  threshold: **8.2×** §4's allocation. `n_claim` is random, so each of these is its **expectation**
  at *n* = 500; the realised denominator is reported as drawn.

So E1c's deliverable is **a wide interval, honestly reported**. Its precision is inherited rather
than chosen, because it has no allocation of its own, and that is stated in the design rather than
left for a reader to work out from the denominator.

**It also required narrowing a rule rather than quietly failing it.** §3 said a conditional rate may
be added "**only** as a separately named measure with its own formula, threshold and allocation".
E1c has two of the three. The amendment therefore **narrows the rule in place** — a conditional rate
with no acceptance role needs name and formula only; one that gates still needs all three — instead
of inventing a threshold the data cannot support or dropping the sentence without saying so.

**The one error most likely to survive review, named in the design for that reason.** Frame B is SRS
without replacement, so conditional on the observed `n_claim` the numerator is binomial and
Clopper–Pearson on `(k, n_claim)` is valid. **Frame C is two-stage**, so its conditional rate is a *ratio
of two estimated quantities* and the binomial bound does not apply; it needs a percentile bootstrap
over **whole cells**. Reusing `clopper_pearson_upper` on frame C would produce a figure that looks
right and is not.

**Two properties that are the opposite of E1b's, and are therefore easy to get backwards.** The claim
denominator is random but **fully observed** — the product's verdict is known everywhere — so
unresolved comparator verdicts inflate the **numerator only** and `u` never enters the denominator.
And `n_claim` = 0 reports **undefined**, never 0.0: an all-`UNKNOWN` product passes E1a and E1b at 0.5974%
(§4), and E1c's denominator vanishes instead of its numerator, so it is the first reported number
that declines to conceal that. Collapsing undefined to zero would restore exactly the concealment it
was added to end.

**Only the inclusion direction is conditioned, and that asymmetry is measured, not argued.** The
dilution argument is symmetric in form. Conditioning on product PASS shrinks the denominator
**13.6×**; conditioning on product FAIL shrinks it **1.3×**, because a sound lower bound on the FAIL
share is 75.2540% of area. E1a is therefore already close to its own conditional and E1b is not. If
a future layer's FAIL share falls materially, the case for a conditional false-exclusion rate
returns.

**What no conditioning can ever see.** The product and the comparator read the **same destination
list**, so a grocery that has closed, is fenced off or was never there produces *agreement* between
the two sides and a wrong answer from both. E1c measures "of the homes we recommend, the share our
own comparator judges wrong", not "the share that would disappoint on arrival". Only plan §0's
walked-journey audit measures the second — see [[project-phase1-s3-step0-audit-harness]].

**The check is shaped like the risk, which here is a wrong number.** `v2/scripts/verify_e1c_figures.py`
recomputes all 59 quoted figures from the arrays and from `locfinder.measure.stats`, renders each as
the document renders it, and fails if the document does not contain it. It was tested by perturbing
one digit — `7.3358%` → `7.3359%` — and it failed on that digit. A doc-figure check that has not been
shown to fail is the pattern in [[feedback-verify-the-shape-of-the-risk]], three times over.

**Also fixed here: revision 11 had no header block and no §13 row**, so the body referred to
"revision 11" in eight places while both of those stopped at revision 10. That is the same silence
pass 30 found in the plan's step-1 row, one document along, and a revision-12 row would have sat on
top of a missing one. Both are now written.

**Phases B–E are deliberately not begun.** A Codex pass on the draft comes before any code, because
a statistics error is cheap in prose and expensive once it is wired into T6's manifest and T11's
report. Then `stats.py`, its tests, and the wiring — and the first thing to check there is whether
the persisted record carries per-observation **product and comparator** verdicts; if it does not,
E1c cannot be recomputed from a stored run and that is a T6 gap to report rather than a scope to
widen. See [[project-phase1-s3-design]].
