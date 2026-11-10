# The audit sheet never said where to walk, and the answer was being discarded

**2026-11-10.** Branch `v2-rethink`. Commits `aeef909` (the library change) and `00b597e` (the
recovery and the sheets).

## What happened

The owner opened `docs/experiments/audit/triangle-grocery-walk-chapelhill.csv`, saw one coordinate
per row, and asked what they were supposed to time. The sheet gives a **start** and no
**destination**.

Its own README already knew: step 3 said "walk to a destination that qualifies under our own
category rule and that you would genuinely use", and the asymmetry section said a walk to a shop we
did not choose cannot clear the product. So the instruction and the limitation contradicted each
other, and the limitation won — the sheet as written measures the walker's journey, not ours.

**The destination identity was being computed on every build and thrown away.**
`scipy.sparse.csgraph.dijkstra(..., min_only=True, return_predecessors=True)` returns three arrays,
and `arrival_seconds_two_weight` bound the third to `_sources`. One underscore. Every published
layer knew which grocery it had routed each household to and kept no record of it.

`arrival_with_selected_destination` now returns `(seconds, selected)` and
`arrival_seconds_two_weight` delegates to it, so there is one search and one selection rule.
`cell_selected_destination` carries it from a query point through the snapped edge.

## The lesson worth keeping

**An `_`-prefixed discard is a decision about what the system will be able to explain later, and it
is invisible in review.** Nothing about `_sources` looks like a choice; it reads as noise from an
API that returns more than was asked for. The cost only appeared when someone downstream needed the
information and was told it did not exist — in a committed README, as a limitation of the method
rather than of one line.

Worth checking the other discards in `traveltime/` against the question "would a user ever ask us
why?" rather than "do we use it now".

## Three defects in my own work, all found by trying to break it

**My snapping fixture could not see the mutation it existed to catch.** It hung a penalised shop off
the far endpoint, which made `T[E]` route back through `S` to `shopS` — so both endpoints selected
the same shop, and swapping `e_idx` for `s_idx` changed nothing observable. The fixture now puts a
different shop behind each endpoint, and a test asserts *that property directly*, so if it ever
stops holding the branch tests fail loudly instead of passing for the wrong reason. Sixth instance
of [[feedback-verify-the-shape-of-the-risk]].

**A guard that is unobservable from outside.** The `chosen_idx` `-1` mask cannot be reached through
either public entry point: an infinite `network` forces an infinite total, so the public masks
always fire first. Deleting it changes no published answer. It is kept, because the field is part of
`_Snapped`'s documented contract and the next caller may be a provenance reader that does not
recompute finiteness — but the test now sits at `_snap_network`, where the invariant lives, instead
of at a level where it cannot fail. Established by mutation, not by reading.

**Both mutation harnesses claimed byte-identical restoration and could not see line endings.** See
[[reference-text-io-rewrites-line-endings]]. `mutate_conditional_rate_guards.py` hashed the
*decoded* text on both sides, so it reported `byte-identical: True` however much the bytes changed.

## A 0.1 s gap that looked like a configuration difference

My first re-check compared the rebuild against the sheet's decimal `seconds` column with a 0.05 s
tolerance, and flagged 3 of 16 rows. That read as "this rebuild is not the configuration that
produced the sheet", which would have blocked the whole recovery.

It was my comparison. The sheet agrees with the stored `float32` on every row. The discrepancy was
that I snapped from `query_lon`/`query_lat`, which is the cell centre **rendered to six decimal
places** — up to **0.069 m** away, measured — and that moves the snapped journey by about a tenth
of a second. The recovery now works from `row`/`col`, indexed out of `GridSpec.cell_centers_xy()`
rather than recomputing the centre arithmetic, and the comparison is `float32(rebuilt) == stored`
exactly.

**Quantisation is a known function, so the honest test is equality after the same cast, not a
tolerance.** `spikes/s0_status_on_real_layer.py` already carried this lesson — a 0.01 s tolerance
there accepted stored 600.005 against rebuilt 599.999, a pair that straddles a 600 s threshold and
so changes the published verdict. I wrote the tolerance anyway, in a new script, with the
counterexample sitting in a file I had read that morning. A lesson recorded in one script's comment
does not transfer to the next script by itself; this is why these notes exist and why the rule now
also lives in the recovery script's own comment.

## What the destinations show before anyone walks

**Nine physical destinations under seven names**, across the 16 Chapel Hill journeys. Harris
Teeter (4 journeys) and Food Lion (3) are each **two different shops**, which is why the name count
and the location count differ — and why `predicted_destination_lat`/`lon`, not the name, is what
identifies a journey:

| name | journeys | locations |
|---|---|---|
| Harris Teeter | 4 | 2 |
| Hill's Family Asian Markets | 4 | 1 |
| Food Lion | 3 | 2 |
| Mikyins Asian Market | 2 | 1 |
| The Fresh Market | 1 | 1 |
| Seal The Seasons | 1 | 1 |
| Trader Joes | 1 | 1 |

**Seven of the sixteen** route to a specialty market or a produce brand rather than a general
supermarket. Whether that is what a household means by "ten minutes from a grocery" is the
`destination_qualifies` judgement, and it is now **inspectable in advance** instead of discovered on
arrival. Step 7's grocery-and-geocoding truth audit has its first concrete material, and it did not
need a walk to produce it.

All 550 grocery places carry `basic_category = food_and_beverage_store`, and **531 of them carry
taxonomy primary `grocery_store`** — not all 550, as revision 1 of this note said. The other 19
carry more specific grocery primaries (8 `mexican_grocery_store`, 5 `organic_grocery_store`, 3
`international_grocery_store`, and one each of `indian_`, `korean_` and `asian_grocery_store`) and
satisfy the rule through the taxonomy hierarchy rather than the primary string. Codex pass 33 found
all three miscounts: the uniform-taxonomy claim, the missing journey to The Fresh Market, and
names read as locations.

The claim that remains unchanged: the layer's aggregation is `cost_selected_category`, the time of
the journey the **cost** model picked, which is an upper bound rather than the minimum over
qualifying destinations. A walk that beats our number has not caught us in an error. And 550 places
snap to 510 road nodes, so where `predicted_destination_alternatives` is non-empty our number does
not distinguish them.

## The verification I claimed was stronger than the one I had

Revision 1 of this note and the sheet's README both said the recovery was verified "bit-exactly
against the committed raster", and read that as establishing it was the published configuration.
**Codex pass 33 took that apart, and it was already wrong for a reason I had found separately.**

Two independent defeats of the argument:

- **Matching counts is not matching sets.** The destination check compared three *counts* against
  s0's recorded provenance. Swapping destination node 539680 for 500268 preserves every sampled
  value in both sheets while changing **1,798 node arrival times**. The recorded provenance does
  not store the node set, so with the artifacts on hand there is no check that can establish set
  identity.
- **Matching 35 sampled cells is not matching the layer.** A current-code rebuild differs from the
  committed raster on **7,246 of 330,502 cells**, maximum difference 2,316.8 s, with finiteness
  unchanged and 10 cells changing verdict at ten minutes. None of the 35 audit rows is among them,
  which is why the sampled check passed. Codex also produced a synthetic tie that changes the
  selected shop while preserving the seconds exactly — so numeric agreement cannot establish
  historical identity even in principle.

**And the raster is stale.** It was built 2026-11-04 13:42 and verified bit-identical at 14:43;
`ab01ffa` at 21:12 then fixed `symmetrise`, which had been asking `G.has_edge(v, u)` and so letting
any edge from `v` to `u` suppress the reverse of *every* road from `u` to `v` — silently removing
pedestrian edges from the shipped walk graph. The sheet's numbers come from the pre-fix raster;
its SHA-256 still matches the sheet metadata, so that is settled rather than suspected.

The honest claim, now in both places: the recovery agrees with the sheet on every row, which is
**consistent with but not proof of** the historical choice, and the layer needs rebuilding to
remove the question. What the script does now is report the full-raster disagreement every time it
runs, so the sheet cannot be produced again with it unstated.

**The generalisation.** A verification that samples where the artifact is *known to agree* measures
nothing. I checked 35 cells chosen by a sampler that had no reason to pick changed ones, and read
agreement as identity. The same session's other instance of this is in
[[reference-text-io-rewrites-line-endings]] — a restore check that compared translated text to
translated text. Both are the same error: **the check ran, and the dimension it claimed to cover
was not in its domain.**

## State

`1,164 passed, 24 skipped`. `scripts/mutate_selected_destination.py`: 8 mutations, all caught.
`scripts/mutate_conditional_rate_guards.py`: 4 mutations, all caught, and its restore check is now
real. Both sheets regenerated and matching the committed raster bit-exactly.

Related: [[project-phase1-s3-step0-audit-harness.md]], [[project-phase1-s3-design]],
[[feedback-verify-the-shape-of-the-risk]], [[reference-text-io-rewrites-line-endings]].
