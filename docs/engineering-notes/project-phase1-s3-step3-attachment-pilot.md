# T0 ran: the attachment convention matters at one point in forty, and changes no eligibility

**2026-11-10.** Plan §0 step 3, stages 1 and 2. Stage 3 needs the comparator and is explicitly
unknown. **Figures live in `docs/experiments/t0-attachment-pilot.md`, rendered from
`t0-attachment-pilot.json` by `v2/scripts/render_t0_results.py`** — they are deliberately not
duplicated here, because two places for one figure is two places for it to drift.

## What it decided

**Nothing, by the pre-registered rule — and that is the correct outcome rather than a failure.**
Candidate sets differ between conventions and eligibility never does, which is rule 3: the choice is
open on impact until stage 3 routes the differing points. A stays the incumbent, not the endorsed
option.

What the measurement did settle:

- **Eligibility is invariant.** 0 of 843,135 points move between answerable and `OFF_NETWORK` under
  any of A, C or D. This is the only verdict-relevant effect reachable without a router, and it is
  exactly zero over both whole populations.
- **The choice is not rare.** A retains more than one candidate at 2.6–2.9% of points. Pass 26 was
  right to refuse "a handful in 512,633".
- **A and C disagree only within a record** — zero cross-record differences in 843,135 points — so
  the magnitude of that whole disagreement is bounded with no routing at all.
- **Each of A and C has exactly one representation sensitivity, in complementary directions**, and
  **D has none**. See below; this is the result nobody argued for.
- **Pass 24 F1 is real and rare** (C discarding a genuine exact tie: 2 in 512,633, 0 in 330,502).
  **Pass 24 F2 is real and common** (C's positions move under record segmentation).

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

### 3. Part of an expensive question can be answered cheaply, exactly

Stage 3 needs a routing comparator. But a journey from arclength *s* on a record of length *L* and
time *T* is `min(t_u + (s/L)T, t_v + (1 − s/L)T)` plus the connector, so moving the attachment along
**one record** changes the journey by **at most `|Δs|/L × T`** whatever the network beyond — a sound
bound, no routing. Since A and C never disagree across records, that bound covers 100% of the A-vs-C
disagreement: median about 0.3 s, over 60 s at eleven points in 843,135.

**It bounds the magnitude, not the rate.** How often a whole-minute verdict moves depends on how
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
  item 1 (exact geometry arithmetic). The pilot enumerates the points that need routing —
  13,196 structures and 7,495 cell centres for A against C — so stage 3 costs about 2.5% of a full
  paired comparison rather than all of it.
- **The A/B/C/D choice** is the owner's where the evidence does not select one. D is now the only
  position-invariant candidate, which is an argument for it; its price is that it is defined by an
  exact rational minimum (§12 item 1 again) and discards every banded near-miss, which is where the
  only unbounded differences in this pilot live.
- **One limitation of the position comparison, stated rather than discovered later:** it compares
  locations, so it merges the two passes of a self-crossing road at one XY — which §2.2 insists are
  one place and two decisions. The merge applies on both sides of a transformation, so a difference
  is still detected unless the change lies entirely inside such a pair. A complete test compares
  remaining-route options, which is routing.

Related: [[feedback-decide-by-measurement-not-by-argument]],
[[feedback-verify-the-shape-of-the-risk]], [[project-phase1-s3-design]],
[[project-phase1-s3-step2-conditional-estimand]].
