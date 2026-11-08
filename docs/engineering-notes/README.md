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
- [`feedback-a-published-page-must-name-its-source`](feedback-a-published-page-must-name-its-source.md) — A published artifact is the only copy that reaches other machines; if it does not name the repo, branch and path that built it, a later session can reproduce everything and still refuse to edit it
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

## Project state and decisions

- [`project-h2-upper-bound-trap`](project-h2-upper-bound-trap.md) — The shipped travel-time surface is cost-selected, so it is never a valid baseline for a counterfactual that minimises time
- [`project-phase0-progress`](project-phase0-progress.md) — Phase 0 state at the end of 2026-11-03 - engine decisions, what is measured, known gaps, and the Phase 1 stage order after Codex pass 7
- [`project-phase1-s0-complete`](project-phase1-s0-complete.md) — Phase 1 stage S0 (the layer contract) is done and committed as 90074e6 - what it decided, the two measured findings, and what S1 picks up
- [`project-phase1-s1-complete`](project-phase1-s1-complete.md) — Phase 1 stage S1 (the expansion primitive) after Codex pass 9 - roots are partial edges, walk agrees at the median with heavy tails, drive carries a +50 s bias that is not the adapter
- [`project-phase1-s2-progress`](project-phase1-s2-progress.md) — Phase 1 stage S2 COMPLETE - all five tasks done, Codex passes 10-12 absorbed; the headline measurements and the over-correction pattern
- [`project-phase1-s3-design`](project-phase1-s3-design.md) — S3 design is revision 10 - revision 9 was reverted after an hour and the candidate universe is now a DECLARED CONVENTION; T0 measures prevalence on the real graph before any further rule choice; T3 refused four times, nothing sampled
- [`project-v2-rethink-decisions`](project-v2-rethink-decisions.md) — Decisions and status for the ground-up rethink (V2) of the Distance Finder / location-finder product, kicked off 2026-11-03

## Environment and tooling facts

- [`reference-codex-runtime-quirks`](reference-codex-runtime-quirks.md) — How to invoke Codex reliably on this machine - supported models for the ChatGPT account, pass --model explicitly, put long prompts in a file, avoid big Bash heredocs
- [`reference-repo-identity`](reference-repo-identity.md) — This work lives in atashie/locationAnalyzer on master; three other things answer to the name "distance finder" and none of them is it
- [`reference-sibling-repos`](reference-sibling-repos.md) — Paths to sibling repos whose code the V2 rebuild may reuse (CHCCS_geospatial gridded travel times, localUpdates NL-to-spatial-SQL agent)

