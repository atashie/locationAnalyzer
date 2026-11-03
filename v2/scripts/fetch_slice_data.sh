#!/usr/bin/env bash
# Fetch and clip OSM data for the Phase 0 slice. Run inside WSL2 Ubuntu:
#   wsl -e bash -lc "bash /mnt/c/Users/arikt/documents/github/distanceFinder/v2/scripts/fetch_slice_data.sh"
# Registry rows for every source live in docs/experiments/source-registry.md (add before fetching).
set -euo pipefail
REPO=/mnt/c/Users/arikt/documents/github/distanceFinder
DATA=$REPO/v2/data
BBOX="-79.15,35.80,-78.55,36.15"   # west,south,east,north (WGS84)
mkdir -p "$DATA/raw" "$DATA/slice" "$DATA/gtfs"

echo "== 1. North Carolina extract (Geofabrik, ODbL) =="
cd "$DATA/raw"
if [ ! -f north-carolina-latest.osm.pbf ]; then
  wget -q --show-progress https://download.geofabrik.de/north-america/us/north-carolina-latest.osm.pbf
fi
ls -la north-carolina-latest.osm.pbf

echo "== 2. osmium-tool =="
if ! command -v osmium >/dev/null; then
  sudo apt-get update -qq && sudo apt-get install -y -qq osmium-tool
fi
osmium --version | head -1

echo "== 3. clip to slice bbox; roads-only XML for osmnx =="
osmium extract -b "$BBOX" north-carolina-latest.osm.pbf -o "$DATA/slice/slice.osm.pbf" --overwrite
osmium tags-filter "$DATA/slice/slice.osm.pbf" w/highway -o "$DATA/slice/slice-roads.osm.pbf" --overwrite
osmium cat "$DATA/slice/slice-roads.osm.pbf" -o "$DATA/slice/slice-roads.osm" --overwrite
ls -la "$DATA/slice"

echo "== 4. GTFS feeds (CC BY 3.0; URLs recorded in v2/data/gtfs/feeds.txt) =="
if [ -s "$DATA/gtfs/feeds.txt" ]; then
  while read -r url; do
    [ -z "$url" ] && continue
    case "$url" in \#*) continue;; esac
    (cd "$DATA/gtfs" && wget -q --content-disposition --trust-server-names "$url" || echo "FAILED: $url")
  done < "$DATA/gtfs/feeds.txt"
  ls -la "$DATA/gtfs"
else
  echo "NOTE: v2/data/gtfs/feeds.txt is missing or empty; add the static GTFS zip URLs from"
  echo "      https://gotriangle.org/developer-resources/ (one per line) and rerun this script."
fi
echo "done"
