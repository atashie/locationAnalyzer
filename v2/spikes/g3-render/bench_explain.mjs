// bench_explain.mjs — what does one explainAt cost on the real published bundle?
//
// The card asks the worker about one cell on every pointer move, and a pointer can move far
// faster than a round trip. Card plan step 5: measure it rather than assume it either way.
//
// **This is a LOWER BOUND and nothing else.** Node's shim calls the worker's handler
// synchronously, so what follows measures the handler and the object it builds. A real
// `Worker.postMessage` adds a structured clone of the reply and two event-loop hops, and a phone
// adds a slower core. The page reports the real figure in its "Card round trip" row; this is the
// floor that figure cannot go below, measured on the shipped planes rather than on a fixture.
//
// Run:  node spikes/g3-render/bench_explain.mjs

import { createRequire } from 'module';
import { fileURLToPath } from 'url';
import fs from 'fs';
import path from 'path';

const require = createRequire(import.meta.url);
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const BUNDLE = path.join(__dirname, 'fixtures', 'published');

const SAMPLES = 20000;
const WARMUP = 2000;

function loadWorker() {
  const outbox = [];
  const selfShim = { postMessage: (m) => outbox.push(m), onmessage: null };
  const prevSelf = globalThis.self;
  globalThis.self = selfShim;
  if (!globalThis.performance) globalThis.performance = { now: () => Date.now(), timeOrigin: 0 };
  delete require.cache[require.resolve(path.join(__dirname, 'worker.js'))];
  require(path.join(__dirname, 'worker.js'));
  const handler = selfShim.onmessage;
  globalThis.self = prevSelf;
  return {
    send(msg) {
      outbox.length = 0;
      const prev = globalThis.self;
      globalThis.self = selfShim;
      try { handler({ data: msg }); } finally { globalThis.self = prev; }
      const err = outbox.find((m) => m && m.type === 'error');
      if (err) throw new Error(`worker reported: ${err.message}`);
      return outbox.slice();
    },
  };
}

function planeBytes(file) {
  const buf = fs.readFileSync(path.join(BUNDLE, file));
  const out = new ArrayBuffer(buf.length);
  new Uint8Array(out).set(buf);
  return out;
}

const manifest = JSON.parse(fs.readFileSync(path.join(BUNDLE, 'manifest.json'), 'utf8'));
const worker = loadWorker();
worker.send({
  type: 'init',
  manifest,
  values: manifest.layers.map((l) => planeBytes(l.value_file)),
  statuses: manifest.layers.map((l) => planeBytes(l.status_file)),
  routeFlags: manifest.layers.map((l) => (l.flag_file ? planeBytes(l.flag_file) : null)),
  destinations: manifest.layers.map((l) => (l.dest_file ? planeBytes(l.dest_file) : null)),
  destTables: manifest.layers.map((l) => (l.dest_table
    ? JSON.parse(fs.readFileSync(path.join(BUNDLE, l.dest_table), 'utf8')) : null)),
});

const thresholds = manifest.layers.map(() => 15);
const enabled = manifest.layers.map(() => true);
const t0 = process.hrtime.bigint();
worker.send({ type: 'compute', seq: 1, thresholds, enabled });
const computeNs = Number(process.hrtime.bigint() - t0);

// A deterministic walk over the grid, so the figure is reproducible and is not dominated by one
// corner of the raster: a prime stride visits every residue class.
const { nrows, ncols } = manifest;
const n = nrows * ncols;
const STRIDE = 7919;
let named = 0;
let withCriteria = 0;

for (let i = 0; i < WARMUP; i++) {
  const p = (i * STRIDE) % n;
  worker.send({ type: 'explainAt', reqId: 1, row: Math.floor(p / ncols), col: p % ncols });
}

const times = new Float64Array(SAMPLES);
for (let i = 0; i < SAMPLES; i++) {
  const p = ((i + WARMUP) * STRIDE) % n;
  const row = Math.floor(p / ncols);
  const col = p % ncols;
  const s = process.hrtime.bigint();
  const out = worker.send({ type: 'explainAt', reqId: 1, row, col });
  times[i] = Number(process.hrtime.bigint() - s) / 1e6;
  const e = out.find((m) => m.type === 'explainAt');
  if (e.criteria) {
    withCriteria++;
    if (e.criteria.some((c) => c.namesDestination)) named++;
  }
}

const sorted = Array.from(times).sort((a, b) => a - b);
const q = (f) => sorted[Math.min(sorted.length - 1, Math.floor(f * sorted.length))];
const total = sorted.reduce((a, b) => a + b, 0);

console.log(`bundle          ${nrows}x${ncols} = ${n} cells, ${manifest.layers.length} layer(s), `
  + `encoding ${manifest.encoding}`);
console.log(`one full compute ${(computeNs / 1e6).toFixed(1)} ms (all cells, T=15)`);
console.log(`explainAt, ${SAMPLES} cells after ${WARMUP} warmup, handler only:`);
console.log(`  median        ${q(0.5).toFixed(4)} ms`);
console.log(`  p90           ${q(0.9).toFixed(4)} ms`);
console.log(`  p99           ${q(0.99).toFixed(4)} ms`);
console.log(`  worst         ${sorted[sorted.length - 1].toFixed(4)} ms`);
console.log(`  mean          ${(total / sorted.length).toFixed(4)} ms`);
console.log(`  answered with criteria ${withCriteria}, of which named a destination ${named}`);
console.log(`\nFor scale: at 60 pointer events a second the median handler cost is `
  + `${(q(0.5) * 60).toFixed(2)} ms of every 1000 ms.`);
console.log(`
WHAT THIS ESTABLISHES, narrowed after Codex pass 51 finding B8.

  It establishes that recomputing one cell is inexpensive FOR THIS BUNDLE ON THIS RUNTIME: one
  layer, one warmed desktop core, no concurrent compute. On that evidence this measurement does
  not justify caching a per-layer outcome plane. It does not establish that the handler could
  never be the cost: its work grows with the number of enabled layers and with the size of the
  destination payload, neither of which is varied here, and a measured desktop duration is not a
  floor for another device or runtime.

  It does NOT establish an end-to-end pointer-move budget, and the comparison against a
  whole-raster compute above is the wrong denominator for one: the quantities that decide whether
  one request per pointer move is affordable are the event rate, the frame budget, the latency a
  person notices, and interference from a compute running at the same time. None of those is
  measured here.

  Two reasons the figure is optimistic: Node's shim calls the handler synchronously, so the
  structured clone of the reply and two event-loop hops are missing, and this is a desktop core
  rather than a phone. The page's own round-trip row also stops before the card is rendered, so it
  excludes the DOM update and the paint.

  One reason it is pessimistic: the stride is a prime (${STRIDE}), so each step jumps about
  ${Math.floor(STRIDE / ncols)} rows and ${STRIDE % ncols} columns and loses the locality a
  pointer moving between neighbouring cells would have. The memory-access component is therefore
  worse here than in use. The net direction is not settled by either argument.`);
