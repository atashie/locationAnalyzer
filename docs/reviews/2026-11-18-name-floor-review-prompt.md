---
name: 2026-11-18-name-floor-review-prompt
description: "Adversarial review prompt for the OSM name-agreement floor and the twelve FSQ closures, committed before launch"
metadata:
  type: reference
---

# Adversarial review: the name-agreement floor, and the twelve closures

Committed **before** the review was launched, so that the prompt cannot be tidied after seeing what
came back. The failure this guards against is ledger instance 56: I once wrote an overstated
guarantee into my own review prompt and handed it to the reviewer as a premise.

Model: `gpt-6.1-sol`. Launched read-only — this is a review, not a fix.

---

## The prompt

You are reviewing two commits on branch `v2-rethink` of this repository, in
`C:\Users\arikt\documents\github\distanceFinder`:

* `80cec78` — applies the last two of twelve Foursquare-derived closures to a published layer.
* `398b501` — adds a name-agreement floor to the OSM prefill, moving the scorer into
  `v2/locfinder/places/name_match.py`.

Read `docs/engineering-notes/project-phase1-s3-osm-name-floor.md` for the claimed measurement and
`v2/tests/test_name_match.py` for what is asserted.

**Be adversarial about the claims, not only the code.** Several of the statements below are mine
and may be wrong. Do not accept any of them because the note states them confidently.

Specifically, try to break these:

1. **The floor's shape.** The claim is that 0.00 agreement conflates "a different business" with
   "nothing to compare", and that only the first should block a proposal. Is `unverified` the right
   side of the line? A row like `Quality Food Mart Cary` sitting 3.7 m from an *unnamed* OSM
   `shop=convenience` now yields no proposal. Is withholding there better or worse than proposing,
   given the sheet is read by a person who can see the 3.7 m?

2. **"A Jaccard threshold is the wrong knob."** I claim a 0.34 floor would reject ~12 rows that
   are the same shop, and that the wrong rows in that band share a *generic* word. Check the
   arithmetic on the table in the note against `tokens()` as implemented. Is there a threshold that
   does better than "one shared word" on BOTH error directions? I did not search for one; I argued
   from a handful of rows.

3. **The stop-word list is now load-bearing in a way it was not.** `STOP_WORDS` contains
   `market`, `store`, `grocery`, `pharmacy`, `supermarket`, `food`, `foods`, `center`. Find a real
   pair of names where this list causes a wrong verdict — ideally one that produces `unverified`
   for two names that plainly identify the same business, or `agrees` for two that do not. The
   `len(w) > 2` rule is also unexamined: it drops `H`, `CVS`? (no — three letters), `BJ`.

4. **The re-export.** `scripts/prefill_from_osm.py` re-exports `name_agreement` and `tokens` from
   the library and four scripts import them from the script. Is there a circular-import or
   `sys.path` hazard in that arrangement, especially given the scripts insert `v2/spikes` and `v2`
   onto `sys.path` at import time?

5. **The closure that was accepted over an unresolved objection.** `c7c31e4e…` (Sam's Club) is now
   removed from a published layer although the stated category objection was never answered: FSQ's
   closed record is categorised as the warehouse club, not a pharmacy counter. The evidence that it
   is gone is *absence in OSM within 300 m*. Argue the other side as strongly as you can: what
   would a household lose if this record is actually a trading club, and is `DROPPED_PLACE_IDS` the
   right mechanism for a record held with this much doubt, versus a flag that keeps it but marks it?

6. **Anything in the note that overstates.** The note says "63% of the proposals were not
   evidence". Is that a fair reading of the measurement, or does it conflate "withheld by the
   floor" with "would have been wrong"? The 51 withheld include rows whose proposal happened to be
   the *right class* off a *wrong match* (`Walgreens` matched to a `Rite Aid` 2.2 m away). Say so
   plainly if the number is being used to carry more than it can.

Report findings as a numbered list, most serious first. For each: the file and line, what breaks,
and the smallest input that demonstrates it. If a claim is correct, say it is correct — a review
that finds nothing is a useful result, and I would rather have that than a manufactured finding.
