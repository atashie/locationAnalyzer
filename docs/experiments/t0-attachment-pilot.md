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

*Written after the run. Nothing above is edited once this section exists; a correction appears here
as a correction.*
