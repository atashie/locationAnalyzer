"""Gate G1 accuracy test with EXACT pair times: own-graph seconds at sampled grid cells
versus Valhalla `sources_to_targets` minimum over all category POIs.

Why: the GeoTIFF layer comparison mixes model error with grid misregistration (Valhalla's
isochrone grid is 0.001-0.002 deg with a per-request origin). A matrix gives exact engine
times for the same cell centre and the same destination set, so the residual is model
error plus snapping differences only (Codex pass 3 H7/H9).

Sampling: cells stratified by the OWN layer's minutes into bands around the user thresholds
(8-12, 13-17, 18-22, 23-27, 28-32, 40-50 min) plus cells the own layer calls unreachable
within 60 min but Valhalla might reach (checked separately). Pass criterion per band
(owner decision 12): median abs error <= 0.10*T, p90 <= 0.20*T.

Run from v2/ with Valhalla serving:
  uv run python spikes/g1_matrix_compare.py grocery walk [--controlled] [--per-band 100]
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (ACCEPTED_PLACES, CONTROLLED_COSTING_OPTIONS, GRID, LAYERS, METRO, VALHALLA,  # noqa: E402
                     VALHALLA_COSTING, append_results, layer_path, stamp)
from locfinder.places.categories import select_overture  # noqa: E402

BANDS = {10: (8, 12), 15: (13, 17), 20: (18, 22), 25: (23, 27), 30: (28, 32), 45: (40, 50)}
CHUNK = 8  # sources per matrix request; Valhalla caps sources x targets at 2500 pairs by default (8 x 285 = 2280)


def matrix_min_seconds(sources, targets, costing, controlled) -> np.ndarray:
    """Minimum travel time (s) from each source to any target. inf where none reachable."""
    out = np.full(len(sources), np.inf)
    for i in range(0, len(sources), CHUNK):
        chunk = sources[i:i + CHUNK]
        body = {"sources": [{"lat": a, "lon": b} for a, b in chunk],
                "targets": [{"lat": a, "lon": b} for a, b in targets], "costing": costing}
        if controlled and CONTROLLED_COSTING_OPTIONS.get(costing):
            body["costing_options"] = {costing: CONTROLLED_COSTING_OPTIONS[costing]}
        r = httpx.post(f"{VALHALLA}/sources_to_targets", json=body, timeout=600)
        if r.status_code != 200:
            raise RuntimeError(f"matrix failed: {r.status_code} {r.text[:200]}")
        rows = r.json()["sources_to_targets"]
        for k, row in enumerate(rows):
            times = [c["time"] for c in row if c.get("time") is not None]
            out[i + k] = min(times) if times else np.inf
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("category")
    ap.add_argument("mode", choices=["walk", "bike", "drive"])
    ap.add_argument("--controlled", action="store_true")
    ap.add_argument("--per-band", type=int, default=100)
    ap.add_argument("--seed", type=int, default=3)
    args = ap.parse_args()
    costing = VALHALLA_COSTING[args.mode]
    rng = np.random.default_rng(args.seed)

    own_path = layer_path("own", args.category, args.mode, ".npy")
    if not own_path.exists():
        raise SystemExit(f"missing {own_path.name} for metro {METRO.name}; build the layer first "
                         f"(a leftover array from another metro must not be paired with these coordinates)")
    own = np.load(own_path).astype(np.float64)
    if own.shape != (GRID.nrows, GRID.ncols):
        raise SystemExit(f"{own_path.name} is {own.shape} but metro {METRO.name} grid is "
                         f"{(GRID.nrows, GRID.ncols)}: wrong metro's layer (Codex pass 5 M1)")
    own_min = own / 60.0
    lons, lats = GRID.cell_centers_lonlat()
    places = gpd.read_parquet(ACCEPTED_PLACES)
    sel = select_overture(places, args.category)
    cent = sel.geometry.centroid
    targets = [(float(y), float(x)) for x, y in zip(cent.x, cent.y)]

    # stratified sample of cells by own minutes
    picks = {}
    for T, (lo, hi) in BANDS.items():
        idx = np.flatnonzero(np.isfinite(own_min) & (own_min >= lo) & (own_min <= hi))
        if len(idx) == 0:
            continue
        picks[T] = rng.choice(idx, size=min(args.per_band, len(idx)), replace=False)
    all_idx = np.concatenate(list(picks.values()))
    sources = [(float(lats.ravel()[i]), float(lons.ravel()[i])) for i in all_idx]
    print(f"{args.category}/{args.mode}: {len(sources)} sampled cells x {len(targets)} POIs ({costing}{' controlled' if args.controlled else ''})")

    t0 = time.perf_counter()
    ref = matrix_min_seconds(sources, targets, costing, args.controlled)
    dt = time.perf_counter() - t0
    ref_min = ref / 60.0
    own_s = own_min.ravel()[all_idx]

    lines = [f"### G1 matrix comparison ({stamp()}): {args.category} / {args.mode}, metro {METRO.name}{' (controlled)' if args.controlled else ''}",
             f"{len(sources)} cells stratified by own-layer minutes; Valhalla `sources_to_targets` min over {len(targets)} POIs; matrix time {dt:.1f} s",
             "", "| T min | band (own min) | n | ref unreachable | median abs err min | p90 abs err min | median/T | p90/T | own faster % | PASS (acc) |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    verdicts = {}
    pos = 0
    for T, idx in picks.items():
        n = len(idx)
        o = own_s[pos:pos + n]
        r = ref_min[pos:pos + n]
        pos += n
        fin = np.isfinite(r)
        if fin.sum() < 20:
            lines.append(f"| {T} | {BANDS[T]} | {n} | {int((~fin).sum())} | - | - | - | - | - | n/a |")
            continue
        err = np.abs(o[fin] - r[fin])
        med, p90 = float(np.median(err)), float(np.percentile(err, 90))
        faster = float((o[fin] < r[fin]).mean())
        ok = med <= 0.10 * T and p90 <= 0.20 * T
        verdicts[T] = ok
        lines.append(f"| {T} | {BANDS[T]} | {n} | {int((~fin).sum())} | {med:.1f} | {p90:.1f} | {med / T:.2f} | {p90 / T:.2f} | {faster:.0%} | {'PASS' if ok else 'FAIL'} |")
    bias = float(np.nanmedian(own_s[np.isfinite(ref_min)] - ref_min[np.isfinite(ref_min)]))
    lines += ["", f"Signed median (own - Valhalla): {bias:+.1f} min over all finite samples (negative = own model is faster/optimistic).",
              "Residual = speed model + snapping/access-leg differences (both engines snap the cell centre); no grid misregistration."]
    text = "\n".join(lines)
    print(text)
    append_results("g1-routing.md", text)
    layer_path("matrix", args.category, args.mode + ("_controlled" if args.controlled else ""), ".json").write_text(
        json.dumps({"idx": all_idx.tolist(), "own_min": own_s.tolist(), "ref_min": ref_min.tolist(), "bands": {str(k): len(v) for k, v in picks.items()}}),
        encoding="utf-8")


if __name__ == "__main__":
    main()
