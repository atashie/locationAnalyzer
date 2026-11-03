"""G6 partial manual audit, automated: recall of Overture and OSM against an AUTHORITATIVE
school inventory (NCES EDGE Public School Locations 2023-24, LEAID 3700720 = Chapel Hill-Carrboro),
cached by the sibling CHCCS_geospatial project.

This is an independent inventory, not cross-source agreement, so it measures recall properly
(Codex pass 3 M2). It covers only the CHCCS part of the slice and only the school category.

Run from v2/:  uv run python spikes/g6_school_recall.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import shapely
from shapely.geometry import Point

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ACCEPTED_PLACES, GRID, OSM_POIS, RESULTS, stamp  # noqa: E402
from locfinder.places.categories import select_osm, select_overture  # noqa: E402

NCES = Path("C:/Users/arikt/documents/github/CHCCS_geospatial/data/cache/nces_school_locations.csv")
MATCH_M = 150.0  # a school campus is large; 150 m from the NCES point counts as found


def main() -> None:
    truth = []
    with NCES.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            truth.append((r["school"], float(r["lat"]), float(r["lon"])))
    tg = gpd.GeoDataFrame({"name": [t[0] for t in truth]},
                          geometry=[Point(t[2], t[1]) for t in truth], crs="EPSG:4326").to_crs(GRID.crs)

    ov = select_overture(gpd.read_parquet(ACCEPTED_PLACES).to_crs(GRID.crs), "school")
    osm = select_osm(gpd.read_parquet(OSM_POIS).to_crs(GRID.crs), "school")

    rows = []
    for src_name, src in (("Overture", ov), ("OSM", osm)):
        if len(src) == 0:
            rows.append((src_name, 0, len(tg), 0.0)); continue
        tree = shapely.STRtree(src.geometry.centroid.values)
        found = []
        for i, g in enumerate(tg.geometry.values):
            hits = tree.query(g, predicate="dwithin", distance=MATCH_M)
            found.append(len(hits) > 0)
        rows.append((src_name, int(sum(found)), len(tg), sum(found) / len(tg)))
        if src_name == "Overture":
            misses = [tg.name.iloc[i] for i, ok in enumerate(found) if not ok]
        else:
            misses_osm = [tg.name.iloc[i] for i, ok in enumerate(found) if not ok]

    lines = ["", "## Independent recall check: schools vs NCES (automated part of the manual audit)", "",
             f"Run {stamp()}. Truth set: {len(tg)} Chapel Hill-Carrboro public schools with NCES EDGE 2023-24 coordinates "
             f"(cached by the CHCCS_geospatial project). A source 'finds' a school if any of its selected "
             f"school-category features lies within {MATCH_M:.0f} m of the NCES point. This is recall against an "
             "independent inventory, not agreement between our two sources.", "",
             "| source | schools found | of | recall |", "|---|---|---|---|"]
    for name, k, n, r in rows:
        lines.append(f"| {name} | {k} | {n} | {r:.0%} |")
    lines += ["", f"Overture missed: {', '.join(misses) if misses else 'none'}.",
              f"OSM missed: {', '.join(misses_osm) if misses_osm else 'none'}.", "",
              "Scope limit: this covers one district and one category. Parks, playgrounds and groceries still need "
              "their own independent inventories (municipal park lists, chain store locators) before a per-category "
              "source preference is defensible."]
    text = "\n".join(lines)
    with (RESULTS / "g6-poi-coverage.md").open("a", encoding="utf-8", newline="\n") as f:
        f.write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
