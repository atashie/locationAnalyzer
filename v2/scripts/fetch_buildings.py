"""Overture **Buildings** for a metro, with fail-closed licensing. Phase 1 stage S2.4.

Run from v2/:  uv run python scripts/fetch_buildings.py --release 2026-10-21.0 [--metro triangle]

Writes under v2/data/<metro>/:
  overture_buildings_raw.parquet        exact download (never used downstream)
  overture_buildings_accepted.parquet   rows whose every source resolved to an allowed licence
  overture_buildings_rejected.parquet   quarantined rows, kept so a decision can be revisited
  overture_buildings_report.json        counts, observed datasets and licences, quarantine reasons

Buildings are **not** Places, and the difference is the point of this script. Places' sources are
all permissive (CDLA-Permissive-2.0, Apache-2.0, CC0-1.0). Buildings draw on OpenStreetMap and
Microsoft ML footprints under **ODbL 1.0** and on Esri and Google Open Buildings under **CC BY
4.0**, neither of which is in `licence.ALLOWED_LICENCES`. So most rows are expected to quarantine,
and that is the fail-closed machinery working rather than a bug: a derived *database* containing
ODbL rows is share-alike, and that is a decision for the owner, not a default for a script.

Acquired for the **grid's own footprint**, which is wider than the geographic evaluation bbox
because the grid is an axis-aligned UTM rectangle enclosing it. 4.54% of the Triangle's cells lie
outside that geographic box and still count towards the published denominator, so the input has to
cover the cells it weights.

S2.4 needs buildings only as a **coverage diagnostic** — rasterised to counts, to weight the
no-data audit by how many buildings sit in a gap rather than by cell area. Nothing is republished,
so the use is a Produced Work. The report records the observed licences so the registry row can be
verified against reality instead of against the documentation.

Acquisition goes through `places.acquire`, which holds the two S4.1 hazards in one tested place: a
raw file is never reused for a different release or bounding box, and an interrupted download can
never be promoted or inherit the previous label. The observed dataset and licence sets are written
out too, so the registry row is checkable against reality rather than against the documentation.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "spikes"))

from _common import METRO_DIR, OVERTURE_RELEASE  # noqa: E402
from locfinder.metros import get_metro  # noqa: E402
from locfinder.places.acquire import Acquisition, acquire  # noqa: E402
from locfinder.places.licence import ALLOWED_LICENCES, UnknownLicence, resolve_licence  # noqa: E402

#: The allowlist for **this diagnostic use only**, never a widening of `ALLOWED_LICENCES`.
#:
#: Measured on the first download: every one of 500,592 Triangle buildings quarantined under the
#: strict list, because the observed licences are
#:   ODbL-1.0                                                      782,594 source entries
#:   "Creative Commons by Attribution (CC BY 4.0) with OpenStreetMap waivers"   25,523
#: across datasets OpenStreetMap (437,549), Microsoft ML Buildings (345,045) and Esri Community
#: Maps (25,523). No Google Open Buildings in this metro.
#:
#: Owner decision 17 is that publishing OSM-derived work under ODbL is welcome, and S2.4 rasterises
#: footprints to **counts** for a coverage audit and republishes nothing, so the use is a Produced
#: Work rather than a database redistribution. **Confirmed by the owner 2026-11-04.** Widening here
#: and nowhere else keeps that reasoning attached to the one place it applies. Note the CC BY string
#: is a **non-SPDX free-text variant**, so it is matched literally -- brittle, and a release that
#: rewords it will quarantine again, which is the safe direction to fail.
DIAGNOSTIC_LICENCES = ALLOWED_LICENCES | frozenset({
    "ODbL-1.0",
    "Creative Commons by Attribution (CC BY 4.0) with OpenStreetMap waivers",
})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", default=OVERTURE_RELEASE)
    ap.add_argument("--metro", default=None)
    args = ap.parse_args()

    import geopandas as gpd

    metro = get_metro(args.metro)
    out_dir = METRO_DIR if args.metro is None else METRO_DIR.parent / metro.name
    out_dir.mkdir(parents=True, exist_ok=True)
    # The published grid's **actual footprint**, not the geographic evaluation bbox.
    # `GridSpec.from_bbox_wgs84` encloses the projected geographic box in an axis-aligned, rounded
    # UTM rectangle and masks nothing, so 15,015 of the Triangle's 330,502 cells (4.54%) fall
    # outside the geographic bbox while still counting towards the published coverage denominator
    # (Codex pass-11 M4). Acquiring buildings for the geographic bbox would weight that denominator
    # with an input covering less ground than the cells it describes.
    w, s_, e_, n = metro.grid().envelope_wgs84()
    bbox = f"{w:.6f},{s_:.6f},{e_:.6f},{n:.6f}"

    raw, _ = acquire(out_dir / "overture_buildings_raw.parquet",
                     Acquisition(overture_type="building", release=args.release, bbox=bbox))
    gdf = gpd.read_parquet(raw)
    print(f"{len(gdf):,} buildings over the {metro.name} grid footprint", flush=True)

    datasets: Counter = Counter()
    licences: Counter = Counter()
    resolved: list[str | None] = []
    reasons: Counter = Counter()
    for row in gdf.to_dict("records"):
        srcs = row.get("sources")
        srcs = [] if srcs is None else list(srcs)
        for src in srcs:
            if isinstance(src, dict):
                datasets[str(src.get("dataset"))] += 1
                licences[str(src.get("license"))] += 1
        try:
            resolved.append(resolve_licence({"sources": srcs}, release=args.release,
                                            allowed=DIAGNOSTIC_LICENCES))
        except UnknownLicence as exc:
            resolved.append(None)
            reasons[str(exc)[:120]] += 1

    gdf["licence"] = resolved
    gdf["overture_release"] = args.release
    accepted = gdf[gdf["licence"].notna()]
    rejected = gdf[gdf["licence"].isna()]
    accepted.to_parquet(out_dir / "overture_buildings_accepted.parquet")
    rejected.to_parquet(out_dir / "overture_buildings_rejected.parquet")

    report = {
        "metro": metro.name, "release": args.release, "bbox": bbox,
        "total": int(len(gdf)), "accepted": int(len(accepted)), "rejected": int(len(rejected)),
        "observed_datasets": dict(datasets.most_common()),
        "observed_licences": dict(licences.most_common()),
        "accepted_licences": accepted["licence"].value_counts().to_dict(),
        "quarantine_reasons": dict(reasons.most_common(8)),
        "strict_allowlist": sorted(ALLOWED_LICENCES),
        "diagnostic_allowlist_used": sorted(DIAGNOSTIC_LICENCES),
        "use": ("building-weighted coverage diagnostic (S2.4): rasterised to counts, never "
                "republished"),
    }
    (out_dir / "overture_buildings_report.json").write_text(
        json.dumps(report, indent=1), encoding="utf-8")

    print(f"accepted {len(accepted):,} / rejected {len(rejected):,}", flush=True)
    print("observed licences:", json.dumps(report["observed_licences"], indent=1), flush=True)
    print("observed datasets:", json.dumps(report["observed_datasets"], indent=1), flush=True)
    if reasons:
        print("quarantine reasons:", json.dumps(report["quarantine_reasons"], indent=1), flush=True)
    print(f"\nwrote {out_dir / 'overture_buildings_report.json'}", flush=True)
    print("The registry row for Buildings must be verified against `observed_licences` above "
          "(docs/experiments/source-registry.md).", flush=True)


if __name__ == "__main__":
    main()
