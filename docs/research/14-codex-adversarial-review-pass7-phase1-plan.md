# Codex adversarial review — Phase 1 plan, pass 7

**Verdict:** revise before execution. A3 cannot establish decision 12 as written; A1 specifies distinctions the builders currently cannot produce; and the supposedly exact expansion reconstruction has an executed counterexample.

**Method:** reviewed the requested plan, context and six implementation files, plus relevant callers, tests and stored artifacts. Ran 35 targeted tests successfully with bytecode, cache and capture writes disabled. Executed in-memory probes; made no routing requests or Google validation calls. Branch: `v2-rethink`. Existing workspace changes were preserved. `verify_two_weight.py` changed externally during the review; conclusions about it refer to the inspected snapshot.

References to **Plan** below mean `docs/plans/2026-11-03-phase1-plan.md`.

## Critical findings

### C1 — A3 can pass while the product fails decision 12

**Fault:** Plan A3, “Pipeline + grid must pass,” “Model error is reported, not gated”; assumptions table.

Same-engine agreement measures construction consistency, not household travel-time accuracy. Memo §0 correction 9 explicitly withdraws the earlier identification of these two. A perfect reconstruction of a sufficiently inaccurate model passes A3 automatically.

Separating engineering and model results is sound. Calling that engineering gate decision 12 is not. The assumptions table compounds this by requiring both Google disagreement **and** confirmation from a few owner journeys before weakening the claim. Untaken or inconclusive journeys become an escape hatch.

**Smallest fix:** name separate outcomes: construction PASS/FAIL and real-world accuracy supported/failed/unverified. Report final encoded-surface versus independent reference error directly. Keep decision 12 unverified until appropriate evidence supports it; a provisional labelled release is a separate product decision.

### C2 — The proposed sample misses important failures and has no defined precision

**Fault:** Plan A3 sampling and reporting.

Selecting only cells near the pipeline’s own encoded boundary excludes predicted-unreachable cells and severely misplaced boundaries. A pipeline that wrongly deletes a neighbourhood never samples that neighbourhood. This drops explicit requirements from pass 5’s “What to measure next.”

“Within one cell-step” is undefined: spatial adjacency and one encoding increment produce different populations. There are no declared anchor, mode, category, access, urbanity or temporal allocations. A building mask alone supplies none of those strata.

The sample size is **480 cell observations per configuration**: four thresholds × two sides × 60. It is not necessarily 480 distinct locations or independent observations.

Sixty predicted-inside cells can estimate contamination of that selected band. They do not automatically provide 60 reference-negative observations for `FP/(FP+TN)`. Equal sampling on predicted sides also needs population weights for population rates.

Even with 60 independent eligible observations and zero failures, the one-sided 95% upper bound is **4.87%**, not zero. About **385 observations per rate denominator** gives a worst-case normal-approximation margin of five percentage points; clustering increases requirements. There is no universally correct N without an estimand and precision target.

**Smallest fix:** predeclare the sampling frame, band definition, allocations, weights, confidence intervals and missing-data treatment. Add an independent residential sample, reference-assisted boundary screening and predicted-missing strata. Treat 60 per side as a pilot unless its uncertainty meets a stated objective.

### C3 — The three-way decomposition does not identify three separate errors

**Fault:** Plan A3 component table and 100/200 m comparison.

“Pipeline” already includes encoding; “grid” includes encoding again. Comparing exact routes at each grid’s own centres does not measure within-cell error at homes or clicked locations.

The grids are not even nested as currently constructed. Executed `TRIANGLE.grid()` results:

| Resolution | Origin x/y | Dimensions |
|---|---|---|
| 100 m | 661900 / 4003500 | 643 × 514 |
| 200 m | 661800 / 4003600 | 322 × 258 |

Different samples on those grids confound resolution, alignment and location. Valhalla-versus-Google differences also include network, snapping, entrance and route-choice differences; they cannot be attributed solely to static speeds versus traffic.

**Smallest fix:** use the same residential coordinates and destination entrances throughout. Retain transient paired values for exact routing at the location, float surface at its cell centre, encoded surface and independent prediction. Report signed paired differences and total disagreement; do not add component medians or percentiles. Call the independent comparison engine disagreement unless causes are controlled.

### C4 — A1 cannot obtain its sentinel meanings from the current pipeline

**Fault:** Plan A1 status table; B2 algebra.

`layer.py:29` represents unavailable results as infinity. `snap.py:183` converts excessive access distance and final cutoff violations to the same infinity. A bounded expansion cannot generally distinguish “no path exists” from “not reached within this search horizon.”

Changing `encode_minutes` cannot recover those lost causes. “Beyond cutoff” must therefore not become “searched, no path exists.” Nor does being farther than 200 m from a candidate edge prove that a point lies outside routing coverage.

B2 also needs an explicit precedence rule: one known failure plus one unknown criterion means the intersection is **excluded**, with incomplete information attached. It is not an unknown eligibility result.

**Smallest fix:** define status production and the complete algebra before allocating codes. Carry reason/status information from acquisition and routing through snapping. Use “not reached within built horizon” where stronger classification is unavailable. Specify that thresholds beyond the built cutoff require another computation.

### C5 — A2 assumes exact reconstruction that accepted inputs can falsify

**Fault:** Plan A2, “reconstructs endpoint times exactly”; `expansion.py:93`, `:112`, `:127`.

Executed two-edge fixture: destination at x=0; root geometry stored `[100,0] → [0,0]`, duration 100; successor `[100,0] → [200,0]`, duration 200, pointing to the root. The adapter assigns **zero seconds at x=100**, where the tree requires 100.

Missing predecessors also become invented zero-time roots (`near_t=0`). `test_unresolvable_predecessor_is_treated_as_a_root` explicitly enshrines that behaviour. Symmetric edge times and node-level merging further require validation for directional and turn-dependent costing; tree membership alone does not prove those reductions preserve it.

**Smallest fix:** pass anchor/root correlation information, distinguish the real root sentinel from missing features, and validate orientation, interior-anchor partial edges, one-ways and turn-dependent cases. Make those structural checks prerequisites to A2’s aggregate benchmark. Actual frequency in Valhalla payloads remains unmeasured.

## High findings

### H1 — A1 omits migration of writers, readers and existing artifacts

**Fault:** Plan A1 file list and pass criteria.

Legacy codes 251–254 are valid minute values; an executed encoding probe confirms that. Reinterpreting them as statuses corrupts old layers.

`grid.py:76` fixes GeoTIFF dtype to uint8. `layer.py:61` uses that profile. The exporter casts to uint8; `g3-render/worker.js:89` requires one byte per cell and `:144` recognises only one sentinel. A Python round-trip test cannot protect the browser.

**Smallest fix:** version the format, namespace/rebuild incompatible artifacts, reject unsupported manifests, update writer/exporter/Worker together, and test actual browser decoding. Define uint16 sentinel locations, byte order and length validation. Never interpolate categorical status codes during reprojection.

### H2 — The declared dependency graph contradicts the tasks

**Fault:** Plan sequencing, A1–A9 and B2.

A3 requires A4’s mask, so A4 is not independent. A1 freezes an encoding selected by A3, creating a freeze-before-selection cycle. B2’s truth table determines A1’s status requirements. A7’s date/deadline semantics determine transit metadata and cache identity.

A6 gates A7’s valid inputs. A9 gates any category whose endpoints it changes. A8 must benchmark the selected production endpoint. These dependencies do not prevent an early drive-only UI scaffold, but they do prevent treating the whole Stage B product as validated.

**Smallest fix:** distinguish provisional schema, candidate evaluation and final freeze. Move semantic design ahead of encoding; A4 ahead of A3; freshness ahead of transit validation. State feature-specific release gates instead of one Stage B start condition.

### H3 — Coverage and routability are still substituted for lawful access

**Fault:** Plan A4, A5, A7 and B8.

Pass 6’s open issue is whether recovered routes are lawful, not merely residential. A4 measures buildings and inspects missing regions; it does not audit newly included routes through restricted land.

`access.py` retains finite penalties, which discourage but permit through-routing. `snap.py:183` adds a straight-line access leg without a barrier test. A5’s path-existence check can likewise approve the wrong direction or an illegal connector. An airport nudge can land across a fence while remaining geometrically close.

**Smallest fix:** add a selected-path and legal-connector audit, covering restricted endpoints versus through traffic, barriers, discarded components and both reachability directions. Reuse bounded legal snapping for anchors, category entrances and transit stops. Report unresolved eligibility as such.

### H4 — The name resolver and correction flow have no implementation task

**Fault:** Plan A5/B1.

Memo D4 explicitly says the metro-bounded name index, candidate chooser and correction flow are unbuilt. A5 starts with an already resolved anchor; B1 lists an API directory without implementing that prerequisite.

Census resolved none of the ten place-name queries. Routability cannot repair a workplace resolved to the wrong entity.

**Smallest fix:** add an explicit places-index and resolver task: source-native identity, search, metro bounds, ambiguity, candidate selection, pin correction and subsequent routability. Include the measured failed/remote-name cases.

### H5 — The one-anchor milestone never explicitly becomes the promised household product

**Fault:** Plan goal, B0–B3 and B8.

B1 ends with one workplace. No subsequent task explicitly requires two independent workplace constraints, deadlines and modes, or verifies their intersection.

Nearest-of-category routing is not interchangeable with two-workplace routing: `min(time_to_A,time_to_B)` accepts reaching either workplace. The goal requires each applicable per-anchor limit to hold. Nor do individually acceptable criterion error distributions establish accuracy of the final multi-criterion region.

**Smallest fix:** add a completion task for two workplace cards plus an amenity and airport criterion. Specify per-anchor AND semantics, category “any qualifying destination” semantics and mixed-grid alignment. Audit the combined region and false classifications directly; do not compose p90s by arithmetic.

### H6 — On-demand correctness and cache identity are unspecified

**Fault:** Plan architecture, A8 and B1.

`g2_anchor_bench.py:28` benchmarks polygon `/isochrone`; the proposed product needs an encoded grid. Earlier G1 results reject the raster approximation for threshold accuracy. Equal encoding does not establish equal surfaces.

Memo D1 also uses own-graph walking for precomputation and Valhalla for arbitrary anchors. Selecting a named destination through different interfaces can therefore visibly move its boundary.

The proposed cache key omits grid, source/profile versions, direction and transit date/deadline. Coordinate rounding can move an anchor across a divided road or barrier.

**Smallest fix:** specify the production grid endpoint and paired online/precomputed consistency tests. Include semantic and build identity in cache keys. Bound and measure coordinate approximation. Benchmark complete cache misses through encoding and transfer, as well as hits.

### H7 — A manifest does not implement reproducible or atomic refreshes

**Fault:** Plan A1/A6; no build/publication task.

The plan lacks an orchestrator for source acquisition → graph/index preparation → layers → validation → publication. Acquisition dates do not identify exact inputs or invalidate dependent outputs.

Concrete existing hazard: `fetch_places.py:31` reuses an existing raw file regardless of requested release; `partition_by_licence` can then label it with the requested release. `g1_expansion_primitive.py:100` similarly loads metro-less comparison artifacts without a full identity check.

**Smallest fix:** add a build command with input hashes/releases, code/profile/category versions and dependency fingerprints. Publish immutable bundles, switch the manifest atomically after checks, retain rollback and invalidate caches. Add lightweight health, stale-data, failure, memory and request-cost monitoring for the VPS.

### H8 — Transit’s query identity and expired-feed policy remain unresolved

**Fault:** Plan architecture, A6/A7.

A static `(mode, category)` identity cannot describe a scheduled transit surface. A7 must define service date, timezone, deadline, window and duration semantics before those fields can be omitted from A1 and cache design.

A6 says Duke’s stale feed makes the build refuse transit output. The adopted seven-feed experiment already includes that stale feed. The plan therefore needs an explicit choice between blocking all transit and excluding Duke with a partial-coverage declaration; it cannot quietly do both.

**Smallest fix:** freeze transit query identity and coverage policy first. Validate active service by required feed/date, including exceptions, overnight service and DST. Test cell-to-stop composition against full itineraries, including non-nearest stops, transfers and final egress. Ten timetable checks are a useful schedule check, not observed reliability validation.

### H9 — A9’s inferred entrances and recall-only gate admit wrong destinations

**Fault:** Plan A9.

A walk edge intersecting a park boundary can be fenced, private or grade-separated; it need not be an entrance. The current category selectors test taxonomy/tags, not opening status, public eligibility or usable access (`places/categories.py`).

Recall against county inventories alone cannot detect closed venues or false category matches. County inventories are not automatically complete across municipal, state and other eligible parks.

**Smallest fix:** distinguish verified entrances from inferred candidates, test barriers/access and audit both precision and recall. Publish user-visible category definitions and source/eligibility rules. Apply equivalent checks to groceries and playgrounds before exposing their layers.

### H10 — Several “pass criteria” cannot fail meaningfully

**Fault:** Plan A2/A3/A8/B8 and owner session.

A8 requires reporting throughput and cache hit rate but specifies no target workload, minimum throughput, latency, failure or memory limits. Any completed run can satisfy it.

A2’s zero observed false inclusions is sample-dependent and may conflict with harmless symmetric interpolation error. Its ±15-second median is also not proof that reconstruction is correct.

B8’s golden-region “tolerance” has no metric or baseline policy. A legitimate road/source change can move a boundary substantially; an erroneous baseline can remain perfectly stable. Owner G5a only schedules sessions, while synthesis §6 requires them before heavy architecture work.

**Smallest fix:** predeclare measurable outcomes, scope, missing-stratum rules and permitted baseline changes. Separate frozen-input regression tests from source-refresh change review and independent accuracy tests. Complete and record owner checks, including phone G3, before claiming their respective gates passed.

### H11 — Source enumeration alone misses publication obligations

**Fault:** Plan A1/A4/A9 and missing publication acceptance.

Memo D3 explicitly requires retaining validated per-source obligations; `licence.py` still returns only the first resolved licence. A1 names sources without requiring notices, attribution or publication partition checks.

The registry currently covers Overture **Places**, not the new Buildings acquisition or county inventories. An allowlisted licence string does not establish that a new dataset’s metadata and obligations have been inspected.

**Smallest fix:** add registry entries and validated obligation sets for new inputs; carry required notices into publication. Test that restricted-source identifiers/data cannot enter the ODbL bundle. Keep OSM contribution evidence independent of Overture and Google.

## Medium findings

### M1 — Buildings are a better diagnostic denominator, not a measured home population

**Fault:** Plan A4, “homes are” the denominator and “product’s real coverage number.”

Overture building counts include garages, commercial buildings and outbuildings; one apartment building may contain many households. Weighting a cell-centre result by footprints also does not test the building’s accessible entrance.

**Evidence:** the saved Triangle walk array has **253,679 finite of 330,502 cells: 76.7557% coverage, 23.2443% missing**. This supports the approximate 23% statement for this grocery/walk build, not every walk query.

**Smallest fix:** call the new result building-weighted coverage; retain cell coverage for spatial diagnostics. Add residential classification and entrance samples with explicit unknown classifications before calling it home coverage.

### M2 — A4 assumes a preserved paired baseline that is not demonstrated

**Fault:** Plan A4, “preserved before/after access-fix arrays”; sensitivity-table explanation.

The inspected layer inventory contains a current Triangle walk array and an older slice array, not an identified matched before/after pair. Pass 6 explicitly said the paired before-array was unavailable.

The sensitivity discrepancy also has a concrete implementation cause: the inspected sweep calls `cell_seconds_from_arrival` without `node_cost` or a final `cutoff_s`, unlike the corrected production builder. Rerunning unchanged code repeats the mismatch.

**Smallest fix:** regenerate both policies on frozen identical inputs, preserving gross missing→finite and finite→missing transitions and endpoint changes. Make the sweep call the production builder. Do not subtract rounded percentages or compare different metros.

### M3 — B7 quotes superseded leakage figures

**Fault:** Plan B7: median 3.12×, maximum 5.45×, up to four parts.

`g4-listings.md` labels itself superseded. Its replacement, `g4-listings-triangle.md:28`, reports **median 3.47× and maximum 6.50×**; row 1 already has five parts.

These are experimental-region statistics, not the leakage of the user’s current region.

**Smallest fix:** cite the replacement and compute leakage for the actual rendered region and outgoing portal bounds. Keep historical aggregate figures in research notes.

### M4 — Storage arguments mix worst-case arithmetic with measured accuracy

**Fault:** Plan A1 heading and encoding choices.

Whole-minute rounding can contribute up to 30 seconds, half the **median allowance at T=10**. That is a correct worst-case bound, not evidence that it routinely spends half the product’s error budget.

Half-minutes still introduce rounding; integer seconds are not exact representations of fractional-second inputs. A 125-minute range exceeds the current 120-minute default, but supported thresholds, transit horizons and relaxation limits are not specified.

**Smallest fix:** define the supported maximum duration and rounding semantics first. Measure encoded threshold classifications, compressed transfer size and phone latency for candidates. State bounds as bounds, and define reserved code 254.

### M5 — Several recommendations need narrower evidence labels

**Fault:** Plan architecture, dropped work and owner-session claims.

- Dropping calibration of an unused own-bike fallback is reasonable. It does **not** validate Valhalla bike layers; the independent spot check is drive-only.
- The architecture names Valhalla/MOTIS while A4 and the dropped-work explanation retain own-graph walking. State the engine per mode explicitly.
- Cameron Village supports testing a direct-walk alternative. “No itinerary” alone does not independently prove its precise cause; define whether transit mode permits walk-only journeys and any walk limit.
- One vertical slice before breadth is a sensible implementation prior, not an experimentally established ordering theorem.
- Five to eight hand-timed trips provide valuable independent observations. They cannot certify a boundary p90, and are not the only possible ground-truth source; the repository itself lists probe archives.

**Smallest fix:** label these choices as measured, inherited owner decisions or priors, with their actual scope.

## Ranked: what to do first

1. **Fix the semantic specification:** B2 truth table, per-anchor household semantics, cutoff/status provenance, per-mode engines and transit query identity. These determine A1.
2. **Repair and test the primitive, then run A2.** Use the production adapter, fresh identified inputs and structural counterexamples. A2’s float measurement does not require final encoding.
3. **Build the minimal resolver/legal snapping path and A4 audit frame.** Preserve paired access-policy artifacts; audit legal connectors and recovered routes.
4. **Evaluate candidate grids/encodings on matched locations; run redesigned A3.** Separate construction consistency, independent disagreement and unverified real-world accuracy. Freeze A1 afterward.
5. **Add reproducible builds, invalidation and atomic publication.** Bring A6 into that path; place publication obligations alongside it.
6. **Build B1’s narrow drive slice and benchmark its actual on-demand endpoint.** Finish phone G3 and owner interaction checks before broadening.
7. **Add two-anchor algebra and selected validated categories.** A9 gates affected categories; A6 and A7 gate transit. Finish explanations, failure states, sharing and legal listings handoff.
8. **Run scoped release acceptance.** Include combined-region correctness, online/precomputed consistency and explicit unresolved accuracy claims.

This permits cheap UI integration early while preventing it from freezing the semantics the measurement still needs to decide.

## What I could not verify

- Corrected expansion accuracy on real Valhalla payloads, including directional/turn-state behaviour and root correlation.
- Real-world boundary accuracy, lawful residential recovery, representative cache reuse, phone performance and joint VPS memory peaks.
- Current county inventory completeness, new dataset obligations or actual Google validation charges.
- A matched preserved before-array; none was identified in the inspected inventory.
- Results of concurrent edits to `verify_two_weight.py`; the script changed during review, and the inspected report still contained historical FAIL verdicts.
- File delivery: filesystem permissions prevented creating `docs/research/14-codex-adversarial-review-pass7-phase1-plan.md`.

