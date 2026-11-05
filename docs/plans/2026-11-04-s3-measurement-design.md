# S3 measurement design — predeclared

**Status:** design, predeclared before any sampling. Nothing here reports a result.

**Revision 5, 2026-11-05**, after Codex pass 18 found twelve defects in revision 4 — three of them
blocking. Change log in §13; revisions 2, 3 and 4 are kept there too.

Pass 18's verdict on revision 4 was that "the statistical redesign largely survives" and the
remaining blockers concerned **which product is being measured**, unresolved comparator semantics,
and acceptance rules that still permitted incompatible implementations. Revision 5 closes those four
blockers (§§2.2, 2.6, 3, 8) and the five contracts that had to be settled before any freeze (§§2.3,
6, 8, 10, 12).

**What revision 4 changes in kind.** Revisions 1–3 were prose specifications of a computation.
Pass 17's judgement is that prose cannot carry this weight — "a program can faithfully implement
each defective instruction", and fixtures derived from the same mistaken premise enforce the defect
rather than catching it. So revision 4 freezes **five artifacts**, not one document (§12):

1. a short **normative specification** of each measured quantity and its observable decision rules;
2. a **versioned reference implementation** of the comparator;
3. **independently derived expected results** on constructed cases — a conformance suite;
4. **configuration and artifact digests**;
5. a **change policy** distinguishing an equivalent implementation change from a semantic amendment.

The boundary between what is frozen and what is free is **not** "anything that could change the
measured rate", which fails literally because correcting a bug changes the rate. It is:

> **Freeze the quantity and its observable decision rules. Implementations may vary only while
> preserving those rules across admissible inputs.**

**Four owner decisions stand** (2026-11-04, before any sampling): finite-population SRS inference;
coordinate destination attachment with modelled connectors; diagnostic A defined on product
verdicts; and a published maximum of 120 minutes at whole minutes with codes 121–254 a versioned
status plane. Pass 17 confirmed none needs reversal.

**One owner decision is open and blocks one claim only.** The **coverage requirement** — what
fraction of requests must be answerable — is a product decision that no raster count can supply. Per
§8, E0 is computed and reported, and **coverage certification is blocked** until a requirement
exists. The construction gate (E1) and all the work below are unaffected. No number is invented here
to unblock it.

---

## 1. Two frames, because there are two populations

**Frame B — structures.** `v2/data/triangle/overture_buildings_accepted.parquet`: **522,160 rows
measured** (522,109 Polygon, 51 MultiPolygon), of which **512,633 have a projected centroid inside
the 100 m grid**. Verified against the artifact, and independently reproduced at pass 17 by
reprojecting all 522,160 geometries and re-binning the centroids to the saved buildings-per-cell
raster **exactly**. Centroids are computed **projected** (EPSG:32617), never geographically.

A building frame, **not a household frame**: Overture carries no reliable residential flag here, so
a shed, a barn, a warehouse and each structure of a hospital campus count once each. Frame B
estimates a property of the **structure-centroid population**. The word "household" appears nowhere
in any S3 output, and no argument in this design may appeal to frame B as a residential population.

**Frame C — ground area.** All 330,502 cells of the 100 m grid (643 × 514, `x_min` 661900,
`y_max` 4003500, EPSG:32617), SRS without replacement of cells, then **one uniformly random point
inside each sampled cell**, the two offsets drawn **independently**.

**What frame C estimates, precisely.** Unbiased for the **average disagreement probability over
ground area** — the mean within-cell rate across equal-area cells. **Not** the fraction of cells
containing any error.

**Why neither frame uses cell centres.** `TRIANGLE.grid()` is **not nested**: 100 m at origin
661900/4003500 against 200 m at 661800/4003600, offset −100 m east and +100 m north. Sampling each
grid at its own centres would confound resolution, alignment and which ground is asked about.

**Both frames are frozen artifacts with digests**, because file order is not stable across downloads
and "the first *N*" silently changed which POIs an experiment used (S2.5).

**Neither frame is demoted.** Pass 17 rejected the proposal to gate frame B alone: it would have
made false PASS and false FAIL across rendered ground descriptive, when the only motivation was
*truthful* abstention on empty ground — and §3's separation of E0 removes that motivation entirely.
96.6% of off-network cells holding no structure does not establish that such ground has no future
residential use, that routes through it cannot matter, or that its rendered state cannot affect a
decision.

---

## 2. Comparator semantics, frozen

This section is normative. It fixes **quantities and observable decision rules**; the reference
implementation (§12) fixes the procedure, and the conformance suite fixes the expected answers.

| | |
|---|---|
| **origin** | the sampled point |
| **origin attachment** | access leg at the layer's access speed (walk **1.26 m/s**), capped at `max_access_m` = **200 m**. No network within the cap is a **status**, not a missing value |
| **destination set** | the 550 grocery places from `select_overture(triangle, "grocery")` — verified 550, all Point, from 107,484 accepted places |
| **destination eligibility** | a destination is **eligible** iff its residual connector is ≤ `poi_snap_max_m` = **300 m**. Under nearest-**edge** attachment exactly **one** of the 550 is ineligible. The eligible set is **549** and both the eligible and selected sets are recorded by identity in the run manifest. Every reported figure carries this qualification |
| **direction** | **origin → destination**. A one-way road can make origin→destination routable while the reverse is not, so the comparator must never run in the arrival surface's internal direction |

### 2.1 The two objectives, and which estimand each serves

- **Objective 1** — `min over eligible destinations of total travel time`.
- **Objective 2** — `total travel time along the path to the destination minimising total cost`.

Both include both connectors and the partial-edge terms of §2.2. **E1 is defined against objective
1.** The difference `objective 2 − objective 1` is the pass-8 H2 selection gap; it is **inside E1 by
construction** and is **reported as its own signed distribution**, never subtracted and never
exempted.

**E2 pairs objective 2 against objective 2.** The independent engine's value is
`travel time along the path to the destination minimising that engine's own total cost` — that is,
**cost-`argmin` then report that pair's time**, which a Valhalla matrix supports because it returns
per-pair costs (verified live: a two-target response carried `(cost, time) = (1068.25, 448)` and
`(1194.771, 1174)`). Taking a minimum over times of cost-optimal paths is a **different functional**
and is forbidden: with identical engines on destinations `(cost, time) = (10, 10), (100, 1)` it
reports −9 s of "disagreement" where there is none.

**E2's own input is the coordinate objective-2 comparator value, named `objective2_own_s`** — not the
float cell surface. Revision 3 called it `t_float` and conflated two separately retained values.

**No property replaces these definitions.** Monotonicity is objective-specific: adding a *cheaper*
destination correctly **increases** objective 2's reported time (executed: 10 s → 100 s). Properties
in the conformance suite supplement exact expected answers; they never substitute for them.

### 2.2 Attachment, partial edges and competition

- A destination or origin attaches at its **nearest position on the graph**, which may be a point
  along an edge. **Geometric ties are resolved by keeping every minimiser.** "Nearest" alone does
  not determine an attachment, and that is not a corner case: two disconnected directed roads from
  x = 0 to x = 100 at y = ±1, with an origin at `(0,0)` and a destination at `(100,0)` each exactly
  1 m from both, give **101.587 s** or **1001.587 s** depending on which road is chosen — a different
  verdict at ten minutes — while *both* choices satisfy nearest-position, the access cap, connector
  charging, direction and objective minimisation. So:
  - **every** attachment whose geometric distance is within `attach_tie_m` = **0.01 m** of the minimum
    is retained as a routing candidate, and the objective minimises over all of them. The reported
    quantity is then a property of the geometry rather than of a convention, and no frozen arbitrary
    order is needed;
  - where one geometry has several equally nearest positions — a point equidistant from two places on
    the same curve — each is retained as a candidate under the same tolerance;
  - equality is **tolerance-based** at `attach_tie_m`, declared here, not exact float equality.
  - the set of retained candidates is **recorded per point** in the manifest, since it is part of what
    determines the answer.
- A **partial edge** contributes `fraction × edge_time` and `fraction × edge_cost`. **Every edge
  penalty is apportioned by the same fraction, with no exceptions**, and an implementation may not
  invent one. The consequential case is the restricted-access penalty: `access.py` adds a fixed
  **120 s per restricted walking edge** to cost, so on a 1% traversal apportionment charges 1.21
  while an entry fee would charge 120.01, and against a 5 s open bypass the two select different
  routes. Apportionment is **already the existing attachment model** and is adopted deliberately —
  it is a fractional-cost model, not a charge for entering restricted access. Changing it to an entry
  charge is a **semantic amendment** under §13 requiring different fixtures, not an implementation
  choice.
- A partial traversal is legal only in a direction the edge permits. Walk symmetrisation supplies the
  pedestrian reverse; **bike and drive do not inherit it**.
- **A same-physical-edge direct traversal is a candidate, not the route.** It competes with
  endpoint-and-network candidates under each objective and can lose: executed, a direct 800 s
  traversal loses to 100 + 1 + 100 = **201 s** via a bypass, and on a one-way `u→v` an origin at
  fraction 0.8 cannot reach a destination at 0.2 directly at all.
- The residual straight-line connector is charged at the **access speed** and is part of both
  objectives' totals.

### 2.3 Objective-specific views, correctly paired

`graph_to_cost_time_csr()` and `EdgeIndex.from_graph()` both deliberately keep the **cost-minimal**
parallel alternative and carry its time, and the second's docstring says the first is what it is
matching. That invariant is **not** "both objectives pick the same edge" — their disagreement is the
point. It is:

> Each objective's attachment weights, node search, selected path and reported time must describe
> **the same objective on a compatible graph.**

Executed on two consecutive 100 m segments with coincident alternatives (time 1/cost 100 and
time 10/cost 10), origin halfway along the first:

| pairing | reported |
|---|---|
| time-selected index + time-minimum nodes | **1.5 s** — correct objective 1 |
| cost-selected index + cost-selected nodes | **15 s** — correct objective 2 |
| time index + cost nodes | 10.5 s — invalid hybrid |
| cost index + time nodes | 6 s — invalid hybrid |

So **two objective-specific views, never a hybrid.** "Build two indices" is an implementation
direction, not the specification: the implementation should share immutable geometry and the spatial
tree with objective-specific weight views, or process objectives sequentially — the real index holds
**713,452 geometries** whose numeric arrays alone are **34.2 MB**. Peak memory and build time are
benchmarked in development.

### 2.4 Ties

**Normative, because the current code is non-deterministic.** With equal-cost coincident
alternatives of time 10 and 1, reversing insertion order changes the reported time from **10 to 1**
in both the CSR and the edge index.

**Identity and grouping are frozen separately from ranking**, because repeating one tie comparator
in three stages cannot repair incompatible grouping — and today the three stages disagree.
`speeds._physical_key` groups by `osmid` plus length rounded to 2 dp;
`snap._canonical_geometry_key` uses exact coordinates and tolerates reversal; the CSR collapse uses
the ordered endpoint pair. Executed consequence: a straight forward road and a curved reverse road
sharing endpoints, `osmid = [7]`, length 100, time 100 and cost 100 are **identical** to
`_physical_key` and **distinct** to the geometry key, so **`symmetrise` suppresses both reverses as
duplicates while the attachment index treats them as two roads, leaving reverse weight `inf` for
each.**

So, normatively:

1. **Canonical directed-edge identity** is `(start node, end node, canonical geometry key, osmid
   normalised to a sorted tuple, length rounded to 2 dp)`. Geometry keys are canonicalised so a
   reversed traversal of the same geometry maps to the same physical road but a *different* directed
   identity.
2. **Reverse pairing** for `symmetrise` uses that same canonical identity, so a road is only ever
   suppressed as a duplicate of a road it is genuinely identical to.
3. **The CSR → directed-edge mapping is preserved**, so a collapsed entry can name the directed edge
   it came from.
4. **Destination identity** is the Overture `id`; **route identity** is the sequence of canonical
   directed-edge identities.
5. Rounding precision is **2 dp on metres** everywhere, stated once.

**Ranking, applied only after identity and grouping:**

> Among alternatives tied on the objective's selection weight, choose the smallest **travel time**;
> then the smallest normalised `osmid` tuple; then the smallest rounded length; then the smallest
> canonical geometry key. The same rule applies in projection, attachment and reconstruction.

The fourth key makes the order **total**: alternatives agreeing on all four are identical in every
quantity this design reports, so the choice among them cannot change a result, and any of them may
be named as the selected edge provided the choice is deterministic.

### 2.5 Bounds: metric, strictness, soundness

A bound is usable **only** as a sound lower bound on **travel time**. Revision 3's rule — "exhausted
through *H* with nothing reached, *T* ≤ *H* → known failure" — is unsafe because **exhaustion
supplies a bound in the search's own metric**, and a cost bound is not a time bound: executed, one
edge with **time 1, cost 121** under a **cost limit of 60** returns `inf` while objective 2 returns
**1 second**, so the rule would fail *T* = 60 for a route that passes in one.

Each comparator result retains **bound metric, bound value, strictness and termination reason**, and:

- **a finite time was found** → that time is the answer, and none of the no-result branches applies.
  This branch is stated first because the others are only reached when nothing was found.
- **unbounded and exhausted** → `NO_PATH`, definitive.
- **a sound lower bound `L` on travel time** → known failure iff `L > T`, or `L ≥ T` only when the
  bound is strict. `t > H` fails *T* = *H*; `t ≥ H` does not.
- **anything else** → comparator-unresolved (§7). `NO_PATH` may never be reported from a bounded
  search: exhaustiveness is a property of the invocation, which is why `status.py` requires
  keyword-only `search_bounded` and why `arrival_seconds_two_weight()` searches unbounded on cost.

Objective-2 cost-selected routes are therefore **reconstructed unbounded** unless a separately valid
time bound is in hand.

### 2.6 The independent engine

Carries **its own horizon** — the own-graph layers were built to 120 minutes and the Valhalla
reference layers to 60, and comparing them without carrying each horizon reads one engine's missing
data as the other's disagreement. Its **tileset identifier, engine version and exact request and
costing configuration** are frozen in the manifest (local `/status` exposes them).

**Its connectors are added, and that choice is now made rather than offered.** Supplying coordinates
is not enough: executed, a target at `(35.999, −78.905)` and its correlated road position
`(35.999022, −78.905211)` both returned **448 s, cost 1068.25**, so the residual ~19 m is **not**
charged at 1.26 m/s. Revision 4 permitted either adding agreed connectors or retaining the engine's
attachment model and declaring the difference inside E2 — **but those are different estimands**, and
leaving the choice open left E2 undefined: on destinations A (cost 10, time 10 s, 100 m residual) and
B (cost 20, time 20 s, 0 m), the raw engine policy selects A and reports **10 s** while charging A's
connector moves the cost-`argmin` to B and reports **20 s**.

**Predeclared: agreed connectors are added to the independent comparator**, because E2 is meant to
measure *engine* disagreement and retaining two different attachment models would conflate that with
attachment disagreement. Specifically:

- the connector's residual is charged at the **access speed** and contributes to **both** the
  independent engine's selection cost and its reported time, exactly as it does for our own
  comparator;
- the correlation position used by the engine is **recorded**, and the residual is measured from the
  place's own coordinate to that position;
- the same `max_access_m` and `poi_snap_max_m` caps apply, so both sides share one eligible set;
- a destination the engine **cannot correlate** is excluded from both sides and recorded by identity.

This declaration is kept separate from destination-selection aggregation (§2.1): they are independent
choices and conflating them is what produced revision 3's −9 s of phantom disagreement.

---

## 3. Estimands

Four. They are never combined, and each names its own frame.

### E0 — abstention (a census, not an estimate)

> **the share of the frame at which the product returns `UNKNOWN` at threshold *T*.**

For a frozen raster-lookup product the verdict is known at **every** cell and threshold, so E0 needs
**no sampling at all**:

**E0 is defined over the actual published lookup, not over the original cells.** A cell's verdict
determines every point inside it *only while the lookup uses that same partition*, and export breaks
that: executed with rasterio, two original 100 m cells holding UNKNOWN and PASS, exported
nearest-neighbour onto a shifted 80 m grid, give published bytes `[UNKNOWN, UNKNOWN, PASS]` — the
second original cell's centre at x = 150 returns PASS while its interior point at x = 110 returns
UNKNOWN, so **20% of that cell is now UNKNOWN** and a structure at x = 110 is UNKNOWN although its
cell centre is not. Frame C's within-cell draw does not break the census; export does.

So, with `published_lookup` the frozen function the product actually answers with:

> `E0_B(T)` = mean over the frozen structure centroids of `1{published_lookup(centroid, T) = UNKNOWN}`
>
> `E0_C(T)` = (area of the original frame-C domain on which `published_lookup` is UNKNOWN) ÷ (area of
> that domain)

Frame C stays uniform over the **original projected ground area**, so counting exported pixels would
change the measure. The simple cell sums `Σ bᵢ·1{·}/Σ bᵢ` and `Σ 1{·}/N_C` are valid **shortcuts**
only once `published_lookup` is shown constant on every original frame cell — which is a checkable
property and is checked, not assumed.

E0 carries **no sampling uncertainty**. But an exact exported census requires projected-area
intersection; if a numerical approximation is used instead, **its error is reported separately and
the result is not called uncertainty-free**. Lookup behaviour **outside the exported footprint** is
defined explicitly rather than left to the implementation.

Reported **by frame, threshold and reason**, because the reasons have different remedies:
`BEYOND_HORIZON` beyond the horizon is answerable by searching further (contract §2's
`needs_recomputation`), `OFF_NETWORK` is not.

For reference, computed on the current artifact — **a measurement of the status quo, not a
requirement**:

| threshold | frame C `UNKNOWN` | frame B `UNKNOWN` |
|---|---|---|
| 10 min | 55,102 / 330,502 = **16.6722%** | 3,371 / 512,633 = **0.6576%** |
| 15 min | 57,243 / 330,502 = **17.3200%** | 3,621 / 512,633 = **0.7064%** |
| 25 min | 57,541 / 330,502 = **17.4102%** | 3,657 / 512,633 = **0.7134%** |
| 45 min | 57,541 / 330,502 = **17.4102%** | 3,657 / 512,633 = **0.7134%** |

`BEYOND_HORIZON` is a known FAIL at every published threshold because the built horizon is 120
minutes. These are **threshold-wise abstention rates**, not the `OFF_NETWORK` reason shares of
17.41% and 0.71%, which the pass-16 record confused.

**Provenance of this table, stated because it has not been reproduced here.** It was computed at
pass 17, which prepared the graph and reconstructed `min_possible_s` — a value the pipeline computes
in `cell_arrival_with_provenance` but **does not save**, so only `seconds` and `reason` are on disk
and the table cannot be recomputed from the saved rasters alone. What *is* checked here is internal
consistency, and it holds exactly: the complements are 57,541 − 55,102 = **2,439** cells proven over
at *T* = 10 and 57,541 − 57,243 = **298** at *T* = 15, matching the independently reported
proven-over counts.

The **physical reason**, corrected: a sound lower bound divides by an upper bound on speed, so
`snap.py:291` computes `min_possible_s = access_m / max_speed_mps(mode)` and walk's maximum is
**1.40 m/s**, not the access speed 1.26 — whose docstring says so explicitly, because access factors
below 1 would make an over-estimate masquerade as a lower bound. Proven-over therefore requires a
nearest-edge distance above **840 m** at *T* = 10, **1,260 m** at 15, **2,100 m** at 25 and
**3,780 m** at 45. The measured maximum nearest-edge distance is **1,688.99 m**, which is why nothing
is proven over at 25 and 45 minutes. The 200 m access cap does **not** bound how far an off-network
cell lies from the graph. (An earlier revision used 1.26 m/s here and would have implied 3,534 and
604 proven-over cells rather than 2,439 and 298.)

Pass 18 **independently reproduced the whole table**, so its figures are verified; exact recomputation
under §10's frozen published lookup remains a task.

### E1a, E1b — construction fidelity (the gate)

**Full-frame joint probabilities**, for mode *m* and published threshold *T*:

> **E1b false inclusion** `= Pr(product = PASS and comparator = FAIL)` — a claim the product made
> that is wrong. A wasted viewing.
> **E1a false exclusion** `= Pr(product = FAIL and comparator = PASS)` — a home never shown.

**A product `UNKNOWN` is a known non-event for both.** It is fully observed — we know exactly what
the product said — so it cannot secretly have been a PASS, and charging it as a possible false
inclusion was revision 3's defect: it put ≈16.7% of frame C against a 1.0% threshold, with a
probability of 2.51 × 10⁻³⁸ of observing at most one such among 500.

**The estimands stay full-frame and are not conditioned on the product having made a claim.**
Conditioning would change the thresholds' meaning and break the allocation arithmetic: executed, one
error among **417** claim-making observations gives a 1.1325% upper bound — over the 1.0% line —
against 0.9452% at 500. A conditional rate may be added **only** as a separately named measure with
its own formula, threshold and allocation. "Reporting the denominator" is presentation and repairs
nothing.

Estimated **separately on each frame**: frame B as a share of structures, frame C as a share of
ground area. Same engine both sides, so a difference is ours to fix — construction testing, not a
validity claim.

### E2 — engine disagreement (descriptive)

> **d = objective2_independent − objective2_own**, in seconds, at the same point with matched arrival
> time.

**Its domain is declared, because a difference does not exist everywhere.** E2 is defined on the
**jointly finite pairs** of each frame, reported **per frame** and never pooled across frames or with
the diagnostics — pooling 2,600 origins would change its sampling distribution. The raster alone has
**73,750** non-finite cells, and the engines carry different horizons, so:

- the estimand is named as **conditional on joint finiteness**, with its denominator stated;
- a **status cross-tabulation** accompanies it, so censored and failed pairs are counted rather than
  deleted;
- if a full-frame summary is ever wanted, it requires identification or censoring bounds, not
  silent deletion.

Reported as signed median and IQR with a bootstrap interval (§6), plus the share with |d| above one
encoding increment.

**Five paired values are retained per point** — objective 1, objective 2 own, float surface, encoded
surface, objective 2 independent — so encoding, snapping, entrance choice, destination selection and
route choice are never collapsed into one unattributable "model error".

### E3 — real-world accuracy (`failed` / UNVERIFIED)

> **the signed difference between a hand-timed journey and the product's reported time.**

5–8 owner-chosen journeys are a convenience sample: the binomial bound does not apply to them, and
with 8 observations and no discrepancy the one-sided 95% exact bound would be **31.2344%** anyway. The
population-rate claim is **UNVERIFIED** and the published label says so.

It can still fail, as a disjunction:

> **E3 returns `failed` if *either* (i) any single journey's observed time exceeds its reported time
> by more than a factor of 1.5 **and** by more than 5 minutes, *or* (ii) the median signed difference
> across journeys taken exceeds 25% of the median reported time.**

Absent a failure the outcome is UNVERIFIED — never "supported". A planned journey that was not
walked leaves UNVERIFIED and **can never erase a failure established by the journeys that were
walked**.

---

## 4. Samples

**Frame B:** SRS without replacement, ***n* = 500**. **Frame C:** SRS without replacement,
***n* = 500**. Chosen by **failure tolerance** (§6), which is a planning property and **not a
statement of expected performance**: at true E1b rates of 0.001 / 0.005 / 0.01 the probability of
meeting E1b's count rule at *n* = 500 is **90.99% / 28.65% / 3.98%**.

E0 is a census (§3) and consumes no sample.

### Diagnostics — conditional samples, never pooled

Each is a **conditional SRS from frame B's 512,633-structure population**, restricted to its
predicate, reporting its own conditional rate. They are never added to a population estimate: a point
can satisfy several predicates at once, so pooling would count the same mass repeatedly.

| diagnostic | predicate | *n* |
|---|---|---|
| **A — boundary-adjacent** | the cell is 4-adjacent to a cell with the **opposite product verdict** at *T* | 150 **per *T*** |
| **B — within one encoding increment** | the reported value is within 60 s of *T* | 150 **per *T*** |
| **D1 — off-network** | product reason `OFF_NETWORK` | 200 |
| **D2 — beyond-horizon** | product reason `BEYOND_HORIZON` | 200 |

**A excludes `UNKNOWN` verdicts, not `OFF_NETWORK` reasons.** The contract returns FAIL for
`OFF_NETWORK` when its access lower bound exceeds *T* — **2,439 such cells at *T* = 10 and 298 at
*T* = 15** — so those are genuine verdicts and eligible. Only a product `UNKNOWN` is not a verdict
and so cannot be an opposite one. (In the current artifact none of those 2,439 touches a passing
cell, so this changes no count today; it is the general predicate that must be right.)

**D1 and D2 measure coordinate-answerable product abstention.** At an abstaining point the
comparator either also declines or returns a definitive verdict the product did not give. The second
case is reported as **coordinate-answerable abstention**, with:

- **numerator** — sampled points of that diagnostic at which the comparator returns a definitive
  verdict;
- **denominator** — *all* sampled points of that diagnostic, **including** any whose product verdict
  is a known FAIL, so the measure is a share of the sampled conditional frame and not of a subset
  selected by outcome.

**It is an opportunity measure, not proof of a contract violation, and it does not protect the
gate.** An earlier revision claimed it stopped an all-abstaining product satisfying E1. That was
**false**: an all-`UNKNOWN` product produces zero E1a and zero E1b events, so both upper bounds are
**0.5974%** at *n* = 500 and it **passes both construction thresholds**. No diagnostic can reverse
that without an acceptance rule, and making this one an acceptance condition requires a §13
amendment. A deliberately capped or coarser raster may also correctly return `UNKNOWN` under its
published rules while a more expensive coordinate calculation answers — so a definitive comparator
answer is an opportunity, not a defect.

**Only the coverage requirement bounds abstention, and it is separately blocked** (§8).

**The diagnostic-versus-population comparison is descriptive screening, not inference.** Revision 3's
rule — a factor of two plus a lower bound above the population *point estimate* — is not a 95%
comparison, because the reference is itself noisy: with equal true rates of 0.001 it flags the
diagnostic with probability **0.0845**. And the ratio is undefined when the reference estimate is
zero. So:

- the comparison is **labelled descriptive screening** and the word "distinguishable" is not used;
- **zero-reference behaviour is defined**: when the population estimate is 0, no ratio is reported
  and the diagnostic's own interval is given alone;
- both conditional rates are reported with **exact one-sided bounds in the relevant direction**, and
  any formal two-sample claim would need a stated comparison accounting for both samples and their
  overlap. None is made.

**Routing budget:** 500 + 500 population points, 150 × 4 + 150 × 4 diagnostic A/B points, 200 + 200
for D1 and D2 = **2,600 memberships** before deduplication. Deduplication of routing work is valid
only if **every membership and denominator survives it**.

---

## 5. No weights, and no design effect

Both population samples are self-weighting SRSs; the diagnostics are conditional SRSs and carry no
weights.

**The design effect is removed** (owner decision 1). Clustering inflates variance when the *design*
clusters — blocks sampled, then every point within them. Points here are drawn independently, so
spatial correlation in the *population* is not correlation in the *estimator*. Pass 17 confirms:
"spatial adjacency alone does not turn SRS into cluster sampling."

Consequently there is no DEFF estimator, no 2 km block grid, no pooling rule and no block bootstrap —
and so none of revision 2's unspecified estimator detail, nor the single-block degeneracy that would
have reported a **zero-width interval** from 2,000 identical replicates.

**A superpopulation claim** — "the rate at which a pipeline of this kind errs", rather than the rate
over these 512,633 structures — would need a stated and validated spatial model. It is out of scope
and no S3 output may be worded as one.

---

## 6. Intervals

**Exact Clopper–Pearson one-sided bounds on the actual sample size**, in the direction the quantity
requires: **upper** bounds for failure rates, **lower** bounds where §4's screening needs one. Both
primitives are required. No effective-sample-size adjustment is applied, and after any such
adjustment a bound may not be called exact — which is why revision 2's "exact bound on *n*/DEFF" was
a contradiction.

**Exact variance, stated correctly.** For a binary finite-frame SRS it is
`p(1−p)/n × (N−n)/(N−1)`, not the `p(1−p)/n × (1−n/N)` revision 3 printed. Frame C is **two-stage** —
a cell, then a point inside it — so its within-cell variance receives **no** finite-population
correction:

> `Var(â_C) = [ (1 − n/N) S_q² + mean(qᵢ(1 − qᵢ)) ] / n`,  `S_q²` on `N − 1`

with `qᵢ` the within-cell error probability. If every cell were half erroneous the variance is
`0.25/n` even at `n = N`, which revision 3's expression wrongly sends to zero. Differences are
numerically small at *n* = 500; the formulas are stated because the wrong one implies a false limit.
A Bernoulli variance is **never** applied to E2's median.

Binomial bounds on a without-replacement SRS are **conservative** — hypergeometric would be tighter,
and `(N−n)/(N−1) = 0.99902` at *n* = 500 — so the conservative direction is kept and named rather
than claimed as precision.

### What each allocation tolerates

| *n* | *k*=0 | *k*=1 | *k*=2 | *k*=3 | E1b ≤ 1.0% | E1a ≤ 2.0% |
|---|---|---|---|---|---|---|
| 400 | 0.7461% | 1.1804% | 1.5655% | 1.9269% | **0 failures** | 3 |
| 473 | 0.6313% | 0.9990% | 1.3250% | 1.6310% | 1 (knife-edge) | 4 |
| **500** | **0.5974%** | **0.9452%** | 1.2538% | 1.5434% | **1 failure** | **4** |
| 628 | 0.4759% | 0.7531% | 0.9991% | 1.2300% | 2 | 6 |

*n* = 400 tolerated **exactly zero** false inclusions; 473 is the minimum surviving one, at 0.9990%,
too close to predeclare; **500 survives one at 0.9452%.** Every value reproduced independently twice.

A zero-failure result is reported as **"0 observed, 95% upper bound x%"**, never as "0%".

### The bootstrap, fully specified

E2's interval is a **percentile bootstrap over points**, fully specified because "the 2.5th
percentile" does not identify a number: on 2,000 replicates of 50 zeros and 1,950 ones it is **0.975**
by linear interpolation, **0** by the lower convention, and **1** by higher or nearest.

| | |
|---|---|
| replicate statistic | the **median** of the paired differences |
| replicates | **2,000** |
| resampling | points drawn **with replacement within each frame**, `n` equal to that frame's sample size, **pairing preserved** within a resampled point |
| endpoint quantile method | **linear interpolation** (`numpy.quantile` default), at **0.025 and 0.975** |
| RNG | `numpy.random.Generator` on **PCG64**, seeded from a recorded integer |

A recorded seed alone does not identify a sequence without its generator and resampling convention,
so all three are frozen together.

- **Ties are admissible** and may legitimately give a degenerate interval.
- **An empty or single-point domain returns "not estimable"**, not an interval.
- Coverage is **approximate** under regularity conditions — not an exact consequence of SRS — and is
  reported as such.
- **No monotonicity of width is asserted.** Revision 3's plan required the interval to widen as the
  sample shrinks; that is false, and an assertion no correct implementation can satisfy: `[-1, 0, 1]`
  gives `[-1, 1]` while the smaller `[0, 0]` gives `[0, 0]`. The conformance test is a fixed
  bootstrap distribution against an independently computed reference, plus seed reproducibility and
  preserved pairing.

---

## 7. The complete accounting

Every sampled point falls in exactly one cell of the product × comparator cross-tabulation. Nothing
is deleted, and agreements are counted — revision 3's three buckets omitted them and mishandled a
comparator failure at an abstaining point.

| product | comparator PASS | comparator FAIL | comparator unresolved |
|---|---|---|---|
| **PASS** | agreement | **E1b** | unresolved potential **E1b** |
| **FAIL** | **E1a** | agreement | unresolved potential **E1a** |
| **UNKNOWN** | **E0** (and **unwarranted abstention**) | **E0** (and **unwarranted abstention**) | **E0**, comparator status retained |

- **Comparator unresolved** means timeout, engine error, snap failure, or no sound bound (§2.5). It
  is bounded **in one direction only** — the direction the observed product claim permits — because a
  product PASS cannot generate a false exclusion. Write **`k`** for identified errors of a direction
  and **`u`** for unresolved observations that could be errors of *that* direction. Both are reported,
  as **distinct objects**: the **identification range** `[k/n, (k+u)/n]` and the **confidence bounds**
  at each end. §8 turns them into a verdict.
- **Comparator failures are retained** for E2 and for operational diagnostics even where they cannot
  identify a directional error.
- **Product reasons are retained** at every `UNKNOWN`, since `BEYOND_HORIZON` and `OFF_NETWORK` have
  different remedies.
- **Invalid product artifacts and layer-wide publication failures** are an explicit **run failure**
  with its own handling. They are never removed by deleting rows.

---

## 8. Acceptance

### The construction gate

For each published mode *m* and threshold *T* ∈ {10, 15, 25, 45} minutes, on **each** frame:

With `k` identified errors of a direction, `u` unresolved observations that could be errors of that
direction, `n` the **full-frame** sample size, and `θ` that direction's threshold (E1a 2.0%,
E1b 1.0%):

> **PASS** if `CP_upper(k + u, n) ≤ θ`
> **FAIL** if `k / n > θ`
> **INCONCLUSIVE** otherwise

Both directions must PASS. Revision 4 said "the point estimate of either exceeds its threshold"
without saying which completion supplies the point estimate, which left the verdict ambiguous: at
*n* = 500 with `k` = 1 and `u` = 1 the completed proportions are 0.2%–0.4%, below 1%, while the
completed upper bounds are 0.9452%–1.2538%, crossing it — so the rule above returns INCONCLUSIVE,
which is correct, whereas reading the pessimistic completion as "the point estimate" would have
returned FAIL at `k` = 4, `u` = 2.

At *n* = 500 this admits **at most one observed false inclusion and four false exclusions**, stated
here before measurement.

**E1b is held tighter** because a false inclusion is a claim the product made; both are harmful and
only the first is one we would have to defend. The thresholds are the owner's to move before
measurement, not after.

**Every published mode and threshold must pass on both frames** for a layer to be called
construction-verified; a single failing combination is reported as such, never averaged.

**No claim is made that this gate is now reachable.** Removing product `UNKNOWN` from E1b removes the
specific obstruction revision 3 created. Whether the gate passes depends on the directional error
rates, the size of the unresolved bucket and the frame denominators, all of which are empirical.

**Multiplicity:** the gate is a conjunction, so no correction is required for the single global
claim — but the sixteen bounds are **not** simultaneous 95% bounds and no output may present them so.

### The coverage requirement — open, and blocking only itself

E0 is computed and reported. **No coverage threshold is predeclared here**, because none can be
derived from the repository and inventing one to finish this document is the failure mode
predeclaration exists to prevent. Four policy shapes are available for the owner:

| policy | shape | its limit |
|---|---|---|
| **absolute coverage** | `E0 ≤ 1 − c_min`, `c_min` justified from the product promise or user research | no value is derivable from raster counts |
| **decision-loss budget** | `λ₀a + λ_b e_b + λ_a e_a ≤ B` in common units | the weights and budget are a product decision |
| **explicit non-regression** | freeze a reference, require no increase by reason and subgroup | principled, but silent on whether the reference was *adequate* |
| **service obligation** | every unresolved request gets an explicit unavailable result or a declared fallback | "transparent and still useless" if it abstains everywhere |

**Recommended: an absolute coverage requirement plus a handling obligation.** Until one exists:

> **The instrument is built, E0 is reported, and coverage certification is BLOCKED.** The
> construction gate is unaffected. A measurement that does not certify coverage must not be described
> as certifying the layer.

A threshold informed by the current artifact is not automatically illegitimate — what matters is that
the justification is transparent and the resulting claim is stated honestly. A threshold chosen
*solely so this artifact passes* is weak evidence of adequacy, and would be labelled as
non-regression rather than adequacy.

### Conformance obligations, which are not statistical

These are pass/fail requirements on the shipped product, tested directly rather than estimated,
because the map, the constraint algebra, `needs_recomputation` and the "why is this out?" explanation
all operate on **cells** whether or not a structure stands there:

- PASS / FAIL / **UNKNOWN** decoding in the browser;
- **a known failure takes precedence over an unknown** when criteria combine;
- threshold and horizon boundary behaviour;
- recomputation eligibility where the threshold exceeds the horizon;
- **every** failing criterion reported, not the first found;
- unavailable ground rendered distinctly from excluded ground.

The existing worker shows why these cannot be inferred from a statistical result: it carries a binary
inclusion mask and treats its single sentinel as failing inclusion.

---

## 9. The encoding, decided — and its wire contract

**Owner decision 4: the published maximum duration is 120 minutes at whole-minute resolution, with
codes 121–254 reserved for a versioned status plane.**

The premise originally given for this question was false, and checking it changed the decision. The
phase-1 plan says a cell at the horizon "is indistinguishable from a genuine 120-minute answer"; in
fact **all 234 cells encoding to exactly 120 carry reason `OK`**, and every censored cell is
`NODATA`, so the **raster pair already disambiguates**. The ambiguity is in the single-raster browser
path, where `worker.js:144` recognises one sentinel and therefore cannot separate **57,541
off-network cells from 16,209 beyond-horizon ones**.

Why 120 and whole minutes: the walk surface's finite maximum is **7,199.999 s = 119.99998 minutes**,
censored at the 7,200 s cutoff, so 120 covers 100% of finite values and the **float surface needs no
rerouting**; 44.0082% / 76.6066% / 92.3206% of finite cells are within 30 / 60 / 90 minutes; **134
codes** (121–254) remain, against 14 at a 240-minute maximum; and the built horizon is not a product
ceiling, because `needs_recomputation` makes a threshold past *H* answerable by a fresh search.

**One code per reason is not sufficient.** Verdicts are not recoverable from a reason alone:
`OFF_NETWORK` at 250 m and at 1,000 m share a reason and differ at *T* = 10. What a cell must carry
for all four thresholds to be decidable in the browser:

| reason | what the decoder needs |
|---|---|
| `OK` | the decoded duration |
| `OFF_NETWORK` | its lower bound, or the bound's exact equivalence class relative to the supported thresholds |
| `BEYOND_HORIZON` | the horizon and **strict**-bound semantics (`t > H`) |
| `NO_PATH` | the reason alone |
| layer-wide failure | the reason, plus invalid/publication handling |

plus versioned spatial lookup, footprint behaviour, units, and the combination and recomputation
algebra.

**Capacity, specified rather than asserted.** For the four fixed published thresholds `OFF_NETWORK`
needs only **five ordered bound classes** — below 10, 10–15, 15–25, 25–45, above 45 minutes, derived
from `access_m / max_speed_mps` — so codes **121–254 plus one companion byte plane** suffice: the
plane carries the bound class for `OFF_NETWORK` and is unused for other reasons. **A numeric bound is
required only if arbitrary thresholds are ever supported**, which is a §13 amendment. "One companion
plane" without its precision and capacity says nothing, so both are fixed here: **one byte per cell,
values 0–4 for the bound classes and 255 unused.**

**The whole chain changes together, and "no rebuild" applies only to the float surface.**
`encode_minutes([121*60, 254*60])` still returns `[121, 254]`, so those remain valid durations for
other layers and **legacy dispatch must be explicit**: the format is versioned and existing artifacts
are rebuilt or namespaced, never reinterpreted. Two concrete repository defects must be fixed in the
same change: the exporter discovers only `<engine>_<category>_<mode>` names and therefore **omits
`own_triangle_grocery_walk.tif`**, and it targets the old 401 × 550 slice while its padding helper
scales every non-255 byte as a minute value. Categorical status codes must **never** be interpolated
during reprojection.

**Scope.** S3.5 says the maximum follows from S0.4's transit horizon and the relaxation limits, and
**S0.4's window is not yet fixed** — there is no Triangle transit layer. This decision covers the walk
layer S3 measures; the version field exists so a longer transit window later widens the format
without reinterpreting existing codes. The duration histogram does **not** establish whole-minute
fidelity — that is what E1 measures.

**Changing the encoding invalidates sample membership**, since diagnostic A is defined on product
verdicts and B on one encoding increment. Both are recomputed whenever the shipped surface or its
encoding changes — which is why §10 requires the encoding settled **before** the freeze.

---

## 10. Development and certification

1. **Conformance suite on constructed fixtures.** Every §7 cell and every §2 rule exercised on
   synthetic graphs with **independently derived** expected answers. Branch coverage is never a
   criterion on real data — genuine `NO_PATH` need not occur at all on the prepared walk graph — and
   fixtures must be derived independently of the implementation, because a fixture built from the
   same mistaken premise enforces the defect rather than catching it.
2. **A development sample**, its own seed, for shakedown, timing and every outcome-driven fix. Its
   observations are **never** substituted for certification estimates.
3. **All outcome-changing selection completes here**: candidate grid choice, the encoding and its
   wire format, exporter migration, browser conformance, phone decode measurements, and the final
   diagnostic predicates. Nothing that can change a measured quantity may happen after the freeze.
4. **Freeze** the five artifacts of §12 together with frames, allocations, thresholds and analysis.
5. **Certification**: draw and run once.

**The certification draw is an independent full-frame SRS**, and development points are **not excluded
from eligibility**. Excluding them would give excluded structures selection probability zero and the
rest `500/(N − N_dev)`, so the estimator would target the complement of the development set while
claiming all 512,633. **Accidental overlap is permitted**; what is forbidden is reusing a development
*observation* as a certification observation.

**Repeated attempts are controlled by a registration, not by good intentions.** Fresh points prevent
holdout reuse but do not preserve a nominal interpretation if the first successful attempt is the one
reported: at *p* = 0.01 a single attempt meets E1b's count rule with probability **0.0397547**, so
twenty attempts give **0.5557336** of at least one pass at the boundary. Retaining outcomes is not
enough either — it does not stop an operator amending the instrument and designating the *next*
attempt "final".

So, **before any certification outcome is observed**, a registration is written and timestamped
**independently of the report**, recording:

1. the claim being certified, and the digests of the instrument and design it is made against;
2. the **uniquely identified designated attempt**;
3. the draw procedure and the **seed-generation rule** — how the seed is obtained, not just its value;
4. the stopping, invalidation and replacement rules;
5. how any earlier outcome and any later amendment affect the certification claim.

Every attempt's identity and outcome is retained and reported, void attempts included. A replacement
drawn after outcomes are seen requires an explicit selection or error-control policy declared in that
registration — "a fresh sample" alone is insufficient — and an instrument change is a §13 amendment.

---

## 11. Remaining methodological requirements

Collected here because they were found as defects and must not be lost again.

- **E3 scoring is a disjunction** and both limbs are tested independently and together. A single
  journey of reported 5 and observed 8 minutes does **not** fire limb (i) but **does** fire limb (ii),
  since the median difference 3 exceeds 25% of 5. An unwalked record never erases a failure.
- **The extraction-truncation diagnostic is a warning, not a bound.** Boundary-touch share among
  retained routes cannot bound the damage: a slow interior path survives while a fast path through
  outside is gone, giving **0% boundary touch and 100% affected**. The diagnostic reports a boundary
  band and a missing-path denominator; a real bound needs a larger-extract comparison.
- **The grid comparison holds everything but the grid fixed** — identical coordinates, identical
  destination attachment — and if its outcome can influence selection it happens in development.
- **Frame C's sampling test needs a joint oracle**, not marginal checks. Marginals do not establish
  joint uniformity: drawing one `u ~ U(0, 100)` and using `(u, u)` for both offsets gives correct
  marginals over 100,000 draws (means 49.9574 m, sd 28.8447 m) with **correlation 1** — every point
  on a diagonal, zero probability over almost all ground. Tests use a deterministic RNG mapping
  oracle on an enumerated toy frame, with fixed seeds and declared tolerances.

---

## 12. The five frozen artifacts

- [ ] **A normative specification** — §§2, 3, 6, 7 of this document, which fix quantities and
      observable decision rules.
- [ ] **A versioned reference comparator** implementing them, built fixture-first.
- [ ] **A conformance suite** of independently derived expected results, containing every
      counterexample from Codex passes 15, 16, 17 and 18 and the objective-specific properties of
      §2.1 — shipped with **evidence of that independence**: the derivation of each expected answer,
      its provenance, and a review against the normative quantity. A digest establishes immutability,
      not correctness or independence.
- [ ] **Digests of every input and configuration**: the float, encoded and status rasters, the
      prepared graph, the eligible and selected destination lists, the independent engine's tileset,
      version and costing configuration, frame artifacts, seeds, and code, profile and grid versions.
- [ ] **A change policy**: an *equivalent implementation change* preserves every §2 decision rule on
      admissible inputs and is recorded with its digest; a *semantic amendment* changes a rule, a
      quantity, an allocation, a threshold, an uncertainty convention or the selection policy, and
      requires a §13 row and fresh certification.
- [ ] **A run manifest and persisted rows** sufficient to **reproduce the report with routing and the
      original sources unavailable** — the payload must satisfy that test *by construction*, not merely
      be checked against it. Per point:
      - **all five numeric values with units**, or an explicit reason-coded absence for each: the
        **float product value**, the **decoded encoded product value**, **objective 1**,
        **objective 2 own**, and **objective 2 independent**. A verdict cannot recover a number —
        100 s and 200 s both PASS at all four thresholds — so the numbers are stored, not inferred.
      - **per threshold**, the product outcome, reason and bounds.
      - per objective, the own comparator's status, bound **metric**, strictness and value; the
        independent engine's status, bound and horizon.
      - the **retained attachment candidate set** (§2.2), the selected destination and its cost, and
        **path references that resolve inside the saved bundle** — or the diagnostic sufficient
        statistics that make the source graph unnecessary.
      - the origin's access distance **and** the product cell's own bound, which are different
        quantities.
      - every diagnostic membership.
    - [ ] **E0's census numerators and denominators by frame, threshold and reason**, stored
      explicitly. The census cannot be rebuilt from 500 sampled rows and a raster digest once the
      rasters are unavailable — a digest identifies missing data, it does not reconstruct it.
- [x] A decision on the published **maximum duration** — §9.
- [ ] **The coverage requirement** — §8. Open; blocks coverage certification only.

---

## 13. Change log

### Revision 4, after Codex pass 16 (6 High, 10 Medium, 2 Low) and pass 17

| finding | revision 3 said | revision 4 says |
|---|---|---|
| **16-F5** | every product `UNKNOWN` into a both-ways bounded bucket | that charged ≈16.7% of frame C against a 1.0% threshold. **E0 is a separate census estimand**; product `UNKNOWN` is a **known non-event** for E1a/E1b, which stay **full-frame joint** probabilities (§3) |
| **16-F1** | E2's independent value = min over destinations of time along cost-optimal paths | a different functional — −9 s with identical engines. **Cost-`argmin`, then report that pair's time**, against our objective 2, named `objective2_own_s` (§2.1) |
| **16-F2** | exhausted through *H* → known failure for *T* ≤ *H* | a **cost** bound is not a time bound (time 1/cost 121 under cost limit 60). Only a **sound lower bound on travel time** scores a failure; metric and strictness retained (§2.5) |
| **16-F3** | project objective 1 before the collapse | necessary but insufficient — `EdgeIndex` collapses by cost too. **Objective-specific views, correctly paired**, never hybrid (§2.3) |
| **16-F4** | the same-edge route *is* the partial traversal | too strong. A **candidate** competing with network routes, legal only in a permitted direction (§2.2) |
| **16-F6** | freeze, certify, then change the encoding | violated its own freeze. **All outcome-changing selection completes in development** (§10) |
| **16-F7** | one `product_outcome`, frame digests | cannot represent four thresholds nor identify the instrument. A full **manifest and per-threshold rows**, reproducible with routing unavailable (§12) |
| **16-F8** | paired values per point | E2's domain is declared **conditional on joint finiteness**, per frame, with a status cross-tab (§3) |
| **16-F9** | `p(1−p)/n × (1 − n/N)` | exact is `(N−n)/(N−1)`, and frame C is **two-stage** with no fpc on its within-cell term (§6) |
| **16-F10** | the bootstrap interval must widen as *n* falls | **false** — an assertion no correct implementation can satisfy. Removed; the bootstrap is fully specified instead (§6) |
| **16-F11** | a 1.6×, 3-minute journey "does not fail" | it **does**, through the median limb. Both limbs tested independently and together (§11) |
| **16-F12** | factor of two plus a lower bound above the population point estimate | not a 95% comparison (flags at 0.0845 with equal rates) and undefined at zero. **Descriptive screening**, zero-reference behaviour defined (§4) |
| **16-F13** | A excludes `OFF_NETWORK` | excludes **`UNKNOWN` verdicts**; 2,439 `OFF_NETWORK` cells are genuine FAILs at *T* = 10 (§4) |
| **16-F14** | development points excluded from certification | that targets the complement. **Independent full-frame draw, overlap permitted**, observations never reused (§10) |
| **16-F15** | void and redraw | ≈55.6% pass at the boundary over twenty attempts. **All attempts retained; one final attempt prespecified** (§10) |
| **16-F16** | 121–254 as a status plane | one code per reason loses the verdict. **Reason plus bound/horizon metadata, decoder algebra, legacy dispatch, exporter and worker together** (§9) |
| **16-F17** | boundary touch bounds extraction damage | **false** — 0% touch with 100% affected. A warning diagnostic (§11) |
| **16-F18** | reject centre-only placement via marginals | marginals admit a diagonal (correlation 1). A **joint mapping oracle** on an enumerated toy frame (§11) |
| **17** | — | **ties were non-deterministic** in production (10 vs 1 on insertion order): a normative tie rule (§2.4). Independent-engine connectors made explicit (§2.6). The diagnostic audit of abstention named (§4). Tolerance is **not** power (§4). The frame-B gate is **not** dropped (§1) |

### Revision 5, after Codex pass 18 (3 High, 8 Medium, 1 Low)

| finding | revision 4 said | revision 5 says |
|---|---|---|
| **18-F1** | a tie rule on the objective's selection weight | that tie never fires, because **attachment** minimises geometric distance — two equidistant roads give 101.587 s or 1001.587 s, a different verdict at ten minutes, with both choices obeying every stated rule. **Every geometric minimiser within `attach_tie_m` = 0.01 m is retained as a candidate** (§2.2) |
| **18-F2** | E0 as a cell-sum census | valid only while the lookup uses that partition. Export breaks it: a shifted 80 m export makes **20% of an original cell UNKNOWN** while its centre says PASS. E0 is defined over the **published lookup**, frame B at frozen centroids and frame C as an **area** over the original domain; the cell sums are shortcuts to be *checked* (§3) |
| **18-F5** | add connectors **or** declare the difference in E2 | different estimands, so E2 was undefined — 10 s against 20 s on the same pair. **Agreed connectors are added** to the independent comparator, in both its cost and its reported time (§2.6) |
| **18-F3** | proven-over above 756 m and 1,134 m at 1.26 m/s | the bound divides by **`max_speed_mps` = 1.40 m/s**, so **840 / 1,260 / 2,100 / 3,780 m**; the measured maximum nearest-edge distance is **1,688.99 m**, which is why nothing is proven over at 25 and 45 minutes (§3) |
| **18-F4** | one tie rule repeated in three stages | cannot repair incompatible **grouping**: `_physical_key`, `_canonical_geometry_key` and the CSR collapse disagree, and `symmetrise` suppresses two reverses the index treats as two roads. **Identity and grouping are frozen separately from ranking**, and a fourth key makes the order total (§2.3) |
| **18-F6** | "the point estimate of either exceeds its threshold" | ambiguous about which completion. **`PASS` iff `CP_upper(k+u, n) ≤ θ`; `FAIL` iff `k/n > θ`; else INCONCLUSIVE**, with the identification range and the confidence bounds reported as distinct objects (§§7–8) |
| **18-F7** | the abstention diagnostic stops an all-abstaining product passing E1 | **false** — an all-`UNKNOWN` product has zero E1 events and both bounds at 0.5974%, passing. It is an **opportunity measure** with a defined numerator and denominator, and only the blocked coverage requirement bounds abstention (§4) |
| **18-F8** | own-objective values persisted | a verdict cannot recover a number. **All five numeric values with units**, plus E0's census numerators and denominators, and path references resolving inside the bundle (§12) |
| **18-F10** | "the 2.5th and 97.5th percentiles" | not a number — 0.975, 0 or 1 on the same replicates by convention. Statistic, quantile method, RNG, bit generator and resampling convention all frozen (§6) |
| **18-F11** | "one final attempt is prespecified" | unauditable. A **registration written and timestamped before any outcome**, naming the claim, digests, the designated attempt, the seed-generation rule and the stopping rules (§10) |
| **18** | partial penalties "declared in the spec if not apportionable" | a hole. **Every penalty is apportioned, no exceptions**; the restricted-access 120 s is named as apportioned cost and changing it is an amendment (§2.2). The wire companion plane's **capacity and precision are fixed** — one byte, five `OFF_NETWORK` bound classes (§9). The **finite-time branch** is stated before the no-result branches (§2.5) |

### Revision 3, after Codex pass 15 (8 High, 10 Medium)

Removed the design effect, the 2 km blocks, the pooling rule and the block bootstrap, on the finding
that spatially adjacent outcomes do not make an SRS a cluster sample; raised the allocation to
*n* = 500 chosen by failure tolerance, after revision 2's gate proved unreachable at 1.4867% against
1.0%; required coordinate destination attachment; added the product `UNKNOWN` column; replaced the
undefined pilot with fixtures, a development sample and a freeze; decided the maximum duration; and
required non-zero statistical fixtures after a wrong implementation passed every zero-event one.

### Revision 2, after Codex pass 14 (4 High, 3 Medium)

Replaced four overlapping pooled strata with two self-weighting samples plus unpooled diagnostics;
split one building frame into two frames with their own estimands; gave the gate an explicit
acceptance rule and an INCONCLUSIVE outcome; specified the comparator and a verdict table; and made
E3 falsifiable.

One judgement kept from revision 1: the allocations are sized for **small** rates, and that is a
**planning assumption, not evidence**. If the development sample shows rates near 0.5 the allocations
are insufficient and the result says so rather than being reported at a margin it cannot support.
