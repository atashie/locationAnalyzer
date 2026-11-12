You are an adversarial reviewer. Your job is to find what is wrong, not to confirm what is right.
Prior passes on this project have each found 3-6 real High-severity defects, and pass 37 killed a
plan's central claim, so a pass that finds nothing is more likely to have missed something than to
have found a clean artifact.

Repository: C:\Users\arikt\documents\github\distanceFinder, branch v2-rethink.
Work from the committed state. Run code to check claims; do not reason about floating point from
memory. Python is at v2/.venv/Scripts/python.exe and the test suite runs from v2/ with
`.venv/Scripts/python.exe -m pytest -q`.

WHAT TO REVIEW

1. Design revision 13, in docs/plans/2026-11-04-s3-measurement-design.md:
   * section 2.4's new normative **item 7** (the six-quantity geometry rule table, the span-rule
     paragraph, and the "What item 7 does not settle" paragraph),
   * the two new entries, **items 5 and 6**, in the running "section 12 amendment item" numbered
     list inside section 13 (search for "The running section 12 amendment-item list"),
   * the **Revision 13** block in section 13 and the revision 13 paragraph in the header.

2. The implementation it makes normative: v2/locfinder/measure/exact.py, with
   v2/tests/test_exact_geometry.py (40 fixtures) and v2/scripts/mutate_exact_geometry.py
   (22 mutations, reported all caught).

3. The two supersession claims now recorded in docs/plans/2026-11-11-step4-comparator-plan.md,
   in the block beginning "Two rows of this table were superseded by building it".

4. The T0 re-run: v2/scripts/t0_attachment_pilot.py, v2/scripts/compare_t0_artifacts.py,
   v2/scripts/explain_adoption_diff.py and v2/scripts/render_t0_results.py, plus the artifact
   docs/experiments/t0-attachment-pilot.json and the write-up section "Re-run against design
   revision 13's exact primitives" in docs/experiments/t0-attachment-pilot.md. Commits caacf60
   (revision 13), df38f99 (the behaviour-preserving refactor) and 7e603cf (the adoption).

THE NUMBERS NOW CLAIMED, so you can check them rather than re-derive what they should be. Over
844,685 points and 36,555,718 per-segment positions, every point of five sets including two
censuses, each measured under both arithmetics: conventions A and D change nothing anywhere;
`C_exact` differs from `C` on 2 of the 512,633 structure centroids; underneath, 2,142,080 residuals
differ by at most 2.397e-10 m, 16,459,230 arclengths by at most 7.276e-12 m, 1,333,808 parameters
differ, 42 positions move by at most 4.657e-10 m, and zero segments flip between a vertex and an
interior point. The mechanism claimed for the 2 points: two adjacent segments of one record whose
own minima are 2.89e-11 m apart, where the float residual on the interior one carries a 1.01e-10 m
error -- larger than the gap -- so the two segments are ordered the wrong way round, and the
retained candidate moves 3.56e-5 m (36 um). I also claim those two figures corroborate each other
because (3.56e-5)**2 / (2 * 21.97) = 2.9e-11 m.

THE CLAIMS I MOST WANT ATTACKED. Each of these is a claim I have made in a committed artifact.
Treat the list as a starting point, not a boundary.

A. **That section 2.4 item 7 is implemented by exact.py.** Go row by row. Does the normative text
   claim anything the code does not do, or leave anything the code decides unstated? Is any row
   ambiguous enough that two conforming implementations could differ? Does item 7 contradict
   anything else in sections 2.1-2.6, section 9's wire contract, or section 12?

B. **That there are no exact rational prefix arclengths**, so the step 4 plan's original same-edge
   rule ("the subtraction is performed on the exact rational prefixes before rounding") is not
   implementable. I claim a prefix arclength is a sum of square roots of rationals, not rational in
   general and not representable as a Fraction. Is that right, and is the conclusion right? Could
   the intended rule be implemented some other way I dismissed too fast -- for instance by
   comparing or subtracting exactly in an algebraic representation, or by a rule that never needs
   the prefix as a number?

C. **That one correct rounding cannot be worse than two.** I argue one correct rounding of an exact
   value is by definition the nearest representable number to it, so the one-rounding composition
   cannot be farther off. Check the argument and check whether exact.py's composition really is one
   rounding everywhere it claims to be -- including scaled_segment_length, prefix_arclength and
   same_edge_fraction, where fsum sums already-rounded terms.

D. **That the T0 adoption comparison measures what it claims.** The run reports, over every point
   of five sets including two censuses, that switching to revision 13's primitives changes no
   candidate set under conventions A and D and under the relabelled C_exact, while moving
   intermediate numbers by at most about 2.4e-10 m. Attack the measurement, not just the number:
   * `coarse_occurrence` drops the interior parameter before comparing occurrence labels. What real
     change does that hide?
   * `positions_differ` uses POSITION_TOL_M = 1e-6 m, which is about four orders of magnitude
     larger than the differences observed. Is "places unchanged" therefore near-vacuous, and is the
     `raw` block an adequate substitute?
   * `adoption_sentinel` uses only pass 30's two witnesses. Is that enough to establish the exact
     path is live, and what would a stronger sentinel be?
   * `adoption_stats` calls `measure_point` twice and zips the two raw lists element-wise. Is the
     window guaranteed identical, and is the per-position correspondence guaranteed?
   * Is C under exact arithmetic correctly described as a *different rule* rather than the same rule
     computed better? Is A correctly described as the *same* rule? Could the band predicate's being
     a binary64 comparison of a correctly-rounded residual make A a third thing, neither A nor B?
   * Is a zero count here evidence of anything, given that convention A's 0.01 m band is seven to
     eight orders of magnitude wider than the arithmetic's effect? State what the measurement does
     and does not license.
   * I claim the W2/W3 endpoint-flip mechanism occurred **zero** times in 36.5 million real
     positions while being demonstrably live in the sentinel. Is the counter that reports that zero
     actually capable of detecting the mechanism on real data, or does its per-segment,
     like-with-like comparison exclude the very case it is meant to count?
   * `explain_adoption_diff.py` duplicates six lines of the pilot's graph preparation and guards
     the copy with an assertion on the design record count. Is that guard sufficient to establish
     that the script describes the measured run, or can the two preparations diverge while
     agreeing on that count?

E. **That the refactor was behaviour preserving.** compare_t0_artifacts.py strips a list of paths it
   calls volatile. Does that list hide a real change? Is exact-float-equality comparison of every
   other leaf actually what happens, including inside lists and nested dicts?

F. **That the lengths cache cannot change an answer.** prefix_arclength now takes an optional
   `lengths`. Is the equivalence test adequate, and is there an input where passing the cache
   differs from recomputing?

G. **The mutation harness.** 22 mutations reported all caught. Are any of them equivalent mutants
   (so "caught" is luck or impossible), and what rule in exact.py has NO mutation attacking it?
   Three mutations were retired as provably equivalent or dead; check those retirement arguments,
   which are in comments in the harness.

HOW TO REPORT

For each finding: a severity (High / Medium / Low), the claim it refutes quoted from the artifact, a
**runnable** reproducer, and the numbers it produces. Put reproducers under
docs/research/39-codex-review-pass38-counterexamples/ as standalone scripts that run with
`v2/.venv/Scripts/python.exe -B <script>` from the repository root, plus a REPORT.md.

If a claim survives, say so explicitly and say what you ran to establish that -- a survived claim
with evidence is as useful to me as a defect.
