---
name: project-phase1-s3-published-layer-uncorroborated
description: "79 of the 555 published grocery records have no evidence from any source that a shop is there: the reverse screen, what the 79 actually are, and why removing them is not the obvious answer"
metadata:
  type: project
---

# 79 of the 555 published grocery records are uncorroborated

**Date: 2026-11-19.** Screen: `v2/scripts/screen_uncorroborated_grocery.py`. Sheet:
`docs/experiments/audit/uncorroborated-grocery.csv`, 122 rows, `verdict` column empty.
**Nothing has been applied.** All business and establishment data is
[[reference-business-data-is-preliminary]].

## The audit nobody had run

Every screen in this project until today asked **what is missing from the layer.**
`rebuild_missing_grocery_stores.py` proposes additions; `shortlist_brandless_grocery.py` and
`recover_brandless_by_name.py` sort records already inside it. All three take for granted that a
published record is a real shop.

But the asymmetry this project works to says the opposite is the dangerous direction: **a wrong
addition sends a household to a shop that is not there.** So the layer needed a screen pointed at
itself, and it had never had one.

It found its first case before it was written. **`4f318935` is published, and it is named
`Longview Poole Road`** — a road — filed by Overture as `grocery_store` at 2405 Poole Rd, Raleigh.
Within 200 m, OSM has a school and two bus stops and no shop of any kind; within 120 m, Foursquare
has a picture-framing business, a child-care centre and a street. A household routed there is
routed to a residential street.

## What corroboration means here, and what the screen found

A record counts as corroborated when something **other than Overture's own category** says a shop
is at that place: its name or brand field names a chain in `SUPERMARKET_BRANDS` (a lookup, not a
heuristic); or an OSM `shop`-tagged feature within 150 m whose name **agrees** by
`name_match.match_verdict`; or an open Foursquare record within 150 m whose name agrees.

| gate | n |
|---|---|
| published `grocery` | **555** |
| held collection bays, published by owner decision | 3 |
| admitted by owner decision, corroboration already in the entry | 23 |
| brand names a chain in `SUPERMARKET_BRANDS` | 250 |
| OSM `shop` tag within 150 m, name agrees | 46 |
| FSQ record within 150 m, name agrees, no closure recorded in the 2025-01-10 snapshot | 114 |
| WEAK: OSM shop within 60 m, name does **not** agree | 13 |
| WEAK: FSQ grocery category within 60 m, name does not agree | 30 |
| **UNCORROBORATED** | **76** |
| of those, named like a place rather than a shop | 1 |

**ASK 9a APPLIED 2026-11-22, so these figures are now 250 / 46 / 76.** Adding `Wegmans`,
`The Fresh Market` and `Kroger` to `SUPERMARKET_BRANDS` moved **two** records out of
UNCORROBORATED -- `d92ad73b` *Kroger Store* and `a2a12800` *The Fresh Market* -- and moved
nine more from the OSM gate to the earlier brand gate, which is why 239 rose by eleven while
55 fell by nine. **No published number changed: `grocery` 555 and `supermarket` 242 both
stand**, because `classify_grocery` keys that table off the Overture brand FIELD and every
record of all three chains has an empty one. The fourth name in the ask, `Rowe's
supermarket`, was REFUSED as a brand: it is one record whose address is the bare word
"Raleigh", and a table of chains is the wrong home for a single independent. It stays in the
76 and belongs to ask 9b.

**436 of 555 corroborated, 119 for a person, 76 with nothing at all.** That is 14% of the
published layer.

**The first run of this screen said 79 and 54, because it measured to OSM feature CENTROIDS.** OSM
supermarkets are polygons; the sixth review caught the same mistake in the held-bay analysis, where
one bay sits *inside* its store's polygon and was recorded 40 m away from it. Fixed to measure to
the geometry, which moved one record out of the uncorroborated set. A distance is not a number
until the geometry it was measured between is named.

## The 79 are at least three different things, and that is the whole problem

**Removing them as a block would be the same mistake in the other direction.** Reading the names
and addresses separates them:

**(a) Real shops the corroborating sources do not cover.** `Tortilleria Y Carniceria Migueleña`,
`Tienda Mi Ranchito`, `Anchau Oriential Market`, `African Continental Grocery`,
`Bossa Nova Brazilian Market`, `La Costena Market`, `Variedades Orozco`. OSM and Foursquare
coverage of small independent and immigrant-run grocers is patchy — the preliminary note already
says their silence means little — and these are exactly the shops a household without a car most
needs. **Removing one hides a real shop, which is its own harm.**

**(b) Real chains missing from our own lookup table.** `Wegmans`, `The Fresh Market`,
`Kroger Store`, `Rowe's supermarket`. These are corroborated in the world and uncorroborated by
us, because `SUPERMARKET_BRANDS` does not hold them — deliberately: *"adding a chain stays a
decision, not a side effect of a name"*. The screen is right to report them and the table is right
not to have guessed. **This is the one group with a clean, safe action: an owner decision to add
chains to the table.** It would not move published `grocery` at all, since they are already in it.

**(c) Records that are not shops.** (`Roofing Inc.` in this group is also in the **published
browser bundle** today, which the sixth-pass reviewers found independently.) `Roofing Inc.`, **`No longer`** (a record whose name is the
first two words of "no longer in business"), `Longview Poole Road`, `Tower Market Place Partners`
(a property partnership), `McKee Foods Corp` (a manufacturer), `Seal The Seasons` ×2 (a frozen-food
brand), `Aloe Verapol, Llc`, `Body Agape Holistic`, `Insain Hot Sauce` and `KismetCrackers` at
residential addresses, `Bar S Foods` in a corporate suite. Counted by pattern: **12 of the 79 have
a suite or mailbox in the address, 10 carry a company suffix, 6 are farms, greenhouses or a
collard patch**, and those sets overlap. This is the group that actually misroutes households, and
it is **larger than the 23 records admitted today**.

## The proportionality point, stated plainly

Today was spent admitting 23 records to this layer and arguing carefully about ten collection
bays. Meanwhile **79 already-published records have no evidence of being shops, and at least a
dozen of them are plainly not shops.** The careful work was pointed at the smaller number.

That is not an argument against the care — the bay episode produced the invariant that is now a
test. It is an argument about **where to point it next**, and the answer the measurement gives is:
at the layer, not at what is missing from it.

## Owner-owed

1. **Add chains to `SUPERMARKET_BRANDS`?** `Wegmans`, `The Fresh Market`, `Kroger Store` and
   `Rowe's supermarket` are the candidates the screen surfaced. Published `grocery` does not move;
   `supermarket` (not published) does. This is the cheap, safe one.
2. **Triage group (c).** The 79 rows are in the sheet with an empty `verdict`. `--emit` prints
   exclusion entries for rows marked `exclude`, so applying a decision is mechanical. A dozen or so
   are clear-cut; the rest need a person.
3. **Do the WEAK rows deserve the same treatment?** 13 + 30 = 43 records where a shop *is* nearby
   but the name disagrees. That is the shape of the bay defect — a different business at the same
   plaza standing in for the record.

## Related

[[reference-business-data-is-preliminary]] · [[project-phase1-s3-brandless-grocery]] ·
[[feedback-verify-the-shape-of-the-risk]] · [[project-phase1-s3-progress]]
