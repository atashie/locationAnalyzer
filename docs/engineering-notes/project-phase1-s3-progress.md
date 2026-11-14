---
name: project-phase1-s3-progress
description: "S3 resume point as of 2026-11-14: what is done, what is in flight, what decisions the owner owes, and the constraints that live nowhere else"
metadata:
  type: project
---

# S3: where the work stands, 2026-11-14

**This note exists to be the single place a session resumes from.** Everything here is either not
recorded elsewhere, or recorded in several places and worth stating once. The detail lives in the
documents linked from each section; this is the index and the live state.

The ordering principle for S3, from `docs/plans/2026-11-04-s3-execution-plan.md` §0, is **product
risk retired, not defect severity**. Keep that when choosing what to do next.

## State of the three things a household is owed

`docs/s3-decision-report.md` names three disclosures. Their status is the clearest summary of where
S3 is:

| owed | data | interface |
|---|---|---|
| the restricted-route flag | **done** `5e5118f` — `published-v3`, optional third plane | not shown |
| the destination the time was measured to | **done** `4685158`, repaired after pass 49 — `published-v4`, optional fourth plane + side table, licence texts and provenance check | not shown |
| which criterion was unknown, and why | — | **the per-criterion card is unbuilt** |

**So the data gap is closed on two of three and the interface gap is open on all three.** The
decoder counts flagged cells and answers `destinationAt` for one cell; nothing displays either.
The card is now the single remaining blocker for every one of the three, which makes it the next
substantial piece of work rather than one of several.

## In flight right now

Nothing. **Codex pass 49 landed and is integrated**: report at
`docs/research/50-codex-review-pass49-counterexamples/REPORT.md`, 11 findings and 3 High, all 11
reproduced. The next thing to start is the card.

What pass 49 cost, in one line each, because these are the live corrections:

* **A release blocker nothing could see.** The published side table held 85 bare `NaN` tokens, so
  `JSON.parse` threw and the page could not display a destination at all. Every conformance check
  built its own fixture; none loaded the artifact. Fixed at the generator, at the serialiser
  (`allow_nan=False`), and with a check that loads the shipped bundle the way the page does.
* **The two-directional invariant does not prove provenance** — it compares answer-presence masks
  and never reads a value, so exchanging two valid destinations passes it. Replaced for that
  purpose by `verify_provenance`, which reprojects a source-cell index and requires every plane to
  match its source at that index: 330,502 of 330,502 cells, 0 uncovered.
* **A licence identifier is not a licence.** `v2/licences/` now holds the texts and the exporter
  refuses to finish without them.
* **The destination cost is 20.6% of the bundle, not 4.1%** — the old figure mixed two grids, used
  the cheaper option's total as the denominator and left the side table out.
* **Four defects passed all 71 checks** because the harness compared one member of the place set.
* Both of the guards I had already fixed in `b37ed59` were confirmed broken, and pass 49 went
  further on each.

## Verified state at `4685158` + the pass 49 integration

1,440 tests, 1,416 passed, 24 skipped, 0 failures. 75 browser conformance checks pass. 37 of 37
mutations caught. `byteswap_control.mjs` confirms that a **recorded expectation**, not a structural
check, is what catches a big-endian destination plane — and now refuses to confirm anything if its
own mutation did not apply or its baseline is not exactly right.

## Decisions the owner owes

Nothing below should be decided by a session on its own.

* **The grocery definition.** Still the project's biggest open modelling choice.
* **Whether to filter the nine `permanently_closed` records.** On current evidence, **no** — 4 of
  the 9 sit within 150 m of an open destination we already publish, and the Kroger site is an
  operating Harris Teeter on the same node, so they are flagged records and not verified closures.
* **The band choice for §12 item 6** (the suffix-aware band). Item 6 was restated from an
  impossibility to a requirement after pass 42.
* **E1c's interval method**, and **the exact-distance cap**.
* **28 candidate destinations and 4 masked identities** from the audit work.
* **One repeat walk of `band15min_pass-03`**, with a recorded door, the selected destination and a
  timed duration. This is the cheapest unblock in the whole project: it is what would make the E3
  verdict admissible, and the record currently holds **no admissible observation**.
* **Which place on a shared node**, if ever. Deliberately not computed — see
  [[project-phase1-s3-destination-identity]]. Resolving it needs either an invented rule or a finer
  routing target than a node.

## Standing constraints that live nowhere else

Pointers where the reasoning is recorded; the rule itself is here so it cannot be lost.

* **Git:** commit and push to `origin` freely on `v2-rethink`; merges to `master` are the owner's.
  The 2026-11-03 "never push" policy was overridden. See [[feedback-autonomous-work-style]].
* **Codex:** run a pass **very regularly** — after every major plan and every analysed result set.
  Commit the prompt first. Trust order: **experimental results > research > priors.**
* **Listings:** legal and free means only — deep links and official or free APIs, **no scraping**.
* **Google:** query live for validation only. **Do not** persist a per-pair table of Google values
  as a dataset, and **do not** use Google output to calibrate the speed model. Places: store
  `place_id` only.
* **Decision 17:** ODbL publication of OSM-derived work is welcome and contributing back is wanted,
  but **contributions to OSM may not be sourced from Overture or Google**, and contractually
  restricted sources — Google place ids, RentCast, MLS/IDX, portals — must never enter an
  ODbL-published artifact. Recorded with its reasoning in [[project-phase1-s2-progress]].
* **The TripAdvisor API key:** the owner said not to worry about it. Do **not** rotate it and do
  **not** raise it again.
* **A live Google Maps API key** was once pasted into a terminal. Restricting or rotating it was
  advised and is unconfirmed; mention once if it becomes relevant, do not nag.
* **`~/.codex/config.toml`** pins an unusable model (`gpt-5.5`). **Do not edit it unasked** —
  always pass `--model gpt-6.1-sol` instead.
* **Prose:** short, plain, concrete sentences. The owner rejected decorated writing in those words.
  Do not write a sentence whose meaning cannot be checked.

## Runtime constraints that cost real time to rediscover

All recorded in [[reference-codex-runtime-quirks]]; the two that bite most often:

* **Codex cannot start a process on this machine.** Every `exec_command` fails with
  `windows unelevated restricted-token sandbox cannot enforce split writable root sets`, under
  `workspace-write`, with and without `--add-dir`, and with `--ephemeral`. Only
  `--dangerously-bypass-approvals-and-sandbox` executes, and Claude Code's auto mode refuses to
  launch it. So a pass needing Python either runs read-only with the measurements handed over **to
  attack as method**, or the owner launches it with a leading `!`. Handing over a measurement to
  attack turned out to be *better* than reproduction — pass 48 broke the method of two of mine.
* **Write patch scripts with the file-writing tool, not with a shell heredoc.** A quoted heredoc
  still eats one backslash level, which silently corrupted regexes and escapes several times in one
  day. Run them with `python -I`.

## The feedback ledger

[[feedback-verify-the-shape-of-the-risk]] now holds **33 instances**. It is the most useful document
in the repository for avoiding repeats, and the five most recent are the ones currently live:

* **29** — **a fixture is a model of the artifact; passing on the model says nothing about the
  artifact.** 71 checks, none of which loaded the real bundle, so a release blocker was invisible.
  For every artifact a consumer loads, one check must load it the way the consumer does.
* **30** — a positive control that can pass on the **wrong cause** is not a control. Require the
  mutation to have applied, the baseline to be exactly right, and the effect to be the specific
  predicted one.
* **31** — checking one member of a set is not checking the set, and a count is not a set.
* **32** — **allocation is not evaluation.** A default-initialised value that is indistinguishable
  from a real answer turns "I have not been asked yet" into a confident reply.
* **33** — a label is not the thing it names, and silence is not confirmation. Both are "absence is
  not evidence of cleanliness", already written down, and I still wrote the code the other way.

And a repeat, not numbered because the shape is in the file twice already: **when a share is
reported, the next sentence names the denominator.** The destination's cost moved from 4.1% to
20.6% when the denominator was fixed.

## Not started, deliberately

* **Step 7's geocoding half** — whether a household's address resolves to the right cell.
* **S3 4b and 4c** — T3 as a development comparator, about 3+1 days.
* **The audit sheet's E3 fields** — the harness should *refuse* to record a journey without
  `start_lon`, `start_lat` and `destination_used`. Now cheap, because the destination is persisted.
