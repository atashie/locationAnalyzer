# Codex Adversarial Review — Research Streams 00–05 (Pass 1)

**Date:** 2026-11-03  
**Reviewer model:** GPT-5 (Codex runtime identifier)  
**Method:** Read all six requested documents, `00-existing-assets-audit.md` through `05-routing-and-precompute-architecture.md`, end to end from local files; no network calls were made. Recomputed the grid/storage/request arithmetic and cross-compared recommendations and open questions. Spot-checks covered `backend/app/routers/analysis.py`, `services/valhalla.py`, `core/config.py`, `frontend/src/components/Map/Map.tsx`, CHCCS `school_desert.py`/`school_closure_analysis.py`, and localUpdates `collect/overture.py`, `query/interpret.py`, and DuckDB extension loading. The V1 POI-mode dispatch bug, largest-MultiPolygon behavior, public-Valhalla default, absence of tests, CHCCS's forced bidirectionality and NetworkX Dijkstra, and localUpdates' structured tool seam were confirmed in code. External claims are challenged from model knowledge and reasoning only; they are explicitly marked for verification rather than presented as newly web-verified facts.

## Verdict

- The research is broad and useful, but **not yet sound enough to freeze the architecture**. It is sufficient to define experiments, not a build plan.
- The weakest link is routing correctness: the proposed destination-outward computation is not defined on the reversed directed graph, while the reusable CHCCS implementation avoids the issue by making every road bidirectional. That is unacceptable for drive-time regions.
- The must-have listings story rests on undocumented, scraper-derived Zillow/Redfin URL formats and an incompletely read RentCast licence. Treat linkage as an experiment until real mobile/desktop links and permitted uses are verified.
- The legal posture is mostly conservative, but the Google Places caching rule appears over-permissive and the OSM “separable layer” conclusion is too categorical for entity-linked/deduplicated data.
- The $10 VPS, sub-second Dijkstra, browser-grid latency, and $10–25/month-at-10k-users claims form one optimistic chain. None has been benchmarked at Triangle scale; bursts, memory representation, tile overviews, cache misses, and operations are omitted.
- The streams conflict on H3 versus square rasters, DuckDB versus PostGIS, transit “from the start” versus defer, and own Dijkstra versus Valhalla for drive layers. These are architectural choices, not harmless wording differences.
- The interaction recommendation is plausible but overstates the evidence: vendor case studies and engagement metrics do not establish that editable chips plus a live grid beats a simpler two-address map for this product.
- Plan the next phase around four cheap spikes: directed routing correctness/accuracy, real listing handoffs, browser raster performance on mobile, and an actual NC Valhalla build with representative load.

## Findings

| id | severity | document and section | claim or issue | why it matters | recommended action (verify / revise / add / drop) | Codex confidence |
|---|---|---|---|---|---|---|
| C1 | Critical | `00-existing-assets-audit.md` §3.6 “Gridded multi-source Dijkstra”; `05-routing-and-precompute-architecture.md` §3.1/§3.4 | “Destination-outward” is called exactly right, but neither stream requires reversing a directed graph. The checked CHCCS code instead adds reverse edges to every road and runs outward. | On a legal one-way graph, distances from destination on the original graph answer the wrong direction; forced bidirectionality yields false drive regions. | **Revise** the algorithm contract to run from destinations on the transposed graph (or origins on the original); **verify** against Valhalla `reverse` isochrones. | High (code-observed + graph theory) |
| C2 | Critical | `04-data-sources-and-legal.md` Executive summary #10 and §3.10 “Google Places (New) — caching and pricing” | “Everything else ≤30 days” likely overstates permitted caching. My training-based understanding is that the 30-day exception is specifically for lat/lng; most other Google Maps Content is generally non-cacheable unless a service term says otherwise, while place IDs are exempt. | Persisting names, ratings, hours, photos, or other content for 30 days could create a direct ToS breach in a later public product. | **Verify** the current Service Specific Terms field by field; **revise** to “store only place ID unless an explicit exception is documented.” | Medium-high (training knowledge; terms must be re-read) |
| C3 | Critical | `04-data-sources-and-legal.md` Executive summary #1/#4, §3.1/§3.2/§3.5, and §4 “Listings linkage” | The must-have listings plan relies on undocumented Zillow `searchQueryState`, a Redfin viewport pattern sourced from scraper documentation, and RentCast rights inferred without reading the full permitted-use list. | A UI can ship with links that silently discard filters or break on mobile, while prototype pins may exceed the licence grant. This would invalidate the wedge's must-have integration after architecture work is committed. | **Verify** links manually across web/app and read the full RentCast licence/provenance; **add** a URL-contract test and a non-RentCast fallback. | High (document-observed uncertainty) |
| H1 | High | `05-routing-and-precompute-architecture.md` Executive summary, §2.2 “Self-hosting options,” §8 “Hybrid,” §9 spikes | A 4–8 GB VPS is assumed to hold Valhalla, FastAPI, DuckDB, and a metro graph, but the in-memory graph representation is unspecified. A NetworkX/GeoPandas graph can consume orders of magnitude more memory than CSR arrays. | The recommended single-box topology can OOM or force a second service/box, changing both cost and operations. | **Verify** RSS with the exact container and CSR graph; **revise** the base plan to 8 GB until measured. | High (engineering inference) |
| H2 | High | `05-routing-and-precompute-architecture.md` §3.2 “Compute,” §4 latency table, §5.2 cost table | The 0.2–1 s SciPy runs, 100–600 ms anchor grids, and $10–25/month at 10k users are estimates stacked as conclusions. Average load (`0.04 req/s`) hides bursts; a full 948k-byte uint8 grid per anchor is already ~0.95 MB before protocol/metadata. | Latency and bandwidth can dominate the UX and cost even if average CPU is low. | **Verify** with concurrent cold/warm benchmarks and compressed, viewport-clipped payloads; **revise** the cost table to ranges with p95 concurrency. | High |
| H3 | High | `04-data-sources-and-legal.md` §3.8 “OSM / ODbL — mixing OSM with other data” and Legal posture #4 | “Link by our own entity ID” is treated as safely separable, yet entity resolution, deduplication, or using one source to correct another may create cross-references or a derivative database under the cited guideline. | The proposed unified POI experience can trigger share-alike obligations that the product assumes are avoided. | **Verify** the precise schema/ETL with ODbL counsel; **revise** “safe” to a conditional design rule and retain source-native records. | Medium-high (legal interpretation, not legal advice) |
| H4 | High | `00-existing-assets-audit.md` §3.10; `04-data-sources-and-legal.md` §3.9; checked `localUpdates/collect/overture.py` | The reusable collector defaults any non-Foursquare row lacking an explicit licence to CDLA-Permissive-2.0. That is a fail-open licensing decision, while the research calls the resulting base “commercial-safe.” | A schema/source change or unknown contributor could be silently assigned a permissive licence. | **Revise** ingestion to fail closed/quarantine missing or unknown licences; **verify** against the actual release manifest and NOTICE requirements. | High (code-observed) |
| H5 | High | `01-consumer-landscape-home-search.md` §5 Implications #2; `03-open-source-landscape.md` §5; `05-routing-and-precompute-architecture.md` §3.2 and Open question #6 | Doc 01 prescribes H3; docs 03/05 prescribe COG/square rasters and leave H3 open. H3 resolution 10 averages ~0.015 km² versus a 100 m square's 0.010 km²—about 50% larger, not a drop-in equivalent. | The canonical grid controls preprocessing, joins, rendering, resampling error, and URL/cache keys. | **Revise** all recommendations to leave the choice open; **verify** with one H3 and one raster prototype. | High (arithmetic) |
| H6 | High | `02-landscape-hotel-and-site-selection.md` “Implications for our build” #1; `05-routing-and-precompute-architecture.md` §3.3 | Doc 02 says transit surfaces must be supported “from the start”; doc 05 says transit can be deferred because Triangle mode share is unverified and on-demand transit needs another runtime. | This can add an R5/OTP/MOTIS workstream before the home-search wedge is validated. | **Revise** to a product decision: transit is phase 1 only if target-household interviews require it; otherwise **drop** from initial architecture. | High |
| H7 | High | `01-consumer-landscape-home-search.md` Executive summary #4/#5 and §5 #1; `02-landscape-hotel-and-site-selection.md` Implications #6 | The claim that successful products expose editable filters conflicts with doc 02's “Every AI competitor hides the resolved filters,” and vendor engagement metrics do not isolate the interaction model. | The team may build NL parsing and chip editing before proving the core map solves the problem. | **Revise** the recommendation to a hypothesis; **verify** with a clickable two-address map versus NL+chips test. | High |
| H8 | High | `04-data-sources-and-legal.md` §3.4 “MLS / IDX”; Legal posture #2 | Policy 7.58 is treated as a sufficient rule set, but the cited PDF is an older national policy and local Doorify rules/vendor agreements are explicitly unverified. The $35+$5 feed fees are not the cost of brokerage participation, compliance, vendor approval, or display operation. | The “only legal path” may be structurally or financially unavailable to this product. | **Verify** current NAR policy plus Doorify's current local rules and obtain a written broker/vendor path before planning IDX. | High (document-observed gap) |
| H9 | High | `05-routing-and-precompute-architecture.md` Executive summary “MapLibre cannot yet threshold arbitrary rasters,” §5.1 and Spike 9 | The limitation may be version-specific or outdated; MapLibre raster colorization capabilities have evolved. Encoding minutes as Terrarium elevation is also a semantic hack with nodata/alpha/quantization risk. | A false limitation can drive unnecessary Worker/canvas complexity; the hack can produce misleading thresholds. | **Verify** against the exact MapLibre version/style spec; **drop** Terrarium unless a tiny spike proves correctness. | Medium (training knowledge; version-sensitive) |
| H10 | High | `05-routing-and-precompute-architecture.md` §3.2 “Compute” and §6 custom categories | SciPy's compiled Dijkstra speed is extrapolated without including CSR construction, directed reversal, source count, cutoff behavior, grid-edge interpolation, serialization, and concurrency. “One run per category” is correct only if all category destinations are seeded together with the correct direction. | The custom-category API and monthly build budget depend on this being seconds, not tens of seconds or memory-bound. | **Verify** one end-to-end category on the actual graph; **revise** estimates to measured component timings. | High |
| M1 | Medium | `03-open-source-landscape.md` §3.1/§4(i); `05-routing-and-precompute-architecture.md` §2.2 | NC Valhalla runtime/build sizing is inferred from unrelated regions/PBF ratios; PBF size does not scale linearly with graph density, tile build peak, elevation, or GTFS. | The chosen host may be undersized and builds may fail. | **Verify** Spike 3 before choosing a provider. | High |
| M2 | Medium | `05-routing-and-precompute-architecture.md` §3.2 storage and §5.1 | The 15–30 MB compressed total excludes COG overviews/tile pyramids, per-tile headers/indexes, multiple formats, manifests, old versions, and poor compression around noisy boundaries. Raw arithmetic (71 MB) is correct; the delivery estimate is not established. | First paint and R2 request counts depend on delivered artifacts, not raw arrays. | **Revise** as a lower-bound estimate; **verify** ten real layers in both formats. | High |
| M3 | Medium | `05-routing-and-precompute-architecture.md` §5.2 | 10k users × 5 queries × 30 reads = 1.5M reads is internally consistent, but it ignores retries, pans/zooms, cache misses, layer toggles, and bot traffic. HA, backups, logs, monitoring, and rebuild compute are absent. | “$10–25” is a best case, not a budget tier. | **Revise** with 3×/10× traffic and two-node/managed fallback scenarios. | High |
| M4 | Medium | `02-landscape-hotel-and-site-selection.md` Executive summary #3 and Open question #3; `04-data-sources-and-legal.md` Executive summary #7 | The Amadeus Self-Service shutdown is explicitly unverified and rests on secondary reporting plus a repository archive. | It narrows the hotel API landscape and supports a deep-link-only conclusion. | **Verify** with an official notice or current developer access attempt before treating it as fact. | High (uncertainty observed) |
| M5 | Medium | `05-routing-and-precompute-architecture.md` Executive summary and VPS table | The Oracle Always Free reduction is a temporally sensitive claim from a secondary article and should not support architecture anyway. | Free-tier volatility can create an accidental production dependency or misleading cost floor. | **Verify** official tenancy limits; **drop** Oracle from the base case. | Medium |
| M6 | Medium | `01-consumer-landscape-home-search.md` §5 #4; `05-routing-and-precompute-architecture.md` Open question #1 | “Rush-hour from day one” conflicts with the admission that the proposed OSM/Valhalla setup has no traffic tiles. A static speed profile is not rush-hour traffic. | Labeling it rush hour would be a product-trust failure. | **Revise** to “modeled commute profile” or **drop** the toggle until validated traffic data exists. | High |
| M7 | Medium | `04-data-sources-and-legal.md` §4 “Stored, commercial-safe core” | Crime, school grades, demographics, noise, canopy, broadband, flood, food access, slope, and more are proposed before the home-search wedge is validated. | This expands data liability, fairness risk, QA surface, and refresh work without proving user value. | **Drop/defer** all but commutes, a few amenity categories, listings handoff, and flood disclosure if users request it. | High |
| M8 | Medium | `03-open-source-landscape.md` §5; `04-data-sources-and-legal.md` §4 | Doc 03 recommends DuckDB; doc 04 labels PostGIS the core store without reconciling operational needs or migration triggers. | Two persistence strategies can leak into schemas and deployment prematurely. | **Revise** to DuckDB for the spike and define explicit PostGIS migration thresholds. | High |

## Detailed notes on Critical and High findings

### C1 — Routing direction is under-specified

This is the most serious technical flaw because it changes the answer, not just performance. The checked CHCCS function `_ensure_bidirectional` literally adds a reverse edge wherever one is missing, then Dijkstra runs outward from each school; that can be tolerable for walking but invalid for driving. A correct “can this cell reach the office?” surface uses a shortest-path search from the office on the **transposed** directed graph, or queries each origin on the original graph. The same requirement applies to Valhalla: the plan must test arrival/reverse semantics, not assume a normal origin isochrone answers a commute-to-work query.

### C2 — Google caching posture may be unsafe

The document correctly treats `place_id` as special, but likely generalizes a 30-day exception too far. My training-based understanding is that temporary caching of latitude/longitude is allowed for up to 30 days, while other Google Maps Content remains subject to a broader no-caching rule unless service-specific terms expressly permit it. Because terms are versioned and high-stakes, this should be a source-registry entry with the exact clause and fields, not a prose summary. Until then, the safe architecture is live fetch plus place-ID persistence only.

### C3 — The wedge depends on an unproven handoff

The research itself says the Zillow and Redfin formats are undocumented and derives them partly from scraper projects. Those URLs can work today and still be unsuitable as a product contract: mobile app interception, region slug requirements, parameter stripping, or site redesign can break them. RentCast is a separate risk: the captured clause permits storage only as necessary for listed permitted uses, but that full list was not read. A one-day experiment should generate representative Triangle polygons, open links on desktop/iOS/Android, confirm map bounds and filters, and have the owner read/save the complete RentCast terms.

### H1 — Single-box memory is not established

“Graph in RAM” can mean compact CSR arrays or a Python NetworkX graph with dictionaries, geometries, node IDs, and indexes; these are radically different footprints. The proposed box also hosts Valhalla, DuckDB, FastAPI, cache, and concurrent workers. A 4 GB recommendation is therefore premature, especially when the success criterion allows a 2 GB graph service plus 1.5 GB Valhalla before OS/page cache. Benchmark on 8 GB first and downsize only from observed peak RSS.

### H2 — Performance and cost estimates are a fragile chain

The arithmetic for average monthly requests is fine, but average rate is not capacity planning. Two arbitrary anchors can transfer roughly 2 MB of raw aligned grids, before JSON/base64 mistakes, and a household demo naturally creates correlated bursts during exploration. The browser also needs six static layers, decompression, algebra, polygonization, and POI filtering. Report p50/p95 under 5–10 concurrent users and measure compressed binary responses before asserting a $10 box handles 10k monthly users.

### H3 — ODbL separability is not automatic

Separate tables are helpful evidence of intent, but they do not decide the legal classification. If an entity resolver declares an OSM row and an Overture row to be the same place, shares identifiers, or backfills attributes, the result may be more than a collective database. The document acknowledges correction/backfill risk but then recommends linking through “our own entity ID” as though that resolves it. Preserve source-native records and lineage, and obtain advice on the exact proposed joined output before monetization.

### H4 — Overture licensing fails open in reusable code

The code spot-check found `_license_for_row` returning CDLA-Permissive-2.0 whenever a non-Foursquare row has no explicit licence. That may match a known Overture release today, but it converts absence of evidence into a permissive grant. A robust ingest should derive licence from a pinned release/source manifest and quarantine unknown contributors or schemas. This is especially important because the research proposes copying this collector as the commercial-safe core.

### H5 — Canonical grid choice is unresolved

H3 is attractive for cell IDs and vector display, while square rasters are attractive for COGs, typed-array algebra, and image operations. The documents alternately prescribe each, creating a hidden resampling step. At average areas, H3 r10 has about 1.5 times the area of a 100 m square, and its center spacing is not 100 m. Build the same two-commute view both ways and choose on mobile payload, visual stability, join complexity, and boundary error.

### H6 — Transit is an unresolved scope decision

The hotel/site-selection stream lets a later use case dictate a from-day-one engine capability, while the routing stream correctly identifies transit as time-windowed, compute-heavy, and operationally distinct. The owner chose home search as the wedge, so later hotel differentiation should not automatically pull R5/OTP/MOTIS into phase 1. Ask the first households whether transit is a purchase constraint; if yes, test one scheduled AM surface, otherwise keep the schema extensible and defer implementation.

### H7 — Interaction evidence does not choose the UI

The research mixes vendor case studies, self-reported preference, general engagement lifts, forum anecdotes, and product screenshots. None isolates whether NL entry, visible chips, hex shading, or better listings caused the measured outcomes, and doc 02 contradicts doc 01 about whether filters are visible. The strongest low-cost alternative is a map-first two-address flow with direct controls and optional NL added only after the result works. Test both with 3–5 actual households and measure time-to-trusted-region and correction rate.

### H8 — IDX feasibility is not represented by feed price

The national IDX policy is a floor, not the full local contract. Doorify can impose local display, vendor, refresh, branding, security, audit, and participant-control rules, and a brokerage must be willing to own the display. The quoted connection/monthly feed fees omit the economically important prerequisites. Until a broker and Doorify confirm the structure in writing, IDX is a future option rather than the established path for pins.

### H9 — The MapLibre constraint needs a versioned test

Raster styling has been changing quickly, so a claim tied to an open issue can age badly. Conversely, pretending travel minutes are terrain elevation may make nodata, interpolation, alpha thresholds, and quantization behave unexpectedly. A 100-line spike against the selected MapLibre version will settle whether native raster colorization, a custom layer, or Worker canvas is simplest. Do that before the frontend architecture is chosen.

### H10 — Dijkstra timing omits the real pipeline

Compiled shortest paths may indeed be fast, but the product path includes graph construction, direction handling, POI snapping, cell-edge interpolation, cutoff semantics, encoding, and transfer. Multi-source `min_only` also yields only the nearest destination distance, which is right for a category but not k-nearest depth or provenance. Measure an end-to-end grocery/walk layer and a drive layer on the actual graph, including correctness comparisons. The benchmark should decide whether own-graph drive survives or Valhalla becomes the single routing truth.

## Attacks on the emerging recommendation

### a. Hybrid static-first architecture

**Failure mode:** directed-drive errors, oversized anchor grids, mobile memory, R2 range-request behavior, or a 4 GB box unable to hold both routing stacks. **Strongest alternative:** a server-first prototype using one routing engine and returning a compact PNG/mask plus GeoJSON; add static distribution only after interaction is validated. **Cheap experiment:** implement two category layers and two anchors for one Triangle subregion, deploy on an 8 GB VPS, and measure p95 latency/RSS plus a throttled mid-range phone before building 75 layers.

### b. NL to editable chips over a live grid

**Failure mode:** parsing corrections take longer than direct entry, chips crowd mobile screens, or users distrust a dense heat map. **Strongest alternative:** direct two-address controls with map pins/sliders and an optional “describe it” shortcut. **Cheap experiment:** clickable A/B prototype with 3–5 target households; compare completion time, correction count, comprehension, and willingness to use the result.

### c. Deep links plus RentCast pins

**Failure mode:** portal URLs break or open a bbox that is too broad, app handoff loses filters, RentCast lacks coverage/freshness, or its licence/provenance fails review. **Strongest alternative:** show the exact region and offer robust city/ZIP portal links while using county parcel/sales data as context; pursue a broker-controlled IDX widget only after demand. **Cheap experiment:** test 20 generated links and 50 known listings across devices, then obtain written RentCast answers on permitted display and upstream rights.

### d. Drop Tripadvisor and public Valhalla dependencies

**Failure mode:** dropping Tripadvisor is unlikely to hurt the home wedge; dropping public Valhalla without a proven host can stall arbitrary anchors. **Strongest alternative:** keep the public server strictly for development with a hosted Mapbox/ORS fallback during the spike, then self-host only after measured demand. **Cheap experiment:** compare 100 representative isochrones across public Valhalla, a local NC build, and one hosted API for accuracy, latency, and failure behavior.

### e. Overture plus separable OSM POIs

**Failure mode:** Overture misses parks/trails or contains duplicates, OSM linkage creates ODbL ambiguity, category mapping is poor, and monthly rebuilds change results unexpectedly. **Strongest alternative:** source-preference by category with no cross-source entity merge in v1 (Overture for businesses, OSM/government for parks/transit), preserving independent records. **Cheap experiment:** manually audit 200 Triangle POIs across five wedge categories, record precision/recall/duplicates/licence provenance, and choose per-category sources before precomputing.

## Load-bearing unverified claims that must be checked before planning

- [ ] Directed/reverse routing produces “home can reach destination” times for own Dijkstra and Valhalla, including one-way roads.
- [ ] Zillow and Redfin bbox deep links preserve bounds and filters on desktop and mobile, and their use remains acceptable under current terms.
- [ ] Full RentCast permitted uses and upstream listing rights cover public map pins, caching, and monetization.
- [ ] Current Google Places terms permit each proposed cached field; otherwise only `place_id` is persisted.
- [ ] Actual NC Valhalla build peak, tile size, serving RSS, GeoTIFF semantics, and p95 isochrone latency on the intended VPS.
- [ ] Triangle SciPy/CSR precompute time, memory, accuracy, and serialization, measured end to end.
- [ ] Browser thresholding/rendering/polygonization and R2 range requests meet targets on a mid-range phone and throttled 4G.
- [ ] OSM/Overture schema and entity-linking approach remains a Collective Database; obtain qualified advice before monetization.
- [ ] Doorify's current local IDX/vendor terms allow the proposed partner-controlled embedded display.
- [ ] MapLibre's exact selected version cannot natively style the required raster; test before choosing canvas/Terrarium.
- [ ] Amadeus Self-Service shutdown, Oracle free-tier limits, and all quoted vendor/free-tier pricing from official current sources.

## Missing alternatives worth a look

- **Hosted matrix/isochrone broker for the prototype:** compare Mapbox, Stadia/Valhalla hosting, ORS, and TravelTime on total engineering cost, not only request price.
- **Cloudflare Worker as cache/orchestrator:** useful for signed R2 manifests and caching compact anchor masks, but not for routing itself.
- **Raw chunked arrays/Zarr versus PMTiles/COG:** Worker algebra may be simpler and smaller without pretending analysis rasters are display tiles.
- **Server-rendered mask first:** PNG/GeoJSON responses can validate product behavior before DuckDB-Wasm and client polygonization.
- **Zillow Bridge/MLS analytics licences:** not presumed available, but a direct inquiry could reveal a licensed path distinct from IDX.
- **Mobile-first interaction constraints:** test touch target density, geolocation, app deep-link behavior, memory, and offline/back-button behavior explicitly.

## What the research got right

The research correctly rejects scraping, public routing servers as production dependencies, and chat-only interaction. It identifies the reusable assets: structured tool calling, provenance-aware POI ingestion, a grid/raster pipeline, and a small Valhalla client. Tiered geography, category precompute versus arbitrary anchors, visible correction, and a source registry are sound directions. The next step is to turn load-bearing uncertainties into measured gates before architecture selection.
