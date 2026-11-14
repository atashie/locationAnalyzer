"""Export the **published** layers in `published-v3` for the browser — S3.5's export half.

**The route-flag plane is optional and its absence means "this layer does not disclose".** A layer
carries one only when `<stem>_restricted_route.npy` sits beside its surface triple, written by
`scripts/flag_restricted_routes.py --write-raster`. A manifest that declares no `flag_file`
discloses nothing about routes, which is a different statement from "no route is restricted" — and
the decoder reports `restrictedIncludedCount: null` rather than 0 so a reader cannot confuse them.

`spikes/g3-render/export_layers.py` exports the G1 engine-comparison tifs and has two defects S3.5
names: it discovers layers by `<engine>_<category>_<mode>`, so it **omits**
`own_triangle_grocery_walk.tif` — the actual product layer — and it targets the 401 × 550 Phase 0
slice rather than the 514 × 643 Triangle footprint. Those two together mean the browser has never
once rendered the layer the product publishes.

This does not patch that exporter. It is a different job: that one compares engines from minute
rasters, and a minute raster **cannot** carry the status plane this format needs, because the
reason and the bound were discarded before the tif was written. This reads the surface triple that
`build_layer_surface` produced — seconds, reason and `min_possible_s` — and writes both planes.

**Nearest resampling for both planes, and no interpolation of anything.** A status code is a name,
so averaging two of them is meaningless; a minute is a decision input, so averaging two of them
publishes a region nobody computed. Pixels the source does not cover become `OUTSIDE` in the status
plane, which decodes to UNKNOWN — never to a known failure, and never to a travel time.

Writes `fixtures/published/<id>.value.bin`, `<id>.status.bin` and `manifest.json`, and reports the
deflated size of each, which is S3.5's transfer-size question.

    python scripts/export_published_layers.py
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import zlib

import numpy as np
import rasterio
from rasterio.transform import from_bounds, from_origin
from rasterio.warp import Resampling, reproject

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from locfinder import wire                                      # noqa: E402
from locfinder.metros import get_metro                          # noqa: E402
from locfinder.status import CATEGORY_COST_SELECTED, Surface    # noqa: E402

V2 = pathlib.Path(__file__).resolve().parents[1]
LAYERS = V2 / "data" / "layers"
OUT = V2 / "spikes" / "g3-render" / "fixtures" / "published"
METRO = get_metro()

#: Every published surface, by the stem of its `.npy` triple. The product layer first.
SOURCES = [
    ("own_triangle_grocery_walk", "Grocery, walk (100 m)", 100.0),
    ("own_triangle_grocery_walk_cell200", "Grocery, walk (200 m candidate)", 200.0),
]


def load_route_flag(stem: str, shape, horizon_s: float,
                    fingerprint: str | None = None) -> np.ndarray | None:
    """The per-cell route flag, if this layer bundle carries one.

    Returning `None` is meaningful: it is "this layer does not disclose", and every consumer has to
    keep it distinct from a plane of zeros.

    Pass 48: the horizon is checked here because the 5,145-cell defect WAS a horizon disagreement
    between this raster and the surface it describes, and `wire.encode_route_flag` catches only one
    direction of it. A surface horizon SMALLER than the flag's leaves flags where the status is no
    longer OK, which that invariant refuses. A LARGER one leaves cells newly OK whose flag was
    never computed, so they ship ROUTE_CLEAR -- and a clear flag asserts nothing, which is exactly
    why nothing downstream can notice. The pairing is therefore checked where the pairing is made.
    """
    path = LAYERS / f"{stem}_restricted_route.npy"
    if not path.exists():
        return None
    flag = np.load(path)
    if flag.shape != tuple(shape):
        raise SystemExit(
            f"{path.name} is {flag.shape} and the surface is {tuple(shape)}; refusing to publish a "
            "disclosure that does not describe this layer")
    meta_path = LAYERS / f"{stem}_restricted_route_build.json"
    recorded = None
    if meta_path.exists():
        recorded = json.loads(meta_path.read_text(encoding="utf-8")).get("horizon_s")
    if recorded is None:
        # The raster in the repository predates the field. Accepting it keeps this a check rather
        # than a rebuild, but the gap is named rather than passed over in silence.
        print(f"  WARNING: {meta_path.name} records no horizon_s, so the flag cannot be checked "
              f"against the surface's {horizon_s:g} s. Rebuild it with "
              f"scripts/flag_restricted_routes.py --write-raster to close this.")
    elif float(recorded) != float(horizon_s):
        raise SystemExit(
            f"{path.name} was computed with horizon {float(recorded):g} s and the surface applies "
            f"{float(horizon_s):g} s. A smaller surface horizon leaves flags on journeys the layer "
            "no longer publishes; a larger one leaves newly published journeys silently unflagged. "
            "Rebuild the flag raster against this surface.")
    # Pass 48 F3: and WHICH surface. Shape, aggregate count and `flag implies OK` all accepted a
    # plane with one flag flipped down and one up, because a clear flag is not an assertion and
    # cannot be checked against anything. Provenance can be.
    if fingerprint is not None and meta_path.exists():
        stated = json.loads(meta_path.read_text(encoding="utf-8")).get("surface_fingerprint")
        if stated is None:
            print(f"  WARNING: {meta_path.name} records no surface_fingerprint, so this flag "
                  "cannot be tied to the surface it describes. Rebuild it with "
                  "scripts/flag_restricted_routes.py --write-raster to close this.")
        elif stated != fingerprint:
            raise SystemExit(
                f"{path.name} was computed against surface {stated} and this surface is "
                f"{fingerprint}. The flag describes a different layer, or the plane has been "
                "altered since it was written. A clear flag asserts nothing, so nothing else in "
                "this pipeline can notice. Rebuild the flag raster against this surface.")
    return flag


def load_surface(stem: str) -> tuple[Surface, dict]:
    build = json.loads((LAYERS / f"{stem}_build.json").read_text(encoding="utf-8"))
    seconds = np.load(LAYERS / f"{stem}.npy").astype(np.float64)
    reason = np.load(LAYERS / f"{stem}_reason.npy")
    lower = np.load(LAYERS / f"{stem}_min_possible_s.npy").astype(np.float64)
    surf = Surface(mode=build["mode"], engine=build["engine"], target=build["category"],
                   aggregation=build.get("aggregation", CATEGORY_COST_SELECTED),
                   horizon_s=float(build["horizon_s"]), seconds=seconds, reason=reason,
                   min_possible_s=lower).validate()
    return surf, build


def source_transform(build: dict, shape: tuple[int, int]):
    """The source grid's transform, from the build record rather than from a tif.

    `build.json` carries the origin and cell size for a layer this script wrote; the published
    100 m layer predates that and is reconstructed from the metro grid instead. Both are checked
    against the array's shape, because a transform that disagrees with its array silently places
    every cell in the wrong place.
    """
    if {"x_min", "y_max", "cell_m"} <= build.keys():
        x_min, y_max, cell_m = build["x_min"], build["y_max"], build["cell_m"]
        crs = build.get("crs", METRO.crs)
        # Pass 43 F8: this branch used to take the origin on trust. A transposed 83,076-cell
        # triple passed and would have exported under the wrong footprint -- silently, because a
        # transform that disagrees with its array moves every cell rather than failing.
        # Pass 44 F6: `None not in recorded` skipped the WHOLE guard when either dimension was
        # missing, so a record explicitly saying `nrows=258` accepted a 322-row array once
        # `ncols` was lost. Each supplied dimension is now checked on its own.
        for key, got in (("nrows", shape[0]), ("ncols", shape[1])):
            recorded = build.get(key)
            if recorded is not None and int(recorded) != int(got):
                raise SystemExit(
                    f"the build record says {key}={recorded} and the array has {got}; refusing "
                    "to export it under a transform that does not describe it")
    else:
        grid = METRO.grid()
        x_min, y_max, cell_m, crs = grid.x_min, grid.y_max, grid.cell_m, grid.crs
        if (grid.nrows, grid.ncols) != shape:
            raise SystemExit(
                f"the metro grid is {grid.nrows}x{grid.ncols} and the array is {shape[0]}x"
                f"{shape[1]}; refusing to guess a transform for it")
    return from_origin(x_min, y_max, cell_m, cell_m), crs


def reproject_plane(plane: np.ndarray, transform, crs, *, src_fill: int, dst_fill: int,
                    bounds, nrows: int, ncols: int) -> np.ndarray:
    dst = np.full((nrows, ncols), dst_fill, dtype=np.uint8)
    reproject(source=np.ascontiguousarray(plane, dtype=np.uint8), destination=dst,
              src_transform=transform, src_crs=crs, src_nodata=src_fill,
              dst_transform=from_bounds(*bounds, ncols, nrows),
              dst_crs="EPSG:4326", dst_nodata=dst_fill, resampling=Resampling.nearest)
    return dst


def deflated(data: bytes) -> int:
    return len(zlib.compress(data, 9))


def v1_plane(value: np.ndarray, status: np.ndarray) -> np.ndarray:
    """The single plane v1 would have written: minutes where OK, `255` everywhere else.

    Pass 43 F5: the first version compared v2's two planes against **v2's own value plane**, which
    carries a lower bound at every missing cell. v1 stored `NODATA` there, and a constant
    compresses far better than a bound, so the baseline was too large and the reported overhead
    too small -- 9% where the true figure is 18%.
    """
    return np.where(status == wire.OK, value, 255).astype(np.uint8)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--candidates", action="store_true",
                    help="also export the rejected 200 m candidate. Pass 43 F4: every manifest "
                         "entry starts enabled in the page, so shipping the candidate beside the "
                         "product made the default answer the INTERSECTION of two versions of one "
                         "criterion, which removed 4,022 passing pixels at the default threshold")
    ap.add_argument("--nrows", type=int, default=514)
    ap.add_argument("--ncols", type=int, default=643)
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    args = ap.parse_args(argv)

    e = METRO.evaluation
    bounds = (e.west, e.south, e.east, e.north)
    args.out.mkdir(parents=True, exist_ok=True)

    entries = []
    sizes = []
    for stem, label, cell_m in SOURCES:
        if cell_m != 100.0 and not args.candidates:
            continue
        if not (LAYERS / f"{stem}.npy").exists():
            print(f"  skipping {stem}: not on disk")
            continue
        surf, build = load_surface(stem)
        value, status = wire.encode_planes(surf)
        raw_flag = load_route_flag(
            stem, value.shape, surf.horizon_s,
            fingerprint=wire.surface_fingerprint(surf.seconds, surf.reason))
        flag = None if raw_flag is None else wire.encode_route_flag(raw_flag, status)
        transform, crs = source_transform(build, value.shape)

        # The value plane's fill is VALUE_NONE, which carries no time and no bound. The status
        # plane's fill is OUTSIDE, which is the thing v1 could not say: a pixel this export covers
        # and the source did not.
        v = reproject_plane(value, transform, crs, src_fill=wire.VALUE_NONE,
                            dst_fill=wire.VALUE_NONE, bounds=bounds,
                            nrows=args.nrows, ncols=args.ncols)
        s = reproject_plane(status, transform, crs, src_fill=wire.OUTSIDE,
                            dst_fill=wire.OUTSIDE, bounds=bounds,
                            nrows=args.nrows, ncols=args.ncols)
        # A status code that survived reprojection must still be one we define. Nearest never
        # invents a value, so this is a guard against a future resampling change, not a live path.
        unknown = sorted(set(np.unique(s).tolist()) - set(wire.STATUS_CODES))
        if unknown:
            raise SystemExit(f"{stem}: reprojection produced undefined status codes {unknown}")

        vb, sb = v.tobytes(), s.tobytes()
        (args.out / f"{stem}.value.bin").write_bytes(vb)
        (args.out / f"{stem}.status.bin").write_bytes(sb)
        entry = {
            "id": stem, "label": label, "engine": build["engine"], "mode": build["mode"],
            "category": build["category"], "cell_m": cell_m,
            "horizon_s": surf.horizon_s,
            "value_file": f"{stem}.value.bin", "status_file": f"{stem}.status.bin",
            "source_shape": list(value.shape),
        }
        fb = None
        if flag is not None:
            # Uncovered pixels become ROUTE_CLEAR, which is safe only because the status plane
            # marks them OUTSIDE: a zero flag at a cell with no published answer discloses
            # nothing, and `wire.encode_route_flag` enforces that a SET flag implies status OK.
            fplane = reproject_plane(flag, transform, crs, src_fill=wire.ROUTE_CLEAR,
                                     dst_fill=wire.ROUTE_CLEAR, bounds=bounds,
                                     nrows=args.nrows, ncols=args.ncols)
            bad = (fplane == wire.ROUTE_RESTRICTED) & (s != wire.OK)
            if bad.any():
                raise SystemExit(
                    f"{stem}: {int(bad.sum())} reprojected cells carry a route flag where the "
                    "status is not OK; nearest resampling moved the two planes apart")
            fb = fplane.tobytes()
            (args.out / f"{stem}.flag.bin").write_bytes(fb)
            entry["flag_file"] = f"{stem}.flag.bin"
            entry["flagged_cells"] = int((fplane == wire.ROUTE_RESTRICTED).sum())
        entries.append(entry)
        sizes.append({
            "id": stem,
            "raw_bytes": len(vb) + len(sb) + (len(fb) if fb else 0),
            "deflated_value": deflated(vb), "deflated_status": deflated(sb),
            "deflated_flag": deflated(fb) if fb else None,
            "deflated_total": deflated(vb) + deflated(sb) + (deflated(fb) if fb else 0),
            "v1_raw_bytes": len(vb),
            "v1_deflated": deflated(v1_plane(v, s).tobytes()),
            "status_counts": {wire.STATUS_CODES[int(c)]: int(n)
                              for c, n in zip(*np.unique(s, return_counts=True))},
        })

    if not entries:
        raise SystemExit("nothing to export")

    manifest = {
        "encoding": wire.ENCODING,
        "discloses_restricted_routes": any("flag_file" in e for e in entries),
        "what_an_absent_flag_plane_means": (
            "that the layer does not disclose, NOT that no route is restricted. A decoder must "
            "report that distinction rather than defaulting to clean"),
        "route_flag_codes": {str(k): v for k, v in wire.ROUTE_FLAG_CODES.items()},
        "nrows": args.nrows, "ncols": args.ncols,
        "bounds_wgs84": list(bounds),
        "units": "minutes",
        "value_means": ("travel time where status is OK; a LOWER BOUND on it where status is "
                        "OFF_NETWORK, BEYOND_HORIZON or NO_PATH; nothing otherwise"),
        "status_codes": {str(k): v for k, v in wire.STATUS_CODES.items()},
        "value_none": wire.VALUE_NONE, "value_max": wire.VALUE_MAX,
        "generator": "v2/scripts/export_published_layers.py",
        "synthetic": False,
        "note": ("Reprojected from UTM 17N (EPSG:32617) to a WGS84 lon/lat grid with "
                 "rasterio.warp.reproject, NEAREST for both planes: a status code is a name and a "
                 "minute is a decision input, and averaging either publishes something nobody "
                 "computed. Uncovered pixels are OUTSIDE, which decodes to UNKNOWN."),
        "layers": entries,
        "transfer_bytes": sizes,
    }
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"wrote {len(entries)} layers to {args.out}")
    print(f"\n{'layer':34s} {'raw':>10s} {'deflated':>10s} {'of which flag':>14s} "
          f"{'v1 defl.':>10s} {'ratio':>6s}")
    for s in sizes:
        fl = f"{s['deflated_flag']:,}" if s["deflated_flag"] is not None else "-"
        print(f"{s['id']:34s} {s['raw_bytes']:>10,} {s['deflated_total']:>10,} {fl:>14s} "
              f"{s['v1_deflated']:>10,} {s['deflated_total'] / s['v1_deflated']:>6.2f}x")
    for s in sizes:
        print(f"\n{s['id']} status plane: {s['status_counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
