// card_selftest.mjs — does the card say the right thing, including what it declines to say?
//
// The worker's conformance suite checks the `explainAt` MESSAGE. This checks the WORDS, which is
// a different failure surface and the one a household actually meets. Three ways a disclosure
// gets lost between a correct message and a sentence, and all three have a check here:
//
//   * printing "no restrictions" where the layer does not disclose, turning "we are not telling
//     you" into "there are none";
//   * printing a bare "20 min" where the 20 is a LOWER BOUND, turning "at least 20 minutes, and
//     we never computed a route" into a measurement;
//   * printing a shop where the pipeline chose a NODE carrying several, presenting our pick as
//     ours when we never made one.
//
// The last section feeds it real `explainAt` replies from the shipped bundle rather than
// hand-built ones, because a renderer correct on its author's fixtures and wrong on the artifact
// is this project's most repeated defect.
//
// Run:  node spikes/g3-render/card_selftest.mjs

import { createRequire } from 'module';
import { fileURLToPath } from 'url';
import fs from 'fs';
import path from 'path';

const require = createRequire(import.meta.url);
const __dirname = path.dirname(fileURLToPath(import.meta.url));
require(path.join(__dirname, 'card.js'));
const C = globalThis.G3Card;

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

const crit = (over) => ({
  layer: 'own_triangle_grocery_walk',
  outcome: 0,
  outcomeName: 'PASS',
  status: 0,
  statusName: 'OK',
  value: 12,
  valueIsLowerBound: false,
  thresholdMin: 15,
  horizonS: 7200,
  routeFlag: 0,
  namesDestination: null,
  ...over,
});
const reply = (criteria, over) => ({
  type: 'explainAt', reqId: 1, seq: 1, row: 10, col: 20,
  verdict: 0, verdictName: 'INCLUDED', criteria, ...over,
});

// ------------------------------------------------------------------ the control: it says something

check('a passing criterion states its time and the limit it was compared against', () => {
  const html = C.renderCardHTML(reply([crit({})]));
  assert(html.includes('12 min'), html);
  assert(html.includes('your limit 15 min'), html);
  assert(html.includes('PASS'), html);
  assert(html.includes('Every criterion you have on is satisfied here.'), html);
});

// ------------------------------------------------------------------ a bound is not a time

check('a lower bound is never printed as a measured time', () => {
  const html = C.renderCardHTML(reply([crit({
    outcome: 1, outcomeName: 'FAIL', status: 1, statusName: 'OFF_NETWORK',
    value: 20, valueIsLowerBound: true,
  })], { verdict: 1, verdictName: 'EXCLUDED' }));
  assert(html.includes('at least 20 min'), `a bound must say so: ${html}`);
  assert(!/(^|[^a-z])20 min/.test(html.replace('at least 20 min', '')),
    `a bare "20 min" survives somewhere: ${html}`);
  assert(html.includes('Ruled out without computing a route'),
    `a known failure from a bound must say no route was computed: ${html}`);
});

check('a status carrying neither a time nor a bound prints no number at all', () => {
  for (const statusName of ['LAYER_UNKNOWN', 'OUTSIDE', 'UNKNOWN_CAUSE']) {
    const html = C.renderCardHTML(reply([crit({
      outcome: 2, outcomeName: 'UNKNOWN', status: 4, statusName, value: null,
      valueIsLowerBound: false,
    })], { verdict: 2, verdictName: 'UNKNOWN' }));
    assert(html.includes('no time published'), `${statusName}: ${html}`);
    assert(!html.includes('255'), `${statusName}: VALUE_NONE reached the card: ${html}`);
    assert(C.minutesText({ value: null }) === null);
  }
});

// ------------------------------------------------------------------ "we cannot tell you", with a cause

check('every unknown cause has words, and they are not the code', () => {
  const codes = { OFF_NETWORK: 1, BEYOND_HORIZON: 2, LAYER_UNKNOWN: 4, OUTSIDE: 5,
    UNKNOWN_CAUSE: 6 };
  for (const [statusName, status] of Object.entries(codes)) {
    const html = C.renderCardHTML(reply([crit({
      outcome: 2, outcomeName: 'UNKNOWN', status, statusName, value: null,
    })], { verdict: 2, verdictName: 'UNKNOWN' }));
    assert(html.includes('We cannot tell you:'), `${statusName}: ${html}`);
    assert(C.WHY_UNKNOWN[statusName], `${statusName} has no words`);
    assert(html.includes(C.WHY_UNKNOWN[statusName]), `${statusName}: ${html}`);
    // The bare code must not be what a household reads.
    assert(!html.includes(`We cannot tell you: ${statusName}`),
      `${statusName} was printed as its own explanation: ${html}`);
  }
});

check('every status code the format defines has card words', () => {
  // From the shipped manifest, so a code added to the wire format without words here fails.
  const manifest = JSON.parse(fs.readFileSync(
    path.join(__dirname, 'fixtures', 'published', 'manifest.json'), 'utf8'));
  for (const name of Object.values(manifest.status_codes)) {
    if (name === 'OK') continue;
    assert(C.WHY_UNKNOWN[name], `the format defines ${name} and the card has no words for it`);
  }
});

// ------------------------------------------------------------------ the restricted-route disclosure

check('a flagged route is disclosed in words', () => {
  const html = C.renderCardHTML(reply([crit({ routeFlag: 1 })]));
  assert(html.includes('not clearly public'), html);
  assert(html.includes('may be longer'), html);
});

check('a layer that does not disclose says so, and never says there are no restrictions', () => {
  for (const flag of [null, undefined]) {
    const html = C.renderCardHTML(reply([crit({ routeFlag: flag })]));
    assert(html.includes('does not say whether the route uses a restricted way'), html);
    assert(!/no restrict/i.test(html),
      `"not telling you" was rendered as "no restrictions": ${html}`);
  }
});

check('a clear route says nothing about restrictions either way', () => {
  // routeFlag 0 is a real answer -- this route is clear -- but the card has no reason to shout
  // it, and it must NOT be confused with the silent case above.
  const html = C.renderCardHTML(reply([crit({ routeFlag: 0 })]));
  assert(!html.includes('does not say whether the route'),
    `a disclosed clear route was rendered as a non-disclosure: ${html}`);
  assert(!html.includes('not clearly public'), html);
});

// ------------------------------------------------------------------ the destination

check('a single-place node is named', () => {
  const html = C.renderCardHTML(reply([crit({
    namesDestination: { ordinal: 3, nodeIndex: 1003, placeCount: 1,
      places: [{ gers_id: 'a', name: 'Harris Teeter' }] },
  })]));
  assert(html.includes('measured to Harris Teeter'), html);
});

check('a node carrying several places names them all and picks none', () => {
  const html = C.renderCardHTML(reply([crit({
    namesDestination: { ordinal: 3, nodeIndex: 1003, placeCount: 3,
      places: [{ name: 'Weaver Street' }, { name: 'Harris Teeter' }, { name: 'Compare Foods' }] },
  })]));
  assert(html.includes('one of 3 places at this junction'), html);
  for (const n of ['Weaver Street', 'Harris Teeter', 'Compare Foods']) {
    assert(html.includes(n), `${n} is missing: ${html}`);
  }
  assert(!html.includes('measured to Weaver Street'),
    `the card presented its own pick as ours: ${html}`);
});

check('a layer that names no destination says so rather than implying there is none', () => {
  const html = C.renderCardHTML(reply([crit({ namesDestination: null })]));
  assert(html.includes('does not say which destination'), html);
});

check('a named node with no names falls back to the junction rather than inventing one', () => {
  const html = C.renderCardHTML(reply([crit({
    namesDestination: { ordinal: 1, nodeIndex: 7, placeCount: 1, places: [] },
  })]));
  assert(html.includes('whose places this bundle does not name'), html);
});

// ------------------------------------------------------------------ the lifecycle and the edges

check('the cell states before a compute and outside the area are distinct sentences', () => {
  assert(C.renderCardHTML({ outside: true }).includes('Outside the published area'));
  assert(C.renderCardHTML({ notComputed: true }).includes('Nothing has been computed yet'));
  const none = C.renderCardHTML(reply(null));
  assert(none.includes('No criteria are switched on'), none);
  assert(!none.includes('satisfied here'),
    `no criteria was rendered as everything qualifying: ${none}`);
});

check('a place name is escaped, not trusted', () => {
  const html = C.renderCardHTML(reply([crit({
    namesDestination: { ordinal: 0, nodeIndex: 1, placeCount: 1,
      places: [{ name: '<img src=x onerror=alert(1)>' }] },
  })]));
  assert(!html.includes('<img'), `an upstream name reached the DOM as markup: ${html}`);
  assert(html.includes('&lt;img'), html);
});

// ------------------------------------------------------------------ the cell lookup

check('the cell lookup is half-open and agrees with the grid at the corners', () => {
  const bounds = [-79.2, 35.7, -78.5, 36.15];
  const [W, S, E, N] = bounds;
  const nrows = 514;
  const ncols = 643;
  const at = (lon, lat) => C.cellForLonLat(bounds, ncols, nrows, lon, lat);
  // North-west corner is cell (0, 0); the south and east edges belong to a cell one past the
  // edge and are therefore outside. Same convention as GridSpec.cell_for_xy.
  const nw = at(W, N);
  assert(nw && nw.row === 0 && nw.col === 0, JSON.stringify(nw));
  assert(at(E, N) === null, 'the east edge is inside');
  assert(at(W, S) === null, 'the south edge is inside');
  const se = at(E - 1e-9, S + 1e-9);
  assert(se && se.row === nrows - 1 && se.col === ncols - 1, JSON.stringify(se));
  assert(at(W - 1e-6, N) === null && at(W, N + 1e-6) === null, 'outside returned a cell');
  // And the middle, against the arithmetic done by hand.
  const mid = at(W + (E - W) / 2, N - (N - S) / 2);
  assert(mid.col === Math.floor(ncols / 2) && mid.row === Math.floor(nrows / 2),
    JSON.stringify(mid));
});

// ------------------------------------------------------------------ against the real bundle

check('the real bundle\'s own explainAt replies all render, and the card never invents', () => {
  // A renderer correct on its author's fixtures and wrong on the artifact is this project's most
  // repeated defect, so the replies here come from the worker reading the shipped planes.
  const BUNDLE = path.join(__dirname, 'fixtures', 'published');
  const outbox = [];
  const selfShim = { postMessage: (m) => outbox.push(m), onmessage: null };
  const prevSelf = globalThis.self;
  globalThis.self = selfShim;
  if (!globalThis.performance) globalThis.performance = { now: () => Date.now(), timeOrigin: 0 };
  delete require.cache[require.resolve(path.join(__dirname, 'worker.js'))];
  require(path.join(__dirname, 'worker.js'));
  const handler = selfShim.onmessage;
  const send = (msg) => {
    outbox.length = 0;
    const prev = globalThis.self;
    globalThis.self = selfShim;
    try { handler({ data: msg }); } finally { globalThis.self = prev; }
    const err = outbox.find((m) => m && m.type === 'error');
    if (err) throw new Error(`worker reported: ${err.message}`);
    return outbox.slice();
  };
  const planeBytes = (file) => {
    const buf = fs.readFileSync(path.join(BUNDLE, file));
    const out = new ArrayBuffer(buf.length);
    new Uint8Array(out).set(buf);
    return out;
  };
  const manifest = JSON.parse(fs.readFileSync(path.join(BUNDLE, 'manifest.json'), 'utf8'));
  send({
    type: 'init',
    manifest,
    values: manifest.layers.map((l) => planeBytes(l.value_file)),
    statuses: manifest.layers.map((l) => planeBytes(l.status_file)),
    routeFlags: manifest.layers.map((l) => (l.flag_file ? planeBytes(l.flag_file) : null)),
    destinations: manifest.layers.map((l) => (l.dest_file ? planeBytes(l.dest_file) : null)),
    destTables: manifest.layers.map((l) => (l.dest_table
      ? JSON.parse(fs.readFileSync(path.join(BUNDLE, l.dest_table), 'utf8')) : null)),
  });
  send({ type: 'compute', seq: 1, thresholds: manifest.layers.map(() => 15),
    enabled: manifest.layers.map(() => true) });
  globalThis.self = prevSelf;

  const { nrows, ncols } = manifest;
  const n = nrows * ncols;
  const STRIDE = 7919;
  const seen = { PASS: 0, FAIL: 0, UNKNOWN: 0 };
  const statuses = new Set();
  let named = 0;
  let several = 0;
  for (let i = 0; i < 40000; i++) {
    const p = (i * STRIDE) % n;
    const out = send({ type: 'explainAt', reqId: 1,
      row: Math.floor(p / ncols), col: p % ncols });
    const msg = out.find((m) => m.type === 'explainAt');
    const html = C.renderCardHTML(msg);
    assert(typeof html === 'string' && html.length > 0, `cell ${p}: empty card`);
    // Nothing the card prints may be a bare format token or an undefined.
    assert(!html.includes('undefined'), `cell ${p}: "undefined" in the card: ${html}`);
    assert(!html.includes('null'), `cell ${p}: "null" in the card: ${html}`);
    assert(!/\b255 min\b/.test(html), `cell ${p}: VALUE_NONE printed as minutes: ${html}`);
    for (const cr of (msg.criteria || [])) {
      seen[cr.outcomeName]++;
      statuses.add(cr.statusName);
      if (cr.namesDestination) {
        named++;
        if (cr.namesDestination.placeCount > 1) several++;
        // The owner's rule, on the real data: where a node carries several places the card may
        // not present one of them as our choice.
        if (cr.namesDestination.placeCount > 1) {
          assert(html.includes('one of'), `cell ${p}: picked one of several: ${html}`);
        }
      }
      // A non-disclosing layer must never produce "no restrictions" anywhere on the real bundle.
      if (cr.routeFlag === null) {
        assert(!/no restrict/i.test(html), `cell ${p}: ${html}`);
      }
    }
  }
  // The exercise must actually have exercised something. A renderer that was handed 40,000
  // identical passing cells has not been tested on this layer.
  assert(seen.PASS > 0 && seen.FAIL > 0 && seen.UNKNOWN > 0,
    `the sample did not reach all three outcomes: ${JSON.stringify(seen)}`);
  assert(statuses.size >= 3, `only ${[...statuses]} occurred`);
  assert(named > 0 && several > 0,
    `the sample reached no shared-node destination: named ${named}, several ${several}`);
  console.log(`      outcomes ${JSON.stringify(seen)}, statuses ${[...statuses].join('/')}, `
    + `${named} named a destination, ${several} of those a shared node`);
});

console.log(failures === 0 ? '\nall card checks passed'
  : `\n${failures} card check(s) FAILED`);
process.exit(failures === 0 ? 0 : 1);
