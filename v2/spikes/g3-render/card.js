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

  /** The headline, and **why the affirmative one is hedged** -- Codex pass 54, 2026-11-16.
   *
   * It read "Every criterion you have on is satisfied here", which asserts a fact about the
   * place. What the bundle holds is a model estimate: seconds computed from the CELL CENTRE
   * (`locfinder/traveltime/layer.py:50`, `grid.cell_centers_xy()`) over our own graph and speed
   * model, then rounded UP to the whole minute (`grid.encode_minutes`, `uint8-minutes-ceil-v1`).
   * A cell can also be INCLUDED on a route our own flag plane calls not clearly public. None of
   * that makes the number wrong. It makes "is satisfied here" a stronger claim than the evidence,
   * and the household who acts on it is the one who then never checks.
   *
   * **The two negative headlines are left as they were, and that is the owner's call to
   * revisit.** They are the same kind of claim, stated the same way. `ESTIMATE_NOTE` is printed
   * under ALL THREE for that reason: a card that hedged only its affirmative verdict would
   * present an exclusion as the more certain answer, which is a new asymmetry rather than a
   * repair.
   */
  const VERDICT_TEXT = {
    INCLUDED: 'The model estimates this cell meets your limits.',
    EXCLUDED: 'At least one criterion is not satisfied here.',
    UNKNOWN: 'We cannot say. At least one criterion does not know, and none has ruled this out.',
  };

  /** Printed directly under the verdict on every card that has criteria, and nowhere else.
   *
   * **"Rounded up", not "rounded".** `encode_minutes` is `ceil`, so a cell displaying 12 min
   * holds a model time in `(11, 12]` minutes: the number shown OVERSTATES by up to 60 s. `ceil`
   * is right -- the byte is a decision input the worker thresholds directly, and `grid.py` proves
   * the encoded verdict equals the float verdict -- but its docstring justified the cost with
   * "nothing displays it", and this card displays it. So the word has to carry it, and "rounded"
   * alone would read as "to the nearest".
   *
   * It is not printed for `outside`, `notComputed` or no criteria, because there is no time on
   * those cards to qualify.
   */
  const ESTIMATE_NOTE = 'Times are estimates: measured from the centre of this cell, and rounded '
    + 'up to the whole minute.';

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
      || msg.verdictName)}</div>`,
    `<div class="estimate">${esc(ESTIMATE_NOTE)}</div>`];

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

      // The restricted-route disclosure. `null` means this layer does not disclose, and then
      // the card says SO -- printing "no restrictions" would be a claim the data does not make,
      // which is the whole reason the plane is optional.
      //
      // **Its position is load-bearing, and it was wrong** -- pass 54 asked for the
      // qualification "beside the relevant time". This block used to sit below the `why` block,
      // so a warning whose own last sentence says "longer than the time above" could have an
      // explanation of an UNKNOWN status between it and the time it was qualifying. It is now
      // the line directly under the minute, which is what makes "above" true.
      if (crit.routeFlag === 1) {
        bits.push('<div class="flag">This route uses a way that is not clearly public — a '
          + 'private drive, a track, or a path with restricted access. Your walk may be longer '
          + 'than the time above.</div>');
      } else if (crit.routeFlag === null || crit.routeFlag === undefined) {
        bits.push('<div class="silent">This criterion does not say whether the route uses a '
          + 'restricted way.</div>');
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
   * * the reply is about a cell that is not the one being inspected — which covers both the
   *   pointer having left the data and the pointer having moved on to another cell;
   * * the **compute** the reply describes is not the one on screen (`seq` against
   *   `displayedSeq`), which is the one a `reqId` check cannot see.
   *
   * The first version carried a separate `pointerGen` counter for leaving the data. The position
   * check added for F4 subsumes it completely — `pointerLeft` sets `inspected` to `null`, and a
   * reply can then match no cell — so both of its mutations SURVIVED once F4 was fixed. It is
   * removed rather than kept as defence in depth: dead defensive code is a permanent mutation
   * survivor, and this project has paid for that lesson once already in `measure/exact.py`.
   * B5's witness is covered by the position check, and its regression test still asserts the
   * behaviour.
   */
  function createInspector() {
    const s = {
      reqSeq: 0,
      pending: false,
      queued: null,
      //: The cell the card describes. The single source of truth for what is being looked at:
      //: `null` means the pointer is not on the data, and a reply matching no cell cannot render.
      inspected: null,
      //: The compute whose raster is on screen. `null` while one is in flight: the new answer
      //: does not exist until it has painted, and the old one no longer describes the criteria.
      displayedSeq: null,
    };

    function sendNow(row, col) {
      s.pending = true;
      s.queued = null;
      return { reqId: ++s.reqSeq, row, col };
    }

    return {
      state: s,
      /** Pointer is over a cell. Returns the request to send, or null if it was coalesced. */
      pointerAt(row, col) {
        s.inspected = { row, col };
        if (s.pending) {
          s.queued = { row, col };
          return null;
        }
        return sendNow(row, col);
      },
      /** Pointer left the raster or the map. Nothing in flight is about anywhere on screen. */
      pointerLeft() {
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
          s.queued = { row: s.inspected.row, col: s.inspected.col };
          return null;
        }
        return sendNow(s.inspected.row, s.inspected.col);
      },
      /** A reply arrived. Returns whether to render it, and the next request to send. */
      reply(msg) {
        s.pending = false;
        // **The reply must be about the cell the pointer is on now** -- pass 52 finding F4. With
        // one request in flight, moving from (1,1) to (2,2) queues the second and renders the
        // FIRST when its reply lands, so the card describes (1,1) while the pointer is over
        // (2,2) until the next round trip. The generation counter this first carried changed
        // only on LEAVING the data, so it could not see a move between two cells, and the
        // regression test written beside it asserted the first reply renders -- preserving the
        // failure.
        const atInspected = !!s.inspected
          && msg.row === s.inspected.row && msg.col === s.inspected.col;
        // **A matching compute sequence, with no exemption for a missing one** -- pass 53 F8.
        // `msg.seq === undefined ||` accepted a reply that named no compute at all, so an old
        // answer delivered without a `seq` replaced "Recomputing..." with the previous criteria's
        // card. The worker always sends one; a reply that does not is not an answer about the
        // region on screen.
        // `displayedSeq` is `null` while a compute is in flight, and `null` never equals a
        // sequence number, so this one comparison covers both "the reply describes another
        // compute" and "no compute is settled on screen". An explicit `displayedSeq !== null`
        // clause was tried and SURVIVED its mutation, because it can never change the outcome.
        const render = msg.reqId === s.reqSeq
          && atInspected
          && msg.seq === s.displayedSeq;
        const next = s.queued;
        s.queued = null;
        const send = next ? sendNow(next.row, next.col) : null;
        return { render, send };
      },
      /** The outstanding request will never be answered. Returns the next request to send.
       *
       * **Pass 52 finding F5: without this the inspector wedges permanently.** A worker `error`
       * for an explanation left `pending` true for ever, so every later hover queued behind a
       * reply that was never coming, and leaving the map, resetting the criteria and further
       * successful computes all failed to recover it. The worker's error message carries no
       * request id, so this settles whatever was outstanding rather than correlating.
       */
      requestFailed() {
        if (!s.pending) return null;
        s.pending = false;
        // **Only a position the pointer has actually moved to.** Re-asking the inspected cell
        // here would retry the request that just failed, and a deterministic failure then loops:
        // error, retry, error, retry, with one message per round and no bound. Sending only a
        // QUEUED position bounds the retries by pointer moves, and the caller tells the viewer
        // the explanation failed so a move retries it.
        const next = s.queued;
        s.queued = null;
        return next ? sendNow(next.row, next.col) : null;
      },
    };
  }

  root.G3Card = { WHY_UNKNOWN, VERDICT_TEXT, ESTIMATE_NOTE, esc, cellForLonLat, minutesText,
    destinationText, renderCardHTML, createInspector };
})(typeof self !== 'undefined' ? self : globalThis);
