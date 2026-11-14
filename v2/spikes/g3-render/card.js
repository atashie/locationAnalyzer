/* card.js — the per-criterion card's text, shared by app.js (browser) and card_selftest.mjs (Node).
 *
 * **Why this is a separate file.** The three disclosures `docs/s3-decision-report.md` names reach
 * a household as WORDS, and the words are where the disclosure can be lost: printing "no
 * restrictions" where a layer does not disclose, printing "20 min" where the 20 is a lower bound,
 * printing a shop where the pipeline never chose one. None of that is visible to the worker's
 * conformance suite, which checks the message. So the rendering is pure functions over the
 * `explainAt` reply, with no DOM, and `card_selftest.mjs` checks them in Node.
 *
 * Same pattern and the same reason as geom.js: attached to `self`/`globalThis` so one file serves
 * a classic <script> tag and a `require` from an .mjs test.
 */
(function (root) {
  'use strict';

  // Why a criterion says nothing, in words a household can act on, keyed by the wire status name
  // the worker reports. **These are the disclosure.** "Unknown" on its own tells somebody nothing;
  // "we cannot tell you, because this spot is too far from any path we hold" tells them whether to
  // believe it and what to do next.
  const WHY_UNKNOWN = {
    OFF_NETWORK: 'this spot is too far from any path we hold for us to measure from it',
    BEYOND_HORIZON: 'we stopped searching before we reached anywhere that qualifies',
    NO_PATH: 'no route to anywhere qualifying exists in the map we hold',
    LAYER_UNKNOWN: 'this criterion does not know for this spot',
    OUTSIDE: 'this spot is outside the area this criterion covers',
    UNKNOWN_CAUSE: 'the published data has no answer here and does not record why',
  };

  const VERDICT_TEXT = {
    INCLUDED: 'Every criterion you have on is satisfied here.',
    EXCLUDED: 'At least one criterion is not satisfied here.',
    UNKNOWN: 'We cannot say. At least one criterion does not know, and none has ruled this out.',
  };

  /** Everything below comes from a published artifact, so it is escaped rather than trusted: a
   *  place name is upstream data and reaches the DOM as text. */
  function esc(s) {
    return String(s).replace(/[&<>"']/g, (ch) => (
      { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
  }

  /** Pointer lon/lat to the cell whose published answer covers it, or null outside the raster.
   *
   * The published grid is a WGS84 lon/lat grid, so rows are linear in LATITUDE and this is the
   * data's own mapping. Half-open, closed on the north and west edges, matching
   * `GridSpec.cell_for_xy` so the page and the pipeline agree about which cell a point is in.
   *
   * **This is not necessarily the cell the pointer is over in the PICTURE.** MapLibre draws the
   * mask as a `canvas` source from four corner coordinates, interpolating the texture across a
   * quad in Mercator space, while these rows are linear in latitude. Over this bundle's latitude
   * span (35.7 to 36.15) the two disagree by at most 0.366 rows -- 35.6 m at a 97.5 m row -- so a
   * pointer within about 36 m of a horizontal cell boundary can be shown one cell's colour and
   * told about its neighbour. That figure is arithmetic on the bounds, not a browser measurement;
   * measuring it in the browser is its own queue item.
   */
  function cellForLonLat(bounds, ncols, nrows, lon, lat) {
    const [W, S, E, N] = bounds;
    if (!(lon >= W && lon < E && lat > S && lat <= N)) return null;
    const col = Math.floor(((lon - W) / (E - W)) * ncols);
    const row = Math.floor(((N - lat) / (N - S)) * nrows);
    if (row < 0 || row >= nrows || col < 0 || col >= ncols) return null;
    return { row, col };
  }

  /** The published minute as a sentence, or null where the layer published none.
   *
   * A bound is not a time. "At least 20 minutes" and "20 minutes" are different claims, and the
   * status plane exists to keep them apart -- so this never prints a bare number for a bound.
   */
  function minutesText(crit) {
    if (crit.value === null || crit.value === undefined) return null;
    return crit.valueIsLowerBound ? `at least ${crit.value} min` : `${crit.value} min`;
  }

  /** The destination, or null where this criterion does not name one.
   *
   * `namesDestination: null` is "this layer does not say which destination", never "there is no
   * destination", so the caller prints the former and never the latter.
   *
   * Where a node carries several places the pipeline did NOT choose between them: the selection
   * is a cost-argmin over nodes. The card may say which places are there; it may not pick one and
   * present the pick as ours (the owner's rule, 2026-11-13).
   */
  function destinationText(crit) {
    const d = crit.namesDestination;
    if (!d) return null;
    const names = (d.places || []).map((p) => p && p.name).filter(Boolean);
    if (!names.length) return 'measured to a junction whose places this bundle does not name';
    if (d.placeCount > 1 || names.length > 1) {
      return `measured to one of ${d.placeCount} places at this junction: ${names.join(', ')}`;
    }
    return `measured to ${names[0]}`;
  }

  /** The whole card as HTML, from one `explainAt` reply. Pure: no DOM, no state. */
  function renderCardHTML(msg) {
    if (msg.outside) return '<em>Outside the published area.</em>';
    if (msg.notComputed) return '<em>Nothing has been computed yet.</em>';
    if (msg.criteria === null || msg.criteria === undefined) {
      // No criteria excludes nothing, which is NOT "everything qualifies here".
      return '<div class="verdict">No criteria are switched on, so nothing is being asked of '
        + 'this spot.</div>';
    }

    const parts = [`<div class="verdict">${esc(VERDICT_TEXT[msg.verdictName]
      || msg.verdictName)}</div>`];

    for (const crit of msg.criteria) {
      const bits = [];
      bits.push(`<div><span class="crit-name">${esc(crit.layer)}</span>`
        + `<span class="outcome ${esc(crit.outcomeName)}">${esc(crit.outcomeName)}</span></div>`);

      const mins = minutesText(crit);
      if (mins !== null) {
        bits.push(`<div>${esc(mins)} &middot; your limit ${esc(crit.thresholdMin)} min</div>`);
      } else {
        bits.push('<div class="why">no time published &middot; your limit '
          + `${esc(crit.thresholdMin)} min</div>`);
      }

      if (crit.outcomeName === 'UNKNOWN') {
        bits.push('<div class="why">We cannot tell you: '
          + `${esc(WHY_UNKNOWN[crit.statusName] || crit.statusName)}.</div>`);
      } else if (crit.valueIsLowerBound) {
        // A known failure reached without ever computing a route. Worth saying, because it is
        // the one case where our answer does not rest on a journey at all.
        bits.push('<div class="why">Ruled out without computing a route: '
          + `${esc(WHY_UNKNOWN[crit.statusName] || crit.statusName)}.</div>`);
      }

      // The restricted-route disclosure. `null` means this layer does not disclose, and then the
      // card says SO -- printing "no restrictions" would be a claim the data does not make, which
      // is the whole reason the plane is optional.
      if (crit.routeFlag === 1) {
        bits.push('<div class="flag">This route uses a way that is not clearly public — a '
          + 'private drive, a track, or a path with restricted access. Your walk may be longer '
          + 'than the time above.</div>');
      } else if (crit.routeFlag === null || crit.routeFlag === undefined) {
        bits.push('<div class="silent">This criterion does not say whether the route uses a '
          + 'restricted way.</div>');
      }

      const dest = destinationText(crit);
      if (dest) {
        bits.push(`<div class="dest">${esc(dest)}</div>`);
      } else if (crit.outcomeName === 'PASS') {
        bits.push('<div class="silent">This criterion does not say which destination the time '
          + 'was measured to.</div>');
      }

      parts.push(`<div class="crit">${bits.join('')}</div>`);
    }
    return parts.join('');
  }

  root.G3Card = { WHY_UNKNOWN, VERDICT_TEXT, esc, cellForLonLat, minutesText, destinationText,
    renderCardHTML };
})(typeof self !== 'undefined' ? self : globalThis);
