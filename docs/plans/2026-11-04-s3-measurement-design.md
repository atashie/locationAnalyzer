# S3 measurement design — predeclared

**Status:** design, predeclared before any sampling. Nothing in this document reports a result.
**Supersedes:** the sampling sketch inside revision 2 of `2026-11-03-phase1-plan.md` (S3.1–S3.4),
which this expands into something executable.

The reason for predeclaring is specific and not ceremonial. Revision 1 chose "60 cells per side per
threshold" with no estimand, and Codex's arithmetic showed what that buys: with 60 independent
observations and **zero** observed failures, the one-sided 95% upper bound on the failure rate is
**4.87%**, not zero. A design chosen after seeing the data can always be the design that passes. So
the estimands, strata, allocations, weights, interval method and missing-data rules are fixed here,
in advance, and the first run is explicitly a **pilot that estimates variance**, not a verdict.

---

## 1. One frozen set of locations, used by everything

Codex established that `TRIANGLE.grid()` is **not nested** across resolutions: 100 m has origin
661900/4003500 and is 643 × 514; 200 m has origin 661800/4003600 and is 322 × 258. Sampling each
grid at its own cell centres would confound three things at once — resolution, alignment, and which
piece of ground is being asked about.

So every candidate grid and every candidate encoding is evaluated at **one frozen set of
coordinates**, and nothing is ever evaluated at cell centres.

**Frame construction.** Locations come from the S2.4 building set
(`overture_buildings_accepted.parquet`, 522,160 rows, 512,633 with a centroid inside the 100 m
grid), projected to EPSG:32617, one point per building centroid. Destination-side points are the
550 grocery places with their own coordinates, not their snapped nodes.

**The frame is an artifact with a digest**, written once and referenced by every S3 measurement, for
the reason recorded in S2.5: file order is not stable across downloads and "the first N" silently
changed which POIs an experiment used. A measurement that cannot name its frame cannot be compared
with another.

**This is a building frame, not a household frame.** Overture carries no reliable residential flag
in this metro, so a shed, a barn, a warehouse and each of a hospital campus's several hundred
structures are one location each. Every estimand below is therefore **building-weighted**, and the
phrase "household" appears nowhere in the outputs. S2.4 measured why this matters: cell coverage is
77.6855% and building coverage 97.3423%, so the choice of denominator moves the headline by twenty
points.

---

## 2. Estimands

Three, measuring different things, with different units and different standards of evidence. They
are never combined into one score.

### E1 — Construction fidelity (the PASS/FAIL gate)

For a mode *m* and published threshold *T*, over the building frame:

> **the proportion of locations at which the product's verdict at *T* differs from the verdict
> obtained by routing to that location's own coordinate with the same engine.**

Decomposed, because the two directions are not equally harmful and S0's H2 bracket predicts only
one of them:

- **E1a false exclusion** — the product says *fail*, the exact route says *pass*. A home the
  household never sees. The category surface is an upper bound on time, so this is the direction
  the bracket predicts.
- **E1b false inclusion** — the product says *pass*, the exact route says *fail*. A wasted viewing.

Reported separately, both building-weighted and cell-weighted. This is **ours to fix**: the
comparison is against the same engine, so a difference is a defect in our pipeline, not a
disagreement about the world.

### E2 — Engine disagreement (descriptive, reported with magnitude)

> **the signed paired difference, in seconds, between our reported time and an independent
> engine's answer at the same coordinate with a matched arrival time.**

Reported as median, IQR, and the proportion exceeding one encoding increment. Four paired values
are retained per location, never summed and never reduced to a median of medians:

| value | what it is |
|---|---|
| exact route to the location | the engine's own answer at that coordinate |
| float surface at the location | our reconstruction, pre-encoding |
| encoded surface at the location | what the product actually ships |
| independent prediction | a different engine, matched arrival time |

E1 is (column 3 vs column 1). The encoding's own contribution is (column 3 vs column 2). E2 is
(column 4 vs column 2). Keeping all four paired is what stops "model error" from absorbing
encoding, snapping, entrance choice and route choice into one unattributable number, which is how
revision 1 went wrong.

### E3 — Real-world accuracy (supported / failed / **UNVERIFIED**)

> **the signed difference between a hand-timed journey and the product's reported time for that
> journey.**

**Predeclared now, before any journey is walked:** 5–8 journeys cannot support a rate. They can
support a *direction and magnitude* check — "the product is not out by a factor of two" — and
nothing more. With 8 observations and zero discrepancies the one-sided 95% upper bound on the
discrepancy rate is **31%**. So decision 12's accuracy claim stays **UNVERIFIED** whatever these
journeys show, and the published label says so, unless and until a far larger independent sample
exists.

This is the honesty mechanism revision 1 got wrong. It required *both* Google disagreement *and*
confirming owner journeys before weakening the claim, which made an untaken or inconclusive journey
an escape hatch that strengthened the claim by default. One condition, stated plainly: **absent
independent observation, the claim is unverified.** Shipping with an unverified accuracy claim is a
legitimate decision for a friends-and-family release; it is the owner's to make explicitly, and not
something this measurement design may grant by construction.

---

## 3. Strata

Four, and the first two are **different populations that are never pooled** — Codex's point, and the
reason revision 1's "cells per side" was ill-defined.

| stratum | definition | what it is for |
|---|---|---|
| **A — boundary-adjacent** | the location's cell is 4-adjacent to a cell with the opposite verdict at *T* | where misclassification concentrates geometrically |
| **B — within one encoding increment** | \|reported − *T*\| ≤ one encoding step (60 s at today's uint8 whole minutes) | where misclassification concentrates *numerically*; a cell can be in B without being in A and vice versa |
| **C — independent residential** | a systematic sample over the whole building frame, unstratified by boundary | catches a pipeline that wrongly deletes a neighbourhood, which A and B can never sample because they condition on being near a boundary |
| **D — predicted unreachable** | the product reports no value (`OFF_NETWORK` or `BEYOND_HORIZON`) | catches false exclusion at the extreme; A and B both condition on *having* a value, so neither can see this |

A and B are defined on the shipped surface, which is what makes them computable before routing. C
and D are defined without reference to *T*.

D is stratified further by reason, because the two have different remedies and very different
building counts (3,657 off-network buildings against 9,967 beyond-horizon): **D1 off-network**,
**D2 beyond-horizon**.

---

## 4. Allocations

**The first run is a pilot.** Its output is a variance and design-effect estimate, not a verdict.

| stratum | pilot *n* | main *n* (conditional on the pilot) |
|---|---|---|
| A boundary-adjacent | 60 | 150 |
| B within one increment | 60 | 150 |
| C independent residential | 60 | 400 |
| D1 off-network | 60 | 200 |
| D2 beyond-horizon | 60 | 200 |

**Where the numbers come from.** For a worst-case proportion (*p* = 0.5), a five-point margin at 95%
needs 1.96² · 0.25 / 0.05² ≈ **385** observations per denominator. But the rates we expect are
small — S0's H2 bracket moves under 1% of cells across every threshold tested — and at *p* ≈ 0.01,
*n* = 385 gives a half-width of about **1.0 point**, which is ample, while *n* = 150 gives about
1.6 points. So the allocation is sized for small rates and the 385 figure is the pessimistic bound,
not the target. Both are reported so a reader can see which regime a result is in.

**Clustering inflates all of this and the pilot measures by how much.** Locations in the same
neighbourhood share a road network, a snapping geometry and a nearest destination, so observations
are not independent. The pilot estimates a design effect **DEFF** by comparing the observed variance
of E1 within spatial blocks against the binomial variance. The main allocation is multiplied by the
estimated DEFF, or — if that is unaffordable — the margin is widened and reported, never the other
way round.

**Predeclared stopping rule:** the main run's allocation is fixed by the pilot's DEFF before any
main-run routing is done, and is not revised afterwards.

---

## 5. Weights

Each stratum is sampled at a different rate, so nothing may be reported as a raw proportion of the
sample. Inverse-probability weights:

> *w<sub>i</sub>* = *N<sub>h</sub>* / *n<sub>h</sub>* for a location *i* in stratum *h*,

where *N<sub>h</sub>* is the stratum's size in the frame and *n<sub>h</sub>* the number sampled.
Two totals are reported for every estimand, because S2.4 showed they disagree by twenty points:

- **building-weighted**, with *N<sub>h</sub>* counted in buildings — the headline;
- **cell-weighted**, with *N<sub>h</sub>* counted in cells — comparable with every coverage figure
  published so far.

A and B are defined per threshold *T*, so their stratum sizes — and therefore their weights — are
recomputed for each *T*. C, D1 and D2 are *T*-independent and keep one set of weights.

---

## 6. Confidence intervals

- Proportions (E1a, E1b): **Wilson score intervals** on the effective sample size *n* / DEFF, not
  Wald. Wald is degenerate at zero observed failures, which is precisely the case the whole design
  exists to handle honestly, and it was the implicit method behind "zero failures means zero".
- Where zero failures are observed, the result is reported as **"0 observed, 95% upper bound x%"**
  and never as "0%".
- Stratified totals: Taylor-linearised variance across strata, with the DEFF applied per stratum.
- Paired differences (E2): bootstrap percentile intervals over **spatial blocks**, not over
  individual locations, so the resampling respects the clustering rather than assuming it away.

---

## 7. Missing data

Three kinds, all **reported with counts and treated as informative**. None is dropped, because each
of them is a result.

1. **The engine will not route to a sampled coordinate** — no snap within the access bound, or no
   path. This is not missing data about the world; it is an observation about our pipeline, and it
   enters the denominator as its own category.
2. **A planned hand-timed journey was not walked.** The claim stays UNVERIFIED. An untaken journey
   is never read as absence of disagreement — that is exactly the escape hatch S3.4 was written to
   close.
3. **A sampled building lies outside the routable extent.** Counted and reported; the routing bbox
   exists to make this rare, and if it is not rare that is a finding about the buffer.

The primary analysis reports every estimand with the missing categories visible in the denominator.
A secondary complete-case analysis may be reported *alongside* it, never instead of it, and the two
must be shown together so a reader can see what the exclusion did.

---

## 8. What a result may say

Per S3.4, three outcomes, not a pass/fail:

1. **Construction fidelity: PASS or FAIL.** Ours to fix. A failure is a defect, and the gate is
   stated as a rate with an interval, not as "no failures seen".
2. **Engine disagreement: reported with magnitude.** Descriptive. Not a defect and not evidence
   about reality; it is two models differing until the cause is controlled.
3. **Real-world accuracy: supported / failed / UNVERIFIED**, with UNVERIFIED the predeclared
   default.

---

## 9. What has to exist before the pilot runs

- [ ] The frozen frame artifact and its digest (§1), built from the S2.4 building set.
- [ ] Stratum membership computed on the shipped surface for each published *T* (§3).
- [ ] An exact-route harness that routes to a **coordinate**, not a cell centre, for each engine.
- [ ] The spatial block definition used by both the DEFF estimate and the bootstrap (§4, §6).
- [ ] A decision on the published **maximum duration**, since it bounds the encoding (S3.5) and the
      current layer cannot distinguish a cell *at* the 120-minute horizon from a genuine 120-minute
      answer.

The last item is the owner's, and the encoding freeze in S3.5 waits on it.
