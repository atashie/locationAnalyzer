# Donut holes: a parcel ruled out while every neighbour around it is included

**2026-11-16.** The owner, looking at the seven-criterion page, reported parcels that stay out of
region while the ring around them is in it, and guessed the cause: *"punishing locations for
proximity to a node along a route … I wonder if we need to add artificial nodes along long
straight routes."*

The shape is real. The mechanism is not the one guessed, and the proposed fix would not change
anything. What it is instead is worse, in the sense of being harder to fix.

## The shape, counted

A hole is defined narrowly so it cannot be produced by a threshold gradient: **an EXCLUDED cell
whose eight neighbours are all INCLUDED.**

| layer | limit | in region | holes | hole slower than its ring by |
|---|---|---|---|---|
| park / walk | 10 min | 31,748 | 80 | median 210 s, max 357 s |
| park / walk | 15 min | 59,116 | 123 | median 228 s, max 503 s |
| park / walk | 20 min | 85,838 | **125** | median 241 s, max 753 s |
| park / walk | 30 min | 129,335 | 80 | median 270 s, max 1,128 s |
| grocery / walk | 20 min | 71,925 | 113 | median 241 s, max 1,577 s |
| school / walk | 20 min | 76,077 | 132 | median 233 s, max 1,641 s |
| grocery / drive | 5 min | 134,601 | 367 | median 63 s, max 330 s |

**Every hole has status OK.** These are computed times, not off-network artefacts. A 100 m step
cannot change a real walk by four minutes, so the discontinuity is the model's, not the ground's.

**They are not empty land.** At park / walk 20 min the 125 holes hold **414 buildings**, and 75 of
the 125 contain at least one. That is 0.08% of all buildings — small in aggregate, and a wrong
answer about somebody's actual house.

## The mechanism, measured

`snap._snap_network` calls `idx.tree.nearest(pts)`. **It considers exactly one edge per cell**, the
geometrically nearest, and the cell inherits that edge's connectivity whatever it is. Decomposing
the three largest holes at park / walk 20 min into access leg, on-edge walk and arrival at the
chosen endpoint:

```
 cell   total   access  onedge   atnode   matched way
 HOLE   24.3m    15.3m    341s    18.4m   (unnamed) [footway] way 554959940
 +1-1    6.8m     1.1m      7s     6.7m   (unnamed) [service] way 53894209

 HOLE   21.0m     5.9m     27s    20.5m   (unnamed) [service] way 461005440/461005460
 +0+1    4.7m    33.3m     42s     3.6m   Atlantic Avenue [secondary] way 746439842

 HOLE   20.6m    28.7m     71s    19.0m   (unnamed) [service] way 692276389
 +0-1    3.5m    13.9m     23s     2.9m   Old Poole Road [tertiary] way 18894454
```

**The gap is in `atnode` and nowhere else.** The access leg and the on-edge walk are small and
comparable between a hole and its neighbours. The hole snapped to an edge whose best endpoint is
twelve to seventeen minutes away; a neighbour 100 m off snapped to a road whose endpoint is three
to seven minutes away.

One case traced to OSM directly. Hole two's matched edge is `service=parking_aisle` — a lane inside
a car park — and it **shares no node with Atlantic Avenue, the secondary road 33 m away**. The
model walks that parcel out of the car park the long way round.

## Why the owner's two guesses do not apply

**"Punished to make its way to the nearest node."** It is not. The rule is
`time_end = (1 - frac) * fwd_t + T_e`: a cell at the midpoint of an edge pays exactly half that
edge's travel time to reach its end. The on-edge walk is **strictly proportional**, which is what a
walker actually does when the road is the only way out.

**"Add artificial nodes along long straight routes."** Subdividing an edge does not change
shortest-path distances — it adds nodes on a path that already existed, at the same total cost. And
on the access side the model already behaves as though a node sat at the perpendicular foot of the
cell, because of the proration above. **Adding nodes would change nothing here.**

*(Nodes do matter in one place: a POI snaps to the nearest NODE, not the nearest edge, within
300 m. Measured for parks: median 27 m, p90 79 m, max 292 m. Real, worth fixing eventually, and
not what makes the holes.)*

## The obvious fix, priced and not recommended as it stands

Take the best edge within the existing 200 m access cap instead of the nearest one. Measured on
park / walk over all 330,502 cells:

| alternatives allowed within | cells improved >1 s | median gain | p99 gain | holes at 20 min |
|---|---|---|---|---|
| *today — nearest edge only* | — | — | — | **125** |
| +10 m of the nearest | 46,587 | 11 s | 749 s | 120 |
| +25 m of the nearest | 91,165 | 15 s | 860 s | 115 |
| +50 m of the nearest | 140,374 | 20 s | 959 s | 96 |
| anything within 100 m | 130,275 | 20 s | 705 s | 95 |
| anything within 200 m | 210,533 | 46 s | 1,312 s | **30** |

Considering more candidates can only lower a time, and the check that no cell got slower passes on
all 330,502 — so this is one-sided by construction.

**The reason not to take it as it stands is the access leg it needs.** For the 90,040 cells that
improve by more than 60 s under the 200 m rule:

- access leg today, to the nearest edge: median **38 m**, p90 107 m
- access leg to the winning edge: median **169 m**, p90 196 m, max 200 m
- winners within 50 m: **1.0%**. Within 100 m: 8.8%.

So the improvement is almost entirely bought by walking a straight line of about 170 m across
whatever lies between the parcel and a better road. Today a long straight access leg is at worst a
field between a house and its own road; this would make it a routine shortcut to a road the
household may have no way of reaching. It trades a visible over-exclusion for an invisible
over-inclusion, and this project's surfaces have been built to give **false exclusions, never
false inclusions**.

**And the cheap version does not work.** Restricting alternatives to edges nearly as close as the
nearest one — the version that keeps the access leg honest — removes 23% of the holes at best.
The holes genuinely are closest to a badly connected edge by a wide margin.

## No single bad tag explains it

Matched-edge class for the 125 holes against 20,000 random cells:

| class | share of holes | baseline | enrichment |
|---|---|---|---|
| `residential` | 35.2% | 26.90% | 1.3x |
| `footway` | 16.8% | 9.40% | 1.8x |
| `service` | 13.6% | 14.85% | 0.9x |
| `service=parking_aisle` | 10.4% | 3.67% | **2.8x** |
| `service=driveway` | 8.0% | 20.43% | 0.4x |

Parking aisles are the most enriched and are only a tenth of the holes; the largest single share is
ordinary residential road. **Excluding a tag class would not fix this.**

## What is not established

**Whether the long times are wrong.** For the parking-aisle case they plainly are — a person walks
33 m to Atlantic Avenue. For a cul-de-sac whose entrance really is a mile round, the long time is
correct and the hole is the right answer. Nothing here distinguishes the two, and the structural
signal — a cell whose nearest edge's endpoint is far worse than an alternative inside the access
cap — flags about 90,000 cells, most of which will not be defects.

This is the same shape as the walked journey: the model says something surprising, and the ground
settles it. It is cheaper to settle here, because a hole is a named parcel with a named road beside
it and the question "can you walk from here to that road" is answerable by looking.

## Options, none taken

1. **Leave it and disclose.** 0.08% of buildings per layer, and the shape is conspicuous enough
   that a reader will ask. Cheapest, and the disclosure has to be written.
2. **Multi-candidate snapping at the full cap.** Fixes 76% of holes; makes 77% of cells faster by a
   median 46 s; needs the 169 m straight-line access leg above. Not recommended alone.
3. **Multi-candidate snapping with a routed access leg** — candidates scored by a real path rather
   than a straight line. This is what mainstream routers do, it is the principled version of 2, and
   it is a substantially larger piece of work.
4. **Check the connectivity hypothesis.** The one hole traced by hand was an OSM noding gap. If a
   sample of holes shows the same, part of this is a data problem with a data fix, and it can be
   contributed back — subject to Decision 17.

Related: [[project-phase1-s3-criteria-build]], [[s3-13-reading-test]],
[[project-phase1-s3-soft-way-dependence]].
