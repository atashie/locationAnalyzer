# S3 measurement design — predeclared

**Status:** design, predeclared before any sampling. Nothing here reports a result.
**Revision 2, 2026-11-04**, after Codex pass 14 found four High and three Medium defects in
revision 1. What changed, and why, is in §10 — because a predeclared design that is quietly edited
is not predeclared.

The reason for predeclaring is specific. Revision 1 of the *plan* chose "60 cells per side per
threshold" with no estimand, and Codex's arithmetic showed what that buys: with 60 independent
observations and **zero** observed failures the one-sided 95% exact upper bound on the failure rate
is **4.8703%**, not zero. A design chosen after seeing the data can always be the design that
passes.

---

## 1. Two frames, because there are two populations

Revision 1 had one frame — buildings — and reported both a building rate and a cell rate from it.
That is not possible (pass-14 H6): **a cell containing no buildings has zero probability of
selection**, and a cell containing a hundred buildings has a hundred times the chance of a cell
containing one. Swapping `N_h` from buildings to cells does not repair either problem.

So there are two frames and two estimands, and they are never computed from each other's sample.

**Frame B — buildings.** The S2.4 set (`overture_buildings_accepted.parquet`; 522,160 rows,
512,633 with a centroid inside the 100 m grid), one point per building centroid, projected to
EPSG:32617. **A building frame, not a household frame**: Overture carries no reliable residential
flag here, so a shed, a barn, a warehouse and each of a hospital campus's many structures count
once each. Every frame-B estimand is therefore about **structures**, and the word "household"
appears nowhere in the outputs.

**Frame C — cells.** All 330,502 cells of the 100 m grid, sampled by simple random sampling without
replacement. This is the frame for any claim about the published surface as a surface.

**Neither frame is evaluated at cell centres.** `TRIANGLE.grid()` is **not nested** across
resolutions — 100 m has origin 661900/4003500 and is 643 × 514; 200 m has origin 661800/4003600 and
is 322 × 258 — so sampling each grid at its own centres would confound resolution, alignment and
which piece of ground is being asked about. Frame B uses building coordinates. Frame C samples a
cell and then draws **one uniformly random point inside it**, which is a property of the ground
rather than of the grid, so the same point set can be evaluated against every candidate grid and
encoding.

**Both frames are frozen artifacts with digests**, for the reason S2.5 recorded: file order is not
stable across downloads, and "the first N" silently changed which POIs an experiment used. A
measurement that cannot name its frame cannot be compared with another.

---

## 2. The comparator, specified before the estimands

Revision 1 said "the engine's own answer at that coordinate", which is not executable (pass-14
M5). Every number below depends on these choices, so they are fixed here.

| | |
|---|---|
| **origin** | the sampled point (a building centroid, or a random point in a sampled cell) |
| **destination set** | the same 550 grocery places the layer was built from, by their own coordinates, **not** their snapped nodes |
| **direction** | the product answers "how long to *reach* a destination", so the comparator routes **origin → destination**. The arrival surface is built on the transposed graph; a one-way road can make origin→destination routable while destination→origin is not, so the comparator must not be run in the surface's internal direction |
| **selection objective** | **two runs**: `min over destinations of time` (the quantity the surface approximates) and `time along the cost-nearest destination's path` (what the surface *reports*). Both are retained, because the gap between them is the pass-8 H2 bound and must not be charged to the pipeline |
| **departure/arrival** | walk and bike are time-independent; drive and transit use the fixed arrival datetime in the `SurfaceKey` being tested |
| **connectors** | the origin's access leg is charged at the layer's own access speed and capped at `max_access_m`; a point with no network within the cap is a **status**, not a missing value (§7) |

E1 compares the **encoded** surface — what ships — against the comparator's first objective. The
encoding's own contribution is the encoded-minus-float difference, kept separately.

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
of cells. This is ours to fix — same engine both sides, so a difference is a defect.

### E2 — engine disagreement (descriptive)

> **d = t_independent − t_float**, in seconds, at the same point with matched arrival time,

where `t_float` is our pre-encoding reconstruction and `t_independent` the other engine's answer
under the same comparator rules. Signed, reported as median and IQR with a block bootstrap, plus
the share with |d| greater than one encoding increment. Revision 1 defined E2 against "reported
time" in one place and the float surface in another; it is the float surface, so that encoding does
not appear twice (pass-14 L2).

Four paired values are retained per point — comparator, float surface, encoded surface, independent
engine — so that encoding, snapping, entrance choice and route choice cannot be absorbed into one
unattributable "model error".

### E3 — real-world accuracy (supported / **failed** / UNVERIFIED)

> **the signed difference between a hand-timed journey and the product's reported time.**

5–8 owner-chosen journeys cannot establish a population rate: they are a convenience sample, so the
binomial bound does not even apply to them, and with 8 observations and no discrepancy the
one-sided 95% exact bound would in any case be **31.2344%**. The population-rate claim is therefore
**UNVERIFIED** and the published label says so.

**But it can still fail, and revision 1 made that impossible** (pass-14 M6). "UNVERIFIED whatever
these journeys show" means eight journeys each taking three times the predicted time could not
produce the `failed` outcome the design advertises. A small sample cannot establish a rate; it can
exhibit a counterexample. So, predeclared:

> **E3 returns `failed` if any single journey's observed time exceeds the product's reported time by
> more than a factor of 1.5 and by more than 5 minutes, or if the median signed difference across
> the journeys taken exceeds 25% of the median reported time.**

`failed` is a statement about the product, not about a rate. Absent a failure, the outcome is
UNVERIFIED — never "supported" — until an independent sample large enough for a rate exists.

---

## 4. Samples

**Frame C — the population estimator for cells.** A simple random sample, *n* = 400.

**Frame B — the population estimator for structures.** A simple random sample, *n* = 400.

**And four diagnostics, which are NOT pooled into either estimate.** Revision 1 called these strata
and planned to combine them with `N_h / n_h` weights. They are not a partition (pass-14 H5): a
building can be boundary-adjacent *and* within one encoding increment *and* in the whole-frame
sample simultaneously, so pooling counts the same population mass several times. An overlapping-frame
estimator needs real inclusion probabilities and a covariance treatment, which is more machinery
than the question deserves.

So they are **targeted diagnostics**, each reported on its own terms and never added to a total:

| diagnostic | sampling frame | *n* | what it is for |
|---|---|---|---|
| **A — boundary-adjacent** | points whose cell is 4-adjacent to a cell with the opposite verdict at *T* | 150 | where misclassification concentrates geometrically |
| **B — within one encoding increment** | points whose reported value is within one encoding step (60 s today) of *T* | 150 | where it concentrates *numerically*; a point can be in one without the other |
| **D1 — off-network** | points the product reports `OFF_NETWORK` | 200 | false exclusion at the extreme, which A and B cannot see because both require a value |
| **D2 — beyond-horizon** | points the product reports `BEYOND_HORIZON` | 200 | the same, with a different remedy and a very different population (3,657 against 9,967 buildings) |

A diagnostic answers "is the rate *here* materially worse than the population rate", and is reported
as its own proportion with its own interval. The population rates come from frames B and C alone.

---

## 5. Weights

The two population samples are simple random samples, so they are **self-weighting**: the estimate
is the sample proportion and no `N_h / n_h` correction applies. That is a deliberate simplification
bought by abandoning the pooled-strata design — it removes the whole class of error pass-14 H5
found.

The diagnostics carry no weights at all, because they estimate nothing about the population.

---

## 6. Intervals, with one convention

**One-sided 95% exact (Clopper–Pearson) upper bounds for failure rates**, throughout. The quantity
of interest is "how bad could this be", the bound is exact rather than approximate, and it behaves
at zero observed failures — which is the case the design exists to handle honestly. Revision 1 said
"Wilson on *n*/DEFF", which is an approximation, and mixed one- and two-sided language (pass-14 M4).

Zero observed failures, for reference, with the alternatives Codex asked be made explicit:

| *n* | exact one-sided | Wilson one-sided | Wilson two-sided |
|---|---|---|---|
| 8 | **31.2344%** | 25.2724% | 32.4408% |
| 60 | **4.8703%** | 4.3147% | 6.0172% |
| 150 | **1.9773%** | 1.7717% | 2.4970% |
| 400 | **0.7461%** | 0.6718% | 0.9512% |

A zero-failure result is reported as **"0 observed, 95% upper bound x%"** and never as "0%".

**Clustering.** Points near each other share a road network, a snapping geometry and a nearest
destination, so observations are not independent and the exact binomial bound is optimistic. The
design effect is estimated as follows, and the zero-event case is predeclared because it is the
expected one (pass-14 M4):

- **Blocks** are the 2 km × 2 km squares of the grid's own projected coordinates — fixed, not
  data-dependent.
- DEFF is estimated by the **between-block variance of the block-level failure proportions** against
  the binomial variance at the pooled rate, over blocks containing **at least 5 sampled points**;
  blocks below that are pooled with their nearest qualifying neighbour.
- **If the pooled failure count is 0, DEFF is not estimable.** The predeclared fallback is
  **DEFF = 2.0**, applied by dividing *n* before computing the bound, which is the conventional
  allowance for a moderately clustered design. The reported bound then says it used the fallback.

Paired differences (E2) use a **block bootstrap over those same blocks**, resampling blocks with
replacement, 2,000 replicates, percentile interval.

---

## 7. Every outcome has a verdict

Revision 1 said missing data would be "reported with counts and treated as informative", which
leaves the arithmetic undefined. A verdict table instead (pass-14 M5), so no status can quietly
contribute a zero to an error count:

| comparator outcome | product says *pass* | product says *fail* |
|---|---|---|
| route found, ≤ *T* | agree | **E1a** false exclusion |
| route found, > *T* | **E1b** false inclusion | agree |
| **definitive no path** (search exhausted) | **E1b** — the product promised a journey that does not exist | agree |
| no network within `max_access_m` of the point | **E1b** | agree |
| **unknown** (timeout, engine error, snap failure) | counted in an **unknown** bucket | counted in **unknown** |

The unknown bucket is **bounded both ways**, never dropped and never assumed benign: the reported
result gives the rate with every unknown counted as agreement and again with every unknown counted
as an error. If those two bounds straddle the acceptance threshold in §8, the result is
**inconclusive** and the gate does not pass.

A planned hand-timed journey that was not walked leaves E3 UNVERIFIED. It is never read as absence
of disagreement — that is the escape hatch S3.4 exists to close.

---

## 8. The acceptance rule, predeclared

Revision 1 called E1 a PASS/FAIL gate without saying what passes (pass-14 H7), which leaves the
verdict selectable after the fact. So:

For each published mode *m* and threshold *T*, on **each** frame:

- **PASS** if the one-sided 95% upper bound on **E1a** is **≤ 2.0%** and on **E1b** is **≤ 1.0%**.
- **FAIL** if the point estimate of either exceeds its threshold.
- **INCONCLUSIVE** otherwise — including whenever the unknown-bucket bounds of §7 straddle a
  threshold. Inconclusive is not a pass, and shipping on one is an explicit owner decision.

**E1b is held to the tighter bound** because a false inclusion is a claim the product made and a
false exclusion is a home it failed to mention; both are harmful, and only the first is a statement
we would have to defend. The thresholds are judgements, recorded here before measurement, and are
the owner's to move — but not after seeing the result.

**Every published mode and threshold must pass on both frames** for the layer to be described as
construction-verified. A single failing combination is reported as such rather than averaged away.

---

## 9. What has to exist before the pilot runs

- [ ] Frame B and frame C artifacts with digests (§1).
- [ ] The comparator harness, implementing §2 exactly, for each engine.
- [ ] Diagnostic membership computed on the shipped surface per published *T* (§4).
- [ ] The 2 km block grid, and the bootstrap over it (§6).
- [ ] A decision on the published **maximum duration**, which bounds the encoding (S3.5) — today a
      cell *at* the 120-minute horizon is indistinguishable from a genuine 120-minute answer.

The last item is the owner's, and the encoding freeze waits on it.

---

## 10. What revision 2 changed, and why

Recorded rather than silently edited, because the point of predeclaring is that changes are visible.

| pass-14 | revision 1 said | revision 2 says |
|---|---|---|
| **H5** | four strata pooled with `N_h / n_h` weights | they overlap, so they are not a partition. Two self-weighting simple random samples estimate the populations; the four are **diagnostics**, never pooled |
| **H6** | one building frame, reporting both building and cell rates | a cell with no buildings has zero selection probability. **Two frames**, each reporting only its own estimand |
| **H7** | "PASS / FAIL", no rule | explicit bounds (E1a ≤ 2.0%, E1b ≤ 1.0%, one-sided 95% upper), an INCONCLUSIVE outcome, and all modes/thresholds/frames must pass |
| **M4** | "Wilson on *n*/DEFF"; DEFF from the pilot | one convention (exact one-sided); fixed 2 km blocks; a named variance estimator; and a **predeclared DEFF = 2.0 fallback**, because zero observed failures makes DEFF inestimable and zero is the expected case |
| **M5** | "the engine's own answer at that coordinate" | a full comparator specification (§2) and a **verdict table for every status** (§7), with the unknown bucket bounded both ways and a definitive "no path" scored as a false inclusion rather than filed under missing |
| **M6** | E3 "UNVERIFIED whatever these journeys show" | unfalsifiable as written. A magnitude-based **falsification rule** can return `failed`; the population *rate* stays UNVERIFIED |
| **L2** | E2 defined against reported time, compared against the float surface | defined once, against the float surface, with an explicit signed formula |

One judgement deliberately kept from revision 1: the allocations are sized for **small** rates. At
*n* = 400 and a true rate near 1%, the exact one-sided bound is about 1.8 points; the familiar
"385 for five points" figure assumes *p* = 0.5 and is the pessimistic bound, not the target. Codex
notes that extrapolating small-rate expectations from the S0 encoding bracket to the building and
boundary populations is not evidence, and that is fair: the expectation is a **planning assumption**,
and if the pilot shows rates near 0.5 the allocations are insufficient and the result will say so
rather than being reported at a margin it cannot support.
