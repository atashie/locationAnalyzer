"""The hatched cells: how many, why, and whether anybody lives in them.

The owner reports grey diagonal pixels on Park, walk that multiply as the walk time goes up. The
diagonal is the renderer's own hatch for UNKNOWN -- `(row + col) & 7 < 2` in worker.js. This
measures the thing the hatch is marking.

Reproduces `outcomeFor` from worker.js on the UTM source surfaces, so each cell can be weighted by
its building count, which the published WGS84 planes cannot be. Cell counts are therefore on the
330,502-cell UTM grid, not the published one.
"""
import json
import pathlib
import sys

import numpy as np

V2 = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V2))
sys.path.insert(1, str(V2 / "spikes"))
from _common import LAYERS  # noqa: E402

from locfinder.grid import encode_minutes  # noqa: E402

OK, OFF_NETWORK, BEYOND_HORIZON, NO_PATH = 0, 1, 2, 3
NAMES = {OK: "OK", OFF_NETWORK: "OFF_NETWORK", BEYOND_HORIZON: "BEYOND_HORIZON",
         NO_PATH: "NO_PATH"}
PASS, FAIL, UNKNOWN = "PASS", "FAIL", "UNKNOWN"
THRESHOLDS = [10, 15, 20, 30, 45, 60]
STEMS = ["own_triangle_park_walk", "own_triangle_grocery_walk", "own_triangle_school_walk"]


def outcomes(status, value, threshold, horizon_s):
    """worker.js `outcomeFor`, vectorised. Same branches, same order."""
    out = np.full(status.shape, "", dtype=object)
    ok = status == OK
    out[ok & (value <= threshold)] = PASS
    out[ok & (value > threshold)] = FAIL
    out[status == NO_PATH] = FAIL
    bh = status == BEYOND_HORIZON
    out[bh] = FAIL if horizon_s >= 60 * threshold else UNKNOWN
    off = status == OFF_NETWORK
    out[off & (value > threshold)] = FAIL
    out[off & (value <= threshold)] = UNKNOWN
    return out


def main() -> None:
    bld = np.load(LAYERS / "own_triangle_buildings_per_cell.npy").astype(np.float64)
    total_b = bld.sum()
    print(f"{bld.size:,} cells, {total_b:,.0f} buildings\n")
    for stem in STEMS:
        reason = np.load(LAYERS / f"{stem}_reason.npy")
        secs = np.load(LAYERS / f"{stem}.npy").astype(np.float64)
        lower = np.load(LAYERS / f"{stem}_min_possible_s.npy").astype(np.float64)
        build = json.loads((LAYERS / f"{stem}_build.json").read_text(encoding="utf-8"))
        horizon_s = float(build["horizon_s"])

        # The published `value`: the time where OK, the lower bound where bounded.
        src = np.where(reason == OK, secs, lower)
        value = encode_minutes(src).astype(np.int32)

        print(f"=== {stem}  (horizon {horizon_s / 60:.0f} min) ===")
        counts = {NAMES[k]: int((reason == k).sum()) for k in NAMES if (reason == k).any()}
        print(f"  statuses: {counts}")
        print(f"  {'limit':>5}  {'UNKNOWN cells':>14} {'of grid':>8}   "
              f"{'UNKNOWN buildings':>18} {'of all':>7}   {'from OFF_NETWORK':>17}")
        for t in THRESHOLDS:
            out = outcomes(reason, value, t, horizon_s)
            unk = out == UNKNOWN
            from_off = unk & (reason == OFF_NETWORK)
            print(f"  {t:>5}  {int(unk.sum()):>14,} {unk.mean() * 100:>7.2f}%   "
                  f"{bld[unk].sum():>18,.0f} {bld[unk].sum() / total_b * 100:>6.2f}%   "
                  f"{int(from_off.sum()):>17,}")
        # What the bound actually is on the OFF_NETWORK cells, which is what drives the growth.
        off = reason == OFF_NETWORK
        b = value[off]
        print(f"  OFF_NETWORK lower bounds, minutes: min {b.min()}, median {int(np.median(b))}, "
              f"p90 {int(np.percentile(b, 90))}, max {b.max()}")
        print(f"  of {int(off.sum()):,} OFF_NETWORK cells, {bld[off].sum():,.0f} buildings "
              f"({bld[off].sum() / total_b * 100:.2f}% of all)\n")


if __name__ == "__main__":
    main()
