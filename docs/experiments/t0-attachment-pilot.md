# T0 — the attachment prevalence-and-impact pilot

Plan §0 step 3. **This file is written in two parts, and the first part is committed before the
measurement runs.** Design §2.2 requires that "a sensitivity budget must be allocated from existing
product requirements *before* the results are seen", and five rounds of choosing the attachment rule
by argument are why. A budget written after the numbers is not a budget.

---

## Part 1 — pre-registration (committed before the run)

### The question

§2.2's candidate universe is a **declared convention**, adopted as a provisional development
baseline chosen for simplicity, not as a demonstrated improvement. Four candidates:

| | rule |
|---|---|
| **A** | per-segment minima, then a 0.01 m band across all records (current, design revision 10) |
| **B** | an exact rational predicate with degree-two normalisation |
| **C** | exact minima **per edge record**, then the band across records (design revision 9, reverted) |
| **D** | exact minima **globally**, no band |

All four then apply the same occurrence deduplication and the same per-candidate caps, in that
order. Only the retention filter differs, and this pilot keeps the shared steps identical across
variants so that a difference is attributable to the filter.

**B is not implemented here.** Stage 2 instead computes **exact rational squared distances** on the
local segment sets, as a diagnostic that separates a genuine geometric tie from a merely close
computed residual. That diagnostic is not an implementation of B and this document must not call it
one; it exists because design revision 10 reverted C for comparing *computed* residuals for exact
equality, and the diagnostic is how often that actually matters on the real graph.

### What this pilot can and cannot establish

| stage | measures | available now |
|---|---|---|
| 1 | attachment: candidate sets under A, C and D at every sampled point | **yes** |
| 2 | the separate counts, the exact-rational tie diagnostic, representation sensitivity | **yes** |
| 3 | whether any of it moves a routed verdict | **no — needs the comparator, plan §0 step 4, itself gated on §12 item 1** |

So one class of impact is measurable now and one is not:

- **Eligibility change is observable without routing.** A point with an in-cap candidate under one
  convention and none under another moves between answerable and `OFF_NETWORK`, which is a verdict
  change on its own.
- **Candidate-set change with unchanged eligibility is not.** Whether a different candidate set
  routes to a different time needs the comparator. Where that is what the pilot finds, verdict
  impact is reported **explicitly unknown**, as the time box requires, and not substituted for by
  candidate frequency.

### The sensitivity budget, derived from an existing requirement

Taken from **§8's construction gate**, which is the existing requirement closest to the quantity
this pilot measures: for each published mode and threshold, on each frame, E1b (false inclusion) is
gated at **1.0%** and E1a (false exclusion) at **2.0%**, and at *n* = 500 the gate admits at most
**one** observed false inclusion and four false exclusions.

The attachment convention cannot be allowed the whole gate — design revision 10's change log says so
explicitly about the 60 s tolerance, and the same objection applies here. The design names six
independent construction choices that can move a reported verdict: the speed priors; the absence of
intersection penalties; the absence of turn restrictions; the restricted-access penalty calibration;
the whole-minute encoding; and this attachment convention. An **equal share of the tighter gate** is
the allocation:

> **Budget: the attachment convention may move at most `1.0% / 6` = 0.167% of a frame's verdicts**,
> at any published threshold, on either frame.

**And the pilot cannot certify compliance with that budget.** 0.167% of *n* = 500 is 0.83
observations, so a single verdict-moving event already puts the point estimate at 0.2%, over the
line, while zero events bound the rate only at **0.5974%** per frame (one-sided 95%, Clopper-Pearson
at *n* = 500) or about **0.30%** pooled at *n* = 1,000. Both exceed the budget. This is stated here,
before the run, because it determines what the result can mean: **a small pilot can identify a
common problem; it cannot establish extreme rarity.**

### The decision rule, pre-registered

1. **Any reproducible eligibility difference between conventions** → the convention that creates it
   is rejected, and the finding is reported with the points that produced it.
2. **Zero candidate-set differences on both frames** → A is retained, with its exposure bounded by
   the figures above and **described as bounded, not as certified**. The §2.2 sensitivities stay on
   the record.
3. **Candidate-set differences present, no eligibility difference** → the choice is **open on
   impact** and stays open until stage 3 runs. A remains the provisional baseline because it is the
   incumbent, not because the pilot endorsed it, and the measured prevalence is published.
4. **The exact-rational diagnostic finds genuine ties that C would discard** → that is a direct
   measurement of pass-24 F1 on real data and counts against C independently of stage 3.
5. **Representation sensitivity** (lawful subdivision moving a candidate set) is reported per
   convention and kept out of the population estimates, since the transformed points are not a
   random sample of anything.

Where the rule above does not select a single convention, the choice is the owner's and this
document says so rather than picking by argument.

### What is pinned

The run records: the graph's `graphml_sha256` and the way-tag manifest; `profile_version` and
`grid_version`; both frame digests (`51a59463`, `7914e80a`) verified on load; the Overture places
file digest; `ATTACH_TIE_M`, `max_access_m`, `poi_snap_max_m`; and the Python, NumPy and Shapely
versions. A measurement whose inputs are not recorded beside it cannot be invalidated — the lesson
of `project-phase1-s3-extract-tag-gap`.

### The sample

| frame | points | cap | what it is |
|---|---|---|---|
| B | 500 | 200 m | structure centroids, `frame_b_51a59463` |
| C | 500 | 200 m | independent within-cell points, `frame_c_7914e80a` |
| groceries | 550 | 300 m | every accepted grocery coordinate, a census not a sample |

The two frames stay **separate** throughout; they are different populations and pooling them would
report neither. The grocery set is a census of the destination population, so it carries no sampling
uncertainty — and a destination's attachment change can affect many origins, which is why it is
audited in full rather than sampled.

---

## Part 2 — results

*Nothing in Part 1 is edited now that this section exists; a correction appears here as a
correction, and the table at the top of this section is the record of them. The figures below the
rule are **rendered from `t0-attachment-pilot.json` by `v2/scripts/render_t0_results.py`**, not
transcribed, and `--check` fails if the document and the artifact drift apart. The prose is written
by hand.*

### Corrected after Codex pass 36

**This section was rewritten.** Pass 36 returned three High findings and five Medium against the
first version, and all nine were reproduced before being acted on. Two of the three Highs were
against claims this document led with, so the corrections are listed before the results rather than
after them:

| first version said | pass 36 | now |
|---|---|---|
| C discards **a genuine exact tie** at 2 of 512,633 structures | at both points the exact minimum is **unique**; a tie needs two occurrences at one exact distance | genuine ties discarded: **0**. What happens at those two points is a float/exact **inversion** — C keeps a position that is exactly *farther* and drops the exactly nearest one |
| the impact bound bounds **the journey time** | it bounds min-over-a-fixed-option-family in one metric. A 0.013 s cost change flipped the selection and moved **objective 2** by 120.011 s; a one-way case turned a finite journey into **none** | the bound is stated for **objective 1** only — which is the objective E1 is defined against — and one-way records are excluded and counted |
| stage 3 needs routing only for the ~2.5% of origins whose attachments differ | a **destination's** attachment change can affect any origin, as the plan itself says; seven grocery sets differ between A and C | **withdrawn.** Every origin is potentially affected. The artifact also holds counts, not the identities the first version claimed were enumerated |
| a record is one `(node pair, canonical geometry)` | that is production's grouping; it collapses parallel records with **different weights**, which design §2.4 requires be kept apart | the pilot now attaches to the **design's** records, keyed by `(node pair, canonical geometry, travel_time, cost)`. The first run's prevalence counts are superseded |
| "0 of 843,135 points" over "both whole populations" | cell centres are **not** a census of frame C, whose population is the cell's *area* | every point measured — all structure centroids, all cell centres, the frozen samples — shows no eligibility difference. The centre census does not establish that for frame C's area |
| `split_midpoint` is lawful | `(0,0),(1,0),(2,0)` became pieces of length 1 and 2, total 3 against 2 | fixed: the two pieces share the cut vertex, and a cut within `MIN_SEGMENT_M` of a vertex snaps to it. Verified length-preserving on all three counterexamples |
| the transformation check isolates the transformation | the transformed window omitted `measure_point`'s numerical slack, so candidates vanished between the two sides with the geometry unchanged | both sides now use the identical window, returned by `measure_point` |
| `positions_differ` matches within tolerance | lexicographic sorting breaks the pairing: `{(0,0),(0,10)}` against `{(-10⁻⁷,10),(10⁻⁷,0)}` was reported as a change | each position is matched to its nearest unmatched counterpart |
| the quoted sample rates `2.2%, 2.0%, 3.45%` | those are A's *multiple-candidate* rates, not A-versus-C disagreement | corrected; and the transformation tables total 11,550 evaluations, not 11,050 |

What pass 36 confirmed: the bbox enumeration is sound (no omissions against full enumeration on 100
queries, including degenerate boxes, zero-length segments and ties); the A/C/D filters, the shared
projection and the dedup-before-cap order match the stated conventions; Part 1 is unchanged from
`14f9219` and precedes the run; the renderer's `--check` fails on a drifted document; `read_frame`
rejects tampered contents; and **rule 3 remains the correct outcome.**

### The verdict against the pre-registered rule

**Rule 3: the choice is open on impact.** Candidate sets differ between conventions, eligibility does
not, so the rule neither rejects nor endorses one. A stays the incumbent. What follows is what the
measurement adds past that.

### The stage was cheap enough to census, so a bound became a count

The time box says to benchmark the first batch before committing to a larger sample or a census, and
to census the attachment stage if benchmarking supports it. At about 0.2 ms per point it does. So
where the pre-registration could only have offered "zero events in 500, one-sided 95% bound
0.5974%", the tables below carry exact counts over every structure centroid and every cell centre.

**But a cell-centre census is not a census of frame C.** Frame C's population is the cell's *area*,
sampled as an independent point within each cell; attachment can vary inside a cell, and the centre
is one point of it. The censuses are exact for the structure population and for the centres, and
frame C's area is covered only by its 500-point sample.

### No eligibility difference anywhere measured

Not one point — across both censuses and all three pre-registered sets — changes between answerable
and `OFF_NETWORK` under A, C or D. Eligibility is the only verdict-relevant effect reachable without
a router, and nothing in the attachment convention moved it.

### Two different rates, and only one of them is about ambiguity

Under the design's record definition about **30%** of points have more than one candidate — ten
times what the first run reported over production's grouping. Almost all of it is one phenomenon:
coincident parallel roads carrying different weights are separate records with the same geometry, so
a point near them attaches to several records **at one position**. Not one point in 843,135 has two
*distinct positions* at the exact minimum. That is multiplicity about **which record**, which the
design wants because those records carry different weights and therefore different journeys, and it
is not ambiguity about **where**.

The decision-relevant rate is how often the conventions *disagree*, and it is **unchanged by the
record definition** — A≠C at **2.5742%** of structures and **2.2678%** of cell centres, identical
to the production-grouping run to the point. The extra multiplicity is shared by all three
conventions, so it cancels out of every comparison. That the disagreement rate is invariant to a
definition which moved the prevalence rate tenfold is worth more than either figure alone.

Pass 26 was still right to refuse "a handful in 512,633": one point in forty is orders of magnitude
larger, and the census pins it rather than bounding it.

### What A and C actually disagree about

Every A≠C point is a dispute about *where along one record* to attach — the pilot found no
cross-record A/C disagreement at all, on any set. But "same record" is not sufficient for the
bound, and the first version treated it as though it were: of 13,196 A≠C structure points,
**7,324 are bounded** and **5,872 sit on a one-way record**, where moving the attachment can change
whether a legal journey exists. Among the bounded ones the median is **0.2818 s**, the maximum
79.16 s, 419 exceed one second and one exceeds sixty.

So the bound covers **55%** of the A-vs-C disagreement on structures, not all of it. And the
one-way share is partly a consequence of the record definition itself: keying by weights separates
a forward/reverse pair whose weights differ into two single-direction records, where production's
grouping merged them and both directions were finite.

**Three limits on that, all of which the first version of this section overstated.**

**It is objective 1, not the reported time.** Design §2.1 defines objective 2 as the time along the
*cost*-minimising path. Selection by cost and reporting by time means an arbitrarily small cost
change can switch the selected route and move the reported time without limit — pass 36 produced a
0.0129 s bound against a 120.011 s objective-2 move, the size of an apportioned restricted-access
penalty. E1 is defined against objective 1, so the bound is useful for the estimand this feeds; it
says nothing about objective 2, whose gap is reported separately inside E1 by construction.

**It is not a rate.** The bound limits how much a time *could* move, not how often a whole-minute
verdict does. That depends on how close each time sits to a threshold, which needs the times.

**One-way records are excluded.** On a one-way record a moved attachment can leave no legal journey
at all; a finite time becomes none, which no difference in seconds describes. Those points are
counted in their own column rather than folded into the bound.

A-vs-D is different in kind: D drops every banded near-miss, so a substantial number of points
differ across records, and nothing here bounds those.

### The reason C was reverted, measured — and it is not the reason that appeared

Revision 10 reverted revision 9 partly because C compares *computed* residuals for exact equality
and can therefore discard a genuine geometric tie (pass 24 F1, two arms at exact rational squared
distance 1 computing as 0.9999999999999999 and 1.0).

**That did not occur.** Genuine exact ties discarded by C: zero, on every set measured.

**What did occur is a float/exact inversion: four dropped candidates in 512,633 structures,
arising from two physical events** — each appears on two coincident parallel records under the
design's keying, and on one under production's. At both points the record's exact minimum is
unique, and C keeps a position whose exact squared distance is *larger* while dropping the exactly
nearest one. The computed order is inverted against the exact order:

| | exact squared distance | computed residual |
|---|---|---|
| the position C dropped | **482.8530714527748** (nearer) | 21.973917981489485 |
| the position C kept | 482.8530714540442 | **21.973917981417063** (nearer) |

The mechanism is the same family as pass 24 F1 — computed residuals disagreeing with exact ones —
but the consequence the design described, losing a tie, is not what the real graph produces. This
does not make C correct; it means the first of revision 10's two reasons rests on a case that is
either absent, or a handful of parts per million, depending on how narrowly it is read.

Under the design's record definition there is a second kind of exact tie, counted separately:
coincident **parallel** roads carrying different weights are different records with the same
geometry, so a point near them has several candidates at one *position* and one exact distance. That
is a tie in the design's sense and a duplicate geometrically. Only the distinct-position column is a
geometric tie of the kind §2.2's band exists to preserve.

### Counting candidates is not measuring the answer

The transformation check first compared candidate **counts**, and on that basis every convention
looked representation-dependent — the draft said so. It is bookkeeping: a record split turns one
shared-vertex occurrence into two while both candidates stay at the same physical place, and
candidates at the same places minimise to the same journey under every objective.

Comparing **positions** gives a different and consistent picture across every set:

| lawful re-expression | what it changes | A | C | D |
|---|---|---|---|---|
| `subdivide` — insert every segment's midpoint | vertices, same records | **moves** | — | — |
| `split_every_segment` — one record per segment | records, same vertices | — | **moves** | — |
| `split_midpoint` — cut each record at its arclength midpoint | both | **moves** | **moves** | — |

**§2.2's claim about A is confirmed, not refuted.** "A degree-two record split does *not* move it"
holds: under pure record segmentation A's candidate count changes and not one retained position
does. The count reading had this backwards.

**Pass 24 F2 is confirmed on real geometry.** C's positions move under record segmentation — the
record-dependence revision 10 reverted revision 9 for. Unlike F1, this one is common.

**D's positions did not move under any of the three.** That is an argument for the option nobody
argued for, and it needs two caveats pass 36 supplied. D is defined by an **exact rational** global
minimum, which is §12 item 1 — the open geometry-arithmetic item — not something the float pipeline
provides. And **D's invariance is a property of transformations that preserve exact geometry**: both
`subdivide` and `split_midpoint` introduce a rounded midpoint, which is not exactly on the original
line, and pass 36 built a case where that alone moves a retained D position. Only
`split_every_segment` cuts at existing vertices and preserves exact geometry. So the zeros are
observations on the points tested, not a theorem.

`split_midpoint` is **confounded by construction** and reported only for completeness: it inserts a
vertex *and* splits a record, so a convention moving under it may be responding to either. That A
and C move under it in equal numbers in every set is what a shared cause looks like.

**The three transformations are not of equal strength** — one new clamped endpoint per segment, one
record boundary per record, one per segment respectively — so the rates are not a ranking of
sensitivity between conventions. What they support is the pattern above.

### What this changes about the choice

| | before T0 | after T0, corrected |
|---|---|---|
| "a handful in 512,633" | the phrasing pass 26 refused | a rate orders of magnitude larger, counted on censuses |
| eligibility risk | unmeasured | no difference on any point measured |
| A vs C magnitude | unknown without routing | **objective 1** bounded; objective 2 and one-way availability not |
| C discards a genuine tie (F1) | a constructed counterexample | **not observed**; two float/exact inversions instead |
| C depends on record segmentation (F2) | a constructed counterexample | **confirmed, and common** |
| A depends on subdivision | a constructed counterexample | **confirmed, and common** |
| A under record segmentation | claimed invariant | **invariant in position**, as claimed |
| D | nobody's candidate | positions unmoved on every point tested, under transformations preserving exact geometry; needs §12 item 1 |

**What would settle it is stage 3**, which needs the development comparator — plan §0 step 4, gated
on §12 item 1. The time box requires that be said rather than substituted for: **verdict impact is
explicitly unknown.** And it cannot be shortened by routing only the origins whose own attachments
differ: a destination's attachment change can affect any origin, which is why the plan says so
explicitly and why the first version's routing-cost estimate is withdrawn.

### What was nearly published instead

Three figures in drafts of this document were wrong, and the same question caught all three: what is
the number a number *of*? "Seven of 25 frame C points have an exact tie" counted raw per-segment
*descriptions*. "Every convention is representation-dependent" counted candidates where it should
have counted positions, which inverted the conclusion about A and about D. And "C discards a genuine
tie" counted *being a record's exact minimum* where a tie requires *two occurrences at one
distance* — that one survived into the committed version and needed an adversary to find. The
failure mode is recorded in `feedback-decide-by-measurement-not-by-argument`, written two days
before this measurement.

---

### Re-run against design revision 13's exact primitives, 2026-11-12

Step 4 phase 4a.1 built `v2/locfinder/measure/exact.py` and design revision 13 made it normative as
§2.4 **item 7**. This pilot was then re-run against it, in two labelled steps, because the step 4
plan required the distinction: a **behaviour-preserving refactor** first, then a **separate
adoption** that can move the figures.

**The refactor moved nothing, and that is a checked claim.** This pilot carried its own copy of the
exact squared distance, written before the module existed. It now imports the module's. The two were
checked to agree bit-exactly on 10 named cases — the pass-30 and pass-37 witnesses, a degenerate
segment, both clamp boundaries, subnormal and `1e300` coordinates — and on 200,000 random segments
across five coordinate scales, a quarter of them placed on the segment so the clamp decides.
`v2/scripts/compare_t0_artifacts.py` then compared the whole re-run against the previous artifact:
**610 leaves, no difference outside the build stamp and the durations**. The tool was itself tested
with planted edits, two volatile and two real, before it was believed — and after Codex pass 38 F7
showed it flattened containers (`{"x": []}` matched `{"x": [{}]}`, `False` matched `0`) it was
rewritten as a recursive typed comparison with a 13-case self-test. **The refactor claim was
re-checked under the stronger tool and survives.**

**The adoption was censused rather than sampled**, at 844,685 points and 36,555,718 per-segment
positions, because making `prefix_arclength` take a cache of its record's segment lengths took the
exact path from 135 ms a point to 4.2 — the function had been recomputing every segment length once
per segment, which is quadratic in the segment count. The cache is a performance argument that could
have altered a measured quantity, so its equivalence is held by a test over random geometries and by
a mutation that supplies a wrong cache, not by the argument that it obviously cannot.

**The result, as corrected after Codex pass 38 F4.** It has two halves and the first draft of this
section reported only one of them.

*What does not move.* Eligibility, candidate counts and retained **places** are identical under
**A**, **C_exact** and **D** on every one of the 844,685 points, bar C's two. The vertex/segment
**structure** of the retained occurrences is identical too, and **no single segment's parameter
flips between a vertex and an interior point anywhere** in 36,555,718 positions. `C_exact` differs
from `C` on **2** of the 512,633 structure centroids and on none of the other four sets.

*What does move.* The **occurrence identity §2.2 actually specifies** carries the *unrounded*
parameter, and it changes on **573,107 of 844,685 points — 67.8%**. The first draft reported "0
occurrences changed" because it compared a deliberately coarsened label with the parameter dropped,
which is the vertex/segment structure and not the normative identity. Underneath, 2,142,228
parameters differ **exactly** where only 1,333,808 differ as rounded binary64 images — the exact
count is **1.61×** the figure first published, which had converted both sides to `float` before
comparing them. 2,142,080 residuals and 16,459,230 arclengths differ, by at most `2.4e-10` m and
`7.3e-12` m, and 42 rounded positions move by at most `4.7e-10` m.

**So the honest summary is a provenance finding, not an answer finding.** The adoption does not move
where a point attaches — the places are identical and the largest displacement anywhere is half a
nanometre — and it does not move which candidates are retained. It does change the **recorded
identity** of two thirds of those candidates, because an occurrence label contains a parameter and
the parameter changes. §12 requires the retained candidate set to be persisted *by identity*, so two
runs differing only in this arithmetic would write different manifests for the same points while
reporting the same answers. That is worth knowing and it is not a defect in either arithmetic.

**Why C is the one that moves, and why that was predicted rather than discovered.** A's rule is a
0.01 m band, which is seven to eight orders of magnitude wider than anything the arithmetic changes,
so a difference would need a residual sitting within `2.4e-10` m of the band edge. D's rule already
*was* exact — it takes the exact rational minimum. C's rule is **equality of the computed residual**
per record, which is the one predicate in the set that reads the last bit. That is why revision 13
reports it as a different rule rather than the same rule computed better, and why it may not inherit
this pilot's evidence.

**The mechanism, read off the numbers rather than inferred.**
`v2/scripts/explain_adoption_diff.py` reproduces both points. At structure `699485.6283,
3963460.7648` the nearest record has two adjacent segments whose own minima are genuinely
`2.89e-11` m apart:

| | segment 2 | segment 3 |
|---|---|---|
| float residual | 21.973917981489485 | **21.973917981417063** (the float minimum) |
| exact residual | **21.97391798138818** (the exact minimum) | 21.973917981417063 |

Segment 3's foot is the shared vertex, where both arithmetics compute the same number. Segment 2's
foot is interior, and there the float residual carries an error of `1.01e-10` m — **larger than the
`2.89e-11` m gap between the two segments**. So the float arithmetic cannot resolve which segment is
nearer, and orders them the wrong way round. C then retains the vertex where the nearer position is
**about 36 µm** (`3.56e-5` m) away inside segment 2. The same record appears twice, once per
direction, which is why both records move together and the candidate count stays at two.

Those two figures check each other, which is the reason to quote both. Moving a distance δ along the
road near the foot of the perpendicular changes the distance to the point only to second order, by
about δ²/2*d*: `(3.56e-5)**2 / (2 * 21.97)` is `2.9e-11` m, which is the measured gap between the
two segments' minima to one part in 50. A 36 µm displacement and a 29 picometre distance difference
are the same fact seen twice.

**What this does and does not license.** It is a census, so there is no sampling uncertainty: the
rate is 2 of 512,633, not an estimate of one. But the change is **structural as well as
positional** — a vertex candidate may leave along every incident edge, an interior one must first
traverse 36 µm of segment 2 — and whether either of those changes a reported journey time is a
routing question this pilot does not answer. That is stage 3, and it is step 4's phase 4c.

**What each column can and cannot see.** No column alone is the measurement, and Codex pass 38 found
this list one entry short — the missing entry was the one that mattered.

* **Vertex/segment structure against exact occurrence identity.** `coarse_occurrence` drops the
  interior parameter, so it answers "did the retained occurrence move between a vertex and a segment
  interior, or onto a different segment". It is **not** §2.2's identity, which includes the
  unrounded parameter. Reporting only the coarse column is how the first draft of this section said
  nothing changed while two thirds of the recorded identities did. Both are now reported, and a
  reader wanting "did the recorded candidate set change" wants the **exact** column.
* `positions_differ` matches places within `POSITION_TOL_M` = `1e-6` m. Every displacement the
  arithmetic itself produces is at most `4.7e-10` m, three to four orders of magnitude *below* that
  tolerance, so the places column is blind to the arithmetic's own drift by construction. What it is
  sensitive to is a **different candidate being selected**, and that is what fired here: 36 µm is 36
  times the tolerance. A zero in that column means "no candidate was swapped, added or removed", not
  "nothing moved".
* The "vertex/interior flips" column compares each segment with itself, so it counts a parameter
  landing on an endpoint in one arithmetic and not the other. It is **zero** across all 36.5 million
  positions — the W2 and W3 mechanism is real, as the sentinel shows, and it did not occur once on
  the Triangle graph. It also cannot see what did happen at these two points, which is *which
  segment* holds the record's minimum, because the two competing positions lie on different segments
  and so are never compared with each other.

---

### The measured figures

<!-- BEGIN GENERATED: scripts/render_t0_results.py -->

**The graph and the record set.** 539,814 nodes, 1,436,992 directed graph edges, **808,433 design records** against 713,452 production ones — 94,981 records that `snap.EdgeIndex`'s grouping collapses, being parallel roads with different weights. The measurement attaches to the design's records; the first run attached to production's and its prevalence counts are superseded.

**Pinned.** graph `2ee931bc0f2a…`, profile `speeds-v0+7bd6d52dbf33d8fe`, grid `grid-v0+7ab61db26b3cc98e`, places `26ad5ea1a4fd…`, `attach_tie_m` 0.01, caps 200 m / 300 m, shapely 2.2.0, numpy 2.5.4.

### How often a point has more than one candidate

| set | points | A | C | D | on >1 record (A) | >1 occurrence on one record (A) |
|---|---:|---:|---:|---:|---:|---:|
| frame B sample | 500 | 153 (30.6000%) | 151 (30.2000%) | 151 (30.2000%) | 151 | 11 |
| frame C sample | 500 | 144 (28.8000%) | 140 (28.0000%) | 139 (27.8000%) | 140 | 8 |
| groceries (census) | 550 | 99 (18.0000%) | 93 (16.9091%) | 81 (14.7273%) | 93 | 7 |
| **all structures (census)** | 512,633 | 165,259 (32.2373%) | 157,735 (30.7696%) | 156,703 (30.5683%) | 157,735 | 13,211 |
| **all cell centres (census)** | 330,502 | 102,473 (31.0053%) | 98,428 (29.7814%) | 97,835 (29.6019%) | 98,428 | 7,511 |

### Where the conventions disagree, and whether it changes an answer

| set | points | A≠C candidates | A≠C **positions** | A≠D candidates | A≠D **positions** | A≠C eligibility | A≠D eligibility |
|---|---:|---:|---:|---:|---:|---:|---:|
| frame B sample | 500 | 11 (2.2000%) | **11** (2.2000%) | 11 (2.2000%) | **11** (2.2000%) | 0 | 0 |
| frame C sample | 500 | 8 (1.6000%) | **8** (1.6000%) | 9 (1.8000%) | **9** (1.8000%) | 0 | 0 |
| groceries (census) | 550 | 7 (1.2727%) | **7** (1.2727%) | 19 (3.4545%) | **19** (3.4545%) | 0 | 0 |
| **all structures (census)** | 512,633 | 13,196 (2.5742%) | **13,191** (2.5732%) | 14,411 (2.8112%) | **14,411** (2.8112%) | 0 | 0 |
| **all cell centres (census)** | 330,502 | 7,495 (2.2678%) | **7,492** (2.2669%) | 8,218 (2.4865%) | **8,218** (2.4865%) | 0 | 0 |

Over both censuses — **843,135 points** — eligibility differs on **0** points for A against C and **0** for A against D.

### The exact rational diagnostic

A *tie* needs two occurrences at the same exact distance. A candidate that is simply its record's **unique** exact minimum is not one, and C dropping it is a float/exact **inversion** — C keeps a position that is exactly farther. The two were conflated in the first run (Codex pass 36 F1). And under the design's record definition, coincident parallel roads give several candidates at one *position*, which is a tie in the design's sense and a duplicate geometrically, so the distinct-position count is reported separately.

| set | points | A cand. C drops | …genuine exact ties | …unique exact minimum (inversions) | ≥2 candidates at exact min | ≥2 **distinct positions** at exact min |
|---|---:|---:|---:|---:|---:|---:|
| frame B sample | 500 | 20 | **0** | **0** | 151 (30.2000%) | 0 (0.0000%) |
| frame C sample | 500 | 12 | **0** | **0** | 139 (27.8000%) | 0 (0.0000%) |
| groceries (census) | 550 | 8 | **0** | **0** | 81 (14.7273%) | 0 (0.0000%) |
| **all structures (census)** | 512,633 | 18,865 | **0** | **4** | 156,703 (30.5683%) | 0 (0.0000%) |
| **all cell centres (census)** | 330,502 | 10,955 | **0** | **0** | 97,835 (29.6019%) | 0 (0.0000%) |

### The objective-1 impact bound, with no routing

`|Δarclength| / L × T` plus the band's connector difference. It bounds **objective 1** — `min over eligible destinations of total travel time`, which is the objective E1 is defined against (design §2.1). It does **not** bound objective 2, the time along the *cost*-minimising path: selection by cost and reporting by time means a 0.013 s cost change can switch the route and move the reported time by 120 s (Codex pass 36 F2). Nor does it bound route **availability**, so points whose disputed record is one-way are excluded and counted — on a one-way record a finite journey can become none, which no difference in seconds describes.

| set | pair | differing | bounded | one-way (excl.) | cross record (unbounded) | median | max | >1 s | >30 s | >60 s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| frame B sample | A vs C | 11 | 2 | 9 | 0 | 2.3754 s | 2.38 s | 1 | 0 | 0 |
| frame B sample | A vs D | 11 | 2 | 9 | 0 | 2.3754 s | 2.38 s | 1 | 0 | 0 |
| frame C sample | A vs C | 8 | 4 | 4 | 0 | 0.6818 s | 0.84 s | 0 | 0 | 0 |
| frame C sample | A vs D | 9 | 4 | 4 | 1 | 0.6818 s | 0.84 s | 0 | 0 | 0 |
| groceries (census) | A vs C | 7 | 6 | 1 | 0 | 0.1698 s | 1.39 s | 1 | 0 | 0 |
| groceries (census) | A vs D | 19 | 6 | 1 | 12 | 0.1698 s | 1.39 s | 1 | 0 | 0 |
| **all structures (census)** | A vs C | 13,196 | 7,324 | 5,872 | 0 | 0.2818 s | 79.16 s | 419 | 3 | 1 |
| **all structures (census)** | A vs D | 14,411 | 7,316 | 5,863 | 1,232 | 0.2823 s | 79.16 s | 419 | 3 | 1 |
| **all cell centres (census)** | A vs C | 7,495 | 3,957 | 3,538 | 0 | 0.3207 s | 38.05 s | 283 | 1 | 0 |
| **all cell centres (census)** | A vs D | 8,218 | 3,956 | 3,534 | 728 | 0.3207 s | 38.05 s | 283 | 1 | 0 |

### Representation sensitivity: three lawful re-expressions

Drawn at random, seed `20261110`, at most 5,000 points per set. Kept out of the population estimates above. **The three transformations are not of equal strength** — `subdivide` adds one clamped endpoint per segment, `split_midpoint` one record boundary per record, `split_every_segment` one per segment — so these rates are not a ranking of sensitivity between conventions.

Two columns per convention, and the difference between them is the whole point: a count can change while every retained candidate stays at the same **place**, and a set of candidates at the same places minimises to the same journey. Only a position change can move a reported time.

| set | points | transformation | A count | A **pos** | C count | C **pos** | D count | D **pos** | eligibility |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| frame B sample | 500 | `subdivide` | 24 | **24** (4.8000%) | 0 | **0** (0.0000%) | 0 | **0** (0.0000%) | 0 |
| frame B sample | 500 | `split_midpoint` | 7 | **7** (1.4000%) | 7 | **7** (1.4000%) | 0 | **0** (0.0000%) | 0 |
| frame B sample | 500 | `split_every_segment` | 42 | **0** (0.0000%) | 53 | **11** (2.2000%) | 42 | **0** (0.0000%) | 0 |
| frame C sample | 500 | `subdivide` | 14 | **14** (2.8000%) | 0 | **0** (0.0000%) | 0 | **0** (0.0000%) | 0 |
| frame C sample | 500 | `split_midpoint` | 1 | **1** (0.2000%) | 1 | **1** (0.2000%) | 0 | **0** (0.0000%) | 0 |
| frame C sample | 500 | `split_every_segment` | 51 | **0** (0.0000%) | 59 | **8** (1.6000%) | 51 | **0** (0.0000%) | 0 |
| groceries (census) | 550 | `subdivide` | 33 | **33** (6.0000%) | 0 | **0** (0.0000%) | 0 | **0** (0.0000%) | 0 |
| groceries (census) | 550 | `split_midpoint` | 19 | **19** (3.4545%) | 19 | **19** (3.4545%) | 0 | **0** (0.0000%) | 0 |
| groceries (census) | 550 | `split_every_segment` | 33 | **0** (0.0000%) | 40 | **7** (1.2727%) | 33 | **0** (0.0000%) | 0 |
| **all structures (census)** | 5,000 | `subdivide` | 239 | **239** (4.7800%) | 0 | **0** (0.0000%) | 0 | **0** (0.0000%) | 0 |
| **all structures (census)** | 5,000 | `split_midpoint` | 63 | **63** (1.2600%) | 63 | **63** (1.2600%) | 0 | **0** (0.0000%) | 0 |
| **all structures (census)** | 5,000 | `split_every_segment` | 367 | **0** (0.0000%) | 507 | **140** (2.8000%) | 367 | **0** (0.0000%) | 0 |
| **all cell centres (census)** | 5,000 | `subdivide` | 190 | **190** (3.8000%) | 0 | **0** (0.0000%) | 0 | **0** (0.0000%) | 0 |
| **all cell centres (census)** | 5,000 | `split_midpoint` | 33 | **33** (0.6600%) | 33 | **33** (0.6600%) | 0 | **0** (0.0000%) | 0 |
| **all cell centres (census)** | 5,000 | `split_every_segment` | 565 | **0** (0.0000%) | 683 | **118** (2.3600%) | 565 | **0** (0.0000%) | 0 |

### Adopting design revision 13's exact primitives

The same points measured twice: once with the arithmetic this pilot published, once with §2.4 item 7's primitives. Scope: **every point of every set** — 844,685 points and 36,555,718 per-segment positions. **A** and **D** are one rule measured two ways. **C** is not: its rule is equality of the *computed* residual, so exact arithmetic makes a different rule, reported as `C_exact` and inheriting none of this pilot's evidence.

| set | points | comparison | eligibility | count | vertex/segment structure | **exact occurrence identity** | places |
|---|---:|---|---:|---:|---:|---:|---:|
| frame B sample | 500 | `A_exact_vs_A` | 0 | 0 | 0 | **384** (76.8000%) | 0 |
| frame B sample | 500 | `C_exact_vs_C` | 0 | 0 | 0 | **384** (76.8000%) | 0 |
| frame B sample | 500 | `D_exact_vs_D` | 0 | 0 | 0 | **384** (76.8000%) | 0 |
| frame C sample | 500 | `A_exact_vs_A` | 0 | 0 | 0 | **259** (51.8000%) | 0 |
| frame C sample | 500 | `C_exact_vs_C` | 0 | 0 | 0 | **259** (51.8000%) | 0 |
| frame C sample | 500 | `D_exact_vs_D` | 0 | 0 | 0 | **259** (51.8000%) | 0 |
| groceries (census) | 550 | `A_exact_vs_A` | 0 | 0 | 0 | **486** (88.3636%) | 0 |
| groceries (census) | 550 | `C_exact_vs_C` | 0 | 0 | 0 | **486** (88.3636%) | 0 |
| groceries (census) | 550 | `D_exact_vs_D` | 0 | 0 | 0 | **486** (88.3636%) | 0 |
| **all structures (census)** | 512,633 | `A_exact_vs_A` | 0 | 0 | 0 | **389,703** (76.0199%) | 0 |
| **all structures (census)** | 512,633 | `C_exact_vs_C` | 0 | 0 | 2 | **389,696** (76.0185%) | 2 |
| **all structures (census)** | 512,633 | `D_exact_vs_D` | 0 | 0 | 0 | **389,673** (76.0140%) | 0 |
| **all cell centres (census)** | 330,502 | `A_exact_vs_A` | 0 | 0 | 0 | **182,275** (55.1510%) | 0 |
| **all cell centres (census)** | 330,502 | `C_exact_vs_C` | 0 | 0 | 0 | **182,272** (55.1500%) | 0 |
| **all cell centres (census)** | 330,502 | `D_exact_vs_D` | 0 | 0 | 0 | **182,264** (55.1476%) | 0 |

The arithmetic underneath those decisions does move. Counted over the same positions, so a zero above is a statement about decisions and not about numbers:

| set | positions | residual differs | max | arclength differs | max | parameter differs, exactly | its rounded image differs | rounded position moved | max | vertex/interior flips |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| frame B sample | 20,353 | 1,459 | 2.364e-10 m | 8,819 | 3.638e-12 m | **1,459** | 910 | 0 | 0.000e+00 m | 0 |
| frame C sample | 28,363 | 969 | 2.308e-10 m | 14,699 | 7.276e-12 m | **969** | 652 | 0 | 0.000e+00 m | 0 |
| groceries (census) | 9,417 | 1,889 | 2.355e-10 m | 2,504 | 9.095e-13 m | **1,889** | 1,056 | 0 | 0.000e+00 m | 0 |
| **all structures (census)** | 17,555,955 | 1,441,030 | 2.394e-10 m | 6,866,788 | 7.276e-12 m | **1,441,101** | 869,627 | 28 | 4.657e-10 m | 0 |
| **all cell centres (census)** | 18,941,630 | 696,733 | 2.397e-10 m | 9,566,420 | 7.276e-12 m | **696,810** | 461,563 | 14 | 4.657e-10 m | 0 |

**The sentinel, because every figure above is a count of differences.** An exact path that silently behaved like the float one would report zeros and read as good news, so two witnesses built to separate the paths must separate them or the run stops:

| witness | must separate | counters fired | float parameter | exact parameter | float label | exact label |
|---|---|---|---|---|---|---|
| W2 dot-product cancellation | yes | yes | `0.0` | `33554432/4722366482869645` | `(0, 'v', 0)` | `(0, 's', 0)` |
| W3 subtraction near the coordinate bound | yes | yes | `1.0` | `10737418239999999/10737418240000000` | `(0, 'v', 1)` | `(0, 's', 0)` |
| control, an ordinary interior attachment | no (control) | no | `0.5` | `1/2` | `(0, 's', 0)` | `(0, 's', 0)` |

Each witness is run through `adoption_stats`, the function that produces the census figures, and not through the projection alone — Codex pass 38 F5 showed that forcing both arithmetic requests to the float branch left the earlier sentinel passing while the census reported zeros. The control exists because two witnesses alone cannot distinguish a live counter from one stuck at 1.

The points where a retained candidate changed:

| point | comparison | what changed | candidates before | after | float minimum (m) | exact minimum (m) |
|---|---|---|---:|---:|---:|---:|
| `683146.6607, 3978519.8710` | `A_exact_vs_A` | exact occurrences | 1 | 1 | 32.988845740123175 | 32.9888457401507 |
| `683146.6607, 3978519.8710` | `C_exact_vs_C` | exact occurrences | 1 | 1 | 32.988845740123175 | 32.9888457401507 |
| `683146.6607, 3978519.8710` | `D_exact_vs_D` | exact occurrences | 1 | 1 | 32.988845740123175 | 32.9888457401507 |
| `690742.6606, 3966109.4743` | `A_exact_vs_A` | exact occurrences | 1 | 1 | 19.055310778327527 | 19.055310778363538 |
| `690742.6606, 3966109.4743` | `C_exact_vs_C` | exact occurrences | 1 | 1 | 19.055310778327527 | 19.055310778363538 |
| `690742.6606, 3966109.4743` | `D_exact_vs_D` | exact occurrences | 1 | 1 | 19.055310778327527 | 19.055310778363538 |
| `714529.6446, 3952743.1862` | `A_exact_vs_A` | exact occurrences | 1 | 1 | 24.545500466016552 | 24.545500466042192 |
| `714529.6446, 3952743.1862` | `C_exact_vs_C` | exact occurrences | 1 | 1 | 24.545500466016552 | 24.545500466042192 |
| `714529.6446, 3952743.1862` | `D_exact_vs_D` | exact occurrences | 1 | 1 | 24.545500466016552 | 24.545500466042192 |
| `725253.6908, 3968851.1242` | `A_exact_vs_A` | exact occurrences | 1 | 1 | 18.372147142183337 | 18.37214714220993 |
| `725253.6908, 3968851.1242` | `C_exact_vs_C` | exact occurrences | 1 | 1 | 18.372147142183337 | 18.37214714220993 |
| `725253.6908, 3968851.1242` | `D_exact_vs_D` | exact occurrences | 1 | 1 | 18.372147142183337 | 18.37214714220993 |
| `720214.3154, 3971646.1918` | `A_exact_vs_A` | exact occurrences | 1 | 1 | 22.93997885039857 | 22.93997885056329 |
| `720214.3154, 3971646.1918` | `C_exact_vs_C` | exact occurrences | 1 | 1 | 22.93997885039857 | 22.93997885056329 |
| `720214.3154, 3971646.1918` | `D_exact_vs_D` | exact occurrences | 1 | 1 | 22.93997885039857 | 22.93997885056329 |
| `702385.3573, 3952714.9979` | `A_exact_vs_A` | exact occurrences | 1 | 1 | 33.30509823706569 | 33.30509823707345 |
| `702385.3573, 3952714.9979` | `C_exact_vs_C` | exact occurrences | 1 | 1 | 33.30509823706569 | 33.30509823707345 |
| `702385.3573, 3952714.9979` | `D_exact_vs_D` | exact occurrences | 1 | 1 | 33.30509823706569 | 33.30509823707345 |
| `686393.2132, 3962595.1125` | `A_exact_vs_A` | exact occurrences | 2 | 2 | 18.287077896368395 | 18.287077896496886 |
| `686393.2132, 3962595.1125` | `C_exact_vs_C` | exact occurrences | 2 | 2 | 18.287077896368395 | 18.287077896496886 |
| `686393.2132, 3962595.1125` | `D_exact_vs_D` | exact occurrences | 2 | 2 | 18.287077896368395 | 18.287077896496886 |
| `716207.4275, 3963041.0154` | `A_exact_vs_A` | exact occurrences | 1 | 1 | 26.88415970672004 | 26.88415970678109 |
| `716207.4275, 3963041.0154` | `C_exact_vs_C` | exact occurrences | 1 | 1 | 26.88415970672004 | 26.88415970678109 |
| `716207.4275, 3963041.0154` | `D_exact_vs_D` | exact occurrences | 1 | 1 | 26.88415970672004 | 26.88415970678109 |
| `715842.4228, 3970098.7283` | `A_exact_vs_A` | exact occurrences | 2 | 2 | 10.891224550679937 | 10.891224550641212 |
| `714120.2237, 3981967.8591` | `A_exact_vs_A` | exact occurrences | 1 | 1 | 61.904383568377824 | 61.90438356825979 |
| `714120.2237, 3981967.8591` | `C_exact_vs_C` | exact occurrences | 1 | 1 | 61.904383568377824 | 61.90438356825979 |
| `714120.2237, 3981967.8591` | `D_exact_vs_D` | exact occurrences | 1 | 1 | 61.904383568377824 | 61.90438356825979 |
| `698903.5190, 3957872.0486` | `A_exact_vs_A` | exact occurrences | 2 | 2 | 2.0285290496316017 | 2.0285290495027626 |
| `698903.5190, 3957872.0486` | `C_exact_vs_C` | exact occurrences | 2 | 2 | 2.0285290496316017 | 2.0285290495027626 |
| `698903.5190, 3957872.0486` | `D_exact_vs_D` | exact occurrences | 2 | 2 | 2.0285290496316017 | 2.0285290495027626 |
| `670578.6202, 3978901.3946` | `A_exact_vs_A` | exact occurrences | 1 | 1 | 18.96929249383617 | 18.969292493834345 |
| `670578.6202, 3978901.3946` | `C_exact_vs_C` | exact occurrences | 1 | 1 | 18.96929249383617 | 18.969292493834345 |
| `670578.6202, 3978901.3946` | `D_exact_vs_D` | exact occurrences | 1 | 1 | 18.96929249383617 | 18.969292493834345 |
| `725788.3540, 3974280.8040` | `A_exact_vs_A` | exact occurrences | 1 | 1 | 37.7153657585658 | 37.71536575863075 |
| `725788.3540, 3974280.8040` | `C_exact_vs_C` | exact occurrences | 1 | 1 | 37.7153657585658 | 37.71536575863075 |
| `725788.3540, 3974280.8040` | `D_exact_vs_D` | exact occurrences | 1 | 1 | 37.7153657585658 | 37.71536575863075 |
| `717171.5886, 3992771.8588` | `A_exact_vs_A` | exact occurrences | 1 | 1 | 6.3952451475143075 | 6.3952451474873655 |
| `717171.5886, 3992771.8588` | `C_exact_vs_C` | exact occurrences | 1 | 1 | 6.3952451475143075 | 6.3952451474873655 |
| `717171.5886, 3992771.8588` | `D_exact_vs_D` | exact occurrences | 1 | 1 | 6.3952451475143075 | 6.3952451474873655 |
| `720369.9936, 3972455.2341` | `A_exact_vs_A` | exact occurrences | 2 | 2 | 5.1056966856260235 | 5.105696685467033 |
| `720369.9936, 3972455.2341` | `C_exact_vs_C` | exact occurrences | 2 | 2 | 5.1056966856260235 | 5.105696685467033 |
| `720369.9936, 3972455.2341` | `D_exact_vs_D` | exact occurrences | 2 | 2 | 5.1056966856260235 | 5.105696685467033 |
| `689764.2705, 3967764.5560` | `A_exact_vs_A` | exact occurrences | 1 | 1 | 16.35518199217936 | 16.355181992208895 |
| `689764.2705, 3967764.5560` | `C_exact_vs_C` | exact occurrences | 1 | 1 | 16.35518199217936 | 16.355181992208895 |
| `689764.2705, 3967764.5560` | `D_exact_vs_D` | exact occurrences | 1 | 1 | 16.35518199217936 | 16.355181992208895 |
| `669830.7804, 3957216.0547` | `A_exact_vs_A` | exact occurrences | 2 | 2 | 51.32439105378845 | 51.32439105387083 |
| `669830.7804, 3957216.0547` | `C_exact_vs_C` | exact occurrences | 2 | 2 | 51.32439105378845 | 51.32439105387083 |
| `669830.7804, 3957216.0547` | `D_exact_vs_D` | exact occurrences | 2 | 2 | 51.32439105378845 | 51.32439105387083 |
| `666350.1127, 3993798.9653` | `A_exact_vs_A` | exact occurrences | 1 | 1 | 123.52546542711657 | 123.52546542692708 |
| `701967.7222, 3963135.3724` | `A_exact_vs_A` | exact occurrences | 1 | 1 | 14.035870539312931 | 14.035870539181852 |
| `701967.7222, 3963135.3724` | `C_exact_vs_C` | exact occurrences | 1 | 1 | 14.035870539312931 | 14.035870539181852 |
| `701967.7222, 3963135.3724` | `D_exact_vs_D` | exact occurrences | 1 | 1 | 14.035870539312931 | 14.035870539181852 |
| `718594.0972, 3968431.2921` | `A_exact_vs_A` | exact occurrences | 1 | 1 | 8.329624653351763 | 8.329624653472203 |
| `718594.0972, 3968431.2921` | `C_exact_vs_C` | exact occurrences | 1 | 1 | 8.329624653351763 | 8.329624653472203 |
| `718594.0972, 3968431.2921` | `D_exact_vs_D` | exact occurrences | 1 | 1 | 8.329624653351763 | 8.329624653472203 |
| `714192.8098, 3974721.7423` | `A_exact_vs_A` | exact occurrences | 1 | 1 | 33.684204060569364 | 33.68420406038772 |
| `714192.8098, 3974721.7423` | `C_exact_vs_C` | exact occurrences | 1 | 1 | 33.684204060569364 | 33.68420406038772 |
| `714192.8098, 3974721.7423` | `D_exact_vs_D` | exact occurrences | 1 | 1 | 33.684204060569364 | 33.68420406038772 |
| `715591.5915, 3959342.5051` | `A_exact_vs_A` | exact occurrences | 3 | 3 | 36.78133925343151 | 36.781339253462164 |
| `715591.5915, 3959342.5051` | `C_exact_vs_C` | exact occurrences | 3 | 3 | 36.78133925343151 | 36.781339253462164 |
| `715591.5915, 3959342.5051` | `D_exact_vs_D` | exact occurrences | 1 | 1 | 36.78133925343151 | 36.781339253462164 |
| `716054.0240, 3968676.8637` | `A_exact_vs_A` | exact occurrences | 1 | 1 | 8.04113977304191 | 8.041139773197127 |
| `716054.0240, 3968676.8637` | `C_exact_vs_C` | exact occurrences | 1 | 1 | 8.04113977304191 | 8.041139773197127 |
| `716054.0240, 3968676.8637` | `D_exact_vs_D` | exact occurrences | 1 | 1 | 8.04113977304191 | 8.041139773197127 |
| `712593.6282, 3963885.3442` | `A_exact_vs_A` | exact occurrences | 1 | 1 | 26.665738948306654 | 26.665738948438538 |
| `712593.6282, 3963885.3442` | `C_exact_vs_C` | exact occurrences | 1 | 1 | 26.665738948306654 | 26.665738948438538 |
| `712593.6282, 3963885.3442` | `D_exact_vs_D` | exact occurrences | 1 | 1 | 26.665738948306654 | 26.665738948438538 |
| `695791.4718, 3948364.4290` | `A_exact_vs_A` | exact occurrences | 1 | 1 | 20.31031743052109 | 20.310317430571672 |
| `695791.4718, 3948364.4290` | `C_exact_vs_C` | exact occurrences | 1 | 1 | 20.31031743052109 | 20.310317430571672 |
| `695791.4718, 3948364.4290` | `D_exact_vs_D` | exact occurrences | 1 | 1 | 20.31031743052109 | 20.310317430571672 |
| `730250.1130, 3948038.9275` | `A_exact_vs_A` | exact occurrences | 1 | 1 | 4.292554865555211 | 4.292554865428522 |
| `730250.1130, 3948038.9275` | `C_exact_vs_C` | exact occurrences | 1 | 1 | 4.292554865555211 | 4.292554865428522 |
| `730250.1130, 3948038.9275` | `D_exact_vs_D` | exact occurrences | 1 | 1 | 4.292554865555211 | 4.292554865428522 |
| `696424.4528, 3962696.1212` | `A_exact_vs_A` | exact occurrences | 1 | 1 | 18.85105772543465 | 18.851057725332666 |
| `708064.8893, 3979367.9073` | `A_exact_vs_A` | exact occurrences | 1 | 1 | 28.205967114011045 | 28.20596711404647 |
| `708064.8893, 3979367.9073` | `C_exact_vs_C` | exact occurrences | 1 | 1 | 28.205967114011045 | 28.20596711404647 |
| `708064.8893, 3979367.9073` | `D_exact_vs_D` | exact occurrences | 1 | 1 | 28.205967114011045 | 28.20596711404647 |
| `688771.3334, 3974212.1913` | `A_exact_vs_A` | exact occurrences | 1 | 1 | 17.967268628841634 | 17.967268628736104 |
| `688771.3334, 3974212.1913` | `C_exact_vs_C` | exact occurrences | 1 | 1 | 17.967268628841634 | 17.967268628736104 |
| `688771.3334, 3974212.1913` | `D_exact_vs_D` | exact occurrences | 1 | 1 | 17.967268628841634 | 17.967268628736104 |
| `690117.4913, 3988351.5923` | `A_exact_vs_A` | exact occurrences | 2 | 2 | 13.384645880327877 | 13.38464588033691 |
| `690117.4913, 3988351.5923` | `C_exact_vs_C` | exact occurrences | 2 | 2 | 13.384645880327877 | 13.38464588033691 |
| `690117.4913, 3988351.5923` | `D_exact_vs_D` | exact occurrences | 2 | 2 | 13.384645880327877 | 13.38464588033691 |
| `722743.3998, 3957481.8879` | `A_exact_vs_A` | exact occurrences | 2 | 2 | 13.724368625674435 | 13.724368625656602 |
| `722743.3998, 3957481.8879` | `C_exact_vs_C` | exact occurrences | 2 | 2 | 13.724368625674435 | 13.724368625656602 |
| `722743.3998, 3957481.8879` | `D_exact_vs_D` | exact occurrences | 2 | 2 | 13.724368625674435 | 13.724368625656602 |
| `691926.7202, 3984247.8644` | `A_exact_vs_A` | exact occurrences | 1 | 1 | 43.09284829956751 | 43.09284829961493 |
| `691926.7202, 3984247.8644` | `C_exact_vs_C` | exact occurrences | 1 | 1 | 43.09284829956751 | 43.09284829961493 |
| `691926.7202, 3984247.8644` | `D_exact_vs_D` | exact occurrences | 1 | 1 | 43.09284829956751 | 43.09284829961493 |
| `710004.5163, 3963918.1317` | `A_exact_vs_A` | exact occurrences | 2 | 2 | 21.427726447964073 | 21.427726448001085 |
| `710004.5163, 3963918.1317` | `C_exact_vs_C` | exact occurrences | 2 | 2 | 21.427726447964073 | 21.427726448001085 |
| `710004.5163, 3963918.1317` | `D_exact_vs_D` | exact occurrences | 2 | 2 | 21.427726447964073 | 21.427726448001085 |
| `678292.4987, 3969009.9924` | `A_exact_vs_A` | exact occurrences | 1 | 1 | 22.09945281378831 | 22.099452813794603 |
| `678292.4987, 3969009.9924` | `C_exact_vs_C` | exact occurrences | 1 | 1 | 22.09945281378831 | 22.099452813794603 |
| `678292.4987, 3969009.9924` | `D_exact_vs_D` | exact occurrences | 1 | 1 | 22.09945281378831 | 22.099452813794603 |
| `720175.2035, 3965415.1894` | `A_exact_vs_A` | exact occurrences | 1 | 1 | 11.398926901034194 | 11.398926900843945 |
| `720175.2035, 3965415.1894` | `C_exact_vs_C` | exact occurrences | 1 | 1 | 11.398926901034194 | 11.398926900843945 |
| `720175.2035, 3965415.1894` | `D_exact_vs_D` | exact occurrences | 1 | 1 | 11.398926901034194 | 11.398926900843945 |
| `683211.4948, 3978663.8336` | `A_exact_vs_A` | exact occurrences | 1 | 1 | 31.18703111076491 | 31.18703111079902 |
| `662150.0000, 4003450.0000` | `A_exact_vs_A` | exact occurrences | 2 | 2 | 0.890926894299036 | 0.8909268944047917 |
| `662150.0000, 4003450.0000` | `C_exact_vs_C` | exact occurrences | 2 | 2 | 0.890926894299036 | 0.8909268944047917 |
| `662150.0000, 4003450.0000` | `D_exact_vs_D` | exact occurrences | 2 | 2 | 0.890926894299036 | 0.8909268944047917 |
| `662250.0000, 4003450.0000` | `A_exact_vs_A` | exact occurrences | 2 | 2 | 21.64280896173798 | 21.64280896165804 |
| `662250.0000, 4003450.0000` | `C_exact_vs_C` | exact occurrences | 2 | 2 | 21.64280896173798 | 21.64280896165804 |
| `662250.0000, 4003450.0000` | `D_exact_vs_D` | exact occurrences | 2 | 2 | 21.64280896173798 | 21.64280896165804 |
| `662350.0000, 4003450.0000` | `A_exact_vs_A` | exact occurrences | 2 | 2 | 42.394691028721404 | 42.394691028911296 |
| `662350.0000, 4003450.0000` | `C_exact_vs_C` | exact occurrences | 2 | 2 | 42.394691028721404 | 42.394691028911296 |
| `662350.0000, 4003450.0000` | `D_exact_vs_D` | exact occurrences | 2 | 2 | 42.394691028721404 | 42.394691028911296 |
| `662450.0000, 4003450.0000` | `A_exact_vs_A` | exact occurrences | 2 | 2 | 22.539380366182808 | 22.539380365978293 |
| `662450.0000, 4003450.0000` | `C_exact_vs_C` | exact occurrences | 2 | 2 | 22.539380366182808 | 22.539380365978293 |
| `662450.0000, 4003450.0000` | `D_exact_vs_D` | exact occurrences | 2 | 2 | 22.539380366182808 | 22.539380365978293 |
| `662550.0000, 4003450.0000` | `A_exact_vs_A` | exact occurrences | 2 | 2 | 13.202618964729657 | 13.202618964623632 |
| `662550.0000, 4003450.0000` | `C_exact_vs_C` | exact occurrences | 2 | 2 | 13.202618964729657 | 13.202618964623632 |
| `662550.0000, 4003450.0000` | `D_exact_vs_D` | exact occurrences | 2 | 2 | 13.202618964729657 | 13.202618964623632 |
| `662650.0000, 4003450.0000` | `A_exact_vs_A` | exact occurrences | 1 | 1 | 4.052400257299257 | 4.052400257299308 |
| `662650.0000, 4003450.0000` | `C_exact_vs_C` | exact occurrences | 1 | 1 | 4.052400257299257 | 4.052400257299308 |
| `662650.0000, 4003450.0000` | `D_exact_vs_D` | exact occurrences | 1 | 1 | 4.052400257299257 | 4.052400257299308 |
| `662750.0000, 4003450.0000` | `A_exact_vs_A` | exact occurrences | 2 | 2 | 18.882997847057513 | 18.88299784707186 |
| `662750.0000, 4003450.0000` | `C_exact_vs_C` | exact occurrences | 1 | 1 | 18.882997847057513 | 18.88299784707186 |
| `662750.0000, 4003450.0000` | `D_exact_vs_D` | exact occurrences | 1 | 1 | 18.882997847057513 | 18.88299784707186 |
| `662850.0000, 4003450.0000` | `A_exact_vs_A` | exact occurrences | 1 | 1 | 33.107713543273086 | 33.10771354330191 |
| `662850.0000, 4003450.0000` | `C_exact_vs_C` | exact occurrences | 1 | 1 | 33.107713543273086 | 33.10771354330191 |
| `662850.0000, 4003450.0000` | `D_exact_vs_D` | exact occurrences | 1 | 1 | 33.107713543273086 | 33.10771354330191 |
| `664650.0000, 4003450.0000` | `A_exact_vs_A` | exact occurrences | 1 | 1 | 145.9827193721531 | 145.98271937215694 |

### Cost

| set | points | seconds | ms/point |
|---|---:|---:|---:|
| frame B sample | 500 | 0.1 | 0.257 |
| frame C sample | 500 | 0.1 | 0.290 |
| groceries (census) | 550 | 0.1 | 0.202 |
| **all structures (census)** | 512,633 | 124.9 | 0.244 |
| **all cell centres (census)** | 330,502 | 91.3 | 0.276 |

Graph preparation 102 s, once. The attachment stage is cheap enough that the time box's "census it if benchmarking supports it" applies, which is why both censuses are here rather than a 500-point bound.

<!-- END GENERATED -->
