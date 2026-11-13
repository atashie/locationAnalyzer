"""What the **export's own grid** costs, on top of the grid S3.1 compared. Codex pass 43 F3.

S3.1 compared two UTM source grids at matched structure coordinates and chose 100 m. The browser
does not receive either of them. It receives a **third** grid: a 514 × 643 WGS84 lon/lat raster
that `export_published_layers.py` produces by reprojecting the UTM layer with nearest resampling.

Nearest resampling preserves every source code exactly — pass 43 confirmed the exported planes
reproduce byte for byte — but it does **not** preserve each address's cell assignment. A
structure's WGS84 pixel can draw from a different UTM cell than `GridSpec.cell_for_xy` would hand
it, because the two tilings are not aligned. So the shipped spatial answer is not the one S3.1
measured, and the difference was unmeasured until this.

It also crops: the export's bounds are the metro's lon/lat evaluation box, while the UTM grid is
the bounding box of that box's projected corners, which is strictly larger. Structures in the
difference have a published answer in the source grid and no pixel in the exported one.

Needs no graph: it reads the published surface and the exported planes.

    python scripts/measure_export_regrid.py
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np
from pyproj import Transformer

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from locfinder import wire                                      # noqa: E402
from locfinder.measure.frames import structure_population       # noqa: E402
from locfinder.metros import get_metro                          # noqa: E402
from locfinder.status import (CATEGORY_COST_SELECTED, Criterion,  # noqa: E402
                              Outcome, Surface, evaluate)

V2 = pathlib.Path(__file__).resolve().parents[1]
LAYERS = V2 / "data" / "layers"
PUBLISHED = V2 / "spikes" / "g3-render" / "fixtures" / "published"
METRO = get_metro()
THRESHOLDS_MIN = (10, 15, 25, 45)
ARTIFACT = V2.parent / "docs" / "experiments" / "s3-5-export-regrid.json"
STEM = "own_triangle_grocery_walk"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=pathlib.Path, default=ARTIFACT)
    args = ap.parse_args(argv)

    manifest = json.loads((PUBLISHED / "manifest.json").read_text(encoding="utf-8"))
    nrows, ncols = manifest["nrows"], manifest["ncols"]
    west, south, east, north = manifest["bounds_wgs84"]
    entry = next(l for l in manifest["layers"] if l["id"] == STEM)
    value = np.frombuffer((PUBLISHED / entry["value_file"]).read_bytes(),
                          dtype=np.uint8).reshape(nrows, ncols)
    status = np.frombuffer((PUBLISHED / entry["status_file"]).read_bytes(),
                           dtype=np.uint8).reshape(nrows, ncols)
    horizon = entry["horizon_s"]

    build = json.loads((LAYERS / f"{STEM}_build.json").read_text(encoding="utf-8"))
    surf = Surface(mode=build["mode"], engine=build["engine"], target=build["category"],
                   aggregation=build.get("aggregation", CATEGORY_COST_SELECTED),
                   horizon_s=float(build["horizon_s"]),
                   seconds=np.load(LAYERS / f"{STEM}.npy").astype(np.float64),
                   reason=np.load(LAYERS / f"{STEM}_reason.npy"),
                   min_possible_s=np.load(
                       LAYERS / f"{STEM}_min_possible_s.npy").astype(np.float64)).validate()

    grid = METRO.grid()
    ids, pts, total = structure_population(LAYERS.parent / METRO.name
                                           / "overture_buildings_accepted.parquet", grid)
    lon, lat = Transformer.from_crs(grid.crs, "EPSG:4326", always_xy=True).transform(
        pts[:, 0], pts[:, 1])
    # The exported raster's own tiling, which is what a browser lookup would use.
    col = np.floor((lon - west) / (east - west) * ncols).astype(np.int64)
    row = np.floor((north - lat) / (north - south) * nrows).astype(np.int64)
    inside = (col >= 0) & (col < ncols) & (row >= 0) & (row < nrows)
    # The source grid's tiling, which is what S3.1 measured.
    scol = np.floor((pts[:, 0] - grid.x_min) / grid.cell_m).astype(np.int64)
    srow = np.floor((grid.y_max - pts[:, 1]) / grid.cell_m).astype(np.int64)

    report = {
        "what_this_is": ("the cost of the EXPORT's own grid, which is a third tiling that S3.1 "
                         "never compared: a WGS84 raster whose pixels are not aligned with the "
                         "UTM cells the decision was made on"),
        "structures": int(len(pts)),
        "inside_the_exported_bounds": int(inside.sum()),
        "omitted_by_the_exported_bounds": int((~inside).sum()),
        "exported_shape": [nrows, ncols], "source_shape": list(surf.seconds.shape),
        "thresholds": {},
    }
    for t_min in THRESHOLDS_MIN:
        source = evaluate(Criterion(label=f"g{t_min}", mode=build["mode"],
                                    target=build["category"], kind="category",
                                    threshold_s=float(t_min) * 60.0), surf)[srow[inside],
                                                                           scol[inside]]
        shipped = wire.outcome_planes(value, status, threshold_min=t_min,
                                      horizon_s=horizon)[row[inside], col[inside]]
        moved = source != shipped
        names = {int(Outcome.PASS): "PASS", int(Outcome.FAIL): "FAIL",
                 int(Outcome.UNKNOWN): "UNKNOWN"}
        transitions = {}
        for a in names:
            for b in names:
                n = int(((source == a) & (shipped == b)).sum())
                if n and a != b:
                    transitions[f"{names[a]}->{names[b]}"] = n
        report["thresholds"][str(t_min)] = {
            "compared": int(inside.sum()), "moved": int(moved.sum()),
            "moved_rate": float(moved.sum()) / float(inside.sum()),
            "transitions": transitions}

    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"structures {report['structures']:,}, inside the exported bounds "
          f"{report['inside_the_exported_bounds']:,}, omitted "
          f"{report['omitted_by_the_exported_bounds']:,}")
    for t_min, row_ in report["thresholds"].items():
        print(f"  T={t_min:>2} min: {row_['moved']:,} of {row_['compared']:,} "
              f"({row_['moved_rate']:.2%}) move between the source grid and the shipped raster"
              f"   {row_['transitions']}")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
