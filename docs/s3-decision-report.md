# S3 decision report — walk to a grocery, Triangle, 100 m grid

**2026-11-13, rewritten the same day after Codex pass 46.** For one decision: whether to put this
in front of a bounded set of households. Every number links to the measurement behind it.

> **This report has now had its central verdict corrected twice, in opposite directions, and the
> answer is neither of them.** The first draft said real-world accuracy was "UNVERIFIED, the
> owner's call", which bypassed the predeclared scorer and understated the evidence (Codex pass
> 46). The second said `FAILED`, quoting that scorer's output, which **overstated** it: the scorer
> cannot be applied to this observation at all (pass 47). What follows is the third framing, and it
> states what is missing rather than supplying a verdict in its place.

## Real-world accuracy: one unresolved discrepancy, and no admissible observation

The owner walked `band15min_pass-03` and reported **about 25 minutes** against a published **14
minutes**. That is a 1.85× discrepancy and it is unexplained. It is **not a scored failure**,
because the audit record does not document the things `E3` compares:

| what E3 needs | what the record has |
|---|---|
| the door the walk started from, inside the cell | not recorded |
| the destination actually reached | not confirmed |
| whether the private approach was used or avoided | **unresolved** — the owner asked the question and it is open |
| a timed duration | "closer to 25 mins", not stopwatch-timed |

**The audit sheet already said this, and both of my framings ignored it.** Its own notes column
records the walk as "OWNER-REPORTED, APPROXIMATE, NOT STOPWATCH-TIMED", gives the owner's words
verbatim, and says of the avoiding route that matches their distance — 2,139.9 m, 1,533.1 s —
that it is **"a reproducible candidate and not proof of the route walked"**. That is the correct
status, written when the journey was logged. The README acknowledges the same gaps, and the
diagnosis note calls the two journeys "potentially different journeys". A sensitivity sweep over the duration cannot
repair a missing journey identity, so the earlier "flips at 16.9 minutes" paragraph is withdrawn —
and it was wrong twice over: `E3`'s `reported_s` is **what the product said**, which is the encoded
**840 s**, not the raw model's 810.8185424804688, and against 840 s the binding boundary is **17.5
minutes**, not 16.9. At exactly 17 minutes the scorer returns `UNVERIFIED`.

**What is established is the model's behaviour, not the walk's.** The published route takes a
**private track**, which beats a 968-second detour even after 360 seconds of penalty. That is a
fact about what the pipeline selects. Saying "the walked journey took a private track" — as the
previous draft did — asserts something about the owner's route that nothing records.

**So E3's status is "no admissible observation", which is a third thing from both "unverified" and
"failed".** What would make this one scorable: a repeat walk from a recorded door inside the cell,
to the destination the layer selected, timed, with the approach route noted. That is one walk.

## The three outcomes

| outcome | status |
|---|---|
| **Construction fidelity** | partly evidenced — no reference comparator exists (T3 is gated on design §12 item 6) |
| **Engine disagreement** | **measured historically, not at this extent.** G1 compared 600 stratified walk cells on the **old 401 × 550 slice** (599 finite): signed median **+12.05 s**, median absolute **30.75 s**, p90 absolute **173.45 s**. Old slice, old configuration, speed-controlled reference, different access treatment, and no real-world accuracy implication. Not replicated on the current 514 × 643 Triangle layer. [g1](experiments/g1-routing.md) |
| **Real-world accuracy** | **no admissible observation.** One unresolved 1.85× discrepancy, above |

## What the product answers

For each 100 m cell in the Triangle, the walking time to **the grocery the routing cost rule
selects** — not the nearest by walking time. Those differ: with costs `(700, 650)` and times
`(500, 650)`, the rule selects the 650-second journey and reports 650 seconds while a 500-second
walk exists. The published number is a whole-minute rounding of the **modelled journey from the
cell centre**; it is not an upper bound on the household's real walk. The standing discrepancy
above is one unresolved case of it reading short, and is not a measured error rate.

Scope is **walk / grocery / Triangle only**. Drive, bike and transit have no layer at this extent.

## What is established

| | |
|---|---|
| **The grid decision** | Keep 100 m. The 200 m candidate roughly doubles the rate at which the published cell answer differs from the answer at the structure's own coordinate — 4.38% against 2.52% at 15 minutes, over 512,633 structures. [s3-1](experiments/s3-1-candidate-grids.md) |
| **The encoding** | `published-v2`: two uint8 planes. The decoder reproduces `status.evaluate` **cell for cell** on all 330,502 cells at ten thresholds, and the browser's JavaScript reproduces the Python — 37 conformance cases, 13 mutations all caught. Costs 18.2% more bytes. [s3-5](experiments/s3-5-browser-path.md) |
| **Three outcomes reach the browser** | 18,648 cells the pipeline can *prove* are over the threshold used to arrive as "unknown", and a known failure in one layer could be overridden by an unknown in another. Both fixed. |
| **Attachment prevalence** | Conventions **A, C and D** measured by census over **843,685** points; eligibility invariant on every point measured. **B is not implemented.** The choice between them is open on verdict impact, which needs the comparator. [t0](experiments/t0-attachment-pilot.md) |

## The known optimistic bias, and who is exposed

The walked journey took a private track that wins on cost. Measured over the **published cell each
structure falls in** — the answer the product would actually give that household:

| *T* | structures included | of those, route uses a restricted way |
|---|---|---|
| 10 min | 80,067 | **7,271 (9.1%)** |
| 15 min | 163,875 | 15,294 (9.3%) |
| 25 min | 298,716 | 30,971 (10.4%) |
| 45 min | 424,886 | 47,236 (11.1%) |

About one in eleven of the **structures** the product includes — this is a structure count, not a
household count, and frame B is a frame of structures.

**These are candidate disclosures, not deliverable ones.** They are the *source grid's* figures;
the browser receives a WGS84 re-tiling and MapLibre places it in Mercator, each moving the lookup
again. And **no flag plane is shipped**, so no household can currently be told any of this.
[s3-8](experiments/s3-8-restricted-routes.json)

The statistic the owner's 2026-11-10 decision owes is the **signed error on restricted-route
journeys**. This supplies the denominator and leaves the numerator empty: one journey, in the
optimistic direction.

## What else is not established

**The destination list is screened, not validated.** Nine records carry a closure flag and **must
not be filtered on current evidence** — four sit within 150 m of an open destination we already
publish. 1,473 structures at ten minutes depend on one of those records. Separately **Target,
Costco, Sam's Club and BJ's are not destinations at all**, and Walmart is split by format.
[s3-7](experiments/s3-7-destination-truth.md)

**The shipped raster is not the measured grid**: a WGS84 re-tiling moves 2.42% of structures at
fifteen minutes and omits 12,182; MapLibre's placement shifts 131,571 by one row (analytical, not a
screenshot).

**E1c has no interval method chosen**, so the conditional estimand is specified and not computed.

**The geocoding audit is unstarted** — whether a household's address resolves to the right cell.

## Release prerequisites, which are longer than "publish the flag"

None of the three things a household is owed can be delivered today:

1. **The restricted-route flag** — computed, not persisted in the layer bundle. Adding it is a
   wire-format change.
2. **The destination the time was measured to** — not persisted either, and a destination *node*
   does not identify a shop: 550 places snap to 510 nodes and 75 share one, so presenting an
   identity needs a rule that does not exist yet.
3. **Which criterion was unknown, and why** — the per-criterion card is unbuilt.

Also outstanding: **phone decode latency is unmeasured** (it needs a device), the
**recomputation-eligibility UI** is absent although the format carries what it needs, and the
browser implementation discussed above is **`v2/spikes/g3-render`, a spike** — not an identified
household product.

## A proposed ordering, not a measured one

No comparative error rates or return-per-hour figures exist, so this is a judgement about where to
look next, not a finding:

1. **Re-walk `band15min_pass-03` with the record E3 needs** — a door inside the cell, the
   selected destination, a timed duration, and whether the private approach was used. It is one
   walk, and it is the only thing that turns the standing discrepancy into evidence either way.
   More walks **cannot** clear a scored failure once one exists: a thousand accurate journeys
   leave an offending one in the set, so what moves a verdict is resolving that observation or
   changing the model, not averaging it away.
2. **More walked journeys on restricted routes** — the only check that consults the world, aimed
   at the ~9% of included structures whose route uses one. Whether that class is *more* often
   wrong is **not measured**; what is known is that the one discrepancy we have is on such a
   route.
3. **The grocery definition decision** — moves 3,912 structures at ten minutes and is currently
   arbitrary at the branch level.
4. **28 candidate destinations and 4 masked identities** checked by someone who can look.
