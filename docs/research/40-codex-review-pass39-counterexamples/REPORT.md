# Pass 39: adversarial review of the pass 38 repairs

Reviewed repair commit **2fb706bd7ccc28a1083dcdb43d66d37032c4fe00**, branch `v2-rethink`.
The actual checkout was **57663776b00d2461b649c784c321b0b0636caf12**. Its only difference
from the requested commit is the addition of `40-codex-review-pass39-prompt.md`; the reviewed
implementation, tests, design and measured artifacts match the requested commit. No checkout,
implementation, existing artifact or existing report was changed.

**Seven findings: 5 Medium, 2 Low; no High.** The corrected exact-parameter comparison,
`exact_occurrence`, prefix-subtraction explanation, finite-coordinate fingerprint and structural
comparator survive the attacks described below. The remaining failures concern guarantees,
measurement guards and coverage, rather than a newly demonstrated defect in the shipped primitive.

## Run the evidence

From the repository root:

```powershell
v2/.venv/Scripts/python.exe -B docs/research/40-codex-review-pass39-counterexamples/run_all.py
```

Every individual `.py` below also runs with `v2/.venv/Scripts/python.exe -B <script>` from the
root. [RESULTS.txt](RESULTS.txt) records the runner's output. A program passing means its review
assertions hold, including assertions that establish a defect. Mutations are compiled in memory;
no implementation source is rewritten. The runner disables pytest's cache and bytecode writing.
No temporary directories were created inside the repository.

The **43 exact-geometry fixtures pass**. All **24 existing mutants** pass their smoke execution and
fail the fixture suite in fresh processes. These failures include numerical assertions and legitimate
behaviour-changing exceptions; I do not equate every test failure with an assertion failure.

The full suite was also attempted from `v2/`, with bytecode/cache disabled and an explicit unique
`--basetemp` beneath `C:\Users\arikt\AppData\Local\Temp`. It encountered fixture errors and
terminated with `PermissionError: [WinError 5]` while accessing that **external** temporary directory.
A first-error run confirmed the same problem. I cannot certify the advertised 1,259/24 result in this
sandbox and do not report that environment failure as a repository defect.

## R1 — Medium — F1's replacement text overclaims the production arithmetic

**Claim refuted**, design §2.4 item 7, lines 545–548:

> decided on the **correctly-rounded residual**, in binary64, under both the production path and T0's exact path

**Reproducer:** [f01_and_f08_contract.py](f01_and_f08_contract.py).

It calls production's actual `_snap_network`, whose residual comes from `shapely.distance`, on a
point at `(0,0)` and the segment
`(56.31181001463545,64.61649631867172) → (112.6236200292709,129.23299263734344)`.
The closest point is the first endpoint. Results:

| quantity | result |
|---|---:|
| production residual | `85.71062678352851` |
| correctly rounded exact distance | `85.7106267835285` |
| production error | **1 ulp** |

The reproducer independently certifies the latter answer by comparing the exact squared distance
against the squared exact midpoints to its two neighbouring floats. This is not an inference from
`rational_sqrt` agreeing with itself. All coordinates and lengths are within the declared domain.

The narrowed scope is useful, but the new assertion about production is false. State that production
uses a computed GEOS residual and that **T0's exact path** uses the correctly rounded rational root.
Also repair `exact_segment_sq`'s surviving docstring claim that “both caps are therefore decided
exactly”; returning the primitive that *could* decide them is not using it to decide them.

**The scoped mathematical clause itself survives.** I enumerated its source-level decisions:

| location/quantity | comparisons and status |
|---|---|
| rational root | `q < 0`, `q == 0`; both exponent-bracketing inequalities; lattice-unit maximum; midpoint difference `> 0`, `< 0`; tie parity — exact rationals/integers |
| power-of-two helper | exponent sign — integer |
| projection | degenerate squared norm `== 0`, clamp `t <= 0`, `t >= 1` — exact rationals |
| partial length | negative `t` check — exact rational |
| prefix | segment-index bounds — integers; cache-present test selects the documented cache, not a numerical ordering |
| same-edge span | empty segment list; integer index bounds; tuple orientation `(segment,t)`; same-segment index equality; sign implicit in `abs(t_d-t_o)` — exact structural/rational decisions |
| zero-total convention | `total == 0.0` uses a float, but is equivalent to exact zero on the admissible domain: lengths are nonnegative and every nonzero admissible segment has length at least `1e-6`; no positive whole segment can round to zero |
| squared-distance ordering | the primitive returns an exact `Fraction`; D compares these exactly; A/C's residual comparisons belong to the explicitly excluded attachment predicates |

The old pass's independent checks still run: 2,004 certified root rounding cells, 400 cache
equivalences, 400 symmetric spans, and 2,005 agreements with the pilot's old exact-distance copy.

**The cap-policy questions.** The same script replays both caps: exact squared excess **`1e-12`**,
rounded residual **200 or 300**, and A/C/D all eligible. Item 7 explicitly chooses operational
rounded comparisons for the current path, so inclusive `<=` is not itself contradictory. However,
§2.2's standalone “distance”, “within” and “both are inclusive” wording does not tell a reader this;
put the arithmetic rule or an explicit cross-reference at §2.2's band and cap definitions.

Leaving an *alternative* exact cap open is defensible provided the current rounded convention is
clearly identified. Computing it is cheap: after obtaining `exact_sq`, compare it with
`Fraction(cap)**2`; no root or algebraic machinery is needed. Choosing it is a semantic amendment,
not an implementation optimisation: it can change attachment/availability and consequently E0's
known/unknown coverage and E1's eligibility and verdict operands. Measuring how often that happens
costs a paired experiment; computational impossibility is not a reason to defer it. Neither
candidate provenance nor a small residual error proves the estimands invariant.
The registered frame denominators remain fixed; the statuses and paired operands can change.

## R2 — Medium — F3's exception blacklist cannot distinguish invalid from wrong

**Claims refuted**, `mutate_exact_geometry.py`, `BROKEN` comment and smoke documentation:

> Errors that mean the MUTATION is broken rather than the behaviour changed.

> Its job is to make a structurally broken mutant raise before the suite is consulted.

**Reproducer:** [f03_mutation_validity.py](f03_mutation_validity.py).

Replace the integer floor in `math.isqrt(scaled.numerator // scaled.denominator)` with true division.
This is a valid Python mutation of an arithmetic operation, rather than an undefined identifier or
an import error. On the ordinary smoke radicand it raises:

```text
TypeError: 'float' object cannot be interpreted as an integer
harness classification: INVALID
```

Using the wrong numeric division is a legitimate behavioural defect. A `TypeError` does not establish
that the mutation tests nothing. The reproducer runs the mutated code and feeds its observed error
through the harness's actual classifier. The blacklist conflates two different reasons for a crash.

The opposite failure remains possible too. An existing mutation attacks the **same-segment** branch
of `same_edge_fraction`; smoke calls it only across segments 0 and 2. Replacing that branch's body
with a reference to an undefined name gives:

```text
broken same-segment branch: smoke passes
same-segment call: NameError
```

Thus a structurally broken mutant at that existing mutation site can still be banked as “caught”.
Invoking every public function once does not execute every mutation's changed expression.
Validity needs mutation-specific expectations and execution of the changed branch; exception class
alone is insufficient. This finding does **not** say one of the current 24 mutants has that defect.

## R3 — Medium — F3 still omits the cross-segment span summation rule

**Claim challenged**, engineering note §6:

> any “N of N caught” claim needs a validity check on each mutant

The **24/24 count is true**, but it does not cover every stated arithmetic rule. The next missing
rule is the single `math.fsum(terms)` at `exact.py:327`, distinct from the total and prefix sums
already mutated by the harness.

**Reproducer:** [f03_mutation_validity.py](f03_mutation_validity.py), which launches its `--suite`
mode in a fresh process. Replace that span `fsum` with a loop accumulating from the left. All
**43 fixtures still pass**, but a complete traversal of
`(0,0),(0.1,0),(0.1,0.2),(0.1,0.5)` returns:

| quantity | result |
|---|---:|
| mutant fraction | **`1.0000000000000002`** |
| required fraction | **`1.0`** |
| left-accumulated span | `0.6000000000000001` |
| specified `fsum` total/span | `0.6` |

This is W1's already known sensitivity, tested through the unprotected span composition. The
required answer follows from applying the same `fsum` rule to the same whole segments in numerator
and denominator; no expected value was copied from the implementation.

**Existing mutant equivalence:** [verify_mutants.py](verify_mutants.py) recompiles all 24 in memory,
executes the exact smoke string and runs the 43 fixtures per mutant. All are caught. Inspection of
the failures/rules and the independent numerical anchors found no equivalent mutant among them.
The repaired floored-scaling mutant is executable and caught. The two newly added interpolation and
destination-partial mutants are also caught. The old retired-equivalence checks still pass, including
2,000 rounded-scaling checks with **224 changed indices and zero changed answers**.

## R4 — Medium — F4's “provenance, not an answer finding” conclusion exceeds the measurement

**Claims refuted**, `t0-attachment-pilot.md:372–378` and pass 38's write-up:

> a provenance finding, not an answer finding

> write different manifests for the same points while reporting the same answers

**Reproducer:** [f04_identity_and_answers.py](f04_identity_and_answers.py).

On `(0,0)→(1,2)`, queried from `(1,1)`, both paths retain a single A candidate at rounded XY
**`(0.6,1.2)`**, with the same residual and rounded parameter **`0.6`**. Nevertheless its parameters
are **`5404319552844595/9007199254740992`** and **`3/5`**. Passing each identity into the **same**
normative `same_edge_fraction`, with destination at the segment end, gives:

| operand/result | float-derived identity | exact identity |
|---|---:|---:|
| remaining fraction | `0.4` | `0.39999999999999997` |
| direct-journey seconds, full weight 1000, same connector | `400.35493142499996` | `400.3549314249999` |
| direct-journey seconds, admissible full weight `1e19` | `4e18` | `3.9999999999999995e18` |

The latter reported-number difference is **512 seconds**. Eligibility, count, coarse structure and
places counters are all **0**; the exact-occurrence counter is **1**. This isolates a route from an
identity difference to a number difference, even when the rounded XY and parameter image agree.
It does not claim that this large weight is present in the Triangle census, or that a Triangle
verdict has been demonstrated to flip. That routed impact remains unmeasured.

§12 makes this more than cosmetic provenance: a manifest that persists occurrences retains the
parameter used to apportion costs/times. Reconstructing a traversal from that identity consumes a
different numeric operand. To promise equal answers one must compare the relevant traversals and
selections, not just locations within a tolerance.

The paragraph also conflates **raw per-segment movement** with **retained-candidate movement**.
Replaying the two committed real windows yields C candidate displacements **`3.562794224442979e-5`
and `6.998565223626435e-6` metres**, each twice because there are two records. The asserted “largest
displacement anywhere is half a nanometre” is false for those retained candidates; `4.6566e-10`
is the maximum for a segment compared with *itself*. The write-up later describes the 36 µm swap
correctly, but that does not make the earlier blanket conclusion true.

**What survives F4:** `exact_occurrence`'s conditional covers the entire tuple concatenation.
Vertex keys return `key[:3]`; interior keys append a `Fraction`. The reproducer tests both branches,
equal float/Fraction representations of `1/2`, and unequal `float(1/3)`/`Fraction(1,3)` values.
The latter are different rational positions, not merely two spellings of the same rational.
Converting the float to a `Fraction` is therefore the correct comparison under §2.2's unrounded key;
it does not overcount representation-only differences.

**67.8% survives with its actual denominator.** Summing the artifact by convention gives:

| comparison | point observations with changed retained identity | denominator | rate |
|---|---:|---:|---:|
| A | 573,107 | 844,685 | 67.848606% |
| C | 573,097 | 844,685 | 67.847422% |
| D | 573,066 | 844,685 | 67.843752% |

These count **points whose set changes**, not changed candidates divided by all candidates. The
prose's “two thirds of those candidates” is not the statistic measured. The combined denominator is
observations across five sets, including samples and censuses, not an asserted disjoint population
of unique coordinates. The engineering note §6's “about three quarters” is also not the measured
rate; it is 7.1514 percentage points above it.

Eligibility and counts measure the right quantities. Coarse structure measures the explicitly named
vertex/segment structure, not identity. Places measures a spatial set **within 1 µm**, not exact
positions or route options. Those four counters are not intrinsically wrong after the fix; the
interpretation of their zeros is too strong. C's two structure/place changes are real exceptions.

## R5 — Medium — F5's repaired sentinel still accepts a dead interior adoption

**Claims refuted**, `adoption_sentinel` docstring:

> Prove the exact path is not quietly the float path, before any zero below is believed.

> a positive control for each counter

**Reproducer:** [f05_sentinel.py](f05_sentinel.py).

An in-memory wrapper returns the exact `measure_point` result only if some raw position changes
its **coarse** vertex/segment key; otherwise it returns the float result. This is a general erroneous
fallback rule, with no witness coordinates, call-stack checks or sentinel-specific branches.

Results:

```text
sentinel passes: 3 of 3; firing pattern: [True, True, False]
ordinary interior: live exact_parameter_differs = 1; dead = 0
dead adoption: positions compared = 1; every difference counter = 0
both committed real census windows also report every difference as zero
```

Both positive witnesses test a vertex/interior transition. Neither requires adoption when the
coarse key stays the same. The recorded full census has **zero raw vertex/interior transitions**,
so this fallback erases the entire recorded adoption signal, including C's swaps, while the sentinel
passes. I replayed the interior example and both real windows; I did not re-run the 47-minute census
under this patch.

The control has a second hole. It computes `fired = parameter_changed AND vertex_changed` and
rejects only `fired`. Setting the parameter counter permanently to **1** still passes the control,
whose vertex counter is **0**. Thus the claim that the ordinary attachment “must increment neither”
is not enforced: `NOT(P AND V)` is weaker than `NOT P AND NOT V`.

The control **does constrain something**: setting *both* counters permanently to 1 is rejected.
The repaired sentinel also rejects pass 38's unconditional float dispatch, which the reproducer
checks. Those are confirmed improvements. Add an interior-only positive witness and test each
control counter independently; give other claimed-live counters their own discriminating witnesses.

## R6 — Low — F4 leaves the old parameter counter published as a permanent zero

**Artifact claim refuted**, every `adoption.sets.*.raw`:

```json
"parameter_differs": 0
```

**Reproducers:** [f04_identity_and_answers.py](f04_identity_and_answers.py) and
[verify_numbers.py](verify_numbers.py).

`adoption_stats` still initialises `parameter_differs` at line 655, but no longer increments it.
The new named fields are correct; this old field is neither removed nor marked deprecated.

| same measurement | legacy field | exact field | rounded-image field |
|---|---:|---:|---:|
| synthetic interior example | 0 | 1 | 0 |
| committed artifact totals | **0** | **2,142,228** | **1,333,808** |

A consumer of the previous artifact schema now sees all parameter differences disappear. The
renderer uses the new fields, so the generated table is correct. Remove the dead field, explicitly
version/deprecate it, or maintain its previous meaning; a plausible named zero is misleading.

## R7 — Low — F8's supersession repair does not reconcile the rest of the plan

**Claim still present**, step 4 plan lines 119–121:

> every comparison that *decides* something made on the exact value where one exists

**Reproducer:** [f01_and_f08_contract.py](f01_and_f08_contract.py).

The plan repeats the unrestricted guarantee that F1 narrowed in the design. Exact cap predicates
exist, and the script again shows exact rejection versus rounded admission at **both 200 and 300 m**.
Mirror the design's scope and exclusions in this callout; it is still presented as what “closing
item 1” means. Its “squared distance, residual ordering” row likewise needs to distinguish exact
squared comparisons from operational rounded-residual comparisons, rather than suggesting one
unqualified residual ordering throughout the comparator.

Other unreconciled statements are visible without numerical interpretation:

* The gate table still calls item 1 **“OPEN. This is phase 4a”**, whereas revision 13 closes item 1
  and opens items 5/6, as the plan's own task 4 says.
* Task 4 still says **“Two rows”** were superseded; the repaired callout correctly says **three**.
* The plan's old 21-mutant count and original 38 fixtures are historical, not the present 24/43;
  label their snapshot scope when using them as current progress evidence.

**F8's targeted repair itself survives:** the zero-total row is explicitly superseded, and the
callout now states fraction 0.0 and preservation of structural occurrence keys. The traversal and
same-edge rows are also explicitly superseded. The root algorithm, per-operand `fsum` convention
and exact projection/clamp rows otherwise agree with revision 13. I found no additional executable
primitive contradiction in them. These are documentation inconsistencies, not a new zero-total bug.

## Repairs confirmed and remaining limits

### F2: the replacement reason is sound

[f01_and_f08_contract.py](f01_and_f08_contract.py) gives both W3 rounded prefixes as
**20,000,000**, their exact rational difference as **0**, and the adopted span as
**558.7935447692871 s** at `6e18`. The underlying gap is exactly **`1/2**29` m**. This is a sufficient
measured reason to reject rounded-prefix subtraction under the stated objective; it does not prove
that the span is the only possible convention, and the replacement text no longer claims that.
Finite sums of rational radicals can be represented as exact algebraic expressions. Cancelling a
common symbolic prefix on W3 is valid; no stronger impossibility claim is needed.

### F6: fingerprint repair confirmed for its record-data scope

[verify_f06_f07.py](verify_f06_f07.py) checks **1,009 finite 2D coordinate-bit round trips**, including
signed zeros, subnormals, adjacent floats and random coordinates. It compares the WKB's actual
coordinate payload with packed binary64 bits, not geometric equality. Changing signed coordinate
zero, a coordinate by one ulp, or a time by one ulp changes the fingerprint: **3/3** checks.
No finite 2D coordinate-bit collision was found. Nonfinite coordinates are outside the contract.

I also ran `v2/scripts/explain_adoption_diff.py` on the local graph. It prepared **808,433** records,
matched the artifact fingerprint
`ed3aae3f04c34dbabae67da5ad79071945556d832a27ef05b8dc82360488f3c8`, and reproduced both census
witnesses. Thus the duplicated preparation did not drift on this run.

Matching this digest makes differences in the duplicated preparation harmless **when their result
is the same ordered geometries and directional times**. It does not bind query points, CRS metadata,
the search tree implementation, band/cap/tolerance constants, arithmetic code/runtime or routing
weights/connectivity that are not in those records. The check demonstrates an unchanged-record
policy edit moving A's count **2 → 1**. That is a scope limit, not a WKB collision or evidence that
the current copied graph preparation is wrong. The legacy no-fingerprint fallback prints a warning
and lacks the full guarantee; it was not used by the present artifact.

### F7: comparator repair confirmed; the suggested bool branch is not a false-equality bug

[verify_f06_f07.py](verify_f06_f07.py) runs the **13/13** self-tests, **1,024** pairs of small JSON
values against an independent typed structural identity, and **6** volatile-path boundary/subtree
checks. No distinct nonvolatile supported JSON values compared equal.

The bool condition skips the early `TYPE` report, but execution continues into `_leaf`, which carries
the type name as well as `repr`. `False`/`0` and `True`/`1` still differ. It is awkward, not broken.
Tuple paths preserve dotted literal keys. Wildcards match exactly one path element; the prefix rule
then intentionally ignores the named volatile subtree. A key such as `seconds_extra`, a literal
`sets.s.seconds`, or a deeper `sets.s.x.seconds` is not accidentally stripped. Changes under an
explicitly volatile subtree are intentionally ignored, including its shape; the documented NaN
equivalence is also intentional, not a counterexample to the promised comparison.

`verify_numbers.py` loads both historical refactor artifacts from git (`df38f99^` and `df38f99`):
**610 nonvolatile scalar leaves each, zero structural differences under the repaired comparator**.

### Fixture and numerical-claim audit

I found no false expected numerical literal among the questioned fixtures. Search-derived literals
are not automatically circular: independent squared-midpoint certificates verify the partial-length,
subnormal and hypot witnesses (**3/3**); the existing independent root oracle and the additional
2,004-cell check supply broader evidence. `_lattice` deliberately mirrors implementation machinery
for the narrow index experiment; cache equivalence also compares related implementation paths.
Neither should be mistaken for an independent oracle for the whole module. R3 is a concrete gap
in which paths the fixtures exercise, despite their correct local expected values.

The artifact/code arithmetic checked by `verify_numbers.py` is:

| measured quantity | checked total/maximum |
|---|---:|
| point observations | 844,685 |
| raw per-segment positions | 36,555,718 |
| differing residuals | 2,142,080 |
| differing arclengths | 16,459,230 |
| differing exact parameters | 2,142,228 |
| differing rounded parameter images | 1,333,808 |
| ratio of the two parameter counts | 1.6060992286745919 |
| differing rounded positions | 42 |
| raw vertex/interior flips | 0 |
| maximum raw residual difference, metres | `2.396749465560788e-10` |
| maximum raw arclength difference, metres | `7.275957614183426e-12` |
| maximum same-segment rounded XY displacement, metres | `4.656612873077393e-10` |
| adoption runtime stored in artifact | 2,803.02 s = 46.717 min |

Eligibility/count changes total zero for all three comparisons. Coarse structure and places change
at **2** structure-centroid observations for C and zero for A/D. The exact-identity totals are in R4.
`render_t0_results.py --check` passes: the generated block matches the JSON. The manually written
interpretation has the issues in R4/R6, and the note's approximately three-quarters description
should use the actual rate. Sections 5's old “no candidate set” claim is historical and corrected by
section 6; it must not be used as a present identity-level result.

The artifact supports approximately **47 minutes** for the corrected adoption run. It does not
retain the original 135 ms pre-cache benchmark, so I cannot independently certify that timing or
the 32× speedup from this artifact. The whole census was not regenerated during this review;
aggregate checks are audits of the committed artifact and aggregation code, supplemented by synthetic
inputs, both saved real windows, the matching full record fingerprint, and the live graph replay.
Routed consequences on the actual census remain open; “same answers” has not been measured.
