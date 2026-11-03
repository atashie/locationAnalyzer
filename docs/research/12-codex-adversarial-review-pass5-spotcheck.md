# Codex Adversarial Review - Engine Spot Check and Its Analysis (Pass 5)

Date: 2026-11-03 | Model: GPT-6 (Codex) | Method: read the requested decisions, spot check, G1 report, memo, seven code/test files and pass 4 in order; additionally inspected snapping/layer code. Recomputed rounded-table statistics and exact binomial calculations in memory; compared supplied unrounded summaries; ran all seven existing component tests successfully with bytecode/cache writes disabled (pytest warned that its timeout configuration was unsupported). No network calls or experiment reruns. Only this review file was created.

## Verdict

- **Valhalla remains a defensible provisional drive engine.** It models capabilities ours omits and agrees best with the selected future-morning prediction on these twelve pairs. This is stronger evidence for choosing an engine, not sufficient support for household boundary accuracy.
- The rounded headline statistics reproduce: signed median zero, median absolute difference one minute, p90 three minutes. Exact zero is a quantized sample statistic, not evidence of calibration.
- The claimed intersection/congestion decomposition is not identified. Its median arithmetic happens to work on rounded data; its causal explanation does not follow.
- Decision 12 remains untested: its denominator is the user's threshold, and its gates concern boundary errors, including p90 and false inclusion/exclusion. Named-place routes cannot validate the final encoded cell surface.
- **Do not adopt “typical weekday morning” as an established label.** One predicted Tuesday departure does not characterize weekday mornings or off-peak service.
- Component pruning fixes a plausible snap-target defect, but can discard valid local networks and does not guarantee directed reachability. Neither improved coverage nor airport-route regression coverage is demonstrated by these tests.
- Reporting repeats pass 4's promotion of narrow comparisons into product conclusions. There is also a direct retention contradiction: the repository and generator contain a complete Google table while claiming not to persist it. No Critical finding is necessary; multiple High findings block the stronger claims.

## Arithmetic audit

Minutes unless stated otherwise. Differences below use the supplied whole-minute values. For p90 I reproduced the script's eleventh absolute order statistic at n=12. “Rounded/unrounded” distinguishes quantization from an arithmetic error; unrounded observations were not supplied for independent recomputation.

| Statistic | Recomputed | Document value | Assessment |
|---|---|---|---|
| Valhalla minus traffic-aware: signed median / median absolute / p90 absolute | 0 / 1 / 3 | 0 / 1 / 3 | Agree |
| OSRM minus traffic-aware: same | -2.5 / 2.5 / 5 | -2.5 / 2.5 / 5 | Agree |
| Google static minus traffic-aware: same | -3 / 3 / 5 | -3 / 3 / 5 | Agree on rounded data; script signed median -2.7 |
| Ours minus traffic-aware: same | -6 / 6 / 9 | -6 / 6 / 9 | Agree on rounded data; script signed median -5.5, p90 reported 9.1 |
| Faster shares versus traffic-aware: Valhalla / OSRM / static / ours | 4/12 / 11/12 / 11/12 / 12/12 | 33% / 92% / 92% / 100% | Agree |
| Ours minus Valhalla: signed / absolute median / p90 | -7 / 7 / 9 | -7 / 7 / 9 | Agree |
| Ours minus OSRM: same | -4 / 4 / 6 | -4.1 / 4.1 / 5.7 | Rounded/unrounded |
| Valhalla minus OSRM: same | 3 / 3 / 5 | 2.9 / 2.9 / 5.6 | Rounded/unrounded |
| Ours minus Google static: same; faster share | -3 / 3 / 7; 11/12 | -2.9 / 2.9 / 7.9; 100% | Rounded/unrounded, including a rounded tie |
| Valhalla minus Google static: same; faster share | 4 / 4 / 6; 1/12 | 3.9 / 3.9 / 5.7; 25% | Rounded/unrounded, including two rounded ties |
| Strict ours < OSRM < Valhalla | 11/12; one OSRM–Valhalla tie | All twelve | Not established by printed precision |
| Median journey length: ours / Valhalla / OSRM / Google static / traffic-aware | 17.5 / 23 / 21 / 19.5 / 23.5 | “21-minute median journey” | Only OSRM has that median |
| Static-minus-ours median + traffic-minus-static median; total median | 3 + 3 = 6; 6 | Clean half-and-half split | Numerical coincidence, not causal evidence |
| Valhalla signed differences: negative / zero / positive; range | 4 / 3 / 5; -3 to +3 | Four faster; no full distribution | Additional diagnostic |
| Mean absolute difference: Valhalla / OSRM / Google static / ours | 1.25 / 2.83 / 3 / 6.50 | Not reported | Ranking survives this metric |
| RMSE: same engine order | 1.61 / 3.34 / 3.46 / 6.96 | Not reported | Ranking also survives tail weighting here |
| Valhalla bias: two-sided exact sign test, omitting ties | n=9, 4 negative, 5 positive; p=1.00 | Not reported | Cannot establish zero bias/equivalence |
| Distribution-free median interval, rounded Valhalla differences | [-1,+1], nominal coverage 96.14% | Not reported | Conditional iid calculation only |
| Paired absolute-error wins for Valhalla versus Google static | 8 wins, 2 ties, 2 losses; sign-test p=0.1094 | “matches … better” | Descriptively true; weak inferential sample |

The median interval uses order statistics 3 and 10; coverage is 1 - 2(1+12+66)/4096. Hand-picked, overlapping routes are not iid random draws, so neither interval nor test supplies population coverage for Triangle households. Pairwise rounding errors can approach one minute; the corresponding latent median interval could extend roughly another minute either way.

## Findings

| id | severity | claim or file | issue | why it matters | recommended action | confidence |
|---|---|---|---|---|---|---|
| H1 | High | Spot check; D1 update | Boundary tolerance replaced by pooled journey agreement | Neither threshold gate nor final surface is tested | Stratify residential boundary cells by T; include missingness and classifications | High |
| H2 | High | “calibrated to morning traffic”; proposed label | Predicted one-hour sample becomes a temporal product promise | Misstates what users can rely on at other times | Retain explicit static-estimate label; validate multiple periods | High |
| H3 | High | “splits cleanly in half” | Uncontrolled engine differences attributed to intersections/congestion | Misstates fixability and expected improvement | Withdraw attribution; perform same-engine penalty ablation | High |
| H4 | High | Spot-check design; routing code | Named anchors and nearest nodes bypass product geometry | Legal access, snapping and representation errors remain unknown | Compare full cell-to-entrance pipeline with references | High |
| H5 | High | Retention statements; spotcheck_engines.py | Complete Google table persisted despite explicit prohibition | Claimed evidence discipline is false and reruns repeat it | Remove persistence in a separate authorized correction; retain permitted aggregates | High |
| H6 | High | largest_component; coverage inference | Largest weak component is substituted for valid reachable networks | Valid routes can disappear or be replaced with illegal access | Use bounded legal candidate snaps; audit lost networks and coverage transitions | High |
| M1 | Medium | g1_matrix_compare.py; _common.py | Reader ignores metro-aware layer_path | Proposed widened rerun can use slice data with Triangle coordinates | Resolve artifacts through common helper; validate grid/metro metadata | High |
| M2 | Medium | Uncertainty and reference provenance | Quantized small-sample agreement called calibration; OSRM deployment uncontrolled | Precision and independent corroboration overstated | Report paired distributions, provenance and conditional uncertainty | High |
| M3 | Medium | Seven component tests | Airport test only asserts removal of a synthetic node | Does not exercise snapping, route restoration or access correctness | Add frozen airport geometry and directed/access counterexamples | High |
| M4 | Medium | Memo and historical G1 verdicts | Strong conclusions precede qualifications; walk “unbiased” language remains | Readers can mistake differential checks for validation | Put scope beside conclusions and supersede conflicting verdicts | High |

## Detailed notes

### H1 — Decision 12 has not been evaluated

“At the 21-minute median journey length here, the 10% tolerance is about 2.1 minutes” changes the acceptance question. Decision 12 says median absolute error **at threshold** ≤10% of T, p90 ≤20%, plus false inclusion/exclusion. No household threshold was assigned to these twelve pairs. The 21-minute value is OSRM's median, not even the traffic-aware reference's median.

At T=10 the budgets are 1 and 2 minutes: the pooled rounded median meets the first exactly, while the pooled p90 of 3 exceeds the second. This does not prove a ten-minute boundary fails—those observations were not sampled there—but prevents claiming it passes. At T=25 the budgets are 2.5 and 5; pooled numbers look encouraging without establishing that boundary either. Do not accidentally require p90 ≤10%; the actual p90 gate is 20%.

Engine agreement is only one contribution to final boundary error. Expansion reconstruction, cell access, destination entrance, grid representation and minute encoding must also fit the budget; their errors may reinforce or offset, so adding their medians is no solution. The corrected expansion still lacks paired remeasurement in the reviewed reports. Pass 4 H2/H5/H8 already identified these distinctions.

### H2 — A future Tuesday forecast cannot establish a morning profile

The heading “Valhalla's static profile is already calibrated to morning traffic” and sentence “On these journeys it lands on real 8 am conditions” overstate the measurement. `DEPART` is 2026-11-10T13:00:00Z: a future Tuesday at 08:00 local, queried on November 3. This is agreement with another model's forecast, not observed congestion or a demonstrated calibration process.

The four negative, three zero and five positive rounded residuals make zero a natural sample median. Rounding alone can turn small nonzero residuals into ties and create an exact-zero median; it cannot explain away all the useful one-to-three-minute agreement. The observed distribution is reasonably tight, rather than merely an arbitrarily wide distribution straddling zero. MAE and RMSE confirm the descriptive ranking. Nevertheless, p90 is effectively governed by two upper-tail observations, and the sign test's p=1 is absence of directional evidence, not an equivalence finding.

“Typical weekday morning” could make an off-peak errand look unnecessarily far away, yet this sample cannot quantify that effect. Nor does traffic-aware being slower prove all that excess is congestion along the same path. A defensible present label is: **“Estimated drive time from a static road model; traffic and departure time are not included.”** Put “closest to an 08:00 Google forecast in a small local check” in research notes, not a general service promise.

The later caveat correctly calls Google a prediction. It conflicts with earlier “actual congestion” and “real 8 am conditions.” “Only congestion-aware number here” is a valid description of the selected legs, not authority to treat it as truth. Forecasts may miss unusual incidents, weather, closures, special events or changed demand; reference error can also correlate across shared corridors. No reference-accuracy measurement was performed here. Google's road data, allowed turns, access correlation and route choice may differ from ours. Only duration was requested, so those explanations cannot be checked from this payload.

### H3 — The causal decomposition is unsupported

“Our six-minute error splits cleanly in half, and only half is ours to fix” appears again as a factual decomposition in D1. Per journey the identity traffic-minus-ours = static-minus-ours + traffic-minus-static is exact. Taking medians does not generally preserve that identity. Here the rounded medians happen to sum; the supplied unrounded signed summaries instead imply component magnitudes 2.9+2.7=5.6 versus a total 5.5, already defeating an exact split at reported precision.

Even the rounded per-journey allocation varies from 0% to 100% attributed to the static gap; only one pair splits equally. No intersection counts, controlled routes or with/without-penalty runs identify the cause. Speed assumptions, network topology, turn restrictions, node snaps and omitted endpoint access all differ simultaneously. Google routing preferences can also select different paths, making the two Google legs a difference between routing outputs, not a pure fixed-route congestion measurement.

Ported penalties are a plausible improvement to test. “Would close about half the gap” is an untested prediction. Conversely, a static model can encode typical delays without live traffic—as the Valhalla argument itself proposes—so “nothing static can” and “not fixable” are too absolute. A static model cannot adapt to each departure's congestion, but can agree with an average under some conditions. Test penalties on our own fixed graph before assigning a minute value to them; do not calibrate from Google outputs.

### H4 — The measured operation is not the product operation

“Twelve real Triangle journeys between named places, point to point” describes plausible OD pairs, not observed trips. `ours_point_to_point` snaps both endpoints to nearest **nodes**, without snap-distance bounds or endpoint access charges. The layer path instead interpolates nearest **edges**, adds modal origin access, caps it at 200 m, and selects nearest-category destinations. POI node snapping has a 300 m bound but does not charge destination access. These unequal operations can inflate the apparent speed advantage of ours; they do not erase its known modelling omissions.

Hospital, town-centre and airport anchors overrepresent major connected roads; residential cells include cul-de-sacs, gated access, disconnected paths, fences, rivers and coordinates off-network. Arbitrary legal entrances matter. The selected directions do not test reverse commutes, although the network is directed, and repeated destinations/corridors reduce effective independence. There are no ultra-short or long-trip strata; the rounded range across engines is 3–34 minutes, with no sub-three or over-35 coverage. Short thresholds are especially sensitive to omitted access seconds.

OSRM adds implementation diversity, but not independent truth: ours, Valhalla and OSRM share OSM ancestry. The demo's deployment profile, customization, source date and snapping policy were not captured. Calling its speeds definitively “free-flow” goes beyond this record. The configured `driving` URL alone does not establish the actual served profile/version. Keep its row as an exploratory check, not a controlled benchmark.

### H5 — Retention discipline is contradicted by both artifact and code

“Per-pair Google values are not recorded here or in the JSON” is false for the reviewed Markdown. The 16:51:45 section contains the full twelve-row, two-Google-column table. The later section keeps two illustrations, but the earlier table remains. This review does not reproduce that dataset.

The generator explains the contradiction: `engines` includes both Google legs; every engine enters the Markdown row loop; `append_results` writes it all to the repository. Only the JSON `keep` comprehension removes Google fields. The docstring's assertion that the results file contains only aggregates and a few illustrations is unimplemented. This is a direct breach of the project's stated discipline; it is not a legal determination about Google's terms. Correct the writer and existing retained table in separately authorized work. No existing file was edited during this review.

### H6 — Pruning is a policy choice, not a general reachability repair

The fix “prunes to the largest component before snapping” and “This also means the layer coverage figures were pessimistic” conflate removing snap candidates with establishing access. Separate valid pedestrian networks, islands, campuses or local amenity networks can support journeys within smaller components. Removing all of them can destroy valid answers. A small fraction of graph nodes can contain a user's entire neighbourhood; a 10% node-loss guard provides no bound on household impact. It is a useful configurable alarm, not a justified correctness threshold, and fragmentation alone does not prove bad filtering or bounds.

Weak connectivity ignores edge direction. A retained one-way branch can still fail origin-to-anchor reachability. Keeping only the largest **strong** component is not the universal fix either: it can discard legitimate one-way approaches or exits needed for particular journeys. Directed reachability to the actual destination set and legal candidate snapping are the relevant tests.

After pruning, a formerly stub-snapped cell may acquire a reachable road, exceed the 200 m access limit, or cross a barrier through the straight-line access leg. A formerly finite cell in a smaller component can become unreachable. POIs can be dropped or resnapped too. Coverage therefore need not increase monotonically; an increase alone would not establish correctness. Publish finite→missing and missing→finite transitions, displacement and legal-access checks before calling 72.7% pessimistic.

All seven tests pass, but `test_the_airport_failure_mode_is_what_this_prevents` only checks that `s0` disappears from a synthetic graph. It never snaps an airport coordinate, computes a route, bounds displacement or checks legality. It tests one necessary mechanism, not the actual failure-and-recovery chain. This pruning is in the own-graph scripts, not proof of better Valhalla expansion coverage.

## Claim-by-claim verdict

1. **Partly supported:** rounded descriptive ranking survives distribution metrics; calibration and exact-zero significance do not. Close with seconds-level, representative paired measurements and uncertainty.
2. **Not supported:** rounded aggregate identity does not identify penalties or a universal half split. Close with controlled same-engine ablation and route inspection.
3. **Not supported as a tolerance test:** decision 12 uses T and boundary populations. Close with threshold-stratified final-surface errors and confusion counts.
4. **Not supported:** the morning label overclaims one forecast. Close with repeated observations across relevant periods; retain a static-estimate label now.
5. **Supported criticism:** sample geometry and time/direction coverage are inadequate. Close with residential cells, legal entrances, reversed pairs and threshold strata.
6. **Partly supported:** Google is the selected congestion-aware proxy, not truth; OSRM is uncontrolled. Close with observed trips and reproducible reference provenance.
7. **Partly supported:** component removal addresses the demonstrated mechanism, not general reachability or improved coverage. Close with actual snapping/routing regressions and lost-network audits.
8. **Supported criticism:** caveats exist, including explicit drive-only scope, but follow stronger claims and do not repair the memo. Historical walk “unbiased/passes” statements still invite real-world validation readings despite the later correction. No evidence of deliberate concealment is needed to explain these contradictions.
9. **Supported direction:** measure actual product boundaries next; another anchor-only comparison has lower decision value.

## What to measure next

1. **Most informative: one paired residential boundary audit of the final drive surface.** For several household anchors, freeze a reproducible sample around T=10/15/25/45, sampling on both sides using reference-assisted screening plus an independent residential frame. Include predicted-unreachable cells and barrier/one-way strata. Compare final encoded cell values, exact Valhalla routes and live independent traffic-aware predictions at the same departures. Report per-T median/T, p90/T, false inclusion/exclusion with explicit denominators, missingness and snap displacement. This separates engine disagreement from product-construction error and directly changes whether decision 12 can be claimed. Use seconds in transient computations and retain only outputs permitted by the established discipline.
2. **Repeat that sample at morning, afternoon peak and off-peak departures**, with direction reversed for a subset and more than one weekday. This tests whether the proposed temporal label helps or misleads. Predeclare the sample rather than selecting favourable routes afterward.
3. **Anchor the comparison with a small set of hand-timed household drives.** Record departure, actual accessible endpoints and consistent travel-time semantics; repeat some trips. This is the cheapest independent check that model agreement is useful to a household, though a handful of drives cannot certify a population p90.
4. **Repair local validation prerequisites before rerunning.** The widened layer writer uses `layer_path`, but `g1_matrix_compare.py` loads `own_{category}_{mode}.npy` while `_common` now defaults to Triangle. A leftover slice array can be paired with Triangle coordinates, or the run can fail if absent. Validate metro/grid metadata, remeasure corrected expansion and test pruning transitions. These inexpensive checks can invalidate an apparently excellent next benchmark before external requests are spent.

The cheapest defensible household demonstration combines the existing provisional Valhalla choice, the explicit static-estimate label, one narrow boundary audit and a few independently timed familiar drives. Present a provisional search aid with uncertainty near the boundary; do not promise the 10% gate until its actual per-threshold results support it. No speed tuning from Google output is required.

## What is right

The spot check exposed a real availability defect, challenged a convenient static reference and made a useful engine ranking visible. The Google-leg rounded arithmetic is substantially correct. Rounding, prediction status, sample size, off-peak uncertainty and missing walk/bike validation are explicitly disclosed. Keeping those disclosures beside the conclusions, and distinguishing engineering selection from validated household accuracy, would preserve the experiment's value without its unsupported product promises.
