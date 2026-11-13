# S3.1 — the matched 100 m / 200 m grid comparison

**2026-11-13.** Step 5 of the S3 execution plan's §0. `v2/scripts/compare_candidate_grids.py`,
`docs/experiments/s3-1-candidate-grids.json`, and the candidate layer
`v2/data/layers/own_triangle_grocery_walk_cell200.*`.

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

**The 200 m grid is about 1.7× worse at every threshold**, and worse in both directions rather than
merely more cautious. At *T* = 15 it wrongly excludes 9,951 structures that qualify and wrongly
includes 11,620 that do not, against 5,646 and 6,827 for the 100 m grid.

The error peaks at 15 minutes, not at 10. That is where the most structures sit near a boundary, so
it is the threshold most sensitive to the grid, and it is one of the two the product leads with.

## The decision

**Keep 100 m.** The 200 m grid's only argument is size — 83,076 cells against 330,502, a quarter of
the bytes — and the browser already holds the 100 m layer at 174 KB deflated, so the saving buys
nothing a household notices. Against that it roughly doubles the rate at which a household is told
the wrong thing about their own address.

What this does **not** settle: a grid finer than 100 m was not measured, and the figures above say
nothing about one. `cell100 − address` is still 2.19–2.52% at the two thresholds that matter, which
is the cost of answering per cell at all, and it is the number a finer grid would have to beat.

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
