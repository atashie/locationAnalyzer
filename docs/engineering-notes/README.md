# Engineering notes

Working notes for this project: decisions taken, methods that failed, and
environment facts worth not rediscovering.

These were accumulated in Claude Code's per-project memory store, which is
machine-local and does not travel with a clone. They are kept here instead, so a
checkout on any machine carries the same context. **Write new notes here, not to
`~/.claude/projects/`.**

Frontmatter is preserved as written, which is why some files carry a `type:` field
and a session id. Treat each as a dated observation, not a standing spec: where a
note disagrees with the code, the code is right and the note needs correcting.

## Who this is for

- [`user-profile`](user-profile.md) — Who the user is - geospatial/hydrology scientist building location-finder tools, wants autonomous agentic work with Codex as adversarial reviewer

## How to work on this (methodology, and what went wrong)

- [`feedback-a-fixture-is-exact-only-where-you-point-it`](feedback-a-fixture-is-exact-only-where-you-point-it.md) — Four reviews defeated the same test suite by varying an axis the fixtures held constant; build the wrong implementation in the test file and name which case kills it
- [`feedback-a-predeclared-gate-must-be-shown-reachable`](feedback-a-predeclared-gate-must-be-shown-reachable.md) — Before predeclaring a PASS/FAIL rule, compute whether the best possible observation passes it at the predeclared sample size; choose n by failure tolerance, not by the zero-event bound
- [`feedback-a-relative-invariant-cannot-see-an-absence`](feedback-a-relative-invariant-cannot-see-an-absence.md) — A relative invariant cannot see an absence, a positional truncation, or a defect only far from the origin; three reviews defeated the same layer this way, and five of my replacement checks rejected correct code
- [`feedback-a-skill-can-subtract`](feedback-a-skill-can-subtract.md) — Writing a skill against a list of observed failures makes everything the list omits invisible - output shape, who decides - and a rule that rewards reporting failures makes fabricated failures profitable
- [`feedback-autonomous-work-style`](feedback-autonomous-work-style.md) — Work iteratively and autonomously, launch subagents freely, pause for user feedback only when absolutely necessary; branch and commit freely but never push
- [`feedback-benchmark-over-point-fixes`](feedback-benchmark-over-point-fixes.md) — When review fixes keep breaking adjacent cases, stop point-fixing and build a graded benchmark with intended answers written down first
- [`feedback-codex-adversarial-review`](feedback-codex-adversarial-review.md) — Use Codex CLI as an adversarial reviewer after every major plan and every analyzed set of results
- [`feedback-computable-property-is-not-the-claim`](feedback-computable-property-is-not-the-claim.md) — When a measurement is hard, the pull is to report the computable property as if it were the product claim; name the gap in the artifact itself
- [`feedback-decide-by-measurement-not-by-argument`](feedback-decide-by-measurement-not-by-argument.md) — Five rounds of choosing a rule by reasoning produced one that lasted an hour; the failure was not the rules but describing an argument as a measurement, and the exit is to measure prevalence on real data before choosing
- [`feedback-experiments-over-priors`](feedback-experiments-over-priors.md) — When a design or architecture question is open, the user wants it settled by a cheap experiment first, then the research record, and only last by our priors
- [`feedback-fix-the-domain-not-the-example`](feedback-fix-the-domain-not-the-example.md) — Three reviews in a row, closing the reviewed defect opened an adjacent one; the exit is an invariant layer over a declared admissible-input domain plus a mutation guard, not more cases
- [`feedback-maps-need-a-basemap`](feedback-maps-need-a-basemap.md) — Every map this user is shown must carry a basemap - roads, political boundaries, place labels - because geometry floating on blank ground cannot be sanity-checked
- [`feedback-match-statistical-machinery-to-the-design`](feedback-match-statistical-machinery-to-the-design.md) — Clustering corrections belong to clustered sampling designs, not to spatially correlated populations sampled independently; check an adjustment's assumptions against how the sample is actually drawn
- [`feedback-provenance-is-not-correctness`](feedback-provenance-is-not-correctness.md) — A figure can carry a perfect provenance label and still be arithmetically wrong - labelling discipline feels like verification and is not, so assert the values themselves
- [`feedback-verify-the-shape-of-the-risk`](feedback-verify-the-shape-of-the-risk.md) — A check that cannot fail the way the change can fail proves nothing, **eight times now**, four of them inside two days - and the eighth was the guard written for the sixth: writing a guard moves the unexamined assumption rather than removing it, and only an adversary trying to get past it has reliably found where it moved to

## Project state and decisions

- [`project-h2-upper-bound-trap`](project-h2-upper-bound-trap.md) — The shipped travel-time surface is cost-selected, so it is never a valid baseline for a counterfactual that minimises time
- [`project-phase0-progress`](project-phase0-progress.md) — Phase 0 state at the end of 2026-11-03 - engine decisions, what is measured, known gaps, and the Phase 1 stage order after Codex pass 7
- [`project-phase1-s0-complete`](project-phase1-s0-complete.md) — Phase 1 stage S0 (the layer contract) is done and committed as 90074e6 - what it decided, the two measured findings, and what S1 picks up
- [`project-phase1-s1-complete`](project-phase1-s1-complete.md) — Phase 1 stage S1 (the expansion primitive) after Codex pass 9 - roots are partial edges, walk agrees at the median with heavy tails, drive carries a +50 s bias that is not the adapter
- [`project-phase1-s2-progress`](project-phase1-s2-progress.md) — Phase 1 stage S2 COMPLETE - all five tasks done, Codex passes 10-12 absorbed; the headline measurements and the over-correction pattern
- [`project-phase1-s3-design`](project-phase1-s3-design.md) — S3 state after plan §0 steps 0, 1 and 2, and **where to resume**: the owner walked a journey, decided on 2026-11-10 to keep the 120 s restricted-walk penalty and monitor the gap rather than calibrate to one observation, and `surface` and `vehicle` went into the extract instead
- [`project-phase1-s3-step2-conditional-estimand`](project-phase1-s3-step2-conditional-estimand.md) — E1c, the conditional false-inclusion rate, is ADOPTED as reported-never-gated with an approximate Clopper-Pearson bound - the claim denominator is ~37 of 500 on the binding frame rather than 417, and a gate would cost ~300-500 claim observations, not 8.2x the survey
- [`project-phase1-s3-soft-way-dependence`](project-phase1-s3-soft-way-dependence.md) — The owner walked a journey and found 25 minutes against a published 13.5. The approach is tagged `access=private`, is correctly penalised at 120 s per edge, and wins anyway because 360 s of penalty over three restricted hops cannot beat a 968 s detour - a calibration finding, not a missing mechanism. 600 s would fix the cell for 1.10% of 15-minute PASS buildings; the owner priced it and kept 120 s, because one journey does not identify the right number
- [`project-phase1-s3-extract-tag-gap`](project-phase1-s3-extract-tag-gap.md) — A rule that reads an OSM tag the extract drops is dead, not conservative: `classify_access` has consulted `vehicle` for drive and bike all along and it was never extracted, and `surface` was absent too, which is why two rounds of measurement could only ask about highway class. Plus the graphml cache that would have made the fix a no-op - and the first version of that guard, which declared a tag set without saying which file it described
- [`project-phase1-s3-stale-walk-raster`](project-phase1-s3-stale-walk-raster.md) — The committed walk raster was built eight hours before `ab01ffa` fixed `symmetrise`, which had been suppressing pedestrian reverse edges: 7,246 cells differ, and none of the 35 audit rows is among them, which is why a verification sampled on those rows passed
- [`project-phase1-s3-audit-destination-recovery`](project-phase1-s3-audit-destination-recovery.md) — The walked-audit sheet gave a start and no destination, and the destination identity was being computed and discarded as `_sources` on every build - now recovered and verified bit-exactly against the committed raster, which immediately shows 7 of 16 Chapel Hill journeys routing to specialty markets that pass the category rule as written
- [`project-phase1-s3-step0-audit-harness`](project-phase1-s3-step0-audit-harness.md) — S3 plan §0 step 0, after Codex pass 26 corrected it - the reconstructed OFF_NETWORK bound is sound and LOSSY not exact (200 m is the floor of those distances, not the ceiling), the first sheet asked for 6.22 hours of walking including a 108-minute *control*, and the unknown-beside-a-pass stratum was dilating OK instead of PASS
- [`project-phase1-s3-encoding-threshold-crossing`](project-phase1-s3-encoding-threshold-crossing.md) — Rounding seconds to whole minutes moves every threshold 30 s more permissive, in one direction only - 8.15% of cells shown as passing 10 minutes do not pass, and ceil makes the encoded verdict exactly the float verdict
- [`project-v2-rethink-decisions`](project-v2-rethink-decisions.md) — Decisions and status for the ground-up rethink (V2) of the Distance Finder / location-finder product, kicked off 2026-11-03

## Environment and tooling facts

- [`reference-text-io-rewrites-line-endings`](reference-text-io-rewrites-line-endings.md) — `Path.read_text` + `Path.write_text` is not a round trip on Windows: it converts an LF file to CRLF, and hashing the decoded text on both sides makes a "restored byte-identically" check that can never fail
- [`reference-codex-runtime-quirks`](reference-codex-runtime-quirks.md) — How to invoke Codex reliably on this machine - supported models for the ChatGPT account, pass --model explicitly, put long prompts in a file, avoid big Bash heredocs
- [`reference-sibling-repos`](reference-sibling-repos.md) — Paths to sibling repos whose code the V2 rebuild may reuse (CHCCS_geospatial gridded travel times, localUpdates NL-to-spatial-SQL agent)
- [`reference-where-secrets-hide`](reference-where-secrets-hide.md) — Where credentials have actually turned up in this repo - .claude/settings.local.json records approved Bash commands verbatim, and four diagnostic scripts printed a live key to stdout - plus the handling pattern that found them

