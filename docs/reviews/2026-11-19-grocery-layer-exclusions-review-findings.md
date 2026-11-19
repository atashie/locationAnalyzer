---
name: 2026-11-19-grocery-layer-exclusions-review-findings
description: "Codex findings on removing eleven records from the published grocery layer: the change never reached the published artifact, ask 5 names the wrong stores and one closed in 2016, and the guard test tests nothing"
metadata:
  type: reference
---

# The fifth pass review: findings

Prompt `551fe74`, committed before launch. Reviewer **Codex `gpt-6.1-sol`**, read-only, against
`ae89174`, `aa1dfb0` and `9291014`. Recorded **before any repair**.

**Antigravity was not run.** Owner decision 2026-11-19: headless operation needs
`--dangerously-skip-permissions`, and *"if it requires multiple dangerously-skip-permissions calls
then I do not think it is worth the effort"*. So this pass has **one reviewer, not two**, and the
cross-reviewer disagreement that made pass 56 valuable is absent. Details in
[[reference-codex-runtime-quirks]].

**This is the most damaging of the four reviews, and the first to find the change had not taken
effect at all.** Every finding below marked VERIFIED was reproduced here before being credited.

---

## 1. The change never reached what households see. VERIFIED

`v2/spikes/g3-render/fixtures/published/own_triangle_grocery_walk.destinations.json` still contains
**ten of the eleven** removed records — `Weaver Street Market, Inc` once and
`Walmart Grocery Pickup and Delivery` nine times. Only `Walmart Grocery Pick Up and Delivery`
(`b570ea04`, the one with the different spelling) is absent, and it is absent for an unrelated
reason.

```
grep -o "Walmart Grocery Pickup and Delivery" \
  v2/spikes/g3-render/fixtures/published/own_triangle_grocery_walk.destinations.json | wc -l   # 9
```

Codex reports the removed destinations' ordinals appear in **2,844 published cells**, and the Food
House ordinal in **439** — not counts of households exclusively dependent on them, because an
ordinal can also contain surviving places.

**LEDGER 60, THIRD INSTANCE, IN THE PASS THAT WROTE IT.** The lesson was *measure the end of the
pipeline, not the end of your change*. I measured the selector (`543 -> 532`), checked for a
`data/published` directory, found none, and concluded there was no published artifact to update.
The published fixtures are at `v2/spikes/g3-render/fixtures/published/`. I stopped one directory
short of the thing the whole lesson is about.

**Consequence that cuts the other way, and matters for the decision:** because nothing published
changed, **the removal has caused no household-visible harm yet**, and holding or reverting it
costs nothing today.

## 2. One of the five "verified missing stores" closed in 2016, and our own data said so. VERIFIED

`a61f0a63`, *Walmart, 1010 Martin Luther King Pkwy, Durham*. Codex: store #4369 closed
**2016-01-28**; the building is now Triangle Rock Club.

**Our own FSQ snapshot contained the answer and I never looked.** `fsq_os_places_2025-01-10.parquet`
at that address holds `Walmart Supercenter` with **`date_closed=2022-05-09`**, plus *Triangle Rock
Club*, *Planet Fitness* and *Boys and Girls Club* as current tenants. The 2022 date is not the real
closure date, but it contradicts "verified operating coverage" on its own.

The project has a closure cross-check script built for exactly this and I did not run it against my
own five candidates. **Ask 5 as written would have added a false destination** — the precise harm
the whole pass was about.

## 3. Ask 5 names mostly the WRONG stores. VERIFIED

I told the owner five missing Supercenters explain the coverage lost at the bay sites. They largely
do not. The actual parent stores are recorded as plain **`Walmart`**, which my
`supercenter|neighborhood market` name filter could never match:

| parent record | address | in published grocery | distance to its bay |
|---|---|---|---|
| `88f1168d-25de-48ae-b495-73dde8fe674e` | 3151 Apex Peakway, Apex | **no** | **63.4 m** from `38c97738` |
| `30614a3f-db5b-4c11-94c6-116a59512152` | 2114 S Main St, Wake Forest | **no** | **20.0 m** from `8226f374` |
| `aec747a0-3bc4-4b87-81fe-94fae9b03f24` | 1725 New Hope Church Rd, Raleigh | **no** | **27.4 m** from `cee0e25b` |

Oxford, Chapel Hill and the closed Durham store are **not** the parents of any removed bay. So the
list cannot repair the loss it was presented as explaining. I searched for the shape of a name
instead of for the thing at the place.

Codex's wider accounting, ACCEPTED on its reproductions rather than re-derived here: of the 26
store-category records, **21 credible missing current shops** (15 Walmart, 6 ALDI); **three**
duplicates of published shops (Garner `bf4a3b75`, Brier Creek `136df00e` at ~50.0 m, Lidl
`2f7ca644` at ~99.6 m); one closed (above); one identity error (`e71befb5` says *Wal-Mart* at 4005
Durham Chapel Hill Blvd, which is now **Sam's Club #4831**). Of the six no-primary records, two are
real Publix. And **`specialty_foods_store` holds omitted Whole Foods, Weaver Street and Trader
Joe's**, so **26 was never an upper bound on the missing-shop problem.**

## 4. An entry in the committed table makes a false claim. VERIFIED

`cee0e25b`'s evidence string says the removal *"costs a household nothing here: the shop it
collects for is itself in the layer"*, naming **Total Oriental Foods** at 147.9 m. Total Oriental
Foods is not the Walmart that bay serves. The real parent, `aec747a0` at **27.4 m**, is **not in
the layer**. The sentence is false, and it is false in the direction that made the removal look
cheap.

Cause: my generator branched on `metres <= 150.0` and then asserted parentage from proximity alone.
Proximity is not identity — the same error as the borrowed building, for the third time.

## 5. Two counts in the removal narrative are wrong: it is three and seven, not two and six. VERIFIED

`cee0e25b` sits at **147.9 m**, inside the 150 m threshold I chose.

* bays with a surviving published grocery within 150 m: **3** (I wrote 2)
* bays with none: **7** (I wrote 6)

So **seven** sites lose their only published grocery record, not six — including in the commit
subject of `ae89174` and in every place the ask was restated.

## 6. Destination removal is NOT monotone in reported travel time. VERIFIED

I claimed the stale rasters must understate time-to-grocery because removing a destination can only
lengthen it. Wrong. The router minimises **penalised cost** and reports the chosen route's
**unpenalised time**, so dropping the cost-cheapest destination can select a route that is faster
in reported time. Executed against the real `arrival_seconds_two_weight`:

```python
cost = csr_matrix(([200., 220.], ([0, 0], [1, 2])), shape=(3, 3))
time = csr_matrix(([200., 100.], ([0, 0], [1, 2])), shape=(3, 3))
f(cost, time, dest_idx=[1, 2])[0]   # 200.0
f(cost, time, dest_idx=[2])[0]      # 100.0  <- removal SHORTENED it
```

Codex also drove it through `build_layer_surface`: at a 150 s horizon the removal flips
`BEYOND_HORIZON -> OK`. "Stale" stands; **"understates" does not.**

## 7. The guard test I presented as protection tests nothing. VERIFIED BY CONSTRUCTION

`test_the_published_layer_excludes_by_id_and_never_by_name` builds its frame with `grocery_frame`,
which supplies only `id`, `taxonomy` and geometry — **no `names` field at all**. So the "unlisted
bay-shaped name" it claims to publish has no name. Codex added an in-memory filter rejecting
`names_a_service_point(name)` and **all 33 tests still passed** while a record genuinely named
`Walmart Grocery Pickup and Delivery` was rejected.

I wrote this test today, put it in a commit message as the thing that stops the table becoming a
name rule, and cited it to the owner. It cannot detect that change.

On the design question (prompt item 3) Codex sides with me, with a sharpening worth keeping:
discovering candidates by heuristic does not invalidate an id table **if independent evidence and
deliberate adjudication decide membership**. The prose should distinguish **discovery** from
**adjudication**, and the guard must actually supply the name.

## 8. Judgement: hold the coverage-losing removals. CONTESTED, OWNER'S CALL

Codex takes the case I asked it to make and concludes it succeeds: Walmart pickup supplies
groceries for a weekly shop, so *"a collection bay is not a weekly shop"* is **a policy judgement
about eligible shopping methods, not an established fact about food access**. Its recommendation:
**hold the bay removals, keep the Food House correction**, and ship the removal together with its
replacement parent stores as one operation — *"correctly identifying the subsidiary record does not
justify temporarily erasing the parent's availability."*

Finding 1 makes holding cheap: nothing published has changed yet.

## 9. The Food House removal is incomplete. VERIFIED

`Weaver Street Market Administration` (`4ff51c50`) survives **at exactly the Food House
coordinate**, so removing the production record did not retire the bad destination location.
`Food Line Distribution Center` (`ee14e175`) also survives while our own classifier returns
`not_a_grocery`. Codex agrees `Variety Pick-Up` should be left pending investigation, since its
name alone establishes nothing.

## 10. Smaller corrections. VERIFIED

* **Unclassified is 254, not 264.** I carried the pre-removal number forward into a line labelled
  *current*. The brandless sub-count needs the project's own definition before it is restated:
  Codex reports 253, and counting "unclassified with no `chain_in_name` match" gives **239**.
* **267 brand-named unpublished records was reported without disclosing its filter.** Unfiltered it
  is **347**; 267 is after excluding service-point names. Both reproduce exactly.
* **The stale-raster date range is wrong.** Legacy `own_grocery_*` rasters carry **2026-11-03**
  timestamps; 2026-11-10 to 11-16 describes only the later `own_triangle_grocery_*` artifacts.
* **Family Fare is a real collision, and my description of its reach was wrong.** The 28
  `convenience_store` rows never enter `select_overture(..., "supermarket")` — the taxonomy gate
  rejects them first. The demonstrated promotion is **five Family Fare records tagged
  `grocery_store`**, already in `grocery`; `7a083a11` at 5800 Duraleigh Rd, which sells Shell fuel,
  classifies as `supermarket`. Codex found **no second homonymous-brand collision**, but notes
  Walmart concessions, Harris Teeter pharmacies and a Publix-branded mall all receive `supermarket`
  from the classifier alone, with only the taxonomy gate containing them.

## What survived

* Exactly ten bays plus the Food House were added; `grocery` **543 -> 532**; `supermarket` **242**,
  unchanged; all eleven were already outside `supermarket`.
* Exactly eight tests added, 33 exclusion tests pass, and **both documented mutations reproduce**
  (eleven entries removed -> 6 failures; protected store plus unlisted id excluded -> 2 failures).
* The Garner duplicate and its 33.3 m separation are correct.
* **Every nearest-survivor distance in the eleven entries is right** to within ~0.7 m under an
  independent EPSG:32617 recomputation, and no nearest record was itself removed. Only
  `cee0e25b`'s *interpretation* is false, not its number.
* **The footprint/licence claim holds**, though my `grep -c "m2"` was inadequate evidence for it.
  Codex removed the footprint-derived name table in memory: `grocery` stays **532** while
  `supermarket` falls **242 -> 235**, and the exporter reads precomputed planes. The conclusion
  survives; the verification did not.
* 1,744 tests collected, consistent with 1,720 passed + 24 skipped. Codex did not certify the full
  suite, because parts of it write files and it was told to modify nothing.
