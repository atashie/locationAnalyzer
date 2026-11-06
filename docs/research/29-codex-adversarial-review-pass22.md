# Adversarial review pass 22 — revision 8 and the instrument

Reviewed HEAD `0a81ed3`, 2026-11-06. The checkout reports branch `oneoff/gnv-chapelhill-trip`, rather than the prompt's `v2-rethink`; I reviewed the files at the requested HEAD without switching branches. Only this review was written. All mutations below were in memory, in separate Python processes, with bytecode and pytest cache writes disabled.

**The instrument is useful but not adequate evidence for freezing T3.** A systematic wrong path enumerator passes all **423 tests** in the conformance, invariant and mutation-guard files together. Several purported domain invariants also reject correct answers. Revision 8 still permits a **1 s versus 1,000 s** objective-2 disagreement from geometry arithmetic.

## P22-F1 — High — frozen weight terms still receive an unfrozen geometry fraction

**Location:** design §2.4 item 6; `toy.py:ToyEdge.length_m`, `nearest_on_graph`, `_same_edge_direct`.

The new multiplication rule repairs the particular base/penalty reassociation. It does not specify segment-length summation, prefix arclength, projection arithmetic, or how an interval becomes its traversal fraction. Those quantities can decide the exact cost argmin before the final `fsum` sees any terms.

**Executed counterexample:** two one-way edges from node 0:

| edge | geometry | time | base cost | penalty |
|---|---|---:|---:|---:|
| A, 0→1 | `(0,0),(.1,0),(.1,.2),(.1,.5)` | 6 | 1 | 0 |
| B, 0→2 | `(0,0),(.1,0)` | 1000 | `1/6` | 0 |

Origin `(0,0)`, destination `(.1,0)`. The shared coordinate is A's interior vertex and B's endpoint, which the graph accepts.

On Python **3.13.1**, the current `sum` of A's segment lengths returns **0.6**. Its first-vertex fraction is **0.16666666666666669**, exceeding B's cost **0.16666666666666666**. Objective 2 selects B and reports **1,000 s**, FAIL at ten minutes.

Replacing only `length_m` with explicit left accumulation gives **0.6000000000000001**. The fraction becomes **0.16666666666666666**. The costs tie, so the time discriminator selects A at **1 s**, PASS. Both versions form `f * (cost_base + penalty)` as one term and exactly sum the resulting journey terms. This is not a violation of the newly frozen multiplication rule.

**Minimal fix — design amendment:** specify the arithmetic producing lengths, prefix lengths, segment parameters and traversal fractions, including the zero-total-length convention. Specify the same-edge interval formula, such as the chosen operation sequence for `abs(f_destination - f_origin)`, rather than relying on mathematical equivalence. Independently derive a decision fixture for the chosen result.

For fixed fractions, the direct candidate can contribute one network term and two connector terms; endpoint candidates can contribute their individual partial/full traversal terms. The zero-span identity convention can omit the identity and contribute zero numerically. The new rule is useful at that stage; it does not settle the fractions supplied to it.

## P22-F2 — High — a bounded path enumerator passes both complete test layers

**Location:** `invariants.py:SCENARIOS`; conformance corpus; `toy.py:_simple_paths`; `test_mutants.py`.

Installed before importing the test modules:

```python
real = toy._simple_paths
def wrong(graph, start, goal):
    return [p for p in real(graph, start, goal) if len(p[2]) <= 4]
toy._simple_paths = wrong
```

**Result:** all **423 tests pass**: 112 conformance, 293 invariants, 18 mutation guards. `invariant_violations()` and the corpus's `check()` also both return empty failure lists. This mutation is a uniform, unconditional path-length cutoff, not a branch recognizing a fixture.

**Executed distinguishing shape: a long directed chain with more intervening hops than any exercised journey.** Seven one-way edges `i→i+1`, geometries `(100*i,0)→(100*(i+1),0)`, each time/cost **80**, origin `(0,0)`, destination `(700,0)`. Both connectors are zero. Correct exhaustive evaluation returns **560 s**, PASS at ten minutes. Entry and exit consume the first and last edges, leaving **five** intervening edges; the mutant discards that path and reports no journey. Interpreting its empty enumeration as exhaustive `NO_PATH` gives FAIL, contrary to §2.5.

No relative representation transform adds the missing hop depth. None of the absolute anchors establishes reachability on this shape.

**Minimal fix — instrument correction, no semantic amendment:** add a parameterized chain family crossing the relevant path-depth boundaries, with independently calculated totals and reachability. Include a mutation distinguishing bounded exhaustion from exhaustive absence. State the coverage dimensions actually exercised; 22 scenarios are a finite sample of the domain, not the domain itself.

## P22-F3 — High — the replacement affine invariant is false for selected answers

**Location:** `invariants.py:scale_weights`, `invariant_violations`; `test_invariants.py:test_scaling_every_weight_leaves_the_selection_alone`, `test_a_total_is_exactly_affine_in_the_weight_scale`; build record's affine-law claim; design §13 revision 8.

A **fixed journey** has an affine real-arithmetic total in the weight scale. The selected journey need not stay fixed. Its network slope competes with other journeys' different connector intercepts. Even the fixed-journey binary64 result need not be exactly affine because multiplication and summation round.

**Executed counterexample:** two bidirectional edges from `(0,0)`, A to `(100,0)` with time/cost **1**, B to `(0,-100)` with time/cost **20**. Destinations are `(100,100)` and `(0,-100)`. A's destination connector is **100 m**, B's is zero. At scales 1, 3 and 7 the two objectives correctly report:

| scale | winning destination | total seconds/cost |
|---:|---|---:|
| 1 | B | 20 |
| 3 | B | 60 |
| 7 | A | `7 + 100/1.26 = 86.36507936507937` |

The tested slopes are **20** and **6.591269841269842**, not equal. The destination-selection assertion also fails. At scale 7, continuing B as a supposed scale-invariant selection reports **140 s**, rather than **86.3651 s**, flipping FAIL to PASS at a 100 s decision threshold.

The minimum-time value is a lower envelope of journey totals, piecewise affine in exact arithmetic; objective 2's reported time can additionally jump when its cost-selected journey changes. The asserted universal affine law and selection invariance are not implied by §2.

The claimed connector guarantee is also contradicted by the instrument's own coverage table: the connector-free-cost mutant passes this invariant layer. A zero intercept is nonnegative and affine, so these conditions cannot establish that a connector was included.

**Minimal fix — instrument correction:** test affine behavior on an explicitly held journey, or under a demonstrated stable-selection condition, with an arithmetic error allowance. For selection over journeys, test the actual envelope/argmin behavior. Retain absolute unequal-connector cost checks. No design change is needed to permit the correct switch; amend the contrary claims in §13 and the build record.

## P22-F4 — Medium — two other universal invariants assert rules the design does not give

**Location:** `invariants.py:_route`, `translate`, the nonempty-route check in `invariant_violations`; `test_invariants.py:test_a_selected_route_is_a_legal_traversal_of_this_graph`.

**Connector-only movement:** one bidirectional edge `(0,0)→(100,0)`, time/cost **1000**, origin `(50,1)`, destination `(50,2)`. Both attach at arclength 50. Correct evaluation returns **`3/1.26 = 2.380952380952381 s`**, with **empty network route**. The coordinates differ, but all movement is in the two connectors. The invariant rejects this legal PASS as a route defect. The design's zero-span convention permits exactly this result.

**Rounded orientation under translation:** one bidirectional edge `0→1`, geometry `(.003,0),(.006,0)`, time/cost **1000**; origin `(.006,0)`, destination `(.003,0)`. Before translation its reverse route has orientation **1**. After the supplied translation by `(12345.678,-98765.432)`, both endpoint x coordinates round to **12345.68**, making the rounded geometry palindromic and orientation **0**. Time remains **1000 s**. `_route` reports `(1,(),0.0)` versus `(0,(),0.0)` and rejects the transform. Monotonicity of addition does not prove preservation of a lexicographic choice made **after rounding**.

**Minimal fix — instrument correction:** require a network identity only when the selected journey has nonzero network traversal, using actual attachment/traversal information. Compare translated routes through a transform-specific correspondence, or restrict translations to a verified identity-preserving domain. Neither universal assertion should become a new design policy accidentally.

## P22-F5 — Medium — a midpoint changes a ten-minute verdict on an ordinary straight edge

**Location:** design §13 revision 8's subdivision exposure; `invariants.py:measure_split_divergence`; build record's owner-question and measured-exposure paragraphs.

**Executed counterexample:** one one-way edge `(0,0)→(100,0)`, time/cost **1199.95**, origin `(49.995,0)`, destination `(100,0)`.

Without subdivision, the origin has one candidate, arclength **49.995**, residual zero. Time is **600.0349975000001 s**, FAIL at ten minutes.

Insert the midpoint `(50,0)`. The second segment now contributes its clamped start as another candidate, only **0.005 m** from the origin and within the 0.01 m band. It gives **`0.5*1199.95 + .005/1.26 = 599.9789682539683 s`**, PASS. Candidate count changes **1→2**. This is not a zero-length segment or floating noise. Increasing weights can amplify the lost network fraction without a uniform bound from connector speed.

This behavior follows the declared per-segment rule. The defect is extrapolating the observations on 22 chosen scenarios into an exposure assessment for the admissible domain. The earlier L-shaped comparison of two readings is also not itself a measurement of subdivision exposure on one geometry.

**Minimal fix — record/instrument correction:** add subdivision shapes with the nearest point within the tie band of a newly inserted vertex, and measure verdicts as well as deltas. A choice to retain the per-segment estimand is coherent; choosing exact per-geometry minimizers instead is a **design amendment and owner policy choice**, not an oracle repair. The choice is framed correctly, but its stated small exposure is not.

## P22-F6 — Medium — node simplicity makes the route set finite, not every reconstructed route unique

**Location:** design §2.4 journey key and §13 F8; `toy.py:_partial_route`, `Journey.rank_key`; manifest path references.

**Executed input:** one one-way edge, time/cost **0**, geometry

```text
(0,0),(100,0),(100,100),(0,100),(0,0),(100,0)
```

Origin `(25,0)`, destination `(75,0)`. Retained direct forward intervals include arclengths **25→75**, **25→475**, and **425→475**. Their lengths are **50, 450, 50 m**. Each has time/cost zero, the same destination, and the **same one-element directed-edge identity sequence**. The full current `rank_key`, including its final cost field, ties.

These direct partial journeys do not acquire repeated graph nodes merely because the geometry revisits an XY position. They do not contain an intervening repeated-node path. Forbidding repeated original graph nodes therefore does not distinguish them. Introducing attachment vertices into a different definition of simplicity would itself need specification.

This flips selected reconstructed geometry, not a numeric PASS/FAIL. For an extraction boundary at `y=100` with a 10 m band, the short interval does not touch the band and the 450 m interval does. T10 can consequently report **0% or 100% boundary touch** for one selected route with identical current ranking fields.

`_route` further discards **both endpoint node IDs and the entire geometry key**, retaining only orientation, osmid and rounded length. Thus its equality is not equality of the declared route identity. Different roads of the same length/osmid/orientation become indistinguishable there. Its introductory description claiming to retain the geometry key is inaccurate.

**Minimal fix — design amendment if a unique reconstruction is promised:** include traversal intervals/occurrence references and a deterministic tie convention for observationally distinct journeys. Define precisely whether simplicity concerns original nodes or a graph split at attachment positions. Compare complete route identities through appropriate transform mappings. If only the identity sequence is promised unique, state that weaker promise and separately specify reconstruction for T10. Node simplicity does repair the infinite lexicographic descent; that repair alone does not settle this tie.

## P22-F7 — Medium — the numeric tolerance has no domain-wide justification, and its helper can report false cleanliness

**Location:** `invariants.py:CONTINUOUS_FIELDS`, `differences`; `conformance.py:tolerance_is_decision_irrelevant`.

I reproduced the claimed small spread **on the current scenarios**: the maximum across answer-preserving transforms plus midpoint subdivision, over the continuous reported fields, is **2.0179413695586845e-12**, on `reverse_traversal_curved` under translation. That is below 1e-11. It is not a bound over admissible inputs.

**Simpler admissible counterexample:** one straight bidirectional edge `(0,0)→(100,0)`, origin `(.1,0)`, destination `(99.9,0)`, time/cost **1,000,000**. Correct evaluation gives **998000.0000000001 s**; the supplied translation gives **997999.9999999927 s**. Spread is **7.450580596923828e-9 s**, exceeding both 1e-11 and the 1e-9 tolerance. All inputs are finite, with ordinary 100 m geometry. There is no stated weight ceiling excluding it.

With time/cost **601.2024048096193**, the same geometry reports **600.0000000000001 s** before translation and **599.9999999999957 s** afterwards: FAIL versus PASS at ten minutes. A faithful floating implementation can cross a decision boundary under a representation change. A tolerance must expose that fact rather than treating translation as an unconditional equivalence.

There are also two direct helper defects:

```python
differences({'objective1_s': 600.0}, {'objective1_s': 600.0})
# {'objective1_s': (600.0, 600.0)}

differences({'objective1_s': 100.0}, {'objective1_s': float('nan')})
# {}
```

The first rejects two exactly identical, valid threshold answers. The second accepts a finite result replaced by a non-result because `abs(a - NaN) > tolerance` is false. The same bypass applies to costs. Costs and metre residuals are additionally sent through a **seconds-based published-threshold** test: that is not a proof that a cost argmin, cap or tie-band decision is unaffected. For example a cost change from **1 to 1+5e-10** is accepted although a competing cost **1+2e-10** changes which journey wins.

**Minimal fix — helper/instrument correction:** accept exact equal finite values first; reject nonfinite outputs explicitly; validate quantity types and compare decision-relevant predicates in their own units. Declare the supported numerical domain and justify an error budget there. A 1e-9 absolute tolerance is defensible for the demonstrated samples, not a universal equivalence contract. No epsilon should be inserted into cost ranking as an incidental test repair.

## P22-F8 — Medium — the mutation helper repeats the imported-binding blind spot

**Location:** `invariants.py` imports and `Scenario.run`, `_absolute_violations`; `conformance.py` import and `Case.run`; `test_mutants.py`.

Both modules still import `evaluate` **by name**. The invariant helper's statement that every call into `toy` goes through the module is false.

**Executed experiment after those modules were imported:** replace `toy.evaluate` with a wrapper that adds **1000 s** to each finite objective time. A 100 s journey now actually returns **1100 s**, changing PASS to FAIL at ten minutes. Nevertheless `invariant_violations()` returns **[]** and every corpus `check(case)` remains clean. Their saved bindings continue to call the original function. `_absolute_violations` also uses that saved binding, so even its zero-time anchor cannot see the wrapper.

This experiment establishes a defect in the **programmatic mutation guard**, not that the wrapper survives every test in `test_invariants.py`: direct `toy.evaluate` calls in that file can expose it. By contrast P22-F2 survives all 423 tests, without exploiting this binding issue.

**Minimal fix — implementation correction:** make evaluator calls use the module attribute, or inject one evaluator consistently into scenarios, cases and anchors. Add a sentinel evaluator mutation proving that the intended call sites execute the replacement. Test the programmatic guard's claimed parity with the pytest invariant layer; they currently differ, including the missing intercept check in the helper.

## P22-F9 — Medium — finite constructor fields do not establish the advertised admissible arithmetic domain

**Location:** `toy.py:ToyEdge.__post_init__`, `_segment_nearest`, `evaluate`; `Scenario`; admissible-domain claims in `invariants.py` and build record.

**Executed finite input:** a one-way edge `(0,0)→(1e-200,0)`, time/cost **1000**, origin `(0,0)`, destination `(1e-200,0)`. Every coordinate and weight is finite and nonnegative. Squaring the segment displacement underflows to zero, so `_segment_nearest` treats this nonzero segment as degenerate and attaches the destination at its start. The oracle reports **7.936507936507936e-201 s**, PASS, instead of the mathematically required endpoint-to-endpoint **1000 s**, FAIL at ten minutes.

Conversely, base cost **1e308** and penalty **1e308** each pass validation but produce `total_cost=inf`. A coincident midpoint query then reaches `0*inf=NaN`; evaluation raises **`ValueError: min() iterable argument is empty`** rather than its promised zero result. Origin/destination coordinates also have no corresponding finite-value validation at the query boundary.

**Minimal fix — admissible-input specification plus implementation:** either bound the supported coordinates/weights and aggregate arithmetic explicitly, or use robust projection and checked arithmetic with a defined response to overflow. Validate query coordinates too. No claim that finite inputs make all geometry arithmetic well defined is justified. The tiny edge is outside plausible road data, but inside the domain the instrument explicitly claims to enforce.

## P22-F10 — Medium — the oracle's final cost discriminator is still absent from the normative journey order

**Location:** design §2.4 ranking/lift; `toy.py:Journey.rank_key`; §13 revision 8.

The oracle now orders by `(time, destination_id, route, cost)`, repairing pass-21 F6 in code. The normative journey lift still ends at the **route sequence**. Revision 8's amendment table has F1, F2, F7 and F8; it does not specify this final cost discriminator.

**Worked input:** two records `0→1`, geometry `(0,0),(100,0)`, identical osmid and identity, both time **100**, costs **1 and 2**. Origin and destination are the endpoints. Objective 1's time, destination and route sequence tie under every stated journey field. A conforming reader of the prose can report selected cost **2**, while the current oracle requires **1**. This changes the manifest's reported selected cost, not its 100 s PASS.

**Minimal fix — design amendment:** put the chosen final discriminator in normative §2.4 and the change log, with its provenance fixture. Describe existing code as the proposed policy until that is done. The earlier statement that the four local edge keys make every reported quantity identical also needs qualification for the objective-1 case.

## P22-F11 — Medium — byte-backed frames resist ordinary writes, but remain mutable through their exposed address

**Location:** `frames.py:_frozen`, `Frame.verify`, `Frame.__reduce__`, `write_frame`; future measurement consumers.

The `.base`/writeable-flag and ordinary pickle repairs work. The public buffer protocol is read-only. They do not make the contents unreachable to native writes.

**Executed on a fresh in-memory frame only:** frame C on `GridSpec('EPSG:32617',0,1000,100,10,10)`, `n=1`, seed **7**, initially contains **`(840.2498298103982,109.67040939317457)`**. Both array/base `setflags(write=True)` attempts fail and `memoryview(points).readonly` is true. Nevertheless:

```python
address = frame.points.__array_interface__['data'][0]
ctypes.c_double.from_address(address).value = frame.points[0, 0] + 999
```

changes x to **1839.2498298103983**, while the stored digest remains unchanged. `frame.verify()` then correctly raises. This moves the point outside the original 1000 m-wide frame; in a product with a boundary between these positions, its sampled verdict can change under the same recorded frame identity.

This requires unsafe native-memory access. It is a limit on the stronger protection claim, not a reason to demand impossible tamper-proof Python objects. Arbitrary `copyreg` reducers, subclass overrides or `object.__setattr__` likewise need a stated trust boundary; ordinary round-trip pickle now revalidates and remains read-only, which I checked.

Repository search still finds **no production calls to `verify()`**. `write_frame` independently recomputes the digest and protects persistence; future measurement consumers have not been built, so no corrupted production measurement is established here.

**Minimal fix — boundary verification and claim correction:** verify the actual frame at measurement entry and before committing results, using a stable snapshot if native/concurrent writers are in scope. Retain byte backing for accidental-write protection. Require consumer tests when T3/T5 are implemented. No new estimand amendment is needed.

## P22-F12 — Medium — T6 still does not require the inputs for the whole report

**Location:** execution-plan T6, T9–T11; design §§10–12. The earlier raw-value, full/intersection objective-2, E0 census and self-contained-reference additions are useful and retained.

**Worked indistinguishable required payloads:** keep every required T6 routing row and all digests identical, with an E3 reported time of **300 s**. Observed time **300 s** yields UNVERIFIED; observed time **1200 s** yields FAILED, with a **900 s** signed discrepancy. Neither observation nor walked/missing flag is required in T6. Implementing the T9 scorer does not persist its inputs. The two bundles can therefore satisfy the listed schema and fail to determine a mandatory report result.

Similarly, a retained path **15 m** from the extraction boundary is counted under a **20 m** band but not a **10 m** band. Self-contained route geometry alone supplies neither that configuration nor the extraction footprint. Saving only surviving paths also cannot recover the missing-path denominator.

The complete regeneration bundle must explicitly require, either in T6 or named companion artifacts:

1. **T9:** journey IDs, reported seconds, observed seconds or explicit unwalked/missing state, and the scoring configuration/version. Preserve planned records as well as completed ones.
2. **T10:** extraction footprint and CRS, boundary-band width and predicate, the objective/population whose routes are counted, point/route membership, missing-path statuses and the complete denominator. Save traversal intervals/geometry or sufficient boundary statistics under that exact predicate.
3. **Diagnostic screening:** actual frame/stratum memberships and counts, population-reference estimates/counts and their domains, the chosen predicates and thresholds, and sampling metadata sufficient to recover the conditional denominators and empty-stratum behavior. Sampled memberships cannot reconstruct an omitted population summary.
4. **Certification history:** the independently timestamped registration, designated attempt and seed-generation/stopping/replacement policy, and all attempt identities/outcomes, including voided runs. A successful run manifest alone cannot regenerate the mandatory failed/voided-attempt account.
5. **Analysis configuration:** actual defining configuration alongside identifiers/digests: units, frame/grid specifications, population qualifications, uncertainty/bootstrap settings and seeds, and decoder/lookup version where used. Qualify each selected destination/cost/status/residual pair by objective and full/intersection population. “Both residuals” must specify each origin/destination residual and its selected journey, rather than an unqualified aggregate.
6. **Any additional development figures included in the report:** paired grid-comparison observations/configurations and phone latency/transfer observations/configurations. They are conditional on those figures being reported; they are not extra operands for the specified routing distributions.

**Minimal fix — payload/plan correction:** require those companion artifacts and reject bundles missing any mandatory report input. T6's regeneration test must disable source artifacts and routing, including implicit access to T9/T10 inputs outside the bundle. No new own objective-2 population or third own time operand is established by this finding.

## Other requested checks

- **Occurrence identity:** adjacent segment descriptions of the same vertex merge; `0.0` and `-0.0` take the same endpoint branch. Ordinary three-segment collinearity does not demand merging projections at different arclengths. Nonadjacent repeated vertices, overlapping segments and a closed ring's 0/L positions correctly remain separate occurrences. No epsilon bucket should be restored: closeness alone does not prove interchangeability. Arithmetic determining endpoint versus interior classification still needs F1's contract.
- **Zero-length segment:** on `(-1,0),(0,0),(0,0),(1,0)`, the implementation retains **two** candidates at arclength 1, vertex indices 1 and 2. This is consistent with treating distinct vertices as distinct structural occurrences; it is not a collapse of the whole zero-length vertex chain. State that explicitly rather than claiming zero-length endpoints all merge. The measured candidate-count subdivision signature is accurate for the current scenarios, not a universal invariant.
- **Palindrome reversal:** renormalization is correct. Closed exact palindromes can share the forward/reverse identity. An open edge with different endpoint **node IDs** still has `(u,v)` versus `(v,u)` and must not share the complete identity. An exact geometric palindrome necessarily has equal endpoint coordinates; geometrically different endpoints can be palindromic only after rounding. The blanket amendment-table statement that a palindrome's directions share identity needs that qualification. Canonical reverse pairing works for those representations, provided weight alternatives remain eligible to compete. The existing production `symmetrise` still uses `_physical_key`; its known replacement remains implementation work, not a demonstrated revision-8 repair.
- **Answers versus provenance:** excluding candidate counts from `explicit_reverses` equality is correct because candidates are per record. §12's same-input implementation-equivalence contract does not itself require invariance under this different input representation. The distinction is useful, but exact numeric answer preservation needs the arithmetic qualifications above. Counts double for candidates on replaced bidirectional records, not universally: a mixture of one one-way and one bidirectional candidate changes **2→3**, not 2→4.
- **`EXPECTED_COVERAGE`:** all eight recorded pairs reproduce; both the real control and all 18 guard tests pass. This supports those specific mutant/layer pairs. It does not prove coverage of evaluator replacements, longer paths, discarded route fields or the rest of the admissible domain.
- **Fields outside the instrument:** `n_journeys` and the complete attachment/path reconstruction are not compared by `answers()`/`provenance()`. The former is diagnostic bookkeeping; the latter is required by the manifest and T10. Do not describe the current reduced dictionaries as every reported number and identity.

## Build-record overstatement audit

The earlier numerical/statistical and frame-draw corrections do not acquire a new defect from these checks. The recorded eight-mutant coverage table is accurate. The remaining overstatements are substantive:

| current claim | supported conclusion |
|---|---|
| Constructors and 22 shapes declare/enforce the admissible domain | They exercise selected points; query validation, aggregate finiteness and safe projection are incomplete (F2, F9). |
| Selected totals are affine and one check verifies connector inclusion | Only a held journey has the proposed real-arithmetic form; selection switches, and zero intercept passes (F3). |
| A translation preserves orientation; reported routes capture identity | Rounding can change orientation, and `_route` removes identifying fields (F4, F6). |
| Domain-wide spread stays under 1e-11; subdivision exposure is only noise except zero-length segments | Both are observations of 22 scenarios, refuted as domain-wide statements by F5/F7. |
| The harness stopped retaining patched names | `evaluate` is still imported by name in both layers (F8). |
| Revision 8 settles the four-item finish line | Geometry arithmetic and unique reconstruction remain open; the final cost order is implemented but not normatively amended (F1, F6, F10). |
| The mutation guard answers “would anything have noticed” | It answers that for eight installed mutations and its actual call paths; the new path cutoff survives all 423 tests (F2). |

The execution plan also retains stale T3/T4 paragraphs referring to review of revision 7 and twelve cases, while its opening refers to revision 8 and the new instrument. These should be reconciled; they are documentation drift, not additional numeric findings.

## Validation and limits

Using the repository's Python 3.13.1 environment, unmutated conformance/invariants/mutation guards pass **423/423**. The four-intervening-edge cutoff passes that same complete set. T1/T2/T9 collect another **185** tests: **180 pass**, while **five frame tests error during pytest temporary-directory setup**, with `PermissionError [WinError 5]` at `C:/Users/arikt/AppData/Local/Temp/pytest-of-arikt`. Those are environment errors, not frame-test failures; I did not redirect temporary output into repository files. Total unmutated evidence here is **603 passed, five setup errors**, not a reproduction of the build record's full 936-test run. No routing sources or full-data frame rebuilds were needed for the worked counterexamples.

## The three judgments

**Can T3 now be implemented as a frozen reference? No.** Ordinary implementation of the settled subset can proceed. Before calling it frozen, settle geometry/projection/arclength/fraction arithmetic and its admissible numerical domain; put the final cost discriminator into the normative order; and define the selected traversal/reconstruction domain and tie handling beyond a bare edge sequence. Reconcile the normative text with the reverse-normalization and node-simple amendments. Add independently calculated decision/provenance fixtures and an oracle carrying those observables. Correct the false universal invariants before using them as a conformance requirement. Frame-consumption verification and a complete regeneration bundle remain prerequisites for measurement/freeze, rather than evidence that already-built consumers are wrong.

**Is the fix-breaks-adjacent-case pattern still running? Yes.** The clearest replacement-rule failure is proportional scaling being replaced by affine scaling of a selected answer: the corrected connector intercept creates the journey switch that refutes the replacement. Frozen weight terms also leave their geometry-derived fraction unfrozen. The new instrument supplies real evidence about eight historical regressions, but the 423-test surviving path cutoff and rejected legal connector-only route show that it has not yet stopped the pattern.

**Does the instrument change what must be true for T3 to be safe? It makes the evidence requirement more concrete, without removing the earlier finish line.** A coherent domain/arithmetic/selection contract, independent numeric and provenance evidence, complete oracle observables, consumer-boundary verification and a reproducible bundle are still required. Add soundness checks for the invariants themselves and verified evaluator injection/coverage of structural dimensions such as hop depth and new subdivision candidates. No finite green suite proves universal equivalence; the value of this instrument is that it can expose wrong rules and missing shapes when those are actually exercised. The owner may retain the current subdivision-dependent estimand, but should do so with F5's demonstrated verdict exposure, not the claim that its effect is only noise.
