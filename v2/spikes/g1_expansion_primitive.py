"""A third layer primitive: Valhalla `/expansion` edges + our own nearest-edge snapping.

Codex pass-4 H1/H5 and `g1_raster_primitive.py` showed that Valhalla's isochrone GeoTIFF
(either one multi-location request or a per-POI minimum) differs from exact engine times by a
median of ~88 s and a p90 of ~6 min, with 9-15% false exclusions at the user thresholds. The
raster is a smoothed contour product, not a per-cell time, so it cannot meet the owner's
tolerance on its own.

`/expansion` with `action=isochrone` returns the actual search tree: one LineString per settled
edge with its `duration` in seconds. Feeding those edges into the snapping/interpolation code we
already ported and tested (`locfinder.traveltime.snap`) gives a per-cell time from Valhalla's own
costing, at edge resolution rather than raster resolution.

This compares all three primitives against the same exact `sources_to_targets` values on the same
sampled cells (reusing v2/data/raster_primitive_<cat>_<mode>.json so the comparison is paired).

Run from v2/ with Valhalla serving, after g1_raster_primitive.py:
  uv run python spikes/g1_expansion_primitive.py --category grocery --mode walk --pois 3
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import geopandas as gpd
import httpx
import numpy as np
import shapely
from pyproj import Transformer
from shapely.geometry import LineString

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ACCEPTED_PLACES, CONTROLLED_COSTING_OPTIONS, DATA, GRID, VALHALLA, append_results, stamp  # noqa: E402
from locfinder.places.categories import select_overture  # noqa: E402
from locfinder.traveltime.speeds import access_speed_mps  # noqa: E402

MAX_MIN = 60
THRESHOLDS = [10, 15, 20, 25, 30, 45]


def expansion_edges(locations, costing, controlled: bool, minutes: int = MAX_MIN):
    body = {"locations": [{"lat": a, "lon": b} for a, b in locations], "costing": costing,
            "contours": [{"time": minutes}], "action": "isochrone", "reverse": True,
            "skip_opposites": True, "expansion_properties": ["duration", "distance"]}
    if controlled and CONTROLLED_COSTING_OPTIONS.get(costing):
        body["costing_options"] = {costing: CONTROLLED_COSTING_OPTIONS[costing]}
    t0 = time.perf_counter()
    r = httpx.post(f"{VALHALLA}/expansion", json=body, timeout=900)
    r.raise_for_status()
    dt = time.perf_counter() - t0
    j = r.json()
    feats = j["features"]
    to_utm = Transformer.from_crs("EPSG:4326", GRID.crs, always_xy=True)
    geoms, durs = [], []
    for f in feats:
        coords = f["geometry"]["coordinates"]
        if len(coords) < 2:
            continue
        xs, ys = to_utm.transform([c[0] for c in coords], [c[1] for c in coords])
        geoms.append(LineString(list(zip(xs, ys))))
        durs.append(float(f["properties"]["duration"]))
    return geoms, np.asarray(durs, dtype=np.float64), dt


def cell_seconds_from_expansion(geoms, durs, xs, ys, *, mode: str, max_access_m: float = 200.0) -> np.ndarray:
    """Nearest expansion edge gives the settled arrival time; add the off-network access leg.

    The expansion reports one duration per settled edge, so within-edge position is not resolved;
    the residual is bounded by the edge's own traversal time, which is small for OSM-simplified
    urban edges and is reported alongside the result."""
    tree = shapely.STRtree(geoms)
    pts = shapely.points(np.asarray(xs).ravel(), np.asarray(ys).ravel())
    nearest = tree.nearest(pts)
    arr = np.empty(len(geoms), dtype=object)
    arr[:] = geoms
    access_m = shapely.distance(pts, arr[nearest])
    total = durs[nearest] + access_m / access_speed_mps(mode)
    total = np.where(access_m > max_access_m, np.inf, total)
    return total.reshape(np.shape(xs))


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
    args = ap.parse_args()
    costing = {"walk": "pedestrian", "bike": "bicycle", "drive": "auto"}[args.mode]

    paired = DATA / f"raster_primitive_{args.category}_{args.mode}.json"
    if not paired.exists():
        raise SystemExit(f"run g1_raster_primitive.py first (missing {paired})")
    saved = json.loads(paired.read_text(encoding="utf-8"))
    idx = np.asarray(saved["idx"], dtype=np.int64)
    A = np.asarray(saved["A"], dtype=np.float64)
    B = np.asarray(saved["B"], dtype=np.float64)
    exact = np.asarray(saved["exact"], dtype=np.float64)

    places = gpd.read_parquet(ACCEPTED_PLACES)
    sel = select_overture(places, args.category).to_crs(GRID.crs)
    cent = sel.geometry.centroid.to_crs("EPSG:4326")
    pts = [(float(y), float(x)) for x, y in zip(cent.x, cent.y)][: args.pois]

    geoms, durs, dt = expansion_edges(pts, costing, True)
    xs, ys = GRID.cell_centers_xy()
    E_full = cell_seconds_from_expansion(geoms, durs, xs, ys, mode=args.mode)
    E = E_full.ravel()[idx]

    edge_len = np.array([g.length for g in geoms])
    fin = np.isfinite(exact)
    dE = np.abs(E[fin & np.isfinite(E)] - exact[fin & np.isfinite(E)])
    dA = np.abs(A[fin & np.isfinite(A)] - exact[fin & np.isfinite(A)])
    dB = np.abs(B[fin & np.isfinite(B)] - exact[fin & np.isfinite(B)])
    signed = E[fin & np.isfinite(E)] - exact[fin & np.isfinite(E)]

    lines = [f"### Expansion primitive vs raster primitives ({stamp()}): {args.category} / {args.mode}, {len(pts)} POIs",
             f"`/expansion action=isochrone reverse=true` returned **{len(geoms)} settled edges** in {dt:.2f} s "
             f"(edge length median {np.median(edge_len):.0f} m, p90 {np.percentile(edge_len, 90):.0f} m). Cells snapped with "
             "`locfinder.traveltime.snap`'s nearest-edge logic plus the modal access leg. Same {n} cells and same exact "
             "`sources_to_targets` values as the raster test, so the three rows are paired.".replace("{n}", str(len(idx))), "",
             "| difference from exact (seconds) | n | median | p90 | max | share > 60 s |", "|---|---|---|---|---|---|",
             describe("**expansion + our snapping**", dE),
             describe("A multi-location GeoTIFF", dA),
             describe("B per-POI GeoTIFF min", dB), "",
             f"Expansion signed median {np.median(signed):+.0f} s (positive = our value is later/more conservative than exact).", "",
             "Threshold classification against exact:", "",
             "| T min | expansion agrees | A agrees | B agrees | expansion false-in | expansion false-out |", "|---|---|---|---|---|---|"]
    for T in THRESHOLDS:
        t = T * 60.0
        ex_in = fin & (exact <= t)
        ex_out = ~ex_in
        row = []
        for X in (E, A, B):
            x_in = np.isfinite(X) & (X <= t)
            row.append(((x_in & ex_in) | (~x_in & ex_out)).mean())
        e_in = np.isfinite(E) & (E <= t)
        fi = (e_in & ex_out).sum() / max(ex_out.sum(), 1)
        fo = (~e_in & ex_in).sum() / max(ex_in.sum(), 1)
        lines.append(f"| {T} | {row[0]:.1%} | {row[1]:.1%} | {row[2]:.1%} | {fi:.1%} | {fo:.1%} |")
    text = "\n".join(lines)
    print(text)
    append_results("g1-routing.md", text)
    (DATA / f"expansion_primitive_{args.category}_{args.mode}.json").write_text(
        json.dumps({"idx": idx.tolist(), "E": E.tolist(), "exact": exact.tolist(), "n_edges": len(geoms),
                    "expansion_seconds": dt}), encoding="utf-8")


if __name__ == "__main__":
    main()
