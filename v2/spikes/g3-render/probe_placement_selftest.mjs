// probe_placement_selftest.mjs — can the placement probe fail?
//
// `probe_placement.js` is the instrument for queue item 3: it asks the live page where it draws
// the published raster and compares that against `docs/experiments/s3-10-drawn-pixel.json`, an
// oracle written before any browser ran. An instrument that reports agreement whatever the page
// does would be worse than no instrument, because its agreement would be quoted. So this runs the
// probe against three stub pages, in Node, before it meets a browser:
//
//   * **Mercator** — a page that places the quad's corners in Web Mercator, which is what the
//     canvas-source contract says MapLibre does. The probe must report ZERO disagreements with
//     the oracle, and must report the three sensitive probes as cases where the picture
//     contradicts the card.
//   * **linear in latitude** — a page with no displacement at all. The probe MUST disagree with
//     the oracle on every sensitive probe. This is the hypothesis the measurement exists to rule
//     out, and if the probe cannot tell it apart from Mercator it is measuring nothing.
//   * **one whole row out** — a page displaced by a full row. The probe MUST disagree on more
//     than the sensitive probes, because a whole row moves cells the sub-row offset leaves alone.
//
// The painted pixels are not taken from the oracle: they come from `worker.js` computing the real
// published bundle, so the probe's RGBA comparison has an independent source on both sides.
//
// Run:  node spikes/g3-render/probe_placement_selftest.mjs

import { createRequire } from 'module';
import { fileURLToPath } from 'url';
import fs from 'fs';
import path from 'path';
import vm from 'vm';

const require = createRequire(import.meta.url);
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const BUNDLE = path.join(__dirname, 'fixtures', 'published');
// Loaded at module scope so the opening-state rules are available before the bundle is
// painted; the `require` lower down is then a cache hit. Read from card.js rather than
// restated here: two copies of "which criteria open on" is one copy too many.
require(path.join(__dirname, 'card.js'));
const CARD = globalThis.G3Card;
const ORACLE = path.join(__dirname, '..', '..', '..', 'docs', 'experiments',
  's3-10-drawn-pixel.json');

let failures = 0;
const pending = [];

function report(name, err) {
  if (err) {
    failures++;
    console.error(`FAIL  ${name}\n      ${err && err.message ? err.message : err}`);
  } else {
    console.log(`PASS  ${name}`);
  }
}

/** Run one check. **If it returns a promise, the result is not known yet.**
 *
 * Codex pass 55 finding F6. This used to print PASS the instant `fn()` returned, and three of
 * the checks below return promises -- the colour-tolerance control, the wrong-grid refusal and
 * the tilted-map refusal. `process.exit()` at the end of this synchronous script ran before any
 * of their continuations, so **their assertions never executed**, for a day, while the runner
 * printed "13 checks, all passed" and that figure was quoted into three documents. The
 * counterexample: replace the tolerance check's assertion with `assert(false, ...)` and the run
 * still ends "all checks passed", exit 0. Reproduced before repairing.
 *
 * The colour-tolerance check was the worst of the three to lose. It is the control that the
 * one-count RGBA tolerance has not turned the colour comparison off -- a control I added the day
 * before, for a risk I had identified myself, which had never once run.
 */
function check(name, fn) {
  let out;
  try {
    out = fn();
  } catch (err) {
    report(name, err);
    return;
  }
  if (out && typeof out.then === 'function') {
    pending.push(out.then(() => report(name, null), (err) => report(name, err)));
    return;
  }
  report(name, null);
}

/** **The control on the runner, not on the probe.**
 *
 * `fn` must fail. This check passes when its failure is actually observed, so it is red exactly
 * when the runner has gone back to reporting an unfinished async check as a pass. No ordinary
 * check can see that, because an ordinary check cannot tell whether it ran.
 */
function checkAnAsyncFailureIsSeen(name, fn) {
  pending.push(Promise.resolve().then(fn).then(
    () => report(name, new Error('a deliberately failing async check was reported as passing')),
    () => report(name, null)));
}

function assert(cond, msg) { if (!cond) throw new Error(msg || 'assertion failed'); }

// ---- the real paint, from the real worker on the real bundle ----------------------------------

function paintTheBundle(thresholdMin) {
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
  // **The OPENING view, not every criterion.** This probe asks where the raster lands on screen;
  // it needs a mask with edges in it to see a displacement at all. Enabling all seven criteria
  // paints their intersection, which is nearly empty, and seven of the fourteen checks below then
  // fail for want of structure -- the inert control included, which is the tell. The opening view
  // is also the mask every figure in s3-10 and s3-11 was measured against, back when it was the
  // only one the bundle could paint.
  const opensOn = manifest.layers.map((l) => CARD.layerOpensOn(l));
  if (!opensOn.some(Boolean)) throw new Error('no layer opens on; there is nothing to place');
  const out = send({ type: 'compute', seq: 1,
    thresholds: manifest.layers.map(() => thresholdMin),
    enabled: opensOn });
  globalThis.self = prevSelf;
  const result = out.find((m) => m.type === 'result');
  if (!result) throw new Error('the worker returned no result for the published bundle');
  return { manifest, rgba: new Uint8Array(result.rgba), send };
}

// ---- three stub pages --------------------------------------------------------------------------

const WIDTH = 900;
const HEIGHT = 700;

/** A page that places the raster by `rowAt`, and paints the real bundle. `rowAt` maps a latitude
 *  to the fractional texture row the page draws there; a projection is built to realise it. */
function stubPage(manifest, rgba, placement) {
  const { nrows, ncols } = manifest;
  const [W, S, E, N] = manifest.bounds_wgs84;
  // Screen y is an affine function of the chosen placement, so the quad's north edge lands at 40
  // and its south edge at HEIGHT - 40 whichever rule is in force. The probe reads the placement
  // through project/unproject exactly as it would read MapLibre's.
  const yTop = 40;
  const yBottom = HEIGHT - 40;
  const u = (lat) => placement(lat) / nrows;              // 0 at the north edge, 1 at the south
  const uy = (y) => (y - yTop) / (yBottom - yTop);
  const latOf = (y) => {
    // Invert `u` numerically: the stub does not need to be fast and a bisection cannot drift.
    // The range runs a whole footprint beyond each edge, because two probes sit outside the
    // published area on purpose and a real map projects those perfectly well.
    let lo = S - (N - S);
    let hi = N + (N - S);
    for (let i = 0; i < 80; i++) {
      const mid = (lo + hi) / 2;
      if (u(mid) < uy(y)) hi = mid; else lo = mid;
    }
    return (lo + hi) / 2;
  };
  const xLeft = 30;
  const xRight = WIDTH - 30;
  return {
    ready: () => true,
    grid: () => ({ nrows, ncols, bounds: manifest.bounds_wgs84.slice() }),
    project: (lon, lat) => ({
      x: xLeft + ((lon - W) / (E - W)) * (xRight - xLeft),
      y: yTop + u(lat) * (yBottom - yTop),
    }),
    unproject: (x, y) => ({
      lon: W + ((x - xLeft) / (xRight - xLeft)) * (E - W),
      lat: latOf(y),
    }),
    maskPixel: (col, row) => {
      const p = (row * ncols + col) * 4;
      return quantise([rgba[p], rgba[p + 1], rgba[p + 2], rgba[p + 3]]);
    },
    bearingPitch: () => ({ bearing: 0, pitch: 0 }),
    canvasRect: () => ({ left: 0, top: 0, width: WIDTH, height: HEIGHT }),
  };
}

/** What a real canvas does to a translucent pixel, and what this file used not to do.
 *
 *  A canvas stores colour premultiplied by alpha in eight bits, so a read-back cannot return the
 *  byte that was written. This reproduces Chrome exactly: the page's blue (24,119,242,150) comes
 *  back (24,119,241,150) and its hatch grey (60,60,60,130) comes back (61,61,61,130), while
 *  opaque pixels are untouched. The stub returned the written bytes, so the probe's exact RGBA
 *  comparison passed here and failed on the first real page. A stub must be at least as hostile
 *  as the thing it stands in for. */
const quantise = ([r, g, b, a]) => (a === 0 || a === 255 ? [r, g, b, a]
  : [r, g, b].map((c) => Math.round(Math.round((c * a) / 255) * (255 / a))).concat(a));

const mercatorY = (lat) => Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI / 180) / 2));

function placements(manifest) {
  const { nrows } = manifest;
  const [, S, , N] = manifest.bounds_wgs84;
  const yn = mercatorY(N);
  const ys = mercatorY(S);
  return {
    // What the canvas-source contract says: linear in Mercator y.
    mercator: (lat) => ((yn - mercatorY(lat)) / (yn - ys)) * nrows,
    // The hypothesis the measurement rules out: no displacement at all.
    linear: (lat) => ((N - lat) / (N - S)) * nrows,
    // A larger distortion of the same kind, bulging two rows in the middle and nothing at the
    // edges. It shows the probe's reach is not confined to the three boundary probes.
    bulge: (lat) => ((yn - mercatorY(lat)) / (yn - ys)) * nrows
      + 2 * Math.sin(Math.PI * ((N - lat) / (N - S))),
    // **The probe's blind spot, on purpose.** The texture is placed a whole row off, and both the
    // corners and the interior move with it. The probe recovers the drawn row from the screen
    // positions of the quad's own corners, so any affine error -- a constant offset, a uniform
    // stretch -- cancels and it reports agreement. Only the SHAPE of the placement is visible to
    // it. Closing this needs a rendered pixel: one screenshot at a colour edge, checked against
    // the screen row the oracle predicts.
    constantOffset: (lat) => ((yn - mercatorY(lat)) / (yn - ys)) * nrows + 1,
  };
}

// ---- the probe, loaded the way a browser would load it -----------------------------------------

function loadProbe() {
  require(path.join(__dirname, 'card.js'));
  const card = globalThis.G3Card;
  assert(card && typeof card.cellForLonLat === 'function', 'card.js did not export G3Card');
  const src = fs.readFileSync(path.join(__dirname, 'probe_placement.js'), 'utf8');
  vm.runInThisContext(src, { filename: 'probe_placement.js' });
  assert(typeof globalThis.g3RunPlacementProbe === 'function',
    'probe_placement.js did not define g3RunPlacementProbe');
  return { card, run: globalThis.g3RunPlacementProbe };
}

/** Install the globals the probe expects. With `hover`, the stub canvas answers a pointer move
 *  the way `wireCardPointer` in `app.js` does — the cell label first, "Reading this spot…", then
 *  the real card from a real `explainAt` one tick later — so the probe's settling loop is
 *  rehearsed here rather than discovered in a browser. */
function installWindow(card, probe, hover) {
  const cardEl = { innerHTML: '<em>Move the pointer over the map.</em>', textContent: '' };
  const cellEl = { textContent: '' };
  const strip = (html) => html.replace(/<[^>]*>/g, '');
  cardEl.textContent = strip(cardEl.innerHTML);
  const set = (html) => { cardEl.innerHTML = html; cardEl.textContent = strip(html); };
  globalThis.window = { G3Card: card, G3Probe: probe, setTimeout: globalThis.setTimeout };
  globalThis.document = {
    getElementById: (id) => (id === 'card' ? cardEl : cellEl),
    querySelector: () => ({
      dispatchEvent: (ev) => {
        if (!hover) return true;
        const { lon, lat } = probe.unproject(ev.clientX, ev.clientY);
        const g = probe.grid();
        const at = card.cellForLonLat(g.bounds, g.ncols, g.nrows, lon, lat);
        if (!at) {
          cellEl.textContent = '';
          set(card.renderCardHTML({ outside: true }));
          return true;
        }
        cellEl.textContent = `(row ${at.row}, col ${at.col})`;
        set('<em>Reading this spot…</em>');
        setTimeout(() => {
          const msgs = hover.send({ type: 'explainAt', reqId: 1, row: at.row, col: at.col });
          set(card.renderCardHTML(msgs.find((m) => m.type === 'explainAt')));
        }, 20);
        return true;
      },
    }),
  };
  // IDL `long`: a fractional clientX is truncated when the event is constructed. Chrome does
  // this; the stub did not, so the probe's sub-pixel pointer worked here and landed in the wrong
  // cell on the first real page.
  globalThis.MouseEvent = class {
    constructor(type, init) {
      Object.assign(this, init);
      this.clientX = Math.trunc(init.clientX);
      this.clientY = Math.trunc(init.clientY);
    }
  };
}

// ---- the three runs ----------------------------------------------------------------------------

const oracle = JSON.parse(fs.readFileSync(ORACLE, 'utf8'));
const { manifest, rgba, send } = paintTheBundle(oracle.page_default_threshold_min);
const place = placements(manifest);
const { card, run } = loadProbe();
const sensitiveIds = oracle.probes.filter((p) => p.sensitive).map((p) => p.id);

async function runWith(name, hover) {
  installWindow(card, stubPage(manifest, rgba, place[name]), hover ? { send } : null);
  const out = await run(oracle, { hover: Boolean(hover) });
  assert(out.ran, `the probe refused to run on the ${name} page: ${out.why}`);
  return out;
}

const mercatorRun = await runWith('mercator');
const linearRun = await runWith('linear');
const bulgeRun = await runWith('bulge');
const offsetRun = await runWith('constantOffset');
const hoverRun = await runWith('mercator', true);
const rectLeft = 0;
const rectTop = 0;

check('the oracle declares probes that can fail', () => {
  assert(sensitiveIds.length >= 3, `${sensitiveIds.length} sensitive probes`);
  assert(oracle.displacement.row_centres_where_the_two_rules_disagree === 0,
    'the oracle no longer records that cell centres cannot distinguish the two rules');
});

check('on a Mercator-placed page the probe agrees with the oracle exactly', () => {
  const bad = mercatorRun.probes.filter((p) => p.disagreements.length);
  assert(mercatorRun.disagreements_with_the_oracle === 0,
    `${mercatorRun.disagreements_with_the_oracle} disagreements: `
    + JSON.stringify(bad.map((p) => [p.id, p.disagreements]), null, 1));
});

check('and reports the picture contradicting the card at every sensitive probe', () => {
  assert(mercatorRun.sensitive_probes === sensitiveIds.length,
    `${mercatorRun.sensitive_probes} sensitive probes seen`);
  assert(mercatorRun.sensitive_probes_where_the_picture_contradicted_the_card
    === sensitiveIds.length,
  `${mercatorRun.sensitive_probes_where_the_picture_contradicted_the_card} of `
    + `${sensitiveIds.length} contradicted`);
});

check('the RGBA it reads is the worker\'s own paint, not the oracle\'s copy of it', () => {
  const p = mercatorRun.probes.find((x) => x.id === sensitiveIds[0]);
  assert(p.rgba_of_the_cell_the_card_names.join() !== p.rgba_under_the_pointer.join(),
    'the two pixels are identical, so this probe cannot show a contradiction');
  const oracleProbe = oracle.probes.find((x) => x.id === sensitiveIds[0]);
  // To within the one count per channel that premultiplied alpha costs on a canvas, and with
  // alpha exact. The bytes are deliberately NOT required to be identical: the stub quantises the
  // way Chrome does, so a reading that matched the oracle byte for byte would be a copy of it.
  const oraclePx = oracleProbe.expected_card.rgba_of_the_cell_the_card_names;
  const read = p.rgba_of_the_cell_the_card_names;
  assert(read[3] === oraclePx[3] && read.slice(0, 3).every((v, i) => Math.abs(v - oraclePx[i]) <= 1),
    `the worker paints this cell ${read} where the oracle predeclared ${oraclePx}`);
});

check('a page with NO displacement is caught, at every sensitive probe', () => {
  const caught = sensitiveIds.filter((id) => {
    const p = linearRun.probes.find((x) => x.id === id);
    return p.disagreements.some((d) => d.what === 'the row the page draws here');
  });
  assert(caught.length === sensitiveIds.length,
    `only ${caught.length} of ${sensitiveIds.length} sensitive probes noticed: `
    + JSON.stringify(linearRun.probes.filter((p) => p.sensitive)
      .map((p) => [p.id, p.drawn_minus_published_row, p.disagreements.length])));
});

check('a larger distortion of the same kind is caught beyond the boundary probes', () => {
  // Count PROBES that noticed, not disagreements. A bigger error can report fewer disagreements
  // than a smaller one, because two rows further away can happen to be painted the same colour
  // and then only the row itself disagrees. The question here is reach, which is how many of the
  // eleven readings can see anything at all.
  const noticed = (run) => run.probes.filter((p) => p.disagreements.length).length;
  assert(noticed(bulgeRun) > noticed(linearRun),
    `bulged: ${noticed(bulgeRun)} probes noticed, no displacement: ${noticed(linearRun)}`);
  const inert = bulgeRun.probes.find((p) => p.id === 'inert_interior');
  assert(inert.disagreements.length > 0,
    'a two-row bulge left the interior probe agreeing, so the probe only ever looks at the three '
    + 'boundary points and its other nine readings establish nothing');
});

check('and the probe DECLARES the error it cannot see, rather than passing over it', () => {
  // A constant offset moves the corners with the interior, and the probe reads the drawn row
  // from where the corners project, so it cancels. This check exists so that the limitation is
  // recorded by a passing test instead of discovered later in a quoted number.
  assert(offsetRun.disagreements_with_the_oracle === 0,
    `a constant offset was reported as ${offsetRun.disagreements_with_the_oracle} disagreements, `
    + 'which would be welcome but is not what this geometry can do; the check below is now wrong');
  assert(/screenshot/.test(mercatorRun.what_this_cannot_see || ''),
    'the probe does not say in its own output that an affine placement error is invisible to it, '
    + 'so a clean run could be read as more than it is');
});

check('the inert control agrees on the Mercator page, so agreement is not automatic', () => {
  const inert = mercatorRun.probes.find((p) => p.id === 'inert_interior');
  assert(inert && inert.disagreements.length === 0, 'the inert probe disagreed on a correct page');
  assert(inert.drawn_minus_published_row === 0,
    `the inert probe sits ${inert.drawn_minus_published_row} rows out, so it is not inert`);
  assert(inert.the_picture_contradicts_the_card_here === false,
    'the inert probe reports a contradiction on a correct page');
});

check('the hover half reads a real card at every probe, and waits for it', () => {
  assert(hoverRun.disagreements_with_the_oracle === 0,
    JSON.stringify(hoverRun.probes.filter((p) => p.disagreements.length)
      .map((p) => [p.id, p.disagreements]), null, 1));
  for (const p of hoverRun.probes) {
    assert(p.hover, `${p.id}: no card was read`);
    assert(!p.hover.timed_out, `${p.id}: the settling loop timed out on a card that did arrive, `
      + 'which in a browser would spend the session waiting');
    assert(!/Reading this spot/.test(p.hover.card_text),
      `${p.id}: the interim text was accepted as the card: ${p.hover.card_text}`);
  }
  // The card that matters: a PASS at exactly the default threshold, on a restricted route, to a
  // junction carrying two places. One hover exercises all three disclosures.
  const north = hoverRun.probes.find((p) => p.id === 'boundary_north');
  assert(north, 'boundary_north is gone from the oracle');
  assert(/Weaver Street Market/.test(north.hover.card_text), north.hover.card_text);
  assert(/restricted|private/i.test(north.hover.card_text), north.hover.card_text);
  assert(north.hover.cell_label.trim() === '(row 100, col 73)', north.hover.cell_label);
  assert(north.hover.placed_on_the_probe_cell,
    'the pointer could not be placed on the probe cell, so this card is about somewhere else');
  for (const p of hoverRun.probes) {
    assert(Number.isInteger(p.hover.pointer_landed_at.x + rectLeft)
      && Number.isInteger(p.hover.pointer_landed_at.y + rectTop),
    `${p.id}: the pointer was placed on a fractional client pixel, which a browser truncates`);
  }
});

check('the colour tolerance does not blind the comparison it loosens', () => {
  // One count per channel is what premultiplied alpha costs. Three is a different picture, and
  // must still be caught, or the tolerance has quietly turned the RGBA check off.
  const base = stubPage(manifest, rgba, place.mercator);
  installWindow(card, { ...base,
    maskPixel: (c, r) => { const px = base.maskPixel(c, r); return [px[0], px[1], px[2] - 3, px[3]]; } });
  return run(oracle, { hover: false }).then((out) => {
    const colour = out.probes.flatMap((p) => p.disagreements)
      .filter((d) => /painted input/.test(d.what));
    assert(colour.length > 0, 'a three-count colour shift went unnoticed');
  });
});

check('and a point outside the footprint is told so, in words', () => {
  for (const id of ['outside_west', 'outside_north']) {
    const p = hoverRun.probes.find((x) => x.id === id);
    assert(/Outside the published area/.test(p.hover.card_text),
      `${id}: ${p.hover.card_text}`);
  }
});

check('the probe refuses a page it cannot compare against', () => {
  installWindow(card, stubPage(manifest, rgba, place.mercator));
  const wrongGrid = JSON.parse(JSON.stringify(oracle));
  wrongGrid.published.nrows = manifest.nrows + 1;
  return run(wrongGrid, { hover: false }).then((out) => {
    assert(out.ran === false, 'the probe ran against a grid the oracle was not written for');
  });
});

check('and refuses a tilted map, where its geometry does not hold', async () => {
  const tilted = stubPage(manifest, rgba, place.mercator);
  installWindow(card, { ...tilted, bearingPitch: () => ({ bearing: 0, pitch: 30 }) });
  const out = await run(oracle, { hover: false });
  assert(out.ran === false, 'the probe ran on a tilted map');
  assert(/tilt/.test(out.why), out.why);
});

checkAnAsyncFailureIsSeen(
  'the runner sees an async check fail, which it did not until pass 55',
  async () => { await Promise.resolve(); assert(false, 'this check is meant to fail'); });

// **Nothing may be reported before every check has finished** -- pass 55 F6.
await Promise.all(pending);

console.log(`\n${failures === 0 ? 'all checks passed' : `${failures} FAILED`}`);
process.exit(failures === 0 ? 0 : 1);
