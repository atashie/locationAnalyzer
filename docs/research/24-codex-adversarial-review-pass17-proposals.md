# Codex adversarial review, pass 17 — the pass-16 record and the three proposals

**Date:** 2026-11-05. **Model:** gpt-6.1-sol. **Head at review:** `3a02502`. **Prompt:**
`codex-pass17-prompt.md` (scratchpad).

**Verdict: A — adopt with changes. B — reject as written. C — adopt with changes.** Plus eight
defects in the proposal's own reasoning, two of which are errors in how I recorded pass 16.

> "Revision 4 should be a frozen measurement specification backed by an executable comparator and a
> conformance suite. It should retain both population frames, measure abstention separately, and
> preserve full-frame directional error estimands unless conditional rates are explicitly justified
> and redesigned."

This was the first pass aimed at proposals rather than a revision, and it was the right move: it
rejected one proposal outright, replaced the reasoning behind a second, and supplied the answer to
the question I had flagged as unresolved.

## First: two errors in my record of pass 16

- **The severity count was wrong.** Pass 16 was **6 High / 10 Medium / 2 Low**, not 8/8/2. The Highs
  are F1, F2, F3, F5, F6, F7; **F4 and F16 are Medium.** This was not cosmetic — the inflated High
  count is what my methodological diagnosis leaned on.
- **I invented a tally and attributed it to the review.** "Eight fully resolved, seven partly
  resolved with a new defect, three opposite-sign repairs" was **my** construction, not Codex's.
  Its disposition table has overlapping rows and only three say "resolved". Two opposite-sign repairs
  are confirmed (F1, F2); the rest of the partition was unsupported.

Both are corrected in `23-...md` with the correction visible rather than silently edited. Seven
qualifications I dropped from individual findings are also listed there for revision 4.

## Part 1 — my own findings, verified and qualified

**1.1 holds, with the heading too absolute.** Every count reproduced, and Codex independently
reprojected all 522,160 geometries and **re-binned the centroids to reproduce the saved
buildings-per-cell raster exactly**. But 17.41% and 0.71% are **`OFF_NETWORK` reason shares, not
abstention rates** — E0 is threshold-dependent:

| threshold | frame C UNKNOWN | frame B UNKNOWN |
|---|---|---|
| 10 min | **16.6722%** | **0.6576%** |
| 15 min | 17.3200% | 0.7064% |
| 25 / 45 min | 17.4102% | 0.7134% |

And "no reallocation can fix it" is true only for *the unchanged product, the full-area estimand and
the all-UNKNOWN-as-error rule*. It does not establish that every estimand or sampling change is
useless — Codex lists four amendments that would change the picture, the first being the one it then
recommends.

**1.2 was right about the facts and wrong about the inference.** The invariant is **not** that both
objectives choose the same edge — their disagreement is deliberate. It is:

> "Each objective's attachment weights, node search, selected path and reported time must describe
> the same objective and compatible graph."

So revision 3's time projection is **necessary**; combining it with the cost-selected attachment
index is what is defective. My "a worse failure than the one it fixed" was unsupported — no ordering
of the two failures is established.

**And the two-index prescription is incomplete.** Codex executed the 2 × 2 on two consecutive 100 m
segments with coincident alternatives (time 1/cost 100 and time 10/cost 10), origin halfway along the
first:

| pairing | reported |
|---|---|
| time index + time-minimum nodes | **1.5** — correct objective 1 |
| cost index + cost-selected nodes | **15** — correct objective 2 |
| time index + cost-selected nodes | 10.5 — incorrect hybrid |
| cost index + time-minimum nodes | 6 — incorrect hybrid |

Correct pairing works, but six further things are required: coordinate destinations and connector
charging in **both** objectives; legal directed same-edge candidates competing with network routes;
recoverable selected edge, destination and path identities; a **frozen tie rule** applied
consistently across projection, attachment and reconstruction; explicit partial-edge cost rules
including penalty apportionment; and both views derived from the same frozen graph preparation.

**A production non-determinism, found in passing.** With equal-cost coincident alternatives of time
10 and 1, **reversing insertion order changes the selected reported time from 10 to 1** — in both the
CSR and the edge index. Two indices do not resolve it; a frozen tie rule does.

**And a cost warning:** the real index holds **713,452 geometries** whose six numeric arrays alone
occupy **34.2 MB**, excluding geometry, the object array, the STRtree and build dictionaries. Share
the immutable geometry and tree with objective-specific weight views, or process objectives
sequentially — do not build two complete indices.

## Proposal A — adopt with changes

Separating observed abstention from unidentified directional error repairs F5's conceptual error. My
*implementation* of it introduced two new problems.

**My conditioning was wrong.** "Only PASS can produce E1b" does not imply the estimands should be
conditioned on claim-making. Keep them **full-frame joint probabilities**:

> `e_b = Pr(P = PASS, C = FAIL)`, `e_a = Pr(P = FAIL, C = PASS)`, and separately
> `a = Pr(P = UNKNOWN)`.

Product UNKNOWN is then a **known non-event** for either directional error while staying visible
under E0 policy. This preserves the frame interpretation, the thresholds and the allocation
arithmetic — all of which my conditional version would have broken, and "report the denominator" does
not repair: executed, **417 claim-making observations with one error gives a 1.1325% upper bound,
exceeding 1%**, against 0.9452% at 500.

**My three buckets were not a partition** — agreements are missing, and comparator ignorance can
occur at an abstaining point too. The full cross-tab:

| product | comparator PASS | comparator FAIL | comparator unresolved |
|---|---|---|---|
| PASS | agreement | **E1b** | unresolved potential E1b |
| FAIL | **E1a** | agreement | unresolved potential E1a |
| UNKNOWN | **E0** | **E0** | E0, plus unresolved comparator status |

Invalid artifacts and layer-wide publication failures need explicit run-failure handling and must not
vanish by row deletion.

**E0 does not need sampling at all** — the insight I missed. For a frozen raster-lookup product the
UNKNOWN verdict is known for **every** cell and threshold, so E0 is a **census**:

> `a_B(T) = Σ b_i · 1{P_i(T) = UNKNOWN} / Σ b_i`,  `a_C(T) = Σ 1{P_i(T) = UNKNOWN} / N_C`

computed after freezing the actual evaluation behaviour — on the *published representation* if export
or reprojection changes it. No sampling uncertainty about E0 whatsoever.

### The E0 threshold: my reasoning was too strong, and four policies exist

I argued that any threshold informed by the current artifact is impermissibly reverse-engineered.
Too strong: "a threshold chosen solely to let this artifact pass is weak evidence of adequacy", but a
requirement **established transparently** from user cost, supported coverage or an explicit
non-regression objective may legitimately use existing information. What matters is the justification
and the resulting claim.

| policy | shape | limit |
|---|---|---|
| **A absolute coverage** | `E0 ≤ 1 − c_min`, with `c_min` justified from the product promise | nothing in the repository fixes a value |
| **B decision-loss budget** | `λ₀a + λ_b e_b + λ_a e_a ≤ B` in common units | weights and budget are a product decision |
| **C explicit non-regression** | freeze a reference, require no increase by reason and subgroup | principled, but proves nothing about whether the reference was *adequate* |
| **D service obligation** | every unresolved request gets an explicit unavailable result or a declared fallback | "a system that announces 'unavailable' everywhere is transparent and still useless" |

**Recommended: an explicit coverage requirement plus a handling obligation.** And the operative
instruction for now:

> "If the owner has not established the coverage requirement, build the instrument and report E0, but
> **block coverage certification**. Do not invent a percentage merely to finish revision 4."

## Proposal B — rejected as written

Three reasons, each independent.

1. **My "no S3 data exists" defence fails.** Relevant outcome information already exists: the
   proposal uses observed coverage to argue for removing a gate that those very observations make
   hard to satisfy. That is an **informed redesign** — legitimate, perhaps, but it must be recorded
   as one, and the absence of *newly sampled comparator* outcomes does not make it innocent.
2. **It demotes far more than abstaining ground.** B would make **all** frame-C results descriptive,
   including false PASS and false FAIL across rendered ground — yet the motivation concerns only
   truthful UNKNOWN on off-network ground. **Once A separates E0, that motivation no longer supports
   demoting area-frame directional fidelity at all.**
3. **96.6% empty is not 96.6% irrelevant.** It does not establish that empty cells have no future
   residential use, that paths through them cannot matter, or that their rendered state cannot affect
   a decision. And frame B counts **structures, not households**, so my household rationale does not
   turn it into a residential population.

Beyond the statistics, the map, the constraint algebra, `needs_recomputation` and the "why is this
out?" explanation all operate on **cells** regardless of whether a structure stands there. Those are
**conformance obligations**, not rates that can safely become descriptive: PASS/FAIL/UNKNOWN
decoding, known-failure-beats-unknown, threshold and horizon boundaries, recomputation eligibility,
every failing criterion, and faithful rendering of unavailable versus excluded ground. The existing
worker shows why — it carries a binary inclusion mask and treats its sentinel as failing.

**And my blanket rejection of different frame-C thresholds was wrong.** Different intended uses can
justify different requirements principledly — for example promising complete *status labelling* over
the whole map while promising a *numerical answer* only inside an independently defined service
domain. What must not happen is an unexplained UNKNOWN and a falsely included region inheriting the
same tolerance merely because both live in frame C.

## Proposal C — adopt with changes, but the diagnosis does not survive

**The diagnosis was wrong.** Not every finding is "existing code does something different from clear
prose": F1 specifies *different mathematical quantities*; F2 contains an *invalid implication*; F5
*confuses* abstention with directional error; F7 *lacks required information*; F6 specifies an
*invalid certification sequence*.

> "A program can faithfully implement each defective instruction. Types will not establish that two
> floating-point values represent the same objective, that a bound is sound, or that an acceptance
> policy has the intended meaning."

And the fatal rejoinder to "every one would have surfaced within minutes": **fixtures derived from
the same mistaken premise enforce the defect — and the plan already contains examples**, namely my
bootstrap-widening assertion and my E3 fixture.

**The boundary needs replacing too.** "Choices that could change the measured rate stay predeclared"
fails literally, because *correcting an implementation error* changes the measured rate. The
replacement:

> **Freeze the quantity and its observable decision rules. Implementations may vary only while
> preserving those rules across admissible inputs.**

| case | freeze (semantics) | free (implementation) |
|---|---|---|
| F1 aggregation | destination eligibility, total objective, connector contributions, tie rule, reported quantity | search algorithm, batching |
| F2 bounds | metric, strictness, applicability, verdict implication | how a valid certificate is computed |
| F3 alternatives | legal alternatives, objective, selected-path meaning | index layout, projection method |
| F4 partial traversal | direction, partial time/cost, same-edge candidates, connector rules | virtual nodes vs analytic candidates |
| F7 persistence | information and identities sufficient to reproduce reports | storage format, layout |
| F16 wire | observable decoded statuses, bounds, versions, algebra | byte representation where equivalent |

So partial traversal **cannot** move wholesale into "mechanics": its arithmetic follows a model whose
penalty treatment, direction and candidate set must be chosen first. A schema is likewise not purely
mechanical when omitting a field changes what can be identified.

**And my properties idea is insufficient on its own.** Executed counterexample: in objective 2,
adding a *cheaper* destination **increases** reported time from 10 to 100 s — correct for
cost-selected-time reporting, so even "monotonicity" needs an objective-specific statement. Two
implementations can respect direction and sound bounds and still disagree because one charges
destination connectors and the other does not.

**Predeclaration is not restricted to prose.** Revision 4 should freeze five things: a short
normative mathematical specification; a versioned reference implementation; independently derived
expected results on constructed cases; configuration and artifact digests; and a change policy
distinguishing equivalent implementation changes from semantic amendments.

## The proposals are not a complete revision-4 plan

**Ten of pass 16's eighteen findings are untouched by all three proposals** — F8 (E2 missing-pair
population), F9 (variance wording), F10 (bootstrap test), F11 (E3 fixture), F12 (diagnostic
comparison), F13 (reason/verdict exception), F14 (development exclusion), F15 (repeated attempts),
F17 (extraction diagnostic), F18 (sampling test) — and **F6 has no concrete repair**. "Mentioned as
implementation work" is not resolved.

## Eight defects in the proposal's own reasoning

1. Wrong severity count and unsupported repair tally — both of which propped up the diagnosis.
2. Off-network reason share presented as threshold-independent abstention.
3. A introduces conditional estimands without redesigning thresholds or allocation.
4. The three-way accounting omits agreement and mishandles overlapping comparator ignorance.
5. "A threshold is supplied, therefore both gates are reachable" is **false** — directional errors,
   comparator uncertainty, denominator sizes and E0 requirements can still prevent passage.
6. B's timing defence ignores relevant observed outcomes.
7. The two-index prescription omits coordinate routing, ties and partial-cost semantics.
8. The diagnosis overpromises fixture-first discovery and treats semantic choices as mechanics.

My "what I would do on each answer" table was also wrong in four of six rows, including a **false
dichotomy**: rejecting B does not force looser thresholds or an abstention-excluded estimand, because
full-frame directional errors plus a separate E0 policy is a third option — the one now recommended.

## What survived attack

The saved coverage and empty-cell counts; the structure-versus-area difference; the population-level
incompatibility of the current frame-C UNKNOWN charging with its threshold; separate abstention and
directional-error accounting; objective-specific attachment and node views; coordinate attachment
with modelled connectors; separate structure and area probability samples; the removal of spatial
DEFF and block machinery; the original allocation arithmetic **for its original full-frame
estimands**; unpooled diagnostics and finite-population claim boundaries; the E1/E2/E3 separation;
the scoped 120-minute encoding decision subject to the wire-contract repairs; and building and
validating the comparator before certification.

**PROP has not silently amended the operative design** — verified: D and P still hash to the SHA-256
values recorded at pass 16.

## What revision 4 must be

1. **Correct the review record** — 6 High / 10 Medium / 2 Low, and drop the unsupported tallies.
2. **Define E0 independently**, computed as a **census** by frame, threshold and reason. Establish a
   justified coverage requirement or explicitly block coverage certification.
3. **Retain full-frame directional E1a/E1b** as joint probabilities; bound comparator uncertainty only
   in the direction the observed product claim permits; add conditional rates only as separately
   defined measures.
4. **Retain both frames**, separating coverage requirements from directional-fidelity requirements,
   and retain full-map conformance tests.
5. **Freeze comparator semantics** — destination eligibility and aggregation, connectors, direction,
   partial weights, ties, bounds, same-edge versus network competition.
6. **Implement the reference fixture-first**, with both reviews' counterexamples, independently
   derived expected answers and objective-specific properties.
7. **Specify the saved and published contracts** — report reconstruction with routing and sources
   unavailable, and actual browser conformance with the status algebra.
8. **Resolve the remaining ten findings**, especially E2 missingness, the diagnostic comparison,
   development sampling and repeated certification.
9. **Finish development before the freeze** — grid and encoding selection, exporter migration,
   browser checks and phone measurements — then draw the certification samples.

> "It cannot remove the need to decide what adequate coverage means. That is the remaining product
> decision; the current 0.71% figure does not answer it."
