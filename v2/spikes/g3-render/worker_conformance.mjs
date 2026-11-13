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
  const worker = loadWorker();
  const manifest = {
    nrows: group.nrows,
    ncols: group.ncols,
    encoding: vectors.encoding,
    layers: group.layers.map((l) => ({ id: l.id, horizon_s: l.horizon_s })),
  };
  check(`${group.name}: init`, () => {
    const out = worker.send({
      type: 'init',
      manifest,
      values: group.layers.map((l) => planeBytes(l.value_file)),
      statuses: group.layers.map((l) => planeBytes(l.status_file)),
    });
    const ready = out.find((m) => m.type === 'ready');
    assert(ready, 'no ready message');
    assert(ready.layerCount === group.layers.length, 'wrong layer count');
  });

  for (const c of group.cases) {
    check(`${group.name}: ${c.name}`, () => {
      const out = worker.send({
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
      const vOut = worker.send({ type: 'verdicts', reqId: 1 });
      const vMsg = vOut.find((m) => m.type === 'verdicts');
      assert(vMsg, 'no verdicts message');
      const verdicts = new Int8Array(vMsg.verdicts);
      assert(verdicts.length === n, `verdict plane is ${verdicts.length}, expected ${n}`);

      const maskOut = worker.send({ type: 'mask', reqId: 1 });
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
      manifest: { nrows: 1, ncols: 2, encoding: 'uint8-minutes-ceil-v1',
                  layers: [{ id: 'x', horizon_s: 7200 }] },
      values: [new ArrayBuffer(2)], statuses: [new ArrayBuffer(2)],
    });
  } catch (err) {
    threw = /is not published-v2/.test(err.message);
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

console.log(failures === 0
  ? `\nall browser conformance checks passed`
  : `\n${failures} browser conformance check(s) FAILED`);
process.exit(failures === 0 ? 0 : 1);
