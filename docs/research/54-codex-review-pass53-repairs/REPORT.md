# Codex pass 53 — the pass 52 repairs

**Run 2026-11-14**, read-only, `--model gpt-6.1-sol`, against `bcae16e`. Prompt:
[`54-codex-review-pass53-prompt.md`](../54-codex-review-pass53-prompt.md).

**Eleven findings, two High. Five of the six claims fail.** The fifth consecutive pass to find more
in the previous pass's repairs than in the work being repaired.

**The prompt's first claim was "this time I enumerated the class rather than the instances", and it
fails twice over** — which is ledger instance 40 recurring for the second pass running:

* **F1** — three more worker corruptions pass all 87 worker checks and all 29 card checks. My
  enumeration of the reply **omitted three envelope fields** (`outside`, `invalidCoordinates`,
  `notComputed`); the sequence assertion compares against a constant because every exhaustive case
  computes with `seq: 1`; and the three-layer group added for F1 last pass **carries no
  destination or flag planes**, so destination-index substitutions survive it.
* **F2** — the sheet has **18 owner columns** and the predicate reads 15. `door_offset_m` is
  omitted, and the README explicitly asks the owner to measure it. Worse, the whole inference is
  unsound in both directions: the README's step 2 has the owner record a start door *before*
  walking, so a prepared-then-abandoned sheet is classified as a refused walk.

**One finding is a live defect on the committed sheets.** F5: `by_name = {p.name: p for p in
permitted}` collapses members by name, so where a node carries two places of the same name the
**coordinate-less alternative overwrites the selected destination** — and
`triangle-grocery-walk-with-destinations.csv` has exactly that shape on two rows. A legitimate walk
ending at the selected shop would be refused for having no coordinate to match.

**What it could and could not do.** Codex cannot start a process here, so it replayed both
JavaScript harnesses in `vm` contexts to a passing baseline and applied every mutation in memory;
the adapter witnesses used the real `app.js` functions with DOM, clock, worker and paint stubs. The
Python findings are source-derived and say so. It also verified the reviewed files against
`bcae16e` by reading git objects directly, allowing for CRLF conversion.

**Two of the prompt's suspicions were settled in my favour**, which is worth recording because most
are not: the single `explainSentAt` timestamp measures the right interval (the old reply's timing
is recorded before `post(send)` overwrites it, confirmed with an executed two-request witness), and
removing `pointerGen` was reasonable for the current contract.

**The report is reproduced verbatim below.**

---

**The class is still open.** I found three worker corruptions that pass both complete suites, another omitted observation column, and a migration that can silently discard an existing observation.

Baseline: **87 worker checks and 29 card checks passed** in JavaScript VM contexts. All mutations were applied in memory. No files changed. HEAD is the subsequent prompt commit `8dcf349`; I read Git objects directly and verified that all 11 reviewed implementation/test files match `bcae16e`, allowing for CRLF conversion.

**Python findings are source-derived, not executed.** I could not run Python, pytest, Git commands, geospatial imports, or a browser. Application witnesses below used the actual `app.js` functions with DOM, clock, worker, and paint stubs.

**F1 — High validation gap: sequence and destination-index corruptions still pass every check.**

Locations: [worker_conformance.mjs:323](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/worker_conformance.mjs:323), [worker.js:656](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/worker.js:656), [worker.js:705](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/worker.js:705), [worker.js:707](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/worker.js:707).

Each mutation independently passed **all 87 worker checks and all 29 card checks**:

| Executed mutation, confined to `handleExplainAt` | Concrete failure outside the checked cases |
|---|---|
| Replace `seq: state.lastSeq` with `seq: 1` | After compute 2, explanations still carry sequence 1. The inspector rejects them. |
| Read `destTables[enabledIndex - 1]` | With `[false, true]`, criterion `destB` names **A Shop 3 / A Annex 3** instead of **B Shop 3 / B Annex 3**. |
| Read `destinations[enabledIndex - 1][p]`, retaining the original availability guard | The same query names **B Shop 0** instead of **B Shop 3 / B Annex 3**. |

The sequence assertion compares against a constant because the exhaustive explanation loop always computes with sequence 1. The lifecycle test computes sequence 3 but does not authenticate the subsequent explanation’s sequence.

The three-layer group has **no destination or flag planes**. Its enable masks therefore cannot discriminate destination-index substitutions. The two naming layers are tested together and with A alone; **B alone is missing**.

My independent reply enumeration is:

- Envelope/result: `type`, `reqId`, `seq`, `row`, `col`, `outside`, `invalidCoordinates`, `notComputed`, `verdict`, `verdictName`, `criteria`.
- Criterion: `layer`, `outcome`, `outcomeName`, `status`, `statusName`, `value`, `valueIsLowerBound`, `thresholdMin`, `horizonS`, `routeFlag`, `namesDestination`.
- Named destination: `ordinal`, `nodeIndex`, `placeCount`, `places`, including every place record.

Your enumeration omits **three actual envelope fields**. Their assertions are incomplete: adding `outside: true` to successful replies passed all 87 worker checks, although the card suite caught it. Changing `invalidCoordinates` to false passed both suites.

**Fix:** vary compute sequences in the exhaustive checks; compare expected presence and absence of lifecycle flags; add disabled-first and disabled-middle cases carrying distinct destination tables, destination planes, and route flags.

**F2 — High: the evidence enumeration still loses observations and cannot reliably establish that a walk happened.**

Locations: [audit_recommendations.py:183](C:/Users/arikt/documents/github/distanceFinder/v2/scripts/audit_recommendations.py:183), [admissible.py:217](C:/Users/arikt/documents/github/distanceFinder/v2/locfinder/measure/admissible.py:217), [score_walked_audit.py:132](C:/Users/arikt/documents/github/distanceFinder/v2/scripts/score_walked_audit.py:132).

The artifact contains **18 owner columns**. The predicate includes these 15:

`walked_date`, `start_lon`, `start_lat`, `destination_used`, `destination_used_lon`, `destination_used_lat`, `destination_qualifies`, `destination_open`, `route_usable`, `route_followed`, `route_identified`, `walked_seconds`, `duration_timed`, `witness_within_10min`, `witness_within_15min`.

It omits:

`door_offset_m`, `unresolved`, `notes`.

**Source-derived witness:** take a published row with `encoded_minutes=14`, clear the 15 evidence fields, and record only `door_offset_m=23` after visiting the starting door. The README explicitly asks the owner to record this measurement. `record_for` discards it; `WalkedRecord` cannot represent it. The row becomes **planned, not walked**, with no refusal.

Free text makes the broader claim harder: `notes="Walked this today; timer failed"` also disappears, but indiscriminately treating every note as a walk would invent walks from planning notes.

There is a corresponding false positive. The README’s step 2 asks the owner to choose and record a starting door **before** step 3’s walk. A sheet prepared through step 2, then abandoned, has start coordinates and is classified as a refused walk.

Raw values can also disappear before the predicate sees them: a sole `duration_timed="not timed"` becomes `None` through `tri_state`, then becomes a planned row. It is an invalid categorical entry, but silently erasing it is not validation.

**Fix:** represent walk occurrence explicitly, retain raw malformed observations for refusal, and reconcile all 18 owner columns with that representation. Extending the inference list alone cannot resolve planning versus completed observation.

**F3 — Medium: duplicate headers silently destroy observations before the migration snapshots them.**

Location: [migrate_audit_sheet.py:74](C:/Users/arikt/documents/github/distanceFinder/v2/scripts/migrate_audit_sheet.py:74).

**Source-derived input:**

```csv
journey_id,row,col,seconds,encoded_minutes,notes,notes
x,0,0,60,1,first observation,second observation
```

`csv.DictReader` retains only the last `notes` value. The migration then writes **“second observation” into both columns**. Its `before` snapshot was built after the first observation disappeared, so read-back succeeds and it prints “none changed.”

This directly covers an owner-added column colliding with a canonical name.

Duplicate journey IDs expose a separate weakness in the same comparison: with two rows labelled `x`, only the last row’s value survives for each `(journey_id, column)` key. Corrupting an earlier duplicate’s note can pass read-back with unchanged row count. The current writer does not itself reorder duplicate IDs; the verification simply cannot establish that it did not.

**Fix:** validate unique headers before dictionary conversion, preserve positional rows, and compare every original cell by row position and column identity. Reject ambiguous duplicate IDs or stop using them as preservation keys.

**F4 — Medium: migration writes can overwrite the only valuable copy or leave an in-place sheet partially written.**

Locations: [migrate_audit_sheet.py:111](C:/Users/arikt/documents/github/distanceFinder/v2/scripts/migrate_audit_sheet.py:111), [migrate_audit_sheet.py:114](C:/Users/arikt/documents/github/distanceFinder/v2/scripts/migrate_audit_sheet.py:114), [migrate_audit_sheet.py:149](C:/Users/arikt/documents/github/distanceFinder/v2/scripts/migrate_audit_sheet.py:149).

Three source-derived witnesses:

1. Migrate `sheet.csv`, fill observations into `sheet.migrated.csv`, then rerun migration from the original old-schema sheet. The default output silently overwrites the filled migrated copy.
2. Run `--in-place` when `.before-migration` already exists. `copy2` silently overwrites that backup; it is not preserved or versioned.
3. Give an old-schema row more fields than its header. `DictReader` stores the surplus under `None`; `DictWriter` raises on that extra key **after opening and truncating the target**. Read-back never runs. With `--out` pointing to the input, there is no backup at all.

**Fix:** validate row widths before writing, reject existing output/backup paths and input/output aliases, and write and verify a temporary file before replacing the destination.

Embedded commas, embedded newlines, quoted CRLF, and an initial BOM **do not reveal the same defect**: the explicit `newline=""`, CSV reader/writer, and `utf-8-sig` input handling are appropriate by source inspection. I did not execute their Python round trips.

**F5 — Medium: same-name alternatives overwrite the selected destination, including on real sheet rows.**

Location: [admissible.py:383](C:/Users/arikt/documents/github/distanceFinder/v2/locfinder/measure/admissible.py:383).

`by_name = {p.name: p for p in permitted}` collapses distinct permitted members by name. The last member wins.

The real metro sheet supplies an immediate witness:

- [CSV line 6](C:/Users/arikt/documents/github/distanceFinder/docs/experiments/audit/triangle-grocery-walk-with-destinations.csv:6): `band10min_fail-02`, selected **Food Lion**, coordinate `(-78.660641, 35.886074)`, alternative **Food Lion**, blank alternative coordinate.
- [CSV line 12](C:/Users/arikt/documents/github/distanceFinder/docs/experiments/audit/triangle-grocery-walk-with-destinations.csv:12): the same shape for `band15min_fail-02`.

Fill an otherwise admissible walk ending exactly at the selected coordinate. The coordinate-less alternative overwrites the selected member. The scorer refuses the walk because its target now has no coordinate.

This is not hypothetical duplicate-name data: the published side table contains seven destination entries with repeated names within an entry.

Even after recovery fills coordinates, the dictionary remains wrong. Two permitted same-name members 540 m apart can both lie within 300 m of their common node; arriving at the first can be refused against the second.

**Fix:** preserve all members for a name, match arrival against eligible members, and retain stable place identifiers rather than making the name unique.

**F6 — Medium: reducing the radius to 200 m still does not establish destination identity.**

Locations: [admissible.py:63](C:/Users/arikt/documents/github/distanceFinder/v2/locfinder/measure/admissible.py:63), [admissible.py:417](C:/Users/arikt/documents/github/distanceFinder/v2/locfinder/measure/admissible.py:417), [recover_audit_destinations.py:141](C:/Users/arikt/documents/github/distanceFinder/v2/scripts/recover_audit_destinations.py:141).

**Constructed witness:** permitted shop A is called Food Lion at `(-79, 35.9)`. A genuinely different shop B has the same name at `(-78.9985, 35.9)` and snaps to another node. Truthfully record B’s name and arrival coordinate. Their separation is **135.11 m**, so the current check accepts the wrong journey.

I evaluated the distance in JavaScript; Python admissibility was not executed.

The reverse remains possible: a legitimate entrance 210 m from its recorded place centroid fails. The snapping code constrains **centroid-to-node distance**, not centroid-to-door distance. The 70.7 m bound cited in the new justification concerns the **origin cell’s centre-to-door displacement**, not destination geometry.

I have not established a real published destination whose legitimate entrance exceeds 200 m. The artifact contains no entrance geometry with which to establish that bound.

**Fix:** treat radius as plausibility evidence, retain destination identities, and support entrances/footprints or explicit arrival verification. Neither 200 m nor centroid proximity proves identity.

**F7 — Medium validation gap: the card suite accepts an affirmative headline for every excluded location.**

Locations: [card.js:129](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/card.js:129), [card_selftest.mjs:398](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/card_selftest.mjs:398).

**Executed mutation:** replace `VERDICT_TEXT[msg.verdictName]` with `VERDICT_TEXT.INCLUDED`.

**All 29 card checks pass.** An EXCLUDED card now starts:

> Every criterion you have on is satisfied here.

The new block assertions authenticate criterion bodies but never authenticate the combined headline.

A second executed mutation copied other criteria’s destination text into unnamed non-PASS blocks. **All 29 checks also passed.** Checking every expected destination’s presence does not check absence from unrelated blocks.

**Fix:** assert the combined verdict sentence and each block’s permitted content, including forbidden cross-criterion destinations.

**F8 — Medium: stale card content remains visible after moving cells, and missing sequences bypass freshness checks.**

Locations: [app.js:383](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/app.js:383), [card.js:276](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/card.js:276).

Two executed adapter witnesses:

1. Render a PASS card at `(1,1)`, then move to `(2,2)`. The app sends another request but leaves the old affirmative card and `(row 1, col 1)` label visible until another accepted reply. The repaired guard prevents a **new stale reply** from rendering; it does not invalidate **already displayed stale content**.
2. Send request 1, start another compute, then deliver its old answer with `seq` omitted. The condition `msg.seq === undefined || …` accepts it and replaces “Recomputing…” with the old PASS card.

The second witness requires a malformed reply; the current worker normally supplies `seq`. It nevertheless disproves the inspector’s unconditional stale-reply guarantee.

**Fix:** clear or mark the card pending when its inspected cell changes, and require a valid matching sequence for computed explanations.

**F9 — Medium: native worker errors still wedge the inspector.**

Location: [app.js:288](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/app.js:288).

**Executed adapter sequence:** initialize successfully, paint compute 1, send an explanation, then deliver `worker.onerror`. Move to another cell and paint compute 2.

Result:

```text
pending = true
queued = (2,2)
explanation requests posted = 1
computePainted(...) = null
```

Only protocol messages with `type: "error"` call `cardFailed`. The native error handler rejects an initialization promise that has already resolved and leaves the outstanding explanation untouched.

**Fix:** handle post-initialization native failures explicitly, settle outstanding requests, and provide worker recovery or a terminal unavailable state.

**F10 — Low: two paint waiters for one sequence overwrite each other.**

Location: [app.js:839](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/app.js:839).

**Executed witness:** register two waiters for sequence 7 before it paints, then release sequence 7. Results were **`[false, true]`**: the first waiter timed out despite the paint. Its timer can also delete the second waiter’s map entry before a later paint.

The present `autoBench` uses one waiter per sequence, so this does not reproduce its old hang.

**Fix:** store a shared completion promise or a collection of waiters per sequence, with ownership-aware timeout cleanup.

The ordinary timeout also prints “done, 20 samples” after stopping at change 1 with zero samples. Report the completed count.

**F11 — Low: the measurement narrowing is incomplete.**

Location: [bench_explain.mjs:6](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/bench_explain.mjs:6).

The executable conclusion is now appropriately scoped. The header still calls the measurement a **LOWER BOUND** and “the floor that figure cannot go below,” while the conclusion explicitly says a desktop duration is not a floor for another runtime.

**Fix:** remove the remaining numerical-floor claim. I did not execute the benchmark or reproduce its timings.

**Disposition of the six claims**

| Claim | Verdict |
|---|---|
| **1. The classes were enumerated and closed** | **Fails.** F1 and F2 independently repeat instance 40. |
| **2. Inspector cannot render stale, wedge, or loop** | **Mixed.** Freshness and adapter recovery remain incomplete: F8–F9. The repaired deterministic-error loop did not recur. |
| **3. Arrival matching establishes identity** | **Fails.** F5 supplies real-sheet false refusals; F6 supplies a wrong-shop acceptance. |
| **4. Migration cannot lose an observation** | **Fails.** F3 silently loses a value; F4 exposes destructive file paths. |
| **5. Three layers expose criterion-index substitution** | **Fails as a general claim.** It discriminates threshold/horizon substitutions, but destination substitutions survive. |
| **6. Benchmark finishes and paint wait is correct** | **Mostly survives for its current single-waiter caller.** Full-window completion, paint-before-wait, reset during waiting, and timeout release passed adapter tests. The general helper fails F10. |

The three-layer planes really do discriminate outcomes. With all enabled, their outcome rows are:

| Cell | A | B | C |
|---|---|---|---|
| 0 | FAIL | UNKNOWN | PASS |
| 1 | FAIL | PASS | UNKNOWN |
| 2 | PASS | PASS | FAIL |

The current `enabledIndex`, `enabledOracles`, `enabledTables`, `enabledDiscloses`, and `enabledNames` walks are correctly indexed by inspection. The defect is what the fixtures can detect when those walks regress.

For paint pruning, slicing the Set removes entries in insertion order. Under the serialized paint path, that is completion order and is suitable for retaining the latest 64 paints. Real browser/MapLibre execution and native failure recovery remain unverified.

**Disposition of your suspicions**

- **Single `explainSentAt`: settled against the proposed queued-request bug.** `handleExplainAt` records the old reply’s timing before `post(send)` overwrites the timestamp. An executed two-request witness measured 50 ms and 30 ms correctly.
- **Migration imports: confirmed dependency fragility.** It imports the recovery module too, bringing in `geopandas`, `osmnx`, and other geospatial dependencies. A shared, standard-library-only schema module avoids both this dependency and duplicated column lists. Import execution was unavailable.
- **Other non-evidence answers: the larger inference remains unsound.** Start coordinates can be prepared before walking; malformed categorical values can disappear. I found no additional explicitly documented sentinel equivalent to witness `untested`.
- **Removing `pointerGen`: reasonable for the current position-and-compute contract.** Leaving and returning to the same cell under the same compute does not make its answer semantically obsolete. Restoring that counter would not repair F8 or F9.
- **Destination names on excluded cells: defensible, still unevidenced as a usability policy.** The current combined headline and per-criterion outcomes provide context; I cannot establish that households misread them. The proposed clarification should be implemented to state the intended interpretation explicitly. It does not replace household testing.
