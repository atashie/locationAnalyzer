# Valhalla (self-hosted) for Phase 0

Image: `ghcr.io/valhalla/valhalla-scripted` (official; env-var names per
https://github.com/valhalla/valhalla/blob/master/docker/README.md — verify there if the container exits early).

Inputs:
- `v2/data/valhalla_custom_files/slice.osm.pbf` (G2 slice build). For the NC build in Phase 1, drop
  `north-carolina-latest.osm.pbf` there instead and set `force_rebuild=True` once.
- `v2/data/gtfs_extracted/<agency>/*.txt` — one directory per feed, produced by the GTFS extraction
  step (feeds listed in `v2/data/gtfs/feeds.txt`; `feeds_report.json` records agency, timezone, and
  whether `calendar.txt`/`calendar_dates.txt` exist). Mounted read-only at `/gtfs_feeds`.

First `docker compose up` builds tiles (and transit tiles if `build_transit=True`); later runs serve.
Config lives at `v2/data/valhalla_custom_files/valhalla.json`. After the first build, raise
`service_limits.isochrone.max_locations` (default is small) and check `service_limits.isochrone.max_time_contour`
if the category experiment (Task 7) needs many destinations or long contours, then `docker compose restart`.

Measurement discipline (Codex pass 3 H8): record build wall-clock from `docker compose up` to the
first successful `/status`, and sample `docker stats --format '{{.MemUsage}}' valhalla-slice` every
5 s for the whole build and during the latency benchmark; report the peak, not a spot reading. The
8 GB cap excludes OS/API headroom, and slice numbers do not establish NC/VPS feasibility; the NC
build on the intended host is a separate, required measurement before G2 is marked passed.

Semantics to remember (Codex pass 3 H1): `reverse: true` gives an arrival (inbound) isochrone for
auto/bicycle/pedestrian. For `multimodal`, `date_time.type` 1 = departure; arrival (type 2) is not
supported, so a scheduled inbound transit surface cannot come from Valhalla; MOTIS is tested for that.
