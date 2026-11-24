/* app.js — G3 render spike, main thread.
 *
 * Loads versions.json (CDN asset ledger) and fixtures/manifest.json + every fixtures/*.bin once,
 * ships the layers into worker.js, renders the AND/threshold mask it returns to a MapLibre
 * `canvas` source, and on demand polygonizes the mask with d3-contour via geom.js. All timings
 * are measured on this device; nothing here guesses at numbers.
 *
 * Cross-thread timing. performance.now() is relative to each execution context's OWN time
 * origin (a Window and its Worker do not share one), but performance.timeOrigin is itself
 * epoch-relative, so `performance.timeOrigin + performance.now()` is an absolute, wall-clock
 * timestamp comparable across threads on the same machine. worker.js already returns
 * tWorkerStartAbs/tWorkerEndAbs this way; nowAbs() below does the same on the main thread so
 * slider-to-repaint and transfer+paint can legitimately subtract a main-thread timestamp from a
 * worker-thread one.
 */
'use strict';

(function () {
  /** Where the published-v2 planes and manifest live. `fixtures/` still holds the v1 engine
   *  comparison fixtures, which are a different artifact for a different question. */
  const FIXTURES = 'fixtures/published';

  const $ = (id) => document.getElementById(id);
  const nowAbs = () => performance.timeOrigin + performance.now();
  const navStart = performance.now(); // ~0; kept for readability at call sites below

  const el = {
    versions: $('versions'),
    bannerSynthetic: $('banner-synthetic'),
    bannerError: $('banner-error'),
    map: $('map'),
    layers: $('layers'),
    btnPolygonize: $('btn-polygonize'),
    btnClear: $('btn-clear'),
    btnBench: $('btn-bench'),
    btnReset: $('btn-reset'),
    rowTotal: $('row-total'),
    stTotal: $('st-total'),
    stCompute: $('st-compute'),
    stTransfer: $('st-transfer'),
    stSamples: $('st-samples'),
    rowFirstPaint: $('row-firstpaint'),
    stFirstPaint: $('st-firstpaint'),
    stFixtures: $('st-fixtures'),
    stCdn: $('st-cdn'),
    stMapLoaded: $('st-maploaded'),
    stWorkerReady: $('st-workerready'),
    stCells: $('st-cells'),
    stNodata: $('st-nodata'),
    stMemory: $('st-memory'),
    plMask: $('pl-mask'),
    plContour: $('pl-contour'),
    plTransform: $('pl-transform'),
    plRender: $('pl-render'),
    plTotal: $('pl-total'),
    plTopology: $('pl-topology'),
    plArea: $('pl-area'),
    rowValid: $('row-valid'),
    plValid: $('pl-valid'),
    results: $('results'),
    log: $('log'),
    card: $('card'),
    cardCell: $('card-cell'),
    stExplain: $('st-explain'),
  };

  const PASS_SLIDER_MS = 100; // synthesis §6 gate G3
  const PASS_FIRSTPAINT_MS = 1500; // on throttled 4G specifically; see docs/experiments/g3-rendering.md

  function log(msg) {
    const t = (performance.now() / 1000).toFixed(3);
    el.log.textContent += `[+${t}s] ${msg}\n`;
    el.log.scrollTop = el.log.scrollHeight;
    // eslint-disable-next-line no-console
    console.log(`[g3 +${t}s] ${msg}`);
  }

  function showError(msg) {
    el.bannerError.hidden = false;
    el.bannerError.textContent = msg;
    log(`ERROR: ${msg}`);
  }

  function fmtMs(ms) {
    return `${ms.toFixed(1)} ms`;
  }
  function fmtBytes(n) {
    if (n >= 1e6) return `${(n / 1e6).toFixed(2)} MB`;
    if (n >= 1e3) return `${(n / 1e3).toFixed(1)} kB`;
    return `${n} B`;
  }
  function median(arr) {
    if (!arr.length) return NaN;
    const s = arr.slice().sort((a, b) => a - b);
    const mid = Math.floor(s.length / 2);
    return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
  }
  function setPassFail(rowEl, ok) {
    rowEl.classList.remove('pass', 'fail');
    rowEl.classList.add(ok ? 'pass' : 'fail');
  }

  // ---- app state -----------------------------------------------------------------------------

  const state = {
    versions: null,
    manifest: null,
    worker: null,
    workerReady: false,
    nrows: 0,
    ncols: 0,
    bounds: null, // [W, S, E, N]
    seq: 0,
    pending: new Map(), // seq -> {tEventAbs}
    window: [], // {totalMs, computeMs, transferMs} rolling, cap 20
    firstPaintDone: false,
    firstPaintMs: null,
    maskCanvas: null,
    maskCtx: null,
    canvasSource: null,
    map: null,
    paintChain: Promise.resolve(), // serializes drawMaskAndWaitForPaint calls; see handleWorkerResult
    maskReqSeq: 0,
    polygonAdded: false,
    lastMaskInCount: 0,
    lastNodataCount: 0,
    fixturesFetchMs: null,
    fixturesDecodedBytes: null,
    fixturesTransferredBytes: null,
    cdnBytes: null,
    mapLoadedMs: null,
    workerReadyMs: null,
    // The per-criterion card: one explainAt in flight, the newest pointer position behind it.
    explainSentAt: 0,
    explainMs: [],      // round trips, for the cost measurement the card plan asks for
    // Which computes have painted, and who is waiting for one. Keyed by sequence number, so a
    // waiter is released by the compute it actually asked about -- see waitForResult (pass 52 F8).
    paintedSeqs: new Set(),
    paintWaiters: new Map(),
    // The rest of the card's lifecycle -- which request is outstanding, which cell is being
    // inspected, which compute the screen shows, and whether the pointer has left since -- lives
    // in `G3Card.createInspector`, because both of pass 51's presentation findings were in that
    // logic and it could not be tested while it was spread through this file.
  };

  // ---- 1. versions.json: known pinned CDN byte totals -----------------------------------------

  async function loadVersions() {
    const res = await fetch('versions.json', { cache: 'no-store' });
    const v = await res.json();
    state.versions = v;
    let total = 0;
    for (const asset of Object.values(v.assets)) {
      if (asset.js && typeof asset.js.bytes === 'number') total += asset.js.bytes;
      if (asset.css && typeof asset.css.bytes === 'number') total += asset.css.bytes;
    }
    state.cdnBytes = total;
    el.stCdn.textContent = `${fmtBytes(total)} (pinned sizes recorded in versions.json, not re-measured over the network)`;
    return v;
  }

  // ---- 2. manifest.json + every fixtures/*.bin, once -------------------------------------------

  async function loadFixtures() {
    const t0 = performance.now();
    const manifestRes = await fetch(`${FIXTURES}/manifest.json`, { cache: 'no-store' });
    if (!manifestRes.ok) throw new Error(`${FIXTURES}/manifest.json: HTTP ${manifestRes.status}`);
    const manifest = await manifestRes.json();
    if (!(manifest.nrows > 0 && manifest.ncols > 0 && Array.isArray(manifest.layers) && manifest.layers.length > 0)) {
      throw new Error('manifest.json missing nrows/ncols/layers');
    }
    // The decoder refuses an encoding it does not know; say so here too, where the message can
    // name the file, rather than letting the worker's refusal arrive without a path.
    // Kept in step with `locfinder.wire.READABLE_ENCODINGS` by
    // tests/test_wire.py::test_the_javascript_encoding_lists_match_the_python_one.
    const READABLE = ['published-v2', 'published-v3', 'published-v4'];
    if (!READABLE.includes(manifest.encoding)) {
      throw new Error(`${FIXTURES}/manifest.json carries encoding "${manifest.encoding}"; this `
        + `page decodes ${READABLE.join(' or ')}. Run scripts/export_published_layers.py.`);
    }

    const fetchPlane = async (file) => {
      const res = await fetch(`${FIXTURES}/${file}`, { cache: 'no-store' });
      if (!res.ok) throw new Error(`${FIXTURES}/${file}: HTTP ${res.status}`);
      return res.arrayBuffer();
    };
    const values = await Promise.all(manifest.layers.map((l) => fetchPlane(l.value_file)));
    const statuses = await Promise.all(manifest.layers.map((l) => fetchPlane(l.status_file)));
    // Optional: a layer discloses its restricted routes only if it says so.
    const routeFlags = await Promise.all(manifest.layers.map(
      (l) => (l.flag_file ? fetchPlane(l.flag_file) : Promise.resolve(null))));
    // Optional: a layer says WHICH destination only if it says so. The side table comes with the
    // plane -- ordinals with no table to resolve them name nothing a reader can use.
    const destinations = await Promise.all(manifest.layers.map(
      (l) => (l.dest_file ? fetchPlane(l.dest_file) : Promise.resolve(null))));
    const destTables = await Promise.all(manifest.layers.map(
      (l) => (l.dest_table
        ? fetch(`${FIXTURES}/${l.dest_table}`, { cache: 'no-store' }).then((r) => {
          if (!r.ok) throw new Error(`${FIXTURES}/${l.dest_table}: HTTP ${r.status}`);
          return r.json();
        })
        : Promise.resolve(null))));

    const expected = manifest.nrows * manifest.ncols;
    // Pass 48: the flag plane was not length-checked here, so a short one reached the worker and
    // failed there with a message about a plane the page had already accepted. A null slot is
    // legal and means the layer declares no plane.
    [[values, 'value'], [statuses, 'status'], [routeFlags, 'flag']].forEach(([bufs, what]) => {
      bufs.forEach((buf, i) => {
        if (buf === null) return;
        if (buf.byteLength !== expected) {
          throw new Error(`${FIXTURES}/${manifest.layers[i][`${what}_file`]}: ${buf.byteLength} bytes, expected nrows*ncols=${expected}`);
        }
      });
    });
    // The destination plane is uint16, so TWO bytes per cell. Checking it against `expected`
    // would pass a plane half the size it should be.
    destinations.forEach((buf, i) => {
      if (buf === null) return;
      if (buf.byteLength !== expected * 2) {
        throw new Error(`${FIXTURES}/${manifest.layers[i].dest_file}: ${buf.byteLength} bytes, expected nrows*ncols*2=${expected * 2}`);
      }
    });

    const t1 = performance.now();
    // Pass 48: this summed value and status only, so the page reported 661,004 bytes for a
    // 991,506-byte payload -- understating the cost of the format change it exists to measure.
    const buffers = values.concat(statuses)
      .concat(routeFlags.filter((b) => b !== null))
      .concat(destinations.filter((b) => b !== null));
    const decodedBytes = buffers.reduce((a, b) => a + b.byteLength, 0);

    // Resource Timing: actual bytes moved over the network (same-origin, so transferSize is
    // populated without needing a Timing-Allow-Origin header). 0 for a cached/opaque response.
    let transferredBytes = 0;
    try {
      const names = [`${FIXTURES}/manifest.json`,
        ...manifest.layers.flatMap((l) => [`${FIXTURES}/${l.value_file}`,
          `${FIXTURES}/${l.status_file}`,
          ...(l.flag_file ? [`${FIXTURES}/${l.flag_file}`] : []),
          ...(l.dest_file ? [`${FIXTURES}/${l.dest_file}`] : []),
          ...(l.dest_table ? [`${FIXTURES}/${l.dest_table}`] : [])])];
      const entries = performance.getEntriesByType('resource');
      for (const name of names) {
        const entry = entries.find((e) => e.name.endsWith(name));
        if (entry) transferredBytes += entry.transferSize || 0;
      }
    } catch (err) {
      log(`resource timing unavailable: ${err.message}`);
    }

    state.manifest = manifest;
    state.nrows = manifest.nrows;
    state.ncols = manifest.ncols;
    state.bounds = manifest.bounds_wgs84;
    state.fixturesFetchMs = t1 - t0;
    state.fixturesDecodedBytes = decodedBytes;
    state.fixturesTransferredBytes = transferredBytes;

    el.stFixtures.textContent =
      `${fmtMs(state.fixturesFetchMs)} / ${fmtBytes(decodedBytes)} decoded / ` +
      `${transferredBytes ? fmtBytes(transferredBytes) : 'n/a (cached or no Resource Timing entry)'}`;

    if (manifest.synthetic) {
      el.bannerSynthetic.hidden = false;
      el.bannerSynthetic.textContent =
        `SYNTHETIC FIXTURES (${manifest.source || 'synthetic'}): these layers are random distance fields ` +
        'from make_fixtures.py, not routing output. Numbers measure rendering cost only.';
    } else {
      el.bannerSynthetic.hidden = true;
    }

    log(
      `fixtures loaded: ${manifest.layers.length} layer(s), ${manifest.nrows}x${manifest.ncols}, ` +
      `source="${manifest.source || 'unknown'}"`,
    );

    return { manifest, values, statuses, routeFlags, destinations, destTables };
  }

  // ---- 3. worker ------------------------------------------------------------------------------

  function initWorker(manifest, values, statuses, routeFlags, destinations, destTables) {
    return new Promise((resolve, reject) => {
      const worker = new Worker('worker.js');
      state.worker = worker;

      worker.onerror = (ev) => {
        showError(`worker error: ${ev.message || ev}`);
        // **Pass 53 F9.** This rejected a promise that had already resolved -- a no-op after
        // init -- and left any outstanding explanation request outstanding for ever, so every
        // later hover queued behind a reply that was never coming. A native error and a protocol
        // `error` message are different events that leave the same state, so both settle it.
        if (state.workerReady) {
          post(cardFailed());
        } else {
          reject(new Error(ev.message || 'worker error'));
        }
      };

      worker.onmessage = (ev) => {
        const msg = ev.data || {};
        switch (msg.type) {
          case 'ready':
            state.workerReady = true;
            state.workerReadyMs = performance.now();
            el.stWorkerReady.textContent = `${fmtMs(state.workerReadyMs)} since load (worker initMs ${fmtMs(msg.initMs)})`;
            log(`worker ready: ${msg.layerCount} layers, ${msg.bytes} bytes, initMs=${msg.initMs.toFixed(2)}`);
            resolve();
            break;
          case 'result':
            handleWorkerResult(msg);
            break;
          case 'mask':
            handleWorkerMask(msg);
            break;
          case 'explainAt':
            handleExplainAt(msg);
            break;
          case 'error':
            // Pass 48 F2: this showed the message and left `initWorker`'s promise PENDING, so a
            // refusal during init hung the page instead of failing it. A protocol error before
            // ready is a failed start; after ready it is one bad message.
            showError(`worker: ${msg.message}`);
            if (!state.workerReady) reject(new Error(msg.message || 'worker refused the bundle'));
            // Pass 52 F5: an error for an explanation left the inspector's request outstanding
            // for ever, so every later hover queued behind a reply that was never coming and
            // nothing recovered it -- not leaving the map, not resetting, not a later compute.
            // The worker's error carries no request id, so whatever was outstanding is settled.
            if (state.workerReady) post(cardFailed());
            break;
          default:
            log(`worker: unknown message type ${msg.type}`);
        }
      };

      // Each plane is listed in the payload (so worker.js can read it) and in the transfer list
      // (so its memory moves instead of being structured-clone copied).
      const flagBuffers = routeFlags.filter((b) => b);
      const destBuffers = (destinations || []).filter((b) => b);
      worker.postMessage(
        { type: 'init', manifest, values, statuses, routeFlags, destinations, destTables },
        values.concat(statuses).concat(flagBuffers).concat(destBuffers));
    });
  }

  const maskRequestResolvers = new Map();
  function requestMask() {
    const reqId = ++state.maskReqSeq;
    return new Promise((resolve) => {
      maskRequestResolvers.set(reqId, resolve);
      state.worker.postMessage({ type: 'mask', reqId });
    });
  }
  function handleWorkerMask(msg) {
    const resolve = maskRequestResolvers.get(msg.reqId);
    if (resolve) {
      maskRequestResolvers.delete(msg.reqId);
      resolve(msg);
    }
  }

  // ---- 3b. the per-criterion card -------------------------------------------------------------
  //
  // The three disclosures `docs/s3-decision-report.md` names are all answers about ONE cell, so
  // they are one surface fed by one message. `compute` cannot supply them: it folds the per-layer
  // outcomes into a single verdict and discards them, which is why `explainAt` exists.
  //
  // The TEXT lives in card.js, with no DOM, because the words are where a disclosure gets lost --
  // "no restrictions" for a layer that does not disclose, a bare number for a lower bound, a shop
  // the pipeline never chose. card_selftest.mjs checks those in Node. What is left here is the
  // plumbing: which cell the pointer is over, one request in flight, and where the HTML lands.

  /** One request in flight at a time, with the latest pointer position coalesced behind it.
   *
   * A pointer can move far faster than a round trip, and queueing every move would build an
   * unbounded backlog that renders cells the pointer has already left. So: send one, remember the
   * newest position, send that when the reply lands.
   */
  // Which replies may reach the screen is decided by `G3Card.createInspector`, a state machine
  // with no DOM: both of pass 51's presentation findings were in this logic and it was not
  // testable here. `card_selftest.mjs` drives it. This file supplies the messages and the DOM.
  const inspector = window.G3Card.createInspector();

  function post(req) {
    if (!req) return;
    state.explainSentAt = performance.now();
    state.worker.postMessage({ type: 'explainAt', ...req });
  }

  function explainAt(row, col) {
    if (!state.workerReady) return;
    post(inspector.pointerAt(row, col));
  }

  function handleExplainAt(msg) {
    const { render, send } = inspector.reply(msg);
    if (render) {
      const ms = performance.now() - state.explainSentAt;
      state.explainMs.push(ms);
      if (state.explainMs.length > 50) state.explainMs.shift();
      // One round trip per pointer move is not free, so the page reports what it actually costs
      // on this device rather than leaving it to be assumed either way. The worker-side handler
      // is about 0.2 microseconds on the shipped bundle (bench_explain.mjs); everything else in
      // this number is the message. It stops before `renderCard`, so it excludes the DOM update.
      const sorted = state.explainMs.slice().sort((a, b) => a - b);
      el.stExplain.textContent =
        `${fmtMs(ms)} / ${fmtMs(sorted[Math.floor(sorted.length / 2)])} (n=${sorted.length})`;
      renderCard(msg);
    }
    post(send);
  }

  function renderCard(msg) {
    el.cardCell.textContent = (!msg.outside && Number.isInteger(msg.row))
      ? `(row ${msg.row}, col ${msg.col})` : '';
    el.card.innerHTML = window.G3Card.renderCardHTML(msg);
  }

  /** The pointer has left the data, so nothing in flight is about anywhere the page is showing. */
  function clearCard(text) {
    inspector.pointerLeft();
    el.cardCell.textContent = '';
    el.card.innerHTML = text;
  }

  /** The criteria changed, so whatever the card says is about the previous ones.
   *
   * Pass 51 B1: nothing invalidated the card, so a cell shown as PASS at a 15-minute limit kept
   * saying PASS, with "your limit 15 min", indefinitely after the limit moved to 5 and the raster
   * excluded it. The card is emptied on the way in and refilled when the new raster has painted.
   */
  function cardAwaitingCompute() {
    el.card.innerHTML = '<em>Recomputing…</em>';
  }

  /** An explanation request failed. Settle it, say so, and let the next one through. */
  function cardFailed() {
    const next = inspector.requestFailed();
    if (!next && inspector.state.inspected) {
      el.card.innerHTML = '<em>That explanation could not be produced. Move the pointer to try '
        + 'again.</em>';
    }
    return next;
  }

  function wireCardPointer(map) {
    map.on('mousemove', (e) => {
      const at = window.G3Card.cellForLonLat(state.bounds, state.ncols, state.nrows,
        e.lngLat.lng, e.lngLat.lat);
      if (!at) {
        clearCard(window.G3Card.renderCardHTML({ outside: true }));
        return;
      }
      // **The card stops describing the old cell the moment the pointer leaves it** -- pass 53
      // F8. The inspector's guard stops a stale REPLY rendering; it cannot unrender what is
      // already on screen, so a PASS card and its `(row 1, col 1)` label stayed visible over a
      // different cell until the next accepted reply arrived.
      const was = inspector.state.inspected;
      if (!was || was.row !== at.row || was.col !== at.col) {
        el.cardCell.textContent = `(row ${at.row}, col ${at.col})`;
        el.card.innerHTML = '<em>Reading this spot…</em>';
      }
      explainAt(at.row, at.col);
    });
    map.on('mouseout', () => clearCard('<em>Move the pointer over the map.</em>'));
  }

  // ---- 4. MapLibre map + canvas source ----------------------------------------------------------

  function initMap(versions) {
    return new Promise((resolve, reject) => {
      const basemap = versions.basemap;
      const map = new maplibregl.Map({
        container: 'map',
        style: {
          version: 8,
          sources: {
            osm: {
              type: 'raster',
              tiles: [basemap.tiles],
              tileSize: 256,
              attribution: basemap.attribution,
            },
          },
          layers: [{ id: 'osm', type: 'raster', source: 'osm' }],
        },
        bounds: [
          [state.bounds[0], state.bounds[1]],
          [state.bounds[2], state.bounds[3]],
        ],
        fitBoundsOptions: { padding: 16 },
        attributionControl: true,
      });
      map.on('error', (e) => showError(`map error: ${e && e.error ? e.error.message : e}`));
      map.on('load', () => {
        state.mapLoadedMs = performance.now();
        el.stMapLoaded.textContent = `${fmtMs(state.mapLoadedMs)} since load`;
        log('map style loaded');
        resolve(map);
      });
      state.map = map;
    });
  }

  /**
   * Add the canvas source. `animate:false` so MapLibre does not run a continuous
   * requestAnimationFrame-driven re-upload loop (CanvasSource with animate:true calls play() on
   * add and keeps calling map.triggerRepaint() every frame forever -- verified against
   * maplibre-gl-js v5.24.0 src/source/canvas_source.ts). Instead, after every redraw we call
   * play() immediately followed by pause(): play() sets _playing=true and calls
   * triggerRepaint() once; pause() synchronously calls prepare() (which re-uploads the canvas
   * pixels to the GPU texture because _playing is still true at that point) and only then sets
   * _playing=false. So play()+pause() back-to-back forces exactly one synchronous texture
   * upload plus exactly one scheduled repaint, with no ongoing animation loop afterwards.
   */
  function addMaskSource(map) {
    const canvas = document.createElement('canvas');
    canvas.width = state.ncols;
    canvas.height = state.nrows;
    state.maskCanvas = canvas;
    state.maskCtx = canvas.getContext('2d', { willReadFrequently: false });
    // Four corners in [lon, lat] order, matching geom.js's documented transform exactly:
    // top-left (W,N), top-right (E,N), bottom-right (E,S), bottom-left (W,S).
    const [W, S, E, N] = state.bounds;
    map.addSource('mask', {
      type: 'canvas',
      canvas,
      animate: false,
      coordinates: [[W, N], [E, N], [E, S], [W, S]],
    });
    map.addLayer({
      id: 'mask-layer',
      type: 'raster',
      source: 'mask',
      paint: { 'raster-fade-duration': 0, 'raster-resampling': 'nearest' },
    });
    state.canvasSource = map.getSource('mask');
  }

  function drawMaskAndWaitForPaint(rgbaBuffer) {
    return new Promise((resolve) => {
      const imageData = new ImageData(new Uint8ClampedArray(rgbaBuffer), state.ncols, state.nrows);
      state.maskCtx.putImageData(imageData, 0, 0);
      state.map.once('render', () => resolve(performance.now()));
      state.canvasSource.play();
      state.canvasSource.pause();
    });
  }

  // ---- 5. layer rows (checkbox + threshold slider) ----------------------------------------------

  function buildLayerRows(manifest) {
    el.layers.innerHTML = '';
    //: Every row's own display refresh. Collected because choosing one scope changes ANOTHER
    //: row's checkbox, and that row's label has to follow.
    const syncs = [];
    manifest.layers.forEach((layer, i) => {
      const row = document.createElement('div');
      row.className = 'layer';
      // Both rules live in card.js so Node can test them: pass 51's two presentation findings
      // were both in logic that sat here, where nothing could reach it.
      const startsOn = window.G3Card.layerOpensOn(layer);
      row.innerHTML = `
        <div class="layer-head">
          <input type="checkbox" id="en-${i}"${startsOn ? ' checked' : ''}>
          <label class="name" for="en-${i}">${layer.label}</label>
          <span class="val" id="val-${i}"></span>
        </div>
        <input type="range" id="th-${i}" min="1" max="60" step="1">
      `;
      el.layers.appendChild(row);

      const checkbox = row.querySelector(`#en-${i}`);
      const slider = row.querySelector(`#th-${i}`);
      const valSpan = row.querySelector(`#val-${i}`);
      slider.value = String(window.G3Card.layerOpeningThreshold(layer));

      const sync = () => {
        valSpan.textContent = `<= ${slider.value} min`;
        row.classList.toggle('disabled', !checkbox.checked);
      };
      syncs.push(sync);
      sync();

      checkbox.addEventListener('change', () => {
        // Alternative SCOPES of the same question cannot both be on, because the worker
        // intersects enabled criteria -- see `enabledAfterToggle`. The rule lives in card.js so
        // Node can test it; this only applies its answer to the boxes.
        const next = window.G3Card.enabledAfterToggle(
          manifest.layers, i, checkbox.checked, currentThresholdsEnabled().enabled);
        manifest.layers.forEach((_layer, j) => { $(`en-${j}`).checked = next[j]; });
        // Assigning `.checked` fires no `change` event, so this cannot recurse.
        syncs.forEach((f) => f());
        recompute('checkbox');
      });
      slider.addEventListener('input', () => {
        sync();
        recompute('slider');
      });
    });
  }

  function currentThresholdsEnabled() {
    const n = state.manifest.layers.length;
    const thresholds = new Array(n);
    const enabled = new Array(n);
    for (let i = 0; i < n; i++) {
      thresholds[i] = parseInt($(`th-${i}`).value, 10);
      enabled[i] = $(`en-${i}`).checked;
    }
    return { thresholds, enabled };
  }

  // ---- 6. compute round-trip + rolling stats --------------------------------------------------

  function recompute(source) {
    if (!state.workerReady) return;
    const tEventAbs = nowAbs();
    const seq = ++state.seq;
    const { thresholds, enabled } = currentThresholdsEnabled();
    state.pending.set(seq, { tEventAbs, source });
    // The raster on screen is about to stop describing the current criteria, so the card must
    // stop claiming to as well (pass 51 B1).
    inspector.computeStarted();
    if (inspector.state.inspected) cardAwaitingCompute();
    state.worker.postMessage({ type: 'compute', seq, thresholds, enabled, tEvent: tEventAbs });
    return seq;
  }

  async function handleWorkerResult(msg) {
    const pending = state.pending.get(msg.seq);
    state.pending.delete(msg.seq);
    const tReceiveAbs = nowAbs();

    // Serialize draws: if slider 'input' events fire faster than a compute+paint round trip,
    // multiple 'result' messages can be in flight at once. Chaining off state.paintChain makes
    // each drawMaskAndWaitForPaint() wait for the previous one to finish, so two putImageData /
    // play()+pause() cycles never interleave (and the once('render') each registers always
    // corresponds to its own draw). The .catch keeps the chain alive even if one draw throws.
    const myTurn = state.paintChain.then(() => drawMaskAndWaitForPaint(msg.rgba));
    state.paintChain = myTurn.catch(() => {});
    const tPaintDoneMs = await myTurn;
    const tPaintDoneAbs = performance.timeOrigin + tPaintDoneMs;

    // Recycle the RGBA ArrayBuffer so the worker can reuse it instead of allocating 220k*4 bytes
    // again next time. This is safe here because: (a) the ImageData(view, w, h) constructor holds
    // a direct reference to the Uint8ClampedArray view, it does not copy at construction time, but
    // (b) ctx.putImageData() is itself synchronous and has already copied those pixel bytes into
    // the canvas's bitmap before it returns -- and drawMaskAndWaitForPaint has resolved (we just
    // awaited it), so putImageData returned well before this line runs. Transferring msg.rgba's
    // memory back to the worker now cannot affect anything already painted.
    state.worker.postMessage({ type: 'recycle', buffer: msg.rgba }, [msg.rgba]);

    const computeMs = msg.computeMs;
    const transferMs = tPaintDoneAbs - tReceiveAbs;
    const totalMs = pending ? tPaintDoneAbs - pending.tEventAbs : NaN;

    state.lastMaskInCount = msg.inCount;
    state.lastNodataCount = msg.nodataCount;
    // Three outcomes, counted separately. `nodataCount` is now UNKNOWN -- cells nothing in the
    // published data settles -- and is no longer the same thing as "excluded", which v1 could not
    // distinguish.
    state.lastExcludedCount = msg.excludedCount;
    // null means no enabled layer discloses, which the UI must not render as "none".
    state.lastRestrictedIncludedCount = msg.restrictedIncludedCount;

    if (pending) {
      state.window.push({ totalMs, computeMs, transferMs });
      if (state.window.length > 20) state.window.shift();
    }

    renderStats({ computeMs, transferMs, totalMs });

    // The raster on screen is now this compute's, so a card built from it is current, and the
    // inspected cell is re-asked. Only the newest compute may claim the screen: with several
    // results in flight an older one must not mark itself displayed after a newer one painted.
    post(inspector.computePainted(msg.seq, state.seq));

    // Record the paint and release anyone waiting for this specific compute. Bounded: only the
    // most recent sequence numbers are kept, which is all a waiter can ask about.
    state.paintedSeqs.add(msg.seq);
    if (state.paintedSeqs.size > 64) {
      for (const old of [...state.paintedSeqs].slice(0, state.paintedSeqs.size - 64)) {
        state.paintedSeqs.delete(old);
      }
    }
    const waiters = state.paintWaiters.get(msg.seq);
    if (waiters) {
      state.paintWaiters.delete(msg.seq);
      for (const w of waiters) w.resolve();
    }

    if (!state.firstPaintDone) {
      state.firstPaintDone = true;
      state.firstPaintMs = tPaintDoneMs; // elapsed since navigation, main-thread clock
      el.stFirstPaint.textContent = `${fmtMs(state.firstPaintMs)} since navigation start`;
      setPassFail(el.rowFirstPaint, state.firstPaintMs < PASS_FIRSTPAINT_MS);
      log(`first mask paint at ${state.firstPaintMs.toFixed(1)} ms since navigation start`);
      el.btnPolygonize.disabled = false;
      el.btnBench.disabled = false;
      el.btnReset.disabled = false;
    }
  }

  function renderStats({ computeMs, transferMs, totalMs }) {
    const totals = state.window.map((w) => w.totalMs);
    const computes = state.window.map((w) => w.computeMs);
    const transfers = state.window.map((w) => w.transferMs);
    const medTotal = median(totals);
    el.stTotal.textContent = `${totalMs.toFixed(1)} / ${medTotal.toFixed(1)} ms`;
    el.stCompute.textContent = `${computeMs.toFixed(1)} / ${median(computes).toFixed(1)} ms`;
    el.stTransfer.textContent = `${transferMs.toFixed(1)} / ${median(transfers).toFixed(1)} ms`;
    el.stSamples.textContent = `${state.window.length} / 20`;
    if (state.window.length >= 5) setPassFail(el.rowTotal, medTotal < PASS_SLIDER_MS);

    const cellKm2 = window.G3Geom.cellAreaKm2(state.bounds, state.ncols, state.nrows);
    el.stCells.textContent = `${state.lastMaskInCount.toLocaleString()} cells / ${(state.lastMaskInCount * cellKm2).toFixed(1)} km^2`;
    el.stNodata.textContent = state.lastNodataCount.toLocaleString();

    if (performance.memory) {
      const m = performance.memory;
      el.stMemory.textContent = `${(m.usedJSHeapSize / 1e6).toFixed(1)} / ${(m.totalJSHeapSize / 1e6).toFixed(1)} MB (used/total)`;
    } else {
      el.stMemory.textContent = 'not exposed by this browser (Chrome-only API)';
    }

    writeResultsRow();
  }

  function writeResultsRow() {
    const totals = state.window.map((w) => w.totalMs);
    const computes = state.window.map((w) => w.computeMs);
    const transfers = state.window.map((w) => w.transferMs);
    const mem = performance.memory ? `${(performance.memory.usedJSHeapSize / 1e6).toFixed(1)} MB` : 'n/a';
    const row =
      `| <environment> | ${median(computes).toFixed(1)} | ${median(transfers).toFixed(1)} | ` +
      `${median(totals).toFixed(1)} | ${state.firstPaintMs == null ? '-' : state.firstPaintMs.toFixed(1)} | ${mem} | ` +
      `${el.plTotal.textContent === '–' ? '-' : el.plTotal.textContent} | ${el.plTopology.textContent === '–' ? '-' : el.plTopology.textContent} | ` +
      `${el.plValid.textContent === '–' ? '-' : el.plValid.textContent} |`;
    el.results.value = row;
  }

  // ---- 7. polygonize ----------------------------------------------------------------------------

  async function polygonize() {
    el.btnPolygonize.disabled = true;
    const tButton = performance.now();
    try {
      const tMaskStart = performance.now();
      const maskMsg = await requestMask();
      const mask = new Uint8Array(maskMsg.mask);
      const tMaskEnd = performance.now();
      el.plMask.textContent = fmtMs(tMaskEnd - tMaskStart);

      // d3-contour grid space: values[x + y*width], width=ncols, height=nrows, matching our
      // row-major row-0-is-north layout exactly (see geom.js header comment).
      const tContourStart = performance.now();
      const contourGen = d3.contours().size([state.ncols, state.nrows]).thresholds([0.5]);
      const [contour] = contourGen(mask);
      const tContourEnd = performance.now();
      el.plContour.textContent = fmtMs(tContourEnd - tContourStart);

      const { feature, stats } = window.G3Geom.contourToGeoJSON(contour.coordinates, state.bounds, state.ncols, state.nrows);
      const validity = window.G3Geom.validate(feature, state.bounds);
      const tTransformEnd = performance.now();
      el.plTransform.textContent = fmtMs(tTransformEnd - tContourEnd);

      const tRenderStart = performance.now();
      await addOrUpdatePolygonLayer(feature);
      const tRenderEnd = performance.now();
      el.plRender.textContent = fmtMs(tRenderEnd - tRenderStart);

      const tTotal = performance.now() - tButton;
      el.plTotal.textContent = fmtMs(tTotal);
      el.plTopology.textContent = `${stats.polygons} / ${stats.holes} / ${stats.vertices}`;

      const cellKm2 = window.G3Geom.cellAreaKm2(state.bounds, state.ncols, state.nrows);
      const rasterKm2 = maskMsg.inCount * cellKm2;
      el.plArea.textContent = `${validity.netAreaKm2.toFixed(2)} / ${rasterKm2.toFixed(2)} km^2`;

      el.plValid.textContent = validity.ok ? 'OK (closed, >=4 vertices, in-bounds, exterior CCW, holes CW)' : `FAIL: ${validity.problems.join('; ')}`;
      setPassFail(el.rowValid, validity.ok);

      log(
        `polygonize: ${stats.polygons} polygon(s), ${stats.holes} hole(s), ${stats.vertices} vertices, ` +
        `valid=${validity.ok}, total=${tTotal.toFixed(1)}ms`,
      );

      writeResultsRow();
      el.btnClear.disabled = false;
    } catch (err) {
      showError(`polygonize failed: ${err && err.message ? err.message : err}`);
    } finally {
      el.btnPolygonize.disabled = false;
    }
  }

  function addOrUpdatePolygonLayer(feature) {
    return new Promise((resolve) => {
      const map = state.map;
      if (map.getSource('polygon')) {
        map.getSource('polygon').setData(feature);
      } else {
        map.addSource('polygon', { type: 'geojson', data: feature });
        map.addLayer({
          id: 'polygon-fill',
          type: 'fill',
          source: 'polygon',
          paint: { 'fill-color': '#ff7f0e', 'fill-opacity': 0.25 },
        });
        map.addLayer({
          id: 'polygon-line',
          type: 'line',
          source: 'polygon',
          paint: { 'line-color': '#d62728', 'line-width': 2 },
        });
      }
      state.polygonAdded = true;
      map.once('render', () => resolve());
      map.triggerRepaint();
    });
  }

  function clearPolygon() {
    const map = state.map;
    if (map.getLayer('polygon-fill')) map.removeLayer('polygon-fill');
    if (map.getLayer('polygon-line')) map.removeLayer('polygon-line');
    if (map.getSource('polygon')) map.removeSource('polygon');
    state.polygonAdded = false;
    el.btnClear.disabled = true;
    el.plMask.textContent = '–';
    el.plContour.textContent = '–';
    el.plTransform.textContent = '–';
    el.plRender.textContent = '–';
    el.plTotal.textContent = '–';
    el.plTopology.textContent = '–';
    el.plArea.textContent = '–';
    el.plValid.textContent = '–';
    el.rowValid.classList.remove('pass', 'fail');
    log('polygon cleared');
  }

  // ---- 8. auto-bench: 20 deterministic slider changes, awaited one at a time -------------------

  /** Resolve when the compute with this sequence number has painted.
   *
   * **Pass 52 finding F8**, which predates the card. This used to wait for the rolling timing
   * window to GROW — and the window is capped at 20, so once it was full `length > before` could
   * never become true: `autoBench` hung on its first change and left its button disabled for the
   * rest of the session. Even a fresh page reached that state, because the bench itself fills the
   * window. A `resetAll` during the wait could invalidate the captured length too.
   *
   * Waiting for the specific compute is both correct and immune to both: the thing being waited
   * for is the thing that was started. The timeout exists so a compute that never paints reports
   * and releases rather than hanging the caller for ever.
   */
  function waitForResult(seq, { timeoutMs = 10000 } = {}) {
    if (state.paintedSeqs.has(seq)) return Promise.resolve(true);
    return new Promise((resolve) => {
      // **A LIST of waiters per sequence** -- pass 53 F10. The map held one callback per
      // sequence, so a second waiter for the same compute overwrote the first: the first then
      // timed out although its compute had painted, and its timer deleted the second's entry.
      // One waiter per sequence is all `autoBench` needs, which is why it never showed.
      const waiters = state.paintWaiters.get(seq) || [];
      const entry = {};
      entry.timer = setTimeout(() => {
        const list = state.paintWaiters.get(seq) || [];
        const left = list.filter((w) => w !== entry);
        if (left.length) state.paintWaiters.set(seq, left);
        else state.paintWaiters.delete(seq);
        log(`compute ${seq} did not paint within ${timeoutMs} ms`);
        resolve(false);
      }, timeoutMs);
      entry.resolve = () => {
        clearTimeout(entry.timer);
        resolve(true);
      };
      waiters.push(entry);
      state.paintWaiters.set(seq, waiters);
    });
  }

  async function autoBench() {
    el.btnBench.disabled = true;
    const n = state.manifest.layers.length;
    log('auto-bench: running 20 scripted slider changes (awaiting each repaint before the next)');
    let done = 0;
    for (let i = 0; i < 20; i++) {
      const layerIdx = i % n;
      const slider = $(`th-${layerIdx}`);
      const base = window.G3Card.layerOpeningThreshold(state.manifest.layers[layerIdx]);
      const next = 1 + ((base + i * 7) % 60); // deterministic pseudo-random walk, 1..60
      slider.value = String(next);
      $(`val-${layerIdx}`).textContent = `<= ${next} min`;
      const seq = recompute('auto-bench');
      if (seq === undefined) {
        log('auto-bench: the worker is not ready, stopping');
        break;
      }
      if (!await waitForResult(seq)) {
        log(`auto-bench: stopping at change ${i + 1}, compute ${seq} never painted`);
        break;
      }
      done++;
    }
    // The COMPLETED count, not the intended one. Pass 53 F10: it printed "done, 20 samples"
    // after stopping at change one with nothing measured.
    log(`auto-bench: finished ${done} of 20 scripted changes`);
    el.btnBench.disabled = false;
  }

  function resetAll() {
    // The OPENING state, not "everything on". Those were the same thing while the bundle held
    // one criterion; with seven, "everything on" is the intersection of all of them and reset
    // hands a household the blank map that `layerOpensOn` exists to prevent. The opening view
    // was fixed first and this was still wrong, one button press away.
    state.manifest.layers.forEach((layer, i) => {
      const min = window.G3Card.layerOpeningThreshold(layer);
      const on = window.G3Card.layerOpensOn(layer);
      $(`th-${i}`).value = String(min);
      $(`en-${i}`).checked = on;
      $(`val-${i}`).textContent = `<= ${min} min`;
      $(`th-${i}`).closest('.layer').classList.toggle('disabled', !on);
    });
    state.window = [];
    recompute('reset');
    log('reset to defaults; stats window cleared');
  }

  // ---- boot ---------------------------------------------------------------------------------

  async function boot() {
    try {
      log('boot: fetching versions.json + fixtures in parallel');
      const [versions, fixtures] = await Promise.all([loadVersions(), loadFixtures()]);

      buildLayerRows(fixtures.manifest);

      const [map] = await Promise.all([
        initMap(versions),
        initWorker(fixtures.manifest, fixtures.values, fixtures.statuses,
          fixtures.routeFlags, fixtures.destinations, fixtures.destTables),
      ]);

      addMaskSource(map);
      wireCardPointer(map);

      el.btnPolygonize.addEventListener('click', polygonize);
      el.btnClear.addEventListener('click', clearPolygon);
      el.btnBench.addEventListener('click', autoBench);
      el.btnReset.addEventListener('click', resetAll);

      recompute('initial');
      log('boot complete; ready for input');
    } catch (err) {
      showError(err && err.message ? err.message : String(err));
      // eslint-disable-next-line no-console
      console.error(err);
    }
  }

  /** **A read-only window for the placement probe** -- queue item 3.
   *
   * The page draws the published raster as a MapLibre `canvas` source, placed by its four
   * corners in Web Mercator, while the raster's own rows are linear in latitude. Those two
   * rules disagree by up to 0.37 of a row, so the pixel under the pointer and the cell the
   * card names can be different cells. Measuring that needs the live map's own projection
   * and the canvas the page actually painted, and `state` is private to this file.
   *
   * **Everything here reads.** Nothing exposed can set a threshold, enable a layer, move the
   * map or render a card, so the probe cannot become a second way of driving the page. The
   * oracle it is compared against is `docs/experiments/s3-10-drawn-pixel.json`, written
   * before any browser ran; the runner is `probe_placement.js` beside this file.
   */
  window.G3Probe = Object.freeze({
    ready: () => Boolean(state.map && state.maskCtx && state.ncols),
    grid: () => ({ nrows: state.nrows, ncols: state.ncols, bounds: state.bounds.slice() }),
    project: (lon, lat) => {
      const p = state.map.project([lon, lat]);
      return { x: p.x, y: p.y };
    },
    unproject: (x, y) => {
      const c = state.map.unproject([x, y]);
      return { lon: c.lng, lat: c.lat };
    },
    /** The RGBA the page painted for one published cell: the input MapLibre samples. */
    maskPixel: (col, row) => Array.from(state.maskCtx.getImageData(col, row, 1, 1).data),
    /** The linear-in-screen interpolation below holds for a north-up, untilted map only. */
    bearingPitch: () => ({ bearing: state.map.getBearing(), pitch: state.map.getPitch() }),
    canvasRect: () => {
      const r = state.map.getCanvas().getBoundingClientRect();
      return { left: r.left, top: r.top, width: r.width, height: r.height };
    },
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
