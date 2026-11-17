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
| the restricted-route flag | **done** `5e5118f` — `published-v3`, optional third plane | built; **rendered 2026-11-15** |
| the destination the time was measured to | **done** `4685158`, repaired after passes 49–53 — `published-v4`, optional fourth plane + side table, licence texts and provenance check | built; **rendered 2026-11-15** |
| which criterion was unknown, and why | **done** — `explainAt`, which computes it per layer per cell | built; **rendered 2026-11-15** |

**All three were drawn in a browser on 2026-11-15, in one card.** Chrome on this machine
loaded the shipped bundle and a hover at (row 100, col 73) produced the cell identity, the
restricted-route warning, and "measured to one of 2 places at this junction: Weaver Street Market,
Inc, Weaver Street Market Administration" — the three owed disclosures, in the words a household
would get. The screenshot is committed at `docs/experiments/s3-11/`. So this row is no longer
*implemented and unobserved*; it is **implemented, observed once, and seen by no household**. One
session by the model that built the page is not a user test.
*(Until 2026-11-15 this said "no browser has ever rendered the page".)*

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
sequence.

**Pass 54 is integrated, and its verdict was that the sequence had become disproportionate:** "the
card was worth building; this sequence of reviews was not worth completing before anyone opened
it." It found **no High defects**, the first time in six passes. Its sharpest point was not that
pass 52 was the stopping boundary but that **the next review of the card should have followed its
first browser use** — a different source of evidence instead of another examination of the same
code. Report at `docs/research/55-codex-review-pass54-fitness/REPORT.md`.

**Queue item 3's first half is done, 2026-11-15**, in the decomposition pass 54 asked for: the
drawn pixel against the published pixel in Python, with the browser left to confirm a predeclared
expectation rather than to discover one. The figures are in item 3 below; the headline is that
**5,801 structures at the threshold the page opens on stand where the painted colour contradicts
their own card**, 2,771 of them painted outside the coloured area although the publication
includes them.

**Item 3 is finished, 2026-11-15. A browser has now drawn this publication.** The owner
installed the extension on this PC; the page was served on loopback and opened in Chrome 157. The
probe ran against its predeclared oracle and **agreed at all eleven points, with zero
disagreements**, and all three sensitive probes showed the live page naming one cell while painting
the colour of the row below. The affine error the probe declares it cannot see is ruled out by a
picture at a colour edge with the one-row alternatives drawn beside it.
`docs/experiments/s3-11-browser-placement.json`, with two screenshots in
`docs/experiments/s3-11/`.

**The first run reported fourteen disagreements and every one was in the instrument**, not the
page — a canvas cannot read back a translucent pixel it wrote, and a `MouseEvent` truncates a
fractional coordinate, so the hover was reading a card for the cell next door. Both had been
stubbed away in the Node self-test, which is ledger instance 48: *a stub must be at least as
hostile as the thing it stands in for*. The self-test now reproduces both and is 13 checks.

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
card's logic landed, **every pass has retired defect risk in code no household has seen.** The
page itself was rendered on 2026-11-15, which took one session and found two defects — both in the
instrument, none in the page. The three owed disclosures have now been read off a screen, and still
by nobody who is trying to find somewhere to live.

So the honest statement of where this stands: the card is as well guarded as anything in the
repository and **less verified than the simplest thing a person could do with it**, which is open
the page. Continuing the chain is defensible; so is stopping it and spending the next hour on a
browser. That choice is the owner's, and it should be made deliberately rather than by momentum.
*(2026-11-15: the page was opened. Item 3 is done and the three disclosures have been seen on a
screen. 2026-11-16: the card's wording was corrected — see the card item. What the card looks like
to somebody who is not the model that built it is still untested, and that is now the
highest-value unblocked item — it needs a person, not a session, and it should now read the
corrected words.)*

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

## Verified state, 2026-11-16

**1,577 tests, 1,553 passed, 24 skipped, 0 failures. 87 browser conformance checks, 44 card
checks, 14 probe checks. 69 of 69 worker mutations, 40 of 40 card mutations, 30 of 30
admissibility mutations, 9 of 9 migration mutations — 0 inert, 0 survived, 0 misplaced, 0
errored anywhere.** Every figure here was re-run on 2026-11-16, not carried forward, and every
browser suite now runs against the **seven-criterion** bundle rather than the one-layer one.

*(The "13 probe checks" this said earlier was worth less than it looked: three of them never
asserted anything. See pass 55 F6 below. It is 14 now, all of them awaited, one of them a control
on the runner itself.)*
*(This block was headed "after the pass 50 integration" and still gave that run's numbers —
1,519 passed, 33 card checks, 29 card mutations — through the browser session and the wording
change. It is the first thing a resuming session reads.)*

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
* **Whether the published minute should become 30-second units.** New with the card's wording
  change, 2026-11-16. `encode_minutes` is `ceil` because the byte is a decision input the worker
  thresholds directly, which makes the displayed number an upper bound overstating by up to 60 s.
  `grid.encode_minutes` named the fix for the day a per-cell number is shown — 30-second units,
  also exact, display error under 30 s, the 120-minute horizon still inside 254, +32% bytes — and
  that day was 2026-11-14. The card now discloses the direction instead, which is the cheap
  answer; the encoding change is a wire-format decision and nothing is blocked internally.
* **28 candidate destinations and 4 masked identities** from the audit work.
* **One repeat walk of `band15min_pass-03`**, with a recorded door, the selected destination and a
  timed duration. This is the cheapest unblock in the whole project: it is what would make the E3
  verdict admissible, and the record currently holds **no admissible observation**. The page was
  read at that cell on 2026-11-16 and shows what the record says it should — 14 min, PASS at a
  15-minute limit, the restricted-route warning, Hill's Family Asian Markets
  ([s3-12](../experiments/s3-12-what-the-page-says-at-the-walked-cell.json)) — so the walk now
  has something specific to confirm or refute.
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
* **Replies to the owner, 2026-11-16:** plain English, bullet points wherever they fit, and
  **always split next steps into two labelled lists** — what the session plans to do and why,
  against what needs the owner's decision, approval or hands. Their words: *"I don't like how we
  are communicating with each other."* See [[feedback-autonomous-work-style]].

## Runtime constraints that cost real time to rediscover

All recorded in [[reference-codex-runtime-quirks]]; the two that bite most often, and one about
the browser:

* **An automated browser session cannot measure anything that completes on an animation frame.**
  Chrome throttles `requestAnimationFrame` to **1 Hz** in a window nothing is displaying, and
  `document.visibilityState` still says `"visible"`, `document.hidden` is `false` and
  `document.hasFocus()` is `true` — occlusion is not the Page Visibility API's hidden state. The
  page's "slider → repaint" stat is taken on a frame, so it read **1002 ms** median over 20
  changes while the worker compute underneath it read 9 ms. The control that settles it: sample
  frame gaps for ten seconds and take a screenshot during the window. They read 1000 ms at rest
  and **17 ms for exactly the frames captured**, then return to 1000. Anything frame-timed needs
  a person with the window on screen. Message round trips and worker-internal timings are
  unaffected, which is why the card's 0.2 ms is trustworthy and the repaint figure is not.
* **Getting a large result out of the page costs nothing if it goes through the access log.**
  `python -m http.server` logs every request line verbatim, so the page can send a 10 KB document
  as a series of GETs with the payload in the query string and `scripts/collect_probe_run.py`
  puts it back together. Encode twice — a slice of a percent-encoded string can cut a `%XX` in
  half. Reading it back through the browser tool instead spends the whole document on context.

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

[[feedback-verify-the-shape-of-the-risk]] now holds **55 instances**. *(This said 42 from pass 52
until 2026-11-16; the count had not been updated for passes 53 and 54, the browser session or the
wording change.)* The three most recent: **47**, closing the instances a reviewer gives you is not
closing the class, for the second time; **48**, a stub must be at least as hostile as the thing it
stands in for; **49**, a tradeoff can stay right while its justification expires — the minute
is `ceil` because "nothing displays it", and since 2026-11-14 the card displays it; **50**,
an index is not a location until it names its grid; **51**, a check on a true neighbouring fact is
not a check on the claim; and **52**, I repaired instance 50 by inventing a location in the same
commit. 49 and 50 were both **corrected by pass 55 for overstatement**, which is the second review
in a row to find that: pass 48 found four of five overstated, pass 55 found two of two. From pass 51:
a check on
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
a **chosen and recorded** door inside the cell whose query coordinate is **lon -79.062476,
lat 35.902334**, to the selected destination, timed, with the approach noted. *(That coordinate is
not a door: it is the centre of the UTM cell the 810.8 s was computed for, and this journey's
`start_lon`/`start_lat` are blank. Recording a real door is the point of the walk -- Codex pass
55, F4, after this note called it a recorded door for a day.)* *(Use the coordinate, not an index. The sheet's `row`/`col`
columns say (286, 129) and those index the **UTM** grid; the published raster has a cell
(286, 129) too, about 400 m away, and it is a different answer entirely — 24 minutes and a FAIL.
In the published raster this door is cell **(282, 126)**, which is what the page's card heading
shows. See [s3-12](../experiments/s3-12-what-the-page-says-at-the-walked-cell.json) and ledger
instance 50.)* The E3 record holds no admissible observation, so this is still the cheapest unblock in the
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
verified. **The interface gap on all three owed disclosures is closed in logic, and on
2026-11-15 the card was drawn in a browser** — `docs/experiments/s3-11-browser-placement.json`,
with the screenshot beside it. No household has seen it.

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

#### The wording, changed 2026-11-16 — pass 54's "cheapest immediate reduction"

Pass 54's one product recommendation, and the only one of its four leftovers that was not a
judgement call about apparatus. The card asserted a fact about the place; it now states a model
result, and says what kind of result.

* **The affirmative headline.** "Every criterion you have on is satisfied here" →
  **"The model estimates this cell meets your limits."**
* **A new line directly under every verdict**, so it qualifies exclusions and unknowns too and
  not only the affirmative one: *"Times are estimates: measured from the centre of this cell, and
  rounded up to the whole minute."* Both halves are claims about this pipeline and both are now
  **checked against the code they describe** — `test_browser_conformance.py` reads the sentence
  out of the running `card.js` and the rounding rule out of the running `encode_minutes`, because
  a check that compares the card against the same string it renders is a tautology.
* **The restricted-route warning moved up**, to the line directly under the time. Its own last
  sentence says "longer than the time above", and it used to sit below the status explanation.

**"Rounded up", not "rounded", and the reason is a stale claim in `grid.py`.** `encode_minutes`
is `ceil`, so a cell displaying 12 min holds a model time in `(11, 12]` and the number shown
**overstates by up to 60 s**. That docstring justified the cost with "nothing displays it — there
is no per-cell readout anywhere in the render path", which the card falsified on 2026-11-14. It
is corrected, and the 30-second-unit option it named for "the day a per-cell number is shown" is
now an owner decision rather than a hypothetical.

**The two negative headlines were left alone**, and that is deliberate: they are the same kind of
claim stated the same way, and changing them was not what pass 54 asked for. The estimate note
sits under all three so the hedge is not applied to inclusions alone — a card that qualified only
its affirmative verdict would present an exclusion as the more certain answer.

36 card checks (3 new), **33 of 33 card mutations caught, 0 inert**, 4 new: the note dropped, the
rounding described as "to the nearest", the measurement described as from the address, and the
warning swapped back below the status explanation. **Rendered in Chrome and photographed on 2026-11-16**, at the same cell (100, 73) as the
2026-11-15 screenshot, which is what pass 54 asked for when it said to test the wording in
the first browser session: `docs/experiments/s3-11/card-after-pass54-wording.png`, beside
the old one. The live card reads, in order — the model sentence, the estimate note,
`own_triangle_grocery_walk PASS`, "20 min · your limit 20 min", the restricted-route
warning, and the two places at the junction.

**Still not done, and still the owner's:** pass 54's other three leftovers, all deletions —
`byteswap_control.mjs`, `bench_explain.mjs` after its measurement is recorded in the experiment
record, and `test_the_migrated_header_is_the_generators_order` with its `mutate_migrate.py`
mutation.

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

### 3. Where the published raster actually lands in the browser — **DONE 2026-11-15, both
halves**

MapLibre places the raster in Web Mercator while the published rows are linear in latitude. That is
now measured rather than guessed, in the decomposition pass 54 asked for — **the drawn pixel
against the published pixel first**, with the source grid left to `s3-5-export-regrid.json`,
because folding the two together hands a correct measurement the wrong interpretation.

`scripts/measure_drawn_pixel.py` → [s3-10-drawn-pixel.json](../experiments/s3-10-drawn-pixel.json):

* **The displacement is sub-pixel.** The drawn raster sits up to **0.3656 of a row — 35.6 m —
  north** of the published one, zero at the footprint's north and south edges and largest in the
  middle. At **all 514 row centres the two rules name the same row**, so the obvious probe — read
  the page at a cell centre and compare — *could not have failed*. It would have reported
  agreement 514 times and established nothing. The probes are near row boundaries for that reason.
* **The household figure is not the row movement.** 131,571 structures read a moved row, which
  reproduces the published figure exactly, but a moved row only matters if the colour moves with
  it. At the twenty minutes the page opens on, **5,801 structures stand where the painted colour
  contradicts their own card** — **2,771 painted out while the publication includes them**, 2,798
  the other way. The first of those is a **false exclusion in the picture**, which is the risk
  Codex pass 54 named as unexamined: nobody opens a card in a neighbourhood they have already
  ruled out.
* **Two controls, in the artifact.** Replacing the drawn rule with the published one must report
  zero contradictions and does; shifting by a whole row must report more and does. The script
  refuses to write the file otherwise.

**The browser ran on 2026-11-15** →
[s3-11-browser-placement.json](../experiments/s3-11-browser-placement.json). Chrome 157 on this
machine, the page served on loopback from the working tree, the shipped bundle, the default 20
minutes:

* **Zero disagreements with the oracle at all eleven probes.** The sub-row displacement is drawn
  exactly as computed, so the 5,801 and the 2,771 above describe the page a household gets rather
  than a model of it.
* **All three sensitive probes contradicted the card in the live page** — blue cell, transparent
  pixel, and the reverse — which is the failure mode itself, observed rather than predicted.
* **The three owed disclosures were rendered, in one card**: `(row 100, col 73)`, the
  restricted-route warning, and "measured to one of 2 places at this junction: Weaver Street
  Market, Inc, Weaver Street Market Administration". Screenshot at
  `docs/experiments/s3-11/card-at-boundary-north.jpg`.
* **The affine blind spot is closed by a picture**, as the self-test said it would have to be.
  Zoomed until one row was 38 screen pixels, the painted edge sits on the line where MapLibre's
  quad puts it; the publication's own line is 9 px south of that, inside unpainted ground, and the
  ±1 row controls are 38 px away. `docs/experiments/s3-11/colour-edge-against-four-hypotheses.png`.
  That reading is off an image, not computed: neither venv here has an image library.

**The first run found two defects, both in the instrument.** A canvas stores translucent pixels
premultiplied by alpha, so the page's blue reads back (24,119,241,150) and not (24,119,242,150);
and `MouseEvent`'s clientX is an IDL `long`, so a fractional coordinate is truncated and the hover
landed up to two thirds of a cell away — on a probe set deliberately placed on cell boundaries.
The Node self-test had stubbed away both. It now reproduces them exactly and is **13 checks**;
`probe_placement.js` compares colour to within the one count premultiplication costs, with alpha
exact, and chooses the whole screen pixel that lands on the cell the probe is about. Ledger
instance 48.

`window.G3Probe` in `app.js` is the read-only window it needs: seven accessors, none of which can
set a threshold, enable a layer, move the map or render a card. *(An earlier note here and the
commit message for `cdcd77c` both said eight; there are seven.)*

### 3b. What the page says at the walked cell — **DONE 2026-11-16**

Pass 54's precondition for the re-walk: *"the audit sheet's encoded 14 minutes is evidence about
its recorded artifact; the outstanding placement question is precisely why it should not simply be
assumed to authenticate the answer shown at a real door."* So the page was read at that door
before anybody walks it. [s3-12](../experiments/s3-12-what-the-page-says-at-the-walked-cell.json).

**The page agrees with the sheet row, at the cell the door is actually in.** At a 15-minute limit
it shows `(row 282, col 126)`, PASS, "14 min · your limit 15 min", the restricted-route warning,
and "measured to Hill's Family Asian Markets" — the sheet's `encoded_minutes`, `outcome_15min`,
restricted approach and `predicted_destination`, rendered. Screenshot at
`docs/experiments/s3-12/card-at-the-walked-cell-15min.png`.

**And the reading found the probe that was supposed to make this checkable was 400 m wrong.**
s3-10's `the_walked_cell` took the sheet's `row`/`col` — (286, 129) — as an index into the
*published* raster. Those columns index the UTM `GridSpec`; the published grid is a different
grid with its own indexing and also has a cell (286, 129). The two disagree about everything a
walker would check: 14 minutes against 24, PASS at the band against FAIL, flagged restricted
against not, Hill's Family Asian Markets against Seal The Seasons. Its own text called its card
"the one a person can check against a walk". **Ledger instance 50**: an index is not a location
until it names its grid. Nothing could have caught it internally — the probe was self-consistent,
its expectations were re-derived from the planes by a second path, and the browser agreed with it
exactly. It took comparing the apparatus against something outside it.

The probe is re-pointed at the door's coordinate, and regenerating the oracle changed that one
probe and nothing else. That made the 2026-11-15 run a run against a *different* oracle, and
`test_the_run_is_against_the_oracle_that_is_committed` failed on it, which is the guard working.
**The probe was re-run against the corrected oracle: eleven probes, zero disagreements, three
sensitive probes still contradicting the card.** The first run is kept as what it was, with its
own check that exactly one probe may now differ.

**Two costs measured, one not.** The card round trip is **0.2 ms median over 17 hovers** in a
real browser — the figure the card plan listed as unverified — which matches the Node worker-side
measurement's order and settles that one `explainAt` per pointer move needs no batching. Worker
compute over 20 scripted threshold changes is 9.1 ms median. The **slider-to-repaint** figure the
page reported, 1002 ms, is **the instrument**: see the runtime constraints below.

### 3c. Codex pass 55 — **INTEGRATED 2026-11-16. Nine findings, and two of my guards were
hollow.**

The owner reopened the chain for the three browser commits. Pass 54 had said the next review of
the card should follow its first browser use rather than another reading of the same code; it had
had three. Report at `docs/research/56-codex-review-pass55/REPORT.md`, prompt committed first.

**The run died at 1h 28m without reporting**, process gone and the job state still saying
`running`. Four findings were recovered from the Codex session transcript and handed back on
resume as established facts. Worth knowing: **Codex could execute processes this session**,
against the standing note in [[reference-codex-runtime-quirks]] that every `exec_command` fails
here. It ran the venv's Python, rebuilt the UTM grid, reproduced counterexamples and ran pytest.

**Two of the findings are defects I shipped yesterday while fixing other defects.**

* **F1 (High): the card's new origin sentence named the wrong point.** "Measured from the centre
  of this cell" — the card's cell is a cell of the *published* WGS84 raster; the seconds were
  computed at a **UTM** cell centre and the publication is a NEAREST reprojection, so a published
  cell carries a time measured a **median 39.9 m** from its own centre, p90 55.8 m, up to the
  70.6 m half-diagonal. Measured here, not argued. It now reads *"Times are model estimates for a
  nearby grid point, not your address, and are rounded up to the whole minute."* **Ledger instance
  51**: a check on a true neighbouring fact is not a check on the claim — my pytest asserted that
  the producer evaluates `cell_centers_xy()`, which is true, and about the other grid.
* **F4 (Medium): a query coordinate was promoted into a recorded door**, in seven places including
  the instruction telling the owner where to walk. `start_lon`/`start_lat` are **blank**; filling
  them is the point of the walk. **Ledger instance 52**: I repaired "an index is not a location"
  by inventing a location, in the same commit.

**And two guards were hollow, each demonstrated with an executable counterexample.**

* **F6: three probe self-tests reported PASS before their assertions ran.** `check()` called
  `fn()` and printed PASS; three checks return promises, so `process.exit()` ran first. Codex put
  `assert(false)` in the colour-tolerance check and the run still printed "all checks passed",
  exit 0 — **I reproduced it before repairing it**. The worst one to lose was that tolerance
  control: I added it the day before, for a risk I had identified myself, and it had never run.
  The runner now awaits, and carries a control on its own awaiting. 14 checks.
* **F7: the newest run was trusted on a summary number nobody checked.** A run doctored to
  contain eleven timed-out hovers, wrong card text and explicit per-probe disagreements passed
  `test_the_run_is_against_the_oracle_that_is_committed`, and every substantive check ran on the
  *first* run only. Both runs now get every structural check and the summary is required to equal
  what the probes say. Re-running Codex's counterexample against the repair: three tests fail.

**Also corrected:** F2, the exclusion headline, now *"Our model rules this cell out for at least
one of your limits"* — leaving it categorical while hedging inclusions made an exclusion read as
the more certain answer, which is the asymmetry the estimate note was supposed to prevent and does
not, because "times are estimates" does not qualify an exclusion caused by a shop we never held.
F3, "the page draws the raster where s3-10 said" — the probe reads the **source canvas** and
computes the drawn row from projected corners; it never samples a rendered pixel, so the
screenshot carries that claim, locally. F5, "free", "untainted" and "60 fps" withdrawn, and
0.2 ms is **1,000 times** 0.0002 ms, not the same order. F8, the 5,801 counts **outcome**
disagreement, not colour. F9, the collector now refuses a chunk index outside its declared range.
The walked-route caveat said "20 minutes"; it is about 25 against a published 14, and inadmissible.

**Ledger instances 49 and 50 were both corrected for overstatement** — pass 48 found four of five
overstated, pass 55 two of two. 49 claimed a cross-check meant the two "cannot drift apart again
in silence", and the next sentence it checked shipped false. 50 claimed "nothing internal could
have found it"; the coordinate and both grids were in the repository all along.

**What pass 55 says to do next:** correct the wording (done), then *"have somebody unfamiliar with
the implementation select a place, interpret its result, and explain what the map has ruled out"*.
It also recommends **keeping whole-minute `ceil`** for now rather than moving to 30-second units —
the display cost is understood and statable, and no household observation shows the rounding
causing a mistaken decision.

### 3d. Seven criteria, and two defects only a real criteria set could show — **DONE
2026-11-16**

The owner chose the criteria for the reading test: park and school on foot, a grocery and a place
of work and the airport by car, coffee by bike, beside the grocery walk already published. Seven.
The bundle had held **one** since it was first exported. Full record in
[[project-phase1-s3-criteria-build]], protocol in [[s3-13-reading-test]].

Reachable is the share of the **UTM** surface's 330,502 cells with a finite time, as each
build reports it. The published WGS84 planes differ slightly — grocery walk is 78.3% there —
and mixing the two in one column is how a table stops being comparable.

| criterion | destinations | reachable | opens on |
|---|---|---|---|
| Grocery shop, walk | 510 nodes / 550 places | 77.7% | 20 min, **on** |
| Park, walk | 723 / 746 | 81.1% | 15 min, off |
| School, walk | 537 / 559 | 78.2% | 20 min, off |
| Grocery shop, drive | 510 / 550 | 80.6% | 10 min, off |
| Coffee shop, bike | 644 / 678 | 83.1% | 15 min, off |
| Duke University Hospital, drive | 1 point | 80.6% | 30 min, off |
| RDU airport, drive | 2 points | 80.6% | 40 min, off |

The last two are **named places**, a new kind of layer target: `locfinder/places/named_places.py`
holds each slug's points *and where they came from*, and `select_target` dispatches so neither
builder carries a branch. Both were pinned against the data rather than matched by name — Overture
holds *JFK Airport New York* at RDU and has no record that is Duke University Hospital, only
per-department ones.

**Two defects, both found by having a real criteria set rather than by any test.**

* **The page opened on a blank map.** Pass 43 F4 recorded that every manifest entry starts
  enabled. Harmless at one criterion; at seven the opening view is the intersection of all of
  them, and *drive to RDU within 10 minutes* is empty from anywhere in Chapel Hill. `resetAll`
  had the same bug one button press away. The manifest now carries `default_on` and
  `default_threshold_min`, both optional and absent-safe; the rules live in `card.js` so Node can
  check them, and one check reads the **shipped** manifest and fails if more than one criterion
  opens enabled.
* **The card named each criterion by its layer id.** `own_triangle_duke-hospital_drive PASS
  20 min`, to a household. The manifest has carried a `label` since it was written and the card
  had never used it. One ugly line while the bundle had one criterion; most of the card at seven.
  Found by hovering **one cell** on the built page.

Neither was reachable by the suite as it stood: every check in it is about a layer, a message or a
sentence, and both of these are properties of the **set**. Eight new card checks and five new card
mutations now cover them.

**`NO_PATH` ships for the first time, and a note had said it could not.**
[[project-phase1-s0-complete]] carried *"NO_PATH is unreachable in every shipped configuration"*.
The reason it gave — `symmetrise` making the retained graph strongly connected — holds for **walk
only**, and every layer that had ever shipped was a walk layer. The drive and bike layers produce
it at once: **57 cells per drive layer, 95 in the bike layer** (39 and 80 after reprojection).
Corrected there, and recorded as **ledger instance 53: "every" meant "the one I have"**. The
card's `NO_PATH` wording has existed all along and had never once rendered from a real published
layer; the card suite now exercises it.

**What it costs.** Deflated transfer goes from **266 KB to 1.15 MB**. Per layer: grocery walk 266 KB
(it alone carries the flag and destination planes), park 206 KB, school 203 KB, grocery drive
109 KB, coffee bike 134 KB, Duke 117 KB, RDU 118 KB.

**What was not re-measured: the slider budget.** Gate G3 is a median slider-to-repaint under
100 ms, measured on a one-layer bundle. A compute now evaluates up to seven layers over 330,502
cells each. The opening case is one enabled criterion and is unchanged; the all-on case is new and
**unmeasured**. One click of Auto-bench with the window on screen gives the figure, and that is
still an owner item.

### 3e. Pass 56 — **the owner was sceptical and asked for a critical review. 2 WRONG, 7
OVERSTATED of 20.**

The owner read the seven-criterion page, reported two anomalies, read my answers and said they
did not believe them. Two reviewers, independently and without sight of each other: **Codex**
(`gpt-6.1-sol`) and **Antigravity/Gemini** (`gemini-4-hydrogen-xhigh`). Prompt committed before
either ran (`5a7a5fe`); reviews at `docs/research/57-review-pass56/`. The prompt numbered twenty
claims and named seven places I thought I was weakest, so the review began at the soft points.

**The five measurement scripts behind the claims were in a session scratchpad**, so until that
commit neither reviewer could have checked a single number. They are in `v2/scripts/` now. That is
the process finding and it is the one most likely to recur.

**What survived:** the holes are real, they hold buildings, single-nearest-edge snapping is the
mechanism, and the hatch is the renderer working as designed. Gemini verified claim 3 as exact set
identity where I had only matched counts, and settled W1 precisely — the recomputed surface is
**bit-identical** to the committed raster once the 7,200 s horizon and the float32 cast are
applied.

> **"The hatch is the renderer working as designed" was overturned by pass 57 — see 3f below.**
> The rule *is* deliberate and both reviewers confirmed that again. But nobody asked whether the
> rule marks the set it names, and it does not: **369 of 1,075 UNKNOWN regions receive no grey
> pixel at all** and are byte-identical to EXCLUDED on screen. Pass 56 answered "is this
> deliberate" and reported it as "is this adequate". Those are different questions and only the
> first was asked.

**What did not.** One error of reasoning and seven of scope:

* **WRONG — "adding nodes would change nothing".** `speeds.py:133` charges the restricted penalty
  **per edge**, so splitting a restricted edge doubles it. Gemini ran it on the real graph:
  splitting every edge over 100 m moves **74,930 OK cells**, and recovers **6 of the 7 parks**
  currently dropped for sitting beyond the 300 m POI-to-node bound — one of which is **0.2 m from
  an edge and 356.4 m from any node**. It still makes the holes worse (125 -> 131/134), so it is
  not the fix; my reason for dismissing it was simply not a reason.
* **WRONG — the Apache counts.** 41 is the accepted input, 35 is what ships; park, school and
  coffee would add **120**, not 137.
* **OVERSTATED x7**, all the same mistake: a true number attached to a population it did not
  describe. Recorded as **ledger instance 54**, with the table of all eight.

**And one the reviewers split on.** `docs/plans/layer-contract.md` — the normative contract — still
said `NO_PATH` "is unreachable in every configuration we currently ship" in three places, and told
readers not to write user-facing copy for it. Codex missed it; Gemini found it. I had corrected
the claim in `project-phase1-s0-complete.md` and left the contract alone, which is the
incomplete-cleanup hazard of instances 40 and 47. Corrected, including the advice, since the card's
`NO_PATH` wording now renders from a real layer for the first time.

### 3f. Pass 57 — **the analysis reviewed, not the facts. The reviewers disagree, and that is
the useful part.**

Pass 56 corrected twenty facts; those facts then became four decisions put to the owner, and this
pass judged the **decisions**: the mechanisms claimed, the options listed, the recommendations made,
and the owner's own four stated positions. Thirty numbered claims, thirteen declared weaknesses.
Prompt committed before either reviewer ran (`39201c6`); reviews at
`docs/research/59-review-pass57/`.

Both reviewers were told, in the prompt, to **try to break the owner's positions rather than agree
with them**, because a reviewer handed a hypothesis hands it back confirmed. Antigravity/Gemini
(`gemini-4-hydrogen-xhigh`) reported 19 CONFIRMED, 9 OVERSTATED, 2 WRONG. Codex (`gpt-6.1-sol`)
executed **38 commands** — the first pass since 48 where the Windows sandbox let it run Python —
and reported 15 CONFIRMED, 11 OVERSTATED, 4 WRONG.

**The new error class, and it is worse than pass 56's.** Pass 56's eight overstatements were true
numbers attached to the wrong population. Pass 57's headline error is **an experiment whose
construction guaranteed its result**. I reported that multi-candidate snapping makes "zero cells
slower". The candidate experiment takes the **minimum reported time including today's answer**, so
no cell *can* come out slower — the claim is true by construction and measures nothing. Codex
re-selected on **cost**, which is what the pipeline actually does, and found **3,202 UTM OK cells
slower**. Recorded as **ledger instance 55**.

**Four claims WRONG.**

* **Claim 6 — the repair rate, the denominator and the direction.** "Fixes 76% of holes" is the
  **net** reduction 125 → 30, not original-hole repair; the executed identity test shows **all 125
  UTM originals filled and 30 new sites appearing** (published: all 121 filled, 29 new). The 77.13%
  share is of **272,961 comparable uncapped UTM cells**, not of all cells. The 169 m median access
  leg describes only the **>60 s improvement subset**. And the direction claim is the construction
  artefact above.
* **Claim 8 — topology cannot settle walkability.** Both reviewers, independently. Geometric
  contact without a shared node establishes a *representation* difference, not an available
  pedestrian connection, and the absence of a mapped fence is not evidence of one.
* **Claim 19 — the destination cap.** Matching the origins' **200 m** cap recovers **5** dropped
  park records and **loses 4 retained ones**. The 6 recoveries need a **300 m edge** cap, which
  loses **0**. Ocaneechee Park is 329.65 m from its nearest node and 229.58 m from its nearest
  edge: a 300 m edge cap recovers it, the origins' 200 m cap does not.
* **Claim 21 — parks are points.** All 746 accepted park records are `Point`; `.centroid` is a
  no-op. Corrected where it was written, in [[project-phase1-s3-criteria-build]].

**And two numbers I gave the owner in chat were wrong, both repeats.**

* **535 km², not 560.** I multiplied 56,036 published cells by 100 m squares. Published cells are
  WGS84 lon/lat and average **9,544 m²** — a 97.69 m equivalent side. Geodesic area is **535.0 km²**;
  I overstated by 25.4 km² (4.7%). Instance **50** again: *the published grid is not the UTM grid.*
* **park/walk's shipped default is 15 minutes, not 20** — and `default_on` is **false**; only
  grocery/walk opens enabled. Instance **54** again: a true number at a population it did not
  describe. The hatch figures barely move (55,752 UNKNOWN at 15 against 56,034 at 20; the 369
  invisible regions and 975 cells are identical), which is why it went unnoticed.

**Where the reviewers disagree, which is the part worth reading.**

| | Antigravity | Codex |
|---|---|---|
| Rank by product risk retired | **4 → 3 → 2 → 1** | **2 → 4 → 3 → 1** |
| "Measure first" (holes) | **UNSUPPORTED** as option 4 | **SUPPORTED** as a *bounded* access investigation |
| "Per stretch" (penalty) | **PREMATURE** | **SUPPORTED** as a charging unit, not as a value |
| "Never a centroid" (parks) | SUPPORTED in principle, PREMATURE against the shipped layer | **PREMATURE** |
| Striping is a defect | **SUPPORTED** | **SUPPORTED** |

They agree on the two ends: **striping is a real defect** and **the donut holes rank last**. My own
presentation order — 1 → 2 → 3 → 4, the order the owner asked in — is wrong as an execution order
under plan §0 on both rankings. The split on first place is substantive: Codex ranks the penalty
first because it is the only one with **direct evidence of a materially misleading recommendation**
(the walked 13.5-vs-25-minute failure); Antigravity ranks presentation first because it is the
cheapest honest improvement and covers 17% of the map. Neither is obviously right and the owner has
not chosen.

**The one finding both reached independently, and it cuts against the owner's leaning.** Keeping
120 s while switching to one charge per continuous restricted run makes the audited three-edge
shortcut **cheaper**, not dearer — so per-stretch at the current value *weakens* the deterrent that
the walk showed was already too weak. Recorded in [[project-phase1-s3-soft-way-dependence]].

**What this pass bought that pass 56 could not.** Codex could execute, so several weaknesses got
answers rather than opinions: the full two-state routing expansion costs **0.089 s → 0.196 s** of
Dijkstra and **37.81 MB → 75.76 MB**, which retires the "per-stretch is too expensive" worry
outright; a per-stretch prototype on grocery/walk moves **5,690 published minute values and 189
threshold decisions**, which retires both "it changes nothing" and "it changes 20%"; and the
invisible UNKNOWN regions hold **55 buildings — 0.011% of the published inventory**, against
**3,364** in UNKNOWN cells overall, which says the owner's visual complaint is where the harm is and
my "invisible patches are the serious half" framing was backwards.

No production code changed. All four decisions remain the owner's and **none is taken**.

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
