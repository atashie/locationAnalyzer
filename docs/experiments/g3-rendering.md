# G3: browser rendering — built and verified without a browser 2026-11-03; live device measurements pending

**Question.** Can a mid-range phone threshold six real travel-time layers in a Web Worker, repaint a MapLibre `canvas` source, and polygonize the result under budget — or does v2.0 need a server-rendered mask instead? (`research/08-synthesis.md` §3.2, §6 gate G3; `research/10-codex-adversarial-review-pass3-plan.md` finding M4.)

Everything in this document that can be checked without opening a real browser has been checked and is reported with its evidence below (exporter run, byte-count assertions, `node --check`, a Node-only geometry self-test, and live lookups against the pinned libraries' actual source/spec). The **timing numbers in §6 require a live browser session on real hardware** and are left as blanks for whoever runs the page next; nothing here is a guessed or simulated number.

## 1. What was built

`v2/spikes/g3-render/`:

| File | Role |
|---|---|
| `export_layers.py` | Reads real `v2/data/layers/*.tif`, reprojects to a WGS84 grid, writes `fixtures/*.bin` + `fixtures/manifest.json` |
| `make_fixtures.py` | Synthetic fallback generator, same contract, same shape, clearly marked `synthetic` |
| `index.html` | Page shell, pinned CDN tags + SRI, stats tables, explanatory `<details>` blocks |
| `app.js` | Main thread: loads fixtures once, drives the worker, draws the MapLibre canvas source, polygonizes, records every timing |
| `worker.js` | Web Worker: AND/threshold mask + nodata accounting + RGBA encode |
| `geom.js` | Pure grid→lon/lat transform, winding normalization, topology validation (shared by `app.js` and `selftest.mjs`) |
| `selftest.mjs` | **Node-only**, no browser, no d3: exercises `geom.js`'s hole/winding/topology logic directly |
| `versions.json` | Lockfile for every pinned CDN asset (exact version, URL, byte count, SHA-384) |
| `styles.css` | Phone-friendly layout (single column under 880px, two-pane above) |

## 2. Method

**Data flow.** `export_layers.py` → `fixtures/*.bin` + `manifest.json` → `app.js` fetches all of it once at load → transfers the raw `ArrayBuffer`s into `worker.js` → on every checkbox/slider change, `app.js` posts `{thresholds, enabled}` → `worker.js` computes `mask[p] = AND over enabled layers of (value <= threshold)`, treating `255` as a **failure** for every layer (`worker.js` line 144: `if (v === nodata) { nd = 1; inside = 0; break; }` — nodata is never treated as a very-large-but-valid minute value), counts cells that are nodata in *any* enabled layer separately, and returns an RGBA buffer (in-region solid blue, out-of-region transparent, nodata a diagonal hatch) plus timings. `app.js` draws that buffer into an off-DOM `<canvas>` and pushes it to a MapLibre `canvas` source whose four corners are the manifest's `[W,S,E,N]` bbox in `[lon,lat]` order. "Polygonize" asks the worker for the current 0/1 mask, runs `d3.contours().size([ncols,nrows]).thresholds([0.5])` on it, and `geom.js` converts the resulting grid-space rings to a WGS84 `MultiPolygon`, normalizing winding and validating topology.

**Cross-thread timing.** `performance.now()` is relative to each execution context's own time origin, and a `Window` and its dedicated `Worker` do not share one — but `performance.timeOrigin` is itself epoch-relative, so `performance.timeOrigin + performance.now()` is an absolute wall-clock timestamp comparable across threads on the same machine. Both `worker.js` (`tWorkerStartAbs`/`tWorkerEndAbs`) and `app.js` (`nowAbs()`) use this convention so "worker compute ms" (purely inside the worker), "transfer+paint ms" (worker→main message delivery, canvas draw, GPU upload, actual compositor paint) and "slider→repaint total ms" (event to paint) are each a real subtraction of two comparable absolute timestamps, not an approximation.

**How "paint" is actually observed.** A MapLibre `CanvasSource` with `animate:true` (the default) calls `play()` on add, which keeps calling `map.triggerRepaint()` forever once per frame — verified by reading `src/source/canvas_source.ts` at the pinned tag (`https://raw.githubusercontent.com/maplibre/maplibre-gl-js/v5.24.0/src/source/canvas_source.ts`). That would make every slider change compete with a free-running render loop and make "repaint" unmeasurable. The page instead adds the source with `animate:false` and, after every `putImageData`, calls `canvasSource.play()` immediately followed by `canvasSource.pause()`: `play()` sets `_playing=true` and schedules one repaint; `pause()` synchronously calls `prepare()` (which re-uploads the canvas to the GPU texture because `_playing` is still `true` at that point) and only then sets `_playing=false`. The net effect, read directly from that source file, is exactly one synchronous texture upload plus exactly one scheduled frame — no ongoing loop. The actual paint completion is observed via `map.once('render', ...)`. Caveat (honest, not fixed): during the very first few hundred milliseconds of page load, an unrelated OSM basemap tile fade-in can itself fire a `'render'` event, which could occasionally be the one `once('render')` catches instead of the mask's own frame, slightly inflating the *very first* sample. Samples taken after the map has settled (essentially everything in the 20-change rolling window) are not subject to this.

**Default thresholds.** Each layer's slider defaults by mode (`walk`→20 min, `bike`→15 min, `drive`→10 min) so the initial AND is a realistic, non-trivial region rather than an arbitrary 30 for everything.

**Auto-bench.** Manual slider-dragging is how a human tester gets "last 20 changes," but for a scripted desktop run the page also has an "Auto-bench" button that fires 20 deterministic threshold changes (a fixed pseudo-random walk across layers, 1..60 min), **awaiting each round trip before starting the next** so every sample is a real, isolated slider→repaint measurement, not a burst.

## 3. Pinned versions (`versions.json`)

| Asset | Version | Source | SHA-384 verified against live bytes? |
|---|---|---|---|
| MapLibre GL JS | **5.24.0** | cdnjs (css+js) | Yes — recomputed `openssl dgst -sha384` against the live CDN response on 2026-11-03; matches `versions.json` exactly for all four pinned files (css, js, d3-array, d3-contour) |
| d3-array | 3.2.5 | jsdelivr | Yes |
| d3-contour | 4.0.3 | jsdelivr | Yes |
| OSM raster basemap | n/a | `tile.openstreetmap.org` | dev/low-volume only per `operations.osmfoundation.org/policies/tiles/`; swap before any public release |

**Why 5.24.0 and not the newest release.** MapLibre GL JS 6.0.0 (PR [#6254](https://github.com/maplibre/maplibre-gl-js/pull/6254), confirmed by fetching `CHANGELOG.md` at tag `v6.0.0`) switched to an ESM-only distribution — the UMD bundle (`maplibre-gl.js`, loadable from a plain `<script>` tag) is no longer published, only `maplibre-gl.mjs`. The latest release as of 2026-11-03 is **v6.16.0** (confirmed via the GitHub releases API, published 2026-10-25) and the newest 5.x release is **v5.24.0** (confirmed: no `v5.25.x` tag exists). A no-build, classic-`<script>` page therefore pins 5.24.0, the newest release that still ships a UMD bundle.

## 4. Data contract

Grid: `v2/locfinder/grid.py` — `NODATA = 255`, minutes 0..254, uint8, row 0 = north edge. Real source rasters: UTM 17N (EPSG:32617), 100 m cells, 550×401, confirmed by `rasterio.open(...).crs/.width/.height/.nodata` on every `.tif` in `v2/data/layers/`.

`fixtures/manifest.json`:
```json
{
  "nrows": 401, "ncols": 550,
  "bounds_wgs84": [-79.15, 35.80, -78.55, 36.15],
  "nodata": 255, "units": "minutes",
  "source": "real, exported <date>",
  "layers": [{"id", "label", "file", "engine", "mode", "category"}, ...]
}
```
`fixtures/<id>.bin`: raw row-major `uint8`, row 0 = north, exactly `nrows*ncols` bytes.

## 5. Running it

```bash
cd v2 && uv run python spikes/g3-render/export_layers.py   # real data (falls back: make_fixtures.py for synthetic)
node spikes/g3-render/selftest.mjs                          # Node-only geometry/topology check, no browser
npx serve v2/spikes/g3-render                                # from the repo root; open http://localhost:3000
```
On a phone over LAN: `http://<this PC's LAN IP>:3000` (same Wi-Fi; allow the port through the Windows firewall). Desktop throttled-4G run: Chrome DevTools → Network → disable cache + the "Fast 4G"/"Slow 4G" preset → hard reload → read "first mask paint," then drag sliders 20+ times (or press Auto-bench) and read the medians.

### 5.1 Exporter output (real data, run 2026-11-03)

7 real GeoTIFFs exist in `v2/data/layers/` (2 engines × 3 modes, with `valhalla` having an extra `_controlled` walk variant used for the G1 own-vs-Valhalla comparison, not a 4th mode). The exporter selects one layer per (engine, mode), preferring the plain variant and falling back to `_controlled` only when no plain variant exists for that pair — true today only for `valhalla`/`bike` — which deterministically yields exactly 6 layers with no padding needed:

| id | source file | bytes | nodata before reproject | nodata after reproject |
|---|---|---|---|---|
| own_grocery_bike | own_grocery_bike.tif | 220,550 | 23.7% | 21.9% |
| own_grocery_drive | own_grocery_drive.tif | 220,550 | 26.4% | 24.5% |
| own_grocery_walk | own_grocery_walk.tif | 220,550 | 25.8% | 23.8% |
| valhalla_grocery_bike | valhalla_grocery_bike_controlled.tif | 220,550 | 48.8% | 46.9% |
| valhalla_grocery_drive | valhalla_grocery_drive.tif | 220,550 | 17.6% | 15.7% |
| valhalla_grocery_walk | valhalla_grocery_walk.tif | 220,550 | 52.3% | 50.5% |

`220,550 = 401 × 550` for every file — asserted by the script and independently re-checked by reading each file's size with Python after the run. Total: 6 layers × 220,550 = 1,323,300 bytes. The 1-3 point nodata-fraction *decrease* after reprojection happens because the source is a UTM rectangle and its reprojection into a lon/lat rectangle is not itself a rectangle — the four corners cannot both be exact matches, so the two footprints disagree slightly at the edges; this is exactly what M4 ("define validity on reprojection") asked to be made explicit rather than silently absorbed, so `rasterio.warp.reproject` is called with `src_nodata=255, dst_nodata=255` and both before/after fractions are logged by the script and reproduced here.

`node selftest.mjs` (no browser, no d3): **11/11 PASS** — grid↔lon/lat corner arithmetic; a single blob normalizes to RFC 7946 exterior-CCW regardless of which winding the input grid-space ring had; a blob-with-hole reports 1 polygon + 1 hole, the hole is CW, and the net area equals the full-blob area minus the hole's own area; two disjoint blobs report 2 polygons / 0 holes; `validate()` actually flags each of: an unclosed ring, a <4-vertex ring, an out-of-bounds vertex, and a hole wound the same way as its exterior.

`node --check` passes on `app.js`, `worker.js`, and `geom.js`. `fixtures/manifest.json` parses with both `JSON.parse`-equivalent tooling and Python's `json` module.

## 6. Results (fill in from a live run — nothing below is simulated)

Pass criteria (synthesis §6 gate G3): median slider→repaint < **100 ms**; first mask paint < **1.5 s** on throttled 4G; polygons topologically valid (closed rings, exterior CCW / holes CW, no self-intersection flags from `validate()`).

| Environment | Worker compute, median (ms) | Transfer+paint, median (ms) | Slider→repaint, median (ms) | First paint since load (ms) | JS heap (MB, `performance.memory`) | Polygonize total (ms) | Polygons / holes / vertices | Topology valid? |
|---|---|---|---|---|---|---|---|---|
| Desktop, warm cache | | | | | | | | |
| Desktop, DevTools 4G throttle, cold cache | | | | | | | | |
| Mid-range phone (model: ___), LAN, warm cache | | | | | | | | |

Each run: load the page, let it reach "boot complete" in the log, press **Auto-bench** (desktop) or drag the sliders 20+ times (phone), copy the `#results` textarea row (already formatted to this table's column order with `<environment>` as the one field to fill in by hand), then press **Polygonize** once and note its row's numbers.

## 7. Native raster-styling finding (checked, not guessed)

**No for a plain `raster` layer.** MapLibre GL JS 5.24.0's `paint_raster` properties, read directly from `@maplibre/maplibre-gl-style-spec@26.5.1`'s `src/reference/v8.json` (`https://cdn.jsdelivr.net/npm/@maplibre/maplibre-gl-style-spec@26.5.1/src/reference/v8.json`), are exactly: `raster-opacity`, `raster-hue-rotate`, `raster-brightness-min`, `raster-brightness-max`, `raster-saturation`, `raster-contrast`, `resampling`, `raster-resampling`, `raster-fade-duration`. There is no `raster-color`. The feature request for exactly this — "Recoloring a raster source like a WMS or image... such as in mapbox: raster-color & raster-color-mix" — is tracked at `https://github.com/maplibre/maplibre-gl-js/issues/4479`, confirmed **open** via the GitHub API on 2026-11-03.

**Partial yes via `color-relief`.** The same style-spec file defines a `color-relief` layer type (`paint_color-relief`: `color-relief-opacity`, `color-relief-color`) added at "js 5.6.0" per its `sdk-support` metadata, with `color-relief-color` taking a color-ramp expression over `["elevation"]`. It requires a `source_raster_dem` (`type: "raster-dem"`) source with `encoding` one of `terrarium`, `mapbox`, or `custom` (`redFactor`/`greenFactor`/`blueFactor`/`baseShift`) — confirmed from the same JSON. This colours **one** elevation-encoded layer; it has no AND-of-six-layers semantics and would require re-encoding minutes into an RGB "fake DEM" tile scheme to use at all, which is why synthesis §3.2's note ("MapLibre raster styling tested on the pinned version, Terrarium trick dropped") rejected it rather than adopting it.

**Conclusion for G3:** native raster styling cannot replace the Worker-AND-then-canvas approach on this MapLibre version; the architecture under test here (Worker computes, main thread paints a `canvas` source) is the only path, which is exactly why this gate measures it rather than a style-spec shortcut.

## 8. M4 checklist (research/10-codex-adversarial-review-pass3-plan.md)

| Finding M4 item | Where addressed |
|---|---|
| Six layers unavailable → use real fixtures | `export_layers.py` reads real `.tif`s; §5.1 above shows 6 real layers, 0 synthetic padding needed this run |
| `^5` is not a pin | `versions.json` pins exact `5.24.0`/`3.2.5`/`4.0.3` with SHA-384 re-verified against live bytes, §3 |
| Mask 255 explicitly | `worker.js`: nodata check is a dedicated branch (`v === nodata`), never folded into the `> threshold` comparison |
| Define validity on reprojection | `export_layers.py`: `rasterio.warp.reproject(..., src_nodata=255, dst_nodata=255)`, before/after nodata fractions logged, §5.1 |
| Canvas corners as lon/lat | `app.js` `addMaskSource`: `coordinates: [[W,N],[E,N],[E,S],[W,S]]` |
| Transform contour pixel coordinates | `geom.js` `gridToLonLat`/`contourToGeoJSON`, independently verified by `selftest.mjs` (11/11 pass) |
| Test holes/topology | `selftest.mjs`: dedicated hole, multi-polygon, and four deliberately-broken-topology test cases |
| Lock an exact MapLibre version | §3 above; 5.24.0 chosen specifically because 6.x dropped the UMD bundle this no-build page needs |

## 9. What could not be verified without a browser

Everything requiring an actual rendering pipeline, real network conditions, or device-specific JS engine behavior is **not** claimed here and is left blank in §6 for a live run: worker compute time under real CPU contention, GPU texture upload + compositor paint time, DevTools 4G-throttled first paint, phone-specific numbers, and `performance.memory` (Chrome-only; not exposed by this sandbox's Node environment at all, and not fabricable). What *was* verified without a browser: every byte-level and JSON-level claim about the exporter and fixtures (§5.1), every line of `geom.js`'s topology logic via a dedicated Node test file with no d3 dependency (§5.1), JS syntax validity of all three browser scripts via `node --check`, the exact d3-contour v4.0.3 API and its row-major `values[y*dx+x]` indexing (read directly from the pinned package's source, matching `geom.js`'s documented convention), and every factual claim in §7 by fetching the actual pinned style-spec JSON and the actual MapLibre GitHub issue/changelog rather than citing them from memory.

## 10. Verdict — **placeholder, pending §6**

- If the live §6 rows meet all three pass criteria (slider→repaint median < 100 ms, first paint < 1.5 s on throttled 4G, valid topology) on the phone row specifically: **adopt browser Worker + canvas** for v2.0's constraint algebra; it is the $0-serving-cost path synthesis §3.2 already prefers, and this gate would confirm it holds up on the weakest device tested.
- If the phone row fails any criterion: **fall back to a server-rendered mask** (the on-demand tier already planned in §3.2's architecture diagram) for that device class, and re-test whether reducing layer count or grid resolution brings the Worker path back into budget before committing to server rendering everywhere.
- Not yet decided either way — **no number in §6 has been measured in a live browser as of this writing.**
