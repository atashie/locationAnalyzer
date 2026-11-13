**F2 is only partly repaired: decoder verdicts are now checked, but materially wrong consumer outputs still pass. F3’s new measurement is correct for the exported raster, but does not measure its placement on the browser map. The new “roughly twice” claim is false.**

Reviewed `3a86018`. During the review, HEAD advanced to `bf2df8b`; findings below refer to the requested commit. I wrote no repository files. **43 relevant tests passed**; I did not run the full suite.

1. **High — the harness still passes wrong pixels and a wrong polygon mask.**  
   [worker_conformance.mjs:121](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/spikes/g3-render/worker_conformance.mjs:121), [worker_conformance.mjs:152](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/spikes/g3-render/worker_conformance.mjs:152)

   Two independent mutations pass **all 37 checks**:

   - `px.fill(0)` immediately before returning the result makes the entire overlay transparent.
   - Writing `2` instead of `0` to excluded mask cells passes `(mask[i] === 1) === (verdicts[i] === V_INCLUDED)`. But [app.js:543](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/spikes/g3-render/app.js:543) polygonizes at threshold **0.5**, so those cells become included.

   **Cost:** the first mutation erases the displayed answer. At 15 minutes, the second promotes **225,520 excluded pixels** into the polygon’s included set.

   **Reproducer:** R1, below. Check exact mask bytes and length, and compare every RGBA pixel against the independently expected verdict and hatch position. The later pixel repair does not, by itself, establish binary mask validity.

2. **Medium — the mutation runner treats an unavailable harness as nine successful catches.**  
   [mutate_worker.mjs:102](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/spikes/g3-render/mutate_worker.mjs:102)

   Every outcome except exit status zero increments `caught`, including `status: null` with a spawn error. In this session, `spawnSync` returned **`EPERM`**, and the runner reported **“9 of 9 mutations caught”** and success.

   **Cost:** the mutation gate can be green when **zero mutated decoders ran**. Syntax errors, signals and timeouts are also counted as catches. Its diagnostic lookup additionally reads stdout, whereas the harness writes `FAIL` messages to stderr.

   **Reproducer:** R2 injects the spawn-error result without touching `worker.js`.

   I separately executed the nine original mutations in memory against the committed harness. Their ordinary failures were meaningful:

   | Failure mechanism | Mutations |
   |---|---:|
   | Cell verdict comparison | 5 |
   | Verdict digest comparison | 1 |
   | Count consistency | 2 |
   | Mask consistency | 1 |

   None required a crash, length error or `INERT` result. The no-criteria mutation first fails count consistency; fixing its counts would still leave incorrect verdicts.

   The source equality guard detects unmatched edits only. Adding `void 0;` changes the source while preserving behavior and therefore “survives”; that is not evidence of a decoder hole. None of the nine committed mutations was such a runtime no-op.

3. **Medium — the new measurement stops before MapLibre’s additional spatial transform.**  
   [measure_export_regrid.py:78](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/scripts/measure_export_regrid.py:78), [app.js:350](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/spikes/g3-render/app.js:350)

   Your arithmetic matches `rasterio.rowcol(from_bounds(...))` for **every census structure**. I also found no differences at the current grid’s edges, internal boundaries, or their adjacent floating-point values.

   The browser overlay is different. MapLibre’s canvas source inherits image-source placement, which converts corners to **Mercator coordinates**. Thus texture rows interpolate in Mercator space rather than latitude. This follows the pinned [CanvasSource](https://raw.githubusercontent.com/maplibre/maplibre-gl-js/v5.24.0/src/source/canvas_source.ts) and [ImageSource](https://raw.githubusercontent.com/maplibre/maplibre-gl-js/v5.24.0/src/source/image_source.ts) implementations.

   Before MapLibre’s corner rounding:

   - **131,571 structures** select a different row.
   - At 15 minutes, **6,866 verdict lookups** differ between the latitude raster lookup and Mercator placement.
   - Source-versus-display disagreement becomes **13,374**, versus the reported **12,098**.

   Those are analytical placement calculations, not screenshot measurements; MapLibre also rounds corner coordinates.

   **Cost:** retain **2.42%** as the source-versus-exported-raster result. Withdraw its interpretation as the complete browser spatial result. The polygon conversion’s claim that its linear latitude mapping matches canvas placement is also incorrect.

   **Reproducer:** R3.

4. **Medium — re-tiling disagreement cannot be added to source-grid disagreement.**  
   [s3-5-browser-path.md:134](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/experiments/s3-5-browser-path.md:134)

   “The shipped answer carries roughly twice the discretisation error” does not follow from two similarly sized disagreement counts. Re-tiling can correct a source-grid disagreement.

   Against the centroid model, on the **same 500,451 structures**:

   | Minutes | Source vs centroid | Export vs source | Export vs centroid |
   |---:|---:|---:|---:|
   | 10 | 11,126 | 10,759 | 13,905 |
   | 15 | 12,687 | 12,098 | **15,684** |
   | 25 | 7,990 | 7,926 | 10,428 |
   | 45 | 3,252 | 3,253 | 4,216 |

   At 15 minutes, re-tiling corrects **4,549** source-grid disagreements.

   **Cost:** replace “roughly twice” with the measured change: **2.54% → 3.13%**, approximately **24% more disagreements**, for the exported raster lookup. Browser placement remains a separate issue.

   **Reproducer:** R3’s final census calculation.

5. **Medium — the horizon “checksum” cannot establish exact horizon agreement.**  
   [worker.js:157](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/spikes/g3-render/worker.js:157), [worker.js:166](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/spikes/g3-render/worker.js:166)

   There are two limitations:

   - A matching first cell permits contradictory later cells. Values `[120,10]`, statuses `[2,2]`, horizon `7200` initialize successfully.
   - Even checking every cell cannot recover the exact horizon from a quantized byte. A valid **601-second** horizon encodes as `11`. A manifest claiming **660 seconds** passes the check, but at 11 minutes changes **UNKNOWN → EXCLUDED**. Saturation is broader: horizons `15300` and `72000` both match byte `254`, yet disagree at 300 minutes.

   **Cost:** withdraw the blanket claim that initialization refuses a horizon that disagrees with the planes. This is a limited consistency check, not an exact horizon checksum.

   **Reproducer:** R4.

   Scanning all **330,502** cells is inexpensive enough to warrant removing the `break`; it catches mixed or damaged planes. The saturation calculation itself matches `wire.encode_planes`. A layer with **no** `BEYOND_HORIZON` cells need not fail: its verdicts do not use the horizon comparison.

6. **Medium — the shape repair still ignores a known contradictory dimension when its partner is absent.**  
   [export_published_layers.py:81](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/scripts/export_published_layers.py:81)

   `None not in recorded` skips the entire guard if either dimension is missing. A build explicitly recording `nrows=258` accepts an array with **322 rows** when `ncols` is absent.

   **Cost:** a transposed **83,076-cell** plane can still be accepted under the wrong footprint after one metadata field is lost. Compare each supplied dimension independently; require complete dimensions when an explicit transform requires them.

   **Runnable reproducer:**

   ```powershell
   @'
   import sys
   sys.path[:0] = ['v2', 'v2/scripts']
   import export_published_layers as e
   build = dict(x_min=661800., y_max=4003600., cell_m=200.,
                nrows=258, crs='EPSG:32617')
   print(e.source_transform(build, (322, 258)))  # accepted
   '@ | & v2/.venv/Scripts/python.exe -B -
   ```

7. **Low — the corrected grid summary still overstates the cell saving.**  
   [s3-1-candidate-grids.md:14](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/experiments/s3-1-candidate-grids.md:14)

   “Saves four fifths” remains. The saving is **74.86%**, approximately three quarters.

   **Reproducer:** `1 - 83076 / 330502`  
   **Cost:** correct the summary’s 80% saving. Also replace “what the product ships today” at line 31 with “the source-grid answer”; the later correction explicitly establishes that distinction.

**Disposition of every pass 43 finding**

| Finding | Disposition |
|---|---|
| F1 boot `ReferenceError` | **Closes.** Initialization receives both plane arrays; the extracted initializer posts them and resolves. |
| F2 harness | **Moves.** Verdict and digest holes close; pixel and mask-consumer holes remain. |
| F3 third grid | **Narrows.** Raster re-tiling is measured correctly; browser placement remains unmeasured. |
| F4 candidate default | **Closes** for the default export. |
| F5 v1 baseline | **Closes** the byte-baseline defect. |
| F6 threshold peak | **Closes.** The sweep records peaks at 14, 14 and 13 as stated. |
| F7 fractional thresholds | **Closes** silent truncation through explicit refusal. |
| F8 explicit transform | **Narrows.** Complete dimension records are checked; incomplete ones bypass it. |
| F9 household accuracy | **Narrows.** The model-reference qualification is sound; inaccurate shipped-answer summaries remain. |
| Horizon authority note | **Narrows.** Detects some mismatches, not exact horizon agreement. |

**Claims I checked and could not break**

- `v1_plane` matches **`grid.encode_minutes(surface.seconds)` byte for byte** on the source surface. Reprojecting that actual v1 plane also matches the surrogate exported baseline byte for byte.
- **202,380 versus 171,260 bytes**, a **31,120-byte / 18.17%** increase, is correct for separate zlib streams at level 9. It is a compression benchmark, not measured HTTP transfer. The marginal increase is **33,057 bytes at level 6**, **47,090 at level 1**, and **330,502 without compression**.
- The product manifest contains one layer. `measure_export_regrid.py` does not depend on the candidate entry or candidate files. The exporter refuses an empty result before writing a manifest, and the page rejects zero layers.
- `test_export_published.py` asserts the right current product artifact, but its manifest test does not exercise CLI selection; a stale artifact could conceal a future exporter regression.
- I found no state leakage between ordinary harness groups. Cache deletion supplies fresh module state, verdict responses return copies, and send-time shims are restored.
- **“Keep 100 m” remains supported** as a choice between these two grids for preserving this model’s centroid answers. F9’s qualification does not invalidate that comparison.
- I found no existing fractional-threshold caller broken by refusal. `evaluate` has a wider contract than the wire decoder. Refusal is defensible, although conservative support is possible: for fractional minute threshold `t`, an OK byte can PASS when `m <= floor(t)`, FAIL when `m > ceil(t)`, and otherwise return UNKNOWN. OFF_NETWORK can prove failure when `m > ceil(t)`; the horizon and NO_PATH rules need no quantization-based refusal.

**R1 — both consumer-output escapes, pinned to the reviewed commit**

Run from the repository root. Each iteration reports all 37 checks passing.

```powershell
$env:REVIEW_HARNESS=(git show 3a86018:v2/spikes/g3-render/worker_conformance.mjs | Out-String)
$env:REVIEW_WORKER=(git show 3a86018:v2/spikes/g3-render/worker.js | Out-String)

foreach ($reviewMutation in @('pixels','mask')) {
  $env:REVIEW_MUTATION=$reviewMutation
  @'
const path=require('path'),M=require('module');
const {pathToFileURL}=require('url');
const dir=path.resolve('v2/spikes/g3-render');
const worker=path.join(dir,'worker.js'),load=M._extensions['.js'];
let s=process.env.REVIEW_WORKER;
s=process.env.REVIEW_MUTATION==='pixels'
 ? s.replace('const tEnd = performance.now();',
             'px.fill(0); const tEnd = performance.now();')
 : s.replace(/mask\[p\] = 0;\r?\n\s*verdict\[p\] = V_EXCLUDED;/,
             'mask[p] = 2;\n          verdict[p] = V_EXCLUDED;');
M._extensions['.js']=(m,f)=>f===worker?m._compile(s,f):load(m,f);
const h=process.env.REVIEW_HARNESS.replaceAll('import.meta.url',
 JSON.stringify(pathToFileURL(path.join(dir,'worker_conformance.mjs')).href));
import('data:text/javascript;base64,'+Buffer.from(h).toString('base64'));
'@ | node
}
```

**R2 — a failed spawn becomes “9 of 9 caught”**

This executes the committed mutation runner with in-memory file operations.

```powershell
$env:REVIEW_MUTATOR=(git show 3a86018:v2/spikes/g3-render/mutate_worker.mjs | Out-String)
$env:REVIEW_WORKER=(git show 3a86018:v2/spikes/g3-render/worker.js | Out-String)
@'
const fs=require('fs'),path=require('path'),vm=require('vm');
const {fileURLToPath,pathToFileURL}=require('url');
const dir=path.resolve('v2/spikes/g3-render'),worker=path.join(dir,'worker.js');
let current=process.env.REVIEW_WORKER;
const fakeFS={...fs,
 readFileSync:(f,...a)=>f===worker?current:fs.readFileSync(f,...a),
 writeFileSync:(f,s)=>{if(f!==worker)throw Error(f);current=s;}
};
const s=process.env.REVIEW_MUTATOR.replace(/^import .*;\r?$/gm,'')
 .replaceAll('import.meta.url',
 JSON.stringify(pathToFileURL(path.join(dir,'mutate_worker.mjs')).href));
vm.runInNewContext(s,{
 fs:fakeFS,path,fileURLToPath,console,
 spawnSync:()=>({status:null,error:Error('spawn EPERM'),stdout:'',stderr:''}),
 process:{execPath:process.execPath,exit:c=>console.log('EXIT',c)}
});
'@ | node
```

**R3 — rasterio agreement, browser-placement difference, and actual combined disagreement**

The final reference calculation rebuilds the graph evaluation and takes several minutes. It writes no output files.

```powershell
@'
import sys,json
import numpy as np
from pyproj import Transformer
from rasterio.transform import from_bounds,rowcol
sys.path[:0]=['v2','v2/scripts']
import export_published_layers as e
import compare_candidate_grids as cg
from locfinder import wire
from locfinder.status import Criterion,evaluate
from locfinder.measure.frames import structure_population

m=json.loads((e.OUT/'manifest.json').read_text())
nr,nc=m['nrows'],m['ncols']
w,s,ee,n=m['bounds_wgs84']
g=e.METRO.grid()
_,pts,_=structure_population(cg.ACCEPTED_BUILDINGS,g)
lon,lat=Transformer.from_crs(g.crs,'EPSG:4326',always_xy=True).transform(
    pts[:,0],pts[:,1])
c=np.floor((lon-w)/(ee-w)*nc).astype(int)
r=np.floor((n-lat)/(n-s)*nr).astype(int)
rr,cc=rowcol(from_bounds(w,s,ee,n,nc,nr),lon,lat)
print('rowcol differences',np.count_nonzero((r!=rr)|(c!=cc)))
k=(c>=0)&(c<nc)&(r>=0)&(r<nr)
merc=lambda a:(1-np.log(np.tan(np.pi/4+np.deg2rad(a)/2))/np.pi)/2
rm=np.floor((merc(lat)-merc(n))/(merc(s)-merc(n))*nr).astype(int)
print('different Mercator rows',np.count_nonzero(k&(r!=rm)))

sf,_=e.load_surface(e.SOURCES[0][0])
l=m['layers'][0]
v=np.frombuffer((e.OUT/l['value_file']).read_bytes(),np.uint8).reshape(nr,nc)
st=np.frombuffer((e.OUT/l['status_file']).read_bytes(),np.uint8).reshape(nr,nc)
sr=np.floor((g.y_max-pts[:,1])/100).astype(int)
sc=np.floor((pts[:,0]-g.x_min)/100).astype(int)
for t in (10,15,25,45):
    a=evaluate(Criterion('g','walk','grocery','category',t*60),sf)[sr[k],sc[k]]
    b=wire.outcome_planes(v,st,threshold_min=t,horizon_s=l['horizon_s'])
    print(t,'source/raster',np.count_nonzero(a!=b[r[k],c[k]]),
          'source/Mercator',np.count_nonzero(a!=b[rm[k],c[k]]),
          'raster/Mercator',np.count_nonzero(b[r[k],c[k]]!=b[rm[k],c[k]]))

idx,T,cost,reasons,_=cg.prepare()
adr=cg.answer_at(idx,T,cost,reasons,pts[:,0],pts[:,1])
for t in (10,15,25,45):
    a=cg.verdicts(*adr,t)[k]
    b=evaluate(Criterion('g','walk','grocery','category',t*60),sf)[sr[k],sc[k]]
    d=wire.outcome_planes(v,st,threshold_min=t,horizon_s=l['horizon_s'])[r[k],c[k]]
    print('combined',t,np.count_nonzero(a!=b),np.count_nonzero(b!=d),
          np.count_nonzero(a!=d),'corrected',np.count_nonzero((a!=b)&(a==d)))
'@ | & v2/.venv/Scripts/python.exe -B -
```

**R4 — horizon mismatches accepted**

```powershell
$env:REVIEW_WORKER=(git show 3a86018:v2/spikes/g3-render/worker.js | Out-String)
@'
const vm=require('vm');
function test(name,values,horizon,t){
 const out=[],self={postMessage:m=>out.push(m)};
 vm.runInNewContext(process.env.REVIEW_WORKER,{self,performance});
 self.onmessage({data:{type:'init',
  manifest:{encoding:'published-v2',nrows:1,ncols:values.length,
            layers:[{id:name,horizon_s:horizon}]},
  values:[Uint8Array.from(values).buffer],
  statuses:[Uint8Array.from(values.map(()=>2)).buffer]}});
 self.onmessage({data:{type:'compute',seq:1,enabled:[true],thresholds:[t]}});
 self.onmessage({data:{type:'verdicts',reqId:1}});
 console.log(name,out.map(m=>m.type==='verdicts'
  ? [...new Int8Array(m.verdicts)] : m.type));
}
test('later corrupt bound',[120,10],7200,15);
test('true horizon 601; manifest 660',[11],660,11);
test('true horizon 15300; manifest 72000',[254],72000,300);
'@ | node
```

The last two initialize successfully and return `[1]`—EXCLUDED—where the true horizons require UNKNOWN.

Codex session ID: 01a1d592-3f16-7c01-8715-d736340b8868
Resume in Codex: codex resume 01a1d592-3f16-7c01-8715-d736340b8868
