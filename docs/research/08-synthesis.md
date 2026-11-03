# V2 Synthesis and Recommendation

**Date:** 2026-11-03 · **Status:** DRAFT v0.1, written after research streams 00–06, before Codex adversarial pass 1 landed. Will be revised against `07-codex-adversarial-review.md` and then re-reviewed by Codex (pass 2) before planning.
**Inputs:** `00-existing-assets-audit.md`, `01-consumer-landscape-home-search.md`, `02-landscape-hotel-and-site-selection.md`, `03-open-source-landscape.md`, `04-data-sources-and-legal.md`, `05-routing-and-precompute-architecture.md`, `06-ux-and-interaction-model.md`, and the kickoff decisions in `../plans/2026-11-03-v2-rethink-decisions.md`.

---

## 1. What we are building

A map-first location finder in which a person (or a couple) says in plain language where they need to be and how they get there, and the system turns each clause into a visible, editable **criteria card** — "Sam drives to Fidelity RTP in ≤ 25 minutes", "10-minute walk to a park", "bikeable to a grocery store", "≤ 45 minutes to RDU" — and draws the **region** where all cards hold, names the neighborhoods inside it, and hands the user to real listings bounded to that region. The wedge is home search in the Research Triangle. The same engine (travel-time surfaces per mode + constraint algebra + region enrichment + deep-link adapters) later serves hotel stays near an event venue and small-business site selection with Census demographics.

What is new relative to V1: the constraint set is the product, not a form; categories are precomputed coverage layers rather than live Overpass queries; the LLM parses intent but never produces geography; results are explainable per cell; and listings are one click away.

---

## 2. Headline conclusions from the research

1. **The gap is real and 15 years old.** No live US product shows where *two* commutes plus amenity layers intersect; users have asked for it on Hacker News since 2011 and Homesnap's 2018 attempt failed. The UK's Jitty is the nearest analogue (01 §1, §4).
2. **Natural language is table stakes, not the differentiator.** Four US portals shipped AI search between Oct 2025 and Aug 2026. The winners translate the sentence into *visible, editable* filters; chat-only products (Flyhomes, Sierra-style) have died or drawn "broken promise" reviews (01 §1, 06 §1).
3. **The interaction model is settled by two independent streams:** a hybrid where language builds a structured `Query` shown as cards over the map, with chat, card controls, and map gestures as three equivalent edit paths (01 §5, 06 §5). Hard AND by default; per-card soft flag; no numeric weights in v1.
4. **The compute problem is smaller than V1 made it look.** Per-cell "minutes to nearest POI of type T by mode M" rasters for the Triangle at 100 m are ~570k land cells; 75 layers as uint8 are tens of MB compressed and compute in well under an hour with scipy csgraph instead of networkx (05 §1, §3). V1's 30 s–8 min queries were Overpass-at-request-time, which goes away.
5. **Arbitrary anchors (an office, a friend's house) are one on-demand isochrone each**, sub-second to ~2 s from self-hosted Valhalla on a $10/month VPS; the public FOSSGIS demo server V1 depends on is dev-only (05 §1, 03 §1).
6. **The cheapest robust serving tier is static files**: uint8 layers as PMTiles or COGs plus an Overture places GeoParquet on Cloudflare R2 (free egress), SPA on Cloudflare Pages, raster algebra in a Web Worker so a slider never round-trips (05 §4–5, 03 §4ii).
7. **Listings are reachable legally for free, but only as deep links.** Zillow accepts `searchQueryState` with `mapBounds`; Redfin accepts `viewport=N:S:E:W`; neither accepts a polygon. RentCast's free developer tier (50 req/month) gives real listing pins for prototyping with storage rights; MLS/IDX data needs a participating-brokerage partner (04 §1, §4).
8. **The POI base is Overture Places (CDLA-Permissive) with OSM kept in a separable table**; TripAdvisor is dropped (deprecated API, no-database and no-commingling terms); Google Places only live, `place_id` only stored (04 §1, 00 §1).
9. **Most of the reusable code is not in V1.** CHCCS_geospatial holds the gridded multi-source Dijkstra engine; localUpdates holds the tested store/geocode/Overture/provenance core, the NL → frozen-filter pattern, and the only eval harness. V1 contributes ~250 lines of ideas and a live bug (minutes treated as miles) that the new design makes impossible by construction (00 §1, §6).
10. **Hotels and site selection are served by the same engine later**: the hotel market expresses proximity as straight-line distance and has no transit-isochrone product; site-selection incumbents cost $700–$34k/year while the data a small operator needs (ACS, LODES, AADT, Overture, parcels) is free (02 §1).

---

## 3. Decisions the research settles

### 3.1 Interaction model (kickoff decision 3, deferred → now recommended)

Adopt the hybrid described in `06 §5`: one `Query` object (`people[]` with places/mode/minutes/time-of-day/hard|soft, `amenities[]`, `budget?`, `quality[]`, `region_hint`); the LLM's only job is NL → Query delta plus disambiguation; the geo engine produces every region and pin. First-run: map already visible, one input with a real example placeholder, four starter cards, cards stream in as parsed with per-card progress, first visible change ≤ 1 s and whole sentence ≤ 10 s. Results: region first (polygon with graded soft fringe), named neighborhoods with fit %, listings/places inside. Correction: per-card edit/mute/delete, tap-anywhere "why is this out?" with real numbers and one-tap relax, chat critiques echoed as card changes. Persistence: the full `Query` in a shareable URL so a couple can co-edit (01 §5 item 7). Two-person household: `Person` is a first-class object with a two-colour overlap view.

Why not chat-first: LLMs invent geography in public demos and users cannot see which clause was misread (06 §6). Why not form-first: it is V1, and multi-person × multi-mode × multi-amenity makes the form the clunkiness (06 §6).

### 3.2 Architecture (hybrid, static-first)

Adopt option C from `05 §8`:

```
 PRECOMPUTE (Windows box, monthly)                 STATIC TIER (Cloudflare, $0)
 Geofabrik NC PBF - osmium clip -> graphs/mode     R2:  layers/{metro}/{mode}/{category}.pmtiles|cog (uint8 minutes)
 Overture places (monthly) -----> POIs/category         places/{metro}.parquet (Overture + separable OSM)
 csgraph multi-source Dijkstra -> uint8 rasters         neighborhoods/{metro}.fgb, metadata.json
 (CHCCS engine, ported) --------> COG/PMTiles ---> Pages: SPA (MapLibre GL JS, Worker raster algebra, DuckDB-Wasm)

 ON-DEMAND TIER (one VPS, ~$10/mo)                 BROWSER
 Valhalla (NC tiles) <- FastAPI -> /isochrone-grid  fetch viewport tiles -> AND/threshold/soft-score in Worker
 own graph in RAM     -> /custom-category           -> canvas layer -> d3-contour polygon -> POIs/listings inside
 DuckDB (listings, cache, logs) -> /nl/parse (LLM)  -> criteria cards <-> Query state <-> URL
```

Choices inside it: MapLibre GL JS replaces Leaflet (03 §1); COG vs raster PMTiles decided by Spike 5; MapLibre `color-relief` cannot threshold arbitrary rasters yet, so the Worker + canvas path is the baseline (05 §1). Precompute runs locally and publishes artifacts; the API stays small because the hot path is static. If the API is down, category constraints still work.

### 3.3 Routing engines

Self-hosted Valhalla on the NC extract (MIT, isochrones + matrix + GeoTIFF output + multimodal) for anchors and as the accuracy reference; in-house csgraph Dijkstra with the CHCCS speed model for category layers **pending Spike 2** (if drive error exceeds median 20% / p90 35% after recalibration, drive layers switch to Valhalla GeoTIFF grids). OSRM has no isochrones; GraphHopper is the fallback engine (03 §1). Public FOSSGIS Valhalla is dev-only at ≤ 1 req/s.

### 3.4 Data stack and legal posture

Per `04 §4–5`: stored commercial-safe core = Overture Places (confidence ≥ 0.85), separable `osm_poi`, ACS 5-year block groups, LODES, NCDOT AADT, FEMA NFHL, NCES EDGE + NC report cards, PAD-US + municipal parks, EPA Walkability, BTS noise, NLCD canopy, county parcels (Wake CC BY 4.0 daily; Orange annual; Durham to verify), GTFS for seven Triangle agencies. Live-only: Google Places (`place_id` only), AirNow. Rules: never scrape; hold no MLS data without a licence; OSM separable; attribution registry row before any layer is ingested; facts not expression.

### 3.5 Listings linkage (kickoff decision 7)

A `ListingLink` adapter emits per-region deep links: Zillow (`searchQueryState.mapBounds` = envelope + price filters), Redfin (`viewport`), Realtor.com/Trulia (patterns to verify), rentals via Zillow Rentals/Apartments.com. Our map keeps the true polygon and says plainly that the portal shows its box. Prototype listing pins from the RentCast developer tier (free, 50 req/month) clearly labelled. Public/monetized pins require a Doorify MLS participant brokerage controlling an IDX display component (Policy 7.58). County assessor data gives housing stock, recent sales and price levels inside any polygon for free, forever.

### 3.6 Code reuse (kickoff decision 5)

Follow `00 §6` in order: copy localUpdates core (models, store seam, DuckDB store, geocoder chain, Overture collector, provenance) with tests into `v2/core/`; port the CHCCS engine as pure functions parameterized by boundary/destinations/mode/speed profile/CRS with a Dijkstra cutoff and COG output into `v2/traveltime/`; rebuild V1's progressive filter as raster algebra in `v2/compose/`; wrap V1's Valhalla client for the on-demand path; port the NL seam and eval harness with spatial golden queries. Do not copy TripAdvisor code, the untracked `backend/test_*.py` scripts (hard-coded API key), the Streamlit PoC, or the V1 frontend.

---

## 4. Where the streams disagreed, and how this synthesis resolves it

| Topic | Positions | Resolution | Decided by |
|---|---|---|---|
| **H3 hexes vs square rasters** | 01: leaders (TravelTime, Jitty) moved to H3 for legibility/performance. 03: H3-keyed GeoParquet + COG. 05: square rasters are what every tile/COG toolchain expects. | Compute and store as square rasters (toolchain, Worker math). Hex is a *presentation* option: resample to H3 r9/r10 at render time if usability testing shows squares read badly. Use H3 as an optional index key for POIs/neighborhood joins only. | Spike 4 + usability test task 1 |
| **DuckDB vs PostGIS** | 04 labels the stored core "PostGIS". 03/05 and the audit favour DuckDB (embedded, GeoParquet-native, Wasm, already behind a `Store` seam). | DuckDB for v2.0. The `Store` seam exists precisely to swap in PostGIS when multi-user writes, licensed listings, or a second metro's concurrency demand a server DB. | Revisit at Phase 3 |
| **Transit** | 02: wait-time-aware transit surfaces are a must-have because no competitor sells them. 05: time-dependent; precompute categories at 250 m with r5py, defer on-demand transit anchors. 03: Transitous for prototyping only (non-commercial, ~720 req/day). | v2.0 ships drive/bike/walk. Transit category layers (weekday 8–9 am window, median) are Phase 3 via Spike 7. On-demand transit anchors wait until a JVM router is worth hosting. The hotel wedge, where transit matters most, is after Phase 3 anyway. | Spike 7 |
| **Hard vs soft constraints** | 01: hard default, soft ranking later. 05: store minutes so scoring is a pure client function. 06: hard AND default, per-card soft flag, no numeric weights in v1. | Exactly 06's answer, enabled by 05's representation. Weights only if usability testing surfaces "how much more important is X than Y". | Usability test |
| **Drive layers: own Dijkstra vs Valhalla** | 00/05: CHCCS speed model is transparent and tunable but ignores one-ways, turn costs, signals as Valhalla models them. 03: Valhalla GeoTIFF is the engine-side equivalent. | Own Dijkstra for walk/bike (accuracy is less sensitive); drive decided by Spike 2 thresholds. | Spike 2 |
| **Peak vs off-peak driving** | 01: rush-hour toggle is the one time-of-day control every portal ships. 05: no traffic data in OSM-based routers. 06: "worst case" toggle must not outrun the data. | Ship "typical" with an honest label; offer "worst case" as a documented slower speed profile (e.g. ×0.7 on arterials) until a traffic source exists. Do not promise departure-time precision. | Phase 2 |
| **TripAdvisor** | 00: drop. 04: deprecated API and incompatible terms. V1 built a feature on it. | Drop, including the Premium Search UI. Live enrichment, if ever, is Google Places with `place_id`-only storage and branding compliance. | Settled |

---

## 5. Budget tiers (kickoff decision 4, deferred → owner to choose)

All numbers from `05 §5.2` and `04`; LLM costs are my estimate: a parse is ~2–4k tokens in, <1k out; at friends-and-family volume (≤ 500 parses/month) that is well under $5/month on a mid-tier model, and cacheable.

| Tier | Monthly cost | What you get | What you give up |
|---|---|---|---|
| **0 — Static only** | $0 (+ domain) | Precomputed layers + places on R2/Pages; Worker algebra; anchors via public FOSSGIS Valhalla at ≤ 1 req/s (dev-only terms) or Mapbox free tier (60-min cap) | No custom categories on demand; "45 min to RDU" fails on Mapbox; not a legitimate production dependency chain |
| **1 — Hybrid (recommended)** | ~$10 (Hetzner CX33-class or Fly 2–4 GB) + ≤ $5 LLM | Everything in Tier 0 plus self-hosted Valhalla NC, FastAPI anchors/custom categories/listings cache, RentCast dev tier pins | On-demand transit anchors |
| **2 — Hybrid + transit + paid pins** | $25–50 | Tier 1 plus a 4–8 GB box for a MOTIS/OTP transit router or r5py batch, RentCast Foundation ($74 would push this to ~$100) | — |

Recommendation: **Tier 1.** It is the smallest configuration whose every dependency is acceptable for a later public product, and it scales to ~10k monthly users at $10–25.

---

## 6. Phased roadmap (shape only; the detailed plan follows owner feedback)

- **Phase 0 — Spikes (1–2 weeks).** Run `05 §9` spikes 1–6, 9, 10 on the Windows box: Triangle precompute benchmark, accuracy vs Valhalla, self-host Valhalla NC under WSL2/Docker, browser raster algebra, R2 delivery, custom category on demand, `color-relief` trick, Overture coverage. Each has a stated success criterion. Also verify the load-bearing claims in §9.
- **Phase 1 — Region engine + static map (Triangle, drive/bike/walk).** `v2/core` from localUpdates; `v2/traveltime` from CHCCS; ~12 categories × 3 modes published to R2; MapLibre SPA with criteria cards (no NL yet), Worker algebra, polygon output, POIs inside, Zillow/Redfin deep links, URL-persisted Query. Fixes V1's bug by construction.
- **Phase 2 — Language, anchors, explainability.** NL → Query delta tool with the localUpdates seam and spatial golden queries; self-hosted Valhalla anchors; "why is this out?"; soft fringe; worst-case profile; friends-and-family usability test (`06 §7`, 6 participants, 7 tasks).
- **Phase 3 — Depth.** Transit category layers (Spike 7); named neighborhoods with fit %; RentCast pins; context layers (schools, flood, noise, canopy); second metro to prove the metro-agnostic pipeline; PostGIS decision.
- **Later wedges.** Hotels: transient-event anchors + Expedia/Kayak/Booking deep links. Site selection: region → block-group apportionment → ACS/LODES/AADT summary ("lite Business Analyst").

---

## 7. Risk register (top items)

| Risk | Severity | Mitigation |
|---|---|---|
| In-house drive-time layers disagree materially with Valhalla | High | Spike 2 thresholds; fall back to Valhalla GeoTIFF for drive |
| Browser raster algebra too slow on mobile/4G | Medium | Spike 4; deck.gl shader fallback; 250 m drive layers |
| Zillow/Redfin change or block deep-link schemes | Medium | Adapter pattern; always show our polygon; county assessor data as the stored fallback |
| LLM misparse goes unnoticed | Medium | Echo line + card highlight; seeded misparse in usability test |
| ODbL contagion from OSM-derived rasters | Medium | Separable buckets; treat layers as produced works pending counsel |
| Fair-housing exposure from free-text suggestions | Medium | No neighborhood-quality prose from the model; templated explanations from engine numbers only |
| Public Valhalla used past dev | Low | Tier 1 removes the dependency |
| Scope creep into hotels/site selection before the wedge works | Medium | Phase gates; engine abstractions only where free |

---

## 8. Scope discipline (YAGNI)

Not in v2.0: numeric weights, heat-map default, transit anchors, booking flows, foot-traffic data, void analysis, Google/Yelp live enrichment in the UI, auth/accounts, a second metro, voice input, native mobile. Each is listed so it is a conscious deferral.

---

## 9. Verification backlog before planning (load-bearing "(unverified)" items)

From the streams' open questions; Codex pass 1 will add to this list.

1. Zillow `searchQueryState.mapBounds` link opens correctly on desktop and mobile; drawn regions are opaque `customRegionId` (04 Q2).
2. Redfin `viewport=N:S:E:W` pattern; Realtor.com and Trulia patterns and linking clauses (04 Q3).
3. Doorify MLS vendor/participant terms and whether an analytics licence exists (04 Q1).
4. FOSSGIS Valhalla usage terms text (05 Spike 8).
5. Oracle Always Free capacity reality; Hetzner CX33 price (05 §1).
6. Valhalla NC build time/RAM on WSL2 (03 Q1, 05 Spike 3).
7. MapLibre `color-relief` raster-dem-only limitation still current (05 §1, Spike 9).
8. Amadeus Self-Service shutdown official notice (02 Q3, 04 Q6).
9. Transitous terms and request cap (03 Q3).
10. Zillow commute filter: multiple destinations and rush-hour support (06 Q2).
11. RentCast licence §1 permitted uses and upstream provenance (04 Q5).
12. Durham parcel licence (04 Q7).

---

## 10. Decisions needed from the owner

1. **Budget tier** (recommend Tier 1, ~$10–15/month).
2. **Confirm the interaction model** (hybrid cards-over-map; hard AND default with soft flag; no numeric weights in v1).
3. **Confirm drops**: TripAdvisor/Premium Search, V1 frontend, Streamlit PoC, public Valhalla as production.
4. **DuckDB now, PostGIS later** — acceptable?
5. **RentCast developer tier** for prototype pins — acceptable to sign up?
6. **Second metro** candidate for Phase 3 (needed only to keep the pipeline metro-agnostic).
7. **Appetite for a Doorify MLS / brokerage conversation** now (information gathering) or later.

---

## 11. Review status

- Codex adversarial pass 1 (streams 00–06): **in progress**, output to `07-codex-adversarial-review.md`.
- Codex adversarial pass 2 (this synthesis): **pending**, after revision against pass 1.
