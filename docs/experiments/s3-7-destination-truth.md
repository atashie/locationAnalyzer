# S3.7 — the grocery destination screening pass

**2026-11-13, rewritten the same day after Codex pass 45.** Step 7's destination half.
`v2/scripts/audit_destination_truth.py`, `docs/experiments/s3-7-destination-truth.json`, the sheet
`docs/experiments/audit/s3-7-destinations-to-check.csv`, review in
`docs/research/46-codex-review-pass45-counterexamples/`.

**This is an automated screening pass with validation outstanding.** The first version of this
document called it a truth audit and reported three findings as established. Pass 45 reproduced
every number and refuted several of the interpretations, including two of my own premises. The
corrections are marked where the wrong claims stood.

**What the design says this is for.** E1 and E2 compare our pipeline against an engine, and both
sides read the **same destination list**. A grocery that is closed, absent, misplaced or missing
produces perfect agreement and two wrong answers. Design §3 states that blind spot. This screens
for candidates; it does not verify any of them.

---

## 1. Nine records carry a closure flag, and nothing in the pipeline reads it

Overture publishes an `operating_status` per place and a `confidence`. **Neither is read anywhere
in this pipeline.** Of the 550 grocery destinations: 435 `open`, 106 with no status, **9
`permanently_closed`**.

Each flag's provenance is recorded per property, which matters — a field with a named source and
date is better evidence than a bare boolean:

| record | confidence | flag source |
|---|---|---|
| Kroger | 0.92 | Overture-signals, 2026-10-13 |
| the other eight | 0.55–0.65 | BrightQuery, 2026-10-14 |

The eight are La Tiendita Market, Kinstar International Food, Carolina Cupboard, Longview Poole
Road, Bell Tower Mart, Jinja Fair Trade, La Nueva Mexicana and **"Roofing Inc."** — which is a
category error as well as a flagged one.

> **Withdrawn (pass 45 F1): "nine closed grocery destinations".** That treats one Overture field as
> ground truth, and I never bounded its error rate. The repository contains evidence pointing the
> other way, which the first version omitted:
>
> | flagged record | an **open** destination already in our list | OSM at the site |
> |---|---|---|
> | Kroger | **Harris Teeter, 16 m — same destination node** | `shop=supermarket`, Mo–Su 06:00–23:00 |
> | Carolina Cupboard | Southern Season, **0 m**, same node | — |
> | Kinstar International Food | Little India, 20 m | `shop=convenience`, 10:30–21:00 |
> | La Tiendita Market | Green Berry Llc, 29 m | `shop=supermarket` |
>
> A different successor name **supports** closure of the old business and says nothing about
> grocery service at that site. So this establishes nine flagged **records**, not nine unusable
> destinations, and the measurement below is renamed the effect of **removing nine flagged
> records**. Removing all nine deletes **7 destination nodes**, not nine, because two of them share
> a node with a record that stays.
>
> "Needed no walk and no external source" described **discovering the flags**. Verifying them needs
> someone who can look.

### What removing them does, in both directions and at both units

| *T* | included as published | removing the 9 flagged records | requiring explicitly `open` |
|---|---|---|---|
| 10 min | 78,627 | **−1,473 / +14** | −11,962 / +11 |
| 15 min | 162,699 | −1,979 / +0 | −16,867 / +29 |
| 25 min | 298,236 | −963 / +0 | −11,811 / +18 |
| 45 min | 424,650 | −0 / +0 | −4,832 / +0 |

Evaluated at the **centre of the cell each structure falls in** — what the product actually
publishes for it — the first column becomes −1,568 / +9 at ten minutes and −2,073 / +0 at fifteen.

**The strict counterfactual is an order of magnitude larger, and that is the interesting part.**
Requiring `operating_status == "open"` drops the 106 records with **no** status too — 99 nodes — and
costs 11,962 structures their inclusion at ten minutes. So the missing-status records carry a great
deal of the published answer, and any `operating_status` policy has to say what it does with
absence, not only with closure.

`confidence` is also unread: it runs from 0.165 to 1.0, with 24 places below 0.5 and 6 below 0.3. A
distribution cannot establish a safe threshold; that needs source-stratified validation and is not
done here.

---

## 2. Brand coverage: five chains absent, and one real within-brand split

> **Corrected (pass 45 F2).** The first version's matcher was `brand.lower() in name.lower()`
> filtered to primaries including `None`. It counted **Mariachi Garib-ALDI- NC** as an omitted Aldi
> branch, **TARGET PharmaSolutions** (a pharmaceutical company) as a Target, and **Harris Teeter
> Fuel Center** as a Harris Teeter. It also admitted **Weaver Street Market Administration** as a
> destination on the other side of the wedge. Matching is now whole-word with a not-the-store name
> filter, and the brand list has been widened with chains that are present **and selected** —
> Lowes Foods, Carlie C's, Save A Lot — because the first list contained only chains I expected to
> fail, which made the table a list of failures rather than a coverage picture.

**No store row in the destination list at all:** Target (15 rows, all `department_store`), Costco
(3: `wholesale_grocer` ×2, `warehouse_club_store`), Sam's Club (2: `warehouse_club_store`), BJ's
(5: `wholesale_grocer` ×4, `warehouse_club_store`), Chatham Marketplace (1:
`specialty_foods_store`), and one `Wal-Mart` row (`superstore`).

**Store rows on both sides:** Publix, Kroger, Aldi, Lidl, Trader Joe's, Whole Foods, Walmart,
Weaver Street, Compare Foods.

> **Withdrawn: "nine chains split across the wedge".** Rows on both sides is not the same as a
> chain whose **branches** are split, and pass 45 checked each one. Harris Teeter's only excluded
> row was the fuel centre, so it is no longer in the table at all. **Lidl's** excluded store shares
> an address with an *included* record whose brand is Lidl — that branch is already represented.
> **Kroger's** excluded record sits 13 m from an included Harris Teeter, so its current identity is
> unresolved rather than omitted.

**What survives, and it is the sharpest single fact here: Walmart.** Fourteen Walmart-branded rows
**are** destinations — the Neighborhood Market format — while twelve store rows are not, including
**4 tagged `superstore`**. So the pipeline treats one format of one chain as a grocery and another
format of the same chain as not a grocery, on a taxonomy string. Aldi is the same shape: 9 branches
in, 5 more as `discount_store`. Whole Foods: 1 in, 5 as `specialty_foods_store`.

### What a brand-based definition would cost

57 store rows, adding **53 destination nodes**:

| *T* | gained | **lost** |
|---|---|---|
| 10 min | +3,912 | **−69** |
| 15 min | +6,325 | −32 |
| 25 min | +8,243 | −5 |
| 45 min | +5,947 | −0 |

**I have not changed the definition, and the price list above is not a sufficient basis for
changing it.** `discount_store` holds 195 places inside the footprint, almost all dollar stores;
`convenience_store` holds 464 petrol-station shops. Admitting a taxonomy wholesale is a different
error from the one it fixes. The brand list is 27 names drawn from this extract, it counts
**records rather than physical stores** — nothing here deduplicates two rows for one shop — and it
still carries a genuine collision ("Las Carolinas Fresh Market" really does contain "Fresh
Market"). What it supports is **examples of taxonomy inconsistency**, not a balanced inventory of
what households would call a grocery.

---

## 3. Adding or removing a destination moves answers in **both** directions

> **Withdrawn (pass 45 F3), and this one is mine twice over.** The impact function's docstring
> said "removing destinations can only lengthen a time, and adding them can only shorten one". That
> is false, and the reason is this project's central distinction: **the search minimises cost and
> reports time**, so a cheaper destination can select a slower journey. Three lines show it — on
> costs `(700, 650)` with times `(500, 650)`, adding the second destination turns **500 s into
> 650 s**, a ten-minute pass into a fail.

Measured: the brand addition **removes** inclusion from 69 structures at ten minutes while adding
3,912. Removing the flagged records **gains** 14 while losing 1,473, so the net is 1,459. Every
figure in this document now carries both directions, and "served only by" is gone — a cost-selected
verdict difference does not prove what qualifying routes were available.

---

## 4. Resolution: measured, and it does not settle what I said it did

| | |
|---|---|
| places snapping within the 300 m cap | 549 of 550 |
| dropped by the cap | 1 |
| between 200 and 300 m from a node | 1 |
| distinct road nodes | 510 |
| places sharing a node with another | 75 |
| largest number on one node | 3 |

> **Withdrawn: "resolution is not the problem".** This measures proximity to road nodes and nothing
> else. It does not establish correct store coordinates, entrance access, distinct retail
> identities, or that a place qualifies. The 75 shared-node places have equal model times **because
> the representation makes them equal**, which supports "no time distinction in this
> representation" and not "no resolution problem" — and the Publix whose Overture and OSM records
> sit **354 m** apart is an unresolved coordinate question of exactly this kind.

---

## 5. Coverage against OSM: 28 unmatched records, and the heuristic cuts both ways

OSM is an independent free source already on disk, so the lists can be compared without scraping.
Inside the published footprint: 455 Overture grocery places, 233 OSM `shop=supermarket` or
`greengrocer`. Half the OSM shops sit within **17 m** of an Overture grocery. **28 are more than
300 m from any.**

| *T* | gained if all 28 are real | lost |
|---|---|---|
| 10 min | +4,551 | −1 |
| 15 min | +6,455 | −5 |
| 25 min | +7,450 | −0 |

> **Qualified (pass 45 F5): 28 is a count of spatially unmatched records under a heuristic, not an
> upper bound on omissions.** `SAME_SHOP_M = 300` was justified as the destination snap cap, but a
> point-to-**node** acceptance radius is not a point-to-**point** identity rule: two points 400 m
> apart can both snap to a node between them. And the heuristic **hides** real omissions, because
> proximity to an *unrelated* selected grocery suppresses a genuine identity disagreement:
>
> | OSM store | its rejected Overture counterpart | the unrelated grocery masking it |
> |---|---|---|
> | Whole Foods Market | 5.2 m | Market at Colonnade Center, 141 m |
> | Trader Joe's | 12.0 m | Wegmans, 299 m |
> | Aldi | 14.2 m | Food Lion, 273 m |
> | Weaver Street Market | 21.6 m | Harris Teeter, 139 m |
>
> So at least four rejected store identities are masked, while the Publix pair 354 m apart is
> counted as unmatched. The bias runs both ways.
>
> **And the acquisition itself is narrower than the selector.** `v2/scripts/fetch_places.py` never
> requests `shop=grocery` at all, so changing `select_osm` cannot recover that stratum — it was
> never downloaded. The reverse-direction figure (197 Overture groceries more than 300 m from any
> OSM supermarket) was explained as "mostly definitional"; that explanation remains **unmeasured**.

**Candidates, not findings.** OSM's own `shop=supermarket` here includes "Tar Heels Termite
Removal" and "Wiley's Workshop on Wheels", both `opening_hours=24/7`. The 28 rows go to
`docs/experiments/audit/s3-7-destinations-to-check.csv` with name, brand, operator, street, hours
and coordinates plus blank `is_a_real_grocery` / `checked_on` / `note` columns. Nothing is added to
the destination list on this evidence.

### The two candidate additions overlap; they do not add

| *T* | gain from OSM | gain from brands | **in both** | in either |
|---|---|---|---|---|
| 10 min | 4,551 | 3,912 | **2,490** | 5,973 |
| 15 min | 6,455 | 6,325 | 4,409 | 8,371 |
| 25 min | 7,450 | 8,243 | 5,454 | 10,239 |

Measured rather than asserted: the top of the OSM sheet — Weaver Street, Publix, Walmart, Aldi — is
the same category question wearing a different hat. These are intersections of two separately
measured gain sets, not a measurement of one joint amendment.

---

## What is owed

* **Validation, before any filter.** The nine flagged records should **not** be filtered on this
  evidence. An amendment needs either corroboration per record or a measured error rate for the
  field, and it must say what it does with the 106 records that carry no status — which cost
  11,962 structures at ten minutes if excluded.
* **The grocery definition decision**, with §2 as examples of inconsistency rather than a price
  list. The Walmart case — one format of a chain in, another out — is the clearest single instance.
* **28 rows checked** by someone who can look, plus the four masked identities in §5.
* **A `confidence` policy** or an explicit decision not to have one, with source-stratified
  validation if it becomes a filter.
* **`shop=grocery` acquired**, so the OSM comparator can be what it claims to be.
* **The geocoding half** — whether a household's address resolves to the right cell — is not
  started.
* Nothing here measures whether an **open** store is usable on arrival. That remains the walked
  audit, the only check that consults the world.
