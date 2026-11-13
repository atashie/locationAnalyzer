# S3.5 — the browser path, and the encoding freeze it needed

**2026-11-13.** Step 6 of the S3 execution plan's §0. `v2/locfinder/wire.py`,
`v2/scripts/export_published_layers.py`, `v2/scripts/make_wire_vectors.py`,
`v2/spikes/g3-render/{worker.js, app.js, worker_conformance.mjs}`, `v2/tests/test_wire.py`,
`v2/tests/test_browser_conformance.py`.

## What was wrong, measured rather than described

§0 recorded the defect as "the export collapses UNKNOWN into EXCLUDED". Reading the code, it is
both narrower and wider than that, in two directions at once:

* the **mask** the worker ships (`mask[p] = inside`, and `inCount`) sets every missing cell to 0,
  which is what EXCLUDED looks like — §0's point, and it is correct;
* the **rendering** does the opposite. It paints every missing cell with the nodata hatch, so a
  cell the pipeline can *prove* is over the threshold is shown as "we don't know";
* and the loop `break`s on the first missing value, so a **known failure in a later layer never
  gets looked at**. That is "one known failure beats any number of unknowns" exactly inverted.

The size of the second one, on the published Triangle walk layer of 330,502 cells:

| | |
|---|---|
| `OK` | 256,752 |
| `OFF_NETWORK` | 57,541 |
| `BEYOND_HORIZON` | 16,209 |

At a ten-minute threshold **18,648 of the missing cells are known failures** — every
`BEYOND_HORIZON` cell, plus 2,439 `OFF_NETWORK` cells whose lower bound already exceeds ten
minutes — and the v1 format cannot say so, because it has one `NODATA` code for all of them.
Step 5's census put the same defect on the structure population: about **10,000 of 512,633
structures** at every threshold.

None of that is a rounding error. `encode_minutes` rounds up, so `ceil(s/60) ≤ T` is exactly
`s ≤ 60T`, and a finite cell's encoded verdict already equalled its float verdict.

## The format: `published-v2`

Two uint8 planes per layer, same shape.

| plane | meaning |
|---|---|
| `value` | travel time in whole minutes where the status is `OK`; a **lower bound** on it where the status is `OFF_NETWORK`, `BEYOND_HORIZON` or `NO_PATH`; `255` otherwise |
| `status` | `0 OK`, `1 OFF_NETWORK`, `2 BEYOND_HORIZON`, `3 NO_PATH`, `4 LAYER_UNKNOWN`, `5 OUTSIDE`, `6 UNKNOWN_CAUSE` |

The wire codes are assigned in `wire.py` and are **not** `status.Reason`'s integers, because the
layer contract says the enum "must never be written into a raster". Two codes are new at this
layer: `OUTSIDE` is a pixel the export covers and the source did not, which v1 could only call
`NODATA` — the same code it used for a cell with no road near it. `UNKNOWN_CAUSE` is how a v1
artifact lifts into this format **without inventing provenance it never had**: missing, cause not
recorded, never a known failure. That is precisely what v1 could assert, so the lift moves no
verdict.

**Rounding up is what makes the bound exact rather than approximate.** For an integer-minute
threshold, `ceil(x/60) > T` is equivalent to `x > 60T`, which is `evaluate`'s own comparison. So a
decoder working in whole minutes reaches `evaluate`'s verdict exactly.

**Capping is sound in one direction only.** A bound above 254 saturates, which weakens it and can
only turn a known failure into an unknown. An `OK` minute above 254 would do the opposite, so the
encoder **refuses** rather than capping. The horizon is 120 minutes, so no cell reaches it today.

Legacy minute values 251–254 stay ordinary minutes: the sentinels moved to the status plane, which
is what "version the format, do not reinterpret the codes" means in practice.

## It costs 9%

| layer | raw | deflated | v1 deflated | ratio |
|---|---|---|---|---|
| `own_triangle_grocery_walk` | 661,004 | **202,380** | 185,053 | 1.09× |
| `own_triangle_grocery_walk_cell200` | 661,004 | 101,696 | 88,987 | 1.14× |

The status plane holds three distinct values in large contiguous regions, so it deflates to almost
nothing. **The entire three-outcome algebra costs 17 KB.**

## The decoder, and the part a Python test cannot reach

`wire.outcome_planes` and `worker.js`'s `outcomeFor` are the same function in two languages.

* `tests/test_wire.py` proves the **Python** one agrees with `status.evaluate` **cell for cell**
  on all 330,502 published cells, at ten thresholds from 1 to 121 minutes. Not in aggregate — an
  over-exclusion in one place must not cancel an under-exclusion in another.
* `worker_conformance.mjs` proves the **JavaScript** one agrees with Python: 37 checks over
  hand-built statuses, the two-layer combination rule, every status code including the three that
  no `Surface` can hold, and a 200 × 200 window of the real published layer carrying every code it
  produces. It drives the real worker through its real message protocol with `self` shimmed, so
  the functions under test are the ones a browser runs.
* `tests/test_browser_conformance.py` runs that under pytest, so the browser check happens on
  every suite run rather than when someone remembers to type `node`.

**That cross-language test earned its place immediately.** `UNKNOWN_CAUSE` was added to `wire.py`
and not to `worker.js`, and the harness failed with *"status plane holds code 6, which this decoder
does not define"* — a divergence no Python test could have seen.

The decoder also refuses rather than guesses: a manifest in an unknown encoding, a layer with no
`horizon_s` (so `BEYOND_HORIZON` cannot be decided), a plane of the wrong size, and an undefined
status code are each rejected with a message naming the problem. A format that silently
reinterpreted 251–254 would publish a region nobody computed.

## The exporter

`scripts/export_published_layers.py` is new and is the product export. It reads the surface triple
`build_layer_surface` produced — seconds, reason and `min_possible_s` — and writes both planes,
reprojected with **nearest for both**: a status code is a name, so averaging two is meaningless,
and a minute is a decision input, so averaging two publishes something nobody computed.

Two of §0's exporter defects are **retired rather than fixed**. `spikes/g3-render/export_layers.py`
discovers layers by `<engine>_<category>_<mode>` and so omitted `own_triangle_grocery_walk.tif`,
and it targeted the 401 × 550 Phase 0 slice rather than the 514 × 643 Triangle footprint — which
together meant the browser had never once rendered the layer the product publishes. That exporter
cannot be fixed into the product path: it reads **minute GeoTIFFs**, and the reason and the bound
were discarded before those were written, so every missing value it can emit is a bare `NODATA`.
It is kept for the G1 engine comparison it was built for, and marked as superseded for the product.

## What is not done

* **Phone decode latency and compressed transfer size on a device.** The sizes above are deflated
  byte counts; decode time on a real handset needs a handset, and that is the owner's.
* **The card combination UI.** The worker now returns three counts — `inCount`, `excludedCount`,
  `nodataCount` (unknown) — and `app.js` carries all three, but the per-criterion card that tells a
  household *which* criterion was unknown and why is not built.
* **`OUTSIDE` has no live producer.** The current export's target bounds sit inside the source's
  projected footprint, so zero pixels are uncovered. The code is exercised by the hand-built
  vectors in both languages, not by a real layer.
* **Recomputation eligibility.** `needs_recomputation` distinguishes a cell unknown *only* because
  the threshold is past the horizon, which is answerable by searching further. The format carries
  what that decision needs (`BEYOND_HORIZON` plus the manifest's `horizon_s`) and the UI does not
  yet offer it.
