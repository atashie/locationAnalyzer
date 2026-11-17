# Pass 57 review - Antigravity / Gemini (gemini-4-hydrogen-xhigh)

Run 2026-11-16 against the prompt in `docs/research/58-review-pass57-prompt.md`, independently of
the Codex pass beside it and without sight of it. Captured from stdout; write access was denied
via `--settings '{"permissions":{"deny":["Write","Edit","NotebookEdit"]}}'`, which still allows
shell reads and execution.

Its tally: **19 CONFIRMED, 9 OVERSTATED, 2 WRONG** of the 30 numbered claims. It matched park
polygons against `osm_pois.parquet` rather than the accepted point input, which is how it produced
the large-park figures; Codex matched a deliberately stricter subset and warns against reading a
geometric gap as time saved. That disagreement is live and is recorded in
[[project-phase1-s3-destination-identity]].

---

root agent idle; waiting for 2 background task(s) to finish
I have completed the fast non-graph checks (published-grid building counts for W13, Overture vs. OSM park polygon geometry checks, zoom resampling simulations for W10, `explain_journey.py` on `band15min_pass-03`, and the JS/pytest suites) and launched the two full-graph empirical measurement runs covering Decisions 1–3 (`W1`, `W4`, `W5`, `W7`, `W8`, `W9`, and Claim 4 hole identity tracking). Waiting for those two background runs to finish before compiling the full review.
The first full-graph audit (`task-121`) has completed with exact results for Decision 1 (W1 desk test across all 125 holes and Claim 4 original-vs-created hole tracking) and Decision 2 (W4 restricted-edge/run distributions across all three walk layers and W5 exact sparse 2-state vs. full 2N benchmarks). Waiting for the remaining multi-mode Decision 3 run (`task-143`) to finish before checking any final follow-up items and compiling the full review.
Waiting for `measure_hole_edge_classes.py` (`task-156`) and `explain_donut_hole.py` (`task-157`) to finish; once they complete, I will synthesize all findings into the final review document.
Waiting for `explain_donut_hole.py` (`task-157`) to finish before assembling the complete review.
Running `v2/scripts/measure_access_candidates.py --target park --mode walk` and `v2/scripts/measure_restricted_walk_policy.py` in the background now; waiting for their completion before compiling the complete review.
# Pass 57 Adversarial Review — Decisions 1–4, Weaknesses W1–W13, Claims 1–30, and Owner Leanings

> **Summary verdict:** Of the **30 numbered claims**, **19 are CONFIRMED**, **9 are OVERSTATED**, and **2 are WRONG** (Claims **7** and **21**). Of the **owner's four positions**, Decision 1's **"Measure first (via Option 4)"** is **UNSUPPORTED**, Decision 2's **"Per stretch"** is **PREMATURE**, Decision 3's **"Never use a centroid"** is **SUPPORTED in principle / PREMATURE against the shipped layer** (because the shipped Overture park layer has **0 polygons and 746 Points**), and on Decision 4 the owner's visual complaint is **backed by the canvas code** against desktop load behaviour while Option **(vi)** (*clip out UNKNOWN*) and standalone Option **(i)** (*flat grey wash over 17% of the map*) have concrete defects. Under [`docs/plans/2026-11-04-s3-execution-plan.md`](file:///C:/Users/arikt/documents/github/distanceFinder/docs/plans/2026-11-04-s3-execution-plan.md#L86-L97) §0 (**product risk retired**), the author's ordering (**1, 2, 3**, with **4** tacked on last) is inverted: the risk-retired order is **4 → 3 → 2 → 1**.
>
> **Workspace integrity:** Zero files were added or edited, no option was taken, `git status -s` returned empty, and the baseline suites verified cleanly (`pytest -o addopts="" -q`: `1553 passed, 24 skipped`; `node card_selftest.mjs; node worker_conformance.mjs`: `all card checks passed, all browser conformance checks passed`).

| Summary Ledger | Breakdown |
|---|---|
| **30 Claims** | **19 CONFIRMED** (`1, 2, 4, 9, 10, 13, 14, 15, 16, 17, 18, 20, 22, 23, 24, 25, 27, 28, 29`) · **9 OVERSTATED** (`3, 5, 6, 8, 11, 12, 19, 26, 30`) · **2 WRONG** (`7, 21`) |
| **Owner Leanings** | **D1 ("Measure first" via Opt. 4):** UNSUPPORTED · **D2 ("Per stretch"):** PREMATURE · **D3 ("Never use centroid"):** SUPPORTED in principle / PREMATURE on shipped layer · **D4 (Striping):** Screen-space hatch + tint + legend fix supported; `(vi)` clip unsupported |
| **§0 Risk Order** | **1st: Decision 4** → **2nd: Decision 3** → **3rd: Decision 2** → **4th: Decision 1** |

---

## 1. Declared Weaknesses (W1–W13)

Starting here as requested: running the scripts and spatial joins against the shipped rasters, Overture/OSM parquet tables, and raw XML (`v2/.venv/Scripts/python.exe`) reverses several of the note's central premises.

### Decision 1 — Donut Holes (`W1–W3`)

#### W1 — Can Claim 8's desk test settle Claim 3, and what test actually exists?
Running an automated topological + geometric + building/barrier test across all **125** UTM `own_triangle_park_walk` `@20 min` holes against the walkable graph (`G_walk`), raw `triangle-roads.osm` (`2,660 / 2,660` ways inspected), `overture_buildings_accepted.parquet`, and `osm_barriers.parquet` shows **W1's fear is right and worse than stated**:

* **Pure OSM noding topology (`triangle-roads.osm`):** `0` holes involve ways crossing at the same level or grade-separated without a node, and only **`4 / 125` (`3.2%`)** are near-touches (`<= 5 m` without a shared node).
* **Physical separation:** **`121 / 125` (`96.8%`)** do not touch at all — edge-to-nearest-PASS-edge gap across all `125` holes is `[min 0.0, p25 31.2, p50 67.7, p75 108.3, p90 177.9, max 326.5] m`, and access distance to the nearest PASS candidate edge is `[min 6.2, p25 54.5, p50 73.7, p75 102.0, p90 140.4, max 190.4] m`.
* **Desk blockage split:** Of those `125` UTM holes, **`49` (`39.2%`)** have a mapped Overture building footprint directly blocking the straight line to the nearest PASS edge (`separated_no_touch_blocked_by_building`), **`72` (`57.6%`)** cross unbuilt open ground/parcels in the data (`separated_no_touch_open_ground_in_data`), and **`4` (`3.2%`)** are `near_touch <= 5 m without node`.
* **Exact sharper desk test:** A meaningful desk triage cannot be pure topology. It must run a 3-stage pipeline per hole:
  1. `near_touch <= 5 m` / crossing check (`4` likely router noding bugs);
  2. straight-line intersection against buildings + [`SEPARATING_BARRIERS`](file:///C:/Users/arikt/documents/github/distanceFinder/v2/locfinder/places/anchor.py#L63) (`49` already ruled out as *not* open cut-throughs without opening imagery);
  3. aerial/street-view check (or routed street-walk delta) on the remaining `72` open-ground holes.

#### W2 — Is Option 4 a stall compared to Option 1 or Option 3?
Yes — under [`docs/experiments/phase0-decisions.md`](file:///C:/Users/arikt/documents/github/distanceFinder/docs/experiments/phase0-decisions.md#L189-L196) (**Decision 17**), OSM-derived output is ODbL and explicitly states: *"Contributions back to OSM may not be sourced from Overture or Google."* Even ignoring upstream lag (months for OSM review + extract refresh), **96.8% of the `125` UTM holes are not OSM noding bugs**, so fixing OSM nodes leaves nearly every hole untouched.

Running hole-identity tracking on `own_triangle_park_walk @20 min` across snapping deltas (`measure_access_candidates.py` rules with `7200 s` horizon cap enforced) clarifies the concrete engineering trade-off:
* **`+25 m` multi-candidate:** UTM `125 -> 115` (repairs **`65` [`52.0%`]** original holes, creates **`55`** new ones); published grid `121 -> 109` (repairs **`64` [`52.9%`]**, creates **`52`**).
* **`+50 m` multi-candidate:** UTM `125 -> 96` (repairs **`100` [`80.0%`]** original holes, creates **`71`**); published grid `121 -> 94` (repairs **`96` [`79.3%`]**, creates **`69`**).
* **`200 m` full cap:** UTM `125 -> 30` (repairs **`125` [`100.0%`]**, creates **`30`**); published grid `121 -> 29` (repairs **`121` [`100.0%`]**, creates **`29`**).

Either pick **Option 1** (defer cleanly under §0 because harm is tiny) or test a **building- and barrier-screened `+25 m / +50 m` / routed Option 3 fallback**. Running Option 4's pure topology test first is a stall.

#### W3 — Is `0.07% of buildings` the wrong risk statement?
Check runs (`measure_donut_holes.py` + `overture_buildings_accepted.parquet` binned onto the published grid and `own_triangle_buildings_per_cell.npy` on UTM):
* `own_triangle_park_walk @20 min` **published grid**: `121` holes (`76` occupied, `45` empty), **`356` buildings** (`0.0711%` of `500,451` published buildings, **`0.1319%` of 20-minute in-region buildings**, `0.0718%` of OK buildings); per occupied hole `[p50=3.5, p90=10.0, max=27]`, with `121 / 356` in the top 10 holes.
* **Wrong threshold note:** `park/walk` opens at **`15 min`**, not `20 min`. At `15 min` on the published grid: **`118` holes** (`84` occupied) holding **`388` buildings** (`0.0775%` of all, **`0.1959%` of 15-min in-region buildings**). (UTM `@15m`: `123` holes, `89` occupied, `466` buildings = `0.2311%` of 15-min in-region; UTM `@20m`: `125` holes, `75` occupied, `414` buildings = `0.1509%` of 20-min in-region.)
* **Missed multi-cell holes:** Restricting "hole" to `1×1` excludes **`146` enclosed 2–18 cell EXCLUDED islands** on published `park/walk @20 min` (`8-connected` sizes `2:54, 3:29, 4:13, ... 18:2`).
* **Better statement of risk:** *"On the shipped `15 min` `park/walk` map, `84` occupied `1×1` enclosed parcels (holding `388` buildings, max `29` UTM / `27` `@20m` pub in one cell — `0.20%` of in-region households) sit inside isolated exclusion rings where every neighbour passes."* Even on the right denominator (`0.13%–0.20%`), the footprint remains small.

---

### Decision 2 — Restricted-Way Penalty Unit (`W4–W6`)

#### W4 — Most likely overstatement check: restricted-edge and run distributions across published layers
Measured exactly across every cell (`330,502`) with `0` float32 discrepancies vs the stored `.npy` layers:

| Layer | UTM OK cells touched (% OK) | UTM OK bldgs touched (% OK bld) | PUB OK touched (% OK) | `> 1` restricted edge | `edges > runs` | `[p25, p50, p75, p95, max]` edges | `[p25, p50, p75, p95, max]` runs |
|---|---:|---:|---:|---:|---:|---|---|
| `own_triangle_grocery_walk` | `57,175 / 256,752` (**22.27%**) | `67,484 / 499,009` (`13.52%`) | `57,193 / 258,684` (`22.11%`) | **26.84%** | **23.03%** | `[1, 2, 3, 7, 25]` | `[1, 1, 1, 2, 7]` |
| `own_triangle_park_walk` | `67,730 / 268,061` (**25.27%**) | `76,422 / 507,231` (`15.07%`) | `67,676 / 270,308` (`25.04%`) | **30.88%** | **24.30%** | `[1, 2, 3, 8, 25]` | `[1, 1, 2, 2, 6]` |
| `own_triangle_school_walk` | `56,397 / 258,412` (**21.82%**) | `73,263 / 501,874` (`14.60%`) | `55,927 / 260,781` (`21.45%`) | **26.49%** | **23.11%** | `[1, 2, 2, 8, 25]` | `[1, 1, 1, 2, 7]` |
| `own_triangle_coffee_bike` | `61,219 / 274,805` (**22.28%**) | — | — | **23.9%** | — | `max 25` | `max 6` |
| `own_triangle_grocery_drive` | `53,769–53,774 / 266,278` (**20.19%**) | — | — | **24.1%** | — | `[1, 3, 25]` | `[1, 1, 4]` |

Also on `own_triangle_grocery_walk` UTM `PASS @ 15 min`: **`5,509 / 47,509` (`11.60%`)** cells holding **`15,294 / 163,875` (`9.33%`)** buildings cross a restricted edge.

**The decisive counterfactual (switching `(a) per-edge 120s` → exact `(b) per-stretch 120s`):**
* Even though `22%–25%` of OK cells touch restricted ways and the **median affected route crosses `2` restricted edges** (refuting W4's fear that median = 1 edge), **switching `(a) -> (b)` at `120 s` moves only `2.18%–3.74%` of UTM OK cells (`> 1 s`)**:
  * `grocery/walk`: `7,492` (`2.92%`, `4,548 > 60 s`, `9,886` bld); `PASS @15m` flips: `176` (`+170 / -6`), `@20m`: `198` (`+195 / -3`); **`walked(286, 129)` stays `810.8 s`**.
  * `park/walk`: `10,035` (`3.74%`, `5,858 > 60 s`); `PASS @15m` flips: `154` (`+153 / -1`), `@20m`: `220` (`+219 / -1`).
  * `school/walk`: `5,624` (`2.18%`, `1,999 > 60 s`); `PASS @15m` flips: `242` (`+241 / -1`).
* Notice **nearly every flip is one-directional (`+170 / -6`, `+153 / -1`, `+241 / -1`)**: at `120 s`, `(b)` purely *weakens* the penalty on multi-edge private roads, admitting slightly more households onto unverified tracks — and **raising `(b)` to `600 s` on `grocery/walk` STILL leaves `walked(286, 129) = 810.8 s` (UNFIXED!)**, only costing `339` lost `15m` PASS cells (`992` bld, `0.61%`) and gaining `84` (`147` bld). Meanwhile, **`per-metre 1.2 s/m` or `4.0 s/m`** shifts `walked(286, 129)` to `857.5 s` (`46` / `229` lost `15m` PASS buildings).
* **Bottom line for W4:** Exposure is large (**22%–25%**), Claim 13 is *not* noise (because `(b)` breaks `600 s` at the walked cell), yet **implementing `(b)` at `120 s` moves almost nobody (`2%–4%`) and in the permissive direction**. The live risk is calibration + disclosure, not `(a)` vs `(b)` at `120 s`.

#### W5 — Per-stretch state space, admissibility, and memory/runtime cost
1. **Can vertex-indexed Dijkstra avoid doubling state? No — verified.** Where a node touches both public (`r=0`) and restricted (`r=1`) edges, entering a restricted edge from public must charge the entry penalty once, while staying on restricted (`r=1 -> r=1`) must charge `0`. Plain edge costs `(u, v)` cannot carry the incoming `r` flag.
2. **Cheaper exact formulation exists and matches `2N` with 0 diffs:** Only nodes incident to *both* public and restricted edges (**`94,881` mixed-incidence nodes out of `N = 539,814`**, **+17.6%**, NOT `+100%` / `2N = 1,079,628`) need two states (`(u, 0)` and `(u, 1)`). We built and verified **0 differences** between sparse 2-state CSR and full `2N` CSR across all destinations:
   * Baseline 1-state SciPy Dijkstra: `nnz = 1,395,589`, Dijkstra `0.11 s`.
   * Sparse 2-state CSR: `M = 634,695`, `nnz = 1,611,240`, build `9.14 s`, peak memory `454.1 MB`, Python-level Dijkstra `9.59–9.72 s`.
   * Full `2N` CSR: `M = 1,079,628`, `nnz = 2,796,674`, build `15.14 s`, peak memory `835.8 MB`, Dijkstra `16.51 s`.
3. **Admissibility / `min_possible_s` / 30 admissibility tests:** Non-negative stretch penalties add `>= 0` to `cost` and `0` to `time`, so [`snap.py:442`](file:///C:/Users/arikt/documents/github/distanceFinder/v2/locfinder/traveltime/snap.py#L442) `min_possible = access_m / max_speed_mps(mode)` remains a valid lower bound on arrival time, preserving `BEYOND_HORIZON` admissibility. Separately, the "`30 of 30` admissibility tests" in [`v2/scripts/mutate_admissible.py`](file:///C:/Users/arikt/documents/github/distanceFinder/v2/scripts/mutate_admissible.py) verify walked-record E3 schema admissibility, not graph Dijkstra optimality — neither breaks under `(b)`.

#### W6 — Is the presentation order wrong under Plan §0?
**Yes — completely.** See [Section 5](#5-ranking-of-the-four-decisions-by-product-risk-retired-plan-0) below (`4 → 3 → 2 → 1`).

---

### Decision 3 — Parks & Destination Snapping (`W7–W9`)

#### W7 — What is the actual centroid-vs-boundary error on the published grid?
First, a structural discovery that **refutes Claim 21**: **`overture_places_accepted.parquet` contains `107,484` rows and EVERY single park (`746 / 746`) is a `Point`, with `0` polygons.** The shipped `own_triangle_park_walk` layer never used polygon centroids! (Notably, [`docs/experiments/s3-13-reading-test.md`](file:///C:/Users/arikt/documents/github/distanceFinder/docs/experiments/s3-13-reading-test.md#L170) also mistakenly stated *"Parks snap to the polygon centroid"*.)

Measuring the *real-world* park boundary error via `osm_pois.parquet` (`1,053` parks/reserves, **`1,002` Polygon/MultiPolygon**: `819` `leisure=park` + `183` `leisure=nature_reserve`; `845` intersect eval UTM grid):
* **Centroid-to-own-boundary distance:**
  * All `1,002` polygons: `[p10..max] = [6.9, 15.2, 32.2, 77.9, 159.3, 218.2, 409.9, 2393.5] m`; **`200 > 100 m`**, **`70 > 200 m`**, **`11 > 400 m`**.
  * Strict `819` `leisure=park`: area `p50=1.59 ha`, `p90=27.54 ha`, `max=1804.9 ha`; centroid-to-boundary `p50=30.6 m`, `p90=136.2 m`, `max=428.8 m` (`139 > 100 m`, `41 > 200 m`).
* **Overture coverage gaps:** Only `353 / 746` Overture parks lie inside an OSM park polygon (enclosing-boundary distance `p50=48.8 m, p90=199.5 m, max=1685.7 m`), while major parks like **Duke Forest Korstian** and **Duke Forest Blackwood** are absent from Overture entirely (`25–51 m` median abutting gap). Even with `8` Overture points inside **Umstead**, abutting cells suffer median `24 m` (`max 76 m`) error, and **Eno River** median `40 m` (`max 105 m`).
* **Published-grid impact across `11,427` published OK cells abutting large OSM parks (`cen->bnd > 100 m`):**

| Park destination model | Abutting median | Abutting `<= 15 min` | Abutting improvement vs published | Published Triangle `15m` in-region (`diff vs pub`) |
|---|---:|---:|---|---:|
| **Published (`Overture Points`, node-snap)** | **31 min** | **26.2%** | baseline | **60,824** (`0`) |
| `Overture Points (edge_snap)` | 31 min | 26.2% | ~0 | 60,329 |
| `OSM_centroid (edge_snap, drops 15 vs 37)` | 26 min | 31.8% | `p50=1m, p90=34m, max=103m` | 65,161 (`+23,855 / -19,518`) |
| **`OSM_road_entries (<=50m)` (`710` crossed, `988/1002` covered)** | **9 min** | **70.1%** | **`p50=17 min, p90=60 min, max=117 min`** | **106,108 (`+57,070 / -11,786`)** |
| `OSM_naive_boundary (<=200m)` (`999/1002` covered) | 5 min | 85.1% | `p50=23 min, p90=66 min, max=119 min` | 125,272 |

**Verdict on W7:** Nowhere near *"median 30 m low value"*: for households abutting large parks on the **published grid**, the error is **median `17 min`, p90 `60 min`, max `117 min`**, nearly **doubling** Triangle `15 min` park-walk coverage (`60,824 -> 106,108`).

#### W8 — Is nearest-boundary-point better, or does it create dangerous optimistic errors?
W8 is **spot on** — naive nearest-boundary creates two documented optimistic failures in this dataset:
1. **`Duke Energy: Harris Nuclear Plant` is a `9,627.8 ha` `leisure=nature_reserve` containing `9` Overture park points** — sampling its entire perimeter treats an industrial/nuclear exclusion fence line as public park access!
2. **Crossing barriers:** Out of `29,594` naive boundary samples compared against `osm_barriers.parquet` (`4,665` lines: `fence 3286, retaining_wall 685, hedge 347, wall 344, city_wall 3`), **`136 / 29,594` (`0.46%`)** snap directly across a separating wall/fence/hedge.
3. **Why mapped entrances alone cannot replace it:** In raw `triangle-roads.osm`, out of `1,002` OSM polygons, only **`26` (`2.6%`)** have `entrance=*` within `20 m` and **`78` (`7.8%`)** have `barrier=gate` within `20 m` (`5,645` gates and `2,221` entrances Triangle-wide).
* **Concrete policy:** Separate `leisure=park` from unscreened `leisure=nature_reserve`, take mapped `entrance=*` + non-private `barrier=gate`, and fill the rest with **`OSM_road_entries (<= 50 m)`** — boundary intersections with walkable network ways + boundary points within `50 m` of a walkable edge that do **not** cross [`SEPARATING_BARRIERS`](file:///C:/Users/arikt/documents/github/distanceFinder/v2/locfinder/places/anchor.py#L63) or restricted edges. That covers **`988 / 1,002` (`98.6%`)** polygons while avoiding fences, motorways, and industrial buffers.

#### W9 — Claim 22 rebuild scope across all 7 published layers
Full edge-snapping (`<= 300 m`) vs node-snapping (`<= 300 m`) re-computed across **all 7 shipped layers** (`0` stored `.npy` diffs on node-snap reproduction):

| Published Layer | Destinations kept (`node -> edge`) | Dest shifted `> 1 m` | UTM OK cells moved `> 1 s` (% OK) | UTM OK moved `> 60 s` | **Published bytes moved (`> 0 min`)** | Flips at shipped default limit |
|---|---:|---:|---:|---:|---:|---:|
| `own_triangle_grocery_walk` (`@20m`) | `549 -> 549` | `498` | `231,349 / 256,591` (**90.16%**) | `15,923` | **63,093 (`19.09%`)** | `1,299 (+423 / -876)` |
| `own_triangle_park_walk` (`@15m`) | **`739 -> 745`** | `657` | `232,291 / 268,020` (**86.67%**) | `32,624` | **94,629 (`28.63%`)** | `2,913 (+1,209 / -1,704)` |
| `own_triangle_school_walk` (`@20m`) | `559 -> 559` | `487` | `230,645 / 258,260` (**89.31%**) | `32,531` | **99,028 (`29.96%`)** | `2,974 (+1,108 / -1,866)` |
| `own_triangle_coffee_bike` (`@15m`) | `678 -> 678` | `622` | `209,896 / 274,805` (**76.38%**) | — | **21,890 (`6.62%`)** | `588 (+165 / -423)` |
| `own_triangle_grocery_drive` (`@10m`) | `550 -> 550` | `508` | `191,120 / 266,278` (**71.77%**) | — | **19,832 (`6.00%`)** | `709 (+167 / -542)` |
| `own_triangle_duke-hospital_drive` (`@30m`) | `1 -> 1` | `1 (>50m)` | `266,278 / 266,278` (**100.00%**) | — | **99,471 (`30.10%`)** | `3,333 (+0 / -3,333)` |
| `own_triangle_rdu-airport_drive` (`@40m`) | `2 -> 2` | `2` | `266,216 / 266,278` (**99.98%**) | — | **12,689 (`3.84%`)** | `247 (+44 / -203)` |

Claim 22 is **not** overstated if you change destination snapping globally (`71.8%–100.0%` of OK cells move across all 7 layers, `3.8%–30.1%` of published bytes change). *Crucial design note:* using edge-snap **only as a fallback** when `nearest_node > 300 m` recovers those `6` parks cleanly while moving **zero** existing destinations on the other `6` layers (`park/walk` moves only cells newly closest to those `6` parks).

---

### Decision 4 — Grey Diagonal Striping (`W10–W13`)

#### W10 — What do `worker.js` and `app.js` actually draw at each zoom level?
[`worker.js`](file:///C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/worker.js#L97-L101) sets `HATCH_PERIOD_MASK = 7`, `HATCH_WIDTH = 2` on the `643 × 514` published grid (`PX_NODATA = packRGBA(60, 60, 60, 130)` on 2 columns/rows out of 8, `PX_OUT = 0` on the other 6), and [`app.js`](file:///C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/app.js#L488-L537) mounts that `643 × 514` canvas via MapLibre `fitBounds` (`padding: 16`) with **`raster-resampling: 'nearest'`**. Exact canvas scaling simulation across viewports predicts:
* **Mobile (`375 × 400`, `z = 8.43`, `0.533 px/col`) & `< 1x` overview (`0.75x`):** `nearest` sampling drops diagonals cleanly (`0.75x` lowers painted UNKNOWN share `25.0% -> 22.3%`, producing beating `0-widths = [1, 4]` and moiré interference).
* **Default laptop / desktop load (`800 × 700` `z = 9.59` `1.194 px/col`; `1040 × 820` `z = 9.96` `1.544 px/col`):** **`nearest` maps the 2-cell band / 6-cell gap into periodic diagonal grey bars `~200 m` wide separated by `~600 m` clear gaps (`0-widths = [2, 7]` at `1.25x`)** — right across Jordan Lake, Falls Lake, Umstead, Duke Forest, and RDU.
* **Zoomed in (`1600 × 1200` `2.288 px/col`, `4.0x`):** thick diagonal Venetian-blind bands (`1-width = 8 px`, `0-widths = [8, 24] px`).
* **What the owner objected to:** Their exact words — *"grey diagonal lines of nodata ... those striping effects"* — directly describe the **coarse periodic diagonal zebra bars rendered on default laptop/desktop load and zoom**, NOT just tiny invisible regions or `< 1x` moiré.

#### W11 — Design judgement: why standalone solid fill `(i)` is weak, and what to ship instead
* **Option `(i)` (flat opaque/translucent grey wash across 17% of the map)** removes stripes and hidden regions, *but* coats ~560 km² (nearly a fifth of the canvas, including Jordan/Falls Lakes and Umstead) in flat grey that visually competes with blue `PX_IN`, washes out basemap features, and reads like an urban-landfill mask rather than missing network data.
* **Concrete fix combining UI clarity + visual legibility:**
  1. Switch to **Option `(iv)` computed in screen/tile space**: a subtle light tint (e.g., ~`6–8%` neutral wash so *every* UNKNOWN cell including all `369` small regions is faintly distinct from `EXCLUDED`, avoiding `(ii)`'s single-pixel hacks) paired with a crisp 1px screen-space 45° hairline hatch (or subtle stipple) at constant pixel pitch regardless of zoom;
  2. Immediately fix [`index.html:29`](file:///C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/index.html#L29), which still prints **`"nodata in an enabled layer"`** next to the hatch swatch — jargon copied straight from debug plumbing — to plain English (*"Outside mapped road network (> 200 m from roads)"*).

#### W12 — Challenge the premise: Option `(vi)` ("clip the published region") vs keeping `UNKNOWN`
Inspecting the exact `1,075` `OFF_NETWORK` components on the published grid exposes two fatal flaws with `(vi)`:
1. **`80.3%` (`44,995 / 56,036`) of `OFF_NETWORK` cells and `83.6%` (`2,811 / 3,364`) of `OFF_NETWORK` buildings are STRICTLY INTERIOR (`1,000` interior pockets)**, not outer-border margin (only `75` boundary-touching regions: `11,041` cells, `553` buildings). Clipping a bounding hull removes less than a fifth of the grey stripes and leaves Jordan Lake, Falls Lake, Umstead, Duke Forest, and interior rural pockets untouched.
2. **Code hazard in [`worker.js:533-536`](file:///C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/worker.js#L533-L536):** in `outcomeFor`, `S_OUTSIDE` (`5`) **falls directly into `return O_UNKNOWN;`**. Any naive raster crop that re-codes omitted cells as `S_OUTSIDE` without splitting renderer status semantics will still draw the exact same grey diagonal stripes!
3. Dropping inhabited interior cells (`2,811` buildings) from disclosure either hides real homes behind transparency (`EXCLUDED` = `"failed threshold"`) or pretends they aren't inside the map bounds. Keep `OFF_NETWORK` / `UNKNOWN` semantically and fix how it renders.

#### W13 — Published-grid building counts in `UNKNOWN` and the `369` wholly invisible regions
To avoid the exporter's nearest-neighbour grid distortion (reprojecting UTM `own_triangle_buildings_per_cell.npy` via NN produces `523,987` buildings — `+11,354` vs UTM's `512,633` and **`+23,536` vs published**!), we projected every building footprint centroid in `overture_buildings_accepted.parquet` (`522,160` rows) directly from UTM to `EPSG:4326` and binned on `card.js` WGS84 bounds:

* **Published grid total:** **`500,451` buildings** (`21,709` outside bounds).
* **`OFF_NETWORK` (`56,036` cells):** **`3,364` buildings (`0.6722%`)**.
* **`UNKNOWN` at `@15m` (`park/walk` default):** `55,752` cells → **`3,343` buildings** (`833` in hatched cells, `2,510` in transparent `PX_OUT` cells).
* **`UNKNOWN` at `@20m` (`park` / `grocery`):** `56,034` cells → **`3,364` buildings** (`838` painted, `2,526` transparent).
* **Inside all `369` wholly invisible regions (`975` cells):** **Identical at `15m` and `20m`: `55` buildings across `17` occupied regions (`352 / 369 = 95.4%` hold zero buildings; `max = 11` in one region; `55 / 500,451 = 0.0110%` of published buildings)** — broken down by region size: `1`: `4` bld; `2-3`: `24` bld; `4-8`: `13` bld; `9-16`: `14` bld; `17-64`: `0` bld.
* **Inside `166` large (`65+`) striped regions:** **`2,883` buildings (`@15m`) / `2,904` buildings (`@20m`, `86.3%` of all UNKNOWN buildings)**.

**Reframing result:** Claim 25's *"369 wholly invisible regions"* affects **55 buildings (`0.011%`)**, almost all in 17 rural pockets; **86% of UNKNOWN households (`2,904` buildings)** sit inside the `166` large striped zones. The owner was right about the visual striping, even though Claim 25's invisible-island count barely holds any buildings.

---

## 2. Claim-by-Claim Verdicts (Claims 1–30)

### Decision 1 — Donut Holes (`Claims 1–8`)

1. **CONFIRMED** — [`snap.py:162`](file:///C:/Users/arikt/documents/github/distanceFinder/v2/locfinder/traveltime/snap.py#L162) executes `nearest = idx.tree.nearest(pts)`, returning strictly `1` edge per origin cell; top holes in [`explain_donut_hole.py`](file:///C:/Users/arikt/documents/github/distanceFinder/v2/scripts/explain_donut_hole.py) (`(356,395)`, `(365,539)`, `(427,579)`) replicate this directly.
2. **CONFIRMED** — Published `own_triangle_park_walk` at `20 min`: `121` holes (`76` occupied, `45` empty), `356` buildings (`0.0711%` of `500,451`); UTM source grid: `125` holes (`75` occupied, `50` empty), `414` buildings (`0.0808%` of `512,633`). *(Clarification: shipped default threshold for `park/walk` is `15 min`, yielding `118` published holes / `388` buildings.)*
3. **OVERSTATED** — While ground-truth cul-de-sac vs defect isn't stored per parcel, **defects:** (a) omits **grid, layer, cap, and pipeline stage** for "`~90,000`": [`measure_access_candidates.py`](file:///C:/Users/arikt/documents/github/distanceFinder/v2/scripts/measure_access_candidates.py) produces `90,040` on the **UTM source grid**, **`own_triangle_park_walk`**, as an **uncapped** total-gain `> 60 s` over `272,961` comparable cells (`~88,978` OK cells with `7200 s` cap) right after Claim 2 cited `121` published cells; (b) `49 / 125` holes already fail a building-intersection screen at a desk (`W1`).
4. **CONFIRMED** — Identity-tracked `+50 m` snapping proves net count hides churn: UTM `@20 min` `125 -> 96` repairs `100` (`80.0%`) original holes and creates `71` new ones (published: `121 -> 94`, repairs `96` [`79.3%`], creates `69`).
5. **OVERSTATED** — Counts (`13 / 125 = 10.4%` `service=parking_aisle`, `44 / 125 = 35.2%` `residential`) come from [`measure_hole_edge_classes.py`](file:///C:/Users/arikt/documents/github/distanceFinder/v2/scripts/measure_hole_edge_classes.py), **defect:** omits **UTM grid, `own_triangle_park_walk`, and `20 min` threshold**, and computes `2.9x` enrichment against a full-grid baseline (`330,502` cells) diluted by `OFF_NETWORK` (`status == 1`) cells that have no snapped road class.
6. **OVERSTATED** — Raw metrics appear in `measure_access_candidates.py`, **defects:** (a) calls a **76% *net* reduction** (`UTM 125->30`, `PUB 121->29`) *"fixes 76%"*, when identity tracking shows `200 m` repairs **`100%` (`125 / 125` UTM, `121 / 121` PUB)** while manufacturing `30` / `29` new holes; (b) omits **UTM grid, `park/walk`, `@20m`**, and states `77%` without its **`272,961` comparable-cell denominator** (`210,533 / 330,502 = 63.7%` of full grid); (c) `"0 cells slower"` is tautological under `np.minimum`; (d) `"169 m"` is the median strictly over the **`90,040` cells gaining `> 60 s`**, not all `210,533` faster cells.
7. **WRONG** — Executed against `triangle-roads.osm` and `G_walk`: pure OSM noding gaps (`near_touch <= 5 m`) account for only **`4 / 125` (`3.2%`)** of UTM holes (`0` crossings without a node). **`96.8%` (`121 / 125`)** do not meet at all (median edge gap `67.7 m`, max `326.5 m`), so Option 4 does **not** measure Claim 3's unknown across the `121` / `125` holes.
8. **OVERSTATED** — Narrow binary junction checks run without altering shipped pipeline code, **but** they settle only `3.2%` (`4 / 125`), leave `96.8%` unsettled without building/barrier/imagery triage, and still required writing bespoke geometry/XML inspection code.

### Decision 2 — Restricted-Road Penalty Unit (`Claims 9–15`)

9. **CONFIRMED** — [`access.py:42, 98-100`](file:///C:/Users/arikt/documents/github/distanceFinder/v2/locfinder/traveltime/access.py#L98-L100): `RESTRICTED_PENALTY_S = {"drive": 450.0, "bike": 120.0, "walk": 120.0}`, applied solely to `cost`.
10. **CONFIRMED** — [`speeds.py:132-135`](file:///C:/Users/arikt/documents/github/distanceFinder/v2/locfinder/traveltime/speeds.py#L132-L135) adds `access_penalty_s` per directed graph edge (plus [`snap.py:194-197`](file:///C:/Users/arikt/documents/github/distanceFinder/v2/locfinder/traveltime/snap.py#L194-L197) prorates any penalty on the cell's matched edge by `(1 - frac)` / `frac`).
11. **OVERSTATED** — [`explain_journey.py`](file:///C:/Users/arikt/documents/github/distanceFinder/v2/scripts/explain_journey.py) prints `3 of 29 hops, 159 m, 360 s`, `810.8 s = 13.5 min` across ways `1254722642` and `1254722641`, **but** (a) **misses that the origin's matched edge (`way 430448289`, `104.6 m track`) is ALSO `access=private`**, adding **`+8.66 s` prorated** (`4` restricted edges touched, `1` continuous run); (b) *"identical 159 m drawn as one way would have been charged 120 s"* is false: **`way 1254722641` is one OSM way yet splits into 2 graph edges** under `simplify=True` because junction node `4297214281` intersects it — only a junctionless single **graph edge** charges `120 s`.
12. **OVERSTATED** — While `450 / 120 = 3.75` and `drive` hits `20.19%` of OK cells (`24.1% > 1` edge), [`g1_own_graph_layer.py:65`](file:///C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g1_own_graph_layer.py#L65) uses `ox.graph_from_xml(..., simplify=True)`, collapsing all `degree == 2` OSM geometry nodes; therefore edge count tracks **junction / highway-tag-split density**, NOT OSM node density, and ignores matched-edge proration.
13. **CONFIRMED** — [`measure_restricted_walk_policy.py`](file:///C:/Users/arikt/documents/github/distanceFinder/v2/scripts/measure_restricted_walk_policy.py) gives `1,803 / 163,875 = 1.10%` at `600 s` on **UTM `own_triangle_grocery_walk` `@15 min`** (note: omits explicit `"UTM"` and `"grocery/walk"` qualifiers), switching UTM `(286, 129)` to `1887.1 s` (`31.5 min FAIL`). Our exact per-stretch `(b)` run at `600 s` confirms the core thesis dramatically: **under `(b)`, `600 s` leaves `(286, 129)` unfixed at `810.8 s`** because only one stretch (~`600 s`) is charged instead of multiple edges!
14. **CONFIRMED** — Exact sparse 2-state CSR (`M = 634,695` = `N + 94,881` mixed nodes vs full `2N = 1,079,628`, `0` diffs against `2N`) verifies plain vertex-indexed Dijkstra cannot represent `(b)`, while `(c)` per-metre is invariant to edge splitting.
15. **CONFIRMED** — [`docs/s3-decision-report.md`](file:///C:/Users/arikt/documents/github/distanceFinder/docs/s3-decision-report.md#L15-L55) and [`s3-12-what-the-page-says-at-the-walked-cell.json`](file:///C:/Users/arikt/documents/github/distanceFinder/docs/experiments/s3-12-what-the-page-says-at-the-walked-cell.json#L1-L55) record all 4 E3 criteria unfulfilled (`~25 min` vs `13.5 min` raw UTM / `14 min` published byte at published cell `(282, 126)`).

### Decision 3 — Parks & Destination Snapping (`Claims 16–22`)

16. **CONFIRMED** — [`g1_own_graph_layer.py:37, 104-107`](file:///C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g1_own_graph_layer.py#L104-L107) calls `.centroid`, `ox.nearest_nodes`, and filters `<= POI_SNAP_MAX_M` (`300.0`).
17. **CONFIRMED** — `7` of `746` Overture parks (`node_dist > 300 m`) are dropped silently with zero UI/manifest disclosure.
18. **CONFIRMED** — Verified directly: `pos=456 name='Sharon Harris Lake'` sits `node_dist=356.4 m` and **`edge_dist=0.2 m`**.
19. **OVERSTATED** — Two real errors: (a) *"There is no stated reason for the difference"* is false — [`anchor.py:139-143`](file:///C:/Users/arikt/documents/github/distanceFinder/v2/locfinder/places/anchor.py#L139-L143) states why destination placement uses nodes (*"a destination has to be a graph node for the arrival search"*); (b) **edge-snapping at `300 m` (`POI_SNAP_MAX_M`) recovers `6 of 7`** (only `Parker Creek Campground Playground` at `707.1 m` exceeds `300 m`), whereas **truly making destinations behave like origins (`<= 200 m`) leaves `Ocaneechee Park` (`edge_dist=229.6 m`) dropped too (`5 of 7`)**.
20. **CONFIRMED** — Matches [`57-review-pass56/ANTIGRAVITY.md`](file:///C:/Users/arikt/documents/github/distanceFinder/docs/research/57-review-pass56/ANTIGRAVITY.md#L28): subdividing `302,067` edges `> 100 m` moves `74,930` UTM `park/walk` OK cells and worsens UTM holes (`125 -> 134`).
21. **WRONG** — *"For the 739 parks that are in the layer we measure to the middle, which for a large park can be several hundred metres past the gate."* **Every single park (`746 / 746`) in `overture_places_accepted.parquet` is a `Point` (`0` polygons).** The 739 published parks were never polygon centroids (they lack boundaries altogether; only external `osm_pois.parquet` polygons expose the real-world middle-vs-entry distortion documented in W7).
22. **CONFIRMED** — Proven by W9 across all `7` layers: universal edge-snapping changes `6.00%–30.10%` of published bytes (`71.77%–100.00%` of OK cells), forcing a full rebuild unless restricted to a `> 300 m` fallback.

### Decision 4 — Grey Diagonal Striping (`Claims 23–30`)

23. **CONFIRMED** — [`worker.js:97-101, 467, 473`](file:///C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/worker.js#L464-L474) paints `(r + c) & 7 < 2` with `PX_NODATA` and leaves `75%` as `PX_OUT = 0`, byte-identical to `EXCLUDED`, indexed on the published grid.
24. **CONFIRMED** — Verified verbatim via [`measure_hatch_visibility.py`](file:///C:/Users/arikt/documents/github/distanceFinder/v2/scripts/measure_hatch_visibility.py) on published `park/walk @20 min`: `56,034` UNKNOWN, `14,023` painted (`25.03%`), `42,011` `PX_OUT`.
25. **CONFIRMED** — Exact output: `1,075` 8-connected regions, `369` (`34.3%`) wholly invisible (`975` cells) — while W13 proves `352 / 369` hold zero buildings (`55` buildings = `0.011%` total).
26. **OVERSTATED** — Counts (`73.1%` 1-cell, `64.6%` 2-3, `12.9%` 9-16, `0%` 65+ [`166` regions], median `7`) are exact for published `park/walk` at `15m` (`55,752` cells) and `20m` (`56,034` cells; claim omits layer & threshold), **overstated** on *"the design works for the big ones"*: the `166` `65+` regions contain **`82.4%` (`46,174 / 56,034` `@20m`) of UNKNOWN cells and `86.3%` (`2,904 / 3,364` `@20m`) of UNKNOWN buildings**, leave `75%` unpainted `PX_OUT`, and generate the zebra striping that triggered the complaint.
27. **CONFIRMED** — Code faithfully implemented `worker.js`'s spec, which failed both small-region marking (`369` invisible) and large-region legibility.
28. **CONFIRMED** — `measure_hatch_visibility.py` yields identical status-1 counts (`56,036`) and UNKNOWN/painted/blob totals across `park`, `grocery`, and `school` walk at every limit (`5–60 min`).
29. **CONFIRMED** — `56,036 / 330,502` (`16.95%`) on the published walk grid have `status = 1` (`OFF_NETWORK`, `> 200 m` from roads; note drive/bike differ).
30. **OVERSTATED** — *"Either could satisfy the owner's complaint"* is false for shrinking `UNKNOWN`: raising `MAX_ACCESS_M` `(v)` leaves large unnetworked lakes/forests hatched while eroding time honesty across rural parcels, and clipping `(vi)` fails on `80.3%` (`44,995`) strictly interior cells while [`worker.js:534`](file:///C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/worker.js#L533-L536) turns `S_OUTSIDE` into `O_UNKNOWN` stripes anyway.

---

## 3. Verdicts on the Owner's Four Positions

### Decision 1 — *"Measure first."* (Option 4)
**Verdict: UNSUPPORTED** (specifically Option 4 as framed: testing OSM noding gaps first).
* **How it breaks:** Option 4 assumes "do these ways cross without a node?" bounds Claim 3's defect rate. Across all `125` UTM `park/walk @20 min` holes, only **`4 / 125` (`3.2%`)** have `<= 5 m` topological gaps (`0` crossings), while `121 / 125` (`96.8%`) are disconnected roads separated by median `67.7 m` — including `49` directly behind mapped buildings — and Decision 17 prohibits copying Overture/Google geometry back to OSM anyway.
* **What would move it to SUPPORTED:** Scoping `"measure first"` as a **sample audit of the `72` open-ground holes** (checking on aerial imagery whether fences/ditches block them vs unmapped pedestrian paths) to decide whether a building/barrier-filtered `+25 m` / `+50 m` rule repairs real walks or creates false positives.

### Decision 2 — *"Per stretch."* (Option b)
**Verdict: PREMATURE.**
* **How it breaks:** The intuitive argument (*"price the decision to enter private land, not OSM vertex splits"*) is appealing, *but*: (1) switching `(a) -> (b)` at `120 s` changes only **`2.2%–3.7%`** of walk OK cells and **solely weakens** the deterrence on multi-edge private tracks (`+170 / -6` `15m` PASS flips on `grocery/walk`); (2) at **`600 s`**, exact `(b)` **still fails to move the walked cell `(286, 129)`** off the `810.8 s` (`13.5 min`) private shortcut because one stretch pays ~`600 s` instead of `~1,843 s`; (3) `(b)` misses the physical length intuition (`2 km` vs `50 m` of private road, `(c)`).
* **What would move it to SUPPORTED:** Complete the E3 timed walk harness across restricted routes (`band15min_pass-03` plus `5–10` other `route_flag == 1` routes) and test whether `(b)` with an empirically calibrated stretch penalty beats `(c)` per-metre on observed route choice.

### Decision 3 — *"We should never use a centroid, else large parks would be tagged unrealistically far away..."*
**Verdict: SUPPORTED in principle, PREMATURE against the shipped Overture park layer.**
* **How it breaks / nuance:** Against the current shipped bundle, **there are zero park centroids (`746 / 746` Overture parks are `Point`s)**. Replacing "centroids" inside [`g1_own_graph_layer.py`](file:///C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g1_own_graph_layer.py#L104-L107) right now changes nothing about `.centroid`. **However**, evaluating real park geometries from `osm_pois.parquet` (`1,002` polygons) proves the owner's *geographic* instinct overwhelmingly right: across **`11,427` published cells abutting large parks (`cen->bnd > 100 m`)**, the shipped map shows **median `31 min`**, whereas **`OSM_road_entries (<= 50 m)`** reports **median `9 min`** — an error of **median `17 min`, p90 `60 min`, max `117 min`**.
* **What would move it to fully actionable / SUPPORTED:** Do *not* switch to unscreened nearest boundary (`Harris Nuclear Plant` = `9,628 ha` `nature_reserve`, `136 / 29,594` fence-jumping samples); test **`leisure=park` road-entry points (`<= 50 m`, barrier-screened) + mapped `entrance=*` / non-private gates** on a walk audit around Umstead, Eno River, and Duke Forest.

### Decision 4 — *"I disagree that the grey diagonal lines of nodata are okay — those striping effects are problematic and should be rectified."*
*(Product judgement belongs to the owner; evaluating options and diagnosis.)*
* **Diagnosis of the complaint:** The author wondered whether the issue was `< 1x` moiré or the `369` wholly invisible holes. On normal desktop load (`800×700` to `1040×820`, `1.19–1.54 px/col` with `raster-resampling: 'nearest'`), the `8`-cell diagonal period visibly renders as coarse **`~200 m`-wide dark bars on `~600 m` transparent gaps across 17% of the map**, paired with a legend reading **`"nodata in an enabled layer"`** ([`index.html:29`](file:///C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/index.html#L29)). The owner described exactly what the initial screen shows.
* **Verdict on options:**
  * **Option `(vi)` (clip UNKNOWN) — UNSUPPORTED:** `80.3%` (`44,995` cells, `2,811` buildings) are strictly interior, and `worker.js:534` paints `S_OUTSIDE` with the exact same hatch.
  * **Option `(i)` (flat grey solid wash) — WEAK alone:** replaces stripes across ~560 km² with muddied lakes/forests.
  * **Option `(iv)` (screen-space hairline hatch + ~6–8% neutral tint wash) + legend copy fix — SUPPORTED:** cleanly removes both grid aliasing/zebra bars at every zoom *and* all `369` invisible blobs, while preserving lakes/basemap contrast.

---

## 4. What Is Right in the Analysis

1. **Structural honesty on two-grid separation (`published-v4`):** The notes consistently guard against confusing UTM indices (`(286, 129)`) with published WGS84 indices (`(282, 126)`), confirmed cleanly across every check.
2. **Claim 4 & W9 instincts:** Refusing to accept net hole reductions (`125 -> 30`) without flagging newly manufactured holes was dead right (`200 m` creates `30` new UTM holes; `+50 m` creates `71`), and warning that wholesale destination edge-snapping dirties **all 7 layers** (`6%–30%` of bytes) was fully vindicated (`W9`).
3. **E3 admissibility discipline (`Claim 15`):** Refusing to force a `600 s` penalty calibration onto an undocumented, untimed single observation saved the pipeline from shipping an arbitrary parameter (`per-stretch 600 s` doesn't even fix `(286, 129)`).
4. **Adding [`measure_hatch_visibility.py`](file:///C:/Users/arikt/documents/github/distanceFinder/v2/scripts/measure_hatch_visibility.py):** Testing the owner's visual complaint quantitatively immediately falsified the pass-56 claim that the hatch "worked as designed" across `369` invisible regions.

---

## 5. Ranking of the Four Decisions by Product Risk Retired (Plan §0)

[`docs/plans/2026-11-04-s3-execution-plan.md`](file:///C:/Users/arikt/documents/github/distanceFinder/docs/plans/2026-11-04-s3-execution-plan.md#L86-L97) §0 requires ordering work by **product risk retired, not defect severity or inquiry order**. By that rule, the note's **1 → 2 → 3 → (4)** presentation order is **upside down**:

| §0 Rank | Decision | Households / Map Footprint & Misleading Magnitude | Concrete Next Step (No Option Taken Yet) |
|---:|---|---|---|
| **1** | **Decision 4** *(Grey striping & legend)* | **16.95% of walk map** (`56,036` cells, `3,364` bld; `19.1%` drive) covered by coarse ~800 m zebra bars on initial desktop load + `"nodata in an enabled layer"` jargon; `86.3%` (`2,904`) of UNKNOWN buildings sit inside striped zones. | Fast isolated UI change in [`worker.js`](file:///C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/worker.js#L469-L474) / MapLibre layer (`screen-space hairline + faint tint` + plain-English legend) **before** running the reading test (`s3-13`). Zero graph rebuild needed. |
| **2** | **Decision 3** *(Park entries & missing destinations)* | **`11,427` published cells abutting large parks off by median `17 min`, p90 `60 min`, max `117 min`** vs barrier-screened `OSM_road_entries (<=50m)`; `7` Overture parks silently missing (`Duke Forest` absent; `9` park points inside `Harris Nuclear Plant`). | Split into two pieces: (a) narrow `> 300 m` **fallback edge-snap** recovers `6 / 7` dropped parks with **zero** churn to existing points; (b) prepare barrier/tag-screened `OSM_road_entries (<=50m)` as candidate park-source replacement for owner review + spot walk check. |
| **3** | **Decision 2** *(Penalty unit `(a)/(b)/(c)`)* | **`22%–25%` of walk OK cells** (`9.3%` `15m` grocery PASS bld) and `20.2%` of drive OK cells touch restricted ways — *but* switching `(a)->(b)` at `120 s` only moves `2.2%–3.7%` of OK cells and leaves `(286, 129)` unfixed even at `600 s`. | Keep `120 s` + route disclosure shipped (`published-v4`), run **E3 timed walks** across `route_flag == 1` journeys first, then test **both `(b)` (via `94,881`-node sparse 2-state) and `(c)` per-metre** against walked ground truth before touching routing cost. |
| **4** | **Decision 1** *(Donut holes)* | **Smallest aggregate exposure:** `0.0711%` of all / `0.13%–0.20%` of in-region buildings (`356 @20m` across `76` parcels, `388 @15m` across `84` parcels); `96.8%` are real disconnected road gaps, not OSM junction typos. | Defer behind Decisions 4, 3, and 2. Instead of Option 4's pure-topology test, inspect a sample of the `72` open-ground holes against imagery/parcels; if real pedestrian shortcuts dominate, prototype a building/barrier-filtered `+25 m` / `+50 m` or routed access fallback. |
