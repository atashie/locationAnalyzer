---
name: feedback-a-predeclared-gate-must-be-shown-reachable
description: "Before predeclaring a PASS/FAIL rule, compute whether the best possible observation passes it at the predeclared sample size; choose n by failure tolerance, not by the zero-event bound"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 3448970c-7f62-4034-83e7-b7d86efb0261
  modified: 2026-11-05T03:30:50.385Z
---

Learned 2026-11-04, Codex pass 15 on the S3 measurement design. I predeclared an acceptance rule
that **no observation could satisfy**:

```
n = 400, failures = 0, DEFF = 2  ->  effective n = 200
one-sided 95% exact upper bound  =  1.4867%
E1b threshold                       1.0%
```

Perfect agreement could not certify the product. Two revisions of a document whose entire purpose
was to be checkable in advance, and nobody had computed the best case.

**Why:** a predeclared gate is written in the register of a commitment, which makes it feel settled
rather than calculated. The threshold and the allocation were chosen in different sections, for
different reasons, and the interaction between them was never evaluated.

**How to apply:**
- **Compute the best-case and worst-case outcome of any gate before predeclaring it.** If the
  best possible observation fails, the gate is not strict, it is broken.
- **Choose *n* by failure tolerance, not by the zero-event bound**, because the zero-event figure
  hides a cliff. Measured for a one-sided 95% exact bound against a 1.0% threshold: *n* = 400
  tolerates **exactly zero** failures (k=1 gives 1.1804%); *n* = 473 is the minimum that survives
  one, at 0.9990% — too close to the line to predeclare; *n* = 500 survives one at 0.9452%. Publish
  that tolerance **next to** the bound, so a near-miss is legible.
- **State the consequence in the design**: "E1b admits at most one observed false inclusion" is a
  sentence the owner can react to; "the bound must be ≤ 1.0%" is not.
- A rounded fixture table is not a numerical test. My statistical tests used only the design's
  printed zero-event values, and Codex produced a wrong implementation —
  `k/n + (1-k/n)*(1-0.05**(1/n))` — that matched every one of them, both endpoints and monotonicity,
  while giving 0.9943% at k=1, n=400 against the correct 1.1804%: **enough to flip the verdict.**
  Always add non-zero fixtures computed by an independent route.

## A second shape, 2026-11-17: the gate that never fired

The same lesson from the other end. `v2/scripts/measure_fsq_coverage.py` carries a contradiction
diagnostic: per category, a regex over the record's own name and the sentence that would deny it,
so a proposal of "not a grocery" about a record called *Super Mercado* is reported as evidence
against **the provider**, not against the record. In the pharmacy half it found the session's most
useful result -- FSQ calls Fuquay Pharmacy a dentist, and 16 of 26 negative proposals deny the
record's own name.

In the grocery half it reported nothing, because FSQ made **zero** "not a grocery" proposals for
that set. The gate did not pass. **It was never reached**, and a clean result from a gate that
could not have fired looks exactly like a clean result from one that did.

> Report how many times a gate was **reached**, not only what it found. A diagnostic that prints
> nothing is ambiguous between "no contradictions" and "no opportunity to contradict", and a report
> will be read as the first.

The same shape caught a test the same day: an assertion that the cache is empty after a provider
failure **passes trivially against code that never caches at all**. The three cache fixes were each
proved by reverting to the defect and watching the specific test fail. A gate must be shown
reachable and a test must be shown to discriminate; neither is established by it being green.

Related: [[project-phase1-s3-fsq-coverage]],
[[feedback-match-statistical-machinery-to-the-design]],
[[feedback-computable-property-is-not-the-claim]], [[feedback-codex-adversarial-review]].
