# Codex Adversarial Review - UX Stream and Synthesis (Pass 2)

**Date:** 2026-11-03 · **Model:** GPT-6 (Codex; exact serving variant unavailable) · **Method:** Read the owner decisions, 07, 06, and 08 in order; checked cited passages and relevant summaries in 00–05; spot-verified primary web sources linked below. No benchmarks or device tests were run. Severity denotes planning impact; confidence distinguishes document-observed contradictions from product hypotheses. Only this file was created.

## Verdict

- **08 is ready to define experiments, not to freeze the build plan.** Its pass-1 corrections are substantial, but dependencies and acceptance criteria remain inconsistent.
- Move arbitrary-address anchors, geocoding, and basic explanations into Phase 1. Without two workplaces, the proposed first release misses its own wedge.
- Treat the complete interaction shape as a hypothesis. Cards first is reasonable; mandatory people objects, soft fringes, and tap-anywhere explanations are not settled by HCI literature.
- Remove “worst case” until independent traffic evidence supports that claim. Agreement with static Valhalla does not validate commute reliability.
- Rebuild the cost comparison around total operating effort and a lawful hosted alternative. Correct the inherited claim that a 60-minute limit excludes 45-minute searches.
- Define soft semantics, missing-data states, privacy, and listings fallback acceptance before implementation. Parcel counts cannot substitute for available homes.
- Keep the reduced scope, deterministic query engine, fail-closed ingestion, and explicit routing/listings gates.

## Part A - Findings on 06

| id | severity | section | issue | why it matters | action | confidence |
|---|---|---|---|---|---|---|
| A1 | High | §5.4–5.9 | Typical 8 am, worst-case traffic, fit percentages, and homes counts exceed demonstrated data contracts. | Mockups promise unsupported certainty and inventory. | Remove or qualify each promise; define its source and denominator. | High |
| A2 | High | §5.4–5.6 | Soft bands, “misses one,” mute/eye, and percent removed lack consistent semantics. | Users can change eligibility while believing they changed visibility. | Specify the algebra and separate visibility from inclusion. | High |
| A3 | High | §1, §6 | Anecdotes and transferable design principles become a verdict against structured entry. | V1 execution failure does not eliminate a simpler two-address design. | Reframe hybrid as a testable recommendation. | High |
| A4 | High | §7 | Leading tasks and repeat mobile task cannot validate comparative superiority or unaided discovery. | Tests can pass while the listed risks persist. | Counterbalance variants; add unprompted and failure tasks. | High |
| A5 | High | §8 Q6; §5.8 | Cohort-based suggestions are entertained; numeric templates are treated as sufficient protection. | Discriminatory choices can enter upstream of explanation prose. | Use user-requested criteria; test suggestions and selection behavior. | High |
| A6 | Medium | §1, §2.2, §4 | Correct source ideas acquire stronger population, quote, and domain claims. | Evidence confidence becomes inflated. | Correct attribution and distinguish quotation from inference. | High |
| A7 | Medium | §5.3, §5.9 | Dense rail, hover effects, horizontal chips, voice, and batch apply have no accessibility contract. | Touch, keyboard, screen-reader, and low-vision users may miss active constraints. | Test a persistent summary and accessible edit drawer. | High |
| A8 | Medium | §6, §7 | Deferring numeric weights is sensible scope control, but absence of demand is not evidence against need. | Fixed soft curves still encode hidden weights. | Disclose defaults; test trade-offs without requiring weight vocabulary. | High |

### Detailed notes on High findings

**A1 — Wireframe truthfulness.** Stream 05 supplies estimated static travel times, optional later profiles, and uncertain listings access. It supplies neither a 95th-percentile commute nor an active-listings census. A parcel can be vacant, nonresidential, or contain multiple homes; its centroid is not an entrance. “See 212 homes” suggests available inventory, which free portal links cannot count. Neighborhood fit needs a boundary source and a denominator: eligible area, residential parcels, households, or satisfied criteria produce different percentages. The Query also offers budget and walkability without identifying an executable region filter. Label unsupported filters as portal-only or defer them.

**A2 — Soft logic is unfinished.** A fixed 25–35-minute fringe is a tolerance, while “meets all but one soft” is a count, and stream 05 proposes weighted decay. These differ with multiple soft criteria. No hard failure should enter the result through a soft fringe. “Removes 62% of remaining area” depends on ordering; a leave-one-out contribution uses another denominator. Two failing constraints can make one-tap “relax to 31” leave a point excluded. Explain all failures, preview the change, and distinguish unknown coverage from failure. An eye icon should never silently disable a constraint.

**A3 — Principles do not select this interface.** HN comments establish useful failure hypotheses, not demand prevalence or the two most requested features across buyers. One failed geographic LLM product does not establish failure of all chat-led interfaces backed by deterministic tools. Conversely, Baymard's evidence favors better filters; it does not show that forms impose more articulation burden than prose. Keep an address-first map in the comparison. A `Person` object can remain internal while users enter two commute cards without household setup.

**A4 — Test behavior, not obedience.** Asking explicitly for a soft constraint or why a region is excluded teaches the feature being evaluated. Repeating the same task on mobile introduces learning. A seeded miles/minutes error detects one conspicuous misparse, not plausible wrong workplaces, omitted clauses, wrong directions, or stale results. Add an initially impossible search, ambiguous address, failed layer fetch, hard-versus-soft comprehension prediction, outside-coverage location, and phone-first participants. Counterbalance direct entry and NL on equivalent novel scenarios. Define success for error detection and recovery, not only completion or reported trust. A confident wrong answer is a failure. Six people can reveal usability problems; they cannot settle market preference.

**A5 — Fairness applies before prose.** Inferring school convenience from a buyer's cohort can steer suggestions even if the final sentence contains only numbers. Avoid inferring protected traits or household needs; offer a consistent neutral palette and honor explicit user requests. Add paired prompts differing only in protected-trait cues and inspect criteria, destinations, and rankings. This is a product control recommendation, not a finding that school/crime data are inherently unlawful: [HUD's April 2026 statement](https://www.hud.gov/news/hud-no-26-028) distinguishes consistent factual information from intentional discriminatory steering. Templates alone do not implement that distinction.

### Source checks and evidence limits

- **Horvitz 1999 and Shneiderman 2020:** attribution and general coupling/control claims check out against [Microsoft's abstract](https://www.microsoft.com/en-us/research/publication/principles-mixed-initiative-user-interfaces/) and [Shneiderman's abstract](https://arxiv.org/abs/2002.04087). Neither validates this rail, household model, or soft visualization.
- **Nielsen 2023:** the hybrid prediction is genuine. The population-literacy statement is explicitly his judgment, with uncertainty; 06 makes it sound established. Preserve that qualification. [Original article](https://www.nngroup.com/articles/ai-paradigm/).
- **Articulation and accordion editing:** the former analyzes over 100 Midjourney prompts; the latter studies eight professionals/students editing generated text. Their GUI and partial-edit recommendations are accurately represented, but application to home search is an inference. [Articulation study](https://www.nngroup.com/articles/ai-articulation-barrier/), [editing study](https://www.nngroup.com/articles/accordion-editing-apple-picking/).
- **Baymard:** 28% lacking an applied-filter overview and the mediocre/poor filtering description are supported. These are ecommerce observations, not home-search abandonment rates. [Applied filters](https://baymard.com/research-articles/how-to-design-applied-filters), [filtering guidance](https://baymard.com/blog/ecommerce-filter-ui).
- **Kulesza 2013:** the completeness/mental-model finding is supported, in a music-recommender study. The quoted phrase “cognitive strain and diminished trust” was not verified verbatim; the repository abstract uses different wording. Paraphrase it and retain the domain limitation. [Author manuscript record](https://openaccess.city.ac.uk/id/eprint/6344/).
- **NAR/Zillow:** NAR's 59/47/31 and Zillow's 61/53/51/49 figures are supported by the [NAR highlights](https://www.nar.realtor/sites/default/files/2025-11/2025-profile-of-home-buyers-and-sellers-highlights-11-04-2025.pdf) and now-accessible [2026 Zillow report](https://www.zillow.com/research/buyers-housing-trends-report-2026/). They measure different questions/populations, not constraint hardness. Friends/family does not mean a sister's specific address; finding the right property does not establish that neighborhood fit caused the difficulty. National buyer samples are not Triangle target-household evidence.

## Part B - Findings on 08

| id | severity | section | issue | why it matters | action | confidence |
|---|---|---|---|---|---|---|
| B1 | Critical | §6–7 | Phase 1 lacks arbitrary anchors; G5 timing and G6 dependencies conflict. | The advertised first product cannot perform two-workplace search. | Repair phase dependencies before planning. | High |
| B2 | High | §3.1, G1 | Static-engine comparison is offered as validation for “worst case”; aggregate error gates tolerate boundary mistakes. | Accurate-looking exclusions can mislead relocation decisions. | Separate model consistency from real-world accuracy. | High |
| B3 | High | §5 | Cost ranges lack a reproducible workload; Tier 0 inherits false 45-minute exclusion. | Tier 1 is preferred using an invalid alternative comparison. | Reprice lawful alternatives and itemize operations. | High |
| B4 | High | §3.1, §4, §11 | Most UI complexity is declared settled despite 07 H7. | An evidence correction becomes only an NL scheduling change. | Keep the complete interaction hypothesis open. | High |
| B5 | High | §3.1–3.5, §8 | Full Query in URLs exposes private anchors; geocoding and failure-state contracts are absent. | Core dependencies and household privacy remain unplanned. | Add provider, persistence, redaction, and error contracts. | High |
| B6 | High | §3.5, G4 | City/ZIP fallback and 90% link success do not establish useful region handoff. | A required feature can pass despite substantial geographic leakage. | Define fallback acceptance and exact-versus-box labeling. | High |
| B7 | Medium | §3.2, §7 | Tiered geography's approximate elsewhere-US experience disappears. | Synthesis silently drops an owner-fixed decision. | Explicitly stage fallback coverage and limitations. | High |
| B8 | Medium | §8–10 | Backlog mixes present blockers with unused products; owner questions include delegated technical choices. | Avoidable research and approvals delay useful experiments. | Prioritize by first data use; ask only genuine owner choices. | High |

### Detailed notes on Critical/High findings and citation audit

**B1 — Phase 1 is internally impossible as described.** Section 3.1 calls it the two-address flow, but §7 places anchors and explanations in Phase 2. Phase 1 needs address resolution, reverse/arrival semantics, anchor computation, and basic failure explanation; NL can follow. G5 is both blocking for Phase 2 (§6) and performed within Phase 2 (§7). G6 blocks Phase 2 in §6 but is placed in Phase 0 in §7; license and coverage auditing must precede the first POI ingest. Run an early clickable comparison before expensive architecture gates, then validate the working two-anchor slice. Requiring a full 75-layer build and two complete rendering representations before that slice is excessive.

**B2 — Wrong reference for the claim.** Valhalla without traffic is a consistency reference, not observed rush-hour truth. The proposed drive p90 relative error of 35% allows roughly nine minutes at a 25-minute boundary. Sample near thresholds and one-way streets, turn restrictions, bridges, entrances, and disconnected components; measure false inclusion/exclusion and absolute error. Clarify that “median abs error <15%” means absolute percentage error and define handling of short/zero/unreachable trips. Validate category minima over candidate destinations, not only pairs chosen as nearest by the model under test. Preserve nodata, direction, units, grid version, and profile in outputs and caches.

**B3 — Budget arithmetic and alternatives.** $12–20 VPS plus up to $5 LLM already reaches $17–25 before separately priced backups, domain, and monitoring. The 10k-user tier has no scaled parse count: 500 parses is 1–2 million input tokens at the stated size; 10k users × five queries could mean 50k parses, or 100 times that workload, before output, retries, and follow-ups. This is a sensitivity example, not a price quote. Include geocoding, basemap tiles, VAT/region/storage, off-box backups and restoration, Valhalla rebuild CPU/disk/upload, refresh labor, security maintenance, and Cloudflare request/CPU limits. RentCast's 50-request quota must be reconciled with pagination and refresh; the $74 addition is outside Tier 2's $40–70 range and must be labeled separately.

Stream 05 §5.2 supports the original hosting arithmetic, not these revised totals. Stream 04 §3.5 supports the quoted RentCast tiers, subject to license verification. Neither establishes sustainable all-in operating cost. Tier 1 is defensible if accuracy and measured demand require it; public intent does not itself exclude commercial hosted services. The [Mapbox documentation](https://docs.mapbox.com/api/navigation/isochrone/) supports 60-minute contours, so 45 minutes is within the limit. It also requires Mapbox-map display; a MapLibre fallback cannot be assumed compliant. Hosted options still need inbound-routing and data-rights checks.

**B4 — At least seven synthesis citations checked:**

| 08 claim and source | Assessment |
|---|---|
| §2.1 → 01 §1/§4: no live US product | Survey found no example; categorical market absence overreaches its access limitations. |
| §2.2 → 01 §1, 06 §1: NL is table stakes | Competitor launches support prevalence, not necessity for this audience. |
| §2.3 → 05 §3: 75 layers ≈71 MB | Correct for 948k bounding-box pixels; 570k land cells alone give ≈42.8 MB. State the distinction. |
| §3.1 → 06 §5, 01 §5: shape is settled | Sources recommend different defaults, including soft ranking later in 01. No comparative test settles the whole shape. |
| §3.3 → 05 Spike 2: accuracy gates | Thresholds are inherited experiment proposals, not evidence of user-safe boundary decisions. |
| §3.5 → 04 §1, 07 C3: listings mechanism | Correctly conditional; “only” legal avenue overstates acknowledged paid/licensed options. |
| §3.6 → 00 §6, 07 C1/H4: reuse corrections | Supported, but typed cards do not make unit/dispatch bugs impossible; require dimensional validation. |

**B5 — Missing critical path and risk controls.** Reusing localUpdates' geocoder seam does not establish address coverage, autocomplete permission, rate limits, or rights to persist coordinates in share URLs. Choose and test a provider contract. Default URLs should omit names/raw addresses; offer deliberate sharing and redact location-bearing telemetry. Define no-results, ambiguous/unresolved anchor, unreachable, outside coverage, expired link, partial data, and routing failure states. Add versioned atomic refresh/rollback, freshness labels, and minimal redacted timing/error analytics. Parcel and neighborhood boundaries need licenses before their first use; defer their ingestion if the features remain Phase 3.

**B6 — Required handoff versus fallback.** Correct bounds must include user filters and app handoff, not merely viewport appearance. A narrow disconnected region can have a huge bounding box. Measure leakage and household ability to identify in-region listings after return. Broken links must not be silently included in a 90% average. City/ZIP links can be an honest useful fallback, but whether they satisfy the fixed bounded-listings requirement is an owner acceptance decision. RentCast cannot block free linkage if pins remain optional.

### Counter-resolutions

**H3 versus square raster:** Freeze a minimal projected square grid for computation; treat H3 as an optional display/index experiment. Compare equal spatial-error budgets rather than nominal resolutions. Two full implementations should be required only if the small raster slice fails a meaningful criterion.

**DuckDB versus PostGIS:** Keep DuckDB until actual concurrent-write, deployment, or transaction requirements exceed it. A second metro with shared users is not a database capability requirement; row-level controls may live in the API. Diagnose a 500 ms query before migrating.

**Transit:** Ask households before locking v1 modes. A single transit-dependent intended user may justify a prototype; “two of five” is arbitrary. Supporting their workplace requires a scheduled anchor, which a category-only AM surface does not supply.

**Hard versus soft:** Ship hard limits and explicit temporary relaxation first. Store minutes to preserve future scoring, while postponing fringes and weights together until trade-off tasks justify them. No numeric sliders is reasonable; unannounced fixed weights are not neutral.

**Own Dijkstra versus Valhalla:** Use one engine for the first small anchor/category slice. Add own-graph precompute only after measuring its operational benefit and boundary disagreement. Benchmark the many-destination Valhalla fallback rather than assuming it is cheap.

**Peak versus off-peak:** Offer one documented static estimate initially. A slower sensitivity scenario may follow with transparent assumptions; neither static agreement nor a renamed toggle establishes worst-case or 95th-percentile travel time.

**TripAdvisor:** Drop runtime integration for this wedge. Preserve V1 as the owner requires. Reconsider a lawful successor only for a later hotel need; API deprecation is not a blanket assertion that every future TripAdvisor offering is unusable.

**Interaction emphasis:** A two-address map with optional early NL parsing is the strongest alternative. Compare equivalent prototypes before deciding prominence; NL need not precede a usable direct-entry product, and direct entry need not postpone all NL experimentation.

## Part C - Pass-1 absorption

“Addressed” means the recommendation was corrected, not that its verification gate has passed.

| pass-1 finding id | severity | addressed / partial / ignored | note |
|---|---|---|---|
| C1 | Critical | addressed | Transposed directed graph explicitly required; turn restrictions and arrival semantics still need testing. |
| C2 | Critical | addressed | Place-ID-only storage corrects the permissive caching assertion. |
| C3 | Critical | partial | Device/license gate added; fallback usefulness and filters not fully in acceptance criteria. |
| H1 | High | addressed | 8 GB provisional baseline, CSR, measured RSS; no measured fit claimed. |
| H2 | High | partial | Payload clipping/concurrency added; scaled costs and rebuild/storage overhead remain unsubstantiated. |
| H3 | High | partial | No cross-source merge helps; source-native records alone do not establish ODbL compliance. |
| H4 | High | addressed | Fail-closed collector and pinned manifest required. |
| H5 | High | addressed | Square choice provisional; comparative G3 test retained. |
| H6 | High | partial | Interviews accepted, but arbitrary voting threshold and category-only response miss anchor needs. |
| H7 | High | partial | NL emphasis becomes a hypothesis; declaring the remaining shape settled contradicts 07's broader caution without evidence. |
| H8 | High | addressed | IDX demoted to future written broker/vendor path. |
| H9 | High | addressed | Versioned rendering test; Terrarium no longer assumed necessary. |
| H10 | High | addressed | Component timings and end-to-end gates included; actual measurements outstanding. |

No Critical/High finding is wholly ignored. Separately, 07 M6 is only partially absorbed: “worst case” survives behind an inappropriate static-reference gate.

## Recommended edits to 08

1. Replace “This shape is required under every candidate model, so building it first is not a bet.” with “Map-first editable criteria are the working hypothesis; people grouping, soft rendering, and explanation discovery require comparative testing.”
2. Replace “This is already usable by friends and family.” with “Phase 1 is usable after it includes two resolved workplace anchors, inbound travel-time regions, basic exclusion/error explanations, and a verified listings handoff.” Move those dependencies from Phase 2.
3. Replace “G5–G6 are blocking for Phase 2” with “G6 blocks POI ingestion; an early G5 prototype informs Phase 1, followed by testing on the working slice before NL prominence is decided.”
4. Replace “offer a documented slower profile as ‘worst case’ only after Gate G1 reports its error against Valhalla” with “Offer static estimates with explicit assumptions; defer worst-case claims until independent time-of-day evidence validates them.”
5. Replace “the full `Query` lives in a shareable URL” with “Persist versioned query state; shared URLs disclose only explicitly approved location information, with private names and addresses omitted by default.”
6. Replace “Tier 1” recommendation with “Tier 1 is provisional pending G2 and a total-cost comparison with a lawful hosted alternative.” Delete “45 min to RDU” from Tier 0 exclusions; add Mapbox display and direction restrictions.
7. After G1's accuracy criterion add: “Report absolute error and false inclusion/exclusion near user thresholds, including missing data, entrances, direction, and restrictions; Valhalla agreement does not validate traffic reliability.”
8. After G4 add: “Test filters, mobile app return, and geographic leakage; optional RentCast pins do not gate free links. Owner acceptance is required if city/ZIP links replace bounded-region handoff.”
9. After §7 add: “Stage approximate elsewhere-US coverage explicitly under kickoff decision 2; show unsupported capabilities and coverage boundaries.”
10. Replace “Also before planning: verify the load-bearing claims in §9.” with “Before first use verify routing, geocoding/storage rights, required handoff, active-source licenses, and recovery behavior. Defer Google, RentCast, IDX, Amadeus, Transitous, and neighborhood checks until those optional integrations enter scope.”
11. Replace §10's technical confirmations with owner choices on spending ceiling, acceptable commute uncertainty, actual transit needs, fallback handoff, and privacy/sharing defaults. Defer second-metro and brokerage questions; the approved reuse/drop recommendations need no new permission.

## What is right

The synthesis genuinely improves routing direction, license handling, memory assumptions, and listings uncertainty. Its scope cut is a useful effective YAGNI list, although Phase 0 still overbuilds experiments. Keep commutes, a few trustworthy amenity categories, an honest region, and a tested listings handoff as the first complete slice. The existing-repo reuse plan and deterministic engine behind editable query state remain sound foundations.
