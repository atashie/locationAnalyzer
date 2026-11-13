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
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

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


def address_comparison(build, pts, inside, srow, scol, row, col, value, status, horizon):
    """Source, export and address, on one population, so the three can be compared rather than
    added. Pass 44 F4: re-tiling can correct a source-grid disagreement as easily as cause one.

    Costs a graph load, because the address answer is not in any artifact — it is this model
    evaluated at the structure's own coordinate, which is what `compare_candidate_grids.py` does.
    """
    import compare_candidate_grids as census

    idx, T, node_cost, reasons, meta = census.prepare()
    addr = census.answer_at(idx, T, node_cost, reasons,
                            pts[inside, 0], pts[inside, 1])
    surf = Surface(mode=build["mode"], engine=build["engine"], target=build["category"],
                   aggregation=build.get("aggregation", CATEGORY_COST_SELECTED),
                   horizon_s=float(build["horizon_s"]),
                   seconds=np.load(LAYERS / f"{STEM}.npy").astype(np.float64),
                   reason=np.load(LAYERS / f"{STEM}_reason.npy"),
                   min_possible_s=np.load(
                       LAYERS / f"{STEM}_min_possible_s.npy").astype(np.float64)).validate()
    out = {"graph": meta, "structures": int(inside.sum()), "thresholds": {}}
    for t_min in THRESHOLDS_MIN:
        crit = Criterion(label=f"g{t_min}", mode=build["mode"], target=build["category"],
                         kind="category", threshold_s=float(t_min) * 60.0)
        a = census.verdicts(addr[0], addr[1], addr[2], t_min)
        # `evaluate` returns Outcome codes and `verdicts` returns them too, so the three are
        # directly comparable; the export side is decoded from the planes.
        src = evaluate(crit, surf)[srow[inside], scol[inside]]
        exp = wire.outcome_planes(value, status, threshold_min=t_min,
                                  horizon_s=horizon)[row[inside], col[inside]]
        src_v_addr = int((src != a).sum())
        exp_v_addr = int((exp != a).sum())
        out["thresholds"][str(t_min)] = {
            "source_against_address": src_v_addr,
            "export_against_address": exp_v_addr,
            "export_against_source": int((src != exp).sum()),
            "retiling_corrected": int(((src != a) & (exp == a)).sum()),
            "retiling_broke": int(((src == a) & (exp != a)).sum()),
            "net_change": exp_v_addr - src_v_addr,
            "net_change_ratio": (exp_v_addr / src_v_addr) if src_v_addr else None,
        }
    return out


def mercator_y(lat: np.ndarray) -> np.ndarray:
    """Web Mercator northing, normalised the way MapLibre's projection does it."""
    rad = np.radians(np.asarray(lat, dtype=np.float64))
    return 0.5 - np.log(np.tan(np.pi / 4.0 + rad / 2.0)) / (2.0 * np.pi)


def mercator_rows(lat: np.ndarray, north: float, south: float, nrows: int) -> np.ndarray:
    """The texture row MapLibre samples, which is linear in MERCATOR y, not in latitude.

    Pass 44 F3: a canvas source inherits image-source placement, which converts its corners to
    Mercator coordinates; the texture then interpolates between those corners in Mercator space.
    The raster's own rows are linear in latitude, so the two disagree away from the middle of the
    image. This is an **analytical placement calculation from the pinned MapLibre 5.24.0 sources,
    not a screenshot measurement**, and MapLibre additionally rounds corner coordinates.
    """
    y0, y1 = mercator_y(np.array([north])), mercator_y(np.array([south]))
    frac = (mercator_y(lat) - y0) / (y1 - y0)
    return np.floor(frac * nrows).astype(np.int64)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=pathlib.Path, default=ARTIFACT)
    ap.add_argument("--with-address", action="store_true",
                    help="also evaluate each structure at its own coordinate, which costs a "
                         "graph load. Pass 44 F4: two similarly sized disagreement counts cannot "
                         "be added -- re-tiling can CORRECT a source-grid disagreement, and only "
                         "comparing both against the address answer says what the net change is")
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

    # How much of the raster the browser samples at a different row than the raster itself has.
    mrow = mercator_rows(lat, north, south, nrows)
    same_pixel = mrow == row
    report["maplibre_placement"] = {
        "what_this_is": ("an analytical calculation from the pinned MapLibre 5.24.0 canvas/image "
                         "source placement, NOT a screenshot: a canvas source converts its "
                         "corners to Mercator and interpolates the texture between them, while "
                         "the raster's rows are linear in latitude"),
        "structures_sampling_a_different_row": int((~same_pixel & inside).sum()),
        "max_row_shift": int(np.abs(mrow - row)[inside].max()),
        "thresholds": {},
    }
    for t_min in THRESHOLDS_MIN:
        decoded = wire.outcome_planes(value, status, threshold_min=t_min, horizon_s=horizon)
        by_raster = decoded[row[inside], col[inside]]
        mr = np.clip(mrow[inside], 0, nrows - 1)
        by_screen = decoded[mr, col[inside]]
        report["maplibre_placement"]["thresholds"][str(t_min)] = {
            "verdicts_differing_between_raster_row_and_placed_row":
                int((by_raster != by_screen).sum()),
        }

    if args.with_address:
        report["against_the_address_answer"] = address_comparison(
            build, pts, inside, srow, scol, row, col, value, status, horizon)

    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"structures {report['structures']:,}, inside the exported bounds "
          f"{report['inside_the_exported_bounds']:,}, omitted "
          f"{report['omitted_by_the_exported_bounds']:,}")
    for t_min, row_ in report["thresholds"].items():
        print(f"  T={t_min:>2} min: {row_['moved']:,} of {row_['compared']:,} "
              f"({row_['moved_rate']:.2%}) move between the source grid and the shipped raster"
              f"   {row_['transitions']}")
    mp = report["maplibre_placement"]
    print(f"\nMapLibre places the texture in Mercator, not latitude: "
          f"{mp['structures_sampling_a_different_row']:,} structures sample a different row "
          f"(max shift {mp['max_row_shift']})")
    for t_min, r in mp["thresholds"].items():
        print(f"  T={t_min:>2} min: "
              f"{r['verdicts_differing_between_raster_row_and_placed_row']:,} verdicts differ "
              f"between the raster row and the placed row")

    if args.with_address:
        print("\nagainst the address answer, on the same population:")
        for t_min, r in report["against_the_address_answer"]["thresholds"].items():
            print(f"  T={t_min:>2} min: source {r['source_against_address']:,} -> export "
                  f"{r['export_against_address']:,}  "
                  f"(re-tiling corrected {r['retiling_corrected']:,}, broke "
                  f"{r['retiling_broke']:,}, net {r['net_change']:+,}, "
                  f"x{r['net_change_ratio']:.3f})")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
