/* geom.js — pure geometry helpers shared by app.js (browser) and selftest.mjs (Node).
 *
 * Coordinate transform (documented here and in docs/experiments/g3-rendering.md):
 *   d3-contour works in grid space where values[j * ncols + i] is the sample for cell (i, j) and
 *   that cell covers x in [i, i+1], y in [j, j+1] (centre at (i+0.5, j+0.5)); with smooth linear
 *   interpolation at threshold 0.5 on a 0/1 mask, ring vertices fall exactly on cell edges.
 *   The grid is a regular lon/lat grid over bounds [W, S, E, N] with row 0 at the NORTH edge, so
 *       lon = W + x * (E - W) / ncols
 *       lat = N - y * (N - S) / nrows
 *   This is the same mapping MapLibre applies to the canvas source's four corner coordinates.
 */
(function (root) {
  'use strict';

  const KM_PER_DEG = 111.32;

  function gridToLonLat(bounds, ncols, nrows) {
    const [W, S, E, N] = bounds;
    const dLon = (E - W) / ncols;
    const dLat = (N - S) / nrows;
    return function toLonLat(pt) {
      return [W + pt[0] * dLon, N - pt[1] * dLat];
    };
  }

  /** Shoelace signed area in the ring's own units; positive = counter-clockwise (y up). */
  function signedArea(ring) {
    let a = 0;
    for (let i = 0, n = ring.length - 1; i < n; i++) {
      a += ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1];
    }
    return a / 2;
  }

  /** Approximate planar area in km^2 of a lon/lat ring, scaling longitude by cos(mean latitude). */
  function ringAreaKm2(ring, lat0) {
    const kx = KM_PER_DEG * Math.cos((lat0 * Math.PI) / 180);
    const ky = KM_PER_DEG;
    let a = 0;
    for (let i = 0, n = ring.length - 1; i < n; i++) {
      const x0 = ring[i][0] * kx, y0 = ring[i][1] * ky;
      const x1 = ring[i + 1][0] * kx, y1 = ring[i + 1][1] * ky;
      a += x0 * y1 - x1 * y0;
    }
    return a / 2;
  }

  function cellAreaKm2(bounds, ncols, nrows) {
    const [W, S, E, N] = bounds;
    const lat0 = (S + N) / 2;
    const dLonKm = ((E - W) / ncols) * KM_PER_DEG * Math.cos((lat0 * Math.PI) / 180);
    const dLatKm = ((N - S) / nrows) * KM_PER_DEG;
    return dLonKm * dLatKm;
  }

  /**
   * Convert d3-contour MultiPolygon coordinates (grid space) to a GeoJSON Feature in WGS84,
   * enforcing RFC 7946 winding (exterior counter-clockwise, holes clockwise in lon/lat).
   * Returns { feature, stats }.
   */
  function contourToGeoJSON(multiPolygonCoords, bounds, ncols, nrows) {
    const toLonLat = gridToLonLat(bounds, ncols, nrows);
    let polygons = 0, holes = 0, vertices = 0, reversed = 0;
    const polys = multiPolygonCoords.map((polygon) => polygon.map((ring, ringIndex) => {
      let out = ring.map(toLonLat);
      vertices += out.length;
      const a = signedArea(out);
      const wantPositive = ringIndex === 0;
      if ((a > 0) !== wantPositive && a !== 0) {
        out = out.slice().reverse();
        reversed++;
      }
      if (ringIndex === 0) polygons++; else holes++;
      return out;
    }));
    const feature = {
      type: 'Feature',
      properties: { source: 'd3-contour threshold 0.5 on 0/1 mask', polygons, holes },
      geometry: { type: 'MultiPolygon', coordinates: polys },
    };
    return { feature, stats: { polygons, holes, vertices, reversedRings: reversed } };
  }

  /** Basic topology checks: closure, vertex count, finiteness, bounds, winding, non-zero area. */
  function validate(feature, bounds) {
    const problems = [];
    const [W, S, E, N] = bounds;
    const lat0 = (S + N) / 2;
    const eps = 1e-9;
    let polygons = 0, holes = 0, vertices = 0, netAreaKm2 = 0;
    const geom = feature && feature.geometry;
    if (!geom || geom.type !== 'MultiPolygon') {
      return { ok: false, problems: ['geometry is not a MultiPolygon'], polygons, holes, vertices, netAreaKm2 };
    }
    geom.coordinates.forEach((polygon, pi) => {
      if (!polygon.length) { problems.push(`polygon ${pi} has no rings`); return; }
      polygon.forEach((ring, ri) => {
        const tag = `polygon ${pi} ring ${ri}`;
        vertices += ring.length;
        if (ring.length < 4) problems.push(`${tag}: fewer than 4 vertices`);
        const first = ring[0], last = ring[ring.length - 1];
        if (!first || !last || first[0] !== last[0] || first[1] !== last[1]) problems.push(`${tag}: not closed`);
        for (let i = 0; i < ring.length; i++) {
          const [x, y] = ring[i];
          if (!Number.isFinite(x) || !Number.isFinite(y)) { problems.push(`${tag}: non-finite coordinate`); break; }
          if (x < W - eps || x > E + eps || y < S - eps || y > N + eps) { problems.push(`${tag}: vertex outside bounds`); break; }
        }
        const a = signedArea(ring);
        if (a === 0) problems.push(`${tag}: zero area`);
        if (ri === 0) {
          polygons++;
          if (a < 0) problems.push(`${tag}: exterior ring is clockwise`);
        } else {
          holes++;
          if (a > 0) problems.push(`${tag}: hole is counter-clockwise`);
        }
        netAreaKm2 += ringAreaKm2(ring, lat0);
      });
    });
    return { ok: problems.length === 0, problems, polygons, holes, vertices, netAreaKm2 };
  }

  root.G3Geom = { gridToLonLat, signedArea, ringAreaKm2, cellAreaKm2, contourToGeoJSON, validate };
})(typeof self !== 'undefined' ? self : globalThis);
