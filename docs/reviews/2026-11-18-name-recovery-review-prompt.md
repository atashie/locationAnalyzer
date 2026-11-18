---
name: 2026-11-18-name-recovery-review-prompt
description: "Adversarial review prompt for the name-based recovery, the closure flag and the 0.25 floor, committed before launch"
metadata:
  type: reference
---

# Adversarial review: the third pass

Committed **before** launch. The previous review (`2026-11-18-name-floor-review-prompt`) found two
real defects and four overclaims that my own tests had missed, so this one is written in the same
spirit: the items below are the places I think I am most likely to be wrong, not the places I am
confident.

Model: `gpt-6.1-sol`, read-only.

---

## The prompt

Review four commits on branch `v2-rethink` in `C:\Users\arikt\documents\github\distanceFinder`:

* `2c322c8` — adopts a 0.25 Jaccard agreement floor.
* `6aba508` — turns one FSQ closure from a drop into a flag.
* `d39141e` — widens the Buildings licence registry row.
* `d224945` — **reads chain names out of the `name` field and writes 13 records into a published
  grocery layer.** This is the one that changes what households see; weight it accordingly.

Read `docs/engineering-notes/project-phase1-s3-brandless-grocery.md` and
`project-phase1-s3-osm-name-floor.md` for the claims, and
`v2/tests/test_grocery_name_recovery.py` for what is asserted.

**Attack these specifically. Several are mine and may be wrong; do not accept them because they
are stated confidently.**

1. **The 13 records now in `NAME_CONFIRMED_SUPERMARKETS`.** Each was accepted because its name
   carries a chain from `SUPERMARKET_BRANDS`, it is not a service point, and a building over
   650 m² stands within 120 m. **Find one that should not be there.** The `Lowes Foods` on an
   837 m² building and the two `Wal Mart` records sharing one 3,943 m² building are the ones I
   already doubt — but look for one I have not flagged. What happens if the nearby large building
   belongs to a *different* business, which is exactly the strip-mall failure that broke the
   footprint-only rule?

2. **The service-point word list is a heuristic wearing a lookup's clothes.** `SERVICE_POINT_WORDS`
   contains `pharmacy`, `fuel`, `vision`, `photo`, `office` and others, chosen by me from looking
   at 34 rows. Find a real grocery whose name this list would wrongly reject — a `Market Office
   Park`, a shop with `Vision` in its name. Is the claim "this is a lookup, not a heuristic"
   honest given this list exists?

3. **`chain_in_name` matching.** It normalises punctuation away and matches whole words, longest
   brand first, plus a space-insensitive equality fallback for `Wal Mart` / `Walmart`. Find a name
   where that fallback over-matches, or where the longest-first ordering picks the wrong brand.
   `IGA` is three letters and `ALDI` four — are the word-boundary rules actually tight enough?

4. **The flag is weaker than the drop for a household, and I claim it is better for the project.**
   `FSQ_FLAGGED_CLOSURES` keeps Sam's Club in the layer and nothing renders the flag, so a
   household is routed to a probably-closed pharmacy with no warning. Argue that this is the wrong
   trade and that the drop was right, as strongly as you can.

5. **The 0.25 floor and `agreement_used`.** The floor is applied to the token set that decided the
   verdict rather than to `name_agreement`. Find a pair of names where `agreement_used` and
   `match_verdict` disagree about whether the floor was cleared, or where the fallback path makes
   the floor behave surprisingly.

6. **The licence reasoning in `d39141e`.** I claim that publishing a classification *derived from*
   ODbL footprints makes the published artifact share-alike, that footprints themselves are still
   never republished, and that CC BY attribution is still separately required. Is any of that
   wrong, and is anything now published that would need an attribution it does not carry?

7. **Anything in the two notes that overstates.** In particular: "unclassified grocery records fall
   from 272 to 259" and "an eighth of what was left". Check the arithmetic and the denominators —
   the previous review caught me conflating two populations in exactly this way.

Report findings as a numbered list, most serious first: file and line, what breaks, and the
smallest input that demonstrates it. **If a claim is correct, say so** — a review that finds
nothing is a useful result and I would rather have it than a manufactured finding.
