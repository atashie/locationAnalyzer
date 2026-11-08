---
name: feedback-benchmark-over-point-fixes
description: "When review fixes keep breaking adjacent cases, stop point-fixing and build a graded benchmark with intended answers written down first"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 3448970c-7f62-4034-83e7-b7d86efb0261
  modified: 2026-11-04T21:30:00.000Z
---

Learned 2026-11-04 on `v2/locfinder/places/resolve.py`, across Codex passes 10-13. **Four
consecutive passes found over-corrections in the same file**: equal categories broke
de-duplication (p10 H4), a raw-set replacement repeated it for stations and fuel (p11 M1), a
subsidiary boolean merged a car park with its airport (p12 H4), and p13 found three more. Every fix
closed the reviewed case and broke an adjacent case nobody had written down.

**Why:** a review finding is one input. Fixing against it optimises for that input, and the
adjacent cases are invisible because nothing asserts them. More care at the moment of fixing does
not help — I tried that for three rounds.

**How to apply:** when a second round of fixes in one area breaks something new, stop and build the
benchmark instead of attempting a third. For the resolver that meant 5 graded queries -> **41 graded
assertions** in `v2/benchmarks/resolver_queries.json`, with intended answers written down **before**
running, and `spikes/s2_resolver_benchmark.py` to grade them. It found **six live defects on its
first run**, including a medial-apostrophe tokenisation bug that had survived because the existing
test used a *trailing* apostrophe.
- Include **property** assertions, not just location ones: outcome kind, the role of the leading
  candidate, whether a typed locality ranked, whether two spellings agree. Most of what kept
  breaking was identity and confidence, not position.
- **Audit the assertions as hard as the code.** Two of mine were wrong: one demanded an outcome no
  ranking could deliver, and one used a proximity test *the wrong answer satisfied* (a bus platform
  56 m from the hospital). **An assertion the wrong answer can pass is worse than no assertion.**
- Leave an assertion **red** when the real fix is a decision rather than a tweak, with the cause
  named in the benchmark file. A red benchmark that names a defect beats a green one.
- Do not invent reference data to widen grading. Say the gap needs an independent source.

**And then pass 14 measured whether the benchmark actually guarded what I built it for. It did
not.** Codex reverted each historical merge over-correction in memory: only pass-10 H4 turned a
benchmark assertion red; pass-11 M1, pass-12 H4 and pass-13 M7 turned **none**. Running the same
four reversions against the unit tests, all four are caught there. So:
- **Verify the guard by reverting the fix.** It is a cheap, decisive experiment and it was not my
  idea. Do it when claiming a test or benchmark protects something.
- **Know which instrument guards what.** Unit tests on constructed fixtures are the regression
  guards; the real-index benchmark is the instrument that finds *new* defects. I had claimed the
  benchmark was the guard; it was not.
- **An assertion no correct answer can pass is as bad as one a wrong answer can.** My Weaver Street
  row required a Carrboro branch, which would have rejected a correct Hillsborough or Raleigh one.
- **Pin location and identity to the same candidate.** `offered_near` is satisfied by *any*
  candidate, so a 5 km distance check passed a dessert shop for "Southpoint", and a Raleigh bus stop
  led while a different candidate supplied the proximity. Assertion kinds `lead_near`,
  `lead_name_contains` and `offered_named_near` exist for this.
- Tightening those assertions **immediately exposed two more live defects** (a 34.9 km and a 32 km
  wrong answer), which is the strongest argument for doing it.

**Pass 15 added the sharpest instance yet, and it was not in a test but in a *fix*.** The design
required pooling blocks "with their nearest **qualifying** neighbour"; I correctly found that
undefined when no block qualifies, and made my fix terminate by merging everything into **one**
block. Resampling one block returns the identical dataset in all 2,000 bootstrap replicates — a
**zero-width interval for an uncertain statistic**. My test asserted that termination, so it would
have *enforced* the defect. "Do not turn a single block into apparent precision."

So the rule generalises beyond assertions: **when a fix makes a degenerate case terminate, check
what the degenerate case now reports.** Terminating is not the same as being right, and a
confident-looking wrong answer is worse than a crash.

Related: [[feedback-codex-adversarial-review]], [[feedback-experiments-over-priors]],
[[feedback-computable-property-is-not-the-claim]],
[[feedback-a-predeclared-gate-must-be-shown-reachable]].
