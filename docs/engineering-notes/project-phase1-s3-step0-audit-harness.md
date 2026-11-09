---
name: project-phase1-s3-step0-audit-harness
description: "S3 plan section 0 step 0 is done - GridSpec had no coordinate-to-cell mapping at all, Surface.min_possible_s and the build parameters are not stored so the harness needs three tested guards, and the near-threshold bands had to be split by the side of the threshold"
metadata:
  node_type: memory
  type: project
  originSessionId: 3448970c-7f62-4034-83e7-b7d86efb0261
  modified: 2026-11-09T00:00:00.000Z
---

Step 0 of the risk-ordered plan (`docs/plans/2026-11-04-s3-execution-plan.md` §0, revision 11) is
done. It exists because Codex pass 25 found that every estimand S3 had built compares the product to
**itself** — E1 against our own engine, with both sides drawing destinations from the same list — so
a closed grocery passes everything we own. A walked journey is the only check that consults the
world, and only the owner can walk one. See [[project-phase1-s3-design]] for the stage, and
[[feedback-decide-by-measurement-not-by-argument]] for why the equivalence claim below is tested
rather than reasoned about.

**Built.** `GridSpec.cell_for_xy` / `cell_for_lonlat` (`v2/locfinder/grid.py`), 7 tests in
`v2/tests/test_grid.py`, `v2/scripts/audit_recommendations.py`, 12 tests in
`v2/tests/test_audit_recommendations.py`, the owner's instructions in
`docs/experiments/audit/README.md`, and the first sheet — 21 journeys, built in **0.07 s with no
graph load**. Suite: 1,110 passed, 24 skipped (was 1,091).

## The grid had no reverse mapping, and one spike had inlined it

`GridSpec` went centre-outward only: `cell_centers_xy`, `cell_centers_lonlat`, `envelope_wgs84`.
Nothing in `locfinder/` answered *which published cell applies to this address*, which is the
question a query asks and the question an audit asks. The arithmetic existed once, inlined in
`spikes/s2_building_weighted_coverage.py:69`.

Three decisions worth keeping:

- **Half-open, closed on the north and west edges.** Cell `(row, col)` holds
  `x in [x_min + col*cell, ...)` and `y in (..., y_max - row*cell]`. Every point lands in at most
  one cell; which side of a measure-zero boundary is a convention, and this one matches
  `rasterio_profile`'s origin-at-north-west transform.
- **Outside returns `None` and never clamps.** Clamping would hand a household the travel time of
  whatever cell we happen to hold nearest, with nothing in the answer marking the substitution.
- **A non-finite coordinate raises.** NaN is not a point outside the footprint, it is not a point;
  returning `None` would launder a malformed input into an ordinary negative answer. This is the
  same defect class as plan §0 step 1's NaN origin that manufactures an authoritative `NO_PATH`.

Five mutants were checked against the new tests and all five were caught: clamping instead of
`None`, measuring the row from the south edge, returning `(col, row)`, closing the east and south
edges, and returning `None` for a non-finite coordinate.

## `min_possible_s` is not stored, and reconstructing it needs three guards

`status.Surface` needs three arrays. `seconds` and `reason` are on disk; **`min_possible_s` was
never saved**. Building it properly means loading the 670 MB `roads.graphml` — minutes per run,
which would make the owner's loop slow enough to skip.

It is reconstructible for *this* artifact as *seconds where `OK`, the horizon where
`BEYOND_HORIZON`, `0` where `OFF_NETWORK`*. That is a property of the artifact, not of the format,
so the script **refuses** rather than guessing unless these hold:

1. **`reason.max() <= Reason.BEYOND_HORIZON`.** A `NO_PATH` cell reconstructed with a bound of `0`
   reads as `UNKNOWN` — a *proven* failure turned into an absence, the one error class this stage
   exists to prevent. Measured: the Triangle grocery/walk reason array holds only `{0, 1, 2}`.
2. **`max_access_m / max_speed_mps(mode) <= min(threshold)`.** This is what makes the weak
   `OFF_NETWORK` bound not merely *sound* but **outcome-identical**. The real bound is
   `access_m / max_speed_mps` (`traveltime/snap.py:291`), at most `200 / 1.4 = 142.9 s` walking, and
   `evaluate` converts a bound into a known failure only when it *strictly exceeds* the threshold —
   so at 600 s and 900 s, `0` and the real bound agree on every cell.

Guard 2's claim is **tested, not argued**: `test_the_weak_off_network_bound_gives_the_same_answers`
builds both bounds with access distances spread over the whole admissible range and asserts
`evaluate` agrees at 600 s and 900 s — *and disagrees at 60 s*, so the refusal is protecting
something real rather than decorating an impossible branch. An assertion that has never been seen to
fire has not been shown to protect anything; that was pass-19 F5, a guard in a scratch directory
that protected one invocation on one afternoon.

**`Surface.validate()` is also the cross-check between the two files**, which were written by
separate runs 43 minutes apart. It requires a finite time exactly where the reason is `OK`, so a
reason array from a different build is rejected rather than silently mislabelling cells — but the
message had to be rewritten to say so, instead of surfacing a bare `ValueError`.

**A third guard, found by asking what else the script assumes about someone else's build.**
`CUTOFF_MIN` and `MAX_ACCESS_M` were constants in the *consumer*, copied from the spike that built
the layer. `Surface.validate` only checks `max finite <= horizon`, so **assuming a horizon larger
than the build used passes validation silently** — measured: a 60-minute layer read as 120 minutes
raises nothing, and then every `BEYOND_HORIZON` bound is wrong by an hour. Two fixes:

* The builder now writes `own_<metro>_<cat>_<mode>_build.json` (horizon, access distance, snap
  radius, aggregation, profile and grid versions) and the harness prefers it. Provenance belongs to
  the artifact, not to a constant in whatever reads it.
* Where there is no sidecar, the assumed horizon is **corroborated against the arrays**:
  `corroborate_horizon` requires that, if any cell was cut off, the largest finite time sits within
  60 s below the claimed horizon. A cutoff that bound leaves cells just inside it — walking 60 s
  covers 84 m, under one cell — so a bound cutoff with no cell near it is not a surface this
  pipeline produces. On the committed layer the gap is **0.001 s**. The arrays can *falsify* a
  horizon claim and cannot *verify* one, and the provenance record says so rather than implying the
  horizon was read from the data.

The access-distance check was also restated. Instead of depending on `MAX_ACCESS_M` being exactly
right, it asks for the widest build it tolerates: the equivalence holds for any
`max_access_m <= min(threshold) * max_speed_mps`, which is **840 m** against the 200 m this project
uses — a 4.2x margin, so being wrong about the build is harmless until it is wrong by a factor of
four.

**The reconstruction is now transitional.** `s2_building_weighted_coverage.py` saves
`own_<metro>_<cat>_<mode>_min_possible_s.npy` beside the layer, and the harness prefers it when
present — in which case neither of the first two guards is needed and a `NO_PATH` layer loads
correctly. Today's sheet still says `"origin": "reconstructed"` and `"build": "assumed"` because the
layer predates both changes.

## A symmetric near-threshold band is the wrong stratum

The first run drew six journeys from a band symmetric about 15 minutes and **all six landed above
it**. Every row asked the same question, and no walk could have shown which direction an offset ran.
Walked journeys are the scarce resource — pass 25 budgeted 3–6 household person-hours for 20–30
origins — so a draw that wastes half its power is not a cosmetic problem.

The bands are now split by **the answer the product gives**: `band10min_pass` holds cells shown as
passing, `band10min_fail` cells shown as failing. That also separates the two error costs. A
displayed PASS that fails when walked is the one a household is harmed by, and it is the numerator
of `Pr(comparator FAIL | product PASS)` — the conditional pass 25 found missing, which is step 2.

Seven strata at 3 each gives 21 journeys, matching pass 25's suggested scale.

## No footprint geometry in the sheet, deliberately

Journeys are restricted to cells holding at least one building, read from the **count raster**
`own_triangle_buildings_per_cell.npy`. A cell with no structure has no door to walk from.

The individual Overture footprints were the obvious way to suggest a real starting door, and were
rejected: `data/triangle/overture_buildings_report.json` records their admitted use as *"rasterised
to counts, never republished"*, and this sheet is committed and pushed. Putting 30 building
coordinates into it would be a wider use than the one recorded, for a convenience the owner does not
need — they can see the cell on an OSM deep link and pick their own front door. It is also faster,
and keeps the whole run at 0.07 s. See [[project-v2-rethink-decisions]] for decision 17.

## What the strata measure, and the limit to read them with

| stratum | cells | with a building | drawn |
|---|---|---|---|
| `band10min_pass` | 6,009 | 4,353 | 3 |
| `band10min_fail` | 6,466 | 4,696 | 3 |
| `band15min_pass` | 7,428 | 5,207 | 3 |
| `band15min_fail` | 7,504 | 5,097 | 3 |
| `off_network_beside_ok` | 24,468 | **633** | 3 |
| `deep_pass_control` | 5,732 | 4,363 | 3 |
| `deep_fail_control` | 112,744 | 51,362 | 3 |

`off_network_beside_ok` is the stratum with real diagnostic value — the product refuses to answer
next door to a cell that passes, and the layer cannot distinguish "the 200 m access rule is too
strict" from "the graph is missing a path people use" — and it is also the thinnest: **633 walkable
cells of 24,468**. Three draws from it are a thin sample of a thin population, so agreement there is
encouraging and not evidence. Within 3 km of Chapel Hill the stratum is **empty**, which is the
expected shape for a dense area and means a `--near` sheet has 18 journeys, not 21.

The by-reason building counts reproduce S2.4's recorded figures exactly (`spotcheck-engines.md`
line 1158 onward: 499,009 of 512,633 buildings `OK`, 97.3423%), which is a useful consistency check
that the reconstructed surface is the same surface — **not a new finding**, and it was nearly written
up as one.

## The blind spot step 0 cannot close

**The sheet cannot say which grocery the product routed to.** The layer stores the minimum over every
qualifying destination and not the argmin, so a walk establishes that *some* destination was open and
reachable, never that *ours* was. That narrows the closed-destination blind spot E1 and E2 share; it
does not close it. Closing it needs `build_layer_surface` to emit the chosen destination per cell,
which it does not do today. Recorded in the script's docstring, in the sheet's `.meta.json`
`blind_spot` field, and in the owner's README, because this is the kind of limitation that is obvious
while writing the code and invisible three weeks later when someone reads the results.

## The encoding moves the threshold, which is a separate finding

Codex pass 26 noticed that three of the 21 emitted rows carry a float verdict of FAIL beside an
encoded minute that would read as PASS. Chased down, it is structural and it is S3's own decision —
see [[project-phase1-s3-encoding-threshold-crossing]] and
`docs/experiments/s3-encoding.md`. The sheet now carries an `encoding_disagrees_min` column naming
the thresholds where the two verdicts differ, so a walked journey is attributed to the right verdict
rather than to whichever one the reader assumes.

## Two traps and one gap, all found by running it

- **`argparse` cannot take `--near -79.0558,35.9132`.** Every longitude in this metro starts with a
  minus sign, and argparse reads a leading-dash value as an unknown option unless it matches
  `^-\d+$|^-\d*\.\d+$` — which a `lon,lat` string does not. Two floats (`nargs=2, type=float`) do
  match, so `--near -79.0558 35.9132`, the form anyone would type, works.
- **`Path.relative_to(REPO)` crashes for an `--out` outside the tree**, and it crashed *after* the
  CSV was written, so the run looked like a failure and had left a file behind. Provenance paths are
  now `as_posix()` and repo-relative where possible, absolute otherwise — also so the record reads
  the same on the second machine.
- **`v2/data/` is gitignored**, so the three input rasters (~4.2 MB) do not travel with a clone: the
  sheet is committed and readable anywhere, but reproducible only on a machine holding the layers.
  The sha256s in the `.meta.json` identify them where they exist, and the rebuild command is in the
  refusal message. Tracking those three files would make the audit reproducible for 4.2 MB, but that
  is a change to the repository's data policy and is the owner's call.

**The sheet refuses to overwrite itself** without `--force`. It is meant to be filled in by hand, so
a rerun erasing walked results is a data-loss bug waiting to happen, not a convenience.

**Next:** plan §0 step 1, the cheap correctness debts. Non-finite coordinates are now rejected at
`cell_for_lonlat`, which is one entry point of several.
