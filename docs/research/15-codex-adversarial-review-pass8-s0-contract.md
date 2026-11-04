# Adversarial review pass 8: Phase 1 S0 layer contract

Reviewed 2026-11-04. Report only; no product source or tests changed by this reviewer.

Three High and four Medium findings; no Critical finding demonstrated. The strongest counterexample: the real category search reports 100 seconds although one qualifying destination takes 20 seconds.

Reviewed the requested modules/tests/contract, Phase 1 revision-2 S0 requirements, pass 7 and Phase 0 decisions; inspected arrival/CSR/component code, expansion reconstruction and engine requests. During review, `profile.py` and five additional identity tests appeared, and `SurfaceKey` gained required access-cap fields. A real-data verification spike and contract §9 also appeared before finalisation. Findings account for those updates. Other workspace edits were left alone.

The initial 166 tests passed, as did the updated 171-test suite. The default uv cache was inaccessible; commands used the existing environment and a workspace cache. Final command from `v2/`:

```powershell
uv --cache-dir .uv-review-cache run --no-sync pytest -q -p no:cacheprovider
```

Actual output:

```text
........................................................................ [ 42%]
........................................................................ [ 84%]
...........................                                              [100%]
```

Appendix A contains the executed main reproduction command and its real output. The first probe draft encountered the concurrently added required key fields; the appendix records the successful updated version. No live Valhalla/MOTIS requests were made. Request construction was inspected, not engine boundary behaviour certified.

## Critical

None demonstrated.

## High

### H1 — Exhaustiveness belongs to a search invocation, not an engine name

**Claim:** Contract §1/§6 and `status.py:137-140` say own-graph search is unbounded and infinite node times prove `NO_PATH`.

**Defect:** `traveltime/layer.py:38-39` runs the two-weight path unbounded, as currently used by `spikes/g1_own_graph_layer.py:94`. But `layer.py:41` explicitly calls the supported single-weight search with `cutoff_s=cutoff_min * 60`. `arrival.py:33-38` returns infinity for reachable nodes beyond that limit. `status.node_reasons` (`status.py:169-174`) knows only T and an engine-wide boolean and certifies those infinities as `NO_PATH`.

**Executed reproduction:** Appendix A, `SINGLE_WEIGHT`, duplicates that bounded invocation on a three-node directed path, then feeds its result through the prescribed provenance composition and validates the Surface:

```text
SINGLE_WEIGHT unbounded= [210.0, 200.0, 0.0] bounded= [inf, inf, 0.0] reason= NO_PATH threshold_300= FAIL
```

The true model time is 210 seconds. A 300-second criterion should be UNKNOWN on the 100-second build, with recomputation offered; this says permanent FAIL. The old builder still emits seconds only, so this demonstrates the new composition's error rather than an already published status raster.

**Smallest correct fix:** remove the node cutoff from the single-weight builder branch too. If bounded own-graph searches remain supported, carry search-exhaustiveness provenance into node classification and use `BEYOND_HORIZON`. Engine capability alone cannot certify a particular call.

### H2 — Cost-optimal category routing is not minimum-over-destination time

**Claim:** Contract §3 says category values are `min_d t(cell -> d)` and answer whether any qualifying destination meets the threshold.

**Defect:** `arrival_seconds_two_weight` (`arrival.py:73-79,98-113`) chooses one destination/path by selection cost, then reports its time. Restricted-access penalties change which destination wins. That does not commute with taking the minimum of separately computed destination times. The category/anchor label guard cannot detect incorrect declared semantics.

**Executed reproduction:** Appendix A, `CATEGORY`, uses the real speed/access model and pedestrian symmetrisation. Destination A is a 28 m private residential edge away; B is a 140 m open residential edge away. A takes 20 seconds with cost 140; B takes 100 seconds with cost 100:

```text
CATEGORY A= 20.0 B= 100.0 category= 100.0
```

A 30-second individual A criterion passes. The category value fails despite A qualifying. This uses the adopted own-graph walking path.

**Smallest correct fix:** decide whether penalties choose routes within a destination or also choose the destination. To preserve the written existential semantics, take the minimum of each destination's cost-selected reported time, or implement an algorithm proven equivalent. Removing all penalties would alter the established access policy; merely renaming the aggregation requires changing the product's “any qualifying destination” semantics.

### H3 — Cache identity still omits dependencies and derived versions remain optional

**Claim:** Contract §5 and `identity.py:113` describe everything that makes a different surface. New `profile.py:24-27` claims every model constant is represented.

**Defect:** the updated code repairs the original omission of the two access/snap caps. Its profile helper also hashes speed/access tables, restricted penalties and `_NODE_EPS`. Remaining gaps:

| Value-changing input | Current coverage/gap |
|---|---|
| `max_access_m`, `POI_SNAP_MAX_M` | Now explicit fields; caller must supply actual build values. |
| `RESTRICTED_PENALTY_S`, speed/access tables | Captured if caller derives `profile_version`; arbitrary strings still accepted. |
| Category selector and actual selected destinations | `target` is a string, with no required selector/destination fingerprint. Updated contract §5 now explicitly acknowledges the selector omission and defers it to S6.3. |
| OSM extract, POI content, GTFS feed set/content, Valhalla tiles | One free-form `source_release` could contain a bundle hash but does not enforce separate source/content identities. |
| Valhalla version, costing options and request settings | Not derived by the own-graph profile helper; controlled/default costing in `spikes/_common.py:52` changes answers. |
| Expansion `_NODE_SNAP_M`, `_MIN_EPSILON_S`, root/drop policy and origin correlation | Not represented by `profile_params`. |
| Symmetrisation, bike contraflow, component policy | Two booleans are hard-coded in the profile, not obtained from actual build choices; contraflow is code-dependent. A caller can change whether it invokes pruning/symmetrisation under the same key. |
| Grid geometry and routing extract extent | Grid helper covers CRS/origin/resolution/dimensions if used. Routing extent/content still needs source identity. |
| Transit direct-walk policy, access/egress/transfer settings and effective server cap | Not explicit transit fields; future composition must cover them. |

`code_version` can intentionally subsume code-defined rules; a source-bundle digest can subsume data. Both remain caller-supplied strings. `identity.py:150-156` checks only direction, transit presence and paired anchor fields. No factory binds the key to actual build inputs/helper digests/engine configuration.

**Executed reproduction:** Appendix A confirms access-cap changes now produce distinct keys and values:

```text
CACHE 200.0 73494a05d823daf3 OFF_NETWORK [inf]
CACHE 400.0 f0da2700133921e7 OK [238.0952380952381]
```

This additional command was executed from `v2/`:

```powershell
@'
from dataclasses import replace
from locfinder import profile, status as s
from locfinder.identity import SurfaceKey
from locfinder.traveltime import expansion
k=SurfaceKey('triangle','drive','valhalla-expansion','x',s.CATEGORY_MIN,100.,'g1','r1',profile.profile_version(),'c1',200.,300.)
before=profile.profile_version(); old=expansion._NODE_SNAP_M
try:
    expansion._NODE_SNAP_M=1.0
    print('ADAPTER_CONSTANT', 'profile_unchanged=',before==profile.profile_version(),'key_unchanged=',k.digest()==replace(k,profile_version=profile.profile_version()).digest())
finally: expansion._NODE_SNAP_M=old
'@ | uv --cache-dir .uv-review-cache run --no-sync python -
```

Actual output:

```text
ADAPTER_CONSTANT profile_unchanged= True key_unchanged= True
```

Changing quantisation changes which endpoints merge (`expansion.py:40-41`), yet neither identity changes. This demonstrates an omitted dependency, not a deployed stale-cache incident; serving is future S5 work.

**Smallest correct fix:** derive keys from one immutable build specification consumed by the producer, including configuration, grid, source-bundle, code/artifact, selector/destination and engine fingerprints. Unbound version strings are a convention, not enforcement.

## Medium

### M1 — A validated layer-wide failure can exclude cells

**Claim:** Contract §2 and `Surface.layer_failure` promise uniform layer-wide reasons and unconditional UNKNOWN, never exclusion.

**Defect:** `Surface.validate` (`status.py:258-265`) checks only that every cell belongs to the set of layer-wide reasons. It requires neither one identical reason nor zero lower bounds. `evaluate` (`status.py:326-332`) applies arbitrary positive lower bounds to those reasons. Public direct construction followed by `.validate()` accepts both defects.

**Executed reproduction:** Appendix A:

```text
LAYER_BAD_BOUND validate=accepted outcome= FAIL
MIXED_LAYER_REASONS validate=accepted [6, 4]
```

These require malformed producer input; the `layer_failure` factory itself correctly writes zero bounds. The advertised validation boundary nevertheless accepts a value that violates the safety invariant.

**Smallest correct fix:** require one uniform layer-wide reason and zero lower bounds; additionally evaluate layer-wide reasons as unconditional UNKNOWN.

### M2 — Approximate horizon validation changes exact threshold answers

**Claim:** `BEYOND_HORIZON` carries exactly H and means `t > H`.

**Defect:** `status.py:268` uses default `np.allclose`, allowing roughly 0.072 seconds of error at H=7200. Evaluation uses the supplied bound, while `needs_recomputation` uses the separate horizon. A validated cell can be FAIL and marked for recomputation at a threshold above H.

**Executed reproduction:** Appendix A supplies bound 7200.05, H=7200, threshold 7200.025:

```text
HORIZON_TOLERANCE validate=accepted outcome= FAIL recompute= [True]
```

The contract requires UNKNOWN. A route taking 7200.01 satisfies the actual horizon condition and could pass; the accepted overstated bound excludes it. The current producer writes the exact horizon, so this is a validator/consumer defect.

**Smallest correct fix:** evaluate this reason against `surf.horizon_s`; enforce exact equality or canonicalise the stored bound. Eligibility comparisons cannot use approximate semantic identity.

### M3 — Transit identity accepts contradictory horizons and invalid windows

**Claim:** Contract §4 and `identity.py:40-42` make `window_s` the surface horizon; `snap.py:242-245` requires the node contour and cell horizon to be one number.

**Defect:** neither `SurfaceKey.__post_init__` nor the provenance producer enforces equality. `TransitQuery.__post_init__` only rejects `<= 0`, so NaN and positive infinity pass. The actual request uses `maxTravelTime: minutes` (`spikes/transit_compare.py:105-106`); identity stores seconds. There is no production identity-to-request adapter yet. `docs/experiments/transit.md:100` explicitly leaves the configured 90-minute cap behaviour untested.

**Executed reproduction:** Appendix A:

```text
WINDOW_NAN nan
MISMATCHED_HORIZON 100.0 5400.0
```

Both constructions succeed. The opposite mismatch—search shorter than declared horizon—would overstate the lower bound. This does not claim the spike sends seconds as minutes; it uses minutes correctly.

**Smallest correct fix:** require finite positive durations and equality of transit window and surface horizon. Derive request units and cell horizon from one checked value, accounting for the effective server cap. Live boundary/cap semantics remain unverified.

### M4 — Existing artifact builders still discard provenance

**Claim:** S0.1 requires carrying provenance rather than collapsing it.

**Defect:** `traveltime/layer.py:13,46-51` still calls the seconds-only function. `g1_own_graph_layer.py:83-94,102-109` does not distinguish empty selection from zero routable destinations and writes only times/encoded minutes. SOURCE_MISSING is explicitly a future S4.3 producer. The new concurrent `spikes/s0_status_on_real_layer.py` does call the provenance function, validates a real-data Surface, and records a histogram; this repairs the earlier lack of a non-test exercise. It does not change the existing artifact builder or implement the two layer-failure branches. The enum-membership test does not establish those build paths.

**Executed inspection command from `v2/`:**

```powershell
rg -n 'cell_arrival_with_provenance|Surface.layer_failure|\.validate\(' locfinder/traveltime/layer.py spikes/g1_own_graph_layer.py
```

Actual output: none, exit status 1.

**Smallest correct fix:** provide and use a provenance-returning builder, distinguishing empty-category/unsnappable-destination cases, or explicitly defer that integration. The diagnostic spike provides useful evidence, not persistent status production by the normal builder. Encoding and S4 freshness/publication remain future work; this finding does not require implementing those stages during S0.

## Low

### L1 — Accepted infinite threshold breaks “NO_PATH always fails”

**Claim:** Contract §2 says NO_PATH fails at every threshold.

**Defect/reproduction:** `Criterion.__post_init__` (`status.py:300`) accepts positive infinity. Then `inf > inf` is false. Appendix A:

```text
INFINITY_THRESHOLD UNKNOWN
```

**Smallest correct fix:** require finite positive thresholds or handle NO_PATH as unconditional FAIL.

### L2 — The explanation rejecting access-speed lower bounds is false for this model

**Claim:** Contract §2 and `snap.py:281` say access speed would not be sound.

**Defect:** for the fixed EdgeIndex and nonnegative network times actually implemented, `total = network + access_m/access_speed`. Thus the charged access time is itself a valid lower bound on the relaxed-cap model answer. Maximum speed gives a weaker valid bound, not a necessary correction. A bound for a different, more permissive model would be another question.

**Smallest correct fix:** identify precisely which model is bounded and correct the rationale. Keeping the weaker bound is acceptable if intentional.

## Claims that survived and limits of validation

1. **Taxonomy:** existing tests execute all four cell reasons through the new function, but NO_PATH is not producible in the shipped symmetric/pruned walk configuration with a nonempty destination set. Every retained edge has an opposite-direction connection; the retained weak component is therefore strongly connected, and every retained node reaches any destination. Bounded engines cannot publish NO_PATH either. The concurrent contract §9 now correctly distinguishes general code producibility from shipped-build producibility, recording zero NO_PATH nodes/cells. Its real-data histogram is independently supplied evidence inspected here, not a run executed by this reviewer. No fifth independently observable per-cell cause was established. Empty category versus unsnappable destinations is build-time knowable. SOURCE_MISSING has no current acquisition producer. Pruning/truncation causality cannot be recovered from retained arrival arrays alone; not allocating those per-cell codes is reasonable. This does not deny the possibility of retaining extra diagnostic data in a future pipeline.

2. **Pruning and NO_PATH:** removing other weak components cannot remove a path between retained nodes: such a path would belong to their weak component. Exhaustive search can prove no path *within that retained built graph*. Pruning changes snapping and the relation to the original network/world. Finite penalties do not defeat exhaustiveness. The two-weight search survives; H1 identifies the bounded single-weight exception.

3. **OFF_NETWORK bound:** survived for the implemented fixed-index, relaxed-access-cap model. Nonnegative network time plus projected `access_m/access_speed` is at least `access_m/max_speed`. Both computations use the same projected distance, so CRS distortion does not break this narrow proof. POIs are node-snapped with a 300 m cap and no destination displacement added (`g1_own_graph_layer.py:85-87`); that changes the model target but does not shorten its charged origin access. This does not prove a bound on travel to an original unsnapped POI with a direct-walk alternative. Checked every drive highway and fallback; list-valued highway tags take their minimum. Bike contraflow copies the same time/length; the 0.1-second floor slows short edges. Own-graph constants do not certify independent Valhalla/transit speed bounds or projected geometry length divided by OSM-length-derived traversal time. No broader certificate was established.

4. **Strict horizon:** finite-network cell cutoff uses strict `total > horizon`, retaining equality. The single-weight helper also retains exact equality. `node_reasons` knows neither actual horizon nor search/cap settings. Valhalla contour and MOTIS maxTravelTime requests were inspected, but live equality/cap semantics were not tested. The synthetic bounded-engine test relabels an unreachable island; it does not establish actual engine semantics. Such an island may remain UNKNOWN at every larger bounded horizon: “answerable by searching further” is an attempted computation, not a guaranteed finite answer.

5. **Refactor:** survived actual HEAD-versus-working-copy byte comparisons: 1,200 calls / 1,200,000 cell results across modes, with/without costs, one-/two-way edges, finite/infinite nodes/costs, exact/near endpoints, off-network points and four cutoffs. Dtypes and bytes matched. Diff inspection found no changed arithmetic order in the old public entry point. This is tested evidence, not exhaustive proof over arbitrary malformed inputs/all geometry.

6. **Relevant endpoints/precedence:** survived 36 additional directed fixtures: forward-only, reverse-only, bidirectional; start/interior/end; all four endpoint NO_PATH/BEYOND_HORIZON combinations. Expectations were computed in physical node order. BEYOND_HORIZON won exactly when a usable endpoint supplied it. The existing endpoint epsilon agrees with old arithmetic. No wrong reason found for coherent inputs; the producer does not validate coherence of T/cost/reason arrays.

7. **Truth table:** existing row tests pass; all 363 combinations of one through five outcomes were additionally exhausted. Known failure always wins. Finite OK uses inclusive `<=`, consistent with strict cutoff `>` and spike threshold classifications. Empty constraints include everything. M1/M2/L1 are domain/validation exceptions. For canonical finite-horizon inputs, recomputation matches UNKNOWN BEYOND_HORIZON cells above H. The function is per criterion; another failing criterion can already settle final membership without more routing.

8. **Per-anchor:** mismatch guards survived both directions in existing tests and an additional executed check. Producer labels cannot prove actual aggregation. The mathematical identity `max(t_A,t_B) <= T` equals per-anchor AND at equal finite thresholds is sound. Different thresholds need the individual values. H2 separately falsifies the category-minimum claim.

9. **DST:** executed US fall/spring and Australia/Lord_Howe half-hour transitions correctly distinguish ambiguous/nonexistent local times. Reference day is Tuesday and resolves to `2026-11-10T13:45:00+00:00`. No UTC deadline defect found for valid naive wall-clock inputs. The API should explicitly require naive `datetime.time`; timezone-bearing time input is not expressly checked. Prior-service-day loading is S4.3 work; the boolean in `fields()` does not implement it.

10. **Identity:** date/deadline/timezone/window/direction and explicit updated access caps distinguish the tested queries. Stable hashing tests pass. Rounding deliberately coalesces anchors; routing to those same rounded coordinates and bounding displacement remain S5.3 obligations. H3 concerns dependencies/enforcement, not an observed live cache incident.

Additional executed probe outputs for the directed-case, fixed-index bound and aggregation checks:

```text
REASON_PRECEDENCE 36 directed endpoint/interior cases passed
ACCESS_BOUND all 3 modes passed against relaxed-cap model times
AGGREGATION_GUARD a 'anchor' criterion needs a 'single_anchor' surface, got 'min_over_category': a category minimum answers 'any of these', an anchor surface answers 'this one'
```

## Appendix A — Executed main reproduction

From `v2/`, PowerShell. Temporary probe source was removed after recording it here. No repository source is edited by the command.

```powershell
@'
import subprocess, types, sys, itertools
from datetime import date, time
from dataclasses import replace
import networkx as nx
import numpy as np
from locfinder import status as s
from locfinder.identity import SurfaceKey, TransitQuery
from locfinder.traveltime.arrival import arrival_seconds, arrival_seconds_two_weight
from locfinder.traveltime.csr import graph_to_csr, graph_to_cost_time_csr
from locfinder.traveltime.snap import EdgeIndex, cell_arrival_with_provenance, cell_seconds_from_arrival
from locfinder.traveltime.speeds import add_travel_times, symmetrise, drive_speed_mps, max_speed_mps, DRIVE_FRICTION_MPH

def graph():
    g=nx.MultiDiGraph()
    for n,x in enumerate([0.,100.,200.]): g.add_node(n,x=x,y=0.)
    g.add_edge(0,1,travel_time=10.,cost=10.)
    g.add_edge(1,2,travel_time=200.,cost=200.)
    return g

def surf(reason, seconds=np.inf, lower=0., H=100.):
    return s.Surface('walk','own-graph','x',s.CATEGORY_MIN,H,np.array([seconds]),np.array([reason]),np.array([lower])).validate()
def crit(t): return s.Criterion('x','walk','x','category',t)

g=graph(); csr,index=graph_to_csr(g); idx=EdgeIndex.from_graph(g,index)
T=arrival_seconds(csr,dest_idx=[2],cutoff_s=100.)
a=cell_arrival_with_provenance(idx,T,np.array([0.]),np.array([0.]),mode='walk',max_access_m=200.,horizon_s=100.,node_reason=s.node_reasons(T,s.engine_for('walk')))
ss=s.Surface('walk','own-graph','x',s.CATEGORY_MIN,100.,*a).validate()
print('SINGLE_WEIGHT', 'unbounded=',arrival_seconds(csr,dest_idx=[2]).tolist(),'bounded=',T.tolist(),'reason=',s.Reason(a[1][0]).name,'threshold_300=',s.Outcome(s.evaluate(crit(300.),ss)[0]).name)

# Two different destination sets on the same cost/time graph.
g=nx.MultiDiGraph()
for n,x,y in [(0,0.,0.),(1,28.,0.),(2,0.,140.)]: g.add_node(n,x=x,y=y)
g.add_edge(0,1,length=28.,highway='residential',access='private')
g.add_edge(0,2,length=140.,highway='residential')
add_travel_times(g,mode='walk'); symmetrise(g)
c,t,ix=graph_to_cost_time_csr(g)
print('CATEGORY', 'A=',arrival_seconds_two_weight(c,t,dest_idx=[1])[0], 'B=',arrival_seconds_two_weight(c,t,dest_idx=[2])[0], 'category=',arrival_seconds_two_weight(c,t,dest_idx=[1,2])[0])

k=SurfaceKey('triangle','walk','own-graph','x',s.CATEGORY_MIN,100.,'g1','r1','p1','c1',200.,300.)
g=graph(); idx=EdgeIndex.from_graph(g,{0:0,1:1,2:2}); T=np.zeros(3)
for cap in [200.,400.]:
    a=cell_arrival_with_provenance(idx,T,np.array([0.]),np.array([300.]),mode='walk',max_access_m=cap,horizon_s=1000.,node_reason=s.node_reasons(T,s.engine_for('walk')))
    print('CACHE',cap,replace(k,max_access_m=cap).digest(),s.Reason(a[1][0]).name,a[0].tolist())

bad=surf(s.Reason.SOURCE_MISSING,lower=1000.)
print('LAYER_BAD_BOUND','validate=accepted','outcome=',s.Outcome(s.evaluate(crit(100.),bad)[0]).name)
bad=surf(s.Reason.BEYOND_HORIZON,lower=7200.05,H=7200.)
print('HORIZON_TOLERANCE','validate=accepted','outcome=',s.Outcome(s.evaluate(crit(7200.025),bad)[0]).name,'recompute=',s.needs_recomputation(crit(7200.025),bad).tolist())
bad=s.Surface('walk','own-graph','x',s.CATEGORY_MIN,100.,np.array([np.inf,np.inf]),np.array([s.Reason.SOURCE_MISSING,s.Reason.NO_DESTINATIONS]),np.zeros(2)).validate()
print('MIXED_LAYER_REASONS','validate=accepted',bad.reason.tolist())
print('INFINITY_THRESHOLD',s.Outcome(s.evaluate(crit(np.inf),surf(s.Reason.NO_PATH,lower=np.inf))[0]).name)
for zone,day,tm in [('America/New_York',date(2026,11,1),time(1,30)),('America/New_York',date(2027,3,14),time(2,30)),('Australia/Lord_Howe',date(2026,4,5),time(1,45)),('Australia/Lord_Howe',date(2026,10,4),time(2,15))]:
    try: TransitQuery(day,tm,100.,zone); result='ACCEPTED'
    except ValueError as e: result=str(e)
    print('DST',zone,day,tm,result)
q=TransitQuery(date(2026,11,10),time(8,45),5400.)
print('REFERENCE',q.service_date.strftime('%A'),q.deadline_utc.isoformat())
print('WINDOW_NAN',TransitQuery(date(2026,11,10),time(8,45),float('nan')).fields()['window_s'])
print('MISMATCHED_HORIZON',replace(k,mode='transit',engine='motis-one-to-all',transit=q).horizon_s,q.window_s)

# Compare the exact pre-refactor function loaded from HEAD, without altering source files.
old=types.ModuleType('locfinder.traveltime._pass8_old'); old.__package__='locfinder.traveltime'; sys.modules[old.__name__]=old
exec(subprocess.check_output(['git','show','HEAD:v2/locfinder/traveltime/snap.py'],text=True),old.__dict__)
rng=np.random.default_rng(8); calls=0; points=0
for one_way in [True,False]:
    g=graph()
    if not one_way:
        for u,v,d in list(g.edges(data=True)): g.add_edge(v,u,**d)
    idx=EdgeIndex.from_graph(g,{0:0,1:1,2:2})
    x=np.r_[0.,100.,200.,.00001,199.99999,rng.uniform(-100,300,995)].reshape(20,50)
    y=np.r_[np.zeros(5),rng.uniform(-500,500,995)].reshape(20,50)
    for i in range(50):
        T=rng.choice([0.,1.,100.,1000.,np.inf],3)
        D=None if i%2 else rng.choice([0.,10.,200.,2000.,np.inf],3)
        for mode,cutoff in itertools.product(['walk','bike','drive'],[None,0.,100.,10000.]):
            kw=dict(mode=mode,max_access_m=200.,node_cost=D,cutoff_s=cutoff)
            a=old.cell_seconds_from_arrival(idx,T,x,y,**kw); b=cell_seconds_from_arrival(idx,T,x,y,**kw)
            assert a.dtype==b.dtype and a.tobytes()==b.tobytes()
            calls+=1; points+=a.size
print('REFACTOR_BIT_IDENTICAL',calls,'calls',points,'cell results')
for n in range(1,6):
    for row in itertools.product(list(s.Outcome),repeat=n):
        expected=s.Verdict.EXCLUDED if s.Outcome.FAIL in row else s.Verdict.UNKNOWN if s.Outcome.UNKNOWN in row else s.Verdict.INCLUDED
        assert s.combine([np.array([o]) for o in row])[0]==expected
print('COMBINE_EXHAUSTIVE','363 rows passed')
assert all(drive_speed_mps({'highway':h})<=max_speed_mps('drive') for h in [*DRIVE_FRICTION_MPH,'unknown'])
print('DRIVE_SPEED_BOUND','all highway tags and fallback passed')

'@ | uv --cache-dir .uv-review-cache run --no-sync python -
```

Actual output:

```text
SINGLE_WEIGHT unbounded= [210.0, 200.0, 0.0] bounded= [inf, inf, 0.0] reason= NO_PATH threshold_300= FAIL
CATEGORY A= 20.0 B= 100.0 category= 100.0
CACHE 200.0 73494a05d823daf3 OFF_NETWORK [inf]
CACHE 400.0 f0da2700133921e7 OK [238.0952380952381]
LAYER_BAD_BOUND validate=accepted outcome= FAIL
HORIZON_TOLERANCE validate=accepted outcome= FAIL recompute= [True]
MIXED_LAYER_REASONS validate=accepted [6, 4]
INFINITY_THRESHOLD UNKNOWN
DST America/New_York 2026-11-01 01:30:00 2026-11-01 01:30:00 is ambiguous in America/New_York (the clock repeats this hour); choose a deadline outside the DST transition
DST America/New_York 2027-03-14 02:30:00 2027-03-14 02:30:00 does not exist in America/New_York (the clock skips this hour); choose a deadline outside the DST transition
DST Australia/Lord_Howe 2026-04-05 01:45:00 2026-04-05 01:45:00 is ambiguous in Australia/Lord_Howe (the clock repeats this hour); choose a deadline outside the DST transition
DST Australia/Lord_Howe 2026-10-04 02:15:00 2026-10-04 02:15:00 does not exist in Australia/Lord_Howe (the clock skips this hour); choose a deadline outside the DST transition
REFERENCE Tuesday 2026-11-10T13:45:00+00:00
WINDOW_NAN nan
MISMATCHED_HORIZON 100.0 5400.0
REFACTOR_BIT_IDENTICAL 1200 calls 1200000 cell results
COMBINE_EXHAUSTIVE 363 rows passed
DRIVE_SPEED_BOUND all highway tags and fallback passed
```

