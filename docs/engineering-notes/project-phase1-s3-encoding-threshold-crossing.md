---
name: project-phase1-s3-encoding-threshold-crossing
description: "DECIDED 2026-11-09: encode_minutes rounds up. rint did not shift the threshold, it destroyed the verdict - cells at 590 s and 610 s both encoded to 10, so 8.15% of what the browser showed as passing 10 minutes did not pass. ceil is exact over every threshold the UI can produce, costs 0.1% of a raster, and nothing displays the minute"
metadata:
  node_type: memory
  type: project
  originSessionId: 3448970c-7f62-4034-83e7-b7d86efb0261
  modified: 2026-11-09T00:00:00.000Z
---

Measured 2026-11-09 on the committed Triangle grocery/walk layer. Numbers and method in
`docs/experiments/s3-encoding.md`, reproducible with
`uv run python spikes/s3_encoding_threshold_crossing.py grocery walk`. Found because Codex pass 26
noticed three rows of the audit sheet ([[project-phase1-s3-step0-audit-harness]]) carrying a
float verdict of FAIL beside an encoded minute that reads as PASS. Pass 27 then corrected the
algebra below — the measured numbers were right, the inequality I wrote for them was not.

## The claim

`status.py` has said since S0 that evaluation "uses the float seconds, never the uint8 encoding, so
rounding cannot move a threshold" (Codex pass-3 H6). **That is true of the Python side and false of
the artifact S3.5 ships.** A browser holding only the encoded raster answers a different threshold,
and the arithmetic is one-sided:

```
rint(s/60) <= T   iff   s <= 60T + 30   for EVEN T        the shipped encoding
rint(s/60) <= T   iff   s <  60T + 30   for ODD  T
ceil(s/60) <= T   iff   s <= 60T                          evaluate's own comparison, for T < 254
floor(s/60) <= T  iff   s <  60(T + 1)
```

**The parity matters and an earlier version of this note missed it.** `np.rint` rounds halves to
*even*, so at exactly `s = 60T + 30` the encoded minute is `T` when `T` is even and `T + 1` when it
is odd: `s = 630, T = 10` passes (`rint(10.5) = 10`) where a blanket strict inequality says it does
not, and `s = 930, T = 15` fails (`rint(15.5) = 16`). Pass 27 found this. The measured numbers below
were computed from the encoded array itself and are unaffected.

**And `ceil` is exact only below 254 minutes, on finite OK cells.** `encode_minutes` clips at
`MAX_MINUTES = 254`, so `s = 18,000` (300 minutes) encodes to 254 and would pass a `T = 254`
threshold it fails by three quarters of an hour; NODATA must be masked explicitly rather than
compared. Neither matters at 10 or 15 minutes, which is where the product lives, but the claim has
to carry its domain.

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

At 10 minutes the same 2,151 cells are **0.84% of OK cells** and **0.65% of the whole grid** —
two different denominators, and an earlier version of this note called the first of them
"frame-wide", which it is not (pass 27).

**Re-measured 2026-11-10 on the rebuilt layer: 2,154 cells, 8.16%.** The figures in this note are
the ones the decision was taken against on 2026-11-09 and are left as they stand; the rebuild
(`ab01ffa`'s `symmetrise` fix, 7,246 cells) moves the ten-minute `rint` rate by one hundredth of a
percentage point. The `ceil` column cannot move at all: `ceil(s/60) <= T` **is** `s <= 60T`, which
is `evaluate`'s own comparison, so its zeros hold by construction on any layer rather than by luck
on this one. That is the property the decision rests on, and it is the reason a changed surface
does not reopen it.

**Pass 25's objection to E1b was exactly this shape**: `Pr(product PASS and comparator FAIL)` over a
whole frame can be ~1% while `Pr(wrong | displayed)` is ~10%, so a frame-wide number understates the
harm. It was offered as a hypothetical about the routing comparison and here it is as arithmetic
about the encoding — under 1% on either wide denominator, 8.15% of what a user is shown. The tighter
the threshold the worse it gets, and 10 minutes is the tightest the product offers.

**What this is not.** It is an **artifact-to-artifact comparison** — the encoded raster against the
float surface that produced it — not a measured error rate against the world. It says nothing about
routing or destination validity, and it does not complete plan step 2, which needs the conditional
computed against a comparator rather than against our own float array.

## `ceil` is exact, and that is a property not a result

`ceil(s/60) <= T` is equivalent to `s <= 60T`, which is `evaluate`'s own comparison, so for a
**finite `OK` cell at a whole-minute threshold below 254** the encoded verdict and the float verdict
are **identical** — zero wrong and zero missed by construction, not by luck on this layer. The
qualifiers are load-bearing: the clip at 254 breaks it above that, and `NODATA` is not a minute.

Its cost is the displayed *number*: the minute becomes an upper bound on our model's time,
overstating by **less than 60 s** (a 0.1 s walk displays as 1 minute, which is 59.9 s out, so "up to
59 s" was wrong), where `rint` is within 30 s either way. A journey under 30 seconds stops
displaying as `0`; exactly zero still displays as `0`. That direction is consistent with
every other conservatism here — `OFF_NETWORK` is unknown rather than excluded, a bounded engine
publishes `BEYOND_HORIZON` rather than `NO_PATH`, the access bound is deliberately kept weak so the
straight-line fiction cannot be used to exclude a household. A region that is exactly the region we
computed looks worth more than a number that is 30 s closer on average, but that is a product
judgement, not a measurement.

## Decided 2026-11-09: `ceil`

The owner took the decision after the exposition below. What was done:

- `grid.encode_minutes` rounds up; `ENCODING = "uint8-minutes-ceil-v1"` is a module constant.
- **`traveltime.layer.write_layer` stamps `encoding` itself**, not the caller, and
  `spikes/g3-render/export_layers.py` puts it in the browser manifest. This was the real risk of the
  change rather than the rounding: nothing anywhere carried an encoding version, so a `rint` raster
  and a `ceil` raster were byte-different and otherwise indistinguishable, and mixing them silently
  is the error class this stage exists to prevent. An artifact with no `encoding` tag is `rint`.
- All eight minute rasters were re-encoded from their stored float seconds by
  `v2/scripts/reencode_minute_rasters.py` — committed, because `v2/data/` is gitignored and the only
  other way to rebuild them was the 670 MB graph. Max shift 1 minute on every raster, as `ceil`
  against `rint` must be; 128,358 of the Triangle's 330,502 cells moved.
- The browser fixtures were re-exported, and the audit sheet reissued: `encoding_disagrees_min` is
  blank on all 19 rows, where 3 disagreed before. Each walked journey now tests one claim.

**Why it was clear-cut, once the consumers were read rather than assumed.** The encoded minute is a
decision input and not a display value: the worker thresholds it against an integer-minute slider
(`min="1" max="60" step="1"`) and **no per-cell number is displayed anywhere** — no hover, no popup,
no `queryRendered`. So the one cost of `ceil`, that the minute becomes an upper bound rather than the
nearest value, is a cost against a feature that does not exist. Measured over 207,000 values across
all 60 thresholds the slider can produce: `ceil` disagrees with the float verdict **0** times,
`rint` 101,199, `floor` 201,958. GeoTIFF size changed by −0.1%.

**The option held in reserve:** `ceil` at 30-second units — same `uint8` width, exact at whole *and*
half-minute thresholds, display error under 30 s, and the 120-minute horizon still fits (240 of
254) — but **+32% GeoTIFF, +35% gzip**, and every consumer must learn the unit changed. It becomes
the right answer the day a per-cell number is displayed.

## The reasoning as it stood before the decision

Changing `grid.encode_minutes` changes committed rasters and moves the boundaries of the legacy
minute codes 251–254, which are real answers in artifacts already on disk (pass-7 H1) — it does not
reinterpret them, which was that finding's actual concern. Whether the shipped client decides
eligibility from minutes or from seconds was listed as open at plan §0 step 6; reading the code
settled it, which is the part worth remembering. The answer was in
`spikes/g3-render/worker.js:139` the whole time.

**It is not a straw man: the browser path we have already built decides from minutes.**
`v2/spikes/g3-render/worker.js:139` reads the minute byte and does `if (v > T[k]) inside = 0`, so the
rendered region is exactly the 30-s-inflated one. The same loop does `if (v === nodata) inside = 0`,
which means the shipped render also **collapses UNKNOWN into EXCLUDED** — `NODATA` is a single code
for `OFF_NETWORK` and `BEYOND_HORIZON` alike, so the three-outcome algebra that S0 built the whole
`Reason` enum for does not survive the export. That is a second, separate step-6 finding and it is
not fixed by changing the rounding.

So the decision is owner-and-step-6's. What is done now: the measurement is recorded and
reproducible, and `scripts/audit_recommendations.py` emits an `encoding_disagrees_min` column naming
the thresholds where the two verdicts differ for each journey, so a walked result is attributed to
the verdict it actually tested instead of to whichever one the reader assumes. Three of the 19
journeys are affected — 627.0 s and 610.9 s both encode to 10 minutes, and 923.8 s encodes to 15.

**The cheap move, and minutes *are* the decision input today:** switch to `ceil`, since there is
no threshold below 254 at which `rint` is safer. It is inexpensive rather than free — the uint8 and
GeoTIFF formats are unchanged and codes 251-254 remain minutes, but their boundaries move, so
artifacts and any pinned expectations need regenerating and versioning, and the clip at 254 needs an
explicit overflow policy. The inspected renderer uses fixed mask colours, so there is no colour-ramp
incompatibility. None of it settles the UNKNOWN-collapse above, which is the larger of the two.
