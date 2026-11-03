# G2: Valhalla self-host (slice build) — measured 2026-11-03

**Question.** Can self-hosted Valhalla build and serve the Phase 0 slice (Chapel Hill–Durham–RTP–west Raleigh, 55×40 km) with transit, under an 8 GB memory cap, and what do anchors cost? (Synthesis §6 G2; Codex pass 3 H8: slice numbers inform G2 but do not pass it — the North Carolina build on the intended host is a separate required measurement.)

## Setup (as run)

- Host: WSL2 Ubuntu 26.04 on the Windows workstation (24 logical CPUs, 64 GB; WSL VM 31 GB), Docker Engine 29.1.3, Compose 2.40.3.
- Image: `ghcr.io/valhalla/valhalla-scripted:latest` → Valhalla **3.9.1-2085e78a5** (reported by `/status`).
- Compose (`v2/infra/valhalla/docker-compose.yml`): `mem_limit: 8g`, `cpus: 2`, `server_threads=4`, `build_transit=True`, `build_admins=True`, `build_time_zones=True`, `build_elevation=False`.
- Inputs: `slice.osm.pbf` (37 MB, osmium extract of Geofabrik NC 2026-11-03); seven GTFS feeds extracted to `v2/data/gtfs_extracted/<agency>/` and mounted at `/gtfs_feeds` (Chapel Hill Transit, Duke Transit, GoCary, GoDurham, GoRaleigh, GoTriangle, NC State; all with `calendar.txt`, tz America/New_York).

## Part 1 — build and serve (measured)

| Metric | Value | Note |
|---|---|---|
| Wall clock from `compose up` to first `/status` 200 | **514 s** | includes admins, time zones, transit ingest (`valhalla_ingest_transit`, 4 threads), tile build (`build_tile_set` 298 s), tar |
| Peak container memory during build | **966 MiB** | 80 samples at 5 s intervals (`docker stats`), `v2/data/valhalla_mem_samples.txt` |
| Tile set on disk | **466 MB** total in `valhalla_custom_files` (tiles + `valhalla_tiles.tar` + transit_tiles + admins/timezones sqlite + the 37 MB PBF) | 17 tiles |
| Restart from existing tiles to ready | **5 s** | |
| Transit tiles | built; `transit_available` in `/status` actions; multimodal departure isochrone returns a polygon | |

Incident: the first container exited (code 255, not OOM) about a minute after becoming ready. Cause: the WSL2 VM shuts down shortly after its last shell session closes, taking Docker with it. Fixed for this session by holding a `sleep infinity` session open; a VPS would not have this problem. Logged so the next person does not chase a Valhalla bug.

## API semantics checked (Valhalla 3.9.1)

| Check | Result |
|---|---|
| Departure vs arrival (`reverse: true`) auto 25-min isochrone from UNC Hospitals | different GeoJSON (27,510 vs 26,514 bytes): arrival semantics are real and asymmetric on one-way streets |
| `format: geotiff` with `reverse: true`, auto 45 min | HTTP 200, `image/tiff`, 40,816 bytes, valid TIFF header (`II*\0`) — the reference path for G1 works |
| `multimodal` with `date_time.type: 1` (departure 2026-11-10 08:00), 45 min | polygon returned (transit tiles in use) |
| `multimodal` with `date_time.type: 2` (arrive by 08:30) | HTTP 501 `Arrive by for multimodal not implemented yet` — confirms Codex pass-3 H1; a scheduled inbound transit surface cannot come from Valhalla; MOTIS is tested for that |
| Isochrone limits | `service_limits.isochrone.max_locations` raised to 1000 and `max_time_contour` to 120 via `infra/valhalla/patch_limits.py` for the category-layer experiment (local only) |

## Part 2 — anchor latency

See the "Anchor latency benchmark (Task 6)" section appended below by `spikes/g2_anchor_bench.py` when it runs (fixed named anchors, 90 random anchors, 2 off-network anchors; cold and warm; concurrency 1 and 8; every failure recorded).

## Verdict (provisional)

The slice is cheap to build and tiny to serve. **G2 is not passed by this**: the NC extract (410 MB PBF) on the intended 8 GB VPS, with transit for the seven agencies, must be built and benchmarked before Phase 1 deployment (Codex pass 3 H8). What is settled: Valhalla 3.9.1 provides arrival isochrones, GeoTIFF grids, and transit departure isochrones; it does not provide transit arrival isochrones.
