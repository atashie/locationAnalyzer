# Adversarial review pass 20 — revision 6, plan revision 5, and T4

Reviewed branch `v2-rethink`, HEAD `5f9f001`, on 2026-11-06. Only this report was written; implementation and existing documents were left unchanged. Pre-existing workspace changes were left alone.

**T3 is not ready to become a frozen reference. T4 does not yet discharge its full obligation.** Revision 6 resolves the old continuum and E1 destination-removal questions, but its replacement identity/deduplication rules introduce numeric ambiguities. The oracle also violates the connector-cost rule. Eleven findings follow, most severe first.

## F1 — High — the oracle omits both connectors from objective 2's selection cost

**Location:** `v2/locfinder/measure/toy.py:358,364`; design §§2.1–2.2.

`journeys` adds `access_o` and `access_d` to `time_s`, but sets cost to `direct[1]` or `ec + pc + xc`. The own comparator must charge connectors to **both** objectives. Revision 6's time-only connector policy is for the independent engine; it does not repeal §2.2 for ours.

**Executed counterexample:** two edges from `(0,0)`: A to `(100,0)`, time/cost `10/10`; B to `(0,-100)`, time/cost `650/20`. Origin `(0,0)`; destinations A `(100,100)` and B `(0,-100)`. A attaches to `(100,0)` with a 100 m connector; B has none. Correct own costs are `10 + 100/1.26 = 89.3650793651` and `20`. Objective 2 must select B and report **650 s**. The oracle selects A at cost **10** and reports **89.3650793651 s**. **FAIL becomes PASS at ten minutes.** Objective 1 correctly selects A.

Every current case still passes: the connector-bearing tie case gives both alternatives identical connectors; the eligibility case has only one eligible destination and does not pin objective-2 cost. Thus omitting connector costs is already a wrong comparator that passes the corpus.

**Minimal fix:** add both connector charges to every own journey's cost. Add the unequal-connector, different-destination fixture above, including selected cost. **Implementation correction**, not a design amendment.

## F2 — High — position deduplication destroys distinct occurrences along an edge and has no specified representative

**Location:** design §2.2 candidate definition; `toy.py:228–237`.

An XY position is not an occurrence along a polyline. Equal rounded positions may have different arclengths, legal continuations and partial-edge weights. The design also supplies no representative rule for different positions falling in one rounded bucket; the oracle silently chooses the earliest fraction.

**Executed counterexample:** one one-way edge with geometry

```text
(-100,0), (0,0), (0,100), (100,100), (100,0), (0,0), (0,-100)
```

Length 600 m, time/cost 1,000. Origin `(0,0)`, destination `(0,-100)`. The origin has two distinct zero-distance occurrences, at arclengths **100 and 500 m**. Keeping both gives `100/600 × 1000 = 166.6666666667 s`. The rounded-XY key merges them, keeps the first and returns **833.3333333333 s**. **PASS becomes FAIL at ten minutes.** This is loss of 400 m of route choice despite zero spatial separation.

**A second executed consequence reaches the cap rule:** geometry `(-100,-.004),(100,-.004),(100,.004),(-100,.004)`, origin `(0,200)`. The horizontal segment projections are `(0,-.004)` and `(0,.004)`, at distances **200.004 and 199.996 m**. Both are in the tie band and both round to `(0,0)`. The oracle keeps the first, then drops it at the cap, returning **zero candidates**. Keeping the other representative gives an attached origin. Thus “each retained candidate independently inside its cap” does not resolve dedup-before-cap representative choice.

**Minimal fix:** identify attachment occurrences by along-edge position, retaining distinct arclengths even at equal XY; deduplicate adjacent-segment projections only when they represent the same occurrence. Explicitly define any quantization/representative policy and its ordering relative to caps. Spatial closeness alone cannot justify merging route choices. **Design amendment**, followed by implementation and fixtures. Shared vertices at the same arclength should still deduplicate; repeated positions at different arclengths should not.

## F3 — High — canonical directed identity cannot distinguish the two directions of a self-loop

**Location:** design §2.4 item 1; `toy.py:153–164`, `attachments` dedup key.

For `u == v`, swapping endpoints does nothing. Canonicalizing geometry against reversal then removes the only remaining direction information. The promised different directed identities are equal.

**Executed counterexample:** node 0 at `(0,0)`, with two one-way self-loop edges representing opposite traversals of the square `(0,0),(100,0),(100,100),(0,100),(0,0)`. Both have `osmid=(7,)`, time/cost 4,000. Origin `(10,0)`, destination `(0,10)`. The correct shorter journey is **200 s**, taking the reverse orientation through node 0. Both `ToyEdge.identity` values compare equal. With the forward edge first, attachment dedup discards the reverse and `evaluate` returns **3,800 s**. Reverse edge order and it returns **200.00000000000009 s**. **PASS/FAIL flips at ten minutes solely on insertion order.**

**Minimal fix:** retain an orientation discriminator for closed edges, derived consistently from their traversal geometry; use it in reverse pairing, attachment identity and route identity. Add this bidirectional-ring case and its reversed insertion order. **Design amendment** to identity, plus implementation correction.

## F4 — High — deduplication selects a duplicate identity before objective-specific ranking

**Location:** `toy.py:228–237`; design §§2.3–2.4 grouping/ranking contract.

Identity excludes time and cost. The oracle therefore merges same-identity records with different weights by input index, before either objective gets to compete. Different `osmid` parallel edges in the corpus do not exercise this.

**Executed counterexample:** two bidirectional edges `0→1`, geometry `(0,0),(100,0)`, `osmid=(7,)`, identical identity. Their time/cost pairs are **2000/2000** and **2/2**. Origin `(20,0)`, destination `(80,0)`. Both objectives should use the fast alternative for **1.2 s**. Slow-first returns **801.9999999999999 s**: reverse 20% of the slow attachment edge, traverse the fast edge, reverse 20% of the slow edge, `400 + 2 + 400`. Fast-first returns **1.2000000000000002 s**. **FAIL/PASS flips at ten minutes.** The erroneous result is not merely a provenance tie.

**Minimal fix:** retain weight alternatives until each objective's ranking has selected its representative, or reject conflicting duplicate records under an explicit input contract. Do not resolve them by `a.edge`. Preserving objective competition is an **implementation correction** under §§2.3–2.4; declaring these admissible inputs invalid would need a **design amendment**.

## F5 — Medium — a strict-cap comparator passes all 78 tests

**Location:** `conformance_cases.py` eligibility/origin-cap cases and `RULE_COVERAGE`; `test_conformance.py` coverage assertions.

I executed this fifth mutant, without changing a file:

```python
real = toy.attachments
toy.attachments = lambda g, p, *, cap_m: real(
    g, p, cap_m=math.nextafter(cap_m, -math.inf))
```

**All 78 tests pass.** This implements `< cap` instead of the required `<= cap`. Existing cases use 250/350 m and 250 m; the cap/band test also has no equality.

**Executed counterexample:** one 100 s/cost-100 edge `(0,0)→(100,0)`, origin `(0,0)`, destination `(100,300)`. Correct eligibility includes the destination, yielding `100 + 300/1.26 =` **338.0952380952 s**, a ten-minute **PASS**. The mutant excludes it and returns no finite journey. Interpreting that exhaustive result as no path gives **FAIL**; reporting an empty-eligible-set status still fails the required eligibility contract. At the origin's 200 m boundary the same mutant wrongly abstains instead of attaching.

**Minimal fix:** add exact 200/300 m and immediately adjacent values, with independently calculated eligibility, status and time. Add exact tie-band inclusion and same-position/direct-zero cases as well. **Test correction**, no amendment. A dictionary mapping rule names to existing names proves referential consistency, not boundary coverage.

## F6 — Medium — E1's selection gap and E2 now require two different own objective-2 values, but persistence supplies one

**Location:** design §§2.1, 2.6, 3 E2 (lines 501–502), 12 (lines 933–935); execution plan T6.

The intersection policy repairs E1 destination removal. It also means `objective2_own_s` for E2 is no longer generally objective 2 over E1's own eligible population. The documents still require the H2 selection-gap distribution and only one own objective-2 operand among their five values.

**Counterexample:** own eligible destinations A `(cost,time)=(1,10)` and B `(2,1000)`, zero connectors; the engine excludes A. Full-own objective 1 and objective 2 are **10 s**, so the H2 selection gap is **0 s**. On the intersection `{B}`, own objective 2 is **1,000 s**. If the engine also reports 1,000, E2 is **0 s**. Save only 10 as the own value and reconstructed E2 becomes **+990 s**, changing `|d|>60` from false to true. Save only 1,000 and reconstructed H2 becomes **990 s**, incorrectly attributing destination exclusion to own selection. No E1 PASS/FAIL should change; this defect corrupts the required diagnostics and regeneration.

**Minimal fix:** name and retain `objective2_own_full_s` and `objective2_own_intersection_s`, with separate destinations/costs/statuses; pair only the latter with the independent engine. H2 uses the former minus full-own objective 1. Amend the five-value payload to include both, or explicitly persist sufficient operands for both distributions. This is a **specification/persistence correction** implementing the already chosen populations, not a change to either estimand.

## F7 — Medium — exact float cost ties make allowed accumulation differences change the selected time by 999 seconds

**Location:** `toy.py:283,419`; design §§2.4 and 12's equivalent-implementation contract.

The issue is not that every near tie ought to be treated as equal. The design needs a numeric cost-comparison convention consistent with its allowance for floating accumulation changes. Exact float comparison alone does not provide that.

**Executed counterexample:** origin and destination lie halfway along unique, zero-time/zero-cost entry and exit edges. Between their endpoint nodes are two disjoint three-edge routes. Fast route costs **(.1,.2,.3)** and takes **1 s** total; slow route costs **(.3,.2,.1)** and takes **1,000 s**. All are one-way. Both routes contain the identical multiset of binary floating weights, so even their exact sums as binary rationals are equal. Ordinary left accumulation yields **0.6000000000000001** for the fast route and **0.6** for the slow. The oracle returns **1,000 s**; stable accurately summed costs (`math.fsum` gives **0.6** for both) tie and select **1 s** under the travel-time rule. **FAIL/PASS flips at ten minutes.** Time-comparison tolerance in T4 cannot repair a different cost-argmin.

For reproduction, use entry `(-100,0)→(0,0)`, exit `(300,0)→(400,0)`, fast intermediate nodes `(100,100),(200,100)`, slow intermediate nodes `(100,-100),(200,-100)`, origin `(-50,0)`, destination `(350,0)`. Entry/exit weights are zero; fast edge times are `1/3`, slow edge times `1000/3`.

**Minimal fix:** freeze cost arithmetic/comparison and test equal multisets under different accumulation orders. Options include a declared exact/fixed-point representation or a carefully specified comparison and tie policy; do not casually insert an unspecified epsilon. This requires a **design amendment to observable numeric/tie semantics**, then implementation changes. Under a policy explicitly freezing ordinary left accumulation the oracle's result could be the declared answer, but implementation reassociation could no longer be called equivalent.

## F8 — Medium — copied read-only arrays can be made writable again

**Location:** `frames.py:124–134`; `test_frames.py:201`; plan T2's identity claim.

The copied arrays own their storage. NumPy permits their owner to turn `WRITEABLE` back on.

**Executed counterexample:** build a one-cell frame C, then run:

```python
f.points.setflags(write=True)
f.points[0, 0] += 999
assert f.digest != f.recomputed_digest
```

This succeeds. It bypasses the advertised in-memory immutability without `object.__setattr__` or monkeypatching. The object now carries the same digest and a point moved **999 m**. If the frame was already saved, subsequent measurement can consume the moved point under its original identity. A boundary crossed by that move can turn an agreement into the second false inclusion of 500, changing **PASS to INCONCLUSIVE**.

The new writer recheck **does catch this before a later write**. Thus pass 19's unchecked serialization hole is repaired; claiming that a digest-mismatched Frame cannot exist, or that the arrays resist their own holder, remains false.

**Minimal fix:** expose views backed by immutable storage, or private storage plus defensive copies, and verify identity at measurement consumption. Protect IDs as well; object-dtype IDs need care because copying an object array does not freeze its referents. Add a `setflags` test. **Implementation correction**. Ordinary readers, NumPy indexing, and the current pandas writer do not need writable input arrays; no legitimate caller in the reviewed code requires mutation.

## F9 — Medium — the oracle's provenance ranking is not §2.4's ranking

**Location:** `toy.py:257–261,355–364`; case/result destination representations.

`rank_key` uses travel time then `repr` of routes. It omits destination ID and the declared edge ranking keys. Endpoint partial traversals are omitted from endpoint/network journeys' `route`, although direct journeys include their edge. The API accepts coordinate lists, not destination IDs, so it cannot implement revision 6's new identity tie rule.

**Concrete counterexamples:**

* Two destinations with IDs `z` and `a` at the same coordinate, each reached at cost/time **1/1** by the same route: §2.4 requires **a** regardless of input order. The oracle cannot receive these IDs; it returns the first list position when route keys tie. Reordering the destinations changes the selected real identity.
* At equal cost/time **1/1**, compare route identities beginning with node pairs **(2,3)** and **(10,11)**, all other fields equal. Numeric element-wise identity order puts **2 before 10**; `repr` puts **'10' before '2'**. An executed pair of `Journey` objects selects the latter. It also puts route order before destination identity.

No numeric PASS/FAIL flips in these equal-time examples; the required selected identity/path provenance is wrong. This is precisely the class of defect revision 6 says it repaired, and T4 does not exercise it.

**Minimal fix:** carry destination IDs and full directed partial traversals, and implement a typed structured rank consistent with the normative ordering. Test actual selected identities and destination reordering, not only times and candidate counts. **Implementation correction**. Define how edge-level keys lift to a multi-edge journey if that is meant to precede destination ID; the current prose does not spell out that lift, so that portion needs a **design clarification/amendment** before freezing a route-provenance order.

## F10 — Medium — the plan's repaired T6 list still names the wrong five numeric values

**Location:** execution plan T6, first added payload bullet, versus design §12.

The plan now lists objective 1, objective 2 own, independent selected time and **both selected costs** as “all five numeric values.” Design §12's five are objective 1, objective 2 own, **float product**, **decoded encoded product**, and independent objective 2. The corrective edit omitted both product numbers.

**Counterexample:** two bundles have objective 1/own objective 2/independent time all **100 s**, identical selected costs and four product PASS outcomes. In one, the float/decoded product pair is **100/120 s**; in the other it is **200/240 s**. Both satisfy the plan's numeric list, but snapping/surface deviation from objective 1 is **0 versus 100 s**, and encoding deviation is **20 versus 40 s**. Those distributions cannot be regenerated after source rasters disappear. No current threshold PASS/FAIL differs; the report-regeneration acceptance check must reject the incomplete bundles.

**Minimal fix:** list both product operands explicitly as well as selected costs and F6's two own objective-2 values. Make T6's regeneration test remove each required field in turn. **Plan correction**, no amendment to measured quantities.

## F11 — Medium — the finite-result branch accepts non-finite results as definitive verdicts

**Location:** `conformance.py:91–92`; design §2.5's “a finite time was found.”

The implementation tests `time_s is not None`, not finiteness. Infinity is a normal representation of routing non-results in this repository and is explicitly discussed in §2.5.

**Executed counterexample:** `threshold_s=600`, `search_bounded=True`, `exhausted=False`, no time bound. Passing `time_s=inf` or `nan` returns **FAIL**, even though the search has established neither a finite route nor a sound bound; correct output is **UNRESOLVED** (or reject the invalid input for normalization). `-inf` returns **PASS**, although no finite route was supplied. With a product PASS, the `inf` case changes a potential E1b into an identified E1b. At `n=500`, ten such cases change the gate from **INCONCLUSIVE** (`k=0,u=10`) to **FAIL** (`k=10,u=0`). No actual point FAIL was established.

**Minimal fix:** validate a supplied time as finite and nonnegative, or normalize non-results before the finite branch, preserving termination reason and bounds. Add `inf`, `nan` and negative tests. **Implementation correction**, no amendment. The four branches otherwise implement the stated rule on valid, normalized inputs.

## Independent audit of the twelve hand derivations

I recalculated each named expected time without using T3. None of the twelve pinned time values is arithmetically wrong. That does not validate unpinned fields or unexercised policies.

| Case | Independent calculation/result |
|---|---|
| Objective views | `0.5×1+1 = 1.5`; cost-selected `0.5×10+10 = 15`; hybrid values 10.5 and 6 are plausible wrong view pairings. |
| Attachment tie | `100+2/1.26 = 101.5873015873`; rejected road `1000+2/1.26 = 1001.5873015873`. Correct selected cost also includes `2/1.26`, but it is unpinned. |
| Cost tie ranks by time | Both cost 50; time 1 beats 10. Only the first tie key is separated. |
| Penalty apportioned | `0.01×121 = 1.21`, time `0.01×1000 = 10`; open alternative 5. Objective 1 is 5, objective 2 is 10. Entry-charge rejection 5 is reachable. |
| One-way with return | `0.2×100+100+100+0.2×100 = 240`; illegal direct reverse is 60. The slow-return correction separates the mutant. |
| One-way without return | No permitted reverse or endpoint return; no journey, but one origin attachment. |
| Same-edge competition | `100+1+100 = 201 < 800`; two incident origin edges. The recorded hand candidate-count correction is accurate. |
| Cost argmin then time | Cost 10 selects time 10; objective 1 selects time 1 on the cost-100 route. |
| Cheaper destination raises objective 2 | New cost 5 selects time 100 instead of cost/time 10/10; objective 1 remains 10. |
| Destination eligibility | 250 eligible, 350 ineligible; `50+250/1.26 = 248.4126984127`. No objective-2 time/cost is pinned. |
| Off-network origin | 250 exceeds 200; zero origin candidates; destination remains eligible. If global nearest distance is retained, bound `250/1.4 = 178.5714285714 < 600`, hence unresolved at ten minutes. |
| Multi-segment polyline | Length 200, destination arclength 150; `0.75×200 = 150`. Within-segment fraction error gives 100. |

The last case's prose says 100 versus 150 differs at **T=2.5 minutes**. Both times actually **PASS** at that inclusive threshold. They differ at **T=2 minutes** (120 s). This is a minor derivation/verdict annotation error, not a wrong expected value; correct the threshold. Neither is a published threshold, so the case separates arithmetic rather than a current published verdict.

The “ineligible as unreachable” rejection in the eligibility case is not numerically separating: a minimum over `{248.4127, inf}` is still 248.4127. It is separated only if the mutant also misreports the explicitly checked eligible/ineligible identities. Do not count it as a time-minimum mutant killed by that case.

`RULE_COVERAGE` establishes that its listed names exist. It does not establish every §2 rule is separated: F1–F5 and F9 exhibit missing dimensions. `RULES_TESTED_WITHOUT_A_GRAPH`'s identity tests prove reversal for distinct endpoints, not self-loops, reverse pairing behavior or the complete ranking. Recording one known omission does not prove exactly one semantic gap. Synthetic observed correlation positions can test connector arithmetic without inventing a live engine's behavior; live verification is a separate T6 obligation.

## What survives the attacks

* **Simple paths:** the cycle-excision argument is sound for the two numeric objectives on this nonnegative, path-independent model. Fix origin/destination attachments and their entry/exit choices first. Removing a repeated-node cycle from the middle path changes neither partial edge nor connector. For objective 2, a positive-cost cycle worsens cost; a zero-cost positive-time cycle loses the time tie. Stopping at the goal discards no better numeric result. This does not establish a lexicographically preferred provenance among arbitrary zero-cost/zero-time walks; freeze simple-route provenance if that is required.
* **Entry/exit enumeration:** all four directional combinations exist for bidirectional edges; the flags correctly remove forbidden options. The same-edge direct candidate competes with leave-and-return journeys, and the corrected 240 s one-way case exercises that return. Duplicate enumeration is harmless for minima. Missing/incorrect candidates and route identities, rather than simple-path pruning, cause the defects above.
* **Ordinary geometry cases:** a zero-length segment has a well-defined nearest XY and the oracle avoids division by zero; an adjacent shared vertex has one arclength occurrence. Coincident edges with different normalized `osmid` identities properly survive as separate alternatives. A straight segment has one projection; collinear consecutive segments do not by themselves create a continuum of equal nearest points. Self-intersections, closed-ring direction and rounded-position buckets require F2–F4.
* **Per-segment versus exact per-geometry minima:** revision 6 really does choose different answers. On one one-way L edge `(0,0),(100,0),(100,100)` of time/cost 1,200, origin `(99.994,.005)`, destination `(100,100)`, the segment candidates have residuals .005 and .006. The chosen segment rule returns **599.9747619048 s**; exact per-geometry nearest-only gives **600.0399682540 s**. **PASS versus FAIL at ten minutes.** This is evidence of the declared amendment's consequence, not a demand to reverse that deliberate choice.
* **Cap and OFF_NETWORK bounds:** a global minimum of 200.5 m leaves no in-cap attachment; retain that global minimum separately and use `200.5/1.4 = 143.2142857143 s` for the stated bound. `attachments()`'s empty tuple does not retain it. T3 must not substitute the 200 m cap or an arbitrary rejected candidate. An empty graph has no finite nearest distance: use an explicit reason/bound absence, not an invented access distance. For example 840.5/1.4 is 600.3571 and proves failure at ten minutes; 200/1.4 does not. Make the distance-producing contract explicit when implementing T3.
* **E2 policy:** §2.6 now explicitly includes selection-policy and attachment disagreement. Its asymmetry is coherent as that estimand: ours charges connectors in cost, the engine does not. With identical on-road A `10/10`, residual 100 m, and B `20/20`, residual zero, ours selects B for 20 s and the engine selects A for 89.3651 s; E2 is **+69.3651 s** despite identical on-road pairs. Report it as selection-policy disagreement, as the amended label requires. The earlier phrase about measuring only engine disagreement should not override that explicit definition. Costs on the independent side must stay unscaled by seconds.
* **Exterior and E0:** the UNKNOWN exterior rule applies equally to structure centroids. If one of two centroids is exterior and the covered centroid is PASS, `E0_B=1/2`; a 20% exterior-area example yields `E0_C=20%`. Report exterior as an exclusive export reason, alongside model reasons; do not add its total twice to UNKNOWN or assign it a BEYOND_HORIZON/OFF_NETWORK reason. The current abstract cross-tab does not double-count it. Partial export defects still need the run-failure handling §7 promises where they constitute invalid publication.
* **§7 accounting:** `CROSS_TAB`, `classify` and `tally` match all nine declared cells. UNKNOWN contributes to neither directional `k` nor `u`; full-frame `n` is retained. A definitive comparator verdict at UNKNOWN is unwarranted abstention regardless of its direction. No finding on this table.
* **Typed identity ordering:** heterogeneous fields at different tuple positions are not themselves a comparison error. With integer node/OSM IDs, numeric coordinate pairs and consistent normalization, element-wise comparison compares like-typed fields. `repr` in F9 is the implementation defect. Any broader node/OSM type domain needs normalization before comparison.
* **Statistics:** pass-19 F3's calibration/tolerance repair survives: the independent inversion fixtures now cover .90/.95/.99 with `rel=0`, and forwarding to acceptance/tolerated counts is exercised. On the accepted `[.5,1)` domain the CP upper bound dominates the sample proportion, keeping acceptance PASS and FAIL disjoint. A lower-confidence one-sided interval is still mathematically a confidence bound; the reason to restrict this API is the declared acceptance-branch invariant, not that such bounds cease to exist. Applying the same restriction to a central two-sided percentile interval unnecessarily rejects a valid 30% interval (`0..100` would give **[35,65]**), but this is documented and does not affect frozen 95% S3 output. No certification defect follows from that convenience restriction.
* **Frames:** stable sorting now runs on cached and uncached builder paths; duplicate IDs/shapes/non-finite points are checked. Digest bytes include kind/CRS, canonical float bytes and full length-delimited IDs. Construction verification and pre-write verification are effective checks, subject to F8's in-memory limitation. The tracked build script actually checks both production counts and passes the expected retained population count to the builder. Runtime/grid metadata and saved-point authority repair the cross-version redraw overstatement. The population-count guard remains opt-in, so a production call must pass it.

## T3 readiness and T4 obligation

**Do not start a purportedly frozen T3 yet.** Ordinary development and the unambiguous fixture subset can proceed. Old pass-19 F1's continuum is now finite, and old F2's engine-dependent E1 population is settled. But new §2.2 still admits different representatives/route occurrences (F2); §2.4 needs closed-loop directed identity (F3), deterministic handling of same-identity weight alternatives (F4), and a cost arithmetic convention (F7). Its edge-to-whole-journey provenance ranking also needs an explicit lift (F9). §2.6's set policy is defined, but its distinct own operands must be named and persisted (F6). These are the remaining §2 rules/contracts for which implementations can currently produce different numeric or selected-provenance answers. A missing-graph/global-distance status contract should be explicit rather than inferred from an empty attachment list.

**Hand derivations plus an independently implemented exhaustive enumerator are adequate evidence of independence from T3 for the fields they actually derive.** Their algorithms and imports can be inspected; the corrected incident-edge count is useful evidence of separate calculations. It is not adequate evidence that all of §2 conforms: the oracle's cost defect survived all twelve cases, two pin only objective 1 despite finite objective 2, and exact boundaries are absent. Independence is necessary, not a proof of correctness or coverage.

Strengthen T4 with the worked counterexamples above, explicit full/intersection selection cases, boundary fixtures without numerical tolerance at equality, and assertions of complete selected costs/IDs/directed partial routes. For cost arithmetic, derive expected ties from exact rational sums independently of the floating oracle. Test each claimed rule with a mutant that actually changes that rule's observable result. Do not reject all threshold-equality cases: use exact verdict assertions there, alongside tolerances only on safely separated cases.

## Build record: corrections and remaining overstatements

The five pass-19 corrections are materially present: tighter independent calibration, sorting on both builder paths, a tracked count-checking script, explicit saved-point/runtime/grid provenance, and complementary rather than independent distributional guards. F8 qualifies the new immutability claim; the writer check is a real improvement.

New or remaining overstatements:

1. **“T4 done” / eight of nine rules covered / exactly one knowingly untested rule:** the surviving strict-cap mutant and F1–F4/F9 refute semantic completeness. The coverage test only inspects the hand-maintained map.
2. **“Every journey”** is too strong after attachment dedup discards occurrences and directions. Simple paths suffice numerically only after the correct candidate/identity domain is established.
3. **“No more design work” pending review:** revision 6's old blockers are addressed, but F2/F3/F7 expose new design decisions that must precede a freeze.
4. **The plan's payload repair:** F10 still omits required product operands, and F6 requires another own objective-2 operand. Recording selected costs does not replace them.
5. **Tolerance claims:** `conformance.py` calls 1e-9 roughly 500 times 1.42e-14; the ratio is actually about **70,423** (the build record's 70,000 is right). The test proves safety of the oracle-versus-hand *time comparison* for the listed thresholds, not cost-argmin stability (F7), cap equality or destination provenance. The edge-order test also still uses `pytest.approx(..., abs=...)` with default relative tolerance; on 1,000 s that permits roughly .001 s, not 1e-9. Current hand checks are stricter, so this is not a separate current numeric failure.

## Executed verification and limitations

* Baseline `test_stats.py` plus `test_conformance.py`: **218 passed** (140 + 78).
* `test_frames.py` excluding the five tests requiring `tmp_path`: **25 passed, 5 deselected**.
* Attempting all 248 tests produced five temporary-directory setup errors and a cleanup `PermissionError` under `C:/Users/arikt/AppData/Local/Temp/codex-pass20-pytest`. These are environmental failures, not evidence that the corresponding frame computations fail. I did not alter repository code or create an in-repository temporary directory to bypass the read-only instruction.
* In-memory strict-cap mutant: **78 passed**. The connector, repeated-position, cap dedup, self-loop, duplicate-weight, cost-order, rank and non-finite counterexamples above were executed directly using the existing venv. Mutations affected only the subprocess's imported functions/objects.

The build record's 576-test result may accurately describe its build environment; this review did not rerun unrelated tests or remeasure the production graph, live engine responses, all structure centroids or saved development-frame equality. It does not certify those carried empirical claims anew.
