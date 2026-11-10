# A walked journey was half the real distance, because the route used an unmapped track

**2026-11-10.** The first finding produced by the walked audit, and it came from the owner, not
from the instrument.

## What the owner reported

> "some of the longer walks are projected to be a bit faster than in reality: e.g.
> band15min_pass-03 is closer to 25 mins of walking (1.3 miles with a few intersections; check to
> see if the location snapped to dogwood dr or to edwards st or merrit mill rd, the latter two of
> which would give artificially short travel times)"

Published: **810.8 s** = 13.5 min. Observed: **~25 min, 1.3 miles**.

## The arithmetic ruled out the obvious explanation first

Our walk speed is **1.40 m/s** and the route is computed at exactly that on the network, so the
speed model is not the error. 810.8 s at 1.40 m/s is **1,135 m**; 1.3 miles is **2,092 m**. The
route was roughly **half the real distance**, which is a graph problem rather than a speed problem.

## What it actually snapped to

Neither Dogwood Dr nor Edwards St nor Merritt Mill Rd. It snapped to an **unnamed OSM `track`**,
[way 1254722642](https://www.openstreetmap.org/way/1254722642), 35.5 m from the cell centre. Then:

| | length | class | name |
|---|---|---|---|
| 1 | 50.2 m | `track` | way 1254722642 |
| 2 | 17.7 m | `track` | way 1254722641 |
| 3 | 91.6 m | `track` | way 1254722641 |
| 4 | 138.4 m | `path` | way 1343881800 |
| 5 | 77.1 m | `residential` | Raintree Lane |
| 6 | 25.2 m | `residential` | Locust Court |
| 7-25 | 573 m | `tertiary` | South Merritt Mill Road |

So the owner's instinct about Merritt Mill Road was half right: the route does run down it for most
of its length, and that part is real. **The artificial part is the 298 m of `track` and `path` that
gets there**, which is what the cell's whole PASS rests on.

Every one of the **14 edges within 120 m** of the cell centre is a track, path, footway or service
way. Distance to the nearest edge of each class:

| class | distance |
|---|---|
| `track` | 35.5 m |
| `footway` | 46.0 m |
| `service` | 57.4 m |
| `path` | 70.4 m |
| `residential` | **142.8 m** |
| `tertiary` | **287.5 m** |

## The counterfactual, which is what the walk is evidence about

Rebuilt with `track` removed, band15min_pass-03 is **1,787 s = 29.8 min**, against 810.8 s
published. The owner's 25 min sits between the two. Removing `path` as well changes nothing further
for this cell.

The verdict flips: 810.8 s passes 15 minutes; 1,787 s fails 15 **and** 25.

That the observation lands between the two bounds is the expected shape — some of those ways are
presumably usable and some are not, so neither "trust every track" nor "delete every track" is the
right model. The useful conclusion is that **this cell's PASS is decided entirely by ways whose
existence on the ground is unverified**.

## Prevalence, so one row does not become a policy

`v2/scripts/measure_soft_way_dependence.py`, full surface, buildings from
`own_triangle_buildings_per_cell.npy`. Baseline is current code.

| *T* | PASS cells | lost without `track` | lost without `track`+`path` | PASS buildings | buildings lost | share |
|---|---|---|---|---|---|---|
| 10 | 24,255 | 19 | 104 | 80,067 | 207 | **0.26%** |
| 15 | 47,509 | 110 | 414 | 163,875 | 644 | **0.39%** |
| 25 | 93,575 | 520 | 1,323 | 298,716 | 1,224 | **0.41%** |
| 45 | 161,670 | 2,524 | 4,239 | 424,886 | 2,389 | **0.56%** |

Removing both classes drops 14,641 edges and takes UNKNOWN cells from 73,750 to 83,760 — 10,010
cells whose only network access was a soft way.

**So the building-weighted exposure is 0.26%-0.56%, and the sheet hit it 3 times in 16.** That is
not a contradiction. The band strata deliberately sample within ±90 s of a threshold, and a cell
loses its PASS only if the soft way saves enough time to cross that threshold — so cells near the
threshold need the least saving and are the most sensitive. The strata are *enriched* for this
failure mode by construction, which is what they are for.

## The decision this leaves open, which is the owner's

1. **Keep them and disclose.** 0.39% of 15-minute PASS buildings is small, and some tracks are
   genuinely walkable.
2. **Exclude them.** Costs 414 PASS cells at 15 minutes and moves 10,010 cells into UNKNOWN.
   Honest about what is verified; converts some true passes into unknowns.
3. **Penalise rather than exclude** — the mechanism `access.py` already uses for restricted edges:
   cost extra to choose, report real time. A track would then lose to any paved alternative but
   still be used where it is the only route. This is the option the existing two-weight machinery
   was built for and the one worth measuring next.

Option 3 cannot be chosen from this note: nothing here measures how often a *penalised* track still
wins, and I should not infer that from the exclusion numbers.

## What this says about the estimands

E1 and E2 cannot see any of it. Both sides read the same road graph, so a route down an impassable
track is agreement, not error — the same structural blind spot as a closed grocery, which is why
[[project-phase1-s3-step2-conditional-estimand]] records destination validity as E1c's declared
blind spot. **One walked journey found what eleven adversarial passes on the instrument could
not.** Plan §0 ranks the walked audit first by risk retired; this is the first evidence that the
ranking was right.

## Tools

- `v2/scripts/explain_journey.py <sheet> <journey_id>` — every edge near the cell, what was
  snapped, the route segment by segment with names and lengths, and the implied speed.
- `v2/scripts/diagnose_track_dependence.py <sheet>` — the two counterfactuals across a whole sheet.
- `v2/scripts/measure_soft_way_dependence.py` — the full-surface prevalence table above, written to
  `v2/data/soft_way_dependence_grocery_walk.json`.

Related: [[project-phase1-s3-audit-destination-recovery]],
[[project-phase1-s3-step0-audit-harness]], [[project-phase1-s3-stale-walk-raster]].
