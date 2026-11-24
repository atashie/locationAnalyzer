---
title: "Codex raw report: the supermarket default layer review"
date: 2026-11-23
reviewer: Codex (gpt-6.1-sol)
status: verbatim, unedited
note: >
  The reviewer's own words, kept so the findings write-up can be checked against them. Codex could
  not run Python in its environment, so every checkable claim here was reproduced locally before
  being credited; the reproductions are in the findings note beside this file. Where Codex proposed
  a settling test rather than an outcome, that distinction is its own and is preserved.
---

I reviewed all five commits and the current code read-only. I edited no files and ran no Python or
tests. Runtime-dependent conclusions below include the check needed to settle them.

1. **The coverage table does not establish the claimed household impact (item 7). Confidence: high
   about the measurement gaps; numerical effects unverified.**

   Leading with **20-minute eligibility is correct**. But "66,925 buildings lose an answer"
   overstates what the table establishes:

   - **These are source-grid counts.** `s2_building_weighted_coverage.py` bins building centroids
     into UTM cells. The exporter reprojects those cells, crops the footprint, and the browser
     introduces another placement distinction. The existing regrid measurement
     (`v2/scripts/measure_export_regrid.py`) documents these differences. The counts cannot yet be
     described as exactly what households encounter.
   - **A net difference is not a count of losses.** This model selects minimum **cost** and reports
     that route's **time**, so supermarket PASS results need not be a subset of grocery PASS
     results. Exact counterexample at 20 minutes: a supermarket route takes 1,140 seconds with cost
     1,260; another grocery route takes 1,250 seconds with cost 1,250. Grocery selects the latter
     and fails; supermarket passes. The repository already explains this mechanism in
     `v2/spikes/s2_destination_monotonicity.py`.
   - **Failing the threshold is different from losing an answer.** Grocery 19 minutes →
     supermarket 21 minutes loses eligibility while retaining a perfectly explicit answer.
   - **Building counts are defensible as a diagnostic, not as household counts.** The denominator is
     512,633 structures inside the source grid. It cannot support "27% of households." On the
     supplied numbers, the result is a **27.4% relative net reduction in passing structures**, or
     **13.1 percentage points** of that building population.
   - "Any answer at all" actually means an answer within the **120-minute build horizon**.
   - "100% classified supermarket" follows from the selector's class filter. It is not independent
     validation. Likewise, the uncorroborated screen explicitly sets aside ordinary
     recognised-chain records, so zero overlap with its 76-record residue is limited evidence.

   **Instead:** report paired PASS/FAIL/UNKNOWN transitions at 20 minutes, first on the source grid
   and then at the same buildings' exported/browser lookups. Keep the building limitation beside the
   headline.

   **Settling test:** reproject both current surfaces in memory using the exporter, evaluate both at
   identical building coordinates, and count transitions using both raster lookup rows and
   `measure_export_regrid.mercator_rows`. Any different totals disprove the literal browser-impact
   figures. Any supermarket gain disproves treating the net difference as gross losses.

   These figures justify disclosing a substantial eligibility reduction. They do **not**, by
   themselves, justify reversing the owner's weekly-shop definition or establish that the narrower
   layer is more accurate.

2. **"Switch on any grocery" does not broaden the default results (items 6-7). Confidence: high.**

   The new supermarket criterion starts enabled. Checking "Any grocery shop" leaves it enabled: the
   UI handles each checkbox independently (`v2/spikes/g3-render/app.js:553`), and the worker
   intersects enabled criteria.

   **Exact state:** supermarket = 25 minutes, grocery = 10 minutes, both thresholds = 20. Checking
   grocery still excludes the cell because supermarket fails. The smaller shops are available as
   data, but the natural action described in the prompt does not restore their coverage.

   **Instead:** make grocery scope a choice -- "Supermarkets" versus "Any grocery" -- or explicitly
   replace the active supermarket criterion when broader grocery is selected.

   **Settling test:** initialise the worker with that one-cell fixture and enable both criteria.
   EXCLUDED confirms the current intersection; the intended scope-switch interaction should yield
   INCLUDED.

3. **The three omissions are real, and the proposed host-building route has an existing
   counterexample (item 2). Confidence: high on selection behaviour; current footprint measurements
   unverified.**

   The omitted IDs are:

   - Buffaloe Bend Publix: `5074229c-e884-4097-8759-4308ddbab7e8`
   - Middle Creek Crossings Publix: `c7fee873-a3c5-4691-8b12-f2c76bb101b9`
   - Clayton Walmart Supercenter: `182dc975-ff2e-4be1-8811-0dc710b42547`

   With the specified empty brands and no classification-table entry, inclusion inheritance admits
   them only as candidates; `classify_grocery` returns `unclassified`, and the default rejects them.

   **The name-table approach is consistent with the November 18 narrowing.** Looking up Publix or
   Walmart in the explicit chain table does not invent a new chain.

   However, the saved name-recovery sheet
   (`docs/experiments/audit/grocery-name-recovery.csv`, line 22) records **no qualifying nearby
   building for all three**. That is historical evidence, not a fresh measurement, but it directly
   challenges the plan to obtain host-building corroboration. The inclusion reasons already carry
   OSM/locator evidence.

   **Instead:** record the reviewed weekly-shop classification by ID using the existing independent
   evidence. Preserve the distinction between curated decisions and the regenerable
   `NAME_CONFIRMED_SUPERMARKETS` table; otherwise regeneration can erase manual exceptions.
   Recompute coverage afterward.

   **Settling test:** for those three IDs, assert both supermarket classification and membership in
   `select_overture(places, "supermarket")`. Separately rerun `corroboration` against the current
   buildings. A non-CORROBORATED result demonstrates that the proposed automatic recovery cannot
   admit that record.

4. **The exporter's refusal happens after publication files have changed (item 6). Confidence:
   high.**

   The declared set **is complete for the exporter's current writes**: value, status, destination,
   destination table, flag, attribution, licence/notice files, and manifest. That suspected defect
   is fine.

   The actual defect is sequencing: the manifest is overwritten before undeclared files are checked
   (`v2/scripts/export_published_layers.py:843`). The planes and licensing files have already been
   overwritten too.

   **Exact state:** an existing served bundle contains `left_behind.value.bin`; otherwise valid
   inputs produce changed output. `main()` updates the bundle, then raises because of the orphan. A
   failed export has nevertheless changed the served publication.

   **Instead:** build and validate in a staging directory, then promote the complete bundle. At
   minimum, detect undeclared files before changing the destination.

   **Settling test:** snapshot every byte in a temporary existing bundle, add an orphan, run a valid
   changed export expecting `SystemExit`, then compare snapshots. Any changed publication file
   proves the defect. The new tests exercise `undeclared_files`, not this refusal behaviour.

5. **The globals are mostly harmless for normal CLI use; the flag writer has a separate
   surface-binding weakness (item 5). Confidence: high about the code path; prevalence unverified.**

   In a single CLI invocation, `MODE`, `CATEGORY`, and `STEM` are assigned consistently before use.
   I found no ordinary serial path that computes drive destinations and writes them under the walk
   stem. The destination writer also checks recomputed seconds against stored seconds.

   There is a smaller re-entry problem: `main(["--category", "supermarket", "--mode", "drive"])`
   changes the defaults subsequently read by `main([])`. Use immutable defaults and local variables
   if repeated invocation is supported.

   More consequentially, the flag writer fingerprints whatever stored surface exists
   (`v2/scripts/flag_restricted_routes.py:236`), without establishing that its recomputation
   describes that surface. This weakness predates these commits; existence and a matching stem do
   not close it.

   **Exact state:** stored seconds are 600 and newly computed seconds are 660, with identical
   dimensions and OK statuses. A newly computed flag can be stamped with the old surface's
   fingerprint. The exporter's fingerprint check then has no basis to detect the mismatch.

   **Instead:** compare recomputed stored-precision seconds and reasons before writing or
   fingerprinting flags, as the destination writer already does for seconds.

   **Settling test:** inject those old/new surfaces into a temporary flag-writer run. Successful
   output carrying the old fingerprint proves false binding; the corrected writer should refuse
   before writing.

6. **Ask 14's guard is reachable and logically sound, but optional data makes it an optional
   safeguard (item 3). Confidence: high from inspection.**

   The test selects grocery records and then independently classifies them. Grocery has no class
   filter, so a newly refused brand remains selected and reaches the assertion. The two explicit
   exclusions correctly enter `DROPPED_PLACE_IDS` at import and are removed by `drop_excluded`.

   **Exact gap:** on a clean checkout without the ignored accepted-place parquet, the test skips.
   The exporter does not itself invoke it. A green suite therefore need not establish that the
   promised guard ran.

   **Instead:** require this data-backed check in the publication workflow and reject skipped
   execution there. An always-running synthetic positive control would also establish that the
   assertion can fail.

   **Settling test:** temporarily monkeypatch `NOT_A_GROCERY_BRANDS` to include `Food Lion`, then
   invoke `test_no_published_grocery_record_is_one_our_own_classifier_refuses` against the accepted
   frame. It should fail listing surviving Food Lion records.

   **The footprint reasoning in both new exclusion entries is fine.** Neither uses a building's
   presence as evidence that the record is a shop or as evidence supporting removal.

7. **The inclusion ordering and remaining symmetry calls are fine as currently used (items 1 and
   4). Confidence: high from inspection.**

   **Item 1:** `(taxonomy OR admission) AND class`, followed by exclusions, implements the stated
   distinction correctly. Grocery has no class filter, so moving admission earlier does not change
   its selection algebra. Its 555 → 553 change belongs to ask 14. Other unchanged categories retain
   their prior behaviour; specialty inheritance is explicit. I have not independently executed the
   claimed counts.

   **Item 4:** `symmetrise_for_mode` preserves walk behaviour, leaves drive/bike directed, and
   rejects unknown modes. The remaining parameterised callers guard their calls with
   `mode == "walk"`; unconditional callers use walk constants or literal walk mode. I found no live
   non-walk misuse. The claim that all remaining callers are "walk-mode" is imprecise -- some
   support drive/bike safely -- but migrating them all is not required to fix a current routing
   defect.

The source-grid portion of item 7 can be settled without rebuilding anything. From the repository
root, this **unrun, read-only** command prints grocery passes, supermarket passes, gross losses,
and gains:

```
from pathlib import Path
import numpy as np

p = Path("v2/data/layers")
w = np.load(p / "own_triangle_buildings_per_cell.npy")
def load(category):
    stem = f"own_triangle_{category}_walk"
    return (np.load(p / f"{stem}.npy"),
            np.load(p / f"{stem}_reason.npy"))

g, gr = load("grocery")
s, sr = load("supermarket")
assert g.shape == s.shape == gr.shape == sr.shape == w.shape
print("minutes grocery supermarket lost gained")
for minutes in (10, 15, 20, 25, 45, 120):
    a = (gr == 0) & (g <= minutes * 60)
    b = (sr == 0) & (s <= minutes * 60)
    print(minutes, *(int(w[m].sum())
                     for m in (a, b, a & ~b, ~a & b)))
```

A nonzero `gained` count proves that the corresponding table difference understates gross losses.
Zero gains validates that interpretation only for the source-grid population.
