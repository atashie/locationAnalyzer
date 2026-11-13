# S3.7 — the grocery destination truth audit

**2026-11-13.** Step 7 of the S3 execution plan's §0. `v2/scripts/audit_destination_truth.py`,
`docs/experiments/s3-7-destination-truth.json`, and the sheet
`docs/experiments/audit/s3-7-destinations-to-check.csv`.

**The failure class no estimand in this design can see.** E1 and E2 compare our pipeline against an
engine, and both sides read the **same destination list**. A grocery that is closed, absent,
misplaced, or missing from the list produces perfect agreement and two wrong answers. Design §3
states that blind spot; this measures it.

Two findings are defects. One is a decision that is not mine to make.

---

## 1. The product routes households to closed groceries, and our own data already said so

Overture publishes an `operating_status` for every place. **Nothing in this pipeline reads it.** Of
the 550 grocery destinations:

| `operating_status` | places |
|---|---|
| `open` | 435 |
| *absent* | 106 |
| **`permanently_closed`** | **9** |

All nine are published as destinations:

| name | confidence |
|---|---|
| Kroger | **0.92** |
| La Tiendita Market | 0.65 |
| Kinstar International Food Inc | 0.65 |
| Longview Poole Road | 0.65 |
| Bell Tower Mart | 0.65 |
| Jinja Fair Trade Llc | 0.65 |
| La Nueva Mexicana | 0.65 |
| **Roofing Inc.** | 0.65 |
| Carolina Cupboard | 0.55 |

"Roofing Inc." is a category error as well as a closed one — it is in the grocery taxonomy.

**Measured impact over all 512,633 structures:**

| *T* | included as published | included **only** because of a closed grocery |
|---|---|---|
| 10 min | 78,627 | **1,473** |
| 15 min | 162,699 | **1,979** |
| 25 min | 298,236 | 963 |
| 45 min | 424,650 | 0 |

So about 1,500–2,000 structures are told they are within ten or fifteen minutes of a grocery when
the only qualifying store is one Overture marks permanently closed. This is the design's own
"closed grocery passes E1 and E2" example, and it needed **no walk and no external source** — only
reading a field we had already ingested.

`confidence` is also unread: it ranges down to 0.165, with 24 places below 0.5 and 6 below 0.3.
What threshold, if any, to require is a separate question and is not answered here.

---

## 2. Whole supermarket brands are not destinations, and nine chains are split in half

This is the decision, and it is the owner's.

The grocery wedge requires Overture taxonomy hierarchy `grocery_store`. Checking brand by brand
against what is actually in this extract — every row below is a store that exists here:

| brand | in the destination list | store rows not in it | their Overture primary |
|---|---|---|---|
| Walmart Supercenter | **0** | 3 | `superstore`, `department_store`, `warehouse_club_store` |
| Target | **0** | 16 | `department_store` ×16 |
| Costco | **0** | 3 | `wholesale_grocer` ×2, `warehouse_club_store` |
| Sam's Club | **0** | 2 | `warehouse_club_store` ×2 |
| BJ's | **0** | 5 | `wholesale_grocer` ×4, `warehouse_club_store` |
| Whole Foods | 1 | 5 | `specialty_foods_store` ×5 |
| Aldi | 9 | 6 | `discount_store` ×5, none ×1 |
| Weaver Street | 3 | 3 | `specialty_foods_store` ×3 |
| Lidl | 7 | 1 | `discount_store` |
| Trader Joe's | 4 | 1 | `specialty_foods_store` |
| Kroger | 3 | 1 | `department_store` |
| Harris Teeter | 44 | 1 | none |
| Publix | 9 | 1 | none |
| Compare Foods | 4 | 1 | `specialty_foods_store` |

Overture **has** all of these. Spot-checked by coordinate: Weaver Street Market sits 7 m from its
OSM point as `specialty_foods_store`, Walmart Supercenter 19 m away as `superstore`, Aldi 9 m away
as `discount_store`. The gap is our category definition, not the data.

**The part that is not merely conservative.** Nine chains appear on *both* sides of the wedge —
Harris Teeter, Publix, Kroger, Aldi, Lidl, Trader Joe's, Whole Foods, Weaver Street and Compare
Foods. Overture tags some branches `grocery_store` and others `discount_store` or
`specialty_foods_store`, so **our destination list admits some branches of a chain and not
others**. Two households the same distance from the same chain get different answers, for a reason
neither the design nor the data intends. That is arbitrary, not cautious.

**Measured impact of a brand-based definition** — 49 store rows added, restricted to primaries that
can be the store itself rather than a concession inside it:

| *T* | structures that would gain |
|---|---|
| 10 min | 4,318 |
| 15 min | 7,128 |
| 25 min | 10,411 |
| 45 min | 5,566 |

**Why I have not changed the definition.** `discount_store` holds 195 places inside the footprint,
almost all dollar stores, and one of them is Aldi; `convenience_store` holds 464, which are
petrol-station shops. Admitting a taxonomy wholesale would be a different error from the one it
fixes. And what counts as "a grocery" changes every published number, so it is an estimand-adjacent
decision that §0's own prohibition reserves for a design amendment. The options are priced above;
the choice is the owner's.

A brand list is also not a general rule — it is 21 names drawn from this extract. A durable fix
needs either a taxonomy set the owner endorses, or a brand list maintained as data with its
provenance recorded.

---

## 3. Resolution is not the problem

| | |
|---|---|
| places snapping within the 300 m cap | 549 of 550 |
| dropped by the cap | 1 |
| between 200 and 300 m from a node | 1 |
| distinct road nodes serving them | 510 |
| places sharing a node with another | 75 |
| largest number of places on one node | 3 |

So 75 places are indistinguishable from a neighbour in the published answer — the layer reports the
cost-selected one and cannot name which. That matters for the manifest, not for the seconds.

---

## 4. Coverage against OSM: 28 candidates, and the mechanism is mostly §2

OSM is an independent free source already on disk, so the lists can be compared without scraping.
Inside the published footprint: 455 Overture grocery places, 233 OSM `shop=supermarket` or
`greengrocer`.

Half of the OSM shops sit within **17 m** of an Overture grocery, which is good agreement. **28 are
more than 300 m from any** — the destination-snap cap, so beyond it they would be different
destinations to this pipeline anyway.

| *T* | structures that would gain if all 28 are real |
|---|---|
| 10 min | 4,551 |
| 15 min | 6,455 |
| 25 min | 7,450 |
| 45 min | 5,595 |

**Candidates, not findings, and the sheet says so.** OSM's `shop=supermarket` in this extract
includes obvious mistags — "Tar Heels Termite Removal" and "Wiley's Workshop on Wheels", both
`opening_hours=24/7`. The 28 rows are written to
`docs/experiments/audit/s3-7-destinations-to-check.csv` with name, brand, operator, street, opening
hours and coordinates, plus blank `is_a_real_grocery` / `checked_on` / `note` columns. Nothing is
added to the destination list on this evidence.

The reverse direction — 197 Overture groceries more than 300 m from any OSM supermarket — is
**mostly definitional, not evidence of nonexistence**: the Overture selector admits ethnic and
organic grocery stores through the taxonomy hierarchy, and OSM tags those `shop=convenience`,
`shop=grocery` or a deli.

And the top of the sheet is not mistags: Weaver Street Market, Publix At Buffaloe Bend, Walmart
Supercenter, Aldi. Those are **the same stores as §2** — Overture has them under a rejected
taxonomy. So most of the 28 is the category-definition question wearing a different hat, and the
two impact figures overlap rather than adding.

---

## What is owed

* **A design amendment for `operating_status`.** Filtering `permanently_closed` is not a policy
  anyone chose — nobody decided to route households to shut shops — but it changes which
  destinations are eligible, so §0's prohibition makes it an amendment with a §13 row rather than
  a silent fix. Drafted, not adopted, following step 2's precedent.
* **The grocery definition decision**, with the table in §2 as its price list.
* **28 rows checked** by someone who can look, which is the owner.
* **A `confidence` policy**, or an explicit decision not to have one.
* Nothing here measures whether an *open* store is actually usable on arrival. That is the walked
  audit, and it remains the only check that consults the world.
