# The walked-journey audit

These sheets exist for one reason: **everything else we have built compares the product to
ourselves.** The travel-time comparison (E1) checks our pipeline against our own routing engine, and
both sides draw their destinations from the same list, so a grocery that closed last year passes
every test we own. Walking a journey is the only check that consults the world. Only the owner can
do it, which is why this is the first item in the S3 plan's section 0 and why the sheet is built to
be cheap to fill in.

One file per metro, category and mode, with a `.meta.json` beside it recording exactly which layer
the answers came from and how much walking the sheet asks for.

Regenerate with, from `v2/`:

```
uv run python scripts/audit_recommendations.py grocery walk
uv run python scripts/audit_recommendations.py grocery walk --near -79.0558 35.9132 --radius-km 3
```

It **refuses to overwrite** an existing sheet, because a rerun would erase walked results; pass
`--force` when you mean it. **Use `--near`**: it keeps the journeys inside one outing instead of
scattering them over 60 km of the Triangle. The run prints the total predicted walking so the cost
is visible before you set out (currently ~3 hours one-way over 16 rows, longest 20 minutes);
`--max-walk-min` caps any single journey and `--per-stratum` scales the whole sheet.

## How to walk one

1. Open `osm_link`. The product's answer is for a **100 m cell** centred on `query_lon`,
   `query_lat` — not for that exact point.
2. Pick a real front door inside that cell. Record it in `start_lon`, `start_lat`, and put the
   distance from the cell centre to that door in `door_offset_m`. `door_offset_max_m` (70.7 m) is
   how far the centre can be from any door in the cell; this column is how far it was for you. Note
   that 70.7 m bounds the *straight-line* displacement, not the travel-time error it causes — a
   fence or a one-entrance building can turn 40 m of displacement into five minutes of walking.
3. Walk to a destination that **qualifies under our own category rule** and that you would
   genuinely use. Time it door to door at a normal pace. Record `walked_seconds` and the store in
   `destination_used`.
4. Fill in the four observation columns separately. They are separate because they fail separately:
   - `destination_qualifies` — is it a grocery by our category rule, or your preferred supermarket
     that happens not to be one?
   - `destination_open` — open, in business and usable on arrival? **A closed, fenced or demolished
     destination is a failed recommendation, not a bad row.** Record `no` and keep the row.
   - `route_usable` — any locked gate, missing crossing, private drive, or path that only exists on
     the map?
   - `witness_within_10min` / `witness_within_15min` — `yes` if this walk reached a *qualifying,
     open* destination inside that time, `no` if it did not, `untested` if you did not try.
5. `unresolved` — say what this walk could **not** settle. This column matters more than it looks;
   see the asymmetry below.
6. `notes` — anything that explains a surprise: a hill, a level crossing, a shortcut through a car
   park.

Leave `seconds`, `reason`, `encoded_minutes` and the `outcome_*` columns alone — they are what the
product said before you set out, and overwriting them destroys the comparison.

## The asymmetry: a walk can confirm a PASS but cannot refute one

The product's claim is **existential** — "some qualifying destination is within T" — and that
changes what a single walk proves.

- **A qualifying, open walk inside T is a witness.** It settles that cell: the claim is true there,
  whatever route we computed.
- **A slow walk proves nothing about the claim.** Eighteen minutes to one grocery does not establish
  that *every* qualifying grocery is more than fifteen minutes away. It is evidence about that
  destination and that route, and it belongs in `unresolved`.
- **A successful walk does not refute an UNKNOWN.** UNKNOWN is us admitting we do not know; your
  being able to walk it is useful information about the access rule, not a contradiction.
- **Walking to a *different* destination than the product chose does not clear the product.** If we
  selected a shop that has closed and you walk nine minutes to another one, the real-world claim
  holds and our stale destination is still undetected. That is why `destination_used` is recorded.

So `agrees` is not a column on this sheet. An earlier version had one and it conflated five
different failures; the observations above are recorded separately and the finding is derived
afterwards.

## What each stratum is asking

| stratum | the question |
|---|---|
| `band10min_pass`, `band15min_pass` | within 90 s **under** a threshold: the product says yes. Is it right? A wrong answer here is the one a household is harmed by |
| `band10min_fail`, `band15min_fail` | within 90 s **over** a threshold: the product says no. Did we wrongly rule a place out? |
| `off_network_beside_pass15min` | the product refuses to answer, immediately next door to a cell that **passes**. Either the 200 m access rule is too strict or the road graph is missing a path people use — the layer cannot tell those apart, and a walk can |
| `deep_pass_control` | comfortably inside, with the whole neighbourhood passing, and at least 5 minutes of margin. These should be easy |
| `deep_fail_control` | comfortably outside, with at least 5 minutes of margin. One journey, not three: it is the longest walk on the sheet and a 30-second offset would leave it failing either way |

A control that disagrees is a signal to stop and look, not proof of a systematic error — a single
local closure, entrance or graph defect explains one control just as well.

The bands are split by the verdict computed from **float seconds**. That is not necessarily the
verdict the shipped page will show: see below.

## Three limits to know before you read the results

**We cannot tell you which destination we routed you to, and our number is an upper bound.** The
layer's aggregation is `cost_selected_category` — the travel time of the journey our *cost* model
picked, which is an upper bound on the time, not the minimum over qualifying destinations — and the
identity of that destination is not stored. Recovering it needs one bounded graph load over the
sampled cells; that is the decisive version of this audit and it is not what this sheet is.

**The encoded minute can disagree with the printed verdict.** Rounding seconds to whole minutes
makes every threshold 30 s more permissive, so a client reading only the encoded raster would pass
some cells this sheet prints as FAIL. The `encoding_disagrees_min` column names the thresholds where
that happens for each row — three of the current rows — and `../s3-encoding.md` has the measurement.
Whether the shipped page decides from minutes or from seconds is still open.

**The journeys only cover cells with at least one building,** because a cell with no structure has
no door to walk from. "Contains a recorded building" is a filter, not proof of a usable starting
door. 17.4% of the metro's cells are `OFF_NETWORK` but they hold 0.71% of its buildings, so the
walkable part of that stratum is small — 77 cells beside a 15-minute pass — and a few draws from it
can find a real access defect but cannot establish how common one is.

## Source and licence

`buildings_in_cell` is derived from **Overture Maps** building footprints, release `2026-10-21.0`,
aggregated to counts per 100 m cell. Overture's Buildings theme in this metro draws on
**OpenStreetMap** (ODbL 1.0), **Microsoft ML Buildings** and **Esri Community Maps** (CC BY 4.0 with
OpenStreetMap waivers); the accepted rows here are 495,507 ODbL and 26,653 CC BY. No footprint
geometry is reproduced in these sheets — only a count per cell — but ODbL §4.3 and CC BY both carry
notice obligations regardless, which this section is.

- Overture attribution: <https://docs.overturemaps.org/attribution/>
- ODbL 1.0: <https://opendatacommons.org/licenses/odbl/1-0/>
- CC BY 4.0: <https://creativecommons.org/licenses/by/4.0/legalcode.en>

Everything else in the sheet is ours or is not licensable from a third party: the grid-centre
coordinates are generated from the grid spec, the travel times come from our own routing over an OSM
extract, and the `osm_link` column is an ordinary hyperlink. Whether a full count *raster* is a
Produced Work or a derivative database has not been settled here and should be before anything
wider than these sheets is published; see `project-v2-rethink-decisions` decision 17.
