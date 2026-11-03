# V2 Synthesis and Recommendation

**Date:** 2026-11-03 · **Status:** v0.4 — revised against Codex adversarial pass 1 (`07`, streams 00–05) and pass 2 (`09`, UX stream and this document); **owner decisions received** (see §11 and `../plans/2026-11-03-v2-rethink-decisions.md` round 2). The implementation plan follows in `../plans/`. A Codex pass 3 reviews that plan.
**Inputs:** research streams `00`–`06`, Codex reviews `07` and `09`, kickoff decisions in `../plans/2026-11-03-v2-rethink-decisions.md`.
**How to read this:** §3 separates what is **settled** (owner decision or converging evidence) from what is a **hypothesis** tied to a numbered gate in §6. Nothing marked hypothesis is built on until its gate passes. Section 11 records how each Codex finding was absorbed.

---

## 1. What we are building

A map-first location finder in which a person or a couple states where they need to be and how they get there, and the system turns each requirement into a visible, editable **criteria card** — "Sam drives to Fidelity RTP in ≤ 25 minutes", "10-minute walk to a park", "bikeable to a grocery store", "≤ 45 minutes to RDU" — and draws the **region** where all cards hold, then hands the user to real listings bounded to that region. The wedge is home search in the Research Triangle; approximate coverage elsewhere in the US is staged explicitly (kickoff decision 2). The same engine (travel-time surfaces per mode + constraint algebra + region enrichment + deep-link adapters) later serves hotel stays near an event venue and small-business site selection with Census demographics.

What is new relative to V1: the constraint set is the product, not a form; amenity categories are precomputed coverage layers rather than live Overpass queries; a language model, when present, parses intent but never produces geography; every exclusion is explainable with real numbers; listings are one click away. The first complete slice is deliberately small: **two resolved workplace anchors, a few trustworthy amenity categories, an honest region, and a tested listings handoff.**

---

## 2. Headline conclusions

1. **The gap is real.** The survey found no live US product that shows where *two* commutes plus amenity layers intersect; the request recurs on Hacker News from 2011; Homesnap's 2018 attempt failed; the UK's Jitty is the nearest analogue (01 §1, §4). This is a finding of the survey's reach, not proof of market absence (09 B4).
2. **Natural language is prevalent, not proven necessary for this audience.** Four US portals shipped AI search between Oct 2025 and Aug 2026; chat-only products have failed publicly (01 §1, 06 §1). The engagement metrics cited do not isolate the interaction model (07 H7, 09 A3).
3. **The compute problem is tractable; its size is a hypothesis.** Triangle at 100 m is ~570k land cells inside a ~948k-pixel bounding box; 75 uint8 layers are ~71 MB raw over the box (~43 MB over land) (05 §3, 09 B4). Build time, compressed size, and serving cost are measured at Gate G1.
4. **The reusable CHCCS routing engine has a correctness flaw.** It forces every road bidirectional and runs Dijkstra outward from destinations; for drive and bike that answers the wrong question on one-way streets. Any port must run on the **transposed** directed graph and be validated against Valhalla arrival ("reverse") isochrones (07 C1; confirmed in `school_desert.py:312–320, 620, 662`).
5. **One routing engine first.** The first slice uses self-hosted Valhalla for both arbitrary anchors and category layers (multi-location arrival isochrones with GeoTIFF output). Own-graph precompute is a later optimization adopted only if it shows measured benefit at acceptable boundary error (09 counter-resolutions, 07 H10).
6. **Static files are the cheapest robust serving tier** (05 §4–5), but whether browser raster algebra beats a server-rendered mask for v2.0 is decided at Gate G3, and the Mapbox-style hosted alternative must be priced honestly (09 B3).
7. **Listings are reachable legally only as deep links today, and the deep links are unproven.** Zillow `searchQueryState.mapBounds` and Redfin `viewport` are undocumented patterns (04 §1, 07 C3). Gate G4 tests bounds, filters, and mobile app return; whether a city/ZIP fallback is acceptable if bounded links fail is an **owner decision** (09 B6).
8. **POI base: Overture Places first, OSM by category where Overture is weak, no cross-source entity merge in v1**; the localUpdates collector's fail-open licence default becomes fail-closed on port; TripAdvisor runtime integration is dropped for this wedge; Google Places persists `place_id` only (04 §1, 07 C2–H4).
9. **Most reusable code is not in V1.** localUpdates holds the tested store/geocode/Overture/provenance core, the NL → frozen-filter pattern, and the only eval harness; CHCCS holds the grid engine (with the flaw above); V1 contributes ~250 lines of ideas (00 §1, §6).
10. **Scope shrinks before it grows.** v2.0 is commutes, a short amenity list, the region, and the listings handoff (07 M7). Context layers, soft fringes, numeric weights, transit routing, and voice are deferred and listed in §8 so the deferral is conscious.

---

## 3. What is settled and what is a hypothesis

### 3.1 Interaction — **map-first editable criteria is the working hypothesis; the rest is tested, not assumed**

Settled by owner decision and converging evidence: map is primary; constraints are visible and editable; the geo engine, not a language model, produces every region and pin; chat-only is rejected (06 §6, 09 A3 concurs).

Hypotheses (09 A2–A4, B4; 07 H7):
- *Entry mode.* Direct two-address entry versus "describe it" (NL → Query delta behind the localUpdates seam) is compared on **equivalent novel scenarios, counterbalanced**, measuring time-to-trusted-region, correction count, and error detection — Gate G5a (clickable prototype, before heavy build) and G5b (working slice).
- *People grouping.* `Person` may stay an internal object; users may simply add two commute cards. G5 decides whether household setup is exposed.
- *Soft constraints.* v2.0 ships **hard limits plus explicit, previewed, temporary relaxation** ("relax Sam's limit to 31 min?"). Minutes are stored so scoring remains possible, but soft fringes and weights are deferred together until trade-off tasks justify them; fixed decay curves would be undisclosed weights (09 A2, A8).
- *Explanation discovery.* "Why is this out?" lists **all** failing constraints with actual values and previews the change; a visibility toggle never changes eligibility (09 A2).
- *Truthful labels.* Travel times are "estimated, typical conditions, static model"; no "rush hour", no "worst case", no 95th-percentile claims until independent time-of-day evidence exists (07 M6, 09 A1, B2). No "N homes here" counts from parcels; neighborhood fit percentages only once a boundary source and denominator are chosen (09 A1).
- *Fairness.* No cohort-inferred suggestions (e.g. schools because of household composition); a consistent neutral starter palette; paired-prompt tests that differ only in protected-trait cues inspect criteria, destinations, and ordering, not just prose (09 A5).
- *Accessibility.* A persistent applied-criteria summary and an accessible edit drawer are tested alongside the card rail (09 A7).
- *Privacy.* Shared URLs carry a versioned query with **names and raw addresses omitted by default**; sharing location-bearing anchors is a deliberate act; telemetry is redacted (09 B5).

### 3.2 Architecture — **hybrid static-first is the working hypothesis; server-first is the fallback**

```
 PRECOMPUTE (Windows box, monthly)                 STATIC TIER (Cloudflare, $0)
 Geofabrik NC PBF - osmium clip -> Valhalla tiles  R2:  layers/{metro}/{mode}/{category} (uint8 minutes, versioned)
 Overture + OSM-by-category -----> POIs/category         places/{metro}.parquet (source-native records, lineage)
 Valhalla arrival isochrones, GeoTIFF -> rasters         manifest.json (grid version, profile, nodata, direction)
 [later: own transposed-graph Dijkstra if G1 pays off]   Pages: SPA (MapLibre GL JS)

 ON-DEMAND TIER (one VPS, 8 GB until measured)     BROWSER
 Valhalla (NC tiles) <- FastAPI -> /isochrone-grid  fetch viewport tiles -> AND/threshold in Worker (or server mask)
 geocoder adapter      -> /custom-category          -> canvas layer -> polygonize -> POIs/listings inside
 DuckDB (cache, logs)  -> /nl/parse (LLM, Phase 2)  -> criteria cards <-> versioned Query state <-> URL (redacted)
```

Contracts added after review: 8 GB VPS until peak RSS is measured (07 H1); anchor grids compressed and viewport-clipped (07 H2); MapLibre raster styling tested on the pinned version, Terrarium trick dropped (07 H9); outputs and caches carry nodata, direction, units, grid version, profile (09 B2); versioned atomic refresh with rollback and freshness labels (09 B5); explicit failure states — no results, unresolved or ambiguous anchor, unreachable, outside coverage, expired link, partial data, routing down (09 B5). A **geocoding provider contract** (coverage, autocomplete terms, rate limits, right to persist coordinates) is chosen and tested in Phase 0; the localUpdates seam is the integration point, not the answer (09 B5). Leaflet → MapLibre stands (03 §1).

### 3.3 Routing — **Valhalla is the single engine for the first slice**

Self-hosted Valhalla on the NC extract (MIT; isochrones, matrix, GeoTIFF output, arrival semantics, multimodal) serves anchors and builds category layers. Own-graph csgraph Dijkstra on the transposed graph is **Gate G1, optional**: adopt it only if it is materially cheaper or faster than Valhalla batch *and* its boundary disagreement is acceptable. Accuracy is judged by **absolute error and false inclusion/exclusion near user thresholds**, sampled around one-way streets, turn restrictions, bridges, entrances, and disconnected components; Valhalla agreement is a consistency check, not traffic truth (09 B2). Public FOSSGIS Valhalla stays dev-only at ≤ 1 req/s; a hosted API is the development fallback until the NC build exists, with its display and inbound-routing terms checked (Mapbox permits 60-minute contours, so a 45-minute airport search is in range, but requires display on a Mapbox map) (09 B3).

### 3.4 Data and legal — **rules settled, v2.0 scope reduced**

Rules (04 §5, hardened by 07/09): never scrape; hold no MLS data without a licence; Google Places persists `place_id` only; OSM and Overture records stay source-native with lineage and no cross-source entity merge in v1, with qualified ODbL advice before monetization; ingestion fails closed on unknown licences; a source-registry row precedes every ingest; facts not expression.

v2.0 stored layers: Overture Places and OSM-by-category for the wedge amenity set (parks, groceries, coffee, pharmacies, playgrounds, trailheads, transit stops — final list by Gate G6); GTFS stop locations only. **Not yet ingested** (licence and need to be established first): county parcels, neighborhood boundaries, ACS, LODES, AADT, FEMA NFHL, school grades, crime, noise, canopy, broadband, walkability, elevation (07 M7, 09 B5).

### 3.5 Listings — **approach settled, mechanism and fallback acceptance are Gate G4**

A `ListingLink` adapter emits per-region deep links; our map always shows the true polygon and labels the portal view as a bounding box. Gate G4 tests 20 generated regions across Zillow/Redfin/Realtor.com/Trulia on desktop, iOS, and Android for **bounds, user filters, app handoff and return, and geographic leakage** (a narrow region can have a huge box); broken links count as failures. Optional RentCast pins require reading its full licence; they never gate the free links. If bounded links fail, a city/ZIP link plus the exact region on our map is an honest fallback, but **whether it satisfies kickoff decision 7 is the owner's call** (09 B6). IDX via a Doorify participant brokerage is a future option requiring written confirmation (07 H8).

### 3.6 Code reuse — **settled, with three corrections**

Follow `00 §6` with: (a) the CHCCS port, if G1 adopts it, replaces `_ensure_bidirectional` with per-mode directed graphs and runs on the transpose (07 C1); (b) the Overture collector's `_license_for_row` fails closed from a pinned release manifest (07 H4); (c) typed constraints get **dimensional validation** (units, mode, direction) in tests, since types alone do not make V1's minutes-as-miles bug impossible (09 B4). Reuse and drop decisions were made at kickoff (decision 5); no new permission is needed. V1 code stays in the repo for reference.

### 3.7 Tiered geography (kickoff decision 2) — **staged explicitly**

Tier A, Research Triangle: precomputed category layers + anchors. Tier B, elsewhere in the US (Phase 3+): anchors only via on-demand isochrones (self-hosted US build or a hosted API), no category layers, with the coverage boundary and unsupported capabilities shown in the UI. Tier C, a second precomputed metro, only when the pipeline is proven metro-agnostic (09 B7).

---

## 4. Disagreements between streams and their resolution

| Topic | Positions | Resolution | Gate |
|---|---|---|---|
| **H3 vs square raster** | 01: H3. 03: H3-keyed + COG. 05: square rasters. 07 H5: H3 r10 ≈ 0.015 km², ~50% larger than a 100 m square. 09: freeze a projected square grid; H3 only as a display/index experiment if the raster slice fails a meaningful criterion. | Projected square grid for computation; compare on equal spatial-error budgets; no second full implementation unless G3 fails. | G3 |
| **DuckDB vs PostGIS** | 04: PostGIS label. 03/05/00: DuckDB behind the `Store` seam. 09: migrate on real concurrent-write or transaction needs; diagnose slow queries before migrating; row-level control can live in the API. | DuckDB. Migration trigger: more than one concurrent writer service or transactional needs the API cannot wrap. | Phase 3 review |
| **Transit** | 02: must-have. 05: precompute categories only. 07 H6/09: ask households; a category-only AM surface does not serve a transit-dependent commuter — that needs a scheduled anchor. | v2.0 ships drive/bike/walk. G5 interviews ask about transit; **any** transit-dependent intended user justifies a scheduled-anchor prototype (r5py/MOTIS) in Phase 3, not a category surface. | G5 |
| **Hard vs soft** | 01/06: hard default, soft flag. 05: store minutes. 09 A2/A8: soft semantics unfinished; fixed curves are hidden weights. | Hard limits + explicit previewed relaxation in v2.0; minutes stored; fringes and weights deferred together. | G5 |
| **Own Dijkstra vs Valhalla** | 00/05: own model transparent. 07 C1/H10: direction and timing unproven. 09: one engine for the first slice; benchmark many-destination Valhalla rather than assume it is cheap. | Valhalla for the slice; own-graph only on measured benefit. | G1 |
| **Peak vs off-peak** | 01: rush toggle everywhere. 05: no traffic data. 07 M6/09 B2: static agreement does not validate worst case. | One documented static estimate; a slower *sensitivity* scenario may follow with transparent assumptions; no "rush hour"/"worst case" labels. | — |
| **Interaction emphasis** | 01/06: NL builds cards. 02: competitors hide filters. 07 H7/09 A3, B4: evidence does not select the interface. | Address-first map with optional early NL parsing, compared on equivalent prototypes (G5a) before prominence is decided; NL need not wait for a finished direct-entry product. | G5 |
| **TripAdvisor** | 00/04: drop. 09: drop runtime integration for this wedge; API deprecation is not a verdict on every future offering. | Dropped for v2.0; V1 code retained; revisit lawful successors only for a hotel need. | — |

---

## 5. Budget — **Tier 1 is provisional; ranges are sensitivity examples, not quotes**

Codex (07 M3, 09 B3) is right that the earlier totals omitted operations and used an invalid hosted comparison. Itemized for friends-and-family (≤ 20 users, ≤ 500 parses/month) and a 10k-monthly-user sensitivity case (5 queries each; if every query is parsed, ~50k parses/month at 2–4k input tokens ≈ 100–200M tokens before retries).

| Item | Friends & family | 10k users (sensitivity) |
|---|---|---|
| Static site + R2 (layers ≤ 1 GB, free egress) | $0 | $0–5 (request/CPU limits, overage headroom) |
| VPS 8 GB (Valhalla + API), backups, monitoring | $15–25 | $40–80 (second node or managed fallback) |
| LLM parsing (Phase 2+) | ≤ $5 | $50–200 (depends on model and caching) |
| Geocoding provider | $0 on free tier (terms to verify) | $0–50 |
| Domain, basemap tiles | ~$1 + $0 (Protomaps/self-served) | ~$1 + $0–20 |
| Valhalla rebuild compute, refresh labor | $0 (local) + owner time | $0–5 + owner time |
| Optional: RentCast Foundation | +$74 (not in totals) | +$74 |
| **Total** | **$20–35** | **$90–360** |
| Lawful hosted alternative for anchors (comparison) | Mapbox 100k isochrones/month free but requires Mapbox map display; Stadia/TravelTime/ORS priced per request and need inbound-routing and data-rights checks | same |

Tier 0 (static + public dev-only routing) is for development only. Tier 2 adds a transit router box (+$25–45). **Recommendation: Tier 1, provisional pending G2 and a total-cost comparison with a lawful hosted alternative.** Developer time dominates every tier.

---

## 6. Gates

Order matters: G6 and the geocoding contract precede the first ingest; G5a precedes heavy architecture work; G2 and G4 precede Phase 1 release; G1 and G3 are optimizations/fallback decisions that need not block a working slice.

| Gate | Question | Method | Pass criterion |
|---|---|---|---|
| **G6 POI coverage and licence** (first) | Which source per wedge category; is lineage clean? | Audit 200 Triangle POIs across the wedge categories; precision/recall/duplicates/licence per source; collector fail-closed test | Per-category source table; zero rows with unknown licence |
| **G5a Early interaction comparison** | Address-first direct entry vs "describe it": which gets households to a trusted region with fewer errors? | Clickable prototypes, 3–5 households, counterbalanced equivalent scenarios; include an impossible search, an ambiguous address, outside-coverage location; phone-first participants; paired fairness prompts | Decides entry-mode prominence and whether people grouping is exposed; records transit need |
| **G2 Valhalla NC self-host** | Does the NC build fit the box; anchor latency; many-destination category build cost? | WSL2/Docker build; serve on 8 GB VPS; 100 representative anchors vs public Valhalla and one hosted API; one category layer by arrival isochrone GeoTIFF | Serving RSS measured; 25-min drive p95 < 800 ms, 45-min < 2 s at 5–10 concurrent; category layer build time recorded |
| **G4 Listings handoff** | Do portal links carry bounds and filters on desktop, iOS, Android, and return cleanly; how much leakage? | 20 generated regions × 4 portals × 3 devices; URL-contract test; leakage ratio (box area / region area); owner reads RentCast licence if pins wanted | ≥ 90% of links correct on all devices for ≥ 2 portals with broken links counted; leakage reported; **owner accepts or rejects city/ZIP fallback** |
| **G5b Working-slice usability** | Does the Phase 1 slice let households find and trust a region, detect errors, and reach listings? | 06 §7 script revised per 09 A4: unprompted discovery, failure tasks, error-detection success criteria, no repeated-task learning | ≥ 5/6 complete core tasks unaided; every participant catches the seeded wrong result; stated understanding of each card |
| **G1 Own-graph precompute (optional)** | Is transposed-graph csgraph Dijkstra cheaper than Valhalla batch at acceptable boundary error? | End-to-end timing (CSR build, transpose, snapping, Dijkstra, encoding); absolute error and false in/exclusion near thresholds vs Valhalla arrival isochrones; one-way/turn-restriction samples | Adopt only if build cost or latency benefit is material and threshold errors are within owner-accepted commute uncertainty |
| **G3 Browser rendering** | Can a mid-range phone threshold six layers and polygonize under budget? | Worker algebra over a metro viewport; MapLibre raster styling on the pinned version; d3-contour; compare raster vs H3 only if raster fails | Slider-to-repaint < 100 ms; first paint < 1.5 s on throttled 4G; else server-rendered mask |

---

## 7. Phased roadmap

- **Phase 0 — Foundations and early gates (2–3 weeks).** G6; geocoding provider contract; Valhalla NC build and G2; G5a clickable comparison; G4 listings test; `v2/core` copied from localUpdates with fail-closed licensing.
- **Phase 1 — The first complete slice (friends and family).** Two resolved workplace anchors with arrival semantics; ~8 category layers (drive/bike/walk) built by Valhalla arrival isochrones; direct-entry criteria cards (NL optional early, per G5a); hard limits with previewed relaxation; "why is this out?" listing all failing constraints; explicit failure states; versioned, redacted share URLs; listings handoff as accepted at G4; MapLibre SPA with Worker algebra or server mask. **Usable only when all of these exist** (09 B1).
- **Phase 2 — Language and evaluation.** NL → Query delta behind the localUpdates seam with spatial golden queries and dimensional validation; G5b on the working slice; prominence of NL decided; accessibility contract tested.
- **Phase 3 — Depth, on evidence.** Scheduled-anchor transit prototype if G5 found a transit-dependent user; own-graph precompute if G1 pays off; neighborhood names with a chosen boundary source and denominator; RentCast pins if licence passes; Tier B anchors-only coverage elsewhere in the US with explicit boundaries; PostGIS review on the §4 trigger.
- **Later wedges.** Hotels: transient-event anchors + affiliate deep links. Site selection: region → block-group apportionment → ACS/LODES/AADT summary.

---

## 8. Deferred on purpose

Numeric weights and soft fringes; heat-map default; transit category surfaces; booking flows; foot-traffic data; void analysis; Google/Yelp live enrichment in the UI; auth/accounts; second precomputed metro; voice input; native mobile; context layers (parcels, flood, schools' grades, crime, noise, canopy, broadband, walkability, elevation); "rush hour"/"worst case" labels; homes-inside counts.

---

## 9. Risk register

| Risk | Severity | Control |
|---|---|---|
| Arrival-direction error produces false drive regions | Critical | Valhalla arrival semantics in the slice; transposed graph if own-graph adopted; G1/G2 near-threshold tests |
| Listings links break, drop filters, or leak geography | High | G4 device matrix, leakage metric, owner-decided fallback, adapter pattern |
| Private addresses exposed in shared URLs or telemetry | High | Redacted-by-default versioned query; deliberate sharing; redacted analytics |
| Google Places content cached beyond `place_id` | High | `place_id` only; registry row with exact clause |
| Boundary errors mislead relocation decisions | High | Absolute-error and false in/exclusion reporting; owner-set acceptable commute uncertainty; truthful labels |
| Single box OOMs | High | 8 GB baseline; measured RSS at G2 |
| Browser algebra too slow on phones | Medium | G3; server-rendered mask fallback |
| ODbL ambiguity | Medium | No entity merge in v1; lineage; qualified advice before monetization |
| Overture licence fail-open | Medium | Fail-closed collector; G6 |
| Steering via inferred suggestions | Medium | No cohort inference; neutral palette; paired-prompt tests |
| Unnoticed misparse (Phase 2) | Medium | Echo + card highlight; error-detection success criteria in G5b |
| Scope creep | Medium | §8 list; phase gates |

---

## 10. Verification backlog, ordered by first use

**Before the first slice:** Valhalla arrival semantics on one-way streets and turn restrictions; geocoding provider terms and right to persist coordinates; Zillow/Redfin/Realtor/Trulia link behavior across devices and current linking terms; licences of every ingested source (Overture release manifest, OSM, GTFS); recovery behavior for routing/data failures; NC Valhalla build and serving measurements; MapLibre raster styling on the pinned version.

**When the integration enters scope:** Google Places field terms; RentCast licence and provenance; Doorify local IDX rules and a willing broker; Amadeus status; Transitous and FOSSGIS terms; parcel and neighborhood boundary licences (Wake, Orange, Durham); OSM/Overture Collective Database posture (counsel) before monetization.

---

## 11. Owner decisions (received 2026-11-03)

1. **Spending ceiling:** Tier 1, roughly $20–35/month. Confirmed.
2. **Acceptable commute uncertainty:** about 10% of the user's limit. Gates G1/G2 therefore require median absolute error at the threshold ≤ 10% and p90 ≤ 20%, with false inclusion/exclusion reported. Labels say "estimated".
3. **Transit:** include early; it is the complex case worth learning from. A **transit scheduled-anchor experiment joins Phase 0** (Valhalla multimodal with the seven Triangle GTFS feeds versus MOTIS self-host versus r5py batch), and a transit mode is in scope for the first slice if it passes.
4. **Listings fallback:** a city/ZIP link plus the exact region on our map is acceptable if bounded links prove fragile. G4 informs but cannot block Phase 1.
5. **Privacy:** not a priority now. Shared URLs carry the full query including anchors (useful for couples); redaction is revisited before any public release. The §3.1 privacy bullet is downgraded accordingly.
6. **Routing-engine order:** decide by experiment. Trust order: **experimental results, then the research, then our priors.** Phase 0 builds both the Valhalla path and the transposed-graph csgraph path on a small slice and chooses on measured build cost, latency, and boundary error against decision 2.

Deferred questions (not needed now): second metro candidate; brokerage/Doorify conversation.

---

## 12. Codex absorption record

**Pass 1 (07):** C1 arrival-direction → §2.4, §3.3, §3.6, G1/G2. C2 Google caching → §3.4. C3 listings → §3.5, G4. H1 memory → §3.2, §5. H2 estimates → §2.3, §5, gates. H3 ODbL → §3.4. H4 fail-open → §3.6. H5 grid → §4. H6 transit → §4. H7 interaction → §3.1, §4. H8 IDX → §3.5. H9 MapLibre → §3.2. H10 timing → G1. M1–M8 → §5, §3.4, §4, labels.

**Pass 2 (09):** B1 Phase 1 dependencies → §7 (anchors, geocoding, explanations, handoff moved into Phase 1; gate ordering fixed). B2 accuracy reference → §3.3, G1/G2 criteria, owner decision 2. B3 budget → §5 (itemized, Mapbox 45-minute error corrected, display restriction noted, Tier 1 provisional). B4 interaction settledness → §3.1 reframed as hypotheses; citation audit corrections in §2. B5 privacy/geocoding/failure states → §3.1, §3.2. B6 handoff acceptance → §3.5, G4, owner decision 4. B7 tiered geography → §3.7. B8 backlog and owner questions → §10, §11. A1 wireframe truthfulness → §3.1 labels, §8. A2 soft semantics → §3.1, §4. A3/A4 evidence and test design → §3.1, G5a/G5b. A5 fairness → §3.1, §9. A7 accessibility → §3.1. A8 hidden weights → §3.1, §4. Counter-resolutions adopted: single engine first; freeze square grid; DuckDB trigger narrowed; transit "any user" rule; hard + relaxation; static estimate only; TripAdvisor wording.
