# Codex Adversarial Review - Phase 0 Decisions (Pass 4)

Date: 2026-11-03 | Model: GPT-6 (Codex) | Method: ordered review of owner decisions, memo, cited evidence, implementation/tests/Valhalla infrastructure, then pass 3; in-memory recomputation from saved arrays, matrix/anchor/transit/geocoding JSON, listings GeoJSON, Overture Parquet and GTFS calendars; 46 existing tests executed successfully with bytecode/cache writing disabled. No experiments regenerated. WSL inspection was denied; live container state was not verified.

## Verdict

- **Safe to begin a reversible Phase 1 prototype, unsafe to treat the advertised accuracy or full architecture as established.** D1 is a defensible provisional engineering choice; disagreement with its reference does not demonstrate real-world accuracy.
- **D2 is weakest as a product capability decision.** MOTIS demonstrates scheduled point routing and stop reachability, not an independently validated home-origin arrival surface. The valid comparison contains 10 pairs, not 11.
- The production category-layer primitive has an unresolved failed equivalence check: multi-location versus per-location rasters differ by up to 27.25 minutes. That omission matters more than the claimed one-second build.
- G2 is correctly pending, but the memo omits that its measured concurrency-8 slice latency already exceeds both targets. NC feasibility is not its only outstanding problem.
- D3 has real licence-enforcement improvements, including rejection of unknown later sources. Zero rejected rows is reproducible; coverage quality and mixed-source obligation handling remain incomplete.
- D4 and D6 are reasonable directions with incomplete product flows; D5 is an unvalidated discretization choice; D7 is a sound requirement awaiting enforcement.
- “Everything a machine can decide alone is decided” is false. Raster consistency, independent boundary tests, licence provenance, transit access, contaminated fixtures and isolated performance checks remain machine-addressable.

## Findings

| id | severity | decision or file | issue | why it matters | recommended action | confidence |
|---|---|---|---|---|---|---|
| H1 | High | D1/D5; g1-routing.md | Multi-location verification reports 1,635 s maximum difference and 626 one-sided cells. | Fast adopted layer construction has no established equivalence to nearest-destination routing. | Compare batched/single rasters with exact matrices on a common grid before accepting method A. | High |
| H2 | High | D1; g1_matrix_compare.py | Reference disagreement is called accuracy failure; sampling uses the tested model; 25-minute evidence has four cells. | Neither engine meets an independently measured owner accuracy gate. | Use independent, representative OD truth and reference-defined boundary samples. | High |
| H3 | High | D2; transit_compare.py | Ten valid matching pairs are described as 11; stop output is promoted to a cell surface. | Transit gate passes before its main product operation exists. | Correct denominator; build and independently validate stop-to-cell arrival composition. | High |
| H4 | High | D1/G2; g2_anchor_bench.py | Loaded p95 is 1.363/2.303 s; HTTP 200 defines success even for invalid anchors. | Friendly serial latency obscures failed load targets and semantic failures. | Separate validity from transport success; benchmark valid anchors under isolated and mixed load. | High |
| H5 | High | D5; grid.py | Source pixels and a 200 m target do not bound resampling, snapping or encoding error. | Decision 12 is a temporal boundary tolerance, not a pixel-size rule. | Measure exact-pair versus final encoded-surface classifications at several grid origins/resolutions. | High |
| H6 | High | D3/G6; categories.py | Source-count superiority substitutes for independent precision/recall and usable entrances. | More records can create more false nearby amenities. | Complete category inventories and access audit before adopting coverage claims. | High |
| H7 | High | D6; g4-listings.md | Six invalid-anchor regions remain; maximum leakage is 5.45, not approximately 3.9. | Generated device fixtures and memo arithmetic are contaminated. | Remove invalid fixtures, correct statistics and regenerate on buffered coverage. | High |
| H8 | High | G1/G6; acquisition and comparison | Pass-3 denominator/provenance fixes were only partly honored. | Repeat ingestion can mislabel releases; comparison still excludes missing boundary predictions from error quantiles. | Bind cached inputs to metadata and publish explicit, comparable confusion tables. | High |
| M1 | Medium | D1 cost claim | Cold Python graph preparation is compared with a resident tile server; edge-index timing is overwritten. | The claimed 30x architectural advantage is overstated. | Separate initialization, amortized category work, service build and resident memory. | High |
| M2 | Medium | D3; licence.py | Resolver validates every source but exports only the first licence; manifests are incompletely evidenced. | A scalar row licence cannot represent every source obligation. | Retain validated licence sets, field scope, attribution and manifest evidence. | High |
| M3 | Medium | D4/geocoding gate | Seven addresses fail, four matched errors exceed 250 m; local name resolver is untested. | Address/name entry is not a passed end-to-end contract. | Test independent addresses, ambiguous names, candidate selection and correction/failure flows. | High |
| M4 | Medium | D2/D7 resource and freshness claims | Idle slice memory is generalized; freshness is a recommendation, not an enforced gate. | Whole-service budget and future-date coverage remain unknown. | Sample import/query peaks and enforce service-window/source-age checks. | High |
| M5 | Medium | Gate accounting/sequencing | G3/G5a reports are absent; G5a entry HTML/protocol are not present in the inspected paths. | “Built” and “needs owner” overstate readiness; heavy builds can precede cheaper falsification. | Finish runnable fixtures/protocol and automate checks before scheduling sessions. | High for observed files |

## Detailed notes

### H1: the adopted raster primitive failed its own check

The memo quotes “category layer in 0.6–1.3 s” but omits `g1-routing.md`'s controlled-walk multi-location check: `cells_both=5011`, `one_sided=626`, `max_abs_diff_s=1635`, `frac_diff_gt_60s=0.0556775`. That is 27.25 minutes maximum difference, 5.57% of jointly finite cells differing by over a minute, and approximately 11.1% one-sided cells in their reachable union. This does not prove the multi-location routing algorithm is defective: per-request grid registration, raster construction and correlation can also differ. It does prove that equivalence was not established, and `verify_multi_location` merely records diagnostics without rejecting method A. Preserve original response rasters and compare both constructions against exact destination minima near relevant boundaries; demonstrate acceptable error before extrapolating its timing to all categories/modes.

### H2: engine disagreement, biased sampling and an unsupported commute inference

The saved drive matrix reproduces the signed median **-5.386 minutes**, with 302 finite comparisons among 304 sampled cells. Its supported bands have median absolute errors 3.243/5.223/8.110 minutes and p90 5.522/9.148/12.388 minutes at nominal thresholds 10/15/20, which supports the quoted percentages as engine disagreements. However, only 26/30/11 samples respectively lie in Valhalla's corresponding `[0.8T,1.2T]` boundary bands; the bands were selected using own-model times, and the 25-minute band has only four cells, none near Valhalla's 25-minute boundary. Unreachable own-model cells promised in the sampling docstring are never selected, and no completed walk/bike matrix artifacts exist. Omitted intersection penalties, nearest-node destinations without destination access time, unequal cutoffs and differing correlation policies make this an evaluation of particular implementations, not an isolated causal test of routing quality. Valhalla may be the cheaper-maintenance choice, but independent route/time checks or observed trips are required to claim the owner's accuracy tolerance; traffic-sensitive driving truth must be evaluated separately from static-model agreement.

### H3: transit passes a narrower test than the memo says

“All 11 valid in-slice origin/anchor pairs matched” contradicts `transit_compare.json`: five valid origins times two valid anchors equals **10**, all matching; 14 total answered pairs include four invalid-origin answers. Agreement between MOTIS deployments is useful configuration evidence, already honestly acknowledged in the memo, but shared engine behavior and unaligned feed/realtime versions cannot independently validate journey timing. The JSON saves only stop counts and summary durations, not one-to-all entries or itinerary legs sufficient to reproduce the claimed latest-departure semantics. A cell surface must compose legal cell-to-stop walking, boarding/transfer constraints and onward schedules, compare all useful stops, and preserve direct walk alternatives. `motis_plan` preferentially selects transit itineraries whenever any exist and does not explicitly enforce `endTime <= ARRIVE_DT`, so it is not a complete best-feasible-journey oracle. The generated limits recorded in `v2/data/motis/import.log` include `onetoall_max_travel_minutes: 90`; test cap behavior and distinguish beyond-horizon from unreachable, then hand-check published journeys, waiting/early-arrival slack and a clearly defined departure/deadline window.

### H4: measured load failure is missing from the decision

The memo's p95 **0.30/0.37 s** and “zero failures in 408 requests” are correct for the warm concurrency-1 group, not general serving performance. Recomputing the concurrency-8 rows gives **1.362679/2.302846 s**, exceeding the specified **0.8/2.0 s** targets by about 70%/15%; the named “cold” 25-minute p95 is 1.001 s. Cary, NC State and even the Jordan Lake test point south of the slice remain in aggregate rows, and `one()` calls any HTTP 200 successful without inspecting geometry, snapping distance or anchor validity. “Cold” merely means first benchmark pass, with no tile/process/cache reset, while the record lacks sufficient workload start/end telemetry to establish whether four matrix jobs overlapped the latency run. Contention on the two-vCPU container could inflate time and cache/memory measurements, but cannot be asserted as the explanation or used to erase this failed observation. Rerun isolated valid workloads and deliberate concurrent precompute/interactive workloads, measuring process RSS, cgroup/cache usage and semantic failures separately.

### H5: a coarser target grid does not solve the error budget

D5 cites “0.001° ... 0.002° ... re-centred per request”; the approximate 36°N conversions are arithmetically plausible, about 90x111 m and 180x223 m. The retained product TIFFs are already reprojected onto 100 m UTM cells, and `geotiff_to_grid_seconds` discards the original transform/dimensions, so these artifacts do not independently verify the original per-mode pixel-size claim or establish it as invariant across request extents. Nearest-neighbor reprojection samples different source locations for different requests; a fixed 200 m grid does not align those source grids or guarantee stable category/anchor intersections. A 200 m cell center is up to 141 m from a corner, source half-diagonals are approximately 143 m for the stated drive pixels, and a 100 m walk cell's 71 m corner offset alone corresponds to roughly 51 seconds at 1.4 m/s before barriers or access detours. Integer-minute encoding adds up to 30 seconds: 20% of a 2.5-minute tolerance at T=25 and 50% of a one-minute tolerance at T=10. D5 is a reasonable candidate resolution, but must pass an end-to-end temporal classification test including one-sided reachability, barriers and grid shifts.

### H6: counts do not establish amenity quality

“Overture leads on grocery (285 vs 146)” establishes selected-record abundance, not better coverage of usable grocery destinations. `categories.py` excludes farmers markets and OSM convenience stores, restricts schools to selected primary labels, excludes dog/skate parks, leaves trails without an OSM mapping, and does not select every public-transport platform tagging pattern fetched by acquisition. These choices can be defensible, but need explicit product meanings and inventory-based precision/recall rather than a generic place-base endorsement. Selectors do not screen operating status or public accessibility, and polygon-centroid proximity cannot establish an accessible park/playground entrance across fences or large sites. The memo honestly leaves parks unresolved, yet the same unfinished independent audit constrains other category choices, particularly the 515-versus-22 playground discrepancy. Define the source/category union, duplicate handling and entrance model before deriving trustworthy layers.

### H7: the slice correction did not propagate

D6 says “Twenty two-anchor regions” with leakage “up to ~3.9x”; the retained G4 table and GeoJSON have **5.45x** at region 10 and **4.65x** at region 8. IDs **2, 6, 8, 15, 16, 19** use Cary or NC State, explicitly invalidated by the transit correction, but remain unflagged in the device checklist and saved geometry. On rounded GeoJSON leakage values, the true median is **3.125** across all 20 and **3.06** across the 14 with valid anchors; the latter still has maximum **5.45**. The generator's reported 3.14 “median” selects the upper middle observation instead of averaging the middle two. Consequently the qualitative need to show our region is stronger than the memo says, but these are model-derived, denoised/generalized regions, not independently established exact geographic truth. Regenerate valid, buffered fixtures before interpreting device success or reusing them in interaction tests.

### H8: pass-3 acceptance conditions were weakened

`g1_compare.table` reports union reachability, but computes quantiles on `near_both` and false rates over global `union`/`ref_in` populations rather than the stated boundary sample. At T=25, the drive arrays reproduce **2,739 missing own predictions among 5,791 reference-boundary cells (47.3%)**, excluded from numerical error quantiles. Own cutoff is 120 minutes versus Valhalla's 60, with own cells restricted to 200 m network access, so global false-inclusion percentages mix cutoff/access policy with model differences and cannot serve as boundary accuracy estimates. Separately, `fetch_overture` returns any existing raw file without validating its release/bbox, then `partition_by_licence` labels it with the supplied release. The current `.state` file confirms the intended release and bbox, so this is a repeat-run provenance defect, not evidence today's dataset is mislabeled. Require cache metadata/hash validation and explicit boundary confusion denominators, with missing coverage treated as a gate outcome.

## Decision-by-decision audit

### D1 — Partly established

Adopt Valhalla provisionally for maintenance and capability reasons. Close the independent boundary-accuracy, multi-location consistency, loaded latency and NC feasibility gaps; do not claim that pending walk/bike results “can only strengthen” a decision. Warm reusable graph preparation could change the cost comparison: mode graph/CSR/edge-index preparation need not repeat for every category, while Valhalla tile build/server memory is outside its per-request timing. `build_layer_seconds` also overwrites the caller's measured edge-index construction time with near-zero reuse time.

### D2 — Partly established

MOTIS is a credible scheduled-transit candidate. Its surface, independent timetable checks, direct-walk alternatives, date/window contract, horizon behavior and resource peaks remain open. An 80 MiB idle slice is not a whole-NC deployment budget. The import logs preserve a MOTIS digest, but a reproducible pinned serving recipe and peak telemetry should accompany the decision.

### D3 — Partly established

Reprocessing every raw row yields zero rejections: **160,392 source entries**, all explicitly allowlisted (155,820 CDLA, 3,813 Apache, 759 CC0). The row-level counts sum correctly to 57,719; zero quarantine did not exercise manifest fallback on this dataset. The resolver iterates all entries, and the later-unknown-source counterexample correctly raises `UnknownLicence`, as its existing regression test requires. Preserve the full validated obligations rather than interpreting the first-source scalar as exhaustive; close independent category audits and reviewed manifest provenance.

### D4 — Partly established

Raw JSON reproduces Census **33/40**, **81.219 m** median error, four matched errors over 250 m and **0.0964 s** median latency; Nominatim reproduces **36/40**, zero median error and **0.3341 s**. This establishes a useful address-provider experiment, not a passed name-index or correction workflow. Test independent addresses and metro-bounded named-place candidates; define unsuccessful and suspicious matches explicitly. Provider-policy conclusions should retain their cited sources rather than being labeled experimentally proved.

### D5 — Not established

Keep 100/200 m as candidate resolutions, subject to final-surface accuracy and multi-resolution algebra/manifest tests. Every retained source product layer still uses the shared 100 m grid; a mixed-resolution implementation has not been demonstrated. Record source grids and measure resampling plus encoding error before freezing the contract.

### D6 — Partly established

Exact-region display and the owner-approved city/ZIP fallback are sound requirements. Bounded link behavior is unmeasured, leakage arithmetic needs correction, and invalid-anchor fixtures need replacement. URL serialization tests verify locally constructed strings, not portal support.

### D7 — Established as a requirement; implementation pending

Recomputed November 10 GTFS service counts exactly reproduce **1,310/526/1,238/2,486/870/692** active trips for the six non-Duke feeds and zero for Duke, whose calendar ends August 10, 2025. Acquisition still tolerates download failures and has no enforced freshness assertion. Check service on requested dates and exceptions, source age and required-agency completeness; Chapel Hill's calendar extending to 2099 shows why a distant end date alone cannot prove fresh schedules.

## Errors the memo did not report

Besides its disclosed stale-feed and out-of-slice incidents, the memo omits the failed multi-location check, two failed loaded-latency targets, transit **10-versus-11** denominator, six contaminated G4 fixtures, wrong maximum leakage, upper-middle “median,” missing destination access cost and overwritten edge-index timing. Anchor “success” counts hide validity failures, and the matrix sampler's promised unreachable stratum is absent. The source raster metadata and transit itinerary/stop payloads needed for independent replay are not retained. The “4 s/130 MB/80 MiB” MOTIS costs are reported observations without a corresponding complete resource-sampling series in the reviewed artifacts; they should not be treated as load peaks.

Pass 3 was substantively honored on taxonomy migration, repository-relative output paths, extracted GTFS mounting, UTC/arrive-by queries, endpoint NaNs, physical-edge matching, exploded OSM tags, accepted-only downstream artifacts, all-source licence validation, float comparisons, radius duplicate queries and a contour fallback. Access-rule tests improved, though restrictions and tied-edge/entrance behavior remain incomplete. Union diagnostics were added without closing missing-prediction gate semantics; controlled speeds did not equalize access/cutoffs; independent truth and early household validation remain outstanding. G3's exact dependency pins and real-data fixtures are improvements, but its report and G5a's report are absent; the inspected G5a directory contains shared scripts/styles/data without the advertised entry HTML or session protocol. Files changed concurrently during inspection, so these readiness statements describe the inspected snapshot, not work that might subsequently arrive.

## Cheapest risk reduction

1. **Validate the raster primitive on the existing slice.** Preserve raw single/batched GeoTIFFs; sample independently of own-model times around 10/25/45-minute reference boundaries; compare exact matrices, source rasters and encoded fixed grids, including missing predictions. Add a small independently checked legal-route/time set. This can falsify D1/D5 without an NC build.
2. **Build one complete inbound transit surface.** Use an in-slice anchor, fresh feeds and a defined deadline; compose legal street access and direct walking, then hand-check published timetable journeys and compare surface cells against point plans. Measure cap behavior, waiting and date/window sensitivity, with import and query memory peaks.
3. **Rerun clean interactive performance and fixture validation.** Remove invalid anchors, enforce snap/coverage checks, measure isolated concurrency 1/8 and deliberate matrix contention with timestamps/resource samples, and correct G4 outputs. Use the resulting valid fixtures for browser checks and household sessions while completing independent POI inventories.

Widen the routing extract with a buffer before rerunning southern anchors; keep evaluation bounds separate from routing-data bounds. Then perform the required NC build on intended hardware once primitive correctness is credible, before deployment commitment. Phase 1 must explicitly inherit the dropped own-graph pipeline's useful responsibilities: legal access and entrances, cutoff/nodata semantics, stable grid/version metadata, independent acceptance tests and full transit access composition. Removing the engine implementation does not remove those requirements.

## What is right

The measurements provide useful runnable artifacts and expose genuine problems instead of manufacturing a clean pass. Transposed Dijkstra, directed-edge tests and all-source rejection are solid improvements, with all 46 existing tests passing. G2 remains provisional, parks remain disputed, Transitous is explicitly identified as the same engine family, and device/household results are not invented. Keeping those honest distinctions while correcting the overclaims makes this a useful foundation for a constrained Phase 1.
