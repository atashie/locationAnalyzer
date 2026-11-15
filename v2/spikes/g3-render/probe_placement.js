/* probe_placement.js — the browser side of queue item 3.
 *
 * One question: **does the page draw the published raster where the publication says it is?**
 *
 * The published rows are linear in latitude. MapLibre draws a `canvas` source as a quad whose four
 * corners are placed in Web Mercator, so the row it paints at a latitude is linear in Mercator *y*
 * instead. `measure_drawn_pixel.py` computes that disagreement — up to 0.3656 of a row, about
 * 36 m, zero at the north and south edges and largest in the middle — and writes
 * `docs/experiments/s3-10-drawn-pixel.json`. **That file is this probe's oracle and it was written
 * before any browser ran.** Nothing here recomputes an expectation; it observes and compares.
 *
 * What makes the probe able to fail: three of its eleven points sit a tenth of a row above a row
 * boundary at a column where the two rows differ in verdict, so the card must name one cell while
 * the pixel under the pointer is painted from the next one down. At a cell *centre* the two rules
 * agree at all 514 rows, so a probe aimed at centres could only ever report agreement — which is
 * why `inert_interior` is here as well, and why its agreement is a control rather than a result.
 *
 * Run it from a session that can reach the page:
 *
 *     eval(<contents of this file>);
 *     await g3RunPlacementProbe(<contents of s3-10-drawn-pixel.json>, { hover: true });
 *
 * `hover` dispatches a real pointer move at each probe's screen position and reads the card the
 * page renders, so the comparison covers the words a household gets and not only the geometry.
 */
'use strict';

/* exported g3RunPlacementProbe */
async function g3RunPlacementProbe(oracle, options) {
  const opts = options || {};
  const P = window.G3Probe;
  const C = window.G3Card;
  const r3 = (n) => Math.round(n * 1000) / 1000;
  const r7 = (n) => Math.round(n * 1e7) / 1e7;
  const same = (a, b) => Array.isArray(a) && Array.isArray(b) && a.length === b.length
    && a.every((v, i) => v === b[i]);

  if (!P) return { ran: false, why: 'window.G3Probe is absent: this page predates the probe accessor' };
  if (!C) return { ran: false, why: 'window.G3Card is absent: card.js did not load' };
  if (!P.ready()) return { ran: false, why: 'the page has not painted a mask yet' };

  // ---- preconditions. A probe run against a different bundle, or a tilted map, would produce
  // ---- numbers that look like findings and are not.
  const bp = P.bearingPitch();
  if (bp.bearing !== 0 || bp.pitch !== 0) {
    return { ran: false, why: `the map is rotated or tilted (bearing ${bp.bearing}, pitch `
      + `${bp.pitch}); the texture row is linear in screen y only for a north-up, untilted map` };
  }
  const grid = P.grid();
  const pub = oracle.published;
  if (grid.nrows !== pub.nrows || grid.ncols !== pub.ncols) {
    return { ran: false, why: `the page carries ${grid.nrows}x${grid.ncols} and the oracle was `
      + `written for ${pub.nrows}x${pub.ncols}` };
  }
  if (!same(grid.bounds.map(r7), pub.bounds_wgs84.map(r7))) {
    return { ran: false, why: `the page's bounds ${JSON.stringify(grid.bounds)} are not the `
      + `oracle's ${JSON.stringify(pub.bounds_wgs84)}` };
  }

  const [W, S, E, N] = grid.bounds;
  const pNW = P.project(W, N);
  const pSW = P.project(W, S);
  const pNE = P.project(E, N);

  /** Which texture pixel the live map draws at a screen point: the quad's corners interpolate
   *  linearly in screen space for an untilted map, so this is MapLibre's own placement, read
   *  through MapLibre's own projection rather than assumed. */
  const drawnCell = (x, y) => ({
    row: Math.floor(((y - pNW.y) / (pSW.y - pNW.y)) * grid.nrows),
    col: Math.floor(((x - pNW.x) / (pNE.x - pNW.x)) * grid.ncols),
  });

  const canvas = document.querySelector('#map canvas');
  const rect = P.canvasRect();

  /** Move a real pointer to a screen position and wait for the card the page renders there. */
  const hoverAndRead = async (x, y) => {
    const cardEl = document.getElementById('card');
    const cellEl = document.getElementById('card-cell');
    const before = cardEl.innerHTML;
    canvas.dispatchEvent(new MouseEvent('mousemove', {
      bubbles: true, cancelable: true, view: window,
      clientX: rect.left + x, clientY: rect.top + y,
    }));
    const deadline = Date.now() + 4000;
    let text = cardEl.textContent;
    while (Date.now() < deadline) {
      text = cardEl.textContent;
      const settled = !/Reading this spot|Awaiting|…$/.test(text.trim())
        && (cardEl.innerHTML !== before || /Outside the published area/.test(text));
      if (settled) break;
      // eslint-disable-next-line no-await-in-loop
      await new Promise((res) => setTimeout(res, 60));
    }
    return { cell_label: cellEl.textContent, card_text: cardEl.textContent.trim(),
             timed_out: Date.now() >= deadline };
  };

  const probes = [];
  for (const probe of oracle.probes) {
    const rec = { id: probe.id, sensitive: !!probe.sensitive, disagreements: [] };
    const note = (what, observed, expected) => rec.disagreements.push({ what, observed, expected });

    const scr = P.project(probe.lon, probe.lat);
    rec.screen = { x: r3(scr.x), y: r3(scr.y) };
    const back = P.unproject(scr.x, scr.y);
    // A control on the projection itself: if project and unproject do not round-trip, every
    // number below is suspect and nothing else in this record means anything.
    rec.round_trip_degrees = { lon: r7(back.lon - probe.lon), lat: r7(back.lat - probe.lat) };
    if (Math.abs(back.lon - probe.lon) > 1e-6 || Math.abs(back.lat - probe.lat) > 1e-6) {
      note('project/unproject round trip', rec.round_trip_degrees, 'within 1e-6 degrees');
    }

    const card = C.cellForLonLat(grid.bounds, grid.ncols, grid.nrows, probe.lon, probe.lat);
    rec.card_cell = card;
    const expected = probe.expected_published_cell;
    if (!card !== !expected) {
      note('the page resolves a cell here', card, expected);
    } else if (card && expected && (card.row !== expected.row || card.col !== expected.col)) {
      note('the cell the card names', card, expected);
    }

    if (card && expected) {
      const d = drawnCell(scr.x, scr.y);
      rec.drawn_cell = d;
      rec.drawn_minus_published_row = d.row - card.row;
      if (d.row !== probe.expected_drawn_row) {
        note('the row the page draws here', d.row, probe.expected_drawn_row);
      }
      // Columns are linear in longitude under both rules, so a moved column is a different fault
      // from the one being measured and must not be folded into it.
      if (d.col !== card.col) {
        note('the column the page draws here (columns must not move)', d.col, card.col);
      }
      rec.rgba_of_the_cell_the_card_names = P.maskPixel(card.col, card.row);
      rec.rgba_under_the_pointer = P.maskPixel(d.col, d.row);
      if (!same(rec.rgba_of_the_cell_the_card_names,
                probe.expected_card.rgba_of_the_cell_the_card_names)) {
        note('the painted input for the card\'s cell', rec.rgba_of_the_cell_the_card_names,
             probe.expected_card.rgba_of_the_cell_the_card_names);
      }
      if (!same(rec.rgba_under_the_pointer, probe.expected_rgba_under_the_pointer)) {
        note('the painted input under the pointer', rec.rgba_under_the_pointer,
             probe.expected_rgba_under_the_pointer);
      }
      rec.the_picture_contradicts_the_card_here =
        !same(rec.rgba_of_the_cell_the_card_names, rec.rgba_under_the_pointer);
      if (rec.the_picture_contradicts_the_card_here
          !== probe.the_picture_contradicts_the_card_here) {
        note('whether the picture contradicts the card here',
             rec.the_picture_contradicts_the_card_here,
             probe.the_picture_contradicts_the_card_here);
      }
    }

    if (opts.hover) {
      // eslint-disable-next-line no-await-in-loop
      const seen = await hoverAndRead(scr.x, scr.y);
      rec.hover = seen;
      const wanted = expected ? `(row ${expected.row}, col ${expected.col})` : '';
      if (expected && seen.cell_label.trim() !== wanted) {
        note('the cell label the card shows', seen.cell_label, wanted);
      }
      if (!expected && !/Outside the published area/.test(seen.card_text)) {
        note('the card for a point outside the footprint', seen.card_text,
             'Outside the published area.');
      }
    }
    probes.push(rec);
  }

  const sensitive = probes.filter((p) => p.sensitive);
  return {
    ran: true,
    oracle: { what: oracle.what_this_is, max_offset_rows: oracle.displacement.max_offset_rows,
              max_offset_metres: oracle.displacement.max_offset_metres },
    view: { zoom: undefined, bearing: bp.bearing, pitch: bp.pitch,
            corner_screen_y: { north: r3(pNW.y), south: r3(pSW.y) },
            drawn_rows_per_screen_pixel: r3(grid.nrows / (pSW.y - pNW.y)) },
    probes,
    disagreements_with_the_oracle: probes.reduce((n, p) => n + p.disagreements.length, 0),
    sensitive_probes: sensitive.length,
    sensitive_probes_where_the_picture_contradicted_the_card:
      sensitive.filter((p) => p.the_picture_contradicts_the_card_here).length,
    what_zero_disagreements_would_mean: ('that the page places the raster exactly as '
      + 'measure_drawn_pixel.py predicts, including the sub-row displacement, so the structure '
      + 'counts in that artifact describe the page a household actually gets'),
    what_this_cannot_see: ('an AFFINE placement error. The drawn row is recovered from where the '
      + "quad's own corners project, so a constant offset or a uniform stretch of the texture "
      + 'cancels out and this probe reports agreement. Only the SHAPE of the placement is visible '
      + 'to it, which is the Mercator-against-latitude question it was built for. Closing the rest '
      + 'needs a rendered pixel: a screenshot at a colour edge, checked against the screen row '
      + 'predicted from corner_screen_y and drawn_rows_per_screen_pixel above.'),
  };
}
