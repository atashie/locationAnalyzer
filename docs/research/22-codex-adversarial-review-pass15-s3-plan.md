# Codex adversarial review, pass 15 — the S3 execution plan

**Date:** 2026-11-04. **Model:** gpt-6.1-sol. **Head at review:** `ab01ffa`. **Prompt:**
`codex-pass15-prompt.md` (scratchpad). **Eighteen defects: 8 High, 10 Medium.**

The verdict, first:

> "**This plan is not fit to execute as written.** Its strongest defects are an acceptance gate that
> cannot pass in the expected zero-failure case, a block-pooling fallback that usually destroys the
> bootstrap, and an unresolved comparator specification. Several defects originate in revision 2
> itself; implementing them faithfully would still produce an invalid instrument."

So the plan is not merely under-specified. The predeclared **design** has an acceptance rule that
its own predeclared allocation cannot satisfy, and three of the eighteen findings are defects I
introduced while trying to make the design executable.

## The one that ends the current design — the gate cannot pass (H2)

Executed arithmetic:

```
n = 400, failures = 0, DEFF = 2  ->  effective n = 200
one-sided 95% exact upper bound  =  1 - 0.05^(1/200)  =  1.4867%
E1b acceptance threshold                                 1.0%
```

**Perfect observed agreement cannot certify E1b.** Zero-event certification at 1.0% needs ≥ 299
effective observations — 598 actual, if the factor-of-two allowance is kept.

This composes with what I had found independently an hour earlier: §6's DEFF estimator **cannot run
at all** at *n* = 400. Simulated against the real building distribution (857 of 858 blocks hold ≥ 1
building; median 327, max 3,804):

| sample | blocks reaching ≥ 5 points | share of sample inside them |
|---|---|---|
| frame B, *n* = 400 | **2.8** | 4% |
| frame C, *n* = 400 | **0.1** | 0% |
| all 1,500 pooled | 103.3 | 46% |

Codex's independent simulation agrees: "1,000 seeded draws: **893 had no block containing at least 5
observations**". So the fallback is the only reachable path, and the only reachable path cannot pass.
Note the cause: the 1,500-point row *would* qualify, but pooling diagnostics into the population
estimates is exactly what pass-14 H5 forbade. **The fix for H5 is what made DEFF inestimable.**

## The deeper finding: DEFF does not belong here at all (H1)

Codex's framing is the one that matters, and it dissolves four findings at once:

> "For the declared finite-population SRS, spatially adjacent outcomes do not by themselves turn the
> sample into a cluster sample."

Clopper–Pearson is an inversion of the binomial model, not a generic variance adjustment, and
dividing *n* by an estimated DEFF destroys its coverage guarantee — the plan did not even specify
whether the numerator is retained or scaled, and `effective_n()` returns a float where
`clopper_pearson_upper()` needs an integer.

**Clustering inflates variance when the *design* clusters.** E1's estimand is a share of a defined
finite frame, sampled by SRS of points; its variance is `p(1-p)/n * (1 - n/N)` regardless of how
correlated neighbouring ground is. The whole clustering apparatus — §6's DEFF, the 2 km blocks, the
≥ 5 pooling rule, the block bootstrap — was imported for a design that was never drawn as a cluster
sample.

## Three findings are defects I added (H3, M9, M11)

Fourth consecutive round in which my own repair is the finding.

- **H3 — my pooling-termination fix creates fake precision.** I was right that "pool with the nearest
  *qualifying* neighbour" is undefined when none qualifies, and my T2 test required pooling to
  terminate in a single block. Codex: resampling one block returns **the identical dataset in all
  2,000 replicates**, so the bootstrap reports a zero-width interval for an uncertain statistic. My
  test would have *enforced* it. "Do not turn a single block into apparent precision."
- **M11 — my T4 test contradicts the layer contract.** I asserted `NODATA` is never "the opposite
  verdict". But the contract makes `BEYOND_HORIZON` a known FAIL whenever *T* ≤ *H*, and Codex
  measured **14 `BEYOND_HORIZON` cells 4-adjacent to a passing cell at *T* = 10**. The design is
  itself inconsistent — its geometric definition says opposite verdicts, its prose says A requires a
  value — and I "silently resolved that contradiction through a test". The same pattern as
  [`feedback-computable-property-is-not-the-claim`]: an ambiguity in the claim settled inside an
  implementation detail.
- **M9 — my bounded-search rule is too blunt.** Refusing to infer `NO_PATH` from a bounded search is
  correct and survived. But a search that exhausts everything through horizon *H* **does** establish
  failure for *T* ≤ *H*, so routing every bounded no-result to the unknown bucket understates the
  *known* E1b count. Retain bound type, value and termination reason; score a failure when the sound
  lower bound exceeds *T*.

## The production-adjacent one (H6)

`traveltime/csr.py`'s `graph_to_cost_time_csr()` keeps the **cost-minimum** parallel edge and its
time, so its `time_csr` cannot find minimum-time routes. Executed counterexample:

```
parallel edge A: time 1, cost 100
parallel edge B: time 10, cost 10
true minimum-time route: 1      Dijkstra on time_csr: 10
```

Objective 1 — the quantity E1 is defined against — would silently inherit cost-based collapse. This
is the **same defect class as S2.3's**: separate the classes on the multigraph *before* collapse, or
the alternative is already lost. And my proposed test (two objectives choosing different
destinations) need not contain parallel edges, so it passes while the implementation is wrong.

## Where I contradicted the design while claiming not to (M7, M14)

Plan §4 claimed it "does not change a single number in the design". Two violations:

- **M7.** I wrote that the cost-versus-time selection gap "must not be charged to the pipeline". But
  §2 compares the encoded surface against **objective 1**, so that gap **is** in E1 by design.
  Retaining objective 2 does not remove it from the gate. Report it separately; do not exempt it.
- **M14.** Authorising E2 on a smaller subsample "if computation is expensive" is an undeclared
  allocation change. Worse, the premise was false — see below.

## Other findings

- **H5 destination snapping.** T5 promises destinations at their own coordinates; T7 admits they
  snap. Measured: **549 of 550** within the 300 m cap, nearest-node distance median **28.07 m**, p90
  45.71 m, **max 478.66 m**. Omitting the destination connector can change destination *selection*
  and cross thresholds, and is **not universally one-sided**. Prohibiting a "building service" claim
  does not repair the comparator.
- **H8 the product has UNKNOWN.** §7's verdict table has only PASS and FAIL columns. Codex
  constructed a 250 m-access off-network surface and `status.evaluate()` returned **UNKNOWN** at
  *T* = 10 — precisely the D1 population. No rule exists for it.
- **H10 the diagnostics have no sampling population**, and A/B are threshold-specific: 150 each
  across four thresholds is **1,200** draws, so the total is **2,400**, not 1,500. T7 never requires
  diagnostic rates or intervals, and "materially worse" has no effect-size criterion.
- **H15 deferring the maximum duration is not arithmetic-only.** The saved float surface is already
  **horizon-censored** — raising *H* cannot recover times from `inf` — and re-encoding changes
  diagnostic A/B membership, so old samples do not stay valid. My "needs no re-routing" was wrong.
- **M16 my test fixtures pass a wrong implementation.** `k/n + (1-k/n)*(1 - 0.05**(1/n))` satisfies
  every zero-event fixture, the endpoint and the monotonicity checks, yet at *k* = 1, *n* = 400 gives
  **0.9943%** against the correct **1.1804%** — enough to flip the E1b verdict. Also: T3's tests
  permit frame C points always at cell centres, and the printed table is rounded, so literal equality
  is not a correct test.
- **M4** the DEFF estimator was never mathematically specified (weights, denominator, unequal block
  sizes, the all-failures case); **M12** a random 50-point prefix cannot exercise every verdict
  branch, and `OFF_NETWORK` legitimately lacks numeric values, so "all four paired values populated"
  is self-contradictory; **M13** the prefix argument is wrong both ways — what matters is the
  **adaptation policy**, not the draw, and reusing debugging observations can be worse than an
  independent debug sample plus a frozen holdout; **M17** frame digests identify points, not the
  instrument — no hashes for the float/encoded/status rasters, the graph or the destination list;
  **M18** no executable tasks for E3 ingestion, S3.1's matched entrances, S3.5's transfer size and
  phone decode, or the contract's extraction-truncation diagnostic.

## My compute estimate was 40× pessimistic

Codex measured individual full-graph Dijkstra calls at **0.057–0.059 s**, not the 1–3 s I assumed
(excluding preparation, attachments, the second objective and cost-path reconstruction). So the
computational justification for E2 subsampling does not exist. **Benchmark the complete comparator
before letting cost drive a design change.**

## What survived attack

- **All three gates are real.** Revision 2 does retain "pilot" language with no operative pilot
  allocation; there is no published-threshold registry in `v2/locfinder/`; Triangle-scale layers
  exist only for walk, and scoped walk certification is reasonable.
- **No multiplicity correction is needed** for the single global conjunction — though the sixteen
  individual bounds are **not** simultaneous 95% bounds, which the report must not imply.
- Separate building and cell samples, immutable frame artifacts, projected centroids, signed E2
  differences, and refusing to pool diagnostic totals are all sound. One point per structure
  estimates the declared structure population, not households.
- **Uniform cell then uniform point is unbiased** for average disagreement over ground *area* — but
  not for "the fraction of cells containing any error". A wording fix, not a sampling change.
- Refusing to infer `NO_PATH` from an arbitrary bounded no-result is correct.
- E1 against an independently implemented path through the same engine is appropriate construction
  testing; E2 is engine disagreement; E3 cannot establish a population rate from convenience
  journeys.
- Every artifact figure reproduced: 522,160 buildings, **512,633** projected centroids inside the
  100 m grid, 643 × 514 = 330,502 cells, the non-nested 200 m grid, 858 intersecting 2 km blocks,
  550 groceries from 107,484 accepted places, 539,814 graph nodes / 1,395,589 CSR entries, walk
  access speed 1.26 m/s, `max_access_m` 200 m, and the encoded TIFF exactly matching
  `encode_minutes(float_surface)`. Building reasons 499,009 OK / 3,657 `OFF_NETWORK` / 9,967
  `BEYOND_HORIZON`; cell reasons 256,752 / 57,541 / 16,209.

## The recommended reshape

Codex's closing proposal, which I endorse: **separate development from certification.** Validate the
harness on synthetic graphs and independent development points, freeze the product and the analysis,
then execute untouched probability samples; use inference justified by the frames' actual sampling
design; and keep spatial exploration and E2 bootstrap reporting out of the construction gate. That
removes the prefix-adaptation problem and avoids building elaborate DEFF machinery around a sample
that was never drawn as a cluster sample.
