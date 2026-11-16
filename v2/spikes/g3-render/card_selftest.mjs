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
//     ours when we never made one;
//   * stating a model estimate as a fact about the place -- Codex pass 54, added 2026-11-16.
//     "Every criterion you have on is satisfied here" is a claim about the world. What we hold is
//     seconds from a cell centre over our own graph, rounded UP to the minute, possibly along a
//     route our own flag plane calls restricted. Nothing in the message is wrong and the sentence
//     still overstates it, which no message-level check can see.
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

/** Load worker.js with `self` shimmed and return a `send`. One instance per caller: the worker
 *  keeps its layer state in a module-level object. */
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
  return (msg) => {
    outbox.length = 0;
    const prev = globalThis.self;
    globalThis.self = selfShim;
    try { handler({ data: msg }); } finally { globalThis.self = prev; }
    const err = outbox.find((m) => m && m.type === 'error');
    if (err) throw new Error(`worker reported: ${err.message}`);
    return outbox.slice();
  };
}

/** A standalone ArrayBuffer: Node's Buffer is a view into a shared pool. */
function planeBytes(dir, file) {
  const buf = fs.readFileSync(path.join(dir, file));
  const out = new ArrayBuffer(buf.length);
  new Uint8Array(out).set(buf);
  return out;
}

/** Every conformance group with two or more layers, initialised and ready to query.
 *
 * The published bundle ships ONE layer, so these fixtures are the only multi-criterion data this
 * project has. Hand-built planes, but real `explainAt` replies through the real worker, which is
 * what pass 51 B6 found missing entirely.
 */
function multiLayerGroups() {
  const FIXTURES = path.join(__dirname, 'fixtures', 'conformance');
  const vectors = JSON.parse(fs.readFileSync(path.join(FIXTURES, 'vectors.json'), 'utf8'));
  const out = [];
  for (const group of vectors.groups) {
    if (group.layers.length < 2) continue;
    const send = loadWorker();
    const entry = (l) => ({ id: l.id, horizon_s: l.horizon_s,
      ...(l.flag_file ? { flag_file: l.flag_file } : {}),
      ...(l.dest_file ? { dest_file: l.dest_file, dest_table: l.dest_table,
                          dest_byte_order: l.dest_byte_order, dest_none: l.dest_none } : {}) });
    const tables = JSON.parse(JSON.stringify(group.dest_tables
      || group.layers.map(() => null)));
    send({
      type: 'init',
      manifest: {
        nrows: group.nrows, ncols: group.ncols, encoding: vectors.encoding,
        destination_plane_byte_order: vectors.destination_plane_byte_order,
        layers: group.layers.map(entry),
      },
      values: group.layers.map((l) => planeBytes(FIXTURES, l.value_file)),
      statuses: group.layers.map((l) => planeBytes(FIXTURES, l.status_file)),
      routeFlags: group.layers.map((l) => (l.flag_file
        ? planeBytes(FIXTURES, l.flag_file) : null)),
      destinations: group.layers.map((l) => (l.dest_file
        ? planeBytes(FIXTURES, l.dest_file) : null)),
      destTables: JSON.parse(JSON.stringify(tables)),
    });
    out.push({ group, send, tables });
  }
  return out;
}

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
  assert(html.includes(C.VERDICT_TEXT.INCLUDED), html);
});

// ------------------------------------------------------------------ a bound is not a time

check('a lower bound is never printed as a measured time', () => {
  const html = C.renderCardHTML(reply([crit({
    outcome: 1, outcomeName: 'FAIL', status: 1, statusName: 'OFF_NETWORK',
    value: 20, valueIsLowerBound: true,
  })], { verdict: 1, verdictName: 'EXCLUDED' }));
  assert(html.includes('more than 19 min'), `a bound must say so: ${html}`);
  assert(!/(^|[^a-z0-9])20 min/.test(html),
    `a bare "20 min" survives somewhere: ${html}`);
  assert(html.includes('Ruled out without computing a route'),
    `a known failure from a bound must say no route was computed: ${html}`);
});

check('a rounded-up bound is not reported as "at least" that many minutes', () => {
  // **Pass 51 finding B3, with its witness.** The value byte is `ceil(bound_seconds / 60)`, so a
  // byte of 11 means the bound lies in (600, 660] seconds. A qualifying journey of 630 seconds is
  // compatible with that evidence and takes LESS than 11 minutes, so "at least 11 min" claims
  // more than the data supports. What the byte establishes is `bound > 600 s`.
  const html = C.renderCardHTML(reply([crit({
    outcome: 2, outcomeName: 'UNKNOWN', status: 2, statusName: 'BEYOND_HORIZON',
    value: 11, valueIsLowerBound: true, thresholdMin: 10, horizonS: 601,
  })], { verdict: 2, verdictName: 'UNKNOWN' }));
  // The criterion block, not the whole card: the UNKNOWN headline legitimately contains the words
  // "At least one criterion does not know", which is about criteria and not about minutes.
  const block = html.split('class="crit"')[1];
  assert(block.includes('more than 10 min'), block);
  assert(!/at least/i.test(block), `"at least" overstates a rounded-up bound: ${block}`);
  assert(!/(^|[^a-z0-9])11 min/.test(block),
    `the ceiling itself was printed as the bound: ${block}`);
  // A 630-second journey must not be excluded by what the card says.
  assert(C.minutesText({ value: 11, valueIsLowerBound: true }) === 'more than 10 min');
});

check('a zero bound is reported as carrying no bound, not as "more than -1 min"', () => {
  // The audit harness's reconstruction writes a bound of 0 for an OFF_NETWORK cell, and
  // `outcomeFor` can never turn that into a failure, so the card must not do arithmetic on it.
  assert(C.minutesText({ value: 0, valueIsLowerBound: true }) === 'no lower bound published');
  const html = C.renderCardHTML(reply([crit({
    outcome: 2, outcomeName: 'UNKNOWN', status: 1, statusName: 'OFF_NETWORK',
    value: 0, valueIsLowerBound: true,
  })], { verdict: 2, verdictName: 'UNKNOWN' }));
  assert(!html.includes('-1'), html);
  assert(html.includes('no lower bound published'), html);
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

// ------------------------------------------------------------------ a model result is not a fact

check('the words are the ones pass 54 asked for, pinned here because nothing else pins them', () => {
  // **Pinned as literals on purpose.** Every other check compares the rendering against
  // `C.VERDICT_TEXT`, so all of them would still pass if the sentence itself were replaced. This
  // is the one place a wording change has to be deliberate, and the reason each is what it is:
  //
  //  * the affirmative headline is a statement about the MODEL, not about the place. Pass 54:
  //    "it reduces the chance that the product asserts a demonstrated real-world fact where it
  //    possesses a model result";
  //  * the note says "rounded UP", because `encode_minutes` is `ceil` and a displayed 12 min
  //    holds a model time in (11, 12]. "Rounded" alone reads as "to the nearest" and would
  //    understate the overstatement;
  //  * it says the centre of the cell, because `build_layer_surface` evaluates
  //    `grid.cell_centers_xy()` and not a door.
  assert(C.VERDICT_TEXT.INCLUDED === 'The model estimates this cell meets your limits.',
    C.VERDICT_TEXT.INCLUDED);
  assert(C.VERDICT_TEXT.EXCLUDED === 'Our model rules this cell out for at least one of your '
    + 'limits.', C.VERDICT_TEXT.EXCLUDED);
  assert(C.ESTIMATE_NOTE === 'Times are model estimates for a nearby grid point, not your '
    + 'address, and are rounded up to the whole minute.', C.ESTIMATE_NOTE);
  assert(/rounded up/.test(C.ESTIMATE_NOTE), C.ESTIMATE_NOTE);
  assert(!/nearest/.test(C.ESTIMATE_NOTE), `the encoding is ceil, not round: ${C.ESTIMATE_NOTE}`);
  assert(/not your address/.test(C.ESTIMATE_NOTE), C.ESTIMATE_NOTE);
  // **The retired false claim, pinned as retired** -- pass 55 F1. The note said "measured from
  // the centre of this cell" for one day. The card's cell is a PUBLISHED cell; the time was
  // measured at a UTM cell centre a median 39.9 m away, up to 70.6 m. If that phrasing ever
  // comes back it is a false statement about where a journey starts, so it is checked for by
  // name rather than left to a reviewer to notice again.
  assert(!/centre of this cell/.test(C.ESTIMATE_NOTE),
    `the note names the displayed cell's centre, which is not where the time was measured: `
    + C.ESTIMATE_NOTE);
  // And the two sentences these replaced reach no card at all, under any verdict.
  for (const name of Object.keys(C.VERDICT_TEXT)) {
    const html = C.renderCardHTML(reply([crit({})], { verdictName: name }));
    assert(!html.includes('Every criterion you have on is satisfied here'),
      `${name} still asserts satisfaction as a fact about the place: ${html}`);
    assert(!html.includes('At least one criterion is not satisfied here'),
      `${name} still asserts an exclusion as a fact about the place: ${html}`);
    assert(!html.includes('centre of this cell'), `${name}: ${html}`);
  }
});

check('the estimate note is on every card that shows a time, and on no card that does not', () => {
  // A hedge on the affirmative verdict alone would present an exclusion as the more certain
  // answer, so all three verdicts carry it.
  for (const name of Object.keys(C.VERDICT_TEXT)) {
    const html = C.renderCardHTML(reply([crit({})], { verdictName: name }));
    assert(html.includes(C.ESTIMATE_NOTE), `${name} card does not qualify its times: ${html}`);
    // Under the verdict, above the criteria: a qualification the reader meets after the number
    // it qualifies is one they have already acted on.
    assert(html.indexOf(C.ESTIMATE_NOTE) > html.indexOf(C.VERDICT_TEXT[name]), html);
    assert(html.indexOf(C.ESTIMATE_NOTE) < html.indexOf('class="crit"'), html);
  }
  // And nowhere there is no time to qualify, where it would be noise claiming to be a disclosure.
  assert(!C.renderCardHTML({ outside: true }).includes('Times are estimates'));
  assert(!C.renderCardHTML({ notComputed: true }).includes('Times are estimates'));
  assert(!C.renderCardHTML(reply(null)).includes('Times are estimates'));
});

check('the restricted-route warning is the line directly under the time it qualifies', () => {
  // Its own last sentence says "longer than the time above", so anything between it and the time
  // makes that word false. It used to sit below the status explanation, which is exactly that
  // case: pass 54 asked for the qualification "beside the relevant time".
  const html = C.renderCardHTML(reply([crit({
    outcome: 2, outcomeName: 'UNKNOWN', status: 1, statusName: 'OFF_NETWORK',
    value: null, valueIsLowerBound: false, routeFlag: 1,
  })], { verdict: 2, verdictName: 'UNKNOWN' }));
  const divs = html.split('class="crit"')[1].split('<div').filter((d) => d.includes('</div>'));
  const timeAt = divs.findIndex((d) => d.includes('your limit'));
  const flagAt = divs.findIndex((d) => d.includes('not clearly public'));
  const whyAt = divs.findIndex((d) => d.includes('We cannot tell you'));
  assert(timeAt >= 0 && flagAt >= 0 && whyAt >= 0, html);
  assert(flagAt === timeAt + 1,
    `the warning is ${flagAt - timeAt} lines below the time it qualifies: ${html}`);
  assert(whyAt > flagAt, html);
});

check('a place name is escaped, not trusted', () => {
  const html = C.renderCardHTML(reply([crit({
    namesDestination: { ordinal: 0, nodeIndex: 1, placeCount: 1,
      places: [{ name: '<img src=x onerror=alert(1)>' }] },
  })]));
  assert(!html.includes('<img'), `an upstream name reached the DOM as markup: ${html}`);
  assert(html.includes('&lt;img'), html);
});

// ------------------------------------------------------------------ more than one criterion
//
// **Pass 51 finding B6: before this section there was no multi-criterion rendering test at all**,
// not even a hand-built one, so changing the renderer's loop to `msg.criteria.slice(0, 1)` passed
// all sixteen checks. A card that silently discards every criterion after the first was accepted.

check('every criterion is rendered, not just the first', () => {
  const html = C.renderCardHTML(reply([
    crit({ layer: 'walk-grocery', value: 2, thresholdMin: 10 }),
    crit({ layer: 'bike-school', value: 7, thresholdMin: 10 }),
    crit({ layer: 'drive-work', outcome: 1, outcomeName: 'FAIL', value: 30, thresholdMin: 10 }),
  ], { verdict: 1, verdictName: 'EXCLUDED' }));
  for (const layer of ['walk-grocery', 'bike-school', 'drive-work']) {
    assert(html.includes(layer), `${layer} is missing from the card: ${html}`);
  }
  // Each criterion's own number must appear beside its own name, so a renderer that prints three
  // headings and one body is caught too.
  const blocks = html.split('class="crit"').slice(1);
  assert(blocks.length === 3, `${blocks.length} criterion blocks, expected 3`);
  assert(blocks[0].includes('2 min') && blocks[1].includes('7 min')
    && blocks[2].includes('30 min'), html);
});

check('each criterion keeps its own disclosure, outcome and destination', () => {
  // Mixed everything: one discloses a clear route and names a shop, one does not disclose at all
  // and names nothing, one is unknown for a reason. A card that associated any of these with the
  // wrong criterion would still contain all the right words.
  const html = C.renderCardHTML(reply([
    crit({ layer: 'walk-grocery', routeFlag: 1, value: 4, thresholdMin: 10,
      namesDestination: { ordinal: 1, nodeIndex: 9, placeCount: 1,
        places: [{ name: 'Weaver Street Market' }] } }),
    crit({ layer: 'bike-school', routeFlag: null, value: 9, thresholdMin: 10,
      namesDestination: null }),
    crit({ layer: 'drive-work', outcome: 2, outcomeName: 'UNKNOWN', status: 2,
      statusName: 'BEYOND_HORIZON', value: null, thresholdMin: 10, routeFlag: 0,
      namesDestination: null }),
  ], { verdict: 2, verdictName: 'UNKNOWN' }));
  const blocks = html.split('class="crit"').slice(1);
  assert(blocks.length === 3, `${blocks.length} blocks`);

  // walk-grocery: flagged route, named shop, no non-disclosure sentence.
  assert(blocks[0].includes('not clearly public'), blocks[0]);
  assert(blocks[0].includes('Weaver Street Market'), blocks[0]);
  assert(!blocks[0].includes('does not say whether the route'), blocks[0]);
  // bike-school: does not disclose, and says so; names nothing, and says so.
  assert(blocks[1].includes('does not say whether the route uses a restricted way'), blocks[1]);
  assert(blocks[1].includes('does not say which destination'), blocks[1]);
  assert(!blocks[1].includes('Weaver Street Market'),
    `another criterion's shop leaked into this one: ${blocks[1]}`);
  // drive-work: unknown with its cause, a disclosed clear route, no number.
  assert(blocks[2].includes('We cannot tell you:'), blocks[2]);
  assert(blocks[2].includes(C.WHY_UNKNOWN.BEYOND_HORIZON), blocks[2]);
  assert(!blocks[2].includes('does not say whether the route'),
    `a disclosed clear route was rendered as a non-disclosure: ${blocks[2]}`);
  assert(blocks[2].includes('no time published'), blocks[2]);
});

check('real worker replies from the multi-layer fixtures render correctly', () => {
  // Hand-built replies are my own idea of what the worker sends. These come from the worker
  // itself, on the conformance groups that have two layers -- the only multi-criterion data this
  // project has, since the published bundle ships one layer.
  const groups = multiLayerGroups();
  assert(groups.length >= 2, `only ${groups.length} multi-layer groups available`);
  let rendered = 0;
  let mixedDisclosure = 0;
  let mixedOutcome = 0;
  let namedBesideSilent = 0;
  for (const { group, send, tables } of groups) {
    for (const c of group.cases) {
      if (c.withhold_flags) continue;
      const enabledIds = group.layers.filter((_l, k) => c.enabled[k]).map((l) => l.id);
      if (enabledIds.length < 2) continue;
      send({ type: 'compute', seq: 1, thresholds: c.thresholds, enabled: c.enabled });
      for (let p = 0; p < group.nrows * group.ncols; p++) {
        const out = send({ type: 'explainAt', reqId: 1,
          row: Math.floor(p / group.ncols), col: p % group.ncols });
        const msg = out.find((m) => m.type === 'explainAt');
        const html = C.renderCardHTML(msg);
        rendered++;
        const blocks = html.split('class="crit"').slice(1);
        assert(blocks.length === msg.criteria.length,
          `${group.name} cell ${p}: ${blocks.length} blocks for `
          + `${msg.criteria.length} criteria`);
        assert(!html.includes('undefined') && !html.includes('null'), html);
        // **The combined headline** -- pass 53 F7. No assertion mentioned it, so replacing
        // `VERDICT_TEXT[msg.verdictName]` with `VERDICT_TEXT.INCLUDED` passed all 29 checks and
        // every excluded cell read "Every criterion you have on is satisfied here."
        const head = html.split('class="crit"')[0];
        assert(head.includes(C.VERDICT_TEXT[msg.verdictName]),
          `${group.name} cell ${p}: headline is not ${msg.verdictName}: ${head}`);
        for (const [name, text] of Object.entries(C.VERDICT_TEXT)) {
          if (name !== msg.verdictName) {
            assert(!head.includes(text),
              `${group.name} cell ${p}: headline also claims ${name}: ${head}`);
          }
        }
        const flags = msg.criteria.map((cr) => cr.routeFlag);
        const outcomes = msg.criteria.map((cr) => cr.outcomeName);
        if (flags.includes(null) && flags.some((f) => f !== null)) mixedDisclosure++;
        if (new Set(outcomes).size > 1) mixedOutcome++;
        const named = msg.criteria.filter((cr) => cr.namesDestination).length;
        if (named && named < msg.criteria.length) namedBesideSilent++;
        for (let i = 0; i < msg.criteria.length; i++) {
          const cr = msg.criteria[i];
          assert(blocks[i].includes(cr.layer),
            `${group.name} cell ${p}: block ${i} is not about ${cr.layer}`);
          // **Every sentence in the block, against the reply it is rendering.** Pass 52 finding
          // F6: this used to check the disclosure's presence and the FIRST destination name, so
          // three mutations passed all 27 checks -- the outcome text replaced by a literal
          // `PASS`, every threshold replaced by `15`, and every place after the first dropped.
          // A card that shows the right words in the wrong places looked complete.
          assert(blocks[i].includes(`>${cr.outcomeName}<`),
            `${group.name} cell ${p} block ${i}: outcome ${cr.outcomeName} is not what the block `
            + `displays: ${blocks[i]}`);
          assert(blocks[i].includes(`your limit ${cr.thresholdMin} min`),
            `${group.name} cell ${p} block ${i}: limit ${cr.thresholdMin} is not displayed: `
            + blocks[i]);
          const mins = C.minutesText(cr);
          assert(mins === null ? blocks[i].includes('no time published')
            : blocks[i].includes(mins),
            `${group.name} cell ${p} block ${i}: expected ${mins}: ${blocks[i]}`);
          if (cr.outcomeName === 'UNKNOWN') {
            assert(blocks[i].includes(C.WHY_UNKNOWN[cr.statusName]),
              `${group.name} cell ${p} block ${i}: no cause for ${cr.statusName}`);
          }
          // Each block carries its OWN disclosure, so a card that attributes one criterion's
          // flag or shop to another is caught rather than looking complete.
          if (cr.routeFlag === null) {
            assert(blocks[i].includes('does not say whether the route'), blocks[i]);
          } else {
            assert(!blocks[i].includes('does not say whether the route'), blocks[i]);
            if (cr.routeFlag === 1) {
              assert(blocks[i].includes('not clearly public'), blocks[i]);
            } else {
              assert(!blocks[i].includes('not clearly public'), blocks[i]);
            }
          }
          if (cr.namesDestination) {
            // EVERY member of the set, not the first. The set IS the answer where a node carries
            // more than one place, and dropping the rest preserved every other assertion.
            for (const place of cr.namesDestination.places) {
              assert(!place.name || blocks[i].includes(place.name),
                `${group.name} cell ${p} block ${i}: place ${place.name} is missing: `
                + blocks[i]);
            }
            if (cr.namesDestination.placeCount > 1) {
              assert(blocks[i].includes(`one of ${cr.namesDestination.placeCount}`), blocks[i]);
            }
          } else {
            assert(blocks[i].includes('does not say which destination')
              || cr.outcomeName !== 'PASS', blocks[i]);
          }
          // **And nothing that belongs to another criterion** -- pass 53 F7. Checking that
          // expected content is PRESENT is half a check: a mutation that copied other criteria's
          // destination text into unnamed blocks satisfied every assertion and passed all 29,
          // because everything expected was there with more beside it.
          for (let j = 0; j < msg.criteria.length; j++) {
            if (j === i) continue;
            const other = msg.criteria[j];
            assert(!blocks[i].includes(other.layer),
              `${group.name} cell ${p} block ${i} names ${other.layer}`);
            for (const place of (other.namesDestination ? other.namesDestination.places : [])) {
              const mine = (cr.namesDestination ? cr.namesDestination.places : [])
                .some((q) => q.name === place.name);
              assert(mine || !place.name || !blocks[i].includes(place.name),
                `${group.name} cell ${p} block ${i} carries ${other.layer}'s `
                + `destination ${place.name}`);
            }
          }
        }
      }
    }
  }
  assert(rendered > 0, 'no multi-criterion cell was rendered');
  // The sample must reach the combinations that make the check discriminating, rather than the
  // same two passing layers over and over.
  assert(mixedDisclosure > 0, 'no cell mixed a disclosing layer with a silent one');
  assert(mixedOutcome > 0, 'no cell mixed outcomes between criteria');
  assert(namedBesideSilent > 0, 'no cell named one criterion\'s destination beside a silent one');
  console.log(`      ${rendered} multi-criterion cells; ${mixedDisclosure} mixed disclosure, `
    + `${mixedOutcome} mixed outcomes, ${namedBesideSilent} named beside silent`);
});

// ------------------------------------------------------------------ which replies reach the screen
//
// Pass 51's two presentation findings, B1 and B5. Both were in logic that lived inside app.js and
// could not be tested without a browser, which is why it is a state machine now.

check('a reply from the previous compute is not rendered beside the new raster', () => {
  // **Pass 51 B1, its witness exactly.** One OK cell holds 12 minutes. Compute at a 15-minute
  // limit, hover it, change the limit to 5, compute again and let it paint. Before the fix the
  // card still read PASS with "your limit 15 min" over a raster that excluded the cell, for as
  // long as the pointer stayed put: nothing invalidated it and the reply check looked only at
  // `reqId`.
  const ins = C.createInspector();
  const first = ins.computePainted(1, 1);
  assert(first === null, 'nothing is inspected yet, so nothing to refresh');

  const req = ins.pointerAt(10, 20);
  assert(req && req.row === 10, 'the first hover must send a request');
  assert(ins.reply({ reqId: req.reqId, seq: 1, row: 10, col: 20 }).render,
    'a current reply must render');

  // The limit changes: a compute is requested, and its raster has not painted.
  ins.computeStarted();
  assert(ins.state.displayedSeq === null, 'the screen shows no settled compute while one runs');
  // A reply built from compute 1 arrives late. It describes the previous criteria.
  const stale = ins.pointerAt(10, 20);
  assert(!ins.reply({ reqId: stale.reqId, seq: 1, row: 10, col: 20 }).render,
    'a reply from compute 1 must not render once compute 2 has been requested');

  // Compute 2 paints, and the inspected cell is re-asked without the pointer moving.
  const refresh = ins.computePainted(2, 2);
  assert(refresh && refresh.row === 10 && refresh.col === 20,
    'the inspected cell must be re-asked when the new raster paints');
  assert(ins.reply({ reqId: refresh.reqId, seq: 2, row: 10, col: 20 }).render,
    'the fresh reply must render');
});

check('an older compute that paints after a newer one does not claim the screen', () => {
  const ins = C.createInspector();
  ins.pointerAt(1, 1);
  ins.reply({ reqId: 1, seq: 1, row: 1, col: 1 });
  ins.computeStarted();
  // Result 2 is requested, then result 1 arrives late from the paint chain.
  assert(ins.computePainted(1, 2) === null, 'compute 1 painted after 2 was requested');
  assert(ins.state.displayedSeq === null, 'it must not mark itself displayed');
  assert(ins.computePainted(2, 2) !== null, 'compute 2 is the one on screen');
  assert(ins.state.displayedSeq === 2);
});

check('a late reply does not restore an inside card after the pointer leaves', () => {
  // **Pass 51 B5, its witness exactly.** Move inside, creating pending request 1; move outside
  // the raster; deliver reply 1. With one request in flight the pending request is still the
  // newest one SENT, so a `reqId` check alone let the old cell's affirmative card replace
  // "Outside the published area".
  const ins = C.createInspector();
  ins.computePainted(1, 1);
  const req = ins.pointerAt(10, 20);
  ins.pointerLeft();                                  // pointer moves off the raster
  const { render, send } = ins.reply({ reqId: req.reqId, seq: 1, row: 10, col: 20 });
  assert(!render, 'a reply for a cell the pointer has left must not be rendered');
  assert(send === null, 'and nothing queued behind it may be sent either');
  assert(ins.state.inspected === null, 'leaving the data forgets the inspected cell');

  // Coming back works: the generation check must not wedge the card shut.
  const again = ins.pointerAt(11, 21);
  assert(again, 'returning to the map must send again');
  assert(ins.reply({ reqId: again.reqId, seq: 1, row: 11, col: 21 }).render,
    'and that reply must render');
});

check('a queued position from before the pointer left is dropped, not sent', () => {
  const ins = C.createInspector();
  ins.computePainted(1, 1);
  const first = ins.pointerAt(1, 1);
  assert(ins.pointerAt(2, 2) === null, 'the second move is coalesced behind the first');
  ins.pointerLeft();
  const { render, send } = ins.reply({ reqId: first.reqId, seq: 1, row: 1, col: 1 });
  assert(!render && send === null,
    'the queued position was recorded before the pointer left and must not be sent');
});

check('positions are coalesced, and a reply for a cell already left is not rendered', () => {
  // **Pass 52 finding F4.** This check used to assert that the first reply renders, which
  // preserved the failure: the pointer is over (3,3) and the card described (1,1) until the next
  // round trip completed. A reply must name the cell being inspected now.
  const ins = C.createInspector();
  ins.computePainted(1, 1);
  const first = ins.pointerAt(1, 1);
  assert(ins.pointerAt(2, 2) === null);
  assert(ins.pointerAt(3, 3) === null, 'only one request is in flight');
  const { render, send } = ins.reply({ reqId: first.reqId, seq: 1, row: 1, col: 1 });
  assert(!render, 'the pointer has moved to (3,3); (1,1) must not be rendered');
  assert(send && send.row === 3 && send.col === 3,
    `the newest queued position must be the one sent, got ${JSON.stringify(send)}`);
  // And that one does render, because it is where the pointer is.
  assert(ins.reply({ reqId: send.reqId, seq: 1, row: 3, col: 3 }).render,
    'the reply for the current cell must render');
});

check('a reply for the wrong cell is never rendered, whatever else is current', () => {
  const ins = C.createInspector();
  ins.computePainted(1, 1);
  const req = ins.pointerAt(5, 6);
  // Everything else about this reply is current: the request id, the generation, the compute.
  assert(!ins.reply({ reqId: req.reqId, seq: 1, row: 5, col: 7 }).render,
    'a reply one column away from the inspected cell must not render');
});

check('a failed request settles instead of wedging the inspector', () => {
  // **Pass 52 finding F5.** A worker `error` for an explanation left the request outstanding for
  // ever: every later hover queued behind a reply that was never coming, and leaving the map,
  // resetting the criteria and further successful computes all failed to recover it.
  const ins = C.createInspector();
  ins.computePainted(1, 1);
  const req = ins.pointerAt(1, 1);
  assert(req && ins.state.pending, 'a request is outstanding');

  // Nothing is re-sent for the cell that just failed: that would retry the failing request, and
  // a deterministic failure then loops without bound. What must be true is that the inspector is
  // SETTLED, so the next pointer move gets through.
  assert(ins.requestFailed() === null, 'the failed cell must not be retried automatically');
  const after = ins.pointerAt(2, 2);
  assert(after, 'the next pointer move must be sent, so the card is not wedged shut');
  assert(ins.reply({ reqId: after.reqId, seq: 1, row: 2, col: 2 }).render,
    'and its reply must render');
  // Calling it twice is harmless: there is nothing outstanding the second time.
  const ins0 = C.createInspector();
  ins0.computePainted(1, 1);
  ins0.pointerAt(1, 1);
  ins0.requestFailed();
  assert(ins0.requestFailed() === null, 'a second failure with nothing outstanding sends nothing');

  // A failure with a newer position queued sends that one instead.
  const ins2 = C.createInspector();
  ins2.computePainted(1, 1);
  ins2.pointerAt(1, 1);
  ins2.pointerAt(4, 4);
  const next = ins2.requestFailed();
  assert(next && next.row === 4 && next.col === 4, JSON.stringify(next));

  // A failure after the pointer has left sends nothing and does not wedge.
  const ins3 = C.createInspector();
  ins3.computePainted(1, 1);
  ins3.pointerAt(1, 1);
  ins3.pointerLeft();
  assert(ins3.requestFailed() === null, 'nothing to re-ask once the pointer has left');
  const back = ins3.pointerAt(2, 2);
  assert(back, 'and the inspector still works afterwards');
});

check('a superseded request is not rendered', () => {
  const ins = C.createInspector();
  ins.computePainted(1, 1);
  const first = ins.pointerAt(1, 1);
  ins.reply({ reqId: first.reqId, seq: 1, row: 1, col: 1 });
  const second = ins.pointerAt(2, 2);
  assert(!ins.reply({ reqId: first.reqId, seq: 1, row: 2, col: 2 }).render,
    'an older reqId must not render over a newer request');
  assert(ins.reply({ reqId: second.reqId, seq: 1, row: 2, col: 2 }).render);
});

check('the combined headline states the verdict it was given, and no other', () => {
  // **Pass 53 finding F7.** Replacing `VERDICT_TEXT[msg.verdictName]` with
  // `VERDICT_TEXT.INCLUDED` passed all 29 card checks, so an excluded cell read "Every criterion
  // you have on is satisfied here." The block assertions authenticate criterion bodies; nothing
  // mentioned the sentence above them.
  for (const [name, text] of Object.entries(C.VERDICT_TEXT)) {
    const html = C.renderCardHTML(reply([crit({})], { verdictName: name }));
    const head = html.split('class="crit"')[0];
    assert(head.includes(text), `${name}: ${head}`);
    for (const [other, otherText] of Object.entries(C.VERDICT_TEXT)) {
      if (other !== name) {
        assert(!head.includes(otherText), `${name} headline also claims ${other}: ${head}`);
      }
    }
  }
});

check('a block never carries another criterion\'s destination', () => {
  const html = C.renderCardHTML(reply([
    crit({ layer: 'walk-grocery',
      namesDestination: { ordinal: 1, nodeIndex: 9, placeCount: 1,
        places: [{ name: 'Weaver Street Market' }] } }),
    crit({ layer: 'drive-work', outcome: 2, outcomeName: 'UNKNOWN', status: 4,
      statusName: 'LAYER_UNKNOWN', value: null, namesDestination: null }),
  ], { verdict: 2, verdictName: 'UNKNOWN' }));
  const blocks = html.split('class="crit"').slice(1);
  assert(blocks.length === 2, `${blocks.length} blocks`);
  assert(blocks[0].includes('Weaver Street Market'), blocks[0]);
  assert(!blocks[1].includes('Weaver Street Market'),
    `the second criterion carries the first's shop: ${blocks[1]}`);
  assert(!blocks[0].includes('drive-work') && !blocks[1].includes('walk-grocery'),
    'a block names another criterion');
});

check('a reply that names no compute is not rendered', () => {
  // **Pass 53 F8's second witness.** `msg.seq === undefined ||` exempted a reply that named no
  // compute, so an old answer delivered without a `seq` replaced "Recomputing..." with the
  // previous criteria's card.
  const ins = C.createInspector();
  ins.computePainted(1, 1);
  const req = ins.pointerAt(1, 1);
  assert(!ins.reply({ reqId: req.reqId, row: 1, col: 1 }).render,
    'a reply with no seq must not render');
  // The control: the same reply WITH its compute named does render, so the refusal above is
  // about the missing `seq` and nothing else.
  assert(ins.reply({ reqId: req.reqId, seq: 1, row: 1, col: 1 }).render,
    'a reply that names the displayed compute must render');
});

check('nothing renders while a compute is in flight', () => {
  const ins = C.createInspector();
  ins.computePainted(1, 1);
  const req = ins.pointerAt(1, 1);
  ins.computeStarted();
  assert(ins.state.displayedSeq === null);
  assert(!ins.reply({ reqId: req.reqId, seq: 1, row: 1, col: 1 }).render,
    'no reply may render while the screen shows no settled compute');
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
