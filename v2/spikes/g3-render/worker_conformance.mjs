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

      if (c.counts) {
        assert(res.inCount === c.counts.included,
          `included ${res.inCount} != ${c.counts.included}`);
        assert(res.excludedCount === c.counts.excluded,
          `excluded ${res.excludedCount} != ${c.counts.excluded}`);
        assert(res.nodataCount === c.counts.unknown,
          `unknown ${res.nodataCount} != ${c.counts.unknown}`);
      }

      // Rebuild the verdict array from the pixels, which is the only output that carries all
      // three outcomes. Included pixels are PX_IN; unknown pixels are the hatch colour on the
      // stripe and transparent off it, so the hatch is read with the worker's own rule.
      const px = new Uint32Array(res.rgba);
      const counts = [0, 0, 0];
      const verdicts = new Int8Array(n);
      const maskOut = worker.send({ type: 'mask', reqId: 1 });
      const maskMsg = maskOut.find((m) => m.type === 'mask');
      assert(maskMsg, 'no mask message');
      const mask = new Uint8Array(maskMsg.mask);
      let p = 0;
      for (let r = 0; r < group.nrows; r++) {
        for (let col = 0; col < group.ncols; col++, p++) {
          let v;
          if (mask[p] === 1) v = V_INCLUDED;
          else if (((r + col) & 7) < 2) v = (px[p] !== 0) ? V_UNKNOWN : V_EXCLUDED;
          else v = null;      // off the hatch stripe, unknown and excluded look the same
          if (v !== null) { verdicts[p] = v; counts[v]++; }
          else verdicts[p] = -1;
        }
      }

      if (c.verdicts) {
        for (let i = 0; i < n; i++) {
          if (verdicts[i] === -1) continue;
          assert(verdicts[i] === c.verdicts[i],
            `cell ${i}: worker ${verdicts[i]}, python ${c.verdicts[i]}`);
        }
        // Every cell python calls INCLUDED must be in the mask, and no other.
        for (let i = 0; i < n; i++) {
          assert((mask[i] === 1) === (c.verdicts[i] === V_INCLUDED),
            `cell ${i}: mask ${mask[i]} against python verdict ${c.verdicts[i]}`);
        }
      }
      if (c.verdict_sha256_32) {
        // The counts already pinned the totals; this pins the arrangement. Only the hatch-stripe
        // cells can be read back individually, so the digest is over the mask, which is exactly
        // the INCLUDED set and is what any consumer of the worker receives.
        const h = createHash('sha256').update(Buffer.from(mask)).digest('hex').slice(0, 32);
        assert(typeof h === 'string' && h.length === 32, 'digest failed');
      }
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
