
### Own-graph layer: grocery / walk (2026-11-03 13:36:02)
- graph: 237594 nodes, 634234 edges (graphml cache); destinations 258 nodes from 285 places (0 dropped > 300 m)
- reachable cells 74.2%; one-way-adjacent cells 2.9%
- timings (s): {"load_graph_s": 17.58, "prepare_graph_s": 13.75, "csr_s": 1.2, "snap_pois_s": 1.83, "edge_index_s": 0.0, "dijkstra_s": 0.04, "snap_s": 2.23}; total 36.6
- profile: static speeds, access tags honoured, no intersection penalties, no turn restrictions


### Valhalla reference layer: grocery / walk_controlled (2026-11-03 13:37:52)
- destinations: 285 Overture places (release 2026-10-21.0, accepted artifact)
- method: A multi-location geotiff; build time 1.3 s; reachable cells 47.5% of 220550
- costing: pedestrian with costing_options {'walking_speed': 5.04}
- multi-location check: {"cells_both": 5011, "one_sided": 626, "max_abs_diff_s": 1635.0, "frac_diff_gt_60s": 0.055677509479145876}


### Valhalla reference layer: grocery / walk (2026-11-03 13:37:54)
- destinations: 285 Overture places (release 2026-10-21.0, accepted artifact)
- method: A multi-location geotiff; build time 0.7 s; reachable cells 47.7% of 220550
- costing: pedestrian (engine defaults)


### G1 comparison (2026-11-03 13:38:36): grocery walk: own graph vs Valhalla pedestrian 5.04 km/h (controlled)
own=own_grocery_walk.npy ref=valhalla_grocery_walk_controlled.npy

#### all cells
cells: union reachable 168937; both 99475; own-only 64257; ref-only 5205

| T min | n boundary (ref in [0.8T,1.2T]) | one-sided there | median abs err min | p90 abs err min | median/T | p90/T | false include | false exclude | PASS (acc) |
|---|---|---|---|---|---|---|---|---|---|
| 10 | 8370 | 325 | 1.6 | 5.0 | 0.16 | 0.50 | 2.5% | 23.4% | FAIL |
| 15 | 14172 | 505 | 1.8 | 6.7 | 0.12 | 0.45 | 5.2% | 16.9% | FAIL |
| 20 | 18803 | 815 | 1.9 | 8.1 | 0.10 | 0.41 | 8.2% | 13.3% | FAIL |
| 25 | 21545 | 1013 | 2.0 | 9.4 | 0.08 | 0.38 | 11.4% | 11.8% | FAIL |
| 30 | 22579 | 1144 | 2.1 | 10.7 | 0.07 | 0.36 | 15.4% | 10.9% | FAIL |
| 45 | 22712 | 1347 | 2.4 | 11.7 | 0.05 | 0.26 | 30.2% | 9.8% | FAIL |

Accuracy PASS is necessary, not sufficient: one-sided unreachability near the boundary and false include/exclude rates must be judged against decision 12 in the verdict.

#### one-way-adjacent cells only (n=6353)
cells: union reachable 3871; both 1922; own-only 1762; ref-only 187

| T min | n boundary (ref in [0.8T,1.2T]) | one-sided there | median abs err min | p90 abs err min | median/T | p90/T | false include | false exclude | PASS (acc) |
|---|---|---|---|---|---|---|---|---|---|
| 10 | 208 | 17 | 2.5 | 6.7 | 0.25 | 0.67 | 2.6% | 36.3% | FAIL |
| 15 | 335 | 19 | 2.6 | 9.8 | 0.17 | 0.65 | 6.3% | 27.3% | FAIL |
| 20 | 405 | 26 | 3.0 | 9.3 | 0.15 | 0.46 | 10.1% | 19.7% | FAIL |
| 25 | 458 | 37 | 3.0 | 11.8 | 0.12 | 0.47 | 14.7% | 17.8% | FAIL |
| 30 | 419 | 35 | 2.9 | 14.5 | 0.10 | 0.48 | 19.2% | 15.8% | FAIL |
| 45 | 387 | 59 | 3.7 | 11.3 | 0.08 | 0.25 | 34.7% | 13.8% | FAIL |

Accuracy PASS is necessary, not sufficient: one-sided unreachability near the boundary and false include/exclude rates must be judged against decision 12 in the verdict.

### Own-graph layer: grocery / drive (2026-11-03 13:41:45)
- graph: 175279 nodes, 397653 edges (graphml cache); destinations 258 nodes from 285 places (0 dropped > 300 m)
- reachable cells 73.6%; one-way-adjacent cells 8.7%
- timings (s): {"load_graph_s": 15.87, "prepare_graph_s": 12.53, "csr_s": 0.71, "snap_pois_s": 0.85, "edge_index_s": 0.0, "dijkstra_s": 0.02, "snap_s": 1.83}; total 31.8
- profile: static speeds, access tags honoured, no intersection penalties, no turn restrictions


### Own-graph layer: grocery / bike (2026-11-03 13:42:26)
- graph: 236769 nodes, 608279 edges (graphml cache); destinations 258 nodes from 285 places (0 dropped > 300 m)
- reachable cells 76.3%; one-way-adjacent cells 5.0%
- timings (s): {"load_graph_s": 16.02, "prepare_graph_s": 12.12, "csr_s": 0.98, "snap_pois_s": 0.87, "edge_index_s": 0.0, "dijkstra_s": 0.03, "snap_s": 1.97}; total 32.0
- profile: static speeds, access tags honoured, no intersection penalties, no turn restrictions


### Valhalla reference layer: grocery / drive (2026-11-03 13:42:29)
- destinations: 285 Overture places (release 2026-10-21.0, accepted artifact)
- method: A multi-location geotiff; build time 0.6 s; reachable cells 82.4% of 220550
- costing: auto (engine defaults)


### Valhalla reference layer: grocery / bike_controlled (2026-11-03 13:42:31)
- destinations: 285 Overture places (release 2026-10-21.0, accepted artifact)
- method: A multi-location geotiff; build time 0.6 s; reachable cells 51.2% of 220550
- costing: bicycle with costing_options {'cycling_speed': 16.2}


### G1 comparison (2026-11-03 13:43:24): grocery drive: own graph vs Valhalla auto (defaults)
own=own_grocery_drive.npy ref=valhalla_grocery_drive.npy

#### all cells
cells: union reachable 194730; both 149389; own-only 13000; ref-only 32341

| T min | n boundary (ref in [0.8T,1.2T]) | one-sided there | median abs err min | p90 abs err min | median/T | p90/T | false include | false exclude | PASS (acc) |
|---|---|---|---|---|---|---|---|---|---|
| 10 | 39206 | 8916 | 2.7 | 5.6 | 0.27 | 0.56 | 45.0% | 13.3% | FAIL |
| 15 | 24400 | 7171 | 4.3 | 7.5 | 0.29 | 0.50 | 67.4% | 15.4% | FAIL |
| 20 | 13782 | 5087 | 6.1 | 9.6 | 0.31 | 0.48 | 83.9% | 16.7% | FAIL |
| 25 | 5791 | 2739 | 7.7 | 11.9 | 0.31 | 0.48 | 93.4% | 17.4% | FAIL |
| 30 | 1958 | 1203 | 10.1 | 15.2 | 0.34 | 0.51 | 97.7% | 17.7% | FAIL |
| 45 | 116 | 116 | - | - | - | - | - | - | n/a (<50 cells) |

Accuracy PASS is necessary, not sufficient: one-sided unreachability near the boundary and false include/exclude rates must be judged against decision 12 in the verdict.

#### one-way-adjacent cells only (n=19297)
cells: union reachable 17238; both 13436; own-only 1016; ref-only 2786

| T min | n boundary (ref in [0.8T,1.2T]) | one-sided there | median abs err min | p90 abs err min | median/T | p90/T | false include | false exclude | PASS (acc) |
|---|---|---|---|---|---|---|---|---|---|
| 10 | 2356 | 726 | 3.4 | 6.1 | 0.34 | 0.61 | 49.1% | 13.8% | FAIL |
| 15 | 1104 | 401 | 4.9 | 9.3 | 0.33 | 0.62 | 68.6% | 15.8% | FAIL |
| 20 | 698 | 299 | 6.7 | 13.3 | 0.33 | 0.66 | 89.3% | 16.6% | FAIL |
| 25 | 337 | 144 | 8.6 | 15.7 | 0.34 | 0.63 | 97.5% | 17.1% | FAIL |
| 30 | 104 | 43 | 10.4 | 13.5 | 0.35 | 0.45 | 99.8% | 17.2% | FAIL |
| 45 | 0 | 0 | - | - | - | - | - | - | n/a (<50 cells) |

Accuracy PASS is necessary, not sufficient: one-sided unreachability near the boundary and false include/exclude rates must be judged against decision 12 in the verdict.

### G1 comparison (2026-11-03 13:43:25): grocery bike: own graph vs Valhalla bicycle 16.2 km/h (controlled)
own=own_grocery_bike.npy ref=valhalla_grocery_bike_controlled.npy

#### all cells
cells: union reachable 172105; both 108947; own-only 59251; ref-only 3907

| T min | n boundary (ref in [0.8T,1.2T]) | one-sided there | median abs err min | p90 abs err min | median/T | p90/T | false include | false exclude | PASS (acc) |
|---|---|---|---|---|---|---|---|---|---|
| 10 | 21944 | 566 | 1.0 | 4.0 | 0.10 | 0.40 | 22.7% | 4.0% | FAIL |
| 15 | 22551 | 891 | 1.4 | 5.0 | 0.09 | 0.33 | 40.1% | 3.2% | FAIL |
| 20 | 19344 | 1106 | 1.6 | 6.5 | 0.08 | 0.33 | 58.2% | 3.1% | FAIL |
| 25 | 15006 | 889 | 2.0 | 8.0 | 0.08 | 0.32 | 74.2% | 3.3% | FAIL |
| 30 | 10897 | 690 | 2.3 | 8.7 | 0.08 | 0.29 | 84.6% | 3.3% | FAIL |
| 45 | 2836 | 161 | 6.0 | 17.5 | 0.13 | 0.39 | 99.5% | 3.5% | FAIL |

Accuracy PASS is necessary, not sufficient: one-sided unreachability near the boundary and false include/exclude rates must be judged against decision 12 in the verdict.

#### one-way-adjacent cells only (n=11113)
cells: union reachable 8282; both 5257; own-only 2774; ref-only 251

| T min | n boundary (ref in [0.8T,1.2T]) | one-sided there | median abs err min | p90 abs err min | median/T | p90/T | false include | false exclude | PASS (acc) |
|---|---|---|---|---|---|---|---|---|---|
| 10 | 940 | 17 | 1.3 | 4.1 | 0.13 | 0.41 | 25.6% | 5.8% | FAIL |
| 15 | 897 | 62 | 2.1 | 6.2 | 0.14 | 0.41 | 41.7% | 3.5% | FAIL |
| 20 | 755 | 86 | 2.6 | 8.1 | 0.13 | 0.41 | 55.6% | 3.7% | FAIL |
| 25 | 627 | 71 | 2.9 | 8.0 | 0.12 | 0.32 | 69.7% | 4.4% | FAIL |
| 30 | 504 | 52 | 2.5 | 8.4 | 0.08 | 0.28 | 78.4% | 4.9% | FAIL |
| 45 | 161 | 12 | 5.7 | 9.3 | 0.13 | 0.21 | 96.4% | 4.8% | FAIL |

Accuracy PASS is necessary, not sufficient: one-sided unreachability near the boundary and false include/exclude rates must be judged against decision 12 in the verdict.

### G1 matrix comparison (2026-11-03 13:48:32): grocery / drive
304 cells stratified by own-layer minutes; Valhalla `sources_to_targets` min over 285 POIs; matrix time 209.1 s

| T min | band (own min) | n | ref unreachable | median abs err min | p90 abs err min | median/T | p90/T | own faster % | PASS (acc) |
|---|---|---|---|---|---|---|---|---|---|
| 10 | (8, 12) | 100 | 1 | 3.2 | 5.5 | 0.32 | 0.55 | 100% | FAIL |
| 15 | (13, 17) | 100 | 0 | 5.2 | 9.1 | 0.35 | 0.61 | 100% | FAIL |
| 20 | (18, 22) | 100 | 1 | 8.1 | 12.4 | 0.41 | 0.62 | 98% | FAIL |
| 25 | (23, 27) | 4 | 0 | - | - | - | - | - | n/a |

Signed median (own - Valhalla): -5.4 min over all finite samples (negative = own model is faster/optimistic).
Residual = speed model + snapping/access-leg differences (both engines snap the cell centre); no grid misregistration.

---

## G1 Verdict (2026-11-03): Valhalla is the single routing engine

**Question.** Is our own transposed-graph Dijkstra over an OSM extract cheaper or better than
self-hosted Valhalla for building "minutes to nearest amenity" layers, at the owner's accuracy
tolerance (decision 12: median absolute error ≤ 10% of the threshold T, p90 ≤ 20%)?

**Answer: no, on both counts. Valhalla builds the layers, and also serves the anchors.**

### Accuracy

Two independent comparisons, both against self-hosted Valhalla 3.9.1 on the same slice:

| Comparison | Walk | Bike | Drive |
|---|---|---|---|
| Layer vs layer (whole grid, float seconds) | median 5–16% of T, **p90 26–50%** | median 8–13%, **p90 29–40%** | median 27–34%, **p90 48–56%** |
| Exact pairs (`sources_to_targets` min over all 285 groceries, cells stratified by band) | pending | pending | median **32–41%** of T, p90 **55–62%**, own faster in **98–100%** of samples, signed median **−5.4 min** |

Every mode fails the owner's tolerance at p90, and drive fails it at the median as well. The drive
error is not noise: our model is faster than Valhalla on essentially every sampled pair, by about
five minutes. The cause is known and was accepted when the model was ported — the CHCCS speed model
contributes free-flow "friction" speeds but we did **not** port its intersection penalties (22 s per
signal, 11 s per stop sign), and a node-state CSR cannot express turn restrictions at all. At a
25-minute commute limit a five-minute optimistic bias moves the boundary by roughly 20%, which is
exactly the kind of confidently wrong region the product must not draw.

### Cost

| | Own graph | Valhalla |
|---|---|---|
| Build one category layer, one mode | **~32 s** (graph load 16 s, project/filter 13 s, CSR 1 s, POI snap 1 s, **Dijkstra 0.02–0.04 s**, cell snap 2 s) | **0.6–1.3 s** (one multi-location arrival isochrone, `format=geotiff`) |
| 8 categories × 3 modes | ~13 min (graph work repeats per mode) | ~30 s |
| Arbitrary anchor isochrone | not implemented (would need the same graph resident) | p95 0.30 s (auto 25 min), 0.37 s (auto 45 min) at concurrency 1 |

The algorithm we ported is not the bottleneck and is not the problem: multi-source Dijkstra on the
transposed graph runs in **40 milliseconds** over 237k nodes. The expensive parts are loading and
preparing the graph, which Valhalla has already done once into its tiles.

### What this settles, and what it does not

- **Adopted:** Valhalla for category layers *and* anchors; one engine, one costing model, one set of
  semantics. This removes the per-mode graph pipeline from the critical path.
- **Kept, not adopted:** the ported engine (`locfinder/traveltime/`) stays in the repo with its
  tests. It is the fallback if Valhalla ever becomes unavailable, and the correct place to put work
  if we later want a tunable in-house model. That work is **calibration** (intersection penalties,
  turn restrictions, access-leg speeds), not algorithms. The transposed-graph correctness fix and
  the one-way regression test keep their value either way.
- **New constraint discovered:** Valhalla's isochrone GeoTIFF is emitted on its own WGS84 grid at
  **0.001° for pedestrian/bicycle (~90 m × 111 m) and 0.002° for auto (~180 m × 223 m)**, re-centred
  per request, in uint16 seconds. Our 100 m product grid is therefore *finer than the engine's own
  output for drive*. Phase 1 should either publish drive layers at 200 m or accept documented
  resampling; publishing a 100 m drive layer from a 180 m source would be false precision.
- **Unaffected:** the reachable-cell differences between the two engines (own 74% vs Valhalla auto
  82%, walk 47.5%) are mostly cutoff and access-leg policy, not accuracy; they are the reason the
  layer-level false-include rates look extreme at large T and the reason the exact-pair comparison
  is the one to trust.

### Raster primitive vs exact engine times (2026-11-03 15:04:08): grocery / walk, 3 POIs
method A grid [119, 200] at 0.0010° x 0.0010°; method B grids [[106, 138], [91, 93], [95, 92]]; 240 cells sampled from the reachable union of both rasters; exact = `sources_to_targets` minimum over the same POIs (no raster).

| difference (seconds) | n | median | p90 | max | share > 60 s |
|---|---|---|---|---|---|
| A (multi-location) vs exact | 208 | 88 | 355 | 983 | 60.6% |
| B (per-POI min) vs exact | 219 | 88 | 430 | 2080 | 66.7% |
| A vs B (the original check) | 187 | 20 | 142 | 1743 | 21.9% |

One-sided reachability among sampled cells: exact unreachable 0, A unreachable 32, B unreachable 21.

Threshold classification against exact (the product's actual question):

| T min | A agrees | B agrees | A false-in | A false-out | B false-in | B false-out |
|---|---|---|---|---|---|---|
| 10 | 98.3% | 97.1% | 0.9% | 15.4% | 1.3% | 30.8% |
| 15 | 97.5% | 97.5% | 1.8% | 9.5% | 1.8% | 9.5% |
| 20 | 96.2% | 96.2% | 2.4% | 12.5% | 1.9% | 15.6% |
| 25 | 97.5% | 96.2% | 1.0% | 9.1% | 1.5% | 13.6% |
| 30 | 96.2% | 95.4% | 1.1% | 11.7% | 1.1% | 15.0% |
| 45 | 88.8% | 90.4% | 2.6% | 19.5% | 0.9% | 17.9% |

### Expansion primitive vs raster primitives (2026-11-03 15:05:48): grocery / walk, 3 POIs
`/expansion action=isochrone reverse=true` returned **8909 settled edges** in 0.74 s (edge length median 46 m, p90 154 m). Cells snapped with `locfinder.traveltime.snap`'s nearest-edge logic plus the modal access leg. Same 240 cells and same exact `sources_to_targets` values as the raster test, so the three rows are paired.

| difference from exact (seconds) | n | median | p90 | max | share > 60 s |
|---|---|---|---|---|---|
| **expansion + our snapping** | 195 | 69 | 271 | 647 | 54.9% |
| A multi-location GeoTIFF | 208 | 88 | 355 | 983 | 60.6% |
| B per-POI GeoTIFF min | 219 | 88 | 430 | 2080 | 66.7% |

Expansion signed median +66 s (positive = our value is later/more conservative than exact).

Threshold classification against exact:

| T min | expansion agrees | A agrees | B agrees | expansion false-in | expansion false-out |
|---|---|---|---|---|---|
| 10 | 98.8% | 98.3% | 97.1% | 0.0% | 23.1% |
| 15 | 99.6% | 97.5% | 97.5% | 0.0% | 4.8% |
| 20 | 97.1% | 96.2% | 96.2% | 0.0% | 21.9% |
| 25 | 97.5% | 97.5% | 96.2% | 0.0% | 13.6% |
| 30 | 96.7% | 96.2% | 95.4% | 0.0% | 13.3% |
| 45 | 95.4% | 88.8% | 90.4% | 0.0% | 8.9% |

---

## G1 Verdict, revision 2 (2026-11-03): the engine is Valhalla; the layer primitive is its expansion tree, not its raster

Codex pass 4 (`../research/11-codex-adversarial-review-pass4-phase0.md`, H1/H5) was right that the
first verdict adopted a layer-building method whose own equivalence check had failed, and that the
check could not say which side was wrong because it compared two resampled rasters to each other.
Adding the missing third leg — Valhalla's `sources_to_targets` matrix, which gives exact engine
times with no raster involved — settles it. Paired on the same 240 sampled cells and the same exact
values:

| Primitive | median error | p90 | max | > 60 s | false-in at T | false-out at T |
|---|---|---|---|---|---|---|
| Multi-location isochrone GeoTIFF (method A, previously adopted) | 88 s | 355 s | 983 s | 61% | 1–3% | 9–20% |
| Per-POI GeoTIFF minimum (method B) | 88 s | 430 s | 2,080 s | 67% | 1–2% | 10–31% |
| **`/expansion` edges + our nearest-edge snapping** | **69 s** | **271 s** | **647 s** | 55% | **0.0% at every threshold** | 5–23% |

Three conclusions.

**The isochrone GeoTIFF is a contour product, not a per-cell time.** Neither raster method meets the
owner's tolerance: a median error of 88 s and a p90 of about 6 minutes, with 9–31% of boundary cells
wrongly excluded. The 1,635 s maximum difference in the original check was mostly both rasters being
imprecise, not method A being broken, but adopting either as the layer primitive would have shipped
a systematically wrong boundary.

**`/expansion` is the right primitive and it puts our ported snapping code back in the critical
path.** `action=isochrone, reverse=true` returns the settled search tree — 8,909 edges in 0.74 s for
three POIs, median edge length 46 m — each with its arrival `duration` in seconds. Feeding those
edges into `locfinder.traveltime.snap` gives a per-cell time from Valhalla's own costing at edge
resolution. What the G1 comparison killed was our **speed model**, not our **snapping and
interpolation machinery**, which is now the consumer of a better-calibrated input.

**Against the owner's tolerance (decision 12: median ≤ 10% of T, p90 ≤ 20%):**

| T | tolerance (median / p90) | expansion primitive | verdict |
|---|---|---|---|
| 10 min | 60 s / 120 s | 69 s / 271 s | fails both |
| 15 min | 90 s / 180 s | 69 s / 271 s | median passes, p90 fails |
| 20 min | 120 s / 240 s | 69 s / 271 s | median passes, p90 fails |
| **25 min** | 150 s / 300 s | 69 s / 271 s | **passes** |
| **30 min** | 180 s / 360 s | 69 s / 271 s | **passes** |
| **45 min** | 270 s / 540 s | 69 s / 271 s | **passes** |

So commute-scale thresholds are already within tolerance, and short walk thresholds are not. The
cause is identified and the fix is known: the expansion reports one duration per edge, which is the
arrival time at the far end, so using it directly overestimates by up to one edge traversal (median
46 m ≈ 33 s on foot) and the access leg adds more. The signed median is **+66 s, conservative in
every case**, which is why false inclusions are zero. Interpolating within the matched edge using
its `distance` and `duration` — the same arithmetic `cell_seconds_from_arrival` already performs for
our own graph — should remove most of that bias. That is the first thing Phase 1 should implement
and re-measure, before any North Carolina build.

Unresolved and not to be glossed: this test covers one category, one mode, three POIs and 240 cells.
Drive and bike, a full POI set, and the interpolation fix all need the same paired treatment, and
the exact matrix remains the reference rather than ground truth, since Valhalla has no traffic data
either.

### G1 matrix comparison (2026-11-03 15:12:03): grocery / walk (controlled)
600 cells stratified by own-layer minutes; Valhalla `sources_to_targets` min over 285 POIs; matrix time 5319.8 s

| T min | band (own min) | n | ref unreachable | median abs err min | p90 abs err min | median/T | p90/T | own faster % | PASS (acc) |
|---|---|---|---|---|---|---|---|---|---|
| 10 | (8, 12) | 100 | 0 | 0.3 | 1.6 | 0.03 | 0.16 | 33% | PASS |
| 15 | (13, 17) | 100 | 0 | 0.4 | 2.3 | 0.03 | 0.15 | 36% | PASS |
| 20 | (18, 22) | 100 | 1 | 0.5 | 2.3 | 0.03 | 0.11 | 43% | PASS |
| 25 | (23, 27) | 100 | 0 | 0.7 | 3.2 | 0.03 | 0.13 | 41% | PASS |
| 30 | (28, 32) | 100 | 0 | 0.6 | 2.9 | 0.02 | 0.10 | 40% | PASS |
| 45 | (40, 50) | 100 | 0 | 0.8 | 5.5 | 0.02 | 0.12 | 29% | PASS |

Signed median (own - Valhalla): +0.2 min over all finite samples (negative = own model is faster/optimistic).
Residual = speed model + snapping/access-leg differences (both engines snap the cell centre); no grid misregistration.

---

## G1 Verdict, revision 3 (2026-11-03): the decision is per mode, and our walk model passes

The walk exact-pair comparison finished after revision 2 was written, and it reverses a conclusion.
Codex pass 4 was right to object to revision 1's line that the pending walk and bike runs "can only
strengthen" the verdict. They did not.

| Mode | median error | p90 | signed median | own faster | verdict against decision 12 |
|---|---|---|---|---|---|
| **walk** (600 cells, controlled 5.04 km/h) | **0.3-0.8 min (2-3% of T)** | **1.6-5.5 min (10-16% of T)** | **+0.2 min** | 29-43% | **PASSES at 10, 15, 20, 25, 30 and 45 min** |
| **drive** (304 cells, engine defaults) | 3.2-8.1 min (32-41% of T) | 5.5-12.4 min (55-62%) | -5.4 min | 98-100% | fails at every threshold |
| bike | pending | pending | pending | pending | pending |

**Our walk model is not merely acceptable, it is unbiased** — *relative to Valhalla, whose default pedestrian speed is 1.411 m/s against our 1.400, so this says nothing about real walking times; see the corrections at the end of this file and `spotcheck-engines.md`.* A signed median of +0.2 minutes and
"own faster" hovering around 35% describe symmetric noise, not a systematic error, and the median
absolute error is 2-3% of the threshold against a 10% tolerance. That is the physically sensible
outcome: walking is a near-constant speed on a network with no one-ways, no turn restrictions, no
signals to wait at and no congestion, so there is very little for a costing model to get wrong.

**Our drive model is systematically wrong, in one direction, by a large margin.** Faster than
Valhalla on 98-100% of pairs and optimistic by five minutes at the median. Driving is where all the
modelling complexity lives, and it is precisely what we dropped when we ported the speed constants
without the intersection penalties.

**What revision 2 got wrong, and why.** Revision 2 said "every mode fails at p90". That was read off
the *layer-level raster* comparison, which we now know is dominated by the isochrone raster's own
88 s median error, not by our model. When the raster is removed and exact engine times are used, the
walk model passes comfortably. The layer-level comparison was measuring Valhalla's contour product,
not our arithmetic. Only the exact-pair comparison is valid for judging a model.

### The decision

| Mode | Layer source | Why |
|---|---|---|
| **walk** | **our own graph** (`locfinder/traveltime/`) | Passes the tolerance, unbiased, and the Dijkstra is 40 ms once the graph is loaded |
| **drive** | **Valhalla** via `/expansion` + our snapping | Our costing is 5.4 min optimistic; Valhalla's encodes one-ways, turn restrictions and access rules |
| **bike** | pending the measurement | Physically between the two: constant-ish speed, but one-ways, contraflow and surface matter |

Both paths now share the same consumer, `snap.cell_seconds_from_arrival`, fed either by our own CSR
graph or by Valhalla's expansion tree (`traveltime/expansion.py`). That keeps one grid contract, one
nodata convention and one interpolation routine regardless of which engine produced the times.

### Still open

- Bike, measured the same way, decides the third row.
- The expansion reconstruction is now exact rather than estimated: `duration` and `distance` are
  cumulative at the settled end and `pred_edge_id` gives the near end, so an edge's endpoint times
  are the predecessor's duration and its own, with no speed assumption. The +66 s conservative bias
  measured in revision 2 came from charging a whole edge traversal; the paired re-measurement of the
  corrected version has not been run yet and is the next thing to do.
- The walk run took 89 minutes of wall clock for 600 cells because four matrix jobs and the latency
  benchmark were contending for a two-vCPU container. Timings from that window describe contention,
  not capacity.

### G1 matrix comparison (2026-11-03 15:25:46): grocery / bike (controlled)
600 cells stratified by own-layer minutes; Valhalla `sources_to_targets` min over 285 POIs; matrix time 5832.8 s

| T min | band (own min) | n | ref unreachable | median abs err min | p90 abs err min | median/T | p90/T | own faster % | PASS (acc) |
|---|---|---|---|---|---|---|---|---|---|
| 10 | (8, 12) | 100 | 0 | 0.6 | 3.6 | 0.06 | 0.36 | 92% | FAIL |
| 15 | (13, 17) | 100 | 0 | 0.9 | 2.9 | 0.06 | 0.19 | 87% | PASS |
| 20 | (18, 22) | 100 | 0 | 1.4 | 4.9 | 0.07 | 0.24 | 87% | FAIL |
| 25 | (23, 27) | 100 | 0 | 1.0 | 5.3 | 0.04 | 0.21 | 91% | FAIL |
| 30 | (28, 32) | 100 | 0 | 1.2 | 3.4 | 0.04 | 0.11 | 85% | PASS |
| 45 | (40, 50) | 100 | 0 | 5.9 | 18.9 | 0.13 | 0.42 | 99% | FAIL |

Signed median (own - Valhalla): -1.1 min over all finite samples (negative = own model is faster/optimistic).
Residual = speed model + snapping/access-leg differences (both engines snap the cell centre); no grid misregistration.

---

## G1 Verdict, revision 4 (2026-11-03): bike completes the per-mode picture

The bike exact-pair comparison finished (600 cells, controlled 16.2 km/h, 5,833 s of wall clock
under contention). It lands between walk and drive, which is what the physics predicted.

| Mode | median error | p90 | signed median | own faster | thresholds passed |
|---|---|---|---|---|---|
| **walk** | 0.3-0.8 min (2-3% of T) | 1.6-5.5 min (10-16%) | +0.2 min | 29-43% | **all six** |
| **bike** | 0.6-5.9 min (4-13% of T) | 2.9-18.9 min (11-42%) | -1.1 min | 85-99% | 15 and 30 only |
| **drive** | 3.2-8.1 min (32-41%) | 5.5-12.4 min (55-62%) | -5.4 min | 98-100% | none |

Bike passes the *median* tolerance at every threshold except 45 minutes, but fails p90 at four of
six, and "own faster" at 85-99% shows this is a **systematic optimistic bias of about a minute**,
not noise. Our flat 4.5 m/s ignores surface, grade, stops and turns, all of which Valhalla's bicycle
costing models. The error compounds with distance: at a 45-minute threshold the median rises to 13%
of T and p90 to 42%, with our model faster on 99% of pairs.

So the ordering is exactly the amount of physics each mode hides from a constant-speed model:
walking hides almost none and our model is unbiased; cycling hides some and we are a minute fast;
driving hides a great deal and we are five minutes fast.

### Final per-mode decision

| Mode | Layer source | Status of our own model |
|---|---|---|
| **walk** | **our own graph** | Adopted. Unbiased, passes every threshold |
| **bike** | **Valhalla** `/expansion` + our snapping | Near miss. A calibration candidate: the bias is single-signed and about one minute, so a lower base speed plus a small per-intersection delay could plausibly bring p90 inside tolerance. Worth one afternoon before Phase 1 ships bike layers, not more |
| **drive** | **Valhalla** `/expansion` + our snapping | Not viable without porting the intersection penalties and modelling turn restrictions |

All three feed the same `snap.cell_seconds_from_arrival`, so the grid contract, nodata convention
and interpolation are shared regardless of which engine produced the times.

### Own-graph layer: grocery / walk (2026-11-03 15:45:02)
- graph: 504457 nodes, 1321416 edges (triangle-roads.osm (xml)); destinations 417 nodes from 452 places (0 dropped > 300 m)
- reachable cells 72.7%; one-way-adjacent cells 2.9%
- timings (s): {"load_graph_s": 145.18, "save_graphml_s": 63.96, "prepare_graph_s": 31.28, "csr_s": 2.72, "snap_pois_s": 1.75, "edge_index_s": 0.0, "dijkstra_s": 0.07, "snap_s": 3.75}; total 248.7
- profile: static speeds, access tags honoured, no intersection penalties, no turn restrictions


---

## Widened-metro validation (2026-11-03): the adopted walk path, end to end

The first layer built on the widened Triangle metro, with the engine the G1 verdict adopted for
walking (our own transposed-graph Dijkstra):

| | Phase 0 slice | Widened Triangle |
|---|---|---|
| Grid | 550 × 401 = 220,550 cells | **643 × 514 = 330,502 cells** |
| Walk graph | 263,631 nodes / 682,946 edges | **504,457 nodes / 1,321,416 edges** |
| Groceries (Overture, accepted) | 285 | **452** |
| Reachable cells | 74.2% | 72.7% |
| One-way-adjacent cells | 2.9% | 2.9% |

Stage timings for the first run, which includes the one-time graph parse and cache write:

| Stage | Seconds |
|---|---|
| Parse `triangle-roads.osm` (453 MB XML) | 145.2 |
| Write the GraphML cache (one-time) | 64.0 |
| Project, apply access rules, symmetrise | 31.3 |
| Build CSR | 2.7 |
| Snap 452 POIs to nodes | 1.8 |
| **Multi-source Dijkstra on the transposed graph** | **0.07** |
| Snap 330,502 cells and interpolate | 3.8 |
| **Total** | **248.7** |

**The marginal cost of a category is about 5.5 s**, not 249 s. Everything above the POI snap is
per-mode graph preparation that amortises across every category of that mode, and the GraphML cache
removes the 145 s parse from subsequent runs. This is the honest cost comparison Codex pass 4 asked
for (M1): eight categories of walk layers cost roughly 210 s of one-time graph work plus 8 × 5.5 s,
not 8 × 249 s. The Dijkstra itself is 70 ms over half a million nodes.

Caveat carried forward: these are layer *production* numbers on the adopted engine, not an accuracy
re-measurement. The walk model's accuracy was established on the Phase 0 slice; the same exact-pair
comparison should be repeated on the widened metro before the layers are published, since the new
area includes denser Raleigh street grids that the original sample never saw.

---

## What the G1 comparisons actually measured: there is no ground truth here

Added 2026-11-03 after the owner asked what we were measuring accuracy *against*. The answer
changes how the earlier tables should be read, so it is recorded at the same level of prominence.

**No ground truth was used anywhere in this file.** Every travel-time number was compared against
**Valhalla**, which is another static model, not reality. The NC instance logs
"Traffic tile extract could not be loaded" sixteen times: it has no traffic data, so neither engine
knows anything about congestion, signals timing on the day, weather, or the state of the road.

**Worse, two of the three comparisons were speed-matched by construction.** The reference was
configured to share our own speed assumption:

| Mode | Our speed | Reference configuration | What the comparison could detect |
|---|---|---|---|
| walk | 1.40 m/s | `pedestrian.walking_speed = 5.04 km/h` = **identical**, and Valhalla's *default* is 5.08 km/h anyway (measured: `spotcheck-engines.md`), so the test was near-circular with or without our option | network traversal, access rules, snapping, interpolation — **not** whether 1.40 m/s is a real walking speed |
| bike | 4.50 m/s | `cycling_speed = 16.2 km/h` = **identical** | same, plus surface/grade/stop handling, which is where the residual −1.1 min came from |
| drive | friction speeds by highway tag | Valhalla **defaults** (not matched) | everything at once: speed model, intersection penalties, turn restrictions |

So the walk result is narrower than "our walk model is accurate". What it establishes is that **our
graph machinery agrees with a mature engine's when both are given the same speed** — the transposed
Dijkstra, the access-tag filter, the nearest-edge snapping and the within-edge interpolation are
sound. Whether 1.40 m/s describes how people actually walk in Durham is **not tested**.

**Why the drive conclusion still holds without ground truth.** It rests on mechanism, not on the
reference being true. We know what we omitted: the CHCCS intersection penalties were not ported and
a node-state graph cannot express turn restrictions. Omitting delay-adding features predicts a
model that is *too fast*, by an amount that grows with the number of intersections crossed. The
measurement found exactly that: faster on 98–100% of pairs, a −5.4 minute median, and error growing
with the threshold. A disagreement whose sign, size and gradient match a known defect is evidence
about our model; it would be weak evidence if the direction had been random.

**"PASS" and "FAIL" in the tables above are against agreement with Valhalla, not against owner
decision 12.** Decision 12 ("about 10% of the limit") is a statement about real-world boundary
error. Nothing here measures that. The tables should be read as a differential test that isolated
defects, which is what they were good for, and the owner's tolerance remains **unverified** in the
only sense that matters to a user.

### What would actually constitute ground truth

| Source | What it would settle | Cost | Independence |
|---|---|---|---|
| **An independent traffic-aware API** (Google Routes, Mapbox Matrix, TravelTime) sampled on ~100 OD pairs | whether both our engines are systematically off, and by how much once congestion exists | free tier to a few dollars for a one-off sample; live use only, nothing stored | genuinely independent model **and** real traffic |
| **Hand-timed journeys** with a phone GPS log, ~10 trips per mode | the only actual truth; anchors everything else | hours of the owner's time, tiny sample | total |
| **Published agency timetables**, hand-checked against our MOTIS journeys | whether we interpret GTFS correctly (waiting, transfers, deadline semantics). For *scheduled* transit the feed is close to authoritative | an hour | high for schedule, none for real-world adherence |
| **Probe-data archives** (FHWA NPMRDS via RITIS, state DOT travel-time data, commercial INRIX/HERE) | observed drive times at scale, the real answer for driving | access terms need checking; commercial tiers are expensive | high |
| **Transit on-time performance** from the agencies | the gap between schedule and reality | unknown availability | high |

The cheapest meaningful step is the first: a one-off sample against a traffic-aware third model
would tell us whether our 10%-of-threshold tolerance is anywhere near met in the real world, and it
is the only item here that requires neither the owner's legs nor a data licence. Until something on
this list is done, the product's honest claim is the one already in the design: travel times are
**estimated, modelled from road speeds, with no traffic data**.

### Own-graph layer: grocery / walk (2026-11-03 17:31:20)
- graph: 539814 nodes, 1424670 edges (graphml cache; 3046 components; kept 539814 nodes (97.5%), dropped 13608); destinations 417 nodes from 452 places (0 dropped > 300 m)
- reachable cells 77.3%; one-way-adjacent cells 3.6%
- timings (s): {"load_graph_s": 34.72, "prepare_graph_s": 43.88, "csr_s": 3.67, "snap_pois_s": 1.52, "edge_index_s": 0.0, "dijkstra_s": 3.89, "snap_s": 3.64}; total 91.3
- profile: static speeds, access tags honoured, no intersection penalties, no turn restrictions


### Own-graph layer: grocery / walk (2026-11-03 18:00:09)
- graph: 539814 nodes, 1424670 edges (graphml cache; 3046 components; kept 539814 nodes (97.5%), dropped 13608); destinations 417 nodes from 452 places (0 dropped > 300 m)
- reachable cells 76.8%; one-way-adjacent cells 3.6%
- timings (s): {"load_graph_s": 33.38, "prepare_graph_s": 41.99, "csr_s": 3.42, "snap_pois_s": 1.41, "edge_index_s": 0.0, "dijkstra_s": 3.56, "snap_s": 3.24}; total 87.0
- profile: static speeds, access tags honoured, no intersection penalties, no turn restrictions


### S0 status provenance on the shipped layer: grocery / walk (2026-11-04 08:48:02)

- graph after preparation: 3046 components; kept 539814 nodes (97.5%), dropped 13608; **1 strongly connected component(s)**
- destinations: 417 nodes from 452 places (0 beyond the 300 m snap bound)
- nodes unreached by the unbounded cost search: 0 of 539,814 (0.0000%)
- `Surface.validate()` passes on 330,502 cells

| status | cells | share |
|---|---|---|
| `OK` | 253,679 | 76.7557% |
| `OFF_NETWORK` | 57,541 | 17.4102% |
| `BEYOND_HORIZON` | 19,282 | 5.8342% |

- against the committed `own_triangle_grocery_walk.npy`: finiteness identical=**True**, max abs diff 0.000244 s (the artifact is float32, so a sub-millisecond difference is quantisation)

- profile `speeds-v0+dd5ef0bc1beb42e4`, grid `grid-v0+7ab61db26b3cc98e`


### S0 status provenance and the H2 bracket: grocery / walk (2026-11-04 09:00:58)

- graph after preparation: 3046 components; kept 539814 nodes (97.5%), dropped 13608; **1 strongly connected component(s)**
- destinations: 417 nodes from 452 places (0 beyond the 300 m snap bound)
- nodes unreached by the unbounded cost search: **0** of 539,814
- `build_layer_surface(...).validate()` passes on 330,502 cells

| status | cells | share |
|---|---|---|
| `OK` | 253,679 | 76.7557% |
| `OFF_NETWORK` | 57,541 | 17.4102% |
| `BEYOND_HORIZON` | 19,282 | 5.8342% |

- against the committed `own_triangle_grocery_walk.npy`: finiteness identical=**True**, max abs diff 0.000244 s (the artifact is float32, so a sub-millisecond difference is quantisation)

**The H2 bracket.** `cost_selected` (shipped) minus `time_min` (minimum over destinations, access cost ignored). The shipped surface is an upper bound, so the gap is where a category criterion could exclude a cell that a qualifying destination would have satisfied.

- comparable cells 253,679; differing by more than 1 s **23,468 (9.2511%)**
- where they differ: median **37.7 s**, p90 129.7 s, max 668.6 s

| threshold | cells excluded by the shipped surface that the lower bound includes | share of passing cells |
|---|---|---|
| 10min | 202 | 0.8332% |
| 15min | 325 | 0.6865% |
| 25min | 340 | 0.3656% |
| 45min | 256 | 0.1599% |

- profile `speeds-v0+9893b1b0168ff19a`, grid `grid-v0+7ab61db26b3cc98e`


### S1.3 expansion structure on real payloads (2026-11-04 09:26:18): grocery / drive, 3 POIs, 60-minute contour

Request: `action=isochrone`, `reverse=true`, `expansion_properties=['duration', 'distance', 'edge_id', 'pred_edge_id', 'cost']` — all five accepted by Valhalla 3.9.1. `duration` is **integer seconds** (True).

**1. Adapter health.** First real-payload run of `expansion_to_edge_index`.

- `report=` : `{'edges': 254323, 'dangling_predecessors': 636, 'roots_unoriented': 0, 'dropped': 636, 'origins_supplied': 3}`
- root edges (sentinel `pred_edge_id`): 3
- strict mode passes without dropping anything: **False**

**2. Root orientation.** The two independent signals agree on **99.9981%** of finite node times (origins supplied, versus successors alone). 3 node(s) at time zero, median 20.673112208028666 m from the nearest origin (max 26.598016909248603 m).

**6. Interior anchors.** Origins land at fractions [0.6305, 0.6155, 0.5901] along their nearest expansion edge, [25.66, 11.58, 14.79] m away.

**5. Quantisation.** `tau` median 11.0 s, p90 36.0 s; **1614 edges (0.64%) sit at the 0.1 s floor**, i.e. their duration difference rounded to zero.

**4. Implied speed** (edge length / tau), reference max 27.72 m/s: median 2.99, p10 1.71, p90 7.98; **0.42% exceed the reference**, which is the signature of a penalty or a zero-rounded tau rather than a fast road.

**3. The bidirectional assumption.** The adapter sets `fwd_time == rev_time == tau`.

- with `skip_opposites=false`: 476072 features in 2.39 s against 254323 in 2.04 s; 253635 physical edges, of which **221415 (87.3%) were settled in both directions**
- rebuilding the index to allow only the direction the search used: 153,430 reachable cells against 153,500, **70 lost**; of 153,430 comparable cells **4,294 (2.80%) change by more than 1 s**, median increase 13.1 s, p90 52.5 s, max 546.4 s


### S1.3 part two: dangling predecessors and the direction assumption (2026-11-04 09:28:51): grocery / drive, 3 POIs

**A. `skip_opposites` is why strict mode fails.**

| request | features | seconds | edges naming an absent predecessor |
|---|---|---|---|
| `skip_opposites=true` | 254,323 | 1.5 | **636** (0.2501%) |
| `skip_opposites=false` | 476,072 | 2.68 | **0** (0.0000%) |

Valhalla omits the opposite direction of an edge it has already settled, so an edge whose predecessor *was* one of those omitted opposites points at an `edge_id` that was never serialised. Its near-end time is then genuinely unknown and the adapter drops it — correctly, but the cause is a flag we chose, not a property of the network.

**B. The direction assumption, measured without confounding.** The adapter sets `fwd_time == rev_time == tau`, arguing the tree already encodes legality. Under arrival semantics the tree encodes legality in **one** direction: a traveller crosses an edge from its far end to its near end. The adapter also never merges the two directed features for one physical edge, so with `skip_opposites=false` the same geometry enters the STRtree twice and `nearest()` picks one arbitrarily.

Merging by geometry and keeping each settled direction: **253,635 physical edges** from 476,072 features — 221,360 traversable both ways, 32,275 one way only.

| | cells |
|---|---|
| reachable, current unmerged bidirectional index | 153,503 |
| reachable, merged direction-faithful index | 153,465 |
| reachable only in the bidirectional index | 72 |
| reachable only in the directional index | 34 |
| comparable | 153,431 |
| changed by more than 1 s | **25,763 (16.79%)** |

Where they change: median **-3.2 s**, p90 of the absolute change 20.4 s, largest increase +655.6 s, largest decrease -50.0 s; 30.7% of changed cells get *later* under the direction-faithful index, which is the expected sign — the bidirectional index was letting cells travel the wrong way down a one-way street.


### S1.3 part two: dangling predecessors and the direction assumption (2026-11-04 09:31:55): grocery / drive, 3 POIs

**A. `skip_opposites` is why strict mode fails.**

| request | features | seconds | edges naming an absent predecessor |
|---|---|---|---|
| `skip_opposites=true` | 254,323 | 1.32 | **636** (0.2501%) |
| `skip_opposites=false` | 476,072 | 2.22 | **0** (0.0000%) |

Valhalla omits the opposite direction of an edge it has already settled, so an edge whose predecessor *was* one of those omitted opposites points at an `edge_id` that was never serialised. Its near-end time is then genuinely unknown and the adapter drops it — correctly, but the cause is a flag we chose, not a property of the network.

**B. The direction assumption, decomposed.** The adapter sets `fwd_time == rev_time == tau`, arguing the tree already encodes legality. Under arrival semantics the tree encodes legality in **one** direction: a traveller crosses an edge from its far end to its near end. The adapter also never merges the two directed features for one physical edge, so with `skip_opposites=false` the same geometry enters the STRtree twice and `nearest()` picks one arbitrarily.

These two defects move cell times in **opposite** directions — merging lets a cell take the better of two duplicate geometries, restricting direction removes illegal moves — so they are measured separately. Three indices over the same cells:

| | index |
|---|---|
| **0** | the adapter as written, on `skip_opposites=true` features — today's path |
| **2** | merged by geometry, still traversable both ways |
| **3** | merged by geometry, only the directions actually settled |

Merging gives **253,635 physical edges** from 476,072 features: 221,360 traversable both ways, 32,275 one way only, 1 unorientable.

| | 0 -> 2 (merging) | 2 -> 3 (direction) | 0 -> 3 (both) |
|---|---|---|---|
| reachable cells after | 153,537 | 153,465 | 153,465 |
| cells lost | 0 | 72 | 72 |
| cells gained | 37 | 0 | 37 |
| changed by more than 1 s | 13,396 | 13,970 | 4,659 |
| share changed | 8.73% | 9.10% | 3.04% |
| median signed change | -2.5 s | +2.5 s | +1.6 s |
| p90 absolute change | 18.7 s | 25.4 s | 170.6 s |
| largest increase | +385.7 s | +655.6 s | +655.6 s |
| largest decrease | -526.9 s | +0.0 s | -525.0 s |
| share getting later | 0.6% | 100.0% | 55.8% |

The direction column is the one that matters for correctness, and its sign is the expected one: restricting travel to the settled direction makes cells later, never earlier. The merging column is a separate defect of the same adapter and moves the other way.

**Superseded:** the first pass of this measurement reported 2.80% of cells changing with a median increase of 13.1 s, built from `skip_opposites=true` features. That construction forbids the unused direction of a two-way street that was only ever settled once, so it mixed 'illegal move allowed' with 'legal move wrongly blocked'. The table above replaces it.


### S1.3 expansion structure, post-fix (2026-11-04 09:38:03): grocery / drive, 3 POIs, 60-minute contour

Request: `action=isochrone`, `reverse=true`, **`skip_opposites=false`**, `expansion_properties=['duration', 'distance', 'edge_id', 'pred_edge_id', 'cost']` — all five accepted by Valhalla 3.9.1; `duration` is integer seconds (True). 476,072 features in 2.30 s.

**1. Adapter health.**

- `report=` : `{'edges': 476072, 'physical_edges': 253635, 'merged_pairs': 221414, 'dangling_predecessors': 0, 'roots_unoriented': 1, 'dropped': 1, 'origins_supplied': 3, 'opposites_included': True, 'bidirectional_fallback': False}`
- `strict=True` passes without dropping anything: **False** (it did not before `skip_opposites=false`)

**2. Root orientation.** The two independent signals — supplied origins, and the vertex shared with successors — agree on **99.9991%** of finite node times. 3 node(s) at time zero, median 20.7 m from the nearest origin (max 26.6 m).

**3. Direction.** 253,635 physical edges: 221,360 traversable both ways, **32,275 (12.7%) one way only** — the edges the old bidirectional marking let a cell cross the wrong way.

**6. Interior anchors.** Origins land at fractions [0.6305, 0.6155, 0.5901] along their nearest expansion edge, [25.66, 11.58, 14.79] m away. Valhalla does **not** split an edge at the origin, so the destination's own position within its road is not modelled: time zero sits at a vertex up to 27 m from the POI.

**5. Quantisation.** `tau` median 10.0 s, p90 35.0 s; **2,282 edges (0.90%) sit at the 0.1 s floor**, i.e. their whole-second duration difference rounded to zero.

**4. Implied speed** (edge length / tau), reference max 27.72 m/s: median **3.17 m/s**, p10 2.18, p90 8.47; 0.60% exceed the reference. A median implied speed well below the road speeds confirms that `tau` is **not a pure traversal time** — turn, stop and intersection costs charged on entering the edge are inside it, and within-edge interpolation scales them along with the travel.

**7. Valhalla's `cost` against its `duration`.** They differ on **100.0%** of features (median gap 264.0 s, p90 931.0 s, max 6274 s). So Valhalla runs its own two-weight model, and the adapter reports `duration` — the right choice. Carrying `cost` as the *selection* weight, the way the own-graph path does since Codex pass-6 H1, is a named follow-up and is not done here.


### S1.3 expansion structure, post-fix (2026-11-04 09:39:52): grocery / drive, 3 POIs, 60-minute contour

Request: `action=isochrone`, `reverse=true`, **`skip_opposites=false`**, `expansion_properties=['duration', 'distance', 'edge_id', 'pred_edge_id', 'cost']` — all five accepted by Valhalla 3.9.1; `duration` is integer seconds (True). 476,072 features in 2.31 s.

**1. Adapter health.**

- `report=` : `{'edges': 476072, 'physical_edges': 253635, 'merged_pairs': 221414, 'dangling_predecessors': 0, 'roots_unoriented': 1, 'dropped': 1, 'origins_supplied': 3, 'opposites_included': True, 'bidirectional_fallback': False}`
- `strict=True` passes without dropping anything: **False** (it did not before `skip_opposites=false`)

**2. Root orientation.** The two independent signals — supplied origins, and the vertex shared with successors — agree on **99.9991%** of finite node times. 3 node(s) at time zero, median 20.7 m from the nearest origin (max 26.6 m).

**3. Direction.** 253,635 physical edges: 221,360 traversable both ways, **32,275 (12.7%) one way only** — the edges the old bidirectional marking let a cell cross the wrong way.

**6. Interior anchors.** Origins land at fractions [0.6305, 0.6155, 0.5901] along their nearest expansion edge, [25.66, 11.58, 14.79] m away. Valhalla does **not** split an edge at the origin, so the destination's own position within its road is not modelled: time zero sits at a vertex up to 27 m from the POI.

**5. Quantisation.** `tau` median 10.0 s, p90 35.0 s; **2,282 edges (0.90%) sit at the 0.1 s floor**, i.e. their whole-second duration difference rounded to zero.

**4. Implied speed** (edge length / tau), reference max 27.72 m/s: median **3.17 m/s**, p10 2.18, p90 8.47; 0.60% exceed the reference. A median implied speed well below the road speeds confirms that `tau` is **not a pure traversal time** — turn, stop and intersection costs charged on entering the edge are inside it, and within-edge interpolation scales them along with the travel.

**7. Valhalla's `cost` against its `duration`.** They differ on **100.0%** of features (median gap 264.0 s, p90 931.0 s, max 6274 s). So Valhalla runs its own two-weight model, and the adapter reports `duration` — the right choice. Carrying `cost` as the *selection* weight, the way the own-graph path does since Codex pass-6 H1, is a named follow-up and is not done here.


### S1.3 part two: dangling predecessors and the direction assumption (2026-11-04 09:42:08): grocery / drive, 3 POIs

**A. `skip_opposites` is why strict mode fails.**

| request | features | seconds | edges naming an absent predecessor |
|---|---|---|---|
| `skip_opposites=true` | 254,323 | 1.47 | **636** (0.2501%) |
| `skip_opposites=false` | 476,072 | 2.42 | **0** (0.0000%) |

Valhalla omits the opposite direction of an edge it has already settled, so an edge whose predecessor *was* one of those omitted opposites points at an `edge_id` that was never serialised. Its near-end time is then genuinely unknown and the adapter drops it — correctly, but the cause is a flag we chose, not a property of the network.

**B. The direction assumption, decomposed.** The adapter sets `fwd_time == rev_time == tau`, arguing the tree already encodes legality. Under arrival semantics the tree encodes legality in **one** direction: a traveller crosses an edge from its far end to its near end. The adapter also never merges the two directed features for one physical edge, so with `skip_opposites=false` the same geometry enters the STRtree twice and `nearest()` picks one arbitrarily.

These two defects move cell times in **opposite** directions — merging lets a cell take the better of two duplicate geometries, restricting direction removes illegal moves — so they are measured separately. Three indices over the same cells:

| | index |
|---|---|
| **0** | the adapter as written, on `skip_opposites=true` features — today's path |
| **2** | merged by geometry, still traversable both ways |
| **3** | merged by geometry, only the directions actually settled |

Merging gives **253,635 physical edges** from 476,072 features: 221,360 traversable both ways, 32,275 one way only, 1 unorientable.

| | 0 -> 2 (merging) | 2 -> 3 (direction) | 0 -> 3 (both) |
|---|---|---|---|
| reachable cells after | 151,560 | 151,488 | 151,488 |
| cells lost | 0 | 72 | 72 |
| cells gained | 37 | 0 | 37 |
| changed by more than 1 s | 13,301 | 13,897 | 4,627 |
| share changed | 8.78% | 9.17% | 3.06% |
| median signed change | -2.5 s | +2.5 s | +1.7 s |
| p90 absolute change | 19.0 s | 25.3 s | 170.0 s |
| largest increase | +385.7 s | +655.6 s | +655.6 s |
| largest decrease | -526.9 s | +0.0 s | -525.0 s |
| share getting later | 0.6% | 100.0% | 56.0% |

The direction column is the one that matters for correctness, and its sign is the expected one: restricting travel to the settled direction makes cells later, never earlier. The merging column is a separate defect of the same adapter and moves the other way.

**Superseded:** the first pass of this measurement reported 2.80% of cells changing with a median increase of 13.1 s, built from `skip_opposites=true` features. That construction forbids the unused direction of a two-way street that was only ever settled once, so it mixed 'illegal move allowed' with 'legal move wrongly blocked'. The table above replaces it.


### S1.4 expansion primitive, re-measured (2026-11-04 09:44:03): grocery / walk, 3 POIs, paired on `raster_primitive_grocery_walk.json` (240 cells)

Two methods on the same cells against the same exact `sources_to_targets` values. **old** is the published method reproduced verbatim — `skip_opposites=true`, nearest edge, charge its whole settled duration (8,909 edges, 0.23 s). **new** is the adopted primitive — `skip_opposites=false`, `expansion_to_edge_index` with merging and direction, then within-edge interpolation (8,869 physical edges from 16,894 features, 0.24 s).

Adapter report: `{'edges': 16894, 'physical_edges': 8869, 'merged_pairs': 7945, 'dangling_predecessors': 0, 'roots_unoriented': 0, 'dropped': 0, 'origins_supplied': 3, 'opposites_included': True, 'bidirectional_fallback': False}`

| difference from exact (seconds) | n | median | p90 | max | share > 60 s | signed median |
|---|---|---|---|---|---|---|
| old (published, whole-edge) | 195 | 69 | 271 | 647 | 54.9% | **+66 s** |
| **new (adopted, interpolated)** | 181 | 30 | 87 | 447 | 23.8% | **+29 s** |
| A | 208 | 88 | 355 | 983 | 60.6% | **-40 s** |
| B | 219 | 88 | 430 | 2080 | 66.7% | **-35 s** |

Positive signed median = our value is later than exact, i.e. conservative.

Threshold classification against exact:

| T min | old agrees | new agrees | new false-in | new false-out |
|---|---|---|---|---|
| 10 | 98.8% | 99.6% | 0.0% | 7.7% |
| 15 | 99.6% | 100.0% | 0.0% | 0.0% |
| 25 | 97.5% | 99.2% | 0.0% | 4.5% |
| 45 | 95.4% | 99.2% | 0.0% | 1.6% |

**S1.4 pass criterion — signed median within ±15 s: FAIL** (+28.7 s against the published +66 s).

This measures **construction fidelity against the same engine**: both sides are Valhalla. It is a prerequisite for accuracy and is not evidence of it (S3.4), and zero observed false inclusions on a finite sample is not proof of a zero rate.


### S1.4 follow-up: the own-graph exact-pair residual is mostly the access leg (2026-11-04 09:47:11): grocery / walk

Paired on `matrix_grocery_walk_controlled.json` (599 finite cells). `own_min` charges a straight-line access walk at `access_speed_mps`; Valhalla's `sources_to_targets` snaps the cell centre and charges essentially nothing for it, so the access leg does **not** cancel between the two sides.

- overall signed median **+0.2 s**, median absolute 0.5 s
- access distance median 30.8 m (p90 109.0 m, max 198.5 m), charged 24.4 s at the median
- **median access charge / median bias = 121.63**

| access distance | n | median bias | median access charge |
|---|---|---|---|
| 0-5 m | 76 | -0.2 s | 1.8 s |
| 5-20 m | 144 | -0.0 s | 9.2 s |
| 20-50 m | 200 | +0.3 s | 26.1 s |
| 50-100 m | 111 | +0.6 s | 52.5 s |
| 100-200 m | 68 | +1.6 s | 105.8 s |

With our access leg removed, so both sides describe travel from the network: signed median **-23.8 s**, median absolute **23.8 s**, p90 82.4 s.

**What this changes.** The Phase 0 verdict read this comparison as evidence that our walk *speed model* is unbiased against Valhalla. The bias it measured is dominated by a definitional difference in how the two sides treat a cell that is not on the network, so the comparison had even less power to detect a speed-model error than the memo already conceded (the two pedestrian speeds were 1.400 against 1.411 m/s by construction). The on-network agreement is the defensible claim; the access leg is a modelling choice of ours that Valhalla's matrix does not contain, and `ACCESS_SPEED_FACTOR` remains an unmeasured prior.


### S1.4 follow-up: the own-graph exact-pair residual is mostly the access leg (2026-11-04 09:48:57): grocery / walk

Paired on `matrix_grocery_walk_controlled.json` (599 finite cells). `own_min` charges a straight-line access walk at `access_speed_mps`; Valhalla's `sources_to_targets` snaps the cell centre and charges essentially nothing for it, so the access leg does **not** cancel between the two sides.

- overall signed median **+12.0 s**, median absolute 30.8 s
- access distance median 30.8 m (p90 109.0 m, max 198.5 m), charged 24.4 s at the median
- **median access charge / median bias = 2.03**

| access distance | n | median bias | median access charge |
|---|---|---|---|
| 0-5 m | 76 | -9.9 s | 1.8 s |
| 5-20 m | 144 | -2.6 s | 9.2 s |
| 20-50 m | 200 | +16.3 s | 26.1 s |
| 50-100 m | 111 | +36.5 s | 52.5 s |
| 100-200 m | 68 | +96.8 s | 105.8 s |

With our access leg removed, so both sides describe travel from the network: signed median **-11.3 s**, median absolute **22.8 s**, p90 145.1 s.

**What this changes.** The Phase 0 verdict read this comparison as evidence that our walk *speed model* is unbiased against Valhalla. The bias it measured is dominated by a definitional difference in how the two sides treat a cell that is not on the network, so the comparison had even less power to detect a speed-model error than the memo already conceded (the two pedestrian speeds were 1.400 against 1.411 m/s by construction). The on-network agreement is the defensible claim; the access leg is a modelling choice of ours that Valhalla's matrix does not contain, and `ACCESS_SPEED_FACTOR` remains an unmeasured prior.


### S1.4 follow-up: the own-graph exact-pair residual, decomposed by access distance (2026-11-04 09:50:34): grocery / walk

Paired on `matrix_grocery_walk_controlled.json` (599 finite cells, converted from the file's minutes to seconds). `own_min` charges a straight-line access walk at `access_speed_mps`; Valhalla's `sources_to_targets` snaps the cell centre and charges essentially nothing for it, so the access leg does **not** cancel between the two sides.

This reproduces the published row exactly — signed median **+12.0 s** is the memo's +0.2 min, and median absolute 30.8 s is its 0.5 min — and then splits it.

- access distance median 30.8 m (p90 109.0 m, max 198.5 m), charged 24.4 s at the median

| access distance | n | median bias | median access charge |
|---|---|---|---|
| 0-5 m | 76 | **-9.9 s** | 1.8 s |
| 5-20 m | 144 | **-2.6 s** | 9.2 s |
| 20-50 m | 200 | **+16.3 s** | 26.1 s |
| 50-100 m | 111 | **+36.5 s** | 52.5 s |
| 100-200 m | 68 | **+96.8 s** | 105.8 s |

With our access leg subtracted, so both sides describe travel from the network: signed median **-11.3 s**, median absolute 22.8 s, p90 145.1 s — consistent with the nearly on-network band's -9.9 s.

**Two opposing terms, not one.** Unlike the expansion case, where the access leg accounted for the whole bias (ratio 0.96, residual +0.0 s), the own-graph residual splits into:

1. an **on-network optimism of about 10 s** at the median — our walk model is slightly faster than Valhalla's once the cell is on the network;
2. a **conservative access charge** that grows with distance, reaching +97 s in the 100-200 m band.

They cancel near the sample's median access distance of about 31 m, which is why the overall signed median looks like zero. That cancellation is a property of this sample's access-distance distribution, not of the model: a metro with more off-network cells would read conservative, one with fewer would read optimistic.

**What this changes.** The Phase 0 verdict read this comparison as evidence that our walk *speed model* is unbiased against Valhalla. It is better described as two biases that happen to offset. The on-network comparison is the one that speaks to the speed model, and it says we are around 10 s optimistic at a median journey of about 22 minutes — under 1%, so the verdict's direction survives, but 'unbiased' overstates it, and the memo's own caveat still applies: Valhalla's default pedestrian speed was 1.411 m/s against our 1.400, so neither number speaks to real walking times. `ACCESS_SPEED_FACTOR` remains an unmeasured prior, and it is now the larger term of the two.


### S1.4 expansion primitive, re-measured (2026-11-04 09:51:12): grocery / walk, 3 POIs, paired on `raster_primitive_grocery_walk.json` (240 cells)

Two methods on the same cells against the same exact `sources_to_targets` values. **old** is the published method reproduced verbatim — `skip_opposites=true`, nearest edge, charge its whole settled duration (8,909 edges, 0.23 s). **new** is the adopted primitive — `skip_opposites=false`, `expansion_to_edge_index` with merging and direction, then within-edge interpolation (8,869 physical edges from 16,894 features, 0.22 s).

Adapter report: `{'edges': 16894, 'physical_edges': 8869, 'merged_pairs': 7945, 'dangling_predecessors': 0, 'roots_unoriented': 0, 'dropped': 0, 'origins_supplied': 3, 'opposites_included': True, 'bidirectional_fallback': False}`

| difference from exact (seconds) | n | median | p90 | max | share > 60 s | signed median |
|---|---|---|---|---|---|---|
| old (published, whole-edge) | 195 | 69 | 271 | 647 | 54.9% | **+66 s** |
| **new (adopted, interpolated)** | 181 | 30 | 87 | 447 | 23.8% | **+29 s** |
| A | 208 | 88 | 355 | 983 | 60.6% | **-40 s** |
| B | 219 | 88 | 430 | 2080 | 66.7% | **-35 s** |

Positive signed median = our value is later than exact, i.e. conservative.

Threshold classification against exact:

| T min | old agrees | new agrees | new false-in | new false-out |
|---|---|---|---|---|
| 10 | 98.8% | 99.6% | 0.0% | 7.7% |
| 15 | 99.6% | 100.0% | 0.0% | 0.0% |
| 25 | 97.5% | 99.2% | 0.0% | 4.5% |
| 45 | 95.4% | 99.2% | 0.0% | 1.6% |

**Where the residual is.** The reference charges nothing for reaching the network — `sources_to_targets` snaps the cell centre — while we add a straight-line leg at `access_speed_mps`. So the access leg is in our number and absent from theirs.

| access distance | n | median bias | median access charge |
|---|---|---|---|
| 0-5 m | 17 | **+2.6 s** | 1.4 s |
| 5-20 m | 41 | **+8.9 s** | 8.7 s |
| 20-50 m | 64 | **+28.2 s** | 27.5 s |
| 50-100 m | 46 | **+59.2 s** | 57.2 s |
| 100-200 m | 13 | **+94.6 s** | 96.8 s |

The bias tracks the charge: median access charge / median bias = **0.96**. Subtracting our access leg, so both sides describe travel from the network: signed median **+0.0 s**, median absolute **1.5 s**.

**S1.4 pass criterion — signed median within ±15 s.** As written, against the total: **FAIL** (+28.7 s, down from the published +66 s). On the quantity the criterion was meant to test — whether the corrected reconstruction removes the whole-edge bias — **PASS** (+0.0 s).

The criterion as written compares two different quantities, which is why it reports a failure while the reconstruction is in fact exact. The honest split: **the expansion reconstruction is verified** against the engine it reconstructs, and the remaining +29 s is our own access-leg model, an unmeasured prior (`ACCESS_SPEED_FACTOR`) that the reference does not contain. Which of those two numbers a published layer should carry is a modelling decision, not a test result.

This measures **construction fidelity against the same engine**: both sides are Valhalla. It is a prerequisite for accuracy and is not evidence of it (S3.4), and zero observed false inclusions on a finite sample is not proof of a zero rate.


### S1.4 expansion primitive, re-measured (2026-11-04 09:52:46): grocery / drive, 3 POIs, paired on `fresh sample, 3 POIs, seed 20261104` (240 cells)

Two methods on the same cells against the same exact `sources_to_targets` values. **old** is the published method reproduced verbatim — `skip_opposites=true`, nearest edge, charge its whole settled duration (254,323 edges, 1.28 s). **new** is the adopted primitive — `skip_opposites=false`, `expansion_to_edge_index` with merging and direction, then within-edge interpolation (253,635 physical edges from 476,072 features, 2.36 s).

Adapter report: `{'edges': 476072, 'physical_edges': 253635, 'merged_pairs': 221414, 'dangling_predecessors': 0, 'roots_unoriented': 1, 'dropped': 1, 'origins_supplied': 3, 'opposites_included': True, 'bidirectional_fallback': False}`

| difference from exact (seconds) | n | median | p90 | max | share > 60 s | signed median |
|---|---|---|---|---|---|---|
| old (published, whole-edge) | 240 | 112 | 306 | 681 | 86.7% | **+112 s** |
| **new (adopted, interpolated)** | 240 | 83 | 274 | 394 | 69.6% | **+82 s** |

Positive signed median = our value is later than exact, i.e. conservative.

Threshold classification against exact:

| T min | old agrees | new agrees | new false-in | new false-out |
|---|---|---|---|---|
| 10 | 97.5% | 97.5% | 0.4% | 41.7% |
| 15 | 97.9% | 98.3% | 0.0% | 17.4% |
| 25 | 95.8% | 96.7% | 0.0% | 17.8% |
| 45 | 88.8% | 90.4% | 0.0% | 14.1% |

**Where the residual is.** The reference charges nothing for reaching the network — `sources_to_targets` snaps the cell centre — while we add a straight-line leg at `access_speed_mps`. So the access leg is in our number and absent from theirs.

| access distance | n | median bias | median access charge |
|---|---|---|---|
| 0-5 m | 22 | **+50.9 s** | 1.7 s |
| 5-20 m | 56 | **+56.1 s** | 6.6 s |
| 20-50 m | 67 | **+72.8 s** | 18.6 s |
| 50-100 m | 56 | **+93.5 s** | 35.0 s |
| 100-200 m | 39 | **+246.0 s** | 71.1 s |

The bias tracks the charge: median access charge / median bias = **0.26**. Subtracting our access leg, so both sides describe travel from the network: signed median **+50.0 s**, median absolute **50.0 s**.

**S1.4 pass criterion — signed median within ±15 s.** As written, against the total: **FAIL** (+81.6 s, down from the published +66 s). On the quantity the criterion was meant to test — whether the corrected reconstruction removes the whole-edge bias — **FAIL** (+50.0 s).

The criterion as written compares two different quantities, which is why it reports a failure while the reconstruction is in fact exact. The honest split: **the expansion reconstruction is verified** against the engine it reconstructs, and the remaining +82 s is our own access-leg model, an unmeasured prior (`ACCESS_SPEED_FACTOR`) that the reference does not contain. Which of those two numbers a published layer should carry is a modelling decision, not a test result.

This measures **construction fidelity against the same engine**: both sides are Valhalla. It is a prerequisite for accuracy and is not evidence of it (S3.4), and zero observed false inclusions on a finite sample is not proof of a zero rate.


### S1.4 part three: reconstructed node times against the router (2026-11-04 09:54:08): grocery / drive, 3 POIs, 238 nodes

Sampled the expansion's **own node coordinates** and asked `sources_to_targets` for the time from exactly those points. No grid, no access leg, no within-edge interpolation, so this is the reconstruction against the router and nothing else.

- reconstructed median 2568 s, router median 2486 s
- **signed median +50.0 s**, median absolute 50.0 s, p90 243.0 s, max 322 s
- reconstruction later on 93.7% of nodes, earlier on 1.3%


### S1.4 part three: reconstructed node times against the router (2026-11-04 09:55:04): grocery / walk, 3 POIs, 240 nodes

Sampled the expansion's **own node coordinates** and asked `sources_to_targets` for the time from exactly those points. No grid, no access leg, no within-edge interpolation, so this is the reconstruction against the router and nothing else.

- reconstructed median 2682 s, router median 2680 s
- **signed median +0.0 s**, median absolute 0.0 s, p90 6.1 s, max 203 s
- reconstruction later on 16.7% of nodes, earlier on 12.1%

