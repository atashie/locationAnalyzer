# Pass 37 — the step-4 plan does not close its arithmetic gate

Reviewed `v2-rethink`, HEAD `255970e`, on 2026-11-11. Target:
`docs/plans/2026-11-11-step4-comparator-plan.md`. **Four High, three Medium, one Low finding.**
No implementation is proposed here. Only this directory was written. Reproducers use the
repository's Windows CPython 3.13.1 environment and require no network. `README.txt` gives commands.
PASS means the script reproduced and asserted the stated finding, not that the plan passed.

**The central claim does not survive.** Exact rational projection plus correctly rounded lengths
and fractions does not preserve the real cost argmin inside the declared domain. Moreover, the
plan's composition does not always correctly round the real prefix or fraction. A deterministic
rounded operational convention is possible, but accepting that convention is the qualification
the plan must make; it has not proved that its numerical choices remove argmin sensitivity.
Under its own third invalidation condition, 4a is not ready to be declared closed.

There is also a distinct architectural problem: scalar shortest-path labels do not implement
the existing whole-journey rounded-cost ranking. This persists after geometry is settled.

## F1 — High — correctly rounded components do not deliver the claimed fraction or real argmin

**Claim.** The rule table and closing paragraph of 4a say the algebraic quantities are exactly
rounded, and treat that as sufficient to close item 1, subject to the final invalidation condition.

**Actual.** There are two separate failures: rounding the components does not correctly round their
composition, and even correctly rounding the final real fraction once can create a false cost tie.

**Evidence: `f01_rounded_argmin.py`.** Two one-way records share origin `(0,0)` and destination
coordinate `(1,0)`:

| record | geometry | full time | full cost |
|---|---|---:|---:|
| A, node 0 to node 2 | `(0,0),(1,0),(2,1)` | 2400 | 1 |
| B, node 0 to node 1 | `(0,0),(1,0)` | 1 | `0.4142135623730951` |

All attachments used have zero residual; exact projection and clamp decisions are unambiguous.
A's destination is its first interior vertex. Its exact traversal fraction is
`f = 1/(1+sqrt(2)) = sqrt(2)-1`, approximately
`0.41421356237309504880168872420969807857`.

The plan computes:

```text
RN(sqrt(2))                     1.4142135623730951
fsum((1, RN(sqrt(2))))          2.414213562373095
1 / that total                 0.4142135623730951
RN(real f)                     0.41421356237309503
```

The real cost of A is strictly below B's cost by about `4.11618e-17`, less than one fraction ulp.
Real selection therefore reports A's **994.112549695428 s, FAIL at 600 s**. The plan makes the
costs tie and selects B by time: **1 s, PASS**. Rounded multiplication by cost 1 and final `fsum`
cannot undo this. The script certifies the inequalities by rational squared comparisons;
100-digit Decimal is used only to display the irrational value.

Even replacing the composition by an oracle for `RN(real f)` does not fix the general claim.
Set B's cost to `0.41421356237309503`, A's full time to 1, and B's time to 1000.
B is now strictly cheaper over the reals, but rounding A's fraction creates a tie and selects
A's subsecond time instead of **1000 s**. Thus this is not just an avoidable double-rounding bug.

The prefix claim also fails independently: correctly rounded lengths `1` and `sqrt(10)` sum by
`fsum` to **4.16227766016838**, while the correctly rounded true sum is
**4.162277660168379**. Geometry `(0,0),(1,0),(2,3)` realizes those lengths.

Both graph variants pass `ToyEdge`/`ToyGraph` validation: coordinates are far below `1e7`,
nonzero segments exceed `1e-6`, weights are nonnegative and formed and aggregate costs/times
are finite. There is no domain rule imposing a minimum separation between candidate costs.

**Required correction.** Say explicitly whether comparison is of real geometric costs or of
the newly declared rounded operation sequence. For the latter, state that real argmins can
change and withdraw the correctly-rounded-composition claim; record the semantic amendment and
requalification. For the former, retain certified algebraic comparison/fallback through selection,
or justify a restricted domain that actually excludes these cases. Irrational quantities cannot
generally be stored exactly in binary64, but exact algebraic representations and certified
comparisons are not mathematically impossible. Correct rounding of each operand is not a proof
about their ratio or an argmin. This finding does **not** say an operational convention is
incoherent, or that universal real-arithmetic equivalence was already promised by revision 12.

## F2 — High — W1's required answer contradicts 4a's selected rule

**Claim.** W1 must change from 1000 s to a tie reporting 1 s; 4a's primitives are fixture-first
against W1, W2 and W3. The selected sum is `fsum`, explicitly rejecting left accumulation.

**Actual.** Those requirements cannot all hold. On the actual pass-22 geometry,
`fsum` gives **1000 s**, exactly like current Python `sum`.

**Evidence: `f02_witnesses.py`.** W1's A geometry is
`(0,0),(.1,0),(.1,.2),(.1,.5)`, time 6, cost 1; B is
`(0,0),(.1,0)`, time 1000, cost `1/6`. Origin is `(0,0)`, destination `(.1,0)`.
Segment lengths are `[0.1,0.2,0.3]`.

| total rule | length | first-vertex fraction | selected time |
|---|---:|---:|---:|
| Python 3.13 `sum` | 0.6 | 0.16666666666666669 | 1000 s |
| adopted `fsum` | 0.6 | 0.16666666666666669 | 1000 s |
| explicit left accumulation | 0.6000000000000001 | 0.16666666666666666 | 1 s |

The reproducer evaluates all three by changing only the length property in memory and restoring
it afterward. No source is patched. Pass 22 presented two permitted readings, not a proof that
the faster reading was the required geometric answer.

**Required correction.** If adopting `fsum`, W1's expected result is **1000 s**, and the rejected
variant is 1 s. Retain W1 as evidence that an arithmetic convention is needed, not that `fsum`
repairs it to the historical left-accumulation result. A mutation fixture must distinguish the
chosen rule rather than enforce its opposite.

## F3 — High — scalar shortest-path selection does not implement whole-journey rounded ties

**Claim.** 4b.2 identifies the production two-CSR architecture as what makes this comparator
affordable, while 4b's scope retains §2.4's whole-journey `fsum` and tie rules.

**Actual.** A scalar best-cost prefix at a node is insufficient for those rules, even with
perfect geometry and a local cost/time tie key. A more expensive prefix can join a final
rounded-cost tie and win by time. Once discarded, reconstruction or post-hoc `fsum` cannot recover it.

**Evidence: `f03_scalar_search.py`.** Two distinct directed paths merge at node 3, then share a suffix:

| path component | individual cost terms | time |
|---|---|---:|
| P, `0→1→3` | `0.5, 0.5` | 1000 s |
| Q, `0→2→3` | `0.5, 0.5000000000000002` | 1 s |
| common `3→4` | `2**54` | 1 s |

At the merge, P is strictly cheaper. After adding the suffix, **both complete `fsum` costs are
`2**54`**. The normative time key selects Q, **2 s, PASS**. The existing CSR/SciPy scalar search
keeps P and reports **1001 s, FAIL**. The current exhaustive oracle independently returns 2 s
on the same admissible graph and endpoint query. These are distinct paths, so parallel-edge
grouping is not the cause. Ordinary edge-by-edge binary64 addition also differs from `fsum` on
`(2**53,1,1)`; fixing that accumulation alone does not fix the discarded-prefix example.

**Required correction.** Add a search-semantics feasibility task and benchmark before promising
a three-day scalable implementation of the existing rules. Specify how the search preserves
all candidates needed by the final rounded ranking, including ties after connectors/partial terms.
An exact additive search followed by rounding just its winner also discards Q in this example.
Alternatively amend the selection semantics explicitly. A pair of CSR arrays is a storage choice,
not evidence that the desired ranking admits the proposed pruning.

## F4 — High — the production cost/time pair erases objective-1 alternatives and other required data

**Claim.** 4b.2 says “two CSR matrices over one sparsity, cost for selection and time for reporting”
is the architecture; 4b.3 requires both objectives, and the scope includes all of §2.

**Actual.** The quoted pair is one **cost-selected** view. It cannot supply objective 1 after
cost-minimal parallel collapse, and it does not carry the attachment records or directed identities
needed for partial traversals and ranking. This is exactly the distinction in design §2.3 and
the execution plan's T3 subsection.

**Evidence: `f04_csr_views.py`, plus `traveltime/csr.py`.** Coincident parallel alternatives
`(time,cost)=(1,100)` and `(10,10)` produce matrices carrying only `(10,10)`. Objective 1's
1-second edge is gone. Equal-cost alternatives `(10,50)` and `(1,50)` return time 10 or 1 by
insertion order, contradicting the required time discriminator. An admissible zero-time/zero-cost
reference edge is rejected by `_validate`, which requires strictly positive weights.

The CSR routine also returns no CSR-entry-to-directed-record mapping. An endpoint-pair entry is
not a retained attachment occurrence. Distinct records and occurrences must survive spatial
enumeration before objective-specific selection (pass-36 F4); otherwise an interior partial route
can disappear before it competes. A same-edge direct candidate needs its own direction-legal
interval and must compete with endpoint/network journeys. Neither task follows from matrix pairing.

**Required correction.** Explicitly retain the design's **two compatible objective views**, a
shared geometry tree with all required weight alternatives, directed edge mappings and deterministic
ranking, zero-weight support, query entry/exit partial terms and the competing direct case. Apply
the same fraction to the already-formed full cost, including penalty; charge both connectors to
time and cost. Preserve direction through reversed search bookkeeping if reverse multi-source
routing is used. Production code is a starting point whose known differences require work, not
an implementation of this contract. These additions still require F3's search-semantics answer.

## F5 — Medium — the six-quantity table leaves consequential formulas unwritten

**Claim.** The table settles all six unfrozen quantities and closes the whole gate.

**Actual.** “Specified” for the last two is a work item, not a formula. The tasks do not explicitly
deliver either formula. Interior prefix construction, complementary fractions and rounding points
also need normative definitions; “one division” does not define its numerator.

**Evidence: `f05_interval_formulas.py`.** On the straight edge `(-1e7,0)→(1e7,0)`, origin
`nextafter(1e7,0)`, destination `(1e7,0)`, two readings give:

```text
abs(RN(s_destination/L) - RN(s_origin/L))   1.1102230246251565e-16
RN(abs(s_destination-s_origin)/L)          9.313225746154785e-17
```

At full weight `1e19`, these mean **1110.2230246251565** versus **931.3225746154785** seconds.
At admissible weight `6e18`, they cross the published 600-second limit:
**666.1338147750939 FAIL** versus **558.7935447692871 PASS**. Exact rational projection
does not decide which reading the amendment adopts. The zero-total-length row likewise supplies
no value for `0/0` or rule for distinct structural vertices on an all-zero-length record.

**Required correction.** Deliver actual equations and rounding stages for all six quantities,
with direction/clamp/zero cases, before declaring the amendment complete:

| original quantity | what is actually supplied |
|---|---|
| segment-length summation | `fsum` of rounded lengths; deterministic here, not generally RN of the real sum (F1) |
| prefix arclength | sum policy, but interior `prefix + t*length` construction/rounding unspecified |
| projection parameter | exact rational formula and exact clamp; sound |
| traversal fraction | division of rounded operands; numerator/complement/interval choices incomplete, and F1 applies |
| same-edge interval | promise to state a formula |
| zero-total length | promise to state a convention |

The plan may intentionally defer drafting these to 4a, but then they must be explicit 4a
deliverables and acceptance checks. As written, the primitive file can be complete while item 1
still lacks its last two rules.

## F6 — Medium — routing every original-graph origin still omits representation impact

**Claim.** 4c answers T0's remaining verdict-impact question by routing all sampled origins under
each convention, recomputing destination candidates.

**Actual.** That is sufficient to remove pass-36 F3's origin-only undercount for comparisons
**on one fixed graph**. It does not measure routed sensitivity to the lawful transformations
that T0 separately tested and that remain a reason for choosing between the conventions.

**Evidence: `f06_transformation_impact.py`.** On the ordinary straight one-way 100 m record of
time/cost 1199.95, origin `(49.995,0)`, destination `(100,0)`, all original-graph conventions
agree at **600.0349975 s, FAIL**, encoded minute 11. Insert the exact midpoint without changing
the record or its weights: A returns **599.978968253968 s, PASS**, encoded minute 10, whereas
the per-record/global exact minima remain at the original attachment. Every original-graph pair
could agree while this exposure is present. This witness needs no contested projection arithmetic.

**Required correction.** Either limit 4c's conclusion expressly to cross-convention disagreement
on the supplied graph, leaving routed representation sensitivity unknown, or add a separate
targeted routed transformation experiment. Transform destination attachments too. Record splits
add a further prerequisite: define the transformed topology and how full time/base/penalty are
apportioned so that the experiment changes representation rather than policy. Reapplying a fixed
120-second penalty to each split piece would confound the experiment. Keep these targeted results
out of population rates, as the T0 execution plan already requires.

## F7 — Medium — T0's exact distance diagnostic is promoted to an exact attachment pipeline

**Claim.** T0 already supplies the arithmetic 4a needs over 843,135 points; replacing its ad-hoc
primitive should leave the published figures unchanged because projection was already exact.

**Actual.** `exact_segment_sq` correctly computes a rational clamped parameter internally but
returns **only the squared distance**. `raw_positions` still calls float `_segment_nearest` for
`t`, position, residual, structural endpoint/interior classification and prefix arclength. Exact
distances select among these float-derived descriptions; they do not replace them. D's retained
distance ranking is more exact than its returned position and occurrence representation.

**Evidence: `f07_t0_exact_scope.py`.** On W2, T0 returns raw parameter **0**, occurrence
`(0,'v',0)`, while the parameter used internally by the rational squared-distance calculation
is **7.105427357601002e-9**, strictly interior. The helper returns the correct smaller squared
distance for that interior point alongside a raw description of the endpoint.

The 843,135 figure is genuinely the two census point counts, **512,633 + 330,502**. It is not
evidence that 843,135 full attachments used rational parameters, or that the new prefix/fraction
rules have already been exercised there. This review does not claim a new prevalence on those
censuses or that their published aggregate counts necessarily change.

**Required correction.** Call the existing code a reusable exact squared-distance diagnostic.
Separate a behavior-preserving refactor of that helper from adoption of exact attachment
parameters, occurrences, positions and new arclength rules. Rerun the affected measurements and
compare memberships/statuses as well as totals; unchanged figures are a hypothesis to check.
Version A/C/D's arithmetic precisely: T0's C deliberately uses computed float residual equality.
Replacing that filter with a rational predicate creates a different variant and cannot silently
inherit the old pilot's evidence. Exact D position-invariance also does not certify all routed
observables or all rounded midpoint transformations.

## F8 — Low — W2 excludes a naive summation replacement, not every `fsum` formulation

**Claim.** “`fsum` cannot reach W2” is the method-setting reason for exact rationals.

**Actual.** The narrower statement in the witness paragraph is true: summing the already-rounded
products gives zero. The broader invalidation wording overstates what that establishes.

**Evidence: `f08_w2_factoring.py`.** Since `dx == dy == 1e-6` here:

```text
fsum((px*dx, py*dy))       0.0
fsum((px, py)) * dx        1.4210854715202003e-20
```

The second expression equals the exact rational dot product on these inputs, and reaches the
stated parameter and **710.5427357601002 s** network time. The cancellation of these two nearby
opposite operands is exact; multiplying their power-of-two difference by `dx` is exact here too.

**Required correction.** Say “replacing the addition of already-rounded products by `fsum`
does not fix general projection arithmetic.” W2 does not uniquely select an implementation
method. Exact rationals or certified robust predicates remain justified for the general problem;
special factoring of this witness does not close W3 or F1, and does not invalidate that rationale.

## Checks found sound, and limits on the findings

### Arithmetic side claims

`arithmetic_checks.py` checks these independently with integer/Fraction arithmetic:

* **Correctly rounded rational square root is achievable.** Choose the output binade's lattice
  unit `u`, compute `k = isqrt(floor(q/u**2))`, then compare the **original rational** `q` with
  `((k+1/2)*u)**2`, resolving equality by even significand. This handles both midpoint parities,
  arbitrary closeness to a midpoint, and subnormal halfway cases. Integer scaling alone is not a
  rounding proof: discarded numerator/denominator information must survive in the midpoint
  comparison, or an interval must be refined until decided. The plan gives no scale or rounding
  algorithm, so no particular insufficient fixed scaling can fairly be attributed to it. A fixed
  guard-bit approximation without a remainder/certification argument is not enough.
* **The stronger norm guarantee is real on this platform.** An admissible segment displacement
  `(4194304.125000001, 0.06250000093132257)` gives CPython `hypot`
  **4194304.125000002**, whereas the correctly rounded answer is **4194304.125000001**.
  Set `y=2**26+1`, `x=y*y`, then scale both by `2**-30`. Before scaling,
  `x*x+y*y = x*x+x < (x+1/2)**2`; the exact norm is strictly below the rounding midpoint.
  The integer oracle certifies the lower result. CPython 3.13 implements its own compensated
  `vector_norm`; generic IEEE-754 requirements are not its operative accuracy contract. Its
  documented guarantee is below one ulp and usually correct rounding, rather than universal
  correct rounding. See the [versioned CPython implementation](https://github.com/python/cpython/blob/v3.13.1/Modules/mathmodule.c#L2259)
  and [Python math documentation](https://docs.python.org/3.13/library/math.html#math.hypot).
  A better primitive guarantee does not imply a better final selection on every query (F1).
* **The factor of three is correct for the stated operands.** Their exact total is
  `21617278211378381/36028797018963968`. The errors of `0.6` and `0.6000000000000001`
  are respectively `1/2**55` and `3/2**55`. This validates that side claim, not W1's required result.
* **`fsum` order independence is appropriate within this pinned, nonnegative, finite-aggregate
  routing domain.** All six permutations of the cited example return `0.6`. Unqualified
  order independence is too broad: `(1e308,1e308,-1e308)` overflows while the alternate order
  succeeds; that counterexample is outside the declared routing domain. The docs also qualify
  portable rounding behavior. No new in-domain order-dependence finding is asserted.

### W2 and W3 numbers

`f02_witnesses.py` reproduces W2's exact dot, parameter and network time. Current total is
**137.032804627088 s**, exact-projection total **847.575540387188 s**: the printed
137.03/847.58 and PASS/FAIL statements are correct. W3's endpoint gap is
**1.862645149230957e-9 m**, current total **1.47828980097695e-9 s**, and real network
time **931.3225746154785 s**. Its figures also reproduce. The unresolved issue is carrying
that corrected geometry into a chosen interval rule (F5), not either witness's published numbers.

### What the four 4b requirements get right, and what they omit

Making the convention a manifest-recorded parameter, implementing scalable routing, returning
both objectives and their signed gap, and preserving absence as a status are all sound requirements.
The positive direction of the full-set gap is meaningful because objective 1 is a time minimum
over the same eligible population. These statements do not supply the view/record/search rules
in F3/F4, or the arithmetic version boundaries in F7.

T0/pass 36 also imply: preserve weight-distinct records before selection; preserve **occurrences**
rather than merely XY positions (pass-36 F7's self-crossing limitation); recompute every grocery
candidate and eligibility set by convention; retain per-point memberships/provenance rather than
only aggregate counts (F3); pin and verify graph, places, frame and rule identities; and separate
targeted transformations, centre censuses and area-sample estimates (F5–F8). The independent
fixtures must cover decision and consumed provenance fields. Existing `conformance.check` does
not compare every `OracleResult` identity/cost field or carry traversal intervals; green T4 is
evidence for its actual assertions. This is a missing acceptance checklist, not evidence that a
not-yet-written T3 has already violated it.

### 4c's denominator and evidential cost

The change from routing only differing origins to routing all sampled origins is sound and
necessary. **It changes work, not the statistical denominator.** The pre-registration's budget is
`0.01/6` of **each frame's verdicts at each threshold**. Keep 500 B observations and 500 C
observations separate, with each convention pair and objective identified. Do not divide by just
differing attachments, by changed destinations, by the displayed-PASS subset, or by a pooled
collection of pairs/objectives. The displayed-PASS rate is an additional conditional measure.
The two frames and the original per-frame/per-threshold denominator remain definite; no
denominator-change finding is warranted simply because routing workload increased.

The plan correctly retains unresolved comparisons, separates false-inclusion direction, compares
both exact and encoded verdicts, and requires benchmarking before scale selection. Zero events
in 500 cannot certify the allocated budget, as the pre-registration already admits. There is no
reason to rederive or loosen that allocation after observing stage 3. Use the registered `1%/6`
rather than treating its three-decimal display `0.167%` as a new exact threshold.

If 4c expires, existing attachment results remain evidence and verdict impact remains unknown;
that limited “costs nothing already held” claim is sound. The invested development time is of
course sunk. A **discovered** contradiction must update the affected attachment claims; stopping
without a result cannot be used to retain a claim that a result has falsified.

### Sequencing, gates, and the independent engine

* The required-reading engineering note is a status note, not the numbered normative design.
  I also read the actual design, `docs/plans/2026-11-04-s3-measurement-design.md`, especially
  §§2, 12 and 13. Item 1 explicitly lists all six geometry quantities, not only projection.
* **Items 2, 3 and 4 are settled at their stated scope.** The uniqueness promise is deliberately
  only total time/cost, destination and route identity; T10 still owes a traversal specification.
  The numeric domain prevents the cited underflow/overflow examples but does not prevent F1.
  The final cost discriminator is normative in §2.4 and the revision-11 row. The step-4 gate
  table's “implemented, not amended” wording for item 4 is stale, copied from the historical
  problem, not another currently open gate.
* T10's missing reconstruction policy blocks its boundary-touch output, not 4b's total-time/cost
  computation or 4c's ordinary verdict comparisons. If either phase consumes decompositions or
  traversal geometry, it must persist the actual chosen reconstruction rather than infer it from
  tied route identities. The owner coverage decision blocks coverage certification only.
* **T2 and T4 exist.** Both development frame artifacts loaded and verified at their recorded
  digests (`51a59463...`, `7914e80a...`), 500 points each, populations 512,633 and 330,502.
  The 17 current conformance cases and the programmatic invariant checker passed. The measured
  current corpus digest is `47f4beb6...`; the engineering note's `e645be28` is stale. No universal
  adequacy follows, and a semantic arithmetic amendment needs reviewed fixtures/oracle updates,
  not an assumption that the old green suite validates it. Consumer-boundary frame verification
  remains an explicit implementation obligation.
* Subject to those qualifications, **closing item 1 plus T2/T4 permits ordinary development**;
  it does not certify a completed T3. F3/F4 expose additional feasibility/implementation work
  hidden in that development step. 4c needs a working, qualified comparator, pinned input and
  destination sets, a preserved frame draw, encoder configuration and comparison records, not
  just the presence of a comparator module. Routed transformations have F6's extra dependency.
* §2.6 is genuinely separate for **4b/4c's full-own-set objectives and E1**. E1 compares the
  product with own objective 1 on the fixed own eligible destinations; an engine correlation
  failure may not remove a destination there. Only E2 needs the engine's eligible intersection
  and the second own objective-2 operand. No independent engine is needed to perform the work
  4b/4c presently promise.
* There is **shared-model blindness**, not an unavoidable computational dependency cycle:
  product and own comparator share graph, speed and destination assumptions. E1 establishes
  construction agreement, not truthful access, a usable grocery or physical travel accuracy.
  Independent T4 derivations help find implementation defects; they cannot replace E2/E3 or
  the grocery/geocoding audit. The narrow development framing is sound if that distinction stays.
* T0's registered outcome really is **open on impact**. Treating the candidate convention as a
  development parameter permits progress without claiming that T0 settled the winner. Calling
  item 0 no longer a development blocker is an operational choice consistent with revision 10,
  not an empirical demonstration of adequacy. D's exact-position invariance under genuinely
  geometry-preserving transformations is useful; it neither requires all of 4a to state the
  mathematical property nor establishes complete routed invariance. Rounded midpoint insertion
  can change exact geometry, as pass 36 correctly says.

## Validation boundary

All nine supplied Python files ran successfully with repository CPython 3.13.1, using `-B`.
Expected differences are asserted; each script prints PASS or CLAIM/ACTUAL lines and raises on
failed assertions. Algebraic comparisons in the central witness and norm checks use exact rational
inequalities rather than trusting displayed decimal approximations. Existing functions are only
read or changed temporarily in process memory. No full Triangle rerouting or T0 census rerun was
performed, and no new real-data rate is claimed. No pytest full-suite count is claimed.

The plan can proceed after choosing and documenting the actual arithmetic contract, reconciling
W1, completing the six formulas, and resolving how scalable search will honor the selected
whole-journey ranking. Calling the current table the whole closed gate would repeat the precise
failure under review: a guarantee about adjacent intermediate quantities reported as a guarantee
about the decision that consumes them.
