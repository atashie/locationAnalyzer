---
name: project-phase0-progress
description: "Phase 0 state at the end of 2026-11-03 - engine decisions, what is measured, known gaps, and the Phase 1 stage order after Codex pass 7"
metadata:
  node_type: memory
  type: project
  originSessionId: 3448970c-7f62-4034-83e7-b7d86efb0261
  modified: 2026-11-03T23:25:20.685Z
---

Branch `v2-rethink`, ~42 commits, nothing pushed. Code in `v2/` (118 tests, `cd v2 && uv run pytest`).
Research in `docs/research/` (00-14, seven Codex adversarial passes). Results in `docs/experiments/`.
Phase 1 plan: `docs/plans/2026-11-03-phase1-plan.md` **revision 2**.

**Routing engines, decided per mode by exact-pair comparison (never by comparing rasters):**
walk = our own graph (unbiased, passes, but Valhalla's walk speed was set equal to ours so it was
never independently tested); bike + drive = Valhalla `/expansion` (ours is 4-7 min optimistic vs
every reference); transit = MOTIS (Valhalla returns 501 for arrive-by multimodal).

**The expansion adapter had never been run on real data, and was wrong.** Codex pass 7 C5, which I
reproduced: for a ROOT edge `expansion.py` assumed the stored geometry ran *away* from the search
origin; where it runs toward it, the two endpoint times swap - destination gets a full edge
traversal, a node 39 m away gets 0 s. Fixed by *deriving* orientation (supplied origins first, then
the vertex shared with successors, else raise). Also: an edge naming an absent predecessor used to
become a fabricated time-zero root. **Nothing outside tests calls this module**, and
`g1_expansion_primitive.py:47` requests only `duration`/`distance`, not the `edge_id`/`pred_edge_id`
it needs - so `g1-routing.md`'s measured expansion numbers describe a *different* implementation
than the adopted one. Re-measuring on real payloads is Phase 1 S1.

**Two-weight access model: verified PASS.** Exact identity `cost == reported + penalty accumulated
on that path`: 0 violations on 539,814 nodes, residual 3.6e-12 s, 12.6% of nodes carrying a real
penalty; plus an independent predecessor walk re-summing 36,802 hops from the graph, 0 mismatches.
**Two earlier FAIL verdicts are withdrawn - both were the test's fault, one was committed.**
`reported == cost-based` is NOT a leak signature: it means the chosen path carries no penalised
edge, so time equals cost necessarily. The lesson worth keeping: before trusting a verification
verdict, check it fires correctly on a case the suite already certifies - this one flagged Codex's
own fixture.

**Phase 1 stage order (revision 2, after pass 7):** S0 semantics *before* any encoding (status
provenance, algebra truth table with known-failure-beats-unknown, per-anchor AND vs min(A,B),
transit query identity) -> S1 primitive repair + real-payload measurement -> S2 name resolver
(unbuilt, absent from revision 1) + legal-connector access + building-weighted coverage -> S3 grid
and encoding evaluated at *matched* coordinates, then frozen (100 m and 200 m grids are **not
nested**: origins 661900/4003500 vs 661800/4003600) -> S4 reproducible build + atomic publication +
freshness gate -> S5 vertical slice + owner gates -> S6 breadth -> S7 release acceptance.

**Accuracy claims, framed to avoid the recurring failure:** construction fidelity against the same
engine is PASS/FAIL and is *not* decision 12; engine disagreement is reported; **real-world accuracy
stays UNVERIFIED until independent observation** (hand-timed journeys). 60 sampled cells per side is
a pilot: with zero observed failures the one-sided 95% upper bound is 4.87%, not zero.

**Still open:** lawfulness (not just residential) of routes the access fix recovered; no paired
before-array exists and must be regenerated on frozen inputs; the penalty sensitivity table's
coverage column is superseded (it omitted `node_cost`/`cutoff_s`, reading 77.3% against the
production 76.8%); `licence.py` returns one licence where D3 requires the validated set;
`fetch_places.py:31` reuses a raw file regardless of requested release; G4 device sessions, G5a
households and the G3 phone run all need the owner.

Related: [[project-v2-rethink-decisions]], [[reference-codex-runtime-quirks]],
[[feedback-experiments-over-priors]], [[feedback-codex-adversarial-review]].
