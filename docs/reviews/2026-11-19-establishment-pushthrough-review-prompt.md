---
name: 2026-11-19-establishment-pushthrough-review-prompt
description: "Adversarial review prompt for the sixth pass: 23 records ADDED to the published grocery layer on an owner instruction to go faster, committed before launch"
metadata:
  type: reference
---

# Adversarial review, sixth pass: adding 23 records to a published layer, quickly, on purpose

Committed **before** launch. One reviewer: **Codex** (`gpt-6.1-sol`). The owner declined
Antigravity on 2026-11-19 because headless operation needs `--dangerously-skip-permissions`, and
asked for it again on the same day; the attempt and its result are recorded in
[[../engineering-notes/reference-codex-runtime-quirks]]. **If only Codex runs, nothing independent
is in a position to contradict it, and that limit applies to every finding below.**

## What changed, and why the risk is the opposite shape to last time

The fifth pass reviewed a change that **removed** eleven records from the published `grocery`
layer. This one reviewed a change that **adds 23** and removes 10.

That matters because the asymmetry this project works to is: *a wrong addition sends a household
to a shop that is not there; a wrong refusal leaves the layer as it is today.* Every gate in
`scripts/rebuild_missing_grocery_stores.py` fails closed for that reason. **This change is the
first one that goes the other way in bulk, and it was made quickly on an explicit owner
instruction to stop deliberating:**

> *"Let's push through this qaqc of businesses and establishments more quickly; in the long term we
> will need to think through a robust approach leveraging well vetted resources. For now, let's
> push through and simple note that our data are preliminary."*

So the question for this pass is not only "is each record right" but **"did going faster break the
discipline that made the slow passes worth anything"**.

---

## What to read

Commits on branch `v2-rethink` in `C:\Users\arikt\documents\github\distanceFinder`:

* `41aaae2` — rebuilds ask 5 as a re-runnable screen and adds the inclusion mechanism, empty.
* `de4c17f` — **the push-through.** 23 records admitted to `INCLUDED_PLACE_IDS["grocery"]`, 7 of
  10 held collection bays removed, 3 ask-6 records excluded, all business data declared
  PRELIMINARY. Published `grocery` 542 → **555**.
* the HEAD commit — my own repair of four defects I found by measuring `de4c17f` after pushing it.
  **Read this one carefully: it is the part of this change that has had the least scrutiny.**

Files: `v2/locfinder/places/exclusions.py` (four tables), `v2/locfinder/places/categories.py` (the
chokepoint where inclusions are applied before exclusions), `v2/scripts/rebuild_missing_grocery_stores.py`
(the screen), `v2/tests/test_place_exclusions.py` (49 tests in that module; 1,736 pass in the suite),
`docs/experiments/audit/missing-grocery-stores.csv` (the sheet the entries were generated from),
`docs/engineering-notes/reference-business-data-is-preliminary.md`, and the dated `CURRENT STATE`
block at the top of `docs/engineering-notes/project-phase1-s3-progress.md`.

Background: `docs/reviews/2026-11-19-grocery-layer-exclusions-review-findings.md` is the fifth
pass, whose best finding was that the change under review **never reached the published artifact**.

## Measurements already run, so you can attack the method rather than reproduce them

Codex cannot execute Python on this machine (restricted-token sandbox; see the runtime-quirks
note). These were measured in `EPSG:32617` from `data/triangle/overture_places_accepted.parquet`,
`osm_pois.parquet` and `fsq_os_places_2025-01-10.parquet` on 2026-11-19:

| quantity | measured |
|---|---|
| published `grocery` | **555** (532 with the inclusion table emptied; the 23 are all net new) |
| published `supermarket` | 242, unchanged |
| admitted ids present in the frame and reaching the selection | 23 of 23 |
| seven lifted bays → recorded parent | 0.2, 20.0, 27.4, 63.4, 75.4, 110.7, 249.3 m; every parent published |
| seven lifted bays → nearest OSM `shop=supermarket` Walmart | 4.8, 14.5, 27.6, 46.3, 59.3, 73.4, 245.5 m; all with an open FSQ `Walmart Supercenter` |
| held bay `9011ca8b` → nearest Overture Walmart **store** | 13.67 km — **but OSM `shop=supermarket` 'Walmart Supercenter' at 40.0 m and an open FSQ 'Walmart Supercenter' at 83.4 m** |
| held bay `0f2b2452` → nearest Overture Walmart **store** | 6.06 km — **but an open FSQ 'Walmart Supercenter' at 229.7 m** |
| held bay `fb500d70` → nearest Overture Walmart **store** | 11.78 km, and nothing corroborating a store within 250 m in either other source |
| `aec747a0` → `Total Oriental Foods` | 133.6 m (the **bay** is 147.9 m from it) |

---

## Attack these. Several are mine and may be wrong; do not soften a finding because I predicted it.

1. **THE CENTRAL JUDGEMENT. I added 23 records to a layer households are sent to, fast, because
   the owner said go faster — and the screen that proposed them is a heuristic.**
   The project's own standard, sharpened by a previous pass of yours, is that *discovery by
   heuristic is legitimate provided adjudication is by evidence and owner decision*. The owner's
   instruction was to push through, not "these 20 are correct". I accepted all 20 PROPOSED rows and
   promoted 3 of the 6 REVIEW rows.
   **Argue as strongly as you can that I let a heuristic adjudicate, that the owner's instruction
   to go faster is not the same as an adjudication, and that the correct reading of "push through"
   was to publish the screen and the preliminary declaration while admitting nothing.** If that is
   right, I have converted an instruction about tempo into an authority to change a published
   layer, which is a failure mode no test can catch.

2. **Is "PRELIMINARY" doing any work, or is it a disclaimer that reaches nobody?** Every entry
   carries the word, there is a note declaring the standing position, and a test asserts the word
   is present. **But no household sees any of it**: the published bundle has no field for it, the
   browser overlay does not mention it, and the word appears only in source files and docs.
   Argue that marking the data preliminary in places only a developer reads is self-reassurance,
   that the honest options were to publish the caveat where a household reads it or to not publish
   the additions, and that a test asserting the presence of a word is the clearest possible sign of
   a caveat that has no mechanism.

3. **The repair I am least sure of: two bays are held for a reason that exposes a hole the screen
   cannot see.** `9011ca8b` and `0f2b2452` have a real Walmart Supercenter at the site
   (OSM/FSQ above) that **Overture does not record as a store at all** — the only Overture record
   at each site is the pickup bay. I keep those bays, published, as the household's answer.
   Attack both halves: (a) that keeping a *pickup bay* published as a grocery destination is the
   same error the fifth pass had me remove bays for, now committed deliberately and dressed as
   evidence; and (b) that a screen which can only propose Overture rows is structurally unable to
   find this class, so the "20 missing stores" number is not an estimate of what is missing but of
   *what is missing and also recorded* — and I have nowhere said how large the unrecorded class is.

4. **The 7 lifted bays and the 400 m rule.** The hold said bays leave "together with their
   replacements". I lifted each when a same-brand store was published within **400 m**. Where did
   400 m come from? It is not derived from anything; the measured parents are all within 250 m, so
   the threshold never bound. Argue that an unbound threshold presented as a safeguard is the same
   defect as a gate that is never reached, which this project already named, and that the real rule
   I applied was "the store I just admitted is the parent I recorded", which is circular.

5. **The two `Publix Super Market` records admitted with NO category at all.** Overture gives them
   no primary. I admitted them on the name plus the judgement that a Publix is a weekly shop. No
   OSM or FSQ corroboration is recorded in either entry. Argue that this is the `Family Fare`
   mistake with the sign flipped — a name treated as a brand — and that the same reasoning would
   admit the three `Family Fare` records I refused, and `Manpower at Walmart`, which sits 7.7 m
   from a published record and has no category either.

6. **`Variety Pick-Up`, which I have called the weakest entry in the table.** It was *excluded* on
   its name plus the absence of corroboration. I have a measurement that should worry me: it sits
   at **1830 New Bern Ave**, the same road as held bay `0f2b2452`, in a corridor with nine
   published grocery records. Argue that "no corroborating record" at a dense, well-surveyed
   address is stronger evidence of a data gap than of a non-shop, and that I excluded it for the
   same reason I am *keeping* two bays — which cannot both be right.

7. **The arithmetic and what it is arithmetic about.** 542 + 23 − 7 − 3 = 555, measured 555. But
   `supermarket` is 242 and unchanged, because the inclusion table has a `grocery` key only. So a
   Walmart Supercenter is now a `grocery` and not a `supermarket`. Argue that this is incoherent
   under the owner's own definition (*"a supermarket you could do a weekly shop at"*), that the two
   layers now disagree about 23 records, and that shipping the disagreement because only one layer
   is published is the kind of reasoning that produced the stale-raster problem.

8. **Nothing published has changed, again.** `v2/spikes/g3-render/fixtures/published/own_triangle_grocery_walk.destinations.json`
   is from 2026-11-17 and still contains the Food House and the lifted bays; the grocery rasters are
   stale. The fifth pass found exactly this and it is still true a day later, through two more
   commits. Argue that a change which cannot reach a household is not an improvement, that counting
   `grocery` at 555 describes a selector rather than the product, and tell me whether the honest
   entry in the progress note is "555" or "532 published, 555 selected".

9. **The four defects I found in my own work by measuring it, and whether the repair is enough.**
   I shipped `de4c17f`, then measured it and found: the three held bays described as "standalone
   collection points" when two have a Supercenter at the site; the three km figures each attached
   to the wrong bay; `Total Oriental Foods` quoted at the bay's distance in a sentence about the
   store; and the progress note's dated block still saying all ten bays were held two paragraphs
   above the block saying seven were removed. **All four are the same class — a claim written from
   the search that was run rather than from the thing at the place.** Argue that the repair treats
   four instances and not the class, and name the mechanism that would have caught all four before
   the commit rather than after it.

10. **The tests.** 49 in that module now, 1,736 in the suite. `test_the_inclusion_table_is_populated_and_every_entry_is_preliminary`
    asserts the count is 23, each id is 36 characters, each reason is over 80 characters, and each
    contains the word PRELIMINARY. **Nothing tests that any admitted record is a shop.** The five
    new guards were mutation-checked (five mutations, five caught, log in the commit message), and
    the first version of one of them was vacuous in exactly the way a previous pass of yours caught
    — `"STANDALONE" not in r or "NOT" in r`, where *"NOTHING TO ADMIT"* satisfies the second
    clause. Argue that a suite which pins the shape of strings while asserting nothing about the
    world is worse than no suite, because it reports green over a table of 23 unverified claims.

11. **Free hits.** Anything else: a wrong id, a record that is a department rather than a shop, a
    closure we missed, a duplicate pair, an entry whose evidence does not support its conclusion.
    The sheet at `docs/experiments/audit/missing-grocery-stores.csv` has the full evidence string
    for all 34 screened rows.

---

## How to report

Numbered findings, each with: what is wrong, the evidence, how to reproduce (marked clearly if you
could not execute it), and **how much it matters to a household**, not to the code. Rank by product
risk, per the S3 execution plan §0. Say explicitly where you think I am right — a pass that finds
only faults is as uninformative as one that finds none, and the last one earned its credit by
confirming two things and destroying two others.

**Say plainly if the answer to item 1 is "revert the 23".** That is the finding I would least like
and most need.
