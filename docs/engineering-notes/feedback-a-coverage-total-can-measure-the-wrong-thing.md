---
title: "A coverage total can measure the road network instead of the destination"
date: 2026-11-23
status: measured
---

# Three unrelated destination sets gave identical coverage, and the number was not wrong

While pricing owner ask 13(a) I compared building-weighted coverage across the layers and found
this in the project's own records:

| run | cells covered | buildings covered |
|---|---:|---:|
| `grocery / drive` (2026-11-16) | 80.5677% | 511,926 |
| `duke-hospital / drive` (2026-11-16) | 80.5677% | 511,926 |
| `rdu-airport / drive` (2026-11-16) | 80.5677% | 511,926 |
| `supermarket / drive` (2026-11-23) | 80.5677% | 511,926 |
| `grocery / drive` (2026-11-23) | 80.5677% | 511,926 |

553 grocery shops, 262 supermarkets, one hospital and one airport all score the same, to four
decimal places. The first reading is that something is broken, or that the surfaces are copies of
each other.

**They are not.** The two 2026-11-23 drive surfaces differ on 110,090 cells, where the supermarket
layer is slower by a median of 1.5 minutes and by up to 17.2. The surfaces are fine.

## What the total actually measures

The horizon is 7,200 s and the cutoff 120 minutes. By car, within two hours, every building that
can reach the road network at all reaches *any* destination in the metro. So the total stops being
a statement about destinations and becomes a statement about **road-network reachability**: 511,926
of 512,633 buildings can get onto the network, and the remaining 707 cannot, whatever you ask them
to drive to.

Identical totals are therefore the correct answer to a question nobody wanted asked.

## Where the difference is

At the thresholds a household actually sets:

| drive threshold | any grocery | supermarket | buildings that lose an answer |
|---|---:|---:|---:|
| 5 min | 393,466 | 359,680 | 33,786 |
| 10 min | 492,403 | 481,048 | 11,355 |
| 15 min | 507,576 | 503,237 | 4,339 |
| 20 min | 511,575 | 511,404 | 171 |
| 30 min | 511,924 | 511,924 | 0 |

The same comparison for walking costs 66,925 buildings at the layer's own 20-minute opening value.
So the cost of restricting the layer to weekly-shop supermarkets falls almost entirely on people
who walk, and by car it is close to free. That is the finding, and the totals row hides it
completely.

## The rule

**A saturated measure cannot compare anything.** Before reading a coverage figure as a comparison,
check whether the denominator is saturated at the horizon applied: if nearly everything is covered
whatever the destination, the figure is measuring access to the network and not proximity to the
destination.

Report the threshold rows. Report the total only to say what it is, which is the share that can
reach the network at all.

This is the same error in a new place as reading `footprint.REFUTED` as *no shop here* when it
means *not a supermarket*, and as reading a blank `date_closed` as a report that a shop is open: an
instrument answering a narrower question than the one being asked of it. The defence is the same
one -- say what the measure measures, in the sentence that quotes it.

## What it caught in this session

I first priced ask 13(a) off the *any answer at all* row for walking: 498,981 buildings against
492,149, a 1.3-point drop, and called it a cheap trade in a draft reply. At the 20-minute threshold
the layer opens on, the same change costs 66,925 buildings their answer -- 27% of those that have
one. Same two surfaces, same denominator, and a conclusion that reverses.
