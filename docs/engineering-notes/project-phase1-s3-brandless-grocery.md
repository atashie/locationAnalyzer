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
  > **CORRECTED 2026-11-18, third review.** That 3,943 m² building is **Europa Center**, 67 m and
  > 81 m from the two points, and it is somebody else's building. So "a real Walmart with a
  > displaced point" was a guess dressed as a reading, and the rule did not read *the wrong
  > structure* — it read *a stranger's structure*. The 120 m guard that came out of this is still
  > the right action for the wrong reason: both records belong undecided, and they do now.

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
## The lead was taken up the same day, and it worked

Owner, *"1-4) yes, proceed"*. The 34 chain-named records are now recovered where the evidence
supports it: `v2/scripts/recover_brandless_by_name.py`, table `NAME_CONFIRMED_SUPERMARKETS` in
`locfinder/places/grocery.py`, sheet `docs/experiments/audit/grocery-name-recovery.csv`.

**`chain_in_name` is a lookup, not a heuristic**, and `grocery.py` now draws that line in its own
words: still refused is *parsing* a name to guess what kind of shop it is; now allowed is *looking
a name up in the same explicit table the brand is looked up in*.

> **CORRECTED 2026-11-18, third review.** This sentence used to claim the discipline for the whole
> classifier, which was an overstatement. Chain membership is a lookup. **`SERVICE_POINT_WORDS` is
> a heuristic** — a word list I chose by reading 34 rows — and so is the geometric screen. The
> review produced a business the word list rejects wrongly: `Norseman IGA and Post Office`, a real
> combined supermarket and post office, refused for the word `office`. It found no local false
> rejection among the current candidates, so this is a limit and not a present defect. Only `SUPERMARKET_BRANDS` is consulted — so
`Kroger Store` and `Wegmans`, both real and both trading here, match nothing until somebody edits
the table. That dropped the candidates from 34 to 33 on its own.

**Two screens, each earned by a failure in the data:**

| | refused | why nothing else could catch it |
|---|---|---|
| **service point** | 11 | Nine `Walmart Grocery Pickup and Delivery` and a `Weaver Street Market Administration`. Several sit on the chain's own ~20,000 m² footprint, so **every geometric signal says supermarket** and only the name says collection bay. |
| **no building** | 9 | `Food Lion` at 536 m², `ALDI` at 489, `Walmart` at 446, `Lidl` at 224 — nothing over 650 m² within 120 m. The name alone would have promoted all of them. |

**13 accepted** — ~~every one checked by name before it went in~~ — `Brier Creek Walmart`
(20,903 m²), `Food Lion` (11,617), `Harris Teeter Supermarkets` (8,937), `Carlie C's IGA` (7,339),
`Lowes Foods On Rowlock Way` (7,056), `ALDI` (5,156), `Weaver Street Market, Inc` (13,127), and
six more.

> ### CORRECTED 2026-11-18, third review: 13 became 7
>
> **8 of the 13 rested on a building their point is not inside**, and the two doubts recorded
> below were both understatements. `corroboration()` in `locfinder/places/footprint.py` now
> requires the record to sit **inside** a building at or above the floor; a big building merely
> *near* the point returns `NEIGHBOUR`, which refuses.
>
> | record | the building it was accepted on | distance |
> |---|---|---|
> | `Lowes Foods`, 2900 Wake Forest Rd | **Discount Tire**, 837 m² | 105 m |
> | `ALDI`, 4241 Louisburg Rd | **New Hope Baptist Church**, 5,156 m² | 115 m |
> | `Wal Mart`, 1748 Fordham Blvd | **Europa Center**, 3,943 m² | 81 m |
> | `Wal Mart`, 1748 Fordham Blvd | **Europa Center**, 3,943 m² | 67 m |
> | `Lowes Foods`, 3480 Kildaire Farm Rd | *commercial*, 5,228 m² | 86 m |
> | `Lowes Foods Of Cary On High House` | *retail*, 4,064 m² | 26 m |
> | `Carlie C's IGA` | *commercial*, 7,339 m² | 118 m |
> | `Weaver Street Market, Inc` | **Eno Mill**, 13,127 m² | 14 m |
>
> **"Every one checked by name before it went in" is the claim that failed.** I did read all 13
> names. Reading a name cannot tell you which building a point is in, and the one thing I did not
> check is the one thing the acceptance rested on.
>
> **`Weaver Street Market, Inc` is the co-op's Food House** — a commercial kitchen, an NCDA
> meat-processing plant (P-317), two bakeries and warehousing, delivering to the four shops twice
> a day. A supplier, promoted to `supermarket`. It is now in `NOT_A_WEEKLY_SHOP_SITES`.
>
> **7 survive:** `Brier Creek Walmart` (20,903 m², and the building is *named* Walmart
> Supercenter), `Food Lion` (11,617), `Harris Teeter Supermarkets` (8,937), `Lowes Foods On
> Rowlock Way` (7,056), `Carlie C's IGA` (6,942 — its **own** building, not the 7,339 next door),
> `Harris Teeter` (4,181), `ALDI` (1,441).
>
> **One doubt is left attached rather than resolved:** the surviving `ALDI` is at 4241 Louisburg
> Rd, which the review reports as an ALDI that relocated to 6101 Capital Blvd in October 2019.
> Reporting confirms a Louisburg Road ALDI moving then, but ties no source to this street number.
> Kept with the doubt in its entry, and raised as an owner ask.

**~~Two things left visible rather than tidied away:~~** *(both superseded by the correction above
— each was a real signal I recorded as a curiosity instead of following.)*

* One `Lowes Foods` is corroborated by an **837 m²** building — just over the floor and small for
  that chain, possibly a point on a neighbouring structure. The number is in its entry so it can
  be struck. — **It is Discount Tire, 105 m away.** "Possibly a point on a neighbouring structure"
  was exactly right and I filed it as a footnote.
* **Two `Wal Mart` records share one 3,943 m² building** and are very probably duplicates of one
  store. That is a de-duplication problem, not a classification one, and this table does not
  pretend to solve it. Both are the records the *footprint* rule got wrong this morning, so the
  name rule has fixed a known error. — **They share Europa Center, which is neither of them.**
  They may still be duplicates of each other; nothing here shows it, and the name rule fixed
  nothing.

**Effect on the blocker, corrected 2026-11-18 after the third review:** unclassified grocery
records fall from **272 to 264**, of which **263** carry no brand — seven recovered plus the Food
House ruled out. The `supermarket` target goes **235 → 242**.

> **What this paragraph used to say, and why each number was wrong.** *"272 to 259, of which 258
> carry no brand. So this took an eighth of what was left, and the blocker went 323 → 259."*
>
> * **259 → 264.** Six of the thirteen were withdrawn.
> * **"An eighth" was the candidate numerator, not the accepted one.** `34 / 272 = 12.5%` is the
>   eighth; `13 / 272 = 4.8%`, and `8 / 272 = 2.9%` is what actually moved. The previous review had
>   caught me conflating two populations and the prompt for this one said so out loud. It happened
>   again, in the same sentence shape, one paragraph from where I warned about it.
> * **"323 → 259" put two different populations on either side of an arrow** — a brandless start
>   against a total-unclassified end. The review supplies the matched figure: the comparable
>   brandless starting count is **271**, not 272.

**Licence — CORRECTED 2026-11-18, third review.** The widened permission is real; **this work did
not exercise it.**

The table feeds the **`supermarket`** target. The published manifest carries **`grocery`**, which
is taxonomy-based and does not consult `classify_grocery` at all. Measured: `supermarket`
235 → 242, **`grocery` 543 → 543**. *(The 543 was the live count when this was measured. It became
**532** the same day in `ae89174`, for an unrelated reason — the owner's ask 3 removed eleven
records by id. The 543 → 543 above is still the right measurement of what the RECOVERY did, which
is what this section is about. Re-checked after `ae89174`: no exclusion entry cites a building
area, so nothing published depends on a footprint and the registry's "authorised, not yet
exercised" still holds.)* `categories.py` says why, in a comment written before any of
this: *"`grocery` below is left exactly as it was, because the published layer is built from it."*

So **nothing published depends on a footprint yet**, and the registry row's own words —
*"authorised, not yet exercised"* — are still accurate. Two sentences I wrote are not:

* ~~"This is the first thing to use footprints for a published classification."~~
* ~~"The published layer is now an ODbL-derived database and so share-alike."~~

Still true, and worth keeping separate: footprints themselves are never republished; the CC BY 4.0
rows still need their own attribution; all 7 surviving corroborating footprints are ODbL-sourced
with **no Esri source**, which the review checked independently.

One nuance the review adds and I had flattened: ODbL distinguishes a **derivative database** from
a **Produced Work**, and *publicly using* a derivative database carries its own obligation to
offer the database. Treating a published classification conservatively as ODbL-derived is sound
project policy; saying it makes "the artifact" share-alike full stop claims more than the licence
does.
