"""Does the UNKNOWN hatch actually mark the UNKNOWN cells? Measured on the PUBLISHED grid.

The owner reports that the grey diagonal striping is "problematic and should be rectified". That
is a product judgement and theirs to make. This script measures a separate, factual question that
the complaint exposed, and which nothing in the repository had measured:

    `worker.js:473` paints an UNKNOWN cell grey only where `(row + col) & 7 < 2`, and paints it
    `PX_OUT` -- fully transparent, byte-identical to an EXCLUDED cell -- everywhere else.

So the hatch marks at most 2 of every 8 diagonal positions. For a large contiguous UNKNOWN region
that reads as a texture, which is the design intent. For a small or thin one it can paint a single
grey dot, or nothing at all, and a region that gets nothing is indistinguishable on screen from a
confident "no". This measures how much of each kind there is.

`row` and `col` in that expression are the PUBLISHED WGS84 grid's indices (`p = r * ncols + c`
over `nrows=514`, `ncols=643`), so this reads `fixtures/published/*.bin` and not the UTM source
surfaces. Quoting a UTM figure at a question about painted pixels is the pass-56 error class.

LIMITATION, stated rather than papered over: this reports CELLS, not buildings. The buildings
raster exists only on the UTM grid, and the exporter's reprojection is nearest-neighbour, which
duplicates and drops cells and so does not conserve a count. Weighting these components by
buildings needs a building count computed on the published grid, which nothing produces yet.

Run from `v2/`:
    python scripts/measure_hatch_visibility.py
    python scripts/measure_hatch_visibility.py --layer own_triangle_park_walk --thresholds 15 20
"""
from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np
from scipy import ndimage

V2 = pathlib.Path(__file__).resolve().parent.parent
PUB = V2 / "spikes" / "g3-render" / "fixtures" / "published"

# worker.js, lines 73-75 and 97-101. Named here so a code and its meaning cannot drift apart.
S_OK, S_OFF_NETWORK, S_BEYOND_HORIZON, S_NO_PATH = 0, 1, 2, 3
S_LAYER_UNKNOWN, S_OUTSIDE, S_UNKNOWN_CAUSE = 4, 5, 6
HATCH_PERIOD_MASK = 7
HATCH_WIDTH = 2

O_PASS, O_FAIL, O_UNKNOWN = 0, 1, 2

WALK_LAYERS = ["own_triangle_park_walk", "own_triangle_grocery_walk", "own_triangle_school_walk"]
DEFAULT_THRESHOLDS = [5, 10, 15, 20, 30, 45, 60]


def outcome(status: np.ndarray, value: np.ndarray, threshold: int, horizon_s: float) -> np.ndarray:
    """`worker.js` outcomeFor, vectorised. Same branches, same order, same comparisons."""
    out = np.full(status.shape, -1, dtype=np.int8)
    ok = status == S_OK
    out[ok & (value <= threshold)] = O_PASS
    out[ok & (value > threshold)] = O_FAIL
    out[status == S_NO_PATH] = O_FAIL
    bh = status == S_BEYOND_HORIZON
    out[bh] = O_FAIL if horizon_s >= 60 * threshold else O_UNKNOWN
    off = status == S_OFF_NETWORK
    out[off & (value > threshold)] = O_FAIL
    out[off & (value <= threshold)] = O_UNKNOWN
    for code in (S_LAYER_UNKNOWN, S_OUTSIDE, S_UNKNOWN_CAUSE):
        out[status == code] = O_UNKNOWN
    if (out < 0).any():
        raise AssertionError("a cell got no outcome; status plane holds an undefined code")
    return out


def hatch_mask(nrows: int, ncols: int) -> np.ndarray:
    """The cells worker.js paints grey, for an UNKNOWN verdict: `(r + c) & 7 < 2`."""
    r = np.arange(nrows, dtype=np.int64)[:, None]
    c = np.arange(ncols, dtype=np.int64)[None, :]
    return ((r + c) & HATCH_PERIOD_MASK) < HATCH_WIDTH


def load(stem: str, nrows: int, ncols: int) -> tuple[np.ndarray, np.ndarray]:
    status = np.fromfile(PUB / f"{stem}.status.bin", dtype=np.uint8)
    value = np.fromfile(PUB / f"{stem}.value.bin", dtype=np.uint8)
    if status.size != nrows * ncols or value.size != nrows * ncols:
        raise AssertionError(f"{stem}: plane is {status.size} cells, manifest says {nrows*ncols}")
    return status.reshape(nrows, ncols), value.reshape(nrows, ncols).astype(np.int32)


def report(stem: str, label: str, status, value, horizon_s, hatch, thresholds) -> None:
    print(f"=== {label}  ({stem}) ===")
    codes = {k: int((status == k).sum()) for k in range(7) if (status == k).any()}
    print(f"  status codes present: {codes}")
    print(f"  {'limit':>5} {'UNKNOWN':>9} {'painted':>9} {'invisible':>10} {'% painted':>10}   "
          f"{'blobs':>7} {'wholly invisible':>17} {'cells in those':>15}")
    for t in thresholds:
        unk = outcome(status, value, t, horizon_s) == O_UNKNOWN
        n_unk = int(unk.sum())
        if n_unk == 0:
            print(f"  {t:>5} {0:>9}")
            continue
        painted = unk & hatch
        n_painted = int(painted.sum())
        # 8-connectivity: what a reader perceives as one grey patch.
        lab, n_blobs = ndimage.label(unk, structure=np.ones((3, 3), dtype=bool))
        sizes = np.bincount(lab.ravel())[1:]
        painted_per = np.bincount(lab[painted].ravel(), minlength=n_blobs + 1)[1:]
        dark = painted_per == 0
        print(f"  {t:>5} {n_unk:>9,} {n_painted:>9,} {n_unk - n_painted:>10,} "
              f"{n_painted / n_unk * 100:>9.2f}%   {n_blobs:>7,} "
              f"{int(dark.sum()):>17,} {int(sizes[dark].sum()):>15,}")
    # The shape of the UNKNOWN regions, at the layer's own default threshold, is what decides
    # whether a hatch can work at all.
    print()
    return None


def shape_detail(label: str, status, value, horizon_s, hatch, threshold: int) -> None:
    unk = outcome(status, value, threshold, horizon_s) == O_UNKNOWN
    if not unk.any():
        return
    lab, n_blobs = ndimage.label(unk, structure=np.ones((3, 3), dtype=bool))
    sizes = np.bincount(lab.ravel())[1:]
    painted_per = np.bincount(lab[unk & hatch].ravel(), minlength=n_blobs + 1)[1:]
    print(f"--- {label}: shape of the UNKNOWN regions at {threshold} min ---")
    print(f"  {n_blobs:,} connected regions, {int(sizes.sum()):,} cells, "
          f"largest {int(sizes.max()):,}, median {int(np.median(sizes))}")
    buckets = [(1, 1), (2, 3), (4, 8), (9, 16), (17, 64), (65, 1 << 30)]
    print(f"  {'size':>12} {'regions':>9} {'cells':>9} {'wholly invisible':>17} "
          f"{'% of regions':>13}")
    for lo, hi in buckets:
        sel = (sizes >= lo) & (sizes <= hi)
        if not sel.any():
            continue
        dark = sel & (painted_per == 0)
        name = f"{lo}" if lo == hi else (f"{lo}-{hi}" if hi < (1 << 30) else f"{lo}+")
        print(f"  {name:>12} {int(sel.sum()):>9,} {int(sizes[sel].sum()):>9,} "
              f"{int(dark.sum()):>17,} {dark.sum() / sel.sum() * 100:>12.1f}%")
    print()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--layer", action="append", default=None,
                    help="published layer id; repeatable. Default: the three walk layers.")
    ap.add_argument("--thresholds", type=int, nargs="+", default=DEFAULT_THRESHOLDS)
    args = ap.parse_args()

    man = json.loads((PUB / "manifest.json").read_text(encoding="utf-8"))
    nrows, ncols = int(man["nrows"]), int(man["ncols"])
    by_id = {L["id"]: L for L in man["layers"]}
    stems = args.layer or WALK_LAYERS
    hatch = hatch_mask(nrows, ncols)

    print(f"published grid {nrows} x {ncols} = {nrows * ncols:,} cells")
    print(f"hatch covers {int(hatch.sum()):,} cells ({hatch.mean() * 100:.2f}%) -- "
          f"an UNKNOWN cell outside it is painted PX_OUT, the same as EXCLUDED\n")

    for stem in stems:
        if stem not in by_id:
            raise SystemExit(f"{stem} is not in the manifest; have {sorted(by_id)}")
        L = by_id[stem]
        status, value = load(stem, nrows, ncols)
        report(stem, L["label"], status, value, float(L["horizon_s"]), hatch, args.thresholds)
        shape_detail(L["label"], status, value, float(L["horizon_s"]), hatch,
                     int(L["default_threshold_min"]))


if __name__ == "__main__":
    main()
