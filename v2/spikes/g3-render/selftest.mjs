// selftest.mjs — Node-only verification of geom.js (no browser, no d3, no network).
//
// geom.js is a plain CommonJS-compatible script (no import/export) shared with app.js via a
// classic <script> tag. It is loaded here with createRequire so this file can stay ESM (.mjs)
// without needing a package.json. geom.js attaches its exports to `globalThis.G3Geom` because it
// guards with `typeof self !== 'undefined' ? self : globalThis` and Node has no `self`.
//
// What this checks, matching research/10-codex-adversarial-review-pass3-plan.md finding M4
// ("test holes/topology"):
//   1. contourToGeoJSON always normalizes winding to RFC 7946 (exterior CCW, holes CW) in
//      lon/lat, regardless of which winding the input grid-space ring happened to have -- this
//      is the actual claim in app.js's "Coordinate transform" <details> block, so it is the one
//      most worth checking without trusting the browser.
//   2. A polygon-with-hole nets a smaller area than the same polygon without the hole.
//   3. A multi-polygon (two disjoint blobs) reports the right polygon/hole counts.
//   4. validate() actually detects each kind of bad topology it claims to (unclosed ring, too
//      few vertices, out-of-bounds vertex, wrong winding) when fed a hand-built bad Feature --
//      contourToGeoJSON's auto-fix would hide these, so they are constructed directly.
//   5. gridToLonLat / cellAreaKm2 arithmetic against hand-computed expected values.
//
// Run:  node spikes/g3-render/selftest.mjs   (from anywhere; paths are relative to this file)

import { createRequire } from 'module';
import { fileURLToPath } from 'url';
import path from 'path';

const require = createRequire(import.meta.url);
const __dirname = path.dirname(fileURLToPath(import.meta.url));
require(path.join(__dirname, 'geom.js'));

const G = globalThis.G3Geom;
if (!G) {
  console.error('FAIL: geom.js did not attach globalThis.G3Geom');
  process.exit(1);
}

const BOUNDS = [-79.15, 35.80, -78.55, 36.15]; // w, s, e, n -- same slice as the manifest
const NCOLS = 550;
const NROWS = 401;

let failures = 0;
function check(name, fn) {
  try {
    fn();
    console.log(`PASS  ${name}`);
  } catch (err) {
    failures++;
    console.error(`FAIL  ${name}\n      ${err && err.stack ? err.stack.split('\n').slice(0, 3).join('\n      ') : err}`);
  }
}

function assert(cond, msg) {
  if (!cond) throw new Error(msg || 'assertion failed');
}
function closeTo(a, b, eps, msg) {
  if (Math.abs(a - b) > eps) throw new Error(`${msg || 'not close'}: ${a} vs ${b} (eps ${eps})`);
}

// A square ring in grid space [[x,y],...], closed, CCW-in-grid-space (y down) by construction.
function gridSquare(x0, y0, x1, y1, ccwInGrid) {
  const corners = ccwInGrid
    ? [[x0, y0], [x0, y1], [x1, y1], [x1, y0], [x0, y0]]
    : [[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]];
  return corners;
}

check('gridToLonLat: corners map to manifest bounds exactly', () => {
  const toLonLat = G.gridToLonLat(BOUNDS, NCOLS, NROWS);
  const [W, S, E, N] = BOUNDS;
  closeTo(toLonLat([0, 0])[0], W, 1e-9, 'x=0 -> west');
  closeTo(toLonLat([0, 0])[1], N, 1e-9, 'y=0 -> north (row 0 is the north edge)');
  closeTo(toLonLat([NCOLS, NROWS])[0], E, 1e-9, 'x=ncols -> east');
  closeTo(toLonLat([NCOLS, NROWS])[1], S, 1e-9, 'y=nrows -> south');
  closeTo(toLonLat([NCOLS / 2, 0])[0], (W + E) / 2, 1e-9, 'x=ncols/2 -> mid-longitude');
});

check('cellAreaKm2: sane magnitude for a 100 m-ish cell at this latitude', () => {
  const a = G.cellAreaKm2(BOUNDS, NCOLS, NROWS);
  // (E-W)/ncols ~ 0.00109 deg lon, (N-S)/nrows ~ 0.000873 deg lat; at ~36N, 1 deg lon ~ 90 km.
  assert(a > 0.005 && a < 0.02, `cell area out of expected range: ${a} km^2`);
});

check('contourToGeoJSON: single square, grid-space CCW input -> RFC7946 exterior CCW', () => {
  const ring = gridSquare(100, 100, 200, 200, /*ccwInGrid*/ true);
  const { feature, stats } = G.contourToGeoJSON([[ring]], BOUNDS, NCOLS, NROWS);
  assert(stats.polygons === 1 && stats.holes === 0, 'expected 1 polygon, 0 holes');
  const v = G.validate(feature, BOUNDS);
  assert(v.ok, `validate reported problems: ${JSON.stringify(v.problems)}`);
  const outerRing = feature.geometry.coordinates[0][0];
  assert(G.signedArea(outerRing) > 0, 'exterior ring must be CCW (positive signed area) in lon/lat');
});

check('contourToGeoJSON: single square, grid-space CW input -> STILL normalized to CCW', () => {
  // Same square, opposite input winding: the transform must not simply trust the input.
  const ring = gridSquare(100, 100, 200, 200, /*ccwInGrid*/ false);
  const { feature } = G.contourToGeoJSON([[ring]], BOUNDS, NCOLS, NROWS);
  const v = G.validate(feature, BOUNDS);
  assert(v.ok, `validate reported problems: ${JSON.stringify(v.problems)}`);
  const outerRing = feature.geometry.coordinates[0][0];
  assert(G.signedArea(outerRing) > 0, 'exterior ring must still end up CCW regardless of input winding');
});

check('contourToGeoJSON: square with an interior hole -> hole is CW, area is smaller', () => {
  const outer = gridSquare(50, 50, 250, 250, true);
  const hole = gridSquare(100, 100, 150, 150, true); // same input winding as outer on purpose
  const { feature, stats } = G.contourToGeoJSON([[outer, hole]], BOUNDS, NCOLS, NROWS);
  assert(stats.polygons === 1 && stats.holes === 1, `expected 1 polygon + 1 hole, got ${JSON.stringify(stats)}`);
  const v = G.validate(feature, BOUNDS);
  assert(v.ok, `validate reported problems: ${JSON.stringify(v.problems)}`);
  const [outerRing, holeRing] = feature.geometry.coordinates[0];
  assert(G.signedArea(outerRing) > 0, 'exterior ring must be CCW');
  assert(G.signedArea(holeRing) < 0, 'hole ring must be CW (negative signed area) per RFC 7946');

  const { feature: noHoleFeature } = G.contourToGeoJSON([[outer]], BOUNDS, NCOLS, NROWS);
  const withHoleArea = G.validate(feature, BOUNDS).netAreaKm2;
  const withoutHoleArea = G.validate(noHoleFeature, BOUNDS).netAreaKm2;
  assert(withHoleArea < withoutHoleArea, 'a polygon with a hole must net less area than the same polygon without it');
  closeTo(withoutHoleArea - withHoleArea, Math.abs(G.ringAreaKm2(hole.map(G.gridToLonLat(BOUNDS, NCOLS, NROWS)), (BOUNDS[1] + BOUNDS[3]) / 2)), 1e-6, 'area removed by the hole must equal the hole ring area');
});

check('contourToGeoJSON: two disjoint blobs -> MultiPolygon with 2 polygons, 0 holes', () => {
  const a = gridSquare(10, 10, 60, 60, true);
  const b = gridSquare(400, 300, 480, 380, true);
  const { feature, stats } = G.contourToGeoJSON([[a], [b]], BOUNDS, NCOLS, NROWS);
  assert(feature.geometry.type === 'MultiPolygon', 'must stay a MultiPolygon');
  assert(stats.polygons === 2 && stats.holes === 0, `expected 2 polygons, 0 holes, got ${JSON.stringify(stats)}`);
  assert(G.validate(feature, BOUNDS).ok, 'two disjoint valid blobs must validate');
});

check('validate(): detects an unclosed ring', () => {
  const toLonLat = G.gridToLonLat(BOUNDS, NCOLS, NROWS);
  const ring = [[100, 100], [100, 200], [200, 200], [200, 100]].map(toLonLat); // no closing point
  const feature = { type: 'Feature', geometry: { type: 'MultiPolygon', coordinates: [[ring]] } };
  const v = G.validate(feature, BOUNDS);
  assert(!v.ok, 'unclosed ring must fail validation');
  assert(v.problems.some((p) => p.includes('not closed')), `expected a "not closed" problem, got ${JSON.stringify(v.problems)}`);
});

check('validate(): detects too few vertices', () => {
  const toLonLat = G.gridToLonLat(BOUNDS, NCOLS, NROWS);
  const ring = [[100, 100], [200, 200], [100, 100]].map(toLonLat); // 3 points, closed, but degenerate
  const feature = { type: 'Feature', geometry: { type: 'MultiPolygon', coordinates: [[ring]] } };
  const v = G.validate(feature, BOUNDS);
  assert(!v.ok, 'a 3-vertex ring must fail validation');
  assert(v.problems.some((p) => p.includes('fewer than 4 vertices')), `expected a vertex-count problem, got ${JSON.stringify(v.problems)}`);
});

check('validate(): detects a vertex outside the manifest bounds', () => {
  const ring = [[-90, 40], [-90, 41], [-89, 41], [-89, 40], [-90, 40]]; // way outside BOUNDS
  const feature = { type: 'Feature', geometry: { type: 'MultiPolygon', coordinates: [[ring]] } };
  const v = G.validate(feature, BOUNDS);
  assert(!v.ok, 'an out-of-bounds vertex must fail validation');
  assert(v.problems.some((p) => p.includes('outside bounds')), `expected an out-of-bounds problem, got ${JSON.stringify(v.problems)}`);
});

check('validate(): detects a hole wound the same direction as its exterior', () => {
  const toLonLat = G.gridToLonLat(BOUNDS, NCOLS, NROWS);
  const outer = gridSquare(50, 50, 250, 250, true);
  const hole = gridSquare(100, 100, 150, 150, true);
  // Build directly (bypassing contourToGeoJSON's auto-fix) with BOTH rings CCW in lon/lat.
  const outerLL = outer.map(toLonLat);
  const holeLL = hole.map(toLonLat);
  if (G.signedArea(holeLL) < 0) holeLL.reverse(); // force the hole to be CCW, i.e. wrong
  const feature = { type: 'Feature', geometry: { type: 'MultiPolygon', coordinates: [[outerLL, holeLL]] } };
  const v = G.validate(feature, BOUNDS);
  assert(!v.ok, 'a hole wound the same way as its exterior must fail validation');
  assert(v.problems.some((p) => p.includes('hole') && p.includes('counter-clockwise')), `expected a hole-winding problem, got ${JSON.stringify(v.problems)}`);
});

check('validate(): a well-formed single square has zero problems and the expected area sign', () => {
  const ring = gridSquare(0, 0, NCOLS, NROWS, true); // the whole grid, sanity check on full extent
  const { feature } = G.contourToGeoJSON([[ring]], BOUNDS, NCOLS, NROWS);
  const v = G.validate(feature, BOUNDS);
  assert(v.ok, `expected no problems, got ${JSON.stringify(v.problems)}`);
  const [W, S, E, N] = BOUNDS;
  const fullArea = Math.abs(G.ringAreaKm2(
    [[W, N], [W, S], [E, S], [E, N], [W, N]],
    (S + N) / 2,
  ));
  closeTo(v.netAreaKm2, fullArea, fullArea * 0.01, 'full-extent polygon area should match the bbox area to ~1%');
});

console.log(`\n${failures === 0 ? 'ALL PASS' : `${failures} FAILURE(S)`}`);
process.exit(failures === 0 ? 0 : 1);
