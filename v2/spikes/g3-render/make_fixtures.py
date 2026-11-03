"""Write SYNTHETIC fixtures for the G3 browser-rendering spike.

These are NOT routing outputs. Each layer is a smooth "minutes to nearest of k
random points" field (equirectangular distance / mode speed) with a few 255
(nodata) patches, in exactly the byte layout the real export script will use:

    manifest.json  {"nrows", "ncols", "bounds_wgs84": [W, S, E, N], "nodata": 255,
                    "units": "minutes", "layers": [{"id", "label", "file"}, ...]}
    <layer>.bin    raw uint8, row-major, nrows*ncols bytes, row 0 = north edge,
                   value = minutes 0..254, 255 = nodata / unreachable

Run from anywhere (output goes next to this file):
    cd v2 && uv run python spikes/g3-render/make_fixtures.py
    python make_fixtures.py        # plain Python 3 + numpy also works

Deterministic (seeded); re-running overwrites identical bytes.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np

NROWS = 401
NCOLS = 550
BOUNDS = [-79.15, 35.80, -78.55, 36.15]  # west, south, east, north (WGS84)
NODATA = 255
SEED = 20261103

# (id, label, number of random amenity points, speed in metres per minute)
LAYERS = [
    ("grocery_walk", "Grocery (walk)", 60, 80.0),
    ("park_walk", "Park (walk)", 90, 80.0),
    ("coffee_walk", "Coffee (walk)", 70, 80.0),
    ("pharmacy_bike", "Pharmacy (bike)", 40, 250.0),
    ("school_drive", "School (drive)", 25, 700.0),
    ("transit_walk", "Transit stop (walk)", 120, 80.0),
]

OUT_DIR = Path(__file__).resolve().parent / "fixtures"


def cell_centres() -> tuple[np.ndarray, np.ndarray]:
    """Lon/lat of every cell centre; row 0 is the north edge."""
    west, south, east, north = BOUNDS
    dlon = (east - west) / NCOLS
    dlat = (north - south) / NROWS
    lon = west + (np.arange(NCOLS) + 0.5) * dlon
    lat = north - (np.arange(NROWS) + 0.5) * dlat
    return np.meshgrid(lon, lat)  # each (NROWS, NCOLS)


def minutes_field(
    rng: np.random.Generator,
    lon: np.ndarray,
    lat: np.ndarray,
    n_points: int,
    speed_m_per_min: float,
) -> np.ndarray:
    west, south, east, north = BOUNDS
    pts_lon = rng.uniform(west, east, n_points)
    pts_lat = rng.uniform(south, north, n_points)
    lat0 = math.radians((south + north) / 2)
    m_per_deg_lat = 111_320.0
    m_per_deg_lon = 111_320.0 * math.cos(lat0)
    best = np.full(lon.shape, np.inf, dtype=np.float64)
    for plon, plat in zip(pts_lon, pts_lat):
        dx = (lon - plon) * m_per_deg_lon
        dy = (lat - plat) * m_per_deg_lat
        np.minimum(best, np.hypot(dx, dy), out=best)
    # Straight-line distance understates network distance; scale by a detour factor.
    minutes = best * 1.3 / speed_m_per_min
    return minutes


def nodata_patches(rng: np.random.Generator, lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    """A few elliptical 255 patches (lakes / unreachable islands) per layer."""
    west, south, east, north = BOUNDS
    mask = np.zeros(lon.shape, dtype=bool)
    for _ in range(rng.integers(2, 5)):
        c_lon = rng.uniform(west, east)
        c_lat = rng.uniform(south, north)
        r_lon = rng.uniform(0.01, 0.04)
        r_lat = rng.uniform(0.008, 0.03)
        mask |= ((lon - c_lon) / r_lon) ** 2 + ((lat - c_lat) / r_lat) ** 2 <= 1.0
    return mask


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    lon, lat = cell_centres()

    manifest = {
        "nrows": NROWS,
        "ncols": NCOLS,
        "bounds_wgs84": BOUNDS,
        "nodata": NODATA,
        "units": "minutes",
        "layers": [],
        # Extra keys beyond the contract, so the page can label the data honestly.
        "synthetic": True,
        "generator": "v2/spikes/g3-render/make_fixtures.py",
        "seed": SEED,
        "note": "SYNTHETIC distance fields, not routing output. Shape matches the real export contract.",
    }

    print(f"writing fixtures to {OUT_DIR}")
    for layer_id, label, n_points, speed in LAYERS:
        minutes = minutes_field(rng, lon, lat, n_points, speed)
        values = np.clip(np.rint(minutes), 0, 254).astype(np.uint8)
        values[nodata_patches(rng, lon, lat)] = NODATA
        assert values.shape == (NROWS, NCOLS) and values.dtype == np.uint8
        data = np.ascontiguousarray(values).tobytes(order="C")
        assert len(data) == NROWS * NCOLS
        fname = f"{layer_id}.bin"
        (OUT_DIR / fname).write_bytes(data)
        manifest["layers"].append({"id": layer_id, "label": label, "file": fname})
        n_nodata = int((values == NODATA).sum())
        reachable = values[values != NODATA]
        print(
            f"  {fname:22s} {len(data):>7d} bytes  min={int(reachable.min()):3d} "
            f"median={int(np.median(reachable)):3d} max={int(reachable.max()):3d} "
            f"nodata={n_nodata} ({100 * n_nodata / values.size:.1f}%)  "
            f"sha256={hashlib.sha256(data).hexdigest()[:12]}"
        )

    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"  manifest.json          layers={len(manifest['layers'])} grid={NROWS}x{NCOLS} bounds={BOUNDS}")


if __name__ == "__main__":
    main()
