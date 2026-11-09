---
name: project-phase1-s0-complete
description: "Phase 1 stage S0 (the layer contract) is done and committed as 90074e6 - what it decided, the two measured findings, and what S1 picks up"
metadata: 
  node_type: memory
  type: project
  originSessionId: 3448970c-7f62-4034-83e7-b7d86efb0261
  modified: 2026-11-04T14:02:38.146Z
---

Committed 2026-11-04 as `90074e6` on `v2-rethink`. 184 tests pass (118 before S0).
Contract: `docs/plans/layer-contract.md`. Code: `v2/locfinder/{status,identity,profile}.py`,
`layer.build_layer_surface`, `snap.cell_arrival_with_provenance`.
Codex pass 8: `docs/research/15-codex-adversarial-review-pass8-s0-contract.md`.

**No encoding was chosen.** That is S3.5, deliberately after the measurements that decide it. The
enum integers in `status.py` are in-memory array codes and must never reach a raster.

**The 23.24% of Triangle walk cells with no time, decomposed for the first time:** OFF_NETWORK
17.41% (57,541), BEYOND_HORIZON 5.83% (19,282), NO_PATH 0%. Sums to 76,823 = exactly the committed
artifact's nodata.

**NO_PATH is unreachable in every shipped configuration.** `symmetrise` runs before
`largest_component`, so the retained walk graph is 1 strongly connected component with 0 of 539,814
nodes unreached; bounded engines (Valhalla expansion, MOTIS) cannot claim it either. **Component
pruning** (3,046 components, 13,608 nodes dropped) is how a disconnected neighbourhood actually goes
missing - such cells snap to a retained road up to 200 m away and read a finite time on a road they
may not be able to reach. That makes S2.4's build-time diagnostic matter more than the status.

**The category surface is NOT min-over-destinations** (Codex pass-8 H2, reproduced): the search
picks the destination nearest by *cost* and reports that path's time, so a 20 s grocery behind a
penalised private edge reads as the 100 s one. It is an **upper bound**, so category criteria give
false exclusions, never false inclusions. Measured on the real build: 9.25% of cells differ (median
37.7 s, max 668 s) but only **0.16-0.83% of passing cells change verdict** at 10/15/25/45 min.
Aggregation renamed `cost_selected_category`. Fixing it properly means changing the access policy,
so it is a design decision for the owner, not a bug fix - and the figures rest on the 450/120 s
penalties that `access.py` labels priors.

**Two of my own claims were false and are corrected in the contract**: the category minimum above,
and the lower-bound rationale (the access-speed bound IS sound and tighter; the weaker
`max_speed_mps` one is kept as a judgement, so an unmapped-driveway fiction does not exclude
households). Both were docstring arguments never executed - the same shape as the `expansion.py`
bug. The lesson that keeps paying: **write the test that forces the real pipeline to produce the
thing, not a test that the enum has four members.**

**Exhaustiveness belongs to the call, not the engine** (H1): `node_reasons` requires
`search_bounded`; `layer.py`'s single-weight branch no longer passes a node cutoff
(output-preserving, verified over 25 graphs x 400 cells).

**Derived versions are enforced**: `SurfaceKey` refuses a hand-typed `profile_version`/
`grid_version`. Current values: profile `speeds-v0+9893b1b0168ff19a`, grid 100 m
`grid-v0+7ab61db26b3cc98e`, 200 m `grid-v0+a1259d05712a3ce2` (the grids are **not** nested).
Still unrepresented and listed as S4.1 obligations: category selector version, source/content
identities, Valhalla version and costing options, transit access/egress settings.

**Next: S1.** Add `edge_id`/`pred_edge_id` to `spikes/g1_expansion_primitive.py:47`, pass
`origins=`, route through `expansion.py`, report the `report=` counts, then S1.3's structural checks
*before* S1.4's paired re-measurement.

Related: [[project-phase0-progress]], [[project-v2-rethink-decisions]],
[[feedback-codex-adversarial-review]], [[feedback-experiments-over-priors]].
