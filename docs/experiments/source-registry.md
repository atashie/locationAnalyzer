# Source registry

No dataset is downloaded or ingested before it has a row here (synthesis §3.4). Terms are
summarized from the linked pages on the access date; re-read them before any public release.

| Source | URL | Licence / terms | Permitted: store / display / commingle / commercial | Access date | Notes |
|---|---|---|---|---|---|
| Geofabrik North Carolina OSM extract | https://download.geofabrik.de/north-america/us/north-carolina-latest.osm.pbf | ODbL 1.0, © OpenStreetMap contributors | store ✓ / display ✓ with attribution / commingle: keep OSM-derived tables separable (research 04 §3.8) / commercial ✓ under ODbL | 2026-11-03 | Routing graphs and OSM POIs for the Phase 0 slice |
| Overture Maps Places, release **2026-10-21.0** (latest on 2026-11-03 per the S3 release listing; pinned via `--release`) | https://docs.overturemaps.org/guides/places/ ; CLI https://github.com/OvertureMaps/overturemaps-py | CDLA-Permissive-2.0; Foursquare-sourced rows Apache-2.0 with NOTICE | store ✓ / display ✓ / commingle ✓ / commercial ✓ | 2026-11-03 | Per-row licence must be present or resolvable from the pinned release manifest; otherwise the row is quarantined (plan Task 10) |
| Triangle GTFS feeds (GoTriangle, GoRaleigh, GoDurham, GoCary, Chapel Hill Transit, Duke, NCSU Wolfline) | https://gotriangle.org/developer-resources/ (record each feed URL in v2/data/gtfs/feeds.txt when fetched) | CC BY 3.0 per the GoTriangle developer page; verify per feed | store ✓ / display ✓ with attribution / commingle ✓ / commercial ✓ | 2026-11-03 | Transit experiment only in Phase 0 |
| Transitous public transit API (ground truth only) | https://transitous.org ; https://api.transitous.org | Community service, non-commercial use, polite rate (research 03: ~720 req/day cap) | store ✗ (results used only for comparison tables) / display ✗ / commercial ✗ | 2026-11-03 | ≤ 100 requests at ≤ 1 req/s with an identifying User-Agent, Phase 0 only |
