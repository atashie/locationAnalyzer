"""S3: does the whole-minute encoding change the verdict, and which rounding makes it not?

Run from `v2/`:  `uv run python spikes/s3_encoding_threshold_crossing.py grocery walk`

This was a decision and it has been taken: **`encode_minutes` rounds up as of 2026-11-09**
(`ENCODING = "uint8-minutes-ceil-v1"`). This script is the evidence it was taken on, kept runnable
so the claim can be re-checked against any layer.

`locfinder/status.py` is explicit that evaluation uses the float seconds "never the uint8 encoding,
so rounding cannot move a threshold" (Codex pass-3 H6). That holds for the Python side. It does
**not** hold for a browser that has only the encoded raster, which is the artifact S3.5 ships, and
which thresholds the byte directly (`spikes/g3-render/worker.js:139`). The arithmetic is one-sided:

    rint(s/60) <= T   <=>   s <= 60T + 30   for even T   (np.rint rounds halves to EVEN)
    rint(s/60) <= T   <=>   s <  60T + 30   for odd  T
    ceil(s/60) <= T   <=>   s <= 60T        for T < 254    (exactly the float verdict)
    floor(s/60) <= T  <=>   s <  60(T + 1)

So a minute-only client answers a threshold **30 s more permissive** than the float surface under
the current encoding, and 60 s more permissive under `floor`. Both err in one direction only: they
show cells as passing that do not pass. Neither can ever hide a cell that does pass, because
rounding a value at or below `60T` cannot carry it above `T` minutes.

`ceil` is the only one of the three whose minute verdict is *identical* to the float verdict at a
whole-minute threshold — on **finite OK cells, below the 254-minute clip**. At `T >= 254` the clip
destroys it (300 minutes encodes to 254 and would pass `T = 254`), and `NODATA` must be masked
rather than compared, which is why every count below is taken over `reason == OK`.

Its cost is the displayed number: a 9 min 01 s walk displays as 10 minutes, an upper bound on our
model's time rather than the nearest value to it. That direction matches every
other conservatism in this system — `OFF_NETWORK` is unknown rather than excluded, a bounded engine
publishes `BEYOND_HORIZON` rather than `NO_PATH` — and a region that is exactly the region we
computed seems worth more than a number that is 30 s closer on average.

This script measures the size of the effect on the committed layer so the choice is made against
numbers. It reads only the layer and the building-count raster; no graph, no network.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import GRID, LAYERS, METRO, append_results, layer_path, stamp  # noqa: E402
from locfinder.grid import MAX_MINUTES  # noqa: E402
from locfinder.status import Reason  # noqa: E402

THRESHOLDS_MIN = (10, 15, 25, 45)
ROUNDINGS = {"rint (was shipped)": np.rint, "ceil (shipped)": np.ceil, "floor": np.floor}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("category")
    ap.add_argument("mode", choices=["walk", "bike", "drive"])
    args = ap.parse_args()

    seconds = np.load(layer_path("own", args.category, args.mode, ".npy")).astype(np.float64)
    reason = np.load(LAYERS / f"own_{METRO.name}_{args.category}_{args.mode}_reason.npy")
    counts = np.load(LAYERS / f"own_{METRO.name}_buildings_per_cell.npy")
    ok = reason == Reason.OK

    rows = []
    for name, fn in ROUNDINGS.items():
        enc = np.clip(fn(seconds / 60.0), 0, MAX_MINUTES)
        for t_min in THRESHOLDS_MIN:
            truth = ok & (seconds <= t_min * 60.0)
            shown = ok & np.isfinite(seconds) & (enc <= t_min)
            wrong = shown & ~truth                 # displayed as passing, does not pass
            missed = truth & ~shown                # passes, not displayed as passing
            rows.append({
                "rounding": name, "t_min": t_min,
                "truth_cells": int(truth.sum()), "shown_cells": int(shown.sum()),
                "wrong_cells": int(wrong.sum()), "missed_cells": int(missed.sum()),
                "wrong_of_shown": wrong.sum() / max(int(shown.sum()), 1),
                "wrong_of_ok": wrong.sum() / max(int(ok.sum()), 1),
                "wrong_buildings": int(counts[wrong].sum()),
                "wrong_buildings_of_shown": counts[wrong].sum() / max(counts[shown].sum(), 1),
            })

    print(render(rows, args))
    append_results("s3-encoding.md", render(rows, args))
    print("\nappended to docs/experiments/s3-encoding.md")


def render(rows: list[dict], args) -> str:
    out = [f"### Whole-minute encoding at a threshold: {args.category} / {args.mode} "
           f"({METRO.name}, {stamp()})", "",
           "`evaluate` uses float seconds, so nothing above is wrong on the Python side. A browser "
           "holding only the encoded raster answers a *different* threshold, and the error is "
           "one-sided: it shows cells as passing that do not pass, and never hides a cell that "
           "does. `wrong of shown` is `Pr(not actually a pass | displayed as a pass)` — the shape "
           "of conditional Codex pass 25 found missing from the estimand set, here for the "
           "encoding rather than the routing. It is an **artifact-to-artifact** comparison, the "
           "encoded raster against the float surface that produced it, and says nothing about "
           "routing or destination validity. `of all OK` is over OK cells, not over the frame. "
           "The browser path already built (`spikes/g3-render/worker.js:139`) does threshold the "
           "minute byte, so this is not hypothetical.", "",
           "| rounding | T | truth | shown | wrong | missed | wrong of shown | of all OK | "
           "wrong buildings | of shown buildings |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append(
            f"| {r['rounding']} | {r['t_min']} min | {r['truth_cells']:,} | {r['shown_cells']:,} | "
            f"**{r['wrong_cells']:,}** | {r['missed_cells']:,} | **{r['wrong_of_shown']:.2%}** | "
            f"{r['wrong_of_ok']:.2%} | {r['wrong_buildings']:,} | "
            f"{r['wrong_buildings_of_shown']:.2%} |")
    out += ["",
            "`missed` is 0 in every row, in every rounding, which is the structural claim: rounding "
            "a value at or below `60T` cannot carry it above `T` minutes, so a minute-only client "
            "can only be too generous.",
            "",
            "**`ceil` is exact for a finite OK cell at a whole-minute threshold below 254.** "
            "`ceil(s/60) <= T` is equivalent to `s <= 60T`, which is `evaluate`'s own comparison, "
            "so `wrong` and `missed` are both 0 by construction rather than by luck on this layer. "
            "At `T >= 254` the clip breaks it and NODATA is not a minute at all. The cost is the "
            "displayed number: an upper bound on our model's time, overstating by less than 60 s "
            "(a 0.1 s walk displays as 1 minute), where `rint` is within 30 s either way.",
            "",
            "**Decided 2026-11-09: `ceil`.** The `rint` row is kept as the comparison the "
            "decision was made against, not as a live option. Every minute raster was re-encoded "
            "from its stored seconds (`scripts/reencode_minute_rasters.py`, max shift 1 minute on "
            "all eight) and every raster and the browser manifest now carry "
            "`encoding=uint8-minutes-ceil-v1`, so a stale artifact is recognisable rather than "
            "merely byte-different. The walked-audit sheet's `encoding_disagrees_min` column is "
            "now blank on every row, where three of nineteen disagreed before.",
            "",
            "**What this does not fix.** The same worker loop treats NODATA as excluded, so the "
            "export still collapses UNKNOWN into EXCLUDED -- NODATA is one code for OFF_NETWORK "
            "and BEYOND_HORIZON alike, and the three-outcome algebra S0 built the Reason enum for "
            "does not survive to the browser. That is the larger of the two step-6 findings and "
            "the rounding has nothing to do with it."]
    return "\n".join(out)


if __name__ == "__main__":
    main()
