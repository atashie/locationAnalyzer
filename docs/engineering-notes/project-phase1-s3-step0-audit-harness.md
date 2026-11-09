---
name: project-phase1-s3-step0-audit-harness
description: "S3 plan section 0 step 0, after Codex pass 26 corrected it - the reconstructed OFF_NETWORK bound is sound and LOSSY not exact (200 m is the floor of those access distances, not the ceiling), the first sheet asked for 6.22 hours of walking including a 108-minute *control*, and the unknown-beside-a-pass stratum was dilating OK instead of PASS"
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
`v2/tests/test_grid.py`, `v2/scripts/audit_recommendations.py`, 16 tests in
`v2/tests/test_audit_recommendations.py`, the owner's instructions in
`docs/experiments/audit/README.md`, and the sheet — 19 journeys, built in **0.08 s with no
graph load**. Suite: 1,115 passed, 24 skipped (was 1,091).

**Read the correction section at the end first.** Codex pass 26 found six verified defects in
the first version of this work, including that its central claim was *inverted*, and the
sections below have been rewritten against the corrected version. The pattern is worth more
than the details: every one of the six came from reasoning about the pipeline instead of
reading it, and the one I was most confident about was the one I had a passing test for.

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

1. **`reason.max() <= Reason.BEYOND_HORIZON`** — a **fail-fast, not a correctness barrier.**
   The first version of this note said a `NO_PATH` cell would otherwise "silently read as
   `UNKNOWN`, turning a proven failure into an absence". **That is false twice over:**
   `Surface.validate` rejects a `NO_PATH` cell whose bound is not `+inf` (`status.py:325`), and
   `evaluate` fails `NO_PATH` unconditionally whatever its bound (`status.py:380`) — the one
   reason in the enum whose verdict never consults the bound. The guard earns its place by
   failing where the cause is readable, and that is all. Measured: the Triangle grocery/walk
   reason array holds only `{0, 1, 2}`.
2. **The adjacency bound**, `(max_access_m + cell_m * sqrt(2)) / max_speed_mps <= min(threshold)`.

**The `0` bound is sound and lossy, not exact, and the first version of this note had the
direction of the access rule backwards.** A cell is `OFF_NETWORK` precisely *because*
`snapped.access_m > max_access_m` (`traveltime/snap.py:265`), so **200 m is the floor of those
distances, not the ceiling** and the real bound `access_m / max_speed_mps` is always *above*
143 s with no upper limit at all. Codex pass 26 built a two-node graph with origins 201 m, 1 km
and 2 km off-network and measured real bounds of 143.6 s, 714.3 s and 1,428.6 s: at a 600 s
threshold the real surface says UNKNOWN, FAIL, FAIL where the reconstruction says UNKNOWN three
times, and both refusals accepted it.

What is true is one-sided and worth stating precisely: `0` never *exceeds* the real bound, so
the reconstruction can report `UNKNOWN` where the pipeline proves `FAIL` but **can never
manufacture an exclusion**. It loses information and never invents it, which is the right
direction for a product that must not wrongly rule a household out.

Exactness comes from the **selection**, not the format: every emitted `OFF_NETWORK` row is
adjacent to an `OK` cell, whose own access is at most `max_access_m`, so the emitted cell's
access is at most `max_access_m + cell_m * sqrt(2)` = 341.4 m — a bound of 243.9 s, well inside
600 s. That is now the condition checked, and the adjacency is re-asserted per emitted row
instead of being inferred from the stratum.

**The test that "proved" the old claim passed vacuously**, and that is the part to remember. It
generated access distances uniformly in `[0, 200]` m — the domain in which a cell is *not*
`OFF_NETWORK` at all — so it asserted agreement over inputs that cannot occur. A fixture is
exact only where you point it ([[feedback-a-fixture-is-exact-only-where-you-point-it]]), and a
passing test over the wrong domain is worse than no test: it ended an inquiry. The replacements
draw from `(200, 3000]` m and assert soundness, demonstrate the loss on that surface, and test
the adjacency bound separately.

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
* Where there is no sidecar, the assumed horizon gets a **plausibility warning and nothing
  more** — and the history of that line is the lesson. It began as a refusal when the largest
  finite time sat more than 60 s below the claimed horizon, justified by "walking 60 s covers 84 m,
  under one cell". Pass 27 rejected that with a legitimate layer whose frontier fell 64.3 s short.
  I replaced it with a *derived* scale, `(max_access_m + cell_m) / access_speed_mps` = 238 s, and
  pass 28 rejected that too: two parallel roads 100 m apart joined by a 12.1 km detour leave a
  **7,164 s** gap, because neighbouring cells can snap to roads separated by an arbitrarily long
  network journey. **There is no bound here to derive.** The check now prints a warning, records
  `is_a_heuristic: true`, and refuses nothing; only the sidecar or `--horizon-min` settles a
  horizon. Twice I replaced an arbitrary threshold with a better-argued threshold when the defect
  was having a threshold at all.

The access-distance check was also restated. Instead of depending on `MAX_ACCESS_M` being
exactly right, it asks for the widest build it tolerates. The inequality actually implemented
includes the cell diagonal, so the tolerance is
`min(threshold) * max_speed_mps - cell_m * sqrt(2)` = **698.6 m**, a **3.49x** margin on the 200 m
this project uses. An earlier version of this paragraph said 840 m and 4.2x, which is the figure you
get by forgetting the diagonal that the whole adjacency argument rests on (pass 27).

**The reconstruction is now transitional.** `s2_building_weighted_coverage.py` saves
`own_<metro>_<cat>_<mode>_min_possible_s.npy` beside the layer, and the harness prefers it when
present — in which case neither of the first two guards is needed and a `NO_PATH` layer loads
correctly. Today's sheet still says `"origin": "reconstructed"` and `"build": "assumed"` because the
layer predates both changes.

## The first sheet was not walkable, and the diagnostic stratum was not diagnostic

Two selection defects, both verified by Codex pass 26, both from never asking what the numbers
*cost*:

- **The 18 rows with a finite prediction totalled 6.22 hours of one-way walking, and three
  "deep FAIL controls" were 3.57 of them — 108, 50 and 56 minutes each.** `DEEP_FAIL_S = 1800`
  asked for cells *at least* 30 minutes from a grocery, and the predicted seconds **are** the
  walking time. Nothing in the script or the sheet mentioned the budget. Controls are now
  defined by their **margin** past the threshold (5 minutes, already 10–20x any offset the
  bands could reveal) rather than an absolute time, a `--max-walk-min` cap (default 25) applies
  to every stratum, the deep FAIL control is drawn **once** rather than three times because it
  is the longest journey on the sheet and buys the least per hour, and the run prints the total.
  Now: **2.98 hours over 16 rows, longest 20 minutes.**
- **`off_network_beside_ok` dilated `reason == OK`, not PASS.** So "unknown next door to a
  pass" actually meant "unknown next door to any cell with a finite time": 24,468 cells, 633
  with a building, and the three drawn had nearest answering neighbours at **3,615 s, 4,783 s
  and 4,293 s** — an hour from a grocery, not beside a pass in any sense. Dilating the PASS mask
  gives 1,081 cells, **77** with a building. The stratum is now `off_network_beside_pass15min`,
  far smaller and the right cells. A few draws from 77 can find a real access defect; they
  cannot establish how common one is, and the README says so.

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

The sheet as it now stands, 19 journeys and **2.98 hours of one-way walking, longest 20
minutes**:

| stratum | cells | with a building | drawn |
|---|---|---|---|
| `band10min_pass` | 6,009 | 4,353 | 3 |
| `band10min_fail` | 6,466 | 4,696 | 3 |
| `band15min_pass` | 7,428 | 5,207 | 3 |
| `band15min_fail` | 7,504 | 5,097 | 3 |
| `off_network_beside_pass15min` | **1,081** | **77** | 3 |
| `deep_pass_control` | 5,732 | 4,363 | 3 |
| `deep_fail_control` | 148,424 | 11,963 | **1** |

(The pre-repair version of this table read `off_network_beside_ok` 24,468 / 633 with three deep FAIL
controls drawn from 112,744 / 51,362, for 21 journeys and 6.22 hours. It survived the first round of
corrections in the prose above and was caught by pass 27 — a reminder that a table is as much a
claim as a sentence.)

`off_network_beside_pass15min` is the stratum with real diagnostic value — the product refuses to
answer next door to a cell that passes, and the layer cannot distinguish "the 200 m access rule is
too strict" from "the graph is missing a path people use" — and it is also the thinnest: **77
walkable cells of 1,081**. Three draws from it are a thin sample of a thin population, so agreement
there is encouraging and not evidence. Within 3 km of Chapel Hill the stratum is **empty**, the
expected shape for a dense area, and a `--near` sheet then has 16 journeys.

The three drawn rows do now neighbour passing cells, at 164.3 s, 582.6 s and 850.5 s (pass 27).

The by-reason building counts reproduce S2.4's recorded figures exactly (`spotcheck-engines.md`
line 1158 onward: 499,009 of 512,633 buildings `OK`, 97.3423%), which is a useful consistency check
that the reconstructed surface is the same surface — **not a new finding**, and it was nearly written
up as one.

## The blind spot step 0 cannot close

**The sheet cannot say which grocery the product routed to, and our number is an upper bound.**
The aggregation is `CATEGORY_COST_SELECTED` — *the travel time of the journey our cost model
selected* (`status.py:210`), **not** the minimum over qualifying destinations, which the first
version of this note, the script docstring, the owner README and the commit message all claimed.
The repo already had a note about exactly this confusion — [[project-h2-upper-bound-trap]] —
and I walked into it anyway. The argmin is not stored either, so a walk establishes that *some*
qualifying destination was open and reachable, never that *ours* was. That narrows the closed-destination blind spot E1 and E2 share; it
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

## What pass 26 corrected, as a list

Kept together because the pattern matters more than any single item. All six were **verified
against the code or by construction**, not suspected:

| claim I made | status |
|---|---|
| the real `OFF_NETWORK` bound is at most `200/1.4` | **false** — 200 m is the floor of those distances |
| the two guards establish whole-surface outcome equivalence | **false** — sound and lossy, exact only on the emitted subset |
| the test covers the admissible `OFF_NETWORK` range | **false** — it covered `[0, 200]`, where cells are not off-network |
| without the `NO_PATH` guard a proven failure reads as an absence | **false** — `validate` rejects it and `evaluate` fails it regardless |
| `validate` rejects files from different builds | **overstated** — it establishes invariants, not shared provenance |
| the layer holds the minimum time over destinations | **overstated** — it is the cost-selected journey, an upper bound |
| one disagreeing control shows a systematic error | **overstated** — a local closure or graph defect explains one just as well |
| the seven strata totals, and S2.4's by-reason figures | **confirmed** by independent recomputation |
| all five grid mutants are caught | **confirmed**, and it is a bounded check, not boundary coverage |

Three of the five "false" rows were things I had written a *passing test* for. The common cause
is that I reasoned about `snap.py` and `status.py` from their docstrings instead of reading the
comparisons, and then wrote tests that encoded the same misreading — so the tests confirmed the
belief rather than the behaviour. The repair that generalises: when a claim is about a
*boundary* (`>` vs `<`, floor vs ceiling, which side is excluded), read the line, and build the
fixture from the domain the code actually admits.

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

Also corrected: `cell_for_xy` tested the *derived index* against the grid's bounds instead of
the coordinate, which let floating-point rounding contradict the declared footprint in both
directions — with `x_min = 450000.1` and `cell_m = 123.4`, `x_max` itself divided into column
`ncols - 1` and so read as inside, while a value one ulp below `x_max` on another grid divided
into `ncols` and read as outside. The footprint now decides membership and the index is derived
and clamped afterwards, which cannot do either.

And a licence gap: the sheet republishes `buildings_in_cell` with no notice. Declining to put
individual footprints in it was a project-use restriction, not evidence the licences forbid
publishing centroids, and a count raster carries ODbL §4.3 and CC BY notice obligations anyway.
Attribution is now in both the sheet's README and its `.meta.json`. Whether a full count raster
is a Produced Work or a derivative database is **not settled** and should be before anything
wider is published.

**Pass 27 then found that one of these repairs was itself a false refusal.** The horizon
plausibility check rejected a *legitimate* `build_layer_surface` output: on a straight 11 km edge
with cells at 9,990 m and 10,090 m, the largest finite time falls **64.3 s** below a true 7,200 s
horizon, and my flat 60 s threshold called that an inconsistent build. The justification — "walking
60 s covers 84 m, under one cell" — was the same shape of error as the original: a plausible
sentence standing in for a bound that does not exist. There is **no sound upper bound** on the gap
between a horizon and the largest finite time, because the frontier can be arbitrarily sparse. So
the check is now explicitly a **heuristic**, its scale is derived
(`(max_access_m + cell_m) / access_speed_mps` = 238 s for a 100 m walk grid, which admits pass 27's
64.3 s and still catches a 60-minute layer read as 120), the provenance record carries
`is_a_heuristic: true`, and `--horizon-min` declares the horizon outright when certainty is needed.
And "only the build sidecar can bind the files into one build" was true of no implementation until
the builder started recording the arrays' digests, which it now does and the consumer checks.

**Next:** plan §0 step 1, the cheap correctness debts. Non-finite coordinates are now rejected at
`cell_for_lonlat`, which is one entry point of several. Codex pass 26's own recommendation is to
let the owner start walking a short local sheet while steps 1 and 2 proceed, and **not** to
expand this harness further — that would repeat pass 25's mistake.
