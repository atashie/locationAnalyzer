---
title: "The ask-7 republish: what changed in the bundle a household is served"
date: 2026-11-22
status: done, measured against a snapshot; nothing here is tracked in git, which is why this note exists
---

# The ask-7 republish, 2026-11-22

Owner answered ask 7 with **"republish"**. This is what it changed and what it did not.

**None of the artifacts is tracked in git.** `v2/.gitignore` excludes `data/` and
`spikes/g3-render/fixtures/published/`, so the republish produced **no diff**, and this note plus
the snapshot in `v2/data/layers/prerepublish-2026-11-22/` are the only record of it. The snapshot
holds the old planes, the old destinations table, the old manifest and a `baseline.json` of
digests, on the pattern of `prerebuild-2026-11-10/`.

## The runbook, which did not exist and cost two false starts

There was no written sequence for rebuilding the published bundle, and **the obvious-looking script
is the wrong one.** For the record, in order, all from `v2/`:

```
uv run python spikes/s2_building_weighted_coverage.py grocery walk   # seconds, reason,
                                                                     # min_possible_s, buildings,
                                                                     # the .tif and the sidecar
uv run python spikes/s0_status_on_real_layer.py grocery walk         # verification, writes no plane
uv run python scripts/flag_restricted_routes.py --write-raster       # the disclosure plane
uv run python scripts/persist_selected_destination.py --write-raster # which shop each answer is
uv run python scripts/export_published_layers.py                     # the browser bundle
uv run python scripts/measure_drawn_pixel.py                         # the probe ORACLE, which
                                                                     # three committed tests read
```

**The last line is not optional and I missed it.** `docs/experiments/s3-10-drawn-pixel.json` is a
committed expectation file derived from the planes, and `tests/test_drawn_pixel.py` re-derives every
probe from the `.bin` files to catch it going stale -- it says in as many words that *a committed
expectation file that no longer matches the planes it was computed from is worse than none*. The
suite went red immediately after the export, which is the guard doing its job.

**Regenerating that oracle then invalidated the browser-session record**, because the oracle picks
its probes where the painted colour can contradict the card and that choice depends on the planes:
four probes now name a different published cell. `docs/experiments/s3-11-browser-placement.json` is
*the only evidence in this project that a browser has ever drawn the publication*, and
`tests/test_browser_placement.py` forbids re-running it. Resolved by having the record **declare its
own supersession** -- a `superseded_by` block naming the event, the date, what is no longer
established and what would restore it -- with two new tests that make the declaration mandatory and
require it to be specific. **Nothing has rendered the 2026-11-22 bundle.**

* `spikes/g1_own_graph_layer.py grocery walk` **is not the product builder.** It is the G1
  engine-comparison candidate. It writes `.npy` and `.tif` and **not** `_reason.npy`,
  `_min_possible_s.npy` or `_build.json`, so running it leaves the status plane and the lower bound
  describing the *previous* build. The product builder is
  `spikes/s2_building_weighted_coverage.py`, whose sidecar carries digests of the three arrays it
  just wrote.
* `spikes/s0_status_on_real_layer.py` **validates and writes no plane.** It is worth running: it
  reported `float32 identical=True, 0 cells differ` against the seconds it had just been given,
  which is how the surface and the status plane are known to describe the same build.
* **`export_published_layers.py` caught the half-rebuild**, refusing with *"a finite time must be
  OK and an OK cell must have a finite time"* when the seconds were new and the reason plane was
  twelve days old. The guard worked and is the reason this note can be trusted. Note also that
  `flag_restricted_routes.py` and `persist_selected_destination.py` ran against that stale plane
  before the error surfaced, so both had to be re-run.
* Runtime on a warm graphml cache: about **100 s** for the surface, ~85 s each for the two plane
  steps, a few seconds for the export. **The ask-7 estimate of "a day of compute" was wrong by two
  orders of magnitude** -- it came from the 2026-11-10 log, where `load_graph_s` was 167 s and
  `save_graphml_s` 73 s on a cold cache, and nothing in that log supported "a day".

## What the bundle now says

| | before | after |
|---|---|---|
| surface built | 2026-11-10 14:24:13 | **2026-11-22 17:18:23** |
| destinations plane built | 2026-11-14 08:28:39 | **2026-11-22 17:23:39** |
| destination places in the routing | 550 | **555** |
| destination nodes | 510 | **518** |
| nodes selected by at least one cell | 432 | **437** |
| place records named in the bundle | 468 | **469** |
| cells with a published answer | 258,684 | **258,497** |

## Did the owner's decisions reach a household? Mostly

* **All 15 ruled-out records are gone.** `DROPPED_PLACE_IDS` had 15 members named in the old
  bundle; the new bundle names **none**. That includes `Weaver Street Market, Inc` (the Food
  House), `Weaver Street Market Administration`, seven `Walmart Grocery Pickup and Delivery` bays,
  `Variety Pick-Up`, `Food Line Distribution Center`, `Usf Sales`, `Southern Season`, the
  2017-closed `Harris Teeter` and two `Kroger` records.
* **17 of the 23 admitted records are now named destinations.** Six are not, and the reason is not
  a defect:

**EIGHT OF THE 23 ADMITTED RECORDS LIE OUTSIDE THE PUBLISHED GRID.** The grid is 514 x 643 cells of
100 m, x 661900..726200, y 3952100..4003500 in EPSG:32617. Distances outside its envelope:

| record | where | metres outside the grid | named in the bundle? |
|---|---|---:|---|
| `50ada728` | 1015 Lewis St, Oxford | 14,169 | no |
| `4e8d15fb` | 1051 E Broad St, Fuquay-Varina | 10,853 | no |
| `c7fee873` | Publix at Middle Creek Crossings | 10,833 | no |
| `84c14b53` | 1318 Mebane Oaks Rd, Mebane | 6,396 | no |
| `28180454` | 7016 Gb Alford Hwy, Holly Springs | 6,298 | no |
| `182dc975` | 805 Town Centre Blvd, Clayton | 2,854 | **yes** |
| `0da6a7a0` | 7106 Knightdale Blvd, Knightdale | 544 | no |
| `5a7ca34c` | 750 Timber Drive, Garner | 286 | **yes** |

A destination outside the grid still competes in the routing and can be the nearest grocery for
cells near the edge, which is why Clayton and Garner appear. The other six are never any cell's
answer. **So "23 admitted" overstates the reach: 15 are inside the area the product covers**, and
the four days spent adjudicating the set included a third of it that cannot change what any
in-grid household is told.

## What a household is told differently

Measured plane by plane against the snapshot. **`value.bin` is uint8 minutes** and **`dest.bin` is
a uint16 ordinal into that bundle's own `destinations.json`** -- the republish renumbered all 437
destinations, so **65.0% of ordinals differ and that number means nothing**. The comparison below
resolves every ordinal through its own bundle's table to a set of Overture ids first, which is the
same lesson as everything else this week: compare the thing, not the encoding.

* **198 cells LOST their answer; 11 gained one.** A lost answer is a cell previously told a grocery
  was within two hours' walk and now told nothing. Every one of them is the removal of a false
  claim rather than a regression -- the answer they had pointed at a distribution centre, an
  administration office or a pickup bay -- but **198 is the harm-direction number for this
  republish** and it is the one to quote.
* **14,360 of 258,486 cells answered in both bundles (5.56%) have a different published minute.**
  9,192 nearer, 5,168 further. Median **-2 min**, p5 -37, p95 +12, range -69..+22.
* **16,494 cells (6.38%) now end at a different shop.** The commonest changes are exactly the
  corrections that were intended:

| cells | answer before | answer now |
|---:|---|---|
| 3,110 | `Usf Sales` | `Food Lion` |
| 1,966 | `Joy Mart` | `Walmart` |
| 1,339 | `Food Lion` | `Aldi` |
| 883 | `Walmart Grocery Pickup and Delivery` | `Walmart` |
| 786 | `Buffaloe Grocery` | `Publix Super Market at Buffaloe Bend` |
| 778 | `Harris Teeter` | `Walmart Neighborhood Market` |
| 701 | `Walmart Grocery Pickup and Delivery` | `Aldi` |
| 634 | `Food Lion` | `Walmart Supercenter` |
| 400 | `Weaver Street Market Administration` | `Carolina Cupboard` |

3,110 cells were being told their nearest grocery was `Usf Sales`. They are now told it is a Food
Lion. That is what the republish was for.

## What the republish did NOT fix, stated as sharply as it can be

Ask 9b was not authorised, so the uncorroborated records stay. Against the screen's own output:

* **63 of the 469 named destinations are records our own screen says nothing corroborates.**
* **42,430 cells -- 16.41% of every answered cell -- have a published answer whose destination is
  entirely uncorroborated records.**
* `Roofing Inc.` is still a selected destination. **540 cells are told their nearest grocery is a
  record named `No longer`.** Others answering more than a thousand cells each:
  `Jean's Neighborhood Market` 4,554, `Homestead Harvest Farm` 3,590,
  `Allen Powell Memorial Collard Patch` 3,228, `ABC Meats` 2,897, `May's Grocery` 2,493,
  `Foodmart` 2,400, `Funny Girl Farm` 1,875, `Tienda Mi Ranchito` 1,718, `Joy Mart` 1,640,
  `Currin Farm` 1,618, `Seal The Seasons` 1,320, `Aloe Verapol, Llc` 1,205,
  `Carolina Cupboard` 1,094, `The Drive Thru Market` 1,064.

**These are not one population and that is the whole difficulty.** `Tienda Mi Ranchito`,
`Tortilleria El Rodeo`, `May's Grocery` and `Jean's Neighborhood Market` are very likely real shops
that our three sources simply do not cover, and removing them hides a real shop from the
neighbourhood most likely to depend on it. `No longer`, `Roofing Inc.`, `Aloe Verapol, Llc`,
`Longview Poole Road` and four farms are a different matter. The 16.41% is therefore **not** an
error rate; it is the size of the population nobody has looked at, and it is now the largest known
problem in the published layer.

## Not done

* **The bundle has not been opened in a browser.** The export validated and the planes are
  internally consistent, but nothing has rendered them. The known defect that the overlay needs a
  panel-scrollbar drag to first paint is unaddressed and unrelated.
* **Only `grocery_walk` was rebuilt.** `grocery_drive`, `coffee_bike`, `park_walk`, `school_walk`,
  `duke-hospital_drive` and `rdu-airport_drive` were re-exported from **their existing surfaces**.
  `grocery_drive` matters most, because it is built from the same `grocery` category: its surface
  is dated **2026-11-16 13:57:33**, which predates every exclusion and admission decided on
  2026-11-18 and 2026-11-19, so it cannot reflect any of them. Which records its destination set
  actually contains has **not been measured** -- that layer carries no destinations table, so the
  only way to know is to rebuild it. Rebuilding it was not asked for and is the obvious follow-on
  to ask 7.
* The `supermarket` layer is untouched and remains unpublished. See ask 10.
