/* worker.js — G3 raster-algebra Web Worker (classic worker, no imports, no build step).
 *
 * Holds the published-v2 layers -- a VALUE plane and a STATUS plane each -- and per request
 * computes a three-outcome verdict per cell, which is `locfinder/wire.py` transcribed:
 *
 *   per layer:  OK             -> value <= T ? PASS : FAIL
 *               NO_PATH        -> FAIL
 *               BEYOND_HORIZON -> horizon_s >= 60*T ? FAIL : UNKNOWN
 *               OFF_NETWORK    -> value > T ? FAIL : UNKNOWN     (value is a LOWER BOUND here)
 *               LAYER_UNKNOWN / OUTSIDE -> UNKNOWN
 *   combined:   any FAIL -> EXCLUDED;  else any UNKNOWN -> UNKNOWN;  else INCLUDED
 *
 * **One known failure beats any number of unknowns.** The previous version broke out of the layer
 * loop on the first missing value, which is that rule inverted: a cell unknown in one layer and
 * excluded in another came out unknown. It also had a single `nodata` code, so a cell past the
 * built horizon -- a known failure at any threshold below it -- was indistinguishable from a cell
 * with no road near it. On the published Triangle walk layer that is 18,648 cells at ten minutes.
 *
 * It writes an RGBA buffer (included colour, excluded transparent, unknown diagonally hatched)
 * and transfers it to the main thread.
 *
 * Protocol (main -> worker):
 *   {type:'init', manifest, values:[ArrayBuffer x N], statuses:[ArrayBuffer x N]}  transferred
 *   {type:'compute', seq, thresholds:[N ints], enabled:[N bools], tEvent}
 *   {type:'recycle', buffer}                                     returns an RGBA buffer to the pool
 *   {type:'mask', reqId}                                         asks for a copy of the current 0/1 mask
 *   {type:'verdicts', reqId}                                     asks for the three-way verdict plane
 * Protocol (worker -> main):
 *   {type:'ready', nrows, ncols, layerCount, bytes, initMs}
 *   {type:'result', seq, tEvent, rgba, inCount, nodataCount, excludedCount, enabledCount,
 *                   computeMs, tWorkerStartAbs, tWorkerEndAbs}   rgba is transferred
 *                   inCount = INCLUDED, nodataCount = UNKNOWN, excludedCount = EXCLUDED
 *   {type:'mask', reqId, seq, inCount, mask}                     mask (Uint8Array buffer, 1 = in) is transferred
 *   {type:'verdicts', reqId, seq, verdicts}                      Int8Array buffer, 0/1/2 = INCLUDED/EXCLUDED/UNKNOWN
 *
 * The verdict plane exists because the mask cannot carry three outcomes and the RGBA buffer can
 * only be read back where the hatch stripe falls. Codex pass 43 F2: without it the conformance
 * harness compared nothing on 3/4 of the cells and nothing at all on the real-layer window, and
 * an implementation that returned UNKNOWN for NO_PATH -- or that rotated the whole raster by
 * 10,007 cells -- passed all 37 of its checks.
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

/* The wire codes. These are `locfinder/wire.py`'s, and deliberately NOT `status.Reason`'s --
 * the layer contract forbids writing the in-memory enum into a raster. `ENCODING` is checked at
 * init, because a format that changed a code's meaning must be refused, never guessed at. */
const ENCODING = 'published-v2';
const S_OK = 0, S_OFF_NETWORK = 1, S_BEYOND_HORIZON = 2, S_NO_PATH = 3;
const S_LAYER_UNKNOWN = 4, S_OUTSIDE = 5;
/* Missing with no recorded cause -- what a v1 artifact's single NODATA becomes when it is lifted
 * into this format. Never a known failure, which is exactly what v1 could assert. */
const S_UNKNOWN_CAUSE = 6;
const O_PASS = 0, O_FAIL = 1, O_UNKNOWN = 2;
/* `status.Verdict`'s order, which the verdict plane is reported in. */
const V_INCLUDED = 0, V_EXCLUDED = 1, V_UNKNOWN = 2;

const PX_IN = packRGBA(24, 119, 242, 150);     // included: translucent blue
const PX_NODATA = packRGBA(60, 60, 60, 130);   // nodata hatch stripe
const PX_OUT = 0;                              // fully transparent
const HATCH_PERIOD_MASK = 7;                   // (row + col) & 7 < HATCH_WIDTH -> stripe
const HATCH_WIDTH = 2;

const state = {
  manifest: null,
  nrows: 0,
  ncols: 0,
  layers: [],      // value plane, Uint8Array per layer
  statuses: [],    // status plane, Uint8Array per layer
  horizons: [],    // horizon_s per layer, for the BEYOND_HORIZON rule
  mask: null,      // Uint8Array, 1 = in region
  verdict: null,   // Int8Array, 0 INCLUDED / 1 EXCLUDED / 2 UNKNOWN -- the whole algebra
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
      case 'verdicts':
        handleVerdicts(msg);
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
  // A versioned format is refused, not reinterpreted. Minute values 251-254 are real answers in
  // artifacts already on disk, so a decoder that guessed at an unknown encoding would read them
  // as sentinels and publish a region nobody computed.
  if (manifest.encoding !== ENCODING) {
    throw new Error(`manifest encoding ${JSON.stringify(manifest.encoding)} is not ${ENCODING}; `
      + 'this decoder refuses a format it does not know rather than guessing at its codes');
  }
  const plane = (bufs, what) => {
    if (!Array.isArray(bufs) || bufs.length !== manifest.layers.length) {
      throw new Error(`expected ${manifest.layers.length} ${what} buffers, got ${bufs && bufs.length}`);
    }
    return bufs.map((buf, i) => {
      if (buf.byteLength !== n) {
        throw new Error(`layer ${manifest.layers[i].id} ${what}: ${buf.byteLength} bytes, expected nrows*ncols = ${n}`);
      }
      return new Uint8Array(buf);
    });
  };
  const layers = plane(msg.values, 'value');
  const statuses = plane(msg.statuses, 'status');
  // `Surface.validate` forces a BEYOND_HORIZON cell's bound to equal the horizon exactly, so its
  // value byte is `ceil(horizon_s / 60)` and is otherwise redundant -- the decoder compares
  // against the manifest, never against the stored bound. That redundancy is a LIMITED
  // CONSISTENCY CHECK, and pass 44 F5 is clear about what it is not: a quantized byte cannot
  // recover an exact horizon. A 601-second horizon encodes as 11, so a manifest claiming 660
  // seconds passes and still turns UNKNOWN into EXCLUDED at eleven minutes; and 15,300 and
  // 72,000 both saturate to 254. What it does catch is a manifest off by a whole minute or more
  // at these magnitudes, and planes that are internally inconsistent -- which is why it scans
  // every cell rather than breaking at the first, as it did when pass 44 found values [120, 10]
  // with statuses [2, 2] initialising happily.
  const horizons = manifest.layers.map((l, i) => {
    if (typeof l.horizon_s !== 'number' || !(l.horizon_s > 0)) {
      throw new Error(`layer ${l.id}: manifest has no positive horizon_s, so BEYOND_HORIZON cannot be decided`);
    }
    return l.horizon_s;
  });
  for (let k = 0; k < layers.length; k++) {
    const expectedByte = Math.ceil(horizons[k] / 60);
    const n2 = layers[k].length;
    for (let p = 0; p < n2; p++) {
      if (statuses[k][p] === S_BEYOND_HORIZON
          && layers[k][p] !== Math.min(expectedByte, 254)) {
        throw new Error(`layer ${manifest.layers[k].id}: the BEYOND_HORIZON cell at ${p} carries `
          + `bound ${layers[k][p]} but the manifest horizon ${horizons[k]}s implies `
          + `${expectedByte}; the manifest does not describe these planes`);
      }
    }
  }
  state.manifest = manifest;
  state.nrows = nrows;
  state.ncols = ncols;
  state.layers = layers;
  state.statuses = statuses;
  state.horizons = horizons;
  state.mask = new Uint8Array(n);
  state.verdict = new Int8Array(n);
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
  const { nrows, ncols, layers, statuses, horizons, mask, verdict } = state;
  if (!mask) throw new Error('compute before init');
  const n = nrows * ncols;

  // Hoist enabled layers, their status planes, thresholds and horizons.
  const L = [];
  const S = [];
  const T = [];
  const H = [];
  for (let k = 0; k < layers.length; k++) {
    if (msg.enabled[k]) {
      L.push(layers[k]);
      S.push(statuses[k]);
      const t = msg.thresholds[k];
      // Pass 43 F7: `| 0` truncates, and at 10.5 minutes a 610-second OK cell decoded as a
      // failure where the rule passes it. The minute planes cannot answer a fractional
      // threshold exactly, so this refuses rather than manufacturing an exclusion.
      if (!Number.isInteger(t)) {
        throw new Error(`threshold ${t} for layer ${k} is not a whole number of minutes; `
          + 'this format stores whole minutes and cannot answer a fractional threshold exactly');
      }
      T.push(t);
      H.push(horizons[k]);
    }
  }
  const m = L.length;

  const buffer = state.pool.pop() || new ArrayBuffer(n * 4);
  const px = new Uint32Array(buffer);
  let inCount = 0;
  let nodataCount = 0;

  let excludedCount = 0;

  if (m === 0) {
    // No criteria excludes nothing -- `status.combine`'s own rule, and the opposite of the empty
    // AND returning false. Every cell is included.
    mask.fill(1);
    verdict.fill(V_INCLUDED);
    px.fill(PX_IN);
    inCount = n;
  } else {
    let p = 0;
    for (let r = 0; r < nrows; r++) {
      for (let c = 0; c < ncols; c++, p++) {
        let anyFail = 0;
        let anyUnknown = 0;
        // No `break`: a known failure in a later layer must beat an unknown in an earlier one.
        for (let k = 0; k < m; k++) {
          const o = outcomeFor(S[k][p], L[k][p], T[k], H[k]);
          if (o === O_FAIL) anyFail = 1;
          else if (o === O_UNKNOWN) anyUnknown = 1;
        }
        if (anyFail) {
          mask[p] = 0;
          verdict[p] = V_EXCLUDED;
          px[p] = PX_OUT;
          excludedCount++;
        } else if (anyUnknown) {
          mask[p] = 0;
          verdict[p] = V_UNKNOWN;
          nodataCount++;
          px[p] = (((r + c) & HATCH_PERIOD_MASK) < HATCH_WIDTH) ? PX_NODATA : PX_OUT;
        } else {
          mask[p] = 1;
          verdict[p] = V_INCLUDED;
          px[p] = PX_IN;
          inCount++;
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
    excludedCount,
    enabledCount: m,
    computeMs: tEnd - tStart,
    tWorkerStartAbs: performance.timeOrigin + tStart,
    tWorkerEndAbs: performance.timeOrigin + tEnd,
  }, [buffer]);
}

/** One layer's outcome for one cell. This is `locfinder/wire.py:outcome_planes`, cell-wise.
 *
 * `value` means two different things and the status plane says which: the travel time where the
 * status is OK, and a LOWER BOUND on it where the status is OFF_NETWORK, BEYOND_HORIZON or
 * NO_PATH. A bound above the threshold is a known failure with no route ever computed.
 *
 * BEYOND_HORIZON compares against the horizon itself and never against the stored bound, so a
 * malformed bound cannot change an eligibility answer -- `status.py`'s rule, kept here.
 */
function outcomeFor(status, value, thresholdMin, horizonS) {
  switch (status) {
    case S_OK:
      return value <= thresholdMin ? O_PASS : O_FAIL;
    case S_NO_PATH:
      return O_FAIL;
    case S_BEYOND_HORIZON:
      return horizonS >= 60 * thresholdMin ? O_FAIL : O_UNKNOWN;
    case S_OFF_NETWORK:
      return value > thresholdMin ? O_FAIL : O_UNKNOWN;
    case S_LAYER_UNKNOWN:
    case S_OUTSIDE:
    case S_UNKNOWN_CAUSE:
      return O_UNKNOWN;
    default:
      throw new Error(`status plane holds code ${status}, which this decoder does not define`);
  }
}

function handleVerdicts(msg) {
  if (!state.verdict) throw new Error('verdicts requested before init');
  const copy = state.verdict.slice();
  self.postMessage({
    type: 'verdicts',
    reqId: msg.reqId,
    seq: state.lastSeq,
    verdicts: copy.buffer,
  }, [copy.buffer]);
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
