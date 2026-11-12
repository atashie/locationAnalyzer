# Step 4 — T3 as a versioned development comparator

> **For Claude:** this is a plan. Nothing here reports a result.

**Status:** plan, **revision 2**, rewritten 2026-11-11 after Codex pass 37 (4 High, 3 Medium, 1 Low —
all eight reproduced, seven re-derived independently). Revision 1 is in history at `255970e`.
**Written 2026-11-11**, after T0 (plan §0 step 3) and Codex passes 36 and 37.

**Goal.** A scalable comparator implementing design §2's decision rules, usable as a *development*
artifact under §12's rewritten terms — pinned runtime, no cross-implementation claim — so that T0
stage 3, S3.1's grid comparison and E1 can run against something other than `toy.py`.

---

## What revision 1 got wrong

Pass 37 reviewed revision 1 and tripped its own first invalidation condition. The corrections come
first rather than being folded in silently, because the plan's shape changed and the reasons matter
more than the new text. Full detail in `docs/research/38-codex-review-pass37.md`.

| revision 1 said | actually |
|---|---|
| exact-rational projection plus exactly-rounded arclength **closes** §12 item 1 | it closes item 1 **as the design words it** and leaves a distinct, newly named gap: the selected argmin can still differ from the real-arithmetic one, with a PASS/FAIL consequence, inside the declared domain (F1) |
| the composition is **exactly rounded** | correctly rounding each operand does not correctly round their ratio or their sum. `fsum(1, RN(√2))` then dividing gives `0.4142135623730951`; `RN(real f)` is `0.41421356237309503` (F1) |
| W1's **required** answer is a tie reporting **1 s** | under the adopted `fsum` rule W1 reports **1,000 s**, which is what the code already does. 1 s is reachable only by the left accumulation this plan rejects (F2) |
| `fsum` **cannot reach** W2 | `fsum` of the already-rounded products cannot. `fsum((px,py)) * dx` reaches it exactly, because `dx == dy` in W2. W3 and F1 carry the argument for exact rationals; W2 alone does not (F8) |
| 4b.2: "**two CSR matrices**, cost for selection and time for reporting" is the architecture | that is **one cost-selected view**, and it erases objective 1 — which 4b.3 requires as first-class, four lines later. Parallel `(1,100)` and `(10,10)` leave only `(10,10)` (F4) |
| the two-CSR architecture makes a scalable implementation affordable | §2.4's whole-journey tie rule is **not implementable by a scalar-label search at all**. A pruned prefix can rejoin the final cost tie and win it on time (F3) |
| the six quantities are settled by the rule table | two of them are marked "specified", which is a promise to write a formula. The same-edge interval has two "exactly rounded" readings that split **666.13 s FAIL against 558.79 s PASS** (F5) |
| T0's `exact_segment_sq` is already the arithmetic 4a needs, over 843,135 points | it returns **only a squared distance**, and `raw_positions` calls it **zero** times — the parameter, position, occurrence and arclength all come from the float path. The 843,135 is the census count, not a count of rational attachments (F7) |
| 4c answers T0's verdict-impact question | it answers cross-convention disagreement **on one fixed graph**. Routed sensitivity to lawful re-expression is a different experiment (F6) |
| §12 item 4 is "implemented, not amended" | **settled** in revision 11. That phrase is the design's own, describing the state before the lift |

**What pass 37 confirmed, which is load-bearing for what follows:** the correctly-rounded rational
square root is achievable and it supplied the algorithm; the "better than `math.hypot`" claim is true
on this platform with a witness (`hypot(4194304.125000001, 0.06250000093132257)` is wrong in the last
place); the factor-of-three figure is exact; `fsum` order-independence holds **in this domain**;
W2's and W3's published numbers reproduce; T2 and T4 verify at their digests; §12 items 2, 3 and 4
are settled; §2.6 is genuinely separate; and T0's "open on impact" outcome stands.

---

## The gate: what is open, after two reviews

| §12 blocker | state |
|---|---|
| 0. the candidate universe | **measured by T0.** The pre-registered rule returned **open on impact**, so §2.2's convention A stays provisional. Not a blocker; a **design requirement on T3** — see 4b.1 |
| 1. the geometry arithmetic | **OPEN. This is phase 4a**, and it is closable as the design words it |
| 2. what uniqueness §2.4 promises | settled, revision 11, at its stated scope. T10 still owes a reconstruction rule; that blocks T10's boundary-touch output, not 4b's totals |
| 3. the admissible numerical domain | settled, revision 11, extended after pass 30. It prevents the demonstrated underflow and overflow. It does **not** prevent F1 |
| 4. the final cost discriminator | **settled**, revision 11, normative in §2.4 |
| **NEW: the argmin is not the real argmin** | **opened by pass 37 F1.** Distinct from item 1 and not closable by arithmetic. 4a.2 bounds it by measurement rather than leaving it unknown |
| **NEW: §2.4's tie rule is not implementable by a scalar search** | **opened by pass 37 F3.** Distinct from geometry and unaffected by 4a. 4b.0 decides what to do about it |

---

## Phase 4a — close §12 item 1, and name what it does not close

§12 item 1 asks for two things: the six unfrozen geometry quantities settled, and "an exact
binary-rational fallback for the cancellation-sensitive projection terms". Both are achievable. The
third thing revision 1 implied — that this makes the comparator's selection agree with real
arithmetic — is not, and the amendment has to say so.

### 4a.1 — the primitives and the six formulas

| quantity | achievable | rule |
|---|---|---|
| projection parameter `t` | **exactly rational** | `t = ((p−a)·(b−a)) / ‖b−a‖²` has no square root. Every binary64 is a rational, so numerator and denominator are exact; **the clamp decision and every ordering comparison are made on the exact value**, and `t` is rounded to binary64 once, at a defined point, only if a binary64 is reported |
| squared distance, residual ordering | **exactly rational** | same argument, and no square root is needed to order distances |
| segment length | **exactly rounded** | `dx²+dy²` is an exact rational. Correct rounding of its root is achieved by pass 37's algorithm: take the output binade's lattice unit `u`, compute `k = isqrt(⌊q/u²⌋)`, then compare the **original rational** `q` against `((k+½)u)²`, resolving equality to even significand. **Integer scaling alone is not a rounding proof** — the discarded numerator and denominator information must survive into the midpoint comparison |
| prefix arclength, total length | **exactly rounded per operand, order-independent** | `math.fsum` over exactly-rounded lengths. **Not** `RN` of the real sum: on `(0,0),(1,0),(2,3)`, `fsum` gives `4.16227766016838` where `RN(1+√10)` is `4.162277660168379`. Left accumulation stays rejected — over the exact rationals `0.6` is the exactly-rounded total, nearer the truth than `0.6000000000000001` by a factor of three |
| traversal fraction `f` | **one rounded division, numerator defined** | `f = RN(prefix / total)` where `prefix` and `total` are the exactly-rounded quantities above and `prefix` is the arclength **from the record's first vertex in the direction of travel**. For an interior attachment the prefix is `fsum(whole segments) ` then `+ RN(t × RN(segment length))`, in that order |
| same-edge interval | **chosen, not merely "specified"** | `f = RN(|s_d − s_o| / total)`, where `s_d` and `s_o` are each the exactly-rounded prefix above and the subtraction is performed **on the exact rational prefixes before rounding**. The rejected reading, `|RN(s_d/total) − RN(s_o/total)|`, differs: at an admissible weight of `6e18`, 666.13 s FAIL against 558.79 s PASS |
| zero total length | **normative value** | `total == 0` gives `f = 0`, every occurrence on the record shares one position, and the record contributes `cost_base + penalty` once with no apportionment. Distinct structural vertices on an all-zero-length record are **one** occurrence for §2.2's identity and the record's own vertex index is retained for provenance |

> **What "closing item 1" means, stated so it cannot be read as more:** exact where the quantity is
> rational, exactly-rounded where it is algebraic, every comparison that *decides* something made on
> the exact value where one exists, and the composition order fixed and written. **It does not mean
> the comparator selects what real arithmetic would select.** It cannot: the traversal fraction is
> irrational, so two candidates whose exact costs differ by less than one ulp of that fraction can
> still be ordered wrongly or tie when they should not, and no binary64 convention avoids that.

### 4a.2 — measure the gap instead of leaving it unknown

Pass 37 F1's residue is a *new* item, and this project's standing method applies to it: decide by
measurement, not by argument. A certified comparison is possible even though an exact binary64
answer is not — the costs are algebraic, and exact rational interval arithmetic over
correctly-rounded square-root bounds separates them in all but genuinely equal cases.

So: a **certified cost comparator** as a separate predicate, used as a diagnostic rather than in the
hot path.

- Filter first on the rounded convention with an error bound; refine an exact rational interval only
  when the bound does not decide. This runs on near-ties only, so the cost is paid where it buys
  something.
- Three outcomes: `AGREES`, `DIFFERS` with both selections recorded, and **`UNRESOLVED`** at a
  declared refinement limit. `UNRESOLVED` is a retained status and is never counted as agreement —
  the same rule 4c already applies to timeouts.
- The reported quantity is **how often the normative convention's argmin differs from the certified
  one**, over T4's fixtures and over T2's frames. That turns F1 from an open gate into a disclosed,
  measured limit.

**This is what lets T3-as-development proceed.** Pass 20's instruction already permitted ordinary
development; what it refused was a frozen T3, and that stays refused.

### The three witnesses, and what each is now for

| | the case | current | expected under 4a |
|---|---|---|---|
| **W1** summation order | one three-segment edge, lengths `0.1, 0.2, 0.3`; first-vertex fraction `0.16666666666666669` against a competing cost of `0.16666666666666666` | **1,000 s** | **1,000 s — unchanged.** W1 **pins** the adopted rule against left accumulation's 1 s. It is a regression fixture, not a repair |
| **W2** dot-product cancellation (pass 30) | segment `(0,0)→(1e-6,1e-6)`, weights `1e11`, origin `(122.09, -122.08999999999999)`: the two terms of `(px−ax)·dx + (py−ay)·dy` cancel to **exactly 0.0** where the exact value is `1.4210854715202003e-20` | parameter 0, **0 s** of network travel, total **137.0328 s PASS** | parameter `7.105427357601002e-9`, **710.542736 s**, total **847.5755 s FAIL** |
| **W3** subtraction near the coordinate bound (pass 30) | `(-1e7,0)→(1e7,0)`, weights `1e19`, origin at `nextafter(1e7, 0)` — 1.86e-9 m before the endpoint | the subtraction rounds the projection onto the endpoint: empty route, **1.48e-9 s** | the geometric network time, **931.3226 s** |
| **W4** the same-edge reading (pass 37 F5) | W3's geometry at weight `6e18`, origin and destination both on the record | — | **558.7935 s PASS** under the adopted reading; the rejected reading gives 666.1338 s FAIL |
| **W5** the real/rounded argmin flip (pass 37 F1) | records `(0,0),(1,0),(2,1)` time 2400 cost 1, and `(0,0),(1,0)` time 1 cost `0.4142135623730951`; origin `(0,0)`, destination `(1,0)` | **1 s PASS**, by a manufactured tie | **1 s PASS — unchanged**, and 4a.2's diagnostic reports `DIFFERS` with the certified selection's 994.1125 s |

**W2 and W3 are what exact rationals are for.** W2 alone does not establish that — `fsum((px,py))·dx`
reaches it, because `dx == dy` there. W3's rounding of a subtraction onto an endpoint is not
reachable by any reassociation, and W5 needs certified comparison rather than better rounding.

### Tasks

1. **`v2/locfinder/measure/exact.py`** — exact rational projection parameter and clamp; exact squared
   distance; correctly-rounded `sqrt` of an exact rational by the binade-lattice algorithm;
   exactly-rounded segment length; the prefix, fraction, same-edge and zero-length formulas above as
   named functions. Fixture-first against W1–W5 and the `toy.py` cases that already exercise the
   projection.
2. **`v2/locfinder/measure/certify.py`** — the certified cost comparison of 4a.2, with
   `AGREES`/`DIFFERS`/`UNRESOLVED` and a declared refinement limit.
3. **A mutation harness** over both. Every rule in this project that was trusted on reading has
   failed; there are eight instances in `feedback-verify-the-shape-of-the-risk` and pass 37 is a
   ninth. The harness must include a mutant that **rounds each operand correctly and composes
   wrongly**, because that is the mutant revision 1 would have shipped.
4. **Design revision 13** — amend §2.4 with the rule table; add a §13 row; add the **two new §12
   items** (the argmin gap, the scalar-search gap) rather than silently closing item 1 over them;
   state the limit in the terms of the callout above. A **semantic amendment**: it changes a
   quantity, so it needs the row and fresh certification, not an "equivalent implementation change"
   note.
5. **Re-run T0 against the new primitives** — as a **behaviour-preserving refactor first**
   (`exact_segment_sq` keeps its contract and gains a tested one), then as a separate, labelled
   adoption of exact parameters, positions and occurrences. Compare **memberships and statuses**, not
   only totals. Unchanged figures are a **hypothesis to test**, not a prediction — `raw_positions`
   takes its parameter and occurrence from the float path today, so the adoption can move them.
   T0's convention C filters on computed float residual **equality**; a rational predicate makes a
   **different variant** and must be versioned as one, not allowed to inherit the pilot's evidence.

**Time box: 3 days** — 2 for 4a.1, 1 for 4a.2. Revision 1 said 2 and did not include 4a.2, the two
missing formulas, or the refactor-then-adopt split. An expired box is reported, not silently
extended.

---

## Phase 4b — T3, as a development comparator only

**Depends on:** 4a, T2 (frames — built and verified), T4 (the conformance suite — built and verified).

Built **fixture-first**, from T4's cases, which are derived from the design and from the reviews'
counterexamples rather than from this code.

### 4b.0 — the search-semantics spike, which comes before any promise of scale

Pass 37 F3 is not an arithmetic problem and 4a does not touch it. **§2.4's whole-journey tie rule is
not implementable by a scalar-label shortest-path search.** A prefix that is strictly more expensive
at a merge can join the final rounded-cost tie after a shared suffix and win it on time; once pruned
it cannot be recovered, and neither post-hoc `fsum` nor an exact additive search followed by rounding
its winner recovers it.

Decide this before committing to an implementation, and report which was chosen:

- **retain a band** — keep every label within a declared neighbourhood of the best, sized from the
  largest reachable suffix ulp, and prove or measure what it misses;
- **amend the rule** — make whole-journey cost accumulation edge-by-edge so the label *is* the cost.
  A semantic amendment, and it changes answers;
- **accept and measure** — implement the scalar search, and use 4a.2's certified comparator and the
  exhaustive `toy.py` oracle to measure how often the result differs, on T4's fixtures and on small
  random graphs.

**Recommendation: measure first, then choose.** If the divergence is unobservable on the fixtures and
on random graphs at realistic weights, "accept and measure" is honest and cheap, and the band is
over-engineering. If it is observable, the band is required. Either way the answer is a number, not
an argument. **Box: 1 day, and 4b's own box does not start until this reports.**

### What T0 and the two reviews require of it, as design requirements rather than preferences

1. **The candidate universe is a parameter, not a constant.** T0's pre-registered rule returned
   *open on impact*, so A is provisional and C and D remain live. T3 takes the convention as
   configuration and records it in the run manifest — the pilot already runs A, C and D through one
   deduplication and cap path, so this costs nothing now and is very expensive to retrofit.
2. **Two objective views, not one cost-selected pair.** Revision 1's "two CSR matrices, cost for
   selection and time for reporting" is the production pair, and it **cannot answer objective 1**:
   parallel alternatives `(1,100)` and `(10,10)` leave only `(10,10)`, so objective 1's one-second
   edge is gone from both matrices. T3 needs a **cost-selected view and a time-selected view over one
   sparsity**, built from a shared record set that keeps weight-distinct parallel records apart.
   Three further defects in the production routine must not be inherited: equal-cost alternatives
   resolve **by insertion order** rather than by the normative time discriminator; `_validate`
   **rejects admissible zero weights**; and no CSR-entry-to-directed-record mapping is returned, so
   attachment occurrences cannot survive into selection.
3. **Occurrences, not positions.** Pass 36 F7's self-crossing limitation applies here too: two passes
   of one road at one XY are one place and two decisions. The record set must carry occurrence
   identity, and the search must carry the directed record it traversed.
4. **Objectives 1 and 2 are both first-class.** Pass 36 F2 is the lesson: a bound on objective 1 is
   not a bound on objective 2, because selection is by cost and reporting is by time. The comparator
   returns both and the `objective 2 − objective 1` gap as its own signed value, which §2.1 already
   requires be reported and never subtracted.
5. **Route availability is a status, not a large number.** On a one-way record a moved attachment can
   leave no legal journey at all. `NO_PATH` must be distinguishable from a long path at every layer,
   including in the manifest.
6. **Partial terms at both ends, and the direct same-edge case.** The query's entry and exit partial
   traversals each apply the fraction to the **already-formed** full cost including penalty, per
   §2.4's frozen term; both connectors are charged to **both** objectives in **both** metrics; and a
   same-edge direct journey competes with the endpoint and network journeys rather than replacing
   them.
7. **An acceptance checklist, because green T4 is evidence for T4's own assertions.**
   `conformance.check` does not compare every `OracleResult` identity and cost field and does not
   carry traversal intervals. A semantic arithmetic amendment needs reviewed fixture and oracle
   updates; it may not assume the existing suite validates it.

### Scope

§2's decision rules: attachment and the candidate set (§2.2), partial edges and the apportionment
rule, direction, competition, connectors, ties (§2.4), bounds with metric and strictness (§2.5).
**Not** §2.6's independent engine — pass 37 confirmed that is genuinely a separate dependency for
what 4b and 4c promise, and it is E2's path.

**One thing to keep saying out loud:** T3 and the product share graph, speeds and destination
assumptions. E1 therefore establishes construction agreement, not truthful access or a usable
grocery. That is shared-model blindness, not a dependency cycle, and only E2/E3 and the step 7 audit
reach it.

### What makes it a *development* artifact

- Identity `comparator-v0-dev+<digest of the rules and the pinned runtime>`, derived like
  `profile_version`, never typed.
- The runtime is pinned and recorded: Python, NumPy, SciPy, Shapely, platform, byte order.
- **No cross-implementation claim.** Conformance means "this runtime, these fixtures"; it does not
  mean a second implementation would agree, and no output may say it does.
- Pass 20's instruction stands: nothing here is called frozen, and §12's first checkbox stays open.

**Time box: 3 days after 4b.0 reports**, and 4b.0 may extend it. Fixture-first, so a day with no
passing fixture is a reportable result.

---

## Phase 4c — T0 stage 3, the verdict impact

**Depends on:** 4b.

This is the question T0 left explicitly unknown, and pass 36 F3 changed its shape:

> **It cannot be restricted to the origins whose own attachments differ.** A *destination's*
> attachment change can affect any origin — the plan's own stage-3 text says so, and pass 36 produced
> an origin whose A and C attachments agree and whose only journey disappears when a destination
> moves. Seven of 550 grocery sets differ between A and C.

So: route **every sampled origin** under each candidate convention, with the destination set
recomputed under that convention, and compare pairs.

- **Benchmark before choosing the scale**, as T0's own time box required: 1,000 frame points first,
  then decide whether the censuses are affordable.
- Compare **paired seconds**, objective-specific selections, **exact** threshold verdicts and
  **encoded whole-minute** verdicts at the release limits — pass 24's exact ten-minute flip is not
  itself an encoded-minute flip.
- Report absolute changes, tails, maximum and **false-inclusion direction separately**.
- **Retain timeouts, `NO_PATH` and `UNRESOLVED`** rather than counting any of them as agreement.
- Report impact **among displayed PASS results** as well as full-frame, since a low full-frame rate
  can conceal concentrated harm.
- **Retain per-point memberships and provenance**, not only aggregate counts. Pass 36 F3 withdrew a
  claim that the affected points were enumerated; they were not, because the artifact held counts.

**The denominator does not change, and pass 37 checked this.** Routing more origins changes the
*work*, not the *statistic*. The budget is `1%/6` of **each frame's verdicts at each threshold**,
with frame B's 500 and frame C's 500 kept separate and each convention pair and objective identified.
It is not divided by differing attachments, by changed destinations, by the displayed-PASS subset, or
by a pooled collection of pairs. Use the registered `1%/6`, not its three-decimal display `0.167%`,
as the threshold. **It must not be re-derived after seeing stage 3.**

**What 4c does not measure, named so it is not later claimed.** It measures cross-convention
disagreement **on one fixed graph**. It does not measure routed sensitivity to lawful re-expression:
pass 37 F6 showed an ordinary straight 100 m one-way record where every convention agrees at
600.0350 s FAIL, encoded minute 11, and inserting the exact midpoint moves A to 599.9790 s PASS,
encoded minute 10, while the exact minima stay put. Every original-graph pair can agree with that
exposure present. A routed transformation experiment is **separate**, needs destination attachments
transformed too, and needs a prior decision this plan does not make: how full time, base cost and
penalty are apportioned across split pieces. Reapplying a fixed 120 s penalty to each piece would
change policy rather than representation and confound the experiment.

**Time box: 1 day after 4b.** If routing proves unaffordable at any useful scale, publish the
attachment result as it stands and leave verdict impact **explicitly unknown** — which is what T0
does today, so stopping costs nothing already held. A **discovered contradiction** is different: it
must update the affected attachment claims. Stopping without a result cannot be used to retain a
claim a result has falsified.

---

## What would invalidate this plan

- **The certified comparator of 4a.2 does not terminate usefully.** If `UNRESOLVED` is common rather
  than rare, the argmin gap stays unmeasured, and the honest move is to publish the convention with
  the gap declared unknown rather than to claim a bound.
- **4b.0 finds the scalar-search divergence observable at realistic weights.** Then the band or the
  rule amendment is required, 4b's box is wrong, and §2.4 may need a semantic change this plan has
  not scoped.
- **The owner settles the convention by decision rather than measurement.** Then 4b.1 is unnecessary
  and 4c is only a confirmation. That is the owner's call and it is cheaper than this plan.
- **Exactly-rounded is judged insufficient** for the arclength quantities. Then the honest options are
  a further restricted domain or a declared convention, as §2.2 did for attachment.

## What this plan does not do

It does not touch §2.6's independent engine, the coverage requirement, the browser path (§0 step 6,
which still collapses UNKNOWN into EXCLUDED and still ignores the Triangle raster), the grocery and
geocoding truth audit (step 7), or the decision report (step 8). It does not revisit the
restricted-walk penalty: that is the owner's standing decision of 2026-11-10 — 120 s, monitored and
disclosed — and nothing in T0 or in pass 37 bears on it.
