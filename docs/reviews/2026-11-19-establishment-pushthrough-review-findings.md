---
name: 2026-11-19-establishment-pushthrough-review-findings
description: "Sixth adversarial pass, TWO reviewers who disagree on the central question: Antigravity says revert the 23, Codex executed the data and says do not. What reproduced, and what my own repair got wrong for the third time"
metadata:
  type: reference
---

# Sixth pass findings: two reviewers, and they disagree

**Committed before any repair.** Prompt: [[2026-11-19-establishment-pushthrough-review-prompt]],
committed before launch. Reviewed `41aaae2`, `de4c17f` and `3859f26`.

* **Codex** `gpt-6.1-sol`, **which executed Python, parquet reads and mutations** — contrary to the
  2026-11-13 note saying it cannot. 11 findings.
* **Antigravity/Gemini** `gemini-4-hydrogen-xhigh`, read-only, no `--dangerously-skip-permissions`.
  10 findings. Both ran independently and neither saw the other's output.

## They disagree about the only question that mattered

| | answer to *"should the 23 admitted records be reverted?"* |
|---|---|
| **Antigravity** | **Yes.** Empty `INCLUDED_PLACE_IDS["grocery"]` and restore the 7 lifted bay exclusions until each store is vetted and the `verdict` column is filled. Keep the mechanism from `41aaae2`. |
| **Codex** | **No.** *"The acceptance process needs repair, but the evidence does not establish that these 23 additions are false. Several accusations in the prompt are contradicted by reproduction."* Hold household publication until the defects are fixed and record what was accepted and why. |

**This disagreement is the most valuable output of the pass**, and it was available only because
there were two reviewers — which the notes had declared impossible a day earlier. Codex reached its
answer by *executing* checks Antigravity could only read: it verified all 23 ids exist and are net
additions, that no admitted pair sits within 200 m of another, that 18 of the 20 proposals carry
both OSM and FSQ support, and it looked up both categoryless Publix stores on Publix's own site
(**Buffaloe Bend #1886**, **Middle Creek Crossings #2031**, the latter with an OSM supermarket
polygon 71.8 m away). Antigravity, reading only, treated the same two records as brand-name
guesses equivalent to `Family Fare`.

**Both agree on the ranking of what matters most**, and it is not the 23: it is that **none of this
reaches a household**, and that **PRELIMINARY reaches nobody**.

## What I reproduced before crediting anything

Measured in `EPSG:32617` from the project's own parquet files. Everything below **reproduced**.

### 1. My own repair contains the same defect it was repairing. Third instance, same day.

`3859f26` corrected the three held bays from "standalone collection points" to "two of three have a
Supercenter at the site". **All three do.** `fb500d70`, the one I called *"the only one of the
three that looks genuinely standalone"*, has:

* an open FSQ **`Walmart Supercenter` at its own address, `4500 Fayetteville Rd`**, 462.9 m away;
* `Walmart Bakery` and `Walmart Pharmacy` at that address, 0.0 m from the bay;
* an OSM `shop=supermarket` Walmart **polygon 413.5 m** away;
* and Walmart's own locator calls it **Supercenter #1372, 4500 Fayetteville Rd**, with grocery
  pickup associated to that store (Codex, EXECUTED, with the retailer page cited).

My search looked 250 m and matched on radius, not on address. **I turned a radius-limited absence
into a site classification** — which is the exact sentence ledger 61 exists to prevent, written by
the person writing the repair for ledger 61.

### 2. A geometry choice I never disclosed produced a false negative.

I measured OSM distances from **feature centroids**. OSM supermarkets are **polygons**:

| bay | polygon distance | centroid distance |
|---|---:|---:|
| `9011ca8b` | **0.0 m — the bay is INSIDE the Walmart polygon** | 40.0 m |
| `0f2b2452` | **209.0 m — inside my own 250 m search** | 270.6 m |
| `fb500d70` | 413.5 m | 485.6 m |

So "no OSM shop-tagged feature within 250 m" for `0f2b2452` is **false**, and the Hillsborough bay
is not 40 m from a Supercenter — it is *in* one. The same defect is in
`screen_uncorroborated_grocery.py`, written today, which also takes `.centroid`.

### 3. `Variety Pick-Up`'s exclusion reason is false.

The entry says no second source says a shop is there. FSQ holds **`Harveys Supermarkets` at
`1830 New Bern Ave`, 16.3 m away, with no closure date** — the record's own address. Also at that
address: a Shell and a Valero fuel pin, and `NYC Grill`. Antigravity found a *different* piece of
evidence I also failed to cite, pointing the other way: our own
`grocery-brandless-footprint-shortlist.csv` records `c8899cfc` inside a **181 m² building**, below
`footprint.py`'s 650 m² floor, which yields `not_a_weekly_shop`. **The decision survives on
evidence that was already on disk; the stated reason does not.**

My prompt's own argument for it was worse: I said it sits "on the same road" as bay `0f2b2452`.
They are **5.2 km apart**. And I claimed a corridor of nine published grocery records; there are
**zero within 500 m**, three within 1 km.

### 4. The screen corroborates stores with the very records we remove as not-shops.

`rebuild_missing_grocery_stores.py` applies `names_a_service_point` to the **Overture** candidate
and never to the **FSQ** row it matches. So **9 of the 14 proposed Walmarts are corroborated by a
department or a bay**: `Walmart Auto Care Centers`, `Walmart Vision & Glasses`, `Walmart Bakery`,
`Walmart Photo Center` — and twice by **`Walmart Grocery Pickup and Delivery`**, which is the exact
record type this project spent two days removing. Visible in the committed sheet.

Codex drove the same hole through `main()` with synthetic input: an Overture Walmart marked
`permanently_closed`, an FSQ Supercenter **closed**, and an FSQ `Walmart Vision & Glasses` with no
closure date at the same coordinate. **The screen returned PROPOSED**, explaining that an optician
established continued trading. *"That conclusion is invented by the code."* A missing `date_closed`
in a January 2025 snapshot means no closure was recorded, not that the shop is open in November
2026.

### 5. The tests pass over a record that does not exist.

Codex replaced an admitted id with the nonexistent UUID `00000000-0000-4000-8000-000000000123`,
keeping the reason and the count. **All 49 tests passed.** The real selection fell 555 → 554. It
then reversed my corrected `Total Oriental Foods` pairing — *"THIS STORE is 147.9 m... its bay is
133.6 m"* — and **all 49 passed again**, because my guard checks for both numbers and the phrase,
not the relationship between them.

Codex's fair qualification, against my own prompt: these tests are **not** worse than no tests —
inclusion precedence and exclusion behaviour are real regression protection. *"Presenting them as
evidence that shops exist is the harmful step."*

### 6. Counts in the material a future session trusts

| claim | measured |
|---|---|
| "every entry repeats the word PRELIMINARY" | **10 of 14** exclusion reasons do |
| preliminary note's table sizes `7 / 9 / 3` | **7 / 28 / 2**, plus 8 `OSM_CONFIRMED_SPECIALTY` and 1 `NOT_A_WEEKLY_SHOP_SITES` unlisted |
| current-state "264 unclassified" | **258** |
| progress note "fifteen corroborated twice over" | **18** |
| my prompt's "34 screened rows" | **33** data rows |
| `686a0d8f`/`b570ea04` parents "admitted via `INCLUDED_PLACE_IDS`" | **neither is in that table**; both were already published |
| `5074229c` "Publix Super Market at Buffaloe **Village**" | **Buffaloe Bend** |
| `c7fee873` "Middle Creek **Commons**" | **Middle Creek Crossings** |
| `HELD_SERVICE_POINTS` header + `test_the_three_standalone_bays_are_still_held` | still assert "6.3, 11.8 and 13.7 km… standalone collection points" — **`3859f26` fixed the entries and not the header or the test name** |
| 23 admitted: `classify_grocery` | **20 `supermarket`, 3 `unclassified`** — and **0 reach the `supermarket` layer** |

### 7. The published bundle, ranked first by both reviewers

`own_triangle_grocery_walk.destinations.json` carries `"built": "2026-11-14 08:28:39"`, **468 place
records across 432 destination nodes**, and still contains the Food House *and* its administration
office at ordinal 105 — an ordinal appearing in **439 published cells**. Across every record
excluded in this chain, affected ordinals appear in **2,358 cells**. Six of the seven lifted bays
are still in it. **Zero of the 23 admitted records are.** `Roofing Inc.` is in it — which my own
uncorroborated screen independently flagged today.

Codex's correction to my own proposed wording: **"532 published, 555 selected" is also wrong**, because
532 is just another selector result. The honest line is **"555 selected; published bundle unchanged
since 2026-11-14"** with the bundle's own counts and date.

### 8. PRELIMINARY cannot reach a household through the current pipeline

Not a missing call — a **closed schema**. `export_published_layers.py` permits exactly
`gers_id, name, brand, category, operating_status, licence`. `persist_selected_destination.py`
writes the same six. `card.js`'s `VERDICT_TEXT` and `ESTIMATE_NOTE` disclose grid geometry and
whole-minute rounding and nothing about the place list. **Rebuilding the bundle would not carry the
caveat.** Both reviewers, independently.

## Where they agree I was right

* The screen in `41aaae2` was the right methodological move, and caught real traps a name filter
  would have shipped: the 2016-closed Durham Walmart, the 2017-closed Harris Teeter, the duplicate
  Lidl, the closed Sam's Club.
* `INCLUDED_PLACE_IDS` / `forced_into` at the chokepoint, with exclusion beating inclusion and
  per-category scoping, is cleaner and safer than widening the `grocery` wedge globally.
* Refusing `Manpower at Walmart`, the three `Family Fare` fuel sites, the Weaver Street office and
  the distribution centre were disciplined, high-precision calls.
* Self-catching the "standalone" error — *"genuine empirical humility"* (Antigravity) — and holding
  the bays rather than erasing a neighbourhood's only Walmart pin is the right instinct on
  coverage, **provided it is a temporary hold while the missing store record is fixed, not a
  permanent reason to publish a parking bay.**
* HEAD's corrected kilometre figures and the 133.6 m / 147.9 m pairing both reproduce. *"It did not
  retire the class of failure"* (Codex) — which is the sentence to keep.

## Related

[[../engineering-notes/feedback-verify-the-shape-of-the-risk]] ·
[[../engineering-notes/reference-business-data-is-preliminary]] ·
[[../engineering-notes/project-phase1-s3-published-layer-uncorroborated]] ·
[[2026-11-19-grocery-layer-exclusions-review-findings]]
