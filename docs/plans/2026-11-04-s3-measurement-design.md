# S3 measurement design — predeclared

**Status:** design, predeclared before any sampling. Nothing here reports a result.

**Revision 3, 2026-11-04**, after Codex pass 15 found eight High and ten Medium defects in revision 2
and in the execution plan written against it. What changed, and why, is in §12 — because a
predeclared design that is quietly edited is not predeclared. Revision 2's own change log is kept
there too.

Revision 3 is not a tightening of revision 2. It **removes a whole subsystem** — the design effect,
the 2 km blocks and the block pooling rule — because pass 15 established that it did not belong:

> "For the declared finite-population SRS, spatially adjacent outcomes do not by themselves turn the
> sample into a cluster sample."

Revision 2's acceptance gate was also **unreachable**: at *n* = 400 with zero observed failures and
the predeclared DEFF = 2.0 fallback, the one-sided 95% bound is 1.4867% against an E1b threshold of
1.0%. Perfect observed agreement could not certify the product. And the DEFF estimator could not run
in the first place — at *n* = 400 only 2.8 blocks (frame B) or 0.1 blocks (frame C) reach the
required five sampled points, and 893 of 1,000 seeded draws produce no qualifying block at all. The
fallback was the only reachable path and the only reachable path failed.

**Four owner decisions are recorded here**, taken 2026-11-04 before any sampling:

1. **Inference is finite-population SRS.** No design effect, no blocks, no pooling. §§5–6.
2. **The comparator attaches destinations by coordinate with a modelled connector**, rather than
   declaring a snapped-node comparator and narrowing the claim. §2.
3. **Diagnostic A is defined on product verdicts**, so `BEYOND_HORIZON` is a genuine opposite verdict
   wherever *T* ≤ *H*, per the layer contract. §4.
4. **The published maximum duration is 120 minutes at whole-minute resolution**, with codes 121–254
   reserved for a **versioned** status plane. §9.

---

## 1. Two frames, because there are two populations

Revision 1 had one frame — buildings — and reported both a building rate and a cell rate from it.
That is not possible (pass-14 H6): **a cell containing no buildings has zero probability of
selection**, and a cell containing a hundred buildings has a hundred times the chance of a cell
containing one. Swapping `N_h` from buildings to cells does not repair either problem.

So there are two frames and two estimands, and they are never computed from each other's sample.

**Frame B — structures.** The S2.4 set (`v2/data/triangle/overture_buildings_accepted.parquet`;
**522,160 rows measured**, of which **512,633 have a projected centroid inside the 100 m grid** —
both figures verified against the artifact, not assumed). One point per building centroid, computed
**projected** (EPSG:32617) and not in the geographic CRS. **A building frame, not a household
frame**: Overture carries no reliable residential flag here, so a shed, a barn, a warehouse and each
of a hospital campus's many structures count once each. Frame B estimates a property of the
**structure-centroid population** and nothing else, and the word "household" appears nowhere in any
S3 output.

**Frame C — ground area.** All 330,502 cells of the 100 m grid (643 × 514, origin `x_min` 661900 /
`y_max` 4003500, EPSG:32617), sampled by simple random sampling without replacement, then **one
uniformly random point inside each sampled cell**.

**What frame C estimates, stated precisely.** Uniform cell selection followed by uniform
within-cell sampling is unbiased for the **average disagreement probability over ground area** —
equivalently, the mean within-cell disagreement rate across equal-area cells. It is **not** an
estimate of "the fraction of cells containing any error", and revision 2's wording invited that
reading. No sampling change follows; the estimand is named correctly instead.

**Neither frame is evaluated at cell centres.** `TRIANGLE.grid()` is **not nested** across
resolutions — 100 m is 643 × 514 at origin 661900/4003500; 200 m is 322 × 258 at origin
661800/4003600, offset by −100 m east and +100 m north — so sampling each grid at its own centres
would confound resolution, alignment and which piece of ground is being asked about. Frame C's
points are properties of the ground, so the same point set can be evaluated against every candidate
grid and encoding.

**Both frames are frozen artifacts with digests**, for the reason S2.5 recorded: file order is not
stable across downloads, and "the first *N*" silently changed which POIs an experiment used.

---

## 2. The comparator, specified before the estimands

Revision 1 said "the engine's own answer at that coordinate", which is not executable (pass-14 M5).
Revision 2 specified most of it and left three things unresolved that pass 15 found: the destination
attachment contradicted itself, the time-minimum objective would have inherited a cost-based edge
collapse, and the independent engine had no declared objective.

| | |
|---|---|
| **origin** | the sampled point (a building centroid, or a random point in a sampled cell) |
| **origin attachment** | the access leg is charged at the layer's own access speed (walk **1.26 m/s**) and capped at `max_access_m` = **200 m**; a point with no network within the cap is a **status**, not a missing value (§7) |
| **destination set** | the 550 grocery places selected by `select_overture(triangle, "grocery")` — **verified at 550, all Point geometries, from 107,484 accepted places** |
| **destination attachment** | **by coordinate, with the connector modelled** — see below |
| **direction** | the product answers "how long to *reach* a destination", so the comparator routes **origin → destination**. The arrival surface is built on the transposed graph; a one-way road can make origin→destination routable while destination→origin is not, so the comparator must not be run in the surface's internal direction |
| **selection objectives** | **two runs**, both retained: **objective 1** `min over destinations of travel time`, and **objective 2** `travel time along the cost-nearest destination's path` |
| **departure/arrival** | walk and bike are time-independent; drive and transit use the fixed arrival datetime in the `SurfaceKey` being tested |

### Destination attachment, which revision 2 contradicted itself about

Revision 2 promised destinations "by their own coordinates, **not** their snapped nodes", and the
execution plan then admitted the destination end still snapped. Measured, that difference is
material: of the 550 groceries, **549 fall within the production 300 m cap**, with nearest-node
distance **median 28.07 m, p90 45.71 m and maximum 478.66 m**. At 1.26 m/s a 46 m connector is 37 s
and a 479 m one is 380 s — enough to change which destination wins and to cross a threshold. The
omission is also **not** uniformly one-sided: different node attachments can change reachability and
route choice, not merely add time.

So, predeclared:

- Each destination attaches at its **nearest position on the graph**, which may be a point **along an
  edge** rather than a node; the partial edge is traversed at the edge's own speed.
- The residual straight-line connector from the place to that position is charged at the **access
  speed** and capped at `poi_snap_max_m` = **300 m**.
- A destination beyond the cap is **excluded from the destination set, by identity, in the run
  manifest**. Exactly one is expected (the 478.66 m case); if more appear, the count is reported.
- Where origin and destination attach to the **same edge**, the route is the partial traversal
  between them, not a detour via either node.

### Objective 1 may not be computed from the cost-collapsed graph

`traveltime/csr.py`'s `graph_to_cost_time_csr()` keeps the **cost-minimum** parallel edge and
carries that edge's time, so its `time_csr` cannot answer a minimum-time question. Executed
counterexample: parallel edges (time 1, cost 100) and (time 10, cost 10) give a true minimum-time
route of 1 and a `time_csr` answer of **10**.

This is the same defect class as S2.3's class separation: **project before the collapse, or the
alternative is already lost.** So objective 1 is computed on a **time-minimum projection built from
the multigraph before any cost collapse**, and objective 2 is computed by **reconstructing the
cost-selected path and summing its time**. Neither is read off the other's matrix.

### The selection gap is inside E1, and is reported

E1 compares the encoded surface against **objective 1**. The difference between objective 2 and
objective 1 — the pass-8 H2 bound — therefore **contributes to E1 by construction**. Revision 2's
execution plan claimed it "must not be charged to the pipeline"; retaining objective 2 does not
remove it from the gate. Predeclared instead: the **paired selection gap** `objective 2 − objective
1` is reported as its own signed distribution alongside E1, so the share of E1 attributable to
cost-based selection is visible rather than asserted away. It is not subtracted from E1.

### The independent engine's objective

A Valhalla matrix request returns, per pair, the time **along its own cost-optimal route**. It does
not return a time-minimal route and cannot be asked for one. So E2's independent value is
`min over destinations of (time along Valhalla's cost-optimal path)`, which is the analogue of
**objective 2**, and E2 pairs it against **our objective 2** — never against objective 1. Calling
both "the same comparator rules" without this would compare two different quantities.

Each engine carries **its own horizon**, because the own-graph layers were built to 120 minutes and
the Valhalla reference layers to 60; comparing them without carrying each horizon reads one
engine's missing data as the other's disagreement.

---

## 3. Estimands

Three, with different units and different standards of evidence. They are never combined.

### E1 — construction fidelity (the PASS/FAIL gate)

For a mode *m* and published threshold *T*:

> **the proportion of sampled points at which the product's verdict at *T* differs from the
> comparator's verdict at the same point.**

Split, because the two directions are not equally harmful and S0's H2 bracket predicts only one:

- **E1a false exclusion** — product says *fail*, comparator says *pass*. A home never shown.
- **E1b false inclusion** — product says *pass*, comparator says *fail*. A wasted viewing.

Estimated **separately on each frame**: on frame B as a share of structures, on frame C as a share
of ground area. This is ours to fix — same engine both sides, so a difference is a defect. E1
against an independently implemented path through the same engine is construction testing, not a
validity claim, and conflating the two is the error the phase-1 plan §0 records as withdrawn once
already.

### E2 — engine disagreement (descriptive)

> **d = t_independent − t_float**, in seconds, at the same point with matched arrival time,

where `t_float` is our pre-encoding reconstruction and `t_independent` the other engine's answer
under §2's rules, **both at objective 2**. Signed, reported as median and IQR with a bootstrap
percentile interval, plus the share with |d| greater than one encoding increment.

**Five** paired values are retained per point — objective 1, objective 2, float surface, encoded
surface, independent engine — so that encoding, snapping, entrance choice, destination selection and
route choice cannot be absorbed into one unattributable "model error".

### E3 — real-world accuracy (supported / **failed** / UNVERIFIED)

> **the signed difference between a hand-timed journey and the product's reported time.**

5–8 owner-chosen journeys cannot establish a population rate: they are a convenience sample, so the
binomial bound does not even apply to them, and with 8 observations and no discrepancy the one-sided
95% exact bound would in any case be **31.2344%**. The population-rate claim is therefore
**UNVERIFIED** and the published label says so.

**But it can still fail, and revision 1 made that impossible** (pass-14 M6):

> **E3 returns `failed` if any single journey's observed time exceeds the product's reported time by
> more than a factor of 1.5 **and** by more than 5 minutes, or if the median signed difference
> across the journeys taken exceeds 25% of the median reported time.**

`failed` is a statement about the product, not about a rate. Absent a failure the outcome is
UNVERIFIED — never "supported". A planned journey that was not walked leaves E3 UNVERIFIED and is
**never** read as absence of disagreement; that is the escape hatch S3.4 exists to close.

---

## 4. Samples

**Frame B — structures.** Simple random sample without replacement, ***n* = 500**.
**Frame C — ground area.** Simple random sample without replacement, ***n* = 500**.

*n* = 500 is chosen by **failure tolerance**, not by a zero-event bound, because the zero-event
figure hides what happens when a single failure appears (§6).

### Diagnostics, which are never pooled into either estimate

Revision 1 called these strata and planned to combine them with `N_h / n_h` weights. They are not a
partition (pass-14 H5): a point can be boundary-adjacent *and* within one encoding increment *and*
in a population sample simultaneously, so pooling counts the same population mass several times.

Revision 2 kept them as diagnostics but never said **what population they are drawn from**, and
treated A and B as though a single allocation covered all thresholds when their predicates are
threshold-specific (pass-15 H10). Predeclared now:

- **Every diagnostic is a conditional simple random sample from frame B's population** — the
  512,633 structure centroids — restricted to its predicate. Frame B is the population whose service
  the product exists to describe, and all four predicates are evaluable at a structure's location.
- **No weights are required** for a conditional SRS, but a **defined conditional sampling
  distribution** is, which is what the line above supplies.
- Each diagnostic reports its **own conditional rate with its own one-sided exact bound**, against
  the matching frame-B population rate. It is never added to a total.
- **A and B are drawn per threshold.** With four published thresholds that is 150 × 4 = 600 draws
  each.
- A point may satisfy several predicates; **every membership is recorded per point** and a point is
  routed once per diagnostic it belongs to. Deduplication of routing work must not lose membership.

| diagnostic | predicate (per threshold where noted) | *n* |
|---|---|---|
| **A — boundary-adjacent** | the point's cell is 4-adjacent to a cell with the opposite **product verdict** at *T* | 150 **per *T*** |
| **B — within one encoding increment** | the product's reported value is within one encoding step (60 s) of *T* | 150 **per *T*** |
| **D1 — off-network** | the product's reason is `OFF_NETWORK` | 200 |
| **D2 — beyond-horizon** | the product's reason is `BEYOND_HORIZON` | 200 |

**Diagnostic A is defined on product verdicts** (owner decision 3). Revision 2 was internally
inconsistent here: its geometric definition said "opposite verdict" while its explanation said A
"requires a value", and `NODATA` has no value. The layer contract settles it — `BEYOND_HORIZON` is a
**known FAIL** wherever *T* ≤ *H* — so a `BEYOND_HORIZON` cell adjacent to a passing cell **is** a
genuine verdict boundary. Measured on the shipped raster: **14 such cells at *T* = 10 minutes**.
`OFF_NETWORK` and anything the product reports `UNKNOWN` are **not** opposite verdicts and are not
boundary members; D1 and the §7 unknown accounting cover them.

**"Materially worse" is given an effect size.** A diagnostic is reported as materially worse than
the population when its point estimate exceeds the matching frame-B point estimate by **at least a
factor of 2** and its one-sided lower bound exceeds the population point estimate. Otherwise it is
reported as not distinguishable at this allocation. Revision 2 asked the question without a
criterion, which makes any answer defensible after the fact.

**Total routing budget:** 500 + 500 population points, 600 + 600 diagnostic A/B points, 200 + 200
for D1/D2 = **2,600 origins** before deduplication. Revision 2's execution plan said 1,500, which
was wrong by the per-threshold factor.

---

## 5. No weights, and no design effect

Both population samples are simple random samples, so they are **self-weighting**: the estimate is
the sample proportion. The diagnostics are conditional SRSs and carry no weights either.

**The design effect is removed entirely** (owner decision 1). Revision 2 imported cluster-sampling
machinery for a sample that was never drawn as a cluster sample. For an SRS of points from a finite
frame, the sampling variance of the estimated proportion is `p(1−p)/n · (1 − n/N)` **however
correlated neighbouring ground happens to be** — clustering inflates variance when the *design*
clusters, as when blocks are sampled and then every point within them. Points here are drawn
independently.

Three consequences, all improvements:

- There is **no DEFF estimator** to specify, so revision 2's unspecified weights, denominator,
  unequal-block-size treatment and all-failures case (pass-15 M4) all disappear.
- There is **no 2 km block grid** and **no ≥5-points-per-block pooling rule**, so the rule that could
  not be satisfied, and the single-block degeneracy that the execution plan's termination fix would
  have introduced — the same dataset in all 2,000 bootstrap replicates, reporting a zero-width
  interval for an uncertain statistic (pass-15 H3) — are both gone.
- The acceptance gate becomes **reachable**, which it was not (§8).

**If a superpopulation claim is ever wanted** — "the rate at which a pipeline of this kind errs",
rather than the rate over these 512,633 structures — that needs a stated and validated spatial
model, not an effective-sample-size adjustment. It is explicitly out of scope, and no S3 output may
be worded as one.

**Spatial structure is still examined**, just not inside the gate: diagnostic A is the geometric
question, and any further spatial exploration is reported separately from the certification result.

---

## 6. Intervals, with one convention

**One-sided 95% exact (Clopper–Pearson) upper bounds for failure rates**, on the **actual** sample
size, throughout. The quantity of interest is "how bad could this be"; the bound is exact; and it
behaves at zero observed failures, which is the case the design exists to handle honestly.

Because the frames are finite and sampling is without replacement, the binomial bound is
**conservative** — the hypergeometric bound would be slightly tighter. The finite-population
correction is negligible here (`1 − n/N = 0.99902` at *n* = 500, *N* = 512,633) and the conservative
direction is the safe one, so Clopper–Pearson is used and the conservatism is stated rather than
claimed as precision.

**The bound must never be reported as exact after any adjustment.** Revision 2's "exact
Clopper–Pearson on *n*/DEFF" was not an exact procedure: dividing the denominator by an estimated
variance inflation destroys the binomial coverage guarantee, and revision 2 never said whether the
numerator was retained or scaled. With the design effect removed, the procedure is exact again.

### What each allocation tolerates

This is the planning table, because the zero-event bound alone hides the cliff:

| *n* | *k*=0 | *k*=1 | *k*=2 | *k*=3 | E1b ≤ 1.0% tolerates | E1a ≤ 2.0% tolerates |
|---|---|---|---|---|---|---|
| 400 | 0.7461% | 1.1804% | 1.5655% | 1.9269% | **0 failures** | 3 |
| 473 | 0.6313% | 0.9990% | 1.3250% | 1.6310% | 1 (knife-edge) | 4 |
| **500** | **0.5974%** | **0.9452%** | 1.2538% | 1.5434% | **1 failure** | **4** |
| 628 | 0.4759% | 0.7531% | 0.9991% | 1.2300% | 2 | 6 |

Revision 2's *n* = 400 tolerated **exactly zero** false inclusions even without the design effect:
one in four hundred fails the gate. *n* = 473 is the minimum that survives one, at 0.9990% — too
close to the threshold to be a defensible predeclaration. ***n* = 500 survives one false inclusion
at 0.9452%**, with margin, and is the allocation chosen.

A zero-failure result is reported as **"0 observed, 95% upper bound x%"** and never as "0%".

**E2's interval** is a bootstrap percentile interval over the SRS — resampling **points**, 2,000
replicates, seeded and recorded. There is no block bootstrap, for the reason in §5.

---

## 7. Every outcome has a verdict

Revision 1 said missing data would be "reported with counts and treated as informative", which
leaves the arithmetic undefined. Revision 2 supplied a table with **two** product columns — but the
product has **three** outcomes: `evaluate()` returns PASS, FAIL **and UNKNOWN**, and an off-network
surface at 250 m access returns `UNKNOWN` at *T* = 10, which is exactly the D1 population
(pass-15 H8).

### What the comparator must retain

A bounded search cannot prove non-existence, because exhaustiveness is a property of the
**invocation**, not of the engine: `status.py` requires a keyword-only `search_bounded` precisely
because a bounded call on our own graph returns `inf` for nodes that are merely distant, and reading
exhaustiveness off the engine name once labelled a node 210 s away as having no route at all
(pass-8 H1). So the comparator **may not report `NO_PATH` unless its search was unbounded.**

But routing *every* bounded no-result to the unknown bucket understates the **known** failure count
(pass-15 M9): a search that exhausts everything through horizon *H* and reaches no destination
**does** establish failure for every *T* ≤ *H*, without proving `NO_PATH`. So each comparator result
retains **bound type, bound value and termination reason**, and the verdict uses the **sound lower
bound** it implies:

- exhausted through *H* with nothing reached, *T* ≤ *H* → **comparator fail**, known.
- bounded with no sound lower bound above *T* → **unknown**.
- unbounded and exhausted → **`NO_PATH`**, definitive.

### The table, completed for all three product outcomes

| comparator outcome | product PASS | product FAIL | product UNKNOWN |
|---|---|---|---|
| route found, ≤ *T* | agree | **E1a** false exclusion | **unknown** bucket |
| route found, > *T* | **E1b** false inclusion | agree | **unknown** bucket |
| **definitive no path** (unbounded, exhausted) | **E1b** — a journey promised that does not exist | agree | **unknown** bucket |
| **sound lower bound > *T*** (bounded, exhausted through *H*) | **E1b** | agree | **unknown** bucket |
| no network within `max_access_m` of the point | **E1b** | agree | **unknown** bucket |
| **unknown** (timeout, engine error, snap failure, no sound bound) | **unknown** bucket | **unknown** bucket | **unknown** bucket |

A product `UNKNOWN` is never scored as agreement and never as a failure; it enters the unknown
bucket with its **product reason retained**, because `BEYOND_HORIZON` with *T* > *H* is answerable
by searching further (contract §2) while `OFF_NETWORK` is not, and the two have different remedies.

The unknown bucket is **bounded both ways**, never dropped and never assumed benign: the reported
result gives each rate with every unknown counted as agreement and again with every unknown counted
as an error. If those two bounds straddle an acceptance threshold in §8, the result is
**INCONCLUSIVE** and the gate does not pass.

---

## 8. The acceptance rule, predeclared

For each published mode *m* and threshold *T* ∈ {10, 15, 25, 45} minutes, on **each** frame:

- **PASS** if the one-sided 95% upper bound on **E1a** is **≤ 2.0%** and on **E1b** is **≤ 1.0%**.
- **FAIL** if the point estimate of either exceeds its threshold.
- **INCONCLUSIVE** otherwise — including whenever the unknown-bucket bounds of §7 straddle a
  threshold. Inconclusive is not a pass, and shipping on one is an explicit owner decision.

At *n* = 500 this means, concretely: **E1b admits at most one observed false inclusion and E1a at
most four.** That consequence is stated here, before measurement, because an allocation whose
tolerance is discovered afterwards is an allocation chosen afterwards.

**E1b is held to the tighter bound** because a false inclusion is a claim the product made and a
false exclusion is a home it failed to mention; both are harmful, and only the first is a statement
we would have to defend. The thresholds are judgements, recorded before measurement, and are the
owner's to move — but not after seeing the result.

**Every published mode and threshold must pass on both frames** for a layer to be described as
construction-verified. A single failing combination is reported as such rather than averaged away.

**On multiplicity.** The gate is a **conjunction**: if any component requirement is false, passing
globally requires falsely passing that component, so no multiplicity correction is needed for the
single global claim. But the sixteen individual bounds are **not** simultaneous 95% confidence
bounds, and no S3 output may present them as such.

**Published thresholds.** T ∈ {10, 15, 25, 45} minutes, matching every S2 figure on record so the
S3 result is comparable with them. There is no published-threshold registry in `v2/locfinder/`
today; this is that declaration, and it is the owner's to change before measurement.

---

## 9. The encoding, decided

**Owner decision 4, taken 2026-11-04: the published maximum duration is 120 minutes at whole-minute
resolution, with codes 121–254 reserved for a versioned status plane.**

The premise this decision was originally framed on was **false**, and checking it changed the
decision. The phase-1 plan says a cell at the horizon "is today indistinguishable from a genuine
120-minute answer". Measured on the shipped layer: **234 cells encode to exactly 120 minutes and all
234 carry reason `OK`**, while every censored cell is `NODATA` with reason `BEYOND_HORIZON` (16,209)
or `OFF_NETWORK` (57,541). In the **raster pair** a genuine 120 is already distinguishable.

The ambiguity is in the **single-raster browser path**: `v2/spikes/g3-render/worker.js:144`
recognises one sentinel, so the browser cannot separate **57,541 off-network cells from 16,209
beyond-horizon ones** — two orders of magnitude larger than the 234-cell question, and the
distinction that decides whether the product says "no road near here" or offers to search further.

Why 120 and whole minutes:

- The walk surface's finite maximum is **7,199.999 s = 119.99998 minutes** — censored exactly at the
  7,200 s cutoff — so 120 covers 100% of finite values and **no rebuild is required**. Raising the
  maximum would require one, because a horizon-censored surface cannot have times recovered from
  `inf`.
- The distribution leaves no case for more: 44.0% of finite cells are within 30 minutes, 76.6%
  within 60, 92.3% within 90.
- It leaves **134 spare codes** (121–254) for the full `Reason` taxonomy, against 14 at a 240-minute
  maximum and none at 254.
- The built horizon *H* is **not** a product ceiling: the contract's `needs_recomputation` makes a
  threshold past *H* answerable by a fresh search, and raising a threshold does not invalidate cells
  that already passed.

**The format version is not optional.** Legacy codes 251–254 are valid minute values in artifacts
already on disk, so a sentinel scheme that reinterprets them would corrupt them. The format carries
a version; existing artifacts are rebuilt or namespaced, never reinterpreted.

**Scope limit.** S3.5 says the maximum "follows from S0.4's transit horizon and the relaxation
limits", and **S0.4's window is not yet fixed to a number** — there is no Triangle transit layer.
This decision therefore covers the walk layer S3 measures, and the version field exists so a later,
longer transit window widens the format without reinterpreting existing codes.

**Changing the encoding invalidates sample membership.** Diagnostic B is defined by one encoding
increment and diagnostic A by product verdicts, so both must be **recomputed** whenever the shipped
surface or its encoding changes. A quantization change and a horizon change are not equivalent: the
first can be re-derived from the retained float values, the second requires rebuilding the surface.

---

## 10. Development and certification are separate samples

Revision 2 referred to "the pilot" in two places while defining no pilot allocation. The execution
plan proposed a 50-point **prefix** of the certification sample, arguing that a prefix avoids a
two-stage design. That argument was wrong in both directions (pass-15 M13): an independent debugging
sample is not automatically an invalid estimator, and a prefix **remains an interim look**. What
matters is not how the points were drawn but whether their outcomes guide changes.

Predeclared instead:

1. **Harness validation runs on constructed fixtures.** Every branch of §7's table is exercised by
   synthetic graphs, where each branch can be produced on demand. A random sample cannot guarantee
   branch coverage — genuine `NO_PATH` need not occur at all on the prepared walk graph — so branch
   coverage is never a criterion on real data.
2. **A separate development sample**, drawn under its own seed and **excluded from certification**,
   is used for every outcome-driven fix, shakedown and timing measurement.
3. **Then the instrument freezes** — product, comparator, frames, allocations, thresholds and
   analysis — and the certification samples of §4 are drawn and run **once**.
4. **After the freeze, no outcome of the certification sample may change** the product, the
   comparator, the sample, the thresholds or the analysis. If something must change, the
   certification result is void, the change is recorded here, and a fresh sample is drawn. A change
   log records adaptation; it does not restore coverage.

The real-data shakedown's success criterion is **complete records** — every value either a valid
number or an explicit reason-coded absence — not universal branch coverage. `OFF_NETWORK`
legitimately has no comparator time, so "all paired values populated" was self-contradictory.

---

## 11. What must exist before the certification run

- [ ] Frame B and frame C artifacts with digests (§1).
- [ ] The comparator, implementing §2 exactly — coordinate attachment with modelled connectors, both
      objectives, objective 1 from a pre-collapse time projection, retained bound metadata (§7).
- [ ] Diagnostic membership on the shipped surface, **per threshold**, under §4's conditional
      sampling.
- [ ] The exact-interval and bootstrap primitives of §6, tested at **non-zero** failure counts and
      not only at zero.
- [ ] A **run manifest** identifying every input and the whole comparator configuration: digests of
      the float raster, the encoded raster, the status raster, the prepared graph and the destination
      list; the excluded destination's identity; seeds; code, profile and grid versions; and per
      point the product, own-comparator and independent-engine statuses, bounds, objectives and
      diagnostic memberships. Frame digests identify *points*, not the instrument. The report must be
      recomputable from saved outputs, and that recomputation is tested.
- [x] A decision on the published **maximum duration** — §9.

---

## 12. Change log

Recorded rather than silently edited, because the point of predeclaring is that changes are visible.

### Revision 3, after Codex pass 15 (8 High, 10 Medium)

| pass-15 | revision 2 said | revision 3 says |
|---|---|---|
| **H1** | "exact Clopper–Pearson" on *n*/DEFF | that is not an exact procedure, and the numerator handling was never specified. **The design effect is removed**; the bound is exact on the actual *n* (§§5–6) |
| **H2** | *n* = 400, E1b ≤ 1.0%, DEFF = 2.0 | **unreachable** — zero failures gives 1.4867%. ***n* = 500** with no DEFF; the gate's failure tolerance is stated in §8 |
| **H3** | ≥5 points per block, pool with the nearest qualifying neighbour | at *n* = 400 almost no block qualifies (893 of 1,000 draws have none), and the plan's single-block fallback would make the bootstrap degenerate. **Blocks and pooling removed**; E2 uses a point bootstrap |
| **M4** | DEFF from between-block variance | never mathematically specified. Moot: removed |
| **H5** | destinations "by their own coordinates, not their snapped nodes" | the plan then snapped them. **Coordinate attachment with a modelled connector**, partial-edge traversal, a capped access leg, and the one over-cap destination excluded by identity (§2) |
| **H6** | one time matrix | `graph_to_cost_time_csr` keeps the cost-minimum parallel edge, so its `time_csr` cannot answer a minimum-time question. **Objective 1 is projected from the multigraph before collapse** (§2) |
| **M7** | the selection gap "must not be charged to the pipeline" | E1 is defined against objective 1, so the gap **is** in E1. It is **reported separately**, not exempted; and E2 pairs objective 2 against Valhalla's cost-optimal time, which is the only thing a matrix returns (§2) |
| **H8** | a verdict table with product PASS and FAIL | the product also returns **UNKNOWN**. The table is completed for all three, with the product reason retained (§7) |
| **M9** | any bounded no-result → unknown | a search exhausted through *H* establishes failure for *T* ≤ *H*. **Bound type, value and termination reason are retained** and a sound lower bound scores a known failure; `NO_PATH` still requires an unbounded search (§7) |
| **H10** | four diagnostics with predicates | no sampling population, and A/B are per-threshold. **Conditional SRS from frame B**, 150 **per threshold**, an effect-size criterion for "materially worse", and a corrected budget of **2,600** origins (§4) |
| **M11** | A is geometric "opposite verdict" but "requires a value" | contradictory. **A is defined on product verdicts**; `BEYOND_HORIZON` is a known FAIL where *T* ≤ *H* (14 such cells at *T* = 10), `OFF_NETWORK` and `UNKNOWN` are not boundary members (§4) |
| **M12, M13** | "the pilot", and a 50-point prefix | branch coverage is impossible on a random sample and a prefix is still an interim look. **Fixtures, then a separate development sample, then a freeze** (§10) |
| **M14** | paired values per sampled point | the plan authorised an E2 subsample on cost grounds. The premise was false — Dijkstra measures **0.057 s**, not 1–3 s — so **E2 is collected in full** |
| **H15** | maximum duration deferred | **decided: 120 minutes, whole minutes, 121–254 a versioned status plane** (§9), after finding the premise behind the question false |
| **M16** | §6's zero-failure table as fixtures | those fixtures pass a wrong implementation: `k/n + (1−k/n)(1−0.05^(1/n))` matches all of them yet gives 0.9943% at *k*=1, *n*=400 against the correct 1.1804% — enough to flip an E1b verdict. **Non-zero fixtures are required**, with a stated rounding tolerance (§11) |
| **M17** | frame digests | identify points, not the instrument. A **full run manifest** is required, and report recomputation is tested (§11) |
| — | frame C "a property of the ground" | named precisely: unbiased for **area-average disagreement**, *not* for the fraction of cells containing any error (§1) |

### Revision 2, after Codex pass 14 (4 High, 3 Medium)

| pass-14 | revision 1 said | revision 2 said |
|---|---|---|
| **H5** | four strata pooled with `N_h / n_h` weights | they overlap, so they are not a partition. Two self-weighting samples estimate the populations; the four are **diagnostics**, never pooled |
| **H6** | one building frame, reporting both building and cell rates | a cell with no buildings has zero selection probability. **Two frames**, each reporting only its own estimand |
| **H7** | "PASS / FAIL", no rule | explicit bounds, an INCONCLUSIVE outcome, and all modes/thresholds/frames must pass |
| **M4** | "Wilson on *n*/DEFF"; DEFF from the pilot | one convention (exact one-sided); fixed 2 km blocks; a predeclared DEFF = 2.0 fallback — **all of which revision 3 removes** |
| **M5** | "the engine's own answer at that coordinate" | a comparator specification and a verdict table for every status |
| **M6** | E3 "UNVERIFIED whatever these journeys show" | unfalsifiable as written; a magnitude-based **falsification rule** |
| **L2** | E2 against reported time in one place, the float surface in another | defined once, against the float surface |

One judgement kept from revision 1: the allocations are sized for **small** rates. At *n* = 500 and a
true rate near 1%, the exact one-sided bound is about 2 points; the familiar "385 for five points"
figure assumes *p* = 0.5 and is the pessimistic bound, not the target. Extrapolating small-rate
expectations from the S0 encoding bracket to the structure and boundary populations is a **planning
assumption**, not evidence: if the development sample shows rates near 0.5 the allocations are
insufficient and the result will say so rather than being reported at a margin it cannot support.
