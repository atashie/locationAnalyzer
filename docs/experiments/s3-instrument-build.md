# S3 instrument build record

**Nothing here is a measurement result.** This records what has been built, with the digests that
identify it, so design §12's frozen-artifact checklist has somewhere to point. The measurement
itself is `s3-walk-grocery-measurement.md`, which does not exist yet.

**Design:** [`2026-11-04-s3-measurement-design.md`](../plans/2026-11-04-s3-measurement-design.md)
revision 5. **Plan:** [`2026-11-04-s3-execution-plan.md`](../plans/2026-11-04-s3-execution-plan.md)
revision 4.

---

## T1 — statistical primitives · done 2026-11-05

`v2/locfinder/measure/stats.py`, `v2/tests/test_stats.py` (65 tests).

Exact one-sided Clopper–Pearson bounds in **both** directions, the §8 acceptance rule, the frozen
bootstrap convention, and the exact finite-population and two-stage variance formulas. No design
effect, no effective-sample-size adjustment.

**The decisive test oracle is binomial-tail inversion** — `brentq` on `binom.cdf` — which calls
neither `beta.ppf` nor the implementation, checked at **1e-10** across *k* = 0…4 and six sample
sizes. Three reviews had defeated weaker oracles:

| wrong implementation | what it passed | where it fails now |
|---|---|---|
| `k/n + (1−k/n)(1−0.05^(1/n))` (pass 15) | every zero-event value, both endpoints, monotonicity | 0.009943 vs 0.011804 at *k*=1, *n*=400 — flips the 1% verdict |
| correct except at *k*=1, *n*=400 (pass 18) | all of the above **at a 0.002 tolerance** | the 1e-10 comparison |
| a two-sided *lower* bound (pass 18) | zero endpoint, confidence direction | 0.000102581 vs 0.000050634 at *k*=1, *n*=500 |

Two tests deliberately record properties that must **not** be asserted: interval width is **not**
monotone in *n* (`[-1,0,1]` → `[-1,1]`; the smaller `[0,0]` → `[0,0]`), and **an all-abstaining
product passes E1** at 0.5974%, which is why coverage is a separately blocked gate and why no
diagnostic may be claimed to prevent it.

`tolerated_failures` returns **−1**, not 0, when not even zero failures satisfies the threshold —
the unreachable-gate condition revision 2 shipped undetected. Verified: *n* = 298 → −1, *n* = 299
→ 0.

## T2 — sampling frames · done 2026-11-05

`v2/locfinder/measure/frames.py`, `v2/tests/test_frames.py` (19 tests).

**The draw is normative, not just the distribution**, because "simple random sample" does not
identify a sequence:

```
rng = numpy.random.Generator(PCG64(seed))
frame C: cells   = rng.permutation(N_cells)[:n]     # first
         offsets = rng.random((n, 2))               # then, two independent columns
frame B: idx     = rng.permutation(N_population)[:n]
```

`permutation(N)[:n]` rather than `choice(..., replace=False)`, because `choice` picks among internal
algorithms by the *n*/*N* ratio and so is not a specification. Frame B's population is sorted by
Overture `id` before any draw, so the ordering is a property of the data rather than of the
download — S2.5 recorded file order changing which POIs an experiment used.

**Two independent guards against the sampling defects two earlier test revisions admitted:** an
exact-sequence oracle transcribed from the specification, and a **joint** check on the two offsets'
correlation. The rejected `(u, u)` implementation selects the *same cells*, so a cells-only test
cannot separate it; it is caught by the exact oracle and by correlation 1.0 against < 0.05.

### Population, verified at build time

| | measured | design §1 |
|---|---|---|
| building rows | **522,160** | 522,160 ✓ |
| projected centroids inside the 100 m grid | **512,633** | 512,633 ✓ |
| grid | 643 × 514 = 330,502 cells, EPSG:32617 | ✓ |

Both counts are **asserted in the build script**, so a future re-acquisition that changes them fails
loudly rather than silently redefining the frame.

### Development frame artifacts

Design §10 separates development from certification: these are the **development** frames, their
observations are never substituted for certification estimates, and the **certification draw happens
after the freeze** under §10's registration. They use *n* = 500 — the certification size — so timing
measured on them is the timing certification will cost, and no new allocation is introduced.

`v2/data/` is not tracked, so the digests below are the artifacts' identity in the repository; the
manifests make each reproducible from its source digest, seed and *n*.

| frame | *n* | population | seed | digest | file |
|---|---|---|---|---|---|
| B structures | 500 | 512,633 | 20261105001 | `93f83cf39e8a0c5f...` | `frame_b_93f83cf3.parquet` |
| C area | 500 | 330,502 | 20261105002 | `e233ff0f38343e1a...` | `frame_c_e233ff0f.parquet` |

Source digests: buildings parquet
`96f3690c17a923b06515d6372032111e5eb46063ab2822cdeef76fc1e52ad54c`; frame C's population is the grid
itself, digest `3edbb48d6b99d337fba5953f4767ccb66738b75c904380d0ba9d7ebe2b285cf2`.

Extents, as a sanity check rather than a result: frame C spans x 661,994 – 726,005 and y
3,952,109 – 4,003,445, essentially the whole grid; frame B spans x 663,228 – 725,868 and y
3,952,317 – 4,003,206, narrower because structures do not reach the grid edges.

A frame artifact is **never overwritten** — a new sample is a new digest, so a name collision is an
attempt to rewrite history and raises.

---

## Suite

**412 tests pass** (328 before S3, plus 65 for T1 and 19 for T2).

## Not yet built

T3 the reference comparator · T4 the conformance suite · T5 diagnostics · T6 the run manifest ·
T7 development including the encoding and wire migration · T8 freeze and certify · T9 E3 scoring ·
T10 the extraction warning · T11 the report.

**Still open and owner-gated:** the **coverage requirement** (design §8), which blocks the coverage
claim only — not the build and not the construction gate.
