---
name: project-phase1-s3-encoding-threshold-crossing
description: "Rounding seconds to whole minutes moves every threshold 30 s more permissive, in one direction only - 8.15% of the cells a minute-only client shows as passing 10 minutes do not pass, and ceil instead of rint makes the encoded verdict exactly the float verdict"
metadata:
  node_type: memory
  type: project
  originSessionId: 3448970c-7f62-4034-83e7-b7d86efb0261
  modified: 2026-11-09T00:00:00.000Z
---

Measured 2026-11-09 on the committed Triangle grocery/walk layer. Numbers and method in
`docs/experiments/s3-encoding.md`, reproducible with
`uv run python spikes/s3_encoding_threshold_crossing.py grocery walk`. Found because Codex pass 26
noticed three rows of the 21-journey audit sheet ([[project-phase1-s3-step0-audit-harness]]) carrying
a float verdict of FAIL beside an encoded minute that reads as PASS.

## The claim

`status.py` has said since S0 that evaluation "uses the float seconds, never the uint8 encoding, so
rounding cannot move a threshold" (Codex pass-3 H6). **That is true of the Python side and false of
the artifact S3.5 ships.** A browser holding only the encoded raster answers a different threshold,
and the arithmetic is one-sided:

```
rint(s/60) <= T   <=>   s < 60T + 30      the shipped encoding: 30 s more permissive
ceil(s/60) <= T   <=>   s <= 60T          exactly the float verdict
floor(s/60) <= T  <=>   s < 60(T + 1)     60 s more permissive
```

A value at or below `60T` cannot round to more than `T` minutes, so a minute-only client can only be
**too generous** — it shows cells as passing that do not pass and can never hide a cell that does.
`missed` is 0 in all twelve measured rows, which is the structural claim confirmed rather than a
property of this layer.

## The size of it

`Pr(not actually a pass | displayed as a pass)`, cells then buildings:

| T | rint (shipped) | ceil | floor |
|---|---|---|---|
| 10 min | **8.15%** / 9.04% | 0 | 15.05% / 16.36% |
| 15 min | **5.14%** / 5.04% | 0 | 9.63% / 9.37% |
| 25 min | 2.19% / 1.75% | 0 | 4.15% / 3.22% |
| 45 min | 0.87% / 0.44% | 0 | 1.72% / 0.86% |

The frame-wide rate at 10 minutes is 0.84% of OK cells. **Pass 25's objection to E1b was exactly
this**: that `Pr(product PASS and comparator FAIL)` over the whole frame can be ~1% while
`Pr(wrong | displayed)` is ~10%, so the frame-wide number understates the harm. It was offered as a
hypothetical about the routing comparison and turns out to be measured fact about the encoding —
0.84% over the frame, 8.15% of what a user is shown. The tighter the threshold, the worse it gets,
and 10 minutes is the tightest one the product offers.

## `ceil` is exact, and that is a property not a result

`ceil(s/60) <= T` is equivalent to `s <= 60T`, which is `evaluate`'s own comparison, so the encoded
verdict and the float verdict are **identical at every whole-minute threshold** — zero wrong and
zero missed by construction, not by luck on this layer.

Its cost is the displayed *number*: the minute becomes an upper bound on our model's time,
overstating by up to 59 s, where `rint` is within 30 s either way. That direction is consistent with
every other conservatism here — `OFF_NETWORK` is unknown rather than excluded, a bounded engine
publishes `BEYOND_HORIZON` rather than `NO_PATH`, the access bound is deliberately kept weak so the
straight-line fiction cannot be used to exclude a household. A region that is exactly the region we
computed looks worth more than a number that is 30 s closer on average, but that is a product
judgement, not a measurement.

## Not decided, and why it is not mine to decide

Changing `grid.encode_minutes` changes committed rasters and interacts with the legacy minute codes
251–254, which are real answers in artifacts already on disk (pass-7 H1). And **whether the shipped
client decides eligibility from minutes or from seconds has never been settled** — it is plan §0
step 6 (S3.5, the browser path end to end, "whole-minute edges" explicitly listed). If the client
decides from float seconds the encoding is display-only and none of this is an error; if it decides
from minutes, every published region is inflated.

So the decision is owner-and-step-6's. What is done now: the measurement is recorded and
reproducible, and `scripts/audit_recommendations.py` emits an `encoding_disagrees_min` column naming
the thresholds where the two verdicts differ for each journey, so a walked result is attributed to
the verdict it actually tested instead of to whichever one the reader assumes. Three of the first 21
journeys are affected — 627.0 s and 610.9 s both encode to 10 minutes, and 923.8 s encodes to 15.

**The cheap move if minutes are the decision input:** switch to `ceil` and keep `rint` nowhere, since
there is no threshold at which `rint` is safer. The expensive part is not the code, it is rebuilding
and re-verifying the artifacts.
