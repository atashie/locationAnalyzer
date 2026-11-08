---
name: feedback-computable-property-is-not-the-claim
description: "When a measurement is hard, the pull is to report the computable property as if it were the product claim; name the gap in the artifact itself"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 3448970c-7f62-4034-83e7-b7d86efb0261
  modified: 2026-11-04T22:30:00.000Z
---

Learned 2026-11-04 on the S2.3 access audit, across Codex passes 13 and 14. **The same claim was
withdrawn twice on one question.**

1. First version: counted restricted edges by *position* in a path and called 26,395 of them
   "unlawful routes". Pass 13: edge position cannot decide lawfulness — splitting a driveway into
   two OSM ways flips the verdict without changing the journey.
2. Rebuilt properly as a language `R* O* R*` on a graph x automaton product, and claimed membership
   means "not through-traffic over private land". Pass 14: still false — an origin in estate A and a
   destination in estate C joined by a continuous restricted road through *unrelated* estate B is
   `RRR` and is **accepted**. The automaton sees edge classes; it cannot see whose access chain an
   edge belongs to.

**Why:** the honest statement ("N nodes have no journey in this edge-class language") is not a
product claim, and the product claim ("this route is lawful") is not computable from the data. Each
time, the fix made the *computation* better and left the **inference** untouched — so a better
measurement produced the same overreach in more convincing language.

**How to apply:**
- State what a measurement decides **in the artifact that computes it**, not only in the write-up.
  `policy.py`'s docstring now says it decides language membership and nothing else.
- When tempted to add the inference, look for the counterexample that separates the computable
  property from the claim. For `R* O* R*` it took 30 seconds to find once I was looking for it.
- Check whether the obvious repair works before proposing it. "Require a non-empty open middle"
  sounds like the fix and would reject a resident walking across their own estate.
- The same trap at one level down: a **nearest-node proxy is not building service**. Assigning a
  building to its nearest node assumes a zero-time, unrestricted, traversable connector, and the
  connector's time was not even added — a node at 7,190 s with a 100 m connector counted inside a
  7,200 s horizon (pass-14 H2). Label proxies as proxies in the table, not in a footnote.

Related: [[feedback-benchmark-over-point-fixes]], [[project-h2-upper-bound-trap]],
[[feedback-experiments-over-priors]].
