# S3 instrument build record

**Nothing here is a measurement result.** This records what has been built, with the digests that
identify it, so design §12's frozen-artifact checklist has somewhere to point. The measurement
itself is `s3-walk-grocery-measurement.md`, which does not exist yet.

**Design:** [`2026-11-04-s3-measurement-design.md`](../plans/2026-11-04-s3-measurement-design.md)
revision 6. **Plan:** [`2026-11-04-s3-execution-plan.md`](../plans/2026-11-04-s3-execution-plan.md)
revision 5.

**Five statements in the first version of this record overstated what had been evidenced.** Codex
pass 19 named each one, and each is corrected in place below rather than quietly dropped — the list
is in [§Corrections](#corrections-to-the-first-version-of-this-record) so the overstatement and its
repair stay visible together.

---

## T1 — statistical primitives · done 2026-11-05, corrected 2026-11-06

`v2/locfinder/measure/stats.py`, `v2/tests/test_stats.py` (**140 tests**).

Exact one-sided Clopper–Pearson bounds in **both** directions, the §8 acceptance rule, the frozen
bootstrap convention, and the exact finite-population and two-stage variance formulas. No design
effect, no effective-sample-size adjustment.

**The decisive test oracle is binomial-tail inversion** — `brentq` on `binom.cdf` — which calls
neither `beta.ppf` nor the implementation, checked across *k* = 0…4, six sample sizes and **three
confidence levels**. Four reviews have now defeated a weaker version of it:

| wrong implementation | what it passed | where it fails now |
|---|---|---|
| `k/n + (1−k/n)(1−0.05^(1/n))` (pass 15) | every zero-event value, both endpoints, monotonicity | 0.009943 vs 0.011804 at *k*=1, *n*=400 — flips the 1% verdict |
| correct except at *k*=1, *n*=400 (pass 18) | all of the above **at a 0.002 tolerance** | the 1e-10 comparison |
| a two-sided *lower* bound (pass 18) | zero endpoint, confidence direction | 0.000102581 vs 0.000050634 at *k*=1, *n*=500 |
| `c* = 0.95 + (c−0.95)/2` in both quantiles (pass 19) | **all 65 tests**, both endpoints, both direction checks | 0.008468733810849356 vs 0.007756994552213629 at *k*=1, *n*=500, *c*=0.90 — PASS to INCONCLUSIVE at θ = 0.8% |

Pass 19's mutant is the most instructive of the four because it is not an exception carved out for
one cell: it is **one wrong formula**, delivering the 92.5% bound for a requested 90% and the 97%
bound for a requested 99%, and it was invisible because every exact fixture used the default level
and the non-default tests checked only *direction*. Its numbers were reproduced here independently
before the fix. The repair is to parametrise both inversion oracles over 0.90/0.95/0.99, build the
mutant in the test file, and check the level reaches `acceptance` and `tolerated_failures`.

A second part of the same finding: **`pytest.approx(x, abs=1e-10)` keeps pytest's default relative
tolerance**, which at an expected 0.8 allows about 8e-7. Eighteen assertions now pass `rel=0`. The
implementation already satisfied the stricter contract — what was wrong was the claim, not the code.

The one-sided confidence domain is now **[0.5, 1)**. Below 0.5 a Clopper–Pearson upper bound can
fall below the observed proportion, and `acceptance(9, 0, 10, 0.8, confidence=0.01)` then satisfied
**both** the PASS and the FAIL predicate — so the documented mutual exclusivity was true at the
frozen 0.95 and not across the accepted domain.

Two tests deliberately record properties that must **not** be asserted: interval width is **not**
monotone in *n* (`[-1,0,1]` → `[-1,1]`; the smaller `[0,0]` → `[0,0]`), and **an all-abstaining
product passes E1** at 0.5974%, which is why coverage is a separately blocked gate and why no
diagnostic may be claimed to prevent it. Pass 19 named two more that must not be asserted and are
not: that a bootstrap endpoint belongs to the input multiset (false under linear quantiles), and
that objective 2's reported time falls when a cheaper destination is added (false, and a conformance
case now records it).

`tolerated_failures` returns **−1**, not 0, when not even zero failures satisfies the threshold —
the unreachable-gate condition revision 2 shipped undetected. Verified: *n* = 298 → −1, *n* = 299
→ 0; and raising the confidence level reaches the same condition, *n* = 500 at 99.9% → −1.

## T2 — sampling frames · done 2026-11-05, corrected 2026-11-06

`v2/locfinder/measure/frames.py`, `v2/tests/test_frames.py` (**30 tests**),
`v2/scripts/build_dev_frames.py`.

**The draw is normative, not just the distribution**, because "simple random sample" does not
identify a sequence:

```
rng = numpy.random.Generator(PCG64(seed))
frame C: cells   = rng.permutation(N_cells)[:n]     # first
         offsets = rng.random((n, 2))               # then, two independent columns
frame B: idx     = rng.permutation(N_population)[:n]
```

`permutation(N)[:n]` rather than `choice(..., replace=False)`, because `choice` picks among internal
algorithms by the *n*/*N* ratio and so is not a specification. Pass 19 confirmed that a full
permutation followed by a prefix **is** an SRS without replacement with uniform ordering of the
selected units, so materialising 512,633 indices is a performance cost and not a sampling defect.

### What pass 19 found the tests were not constraining

**The population was supplied to every draw test, never constructed by one.** No test called
`structure_population`, so the review replaced its stable `argsort` with `np.arange` and **all 17
tests passed**. Projection, centroid computation, boundary filtering and population ordering were
entirely unconstrained. Six tests now build real parquet populations and check:

- the filter is **half-open on all four sides** — `[x_min, x_max) × [y_min, y_max)`, so the west and
  south edges are in and the east and north are out. The `cell_bounds` docstring had claimed the
  opposite convention while the code did this; the arithmetic was right and the prose was wrong;
- centroids are taken **after** projection, via an EPSG:4326 round trip;
- the same unit is selected from a file written in either order. Pass 19's counterexample: ids
  `[b, a]`, PCG64 seed 7 giving `permutation(2) = [0, 1]`, so at *n* = 1 the sorted population picks
  **a** and a file-ordered one picks **b** — the same seed choosing a different structure.

**The cached-population path bypassed the ordering this module claimed.** `build_frame_b(population=…)`
took the caller's order as given, so the module's own statement that frame B is sorted by Overture
`id` before any draw held on one of two entry points: the same grid, seed and source digest returned
**different digests** for two orderings of the same two units. `validate_population` now runs on both
paths and also rejects duplicate ids, mismatched shapes and non-finite coordinates.

**`frozen=True` does not freeze a numpy array.** The review constructed a frame, recorded its digest,
then moved a point 999 m in place: `digest` was unchanged and `write_frame` would have serialised the
moved points under the old identity. A 999 m move can cross a product boundary, so an agreement could
have become the second false inclusion of *n* = 500 — PASS turning INCONCLUSIVE **under the same
recorded frame identity**. Arrays are now copied and made read-only, and the digest is verified both
on construction and before writing.

**The digest was not canonical and was missing two fields.** It omitted `kind` and `crs`, so two
frames with identical arrays differing only in `EPSG:32617` against `EPSG:4326` described different
places on Earth and digested the same. It hashed native-endian float bytes — 1.0 contributes
`000000000000f03f` little-endian and `3ff0000000000000` big-endian — and fixed-width `U64` ids, which
truncate silently past 64 characters. Bytes are now explicitly little-endian with length-delimited
UTF-8 ids, so `("ab","c")` and `("a","bc")` cannot collide.

### The two guards on the draw, described accurately

An **exact-sequence oracle** transcribed from the specification, and a **joint** check on the two
offsets' correlation and quadrant balance. The rejected `(u, u)` implementation selects the *same
cells*, so a cells-only test cannot separate it; it is caught by the exact oracle and by correlation
1.0 against < 0.05.

Pass 19's correction to how this was described: these are **complementary** — one tests the draw
mapping, one tests a pair of statistics — and together they do **not** independently prove joint
uniformity. A uniform angle on a circle also has zero *x*/*y* correlation with balanced quadrants
and zero probability over almost all of a cell. **The exact mapping test is what rejects such a
distribution**, and neither guard touches population construction, which is what the six new tests
above are for.

### Population, verified at build time *and* at the builder

| | measured | design §1 |
|---|---|---|
| building rows | **522,160** | 522,160 ✓ |
| projected centroids inside the 100 m grid | **512,633** | 512,633 ✓ |
| grid | 643 × 514 = 330,502 cells, EPSG:32617 | ✓ |

Both counts are checked in `v2/scripts/build_dev_frames.py` — **which is now tracked**; the first
version of this record claimed a build script enforced them, and pass 19 looked for it and found
none, because it lived in a scratch directory. A one-off assertion outside the repository protects
one invocation and nothing else. The counts are therefore also enforced inside `build_frame_b` via
`expect_population_n`, which is the guard that travels with the code: without it a 500-unit cached
subset is indistinguishable from the full population at the builder boundary, and would be sampled
exhaustively while carrying the real source digest and omitting 512,133 eligible structures.

### Development frame artifacts

Design §10 separates development from certification: these are the **development** frames, their
observations are never substituted for certification estimates, and the **certification draw happens
after the freeze** under §10's registration. They use *n* = 500 — the certification size — so timing
measured on them is the timing certification will cost, and no new allocation is introduced.

`v2/data/` is not tracked, so the digests below are the artifacts' identity in the repository.

| frame | *n* | population | seed | digest | file |
|---|---|---|---|---|---|
| B structures | 500 | 512,633 | 20261105001 | `51a59463d5df4994…` | `frame_b_51a59463.parquet` |
| C area | 500 | 330,502 | 20261105002 | `7914e80ac88eeb10…` | `frame_c_7914e80a.parquet` |

**These supersede the first pair, `93f83cf3…` and `e233ff0f…`, which were digest version 1.** The
frames were rebuilt after the identity fixes above, and the source ids and coordinates are
**bit-identical** across the rebuild — which is the evidence that the ordering fix closed a hole
without moving the sample. Only the digest's byte layout changed. The version-1 files were deleted
rather than kept, since their digest scheme no longer exists.

Source digests: buildings parquet
`96f3690c17a923b06515d6372032111e5eb46063ab2822cdeef76fc1e52ad54c`; frame C's population is the grid
itself, digest `3edbb48d6b99d337fba5953f4767ccb66738b75c904380d0ba9d7ebe2b285cf2`.

Extents, as a sanity check rather than a result: frame C spans x 661,994 – 726,005 and y
3,952,109 – 4,003,445, essentially the whole grid; frame B spans x 663,228 – 725,868 and y
3,952,317 – 4,003,206, narrower because structures do not reach the grid edges.

A frame artifact is **never overwritten** — a new sample is a new digest, so a name collision is an
attempt to rewrite history and raises.

**What the manifest does and does not promise.** It records the grid's parameters — `x_min` 661900,
`y_max` 4003500, 100 m, 643 × 514 — rather than only their hash, because a digest is an identifier
and not the inputs a reader without that grid would need. It records the Python, NumPy and platform
versions and the byte order. It does **not** promise bit-identical regeneration elsewhere:
`numpy.random.Generator` carries an explicit "No Compatibility Guarantee", and PCG64's stream
guarantee does not freeze `permutation`'s internal shuffle. **The saved points are the artifact**; a
redraw is a check to run, not a claim the manifest makes.

## T4 — the conformance suite · done 2026-11-06

`v2/locfinder/measure/toy.py`, `conformance.py`, `conformance_cases.py`,
`v2/tests/test_conformance.py` (**78 tests**). Twelve cases, corpus digest
`b09596d19ed0efe61a3bf8fe5948805d73fd94ee5b25f6048e0ce38eb6a055f6`.

Design §12 artifact 3. The execution plan requires that "derived independently of T3" be
**evidenced, not asserted**, and notes that "written before T3 is complete" is not evidence and a
digest proves immutability rather than correctness. So every case carries three things:

1. **hand arithmetic** with the derivation written out, taken where possible from a review pass's own
   executed counterexample rather than computed now;
2. **the exhaustive oracle's answer** — `toy.py` enumerates every attachment candidate, every entry
   and exit choice and every simple path, then takes the extremum. It has no shortest-path algorithm,
   no spatial index and no "objective view", so design §2.3's hybrid defect is *unrepresentable* in
   it rather than merely absent;
3. **the numbers the case rejects**, as values rather than prose — 16 of them. A case that cannot
   name a wrong answer it separates is evidence of nothing.

**The two routes disagreed once, which is why there are two.** The same-edge competition case was
written with one origin candidate and has **two**: a node origin attaches to every incident edge, all
at distance zero and all inside the tie band. The hand value was wrong and the oracle rejected it.
That is the clearest evidence available that the routes are independent, and it is recorded in the
case's own derivation.

**Building the wrong implementations found a second defect in my own work.** Four are constructed and
shown to be caught — a one-candidate attachment, the forbidden objective-2 functional, a symmetrised
graph, and a penalty charged on entry. The one-way case originally had a **fast** return route, so an
implementation ignoring the one-way flag took the illegal 60 s shortcut, lost to the legal 50 s
route, and returned the **correct** answer: the case separated nothing. Its return route is now slow
enough (240 s legal against the 60 s shortcut) that the illegal path would win.

**The tolerance is argued, not declared.** Pass 18 defeated T1 through a tolerance wide enough to
hide a decision flip, so a small number is not an argument here either. Times are compared at 1e-9 s
— about 70,000× the observed float-association spread of 1.42e-14 s and 11 orders below the smallest
threshold — and every pinned time is additionally checked to give the **same verdict at ±tolerance at
all four published thresholds**. A case whose time sits within a nanosecond of a threshold is
**refused**, not admitted.

Eight of the nine rules in the plan's T3 table have graph cases. The ninth — the independent engine's
connector charge — is **deliberately absent and recorded as absent**, because it depends on
Valhalla's observed correlation position and belongs to T6, where that position is persisted.
Asserting it here would mean inventing the engine's answer. Four further rules are tested without a
graph (bound soundness, `NO_PATH` exhaustiveness, canonical identity, the §7 cross-tab), and a test
asserts that exactly one rule is knowingly untested, so a second gap cannot open silently.

---

## Suite

**576 tests pass**: 328 before S3, plus 140 for T1, 30 for T2 and 78 for T4.

## Not yet built

T3 the reference comparator · T5 diagnostics · T6 the run manifest · T7 development including the
encoding and wire migration · T8 freeze and certify · T9 E3 scoring · T10 the extraction warning ·
T11 the report.

**T3 is gated.** Pass 19's verdict: *"Do not start a purportedly normative T3 until F1 and F2 are
settled."* Design revision 6 settles both — §2.2's candidate universe is now a finite per-segment set
and §2.6 can no longer remove destinations from E1 — so T3 waits on a review of revision 6 rather
than on more design work.

**Still open and owner-gated:** the **coverage requirement** (design §8), which blocks the coverage
claim only — not the build and not the construction gate.

---

## Corrections to the first version of this record

Pass 19 named five statements that claimed more than had been shown. All five are corrected above;
they are listed here because a record that silently repairs its own overstatements teaches nothing.

| the claim | why it was wrong |
|---|---|
| "checked at **1e-10**" | `pytest.approx(x, abs=1e-10)` retains pytest's relative tolerance, so 18 assertions were looser than stated — and exact calibration was checked only at the default confidence |
| "Frame B's population is **sorted by Overture `id` before any draw**" | false on the public cached-population path, which took the caller's order |
| "Both counts are **asserted in the build script**, so a future re-acquisition … fails loudly" | no such script was tracked; it was in a scratch directory, and neither builder enforced the counts |
| "the manifests make each **reproducible** from its source digest, seed and *n*" | frame C's manifest carried a grid hash and not the grid's parameters, and neither NumPy compatibility nor hash byte order was frozen |
| "**Two independent guards**" | they are complementary — a draw-mapping test and a pair of statistics — and neither covers population construction. Zero correlation with balanced quadrants does not establish joint uniformity |

One statement pass 19 examined and **did not** overturn: the recorded **412 tests pass** described
the build environment accurately. The review could not reproduce it because this environment denied
it temporary directories, and it said so rather than treating its own failure as a finding.
