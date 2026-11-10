---
name: project-phase1-s3-design
description: "S3 state after plan §0 steps 0 and 1: the walked-journey audit harness and the Chapel Hill sheet exist, encode_minutes rounds up, three of §12's four items are settled and the geometry arithmetic is the one still open and still gating T3. Codex passes 25-30. No sampling has happened"
metadata:
  node_type: memory
  type: project
  originSessionId: 3448970c-7f62-4034-83e7-b7d86efb0261
  modified: 2026-11-09T00:00:00.000Z
---

As of 2026-11-09, head `f8b123f` on `v2-rethink`, pushed. **No sampling has happened.** Design
`docs/plans/2026-11-04-s3-measurement-design.md` is **revision 11**; plan
`...-s3-execution-plan.md` is **revision 11**, whose **§0 is the entry point** and now carries
per-step status. Codex passes 14-26 are `docs/research/21-` to `33-`; passes 27-30 ran in-session
and their findings are recorded in the commits named below rather than as research files.
Build record: `docs/experiments/s3-instrument-build.md`.

## Where §0 has got to

**Measured 2026-11-09, not recalled:** 1,159 collected, **1,135 passed, 24 skipped**; 31 scenarios,
14 mutants, 17 conformance cases.

| step | state |
|---|---|
| 0 — the audit harness | **done**, `0a4a24b`..`c081920` |
| the encoding decision | **done**, `2bb839d` — owner chose `ceil` |
| 1 — the cheap correctness debts | **done** `ed8bb6b`, `f8b123f`; three of §12's four items |
| 2 — the missing conditional | **next**, and an owner decision |

**The thing to walk:** `docs/experiments/audit/triangle-grocery-walk-chapelhill.csv` — 16 journeys
inside 5 km of Franklin Street and Carrboro, **3.01 h one-way**, longest 22 min. Codex pass 29
verified it fit to walk: byte-identical regeneration, all three input digests matching, all 16
encoded minutes matching the current raster. Its own README is the protocol; there is no `agrees`
column, deliberately. See [[project-phase1-s3-step0-audit-harness]].

**The encoding is `uint8-minutes-ceil-v1`** and is stamped in every raster and the browser manifest.
`rint` did not shift the threshold, it destroyed the verdict — 590 s and 610 s both encoded to 10 —
and 8.15% of what the browser showed as passing ten minutes did not pass. See
[[project-phase1-s3-encoding-threshold-crossing]]. The larger of step 6's two findings is **not**
fixed: the render worker treats `NODATA` as excluded, so the export collapses UNKNOWN into EXCLUDED
and the three-outcome algebra does not reach the browser.

**§12's four amendment items are now labelled individually, because they are not the four things
step 1 did.** Items 2 (uniqueness), 3 (numerical domain) and 4 (cost discriminator) are settled.
**Item 1, the geometry arithmetic, was never in step 1's scope and is still open** — Codex pass 30
found two witnesses inside the newly declared numerical domain, so the domain does not close it, and
**T3 remains gated on it**. It needs exact binary-rational arithmetic in the projection: a
revision-12 change, not a cheap debt.

**What four adversarial passes cost, as a fact about this work rather than a complaint.** Passes
26-30 found roughly twenty verified defects across step 0, the encoding change and step 1 — and the
majority were in the *repairs* for earlier findings, not in the original work. Pass 26 inverted my
central claim (200 m is the floor of the OFF_NETWORK access distances, not the ceiling); pass 27
found the guard I wrote in response was a false refusal; pass 28 found the provenance sidecar I added
was certifying seconds the build never wrote; pass 29 found a guard built from a loose substring
match had silently skipped an import; pass 30 found the uniqueness promise I had just weakened was
still too strong. The pattern is recorded in
[[feedback-verify-the-shape-of-the-risk]] and
[[feedback-a-fixture-is-exact-only-where-you-point-it]], and the practical lesson is that a repair
deserves the same adversarial pass as the thing it repairs.

**`master` is merged in as of `763540a`.** `v2-rethink` branched at `be2acf8` and had missed the 11 commits `master` gained since — including `3c0360c`, which moved these notes out of the machine-local memory store into `docs/engineering-notes/`, and the `CLAUDE.md` rule that makes that the standing practice. Checking out `v2-rethink` on a second machine would therefore have produced **no notes and a `CLAUDE.md` without the rule** — exactly the failure the migration existed to prevent. Only `.gitignore` conflicted (both branches appended at the end); both sides kept. `skills/planning-route-stops` came along with it.

**A branch mistake, fixed:** five V2 commits had been made on `oneoff/gnv-chapelhill-trip`
(interleaved with that trip's commits) rather than `v2-rethink`. Cherry-picked across; `v2/` and
`docs/` verified byte-identical. Check `git branch --show-current` before committing V2 work.

**Built — counts measured 2026-11-09, not recalled (`uv run pytest`: 1,091 passed, 24 skipped,
1,115 collected; 328 pre-S3, 140 T1, 30 T2, 112 T4 corpus, 459 invariants, 31 mutation guard,
15 T9):**
- **T1** `measure/stats.py` — exact one-sided Clopper-Pearson both directions, §8 acceptance, frozen
  bootstrap, SRS and two-stage variance. Confidence domain **[0.5, 1)**.
- **T2** `measure/frames.py` + `scripts/build_dev_frames.py` — the draw is normative
  (`PCG64(seed)`, `permutation(N)[:n]`, then `random((n, 2))`). Development frames **B `51a59463`,
  C `7914e80a`** at *n* = 500 (digest version 2). `verify()` still has **no non-test caller**;
  byte-backed arrays stop accidental writes but not a native write through
  `__array_interface__`.
- **T4** `measure/toy.py` + `conformance.py` + `conformance_cases.py` — **17 cases, 23 numeric
  rejected values** (cases measured), corpus digest `e645be28`.
- **T4's second layer** `measure/invariants.py` + `mutants.py` — **31 scenarios, 14 mutants** (measured).
  **Nine** mutants escape the corpus; **one** escapes the invariants (`pass20-F5-strict-cap`); each is
  caught by the other layer, and `EXPECTED_COVERAGE` pins the split.

  > `EXPECTED_COVERAGE`'s tuples are **`(invariants, corpus)`** — `test_mutants.py:100` unpacks
  > `want_invariants, want_corpus`. Read in the order the names suggest they come out backwards,
  > which is how an earlier version of this note came to say "six escape the corpus".
- **T9** `measure/e3.py` — the §3 disjunction, FAILED or UNVERIFIED only.

**Pass 22 is the one to remember, and its lesson is in
[[feedback-a-relative-invariant-cannot-see-an-absence]].** It defeated the whole instrument with a
uniform `<=4`-edge bound on path enumeration — **423/423 tests passed**, reproduced locally — and
found that three of my invariants *reject correct answers*. All corrected: the affine law replaced by
concavity plus conditioned affinity, the route check weakened to an implication, orientation excluded
under `translate` only, `differences()` reordered, hop depth declared as `CHAIN_DEPTHS` and anchored
to numbers, and both layers switched to `toy.evaluate` with a sentinel mutant guarding the harness.

**Two design claims withdrawn** (§13, top): the affine scaling law including the intercept inference
that was supposed to prove connector inclusion; and the subdivision exposure, which said "float noise
except on a zero-length segment" and is wrong on an ordinary straight edge.

**T3 has been refused four times** — passes 19, 20, 21, 22 — and pass 23 found a defect in every one
of the four replacement rules written for pass 22. **Four rules are still owed**, all named in §13 and
in the plan's T3 section, none an owner decision. (The candidate universe is *not* among them any
more: revision 9 claimed to settle it, was reverted, and §2.2 now declares a convention — see the
REVERTED block below.) Plan §0 step 1 boxes rules 3 and 4 at half a day together with the weakened
uniqueness promise:
1. **The geometry arithmetic** that produces a traversal fraction. Revision 8 froze
   `f × (cost_base + penalty)` as one term and left the fraction unfrozen; `sum` against left
   accumulation of one edge's segment lengths reports **1,000 s against 1 s**. **Already decided in
   principle:** 0.6 is the exactly-rounded sum (nearer the true total than 0.6000000000000001 by 3x),
   so extend §2.4's existing exactly-rounded order-independent summation into the geometry. Pass 22's
   suggested left accumulation is the *less* accurate option and is not adopted.
2. **What uniqueness §2.4 promises.** Node simplicity makes the route set finite, not a
   reconstruction unique — three partial journeys tie on every declared field at 50/450/50 m,
   flipping T10's boundary touch between **0% and 100%**.
3. **The admissible numerical domain.** `1e-200` segment underflows to degenerate (7.94e-201 s where
   1,000 s is required); `1e308` cost plus `1e308` penalty totals to `inf` then raises from an empty
   `min()`. Query coordinates unvalidated.
4. **The final cost discriminator** — implemented in `toy.py`'s `rank_key`, absent from the
   normative lift.

Plus: independently derived decision *and provenance* fixtures, an oracle carrying the complete
declared observables, frame verification at measurement consumption, and T6's companion artifacts
(**pass-22 F12**: T9's observations, T10's footprint/band/denominator, diagnostic memberships,
certification history including voided runs, the analysis configuration itself).

**REVERTED — design revision 10. The candidate universe is a declared convention, and the choice is
deferred to measurement.** Revision 9 (exact minimum per edge record, then the band) lasted **one
hour**. Codex pass 24 found it unsound and I reproduced both findings:

* it compared **computed** residuals for exact equality, which discards genuine geometric ties — two
  arms at exact rational squared distance **1** compute as 0.9999999999999999 and 1.0, so one was
  dropped: **996.764 s FAIL** against **16.912 s PASS**;
* it **did not fix** the subdivision case it was adopted for (`split_segments` still moves 996.764
  FAIL → 16.912 PASS: the sensitivity is in the **projection arithmetic**, not the band — I changed
  the step that was not the cause);
* and a pure **degree-two record split** moved 600.035 FAIL → 599.979 PASS, so record segmentation
  became part of the answer.

§2.2 now **declares** per-segment minima plus the band as a convention — a function of the supplied
geometry, not a property of the road — with sensitivities listed rather than denied. **§12's
equivalence contract was rewritten**: the old "implementations may vary only while preserving those
rules across admissible inputs" claimed a portable equivalence this project has not supplied, so T3
can be a frozen **versioned development comparator** and not a universal reference.

**Pass 26 reviewed the reversal before it was made and corrected three things I had overstated** —
revision 9 did *not* "buy nothing" (it fixed its motivating case, and revision 10 reinstates that
sensitivity knowingly); "strictly worse" overstates agreement on two representations; and the 60 s
tolerance is an **aggregate real-world target**, not an allowance to spend on the attachment rule. It
also corrected my rarity argument: zero events in 1,000 observations **per frame** bounds the rate at
about **0.30%**, not "a handful in 512,633".

**Codex pass 25 (`docs/research/32-`) reviewed the whole effort for fitness and moved the entry
point.** It judged the work *disproportionate and elaborating the wrong axis*: eleven adversarial
passes and ~11,000 lines of apparatus had gone into the instrument while the grid and encoding
decisions **S3 exists to make** were unstarted, and the estimand carrying nearly all the rigour
(E1) compares our pipeline to **our own engine**. Two specific findings: **E1b measures the wrong
conditional** — `Pr(product PASS and comparator FAIL)` over the whole frame, not `Pr(wrong |
displayed)`, so a 1% frame-wide rate can coexist with 10% of *shown* results being wrong — and a
**closed grocery passes both E1 and E2**, because both sides share the destination list.

**Execution plan revision 11 adds §0, the risk-ordered next steps**, and that is now the entry point
to the plan. Ordered by *product risk retired*, not defect severity, per pass 25:

0. **The audit harness** (half a day) — so the owner can start walking real recommendations, the
   only item that tests whether the product tells the truth rather than agreeing with itself. A
   closed or unusable destination is a **failed recommendation**, not a discarded row.
1. The cheap correctness debts (half a day) — the four rules below.
2. The missing conditional-reliability estimand (half a day; **owner decision**, it changes what is
   reported).
3. **T0** (one day).
4. T3 as a versioned development comparator (2-3 days).
5. **S3.1 — the matched 100 m / 200 m grid comparison**, the decision S3 exists to make.
6. S3.5 — the browser path end to end, before any byte freeze.
7. Grocery and geocoding truth audit.
8. The one-page decision report, then a bounded household release.

**Cut** on pass 25's recommendation: further general-purpose mutation or invariant expansion, portable
bitwise comparator equivalence, unique reconstruction beyond what an output actually consumes, and
certifying every future mode before this narrow release. **No more apparatus without a named
product risk.**

**Step 0's reconnaissance is done, and two findings matter.** There is **no coordinate-to-cell
helper anywhere in `locfinder/`** — `GridSpec` goes centre-outward only — so `cell_for_xy` /
`cell_for_lonlat` must be written. And `status.Surface` needs `min_possible_s`, which is **not
stored** beside the layer; but the real reason array holds **only 0, 1, 2** (`OK`, `OFF_NETWORK`,
`BEYOND_HORIZON` — no `NO_PATH`, as S0 found), and `evaluate` reads `horizon_s` directly for
`BEYOND_HORIZON`, so a **sound** bound is reconstructible as *seconds where OK, the horizon where
BEYOND_HORIZON, 0 where OFF_NETWORK*. That lets the harness skip the 670 MB `roads.graphml` and run
in about a second.

> **Corrected after Codex pass 26 built it.** Two claims written here before the work were wrong.
> The `NO_PATH` assertion is a **fail-fast, not a correctness barrier**: `Surface.validate` rejects
> a `NO_PATH` cell whose bound is not `+inf` and `evaluate` fails `NO_PATH` unconditionally, so
> nothing would have been *silently* misread. And the `0` for `OFF_NETWORK` is **sound but lossy,
> not exact**: a cell is `OFF_NETWORK` because `access_m > max_access_m`, so 200 m is the *floor* of
> those distances and the real bound is unbounded above. The reconstruction can report `UNKNOWN`
> where the pipeline proves `FAIL` — losing information, never manufacturing an exclusion — and is
> exact only for cells **adjacent to an `OK` cell**, which is all the harness emits. See
> [[project-phase1-s3-step0-audit-harness]].

**T0 keeps its design and moves to position 3**: pass 26's staged
prevalence-and-impact pilot on the real Triangle graph (all data already on disk), **time boxed to
one developer day**, with the sensitivity budget allocated **before** the results are seen. Then pick
among A (current convention), B (exact rational predicate + degree-two normalisation), C (revision 9
with record dependence declared), D (exact minima globally, no band).

**The lesson, and it is the real one:** four passes diagnosed the *process* and the instrument I built
in response did not stop it. The failure is not in the rules — **I keep deciding by argument and then
describing the argument as a measurement.** Plan §2a records pass 26's decision procedure. See
[[feedback-decide-by-measurement-not-by-argument]].

**The four owner decisions still stand** (finite-population SRS at *n* = 500 by failure tolerance;
coordinate attachment with modelled connectors; diagnostic A on product verdicts; 120 minutes at
whole minutes with codes 121-254 a versioned status plane).

**Verified artifact figures — do not re-derive:** 522,160 buildings, **512,633** projected centroids
in-grid, 643 x 514 = 330,502 cells at `x_min` 661900 / `y_max` 4003500 (so `y_min` 3952100), 200 m
grid non-nested by -100/+100 m, **550** groceries (549 eligible) from 107,484 accepted places,
539,814 graph nodes. Walk **access** speed **1.26** m/s; the off-network bound divides by
**`max_speed_mps` = 1.40** — different quantities, and confusing them was a recorded error. Building
reasons 499,009 OK / 3,657 OFF_NETWORK / 9,967 BEYOND_HORIZON; cell reasons 256,752 / 57,541 /
16,209. A full-graph Dijkstra is **0.057 s**, so E2 is collected in full.

**Scope reality:** only walk/grocery exists at Triangle scale (514, 643); every drive/bike/Valhalla
layer is (401, 550). The verdict is reported for walk/grocery/Triangle only and the gate re-runs per
mode in S6.

**Still owner-gated:** the **coverage requirement** (blocks the
coverage claim only), the 5-8 hand-timed E3 journeys, the G4 device matrix, G3 phone render, 3-5 G5a
household sessions.

Related: [[project-phase1-s2-progress]], [[project-h2-upper-bound-trap]],
[[feedback-a-relative-invariant-cannot-see-an-absence]],
[[feedback-fix-the-domain-not-the-example]],
[[feedback-a-fixture-is-exact-only-where-you-point-it]],
[[feedback-a-predeclared-gate-must-be-shown-reachable]],
[[feedback-match-statistical-machinery-to-the-design]].
