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
   * quad in Mercator space, while these rows are linear in latitude.
   *
   * Two components, and the second was missed at first:
   *
   * * the **projection** difference over this bundle's latitude span (35.7 to 36.15) is at most
   *   **0.366 rows**, which is 35.6 m at a 97.5 m row. Arithmetic on the bounds.
   * * MapLibre also **quantises the corner positions** to integer tile coordinates before
   *   drawing, which `CanvasSource` inherits from `ImageSource`. Codex pass 51 read the pinned
   *   v5.24.0 source and puts the combined maximum at about **0.388 rows, roughly 37.8 m**, plus
   *   about **0.023 columns** horizontally -- longitude is linear in Mercator, so it has no
   *   curvature error, but quantisation still shifts it. That reading has not been reproduced
   *   here and is recorded as its figure, not as ours.
   *
   * So: up to about **four tenths of a row**, which near a boundary is a whole cell. A pointer
   * within roughly 38 m of a horizontal cell edge can be shown one cell's colour and told about
   * its neighbour. **None of this is a screen-space measurement** -- it is analysis of the
   * placement path, and measuring what is actually drawn is still owed.
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
   * A bound is not a time. "20 minutes" and a bound are different claims and the status plane
   * exists to keep them apart, so this never prints a bare number for a bound.
   *
   * **And "at least N minutes" was itself an overstatement** -- pass 51 finding B3. The value byte
   * holds `ceil(bound_seconds / 60)`, so a byte of 11 means the bound is somewhere in
   * `(600, 660]` seconds. A journey of 630 seconds is compatible with that evidence and takes
   * **less** than 11 minutes, so "at least 11 min" claims more than the data supports. What the
   * byte does establish is `bound > 60 * (v - 1)`, which is "more than v-1 minutes".
   *
   * At `v = 0` the bound is zero and establishes nothing; the audit harness's reconstruction
   * writes exactly that for an `OFF_NETWORK` cell, and `outcomeFor` can never turn it into a
   * failure, so the card says it carries no bound rather than printing "more than -1 min".
   */
  function minutesText(crit) {
    if (crit.value === null || crit.value === undefined) return null;
    if (!crit.valueIsLowerBound) return `${crit.value} min`;
    if (crit.value <= 0) return 'no lower bound published';
    return `more than ${crit.value - 1} min`;
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

  /** The card's request lifecycle, as a state machine with no DOM and no worker.
   *
   * **Both of pass 51's presentation findings were in this logic, and it was untestable.** B1: a
   * cell shown as PASS at a 15-minute limit kept saying PASS, with "your limit 15 min",
   * indefinitely after the limit moved to 5 and the raster excluded it — nothing invalidated the
   * card when the criteria changed. B5: with one request in flight, the pending request is still
   * the newest one *sent*, so after the pointer left the raster its late reply replaced "Outside
   * the published area" with the old cell's affirmative card.
   *
   * Both are about which replies may reach the screen, which is decidable without a browser. So
   * it lives here and `card_selftest.mjs` drives it; `app.js` supplies `postMessage` and the DOM.
   *
   * Three things can make a reply obsolete, and all three are checked:
   *
   * * a newer **request** was sent (`reqId`);
   * * the pointer has left the data since the request was sent (`pointerGen`);
   * * the **compute** the reply describes is not the one on screen (`seq` against
   *   `displayedSeq`), which is the one a `reqId` check cannot see.
   */
  function createInspector() {
    const s = {
      reqSeq: 0,
      pending: false,
      queued: null,
      pointerGen: 0,
      sentGen: 0,
      //: The cell the card describes, so a finished compute can refresh it in place.
      inspected: null,
      //: The compute whose raster is on screen. `null` while one is in flight: the new answer
      //: does not exist until it has painted, and the old one no longer describes the criteria.
      displayedSeq: null,
    };

    function sendNow(row, col) {
      s.pending = true;
      s.queued = null;
      s.sentGen = s.pointerGen;
      return { reqId: ++s.reqSeq, row, col };
    }

    return {
      state: s,
      /** Pointer is over a cell. Returns the request to send, or null if it was coalesced. */
      pointerAt(row, col) {
        s.inspected = { row, col };
        if (s.pending) {
          s.queued = { row, col, gen: s.pointerGen };
          return null;
        }
        return sendNow(row, col);
      },
      /** Pointer left the raster or the map. Nothing in flight is about anywhere on screen. */
      pointerLeft() {
        s.pointerGen++;
        s.queued = null;
        s.inspected = null;
      },
      /** A compute was requested: the raster on screen is about to stop being the answer. */
      computeStarted() {
        s.displayedSeq = null;
      },
      /** A compute's raster has painted. Returns a request to refresh the card, or null.
       *
       * `seq !== newestSeq` means an older result painted after a newer one was requested; it
       * must not claim the screen.
       */
      computePainted(seq, newestSeq) {
        if (seq !== newestSeq) return null;
        s.displayedSeq = seq;
        if (!s.inspected) return null;
        if (s.pending) {
          s.queued = { row: s.inspected.row, col: s.inspected.col, gen: s.pointerGen };
          return null;
        }
        return sendNow(s.inspected.row, s.inspected.col);
      },
      /** A reply arrived. Returns whether to render it, and the next request to send. */
      reply(msg) {
        s.pending = false;
        const render = msg.reqId === s.reqSeq
          && s.sentGen === s.pointerGen
          && (msg.seq === undefined || msg.seq === s.displayedSeq);
        const next = s.queued;
        s.queued = null;
        const send = (next && next.gen === s.pointerGen) ? sendNow(next.row, next.col) : null;
        return { render, send };
      },
    };
  }

  root.G3Card = { WHY_UNKNOWN, VERDICT_TEXT, esc, cellForLonLat, minutesText, destinationText,
    renderCardHTML, createInspector };
})(typeof self !== 'undefined' ? self : globalThis);
