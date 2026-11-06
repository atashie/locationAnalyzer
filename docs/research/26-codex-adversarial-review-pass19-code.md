# Adversarial review pass 19 — design 5, plan 4, T1 and T2

Reviewed 2026-11-06 on `v2-rethink`, HEAD `e57fb36`. Repository sources were not edited. Mutations below were compiled into module dictionaries in memory, with bytecode and pytest caching disabled.

**T3 is not ready to implement as a frozen reference.** The statistical implementation is substantially better than the preceding specifications, but the attachment candidate domain and the destination population still admit incompatible answers. T4 can start on the settled rules; it cannot independently derive one correct answer where the specification admits two.

Validation: the unmodified statistical suite passed all 65 tests. Of the frame suite, 17 tests passed and the two persistence tests failed during fixture setup because this environment denied access to pytest temporary directories. An explicit fresh directory under the system temp directory was also denied. Those are environment errors, not demonstrated product failures. I do not claim to have reproduced the build record's full 412-test result. The frame mutation below likewise passed the 17 executable tests; the two persistence tests could not run. Their bodies do not exercise the mutated function.

## Defects, most severe first

### F1 — High: “every attachment within tolerance” does not define the candidate domain

**Location:** design §2.2, lines 121–135; §2.3's geometry/index views; T3/T4.

The text alternates between retaining geometric minimisers and retaining **every attachment whose distance is within 0.01 m of the minimum**. Those are different sets. The latter is usually uncountable, even for one straight edge. Saying “each” equally nearest position on a curve does not specify whether to enumerate exact/local projections, projections onto constituent segments, or the entire tolerance sublevel set.

**Counterexample:** a directed edge from `(0,0)` to `(100,0)`, origin `(0,1)`, destination `(100,0)`, edge time/cost 100,000 s. The nearest projection is `(0,0)`, distance 1 m. A finite nearest-projection interpretation returns

`1/1.26 + 100000 = 100000.793650794 s`.

But `(sqrt(1.01²−1),0) = (0.1417744688,0)` also satisfies the literal tolerance rule. Its connector is 1.01 m and its remaining fractional traversal yields

`1.01/1.26 + (1−0.1417744688/100)*100000 = 99859.027118514 s`.

Both obey a plausible reading of §2.2. The difference is **141.766532280 s**. At 99,900 s they produce FAIL and PASS respectively. The large edge weight makes the difference visible; it can also arise from large apportioned penalties. There is no universal seconds bound obtained by dividing the spatial tolerance by access speed.

**Minimal fix:** define a finite set of projection occurrences, including repeated nearest positions on a polyline, then apply the distance tolerance to that set; alternatively explicitly define and solve the continuous constrained optimisation. State whether segment endpoints and local minima are candidates and how coincident occurrences are deduplicated. These alternatives change answers: **design amendment**, §13 row, new conformance cases, and fresh certification if already drawn.

The residual cutoff discontinuity is separate from the ambiguity. For two disconnected roads of network times 100 and 1,000 s, with origin distances 1 m and 1.009 m and zero destination connectors, retaining the fast second road gives `100 + 1.009/1.26 = 100.800793651 s`. Moving it to 1.011 m excludes it and leaves `1000 + 1/1.26 = 1000.793650794 s`: a **899.992857143 s** jump and a PASS→FAIL at 600 s. A 0.005 m tolerance would exclude the 1.009 m candidate already. Keeping all candidates correctly solves the finite three-road case once the candidate universe is specified; it does not remove cutoff discontinuities. The frozen 0.01 m rule may deliberately accept that discontinuity, but must not be defended as geometric continuity.

### F2 — High: the independent engine can change E1's destination set

**Location:** design §2 destination table, line 91, versus §2.6, lines 268–269.

§2 fixes the own-graph eligible set at **549** and defines eligibility by the 300 m own attachment. §2.6 additionally says an engine-uncorrelatable destination is “excluded from both sides.” It does not restrict “both sides” to the E2 pair. That permits either one shared comparator with an engine-filtered destination set or an E1 comparator retaining the original 549. Those produce different construction-fidelity answers.

**Counterexample:** own graph reaches grocery A in 10 s and B in 1,000 s; both have zero residual and are eligible. Product reports 10 s. The independent engine cannot correlate A. Keeping A for E1 gives comparator 10 s and agreement at 600 s. Removing A from the own comparator gives 1,000 s and a **false inclusion**. In an otherwise clean n=500 sample already containing one false inclusion, this changes `k=1` to `k=2`: **PASS→INCONCLUSIVE** at 1%, since the CP bounds are 0.945228221% and 1.2537605%.

Equal numeric caps also do not imply a shared eligible set: a destination 299 m from the own graph and 301 m from the engine's correlated road passes one cap and fails the other. Correlation failure is not the only exclusion needing a rule.

**Minimal fix:** explicitly preserve the fixed own eligible set for E1 and define a separately identified intersection for E2, including over-cap correlations, or explicitly redefine E1 against the intersection and qualify all 549 claims. The first resolves the conflict in favour of §2's existing E1 definition; the second is a **design amendment** to E1. Record the chosen policy in §13 before drawing certification.

### F3 — High: a globally wrong confidence calibration passes all 65 statistics tests

**Location:** `v2/tests/test_stats.py:74`, `:129`, `:156`; build record's claim of a decisive oracle.

This is a test defect, not an allegation that the current beta formulas are wrong. All exact numerical inversion fixtures use the default confidence. The non-default tests check direction only.

**Executed mutant:** replace confidence `c` by `c* = 0.95 + (c−0.95)/2` in both beta quantiles. In source terms:

```python
# upper
beta.ppf(0.95 + (confidence - 0.95)/2, failures + 1, n - failures)
# lower
beta.ppf(0.05 - (confidence - 0.95)/2, failures, n - failures + 1)
```

**All 65 tests pass.** This is one global wrong formula, not an exception for a chosen `(k,n)`.

**Counterexample:** `k=1,n=500,c=0.90`. Correct upper bound: **0.007756994552214**. Mutant: **0.008468733810849** (the 92.5% bound). At `theta=0.008`, `acceptance(1,0,500,theta,confidence=.90)` changes **PASS→INCONCLUSIVE**. The lower bound likewise changes from **0.000210698831199** to **0.000155910927567**. At nominal 99%, the mutant actually supplies 97% coverage. Current code returns the correct values.

Also, `pytest.approx(expected, abs=1e-10)` retains pytest's default relative tolerance. At expected 0.8 it allows about `8e-7`, not the advertised absolute `1e-10`. The build record's “checked at 1e-10” overstates the assertions.

**Minimal fix:** numerically invert tails at 90%, 95%, 99% for both bounds and test downstream confidence forwarding; use `rel=0, abs=1e-10` where that absolute contract is intended. Add a bootstrap confidence fixture separately, since its confidence is central two-sided. **Implementation/test correction**, no design amendment.

### F4 — High: frame tests never constrain population construction; deleting sorting survives

**Location:** `v2/locfinder/measure/frames.py:150–169`; `v2/tests/test_frames.py:220–266`.

Every frame-B draw test supplies an already ordered synthetic `population`. None calls `structure_population`, so projection, centroid calculation, boundary filtering and population ordering can all be broken without these assertions noticing.

**Executed mutant:** replace

```python
order = np.argsort(ids, kind="stable")
```

with `order = np.arange(len(ids))`. All **17 executable frame tests pass**; the two persistence fixtures have the identical environment limitation described above. Neither persistence test calls `structure_population`, so neither contains a check that can reject this mutant. This differs from the known-bad `(u,u)` draw.

**Counterexample:** a projected file contains IDs `[b,a]` at `[(1001,1991),(1002,1992)]`, both inside the toy grid. PCG64 seed 7 gives `permutation(2)=[0,1]`. At n=1 the correct sorted population selects **a** at `(1002,1992)`; the mutant selects **b** at `(1001,1991)`. Give a a product/comparator agreement and b a false inclusion: the same seed now selects different error observations. At production n=500, replacing one agreement in an otherwise one-error sample changes the 1% construction result **PASS→INCONCLUSIVE**.

**Minimal fix:** test actual population construction using an independently specified small GeoDataFrame/file or a mocked parquet reader; include shuffled IDs, projected centroid values, and all outer boundaries. Verify identical selected IDs after source-row permutation. **Test correction**, no amendment. An actual unsorted population used for certification invalidates that draw's claim to follow the frozen mapping.

### F5 — Medium: cached populations bypass ordering, validation and the claimed count guard

**Location:** `frames.py:172–190`; build record “Population, verified at build time.”

The current unmutated cached path accepts arbitrary IDs/points without sorting or validation. The file path discards `total_rows` at line 178. Neither path asserts the recorded production counts. I found no tracked script in `v2/scripts` containing the advertised frame builder/count assertions.

**Executed counterexample:** supply the two-unit population from F4 in `[b,a]` and `[a,b]` order, with the same grid, n=1, seed=7 and source digest `same`. The current builder selects **b** in the first case and **a** in the second, returning different frame digests. The advertised intrinsic-order invariant holds only on the uncached path. It also happily returns `population_n=2`; neither the expected 522,160 input rows nor 512,633 retained centroids is checked. This tiny frame is legitimate for a unit-test helper, but indistinguishable from an unvalidated production invocation at the builder boundary. A 500-unit cached subset can similarly be sampled exhaustively and labelled as the supplied source while omitting 512,133 eligible structures.

**Minimal fix:** introduce a validated, sorted population artifact carrying source/grid digests and total/in-grid counts; require the production orchestration entry point to check the frozen production identity/counts. Keep generic small-frame helpers for tests. Reject duplicate IDs, mismatched coordinate lengths and non-finite/outside coordinates. **Implementation correction**, no amendment for restoring the existing frame; changing the actual population is an amendment.

### F6 — Medium: adding connectors does not establish E2's claimed common attachment/cost model

**Location:** design §2.6, lines 259–269; E2's “engine disagreement” interpretation.

The own side uses §2.2 candidates; the independent side uses whatever road the engine correlates and then adds its own residual. Equal connector speeds do not make those attachments equal. Moreover, adding a travel-time number directly to an engine's generalised selection cost fixes a cost-scale assumption that is not justified by observing one matrix response.

**Counterexample, attachment:** identical on-road paths take 100 s on both engines. Own residual is 1 m; engine correlation residual is 100 m, both under the cap. The reported values become **100.793650794 s** and **179.365079365 s**, yielding **+78.571428571 s**, crossing the reported `|d|>60 s` criterion with zero on-road engine disagreement. Retaining multiple own attachments while accepting one engine correlation makes this possible even with the same road geometry.

**Counterexample, cost scale:** A has `(cost,time)=(10,10)` and a 100 m connector; B has `(20,20)` and none. Adding `100/1.26=79.365079365` to cost selects B, reporting **20 s**. Another engine with exactly the same path preferences reports generalised costs 1,000 and 2,000 (a positive scaling of the same objective). Adding the same 79.365 selects A, reporting **89.365079365 s**. E2 becomes **69.365079365 s**, again crossing 60 s, solely because the arbitrary internal cost unit changed.

The frozen 1.26 m/s is defensible as an explicitly imposed access model. It is not evidence that this model matches the independent engine's internal walking factors or distance penalties. The raw response must also be checked for connector-related cost already included before another charge is added.

**Minimal fix:** choose and evidence an attachment protocol the engine can actually obey, or explicitly include correlation disagreement in the E2 estimand/label. Specify connector generalised-cost units and conversion relative to each engine's costing configuration, with a scale/change-of-costing fixture and an audit for pre-existing connector charges. **Design amendment** if attachments or connector cost semantics change; correcting only the overstated interpretation needs no new sample.

### F7 — Medium: a frozen dataclass does not freeze the frame, and writes trust stale digests

**Location:** `frames.py:72–86`, `:93–103`, `:197–222`.

`frozen=True` prevents rebinding attributes, not mutations of `points` or `source_ids`. `write_frame` serialises their current contents under the old digest without validating it.

**Executed counterexample:** construct a frame with `points=np.array([[1.,2.]])`, compute its digest, then assign `points[0,0]=1000`. `frame.points` is now `[[1000,2]]`, but `frame.digest` is unchanged and differs from a recomputed digest. The writer will accept that state. A 999 m move can cross a product boundary; if this changes an agreement into the second false inclusion of n=500, the construction result is **PASS→INCONCLUSIVE under the same recorded frame identity**.

The hash also omits `kind` and `crs`. Two directly constructed frames with identical arrays, seed, population size and source digest but CRS `EPSG:32617` versus `EPSG:4326` have the same content digest despite representing different locations. This is relevant because the public constructor accepts those metadata independently.

**Minimal fix:** own/copy and freeze array storage, and recompute/verify a canonical digest at persistence including kind, CRS, shapes and full IDs. Validate loaded artifacts too. **Implementation correction**, no amendment; already-written artifacts need an integrity audit rather than blind trust in their names.

### F8 — Medium: E0's new definition is sound, but the plan still permits the old census and never supplies the footprint rule

**Location:** design §3 E0, especially lines 306–313; execution plan T8 lines 266–269 and T11 line 309.

The design correctly changes frame C to projected area and frame B to centroid evaluations. These are **two different estimands**, not two methods measuring one common abstention rate. That distinction is sound. But T8 still orders a census “over every cell,” and neither document actually supplies the promised outside-exported-footprint verdict. Saying it “is defined explicitly” is not a definition.

**Counterexample, old census:** in the shifted-export example already documented, the second original 100 m cell's centre says PASS while 20% of its area says UNKNOWN. A centre-based original-cell census reports **0%** for that cell; the required projected-area answer is **20%**. A structure in that strip must be counted individually, irrespective of its old cell's centre. This changes E0's reported numerator; a coverage verdict cannot yet be flipped because no coverage threshold exists.

**Counterexample, footprint:** original domain `[0,200]×[0,100]`, exported coverage `[0,160]×[0,100]`, every covered point PASS. Returning UNKNOWN outside yields `E0_C=4000/20000=20%`; treating outside as FAIL yields **0%**. The declarations leave the answer to a later footprint/decoder choice.

**Minimal fix:** T8 must integrate the frozen published lookup over its intersections with the original projected domain and evaluate every retained centroid; retain/export the georeferencing, projection, status/bound planes and footprint policy needed for that calculation. Define the exterior verdict. Persisting the final numerators/denominators is enough to regenerate the report, but a hash alone cannot construct this census. Restoring the already-defined area calculation is an **implementation/plan correction**; selecting previously unspecified footprint behaviour is a **design amendment**. Approximation error must be separately quantified as §3 already requires.

### F9 — Medium: plan revision 4 omits revision 5's decisive persistence and registration requirements

**Location:** execution plan T6 lines 212–222, T8 lines 274–276; design §§10 and 12.

T6 still lists statuses, bounds, path references and selected costs without requiring all five numeric values, the retained attachment candidate set, self-contained path references/sufficient statistics, or explicit E0 census totals. T8's “one final attempt is prespecified” omits the independently timestamped registration and seed-generation/stopping/replacement policy that revision 5 introduced precisely because that sentence was inadequate.

**Counterexample, persistence:** two saved runs can satisfy T6's listed status/verdict fields and have all four thresholds PASS while one has `objective2_own=100, independent=100` and the other `objective2_own=100, independent=200`. With equal generalised selected costs and no retained raw times, E2 is **0 versus +100 s** and the `|d|>60` share is **0 versus 1**, unrecoverable from the specified rows. A test requiring report regeneration must fail such a bundle, regardless of whether a developer happened to save extra fields.

**Counterexample, registration:** retaining twenty outcomes and naming the first successful attempt “final” satisfies the plan's weak recordkeeping interpretation while moving boundary-pass probability from **0.0397547** per attempt to **0.5557336** over twenty. This is exactly the policy revision 5 disallows. No code is yet alleged to implement that policy; the executable task list simply fails to carry the fix.

**Minimal fix:** copy the concrete payload and pre-outcome registration obligations into T6/T8 and their acceptance checks. The design wins, so this is a **plan correction**, not a new design decision. Any later change to the registered selection policy is an amendment and cannot retroactively validate an outcome-selected attempt.

### F10 — Medium: RNG calls plus a seed are not the promised portable artifact identity

**Location:** `frames.py:93–103`, `:219–222`; test `test_the_manifest_records_what_is_needed_to_redraw_the_frame`; build record's reproducibility claim.

The manifest records PCG64 and call names but no NumPy version/platform/int-width contract or grid specification for C, only its hash. The installed NumPy **2.5.4** `Generator` docstring explicitly says “No Compatibility Guarantee” and that Generator does not provide a version compatibility guarantee. The PCG64 bit-generator guarantee does not automatically freeze `Generator.permutation`'s bounded-integer/shuffle implementation.

There is also an immediate byte-order counterexample independent of a future NumPy change: `_digest_points` hashes native `float64` and native `U64` memory. Float 1.0 contributes bytes **`000000000000f03f`** on little endian versus **`3ff0000000000000`** on big endian. Thus identical numeric points/IDs can receive different frame identities on another byte order. The existing source hash does not repair native-endian point serialization.

**Concrete consequence:** the recorded production seed's first C point here is cell **138767**, `(714120.22369282,3981967.85907658)`. These numeric values can be identical after moving the saved artifact to another architecture yet fail native-byte digest recomputation. Conversely, a seed plus a grid hash does not reveal `x_min=661900,y_max=4003500,cell=100,ncols=643,nrows=514` to a reader who no longer has that grid. A digest is an identifier, not those missing inputs.

**Minimal fix:** make saved arrays the authoritative draw; record full grid/population ordering identity, NumPy/runtime details and explicit integer/draw conventions for redraw checks. Canonicalise hash bytes, for example explicit little-endian floats and length-delimited UTF-8 IDs. Do not promise cross-version regeneration without a frozen shuffle algorithm. **Implementation/provenance correction**; changing the draw algorithm is a **design amendment**.

## T3 readiness: remaining rules with more than one answer

Do not start a purportedly normative T3 until F1 and F2 are settled. Development prototypes and the unambiguous fixture subset can proceed.

* **§2.2 candidate universe:** exact per-geometry minima, local/segment minima, and all positions in the tolerance band produce different fractional traversals (F1). This also determines whether candidate sets can be persisted finitely. Two edges of the same road must be treated as projection occurrences with a declared deduplication rule, not arbitrarily reduced to the first Shapely projection.
* **§2/§2.6 eligible population:** fixed own 549 versus the independent-engine intersection changes E1 (F2). An over-cap engine correlation also needs the same explicit intersection policy as an absent correlation.
* **§2.6 attachment and connector costs:** an imposed engine correlation versus the own retained candidates is not a common attachment; connector cost requires an explicit conversion/audited request configuration (F6). If the intended quantity deliberately includes these differences, name it and make those request/configuration inputs part of the frozen definition.
* **§2.4 recorded identity ties:** two different destination IDs at identical coordinates, with identical cost/time/route, tie on every listed edge key. Either selected destination can be recorded. Numeric answers agree, but “the fourth key makes the order total” is not true for the selected-destination identity. Specify destination ID and, where needed, an ordering of full route-identity sequences as final provenance keys. This is a provenance ambiguity, not an additional numeric defect.

The 200/300 m caps should filter each retained candidate; a nearest origin candidate at 199.995 m does not authorise a second at 200.004 m merely because it is within the geometric tie band. Test that explicitly. An empty eligible attachment set needs an explicit status/bound rather than `min([])`; when a nearest graph edge exists beyond the cap its distance can support the stated OFF_NETWORK bound. When the graph itself is empty, do not invent such a distance or call a bounded search exhaustive.

## T4: independent derivation for each of the nine T3 rules

| T3 rule | Independent expected answer and present limitation |
|---|---|
| Objective-specific views | **Yes.** Enumerate all legal paths on a tiny multigraph using original edge identities, separately sum time/cost, and minimise lexicographically. The documented consecutive-segment fixture gives 1.5 s and 15 s without any T3 call. Do not reuse T3's collapsed index. |
| Normative tie rule | **Partly.** Edge-level equal-cost times 10/1 have independent answer 1. Enumerated full routes can prove numerical ties. F1's attachment domain and the missing destination/full-route identity ordering must be settled before a unique expected provenance answer exists. Otherwise test an explicitly allowed set of identities and the unique numeric result. |
| Partial edge, penalties, direction | **Yes.** Hand fractions: 1% of an edge with time 1 and cost 121 contributes time 0.01 and cost 1.21. A one-way 0.8→0.2 traversal is illegal. Enumerate other legal paths rather than assuming NO_PATH. |
| Same-edge competition | **Yes.** Enumerate the direct 800 s candidate and the 100+1+100=201 s bypass. Expected minimum 201 s is arithmetic, independent of routing code. |
| Eligibility at 300 m | **Partly.** Synthetic residuals 299.99/300/300.01 independently give eligible/eligible/ineligible for a single specified graph. The real claim 549/550 requires a separate geometry calculation and IDs; it cannot be proved by a T3 output or a row count. The shared-engine set awaits F2. |
| Bound metric, strictness, soundness | **Yes on constructed graphs.** Enumerate a 1 s/cost 121 path under cost limit 60: a cost cutoff cannot establish failure at time 60. Check non-strict L=T versus strict L=T independently against explicit reachable times. |
| NO_PATH only unbounded | **Yes.** An independently enumerated disconnected graph proves absence; a route of 210 s beyond a 60 s cutoff proves the bounded result must not be NO_PATH. A real engine's non-result cannot independently establish exhaustiveness without an engine/API guarantee. |
| E2 cost-argmin then time | **Yes given complete pair values.** On `(cost,time)=(10,10),(100,1)`, choose 10 s on each side and d=0, not −9. An independent enumerator or separately captured matrix response is the oracle; T3 must not generate its own expected matrix. |
| Independent engine connectors | **Partly.** Given correlation positions and declared cost conversion, Euclidean residual/1.26 and pair re-ranking are hand-computable (A→B gives 20 s in the design's example). A raw 448 s response at two nearby inputs does not establish universally absent connector costs or enforceable common correlation. Freeze/evidence the protocol first; until then use stubbed responses for arithmetic and label live checks as integration evidence, not independent ground truth. |

Each expected result should carry its derivation and original fixture inputs. “Written first” and a digest remain insufficient evidence of independent correctness.

## Checks that survived, and edge limitations

* Current CP upper/lower formulas implement §6. At n=500, k=0 upper is **0.005973551516349557**; at k=n upper is 1 and lower is **0.9940264484836504**. `tolerated_failures(298,.01)=-1`, `(299,.01)=0`, `(500,.01)=1`, `(500,.02)=4`. These fixes survive.
* At the frozen confidence 0.95, valid integer counts with `k+u<=n` have exhaustive, disjoint acceptance branches: CP upper is at least the observed proportion, so PASS precludes identified FAIL; otherwise the `else` covers the remainder. `k+u>n` raises. An all-abstaining product passes at **0.5973551516%**, consistent with the rounded 0.5974% claim.
* The public confidence API is wider than that proof: `acceptance(9,0,10,.8,confidence=.01)` returns PASS because upper=`0.6309573444801932`, even though `9/10>.8` also satisfies the documented FAIL predicate. This is outside frozen S3's 95% use, so I do not count it as a certification blocker. Restrict this helper to its intended confidence domain or define branch precedence for the broader API; do not claim mutual exclusivity at every accepted confidence.
* Confidence semantics are coherent **when named by interval type**: CP, tolerated counts and acceptance use a one-sided level; percentile interval/bootstrap use central two-sided coverage. On replicate values 0…100, 95% gives `[2.5,97.5]`, not `[5,95]`. These are deliberately different tail conventions, not a current implementation mix-up. Non-default calibration remains untested (F3).
* `srs_variance` is correct on its declared `N>=2` domain and zero at n=N. Both variance functions reject N=1. Mathematically a one-unit fixed binary census has variance 0 and a one-cell uniform-point experiment with q=.5 has variance .25; those cases are unsupported, rather than numerically implemented. A general-purpose one-cell extension should branch before the `N−1` division.
* `two_stage_variance` has the correct uncorrected within-cell term: all q=.5 gives `.25/n` even at n=N. Add a mixed fractional q fixture, e.g. q=`[.25,.75]`, n=1,N=2: between=.125, within=.1875, answer **.25**; current code gets it right.
* Bootstrap constants match §6: 2,000, PCG64, median, replacement, linear central percentiles. Empty/singleton **input domains** return None; degenerate multi-point domains may yield zero width. `percentile_interval([7])=(7,7)` is appropriate for its separate task of taking quantiles of already supplied replicate statistics. The design's domain restriction belongs on `percentile_bootstrap`, where it exists.
* The two deliberate counterproperties are correct: bootstrap width need not grow when n shrinks, and construction fidelity need not penalise abstention. Also do not assert sample identity is independent of supplied cached ordering (currently false), objective-2 reported time decreases when a cheaper destination is added (false), or bootstrap endpoints must always belong to the input multiset (false with linear quantiles). The current three-value pairing example happens to satisfy the last property; it does not establish pairing in general.
* A full random permutation followed by a prefix **is SRS without replacement**, with uniform ordering of the selected units. Materialising 512,633 or 330,502 indices is a performance cost, not a sampling defect.
* Production cell arithmetic is correct: first bounds `(661900,4003400,662000,4003500)`; last flat index **330501**, row 513/col 642, bounds `(726100,3952100,726200,3952200)`. The structure filter consistently uses `[x_min,x_max)×[y_min,y_max)`. The `cell_bounds` docstring's `(y0,y1]` convention disagrees with this and the draw's `[y0,y1)` convention. This is a boundary-documentation defect, not an interior arithmetic error; explicitly choose the published raster lookup's boundary convention for discrete centroids.
* The off-network correction survives: division by 1.40 gives the 840/1260/2100/3780 m strict cutoffs. Using 1.26 would be a different, tighter model bound and would change E0; do not silently substitute it. I did not reroute the entire production graph to remeasure the carried counts.

## Build record statements that overstate what is evidenced

1. **“checked at 1e-10”** — pytest's retained relative tolerance weakens this contract, and exact calibration is checked only at default confidence (F3).
2. **“Frame B's population is sorted by Overture id before any draw”** — false for the public cached-population path (F5).
3. **“Both counts are asserted in the build script, so a future re-acquisition that changes them fails loudly rather than silently redefining the frame.”** — no such tracked script was found; neither builder enforces it. A one-off build-time assertion cannot protect another construction path (F5).
4. **“the manifests make each reproducible from its source digest, seed and n”** — C's manifest has a grid hash rather than the grid parameters, and neither NumPy compatibility nor canonical hash byte order is frozen (F10). Saved point artifacts are much stronger evidence than this redraw promise.
5. **“Two independent guards”** — they are complementary tests of the draw mapping and one joint statistic. Near-zero correlation plus quadrant balance does not independently prove joint uniformity, and neither guard covers population construction. For example, a uniform angle on a circle has zero x/y correlation and balanced quadrants but zero probability on almost all cell area. The exact mapping test is what rejects that distribution here.

The recorded **412 tests pass** may accurately describe the original build environment; my temporary-directory failures do not refute it. They also do not validate the stronger correctness or freeze claims above. No measurement or certification result has yet been built, and the record correctly says so.
