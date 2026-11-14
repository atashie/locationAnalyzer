// worker_conformance.mjs — replay Python's conformance vectors through the REAL worker.
//
// S3.5: "A Python round-trip cannot protect the browser." `locfinder/wire.py` and `worker.js`
// implement the same decode in two languages; `tests/test_wire.py` proves the Python one agrees
// with `status.evaluate` on every published cell, and this proves the JavaScript one agrees with
// Python — on hand-built statuses, on the two-layer combination rule, and on a window of the real
// published layer that carries every status code it produces.
//
// worker.js is a classic Web Worker: it reads `self.onmessage` and calls `self.postMessage`. Node
// has neither, so this shims both and drives the worker through its real message protocol rather
// than reaching into its internals. The functions under test are therefore exactly the ones a
// browser runs.
//
// Run:  node spikes/g3-render/worker_conformance.mjs
// It is also run by tests/test_browser_conformance.py, so it cannot be forgotten.

import { createRequire } from 'module';
import { fileURLToPath } from 'url';
import { createHash } from 'crypto';
import fs from 'fs';
import path from 'path';

const require = createRequire(import.meta.url);
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FIXTURES = path.join(__dirname, 'fixtures', 'conformance');

const V_INCLUDED = 0, V_EXCLUDED = 1, V_UNKNOWN = 2;

// worker.js's own palette, recomputed here rather than imported, so a change to one side has to
// be made deliberately on the other.
const LITTLE_ENDIAN = new Uint8Array(new Uint32Array([1]).buffer)[0] === 1;
const packRGBA = (r, g, b, a) => (LITTLE_ENDIAN
  ? ((a << 24) | (b << 16) | (g << 8) | r) >>> 0
  : ((r << 24) | (g << 16) | (b << 8) | a) >>> 0);
const PX_IN = packRGBA(24, 119, 242, 150);
const PX_NODATA = packRGBA(60, 60, 60, 130);
const PX_OUT = 0;

let failures = 0;
function check(name, fn) {
  try {
    fn();
    console.log(`PASS  ${name}`);
  } catch (err) {
    failures++;
    console.error(`FAIL  ${name}\n      ${err && err.message ? err.message : err}`);
  }
}
function assert(cond, msg) { if (!cond) throw new Error(msg || 'assertion failed'); }

/** Load worker.js with `self` shimmed, and return a send/collect pair. */
function loadWorker() {
  const outbox = [];
  const selfShim = {
    postMessage: (msg) => outbox.push(msg),
    onmessage: null,
  };
  const prevSelf = globalThis.self;
  const prevPerf = globalThis.performance;
  globalThis.self = selfShim;
  if (!globalThis.performance) {
    globalThis.performance = { now: () => Date.now(), timeOrigin: 0 };
  }
  // A fresh module instance per group: the worker holds layer state in a module-level object.
  delete require.cache[require.resolve(path.join(__dirname, 'worker.js'))];
  require(path.join(__dirname, 'worker.js'));
  const handler = selfShim.onmessage;
  globalThis.self = prevSelf;
  globalThis.performance = prevPerf;
  if (typeof handler !== 'function') throw new Error('worker.js did not install self.onmessage');

  return {
    send(msg) {
      outbox.length = 0;
      const prev = globalThis.self;
      const prevP = globalThis.performance;
      globalThis.self = selfShim;
      if (!globalThis.performance) globalThis.performance = { now: () => Date.now(), timeOrigin: 0 };
      try {
        handler({ data: msg });
      } finally {
        globalThis.self = prev;
        globalThis.performance = prevP;
      }
      const err = outbox.find((m) => m && m.type === 'error');
      if (err) throw new Error(`worker reported: ${err.message}`);
      return outbox.slice();
    },
  };
}

function planeBytes(file) {
  const buf = fs.readFileSync(path.join(FIXTURES, file));
  // Copy into a standalone ArrayBuffer: Node's Buffer is a view into a shared pool, so passing
  // `buf.buffer` straight through would hand the worker the whole pool and fail its length check.
  const out = new ArrayBuffer(buf.length);
  new Uint8Array(out).set(buf);
  return out;
}

const vectors = JSON.parse(fs.readFileSync(path.join(FIXTURES, 'vectors.json'), 'utf8'));

for (const group of vectors.groups) {
  // Two workers per group when the group discloses: one initialised WITH the flag planes and one
  // WITHOUT, so "the plane moves no verdict" is checked against the same expectations rather than
  // argued. A `withhold_flags` case runs on the second.
  const discloses = group.layers.some((l) => l.flag_file);
  const worker = loadWorker();
  const plainWorker = discloses ? loadWorker() : null;
  const names = group.layers.some((l) => l.dest_file);
  const entry = (l) => ({ id: l.id, horizon_s: l.horizon_s,
    ...(l.flag_file ? { flag_file: l.flag_file } : {}),
    ...(l.dest_file ? { dest_file: l.dest_file, dest_table: l.dest_table,
                        dest_byte_order: l.dest_byte_order, dest_none: l.dest_none } : {}) });
  const manifest = {
    nrows: group.nrows,
    ncols: group.ncols,
    encoding: vectors.encoding,
    destination_plane_byte_order: vectors.destination_plane_byte_order,
    layers: group.layers.map(entry),
  };
  // The same bundle with every disclosure removed, which must still be readable.
  const plainManifest = {
    nrows: group.nrows, ncols: group.ncols, encoding: vectors.encoding,
    layers: group.layers.map((l) => ({ id: l.id, horizon_s: l.horizon_s })),
  };
  const initArgs = (m) => ({
    type: 'init',
    manifest: m,
    values: group.layers.map((l) => planeBytes(l.value_file)),
    statuses: group.layers.map((l) => planeBytes(l.status_file)),
    routeFlags: group.layers.map((l) => (l.flag_file ? planeBytes(l.flag_file) : null)),
    destinations: group.layers.map((l) => (l.dest_file ? planeBytes(l.dest_file) : null)),
    destTables: (group.dest_tables || group.layers.map(() => null)),
  });
  check(`${group.name}: init`, () => {
    const out = worker.send(initArgs(manifest));
    const ready = out.find((m) => m.type === 'ready');
    assert(ready, 'no ready message');
    assert(ready.layerCount === group.layers.length, 'wrong layer count');
    assert(ready.disclosesRoutes === discloses,
      `disclosesRoutes ${ready.disclosesRoutes}, expected ${discloses}`);
    assert(ready.namesDestinations === names,
      `namesDestinations ${ready.namesDestinations}, expected ${names}`);
    if (group.expect_names_destinations !== undefined) {
      assert(ready.namesDestinations === group.expect_names_destinations,
        'the vectors and the worker disagree about whether this group names destinations');
    }
    if (group.expect_discloses_routes !== undefined) {
      assert(ready.disclosesRoutes === group.expect_discloses_routes,
        'the vectors and the worker disagree about whether this group discloses');
    }
    if (plainWorker) {
      const p = plainWorker.send({ ...initArgs(plainManifest), routeFlags: undefined });
      const pr = p.find((m) => m.type === 'ready');
      assert(pr && pr.disclosesRoutes === false,
        'a bundle with no flag_file must report that it does not disclose');
    }
  });

  for (const c of group.cases) {
    check(`${group.name}: ${c.name}`, () => {
      // A withheld-flags case runs on the worker that never received the planes, so the verdict
      // expectations below are met by a decoder that cannot see a disclosure at all.
      const w = c.withhold_flags ? plainWorker : worker;
      assert(w, 'this case needs a non-disclosing worker and the group has none');
      const out = w.send({
        type: 'compute', seq: 1, tEvent: 0,
        thresholds: c.thresholds, enabled: c.enabled,
      });
      const res = out.find((m) => m.type === 'result');
      assert(res, 'no result message');
      const n = group.nrows * group.ncols;
      assert(res.rgba.byteLength === n * 4, 'rgba buffer is the wrong size');

      if (c.counts) {
        assert(res.inCount === c.counts.included,
          `included ${res.inCount} != ${c.counts.included}`);
        assert(res.excludedCount === c.counts.excluded,
          `excluded ${res.excludedCount} != ${c.counts.excluded}`);
        assert(res.nodataCount === c.counts.unknown,
          `unknown ${res.nodataCount} != ${c.counts.unknown}`);
      }

      // Ask the worker what it decided. Reconstructing this from the RGBA buffer was the
      // mistake pass 43 F2 found: included is readable from the mask, but EXCLUDED and UNKNOWN
      // are only distinguishable where the hatch stripe falls, so three quarters of the cells
      // were compared against nothing — and the real-layer window, which has no inline expected
      // array, was compared against nothing at all. A worker that returned UNKNOWN for NO_PATH,
      // and one that rotated the entire raster by 10,007 cells, both passed all 37 checks.
      // A disclosure must never be an eligibility input: whichever worker ran, the counts and
      // the verdict plane below are compared against the same expectations.
      if (c.restricted_included === null) {
        assert(res.restrictedIncludedCount === null,
          `restrictedIncludedCount ${res.restrictedIncludedCount}, expected null when nothing `
          + 'discloses -- "not telling you" must not read as "none"');
      } else if (c.restricted_included !== undefined) {
        assert(res.restrictedIncludedCount === c.restricted_included,
          `restrictedIncludedCount ${res.restrictedIncludedCount}, expected `
          + `${c.restricted_included}`);
      }

      const vOut = w.send({ type: 'verdicts', reqId: 1 });
      const vMsg = vOut.find((m) => m.type === 'verdicts');
      assert(vMsg, 'no verdicts message');
      const verdicts = new Int8Array(vMsg.verdicts);
      assert(verdicts.length === n, `verdict plane is ${verdicts.length}, expected ${n}`);

      // The destination query, cell by cell. Every field is compared against what the vectors
      // record, and the whole place SET against the side table the worker was handed.
      //
      // Pass 49 finding 5: comparing the ordinal, the count and the FIRST place's name left four
      // real defects passing all 71 checks -- wrong names on every place after the first, every
      // place replaced by a copy of the first (the count survives), a constant `node_index`
      // (never compared at all), and the removal of the named-implies-OK half of the init
      // invariant. The set IS the answer here, so checking one member of it is not checking it.
      //
      // Pass 49 finding 6 also corrected why these comparisons matter. A big-endian read is not
      // caught by the name in particular; it is caught by comparing against a RECORDED
      // expectation at all. What a swap survives is the structural bounds check.
      for (const q of (c.destination_at || [])) {
        const dOut = w.send({ type: 'destinationAt', reqId: 1, row: q.row, col: q.col });
        const d = dOut.find((m) => m.type === 'destinationAt');
        assert(d, `no destinationAt reply for (${q.row}, ${q.col})`);
        assert(d.included === q.included,
          `(${q.row}, ${q.col}) included ${d.included}, expected ${q.included}`);
        if (q.names === null) {
          assert(d.namesDestination === null,
            `(${q.row}, ${q.col}) namesDestination ${JSON.stringify(d.namesDestination)}, `
            + 'expected null -- "this bundle does not say" must not render as an empty list');
          continue;
        }
        assert(Array.isArray(d.namesDestination),
          `(${q.row}, ${q.col}) expected a list of destinations`);
        assert(d.namesDestination.length === q.names.length,
          `(${q.row}, ${q.col}) ${d.namesDestination.length} destinations, expected `
          + `${q.names.length}`);
        for (let i = 0; i < q.names.length; i++) {
          const got = d.namesDestination[i];
          const want = q.names[i];
          assert(got.layer === want.layer,
            `(${q.row}, ${q.col}) layer ${got.layer}, expected ${want.layer}`);
          assert(got.ordinal === want.ordinal,
            `(${q.row}, ${q.col}) ordinal ${got.ordinal}, expected ${want.ordinal}`);
          assert(got.placeCount === want.place_count,
            `(${q.row}, ${q.col}) placeCount ${got.placeCount}, expected ${want.place_count}`);
          assert(Array.isArray(got.places) && got.places.length === want.place_count,
            `(${q.row}, ${q.col}) places must be a list as long as placeCount -- the set IS the `
            + 'answer where a node carries more than one place');
          assert(got.places[0].name === want.first_place_name,
            `(${q.row}, ${q.col}) first place ${JSON.stringify(got.places[0].name)}, expected `
            + `${JSON.stringify(want.first_place_name)}`);
          // The node the time was measured to. Never compared before pass 49, so a constant
          // stood in for it through 71 passing checks.
          assert(got.nodeIndex === want.node_index,
            `(${q.row}, ${q.col}) nodeIndex ${got.nodeIndex}, expected ${want.node_index}`);
          // Every name, in order. Catches a defect that preserves the count.
          const gotNames = got.places.map((pl) => pl.name);
          assert(JSON.stringify(gotNames) === JSON.stringify(want.place_names),
            `(${q.row}, ${q.col}) place names ${JSON.stringify(gotNames)}, expected `
            + `${JSON.stringify(want.place_names)}`);
          // And the whole record set, against the table this worker was handed. This pins the
          // reply to its input: a worker that rewrites, reorders or duplicates a record fails
          // here even where the vectors record only names.
          const layerIndex = group.layers.findIndex((l) => l.id === want.layer);
          const entry = group.dest_tables[layerIndex].destinations[want.ordinal];
          assert(JSON.stringify(got.places) === JSON.stringify(entry.places),
            `(${q.row}, ${q.col}) the places returned are not the side table's record set for `
            + `ordinal ${want.ordinal}`);
        }
      }

      const maskOut = w.send({ type: 'mask', reqId: 1 });
      const maskMsg = maskOut.find((m) => m.type === 'mask');
      assert(maskMsg, 'no mask message');
      const mask = new Uint8Array(maskMsg.mask);

      // The mask is a CONSUMER OUTPUT, not a debug aid: app.js polygonizes it at a 0.5
      // threshold, so any non-zero byte lands inside the polygon. Pass 44 F1: asserting only
      // `(mask[i] === 1) === (verdict === INCLUDED)` let `mask[p] = 2` through at excluded
      // cells, which promotes 225,520 excluded pixels into the polygon's included set at 15
      // minutes. The byte is checked exactly, not for truthiness.
      assert(mask.length === n, `mask is ${mask.length} bytes, expected ${n}`);
      for (let i = 0; i < n; i++) {
        const want = verdicts[i] === V_INCLUDED ? 1 : 0;
        assert(mask[i] === want,
          `cell ${i}: mask byte ${mask[i]}, expected exactly ${want} for verdict ${verdicts[i]}`);
      }
      // And the counts must match the plane they claim to summarise.
      let ci = 0, ce = 0, cu = 0;
      for (let i = 0; i < n; i++) {
        if (verdicts[i] === V_INCLUDED) ci++;
        else if (verdicts[i] === V_EXCLUDED) ce++;
        else cu++;
      }
      assert(ci === res.inCount && ce === res.excludedCount && cu === res.nodataCount,
        `counts ${res.inCount}/${res.excludedCount}/${res.nodataCount} against plane ${ci}/${ce}/${cu}`);

      if (c.verdicts) {
        for (let i = 0; i < n; i++) {
          assert(verdicts[i] === c.verdicts[i],
            `cell ${i}: worker ${verdicts[i]}, python ${c.verdicts[i]}`);
        }
      }

      // The verdict plane is what the harness compares, so on its own it would let a defect
      // corrupt what a VIEWER sees while leaving the plane right. Every pixel is therefore
      // checked against the verdict it claims to render.
      const px = new Uint32Array(res.rgba);
      let p2 = 0;
      for (let r = 0; r < group.nrows; r++) {
        for (let col = 0; col < group.ncols; col++, p2++) {
          const onStripe = ((r + col) & 7) < 2;
          let want;
          if (verdicts[p2] === V_INCLUDED) want = PX_IN;
          else if (verdicts[p2] === V_UNKNOWN) want = onStripe ? PX_NODATA : PX_OUT;
          else want = PX_OUT;
          assert(px[p2] === want,
            `cell ${p2} verdict ${verdicts[p2]}: pixel ${px[p2]} but ${want} renders it`);
        }
      }
      if (c.verdict_sha256_32) {
        // Python hashes the same Int8Array bytes of the same three-way plane. It used to hash
        // three-way verdicts while this hashed the binary mask, and the result was never
        // compared to anything — a digest computed and thrown away is not a check.
        const h = createHash('sha256').update(Buffer.from(verdicts.buffer, 0, n))
          .digest('hex').slice(0, 32);
        assert(h === c.verdict_sha256_32,
          `verdict digest ${h} != python ${c.verdict_sha256_32}`);
      }
      assert(c.verdicts || c.verdict_sha256_32,
        'this case asserts nothing about the arrangement of its verdicts');
    });
  }
}

// --------------------------------------------------------------------- the refusals

check('a manifest in an unknown encoding is refused, not guessed at', () => {
  const worker = loadWorker();
  let threw = false;
  try {
    worker.send({
      type: 'init',
      manifest: { nrows: 1, ncols: 2, encoding: 'uint8-minutes-ceil-v0',
                  layers: [{ id: 'x', horizon_s: 7200 }] },
      values: [new ArrayBuffer(2)], statuses: [new ArrayBuffer(2)],
    });
  } catch (err) {
    threw = /is not one of/.test(err.message);
  }
  assert(threw, 'the worker accepted a v1 manifest');
});

check('a layer with no horizon is refused, because BEYOND_HORIZON cannot be decided', () => {
  const worker = loadWorker();
  let threw = false;
  try {
    worker.send({
      type: 'init',
      manifest: { nrows: 1, ncols: 2, encoding: 'published-v2', layers: [{ id: 'x' }] },
      values: [new ArrayBuffer(2)], statuses: [new ArrayBuffer(2)],
    });
  } catch (err) {
    threw = /horizon_s/.test(err.message);
  }
  assert(threw, 'the worker accepted a layer with no horizon');
});

check('a plane of the wrong size is refused', () => {
  const worker = loadWorker();
  let threw = false;
  try {
    worker.send({
      type: 'init',
      manifest: { nrows: 10, ncols: 10, encoding: 'published-v2',
                  layers: [{ id: 'x', horizon_s: 7200 }] },
      values: [new ArrayBuffer(4)], statuses: [new ArrayBuffer(100)],
    });
  } catch (err) {
    threw = /expected nrows\*ncols/.test(err.message);
  }
  assert(threw, 'the worker accepted a short plane');
});

check('an undefined status code is refused rather than rendered', () => {
  const worker = loadWorker();
  worker.send({
    type: 'init',
    manifest: { nrows: 1, ncols: 1, encoding: 'published-v2',
                layers: [{ id: 'x', horizon_s: 7200 }] },
    values: [new ArrayBuffer(1)],
    statuses: [(() => { const b = new ArrayBuffer(1); new Uint8Array(b)[0] = 99; return b; })()],
  });
  let threw = false;
  try {
    worker.send({ type: 'compute', seq: 1, tEvent: 0, thresholds: [10], enabled: [true] });
  } catch (err) {
    threw = /does not define/.test(err.message);
  }
  assert(threw, 'the worker rendered an undefined status code');
});


check('a v2 bundle is still readable and reports that it does not disclose', () => {
  const worker = loadWorker();
  const out = worker.send({
    type: 'init',
    manifest: { nrows: 1, ncols: 1, encoding: 'published-v2',
                layers: [{ id: 'x', horizon_s: 7200 }] },
    values: [new ArrayBuffer(1)],
    statuses: [new ArrayBuffer(1)],
  });
  const ready = out.find((m) => m.type === 'ready');
  assert(ready, 'no ready message');
  assert(ready.disclosesRoutes === false, 'a v2 bundle cannot disclose');
});

check('a declared flag plane that does not arrive is refused, not treated as absent', () => {
  const worker = loadWorker();
  let threw = false;
  try {
    worker.send({
      type: 'init',
      manifest: { nrows: 1, ncols: 1, encoding: 'published-v3',
                  layers: [{ id: 'x', horizon_s: 7200, flag_file: 'x.flag.bin' }] },
      values: [new ArrayBuffer(1)], statuses: [new ArrayBuffer(1)],
    });
  } catch (err) {
    threw = /route flag/.test(err.message);
  }
  assert(threw, 'a missing declared plane became "no route is restricted"');
});

check('a route flag set where the status is not OK is refused', () => {
  const worker = loadWorker();
  const one = (v) => { const b = new ArrayBuffer(1); new Uint8Array(b)[0] = v; return b; };
  let threw = false;
  try {
    worker.send({
      type: 'init',
      manifest: { nrows: 1, ncols: 1, encoding: 'published-v3',
                  layers: [{ id: 'x', horizon_s: 7200, flag_file: 'x.flag.bin' }] },
      values: [one(255)], statuses: [one(1)], routeFlags: [one(1)],
    });
  } catch (err) {
    threw = /no route for it to describe/.test(err.message);
  }
  assert(threw, 'a flag was accepted where the format says there is no journey');
});

check('an undefined route-flag byte is refused', () => {
  const worker = loadWorker();
  const one = (v) => { const b = new ArrayBuffer(1); new Uint8Array(b)[0] = v; return b; };
  let threw = false;
  try {
    worker.send({
      type: 'init',
      manifest: { nrows: 1, ncols: 1, encoding: 'published-v3',
                  layers: [{ id: 'x', horizon_s: 7200, flag_file: 'x.flag.bin' }] },
      values: [one(5)], statuses: [one(0)], routeFlags: [one(2)],
    });
  } catch (err) {
    threw = /does not define/.test(err.message);
  }
  assert(threw, 'an undefined flag byte was accepted');
});


check('a plane that arrives for a layer the manifest does not declare is refused', () => {
  const worker = loadWorker();
  const one = (v) => { const b = new ArrayBuffer(1); new Uint8Array(b)[0] = v; return b; };
  let threw = false;
  try {
    worker.send({
      type: 'init',
      manifest: { nrows: 1, ncols: 1, encoding: 'published-v3',
                  layers: [{ id: 'declares', horizon_s: 7200, flag_file: 'a.flag.bin' },
                           { id: 'silent', horizon_s: 7200 }] },
      values: [one(5), one(5)], statuses: [one(0), one(0)],
      routeFlags: [one(1), one(1)],
    });
  } catch (err) {
    threw = /does not declare/.test(err.message);
  }
  assert(threw, 'a plane the manifest does not declare was accepted, so the payload and the '
    + 'manifest were allowed to disagree about what the layer discloses');
});

check('a null slot is legal exactly where the manifest declares no plane', () => {
  const worker = loadWorker();
  const one = (v) => { const b = new ArrayBuffer(1); new Uint8Array(b)[0] = v; return b; };
  // Pass 48: this CRASHED on `null.byteLength`. One disclosing layer beside one plain layer is
  // the ordinary shape as soon as a second criterion exists.
  const out = worker.send({
    type: 'init',
    manifest: { nrows: 1, ncols: 1, encoding: 'published-v3',
                layers: [{ id: 'declares', horizon_s: 7200, flag_file: 'a.flag.bin' },
                         { id: 'silent', horizon_s: 7200 }] },
    values: [one(5), one(5)], statuses: [one(0), one(0)],
    routeFlags: [one(1), null],
  });
  const ready = out.find((m) => m.type === 'ready');
  assert(ready, 'a mixed bundle did not initialise');
  assert(ready.disclosesRoutes === true, 'a bundle with one disclosing layer discloses');
});


check('a big-endian read of the destination plane is refused, not guessed at', () => {
  const worker = loadWorker();
  const one = (v) => { const b = new ArrayBuffer(1); new Uint8Array(b)[0] = v; return b; };
  const u16 = (v) => { const b = new ArrayBuffer(2); const a = new Uint8Array(b);
    a[0] = v & 0xff; a[1] = v >> 8; return b; };
  const table = { destinations: [{ ordinal: 0, node_index: 1, place_count: 1,
                                   places: [{ gers_id: 'x', name: 'X' }] }] };
  let threw = false;
  try {
    worker.send({
      type: 'init',
      manifest: { nrows: 1, ncols: 1, encoding: 'published-v4',
                  destination_plane_byte_order: 'big',
                  layers: [{ id: 'x', horizon_s: 7200, dest_file: 'x.dest.bin' }] },
      values: [one(5)], statuses: [one(0)], destinations: [u16(0)], destTables: [table],
    });
  } catch (err) {
    threw = /little-/.test(err.message);
  }
  assert(threw, 'a declared big-endian destination plane was read anyway, which yields VALID '
    + 'wrong ordinals rather than an error');
});

check('a published time with no destination is refused as a contradiction', () => {
  const worker = loadWorker();
  const one = (v) => { const b = new ArrayBuffer(1); new Uint8Array(b)[0] = v; return b; };
  const u16 = (v) => { const b = new ArrayBuffer(2); const a = new Uint8Array(b);
    a[0] = v & 0xff; a[1] = (v >> 8) & 0xff; return b; };
  const table = { destinations: [{ ordinal: 0, node_index: 1, place_count: 1,
                                   places: [{ gers_id: 'x', name: 'X' }] }] };
  let threw = false;
  try {
    worker.send({
      type: 'init',
      manifest: { nrows: 1, ncols: 1, encoding: 'published-v4',
                  destination_plane_byte_order: 'little',
                  layers: [{ id: 'x', horizon_s: 7200, dest_file: 'x.dest.bin' }] },
      values: [one(5)], statuses: [one(0)], destinations: [u16(65535)], destTables: [table],
    });
  } catch (err) {
    threw = /names no destination/.test(err.message);
  }
  assert(threw, 'DEST_NONE beside a published time was accepted; unlike a clear route flag that '
    + 'is a contradiction, because a published time is a time to somewhere');
});

check('a destination ordinal past the end of the side table is refused', () => {
  const worker = loadWorker();
  const one = (v) => { const b = new ArrayBuffer(1); new Uint8Array(b)[0] = v; return b; };
  const u16 = (v) => { const b = new ArrayBuffer(2); const a = new Uint8Array(b);
    a[0] = v & 0xff; a[1] = (v >> 8) & 0xff; return b; };
  const table = { destinations: [{ ordinal: 0, node_index: 1, place_count: 1,
                                   places: [{ gers_id: 'x', name: 'X' }] }] };
  let threw = false;
  try {
    worker.send({
      type: 'init',
      manifest: { nrows: 1, ncols: 1, encoding: 'published-v4',
                  destination_plane_byte_order: 'little',
                  layers: [{ id: 'x', horizon_s: 7200, dest_file: 'x.dest.bin' }] },
      values: [one(5)], statuses: [one(0)], destinations: [u16(7)], destTables: [table],
    });
  } catch (err) {
    threw = /side table holds/.test(err.message);
  }
  assert(threw, 'an ordinal with no table entry was accepted');
});

check('a destination plane with no side table is refused', () => {
  const worker = loadWorker();
  const one = (v) => { const b = new ArrayBuffer(1); new Uint8Array(b)[0] = v; return b; };
  const u16 = (v) => { const b = new ArrayBuffer(2); const a = new Uint8Array(b);
    a[0] = v & 0xff; a[1] = (v >> 8) & 0xff; return b; };
  let threw = false;
  try {
    worker.send({
      type: 'init',
      manifest: { nrows: 1, ncols: 1, encoding: 'published-v4',
                  destination_plane_byte_order: 'little',
                  layers: [{ id: 'x', horizon_s: 7200, dest_file: 'x.dest.bin' }] },
      values: [one(5)], statuses: [one(0)], destinations: [u16(0)], destTables: [null],
    });
  } catch (err) {
    threw = /names nothing a reader can resolve/.test(err.message);
  }
  assert(threw, 'ordinals shipped with no table to resolve them');
});

// Pass 49 finding 7. The guard accepted a manifest that said NOTHING about the byte order and
// read little-endian by default, so a plane written the other way round resolved to in-range
// ordinals and confident wrong names. The published rule is that an order a decoder cannot
// confirm is refused; silence is not confirmation.
check('a destination plane with no declared byte order is refused', () => {
  const worker = loadWorker();
  const one = (v) => { const b = new ArrayBuffer(1); new Uint8Array(b)[0] = v; return b; };
  const u16 = (v) => { const b = new ArrayBuffer(2); const a = new Uint8Array(b);
    a[0] = v & 0xff; a[1] = (v >> 8) & 0xff; return b; };
  const table = { destinations: [{ ordinal: 0, node_index: 1, place_count: 1,
                                   places: [{ gers_id: 'x', name: 'X' }] }] };
  let threw = false;
  try {
    worker.send({
      type: 'init',
      manifest: { nrows: 1, ncols: 1, encoding: 'published-v4',
                  layers: [{ id: 'x', horizon_s: 7200, dest_file: 'x.dest.bin' }] },
      values: [one(5)], statuses: [one(0)], destinations: [u16(0)], destTables: [table],
    });
  } catch (err) {
    threw = /declares no destination byte order/.test(err.message);
  }
  assert(threw, 'an undeclared byte order was read as little-endian by default, which is a guess '
    + 'at an ordinal the decoder cannot verify');
});

// Pass 49 finding 5. The init invariant has two halves and only one had a refusal case, so
// deleting the named-implies-OK half passed all 71 checks.
check('a destination named where no time is published is refused', () => {
  const worker = loadWorker();
  const one = (v) => { const b = new ArrayBuffer(1); new Uint8Array(b)[0] = v; return b; };
  const u16 = (v) => { const b = new ArrayBuffer(2); const a = new Uint8Array(b);
    a[0] = v & 0xff; a[1] = (v >> 8) & 0xff; return b; };
  const table = { destinations: [{ ordinal: 0, node_index: 1, place_count: 1,
                                   places: [{ gers_id: 'x', name: 'X' }] }] };
  let threw = false;
  try {
    worker.send({
      type: 'init',
      manifest: { nrows: 1, ncols: 1, encoding: 'published-v4',
                  destination_plane_byte_order: 'little',
                  layers: [{ id: 'x', horizon_s: 7200, dest_file: 'x.dest.bin' }] },
      // OFF_NETWORK, so there is no journey -- and ordinal 0 names a destination for it.
      values: [one(255)], statuses: [one(1)], destinations: [u16(0)], destTables: [table],
    });
  } catch (err) {
    threw = /no journey for it to be the/.test(err.message);
  }
  assert(threw, 'a destination was named at a cell with no published journey; the invariant has '
    + 'TWO directions and this is the one that had no refusal case');
});

// Pass 49 finding 11. `verdict` is allocated at init and zero-filled, and 0 is INCLUDED, so a
// query before any compute used to answer `included: true` and name a shop for a cell no
// criterion had been applied to. Allocation is not evaluation.
check('a destination query before any compute says nothing has been computed', () => {
  const worker = loadWorker();
  const one = (v) => { const b = new ArrayBuffer(1); new Uint8Array(b)[0] = v; return b; };
  const u16 = (v) => { const b = new ArrayBuffer(2); const a = new Uint8Array(b);
    a[0] = v & 0xff; a[1] = (v >> 8) & 0xff; return b; };
  const table = { destinations: [{ ordinal: 0, node_index: 1, place_count: 1,
                                   places: [{ gers_id: 'x', name: 'X' }] }] };
  worker.send({
    type: 'init',
    manifest: { nrows: 1, ncols: 1, encoding: 'published-v4',
                destination_plane_byte_order: 'little',
                layers: [{ id: 'x', horizon_s: 7200, dest_file: 'x.dest.bin' }] },
    values: [one(5)], statuses: [one(0)], destinations: [u16(0)], destTables: [table],
  });
  const out = worker.send({ type: 'destinationAt', reqId: 1, row: 0, col: 0 });
  const d = out.find((m) => m.type === 'destinationAt');
  assert(d, 'no destinationAt reply');
  assert(d.notComputed === true, 'a query before any compute did not say so');
  assert(d.included === null, `included ${d.included}, expected null -- "nothing has been `
    + 'evaluated" is not "included" and is not "excluded"');
  assert(d.namesDestination === null, 'a destination was named before any compute ran');
  // And after a compute the same cell answers normally, so the guard is not simply off.
  worker.send({ type: 'compute', seq: 1, thresholds: [10], enabled: [true] });
  const after = worker.send({ type: 'destinationAt', reqId: 2, row: 0, col: 0 })
    .find((m) => m.type === 'destinationAt');
  assert(after.notComputed === undefined && after.included === true
    && after.namesDestination[0].places[0].name === 'X',
    'the lifecycle guard blocks a legitimate query after a compute');
});

// ---------------------------------------------------------------------------------------------
// The SHIPPED bundle, loaded the way the page loads it.
//
// Pass 49 finding 2 was a release blocker that all 71 of the checks above were blind to: the
// published side table contained 85 bare `NaN` tokens, so `JSON.parse` -- and therefore
// `Response.json()` -- threw before the worker was ever constructed. The page could not display
// a destination at all. Every check above builds its own fixture, so not one byte of the real
// artifact had ever been through this harness.
//
// A fixture is a model of the artifact. Passing on the model says nothing about the artifact.
check('the shipped published bundle loads the way the page loads it', () => {
  const dir = path.join(__dirname, 'fixtures', 'published');
  if (!fs.existsSync(path.join(dir, 'manifest.json'))) {
    throw new Error('no published fixture bundle to check; export one before running this');
  }
  const bytesOf = (file) => {
    const buf = fs.readFileSync(path.join(dir, file));
    const out = new ArrayBuffer(buf.length);
    new Uint8Array(out).set(buf);
    return out;
  };
  // JSON.parse, not a tolerant reader. This is the browser's parser and it rejects NaN,
  // Infinity, trailing commas and comments.
  const manifest = JSON.parse(fs.readFileSync(path.join(dir, 'manifest.json'), 'utf8'));
  const tables = manifest.layers.map((l) => (l.dest_table
    ? JSON.parse(fs.readFileSync(path.join(dir, l.dest_table), 'utf8'))
    : null));
  const worker = loadWorker();
  const ready = worker.send({
    type: 'init',
    manifest,
    values: manifest.layers.map((l) => bytesOf(l.value_file)),
    statuses: manifest.layers.map((l) => bytesOf(l.status_file)),
    routeFlags: manifest.layers.map((l) => (l.flag_file ? bytesOf(l.flag_file) : null)),
    destinations: manifest.layers.map((l) => (l.dest_file ? bytesOf(l.dest_file) : null)),
    destTables: tables,
  }).find((m) => m.type === 'ready');
  assert(ready, 'the shipped bundle did not initialise');
  // The reported byte count must include every plane that arrived, the uint16 destination plane
  // included -- pass 49 finding 9 found it omitted, which understated the bundle by two thirds.
  const n = manifest.nrows * manifest.ncols;
  const expectBytes = manifest.layers.reduce((sum, l) => sum + n * (2
    + (l.flag_file ? 1 : 0) + (l.dest_file ? 2 : 0)), 0);
  assert(ready.bytes === expectBytes,
    `ready.bytes ${ready.bytes}, expected ${expectBytes} -- a byte count that omits a plane`);
  worker.send({ type: 'compute', seq: 1, thresholds: manifest.layers.map(() => 254),
                enabled: manifest.layers.map(() => true) });
  // Find a cell that actually names something and resolve it, so the table is not merely
  // parsed but used.
  const dest = new Uint16Array(bytesOf(manifest.layers[0].dest_file));
  let named = -1;
  for (let p = 0; p < dest.length; p++) if (dest[p] !== 65535) { named = p; break; }
  assert(named >= 0, 'the shipped destination plane names nothing');
  const d = worker.send({ type: 'destinationAt', reqId: 1,
                          row: Math.floor(named / manifest.ncols), col: named % manifest.ncols })
    .find((m) => m.type === 'destinationAt');
  assert(d && d.namesDestination && d.namesDestination.length,
    'the shipped bundle named no destination at a cell whose plane holds an ordinal');
  const places = d.namesDestination[0].places;
  assert(Array.isArray(places) && places.length === d.namesDestination[0].placeCount,
    'the shipped place set is not as long as its own count');
  assert(places.every((pl) => typeof pl.gers_id === 'string' && pl.gers_id.length),
    'a shipped place record carries no GERS id');
});

check('a v3 bundle is readable and reports that it names no destination', () => {
  const worker = loadWorker();
  const out = worker.send({
    type: 'init',
    manifest: { nrows: 1, ncols: 1, encoding: 'published-v3',
                layers: [{ id: 'x', horizon_s: 7200 }] },
    values: [new ArrayBuffer(1)], statuses: [new ArrayBuffer(1)],
  });
  const ready = out.find((m) => m.type === 'ready');
  assert(ready, 'no ready message');
  assert(ready.namesDestinations === false, 'a v3 bundle cannot name a destination');
});

console.log(failures === 0
  ? `\nall browser conformance checks passed`
  : `\n${failures} browser conformance check(s) FAILED`);
process.exit(failures === 0 ? 0 : 1);
