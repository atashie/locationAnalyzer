# Pass 9: adversarial review of S1's expansion primitive

Reviewed `c04e34d`, 2026-11-04. Report only; no implementation, tests, plan, or experiment results changed. No Critical finding established. Four High and four Medium findings follow. The published walk row reproduces; the claim of exact reconstruction does not survive.

All Python commands ran from `v2/`, with PowerShell environment settings:

```powershell
$env:UV_CACHE_DIR = "$PWD/.uv-cache"
$env:LOCFINDER_METRO = 'slice'
```

Valhalla's local `/status` returned HTTP 200. `uv run pytest -q` completed successfully: 72 + 72 + 45 = **189 tests passed**. It emitted a warning that pytest could not write its cache. A passing suite does not cover the counterexamples below.

## H1 — High: origin proximity reverses real roots and deletes legal directions

**Claim.** Roots are oriented authoritatively by the supplied origins, and direction marking is faithful. Sources: `v2/locfinder/traveltime/expansion.py:96`, `:109`, `:219`, `:253`; plan `docs/plans/2026-11-03-phase1-plan.md:150`.

**Defect.** A search origin inside a road is not either endpoint of its full serialized geometry. Both opposing root features cover that same road, with opposite coordinate order and different *partial* durations. Choosing the endpoint nearest the POI selects the same physical near endpoint for both features. After re-expression into the first record's coordinate order, both can be marked in the **same** travel direction. Thus merging loses a direction even though both directed features were supplied. It also puts zero at a real vertex that requires positive travel time to the destination, and interpolates a partial duration over a full road.

This is present on the real payload, not just a hypothetical concern. Reproduction commands are in A2–A3. Actual output:

```text
features 476072 roots 6 targets [(35.84490631999999, -79.08932463), (35.86684, -79.02845), (35.852677899999996, -79.02578838)]
ROOT 2957157889946 dur 2 origin_near_start False succ_near_start True
ROOT 2785963177882 dur 3 origin_near_start False succ_near_start True
ROOT 2732208977818 dur 3 origin_near_start True succ_near_start True
ROOT 2956990117786 dur 3 origin_near_start True succ_near_start True
ROOT 2731839879066 dur 5 origin_near_start None succ_near_start None
ROOT 2785795405722 dur 5 origin_near_start True succ_near_start True
```

The first two roots disagree with the independently identifiable successor endpoint. Their opposing roots are also present. Reading the merged records gave:

```text
root 2957157889946 index 0 fwd/rev 2.0 inf T endpoints 2.0 0.0
root 2956990117786 index 0 fwd/rev 2.0 inf T endpoints 2.0 0.0
root 2785963177882 index 1 fwd/rev 3.0 inf T endpoints 3.0 0.0
root 2785795405722 index 1 fwd/rev 3.0 inf T endpoints 3.0 0.0
```

All three zero nodes were queried through the matrix:

```text
zero node matrix times [2.0, 3.0, 5.0]
```

The metre-coordinate counterexample in A1 also returned `3.999999999999999` seconds **at the destination**, and `0.0` at the wrong real endpoint.

**Smallest correct fix.** Treat roots as partial edges ending at a correlated destination anchor. Obtain the directed edge/node identities and correlated point/fraction, retain each root's actual settled endpoint, and split or special-case interpolation at that anchor. Do not override an unambiguous successor signal with proximity to an off-road POI. Merely swapping the root-priority order fixes neither the missing virtual anchor nor the partial-duration interpolation.

## H2 — High: the physical-edge key already has non-pair collisions on the real payload

**Claim.** Canonical rounded coordinates identify one physical road and merging preserves its two directions. Sources: `expansion.py:85`, `:241`, `:256`; tests `v2/tests/test_expansion.py:201`, `:270`.

**Defect.** Coordinates identify a shape, not a topological edge or its opposing edge. The adapter never verifies that the members of a group are actual opposites or repeated labels for one edge. Independently minimizing traversal times and endpoint labels then discards the identities needed to distinguish overlapping roads, hierarchy representations, or different turn states.

A2's live collision audit produced:

```text
unique edge ids 476072 duplicates 0 groups >2 519 max group 5
GROUP [({'duration': 302, 'distance': 2341, 'edge_id': 2732477413274, 'pred_edge_id': 2730430592922}, [[-79.030831, 35.866967], [-79.030809, 35.866779]]), ({'duration': 307, 'distance': 2349, 'edge_id': 2732510967706, 'pred_edge_id': 2730430592922}, [[-79.030831, 35.866967], [-79.030809, 35.866779]]), ({'duration': 316, 'distance': 2371, 'edge_id': 2732578076570, 'pred_edge_id': 2732477413274}, [[-79.030809, 35.866779], [-79.030831, 35.866967]]), ({'duration': 316, 'distance': 2371, 'edge_id': 2732544522138, 'pred_edge_id': 2732510967706}, [[-79.030809, 35.866779], [-79.030831, 35.866967]])]
```

Four distinct directed IDs with distinct labels have become one record. This proves the implementation's unverified “one shape = one opposing pair” assumption is exercised. It does **not** by itself prove that those particular four IDs represent different streets or that this group produces an illegal journey; identifying their topology requires tile attribution. That distinction is important.

A1 establishes the API-level failures independently: different edge IDs with coincident geometry collapse; the same line with an extra collinear vertex gets a different key; two different shapes separated by `0.00000004` coordinate units get the same 7-dp key. The tiny rounding example is a synthetic stress test, not evidence of that precision difference in this Valhalla payload, whose inspected coordinates have six decimal places.

**Smallest correct fix.** Pair using authoritative opposing-edge IDs, preserve endpoint node identities/levels, and use geometry as a consistency check. Until that metadata is available, detect/report groups with excess distinct IDs and refuse to claim identity or exactness. Adding a tolerance or removing collinear vertices alone makes the collision problem worse. The test at `test_expansion.py:270` explicitly blesses merging different IDs in one direction without establishing that they are one road.

## H3 — High: reversed loops lose their opposite direction; short edges lose endpoint times

**Claim.** `same_order` handles reversed storage and `_NODE_SNAP_M = 0.5` merges node identities safely. Sources: `expansion.py:69`, `:81`, `:246`, `:253`, `:304`.

**Defect.** For a closed loop, both stored directions start at the same endpoint. The endpoint-only `same_order` test therefore always returns true. A loop and its reverse are merged into a single direction; the missing direction can change which way an interior point can leave the loop. Comparing the canonical/full coordinate sequence would distinguish the non-palindromic loop in the reproduction.

Separately, `_node_key` is a square quantization bucket, not a 0.5 m distance test or a graph identity. It merges endpoints almost 0.707 m apart and can separate endpoints only 0.02 m apart. If a short road's endpoints land in one bucket, `T` loses the larger endpoint label. `snap.py:156` then returns that shared smaller label at the far endpoint.

Executed A1 output:

```text
reversed loop: start=end True fwd= inf rev= 150.0
short edge: start=end True far endpoint time= 100.0 expected 200
node key 2cm apart: (0, 0) (1, 0) node key .69m apart: (0, 0) (0, 0)
```

There were **zero exact closed geometries** in this live drive response, so the loop defect is a constructed counterexample, not a measured drive incidence. The live index did merge two node buckets containing distinct coordinates; maximum coordinate spread was `0.37741125959301497` m. None of the 240 sampled drive nodes belonged to those two buckets. This particular sample's +50 s median therefore cannot be blamed on that coordinate conflation.

**Smallest correct fix.** Compare entire forward/reverse sequences when re-expressing geometry order; explicitly handle palindromic/closed degenerate cases where geometry cannot establish orientation. Use graph node IDs for connectivity. If unavailable, do not silently conflate a positive-length edge's endpoints; surface ambiguous identities instead. A Euclidean clustering implementation would correct the misleading distance description but would still conflate distinct co-located graph nodes.

## H4 — High: median agreement is presented as proof of exactness, despite measured large errors

**Claim.** “The reconstruction machinery is provably exact,” the whole walk residual is access, and the drive gap cannot be the adapter. Sources: plan `:194`, `:206`; `docs/experiments/g1-routing.md:910`, `:951`; `g1_expansion_primitive.py:327`.

**Defect.** A near-zero signed median neither bounds per-point error nor proves the absence of adapter defects. The walk node artifact itself reports p90 absolute error **6.1 s**, maximum **203 s**, and shares later/earlier by more than one second of **16.7% / 12.1%**. The reproduction below found a maximum cell residual of **478.4 s after removing our access term**. Calling the reconstruction exact, or saying that the *entire* residual is access, contradicts those results and H1–H3.

A4's live paired walk reproduction returned:

```text
walk old: 8909 n 195 median/p90/signed 69.36603526080216 271.2639266598147 66.39457714725086
walk new n 181 signed 28.67202060856232 access/bias 0.9638972817173409 after subtract median/abs/p90/max 0.04718512762735827 1.5413826877975225 10.617995632089787 478.3833640816788
```

The generated drive prose is additionally mode-independent: after correctly printing an on-network **FAIL (+50.0 s)** it asserts “the remaining +82 s is our own access-leg model.” That is an unconditional template error at `g1_expansion_primitive.py:327`, preserved in `g1-routing.md:951`. The drive access/bias ratio is **0.26**, not approximately one.

**Smallest correct fix.** Replace “exact/provably exact” with the measured conditional error distribution and sample scope; retain the tail errors and root failures as unresolved. Generate mode/result-dependent conclusions. Keep both total and on-network pass criteria explicit; a failed construction criterion does not become a pass by changing its interpretation after measurement.

## M1 — Medium: the reported “merging only” experiment changes the request and node labels

**Claim.** The 8.78% figure isolates removal of duplicate geometries. Sources: `s1_expansion_directions.py:235`, `:239`, `:266`; plan `:163`.

**Defect.** Index 0 calls the **new, already-merging** adapter on `skip_opposites=true`; index 2 calls another merging implementation on `skip_opposites=false`. This changes the feature set, dropped predecessors (636 versus zero), node times, and connectivity, as well as which directional traversal times exist. It is not a comparison between unmerged and merged representations of identical labels. The code comments describing index 0 as the pre-fix path are stale. The stored artifact's 37 gained cells cannot be assigned solely to duplicate-geometry tie breaking.

Executed inspection:

```powershell
Get-Content v2/spikes/s1_expansion_directions.py | Select-Object -Skip 220 -First 28
Get-Content v2/data/s1_expansion_directions_grocery_drive.json
```

Relevant real output:

```text
i0, t0_ = expansion_to_edge_index(feats_skip, target_crs=GRID.crs, opposites_included=False,
                                  origins=lonlat, strict=False, report={})
i2, t2_, d2 = merged_index(feats_both, target_crs=GRID.crs, origins=lonlat, directional=False)
"merging_effect": { ... "gained": 37, ... "changed_over_1s": 13301,
                   "share_changed": 0.08778205288966032, ... }
```

**Smallest correct fix.** Freeze one complete payload and one node-time array. Compare an explicit unmerged representation with a merged representation, keeping all other inputs fixed. Rename the existing result as a combined request/reconstruction change until that experiment runs.

**The direction-only result survives this attack.** Indices 2 and 3 both call `merged_index(feats_both, ...)`; `directional` only changes the final edge-time arrays, after the identical `T` calculation. Thus the proposed node-time confound does not apply to **2 → 3**. For fixed geometry and T, taking away a branch or replacing the cheaper bidirectional fallback with its larger directional time cannot lower the local minimum in `snap.py:149`. This is a local interpolation monotonicity result, not a fresh shortest-path search. The saved measurement excludes changes of at most one second and excludes non-finite pairs: 13,897 comparable changes got later, **72 other cells became unreachable**, and none gained reachability. “100% of changed cells” needs those qualifications. It does not prove that the inferred direction labels are legal: H1's wrong labels also satisfy this check.

## M2 — Medium: the paired time-error rows silently use different cohorts and different cutoffs

**Claim.** The new row improves the published row on the same paired cells. Sources: `g1_expansion_primitive.py:92`, `:212`, `:220`; `g1-routing.md:874`.

**Defect.** The old path has no final 3,600 s cutoff; the new path does. Time-error statistics then separately intersect each output's finite set with the reference. The old walk median uses **195** points; the new uses **181**, although the plan labels the table “240 paired cells.” Threshold statistics do use the reference-finite sample, so this is specifically a time-error-comparison problem. The actual experiment document prints n, but its narrative and the plan still overstate pairing.

Executed a second new-path calculation with the cutoff omitted (same request, baseline, access policy). Real output:

```text
new WITHOUT cutoff: n 195 median abs 29.983465205872108 p90 88.62507920199421 signed 27.709236122528864 over 3600 14
```

Command: A4, changing the `cell_seconds_from_arrival(...)` call to omit `cutoff_s=3600`, then printing `m.sum()`, the absolute-error median/p90, signed median, and `sum(e[m] > 3600)`. The 14-point difference is caused by that cutoff on this sample. The improvement in the median still exists; it should not be represented as a 195-versus-181 paired time-error estimate.

**Smallest correct fix.** Preserve unclipped times for fidelity measurement, or apply the same censoring to both. Compute paired improvements on the common finite mask and separately report failures/coverage for all 240 reference points. Do not hide missing predictions inside the time-error denominator.

## M3 — Medium: 41.7% is five of twelve conditional positives, not an estimated general drive exclusion rate

**Claim.** The conservative bias produces a 41.7% false-exclusion rate at ten minutes. Sources: `g1_expansion_primitive.py:140`, `:264`, `:272`; plan `:210`, `:463`.

**Arithmetic survives.** `ex_in = finite(exact) & (exact <= 600)` and the denominator is `ex_in.sum()`, not 240. The numerator is reference-positive cells whose new prediction is missing or above threshold. This correctly counts model-unreachable/reference-reachable cells **if sampled**. Executed artifact check:

```powershell
@'
import json
from pathlib import Path
p=json.loads(Path('data/s1_expansion_remeasure_grocery_drive_fresh.json').read_text())['thresholds']['10']
print('10 minute threshold:',p)
print('false negatives / reference positives =',round(p['new_false_out']*p['exact_in']),'/',p['exact_in'])
'@ | uv run python -
```

```text
10 minute threshold: {'old_agrees': 0.975, 'new_agrees': 0.975, 'new_false_in': 0.0043859649122807015, 'new_false_out': 0.4166666666666667, 'exact_in': 12}
false negatives / reference positives = 5 / 12
```

**Defect.** `fresh_baseline` samples only the expansion model's own finite, under-60-minute set. It assigns zero sampling probability to every excluded cell, including any truly under-ten-minute cell that the primitive cannot reach or has overestimated beyond the horizon. A fixed seed makes that conditional sample repeatable, not representative of the full grid or of near-ten-minute journeys. Only twelve sampled positives support the headline. The direction or size of bias for the full-grid rate is not quantified; do not turn the conditional figure into either a general rate or a proven lower bound. The independent node experiment similarly excludes T=0 and infinite T, so it cannot test destination correctness or missing predictions.

**Smallest correct fix.** Label the existing number “5/12 reference positives in 240 model-reachable sampled cells.” Add independent grid sampling with positive inclusion probability outside the model's reachable set; oversample the reference threshold band with known weights, and publish counts and uncertainty. Save sampled coordinates, reference outputs, prediction outputs, and request/metro identity. The current fresh result JSON saves aggregates but omits the cohort's `idx` and raw `exact` values.

## M4 — Medium: strict mode is not a reconstruction-validity gate

**Claim.** Strict mode rejects a tree that is not self-consistent; relaxing it merely drops bad edges safely. Sources: `expansion.py:154`, `:182`, `:221`, `:275`.

**Defect.** It checks missing predecessors and unorientable roots only. Decreasing cumulative durations are clamped to 0.1 s rather than rejected, missing IDs/sentinel defaults can silently change meaning, duplicate IDs overwrite the lookup, endpoint adjacency has an unbounded nearest-end fallback, and neither graph identity nor root coverage is checked. Retained descendants can still read a skipped parent's raw duration from `by_edge`; “dropped” does not mean the entire dependent reconstruction has been invalidated.

A1 executed with default `strict=True`:

```text
decreasing duration accepted: tau= [100.0, 0.1] T= [0.0, 100.0, 50.0] midpoint= 100.05
```

This edge's far label is 50 but its midpoint reconstructs as 100.05. Strict mode returns normally.

**The real residual root.** There are six root features for three destinations, not three roots. Root `2731839879066` has duration 5, no successors, and is opposite retained root `2732208977818`. It is not an isolated malformed destination. With `strict=False`, its shape is still present through the other direction. I restored its missing direction with traversal time 5 while keeping the existing T and reran all grid cells:

```text
restore dropped root direction (5 s), same T: changed finite cells 0 reachability changes 0
```

That is a sensitivity test, not a correct partial-root implementation. Under today's erroneous zero-node assignment the alternative branch dominates it, masking the omission. It does not establish safe dropping in general or validate cells near the destination. H1's positive matrix times at the zero nodes show why.

**Smallest correct fix.** Keep `strict=False` for diagnostics. Do not adopt it as an unconditional production policy. A production acceptance check must validate the actual roots/partial anchors and destination coverage, authoritative opposite identities and direction consistency, usable predecessor chains/joins, finite nonnegative labels with monotonic cumulative durations (allowing documented quantization), and explicit provenance for every rejection. Until root handling is repaired, fail construction or mark affected answers unknown. An arbitrary allowance of one dropped root, or `dangling_predecessors == 0`, is insufficient.

## Claims that survived, and the remaining drive-mechanism question

**Basic arrival-direction algebra survives.** At fraction f along S→E, forward travel uses `(1-f)*fwd_time + T[E]`; reverse uses `f*rev_time + T[S]` (`snap.py:149`). If the near end truly is S, far→near really is reverse travel. The usual open-edge reversed-storage re-expression also works; I inspected the triangle tests and exercised reversed storage. The counterexamples concern inference of the near end, root anchors, topology, and closed-loop order, not that algebra. I also resolved raw far endpoints recursively from successor-identifiable roots: **476,071** directed endpoints resolved, **zero** unresolved joins, **zero** non-root near-end disagreements with the adapter on those resolved features. Although **51,457** features share both endpoints with their predecessor, that ambiguity did not produce an observed non-root orientation error on this payload. It remains insufficiently specified for arbitrary input (A1 includes such a constructed case).

**The old walk row is faithful.** I inspected `git show fc55be1:v2/spikes/g1_expansion_primitive.py`. Its request, costing options, selection of the first three grocery centroids, nearest geometry, full duration charge, access-speed term, 200 m mask, and absence of a final cutoff match the new `cells_old_method`. A4 reproduced the full-precision old values printed above, which round to **69 / 271 / +66 s**. I found no flattering implementation substitution in that old path. This does not rescue the new path's different finite cohort (M2).

**The unit conversions and access subtraction survive.** `g1_matrix_compare.py:76`, `:97`, `:128` writes minutes; `g1_raster_primitive.py:73`, `:153` stores matrix seconds without dividing. The *ratio is access charge / bias*, not bias / charge. `snap.py:220` adds exactly distance divided by access speed. For finite retained observations, subtracting that exact term recovers this model's network component. It cannot unclip missing observations or force Valhalla to correlate onto the same road. Nor does subtracting medians equal the median of pointwise subtraction: 81.6 s total median minus 21.2 s access median need not be the reported 50.0 s residual.

I reran the own-graph decomposition with its writers disabled:

```powershell
@'
import sys
from pathlib import Path
sys.path.insert(0,'spikes')
import s1_access_leg_decomposition as s
s.append_results=lambda *a:None
Path.write_text=lambda *a,**kw:0
sys.argv=['s1_access_leg_decomposition.py','grocery','walk']
s.main()
'@ | uv run python -
```

Actual output excerpt:

```text
n=599  signed median +12.0 s  median abs 30.8 s
access distance median 30.8 m -> charged 24.4 s
    0-5   m  n=  76  bias     -9.9 s  access     1.8 s
    5-20  m  n= 144  bias     -2.6 s  access     9.2 s
   20-50  m  n= 200  bias    +16.3 s  access    26.1 s
   50-100 m  n= 111  bias    +36.5 s  access    52.5 s
  100-200 m  n=  68  bias    +96.8 s  access   105.8 s
with the access leg removed: signed median -11.3 s, median abs 22.8 s, p90 145.1 s
median access charge / median bias = 2.0271023656238034
```

The own-graph residual is consistent with approximately 11 s of on-network optimism plus access charging. It does not isolate the *speed* model from network selection, correlation, route preference, or graph differences. The 100–200 m band's +96.8 s is **net bias**; its actual median access charge is **105.8 s**. The narrative's “access charge ... +97 s” (`s1_access_leg_decomposition.py:175`) misnames those two columns.

**The drive +50 s observation survives several attacks, but its mechanism remains unresolved.** A3 reproduced **238 finite comparisons**, median **+50.0 s**, maximum absolute **322.0 s**. The two discarded references are missing comparisons, not evidence of fidelity. The sampled node coordinates were first representatives of quantized node buckets, not authoritative graph IDs. I measured the coordinate conflation described in H3 and found none among these 240 sampled points.

I independently assigned each raw directed feature's cumulative duration to its recursively resolved far endpoint, took coordinate minima, and compared those labels directly with the same matrix sample. This bypasses physical-edge merging, tau differences, root-zero interpolation, and the adapter's node-label minima. Output:

```text
direct raw far-duration vs router: n 238 signed median 50.0 max abs 322.0
adapter vs raw endpoint min: changed nodes 4
```

Thus the median gap exists upstream of this adapter on this cohort, while the adapter still has local defects. Six `/route` checks to the matrix-selected best target further returned:

```text
NODE 205927 T 3270.0 matrix 3220 route 3220.999
NODE 158347 T 2893.0 matrix 2844 route 2844.096
NODE 43948 T 2034.0 matrix 2040 route 2034.965
NODE 180962 T 3085.0 matrix 3036 route 3036.416
NODE 194421 T 3354.0 matrix 3187 route 3187.728
NODE 31472 T 1656.0 matrix 1607 route 1607.037
```

Five agree with the matrix within one second and disagree with expansion. One exposes a matrix-versus-route difference of about five seconds. Matrix response coordinates can differ from input: for node 205927 the input was `(-78.592177, 35.85304999999999)`, response `(-78.592176, 35.853049)`. These response values alone do not establish the selected graph edge/node or whether the difference is snapping versus serialization. The node spike's “exactly those points ... and nothing else” claim (`s1_expansion_node_fidelity.py:127`) has not controlled correlation identity.

Auto controlled options are `{}` (`spikes/_common.py:59`), so there is no controlled-versus-default parameter mismatch in these auto requests. A longer-contour experiment returned:

```text
60->120 min: common directed edges 476072 changed 6 median delta 0.0 max abs delta 1044
```

The contour can affect some labels, but does not change the median common-edge label. I did not rerun the full node cohort against the 120-minute response, so this does not quantify its effect on the sampled median. It also disproves any blanket assumption that common expansion labels are contour-independent.

**Decisive next test.** Pin source and target correlation to the same directed edge IDs and fractions. For a node with a large gap, retain the complete expansion predecessor chain and its chosen target. Obtain/reconstruct the router's chosen directed edge sequence and recost **both fixed sequences** under identical forward and reverse traversal, reporting edge seconds and transition seconds separately. Compare routes before summing: a different target/path is a cost-selection discrepancy; different seconds on the same path is a costing/search discrepancy; only a difference at the starting transition supports the “fresh start avoids a turn” explanation. A cost-only penalty must not be mistaken for elapsed time. Valhalla 3.9.1 distinguishes transition cost from elapsed seconds in [auto costing](https://raw.githubusercontent.com/valhalla/valhalla/3.9.1/src/sif/autocost.cc), and its [isochrone code](https://raw.githubusercontent.com/valhalla/valhalla/3.9.1/src/thor/isochrone.cc) uses cost for queue ordering and time for termination. These are reasons to measure the separate quantities, not proof of the proposed mechanism.

I ran the raw-label, correlation-response, route, and contour controls above. I did **not** complete a pinned-edge, per-transition recost comparison or an engine build with transition seconds instrumented/disabled. Neither the existing spike nor this review establishes that turn/stop costs explain the 50 s median. Turning off a few public penalty options would not be decisive because it can change route choice and need not remove elapsed transition seconds.

## Reproduction commands

The following commands show the executed procedures and inputs. `.review9` is a temporary local cache of live responses. Cleanup was attempted, but command approval rejected both recursive directory removal and explicit file removal as blocked by policy, so its three pickle files remain locally. A2 recreates it; no pre-existing cache is needed. A3's index cache is used by the supplementary snippets. No spike `main()` that appends experiment results was run without disabling its writers.

### A1 — synthetic counterexamples (no server needed)

```powershell
@'
import numpy as np
from locfinder.traveltime.expansion import expansion_to_edge_index, _physical_key, _node_key
from locfinder.traveltime.snap import cell_seconds_from_arrival
def f(c,t,i,p=None):
 return {'geometry':{'coordinates':c},'properties':{'duration':t,'edge_id':i,'pred_edge_id':p}}
def build(fs,origins):
 return expansion_to_edge_index(fs,target_crs='EPSG:3857',source_crs='EPSG:3857',opposites_included=True,origins=origins)
def at(idx,T,p):
 return float(cell_seconds_from_arrival(idx,T,np.array([p[0]]),np.array([p[1]]),mode='walk',max_access_m=200)[0])
a,b,c=(0,0),(100,0),(200,0)
i,t=build([f([a,b],100,1),f([b,c],200,2,1),f([b,c],120,3,1)],[a])
print('distinct ids, same geometry: entries=',len(i.geoms),'(expected 3 if distinct roads)')
print('same road with extra collinear vertex keys equal:',_physical_key([a,b])==_physical_key([a,(50,0),b]))
print('7dp collision:',_physical_key([(0,0),(1,0)])==_physical_key([(0,0.00000004),(1,0.00000004)]))
i,t=build([f([a,b],100,1),f([a,b],200,2,1)],[a])
print('opposite root/successor: fwd=',i.fwd_time.tolist(),'rev=',i.rev_time.tolist(),'(expected fwd 100, rev 100)')
loop=[b,(150,50),c,b]
i,t=build([f([a,b],100,1),f(loop,250,2,1),f(list(reversed(loop)),260,3,1)],[a])
print('reversed loop: start=end',i.start_idx[1]==i.end_idx[1],'fwd=',i.fwd_time[1],'rev=',i.rev_time[1])
i,t=build([f([(0,0),(10,0)],100,1),f([(10,0),(10.2,0)],200,2,1)],[(0,0)])
print('short edge: start=end',i.start_idx[1]==i.end_idx[1],'far endpoint time=',at(i,t,(10.2,0)),'expected 200')
print('node key 2cm apart:',_node_key(.24,0),_node_key(.26,0),'node key .69m apart:',_node_key(-.24,-.24),_node_key(.24,.24))
i,t=build([f([a,b],100,1),f([b,c],50,2,1)],[a])
print('decreasing duration accepted: tau=',i.rev_time.tolist(),'T=',t.tolist(),'midpoint=',at(i,t,(150,0)))
i,t=build([f([a,b],20,1)],[(80,0)])
print('interior root: reported at destination=',at(i,t,(80,0)),'expected 0; at b=',at(i,t,b),'expected >0')
'@ | uv run python -
```

Real output:

```text
distinct ids, same geometry: entries= 2 (expected 3 if distinct roads)
same road with extra collinear vertex keys equal: False
7dp collision: True
opposite root/successor: fwd= [inf] rev= [100.0] (expected fwd 100, rev 100)
reversed loop: start=end True fwd= inf rev= 150.0
short edge: start=end True far endpoint time= 100.0 expected 200
node key 2cm apart: (0, 0) (1, 0) node key .69m apart: (0, 0) (0, 0)
decreasing duration accepted: tau= [100.0, 0.1] T= [0.0, 100.0, 50.0] midpoint= 100.05
interior root: reported at destination= 3.999999999999999 expected 0; at b= 0.0 expected >0
```

The opposite-root/successor fixture is an API counterexample assuming the described U-turn is legal, not a claim that Valhalla emits that exact two-feature tree.

### A2 — live request and geometry collision audit

```powershell
@'
import sys,pickle,collections
from pathlib import Path
sys.path.insert(0,'spikes')
import geopandas as gpd
from _common import ACCEPTED_PLACES,GRID
from locfinder.places.categories import select_overture
from s1_expansion_node_fidelity import expansion_request
from locfinder.traveltime.expansion import _physical_key
p=select_overture(gpd.read_parquet(ACCEPTED_PLACES),'grocery').to_crs(GRID.crs).geometry.centroid.to_crs('EPSG:4326')
ll=list(zip(p.y,p.x))[:3]
fs=expansion_request(ll,'auto',skip_opposites=False)
Path('.review9').mkdir(exist_ok=True)
with open('.review9/live.pkl','wb') as out: pickle.dump((ll,fs),out)
ids=collections.Counter(f['properties']['edge_id']for f in fs)
groups=collections.defaultdict(list)
for f in fs:groups[_physical_key(f['geometry']['coordinates'])].append(f)
large=[g for g in groups.values()if len(g)>2]
print('unique edge ids',len(ids),'duplicates',sum(v-1 for v in ids.values()),'groups >2',len(large),'max group',max(map(len,groups.values())))
for g in large[:2]:print('GROUP',[(x['properties'],x['geometry']['coordinates'])for x in g])
'@ | uv run python -
```

The request/cache and collision count were executed as two stdin invocations; this block combines them for convenience. The real collision output is pasted in H2.

### A3 — live root signals, coordinates, zero nodes, and node sample

```powershell
@'
import sys,pickle,numpy as np,shapely
sys.path.insert(0,'spikes')
from _common import GRID
from pyproj import Transformer
from locfinder.traveltime.expansion import expansion_to_edge_index,_orient_root
from s1_expansion_node_fidelity import matrix_exact
ll,fs=pickle.load(open('.review9/live.pkl','rb'));succ={}
for f in fs:succ.setdefault(f['properties'].get('pred_edge_id'),[]).append(f)
proj=Transformer.from_crs('EPSG:4326',GRID.crs,always_xy=True)
ox,oy=proj.transform([p[1] for p in ll],[p[0] for p in ll]);origins=shapely.points(ox,oy)
for f in succ[70368744177663]:
 c=f['geometry']['coordinates'];x,y=proj.transform(*zip(*c));g=shapely.LineString(zip(x,y));e={'geom':g,'ll_first':tuple(c[0]),'ll_last':tuple(c[-1])};ss=[{'ll_first':tuple(z['geometry']['coordinates'][0]),'ll_last':tuple(z['geometry']['coordinates'][-1])}for z in succ.get(f['properties']['edge_id'],[])]
 print('ROOT',f['properties']['edge_id'],'dur',f['properties']['duration'],'origin_near_start',_orient_root(e,ss,origins),'succ_near_start',_orient_root(e,ss,None))
rep={};idx,T=expansion_to_edge_index(fs,target_crs=GRID.crs,opposites_included=True,origins=[(lo,la)for la,lo in ll],strict=False,report=rep)
print('report',rep)
node_xy={};spread={}
for k,g in enumerate(idx.geoms):
 for n,p in ((int(idx.start_idx[k]),g.coords[0]),(int(idx.end_idx[k]),g.coords[-1])):
  if n in node_xy:spread[n]=max(spread.get(n,0),np.linalg.norm(np.array(p)-node_xy[n]))
  node_xy.setdefault(n,p)
finite=[n for n in node_xy if np.isfinite(T[n]) and T[n]>0];pick=np.random.default_rng(20261104).choice(finite,size=240,replace=False)
inv=Transformer.from_crs(GRID.crs,'EPSG:4326',always_xy=True)
xy=np.array([node_xy[int(n)]for n in pick]);lon,lat=inv.transform(xy[:,0],xy[:,1]);exact=matrix_exact(list(zip(lon,lat)),ll,'auto');m=np.isfinite(exact)
print('node replication:',int(m.sum()),'median',np.median(T[pick][m]-exact[m]),'max',np.max(abs(T[pick][m]-exact[m])))
print('nodes sharing distinct coordinates',sum(v>1e-6 for v in spread.values()),'max spread m',max(spread.values()),'sample affected',sum(spread.get(int(n),0)>1e-6 for n in pick))
zero=np.flatnonzero(T==0);xy0=np.array([node_xy[int(n)]for n in zero]);lo,la=inv.transform(xy0[:,0],xy0[:,1]);ex0=matrix_exact(list(zip(lo,la)),ll,'auto');print('zero node matrix times',ex0.tolist())
with open('.review9/index.pkl','wb')as out:pickle.dump((idx,T,node_xy,pick,exact),out)
'@ | uv run python -
```

Additional real output, besides H1's root rows:

```text
report {'edges': 476072, 'physical_edges': 253635, 'merged_pairs': 221414, 'dangling_predecessors': 0, 'roots_unoriented': 1, 'dropped': 1, 'origins_supplied': 3, 'opposites_included': True, 'bidirectional_fallback': False}
node replication: 238 median 50.0 max 322.0
nodes sharing distinct coordinates 2 max spread m 0.37741125959301497 sample affected 0
zero node matrix times [2.0, 3.0, 5.0]
```

### A4 — paired walk reproduction and residual tails

```powershell
@'
import sys,numpy as np,geopandas as gpd,shapely
sys.path.insert(0,'spikes')
from _common import GRID,ACCEPTED_PLACES
from locfinder.places.categories import select_overture
import g1_expansion_primitive as g
from locfinder.traveltime.expansion import expansion_to_edge_index
from locfinder.traveltime.snap import cell_seconds_from_arrival
from locfinder.traveltime.speeds import access_speed_mps
p=select_overture(gpd.read_parquet(ACCEPTED_PLACES),'grocery').to_crs(GRID.crs).geometry.centroid.to_crs('EPSG:4326');ll=list(zip(p.y,p.x))[:3]
k,ex,_,_,_=g.load_paired('raster','grocery','walk');xs,ys=GRID.cell_centers_xy()
f,_=g.expansion_request(ll,'pedestrian',controlled=True,skip_opposites=True,props=g.PROPS_OLD);old,n=g.cells_old_method(f,xs,ys,mode='walk');old=old.ravel()[k];m=np.isfinite(old)&np.isfinite(ex)
print('walk old:',n,'n',m.sum(),'median/p90/signed',np.median(abs(old[m]-ex[m])),np.percentile(abs(old[m]-ex[m]),90),np.median(old[m]-ex[m]))
f,_=g.expansion_request(ll,'pedestrian',controlled=True,skip_opposites=False,props=g.PROPS_NEW);idx,T=expansion_to_edge_index(f,target_crs=GRID.crs,opposites_included=True,origins=[(lo,la)for la,lo in ll]);e=cell_seconds_from_arrival(idx,T,xs,ys,mode='walk',max_access_m=200,cutoff_s=3600).ravel()[k]
pts=shapely.points(xs.ravel()[k],ys.ravel()[k]);a=shapely.distance(pts,idx.geoms[idx.tree.nearest(pts)])/access_speed_mps('walk');m=np.isfinite(e)&np.isfinite(ex);r=e[m]-a[m]-ex[m]
print('walk new n',m.sum(),'signed',np.median(e[m]-ex[m]),'access/bias',np.median(a[m])/np.median(e[m]-ex[m]),'after subtract median/abs/p90/max',np.median(r),np.median(abs(r)),np.percentile(abs(r),90),max(abs(r)))
'@ | uv run python -
```

Output is pasted in H4. This invokes helpers only; it does not append to `g1-routing.md` or rewrite result JSON.

### A5 — contour and independent router controls

```powershell
@'
import pickle,sys,numpy as np
sys.path.insert(0,'spikes')
from s1_expansion_node_fidelity import expansion_request
ll,fs=pickle.load(open('.review9/live.pkl','rb'));old={f['properties']['edge_id']:f['properties']['duration']for f in fs}
f=expansion_request(ll,'auto',skip_opposites=False,minutes=120)
d=[x['properties']['duration']-old[x['properties']['edge_id']]for x in f if x['properties']['edge_id']in old]
print('60->120 min: common directed edges',len(d),'changed',np.count_nonzero(d),'median delta',np.median(d),'max abs delta',max(abs(np.array(d))))
'@ | uv run python -
```

```powershell
@'
import sys,pickle,numpy as np,httpx
sys.path.insert(0,'spikes')
from _common import GRID
from pyproj import Transformer
ll,fs=pickle.load(open('.review9/live.pkl','rb'));idx,T,xy,pick,exact=pickle.load(open('.review9/index.pkl','rb'))
inv=Transformer.from_crs(GRID.crs,'EPSG:4326',always_xy=True)
for q in [0,1,2,3,4,5]:
 n=int(pick[q]);lo,la=inv.transform(*xy[n]);src={'lon':lo,'lat':la};tg=[{'lon':lo1,'lat':la1}for la1,lo1 in ll]
 j=httpx.post('http://localhost:8002/sources_to_targets',json={'sources':[src],'targets':tg,'costing':'auto'},timeout=90).json()
 row=j['sources_to_targets'][0];best=min((c['time'],k)for k,c in enumerate(row)if c.get('time')is not None);r=httpx.post('http://localhost:8002/route',json={'locations':[src,tg[best[1]]],'costing':'auto','directions_options':{'units':'kilometers'}},timeout=90).json()
 print('NODE',n,'T',T[n],'matrix',best[0],'route',r.get('trip',{}).get('summary',{}).get('time'),'corr_source',j.get('sources'),'input',src)
'@ | uv run python -
```

The result discussion above pastes the real time columns and one correlation example from this output.

### A6 — independent raw endpoint labels, bypassing the adapter

The recursive endpoint resolution and label comparison were executed in separate invocations. Combined reproduction:

```powershell
@'
import pickle,sys,collections,numpy as np
sys.path.insert(0,'spikes')
from _common import GRID
from pyproj import Transformer
from locfinder.traveltime.expansion import _node_key
ll,fs=pickle.load(open('.review9/live.pkl','rb'))
idx,T,xy,pick,exact=pickle.load(open('.review9/index.pkl','rb'))
succ=collections.defaultdict(list)
for f in fs:succ[f['properties'].get('pred_edge_id')].append(f)
far={};queue=[]
for f in succ[70368744177663]:
 c=f['geometry']['coordinates'];shared={tuple(p) for s in succ[f['properties']['edge_id']] for p in (s['geometry']['coordinates'][0],s['geometry']['coordinates'][-1])}
 if (tuple(c[0])in shared)!=(tuple(c[-1])in shared):
  far[f['properties']['edge_id']]=tuple(c[0])if tuple(c[0])in shared else tuple(c[-1]);queue.append(f)
wrong=[];unresolved=[]
for p in queue:
 pf=far[p['properties']['edge_id']]
 for f in succ[p['properties']['edge_id']]:
  c=f['geometry']['coordinates'];a,b=map(tuple,(c[0],c[-1]));eid=f['properties']['edge_id']
  if pf not in (a,b):unresolved.append(eid);continue
  near_start=a==pf;far[eid]=b if near_start else a;queue.append(f)
  pc=p['geometry']['coordinates'];old=a in map(tuple,(pc[0],pc[-1]))
  if not old and b not in map(tuple,(pc[0],pc[-1])):continue
  if old!=near_start:wrong.append((f,p))
print('resolved endpoints',len(far),'unresolved joins',len(unresolved),'wrong near end',len(wrong))
nodeT={}
for f in fs:
 eid=f['properties']['edge_id']
 if eid in far:
  p=far[eid];nodeT[p]=min(nodeT.get(p,np.inf),f['properties']['duration'])
keyT={};proj=Transformer.from_crs('EPSG:4326',GRID.crs,always_xy=True)
for p,t in nodeT.items():
 k=_node_key(*proj.transform(*p));keyT[k]=min(keyT.get(k,np.inf),t)
alt=np.array([keyT.get(_node_key(*xy[int(n)]),np.inf) for n in pick]);m=np.isfinite(exact)&np.isfinite(alt)
print('direct raw far-duration vs router: n',m.sum(),'signed median',np.median(alt[m]-exact[m]),'max abs',max(abs(alt[m]-exact[m])))
print('adapter vs raw endpoint min: changed nodes',sum(abs(T[int(n)]-keyT.get(_node_key(*p),np.inf))>1 for n,p in xy.items()))
'@ | uv run python -
```

Actual output:

```text
resolved endpoints 476071 unresolved joins 0 wrong near end 0
direct raw far-duration vs router: n 238 signed median 50.0 max abs 322.0
adapter vs raw endpoint min: changed nodes 4
```

This deliberately retains the existing coordinate-bucket mapping when matching the sample; it independently reconstructs cumulative endpoint labels, not an independently attributed graph topology. A3 established that the sampled buckets have no distinct-coordinate conflation.

### A7 — dropped-root direction sensitivity

```powershell
@'
import pickle,numpy as np,sys
sys.path.insert(0,'spikes')
from _common import GRID
from locfinder.traveltime.snap import cell_seconds_from_arrival
ll,fs=pickle.load(open('.review9/live.pkl','rb'));idx,T,xy,pick,exact=pickle.load(open('.review9/index.pkl','rb'));xs,ys=GRID.cell_centers_xy()
a=cell_seconds_from_arrival(idx,T,xs,ys,mode='drive',max_access_m=200,cutoff_s=3600)
idx.fwd_time[2]=idx.fwd_cost[2]=5
b=cell_seconds_from_arrival(idx,T,xs,ys,mode='drive',max_access_m=200,cutoff_s=3600)
print('restore dropped root direction (5 s), same T: changed finite cells',np.count_nonzero(abs(a[np.isfinite(a)&np.isfinite(b)]-b[np.isfinite(a)&np.isfinite(b)])>1e-6),'reachability changes',np.count_nonzero(np.isfinite(a)!=np.isfinite(b)))
'@ | uv run python -
```

Actual output is pasted in M4. This mutates only an in-memory diagnostic index and is not a code fix.
