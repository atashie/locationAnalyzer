---
name: feedback-match-statistical-machinery-to-the-design
description: "Clustering corrections belong to clustered sampling designs, not to spatially correlated populations sampled independently; check an adjustment's assumptions against how the sample is actually drawn"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 3448970c-7f62-4034-83e7-b7d86efb0261
  modified: 2026-11-05T03:31:06.316Z
---

Learned 2026-11-04, Codex pass 15. I built a whole subsystem — a design effect, a fixed 2 km block
grid, a ≥5-points-per-block pooling rule, a block bootstrap — on the reasoning that *"points near
each other share a road network, a snapping geometry and a nearest destination, so observations are
not independent."*

That reasoning is wrong, and the one-line correction is worth keeping verbatim:

> "For the declared finite-population SRS, spatially adjacent outcomes do not by themselves turn
> the sample into a cluster sample."

**Clustering inflates variance when the *design* clusters** — when you sample blocks and then take
every point inside them. For an SRS of points from a finite frame the variance of the estimated
proportion is `p(1-p)/n * (1 - n/N)` **however correlated the underlying ground is.** Correlation in
the *population* is not correlation in the *estimator*.

Two further things fell out once the assumption was checked:

- Dividing *n* by an estimated DEFF **destroys Clopper–Pearson's coverage guarantee**. It is an
  inversion of the binomial model, not a generic variance adjustment, so "exact bound on n/DEFF" is
  a contradiction. Conservative in the right direction, but never *exact*.
- The machinery was also **unusable**: at *n* = 400, frame B reached 2.8 blocks with ≥5 points and
  frame C 0.1; 893 of 1,000 seeded draws had no qualifying block at all. I found that by simulating
  it. **If I had simulated it when I designed it, I would have questioned the whole apparatus a
  revision earlier.**

**How to apply:**
- Before adopting a correction, name the design feature it corrects for and check the sample is
  actually drawn that way. "Observations feel dependent" is not a design feature.
- **Simulate the estimator on the real population at the predeclared n before predeclaring it.** The
  cheap decisive experiment again — see [[feedback-experiments-over-priors]].
- If a superpopulation or model-based claim is what is really wanted ("the rate at which a pipeline
  of this kind errs" rather than the rate over these 512,633 structures), that needs a stated and
  validated spatial model, not an effective-sample-size fudge. Decide which claim is being made.
- Removing machinery is a legitimate and often correct repair. Dropping DEFF made the acceptance
  gate reachable, deleted a whole plan task, and removed an entire class of unspecified detail.

Related: [[feedback-a-predeclared-gate-must-be-shown-reachable]],
[[feedback-experiments-over-priors]], [[feedback-codex-adversarial-review]].
