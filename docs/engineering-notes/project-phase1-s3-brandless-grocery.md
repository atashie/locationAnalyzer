---
name: project-phase1-s3-brandless-grocery
description: "The brandless grocery rule: floor area separates supermarkets from corner shops at 94%, and still decides only 11% of the blocker, because the records that need deciding are in strip malls"
metadata:
  type: project
---

# Floor area is a good signal and a weak rule

**Owner decision 2026-11-18**, *"1-4) yes, proceed"*, on the third ask: the brandless grocery rule,
which the resume point has called the real blocker. 323 of the 541 grocery records carried no
Overture `brand`, 272 are still unclassified today, and `grocery_store` covers a supermarket and a
corner shop alike.

`locfinder/places/grocery.py` named what a better mechanism would need:

> nothing in Overture or OSM measures range. A more robust mechanism would need something that
> does: **floor area**, aisle or department counts, a product-range signal from a source that
> holds one, or simply asking people in the neighbourhood.

Floor area is first on that list and 522,160 footprint polygons were already on disk. So it was
measured rather than discussed. **The result is that floor area is a genuinely good discriminator
and a weak rule for this population, and the reason why is worth more than the rule.**

Scripts: `v2/scripts/measure_footprint_separation.py` (predictions committed before either run, at
`90aa77e`) and `v2/scripts/shortlist_brandless_grocery.py`. Sheet:
`docs/experiments/audit/grocery-brandless-footprint-shortlist.csv`, blank `verdict` column.

## It separates the populations very well

Calibrated on OSM's own tags, using each feature's **own polygon** where it has one so that no
footprint is borrowed from a neighbour:

| | n | median | IQR | max |
|---|---|---|---|---|
| `shop=supermarket` | 103 | 4,081 m² | 2,207 – 5,562 | 20,903 |
| `shop=convenience` | 269 | 289 m² | 224 – 407 | **1,051** |

A single threshold at **650 m²** puts 94.2% of supermarkets above and 95.2% of convenience stores
below. Widen the calibration to include point features that borrow the building underneath them
and the optimum moves to 750 m² at 93.7% / 93.6% — slightly *worse*, while the convenience maximum
jumps from 1,051 m² to 13,898 m². That jump is the whole story: the giant "convenience stores" are
units in a retail parade wearing the parade's footprint.

The prediction committed beforehand was a supermarket median of at least 2,500 m², convenience
under 400 m², and a threshold getting 85% of both sets right. **All three held.** Coverage was
predicted at 70% or better and came in at 77.9%.

## And the obvious rule would have been a disaster

Apply `area >= 750 -> supermarket` and 137 of the 272 open records become weekly shops. Then ask
how many of those actually have the building to themselves:

| of 211 reachable brandless records | total | ≥ 750 m² | < 750 m² |
|---|---|---|---|
| **sole place in its footprint** | 30 | **2** | 28 |
| **shares its footprint** | 181 | 135 | 46 |

The shared ones run to **31, 40, even 79 place records in one polygon**. So nearly every record the
naive rule would have promoted is a small shop in a parade, and the rule would have put 135 corner
shops into a **published** weekly-shop layer.

## The positive branch is withdrawn, and the reason is structural

The two records that passed "large footprint, sole occupant" are **both wrong**:

* `Big Spoon Roasters`, 980 m² — a nut-butter maker.
* `C & F Foods`, 12,180 m² — warehouse scale, a distributor.

0 of 2 verified, and not by bad luck. A real Triangle supermarket **sits in a shopping centre and
therefore shares its footprint**, so "large building, sole occupant" selects for food production
and distribution — the opposite of a weekly shop. The branch proposes nothing and this finding
replaces it.

## The rule that survives, and the free probe that fixed it

**A footprint is an upper bound on the shop inside it.** That gives one proposal, in the cheap
direction only:

* **`not_a_weekly_shop`** — the whole matched building is under 650 m² **and** nothing within
  120 m is over it either. If no building big enough to be a supermarket stands anywhere near,
  none is there.
* **`undecided`** — everything else.

The second condition came from a probe worth keeping: **34 of the 272 records are *named* after a
known chain**, which makes the rule checkable without a site visit. It first called 7 of them
`not_a_weekly_shop`. Checking each against nearby buildings:

* **5 were right.** `ALDI` (489 m²), `Lidl` (224), `Lowes Foods` (256), `Food Lion` (536) and
  `Walmart` (446) have no building over the floor anywhere within 120 m. Whatever those records are
  — defunct stores, pickup lockers, phantom rows — no supermarket stands there.
* **2 were wrong.** Both `Wal Mart` records sit outside any building with a **3,943 m²** building
  120 m away: a real Walmart with a displaced point, and the rule read the wrong structure.

The 120 m guard fixes exactly that, and both Walmarts are now `undecided`. It costs yield honestly:
the proposal count falls from 70 to 30.

## What it decides

```
272 grocery records are unclassified and brandless
   30  proposed NOT a weekly shop            (11.0%)
  242  left undecided                        (89.0%)
  footprint reach: 211 of 272 have one at all (77.6%), median 1,189 m2
```

**11% of the blocker, all of it in the cheap direction.** `unclassified` and `not_a_weekly_shop`
are both outside the supermarket layer, so a wrong negative changes a household's result not at all
and only records a judgement that can be revisited; a wrong positive would route somebody to a
nut-butter workshop. The rule only speaks where being wrong is free.

## The better lead this turned up

The probe is the useful part. **34 of 272 brandless records are named after a chain already in
`SUPERMARKET_BRANDS`** — `Food Lion`, `Harris Teeter Supermarkets`, `Lowes Foods On Rowlock Way`,
`Carlie C's Iga`, five `Walmart Grocery Pickup and Delivery`, `ALDI`, `Lidl`. The `brand` field is
empty on every one of them; the `name` field says the answer.

So **the brandless blocker is substantially a brand-FIELD blocker rather than a classification
problem**, and roughly an eighth of it is recoverable by matching the place name against the same
explicit chain table the brand is already matched against — which is not a name *heuristic*, it is
the existing table consulted through a second field.

**That is a decision for the owner, not a session**, because `grocery.py` records the opposite
instruction in as many words: *"there is deliberately no heuristic on the name, because the name
and the brand are exactly where this data is worst."* Worth noting while deciding: every example
that module gives for distrusting the data is a case where the **brand** is wrong and the **name**
is right — `Bitcoin Depot` branded onto a place *named* `Casablanca Market`, `Ray's Food Place`
branded onto `Ray's Supermarket`, `Food Lion- Summersville, WV` branded onto `Food Line
Distribution Center`. The name was the better field in all three.

## Licence, which is separate from whether it works

The buildings file was acquired under the **diagnostic** allowlist and its own report records the
use as *"rasterised to counts, never republished"*. Every row is ODbL-1.0 or CC BY 4.0. Measuring
is inside that, and this stopped at a sheet.

**Classifying a published layer from it would not be.** It would make the grocery layer an
ODbL-derived database and falsify that registry row. It is the same exposure the project already
carries — `OSM_CONFIRMED_SUPERMARKETS` is derived from the ODbL `osm_pois` extract and feeds the
same layer — and decision 17 welcomes ODbL publication of OSM-derived work. But the registry row
would need rewriting, and that is the owner's line to move.

## What was not done, deliberately

No change to `classify_grocery` and no new table in `grocery.py`. The owner's decision for that
module is *"use big brands, and a curated list for the independents"*, and a machine-generated list
is not a curated list. The artefact is named a shortlist rather than `FOOTPRINT_CONFIRMED_*` for
the same reason `pharmacy-fsq-shortlist.csv` is: a script must not pre-empt an open decision by
choosing a filename.
