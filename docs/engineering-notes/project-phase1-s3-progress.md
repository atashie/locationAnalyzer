---
name: project-phase1-s3-progress
description: "S3 resume point as of 2026-11-14: what is done, the ordered queue of what comes next, what decisions the owner owes, and the constraints that live nowhere else"
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
| the restricted-route flag | **done** `5e5118f` — `published-v3`, optional third plane | **built, never rendered** |
| the destination the time was measured to | **done** `4685158`, repaired after passes 49–53 — `published-v4`, optional fourth plane + side table, licence texts and provenance check | **built, never rendered** |
| which criterion was unknown, and why | **done** — `explainAt`, which computes it per layer per cell | **built, never rendered** |

**All three are now closed in logic and shown to nobody.** The card is built — `explainAt` in
`worker.js`, the words in `card.js`, the surface in `index.html` — and **no browser has ever
rendered the page**, because none has been reachable from any session that built it. So the right
description of this row is not "unbuilt" and not "done": it is *implemented and unobserved*.

Codex pass 54 put it as "the mitigation exists in code; its effectiveness remains unobserved", and
judged the five review passes that followed the card "not worth completing before anyone opened
it". **Corrected 2026-11-15**; this table said "the per-criterion card is unbuilt" for a day after
it was built, at the top of the document a resuming session reads first.

## In flight right now, and what comes next

**Codex pass 54 is running, and the owner asked for it as the FINAL round of this chain.**
Prompt at `docs/research/55-codex-review-pass54-prompt.md`, committed before the run. It is
deliberately **not** a sixth defect hunt on the repairs: it is a fitness review in the shape of
pass 25, asking whether this body of work is proportionate to the product's purpose and what the
highest-value next action is, with a last defect sweep attached rather than leading. Pass 25 is
the precedent and the most valuable pass in this project's history — it is the one that produced
§0's ordering rule after judging eleven passes of apparatus "disproportionate and elaborating the
wrong axis".

**Codex pass 53 is fully integrated**, all eleven findings — see §2c of the queue for what each
was. The chain stands at 49, 50, 51, 52, 53, every one of which found more in the previous pass's
repairs than in the work being repaired.

**After pass 54, the chain is closed by the owner's instruction.** A resuming session should not
start a pass 55 on its repairs without being asked: the standing Codex cadence is "after every
major plan and every analysed result set", and the owner has now named the end of this particular
sequence. What comes next is queue item 3 — the browser — unless pass 54 says otherwise.

**The sheet gained three columns across these two passes**, so an owner holding a filled copy must
run `python scripts/migrate_audit_sheet.py <their copy>` rather than regenerating: `walked`
(did you make this journey — asked rather than inferred), `destination_used_lon`/`_lat` (where you
ended up, because a name does not identify a shop) and `route_identified`. The migration is
lossless by construction and says so after reading its own output back.

### A judgement the owner should make, and the reason to make it now

**Five consecutive adversarial passes have each found more in the previous pass's repairs than in
the work being repaired** — 49 → 50 → 51 → 52 → 53, and the chain is not converging. Pass 53's
first claim was "this time I enumerated the class rather than the instances" and it failed twice in
one pass, on both sides of the codebase.

That is the pattern **Codex pass 25 named about a different surface** and the reason §0 orders work
by *product risk retired*: eleven passes and 11,000 lines of apparatus had gone into an instrument
while the decisions S3 exists to make were unstarted. The same question now applies here. Since the
card's logic landed, **every pass has retired defect risk in code no household has seen, on a page
that has never been rendered in a browser.** The three owed disclosures are closed in logic and
shown to nobody.

So the honest statement of where this stands: the card is as well guarded as anything in the
repository and **less verified than the simplest thing a person could do with it**, which is open
the page. Continuing the chain is defensible; so is stopping it and spending the next hour on a
browser. That choice is the owner's, and it should be made deliberately rather than by momentum.
See queue item 3, which is now the highest-value unblocked item.

Nothing else in flight. **Codex passes 49 and 50 are both integrated.** Reports at
`docs/research/50-codex-review-pass49-counterexamples/REPORT.md` and
`docs/research/51-codex-review-pass50-counterexamples/REPORT.md`.

**The next planned step is the per-criterion card, planned in
`docs/plans/2026-11-14-per-criterion-card-plan.md`.** Read that before starting anything.

Its one load-bearing finding, so a resuming session does not have to rediscover it: the third
owed disclosure is not merely unshown, it is **not computed as an answer**. `handleCompute`
evaluates `outcomeOf` per layer per cell, folds the results into `anyFail`/`anyUnknown`, writes one
combined verdict and discards the detail. None of the worker's six message types can say which
criterion was unknown at a cell or why. So the card is one new message, `explainAt`, plus one
surface — and that single message is what unblocks all three disclosures at once, because they are
the same question asked of one cell.

This was chosen over another Codex pass on the pass 50 repairs, deliberately and against the pull
of the evidence: passes 49 and 50 both found more in the repairs than in the work they repaired,
which is a real argument for a pass 51. But §0 orders by **product risk retired, not defect
severity**, and those findings are defect risk in code no household has ever seen. The pass comes
after the card, per the standing cadence of running Codex once a major plan is written and once
its results land.

Pass 49 (11 findings, 3 High) reviewed the destination publication; pass 50 (14 findings, 4 High)
reviewed pass 49's **repairs** and found more in them than pass 49 had found in the original work.
The live corrections:

* **A release blocker nothing could see.** 85 bare `NaN` tokens in the published side table, so
  `JSON.parse` threw and the page could not display a destination. Every conformance check built
  its own fixture; none loaded the artifact. Fixed at the generator, the serialiser
  (`allow_nan=False`) and with a check that loads the shipped bundle.
* **The two-directional invariant does not prove provenance** — it compares answer-presence masks
  and never reads a value. And `verify_provenance`, which replaced it for that purpose, is an
  output-**value** consistency check, not a proof of source-cell identity: two source cells
  holding the same value are indistinguishable to it. 330,502 of 330,502 cells agree.
* **The surface fingerprint was being stamped after comparing masks, not values.** 256,276 cells
  can have 60 s added while the journey mask holds. The gate now compares the recomputed per-cell
  seconds exactly, after the `float32` cast the surface was written through.
* **A licence identifier is not a licence**, and only Apache §4(a) is discharged. The bundle
  records `apache_records_are_cleared_for_redistribution: false` and says why: §4(b) needs a
  notice on the modified file, §4(c) needs an inventory of upstream notices, §4(d) needs the real
  Foursquare `NOTICE`, which is behind a gated repository.
* **The publication allowlist covered two entrances of four** — not the table root, not the
  licence block, not the types inside permitted fields, so a website could ship inside `brand`.
* **The conformance oracle was the object under test.** The worker was handed `group.dest_tables`
  and the expectation was read back out of it, so a worker that rewrote every `gers_id` in place
  agreed with itself. Snapshot frozen before init now.
* **Coercion before validation:** `msg.row | 0` wrapped 4294967296 to 0 and answered confidently.
* **The lifecycle fix covered one reader of three.** `verdicts` and `mask` had the same hole, and
  a failed compute left a half-written plane wearing the previous sequence number.
* **The destination cost is 20.6% of the bundle, not 4.1%** — two grids mixed, the cheaper
  option's total as denominator, the side table omitted.
* **Two of my own controls confirmed on the wrong cause**, and four of my five new ledger
  instances were overstated. Both are recorded in the ledger rather than quietly fixed.

## Verified state after the pass 50 integration

**1,543 tests, 1,519 passed, 24 skipped, 0 failures. 87 browser conformance checks, 33 card
checks. 69 of 69 worker mutations, 29 of 29 card mutations, 30 of 30 admissibility mutations, 9 of
9 migration mutations — 0 inert, 0 misplaced, 0 errored anywhere.**

Three of the four mutation runners now also **report where each mutation landed** and fail the run
when it is not the function the mutation names, because a mutation that edits the wrong function is
caught by a check about something else. That happened twice; both gates are controlled by
deliberately mis-declaring a function and confirming the run fails.

Earlier figures, kept for the trail: at the end of pass 50 it was 1,460 tests, 79 conformance
checks and 43 of 43 mutations; at the end of pass 52, 1,500 tests and 87 checks. `byteswap_control.mjs` confirms that a **recorded expectation**, not a
structural check, is what catches a big-endian destination plane — and refuses to confirm anything
unless its own mutation applied, the baseline matches the recorded ordinals, and the mutated
ordinals are exactly their byte-swaps.

One guard is deliberately **unguarded** and says so in `mutate_worker.mjs`: resetting
`lastInCount` at init is now unreachable through the message protocol, because the reader that
would expose a stale value refuses until a compute has run. A mutation removing it survives every
check, so it is listed as absent rather than left to look like an oversight.

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
* **Whether the Apache-licensed destination names may be published at all yet.** New with pass
  50. 35 of the 468 published place records are Apache-2.0, which in Overture means
  Foursquare-sourced, and only §4(a) of that licence is discharged: §4(b) wants a notice on the
  modified file, §4(c) wants an inventory of upstream notices nobody has made, and §4(d) wants the
  real Foursquare `NOTICE`, which sits behind a gated Hugging Face repository that answers HTTP
  401. The build records `apache_records_are_cleared_for_redistribution: false` rather than
  implying clearance. Three ways out, all the owner's: obtain the real `NOTICE`; drop the 35
  Apache records and publish only the CDLA and CC0 ones; or publish as-is on the owner's own
  judgement. Nothing is blocked internally — this matters when the bundle leaves this machine.
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

[[feedback-verify-the-shape-of-the-risk]] now holds **42 instances**. From pass 51: a check on
the answer is not a check on the explanation of the answer; one field cannot answer two questions;
a rule borrowed from a different question changes meaning on arrival. From pass 52: **closing the
instances a reviewer supplies is not closing the class** (both its High findings); a regression
test written beside a fix can lock in the adjacent bug; and a schema change is not finished until
the copies already in the field can move. Plus recurrences **inside the checks written for them**
— instance 32 in a digest buffer, instance 30 in a mutation anchor, and the oldest one of all,
a fixture set holding a dimension constant. It is the most useful document
in the repository for avoiding repeats. The ones currently live:

* **29** — a fixture is a model of the artifact, and passing on the model does not establish that
  the **particular shipped artifact** loads. For every artifact a consumer loads, one check must
  load it the way the consumer does.
* **30** — a positive control that can pass on the **wrong cause** is not a control. Require the
  mutation to have applied, the baseline to match a **recorded** expectation, and the effect to be
  the specific predicted one.
* **31** — compare every field you claim to check; and give **both** halves of a two-sided
  invariant a refusal case.
* **32** — **allocation is not evaluation.** A default-initialised value indistinguishable from a
  real answer turns "I have not been asked yet" into a confident reply. This one generalised
  correctly and found two more readers with the same hole.
* **33** — a label is not the thing it names, and silence is not confirmation. Requiring a
  declaration establishes a *declared* fact, not a verified one.
* **34** — **the oracle must not be reachable by the code under test.** Snapshot and freeze the
  expectation before that code can touch it.
* **35** — **coercion is not validation.** A coercion that maps invalid input onto a valid value
  destroys the evidence that it was invalid.
* **36** — an allowlist is a claim about **every** entrance. Two of four is not an allowlist.

And the repeat that will not go away: **a measurement's output must be in the units of the
question** — mask agreement is not value agreement, and a share is not a share until its
denominator is named.

## The queue after the card, ordered by product risk retired

**Laid out 2026-11-14. Nothing below is started.** The order is §0's rule applied to what is left,
not the order these became known. Each item says what risk it retires, because that is what
justifies its position.

**Running in parallel, and only the owner can do it: one repeat walk of `band15min_pass-03`**, from
a recorded door inside cell (286, 129), to the selected destination, timed, with the approach
noted. The E3 record holds no admissible observation, so this is still the cheapest unblock in the
project — and since 2026-11-14 the sheet refuses a row that omits any of those four things, so the
next walk is scorable the moment it is recorded rather than months later by argument.

### 0. Make the walked record admissible by construction — **DONE 2026-11-14**

The sheet is not the gap. `triangle-grocery-walk-chapelhill.csv` **already carries** `start_lon`,
`start_lat`, `destination_used`, `destination_qualifies`, `destination_open`, `route_usable` and
`walked_seconds`. What is missing is anything that **refuses a row that leaves them blank**, and
there is no ingestion path from the sheet to the scorer at all — only
`audit_recommendations.py` and `compare_rebuild_to_stored.py` read those columns.

And the scorer cannot represent the problem. `Journey` in `locfinder/measure/e3.py` has three
fields — `label`, `reported_s`, `observed_s` — and therefore **two** states: `observed_s is None`
means not walked, anything else means walked and scorable. Pass 47's verdict on the one journey was
a *third* thing, "walked but not admissible", and it was reached by a human reading the audit README
rather than by the instrument. **A binary where a third state is load-bearing** — the same shape as
the three-outcome algebra and as ledger 32.

**Delivered.** `locfinder/measure/admissible.py` is the decision report's own table in code —
`Admissibility` with three values, a `WalkedRecord` whose every observation field defaults to
"the record does not say", and a predicate that collects **every** reason rather than the first.
`scripts/score_walked_audit.py` is the ingestion path, reading the published whole minute as what
the product said rather than the model's float. `E3Result` gained
`inadmissible`, `without_a_published_time` and `no_admissible_observation`, so an outcome cannot be
reported without the refusals: UNVERIFIED on an empty set and UNVERIFIED after refusing a walk are
different claims about the world, and the metro sheet and the Chapel Hill sheet now return
different answers for that reason. `E3Outcome` still has two values — a third would be a design
amendment.

The sheets gained `duration_timed` and `route_followed`, which is what moved the record from prose
to columns. Run on the Chapel Hill sheet, the one walked row is refused on all four counts and the
reasons are the decision report's four rows. 31 tests, and
`scripts/mutate_admissible.py` reverts each of the ten rules and reports which test catches it —
**10 caught, 0 inert.** Every refusal test has the positive control beside it: the same record,
repaired, is admissible and **FAILS**, because a refusal test that cannot distinguish a working
predicate from one refusing everything proves nothing.

One defect found while doing it: `GridSpec.cell_for_lonlat` **raises** on a non-finite or
unprojectable coordinate, by design, so one mistyped cell in a hand-filled sheet would have taken
down the ingestion of every other row. Refused per row now, with its own reason.

### 1. The card — **DONE 2026-11-14, all six steps including the Codex pass**

`docs/plans/2026-11-14-per-criterion-card-plan.md` carries what was built and what is still not
verified. **The interface gap on all three owed disclosures is closed in logic.** It is not closed
in anything anyone has looked at: no browser was reachable from the session that built it.

`explainAt(row, col)` reports, per enabled layer, the outcome, the status as code and name, the
minute or `null`, whether that minute is a lower bound, the threshold, the horizon, the route flag
or `null`, and the destination set. It answers for excluded and unknown cells — why a cell is
excluded is the question — and it recomputes rather than storing a plane, because a stored plane
is a second thing that can drift from the verdict it explains. The handler costs 0.0002 ms median
on the shipped bundle, so recomputing is settled by measurement.

The words live in `card.js` with no DOM, and so does the request lifecycle, because **both of the
card's presentation defects were in plumbing that could not be tested from a browser-less
session**. `card_selftest.mjs` drives both: 27 checks, including real worker replies from the
two-layer fixtures and 40,000 from the shipped bundle.

**Guards: 79 browser conformance checks, 27 card checks, 60 of 60 worker mutations and 21 of 21
card mutations caught, 0 inert.**

### 2. Codex pass 51 — **INTEGRATED 2026-11-14. Twelve findings, three High.**

Report at `docs/research/52-codex-review-pass51-card/REPORT.md`, prompt at
`docs/research/52-codex-review-pass51-prompt.md`. **Four of the six claims the prompt put up failed
or were narrowed, and both suspicions it was asked to settle came back as defects.** Every finding
was reproduced before being fixed.

The three High:

* **Outcomes do not authenticate the explanation beside them** (B2). The fold check and the
  recorded per-layer outcomes bound the *outcome*. Everything reported with it was checked for
  **shape** only — a flag being 0 or 1, a value not being 255 — so five corruptions each passed
  all 79 conformance checks and all 16 card checks: a minute of 42, an inverted route flag, a
  forced INCLUDED headline, invented place names, a horizon of 1. Every field is now compared with
  the fixture byte it reports, against planes read separately from the ones the worker is handed.
  All five are kept as controls.
* **A documented walk with no duration vanished into "planned, not walked"** (A1).
  `WalkedRecord.walked` was `walked_seconds is not None`, one expression asked to mean both *a
  walk happened* and *we have its duration*. A row dated, with a door, a destination and a route
  recorded, and no usable duration, returned `walked=0, planned=1`, nothing inadmissible. Nine
  observation columns are evidence of a walk now, and a walk with no duration is refused with the
  evidence named.
* **The card kept an obsolete answer beside a recomputed raster, indefinitely** (B1). Nothing
  invalidated it when the criteria changed, and the reply check looked only at `reqId`. A cell
  shown PASS at a 15-minute limit kept saying PASS, "your limit 15 min", after the limit moved to
  5 and the raster excluded it. Freshness has three dimensions — request, pointer generation
  (B5), and which compute the screen shows — and all three are checked now.

And the mediums worth carrying forward:

* **A name is not an identity** (A2). The metro sheet holds two different `Food Lion`s 11 km
  apart, and one journey's own alternatives list is *also* `Food Lion`. The sheet gained an
  arrival coordinate; the permitted set is now the selected place plus the others on its node,
  which also stops a **permitted** alternative being refused.
* **Prose cannot be checked** (A3). "I cannot remember whether I used the private track or avoided
  it" is non-blank and satisfied a non-blank test, so `route_identified` is the structured half.
* **"At least 11 min" overstated a rounded-up bound** (B3). The byte is `ceil(bound/60)`, so a
  byte of 11 means the bound is in `(600, 660]` s and a 630-second journey is compatible with it
  while taking less than 11 minutes. The card says "more than 10 min".
* **Suppression masqueraded as non-disclosure** (B4). `destinationAt`'s rule, copied into
  `explainAt` without re-deriving it, made the card say a layer "does not say which destination"
  about a layer whose plane names one. Destinations are disclosed per criterion now, whatever the
  combined verdict.
* **There was no multi-criterion rendering test at all** (B6) — not even hand-built, so
  `criteria.slice(0, 1)` passed all 16 checks. There are now three, one driving real worker
  replies from the two-layer fixtures.
* **The 0.366-row Mercator figure is the idealised one** (B7). MapLibre also quantises corner
  positions; Codex's reading of the pinned v5.24.0 source puts the combined maximum at about 0.388
  rows (~37.8 m) plus ~0.023 columns. Recorded as its figure, not reproduced here.
* **The benchmark did not support its conclusion** (B8). It establishes that the handler is not
  the cost, which settles the caching question; it does not establish an end-to-end pointer-move
  budget, and a whole-raster compute is the wrong denominator for one.
* **The digest buffer was zero-filled and zero is the PASS code** (B9), so a cell never explained
  already held a plausible answer — Codex skipped real-window cell 5166 and all 79 checks passed.
  Ledger instance 32, inside the check written to prove a plane was read.

**Two of my own guards confirmed on the wrong cause.** One new mutation anchored on text
`destinationAt` also carries, so it mutated the wrong handler and reported CAUGHT while the guard
under test was never touched; the pre-existing one used a bare positional anchor for the same text
and would have retargeted silently the next time a handler was added above it.

### 2b. Codex pass 52 — **INTEGRATED 2026-11-14. Ten findings, two High.**

Report at `docs/research/53-codex-review-pass52-repairs/REPORT.md`, prompt at
`docs/research/53-codex-review-pass52-prompt.md`. **Five of the six claims failed.** The fourth
consecutive pass to find more in the previous pass's repairs than in the work being repaired, and
both High findings are the same shape: **closing the instances a reviewer supplies is not closing
the class.**

* **Five MORE corruptions of `explainAt` survived** (F1). Three were response-envelope fields no
  assertion mentioned: `seq: -1` (after which the page rejects every explanation it receives),
  `reqId: 0` (every request rejected), `row: 0, col: 0` (every answer labelled as another cell's).
  Two were criterion-index substitutions invisible to every fixture, because **every multi-layer
  group gave its layers the same threshold and the same horizon** — built before `explainAt`
  existed to read those arrays, and nothing re-asked whether they still discriminated. There is
  now a three-layer group with three thresholds and three horizons, and it catches both.
* **The walk-evidence list left out the two columns that most mean a walk happened** (F2) —
  `duration_timed` and `route_identified` — so a row whose only entry was one of those vanished
  exactly as before the repair. And it read `witness_within_15min=untested`, which the README
  tells the owner to write when they did not try, as affirmative evidence that somebody walked.
* **Proximity is not identity either** (F3). The 600 m envelope round the *selected* place accepts
  a different shop of the same name 270 m away on another node, and refuses a legitimate door
  measured from the wrong member. The arrival is now matched against the coordinate of **the
  member whose name was recorded**, inside 200 m, and `recover_audit_destinations.py` writes each
  alternative's own coordinate beside its name.
* **The card rendered a cell the pointer had already left** (F4) — and my regression test for
  B5 asserted that it should, as a precondition. Once that was fixed, the pointer-generation
  mechanism B5 introduced became redundant and both of its mutations survived, so it is removed.
* **A worker error wedged the card permanently** (F5): the request was never settled, so every
  later hover queued behind a reply that was never coming, and leaving the map, resetting and
  further computes all failed to recover it.
* **Three rendering corruptions still passed all 27 card checks** (F6) — the outcome text forced
  to `PASS`, every threshold forced to 15, every place after the first dropped. Each block's
  outcome, limit, bound, cause, disclosure and whole place set is compared with its own reply now.
* **A schema change with no migration** (F7). The scorer refused an owner's filled sheet and told
  them to **regenerate**, which writes every owner column blank. `scripts/migrate_audit_sheet.py`
  adds missing columns in place, keeps every value and every column the owner added, and reads the
  result back to prove nothing recorded changed. Nine tests.
* **`autoBench` could never finish** (F8, inherited and older than this work): it waited for the
  rolling timing window to grow, and the window is capped at 20. It awaits its own compute's
  sequence number now.
* **An impossible latitude manufactured agreement** (F9): `395.910405` wrapped through 360° in
  the haversine and returned 1.6e-9 m, so a typo read as "you arrived exactly at the shop".
* **The benchmark conclusion was still too broad** (F10): it establishes that recomputing is cheap
  for this one-layer bundle on this runtime, not that the handler can never be the cost.

### 2c. Codex pass 53 — **INTEGRATED 2026-11-15. Eleven findings, two High, all fixed.**

Report at `docs/research/54-codex-review-pass53-repairs/REPORT.md`. **Five of six claims failed.**
The owner asked for the integration starting with F5, and that is the order it was done in. All
eleven are fixed and guarded; what each one was, and what closed it:

1. **F5 (Medium, but live) — same-name members collapse and overwrite each other.**
   `by_name = {p.name: p for p in permitted}` in `admissible.py` keeps the LAST member for a name,
   so a coordinate-less alternative overwrites the selected destination. Confirmed on
   `band10min_fail-02` and `band15min_fail-02`. The fix is to keep every member for a name and
   match the arrival against **any eligible** member, and to carry a stable identifier (the side
   table has `gers_id`) rather than making the name unique.
2. **F1 (High) — three more worker corruptions pass all 87 worker checks and all 29 card checks.**
   Three distinct causes, all mine: my reply enumeration **omitted three envelope fields**
   (`outside`, `invalidCoordinates`, `notComputed`), and adding `outside: true` to a successful
   reply passed all 87; the `seq` assertion compares against a **constant** because every
   exhaustive case computes with `seq: 1`; and **the three-layer group I added for F1 last pass
   carries no destination or flag planes**, so `destTables[enabledIndex - 1]` makes criterion B
   name A's shops undetected, and layer B is never enabled alone.
3. **F2 (High) — the sheet has 18 owner columns and the predicate reads 15.** `door_offset_m`,
   `unresolved` and `notes` are omitted, and the README explicitly asks the owner to measure
   `door_offset_m`. The deeper point is that **the inference is unsound in both directions**: the
   README's step 2 has the owner record a start door *before* walking, so a prepared-then-abandoned
   sheet reads as a refused walk. Extending the list again cannot fix that — it needs an explicit
   "did a walk happen" field, which is what the fix should add. A sole `duration_timed="not timed"`
   also vanishes through `tri_state` rather than being refused as malformed.
4. **F3 and F4 (Medium) — the migration can lose an observation after all.** A duplicate header
   means `csv.DictReader` keeps only the last value, and my read-back snapshot is built **after**
   the loss, so it prints "none changed". Plus three destructive paths: the default output silently
   overwrites a filled `.migrated.csv`, `--in-place` silently overwrites an existing
   `.before-migration`, and a surplus-field row raises **after** the target is truncated. Duplicate
   `journey_id`s also make the comparison key ambiguous.
5. **F7 (Medium) — the card suite accepts an affirmative headline on every excluded cell.**
   Replacing `VERDICT_TEXT[msg.verdictName]` with `VERDICT_TEXT.INCLUDED` passes all 29 checks, so
   an excluded cell reads "Every criterion you have on is satisfied here." A second mutation copied
   other criteria's destination text into unnamed blocks and also passed: checking that expected
   content is **present** does not check that foreign content is **absent**.
6. **F8 and F9 (Medium) — the card's freshness is still incomplete.** Already-displayed stale
   content stays visible when the pointer moves to a new cell (the guard stops a stale reply
   rendering; it does not invalidate what is already on screen), and a **native**
   `worker.onerror` still wedges the inspector because only `type: "error"` messages reach
   `cardFailed`.
7. **F6 (Medium) — 200 m still does not establish identity**: a different shop of the same name
   135 m away passes. My justification cited the 70.7 m centre-to-door bound, which is about the
   **origin cell**, not destination geometry. The honest fix is to treat the radius as plausibility
   evidence and carry identities.
8. **F10 and F11 (Low)** — two paint waiters for one sequence overwrite each other, so one can time
   out after its sequence painted; `autoBench` prints "done, 20 samples" after stopping at change
   one; and `bench_explain.mjs`'s header still calls the figure a LOWER BOUND while its own
   conclusion denies that.

**Two suspicions settled in my favour**, recorded because most are not: the single `explainSentAt`
timestamp measures the right interval (the old reply's timing is recorded before `post(send)`
overwrites it), and removing `pointerGen` was reasonable for the current contract.

### 3. Where the published raster actually lands in the browser

MapLibre places the raster in Web Mercator while the published rows are linear in latitude, and
**nothing has measured the result**. If a household reads a cell that is not the cell the answer was
computed for, every disclosure above it is attached to the wrong place — which makes this a
wrong-answer risk in the thing actually shown, not a defect in unseen code. Cheap, and it needs no
new data: compare the cell the page resolves at known coordinates against
`GridSpec.cell_for_lonlat`, at the footprint corners and far from the origin, because
[[feedback-a-relative-invariant-cannot-see-an-absence]] applies here too.

### 4. Phone decode latency

Needs a device, so the owner's. Still listed as open on step 6.

### 5. Step 7's geocoding half

Whether a household's address resolves to the right cell. Not started. The destination-screening
half ran on 2026-11-13.

### 6. Step 4's remaining phases — the long one

The T0 re-run as a labelled refactor-then-adopt, then **4a.2** (a certified cost comparison as a
diagnostic), **4b.0** (the search-semantics spike, because §2.4's whole-journey tie rule is not
implementable by a scalar-label search), **4b** (T3 as a development comparator) and **4c** (T0
stage 3). 4c is what finally makes verdict impact reachable, and it has been explicitly unknown
since step 3.

### Still blocked on an owner decision, not on work

The grocery definition changes every published number, so items that depend on destination
eligibility cannot be closed before it. The Apache question blocks publication off this machine and
nothing internal.
