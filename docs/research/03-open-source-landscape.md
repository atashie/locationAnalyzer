# 03 - Open-Source Landscape: Routing, Accessibility, Precompute/Serving, LLM-to-GIS, Geocoding/POI Tooling

**Date:** 2026-11-03
**Status:** Draft v1 (research survey; no code changes)
**Author:** research stream "open-source landscape" (Claude Code session)

## Scope and method

This document surveys open-source software we could adopt, borrow patterns from, or should avoid for the location-finder product (home-search wedge, Research Triangle NC first; later hotels and business site selection). Five groups were covered:

- **A.** Routing / isochrone engines
- **B.** Accessibility, 15-minute-city and "where should I live" projects
- **C.** Precompute, gridded travel-time storage and cheap browser serving
- **D.** LLM-to-GIS agents and geospatial MCP servers
- **E.** Geocoding and POI/OSM/GTFS data tooling

Method: web search for candidates, then primary-source verification of each repo via its GitHub README and the GitHub REST API (`stargazers_count`, `license.spdx_id`, `pushed_at`, `releases/latest`) on 2026-11-03, plus project docs pages. Star counts are rounded and dated 2026-11-03 unless stated. Anything not confirmed from a primary source is marked **(unverified)**. Hardware figures labelled "estimate" are our extrapolations, not published numbers. Note that some project README pages fetched during this survey summarised release years inconsistently; where that happened the GitHub API timestamp was used as authoritative.

In-house assets this survey is evaluated against (see `00-existing-assets-audit.md`): OSMnx/GeoPandas progressive polygon filtering, a Valhalla isochrone client, a gridded multi-source Dijkstra travel-time raster pipeline (100 m grid, snap to nearest OSM edge, speed model with intersection penalties), and a natural-language -> structured filter -> DuckDB spatial SQL agent over Overture Maps places.

---

## 1. Executive summary

1. **Valhalla is the right on-demand routing engine for us and we already have a client.** MIT, C++, 6.4k stars, v3.9.1 (2026-10-06), official `ghcr.io/valhalla/valhalla` images (the popular `docker-valhalla` wrapper was archived 2026-03 and folded upstream). It is the only mainstream engine with isochrones, matrix, multimodal transit (GTFS), time-of-day costing and a **GeoTIFF isochrone output** in one binary. The North Carolina Geofabrik extract is 430 MB (2026-11-03), so a state-level self-host fits a small VM.
2. **OSRM has no isochrone endpoint** (an AI-assisted proposal, issue #7751, opened 2026-10-21 and is still unmerged). It remains the fastest matrix engine, but for us it is a reference only.
3. **GraphHopper is the credible alternative** (Apache-2.0, `/isochrone`, `/spt`, GTFS public transit in OSS), but the matrix API is commercial-only and Docker images are community-maintained. **openrouteservice** has isochrones + matrix but is GPL-3.0 and heavier; its public API is a useful fallback, not a core dependency.
4. **For transit we do not need to self-host first.** MOTIS (MIT) powers Transitous, whose community feed list (`feeds/us-nc.json`) already includes GoTriangle, GoRaleigh, GoDurham, GoCary, Chapel Hill Transit and NCSU Wolfline. Transitous is **non-commercial only and capped around 720 requests/day**, so it is a prototyping path; MOTIS self-host or Valhalla multimodal is the production path.
5. **The "precompute a gridded travel-time layer" pattern is well established and our pipeline is in the mainstream.** Helsinki Travel Time Matrix (r5py, 13k cells), Snowflake's H3 matrix write-up (June 2026), Close/Henry Spatial (r5r, per-block), transport-maps (H3 + PMTiles binary arrays), SF commute map (baked static bundles). The recurring lesson: precision is bounded by cell size and build cost grows roughly quadratically with resolution; no one serves per-cell matrices live.
6. **Cheapest browser serving today is static files on object storage with range requests, no tile server.** PMTiles (raster or vector) on Cloudflare R2 (10 GB free, zero egress) or COGs rendered client-side via `maplibre-cog-protocol` / `cog-tiler-wasm`. TiTiler is the mature server option if we need dynamic colour ramps or non-Mercator sources.
7. **MapLibre GL JS should replace Leaflet for the map.** MapLibre (12k stars, v6.16.0 2026-10-25, BSD-3) supports `addProtocol` for `pmtiles://` and `cog://`, GPU rendering and vector tiles. Leaflet (45.8k) is alive but its last release is v1.9.4 (2023-05); raster overlays work via `georaster-layer-for-leaflet` but it is a dead end for our volume of cells.
8. **DuckDB spatial is production-grade for our use** (R-tree index, GeoParquet, `ST_ReadOSM`, and a browser build: DuckDB-Wasm ships spatial, httpfs, parquet and community H3). This validates the in-house DuckDB agent and opens a "query in the browser" option for POI filters.
9. **For the NL layer, structured tool-calling beats code generation.** Code-generating agents (LLM-Geo, IntelliGeo) are research prototypes with GPL licences and no verifiability. The maturing pattern is a registry of typed tools with safety metadata (opengeos/GeoAgent, 530 stars, MIT; iamtekson GeoAgent for QGIS) or NL -> intermediate representation -> SQL (geointent, very early). Our structured-filter -> SQL agent is the right shape; what to add is schema-constrained outputs, a dry-run validator and user-visible provenance.
10. **Geospatial MCP servers are numerous but thin** (most OSM servers have <50 stars, wrap Nominatim/Overpass/OSRM, and enforce 1 req/s public-API etiquette). Google's managed "Maps Experience agent tools" MCP is restricted GA, 10k free requests/month, and has **no isochrone or matrix**. Useful as reference for tool-shape; we should expose our own tools, not depend on these.
11. **Do not self-host a geocoder yet.** Nominatim (planet: 128 GB RAM, 1 TB) and Photon (planet ~95 GB index, 64 GB RAM recommended) are over-scoped; Pelias is the easiest metro-scale option (Portland example: 8 GB RAM, <1 h) but has no Windows support. Keep the Nominatim public API for dev; revisit Pelias when request volume justifies it.
12. **Dead or stale, do not build on:** `osrm-isochrone` (archived 2024-11), `node-isochrone` (archived 2026-09), `isochrone` npm (8 years), Conveyal `analysis-backend` (archived 2020), Amsterdam MapItOut (archived 2021), `tracc` (2020), `spatial_access` (2022), Mapumental (gone). Mapnificent (last push 2024-04) and time2reach (2024-03) are useful references only.

---

## 2. Per-group tables

Verdict scale: **adopt** (use as-is), **consider** (viable alternative or later phase), **reference** (borrow pattern/data, do not depend), **reject** (do not use).

### Group A - Routing / isochrone engines

| Project | URL | License | Stars / activity | What it does | Fit for us | Verdict |
|---|---|---|---|---|---|---|
| Valhalla | github.com/valhalla/valhalla | MIT | 6.4k; pushed 2026-11-03; v3.9.1 2026-10-06 | Tile-based multimodal router: route, isochrone (time or distance contours, max 4 by default, `reverse`, `date_time`, GeoJSON or GeoTIFF), matrix (`sources_to_targets`, no multimodal), map-matching, GTFS transit, elevation. Official ghcr images incl. `valhalla-scripted` (env-var tile builds, `/gtfs_feeds` mount). | We already have a client; one engine covers car/bike/walk/transit, isochrone and matrix; GeoTIFF output matches our raster pipeline. | **adopt** - lowest-risk single engine; self-host NC extract. |
| OSRM | github.com/Project-OSRM/osrm-backend | BSD-2-Clause | 8.2k; pushed 2026-11-02; v26.11.0 2026-11-01 (date-based versions) | CH/MLD car/bike/foot routing; Table (matrix), Match, Trip, Tile services. No isochrone (issue #7751, proposal opened 2026-10-21, unmerged). Planet car profile ~123 GiB RAM at runtime. | Fast matrices but one profile per instance and no isochrone, no transit, no time-dependence. | **reference** - only if a many-to-many matrix bottleneck appears. |
| GraphHopper | github.com/graphhopper/graphhopper | Apache-2.0 | 6.8k; pushed 2026-11-02; 11.1 2025-09-29 | Java router; `/isochrone` (time_limit, buckets, reverse_flow, `pt` profile), `/spt` shortest-path tree, GTFS public transit (trip-based since 11.0). Matrix API is commercial only. Docker via community `israelhikingmap/graphhopper`. Planet import ~60 GB RAM. | Solid alternative with permissive licence; SPT endpoint is handy for grid precompute. | **consider** - fallback if Valhalla transit quality disappoints. |
| openrouteservice | github.com/GIScience/openrouteservice | GPL-3.0 (API lib LGPL-3.0) | 2.0k; pushed 2026-11-03; v10.1.0 2026-10-14 | Java (GraphHopper fork) with directions, isochrones, matrix, snapping, export; docker compose; RAM guidance: Baden-Wurttemberg 2-4 GB, Germany ~8 GB, planet 100-105 GB. Hosted public API with free tier (quotas page returned 404 during survey - **unverified**). | Feature-complete but GPL and heavier JVM; public API is a handy second source for cross-checking isochrones. | **consider** (public API as fallback) / **reject** for self-host. |
| R5 / r5py / r5r | github.com/conveyal/r5, github.com/r5py/r5py | R5 MIT; r5py dual GPL-3.0-or-later / MIT | R5 405, pushed 2026-10-16; r5py 195, v1.1.7 2026-06-29; r5r on CRAN 2026-05 | Realistic multimodal (transit-first) travel-time matrices and accessibility; `TravelTimeMatrixComputer`; Java 21+; conda recommended on Windows. Conveyal states no API stability for third parties. | Best open tool for **batch** transit travel-time matrices (used by Helsinki TTM and Close). Not a live API. | **adopt** for offline transit grid precompute; **reject** as runtime service. |
| OpenTripPlanner 2 | github.com/opentripplanner/OpenTripPlanner | LGPL-3.0 | 2.8k; pushed 2026-11-03; v2.10.0 2026-09-09 | Transit trip planner; sandbox Travel Time API: `/otp/traveltime/isochrone` and `/surface` (GeoTIFF int32 seconds). Java 25. | Heavy for our need; isochrone API is a sandbox feature. | **reference** - GeoTIFF surface pattern. |
| MOTIS | github.com/motis-project/motis | MIT | 622; pushed 2026-11-03 | C++ intermodal router (GTFS, GTFS-RT, OSM street routing, GBFS); REST + OpenAPI; `/plan`, `/one-to-many`, `/one-to-all`; low memory; powers Transitous. | Lightest path to transit isochrones; `/one-to-all` is exactly a grid precompute primitive. | **consider** - strong candidate for transit; validate NC build. |
| Transitous (service) | transitous.org / github.com/public-transport/transitous | service; MOTIS MIT | community-run | Free public MOTIS instance; `feeds/us-nc.json` lists GoTriangle, GoRaleigh, GoDurham, GoCary, Chapel Hill Transit, NCSU Wolfline (Duke skipped: auth required). Policy: non-commercial, open-source clients, >720 req/day requires coordination, User-Agent required. | Zero-cost transit routing for prototypes and ground truth; not usable in a commercial product. | **reference / prototype only**. |
| Headway | github.com/headwaymaps/headway | Apache-2.0 | 3.0k; pushed 2026-11-02 | Docker-compose/k8s "maps in a box": Valhalla + Pelias + tile server (+ OTP, transit WIP) for 200+ cities or custom extract. Build >= 8 GB RAM, run ~4 GB for a mid-size metro, 50-100 GB disk during build. | Proof that a full metro stack runs on a 4-8 GB box; good reference for compose wiring. | **reference** - copy the compose patterns, not the whole stack. |
| pgRouting | github.com/pgRouting/pgrouting | GPL-2.0 + BSL | 1.4k; pushed 2026-11-02; v4.0.2 2026-09-05 | PostGIS routing (`pgr_drivingDistance`, all-pairs, Dijkstra variants). | Requires PostGIS; slower than C++ engines; no isochrone polygons without alpha-shape step. | **reject** for our stack. |
| Pandana | github.com/UDST/pandana | AGPL-3.0 | 432; pushed 2026-10-01; v0.8 2026-08-24 (LTS/compat mode) | Contraction-hierarchy network aggregation; nearest-POI-per-node queries; isochrone accessibility (v0.7). | Exactly our "nearest POI per cell" primitive, but AGPL and in maintenance mode; Python 3.10-3.14. | **reference** - algorithm pattern; licence blocks adoption. |
| UrbanAccess | github.com/UDST/urbanaccess | AGPL-3.0 | 267; pushed 2026-10-10 | Builds GTFS + OSM pedestrian graphs for Pandana. | Same AGPL constraint. | **reference**. |
| Conveyal Analysis | github.com/conveyal/analysis-ui, analysis-backend | MIT | ui 7 stars, pushed 2022-01; backend archived 2020-11 | Scenario-planning UI over R5. | Dead as a product; R5 lives on. | **reject**. |
| o-isochrone | github.com/Martenz/o-isochrone | MIT | 0; created 2026-09-22 | OSMnx + NetworkX isochrones with buffered/concave/H3 output layers; FastAPI + MapLibre demo. | Near-duplicate of our OSMnx approach; nice H3 layer option. | **reference**. |
| osrm-isochrone (Mapbox) | github.com/mapbox/osrm-isochrone | MIT | 131; archived 2024-11-21 | Sampled-points isochrones on OSRM. | Dead. | **reject**. |
| node-isochrone / `isochrone` npm | github.com/stepankuzmin/node-isochrone | MIT | 30; archived 2026-09-13; npm last publish 8 yrs | OSRM table + concaveman. | Dead. | **reject**. |
| mapbox-isochrone | github.com/mapbox/mapbox-isochrone | MIT | 119; pushed 2026-03 | CONREC contours over Mapbox Matrix API (commercial). | Pattern for matrix -> contour; vendor lock-in. | **reference**. |
| TravelTime Python SDK | github.com/traveltime-dev/traveltime-python-sdk | MIT (SDK; API commercial) | 25; pushed 2026-09 | `time_map`, `time_filter_fast`, H3 and geohash endpoints. | Shows the commercial state of the art for H3 "fast" reachability; paid. | **reference**. |
| Google Maps Experience agent tools (MCP) | developers.google.com/maps/ai/grounding-lite | commercial | Restricted GA | Managed MCP: search places, weather, compute routes, resolve names/URLs. $7/1k after 10k free (Essentials); 300 QPM. No isochrone, no matrix, no step directions. | Cheap grounding for place names; not a routing substitute. | **consider** for place resolution only. |

### Group B - Accessibility / 15-minute city / "where should I live"

| Project | URL | License | Stars / activity | What it does | Fit for us | Verdict |
|---|---|---|---|---|---|---|
| Close (close.city) + `city_walkability` | github.com/henryspatialanalysis/city_walkability | MIT (tutorial); Close itself has no public source found | 29; pushed 2023-08 | Tutorial recreating a "15-minute city" map: census blocks as origins, OSM amenities, **r5r** (replaced openrouteservice; ~100x faster, slope-aware), embeddable web map. Close is the productised multimodal "every block" map. | Direct precedent for block/cell-level nearest-amenity travel times; R not Python. | **reference** - method; Close is closed. |
| Mapnificent | github.com/mapnificent/mapnificent | licence file present, SPDX NOASSERTION | 407; pushed 2024-04 | GTFS -> protobuf (Go generator), in-browser transit reachability; Jekyll static site. | Shows fully client-side transit reachability is feasible; stale. | **reference**. |
| time2reach | github.com/econaxis/time2reach | none declared | 196; pushed 2024-03 | Rust GTFS BFS/RAPTOR-like engine, React + Mapbox GL colouring road segments by travel time; built for Toronto apartment hunting (Show HN 2023). | Confirms house-hunting demand and UX (double-click origin, coloured segments); no licence. | **reference**. |
| sf-commute-isochrone | github.com/AkshayM21/sf-commute-isochrone | MIT | 1; created 2026-08 | Reverse range-RAPTOR transit + hill-aware OSM walking graph; "baked" static bundles served from a static host. | Modern example of precompute-and-bake for one metro; small. | **reference**. |
| uk-isochrones-map | github.com/pbarber/uk-isochrones-map | Unlicense | 4; pushed 2024-01 | Pre-generated per-area isochrone GeoJSON on S3, GitHub Pages viewer. | Minimal static-serving pattern. | **reference**. |
| MapItOut (Amsterdam) | github.com/Amsterdam/mapitout-frontend, -backend | MPL-2.0 / LGPL-3.0 | archived 2021-04 | Vue front end over a Lambda proxy to the commercial TravelTime API; housing-search use case. | Dead; proves municipal demand. | **reject**. |
| A/B Street (15-minute tool) | github.com/a-b-street/abstreet | Apache-2.0 | 8.2k; pushed 2025-09 | Rust simulation; 15-minute neighbourhood explorer and game. | Different product; walking-only. | **reference**. |
| Zverik/15minute | github.com/Zverik/15minute | ISC | 18; pushed 2025-11 | GraphHopper isochrones per amenity, colours buildings reachable/unreachable. | Simple, readable pipeline. | **reference**. |
| CityAccessMap | cityaccessmap.com | described as open source; repo not found **(unverified)** | - | Walking accessibility for ~3,500 cities from OSM + GHSL; Svelte + Mapbox + D3. | Global scale, coarse. | **reference**. |
| pysal/access | github.com/pysal/access | BSD-3-Clause | 31; pushed 2026-10 | 2SFCA, gravity, RAAM access measures from travel-time matrices. | Useful if we score "access to category" beyond nearest. | **consider** (scoring). |
| tracc | github.com/jamaps/tracc | MIT | 20; pushed 2020-09 | Potential/passive accessibility from precomputed matrices. | Dead. | **reject**. |
| spatial_access (GeoDaCenter) | github.com/GeoDaCenter/spatial_access | none | 40; pushed 2022-01 | OSM many-to-many matrices + access models. | Dead. | **reject**. |
| UrbanPy | github.com/EL-BID/urbanpy | GPL-3.0 | 132; pushed 2026-08; v0.2.2 2024-07 | H3 hex grid + OSRM-in-Docker travel times to POIs; Nominatim/Overpass/HDX inputs; Windows "coming soon". | Same architecture as ours at coarser scale; GPL. | **reference**. |
| AccessMod 5 | github.com/unige-geohealth/accessmod | LGPL-3.0 | 49; pushed 2026-09 | R/Shiny + GRASS raster friction-surface cost distance (health). | Raster-friction approach; our Dijkstra pipeline is network-based, better for cities. | **reference**. |
| Momepy | github.com/pysal/momepy | BSD-3-Clause | 638; pushed 2026-10 | Urban morphology metrics. | Not accessibility. | **reject** (out of scope). |
| Helsinki Travel Time Matrices | github.com/DigitalGeographyLab/Helsinki-Travel-Time-Matrices | GPL-3.0 | 4; pushed 2024-01 | r5py pipeline: 13,132 YKR grid cells (250 m), walk/bike/PT/car, dockerised; run on a 64-core VM with 200 GB swap; Sci Data 2024 paper. | Gold standard for a published metro matrix; shows compute scale for all-pairs. | **reference**. |
| TTM visualisation preprocessing | github.com/DigitalGeographyLab/travel-time-matrix-visualisation-preprocessing | not stated | 0 | Per-cell isochrone GeoJSON (<=15/15-30/30-60 min), simplified and gzipped: ~2.5 GB per matrix. | Shows cost of per-origin polygons vs rasters. | **reference**. |
| transport-maps | github.com/hletrd/transport-maps | MIT (code) | 2; created 2026-09 | Global door-to-door times per H3 res 6/7 cell; Dijkstra; **PMTiles with binary arrays per origin**, MapLibre 6.11 front end. | Cheapest known serving design for many-origin times. | **reference** - PMTiles binary payload idea. |
| Snowflake H3 travel-time matrix (blog) | snowflake.com/.../h3-travel-time-matrix | article (2026-06-25) | - | H3 res 6 Germany HGV: 121M rows; precompute once, SQL lookups at ~400 QPS; road-aware tessellation halves cells; precision bounded by hex size, cost ~quadratic in resolution. | Confirms our tiering logic and resolution trade-off. | **reference**. |

### Group C - Precompute / gridded travel-time / serving

| Project | URL | License | Stars / activity | What it does | Fit for us | Verdict |
|---|---|---|---|---|---|---|
| PMTiles | github.com/protomaps/PMTiles | BSD-3 (impl), CC0 (spec) | 3.1k; pushed 2026-09 | Single-file Z/X/Y archive (vector **or raster**) read by HTTP range requests from S3/R2; JS lib for MapLibre and Leaflet; `go-pmtiles` CLI; Lambda/Workers examples. | Serve precomputed travel-time rasters or H3 vector tiles with zero servers. | **adopt**. |
| Protomaps basemaps | github.com/protomaps/basemaps | NOASSERTION (BSD-3 per repo) | 770; pushed 2026-09 | PMTiles basemap generation + styles. | Free/cheap basemap instead of Mapbox/Google tiles. | **consider**. |
| Cloudflare R2 (hosting) | developers.cloudflare.com/r2/pricing | service | - | 10 GB storage, 1M Class A, 10M Class B free/month; zero egress; $0.015/GB-month after. | Natural home for PMTiles/COG/GeoParquet. | **adopt**. |
| TiTiler | github.com/developmentseed/titiler | MIT | 1.2k; pushed 2026-11-02; v2.4.0 2026-09-21 | FastAPI dynamic COG tiler; Lambda/ECS/K8s recipes; colormaps, rescale. | Server-side option if we need dynamic styling or non-3857 COGs; adds a service to run. | **consider**. |
| maplibre-cog-protocol | github.com/geomatico/maplibre-cog-protocol | MIT | 163; pushed 2026-09 | `cog://` protocol for MapLibre: range-reads and decodes COG tiles in the browser; EPSG:3857 only; ColorBrewer/CARTO ramps; custom per-pixel functions. | Serverless raster overlay of travel-time COGs; our rasters must be reprojected to 3857. | **adopt** (pilot). |
| cog-tiler-wasm | github.com/opengeos/cog-tiler-wasm | MIT | 13; created 2026-06 | Rust/WASM TiTiler-style tiling in-browser (whitebox-wasm); EPSG:3857 only; LERC/ZSTD fall back to geotiff.js. | Alternative to the above; very new. | **consider**. |
| georaster-layer-for-leaflet | github.com/GeoTIFF/georaster-layer-for-leaflet | Apache-2.0 | 352; pushed 2025-09 | GeoTIFF/COG rendering in Leaflet via web workers; no WebGL. | Keeps Leaflet alive short term. | **consider** (interim only). |
| DuckDB spatial | github.com/duckdb/duckdb-spatial | MIT | 721; pushed 2026-11-02 | GEOMETRY type, R-tree index (used by ST_Intersects/Within/Contains... with a constant argument), GDAL vector I/O (`st_read`, no rasters), GeoParquet, `ST_ReadOSM`. DuckDB-Wasm ships spatial, httpfs, parquet; H3 via community. | Already our query engine; browser build enables client-side POI filtering. | **adopt**. |
| h3-duckdb | github.com/isaacbrodsky/h3-duckdb | Apache-2.0 | 254; pushed 2026-10 | H3 functions in DuckDB (community extension). | H3 keys for travel-time tables. | **adopt** if we go H3. |
| H3 | github.com/uber/h3 | Apache-2.0 | 6.7k; pushed 2026-11-01 | Hex grid; res 9 = 0.105 km2 (~201 m edge), res 10 = 0.015 km2 (~76 m edge). | Res 10 approximates our 100 m grid; res 9 for tier-2 metros. | **consider**. |
| FlatGeobuf | github.com/flatgeobuf/flatgeobuf | BSD-2-Clause | 827; pushed 2026-11-02 | Streaming vector format with packed Hilbert R-tree; HTTP range spatial filter; MapLibre/Leaflet/OpenLayers examples. | Good for serving POI points or cell polygons by bbox without a server. | **consider**. |
| GeoParquet | github.com/opengeospatial/geoparquet | Apache-2.0 | 1.1k; pushed 2026-11-03; v2.0.0 (OGC approval pending) | Parquet geospatial logical types; Overture and Foursquare distribute in it. | Storage format for cells, POIs, matrices. | **adopt**. |
| MapLibre GL JS | github.com/maplibre/maplibre-gl-js | BSD-3-Clause | 12.1k; v6.16.0 2026-10-25 | WebGL vector/raster map; `addProtocol`; raster-dem; MLT tiles. | Target map library. | **adopt** (migrate). |
| Leaflet | github.com/Leaflet/Leaflet | BSD-2-Clause | 45.8k; pushed 2026-11-03; latest release v1.9.4 2023-05 | DOM/canvas map; huge plugin ecosystem. Leaflet 2 in development **(unverified)**. | Current front end; fine for GeoJSON polygons, weak for large rasters/cell sets. | **consider** (keep until migration). |
| deck.gl | github.com/visgl/deck.gl | MIT | 14.7k; pushed 2026-11-03 | WebGL2/WebGPU layers (H3HexagonLayer, BitmapLayer); interleaves with MapLibre. | Only if we render hundreds of thousands of cells client-side. | **consider** (later). |
| kepler.gl | github.com/keplergl/kepler.gl | MIT | 12.1k; active | Redux/React analytics map app on deck.gl. | Too opinionated to embed. | **reference**. |
| lonboard | github.com/developmentseed/lonboard | MIT | 975; pushed 2026-11-02 | GeoArrow + deck.gl in Jupyter. | Internal QA of grids, not product. | **consider** (dev tooling). |
| tippecanoe | github.com/felt/tippecanoe | BSD-2-Clause | 1.6k; pushed 2026-09 | GeoJSON/FlatGeobuf -> vector tiles (MBTiles/PMTiles). | Build H3/cell vector tiles. | **adopt** if vector cells. |
| martin | github.com/maplibre/martin | Apache-2.0 | 4.0k; pushed 2026-11-03 | Rust PostGIS/MBTiles/PMTiles tile server. | Only if we outgrow static PMTiles. | **consider**. |

### Group D - LLM-to-GIS agents and geospatial MCP

| Project | URL | License | Stars / activity | What it does | Structured vs code-gen | Verdict |
|---|---|---|---|---|---|---|
| LLM-Geo | github.com/gladcolor/LLM-Geo | GPL-3.0 | 461; pushed 2026-10-18 | "Autonomous GIS": solution graph -> **generates full Python**, review/debug loop; o3-mini default. | Code generation; not verifiable; GPL. | **reference** (solution-graph idea). |
| opengeos/GeoAgent | github.com/opengeos/GeoAgent | MIT | 530; created 2026-02, pushed 2026-11-01 | Agent layer on Strands Agents; `@geo_tool` decorator, `GeoToolRegistry` with `requires_confirmation`/`destructive`/`long_running` flags; adapters for leafmap, anymap, QGIS; many model providers incl. Anthropic. | **Structured tool calling** with safety metadata. | **adopt pattern** (do not import whole). |
| GeoAgent (QGIS plugin) | github.com/iamtekson/GeoAgent | MIT | 48; created 2025-12, pushed 2026-10 | LangGraph state machine builds dependency-ordered task queue; discovers QGIS Processing registry; emits parameter-filled algorithm calls; Ollama/OpenAI/Gemini/Claude. | Hybrid: structured calls into a registry. | **reference**. |
| IntelliGeo | github.com/MahdiFarnaghi/intelli_geo | Apache-2.0 | 63; pushed 2025-06; v0.1.0 | QGIS chat producing PyQGIS scripts or graphical models; OpenAI/Cohere. | Code generation. | **reject**. |
| qgis-mcp (nkarasiak) | github.com/nkarasiak/qgis-mcp | GPL-2.0 plugin / MIT server | 409; created 2026-03, pushed 2026-10 | 125 MCP tools incl. processing algorithms and `execute_code`. | Mixed; desktop-only. | **reference**. |
| GeoAgent (IJGIS 2026, hierarchical multi-agent) | tandfonline.com/doi/10.1080/13658816.2026.2624784 | paper | - | Planning/execution/review layers; 94.6% success on 147 spatial tasks (GPT-4o). Repo not confirmed **(unverified)**. | Code/tool hybrid. | **reference**. |
| MapAgent | github.com/hasebul/mapagent | none declared | 19; pushed 2026-01 | Hierarchical agents over Google Maps API; EACL 2026. | Structured modules; vendor API. | **reference**. |
| awesome-agentic-AI-for-Geospatial-Data | github.com/mohammadhashemii/awesome-agentic-AI-for-Geospatial-Data | none | 42; pushed 2026-08 | Curated papers/repos; notes a 2025 "GeoJSON Agents: function calling vs code generation" comparison. | Survey. | **reference**. |
| geointent | github.com/FultonGeo/geointent | not stated | 0; 4 commits | NL -> intermediate spatial representation -> PostGIS / GeoPandas / DuckDB SQL; Claude; mock LLM for tests. | **Structured IR then compile** - same shape as our agent. | **reference** (very early). |
| geoask | github.com/Drusinek1/geoask | - | 404 at fetch **(unverified)** | Claude tool-use writing read-only DuckDB spatial SQL with shown work. | Structured. | n/a. |
| GeoSQL-7B, Llama-3.2-3B Spatial SQL | huggingface.co/SongY123/GeoSQL-7B | model weights | - | Fine-tunes for PostGIS text-to-SQL. | Could lower cost of SQL step later. | **reference**. |
| cyanheads/openstreetmap-mcp-server | github.com/cyanheads/openstreetmap-mcp-server | Apache-2.0 | 9; pushed 2026-10 | Nominatim + Overpass tools; stdio + streamable HTTP; paces Nominatim at ~1 req/s. | Clean MCP scaffolding. | **reference**. |
| NERVsystems/osmmcp | github.com/NERVsystems/osmmcp | MIT | 30; pushed 2026-10 | Go; 25 tools: geocode, OSRM routes, nearby places, "analyze_neighborhood", commute analysis. | Closest to our domain vocabulary. | **reference**. |
| ni-c/osm-mcp | github.com/ni-c/osm-mcp | MIT | 5; created 2026-08 | OSRM + Valhalla isochrones + optional ORS; Overpass POIs; rate-limited. | Shows "natural language -> isochrone" via MCP. | **reference**. |
| GRABOSM/osm-mcp | github.com/GRABOSM/osm-mcp | MIT | 6; pushed 2026-01 | 30 tools incl. `calculate_isochrone`, OSMOSE QA. | Thin. | **reference**. |
| overture-maps-mcp | github.com/koizumikento/overture-maps-mcp | MIT | 0; created 2026-10 | Read-only DuckDB+httpfs over Overture STAC: bbox/radius/polygon search, nearest, spatial join, GERS lookup. | Validates our Overture-in-DuckDB design. | **reference**. |
| mcp-server-motherduck | github.com/motherduckdb/mcp-server-motherduck | MIT | 539; pushed 2026-10-30 | `execute_query` etc. over local DuckDB or MotherDuck; read-only mode. | Could expose our DuckDB to Claude Code for internal analysis. | **consider** (dev tooling). |
| Google Maps Experience agent tools | developers.google.com/maps/ai/grounding-lite | commercial | Restricted GA | See Group A. | Structured tools; no isochrone/matrix. | **consider** (place resolution). |
| Sparkgeo "77+ geospatial MCP servers" | sparkgeo.com/blog/geospatial-mcp-servers-mapped-and-categorized | article (403 at fetch) | - | Categorised list incl. MCP-Geo, mcp-nominatim. | Survey. | **reference (unverified)**. |

### Group E - Geocoding and POI/OSM/GTFS tooling

| Project | URL | License | Stars / activity | What it does | Fit for us | Verdict |
|---|---|---|---|---|---|---|
| Nominatim | github.com/osm-search/Nominatim | GPL-3.0 | 4.5k; v5.3.3 2026-10-14 | OSM geocoder; planet: >=128 GB RAM, 1 TB disk, ~2.5 days import; min 2 GB; community Docker. Public API has strict usage policy. | Public API for dev/low volume; state-level self-host feasible (estimate: a few hours, 8-16 GB) but unnecessary now. | **consider** (public API now). |
| Photon | github.com/komoot/photon | Apache-2.0 | 3.2k; 1.3.0 2026-08-07 | OpenSearch-based geocoder; weekly planet dumps (~95 GB, 2026) from GraphHopper; 64 GB RAM recommended for planet; Java 21+. | Over-scoped unless we import our own Nominatim subset. | **reject** (for now). |
| Pelias | github.com/pelias/pelias, pelias/docker | MIT | 3.6k; docker 469 | Elasticsearch geocoder with OSM/OpenAddresses/WOF importers; Portland metro build >=8 GB RAM in <1 h; **Windows not supported**. | Best metro-scale self-host when volume justifies; run in WSL2/Linux. | **consider** (phase 2). |
| overturemaps-py | github.com/OvertureMaps/overturemaps-py | MIT | 280; v1.0.2 2026-08-25 | CLI/API: bbox download by theme/type to GeoParquet/GeoJSON; release listing; GERS lookup. | Already our POI source. | **adopt**. |
| QuackOSM | github.com/kraina-ai/quackosm | Apache-2.0 | 380; 0.20.0 2026-11-02 | DuckDB `ST_ReadOSM` PBF -> GeoParquet; tag and geometry filters; auto-download; ~10x disk overhead; Python >= 3.10. | Replace Overpass calls in `location_analyzer.py` with local PBF -> GeoParquet. | **adopt**. |
| pyrosm | github.com/pyrosm/pyrosm | BSD-3-Clause | 441; pushed 2026-11-02 | PBF -> GeoDataFrame (networks, POIs, buildings); out-of-core streaming; wheels for Windows/3.11-3.15. | Alternative to QuackOSM; feeds OSMnx graphs offline. | **consider**. |
| OSMnx | github.com/gboeing/osmnx | MIT | 5.9k; pushed 2026-07 | Network download/model via Overpass. | Keep for graph building; move POI fetch off Overpass. | **adopt** (existing). |
| osm2pgsql | github.com/osm2pgsql-dev/osm2pgsql | GPL-2.0 | 1.7k; 2.3.1 2026-07-05 | PBF -> PostGIS (flex Lua); Windows binaries. | Only with a PostGIS tier. | **reference**. |
| osmium-tool | github.com/osmcode/osmium-tool | GPL-3.0 | 713; v1.19.0 2026-01-18 | `extract`, `tags-filter`, `merge` for PBFs; Windows via vcpkg. | Clip NC PBF to the Triangle before Valhalla/QuackOSM. | **adopt** (CLI utility). |
| Foursquare OS Places | docs.foursquare.com/data-products/docs/access-fsq-os-places | Apache-2.0 | 104M POIs; ~10.6 GB Parquet (2024 release); now Iceberg "Places Portal", Hugging Face mirror, PMTiles on S3 | Global POIs with categories, `date_refreshed`, `date_closed`. | Second POI source to cross-validate Overture; Apache-2.0 is friendlier than ODbL for commercial use. | **consider**. |
| gtfs_kit | github.com/mrcagney/gtfs_kit (moved to codeberg.org/araichev/gtfs_kit) | MIT | 123 | In-memory GTFS analysis (pandas/GeoPandas). | Stop/route extraction for "near transit" criteria. | **consider**. |
| Mobility Database catalogs | github.com/MobilityData/mobility-database-catalogs | Apache-2.0 / CC0 metadata | 354; pushed 2026-10 | `feeds_v2.csv` and JSON of GTFS feeds; filter by subdivision. | Discover Triangle feeds (Transitous `us-nc.json` already enumerates them). | **adopt**. |

---

## 3. Detailed notes on the top candidates

### 3.1 Valhalla (adopt)

**What we would use:** the official `ghcr.io/valhalla/valhalla-scripted` image with `tile_urls` pointing at the Geofabrik North Carolina PBF (430 MB, 2026-11-03) or an `osmium extract` of the Triangle; endpoints `/isochrone` (auto, bicycle, pedestrian, multimodal; `contours` by time or distance; `polygons=true`; `reverse=true` for "which places can reach X"; `format=geotiff` for raster grids), `/sources_to_targets` for on-demand many-to-many against user-specified places, and optionally `/gtfs_feeds` for transit.
**Integration effort:** low; `backend/app/services/valhalla.py` already exists. Main change is pointing `VALHALLA_URL` at our own container instead of the FOSSGIS demo server, which is explicitly a demo and not for production load.
**Gotchas:** tile build is Linux-container only (Windows dev via Docker Desktop/WSL2); the matrix endpoint does not support multimodal costing; isochrones default to max 4 contours; time-dependent auto costing needs `date_time` and benefits from traffic data we do not have; `docker-valhalla` (318 stars) is archived - follow upstream docs.
**Hosting:** tile-based design keeps RAM moderate; published figures are 16 GB for Europe, 32 GB planet. For NC we estimate 2-4 GB RAM at runtime and roughly 1-3 GB of tiles (estimate; measure in a spike). That fits one small VM or a Railway/Fly container with a persistent volume.

### 3.2 MOTIS / Transitous (consider for transit)

**What we would use:** MOTIS `/one-to-many` and `/one-to-all` for transit travel-time grids, `/plan` for user-facing checks; Triangle GTFS feeds as enumerated in Transitous `feeds/us-nc.json` (GoTriangle, GoRaleigh, GoDurham, GoCary, Chapel Hill Transit, NCSU Wolfline; Duke requires auth).
**Integration effort:** medium; new client, new container; MOTIS is C++ with a Dockerfile and OpenAPI spec, low memory by design.
**Gotchas:** Transitous API is non-commercial and ~720 req/day; useful only for prototyping and validation. Documentation is thinner than Valhalla's. We need to confirm MOTIS isochrone-style polygon output (it returns one-to-many times; polygons would be our job - which suits a grid pipeline anyway).

### 3.3 GraphHopper (consider)

Apache-2.0 Java engine with `/isochrone` (buckets, `reverse_flow`, `pt` profile) and `/spt` (shortest-path tree as points, ideal for sampling to a grid). No OSS matrix API. Memory: planet import ~60 GB, so a state is small. Use if Valhalla's transit or isochrone shape quality is unsatisfactory, or to cross-check. Docker is community-maintained (`israelhikingmap/graphhopper`).

### 3.4 r5py / R5 (adopt for offline transit matrices)

Best-in-class realistic transit travel times (multiple departure times, percentiles). Used by Helsinki TTM and Henry Spatial's Close method (r5r). Requires JDK 21+; conda is the recommended Windows path. R5 is MIT but Conveyal offers no API stability. Use it as a batch job to produce the transit layer of our tiered grid, not as a service. Expect heavy compute for all-pairs (Helsinki used a 64-core VM), but our use is many-to-few (cells to POI categories), which is far cheaper.

### 3.5 PMTiles + Cloudflare R2 (adopt for serving)

Single-file tile archives (raster PNG/WebP or vector MVT) served by HTTP range requests from object storage; MapLibre and Leaflet plugins exist; `go-pmtiles` converts and uploads. R2 free tier (10 GB, 10M reads/month, zero egress) covers several metros of travel-time tiles. `transport-maps` demonstrates packing per-origin binary arrays into PMTiles, which is a clever way to serve "times from this cell" without a server. Integration: build tiles in the precompute job (tippecanoe for vector cells, `rio-tiler`/GDAL for rasters), upload, point MapLibre at `pmtiles://`.

### 3.6 COG + maplibre-cog-protocol (adopt pilot) / TiTiler (consider)

Our 100 m Dijkstra rasters are a natural COG. `maplibre-cog-protocol` (163 stars, MIT, EPSG:3857 only) renders them client-side with ColorBrewer ramps and per-pixel functions (e.g. threshold at 15 min). Zero server cost. If we need non-3857 sources, dynamic re-styling or large mosaics, TiTiler (v2.4.0, MIT) on Lambda or a small container is the mature answer. Gotcha: write COGs with overviews and Mercator projection; `cog-tiler-wasm` is a second, newer client-side option.

### 3.7 DuckDB spatial + DuckDB-Wasm + h3-duckdb (adopt)

Confirms the in-house agent's engine: R-tree indexes accelerate ST_Intersects/Within/Contains filters with a constant geometry, GeoParquet is native, `ST_ReadOSM` reads PBFs, and GDAL vector drivers are bundled (no rasters). DuckDB-Wasm supports spatial, httpfs and parquet, plus community H3, so "download a metro's POI GeoParquet once and filter in the browser" is viable for the POI explorer. Gotcha: httpfs in the browser requires CORS and HTTPS; bundled GDAL may lag system GDAL.

### 3.8 QuackOSM + osmium-tool (adopt for data plumbing)

Replace Overpass POI queries (the acknowledged 95% bottleneck) with a nightly `osmium extract` of the Triangle from the NC PBF, then QuackOSM tag-filtered GeoParquet (amenity/shop/leisure tags). QuackOSM 0.20.0 (2026-11-02), Apache-2.0, Python 3.10+, runs on Windows via DuckDB. Budget ~10x the PBF size in scratch disk.

### 3.9 overturemaps-py + Foursquare OS Places (adopt / consider)

`overturemaps download --bbox ... --type=place -f geoparquet` remains the primary POI source (v1.0.2, MIT). Foursquare OS Places (Apache-2.0, 104M POIs, `date_closed`/`date_refreshed`) is a strong cross-check for business-site and hotel wedges; access moved to an Iceberg catalog with a Hugging Face mirror. Gotcha: Overture places carry CDLA-Permissive-2.0 and OSM-derived parts ODbL; keep attribution consistent.

### 3.10 MapLibre GL JS (adopt, migrate from Leaflet)

v6.16.0 (2026-10-25), BSD-3, `addProtocol` for `pmtiles://` and `cog://`, GPU rendering for hundreds of thousands of cells, vector basemaps from Protomaps. Migration is a contained change to `frontend/src/components/Map/Map.tsx` (react-leaflet -> react-map-gl/maplibre or raw MapLibre). Keep Leaflet for the current polygon-only UI until the grid layer ships.

### 3.11 opengeos/GeoAgent and the structured tool pattern (adopt pattern)

530 stars, MIT, created 2026-02 and actively pushed. Its contribution is not the agent loop but the **tool contract**: a decorator that turns functions into typed tools with `requires_confirmation`, `destructive`, `long_running` flags and categories in a registry, plus adapters for multiple map widgets and model providers (Anthropic included). We should apply this to our NL -> structured filter agent: every criterion type (`distance_to_place`, `travel_time_to_category`, `transit_access`) becomes a typed tool with validation, and the compiled DuckDB SQL is shown to the user as provenance.

### 3.12 Pelias (consider, phase 2) and Nominatim public API (now)

Pelias docker Portland-metro example (>=8 GB RAM, <1 h) is the only metro-scale geocoder self-host that is cheap; Windows is unsupported so it runs in WSL2 or on the VM. Until volumes justify it, keep the Nominatim public API (1 req/s, identifying User-Agent) exactly as `validate-location` does today, or pay-as-you-go via Google's Maps MCP place resolution (10k free/month).

---

## 4. Specific findings

### (i) Most practical way to self-host or avoid self-hosting routing for a metro

1. **Self-host Valhalla on a state extract.** NC PBF is 430 MB; Valhalla's tile store keeps runtime RAM moderate (published: 16 GB Europe, 32 GB planet). Estimate 2-4 GB RAM and a few GB of disk for NC; build time tens of minutes (estimate, verify). Use the official scripted image, mount `custom_files` and `gtfs_feeds`, set `server_threads` low if the build is OOM-killed. Headway shows a complete Valhalla+Pelias+tiles stack running a mid-size metro in ~4 GB.
2. **Clip before you build.** `osmium extract` with a Triangle polygon cuts build time and tile size further and lets us run multiple metros as separate containers or a single multi-extract build (`tile_urls` accepts several PBFs).
3. **Avoid self-hosting for transit at first.** Transitous (MOTIS) already loads the Triangle agencies; use it for prototypes and ground-truth comparisons under its non-commercial, ~720 req/day policy, then self-host MOTIS (MIT, low memory) or enable Valhalla multimodal with the same GTFS.
4. **Keep a hosted fallback.** openrouteservice's public API (isochrones + matrix) and the FOSSGIS Valhalla demo server exist, but neither is for production. Commercial Valhalla hosts (e.g. Stadia Maps) and TravelTime are the paid fallbacks **(pricing unverified in this survey)**. Google's Maps MCP does not offer isochrones or matrices.
5. **Do not pick OSRM or pgRouting for this product**: OSRM lacks isochrones and multi-profile in one process; pgRouting adds a PostGIS dependency and is slower.

### (ii) Proven approaches to precomputing travel-time grids and serving them cheaply

- **Resolution and tiering.** Helsinki TTM uses 250 m cells (13,132) for all-pairs; Snowflake's H3 res-6 matrix for Germany was 121M rows and they note precision is bounded by hexagon size with roughly quadratic cost growth; Close uses census blocks. Our 100 m grid (~H3 res 10, 76 m edge, 0.015 km2) is finer than any of these and justified only because we compute many-to-few (cells to POI categories) rather than all-pairs. Tier 2 metros can use H3 res 9 (201 m edge) with the same pipeline.
- **Nearest-POI-per-cell is a solved primitive.** Pandana's network aggregation and `nearest_pois` (AGPL) and our multi-source Dijkstra are the same algorithm; GraphHopper `/spt`, MOTIS `/one-to-all` and Valhalla GeoTIFF isochrones are engine-side equivalents when we want engine-quality costing rather than our own speed model.
- **Store as rasters, not polygons.** Helsinki's per-cell isochrone GeoJSON weighs ~2.5 GB per matrix; OTP and Valhalla both emit GeoTIFF travel-time surfaces. One int16 minutes band per (metro, mode, category) as a COG with overviews is compact and directly renderable.
- **Serve statically.** Three zero-server patterns are in use: (a) COG on object storage decoded in the browser (`maplibre-cog-protocol`, `cog-tiler-wasm`, `georaster-layer-for-leaflet`); (b) raster or vector PMTiles via range requests (PMTiles, Protomaps; `transport-maps` packs per-origin binary arrays); (c) pre-baked GeoJSON per area on S3/GitHub Pages (uk-isochrones-map, sf-commute-isochrone). Cloudflare R2's zero-egress free tier makes (a) and (b) effectively free at our scale. TiTiler remains the dynamic-server option.
- **Combine with on-demand.** Snowflake's and Close's experience is that precompute covers category layers while user-specific places need live routing; our design (gridded layers + Valhalla matrix for arbitrary places) matches.

### (iii) State of LLM -> GIS agents and the most reliable pattern

- **Code generation (LLM-Geo, IntelliGeo, GeoColab, ShapefileGPT)** produces arbitrary Python/PyQGIS; results are hard to verify, sandboxing is required, and the leading repos are GPL research code. Fine for analysts, wrong for a consumer product where every answer must be explainable.
- **Structured tool calling into a registry (opengeos/GeoAgent, iamtekson GeoAgent, qgis-mcp minus `execute_code`, MapAgent)** is where active 2026 development is: typed parameters, safety flags, dependency-ordered task queues. Benchmarks in the awesome-list note explicit "function calling vs code generation" comparisons; the hierarchical GeoAgent paper reports ~95% success on 147 tasks but with multi-layer review overhead.
- **NL -> intermediate representation -> SQL (geointent, geoask, GeoSQL-7B)** is the lightest and most verifiable: the IR is validated against a schema, compiled to DuckDB/PostGIS SQL, executed read-only, and the SQL plus row counts are shown. This is the pattern of our in-house agent.
- **Geospatial MCP servers** are mostly small wrappers (5-30 stars) around Nominatim/Overpass/OSRM/Valhalla with polite rate limiting. Their value to us is as reference for tool naming and argument shapes (`analyze_neighborhood`, `calculate_isochrone`, `find_nearby_places`) and as a way to expose our own backend to Claude or other assistants later. Google's managed MCP is the only production-grade one and lacks reachability tools.
- **Recommendation:** keep the structured-filter IR; make every criterion a typed tool with JSON-schema validation; compile to SQL and to Valhalla requests deterministically; run a dry-run cost estimate; display the compiled criteria and SQL to the user; log IR for evaluation. Borrow GeoAgent's registry metadata and geointent's multi-backend compile idea.

---

## 5. Implications and recommended stack

**Recommended open-source stack (with alternatives):**

| Layer | Primary | Alternative |
|---|---|---|
| On-demand routing / isochrones / matrix | Valhalla (self-hosted NC extract, official ghcr image) | GraphHopper (Apache-2.0) |
| Transit | Transitous (prototype) -> MOTIS self-host or Valhalla multimodal with Triangle GTFS | r5py batch for transit grids; OTP 2 |
| Grid precompute | In-house 100 m Dijkstra pipeline; Valhalla GeoTIFF / MOTIS one-to-all for cross-check | r5py (transit), Pandana (AGPL, reference only) |
| Grid storage | COG GeoTIFF (int16 minutes) + GeoParquet cells keyed by H3 res 10/9 (h3-duckdb) | PMTiles raster |
| Serving | Cloudflare R2 + `maplibre-cog-protocol` / PMTiles (no server) | TiTiler (dynamic), martin (vector tiles) |
| Query engine | DuckDB spatial (server) and DuckDB-Wasm (browser POI filters) | PostGIS + pgRouting |
| POI data | Overture places via overturemaps-py; OSM via osmium-tool + QuackOSM to GeoParquet | Foursquare OS Places (Apache-2.0); pyrosm |
| GTFS discovery | Mobility Database catalogs; Transitous `us-nc.json` | gtfs_kit for stop/route extraction |
| Geocoding | Nominatim public API (dev, low volume) | Pelias docker (phase 2); Google Maps MCP resolve-names |
| Front end | MapLibre GL JS (migrate `Map.tsx`) with Protomaps basemap | Leaflet + georaster-layer-for-leaflet (interim); deck.gl for very large cell sets |
| NL agent | In-house structured IR -> DuckDB SQL + Valhalla calls; adopt GeoAgent-style tool registry and safety flags | geointent-style multi-backend compiler |

**Concrete implications for the build:**

1. Replace the FOSSGIS demo URL default in `backend/app/services/valhalla.py` with a self-hosted Valhalla container (compose file, `tile_urls` = NC or Triangle extract) and add `format=geotiff` support so engine isochrones can be compared with our raster pipeline.
2. Move OSM POI acquisition in `location_analyzer.py` off Overpass to a scheduled `osmium extract` + QuackOSM GeoParquet build; keep OSMnx for graphs.
3. Emit precompute outputs as 3857 COGs with overviews and as H3-keyed GeoParquet; publish to R2; add a MapLibre layer using `cog://`.
4. Plan the Leaflet -> MapLibre migration as its own milestone; the current polygon UI can stay on Leaflet until grid layers ship.
5. Harden the NL agent: JSON-schema for the filter IR, typed tool registry with confirmation flags, read-only DuckDB connection, visible compiled SQL; evaluate on a logged query set.
6. Licence hygiene: avoid AGPL (Pandana/UrbanAccess) and GPL (LLM-Geo, ORS self-host) in product code; prefer MIT/BSD/Apache components listed above; track ODbL (OSM/Overture), CDLA-Permissive-2.0 (Overture places) and Apache-2.0 (Foursquare) attribution.

---

## 6. Open questions

1. Actual Valhalla build time, tile size and runtime RAM for the NC extract on a 2-4 GB container (spike needed); whether a Triangle-only `osmium extract` is worth the extra step.
2. Quality of Valhalla multimodal transit vs MOTIS vs r5py on Triangle GTFS (frequency-based vs schedule-based, transfer penalties); which becomes the production transit path.
3. Transitous terms for a future commercial product (currently non-commercial); whether a hosted MOTIS instance is cheaper than Valhalla multimodal.
4. COG-in-browser vs raster PMTiles for the grid layer: payload size at zoom 10-15, mobile performance, and whether per-pixel threshold functions suffice for "within N minutes" UI.
5. H3 res 10 vs our 100 m square grid as the canonical key: resampling cost, DuckDB join performance, and tile generation path (tippecanoe).
6. Whether DuckDB-Wasm in the browser (POI GeoParquet per metro) is acceptable on first load (download size, memory) or should remain server-side.
7. Leaflet 2.0 timing and react-leaflet compatibility (unverified) vs the cost of migrating to MapLibre now.
8. Hosted-API fallbacks: openrouteservice free-tier quotas (page unavailable during survey), Stadia Maps/TravelTime pricing for isochrones and matrices.
9. Foursquare OS Places access path after the move to the Iceberg "Places Portal": can DuckDB read it directly, or do we rely on the Hugging Face mirror?
10. Evaluation harness for the NL agent: do we need a fine-tuned spatial text-to-SQL model (GeoSQL-7B class) for cost, or is Claude tool-calling with a strict IR sufficient?

---

## 7. Sources

All accessed 2026-11-03.

- https://github.com/valhalla/valhalla - Valhalla README; https://github.com/valhalla/valhalla/releases; https://api.github.com/repos/valhalla/valhalla
- https://valhalla.github.io/valhalla/api/isochrone/ - Isochrone API reference
- https://valhalla.github.io/valhalla/api/matrix/ - Matrix API reference
- https://github.com/valhalla/valhalla/blob/master/docker/README.md - official Docker images
- https://github.com/nilsnolde/docker-valhalla - docker-valhalla (archived 2026-03-03)
- https://github.com/Project-OSRM/osrm-backend ; https://api.github.com/repos/Project-OSRM/osrm-backend/releases/latest
- https://github.com/Project-OSRM/osrm-backend/issues/7751 - OSRM isochrone proposal (2026-10-21)
- https://github.com/Project-OSRM/osrm-backend/wiki/Disk-and-Memory-Requirements
- https://github.com/graphhopper/graphhopper ; /releases ; docs/web/api-doc.md ; docs/core/deploy.md
- https://github.com/GIScience/openrouteservice ; https://api.github.com/repos/GIScience/openrouteservice/releases/latest
- https://giscience.github.io/openrouteservice/run-instance/system-requirements
- https://github.com/r5py/r5py ; https://api.github.com/repos/r5py/r5py/releases/latest ; https://r5py.readthedocs.io/stable/user-guide/installation/installation.html
- https://github.com/conveyal/r5 ; https://github.com/conveyal/analysis-ui ; https://api.github.com/repos/conveyal/analysis-backend
- https://github.com/opentripplanner/OpenTripPlanner ; /releases ; https://docs.opentripplanner.org/en/v2.2.0/sandbox/TravelTime/
- https://github.com/motis-project/motis ; https://transitous.org/ ; https://transitous.org/api/ ; https://raw.githubusercontent.com/public-transport/transitous/main/feeds/us-nc.json
- https://github.com/headwaymaps/headway
- https://github.com/pgRouting/pgrouting ; https://api.github.com/repos/pgRouting/pgrouting/releases/latest
- https://github.com/UDST/pandana ; https://api.github.com/repos/UDST/pandana/releases/latest ; https://github.com/UDST/urbanaccess
- https://github.com/Martenz/o-isochrone ; https://github.com/mapbox/osrm-isochrone ; https://github.com/stepankuzmin/node-isochrone ; https://github.com/mapbox/mapbox-isochrone
- https://github.com/traveltime-dev/traveltime-python-sdk
- https://developers.google.com/maps/ai/grounding-lite - Maps Experience agent tools (MCP)
- https://www.pistack.xyz/posts/2026-04-25-graphhopper-vs-osrm-vs-valhalla-self-hosted-routing-engines-guide-2026/ - engine comparison (2026-04-25)
- https://mapsi.dev/developers/routing-engine-comparison - engine comparison (2025)
- https://tech.marksblogg.com/valhalla-isochrones.html - Valhalla isochrone walkthrough (2022-08-19)
- https://download.geofabrik.de/north-america/us/north-carolina.html - NC extract size
- https://github.com/henryspatialanalysis/city_walkability ; https://henryspatialanalysis.com/news/tutorial-15-minute-city-interactive-map
- https://github.com/mapnificent/mapnificent ; https://github.com/econaxis/time2reach ; https://news.ycombinator.com/item?id=36847960
- https://github.com/AkshayM21/sf-commute-isochrone ; https://github.com/pbarber/uk-isochrones-map
- https://github.com/Amsterdam/mapitout-frontend ; https://api.github.com/repos/Amsterdam/mapitout-backend
- https://github.com/a-b-street/abstreet ; https://github.com/Zverik/15minute
- https://www.informationisbeautifulawards.com/showcase/5302-cityaccessmap
- https://github.com/pysal/access ; https://github.com/jamaps/tracc ; https://github.com/GeoDaCenter/spatial_access ; https://github.com/pysal/momepy
- https://github.com/EL-BID/urbanpy ; https://docs.urbanpy.org/ ; https://github.com/unige-geohealth/accessmod
- https://github.com/DigitalGeographyLab/Helsinki-Travel-Time-Matrices ; https://github.com/DigitalGeographyLab/travel-time-matrix-visualisation-preprocessing ; https://www.nature.com/articles/s41597-024-03689-z
- https://www.snowflake.com/en/blog/engineering/routing-inside-snowflake-h3-travel-time-matrix0/ (2026-06-25)
- https://github.com/hletrd/transport-maps
- https://github.com/protomaps/PMTiles ; https://docs.protomaps.com/pmtiles/ ; https://github.com/protomaps/basemaps
- https://developers.cloudflare.com/r2/pricing/
- https://github.com/developmentseed/titiler ; https://api.github.com/repos/developmentseed/titiler/releases/latest
- https://github.com/geomatico/maplibre-cog-protocol ; https://github.com/opengeos/cog-tiler-wasm ; https://github.com/GeoTIFF/georaster-layer-for-leaflet
- https://github.com/duckdb/duckdb-spatial ; https://duckdb.org/docs/2.0/core_extensions/spatial/r-tree_indexes.html ; https://duckdb.org/docs/2.0/core_extensions/spatial/gdal.html ; https://duckdb.org/docs/2.0/clients/wasm/extensions.html
- https://github.com/isaacbrodsky/h3-duckdb ; https://github.com/uber/h3 ; https://h3geo.org/docs/core-library/restable
- https://github.com/flatgeobuf/flatgeobuf ; https://github.com/opengeospatial/geoparquet
- https://github.com/maplibre/maplibre-gl-js ; https://api.github.com/repos/maplibre/maplibre-gl-js/releases/latest ; https://github.com/Leaflet/Leaflet ; https://api.github.com/repos/Leaflet/Leaflet/releases/latest
- https://github.com/visgl/deck.gl ; https://github.com/keplergl/kepler.gl ; https://github.com/developmentseed/lonboard
- https://api.github.com/repos/felt/tippecanoe ; https://api.github.com/repos/maplibre/martin
- https://github.com/gladcolor/LLM-Geo ; https://github.com/opengeos/GeoAgent ; https://github.com/iamtekson/GeoAgent ; https://github.com/MahdiFarnaghi/intelli_geo ; https://github.com/nkarasiak/qgis-mcp
- https://github.com/hasebul/mapagent ; https://github.com/mohammadhashemii/awesome-agentic-AI-for-Geospatial-Data ; https://www.tandfonline.com/doi/full/10.1080/13658816.2026.2624784
- https://github.com/FultonGeo/geointent ; https://pypi.org/project/geointent/ ; https://huggingface.co/SongY123/GeoSQL-7B
- https://github.com/cyanheads/openstreetmap-mcp-server ; https://github.com/NERVsystems/osmmcp ; https://github.com/ni-c/osm-mcp ; https://github.com/GRABOSM/osm-mcp
- https://github.com/koizumikento/overture-maps-mcp ; https://github.com/motherduckdb/mcp-server-motherduck
- https://sparkgeo.com/blog/geospatial-mcp-servers-mapped-and-categorized/ (403 at fetch; search snippet only)
- https://github.com/osm-search/Nominatim ; https://nominatim.org/release-docs/latest/admin/Installation/ ; https://api.github.com/repos/osm-search/Nominatim/releases/latest
- https://github.com/komoot/photon ; https://api.github.com/repos/komoot/photon/releases/latest
- https://github.com/pelias/pelias ; https://github.com/pelias/docker
- https://github.com/OvertureMaps/overturemaps-py ; https://api.github.com/repos/OvertureMaps/overturemaps-py/releases/latest
- https://github.com/kraina-ai/quackosm ; https://api.github.com/repos/kraina-ai/quackosm/releases/latest ; https://github.com/pyrosm/pyrosm ; https://github.com/gboeing/osmnx
- https://github.com/osm2pgsql-dev/osm2pgsql ; https://github.com/osmcode/osmium-tool
- https://docs.foursquare.com/data-products/docs/access-fsq-os-places ; https://tech.marksblogg.com/foursquare-open-global-poi-dataset.html
- https://github.com/mrcagney/gtfs_kit (moved to https://codeberg.org/araichev/gtfs_kit) ; https://github.com/MobilityData/mobility-database-catalogs
