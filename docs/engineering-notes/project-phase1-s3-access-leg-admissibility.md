# The nearest road is not always a road you can reach

**2026-11-17. Owner decision, and a known issue opened and deliberately deferred.**

Asked to choose a unit for the restricted-road penalty — per edge, per stretch or per metre — the
owner declined all three and reframed the problem:

> "keep the penalty as is; the issue is not the penalty but that we are snapping to the 'wrong'
> nearest road - the nearest road by distance is not always a road that is legally accessable or
> physically accessible (e.g., across a stream without a bridge); let's note this as a known issue
> but defer addressing it, and perhaps revisit later with some more advanced geospatial techniques
> (e.g., bringing in DEM topography or waterbody delineations or property boundary polygons)."

**Decision 2 is therefore closed with no change.** `RESTRICTED_PENALTY_S` stays at 120 s for walk
and bike and 450 s for drive, charged per graph edge. The reviewers' split — Codex SUPPORTED
per-stretch, Antigravity PREMATURE — is moot, because both were answering a question about the
*price* of using a way, and the owner's position is that the defect is in *which way we attach to
at all*.

## Why the reframe is better than the question it replaced

The penalty exists to discourage routing down private ground. It is a price on a way the model has
already decided to use. But the model's first act is geometric and unpriced:

* **`snap.py` matches each cell to the single nearest edge by straight-line distance**, within
  `MAX_ACCESS_M = 200 m`, via `idx.tree.nearest(pts)` — exactly one candidate.
* **Nothing checks that the household can get to that edge.** Not whether there is a fence, a
  stream, a cliff, a wall, a building, or somebody else's garden in between. The access leg is a
  straight line on a map, and a straight line is not a path.

Three measurements already in the repository say the same thing from different directions, and none
of them was read this way until the owner said it:

* **The donut holes.** Of the 125 isolated excluded cells, only **4 (3.2%)** are OSM noding gaps.
  **96.8% do not touch a passing road at all** (median gap 67.7 m), **49 are blocked by a mapped
  building**, and **72 cross open ground**. We called that "real disconnected roads". It is equally
  a description of access legs nobody can walk.
* **The walked journey.** `band15min_pass-03` was published at 810.8 s because the route takes
  305 m of OSM way 1254722641, tagged `access=private`. The penalty argument is about what that
  305 m should cost. The owner's argument is that it should not have been a candidate.
* **`anchor.py` already does the thing, for destinations only.** It has reachability, displacement
  and barrier-crossing evidence, and Antigravity's W8 run used the same idea to find that 136 of
  29,594 park-boundary samples cross a mapped fence or wall. **Origins get none of it.**

So the project already owns a barrier-aware attachment model, applies it at one end of the journey,
and attaches the other end by nearest neighbour.

## What "deferred" means here

Not a backlog item to be quietly dropped. It is deferred because the honest fix needs data the
project does not hold, and the owner named the candidates:

| technique | what it would rule out | cost |
|---|---|---|
| **Waterbody delineation** | access legs crossing a stream, pond or lake with no bridge | free; NHD or OSM `natural=water` |
| **DEM topography** | legs up a cliff or an embankment a map shows as flat | free; USGS 3DEP, but a real raster pipeline |
| **Property boundary polygons** | legs across land the household has no right to cross | the hard one — parcel data is county-by-county and often licence-encumbered |
| **OSM barriers** | fences, walls, hedges, gates | **already on disk** (`osm_barriers.parquet`), already used for destinations |

The last row is the cheap one and is the obvious first step whenever this is picked up: extend
`anchor.py`'s barrier screening from destinations to origins, and measure how many cells change.
Nothing in this note authorises doing it.

## What this does NOT say

* It does not say the published numbers are wrong. It says a class of them is unverified in a
  specific way, and names the way.
* It does not retire the per-edge penalty's segmentation artefact. That is still true — the charge
  still depends on where junctions happen to be mapped — it is simply no longer the thing being
  fixed first.
* It does not establish how many cells are affected. **Nobody has measured it**, and the number
  that would matter is "cells whose selected access leg crosses something impassable", which needs
  the barrier screen to exist before it can be counted.

## The one measurement worth taking when this is revisited

Before any of the advanced techniques: run the existing `osm_barriers.parquet` screen against every
cell's matched access leg and count how many legs cross a barrier. It costs one graph load, it uses
data already in the repository, and it converts this note from a hypothesis into a size. If the
answer is small, the whole issue is a footnote; if it is large, it outranks everything else in S3.

Related: [[project-phase1-s3-donut-holes]], [[project-phase1-s3-soft-way-dependence]],
[[project-phase1-s3-destination-identity]], [[project-phase1-s3-progress]].
