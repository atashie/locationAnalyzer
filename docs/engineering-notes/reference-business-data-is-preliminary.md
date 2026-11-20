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
| `NAME_CONFIRMED_SUPERMARKETS`, `OSM_CONFIRMED_SUPERMARKETS`, `CURATED_INDEPENDENT_SUPERMARKETS` | this record is a supermarket | 7 / 9 / 3 |

## What it is actually built from

Three free sources, cross-checked against each other, and nothing else:

* **Overture Places** — the base. Its taxonomy is the problem as often as the answer: it files a
  Walmart Supercenter under `department_store`, `superstore` or `warehouse_club_store`, and it
  gives some real Publix stores no category at all.
* **OpenStreetMap POIs** — the strongest corroboration available here, because `shop=supermarket`
  is an observation of a shopfront rather than a business-registry inference. Coverage of small
  independent grocers is patchy, so its silence means little.
* **Foursquare OS Places (2025-01-10 snapshot)** — the only source carrying `date_closed`, which
  is what catches a shop that shut years ago. Its category labels are unreliable: it labels one
  distribution centre both *'Retail > Drugstore'* and food retail, and a contract biologics
  manufacturer as a pharmacy.

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
  limit of the current approach and it was found by measurement on 2026-11-19: at
  501 Hampton Pointe, Hillsborough and 4431 New Bern Ave, Raleigh there is a real Walmart
  Supercenter — OSM `shop=supermarket` at 40.0 m in the first case, an open FSQ
  `Walmart Supercenter` at 83.4 m and 229.7 m — and **Overture has no store record for either**.
  The only Overture record at each site is a grocery pickup bay. Those two households are served
  today only because the bay is published, which is the right answer at the right place arrived at
  for the wrong reason. A screen that reads Overture rows can never see this class; only a source
  with its own store list can.
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
