# Codex pass 36 — nine findings against T0, and two of the three High ones were the headlines

**2026-11-11.** Reviewed `3aa4a44..38ae076` (commits `14f9219`, `19a080d`, `38ae076`): T0, the
attachment prevalence-and-impact pilot, stages 1 and 2. Model `gpt-6.1-sol`, 13m 41s. Reproducers in
`37-codex-review-pass36-counterexamples/`; every finding was reproduced here before being acted on.

**3 High, 5 Medium, 1 Low. All nine stand.** None is an arithmetic error.

## What it confirmed

Listed first, because a review that reads as all fault is easy to discount and this one was not:

- the bbox window enumeration is sound — no omissions against **full enumeration on 100 queries**,
  including degenerate bounding boxes, zero-length segments and ties;
- given the supplied records, the A/C/D retention filters, the shared projection arithmetic and the
  dedup-before-cap order match the stated conventions;
- Part 1 is unchanged from `14f9219` and **precedes the recorded run**; equal sixths is a declared
  allocation; the small-sample certification limitation is correctly stated;
- the generated document matches the artifact, and `--check` **fails** on a deliberately drifted
  copy;
- `read_frame` rejected tampered contents, 34 frame tests pass, no bypass found;
- **rule 3 remains the correct outcome.**

## F1 (High) — the two "genuine exact ties" are not ties

The diagnostic asked whether a dropped candidate equals its record's exact minimum. A **tie** needs
two occurrences *at the same exact distance*; being a unique minimum is a different property. Codex
rechecked all 512,633 structures: both events have a **unique** exact minimum.

Reproduced here, and the event is worth stating precisely because it is not nothing:

| | exact squared distance | computed residual |
|---|---|---|
| the position C dropped | **482.8530714527748** (nearer) | 21.973917981489485 |
| the position C kept | 482.8530714540442 | **21.973917981417063** (nearer) |

The computed order is **inverted** against the exact order, so C keeps a position that is exactly
farther and discards the exactly nearest one. Same family as pass 24 F1 — computed residuals
disagreeing with exact ones — but not the consequence the design described. **Genuine ties
discarded: zero.** Now counted separately, and under the design's record keying the two physical
events present as four dropped candidates.

## F2 (High) — the bound bounds objective 1, not the reported time

The claim was a bound on "the journey time". Design §2.1 defines **objective 2** as the time along
the *cost*-minimising path, so selection by cost and reporting by time means an arbitrarily small
cost change can switch the route. Codex's counterexample: a bound of **0.0129365 s** against an
objective-2 move from **249.995 s to 129.983968 s** — 120.011 s, the size of an apportioned
restricted-access penalty. Objective 1 in the same case moved 0.0011 s, inside the bound.

A second failure is about existence rather than magnitude: on a one-way record a moved attachment
can leave **no legal journey at all**, which no difference in seconds describes.

Fixed by scoping rather than deleting. The bound is now reported for **objective 1 with both
directions legal** — the objective E1 is defined against — and one-way records are excluded and
counted. That turned out to matter a great deal: **5,872 of 13,196** A≠C structure points sit on a
one-way record, so the bound covers **55%** of the A-vs-C disagreement, not the 100% first claimed.
"Selection is by cost, reporting is by time" is written down in three places in this project and I
still derived a time bound from a time identity for a product that reports a cost-selected time.

## F3 (High) — stage 3 cannot be restricted to the origins whose attachments differ

Seven grocery candidate sets differ between A and C, and a **destination's** attachment change can
affect any origin — which the plan's own stage-3 text states. Codex produced an origin whose A and C
attachments agree and whose only journey disappears when a destination moves. The artifact also
holds aggregate counts, not the point identities the write-up claimed were enumerated.

**"About 2.5% of a full paired comparison" is withdrawn**, along with "enumerated, not guessed".

## F4 (Medium) — a record was production's geometry group

`snap.EdgeIndex` keys by `(node pair, canonical geometry)` and keeps the cost-minimal parallel edge.
That collapses parallel records carrying **different weights**, which design §2.4 requires be kept
apart so that grouping cannot answer a ranking question. On the frozen frames: 11 multiple-candidate
points become **16** on frame B, 10 become 16 on frame C, over 5,239 affected geometry groups.

The pilot now attaches to the design's records, keyed by
`(node pair, canonical geometry, travel_time, cost)` — **808,433** against production's 713,452.
Two consequences, both worth more than the fix:

- **prevalence rose tenfold**, from 2.9% to about 30% of points, almost entirely coincident parallel
  roads at *one position*. Zero points anywhere have two *distinct positions* at the exact minimum,
  so a separate column now distinguishes design-sense ties from geometric ones. Without it the
  write-up would have reported ~30% "genuine exact ties";
- **the disagreement rate did not move at all** — A≠C at 2.5742% of structures, identical to the
  production run. The multiplicity is shared by all three conventions and cancels. A number that
  survives a definition change which moved its neighbour tenfold is the one to trust.

## F5 (Medium) — `split_midpoint` was not length-preserving

`(0,0),(1,0),(2,0)` became pieces of length 1 and 2 — total 3 against an original 2 — because the
second piece was built from the segment's *start* where the cut landed on its end. Two near-vertex
cases produced gaps or overlaps. Fixed so the pieces share the cut vertex, with a cut inside
`MIN_SEGMENT_M` of a vertex snapped to it; verified length-preserving on all three counterexamples.

Codex also showed that a float midpoint is **not exactly on the original line**, so `subdivide` and
`split_midpoint` do not preserve exact geometry and can move a retained D position for an arithmetic
reason rather than a representational one. **D's invariance is therefore a property of
transformations that preserve exact geometry** — which is `split_every_segment`, cutting only at
existing vertices — and the reported zeros are observations on the points tested, not a theorem.

## F6 (Medium) — the transformation window manufactured changes

The transformed side recomputed its window without `measure_point`'s numerical slack, so the two
sides of the comparison were not computed alike: with GEOS reporting 26.770322868537935 and the
recomputation 26.77032286853794, a record at the computed band edge was present before and absent
after with the geometry unchanged — two A candidates became one before any transformation. Fixed by
returning the window from `measure_point` and reusing it. The transformation results are unchanged
on these samples, which says the pattern was not an artifact of it.

## F7 (Medium) — `positions_differ` matched lexicographically

Sorting both sets by `(x, y)` and comparing pairwise breaks the correspondence under a perturbation
smaller than the tolerance: `{(0,0),(0,10)}` against `{(-10⁻⁷,10),(10⁻⁷,0)}` was reported as a
change. The dedup also compared only against the last kept point. Fixed with nearest-unmatched
matching and an all-pairs dedup. The stated self-crossing limitation is now quantified: removing one
pass of a self-crossing road is invisible here even where the remaining journey times differ by
**666.667 s**.

## F8 (Medium) — cell centres are not a census of frame C

The code and artifact said so; the prose promoted the result to "both whole populations". Frame C's
population is the cell's **area**, sampled as an independent within-cell point, and attachment can
vary inside a cell. Corrected to: no eligibility difference on any point measured — all structure
centroids, all cell centres, the three pre-registered sets — with frame C's area covered only by its
500-point sample.

## F9 (Low) — three misread figures

The quoted sample rates `2.2%, 2.0%, 3.45%` are A's *multiple-candidate* rates, not A-versus-C
disagreement (2.2%, 1.6%, 1.2727%). The transformation tables total **11,550** evaluations, not
11,050. And the five-point gap between the candidate-set and position columns cannot be attributed
to the exact predicate, because A and C do not use it.

## The pattern, which is the point

Every one of the nine is a **mismatch between the thing measured and the thing claimed**. The code
computed what it was told to, in all nine cases. Two were caught in drafting by asking what the
number was a number *of*; the third of that kind — F1 — survived into the committed version and
needed an adversary with the data. Reviewing the reasoning twice before publishing did not find any
of them.

See `docs/engineering-notes/project-phase1-s3-step3-attachment-pilot.md` for the lessons and
`docs/experiments/t0-attachment-pilot.md` Part 2 for the corrected results, which open with the
correction table rather than burying it.
