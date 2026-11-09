# The walked-journey audit

These sheets exist for one reason: **everything else we have built compares the product to
ourselves.** The travel-time comparison (E1) checks our pipeline against our own routing engine, and
both sides draw their destinations from the same list, so a grocery that closed last year passes
every test we own. Walking a journey is the only check that consults the world. Only the owner can
do it, which is why this is the first item in the S3 plan's section 0 and why the sheet is built to
be cheap to fill in.

One file per metro, category and mode, with a `.meta.json` beside it recording exactly which layer
the answers came from.

Regenerate with, from `v2/`:

```
uv run python scripts/audit_recommendations.py grocery walk
uv run python scripts/audit_recommendations.py grocery walk --near -79.0558 35.9132 --radius-km 3
```

It **refuses to overwrite** an existing sheet, because a rerun would erase walked results; pass
`--force` when you mean it. `--near` keeps the journeys inside one outing instead of scattering them
over 60 km of the Triangle — use it.

## How to walk one

1. Open `osm_link`. The product's answer is for a **100 m cell** centred on
   `query_lon`, `query_lat` — not for that exact point.
2. Pick a real front door inside that cell. Record it in `start_lon`, `start_lat`, and put the
   distance from the cell centre to that door in `door_offset_m`. `door_offset_max_m` (70.7 m) is
   how far wrong the centre can be; this column is how far wrong it actually was for your journey.
3. Walk to the grocery **you would actually use** from there. Time it door to door at a normal pace.
   Record `walked_seconds`, and which store in `destination_used`.
4. `destination_open` — was it open, in business, and usable when you arrived? **A closed, fenced or
   demolished destination is a failed recommendation, not a bad row.** Record `no` and keep the row.
5. `agrees` — `yes` if the walk is consistent with the product's `outcome_10min` /
   `outcome_15min`, `no` if a household acting on our answer would have been misled. Judge the
   *decision*, not the seconds: 9:40 against a predicted 9:10 agrees; 13:00 against a predicted
   9:10 does not.
6. `notes` — anything that explains a disagreement: a crossing that does not exist, a locked gate, a
   path through a car park, a level crossing, a hill.

Leave `seconds`, `reason` and the `outcome_*` columns alone — they are what the product said before
you set out, and overwriting them destroys the comparison.

## What each stratum is asking

| stratum | the question |
|---|---|
| `band10min_pass`, `band15min_pass` | within 90 s **under** a threshold: the product says yes. Is it right? A wrong answer here is the one a household is harmed by |
| `band10min_fail`, `band15min_fail` | within 90 s **over** a threshold: the product says no. Did we wrongly rule a place out? |
| `off_network_beside_ok` | the product refuses to answer, next door to a cell that passes. Either the 200 m access rule is too strict or the road graph is missing a path people use — the layer cannot tell those apart, and a walk can |
| `deep_pass_control` | comfortably inside, with the whole neighbourhood passing. These should be easy. If a control disagrees, the error is systematic and the bands cannot be read |
| `deep_fail_control` | comfortably outside, with the whole neighbourhood failing. Same purpose, other direction |

The bands are deliberately split by the answer the product gives. An earlier, symmetric version drew
six journeys that all happened to sit *above* 15 minutes, so every row asked the same question and no
walk could have shown which direction an offset ran.

## Two limits to know before you read the results

**We cannot tell you which grocery we routed you to.** The layer stores the minimum over every
qualifying destination and not which one won, so your walk establishes that *some* destination was
open and reachable, not that *ours* was. That narrows the closed-destination blind spot; it does not
close it. Closing it needs `build_layer_surface` to emit the chosen destination per cell.

**The journeys only cover cells with at least one building.** A cell with no structure has no door
to walk from. 17.4% of the metro's cells are `OFF_NETWORK` but they hold 0.71% of its buildings, so
the walkable part of that stratum is small — 633 cells of 24,468 — and three draws from it are a
thin sample of a thin population. Read agreements there as encouraging, not as evidence.
