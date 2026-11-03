
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
