# Codex pass 51 — the per-criterion card and the walked-record refusal

**Run 2026-11-14**, read-only, `--model gpt-6.1-sol`, against commits `04bfacf`, `3406da6`,
`ba9213c`, `1aa0570`. Prompt: [`52-codex-review-pass51-prompt.md`](../52-codex-review-pass51-prompt.md).

**Twelve findings, three High.** Four of the six claims the prompt put up fail or are narrowed, and
both of the two suspicions the prompt asked it to settle came back **confirmed as defects**.

**What it could and could not do.** Codex cannot start a process on this machine — see
[`reference-codex-runtime-quirks`](../../engineering-notes/reference-codex-runtime-quirks.md) — so
it could not run Python, pytest, `node` or the benchmark. It did what passes 49 and 50 did instead:
replayed both JavaScript harnesses inside `vm` contexts through the `node_repl` tool, reaching the
baseline **79 conformance checks and 16 card checks passing**, and then applied each mutation in
memory. So the B findings carry **executed** witnesses; the A findings are source-derived and say
so. The three measurements the prompt handed over were attacked as **method**, which is the only
way they could be attacked here, and B7 and B8 are the result.

**The report is reproduced verbatim below**, including the parts this project disagrees with, so a
later reader can judge the review rather than my summary of it. What was reproduced and what was
changed is in the commit that integrates it.

---

Three High findings: a walk without a duration can disappear into “planned,” the card can retain an obsolete eligibility answer indefinitely, and substantial corruption of explanations passes both suites.

I replayed the harnesses in JavaScript VM contexts: **79 conformance checks and 16 card checks passed on baseline**. All mutations below were applied in memory. No files changed. Python findings are explicitly source-derived; I could not execute Python, pytest, or the benchmark.

**A1 — High: a documented walk without a duration becomes “not walked.”**  
[admissible.py:113](C:/Users/arikt/documents/github/distanceFinder/v2/locfinder/measure/admissible.py:113), [score_walked_audit.py:82](C:/Users/arikt/documents/github/distanceFinder/v2/scripts/score_walked_audit.py:82)

**Witness, source-derived:** take a sheet row with `encoded_minutes=14`, set `walked_date=2026-11-14`, leave `walked_seconds` blank, and record `duration_timed=no`. The person walked but failed to record a usable duration.

`record_for` discards `walked_date`. `WalkedRecord.walked` becomes false solely because `walked_seconds is None`. `admissibility` returns `NOT_WALKED` immediately, before checking timing or any other evidence.

For that singleton, the resulting values follow directly from the source:

```text
walked=0
planned=1
inadmissible=()
no_admissible_observation=False
```

The event has vanished from the refusal record. This breaks claim 6.

**Fix:** represent whether a walk happened separately from whether its duration was recorded. Ingest the existing event evidence, and refuse a walked record lacking a duration. Test a dated walk with blank seconds.

**B1 — High: changing criteria leaves the old card beside the new raster indefinitely.**  
[app.js:374](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/app.js:374), [app.js:558](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/app.js:558)

**Executed witness:** one OK cell contains 12 minutes.

1. Compute sequence 1 with limit 15.
2. Hover it: the card says PASS, “Every criterion you have on is satisfied here,” and “your limit 15 min.”
3. Change the limit to 5.
4. Compute sequence 2 and complete its repaint.

The raster now excludes the cell. The card still displays the sequence-1 PASS and limit 15. Neither `recompute` nor `handleWorkerResult` invalidates or refreshes it. `handleExplainAt` checks `reqId` but never checks `msg.seq`.

I reproduced this through the actual app functions with DOM and paint stubs, including completion of `handleWorkerResult`.

**Fix:** track the current inspected cell and the computation represented by the displayed raster. Invalidate obsolete cards when criteria change, refresh after computation, and reject explanations belonging to another sequence. Test delayed replies and completed repaints.

**B2 — High validation gap: the explanation’s disclosures can be wrong while every advertised check passes.**  
[worker_conformance.mjs:296](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/worker_conformance.mjs:296), [worker.js:703](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/worker.js:703)

This is the second structural blind spot requested in claim 1. Outcomes do not authenticate the accompanying explanation.

Each following mutation, confined to `handleExplainAt`, independently passed **all 79 conformance checks and all 16 card checks**:

| Executed mutation | Undetected consequence |
|---|---|
| Report `42` for every non-null published time or bound | Correct outcome beside a fabricated minute |
| Report `1 - routeFlags[k][p]` for disclosing layers | Restricted routes become clear; clear routes become restricted |
| Always report `verdictName: "INCLUDED"` | Excluded cells get the affirmative headline |
| Rename every destination place after the first to `"Fabricated Shop"` | Invented members of shared-node sets reach the card |
| Report `horizonS: 1` | Incorrect horizon metadata |

The assertions bind outcome names to outcome codes and status names to status codes. They do not comprehensively bind those fields to the source planes. The verdict name is not bound to the verdict code. The thorough `destinationAt` comparisons do not establish that `explainAt` returns the same destination.

**Fix:** compare every explanation field with immutable expectations derived from fixture bytes and the frozen destination tables. Include verdict spelling, actual status, minute/null, horizon, actual flag byte, and the complete destination record. Keep these surviving mutations as controls.

**A2 — Medium: destination-name equality accepts the wrong branch and cannot represent permitted alternatives.**  
[admissible.py:197](C:/Users/arikt/documents/github/distanceFinder/v2/locfinder/measure/admissible.py:197), [score_walked_audit.py:95](C:/Users/arikt/documents/github/distanceFinder/v2/scripts/score_walked_audit.py:95)

**Concrete witness, source-derived:** the committed metro sheet contains two different destinations named Food Lion:

- `band10min_fail-02`: destination at `(-78.660641, 35.886074)`.
- `band15min_fail-02`: destination at `(-78.611194, 35.794319)`.

Start inside the first row’s cell, walk to the second Food Lion, truthfully enter `destination_used=Food Lion`, and supply the other required fields. The predicate accepts the destination comparison. It has no reached-destination identifier or coordinate to distinguish the shops.

The opposite error is also encoded: the README explicitly permits any shop among `predicted_destination_alternatives`, but ingestion discards that column. A differently named permitted alternative is refused.

**Fix:** compare destination identities against the selected node’s allowed place set. Preserve branch/location identity and ingest alternatives. Names should be presentation fields.

**A3 — Medium: an explicitly unresolved approach passes the route requirement.**  
[admissible.py:209](C:/Users/arikt/documents/github/distanceFinder/v2/locfinder/measure/admissible.py:209)

**Witness, source-derived:** replace the existing `good` fixture’s route with:

```text
I cannot remember whether I used the private track or avoided it.
```

Everything else remains unchanged. The predicate returns ADMISSIBLE because the text is nonblank. The singleton consequently scores FAILED, although the decision report’s private-approach question remains explicitly unresolved.

The README documents the weaker nonblank rule, so the README and predicate agree. They do not establish the stronger requirement claimed by the decision report.

**Fix:** capture a structured approach answer with an unresolved state and refuse that state where approach identification is required. Retain prose for detail. Merely requiring a longer sentence would not resolve this.

**B3 — Medium: “at least” overstates a rounded-up lower bound.**  
[card.js:70](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/card.js:70), [wire.py:28](C:/Users/arikt/documents/github/distanceFinder/v2/locfinder/wire.py:28)

**Executed witness:** initialise a valid BEYOND_HORIZON cell with:

```text
horizon_s=601
value=11
threshold=10
```

The worker accepts it. The card prints:

> at least 11 min

The data establishes that the search horizon was 601 seconds. A qualifying journey taking 630 seconds is compatible with that evidence, yet takes less than 11 minutes. Ceiling preserves the integer-threshold predicate; it does not preserve a literal lower bound expressed in minutes.

This is a sixth failure beyond the five targeted rendering errors.

**Fix:** render a mathematically justified bound—for example, “more than 10 min” here—or retain sufficient precision to disclose the actual bound. Add non-integral-minute bound cases.

**B4 — Medium: deliberate suppression becomes a false claim that the layer does not disclose.**  
[worker.js:691](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/worker.js:691), [card.js:146](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/card.js:146)

**Executed witness:** two enabled criteria at one cell:

```text
walk-grocery: OK, 2 min, limit 10, destination Grocery A
drive-work:   OK, 30 min, limit 10, destination Work B
```

The combined verdict is EXCLUDED. `explainAt` suppresses both destinations. The passing grocery criterion then renders:

> This criterion does not say which destination the time was measured to.

It does say: Grocery A is present in its plane and table. The handler withheld it because another criterion failed.

This settles suspicion 2 as an actual disclosure defect. The existing `destinationAt` policy does not justify assigning the same meaning to `null` in this different response.

**Fix:** disclose the destination of each enabled criterion’s published journey independently of the combined verdict. If suppression remains policy, represent suppression separately from non-disclosure and render it accurately.

**B5 — Medium: a late reply restores an inside-area card after the pointer leaves.**  
[app.js:374](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/app.js:374), [app.js:404](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/app.js:404)

**Executed witness:** move inside, creating pending request 1; move outside the raster; deliver reply 1. “Outside the published area” is replaced with the old cell’s affirmative card.

`mouseout` has the same issue. Neither path invalidates the pending request or clears queued positions. With one request in flight, the old request remains the newest *sent* request even after the pointer has moved elsewhere.

**Fix:** invalidate pointer requests and queued positions on exit. Check replies against the current pointer generation/location, and avoid rendering a superseded position before sending its replacement.

**B6 — Medium validation gap: there are no multi-criterion rendering tests, including hand-built ones.**  
[card_selftest.mjs:42](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/card_selftest.mjs:42), [card_selftest.mjs:280](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/card_selftest.mjs:280)

Suspicion 1 understates the gap. The hand-built rendering calls also supply one criterion at a time.

**Executed witness:** change the renderer loop to:

```js
for (const crit of msg.criteria.slice(0, 1))
```

All 16 checks still pass. A renderer that silently discards every later criterion is therefore accepted.

The real-data sample exercises three statuses and shared destinations, but cannot exercise mixed disclosure, mixed outcomes, multiple destinations, disabled middle layers, or per-criterion association. Its assertions also do not validate most sentences against their underlying records.

**Fix:** render actual worker replies from the multi-layer conformance groups and assert every criterion’s disclosures separately. Add three distinct layers, distinct thresholds/horizons, all enable masks, mixed disclosure, and PASS/FAIL/UNKNOWN combinations. Real multi-layer data would add evidence, but these discriminating fixture tests can be added immediately.

**B7 — Medium: 0.366 rows is the idealised projection error, not the renderer’s full analytical error.**  
[card.js:48](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/card.js:48), [card plan:165](C:/Users/arikt/documents/github/distanceFinder/docs/plans/2026-11-14-per-criterion-card-plan.md:165)

The Mercator interpolation assumption is substantially right for this rectangular source. However, MapLibre first rounds its corner positions to integer tile coordinates. Canvas sources inherit this placement path; raster drawing uses those rounded corners. [CanvasSource](https://raw.githubusercontent.com/maplibre/maplibre-gl-js/v5.24.0/src/source/canvas_source.ts), [ImageSource](https://raw.githubusercontent.com/maplibre/maplibre-gl-js/v5.24.0/src/source/image_source.ts), [raster drawing](https://raw.githubusercontent.com/maplibre/maplibre-gl-js/v5.24.0/src/webgl/draw/draw_raster.ts).

**Executed arithmetic using the pinned implementation:**

| Quantity | Result |
|---|---:|
| Ideal, unrounded maximum row-coordinate difference | 0.3656216 rows |
| Maximum after corner quantisation | approximately 0.3880725 rows |
| At the stated 97.5 m/row | approximately 37.84 m |
| Maximum horizontal difference for these bounds | approximately 0.02278 columns |

The selected source tile zoom is 9, with extent 8192. Longitude is linear in Mercator, so it has no corresponding latitude-curvature error; corner quantisation still shifts it. [Tile conversion](https://raw.githubusercontent.com/maplibre/maplibre-gl-js/v5.24.0/src/tile/tile_id.ts), [extent](https://raw.githubusercontent.com/maplibre/maplibre-gl-js/v5.24.0/src/data/extent.ts).

These are continuous coordinate offsets. The corresponding discrete cell indices can differ by one near boundaries. They are not a complete screen-space rendering bound.

**Fix:** include actual corner quantisation in the analytical account and test rendered placement. The card formula matches the shipped latitude-linear grid, but that establishes only its lookup convention. The displayed colour and explanation still need to refer to the same geographical cell.

**B8 — Low, measurement claim: the benchmark does not establish the pointer-move conclusion.**  
[bench_explain.mjs:71](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/bench_explain.mjs:71), [card plan:152](C:/Users/arikt/documents/github/distanceFinder/docs/plans/2026-11-14-per-criterion-card-plan.md:152)

**Method witness:** the script compares one initial compute with warmed explanation calls, excludes browser messaging and rendering, and measures one layer.

Here `gcd(7919, 330502)=1`, so a full period visits every cell. The measured 20,000 calls visit only about 6% of that period. Each step jumps roughly twelve rows plus 203 columns, losing the locality of neighbouring pointer positions. That makes the **memory-access component generally pessimistic** relative to local movement.

Conversely, the tight warmed loop, recent whole-plane scan, desktop runtime, and missing asynchronous/rendering work can make the overall figure optimistic. Prime stride does not settle the net direction.

A whole-raster compute is not the relevant denominator. The relevant quantities are event rate, frame budget, end-to-end latency, and interference from concurrent computes. The page’s round-trip timing also stops before `renderCard`, excluding its DOM update and paint.

**Fix:** retain recomputation as a reasonable prototype choice, but narrow the conclusion. Measure real browser interactions and phone latency, including rendering and queued computes. The existing pointer coalescing is already useful.

**B9 — Low, oracle claim: independence is narrower than stated, and zero-filled digests cannot prove visitation.**  
[make_wire_vectors.py:65](C:/Users/arikt/documents/github/distanceFinder/v2/scripts/make_wire_vectors.py:65), [worker_conformance.mjs:252](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/worker_conformance.mjs:252)

The expectations are independent of the JavaScript implementation. They are not independent of Python’s verdict-generation rule.

I checked the recorded fixtures:

- **41 single-criterion cases:** the outcome expectation duplicates the verdict expectation.
- **Five multi-criterion cases, covering 14 cells:** the new expectations preserve information erased by combination.
- One case enables nothing.

All 18 real-window outcome digests exactly equal their existing verdict digests. The generator’s separate comparisons with `status.evaluate` provide additional evidence; this is not wholly circular.

The digest byte representation itself is correct: both sides hash contiguous signed eight-bit codes in row-major order.

**Executed visitation witness:** skip querying real-window cell 5166, an OK one-minute PASS, in the T=121 cases. All 79 checks still pass. Its unwritten `Int8Array` slot already contains zero, the correct PASS code. The current loop visits every cell; the digest alone cannot establish that fact.

**Fix:** initialise observation buffers to an impossible code or track visitation explicitly. Describe the oracle as cross-language conformance with additional per-layer discrimination, and preserve independent semantic checks.

**Disposition of the six claims**

| Claim | Verdict |
|---|---|
| **1. Outcomes fold to compute’s verdict** | Survives as the tested numeric relationship. It does not authenticate the explanation’s disclosures or headline: B2. |
| **2. Python expectations are therefore independent** | Narrowed. Independent of JavaScript; largely duplicate existing single-layer expectations and share Python semantics. B9. |
| **3. `explainAt` cannot move eligibility** | Numeric non-interference survived my probes. Household consistency fails through stale presentation: B1 and B5. |
| **4. Null is accurately disclosed and the card never overclaims** | Fails: policy suppression masquerades as non-disclosure, and rounded bounds overclaim duration. B3 and B4. |
| **5. Predicate is the report’s table in code** | Fails: destination labels do not establish identity, alternatives are lost, and explicit route uncertainty passes. A2 and A3. |
| **6. Inadmissible walks never disappear** | Fails for a documented walk lacking seconds: A1. The specifically listed duplicate-label, unpublished-time-with-seconds, and zero-second cases are handled correctly by source inspection. |

For the surviving numeric claims, missing evidence remains browser structured-clone/event sequencing, broader lifecycle combinations, and more varied multi-layer fixtures. I found no current `enabledIndex` mis-walk.

**Disposition of the five suspicions**

1. **Confirmed, more strongly:** even the hand-built card tests never render multiple criteria. The first-criterion-only mutant survives.
2. **Confirmed as a defect:** suppression produces a false non-disclosure sentence, not merely an omitted convenience.
3. **Current indexing held:** all eight three-layer enable masks preserved thresholds 11/17/23 correctly. A throwing fractional-threshold compute left `explainAt` reporting `notComputed`. Commit those patterns as regression coverage.
4. **A false `yes` is a self-report limit:** an extra checkbox cannot verify a timer. Useful checks can reject missing durations, inconsistent timing records, and unresolved answers; independent timing evidence would be needed to verify honesty.
5. **The backfill is defensible:** the pre-existing notes explicitly say “NOT STOPWATCH-TIMED.” Moving that documented assertion into `duration_timed=no` preserves its meaning. “Closer to 25 mins” alone would not justify the inference. Existing owner copies still need a migration that preserves their observations; regenerating a filled sheet is not an appropriate migration.
