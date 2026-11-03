# Routing services

Two engines, chosen by measurement (see `../../docs/experiments/phase0-decisions.md` D1, D2, D9):

| Service | Port | Covers | Role |
|---|---|---|---|
| **Valhalla** 3.9.1 | 8003 | **all of North Carolina** | arbitrary arrival anchors for drive/bike/walk; drive and bike category layers via `/expansion` |
| **MOTIS** | 8080 | buffered Triangle OSM + seven GTFS feeds | scheduled **arrive-by** transit, which Valhalla cannot do (HTTP 501) |

Walk category layers come from our own graph, not from either service (D1: our walk model is
unbiased and passes the owner's tolerance; our drive model is 5.4 min optimistic and does not).

## Current state on this machine

Both run in Docker inside WSL2 Ubuntu, on the **native** Linux filesystem (`/root/...`). A Windows
bind mount works for Valhalla but **fails for MOTIS** with a resize error, so keep both native.

    docker ps                       # valhalla-nc on 8003, motis on 8080
    curl -s localhost:8003/status
    curl -s "localhost:8080/api/v1/plan?fromPlace=35.9960,-78.9010&toPlace=35.9049,-79.0469&time=2026-11-10T13:00:00Z&arriveBy=true"

Measured footprints: Valhalla 568 MiB resident serving statewide tiles (capped at 2 vCPU / 8 GB),
MOTIS 393 MiB (capped at 2 vCPU / 2 GB). Tiles and timetables on disk: 2.2 GB and 281 MB.

**WSL2 shuts its VM down shortly after the last shell closes, taking Docker with it.** Hold a
session open (`wsl -e sleep infinity`) during long runs, or expect the containers to vanish. This
cost one confusing debugging detour; a real VPS does not behave this way.

## Rebuilding Valhalla for a state

    # workstation build (121 s for North Carolina on 8 vCPU), then upload the tar
    docker run -d --name valhalla-build --cpus 8 --memory 16g \
      -v "$HOME/valhalla_nc:/custom_files" -v "$HOME/valhalla_nc/gtfs_feeds:/gtfs_feeds:ro" \
      -e use_tiles_ignore_pbf=False -e force_rebuild=True -e build_elevation=False \
      -e build_admins=True -e build_time_zones=True -e build_transit=True \
      -e serve_tiles=False -e update_existing_config=True \
      ghcr.io/valhalla/valhalla-scripted:latest

    # serve prebuilt tiles (ready in 3 s)
    docker run -d --name valhalla-nc --cpus 2 --memory 8g -p 8003:8002 \
      -v "$HOME/valhalla_nc:/custom_files" -v "$HOME/valhalla_nc/gtfs_feeds:/gtfs_feeds:ro" \
      -e use_tiles_ignore_pbf=True -e serve_tiles=True -e server_threads=4 \
      ghcr.io/valhalla/valhalla-scripted:latest

Do **not** build in place on an 8 GB server: it succeeds but peaks at 7,603 MiB, 93% of the cap
(D9). `infra/valhalla/patch_limits.py` raises the isochrone and matrix service limits the
experiments need; rerun it after a rebuild, since a rebuild rewrites `valhalla.json`.

## Rebuilding MOTIS

    cd $HOME/motis_nc    # native filesystem, not /mnt/c
    docker run --rm --user 0:0 -v "$PWD:/data" -w /data ghcr.io/motis-project/motis:latest \
      /motis config triangle-routing.osm.pbf *.zip
    # remove the `tiles:` block from config.yml: the vector-tile profile only exists at the image root
    docker run --rm --user 0:0 -v "$PWD:/data" -w /data ghcr.io/motis-project/motis:latest /motis import
    docker run -d --name motis --user 0:0 --cpus 2 --memory 2g -p 8080:8080 \
      -v "$PWD:/data" -w /data ghcr.io/motis-project/motis:latest /motis server

The binary is `/motis` and is not on `PATH`, so `docker run ... motis import` fails with "executable
file not found". Import takes 7 s. Validate every GTFS feed's calendar against the dates you intend
to query: Duke Transit's published feed is more than a year stale and contributes zero trips (D7).
