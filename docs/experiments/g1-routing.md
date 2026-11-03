
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
