
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

**Our walk model is not merely acceptable, it is unbiased.** A signed median of +0.2 minutes and
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
