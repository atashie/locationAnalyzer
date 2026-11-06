# S3 instrument build record

**Nothing here is a measurement result.** This records what has been built, with the digests that
identify it, so design §12's frozen-artifact checklist has somewhere to point. The measurement
itself is `s3-walk-grocery-measurement.md`, which does not exist yet.

**Design:** [`2026-11-04-s3-measurement-design.md`](../plans/2026-11-04-s3-measurement-design.md)
revision 8. **Plan:** [`2026-11-04-s3-execution-plan.md`](../plans/2026-11-04-s3-execution-plan.md)
revision 7.

**Ten statements across two versions of this record overstated what had been evidenced** — five found
by Codex pass 19, five by pass 20. Each is corrected in place below rather than quietly dropped, and
the list is in [§Corrections](#corrections--what-this-record-claimed-and-could-not-show) so each
overstatement and its repair stay visible together.

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

## T4 — the conformance suite · done 2026-11-06, corrected the same day after pass 20

`v2/locfinder/measure/toy.py`, `conformance.py`, `conformance_cases.py`,
`v2/tests/test_conformance.py` (**112 tests**). **Seventeen** cases, corpus digest
`e645be289098f2a599cf727110e50b81a430cbcc14772f2405395d5f320e0977`.

Design §12 artifact 3. The execution plan requires that "derived independently of T3" be
**evidenced, not asserted**, and notes that "written before T3 is complete" is not evidence and a
digest proves immutability rather than correctness. So every case carries three things:

1. **hand arithmetic** with the derivation written out, taken where possible from a review pass's own
   executed counterexample rather than computed now;
2. **the exhaustive oracle's answer** — `toy.py` enumerates attachment candidates, entry and exit
   choices and simple paths, then takes the extremum. It has no shortest-path algorithm, no spatial
   index and no "objective view", so design §2.3's hybrid defect is *unrepresentable* in it rather
   than merely absent;
3. **the numbers the case rejects**, as values rather than prose — 23 of them. A case that cannot
   name a wrong answer it separates is evidence of nothing.

**Pass 20 asked the question this suite exists to answer — can a wrong comparator pass the whole
corpus? — and the answer was yes, twice.** That is the most important thing in this section, and the
reason the figures above are larger than the first version's:

- **A strict-cap comparator passed all 78 tests.** `< cap` rather than `<= cap`, executed by
  replacing each cap with its next float down. Every case used 250 m or 350 m and none sat on a
  boundary. On a destination exactly 300 m from the network it finds **no journey at all** where the
  answer is a 338.0952380952 s ten-minute PASS.
- **The oracle itself charged both connectors to objective 2's reported time and omitted them from
  the cost it selects on**, against design §2.1 and §2.2. With destinations at
  `(cost, time) = (10, 10)` carrying a 100 m residual and `(20, 650)` carrying none, the own costs
  are `10 + 100/1.26` = 89.3650793651 and 20, so objective 2 must select the second and report
  **650 s**; omitting the connector selects the first and reports 89.3650793651 s — **FAIL becomes
  PASS**. No case separated it because only *unequal* connectors on *different* destinations can, and
  none had both.

Five cases and three further mutants close those, and the generalisable lesson is recorded: **the
corpus is evidence only of the dimensions it actually varies.** Seven mutants are now built and each
is shown to be killed by a named case — a one-candidate attachment, the forbidden objective-2
functional, a symmetrised graph, a penalty charged on entry, the strict cap, the connector-free cost,
and a text-ordered route rank.

**The two routes disagreed once, which is why there are two.** The same-edge competition case was
written with one origin candidate and has **two**: a node origin attaches to every incident edge, all
at distance zero and all inside the tie band. The hand value was wrong and the oracle rejected it.
Pass 20 independently recalculated all twelve original expected times and found **none of them
arithmetically wrong**, which is evidence about the derivations and not about coverage.

**Building the wrong implementations found two defects in my own work.** The one-way case originally
had a **fast** return route, so an implementation ignoring the one-way flag took the illegal 60 s
shortcut, lost to the legal 50 s route, and returned the **correct** answer: the case separated
nothing. Its return route is now slow enough — 240 s legal against the 60 s shortcut — that the
illegal path would win. And two of my annotations were simply wrong, both found by pass 20: the
multi-segment case's verdicts differ at *T* = 2 min, not the 2.5 min I wrote, where 100 s and 150 s
both pass an inclusive threshold; and the eligibility case does **not** separate "ineligible treated
as unreachable", because a minimum over `{248.4126984127, inf}` is still 248.4126984127 — only the
explicitly checked identity tuples separate that.

**The tolerance is argued, not declared — and its scope is now stated.** Pass 18 defeated T1 through
a tolerance wide enough to hide a decision flip, so a small number is not an argument here either.
Times are compared at 1e-9 s — about **70,400×** the observed float-association spread of 1.42e-14 s
and 11 orders below the smallest threshold — and every pinned time is additionally checked to give
the **same verdict at ±tolerance at all four published thresholds**. A case whose time sits within a
nanosecond of a threshold is **refused**, not admitted.

What that argument does *not* cover, and pass 20 was right to say so: it bounds the oracle-versus-hand
**time** comparison only. It says nothing about cost-argmin stability, cap equality, or selected
provenance — which is why cost totals now use an exactly-rounded sum (design §2.4 revision 7), the
caps have exact-boundary cases, and the selected destination id is asserted directly.

**Coverage, stated honestly.** Every rule in the plan's T3 table has at least one graph case except
the independent engine's connector charge, which is **deliberately absent and recorded as absent**
because it depends on Valhalla's observed correlation position and belongs to T6. Four further rules
are tested without a graph (bound soundness, `NO_PATH` exhaustiveness, canonical identity, the §7
cross-tab). But the coverage *test* inspects a hand-maintained map, so it proves that every name
resolves to a real case and that no case is unclaimed — **bookkeeping, not semantic completeness.**
The strict-cap mutant is the proof that those are different things. Independence from T3 is
established; coverage of §2 is not, and no claim here says otherwise.

## T4's second layer — invariants and a mutation guard · 2026-11-06

`v2/locfinder/measure/invariants.py`, `mutants.py`, `v2/tests/test_invariants.py` (**293 tests**),
`v2/tests/test_mutants.py` (**18 tests**). 22 scenarios, 8 mutants.

**This exists because pass 21 named the process rather than a rule.** Its diagnosis, after the third
consecutive pass where closing the reviewed defects opened adjacent ones: *"treating repair of the
motivating example as evidence that a replacement rule's domain is settled."* And its
recommendation: *"a compact set of invariants and admissible-input rules exercised across
representations, rather than another claim that the previous named examples now pass."* That is the
resolver lesson arriving from outside, and this was the third round, so it was taken.

The layer declares three things a corpus of cases cannot: **what an admissible input is** (enforced
in the constructors, with 22 scenarios tagged by structural shape), **what must hold of every
admissible input**, and **which re-expressions of one input must give the same answer**.

### What it found before it was finished

Four times, and every time by rejecting something written rather than the code:

| it rejected | the sharper statement that replaced it |
|---|---|
| "every re-expression preserves everything" | re-expressing one bidirectional edge as two opposed one-ways preserves every **number** and **doubles** the candidate count, because there genuinely are two routing records — so **answers and provenance are invariant under different things**, and §12's equivalence contract is about implementations varying on *one* input |
| "a total is proportional to a uniform weight scale" | a total is **affine**: `87.9365079365 s` becomes `567.9365079365 s` at ×7, which is `7 × 80 + 7.9365079365`, because the connector does not scale. Three factors pin both coefficients, so **one check verifies the connectors are in both objectives' time *and* cost** — the pass-20 F1 defect that no fixture separated |
| "re-expression preserves a time exactly" | exact float equality is a stronger claim than the arithmetic supports. Translating a **curved** geometry 12 km moves a 90.8601039862 s answer by **2.0e-12 s** and subdividing it by **1.4e-14 s**, with every identity unchanged. Every axis-aligned geometry in the first domain hid it; discrete fields now compare exactly and continuous ones at a decision-irrelevant tolerance |
| "the pass-21 fixes are protected" | **three were not guarded at all.** The orientation bit, the zero-span branch and the route's partial traversals all survived both suites. The absolute anchors exist because the mutation check said so |

### The measured division of labour

`test_mutants.py` installs each historical wrong implementation and requires some layer to reject
it — the *"verify the guard by reverting the fix"* experiment, run on every test run rather than once.

| mutant | invariants | corpus |
|---|---|---|
| pass-20 F1 connector-free cost | — | **caught** |
| pass-20 F5 strict cap | — | **caught** |
| pass-20 F4 identity-keyed dedup | **caught** | **caught** |
| pass-21 F1 rounded occurrence bucket | **caught** | — |
| pass-21 F4 dropped zero-span branch | **caught** | — |
| pass-21 F5 route without partials | **caught** | — |
| pass-21 F6 rank without cost | **caught** | — |
| pass-21 F7 bit-complemented orientation | **caught** | — |

**Five escape the corpus, two escape the invariants, and every one is caught by the other**, so
neither layer may be dropped and the split is pinned in `EXPECTED_COVERAGE` where a drift in it is
visible. A uniformly tightened cap and a uniformly connector-free cost preserve every *relative*
property — both sides are equally wrong — so only an exact-boundary or exact-value case sees them.

**Getting that table right took two harness fixes**, both worth recording because they are easy to
repeat: a patched module global cannot reach a binding another module imported **by name**, so
`invariants.py` had to stop holding its own reference to `directed_identity`; and the orientation
mutant stayed invisible until the domain gained an input whose **selected route traverses a
palindromic edge backwards**, since the bit flip and the renormalisation agree on every other
geometry.

### What is recorded as deliberately not an invariant

Objective 2 is **not** monotone in the destination set. Subdivision is **not** required to preserve
the answer, because §2.2's candidate rule is per segment — measured divergence across the domain is
float noise everywhere except a zero-length segment, where a candidate count changes. And the answer
is **not continuous** in the geometry: 2 mm can move it 899.99 s.

---

## T9 — E3 scoring · done 2026-11-06

`v2/locfinder/measure/e3.py`, `v2/tests/test_e3.py` (**15 tests**). Depends only on T1, so it is
unaffected by the items gating T3.

E3 is the one estimand that can **only** fail. 5–8 owner-chosen journeys are a convenience sample —
with 8 observations and no discrepancy the one-sided 95% bound is **31.2344%** — so the outcome is
`FAILED` or `UNVERIFIED` and there is no third value. The word "supported" appears nowhere, and a
test asserts the enum has exactly two members and that neither contains it.

**Plan revision 2's fixture for the rule was impossible**, which is why the tests are shaped as they
are. It asserted that a journey 1.6× over but only 3 minutes over does not fail. Limb (i) is indeed
quiet — it needs more than 1.5× **and** more than 5 minutes — but for a single journey of reported
5 min and observed 8 min the median signed difference is 3 min against a limit of 1.25 min, so limb
(ii) fires. That singleton is tested as a **failure**, with both limbs' quantities asserted: a
disjunction cannot be fixtured one limb at a time.

Each limb is also tested where only it can fire, and both boundaries are tested as strict — exactly
1.5×, exactly 5 minutes and exactly 25% of the median all pass, and a second past each fails. The
median is **signed**: three journeys 10 minutes early and three 10 minutes late give a median of zero
and must not fail, where a median of absolute differences would read 10 minutes and would.

The one-way rule is tested as one-way. Adding 1, 3 or 20 unwalked journeys to an established failure
keeps it failing, and the medians stay over walked journeys only — counting a missing observation as
a zero difference would dilute a failure away. With no walked journey both medians are `None` rather
than 0.0, because zero would assert the product was accurate.
---

## Suite

**936 tests pass**: 328 before S3, plus 140 for T1, 30 for T2, 112 for T4's corpus, **293 for the
invariant layer**, **18 for the mutation guard**, and 15 for T9.

## Not yet built

T3 the reference comparator · T5 diagnostics · T6 the run manifest · T7 development including the
encoding and wire migration · T8 freeze and certify · T10 the extraction warning · T11 the report.

**T3 is gated, and has now been refused three times** — by passes 19, 20 and 21. Each refusal was
for different rules, and each time the new rules were *revisions of the previous refusal's fix*.
Pass 21 stopped describing the rules and described the pattern: *"treating repair of the motivating
example as evidence that a replacement rule's domain is settled."*

Design revision 8 settles the four items pass 21 named as the finish line, and the **invariant
layer** above is the structural answer to the diagnosis. The useful question is no longer "which
rules are wrong" but "would anything have noticed", and the mutation guard answers it on every run.

Pass 21 also stated what remains, which is worth having written down rather than discovered one pass
at a time: a coherent contract for the four items, independently derived decision and provenance
fixtures for them, an oracle representing the complete declared journey key, frame verification at
measurement consumption, and the remaining bundle fields. **None of it changes an owner decision, an
allocation or an acceptance threshold.**

**One question is the owner's, not mine.** §2.2's per-segment candidate rule makes the measured value
depend on how a polyline is **subdivided**, which the exact per-geometry reading would not. Pass 20
measured the two readings as 599.9747619048 s against 600.0399682540 s on its L-shaped edge — PASS
against FAIL at ten minutes. Across the whole scenario domain the measured divergence is now float
noise everywhere except a zero-length segment, so the exposure looks far smaller than that worked
example suggests. But the data source can re-densify geometries, so the choice is a real one and it
is recorded rather than settled.

**Still open and owner-gated:** the **coverage requirement** (design §8), which blocks the coverage
claim only — not the build and not the construction gate.

---

## Corrections — what this record claimed and could not show

Ten statements across two versions of this record claimed more than had been shown, five found by
each of passes 19 and 20. All are corrected above; they are listed here because a record that
silently repairs its own overstatements teaches nothing, and because the *pattern* is the useful
part: each time, the overstatement was in the section describing work I had just finished.

### Pass 19's five, against the first version

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

### Pass 20's five, against the version written the same day

Pass 20 confirmed the five above were materially repaired, then found five more. Four are in the T4
section I had just written, which is the point worth keeping: a fresh section is not a safer one.

| the claim | why it was wrong |
|---|---|
| "**T4 done**", eight of nine rules covered, exactly one rule knowingly untested | refuted by a strict-cap mutant that passed all 78 tests and by five further semantic gaps. The coverage test inspects a hand-maintained map, so it proves bookkeeping — every name resolves, no case is unclaimed — and not semantic completeness |
| "the exhaustive oracle enumerates **every journey**" | too strong while the candidate key was discarding occurrences and closed-edge directions. Simple paths suffice *numerically*, but only once the candidate and identity domain is right |
| "T3 waits on a review of revision 6, **not on more design work**" | revision 6's replacement rules opened four new design decisions — the candidate key, closed-edge identity, weight grouping and cost arithmetic — all of which had to be made before any freeze |
| the plan's repaired T6 payload | still named the two **selected costs** where design §12's five are objective 1, objective 2 own, the **float product**, the **decoded** product and the independent engine's objective 2 — and §2.6's intersection had meanwhile created a second own objective-2 operand |
| "about **70,000×** the float-association spread" | the ratio is right (70,423), but the claim's *scope* was not stated: it bounds the oracle-versus-hand **time** comparison only, and says nothing about cost-argmin stability, cap equality or selected provenance. A comment inside `conformance.py` also said "~500×", which was simply wrong |

Two further things pass 20 checked and **did not** overturn: the cycle-excision argument for
node-simple paths is sound for both numeric objectives on this model, and the entry/exit enumeration
covers all four directional combinations. It also recalculated all twelve original expected times
independently and found none of them arithmetically wrong — which is evidence about the derivations,
and deliberately not evidence about coverage.

It could not run five frame tests, because this environment denied it temporary directories, and it
said so rather than reporting the failure as a finding.
