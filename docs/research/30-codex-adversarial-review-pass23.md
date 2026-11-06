# Adversarial review pass 23 — the corrected instrument

Reviewed `v2-rethink`, HEAD `18ab58c`, on 2026-11-06, using the repository's Python 3.13.1 environment. Only this review was written. Mutations and experiment programs were supplied through stdin, in separate processes, with bytecode and pytest cache writes disabled.

**The replacement-rule pattern has not stopped.** The conditioned affinity test mistakes a route key for a journey; the newly reported network seconds distinguish previously indistinguishable winners; and weakening translation hides an incorrect orientation rule. A separate, uniform destination-count reduction also escapes every exercised oracle call.

## P23-F1 — High — destination cardinality is an unexercised search dimension

**Location:** `toy.py:journeys`; scenario/corpus populations; `test_invariants.py:test_adding_a_destination_never_slows_objective_1`.

Installed before test imports:

```python
real = toy.journeys
def wrong(graph, origin, destinations, destination_ids=None):
    return real(graph, origin, destinations[:4],
                None if destination_ids is None else destination_ids[:4])
toy.journeys = wrong
```

This is a uniform destination-count cutoff, independent of geometry, names, weights and fixtures. Eligibility still examines every destination; only journey enumeration is truncated. Every surviving journey is correct. Instrumenting all calls during the full suite found a maximum of **three destinations**. Thus the cutoff never activates in any executed oracle call, including mutation guards and destination-addition checks.

**Executed distinguishing input:** five one-way spokes from `(0,0)` to `(1000,0)`, `(0,1000)`, `(-1000,0)`, `(0,-1000)`, `(1000,1000)`. Each has its own endpoint node. The first four have time/cost **1000/1000**; the fifth has **1/1**. The origin is the hub and the five destinations are the endpoints, in that order. Connectors are zero. Correct evaluation selects destination 4 at **1 s**, PASS at ten minutes. The cutoff selects destination 0 at **1000 s**, FAIL. Both evaluations report all five destinations eligible.

**Validation:** baseline and mutant each produced **1017 passed, 22 setup errors, one failure** over the 1040 collected tests. All 23 non-passing results were the same temporary-filesystem permission problems, described below. No mutation-induced failure occurred. I cannot honestly report 1040/1040 passing in this environment; the measured call cardinalities additionally establish why this mutation cannot affect the blocked tests unless they introduce a larger oracle call after setup.

**Minimal fix — instrument correction, no design amendment:** exercise destination cardinality with independently anchored optima at different list positions, including beyond the current maximum, and permute destination order while preserving IDs. Include eligible-but-unreachable destinations and unequal connector costs. Test exhaustion/completeness across this dimension, rather than treating five hop-depth anchors as completeness evidence for every enumeration loop.

## P23-F2 — High — the conditioned affinity check still rejects a correct selection switch

**Location:** `invariants.py:72, 590` (`_route` and affinity condition); `test_invariants.py:231`.

Route and destination equality do **not** establish that the selected journey stayed fixed. They omit attachment occurrences, fractions, connector residuals and weight-record identity. Even the full declared edge-identity sequence would not establish those facts.

**Executed counterexample:** one one-way edge with geometry `(0,0),(50,0),(100,0)`, time/cost **40/40**; origin `(49.995,0)`, destination `(100,0)`.

The origin has two retained candidates: its exact projection and the next segment's clamped start at 50, residual **0.005 m**. Their totals at scale `k` are approximately `20.002*k` and `20*k + .005/1.26`.

| scale | correct selected time | network seconds |
|---:|---:|---:|
| 1 | 20.002000000000002 | 20.002000000000002 |
| 3 | 60.00396825396825 | 60 |
| 7 | 140.00396825396825 | 140 |

Every selected destination ID is `"0"`; every reduced route is `((0, (), 100.0),)`; every full route is the same single directed-edge identity. Nevertheless the attachment switches. The tested slopes are **20.000984126984125** and **20**, differing by almost a million times the tolerance. The check rejects a correct oracle. The decision flipped here is conformance acceptance, not a ten-minute verdict.

**It is not vacuous on the current scenarios:** all **27** pass its route/destination condition; **24** execute the slope assertion; three (`off_network_origin`, `no_route`, `empty_graph`) return after checking that all times are `None`. **Zero scenarios invoke `pytest.skip`.** The named regression demonstrating a destination switch is outside `SCENARIOS`, so this conditioned test does not encounter it.

**Minimal fix — instrument correction:** hold an actual journey fixed, including both attachment occurrences, edge records, path and traversal choices, and evaluate that journey at each scale. Alternatively prove that one identical affine candidate remains a minimizer throughout the interval. Do not identify journeys by reported route/destination equality. Defining unique selected reconstruction separately still requires the P22-F6 design amendment.

## P23-F3 — Medium — adding network seconds creates an unsatisfied permutation obligation

**Location:** `toy.py:351, 607`; `invariants.py:answers`, answer-preserving comparisons.

`network_s` is computed sensibly, but is not determined by the current ranking fields. Reporting it as an invariant adds an observable that tied winners can disagree on.

**Executed counterexample:** two one-way records from node 0 at `(0,0)` to node 1 at `(100,0)`, both with empty osmid:

| record | geometry | time and cost |
|---|---|---:|
| A | `(0,0),(50,0),(100,0)` | 2 |
| B | `(0,0),(50,.004),(100,0)` | 1.9936507809117465 |

Origin `(25,0)`, destination `(75,0)`. B's two residuals are each **0.0019999999936 m**, its traversal fraction is **0.5000000031999999**, and its connector total is **0.003174603164444445 s**. Both records have the same complete rounded directed identity: rounded geometry has middle vertex `(50,0)`, orientation 0 and length 100.

Both winning direct journeys have exactly **time 1, cost 1, destination `"0"`, and the same full route**. Their complete `rank_key`s tie. A has network time **1**; B has **0.9968253968355556**. Input order A,B selects A; B,A selects B. `compare(..., "permute_edges")` consequently reports both network fields different by **0.0031746031644444 s**, rejecting faithful evaluation. No time verdict flips; the selected network decomposition and invariant verdict do.

**Minimal fix — design amendment if unique selected decomposition is promised:** settle ties between observationally distinct journeys using complete traversal/attachment information, or explicitly allow tied-winner decomposition sets and compare those. Merely documenting `_route` as lossy does not settle this. Removing network seconds from representation equality would avoid the new obligation while retaining the per-result route implication, but would leave reconstruction uniqueness open.

The implication **empty route ⇒ zero network seconds** is sound for successfully evaluated finite journeys. Direct candidates use their direct network term; a zero span supplies zero; endpoint candidates sum exactly their network terms. `network_s` is `compare=False`, absent from `rank_key`, and no journey set/dictionary deduplication is performed: adding the field changes neither ranking nor deduplication. Its description as “total less connectors” should mean a decomposition, not binary64 subtraction of rounded totals. Several remaining docstrings still incorrectly call the implication an equivalence.

## P23-F4 — Medium — the translation weakening hides a coordinate-dependent orientation defect

**Location:** `invariants.py:453–478` (`WEAKENED`, `_drop_orientation`, `compare`); route legality checks.

Installed this wrong identity rule:

```python
real = toy.directed_identity
def wrong(edge, *, forward):
    ident = real(edge, forward=forward)
    if max(abs(c) for p in edge.geometry for c in p) > 10000:
        ident = ident[:3] + (0,) + ident[4:]
    return ident
toy.directed_identity = wrong
```

This forces orientation 0 outside an absolute-coordinate box. It preserves equivalence with explicitly reversed records because both representations receive the same wrong rule. The existing absolute identity anchors are inside the box. Route legality recomputes identities using the same mutated function.

**Executed counterexample:** the existing `reverse_traversal` scenario, translated by the supplied offset: edge `(12345.678,-98765.432)` to `(12445.678,-98765.432)`, origin at the translated 80 m position, destination at 20 m. Correct reverse traversal has orientation **1**; the mutant reports **0**, with the same approximately **60 s** time and the same remaining identity fields. This is not a rounding-induced palindrome. The normative directed-route identity is wrong, and the translation comparison discards exactly the evidence.

**Result:** all **527** conformance/invariant/mutation-guard tests pass under the mutant. The full suite has exactly the baseline result, **1017 passed, 22 errors, one permission-related failure**. The dimension is **absolute-coordinate dependence of identity**, combined with missing independent validation on transformed inputs. The claim that this weakening “costs no coverage” is false, even though the historical bit-complement mutant remains caught.

**Minimal fix — instrument correction, no new identity policy:** compare through an explicit correspondence between actual traversals, validating the transformed identity against the normative rounded geometry. Retain orientation comparison where the rounded orientation is proven preserved, and independently test both legitimate changes and illegitimate ones. `_drop_orientation` itself uses the correct positions: `_route` produces `(orientation, osmid, length)`, so slicing each item at `[1:]` removes orientation. It would be wrong on raw six-field identities, but those are not its current inputs.

Also, `_route`'s new explanation for dropping node pairs under `explicit_reverses` is mistaken: a reverse traversal of `u→v` and a forward traversal of the explicitly reversed record both have endpoints **`(v,u)`**. That transform does not require discarding them.

## P23-F5 — Medium — reported binary64 minima are not universally concave

**Location:** `invariants.py:494, 575`; `test_invariants.py:203`; corrected build record's `SCALE_LAW` claim.

The real-arithmetic lower-envelope theorem is sound. The implemented weight scaling rounds each edge field before forming and summing traversal terms; the reported values therefore need an error budget. The absolute **1e-9** allowance is not valid over all accepted finite weights.

**Executed counterexample:** one one-way edge `(0,0)→(100,0)`, time/cost **100000000.1**, no penalty; endpoint origin and destination, zero connectors. The correct evaluator reports:

| scale | time and cost |
|---:|---:|
| 1 | 100000000.1 |
| 3 | 300000000.29999995 |
| 7 | 700000000.6999999 |

The implemented chord is **300000000.3**, exceeding the middle value by **5.960464477539063e-8**. Even the exact rational chord of these three binary64 outputs exceeds the middle by **1.9868214925130207e-8**: this is not solely an error evaluating the chord. Subtracting 1e-9 does not repair it. Both concavity assertions reject the correct result. The flipped decision is whether a conforming implementation passes the instrument.

**Minimal fix — instrument correction, plus the numerical-domain amendment already required by P22-F9:** distinguish the ideal envelope theorem from rounded observations; derive an error budget covering scaling, cost formation, traversal multiplication, summation and chord arithmetic on a specified supported domain, or test a suitable exact-arithmetic model. Do not change the cost argmin to use an epsilon.

For the ideal theorem: geometric eligibility **and reachability** are weight-independent on a fixed graph under positive finite scaling. A destination does not become unreachable because its weights increased. `None` must occur at all scales or none; pytest checks this, whereas `invariant_violations()` merely skips a triple with any `None`. Objective-2 time tie-breaking does not change its minimum cost value. Zero-weight journeys give constant affine candidates. Three points cannot expose a kink outside `[1,7]`; within that interval exact chord equality for a concave envelope excludes a genuine interior change of slope, but does not prove that a selected journey identity never switched among ties. Finite tolerance can also conceal a small interior kink. “Equality exactly where the argmin does not switch” needs those qualifications.

## P23-F6 — Medium — equal non-finite values still bypass the non-finite check

**Location:** `invariants.py:131–160`, `differences()`.

Executed results:

```python
differences({'objective1_s': float('inf')},
            {'objective1_s': float('inf')})       # {}
n = float('nan')
differences({'objective1_s': n}, {'objective1_s': n})  # {}
```

Equality catches the infinities; object identity catches the shared NaN. Thus the documented rule “non-finite always a difference” is false. A wrong implementation returning the same non-result across representations can pass this helper; an infinite purported time is accepted as unchanged instead of flagged invalid. This is a helper counterexample, not a claim that replacing every suite answer with infinity survives the absolute anchors.

**Minimal fix — implementation correction, no design amendment:** recognize missing `None` separately, validate numeric finiteness before equality, and then accept equal finite values. Preserve the repaired behavior for two identical finite threshold values.

## P23-F7 — Medium — metre thresholds do not prove attachment decision irrelevance

**Location:** `invariants.py:113–129`, metre branch of `differences()`.

The tie test is **candidate residual ≤ global minimum + .01**, not **global minimum ≤ .01**. `origin_nearest_m` does not face the three fixed thresholds claimed for it: the destination cap applies to destination residuals, while the band applies to relative gaps. Being nine orders of magnitude below a band width does not bound distance from its boundary.

**Executed counterexample:** two disconnected, one-way horizontal edges from x=0 to x=100, at y=**−100** and y=**100.0100000002**. Their time/costs are **1000/1000** and **0/0**, respectively. With origin `(0,0)` and destination `(100,0)`, the second edge is outside the tie band. Correct time is **1158.7301587301588 s**, FAIL at ten minutes. Move both query y coordinates to **5e-10**. Nearest residual becomes **100.0000000005**; the other edge's residual becomes approximately **100.0099999997**, now inside the band. Correct time becomes **158.74603174555554 s**, PASS, and origin candidate count changes **1→2**.

Nevertheless `differences({'origin_nearest_m':100.0}, {'origin_nearest_m':100.0+5e-10})` returns **`{}`**. The full answer comparison would catch the large time/count changes; the false claim is that the metre helper independently proves this accepted residual change decision-irrelevant.

**Minimal fix — instrument correction:** compare actual cap predicates and candidate-minus-minimum band predicates, using retained candidate information. Call 1e-9 a measured numeric allowance until a supported-domain error analysis exists. No attachment-policy amendment is needed.

Checking both endpoints of a seconds tolerance introduces additional **conservative rejection**, too. Executed on edge `(0,0)→(100,0)`, time/cost **601.2024048106233**, origin `(.1,0)`, destination `(99.9,0)`, the supplied translation moves **600.0000000010021** to **600.0000000009976 s**. Difference: **4.547473508864641e-12 s**. Both are FAIL at ten minutes. The old first-endpoint guard accepts the pair; the new second-endpoint guard rejects it. This is defensible as an expressly conservative admission policy, but not as a test that accepts every correct implementation or only rejects pairs with different verdicts. To establish this pair's verdict equivalence, compare its actual threshold predicates; a full ±1e-9 neighborhood proves a stronger property than necessary. `COST_FIELDS`/`NOT_PROVEN` now honestly acknowledge their argmin limitation; they do not repair this separate issue.

## P23-F8 — Medium — the connector anchor does not establish all four claimed inclusions

**Location:** `invariants.py:614`, `_absolute_violations`; `test_invariants.py:262`, `test_both_connectors_are_in_both_totals`.

The anchor establishes the historical selection distinction and objective 1's reported time. It does not assert either selected cost. Its origin connector is zero, and objective 2 selects the destination with **zero destination connector**, so its 650 s assertion cannot establish connector inclusion in objective 2's reported time.

**Executed wrapper:** after correct selection, replace `objective1_cost` with `objective1_cost - (objective1_s - objective1_network_s)` and `objective2_s` with `objective2_network_s`. Both the named connector test and `_absolute_violations()` still pass. This removes connectors from two of the four claimed outputs. This wrapper is an anchor-coverage demonstration, not a whole-suite survivor.

For a distinguishing decision, take one straight 100 m edge with time/cost **580/580**, origin `(0,10)`, destination `(100,20)`. Correct totals are **580 + 30/1.26 = 603.8095238095239**. The wrapper reports objective-1 cost **580** and objective-2 time **580**, turning objective 2 from ten-minute FAIL to PASS. With no alternative destination, dropping connector cost cannot be detected indirectly through selection either.

**Minimal fix — instrument correction, no design amendment:** independently assert both objectives' selected times and costs on cases with nonzero origin and destination connectors, and retain the unequal-destination selection case. The anchor does catch the historical connector-free-cost mutant; that narrower claim is supported.

## Still-open pass-22 items: sequencing

Ordinary T3 development can proceed on the settled subset. None of these requires stopping all implementation work. “Freeze blocker” below means an unresolved contract/evidence requirement before calling the reference complete, rather than a prohibition on writing provisional code.

| open item | sequencing judgment |
|---|---|
| **P22-F1 — geometry arithmetic** | **Blocks T3's freeze, not ordinary implementation.** Reproduced unchanged: geometry A `(0,0),(.1,0),(.1,.2),(.1,.5)`, time/cost 6/1, versus B `(0,0),(.1,0)`, time/cost 1000/(1/6), origin `(0,0)`, destination `(.1,0)`. Current length `sum` gives A length **0.6**, selecting B at **1000 s**; in-memory explicit left accumulation gives **0.6000000000000001**, ties costs, and selects A at **1 s**. FAIL/PASS at ten minutes still flips. |
| **P22-F6 — unique reconstruction** | **Blocks T3's freeze under the current provenance promise.** Calling `_route` lossy is accurate but insufficient; §2.4 must specify the promised observable and resolve observationally distinct ties, or explicitly weaken uniqueness and specify reconstruction separately. P23-F3 demonstrates that this now reaches an additional numeric field, not only future T10 geometry. |
| **P22-F9 — underflow/overflow/domain** | **Blocks T3's freeze, not provisional implementation.** Choose and enforce a supported arithmetic domain or define robust arithmetic and failure statuses. This decision belongs with F1, before trusting universal scaling/translation claims. Finite input components alone remain insufficient. |
| **P22-F10 — final cost discriminator** | **Blocks T3's freeze, not provisional implementation.** Amend normative §2.4 to match the intended final cost key, then independently fixture it. The oracle's existing policy is usable as a proposal. |
| **P22-F11 — native writes/consumer verification** | **Neither as a prerequisite design gate for T3.** Implement verification at actual measurement consumption and before committing results, with a snapshot if concurrent native mutation is in scope. That is a completion requirement for a T3 entry point that consumes frames, and a measurement-freeze requirement, not a reason to prohibit development or demand native-memory tamper-proof objects. |
| **P22-F12 — T6 companion artifacts** | **Neither for T3 alone.** It blocks complete-bundle/report regeneration and the overall study freeze. Specify T9/T10/configuration/denominator/history companion inputs before freezing T6; independent numeric comparator development need not await their implementation. |

For F1, naming an operation sequence is **necessary but not sufficient** for portable bitwise equivalence: define binary64 rounding of primitive operations, segment norms, prefix/total accumulation, projection/clamping, fraction and interval arithmetic, underflow/overflow, and whether reassociation or fused operations are allowed. Naming `sum` alone delegates behavior to a runtime; naming `hypot` alone is not an exact output-bit specification. Either specify deterministic numerical semantics and verify implementations against them, or declare a qualified runtime/version/platform contract with decisive bit-level fixtures and requalification on change. A pinned platform is a reproducibility boundary, not a mathematical proof; it need not be the only solution. Do not silently promise equivalence on arbitrary platforms while exact cost ranking can amplify one bit into 999 s.

## Requested judgments

**Has the pattern stopped? No.** The affinity replacement closes destination switching but misses attachment switching (P23-F2). The route implication is sound, while exposing network seconds creates an adjacent tied-winner obligation (P23-F3). Excluding translated orientation permits a new coordinate-dependent identity mutant (P23-F4). Equality-first fixes identical finite thresholds but still accepts identical non-finite outputs (P23-F6). These are replacement-domain failures, not repetitions of the motivating examples.

**Is `EXPECTED_COVERAGE` accurate? Yes.** All ten pairs reproduce, including connector-free cost **(True, True)**, bounded paths **(True, False)** and inflated evaluator **(True, True)**. Six mutants escape the corpus and one escapes invariants, as recorded. This is accurate coverage of those installed mutations; it does not cover destination-count truncation or P23-F4's orientation rule.

**Does the connector anchor do what the intercept check was credited with? Only in the narrower historical-mutant sense.** It catches omitted connector cost through changed selection and pins objective 1's time. It does not establish both connectors in both objectives' selected time and cost (P23-F8).

The hop-depth anchors and `_chain` arithmetic are sound at their declared depths: `80*depth`, `depth` route elements, and `depth-2` intervening path edges. They do not exercise branching, curvature, nonzero connectors, unequal weights, or unlimited depth; P23-F1 gives a separate missing dimension without merely moving the chain cutoff to 10.

## Validation and scope

The conformance/invariant/mutation-guard files contain **527 tests** (112 + 392 + 23). The orientation mutant passes all 527; the destination cutoff never activates in any oracle call across the full suite. Baseline, destination-cutoff and orientation full runs each give **1017 passed, 22 setup errors, one failure**, totaling 1040. The errors are 17 acquisition and five frame temporary-directory setup failures at `C:/Users/arikt/AppData/Local/Temp/pytest-of-arikt`; the remaining acquisition test fails with permission errors opening a temporary `raw.parquet.lock` and cleaning its directory. These are environment denials, not evidence of a mutant or product regression. I did not redirect temporary output into the repository.

The build record acquired an external uncommitted edit during this review; I read the corrected text as well and did not modify it. Pre-existing unrelated workspace changes were left intact. No source files, tests, fixtures, manifests, caches or dependencies were written by this review.
