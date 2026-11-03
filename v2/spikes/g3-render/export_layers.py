"""Export REAL travel-time layers for the G3 browser-rendering spike.

Reads the uint8 minutes-to-nearest-grocery GeoTIFFs already on disk under
``v2/data/layers/`` (grid contract: ``v2/locfinder/grid.py``, UTM 17N, 100 m
cells, 550 x 401, NODATA=255), reprojects each to a regular WGS84 lon/lat
grid covering the Phase 0 slice bbox (west -79.15, south 35.80, east -78.55,
north 36.15), and writes the browser fixture format:

    fixtures/<id>.bin       raw row-major uint8, row 0 = north, nrows*ncols bytes
    fixtures/manifest.json  {nrows, ncols, bounds_wgs84:[w,s,e,n], nodata, units,
                              source, layers:[{id,label,file,engine,mode,category}]}

Run from the v2 directory:

    cd v2 && uv run python spikes/g3-render/export_layers.py

Layer selection
---------------
``data/layers/*.tif`` holds up to two engines (own-graph csgraph, Valhalla
arrival isochrones) x three modes (walk, bike, drive) for one category
(grocery), some with a "_controlled" suffix (a matched-speed-profile variant
built for the G1 own-vs-Valhalla comparison, not a different mode). For each
(engine, mode) pair we prefer the plain variant and fall back to "_controlled"
only when no plain variant exists for that pair (true today for
valhalla/bike, which only has ``valhalla_grocery_bike_controlled.tif``). This
is a selection rule, not a cherry-pick: it is deterministic and documented so
a re-run with different files on disk reproduces the same choice.

If fewer than 3 real (engine, mode) layers are found this script raises
(nothing to render). If between 3 and 5 are found, it pads up to 6 by adding
clearly-labelled DERIVED variants (a fixed minute scaling of an existing real
layer, re-clamped and re-NODATA'd) rather than inventing geometry; the
manifest marks each with ``"derived": true`` and a ``derived_from`` id. With 6
or more real layers (today: 7 on disk), no padding happens and the extra
layer(s) beyond the 6 selected are simply left unexported.

Reprojection and NODATA validity (research/10-codex-adversarial-review-pass3-plan.md
finding M4: "mask 255 explicitly, define validity on reprojection")
--------------------------------------------------------------------
``rasterio.warp.reproject`` is called with ``src_nodata=255, dst_nodata=255``
and nearest-neighbour resampling, so:
  * every source NODATA cell maps to NODATA minutes in the output (never 0,
    never interpolated into a bogus "reachable" value), and
  * every destination cell whose footprint falls outside the source raster's
    coverage (the source is a UTM rectangle; its reprojection into a lon/lat
    rectangle is not itself a rectangle, so the four corners cannot both be
    exact matches) is explicitly set to NODATA by rasterio, not left as
    whatever happened to be in the uninitialized destination array.
We allocate the destination array pre-filled with NODATA before calling
reproject (defensive: rasterio already does this for uncovered pixels, but an
explicitly-NODATA-filled destination removes any doubt that an uncovered
pixel could read as 0) and log the NODATA fraction before vs. after
reprojection so any edge effect is visible in the printed output and the doc.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.warp import Resampling, reproject

NODATA = 255
NROWS = 401
NCOLS = 550
BOUNDS_WGS84 = [-79.15, 35.80, -78.55, 36.15]  # west, south, east, north
DST_CRS = "EPSG:4326"
TARGET_LAYER_COUNT = 6  # matches synthesis §6 gate G3: "threshold six layers"
CATEGORY = "grocery"  # the only category present in data/layers today

SCRIPT_DIR = Path(__file__).resolve().parent          # v2/spikes/g3-render
V2_ROOT = SCRIPT_DIR.parents[1]                        # v2/
LAYERS_DIR = V2_ROOT / "data" / "layers"
OUT_DIR = SCRIPT_DIR / "fixtures"

# <engine>_<category>_<mode>[_controlled].tif
FILENAME_RE = re.compile(
    r"^(?P<engine>[a-z0-9]+)_(?P<category>[a-z0-9]+)_(?P<mode>walk|bike|drive)(?P<controlled>_controlled)?$"
)


@dataclass(frozen=True)
class RealLayer:
    engine: str
    mode: str
    category: str
    controlled: bool
    path: Path

    @property
    def key(self) -> tuple[str, str]:
        return (self.engine, self.mode)


def discover_real_layers() -> list[RealLayer]:
    found: list[RealLayer] = []
    if not LAYERS_DIR.is_dir():
        print(f"  (no such directory: {LAYERS_DIR})")
        return found
    for tif in sorted(LAYERS_DIR.glob("*.tif")):
        m = FILENAME_RE.match(tif.stem)
        if not m:
            continue
        found.append(
            RealLayer(
                engine=m.group("engine"),
                mode=m.group("mode"),
                category=m.group("category"),
                controlled=bool(m.group("controlled")),
                path=tif,
            )
        )
    return found


def select_layers(candidates: list[RealLayer]) -> list[RealLayer]:
    """One layer per (engine, mode): prefer the plain variant, else controlled."""
    by_key: dict[tuple[str, str], RealLayer] = {}
    for c in candidates:
        existing = by_key.get(c.key)
        if existing is None or (existing.controlled and not c.controlled):
            by_key[c.key] = c
    # Deterministic order: engine then mode.
    return sorted(by_key.values(), key=lambda c: (c.engine, c.mode))


def reproject_to_grid(src_path: Path) -> tuple[np.ndarray, dict]:
    dst_transform = from_bounds(*BOUNDS_WGS84, NCOLS, NROWS)
    dst = np.full((NROWS, NCOLS), NODATA, dtype=np.uint8)
    with rasterio.open(src_path) as src:
        src_arr = src.read(1)
        src_nodata_frac = float((src_arr == NODATA).mean())
        reproject(
            source=src_arr,
            destination=dst,
            src_transform=src.transform,
            src_crs=src.crs,
            src_nodata=NODATA,
            dst_transform=dst_transform,
            dst_crs=DST_CRS,
            dst_nodata=NODATA,
            resampling=Resampling.nearest,
        )
    dst_nodata_frac = float((dst == NODATA).mean())
    info = {
        "src_shape": (src_arr.shape if 'src_arr' in locals() else None),
        "src_nodata_frac": src_nodata_frac,
        "dst_nodata_frac": dst_nodata_frac,
    }
    return dst, info


def mode_label(mode: str) -> str:
    return {"walk": "walk", "bike": "bike", "drive": "drive"}.get(mode, mode)


def engine_label(engine: str) -> str:
    return {"own": "own-graph", "valhalla": "Valhalla"}.get(engine, engine)


def build_layer_entry(layer: RealLayer, variant_note: str = "") -> dict:
    layer_id = f"{layer.engine}_{layer.category}_{layer.mode}"
    suffix = f" ({variant_note})" if variant_note else (" [controlled]" if layer.controlled else "")
    label = f"{layer.category.capitalize()}, {mode_label(layer.mode)} ({engine_label(layer.engine)}){suffix}"
    return {
        "id": layer_id,
        "label": label,
        "file": f"{layer_id}.bin",
        "engine": layer.engine,
        "mode": layer.mode,
        "category": layer.category,
    }


def derive_padding_layer(base_arr: np.ndarray, base_entry: dict, index: int) -> tuple[np.ndarray, dict]:
    """Fabricate a clearly-labelled derived variant from a real layer to reach 6.

    Only used when fewer than 6 real (engine, mode) layers exist on disk.
    Scales finite minutes by a fixed factor (>1, so it reads as "a slower
    hypothetical profile", never a faster/shorter claim) and re-clamps; NODATA
    cells stay NODATA. This is synthetic derivation of a real layer, not an
    independent measurement, and the manifest says so explicitly.
    """
    scale = 1.25 + 0.25 * index  # 1.25, 1.50, 1.75, ... per padding slot
    out = base_arr.copy()
    finite = out != NODATA
    scaled = np.clip(np.rint(out[finite].astype(np.float64) * scale), 0, 254)
    out[finite] = scaled.astype(np.uint8)
    derived_id = f"derived_{base_entry['id']}_x{scale:.2f}".replace(".", "p")
    entry = {
        "id": derived_id,
        "label": f"{base_entry['label']} [DERIVED x{scale:.2f}, not independently routed]",
        "file": f"{derived_id}.bin",
        "engine": base_entry["engine"],
        "mode": base_entry["mode"],
        "category": base_entry["category"],
        "derived": True,
        "derived_from": base_entry["id"],
        "derived_scale": scale,
    }
    return out, entry


def clean_fixtures_dir() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for stale in OUT_DIR.glob("*.bin"):
        stale.unlink()


def main() -> int:
    print(f"v2 root:    {V2_ROOT}")
    print(f"layers dir: {LAYERS_DIR}")
    print(f"out dir:    {OUT_DIR}")

    candidates = discover_real_layers()
    print(f"found {len(candidates)} candidate GeoTIFF(s) matching the naming pattern:")
    for c in candidates:
        print(f"  {c.path.name:40s} engine={c.engine:9s} mode={c.mode:6s} controlled={c.controlled}")

    selected = select_layers(candidates)
    print(f"selected {len(selected)} layer(s), one per (engine, mode), preferring the plain variant:")
    for s in selected:
        print(f"  ({s.engine}, {s.mode}) -> {s.path.name}")

    if len(selected) < 3:
        print(
            f"ERROR: only {len(selected)} real layer(s) found under {LAYERS_DIR}; "
            "need at least 3. Run make_fixtures.py for a fully synthetic fixture set instead.",
            file=sys.stderr,
        )
        return 1

    clean_fixtures_dir()

    manifest_layers: list[dict] = []
    written_bytes: dict[str, int] = {}
    real_arrays: list[tuple[np.ndarray, dict]] = []

    for layer in selected:
        entry = build_layer_entry(layer)
        arr, info = reproject_to_grid(layer.path)
        real_arrays.append((arr, entry))
        data = np.ascontiguousarray(arr, dtype=np.uint8).tobytes(order="C")
        assert len(data) == NROWS * NCOLS, (
            f"{entry['id']}: byte count {len(data)} != nrows*ncols {NROWS * NCOLS}"
        )
        (OUT_DIR / entry["file"]).write_bytes(data)
        written_bytes[entry["id"]] = len(data)
        manifest_layers.append(entry)
        print(
            f"  wrote {entry['file']:45s} {len(data):>7d} bytes  "
            f"nodata src={info['src_nodata_frac']*100:5.1f}%  dst={info['dst_nodata_frac']*100:5.1f}%"
        )

    # Pad to TARGET_LAYER_COUNT with derived variants if we came up short.
    pad_index = 0
    while len(manifest_layers) < TARGET_LAYER_COUNT and real_arrays:
        base_arr, base_entry = real_arrays[pad_index % len(real_arrays)]
        derived_arr, derived_entry = derive_padding_layer(base_arr, base_entry, pad_index)
        data = np.ascontiguousarray(derived_arr, dtype=np.uint8).tobytes(order="C")
        assert len(data) == NROWS * NCOLS, (
            f"{derived_entry['id']}: byte count {len(data)} != nrows*ncols {NROWS * NCOLS}"
        )
        (OUT_DIR / derived_entry["file"]).write_bytes(data)
        written_bytes[derived_entry["id"]] = len(data)
        manifest_layers.append(derived_entry)
        print(f"  PADDED {derived_entry['file']:45s} {len(data):>7d} bytes  (derived from {derived_entry['derived_from']})")
        pad_index += 1

    if len(manifest_layers) > TARGET_LAYER_COUNT:
        # Only happens if select_layers() + padding ever exceeds the target; not expected today.
        manifest_layers = manifest_layers[:TARGET_LAYER_COUNT]

    manifest = {
        "nrows": NROWS,
        "ncols": NCOLS,
        "bounds_wgs84": BOUNDS_WGS84,
        "nodata": NODATA,
        "units": "minutes",
        "source": f"real, exported {date.today().isoformat()}",
        "synthetic": False,
        "generator": "v2/spikes/g3-render/export_layers.py",
        "note": (
            "Real Valhalla arrival-isochrone and own-graph csgraph minutes-to-nearest-grocery "
            "layers, reprojected from UTM 17N (EPSG:32617) 100 m cells to a WGS84 lon/lat grid "
            "with rasterio.warp.reproject (nearest, src_nodata=255, dst_nodata=255)."
        ),
        "layers": manifest_layers,
    }
    manifest_path = OUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    total_bytes = sum(written_bytes.values())
    expected_each = NROWS * NCOLS
    print(f"manifest.json: {len(manifest_layers)} layer(s), grid {NROWS}x{NCOLS}, bounds {BOUNDS_WGS84}")
    print(f"total bytes written: {total_bytes} ({len(manifest_layers)} x {expected_each})")
    assert total_bytes == len(manifest_layers) * expected_each
    for layer_id, nbytes in written_bytes.items():
        assert nbytes == expected_each, f"{layer_id}: {nbytes} != {expected_each}"

    print("OK: every fixture's byte count equals nrows*ncols.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
