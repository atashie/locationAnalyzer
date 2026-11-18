---
name: 2026-11-18-name-floor-review-findings
description: "What the adversarial review of the name-agreement floor found: one real defect in the floor, one measurement bug that inflated my own note, and four overclaims in the note's prose"
metadata:
  type: reference
---

# Findings: the name-agreement floor review

Prompt: [[2026-11-18-name-floor-review-prompt]], committed before launch. Reviewer: Codex
`gpt-6.1-sol`, read-only, 37 targeted tests, no edits.

**The review was worth running.** It found a defect in the floor itself, a bug in the measurement
that fed my own note, and four places where the note's prose claimed more than the measurement
supported. Nothing here was found by the tests I wrote.

## Acted on

| # | finding | what I did |
|---|---|---|
| 2 | **`A&C Supermarket` against an identical OSM name 12.0 m away scored `unverified` and its correct proposal was withheld.** `a` and `c` fall to the length rule, `supermarket` is a stop-word, so both token sets emptied and the code read that as "nothing to compare". | **Real defect, fixed.** `short_tokens` fallback: when the strict pass is empty on either side, retry both without the length filter. Not a string-equality special case, because `A&C` vs `A & C` has to work too. 5 new tests. |
| 5 | **The `weak` caveat was concatenated onto an empty proposal**, so 12 pharmacy rows held warning text in a proposal cell — and my note counted all 12 as proposals, reporting 102/29 (28.4%) where the truth is 90/17 (18.9%). | **Real bug, fixed.** `proposal_text()` returns `""` when there is no proposal; test asserts it. Note corrected. |
| 4 | **"63% of the proposals were not evidence" overstates a withholding rate** as a wrong-match rate, in both directions: withheld `unverified` rows may be correct, and the survivors include the three generic-word matches. "30 usable proposals" overstated the survivors likewise. Also: the 42 zero-agreement OSM proposals in the comparable set are a mix of `differs` and `unverified`, not 42 different businesses. | **Corrected.** This was the exact overclaim item 6 of the prompt asked the reviewer to attack, so the prompt earned its keep. |
| 6 | **"The same verdict function applies to the FSQ side and withholds almost nothing" is false as a description of what runs** — the FSQ path never calls `match_verdict` at all. | **Corrected.** The floor is not applied to FSQ; what is true is only that it would matter little (0.9% vs 12.4%). |
| 3 | **Claim "a Jaccard threshold is the wrong knob" is partly refuted.** An inclusive floor at **0.25** keeps all twelve correct matches in the band *and* rejects `Han-Ah-Rum Mart` / `Han-Dee Hugo's` at 0.20, since the correct `Handee Hugo 77` / `Han Dee Hugo` scores 0.25. Also "the first five and 12 rows like them" should be twelve correct rows in total. | **Corrected, option not adopted.** 0.25 strictly dominates on the sample. Not taken because it was chosen by looking at the same fifteen rows that would judge it. Recorded as an owner-visible option. |

## Noted, not acted on

| # | finding | why |
|---|---|---|
| 1 | **Sam's Club is removed more decisively than the evidence warrants.** Neither the warehouse-club category nor OSM's silence establishes the pharmacy's status; the warning survives only in source text while selection removes the record completely. A retained-but-flagged record would express the doubt better. Explicitly *"a publication risk, not a demonstrated false closure"*. | **This is the owner's decision, made today over exactly this stated doubt.** It is passed back to them rather than reversed by a session, with the reviewer's suggestion attached: a flag that keeps the record would carry the doubt into the data instead of into a comment. Harris Teeter was confirmed correctly resolved. |
| 7 | The `differs` / `unverified` distinction is correct and useful, but *"only disagreement should block"* is a policy preference rather than a consequence of the measurement, and blocking both makes acceptance mathematically equivalent to `name_agreement > 0`. | **Fair, and the note no longer claims otherwise.** The A&C defect was the concrete case where the conservative policy failed, and that is fixed. Whether to propose from an unnamed feature 3.7 m away stays a judgement; the reviewer could not establish it either way. |

## Checked and clean

Finding 8: the re-export works. All four dependent scripts import, both identity comparisons hold,
the library imports only `re` and has no reverse dependency. No circular-import or `sys.path`
regression attributable to the extraction.

## One thing the review got wrong, and one I could not reproduce

* **The prompt's own population error was the reviewer's catch, not its mistake:** I had used
  `Walgreens` / `Rite Aid` at 2.2 m as an example among "the 51 grocery" rows. It is a **pharmacy**
  row. Corrected in the note.
* **I could not reproduce the split "42 = 30 `differs` + 12 `unverified`".** Running the verdict
  over both accuracy sheets gives 83 zero-agreement OSM proposals (68 `differs`, 14 `unverified`,
  1 `agrees` after the fallback fix), so the reviewer was using a narrower filter than I could
  rebuild. The qualitative correction — that the 42 are a mix and not 42 different businesses —
  is certainly right and is what the note now says; the number is not asserted.
