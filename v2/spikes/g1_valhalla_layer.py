"""Reference layer for Gate G1: seconds-to-nearest-<category> by Valhalla ARRIVAL
isochrones (reverse=true), resampled onto the frozen grid.

Method A: one multi-location arrival isochrone with format=geotiff (needs
service_limits.isochrone.max_locations raised in valhalla.json; see infra/valhalla/patch_limits.py).
Method B: per-POI GeoTIFF arrival isochrones combined by per-cell minimum.
Method C (only if GeoTIFF is unsupported): contour bracketing at 5-minute steps,
rasterised with the upper bound (quantisation error up to 5 minutes, stated in the output).

Outputs (v2/data/layers/): valhalla_<cat>_<mode>[_controlled].tif (uint8 minutes),
.npy (float32 seconds, inf unreachable), and a results section appended to
docs/experiments/g1-routing.md.

Run from v2/:  uv run python spikes/g1_valhalla_layer.py grocery walk [--controlled] [--verify-multi]
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import time
from pathlib import Path

import geopandas as gpd
import httpx
import numpy as np
import rasterio
from rasterio.features import rasterize
from rasterio.io import MemoryFile
from rasterio.warp import Resampling, reproject
from shapely.geometry import shape

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (ACCEPTED_PLACES, CONTROLLED_COSTING_OPTIONS, GRID, LAYERS, VALHALLA, VALHALLA_COSTING,  # noqa: E402
                     append_results, stamp)
from locfinder.grid import encode_minutes  # noqa: E402
from locfinder.places.categories import select_overture  # noqa: E402

MAX_MIN = 60


def isochrone_request(locations, costing, *, contours, fmt=None, controlled=False, polygons=True):
    body = {"locations": [{"lat": a, "lon": b} for a, b in locations], "costing": costing,
            "contours": contours, "reverse": True, "polygons": polygons}
    if fmt:
        body["format"] = fmt
    if controlled and CONTROLLED_COSTING_OPTIONS.get(costing):
        body["costing_options"] = {costing: CONTROLLED_COSTING_OPTIONS[costing]}
    return httpx.post(f"{VALHALLA}/isochrone", json=body, timeout=900)


def geotiff_to_grid_seconds(content: bytes) -> np.ndarray:
    """Valhalla's GeoTIFF band is seconds, north-up (Codex pass 3 confirmed from the
    serializer). Cells outside the max contour are nodata -> inf."""
    with MemoryFile(content) as mem, mem.open() as src:
        arr = src.read(1).astype("float64")
        nod = src.nodata
        bad = ~np.isfinite(arr) | (arr < 0)
        if nod is not None:
            bad |= arr == nod
        arr[bad] = np.inf
        dst = np.full((GRID.nrows, GRID.ncols), np.inf)
        reproject(arr, dst, src_transform=src.transform, src_crs=src.crs,
                  dst_transform=GRID.rasterio_profile()["transform"], dst_crs=GRID.crs,
                  resampling=Resampling.nearest, src_nodata=np.inf, dst_nodata=np.inf)
        tags = src.tags()
    return dst, tags


def method_a(points, costing, controlled):
    r = isochrone_request(points, costing, contours=[{"time": MAX_MIN}], fmt="geotiff", controlled=controlled, polygons=False)
    if r.status_code != 200:
        raise RuntimeError(f"multi-location geotiff failed: {r.status_code} {r.text[:200]}")
    return geotiff_to_grid_seconds(r.content)[0]


def method_b(points, costing, controlled, log_every=25):
    secs = np.full((GRID.nrows, GRID.ncols), np.inf)
    for i, p in enumerate(points):
        r = isochrone_request([p], costing, contours=[{"time": MAX_MIN}], fmt="geotiff", controlled=controlled, polygons=False)
        if r.status_code != 200:
            raise RuntimeError(f"geotiff unsupported or failed for {p}: {r.status_code} {r.text[:200]}")
        secs = np.minimum(secs, geotiff_to_grid_seconds(r.content)[0])
        if i % log_every == 0:
            print(f"  {i}/{len(points)}")
    return secs


def method_c(points, costing, controlled):
    """Contour bracketing: polygons at 5-minute steps; cell value = upper bound (seconds)."""
    secs = np.full((GRID.nrows, GRID.ncols), np.inf)
    transform = GRID.rasterio_profile()["transform"]
    for p in points:
        for t in range(MAX_MIN, 0, -5):  # largest first so smaller contours overwrite
            r = isochrone_request([p], costing, contours=[{"time": t}], controlled=controlled)
            if r.status_code != 200:
                continue
            geoms = [shape(f["geometry"]) for f in r.json().get("features", []) if f["geometry"]["type"].endswith("Polygon")]
            if not geoms:
                continue
            gs = gpd.GeoSeries(geoms, crs="EPSG:4326").to_crs(GRID.crs)
            mask = rasterize([(g, 1) for g in gs], out_shape=(GRID.nrows, GRID.ncols), transform=transform, fill=0, dtype="uint8").astype(bool)
            secs[mask] = np.minimum(secs[mask], t * 60.0)
    return secs


def verify_multi_location(points, costing, controlled):
    p2 = points[:2]
    multi = method_a(p2, costing, controlled)
    single = np.minimum(method_b([p2[0]], costing, controlled, log_every=10**9), method_b([p2[1]], costing, controlled, log_every=10**9))
    both = np.isfinite(multi) & np.isfinite(single)
    diff = np.abs(multi[both] - single[both])
    return {"cells_both": int(both.sum()), "one_sided": int((np.isfinite(multi) ^ np.isfinite(single)).sum()),
            "max_abs_diff_s": float(diff.max()) if diff.size else None, "frac_diff_gt_60s": float((diff > 60).mean()) if diff.size else None}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("category")
    ap.add_argument("mode", choices=["walk", "bike", "drive"])
    ap.add_argument("--controlled", action="store_true", help="match our static speed profile (pedestrian 5.04 km/h)")
    ap.add_argument("--verify-multi", action="store_true", help="check multi-location minimum against per-location minimum")
    ap.add_argument("--max-pois", type=int, default=None)
    args = ap.parse_args()
    costing = VALHALLA_COSTING[args.mode]

    places = gpd.read_parquet(ACCEPTED_PLACES)
    sel = select_overture(places, args.category)
    cent = sel.geometry.centroid
    points = [(float(y), float(x)) for x, y in zip(cent.x, cent.y)]
    if args.max_pois:
        points = points[: args.max_pois]
    print(f"{args.category}/{args.mode}: {len(points)} Overture places (accepted artifact)")

    notes = []
    if args.verify_multi:
        try:
            notes.append("multi-location check: " + json.dumps(verify_multi_location(points, costing, args.controlled)))
        except Exception as e:  # noqa: BLE001
            notes.append(f"multi-location check failed: {e}")
        print(notes[-1])

    t0 = time.perf_counter()
    try:
        secs = method_a(points, costing, args.controlled)
        method = "A multi-location geotiff"
    except Exception as e_a:  # noqa: BLE001
        print("method A unavailable:", str(e_a)[:160])
        try:
            secs = method_b(points, costing, args.controlled)
            method = "B per-POI geotiff min"
        except Exception as e_b:  # noqa: BLE001
            print("method B unavailable:", str(e_b)[:160])
            secs = method_c(points, costing, args.controlled)
            method = "C contour bracketing (5-minute quantisation, upper bound)"
    dt = time.perf_counter() - t0

    suffix = "_controlled" if args.controlled else ""
    base = LAYERS / f"valhalla_{args.category}_{args.mode}{suffix}"
    np.save(base.with_suffix(".npy"), secs.astype(np.float32))
    arr = encode_minutes(secs)
    with rasterio.open(base.with_suffix(".tif"), "w", **GRID.rasterio_profile()) as dst:
        dst.write(arr, 1)
        dst.update_tags(engine="valhalla", method=method, category=args.category, mode=args.mode, costing=costing,
                        controlled=str(args.controlled), direction="arrival", max_min=str(MAX_MIN), built_s=f"{dt:.1f}", built_at=stamp())
    reach = float(np.isfinite(secs).mean())
    text = (f"### Valhalla reference layer: {args.category} / {args.mode}{suffix} ({stamp()})\n"
            f"- destinations: {len(points)} Overture places (release 2026-10-21.0, accepted artifact)\n"
            f"- method: {method}; build time {dt:.1f} s; reachable cells {reach:.1%} of {secs.size}\n"
            f"- costing: {costing}" + (f" with costing_options {CONTROLLED_COSTING_OPTIONS[costing]}" if args.controlled else " (engine defaults)") + "\n"
            + "".join(f"- {n}\n" for n in notes))
    print(text)
    append_results("g1-routing.md", text)


if __name__ == "__main__":
    main()
