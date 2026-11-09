---
name: feedback-a-relative-invariant-cannot-see-an-absence
description: "A relative invariant cannot see an absence, a positional truncation, or a defect only far from the origin; three reviews defeated the same layer this way, and five of my replacement checks rejected correct code"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 3448970c-7f62-4034-83e7-b7d86efb0261
  modified: 2026-11-06T17:35:33.105Z
---

Learned 2026-11-06 from Codex pass 22, which defeated the invariant layer built in response to pass
21. I asked it to construct a wrong implementation that passes **both** the conformance corpus and
the new invariant layer. It did, with four lines:

```python
real = toy._simple_paths
toy._simple_paths = lambda g, s, go: [p for p in real(g, s, go) if len(p[2]) <= 4]
```

**423/423 tests passed, mutated and unmutated.** Reproduced before planning on it.

**This happened three times, and I drew the lesson too narrowly after the first.** Pass 23 then did
it twice more on the corrected layer: a `destinations[:4]` truncation passed all **1,040** tests
(no oracle call anywhere received more than three destinations) and an orientation rule wrong only
outside a coordinate box passed all **527** (every identity anchor sat near the origin).

**The general form.** A relative invariant compares two runs, so it cannot see:
- an **absence** — a mutant that removes results reports `None`, and `None` equals `None`;
- a **positional truncation** — both sides of a transform are truncated alike;
- a defect only **far from the origin** — no near-origin transform reaches it;
- anything the **comparison key does not carry**.

Every repair is an **absolute anchor**: a named number, at each point of the dimension.

**Two separate reasons the first one was invisible, and both generalise.**

1. **Hop depth was not a declared dimension.** The mutant recognises no fixture and every journey it
   returns is correct — it just stops looking. Every *relative* invariant held because both sides
   were equally truncated. The gap was a **dimension**, not an input: 22 shapes, none needing a
   journey more than four edges deep. The fix is a parameterised family (`CHAIN_DEPTHS = (2,4,5,7,9)`)
   plus a `shapes` entry, so the dimension is named rather than sampled by accident.
2. **A relative invariant cannot see an absence.** Adding the chain scenarios *did not catch it*, and
   the measurement said so immediately. A mutant that removes journeys reports `None` for every
   field; the transform comparisons then find `None` equal to `None`; and every per-result check sits
   behind `if objective1_s is not None`. The depth had to be **anchored to a number**, exactly as a
   uniformly tightened cap and a uniformly connector-free cost had to be.

**The harder lesson: eight of my invariants rejected correct answers** — three found by pass 22, five
more by pass 23 in the *repairs* written for pass 22. That is worse than an escape, because it blocks
a correct implementation and reads as a code defect.

- The **affine scaling law** — written one pass earlier to replace a proportionality that review had
  refuted — asserted selection was scale-invariant. The connector term that makes a total affine is
  *precisely* what gives journeys different intercepts, so their lines cross: selection b, b, **a** at
  scales 1, 3, 7. Proportional → affine → refuted. **The pattern ran inside the instrument built to
  stop it.** What survives is concavity (a minimum of affine functions) plus affinity conditioned on
  the journey holding — and the *condition* then took two more goes to get right; see below.
- "A journey whose endpoints differ has a non-empty route" rejected a legal answer where both points
  attach at one position and all movement is in the connectors. I rewrote it as an equivalence and
  `zero_weight_edge` refused that within the minute — a 0 s edge gives a real route with zero network
  seconds. Only the **implication** survives.
- Orientation under translation: it is chosen lexicographically on the *rounded* geometry, so an
  offset can legitimately flip it. Monotonicity of addition proves nothing about a choice made after
  rounding.

Pass 23's five, which are the pattern at its purest because they are all in repairs:
- the affinity law conditioned on **route and destination** holding — neither names the attachment
  occurrence, so an attachment can switch with both unchanged (slopes 20.000984126984125 against 20).
  The exact condition is `n_journeys == 1`.
- **concavity at an absolute 1e-9** — true of the real-arithmetic envelope, false of binary64: one
  edge of 100000000.1 has a chord 5.96e-8 above the middle value. Needs a magnitude-proportional
  allowance, labelled an allowance.
- `differences` documented non-finite as always a difference and **wasn't** — equality caught two
  infinities, identity caught a shared NaN. Fixing pass 22's defect introduced its exact mirror.
- the seconds tolerance required a clean `±tol` **neighbourhood**, refusing two values 4.5e-12 s apart
  that are both FAIL at every threshold. **Compare the verdict predicates, not a neighbourhood.**
- the **connector anchor** written to replace the withdrawn intercept inference asserted two of the
  four numbers it claimed. *The replacement for an overstatement was itself an overstatement.*

**How to apply.**
- **Every relative layer needs absolute anchors**, one per dimension where a uniform defect is
  possible: boundaries, magnitudes, reachability at depth, cardinality of every input list, absolute
  position, inclusion of a term. If a defect would be invisible with both sides equally wrong, only a
  named number sees it.
- **When an anchor replaces a withdrawn claim, check it asserts all of what the claim did.** Mine
  asserted two of four because its origin connector was zero and its winner's destination connector
  was zero — the zeros that made the case convenient also made it blind.
- **An invariant conditioned on reported fields holds nothing fixed.** Reported fields are a
  projection; two runs agreeing on them can differ in what produced them. Condition on something
  structural and exact (here, "the graph admits one journey"), or construct the held case directly.
- **A theorem about real arithmetic is not a predicate on binary64 output.** Concavity, affinity and
  monotonicity all need a magnitude-proportional allowance, and calling it an allowance rather than
  an error analysis is the honest version until a numerical domain is declared.
- **Check your own coverage table before a reviewer does.** `EXPECTED_COVERAGE` recorded the
  connector-free mutant escaping the invariant layer from day one. That row *was* the proof that the
  intercept check could not establish connector inclusion — a zero intercept is non-negative and
  affine. I read my own table as bookkeeping instead of as evidence.
- **Fix the binding class, not the binding.** Pass 21: `invariants.py` imported `directed_identity`
  by name, so the mutant was unreachable. I fixed that one name. Pass 22 patched `toy.evaluate` —
  still imported by name in **both** layers — and a wrapper adding 1000 s to every journey left
  `invariant_violations()` returning `[]`. Add a **sentinel mutation** whose only job is to fail if
  any layer stops seeing an evaluator replacement; without it every coverage row measures nothing.
- **"Measured across the domain" is a lie if you measured the scenarios.** I wrote that subdivision
  divergence was "float noise except on a zero-length segment". A midpoint on one ordinary straight
  edge moves 600.0349975 s to 599.9789683 s — FAIL to PASS. Same error for a 1e-11 s float spread,
  refuted at 7.5e-9 s. Say "observed on these N scenarios".
- **Order a tolerance check: exact equality, then non-finite, then magnitude, then decision
  relevance.** Mine asked about decision-relevance first, so two identical values of exactly 600.0 s
  compared *different*, and `abs(a - nan) > tol` being false let NaN replace a finite answer.
- **Do not let a quantity borrow another unit's threshold test.** A cost faces no published
  threshold, only an argmin, so no tolerance on it is decision-irrelevant — record that rather than
  running it through a seconds test.

Related: [[feedback-fix-the-domain-not-the-example]],
[[feedback-a-fixture-is-exact-only-where-you-point-it]], [[feedback-benchmark-over-point-fixes]],
[[feedback-computable-property-is-not-the-claim]], [[feedback-codex-adversarial-review]].
