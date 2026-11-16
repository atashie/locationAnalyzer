# Pass 56 review - Antigravity / Gemini (gemini-4-hydrogen-xhigh)

Run 2026-11-16 against the prompt in docs/research/57-review-pass56-prompt.md, independently
of the Codex pass beside it and without sight of it. Captured from stdout; the reviewer was
given no write access to the repository. Unlike Codex it COULD execute Python, and ran the
real-graph subdivision experiment for W7 rather than constructing one.

---

# Pass 56 Independent Review (`9cfa6c3`, `a5ff969`, `project-phase1-s3-donut-holes.md`)

**Verdict tally across Claims 1–20:** **11 CONFIRMED**, **7 OVERSTATED**, **2 WRONG** (Claims **11** and **20**).

The core engineering instincts hold up: the diagonal hatch is intentional UI styling for `OFF_NETWORK` cells (`worker.js`), and shipping unpenalized 200 m multi-candidate snapping (`measure_access_candidates.py`) would trade ~95 local holes for 88,978–90,040 cells jumping >60 s onto ~169 m straight-line edges. Where the write-up slips is precision and scope discipline: seven claims overstate single-slice or UTM-grid numbers onto the published map (`4, 5, 7, 10, 14, 16, 17`), the edge-subdivision impossibility claim (**11**) fails both synthetically and on the live walk graph, and the Apache destination-record audit (**20**) cites raw parquet counts (`41` / `137`) rather than shipped/selectable records (`35` / `120`).

---

## Declared Weaknesses (W1–W7) Executed

| Weakness | Test & Observed Result | Impact on Claims |
| --- | --- | --- |
| **W1** (`_snap_network` reconstruction vs [own_triangle_park_walk.npy](file:///C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/fixtures/layers/own_triangle_park_walk.npy)) | Adding `cutoff_s=7200.0` + float32 cast gives **`0` cell differences** (`array_equal=True`). However, [measure_access_candidates.py](file:///C:/Users/arikt/documents/github/distanceFinder/v2/scripts/measure_access_candidates.py#L94-L95) omits the 7200 s horizon cap, so all **`4,900` `BEYOND_HORIZON`** cells enter `cur_total` as finite `7200.04–11482.24 s`. | **Material denominator inflation, direction unchanged:** on published `OK` cells only, **12** becomes **`207,947 / 268,061` (`77.57%`)** (vs `210,533 / 272,961` = `77.13%`), and **13** becomes **`88,978`** >60 s cells (vs `90,040`) with median `168.80 m`, p90 `195.65 m`, `<=50 m` `1.05%`. |
| **W2** (`STRtree.query(pts, predicate="dwithin", ...)` row order) | Direct probe on 5 m `dwithin` confirms **row 0 = `pts` index**, **row 1 = `tree` index**. | **Claims 12–15 indexing valid.** |
| **W3** (`np.roll` ring border handling) | Compared `np.roll` mask (first/last row & col zeroed) against non-wrapping slice indexing across all 4 layers at `[5, 10, 15, 20, 30]`: **`0` differences**. | **Claims 6–9 hole masks exact.** |
| **W4** (`np.lexsort((cand_total, pi))` tie-breaking in Claim 13) | Checked `28,869` of `90,040` cells that have `>1` candidate within `1e-9 s` of `winner`, plus `cur_total < winner - 1e-6`: **`0` cells** had `cur_total < winner - 1e-6`, and **`0` cells** had tied-winner `acc` spread `> 0.01 m` (`max spread = 0.0`, median `168.81 m`, p90 `195.65 m`). | **Claim 13 is unaffected by ties.** (`RuntimeWarning` on `frac * rev_t` comes from self-loop edges like `4565712609->4565712609` where `snap.py` leaves `rev_t = inf`; `np.where` still assigns `np.inf` cleanly.) |
| **W5** (identical hatched sets, not just counts) | Direct cell-by-cell comparison across `grocery_walk`, `park_walk`, and `school_walk` at every slider step `1..60` on published WGS84 `.status.bin` / `.val.bin` and on UTM `reason == 1` / `min_possible_s[off_net]`: **`0` diffs**. | **Claim 3 verified as exact set identity.** |
| **W6** (`57,237` unsettled DOM count; WGS84 vs UTM gap) | Running `worker.js` directly in Node on `park(15) + rdu-airport(40)` produces **`nodataCount = 57,237`** (the multi-criterion combination before the threshold update landed). Nearest-neighbour reprojection (`export_published_layers.reproject_plane`) of UTM `reason == 1` reproduces published WGS84 `status == 1` bit-for-bit (`True`), sampling `315,512` distinct UTM cells (dropping `14,990` incl. `4,075` `OFF_NETWORK`, duplicating `14,898` incl. `2,556` `OFF_NETWORK >= 2x`). | **Unsettled explanation true**; however WGS84 `park_walk` saturates at **`56,036`** (>=21 min), not `56,034` (**Claim 4**). |
| **W7** (Claim 11: "subdividing an edge does not change shortest-path distances") | **Executed synthetically & on the real Triangle walk graph:** (1) splitting a 140 m `access=private` edge doubles its fixed `RESTRICTED_PENALTY_S = 120.0` (node jumps `100.0 s -> 280.0 s`, cell `101.34 s -> 279.05 s`); (2) on the real graph (`123,756` restricted walk directed edges, `9,345` > 200 m), splitting the **`302,067` edges > 100 m** shifts **`4,915` OK cells** (`max 2,068.9 s`, `133` reachability changes) even with *identical* POI nodes; re-snapping POIs (`ox.nearest_nodes`) recovers **`6` of the `7` dropped parks** (`745` vs `739`, e.g., park `#456` sits `0.2 m` from an edge but `356.4 m` from a node) and moves **`74,930` OK cells** (`max 2,893.2 s`, `185` reachability changes). Holes at 20 min still rise: `125 -> 131` (same POIs) / `134` (re-snapped). | **Claim 11's invariance claim is WRONG.** The owner's subdivision intuition does change distances/snaps substantially—yet still worsens hole counts (`125 -> 131 / 134`). |

---

## Claim-by-Claim Verdicts (1–20)

| # | Verdict | Summary Evidence |
| --- | --- | --- |
| **1** | **CONFIRMED** | [worker.js](file:///C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/worker.js#L98-L101) defines `PX_NODATA = packRGBA(60, 60, 60, 130)` and paints `(((r + c) & 7) < 2) ? PX_NODATA : PX_OUT` ([worker.js](file:///C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/worker.js#L470-L474)). |
| **2** | **CONFIRMED** | Walk `.status.bin` contain only `{0, 1, 2}` (`horizon_s = 7200`, `BEYOND_HORIZON` = 4,900 UTM `park/walk` cells); [app.js](file:///C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/app.js#L567) bounds slider `T` to `1..60` (`<= 3600 s < 7200 s`), so `BEYOND_HORIZON` is always FAIL, never UNKNOWN. |
| **3** | **CONFIRMED** | W5 check across `grocery_walk`, `park_walk`, `school_walk` gives **`0` cell differences** at every threshold `1..60` on WGS84 and on UTM `reason == 1` / `min_possible_s`. |
| **4** | **OVERSTATED** | Direct Node execution of `worker.js` on published `park_walk`: `T=5`: `38,834`; `T=10`: `53,764`; `T=15`: `55,752`; `T=19`: `56,030`; `T=20`: `56,034`; **`T=21, 25, 30, 45, 60`: `56,036`** (not flat after 20!). Two `OFF_NETWORK` cells have 21-min lower bounds (`1205.04 s`, `1206.42 s`), matching UTM jumping `57,539 -> 57,541` (`measure_unknown_hatch.py`). Meanwhile [s3-13-reading-test.md](file:///C:/Users/arikt/documents/github/distanceFinder/docs/experiments/s3-13-reading-test.md#L173-L178) contradicts Claim 4 by writing `56,036 at 20`. (Coincidentally both extra cells fall outside `((r+c)&7)<2`, keeping painted pixels at `14,023`.) |
| **5** | **OVERSTATED** | `17.4%` (`57,541 / 330,502 = 17.41%`) and `0.71%` (`3,657 / 512,633`) are exact on **UTM** ([measure_unknown_hatch.py](file:///C:/Users/arikt/documents/github/distanceFinder/v2/scripts/measure_unknown_hatch.py)). On the **published WGS84** grid shown to users: `56,036 / 330,502 = 16.95%` and `3,364 / 500,451 = 0.67%` (out of `522,160` total parquet buildings). [s3-13-reading-test.md](file:///C:/Users/arikt/documents/github/distanceFinder/docs/experiments/s3-13-reading-test.md#L173-L178) mixes UTM `17.4%`/`0.71%` with WGS84 `38,834`/`56,036` in one paragraph. |
| **6** | **CONFIRMED** | [measure_donut_holes.py](file:///C:/Users/arikt/documents/github/distanceFinder/v2/scripts/measure_donut_holes.py) reproduces `125` (`park/walk`), `113` (`grocery/walk`), `132` (`school/walk`) at 20 min on UTM (WGS84 counts are `121`, `109`, `121`). |
| **7** | **OVERSTATED** | True on the walk layers (`{0: N}`), **false as stated** ("Every hole"): `measure_donut_holes.py` reports **`NO_PATH` holes on `grocery/drive`** (`{0: 353, 3: 14}` at 5 min, `{0: 83, 3: 15}` at 10 min, `{0: 31, 3: 15}` at 15 min; WGS84 `5 min`: `{0: 326, 3: 14}`). |
| **8** | **CONFIRMED** | `measure_donut_holes.py` prints `median 241 s, p90 449 s, max 753 s` on UTM `park/walk` 20 min. |
| **9** | **CONFIRMED** | Confirmed on UTM (`414` buildings across `75` of `125` holes). On published WGS84: `356` buildings across `76` of `121` holes. |
| **10** | **OVERSTATED** | Single-edge `idx.tree.nearest(pts)` snap confirmed ([snap.py](file:///C:/Users/arikt/documents/github/distanceFinder/v2/locfinder/traveltime/snap.py)). However, **"the whole gap is in `atnode`" overstates**: in Hole 1 `(356, 395)` `atnode` gap is `683.9 / 752.8 s` (`90.8%`), while `onedge = 341.2 s` (`+78.9 s` vs ring mean, `+334 s` vs `+1-1`) pushes `atnode = 18.45 min` (`1107.0 s`) over 20 min; across all `125` holes `108/125` have `atnode <= 1200 s`, and `atnode / gap_tot` spans `-3.002` to `2.620` (p10 `0.570`, median `1.051`). |
| **11** | **WRONG** | First half (`(1 - frac) * fwd_t` / directional endpoint walk, not penalty to nearest node) confirmed. Second half (**"subdividing an edge does not change shortest-path distances"**) is **WRONG**: W7 real-graph test moves `4,915` OK cells (up to `2,068.9 s`) at fixed POI nodes via per-edge `RESTRICTED_PENALTY_S`, and recovers `6/7` dropped parks + moves `74,930` OK cells (up to `2,893.2 s`) on re-snap (still rising holes `125 -> 131 / 134`). |
| **12** | **CONFIRMED** | Script outputs `125 -> 30`, `210,533 (77.1%)`, `median 46 s`, `p99 1,312 s`, `0` worse (`0` worse confirmed). After fixing W1's missing `7200 s` cap, `OK`-only result is `207,947 / 268,061` (`77.57%`). |
| **13** | **CONFIRMED** | `OK`-only (>60 s) yields `88,978` cells (vs `90,040`), median `168.80 m` (vs `169 m`), p90 `195.65 m` (vs `196 m`), `<=50 m` `1.05%` (vs `1.0%`), today's median `38 m`; W4 tie spread is `0.0 m`. |
| **14** | **OVERSTATED** | `+50 m` removes `23.2%` (`125 -> 96`) **only at 20 min**. At the other thresholds printed by `measure_access_candidates.py` for `park/walk`, `+50 m` removes **`38.8%` at 10 min** (`80 -> 49`), **`39.8%` at 15 min** (`123 -> 74`), and **`26.3%` at 30 min** (`80 -> 59`). |
| **15** | **CONFIRMED** | Script outputs `service:parking_aisle` `10.4%` (`2.8x`) and `residential` `35.2%` vs `26.90%` baseline. Note the random 20k baseline includes `17.615%` `OFF_NETWORK` rows; against an `OK`-only baseline, `service:parking_aisle` is `4.29%` (`2.4x` enriched) and `residential` is `29.42%`—same conclusion. |
| **16** | **OVERSTATED** | Verified in `G` and raw `triangle-roads.osm`: ways `461005440`/`461005460` (`parking_aisle`, simplified into self-loop `4565712609->4565712609`) share **`0` nodes** with `746439842` (Atlantic Ave). **Fact error on `"33 m away"`:** Atlantic Ave is **`105.94 m`** from hole `(365, 539)` and **`85.85 m`** from the matched edge geometry (`33.3 m` is neighbour `+0+1`'s access leg in `explain_donut_hole.py`!). Closer connected `track` edges sit at `31.4 m` (`461005430`, `best_node_T=7.0m`) and `40.0 m` (`461005466`, `best_node_T=6.3m`). |
| **17** | **OVERSTATED** | `NO_PATH` counts (`57` drive / `95` bike UTM; `39` / `80` WGS84) and ledger instance 53 in [project-phase1-s0-complete.md](file:///C:/Users/arikt/documents/github/distanceFinder/docs/engineering-notes/project-phase1-s0-complete.md) confirmed. **Overstated cleanup:** [layer-contract.md](file:///C:/Users/arikt/documents/github/distanceFinder/docs/plans/layer-contract.md#L64-L65) still carries `"NO_PATH is unreachable in every configuration we currently ship."` at lines `64–65`, `553`, and `566` (repeating ledger instance 40/47). |
| **18** | **CONFIRMED** | Direct Node check of `worker.js`: all 7 ON at `{walk:20, bike:15, drive:10}` yields **`0` in-region cells** (`49,274` unknown, `281,228` excluded). With `default_on` / `default_threshold_min`, opening default yields `74,227` in-region (`17,393` with all 7 ON at `default_threshold_min`), and `card.js` is absent-safe. |
| **19** | **CONFIRMED** | `9cfa6c3` added `label` in `worker.js` and updated `card.js` to render `crit.label || crit.layer`. |
| **20** | **WRONG** | Qualitative licence/manifest tension confirmed ([manifest.json](file:///C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/fixtures/published/manifest.json#L16-L20): `"apache_records_are_cleared_for_redistribution": false`), **but both record counts are wrong**. Shipped grocery has **`35`** Apache-2.0 records (not `41`), and `persist_selected_destination.py` selection on park + school + coffee would ship **`39 + 2 + 79 = 120`** Apache-2.0 records (not `44 + 3 + 90 = 137`, which are pre-snap / pre-dedup parquet counts). |

<details>
<summary>Re-executed fast verification output (`measure_unknown_hatch.py`, `measure_donut_holes.py`) & existing suite baselines</summary>

- `cd v2; .\.venv\Scripts\python.exe scripts/measure_unknown_hatch.py`: `330,502 cells, 512,633 buildings`; all three walk layers (`park`, `grocery`, `school`) report identical `OFF_NETWORK`: `57,541` (`10->55,102`, `15->57,243`, `20->57,539`, `30/45/60->57,541`), lower bounds `min 3, median 4, p90 8, max 21`, `3,657 buildings (0.71% of all)`.
- `cd v2; .\.venv\Scripts\python.exe scripts/measure_donut_holes.py`: UTM `park/walk @ 20m` `125` holes (`{0: 125}`, `median 241 s, p90 449 s, max 753 s`), `grocery/walk @ 20m` `113`, `school/walk @ 20m` `132`; `grocery/drive` `5m: 367 {0:353, 3:14}`, `10m: 98 {0:83, 3:15}`, `15m: 46 {0:31, 3:15}`.
- Prior unmodified-repo test runs observed before context truncation: `1553 passed, 24 skipped` (`cd v2; .\.venv\Scripts\python.exe -m pytest -o addopts=""`), plus passing `spikes/g3-render/card_selftest.mjs` and `spikes/g3-render/worker_conformance.mjs`.

</details>

---

## What Is Right in `9cfa6c3` and `a5ff969`

1. **Holding off on unpenalized 200 m multi-candidate snapping (`a5ff969`)**: Re-verifying with `cutoff_s=7200` and `0.0 m` tie-spread confirms that letting every cell jump to the fastest edge within 200 m alters **`77.57%` of all `OK` cells** and moves `88,978` cells by >60 s onto **`168.80 m` median** straight-line teleports (only `1.05%` within 50 m). Rejecting this knee-jerk fix prevented silent map distortion.
2. **Diagnosing both user-reported surprises accurately in essence**: Grey diagonals are `PX_NODATA` (`OFF_NETWORK`) rather than Park corruption, and `default_on` / `default_threshold_min` + label rendering (`9cfa6c3`) stopped the 7-criterion launch from rendering **`0` cells**.
3. **Resisting premature Apache-2.0 destination publication (`9cfa6c3`)**: Flagging the manifest redistribution guard before exporting park/school/coffee records avoided shipping ~120 additional un-cleared records (even though the parquet counts `41`/`137` were imprecise).

---

## Findings Ranked by Product Risk Retired (per §0 of [execution plan](file:///C:/Users/arikt/documents/github/distanceFinder/docs/plans/2026-11-04-s3-execution-plan.md))

1. **Legend & UX comprehension risk ahead of the reading test ([s3-13-reading-test.md](file:///C:/Users/arikt/documents/github/distanceFinder/docs/experiments/s3-13-reading-test.md), [index.html](file:///C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/index.html#L29)):** Leaving 17% of the map cross-hatched with the legend text `"nodata in an enabled layer"` already misled the project owner into thinking data was corrupted. Doing nothing until after user testing guarantees test participants waste cognitive load decoding UI jargon instead of testing spatial reading.
2. **Misframed root cause locking in flawed snapping assumptions (Claims 10, 11, 16, W7):** Treating donut holes as simple "missing OSM links next to `parking_aisle` edges 33 m from a secondary road" misreads the broader coupled defect:
   - Single-edge `nearest()` snapping creates boundary cliffs across `77.6%` of the surface (`residential` is 35.2% of holes; `service=parking_aisle` only 10.4%).
   - Drive holes include **`14–15` `NO_PATH` islands** (Claim 7), not just `OK` slow cells.
   - `ox.nearest_nodes` POI snapping drops `6` parks that sit `0.2–229.6 m` from walk edges (`#456` at `0.2 m`), while per-edge `120 s` `RESTRICTED_PENALTY_S` violates graph subdivision invariance across `9,345` restricted walk edges >200 m.
3. **Active architectural contract drift ([layer-contract.md](file:///C:/Users/arikt/documents/github/distanceFinder/docs/plans/layer-contract.md#L64-L65)):** Claiming `NO_PATH is unreachable in every configuration we currently ship` in three places (`L64–65`, `L553`, `L566`) despite shipping 39 drive / 80 bike `NO_PATH` cells reproduces the exact ledger-instance 40/47 hazard for future work on status handling and UI cards.
4. **Cross-grid & pre-snap counting errors eroding note credibility (Claims 4, 5, 14, 16, 20):** Reporting `41`/`137` instead of shipped/selectable `35`/`120`, mixing WGS84 counts (`38,834`/`56,036`) with UTM rates (`17.4%`/`0.71%`), asserting flat `56,034` above 20 min, citing `23%` for `+50 m` (actually `38.8–39.8%` at 10–15 min), and misattributing neighbour `+0+1`'s `33.3 m` leg (`105.94 m` actual distance to Atlantic Ave) leave avoidable contradictions across repo docs.

---

## Critique of the Recommendation

> *"Do nothing yet; test the connectivity hypothesis first."*

**Right not to patch `snap._snap_network` with naive 200 m minimum-of-candidates today.** That option clearly breaks Euclidean access realism (`168.8 m` straight-line jumps across blocks).

**Wrong as a complete next step on three fronts:**
1. **Fix the hatch legend before the reading test**: replace `"nodata in an enabled layer"` with plain user language (e.g., `"off-network / >200 m from road — too close to tell"` or `"no nearby path"`), and note `56,036` / WGS84 figures consistently in [s3-13-reading-test.md](file:///C:/Users/arikt/documents/github/distanceFinder/docs/experiments/s3-13-reading-test.md).
2. **Don't stop at a hand-audit of OSM `parking_aisle` connectivity**: only 10.4% of holes are `parking_aisle`, `NO_PATH` islands cause drive holes too, and the same graph pipeline simultaneously suffers from node-only POI snapping (`6` dropped parks) and per-edge restricted penalties (W7).
3. **Prototype the right architectural fix (`v2` snapping backlog):** compare **restricted/bounded multi-candidate snapping** (e.g., candidates within `min(nearest_m + 30..50m, 200m)` with an off-network penalty on `service=parking_aisle`/`private` links or cost-per-meter restricted penalty + edge-based POI snapping) rather than binary nearest-edge vs unconstrained 200 m, and clean up the stale `NO_PATH` assertions in [layer-contract.md](file:///C:/Users/arikt/documents/github/distanceFinder/docs/plans/layer-contract.md#L64-L65) right away.
