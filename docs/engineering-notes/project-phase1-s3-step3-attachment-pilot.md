# T0 ran: the attachment convention matters at one point in forty, and changes no eligibility

**2026-11-10, corrected 2026-11-11 after Codex pass 36 (3 High, 5 Medium, 1 Low — all nine
reproduced).** Plan §0 step 3, stages 1 and 2. Stage 3 needs the comparator and is explicitly
unknown. **Figures live in `docs/experiments/t0-attachment-pilot.md`, rendered from
`t0-attachment-pilot.json` by `v2/scripts/render_t0_results.py`** — they are deliberately not
duplicated here, because two places for one figure is two places for it to drift. That write-up's
Part 2 opens with the correction table; this note carries only the lessons.

## What it decided

**Nothing, by the pre-registered rule — and that is the correct outcome rather than a failure.**
Candidate sets differ between conventions and eligibility never does, which is rule 3: the choice is
open on impact until stage 3 routes the differing points. A stays the incumbent, not the endorsed
option.

What the measurement did settle:

- **Eligibility is invariant on every point measured** — all structure centroids, all cell centres
  and the three pre-registered sets. The only verdict-relevant effect reachable without a router,
  and nothing in the convention moved it. A cell-centre census is **not** a census of frame C,
  whose population is the cell's area, so this does not establish it throughout frame C.
- **Two different rates, and only one is about ambiguity.** About 30% of points have several
  candidates under the design's record definition, almost entirely coincident parallel roads at
  **one position** — zero points anywhere have two *distinct positions* at the exact minimum. The
  decision-relevant rate is the disagreement rate, 2.57% of structures, and it is **unchanged** by
  a record definition that moved the prevalence rate tenfold.
- **A and C disagree only within a record** — zero cross-record differences anywhere — but that is
  not enough for the bound: 7,324 of 13,196 structure points are bounded and 5,872 sit on a
  one-way record where availability itself can change.
- **Each of A and C has exactly one representation sensitivity, in complementary directions**, and
  **D's positions did not move under any transformation preserving exact geometry**. See below.
- **Pass 24 F1 was not observed.** C discarded no genuine exact tie anywhere. What it did was keep
  a position that is exactly *farther* twice in 512,633 structures — a float/exact inversion, which
  is the same family and not the consequence the design described. **Pass 24 F2 is real and
  common** (C's positions move under record segmentation).

## Four things worth reusing

### 1. Benchmark before fixing the sample size, because the answer may be a census

The time box says "benchmark the first batch before choosing a larger sample or a census" and
"census the cheap attachment stage if benchmarking supports it". It did: 0.2 ms per point made both
populations affordable in under three minutes. That replaced "zero in 500, one-sided 95% bound
0.5974%" with exact counts — and the pre-registration had already stated, before the run, that a
500-point sample could not reach the 0.167% budget either way.

**The sample size was a parameter of the cost, and the cost was unmeasured until someone measured
it.** Thirty seconds of benchmarking bought four orders of magnitude of precision.

### 2. Count what the decision needs, not what is easy to count — twice in one measurement

Both are the failure mode `feedback-decide-by-measurement-not-by-argument` records, in the first
measurement taken after it was written.

**First: descriptions against candidates.** "Seven of 25 frame C points have an exact tie at the
global minimum" was counted over raw per-segment positions, where one occurrence described twice —
parameter 1 on segment *k*, parameter 0 on segment *k*+1 — appears as two entries that collapse in
deduplication. The same run reported that no frame C point had more than one candidate. Both
statements were true of different populations and the pair is incoherent.

**Second, and it inverted a conclusion: candidates against positions.** The transformation check
compared candidate **counts**, and on that basis every convention looked representation-dependent —
a lawful record split moved A, C and D alike. It is bookkeeping. A record split turns one
shared-vertex occurrence into two, so the count rises while both candidates stay at the same
physical place, and candidates at the same places minimise to the same journey under every
objective. Comparing **positions** instead reverses it: under pure record segmentation A's positions
do not move at all (confirming §2.2's claim, which the count reading had appeared to refute), C's
do, and D's never move under any lawful re-expression tested.

**The draft that nearly shipped said "A is not uniquely representation-dependent; every convention
moves."** The opposite is true of the quantity that determines an answer.

### 3. Part of an expensive question can be answered cheaply — but say which question

Stage 3 needs a routing comparator. A journey from arclength *s* on a record of length *L* and time
*T* is `min(t_u + (s/L)T, t_v + (1 − s/L)T)` plus the connector, so moving the attachment along
**one record** changes that minimum by at most `|Δs|/L × T` whatever the network beyond. Sound, no
routing — **and it is a bound on objective 1, which I reported as a bound on the journey time.**

Pass 36 F2 is the correction and it is the most useful thing in this note. Design §2.1's objective
2 is the time along the **cost**-minimising path: selection by cost, reporting by time. An
arbitrarily small cost change can switch the selected route, so the reported time can jump without
limit — a 0.0129 s bound against a 120.011 s objective-2 move, the size of an apportioned
restricted-access penalty. Nothing local can bound that. **And "same record" was not sufficient
either:** on a one-way record a moved attachment can leave no legal journey at all, which no
difference in seconds describes, and that is 5,872 of 13,196 A≠C structure points.

So the bound survives, scoped: **objective 1, both directions legal**, which covers 55% of the
A-vs-C disagreement on structures, and objective 1 is what E1 is defined against. Two lessons, not
one:

- **A bound in one metric is not a bound in another when selection and reporting use different
  metrics.** "Selection is by cost, reporting is by time" is written down in this project in three
  places and I still derived a time bound from a time identity while the product reports a
  cost-selected time.
- **A bound also has to cover existence, not just magnitude.** A quantity that can become undefined
  is not bounded by any number of seconds.

**And it bounds the magnitude, not the rate.** How often a whole-minute verdict moves depends on how
close each time sits to a threshold, which needs the times. Substituting the product's own arrival
times would compare one side of E1 to itself — the error §2.6 exists to prevent — so the rate stays
unknown and is reported as unknown.

### 4. A pre-registration is only a pre-registration if it is in history first

`docs/experiments/t0-attachment-pilot.md` is written in two parts and **Part 1 was committed before
the run** (`14f9219`), with the budget derived from §8's construction gate rather than invented: E1b
is gated at 1.0%, the design names six independent construction choices that can move a verdict, and
an equal share gives the attachment convention 0.167%. The pre-registration also states what the
pilot *cannot* do — certify compliance with that budget at *n* = 500 — before the numbers could
influence the claim.

Part 2's figures are **rendered from the artifact**, not transcribed, and `--check` fails if the
document and the JSON drift apart. The artifact lives under `docs/experiments/` rather than
`v2/data/` for the same reason: nothing under `v2/data/` travels with a clone, and a rendered figure
whose source does not travel is a figure nobody can re-derive.

## What is open

- **Stage 3**, the verdict impact, needs the development comparator: plan §0 step 4, gated on §12
  item 1 (exact geometry arithmetic). **It cannot be shortened to the origins whose own attachments
  differ** — a *destination's* attachment change can affect any origin, which the plan's stage-3
  text says explicitly and which pass 36 F3 demonstrated with an origin whose A and C attachments
  agree and whose only journey disappears when a destination moves. Seven grocery sets differ
  between A and C. My "2.5% of a full paired comparison" is withdrawn, and so is the claim that the
  affected points are enumerated: the artifact holds counts.
- **The A/B/C/D choice** is the owner's where the evidence does not select one. D is now the only
  position-invariant candidate, which is an argument for it; its price is that it is defined by an
  exact rational minimum (§12 item 1 again) and discards every banded near-miss, which is where the
  only unbounded differences in this pilot live.
- **One limitation of the position comparison, stated rather than discovered later:** it compares
  locations, so it merges the two passes of a self-crossing road at one XY — which §2.2 insists are
  one place and two decisions. The merge applies on both sides of a transformation, so a difference
  is still detected unless the change lies entirely inside such a pair. A complete test compares
  remaining-route options, which is routing.

### 5. Nine findings, and the review was worth more than the measurement

Pass 36 returned three High and five Medium against a write-up I had already corrected twice. Two of
the Highs were against the claims I had put at the top. The pattern across all nine is worth more
than any one of them:

| the defect | what it had in common |
|---|---|
| the bound bounded objective 1, not the reported time | a claim about a quantity *adjacent* to the one that matters |
| "2 genuine exact ties" were unique minima | a predicate that is *necessary* for a tie reported as sufficient |
| stage 3 restricted to 2.5% of origins | a cost estimate that ignored a dependency the plan states |
| a record was production's geometry group | one definition's counts reported as another's |
| `split_midpoint` changed a road's length | a transformation called lawful without checking the invariant |
| the transformed window lost its slack | a comparison whose two sides were not computed alike |
| `positions_differ` sorted lexicographically | a tolerance that matching order can defeat |
| cell centres as a census of frame C | a population substituted for a nearby one |
| the sample rates were the wrong column | a figure read from the adjacent column |

**Every one is a mismatch between the thing measured and the thing claimed, and not one is an
arithmetic error.** The code computed what it was told to compute, in all nine. That is the shape
this project keeps producing, and the only thing that has reliably found it is an adversary with
the data in hand — not review of the reasoning, which I did twice before publishing.

What the pass also did, which is worth recording because a review that only finds fault is easy to
discount: it reproduced the enumeration against full enumeration and found no omissions, confirmed
the A/C/D filters and ordering against the design, confirmed the pre-registration precedes the run
in git, confirmed `--check` fails on a drifted document, failed to bypass `read_frame`, and agreed
that **rule 3 is the correct outcome**.

Related: [[feedback-decide-by-measurement-not-by-argument]],
[[feedback-verify-the-shape-of-the-risk]], [[project-phase1-s3-design]],
[[project-phase1-s3-step2-conditional-estimand]].
