"""Gate G6: Overture (accepted artifact) vs OSM per wedge category in the slice.

Reports counts, cross-source AGREEMENT within 50 m (agreement is not truth; the manual
audit of 200 POIs supplies recall against an independent inventory), Overture duplicate
pairs via a radius query (25 m, same primary name), and the licence partition summary.
Writes docs/experiments/g6-poi-coverage.md (overwrites the generated section).

Run from v2/:  uv run python spikes/g6_poi_coverage.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import shapely

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ACCEPTED_PLACES, GRID, OSM_POIS, RESULTS, SLICE, stamp  # noqa: E402
from locfinder.places.categories import WEDGE_CATEGORIES, select_osm, select_overture  # noqa: E402

AGREE_M = 50.0
DUP_M = 25.0


def agreement(a: gpd.GeoDataFrame, b: gpd.GeoDataFrame) -> int:
    """Number of rows in a with at least one row of b within AGREE_M metres."""
    if len(a) == 0 or len(b) == 0:
        return 0
    tree = shapely.STRtree(b.geometry.centroid.values)
    hits = tree.query(a.geometry.centroid.values, predicate="dwithin", distance=AGREE_M)
    return int(len(np.unique(hits[0])))


def duplicate_pairs(o: gpd.GeoDataFrame) -> int:
    if len(o) < 2:
        return 0
    pts = o.geometry.centroid.values
    names = o["names"].apply(lambda n: (n or {}).get("primary") if hasattr(n, "get") else None).to_numpy()
    tree = shapely.STRtree(pts)
    i, j = tree.query(pts, predicate="dwithin", distance=DUP_M)
    m = (i < j) & (names[i] == names[j]) & (names[i] != None)  # noqa: E711
    return int(m.sum())


def main() -> None:
    ov = gpd.read_parquet(ACCEPTED_PLACES).to_crs(GRID.crs)
    osm = gpd.read_parquet(OSM_POIS).to_crs(GRID.crs)
    report = json.loads((SLICE / "overture_rejected_report.json").read_text(encoding="utf-8"))
    lines = [f"# G6: POI coverage and licence (generated {stamp()})", "",
             f"Slice bbox {GRID.ncols}x{GRID.nrows} cells. Overture release {report['release']}: raw {report['rows_raw']}, "
             f"accepted {report['rows_accepted']}, rejected {report['rows_rejected']} (fail-closed resolver; every source entry carried an explicit "
             f"allow-listed licence: {report['accepted_licences']}). Observed source datasets: {sorted(report['observed_datasets'])}.",
             f"OSM POIs (QuackOSM, exploded tags): {len(osm)} features.", "",
             "Agreement = other source has a feature within 50 m (not recall; see manual audit below).", "",
             "| category | overture n | osm n | overture with OSM within 50 m | osm with Overture within 50 m | overture dup pairs (25 m, same name) | notes |",
             "|---|---|---|---|---|---|---|"]
    for cat, spec in WEDGE_CATEGORIES.items():
        o = select_overture(ov, cat)
        s = select_osm(osm, cat) if spec["osm"] else osm.iloc[0:0]
        note = ""
        if cat == "transit_stop":
            note = "Overture has stations/facilities only; bus stops come from OSM"
        if cat == "trail":
            note = "no OSM tag mapping yet"
        lines.append(f"| {cat} | {len(o)} | {len(s)} | {agreement(o, s)} | {agreement(s, o)} | {duplicate_pairs(o)} | {note} |")
    lines += ["", "## Manual audit (to fill)", "",
              "Audit 25 POIs per category against an independent inventory (e.g. municipal park lists, chain store locators, NCES for schools); "
              "record precision and recall per source and choose the preferred source per category.", "",
              "| category | sample n | overture precision | overture recall | osm precision | osm recall | preferred source | reason |",
              "|---|---|---|---|---|---|---|---|"]
    (RESULTS / "g6-poi-coverage.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
