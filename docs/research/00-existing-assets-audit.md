# 00 — Existing Assets Audit (distanceFinder V1, CHCCS_geospatial, localUpdates)

**Date:** 2026-11-03
**Status:** Complete (read-only audit; no repo code modified)
**Scope and method:** Three local repos were read for reuse in a ground-up location-finder rebuild (home-search wedge, Research Triangle NC first; tiered precompute + on-demand queries + AI-assisted query interface). Every file named in the brief was read in full except the large CHCCS modules (`school_desert.py` 2,271 lines, `school_closure_analysis.py` 3,293, `school_socioeconomic_analysis.py` 4,328, `road_pollution.py` 2,713, the three `*_story.py` generators) and localUpdates `pipeline.py`/`dedup.py`/`freshness.py`, which were outlined with `grep` and read in targeted ranges; those are marked "sampled" below. Line numbers refer to the files as they exist on disk today. No web research was done.

---

## 1. Executive summary

- **The genuinely reusable core is in CHCCS_geospatial, not in V1.** `school_desert.py` and `school_closure_analysis.py` already implement the tiered-precompute primitive the new product needs: a 100 m WGS84 point grid, STRtree edge-snapping with fractional interpolation, multi-source Dijkstra run *outward from destinations* with a documented speed model (friction speeds + intersection penalties), vectorized per-destination float32 travel-time rasters encoded for client-side `min()`, and a GeoTIFF/PNG overlay pipeline. Port this as the "gridded travel-time layer" engine.
- **V1's algorithms are small and mostly correct in intent but thin in implementation.** Progressive polygon intersection, smart criterion ordering, query-area expansion, and stable-boundary POI caching are sound ideas worth keeping (~250 lines total). The "realistic buffer" (sine-wave jitter on a circle) is cosmetic, not a travel-time model, and should be dropped in favor of real isochrones/grids.
- **V1 has a live correctness bug in the `/analyze` router:** POI-type criteria are always dispatched to the straight-line buffer with `max_distance_miles=criterion.value`, even when the frontend sends `mode=walk|bike|drive` with a value in minutes (`backend/app/routers/analysis.py:131-136`). "10-minute walk to a park" is computed as "10 miles from a park." `add_travel_time_criterion` with `poi_type` is unreachable from the API.
- **V1 has zero automated tests** (no `backend/tests/`, no frontend tests). The eight untracked `backend/test_*.py` files are manual scripts against the production URL, and five of them hard-code a TripAdvisor API key in source. CHCCS has no tests either. localUpdates has ~1,000 deterministic tests and is the only repo with an eval harness.
- **The TripAdvisor client must be dropped, not ported.** localUpdates' legal research (`docs/research-findings.md:53,178,188,200`) found the Content API forbids building a searchable database and forbids commingling with other data — exactly what a listings-linked location finder does. V1's client (`backend/app/services/tripadvisor.py`) also works around a paid-tier `nearby_search` by abusing `location/search` with a generic query string (lines 191-234).
- **localUpdates' query layer is the right template for the AI-assisted interface:** NL → Claude forced tool-use → frozen Pydantic `QueryFilter` → deterministic retrieval, with the LLM behind an injectable `Protocol` so the mapping is unit-tested offline. Port the pattern and the determinism discipline; the filter vocabulary itself (events, age bands, time-of-day) is domain-specific and must be rewritten for spatial constraints.
- **localUpdates' Overture collector, DuckDB store seam, Census→Geoapify→Nominatim geocoder chain, and `SourceObservation` provenance/license model are directly reusable** for the POI/listings layer and for keeping legally storable data (Overture, OSM, Census) separable from live-only enrichment (Google/Yelp).
- **CHCCS Census/ACS fetch + dasymetric downscaling is a reference-quality implementation** of neighborhood demographics by zone, but it is hard-wired to Orange County FIPS 37135, UTM 17N, and CHCCS attendance zones; port the fetch/downscale functions, drop the school-specific aggregation.
- **Drop outright:** V1 frontend (React 19 + react-leaflet, no tests, `Date.now()` in a `useMemo` key), the Streamlit PoC and 1.1 MB notebook, CHCCS `data_processing.py`/`property_data.py`/story generators/`slides_builder.py`, V1 TripAdvisor premium search, and the public-Valhalla dependency as a production path (keep the client as an optional on-demand fallback behind a self-hosted URL).

---

## 2. Per-repo inventory

### 2.1 distanceFinder (V1) — 21 commits, last 2026-01-07, no tests

| Component | Path | What it does | Quality / tests | Verdict | Coupling / dependencies |
|---|---|---|---|---|---|
| `LocationAnalyzer` | `backend/app/services/location_analyzer.py:34-563` | Center geocode → UTM circle → progressive intersection of buffer/isochrone criteria; in-memory POI cache keyed by OSM tags | Clear, typed; no tests; two near-duplicate POI-extraction blocks (470-563 vs router 275-312) | **Port with changes** | osmnx (Nominatim + Overpass), geopandas, shapely; imports `valhalla.get_isochrone_sync` lazily |
| Realistic buffer | `location_analyzer.py:104-156` | 36-vertex polygon with fixed sine-wave radius variation per mode | Deterministic but has no relation to the road network | **Drop** | none |
| Query-area expansion | `location_analyzer.py:158-196`, `constants.py:51` | Buffers current polygon by criterion distance (cap 5 mi) before POI query so edge POIs are caught | Correct fix for a real edge bug | **Reuse as-is** (concept) | UTM reprojection helpers |
| Stable-boundary POI cache | `location_analyzer.py:380-453` | Always queries the original search circle, caches per tag set, filters to current area | Benchmarked 4-80x in changelog 1.2.0; per-request only | **Port with changes** (persist across requests) | osmnx disk cache |
| Valhalla client | `backend/app/services/valhalla.py:23-100` | POST `/isochrone`, one contour, `generalize=50`, returns largest polygon of a MultiPolygon | Small, handles timeout/HTTP errors; silently drops disconnected isochrone parts (79-85) | **Port with changes** | httpx; `config.valhalla_url` defaults to public `valhalla1.openstreetmap.de` |
| Geocoding | `backend/app/services/geocoding.py:15-104` | `ox.geocode_to_gdf` with `lru_cache(1000)` and ", USA" suffix retries | Fine for validation; no provenance, no rate-limit handling | **Reference only** (localUpdates' chain is better) | osmnx → Nominatim |
| TripAdvisor client + premium search | `tripadvisor.py:19-423`; `routers/analysis.py:383-620` | File-cached enrichment, monthly-usage JSON, centroid search of up to 5 largest polygons, polygon containment filter | Works; `nearby_search_batch` (236-272) is dead code; legal incompatibility (see §4.5) | **Drop** | httpx, filesystem cache dir |
| Smart ordering | `routers/analysis.py:51-100` | Sort key `(type, mode, normalized_miles)` so most-restrictive criteria run first | Correct, tiny; speed constants duplicated from `constants.py` | **Reuse as-is** | none |
| `/analyze` router | `routers/analysis.py:103-185` | Dispatches criteria; builds `AnalysisResponse` | **Bug:** POI criteria ignore `mode` (131-136) | **Port with changes** | FastAPI, Pydantic schemas |
| `/pois` router | `routers/analysis.py:219-331` | Direct `ox.features_from_polygon` on user polygon, extracts name/addr/hours | Bypasses the cache; duplicates `query_pois_in_polygon` | **Drop** (replace with Overture/DuckDB lookup) | osmnx |
| Constants | `backend/app/core/constants.py:1-51` | 25 POI types → OSM tags; speeds 3/12/30 mph; detour factors 1.2/1.3/1.5 | Reasonable seed list | **Reuse as-is** (POI map) / **Drop** (speeds; CHCCS model supersedes) | none |
| Pydantic schemas | `backend/app/models/schemas.py:1-260` | `Criterion{type, poi_type, location, mode, value}`, responses | Clean; `Criterion` is the right shape to grow from | **Port with changes** | pydantic v2 |
| Performance test | `backend/performance_test.py:1-565` | Instrumented analyzer, random criteria over 5 NC cities, bottleneck JSON | Useful method; no saved results on disk | **Reference only** | osmnx, duplicates constants |
| Frontend | `frontend/src/**` (1,500 lines) | React 19, react-leaflet 5, Tailwind 4, axios, React Query; `MapUpdater` + keyed `GeoJSON` to work around react-leaflet immutability (`Map.tsx:38-75, 239-243`) | No tests; judged clunky | **Drop** (keep the `MapUpdater` trick as a note) | Vite 7, TS 5.9 |
| Streamlit PoC + notebook | `distanceFinder/app.py` (894 lines), `distanceFinder.ipynb` (1.1 MB) | Original analyzer; `_network_travel_analysis` is a stub (486-497) | Superseded | **Drop** | streamlit, folium, networkx |
| Docs | `architecture.md`, `project_spec.md`, `changelog.md`, `brainstorm.md` | Accurate for V1; brainstorm Q3-Q5 state the performance thesis | Good | **Reference only** | — |

### 2.2 CHCCS_geospatial — 109 commits, last 2026-07-02, no tests

| Component | Path | What it does | Quality / tests | Verdict | Coupling / dependencies |
|---|---|---|---|---|---|
| Speed model constants | `src/school_desert.py:105-162` | Walk 2.5 mph (K-5 children), bike 12 mph, drive friction speeds by OSM `highway` (11-59 mph), node penalties (signal 22 s, stop 11 s, yield 6 s, crossing 3 s) with HCM6/FHWA citations | Documented, sourced; calibrated for school-hour peak and child walkers | **Port with changes** (adult walk speed, off-peak drive) | none |
| Edge weighting | `school_desert.py:444-480` | `travel_time = length/speed (+ penalty at destination node)` per mode | Clean | **Reuse as-is** | networkx graph from osmnx |
| Overpass intersection supplement | `school_desert.py:483-597` | Pulls signal/stop/yield/crossing nodes for bbox, cKDTree-matches within 25 m, caches JSON | Robust to Overpass failure (falls back) | **Reuse as-is** | requests → overpass-api.de |
| Network download | `school_desert.py:600-669` | Buffered polygon (2.5 km drive / 500 m walk-bike), `graph_from_polygon`, GraphML cache, bike→`all` fallback, `_ensure_bidirectional` (312-320) | Good; bidirectionality makes one-way streets two-way (documented limitation) | **Port with changes** | osmnx, UTM 17N hard-coded |
| Node/edge spatial index | `school_desert.py:230-309` | cKDTree over nodes; STRtree over deduped edge LineStrings, lon scaled by cos(lat) | Correct, vectorized | **Reuse as-is** | shapely 2, scipy |
| Multi-source Dijkstra | `school_desert.py:672-695`; `school_closure_analysis.py:731-772` | `single_source_dijkstra_path_length` (or `dijkstra_predecessor_and_distance`, pickled) from each destination, no cutoff | 33 runs for 11 schools × 3 modes; pure networkx (Python-speed) | **Port with changes** (add cutoff, consider igraph/pandana) | networkx |
| Grid creation | `school_desert.py:698-737` | WGS84 point grid with lat-corrected spacing, prepared-polygon containment | Avoids UTM→WGS84 rotation; ~16k pts for CHCCS | **Reuse as-is** | shapely |
| Edge snapping + scoring | `school_desert.py:740-857`; vectorized in `school_closure_analysis.py:656-728, 775-823` | Nearest edge, perpendicular access distance, `line_locate_point` fraction, `min(t_u + f·e, t_v + (1-f)·e) + access`; >200 m unreachable | Closure version is NumPy-vectorized (~10x), cached as `.npz` | **Reuse as-is** (closure version) | shapely 2, numpy |
| Per-destination grids | `school_closure_analysis.py:977-1048` | float32 minutes raster per destination, base64 for client-side `min()` across a selectable set | This *is* the precompute tile format | **Port with changes** (file-based, not inline HTML) | rasterize_grid |
| Rasterize / GeoTIFF / PNG | `school_desert.py:863-1033` | Points → 2D array (min-wins), shared grid params, gap-fill, polygon mask, GeoTIFF with WGS84 transform, matplotlib colormap → base64 PNG | Correct; `gap fill` is a no-op safety net | **Reuse as-is** | rasterio, scipy.ndimage, matplotlib |
| Voronoi zones | `school_socioeconomic_analysis.py:600-649` | Nearest-label partition from labelled points, clipped to boundary | Clean helper | **Reuse as-is** | shapely `voronoi_diagram` |
| Census API client | `school_socioeconomic_analysis.py:244-301` (dup at `school_closure_analysis.py:1051-1093`) | Chunked (48 vars) ACS/Decennial GET, merges on geo columns | Solid; duplicated across modules | **Reuse as-is** (dedupe) | requests, optional `CENSUS_API_KEY` |
| ACS variable set | `school_socioeconomic_analysis.py:102-165` | Pop, age bands, race/ethnicity, income brackets, poverty ratio, tenure, vehicles, family type | Well-chosen for neighborhood profiling | **Reuse as-is** | — |
| TIGER download + dasymetric downscale | `school_socioeconomic_analysis.py:424-500, 796-961`; `school_closure_analysis.py:1197-1360` | Block groups/blocks zip download; BG counts → blocks weighted by residential parcel area → pixels | Reference-quality; parcel weights depend on Orange County tax data | **Port with changes** (parcel weights optional; fall back to block population) | geopandas, county parcel GPKG |
| Zone aggregation + map | `school_socioeconomic_analysis.py:963-1167, 1654-3664` | Intersect zones with BGs, aggregate; 2,000-line Folium/JS map | School-zone specific | **Drop** (aggregation) / **Reference only** (map) | folium |
| Road pollution (TRAP) | `src/road_pollution.py` (sampled) | Exponential-decay road exposure index with class weights (`ROAD_WEIGHTS` 73-88, `LAMBDA` 68), NCDOT AADT overrides, ESA WorldCover canopy | Interesting future "environment" criterion | **Reference only** | rasterio, planetary-computer, pystac |
| Census batch geocoder | `src/mls_geocode.py:103-230` | Census `addressbatch` POST in 1,000-row chunks, Chapel Hill→Carrboro retry, Nominatim fallback (232-266) | Works; hand-rolled CSV parse; city hard-coded | **Reference only** (localUpdates has the cleaner single-address chain) | requests |
| Childcare geocode | `src/childcare_geocode.py` | geopy Nominatim + `RateLimiter`, haversine distance bands | Generic but CSV-driven | **Drop** | geopy |
| Parcel processing | `src/property_data.py:1-164` | Orange County parcel shapefile + FOIA Excel merge → residential centroids | Entirely local | **Drop** (pattern only) | openpyxl |
| `data_processing.py`, `maps.py` | `src/` | Non-geospatial loaders; folium maps | Flagged as TODO in their own CLAUDE.md | **Drop** | — |
| Scrollytelling + slides | `closure_story.py`, `socioeconomic_story.py`, `environmental_story.py`, `slides_builder.py` | Self-contained HTML methodology pages; Playwright + python-pptx deck | ~1,000-line inline HTML per file | **Reference only** (grid→PNG→Leaflet overlay recipe) | playwright, python-pptx |
| Guidelines doc | `docs/GEOSPATIAL_ANALYSIS_GUIDELINES.md` | CRS discipline (WGS84 store / UTM compute), WGS84-native grids, make_valid, clip rules | Directly adoptable conventions | **Reuse as-is** | — |

### 2.3 localUpdates — 135 commits, last 2026-11-03, ~1,000 tests (README: 988; CLAUDE.md: 1,034 passed / 5 skipped post-merge)

| Component | Path | What it does | Quality / tests | Verdict | Coupling / dependencies |
|---|---|---|---|---|---|
| NL → filter | `src/localupdates/query/interpret.py:95-108, 184-270, 281-414` | `FilterExtractor` Protocol; Claude forced tool-use `build_filter` (strict schema); deterministic `_map_to_filter` with enum/number/bool clamping; injected `now`/tz | 37 tests; live path smoke-tested only | **Port with changes** (new tool schema) | anthropic SDK (lazy), `QueryFilter` |
| Client plumbing | `query/llm.py:23-42` | Lazy `anthropic.Anthropic()`; model from `SETTINGS.claude_model` | 3 tests | **Reuse as-is** | anthropic |
| Retrieval | `query/retrieve.py:106-195, 643-793` | Frozen `QueryFilter`; UTC-window SQL then local-day refine in Python; quality-first ranking `_sort_key` (612); uncertainty aggregation (525) | 62 tests; occurrence-driven (standalone Places unreachable — their CLAUDE.md gap #1) | **Reference only** (pattern) | `Store`, `dedup.haversine_miles` |
| Heuristics | `query/heuristics.py:49-163` | Price parse, indoor/outdoor keyword inference, category blob | Domain-specific | **Drop** | — |
| Answer composition | `query/answer.py` (outlined, 1,036 lines) | Facts-only citation documents, caveat computation, Anthropic Citations API | 60 tests | **Reference only** | anthropic |
| Live enrichment | `query/enrich.py` (outlined, 406 lines) | Google Places (New) at query time, never stored, `place_id` only persisted | 42 tests; legally reasoned | **Port with changes** | requests (lazy), `GOOGLE_MAPS_API_KEY` |
| Store seam | `store/base.py:25-207` | ABC: generic `upsert/get/delete`, `find_places_near`, occurrence windows, `transaction` | 15+34+10 tests | **Reuse as-is** (extend for grids) | — |
| DuckDB store | `store/duckdb_store.py:87-514`, `store/schema.sql:1-105` | `spatial` required/`vss` optional, explicit haversine SQL (54-60; avoids broken `ST_Distance_Sphere`), hybrid key-columns + `doc JSON` | Solid; extension `INSTALL` hits network first run | **Reuse as-is** | duckdb, pytz |
| Projection | `store/repository.py:41-196` | Model→(table, columns) single source of truth; anti-drift | Tested | **Reuse as-is** | pydantic models |
| Models | `models.py:131-421` | `GeoPoint`, `Place`, `Event`, `Occurrence`, `SourceObservation` with license/attribution/allowed_use/`raw_storage_allowed` (390-395), `ProvenanceMixin` | 53 tests | **Port with changes** (add `Listing`, `TravelTimeLayer`) | pydantic v2 |
| Overture collector | `collect/overture.py:175-525` | Tolerant GeoJSON read, per-row license resolution (Foursquare→Apache-2.0 else CDLA), confidence ≥0.85, bbox filter, deterministic dedupe | 35 tests | **Reuse as-is** | `config.County` bboxes |
| Geocoder chain | `geocode.py:282-330, 348-765` | Address cleaning; Census → Geoapify (keyed) → Nominatim (1 req/s throttle, UA) fallback; `GeocodeHit` carries attribution; typed `GeocoderError` vs cacheable no-match | 93 tests, `httpx.MockTransport` | **Reuse as-is** | httpx |
| Dedup | `dedup.py` (outlined) | Name/address/phone/domain/geo matching, coherent clustering, canonical merge, conflict detection | 61 tests; known false-merge on sibling campuses | **Port with changes** | — |
| Freshness | `freshness.py` (outlined) | Source trust rank, expected expiry, confidence, `possibly_closed` | 49 tests | **Reference only** | — |
| Pipeline | `pipeline.py` (outlined, 1,133 lines) | Build-then-persist orchestration | 37 tests; their critique calls it a procedural monolith | **Reference only** | everything above |
| Eval harness | `eval/harness.py:95-547`, `eval/golden_queries.py`, `eval/fixtures.py`, `eval/run_golden_queries.py` | Seeds real pipeline into real store, runs real query chain, 8-criterion bar, scripted LLM stand-ins for determinism, live runner degrades without key | 18 tests | **Port with changes** (new golden queries) | all of the above |
| Legal research | `docs/legal-and-data-use.md`, `docs/research-findings.md` | 18-source commercialization matrix with ToS citations | Verified 2026-06-28/30 | **Reuse as-is** | — |

---

## 3. Reusable algorithms

### 3.1 Progressive polygon filtering + smart ordering (V1)
**What:** Start from a UTM circle of `radius_miles`; for each criterion compute a polygon (buffer union or isochrone), intersect with the running area; apply criteria in order of estimated restrictiveness.
**Inputs/outputs:** `AnalysisRequest{center, radius_miles, criteria[]}` → final shapely polygon + per-criterion areas.
**Where:** `location_analyzer.py:37-87` (init), `:198-253` (buffer criterion), `:255-378` (travel-time criterion), `:158-196` (expansion); `routers/analysis.py:51-100` (ordering), `:127-150` (dispatch).
**Limitations:** Per-request only; every criterion is AND (no OR, no weighting, no soft scoring/heat map); router bug on POI+mode (131-136); results are a polygon, never a per-cell score, so there is no way to say "better" vs "acceptable".

### 3.2 "Realistic" travel-time buffers (V1)
**What:** Distance = minutes/60 × speed ÷ detour factor; polygon = circle with fixed sine-wave radius modulation (`:104-156`), used for all POI-type travel-time criteria and as Valhalla fallback.
**Limitations:** Shape is independent of roads; the 1.2/1.3/1.5 detour factors are guesses; drive at 30 mph flat. Keep only the minutes→miles bound as a pre-mask (CHCCS speeds are better), drop the shape.

### 3.3 Valhalla isochrone client (V1)
**What:** One POST per (point, mode, minutes); returns the largest polygon. `valhalla.py:23-100`; costing map `:16-20`.
**Limitations:** Single contour per call; MultiPolygon reduced to largest part (loses islands reachable via disconnected roads); 30 s timeout; public server default (`config.py:36`); no retry/backoff; no caching of isochrones. Fine as the on-demand path for *arbitrary* user places if pointed at a self-hosted instance and cached by `(rounded lat/lon, mode, minutes)`.

### 3.4 OSM POI querying and its performance problem (V1)
**What:** `ox.features_from_polygon(search_boundary, tags)` once per tag set, cached in memory, filtered with `intersects` (`location_analyzer.py:417-451`); expansion buffer first (`:158-196`).
**Measured:** project_status and changelog 1.2.0 report OSM queries at 95%+ of request time and 6 criteria in 3.86 s after caching (was ~18 s). The 25-mile cap exists because Overpass times out on large polygons.
**Limitations:** Overpass is a shared public service; results are not persisted across requests or processes; POI name/address extraction is duplicated; building footprints come back as polygons and are centroid-ed ad hoc. Replace with a precomputed Overture/OSM places table in DuckDB (localUpdates' store) and keep Overpass only as a gap filler.

### 3.5 TripAdvisor client (V1) — flagged
**What:** `tripadvisor.py:19-392`; premium search `routers/analysis.py:447-620` (centroids of ≤5 largest polygons → `location/search` → details → containment filter → photos).
**Legal flag:** localUpdates' research sweep classified TripAdvisor Content API as **"forbids searchable DB AND commingling — reject (incompatible by design)"** (`docs/research-findings.md:53`; reiterated at `:178,188,200`). The new product stores a POI/listings database and shows TripAdvisor data next to OSM/Overture/MLS data; both prohibited. V1 also caches responses to disk for 7 days (`:107-139`). **Do not port.** The centroid-sampling idea is only needed because of a provider that cannot be stored; with a storable POI layer it is unnecessary.

### 3.6 Gridded multi-source Dijkstra travel-time method and speed model (CHCCS)
**What:** (1) download buffered OSM graph per mode, make bidirectional, weight edges `length/speed + node_penalty` (`school_desert.py:444-480, 600-669`); (2) Dijkstra from each destination over the whole graph (`:672-695`, with predecessors `school_closure_analysis.py:731-772`); (3) build a WGS84 grid (`:698-737`); (4) snap every grid point to the nearest edge with STRtree, get fraction `f` and perpendicular access distance (`school_closure_analysis.py:656-728`); (5) time to destination = `min(t_u + f·e, t_v + (1-f)·e) + access_dist/(factor·speed)`, unreachable if >200 m from any edge; vectorized over all points and destinations (`:775-823`).
**Inputs/outputs:** destination points (lat/lon), boundary polygon, mode → per-destination `{node: seconds}` dicts, per-point minutes arrays, nearest-destination labels.
**Speed model:** `school_desert.py:105-162` — walk 1.12 m/s, bike 5.36 m/s, drive friction speeds by highway class with 20 mph default, penalties applied at the arriving node; Overpass supplements stop/signal tags lost to OSMnx simplification (`:483-597`).
**Limitations:** Calibrated for K-5 walkers and school-hour drive peaks (adult walk ≈ 1.4 m/s; off-peak drive faster); bidirectional graph ignores one-way streets; no turn penalties, elevation, transit, or time-of-day; networkx Dijkstra is pure Python (acceptable for a district, needs cutoff or igraph/pandana for a metro); UTM 17N and Orange County hard-coded in several constants; the "33 Dijkstra runs" design is destination-outward, which is exactly right for *precomputed layers for known destinations* (schools, grocery stores, parks, RDU) but not for an arbitrary user address (use Valhalla or a reverse Dijkstra on demand).

### 3.7 Rasterization / overlay pipeline (CHCCS)
**What:** points → 2D float32 raster via `np.minimum.at` with shared `grid_params` so every layer aligns (`school_desert.py:863-977`); GeoTIFF with WGS84 affine (`:980-999`); colormap → base64 PNG with NaN transparent (`:1002-1025`); raw float32 base64 for client hover (`:1028-1033`); per-destination grids for client-side `min()` across a toggled set (`school_closure_analysis.py:977-1048`). Guidelines in `docs/GEOSPATIAL_ANALYSIS_GUIDELINES.md` §5.
**Limitations:** Everything is inlined into one HTML file (hundreds of KB of base64); no tiling, no COG, no zoom levels. For the product, write GeoTIFF/COG or Zarr per (destination-class, mode) and serve as tiles or fetch as typed arrays; the math transfers unchanged.

### 3.8 Census/ACS by zone with dasymetric downscaling (CHCCS)
**What:** `_census_get` chunked client (`school_socioeconomic_analysis.py:244-301`); ACS 5-year block-group variables (`:102-165`) joined to TIGER BG geometry (`:308-351`, `:424-462`); Decennial block race (`:353-422`); BG counts distributed to blocks proportional to residential parcel area (`:796-961`); blocks to pixels by area intersection (`school_closure_analysis.py:1197-1360`).
**Limitations:** FIPS 37135 and ACS 2024 hard-coded; parcel weights require a county parcel GPKG; conservation checks exist but no tests. For the home-search wedge, neighborhood demographics are a "context layer," not a constraint; port the fetch + downscale, parameterize county list, and fall back to area weighting when parcels are absent.

### 3.9 NL → structured filter → SQL (localUpdates)
**What:** `interpret_query(text, now, origin, extractor)` (`interpret.py:239-270`) → `extractor.extract(...)` (Claude strict tool `BUILD_FILTER_TOOL`, `:281-337`, system prompt `:340-367`) → `_map_to_filter` clamps every field (`:184-231`) → frozen `QueryFilter` (`retrieve.py:106-156`) → `retrieve()` runs parameterized SQL through `Store` then refines/ranks in Python (`:643-793`). `llm.py:23-42` keeps the SDK import lazy so tests need no key.
**Transferable:** Protocol seam, injected `now`, strict tool schema with "omit what you can't infer," clamp-never-raise mapping, scripted extractor for the eval harness.
**Not transferable:** The filter fields (date, time band, age, price, indoor/outdoor) and `_minutes_to_miles` straight-line conversion (`:74-87`, 30 mph × 0.8) — the new product should emit a list of spatial `Constraint{anchor, mode, minutes|miles, hard|soft}` and resolve travel time with grids/isochrones, not haversine.

### 3.10 Overture collector, DuckDB store, geocoding, eval harness (localUpdates)
- **Overture** (`collect/overture.py:175-525`): storable, commercially usable POI backbone; `load_overture_places(path, counties, min_confidence=0.85)` → `(Place, SourceObservation)` pairs with per-row license. Needs an actual Overture pull step (the repo reads a pre-downloaded GeoJSON; the TODO at `:461-464` notes bbox-not-polygon filtering).
- **Store** (`store/base.py`, `duckdb_store.py`, `schema.sql`): `find_places_near(lat, lon, radius_miles)` via explicit haversine (`duckdb_store.py:54-60, 330-345`); hybrid key-columns + `doc JSON`; `vss` optional. Extend `schema.sql` with `listings` and `travel_time_layers` tables; keep the dialect boundary.
- **Geocoding** (`geocode.py:348-765`): Census → Geoapify → Nominatim chain with attribution carried on each hit, 1 req/s Nominatim throttle (`:617-632`), address cleaner (`:282-330`). Replaces V1's `geocoding.py` outright.
- **Eval harness** (`eval/harness.py:95-547`): seeds the real pipeline, runs the real chain, scores an 8-criterion bar, swaps scripted vs live LLM. Port the structure; write golden queries for spatial constraints ("20 min drive of A and 25 of B, 10 min walk to a park" → expected cells/listings).

---

## 4. Gaps — capabilities none of the three repos provide

1. **Multi-anchor soft scoring / heat map.** V1 is hard AND-intersection; CHCCS computes min-time to *one class* of destination; nothing combines several anchors into a per-cell score, weights, or "mostly satisfies."
2. **On-demand reverse travel time from an arbitrary user point to many cells.** CHCCS is destination-outward for fixed destinations; V1 defers to public Valhalla. No self-hosted router, no isochrone cache, no graph persisted for metro-scale queries.
3. **Listings.** No MLS/listing ingestion beyond CHCCS's one-off Chapel Hill CSV geocode (`mls_geocode.py`); no hotel/short-stay source; no listing↔cell join.
4. **Metro-scale network handling.** All CHCCS runs are one school district (~16k grid points); no tiling, chunked Dijkstra, igraph/pandana, or contraction hierarchies.
5. **Precompute storage/serving.** No tile store, COG/Zarr, versioning, or invalidation; CHCCS inlines base64 into HTML; V1 has no persistence at all.
6. **Transit mode.** Absent everywhere (OSM `highway=bus_stop` as a POI type is the only mention).
7. **Multi-metro configuration.** Every repo hard-codes a geography (Durham default, Orange/Durham bboxes, FIPS 37135, UTM 17N).
8. **Hosting-grade concerns:** auth, rate limiting, job queue for long precomputes, CI (none of the three has CI; localUpdates' critique R8 says so explicitly).
9. **UI for the target user.** V1's form-based UI is the thing being replaced; CHCCS maps are analyst artifacts; localUpdates is CLI-only.
10. **Google attribution compliance for a visual UI.** localUpdates notes its text-only placeholder does not satisfy "Powered by Google" branding for any non-CLI surface (`docs/legal-and-data-use.md`, row 9 detail).

---

## 5. Technical debt and risks in reuse

| Piece | Risk | Evidence |
|---|---|---|
| V1 Valhalla | Production dependence on a volunteer public server; 30 s timeout; silent fallback to a fake buffer means users cannot tell real from approximate | `config.py:36-38`, `location_analyzer.py:310-333` |
| V1 OSMnx/Overpass | Timeouts drove the 25-mile cap and the "Specific Place" default; cache is per-process; `ox.settings` mutated at import in `main.py:21-24` | `project_status.md` "95%+", `SearchForm.tsx:27-78` time-estimate heuristics |
| V1 router | POI criteria ignore `mode` (minutes read as miles); `query_pois_in_polygon` and `nearby_search_batch` are dead code | `routers/analysis.py:131-136`; grep shows no callers |
| V1 secrets | Five untracked scripts contain a literal TripAdvisor API key | `backend/test_search_endpoint.py:5`, `test_search_simple.py:5`, `test_tripadvisor_direct.py:7`, `test_tripadvisor_endpoints.py:5`, `test_with_headers.py:4` — rotate the key; never copy these files |
| V1 Windows | Stray zero-byte `nul` file at repo root (a Windows redirect artifact); `.claude/settings.local.json` has uncommitted changes | `ls -la nul` |
| V1 tests | None automated; manual scripts hit production | no `backend/tests/`, no `*.test.*` in frontend |
| CHCCS size/coupling | Analysis and 1,000+ line inline HTML/JS live in the same modules (`_build_control_html` `school_desert.py:1192-1939`, `school_closure_analysis.py:1850-2981`); constants duplicated across files (their own CLAUDE.md TODO) | outlines above |
| CHCCS geography | UTM 17N, Orange County FIPS, CHCCS shapefile paths, `CHAPEL_HILL_CENTER` hard-coded; `build_zone_polygons` imports from the socioeconomic module | `school_desert.py:168-172`, `school_closure_analysis.py:833` |
| CHCCS performance | Pure-Python networkx Dijkstra with no cutoff; Overpass dependency for intersection tags; pickled predecessor maps | `:672-695`, `:483-597`, `school_closure_analysis.py:731-772` |
| CHCCS Windows | `plt.rcParams` prefer "Segoe UI"; Playwright for slides; otherwise pathlib-clean | `school_socioeconomic_analysis.py:171`, `road_pollution.py:143` |
| CHCCS tests | None; correctness rests on documented conservation checks and manual audits | `docs/IMPLEMENTATION_NOTES.md` bug write-ups |
| localUpdates runtime | Python ≥3.13 + `uv`; DuckDB extension `INSTALL` needs network on first run; `pytz`/`tzdata` pinned for Windows TIMESTAMPTZ | `pyproject.toml`, `duckdb_store.py:93-151` |
| localUpdates design | Retrieval is occurrence-driven so standalone Places are unreachable (their gap #1); dedup can false-merge sibling campuses; `pipeline.py` monolith; no CI | `CLAUDE.md` "Known open gaps", `docs/2026-08-10-workflow-critique.md` |
| localUpdates model | `claude_model = "claude-opus-4-8"` hard-coded in `config.py:84` | — |
| Legal (all) | OSM/Overpass data is ODbL share-alike: keep OSM-derived tables separable from proprietary listings; Google/Yelp live-only; TripAdvisor incompatible; Census disclaimer string mandatory wherever Census-geocoded points appear | `docs/legal-and-data-use.md` rows 9, 10, 15, 16 |

---

## 6. Recommended reuse plan (ordered)

1. **Copy** localUpdates `models.py`, `store/{base.py, duckdb_store.py, repository.py, schema.sql}`, `geocode.py`, `collect/overture.py`, `collect/_common.py`, `config.py` and their tests into `v2/core/`. Rename package; keep the `Store` seam; add `listings` and `grid_layers` tables to `schema.sql`. This gives a tested, legally reasoned POI + geocoding + provenance base on day one.
2. **Port** CHCCS travel-time engine into `v2/traveltime/`: `school_desert.py:105-162, 230-320, 444-669` and `school_closure_analysis.py:228-240, 656-823, 857-1048` as pure functions parameterized by `(boundary_polygon, destinations, mode, speed_profile, utm_crs)`. Replace hard-coded CRS with `gpd.estimate_utm_crs()`; add a Dijkstra cutoff (e.g. 60 min); write GeoTIFF/COG per layer instead of base64 in HTML; add unit tests on a tiny synthetic graph (the repo has none).
3. **Port** V1's progressive-filter ideas into `v2/compose/`: smart ordering (`routers/analysis.py:51-100`), query-area expansion (`location_analyzer.py:158-196`), and polygon intersection — but operate on grid rasters (per-cell min/AND/weighted score) rather than shapely polygons, with polygonization as an output step. Fix the POI-mode dispatch bug by construction (one `Constraint` type with explicit units).
4. **Wrap** V1's Valhalla client (`valhalla.py:23-100`) as the on-demand path for arbitrary anchors: self-hosted URL, request all needed contours in one call, keep MultiPolygons, cache by rounded point/mode/minutes in DuckDB.
5. **Port** localUpdates `query/interpret.py` + `llm.py` as `v2/nl/`: new `build_constraints` tool schema emitting `[Constraint]` + a region hint; keep `FilterExtractor` seam and clamp-never-raise mapping; delete the events vocabulary and `_minutes_to_miles`.
6. **Port** localUpdates `eval/harness.py` + `golden_queries.py` structure with 5–10 spatial golden queries over a synthetic Triangle fixture (small graph + a dozen POIs + a few listings), scripted extractor for determinism, live runner gated on `ANTHROPIC_API_KEY`.
7. **Port** CHCCS Census client + ACS variable set + dasymetric downscale (`school_socioeconomic_analysis.py:102-165, 244-301, 308-500, 796-961`) into `v2/context/census.py`, parameterized by FIPS list; use as an optional "neighborhood context" layer, not a filter, in the first release.
8. **Adopt** `CHCCS docs/GEOSPATIAL_ANALYSIS_GUIDELINES.md` §1–§5 and localUpdates `docs/legal-and-data-use.md` as `v2/docs/` conventions verbatim (with attribution to their source repos).
9. **Keep as reference only:** V1 `Map.tsx` `MapUpdater` workaround, CHCCS `road_pollution.py` exposure index (future "quiet street" criterion), localUpdates `answer.py` facts-only citation rendering, `performance_test.py` methodology.
10. **Do not copy:** TripAdvisor code, untracked `backend/test_*.py`, Streamlit PoC/notebook, V1 frontend, CHCCS story/slides generators, `data_processing.py`, `property_data.py`.

---

## 7. Open questions for the architect

1. **Grid resolution and extent for the Triangle tier-1 precompute.** CHCCS used 100 m over ~70 km² (~16k points). Wake + Durham + Orange is roughly 60× that; at 100 m that is ~1M cells × (destination classes × 3 modes) float32 layers. Is 250 m acceptable for drive, 100 m for walk/bike, or should layers be tiled by zoom?
2. **Destination-outward vs. cell-outward.** Destination-outward (CHCCS) is cheap for *classes* (all grocery stores → one layer via min). For "partner A's office" the anchor is arbitrary. Is the plan one on-demand isochrone per arbitrary anchor (Valhalla, self-hosted) rasterized onto the shared grid, or a cell-outward precompute (e.g. OSRM/Valhalla matrix) that makes arbitrary anchors a lookup?
3. **Routing engine.** Keep networkx + CHCCS speed model (transparent, tunable, slow) or move to Valhalla/OSRM/pandana for both precompute and on-demand, using the CHCCS constants only as a documented calibration reference?
4. **Speed profiles.** CHCCS is K-5 walk + school-hour drive. Which profiles does the product expose (adult walk, commute-peak drive, off-peak drive)? Does "20-minute drive to the office" mean peak?
5. **Hard vs. soft constraints.** V1 is all-hard. Should the output be a boolean region, a scored heat map, or both (score with a threshold)? This determines whether `v2/compose/` is raster algebra or polygon intersection.
6. **Store.** Stay on DuckDB (embedded, GeoParquet-native, already behind a `Store` seam) for tier-1 metros, or go to Postgres/PostGIS now that hosting is intended? localUpdates designed the seam for exactly this swap.
7. **Listings source and legality.** MLS access for the Triangle (CHCCS used a one-off CSV); hotel/short-stay sources for the later wedge; which of these may be stored vs. live-fetched?
8. **OSM share-alike posture.** If the POI table is Overture (CDLA) + OSM (ODbL) + proprietary listings, do we keep OSM-derived rows in a separate database/file to avoid ODbL contagion, as localUpdates recommends?
9. **Google/Yelp enrichment in a visual UI.** localUpdates' `enrich.py` is CLI-grade; a web UI triggers logo/branding obligations. Is live enrichment in scope for v2.0 at all?
10. **Python version baseline.** localUpdates requires 3.13 (uv); V1 ran on 3.13 but CHCCS is "3.10+" with heavy geo deps (rasterio, osmnx, pystac). Standardize on 3.12 or 3.13 and verify the geo stack installs on Windows before porting.
