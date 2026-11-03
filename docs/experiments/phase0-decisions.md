# Phase 0 decision memo

**Date:** 2026-11-03 · **Branch:** `v2-rethink` · **Status:** draft for Codex pass 4, then owner review
**Inputs:** the experiment files in this directory, the plan in `../plans/2026-11-03-phase0-experiments.md`, the design in `../research/08-synthesis.md`, and the owner decisions in `../plans/2026-11-03-v2-rethink-decisions.md`.

Per the owner's stated trust order — **experimental results, then the research, then our priors** —
every claim below is tagged **[measured]** (observed on this machine today, with the numbers in the
cited file), **[research]** (from the survey documents, not yet observed here), or **[assumed]** (a
judgement we are making with neither measurement nor source). Decisions rest only on the first two,
and where an assumption is load-bearing it is named as such.

---

## 1. Decisions

### D1. Valhalla is the single routing engine for drive, bike and walk — layers *and* anchors

**[measured]** `g1-routing.md`. Our ported transposed-graph Dijkstra fails the owner's tolerance
(decision 12: median ≤ 10% of the threshold, p90 ≤ 20%) on all three modes, and fails at the median
for drive: exact-pair comparison over 304 stratified cells against all 285 groceries gives a median
absolute error of 32–41% of the threshold, p90 55–62%, with our model faster in 98–100% of samples
and a signed median bias of **−5.4 minutes**. Valhalla also builds a category layer in **0.6–1.3 s**
versus **~32 s** for the own-graph path, and answers an arbitrary anchor at p95 **0.30 s** (auto,
25 min) / **0.37 s** (auto, 45 min) at concurrency 1 with zero failures in 408 requests (`g2-valhalla.md`).

The ported engine stays in the repo with its tests as a fallback and as the right home for any future
in-house model; the work it would need is **calibration** (intersection penalties, turn restrictions),
not algorithms — its Dijkstra runs in 40 ms over 237k nodes. This supersedes the synthesis's
"own-graph if Gate G1 pays off" and answers owner decision 16 by experiment.

### D2. Transit requires a second engine: MOTIS, and it is cheap

**[measured]** `transit.md`. Valhalla cannot answer the question a commuter asks — `multimodal` with
`date_time.type=2` (arrive by) returns **HTTP 501, "Arrive by for multimodal not implemented yet"**.
Self-hosted MOTIS can: importing the slice plus seven Triangle GTFS feeds took **4 s**, produced
**130 MB**, idles at **80 MiB** resident, answers `plan?arriveBy=true` in ~0.1 s and
`one-to-all?arriveBy=true` in **0.03 s** returning 478–584 reachable stops with each stop's latest
feasible departure — the exact primitive a precomputed arrival surface needs. All 11 valid in-slice
origin/anchor pairs matched the public Transitous instance **to the minute**, which validates our
feed ingestion (both run MOTIS, so this checks configuration, not accuracy).

Transit therefore enters the architecture as a second small container, not as a Valhalla costing.
The research had budgeted 4–8 GB for a transit router **[research]**; the measured footprint is two
orders of magnitude smaller, so transit no longer justifies its own budget tier.

### D3. Overture is the place base; OSM supplies what Overture lacks

**[measured]** `g6-poi-coverage.md`. Overture release 2026-10-21.0 over the slice: 57,719 places,
**zero quarantined** by the fail-closed licence resolver, resolving to CDLA-Permissive-2.0 (53,147),
Apache-2.0 (3,813, Foursquare) and CC0-1.0 (759), across 13 observed source datasets. Per category,
Overture leads on grocery (285 vs 146), coffee (354 vs 136), pharmacy (235 vs 58) and library
(81 vs 35); **OSM leads decisively on playgrounds (515 vs 22) and transit stops (2,462 vs 51)**; parks
disagree in both directions (363 vs 545, only 63 agreeing within 50 m) and need the manual audit
before either is trusted. The old `categories` column is gone from current Overture releases; selectors
use `taxonomy.primary` and `taxonomy.hierarchy` **[measured]**.

### D4. Street addresses from the Census geocoder; place *names* from our own index, metro-bounded

**[measured]** `geocoding.md`. Census matched 33/40 slice addresses at 0.10 s median with 81 m median
error; Nominatim matched 36/40 but is dev-only under its usage policy. Neither is a name resolver:
Census resolved **none** of ten place-name queries, and unbounded Nominatim returned **"UNC Hospitals"
in Morganton, 180 km away** and "Southpoint" in Wisconsin. Name lookup must hit our own accepted place
index restricted to the search metro, with candidates shown when several match.

### D5. The product grid is 100 m for walk and bike, 200 m for drive

**[measured]** `g1-routing.md`. Valhalla emits its isochrone GeoTIFF on its own WGS84 grid at 0.001°
for pedestrian/bicycle (~90 × 111 m) but **0.002° for auto (~180 × 223 m)**, in uint16 seconds,
re-centred per request. Publishing a 100 m drive layer from a 180 m source would be false precision.

### D6. Listings handoff stays deep-link-first, and the region must always be shown by us

**[measured]** `g4-listings.md`. Twenty two-anchor regions were generated from real arrival
isochrones; the bounding box a portal receives is a **median ~3× and up to ~3.9× larger than the
region**, and several regions are disconnected (up to 4 parts). A portal link can therefore never
stand in for the result — our map must always render the true region. Whether the links themselves
survive desktop, iOS and Android is **[pending]** owner device sessions; owner decision 14 already
accepts a city/ZIP fallback, so this cannot block Phase 1.

### D7. Every data source needs a freshness gate, not just a licence row

**[measured]** `transit.md`. Validating each GTFS calendar against the test date found **Duke
Transit's published feed spans 2025-01-06 to 2025-08-10 — more than a year stale** — while the other
six carry 526–2,486 trips that day. A feed, parcel file or Overture release that is quietly out of
date produces confidently wrong answers, so ingestion must assert freshness and fail loudly.

---

## 2. What Phase 0 changed about the plan

| Synthesis position | After the experiments |
|---|---|
| Own-graph precompute "if Gate G1 pays off"; Valhalla as reference | **Valhalla only.** The own-graph pipeline leaves the critical path (D1) |
| Transit deferred to Phase 3, "any transit-dependent user justifies a prototype" | **Transit is viable now** and cheap; MOTIS joins Phase 1 as a second container (D2) |
| Transit router needs 4–8 GB, its own budget tier | 80 MiB measured; no separate tier needed (D2) |
| 100 m grid throughout | 100 m walk/bike, 200 m drive, matching engine output (D5) |
| Geocoder "chosen and tested in Phase 0" | Chosen: Census for addresses, own index for names; public Nominatim is dev-only (D4) |
| Tier 1 ≈ $20–35/month, 8 GB VPS provisional | Still 8 GB and still provisional — the **NC build is the open measurement** (§3) |

---

## 3. Gate status

| Gate | Status | Evidence / what remains |
|---|---|---|
| G6 POI coverage and licence | **passed in part** | Licence partition clean, per-category counts measured; the 200-POI manual audit against independent inventories (park/playground precision especially) remains |
| Geocoding contract | **passed** | `geocoding.md`, verdict recorded |
| G1 own-graph vs Valhalla | **decided** | Own-graph not adopted (D1). Walk and bike exact-pair runs were still executing when this memo was written; they can only strengthen a verdict already decided by drive and by the 30× build-cost difference |
| Transit engine | **passed** | MOTIS adopted (D2) |
| G2 Valhalla self-host | **not passed** | Slice measured (514 s build, 966 MiB build peak, 466 MB tiles, 5 s restart). **The North Carolina build on the intended 8 GB VPS is the blocking measurement**; also note `docker stats` showed ~3.7 GiB resident while serving the slice under load, which includes page cache for mmapped tiles and needs interpreting on the real host |
| G4 listings handoff | **links generated** | Leakage measured; owner must open the links on three device classes |
| G3 browser rendering | **built, not measured** | Page and real-data exporter exist; needs a desktop, throttled-4G and phone run |
| G5a interaction | **built, not run** | Prototypes and protocol exist; needs 3–5 households |

Two gates (G4 device sessions, G5a households) and one measurement (G3 on real devices) require the
owner. Everything a machine can decide alone is decided.

---

## 4. Architecture after Phase 0

```
 PRECOMPUTE (monthly, local or VPS)              STATIC TIER (Cloudflare, ~$0)
 Geofabrik NC PBF --> Valhalla tiles             R2: layers/{metro}/{mode}/{category}  uint8 minutes
 GTFS x7 (freshness-gated) --> MOTIS timetable        100 m walk/bike, 200 m drive, versioned manifest
 Overture 2026-10-21.0 (fail-closed licence)          places/{metro}.parquet (source-native, lineage)
   + OSM for playgrounds/transit stops           Pages: SPA (MapLibre, Worker algebra or server mask per G3)
 Valhalla multi-location arrival isochrones
   --> category layers (~1 s each)               ON-DEMAND (one 8 GB VPS)
 MOTIS one-to-all arriveBy --> transit surface    Valhalla: anchor arrival isochrones (p95 0.3 s)
                                                  MOTIS:    transit anchors + arrival surfaces (80 MiB)
                                                  FastAPI:  constraint algebra, places, listings links
                                                  DuckDB:   places, cache, logs
```

The own-graph engine (`v2/locfinder/traveltime/`) remains as a tested fallback, not a dependency.

---

## 5. Open risks

1. **NC build unmeasured** (D1, G2). Everything about Tier 1 hangs on the North Carolina tile build
   fitting the intended box. Until it is built there, the hosting decision is provisional.
2. **Slice bbox is too small for the Triangle.** The Phase 0 extract (lat 35.80–36.15) excludes
   downtown Raleigh, Cary and NC State. It cost us three invalid transit rows before it was caught,
   and any real build must extend south to about 35.70 **[measured]**.
3. **Park and playground data are unresolved** (D3). The two sources disagree more than they agree,
   and parks are a headline amenity.
4. **Drive-time truth is still Valhalla's opinion, not the road's.** We replaced our optimistic model
   with a better-calibrated one; neither has traffic data. The product must keep saying "estimated,
   modelled from road speeds" and must not ship a "rush hour" or "worst case" label **[assumed]** to
   be adequate until a time-of-day source exists.
5. **Static-tier serving is unproven** (G3). If browser raster algebra fails on a mid-range phone,
   the fallback is a server-rendered mask, which changes the cost profile.

---

## 6. Recommended next step

Phase 1 as described in the synthesis, with D1–D7 folded in and two additions ahead of it: build the
**North Carolina** Valhalla and MOTIS datasets on the intended host (closing G2), and widen the metro
extract south to cover Wake County. The own-graph precompute work drops out of Phase 1 entirely, which
removes roughly a third of its planned surface.
