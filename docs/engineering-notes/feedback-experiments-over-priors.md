---
name: feedback-experiments-over-priors
description: "When a design or architecture question is open, the user wants it settled by a cheap experiment first, then the research record, and only last by our priors"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 3448970c-7f62-4034-83e7-b7d86efb0261
  modified: 2026-11-03T18:01:20.199Z
---

Stated 2026-11-03 when asked which routing engine to build on first: "trust in
this order: experimental results, the research, our priors."

**Why:** The user is an empirical scientist; they would rather spend a day on a
spike with explicit pass criteria than argue from documents or intuition, and
they consider the complex cases (e.g. transit) worth attacking early because
they teach the most.

**How to apply:** Frame open questions as gates with measurable criteria and run
them before committing architecture. Do not pre-decide between viable options in
a plan; build the small slice both ways if the cost is low. When reporting,
separate measured results from research-derived claims from assumptions.
Related: [[project-v2-rethink-decisions]], [[feedback-autonomous-work-style]].
