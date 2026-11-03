# V2 Synthesis and Recommendation

**Date:** 2026-11-03 · **Status:** DRAFT v0.2 — revised against Codex adversarial pass 1 (`07-codex-adversarial-review.md`). Awaiting Codex pass 2 on this document and `06-ux-and-interaction-model.md`, then owner review.
**Inputs:** research streams `00`–`06`, Codex pass 1 (`07`), and the kickoff decisions in `../plans/2026-11-03-v2-rethink-decisions.md`.
**How to read this:** §3 states what the research settles; where Codex showed a conclusion rests on an unmeasured estimate, it is labelled **hypothesis** and tied to a numbered gate in §6. Nothing marked hypothesis should be built on until its gate passes.

---

## 1. What we are building

A map-first location finder in which a person (or a couple) states where they need to be and how they get there, and the system turns each requirement into a visible, editable **criteria card** — "Sam drives to Fidelity RTP in ≤ 25 minutes", "10-minute walk to a park", "bikeable to a grocery store", "≤ 45 minutes to RDU" — and draws the **region** where all cards hold, then hands the user to real listings bounded to that region. The wedge is home search in the Research Triangle. The same engine (travel-time surfaces per mode + constraint algebra + region enrichment + deep-link adapters) later serves hotel stays near an event venue and small-business site selection with Census demographics.

What is new relative to V1: the constraint set is the product, not a form; amenity categories are precomputed coverage layers rather than live Overpass queries; the language model, when present, parses intent but never produces geography; every exclusion is explainable with real numbers; listings are one click away.

---

## 2. Headline conclusions

1. **The gap is real and old.** No live US product shows where *two* commutes plus amenity layers intersect; the request recurs on Hacker News from 2011 onward; Homesnap's 2018 multi-destination attempt failed; the UK's Jitty is the nearest analogue (01 §1, §4).
2. **Natural language is table stakes, not the differentiator.** Four US portals shipped AI search between Oct 2025 and Aug 2026. Chat-only products have died or drawn "broken promise" reviews (01 §1, 06 §1). Codex (07 H7) is right that the engagement metrics cited for "NL plus visible filters" do not isolate the interaction model; see §3.1.
3. **The compute problem is tractable, but its size is a hypothesis.** Per-cell "minutes to nearest POI of type T by mode M" rasters for the Triangle at 100 m are ~570k land cells; 75 uint8 layers are ~71 MB raw (05 §3). Compressed size, build time, and serving cost are estimates until Gate G1 measures them (07 H2, H10, M2).
4. **Reusable routing code has a correctness flaw that must be fixed on port.** The CHCCS engine runs Dijkstra outward from destinations after forcing every road bidirectional. For drive (and bike) that answers the wrong question on one-way streets. The port must run from destinations on the **transposed** directed graph and be validated against Valhalla reverse isochrones (07 C1).
5. **Arbitrary anchors are one on-demand isochrone each**, served by self-hosted Valhalla; the public FOSSGIS demo is dev-only (05 §1, 03 §1). Latency and box size are hypotheses until Gate G2 (07 H1, H2, M1).
6. **Static files are the cheapest robust serving tier**: uint8 layers plus a places file on Cloudflare R2, SPA on Pages, raster algebra in a Web Worker (05 §4–5). Whether that beats a simpler server-rendered mask for v2.0 is decided by Gate G3 (07 attack a, H9).
7. **Listings are reachable legally only as deep links today, and the deep links are unproven.** Zillow `searchQueryState.mapBounds` and Redfin `viewport` are undocumented, partly scraper-derived patterns (04 §1, 07 C3). RentCast's full permitted-use list has not been read. Listings handoff is Gate G4 and must pass before Phase 1 ends.
8. **POI base: Overture Places first, OSM by category where Overture is weak, no cross-source entity merge in v1**, so ODbL questions stay simple (04 §1, 07 H3, attack e). The localUpdates collector's fail-open licence default must be made fail-closed on port (07 H4). TripAdvisor is dropped (deprecated API, incompatible terms). Google Places: store `place_id` only, nothing else (07 C2).
9. **Most reusable code is not in V1.** CHCCS holds the grid engine (with the flaw above); localUpdates holds the tested store/geocode/Overture/provenance core, the NL → frozen-filter pattern, and the only eval harness; V1 contributes ~250 lines of ideas and a live bug (minutes treated as miles) the new design makes impossible by construction (00 §1, §6).
10. **Scope must shrink before it grows.** Codex (07 M7) is right that the proposed context layers (crime, school grades, noise, canopy, broadband, slope) expand liability and QA before the wedge is proven. v2.0 is commutes, a short list of amenity categories, the region, and the listings handoff.

---

## 3. Decisions the research settles, and hypotheses it does not

### 3.1 Interaction model (kickoff decision 3) — **settled in shape, hypothesis in emphasis**

Settled: the UI is **map-first with visible, editable criteria cards** over a deterministic region; `Person` is a first-class object; hard AND by default with a per-card soft flag; tap-anywhere "why is this out?" with real numbers; the full `Query` lives in a shareable URL (06 §5, 01 §5). Chat-only is rejected (06 §6). This shape is required under every candidate model, so building it first is not a bet.

Hypothesis (07 H7): that natural-language entry should be the *primary* input rather than a shortcut. The research shows users like NL and that products hide resolved filters, but no source isolates NL's contribution. Resolution: Phase 1 ships direct-manipulation cards (the two-address flow Codex proposes as the strongest alternative); Phase 2 adds NL → Query delta behind the localUpdates tool-use seam; **Gate G5** is a 3–5 household comparison of "describe it" versus direct entry on time-to-trusted-region and correction count, which decides how prominent the input box is. Either way the engine, cards, and explainability are the same.

Rush hour (07 M6): there is no traffic data in OSM-based routers. The UI will say **"modeled commute profile"**, never "rush hour", and offer a documented slower profile as "worst case" only after Gate G1 reports its error against Valhalla.

### 3.2 Architecture — **hybrid static-first is the working hypothesis; server-first is the fallback**

Working hypothesis (05 §8 option C):

```
 PRECOMPUTE (Windows box, monthly)                 STATIC TIER (Cloudflare, $0)
 Geofabrik NC PBF - osmium clip -> directed graphs R2:  layers/{metro}/{mode}/{category} (uint8 minutes)
 Overture + OSM-by-category -----> POIs/category         places/{metro}.parquet (source-native records)
 csgraph Dijkstra on TRANSPOSED graph -> rasters         neighborhoods/{metro}.fgb, manifest.json
 (CHCCS engine, ported + fixed) -> COG/PMTiles --> Pages: SPA (MapLibre GL JS, Worker raster algebra)

 ON-DEMAND TIER (one VPS, 8 GB until measured)     BROWSER
 Valhalla (NC tiles) <- FastAPI -> /isochrone-grid  fetch viewport tiles -> AND/threshold/soft in Worker
 CSR graph in RAM     -> /custom-category           -> canvas layer -> polygonize -> POIs/listings inside
 DuckDB (cache, logs) -> /nl/parse (LLM, Phase 2)   -> criteria cards <-> Query state <-> URL
```

What Codex changed: the VPS baseline is **8 GB** until peak RSS is measured with a CSR graph (07 H1); anchor grids must be **compressed and viewport-clipped**, not ~1 MB raw per anchor (07 H2); the MapLibre `color-relief` limitation is **version-specific** and the Terrarium-elevation trick is dropped unless a tiny spike proves it (07 H9); and a **server-rendered PNG mask + GeoJSON** path is kept as the fallback if browser algebra fails Gate G3 on a mid-range phone (07 attack a). Leaflet → MapLibre migration stands (03 §1).

### 3.3 Routing engines — **Valhalla is the single routing truth until own-graph layers pass accuracy gates**

Self-hosted Valhalla on the NC extract (MIT; isochrones, matrix, GeoTIFF output, multimodal) serves anchors and is the accuracy reference. Own-graph csgraph Dijkstra for category layers is a hypothesis with two gates: correctness on the transposed directed graph with one-way streets (07 C1) and accuracy thresholds (walk/bike median error < 15%, p90 < 30%; drive median < 20%, p90 < 35%; 05 Spike 2). If drive fails, drive layers come from Valhalla GeoTIFF grids. OSRM lacks isochrones; GraphHopper is the fallback engine (03 §1). Public FOSSGIS Valhalla stays dev-only at ≤ 1 req/s; a hosted API (Mapbox/ORS) is the development fallback for anchors until the NC build exists (07 attack d).

### 3.4 Data stack and legal posture — **settled rules, reduced v2.0 scope**

Rules (04 §5, hardened by 07): never scrape; hold no MLS data without a licence; Google Places persists `place_id` only; OSM and Overture records stay source-native with lineage and **no cross-source entity merge in v1** (07 H3); ingestion fails closed on unknown licences (07 H4); every layer has a source-registry row before ingest; facts not expression.

v2.0 stored layers (07 M7 applied): Overture Places and OSM-by-category for the wedge amenity set (parks, groceries, schools as places, coffee, pharmacies, transit stops, trailheads, playgrounds — final list by Gate G6 coverage audit); county parcel centroids for "homes exist here" counts (Wake CC BY 4.0; Orange; Durham licence to verify); neighborhood boundaries (source to pick: Census places/CDPs plus municipal neighborhood layers); GTFS stop locations only (no transit routing). Deferred to a later phase and only on user request: ACS demographics, LODES, AADT, FEMA NFHL (flood is the first candidate to add), schools' grades, crime, noise, canopy, broadband, walkability index, elevation.

### 3.5 Listings linkage (kickoff decision 7) — **approach settled, mechanism is Gate G4**

A `ListingLink` adapter emits per-region deep links; our map always shows the true polygon and says plainly that the portal shows its box. Gate G4 (07 C3): generate 20 representative Triangle regions, open Zillow/Redfin/Realtor.com/Trulia links on desktop, iOS and Android, confirm bounds and filters survive, and write a URL-contract test; read the full RentCast licence and provenance before any pin is shown; keep a **fallback of city/ZIP portal links plus county parcel context** if bbox links prove fragile. IDX via a Doorify participant brokerage is a **future option, not the plan** (07 H8): it needs written confirmation of local rules and a willing broker.

### 3.6 Code reuse (kickoff decision 5) — **settled, with two corrections**

Follow `00 §6` in order, with: (a) the CHCCS port replaces `_ensure_bidirectional` with per-mode directed graphs and runs Dijkstra on the transpose (07 C1); (b) the localUpdates Overture collector's `_license_for_row` fails closed and derives licence from the pinned release manifest (07 H4). Do not copy TripAdvisor code, the untracked `backend/test_*.py` scripts, the Streamlit PoC, or the V1 frontend.

---

## 4. Where the streams disagreed, and the resolution after Codex

| Topic | Positions | Resolution | Gate |
|---|---|---|---|
| **H3 hexes vs square rasters** | 01: leaders moved to H3. 03: H3-keyed GeoParquet + COG. 05: square rasters fit every tile/COG toolchain. 07 H5: H3 r10 cells average ~0.015 km², ~50% larger than a 100 m square; not a drop-in; leave open and prototype both. | Compute on square rasters (toolchain) as the working choice; build the two-commute view both ways in Gate G3 and choose on mobile payload, visual stability, join complexity, boundary error. | G3 |
| **DuckDB vs PostGIS** | 04 labels the core "PostGIS"; 03/05/00 favour DuckDB behind the existing `Store` seam. 07 M8: define migration thresholds. | DuckDB for v2.0. Migrate to PostGIS when any holds: concurrent writers > 1 service, licensed listings requiring row-level access control, second metro with shared users, or p95 query > 500 ms on DuckDB. | Phase 3 review |
| **Transit** | 02: must-have from the start. 05: time-dependent, precompute categories only, defer anchors. 07 H6: product decision; ask households. | v2.0 ships drive/bike/walk. Usability interviews (Gate G5) ask whether transit is a purchase constraint; if ≥ 2 of 5 households say yes, Phase 3 adds one scheduled AM transit surface (05 Spike 7); otherwise deferred. | G5 |
| **Hard vs soft constraints** | 01: hard default, soft later. 05: store minutes so scoring is client-side. 06: hard AND + per-card soft flag, no numeric weights in v1. | Adopt 06. Weights only if Gate G5 surfaces "how much more important is X than Y". | G5 |
| **Drive layers: own Dijkstra vs Valhalla** | 00/05: own model is transparent but ignores one-ways, turns, signals. 07 C1/H10: direction and end-to-end timing unproven. | Valhalla is the reference; own-graph drive layers only if Gate G1 passes correctness and accuracy. | G1 |
| **Peak vs off-peak** | 01: every portal ships a rush toggle. 05: no traffic data. 06/07 M6: do not call a static profile rush hour. | "Modeled commute profile" label; "worst case" slower profile only after G1 reports its error. | G1 |
| **Interaction emphasis** | 01/06: NL builds visible cards. 02: AI competitors hide filters. 07 H7: evidence does not isolate NL. | Cards first (Phase 1), NL second (Phase 2), prominence decided by G5. | G5 |
| **TripAdvisor** | 00/04: drop. | Dropped, including Premium Search. | — |

---

## 5. Budget tiers (kickoff decision 4) — **owner to choose; numbers are ranges, not quotes**

Codex (07 M3, H2) is right that the $10–25 figure was a best case. Revised with 3× burst headroom, backups, monitoring, and rebuild compute; LLM costs assume ≤ 500 parses/month at 2–4k tokens each.

| Tier | Monthly (friends & family) | Monthly (10k users, 3× burst) | What you get | What you give up |
|---|---|---|---|---|
| **0 — Static only** | $0 + domain | n/a (not a legitimate production chain) | Precomputed layers on R2/Pages; anchors via public FOSSGIS Valhalla (dev-only) or Mapbox free tier (60-min cap) | Custom categories; "45 min to RDU" on Mapbox; production legitimacy |
| **1 — Hybrid (recommended)** | $15–25 (8 GB VPS $12–20, LLM ≤ $5, backups/monitoring) | $40–80 (second node or managed fallback, R2 overage headroom) | Self-hosted Valhalla NC + FastAPI anchors/custom categories, RentCast dev tier pins if licence permits | On-demand transit anchors |
| **2 — Hybrid + transit** | $40–70 | $90–150 | Tier 1 + a 4–8 GB box for MOTIS/OTP or r5py batch; RentCast Foundation adds $74 | — |

Recommendation: **Tier 1**, provisioned at 8 GB and downsized only from measured peak RSS (07 H1). Developer time, not hosting, is the dominant cost at every tier.

---

## 6. Gates (Phase 0) — what must be measured before planning the build

Each gate is a spike with a success criterion; the spikes in `05 §9` are the method. Gates G1–G4 are blocking for Phase 1; G5–G6 are blocking for Phase 2.

| Gate | Question | Method | Pass criterion |
|---|---|---|---|
| **G1 Routing correctness and speed** | Does own-graph Dijkstra on the transposed directed graph match Valhalla, and how long does an end-to-end layer take? | Build NC walk/bike/drive directed graphs (pyrosm/osmium → CSR); port CHCCS snapping; one grocery/walk and one office/drive layer; compare 500 sampled pairs per mode with Valhalla `route` (reverse semantics); time CSR build, reversal, snapping, Dijkstra, encoding separately | Walk/bike median abs error < 15%, p90 < 30%; drive median < 20%, p90 < 35%; else drive via Valhalla GeoTIFF. Full 75-layer build < 60 min, peak RAM < 16 GB |
| **G2 Valhalla NC self-host** | Does the NC build fit the intended box, and what is anchor latency? | Build under WSL2/Docker; serve on an 8 GB VPS; 100 representative isochrones compared with public Valhalla and one hosted API | Serving RSS measured; 25-min drive p95 < 800 ms, 45-min < 2 s at 5–10 concurrent; GeoTIFF grid aligned to our raster |
| **G3 Browser rendering** | Can a mid-range phone threshold six layers and polygonize under budget, in raster and in H3? | Worker algebra over a metro viewport; compressed viewport-clipped anchor grids; MapLibre canvas vs native raster styling on the pinned version; d3-contour; same view in H3 r9/r10 | Slider-to-repaint < 100 ms; first paint < 1.5 s on throttled 4G; polygons valid; otherwise fall back to server-rendered mask |
| **G4 Listings handoff** | Do portal deep links carry bounds and filters on desktop, iOS, Android, and is RentCast usable? | 20 generated regions × Zillow/Redfin/Realtor/Trulia on three devices; URL-contract test; owner reads full RentCast licence and provenance | ≥ 90% of links open with correct bounds on all devices for at least two portals; written RentCast answers on display, caching, monetization |
| **G5 Interaction** | Direct cards vs "describe it": which gets households to a trusted region faster with fewer corrections? Is transit a purchase constraint? | 06 §7 script with 3–5 households on the Phase 1 build plus a clickable NL mock; add two interview questions on transit and weights | Decides NL prominence, transit in Phase 3, and whether weights enter v2 |
| **G6 POI coverage and licence** | Which source per category, and is lineage clean? | Manual audit of 200 Triangle POIs across the wedge categories; precision/recall/duplicates/licence per source; collector fail-closed test | Per-category source preference table; zero rows with unknown licence |

Also before planning: verify the load-bearing claims in §9.

---

## 7. Phased roadmap (shape only)

- **Phase 0 — Gates G1–G4, G6 (2–3 weeks on the Windows box plus one VPS).**
- **Phase 1 — Region engine + direct-manipulation cards (Triangle, drive/bike/walk).** `v2/core` from localUpdates; `v2/traveltime` from CHCCS with the direction fix; ~10 categories × 3 modes to R2; MapLibre SPA with criteria cards, Worker algebra (or server mask per G3), polygon output, POIs inside, URL-persisted Query, listings handoff per G4. Fixes V1's bug by construction. This is already usable by friends and family.
- **Phase 2 — Language, anchors, explainability.** NL → Query delta behind the localUpdates seam with spatial golden queries; self-hosted Valhalla anchors; "why is this out?"; soft fringe; modeled-commute label; Gate G5 usability test.
- **Phase 3 — Depth, on evidence.** Transit surface if G5 says so; named neighborhoods with fit %; RentCast pins if G4 licence passes; flood layer if requested; second metro to prove the metro-agnostic pipeline; PostGIS review against the thresholds in §4.
- **Later wedges.** Hotels: transient-event anchors + affiliate deep links. Site selection: region → block-group apportionment → ACS/LODES/AADT summary.

---

## 8. Risk register

| Risk | Severity | Mitigation / gate |
|---|---|---|
| Directed-graph error in ported engine produces false drive regions | Critical | Transposed-graph contract; G1 validation against Valhalla reverse isochrones |
| Listings deep links break or lose filters; RentCast licence insufficient | High | G4; city/ZIP + parcel fallback; adapter pattern |
| Google Places content cached beyond `place_id` | High | Persist `place_id` only; source-registry row with exact clause |
| Own-graph drive layers inaccurate | High | G1 thresholds; Valhalla GeoTIFF fallback |
| Single 4 GB box OOMs with Valhalla + graph + DuckDB | High | 8 GB baseline; CSR graph; measure RSS in G2 |
| Browser algebra too slow on phones | Medium | G3; server-rendered mask fallback |
| ODbL ambiguity from cross-source merging | Medium | No entity merge in v1; source-native records; counsel before monetization |
| Overture licence fail-open | Medium | Fail-closed collector; G6 |
| NL misparse unnoticed | Medium | Echo line + card highlight; seeded misparse in G5 |
| Fair-housing exposure in suggestions/explanations | Medium | No neighborhood-quality prose from the model; templated explanations from engine numbers |
| Scope creep into context layers and later wedges | Medium | §3.4 deferral list; phase gates |

---

## 9. Verification backlog (load-bearing, from 07 and the streams)

- [ ] Transposed-graph Dijkstra and Valhalla reverse-isochrone semantics on one-way streets (07 C1).
- [ ] Zillow and Redfin bbox links across desktop/iOS/Android; current linking terms (07 C3; 04 Q2–Q3).
- [ ] Full RentCast permitted uses and upstream rights (07 C3; 04 Q5).
- [ ] Google Places Service Specific Terms, field by field (07 C2).
- [ ] NC Valhalla build peak, tile size, serving RSS, GeoTIFF semantics, p95 latency (07 H1, M1; 05 Spike 3).
- [ ] End-to-end Triangle precompute time, memory, accuracy, serialization (07 H10; 05 Spike 1).
- [ ] Browser thresholding and R2 range requests on a mid-range phone, 4G (07 H2; 05 Spikes 4–5).
- [ ] OSM/Overture schema remains a Collective Database under the proposed ETL; counsel before monetization (07 H3).
- [ ] Doorify current local IDX/vendor terms; a willing broker (07 H8; 04 Q1).
- [ ] MapLibre raster styling on the pinned version (07 H9; 05 Spike 9).
- [ ] Amadeus Self-Service status; Oracle free tier dropped from the base case (07 M4, M5).
- [ ] FOSSGIS Valhalla usage terms text (05 Spike 8); Transitous terms (03 Q3).
- [ ] Durham parcel licence (04 Q7); neighborhood boundary source and licence.

---

## 10. Decisions needed from the owner

1. **Budget tier** — recommend Tier 1 at 8 GB (~$15–25/month friends-and-family).
2. **Confirm the interaction shape** — map-first editable cards, hard AND with soft flag, no numeric weights in v1; NL added in Phase 2 with prominence decided by Gate G5.
3. **Confirm the scope cut** — v2.0 is commutes + a short amenity list + region + listings handoff; context layers deferred.
4. **Confirm drops** — TripAdvisor/Premium Search, V1 frontend, Streamlit PoC, public Valhalla as production, Oracle free tier.
5. **DuckDB now, PostGIS on the §4 thresholds** — acceptable?
6. **RentCast** — willing to read and accept its licence for prototype pins (Gate G4)?
7. **Second metro** candidate for Phase 3.
8. **Doorify/brokerage conversation** — now (information only) or later.

---

## 11. Codex pass-1 absorption

| Finding | Severity | How this synthesis responds |
|---|---|---|
| C1 directed-graph reversal | Critical | §2.4, §3.3, §3.6, G1 — algorithm contract changed; validation required |
| C2 Google Places caching | Critical | §2.8, §3.4 — `place_id` only; registry row with clause |
| C3 listings handoff unproven | Critical | §3.5, G4 — gate with device matrix, URL-contract test, fallback |
| H1 VPS memory | High | §3.2, §5 — 8 GB baseline, CSR, measure in G2 |
| H2 estimate chain | High | §2.3, §5, G1–G3 — hypotheses with gates; compressed clipped payloads; p95 at concurrency |
| H3 ODbL separability | High | §3.4 — no cross-source merge in v1; counsel before monetization |
| H4 Overture fail-open | High | §3.6, G6 — fail-closed collector |
| H5 H3 vs raster | High | §4 — both prototyped in G3 |
| H6 transit scope | High | §4 — product decision via G5 interviews |
| H7 interaction evidence | High | §3.1 — cards first, NL second, prominence by G5 |
| H8 IDX feasibility | High | §3.5 — future option, written path required |
| H9 MapLibre limitation | High | §3.2, G3 — version-specific test; Terrarium dropped |
| H10 Dijkstra timing | High | G1 — component timings end to end |
| M1–M8 | Medium | §5 ranges; §3.4 scope cut; §4 PostGIS thresholds; "modeled commute profile"; Amadeus/Oracle to verify/drop |
