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
    const manifestRes = await fetch('fixtures/manifest.json', { cache: 'no-store' });
    if (!manifestRes.ok) throw new Error(`fixtures/manifest.json: HTTP ${manifestRes.status}`);
    const manifest = await manifestRes.json();
    if (!(manifest.nrows > 0 && manifest.ncols > 0 && Array.isArray(manifest.layers) && manifest.layers.length > 0)) {
      throw new Error('manifest.json missing nrows/ncols/layers');
    }

    const buffers = await Promise.all(
      manifest.layers.map(async (layer) => {
        const res = await fetch(`fixtures/${layer.file}`, { cache: 'no-store' });
        if (!res.ok) throw new Error(`fixtures/${layer.file}: HTTP ${res.status}`);
        return res.arrayBuffer();
      }),
    );

    const expected = manifest.nrows * manifest.ncols;
    buffers.forEach((buf, i) => {
      if (buf.byteLength !== expected) {
        throw new Error(`fixtures/${manifest.layers[i].file}: ${buf.byteLength} bytes, expected nrows*ncols=${expected}`);
      }
    });

    const t1 = performance.now();
    const decodedBytes = buffers.reduce((a, b) => a + b.byteLength, 0);

    // Resource Timing: actual bytes moved over the network (same-origin, so transferSize is
    // populated without needing a Timing-Allow-Origin header). 0 for a cached/opaque response.
    let transferredBytes = 0;
    try {
      const names = ['fixtures/manifest.json', ...manifest.layers.map((l) => `fixtures/${l.file}`)];
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

    return { manifest, buffers };
  }

  // ---- 3. worker ------------------------------------------------------------------------------

  function initWorker(manifest, buffers) {
    return new Promise((resolve, reject) => {
      const worker = new Worker('worker.js');
      state.worker = worker;

      worker.onerror = (ev) => {
        showError(`worker error: ${ev.message || ev}`);
        reject(new Error(ev.message || 'worker error'));
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
          case 'error':
            showError(`worker: ${msg.message}`);
            break;
          default:
            log(`worker: unknown message type ${msg.type}`);
        }
      };

      // buffers are listed both in the payload (so worker.js can read msg.buffers) and in the
      // transfer list (so their memory moves instead of being structured-clone copied).
      worker.postMessage({ type: 'init', manifest, buffers }, buffers);
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

  function defaultThreshold(mode) {
    return { walk: 20, bike: 15, drive: 10 }[mode] || 20;
  }

  function buildLayerRows(manifest) {
    el.layers.innerHTML = '';
    manifest.layers.forEach((layer, i) => {
      const row = document.createElement('div');
      row.className = 'layer';
      row.innerHTML = `
        <div class="layer-head">
          <input type="checkbox" id="en-${i}" checked>
          <label class="name" for="en-${i}">${layer.label}</label>
          <span class="val" id="val-${i}"></span>
        </div>
        <input type="range" id="th-${i}" min="1" max="60" step="1">
      `;
      el.layers.appendChild(row);

      const checkbox = row.querySelector(`#en-${i}`);
      const slider = row.querySelector(`#th-${i}`);
      const valSpan = row.querySelector(`#val-${i}`);
      slider.value = String(defaultThreshold(layer.mode));

      const sync = () => {
        valSpan.textContent = `<= ${slider.value} min`;
        row.classList.toggle('disabled', !checkbox.checked);
      };
      sync();

      checkbox.addEventListener('change', () => {
        sync();
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
    state.worker.postMessage({ type: 'compute', seq, thresholds, enabled, tEvent: tEventAbs });
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

    if (pending) {
      state.window.push({ totalMs, computeMs, transferMs });
      if (state.window.length > 20) state.window.shift();
    }

    renderStats({ computeMs, transferMs, totalMs });

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

  function waitForNextResult() {
    const before = state.window.length;
    return new Promise((resolve) => {
      const poll = () => {
        if (state.window.length > before) resolve();
        else setTimeout(poll, 5);
      };
      poll();
    });
  }

  async function autoBench() {
    el.btnBench.disabled = true;
    const n = state.manifest.layers.length;
    log('auto-bench: running 20 scripted slider changes (awaiting each repaint before the next)');
    for (let i = 0; i < 20; i++) {
      const layerIdx = i % n;
      const slider = $(`th-${layerIdx}`);
      const base = defaultThreshold(state.manifest.layers[layerIdx].mode);
      const next = 1 + ((base + i * 7) % 60); // deterministic pseudo-random walk, 1..60
      slider.value = String(next);
      $(`val-${layerIdx}`).textContent = `<= ${next} min`;
      recompute('auto-bench');
      await waitForNextResult();
    }
    log('auto-bench: done, 20 samples in the rolling window');
    el.btnBench.disabled = false;
  }

  function resetAll() {
    state.manifest.layers.forEach((layer, i) => {
      $(`th-${i}`).value = String(defaultThreshold(layer.mode));
      $(`en-${i}`).checked = true;
      $(`val-${i}`).textContent = `<= ${defaultThreshold(layer.mode)} min`;
      $(`th-${i}`).closest('.layer').classList.remove('disabled');
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
        initWorker(fixtures.manifest, fixtures.buffers),
      ]);

      addMaskSource(map);

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

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
