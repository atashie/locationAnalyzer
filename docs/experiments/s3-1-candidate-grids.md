# S3.1 — the matched 100 m / 200 m grid comparison

**2026-11-13, revised the same day after Codex pass 43.** Step 5 of the S3 execution plan's §0.
`v2/scripts/compare_candidate_grids.py`, `docs/experiments/s3-1-candidate-grids.json`, the full
slider sweep in `s3-1-threshold-sweep.json`, and the candidate layer
`v2/data/layers/own_triangle_grocery_walk_cell200.*`. Review in
`docs/research/44-codex-review-pass43-counterexamples/`.

**Pass 43 reproduced every verdict count here and corrected two claims around them** — a peak that
was a property of the four thresholds I happened to report, and wording that read a disagreement
between two versions of our own model as a household being told the wrong thing.

**The decision S3 exists to make, and it is now made by measurement: keep the 100 m grid.** The
200 m candidate saves four fifths of the cells and roughly doubles the error at a household's
address.

## How it was measured, and why not the obvious way

The two candidate grids are **not nested**. `TRIANGLE.grid(100)` has origin 661900/4003500 and is
514 × 643; `TRIANGLE.grid(200)` has origin 661800/4003600 and is 258 × 322. Their cell centres are
different places, so sampling each grid at its own centres would confound resolution with alignment
and with which patch of ground was asked about.

So the unit here is a **structure, not a cell**. Frame B's population — all 512,633 Overture
structure centroids inside the published footprint, of 522,160 rows — is evaluated three ways from
one graph, one destination set and one multi-source Dijkstra:

| value | what it is |
|---|---|
| `address` | the answer at the structure's own centroid — what the pipeline would say if it answered per address |
| `cell100` | the answer at the centre of the 100 m cell containing it — **what the product ships today** |
| `cell200` | the answer at the centre of the 200 m cell containing it |

Only the grid varies between the last two. The first is the reference: `cell100 − address` is what
the current product already costs a household by answering for a cell, and `cell200 − cell100` is
what the candidate would add.

Offsets are what geometry demands and are worth stating, because they are the mechanism:

| grid | cells | median centroid-to-centre | p95 | max |
|---|---|---|---|---|
| 100 m | 330,502 | 39.9 m | 59.9 m | 70.5 m |
| 200 m | 83,076 | 79.8 m | 119.9 m | 141.2 m |

## Signed paired seconds

498,000-odd structures where both sides answered. Never a mean of means — the tail is where a
verdict flips.

| pair | median | p05 | p95 | &#124;d&#124; > 120 s |
|---|---|---|---|---|
| `cell100 − address` | −2.8 s | −91 | +82 | 32,094 |
| `cell200 − address` | −1.7 s | −165 | +152 | **76,777** |
| `cell200 − cell100` | +1.5 s | −156 | +148 | 70,174 |

The medians are near zero and say almost nothing: cell-centre error is roughly symmetric. The
spread is the finding. Going to 200 m widens the p05–p95 band from about ±85 s to about ±160 s and
**2.4× more structures land more than two minutes from their own answer**.

## Verdicts that move, which is what a household is handed

Counts of structures out of 512,633.

| *T* | `cell100` vs address | `cell200` vs address | `cell200` vs `cell100` |
|---|---|---|---|
| 10 min | 11,246 (2.19%) | 19,527 (**3.81%**) | 19,245 (3.75%) |
| 15 min | 12,935 (2.52%) | 22,430 (**4.38%**) | 21,998 (4.29%) |
| 25 min | 8,227 (1.60%) | 14,566 (2.84%) | 14,564 (2.84%) |
| 45 min | 3,327 (0.65%) | 6,097 (1.19%) | 5,977 (1.17%) |

**The 200 m grid is about 1.7× worse at every threshold**, and worse in both directions rather
than merely more cautious. At *T* = 15 it disagrees with the address answer by excluding 9,951
structures the address answer includes, and including 11,620 it excludes, against 5,646 and 6,827
for the 100 m grid.

> **What these transitions are, and are not (pass 43 F9).** The `address` column is **our own
> model** evaluated at the structure's coordinate, not ground truth. It shares every model defect
> with the two cell columns — the same graph, the same destinations, the same speeds — so it is a
> legitimate reference for measuring *this model's discretisation*, and it is not evidence about
> what a household would find on the ground. A transition is a disagreement between two evaluation
> points of one model, not a wrong answer observed. The wording above said "wrongly excludes", and
> that overstated it.

> **The peak is at 14 minutes, not 15 (pass 43 F6).** 15 was the largest of the four thresholds I
> reported, which is a claim about those four. Sweeping every whole minute the slider can produce,
> 1 to 60, the maximum against the address answer is at **14 minutes** — 13,225 for 100 m and
> 22,794 for 200 m, against 12,935 and 22,430 at 15 — and the 200 m-against-100 m maximum is at
> **13**. The explanation I offered, that this is where the most structures sit near a boundary,
> was never measured and is withdrawn.

## The decision

**Keep 100 m.** The 200 m grid's only argument is size — 83,076 source cells against 330,502 —
and it roughly doubles the rate at which the published cell answer differs from the answer at the
address itself.

> **The size argument is weaker than it first looked (pass 43 F5).** Both candidates export to the
> same 514 × 643 WGS84 raster, so the 200 m layer's **raw transfer is identical** and its deflated
> transfer is about half, not a quarter — the quarter-size saving is in source cells. And whether
> any of that is noticeable on a handset is unmeasured: decode latency needs a device, which is
> step 6's open item. "The saving buys nothing a household notices" is withdrawn as unmeasured.

What this does **not** settle:

* **a grid finer than 100 m was not measured.** `cell100 − address` is still 2.19–2.52% at the two
  thresholds that matter, which is the cost of answering per cell at all, and it is the number a
  finer grid would have to beat.
* **the browser does not receive either candidate.** It receives a third grid — a WGS84 raster
  reprojected from the UTM source — whose re-tiling moves another 2.42% of structures at 15
  minutes and omits 12,182 of them entirely. That is measured in
  `docs/experiments/s3-5-export-regrid.json` and reported in the S3.5 write-up. It applies equally
  to both candidates and does not change the ranking, but the decision was made on the source
  layers and the product ships the raster.
* **the population is the 100 m grid's, which makes the coverage comparison asymmetric.** Every
  structure selected here lies inside both grids, but the 200 m footprint contains **905 further
  accepted structures** that the 100 m population definition excludes. Pass 43 confirmed that
  cannot reverse the ranking at any reported threshold. `structure_population` also uses the
  opposite north/south boundary convention from `GridSpec.cell_for_xy`; no selected structure sits
  on the boundary where that matters in this run.

## A by-product: the shipped encoding loses about 10,000 structures

The same run compared each structure's verdict from the float surface against the verdict reachable
from the **published byte**. At every threshold, about 10,000 structures differ — 10,253 at *T* = 10
and 9,967 at *T* = 25 and 45.

None of that is a rounding error. `encode_minutes` rounds up, so `ceil(s/60) ≤ T` is exactly
`s ≤ 60T` and a finite cell's encoded verdict equals its float verdict. The difference is entirely
cells with **no** finite time: the v1 wire format has one `NODATA` code, so a decoder holding only
the minutes plane must call every missing value unknown, while `evaluate` proves 16,209
`BEYOND_HORIZON` cells and 2,439 bounded `OFF_NETWORK` cells to be **known failures** at ten
minutes.

That is step 6's defect, measured here on the structure population rather than argued. The
`published-v2` format and its decoder are the fix, and `v2/tests/test_wire.py` asserts they
reproduce `evaluate` cell for cell on all 330,502 published cells at ten thresholds.
