"""What the **shipped** disclosure is, which is not what step 8 published. Codex pass 48 §B.

Step 8's headline — 7,271 of 80,067 included structures at *T* = 10, 9.1% — is measured on the
source UTM grid. The browser never receives that grid. It receives the 514 × 643 WGS84 raster, and
MapLibre then places that raster's rows linearly in Mercator while the raster's own rows are linear
in latitude. `s3-5-export-regrid.json` already measured that 2.1% of structures change **verdict**
across the first of those steps. Nobody had measured what either step does to the **disclosure**,
and the commit that published the plane reported a source-grid figure as though it were shipped.

Two measurements, because they answer different questions.

**Reprojection fidelity** is about cells. The export reports `flagged_cells: 57,193` where the
source raster holds 57,175, and the only post-reprojection check looks for a flag where the status
is not OK — so a *dropped* flag passes it silently, a clear flag being no assertion. The net being
+18 says nothing about the gross. This reports the gross in both directions, how many source cells
the destination grid never samples at all, and — the question that decides whether the triple is
even coherent — whether each destination cell's value, status and flag come from **one** source
cell or from three independent nearest lookups.

**Shipped disclosure** is about households. One structure population read three ways: at its cell
in the source grid, at its pixel in the shipped raster, and at the row MapLibre actually samples.
It reports the share at each, and the gross movement between them, because an aggregate that
survives a re-tiling and a set of households that does not are different facts and the report owes
both.

Reads the published surface, the shipped planes and the structure population. **No graph.**

    v2/.venv/Scripts/python.exe scripts/measure_shipped_disclosure.py
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np
from pyproj import Transformer
from rasterio.transform import from_bounds
from rasterio.warp import Resampling, reproject

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from export_published_layers import (load_route_flag, load_surface,       # noqa: E402
                                     reproject_plane, source_transform)
from locfinder import wire                                               # noqa: E402
from locfinder.measure.frames import structure_population                # noqa: E402
from locfinder.metros import get_metro                                   # noqa: E402
from locfinder.status import (Criterion, Outcome, evaluate)              # noqa: E402

V2 = pathlib.Path(__file__).resolve().parents[1]
LAYERS = V2 / "data" / "layers"
PUBLISHED = V2 / "spikes" / "g3-render" / "fixtures" / "published"
METRO = get_metro()
THRESHOLDS_MIN = (10, 15, 25, 45)
STEM = "own_triangle_grocery_walk"
ARTIFACT = V2.parent / "docs" / "experiments" / "s3-8-shipped-disclosure.json"


def mercator_y(lat: np.ndarray) -> np.ndarray:
    phi = np.radians(np.clip(lat, -85.05112878, 85.05112878))
    return np.log(np.tan(np.pi / 4 + phi / 2))


def mercator_rows(lat, north, south, nrows) -> np.ndarray:
    """The texture row MapLibre samples, which is linear in Mercator *y*, not in latitude."""
    yn, ys = mercator_y(np.array([north])), mercator_y(np.array([south]))
    return np.floor((yn - mercator_y(lat)) / (yn - ys) * nrows).astype(np.int64)


def fidelity(value, status, flag, transform, crs, bounds, nrows, ncols, shipped_flag) -> dict:
    """The gross reprojection accounting, and whether the shipped triple is one source cell's."""
    def fwd(plane, fill):
        return reproject_plane(plane, transform, crs, src_fill=fill, dst_fill=fill,
                               bounds=bounds, nrows=nrows, ncols=ncols)

    # Which source cell each destination cell samples, carried through as three uint8 planes.
    # Coverage travels separately because 255 is a legal byte of an index.
    idx = np.arange(value.size, dtype=np.uint32).reshape(value.shape)
    parts = [fwd(((idx >> s) & 0xFF).astype(np.uint8), 0).astype(np.uint32) for s in (0, 8, 16)]
    covered = fwd(np.ones(value.shape, np.uint8), 0) == 1
    src_of_dst = parts[0] | (parts[1] << 8) | (parts[2] << 16)

    uniq, counts = np.unique(src_of_dst[covered], return_counts=True)
    seen = np.zeros(value.size, dtype=bool)
    seen[uniq] = True
    flat_flag = flag.ravel() == wire.ROUTE_RESTRICTED
    flat_ok = status.ravel() == wire.OK

    dv, ds, df = (fwd(value, wire.VALUE_NONE), fwd(status, wire.OUTSIDE),
                  fwd(flag, wire.ROUTE_CLEAR))
    s = src_of_dst[covered]
    same = ((dv[covered] == value.ravel()[s]) & (ds[covered] == status.ravel()[s])
            & (df[covered] == flag.ravel()[s]))

    def back(dst_plane, fill):
        o = np.full(value.shape, fill, dtype=np.uint8)
        reproject(source=np.ascontiguousarray(dst_plane, dtype=np.uint8), destination=o,
                  src_transform=from_bounds(*bounds, ncols, nrows), src_crs="EPSG:4326",
                  src_nodata=fill, dst_transform=transform, dst_crs=crs, dst_nodata=fill,
                  resampling=Resampling.nearest)
        return o

    rv, rs, rf = (back(dv, wire.VALUE_NONE), back(ds, wire.OUTSIDE), back(df, wire.ROUTE_CLEAR))
    lost = (flag == wire.ROUTE_RESTRICTED) & (rf == wire.ROUTE_CLEAR)
    gained = (flag == wire.ROUTE_CLEAR) & (rf == wire.ROUTE_RESTRICTED)

    out = {
        "what_this_measures": ("cells, not households: what the re-tiling does to the planes "
                              "themselves"),
        "source_cells": int(value.size), "destination_cells": nrows * ncols,
        "destination_cells_covered": int(covered.sum()),
        "distinct_source_cells_sampled": int(uniq.size),
        # "Never sampled" means no destination cell CENTRE falls in it. It is not a count of
        # households that lose a disclosure: a household in such a cell reads whichever pixel
        # covers its coordinate, and that pixel carries a neighbouring cell's complete answer.
        "source_cells_never_sampled": int(value.size - uniq.size),
        "source_cells_sampled_more_than_once": int((counts > 1).sum()),
        "largest_duplication": int(counts.max()),
        "flagged_source_cells": int(flat_flag.sum()),
        "flagged_source_cells_never_sampled": int((flat_flag & ~seen).sum()),
        "ok_source_cells_never_sampled": int((flat_ok & ~seen).sum()),
        "destination_flagged_cells": int((df == wire.ROUTE_RESTRICTED).sum()),
        "shipped_flagged_cells": int((shipped_flag == wire.ROUTE_RESTRICTED).sum()),
        "shipped_plane_matches_recomputed": bool(shipped_flag.tobytes() == df.tobytes()),
        "destination_cells_whose_triple_is_one_source_cell": int(same.sum()),
        "destination_cells_whose_triple_is_mixed": int((~same).sum()),
        "what_zero_mixed_means": (
            "every shipped cell's minutes, status and flag agree with ONE source cell's, so the "
            "re-tiling does not hand a household a time whose disclosure describes a different "
            "journey. Pass 48 narrowed the strength of this: three warped byte planes can in "
            "principle recombine into a valid index, so a zero here is strong evidence and not a "
            "proof. The reason to EXPECT it is that the three reprojections share geometry, "
            "dimensions, resampling and fill, which makes a common sampled cell structural rather "
            "than lucky; the measurement confirms the expectation holds on this grid pair"),
        "round_trip_value_changed": int((value != rv).sum()),
        "round_trip_status_changed": int((status != rs).sum()),
        "round_trip_flag_changed": int((flag != rf).sum()),
        "round_trip_flags_dropped": int(lost.sum()),
        "round_trip_flags_raised": int(gained.sum()),
        "round_trip_flags_dropped_where_status_stayed_ok": int(
            (lost & (status == wire.OK) & (rs == wire.OK)).sum()),
        "round_trip_flags_raised_where_status_stayed_ok": int(
            (gained & (status == wire.OK) & (rs == wire.OK)).sum()),
        "round_trip_status_ok_lost": int(((status == wire.OK) & (rs != wire.OK)).sum()),
        "round_trip_status_ok_gained": int(((status != wire.OK) & (rs == wire.OK)).sum()),
        "why_the_round_trip_is_not_a_household_figure": (
            "it bounds nothing. Reprojecting back applies a second nearest lookup, which can undo "
            "an outward error, introduce a new one, or miss a disagreement away from a cell "
            "centre. Pass 48's counterexample: two source cells re-tiled to three and back "
            "restore every source value EXACTLY while a coordinate at 0.9 still reads the wrong "
            "cell. So these figures describe the composition of two resamplings at cell centres "
            "and nothing about households. The structure figures below are the household ones, "
            "and they come from the forward comparison -- source cell against shipped pixel at "
            "each structure's own coordinate"),
    }
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=pathlib.Path, default=ARTIFACT)
    args = ap.parse_args(argv)

    man = json.loads((PUBLISHED / "manifest.json").read_text(encoding="utf-8"))
    nrows, ncols = man["nrows"], man["ncols"]
    west, south, east, north = man["bounds_wgs84"]
    entry = next(l for l in man["layers"] if l["id"] == STEM)
    value_shipped = np.frombuffer((PUBLISHED / entry["value_file"]).read_bytes(),
                                  dtype=np.uint8).reshape(nrows, ncols)
    status_shipped = np.frombuffer((PUBLISHED / entry["status_file"]).read_bytes(),
                                   dtype=np.uint8).reshape(nrows, ncols)
    flag_shipped = np.frombuffer((PUBLISHED / entry["flag_file"]).read_bytes(),
                                 dtype=np.uint8).reshape(nrows, ncols)
    horizon = entry["horizon_s"]

    surf, build = load_surface(STEM)
    value, status = wire.encode_planes(surf)
    raw_flag = load_route_flag(STEM, value.shape, surf.horizon_s)
    if raw_flag is None:
        raise SystemExit(f"{STEM} carries no flag raster, so there is no disclosure to measure")
    flag = wire.encode_route_flag(raw_flag, status)
    transform, crs = source_transform(build, value.shape)
    e = METRO.evaluation
    bounds = (e.west, e.south, e.east, e.north)

    report = {
        "what_this_is": ("what the SHIPPED disclosure is, as against the source-grid figure step "
                         "8 published: the re-tiling and MapLibre's placement each move which "
                         "pixel a structure reads"),
        "source_shape": list(value.shape), "shipped_shape": [nrows, ncols],
        "reprojection_fidelity": fidelity(value, status, flag, transform, crs, bounds,
                                          nrows, ncols, flag_shipped),
    }

    grid = METRO.grid()
    _ids, pts, _total = structure_population(
        LAYERS.parent / METRO.name / "overture_buildings_accepted.parquet", grid)
    lon, lat = Transformer.from_crs(grid.crs, "EPSG:4326", always_xy=True).transform(
        pts[:, 0], pts[:, 1])
    col = np.floor((lon - west) / (east - west) * ncols).astype(np.int64)
    row = np.floor((north - lat) / (north - south) * nrows).astype(np.int64)
    inside = (col >= 0) & (col < ncols) & (row >= 0) & (row < nrows)
    mrow = np.clip(mercator_rows(lat, north, south, nrows), 0, nrows - 1)
    scol = np.clip(np.floor((pts[:, 0] - grid.x_min) / grid.cell_m).astype(np.int64),
                   0, value.shape[1] - 1)
    srow = np.clip(np.floor((grid.y_max - pts[:, 1]) / grid.cell_m).astype(np.int64),
                   0, value.shape[0] - 1)

    report["structures"] = int(len(pts))
    report["inside_the_shipped_bounds"] = int(inside.sum())
    report["omitted_by_the_shipped_bounds"] = int((~inside).sum())
    report["why_the_source_figures_here_differ_from_step_8s"] = (
        "step 8 counted all 512,633 structures and this counts the "
        f"{int(inside.sum()):,} inside the shipped bounds, because the other "
        f"{int((~inside).sum()):,} have no shipped pixel to compare against")
    report["thresholds"] = {}

    src_flag_bool = raw_flag.astype(bool)
    for t_min in THRESHOLDS_MIN:
        crit = Criterion(label=f"g{t_min}", mode=build["mode"], target=build["category"],
                         kind="category", threshold_s=float(t_min) * 60.0)
        src_inc = np.asarray(evaluate(crit, surf)) == np.int8(Outcome.PASS)
        ship_out = wire.outcome_planes(value_shipped, status_shipped, threshold_min=t_min,
                                       horizon_s=horizon)
        ship_inc = np.asarray(ship_out) == np.int8(Outcome.PASS)
        ship_disc = wire.disclosed_restricted(flag_shipped, ship_out)

        s_inc, s_flag = src_inc[srow[inside], scol[inside]], src_flag_bool[srow[inside],
                                                                          scol[inside]]
        p_inc, p_flag = ship_inc[row[inside], col[inside]], ship_disc[row[inside], col[inside]]
        m_inc, m_flag = ship_inc[mrow[inside], col[inside]], ship_disc[mrow[inside], col[inside]]

        def pair(inc, fl):
            n = int(inc.sum())
            d = int((inc & fl).sum())
            return {"included": n, "disclosed": d,
                    "share_of_included": (d / n) if n else None}

        src_d = s_inc & s_flag
        ship_d = p_inc & p_flag
        plc_d = m_inc & m_flag
        report["thresholds"][str(t_min)] = {
            "on_the_source_grid": pair(s_inc, s_flag),
            "at_the_shipped_pixel": pair(p_inc, p_flag),
            "at_the_row_maplibre_places": pair(m_inc, m_flag),
            "disclosure_lost_source_to_shipped": int((src_d & ~ship_d).sum()),
            "disclosure_gained_source_to_shipped": int((ship_d & ~src_d).sum()),
            "disclosure_lost_shipped_to_placed": int((ship_d & ~plc_d).sum()),
            "disclosure_gained_shipped_to_placed": int((plc_d & ~ship_d).sum()),
            "included_as_shipped_flagged_at_source_but_unflagged_as_shipped":
                int((p_inc & s_flag & ~p_flag).sum()),
        }

    report["which_figure_a_report_may_quote"] = (
        "at_the_shipped_pixel. Pass 46 F2 settled that the unit is the cell the product answers "
        "for; the cell the product answers for is now the SHIPPED pixel, not the source cell. The "
        "source figure is model sensitivity and the MapLibre figure is the placement's own cost")
    report["what_this_does_not_say"] = (
        "that any household receives a disclosure. The plane ships and the decoder counts it; no "
        "interface displays a flagged answer, because the per-criterion card is unbuilt")

    args.out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    f = report["reprojection_fidelity"]
    print(f"reprojection: {f['source_cells_never_sampled']:,} of {f['source_cells']:,} source "
          f"cells are never sampled, {f['flagged_source_cells_never_sampled']:,} of them flagged; "
          f"{f['destination_cells_whose_triple_is_mixed']:,} shipped cells have a mixed triple")
    print(f"\n{'T':>4}  {'source':>18}  {'shipped':>18}  {'placed':>18}  {'lost':>6} {'gained':>6}")
    for t, r in report["thresholds"].items():
        def fmt(d):
            return f"{d['disclosed']:,}/{d['included']:,} {d['share_of_included']:.2%}"
        print(f"{t:>4}  {fmt(r['on_the_source_grid']):>18}  "
              f"{fmt(r['at_the_shipped_pixel']):>18}  "
              f"{fmt(r['at_the_row_maplibre_places']):>18}  "
              f"{r['disclosure_lost_source_to_shipped']:>6,} "
              f"{r['disclosure_gained_source_to_shipped']:>6,}")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
