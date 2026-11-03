"""Overture places + OSM POIs for the Phase 0 slice. Writes GeoParquet under v2/data/slice/.

Run from v2/:  uv run python scripts/fetch_places.py
Registry rows: docs/experiments/source-registry.md (Overture CDLA-Permissive-2.0 / Apache-2.0; OSM ODbL).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

BBOX = "-79.15,35.80,-78.55,36.15"  # west,south,east,north
OUT = Path(__file__).resolve().parents[1] / "data" / "slice"
OUT.mkdir(parents=True, exist_ok=True)

OSM_TAGS = {
    "leisure": ["park", "playground", "nature_reserve"],
    "shop": ["supermarket", "greengrocer", "convenience"],
    "amenity": ["cafe", "pharmacy", "school", "library"],
    "highway": ["bus_stop"],
    "railway": ["station", "tram_stop"],
    "public_transport": ["platform", "station"],
}


def fetch_overture() -> Path:
    out = OUT / "overture_places.parquet"
    if out.exists():
        print("overture places already present:", out)
        return out
    cmd = [sys.executable, "-m", "overturemaps.cli", "download", f"--bbox={BBOX}",
           "-f", "geoparquet", "--type=place", "-o", str(out)]
    print("running:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    return out


def fetch_osm_pois() -> Path:
    import quackosm as qosm

    out = OUT / "osm_pois.parquet"
    pbf = OUT / "slice.osm.pbf"
    if not pbf.exists():
        raise SystemExit(f"missing {pbf}; run scripts/fetch_slice_data.sh in WSL first")
    gdf = qosm.convert_pbf_to_geodataframe(str(pbf), tags_filter=OSM_TAGS, keep_all_tags=True)
    gdf.to_parquet(out)
    print("osm pois:", len(gdf), "->", out)
    return out


if __name__ == "__main__":
    ov = fetch_overture()
    print("overture bytes:", ov.stat().st_size)
    fetch_osm_pois()
