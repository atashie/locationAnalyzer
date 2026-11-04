# Adversarial review pass 11: acquisition, resolver fixes and re-measurements

Reviewed 2026-11-04. Report only; no production code or existing documentation was changed by this review. No Critical defect demonstrated. Four High, five Medium and one Low finding follow. The headline counts and the three-generation coverage chain reproduce. The concurrent acquisition guarantee, exact-name preservation, cross-source merge safeguards, and documentation completeness do not survive.

The prompt names `aead069`; the checkout was already at `7cad6c9` (the subsequent provenance re-verification commit). I reviewed the working files, including that correction. In particular, the current rebuilt artifact agrees with the provenance builder; the earlier 4,091-second mismatch is historical, not a current finding. Existing unrelated working-tree changes were preserved.

## Execution and measurement record

All Python commands ran from `v2/` using the existing environment, with this PowerShell prefix:

```powershell
$env:UV_CACHE_DIR = "$PWD/.uv-cache-review"
```

The default uv cache was inaccessible. `uv run --offline pytest -p no:cacheprovider --ignore=tests/test_acquire.py -rA --tb=short` returned **245 passed in 2.81s**. The ten acquisition tests hit sandbox permission errors when pytest created temporary directories. I then executed all ten original test functions against the existing writable `data/` directory, substituting only their temporary-directory location; **all ten passed**. These permission failures are not product defects. The acquisition tests do not cover the interleaving in H1.

Review probes are retained locally under gitignored `v2/data/pass11_review.py` and `v2/data/pass11_edges.py`. They exercise production functions without changing them. Executed commands:

```powershell
uv run --offline python data/pass11_review.py synthetic
uv run --offline python data/pass11_review.py real
uv run --offline python data/pass11_review.py measure
uv run --offline python data/pass11_edges.py
```

The independent measurement probe loads and prepares the real GraphML, constructs both CSRs and the edge index, calls `build_layer_surface`, then separately runs the sweep's bounded-node-time/final-cell-cutoff path. It reconstructs the narrow input by filtering the *current pinned routing-extent download* to the evaluation bbox, so the comparison holds release and graph fixed. Real output:

```text
COUNTS 107484 7425 550 113720 229
GRAPH 539814 1424670
FULL 510 {'OK': (256752, np.float64(77.68546)), 'OFF_NETWORK': (57541, np.float64(17.410182)), 'BEYOND_HORIZON': (16209, np.float64(4.904358))}
PIPELINE wide places 550 nodes 510 right 256752 0.7768546029978639 wrong 258684 0.7827002559742452
PIPELINE narrow places 452 nodes 417 right 253679 0.7675566259810833 wrong 255547 0.7732086341383714
ARTIFACT True 0.0002441211263430887
```

`COUNTS` means accepted Overture rows, raw OSM POIs, selected groceries, named index entries, distinct localities. The index entry count is before query-time corroboration, not a count of unique physical entities. The 1189-row difference from adding both raw source counts is expected loader filtering, not evidence that these rows were merged.

Thus **107,484 / 550 / 510 / 113,720 / 229**, **77.6855% OK**, **17.4102% OFF_NETWORK**, **4.9044% BEYOND_HORIZON**, and the adopted-120-second sweep's **77.69%, 256,752 reachable cells** all reproduce. One of the 550 places fails the 300 m node snap, leaving 549 snapped places and 510 distinct destination nodes. The full five-penalty sweep was not re-executed; its adopted-penalty result was independently computed, not merely read from the report.

The historical chain also survives a controlled reconstruction: **255,547 / 330,502 = 77.3209%** with the old cell call; **253,679 / 330,502 = 76.7557%** with the corrected cell call on the same 452 groceries; **256,752 / 330,502 = 77.6855%** with corrected routing-extent inputs. This is stronger evidence than comparing three rounded tables. It establishes the opposite directions of the two corrections for this build, not a general monotonicity theorem (M3).

## High findings

### H1 — Concurrent acquisitions can successfully commit the wrong release label

**Claim.** `acquire.py:14-20,71-103` ensures that new bytes never inherit a wrong label, and the two scripts can trust the returned file.

**Defect.** Removing the old state before replacement makes a *single writer's process interruption* safe, but there is no lock. Both writers share `raw.partial` (`:89`) and independently replace raw and write state (`:100-102`). A valid schedule is A replaces raw; B downloads and commits B; A writes state A. Both calls succeed, and the next A request trusts B's bytes. A common temporary filename also permits one downloader or exception cleanup to delete another's work.

**Executed reproduction.** `uv run --offline python data/pass11_edges.py` deterministically interposes a complete B acquisition just before A's `Path.write_text` of the state. This is an ordinary possible two-process interleaving, simulated without timing luck. Core probe:

```python
original = Path.write_text
def interleave(self, data, *args, **kwargs):
    if self == state_path(raw) and '"A"' in data:
        acquire(raw, B, downloader=writer('B-bytes'), log=lambda *a: None)
    return original(self, data, *args, **kwargs)
with patch.object(Path, 'write_text', interleave):
    acquire(raw, A, downloader=writer('A-bytes'), log=lambda *a: None)
```

Real output:

```text
RACE B-bytes {'type': 'place', 'release': 'A', 'bbox': 'bbox'}
REUSE_WRONG False B-bytes
```

The second line is `downloaded=False`, demonstrating actual reuse of the mislabeled bytes.

**Smallest correct fix.** Serialize the complete check/download/commit transaction with an interprocess lock keyed to raw, and use unique sibling temporary files. Also protect the consumer's read: `fetch_places.py:52` returns a mutable pathname which `partition_by_licence` later reads and labels with the caller's release. Releasing a writer lock before that read still permits another release to replace the file. Either hold the lock through consumption or return immutable files keyed by acquisition identity and publish an atomic pointer/manifest. Test both schedules, rather than only failed downloaders.

### H2 — Locality parsing and connective stripping destroy exact names and can resolve the wrong entity

**Claim.** Prefix/suffix locality handling and dropping connectives improve natural queries without losing the actual name (`resolve.py:232-258`).

**Defect.** The parser commits to one interpretation before scoring. A locality word can be part of the entity name. After splitting, `_strip_connectives` removes leading/trailing words belonging to the name too. There is no comparison with the intact query. This converts a correct exact-name winner into a confident wrong answer; the problem is not merely a lower cosmetic score.

**Executed reproduction.** The `synthetic` probe builds two Durham entries, `Durham Coffee` and `Coffee`. The full-name query gives:

```text
LOCALITY_NAME resolved [('Coffee', 1.0), ('Durham Coffee', 0.725)]
```

The `edges` probe builds a mall called `The Streets At Southpoint` and a separate office called `Streets At Southpoint`, both with Durham locality:

```text
CONNECTIVE_WINNER The Streets At Southpoint resolved [('mall', 1.0), ('other', 0.6375)]
CONNECTIVE_WINNER The Streets At Southpoint Durham resolved [('other', 1.0), ('mall', 0.8125)]
```

On the actual index the same parsing regression is visible without inventing an office:

```text
REAL The Streets At Southpoint Durham ambiguous 11 [('Dell@ Streets at Southpoint', 'a81e39cd-9343-4f7f-b79e-ab35f9b89dff', 'computer_wholesaler', 0.8125, ()), ('The Streets At Southpoint', '5d46537a-4a39-42fe-a206-335b9b0dfc89', 'shopping_mall', 0.8125, ()), ('The Streets at Southpoint', 'node/6507463159', 'platform', 0.8125, ()), ('Rowan The Streets at Southpoint', '52bee07f-c68a-4ea4-ae8a-3746bcb374ea', 'tattoo_and_piercing', 0.76, ())]
```

**Smallest correct fix.** Preserve both the original name tokens and plausible locality-stripped interpretations; preserve the unstripped name when removing an actual locality. Prefer a full exact entity-name explanation over a destructive parse. Remove words only from the verified boundary between name and locality, not indiscriminately from the remaining entity. Add the two wrong-winner fixtures above.

`Bank of America` and `Inn at the Park`, with locality prefixed or suffixed, survived my direct tests: their connectives are internal and are not stripped. `The Streets At Southpoint` did not. Scaling subset scores by token coverage is a defensible precision/recall tradeoff by itself; it does not repair the destructive parsing preceding it.

### H3 — The same-source merge prohibition is bypassed through one cross-source representative

**Claim.** The different-source requirement prevents two records from the same source collapsing into one confident answer (`resolve.py:368-390`).

**Defect.** `_merge_corroborating` checks only the *winning representative's* source (`:406-418`). An OSM representative can absorb any number of same-named nearby Overture records. After the first merge it still has source OSM, so the second Overture record passes the same test. The corroboration tuple records source names, not member identities or multiplicity. Two independent Overture places can disappear into one OSM anchor and make ambiguity vanish.

**Executed reproduction.** `synthetic` uses one OSM `Acme` and two Overture `Acme` records, the second 0.0001 degrees east; all are non-subsidiary and within 60 m:

```text
MANY_TO_ONE resolved 1
```

A direct pair of two OSM records is no longer mergeable, so the original direct-pair test passes while this cluster case fails.

**Smallest correct fix.** Retain cluster membership and enforce at most one member per source unless separately justified same-source deduplication has occurred. Treat one-to-many cross-source matches as unresolved associations rather than silently greedy merges. Include native IDs in corroboration so a displayed trust signal remains auditable.

### H4 — Duke Hospital still resolves confidently to the platform; a naming gap does not justify that outcome

**Claim.** Demoting reference features on ties closes the bus-platform hazard; if Duke still fails, ranking cannot fix the naming gap.

**Defect.** The implemented demotion is only a sorting key (`resolve.py:320-333`), not a confidence constraint. A platform with an exact score of 1.0 beats actual hospitals at 0.7833 and is auto-selected by `_decide`. The category is now present, so the resolver knows it selected a reference feature yet still presents that as the single answer to a hospital query.

**Executed reproduction.** `real` returned:

```text
REAL Duke Hospital resolved 35 [('Duke Hospital', 'node/6509747409', 'platform', 1.0, ()), ('Duke Hospital South', '7a29d122-6855-4a68-83e2-6942b74bef80', 'hospital', 0.7833, ()), ('Duke Raleigh Hospital', '6cf983b5-0c8b-4a4a-b194-0f7b7cfe0bb2', 'hospital', 0.7833, ()), ('Duke Regional Hospital', '2d5ef728-e6af-45a1-90d6-768d628ad4ce', 'hospital', 0.7833, ())]
```

`Duke University Hospital` is ambiguous and begins with imaging services and an emergency department, rather than a clean exact hospital record. I inspected the loaded hospital-category names: the precise main-hospital name is indeed missing as a clean exact candidate. This supports a data/name/alias gap. It does **not** establish that no ranking or decision change could prevent the confident wrong answer. Abstention and surfacing entity types are available even before the missing parent is acquired.

**Smallest correct fix.** Add a confidence/intent guard that surfaces reference-versus-parent uncertainty and identifies the platform explicitly; separately acquire/curate the verified hospital parent and aliases. Do not promote an arbitrary other Duke hospital merely because it has a medical category. Pure tie demotion also cannot establish that the user intended a parent rather than a station: this is a defensible ranking preference, not an intent proof.

## Medium findings

### M1 — Subsidiary classification repeats the cross-taxonomy overcorrection on real stations and fuel sites

**Claim.** Comparing subsidiary status instead of exact categories preserves valid corroboration across source vocabularies.

**Defect.** Status is derived by exact raw-category membership in `SUBSIDIARY_FEATURE_TYPES` (`resolve.py:86-97,313-317,388`). OSM `station` is subsidiary but Overture `train_station` is not; OSM `fuel` is subsidiary but Overture `gas_station` is not. Consequently the relaxed rule still blocks legitimate matches for the same reason equal-category matching did. `parking_lot`, `parking_garage` and `ev_charging_station` are additional unnormalized Overture categories present in the local download. A fuel station or car park can also be a standalone destination rather than a subsidiary borrowing a parent's name.

**Executed reproduction.** The `synthetic` probe returned `MERGE train_station False`, `MERGE parking_lot False`, and `MERGE gas_station False`. A real-index inspection using `build_metro_index` and resolving the names returned:

```text
Durham ambiguous [('28b9023b-9a09-4d73-bf22-d4f8696c004c', 'Durham', 'train_station', -78.9062126, 35.9976193, ()), ('node/7024572472', 'Durham', 'station', -78.906464, 35.9975323, ()), ...]
Sky Mart ambiguous [('way/608189623', 'Sky Mart', 'fuel', -79.00616628171224, 35.64296465, ()), ('b46f53e7-fb23-4371-b086-0a3540e578ce', 'Sky Mart', 'gas_station', -79.00615013, 35.64281704, ()), ...]
```

The near-identical coordinates show this is not merely a theoretical vocabulary example. The station tie also ranks the Overture record above OSM because reference demotion is inconsistent across vocabularies.

**Smallest correct fix.** Normalize source categories into semantic roles before comparing them. Distinguish a platform/entrance from a whole station, and a site's parking from a standalone parking facility. Keeping `entrance` or `parking` as a signal is defensible, but treating either as automatic evidence of a parent/child relationship is not. Also `from_osm:561-565` never reads the `entrance` tag, so listing `entrance` in the constant does not by itself recognize `entrance=yes` records.

### M2 — Sorting POIs does not make results independent of graph ordering

**Claim.** The selector ordering fix makes the spikes reproducible.

**Defect.** It makes the chosen *POI prefix* stable for an unchanged ID set. Graph tie behavior remains. `graph_to_cost_time_csr` uses `list(G.nodes())` and retains the first equal-cost parallel edge (`csr.py:53-64`). `EdgeIndex.from_graph` has the same strict-less-than retention rule (`snap.py:76-107`). Equal selection cost can carry different reported time. `arrival.py:52-56` already acknowledges that scipy equal-cost path selection is insertion-order dependent. `ox.nearest_nodes` callers likewise supply no stable node-ID tie rule. Sorting POIs cannot remove these dependencies.

**Executed reproduction.** `edges` builds two parallel 0→1 edges with cost 100 and times 10 and 90, then reverses their insertion order. Real output:

```text
PARALLEL_ORDER False 10.0
PARALLEL_ORDER True 90.0
```

**Smallest correct fix.** Scope the promise to stable POI selection on frozen inputs. If rebuild-independent output is required, specify canonical node ordering and explicit tie policies for parallel edges, paths and nearest-node/edge matches, and record native selected destination IDs in each spike artifact. Stable sorting cannot preserve “first three” across an enlarged ID set; new lower IDs can legitimately change the cohort. A comparison of the *same* three destinations needs frozen IDs.

This is a Medium reproducibility limitation, not evidence that the current frozen-GraphML rebuild is random. The repeated real rebuild matched the saved float32 artifact.

### M3 — “More destinations can only help reachability” is false for cost-selected reported-time coverage

**Claim.** `spotcheck-engines.md:858-859` says more destinations can only help reachability; `g1-routing.md:4-6` supersedes old figures “in the direction of more reachability.”

**Defect.** That theorem holds for existence of a path, minimum cost, or minimum time. This product selects the least-cost destination and reports that path's *time*, then applies a time horizon. Adding a cheaper but slower destination can move an OK cell to BEYOND_HORIZON. This is the known cost/time distinction applied to the new interpretation, not a new accusation that the two-weight policy is incorrectly implemented.

**Executed reproduction.** `edges` constructs 0→1 with time 60/cost 260, and 0→2 with time 180/cost 180:

```text
MORE_DESTINATIONS [1] 60.0
MORE_DESTINATIONS [1, 2] 180.0
```

At a 120-second horizon the origin is OK with destination 1 and beyond the horizon after adding destination 2. Both edges have positive weights and cost at least time. The claim is therefore false even under those model invariants.

**Smallest correct fix.** Say coverage *increased in this measurement*. Report the paired cell-transition matrix before claiming no cells worsened; an aggregate net gain of 3,073 cells is not the count of newly reachable cells unless losses are also measured. Reserve monotonicity for the quantity that actually has it. This does not invalidate the reproduced three-generation coverage chain.

### M4 — Evaluation-bbox building inputs and the published cell denominator have different footprints

**Claim.** `fetch_buildings.py:76-79`, `fetch_places.py:139-141` and `source-registry.md:9-10` describe the evaluation bbox as the published grid/coverage denominator, justifying evaluation-only building acquisition.

**Defect.** `GridSpec.from_bbox_wgs84` (`grid.py:40-61`) encloses the projected geographic box in an axis-aligned, rounded UTM rectangle. It does not mask cell centers outside the original geographic evaluation bbox. The production surface uses the whole rectangle as its denominator. Buildings are downloaded only for the geographic bbox. The planned building-weighted comparison therefore omits part of the area whose cells enter the area-weighted percentage.

**Executed reproduction.** This command used the actual grid and rebuilt array:

```powershell
@'
from locfinder.metros import TRIANGLE
import numpy as np
g=TRIANGLE.grid(); x,y=g.cell_centers_lonlat(); e=TRIANGLE.evaluation
inside=(x>=e.west)&(x<=e.east)&(y>=e.south)&(y<=e.north)
a=np.load('data/layers/own_triangle_grocery_walk.npy')
print('grid_total',inside.size,'outside_evaluation_bbox',int((~inside).sum()),'share',float((~inside).mean()))
print('finite_outside_eval',int((np.isfinite(a)&~inside).sum()),'coverage_masked_eval',float(np.isfinite(a)[inside].mean()),'whole_rectangle',float(np.isfinite(a).mean()))
'@ | uv run --offline python -
```

```text
grid_total 330502 outside_evaluation_bbox 15015 share 0.04543088997948575
finite_outside_eval 9811 coverage_masked_eval 0.7827295577947744 whole_rectangle 0.7768546029978639
```

**Smallest correct fix.** Choose and record one audit footprint. Either mask both diagnostics to the geographic evaluation polygon, or acquire buildings over the actual grid footprint and clip them to the same raster rectangle. Existing 77.6855% is correct for the raster rectangle; it must not silently be relabeled coverage of the geographic bbox. The building audit is still unimplemented, so this is a concrete input/denominator mismatch to resolve before publishing that comparison, not a fabricated failure of a nonexistent finished audit.

### M5 — Current narrative still quotes stale figures, and supersession notes contradict the new results

**Claim.** All destination-sensitive figures are annotated, including supersession notes.

**Defect and evidence.** Repository-wide `rg` searches for the old counts and coverage values found these unqualified current passages:

| Location | Stale or inaccurate claim | Required correction |
|---|---|---|
| `docs/plans/2026-11-03-phase1-plan.md:508-509` | S2.4 says 23.24% missing, 253,679 finite, “verified” | Current rectangle has 73,750 missing, 22.3145%; 256,752 finite. Label the old build or update. |
| same file `:552-564` | S2.5's current completion text still says 76.76%, 0.10 points, 55,694 changed nodes, 4,367/253,679 restricted-nearest cells | Mark as narrow-input historical results; newest table is 77.69%, 0.09 points, 73,444 changed nodes at 960 s, 4,420/256,752 restricted-nearest cells. |
| `docs/plans/layer-contract.md:464-467` | “76,823 = 23.2443% ... exactly the nodata share ... committed artifact”; three missing cells in four off-network | Current artifact has 73,750 missing, 22.3145%; off-network is 57,541/73,750 = about 78.0% of missing cells. This paragraph follows the new artifact-agreement note, so historical tense matters. |
| same file `:511-529` | Unmarked H2 bracket: 253,679 comparable, 23,468/9.25%, median 37.7 s, flips 202/325/340/256 | Newest G1 results are 256,752 comparable, 24,745/9.6377%, median 40.0 s, flips 205/329/363/265. |
| `docs/experiments/geocoding.md:36,60,84` | All three S2.1 runs still say 96,585 entries, 90,349 accepted rows, 177 localities, bounded by routing bbox | Mark these as the old partly evaluation-only index and the old resolver. They have dates but no supersession annotation; candidate outcomes and timings also depend on the fixes and expanded index. |
| `docs/experiments/g1-routing.md:2-9` | Says destination counts “below” are evaluation-extent and all dependent results superseded | The file now includes new 550-place/510-node runs at `:1265` and `:1302`. Bound the notice to historical sections. Structural mechanisms survive, but old numerical error distributions using a different destination cohort are not proven unaffected. |
| `docs/experiments/spotcheck-engines.md:846` | “Everything below” used 452 groceries | Below includes the new 510-destination run at `:1024`. Specify the exact historical subsection. |

The searches were `rg -n '90,349|96,585|177 local|452|417|76\.75|23\.24|77\.32|253,679|255,547|49,363|55,694' docs` and targeted reads around every relevant hit. Historical dated slice experiments such as `g6-poi-coverage.md` and `g3-rendering.md` remain valid as slice experiments; they are not automatically false because the Triangle changed. Earlier adversarial reports are historical evidence, not current benchmark claims.

**Smallest correct fix.** Add local input-generation labels to old benchmark passages, update current plan/contract summaries, and delimit notices so they do not supersede the very replacement results they point readers toward. The chain's numeric supersession is accurate; the scope and monotonicity wording are not.

## Low finding

### L1 — The artifact-equivalence check reports discrepancies but does not fail verification

**Claim.** `s0_status_on_real_layer.py:3-8,122` describes a check that the provenance path leaves committed seconds unchanged.

**Defect.** At `:123-137` the check computes and prints `finiteness_identical` and the maximum difference, but asserts neither, checks no expected float32 tolerance, and skips the comparison entirely if the file is absent. A mismatch therefore still leads to written results and successful process exit. The historical run retained at `g1-routing.md:1278` shows exactly this: `finiteness identical=False`, max difference 4091.769798 s, followed by the rest of the report. The new run repairs the measured artifact, but not this verification behavior.

**Executed evidence.** The current independent reproduction prints `ARTIFACT True 0.0002441211263430887`, so there is no current equivalence failure to report. Inspection of the complete comparison branch confirms it only assigns and prints results; its next actual assertion is the separate bracket check at `:152`.

**Smallest correct fix.** Make “verify existing artifact” a mode that requires an artifact, identical finiteness, matching shape and bounded finite-value error; fail with a clear generation-mismatch message otherwise. Keep an explicitly named exploratory comparison mode if nonfatal mismatches are useful during re-acquisition. Do not print schema validation PASS as if it also established artifact equivalence.

## Claims that survived, with limits of the attack

### Outcome before truncation and locality uniqueness

H3's truncation repair survives inspection and the resolver tests. There is one nonempty ranking decision path: `resolve.py:299-305` sorts, merges, decides on the full merged list and only then slices. `n_matched` is the full merged count. Early `not_found` returns do not decide among a truncated ranking. `limit=1` cannot by itself turn an ambiguous pair into a resolved result. H3 above is a *merge* defect preceding that otherwise-correct decision, not a hidden truncation path.

M1's leading tier is consistent with the documented margin: candidates less than `AMBIGUITY_MARGIN` below the leader participate; a runner-up at least that far behind is decisively separated. Counting all locality hits in this tier closes the third-candidate hole. It can decline to use a lower-scoring local answer when a nonlocal answer leads, or leave noisy local candidates ambiguous. That is conservative policy under the existing score-first design, not an independently demonstrated defect. H2's parsing can still feed the right logic the wrong scores.

The subset ratio penalizes short names with extra descriptive query words and can push them below `SCORE_FLOOR`. That is an expected recall cost of rejecting one-word subset false matches. I would not remove it or declare it defective without an intent/recall policy; the demonstrated wrong-entity regression is the irreversible locality/connective parse.

### Exact geometric boundary and deterministic node-coordinate representative

M3's tree-hit filter survives the boundary attack. `anchor.py:202-206` retains true point-to-line distances **<=** the cap; endpoint candidates at `:219-222` use the same inclusive condition. The `edges` probe's long horizontal road, with endpoints outside the cap, returned:

```text
BOUNDARY 149.99999999 node_too_far
BOUNDARY 150.0 node_too_far
BOUNDARY 150.00000001 off_network
```

Thus a road exactly 150 m away is present, and 150 m plus 10 nanometres is absent. The original diagonal-envelope false positive is eliminated; long edges with distant junctions remain correctly distinct from no nearby road.

`node_coordinates` (`anchor.py:108-125`) selects a lexicographic minimum over every endpoint observation of a node, which is independent of their iteration order. This is a stable representative of the index bucket. It is not a claim that every geometry endpoint is identical or an authoritative NetworkX node coordinate: expansion buckets have no unique exact geometric coordinate, and CSR itself stores no coordinates. The real own-graph layer uses the frozen graph's edges, not the new representative to move nodes. Do not extend the guarantee into graph-order-independent nearest-node/path selection (M2). My two-edge anchor-order probe selected the same node in both orders; it did not demonstrate a new anchor tie defect.

### Sequential acquisition interruption and filesystem placement

I injected `KeyboardInterrupt` precisely at state writing after raw replacement. Real output from `edges`:

```text
CRASH_AFTER_REPLACE A-bytes None
REDOWNLOADED True
```

This is safe failure: bytes exist but are unlabeled, and the next request downloads again. Killing the process between unlink and replace similarly leaves no trusted state. A partially written JSON document is rejected by `read_state`. There is an availability/re-download cost, not the old sequential mislabeling defect. No cross-filesystem move is inherent in this implementation: `raw.with_name(raw.name + '.partial')` creates a sibling of raw. `Path.replace` across filesystems is therefore not a new defect under the normal downloader contract. The current pair is not a transactional concurrency protocol (H1), nor a power-loss durability guarantee with fsync.

Both scripts really call the shared helper: `fetch_places.py:46-52` and `fetch_buildings.py:41,81-82`. Places require a pinned release and use the routing bbox; buildings use the evaluation bbox. The ten existing failure/reuse tests all passed when run against an accessible directory.

### Extent argument and buffer adequacy

The reason for acquiring places beyond the output footprint survives: anchors can be outside evaluation, and edge cells can use outside category destinations. The production grid did not grow with the place download. The layer selector uses Overture only, not Overture plus OSM, and destination node indices are put in a set; the extent change does not introduce cross-source destination double-counting. Query-time source merging has separate defects above.

For the **120-minute static walk model**, 1.4 m/s permits at most **10,080 m** of physical travel. Projecting a densified routing-bbox boundary and measuring its clearance from all four actual raster corners yielded **12,622.68 / 13,491.40 / 13,610.97 / 12,215.87 m**. Thus the relevant buffer is nearer 12–14 km around the padded raster corners, still comfortably beyond the walking horizon, including 200 m access and 300 m POI snap allowances. There is no demonstrated within-horizon walking truncation caused simply by a too-small destination bbox.

That argument assumes the model's lengths/geometries represent physical distance. It is not a general completeness proof for an **unbounded cost-selected search**: cheaper routes with more real time may extend beyond the walking horizon, and M3 shows that their selection can affect reported-time coverage. It also gives no comparable guarantee for faster bike/drive profiles, or for anchors arbitrarily near the *routing* boundary. Preserve the planned boundary sensitivity diagnostic rather than declaring the 15 km buffer sufficient for every mode and every selection policy. M4 separately corrects the claimed denominator footprint.

### OFF_NETWORK invariance is structural here, not a lucky equality

The interpretation is correct with its assumptions stated. `_snap_network` (`snap.py:138-141`) chooses the nearest geometry and computes access distance *before* consulting arrival times. `cell_arrival_with_provenance` (`:259-284`) defines `off = access_m > max_access_m`, then assigns OFF_NETWORK with precedence over endpoint reachability and horizon results. For a fixed grid, edge index, cap and nonempty valid destination set, OFF_NETWORK is therefore independent of destinations. An off-network cell cannot become OK merely by adding a closer destination node: its access distance remains over the cap. The exact equality of 57,541 cells is predicted by the implementation.

The nonempty-valid-set condition matters: `build_layer_surface:126-134` returns a uniform NO_DESTINATIONS/NO_ROUTABLE_DESTINATIONS failure for an empty routable set, bypassing geometric classification. Changing graph pruning, geometry, grid, cap or destination-specific graph construction can also change the off-network mask. Within the measured setup none of these changed. The contract's claim that a decomposition moving both statuses would automatically prove the split “not real” is too broad outside those controlled assumptions; it is useful as a fixed-input regression check.

The actual arithmetic supports a **net** gain of 3,073 OK cells and a matching net fall in BEYOND_HORIZON, with the off-network mask fixed. It does not by itself prove that every individual beyond-horizon transition was an improvement or that no formerly OK cell worsened. That stronger claim needs the paired transition check described in M3.
