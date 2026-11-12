You are an adversarial reviewer. Your job is to find what is wrong, not to confirm what is right.

**This pass reviews the FIXES made in response to pass 38, not the whole instrument again.** Pass 38
found 1 High, 5 Medium and 2 Low; all were acted on in commit `2fb706b`. A repair deserves the same
adversarial pass as the thing it repairs, and in this project repairs have failed before: Codex pass
23 found a defect in every one of the four replacement rules written for pass 22.

Repository: C:\Users\arikt\documents\github\distanceFinder, branch v2-rethink, HEAD `2fb706b`.
Python is at v2/.venv/Scripts/python.exe; the suite runs from v2/ with
`.venv/Scripts/python.exe -m pytest -q` and passes 1,259 / 24 skipped here. Run code to check
claims; do not reason about floating point from memory. Pass 38's own report and reproducers are in
docs/research/39-codex-review-pass38-counterexamples/ and still run.

## What changed, and what to attack about each

**F1's fix — design §2.4 item 7.** The clause "every comparison that decides something made on the
exact value" is now scoped to the quantities item 7 fixes, and §2.2's two caps and 0.01 m band are
stated to be decided on the correctly-rounded residual. An exact-distance cap is recorded as a
*different convention*, left open rather than adopted.
* Is the scoped clause now **accurate**, or does it still claim something the code does not do?
  Enumerate the comparisons item 7's quantities actually contain and check each.
* Does the new text **contradict §2.2**, which declares the caps as inclusive distance limits? If
  §2.2 says "within 200 m" and item 7 says that is decided on a rounded residual, is §2.2 now
  ambiguous, and does it need its own amendment rather than a note inside item 7?
* Is "leave it open as a different convention" defensible, or is it a way of not deciding? What
  would it cost to decide it, and does anything in §3's estimands depend on which way it goes?

**F2's fix.** The "only implementable reading" claim is withdrawn in both the design and the step 4
plan, and replaced with the measured reason: the rounded-prefix subtraction gives 0.0 on W3.
* Is the replacement reason **sufficient and correctly stated**? Does the new text now claim
  anything about representability that is still too strong?

**F3's fix — v2/scripts/mutate_exact_geometry.py.** The crashing mutation now computes the floor
locally; two new mutations cover `exact_position`'s y interpolation and the cross-segment
destination partial; every mutant is smoke-run first and reported INVALID if it raises one of
`NameError, ImportError, SyntaxError, IndentationError, AttributeError, TypeError,
UnboundLocalError`; `--self-test` plants a broken mutant to prove the detector fires. 24 mutations,
all caught.
* **`TypeError` is in that list.** Can a legitimate behaviour-changing mutation raise `TypeError` on
  the smoke input and be wrongly dismissed as INVALID? Construct one.
* Does the smoke actually **execute every mutated line**? Find a mutation whose line the smoke never
  reaches, so a broken mutant there would still slip through.
* What rule in `exact.py` still has **no** mutation attacking it? Pass 38 found two; find the next.
* Are any of the 24 equivalent mutants, so "caught" is luck?

**F4's fix — v2/scripts/t0_attachment_pilot.py and the corrected census.** The parameter comparison
is now exact (`Fraction(pf.t)` against `pxx.t`), reported as `exact_parameter_differs` beside
`rounded_parameter_image_differs`; a new candidate-level `exact_occurrences_changed` uses
`exact_occurrence`, which keeps the parameter. The corrected census reports 2,142,228 exact
parameter differences against 1,333,808 rounded images, and the retained occurrence identity
changing on 573,107 of 844,685 points (67.8%).
* Is `exact_occurrence` **correct**? It is a conditional expression over a tuple slice; check its
  precedence and its behaviour on both vertex and interior keys.
* Is comparing a float-derived `Fraction` against an exact `Fraction` the **right** cross-arithmetic
  comparison, or does it overcount — for instance by treating a parameter that is merely
  *represented* differently as a different occurrence when §2.2 would call them the same?
* Is **67.8%** the right figure for the claim made about it in
  docs/experiments/t0-attachment-pilot.md? The write-up calls the result "a provenance finding, not
  an answer finding". Attack that framing: is there a route by which a changed occurrence identity
  changes a reported number, and does §12's manifest requirement make this worse than the write-up
  admits?
* The write-up still reports zero for eligibility, counts, places and vertex/segment structure.
  Given F4, is any of those four also measuring the wrong quantity?

**F5's fix.** `adoption_sentinel` now runs each witness through `adoption_stats` and carries a
control case that must not fire.
* Can the sentinel still pass while the adoption is dead? Try to defeat it as pass 38 defeated its
  predecessor — patch something in memory so the census reports zeros and the sentinel passes.
* Does the control case constrain anything, or would it pass under any implementation?

**F6's fix.** The artifact records `design_records_fingerprint`, a SHA-256 over
`shapely.to_wkb(geom, flavor="iso")` plus the forward and reverse times of every record in order;
`explain_adoption_diff.py` checks it.
* Does WKB capture the coordinate **bits** exactly, or can two records with different binary64
  coordinates produce the same WKB?
* The script still **duplicates** six lines of the pilot's graph preparation. Does the fingerprint
  make that safe, and what does it still fail to bind?

**F7's fix — v2/scripts/compare_t0_artifacts.py.** Rewritten as a recursive typed structural
comparison with a 13-case self-test, including pass 38's four cases.
* Find a pair of distinct artifacts it still reports as equal. Check the bool/type branch carefully:
  `type(a) is not type(b) and not (isinstance(a, bool) or isinstance(b, bool))`.
* Does the volatile-path matcher behave correctly now paths are tuples? Can a pattern strip more
  than intended?

**F8's fix.** The zero-total row of the step 4 plan is marked superseded.
* Is any *other* row of that table, or any other statement in that plan, still contradicting design
  revision 13?

## Also worth a look, unprompted by pass 38

* `v2/tests/test_exact_geometry.py` is now 43 fixtures. Are any of them **asserting the
  implementation rather than the rule** — a fixture whose expected value was read off a run?
* Everything in docs/engineering-notes/project-phase1-s3-step4a-exact-geometry.md sections 5 and 6,
  and docs/research/39-codex-review-pass38.md, states what was measured. Check the numbers against
  the artifact and the code.

## How to report

Severity (High / Medium / Low), the claim refuted quoted from the artifact, a **runnable**
reproducer, and the numbers it produces. Put reproducers under
docs/research/40-codex-review-pass39-counterexamples/ as standalone scripts that run with
`v2/.venv/Scripts/python.exe -B <script>` from the repository root, plus a REPORT.md. Do not create
temporary directories inside the repository.

If a fix is sound, say so explicitly and say what you ran. A confirmed repair is as useful to me as
a defect, because repairs in this project have a poor record.
