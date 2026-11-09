"""Re-encode the uint8 minute GeoTIFFs from the float seconds already on disk.

Run from `v2/`:
    uv run python scripts/reencode_minute_rasters.py            # report only
    uv run python scripts/reencode_minute_rasters.py --write     # overwrite the rasters

**Why this exists.** `grid.encode_minutes` changed from `rint` to `ceil` on 2026-11-09, so every
minute raster written before that encodes a different rule — one that differs by up to 30 s at every
threshold and is otherwise byte-compatible. The rasters live under `v2/data/`, which is gitignored,
so they do not travel with a clone and nothing in the repository can regenerate them except the
layer builders, which need the 670 MB `roads.graphml` and several minutes.

They do not need it. The **float seconds** are on disk beside every raster, and the minute raster is
a pure function of them, so re-encoding costs a second and no network. This script is committed
because an artifact that cannot be rebuilt from the repository is an artifact one cleanup away from
unrecoverable, and because the next encoding decision (30-second units, if a per-cell number is ever
displayed) will need exactly this operation again.

It **reports by default and writes only under `--write`**, and it refuses rather than guessing when
it cannot identify the grid a raster belongs to. The old raster's provenance tags are carried
across; `write_layer` stamps `encoding` itself.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import rasterio

from locfinder.grid import ENCODING, GridSpec, encode_minutes
from locfinder.metros import METROS
from locfinder.traveltime.layer import write_layer

LAYERS = Path("data/layers")


def grids_by_shape() -> dict[tuple[int, int], tuple[str, GridSpec]]:
    """Every grid this project has published on, keyed by raster shape.

    A raster is matched to its grid by shape, which is sound only because the shapes differ: the
    Phase 0 slice is 401 x 550 and the Triangle 514 x 643. The function asserts that rather than
    assuming it, because a future metro with a coincidentally equal shape would otherwise be
    silently reprojected into the wrong footprint.
    """
    out: dict[tuple[int, int], tuple[str, GridSpec]] = {}
    for name, metro in METROS.items():
        g = metro.grid()
        key = (g.nrows, g.ncols)
        if key in out:
            raise SystemExit(
                f"grids for {out[key][0]!r} and {name!r} are both {key}; shape no longer "
                "identifies a grid and this script needs an explicit mapping")
        out[key] = (name, g)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="overwrite the rasters in place")
    args = ap.parse_args()

    by_shape = grids_by_shape()
    tifs = sorted(LAYERS.glob("*.tif"))
    if not tifs:
        raise SystemExit(f"no rasters under {LAYERS}/")

    print(f"{'raster':<42} {'grid':<9} {'changed cells':>14} {'max shift':>10}  encoding was")
    changed_any = False
    for tif in tifs:
        npy = tif.with_suffix(".npy")
        if not npy.exists():
            print(f"{tif.name:<42} {'-':<9} {'SKIPPED':>14} {'-':>10}  "
                  f"no {npy.name} to re-encode from")
            continue
        seconds = np.load(npy).astype(np.float64)
        key = seconds.shape
        if key not in by_shape:
            print(f"{tif.name:<42} {'-':<9} {'REFUSED':>14} {'-':>10}  "
                  f"shape {key} matches no known grid")
            continue
        metro_name, grid = by_shape[key]

        with rasterio.open(tif) as src:
            old = src.read(1)
            tags = dict(src.tags())
        was = tags.pop("encoding", "minutes-rint-v0 (untagged)")
        new = encode_minutes(seconds)
        diff = old.astype(np.int16) != new.astype(np.int16)
        shift = int(np.abs(old.astype(np.int16) - new.astype(np.int16))[diff].max()) if diff.any() else 0
        print(f"{tif.name:<42} {metro_name:<9} {int(diff.sum()):>14,} {shift:>10}  {was}")
        if diff.any():
            changed_any = True
        if args.write:
            write_layer(tif, new, grid, tags=tags)

    print()
    if args.write:
        print(f"written, all tagged encoding={ENCODING}")
    elif changed_any:
        print(f"report only. Pass --write to overwrite these with encoding={ENCODING}.")
    else:
        print(f"report only; nothing would change (already {ENCODING}).")


if __name__ == "__main__":
    sys.exit(main())
