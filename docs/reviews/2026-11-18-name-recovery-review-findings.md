---
name: 2026-11-18-name-recovery-review-findings
description: "Findings of the third adversarial review: 8 of the 13 name recoveries rest on a neighbour's building, the recovery cannot regenerate itself, and the published layer never saw any of it"
metadata:
  type: reference
---

# Findings: the third adversarial review

Prompt: [[2026-11-18-name-recovery-review-prompt]], committed before launch (`aac3f11`). Codex
`gpt-6.1-sol`, read-only, 9m 38s, 94 targeted tests run. Eleven findings, three at P1.

**This is the worst result of the three reviews, and the prompt asked for it.** Item 1 of the
prompt said *"Find one that should not be there... look for one I have not flagged"* and item 7
said *"the previous review caught me conflating two populations in exactly this way."* Both
invitations were taken, and both found something.

**Every finding below that I state as confirmed, I reproduced locally.** The reviewer's numbers
came back identical in four independent places (20 vs 33 candidates, 235 → 248, 543 → 543, and the
four buildings it named). That is why the external claims it makes are credited too.

---

## P1-1. An accepted "supermarket" is the chain's food-production plant

`Weaver Street Market, Inc`, `1e99e399-b118-4d95-8c78-6770a47287c8`, **confirmed**.

Our own record carries the address **`437 Dimmocks Mill Rd Ste 10`** and
`operating_status: "open"`. That address is the co-op's **Food House**: a commercial kitchen, a
meat-processing plant (NC Dept of Agriculture plant **P-317**, processing not slaughter), a bread
and bagel bakery, a pastry bakery and warehousing, which delivers to the co-op's four stores twice
a day. The Hillsborough *shop* is a different address.

So the record is a **supplier**, not a weekly shop, and it is now in a table that says
`supermarket`. The service-point screen passed it because its name contains no forbidden word, and
the 13,127 m² Eno Mill footprint it borrowed proves neither retail access nor identity.

This is the second time the Weaver Street site has produced a wrong destination. The commit message
for `d224945` even says so — about the *Administration* record, which the screen did catch — while
a second record at the same site went through.

## P1-2. The footprint "corroboration" accepts buildings belonging to other businesses

**Confirmed, and worse than the review stated: 8 of the 13, not 4.**

`recover_brandless_by_name.py` takes `max(area)` over buildings **intersecting a 120 m buffer**,
with no containment test and no identity test. Measured, with the building Overture names:

| record | address | winning building | dist | the building the point is *in* |
|---|---|---|---|---|
| Carlie C's IGA | 1514 Garner Station Blvd | *commercial*, 7,339 m² | 117.7 m | 6,942 m² |
| **ALDI** | 4241 Louisburg Rd | **New Hope Baptist Church**, 5,156 m² | 115.0 m | 1,441 m² |
| **Lowes Foods** | 2900 Wake Forest Rd | **Discount Tire**, 837 m² | 105.0 m | **none** |
| Lowes Foods | 3480 Kildaire Farm Rd | *commercial*, 5,228 m² | 85.8 m | **none** |
| **Wal Mart** | 1748 Fordham Blvd | **Europa Center**, 3,943 m² | 80.6 m | **none** |
| **Wal Mart** | 1748 Fordham Blvd | **Europa Center**, 3,943 m² | 66.9 m | **none** |
| Lowes Foods Of Cary On High House | 930 High House Rd | *retail*, 4,064 m² | 25.9 m | **none** |
| Weaver Street Market, Inc | 437 Dimmocks Mill Rd | **Eno Mill**, 13,127 m² | 13.9 m | 1,693 m² |

The review named four of these buildings — New Hope Baptist Church, Discount Tire, and Europa
Center twice — and **our own buildings table carries all four names.** The 837 m² `Lowes Foods` I
had already flagged as "small for that chain" is not a small Lowes Foods at all. It is a tyre shop
105 m away.

**This is the strip-mall failure that killed the footprint-only rule, re-entering through the rule
that replaced it.** `measure_footprint_separation.py` withdrew its positive branch for exactly
this reason on the same day, and then the name rule used proximity as a positive anyway.

## P1-3. Sam's Club: the closure is documented, so the flag is the weaker option

**Confirmed, and it resolves the objection the owner's decision rested on.**

Our record's address is `1101 Shiloh Glenn Dr`. North Carolina's 2018 WARN report records
**Sam's Club #6668, notice 2018-01-11, effective 2018-01-26, 187 employees, closure type
permanent**, at that address. Contemporary reporting adds the detail that settles the category
objection directly: **the pharmacies stayed open about two weeks while prescriptions were
transferred to other boards of pharmacy.**

The objection that held this record back was *"a counter closing inside a club that keeps trading
is indistinguishable in this data from the whole club closing."* The answer is that the **whole
club closed, permanently, on a dated state filing**, and the pharmacy was wound down with it. The
evidence is no longer OSM's silence. It is an affirmative public record.

This is an **owner decision to re-open** — see the ask in the progress note. The review was asked
to argue the drop as strongly as it could, and it won the argument by finding evidence rather than
by arguing.

## P2-4. The recovery cannot regenerate its own table

**Confirmed by measurement: 20 candidates now, 33 with the table emptied in memory.**

`recover_brandless_by_name.py:119` skips any record where
`classify_grocery(rec) != "unclassified"` — which, now that the 13 are in
`NAME_CONFIRMED_SUPERMARKETS`, includes all 13. So `--emit` prints a table **without them** and
following the documented regeneration workflow silently deletes the recovery.

`d224945` calls the table "a regenerable derivation" and puts it on the same footing as
`OSM_CONFIRMED_SUPERMARKETS` for that reason. **The claim was false the moment it was committed.**
A derivation that erases itself on re-run is not regenerable.

## P2-5. "A lookup, not a heuristic" is true of one screen and false of the classifier

**Confirmed as an overstatement.** Chain membership *is* a lookup. The service-point screen and the
geometric acceptance are both heuristics, and the module's own prose claims the discipline for the
whole thing.

Demonstration, outside this metro: `chain_in_name("Norseman IGA and Post Office")` returns `IGA`
and `names_a_service_point(...)` returns `True` — a real combined supermarket and post office,
rejected for the word `office`. The review looked for a local false rejection among the current
candidates and **found none**, so this is a limit of the rule, not a present defect.

## P2-6. The 0.25 floor invariant is correct; the short-token fallback is a pre-existing limit

**The claim I most wanted attacked survived.** `agreement_used >= 0.25` and
`match_verdict == AGREES` agree by construction; the review found no inconsistency across either
sheet or its own probes, and identical `A&C Supermarket` names score 1.0 on the deciding tokens.

The fallback can still approve different initialisms — `A&C Supermarket` vs `A&B Supermarket`
scores 1/3 and returns `agrees`. The review states plainly that this **predates these four
commits** and is not a regression of the floor.

## P2-7. `Wal Mart Supercenter` matches nothing

**Confirmed, and the common historical spelling fails too:**

| name | `chain_in_name` |
|---|---|
| `Wal Mart` | `Walmart` |
| `Wal Mart Supercenter` | **`None`** |
| `Wal-Mart Supercenter` | **`None`** |

The space-insensitive fallback compares the **whole** collapsed name against the brand, so any
descriptive suffix defeats it. A wrong negative is free under the project's asymmetric rule, so
this is P2 — but it is free to fix.

The ordinary word-boundary claim **is** correct: `Rigaud Fine Foods` and `Aldine Supply` do not
match IGA or ALDI, and the review found no wrong-brand selection from longest-first ordering.

## P2-8. The 13 records never reached the published layer

**Confirmed by measurement, and this is the finding that matters most for the record.**

| target | without the table | with it |
|---|---|---|
| `supermarket` | 235 | **248** |
| `grocery` | 543 | **543** |

The published manifest carries `grocery`, `grocery_walk`, `grocery_drive` — **no `supermarket`
layer.** `categories.py` says why, in a comment written before any of this: *`grocery` below is
left exactly as it was, because the published layer is built from it.*

So three claims in `d224945` are wrong:

* that it "writes 13 records into a published grocery layer" — it changes `supermarket` eligibility;
* that it is "the first thing to use footprints for a published classification";
* that "the published layer is now an ODbL-derived database and so share-alike" — **nothing
  published depends on a footprint yet.**

The irony is exact: `d39141e`, the commit immediately before, says **"AUTHORISED, NOT YET
EXERCISED, as of this commit: nothing published depends on a footprint. The next commit changes
that."** That sentence was correct. The next commit did not change that, and claimed it had.

## P3-9. "An eighth" uses the candidate numerator

**Confirmed.** `13 / 272 = 4.8%`, nearer a twentieth. `34 / 272 = 12.5%` is the eighth — the
*candidates*, before either screen. And `323 → 259` puts a brandless starting population against a
total-unclassified ending one. The review also gives the matched figure: the comparable brandless
starting count is **271**, not 272.

## P3-10. The footprint note asserts classifications it did not measure

**Confirmed.** "135 corner shops" is 135 records *sharing a large footprint*, not 135 verified
corner shops — `Brier Creek Walmart` (20,903 m², 27 place records) is in that population and is a
real Supercenter. And the note's claim that the two `Wal Mart` records are "a real Walmart with a
displaced point" is unsupported: the building they borrowed is **Europa Center**.

## 11. The licence reasoning is right in its parts and too broad in its conclusion

Correct: no footprint polygon is republished; CC BY obligations stay separate; all 13 corroborating
footprints are ODbL-sourced with **no Esri source**, and the audit README already credits Esri.

Too broad: using a footprint does not automatically make **every** downstream artifact share-alike.
ODbL distinguishes a derivative database from a Produced Work, and publicly using a derivative
database carries its own access obligation. Treating the classification conservatively as
ODbL-derived is sound policy; the blanket sentence claims more than the licence says.

---

## The lesson

**Measure the end of the pipeline, not the end of your change.** The change ended at
`NAME_CONFIRMED_SUPERMARKETS` and I measured it there: 13 rows, 272 → 259, and a test for each.
The pipeline ends at a published layer that does not consult that table at all, and
`categories.py` said so in a comment I had read.

Ledger 58 was *the code was careful and the prose was not*. This is its sharper form: **I verified
the mechanism and asserted the consequence.** Every number I checked was right. Every number I did
not check was in the sentence that mattered.
