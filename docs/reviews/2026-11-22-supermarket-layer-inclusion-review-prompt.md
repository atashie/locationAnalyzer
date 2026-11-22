---
title: "Ask 10: the `supermarket` layer excludes all 23 admitted records. Review the options."
date: 2026-11-22
reviewer: Codex (gpt-6.1-sol), commissioned by the owner
status: prompt, committed before launch
---

# Ask 10, commissioned: how should the 23 admitted records reach the `supermarket` layer, if at all?

The owner answered asks 7-11 on 2026-11-22 and answered **10** with *"have codex review our
options here"*. This is that commission. **You are not being asked to pick the brave option.** You
are being asked to find the option whose failure mode we can live with, and to say plainly which
of the options below is incoherent.

Repo: `C:\Users\arikt\documents\github\distanceFinder`, branch `v2-rethink`. Everything named here
is committed. Read the code, run it, and contradict anything in this prompt that the data does not
support -- **previous passes found errors in the prompt itself, and saying so is the most valuable
thing you can do.**

## The situation, in numbers you should verify rather than trust

* `INCLUDED_PLACE_IDS` in `v2/locfinder/places/exclusions.py` has **one key, `"grocery"`**, holding
  **23** Overture ids. It is consumed at the chokepoint by `forced_into` in
  `v2/locfinder/places/categories.py`.
* `select_overture(places, "grocery")` returns **555** records. `select_overture(places,
  "supermarket")` returns **242**.
* **Zero of the 23 are in the 242.** Of the 23, `classify_grocery` calls **20 `supermarket`** and
  **3 `unclassified`** (`182dc975`, `5074229c`, `c7fee873`).
* So the project's own classifier says 20 of these are supermarkets, and the `supermarket` layer
  does not contain them, because the inclusion table is scoped to `grocery` alone.
* `supermarket` is **not published**. The published browser bundle is a `grocery` walk and is
  unchanged since 2026-11-14. This defect is therefore **latent**, and the owner has just
  authorised a republish (ask 7), which is why it is being decided now rather than later.

## Why the two layers differ, which is the crux

Read `v2/locfinder/places/categories.py` and `v2/locfinder/places/grocery.py` first.

* `grocery` is **taxonomy-based**: it matches Overture's `grocery_store` hierarchy. It never calls
  `classify_grocery`. The 23 exist because Overture files a Walmart Supercenter under
  `department_store`, `superstore` or `warehouse_club_store`, so a real weekly shop never reaches
  the wedge.
* `supermarket` is **judgement-based**: it calls `classify_grocery`, which consults
  `SUPERMARKET_BRANDS` (via the Overture brand FIELD), then the id tables
  `CURATED_INDEPENDENT_SUPERMARKETS`, `OSM_CONFIRMED_SUPERMARKETS`, `NAME_CONFIRMED_SUPERMARKETS`,
  then `SPECIALTY_BRANDS` and `SPECIALTY_PRIMARIES`, and otherwise returns `unclassified`.

`unclassified` is deliberate and is documented as such: it is **not** `supermarket`, because that
would put a corner shop in the weekly-shop layer, and **not** `specialty` either, because nobody
has looked. The project's phrase for the failure it prevents is that asserting a category nobody
checked *"is how `Roofing Inc.` became a grocery"*.

## The options as we see them. Rank them, and add any we have missed

1. **Add a `"supermarket"` key to `INCLUDED_PLACE_IDS`, listing ids by hand.** Explicit, per-record,
   same shape as everything else. Costs a second table that can drift from the first.
2. **Make inclusion copy across categories automatically** -- anything forced into `grocery` is
   forced into `supermarket` too. One edit, no drift. But it silently asserts that a record
   admitted on "a weekly shop could happen here" is also a *supermarket* in the classifier's
   sense, and three of the 23 are records `classify_grocery` declines to classify at all.
3. **Have `supermarket` consult `classify_grocery` for forced records only** -- admit a forced
   record to `supermarket` iff `classify_grocery` returns `supermarket`. That would admit 20 and
   refuse 3, with no new table and no new judgement. Our worry: it makes inclusion mean two
   different things depending on which layer asks.
4. **Do nothing, and record that `supermarket` is knowingly incomplete** until it is published.
   Cheapest and fails closed. Our worry: the incoherence is then load-bearing the moment anybody
   publishes `supermarket`, and the note that explains it will be four months old by then.

## The specific questions

1. **Is option 3 actually coherent?** It is the one we are drawn to and therefore the one we are
   least able to see straight. If "forced into `grocery`" and "is a `supermarket`" are different
   claims, is deriving the second from the first by classifier a sound inference or a dressed-up
   version of option 2?
2. **What happens to the 3 unclassified under each option?** `182dc975` is named
   `Walmart Supercenter` and the classifier still returns `unclassified` for it -- work out why,
   because we think the reason is that its Overture brand field is empty and it is on none of the
   id tables, and if that is right then option 3 refuses a record whose NAME states the chain.
3. **Does any option move a number in the published `grocery` layer?** It must not. The republish
   in ask 7 is about to bake whatever `grocery` returns into a household-facing artifact, and a
   change to `supermarket` that leaks into `grocery` is the worst outcome available here. Check
   `forced_into` and the exclusion-beats-inclusion precedence, and try to break it.
4. **Is there a test that would catch each option going wrong?** `v2/tests/test_place_exclusions.py`
   holds 55 tests on this table, four of them added 2026-11-22 after we found that **rewriting all
   twenty generated reasons broke none of the previous fifty-one** -- they asked whether a reason
   existed, never what it claimed. Assume our tests are weaker than they look and try to pass a
   wrong implementation through them.
5. **Mutate.** Change `forced_into`, change the category scoping, change the precedence, and tell
   us which mutations the suite does not catch.

## Constraints that are not open to review

* **Nothing is applied by you.** Adding a record to a published layer moves a published number
  upward and is the owner's decision. Report, do not edit.
* **Exclusion beats inclusion**, always, and inclusion is per-category by design. If you think the
  design is wrong, say so, but do not assume it away.
* **Adding a chain stays a decision**, never a side effect of a name.
* Owner constraint: Google is for live validation only, never persisted as a dataset and never used
  to calibrate anything. Nothing is scraped. Overture and Google must never feed an ODbL artifact.

## What we think we already know, for you to attack

* That option 4 is what an honest reading of the asymmetry recommends, because `supermarket` is
  unpublished and every other option asserts something new about 20 or 23 records in order to fix
  a layer nobody reads yet.
* That the reason this is not simply option 4 is ask 7: the republish makes the two layers'
  divergence a thing that will be baked into an artifact rather than a thing in a notebook.
* That option 1 is the shape the rest of this project uses and is therefore the one we would pick
  on precedent rather than on reasoning -- which is exactly the kind of choice these passes exist
  to catch.
