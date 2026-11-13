# Pass 40 adversarial review: phase 4a.2

Reviewed `v2-rethink`, HEAD `7d1c60bdff115af962786186ca1ff6bd72da3bca`, on 2026-11-12. The prompt names `8d86cc6`; the requested checkout adds the prompt itself. Production code, tests, scripts and published artifacts were left unchanged.

**Findings: one High, four Medium, three Low.** The published 51.42% / 48.32% figures reproduce exactly. The square-root bracket survives. The comparator has a false `DIFFERS` case, its advertised refinement limit is not reached, its equality metadata can misclassify or hide unresolved cases, and signed interval division is unsound. The mutation results reproduce but do not establish the claimed protection against crashes or cover several important rules.

## Reproduction and evidence

From the repository root, using the specified interpreter:

```powershell
.\v2\.venv\Scripts\python.exe -B .\docs\research\41-codex-review-pass40-counterexamples\run_all.py
```

Add `--suite` to run the complete repository suite as well. Individual reproducers are independently runnable with that interpreter:

| Script | Evidence |
| --- | --- |
| `core.py` | Brackets, signed division, selection labels, refinement, equality metadata, independent Decimal containment and W5 proof |
| `population.py` | Published draws checked independently, seed/count/precision sensitivity, omitted time assignment, unenforced admissibility |
| `t4.py` | All 222 T4 journeys reconstructed with independently computed exact rational projections, segment lengths and costs |
| `mutations.py` | Original 21 mutations and self-test, four surviving additional mutants, crash counted as caught, retired-guard counterexamples |

The corresponding `*-output.json` files contain the numbers. `remeasured.json` matches the published JSON in every field except runtimes. `measurement-output.txt` captures the measurement program's printed claims. `suite-output.txt` records the successful full-suite run: **1,300 passed, 24 skipped**, exit 0 (the double quiet configuration emits progress rather than a summary; its progress contains 1,300 `.` and 24 `s`).

**Temporary-directory handling:** all newly created scratch directories were outside the repository. Mutation runs copy only the needed files to the system temporary directory and restore/check the copied source. The first full-suite attempt hit Windows permission errors reopening directories created with mode `0700`. The successful attempt changed `os.mkdir` to use ordinary permissions within the pytest process and passed an explicit external `--basetemp`; `run_all.py --suite` includes that workaround. No product assertion was bypassed. Existing inaccessible repository directories were not created, modified or removed by this review.

## F1 — High: default or duplicate labels produce false `DIFFERS`

**Claim refuted:** `certify_selection` asks, “Did the convention's selection match the real argmin?” and documents that an alternative “certified **strictly cheaper** makes this `DIFFERS`.” `Journey.label` is documented as carrying whatever the caller uses to name the selection and defaults to `""`.

**Reproducer:** `core.py`, `duplicate_default_labels`.

```python
a = c.Journey(full_edge_costs=(1.0,))
b = c.Journey(full_edge_costs=(2.0,))
print(c.certify_selection([a, b], chosen=0))
```

**Result:** `DIFFERS`, `convention=''`, `certified=''`, precision 8. The selected cost is exactly 1 and the only alternative is exactly 2. This must be agreement.

`certify_cheaper` returns the winning **label**, and `certify_selection` tests `winner == other.label`. When labels coincide, a win for the selected candidate is mistaken for a win for its alternative. This is reachable with ordinary nonnegative full-edge costs and every constructor default; there is no uniqueness check or documented precondition. The published population uses distinct labels, so this defect does not change its reproduced counts. Return/compare candidate identities or indices rather than descriptive labels.

## F2 — Medium: refinement claims a precision it never evaluates

**Claims refuted:** `Certification.precision` is “the precision reached”; `certify_cheaper` says `None` means intervals “still overlapped at `max_precision`”; the module promises refinement “up to a **declared limit**.”

**Reproducer:** `core.py`, `precision_limit`.

A is a full traversal of the admissible unit segment at cost 1. B has full-edge terms `(1.0, 2.0**-150)`, so its exact cost is `1 + 2**-150`. Choose B.

**Results:**

| Check | Result |
| --- | --- |
| Default limit 192 | `UNRESOLVED`, reported precision **192** |
| Instrumented precisions actually tried | **8, 16, 32, 64, 128** |
| Direct interval comparison at 192 | A strictly below B: **True** |
| Limit 256 | `DIFFERS`, certified A, precision 256 |
| Limit 7 | Reports precision **7**, without evaluating any interval |

The loop doubles 128 to 256, exits, then reports `min(256, 192)`. It needs a final evaluation at the declared cap, and honest reporting of what was actually attempted. The published draws all resolve by 64, so their figures survive this defect.

**An associated rationale also fails.** The constant's comment says `2**-192` is “far below any gap a binary64 cost can express,” and reaching it means “no reported quantity distinguishes” the costs. Binary64's minimum positive gap is `2**-1074`. With a connector residual `1e-100`, the two *reported* costs in the reproducer are **7.936507936507937e-101** and **2e-100**. Default certification is unresolved; at 512 it agrees. Such a residual can arise from an admissible query `(0, 1e-100)` against an ordinary horizontal unit segment. An absolute root-bracket width is not a universal bound on representable cost gaps. Finite caps are legitimate; this justification for the cap is not.

## F3 — Medium: equality metadata confuses unknown with unequal, and can hide unequal unresolved alternatives

**Claims refuted:** `_exactly_tied` says unsupported cases are “reported as **unknown** otherwise rather than guessed”; `Certification.exactly_tied` is meant to distinguish actual equality; the measurement output calls false values “NOT tied” and declares the invalidation condition fired.

**Reproducer:** `core.py`, `equal_but_not_exactly_tied` and `first_unresolved_masks_unequal`.

**Results:**

1. Two identical journeys with `connector_sq=(Fraction(1),)` return `UNRESOLVED`, **`exactly_tied=False`**. Both exact costs are `50/63`. `_rational_cost` rejects all connectors, even perfect rational squares.
2. A complete traversal of `(0,0) -> (1,1)` at cost 1 against a full edge at cost 1 also returns **False**. Its fraction is exactly `sqrt(2)/sqrt(2)=1`.
3. Choose B of cost `1 + 2**-150`. Give it an identical rational-cost alternative and the cheaper unit-segment traversal from F2. Order `[B, rational_tie, cheaper]` reports **`exactly_tied=True`**; order `[B, cheaper, rational_tie]` reports **False**, with the same candidate set and status. Only the first undecided alternative is retained. Thus a recognized tie can hide an unresolved unequal alternative from diagnostics that treat tied unresolved cases as harmless.

For well-typed valid inputs, I found no false positive in `_rational_cost`'s recognized rational subset: its perfect-square checks and rational span formula are sound. Its incompleteness is the issue; `_exactly_tied(False)` does not prove inequality. Preserve a tri-state result and enough per-comparison information to distinguish proven ties, proven unequal pairs and unknown equality. The published JSON has zero unresolved cases, so the conflation is **not numerically exercised in those published figures**. It is visible in the output schema and invalidation message, and prevents those messages from being reliable for other populations or caps.

## F4 — Medium: division by a positive interval fails for negative numerators

**Claim refuted:** `Interval` is “a closed rational interval” whose operations do not round; `divided_by` promises division by a “strictly positive interval,” with anything else a caller error. No nonnegative-numerator precondition is stated.

**Reproducer:** `core.py`, `signed_division`.

| Numerator / denominator | Returned | Correct enclosure |
| --- | --- | --- |
| `[-1,1] / [1,2]` | `[-1/2,1]` | `[-1,1]` |
| `[-2,-1] / [1,2]` | `[-1,-1]` | `[-2,-1/2]` |
| `[-2,-1] / [1,4]` | Raises `ValueError: an inverted interval: [-1/2, -1]` | `[-2,-1/4]` |

The first two results exclude attainable values -1 and -2 respectively. Use the extrema of the four endpoint quotients, or implement sign-aware formulas.

**Reachability matters:** valid traversal spans are nonnegative; negative cost scaling happens *after* fraction division. I did not find a well-formed, uniquely labeled journey whose certified pairwise ordering is wrong through this bug. It is an unsound public primitive, not evidence that the published positive-span population's ordering is wrong. Negative scaling itself survived the independent checks.

## F5 — Medium: the mutation self-test does not prevent crashes being counted as catches; important rules have no attacks

**Claims refuted:** `--self-test` prints “so a crash cannot be banked as a catch”; the smoke comment says it exercises “every branch a mutation below touches”; the engineering note relies on “21 mutations all caught” as evidence for the comparator's tests.

**Reproducer:** `mutations.py`, `invalid_mutant_outside_smoke`, `discarded_failure`, `extra_mutants`.

The supplied **21/21 caught** and `--self-test` exit **0** both reproduce. Their scope is narrower than the claims. Insert an undefined-name access in `Journey.cost_interval` only when there are three full-edge terms. The smoke's full-edge examples have at most two terms; the suite includes three.

**Result:** the suite stops with **`NameError`**, **1 failed, 30 passed**. The harness prints **`caught NameError outside smoke`**, **`all 1 mutations caught`**, and exits **0**. The mutation is broken by the harness's own `BROKEN` definition. Its `run_tests()` reduces every pytest failure to a boolean and throws away the exception information. The self-test establishes detection of its one undefined name on its fixed smoke inputs, not the general protection it claims.

Four additional, non-equivalent mutations each leave **all 40 fixtures passing**:

| Mutation absent from the supplied list | Demonstrated wrong behavior |
| --- | --- |
| `_exactly_tied` returns True for recognized rational costs regardless of equality | Exact costs **1 and 2** reported exactly tied when comparison is left unresolved |
| `_rational_sqrt_exact` accepts nonsquares using integer root approximations | `1/(1+sqrt(2))` declared exactly tied with **1/2** |
| `_NeedsPrecision` branch returns the zero interval | A positive full traversal of exact cost **1** certified agreeing against a cheaper **0.5** alternative |
| Exhausted precision reports `max_precision + 123` | Default unresolved precision reported as **315** |

These attack equality recognition, insufficient-denominator refinement and precision accounting—rules that none of the 21 supplied mutations attacks. The zero-length test never exercises the positive-but-too-small denominator branch. The tiny-segment witness is valid for this public API; it is outside the toy graph's micrometre floor, which explains why the manufactured population does not encounter it.

I found no equivalent mutation among the current 21; their changed arithmetic or guard behavior is distinguishable. “All 21 caught” is a reproducible finite result, not completeness or a guarantee that every caught mutant failed semantically.

## F6 — Low: the two retired mutations were not equivalent over the documented domains

**Claim refuted:** the engineering note says “Two further survivors were **equivalent** mutants”—removing the denominator guard and removing the selection-index guard.

**Reproducer:** `mutations.py`, `removed_denominator_guard` and `removed_index_guard`.

**Results:**

* Remove `other.lo <= 0`: `[1,2] / [-2,-1]` returns **`[-1,-1]`** instead of refusing the denominator. The guard covers negative intervals, not just a denominator endpoint equal to zero.
* Remove `0 <= chosen < len(candidates)`: `chosen=-1` on a one-candidate set returns **`UNRESOLVED`**, precision 192, `exactly_tied=True`, instead of `IndexError`. Python accepts the negative list index, and the enumeration then compares the candidate against itself because its index 0 is not -1.

The replacements in the current harness do not reintroduce these production bugs. The problem is the documented equivalence conclusion and the missing boundary fixtures that supported it. Equivalence held only for the particular zero endpoint / positive out-of-range examples that had been tried.

## F7 — Low: “contains no near tie” is broader than the T4 measurement

**Claim refuted:** the JSON says “these fixtures have none”; the plan and engineering note say “**0 of 17 fixtures contains a near tie** under 10^6 ulps.”

**Reproducer:** `t4.py`, case `same_identity_alternatives_still_compete_on_weights`.

**Results:** it contains distinct rounded costs **401.5999999999999 / 401.6**, and **402.39999999999986 / 402.4**. Each gap is **2 ulps**. Thus **1 of 17** fixtures contains such a pair. The script only measures the minimum against the next distinct cost.

This does **not** reverse the decision to skip a cost-argmin sweep. Both pairs are well above this fixture's minimum. The stronger audit reconstructed **222 journeys** and found:

* **0** binary64-equal / real-unequal pairs anywhere in the corpus;
* all **15** cases with journeys select a real minimum; the other two have no journeys;
* every used nonzero partial and every connector has an exactly rational cost here. The one diagonal edge is used as a full edge, or with a zero partial, so it does not create a hidden irrational tie;
* the original minimum-margin result is **0/17**, the discriminator candidate count is **11/17**, and exactly **1** case has differing times at the minimum.

“Changes the reported time” is generally an incomplete consequence test: destination and route identity are also reported. I checked them too. In the ten equal-time T4 tie cases, all tied minima share one destination and one route identity. Only `equal_cost_alternatives_rank_by_travel_time` has two routes/times. Thus the narrow consequence count also survives for **this corpus**, despite the insufficient general argument. State the margin result as a margin above the minimum.

## F8 — Low: two population guarantees are assumptions rather than generated fields/checks

**Claims refuted:** “B is given the smaller travel time, so **the convention always selects B**”; A is a “random admissible record.”

**Reproducer:** `population.py`, `time_key_is_assumed` and `admissibility_not_enforced`.

`Journey` has exactly five fields: `full_edge_costs`, `partials`, `connector_sq`, `label`, `access_speed`. Neither generated candidate has a time, and the selection code is never invoked: `chosen=1` is supplied directly. Using the same tied costs with A time **1** and B time **2** makes the actual toy ranking select **A**. Reversing the assignment makes it select B. The experiment is correctly interpretable as **conditional on stipulating B wins the time key**; it does not test that integration.

The generator also has no lower-segment-length check. A `Random` subclass returning in-range uniform steps of `1e-8` makes `draw()` return a segment of length **1.4142135537782532e-08 m**; the repository's actual `ToyEdge` admissibility check rejects it against **1e-6 m**. These step values are also reachable in the support of binary64 uniform sampling (and a neighborhood is rejected), but this adversarial RNG is a construction witness, **not a claimed natural-seed observation**. Exact zero steps are likewise allowed by the sampling support; zero-cost draws are skipped by the measurement.

Neither issue contaminates the published sample: all **10,000** actual draws were checked and are admissible, nonzero-cost, distinct-segment traversals with equal rounded A/B costs. Minimum observed segment lengths were recorded in `population-output.json`. `seg_o == seg_d` is impossible for the implemented generator because `n` is always 2–4 and two distinct segment indices are sampled. Describe the selection as stipulated, and enforce the admissibility condition if it is part of the population definition.

## Claims that survived, with what was run

### A. Square-root bounds, width and nesting

`core.py` checked **7,028** `(q,k)` combinations, including zero, `q=2**-2148`, a 4,097-bit integer, large nonintegral rationals, 1,000 random 256-bit rational pairs, and precisions 0, 1, 8, 53, 128, 192 and 1074. All satisfy `lo**2 <= q < hi**2`, exact width `2**-k`, nesting and `2*s_k <= s_(k+1) <= 2*s_k+1`.

The proof applies to every nonnegative rational: `isqrt(floor(x))` is `floor(sqrt(x))`; squaring the integer endpoints gives the stated inequalities. Refinement does not otherwise rely on stored nesting: it recomputes the intervals at each precision. Independent enclosure at each precision is sufficient for soundness, even without invoking nesting.

### B. Reachable cost arithmetic and termination

For well-formed spans and distinct labels, **400** independent 100-digit Decimal cost calculations fell inside the exact rational intervals at precision 128. These included negative partial-cost scaling and irrational connectors. Full-edge interval sums were invariant under every permutation of `(0.1,0.2,0.3)`. The connector coefficient is applied correctly in the exact model. No wrong pairwise real-cost ordering was found on this domain.

For finite integer caps, `_NeedsPrecision` cannot loop forever: each catch doubles `k` and the loop is bounded. A positive segment of length `2**-200` stays unresolved by default and resolves at 256; a genuine all-zero record returns the exact zero interval at precision 0. The exact-radicand guard does not mask such a record. The cap/reporting and insufficient-precision test gaps are F2/F5.

### C. Headline rate and its interpretation

The original command with **5,000** draws, seed **20261112**, cap **192** reproduces:

| Regime | AGREES | DIFFERS | UNRESOLVED | Rate | Maximum precision actually needed |
| --- | ---: | ---: | ---: | ---: | ---: |
| UTM-like | 2,429 | 2,571 | 0 | 51.42% | 64 |
| Toy | 2,584 | 2,416 | 0 | 48.32% | 64 |

Independent 100-digit Decimal evaluation of **all 10,000** real costs reproduces the same direction counts. The near-half split is structurally expected: B is placed exactly at A's computed rounded cost, so choosing B loses precisely when A's accumulated rounding error is positive. It measures the sign of that error in this construction. There is no theorem of an exactly symmetric 50/50 distribution, and it is not a frequency over all cost ties, full/full ties, or real graphs. Moving B 16 ulps down/up puts it strictly below/above A's independently computed real cost in every audited draw; those alternatives are no longer manufactured ties.

The seed, count and cap are disclosed in the JSON, and the CLI permits changing them. At 1,000 draws, seeds **0/1/2/20261112** give UTM rates **49.9/49.6/49.8/51.5%** and toy rates **50.6/51.6/45.8/49.3%**. The original seed's 1,000-draw prefix differs from its 5,000-draw rate. Caps **32, 48 and 63** yield **1,000 unresolved out of 1,000** in each regime, whereas cap **64** resolves every one. For 48/63 the loop actually stops at 32 (F2). The script's term `decided_draws` includes unresolved draws, and its rate divides by all retained draws; this has no numerical effect on the zero-unresolved published artifact, but under a lower cap a displayed zero `DIFFERS` rate is a censored count, not evidence of agreement.

### D–F. T4, harness and fixture expectations

T4's narrow argmin conclusion survives the independent exact reconstruction (F7). The 21-mutant result and the single injected-NameError self-test reproduce (F5); the two retired equivalence claims fail outside their original examples (F6).

I found no fixture expectation demonstrably read off a comparator run. The lattice-square family and middle-segment fixture were discovered through mutation/search, but their expectations are then derived from exact inequalities and length arithmetic. Discovery by execution does not make those expectations circular.

W5's Decimal check is independent of `certify.py` and `exact.py`: Decimal computes `sqrt(2)`, and `Fraction(binary64_B)` gives B's exact rational value. At 100 digits the gap is **4.1161781903271303350690105193714848801823320262009267521537892961149612465672358427e-17**. Sixty digits comfortably suffice for that comparison. As an exact check requiring no numerical square root, `core.py` proves `(1+B)**2 - 2 = 37781456166601769 / 324518553658426726783156020576256 > 0`; since `1+B > 0`, B is strictly above `sqrt(2)-1`. The test does change the global Decimal context without restoring it, a minor test-isolation weakness rather than an invalid W5 expectation.

One additional interface limitation is reproduced in `core.py`: with selected cost **5** and alternatives ordered **4, 1**, `Certification.certified` names the **4** candidate. The implementation explicitly documents returning the first cheaper witness, so I have not counted that as a separate implementation defect. Consumers must treat that field as a witness disproving the chosen argmin, not as the global certified argmin promised by the broader plan's wording.
