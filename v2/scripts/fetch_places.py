"""Overture places + OSM POIs for a metro, with fail-closed licensing.

Run from v2/:  uv run python scripts/fetch_places.py --release 2026-10-21.0 [--metro triangle]

Writes under v2/data/<metro>/:
  overture_places_raw.parquet      exact download (never used downstream)
  overture_places_accepted.parquet rows whose every source resolved to an allowed licence
  overture_rejected_report.json    counts, observed datasets, and quarantine reasons
  overture_schema.txt              observed Arrow schema (the `categories` column was removed in
                                   the 2026-09 release in favour of `taxonomy`/`basic_category`)
  osm_pois.parquet                 OSM POIs via QuackOSM with exploded tags

Registry rows must exist in docs/experiments/source-registry.md before fetching.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "spikes"))

OSM_TAGS = {
    "leisure": ["park", "playground", "nature_reserve"],
    "shop": ["supermarket", "greengrocer", "convenience"],
    "amenity": ["cafe", "pharmacy", "school", "library"],
    "highway": ["bus_stop"],
    "railway": ["station", "tram_stop"],
    "public_transport": ["platform", "station"],
}


def fetch_overture(out_dir: Path, bbox: str, release: str | None) -> Path:
    raw = out_dir / "overture_places_raw.parquet"
    if raw.exists():
        print("overture raw already present:", raw)
        return raw
    cmd = [sys.executable, "-m", "overturemaps.cli", "download", f"--bbox={bbox}", "-f", "geoparquet",
           "--type=place", "-o", str(raw)]
    if release:
        cmd += ["--release", release]
    print("running:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    return raw


def inspect_schema(raw: Path, out_dir: Path) -> list[str]:
    import pyarrow.parquet as pq

    schema = pq.read_schema(raw)
    (out_dir / "overture_schema.txt").write_text(str(schema), encoding="utf-8")
    cols = schema.names
    print("columns:", cols)
    for candidate in ("categories", "taxonomy", "basic_category"):
        print(f"  has {candidate!r}: {candidate in cols}")
    return cols


def partition_by_licence(raw: Path, out_dir: Path, release: str) -> None:
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
    acc.to_parquet(out_dir / "overture_places_accepted.parquet")
    report = {
        "release": release,
        "rows_raw": int(len(gdf)),
        "rows_accepted": int(len(acc)),
        "rows_rejected": int(len(gdf) - len(acc)),
        "observed_datasets": dict(datasets),
        "rejection_reasons": dict(reasons),
        "accepted_licences": dict(Counter(licences)),
    }
    (out_dir / "overture_rejected_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps(report, indent=1))


def fetch_osm_pois(out_dir: Path, pbf: Path) -> Path:
    import quackosm as qosm

    out = out_dir / "osm_pois.parquet"
    if not pbf.exists():
        raise SystemExit(f"missing {pbf}; extract the routing area first (scripts/fetch_slice_data.sh)")
    gdf = qosm.convert_pbf_to_geodataframe(str(pbf), tags_filter=OSM_TAGS, keep_all_tags=True, explode_tags=True)
    gdf.to_parquet(out)
    print("osm pois:", len(gdf), "->", out)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", default=None, help="Overture release id, e.g. 2026-10-21.0 (pin it)")
    ap.add_argument("--metro", default=None, help="metro name; defaults to LOCFINDER_METRO or 'triangle'")
    ap.add_argument("--skip-osm", action="store_true")
    args = ap.parse_args()

    from locfinder.metros import get_metro

    metro = get_metro(args.metro)
    out_dir = Path(__file__).resolve().parents[1] / "data" / metro.name
    out_dir.mkdir(parents=True, exist_ok=True)
    # Places are selected on the EVALUATION bbox; routing data uses the buffered bbox.
    bbox = metro.evaluation.as_osmium()
    print(f"metro {metro.name}: places bbox {bbox}")

    raw = fetch_overture(out_dir, bbox, args.release)
    inspect_schema(raw, out_dir)
    if args.release:
        partition_by_licence(raw, out_dir, args.release)
    else:
        print("NOTE: no --release given; accepted artifact not written (manifests are keyed by release).")
    if not args.skip_osm:
        pbf = out_dir / ("slice.osm.pbf" if metro.name == "slice" else "triangle-routing.osm.pbf")
        fetch_osm_pois(out_dir, pbf)


if __name__ == "__main__":
    main()
