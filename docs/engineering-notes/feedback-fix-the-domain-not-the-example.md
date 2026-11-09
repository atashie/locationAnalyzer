---
name: feedback-fix-the-domain-not-the-example
description: "Three reviews in a row, closing the reviewed defect opened an adjacent one; the exit is an invariant layer over a declared admissible-input domain plus a mutation guard, not more cases"
metadata: 
  node_type: memory
  type: feedback
  modified: 2026-11-06T14:52:55.398Z
  originSessionId: 3448970c-7f62-4034-83e7-b7d86efb0261
---

Learned 2026-11-06 on S3's comparator design, across Codex passes 19, 20 and 21. **Each pass's fix
became the next pass's finding.** Pass 19's two blockers → revision 6 → four of pass 20's eleven
findings → revision 7 → three of pass 21's nine. Pass 21 named the cause, and the sentence is the
memory:

> **"Treating repair of the motivating example as evidence that a replacement rule's domain is
> settled."**

A counterexample proves a point. A rule's **domain** is a different object, and closing the point
says nothing about it. Three times I wrote a replacement rule, checked it against the case that
motivated it, and shipped the domain unexamined — rounding a candidate key to centimetres after
rounding it to a position, complementing an orientation bit, declaring a summation without declaring
the terms.

**The exit, which pass 21 also supplied:** *"a compact set of invariants and admissible-input rules
exercised across representations, rather than another claim that the previous named examples now
pass."* Built as `v2/locfinder/measure/invariants.py` + `mutants.py` + `tests/test_mutants.py`.

**How to apply.**
- **Declare the admissible input domain and enforce it in the constructor.** A claim of total
  ordering over floats needs a finite-input contract under it.
- **Name the structural shapes** and keep one scenario per shape, each tagged. A shape arriving in a
  finding becomes a shape in the domain, not another one-off case. Mine: parallel, shared-identity,
  oneway, partial-edge, multi-segment, self-crossing, closed, palindrome, reverse-traversal,
  zero-length-segment, zero-weight, zero-span, disconnected, geometric-tie, penalty, off-network,
  no-path, empty-graph.
- **Test across representations, not just inputs.** Permute the input list; translate every
  coordinate; re-express a bidirectional edge as two opposed one-ways; subdivide every segment;
  scale every weight. These find what no fixture can: every geometry in my first domain was
  axis-aligned and near the origin, so *nothing* would have caught a coordinate dependence.
- **Keep every historical wrong implementation executable and assert something still catches it.**
  This is `feedback-benchmark-over-point-fixes`'s "verify the guard by reverting the fix", made
  automatic. It immediately found **three fixes with no guard at all**.
- **Expect the instrument to reject your invariants, and treat that as it working.** Mine rejected
  four, and each replacement was sharper: answers and provenance are invariant under *different*
  things; a total is **affine** in a weight scale, not proportional, because the connector does not
  scale; exact float equality across representations is a stronger claim than the arithmetic
  supports (2.0e-12 s on a translated curve).
- **Record non-invariants explicitly.** Objective 2 is not monotone; subdivision is not
  answer-preserving under a per-segment rule; the answer is not continuous in the geometry.
- **Two harness traps.** A patched module global cannot reach a binding another module imported *by
  name* — the mutant reads as caught by nobody. And a mutant is invisible until the domain contains
  an input that exercises the branch it breaks: the orientation defect needed a scenario whose
  *selected route* traverses a palindromic edge backwards.

**The payoff is a measured division of labour, not a replacement.** Five of eight mutants escape the
case corpus; two escape the invariants; every one is caught by the other. Uniform defects — a cap
tightened everywhere, a cost term missing everywhere — preserve every *relative* property, so only
an exact-boundary or exact-value case sees them. Pin the split so a drift in it is visible.

Related: [[feedback-benchmark-over-point-fixes]],
[[feedback-a-fixture-is-exact-only-where-you-point-it]], [[feedback-codex-adversarial-review]],
[[feedback-computable-property-is-not-the-claim]].
