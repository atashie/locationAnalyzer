# Codex pass 52 — the pass 51 repairs

**Run 2026-11-14**, read-only, `--model gpt-6.1-sol`, against commit `50e3884`. Prompt:
[`53-codex-review-pass52-prompt.md`](../53-codex-review-pass52-prompt.md).

**Ten findings, two High. Five of the six claims the prompt put up fail.** The fourth consecutive
pass to find more in the previous pass's repairs than in the work being repaired.

The two that matter most are both "the repair closed the instances and not the class":

* **F1** — pass 51's five surviving worker mutations are caught, and **five more survive**. Three
  are response-envelope fields no assertion mentions (`seq`, `reqId`, `row`/`col`); two are index
  substitutions the fixtures cannot discriminate, because no group has unequal thresholds or
  horizons across its layers.
* **F2** — the walk-evidence predicate written for A1 **omits `duration_timed` and
  `route_identified`**, so a row whose only entry is one of those loses its evidence exactly as
  before; and it reads `witness_within_15min=untested`, which the README explicitly permits for
  "I did not try", as affirmative evidence that somebody walked.

**What it could and could not do.** Codex cannot start a process on this machine, so it replayed
both JavaScript harnesses inside `vm` contexts to a passing baseline — **79 conformance checks and
27 card checks** — and applied every mutation in memory. The JavaScript findings carry executed
witnesses; the Python findings are source-derived and say so.

**One finding is inherited, not new:** F8, `autoBench` wedging once the rolling window is full,
predates this work and was found while checking the adapter paths it was asked about.

**The report is reproduced verbatim below**, including the parts this project disagrees with.

---

**The repair closes the five original mutations, but the claimed class is still open.** I reproduced five additional worker corruptions that pass both suites, plus three rendering corruptions.

Baseline replay: **79 conformance checks and 27 card checks passed** in JavaScript VM contexts. All mutations were in memory; no files changed. I checked the reviewed implementation files against `50e3884`. **Python findings below are source-derived:** I could not execute Python, pytest, Git commands, or the benchmark process.

Findings are ranked by severity.

**F1 — High validation gap: reply correlation remains unauthenticated, and the fixtures do not discriminate criterion indexes.**

Locations: [worker_conformance.mjs:309](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/worker_conformance.mjs:309), [worker.js:656](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/worker.js:656), [worker.js:684](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/worker.js:684).

Each mutation below was confined to `handleExplainAt`. **Each independently passed all 79 conformance checks and all 27 card checks.**

| Executed corruption | Consequence |
|---|---|
| Reply with `seq: -1` | The page rejects every explanation after a normal compute. |
| Reply with `reqId: 0` | Every legitimate inspector request is rejected. |
| Reply with `row: 0, col: 0` | Correct answers are labelled as belonging to cell `(0,0)`. |
| Read `state.lastThresholds[0]` for every criterion | Later criteria can receive another criterion’s threshold and outcome. |
| Report `horizonS: horizons[0]` | Later criteria can disclose another layer’s horizon. |

The first three fields are not asserted. The last two expectations are indexed correctly, but the fixtures do not supply unequal values that expose these substitutions.

A concrete threshold counterexample is two OK layers holding 12 minutes, with limits `[5,15]`. Compute correctly excludes the cell: first criterion FAIL, second PASS. The surviving threshold mutation explains both as FAIL at limit 5.

**Fix:** assert the complete response envelope, vary request IDs and compute sequences, and add three-layer cases with unequal thresholds/horizons and a disabled middle layer. Feed actual worker replies through the inspector; the suites currently test those components separately.

**F2 — High: the evidence predicate still loses walks, and also invents them.**

Locations: [admissible.py:165](C:/Users/arikt/documents/github/distanceFinder/v2/locfinder/measure/admissible.py:165), [admissible.py:238](C:/Users/arikt/documents/github/distanceFinder/v2/locfinder/measure/admissible.py:238), [admissible.py:381](C:/Users/arikt/documents/github/distanceFinder/v2/locfinder/measure/admissible.py:381).

**Source-derived witnesses:** take a normal published row with `encoded_minutes=14`, clear its observation fields, then fill exactly one:

| Sole observation | Result implied by source |
|---|---|
| `duration_timed=yes` | `walked=0`, `planned=1`, no refusal |
| `route_identified=yes` | Same |
| `witness_within_15min=untested` | Refused as a walk; `no_admissible_observation=True` |

The first two answers concern an actual duration or route, but neither field appears in `EVIDENCE_FIELDS`. Their evidence disappears before admissibility checks run.

The third reverses the error. The README explicitly permits `untested` when the owner did not try. `_blank` treats that answer as affirmative evidence that somebody walked.

The three buckets are exhaustive mechanically; **the predicate assigning rows to them is not semantically sound**.

**Fix:** represent whether a walk happened explicitly, preserve contradictory evidence, and interpret categorical observation values individually. At minimum, cover the two omitted self-report fields and distinguish `untested` from an observed yes/no.

**F3 — Medium: 600 metres establishes proximity, not destination identity.**

Locations: [admissible.py:56](C:/Users/arikt/documents/github/distanceFinder/v2/locfinder/measure/admissible.py:56), [admissible.py:288](C:/Users/arikt/documents/github/distanceFinder/v2/locfinder/measure/admissible.py:288), [admissible.py:316](C:/Users/arikt/documents/github/distanceFinder/v2/locfinder/measure/admissible.py:316).

**Source-derived counterexample:** two genuinely different shops called Food Lion occupy `(-79,35.9)` and `(-78.997,35.9)`, approximately **270.22 m apart**, and snap to different nodes. Select the first; truthfully walk to and record the second. The name belongs to the permitted set and the distance is below 600 m, so the identity checks accept the wrong journey.

The acquisition reasoning proves only a necessary geometric condition. The actual snapping code caps **projected centroid-to-node distance** at 300 m; `fetch_places.py` itself does not apply that cap. Being within the resulting envelope cannot establish membership in the selected node’s place set.

The opposite error is also possible because the README asks for an **arrival pin at the door**, while recovery stores a **place centroid**. Construct two permitted places with centroids 290 m on opposite sides of their shared node. A legitimate entrance 40 m beyond the second centroid is 620 m from the selected centroid and is refused. Both acquisition distances remain below 300 m.

The real side table preserves GERS IDs and node membership, but the scorer discards both. It also does not justify calling two same-name records “a second shop”: for example, ordinal 127 contains two Food Lion IDs on node 219490. Separate records do not establish separate physical shops.

**Fix:** carry permitted destination identities and their individual locations or footprints into the sheet/scorer. Match arrival evidence to a permitted member. Retain 600 m, if useful, as a coarse plausibility check.

I did not establish that today’s real alternatives contain a greater-than-600-m entrance separation; that witness is a source-valid construction.

**F4 — Medium: moving between cells still renders a superseded explanation.**

Locations: [card.js:223](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/card.js:223), [card.js:257](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/card.js:257), [card_selftest.mjs:513](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/card_selftest.mjs:513).

**Executed sequence:**

```text
computePainted(1, 1)
pointerAt(1, 1)                 → request 1
pointerAt(2, 2)                 → queued
reply({reqId: 1, seq: 1})       → render: true; sends request 2
```

The pointer is over `(2,2)`, but the page renders `(1,1)` until the next round trip completes. `pointerGen` changes only when leaving the raster/map. A newer inspected cell does not invalidate the earlier reply.

The regression test explicitly asserts that the first reply renders, thereby preserving this failure.

**Fix:** validate the reply against the current inspected position, or advance a position generation when the cell changes. Continue sending the queued request without rendering a different cell’s answer.

**F5 — Medium: an explanation error permanently wedges the inspector.**

Locations: [app.js:308](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/app.js:308), [card.js:225](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/card.js:225), [card.js:250](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/card.js:250).

**Executed through the actual app adapter with worker/DOM stubs:**

1. Paint compute 1 and send an explanation.
2. Deliver a worker `error` for that request.
3. Leave and re-enter the map.
4. Start and paint compute 2.

The error handler displays a banner but never settles the inspector request. Afterwards:

```text
pending = true
queued = newest position
computePainted(...) returns null
explanation requests posted = 1
```

Every subsequent hover and repaint queues behind a reply that will never arrive. Leaving, resetting criteria, and successful computes do not recover it.

**Fix:** correlate worker errors with request type/ID and add an inspector failure transition that settles or invalidates the affected request. Show a failure state and permit subsequent requests. Anonymous worker errors currently make selective recovery difficult.

**F6 — Medium validation gap: the new rendering checks still accept materially false cards.**

Locations: [card_selftest.mjs:327](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/card_selftest.mjs:327), [card_selftest.mjs:398](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/card_selftest.mjs:398), [card.js:135](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/card.js:135).

Each following rendering mutation independently passed **all 27 card checks**:

| Executed mutation | Accepted false presentation |
|---|---|
| Replace displayed outcome text with literal `PASS` | A FAIL criterion displays PASS beside “30 min · your limit 10 min”. |
| Replace every displayed threshold with `15` | Limits from actual replies are silently falsified. |
| For multi-criterion cards, retain only the first destination place | Shared-node alternatives disappear. |

The fixture-driven checks inspect disclosure presence and the **first** destination name. They do not authenticate each block’s outcome, limit, or complete place set.

**Fix:** assert each criterion block’s outcome, time/bound, threshold, cause, restriction disclosure, and every destination member, including absence of another criterion’s content.

**F7 — Medium: existing owner sheets have no observation-preserving migration path.**

Locations: [score_walked_audit.py:153](C:/Users/arikt/documents/github/distanceFinder/v2/scripts/score_walked_audit.py:153), [audit_recommendations.py:729](C:/Users/arikt/documents/github/distanceFinder/v2/scripts/audit_recommendations.py:729).

**Source-derived witness:** an owner’s filled copy from the parent commit lacks the newly required arrival coordinates and `route_identified`. `read_sheet` refuses it and instructs the owner to **regenerate** using `audit_recommendations.py`.

That generator initializes every owner column to blank. Its overwrite guard initially prevents damage; using `--force` then erases observations. Regenerating also does not perform destination recovery.

The committed edits themselves were sound: comparing all four CSVs against the parent showed **no changed pre-existing cells, no removed columns, unchanged row counts, and consistent widths**. This commit added **three columns**, not two: longitude, latitude, and route identification.

**Fix:** provide an idempotent schema migration that adds missing columns while preserving every existing value and custom column, with backup/output-copy behavior. Missing observations must remain blank for the owner to supply.

**F8 — Medium, inherited: auto-bench cannot finish once the rolling window is full.**

Locations: [app.js:785](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/app.js:785), [app.js:621](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/app.js:621).

**Executed witness:** begin with 20 timing samples and call `autoBench`. Its first compute completes, but the result handler caps the window at 20. `waitForNextResult` waits for `window.length > 20` forever. The benchmark button stays disabled.

Even starting with the normal initial sample, the benchmark eventually reaches this condition. `resetAll` during a wait can also invalidate the captured length.

This defect predates `50e3884`; it was found while checking the requested adapter paths.

**Fix:** await completion of the specific compute sequence, rather than growth of a capped/resettable statistics array.

**F9 — Low: arrival-coordinate validation accepts impossible latitudes.**

Locations: [admissible.py:105](C:/Users/arikt/documents/github/distanceFinder/v2/locfinder/measure/admissible.py:105), [admissible.py:315](C:/Users/arikt/documents/github/distanceFinder/v2/locfinder/measure/admissible.py:315).

**Source-derived witness:** change the good fixture’s arrival latitude from `35.910405` to **`395.910405`**, retaining longitude `-79.065417`.

The trigonometric calculation wraps through 360 degrees and produces essentially zero distance. The coordinate check accepts the impossible latitude; the remaining good fields make the record admissible. JavaScript evaluation of the same formula produced approximately `1.56e-9 m`; Python was not executed.

**Fix:** validate finite numeric longitude/latitude and geographic ranges before calculating distance.

**F10 — Low measurement overclaim: the caching question is still declared closed without the necessary scope.**

Location: [bench_explain.mjs:122](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/bench_explain.mjs:122), also its “floor” claim at line 10.

The output still concludes:

> “the HANDLER is not the cost”

and declares the caching question answered.

**Method witness:** the benchmark measures one warmed desktop runtime, one layer, and no concurrent compute. Handler work grows with enabled layers and destination payloads. It also has no end-to-end cost breakdown establishing which component dominates. A measured desktop duration is not a universal numerical floor for another browser/runtime.

**Fix:** state the supported local conclusion: recomputation appears inexpensive for this one-layer bundle on the measured runtime, so this measurement does not currently justify caching. Keep broader layer-count/device/concurrency questions open.

**Disposition of the six claims**

| Claim | Verdict |
|---|---|
| **1. Every explanation field is authenticated; the corruption class is closed** | **Fails.** F1 supplies five additional surviving mutations. The criterion-byte comparisons are substantially improved. |
| **2. Stale replies cannot render and legitimate replies cannot become wedged** | **Fails.** F4 and F5. The original compute-change and pointer-exit witnesses are repaired. |
| **3. Walks cannot disappear from the refusal record** | **Fails.** F2. Bucket coverage is exhaustive, but “walk happened” remains incorrectly inferred. |
| **4. The destination check establishes identity** | **Fails.** F3; F9 adds malformed-coordinate acceptance. |
| **5. Per-criterion destination disclosure is the right rule** | **Survives as a defensible policy, not an established usability result.** The combined EXCLUDED headline and criterion outcome provide context. Household interpretation evidence is still missing. |
| **6. The measurement statements are now honest** | **Mixed.** The 0.388-row attribution accurately represents pass 51 and correctly distinguishes analysis from screen measurement. The benchmark conclusion remains overstated: F10. |

For claim 5, suppression is also defensible on a recommendation surface. It must have an explicit state and truthful wording, for example: **“Destination names are hidden because this location does not meet all your criteria.”** With disclosure retained, a useful clarification is: **“These destinations explain individual criteria; this location does not meet all your criteria.”** Restoring a false “does not disclose” sentence would not resolve that policy question.

**Disposition of the suspicions and remaining checks**

- **`withhold_flags`: settled in favor of the current expectations.** `plainManifest` removes both disclosures, so both false expectations are correct for that worker. The enabled oracle/table index walks and bounded/`VALUE_NONE` rules survived inspection. This does not rescue the missing envelope assertions or nondiscriminating fixtures.
- **Self-report inconsistencies:** `route_identified=yes` with blank `route_followed` is already refused when the row reaches the checks. F2 shows how the early walk classification bypasses them. Round seconds alone cannot establish that timing was fabricated.
- **CSV insertion:** no committed data loss or column shift found. The missing migration and regeneration instruction are the defects.
- **`minutesText(1)`:** mathematically safe but unhelpful. “No useful whole-minute lower bound” would convey more. **Zero is reachable:** I initialized an OFF_NETWORK cell with value 0 through the real worker and received an UNKNOWN explanation carrying that bound. Negative values are not reachable through the byte plane.
- **Real multi-criterion data:** a second shipped layer is unnecessary for stronger tests. Separate test criteria can use the actual published planes with unequal thresholds. A distinct 200 m candidate surface triple also exists and is listed in the exporter. Neither substitutes for evidence from two independently meaningful production layers.
- **Visitation guard:** **survives the original attack.** Skipping real-window cell 5166 now fails all 18 window cases.
- **The specifically requested Python rows:** route-only evidence is refused; `"0"` seconds is preserved as evidence and can score when otherwise admissible; seconds without a published minute produces an explicit refusal; `destination_qualifies=no` alone produces a refusal. `E3Result.walked` counts scored observations, so refused walks correctly remain outside that count. These conclusions were inspected in source, not executed.
