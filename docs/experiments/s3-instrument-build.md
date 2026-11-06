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
`f5ced7a0f1aeab2f776bea9cc90668678e475cfe1a8cbbba14200ee69011608a`
(was `e645be28…` until design revision 9 relabelled the two reading-dependent cases; `case_json` covers each case's justification on purpose, so an annotation edit moves the digest and that is the intended behaviour).

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

## T4's second layer — invariants and a mutation guard · 2026-11-06, corrected after passes 22 and 23

`v2/locfinder/measure/invariants.py`, `mutants.py`, `v2/tests/test_invariants.py` (**457 tests, 433
passing and 24 skipped**), `v2/tests/test_mutants.py` (**31 tests**). 31 scenarios, 14 mutants.

**This exists because pass 21 named the process rather than a rule.** Its diagnosis, after the third
consecutive pass where closing the reviewed defects opened adjacent ones: *"treating repair of the
motivating example as evidence that a replacement rule's domain is settled."* And its
recommendation: *"a compact set of invariants and admissible-input rules exercised across
representations, rather than another claim that the previous named examples now pass."* That is the
resolver lesson arriving from outside, and this was the third round, so it was taken.

The layer declares three things a corpus of cases cannot: **what an admissible input is** (enforced
in the constructors, with scenarios tagged by structural shape), **what must hold of every
admissible input**, and **which re-expressions of one input must give the same answer**.

### What it does not do, measured three times

Passes 22 and 23 were each asked to construct a wrong implementation that passes **both** layers,
which is the question the layer was built to answer. Between them they produced three, and all three
were reproduced here:

| mutant | passed | the dimension nobody had declared |
|---|---|---|
| `<=4`-edge bound on `_simple_paths` (22 F2) | **423/423** | **hop depth** — no scenario needed a journey more than four edges deep |
| `destinations[:4]` in `journeys` (23 F1) | **1,040/1,040** | **destination cardinality** — no oracle call anywhere received more than three |
| orientation forced to 0 outside a coordinate box (23 F4) | **527/527** | **absolute-coordinate dependence of identity** — every identity anchor sat near the origin |

None of them recognises a fixture. Each is a *uniform* reduction, and every answer it does return is
correct — it simply stops looking, or stops looking correctly somewhere nobody looks. The first
violates design §2.5 outright: `NO_PATH` may never be reported from a bounded search.

**The general lesson, which took three instances because I drew it too narrowly the first time.**
After the first I wrote down that *a relative invariant cannot see an absence* — a mutant that
removes journeys reports `None`, the transform comparisons find `None` equal to `None`, and every
per-result check sits behind `objective1_s is not None`. That is true and too specific. A relative
invariant compares two runs, so it also cannot see:

- a **positional truncation**, because both sides of a transform are truncated alike;
- a defect that appears only **far from the origin**, because no near-origin transform reaches it;
- anything the comparison key does not carry.

All three repairs are therefore **absolute anchors**, like the cap and the connector before them:
`CHAIN_DEPTHS` at 2, 4, 5, 7 and 9; five-spoke scenarios with the optimum at each end of the
destination list; and orientation asserted at three coordinate offsets.

The honest statement of what this layer is: it is not evidence that the comparator is right. It is
the thing that keeps establishing that my *rules* are wrong — eleven times now — and it finds a
wrong implementation only on a dimension someone has thought to declare.

### What it found before it was finished

Every time by rejecting something written here rather than the code:

| it rejected | the sharper statement that replaced it |
|---|---|
| "every re-expression preserves everything" | re-expressing one bidirectional edge as two opposed one-ways preserves every **number** and **doubles** the candidate count, because there genuinely are two routing records — so **answers and provenance are invariant under different things**, and §12's equivalence contract is about implementations varying on *one* input |
| "a total is proportional to a uniform weight scale" | a total is **affine**, because the connector does not scale — *and this replacement was itself refuted; see below* |
| "re-expression preserves a time exactly" | exact float equality is a stronger claim than the arithmetic supports. Translating a **curved** geometry 12 km moves a 90.8601039862 s answer by **2.0e-12 s** and subdividing it by **1.4e-14 s**, with every identity unchanged. Every axis-aligned geometry in the first domain hid it |
| "the pass-21 fixes are protected" | **three were not guarded at all.** The orientation bit, the zero-span branch and the route's partial traversals all survived both suites. The absolute anchors exist because the mutation check said so |
| "an empty route means the journey went nowhere" | an empty route is legal when both points attach at one position and all movement is in the connectors — **and** a non-empty route with zero network seconds is legal on a zero-weight edge, which `zero_weight_edge` established within a minute of the first repair. Only the implication survives: an empty route implies zero network seconds |
| "the two layers together are hard to slip past" | a uniform bound on path enumeration passed all 423 tests of both. The gap was a declared **dimension**, not a missing input |

### The affine law, withdrawn

The second row above deserves its own entry, because it is the clearest instance of the pattern the
whole layer exists to break: **proportional → affine → refuted**, each step closing the example that
motivated it and leaving the domain unexamined.

The affine law asserted two things — that a uniform weight scaling leaves the *selection* alone, and
that a total is exactly affine in the scale — and offered the non-negative intercept as proof that
the connectors were present in both objectives' time and cost. Pass-22 F3 refuted all three with one
input. Two bidirectional edges from `(0,0)`: A to `(100,0)` at time/cost 1, B to `(0,-100)` at 20.
Destination A sits at `(100,100)` so it carries a 100 m connector; B's is zero.

| scale | selected | reported |
|---:|---|---:|
| 1 | B | 20 s |
| 3 | B | 60 s |
| 7 | **A** | `7 + 100/1.26` = **86.3650793651 s** |

The connector term that makes a total affine is exactly what gives two journeys different intercepts,
so their lines **cross** and the selection switches. The refuted law would have continued B and
reported 140 s — FAIL where the correct answer is PASS at a 100 s threshold. The slopes it compared,
20 and 6.5912698413, are not equal and were never required to be.

What stands in its place, in `SCALE_LAW`:

- **concavity.** Objective 1's reported time and objective 2's reported cost are each a minimum over
  journeys whose totals are affine in the scale, so each is concave in the scale, with equality
  exactly where the argmin does not switch. Objective 2's reported *time* and objective 1's reported
  *cost* are the other quantity of the selected journey, so they are concave in nothing and are not
  claimed.
- **affinity, conditioned.** A journey held fixed has an affine total, asserted only where the
  selected route and destination are identical at all three scales.

And the intercept argument is gone entirely. **A zero intercept is non-negative and affine**, so no
check of this family could ever have established that a connector was included — and
`EXPECTED_COVERAGE` had recorded the connector-free mutant escaping this layer from the day it was
written. That row *was* the refutation, sitting in my own table, and pass 22 had to point at it. The
connector is now an absolute anchor instead: two destinations, one over a 100 m connector and one
with none, where omitting the connector from cost selects the wrong one and reports 89.3650793651 s
instead of 650 s.

### The measured division of labour

`test_mutants.py` installs each historical wrong implementation and requires some layer to reject
it — the *"verify the guard by reverting the fix"* experiment, run on every test run rather than once.

| mutant | invariants | corpus |
|---|---|---|
| pass-20 F1 connector-free cost | **caught** | **caught** |
| pass-20 F5 strict cap | — | **caught** |
| pass-20 F4 identity-keyed dedup | **caught** | **caught** |
| pass-21 F1 rounded occurrence bucket | **caught** | — |
| pass-21 F4 dropped zero-span branch | **caught** | — |
| pass-21 F5 route without partials | **caught** | — |
| pass-21 F6 rank without cost | **caught** | — |
| pass-21 F7 bit-complemented orientation | **caught** | — |
| pass-22 F2 bounded path enumeration | **caught** | — |
| pass-22 F8 inflated evaluate (sentinel) | **caught** | **caught** |
| pass-23 F1 bounded destinations | **caught** | — |
| pass-23 F4 coordinate-dependent orientation | **caught** | — |
| pass-23 F8 connector-free reported cost | **caught** | **caught** |
| revision-9 per-segment candidate band (withdrawn estimand) | **caught** | — |

**Nine escape the corpus, one escapes the invariants, and every one is caught by the other**, so
neither layer may be dropped and the split is pinned in `EXPECTED_COVERAGE` where a drift in it is
visible. The connector-free cost moved into the invariants when the anchor replaced the intercept
inference. The strict cap is the remaining relative-invariant blind spot and will stay one: a cap
tightened everywhere preserves every relative property, because both sides are equally wrong, so only
an exact-boundary case sees it.

`pass23-F8-connector-free-reported-cost` is not a historical defect. It is a probe of the anchor
that replaced the intercept inference, which claimed to establish the connectors were in both
objectives' time *and* cost and asserted only two of those four numbers — its origin connector was
zero and its objective-2 winner had no destination connector. **The replacement for a withdrawn
overstatement was itself an overstatement**, which is the pattern in its purest form.

**Getting that table right took three harness fixes**, all worth recording because they are easy to
repeat — and the second is the one to remember:

1. A patched module global cannot reach a binding another module imported **by name**, so
   `invariants.py` had to stop holding its own reference to `directed_identity`.
2. **I fixed that one binding and not the others.** Pass-22 F8 patched `toy.evaluate` with a wrapper
   adding 1000 s to every finite time — a 100 s PASS becoming an 1100 s FAIL — and
   `invariant_violations()` returned `[]` while every corpus `check()` stayed clean, because both
   modules still bound `evaluate` at import. Fixing the example instead of the domain, inside the
   module whose entire purpose is not doing that. Both now call through the module attribute, and
   `test_a_sentinel_evaluator_mutation_reaches_both_layers` fails if either ever stops seeing an
   evaluator replacement — without it, every other row of the table measures nothing.
3. The orientation mutant stayed invisible until the domain gained an input whose **selected route
   traverses a palindromic edge backwards**, since the bit flip and the renormalisation agree on
   every other geometry.

### What is recorded as deliberately not an invariant

Objective 2 is **not** monotone in the destination set. A uniform weight scaling does **not**
preserve the selection, and a total is **not** proportional to it. The answer is **not continuous**
in the geometry: 2 mm can move it 899.99 s. And a cost tolerance is **not** decision-irrelevant —
`NOT_PROVEN` says so where the number is used, because a cost never faces a published threshold, only
an argmin, so a competing cost 2e-10 away can flip the selection while a 5e-10 difference passes any
such test.

**Subdivision is not required to preserve the answer, and the exposure is not small.** This record
previously said the measured divergence was "float noise everywhere except a zero-length segment".
That was an observation on 22 scenarios reported as a property of the domain, and pass-22 F5 refuted
it on an ordinary straight edge. One one-way edge `(0,0)→(100,0)` of time/cost **1199.95**, origin
`(49.995,0)`, destination `(100,0)`:

| | candidates | reported | verdict at ten minutes |
|---|---:|---:|---|
| as drawn | 1 | 600.0349975000 s | **FAIL** |
| midpoint `(50,0)` inserted | 2 | 599.9789682540 s | **PASS** |

The inserted vertex puts a clamped segment start **0.005 m** from the origin, inside the 0.01 m tie
band, and it wins. No road changed and no zero-length segment is involved, and raising the weight
amplifies the lost network fraction without any bound from connector speed. The divergence
*signature* across the scenario domain is still a single name, and that signature is checked rather
than the claim.

### The owner's question, settled — and the trade I stated did not exist

§2.2's per-segment candidate rule made the measured value depend on how a polyline was **subdivided**.
The owner adopted the alternative on 2026-11-06; design **revision 9** is the amendment, and §2.2 now
takes the **exact minimum per edge record** before applying the tie band **across** records.

**I put the decision to the owner with a trade that measurement then refuted**, which is the third
time a claim about what a measurement decides has had to be withdrawn after measuring it
(`feedback-computable-property-is-not-the-claim`). I had said per-segment minima "deliver the
equidistant-points-on-one-curve case rather than assuming it". They deliver nothing the exact rule
does not: an exact-minimum filter keeps **every** position achieving the minimum, so a record
doubling back with both arms exactly 1 m out keeps both under either rule and reports the same
**0.7936507937 s**.

What the implemented comparison showed:

| question | measured |
|---|---|
| does the exact rule fix the verdict flip? | yes — 600.0349975000 s both ways, candidates 1 both ways |
| do the two readings disagree anywhere in the scenario domain? | **no**, 0 of 29 |
| does the exact rule keep genuine within-record equidistance? | yes — arclengths 0 and 402 both retained |
| what does the per-segment rule buy on a *near* within-record tie? | a far arm at **9.9 mm** gives 0.8015079365 s and at **10.1 mm** gives 1000.7936507937 s — **a 1000 s jump across 0.2 mm** |
| do the reading-marked conformance cases change? | **no**, both survive unchanged |

So what the superseded rule "protected" on the one input where the two differ was the band's own
discontinuity, not a correct answer. The real decision was amendment surface against a known defect,
and that is how it was put the second time.

**What is still not claimed.** The answer is **not** subdivision-invariant in general. Two residues
remain and neither moves a verdict: subdividing a **zero-length** segment changes the occurrence
count (2→3 on `zero_length_segment`, reported time unchanged at **100.0 s**), and re-expressing a
curved geometry moves the answer **1.4e-14 s**. `measure_split_divergence` reports both; its expected
signature is unchanged by the amendment, which is itself worth noting — the amendment removed a
verdict flip that the *signature* never showed, because `differences` compares seconds at a tolerance
and the flip was 0.056 s on one input outside the domain.

The superseded rule is kept executable as `revision9-per-segment-candidate-band`, because **a
withdrawn estimand needs a guard just as much as a fixed defect does**. It is caught by the
invariants and not by the corpus.

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

**1,113 collected: 1,089 pass and 24 skip.** 328 before S3, plus 140 for T1, 30 for T2, 112 for
T4's corpus, **457 for the invariant layer** (433 passing, 24 skipped), **31 for the mutation
guard**, and 15 for T9.
The skips are the affine law declining to assert where more than one journey exists and the selected
one may legitimately switch — visible, rather than silently asserting something false.

## Not yet built

T3 the reference comparator · T5 diagnostics · T6 the run manifest · T7 development including the
encoding and wire migration · T8 freeze and certify · T10 the extraction warning · T11 the report.

**T3 is gated, and has now been refused four times** — by passes 19, 20, 21 and 22. Each refusal was
for different rules, and each time the new rules were *revisions of the previous refusal's fix*.
Pass 21 stopped describing the rules and described the pattern: *"treating repair of the motivating
example as evidence that a replacement rule's domain is settled."*

The **invariant layer** is the structural answer to that diagnosis, and pass 22's verdict on it is
the one to keep: it makes the evidence requirement more concrete without removing the finish line,
and it had not stopped the pattern. The clearest instance was in the layer itself — proportional →
affine → refuted — and a uniform bound on path enumeration passed all 423 tests of both layers. So
the useful question is still "would anything have noticed", and the honest answer is "on the
dimensions someone has declared".

**What remains before T3 can be frozen**, now naming pass 22's additions rather than discovering them
one pass at a time:

1. **The geometry arithmetic** (F1). Freezing `f × (cost_base + penalty)` as one term froze the
   multiplication and left the *fraction* unfrozen. Segment-length summation, prefix arclength, the
   projection parameter, the traversal fraction, the same-edge interval formula and the
   zero-total-length convention all still decide the exact cost argmin before any `fsum` sees a term.

   **Verified at `eeb22e3` on Python 3.13.1.** On the edge `(0,0),(.1,0),(.1,.2),(.1,.5)` against a
   competitor of cost `1/6`, the current `sum` of segment lengths gives **0.6**, a first-vertex
   fraction of **0.16666666666666669**, and objective 2 reports **1,000 s**. Left accumulation gives
   0.6000000000000001, the costs tie, and the time discriminator reports **1 s**. Both obey the
   frozen multiplication rule, so the finding stands: the rule decides a verdict and is unspecified.

   **Pass 22's proposed repair is backwards, and that settles the amendment.** It suggested replacing
   `length_m` with left accumulation, which is the *less accurate* option. Over the exact rational
   values of those three doubles the true sum is nearer 0.6 than 0.6000000000000001 by a factor of
   three — errors of `1/2**55` against `3/2**55` — so **0.6 is the exactly-rounded sum** and
   `math.fsum` returns it. The 1 s answer left accumulation produces is right only by the accident of
   a tie it creates through being wrong.

   So revision 9 does not choose between arithmetics on which answer reads better. It extends the
   rule §2.4 **already** states for journey totals — exactly-rounded, order-independent summation —
   down into the geometry, which happens to be what the code does and is defensible for the reason
   the existing rule is defensible. The amendment is still required: an implementation accumulating
   left to right conforms to revision 8 and reports a different verdict.
2. **What uniqueness §2.4 promises** (F6). Node simplicity makes the route set finite; it does not
   make a reconstruction unique. On a self-crossing zero-weight edge, direct partial journeys over
   arclengths 25→75, 25→475 and 425→475 — lengths 50, 450 and 50 m — tie on time, cost, destination
   and the one-element identity sequence. That flips T10's boundary-touch between **0% and 100%** for
   one selected route. Either the key gains traversal intervals and a tie convention, or §2.4 states
   the weaker promise and T10 gets its own reconstruction spec.
3. **The admissible numerical domain** (F9). Finite constructor fields are not a domain. **Both
   limbs verified at `eeb22e3`:** a `(0,0)→(1e-200,0)` segment is accepted, underflows to degenerate
   and reports **7.936507936507936e-201 s** where the endpoint-to-endpoint 1,000 s is required — PASS
   against FAIL; and a `1e308` base with a `1e308` penalty validates, totals to `inf`, and raises
   `ValueError: min() iterable argument is empty` instead of returning its promised zero.

   **A third, found while checking and worse than the "no corresponding validation" pass 22
   recorded:** a **NaN origin coordinate is accepted and returns `objective1_s = None`**. Design §2.5
   reads `None` from this oracle as a genuine `NO_PATH`, because the enumeration is unbounded — so an
   invalid query does not raise, it manufactures an authoritative absence. Query coordinates must be
   validated at the boundary rather than left to produce a reportable verdict.
4. **The final cost discriminator** (F10). The oracle ranks by `(time, destination_id, route, cost)`;
   normative §2.4 still stops at the route sequence, so a conforming reader may report a different
   selected cost. Implemented, not amended.
5. **Independently derived decision *and provenance* fixtures** for all of the above, an oracle
   carrying the complete declared observables, frame verification at measurement consumption, and
   the remaining bundle fields.

**None of it changes an owner decision, an allocation or an acceptance threshold.** One item **is**
the owner's, and its stakes changed: see "The owner's question, with its real stakes" above —
subdivision moves a ten-minute verdict on an ordinary straight edge, which is not what this record
previously claimed.

**Still open and owner-gated:** the **coverage requirement** (design §8), which blocks the coverage
claim only — not the build and not the construction gate.

---

## Corrections — what this record claimed and could not show

Twenty-two statements across four versions of this record claimed more than had been shown: five
found by each of passes 19 and 20, seven by pass 22, and five by pass 23. All are corrected above;
they are listed here because a record that silently repairs its own overstatements teaches nothing,
and because the *pattern* is the useful part: **every time, the overstatement was in the section
describing work I had just finished.** Pass 22's seven are in the invariant-layer section written
the same day, exactly as pass 20's four were in the T4 section written the same day — and pass 23's
five are in the **corrections** that answered pass 22.

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

### Pass 22's seven, against the invariant layer written the same day

| the claim | why it was wrong |
|---|---|
| constructors and 22 shapes **declare and enforce** the admissible domain | they exercise selected points. A `1e-200` segment underflows to degenerate, a `1e308` cost pair totals to `inf` and then raises, and query coordinates are never validated. The finite-field check is a necessary condition presented as the domain |
| a total is **affine** in a weight scale, and the non-negative intercept verifies connector inclusion | a *held* journey is affine; the **selection switches**, because connectors give journeys different intercepts and their lines cross. And a zero intercept is non-negative and affine, so the check cannot distinguish a connector from its absence — which `EXPECTED_COVERAGE` had recorded all along |
| a translation preserves orientation, and the compared route **captures the route identity** | orientation is chosen lexicographically on the **rounded** geometry, so an offset can make a geometry palindromic and flip it legitimately. And `_route` drops the node pair and the geometry key, so two different roads of one osmid, orientation and rounded length are indistinguishable in it |
| domain-wide float spread stays under **1e-11 s** | an observation on 22 scenarios. One straight edge of 1,000,000 s with origin `(.1,0)` and destination `(99.9,0)` moves 998000.0000000001 s to 997999.9999999927 s under translation — **7.5e-9 s**, past the 1e-9 tolerance; at 601.2024048096 s it crosses the ten-minute boundary |
| subdivision exposure is **float noise except on a zero-length segment** | also an observation on 22 scenarios. A midpoint on one ordinary straight edge moves 600.0349975000 s to 599.9789682540 s — **FAIL to PASS** — because the inserted vertex's clamped start lands 0.005 m away, inside the tie band |
| the harness **stopped retaining patched names** | `directed_identity` stopped being retained. `evaluate` was still imported by name in **both** layers, so a wrapper adding 1000 s to every journey left `invariant_violations()` returning `[]`. The fix was applied to the example, not the domain |
| the mutation guard answers **"would anything have noticed"** | it answers that for the installed mutations along their actual call paths. A uniform `<=4`-edge bound on path enumeration passed all 423 tests of both layers |

Pass 22 also checked and **did not** overturn: occurrence identity merges adjacent descriptions of
one vertex and keeps non-adjacent repeats, overlapping segments and a ring's 0 and *L* apart;
`0.0` and `-0.0` take the same branch; reverse identity by renormalisation is correct; the
answers/provenance split is right, and so is its stated reason; and all eight then-recorded coverage
pairs reproduce. It qualified two statements rather than refuting them — a palindrome's two
directions share an identity only for a **closed** palindrome, since an open edge with different
endpoint node ids keeps `(u,v)` against `(v,u)`; and candidate counts under `explicit_reverses`
double only for candidates on replaced bidirectional records, so a mixture gives 2→3, not 2→4.

It could not reproduce the full suite: five frame tests error in this environment's pytest temporary
directories with `PermissionError [WinError 5]`, which it reported as an environment limit rather
than a finding.

### Pass 23's five, against the corrections that answered pass 22

This is the sharpest instance of the pattern in the record, because the overstatements are *in the
repairs*. Four replacement rules were written in response to pass 22 and every one had a defect; five
of them rejected correct implementations, which is worse than an escape, because it blocks a correct
T3 and reads as a code defect.

| the claim | why it was wrong |
|---|---|
| the affinity law is correctly conditioned on the selected route and destination holding | neither names the **attachment occurrence**. On `(0,0),(50,0),(100,0)` of time/cost 40 with the origin at `(49.995,0)`, the attachment switches between the exact projection and the next segment's clamped start while the destination stays `"0"` and the route stays one identity — slopes **20.000984126984125 against 20**, nearly a million tolerances apart. The condition is now `n_journeys == 1`, which is exact; and since all six qualifying scenarios have zero connectors, the intercept is a named number rather than an inference |
| a minimum over journeys is concave in the scale, at an absolute 1e-9 | true of the real-arithmetic envelope, not of binary64 observations. One edge of time/cost **100000000.1** reports 100000000.1, 300000000.29999995 and 700000000.6999999, whose chord exceeds the middle by **5.96e-8** — and by 1.99e-8 in exact rational arithmetic over those three outputs, so not an artefact of the chord. The slack is now magnitude-proportional and labelled an **allowance**, pending revision 9's numerical domain |
| `differences` treats a non-finite value as always a difference | it did not. Equality caught two infinities and object identity caught a shared NaN, so an implementation returning the same non-result across representations passed. Putting exact equality first repaired pass-22 F7 and introduced its exact mirror |
| the seconds tolerance is decision-irrelevant, and so is the metre one | the seconds check required a clean `±tol` **neighbourhood**, refusing 600.0000000010021 s against 600.0000000009976 s — 4.5e-12 s apart and both FAIL at every threshold. It now compares the verdict predicates, which is what was needed. And `origin_nearest_m` faces **no** fixed threshold: the tie band is a *relative* gap against the global minimum and the 300 m cap applies to destination residuals, so `NOT_PROVEN` now covers metres as well as cost |
| the connector anchor does what the intercept check was wrongly credited with | it asserted **two of the four** numbers it claimed. Its origin connector was zero and objective 2's winner had no destination connector, so a wrapper replacing `objective1_cost` and `objective2_s` with their network-only values passed it untouched — 603.8095238095 s FAIL becoming 580 s PASS. Replaced by a case with both residuals non-zero asserting all four |

Two further corrections pass 23 made to text rather than to behaviour: `_route`'s stated reason for
dropping the node pair was simply wrong — a reverse traversal of `u→v` and a forward traversal of the
explicitly reversed record both carry `(v, u)`, so that transform does not require discarding them,
and the pair stays dropped as a convenience; and two `toy.py` docstrings still called the route rule
an **equivalence** after the code had been corrected to an implication.

One addition rather than a correction: exposing `network_s` created a new obligation nobody had asked
for. It is not determined by the declared ranking fields, so two winners tying on time, cost,
destination and route can carry decompositions of **1 against 0.9968253968355556** on two records
sharing a rounded identity — and comparing it across representations would make edge order decide a
reported number. It is now out of the cross-representation comparison and the per-result implication
stays. Whether that tie should be broken is design revision 9's item 2, which is also the answer to
pass-22 F6.

Pass 23 also checked and **did not** overturn: the empty-route implication is sound for successfully
evaluated finite journeys, including the same-edge direct candidate and a zero-span traversal;
`network_s` is `compare=False`, absent from `rank_key`, and changes neither ranking nor
deduplication; `_drop_orientation` slices the correct tuple positions; `EXPECTED_COVERAGE` reproduces
in full; and the hop-depth anchors are arithmetically right at their declared depths. It noted that
the chain shape is simultaneously straight, one-way, equal-weight and zero-connector, so those remain
unexercised at depth.
