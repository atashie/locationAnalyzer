"""Overture places + OSM POIs for the Phase 0 slice, with fail-closed licensing.

Run from v2/:  uv run python scripts/fetch_places.py [--release YYYY-MM-DD.0]

Writes under v2/data/slice/:
  overture_places_raw.parquet      exact download (never used downstream)
  overture_places_accepted.parquet rows whose every source resolved to an allowed licence
  overture_rejected_report.json    counts and examples of quarantined rows
  overture_schema.txt              observed Arrow schema (verify category/taxonomy column names)
  osm_pois.parquet                 OSM POIs via QuackOSM with exploded tags

Registry rows: docs/experiments/source-registry.md (Overture CDLA-Permissive-2.0 / Apache-2.0; OSM ODbL).
Codex pass 3 (C1, H4, H5): pin the release, inspect the schema (the `categories` column was
removed in the 2026-09 release in favour of `taxonomy`/`basic_category`), explode OSM tags,
and persist an ACCEPTED artifact separate from the raw download.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

BBOX = "-79.15,35.80,-78.55,36.15"  # west,south,east,north
V2 = Path(__file__).resolve().parents[1]
OUT = V2 / "data" / "slice"

OSM_TAGS = {
    "leisure": ["park", "playground", "nature_reserve"],
    "shop": ["supermarket", "greengrocer", "convenience"],
    "amenity": ["cafe", "pharmacy", "school", "library"],
    "highway": ["bus_stop"],
    "railway": ["station", "tram_stop"],
    "public_transport": ["platform", "station"],
}


def fetch_overture(release: str | None) -> Path:
    raw = OUT / "overture_places_raw.parquet"
    if raw.exists():
        print("overture raw already present:", raw)
        return raw
    cmd = [sys.executable, "-m", "overturemaps.cli", "download", f"--bbox={BBOX}", "-f", "geoparquet",
           "--type=place", "-o", str(raw)]
    if release:
        cmd += ["--release", release]
    print("running:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    return raw


def inspect_schema(raw: Path) -> list[str]:
    import pyarrow.parquet as pq

    schema = pq.read_schema(raw)
    (OUT / "overture_schema.txt").write_text(str(schema), encoding="utf-8")
    cols = schema.names
    print("columns:", cols)
    for candidate in ("categories", "taxonomy", "basic_category"):
        print(f"  has {candidate!r}: {candidate in cols}")
    return cols


def partition_by_licence(raw: Path, release: str) -> None:
    import geopandas as gpd

    from locfinder.places.licence import UnknownLicence, resolve_licence

    gdf = gpd.read_parquet(raw)
    accepted_idx, licences, reasons, datasets = [], [], Counter(), Counter()
    for i, srcs in enumerate(gdf["sources"]):
        entries = []
        for s in (list(srcs) if srcs is not None else []):
            s = dict(s) if not isinstance(s, dict) else s
            entries.append(s)
            datasets[str(s.get("dataset"))] += 1
        try:
            licences.append(resolve_licence({"sources": entries}, release=release))
            accepted_idx.append(i)
        except UnknownLicence as e:
            reasons[str(e)[:120]] += 1
    acc = gdf.iloc[accepted_idx].copy()
    acc["licence"] = licences
    acc["overture_release"] = release
    acc.to_parquet(OUT / "overture_places_accepted.parquet")
    report = {
        "release": release,
        "rows_raw": int(len(gdf)),
        "rows_accepted": int(len(acc)),
        "rows_rejected": int(len(gdf) - len(acc)),
        "observed_datasets": dict(datasets),
        "rejection_reasons": dict(reasons),
        "accepted_licences": dict(Counter(licences)),
    }
    (OUT / "overture_rejected_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps(report, indent=1))


def fetch_osm_pois() -> Path:
    import quackosm as qosm

    out = OUT / "osm_pois.parquet"
    pbf = OUT / "slice.osm.pbf"
    if not pbf.exists():
        raise SystemExit(f"missing {pbf}; run scripts/fetch_slice_data.sh in WSL first")
    gdf = qosm.convert_pbf_to_geodataframe(str(pbf), tags_filter=OSM_TAGS, keep_all_tags=True, explode_tags=True)
    gdf.to_parquet(out)
    print("osm pois:", len(gdf), "columns:", [c for c in gdf.columns if c in OSM_TAGS or c in ("name", "geometry")], "->", out)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", default=None, help="Overture release id, e.g. 2026-10-21.0 (pin it; see licence manifests)")
    ap.add_argument("--skip-osm", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    raw = fetch_overture(args.release)
    inspect_schema(raw)
    if args.release:
        partition_by_licence(raw, args.release)
    else:
        print("NOTE: no --release given; accepted artifact not written (licence manifest is keyed by release).")
    if not args.skip_osm:
        fetch_osm_pois()


if __name__ == "__main__":
    main()
