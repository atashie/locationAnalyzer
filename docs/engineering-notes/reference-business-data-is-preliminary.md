---
name: reference-business-data-is-preliminary
description: "Every business and establishment classification in V2 is PRELIMINARY: what that means, what it is built from, and what a robust approach would need instead"
metadata:
  type: reference
---

# Business and establishment data is PRELIMINARY

**Owner instruction, 2026-11-19:** *"Let's push through this qaqc of businesses and establishments
more quickly; in the long term we will need to think through a robust approach leveraging well
vetted resources. For now, let's push through and simple note that our data are preliminary."*

So: **every decision about what a business or establishment IS, in any V2 layer, is preliminary.**
This note is the single place that says so, and every table that carries such a decision points
here. Entries are marked `PRELIMINARY` in their own text so the caveat travels with the record
rather than living only in this file.

## What that covers

| table | what it decides | records |
|---|---|---|
| `EXCLUDED_PLACE_IDS` | this record is not the thing its taxonomy says | 14 |
| `INCLUDED_PLACE_IDS["grocery"]` | this record IS a weekly shop although its taxonomy hides it | 23 |
| `HELD_SERVICE_POINTS` | recorded, deliberately not acted on | 3 |
| `FSQ_CONFIRMED_CLOSURES` | this shop has closed | 12 |
| `PENDING_CLOSURES` | a closure asserted and not acted on | 8 |
| `NAME_CONFIRMED_SUPERMARKETS`, `OSM_CONFIRMED_SUPERMARKETS`, `CURATED_INDEPENDENT_SUPERMARKETS` | this record is a supermarket | 7 / 28 / 2 |
| `OSM_CONFIRMED_SPECIALTY`, `NOT_A_WEEKLY_SHOP_SITES` | this record is specialty, or is not a shop at all | 8 / 1 |

## What it is actually built from

Three free sources, cross-checked against each other, and nothing else:

* **Overture Places** — the base. Its taxonomy is the problem as often as the answer: of the 23
  shops admitted by hand because the `grocery` wedge could not see them, it files **11 as
  `department_store`, 6 as `discount_store`, 4 as `superstore` and 2 with no category at all**.
  The two uncategorised ones are real Publix stores.
* **OpenStreetMap POIs** — the strongest corroboration available here, because `shop=supermarket`
  is an observation of a shopfront rather than a business-registry inference. Coverage of small
  independent grocers is patchy, so its silence means little.
* **Foursquare OS Places (2025-01-10 snapshot)** — the only source carrying `date_closed`, which
  is what catches a shop that shut years ago. Its category labels are unreliable: it labels one
  distribution centre both *'Retail > Drugstore'* and food retail, and a contract biologics
  manufacturer as a pharmacy.

  **A BLANK `date_closed` IN IT IS NOT A REPORT THAT A SHOP IS OPEN.** The snapshot is dated
  2025-01-10, so an empty field means no closure had been recorded by then: twenty-two months of
  silence, not a statement about today. Until 2026-11-22 the proposal screen read that absence as
  “open” and, worse, let it OVERRULE a closure that WAS recorded -- a closed Supercenter beside an
  open optician returned PROPOSED. Ten of the 23 admitted records carried a reason built on it.
  Every claim read out of this file now quotes the snapshot date, so the age of a claim travels
  with the claim, and a test asserts the date matches the filename.

  **A record carrying a brand is not necessarily the shop.** `Walmart Bakery` is a counter,
  `Harris Teeter Parking Lot` is tarmac, `Wal-Mart DC` is a distribution centre, and all three
  clear a name-agreement floor against a record called `Walmart`. Two screens guard this and both
  are HEURISTICS over names rather than lookups, which is why they are listed here:
  `names_a_service_point` (brand-independent -- a `Grocery Pickup` is a bay whoever runs it) and
  `names_part_of_a_store` (brand-qualified, so a standalone `Sunrise Bakery` stays a shop; its
  eleven words were counted off this snapshot rather than guessed).

Google is queried for live validation only and **never persisted as a dataset or used to
calibrate anything** (owner constraint). Nothing is scraped.

## What "preliminary" means in practice

* **Each decision is one table entry to revert**, with its evidence beside it, and a test naming
  which assertions flip.
* **The asymmetry is deliberate and should stay:** a wrong ADDITION sends a household to a shop
  that is not there; a wrong REFUSAL leaves the layer as it was. The first is a new harm, the
  second is the status quo, so the screens fail closed.
* **Some entries are much weaker than others, and say so.** `Variety Pick-Up` was removed on its
  name plus the absence of any corroborating record — the thinnest basis in the whole table, and
  the first thing to revisit.
* **Published counts move with these decisions**, so a count quoted without a date is meaningless.
  See the dated block in [[project-phase1-s3-progress]].
* **A screen over Overture cannot propose a store Overture omits.** This is the sharpest known
  limit of the current approach. At **all three** remaining bay sites — 501 Hampton Pointe in
  Hillsborough, 4431 New Bern Ave and 4500 Fayetteville Rd in Raleigh — there is a real Walmart
  Supercenter, and **Overture has no store record for any of them**. The only Overture record at
  each site is a grocery pickup bay, so those households are served today only because the bay is
  published. A screen that reads Overture rows can never see this class; only a source with its own
  store list can.
* **Measure to the polygon, not to its centroid.** The three sites above were first written up as
  "standalone", then as two-of-three, and both were wrong, partly because OSM distances were taken
  from feature **centroids** while OSM supermarkets are **polygons**. One bay is *inside* its
  store's polygon (0.0 m) and was recorded as 40.0 m away; another is 209.0 m from one and was
  reported as having nothing within 250 m. A distance is not a number until the geometry it was
  measured between is named.
* **A radius is not an address.** The third site was called standalone because a 250 m search came
  back empty. An open Foursquare `Walmart Supercenter` carrying that record's **own street
  address** sat 462.9 m away. Compare the identifiers the record already holds before trusting a
  spatial search.
* **The screens are re-runnable**, which matters more than the current answers:
  `scripts/rebuild_missing_grocery_stores.py` and `scripts/crosscheck_fsq_closures.py` regenerate
  their sheets, so a new Overture release is a re-run rather than a re-litigation.

## What a robust approach would need instead — future work, not started

Recorded so the eventual design starts from the failures already observed rather than from scratch:

1. **A source with an authority claim about operating status.** Every error this project has made
   about a shop was an error about whether it was *there*, not about where it was: a Walmart that
   closed in 2016, a Sam's Club that closed in 2018, a Harris Teeter that closed in 2017. Licensing
   or registry data carries that claim; a POI dump does not.
2. **Identity, not proximity.** The repeated defect has been reading parentage or identity off
   distance — a shop accepted on a neighbour's building, a bay accepted as its own parent store, a
   pickup point standing in for the Supercenter. A robust source has stable entity ids that say
   *these two records are the same business* and *this record is a department of that one*.
3. **Chain names are not brands.** `Family Fare` is a Michigan supermarket and a North Carolina
   petrol-station chain; the name lookup cannot tell them apart. Brand identifiers resolve it;
   string matching never will.
4. **Something that distinguishes a shop from a desk inside a shop.** `Manpower at Walmart`,
   `Walmart Bakery`, `Harris Teeter Pharmacy` and `Weaver Street Market Administration` are all
   sited inside or beside a real shop, and 132 `money_transfer_service` counters carry supermarket
   brand names. The giveaway is never the name alone.
5. **A licence that permits publication.** The current sources were chosen partly for this; any
   replacement has to clear decision 17 and the ODbL reasoning in
   [[../experiments/source-registry]] before it informs a published artifact.

Until that exists, the layers are usable for building and testing the product and **should not be
presented to a household as authoritative.**
