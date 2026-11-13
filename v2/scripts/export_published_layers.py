"""Export the **published** layers in `published-v2` for the browser — S3.5's export half.

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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
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
        if not (LAYERS / f"{stem}.npy").exists():
            print(f"  skipping {stem}: not on disk")
            continue
        surf, build = load_surface(stem)
        value, status = wire.encode_planes(surf)
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
        entries.append({
            "id": stem, "label": label, "engine": build["engine"], "mode": build["mode"],
            "category": build["category"], "cell_m": cell_m,
            "horizon_s": surf.horizon_s,
            "value_file": f"{stem}.value.bin", "status_file": f"{stem}.status.bin",
            "source_shape": list(value.shape),
        })
        sizes.append({
            "id": stem,
            "raw_bytes": len(vb) + len(sb),
            "deflated_value": deflated(vb), "deflated_status": deflated(sb),
            "deflated_total": deflated(vb) + deflated(sb),
            "v1_raw_bytes": len(vb),
            "v1_deflated": deflated(vb),
            "status_counts": {wire.STATUS_CODES[int(c)]: int(n)
                              for c, n in zip(*np.unique(s, return_counts=True))},
        })

    if not entries:
        raise SystemExit("nothing to export")

    manifest = {
        "encoding": wire.ENCODING,
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
    print(f"\n{'layer':38s} {'raw':>10s} {'deflated':>10s} {'v1 defl.':>10s} {'ratio':>6s}")
    for s in sizes:
        print(f"{s['id']:38s} {s['raw_bytes']:>10,} {s['deflated_total']:>10,} "
              f"{s['v1_deflated']:>10,} {s['deflated_total'] / s['v1_deflated']:>6.2f}x")
    for s in sizes:
        print(f"\n{s['id']} status plane: {s['status_counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
