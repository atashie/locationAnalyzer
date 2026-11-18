---
name: project-phase1-s3-osm-name-floor
description: "The name-agreement floor on the OSM prefill: 0.00 agreement is two different facts, a Jaccard threshold is the wrong knob, and 63% of the grocery proposals were withheld once the floor went in"
metadata:
  type: project
---

# The OSM prefill needed a floor, and not the one that looked obvious

**Owner decision 2026-11-18**, *"1-4) yes, proceed"*, answering the first of the three questions
the FSQ accuracy run raised: *whether to put a name-agreement floor on the OSM prefill*. The floor
is in, in `v2/locfinder/places/name_match.py`, with tests.

## What the accuracy run found, and how much worse it is than that

The accuracy run measured the **comparable set** — the records OSM reached and FSQ also spoke
about — and found **42 of 338 (12.4%)** of OSM's proposals resting on a match with name agreement
0.00, against **3 of 338 (0.9%)** for Foursquare.

> **Corrected:** that sentence first said those 42 *are* a different business. They are not all
> that, and this note is the wrong place of all places to make that conflation, since the next
> section is about 0.00 meaning two things. The 42 are a **mix of `differs` and `unverified`**.
> I have not reproduced the exact split — the accuracy run's filter for the comparable set is not
> the one used below, and running the verdict over the accuracy sheets gives a larger population
> (83 zero-agreement OSM proposals across both categories: 68 `differs`, 14 `unverified`, and one
> `agrees` that only became an `agrees` with the fallback fix described below). So the split is
> stated as a mix rather than replaced with a number I have not checked. Adversarial review
> finding 4.

On the records the prefill is **actually used on** it is much worse, because those are the records
OSM covers badly:

| sheet | proposals | resting on 0.00 agreement |
|---|---|---|
| `grocery-unclassified-prefill.csv` | 117 | **51 (43.6%)** |
| `pharmacy-prefill-from-osm.csv` | 90 | **17 (18.9%)** |

> **The pharmacy row is corrected.** It first read 102 and 29 (28.4%), which was wrong, and wrong
> because of a defect in the script rather than a slip in the note: the "weak" caveat was
> concatenated onto an **empty** proposal, so a pharmacy record matched to an OSM
> `shop=convenience` — a tag with no pharmacy mapping at all — produced a non-empty cell holding
> nothing but the warning. Twelve rows had that shape and I counted all twelve as proposals.
> Found by the adversarial review of 2026-11-18, finding 5. `proposal_text()` now returns the
> empty string when there is no proposal, and a test asserts it.

Of the 51 grocery ones, **25 proposed `supermarket`** — the strongest and most consequential
proposal in the table — from a feature carrying some other shop's name. A sample, all real rows:

| our record | the OSM feature it was read from | distance | it proposed |
|---|---|---|---|
| Flower Gallery | Harris Teeter | 32.6 m | supermarket |
| Cameron Village ABC Store | The Fresh Market | 35.0 m | supermarket |
| El FARO | Food Lion | 0.0 m | supermarket |
| Don julio grill | Speed Mart | 9.5 m | convenience |
| Harris Teeter Supermarkets | Ollie's Surplus | 58.9 m | convenience |
| Walgreens | Rite Aid | 2.2 m | pharmacy *(this row is from the **pharmacy** sheet, not the 51)* |

`Cameron Village ABC Store` is the same row the accuracy run used to retire "FSQ confirms, never
rejects": a state liquor store, proposed as a supermarket off a Fresh Market 35 m away, which FSQ
correctly refused.

The last two rows are the ones worth sitting with. `Harris Teeter Supermarkets` is a supermarket
and got **demoted** to convenience by a surplus store. `Walgreens` matched to a `Rite Aid` 2.2 m
away and the proposal — pharmacy — is **right**, by luck, off a match that is wrong. A floor loses
those accidental right answers, and should: *a proposal is worth what its match is worth.*

## Finding 1: 0.00 is two different facts, so the gate cannot be the number

`name_agreement` returns 0.0 both when two informative names share nothing and when one side has
no informative word at all — an unnamed OSM feature, or a name made only of category words
("Grocery Store"). Those are opposite situations: the first refutes the match, the second says
nobody told us.

Measured on the 0.00 rows:

| | a different business | nothing to compare |
|---|---|---|
| grocery (51) | **42 (82.4%)** | 9 (17.6%) |
| pharmacy (29) | **23 (79.3%)** | 6 (20.7%) |

So the gate is a three-valued verdict — `agrees` / `differs` / `unverified` — and the float is
only ever reported, because a reader disagreeing with the gate needs to see how close the call
was. `unverified` rows keep their tag, distance and agreement in the sheet; they just do not get a
proposal asserted on their behalf.

**My prediction was wrong, and it is recorded because the bar was set before the run.** I predicted
the "nothing to compare" share would be over a third, which would have justified a more elaborate
rule, and named "under a tenth" as the number that would refute it. It came back 17.6% — neither.
The elaborate rule was not justified by my own stated bar, so the simple one stands and the
distinction is printed in the `evidence` column rather than built into the logic. Ledger instance
57, applied the same week it was written.

## Finding 2: a Jaccard threshold is the wrong knob

This is the one that would have gone wrong quietly. The obvious floor is the `0.34` this project
already used for the sheet's "names agree" wording. **It would have been a mistake.** The
partial-agreement band is almost entirely *correct* matches, because our names and OSM's differ by
suffix and spelling rather than by identity:

| our record | OSM feature | distance | Jaccard |
|---|---|---|---|
| Walmart Grocery Pickup and Delivery | Walmart Supercenter | 0.0 m | 0.25 |
| Handee Hugo 77 | Han Dee Hugo | 0.0 m | 0.25 |
| Angadi Halal Meat Market | Angadi - Indian Grocery Store | 28.4 m | 0.25 |
| Apna Bazar | Apna Bazaar | 10.7 m | 0.33 |
| Mikyins Asian Market | Mikyin's Asian Market | 8.3 m | 0.33 |
| Larry's Super Market | Larry's Supermarket | 2.0 m | 0.50 |
| H Mart Cary | H Mart | 2.2 m | 0.50 |

A floor at 0.34 rejects **twelve correct rows** in this band, every one the same shop. The wrong
matches in that band are wrong for an unrelated reason — **they share a generic word**:
`Han-Ah-Rum Mart` / `Han-Dee Hugo's` share `han`, `Tazza Mandi` / `Sabzi Mandi` share `mandi`,
`The Produce Box` / `Ford's Produce Garage` share `produce`.

> **Partly refuted, and the counter-example is better than my claim.** I wrote that a Jaccard
> threshold is simply the wrong knob. The review did the arithmetic I had not: an inclusive floor
> at **0.25** keeps all twelve correct matches *and* rejects `Han-Ah-Rum Mart` / `Han-Dee Hugo's`,
> which scores 1/5 = 0.20, while the correct `Handee Hugo 77` / `Han Dee Hugo` scores 1/4 = 0.25.
> On this sample a 0.25 floor **strictly dominates** the one adopted: one fewer false match, no
> correct match lost. It still misses the other two generic-word cases, and no stricter scalar
> floor catches those while keeping the twelve.
>
> **It is not adopted, and not because it fails.** 0.25 was chosen by looking at the same fifteen
> rows that would judge it, which is how a threshold gets fitted to its own test set. It is
> recorded as a measured option for the owner rather than taken quietly. What survives of the
> original claim is its narrower and more useful half: in this band the *magnitude* of the score
> is not what separates good matches from bad, the *genericness of the shared word* is.
> Adversarial review finding 3.

So the floor is **at least one shared informative word**, and the knob for a false match is the
**stop-word list**, not the threshold. Raising the threshold punishes the good rows to catch three
bad ones.

**Those three are a known residue and are not fixed.** `han` and `mandi` are parts of real business
names and excluding them costs more than they do; two of the three sit at 78.5 m and 83.3 m, which
the distance column already shows.

## What the floor does to the output

Re-run 2026-11-18. The populations shrank legitimately since the sheets were first written — 35
records were classified from them into `OSM_CONFIRMED_SUPERMARKETS` and `OSM_CONFIRMED_SPECIALTY`,
and the twelve FSQ closures came out — so compare the proportions, not the row counts.

```
grocery:  272 records considered
     31 got a proposal from an OSM tag whose name AGREES
      9 of those agree exactly
    148 have no OSM feature within 120 m -- the Yelp backlog
    [gate]     agrees: reached   34, withheld    0
    [gate]    differs: reached   80, withheld   43
    [gate] unverified: reached   10, withheld    7
     50 proposals WITHHELD (61.7% of what would have been proposed)

pharmacy: 397 records considered
     73 got a proposal from an OSM tag whose name AGREES
     69 of those agree exactly
    174 have no OSM feature within 120 m
    [gate]     agrees: reached  107, withheld    0
    [gate]    differs: reached   98, withheld   13
    [gate] unverified: reached   18, withheld    4
     17 proposals WITHHELD (18.9% of what would have been proposed)
```

*(These are the numbers after both review fixes. Before them the grocery run withheld 51 and
reported 63.0%: the extra withholding was the `A&C Supermarket` defect below, which moved one row
from `unverified` to `agrees` and two more from `unverified` to `differs`.)*

## The defect the review found in the floor itself

**`A&C Supermarket` matched against an OSM feature of the same name 12.0 m away, and the floor
withheld the proposal.** Every word in that name is erased: `a` and `c` fall to the length rule,
`supermarket` is a category word, so both token sets came back empty and the code read that as
"nothing to compare". There was plenty to compare. The tokeniser had thrown it away, and
"unverified" was dressing a bug as a category.

Fixed with a fallback rather than a special case for equality, because `A&C Supermarket` against
`A & C Supermarket` has to work too: when the strict pass is empty on either side, both sides are
retried **without the length filter**. The stop list still applies, so `Grocery Store` against
`Food Lion` stays `unverified` — the length rule was never the reason for that one — and `A&C`
against `B&B` now reads `differs` instead of `unverified`, which is also more useful.

While fixing it I checked whether `mart` belongs in the stop list, since it is as generic as
`market`. Measured across both sheets: **exactly one** agreement rests on `mart` alone —
`H Mart Cary` against `H Mart` at 2.2 m, which is correct — so adding it would break the only case
it touches. It stays. That is a hunch checked rather than acted on. Adversarial review finding 2.

**The honest headline is the grocery one: the floor withholds 62% of the proposals.** What is left
is 31 surviving proposals across 272 unclassified grocery records, and 148 of those records have no
OSM feature within 120 m at all.

> **Corrected, and this one matters most.** The sentence first read "63% of the proposals were not
> evidence", which claims more than was measured. 61.7% is the **withholding rate** — the share of
> proposals whose match does not clear the floor. It is *not* an independently measured
> wrong-match or wrong-classification rate, and the two differ in both directions: the withheld
> set includes `unverified` rows that may well be correct, and the surviving 31 include the three
> matches that clear the floor on a shared generic word. "30 usable proposals" overstated the
> survivors for the same reason. Adversarial review finding 4, which is exactly what item 6 of the
> review prompt asked for, so the prompt did its job. The OSM prefill is a much weaker instrument than its output looked,
and it looked strong because a filled cell reads as an answer. Nothing was deleted — a withheld
proposal moves to a `withheld_proposal` column and keeps its row, because it is still the best
lead that record has.

Every gate prints **how often it was reached**, not only what it caught, including a line that says
`NEVER REACHED` in those words. A gate that is never reached otherwise prints a blank that reads as
a clean result; that is ledger instance 47.

## Where it lives, and why it moved

`name_agreement` and `tokens` were defined in `scripts/prefill_from_osm.py` and imported from there
by four other scripts. A threshold that decides what enters a **published** layer's candidate list
is not a script-local helper, so they moved to `locfinder/places/name_match.py` with the floor, the
measurement above and 18 tests. The script re-exports both names, and one of the tests asserts they
are the same objects, so `measure_fsq_accuracy`, `measure_fsq_coverage`,
`crosscheck_fsq_closures` and `shortlist_fsq_pharmacy` keep working unchanged.

## What this does not do

* **It does not re-score anything already admitted.** `OSM_CONFIRMED_SUPERMARKETS` and
  `OSM_CONFIRMED_SPECIALTY` were seeded under a stricter rule than this floor — exact name
  agreement within 100 m — so the floor cannot retroactively admit or reject one of them.
* **It does not touch the FSQ side, in a stronger sense than I first wrote.** The original said
  "the same verdict function applies to them and withholds almost nothing". That is **false as a
  description of what runs**: the FSQ path in `measure_fsq_coverage.py` never calls `match_verdict`
  or `clears_the_floor` at all, so no floor is applied to it and nothing is withheld because
  nothing is gated. What is true is the reason it would not matter much: FSQ's proposals rest on
  0.00 agreement 0.9% of the time against OSM's 12.4%. Adversarial review finding 6.
* **It does not answer whether FSQ should take over the identity pass.** That is still owed, and
  this makes the case for it stronger rather than settling it.
## Third pass, 2026-11-18: the 0.25 floor was adopted, and it nearly reintroduced the bug

Owner, *"1-4) yes, proceed"*. The inclusive 0.25 Jaccard floor the review surfaced is now in, with
the caveat stated rather than buried: **0.25 was chosen by looking at the same fifteen rows that
would judge it.** On the two sheets it costs exactly one proposal and buys exactly one — the same
row, `Han-Ah-Rum Mart` against `Han-Dee Hugo's` 78.5 m away, sharing only the generic `han` and
scoring 1/5. A small, well-understood change, not a breakthrough.

**Implementing it is the part worth reading.** Applied naively to `name_agreement`, the floor
would have rejected `A&C Supermarket` against an OSM feature of the **same name** 12.0 m away —
because the strict tokeniser erases every word in that name and the score is 0.00. That is the
defect the review found one commit earlier, walking back in through a different door, and it was
caught only by measuring the floor's effect on the real sheets before writing it.

So the floor is applied to **`agreement_used`**, the Jaccard over whichever token set the verdict
was actually taken on, and a test asserts the two disagree for that row: `name_agreement` says
0.00, `agreement_used` says 1.00. The `name_agreement` column in both sheets now reports
`agreement_used`, because the evidence text tells a reader to compare it against the floor and it
would otherwise be the wrong number.

After it: grocery **30 proposals surviving, 51 withheld**; pharmacy unchanged at 73 and 17.
