# S3: two proposals before revision 4

**Status:** proposal, for adversarial review and owner decision. **Not yet adopted.** Nothing here
changes the operative design, which remains
[`2026-11-04-s3-measurement-design.md`](./2026-11-04-s3-measurement-design.md) revision 3.
**Date:** 2026-11-05 · **Head:** `6a9c1f4` on `v2-rethink`

**Why this exists.** Codex passes 15 and 16 each returned **eighteen defects, eight High**, with the
verdict "not fit to execute as written" both times. Pass 16's disposition table shows seven of pass
15's eighteen repairs carried a **new** defect, and three of my repairs went wrong in the *opposite*
direction from the finding they addressed. Writing revision 4 the same way is unlikely to converge,
so this proposes a change of method as well as content — and submits that change to review before
acting on it, because a methodology change made unilaterally after two failed attempts is exactly
when I am least reliable.

---

## Part 1 — Two findings of my own, beyond pass 16

Recorded here because they refine pass 16 rather than repeat it, and both were obtained by reading
the repository rather than by argument.

### 1.1 The abstention problem is specific to the area frame, and no reallocation can fix it

Measured on the shipped reason raster and the buildings-per-cell raster:

| reason | share of **cells** | share of **structures** |
|---|---|---|
| OK | 77.69% | **97.34%** |
| `OFF_NETWORK` | **17.41%** | **0.71%** |
| `BEYOND_HORIZON` | 4.90% | 1.94% |

**96.6% of off-network cells (55,574 of 57,541) hold zero buildings.** So product abstention is a
large area phenomenon and a small structure phenomenon.

This is the **same asymmetry S2.4 already measured** — 77.69% cell against 97.34% building coverage —
and I failed to connect it when writing §7. The thing that made cell coverage look bad in S2.4 is
the thing that makes the frame-C gate unreachable in S3. Pass 16's framing ("makes the **area-frame**
acceptance gate effectively unreachable") is therefore precise, and the implication is that raising
*n* cannot help: 16.67% abstention at *T* = 10 is a property of the population, not of the sample.

### 1.2 The `EdgeIndex` collapse is a deliberately maintained invariant, so revision 3's repair would have broken it

Pass 16 finding 3 says my pre-collapse time projection leaves the same defect at the attachment
layer. Reading `v2/locfinder/traveltime/snap.py:66-69`, it is worse than that — the docstring states
the intent:

> "For each physical edge and direction the **cost-minimal** parallel edge wins and its own time is
> carried, **matching `csr.graph_to_cost_time_csr` so the two stages cannot disagree about which edge
> a path uses**."

So the collapse is not an oversight; it is an invariant the code deliberately maintains between the
node matrix and the attachment index. Revision 3's instruction to "project objective 1 from the
multigraph before any cost collapse" would have made the two stages **disagree**, which is a worse
failure than the one it was fixing.

**The correct shape is two parallel indices** — one cost-selected for objective 2, one time-selected
for objective 1 — each internally consistent with its own node matrix, rather than one index
mutated. That is a different instruction from the one revision 3 gives.

---

## Part 2 — Proposal A: abstention becomes its own gated estimand

**The defect.** §7 routes every product `UNKNOWN` into a bucket bounded both ways, so the
"all unknowns are errors" bound reaches ≈16.7% on frame C against an E1b threshold of 1.0%. But a
product `UNKNOWN` is **fully observed** — we know exactly what the product said — so bounding it as
though it might have been a PASS conflates two different ignorances.

**Proposed.**

1. **Only a product PASS can produce E1b**, and **only a product FAIL can produce E1a**. The
   directional estimands are conditioned on the product having made a claim.
2. **Product `UNKNOWN` is a separate estimand, E0 — abstention rate**, estimated on each frame with
   its own interval, and reported with the product reason retained (`OFF_NETWORK` and
   `BEYOND_HORIZON` have different remedies; the latter is answerable by searching further).
3. **The unknown bucket keeps only genuine comparator ignorance** — timeout, engine error, snap
   failure, no sound bound — which is small and is the thing both-ways bounding was designed for.
4. **E1a and E1b are reported with their denominators visible**: the share of the frame on which the
   product made a claim at all. A rate conditioned on a shrinking denominator must not be read as a
   rate over the frame.

**The obvious attack, which this proposal must survive.** If abstention is not gated, **a product
that abstains everywhere passes E1 trivially** — the gate becomes vacuous, and the design would have
created a direct incentive to abstain. So E0 must itself be gated, and this proposal is incomplete
without a threshold for it. I do not have a principled value: 0.71% of structures is already the
status quo for walk, so any threshold near it is reverse-engineered from the current artifact, which
is the thing predeclaration forbids. **This is the part I am least confident about and most want
attacked.**

## Proposal B: the gate is frame B; frame C is reported

**Proposed.** §8's "every published mode and threshold must pass on **both** frames" becomes: the
**acceptance gate is frame B** (structures), and **frame C is reported descriptively** with its own
E0, E1a and E1b and no gate.

**For:** an area-average gate is dominated by ground nobody lives on — 96.6% of the abstaining cells
hold zero buildings, and 17.41% of the area is off-network. The product's purpose is to tell a
household where it could live, which is a statement about structures.

**Against, and this is not weak:** frame C is the frame for "the published surface as a surface",
which is what gets rendered on a map, and a surface that is wrong across 17% of the visible area is a
real defect even where nobody lives. Demoting it to descriptive could be the same move as weakening a
threshold after seeing it fail — the difference being that no S3 data exists yet, which is precisely
why the decision is legitimate **now** and would not be later.

**Alternative not chosen:** give frame C its own looser thresholds. Rejected because any value would
be chosen with the 16.67% abstention figure already in view, which is choosing a threshold from the
data.

---

## Part 3 — Proposal C: split the design by what predeclaration is for

**The diagnosis.** Six of pass 16's eight High findings have the same shape: **the prose says X and
the code would do Y.** Mid-edge attachment on a one-way parallel pair; which metric a search bound is
expressed in; the verdict algebra; the edge-index collapse; the persisted schema's threshold keying;
the status-code wire contract. Every one would have surfaced within minutes of writing the code and
its fixtures. Prose has no type checker, and two reviewers' worth of careful reading is an expensive
and unreliable substitute for one failing test.

Meanwhile, what **survived both passes untouched** is the statistical commitment: the allocation
table (every value reproduced twice), the removal of the design effect, the frame definitions, the
claim boundaries, the 2,600-origin budget.

**Proposed.** Predeclaration exists to prevent choosing the analysis after seeing the data. Split the
document accordingly:

- **Stays predeclared, frozen in prose:** estimands (now including E0), frames, allocations,
  acceptance thresholds, uncertainty conventions, the adaptation and selection policy, and the
  development/certification separation. These are statistical degrees of freedom and prose is the
  right medium.
- **Moves into a tested implementation the design cites:** the comparator's mechanics — attachment
  geometry, partial-edge traversal, parallel alternatives, bound metrics and strictness, the verdict
  function. Built fixture-first, with each pass-16 counterexample as a test before the code exists.
  The design references the tested behaviour instead of restating it.

**The tension I cannot resolve by myself, and the real question for this review.** The split is
**not clean**, because some comparator choices *are* statistical degrees of freedom. Whether the
destination connector is charged changes the measured E1 rate. Whether a bounded no-result scores as
a failure or an unknown changes E1b directly. If those move into "implementation", then the
measurement can be tuned after the fact by an implementation decision — **which is exactly the escape
hatch predeclaration exists to close.** So Proposal C risks being a principled-sounding way to
exempt the hard parts from the discipline that has been catching my errors.

My tentative line is: a comparator choice that could **change the measured rate** stays predeclared
(charge the connector; which objective pairs to which estimand; direction; destination-set identity;
how a bound maps to a verdict), while a choice that is purely **about computing the predeclared
quantity correctly** goes to code (how a partial edge is traversed, how parallel alternatives are
preserved, how the index is built). I am not confident that line is drawable in practice, and I would
rather be told it is not than discover it in pass 18.

---

## What I would do on each answer

| if | then |
|---|---|
| A accepted with an E0 threshold supplied | revision 4 fixes the estimands and §7, and the gate is reachable on both frames |
| A accepted, no E0 threshold yet | revision 4 defines E0 and marks its threshold **an open owner decision that blocks certification**, not the build |
| B accepted | §8 gates frame B only; frame C reports E0/E1a/E1b descriptively |
| B rejected | frame C needs either its own predeclared thresholds or an abstention-excluded estimand, and I would want the choice made before any data exists |
| C accepted | §§2 and 7 become a cited implementation; T1 and T3 are built fixture-first from pass 16's counterexamples |
| C rejected | revision 4 rewrites §§2 and 7 in prose with every pass-16 counterexample addressed, and I should expect a pass 18 of similar size |
