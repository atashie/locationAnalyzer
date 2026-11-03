# Codex Adversarial Review - Restricted Access and the Two-Weight Model (Pass 6)

Date: 2026-11-03 | Model: GPT-6 (Codex) | Method: read the requested decisions, experiment reports, seven implementation files, six test files and pass-5 review in order; inspected remaining callers and G1 records. Ran all 59 requested tests successfully without bytecode or pytest-cache writes; executed in-memory adversarial probes and 100 randomized multi-source comparisons (2,940 reachable-node checks). Read the stored Triangle walk array. NumPy 2.5.4, SciPy 1.18.1. No network calls, source edits or full experiment reruns; only this review file created.

## Verdict

- The two-weight CSR construction and node reconstruction are sound under the pipeline's ordinary positive-weight conditions. This does **not** establish correctness of the resulting cell layer.
- **Do not publish layers as access-correct yet.** Snapping discards cost and can choose the restricted shortcut that the node search deliberately rejected, even at an exact node.
- A finite per-edge penalty discourages through traffic; it does not prevent it or establish permission. `destination` receives no penalty whatsoever.
- The stored after-array confirms 255,547 finite cells, 77.3209% of 330,502. The approximate net gain reproduces from rounded percentages; its residential composition and legitimate access remain unverified.
- The histogram does not test penalty leakage. Existing synthetic tests provide better, though incomplete, evidence; add an independent path-sum oracle through final cell construction.
- All 59 tests pass, but the access test enshrines the `destination` mistake and the snapping tests never combine snapping with penalised routing. Twelve unchanged open-road journeys are a useful regression control, not a positive test of this fix.
- Correct cost-aware cell selection, access semantics and tag precedence first; then perform paired coverage, pruning and threshold audits. Decision 12 remains untested, and decision 17 supplies no permission to calibrate from restricted sources.

## Correctness of the reconstruction

In exact arithmetic, let d[n] be minimum cost from a destination on the transposed graph. Every non-root predecessor p satisfies d[n] = d[p] + c(p,n). If every stored cost is strictly positive, d[p] < d[n]: sorting reachable nodes by distance resolves each parent first. Equal distances between unrelated branches are harmless. Sources have zero distance and no predecessor; disconnected nodes never enter the sweep. A finite-distance node cannot have an unreachable predecessor in a valid Dijkstra forest.

`min_only=True` returns one multi-source predecessor forest. Ignoring `_sources` does not invalidate accumulation: following predecessors reaches the selected root. Equal-cost alternatives may select different roots, but the returned forest still specifies one path. The randomized checks independently followed each predecessor chain, summed original-direction time entries and checked the returned source identity; all 2,940 reachable cases agreed. This supports implementation consistency, not legal routing or deterministic tie policy.

Both builders reject zero, negative and non-finite weights; `add_travel_times` floors time at 0.1 seconds and adds nonnegative penalties. Zero edges therefore cannot arise through those builders. The public arrival function, however, validates only matrix shape. Explicit zero-cost entries supplied directly can invalidate its ordering assumption. Same-shaped matrices with missing time entries silently produce zero sparse lookups rather than an error.

Even strictly positive float64 weights do not guarantee strict *computed* distance increase. Executed counterexample: insert nodes `[n,p,d]`; add n->p with cost/time 0.1/0.1 and p->d with cost/time 1e16/0.1. Both computed costs round to 1e16. Stable sorting processes n before p, returning infinity for n although its real path takes 0.2 seconds. This passes builder validation. It is an API robustness defect, not evidence that ordinary Triangle costs encounter this magnitude. Use predecessor dependency traversal, or explicitly constrain numeric scale and reject invalid matrix inputs.

The paired builder chooses each node pair's cost-minimal edge once and derives both matrices from that same dictionary. Transposition preserves correspondence: `time_t[p,n]` refers to original edge n->p used by the reverse search. Parallel-edge identity is therefore correct within this reduction. Equal-cost parallels retain the first encountered edge, making reported time insertion-order dependent. Define a secondary time/key order if reproducibility matters.

Float64 matrices and a separate float64 output avoid obvious integer truncation or output aliasing; empty matrices are separately copied. The sweep sorts R reachable nodes in O(R log R), then performs R Python sparse scalar lookups, each with dispatch and a row-index search (potentially linear in row degree), rather than a vectorized gather. Include two transposes, Dijkstra and temporary arrays in cost accounting. The reported 3.89 seconds measures this combined stage, not reconstruction alone. Aligned CSR indices could support efficient edge-time gathering and an O(V+E) dependency walk.

## Findings

| id | severity | claim or file | issue | why it matters | recommended action | confidence |
|---|---|---|---|---|---|---|
| H1 | High | snap.py:136; layer.py | Cell route selection minimizes time after cost is discarded | Restricted shortcuts reappear; node and cell results disagree | Carry cost and time through partial-edge selection | High; executed |
| H2 | High | access.py; “not a through-route” | Finite per-edge penalties neither enforce endpoint-only access nor permission | Illegal transit and ineligible endpoints can be admitted | Specify eligibility and restricted-region traversal policy | High |
| H3 | High | PERMITTED_ACCESS; destination test | `destination` is completely unpenalised | Explicit no-through roads become ordinary shortcuts | Classify as restricted at minimum; test traversal versus endpoints | High; executed |
| H4 | High | Coverage narrative; phase0 §5 | Net finite-cell increase presented as recovered homes with legitimate access | Product availability improvement may contain false inclusions | Paired residential/access audit with gross transitions | High |
| H5 | High | access.py:50-74 | Incorrect specificity and inconsistent list aggregation | Roads can be wrongly blocked or restrictions erased | Resolve motorcar before motor_vehicle; aggregate conservatively | High; executed |
| M1 | Medium | “No penalty leak” | Smooth histogram cannot exclude additive offsets | Unsupported assurance of reporting correctness | Independent per-path time/cost oracle | High |
| M2 | Medium | Penalty magnitude and pruning | No sensitivity or component provenance audit | Reachability and route choice may depend on segmentation and pruning | Frozen-graph sweeps; node/edge/component diffs | High |
| M3 | Medium | “marginal cost ... unchanged”; intersections | Amortization hides repeated cost; real delay treated as preference | Misstates build cost and future timing semantics | Warm-category timing; put physical delays in time too | High |
| M4 | Medium | arrival API | Only shape checked; cost ties depend on insertion order | Invalid pairs or equal-cost paths silently change results | Validate correspondence; explicit tie policy | High |
| L1 | Low | Increasing-cost sweep | Float rounding can erase strict parent ordering | Valid extreme inputs incorrectly become unreachable | Traverse predecessor dependencies | High; executed; low production likelihood |

## Detailed notes

### H1 — Cost-aware nodes feed time-only snapping

The challenged promise is “the reported figure always belongs to the path actually chosen.” `cell_seconds_from_arrival` instead executes `network = np.minimum(via_end, via_start)`. `EdgeIndex` stores only directional times, not costs; same-geometry parallel edges also reduce by minimum **time**, independently of the CSR rule.

Executed fixture: S=(0,0), E=(100,0), D=(100,100). S<->E has time 10 and cost 460 per direction; S->D is open, time/cost 200; E->D is open, time/cost 10. To D, node reconstruction correctly gives T[S]=200 and T[E]=10. Yet snapping (0,0) to S-E returns 20: forward edge time 10 plus T[E]. At x=1 it returns 19.9; at the midpoint, 15. Thus an exact-node special case still loses to another candidate, and this is not merely a corner-rounding discrepancy.

Retain node costs alongside times and compare complete partial-edge **costs**, then report the selected candidate's time. Define treatment of entering an already occupied restricted edge or region. Test same-geometry parallels and exact-node authority. Also apply any advertised final time cutoff after on-edge and access additions: currently the cutoff is applied only to node T, so final cells can exceed it.

### H2 — Discouragement is advertised as prohibition

The section title says “restricted access is now reachable but not a through-route.” With drive penalty 450, a 60-second private cut-through costs 510 and beats a 600-second open detour. It is selected and reported as 60 seconds. If it is the only bridge between public roads it is also selected, regardless of whether either endpoint is private. The existing “only way” test positively requires that behavior without establishing endpoint eligibility.

Moreover, penalties are charged per simplified edge, not per entry into a restricted area. Split one 60-second private edge into two 30-second edges: cost rises from 510 to 960 without any physical change, potentially flipping route selection. This is not sufficient evidence of equivalent mainstream-router behavior; no local comparison of charging semantics was supplied.

Permission also depends on the traveler and destination. Residents may access their own driveway; that does not authorize a grocery trip through somebody else's private estate, or a home-search user's use of delivery/permit/agricultural access. Specify supported eligibility and how it applies to cell origins and category endpoints. A restricted-region state or endpoint exception can express stronger rules than one scalar penalty. If retaining a heuristic, label its limitations and audit its selected paths.

### H3 — Destination restriction is lost entirely

`test_destination_access_is_open` says: “our cost model expresses as open plus the through-routing penalty structure”. That structure is absent for this value. Executed classification gives OPEN and penalty 0. A ten-second destination-only connection beats a 200-second public detour exactly like an unrestricted road.

Move `destination` into restricted handling as an immediate consistency correction, including mode-specific tags. This will discourage, but still not prohibit, through traversal; H2 remains. The stated 550 edges quantify exposure, not affected journeys. Recompute routes and cell transitions around those edges and add both destination-endpoint and destination-through tests. The present test verifies the erroneous policy rather than the claimed behavior.

### H4 — Availability is not residential access validation

The challenged sentence is: “Those are overwhelmingly homes on driveways, which is the population a home-search product exists to serve”. No residential classification, entrance inspection or selected-path audit accompanies it. `access.py` similarly converts “92.8% ... within one restricted hop” into “driveways, in other words, which are exactly where people live.” One-hop adjacency establishes neither land use nor permission. Parking lots and industrial service networks qualify too.

The stored after-array independently confirms 255,547 finite cells and 202 within [115,125] seconds. Before coverage exists here as a rounded 72.7% report, not a preserved paired before-array. The arithmetic 0.046*330,502 = 15,203.092 explains “about 15,200”; rounded percentages alone leave roughly ±331 cells of uncertainty. Net gain is not the number newly reachable if some previously finite cells were lost.

Freeze extract, profile, destination selection and pruning; regenerate before/after arrays in separately authorized experiment work. Publish missing->finite, finite->missing and finite->finite time changes, snap displacement, destination changes and restricted-edge chains. Stratify a reproducible sample by restriction value, barrier, network size, urbanity and residential status. Use compatible residential/address/parcel data and actual entrance/field checks, including unsuccessful cells. Drive currently excludes `highway=track`, so agricultural/forestry tracks are not automatically a drive-specific recovery mechanism; qualifying service/residential ways and walk/bike tracks still warrant inspection.

The spurious fraction is **unknown**; assigning a percentage now would repeat the reporting error. Estimate it separately for newly finite cells and residential cells, with weighted uncertainty. Roughly 385 independent audited cases gives a worst-case binomial margin near five percentage points; spatial clustering reduces effective sample size. Validate final encoded boundaries against decision 12: median error <=10% of T, p90 <=20% of T, plus false inclusion/exclusion. Open-road spot checks cannot substitute.

### H5 — Mode overrides are only partly implemented

“Mode-specific tags override the generic one, as OSM intends” describes the easy case, not the actual hierarchy. `_mode_tag_values` selects `motor_vehicle` before `motorcar`; with `motor_vehicle=no, motorcar=yes`, the executed drive classification is FORBIDDEN despite the narrower passenger-car allowance. Reverse the values and the narrower prohibition can be ignored. The broader `vehicle` tag is not handled.

Generic lists test forbidden, then restricted. Specific lists instead test forbidden, then permitted, then restricted. Executed `foot=['yes','private']` becomes OPEN, whereas generic `access=['yes','private']` is RESTRICTED. Simplification can therefore wash a restricted segment into an unrestricted pedestrian connection. Resolve specificity before conservative within-tag aggregation, preserve required tags during ingestion/cache creation, and test both directions of every override and mixed list. The existing strict-list test covers only generic access.

## Claim-by-claim verdict

1. **Partly supported:** forest reconstruction is correct under stated numeric/matrix conditions; randomized checks pass. Add dependency traversal, validation, multiple-source and tie regressions; profile sparse lookup separately.
2. **Supported for the declared cost-selected route:** carrying the chosen edge's time is right. Reporting an unused minimum-time parallel would invent a path. A private 10-second/460-cost edge versus open 90-second/90-cost edge legitimately reports 90, surprising users expecting “fastest.” Define that contract and deterministic equal-cost behavior; fix snapping's conflicting reduction.
3. **Not supported:** destination is open with zero penalty. Introduce restricted treatment and endpoint-versus-through tests.
4. **Not supported by the histogram:** leakage shifts T to T+kP, generally producing a smooth translated mixture, not a spike at P. Establish with path sums as below.
5. **Partly supported:** after coverage verified; rounded net arithmetic agrees. Residential and legal recovery needs paired audits; no defensible spurious-rate estimate exists yet.
6. **Partly supported:** unchanged open-road times are a regression control. Include a surveyed/compatible-source residential cul-de-sac that requires restricted origin access, its reverse, and a tempting forbidden through shortcut. Exercise the cell-to-entrance pipeline.
7. **Not supported as calibrated:** 450/120 are explicit priors; the code describes only 450 as Valhalla's documented default and motivates smaller walk/bike values itself. No network verification was permitted. Sweep values and audit routes before adoption.
8. **Partly supported:** more surviving disconnected restricted networks can explain higher dropped counts, not their legitimacy or exact provenance. Establish matching mode, node universe and component diffs; use directed destination reachability where relevant.
9. **Partly supported:** both real own-graph callers migrated correctly; contraflow and symmetrisation preserve both weights. The single-CSR API remains permissive and cell construction remains inconsistent.
10. **Not supported as restrained reporting:** measured quantities again become unsupported causal/product assurances. Replace “Nothing else moved,” “no penalty reached a reported time,” the residential assertion and pruning explanation with bounded observations and named hypotheses.

## Tests that should exist and do not

- `test_two_weight_layer_preserves_node_cost_choice`: reproduce H1, including the exact node, edge interior, same-geometry parallels and final cutoff.
- `test_destination_endpoint_allowed_but_through_route_rejected`: separate access eligibility from soft preference; also test a detour longer than one penalty and a restricted-only public-to-public bridge.
- `test_restricted_penalty_is_segmentation_stable`: split the same physical restricted connection and assert the intended entry/region policy.
- `test_access_specificity_and_mixed_lists`: motorcar/motor_vehicle/vehicle hierarchy, permitted/restricted lists, and ingestion preservation.
- `test_two_weight_multisource_ties_and_disconnection`: multiple roots, shared frontiers, destination order, insertion order, unreachable nodes and explicit equal-cost/different-time choices. Existing two-weight tests use single destinations.
- `test_reconstruction_numeric_and_matrix_contract`: absorbed-positive-cost counterexample, zero-cost direct CSR input, identical shapes with mismatched sparsity, and source sentinels.
- `test_no_penalty_leak_path_oracle`: independently identify chosen edge keys and sum physical times along each forest path. Check reported time equals that sum and search cost equals time plus selected penalties for this profile. Include several restricted hops and nonzero open approach time. Extend through cell partial-edge costs, access legs and encoding. A dynamic-programming oracle is O(V+E) plus sampling/geometry; naive full chain tracing can be quadratic. One metro run is comparable to a layer build, synthetic tests milliseconds. No external API is needed.
- `test_recovered_residential_cells_and_pruning_transitions`: frozen legal entrances, barriers, disconnected but valid local destinations, one-way branches and restricted chains. A node-count guard alone cannot certify any of these.

## What is right

The cost/time separation fixes a real modeling omission. Original-direction arrival, positive-weight validation, paired parallel-edge selection, real-time cutoff at the node stage, and copied reverse-edge weights are valuable. Executed contraflow and walk symmetrisation probes preserved both weights.

A repository-wide Python search found `graph_to_csr` calls only in `test_arrival.py` and `test_snap_layer.py`, using unpenalised fixtures; `test_two_weight.py` merely imports it unused. Its intentional single-cost arrival demonstration reports 480 rather than 30 seconds. No remaining production caller was found: `g1_own_graph_layer.py` passes the pair, and `spotcheck_engines.py` invokes two-weight arrival. Default single-weight **time** would ignore penalties, whereas explicitly using **cost** would inflate reports; the blanket “single-weight ... reports inflated minutes” statement confuses these distinct failures.

The documented 0.07->3.89-second stage change is about 56x; graph load amortizes, this per-category stage does not. “Marginal cost ... unchanged in practice” needs warm-category measurements. Physical intersection delay must enter reported time as well as cost; only a preference penalty belongs exclusively in cost.

Admitting edges cannot increase weak component count on a fixed node universe; this pipeline removes isolates first, so newly surviving isolated private networks can increase counted components. The quoted older 1,685 count describes **drive**, while 3,046 is recorded for **walk**; that is not a controlled before/after component comparison. Largest-component pruning still discards valid local journeys and straight-line snapping can cross barriers. More weak connectivity is not more permission or directed reachability.

For sensitivity, paths cross where t1+k1P = t2+k2P. A 60-second private route overtakes a 600-second open detour below P=540 with one penalised edge; segmentation changes that boundary. With no cost cutoff, any finite penalty retains graph reachability, but selected real times, real-time cutoff and competing destinations can change finite-cell coverage. Sweep P=0,30,120,450,900 and larger values on a frozen graph; inspect restrictions, residential recovery, boundary errors and route changes. Choose policy from compatible observations and independently timed journeys, not restricted-source outputs. This preserves owner decision 17 and avoids repeating pass 5's unverified access and attribution claims.
