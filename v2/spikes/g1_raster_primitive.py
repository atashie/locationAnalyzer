"""Does the adopted layer primitive agree with exact engine times? (Codex pass-4 H1/H5)

The Phase 0 memo adopted "one multi-location arrival isochrone, format=geotiff" (method A) as the
way to build a category layer, on the strength of its speed, while `g1_valhalla_layer.py`'s own
`verify_multi_location` check reported a 1,635 s maximum difference against the per-location minimum
(method B). That check was diagnostic only and compared two resampled rasters to each other, so it
could not say which (if either) was wrong, nor how much of the difference was resampling.

This script adds the missing third leg: Valhalla's `sources_to_targets` matrix, which gives the
EXACT engine time from a cell centre to the nearest of the chosen POIs, with no raster involved.

For K POIs and N sampled cells it reports, in seconds:
    |A - exact|   method A raster error
    |B - exact|   method B raster error
    |A - B|       the difference the original check saw
and the classification agreement at the user thresholds, which is what the product actually needs.

Run from v2/ with Valhalla serving:
  uv run python spikes/g1_raster_primitive.py [--pois 3] [--cells 240]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import geopandas as gpd
import httpx
import numpy as np
from rasterio.io import MemoryFile
from rasterio.warp import Resampling, reproject

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ACCEPTED_PLACES, CONTROLLED_COSTING_OPTIONS, DATA, GRID, VALHALLA, append_results, stamp  # noqa: E402
from locfinder.places.categories import select_overture  # noqa: E402

MAX_MIN = 60
THRESHOLDS = [10, 15, 20, 25, 30, 45]
CHUNK_PAIRS = 2000


def iso_geotiff(locations, costing, controlled: bool) -> np.ndarray:
    body = {"locations": [{"lat": a, "lon": b} for a, b in locations], "costing": costing,
            "contours": [{"time": MAX_MIN}], "format": "geotiff", "reverse": True, "polygons": False}
    if controlled and CONTROLLED_COSTING_OPTIONS.get(costing):
        body["costing_options"] = {costing: CONTROLLED_COSTING_OPTIONS[costing]}
    r = httpx.post(f"{VALHALLA}/isochrone", json=body, timeout=600)
    r.raise_for_status()
    with MemoryFile(r.content) as mem, mem.open() as src:
        arr = src.read(1).astype("float64")
        bad = ~np.isfinite(arr) | (arr < 0)
        if src.nodata is not None:
            bad |= arr == src.nodata
        arr[bad] = np.inf
        dst = np.full((GRID.nrows, GRID.ncols), np.inf)
        reproject(arr, dst, src_transform=src.transform, src_crs=src.crs,
                  dst_transform=GRID.rasterio_profile()["transform"], dst_crs=GRID.crs,
                  resampling=Resampling.nearest, src_nodata=np.inf, dst_nodata=np.inf)
        meta = {"shape": list(arr.shape), "pixel_deg": [abs(src.transform.a), abs(src.transform.e)]}
    return dst, meta


def matrix_min(sources, targets, costing, controlled: bool) -> np.ndarray:
    per = max(1, CHUNK_PAIRS // max(len(targets), 1))
    out = np.full(len(sources), np.inf)
    for i in range(0, len(sources), per):
        chunk = sources[i:i + per]
        body = {"sources": [{"lat": a, "lon": b} for a, b in chunk],
                "targets": [{"lat": a, "lon": b} for a, b in targets], "costing": costing}
        if controlled and CONTROLLED_COSTING_OPTIONS.get(costing):
            body["costing_options"] = {costing: CONTROLLED_COSTING_OPTIONS[costing]}
        r = httpx.post(f"{VALHALLA}/sources_to_targets", json=body, timeout=600)
        r.raise_for_status()
        for k, row in enumerate(r.json()["sources_to_targets"]):
            times = [c["time"] for c in row if c.get("time") is not None]
            out[i + k] = min(times) if times else np.inf
    return out


def describe(label: str, d: np.ndarray) -> str:
    if d.size == 0:
        return f"| {label} | 0 | - | - | - | - |"
    return (f"| {label} | {d.size} | {np.median(d):.0f} | {np.percentile(d, 90):.0f} | "
            f"{d.max():.0f} | {(d > 60).mean():.1%} |")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--category", default="grocery")
    ap.add_argument("--mode", default="walk", choices=["walk", "bike", "drive"])
    ap.add_argument("--pois", type=int, default=3)
    ap.add_argument("--cells", type=int, default=240)
    ap.add_argument("--controlled", action="store_true", default=True)
    args = ap.parse_args()
    costing = {"walk": "pedestrian", "bike": "bicycle", "drive": "auto"}[args.mode]
    rng = np.random.default_rng(17)

    places = gpd.read_parquet(ACCEPTED_PLACES)
    sel = select_overture(places, args.category).to_crs(GRID.crs)
    cent = sel.geometry.centroid.to_crs("EPSG:4326")
    pts = [(float(y), float(x)) for x, y in zip(cent.x, cent.y)][: args.pois]

    a_raster, a_meta = iso_geotiff(pts, costing, args.controlled)
    b_raster = np.full_like(a_raster, np.inf)
    b_metas = []
    for p in pts:
        r, m = iso_geotiff([p], costing, args.controlled)
        b_raster = np.minimum(b_raster, r)
        b_metas.append(m)

    # sample cells reachable in EITHER raster, so one-sided cases are included
    cand = np.flatnonzero(np.isfinite(a_raster.ravel()) | np.isfinite(b_raster.ravel()))
    idx = rng.choice(cand, size=min(args.cells, cand.size), replace=False)
    lons, lats = GRID.cell_centers_lonlat()
    sources = [(float(lats.ravel()[i]), float(lons.ravel()[i])) for i in idx]
    exact = matrix_min(sources, pts, costing, args.controlled)

    A, B = a_raster.ravel()[idx], b_raster.ravel()[idx]
    fin = np.isfinite(exact)
    dA = np.abs(A[fin & np.isfinite(A)] - exact[fin & np.isfinite(A)])
    dB = np.abs(B[fin & np.isfinite(B)] - exact[fin & np.isfinite(B)])
    both = np.isfinite(A) & np.isfinite(B)
    dAB = np.abs(A[both] - B[both])

    lines = [f"### Raster primitive vs exact engine times ({stamp()}): {args.category} / {args.mode}, {len(pts)} POIs",
             f"method A grid {a_meta['shape']} at {a_meta['pixel_deg'][0]:.4f}° x {a_meta['pixel_deg'][1]:.4f}°; "
             f"method B grids {[m['shape'] for m in b_metas]}; {len(sources)} cells sampled from the reachable union of both rasters; "
             "exact = `sources_to_targets` minimum over the same POIs (no raster).", "",
             "| difference (seconds) | n | median | p90 | max | share > 60 s |", "|---|---|---|---|---|---|",
             describe("A (multi-location) vs exact", dA), describe("B (per-POI min) vs exact", dB),
             describe("A vs B (the original check)", dAB), "",
             f"One-sided reachability among sampled cells: exact unreachable {int((~fin).sum())}, "
             f"A unreachable {int((~np.isfinite(A)).sum())}, B unreachable {int((~np.isfinite(B)).sum())}.", "",
             "Threshold classification against exact (the product's actual question):", "",
             "| T min | A agrees | B agrees | A false-in | A false-out | B false-in | B false-out |", "|---|---|---|---|---|---|---|"]
    for T in THRESHOLDS:
        t = T * 60.0
        ex_in = fin & (exact <= t)
        ex_out = ~ex_in
        for_rows = []
        for X in (A, B):
            x_in = np.isfinite(X) & (X <= t)
            agree = ((x_in & ex_in) | (~x_in & ex_out)).mean()
            fi = (x_in & ex_out).sum() / max(ex_out.sum(), 1)
            fo = (~x_in & ex_in).sum() / max(ex_in.sum(), 1)
            for_rows.append((agree, fi, fo))
        (aa, afi, afo), (ba, bfi, bfo) = for_rows
        lines.append(f"| {T} | {aa:.1%} | {ba:.1%} | {afi:.1%} | {afo:.1%} | {bfi:.1%} | {bfo:.1%} |")
    text = "\n".join(lines)
    print(text)
    append_results("g1-routing.md", text)
    (DATA / f"raster_primitive_{args.category}_{args.mode}.json").write_text(
        json.dumps({"idx": idx.tolist(), "A": A.tolist(), "B": B.tolist(), "exact": exact.tolist(),
                    "a_meta": a_meta, "b_metas": b_metas}, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
