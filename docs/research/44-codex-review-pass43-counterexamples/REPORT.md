**Keeping 100 m is supported by the measured model comparison. The browser path is not ready: the app cannot initialize, and the conformance harness passes materially wrong implementations.**

Reviewed code matches `e2bd56f`; the checkout’s additional commit changes only the review prompt. No repository files changed. The 36 wire/browser tests passed. I reproduced the full census in memory; I did not run the full suite.

The reproducible findings follow. R1–R3 below are runnable from the repository root and write no files.

1. **High — the browser fails before posting its initialization message.**  
   [app.js:269](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/spikes/g3-render/app.js:269)

   `initWorker(manifest, buffers)` references `values` and `statuses`, which exist only inside `loadFixtures()`. The actual result is **`ReferenceError: values is not defined`**. Boot exits before adding the mask source or computing the initial result.

   **Reproducer:** R2 prints `BOOT values is not defined`.  
   **Cost:** no working browser rendering path. Pass the planes explicitly or split `buffers` inside `initWorker()`.

2. **High — the conformance harness permits wrong verdicts and arbitrary spatial rearrangement.**  
   [worker_conformance.mjs:146](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/spikes/g3-render/worker_conformance.mjs:146), [worker_conformance.mjs:166](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/spikes/g3-render/worker_conformance.mjs:166)

   There are two independent holes:

   - Synthetic cases distinguish EXCLUDED from UNKNOWN only on stripe positions. The hand-built `NO_PATH` cell is at index 6, off-stripe. Changing its outcome to UNKNOWN passes every check.
   - Real-window cases have no `c.verdicts`. Consequently, **zero cells receive a positional comparison**, including their INCLUDED membership. The digest is computed but never compared with the expected digest. Moreover, Python hashes three-way verdicts while JavaScript hashes the binary mask; those are different payloads.

   **Reproducer:** R2 makes both mutations in memory and still passes all **37 checks**. The window rotation changes **13,695 verdict positions**, including **1,862 mask positions**, at ten minutes.

   **Cost:** withdraw the claim that these checks establish JavaScript’s cell-by-cell agreement. Compare the same expected mask digest, and return or otherwise test a complete three-way verdict plane to cover EXCLUDED versus UNKNOWN everywhere.

3. **Medium — the product exporter introduces another grid whose error the grid decision did not measure.**  
   [export_published_layers.py:105](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/scripts/export_published_layers.py:105), [export_published_layers.py:111](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/scripts/export_published_layers.py:111)

   The browser gets a new 514 × 643 WGS84 raster. A structure’s WGS84 pixel can select a different UTM source cell from direct `GridSpec.cell_for_xy()` lookup.

   At 15 minutes, these two lookups disagree for **12,098 of 500,451 structures** inside the browser bounds. Those bounds also omit **12,182 structures** from the published-footprint census.

   **Reproducer:** R1 prints `REGRID inside 500451 omitted 12182 changed 12098`.

   **Cost:** the source-grid comparison does not describe the shipped spatial answer. Nearest resampling preserves source codes; it does not preserve each address’s cell assignment.

   I also measured the exported candidates against the centroid reference: **15,684 disagreements for 100 m versus 23,528 for 200 m**, over that common browser population. The ranking survives, but the browser’s measured result needs its own reporting.

4. **Medium — the app defaults to intersecting both candidate grids.**  
   [app.js:384](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/spikes/g3-render/app.js:384)

   Every manifest entry starts checked, including the rejected 200 m candidate. Reset also enables both. After fixing finding 1, the default answer is therefore the intersection of two versions of the same criterion.

   **Reproducer:** R1 prints `DEFAULT 74227 70205` at the app’s default 20-minute threshold.

   **Cost:** **4,022 passing 100 m pixels disappear**. Candidate selection should be exclusive, or the candidate should be outside the product manifest.

5. **Medium — “it costs 9%” uses the wrong v1 baseline.**  
   [export_published_layers.py:155](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/scripts/export_published_layers.py:155), [s3-5-browser-path.md:65](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/experiments/s3-5-browser-path.md:65)

   `v1_deflated` compresses v2’s value plane, including lower bounds at missing cells. V1 would store **255** there.

   **Reproducer:** R1’s `SIZE` output.

   | Candidate | V2 deflated | Actual v1 plane deflated | Increase |
   |---|---:|---:|---:|
   | 100 m | 202,380 | 171,260 | **18.17%** |
   | 200 m | 101,696 | 81,645 | **24.56%** |

   **Cost:** the 100 m marginal cost is **31,120 bytes**, not 17,327. “It costs 9%” and “the entire algebra costs 17 KB” must change.

   Also, the exported 200 m candidate has the **same raw byte count**, and about half the deflated bytes—not a quarter. The quarter-size claim applies to source cells.

6. **Medium — the claimed 15-minute peak is a consequence of checking only four thresholds.**  
   [s3-1-candidate-grids.md:69](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/experiments/s3-1-candidate-grids.md:69)

   At 14 minutes, disagreements against the centroid reference are **13,225 for 100 m and 22,794 for 200 m**. Both exceed the reported 15-minute counts, 12,935 and 22,430. The 200 m maximum over integer thresholds 1–60 is at **14 minutes**.

   **Reproducer:** R3.

   **Cost:** withdraw “the threshold most sensitive to the grid.” “Largest among the four thresholds reported” is supported. The explanation about where most structures sit near a boundary was not separately measured.

7. **Medium — fractional thresholds silently violate the stated safe direction.**  
   [wire.py:158](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/locfinder/wire.py:158), [worker.js:170](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/spikes/g3-render/worker.js:170)

   Python truncates with `int()`; JavaScript truncates with `| 0`. At **10.5 minutes**, a 610-second OK value should PASS, and a 610-second non-strict bound should remain UNKNOWN. Both decode as FAIL.

   **Reproducer:** R1 prints `FRACTIONAL surface [0, 2] wire [1, 1]`.

   **Cost:** callers outside the present slider can manufacture exclusions. The minute format cannot answer arbitrary fractional thresholds exactly; reject unsupported thresholds explicitly.

8. **Medium — the explicit-grid source transform never checks array dimensions.**  
   [export_published_layers.py:75](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/scripts/export_published_layers.py:75)

   The claimed shape check exists only in the fallback branch. The explicit branch ignores `build["nrows"]` and `build["ncols"]`.

   **Reproducer:** R1 passes `(322, 258)` against the actual 200 m build record and prints `WRONG_SHAPE_ACCEPTED`.

   **Cost:** a transposed 83,076-cell triple can pass validation and be exported under the wrong footprint. This is a missing guard; the current artifacts’ transforms are correct.

9. **Medium — the write-up promotes model disagreement into household accuracy.**  
   [s3-1-candidate-grids.md:66](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/experiments/s3-1-candidate-grids.md:66), [s3-1-candidate-grids.md:75](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/experiments/s3-1-candidate-grids.md:75)

   The centroid reference is legitimate for measuring this model’s discretization. Shared model defects do not invalidate that comparison. They do prevent interpreting its transitions as observed “wrong” household answers.

   **Reproducer:** the existing shared-model counterexample:

   ```powershell
   & v2/.venv/Scripts/python.exe -B -m pytest `
     v2/tests/test_status.py::test_a_category_surface_is_an_upper_bound_not_a_minimum_over_destinations `
     -q -s -p no:cacheprovider --basetemp="$env:TEMP/distanceFinder-pass43-status"
   ```

   **Cost:** qualify “wrongly excludes/includes” and “roughly doubles … the wrong thing” as disagreement with this model at structure centroids. Also withdraw “the saving buys nothing a household notices”: the document correctly acknowledges that device latency remains unmeasured.

**What survived the attacks**

- **Matched evaluation:** the published builder applies the same coordinate evaluator to cell centres. I found no additional cell-centre processing bypassed by `answer_at()`. All three columns share graph preparation and searches.
- **Counts and exclusions:** every reported verdict count reproduced:

  | Minutes | 100 m vs centroid | 200 m vs centroid | 200 m vs 100 m |
  |---:|---:|---:|---:|
  | 10 | 11,246 | 19,527 | 19,245 |
  | 15 | 12,935 | 22,430 | 21,998 |
  | 25 | 8,227 | 14,566 | 14,564 |
  | 45 | 3,327 | 6,097 | 5,977 |

  These are structure counts, consistently restricted by `covered`. Seconds distributions correctly disclose their smaller denominators: **498,731; 498,480; 498,461**. They omit respectively **13,902; 14,153; 14,172** structures with a non-OK side. Indexing before subtraction is correct; verdict comparisons retain those structures.

- **Population edges:** zero selected structures are outside either grid. However, the 200 m footprint contains **905 additional accepted structures** excluded by the 100 m population definition. That is an asymmetric coverage comparison, although it cannot reverse the ranking at the four reported thresholds. `structure_population` also uses the opposite north/south boundary convention from `cell_for_xy`; no selected structure hits the consequential boundary in this run.
- **Centre keys:** injective for valid indices at these grid sizes. Exhaustive reconstruction matched `cell_centers_xy()` exactly over all **330,502 and 83,076 cells**.
- **Integer decoding:** both published source surfaces agreed with `evaluate` at **every integer threshold 1–254**. Capping weakens bounds safely; `NO_PATH` remains unconditional. Neither current layer caps an OFF_NETWORK bound. A longer-horizon builder can reach the OK refusal; the current 120-minute artifacts cannot. Zero is outside `Criterion`’s accepted threshold domain.
- **Horizon authority:** the value is redundant for BEYOND_HORIZON. A wrong manifest horizon can change UNKNOWN into FAIL: a bound byte of 10 with horizon 600 is UNKNOWN at 15 minutes; the same planes with horizon 7200 are FAIL. Current exports carry the correct horizon, but the decoder does not establish their consistency.
- **`UNKNOWN_CAUSE`:** bare v1 NODATA contains no stronger per-criterion evidence. Its lift preserves INCLUDED-mask membership: unknown remains zero, including when another criterion fails. The combined three-way rendering can change UNKNOWN to EXCLUDED because of the deliberate precedence fix, so “moves no verdict” needs that qualification. I found no mask regression from the lift itself.
- **No enabled criteria:** the algebra is correct. The renderer does paint a blue sheet over all **330,502 cells** after initialization is fixed. For the map, I recommend a transparent inactive state with an empty-search message while retaining the universal INCLUDED result for algebraic consumers.
- **Harness state and window:** cache deletion creates fresh module state per group. The `(0, 0)` window really contains all produced codes—counts **31,312 OK, 7,921 OFF_NETWORK, 767 BEYOND_HORIZON**—but is simply the first matching window, not a representative sample.
- **Export placement:** the current 100 m transform matches its GeoTIFF; the 200 m transform matches its grid. Reprojection reproduced both exported planes byte-for-byte. No undefined status codes appeared.

**R1 — fast numerical reproducers**

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
@'
import sys
from pathlib import Path
import numpy as np
from pyproj import Transformer
sys.path[:0]=['v2','v2/scripts']
import export_published_layers as e
from locfinder import wire
from locfinder.status import Surface,Criterion,evaluate,CATEGORY_COST_SELECTED
from locfinder.measure.frames import structure_population

p=Path('v2/spikes/g3-render/fixtures/published')
exported=[]
for stem,_,size in e.SOURCES:
    surf,build=e.load_surface(stem)
    v=np.frombuffer((p/(stem+'.value.bin')).read_bytes(),np.uint8).reshape(514,643)
    s=np.frombuffer((p/(stem+'.status.bin')).read_bytes(),np.uint8).reshape(514,643)
    old=np.where(s==wire.OK,v,255).astype(np.uint8)
    z=lambda a:e.deflated(a.tobytes())
    print('SIZE',size,'v2',z(v)+z(s),'true_v1',z(old),
          'increase',(z(v)+z(s))/z(old)-1)
    exported.append((v,s))
    if size==100: source=surf
    if size==200:
        print('WRONG_SHAPE_ACCEPTED',e.source_transform(build,(322,258)))

a,b=[wire.outcome_planes(v,s,threshold_min=20,horizon_s=7200)
     for v,s in exported]
both=wire.combine_planes([a,b])
print('DEFAULT',int((a==0).sum()),int((both==0).sum()))

ids,pts,_=structure_population(
    Path('v2/data/triangle/overture_buildings_accepted.parquet'),e.METRO.grid())
x,y=Transformer.from_crs(e.METRO.crs,'EPSG:4326',always_xy=True).transform(
    pts[:,0],pts[:,1])
box=e.METRO.evaluation
cc=np.floor((x-box.west)/(box.east-box.west)*643).astype(int)
rr=np.floor((box.north-y)/(box.north-box.south)*514).astype(int)
k=(cc>=0)&(cc<643)&(rr>=0)&(rr<514)
g=e.METRO.grid()
sc=((pts[:,0]-g.x_min)/100).astype(int)
sr=((g.y_max-pts[:,1])/100).astype(int)
a=evaluate(Criterion('g','walk','grocery','category',900),source)[sr[k],sc[k]]
v,s=exported[0]
b=wire.outcome_planes(v,s,threshold_min=15,horizon_s=7200)[rr[k],cc[k]]
print('REGRID','inside',int(k.sum()),'omitted',int((~k).sum()),
      'changed',int((a!=b).sum()))

sf=Surface('walk','own-graph','grocery',CATEGORY_COST_SELECTED,7200,
    np.array([610.,np.inf]),np.array([0,1]),np.array([0.,610.])).validate()
v,s=wire.encode_planes(sf)
print('FRACTIONAL',
      'surface',evaluate(Criterion('g','walk','grocery','category',630),sf).tolist(),
      'wire',wire.outcome_planes(v,s,threshold_min=10.5,horizon_s=7200).tolist())
'@ | & v2/.venv/Scripts/python.exe -B -
```

**R2 — boot failure and both harness escapes, without editing files**

```powershell
@'
const fs=require('fs'),vm=require('vm'),path=require('path'),Module=require('module');
const dir=path.resolve('v2/spikes/g3-render');
const app=fs.readFileSync(path.join(dir,'app.js'),'utf8');
const start=app.indexOf('  function initWorker(');
const end=app.indexOf('\n  const maskRequestResolvers',start);
vm.runInNewContext(
  app.slice(start,end)+
  '\ninitWorker({layers:[]},[]).catch(e=>console.log("BOOT",e.message));',
  {Worker:class{postMessage(){console.log('INIT POSTED')}},state:{},console}
);

const original=Module._extensions['.js'];
Module._extensions['.js']=function(m,f){
  if(f!==path.join(dir,'worker.js')) return original(m,f);
  let src=fs.readFileSync(f,'utf8');
  src=src.replace(/case S_NO_PATH:\s*return O_FAIL;/,
                  'case S_NO_PATH: return O_UNKNOWN;');
  src=src.replace('const tEnd = performance.now();',`if(n===40000){
    mask.set(Uint8Array.from({length:n},(_,i)=>mask[(i+10007)%n]));
    px.set(Uint32Array.from({length:n},(_,i)=>px[(i+10007)%n]));
  } const tEnd = performance.now();`);
  m._compile(src,f);
};
import(require('url').pathToFileURL(
  path.join(dir,'worker_conformance.mjs')).href);
'@ | node
```

**R3 — repeat the census and find the peak across the slider range**

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
@'
import sys,json
from pathlib import Path
sys.path[:0]=['v2/scripts','v2']
import compare_candidate_grids as c

c.THRESHOLDS_MIN=tuple(range(1,61))
reports=[]
Path.write_text=lambda self,data,**kwargs: reports.append(json.loads(data))
c.print_summary=lambda report: None
c.main(['--no-write-layer'])

r=reports[0]
for key in ['cell100_against_address','cell200_against_address']:
    peak=max(r['verdicts'],key=lambda t:r['verdicts'][t][key]['moved'])
    print(key,'peak',peak,r['verdicts'][peak][key]['moved'])
    for t in ['10','14','15','25','45']:
        print(t,r['verdicts'][t][key]['moved'])
print(json.dumps(r['signed_paired_seconds'],indent=2))
'@ | & v2/.venv/Scripts/python.exe -B -
```

Codex session ID: 01a1d54d-05b1-7140-ba81-2d324eb740cd
Resume in Codex: codex resume 01a1d54d-05b1-7140-ba81-2d324eb740cd
