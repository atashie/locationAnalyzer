# Codex adversarial review, pass 16 — S3 design revision 3 and plan revision 2

**Date:** 2026-11-04. **Model:** gpt-6.1-sol. **Head at review:** advanced from `ab01ffa` to
`87bb239` mid-review (same document revisions). **Prompt:** `codex-pass16-prompt.md` (scratchpad).
**Eighteen defects: 8 High, 8 Medium, 2 Low.**

> "The allocation arithmetic and removal of spatial DEFF survive. The repairs nevertheless introduce
> a mismatched E2 objective, an unsafe bounded-search implication, and changes to the instrument
> after certification. **UNKNOWN accounting makes the area-frame acceptance gate effectively
> unreachable again.**"

**All four owner decisions survive on the evidence.** What does not survive is my execution of them.
Second consecutive pass at eighteen findings, and the disposition table is the thing to read: of
pass 15's eighteen, **eight are fully resolved, seven are partly resolved with a new defect in the
repair, and three repairs introduced a defect of the opposite sign.**

## The headline: I made the gate unreachable again, by the opposite mechanism (F5)

Pass 15 H2 was an acceptance rule no observation could satisfy. Revision 3 fixed that and then
recreated it through the fix for pass-15 H8:

- 16.67% of frame C — **55,102 of 330,502 cells at *T* = 10** — is product `UNKNOWN`.
- §7 routes every product `UNKNOWN` into the unknown bucket, and §7 bounds that bucket **both ways**:
  once with every unknown as agreement, once as an error.
- The "every unknown as an error" bound is therefore ≈16.7% against an E1b threshold of 1.0%. The
  binomial probability of observing at most one such among 500 is **2.51 × 10⁻³⁸**.

And the conceptual error underneath is sharper than the arithmetic:

> "An observed abstention cannot secretly be a product PASS."

E1b is *false inclusion* — only a product **PASS** can produce one. E1a is *false exclusion* — only a
product **FAIL** can produce one. A product `UNKNOWN` is **fully observed**: we know exactly what the
product said. It is a **coverage** fact, not an unidentified directional error, and bounding it as
though it might be either conflates "we do not know what the comparator says" with "the product
declined to say". Those need separate estimands.

Codex also measured that this is not a corner: of 57,541 `OFF_NETWORK` cells only **2,439** have
bounds sufficient to FAIL at *T* = 10 and **298** at *T* = 15; at *T* = 25 and 45 **all 57,541** are
`UNKNOWN`. No comparator, however good, can eliminate a product abstention.

## Two repairs overcorrected in the opposite direction

- **F2 (High) — a cost horizon is not a time bound.** Pass-15 M9 said routing every bounded
  no-result to unknown *understates* known E1b. I then wrote "exhausted through *H* with nothing
  reached, *T* ≤ *H* → known failure", which *overstates* it. Executed with the repository's own CSR
  and arrival functions: one edge with **time 1, cost 121**, searched under a **cost limit of 60**,
  returns `inf` — while objective 2 returns **1 second**. My rule scores a FAIL at *T* = 60 for a
  route that passes in one second. `arrival_seconds_two_weight()` searches unbounded on cost
  precisely for this reason. Strictness matters too: `t > H` fails *T* = *H*; `t ≥ H` does not.
- **F1 (High) — E2's objectives are still different functionals**, and my stated reason for the
  mismatch was false. Our objective 2 takes `argmin` over **cost** and reports that path's time;
  revision 3's independent definition takes the **minimum time** across destinations' cost-optimal
  paths. Executed with identical engines on destinations `(cost, time) = (10, 10), (100, 1)`: ours
  gives 10, mine gives 1, so **E2 reports −9 s with identical engines**. And I claimed a Valhalla
  matrix "cannot be asked for" the right quantity — it can: a live local
  `3.9.1-2085e78a5` two-target response returned per-pair **costs** `(1068.25, 448)` and
  `(1194.771, 1174)`, so cost-based `argmin` is directly achievable.

## The pattern finding: I fixed the node layer and left the same defect one layer over (F3)

Pass-15 H6 was `graph_to_cost_time_csr()` collapsing parallel edges by cost. Revision 3 projects
objective 1 from the multigraph before collapse — and **`EdgeIndex.from_graph()` still keeps the
cost-minimum parallel alternative per physical geometry and direction.** Executed on coincident
100 m edges `(time, cost) = (1, 100), (10, 10)`: the corrected node CSR gives u→v = **1**, while
attaching an origin halfway along the segment through the existing edge index returns **5** instead
of **0.5**.

> "A correct node CSR does not protect mid-edge evaluation."

My own proposed node-level parallel-edge fixture passes this implementation. This is the third time
the same lesson has arrived — separate before the collapse — and the second time I applied it at one
layer and not the next.

## My own freeze, violated by my own task order (F6)

§10 freezes the instrument before certification. T10 then changes the writer, exporter and browser
decoder, **recomputes outcome-dependent diagnostic membership**, and re-runs the arithmetic on
certification data. T9 likewise evaluates a candidate grid on certification locations without
preventing selection from those outcomes.

> "Recomputing membership does not make an old conditional sample an SRS from a new predicate."

Candidate-grid and encoding selection, migration, browser checks and phone measurements must all
complete **in development**, before the freeze.

## Three of my new tests are impossible or weak

- **F10 — my bootstrap-widening assertion is mathematically false.** I required the interval to widen
  as the sample shrinks. Executed: `[-1, 0, 1]` gives `[-1, 1]`; the smaller `[0, 0]` gives
  `[0, 0]`. An assertion **no correct implementation can satisfy** — the failure mode I already have
  a note about, reintroduced while fixing a different one.
- **F11 — my E3 fixture contradicts the design.** I asserted that a journey 1.6× over but only 3
  minutes over "does not fail". For a single journey of reported **5** and observed **8** minutes the
  individual conjunction indeed does not fire, but the median signed difference **3** exceeds 25% of
  the reported median **5**, so the design requires `failed`.
- **F18 — my frame-C test still admits non-area sampling.** Marginal means and spreads do not
  establish joint uniformity: drawing one `u ~ U(0, 100)` and using `(u, u)` for both offsets gives
  both marginals correct over 100,000 draws (means 49.9574 m, sd 28.8447 m) with **correlation 1** —
  every point on a diagonal, zero probability over almost all ground area.

## The remaining findings

- **F7 (High) — the persisted record cannot reproduce the report or enforce the freeze.** One
  unkeyed `product_outcome` cannot represent four thresholds; `OFF_NETWORK` at 250 m and at 1,000 m
  share a reason but differ at *T* = 10, so reason + one outcome + a digest cannot recreate four
  decisions. No product lower bounds, no per-objective statuses, no independent bound metadata, no
  selected destination or cost, and **no paths — although T11 says paths are retained.**
  `origin_access_m` is the comparator coordinate's access, not the product cell centre's. The
  manifest also fails to freeze the independent engine's **tileset, version and costing
  configuration**, which local `/status` exposes.
- **F14 (Medium) — excluding development points breaks the SRS.** Conditional on a development set,
  excluded structures have selection probability zero and the rest `500/(N − N_dev)`, so the
  estimator targets the **complement** while the design claims all 512,633. Fix: an independent
  full-frame draw after the freeze, allowing accidental overlap.
- **F15 (Medium) — "void and redraw" has no repeated-attempt policy.** At *p* = 0.01 a 500-point
  attempt meets E1b's count rule with probability 0.0398; **twenty attempts give ≈55.6%** of at least
  one pass at the boundary. Retain every attempt's identity and outcome, and declare one
  prespecified final attempt or a sequential error budget.
- **F12 (Medium) — the diagnostic comparison ignores the reference's uncertainty.** A diagnostic
  lower bound above a *noisy population point estimate* is not a 95% comparison; the factor-of-two
  ratio is undefined when the reference is zero; and I specified only an upper-bound primitive while
  the rule needs a lower bound. With equal true rates of 0.001 the naive rule calls the diagnostic
  materially worse with probability **0.0845**.
- **F8 (Medium) — E2 has no missing-pair domain.** The raster has **73,750** nonfinite cells and the
  engines carry different horizons; dropping non-finite pairs silently changes the estimand to a
  conditional one, and pooling 2,600 origins changes its sampling distribution.
- **F16 (Medium) — the status plane needs more than one code per reason.** `OFF_NETWORK` needs its
  access bound and horizon-sensitive reasons need horizon metadata, or verdicts are not recoverable.
  `encode_minutes([121*60, 254*60])` still returns `[121, 254]`, so those remain valid durations for
  other layers and legacy dispatch must be explicit. And a concrete repository defect: **the exporter
  discovers only `<engine>_<category>_<mode>` names, omitting `own_triangle_grocery_walk.tif`**, and
  targets the old 401 × 550 slice; its padding helper scales every non-255 byte as a minute value.
- **F17 (Medium) — boundary touch cannot bound extraction damage.** Routes chosen *inside* a
  truncated graph cannot reveal what truncation removed: a slow interior path survives while a fast
  path through outside is gone, giving **0% boundary touch and 100% affected**. T11's upper-bound
  claim must go; it is a warning diagnostic, and a real bound needs a larger-extract comparison.
- **F9 (Low) — the variance statement is inexact.** For a binary finite-frame SRS it is
  `p(1−p)/n × (N−n)/(N−1)`, and frame C is **two-stage**: its within-cell variance gets no
  finite-population correction, so the true form is
  `[(1 − n/N) S_q² + mean(q_i(1 − q_i))] / n`. Numerically negligible at *n* = 500; conceptually
  wrong as printed, and a Bernoulli variance must not be applied to E2's median.
- **F13 (Low) — A excludes a reason where it should exclude a verdict.** The contract can return FAIL
  for `OFF_NETWORK` when its lower bound exceeds *T*, so A should exclude `UNKNOWN`, not
  `OFF_NETWORK`. It does not change the count here (none of the 2,439 known `OFF_NETWORK` failures
  touches a passing cell) and the **14-cell `BEYOND_HORIZON` cross-check reproduces**.
- **F4 (Medium) — a same-edge traversal is a candidate, not the route.** "The route is the partial
  traversal, not a detour via either node" is too strong: on a one-way `u→v`, an origin at 0.8
  cannot reach a destination at 0.2 directly; and even two-way, a slow direct 800 s traversal loses
  to 100 + 1 + 100 = **201 s** via a bypass. Walk symmetrisation supplies the pedestrian reverse;
  bike and drive cannot inherit it.

## And my own slogan was wrong

P §4 said "any number this plan appears to add is a defect in this plan." Untenable — fixture values
and implementation references are legitimate additions, and the 200 m grid candidate comes from the
phase-1 S3 context rather than from the design. The honest form is a prohibition on changing
**estimands, allocations, acceptance thresholds, uncertainty conventions, or adaptation and selection
policy** without a design amendment. Under that stronger rule, T10's post-certification adaptation is
a substantive violation.

## What survived attack

- **Every allocation-table value reproduces** from `BetaInv(0.95, k+1, n−k)`, both tolerance
  assertions are correct, and 473 is confirmed the minimum admitting one E1b failure. Planning by
  tolerated counts is legitimate. **But tolerance is not power:** at true E1b rates of
  0.001 / 0.005 / 0.01, the pass probability at *n* = 500 is **90.99% / 28.65% / 3.98%**. "Do not
  present a tolerance as expected performance."
- **DEFF removal survives.** Spatial adjacency alone does not make an SRS a cluster sample; separate
  structure and area frames and unpooled conditional diagnostics are right; uniform cell then an
  independent uniform point is unbiased for area-average error; a small-fraction point bootstrap is
  reasonable approximate inference for a regular E2 median. Effective-*n* adjustments "should not
  return".
- **Claim boundaries survive:** finite-population-only language, the E1/E2/E3 separation, convenience
  journeys unable to certify a rate, and no multiplicity adjustment for a global conjunction.
- **Every encoding and geographic figure reproduces**, including 234 cells at exactly 120 all `OK`,
  the 119.99998-minute maximum, 134 codes in 121–254, 44.0082/76.6066/92.3206% within 30/60/90
  minutes, 522,160 structures, 512,633 centroids, 550 groceries, 539,814 nodes, and the TIFF equal
  to `encode_minutes(saved_float)` everywhere.
- **The 2,600-origin budget and the 1.43 M independent-pair figure are correct.**
- One correction to a figure I quoted: under the **new nearest-edge** attachment the connector
  distances are **18.8091 / 35.6460 / 477.4967 m**, not the node distances 28.07 / 45.71 / 478.66 m
  I cited in §2 — those describe the old rule. Exactly one destination still exceeds the 300 m cap.

## Codex's own caution on decision 2

Coordinate attachment "is not implemented merely by supplying coordinates to Valhalla". Executed: a
target at `(35.999, −78.905)` and its correlated road position `(35.999022, −78.905211)` both
returned **448 s, 0.633 km, cost 1068.25** — the residual ~19 m is **not** charged at 1.26 m/s. So
the independent comparator needs explicit agreed connectors, or the attachment-model difference must
be declared *inside* E2 and kept separate from destination-selection aggregation.
