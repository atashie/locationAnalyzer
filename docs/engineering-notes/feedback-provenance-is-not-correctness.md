---
name: feedback-provenance-is-not-correctness
description: "A figure can carry a perfect provenance label and still be arithmetically wrong - labelling discipline feels like verification and is not, so assert the values themselves"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 7b2884de-c576-4048-9933-aa7a65c6a0cf
  modified: 2026-11-06T23:15:44.078Z
---

Learned 2026-11-06 building `planning-route-stops`. Two adversarial Codex passes over the
skill's own tooling returned **20 findings. Twelve had already shipped to a published page
as confident statements** — and every one of them carried a *correct* provenance label. They
were measured, by one instrument, free-flow, labelled "measured". And wrong.

- A venue whose hours nobody published rolled up as `nothing-open`, so the page printed
  "nothing here is open when you arrive" — a flat falsehood about the world, derived from
  an absence of data.
- "The corridors are **185 miles** apart" became **223** if you reordered the option list:
  the separation function took one direction of an asymmetric measure.
- The direct drive, quoted as 8h41 in every draft, was **8h42** — every duration helper
  truncated seconds instead of rounding, and a small negative rendered as `-1h59`.
- Two **17-mile stretches of I-75** vanished from the map because the filter used vertex
  count as a proxy for importance, and a straight road simplifies to two points.

**Why:** provenance and correctness are orthogonal, and only one of them had a rule. I had
built careful machinery for *where a fact came from* and *how sure I was* — and that
machinery feels like rigour, which is exactly why the arithmetic underneath went unexamined
for four rounds of review. It is the same displacement as
[[feedback-a-skill-can-subtract]]: the discipline I had redirected attention away from the
discipline I lacked.

**How to apply:**

- Treat a figure you computed as a claim needing evidence, not as a given. Ask of every
  published number: *what assertion stands behind this?*
- The cheap checks that found all of it: round-trip anything you decode; assert landmarks
  and bounds on anything projected; swap the arguments of anything that should be
  symmetric; test rounding at ±30 s, exactly an hour, and a small negative; feed the
  degenerate case (zero tolerance, a two-point line, a venue open past midnight, a stop
  with no hours); re-derive one published figure by hand; grep the generator for literals,
  because prose is not covered by a data pipeline.
- **An absence of data is not a negative finding.** Unknown hours are not "closed", an
  unpriced ticket is not "free". Every collapse of unknown into a definite claim here
  produced a confident falsehood.
- **Never filter on a proxy for the property you mean.** Vertex count is not road
  importance; filter on visible length.
- The remedy that stuck is the same shape as [[feedback-benchmark-over-point-fixes]]: a
  no-network `selftest.py` where **every case is a defect that shipped**, 31 of them, run in
  a second. A fix without a failing test beside it is a fix that comes back.
- Worth a **second** Codex pass aimed only at the fixes — surgery on live logic (interval
  arithmetic, clipping, stitching) is where regressions hide. See
  [[feedback-codex-adversarial-review]].
