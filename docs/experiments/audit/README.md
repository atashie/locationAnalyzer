# The walked-journey audit

These sheets exist for one reason: **everything else we have built compares the product to
ourselves.** The travel-time comparison (E1) checks our pipeline against our own routing engine, and
both sides draw their destinations from the same list, so a grocery that closed last year passes
every test we own. Walking a journey is the only check that consults the world. Only the owner can
do it, which is why this is the first item in the S3 plan's section 0 and why the sheet is built to
be cheap to fill in.

## Walk this one

**`triangle-grocery-walk-chapelhill-with-destinations.csv`** — 16 journeys inside 5 km of
Franklin Street and Carrboro, **3.01 hours of one-way walking**, longest 22 minutes. This is the
sheet to fill in.

It is the `…-chapelhill.csv` draw plus the `predicted_destination*` columns, which say **which
grocery each number is about**. Walk this one, not the bare draw: without those columns you would
be picking your own destination and timing your journey rather than checking ours.

`triangle-grocery-walk.csv` beside it is the unrestricted metro-wide draw, kept because its stratum
counts are the metro-wide populations the local sheet is sampled from. Its 19 journeys are scattered
over about 50 km and it is not meant to be walked as one outing.

Each sheet has a `.meta.json` recording exactly which layer the answers came from, which rounding
the minutes use, and how much walking it asks for.

Regenerate with, from `v2/`:

```
uv run python scripts/audit_recommendations.py grocery walk --near -79.0656 35.9117 --radius-km 5 \
  --out ../docs/experiments/audit/triangle-grocery-walk-chapelhill.csv
uv run python scripts/audit_recommendations.py grocery walk      # the metro-wide draw

# then add the destinations (one graph load, about 1.5 minutes per sheet)
python scripts/recover_audit_destinations.py \
  ../docs/experiments/audit/triangle-grocery-walk-chapelhill.csv
```

It **refuses to overwrite** an existing sheet, because a rerun would erase walked results; pass
`--force` when you mean it. **Use `--near`**: it keeps the journeys inside one outing instead of
scattering them over 60 km of the Triangle. The run prints the total predicted walking so the cost
is visible before you set out, and `--max-walk-min` / `--per-stratum` scale it.

The two sheets, kept straight because an earlier version of this file mixed their figures:

| sheet | journeys | with a predicted time | one-way walking | longest |
|---|---|---|---|---|
| `…-chapelhill-with-destinations.csv` — **walk this** | 16 | 16 | **3.01 h** | 22 min |
| `…-walk-with-destinations.csv` — metro-wide reference | 19 | 16 | 2.98 h | 20 min |

The bare `…-chapelhill.csv` and `…-walk.csv` are kept as the draws the recovery reads, and are
what `audit_recommendations.py` regenerates. All 16 Chapel Hill journeys and 16 of the 19
metro-wide ones name a destination; the three that do not are the `off_network` rows, which have no
predicted time and therefore no journey to name.

The metro-wide sheet's other three rows are `off_network_beside_pass15min` and have **no predicted
time at all**, so they sit outside both the `--max-walk-min` cap and the walking total: adjacency
bounds their distance to the *indexed network*, which is not a promise of a short usable walk. The
Chapel Hill sheet has none of them — see below.

## How to walk one

1. Open `osm_link`. The product's answer is for a **100 m cell** centred on `query_lon`,
   `query_lat` — not for that exact point.
2. Pick a real front door inside that cell. Record it in `start_lon`, `start_lat`, and put the
   distance from the cell centre to that door in `door_offset_m`. `door_offset_max_m` (70.7 m) is
   how far the centre can be from any door in the cell; this column is how far it was for you. Note
   that 70.7 m bounds the *straight-line* displacement, not the travel-time error it causes — a
   fence or a one-entrance building can turn 40 m of displacement into five minutes of walking.
3. Walk to **`predicted_destination`** — the shop we actually routed you to. Its coordinates
   and its own map link are in the next columns. Time it door to door at a normal pace. Record
   `walked_seconds`, and put the store you actually used in `destination_used`: normally the same
   name, but not if you had to divert.

   If `predicted_destination_alternatives` is non-empty, several shops snapped to the same road
   node and our number cannot distinguish them. Walk to whichever you would use and name it.

   **If that shop is not somewhere you would genuinely buy groceries, record that and walk it
   anyway.** "Within ten minutes of a grocery" resting on a specialty importer or a produce
   wholesaler is a product finding, and it is the one `destination_qualifies` exists to capture.
   Walking it still gives a usable `walked_seconds` for the routing question.
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
  holds and our stale destination is still undetected. That is why `destination_used` is recorded
  separately from `predicted_destination`: the pair is what shows whether you checked our journey
  or substituted a better one.

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

**The Chapel Hill sheet has no `off_network_beside_pass15min` row.** There are 77 such cells in
the whole metro and **none within 5 km of Franklin Street** under these filters — at least one
recorded building, off-network, and 8-adjacent to a cell passing fifteen minutes. That is an
*absence under those filters*, which is weaker than a statement about the town's connectivity: the
building raster, the 200 m access rule and the adjacency requirement each exclude cells, and a cell
with no recorded building is invisible to it whether or not anyone lives there. The run prints where
the nearest one is. Two are worth a deliberate trip if you are ever passing:

| where | distance from Chapel Hill | its nearest answering neighbour |
|---|---|---|
| `35.94727, -78.99930` (cell 235,185) | 7.2 km | 13.3 min from a grocery |
| `35.84145, -79.08831` (cell 354,107) | 8.1 km | **3.7 min** from a grocery |

The second is the one to pick: we decline to answer for a cell whose neighbour is a four-minute
walk from a shop. Either the 200 m access rule is too strict there or the graph is missing a path
people use. Going there would probably show which — a usable footway we do not have is visible on
the ground, and so is genuinely trackless land — but one visit to one cell settles that cell, not
the rule.

The bands are split by the verdict computed from **float seconds**. That is not necessarily the
verdict the shipped page will show: see below.

## One journey has been walked

**`band15min_pass-03`**, which the product put at **13.5 minutes** and the owner reports at **about
25**. It is recorded in the sheet's observation columns and marked owner-reported and approximate:
it was not stopwatch-timed, no start door was recorded, and which shop was reached is not confirmed.
The cause is understood — the 305 m approach is OSM way **1254722641**, tagged **`access=private`**,
which costs 120 s per restricted edge in `cost` and wins anyway because 360 s of penalty over the
three restricted hops cannot beat the 968 s public detour. **Owner decision 2026-11-10: the penalty stays at 120 s**, because one
journey prices the alternatives without identifying the right one. The gap is monitored, and
estimates that depend on a restricted way are to be flagged when they are delivered. The statistic
to accumulate is the **signed error on journeys whose route uses a restricted edge**: this is one
observation at about +11.5 minutes, which is not a rate. See
`docs/engineering-notes/project-phase1-s3-soft-way-dependence.md`.

Note what the row does *not* claim. Per the asymmetry below, a slow walk to one shop does not refute
the existential fifteen-minute claim for that cell. `witness_within_15min` is `no` **for this walk**;
`unresolved` carries the rest.

## Two limits and one closed question

**We can now tell you which destination we routed you to. Our number is still an upper bound.**

Until 2026-11-10 this section said the destination's identity was not stored and recovering it
"needs one bounded graph load". It was never not computed: `scipy`'s multi-source search returns
the selected source beside the distances, and our code discarded it as `_sources`. The graph load
has now been done — `v2/scripts/recover_audit_destinations.py` — and the `predicted_destination*`
columns are its output. Every row of both sheets was re-derived and matches the committed raster bit-exactly after the
float32 cast.

> **The layer has been rebuilt, and that caveat is retired.** Until 2026-11-10 this said the
> destinations were recovered with *current* code against a raster built before `ab01ffa` fixed
> `symmetrise`, so the agreement was **consistent with but not proof of** the destination the
> stored layer chose (Codex pass 33). The rebuild closes it: the recovery now prints *"the
> committed own_triangle_grocery_walk.npy matches a current-code rebuild on all 330,502 cells"*,
> so these destinations are the ones the layer on disk actually selects. It still runs that check
> every time, so if the arrays and the code drift apart again it will say so.
>
> **What the rebuild moved, and what it did not.** 7,246 of 330,502 cells changed seconds — 7,227
> faster, largest change 2,316.8 s, 11,436 buildings — with **no** change to any cell's reason and
> none to finiteness. At fifteen minutes 15 cells gained a PASS and 1 lost one. **Not one of the 35
> audited journeys moved by a second**, which is why the sample was *not* redrawn: the sheets
> stand, each `.meta.json` now carries a `superseded_by_rebuild` block naming where the arrays it
> digests are kept (`v2/data/layers/prerebuild-2026-11-10/`), and `…-rebuild-delta.csv` beside each
> sheet records the before and after per journey. The same rebuild wrote `_min_possible_s.npy` for
> the first time, so the audit reads a real lower bound instead of reconstructing one.

Rebuild them with:

    cd v2 && python scripts/recover_audit_destinations.py \
        ../docs/experiments/audit/triangle-grocery-walk-chapelhill.csv

Two things that remain true. The layer's aggregation is `cost_selected_category` — the travel time
of the journey our **cost** model picked, which is an upper bound on the time, not the minimum over
qualifying destinations. So a walk that beats our number has not caught us in an error. And a
destination node can carry several places (550 grocery places snap to 510 road nodes), so where
`predicted_destination_alternatives` is non-empty our number does not distinguish them.

One measured detail, because it looked like a defect and was not: `query_lon`/`query_lat` are the
cell centre rendered to six decimal places, which is up to **0.069 m** from the centre itself. That
is enough to shift the snapped journey by about a tenth of a second, so re-projecting the printed
coordinate does **not** reproduce the published number — the recovery works from `row`/`col`
instead. Irrelevant beside a 70 m door offset, but it is why the re-check is exact rather than
tolerance-based.

**The encoded minute now agrees with the printed verdict, and did not before.** Until
2026-11-09 the encoding rounded to nearest, which made every threshold up to 30 s more permissive:
a client reading only the encoded raster passed some cells this sheet prints as FAIL, and three of
these nineteen rows were affected. `encode_minutes` now rounds up, which makes `minute <= T` mean
`seconds <= 60T` exactly, and `encoding_disagrees_min` is blank on every row — so each walk tests
one claim rather than two. `../s3-encoding.md` has the measurement and the decision. If that column
is ever non-blank again, the row is testing two things at once and should be read accordingly.

**The journeys only cover cells with at least one building,** because a cell with no structure has
no door to walk from. "Contains a recorded building" is a filter, not proof of a usable starting
door. 17.4% of the metro's cells are `OFF_NETWORK` but they hold 0.71% of its buildings, so the
walkable part of that stratum is small — 77 cells beside a 15-minute pass — and a few draws from it
can find a real access defect but cannot establish how common one is.

## Source and licence

**`buildings_in_cell`** is derived from **Overture Maps** building footprints, release
`2026-10-21.0`, aggregated to counts per 100 m cell. In this metro that theme draws on:

| upstream source | rows observed | licence |
|---|---|---|
| OpenStreetMap | 454,012 | **ODbL 1.0** |
| Microsoft ML Buildings | 360,755 | **ODbL 1.0** |
| Esri Community Maps contributors | 26,653 | **CC BY 4.0** (with OpenStreetMap waivers) |

An earlier version of this notice grouped Microsoft with Esri under CC BY. That was wrong, and our
own acquisition report says so: 454,012 + 360,755 = 814,767, exactly the ODbL count it recorded
(pass 27). No footprint geometry is reproduced in these sheets — only a count per cell, which is the
modification made — but ODbL §4.3 and CC BY §3 carry notice obligations regardless, which this
section is.

**The travel times** are produced by our own routing over an **OpenStreetMap** extract (ODbL 1.0).
Running our own router does not remove the source-database notice, so OSM is credited for those too.
The grid-centre coordinates are generated from the grid spec, and `osm_link` is an ordinary
hyperlink.

- Overture attribution: <https://docs.overturemaps.org/attribution/>
- ODbL 1.0: <https://opendatacommons.org/licenses/odbl/1-0/>
- CC BY 4.0: <https://creativecommons.org/licenses/by/4.0/legalcode.en>

Whether the full count *raster* is a Produced Work or a derivative database is **not settled here**,
and should be before anything wider than these sheets is published; see
`project-v2-rethink-decisions` decision 17. Nothing above should be read as a finding that this sheet
breaches an obligation — only that the notice now says what it is attributing and to whom.
