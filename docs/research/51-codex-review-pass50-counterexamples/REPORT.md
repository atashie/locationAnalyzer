# Codex adversarial review, pass 50 — the report

The prompt is `../51-codex-review-pass50-prompt.md`. **Read-only**, for the reason in
`docs/engineering-notes/reference-codex-runtime-quirks.md`: Codex's Windows sandbox cannot start a
process on this machine. The reviewer read the repository and executed JavaScript through
`node_repl`; it ran no Python, no pytest and no rasterio, and its Python reproducers are marked
unexecuted. It wrote the report to stdout and this file is that output verbatim.

It reports **14 findings, 4 of them High**, on the *repairs* made for pass 49 rather than on the
original work. Two answers to questions the prompt asked:

* **The `src_nodata` hazard I suspected is not real** — it says so explicitly. My own measurement
  at 1:1, many:1 and 1:many agreed, so that question is settled from both directions.
* **The provenance check is unsound as a proof of source-cell identity** and sound as an
  output-value consistency check, because two source cells holding the same value are
  indistinguishable to it. That is a real narrowing of a claim I made two commits ago.

Reviewed at `40c454e`.

---

## A. `verify_provenance`

**`verify_provenance` is unsound as a proof of source-cell identity. It is sound as an output-value consistency check.** The distinction matters: I did **not** find the proposed nodata-selection bug.

Reviewed branch: `v2-rethink`, tip `40c454e72cabad97e61f5ff29841da4f4e1dc11c`. No files changed. JavaScript ran through `node_repl`; Python, pytest, Git and Rasterio were not executed.

### A1 — Medium: the check establishes matching values, not identical physical provenance

Location: [export_published_layers.py:390](C:/Users/arikt/documents/github/distanceFinder/v2/scripts/export_published_layers.py:390), especially lines 394–396 and 581–584; [destination-identity.md:147](C:/Users/arikt/documents/github/distanceFinder/docs/engineering-notes/project-phase1-s3-destination-identity.md:147).

The claim that mismatched source cells fail “whatever the values are” is false. If two source cells contain the same destination ordinal, sampling either produces the same byte pair. The comparison cannot distinguish their identities. This is harmless for the published answer when all observed values agree, but it defeats the stronger provenance claim.

Runnable Python, **unexecuted**:

```python
import sys
from pathlib import Path
import numpy as np
from rasterio.transform import from_origin

V2 = Path(r"C:\Users\arikt\documents\github\distanceFinder\v2")
sys.path[:0] = [str(V2), str(V2 / "scripts")]
import export_published_layers as e

source = {
    "value": np.array([[5, 5]], dtype=np.uint8),
    "status": np.array([[0, 0]], dtype=np.uint8),
    "destination": np.array([[7, 7]], dtype=np.uint16),
    "flag": np.array([[0, 0]], dtype=np.uint8),
}
# Each plane takes the opposite source cell. The values conceal that.
published = {k: v[:, ::-1].copy() for k, v in source.items()}

print(e.verify_provenance(
    "equal-values", from_origin(0, 1, 1, 1), "EPSG:4326",
    (0, 0, 2, 1), 1, 2, source=source, published=published
))
```

**Cost:** withdraw “cannot survive … whatever the values are.” Keep the narrower, useful claim: every published value agrees with the value at the reference index.

The nodata concern itself does not break that narrower check. GDAL documents nearest as selecting the source cell containing the transformed centre; if that cell is invalid, the target becomes nodata. It does not search neighbouring valid cells. Its wording is: “If this source pixel is invalid, the target pixel is considered as nodata.” [GDAL nearest/nodata documentation](https://gdal.org/en/stable/programs/gdalwarp.html#nodata-source-validity-mask-handling).

Consequently, in these calls:

- An ordinary source value is copied.
- A source value equal to `src_nodata` leaves the destination nodata value.
- Because `src_fill == dst_fill`, both cases produce the expected source value.
- `ROUTE_CLEAR=0` therefore remains zero. Clear cells are not replaced by neighbouring restricted cells.

The real grid is also **not a one-to-one retiling**. Decoding the actual source NPY and published binary gave:

| Measurement | Source | Published |
|---|---:|---:|
| Named cells | 256,752 | 258,684 |
| Distinct destinations | 432 | 425 |

Under the asserted correct nearest mapping, those counts require repeated source selections; a bijection could not increase the named-cell count by 1,932.

The tiny controls do have inadequate coverage: they explicitly use a one-to-one grid, omit the flag plane, and do not exercise uncovered output or changed resolution. Add those cases. But the stronger allegation that the check **only ever runs on one-to-one mappings** is contradicted by the shipped counts. I did not independently rerun the Rasterio index plane or its reported zero disagreements.

### A2 — High: the source fingerprint is still earned with a mask-only check

Location: [persist_selected_destination.py:249](C:/Users/arikt/documents/github/distanceFinder/v2/scripts/persist_selected_destination.py:249), fingerprint at line 318; corresponding claim at [destination-identity.md:156](C:/Users/arikt/documents/github/distanceFinder/docs/engineering-notes/project-phase1-s3-destination-identity.md:156).

The repair checks whether fresh destinations and saved seconds agree about **journey presence**. It still never compares saved journey times with the fresh computation.

Changing saved times while retaining the same finite/within-horizon mask passes this guard and receives a new fingerprint. The exporter’s new provenance check then faithfully checks against that already-mismatched source tuple.

Executed JavaScript decoded the source float32 NPY: **256,276 cells can have 60 seconds added while remaining within 7,200 seconds**. Their published minute values change; the new mask guard cannot notice.

Runnable Python replaying the **actual guard**, **unexecuted**:

```python
import textwrap
from unittest.mock import patch
import persist_selected_destination as p

layers = V2 / "data/layers"
original = np.load(layers / f"{p.STEM}.npy")
altered = original.copy()
change = np.isfinite(altered) & (altered <= p.HORIZON_S - 60)
altered[change] += 60

ordinals = np.load(layers / f"{p.STEM}_selected_destination.npy")

# Execute the current source's guard, without writing anything.
lines = (V2 / "scripts/persist_selected_destination.py").read_text(
    encoding="utf-8"
).splitlines()
guard = textwrap.dedent("\n".join(lines[251:262]))
scope = dict(np=np, LAYERS=layers, STEM=p.STEM,
             HORIZON_S=p.HORIZON_S, ordinals=ordinals)

with patch.object(np, "load", return_value=altered):
    exec(guard, scope)

assert scope["orphan"] == scope["missing"] == 0
print("Changed times accepted:", int(change.sum()))
```

**Cost:** up to **256,276 changed minute answers** in this construction while the new binding guard remains green. The claim that the fingerprint now proves the destinations describe the saved journey times must be narrowed. Generate both from the same computation, or compare the recomputed cell times as well.

## B. The licence bundle

### B1 — High: the publication allowlist has unguarded entrances

Location: [export_published_layers.py:185](C:/Users/arikt/documents/github/distanceFinder/v2/scripts/export_published_layers.py:185); unchanged-table serialization at line 540.

The gate checks destination-entry keys and place-record keys. It does not check:

- Root table keys.
- Keys inside the root `licence` object.
- Types or nested contents of permitted place fields.

A phone can enter as root metadata, an upstream provider ID inside `licence`, or a website inside an object stored under `brand`. All are serialized unchanged.

Runnable Python, **unexecuted**:

```python
import json

table_path = layers / f"{p.STEM}_selected_destination_table.json"
t = json.loads(table_path.read_text(encoding="utf-8"))
t["phones"] = ["+1-919-555-0100"]
t["licence"]["upstream_provider_id"] = "forbidden-provider-id"
t["destinations"][0]["places"][0]["brand"] = {
    "website": "https://example.invalid/"
}

e.check_table_is_publishable(t, table_path)  # Returns successfully.
encoded = json.dumps(t, allow_nan=False)
assert all(x in encoded for x in
           ["+1-919-555-0100", "forbidden-provider-id", "example.invalid"])
```

I also injected this table through an in-memory filesystem facade into the real shipped-bundle harness: **75/75 passed**.

**Cost:** the “no forbidden fields can leave” guarantee is false. Apply a schema to the entire table, including allowed scalar types and nested metadata.

### B2 — High: the licence gate does not establish Apache §4 compliance

Locations: [export_published_layers.py:324](C:/Users/arikt/documents/github/distanceFinder/v2/scripts/export_published_layers.py:324), [ATTRIBUTION.md:14](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/fixtures/published/ATTRIBUTION.md:14), [NOTICE-foursquare.txt:16](C:/Users/arikt/documents/github/distanceFinder/v2/licences/NOTICE-foursquare.txt:16).

For the complete directory bundle:

| Apache clause | Assessment |
|---|---|
| **4(a)** | Satisfied: recipients receive “a copy of this License” in `LICENSES/Apache-2.0.txt`. |
| **4(b)** | Not discharged by the current placement: the requirement concerns “modified files to carry prominent notices.” The modified JSON carries no modification notice; a separate `ATTRIBUTION.md` carries it. |
| **4(c)** | Not established. This independently requires retaining “all copyright, patent, trademark, and attribution notices” applicable to the distributed source. The build has not inventoried those upstream notices. |
| **4(d)** | Not established. It requires a “readable copy of the attribution notices” from the applicable NOTICE. The shipped file explicitly says it is not that copy, and completeness has not been checked. |

Those quoted requirements are from [Apache-2.0 §4](https://www.apache.org/licenses/LICENSE-2.0).

The gate merely checks whether the NOTICE pathname exists. An **empty NOTICE** passes:

```python
# UNEXECUTED Python
import shutil
import tempfile

with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    licence_dir = td / "licences"
    licence_dir.mkdir()
    shutil.copyfile(e.LICENCES / "Apache-2.0.txt",
                    licence_dir / "Apache-2.0.txt")
    (licence_dir / "NOTICE-foursquare.txt").write_text("", encoding="utf-8")

    t = {"destinations": [{"places": [{"licence": "Apache-2.0"}]}]}
    with patch.object(e, "LICENCES", licence_dir):
        result = e.write_licence_bundle(td / "out", [t], {"test-release"})

    assert (td / "out/LICENSES/NOTICE-foursquare.txt").stat().st_size == 0
    print(result)
```

**Cost:** the build cannot claim redistribution compliance for the **35 Apache records**. This is an unresolved release prerequisite, not proof that additional upstream notices necessarily exist.

Shipping the honest partial notice is **better than shipping none**: it preserves known attribution and tells reviewers what remains unknown. It becomes worse operationally if its mere existence is treated as clearance. That is what this gate currently does. Overture itself says to preserve source NOTICE attribution, with the copyright line as a minimum. [Overture attribution requirements](https://docs.overturemaps.org/attribution/).

Two documentation corrections also follow:

- Apache §4(b) does **not** require a modification date. `ATTRIBUTION.md:17`, the template at exporter line 359, the README and the test comment at `test_export_published.py:298` invent that requirement.
- CDLA-Permissive-2.0 does not impose a separate attribution requirement of the kind claimed at `destination-identity.md:69`; its sharing condition is making the agreement text available.

**CDLA §2.1:** I could not break the directory-bundle arrangement. It requires making the agreement text available “with the shared Data,” not a pointer embedded in every JSON file. The manifest lists the accompanying files. Distributing the JSON alone would be a different distribution and would lose that accompaniment. [CDLA-Permissive-2.0](https://cdla.dev/permissive-2-0/).

**Separation:** the withdrawal is substantially correct. Separate files can help preserve independently usable datasets and document their boundaries; they do not establish independence. There remains a valid collective-database argument for substantively independent datasets, including arrangements recognized by OSMF’s guidelines. Nothing reviewed establishes that this node-linked, selected side table meets that boundary. [ODbL definitions](https://opendatacommons.org/licenses/odbl/1-0/index.html), [OSMF collective-database guidance](https://osmfoundation.org/wiki/Licence/Community_Guidelines/Collective_Database_Guideline_Guideline).

## C. The harness and the artifact

The JavaScript snippets below use the read-only VM setup at the end.

### C1 — High: the full-record oracle aliases the worker’s mutable input

Location: [worker_conformance.mjs:134](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/worker_conformance.mjs:134), comparison at lines 265–268; shim at lines 55 and 80.

The worker receives `group.dest_tables` itself. Later, the expected full record is read from that same object. The shim supplies neither incoming nor outgoing structured cloning.

Executed:

```js
var corruptRecords = source.replace(
  "const entry = destTables[k].destinations[d];",
  `const entry = destTables[k].destinations[d];
   entry.places.forEach(pl => {
     pl.gers_id = "WRONG";
     pl.licence = "Proprietary";
   });`
);
console.log(replay(corruptRecords));
```

Result: **exit 0, 75 passes, zero failures**.

The independent names and node checks still help. They do not protect the other fields.

**Cost:** every returned GERS ID and licence can be corrupted while the claimed whole-record check passes.

Returning `entry.places` by reference is itself normal worker code: a real `postMessage` clones it. The test defect is allowing mutation of the expected result. Snapshot an immutable oracle **before init**, clone the worker input, and compare output against that snapshot. Independently recorded full-record expectations or digests would additionally protect fixture generation.

A second destination mutation also survived **75/75**:

```js
console.log(replay(source.replace(
  "if (buf.byteLength !== n * 2) {",
  "if (false) {"
)));
```

The suite has no destination-length refusal case.

### C2 — Medium: the shipped check accepts a completely empty place set and stale identities

Location: [worker_conformance.mjs:729](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/worker_conformance.mjs:729), especially lines 740–744.

Executed:

```js
var stub = structuredClone(table);
stub.destinations.forEach(e => {
  e.place_count = 0;
  e.places = [];
});
console.log(replay(source, intercept(file =>
  file === path.join(PUB, entry.dest_table)
    ? JSON.stringify(stub) : undefined
)));
```

Result: **75 passes** with **432 destination entries and zero place records**. Length equality holds, and `.every(...)` on the empty set is true.

Executed against the actual destination bytes:

```js
var swapped = Buffer.from(fs.readFileSync(path.join(PUB, entry.dest_file)));
var a = swapped.readUInt16LE(7 * 2);
var b = swapped.readUInt16LE(112 * 2);
swapped.writeUInt16LE(b, 7 * 2);
swapped.writeUInt16LE(a, 112 * 2);

console.log(replay(source, intercept(file =>
  file === path.join(PUB, entry.dest_file) ? swapped : undefined
)));
```

Result: **75 passes** after swapping ordinals **240 and 17** at cells **7 and 112**.

**Cost:** the new check detects the previous JSON release blocker, but it does not establish that the shipped names are substantive, current, or generated from the current sources. Require nonempty sets, validate every entry, and check regeneration/fingerprints separately.

It does reject an actually zero-length destination file, an all-sentinel destination plane beside unchanged OK statuses, and a missing destination table. Those repairs held.

The name “loads the way the page loads it” remains too strong. These real-load behaviours are absent:

- Relative-URL resolution, URL escaping and case sensitivity under the server.
- Network rejection, HTTP status handling, browser security restrictions, and response content decoding.
- Cross-request delivery of mutually stale files; `no-store` does not make several requests atomic.
- Execution of the app’s own manifest checks and readable-encoding declaration.
- Execution of the app’s separate plane-length checks and its fetch error paths.
- Resource Timing lookup, transferred-byte accounting and the assignments to page state, including bounds.
- Real Worker construction, script delivery, structured cloning, transferred-buffer detachment and asynchronous message handling.
- The prerequisite `versions.json` load.

Several checks are duplicated by the worker. That is useful coverage, but it does not exercise the app’s implementations.

### C3 — Medium: out-of-range destination coordinates wrap into valid cells

Location: [worker.js:527](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/worker.js:527).

Executed against the unchanged worker:

```js
var w = load(source);
w.send(fixtureInit(swapGroup));
w.send({type:"compute", seq:1, enabled:[true], thresholds:[10]});
console.log(w.send({
  type:"destinationAt", reqId:1, row:4294967296, col:0
}));
```

Result: `row:0`, `col:0`, `included:true`, naming **S Shop 1**.

`| 0` runs before bounds checking. Large integers wrap, fractions truncate, and missing/nonfinite coordinates become zero.

**Cost:** an invalid/outside request receives a confident destination for another cell. Validate integer coordinates before coercion. A mutation clamping negative coordinates to zero also survived **75/75**.

## D. `state.computed`

### D1 — Medium: the lifecycle repair covers one reader, not the class

Locations: [worker.js:573](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/worker.js:573), line 584; reset block at line 340.

Executed:

```js
var w = load(source);
w.send(fixtureInit(swapGroup));
console.log(w.send({type:"verdicts", reqId:1}).map(m => ({
  ...m, verdicts:[...new Int8Array(m.verdicts)]
})));

w.send({type:"compute", seq:10, enabled:[true], thresholds:[10]});
w.send(fixtureInit(swapGroup));
console.log(w.send({type:"mask", reqId:2}).map(m => ({
  ...m, mask:[...new Uint8Array(m.mask)]
})));
```

Results:

```text
Before compute: verdicts=[0,0], seq=-1
After reinit:   mask=[0,0], inCount=2, seq=-1
```

The first reply means **two INCLUDED cells** despite no evaluation. The second combines a fresh zero mask with a stale count from the previous initialization.

**Cost:** contradictory consumer outputs and the same unevaluated-answer defect through another message type. `lastInCount` is the additional stale field across successful init. Other stored planes, dimensions, horizons and the buffer pool are replaced.

Guard both plane-query handlers with `computed`, and reset `lastInCount`.

### D2 — Medium: a failed compute leaves a partially changed plane labelled with the previous sequence

Locations: [worker.js:423](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/worker.js:423), state commit at line 453; error handling at line 139.

Executed:

```js
var w = load(source);
w.send({
  type:"init",
  manifest:{nrows:1,ncols:2,encoding:"published-v3",
            layers:[{id:"x",horizon_s:7200}]},
  values:[Uint8Array.of(5,0).buffer],
  statuses:[Uint8Array.of(0,99).buffer]
});
w.send({type:"compute",seq:1,enabled:[false],thresholds:[10]});
console.log(w.send({
  type:"compute",seq:2,enabled:[true],thresholds:[0]
}));
console.log(w.send({type:"verdicts",reqId:1}).map(m => ({
  ...m, verdicts:[...new Int8Array(m.verdicts)]
})));
console.log(w.send({type:"mask",reqId:2}).map(m => ({
  ...m, mask:[...new Uint8Array(m.mask)]
})));
```

Result:

```text
compute 2: error on status 99
verdicts: seq=1, [1,0]
mask:     seq=1, inCount=2, [0,1]
```

**Cost:** the previous completed result is silently modified after an unsuccessful request. Invalidate computation state before mutation, or compute into temporary buffers and commit atomically.

On the API design: `included:null` plus an explicit discriminator is defensible, and there is no existing consumer to break. I prefer a tagged reply such as `status:"notComputed"`, with evaluated replies carrying a verdict. Rejecting pre-compute `mask`/`verdicts` requests is especially straightforward. A bare nullable boolean invites truthiness mistakes.

## E. Required byte order

**Could not break it with a normal structured-cloneable payload.**

Every destination buffer the worker actually decodes must belong to a layer declaring `dest_file`. That makes `declaresDest` true, which makes `anyPlane` true and requires the global declaration. Undeclared arriving planes are rejected.

Skipping the declaration when all slots are absent is correct. Requiring a declaration still cannot verify that the bytes were written in the declared order; the repair acknowledges that limit.

## F. Cost report

The **20.63% arithmetic is correct for the five recorded payload sizes**: `59,278 / 287,309`. Summing separately compressed JSON and binary files is a reasonable model when each HTTP response receives that content encoding. Different media types do not invalidate the sum.

It is not an observed HTTP transfer measurement:

- The denominator omits `manifest.json`, and the complete directory bundle also contains attribution/licence files.
- Server content encoding, compression settings, headers and caching remain unmeasured.
- My Node compressor did **not** reproduce the recorded Python deflate sizes: the five files totalled **290,470**, with destination plus table **58,813**. I cannot distinguish compressor-version differences from stale recorded measurements without executing the Python compressor, so I am **not reporting this as proven artifact staleness**.

The source/published totals are now separated correctly. One remaining presentation ambiguity: **28,989 runs / 173,934 bytes is the source-grid index**, not the published-grid index. Executed on the published plane, I measured **28,422 runs / 170,532 index bytes**.

The source-grid lookup reproduction matched exactly: **330,502 probes, zero mismatches**.

“Simplicity” is an honest engineering preference. Two supporting sentences remain wrong at [price_destination_encodings.py:237](C:/Users/arikt/documents/github/distanceFinder/v2/scripts/price_destination_encodings.py:237) and [destination-identity.md:218](C:/Users/arikt/documents/github/distanceFinder/docs/engineering-notes/project-phase1-s3-destination-identity.md:218):

- The plane does have a decode step: `readLittleEndianU16` loops over every cell and allocates the decoded array.
- Both formats must keep ordinals consistent with the side table. A run-end index does not introduce a different ordinal assignment.

**Low-severity correction:** describe fewer decoding/indexing mechanisms, and label the byte figures as a compression model rather than literally all “what ships.”

## G. Repaired guards and new controls

### G1 — Medium: `byteswap_control` still accepts an incorrect baseline

Location: [byteswap_control.mjs:119](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/byteswap_control.mjs:119).

The baseline checks that the ordinal is non-null. It never compares it with the recorded ordinal.

Executed through the actual control:

```js
var incorrectBaseline = source.replace(
  "ordinal: d,",
  "ordinal: d === 1 ? 256 : d === 256 ? 1 : d,"
);
console.log(runByteswapControl(incorrectBaseline));
```

Result: **exit 0, `CONFIRMED`**.

Its baseline reports:

```text
ordinal 256 with S Shop 1
ordinal 1   with S Shop 256
```

Those are both wrong ordinal/name associations. The mutated outputs are exactly the swaps of those incorrect baseline ordinals, so the relational test accepts them.

**Cost:** withdraw “baseline … completely correctly” in the control, test description, destination note and ledger instance 30. Compare the baseline ordinal to the recorded expected ordinal, then require the mutation’s absolute expected ordinals.

The mutation-application guard itself held.

### G2 — Low: the claimed early exit of the mutation runner does not happen

Locations: [byteswap_control.mjs:3](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/byteswap_control.mjs:3), [test_browser_conformance.py:67](C:/Users/arikt/documents/github/distanceFinder/v2/tests/test_browser_conformance.py:67).

Executed:

```js
var endian = mutations.find(m =>
  m.name === "the destination plane is read big-endian"
);
var result = replay(endian.apply(source));
console.log(result.passes, result.failures.length);
console.log(result.failures.filter(s => s.includes("byte swap")));
```

Result: **67 passes, 8 failures, 75 checks executed**, including:

```text
destination ordinals that survive a byte swap:
(0, 0) ordinal 256, expected 1
```

`check()` catches failures and continues. `mutate_worker.mjs` merely selects the first FAIL line for reporting.

**Cost:** withdraw the claim that the byte-swap fixture was never reached. The isolated control remains useful for a focused experiment; that justification for it is false.

### G3 — Medium: the comment stripper can hide executable declarations and accept string contents as code

Location: [test_wire.py:395](C:/Users/arikt/documents/github/distanceFinder/v2/tests/test_wire.py:395), consumers at lines 483 and 516.

This construct defeats both sides of the repair:

```js
const example = `
const READABLE = ['published-v2', 'published-v3', 'published-v4'];
`;
/* supported versions */ const READABLE = ['published-v2', 'published-v3'];
```

The stripper keeps the declaration-shaped text inside the template literal and removes the executable declaration following the block comment.

I executed this mutation inside the **actual app source**, extracted and ran the real `loadFixtures`, and reproduced the guard’s line-stripping algorithm:

```text
Regex declarations found: exactly one, containing v2/v3/v4
Real loadFixtures: refuses the shipped published-v4 manifest
```

Runnable Python against the actual helper, **unexecuted**:

```python
import re
sys.path.insert(0, str(V2 / "tests"))
from test_wire import executable_lines

attack = """const example = `
const READABLE = ['published-v2', 'published-v3', 'published-v4'];
`;
/* supported versions */ const READABLE = ['published-v2', 'published-v3'];
"""
found = re.findall(r"const READABLE = \[([^\]]*)\]",
                   executable_lines(attack))
assert len(found) == 1
assert "'published-v4'" in found[0]
```

**Cost:** both nominal encoding checks can pass while the page rejects the artifact. The test named `test_the_page_accepts_the_encoding_the_exporter_writes` still does not execute page behaviour.

### G4 — Low: `versions.json` is outside the strict-JSON roots

Locations: [test_export_published.py:359](C:/Users/arikt/documents/github/distanceFinder/v2/tests/test_export_published.py:359), consumer at [app.js:135](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/app.js:135).

The omitted artifact is:

```text
v2/spikes/g3-render/versions.json
```

The page parses it before boot can finish. It is outside all three scan roots.

Executed: presenting an invalid `versions.json` through the filesystem facade leaves **75/75 conformance checks passing**, because the harness never reads it.

**Cost:** the claimed generalization to every JSON artifact loaded by a non-Python consumer is false. Include this file explicitly or derive the inventory from consumer load paths.

### G5 — Medium: the tie control accepts moves caused by an invalid algorithm

Location: [persist_selected_destination.py:459](C:/Users/arikt/documents/github/distanceFinder/v2/scripts/persist_selected_destination.py:459), acceptance at lines 384–392.

It requires multiple selected destinations and one seconds value, but does not require the known answer **300 seconds** or selected destinations exactly **{0,1}**.

Runnable Python, **unexecuted**:

```python
def broken_arrival(cost, time, **kwargs):
    n = cost.shape[0]
    # Ignores all costs and destination candidates.
    return np.zeros(n), np.zeros(n, dtype=np.int64)

with patch.object(p, "arrival_with_selected_destination",
                  side_effect=broken_arrival):
    control = p.destination_tie_control()

print(control)
assert control["total_destination_moves"] > 0
assert control["total_seconds_moves"] == 0
```

By inspection, relabelling maps the constant selected index back to original nodes **0, 1 and 2**; seconds remain **0**. Those are precisely the two acceptance conditions.

**Cost:** the control can certify movement when the algorithm never solves the constructed problem. Pin the absolute baseline answer and candidate set before interpreting movement.

The provenance mutation controls are stronger about the failure message and non-inert mutation, but their negative cases do not first establish that their unmodified input passes `verify_provenance`. Add that baseline assertion to isolate the cause.

## H. Figures, records and verified limits

The revised destination note still needs these corrections:

- Lines 147–154 overstate physical source identity: **A1**.
- Lines 156–160 overstate what the source mask check earns: **A2**.
- Lines 98–107 omit §4(c), invent a date requirement, and cannot claim complete NOTICE compliance: **B2**.
- Line 193’s “completely correctly” baseline is false: **G1**.
- Lines 215–219 should label source-grid figures and acknowledge the existing uint16 decoder: **F**.

For ledger instances 29–33:

- **29:** the useful conclusion is that fixture success does not establish that the particular shipped artifact loads. “Says nothing” is broader than necessary; model tests still provide algorithmic evidence. The proposed consumer-equivalent check is only partially implemented.
- **30:** the principle is right; its claim that all three requirements are now enforced is false.
- **31:** the set/count principle holds. Constant node identity and a missing refusal branch are separate omissions, not consequences of checking only one set member.
- **32:** the generalization is right and immediately exposes the remaining `verdicts`, `mask` and failed-compute cases.
- **33:** sound about missing obligations/declarations, but supplying a declaration establishes declared order, not independently verified order.

Verified in `node_repl`:

| Check | Result |
|---|---:|
| Baseline conformance | **75 passed** |
| Supplied mutations | **37/37 caught** |
| Inert supplied mutations | **0** |
| Source run-length index | **28,989 runs; 173,934 bytes** |
| Source lookup probes | **330,502; 0 mismatches** |

**Not executed:** the claimed **1,442 Python tests / 1,418 passed / 24 skipped**, Python controls, graph computations and Rasterio reprojection. The test-count arithmetic agrees; the execution claim remains unverified in this runtime.

### Read-only JavaScript reproducer setup

This is the runnable VM setup for the executed JavaScript cases above; it starts no child processes and writes no files.

```js
var fs = await import("node:fs");
var path = await import("node:path");
var vm = await import("node:vm");
var crypto = await import("node:crypto");

var D = "C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render";
var read = file => fs.readFileSync(path.join(D, file), "utf8");
var source = read("worker.js");
var harness = read("worker_conformance.mjs");
var vectors = JSON.parse(read("fixtures/conformance/vectors.json"));
var PUB = path.join(D, "fixtures/published");
var manifest = JSON.parse(fs.readFileSync(path.join(PUB, "manifest.json"), "utf8"));
var entry = manifest.layers[0];
var table = JSON.parse(fs.readFileSync(path.join(PUB, entry.dest_table), "utf8"));

var bytes = file => {
  var b = fs.readFileSync(path.join(D, file));
  return b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength);
};

var load = src => {
  var out = [];
  var ctx = vm.createContext({
    performance, ArrayBuffer, Uint8Array, Uint16Array, Uint32Array, Int8Array,
    self: { postMessage: m => out.push(m) }
  });
  vm.runInContext(src, ctx);
  return {
    send(m) {
      out = [];
      ctx.self.onmessage({data:m});
      return out.slice();
    }
  };
};

var fixtureInit = g => ({
  type:"init",
  manifest:{
    nrows:g.nrows, ncols:g.ncols, encoding:vectors.encoding,
    destination_plane_byte_order:vectors.destination_plane_byte_order,
    layers:structuredClone(g.layers)
  },
  values:g.layers.map(l => bytes("fixtures/conformance/" + l.value_file)),
  statuses:g.layers.map(l => bytes("fixtures/conformance/" + l.status_file)),
  routeFlags:g.layers.map(l => l.flag_file
    ? bytes("fixtures/conformance/" + l.flag_file) : null),
  destinations:g.layers.map(l => l.dest_file
    ? bytes("fixtures/conformance/" + l.dest_file) : null),
  destTables:structuredClone(g.dest_tables)
});
var swapGroup = vectors.groups.find(g => /survive a byte swap/.test(g.name));

var intercept = fn => new Proxy(fs, {
  get(target, key) {
    if (key !== "readFileSync") return target[key];
    return (file, ...args) => {
      var replacement = fn(String(file));
      return replacement === undefined
        ? target.readFileSync(file, ...args) : replacement;
    };
  }
});

var replay = (src, filesystem = fs) => {
  var logs = [], exitCode;
  var code = harness
    .replace(/^import .*;\r?\n/gm, "")
    .replace("const require = createRequire(import.meta.url);", "")
    .replace("const __dirname = path.dirname(fileURLToPath(import.meta.url));", "")
    .replace(
      /function loadWorker\(\) \{[\s\S]*?\r?\n\}\r?\n\r?\nfunction planeBytes/,
      "function loadWorker() { return factory(); }\nfunction planeBytes"
    );

  vm.runInNewContext(code, {
    __dirname:D, fs:filesystem, path, createHash:crypto.createHash,
    Buffer, ArrayBuffer, Uint8Array, Uint16Array, Uint32Array, Int8Array,
    performance,
    factory:() => {
      var w = load(src);
      return {send(m) {
        var out = w.send(m);
        var err = out.find(x => x.type === "error");
        if (err) throw Error(err.message);
        return out;
      }};
    },
    console:{
      log:s => logs.push(String(s)),
      error:s => logs.push(String(s))
    },
    process:{exit:n => { exitCode = n; }}
  });

  return {
    exitCode,
    passes:logs.filter(s => s.startsWith("PASS")).length,
    failures:logs.filter(s => s.startsWith("FAIL"))
  };
};

var mutationSource = read("mutate_worker.mjs");
var mutations = vm.runInNewContext(
  mutationSource.slice(
    mutationSource.indexOf("const MUTATIONS ="),
    mutationSource.indexOf("const original =")
  ) + "\nMUTATIONS;"
);

// Reproduce the reported baseline and all supplied mutation outcomes.
console.log(replay(source));
console.log(mutations.map(m => ({
  name:m.name,
  inert:m.apply(source) === source,
  ...replay(m.apply(source))
})));

var runByteswapControl = src => {
  var logs = [], exitCode;
  var control = read("byteswap_control.mjs")
    .replace(/^import .*;\r?\n/gm, "");
  var filesystem = intercept(file =>
    path.normalize(file) === path.join(D, "worker.js") ? src : undefined
  );
  try {
    vm.runInNewContext(control, {
      fs:filesystem, path, vm, performance,
      ArrayBuffer, Uint8Array, Uint16Array, Uint32Array, Int8Array,
      console:{log:s => logs.push(String(s))},
      process:{exit:n => {
        exitCode = n;
        throw Error("__CONTROL_EXIT__");
      }}
    });
  } catch (err) {
    if (err.message !== "__CONTROL_EXIT__") throw err;
  }
  return {exitCode, logs};
};
```
