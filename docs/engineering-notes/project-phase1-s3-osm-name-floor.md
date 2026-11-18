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
0.00, a different business, against **3 of 338 (0.9%)** for Foursquare.

On the records the prefill is **actually used on** it is much worse, because those are the records
OSM covers badly:

| sheet | proposals | resting on 0.00 agreement |
|---|---|---|
| `grocery-unclassified-prefill.csv` | 117 | **51 (43.6%)** |
| `pharmacy-prefill-from-osm.csv` | 102 | **29 (28.4%)** |

Of the 51 grocery ones, **25 proposed `supermarket`** — the strongest and most consequential
proposal in the table — from a feature carrying some other shop's name. A sample, all real rows:

| our record | the OSM feature it was read from | distance | it proposed |
|---|---|---|---|
| Flower Gallery | Harris Teeter | 32.6 m | supermarket |
| Cameron Village ABC Store | The Fresh Market | 35.0 m | supermarket |
| El FARO | Food Lion | 0.0 m | supermarket |
| Don julio grill | Speed Mart | 9.5 m | convenience |
| Harris Teeter Supermarkets | Ollie's Surplus | 58.9 m | convenience |
| Walgreens | Rite Aid | 2.2 m | pharmacy |

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

A floor at 0.34 rejects the first five and 12 rows like them, every one the same shop. The wrong
matches in that band are wrong for an unrelated reason — **they share a generic word**:
`Han-Ah-Rum Mart` / `Han-Dee Hugo's` share `han`, `Tazza Mandi` / `Sabzi Mandi` share `mandi`,
`The Produce Box` / `Ford's Produce Garage` share `produce`.

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
     30 got a proposal from an OSM tag whose name AGREES
      9 of those agree exactly
    148 have no OSM feature within 120 m -- the Yelp backlog
    [gate]     agrees: reached   33, withheld    0
    [gate]    differs: reached   79, withheld   42
    [gate] unverified: reached   12, withheld    9
     51 proposals WITHHELD (63.0% of what would have been proposed)

pharmacy: 397 records considered
     73 got a proposal from an OSM tag whose name AGREES
     69 of those agree exactly
    174 have no OSM feature within 120 m
    [gate]     agrees: reached  107, withheld    0
    [gate]    differs: reached   97, withheld   13
    [gate] unverified: reached   19, withheld    4
     17 proposals WITHHELD (18.9% of what would have been proposed)
```

**The honest headline is the grocery one: 63% of the proposals were not evidence.** What is left is
30 usable proposals across 272 unclassified grocery records, and 148 of those records have no OSM
feature within 120 m at all. The OSM prefill is a much weaker instrument than its output looked,
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
* **It does not touch the FSQ side.** FSQ's proposals rest on 0.00 agreement 0.9% of the time; the
  same verdict function applies to them and withholds almost nothing.
* **It does not answer whether FSQ should take over the identity pass.** That is still owed, and
  this makes the case for it stronger rather than settling it.
