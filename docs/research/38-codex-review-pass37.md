# Codex pass 37 — the step 4 plan's central claim was wrong, and the plan said so itself

**2026-11-11.** Reviewed `docs/plans/2026-11-11-step4-comparator-plan.md` at head `255970e`. Model
`gpt-6.1-sol`, 12m 00s. **Four High, three Medium, one Low. All eight stand.** Reproducers in
`38-codex-review-pass37-counterexamples/`; every finding reproduced here before being acted on, and
seven of the eight were re-derived with my own arithmetic rather than by running Codex's scripts.

This was a review of a **plan**, so nothing was built wrong. The cost is a rewrite, not a rebuild.

## The headline

**4a does not close §12 item 1, and the plan's own first invalidation condition is what it trips.**
That condition reads:

> **4a turns out not to close W2.** [...] if an exact projection still produces a wrong argmin on
> some witness, the item is wider than arithmetic and T3 stays gated.

Pass 37 produced the witness. Exact rational projection plus correctly-rounded lengths and fractions
**does not preserve the real cost argmin**, because the traversal fraction is irrational and can only
ever be rounded. The plan presented "exact where rational, exactly-rounded where algebraic" as
closing the gate. It narrows the gate.

## What it confirmed

Listed first, because this one confirmed more than it broke and the confirmations are load-bearing:

- **A correctly-rounded square root of an exact rational is achievable**, and Codex supplied the
  algorithm the plan had only gestured at: pick the output binade's lattice unit `u`, take
  `k = isqrt(floor(q/u²))`, then compare the **original rational** `q` against `((k+½)u)²`, breaking
  equality to even. Integer scaling alone is *not* a rounding proof — the discarded numerator and
  denominator information has to survive into the midpoint comparison.
- **The "strictly better than `math.hypot`" claim is true on this platform, with a witness.** The
  displacement `(4194304.125000001, 0.06250000093132257)` gives CPython 3.13.1
  `hypot` **4194304.125000002** where the correctly rounded answer is **4194304.125000001**. Built
  from `y = 2²⁶+1`, `x = y²`, both scaled by `2⁻³⁰`, so the exact norm sits just below the rounding
  midpoint. CPython implements its own compensated `vector_norm` and documents "usually correctly
  rounded", not always — so the operative fact is CPython's contract, not IEEE-754's.
- **The factor-of-three figure is exact.** The true total is `21617278211378381/36028797018963968`;
  the errors of `0.6` and `0.6000000000000001` are `1/2⁵⁵` and `3/2⁵⁵`.
- **`fsum` order-independence holds in this domain**, and the qualification matters: all six
  permutations of the cited example return `0.6`, but `(1e308, 1e308, -1e308)` is order-dependent
  through intermediate overflow. That case is outside the declared domain, so the rule stands as
  stated **for this domain** and the unqualified wording does not.
- **W2's and W3's published numbers reproduce.** W2: exact dot `1.4210854715202003e-20`, parameter
  `7.105427357601002e-9`, 137.032804627088 s PASS against 847.575540387188 s FAIL. W3: endpoint gap
  `1.862645149230957e-9` m, 1.47828980097695e-9 s against 931.3225746154785 s.
- **T2 and T4 exist and verify** at their recorded digests, 500 points each, populations 512,633 and
  330,502; the 17 conformance cases and the invariant checker pass.
- **§2.6 is genuinely a separate dependency** for what 4b and 4c promise, and §12 items 2, 3 and 4
  are settled at their stated scope. Closing item 1 plus T2/T4 does permit ordinary development.
- **T0's registered outcome really is "open on impact"**, and treating the convention as a
  development parameter is a legitimate way to proceed without claiming T0 picked a winner.

## F1 (High) — correctly rounded components do not give the real argmin, or even a correctly rounded fraction

Two one-way records share origin `(0,0)` and destination `(1,0)`.

| record | geometry | full time | full cost |
|---|---|---:|---:|
| A | `(0,0),(1,0),(2,1)` | 2400 s | 1 |
| B | `(0,0),(1,0)` | 1 s | `0.4142135623730951` |

A's destination is its first interior vertex, so its exact traversal fraction is
`f = 1/(1+√2) = √2−1 = 0.41421356237309504880…`. Every attachment has zero residual; the clamp
decisions are unambiguous. Certified with `Fraction` — `((1−c)/c)² < 2` — **A is strictly cheaper
than B over the reals**, by about `4.1e-17`.

| | value |
|---|---|
| `RN(√2)` | `1.4142135623730951` |
| `fsum((1, RN(√2)))` | `2.414213562373095` |
| the plan's `f` = 1 / that | `0.4142135623730951` |
| `RN(real f)` | `0.41421356237309503` |

Two failures, not one:

1. **The composition does not correctly round.** The plan's `f` is not `RN(real f)`. Rounding each
   operand correctly says nothing about their ratio.
2. **Even an oracle for `RN(real f)` does not fix it.** The plan's `f` equals B's cost exactly, so
   the costs **tie**, and §2.4's time discriminator selects B: **1 s, PASS at 600 s**. Real selection
   takes A: **994.112550 s, FAIL**. Set B's cost to `RN(real f)` instead and the inversion simply
   changes direction — rounding A's fraction manufactures a tie and selects A's sub-second time where
   the reals require B's 1000 s.

The prefix claim fails independently: on `(0,0),(1,0),(2,3)`, `fsum` of the correctly-rounded lengths
`1` and `√10` gives `4.16227766016838` where `RN(1+√10)` is `4.162277660168379`.

Both graphs pass validation — coordinates far below `1e7`, segments above `1e-6`, weights
nonnegative and finite. **There is no domain rule imposing a minimum separation between candidate
costs**, and that is the gap: revision 11's bounds prevent underflow and overflow, and cannot
prevent two costs from differing by less than one ulp of the fraction that forms them.

**This does not say the design asked for the impossible.** §12 item 1 asks for "an exact
binary-rational fallback for the cancellation-sensitive projection terms" — which is W2 and W3, and
which exact rationals do deliver. It says the **plan's** claim about what that buys was too strong.

## F2 (High) — W1's required answer contradicts the rule the plan adopts

The plan's fixture table says W1 must change from 1,000 s to "the costs tie and the time
discriminator reports **1 s**". Under the adopted `fsum` rule it reports **1,000 s**.

| total rule | length | first-vertex fraction | selected time |
|---|---:|---:|---:|
| CPython `sum` | `0.6` | `0.16666666666666669` | **1,000 s** |
| adopted `fsum` | `0.6` | `0.16666666666666669` | **1,000 s** |
| naive left accumulation | `0.6000000000000001` | `0.16666666666666666` | **1 s** |

1 s is reachable **only** by the left accumulation the plan explicitly rejects as less accurate — and
rejects correctly, by its own factor-of-three argument. So the plan simultaneously argued that `0.6`
is the right total and wrote down the answer that follows from `0.6000000000000001`.

Two things worth keeping. First, **CPython ≥3.12's `sum` uses compensated summation**, so `sum` is
not left accumulation and the design's `sum`-gives-`0.16666666666666669` text is right for the wrong
reason — the naive accumulation it was contrasted with is no longer what `sum` does. Second, the
**normative design is not wrong here**: §12 item 1 describes both readings and adopts the one giving
1,000 s. The defect is mine, in the plan, and it inverted a fixture's expected value.

**W1 is therefore not a repair fixture. It pins the adopted convention against a plausible
alternative, and its expected value is what the code already does.**

## F3 (High) — a scalar cost label cannot implement §2.4's whole-journey tie rule

This is the finding that threatens 4b's three-day box, and it survives 4a entirely.

Two distinct directed paths merge at a node and then share a suffix:

| | per-edge costs | time |
|---|---|---:|
| P | `0.5, 0.5` | 1000 s |
| Q | `0.5, 0.5000000000000002` | 1 s |
| shared suffix | `2⁵⁴` | 1 s |

At the merge P is strictly cheaper, so **any scalar best-cost label discards Q**. After the suffix,
both whole-journey `fsum` costs are exactly `1.8014398509481984e16` — a **tie** — and §2.4's time
discriminator selects **Q, 2 s, PASS**. The scalar search reports **P, 1001 s, FAIL**. `ulp(2⁵⁴)` is
`4.0`, which swallows the prefix gap of `2.2e-16`.

Post-hoc `fsum` over the winner cannot recover a prefix already pruned, and an exact additive search
followed by rounding its winner discards Q too. **A pair of CSR arrays is a storage choice; it is not
evidence that the ranking the design specifies admits the pruning Dijkstra requires.**

## F4 (High) — the production cost/time pair is one cost-selected view, so it cannot answer objective 1

4b.2 named "two CSR matrices over one sparsity, cost for selection and time for reporting" as the
architecture. 4b.3 requires both objectives first-class. Those two sentences contradict each other,
and I wrote them four lines apart.

Verified directly against `csr.graph_to_cost_time_csr`: coincident parallel alternatives
`(time, cost) = (1, 100)` and `(10, 10)` produce matrices carrying **only `(10, 10)`**. Objective 1
needs the 1-second edge and it is gone from both matrices. Two more defects in the same place: equal
-cost parallel alternatives resolve **by insertion order**, not by the normative time discriminator;
and an admissible zero-weight reference edge is **rejected** by `_validate`, which requires strictly
positive weights.

The routine also returns no CSR-entry-to-directed-record mapping, so attachment occurrences cannot
survive into selection — which is pass 36 F4's lesson arriving one layer further down.

## F5 (Medium) — two of the six quantities are a promise, and the gap is consequential

The rule table marks the same-edge interval formula and the zero-total-length convention
**"specified"**. That is a work item, not a formula, and the 4a task list does not deliver either.

It matters. On the straight edge `(-1e7,0)→(1e7,0)` with the origin at `nextafter(1e7, 0)`, two
readings of the same-edge interval — both "exactly rounded" — give:

```
|RN(s_d/L) − RN(s_o/L)|   1.1102230246251565e-16
RN(|s_d − s_o|/L)         9.313225746154785e-17
```

At an admissible edge weight of `6e18` that is **666.13 s FAIL against 558.79 s PASS**, across the
published 600 s limit. Exact projection does not pick one. (My first attempt to reproduce this
collapsed both readings to zero because I took the arclengths by float subtraction — which is W3's
own defect. The readings only diverge once the projection is exact, which is the point.)

## F6 (Medium) — 4c measures cross-convention disagreement, not representation sensitivity

Routing every sampled origin on the production graph removes pass 36 F3's undercount. It does not
measure the thing T0's transformation stage was about. On an ordinary straight one-way 100 m record,
all conventions agree at 600.0349975 s FAIL, encoded minute 11; insert the exact midpoint and A
returns 599.978968 s PASS, encoded minute 10, while the per-record and global exact minima stay put.
**Every original-graph pair can agree while that exposure is present.**

A routed transformation experiment also needs a prior decision the plan does not make: how full time,
base cost and penalty are apportioned across split pieces. Reapplying a fixed 120 s penalty to each
piece would change policy rather than representation and confound the result.

## F7 (Medium) — T0's exact helper is a diagnostic, not an attachment pipeline

The plan says T0's `exact_segment_sq` "is already the arithmetic 4a needs", over 843,135 points, and
predicts the published figures will not move when it is replaced.

`exact_segment_sq` computes a rational clamped parameter internally and **returns only the squared
distance** — verified: its single `return` is `ex*ex + ey*ey`, and `raw_positions` calls it **zero**
times, taking the parameter, position, occurrence label and prefix arclength from the float
`_segment_nearest` path. The exact values are attached afterwards as a diagnostic field. On W2, T0
reports raw parameter `0` and occurrence `(0,'v',0)` while the parameter used inside the rational
calculation is `7.105427357601002e-9`, strictly interior.

So the 843,135 figure is real — it is `512,633 + 330,502`, the two census counts — but it is **not**
evidence that 843,135 attachments used rational parameters. And the prediction that the figures will
not move is a **hypothesis to test**, not a consequence of what the code does. One more trap named:
T0's convention C deliberately filters on computed float residual **equality**. Replacing that with a
rational predicate makes a different variant, which cannot inherit the pilot's evidence silently.

## F8 (Low) — "`fsum` cannot reach W2" is true of the products, not of every formulation

The narrow statement holds: `fsum` of the already-rounded products is `0.0`. The broad one does not.
Because `dx == dy` in W2, `fsum((px, py)) * dx` gives `1.4210854715202003e-20` — the exact dot
product — and reaches the correct parameter. The cancellation of two nearby opposite operands is
exact, and multiplying their power-of-two difference by `dx` is exact here too.

So W2 does not uniquely select exact rationals as the method. It excludes a naive summation
replacement. W3 and F1 still justify the method; the reasoning has to come from them.

## The pattern, and why this pass was cheap

Pass 36's nine findings were all "a mismatch between the thing measured and the thing claimed". Pass
37's are the same shape one level up: **a guarantee about intermediate quantities reported as a
guarantee about the decision that consumes them.** Codex's closing sentence names it better than I
would have:

> Calling the current table the whole closed gate would repeat the precise failure under review: a
> guarantee about adjacent intermediate quantities reported as a guarantee about the decision that
> consumes them.

F1 and F3 are both that. F4 is two of my own sentences contradicting each other four lines apart.
F2 is a fixture whose expected value I inverted against the rule I adopted in the same table.

**The cheap part is that all of it was found against a plan.** Pass 36 cost a correction to published
figures. This pass costs a rewrite of a document nothing has been built from yet. That is the
argument for reviewing plans adversarially and not only results.

## Two stale facts it also caught

- `project-phase1-s3-design.md:244` records the conformance corpus digest as `e645be28`. It is
  `47f4beb6`, and `docs/experiments/s3-instrument-build.md` already records the chain
  `e645be28 → f5ced7a0 → 47f4beb6`. The status note did not follow.
- The step 4 gate table calls §12 item 4 "implemented, not amended". That phrase is the design's
  own, describing the state *before* revision 11 lifted the discriminator into normative prose. The
  item is **settled**.

Related: [[project-phase1-s3-design]], [[feedback-verify-the-shape-of-the-risk]],
[[feedback-decide-by-measurement-not-by-argument]], [[feedback-codex-adversarial-review]].
