# Codex adversarial review, pass 18 — S3 design revision 4 and plan revision 3

**Date:** 2026-11-05. **Model:** gpt-6.1-sol. **Head at review:** `d021072`. **Prompt:**
`codex-pass18-prompt.md` (scratchpad).

**Twelve defects: 3 High / 8 Medium / 1 Low.** Eighteen, eighteen, twelve.

> "**D is not yet sound enough to measure against, and P is not fit to execute end to end.** The
> statistical redesign largely survives. The remaining blockers concern which product is being
> measured, unresolved comparator semantics, and acceptance rules that still permit incompatible
> implementations."

And the sentence that changes what happens next:

> "**T1 and T2 can proceed as instrument-development work after tightening their test oracles.**
> Their completion would not yet authorise certification."

Of revision 4's nine requirements: **three done, six partly done, none missed.** The statistical core
— full-frame joint estimands, the corrected two-stage variance, DEFF removal, unpooled diagnostics,
E2's status cross-tab, E3's disjunction, the extraction warning — all survived.

## The three High findings

### F1 — my tie rule governs the wrong tie

§2.4's rule applies to alternatives tied on **the objective's selection weight**. But nearest-edge
**attachment** minimises **geometric distance**, and equidistant edges can have wildly unequal
objective weights — so no objective-weight tie ever occurs and the rule never fires.

Executed: two disconnected directed roads from x=0 to x=100 at y=−1 and y=+1, origin `(0,0)` and
destination `(100,0)` each exactly 1 m from both, travel times 100 s and 1,000 s.

```
south attachment:  101.587 s
north attachment: 1001.587 s
```

Both implementations obey every stated rule — nearest position, access cap, connector charging,
direction, objective minimisation — and **the verdict differs at ten minutes.** This is precisely the
gap I asked pass 18 to hunt for in the "implementations may vary while preserving the rules"
contract, and it found it: the contract cannot establish equivalence while both answers satisfy it.

**Fix:** define selection among **all** geometric minimisers — either retain every equally-nearest
attachment as a routing candidate, or impose a frozen total geometric/identity order — plus the
multiple-equally-nearest-positions-on-one-geometry case, and whether equality is exact or
tolerance-based.

### F2 — the E0 census uses the wrong partition once the product is exported

A cell's verdict determines every point inside it **only while the lookup uses that same partition**.
Frame C's within-cell point does not break the original-grid census — export does.

Executed with rasterio: two original 100 m cells (UNKNOWN, PASS) exported nearest-neighbour onto a
shifted 80 m grid give published bytes `[UNKNOWN, UNKNOWN, PASS]`. The original second cell's centre
at x=150 returns PASS while its interior point at x=110 returns UNKNOWN — **20% of that cell is now
UNKNOWN**, and a structure at x=110 is UNKNOWN although its cell's centre is not.

**Fix:** define E0 over the **actual published lookup** while keeping the original frames:

> `E0_B(T)` = mean over frozen structure centroids of `1{published_lookup(centroid, T) = UNKNOWN}`
> `E0_C(T)` = area of UNKNOWN published lookup over the original frame-C domain ÷ area of that domain

My §3 formulas are valid **shortcuts** only once the published lookup is shown constant on every
original cell. An exact exported census needs projected-area intersection; an approximation must
report its error and **must not be called uncertainty-free**. Lookup behaviour outside the exported
footprint must be defined.

### F5 — E2 still permits two different connector policies, so it is not yet one quantity

§2.6 offered a choice — add agreed connectors to the independent comparator, **or** retain its
attachment model and declare the difference inside E2 — and revision 4 never chose. Those are
different estimands.

Executed: destinations A (cost 10, time 10 s, 100 m residual) and B (cost 20, time 20 s, 0 m). The
raw engine policy selects A and reports **10 s**; charging A's connector at 1.26 m/s moves the
cost-`argmin` to B and reports **20 s**. Both satisfy §2.6 as written.

> "Merely recording 'connectors made explicit' does not choose the quantity."

## The Medium findings

- **F3 — my physical explanation used the wrong speed.** `min_possible_s = access_m /
  max_speed_mps(mode)`, and walk's maximum is **1.40 m/s**, not the access speed 1.26 — a sound lower
  bound divides by an upper bound on speed. So the proven-over distances are **840 m and 1,260 m**,
  not 756 and 1,134. Using my figure would give 3,534 and 604 proven-over cells against the correct
  **2,439 and 298** — so my "internal consistency" check happened to confirm the right subtraction
  through wrong physics. The measured maximum nearest-edge distance is **1,688.99 m**, which is the
  real reason nothing is proven over at 25 and 45 minutes (they need 2,100 and 3,780 m), and the
  200 m access cap does **not** bound how far an off-network cell sits from the graph.
  **Codex independently reproduced the whole carried E0 table**, so §3's figures are now verified.
- **F4 — identity and grouping must be frozen separately from ranking, and three stages disagree
  today.** `speeds._physical_key` groups by `osmid` + length rounded to 2 dp;
  `snap._canonical_geometry_key` uses exact coordinates allowing reversal; the CSR collapse uses the
  ordered endpoint pair. Executed: a straight forward road and a curved reverse road sharing
  endpoints, `osmid=[7]`, length 100, time 100, cost 100 — the three specified tie keys are equal and
  `_physical_key` calls them identical, while the geometry key does not. **The symmetriser suppresses
  both reverses as duplicates while the attachment index treats them as two roads, leaving reverse
  weight `inf` for each.** Repeating a tie comparator in three stages cannot repair incompatible
  grouping. My rule's three keys are also **not total** — different geometries can share all three.
- **F6 — the acceptance rule is still not executable.** "Bounds straddle a threshold" does not say
  whether it means completed proportions or confidence bounds, nor which completion supplies §8's
  "point estimate". Executed at *n* = 500 with *k* = 1 known and *u* = 1 unresolved: completed
  proportions 0.2%–0.4% (below 1%) but completed upper bounds 0.945%–1.254% (crossing it). The
  replacement is explicit:

  > **PASS** if `CP_upper(k + u, n) ≤ threshold`; **FAIL** if `k/n > threshold`; **INCONCLUSIVE**
  > otherwise — with *n* full-frame, and the identification range and the confidence bounds reported
  > as distinct objects.
- **F7 — my abstention diagnostic does not protect the gate, and I claimed it did.** Executed: an
  **all-UNKNOWN product produces zero E1a and E1b events**, so both upper bounds are **0.5974%** at
  *n* = 500 and it **passes both construction thresholds**. A diagnostic cannot reverse that without
  an acceptance rule. Also, a definitive coordinate answer does not prove a contract violation: a
  deliberately capped or coarser raster may correctly return UNKNOWN under its published rules while
  a more expensive coordinate calculation answers. So it is an **opportunity measure** —
  "coordinate-answerable product abstention" — needing an explicit numerator and denominator, and the
  claim that it prevents E1 passage must go.
- **F8 — persistence and the report dependency graph are incomplete.** T6 lists own-objective values
  but not the float product value, the decoded product value, or the finite independent objective-2
  value — and a verdict at four thresholds cannot recover a number, since **100 s and 200 s both PASS
  at all four**. Digests identify missing data; they do not reconstruct it. The **full E0 census**
  also cannot be rebuilt from 500 sampled rows once the rasters are gone. And T11 depends only on T8,
  so it can nominally complete without T9's E3 result or T10's extraction diagnostic, and its
  checklist omits E2's IQR and exceedance share.
- **F9 — T1 still admits a wrong implementation.** "A declared tolerance" put no limit on the
  tolerance: at an absolute tolerance of **0.002**, an implementation correct everywhere except
  `n=400, k=1` — where it returns the old defective 0.009943 against the correct 0.011804 — passes
  every stated fixture, both tolerated-count assertions and every endpoint check, **while flipping
  the 1% decision**. The lower-bound tests also have no non-zero oracle: a mistakenly **two-sided**
  lower bound passes them (correct one-sided at `k=1, n=500` is 0.000102581; two-sided gives
  0.000050634). Fix: fixtures at **1e-10**, non-zero lower-bound fixtures, complementary
  upper/lower identities, and at least one oracle derived by **binomial-tail inversion** rather than
  by calling the same Beta inverse the implementation uses.
- **F10 — the bootstrap percentile convention is unspecified.** Executed on 2,000 replicates of 50
  zeros and 1,950 ones, the "2.5th percentile" is **0.975 linear, 0 lower, 1 higher, 1 nearest** —
  all satisfying the phrase. A recorded seed also does not identify a sequence without its generator
  and resampling convention. Fix: freeze the replicate statistic, the endpoint quantile method, the
  RNG and bit generator, and the resampling convention — and test percentile calculation on a
  **fixed replicate vector**, independent of RNG reproduction.
- **F11 — "one final attempt prespecified" is not auditable.** Recording outcomes does not stop an
  operator amending the instrument and designating the next attempt final. Before any outcome is
  observed, register the claim and instrument/design digests, the uniquely identified designated
  attempt, the draw procedure and seed-generation rule, the stopping/invalidation/replacement rules,
  and how earlier outcomes and later amendments affect the claim — timestamped independently of the
  report. (At *p* = 0.01: 0.0397547 for one attempt, **0.5557336** for at least one of twenty.)
- **F12 (Low) — eight verdicts, not sixteen.** 1 mode × 4 thresholds × 2 frames = **8 gate
  verdicts**, and 8 × 2 directions = **16 bounds**. The design says bounds correctly; my plan asked
  for "all 16 verdict combinations".

## What survived, and two useful refinements

- **Partial penalties: a model choice, not an arithmetic error.** `access.py` assigns a fixed **120 s
  per restricted walking edge** and `speeds.py` adds it to cost. On a 1% traversal, apportionment
  gives cost 1.21 while an entry fee would give 120.01, and the two select different routes against a
  5 s bypass. But **proportional apportionment is already the existing attachment model** and the
  design adopts it deliberately, so calling it wrong would overstate the evidence. The normative text
  should name restricted-access penalties explicitly as apportioned cost, enumerate exceptions, and
  forbid implementations inventing their own.
- **Unbounded objective-2 reconstruction is tractable.** With fixed destination attachments, virtual
  destination links plus a sink permit a reversed multi-source cost search, and predecessors support
  reconstruction without materialising every origin–destination path — Codex's constructed
  virtual-sink case returned the correct **11 s**.
- **Wire capacity is sufficient**: codes 121–254 plus a **suitably specified** companion plane work,
  one code per reason does not, and for four fixed thresholds `OFF_NETWORK` needs only **five ordered
  bound classes** (a numeric bound only for arbitrary thresholds). "One companion plane" says nothing
  about precision or capacity, so that must be specified.
- **Both exporter defects reproduced**, as I had also verified independently: discovery omits
  `own_triangle_grocery_walk.tif`, and padding turns `[120, 121, 254, 255]` into
  `[150, 151, 254, 255]` — scaling a prospective status byte as minutes.
- **Accidental development/certification overlap does not invalidate the interval**, provided the
  product is frozen and the certification draw is independently taken from the full frame. Excluding
  development units would change the frame.
- **A deterministic RNG-sequence oracle is a useful regression test but does not establish joint
  uniformity** — "merely because another implementation emits the same sequence". Pair it with
  independently specified RNG inputs with distinct offsets and enumerated toy-frame selection checks.
  And **T4's independence needs evidence** — calculations, fixture provenance, review against the
  normative quantity. "A digest establishes immutability, not correctness or independence."
- **The refusal to promise reachability is correct**, and with conservative unresolved completion
  passage at *n* = 500 requires at most **one identified-or-potential false inclusion and four false
  exclusions** per combination.
- Every artifact figure reproduced again, including 522,160 / 512,633, the reason totals, 550 and 549
  destinations, connector 18.8091 / 35.6460 / 477.4967 m, 234 cells at 120 all OK, the
  7,199.999 s maximum, 44.0082 / 76.6066 / 92.3206%, and the count-rule pass probabilities
  90.9872 / 28.6526 / 3.9755%.

**No new allocation, threshold or subsampling violation was found in the plan** — "its main
violations are incomplete implementation of D's contracts, rather than the earlier overt policy
changes."

## The minimum blocking set

1. Resolve **geometric attachment ties** (F1).
2. Define **E0 over the actual published lookup** while retaining the original frames (F2).
3. **Select the independent connector policy** (F5).
4. Make **unresolved-case acceptance executable** (F6).

Then, before freezing: the identity and grouping contract (F4), persistence (F8), the statistical
oracles (F9), the bootstrap convention (F10), and attempt registration (F11).
