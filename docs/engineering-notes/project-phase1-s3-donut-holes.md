# Donut holes: a parcel ruled out while every neighbour around it is included

**2026-11-16.** The owner, looking at the seven-criterion page, reported parcels that stay out of
region while the ring around them is in it, and guessed the cause: *"punishing locations for
proximity to a node along a route … I wonder if we need to add artificial nodes along long
straight routes."*

The shape is real. The mechanism is not the one guessed. **The claim that the proposed fix
"would not change anything" was wrong, and two independent reviewers refuted it** — see below.

**Reviewed 2026-11-16 by Codex (`gpt-6.1-sol`) and Antigravity/Gemini (`gemini-4-hydrogen-xhigh`),
independently, because the owner was sceptical of these findings and said so.** Twenty claims:
Gemini's tally is 11 CONFIRMED, 7 OVERSTATED, 2 WRONG. The headline findings survived — the holes
are real, they hold buildings, and single-nearest-edge snapping is the mechanism. Several of my
reasons and some of my precision did not. Every correction below is marked, and the reviews are at
`docs/research/57-review-pass56/`.

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

**Every hole in the WALK layers has status OK** — computed times, not off-network artefacts. A
100 m step cannot change a real walk by four minutes, so the discontinuity is the model's, not the
ground's.

> **Corrected: the unqualified "every hole" was wrong, and my own table above contradicts it.**
> `grocery/drive` at 5 minutes has **353 OK holes and 14 `NO_PATH`** ones; at 10 and 15 minutes,
> 15 `NO_PATH` each. The script printed `{0: 353, 3: 14}` and I wrote the sentence anyway. Both
> reviewers caught it.

> **The counts above are on the UTM surface. The browser paints the reprojected WGS84 grid, and
> there the same measurement gives 121 / 109 / 121** for park, grocery and school at 20 minutes,
> against 125 / 113 / 132. The published grid holds **356 buildings across 76 of 121 holes**, not
> 414 across 75 of 125. When this is quoted at the picture the owner is looking at, the published
> figures are the ones that describe it.

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

**`atnode` is the dominant term.** The hole snapped to an edge whose best endpoint is twelve to
seventeen minutes away; a neighbour 100 m off snapped to a road whose endpoint is three to seven
minutes away.

> **Corrected: "and nowhere else" was wrong, against this note's own table.** In hole one the
> on-edge difference alone is 341 - 7 = **334 s**, about **32%** of that pair's 1,050 s gap.
> Measured across all 125 holes, the ratio of the `atnode` gap to the total gap has a **median of
> 1.05** and a range from -3.00 to 2.62, so `atnode` dominates typically and not uniformly.
> "Dominant" is the claim the measurement supports; "exclusive" is not.

One case traced to OSM directly. Hole two's matched edge is `service=parking_aisle` — a lane
inside a car park — and it **shares no node with Atlantic Avenue**, confirmed from the raw
`triangle-roads.osm` by both reviewers and by re-deriving the geometry here.

> **Corrected: I said Atlantic Avenue was "33 m away". From the hole it is 105.94 m.** The
> 33.28 m is the **east neighbour's** access leg — I read it off the neighbour row of my own table
> and attributed it to the hole. Reproduced to the centimetre by both reviewers and by me:
>
> | from | to Atlantic Ave | to parking way 461005460 |
> |---|---|---|
> | hole (365,539) | **105.94 m** | 5.86 m |
> | east neighbour (365,540) | **33.28 m** | 89.86 m |
>
> The sentence "a person walks 33 m to Atlantic Avenue" was not established for this hole and is
> withdrawn. What survives, and is arguably stronger: Gemini found **connected `track` edges at
> 31.4 m and 40.0 m from the hole whose endpoints are 7.0 and 6.3 minutes from a park**, against
> the 20.5 minutes the model used. A much better way in exists well within the access cap; the
> model never looks at it. That is the finding, and it does not depend on Atlantic Avenue.

## Why the owner's two guesses do not apply

**"Punished to make its way to the nearest node."** It is not. The rule is
`time_end = (1 - frac) * fwd_t + T_e`: a cell at the midpoint of an edge pays exactly half that
edge's travel time to reach its end. The on-edge walk is **strictly proportional**, which is what a
walker actually does when the road is the only way out.

**"Add artificial nodes along long straight routes."** I wrote that this **would change
nothing**, because subdividing an edge does not change shortest-path distances. **That is wrong
for this pipeline, and both reviewers refuted it — Codex by construction, Gemini on the real
graph.**

`speeds.py:133` sets `cost = travel_time + access_penalty_s(data, mode)`, and that penalty is a
**flat 120 s charged per edge**. Split a restricted edge and you charge it twice. Reproduced here
through the production `add_travel_times`:

| | private route | detour | selected | reported |
|---|---|---|---|---|
| one 140 m `access=private` edge | t=100 s, cost=100+120=**220** | 250 | private | **100 s** |
| the same edge split at its midpoint | t=100 s, cost=2x(50+120)=**340** | 250 | detour | **250 s** |

Gemini then ran it on the real Triangle walk graph. Splitting the **302,067 edges longer than
100 m** moves **4,915 OK cells** (max 2,068.9 s, 133 reachability changes) with destinations held
fixed; re-snapping destinations as well moves **74,930 OK cells** (max 2,893.2 s). **And the holes
get worse, not better: 125 -> 131 with fixed destinations, 134 with re-snapped ones.**

So the owner's suggestion changes a great deal. It is not a fix for this, and the reason I gave
for dismissing it was not a reason.

**One thing it would genuinely fix.** A POI snaps to the nearest **node**, not the nearest edge,
within 300 m — median 27 m for parks, p90 79 m, max 292 m. Gemini found that subdividing recovers
**6 of the 7 parks currently dropped** for being beyond that bound, including one that **sits
0.2 m from an edge and 356.4 m from any node**. A park right beside a road, discarded because the
nearest junction is too far away, is a defect in its own right and has nothing to do with the
holes.

**And the counterexample exposes something neither reviewer was asked about.** If the restricted
penalty is charged per edge, then **the penalty a journey pays depends on how many graph edges its
restricted stretch happens to be cut into**, which is a property of where junctions are mapped and
not of the journey. The walked audit's own approach — `band15min_pass-03` — was charged **360 s**
for 159 m of private track lying on **two** OSM ways, because the route crosses three graph edges.
As one edge it would be 120 s. The owner declined to raise `RESTRICTED_PENALTY_S` from 120 s
because it is an unmeasured behavioural quantity; the effective penalty was never 120 s per
journey. See [[project-phase1-s3-soft-way-dependence]].

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

Considering more candidates can only lower a time.

> **"0 cells got slower" is not a check.** It is enforced by construction, because the candidate
> set contains the nearest edge and the comparison takes a minimum. I presented it as a sanity
> check; it cannot be one. Both reviewers said so.

> **The denominator.** 210,533 is **77.1% of the 272,961 comparable cells** and **63.7% of the
> full 330,502-cell grid**. I quoted the first without saying which.

> **W1, the weakness I flagged and checked.** The table was built against a *recomputed* current
> surface. Gemini established the exact relationship: adding the 7,200 s horizon cap and the
> float32 cast makes the recomputation **bit-identical** to the committed raster — `array_equal`
> is True, 0 cells differ. Without the cap, the 4,900 `BEYOND_HORIZON` cells enter as finite times
> of 7,200-11,482 s. Restricted to the cells the product actually publishes a time for, the
> figures become **207,947 improved** (median 46 s, p99 1,286 s) and **88,978** improved by more
> than 60 s, with the winning access leg at a median **168.8 m** and **1.05%** within 50 m. No
> conclusion moves.

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

**And the cheap version does not work well.** Restricting alternatives to edges nearly as close
as the nearest one — the version that keeps the access leg honest — removes **23% of the holes at
20 minutes**. The holes genuinely are closest to a badly connected edge by a wide margin.

> **Corrected: 23% was the worst threshold, quoted as if it were the rule.** At the other limits
> the same +50 m rule removes **38.8% at 10 minutes** (80 -> 49), **39.8% at 15** (123 -> 74) and
> **26.3% at 30** (80 -> 59). It is a weak fix, not a negligible one.

> **And a net count is not a repair count.** 125 -> 96 is a net reduction. Filling one hole can
> complete a ring somewhere else and create another, so the number of *original* holes repaired is
> not measured by either figure. Nothing here tracks hole identity, and a decision based on these
> rows needs that.

## No single bad tag explains it

Matched-edge class for the 125 holes against 20,000 random cells:

| class | share of holes | baseline | enrichment |
|---|---|---|---|
| `residential` | 35.2% | 27.03% | 1.3x |
| `footway` | 16.8% | 9.42% | 1.8x |
| `service` | 13.6% | 14.79% | 0.9x |
| `service=parking_aisle` | 10.4% | 3.64% | **2.9x** |
| `service=driveway` | 8.0% | 20.32% | 0.4x |

Parking aisles are the most enriched and are only a tenth of the holes; the largest single share
is ordinary residential road. **Excluding a tag class would not fix this.**

> Gemini checked the baseline, which contains 17.6% `OFF_NETWORK` rows that can never be a hole.
> Against an OK-only baseline `service=parking_aisle` is 4.29% at 2.4x enrichment and `residential`
> 29.42% — the conclusion is unchanged.

> **A defect in the measurement, found by Codex.** `measure_hole_edge_classes.py` labelled a node
> pair by its **longest parallel edge** rather than by the matched geometry — which is the mistake
> `explain_journey.py` carries a comment about having already fixed once (pass 35). Corrected
> 2026-11-16; the table above is the corrected run.

## What is not established

**Whether the long times are wrong.** Not even for the parking-aisle case, which I claimed was
plain and which rested on the 33 m error above. What is established there is topology — no shared
node — and geometry: connected track edges 31.4 m and 40.0 m away whose endpoints are about seven
minutes from a park. Neither establishes that a person may walk across the intervening ground. For
a cul-de-sac whose entrance really is a mile round, the long time is correct and the hole is the
right answer. Nothing here distinguishes the two, and the structural
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

### Pass 57 corrected the numbers under options 2 and 4, and both reviewers ranked this decision last

**Option 2's figures above are three different mistakes and are left standing only so the
correction has something to point at.**

* **"Fixes 76% of holes" is a net count, not a repair count.** The executed identity test —
  which nothing had run — shows **all 125 UTM originals filled and 30 new hole sites appearing**
  (published: **all 121 filled, 29 new**). A net 125 → 30 was concealing complete turnover.
  Antigravity's run of the same question at +50 m found **100 of 125 repaired and 71 created**.
* **"Makes 77% of cells faster" is true of 272,961 comparable uncapped UTM cells**, not of all
  330,502, and the **169 m** median access leg describes only the **>60 s improvement subset**.
* **"No cell gets slower" is true by construction and therefore measures nothing.** The candidate
  experiment takes the **minimum reported time including today's answer**, so a cell cannot come
  out slower. Re-selected on **cost**, which is what the pipeline does, **3,202 UTM OK cells are
  slower**. This is ledger instance 55.

**Option 4 — "check whether these are noding gaps first" — was my recommendation and it does not
survive.** Antigravity ran it across all 125 holes: **4 (3.2%)** are near-touches within 5 m
without a shared node, **0** are crossings, and **96.8% do not touch at all** (median edge gap
**67.7 m**, max 326.5 m). **49 of 125** are blocked by a mapped building and **72** cross open
ground. So the holes are overwhelmingly real disconnected roads, not junction typos, and a
noding-only audit would have returned "not a data problem" after doing the work.

Both reviewers also rejected the test on principle, independently: **topology cannot settle
walkability.** Geometric contact without a shared node is a representation difference, not an
available pedestrian connection, and the absence of a mapped fence is not evidence of one. Codex's
replacement is a five-step desk audit per hole — recover the cell, edge, route and alternative;
inspect the original ways and nodes including any the component pruning removed; check grade
separation, access tags, barriers and entrances; identify a physically plausible connection; then
evaluate **that specific connection** in a routing counterfactual — classifying each hole as
**supported missing connection**, **supported legitimate separation** or **unresolved**.
Antigravity's is a sharper three-stage version aimed at the 72 open-ground holes against imagery
and parcels.

**Both reviewers rank this decision last of the four** (Antigravity 4 → 3 → 2 → 1; Codex
2 → 4 → 3 → 1), on the same reasoning: the shape and the occupied-cell exposure are established,
the **error prevalence is unknown**, and every candidate fix changes far more journeys than the
121 cells it would repair. Corrected exposure at 20 minutes on published park/walk: **121 holes,
356 buildings, 76 occupied cells, 45 empty**, largest hole 27 buildings, against a published
inventory of **500,451**. Those are **raster cells, not parcels**.

Related: [[project-phase1-s3-unknown-presentation]].

Related: [[project-phase1-s3-criteria-build]], [[s3-13-reading-test]],
[[project-phase1-s3-soft-way-dependence]].
