# Codex adversarial review, pass 49 — the report

The prompt is `../50-codex-review-pass49-prompt.md`. **This pass ran read-only**, for the reason
recorded in `docs/engineering-notes/reference-codex-runtime-quirks.md`: Codex's Windows sandbox
cannot start a process on this machine at all. So the reviewer read the repository and executed
JavaScript through its `node_repl` MCP tool, which is enough to drive `worker.js` and replay the
whole conformance harness in memory. It ran no Python, no pytest and no graph load; its Python
reproducers are marked unexecuted where they are. It wrote the report to stdout rather than to a
file, and this file is that output verbatim.

It reports **11 findings, 3 of them High**, and one of those is a release blocker that nothing in
my own suite could see: the shipped destination table is not valid JSON, so the page cannot finish
loading it. The conformance fixtures are synthetic and never parse the real exported table.

Two questions in the prompt were ones I had already answered in `b37ed59` before the report
landed — the destination tie control (finding 8) and the vacuous `or True` assertion (inside
finding 5). The reviewer read `4685158`, so its answers there are confirmations, and in both cases
it goes further than I did.

---

**The two-directional invariant is unsound as a proof of common source-cell provenance.** It is sound as a completeness check under the stated contract; I found no legitimate `DEST_NONE` beside `OK` when a layer promises complete destination naming.

There is also a concrete release blocker: **the shipped destination table is invalid JSON, so the page cannot finish loading it.**

I executed JavaScript through `node_repl`, including the full conformance harness in VM contexts. Baseline: **71 checks passed**. All **30 supplied mutations were caught**, with no inert edits. I could not execute Python, pytest, Git, Rasterio, or a phone/browser benchmark. No files were changed.

The JavaScript reproducers below share this setup, runnable in `node_repl` without starting a process:

```js
var fs = await import("node:fs");
var path = await import("node:path");
var vm = await import("node:vm");
var crypto = await import("node:crypto");
var D = String.raw`C:\Users\arikt\documents\github\distanceFinder\v2\spikes\g3-render`;
var read = p => fs.readFileSync(path.join(D, p), "utf8");
var bytes = p => {
  var b = fs.readFileSync(path.join(D, p));
  return b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength);
};
var source = read("worker.js");
var vectors = JSON.parse(read("fixtures/conformance/vectors.json"));

var loadWorker = s => {
  var out = [];
  var ctx = vm.createContext({
    performance, ArrayBuffer, Uint8Array, Uint16Array, Uint32Array, Int8Array,
    self: { postMessage: m => out.push(m) }
  });
  vm.runInContext(s, ctx);
  return {
    send(m) {
      out.length = 0;
      ctx.self.onmessage({data:m});
      var err = out.find(x => x.type === "error");
      if (err) throw Error(err.message);
      return out.slice();
    }
  };
};

var fixtureInit = g => ({
  type: "init",
  manifest: {
    nrows:g.nrows, ncols:g.ncols, encoding:vectors.encoding,
    destination_plane_byte_order:vectors.destination_plane_byte_order,
    layers:structuredClone(g.layers)
  },
  values:g.layers.map(l => bytes("fixtures/conformance/" + l.value_file)),
  statuses:g.layers.map(l => bytes("fixtures/conformance/" + l.status_file)),
  destinations:g.layers.map(l => l.dest_file
    ? bytes("fixtures/conformance/" + l.dest_file) : null),
  destTables:structuredClone(g.dest_tables)
});

var replay = s => {
  var logs = [], exitCode;
  var h = read("worker_conformance.mjs")
    .replace(/^import .*;\r?\n/gm, "")
    .replace("const require = createRequire(import.meta.url);", "")
    .replace("const __dirname = path.dirname(fileURLToPath(import.meta.url));", "")
    .replace(
      /function loadWorker\(\) \{[\s\S]*?\r?\n\}\r?\n\r?\nfunction planeBytes/,
      "function loadWorker() { return factory(workerSource); }\n\nfunction planeBytes"
    );
  vm.runInNewContext(h, {
    fs, path, __dirname:D, createHash:crypto.createHash,
    factory:loadWorker, workerSource:s,
    ArrayBuffer, Uint8Array, Uint16Array, Uint32Array, Int8Array, Buffer,
    console:{log:(...a)=>logs.push(a.join(" ")),
             error:(...a)=>logs.push(a.join(" "))},
    process:{exit:c=>exitCode=c}
  }, {timeout:30000});
  return {
    exitCode,
    passes:logs.filter(x=>x.startsWith("PASS")).length,
    failures:logs.filter(x=>x.startsWith("FAIL"))
  };
};

var swapGroup = vectors.groups.find(g => /survive a byte swap/.test(g.name));
```

**1. High — valid destinations can be exchanged while every invariant and aggregate survives.**

Locations: [export_published_layers.py:313](C:/Users/arikt/documents/github/distanceFinder/v2/scripts/export_published_layers.py:313), [wire.py:229](C:/Users/arikt/documents/github/distanceFinder/v2/locfinder/wire.py:229).

On the shipped grid, I exchanged destinations at flattened cells **7** and **112**:

| Cell | Original `(minutes, status, destination)` | Mutated |
|---|---|---|
| 7 | `(120, OK, 240)` | `(120, OK, 17)` |
| 112 | `(71, OK, 17)` | `(71, OK, 240)` |

The worker accepted initialization and returned both substituted destinations. **258,684 OK cells, 258,684 named cells, 425 distinct destinations, and zero named/status disagreement all remain unchanged.** Two journeys are now misidentified.

Executed reproducer; the `NaN` normalization is explicitly necessary to bypass finding 2 for this independent experiment:

```js
var manifest = JSON.parse(read("fixtures/published/manifest.json"));
var tableText = read("fixtures/published/" + manifest.layers[0].dest_table);
var table = JSON.parse(tableText.replace(/\bNaN\b/g, "null"));
var init = {
  type:"init", manifest,
  values:manifest.layers.map(l=>bytes("fixtures/published/"+l.value_file)),
  statuses:manifest.layers.map(l=>bytes("fixtures/published/"+l.status_file)),
  routeFlags:manifest.layers.map(l=>bytes("fixtures/published/"+l.flag_file)),
  destinations:manifest.layers.map(l=>bytes("fixtures/published/"+l.dest_file)),
  destTables:[table]
};
var d = new DataView(init.destinations[0]);
var a = d.getUint16(7*2,true), b = d.getUint16(112*2,true);
d.setUint16(7*2,b,true);
d.setUint16(112*2,a,true);
var w = loadWorker(source);
console.log(w.send(init)); // ready
w.send({type:"compute",seq:1,enabled:[true],thresholds:[254]});
console.log(w.send({type:"destinationAt",row:0,col:7}));
console.log(w.send({type:"destinationAt",row:0,col:112}));
```

Withdraw the claim that the invariant proves a common source cell. It establishes equality of the **answer-presence masks**, and does not inspect the value plane at all. Jointly reprojecting a source-cell identifier and verifying all outputs against that identifier would address provenance.

There is a related source-only weakness at [persist_selected_destination.py:259](C:/Users/arikt/documents/github/distanceFinder/v2/scripts/persist_selected_destination.py:259): the new computation is stamped with a fingerprint of the **existing on-disk surface**, without establishing that its recomputed journey times match that surface. This can bless a fresh destination computation against stale published seconds. I could not execute that Python build path.

For route flags, `CLEAR` beside `OK` **does assert that the selected route uses no restricted way**; “asserts nothing” is inaccurate there. What is absent is an independent witness to verify that assertion. There is no valid reverse implication `OK ⇒ RESTRICTED`.

**2. High — the published table’s 85 bare `NaN` values prevent page initialization.**

Locations: [published table:223](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/fixtures/published/own_triangle_grocery_walk.destinations.json:223), [persist_selected_destination.py:89](C:/Users/arikt/documents/github/distanceFinder/v2/scripts/persist_selected_destination.py:89), [app.js:186](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/app.js:186).

Executed:

```js
var raw = read(
  "fixtures/published/own_triangle_grocery_walk.destinations.json"
);
console.log((raw.match(/\bNaN\b/g)||[]).length); // 85
JSON.parse(raw); // SyntaxError: Unexpected token 'N'
```

Missing `operating_status` values survive as floating-point NaNs. Python’s default `json.dumps` writes them; the exporter preserves them; `Response.json()` rejects them.

**Cost:** the declared destination feature blocks the entire fixture-loading operation before worker initialization. The passing synthetic conformance tests do not exercise the shipped side table.

Normalize missing scalar values to `None`, serialize with `allow_nan=False`, and parse the actual exported table with JavaScript during verification.

**3. High — the licence block omits required redistribution material.**

Location: [persist_selected_destination.py:222](C:/Users/arikt/documents/github/distanceFinder/v2/scripts/persist_selected_destination.py:222).

The exported table contains **411 CDLA**, **35 Apache**, and **22 CC0** place records. It carries licence identifiers and an Overture release label, but no accompanying licence texts or Foursquare notice. The published directory contains only the manifest and data files.

Executed artifact inspection:

```js
var t = JSON.parse(raw.replace(/\bNaN\b/g,"null"));
console.log(t.licence);
console.log(fs.readdirSync(path.join(D,"fixtures/published")));
console.log(t.destinations.flatMap(e=>e.places).reduce((a,p)=>
  (a[p.licence]=(a[p.licence]||0)+1,a),{}));
```

CDLA-Permissive-2.0 §2.1 requires making the **agreement text available with shared data**. An SPDX label alone does not do that. This is more specific than the report’s “attribution and notice” explanation. [CDLA licence](https://cdla.dev/permissive-2-0/)

Apache §4 requires recipients to receive the licence and applicable notices. Overture identifies Foursquare’s Apache data and links its `NOTICE.txt`. [Apache licence](https://www.apache.org/licenses/LICENSE-2.0), [Overture Places attribution](https://docs.overturemaps.org/attribution/#places)

**Cost:** “publishable with attribution” has not been implemented as an adequate redistribution package. Add the actual required texts/notices and source attribution to the exported bundle.

**4. Medium — separate filenames do not establish the claimed ODbL boundary, and decision 17 does not require this separation.**

Locations: [destination-identity.md:78](C:/Users/arikt/documents/github/distanceFinder/docs/engineering-notes/project-phase1-s3-destination-identity.md:78), [persist_selected_destination.py:226](C:/Users/arikt/documents/github/distanceFinder/v2/scripts/persist_selected_destination.py:226).

ODbL distinguishes collective and derivative databases by their substantive relationship and independence, not by counting files. A shared manifest does not automatically make everything one derivative database; separate files do not automatically establish independence either. ODbL also distinguishes rights in database contents from rights in the database. [ODbL definitions, §§2.4 and 4.5](https://opendatacommons.org/licenses/odbl/1-0/)

The repository’s decision 17 explicitly permits OSM-derived and Overture-derived data **in the same tables**, provided the notices travel with them.

Runnable inspection:

```js
console.log(fs.readFileSync(path.resolve(
  D,"../../../docs/plans/2026-11-03-v2-rethink-decisions.md"
),"utf8").split("\n").slice(50,55).join("\n"));
console.log(t.licence.why_it_is_a_separate_artifact);
```

**Cost:** withdraw “keeping the table apart is what stops” share-alike applying, and “without having to argue about derivative-database boundaries.” Separate packaging is useful organization; it is not the claimed legal determination. This does **not** establish that the permissive names cannot be published.

**5. Medium — four destination defects survive the entire harness; the fixture-shape guard is partly vacuous.**

Locations: [worker_conformance.mjs:234](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/worker_conformance.mjs:234), [test_browser_conformance.py:95](C:/Users/arikt/documents/github/distanceFinder/v2/tests/test_browser_conformance.py:95).

These executed mutations each returned **exit 0, 71 passes**:

```js
console.log(replay(source.replace(
  "places: entry.places,",
  "places: entry.places.map((p,i)=>i ? {...p,name:'WRONG'} : p),"
)));
console.log(replay(source.replace(
  "places: entry.places,",
  "places: entry.places.map(()=>entry.places[0]),"
)));
console.log(replay(source.replace(
  "nodeIndex: entry.node_index,", "nodeIndex: 999999,"
)));
console.log(replay(source.replace(
  "if (named && statuses[k][p] !== S_OK) {", "if (false) {"
)));
```

The harness checks only the **first place’s name**, plus array length and count. Thus duplicating the first place preserves the count while destroying the set. `nodeIndex` is never compared. Removing the **named ⇒ OK** half of the invariant also survives: the refusal suite lacks that destination case.

**Cost:** full-set identity, destination-node identity, and half of the advertised invariant are unprotected by these checks. These are absent from the supplied mutation inventory.

`assert A != B or True` is indeed vacuous. Moreover, different tables do not establish different per-cell ordinals. Replace it with assertions over decoded fixture planes that demonstrate:

- A queried cell with both layers naming different ordinals.
- A cell with different OK/non-OK membership between layers.
- Distinct expected table entries at a shared ordinal.

Compare complete place records, or canonical sets of stable place IDs and names, and assert `nodeIndex`. The adjacent `any(destination_at)` assertion does not establish the status divergence described by its comment.

Both regex-anchored destination mutations currently hit their intended statements. Their observed failures match their stated defects. The endian mutation’s first failure is a bounds rejection, addressed next.

**6. Medium — the endian positive control can report success without performing an endian mutation.**

Locations: [byteswap_control.mjs:76](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/byteswap_control.mjs:76), [worker_conformance.mjs:234](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/worker_conformance.mjs:234).

On the current source, the control correctly observes `1 ↔ 256` and wrong names. But it never requires a correct baseline, a changed mutation, or the expected swapped ordinals.

I reformatted the little-endian expression so its replacement became inert, then introduced an unrelated wrong-name defect. **The actual control still exited 0 and printed `CONFIRMED`.**

Executed reproducer:

```js
var control = read("byteswap_control.mjs").replace(/^import .*;\r?\n/gm,"");
var unrelated = source
  .replace(
    "out[i] = bytes[2 * i] | (bytes[2 * i + 1] << 8);",
    "out[i] = (bytes[2 * i]) | (bytes[2 * i + 1] << 8);"
  )
  .replace(
    "places: entry.places,",
    "places: entry.places.map(p=>({...p,name:'WRONG'})),"
  );
var logs=[], exitCode;
vm.runInNewContext(control,{
  fs:{readFileSync:(p,e)=>String(p).endsWith("worker.js")
    ? unrelated : fs.readFileSync(p,e)},
  path,vm,performance,ArrayBuffer,Uint8Array,Uint16Array,Uint32Array,Int8Array,
  console:{log:(...a)=>logs.push(a.join(" "))},
  process:{exit:c=>exitCode=c}
});
console.log(exitCode,logs.at(-1)); // 0, CONFIRMED...
```

Additionally, the main harness’s byte-swap group fails first on **`ordinal 256, expected 1`**, before comparing a name. Its ordinal assertion already catches this mutation.

**Cost:** withdraw “the name comparison is the only thing that catches a big-endian read.” The control demonstrates a wrong-name consequence on today’s source; it does not establish that causal claim or protect itself against an unrelated failure.

**7. Medium — missing byte-order declarations are accepted despite the published refusal rule.**

Location: [worker.js:196](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/worker.js:196).

Executed:

```js
var x=fixtureInit(swapGroup);
delete x.manifest.destination_plane_byte_order;
for(var buf of x.destinations) {
  var b=new Uint8Array(buf);
  for(var p=0;p<b.length;p+=2)
    [b[p],b[p+1]]=[b[p+1],b[p]];
}
var w=loadWorker(source);
console.log(w.send(x)); // ready
w.send({type:"compute",seq:1,enabled:[true],thresholds:[10]});
console.log(w.send({type:"destinationAt",row:0,col:0}));
// ordinal 256 / S Shop 256, expected 1 / S Shop 1
```

**Cost:** two in-range destinations are silently exchanged in this fixture.

A documented little-endian default is defensible. It contradicts the current manifest/specification language saying an unconfirmed order **must be refused**. Choose one contract and test it. Requiring the field still cannot detect bytes that are incorrectly labelled little-endian.

**8. Medium — the destination tie measurement leaves the positive control behind.**

Locations: [persist_selected_destination.py:204](C:/Users/arikt/documents/github/distanceFinder/v2/scripts/persist_selected_destination.py:204), [persist_selected_destination.py:330](C:/Users/arikt/documents/github/distanceFinder/v2/scripts/persist_selected_destination.py:330), [measure_tie_flag.py:118](C:/Users/arikt/documents/github/distanceFinder/v2/scripts/measure_tie_flag.py:118).

The destination path neither imports nor calls the flag control. More fundamentally, that control has **one destination, `[0]`**. It exercises competing routes to one destination and cannot demonstrate detection of a changed destination.

**The zero is worthless as controlled evidence that destination selection is well defined.** It remains a recorded observation under three permutations. Even a functioning control would not turn three permutations into proof that no exact ties exist.

Unexecuted Python reproducer/proposed positive control, run from `v2`:

```python
import inspect
import numpy as np
from scipy.sparse import csr_matrix
from scripts import persist_selected_destination as p

assert "control(" not in inspect.getsource(p.measure_destination_ties)

# Two distinct, equally costly destinations, unlike the flag control.
m = csr_matrix(np.array([
    [0., 0., 1.],
    [0., 0., 1.],
    [1., 1., 0.],
]))
seconds, selected = p.arrival_with_selected_destination(
    m, m, dest_idx=[0, 1])
report = p.measure_destination_ties(m, m, [0, 1], selected, seconds)
print(report)
assert report["total_destination_moves"] > 0
```

**Cost:** withdraw the artifact’s assertion that zero means exact destination ties do not occur. Gate the real measurement on a destination-specific positive control.

**9. Medium — the cost report mixes grids, reports the wrong bundle total, and overstates the RLE requirement.**

Locations: [price_destination_encodings.py:92](C:/Users/arikt/documents/github/distanceFinder/v2/scripts/price_destination_encodings.py:92), [price_destination_encodings.py:157](C:/Users/arikt/documents/github/distanceFinder/v2/scripts/price_destination_encodings.py:157), [worker.js:332](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/worker.js:332).

The script prices the **source raster**, while taking value/status/flag costs from the **reprojected published bundle**. It then adds the *cheapest* destination encoding when reporting “bundle with the destination plane.”

Executed arithmetic:

```js
var cost=JSON.parse(fs.readFileSync(path.resolve(
  D,"../../../docs/experiments/s3-9-destination-format-cost.json"
),"utf8"));
console.log({
  reported:cost.bundle_with_the_destination_plane, // 256058
  sourcePlaneTotal:cost.bundle_without_the_destination_plane+
    cost.encodings.uint16_plane_as_written.deflated_bytes, // 266536
  publishedManifestTotal:manifest.transfer_bytes[0].deflated_total // 266030
});
```

The report understates its own chosen-plane total by **10,478 bytes**. Its 4.1% denominator is the cheaper alternative’s total. Using its source-plane figures gives **3.93%** of the chosen-plane total. Neither total includes the destination table.

The access argument also presents a false necessity: RLE does not require expanding 330,502 cells. I built cumulative run endpoints locally and binary-searched them. Across **all 330,502 source cells**, lookup mismatches were **zero**. Typed-array storage was **173,934 bytes**, versus **661,004 bytes** for the plane. The index need not be shipped.

Executed reproducer:

```js
var npy=fs.readFileSync(path.resolve(
  D,"../../data/layers/own_triangle_grocery_walk_selected_destination.npy"));
var offset=10+npy.readUInt16LE(8); // inspected file is NPY v1, <u2
var payload=npy.subarray(offset);
var plane=new Uint16Array(payload.buffer.slice(
  payload.byteOffset,payload.byteOffset+payload.byteLength));
var values=[], ends=[];
for(var col=0;col<643;col++) for(var row=0;row<514;row++) {
  var v=plane[row*643+col], index=col*514+row;
  if(values.length && values.at(-1)===v) ends[ends.length-1]=index+1;
  else { values.push(v); ends.push(index+1); }
}
var rv=Uint16Array.from(values), re=Uint32Array.from(ends);
var at=(row,col)=>{
  var target=col*514+row,lo=0,hi=re.length;
  while(lo<hi) {
    var mid=(lo+hi)>>>1;
    if(re[mid]<=target) lo=mid+1; else hi=mid;
  }
  return rv[lo];
};
var wrong=0;
for(var p=0;p<plane.length;p++)
  wrong+=at(Math.floor(p/643),p%643)!==plane[p];
console.log(re.length,rv.byteLength+re.byteLength,wrong);
// 28989, 173934, 0
```

The worker already reads and validates the destination plane **wholesale at init**. I found no implemented wholesale destination repaint/legend consumer, so the distinction between initialization and repeated card lookup remains useful. It does not establish that an expanded plane is necessary.

The `ready.bytes` field independently reports **991,506**, omitting all **661,004 destination bytes**; actual plane storage is **1,652,510**, before tables and working arrays.

The decoder temporarily holds both the incoming destination buffer and its copied `Uint16Array`. A correct faster implementation can use the existing host-endian test:

```js
if (LITTLE_ENDIAN) return new Uint16Array(buf,0,count);
// Retain the explicit little-endian loop for big-endian hosts.
```

I verified view/loop equality here. **Phone cost remains unmeasured.** The plane choice can remain an engineering choice, but the current cost/access justification needs correction.

**10. Medium — a comment can satisfy the encoding-list guard while the executable list drifts.**

Location: [test_wire.py:418](C:/Users/arikt/documents/github/distanceFinder/v2/tests/test_wire.py:418).

Renaming the constant or making the regex fail does **not** pass vacuously: `assert found` catches it. Ordinary list drift is also caught. But the first regex match may be a comment.

Executed JavaScript equivalent of the Python matching operation:

```js
var declaration=
  "const READABLE_ENCODINGS = ['published-v2', 'published-v3', 'published-v4'];";
var drifted=source.replace(declaration,
  "// "+declaration+
  "\nconst READABLE_ENCODINGS = ['published-v2', 'published-v3'];");
console.log(drifted.match(
  /const READABLE_ENCODINGS = \[([^\]]*)\]/
)[1]); // apparently correct v2/v3/v4 list
loadWorker(drifted).send(fixtureInit(swapGroup));
// rejects published-v4
```

**Cost:** the specific synchronization guard passes against stale commented text. The same construction applies to `app.js`, whose executable acceptance behavior is not exercised by the worker harness.

Use an AST extraction or an executable acceptance test. I did not execute the Python test itself.

**11. Medium — a destination query before the first compute claims the cell is included.**

Locations: [worker.js:496](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/worker.js:496), [worker.js:508](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/worker.js:508).

Initialization allocates a zero-filled verdict array, and zero means INCLUDED. The query checks allocation rather than whether any criteria have actually been evaluated.

Executed:

```js
var w=loadWorker(source);
w.send(fixtureInit(swapGroup));
console.log(w.send({type:"destinationAt",row:0,col:0}));
// included:true, seq:-1, names a destination
```

**Cost:** the new protocol can return an affirmative destination disclosure before evaluating a threshold or enabled-layer selection. Require a completed compute, and reset that lifecycle state on reinitialization.

The remaining claims I checked:

- **Horizon/pruning:** source inspection found matching final-time cutoff masks and selection from `dest_idx`. The table is constructed from selected nodes after graph pruning. Losing a selected node would indicate an inconsistent build, not a legitimate complete plane with `DEST_NONE`. Python execution remains outstanding.
- **Byte order:** `destination_plane_bytes` and the vector writer explicitly use the little-endian wire serializer. NPY is self-describing; native `uint16` during reprojection does not itself create a wire-order defect because final serialization converts it. I found no additional endian bug in those paths.
- **Set preservation:** the current exporter preserves the table byte-for-byte in this artifact, and `handleDestinationAt` returns the full stored array without reordering it. However, neither the exporter nor worker enforces a field allowlist. A future added field will ship, including through `places` in query replies. An export schema should reject unexpected fields and unreviewed licences.
- **Restricted content:** the current table has only `gers_id`, `name`, `brand`, `category`, `operating_status`, and `licence` in place records. I found none of the forbidden contact/address/provider-ID fields or a restricted licence label. I could not independently audit the originating parquet.
- **Unreferenced entries:** the seven entries are unreachable through the shipped plane, following reprojection. They are payload waste and a catalog-consumer hazard, not evidence of incorrect cell destinations. Table iteration must not imply reachability.
- **Figures:** I independently decoded the source NPY and shipped binary in JavaScript. Source: **256,752 named cells, 432 destinations**, with shared-node cell counts **14,116 + 371 = 14,487**. Shipped: **258,684 OK/named, 425 destinations**, with **14,964 shared-node cells (5.78%)**. These confirm the stated source/shipped distinction.
- **“75 share one”:** **75 places on 36 shared nodes** is the consistent reading: `549 − 510 = 75 − 36 = 39`. “550 places snap” is imprecise because one of the 550 fails the snap-distance limit. I could not rerun the graph/GeoParquet calculation establishing those candidate-node counts.
