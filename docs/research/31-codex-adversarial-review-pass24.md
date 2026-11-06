# Adversarial review pass 24 — revision 9's candidate universe

Reviewed `v2-rethink`, HEAD `855098996b72a64392e39833e46f360434a24c5f`, on 2026-11-06 with repository Python 3.13.1. Only this review was written. Experiments and mutations ran through stdin, with bytecode and pytest cache writes disabled.

**Revision 9 is not sound as justified.** It implements its declared float filter, but that filter discards genuine geometric minima and still permits verdict changes from midpoint densification. Its within-record/across-record distinction also trades segment-boundary dependence for record-boundary dependence. The fix-breaks-adjacent-case pattern has not stopped.

## P24-F1 — High — exact equality of computed residuals discards exact geometric ties

**Location:** `v2/locfinder/measure/toy.py:91, 369–370`; design §2.2 step 2 and “Exactness does not discard genuine equidistance.”

**Executed input:** one one-way record, time/cost **1000/1000**, geometry

```text
(-1,2), (195,-145), (189,-143), (-7,4)
```

Origin `(0,0)`, destination `(-7,4)`. All coordinates are small exact integers. The first and last segments lie on **3x + 4y = 5** and **3x + 4y = -5**, respectively. Their exact nearest positions are `(3/5,4/5)` and `(-3/5,-4/5)`: both squared distances are **exactly 1**. Exact projection parameters are **2/245** and **237/245**. The connecting segment is over 237 m away and cannot compete.

The implementation computes:

| occurrence | computed residual | arclength | step 2 |
|---|---:|---:|---|
| first arm | 0.9999999999999999 | 2 | kept |
| last arm | 1.0 | 488.3245553203368 | discarded |

These residuals are **adjacent binary64 values**, one ulp apart. Total length is `490 + sqrt(40)` = **496.3245553203368 m**. Keeping only the first arm reports **996.7640294933123 s**, ten-minute **FAIL**, for both objectives. Keeping both exact geometric minima reports **16.912135995005965 s**, **PASS**. The latter leaves only 8 m of network travel, plus `1/1.26` connector seconds. The old executable rule confirms the two-candidate result; the exact rational projection calculation independently establishes that both are genuine minima.

**The claimed remaining subdivision residues are not exhaustive.** Applying the existing `split_segments` transform to this very input inserts exact collinear midpoints. The last-arm computed residual becomes **0.9999999999999943**; it now wins, and revision 9 reports **16.91213599500585 s**, PASS. Thus midpoint densification still changes **996.764 s FAIL → 16.912 s PASS**, without splitting a record or changing the measured line. The problem is projection arithmetic, not a final summation error.

**Minimal fix — design amendment to the meaning of exact minimum:** compare geometric distances with a robust predicate, rather than comparing rounded `hypot` residuals. For binary64 input coordinates interpreted as exact rationals, a clamped point-to-segment **squared** distance is rational. Compare those values exactly, or use certified error intervals with an exact fallback when the ordering is unresolved. Retain all exact ties, then specify how the selected projections and residuals are rounded for subsequent arithmetic. Replacing only `hypot` with a correctly rounded norm is insufficient: its projected-point operands have already rounded.

**Do not restore a within-record 0.01 m band.** No positive geometric band is required to preserve an exact tie. A fixed absolute or ulp allowance is also not an exact-minimum rule: it admits strictly more distant positions, and cancellation can make projection error exceed a fixed residual-ulp allowance. An arithmetic error bound should trigger more accurate comparison, not turn uncertainty into geometric eligibility. Alternatively, explicitly adopt minima of a specified rounded computation and withdraw the geometric-equidistance and subdivision claims; that preserves the defect as a policy consequence.

## P24-F2 — High — a degree-two record split restores the removed verdict flip

**Location:** design §2.2 steps 2–3; `toy.py:369–376`; record representation transforms in `invariants.py`.

**Executed input:** origin `(49.995,0)`, destination `(100,0)`, one-way movement, no penalties. Compare three representations of the same uniformly weighted straight road:

| representation | time/cost records | origin candidates | both reported times |
|---|---|---:|---:|
| one record, `(0,0),(100,0)` | 1199.95/1199.95 | 1 | 600.0349975000001 s, FAIL |
| one record, `(0,0),(50,0),(100,0)` | 1199.95/1199.95 | 1 | 600.0349975000001 s, FAIL |
| two records, `0→50`, `50→100` | each 599.975/599.975 | 2 | 599.9789682539683 s, PASS |

The new midpoint node is a pure degree-two subdivision; weights are apportioned proportionally, and connectivity supplies the same legal traversals. On one record, step 2 removes the clamped start at 50 m because its residual is **0.005 m**, against zero. On two records, that start is its record's exact minimum, so step 3 admits it. Taking the 5 mm connector and only the second record costs `0.005/1.26 + 599.975`, which passes ten minutes. This is the amendment's own motivating case, restored solely by moving the subdivision into the record structure.

**The one-ulp version also executes:** split P24-F1's record at `(195,-145)`, assigning weights `1000*245/L` and `1000*(245+sqrt(40))/L`, where `L=490+sqrt(40)`. The same residuals **0.9999999999999999 and 1.0** now both survive on separate records. Both objectives report **16.912135995005894 s**, PASS, against the unsplit record's **996.7640294933123 s**, FAIL.

The superseded rule agreed on the last two representations: both exposed that clamped segment start. Revision 9 separates them. Record boundaries now determine whether a near position competes, even when those boundaries represent no physical distinction.

**Minimal fix — design amendment:** define the attachment object independently of source record segmentation, with an explicit correspondence back to routing records. At minimum, specify how pure degree-two subdivisions with identical direction and proportional weights are normalised before the within-object minimum is taken. Keep distinct routing weight alternatives; grouping by `osmid` or rounded edge identity is not a valid substitute. Another coherent policy is exact minima globally, but that withdraws the across-road band. If record-relative attachment is deliberately retained instead, declare record segmentation part of the estimand and withdraw representation independence. Merely adding another regression cannot reconcile these policies.

## P24-F3 — High — within-record minimum multiplicity is an unexercised dimension

**Location:** `invariants.py:SCENARIOS`; conformance corpus; `toy.py:nearest_on_graph`; mutation coverage.

Installed this uniform wrong implementation before importing the tests:

```python
real = toy.nearest_on_graph
def wrong(*args, **kwargs):
    found = real(*args, **kwargs)
    counts, kept = {}, []
    for a in found.candidates:
        counts[a.edge] = counts.get(a.edge, 0) + 1
        if counts[a.edge] <= 4:
            kept.append(a)
    return toy.NearestOnGraph(tuple(kept), found.global_min_m)
toy.nearest_on_graph = wrong
```

This silently caps **occurrences per record**, independently of graph depth, destination count, coordinates, residual value and fixture names. Every surviving candidate is correct. Instrumenting the baseline full suite found that no executed call returned more than **three candidates on any one record**; the added equidistance anchor exercises two.

**Result:** baseline and mutant each pass **576 tests, with 24 skipped**, across conformance, invariants and mutation guards. Each full-suite run has **1066 passed, 24 skipped, 22 setup errors and one failure**, with the same environment denials. The mutation adds no failure. The 23 blocked tests cannot be called passing here; the observed call multiplicity explains the gap in everything exercised.

**Executed distinguishing input:** one one-way record with geometry beginning at `(0,0)`, repeating the excursion `(1000,0),(0,0)` **eight times**, then ending at `(0,1000)`. Total length **17000 m**; time/cost **8500/8500**. Origin `(0,0)`, sole destination `(0,1000)`.

There are **nine zero-residual origin occurrences**, at arclengths `0,2000,…,16000`. Correct selection uses the last and reports **500.0000000000001 s**, PASS. The cutoff retains arclengths `0,2000,4000,6000`; its best leaves 11000 m and reports **5499.999999999999 s**, FAIL. Eligibility and the global nearest distance remain correct. This is a fourth missing dimension: completeness over a record's retained geometric minima.

**Minimal fix — instrument correction, no estimand amendment:** declare and vary minimum-occurrence multiplicity, anchor optima at different occurrence positions, and check the complete candidate set against an independent geometric construction. Include interior projections and repeated vertices, direction changes and zero-length runs. A second axis-aligned two-arm example would not exercise this dimension.

## P24-F4 — Medium — a NaN query manufactures an authoritative absence

**Location:** `toy.py:269, 336, 667, 692–701`; `test_invariants.py:test_a_non_finite_input_is_refused`; design §2.5 and the outstanding numerical-domain rule.

**Confirmed, unchanged by revision 9.** On a bidirectional edge `(0,0)→(100,0)` of time/cost **100/100**, destination `(100,0)`, the valid origin `(0,0)` reports **100 s**, PASS. Origin `(NaN,0)` is accepted and returns:

```text
objective1_s = objective2_s = None
origin_candidates = n_journeys = 0
origin_nearest_m = None
eligible = (0,)
```

In particular, NaN residuals fail even their own step-2 equality test. The nonempty graph loses its measured minimum, and `evaluate` returns its exhaustive-absence result. The decision is **invalid query → genuine NO_PATH**, an authoritative failure under §2.5, rather than input rejection. Tests currently validate edge constructor fields, not query coordinates.

**Minimal fix — boundary validation plus the already-required domain amendment:** reject non-finite origin and destination coordinates at every public query entry point before projection, including on an empty graph. Specify invalid-input handling separately from absence. This check does not settle finite-input underflow, overflow or admissible caps and weights; those remain part of P22-F9.

## Evidence claims and the other readings

**The 31 untransformed scenarios agree:** comparing the complete `reported()` dictionaries under both executable rules found zero differences. This finite measurement is correct; it does not extend to all inputs or all transformed inputs.

**The stated U-shaped example is correct:** `(0,1),(200,1),(200,-1),(0,-1)` retains arclengths 0 and 402 and reports **0.7936507936507936 s** under both rules. The inference that this establishes preservation of genuine equidistance is refuted by P24-F1.

**The near-tie measurement is correct:** with the far arm at residual **1.0099 m**, the old rule reports **0.8015079365079365 s**; at **1.0101 m**, **1000.7936507936507 s**. Here “9.9 mm” and “10.1 mm” are excess residuals above the nearest arm's 1 m, not absolute residuals. Revision 9 reports approximately **1000.7936507936508 s** in both cases.

**Both reading-marked conformance cases pass unchanged under both rules.** The corpus alone does not distinguish them.

**The reported residues reproduce on the declared scenarios:** `zero_length_segment` changes count **2→3**, time **100.0 s** unchanged; the curved reverse-traversal scenario changes all four totals by **-1.4210854715202004e-14**. These are observations on that finite set, not bounds on subdivision effects; P24-F1 adds a large verdict-changing residue.

The competing readings must stay distinct:

| reading | consequence |
|---|---|
| nearest per segment, then global band | superseded executable rule; midpoint-clamped candidates can compete |
| one arbitrary nearest position per record, then band | loses multiple occurrences even in the exact axis-aligned U example; incompatible with retaining every minimiser |
| all positions within a geometric distance band | generally a continuum; requires a different optimisation problem, not this finite generator |
| all exact global minimisers | finite via segment projections, but drops a second road whose true residual is 1.009 m against 1 m; withdraws the declared across-record band |
| all exact record minima, then global band | revision 9; finite and structurally intelligible, but its float implementation and representation justification fail above |

**Occurrence identity and representative selection remain coherent.** Filtering before occurrence deduplication preserves the smallest-residual description whenever that occurrence survives: a discarded lower-quality duplicate cannot have been its preferred representative. Distinct self-crossing occurrences remain distinct. Exact equality here must not be confused with rounding an occurrence key.

**Zero-length segments introduce no new step-2 inconsistency.** On `(-1,0),(0,0),(0,0),(1,0)`, both vertex indices **1 and 2** survive at arclength **1**, fraction **0.5**. Their equal distance survives the filter; they are distinct structural vertices. With an entirely constant geometry of **n vertices**, the current `t=0` convention generates **n−1 candidates**, all fraction/arclength zero; the terminal vertex is never generated. Two and three vertices yield one and two candidates, respectively. Coincident origin/destination return zero network time, even with a positive stored edge weight. Freeze this total-zero convention in the geometry amendment; step 2 itself neither adds nor removes these equal-residual candidates.

**Retaining `global_min_m` after step 2 is correct for finite residuals:** `min(records' minima) = min(all segment residuals)`. A smaller pre-filter minimum cannot have been discarded. No separate pre-filter value is needed for the off-network bound. Numerical certification of a geometric lower bound remains part of the arithmetic/domain debt; this identity alone does not certify rounding safety. NaN violates the finite premise, as P24-F4 demonstrates.

## The outstanding rules

**P22-F1, geometry arithmetic: the owner's sum calculation is correct, but the proposed extension is insufficient by itself.** For the three binary64 segment lengths `0.1, 0.2, 0.3`, their exact rational sum is **21617278211378381 / 36028797018963968**. Its distances from `0.6` and `0.6000000000000001` are **1/2^55** and **3/2^55**, respectively. Thus `0.6` is correctly rounded; left accumulation is less accurate. My earlier left-accumulation experiment demonstrates the ambiguity, not a reason to prefer its 1 s result.

The existing geometry counterexample still reports **1000 s**: A has geometry `(0,0),(.1,0),(.1,.2),(.1,.5)`, time/cost **6/1**; B has `(0,0),(.1,0)`, **1000/(1/6)**. Origin `(0,0)`, destination `(.1,0)`. Exactly rounded total length **0.6** gives A fraction **0.16666666666666669**, so B wins; left accumulation creates a cost tie and the **1 s** answer. Do not choose the arithmetic by the preferred verdict.

The amendment must cover total and prefix sums, term formation, differences, dot products, norms, projection/clamping, fractions, interval subtraction and zero-total geometry. Define primitive rounding and fused/reassociated operations, intermediate range behavior, and deterministic norm semantics, or qualify a specific runtime/platform with decisive fixtures. An exactly rounded sum cannot repair differently rounded inputs to that sum, and cannot repair P24-F1's equality predicate. This still blocks T3's freeze, not ordinary implementation.

**P22-F6 / P23-F3, uniqueness: still unresolved and not repaired or newly broken by revision 9.** Re-executed the two-record witness: straight geometry `(0,0),(50,0),(100,0)` at **2/2**, versus `(0,0),(50,.004),(100,0)` at **1.9936507809117465** for both weights, with origin `(25,0)` and destination `(75,0)`. Both winners report **time 1, cost 1**, the same destination and full rounded route identity. Edge order selects network seconds **1** or **0.9968253968355556**. Removing this field from invariant comparisons avoids rejecting either winner; it does not promise unique reconstruction. Declare the complete observable, then specify interval/attachment/record tie-breaking or permit a set of tied reconstructions and give T10 its own rule. The separate normative final-cost-discriminator debt also remains.

**P22-F9, admissible numerical domain: still unresolved; P24-F4 confirms the additional query-boundary failure.** Finite constructor components do not guarantee finite intermediates or nondegenerate arithmetic. Exactly rounded geometry summation alone does not change that conclusion.

## Instrument checks and verdict

**`measure_split_divergence` is worth keeping as a finite-domain diagnostic, not as evidence of general subdivision safety.** Its current signature is exactly `{'zero_length_segment': {'origin_candidates': (2,3)}}`; tolerance hides the small curved difference. The unchanged signature previously missed the motivating flip because its witness was outside the scenarios. That omission is now repaired: under the old mutant, the newly added `subdivision_sensitive` scenario contributes **600.0349975000001→599.9789682539683 s** and count **1→2** to the signature. It therefore does distinguish the two rules on the current domain. Add the geometric-tie and record-split dimensions above, retain raw differences alongside decision predicates, and correct the stale per-segment-rule explanations in `invariants.py` and the subdivision test. Do not assert that the observed exception list exhausts admissible behavior.

**The rebuilt attachment-switch regression is sound for its stated purpose.** Its two different records at residuals **0.01 and 0**, common `osmid=(7,)` and length 100, legally survive the across-record band; their affine connector/network tradeoff switches selection while the reduced route stays fixed. It demonstrates that reduced route equality cannot establish a held journey. It does not claim equality of the full directed identities or establish within-record tie coverage.

**`EXPECTED_COVERAGE` is accurate:** all **14 pairs** reproduce, including revision 9's **(invariants caught, corpus not caught)** row. Nine mutants escape the corpus, one escapes invariants, and none escapes both. This is coverage of the installed mutations, not of P24-F3.

**The corpus digest recomputes exactly:** `f5ced7a0f1aeab2f776bea9cc90668678e475cfe1a8cbbba14200ee69011608a`.

Baseline and occurrence-cutoff runs each produce **576 passed, 24 skipped** for the three instrument files. Their full-suite results are identically **1066 passed, 24 skipped, 22 setup errors and one failure**. The blocked acquisition/frame tests encounter the known pytest temporary-directory/lock-file permission denials. **Those denials are an environment limit, not a finding.** I did not redirect temporary output into the repository. Pre-existing unrelated changes were left intact. Additional changes to `v2/.gitignore` and a pass-25 review appeared during this pass; I did not author or modify them.

**Final judgment:** revision 9 removes its specific straight-edge segment-clamping failure but remains unsound as a geometry-preserving replacement. It both retains a verdict-changing densification failure through rounded projection equality and introduces record-boundary dependence through its asymmetry. The fix-breaks-adjacent-case pattern has not stopped.
