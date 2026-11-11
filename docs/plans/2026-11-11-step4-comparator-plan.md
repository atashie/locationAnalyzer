# Step 4 — T3 as a versioned development comparator

> **For Claude:** this is a plan. Nothing here reports a result.

**Status:** plan, for adversarial review before any of 4a is written.
**Written 2026-11-11**, after T0 (plan §0 step 3) and Codex pass 36.

**Goal.** A scalable comparator implementing design §2's decision rules, usable as a *development*
artifact under §12's rewritten terms — pinned runtime, no cross-implementation claim — so that T0
stage 3, S3.1's grid comparison and E1 can run against something other than `toy.py`.

**Why it is three phases and not one.** T3 has been refused four times, and each refusal was over
rules that were revisions of the previous refusal's fix. Pass 20's standing instruction is
unchanged: *"Do not start a purportedly frozen T3 yet. Ordinary development and the unambiguous
fixture subset can proceed."* One gate remains open, and it is not a detail.

---

## The gate: what T0 closed, and what it did not

| §12 blocker | state |
|---|---|
| 0. the candidate universe | **measured by T0.** The pre-registered rule returned **open on impact**, so §2.2's convention A stays provisional. This is no longer a *blocker*; it is a **design requirement on T3** — see 4b.1 |
| 1. the geometry arithmetic | **STILL OPEN. This is phase 4a.** |
| 2. what uniqueness §2.4 promises | settled, revision 11 |
| 3. the admissible numerical domain | settled, revision 11, extended after pass 30 |
| 4. the final cost discriminator | implemented, not amended |

T0 also added a third reason to close item 1, independent of the two already on record: Codex pass 36
showed that convention **D's position-invariance holds only under transformations that preserve
exact geometry**. Without exact geometry there is no way to state D's one advantage, so the choice
among A/B/C/D cannot be made on evidence while item 1 is open.

---

## Phase 4a — close §12 item 1, the geometry arithmetic

**This is the whole gate.** §2.4 froze `f × (cost_base + penalty)` as one term and left the
**fraction** unfrozen. Six quantities decide the exact cost argmin before any `fsum` sees a term:

1. segment-length summation
2. prefix arclength
3. the projection parameter
4. the traversal fraction
5. the same-edge interval formula
6. the zero-total-length convention

### The three witnesses, which are the fixtures

| | the case | today | required |
|---|---|---|---|
| **W1** summation order | one three-segment edge; `sum` of its segment lengths gives a first-vertex fraction of `0.16666666666666669` against a competing cost of `0.16666666666666666` | **1,000 s** | the costs tie and the time discriminator reports **1 s** |
| **W2** dot-product cancellation (pass 30) | segment `(0,0)→(1e-6,1e-6)`, weights `1e11`, origin `(122.09, -122.08999999999999)`: the two terms of `(px−ax)·dx + (py−ay)·dy` cancel to **exactly 0.0** in binary64 where the exact value is `1.4210854715202003e-20` | parameter 0, **0 s** of network travel, total **137.03 s PASS** | parameter `7.105427357601002e-9`, **710.542736 s**, total **847.58 s FAIL** |
| **W3** subtraction near the coordinate bound (pass 30) | `(-1e7,0)→(1e7,0)`, weights `1e19`, origin at `nextafter(1e7, 0)` — 1.86e-9 m before the endpoint | the subtraction rounds the projection onto the endpoint: empty route, **1.48e-9 s** | the geometric network time, **931.32 s** |

**W2 is the one that sets the method.** `fsum` of the already-rounded products still returns zero,
so a summation rule alone cannot reach it. Both W2 and W3 lie *inside* revision 11's declared
numerical domain, so the domain does not close this item either — revision 11's claim that its
bounds were "derived from where the arithmetic stops being exact" was withdrawn for exactly this
reason.

### The rule to adopt, and an honest limit on it

The design says this "needs exact binary-rational arithmetic in the projection". That is achievable
for the projection and **not** for arclength, and the amendment has to say so rather than promise
exactness it cannot deliver:

| quantity | achievable | rule |
|---|---|---|
| projection parameter `t` | **exactly rational** | `t = ((p−a)·(b−a)) / ‖b−a‖²` has no square root. Every binary64 is a rational, so numerator and denominator are exact; the clamp decision and every *ordering* comparison are made on the exact value, and the parameter is rounded to binary64 once, at a defined point, only if a binary64 is reported |
| squared distance, residual ordering | **exactly rational** | same argument. This is what T0's `exact_segment_sq` already does, over 843,135 points |
| segment length | **exactly rounded**, not exact | `‖b−a‖` is irrational. But `dx²+dy²` is an exact rational, and a correctly-rounded square root of an exact rational is computable with integer square roots on a scaled numerator and denominator. That is strictly better than `math.hypot`, which IEEE-754 does **not** require to be correctly rounded |
| prefix arclength, total length | **exactly rounded** | `math.fsum` over exactly-rounded lengths, which is order-independent — the rule §2.4 already requires for journey totals, extended downward as the design determined. Pass 22's left accumulation is the *less* accurate option and is not adopted: over the exact rational values, `0.6` is the exactly-rounded sum, nearer the true total than `0.6000000000000001` by a factor of three |
| traversal fraction `f` | **exactly rounded** | one division of two exactly-rounded quantities |
| same-edge interval, zero-total-length | **specified** | stated as formulae with the zero case normative, not left to an implementation |

> **So "closing item 1" means: exact where the quantity is rational, exactly-rounded where it is
> algebraic, with the composition order fixed and stated.** Not "exact throughout". Writing the
> amendment as the latter would be a promise the arithmetic cannot keep, and that is the shape of
> claim this project has had to withdraw twice.

### Tasks

1. **`v2/locfinder/measure/exact.py`** — the primitives: exact rational projection parameter and
   clamp; exact squared distance; correctly-rounded `sqrt` of an exact rational; exactly-rounded
   segment length. Fixture-first against W1, W2, W3 and the `toy.py` cases that already exercise
   the projection.
2. **A mutation harness** over it. Every rule in this project that was trusted on reading has
   failed; eight instances in `feedback-verify-the-shape-of-the-risk`.
3. **Design revision 13** — amend §2.4 with the table above, add a §13 row, and state the limit
   explicitly. A **semantic amendment** under §12's change policy: it changes a quantity, so it
   needs the row and fresh certification, not an "equivalent implementation change" note.
4. **Re-run T0 with the exact primitives** in place of `exact_segment_sq`'s ad-hoc version, and
   check the published figures move or do not. They should not — T0's diagnostic already used exact
   rationals for the projection — and confirming that is cheap.

**Time box: 2 days.** An expired box is reported, not silently extended.

---

## Phase 4b — T3, as a development comparator only

**Depends on:** 4a, T2 (frames — built), T4 (the conformance suite — built).

Built **fixture-first**, from T4's cases, which are derived from the design and from the reviews'
counterexamples rather than from this code.

### What T0 requires of it, as a design requirement rather than a preference

1. **The candidate universe is a parameter, not a constant.** T0's pre-registered rule returned
   *open on impact*, so A is provisional and C and D remain live. T3 must take the convention as
   configuration and record it in the run manifest — the pilot has already shown A, C and D sharing
   one deduplication and cap path, so this costs nothing to build and is very expensive to retrofit.
2. **It must be scalable in the way `toy.py` is not.** `toy.py` enumerates simple paths; stage 3
   needs paired routing over at least the 500+500 frame points under two conventions, and the
   census question is a benchmark away. The architecture that makes that affordable is the one
   already used in production — two CSR matrices over one sparsity, cost for selection and time for
   reporting — not path enumeration.
3. **Objectives 1 and 2 are both first-class.** Pass 36 F2 is the lesson: a bound on objective 1 is
   not a bound on objective 2, because selection is by cost and reporting is by time. The comparator
   must return both, and the `objective 2 − objective 1` gap as its own signed value, which §2.1
   already requires be reported and never subtracted.
4. **Route availability is a status, not a large number.** The same finding: on a one-way record a
   moved attachment can leave no legal journey at all. `NO_PATH` must be distinguishable from a long
   path at every layer, including in the manifest.

### Scope

§2's decision rules: attachment and the candidate set (§2.2), partial edges and the apportionment
rule, direction, competition, connectors charged to **both** objectives in **both** metrics, ties
(§2.4), bounds with metric and strictness (§2.5). **Not** §2.6's independent engine — that is E2's
path and a separate dependency.

### What makes it a *development* artifact

- Identity `comparator-v0-dev+<digest of the rules and the pinned runtime>`, derived like
  `profile_version`, never typed.
- The runtime is pinned and recorded: Python, NumPy, SciPy, Shapely, platform, byte order.
- **No cross-implementation claim.** Conformance means "this runtime, these fixtures"; it does not
  mean a second implementation would agree, and no output may say it does.
- Pass 20's instruction stands: nothing here is called frozen, and §12's first checkbox stays open.

**Time box: 3 days.** Fixture-first, so a day with no passing fixture is a reportable result.

---

## Phase 4c — T0 stage 3, the verdict impact

**Depends on:** 4b.

This is the question T0 left explicitly unknown, and pass 36 F3 changed its shape:

> **It cannot be restricted to the origins whose own attachments differ.** A *destination's*
> attachment change can affect any origin — the plan's own stage-3 text says so, and pass 36
> produced an origin whose A and C attachments agree and whose only journey disappears when a
> destination moves. Seven of 550 grocery sets differ between A and C. The withdrawn estimate that
> stage 3 would cost "2.5% of a full paired comparison" was wrong by that factor.

So the design is: route **every sampled origin** under each candidate convention, with the
destination set recomputed under that convention, and compare pairs.

- **Benchmark before choosing the scale**, as T0's own time box required and as paid for there:
  1,000 frame points first, then decide whether the censuses are affordable.
- Compare **paired seconds**, objective-specific selections, **exact** threshold verdicts and
  **encoded whole-minute** verdicts at the release limits — pass 24's exact ten-minute flip is not
  itself an encoded-minute flip.
- Report absolute changes, tails, maximum and **false-inclusion direction separately**.
- **Retain timeouts and unresolved comparisons** rather than counting them as agreement.
- Report impact **among displayed PASS results** as well as full-frame, since a low full-frame rate
  can conceal concentrated harm.
- The sensitivity budget is already pre-registered and **must not be re-derived**: 0.167% of a
  frame's verdicts, one sixth of E1b's 1.0% gate. It was committed before T0 ran and the same
  allocation governs stage 3.

**Time box: 1 day after 4b.** If routing proves unaffordable at any useful scale, publish the
attachment result as it stands and leave verdict impact **explicitly unknown** — which is what T0
does today, so this phase can fail without costing anything already held.

---

## What would invalidate this plan

- **4a turns out not to close W2.** The exact-rational projection is the method precisely because
  `fsum` cannot reach W2; if an exact projection still produces a wrong argmin on some witness, the
  item is wider than arithmetic and T3 stays gated.
- **The owner settles the convention by decision rather than measurement.** Then 4b.1 is unnecessary
  and 4c is only a confirmation. That is the owner's call and it is cheaper than this plan.
- **Exactly-rounded is judged insufficient** for the arclength quantities. Then item 1 cannot be
  closed as specified here and the honest options are to restrict the admissible domain further or
  to accept a declared convention, as §2.2 did for attachment.

## What this plan does not do

It does not touch §2.6's independent engine, the coverage requirement, the browser path (§0 step 6,
which still collapses UNKNOWN into EXCLUDED and still ignores the Triangle raster), the grocery and
geocoding truth audit (step 7), or the decision report (step 8). It does not revisit the
restricted-walk penalty: that is the owner's standing decision of 2026-11-10 — 120 s, monitored and
disclosed — and nothing in T0 bears on it.
