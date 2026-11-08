---
name: project-h2-upper-bound-trap
description: "The shipped travel-time surface is cost-selected, so it is never a valid baseline for a counterfactual that minimises time"
metadata:
  node_type: memory
  type: project
  originSessionId: 3448970c-7f62-4034-83e7-b7d86efb0261
  modified: 2026-11-04T21:30:00.000Z
---

Learned 2026-11-04 building the S2.3 access-policy audit, caught by a soundness assertion before it
became a published number.

`arrival_seconds_two_weight` reports the travel time along the **cost**-optimal path, so it is an
**upper bound** on `min_d t(cell -> d)` and not that minimum (Codex pass-8 H2). Therefore **any
counterfactual that minimises time and is compared against the shipped surface is confounded by
that bound.** Measuring a policy that way made **26,376 nodes look faster WITH the policy than
without it** — impossible, since the policy's journeys are a subset.

**How to apply:** compare like with like. `locfinder/traveltime/policy.py` has
`unrestricted_arrival` (a plain time minimum over both access classes) for exactly this, and
`min_time` to build it — note `sp.csr_matrix.minimum` is unusable because it treats a missing entry
as a stored zero and zero wins a minimum. Report the shipped surface *beside* a counterfactual as
what the product says, never as the baseline.

Also worth keeping: an invariant that *can* fail ("the restricted subset is never faster") earned
its place here. The confound was invisible in the numbers and obvious to the assertion.

Related: [[project-phase1-s0-complete]], [[project-phase1-s2-progress]].
