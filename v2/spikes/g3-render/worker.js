/* worker.js — G3 raster-algebra Web Worker (classic worker, no imports, no build step).
 *
 * Holds the six uint8 minute layers and, per request, computes
 *     mask[p] = AND over enabled layers k of (layer_k[p] <= threshold_k)
 * where the nodata value (manifest.nodata, 255) always FAILS, and separately counts cells
 * that are nodata in ANY enabled layer. It writes an RGBA buffer (in-region colour,
 * out-of-region transparent, nodata diagonally hatched) and transfers it to the main thread.
 *
 * Protocol (main -> worker):
 *   {type:'init', manifest, buffers:[ArrayBuffer x N]}          buffers are transferred
 *   {type:'compute', seq, thresholds:[N ints], enabled:[N bools], tEvent}
 *   {type:'recycle', buffer}                                     returns an RGBA buffer to the pool
 *   {type:'mask', reqId}                                         asks for a copy of the current 0/1 mask
 * Protocol (worker -> main):
 *   {type:'ready', nrows, ncols, layerCount, bytes, initMs}
 *   {type:'result', seq, tEvent, rgba, inCount, nodataCount, enabledCount, computeMs,
 *                   tWorkerStartAbs, tWorkerEndAbs}              rgba is transferred
 *   {type:'mask', reqId, seq, inCount, mask}                     mask (Uint8Array buffer, 1 = in) is transferred
 *   {type:'error', message}
 *
 * Absolute times are performance.timeOrigin + performance.now(), comparable across threads.
 */
'use strict';

const LITTLE_ENDIAN = new Uint8Array(new Uint32Array([1]).buffer)[0] === 1;

/** Pack one pixel so a single Uint32 write yields bytes [r, g, b, a] in memory order. */
function packRGBA(r, g, b, a) {
  return LITTLE_ENDIAN
    ? ((a << 24) | (b << 16) | (g << 8) | r) >>> 0
    : ((r << 24) | (g << 16) | (b << 8) | a) >>> 0;
}

const PX_IN = packRGBA(24, 119, 242, 150);     // in-region: translucent blue
const PX_NODATA = packRGBA(60, 60, 60, 130);   // nodata hatch stripe
const PX_OUT = 0;                              // fully transparent
const HATCH_PERIOD_MASK = 7;                   // (row + col) & 7 < HATCH_WIDTH -> stripe
const HATCH_WIDTH = 2;

const state = {
  manifest: null,
  nrows: 0,
  ncols: 0,
  nodata: 255,
  layers: [],      // Uint8Array per layer
  mask: null,      // Uint8Array, 1 = in region
  pool: [],        // recycled RGBA ArrayBuffers
  lastSeq: -1,
  lastInCount: 0,
};

self.onmessage = (ev) => {
  const msg = ev.data || {};
  try {
    switch (msg.type) {
      case 'init':
        handleInit(msg);
        break;
      case 'compute':
        handleCompute(msg);
        break;
      case 'recycle':
        if (msg.buffer && msg.buffer.byteLength === state.nrows * state.ncols * 4 && state.pool.length < 3) {
          state.pool.push(msg.buffer);
        }
        break;
      case 'mask':
        handleMask(msg);
        break;
      default:
        self.postMessage({ type: 'error', message: `worker: unknown message type ${String(msg.type)}` });
    }
  } catch (err) {
    self.postMessage({ type: 'error', message: `worker: ${err && err.message ? err.message : String(err)}` });
  }
};

function handleInit(msg) {
  const t0 = performance.now();
  const manifest = msg.manifest;
  const nrows = manifest.nrows | 0;
  const ncols = manifest.ncols | 0;
  const n = nrows * ncols;
  if (!(nrows > 0 && ncols > 0)) throw new Error('manifest nrows/ncols invalid');
  if (!Array.isArray(msg.buffers) || msg.buffers.length !== manifest.layers.length) {
    throw new Error(`expected ${manifest.layers.length} layer buffers, got ${msg.buffers && msg.buffers.length}`);
  }
  const layers = msg.buffers.map((buf, i) => {
    if (buf.byteLength !== n) {
      throw new Error(`layer ${manifest.layers[i].id}: ${buf.byteLength} bytes, expected nrows*ncols = ${n}`);
    }
    return new Uint8Array(buf);
  });
  state.manifest = manifest;
  state.nrows = nrows;
  state.ncols = ncols;
  state.nodata = typeof manifest.nodata === 'number' ? manifest.nodata : 255;
  state.layers = layers;
  state.mask = new Uint8Array(n);
  state.pool = [];
  self.postMessage({
    type: 'ready',
    nrows,
    ncols,
    layerCount: layers.length,
    bytes: n * layers.length,
    initMs: performance.now() - t0,
  });
}

function handleCompute(msg) {
  const tStart = performance.now();
  const { nrows, ncols, layers, mask, nodata } = state;
  if (!mask) throw new Error('compute before init');
  const n = nrows * ncols;

  // Hoist enabled layers and their thresholds.
  const L = [];
  const T = [];
  for (let k = 0; k < layers.length; k++) {
    if (msg.enabled[k]) {
      L.push(layers[k]);
      T.push(msg.thresholds[k] | 0);
    }
  }
  const m = L.length;

  const buffer = state.pool.pop() || new ArrayBuffer(n * 4);
  const px = new Uint32Array(buffer);
  let inCount = 0;
  let nodataCount = 0;

  if (m === 0) {
    mask.fill(0);
    px.fill(PX_OUT);
  } else {
    let p = 0;
    for (let r = 0; r < nrows; r++) {
      for (let c = 0; c < ncols; c++, p++) {
        let inside = 1;
        let nd = 0;
        for (let k = 0; k < m; k++) {
          const v = L[k][p];
          if (v === nodata) { nd = 1; inside = 0; break; }
          if (v > T[k]) inside = 0;
        }
        mask[p] = inside;
        if (inside) {
          px[p] = PX_IN;
          inCount++;
        } else if (nd) {
          nodataCount++;
          px[p] = (((r + c) & HATCH_PERIOD_MASK) < HATCH_WIDTH) ? PX_NODATA : PX_OUT;
        } else {
          px[p] = PX_OUT;
        }
      }
    }
  }

  const tEnd = performance.now();
  state.lastSeq = msg.seq;
  state.lastInCount = inCount;
  self.postMessage({
    type: 'result',
    seq: msg.seq,
    tEvent: msg.tEvent,
    rgba: buffer,
    inCount,
    nodataCount,
    enabledCount: m,
    computeMs: tEnd - tStart,
    tWorkerStartAbs: performance.timeOrigin + tStart,
    tWorkerEndAbs: performance.timeOrigin + tEnd,
  }, [buffer]);
}

function handleMask(msg) {
  if (!state.mask) throw new Error('mask requested before init');
  const copy = state.mask.slice();
  self.postMessage({
    type: 'mask',
    reqId: msg.reqId,
    seq: state.lastSeq,
    inCount: state.lastInCount,
    mask: copy.buffer,
  }, [copy.buffer]);
}
