# Codex adversarial review, pass 48 — the report

The prompt is `../49-codex-review-pass48-prompt.md`. **This pass ran read-only**, because Codex's
Windows sandbox cannot start processes at all on this machine: every `exec_command` failed with
`windows unelevated restricted-token sandbox cannot enforce split writable root sets`, under
`workspace-write`, with and without `--add-dir`, and with `--ephemeral`. The only invocation that
can execute here is `--dangerously-bypass-approvals-and-sandbox`, which this session is not
permitted to use. So the reviewer read the repository and executed JavaScript through its
`node_repl` MCP tool, which was enough to drive `worker.js` and the conformance harness in memory;
it ran no Python, no pytest and no graph load, and its Python reproducers are explicitly marked
unexecuted. It wrote this report to stdout rather than to a file, and this file is that output
verbatim.

The measurements in §B and §D of the prompt were run by me beforehand and handed to the reviewer
to attack **as method** rather than to reproduce, for the same reason. It took two of them apart:
see findings 5 and 6.

---

**Claim A is unsound as a structural guarantee.** A flag-dependent eligibility mutation passes all 50 conformance checks without changing either outcome function’s signature. I did **not** find that coupling in the unmodified worker.

This report is returned here, as requested. No files or temporary directories were created.

The checkout points to `b11c30d`, a documentation-only child of `5e5118f`. Its changes are the two record corrections and the review prompt. The reviewed implementation files match `5e5118f`, allowing for checkout line endings.

I executed JavaScript probes and an in-memory replay of the conformance harness: the baseline passed 50 checks, and all 18 existing mutations produced assertion failures. I did not start processes, run pytest, load the graph, or execute Python/GDAL. Python reproducers below are explicitly unexecuted. The shared JavaScript setup is at the end.

**1. High — the eligibility guard misses coupling whenever more than one layer is enabled**

Locations: [worker.js:289](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/worker.js:289), [test_wire.py:273](C:/Users/arikt/documents/github/distanceFinder/v2/tests/test_wire.py:273), [make_wire_vectors.py:144](C:/Users/arikt/documents/github/distanceFinder/v2/scripts/make_wire_vectors.py:144).

Every disclosing fixture has one layer. The two-layer fixture discloses nothing. Consequently, this mutation survives:

```js
var coupled = W.replace(
  'if (o === O_FAIL) anyFail = 1;',
  'if (o === O_FAIL || (m > 1 && F[k] && F[k][p] === ROUTE_RESTRICTED)) anyFail = 1;'
);
console.log(replay(coupled));
console.log(probe(coupled, [0, 0]).verdict);
console.log(probe(coupled, [1, 0]).verdict);
```

Observed:

```text
50 passed; exit 0
[0]   // INCLUDED
[1]   // EXCLUDED
```

The values, statuses, horizons, thresholds and enabled layers are identical. Only the flag changes. Neither `outcomeFor` nor Python’s `outcome_planes` signature changes.

**Cost:** withdraw “the guarantee is structural.” The current code keeps the flag outside eligibility, but the signature assertion and current vectors do not enforce that property across supported combinations.

The same missing fixture family allows two disclosure defects through all 50 checks:

```js
var firstLayer = W.replace('F.push(routeFlags[k]);', 'F.push(routeFlags[0]);');
var duplicates = W.replace('restrictedIncludedCount++; break;', 'restrictedIncludedCount++;');

console.log(replay(firstLayer));
console.log(probe(firstLayer, [1, 0], [false, true]).result.restrictedIncludedCount);
console.log(replay(duplicates));
console.log(probe(duplicates, [1, 1]).result.restrictedIncludedCount);
```

Observed counts are respectively **1 instead of 0**, and **2 instead of 1**. Both mutants pass. Their affected locations are [worker.js:247](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/worker.js:247) and line 310.

These are missing mutations worth adding alongside fixtures for mixed disclosure, multiple disclosing layers, disabled disclosing layers, and overlapping flags.

**2. High — optional planes crash a valid mixed-layer bundle**

Locations: [worker.js:149](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/worker.js:149), lines 164–165; [app.js:174](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/app.js:174).

The app correctly represents an absent per-layer plane as `null`. Once **any** layer declares a flag, the worker passes **every** slot through the mandatory-plane validator. That validator dereferences `buf.byteLength` before considering whether this particular layer discloses.

Runnable reproducer:

```js
console.log(probe(W, [1, null], [true, true], [true, false]));
```

Observed:

```text
worker: Cannot read properties of null (reading 'byteLength')
```

This is the app’s actual payload shape for one disclosing layer beside one non-disclosing layer. The exporter’s `--candidates` path can produce that configuration when only the product layer has a flag file.

**Cost:** the whole bundle fails to initialise; no eligibility results arrive. Optionality works for wholly disclosing and wholly non-disclosing fixtures, but fails between layers.

There is a secondary delivery consequence at [app.js:263](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/app.js:263): the worker’s protocol error displays an error but does not reject `initWorker`’s promise. Initialisation remains pending.

**3. High — the flag is not bound to the surface it purports to describe**

Locations: [flag_restricted_routes.py:60](C:/Users/arikt/documents/github/distanceFinder/v2/scripts/flag_restricted_routes.py:60), lines 158, 168 and 192; [export_published_layers.py:70](C:/Users/arikt/documents/github/distanceFinder/v2/scripts/export_published_layers.py:70); [wire.py:184](C:/Users/arikt/documents/github/distanceFinder/v2/locfinder/wire.py:184).

The flag generator uses its own `7200.0` constant. It does not read the persisted surface’s build horizon. The exporter reads that build horizon independently and checks the flag file’s shape, then `flag ⇒ OK`.

They agree today by configuration, not by construction.

A longer surface horizon produces the dangerous direction: a restricted journey can remain OK in the surface while the flag generator clears it at 7,200 seconds. Export accepts the clear flag.

This graph-free, synthetic Python reproducer is **unexecuted here**. Run from the repository root with the supplied Python:

```python
import sys
sys.path[:0] = ["v2", "v2/scripts"]

import networkx as nx
import numpy as np
from flag_restricted_routes import HORIZON_S
from locfinder import wire
from locfinder.status import (
    CATEGORY_COST_SELECTED, ENGINES, Surface, node_reasons
)
from locfinder.traveltime.arrival import arrival_seconds, arrival_with_route_flag
from locfinder.traveltime.csr import graph_to_cost_time_flag_csr
from locfinder.traveltime.snap import (
    EdgeIndex, cell_arrival_with_provenance, cell_route_flag
)

g = nx.MultiDiGraph()
g.add_node(0, x=0.0, y=0.0)
g.add_node(1, x=100.0, y=0.0)
g.add_edge(0, 1, travel_time=8000.0, cost=8120.0, access_restricted=True)

c, t, f, ix = graph_to_cost_time_flag_csr(g)
T, _, nf = arrival_with_route_flag(c, t, f, dest_idx=[ix[1]])
D = arrival_seconds(c, dest_idx=[ix[1]])
idx = EdgeIndex.from_graph(g, ix)
x, y = np.array([0.0]), np.array([0.0])
kw = dict(mode="walk", max_access_m=200.0, node_cost=D)
nr = node_reasons(T, ENGINES["own-graph"], search_bounded=False)

secs, reason, lower = cell_arrival_with_provenance(
    idx, T, x, y, horizon_s=10800.0, node_reason=nr, **kw
)
surf = Surface(
    mode="walk", engine="own-graph", target="grocery",
    aggregation=CATEGORY_COST_SELECTED, horizon_s=10800.0,
    seconds=secs, reason=reason, min_possible_s=lower
).validate()

wrong = cell_route_flag(idx, T, x, y, node_flag=nf, cutoff_s=HORIZON_S, **kw)
right = cell_route_flag(idx, T, x, y, node_flag=nf, cutoff_s=surf.horizon_s, **kw)
v, s = wire.encode_planes(surf)
encoded = wire.encode_route_flag(wrong, s)
outcome = wire.outcome_planes(v, s, threshold_min=140, horizon_s=surf.horizon_s)

assert list(s) == [wire.OK]
assert list(wrong) == [False]
assert list(right) == [True]
assert not wire.disclosed_restricted(encoded, outcome).any()
print("One included restricted journey silently disclosed as clear")
```

**Cost:** one false-clear disclosure in this constructed configuration. With a shorter surface horizon, extra flags can instead cause export refusal. Neither behavior is a reliable binding between artifacts.

The missing completeness check also survives current manifest aggregates. I executed this alteration entirely in memory:

```js
var changed = PF.slice();
var drop = changed.findIndex((f, i) => f === 1 && PV[i] <= 20);
var raise = changed.findIndex((f, i) => f === 0 && PS[i] === 0 && PV[i] > 20);
changed[drop] = 0;
changed[raise] = 1;
console.log({drop, raise, flags: changed.reduce((a, b) => a + b, 0)});
console.log(pub());
console.log(pub(changed));
```

Observed:

| Quantity | Original | Altered |
|---|---:|---:|
| Set flags | 57,193 | 57,193 |
| Included at T=20 | 74,227 | 74,227 |
| Restricted included | **9,324** | **9,323** |
| Verdict digest | `c93513931d7d1ba17091ebfe70fc449f` | identical |

The changed indices were 214 and 7; both statuses are OK. All existing worker initialisation checks accept the alteration.

This demonstrates a validation limit, **not evidence that the checked-in flag file is corrupted**. Shape, aggregate count and `flag ⇒ OK` cannot establish that clear means the selected journey is unrestricted. The flag build record also lacks a binding to the surface arrays, horizon and routing inputs.

The browser fixture cannot supply that assurance: [make_wire_vectors.py:192](C:/Users/arikt/documents/github/distanceFinder/v2/scripts/make_wire_vectors.py:192) manufactures flags at every sixth OK cell. It tests decoding and counting, not the published route disclosure’s truth.

**4. Medium — browser transfer accounting omits the new plane**

Locations: [app.js:187](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/app.js:187), lines 194–196 and 214–216.

The flag fetch is awaited, but its buffer is omitted from `decodedBytes`, and its resource URL is omitted from the transfer-size sum.

Runnable arithmetic reproducer using the actual loaded planes:

```js
console.log({
  reportedDecoded: PV.byteLength + PS.byteLength,
  actualDecoded: PV.byteLength + PS.byteLength + PF.byteLength
});
```

Observed:

```text
reportedDecoded: 661004
actualDecoded:   991506
```

**Cost:** the displayed decoded payload is understated by **330,502 bytes**, one third of the actual payload. Network accounting omits the entire flag response, including whatever compression and response overhead the server actually uses.

The exporter’s manifest size arithmetic is separate and includes the flag correctly. This finding concerns the browser’s measurement of what it loads.

**5. Medium — the reprojection measurements do not establish household disclosure losses**

Locations: [export_published_layers.py:209](C:/Users/arikt/documents/github/distanceFinder/v2/scripts/export_published_layers.py:209), lines 212–216; [measure_export_regrid.py:145](C:/Users/arikt/documents/github/distanceFinder/v2/scripts/measure_export_regrid.py:145).

Accepting the supplied sampling measurements, the count balance is:

```text
57,175 source flags
−2,691 flagged source cells never sampled
+2,709 extra copies of sampled flags
=57,193 destination flags
```

The **2,709 are extra copies**, not a measured population of clear household locations raised to restricted. Likewise, “never sampled” means absent from destination **centre sampling**. It does not count households receiving a dropped disclosure.

A round trip measures the composition of two resamplings at source centres. It can introduce additional errors, undo forward errors, and miss disagreement elsewhere inside cells.

Runnable counterexample:

```js
var source = [0, 1];                    // two cells covering [0, 2)
var shipped = Array.from({length: 3},
  (_, j) => source[Math.floor((j + 0.5) * 2 / 3)]);
var returned = source.map((_, i) =>
  shipped[Math.floor((i + 0.5) * 3 / 2)]);
var q = 0.9;

console.log({
  source, shipped, returned,
  sourceAtQ: source[Math.floor(q)],
  shippedAtQ: shipped[Math.floor(q * 3 / 2)]
});
```

Output:

```text
source:     [0, 1]
shipped:    [0, 1, 1]
returned:   [0, 1]
sourceAtQ:  0
shippedAtQ: 1
```

The round trip is perfect; the coordinate answer is wrong. Complementing the flags gives the corresponding missed-disclosure example.

**Cost:** withdraw any interpretation of **2,699 dropped / 3 raised**, or **6 dropped while status stayed OK**, as household counts or bounds on household error. The forward coordinate comparison remains unmeasured for flags.

The appropriate graph-free comparison follows the existing `measure_export_regrid.py` coordinate indexing:

- At each structure coordinate, read the original source cell and the shipped WGS84 pixel directly.
- Compare flags alongside each side’s status and verdict.
- Separately compare the analytically placed Mercator row.
- Keep cropped coordinates and status transitions separate from false-clear transitions where both sides still publish an included journey.

On the identity-plane method:

- Three bytes can encode this grid’s indices without truncation: 330,502 is well below \(2^{24}\).
- Coverage needs an independent validity test or an unambiguous outside sentinel.
- Reconstructing one ID from three warped byte components does not independently prove three datasets’ provenance. Mixed components can themselves form a valid ID.
- For this exporter, identical nearest-neighbour geometry, dimensions and matching nodata/fill values provide the stronger reason to expect a common sampled cell. Changing destination shape alone does not create three different journeys.

I therefore found no evidence supporting the proposed **P/Q/R mixed-journey defect** in this implementation. That does not rescue coordinate fidelity.

The commit’s “57,175 … matches the reported aggregate exactly” is true about the source artifact. As a statement about what ships, it needs qualification: the manifest says **57,193**, and neither count measures affected households.

**6. Medium — the contract argument does not require a third byte plane**

Location: [wire.py:76](C:/Users/arikt/documents/github/distanceFinder/v2/locfinder/wire.py:76), especially lines 78–81.

The existing v2 contract defines whole-byte codes and rejects other values. It did **not** reserve a flag bit. Setting a bit while continuing to claim v2 would therefore violate that contract.

That does not prohibit an explicitly versioned successor from defining two fields in a byte. For example, a new encoding could specify:

```text
status = byte & 7
restricted = (byte & 8) !== 0
```

Codes 0–6 retain their status-field meanings. The new version explicitly defines the additional field, and old readers refuse the new encoding. That is a format change, just as the third plane is.

Runnable construction and comparison:

```js
var zlib = await import('node:zlib');
var deflate = x => zlib.deflateSync(x, {level: 9}).length;
var combined = Uint8Array.from(PS, (s, i) => s | (PF[i] << 3));

console.log({
  flagsPreserved: combined.every((b, i) => ((b & 8) !== 0) === Boolean(PF[i])),
  statusesPreserved: combined.every((b, i) => (b & 7) === PS[i]),
  separateFlagBytes: deflate(PF),
  marginalBitBytes: deflate(combined) - deflate(PS)
});
```

Both preservation checks returned true. This runtime’s compression output differed slightly from the supplied Python measurements, but retained the same ordering.

Using your supplied same-compressor figures:

| Alternative | Saving against shipped bundle |
|---|---:|
| Packed bitmap | 3,629 bytes |
| Row-major run length | 3,014 bytes |
| Column-major run length | 3,312 bytes |
| Delta-varint indices | 2,978 bytes |
| Status bit | **4,555 bytes** |

**Cost:** withdraw both “the byte argument … does not survive measurement” and the claim that the contract itself forbids a versioned bit field.

The marginal-cost comparison is fair: it compares the incremental cost of preserving the same information. A phone decode disadvantage has not been measured. A bit field can also avoid allocating the additional 330,502-byte flag plane; extra masking operations do not establish a meaningful latency disadvantage.

The status bit saves **2.00% of the shipped compressed bundle**. That is modest, but real. Sparse encodings beat this particular plane by roughly 3 KB; density alone would not establish that without measurement.

I could not break `v1_plane()` as the intended baseline. It correctly replaces every non-OK value with constant 255. The supplied **1.33149×** bundle ratio is fair for that comparison. It does not establish that the chosen disclosure encoding is smallest.

A third plane remains a defensible simplicity and delivery-contract choice. The stated necessity and size arguments do not establish it.

**7. Medium — the corrections are locally true but incomplete and not reproducible**

Locations:

- [flag_restricted_routes.py:122](C:/Users/arikt/documents/github/distanceFinder/v2/scripts/flag_restricted_routes.py:122), lines 127–128.
- [s3-decision-report.md:70](C:/Users/arikt/documents/github/distanceFinder/docs/s3-decision-report.md:70), lines 91 and 118–119.
- [execution-plan.md:364](C:/Users/arikt/documents/github/distanceFinder/docs/plans/2026-11-04-s3-execution-plan.md:364), lines 378 and 389.
- [soft-way-dependence.md:228](C:/Users/arikt/documents/github/distanceFinder/docs/engineering-notes/project-phase1-s3-soft-way-dependence.md:228).

The corrected JSON now accurately says:

- 7,271 agrees with its own T=10 datum.
- A plane ships.
- Source-grid figures still differ from shipped lookup figures.
- Nothing displays the disclosure.

The corrected step 8 row also accurately distinguishes publication from visibility.

But the generator still emits **7,276** and **“no flag plane is shipped at all.”** The next ordinary regeneration restores both errors.

Runnable record sweep:

```js
for (var file of [
  'v2/scripts/flag_restricted_routes.py',
  'docs/s3-decision-report.md',
  'docs/plans/2026-11-04-s3-execution-plan.md',
  'docs/engineering-notes/project-phase1-s3-soft-way-dependence.md'
]) {
  fs.readFileSync(path.join(ROOT, file), 'utf8').split('\n').forEach((s, i) => {
    if (/7,276|no flag plane|flag is not persisted|not persisted in the layer bundle|not published in the layer bundle|published-v2.*two uint8/.test(s))
      console.log(`${file}:${i + 1}: ${s.trim()}`);
  });
}
```

**Cost:** the decision report’s current release prerequisites falsely say publication is still outstanding. Its encoding row also describes the earlier two-plane, 18.2% version as the established encoding. The plan contradicts its corrected row, and the engineering note still presents aggregation as absent.

Historical records can retain historical claims, but need an explicit dated supersession. The generator and current decision report need actual corrections.

**Mutation audit**

There are **five**, not four, newly added mutations: the parent has 13 and this commit has 18.

| Mutation | Executed rejection | Assessment |
|---|---|---|
| Restricted route excludes | First fails hand T=5; real T=1 inclusion falls 21→18 | Produces its named defect. No withheld case fails; positive expectations catch it. |
| Never count disclosure | Real T=1 returns 0 instead of 3 | Directly caught by disclosure assertion. |
| Count excluded cells | Real T=1 returns 5,219 instead of 3 | Directly caught. Mutation specifically uses `F[0]`, so exercises the first-layer version. |
| Missing disclosure returns zero | All nine withheld real cases fail strict null assertion | Directly caught; those assertions execute. |
| Disable flag/status check | Dedicated non-OK flag refusal fails | Directly caught by the targeted refusal. |

The five edits change behavior and are caught for relevant reasons. The process-launch/error classification in `mutate_worker.mjs` was reviewed from source; I did not execute its subprocess runner.

The surviving multi-layer mutations in finding 1, the mixed-null crash, and upstream missing/misassigned flags are unrepresented defects.

**Claims checked and not broken**

- **Current eligibility algebra:** the unmodified verdict loop does not consult flags. The shipped T=20 verdict digest also stayed identical under removed and reassigned flags.
- **Current two-worker state:** each loaded module has its own lexical `state`. Plane loading creates fresh standalone buffers. The plain manifest is separate, and `routeFlags: undefined` prevents delivery. I found no flag-bearing `globalThis`, retained shared closure, or shared plane buffer in the current worker.
- **Limits of that isolation:** deleting `require.cache` does not isolate arbitrary future globals. However, shared state would not automatically invalidate the independent expected digest: wrong covered verdicts would still fail it.
- **Withheld assertions:** counts and digest checks execute on the selected plain worker. They are not bypassed.
- **Horizon fix coverage:** the cutoff applies inside the loop over all three populations. The separate raster-writing call also supplies it.
- **Absent declaration with an arriving plane:** the plane is ignored; the count is null and `disclosesRoutes` is false. Slots are not compacted or shifted.
- **Manifest aggregate:** the exporter derives `discloses_restricted_routes` from entries. The worker ignores that aggregate and derives disclosure from `flag_file`; manually inconsistent manifests are accepted. I observed both disagreement directions.
- **Null consumer trace:** the sole app consumer assigns `msg.restrictedIncludedCount` to `state.lastRestrictedIncludedCount` at line 477. Nothing reads that property afterward. I found no null-to-zero or null-to-false conversion, and no rendered “0”; the path ends without rendering anything.
- **Published invariant:** setting a flag at a non-OK cell is refused. Its missing converse and artifact binding are the limitations in finding 3.

**Shared JavaScript reproducer setup**

Run once in `node_repl`, then run the JavaScript blocks above. It reads files and executes source in memory; it neither writes files nor starts processes.

```js
var fs = await import('node:fs');
var path = await import('node:path');
var vm = await import('node:vm');
var crypto = await import('node:crypto');

var ROOT = 'C:/Users/arikt/documents/github/distanceFinder';
var DIR = path.join(ROOT, 'v2/spikes/g3-render');
var W = fs.readFileSync(path.join(DIR, 'worker.js'), 'utf8');
var H = fs.readFileSync(path.join(DIR, 'worker_conformance.mjs'), 'utf8');

function worker(source = W) {
  var messages = [];
  var context = vm.createContext({
    performance, ArrayBuffer, Uint8Array, Uint32Array, Int8Array,
    self: {postMessage: m => messages.push(m)}
  });
  vm.runInContext(source, context);
  return {
    send(m) {
      messages.length = 0;
      context.self.onmessage({data: m});
      return messages.slice();
    }
  };
}

function replay(source = W) {
  var logs = [], exits = [];
  var context = vm.createContext({
    performance, ArrayBuffer, Uint8Array, Uint32Array, Int8Array, Buffer,
    __dirname: DIR, fs, path, createHash: crypto.createHash,
    process: {exit: code => exits.push(code)},
    console: {log: s => logs.push(s), error: s => logs.push(s)}
  });
  function requireMemory(file) {
    if (!requireMemory.cache[file]) {
      var load = vm.runInContext(
        '(function(exports,require,module,__filename,__dirname){' +
        source + '\n})', context
      );
      load({}, requireMemory, {exports: {}}, file, path.dirname(file));
      requireMemory.cache[file] = true;
    }
    return {};
  }
  requireMemory.cache = {};
  requireMemory.resolve = file => file;
  context.require = requireMemory;
  vm.runInContext(H.slice(H.indexOf('const FIXTURES')), context);
  return {
    passes: logs.filter(s => s.startsWith('PASS')).length,
    failures: logs.filter(s => s.startsWith('FAIL')),
    exits
  };
}

var one = n => new Uint8Array([n]).buffer;

function probe(source = W, flags = [1, 0],
               enabled = [true, true], declared = flags.map(() => true)) {
  var w = worker(source);
  var init = w.send({
    type: 'init',
    manifest: {
      nrows: 1, ncols: 1, encoding: 'published-v3',
      layers: declared.map((d, i) => ({
        id: String(i), horizon_s: 7200,
        ...(d ? {flag_file: `${i}.flag.bin`} : {})
      }))
    },
    values: flags.map(() => one(5)),
    statuses: flags.map(() => one(0)),
    routeFlags: flags.map(f => f === null ? null : one(f))
  });
  if (init.some(m => m.type === 'error')) return {init};
  var result = w.send({
    type: 'compute', seq: 1,
    thresholds: flags.map(() => 10), enabled
  })[0];
  var verdict = w.send({type: 'verdicts', reqId: 1})[0];
  return {init, result, verdict: [...new Int8Array(verdict.verdicts)]};
}

var PUB = path.join(DIR, 'fixtures/published');
var PM = JSON.parse(fs.readFileSync(path.join(PUB, 'manifest.json'), 'utf8'));
var PL = PM.layers[0];
var plane = file => Uint8Array.from(fs.readFileSync(path.join(PUB, file)));
var PV = plane(PL.value_file);
var PS = plane(PL.status_file);
var PF = plane(PL.flag_file);

function pub(flag = PF, manifest = PM) {
  var w = worker();
  var ready = w.send({
    type: 'init', manifest,
    values: [PV.buffer], statuses: [PS.buffer],
    routeFlags: [flag.buffer]
  })[0];
  var result = w.send({
    type: 'compute', seq: 1, thresholds: [20], enabled: [true]
  })[0];
  var verdict = w.send({type: 'verdicts', reqId: 1})[0];
  return {
    ready,
    included: result.inCount,
    restricted: result.restrictedIncludedCount,
    digest: crypto.createHash('sha256')
      .update(new Uint8Array(verdict.verdicts))
      .digest('hex').slice(0, 32)
  };
}
```
