# 05 — Routing, Isochrones, and Precompute/Serving Architecture

**Date:** 2026-11-03
**Status:** Complete (research; no code changed). Numbers marked *(estimate)* show their arithmetic; items marked *(unverified)* could not be confirmed against a primary source today.
**Scope and method:** Web research against official docs, pricing pages, GitHub issues/discussions and project pages (all accessed 2026-11-03; URLs in §10), combined with the in-house numbers from `00-existing-assets-audit.md` (CHCCS 100 m grid engine, V1 Valhalla client, localUpdates DuckDB/Overture store). Sizing estimates are for the Research Triangle defined as Wake + Durham + Orange + Chatham counties. The web-search budget for this session ran out part-way; the remaining gaps (FOSSGIS Valhalla terms page, openrouteservice per-endpoint quotas, HERE's own pricing page, Close's technical stack) are flagged rather than guessed.

---

## 1. Executive summary

- **Hosted routing APIs are fine for friends-and-family and wrong for the product.** Every free tier is either non-commercial (GraphHopper 500 credits/day, TravelTime 120 hits/min "development and testing only", FOSSGIS OSRM/Valhalla "1 request per second, no heavy usage"), too small (HERE isoline 2,500/month, openrouteservice ~500 isochrones/day *(unverified)*), or metered in a way that bills per request forever (Mapbox 100k free then $2/1k; Google Isochrones 10k free then $3/1k once GA). Public use of the FOSSGIS Valhalla demo, which V1 depends on, is not an acceptable production path.
- **Self-hosting the North Carolina extract is small.** Geofabrik's `north-carolina-latest.osm.pbf` is 410 MB. By the published rules of thumb (ORS: 450 MB Baden-Württemberg → 2–4 GB RAM; OSRM blog: ~2 GB RAM per 100 MB PBF during extract; Valhalla: "city or small region 2–4 GB") a Valhalla or ORS instance for NC fits a **2 vCPU / 4–8 GB VPS costing $7–10/month** (Hetzner CX23 $6.70, CX33 $10.05 via getdeploying; Fly shared-cpu-1x 1 GB $6.70, 2 GB $13.39). Tiles can be built on the Windows machine under WSL2/Docker Desktop (default VM memory = 50% of host RAM, raise via `.wslconfig`) and uploaded.
- **Oracle's Always Free ARM tier was halved on 2026-06-15 to 2 OCPU / 12 GB.** That is still enough to serve Valhalla for one state at $0, but capacity availability is unreliable; treat it as a bonus, not the plan.
- **For category constraints, per-cell "minutes to nearest POI of type T by mode M" rasters (the CHCCS approach) dominate the alternatives** on storage, compute and query latency. The Triangle at 100 m is ~570k land cells (~950k pixels in the bounding box); 75 layers (25 categories × 3 modes) as uint8 are **~71 MB raw, ~15–30 MB compressed** *(estimate)*. H3 or grid travel-time *matrices* (Helsinki-style) blow up for driving (91k 250 m cells → 8.3 billion pairs); cached per-POI isochrone polygons are heavier and only answer the thresholds you precomputed.
- **Compute is minutes, not days, if we leave networkx.** One multi-source Dijkstra per (category, mode) over a metro graph of ~1–1.5 M edges is ~10–20 s in pure-Python networkx but ~0.2–1 s with `scipy.sparse.csgraph.dijkstra(min_only=True)` or igraph *(estimate)*. Seventy-five layers plus grid snapping is **well under an hour on the existing Windows machine**; the bottleneck becomes building the graph from the PBF (use pyrosm/osmium, not Overpass).
- **Arbitrary user anchors (office, friend's house) need one on-demand computation each**: either a Valhalla isochrone (self-hosted; Valhalla can return the raw time grid as a GeoTIFF, which drops straight onto our raster) or a reverse Dijkstra over our own graph on the API server. Both are sub-second for walk/bike and ~0.5–2 s for a 45-minute drive *(estimate)*; TravelTime's published benchmark for a hosted engine is 90–290 ms.
- **Combine layers in the browser.** Thresholding six uint8 layers over a 1 M-pixel viewport is tens of milliseconds in a Web Worker; polygonizing with marching squares (d3-contour client-side or `rasterio.features.shapes` / `skimage.measure.find_contours` server-side) is 0.1–1 s. Sliding a threshold should never round-trip to a server.
- **Serve the static tier from Cloudflare R2 + Pages at $0.** R2's free tier is 10 GB-month, 1 M Class A and 10 M Class B operations, with free egress; Pages caps single assets at 25 MiB (so PMTiles/COGs go in R2, not Pages); GitHub Pages is 1 GB / 100 GB-month soft and forbids SaaS use. PMTiles and COG both work by HTTP range requests from dumb storage; `maplibre-cog-protocol` requires EPSG:3857 COGs.
- **MapLibre cannot yet threshold arbitrary rasters natively.** `color-relief` exists but only for `raster-dem` sources; the proposal to extend pixel styling to any raster (maplibre-style-spec #1490, opened 2026-02-02) is still open. Options: encode minutes as Terrarium "elevation" and use `color-relief` (spike), a canvas/deck.gl custom layer, or compute in a Worker and draw to a canvas source.
- **Replace Overpass-at-request-time with pre-ingested Overture places.** Overture is 88 M places, monthly releases (`2026-10-21.0` current; next 2026-11-18), CDLA-Permissive-2.0/Apache-2.0, with a 0–1 confidence score and a 2,300-category taxonomy; DuckDB (native and Wasm, which includes the `spatial` extension) reads the GeoParquet with bbox pushdown. A Triangle slice is tens of MB. Keep Overpass only as a gap filler for categories Overture lacks.
- **Transit is a different animal.** GTFS for all seven Triangle agencies is published (GoTriangle developer page). Transit travel time is time-dependent, so a precomputed layer means "walk+transit, weekday 8–9 am departure window, median" computed with r5py (as Helsinki did for 13,231 cells × 4 modes × 3 windows). Precompute at 250 m for categories; defer on-demand transit anchors (needs an R5/OTP server in RAM) to a later phase.
- **Accuracy trade-off is real but manageable.** Static-speed Dijkstra on a bidirectional graph ignores one-ways, turn costs and signals that Valhalla models; for a *threshold* product the question is whether the 10-minute walk boundary moves by more than a cell or two. Calibrate the CHCCS speed model against Valhalla on a few hundred sampled pairs before trusting the layers (Spike 2).
- **Recommended architecture (one paragraph).** *Hybrid, static-first.* Precompute category travel-time rasters for the Triangle on the Windows machine (own graph from the Geofabrik PBF, csgraph multi-source Dijkstra, uint8 minutes, 100 m walk/bike and 250 m drive), publish them as PMTiles (or COGs) plus an Overture-derived places GeoParquet/FlatGeobuf to Cloudflare R2, and host the SPA on Cloudflare Pages. The browser fetches viewport tiles, does threshold/AND/weighted scoring in a Worker, polygonizes, and lists POIs/listings inside the region. One small always-on VPS (Hetzner CX33-class, ~$10/month) runs self-hosted Valhalla for NC plus a FastAPI service that (a) returns anchor isochrones as grids cached by rounded point/mode/minutes, (b) runs on-demand multi-source Dijkstra for categories not in the precomputed set, and (c) proxies anything needing secrets. Friends-and-family cost: $0–10/month; 10k-user cost: $10–25/month. The thing this design makes hard is on-demand transit for arbitrary anchors; everything else scales by adding files.

---

## 2. Routing providers: hosted and self-hosted

### 2.1 Hosted / public servers

| Provider | Free tier (as published) | Paid | Key limits | Fit: friends & family | Fit: public product |
|---|---|---|---|---|---|
| **FOSSGIS Valhalla demo** (`valhalla1.openstreetmap.de`) | Shared demo; FOSSGIS terms page is behind an anti-bot wall today. The sibling OSRM "about" page says "one request per second max", no scraping, no "heavy usage". | none | Default Valhalla limits: 4 contours, 120 min max time contour, 1 isochrone location, 2,500 matrix pairs | OK at low volume, with a User-Agent and caching | **No** — volunteer-run, no SLA, no commercial terms |
| **FOSSGIS OSRM demo** (`router.project-osrm.org`) | "Do not exceed 1 request per second", "reasonable, non-commercial use-cases", "no guarantees wrt. uptime, latency, or data updates" | none | No isochrone endpoint at all (route/nearest/table/match/trip/tile only) | OK for routes/tables | **No** |
| **openrouteservice (HeiGIT)** | Free Standard key; FAQ confirms per-endpoint daily and per-minute limits, e.g. directions 2,000/day and 40/min, rolling 24 h reset. Isochrones/matrix quotas *(unverified today; plans page 404s; previously ~500/day, 20/min for isochrones)* | Collaborative/research plans by request | Public isochrone range capped (~60 min) *(unverified)* | OK | **No** at these quotas; self-host instead |
| **GraphHopper Directions API** | 500 credits/day, "non-commercial use only", 5 locations max, no flexible mode | Basic €69/mo 5,000 credits/day; Standard €199 15,000; Premium €479 50,000 | Isochrone max 15–30 min on standard plans, 60 min Custom; matrix billed per origin×destination pair | OK | Only with a paid plan; isochrone time cap is a product constraint |
| **TravelTime** | 120 hits/min on Basic keys, "development and testing only; not for commercial use". One origin = one hit regardless of destination count. | Fixed annual subscription on provisioned hits/minute, 12-month minimum, price unpublished | Isochrone 4 h max; 10 departure + 10 arrival searches, 10 unions, 10 intersections per request; multimodal incl. transit | Good (unions/intersections are exactly our query) | Possible but enterprise-priced and unquantifiable |
| **Mapbox Isochrone API** | 100,000 requests/month | $2.00 per 1,000 for 100k–500k, declining above | 4 contours, 60 min max, 100 km max distance, 300 req/min; driving-traffic/driving/walking/cycling | Good | Viable: 10k users × 10 isochrones = 100k/month = $0; 60-minute cap bites for airport commutes |
| **Google Routes API** (Compute Routes / Compute Route Matrix Essentials) | 10,000 events/month each | $5.00/1k (10k–100k), $4.00 (100k–500k), $3.00 (500k–1M), $1.50, $0.38 | Route Matrix bills per *element* | Fine | Expensive at scale for matrices; no isochrone here |
| **Google Isochrones API** (new) | Pre-GA Preview: no charge during preview; at GA 10,000 requests/month free | $3.00/1k (0–100k) to $0.24/1k (5M+) at GA | 300 requests/min/project | Good while in preview | Cheapest big-vendor isochrone once GA; preview terms can change |
| **HERE Isoline Routing** | 2,500 transactions/month *(third-party summaries; HERE's own pricing page would not render)* | ~$5.00 per 1,000 *(unverified)* | 30,000/month free for standard routing *(unverified)* | Marginal | Pricey for isochrones |

Takeaways: for development use the public FOSSGIS Valhalla with a descriptive User-Agent, under 1 req/s, and cache aggressively (the audit already recommends caching by rounded lat/lon, mode, minutes). For anything public, either self-host or pay Mapbox/Google per isochrone. At our volumes self-hosting is cheaper than any hosted option past the free tier and removes the 60-minute caps.

### 2.2 Self-hosting options

| Engine | Isochrones | Matrix | Transit | RAM for NC (410 MB PBF) | Build | Notes |
|---|---|---|---|---|---|---|
| **Valhalla** | Yes; 4 contours default; polygons or lines; `generalize`/`denoise`; **raw grid as GeoTIFF** | `sources_to_targets`, default 2,500 pairs (configurable), `costmatrix` faster than `timedistancematrix` | Multimodal with GTFS ingest (experimental) *(unverified maturity)* | Docs: "city or small region 2 CPU, 2–4 GB". Build of NC: 4–8 GB peak *(estimate: ~10× the 410 MB PBF, mmap inflates apparent usage per discussion #3288)*; serving RSS well under 2 GB | Planet ~24 h on 24 threads/NVMe; NC tens of minutes *(estimate)* | Docker image moved upstream (nilsnolde/docker-valhalla archived 2026-03-03); tiles are plain files, so build on Windows/WSL2 and `scp` the tar |
| **OSRM** | **No isochrone endpoint** | `table` service; `--max-table-size` default 100 (raise by flag); CH very fast for big tables | No | Extract: ~2 GB per 100 MB PBF → ~8 GB for NC *(blog rule of thumb)*; runtime 1–3 GB for a US state (MLD) | Minutes for a state | Best pure matrix engine; irrelevant to isochrones unless we rasterize tables ourselves |
| **GraphHopper (OSS)** | `/isochrone` endpoint; `/spt` shortest-path-tree endpoint returns per-node times *(unverified in current version)* | Matrix is in the paid API; OSS has routing + spt | PT routing exists but limited | World import ~60 GB; NC ≈ 0.5% of world → ~1 GB heap *(estimate: 410 MB / ~80 GB planet)* | Fast for a state | Java; `spt` is attractive for "Dijkstra from a point, give me node times" |
| **openrouteservice** | Yes, multiple locations, intervals | Yes | No | Docs: Baden-Württemberg (450 MB) 2–4 GB; Germany (3 GB) ~8 GB; planet 100–105 GB for bike+ped | More RAM = faster build | Java; `vm.max_map_count=81920` for big builds in containers |
| **R5 / r5py** | Via travel-time matrices (origins × destinations), departure windows, percentiles | Yes (that is its job) | **Yes**, GTFS; RAPTOR; time-sensitive | r5py grants JVM up to 80% of RAM minus 2 GiB by default; Helsinki-style regional runs use ~6–12 GB | Minutes for region | The right tool for transit precompute; Helsinki 2023 matrix used a patched R5 |
| **OpenTripPlanner 2** | Isochrone endpoint (Traveltime API) | No general matrix | Yes | "Less than 1 GB to more than 100 GB"; Portland GTFS+OSM runs at ~1.4 GB heap, NYC 11 feeds at 3 GB | Minutes | Better as a trip planner than a batch engine |

**VPS sizing and cost (monthly, 2026-11-03):**

| Host | Plan | Specs | Price | Notes |
|---|---|---|---|---|
| Hetzner Cloud | CX23 | 2 vCPU / 4 GB | $6.70 *(getdeploying; Hetzner site says "from €5.99/€6.49", Cost-Optimized line "currently not available")* | US regions Ashburn, Hillsboro exist; plan availability per region to confirm |
| Hetzner Cloud | CX33 | 4 vCPU / 8 GB | $10.05 | Comfortable for Valhalla + Python graph server + DuckDB |
| Hetzner Cloud | CX43 | 8 vCPU / 16 GB | $18.43 | Room for r5py/OTP transit |
| Fly.io | shared-cpu-1x 1 GB | 1 vCPU shared / 1 GB | $6.70 | RAM $6/GB extra; stopped machines $0.15/GB rootfs; egress $0.02/GB NA |
| Fly.io | shared-cpu-1x 2 GB | 1 vCPU shared / 2 GB | $13.39 | Auto-stop/start gives a true scale-to-zero router |
| Railway | Hobby | usage-based | $5 incl. $5 credit; RAM $10/GB-mo, vCPU $20/vCPU-mo | A 2 GB always-on router ≈ $40/mo — poor fit for a routing daemon |
| Render | Free web service | spins down after 15 min idle, ~1 min restart, 750 h/month | $0 | Not for a router (restart delay, RAM too small *(size unverified)*) |
| Oracle Cloud | Always Free Ampere A1 | **2 OCPU / 12 GB since 2026-06-15** (was 4/24) | $0 | Enough for NC Valhalla; capacity shortages and silent policy changes are the risk |

**Docker on Windows feasibility:** WSL2's VM defaults to 50% of host RAM and all logical processors, both overridable in `%UserProfile%\.wslconfig` (`memory=`, `processors=`, `swap=`). Valhalla, OSRM, ORS and r5py are all Linux containers that run fine under Docker Desktop; the only practical issue is that Valhalla's build mmaps large files and will look like it uses far more RAM than it needs (discussion #3288). Build on Windows, serve on the VPS.

**Cold-start patterns:** Fly machines stop when idle and resume in seconds (rootfs billed at $0.15/GB while stopped); Render free restarts take ~1 minute; Railway bills nothing for stopped services. Valhalla loads tiles lazily via mmap so a cold Valhalla is fast; R5/OTP (JVM + graph load) are the slow starters, which is another reason to keep transit out of the on-demand path initially.

**Matrix endpoint realities:** Valhalla 2,500 pairs by default, raise in `valhalla.json`; OSRM 100 locations by default (`--max-table-size`); GraphHopper and Google bill per pair/element; TravelTime bills per origin only; Mapbox Matrix counts elements. None of these make "all cells × all POIs" feasible for a metro — that is why the destination-outward Dijkstra precompute exists.

---

## 3. Precompute design

### 3.1 Comparison

| Design | What is stored | Storage scaling | Compute | Query | Answers | Cannot answer |
|---|---|---|---|---|---|---|
| **(a) Per-cell minutes-to-nearest-POI rasters** (CHCCS) | One uint8/float16 raster per (category, mode) | cells × categories × modes; ~1 MB per 100 m layer | One multi-source Dijkstra per layer (seconds with csgraph) | Pixel threshold; instant | "≤ N min by mode M to *any* T"; soft decay scores; k-nearest with extra bands | Travel to a *specific* POI (needs its own layer or an isochrone); "count within N min" unless extra bands |
| **(b) Cell-to-cell travel-time matrices** (H3/grid; Helsinki model) | T[origin cell][destination cell] | cells²: H3 r9 (0.105 km²) → 54k cells → 2.9 B pairs; r8 (0.74 km²) → 7.7k cells → 59 M pairs ≈ 119 MB uint16 | Many Dijkstras or router matrix calls | Row lookup; any anchor snapped to a cell is instant | Arbitrary anchors *and* categories (min over POI cells) | Fine resolution for driving; dense drive matrices are the problem (most cells reach most cells in 60 min) |
| **(c) Cached isochrone polygons per POI** | Polygons at fixed thresholds | POIs × modes × thresholds × 5–20 KB | One router call per polygon (15k+ calls for the Triangle) | Union of hundreds of polygons (shapely 1–5 s) | Precise shapes at precomputed thresholds | Any threshold not precomputed; heavy client union; no scoring |
| **(d) Network distance in pgRouting / DuckDB** | Graph tables; results computed per query | Graph only | `pgr_drivingDistance` supports many root vids with `equicost` (Boost Dijkstra) | Seconds per query on a metro graph | Anything, at analysis speed | Interactive latency; DuckDB has no routing at all (routing must happen in Python) |

**Verdict:** (a) for categories, Valhalla-or-own-graph on demand for anchors (and cache the result in (c) form keyed by rounded point/mode/minutes), (b) only as a coarse optional drive lookup (H3 r8 ≈ 900 m) if on-demand anchors ever become a cost problem, (d) for offline analysis only.

### 3.2 Triangle sizing (arithmetic shown)

**Land area** (Wikipedia, 2026-11-03): Wake 834.59 mi² (2,161.6 km²), Durham 286.53 (742.1), Orange 397.56 (1,029.7), Chatham 681.68 (1,765.5). **Total 2,200.4 mi² = 5,698.9 km²**; population ≈ 1.84 M (2025 estimates: 1,257,235 + 347,240 + 152,498 + 85,111).

**Bounding box** *(estimate)*: ~1.3° longitude × ~0.73° latitude at 35.9° N ≈ 117 km × 81 km ≈ 9,480 km².

| Resolution | Cells/km² | Land cells | Bbox pixels | uint8 per layer (bbox) | float16 | float32 |
|---|---|---|---|---|---|---|
| 50 m | 400 | 2.28 M | 3.79 M | 3.8 MB | 7.6 MB | 15.2 MB |
| **100 m** | 100 | **570 k** | **948 k** | **0.95 MB** | 1.9 MB | 3.8 MB |
| **250 m** | 16 | **91 k** | **152 k** | **0.15 MB** | 0.30 MB | 0.61 MB |

**75 layers (25 categories × walk/bike/drive):**
- 100 m uint8: 75 × 0.95 MB = **71 MB raw**; deflate/zstd on smooth travel-time surfaces typically 3–5× → **15–30 MB** *(estimate)*.
- 100 m float16: 142 MB raw. Not needed: uint8 at 0.5-minute steps covers 0–127 min with 255 = nodata, which exceeds any threshold we expose.
- 250 m uint8: 75 × 0.15 MB = **11 MB raw**.
- Mixed plan (100 m walk/bike = 50 layers, 250 m drive = 25 layers): 50 × 0.95 + 25 × 0.15 = **51 MB raw**.
- Adding 2nd- and 3rd-nearest bands for Walk-Score-style "depth of choice": ×3 → ~150 MB raw at 100 m. Still trivial for R2's 10 GB free tier.
- Transit (250 m, walk+transit, one AM window, 25 categories): +3.8 MB.

**Compute** *(estimates; Spike 1 measures them)*:
- Graph: NC PBF 410 MB; Triangle drive graph ~300k nodes / ~700k edges after simplification, walk graph ~600k / ~1.5 M (the audit's CHCCS district graph was ~70 km²; the Triangle is ~80× the area but much of it is rural).
- Multi-source Dijkstra, networkx (pure Python, ~5–10 µs per edge relaxation): 1.5 M edges ≈ 10–20 s per run → 75 runs ≈ **12–25 min**.
- Same with `scipy.sparse.csgraph.dijkstra(indices=sources, min_only=True)` or igraph: ~0.2–1 s per run → 75 runs ≈ **1–2 min**.
- Grid snapping (shapely 2 STRtree nearest, lon-scaled, per mode graph): 570k points × 3 graphs ≈ 15–60 s total.
- Rasterize + write COG/PMTiles: seconds per layer.
- **Whole Triangle precompute: < 1 hour on the Windows machine, dominated by building the graph from the PBF** (pyrosm/osmium from Geofabrik, not Overpass). CHCCS's Overpass dependency for stop/signal tags should be replaced by reading those tags from the PBF.
- Comparison: doing category layers with Valhalla isochrones instead would be ~5,000 POIs × 3 modes = 15,000 calls (~0.3 s each on a laptop → ~75 min) and would yield only fixed-threshold polygons.

**Refresh cadence:** Overture ships monthly (next 2026-11-18); Geofabrik NC updates daily. Networks change slowly; POIs churn faster. Recommend **monthly layer rebuilds** triggered after each Overture release (Task Scheduler → WSL script → upload to R2), quarterly re-check of the speed model, and on-demand isochrone cache invalidation keyed to the Valhalla tile build date.

### 3.3 Transit

- GTFS is published for GoTriangle, GoRaleigh, GoDurham, GoCary, Chapel Hill Transit, NC State and Duke (GoTriangle developer resources), all with GTFS-realtime.
- Transit travel time is time-dependent; any precomputed layer is a statement like "walk + transit, Wednesday 08:00–09:00 departures, median (or 50th-percentile per Conveyal)". Helsinki computed 13,231 origins × 13,231 destinations × 4 modes × 3 windows with r5py; Conveyal computes one origin per worker task over a departure window and reports percentiles.
- For us: r5py from all 91k 250 m cells to all ~5k POIs (r5py returns all destinations per origin, so all categories come from one run). At ~0.1–0.5 s per origin on a bus-only network *(estimate)* that is 2.5–13 hours per departure window, i.e. an overnight job on the Windows machine with a 12 GB heap. Then take the per-category minimum → 25 transit layers.
- **Recommendation:** precompute transit-to-categories at 250 m for one weekday-AM window as a later phase; do *not* offer on-demand transit anchors until a JVM router (R5 or OTP2) is worth keeping in RAM. Triangle transit mode share is small *(unverified)*, so the wedge does not need it.

### 3.4 Accuracy trade-offs

- **Static speeds vs Valhalla costing.** CHCCS uses friction speeds by `highway` class and node penalties (signal 22 s, stop 11 s, yield 6 s, crossing 3 s) on a *bidirectional* graph; Valhalla's `auto` costing adds one-way handling, turn costs, access restrictions, maneuver penalties, and (if tiles have it) time-dependent speeds. For walking, Valhalla's default speed is ~5.1 km/h *(unverified)* versus CHCCS's 1.12 m/s (4.0 km/h, K-5 children) — a 27% systematic difference that moves a 10-minute boundary by ~150 m. Fix: adopt an adult 1.4 m/s profile and calibrate drive friction speeds against Valhalla on sampled pairs (Spike 2). Driving is the mode where own-graph Dijkstra is weakest (one-ways, interchanges); if Spike 2 shows >25% error, compute the 25 *drive* layers with Valhalla's GeoTIFF isochrone grid output instead (still a batch job).
- **Nearest-edge snapping.** Snapping a cell centre to the nearest edge of a *mode-specific* graph (so pedestrians never snap to a motorway), adding the perpendicular access distance at mode speed, and marking cells >200 m from any edge unreachable (the CHCCS rule) is standard and matches how routers snap. Known failure modes: gated communities and cul-de-sacs (over-optimistic), large parcels (cell centre far from the driveway), and area POIs represented as centroids (a 200-acre park's centroid is a poor destination; use boundary vertices every ~100 m or mapped entrances as sources).
- **Isochrone generalization.** Valhalla's `generalize` (Douglas-Peucker metres) and `denoise` (drop small islands) and Mapbox's equivalents trade fidelity for payload; V1 silently kept only the largest polygon, losing legitimately reachable islands. Keep MultiPolygons; when rasterizing, islands cost nothing.

---

## 4. Combining layers at query time

**Pipeline (client-first):**
1. Parse constraints into `[{layer | anchor, mode, minutes | miles, hard | soft, weight}]`.
2. For each category constraint, fetch the viewport's tiles for layer (T, M) from R2 (PMTiles range requests or COG). For each anchor, call the API once: `/isochrone-grid?lat,lon,mode,minutes` → uint8 grid aligned to our raster (server: Valhalla GeoTIFF grid or own-graph reverse Dijkstra, resampled to the shared `grid_params`; cached in DuckDB/R2 by rounded point).
3. In a Web Worker: `mask = AND_i (layer_i <= threshold_i)`; soft score `S = Σ w_i f_i(t_i)` with Walk-Score-style decay (full points ≤ 5 min, zero at 30 min, polynomial between); write RGBA to an `ImageData`.
4. Render: MapLibre `canvas` source (or deck.gl `BitmapLayer`) over the basemap; recompute on slider drag without network.
5. Vectorize on demand (for "download region" or listing search): marching squares (d3-contour in the browser; `skimage.measure.find_contours` or `rasterio.features.shapes` server-side), simplify (Douglas-Peucker 20–50 m), smooth (buffer −r/+r or Chaikin), keep holes/islands.
6. Places/listings inside the region: DuckDB-Wasm over a Triangle GeoParquet on R2 (spatial extension is available in Wasm; HTTPS + CORS required) or FlatGeobuf bbox streaming, then point-in-polygon client-side; server-side DuckDB for listings that carry licence restrictions.

**Server-first variant:** same math in numpy on the API (rasterio for IO), returning a PNG mask + GeoJSON. Simpler to build from the existing Python, but every slider move is a round trip.

**Latency estimates** *(all estimates; Spikes 4–6 measure)*:

| Step | Client-first | Server-first |
|---|---|---|
| Fetch 6 category layers for a metro viewport (6 × 3–10 tiles × 20–40 KB ≈ 0.4–2 MB) | 200–600 ms on broadband, ~1–2 s on 4G | server reads local files: ~50 ms |
| Anchor isochrone, walk/bike 15 min | 100–300 ms incl. RTT | same |
| Anchor isochrone, drive 20–25 min | 200–600 ms | same |
| Anchor isochrone, drive 45 min (RDU) | 0.5–2 s | same |
| Threshold + AND + score over ~1 M px × 6 layers | 20–60 ms (typed arrays); <10 ms WebGL | 10–30 ms numpy |
| Polygonize 1 M px | 100–400 ms (d3-contour) | 200–1,000 ms (`features.shapes`) + simplify |
| POIs inside region (150k Triangle places) | 50–200 ms DuckDB-Wasm bbox + PIP | 20–100 ms DuckDB |
| **Cold full query with 2 anchors** | **~1–3 s** | ~1–2 s + hosting cold start (Railway/Render 1–60 s) |
| **Slider change, no new anchors** | **<100 ms, no network** | 300–800 ms round trip |

Soft constraints: store minutes (not booleans) so scoring is a pure client-side function; expose "hard" as weight = ∞ (a threshold) and "soft" as a decay curve. Walk Score's published shape (max points within 5 minutes, decay to zero at 30, fifth-order polynomial fit, category weights 3/3/2/1) is a sensible default for amenities; commutes are better served by a user-set threshold with a soft margin (e.g., linear penalty from 20 to 30 min).

---

## 5. Storage and serving cheaply

### 5.1 Options

| Option | How it works | Fit for layers | Fit for places | Caveats |
|---|---|---|---|---|
| **COG on R2** (`maplibre-cog-protocol`, geotiff.js) | Range requests into one GeoTIFF per layer with overviews | Good; one file per layer, ~1 MB compressed | — | COG must be EPSG:3857, 256-px tiles; colour mapping via plugin colour functions; a few range requests per view |
| **PMTiles raster on R2** | One archive per layer (or per mode with 3–4 layers packed into RGBA), tiles z0–z11 (100 m ≈ z10–11 at 36° N) | Good; ~70 tiles per layer, 1.5–3 MB *(estimate)*; natively supported by MapLibre via the pmtiles protocol | Vector PMTiles for POIs too | Read-only; rebuild whole archive on refresh; CORS on bucket |
| **Raw uint8 arrays / Zarr chunks** | Fetch chunk files directly as `Uint8Array` | Simplest for Worker math; Zarr adds chunking metadata | — | No MapLibre rendering without our own canvas layer |
| **GeoParquet + DuckDB-Wasm** | SQL in the browser over R2 files with bbox pushdown | — | Excellent for Overture places (tens of MB for the Triangle) | Wasm bundle ~10 MB+; HTTPS-only; CORS |
| **FlatGeobuf** | Packed Hilbert R-tree, bbox range queries from static hosting | — | Good, lighter than DuckDB-Wasm | Preflight caching matters on CDN |
| **Cloudflare Pages** | Static SPA hosting | assets ≤ 25 MiB each, 20k files free, 500 builds/month | — | Big data goes to R2 |
| **GitHub Pages** | Static hosting | 1 GB site, 100 GB/month soft bandwidth | — | Prohibits SaaS/commercial use — fine for friends-and-family only |
| **Cloudflare Workers** | Edge functions, R2 bindings | 100k req/day free, 10 ms CPU; Paid $5/mo for 10 M req + 30 M CPU-ms | — | Cannot run Valhalla; fine for signed-URL proxies, caching, tiny APIs |
| **FastAPI on a VPS** (Hetzner/Fly) | Always-on Python + Valhalla + DuckDB | On-demand anchors, custom categories, listings | DuckDB native | The one paid component |
| **FastAPI on Railway/Render** | Usage-billed containers | OK for stateless API; poor for a 2 GB router daemon | — | Railway RAM $10/GB-mo; Render free spins down |

**Rendering stack:** MapLibre GL JS over Leaflet — PMTiles/COG protocols, `canvas` and custom WebGL layers, and `color-relief` (currently `raster-dem` only; a spike can test encoding minutes as Terrarium elevation to get native threshold colouring) all exist; Leaflet can show PNG overlays but has no GPU path. deck.gl is the fallback for multi-texture shader math if the Worker approach is too slow (it will not be at 1 M px).

### 5.2 Cost table

Assumptions: Triangle layers ~100 MB total in R2; places + listings data ~100 MB; each page view touches ~30 tile/range requests; 10k-user scale = 10,000 monthly users × 5 queries × 2 anchors = 100k anchor isochrones and ~1.5 M R2 Class B reads per month *(estimates)*.

| Component | Friends & family (≤ 20 users) | 10k monthly users |
|---|---|---|
| Static site (Cloudflare Pages) | $0 | $0 |
| Layers + places on R2 (≤ 1 GB, ≤ 10 M reads, free egress) | $0 | $0 (1.5 M Class B reads ≪ 10 M free) |
| On-demand router + API: Hetzner CX23/CX33 **or** Fly 1–2 GB auto-stop | $0 (public FOSSGIS Valhalla, ≤ 1 req/s, dev only) **or** $6.70–10.05 | $10.05 (CX33) — 100k isochrones/month is 0.04 req/s average |
| Edge proxy/cache (Workers free) | $0 | $0–5 |
| Domain | ~$10/yr | ~$10/yr |
| **Total** | **$0–10 / month** | **$10–25 / month** |
| For comparison: hosted isochrones at 100k/month | — | Mapbox $0 (free tier), Google $270 at GA, HERE ~$490 *(unverified)*, GraphHopper €199+ |

---

## 6. POI / places query performance

- **Replace Overpass at request time.** V1's 30 s–8 min Overpass calls become a one-time ingest: `SELECT … FROM read_parquet('s3://overturemaps-us-west-2/release/2026-10-21.0/theme=places/type=place/*') WHERE bbox.xmin BETWEEN … AND bbox.ymin BETWEEN …` in DuckDB (bbox columns give pushdown; DuckDB ≥1.1 casts the geometry column automatically). Filter `confidence ≥ 0.85` as localUpdates already does; map Overture's `categories.primary` / `hierarchy` (2,300 categories, ~280 `basic_category` labels) onto our 25 product categories. The Triangle slice is on the order of 100–150k places *(estimate from 88 M global)*, i.e. tens of MB as GeoParquet.
- **Overture quality caveats** (its own docs): duplicates, "a high junk rate, and low property completeness"; Overture places exclude OSM. Parks, trails, schools and transit stops are better in OSM. So the places table is **Overture + OSM extract (osmium tags-filter on the Geofabrik PBF) with per-row licence**, kept in separate tables so ODbL rows stay separable from CDLA/Apache rows and from proprietary listings — exactly the `SourceObservation` model in localUpdates.
- **Refresh:** monthly Overture release + daily Geofabrik → a scheduled WSL job on the Windows machine re-ingests, re-runs the 75-layer precompute, uploads Parquet/PMTiles/COGs to R2, bumps a `manifest.json` version the SPA reads.
- **Serving:** DuckDB on the API (ms for bbox + `ST_Within`) and/or DuckDB-Wasm/FlatGeobuf in the browser for pure Overture/OSM data. Listings go through the API only.
- **Category not in the precomputed set:** (1) map the request to Overture/OSM categories (the LLM interpreter already emits structured constraints); (2) fetch matching POIs for the metro from DuckDB (ms); (3) if ≤ ~20 POIs, fire parallel Valhalla isochrones and union; otherwise run a multi-source Dijkstra on the metro graph held in RAM on the API (csgraph, ~0.3–1 s) and return a transient uint8 layer on the shared grid; (4) if the same category is requested more than N times, persist it to R2 as a new layer. This keeps the fallback at seconds rather than minutes and never touches Overpass.

---

## 7. Reference architectures

| Project | What they precompute | Resolution / units | Engine | Serving | Lesson for us |
|---|---|---|---|---|---|
| **Conveyal Analysis** | Travel-time distributions from every grid origin over a departure window; accessibility at a percentile (default 50th) | Web Mercator grids: z9 ≈ 216 m, z10 ≈ 108 m, z11 ≈ 54 m at 45°; ≤ 5 M cells; one origin per worker task | R5 (RAPTOR for transit) | Cloud workers; GeoTIFF downloads | Use a Mercator-aligned grid so tiles are exact; think in percentiles for transit |
| **Walk Score** | Network distance to nearest amenity in 9 categories, polynomial decay (full ≤ 5 min, zero at 30), category weights 3/3/2/1, depth-of-choice for restaurants/coffee; pedestrian-friendliness from block length and intersection density | Grid points ~500 ft apart for rankings | Proprietary | API/website | A ready-made soft-scoring shape; store k-nearest bands if we want depth of choice |
| **TravelTime** | Proprietary multimodal engine; isochrones in 90–290 ms up to 3 h; unions/intersections of up to 10 searches per request; H3/geohash outputs | — | Own | Hosted API | Our query *is* their union/intersection primitive; their H3 endpoint suggests hex cells are a reasonable transport for results |
| **Mapnificent** | GTFS → protobuf of stations, lines, inter-stop times and headways per city; **browser** runs the station-graph search from the clicked point and draws walking circles | Stations, not grid | Custom JS | Static files | A fully client-side transit reachability model is possible when the network is small; headway-based, not timetable-exact |
| **Helsinki Travel Time Matrix 2023** | Full cell-to-cell matrix: 13,231 × 13,231 cells, walk/bike/PT/car, three time windows, door-to-door | 250 m YKR grid | r5py with a patched R5; local walking speeds, Strava cycling, floating-car speeds | CSV per destination (zstd) + GeoPackage | The gold standard for a *research* dataset; shows matrices are feasible for a metro at 250 m when the use is offline, not for a drive-time slider |
| **Close (Henry Spatial Analysis)** | Travel times from 7.9 M census blocks to 3.2 M destinations, walk/bike/transit, nationwide (launched April 2024) | Census blocks | *(unverified — pages could not be fetched)* | Interactive web map | A nationwide precomputed "minutes to nearest amenity" product exists and found a homebuyer audience; our wedge is the same idea with user-set anchors added |
| **Overture + DuckDB** | Monthly GeoParquet releases with bbox columns | — | DuckDB native/Wasm | S3 public bucket | The ingest path for places is a single SQL statement |
| **Placemark** (open source, MIT) | — | — | MapLibre GL JS client, routing via ORS/Geoapify/OSRM | Static-friendly | Confirms MapLibre + pluggable routers as the pragmatic client stack |

---

## 8. Candidate end-to-end architectures

### A. Static-first
Precomputed PMTiles/COG layers + places GeoParquet/FlatGeobuf on R2; SPA on Cloudflare Pages; all algebra in a Worker; a Cloudflare Worker proxy to the **public** FOSSGIS Valhalla (dev) or Mapbox (prod) for anchors.
- **Cost:** $0 F&F; $0–5 at 10k users while under Mapbox's 100k/month.
- **Effort:** medium-high front-end (Worker math, canvas layer, polygonization, DuckDB-Wasm); near-zero ops.
- **Pros:** nothing to keep alive; scales by adding files; works offline for layers.
- **Cons / impossible:** no custom categories on demand (no graph server); 60-minute isochrone cap (Mapbox) kills "45 min to RDU"; listings with licence restrictions cannot be served; public Valhalla is not a legitimate production dependency.

### B. Server-first
FastAPI + DuckDB + own metro graph in RAM + self-hosted Valhalla on one Hetzner CX33 (or Fly 4 GB); server computes everything, returns PNG masks + GeoJSON; React/MapLibre client is thin.
- **Cost:** $10–20/month at both scales (one box handles 10k users easily; HA would double it).
- **Effort:** lowest initially — it is the V1 shape with the CHCCS engine swapped in.
- **Pros:** one language, one deploy, easy custom categories and listings, consistent engine for layers and anchors.
- **Cons / impossible:** every slider move is a round trip; no static distribution; single point of failure; bigger metros mean bigger boxes.

### C. Hybrid (recommended)
A's static tier (layers + places on R2, Pages, Worker algebra) **plus** B's small always-on API (Hetzner CX33-class) running self-hosted Valhalla for NC and the Python graph service for anchors, custom categories, and listings. Precompute runs on the Windows machine and publishes artifacts.
- **Cost:** $7–10 F&F (or $0 with the public demo during development); $10–25 at 10k users.
- **Effort:** medium; the API is small because the hot path is static.
- **Pros:** instant interaction, cheap, no hosted-API caps, legitimate production dependency chain, graceful degradation (if the API is down, category constraints still work).
- **Cons / impossible:** two deploy targets; on-demand transit anchors still out of scope until a JVM router is worth hosting; a second metro means another precompute run (hours, not money) and ~100 MB more R2.

---

## 9. Risks and unknowns — spikes to run

| # | Spike | Method | Success criterion |
|---|---|---|---|
| 1 | **Triangle precompute benchmark** | Build walk/bike/drive graphs for the 4 counties from the Geofabrik NC PBF with pyrosm/osmium; port CHCCS snapping; compute 75 layers with `scipy.sparse.csgraph.dijkstra(min_only=True)`; write uint8 COG + PMTiles | End-to-end < 60 min on the Windows machine; peak RAM < 16 GB; all layers < 50 MB compressed; networkx vs csgraph timings recorded |
| 2 | **Accuracy vs Valhalla** | Sample 500 random (cell, nearest-POI) pairs per mode; compare own-graph minutes with Valhalla `route` durations (self-hosted NC) | Walk/bike median abs error < 15%, p90 < 30%; drive median < 20%, p90 < 35% after recalibrating speeds; else switch drive layers to Valhalla GeoTIFF grids |
| 3 | **Self-host Valhalla NC** | Build tiles under Docker Desktop/WSL2 (`.wslconfig memory=12GB`); serve on a 4 GB VPS (Hetzner CX23 or Fly 2 GB) | Build completes; serving RSS < 1.5 GB; 25-min drive isochrone p95 < 800 ms, 45-min < 2 s; GeoTIFF grid output verified and aligned to our grid |
| 4 | **Browser raster algebra** | Worker thresholding 6 layers over a metro viewport; MapLibre canvas source; d3-contour polygonization | Slider-to-repaint < 100 ms; first paint < 1.5 s on throttled 4G; polygon output topologically valid |
| 5 | **R2 delivery** | Upload PMTiles and COG versions of 10 layers; measure range-request counts and latency from NC and from Europe; simulate 10k-user month | Viewport load < 500 ms from US; monthly Class B ops < 10 M at simulated load; CORS/range work on both formats |
| 6 | **On-demand custom category** | Hold the metro graph in RAM in FastAPI; Overture category → POIs → multi-source Dijkstra → uint8 grid | p95 < 3 s walk, < 5 s drive on 2 vCPU; memory < 2 GB |
| 7 | **Transit precompute** | r5py with 7 Triangle GTFS feeds + OSM; 250 m cells → all POIs; 08:00–09:00 window, median | Completes overnight (< 12 h) with ≤ 12 GB heap; 20 OD pairs within ±5 min of GoTriangle's trip planner |
| 8 | **FOSSGIS terms** | Read the Nutzungsbedingungen in a browser (blocked for automated fetch) / email FOSSGIS | Written policy text confirming acceptable dev use and limits; otherwise treat the demo as dev-only at ≤ 1 req/s |
| 9 | **MapLibre `color-relief` trick** | Encode minutes as Terrarium elevation in a `raster-dem` PMTiles; style with a step expression to transparent above threshold | Single-layer threshold renders natively with no custom shader; if alpha is unsupported, document and fall back to canvas |
| 10 | **Overture coverage for the Triangle** | Count Overture vs OSM features per product category | ≥ 90% of OSM parks/groceries/schools matched or complemented; define per-category source preference |

---

## 10. Open questions

1. Peak or off-peak driving as the default for "20 minutes to the office"? (No traffic data in default OSM-based routers; Valhalla time-dependent speeds need traffic tiles we do not have.)
2. Walk-speed profile(s) to expose (adult 1.4 m/s default; optional slower profile) and whether bike uses elevation (Valhalla does if built with elevation; CHCCS does not).
3. Hard-only output, soft scores, or both? The raster design supports both; the UI decision drives the default.
4. How to represent area destinations (parks, lakes, campuses): boundary samples vs mapped entrances vs centroids.
5. Should drive layers be computed with Valhalla for consistency with anchor isochrones, accepting a slower batch job? (Decided by Spike 2.)
6. Square grid vs H3 for the *display/transport* of results — H3 r10 (0.015 km², 76 m edge) is a near-equivalent of 100 m cells and plays well with TravelTime/Uber-style tooling, but square rasters are what every tile/COG toolchain expects.
7. ODbL posture for OSM-derived rasters: are travel-time layers a "produced work" or a derivative database? Keep OSM-only rows and OSM-derived rasters in their own buckets until counsel answers.
8. Which metro is second, and does the precompute script need to be metro-agnostic from day one (yes, cheap to do now).
9. Where does the monthly rebuild run long-term — the Windows box via Task Scheduler/WSL, or a Hetzner box spun up for an hour (~$0.02)?
10. Do we ever need cell-to-cell matrices (H3 r8 drive matrix, ~119 MB) to make anchors zero-latency, or is a 0.5 s Valhalla call always good enough?

---

## 11. Sources (all accessed 2026-11-03)

**Public routing servers and hosted APIs**
- OSRM demo server policy — https://github.com/Project-OSRM/osrm-backend/wiki/Demo-server
- FOSSGIS routing demo about page — https://routing.openstreetmap.de/about.html
- Valhalla FOSSGIS demo app (title only; terms page blocked) — https://valhalla.openstreetmap.de/ ; https://www.fossgis.de/arbeitsgruppen/osm-server/nutzungsbedingungen/ *(not retrievable)*
- openrouteservice FAQ (quotas, reset rules) — https://giscience.github.io/openrouteservice/frequently-asked-questions ; plans page 404 — https://openrouteservice.org/plans/
- GraphHopper Directions API pricing — https://www.graphhopper.com/pricing/
- TravelTime pricing — https://traveltime.com/pricing ; usage limits — https://docs.traveltime.com/api/overview/usage-limits ; isochrones reference — https://docs.traveltime.com/api/reference/isochrones ; isochrone performance claims — https://traveltime.com/isochrones
- Mapbox pricing — https://www.mapbox.com/pricing ; Isochrone API docs — https://docs.mapbox.com/api/navigation/isochrone/
- Google Maps Platform pricing (Routes, Route Matrix, Distance Matrix legacy) — https://developers.google.com/maps/billing-and-pricing/pricing ; Isochrones API overview — https://developers.google.com/maps/documentation/isochrones/overview ; usage and billing (preview status) — https://developers.google.com/maps/documentation/isochrones/usage-and-billing
- HERE pricing (third-party summaries; HERE page did not render) — https://placematic.com/here-location-services/here-pricing/ ; https://apicostcalc.com/here.html *(unverified)*

**Self-hosting**
- Geofabrik North Carolina extract (410 MB, data to 2026-11-02) — https://download.geofabrik.de/north-america/us/north-carolina.html
- Valhalla default `service_limits` (build config script) — https://raw.githubusercontent.com/valhalla/valhalla/master/scripts/valhalla_build_config
- Valhalla isochrone API (grid-based, GeoTIFF output, 4 contours) — https://valhalla.github.io/valhalla/api/isochrone/
- Valhalla matrix API (costmatrix vs timedistancematrix, `matrix_locations`) — https://valhalla.github.io/valhalla/api/matrix/
- Valhalla build memory discussion #3288 — https://github.com/valhalla/valhalla/discussions/3288 ; planet build duration #3197 — https://github.com/valhalla/valhalla/discussions/3197 ; Mjolnir getting started — https://valhalla.github.io/valhalla/mjolnir/getting_started_guide/
- docker-valhalla (archived 2026-03-03, moved upstream) — https://github.com/nilsnolde/docker-valhalla
- OSRM command-line tools (`--max-table-size` 100, `--algorithm`, `--mmap`) — https://project-osrm.org/docs/v26.4.0/tools ; OSRM API (no isochrone service) — https://project-osrm.org/docs/v5.24.0/api/ ; OSRM memory rule of thumb — https://blog.afi.io/blog/hosting-the-osrm-api-on-amazon-ec2-running-osrm-backend-as-a-web-service/
- GraphHopper deployment guide (import memory) — https://raw.githubusercontent.com/graphhopper/graphhopper/master/docs/core/deploy.md
- openrouteservice system requirements — https://giscience.github.io/openrouteservice/run-instance/system-requirements
- r5py advanced use (JVM memory) — https://r5py.readthedocs.io/stable/user-guide/user-manual/advanced-use.html
- OpenTripPlanner 2 system requirements — https://docs.opentripplanner.org/en/latest/System-Requirements/ ; Basic tutorial (Portland heap) — https://docs.opentripplanner.org/en/latest/Basic-Tutorial/
- WSL2 `.wslconfig` defaults (memory 50%, processors, swap) — https://learn.microsoft.com/en-us/windows/wsl/wsl-config

**Hosting and storage pricing**
- Hetzner Cloud overview — https://www.hetzner.com/cloud/ ; plan prices via getdeploying — https://getdeploying.com/hetzner
- Fly.io pricing — https://docs.fly.io/about/pricing
- Railway pricing — https://railway.com/pricing
- Render free tier docs — https://render.com/docs/free
- Oracle Always Free A1 reduction (InfoQ, 2026-07) — https://www.infoq.com/news/2026/07/oracle-cloud-free-tier-limits/
- Cloudflare R2 pricing — https://developers.cloudflare.com/r2/pricing/ ; Workers pricing — https://developers.cloudflare.com/workers/platform/pricing/ ; Pages limits — https://developers.cloudflare.com/pages/platform/limits/
- GitHub Pages limits — https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits

**Formats, rendering, in-browser compute**
- PMTiles docs — https://docs.protomaps.com/pmtiles/ ; Protomaps deploy guide — https://docs.protomaps.com/deploy
- Cloud Optimized GeoTIFF — https://cogeo.org/
- maplibre-cog-protocol (EPSG:3857 requirement, colour functions) — https://github.com/geomatico/maplibre-cog-protocol
- MapLibre color-relief example — https://maplibre.org/maplibre-gl-js/docs/examples/add-a-color-relief-layer/ ; pixel-styling proposal #1490 (open) — https://github.com/maplibre/maplibre-style-spec/issues/1490 ; FR #7029 — https://github.com/maplibre/maplibre-gl-js/issues/7029
- FlatGeobuf — https://flatgeobuf.org/
- DuckDB-Wasm extensions (spatial available; HTTPS/CORS caveats) — https://duckdb.org/docs/2.0/clients/wasm/extensions.html
- rasterio.features (`shapes`, `rasterize`) — https://rasterio.readthedocs.io/en/stable/api/rasterio.features.html
- skimage.measure.find_contours (marching squares) — https://scikit-image.org/docs/stable/api/skimage.measure.html
- pgRouting `pgr_drivingDistance` (multiple roots, `equicost`) — https://docs.pgrouting.org/latest/en/pgr_drivingDistance.html
- H3 resolution table — https://h3geo.org/docs/core-library/restable/

**Places data**
- Overture places guide (88 M places, confidence, taxonomy, licences, quality caveats) — https://docs.overturemaps.org/guides/places/
- Overture DuckDB example (S3 path, bbox filter) — https://docs.overturemaps.org/getting-data/duckdb/
- Overture release calendar (monthly; next 2026-11-18) — https://docs.overturemaps.org/release-calendar/
- GoTriangle developer resources (GTFS for 7 agencies) — https://gotriangle.org/developer-resources

**Reference architectures**
- Conveyal methodology — https://docs.conveyal.com/analysis/methodology ; regional analysis — https://docs.conveyal.com/analysis/regional
- Walk Score methodology — https://www.walkscore.com/methodology.shtml
- Helsinki Region Travel Time Matrix 2023 — https://www.helsinki.fi/en/researchgroups/digital-geography-lab/helsinki-region-travel-time-matrix-2023 ; Scientific Data paper (paywall redirect) — https://www.nature.com/articles/s41597-024-03689-z
- Mapnificent generator — https://github.com/mapnificent/mapnificent_generator ; Mapnificent — https://github.com/mapnificent/mapnificent ; description of the client algorithm — https://trilliumtransit.com/2010/11/16/mapnificent-public-transport-travel-time-maps/
- Close (Henry Spatial Analysis): launch coverage — https://www.bloomberg.com/news/newsletters/2024-09-11/how-walkable-is-your-neighborhood-a-new-map-tool-offers-an-answer ; https://bungalower.com/2024/09/16/map-interactive-map-shows-neighborhood-walkability-across-the-country/ ; https://henryspatialanalysis.com/ *(technical stack unverified)*
- Placemark (open source) — https://github.com/placemark/placemark

**Geography**
- Wikipedia county pages (land area, 2025 population estimates): Wake — https://en.wikipedia.org/wiki/Wake_County,_North_Carolina ; Durham — https://en.wikipedia.org/wiki/Durham_County,_North_Carolina ; Orange — https://en.wikipedia.org/wiki/Orange_County,_North_Carolina ; Chatham — https://en.wikipedia.org/wiki/Chatham_County,_North_Carolina

**In-house**
- `docs/research/00-existing-assets-audit.md` (CHCCS grid engine, V1 Valhalla client, localUpdates DuckDB/Overture store) — this repository.
