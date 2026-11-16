"""Donut holes: excluded cells ringed by included ones. Do they exist, how many, and are they
really closer to a destination than the ring around them?

The owner reports parcels that stay out of region while every neighbour is in it, and which look
CLOSER to the point of interest. Before any mechanism is argued, this establishes whether the
shape is there and how common it is.

A hole is defined narrowly on purpose: an EXCLUDED cell whose eight neighbours are ALL INCLUDED.
That is the shape described, it cannot be produced by a threshold gradient, and it is countable.
"""
import json
import pathlib
import sys

import numpy as np

V2 = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V2))
sys.path.insert(1, str(V2 / "spikes"))
from _common import GRID, LAYERS  # noqa: E402

from locfinder.grid import encode_minutes  # noqa: E402

OK, OFF_NETWORK, BEYOND_HORIZON, NO_PATH = 0, 1, 2, 3
LAYERS_TO_CHECK = [
    ("own_triangle_grocery_walk", [10, 15, 20, 30]),
    ("own_triangle_park_walk", [10, 15, 20, 30]),
    ("own_triangle_school_walk", [15, 20]),
    ("own_triangle_grocery_drive", [5, 10, 15]),
]


def outcome_planes(stem, threshold):
    """PASS / FAIL / UNKNOWN as three boolean planes, by worker.js `outcomeFor`."""
    reason = np.load(LAYERS / f"{stem}_reason.npy")
    secs = np.load(LAYERS / f"{stem}.npy").astype(np.float64)
    lower = np.load(LAYERS / f"{stem}_min_possible_s.npy").astype(np.float64)
    horizon_s = float(json.loads((LAYERS / f"{stem}_build.json")
                                 .read_text(encoding="utf-8"))["horizon_s"])
    value = encode_minutes(np.where(reason == OK, secs, lower)).astype(np.int32)
    ok = reason == OK
    off = reason == OFF_NETWORK
    bh = reason == BEYOND_HORIZON
    npth = reason == NO_PATH
    passing = ok & (value <= threshold)
    failing = (ok & (value > threshold)) | npth | (off & (value > threshold))
    if horizon_s >= 60 * threshold:
        failing = failing | bh
        unknown = off & (value <= threshold)
    else:
        unknown = (off & (value <= threshold)) | bh
    return passing, failing, unknown, secs, reason


def holes(passing, failing):
    """EXCLUDED cells whose eight neighbours are all INCLUDED."""
    p = passing
    ring = np.ones_like(p, dtype=bool)
    ring[:, :] = True
    shifted = []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            s = np.roll(np.roll(p, dr, axis=0), dc, axis=1)
            shifted.append(s)
    allpass = np.logical_and.reduce(shifted)
    ring = allpass.copy()
    ring[0, :] = ring[-1, :] = ring[:, 0] = ring[:, -1] = False
    return failing & ring


def main() -> None:
    xs, ys = GRID.cell_centers_xy()
    print(f"grid {xs.shape}, cell {GRID.cell_m if hasattr(GRID, 'cell_m') else '100'} m\n")
    for stem, thresholds in LAYERS_TO_CHECK:
        print(f"=== {stem} ===")
        for t in thresholds:
            passing, failing, unknown, secs, reason = outcome_planes(stem, t)
            h = holes(passing, failing)
            n = int(h.sum())
            if n == 0:
                print(f"  limit {t:>3} min: {int(passing.sum()):>7,} in region, 0 holes")
                continue
            rows, cols = np.where(h)
            # How much slower is the hole than the mean of its eight neighbours?
            gaps = []
            for r, c in zip(rows, cols):
                nb = secs[r - 1:r + 2, c - 1:c + 2].copy()
                mine = secs[r, c]
                nb[1, 1] = np.nan
                if np.isfinite(mine) and np.isfinite(np.nanmean(nb)):
                    gaps.append(mine - np.nanmean(nb))
            gaps = np.array(gaps) if gaps else np.array([0.0])
            print(f"  limit {t:>3} min: {int(passing.sum()):>7,} in region, "
                  f"**{n:,} holes**; the hole is slower than its ring by "
                  f"median {np.median(gaps):.0f} s, p90 {np.percentile(gaps, 90):.0f} s, "
                  f"max {gaps.max():.0f} s")
            by_reason = {int(k): int(v) for k, v in
                         zip(*np.unique(reason[h], return_counts=True))}
            print(f"              hole statuses: {by_reason}")
        print()


if __name__ == "__main__":
    main()
