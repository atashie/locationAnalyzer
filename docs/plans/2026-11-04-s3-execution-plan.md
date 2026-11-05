# S3 execution plan — building the instrument the measurement design predeclares

**Status:** plan, for adversarial review. **Nothing here reports a result.**
**Revision 2, 2026-11-04**, rewritten after Codex pass 15 found the previous revision "not fit to
execute as written" — eight High and ten Medium defects, three of them introduced by the plan itself
while trying to make revision 2 of the design executable.
**Branch:** `v2-rethink` · **Head:** `ab01ffa`

**What this executes:** [`2026-11-04-s3-measurement-design.md`](./2026-11-04-s3-measurement-design.md)
**revision 3**, which is the operative document. Where this plan and that design differ, the design
wins and this plan is wrong.

**What changed from revision 1 of this plan.** Revision 1 proposed three "gates" where the design
could not be executed as written; all three were confirmed real, and the owner has now settled them
along with the question revision 1 deferred. The design absorbed those answers, so this plan no
longer proposes design changes — it implements them. The substantive differences:

- **T2 is deleted.** The 2 km block grid, the ≥5-points pooling rule and the block bootstrap are gone
  with the design effect. Revision 1's pooling-termination fix would have produced a degenerate
  bootstrap — the identical dataset in all 2,000 replicates, reported as a zero-width interval.
- **T5 is substantially larger**, because coordinate-based destination attachment, a pre-collapse
  time projection and bound metadata are all now required rather than assumed.
- **The sample is 2,600 origins, not 1,500**, because diagnostics A and B are per threshold.
- **The dry run is replaced** by fixtures, then a separate development sample, then a freeze.
- **Three tasks are added** for work revision 1 left unassigned: E3 ingestion, the grid comparison,
  and the encoding freeze's measurements.

---

## 1. Scope

**In:** walk, grocery, Triangle, the 100 m grid, *T* ∈ {10, 15, 25, 45} minutes, frames B and C, E1
and E2, the four diagnostics, and the encoding freeze now that the maximum duration is decided.

**Out:**

- **drive, bike, transit** — no Triangle-scale layer exists. Verified: the walk surface, its reason
  raster, buildings-per-cell and one-way mask are all (514, 643); every drive, bike and Valhalla
  layer in `v2/data/layers/` is (401, 550) — the earlier, smaller slice. So §8's "every published
  mode and threshold must pass" **cannot** be satisfied now, for the plain reason that three of the
  four modes have nothing to verify. The §8 verdict is reported **for walk / grocery / Triangle only
  and named as such**, and the gate is re-run per mode as layers land in S6. Describing the layer set
  as verified on one mode is the averaging-away §8's last sentence forbids.
- **walking the E3 journeys** — the owner's. T8 builds the ingestion and scoring so the result is not
  a hand calculation.
- **any claim about households** — frame B is a frame of **structures**.

---

## 2. Tasks

Ordering rationale: T1 is fully specified and its correctness is checkable against closed forms, so
it is first and it is the cheapest place to discover a misreading. T5 is the expensive and
ambiguous one, so it is deliberately not first, and by the time it starts the verdict arithmetic it
feeds already has tests. T6 cannot begin until the instrument freezes (design §10).

### T1 — `v2/locfinder/measure/stats.py`

**Depends on:** nothing.

```python
def clopper_pearson_upper(failures: int, n: int, *, confidence: float = 0.95) -> float: ...
def tolerated_failures(n: int, threshold: float, *, confidence: float = 0.95) -> int: ...
def bootstrap_ci(values, *, replicates: int = 2000, seed: int,
                 statistic=np.median) -> tuple[float, float]: ...
```

No DEFF, no `effective_n`, no block machinery (design §5). `bootstrap_ci` resamples **points**.

**Tests.** Revision 1's fixtures were the design's zero-failure table alone, and pass 15 produced a
wrong implementation that satisfies every one of them:

```python
k / n + (1 - k / n) * (1 - 0.05 ** (1 / n))     # matches all zero-event values,
                                                 # the endpoints and monotonicity
```

At *k* = 1, *n* = 400 it gives **0.9943%** against the correct **1.1804%** — enough to flip an E1b
verdict. So the tests are:

- **Non-zero fixtures**, independently computed: *k* = 1, 2, 3, 4 at *n* = 400 and 500, against
  values from the Beta quantile relation `p_u = BetaInv(1 − α, k + 1, n − k)`, which is a different
  route to the number than a search over the binomial tail.
- **Two closed forms at zero failures**, both independent of the table: exact is
  `1 − α**(1/n)`, and Wilson at zero events is `z²/(n + z²)`.
- **Confidence-level variation** — 90% and 99% must move the bound in the right direction and amount.
- `failures == n` is exactly 1.0; monotone in `failures`; anti-monotone in `n`.
- **A stated rounding tolerance.** The design's printed table is rounded, so literal equality to its
  decimals is not a correct numerical test; comparisons use `pytest.approx` at a declared tolerance.
- `tolerated_failures(500, 0.01) == 1` and `tolerated_failures(500, 0.02) == 4`, which pins design
  §8's stated consequence in code rather than in prose.
- The bootstrap is reproducible from its seed, and its interval **widens** as the sample shrinks —
  the property revision 1's single-block fallback destroyed.

**Verification:** `pytest v2/tests/test_stats.py -v`.

### T2 — `v2/locfinder/measure/frames.py`, plus frozen artifacts

**Depends on:** T1.

Design §1. Two frames, two seeded samples at ***n* = 500**, with digests.

- **Frame B** from `v2/data/triangle/overture_buildings_accepted.parquet`. **Verified, not assumed:
  522,160 rows (522,109 Polygon + 51 MultiPolygon) and 512,633 projected centroids inside the 100 m
  grid.** Centroids computed **projected** to EPSG:32617, never in the geographic CRS.
- **Frame C** over all 330,502 cells: SRS without replacement of cells, then **one uniformly random
  point inside each sampled cell**.

```python
@dataclass(frozen=True)
class Frame:
    kind: str                  # "buildings" | "cells"
    points: np.ndarray         # (n, 2) float64, EPSG:32617
    source_ids: np.ndarray     # building id, or flat cell index
    seed: int
    population_n: int          # 512,633 (measured) or 330,502
    source_digest: str
    digest: str
```

Written to `v2/data/frames/frame_{b,c}_<digest8>.parquet` with a sibling `.json` manifest holding the
seed, population count, source digest, sampling method and code version. **Never overwritten**: a
new sample is a new digest.

**Tests.** Revision 1's tests permitted frame C points always at cell **centres** — they are
reproducible, inside distinct sampled cells, and satisfied every assertion. So:

- **Reject centre-only placement**: over many seeded draws the within-cell offsets must cover the
  cell, tested as a distributional property (offsets not constant, mean near the centre, spread
  consistent with uniform) rather than by a single point's position.
- **Reject a fixed building subset**: two seeds must select substantially different building ids, and
  the selected ids' distribution must be consistent with uniform selection over the frame.
- **Without replacement**: no repeated `source_ids`.
- Frame C's points fall **inside** the cell their flat index names — the test that catches an
  off-by-one in the index↔(row, col) conversion and sampling in the wrong CRS. Note the grid's
  origin is `(x_min, y_max)` = (661900, 4003500) with **`y_min` = 3952100** and rows running
  **downward** from `y_max`; the conversion is tested at the first and last row explicitly.
- Same seed reproduces identical points bit-for-bit; the digest changes when any point changes.

**Verification:** `pytest v2/tests/test_frames.py -v`, then build both artifacts and record digests.

### T3 — `v2/locfinder/measure/comparator.py`

**Depends on:** T2. **The task with the real risk in it.**

Design §2 exactly, plus §7's bound bookkeeping.

```python
@dataclass(frozen=True)
class PointResult:
    point_xy: tuple[float, float]
    objective1_min_time_s: float | None        # min over destinations of TIME
    objective2_cost_path_time_s: float | None  # time along the COST-nearest path
    float_surface_s: float | None
    encoded_surface_s: float | None
    independent_engine_s: float | None         # Valhalla, objective-2 analogue
    product_outcome: Outcome                   # PASS | FAIL | UNKNOWN
    product_reason: Reason
    comparator_status: Reason
    comparator_bound_kind: str                 # "unbounded" | "horizon" | "none"
    comparator_bound_s: float | None
    comparator_termination: str                # "exhausted" | "cutoff" | "error"
    independent_status: Reason
    independent_horizon_s: float | None
    origin_access_m: float | None
    diagnostic_memberships: tuple[str, ...]
```

Three things revision 1 left wrong:

**Destination attachment is by coordinate, with the connector modelled.** Revision 1 promised
coordinates and admitted snapping. Measured: **549 of 550** groceries lie within the 300 m cap, with
nearest-node distance **median 28.07 m, p90 45.71 m, maximum 478.66 m** — at 1.26 m/s that is 37 s at
p90 and 380 s at the maximum, enough to change which destination wins. So each destination attaches
at its nearest **position on the graph**, which may be a point along an edge; the partial edge is
traversed at its own speed; the residual straight line is charged at the access speed and capped at
`poi_snap_max_m` = 300 m; and the one over-cap destination is **excluded by identity in the run
manifest**.

**Objective 1 is computed from a pre-collapse time projection.** `graph_to_cost_time_csr()` keeps
the cost-minimum parallel edge and its time, so its `time_csr` answers the wrong question —
executed: parallel edges (time 1, cost 100) and (time 10, cost 10) give a true minimum of 1 and a
`time_csr` answer of **10**. Objective 1 is projected from the multigraph **before** any collapse,
and objective 2 reconstructs the cost-selected path and sums its time.

**Bound metadata is retained, so `NO_PATH` is earned and bounded failures are not discarded.** A
bounded search may not report `NO_PATH` (`status.py` requires keyword-only `search_bounded`). But a
search exhausted through *H* that reached nothing **does** establish failure for *T* ≤ *H*, so the
verdict uses the sound lower bound rather than routing everything to unknown.

**Tests.** Each is a constructed graph, because every §7 branch can be produced on demand there and
cannot be guaranteed on real data:

- **The parallel-edge counterexample above**, which revision 1's "two objectives pick different
  destinations" test would have passed while the implementation was wrong.
- A destination **midway along an edge**; two destinations with **different connector lengths**; the
  **over-cap rejected** destination; and origin and destination on the **same edge**, where the route
  is the partial traversal and not a detour via either node.
- The **one-way** case where origin→destination is routable and the reverse is not, pinning direction.
- The access cap boundary at `max_access_m` either side.
- **Every cell of §7's three-column table**, including all three product outcomes and the unknown row.
- **`NO_PATH` refused** when the search was bounded; and a bounded-but-exhausted search **scored as a
  known failure** for *T* ≤ *H* rather than as unknown.

**Verification:** `pytest v2/tests/test_comparator.py -v`.

### T4 — `v2/locfinder/measure/diagnostics.py`

**Depends on:** T2, T3.

Design §4. Four **conditional simple random samples from frame B's population**, each restricted to
its predicate, each reporting its own conditional rate with its own one-sided bound, never pooled.

| diagnostic | predicate | *n* |
|---|---|---|
| A boundary-adjacent | the cell is 4-adjacent to a cell with the opposite **product verdict** at *T* | 150 **per *T*** |
| B within one encoding increment | reported value within 60 s of *T* | 150 **per *T*** |
| D1 off-network | product reason `OFF_NETWORK` | 200 |
| D2 beyond-horizon | product reason `BEYOND_HORIZON` | 200 |

**Tests.** Revision 1 asserted `NODATA` is never "the opposite verdict", which **contradicts the
layer contract**: `BEYOND_HORIZON` is a known FAIL wherever *T* ≤ *H*, and **14 `BEYOND_HORIZON`
cells are 4-adjacent to a passing cell at *T* = 10**. So:

- A is computed from **product verdicts**, and the 14-cell figure at *T* = 10 is reproduced as a
  cross-check.
- `OFF_NETWORK` and product `UNKNOWN` are **not** boundary members.
- 4-adjacency, not 8, on a hand-built raster with a known boundary.
- D1 and D2 are disjoint; membership counts are reported per *T*; the design's building-reason
  figures (**499,009 OK / 3,657 `OFF_NETWORK` / 9,967 `BEYOND_HORIZON`**) are reproduced.
- A point satisfying several predicates **keeps every membership** through routing deduplication.
- The conditional draw is uniform over the predicate's members and without replacement.

**Verification:** `pytest v2/tests/test_diagnostics.py -v`, plus a membership table per *T*.

### T5 — the run manifest and persistence

**Depends on:** T2, T3, T4.

Design §11. Frame digests identify *points*, not the instrument, so the manifest additionally
records digests of the **float raster, encoded raster, status raster, prepared graph and destination
list**; the excluded destination's identity; every seed; code, profile and grid versions; and per
point all of `PointResult`.

**Tests.** The report is **recomputable from saved outputs alone** — a test regenerates every number
in T7's report from the persisted rows and asserts equality. A manifest missing any required digest
is an error, not a warning.

### T6 — fixtures, development sample, freeze, certification

**Depends on:** T1–T5.

Design §10, in four steps that may not be reordered:

1. **Fixtures.** Every §7 branch exercised on constructed graphs (T3). Branch coverage is **never** a
   criterion on real data: genuine `NO_PATH` need not occur at all on the prepared walk graph.
2. **Development sample**, own seed, **excluded from certification**. Used for shakedown, timing and
   every outcome-driven fix. Success is **complete records** — each value a valid number or an
   explicit reason-coded absence — not branch coverage, because `OFF_NETWORK` legitimately has no
   comparator time.
3. **Freeze** the product, comparator, frames, allocations, thresholds and analysis.
4. **Certification**: frames B and C at *n* = 500 each, diagnostics 150 per threshold for A and B and
   200 each for D1 and D2 — **2,600 origins** before deduplication. Run **once**. After the freeze no
   certification outcome may change anything; if something must change, the result is void, the
   change is logged in the design, and a fresh sample is drawn.

**Compute.** Revision 1 estimated 1–3 s per unbounded Dijkstra and was **40× pessimistic** — measured
**0.057–0.059 s** — so it then used that false premise to authorise an E2 subsample. **E2 is
collected in full.** The remaining unknown is the end-to-end cost including graph preparation,
attachment, the second objective, cost-path reconstruction, and 2,600 × 549 ≈ **1.43 M** Valhalla
pairs. Step 2 **benchmarks the complete comparator** and reports it; no design change may be
justified by computation before that measurement exists.

### T7 — the report

**Depends on:** T6.

`docs/experiments/s3-walk-grocery-measurement.md`:

- E1a and E1b per frame per *T*, point estimate and one-sided 95% exact upper bound, with the
  **tolerated failure count** stated alongside so a near-miss is legible.
- The §8 verdict per combination — PASS / FAIL / INCONCLUSIVE — with all 16 decisions shown and
  **none averaged**, and an explicit note that these are **not** simultaneous 95% bounds.
- The unknown bucket **bounded both ways**, with product reasons retained, and INCONCLUSIVE declared
  where the bounds straddle a threshold.
- The **paired selection gap** (objective 2 − objective 1) as its own signed distribution, since it
  is inside E1 by construction and must be visible rather than exempted.
- E2 as signed median and IQR with a point-bootstrap interval, plus the share exceeding one encoding
  increment, paired **objective 2 against objective 2**.
- Each diagnostic's conditional rate and bound, against the frame-B rate, with design §4's
  factor-of-two **effect-size criterion** applied.
- The full run manifest.
- Zero-failure results as **"0 observed, 95% upper bound x%"**, never "0%".

**Acceptance-boundary tests**, which revision 1 had none of: the verdict function is tested at
exactly the threshold, immediately either side, and under direction-specific unknown bounds.

**What the report may not say:** that the *layer set* is construction-verified (one mode); that
building *service* is established (frame B now charges the origin connector and T3 charges the
destination connector, which is a real advance over the pass-14 H2 nearest-node proxy, but the frame
is still structures); that real-world accuracy is supported (E3); or anything containing the word
"household".

### T8 — E3 ingestion and scoring

**Depends on:** T1.

Revision 1 assigned the journeys to the owner and stopped, which left the design's falsification
rule unimplemented. This task builds the small piece that makes the result mechanical:

- A journey record: origin, destination, mode, departure, observed duration, the product's reported
  time, and notes.
- `score_e3(journeys)` implementing design §3 exactly: `failed` if **any** journey exceeds its
  reported time by more than a factor of 1.5 **and** by more than 5 minutes, or if the median signed
  difference exceeds 25% of the median reported time; otherwise **UNVERIFIED**, never "supported".

**Tests.** Both limbs of the conjunction independently — a journey 1.6× over but only 3 minutes over
does **not** fail, and one 6 minutes over at 1.2× does **not** fail; the median limb at either side
of 25%; an empty set returns UNVERIFIED; and an **unwalked** planned journey leaves UNVERIFIED and is
never scored as agreement.

### T9 — the grid comparison (S3.1)

**Depends on:** T3, T6.

Re-evaluate the **same frame C points** against the 200 m grid. Cheap once T3 exists, and the reason
frame C samples ground rather than cell centres. The stage context also requires **matched
destination entrances**, so the comparison holds the destination attachment of T3 fixed and varies
only the grid — otherwise resolution, alignment and attachment move together, which is the confound
S3.1 exists to avoid.

### T10 — the encoding freeze (S3.5)

**Depends on:** T6, T7.

The maximum duration is decided (design §9): **120 minutes, whole minutes, codes 121–254 a versioned
status plane**. No surface rebuild is required, since the walk surface's finite maximum is
119.99998 minutes.

- The **writer, exporter and browser decoder change together**. `v2/spikes/g3-render/worker.js:144`
  recognises exactly one sentinel today, which is why the browser cannot separate **57,541
  off-network cells from 16,209 beyond-horizon ones**; it must recognise the status plane.
- **Test actual browser decoding.** A Python round-trip test cannot protect the browser.
- **Version the format.** Legacy codes 251–254 are valid minute values in artifacts on disk; they are
  rebuilt or namespaced, never reinterpreted.
- Categorical status codes must **never be interpolated** during reprojection.
- Measure **compressed transfer size and phone decode latency** per candidate, not size alone — a
  requirement revision 1 dropped. Reference: the current Triangle walk layer is 174 KB deflated at
  uint8 whole minutes.
- **Recompute diagnostic membership**, because A is defined on product verdicts and B on one encoding
  increment, so both move when the encoding does. Then re-run T7's E1 arithmetic. A quantization
  change can be re-derived from retained float values; a horizon change could not, which is why the
  decision was taken before measuring.

### T11 — the extraction-truncation diagnostic

**Depends on:** T3.

The layer contract assigns this to S3 and revision 1 had no task for it. A route whose true path
leaves the routing bbox is truncated, and the contract declines to give it a per-cell status because
the pipeline discards the path's node sequence — so it is a **build-time diagnostic**: the share of
comparator routes whose path touches the routing-buffer boundary, reported as a bound on how much of
the measurement could be affected. The comparator retains paths, so this is nearly free here and
impossible later.

---

## 3. What would invalidate this plan

- **The development sample shows failure rates near 0.5 rather than near 0.** The allocations are
  sized for small rates; at *p* near 0.5 the bound is far wider than the thresholds. The design's
  instruction is that the result **says so**. Re-sizing is a design change with a change-log row, and
  it voids the certification sample.
- **The end-to-end benchmark shows E2 is infeasible in full.** Then the subsample is a design
  amendment with its size, frames, diagnostic coverage and interval procedure fixed **before** it is
  drawn — not a run-time decision.
- **The measured frame-B population differs from 512,633.** Verified equal today; if a re-acquisition
  changes it, the discrepancy is the finding.
- **The comparator and the float surface disagree pervasively rather than at the margins.** That is
  E1 doing its job: a defect in the pipeline, not the measurement — and S3 stops while S2 reopens.
- **Coordinate attachment proves intractable on the real graph** (for instance partial-edge traversal
  interacting badly with the one-way mask). Then the design's decision 2 is revisited explicitly,
  rather than quietly falling back to snapped nodes.

## 4. What this plan does not do

- It does not touch the shipped pipeline, except T10's encoding freeze, which is scheduled after the
  measurement and changes writer, exporter and decoder together.
- It does not change a number in the design. Revision 1 claimed this and broke it twice — exempting
  the selection gap that §2 puts inside E1, and authorising an E2 subsample. Both are now the
  design's, not the plan's. **Any number this plan appears to add is a defect in this plan.**
- It does not schedule the G4 device matrix, the G3 phone render or the G5a household sessions. Those
  are the owner's and are tracked in the phase-1 plan.
