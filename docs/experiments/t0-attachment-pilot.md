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
correction. The figures below are **rendered from `v2/data/t0_attachment_pilot.json` by
`v2/scripts/render_t0_results.py`**, not transcribed — this project has produced wrong figures by
transcription three times, and `--check` fails if the document and the artifact drift apart. The
prose outside the generated block is written by hand.*

### The verdict against the pre-registered rule

**Rule 3: the choice is open on impact.** Candidate sets differ and eligibility never does, so no
convention is rejected and none is endorsed by the rule. A stays the provisional baseline because it
is the incumbent, not because the pilot endorsed it. Everything below is what the measurement added
past that, and two of the results are sharper than rule 3 anticipated.

### The stage was cheap enough to census, so a bound became a count

The time box says to benchmark the first batch before committing to a larger sample or a census, and
to census the attachment stage if benchmarking supports it. At about **0.2 ms per point** it does:
both populations — every structure centroid and every cell centre — ran in under three minutes. So
where the pre-registration could only have offered "zero events in 500, one-sided 95% bound
0.5974%", the tables below carry exact counts over **843,135 points**. That was available for the
price of reading a benchmark before fixing a sample size.

### Eligibility never changes — exactly, not approximately

**0 of 843,135 points** change eligibility between A, C and D. Eligibility is the only
verdict-relevant effect observable without the comparator: a point with an in-cap candidate under
one convention and none under another moves between answerable and `OFF_NETWORK`. Over the whole of
both populations that never happens. §2.2's worry that "two disconnected roads 1 m either side of a
point are equally near and can differ by 900 s" is a real hazard for *which* journey gets reported;
on this graph it is not a hazard for *whether* one does.

### The convention matters at about one point in forty, which is not rare

On the two censuses A retains more than one candidate at **2.611%** of cell centres and **2.894%**
of structures, and A's candidate set differs from C's at **2.268%** and **2.574%**. Pass 26 was right
to refuse "a handful in 512,633": the honest figure is four orders of magnitude larger than that
phrase suggests. The three pre-registered sets agree — 2.2%, 2.0% and 3.45% — but at *n* = 500 they
could only ever have seen about a dozen such points. The census is what pins the rate.

### A and C disagree only ever about *where on one record*

**Zero cross-record differences between A and C in 843,135 points.** Every A≠C point is a dispute
about which position along one polyline to attach to, which is exactly the class the impact bound
covers — so the magnitude of the entire A-vs-C disagreement is bounded **without routing anything**.
The median bound is about **0.3 s**. The tail is not negligible: it exceeds 60 s at 8 structures and
3 cell centres, eleven points in 843,135.

A-vs-D is different in kind. D drops every banded near-miss, so **1,232 structures and 728 cell
centres** differ across records, and for those nothing short of the comparator bounds the
difference. That asymmetry is why the two comparisons are reported separately rather than averaged.

A small gap in the A≠C row is worth naming because it is the only place the two columns come apart:
candidate sets differ at 13,196 structures and **positions** at 13,191. The five-point difference is
the float-against-exact clamp — the occurrence key is built from the binary64 clamp, so two
descriptions of a shared vertex merge into one candidate while `exact_segment_sq` clamps in exact
arithmetic and can place them a hair apart. It is five points in 512,633 and it is reported rather
than rounded away.

**A bound is not a rate.** `|Δarclength| / L × T` bounds how much a journey time *could* move; it
says nothing about how often a whole-minute verdict actually moves, which depends on how close the
time sits to a threshold. Turning the bound into a verdict rate needs the times, which needs the
comparator. Using the product's own arrival times instead would compare one side of E1 to itself,
which is the error §2.6 exists to prevent.

### The reason C was reverted is real, and it is four parts per million

Revision 10 reverted revision 9 partly because C compares *computed* residuals for exact equality
and so can discard a genuine geometric tie — pass 24 F1, shown on a constructed record whose two
arms are at exact rational squared distance 1 but compute as 0.9999999999999999 and 1.0. The exact
rational diagnostic finds that on real geometry at **2 of 512,633 structure centroids and 0 of
330,502 cell centres**.

It is real. It is also about 4 × 10⁻⁶. Genuine exact ties are far more common than the failure to
keep them — **422 structures and 411 cell centres** have two or more candidates at the exact minimum
— and C preserves nearly all of them, because positions that are genuinely equidistant usually
compute equal too. The arithmetic loses a tie only in the narrow case where it does not.

This does not make C correct. It does mean the first of revision 10's two reasons, taken on its own,
is a thin basis for a convention choice, and this is the first thing to say so with a number.

### Counting candidates is not measuring the answer, and that distinction decides this section

The transformation check first compared candidate **counts**, and on that basis every convention
looked representation-dependent: a lawful record split moved A, C and D alike. That reading was
wrong, and the reason is worth keeping. A record split turns one shared-vertex occurrence into two —
`(r,"v",k)` becomes `(r_a,"v",1)` and `(r_b,"v",0)` — so the count rises while **both candidates sit
at the same physical position**, and a set of candidates at the same places minimises to the same
journey under every objective. The count changed; the answer could not.

So both are measured, and only the second one bears on a reported time. Comparing positions at a
1 µm tolerance — far below anything physical, far above the ~2.3 × 10⁻¹⁰ m spacing of binary64 at
UTM magnitudes — gives a clean and quite different picture:

| lawful re-expression | what it changes | A | C | D |
|---|---|---|---|---|
| `subdivide` — insert every segment's midpoint | vertices, same records | **moves** | — | — |
| `split_every_segment` — one record per segment | records, same vertices | — | **moves** | — |
| `split_midpoint` — cut each record at its arclength midpoint | both | **moves** | **moves** | — |

Three things follow, and the third was not predicted by anybody.

**§2.2's claim about A is confirmed, not refuted.** "A degree-two record split does *not* move it"
holds: under a pure record segmentation A's candidate count changes but **not one retained position
does**. My first reading of the count table had this backwards.

**Pass 24 F2 is confirmed on real geometry.** C's positions *do* move under record segmentation —
the record-dependence revision 10 reverted revision 9 for. Unlike F1's four-parts-per-million, this
one is common.

**D is the only convention whose retained positions survive all three re-expressions.** That is a
real argument for the option nobody argued for, and it should be stated with its price: D is defined
by an **exact rational** global minimum, which is §12 item 1 — the open geometry-arithmetic item —
rather than something the current float pipeline supplies, and it discards every banded near-miss,
which is the 1,232 and 728 cross-record differences whose impact nothing here bounds.

`split_midpoint` is **confounded by construction** and is reported only for completeness: it inserts
a vertex *and* splits a record, so a convention moving under it may be responding to either. It is
not evidence about record segmentation, and `split_every_segment` — same vertices, new records — is
the clean test.

**The three transformations are not of equal strength.** `subdivide` adds one clamped endpoint per
segment, `split_every_segment` one record boundary per segment, `split_midpoint` one per record. The
rates in the generated table are not a ranking of sensitivity between conventions; what they support
is the qualitative pattern above.

### What this changes about the choice

Nothing is settled, and the pre-registered rule says so. But the evidential position has moved:

| | before T0 | after T0 |
|---|---|---|
| "a handful in 512,633" | the phrasing pass 26 refused | **2.6–2.9% of points**, counted |
| eligibility risk | unmeasured | **0 of 843,135**, exact |
| A vs C magnitude | unknown without routing | **bounded everywhere**: median 0.3 s, >60 s at 11 points |
| C discards a genuine tie (F1) | a constructed counterexample | **2 in 512,633**, 0 in 330,502 |
| C depends on record segmentation (F2) | a constructed counterexample | **confirmed, and common** |
| A depends on subdivision | a constructed counterexample | **confirmed, and common** |
| A under record segmentation | claimed invariant | **invariant in position**, as claimed |
| D | nobody's candidate | **the only position-invariant convention**, at the price of exact arithmetic and unbounded near-miss loss |

**What would settle it is stage 3**, which needs the development comparator — plan §0 step 4, itself
gated on §12 item 1. The time box requires this be said rather than substituted for: **verdict
impact is explicitly unknown.**

One thing the pilot has made cheap for whoever runs stage 3: the points needing a paired route are
enumerated rather than guessed. Only the points whose candidate sets differ need one — **13,196
structures and 7,495 cell centres** for A against C, about 2.5% of the routing a full comparison
would have cost.

### A note on what was nearly published instead

Two figures in this document were wrong in a first draft and both were caught by asking what the
number was a number *of*. "Seven of 25 frame C points have an exact tie" counted raw per-segment
*descriptions* where one occurrence described twice appears as two — on a set where no point had two
candidates. And "every convention is representation-dependent" counted candidates where it should
have counted positions, which inverted the conclusion about A and about D. Both are the failure mode
`feedback-decide-by-measurement-not-by-argument` records from 2026-11-10, two days after it was
written, in the first measurement taken since.

---

### The measured figures

<!-- BEGIN GENERATED: scripts/render_t0_results.py -->

**The graph and the record set.** 539,814 nodes, 1,436,992 directed graph edges, **713,452 physical records** (2.0141 graph edges per record — a symmetrised walk graph carries two directed edges per record, so a ratio near 2.0 is the pedestrian reverse and not parallel roads).

**Pinned.** graph `2ee931bc0f2a…`, profile `speeds-v0+7bd6d52dbf33d8fe`, grid `grid-v0+7ab61db26b3cc98e`, places `26ad5ea1a4fd…`, `attach_tie_m` 0.01, caps 200 m / 300 m, shapely 2.2.0, numpy 2.5.4.

### How often a point has more than one candidate

| set | points | A | C | D | on >1 record (A) | >1 occurrence on one record (A) |
|---|---:|---:|---:|---:|---:|---:|
| frame B sample | 500 | 11 (2.2000%) | 0 (0.0000%) | 0 (0.0000%) | 0 | 11 |
| frame C sample | 500 | 10 (2.0000%) | 2 (0.4000%) | 1 (0.2000%) | 2 | 8 |
| groceries (census) | 550 | 19 (3.4545%) | 12 (2.1818%) | 0 (0.0000%) | 12 | 7 |
| **all structures (census)** | 512,633 | 14,833 (2.8935%) | 1,654 (0.3226%) | 422 (0.0823%) | 1,654 | 13,211 |
| **all cell centres (census)** | 330,502 | 8,629 (2.6109%) | 1,139 (0.3446%) | 411 (0.1244%) | 1,139 | 7,511 |

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

| set | points | A candidates C drops | …that are genuine exact ties | points with ≥2 candidates at the exact minimum |
|---|---:|---:|---:|---:|
| frame B sample | 500 | 11 | **0** | 0 (0.0000%) |
| frame C sample | 500 | 8 | **0** | 1 (0.2000%) |
| groceries (census) | 550 | 7 | **0** | 0 (0.0000%) |
| **all structures (census)** | 512,633 | 13,205 | **2** | 422 (0.0823%) |
| **all cell centres (census)** | 330,502 | 7,505 | **0** | 411 (0.1244%) |

### The impact bound, with no routing

`|Δarclength| / L × T` plus the band's connector difference, which bounds the journey-time change whatever the network beyond the record's endpoints. Applies only where the disputed candidates sit on the **same record**; across records nothing short of routing bounds it.

| set | pair | differing | same record | cross record (unbounded) | median | max | >1 s | >30 s | >60 s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| frame B sample | A vs C | 11 | 11 | 0 | 0.3043 s | 2.38 s | 2 | 0 | 0 |
| frame B sample | A vs D | 11 | 11 | 0 | 0.3043 s | 2.38 s | 2 | 0 | 0 |
| frame C sample | A vs C | 8 | 8 | 0 | 0.5605 s | 0.84 s | 0 | 0 | 0 |
| frame C sample | A vs D | 9 | 8 | 1 | 0.5605 s | 0.84 s | 0 | 0 | 0 |
| groceries (census) | A vs C | 7 | 7 | 0 | 0.1287 s | 1.39 s | 1 | 0 | 0 |
| groceries (census) | A vs D | 19 | 7 | 12 | 0.1287 s | 1.39 s | 1 | 0 | 0 |
| **all structures (census)** | A vs C | 13,196 | 13,196 | 0 | 0.2794 s | 127.41 s | 726 | 14 | 8 |
| **all structures (census)** | A vs D | 14,411 | 13,179 | 1,232 | 0.2793 s | 79.16 s | 719 | 7 | 2 |
| **all cell centres (census)** | A vs C | 7,495 | 7,495 | 0 | 0.3431 s | 80.24 s | 577 | 6 | 3 |
| **all cell centres (census)** | A vs D | 8,218 | 7,490 | 728 | 0.3428 s | 80.24 s | 574 | 3 | 1 |

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

### Cost

| set | points | seconds | ms/point |
|---|---:|---:|---:|
| frame B sample | 500 | 0.1 | 0.274 |
| frame C sample | 500 | 0.1 | 0.281 |
| groceries (census) | 550 | 0.1 | 0.207 |
| **all structures (census)** | 512,633 | 118.2 | 0.231 |
| **all cell centres (census)** | 330,502 | 75.5 | 0.228 |

Graph preparation 109 s, once. The attachment stage is cheap enough that the time box's "census it if benchmarking supports it" applies, which is why both censuses are here rather than a 500-point bound.

<!-- END GENERATED -->
