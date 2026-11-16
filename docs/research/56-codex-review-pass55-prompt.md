# Codex review, pass 55 — the three browser sessions, and what they claim

The owner closed the review chain after pass 54 and has now reopened it for this work
specifically. Pass 54's own verdict was that **the next review of the card should follow its first
browser use** — "a different source of evidence instead of another examination of the same code".
That has now happened three times. This is that review.

Repository: `C:\Users\arikt\documents\github\distanceFinder`, branch `v2-rethink`, at `3705195`.
Python: `v2/.venv/Scripts/python.exe`.

## Runtime note

Your sandbox cannot start processes: every `exec_command` fails with `windows unelevated
restricted-token sandbox cannot enforce split writable root sets`. See
`docs/engineering-notes/reference-codex-runtime-quirks.md`. You can read any file and run
JavaScript through `node_repl`. For Python, reason from source and **say plainly what you could
not execute**. Report to stdout as your final message.

**You cannot reach a browser either**, and every claim below rests on browser readings I made and
you cannot reproduce. Treat them as reported observations, attack the *method* that produced them,
and say which of my conclusions would survive if a reading were wrong.

## What is under review

Three commits, 2,790 insertions across 27 files, all since pass 54:

| commit | what |
|---|---|
| `1365f13` | the first browser run of the published page; `docs/experiments/s3-11-browser-placement.json` |
| `a34caa8` | the card's wording changed, per pass 54's one product recommendation |
| `3705195` | the page read at the walked cell; a defect found in the s3-10 oracle; `docs/experiments/s3-12-*.json` |

Current state: 1,542 Python tests passing, 24 skipped; 87 browser conformance checks; 36 card
checks; 13 probe checks; 69 of 69 worker mutations, 33 of 33 card, 30 of 30 admissibility, 9 of 9
migration — 0 inert, 0 survived, 0 errored.

Read first: `docs/engineering-notes/project-phase1-s3-progress.md` (live state), the two
experiment records, `v2/spikes/g3-render/card.js`, `v2/scripts/measure_drawn_pixel.py`, and ledger
instances 48, 49 and 50 in `docs/engineering-notes/feedback-verify-the-shape-of-the-risk.md`.

## Where I am weakest, declared

Do not let this list bound you — but do not let me look better than I am either.

1. **I never verified that the audit sheet's `row`/`col` are UTM `GridSpec` indices.** This is the
   load-bearing claim of commit `3705195` and ledger instance 50. What I actually established is
   narrower: the sheet's own `query_lon`/`query_lat` for `band15min_pass-03` fall in published cell
   (282, 126), not (286, 129), and (282, 126) matches all four of that row's recorded values while
   (286, 129) matches none. My attempt to rebuild the UTM grid failed on
   `ModuleNotFoundError: No module named 'locfinder.regions'` and I did not pursue it. **Check
   whether the sheet's indices really are the UTM grid's**, and whether my account of the cause is
   right or merely plausible. If the real cause is different, instance 50 is wrong and so is the
   note I put in three documents.
2. **The affine blind spot (s3-11) was closed by reading a screenshot by eye.** Neither venv has an
   image library. I drew four one-pixel lines across a colour edge and judged which one the painted
   edge sat on. Is that sufficient for the claim it supports, and is the margin argument (38 px
   between hypotheses against a 9 px gap) actually what the picture shows?
3. **The two "instrument defects" in the first probe run** — canvas premultiplied alpha, and
   `MouseEvent` truncating `clientX` — were each diagnosed with a control in the same call, then
   the probe was changed and re-run clean. **This project's own history is that a control can
   confirm on the wrong cause** (pass 50 found two of mine doing exactly that). Attack both.
4. **I re-pointed a predeclared oracle after a browser had run against it, then re-ran the probe
   and reported zero disagreements.** Is that legitimate, or did I move a goalpost? I also changed
   `test_the_run_is_against_the_oracle_that_is_committed` to read the newer run and added
   `test_the_first_run_is_kept_as_what_it_was`. **Did I weaken a guard while appearing to keep
   it?** Read both tests and say so if I did.
5. **The 1002 ms repaint figure I rejected as an artefact.** I claim Chrome throttled animation
   frames to 1 Hz in an unobserved window and that the page's paint-completion stat therefore
   measured a frame clock. My control was a 10-second frame-gap sample during which a screenshot
   was taken: gaps read 1000 ms, then 17 ms for nine frames, then 1000 ms. **Is there a reading
   where 1002 ms is real and my control is the artefact?** If so the page has a one-second repaint
   and I have talked myself out of a genuine product defect.
6. **Ledger instances 49 and 50 may be overstated.** Pass 48 found four of my five new instances
   overstated. 49 says a tradeoff can stay right while its justification expires; 50 says an index
   is not a location until it names its grid. Say if either is a restatement of an existing
   instance or inflated beyond its evidence.

## The questions

Answer 1 and 2 at length; they matter more than any defect you will find.

1. **Did these three commits retire product risk, or only defect risk?** §0 of
   `docs/plans/2026-11-04-s3-execution-plan.md` orders by product risk retired. Pass 54 judged five
   prior passes disproportionate on exactly this test. Apply it to this work. The card's words now
   say "The model estimates this cell meets your limits" and "Times are estimates: measured from
   the centre of this cell, and rounded up to the whole minute" — **argue the case that this is
   cosmetic**, as strongly as you can, and then say whether you believe it.

2. **Is the card's wording now honest, and is it honest in the right places?** Specifically:
   - I hedged the affirmative headline and **left both negative headlines unchanged** ("At least
     one criterion is not satisfied here"), on the reasoning that the estimate note under all
     three verdicts covers them and that rewriting a sentence the owner had not asked about was
     not mine to do. Is that defensible, or does it now present an exclusion as the more certain
     answer — the exact asymmetry I claimed to be avoiding?
   - `minutesText` still prints a bare "14 min". The byte is `ceil`, so that cell's model time is
     in `(13, 14]`. Is "rounded up to the whole minute" in a separate line an adequate disclosure,
     or should the number itself carry it?
   - The restricted-route warning moved to the line under the time. Is "beside the relevant time"
     actually what that achieves, given the card can show several criteria?

3. **`grid.encode_minutes` is `ceil` and its docstring justified the cost with "nothing displays
   it".** The card has displayed it since 2026-11-14. I corrected the docstring and made the
   30-second-unit question an owner decision. **Should the encoding change?** The docstring's own
   analysis says 30-second units are exact, hold display error under 30 s and fit the 120-minute
   horizon in 254, at +32% bytes. Give a recommendation, not a survey.

4. **The two experiment records.** `s3-11` and `s3-12` are written to be quoted by a later reader.
   Find a sentence in either that a reader could quote to claim more than the evidence supports.
   I annotated rather than rewrote the s3-11 record when its probe turned out to be mislabelled —
   check that the annotation is adequate and that nothing in the run data was edited.

5. **A last defect sweep**, attached rather than leading: `card.js`, `probe_placement.js`,
   `measure_drawn_pixel.py`, `collect_probe_run.py`, `write_s3_12_walked_cell.py` and the three new
   test files. Rank by product risk, not severity.

## What I believe, so you have something to disagree with

- The page draws the raster where `measure_drawn_pixel.py` said, at all eleven probes, twice.
- The three disclosures reach a screen in one card, and I have now seen them.
- The walked-cell reading was worth more than the five code reviews that preceded it: it found a
  400 m error in the apparatus in its first comparison against anything outside that apparatus.
- The wording change is small and real, and the thing it most reveals is that nobody who is not me
  has read this card.

Disagree with any of it if the files say otherwise.
