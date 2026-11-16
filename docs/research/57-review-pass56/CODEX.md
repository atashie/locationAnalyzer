# Pass 56 review — Codex

**2026-11-16. Partial execution review: W1 remains unresolved.** The hatch explanation and the three walk-layer hole measurements largely survive independent execution. The blanket dismissal of subdivision does not survive the pipeline's cost rules. Several numbers describe an input population or a source grid rather than the published product.

**This is not a completed reproduction of claims 12–15.** I could execute JavaScript, read the arrays and OSM extract, and execute the actual worker and card code. The shell runner refused to start any process:

~~~text
UnsupportedOperation("windows unelevated restricted-token sandbox cannot enforce split writable root sets directly; refusing to run unsandboxed")
~~~

An in-process Node subprocess attempt also returned `spawn EPERM`. A second attempt to start `v2/.venv/Scripts/python.exe` failed with the same shell error. Consequently I did **not** run the five Python measurement commands, pytest, the real Shapely query, or the full graph reconstruction. These are execution limitations, not evidence that their reported numerical results are false. No configuration was changed to get around the restriction.

All measurements below explicitly distinguish executed artifact checks, source inspection, and unexecuted follow-up checks. Only this review file was written. I did not read the other reviewer's output.

## What changes the product decision, in risk order

1. **Keep the full-cap candidate change unadopted, but do not treat its pricing as independently validated.** The decisive comparison with the stored surface, W1, is still missing. There is also a denominator error: 77.1% refers to comparable cells, not all cells. Validating the baseline, then measuring both original holes repaired and new holes created, should precede a decision based on that experiment.
2. **Withdraw “adding nodes would change nothing.”** The production profile adds 120 seconds of selection cost per restricted walk edge. Splitting such an edge and reapplying the profile can change the chosen route and its reported seconds. Adding a node also changes the node candidates used to attach destinations. This does not validate the owner's nearest-node explanation or establish densification as a fix.
3. **Retain a connectivity/access investigation as the next substantive investigation, with a broader question.** The named parking ways do share no node with Atlantic Avenue. That is not proof of missing OSM connectivity or permission to walk across the intervening land. The cited 33 m is the neighbouring cell's access distance; the hole's own centre is about 106 m from Atlantic Avenue. Check actual entrances, barriers, connecting ways and destination attachment, alongside network topology.
4. **Keep the defaults and label fixes.** Executing the old default behavior with the seven planes gives zero INCLUDED cells. The new opening gives 74,227. The actual card renders the label and retains its id fallback. These retire a concrete first-use failure.
5. **Correct the scope of the explanations.** UNKNOWN coverage is largely understood; the walk-hole measurements are real. But “every hole is OK,” “the whole gap is atnode,” “137 additional records would ship,” and “41 already shipped” go beyond their supporting measurements.

My recommendation is therefore close to the author's practical recommendation: **investigate before changing snapping**, while correcting the reasons given for rejecting subdivision and the claimed certainty about the parking example. “Do nothing yet” should mean no untested routing change, with these misleading explanations corrected and the baseline comparison completed. It should not mean that the present times have been shown correct.

## Per-claim verdicts

“OVERSTATED” sometimes means a demonstrated scope error and sometimes an unvalidated measurement. The evidence column says which; an environment failure does not turn a numerical claim into a counterexample.

| Claim | Verdict | Evidence |
|---|---|---|
| **1** | **CONFIRMED** | Executed the actual `worker.js` on the published planes. Every emitted grey stripe pixel checked had RGBA 60/60/60/130 and satisfied `((row + col) & 7) < 2`. At park/walk 20 there are 56,034 UNKNOWN cells, of which 14,023 receive grey ink. UNKNOWN-cell count and painted-pixel count are different quantities. |
| **2** | **CONFIRMED** | The three walk planes contain only OK, OFF_NETWORK and BEYOND_HORIZON. The manifest horizon is 7,200 s and the actual sliders offer integer 1–60 minutes. The actual worker makes BEYOND_HORIZON FAIL throughout that interval. All walk UNKNOWN cells therefore come from OFF_NETWORK. |
| **3** | **CONFIRMED, at equal thresholds** | Compared the OFF_NETWORK membership and its encoded bounds cell by cell, on both grids. Grocery versus park and school: **zero differences**. This establishes identical UNKNOWN sets for every offered threshold, not just matching counts. Different enabled criteria or different thresholds can still change the combined hatch because any FAIL wins. |
| **4** | **WRONG as an exact UNKNOWN-count plateau** | The actual worker returns 38,834 / 53,764 / 56,034 at 5 / 10 / 20, then **56,036 at 21**, flat thereafter. The maximum bound is indeed 21. The two extra UNKNOWN cells do not fall on a stripe, so the count of grey-painted cells already plateaus at 20. The explanation is substantially right; “56,034 then flat” is not exact. |
| **5** | **CONFIRMED for the UTM measurement** | Direct source-array census: 57,541/330,502 = **17.4102%** and 3,657/512,633 = **0.71338%** of buildings. At 20 minutes the source UNKNOWN count is 57,539, with the same 3,657 buildings. Published-grid saturated UNKNOWN coverage is **16.9548%**, not 17.4%. The building figure weights source cells; it is not a measurement of addresses under the reprojected browser mask. |
| **6** | **CONFIRMED on the UTM grid** | An independent direct-neighbour loop, with no roll, returns park **125**, grocery **113**, school **132** at 20. The narrow definition is implemented correctly. On the published WGS84 grid the corresponding counts are **121 / 109 / 121**. State the grid when connecting the measurement to the owner's picture. |
| **7** | **OVERSTATED** | All holes in the named walk cases are OK, including the additional walk thresholds I checked. The engineering note's unqualified sentence follows a table that includes drive: grocery/drive 5 has **353 OK + 14 NO_PATH** holes. At 10 and 15 it has 15 NO_PATH holes each. Limit the sentence to the measured walk cases. |
| **8** | **CONFIRMED** | Direct arithmetic on stored park/walk seconds at the 125 source holes: median **241.258781 s**, maximum **752.795296 s** above the eight-neighbour mean. |
| **9** | **CONFIRMED** | Direct indexing of the building-count array at those 125 source holes: **414 buildings**, **75 occupied cells**. This is 0.08076% of the building population, not a household count. |
| **10** | **OVERSTATED** | `snap.py:162` does take one nearest edge. The claim that the **whole** gap is at the endpoint contradicts the note's own decomposition. In its first example, the on-edge difference alone is **341 − 7 = 334 s**, about 32% of that pair's stored 1,050.156 s total gap. Endpoint arrival is dominant in that comparison, not exclusive. I could not independently recompute the three endpoint decompositions or establish this as the sole cause of all holes. |
| **11** | **WRONG** | Ordinary on-edge time is proportional, as claimed. The inference that subdivision cannot change this pipeline is false: profile application charges a new per-edge penalty on each restricted child; cost-selected routes can change. Destination nearest-node attachment can change too. See the explicit construction below. |
| **12** | **OVERSTATED; numerical rerun outstanding** | I did not validate 210,533, the gain quantiles, or 125→30 against the stored baseline. Independently, **77.1% is of comparable cells**: 210,533/272,961 = 77.1293%; it would be **63.7010% of the full 330,502-cell grid**. Zero slower cells is enforced by taking `minimum(candidate, cur_total)`, so it cannot establish baseline fidelity or real-world accuracy. |
| **13** | **OVERSTATED as independently established product evidence** | The grouping/minimum recovery logic survived independent generated tests; I found no indexing counterexample there. But the 90,040-cell population, 169/196 m quantiles and 1.0% fraction were not reproduced on real candidates, and depend on W1. A long straight-line leg is a valid reason for caution; this run does not certify the exact quoted price. |
| **14** | **OVERSTATED** | 125→96 would be a **23.2% net reduction in the hole count**. It does not establish that only 23.2% of the original holes were repaired: increasing inclusion can fill old holes and create new ones elsewhere. The script counts totals, not original-hole identities. The actual +50 m experiment also remains unrerun here. |
| **15** | **OVERSTATED** | A class covering 10.4% cannot explain all holes alone; that narrow conclusion is reasonable. Marginal class frequencies do not establish “no tag class explains it” causally or rule out a targeted fix. I did not reproduce 2.8×, 10.4% or 35.2%. The diagnostic also labels a node pair using its longest parallel edge, rather than necessarily the matched geometry; that deserves checking before trusting the class attribution. |
| **16** | **OVERSTATED** | Directly read the three ways from the local OSM XML: both service ways are parking aisles; Atlantic is secondary; the node-id intersection is **empty**. But the source hole centre at (365,539) is **105.94 m** from Atlantic, while its east neighbour is **33.28 m** away. The asserted 33 m proximity is misassigned. No shared node does not by itself prove a noding defect or a lawful walkable connection. I did not rerun the graph snap identifying the matched edge. |
| **17** | **CONFIRMED for the counts and correction** | Direct counts: all three drive layers **57 UTM / 39 published** NO_PATH; coffee/bike **95 / 80**; walk zero. The S0 note now explicitly corrects the former “every shipped configuration” statement, and the criteria/progress notes explicitly reference ledger instance 53. I did not independently audit the full historical “first ever shipped” assertion. |
| **18** | **CONFIRMED** | Executed actual card default helpers and actual worker with the seven published planes. Removing the new fields gives the prior thresholds 20/20/20/10/15/10/10, all enabled: **0 INCLUDED**, 49,274 UNKNOWN. Current defaults give **74,227 INCLUDED**. Absence falls back to the previous enabled/mode-threshold rules. “Blank” means no included blue region; grey UNKNOWN ink remains. |
| **19** | **CONFIRMED** | Read the parent of `9cfa6c3` directly from Git objects: old card prints `crit.layer`. Executed the current worker→card path: “Grocery shop, walk” appears, the raw id does not, and removing the label restores the id fallback. |
| **20** | **OVERSTATED** | Independent accepted-Parquet census confirms **44 + 3 + 90 = 137** Apache records in the three category inputs. The actually shipped grocery side table contains **35 Apache records**, not 41; 41 is the accepted grocery input count. The destination writer retains nodes actually selected by a published answer, so the input census does not establish exactly how many additional records would ship. The manifest really declares clearance false; holding back expansion remains justified by that declared unresolved condition. This is an artifact-count review, not a new legal clearance opinion. |

## W1: the most important requested check is still open

`measure_access_candidates.py:93` reconstructs the baseline. It never reads the stored seconds to compare them. Reading the reason plane later does not establish agreement. I could not execute the graph load and therefore cannot honestly give a divergence count, magnitude or map.

The meaningful check must report:

- agreement of the finite mask and OK status after applying the same 200 m cap and 7,200 s horizon;
- seconds differences on stored OK cells, both before and after float32 storage rounding;
- threshold-decision differences at every offered integer threshold;
- concrete row/column examples for every type of mismatch.

Do not count the expected difference between an unbounded reconstructed time and a horizon-truncated stored infinity as unexplained divergence. Do not call tiny float64-versus-float32 differences a routing failure either. Conversely, a nonzero decision difference matters even if aggregate hole counts happen to match.

The unexecuted Python block at the end instruments the existing measurement without editing it, and performs this comparison before the candidate experiment. **Until it runs, claims 12–14 remain reconstruction measurements whose product fidelity is unverified.**

## W2 and W4: separate the two index questions

**W2 is not runtime-verified here.** The code assumes row 0 of the Shapely query is the input-point index and row 1 the tree geometry index. The appended Python check deliberately uses two inputs and three tree objects, with expected pairs (0,2) and (1,0), so swapping the rows cannot accidentally pass. I have not presented its expected result as observed.

W2 does **not** directly infect claim 15: `measure_hole_edge_classes.py` uses `nearest`, not this candidate `query`. Its runtime/classification validation is a separate issue.

**W4's algorithm is sound under the stated lexsort order.** Sorting primarily by cell id, secondarily by candidate total, then selecting the first element in each cell group recovers a minimizing candidate and that same candidate's access distance. I executed 1,000 generated cases, including ties and shuffled cell ids, against a separate per-cell brute minimum: zero mismatches. This was a JavaScript implementation of the indexing algorithm, not execution of NumPy's `lexsort` or the real candidate arrays. Exact-time ties can have different access distances; the code returns the first tied candidate, not necessarily the closest tied candidate.

One population detail worth retaining in the real rerun: the claim-13 selector uses `flat_cur - winner > 60` without the “both finite” mask used for claim 12. If any formerly infinite cells acquire a finite candidate, they enter claim 13 as infinite gains. That is a conditional concern, not a measured defect in park/walk.

## W3 and W5: these checks survived

For offsets of at most one cell, wrap-around can reach a tested centre only when that centre is on the outermost row or column. Clearing that complete border removes every such centre. For an interior centre, each of its eight reads is already in bounds.

I also executed the wrapped algorithm with that border clear against a direct in-bounds implementation for **every binary mask on every 1×1 through 4×4 shape**: **74,954 masks, zero mismatches**. The real UTM counts independently agree using direct neighbours.

For W5, I compared **membership and encoded lower-bound values**, not counts. Differences between grocery and each of park/school were zero on both source and published grids. With the shared horizon and the actual status inventory, that establishes identical per-layer UNKNOWN sets across the entire slider range. It does not require an inference from equal totals.

## W6: settled counts are real; exact re-export fidelity was not completed

The actual worker executes synchronously in the harness and its response is read directly. There is no DOM settle race.

| Threshold | UTM UNKNOWN | Published UNKNOWN | Published grey stripe pixels |
|---:|---:|---:|---:|
| 5 | 39,826 | 38,834 | 9,756 |
| 10 | 55,102 | 53,764 | 13,428 |
| 15 | 57,243 | 55,752 | 13,953 |
| 20 | 57,539 | 56,034 | 14,023 |
| 21 | 57,541 | 56,036 | 14,023 |
| 30–60 | 57,541 | 56,036 | 14,023 |

The prompt's source figures 55,102 / 57,243 / 57,541 correspond to **10 / 15 / saturation**, not the published 5 / 10 / 20 sequence. Comparing those sequences term by term would add a threshold mismatch to the grid mismatch.

Both grids have 514×643 cells, but they cover different rectangles with different cell boundaries. I read the source GeoTIFF georeferencing: 100 m cells, west 661,900 m, north 4,003,500 m in UTM 17N. The published manifest instead uses the longitude/latitude rectangle [-79.2,35.7,-78.5,36.15]. Thus “same shape” does not mean “same cells,” and the independent raw-plane counts establish that the DOM figures are not invented.

**I did not complete a byte-for-byte rerun of rasterio's export.** A direct centre-projection mapping I tried disagreed with the park plane at 6,200 value bytes and 411 status bytes. An experimental scanline approximation reduced this to 87 and 3, but that experimental mapping is not the exporter and cannot certify it. These attempts are not evidence of corrupt published data; they are an explicit limit on this review. The grid distinction is real and the settled counts are confirmed, while the stronger assertion that the entire discrepancy is accounted for by the actual export still needs the rasterio rerun.

## W7: why a plain shortest-path invariance does not settle this pipeline

The source rules are explicit:

- `access.py:42` assigns restricted walk edges a 120 s penalty.
- `speeds.py:132` adds that penalty **per edge** to selection cost, keeping reported time separate.
- `snap.py:195` prorates edge **cost** when selecting the endpoint branch, as well as prorating time.
- `symmetrise` copies the edge data to a missing reverse. It does not make two child penalties add up to one parent penalty.
- The builders attach POIs to nearest **nodes**, so a retained new node also changes the attachment candidate set.

A concrete construction, with a fixed destination D and no destination re-snap, is enough:

~~~text
A -- private 140 m --> D
A -- open 175 m --> X -- open 175 m --> D
walk speed 1.4 m/s; symmetrise after profiling

Before: private time 100, cost 100 + 120 = 220
        detour time/cost 250
        selected reported time = 100 s

After retaining a midpoint M and applying the same profile:
        private A→M→D time 50 + 50 = 100
        private selection cost (50 + 120) + (50 + 120) = 340
        detour time/cost 250
        selected reported time = 250 s
~~~

I executed these cost comparisons in JavaScript; the production-Python construction is supplied below but could not be run. The counterexample follows directly from the inspected production arithmetic. It refutes the general invariance claim, not a claim that these particular 125 holes would improve under subdivision.

If instead one splits an already weighted graph and deliberately divides **both total cost and time** proportionally, holds destinations fixed, preserves both directions and geometry, and avoids changing tie choices, the ordinary invariance argument has force. Those extra conditions were missing from “would change nothing.” Reprofiling newly split restricted edges is outside that invariant.

The owner's first mechanism is still unsupported: a normal midpoint pays half the edge's physical traversal time, not a trip to a nearest vertex at full-edge cost. The note's first largest-hole example nevertheless contains a substantial **341 s on-edge leg**, so “nowhere else” was especially unwarranted there.

## Two further interpretation corrections

**A net hole-count change is not a repair count.** I executed a monotone toy mask with one existing hole. Filling that centre repairs it; adding one more included cell completes a different ring and creates a new hole. Before: one hole. After: one hole. Original holes repaired: 100%. Net reduction: 0%. Claims such as “removes 23%” need an identity comparison, even if 125→96 is reproduced exactly. Record old centres filled, old centres remaining, and newly created holes separately.

**The parking example establishes geometry and identifiers, not ground access.** I streamed the local `triangle-roads.osm` and extracted all node ids and tags for the three named ways. The parking ways contain 2 and 7 node references; Atlantic contains 18; there is no shared node id. Distances computed from those coordinates to the actual UTM cell centres are:

~~~text
hole (365,539):       parking way 461005460    5.8608 m
hole (365,539):       Atlantic 746439842     105.9362 m
east neighbour:      Atlantic 746439842      33.2790 m
~~~

These reproduce the note's 5.9 m and 33.3 m access legs while showing that they start at **different cells**. The sentence “a person walks 33 m to Atlantic Avenue” is not established for the hole. A topology-only or imagery-only observation also cannot establish walking permission.

## Artifact and commit provenance

I read Git's compressed objects directly because its executable could not start. HEAD was `5a7a5fe01db429d8ce31f93a5cd6070bd7151a6b`, the prompt/scripts commit, whose parent is `a5ff969` and grandparent `9cfa6c3`. The current worker, card and donut note match `a5ff969` ignoring checkout line endings; the candidate script matches HEAD. The local published directory was not present in the inspected HEAD tree. The runtime conclusions therefore describe the **local supplied artifacts**, rather than asserting those binaries were retrieved from the commit.

SHA-256 values for critical local inputs:

| Artifact | SHA-256 |
|---|---|
| `own_triangle_park_walk.npy` | `0af97abcb98261744870a993d3cce366b6c1b2173951fc0381d6bd513881abf2` |
| `own_triangle_park_walk_reason.npy` | `870d62c5b55fce99eb7750c7bd707dc8e983988f720511737fa9ec3bbb4ccca0` |
| accepted-place Parquet | `26ad5ea1a4fde079096aa8d9179c8c481229041762d70ca904c55811184db0b7` |
| published manifest | `ebdcae37b6e7fe85896f20d7677808ab8a024f19421ca9a712be342b963b829f` |

The park seconds/reason digests also equal their build-sidecar values.

The accepted-place licence census was executed with an in-process reader for the Parquet compact-Thrift footer, Snappy pages and dictionary/RLE columns, applying the primary/hierarchy/exclusion rules in `categories.py`. It returned:

| Input category | Places | Apache | CC0 | CDLA |
|---|---:|---:|---:|---:|
| Grocery | 550 | 41 | 26 | 483 |
| Park | 746 | 44 | 0 | 702 |
| School | 559 | 3 | 0 | 556 |
| Coffee | 678 | 90 | 5 | 583 |

The published grocery JSON independently returns **468 place records: 35 Apache, 22 CC0, 411 CDLA**. `persist_selected_destination.py:252` assigns ordinals only to nodes actually selected by a source-grid answer. Thus the 137 input records are an exposure to assess, not an established count of additional output records.

## Executed read-only harness

This harness was executed through the in-process Node tool against the workspace. It reads the real NPY and binary planes and runs the actual worker/card source; its neighbour and indexing checks are independent implementations. It neither launches subprocesses nor writes files.

To reproduce from `v2/` with a current Node version supporting `toSorted`:

~~~powershell
$reviewText = Get-Content ..\docs\research\57-review-pass56\CODEX.md -Raw
$harness = [regex]::Match($reviewText, '(?s)<!-- REVIEW_HARNESS -->\s*~~~javascript\s*(.*?)\s*~~~').Groups[1].Value
$harness | node --input-type=module -
~~~

<!-- REVIEW_HARNESS -->
~~~javascript
await (async () => {
  const fs = await import('node:fs/promises');
  const vm = await import('node:vm');
  const B = globalThis.REVIEW_V2 || '.';
  const emit = globalThis.REVIEW_EMIT || console.log;
  const read = p => fs.readFile(B + '/' + p);
  const json = async p => JSON.parse((await read(p)).toString());
  const ab = b => b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength);
  async function npy(p) {
    const b = await read('data/layers/' + p + '.npy');
    const start = b[6] === 1 ? 10 : 12;
    const len = start === 10 ? b.readUInt16LE(8) : b.readUInt32LE(8);
    const h = b.subarray(start, start + len).toString();
    const d = h.match(/'descr': '([^']+)'/)[1];
    const types = {'<f4':Float32Array, '<f8':Float64Array, '<i4':Int32Array,
      '<u4':Uint32Array, '<i8':BigInt64Array, '<u2':Uint16Array,
      '|u1':Uint8Array, '|i1':Int8Array, '|b1':Uint8Array};
    if (!types[d]) throw Error('unsupported dtype ' + d);
    return new types[d](ab(b.subarray(start + len)));
  }
  const prefix = 'spikes/g3-render/fixtures/published/';
  const manifest = await json(prefix + 'manifest.json');
  const values = await Promise.all(manifest.layers.map(async l => ab(await read(prefix+l.value_file))));
  const statuses = await Promise.all(manifest.layers.map(async l => ab(await read(prefix+l.status_file))));
  const routeFlags = await Promise.all(manifest.layers.map(async l => l.flag_file ? ab(await read(prefix+l.flag_file)) : null));
  const destinations = await Promise.all(manifest.layers.map(async l => l.dest_file ? ab(await read(prefix+l.dest_file)) : null));
  const destTables = await Promise.all(manifest.layers.map(l => l.dest_table ? json(prefix+l.dest_table) : null));
  const messages = [];
  const ctx = vm.createContext({self:{postMessage:m => messages.push(m)}, performance});
  vm.runInContext((await read('spikes/g3-render/worker.js')).toString(), ctx);
  ctx.self.onmessage({data:{type:'init',manifest,values,statuses,routeFlags,destinations,destTables}});
  if (messages.at(-1).type !== 'ready') throw Error(JSON.stringify(messages));
  const outcome = vm.runInContext('outcomeFor', ctx);
  const enc = s => Number.isFinite(s) ? Math.max(0,Math.min(254,Math.ceil(s/60))) : 255;
  const n = manifest.nrows * manifest.ncols;
  function compute(thresholds,enabled) {
    messages.length=0;
    ctx.self.onmessage({data:{type:'compute',seq:1,thresholds,enabled,tEvent:0}});
    const m=messages.at(-1);
    if (m.type !== 'result') throw Error(JSON.stringify(m));
    return m;
  }
  const published=[];
  for (const t of [5,10,15,20,21,30,60]) {
    const m=compute(manifest.layers.map(()=>t),manifest.layers.map((_,i)=>i===1));
    const rgba=new Uint8Array(m.rgba);
    let stripes=0,bad=0;
    for(let i=0;i<n;i++) if(rgba[4*i+3]===130) {
      stripes++;
      if(rgba[4*i]!==60 || rgba[4*i+1]!==60 || rgba[4*i+2]!==60 ||
         ((Math.floor(i/manifest.ncols)+i%manifest.ncols)&7)>=2) bad++;
    }
    published.push({t,unknown:m.nodataCount,stripes,bad});
  }
  emit({publishedPark:published});
  const L={};
  for (const m of manifest.layers) L[m.id]={
    sec:await npy(m.id),reason:await npy(m.id+'_reason'),lower:await npy(m.id+'_min_possible_s')};
  const buildings=await npy('own_triangle_buildings_per_cell');
  emit({totalBuildings:Array.from(buildings).reduce((a,b)=>a+Number(b),0)});
  const source=[];
  const grocery=L.own_triangle_grocery_walk;
  const identity=[];
  for(let k=0;k<3;k++) {
    const m=manifest.layers[k], l=L[m.id];
    let ud=0,pd=0;
    const s0=new Uint8Array(statuses[0]),sk=new Uint8Array(statuses[k]);
    const v0=new Uint8Array(values[0]),vk=new Uint8Array(values[k]);
    for(let i=0;i<n;i++) {
      if((l.reason[i]===1)!==(grocery.reason[i]===1) ||
         (l.reason[i]===1 && enc(l.lower[i])!==enc(grocery.lower[i]))) ud++;
      if((sk[i]===1)!==(s0[i]===1) || (sk[i]===1 && vk[i]!==v0[i])) pd++;
    }
    identity.push({layer:m.category,sourceOffOrBoundDiff:ud,publishedOffOrBoundDiff:pd});
  }
  emit({identity});
  for(const t of [5,10,15,20,21,30,60]) {
    let cells=0,b=0;
    for(let i=0;i<n;i++) if(outcome(grocery.reason[i],enc(grocery.reason[i]===0?grocery.sec[i]:grocery.lower[i]),t,7200)===2) {
      cells++; b+=Number(buildings[i]);
    }
    source.push({t,cells,buildings:b});
  }
  emit({sourceWalk:source});
  function holes(p,f,R=manifest.nrows,C=manifest.ncols) {
    const out=[];
    for(let r=1;r<R-1;r++) for(let c=1;c<C-1;c++) {
      const i=r*C+c;
      if(!f[i]) continue;
      let all=true;
      for(let dr=-1;dr<=1;dr++) for(let dc=-1;dc<=1;dc++)
        if((dr||dc) && !p[(r+dr)*C+c+dc]) all=false;
      if(all)out.push(i);
    }
    return out;
  }
  const holeRows=[];
  for(const [id,threshold] of [['park_walk',20],['grocery_walk',20],['school_walk',20],['grocery_drive',5]]) {
    const l=L['own_triangle_'+id];
    const o=Uint8Array.from(l.reason,(s,i)=>outcome(s,enc(s===0?l.sec[i]:l.lower[i]),threshold,7200));
    const ids=holes(o.map(v=>v===0?1:0),o.map(v=>v===1?1:0));
    const gaps=ids.filter(i=>Number.isFinite(l.sec[i])).map(i=>{
      let sum=0;
      for(let dr=-1;dr<=1;dr++)for(let dc=-1;dc<=1;dc++)if(dr||dc)sum+=l.sec[i+dr*manifest.ncols+dc];
      return l.sec[i]-sum/8;
    }).sort((a,b)=>a-b);
    const mid=(gaps.length-1)/2;
    holeRows.push({id,threshold,holes:ids.length,
      statusCounts:ids.reduce((a,i)=>(a[l.reason[i]]=(a[l.reason[i]]||0)+1,a),{}),
      medianGap:(gaps[Math.floor(mid)]+gaps[Math.ceil(mid)])/2,maxFiniteGap:gaps.at(-1),
      buildings:ids.reduce((b,i)=>b+Number(buildings[i]),0),occupied:ids.filter(i=>buildings[i]>0).length});
  }
  emit({holes:holeRows});
  emit({noPath:manifest.layers.map((m,k)=>({id:m.id,
    source:Array.from(L[m.id].reason).filter(s=>s===3).length,
    published:Array.from(new Uint8Array(statuses[k])).filter(s=>s===3).length}))});
  const card=vm.createContext({});
  vm.runInContext((await read('spikes/g3-render/card.js')).toString(),card);
  const old=manifest.layers.map(l=>{const x={...l};delete x.default_on;delete x.default_threshold_min;return x;});
  const opening=compute(manifest.layers.map(l=>card.G3Card.layerOpeningThreshold(l)),manifest.layers.map(l=>card.G3Card.layerOpensOn(l)));
  const legacy=compute(old.map(l=>card.G3Card.layerOpeningThreshold(l)),old.map(l=>card.G3Card.layerOpensOn(l)));
  emit({defaultIncluded:opening.inCount,legacyIncluded:legacy.inCount,legacyUnknown:legacy.nodataCount});
  compute(manifest.layers.map(l=>l.default_threshold_min),manifest.layers.map(l=>l.default_on));
  messages.length=0;
  ctx.self.onmessage({data:{type:'explainAt',reqId:1,row:356,col:395}});
  const e=messages.at(-1),html=card.G3Card.renderCardHTML(e);
  const fallback=card.G3Card.renderCardHTML({...e,criteria:e.criteria.map(c=>({...c,label:undefined}))});
  emit({cardLabel:e.criteria[0].label,labelRendered:html.includes('Grocery shop, walk'),
    idRendered:html.includes('own_triangle_grocery_walk'),fallbackIdRendered:fallback.includes('own_triangle_grocery_walk')});
  const licenceCounts={};
  for(const t of destTables.filter(Boolean)) for(const d of t.destinations) for(const p of d.places)
    licenceCounts[p.licence]=(licenceCounts[p.licence]||0)+1;
  emit({shippedTableLicences:licenceCounts});
  let masks=0,mismatches=0;
  for(let R=1;R<=4;R++)for(let C=1;C<=4;C++)for(let bits=0;bits<2**(R*C);bits++) {
    const p=Uint8Array.from({length:R*C},(_,i)=>(bits>>i)&1),wrapped=[];
    for(let r=0;r<R;r++)for(let c=0;c<C;c++) {
      let all=true;
      for(let dr=-1;dr<=1;dr++)for(let dc=-1;dc<=1;dc++)
        if((dr||dc)&&!p[((r+dr+R)%R)*C+(c+dc+C)%C])all=false;
      if(r===0||r===R-1||c===0||c===C-1)all=false;
      if(all&&!p[r*C+c])wrapped.push(r*C+c);
    }
    if(JSON.stringify(wrapped)!==JSON.stringify(holes(p,p.map(v=>1-v),R,C)))mismatches++;
    masks++;
  }
  emit({wraparoundMasks:masks,mismatches});
  let seed=0x12345678,winnerMismatch=0;
  const rnd=()=>{seed=(1664525*seed+1013904223)>>>0;return seed/2**32;};
  for(let test=0;test<1000;test++) {
    const pairs=Array.from({length:50},(_,j)=>({pi:Math.floor(rnd()*10),total:Math.floor(rnd()*10),acc:rnd()*200,j}));
    const sorted=pairs.toSorted((a,b)=>a.pi-b.pi||a.total-b.total||a.j-b.j),picked=new Map(),brute=new Map();
    for(const p of sorted)if(!picked.has(p.pi))picked.set(p.pi,p);
    for(const p of pairs)if(!brute.has(p.pi)||p.total<brute.get(p.pi).total)brute.set(p.pi,p);
    for(const [i,p] of brute)if(p.acc!==picked.get(i).acc)winnerMismatch++;
  }
  emit({winnerCases:1000,winnerMismatch,numpyExecuted:false});
  emit({subdivisionArithmetic:{beforeCost:100+120,beforeTime:100,
    splitRestrictedCost:50+120+50+120,openDetourCost:250,afterTime:250},productionPythonExecuted:false});
})();
~~~

## Remaining Python checks — supplied, not executed

This is a follow-up command, **not an observed result**. Run from `v2/` once process execution works. It checks W2 on deliberately asymmetric indices, executes the actual production functions for the subdivision construction, tests the real NumPy winner indexing on a small fixture, and instruments the existing candidate script for W1. It writes no artifacts.

~~~powershell
@'
import importlib.util
import json
import pathlib
import sys
import numpy as np
import networkx as nx
import shapely
from locfinder.grid import encode_minutes
from locfinder.traveltime.arrival import arrival_seconds, arrival_seconds_two_weight
from locfinder.traveltime.csr import graph_to_cost_time_csr
from locfinder.traveltime.snap import EdgeIndex, _snap_network
from locfinder.traveltime.speeds import add_travel_times, symmetrise, access_speed_mps

# W2: row orientation cannot pass accidentally when input/tree sizes differ.
tree = shapely.STRtree(shapely.points([10., 20., 30.], [0., 0., 0.]))
pts = shapely.points([30., 10.], [0., 0.])
pairs = tree.query(pts, predicate="dwithin", distance=0.01)
print("W2 pairs:", pairs.tolist(), flush=True)
assert set(map(tuple, pairs.T.tolist())) == {(0, 2), (1, 0)}

# W4: actual NumPy lexsort, interleaved groups and a tie.
pi = np.array([2, 0, 2, 0, 1, 1])
tot = np.array([9., 7., 3., 4., 5., 5.])
acc = np.array([90., 70., 30., 40., 50., 60.])
order = np.lexsort((tot, pi))
first = np.ones(len(pi), dtype=bool)
first[1:] = pi[order][1:] != pi[order][:-1]
got = np.full(3, np.nan)
got[pi[order][first]] = acc[order][first]
print("W4 recovered access:", got.tolist(), flush=True)
assert got.tolist() == [40., 50., 30.]

# W7: split before profiling; same destination; same physical path lengths.
# The open detour has actual geometry matching its assigned 175 m legs.
def subdivision_case(split):
    G = nx.MultiDiGraph()
    G.graph["crs"] = "EPSG:32617"
    xy = {"A": (0., 0.), "D": (140., 0.),
          "X": (70., (175.**2 - 70.**2)**0.5)}
    if split:
        xy["M"] = (70., 0.)
    for node, (x, y) in xy.items():
        G.add_node(node, x=x, y=y)
    if split:
        G.add_edge("A", "M", length=70., highway="service",
                   access="private", osmid=1)
        G.add_edge("M", "D", length=70., highway="service",
                   access="private", osmid=1)
    else:
        G.add_edge("A", "D", length=140., highway="service",
                   access="private", osmid=1)
    G.add_edge("A", "X", length=175., highway="residential", osmid=2)
    G.add_edge("X", "D", length=175., highway="residential", osmid=3)
    G = symmetrise(add_travel_times(G, mode="walk"))
    cost, time, index = graph_to_cost_time_csr(G)
    dest = [index["D"]]
    T = arrival_seconds_two_weight(cost, time, dest_idx=dest)
    D = arrival_seconds(cost, dest_idx=dest)
    idx = EdgeIndex.from_graph(G, index)
    snap = _snap_network(idx, T, np.array([0.]), np.array([0.]), node_cost=D)
    return float(D[index["A"]]), float(snap.network[0])
print("W7 unsplit (cost, reported):", subdivision_case(False), flush=True)
print("W7 split   (cost, reported):", subdivision_case(True), flush=True)

# W1: hook the baseline call; let the rest of the original experiment run.
path = pathlib.Path("scripts/measure_access_candidates.py")
spec = importlib.util.spec_from_file_location("review_pass56_candidates", path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
original_snap = m._snap_network

def checked_snap(idx, T, x, y, *, node_cost):
    cur = original_snap(idx, T, x, y, node_cost=node_cost)
    raw = cur.network + cur.access_m / access_speed_mps("walk")
    raw = np.where(cur.access_m <= m.MAX_ACCESS_M, raw, np.inf)
    stem = m.LAYERS / "own_triangle_park_walk"
    stored = np.load(str(stem) + ".npy").astype(np.float64).ravel()
    reason = np.load(str(stem) + "_reason.npy").ravel()
    build = json.loads(pathlib.Path(str(stem) + "_build.json").read_text())
    horizon = float(build["horizon_s"])
    canonical = np.where(raw <= horizon, raw, np.inf).astype(np.float32).astype(np.float64)
    finite_diff = np.isfinite(canonical) != np.isfinite(stored)
    status_diff = np.isfinite(canonical) != (reason == 0)
    exact_diff = canonical != stored
    both_ok = (reason == 0) & np.isfinite(raw) & np.isfinite(stored)
    err = np.abs(raw[both_ok] - stored[both_ok])
    print("W1 finite-mask disagreements:", int(finite_diff.sum()), flush=True)
    print("W1 reconstructed finite vs stored OK:", int(status_diff.sum()), flush=True)
    print("W1 float32 canonical seconds disagreements:", int(exact_diff.sum()), flush=True)
    print("W1 raw seconds abs error p50/p99/max:",
          np.percentile(err, [50, 99]).tolist() + [float(err.max())] if err.size else [],
          flush=True)
    bad = np.flatnonzero(exact_diff | status_diff)
    cols = m.GRID.ncols
    print("W1 first mismatches:",
          [(int(i // cols), int(i % cols), int(reason[i]),
            float(stored[i]), float(raw[i]), float(canonical[i])) for i in bad[:20]],
          flush=True)
    changed_any = np.zeros(stored.shape, dtype=bool)
    changes = {}
    stored_v, rebuilt_v = encode_minutes(stored), encode_minutes(canonical)
    for threshold in range(1, 61):
        old = (reason == 0) & (stored_v <= threshold)
        new = np.isfinite(canonical) & (rebuilt_v <= threshold)
        delta = old != new
        changed_any |= delta
        changes[threshold] = int(delta.sum())
    print("W1 changed decisions by threshold:", changes, flush=True)
    print("W1 cells with any slider disagreement:", int(changed_any.sum()), flush=True)
    return cur

m._snap_network = checked_snap
sys.argv = [str(path), "--target", "park", "--mode", "walk", "--thresholds", "20"]
m.main()
'@ | .\.venv\Scripts\python.exe -
~~~

The remaining hole-class command is still needed for claim 15:

~~~powershell
.\.venv\Scripts\python.exe scripts\measure_hole_edge_classes.py --target park --mode walk --threshold 20
~~~

A rasterio re-export comparison should be done in memory, rather than invoking an exporter that overwrites the supplied bundle. This review intentionally leaves those missing executions visible; it does not substitute the candidate script's own output for independent confirmation of its baseline.
