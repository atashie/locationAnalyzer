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

Seven distinct shops across the 16 Chapel Hill journeys: 4 Harris Teeter, 3 Food Lion, 1 Trader
Joes — and **4 to Hill's Family Asian Markets, 2 to Mikyins Asian Market, 1 to Seal The Seasons**.

Every one of the 550 grocery places carries `basic_category = food_and_beverage_store` with
taxonomy primary `grocery_store`, so each passes the category rule exactly as written. Whether a
specialty importer or a local-produce brand is what a household means by "ten minutes from a
grocery" is the `destination_qualifies` judgement, and it is now **inspectable in advance** instead
of discovered on arrival. Step 7's grocery-and-geocoding truth audit has its first concrete
material, and it did not need a walk to produce it.

The claim that remains unchanged: the layer's aggregation is `cost_selected_category`, the time of
the journey the **cost** model picked, which is an upper bound rather than the minimum over
qualifying destinations. A walk that beats our number has not caught us in an error. And 550 places
snap to 510 road nodes, so where `predicted_destination_alternatives` is non-empty our number does
not distinguish them.

## State

`1,164 passed, 24 skipped`. `scripts/mutate_selected_destination.py`: 8 mutations, all caught.
`scripts/mutate_conditional_rate_guards.py`: 4 mutations, all caught, and its restore check is now
real. Both sheets regenerated and matching the committed raster bit-exactly.

Related: [[project-phase1-s3-step0-audit-harness.md]], [[project-phase1-s3-design]],
[[feedback-verify-the-shape-of-the-risk]], [[reference-text-io-rewrites-line-endings]].
