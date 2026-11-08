---
name: feedback-a-fixture-is-exact-only-where-you-point-it
description: Four reviews defeated the same test suite by varying an axis the fixtures held constant; build the wrong implementation in the test file and name which case kills it
metadata: 
  node_type: memory
  type: feedback
  modified: 2026-11-06T13:40:56.544Z
  originSessionId: 3448970c-7f62-4034-83e7-b7d86efb0261
---

Learned 2026-11-05/06 on `v2/locfinder/measure/`, across Codex passes 15, 18 and 19. **Four
successive versions of one test suite were each defeated, and every time by the same move: vary an
axis the fixtures held constant.**

| pass | the wrong implementation | the axis the fixtures held constant |
|---|---|---|
| 15 | `k/n + (1−k/n)(1−0.05^(1/n))` | *k* — every fixture was a zero-event value |
| 18 | correct except at *k*=1, *n*=400 | the **tolerance** — 0.002 hid a decision-flipping 0.0019 |
| 18 | a two-sided *lower* bound | which **tail** — only endpoints and direction were checked |
| 19 | `c* = 0.95 + (c−0.95)/2` in both quantiles | **confidence** — all 65 exact fixtures used 0.95 and the non-default tests checked only direction |
| 19 | `order = np.arange(len(ids))` for the population sort | the **population** — every draw test was *handed* an already sorted one, so no test called the constructor |

Pass 19's is the most instructive: **one global wrong formula**, delivering the 92.5% bound for a
requested 90% and the 97% bound for a requested 99%, passing all 65 tests. Not an exception carved
out for one input.

**Why:** a fixture pins a point, not a function. Writing more fixtures along the axis you already
varied adds nothing. The defeat always comes from the parameter you fixed because it "obviously
doesn't matter" — the confidence level, the tolerance, the input the test supplies instead of builds.

**How to apply:**
- **Parametrise every exact fixture over every argument that changes the answer**, not just the one
  the bug was in. Three confidence levels cost nothing and closed pass 19's F3 permanently.
- **Build the wrong implementation in the test file and assert which case kills it.** Four are built
  in `test_conformance.py` and one in `test_stats.py`. Doing this found a defect in my own corpus:
  the one-way case had a *fast* return route, so an implementation ignoring the one-way flag took the
  illegal 60 s shortcut, lost to the legal 50 s route, and returned the **correct** answer. That case
  separated nothing. A rule is only testable where the illegal option would otherwise win.
- **Pin rejected answers as numbers, not prose.** A `rejects:` string is unchecked text; 16 numeric
  rejected values are assertions.
- **If the test supplies a value, nothing about producing that value is tested.** Mutating the
  producer is the check.
- **`pytest.approx(x, abs=1e-10)` keeps pytest's default *relative* tolerance** — about 8e-7 at an
  expected 0.8. Pass `rel=0, abs=...` when an absolute contract is meant, and do not claim 1e-10
  without it.
- **A declared tolerance is not an argument; make it provably decision-irrelevant.** For T4 every
  pinned time is checked to give the same verdict at ±tolerance at all four published thresholds, and
  a case whose value sits within a tolerance of a threshold is *refused* rather than admitted.

Related: [[feedback-benchmark-over-point-fixes]], [[feedback-codex-adversarial-review]],
[[feedback-computable-property-is-not-the-claim]],
[[feedback-a-predeclared-gate-must-be-shown-reachable]].
