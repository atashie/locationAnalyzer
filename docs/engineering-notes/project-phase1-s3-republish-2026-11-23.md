---
title: "Republish 2026-11-23: the supermarket layer opens on, and the drive layer can say where it sent you"
date: 2026-11-23
status: published; owner asks 17-19 outstanding
---

# What was republished, and what moved

Owner decisions of 2026-11-23: **13(a)** the default layer becomes `supermarket`; **14** remove the
two records our own classifier refuses; **16** rebuild the drive layer and give it a destination
plane. **15** is approved and not yet done.

Nine layers, up from seven. Reproduce with the runbook at the end.

## The bundle, before against after

| layer | cells answered | change |
|---|---:|---|
| `own_triangle_supermarket_walk` | 246,950 | **NEW, and the layer that opens on** |
| `own_triangle_grocery_walk` | 258,497 | unchanged in count; 303 cells name a different shop |
| `own_triangle_supermarket_drive` | 267,317 | **NEW** |
| `own_triangle_grocery_drive` | 267,317 | unchanged in count; 6,177 cells changed minute; **destination plane added** |
| `park_walk`, `school_walk`, `coffee_bike`, `duke-hospital_drive`, `rdu-airport_drive` | — | **byte-identical** |

The five unrebuilt layers changing in **zero** cells is the control: it says the export is
deterministic and that what moved, moved because a surface was rebuilt.

## The 303 cells are exactly the two records ask 14 removed

`grocery_walk` answers the same 258,497 cells as before — nothing gained, nothing lost — and
**303 of them now name a different shop**. `Pet Dairy` was answering 44 cells and
`Market at Colonnade Center` 259. 44 + 259 = 303.

293 of those cells got **slower**, by a median of 7 minutes and up to 15, and **none got faster**.
That is the shape you would predict: a cell being answered by a dairy brand or a landlord's
property record was being told a shorter walk than its nearest actual shop.

Destinations were compared by resolving each plane through **its own side table** to a set of GERS
ids. Ordinals are dense over the destinations a bundle actually selects, so they renumber whenever
the set changes; comparing them directly once reported 65% of cells "changed destination" when only
the numbering had moved.

## The drive layer, finally current

The published drive surface was built on **2026-11-16 13:57:33**. **22 commits changed which shops
are in the grocery set after that**, including the twelve recorded closures, eleven records leaving
the layer, the ten held collection bays, ask 5's additions, ask 9a's three chains and ask 14's two
removals. With no destination plane, nothing could say which of those shops it was still sending
people to — including shops recorded as closed.

Rebuilt: **6,177 cells changed minute**, 3,878 faster and 2,299 slower, median −1. Faster where
shops were admitted, slower where closures were applied. And it now carries a destination plane:
433 destinations, 31 nodes holding more than one shop, with its own licence block and no phones,
emails, websites, addresses or upstream provider ids.

## What the new default costs, stated carefully

Measured on the **source grid** before reprojection, weighted by building count:

| threshold | any grocery | supermarket | gross lost | gained |
|---|---:|---:|---:|---:|
| 10 min walk | 80,613 | 42,236 | 38,381 | 4 |
| 15 min walk | 165,866 | 102,651 | 63,254 | 39 |
| **20 min walk — the opening value** | **243,908** | **176,983** | **66,929** | **4** |
| 25 min walk | 301,616 | 245,651 | 55,966 | 1 |
| 45 min walk | 428,566 | 401,711 | 26,855 | 0 |
| any answer, 120-min horizon | 498,981 | 492,149 | 6,832 | 0 |
| 10 min drive | 492,403 | 481,048 | 11,355 | 4 |
| 30 min drive | 511,924 | 511,924 | 0 | 0 |

Four things this table is not, each of which was got wrong in a first draft:

1. **A building that fails a threshold has not lost its answer.** 19 minutes becoming 21 minutes is
   a failed threshold and a perfectly good answer. Only the 6,832 at the 120-minute horizon lose an
   answer at all.
2. **The difference is gross, not net.** The model selects minimum *cost* and reports that route's
   *time*, so a supermarket pass need not be a subset of a grocery pass — 4 buildings gain at 20
   minutes and 39 at 15. Small, and real.
3. **These are source-grid counts.** The exporter reprojects and crops, and the browser places
   rows differently again; `measure_export_regrid.py` documents it. In the exported grid the walk
   layers answer 246,950 and 258,497 against 243,417 and 256,569 on the source grid.
4. **The denominator is 512,633 structures, not households.** Overture carries no residential flag
   here, so a shed and a tower block count alike. It is a diagnostic, and cannot be restated as
   households or people.

**The cost falls almost entirely on people who walk.** By car it is 11,355 buildings at 10 minutes
and nothing by 30.

## What the default layer contains

262 records, every one classified `supermarket`, with **zero of the 76 uncorroborated records** and
zero of the 258 nobody has checked. That is true and it is **circular** — it follows from the
category's own class filter, so it describes the selector rather than validating it. What is not
circular: those 258 and 76 records are still published, in the switchable `grocery` layer. Nothing
was deleted.

## Two orphan files removed

`own_triangle_grocery_walk_cell200.{value,status}.bin`, dated 2026-11-13, were being served with no
manifest record, no licence entry and no attribution line. The exporter now refuses before writing
anything when the directory holds a file belonging to no layer it publishes; that refusal named
these two, the bundle was byte-identical afterwards, and they were then removed deliberately. They
regenerate with `--candidates`.

## The one test that went red, and why it was right to

`test_drawn_pixel.py::test_every_probe_expectation_still_matches_the_planes` failed on probe
`corner_se`: the oracle recorded destination ordinal 303 and the plane now holds 302.

**Same shop, same node.** `Food Lion`, node 325658, in both bundles. The destination table went
from 437 entries to 435 when ask 14 removed two records, and every ordinal above them shifted by
one. The oracle was regenerated; no household-facing answer changed for that probe.

## Known and not fixed

* **Ticking "Any grocery shop" cannot broaden the map.** Criteria are intersected, so adding the
  broader layer while the narrower one is ticked can only narrow the result. A household must untick
  `Supermarket` first. Owner ask 17.
* **`measure_drawn_pixel.py` and the walked-cell oracle still read `own_triangle_grocery_walk`**,
  which is no longer the layer a household opens with. They now measure a layer nobody is shown by
  default.
* **Nothing has rendered this bundle in a browser.** The 2026-11-22 bundle was never rendered
  either.
* **The `REFUTED` footprint verdicts are contaminated** by missing building data — see the review
  findings of the same date.

## Runbook

From `v2/`, in this order. Roughly two minutes per surface, two per destination plane, three per
flag plane on a warm graph cache.

```
uv run python spikes/s2_building_weighted_coverage.py supermarket walk
uv run python spikes/s2_building_weighted_coverage.py grocery walk
uv run python spikes/s2_building_weighted_coverage.py supermarket drive
uv run python spikes/s2_building_weighted_coverage.py grocery drive

uv run python scripts/persist_selected_destination.py --category supermarket --mode walk  --write-raster
uv run python scripts/persist_selected_destination.py --category grocery     --mode walk  --write-raster
uv run python scripts/persist_selected_destination.py --category supermarket --mode drive --write-raster
uv run python scripts/persist_selected_destination.py --category grocery     --mode drive --write-raster

uv run python scripts/flag_restricted_routes.py --category supermarket --mode walk --write-raster
uv run python scripts/flag_restricted_routes.py --category grocery     --mode walk --write-raster

uv run python scripts/export_published_layers.py
uv run python scripts/measure_drawn_pixel.py        # the oracle, after the bundle moves
uv run python -m pytest
```

`s2_building_weighted_coverage.py` is the product builder. `g1_own_graph_layer.py` is the
engine-comparison candidate and writes no reason, bound or destination artifacts — using it leaves
the exporter refusing with *"a finite time must be OK and an OK cell must have a finite time"*,
which is the guard catching a half-rebuild.
