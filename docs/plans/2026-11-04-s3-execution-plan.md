# S3 execution plan — building the instrument

**Status:** plan, for adversarial review. **Nothing here reports a result.**
**Revision 8, 2026-11-06.** Implements **design revision 8**, which is the operative document —
where this plan and that design differ, the design wins and this plan is wrong.

Pass 19 found ten defects in design revision 5 and the first code, four of them High, and its verdict
was that **T3 is not ready to implement as a frozen reference** until §2.2's candidate domain and
§2.6's eligible population were settled. Design revision 6 settles both. Pass 19 also found two
defects in *this plan*, which revision 5 fixes: T6's persistence list was insufficient to
reconstruct E2, and T8's attempt registration had been reduced to a sentence that an
outcome-selected attempt satisfies. Both were cases of the plan failing to carry a fix the design had
already made, so both are plan corrections rather than new decisions.

Pass 20 then reviewed revision 6 together with T4 and found eleven more, four High, with the same
verdict. Four of its findings were consequences of revision 6's own replacement rules. **Pass 21
then found nine in revision 7, three of them again consequences of revision 7's replacements**, and
refused T3 a third time — but also gave the finish line: a coherent contract for four named items,
independently derived fixtures for them, and an oracle representing the complete declared journey
key. Design revision 8 settles the four.

**Pass 22 refused T3 a fourth time**, and its three High findings were in the *instrument* rather
than the design. Two were invariants that reject correct implementations, including the affine
scaling law written to replace a proportionality that pass 21 had refuted — proportional → affine →
refuted, the pattern running inside the thing built to stop it. The third was the answer to the
question the instrument was built to answer: a **uniform `<=4`-edge bound on path enumeration passed
all 423 tests** of the conformance corpus and the invariant layer together, because hop depth was not
a declared dimension of the domain.

**Pass 23 then reviewed the corrections**, and every one of the four replacement rules written for
pass 22 had a defect — five of them rejecting correct implementations. It also defeated the whole
instrument twice more, by the same mechanism and in dimensions I had not generalised to: a
`destinations[:4]` truncation passed all **1,040** tests because no oracle call anywhere received
more than three destinations, and an orientation rule wrong only outside a coordinate box passed all
**527** because every identity anchor sat near the origin. The reusable conclusion is in the build
record: **a relative invariant cannot see an absence, a positional truncation, or a defect that
appears only far from the origin.** All such repairs are absolute anchors.

**T1, T2, T4 and T9 are built, and T4 now has a second layer.** **1,058 tests pass and 23 skip**: the conformance
corpus, plus an **invariant layer** over the admissible-input domain and a **mutation guard**
asserting every historical wrong implementation is still caught by one of them. Pass 21 asked for
that instrument by name, having diagnosed the repeated adjacent breakage as "treating repair of the
motivating example as evidence that a replacement rule's domain is settled". T4's expected answers
come from hand arithmetic and from an exhaustive enumerator, neither of which calls T3 — a
construction pass 19 independently described as the right one, and which pass 20 confirmed is
adequate evidence of *independence* while being explicit that independence is not coverage. It found
a wrong comparator that passed the whole corpus as it then stood, and pass 22 found one that passed
**both** layers.

**T3 is gated on design revision 9**, which must settle the geometry arithmetic, what uniqueness
§2.4 promises, the admissible numerical domain and the final cost discriminator. The build record's
"Not yet built" section carries the five items with their worked counterexamples.

**Branch:** `v2-rethink`

**What changed in kind.** Revision 2 specified a computation in prose and pass 16 found six High
defects of the form "the prose says X and the code would do Y". But the diagnosis I drew from that —
that fixture-first implementation would have caught them all — did not survive review: *"a program
can faithfully implement each defective instruction"*, and my own bootstrap-widening and E3 fixtures
are examples of fixtures that would have **enforced** a defect. So this plan does not merely move
prose into code. It builds the **five frozen artifacts** of design §12, in which the normative
decision rules stay in the design, the procedure lives in a versioned reference implementation, and
the expected answers come from a conformance suite whose cases are derived **independently** of that
implementation.

**The prohibition that replaces revision 2's slogan.** Revision 2 said "any number this plan appears
to add is a defect", which is untenable — fixture values and implementation references are legitimate
additions. The rule is: **this plan may not change an estimand, an allocation, an acceptance
threshold, an uncertainty convention, or the adaptation and selection policy.** Those require a
design amendment with a §13 row.

---

## 1. Scope

**In:** walk / grocery / Triangle, the 100 m grid, *T* ∈ {10, 15, 25, 45}, frames B and C, E0, E1,
E2, the four diagnostics, the conformance suite, the wire-format migration, and the encoding freeze.

**Out:**

- **drive, bike, transit.** No Triangle-scale layer exists: the walk surface, its reason raster,
  buildings-per-cell and one-way mask are all (514, 643), while every drive, bike and Valhalla layer
  in `v2/data/layers/` is (401, 550) — the earlier slice. The §8 verdict is reported **for walk /
  grocery / Triangle only and named as such**, and the gate re-runs per mode as layers land in S6.
- **walking the E3 journeys** — the owner's. T9 builds ingestion and scoring so the verdict is
  mechanical rather than a hand calculation.
- **setting the coverage requirement** — the owner's. T4 computes and reports E0; design §8 blocks
  only the coverage claim, so nothing here waits on it.
- **any claim about households.** Frame B is a frame of structures.

---

## 2. Tasks

### T1 — `v2/locfinder/measure/stats.py`

**Depends on:** nothing. **Built** 2026-11-05, corrected 2026-11-06 after pass 19. 140 tests.

```python
def clopper_pearson_upper(failures: int, n: int, *, confidence: float = 0.95) -> float
def clopper_pearson_lower(failures: int, n: int, *, confidence: float = 0.95) -> float
def tolerated_failures(n: int, threshold: float, *, confidence: float = 0.95) -> int
def srs_variance(p: float, n: int, N: int) -> float                      # p(1-p)/n * (N-n)/(N-1)
def two_stage_variance(q: np.ndarray, n: int, N: int) -> float           # design §6
def percentile_bootstrap(values, *, replicates: int = 2000, seed: int,
                         statistic=np.median, confidence: float = 0.95
                         ) -> tuple[float, float] | None                # None => not estimable
```

Both directions of the exact bound are required — design §4's screening needs the lower one and
revision 2 specified only the upper. No DEFF, no `effective_n`, no block machinery.

**Tests.** Revision 2's fixtures were the design's zero-event table alone, and pass 15 produced
`k/n + (1 - k/n) * (1 - 0.05 ** (1/n))`, which satisfies every one of them plus the endpoints and
monotonicity while giving **0.9943% at *k* = 1, *n* = 400 against the correct 1.1804%** — enough to
flip an E1b verdict. So:

- **Non-zero fixtures, at least one from a genuinely independent route.** "A declared tolerance"
  placed no limit on the tolerance, and at an absolute tolerance of **0.002** an implementation
  correct everywhere *except* `n=400, k=1` — returning the old defective **0.009943** against the
  correct **0.011804** — passes every stated fixture, both tolerated-count assertions and every
  endpoint check **while flipping the 1% decision**. So:
  - fixtures are stored at full precision and compared at **1e-10 absolute**, not at a tolerance wide
    enough to hide a decision-flipping error — and passed as `rel=0, abs=1e-10`, because
    `pytest.approx(x, abs=...)` retains pytest's default *relative* tolerance and at an expected 0.8
    allows about 8e-7 (pass-19 F3);
  - **every exact fixture is parametrised over the confidence level**, at 0.90, 0.95 and 0.99. With
    the level fixed at the default, one global miscalibration — `c* = 0.95 + (c − 0.95)/2` — passed
    all 65 tests while delivering the 92.5% bound for a requested 90% and the 97% bound for a
    requested 99%, because the non-default tests checked only direction (pass-19 F3). The level is
    also checked to reach `acceptance` and `tolerated_failures`, and the percentile interval's
    **central two-sided** convention is pinned separately from the one-sided bounds;
  - at least one oracle is derived by **binomial-tail inversion** — solving `P(X ≤ k | p) = α` by
    bisection on the binomial CDF — rather than by calling the same `BetaInv` the implementation
    calls;
  - **non-zero lower-bound fixtures** are included, because a mistakenly **two-sided** lower bound
    passes the zero endpoint and confidence-direction checks: at `k=1, n=500` the correct one-sided
    value is **0.000102581** and the two-sided is **0.000050634**;
  - **complementary upper/lower identities** are asserted, e.g. `CP_lower(k, n, c)` against
    `1 − CP_upper(n − k, n, c)`.
- **Two closed forms at zero failures**, independent of the table: exact `1 − α^(1/n)`; and Wilson at
  zero events `z²/(n + z²)` — which is a check on *that* formula, **not** an expected value for the
  Clopper–Pearson function.
- `tolerated_failures(500, 0.01) == 1` and `(500, 0.02) == 4`, pinning design §8's stated
  consequence in code.
- Confidence-level variation at 90% and 99% moves both bounds in the right direction; the lower bound
  is 0.0 at *k* = 0 and the upper is exactly 1.0 at *k* = *n*.
- **The bootstrap is tested in two separable halves**, because a single test conflates percentile
  arithmetic with RNG reproduction:
  1. **percentile calculation on a fixed replicate vector** supplied directly, with no resampling —
    including the case that exposes the convention, 50 zeros and 1,950 ones, whose 0.025 quantile is
    **0.975** by linear interpolation against 0 or 1 under other conventions;
  2. **resampling reproducibility** from a recorded seed, generator and bit generator, with pairing
    preserved.
  **No width-monotonicity assertion** — it is false (`[-1,0,1]` → `[-1,1]`; the smaller `[0,0]` →
  `[0,0]`), and revision 2 required it. Ties are admissible and may give a degenerate interval; an
  empty or single-point domain returns **not estimable**.
- `srs_variance` and `two_stage_variance` against hand-computed values, including the case the wrong
  formula gets wrong: with every cell half erroneous the two-stage variance is `0.25/n` at `n = N`,
  **not zero**.

### T2 — `v2/locfinder/measure/frames.py`, plus frozen artifacts

**Depends on:** T1. **Built** 2026-11-05, corrected 2026-11-06 after pass 19. 30 tests. Development frames `51a59463` (B) and `7914e80a` (C).

Design §1. Two SRSs at ***n* = 500***, digests, never overwritten.

- **Frame B** from `overture_buildings_accepted.parquet`: 522,160 rows, **512,633** projected
  centroids inside the grid — verified, and independently reproduced at pass 17 against the saved
  buildings-per-cell raster.
- **Frame C**: SRS of cells, then one uniform point inside each, **the two offsets drawn
  independently**.

**Tests.** Revision 2's tests admitted centre-only placement; the replacement I wrote then admitted
worse — marginal means and spreads accept `(u, u)` for both offsets, which over 100,000 draws gives
correct marginals (means 49.9574 m, sd 28.8447 m) with **correlation 1**, every point on a diagonal.
So the test is **not** a distributional check on marginals:

- **A deterministic RNG mapping oracle on an enumerated toy grid**: for a fixed seed the exact
  expected (cell, offset) sequence is computed independently and compared element-wise. This is a
  **mapping regression test** — it catches centre-only placement, repeated offsets and row-direction
  errors — but it does **not** establish joint uniformity merely because a second implementation
  emits the same sequence. So it is paired with **independently specified RNG inputs whose two
  offsets are drawn from distinct draws**, asserting the implementation consumes them that way, which
  is what rules out the `(u, u)` diagonal.
- **Enumerated-frame inclusion**: on a toy frame small enough to enumerate, every unit is reachable
  and selection is uniform without replacement.
- Fixed seeds and **declared tolerances** throughout; no "many seeded draws" with an unstated
  parameter.
- **The population is constructed in a test, not supplied to one.** Pass-19 F4: every draw test
  handed in an already ordered synthetic population, so none called `structure_population` and
  deleting its stable sort passed all 17 tests. Real parquet populations now exercise projection
  before centroids, the half-open filter on all four sides, and the same sample from a file written
  in either order.
- **Both entry points enforce the population's order**, since the cached path took the caller's order
  as given and returned two different digests for two orderings of the same two units (F5). The
  frozen counts live on the builder as `expect_population_n`, not only in a build script.
- **The artifact's identity resists its own holder**: arrays are copied read-only and the digest is
  verified on construction and before writing, because `frozen=True` did not stop a 999 m in-place
  move under an unchanged digest (F7). `kind` and `crs` are in the identity, bytes are explicitly
  little-endian and ids length-delimited UTF-8 (F7, F10).
- Frame C points fall inside the cell their flat index names, tested at the **first and last row**,
  since the grid origin is `(x_min, y_max)` = (661900, 4003500) with `y_min` = 3952100 and rows
  running **downward**.
- Same seed reproduces bit-for-bit; the digest changes when any point changes.

### T3 — `v2/locfinder/measure/comparator.py` — the reference implementation

**Depends on:** T2, T4. **The task with the real risk in it, and the one pass 19 refused to
authorise.**

Implements design §2's decision rules. Built **fixture-first**, and the fixtures are T4's, derived
from the design and from the four reviews' counterexamples rather than from this code.

**Four refusals, each over rules that were revisions of the previous refusal's fix.** Pass 19 named
two preconditions: §2.2's candidate domain was a continuum rather than a set, and §2.6 let the
independent engine remove destinations from E1. Revision 6 settled both — and pass 20 found its
*replacements* opened four more: the candidate key merged distinct occurrences and distinct weight
alternatives (F2, F4), closed edges had no directed identity (F3), and cost summation order could
decide a verdict (F7). Revision 7 settled those; pass 21 refuted three of them in turn, and revision
8 settled those. Pass 22 then refused again.

Pass 20's standing instruction is unchanged in form: *"Do not start a purportedly frozen T3 yet.
Ordinary development and the unambiguous fixture subset can proceed."*

**What revision 9 must settle before a freeze**, with the counterexample for each in the build
record's "Not yet built":

1. **The geometry arithmetic.** Revision 8 froze `f × (cost_base + penalty)` as one term and left the
   *fraction* unfrozen. `sum` against left accumulation of one three-segment edge's lengths gives
   0.16666666666666669 against 0.16666666666666666 as the first-vertex fraction, which loses or wins
   a cost argmin and reports **1,000 s or 1 s**. Needs: segment-length summation, prefix arclength,
   the projection parameter, the traversal fraction, the same-edge interval formula, and the
   zero-total-length convention.
2. **What uniqueness §2.4 promises.** Node simplicity makes the route set finite, not a
   reconstruction unique: three direct partial journeys over one zero-weight self-crossing edge tie
   on every declared field at lengths 50, 450 and 50 m, flipping T10's boundary-touch between **0%
   and 100%**. Either traversal intervals and a tie convention enter the key, or §2.4 states the
   weaker promise and T10 gets its own reconstruction spec.
3. **The admissible numerical domain.** Finite fields are not a domain: a `(0,0)→(1e-200,0)` segment
   underflows to degenerate and reports 7.94e-201 s where 1,000 s is required; `1e308` base plus
   `1e308` penalty validates, totals to `inf`, reaches `0*inf` and raises from `min()`. Query
   coordinates are unvalidated.
4. **The final cost discriminator.** `toy.py` ranks by `(time, destination_id, route, cost)`;
   normative §2.4 stops at the route sequence, so a conforming reader may report a different selected
   cost. Implemented, not amended.

The pattern is worth naming, because it has now run four times: closing the blockers opens new ones,
and only an adversarial pass over the fix finds them. Pass 22 showed it running inside the
**instrument** too — the affine law written to replace a refuted proportionality was itself refuted —
and showed that a uniform bound on path enumeration passed all 423 tests of both layers. Pass 23
then found a defect in every one of the four replacements written for pass 22, and defeated the
instrument twice more.

T4's **17 cases** and the oracle in `toy.py` already cover eight of the nine rules below; the ninth,
the independent engine's connector charge, is deliberately absent from the corpus because it depends
on Valhalla's observed correlation position and belongs to T6. Coverage of the *rules* is not
coverage of their domains: five mutants escape the corpus and one escapes the invariant layer.

Required shape, from design §2.3: **objective-specific views, correctly paired, never hybrid** —
sharing immutable geometry and the spatial tree with per-objective weight views, or processing
objectives sequentially. The real index holds **713,452 geometries** whose numeric arrays alone are
**34.2 MB**, so two complete indices are not built; peak memory and build time are measured here.

What this task must get right, each with its conformance case in T4:

| design rule | the defect it closes |
|---|---|
| objective 1 from time-selected views; objective 2 from cost-selected views | a hybrid gives 10.5 or 6 where the answers are 1.5 and 15 |
| the normative **tie rule** (§2.4) | equal-cost coincident alternatives currently return 10 or 1 **on insertion order** |
| partial-edge time, cost and **penalty apportionment**; direction legality | a one-way `u→v` origin at 0.8 cannot reach 0.2 directly |
| same-edge traversal as a **candidate** competing with network routes | a direct 800 s traversal must lose to 100 + 1 + 100 = 201 s |
| destination **eligibility** at 300 m, the eligible set recorded by identity | 549 of 550 eligible under edge attachment |
| bound **metric, strictness, soundness** (§2.5) | a cost limit of 60 on an edge of time 1 / cost 121 must not fail *T* = 60 |
| `NO_PATH` only from an unbounded search | `status.py` requires keyword-only `search_bounded` |
| E2 pairs **cost-`argmin` then its time** on both engines | the wrong functional reports −9 s with identical engines |
| the independent engine's **connectors made explicit** | a ~19 m residual is currently uncharged |

### T4 — the conformance suite

**Depends on:** T1, the design. **Written before T3 is complete, and not derived from it.** **Built** 2026-11-06: `toy.py`, `conformance.py`, `conformance_cases.py`, **17 cases, 112 tests**, corpus digest `e645be28`. Five cases came from pass 20, which found both a strict-cap comparator and a connector-cost defect that passed the original twelve.

**Second layer, same date:** `invariants.py`, `mutants.py`, **427 invariant tests and 29 mutation-guard tests**. 29 scenarios tagged by structural shape, hop depth and destination cardinality, 13 mutants. Eight mutants escape the case corpus and one escapes the invariants, each caught by the other, and `EXPECTED_COVERAGE` pins the split so a drift in it is visible. Three mutants defeated both layers at once when they were written — a bounded path enumeration, a bounded destination list and a coordinate-dependent orientation — which is why `CHAIN_DEPTHS`, the five-spoke scenarios and the multi-offset orientation anchor exist, and why all three are anchored to numbers rather than compared across transforms.

Every cell of design §7's cross-tab, every rule of §2, with **independently derived** expected
answers. Contains every counterexample from passes 15, 16 and 17, plus objective-specific property
checks — which **supplement** exact answers and never replace them, since even monotonicity is
objective-specific: adding a *cheaper* destination correctly raises objective 2's reported time from
10 to 100 s.

The suite is a frozen artifact with a digest (design §12) — and **"derived independently of T3" is
an obligation that must be evidenced, not asserted.** "Written before T3 is complete" is not
evidence, and a digest proves immutability rather than correctness. So each case ships with its
**derivation, its provenance, and a review against the normative quantity in design §2**; where an
expected answer is computed, it is computed by a route that does not call T3.

### T5 — `v2/locfinder/measure/diagnostics.py`

**Depends on:** T2, T3.

Design §4. Four **conditional SRSs from frame B's 512,633-structure population**, A and B drawn **per
threshold** (150 each × 4), D1 and D2 at 200.

- **A excludes `UNKNOWN` verdicts, not `OFF_NETWORK` reasons.** `OFF_NETWORK` is a genuine FAIL
  where its bound exceeds *T* — **2,439 cells at *T* = 10, 298 at *T* = 15** — so those are eligible.
  Revision 2's test asserted the opposite and contradicted the layer contract.
- The **14 `BEYOND_HORIZON` cells 4-adjacent to a passing cell at *T* = 10** are reproduced as a
  cross-check.
- **D1 and D2 audit abstention**: the comparator at an abstaining point either confirms the
  abstention or returns a definitive verdict the product declined to give. The latter is
  **unwarranted abstention**, reported with its own conditional rate and interval.
- The comparison against the population is **descriptive screening**, labelled as such, with
  **zero-reference behaviour defined** and the word "distinguishable" unused.
- Every membership survives routing deduplication.

### T6 — the run manifest and persistence

**Depends on:** T2, T3, T5.

Design §12's final bullet. Revision 2's `PointResult` could not do this: one unkeyed
`product_outcome` cannot represent four thresholds, and `OFF_NETWORK` at 250 m and 1,000 m share a
reason while differing at *T* = 10.

Persisted **per point and per threshold**: product outcome, reason and bounds; per objective, the own
comparator's status, bound metric, strictness and value; the independent engine's status, bound and
horizon; the selected destination and its cost; path references; the origin's access distance **and**
the product cell's own bound, which are different quantities; and every diagnostic membership.

**Pass-19 F9 found this list insufficient**, and the gap is not stylistic: two bundles can satisfy
every field above and still make E2 unrecoverable. With `objective2_own` = 100 s on both and the
independent engine at 100 s in one bundle and 200 s in the other, equal *selected generalised costs*
and no retained raw times leave E2 at **0 s against +100 s** and the `|d| > 60 s` share at **0
against 1**, from rows that each look complete and each show four PASSes. So, additionally required,
and a regeneration test must **fail** a bundle missing any of them:

- **design §12's five numeric values per point and threshold** — objective 1 own, objective 2 own,
  the **float product**, the **decoded encoded product**, and the independent engine's objective 2 —
  never a difference in place of its operands. Revision 5's first attempt at this bullet named the
  two *selected costs* in place of the two product values, which pass-20 F10 caught: two bundles can
  then agree on every listed number and four PASSes while their float/decoded product pairs are
  100/120 s and 200/240 s, making the snapping deviation from objective 1 **0 against 100 s** and the
  encoding deviation **20 against 40 s**, neither recoverable once the source rasters are gone;
- **the two selected generalised costs as well** — ours and the engine's — which are additional
  values, not substitutes for the product pair;
- **both own objective-2 operands** (design §2.1 revision 7): `objective2_own_full_s` over the fixed
  549 for the H2 selection gap, and `objective2_own_intersection_s` over §2.6's intersection for E2,
  each with its own selected destination, cost and status. Keeping one made reconstructed E2 **+990 s**
  or the reconstructed selection gap **990 s** on pass-20 F6's two-destination case — and **only the
  intersection value is ever paired with the engine**;
- **both connector residuals** (ours and the engine's correlation residual), per design §2.6
  revision 6, since E2 is declared inclusive of attachment disagreement and the components must stay
  separable;
- **the retained attachment candidate set** per point, which design §2.2 revision 6 makes part of
  what determines the answer;
- **self-contained path references** — a route identity resolvable from the bundle alone, not a key
  into a graph the bundle does not carry;
- **the E0 census numerators and denominators** by frame, threshold and reason, since §3's area
  census cannot be reconstructed from a digest.

Manifest digests: float, encoded and status rasters; the prepared graph; eligible and selected
destination lists plus **E2's recorded intersection** (§2.6 revision 6); **the independent engine's
tileset, version and costing configuration**; frame artifacts; seeds; code, profile and grid
versions; and the conformance suite.

**Pass-22 F12 found the list still insufficient for the whole report**, not just for E2. The routing
rows can be complete and identical while a *mandatory report result* is undetermined, because T6 says
nothing about the inputs of T9, T10, the diagnostics or the certification history. With an E3
reported time of 300 s, an observed 300 s yields `UNVERIFIED` and an observed 1200 s yields `FAILED`
with a 900 s discrepancy — and neither the observation nor the walked/missing flag is required
anywhere. Implementing the T9 scorer does not persist what it scored. Likewise a retained path 15 m
from the extraction boundary counts under a 20 m band and not under a 10 m band, and route geometry
alone supplies neither the band nor the footprint; saving only surviving paths also loses T10's
denominator.

So the regeneration bundle must additionally require, in T6 or in named companion artifacts, and the
regeneration test must **disable** every source including implicit access to these:

1. **T9's inputs** — journey ids, reported seconds, observed seconds *or* an explicit
   unwalked/missing state, and the scoring configuration and version. Planned journeys are preserved
   as well as completed ones, since a silently dropped plan changes the denominator.
2. **T10's inputs** — the extraction footprint and its CRS, the boundary band width and predicate,
   which objective and population the counted routes come from, point and route membership, missing
   path statuses, and the complete denominator. Either traversal intervals and geometry, or
   sufficient boundary statistics computed under that exact predicate.
3. **The diagnostic screening inputs** — actual frame and stratum memberships with counts, the
   population-reference estimates and counts with their domains, the chosen predicates and
   thresholds, and enough sampling metadata to recover the conditional denominators and the
   empty-stratum behaviour. Sampled memberships cannot reconstruct an omitted population summary.
4. **The certification history** — the independently timestamped registration, the designated
   attempt, the seed-generation, stopping and replacement policy, and every attempt identity and
   outcome **including voided runs**. A successful run manifest alone cannot regenerate the mandatory
   failed-attempt account, which is the whole point of §8's registration.
5. **The analysis configuration itself**, not only its identifiers and digests — units, frame and
   grid specifications, population qualifications, uncertainty and bootstrap settings with seeds, and
   the decoder/lookup version where one is used. Every selected destination, cost, status and
   residual is qualified **by objective and by full-set or intersection population**; "both
   residuals" names each of the origin and destination residual with the journey it belongs to,
   rather than an unqualified aggregate.
6. **Any development figure the report quotes** — the paired grid-comparison observations and their
   configuration, and the phone latency and transfer observations and theirs. Conditional on those
   figures appearing in the report; they are not extra operands for the routing distributions.

**Test:** the report is regenerated from the saved bundle **with routing and the original source
artifacts unavailable**. Revision 2's test would have passed by re-querying a live engine. The test
must also reject a bundle that omits any required value above, because a developer happening to save
extra fields is not the same as the format requiring them.

### T7 — development: everything that can change a measured quantity

**Depends on:** T1–T6. **All of it completes before the freeze** — revision 2 scheduled the encoding
change after certification, violating the design's own freeze.

1. **Conformance suite green** (T4) on constructed fixtures. Branch coverage is never a criterion on
   real data: genuine `NO_PATH` need not occur on the prepared walk graph.
2. **Development sample**, own seed, for shakedown and timing. Its observations are never substituted
   for certification estimates. Success is **complete records** — every value a number or an explicit
   reason-coded absence.
3. **End-to-end benchmark.** Revision 2 estimated 1–3 s per Dijkstra and was 40× pessimistic
   (measured 0.057 s), then used that false premise to authorise an E2 subsample. **E2 is collected
   in full**, and no design change may cite computation before this benchmark exists. The costs to
   measure are graph preparation, both objective views, attachment, cost-path reconstruction, and
   ≈2,600 × 549 ≈ **1.43 M** independent pairs.
4. **Candidate grid comparison (S3.1)** — the same frame-C points against the 200 m grid, holding
   coordinates and destination attachment fixed so only the grid varies. Here, because its outcome
   can influence selection.
5. **The encoding and its wire format (S3.5).** 120 minutes, whole minutes, 121–254 a versioned
   status plane — but **one code per reason is insufficient**, so the format carries the reason plus
   the bound or horizon metadata its verdict needs, and the decoder implements the **verdict and
   combination algebra**. Changed together: writer, exporter, `worker.js`, derived-layer transforms
   and the manifest. Fix the two repository defects in the same change — the exporter discovers only
   `<engine>_<category>_<mode>` and so **omits `own_triangle_grocery_walk.tif`**, and it targets the
   401 × 550 slice while its padding helper scales every non-255 byte as a minute value. Legacy
   dispatch is explicit, because `encode_minutes([121*60, 254*60])` still returns `[121, 254]`.
   Status codes are never interpolated during reprojection.
6. **Browser conformance tested in a browser** (design §8): PASS/FAIL/UNKNOWN decoding,
   known-failure-beats-unknown, threshold and horizon boundaries, recomputation eligibility, every
   failing criterion, and unavailable rendered distinctly from excluded. A Python round-trip cannot
   protect the browser.
7. **Phone decode latency and compressed transfer size** per candidate. Reference: the current
   Triangle walk layer is 174 KB deflated.
8. **Final diagnostic predicates fixed**, since A depends on product verdicts and B on the encoding
   increment, so both move when the encoding does.

### T8 — freeze, then certify

**Depends on:** T7.

**Freeze** the five artifacts of design §12 with frames, allocations, thresholds and analysis. Then:

- **E0 as a census** (design §3) by frame, threshold and reason, on the **frozen published
  representation** — **not** "over every cell", which revision 4 still said and which pass-19 F8
  showed is the wrong partition. The census integrates the frozen `published_lookup` over its
  intersection with the **original projected domain** for frame C, and evaluates **every retained
  centroid** for frame B. In the documented shifted-export case a centre-based original-cell census
  reports **0%** for a cell whose required area answer is **20%**, and a structure in that strip must
  be counted individually whatever its old cell's centre says. The cell sums remain shortcuts, valid
  only once `published_lookup` is shown constant on every original frame cell.
  - This requires that the export **retain its georeferencing, projection, status and bound planes
    and footprint policy**, since none of the census can be computed from a digest. Exterior area is
    `UNKNOWN` and is additionally reported as an **export defect** (design §3 revision 6).
  - It also **recomputes the reference table in design §3**, which was carried from pass 17 and
    cannot be reproduced from the saved rasters because `cell_arrival_with_provenance` computes
    `min_possible_s` without saving it.
  - Any numerical approximation in the area integration has **its error quantified separately**, and
    the result is then not called uncertainty-free.
- **Certification**: an **independent full-frame SRS** at *n* = 500 per frame plus the diagnostics —
  **development points are not excluded from eligibility**, because excluding them would target the
  complement of the development set while claiming all 512,633. Accidental overlap is permitted;
  reusing a development *observation* is not.
- **Attempt registration, which revision 4 reduced to a sentence.** "Every attempt's identity and
  outcome is retained, and one final attempt is prespecified" is satisfied by retaining twenty
  outcomes and *then* naming the first success "final" — which moves the boundary-pass probability
  from **0.0397547** per attempt to **0.5557336** over twenty, and is exactly what design §10's
  registration exists to forbid. Carried over from the design, and binding here:
  - each attempt is **registered before it is drawn**, with an independent timestamp, its seed and
    its intended analysis;
  - the **seed-generation rule, the stopping rule and the replacement rule** are fixed in that
    registration, so "one more attempt" is not available after seeing an outcome;
  - **which attempt is the final one is named before its outcome is known**;
  - every attempt's identity and outcome is retained whether or not it is the final one, and the
    report lists them all.
  At *p* = 0.01 a single attempt meets E1b's count rule with probability 0.0398, which is why
  outcome-selected attempts and prespecified ones are not the same measurement.

### T9 — E3 ingestion and scoring

**Depends on:** T1. **Built** 2026-11-06: `measure/e3.py`, 15 tests.

`score_e3(journeys)` implementing design §3 as a **disjunction**: `failed` if any journey exceeds its
reported time by more than a factor of 1.5 **and** by more than 5 minutes, **or** if the median
signed difference exceeds 25% of the median reported time; otherwise UNVERIFIED, never "supported".

**Tests.** Revision 2's fixture was impossible: it asserted that a journey 1.6× over but only 3
minutes over does not fail, when for a single journey of reported 5 and observed 8 the **median limb
fires** (3 > 25% of 5). So both limbs are tested independently **and** the complete OR is tested on
that singleton; an unwalked record leaves UNVERIFIED and **can never erase a failure** established by
completed journeys.

### T10 — the extraction-truncation diagnostic

**Depends on:** T3.

A **warning diagnostic**, not a bound. Revision 2 claimed boundary-touch share bounds extraction
damage; it cannot — a slow interior path survives while a fast path through outside is gone, giving
**0% boundary touch and 100% affected**. This reports a declared boundary band and a missing-path
denominator. A real bound needs a larger-extract comparison, which is named as the way to get one and
is not attempted here.

### T11 — the report

**Depends on:** T8, **T9 and T10** — the report may not be issued without E3's outcome and the
extraction warning, which revision 3 left able to complete without them.

`docs/experiments/s3-walk-grocery-measurement.md`:

- **E0 by frame, threshold and reason**, as a census with no interval, and the coverage claim marked
  **BLOCKED** pending the owner's requirement.
- **E1a and E1b per frame per *T*** as full-frame joint rates, with point estimate, one-sided 95%
  exact upper bound, and the **tolerated failure count** alongside so a near-miss is legible — and an
  explicit statement that tolerance is **not** power (at true rates 0.001/0.005/0.01 the pass
  probability at *n* = 500 is 90.99%/28.65%/3.98%).
- The §8 verdict for **all eight** frame-by-threshold combinations (1 mode × 4 thresholds × 2
  frames), **none averaged**, together with all **sixteen** directional bounds (8 × 2 directions) —
  and a note that the sixteen are **not** simultaneous 95% bounds.
- The **comparator-unresolved** bucket bounded **in one direction only** per design §7, with
  INCONCLUSIVE declared where the bounds straddle a threshold.
- **Unwarranted abstention** from D1 and D2.
- The **selection gap** (objective 2 − objective 1) as its own signed distribution, since it is
  inside E1 by construction.
- **E2** on its declared jointly-finite domain, per frame, with denominators and a status
  cross-tabulation — never silently dropping pairs — reporting **median, IQR, the bootstrap interval
  and the share with |d| above one encoding increment**, all four.
- **E3's outcome** from T9 and the **extraction warning** from T10, both required.
- Each diagnostic's conditional rate and bound as **descriptive screening**.
- The full manifest, and **run failures** recorded rather than deleted.
- Zero-failure results as **"0 observed, 95% upper bound x%"**, never "0%".

**Acceptance-boundary tests**: the verdict function at exactly the threshold, immediately either
side, and under direction-specific unresolved bounds.

**What the report may not say:** that the layer *set* is construction-verified (one mode); that
**coverage** is certified (blocked); that building *service* is established (both connectors are now
modelled, which is a real advance over the pass-14 nearest-node proxy, but the frame is structures);
that real-world accuracy is supported (E3 returns UNVERIFIED absent a counterexample); or anything
containing the word "household".

---

## 3. What would invalidate this plan

- **The development sample shows rates near 0.5.** The allocations are sized for small rates, which
  is a planning assumption, not evidence. The result says so; re-sizing is a design amendment and
  voids the certification sample.
- **The end-to-end benchmark shows E2 infeasible in full.** Then a subsample is a design amendment
  with its size, frames, diagnostic coverage and interval fixed **before** it is drawn.
- **Coordinate attachment proves intractable** on the real graph — for instance partial-edge
  traversal interacting with the one-way mask. Then owner decision 2 is revisited explicitly rather
  than quietly falling back to snapped nodes.
- **The E0 census differs materially from design §3's carried table.** Then the carried figures were
  wrong and the discrepancy is the finding.
- **The comparator and the surface disagree pervasively rather than at the margins.** E1 doing its
  job: a defect in the pipeline, and S3 stops while S2 reopens.

## 4. What this plan does not do

- It does not change an estimand, an allocation, an acceptance threshold, an uncertainty convention,
  or the adaptation and selection policy. Those are design amendments.
- It does not set the coverage requirement, and does not wait on it.
- It does not schedule the G4 device matrix, the G3 phone render or the G5a household sessions.
