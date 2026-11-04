"""Phase 1 S1.4, part three: is the expansion tree's reconstructed time at a NODE the same number
Valhalla's router gives for that node?

S1.4 split the residual by access distance. For walk it was entirely our access leg — on-network
the reconstruction matched `sources_to_targets` to a median of 1.5 s. For **drive** it did not:
the nearly-on-network band still showed **+50.9 s** with only 1.7 s of access charge, so something
other than snapping is responsible.

This isolates it. Instead of sampling grid cells, sample the expansion's own **node coordinates**
and ask `sources_to_targets` for the time from exactly those coordinates to the same POIs. No grid,
no access leg, no within-edge interpolation — just the reconstructed node time against the router's
own answer for the same point.

If they agree, the drive residual lives in snapping or interpolation. If they disagree, the
expansion tree and the router disagree about the route, and the primitive inherits that.

Run from v2/ with Valhalla serving:
  LOCFINDER_METRO=slice uv run python spikes/s1_expansion_node_fidelity.py --mode drive --pois 3
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import geopandas as gpd
import httpx
import numpy as np
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (ACCEPTED_PLACES, CONTROLLED_COSTING_OPTIONS, DATA, GRID, VALHALLA,  # noqa: E402
                     VALHALLA_COSTING, append_results, stamp)
from locfinder.places.categories import select_overture  # noqa: E402
from locfinder.traveltime.expansion import expansion_to_edge_index  # noqa: E402

MAX_MIN = 60
PROPS = ["duration", "distance", "edge_id", "pred_edge_id"]
CHUNK = 8


def expansion_request(locations, costing, *, skip_opposites: bool, minutes: int = MAX_MIN):
    body = {"locations": [{"lat": a, "lon": b} for a, b in locations], "costing": costing,
            "contours": [{"time": minutes}], "action": "isochrone", "reverse": True,
            "skip_opposites": skip_opposites, "expansion_properties": PROPS}
    if CONTROLLED_COSTING_OPTIONS.get(costing):
        body["costing_options"] = {costing: CONTROLLED_COSTING_OPTIONS[costing]}
    r = httpx.post(f"{VALHALLA}/expansion", json=body, timeout=1800)
    r.raise_for_status()
    return r.json()["features"]


def matrix_exact(sources_lonlat, targets_latlon, costing) -> np.ndarray:
    out = np.full(len(sources_lonlat), np.inf)
    tg = [{"lat": a, "lon": b} for a, b in targets_latlon]
    for i in range(0, len(sources_lonlat), CHUNK):
        chunk = sources_lonlat[i:i + CHUNK]
        body = {"sources": [{"lat": la, "lon": lo} for lo, la in chunk], "targets": tg,
                "costing": costing}
        if CONTROLLED_COSTING_OPTIONS.get(costing):
            body["costing_options"] = {costing: CONTROLLED_COSTING_OPTIONS[costing]}
        r = httpx.post(f"{VALHALLA}/sources_to_targets", json=body, timeout=900)
        r.raise_for_status()
        for j, row in enumerate(r.json()["sources_to_targets"]):
            vals = [c["time"] for c in row if c.get("time") is not None]
            if vals:
                out[i + j] = float(min(vals))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--category", default="grocery")
    ap.add_argument("--mode", default="drive", choices=["walk", "bike", "drive"])
    ap.add_argument("--pois", type=int, default=3)
    ap.add_argument("--nodes", type=int, default=240)
    args = ap.parse_args()
    costing = VALHALLA_COSTING[args.mode]

    places = gpd.read_parquet(ACCEPTED_PLACES)
    sel = select_overture(places, args.category).to_crs(GRID.crs)
    cent = sel.geometry.centroid.to_crs("EPSG:4326")
    latlon = [(float(y), float(x)) for x, y in zip(cent.x, cent.y)][: args.pois]
    lonlat = [(lo, la) for la, lo in latlon]

    feats = expansion_request(latlon, costing, skip_opposites=False)
    rep: dict = {}
    idx, T = expansion_to_edge_index(feats, target_crs=GRID.crs, opposites_included=True,
                                     origins=lonlat, strict=False, report=rep)
    print(f"{rep}", flush=True)

    # node coordinates, taken from the geometries the index was built from
    node_xy: dict[int, tuple[float, float]] = {}
    for i, g in enumerate(idx.geoms):
        node_xy.setdefault(int(idx.start_idx[i]), g.coords[0])
        node_xy.setdefault(int(idx.end_idx[i]), g.coords[-1])
    finite = [n for n in node_xy if np.isfinite(T[n]) and T[n] > 0]
    rng = np.random.default_rng(20261104)
    pick = rng.choice(finite, size=min(args.nodes, len(finite)), replace=False)

    to_wgs = Transformer.from_crs(GRID.crs, "EPSG:4326", always_xy=True)
    xs = np.array([node_xy[int(n)][0] for n in pick])
    ys = np.array([node_xy[int(n)][1] for n in pick])
    lon, lat = to_wgs.transform(xs, ys)
    recon = np.array([T[int(n)] for n in pick], dtype=np.float64)
    exact = matrix_exact(list(zip(lon, lat)), latlon, costing)

    m = np.isfinite(exact) & np.isfinite(recon)
    signed = recon[m] - exact[m]
    out = {
        "mode": args.mode, "category": args.category, "pois": len(latlon),
        "nodes_sampled": int(m.sum()), "adapter_report": rep,
        "signed_median_s": float(np.median(signed)),
        "median_abs_s": float(np.median(np.abs(signed))),
        "p90_abs_s": float(np.percentile(np.abs(signed), 90)),
        "max_abs_s": float(np.abs(signed).max()),
        "share_recon_later": float((signed > 1.0).mean()),
        "share_recon_earlier": float((signed < -1.0).mean()),
        "recon_median_s": float(np.median(recon[m])),
        "exact_median_s": float(np.median(exact[m])),
    }
    print(json.dumps(out, indent=1), flush=True)

    lines = [
        f"### S1.4 part three: reconstructed node times against the router ({stamp()}): "
        f"{args.category} / {args.mode}, {len(latlon)} POIs, {out['nodes_sampled']} nodes", "",
        "Sampled the expansion's **own node coordinates** and asked `sources_to_targets` for the "
        "time from exactly those points. No grid, no access leg, no within-edge interpolation, so "
        "this is the reconstruction against the router and nothing else.", "",
        f"- reconstructed median {out['recon_median_s']:.0f} s, router median "
        f"{out['exact_median_s']:.0f} s",
        f"- **signed median {out['signed_median_s']:+.1f} s**, median absolute "
        f"{out['median_abs_s']:.1f} s, p90 {out['p90_abs_s']:.1f} s, max {out['max_abs_s']:.0f} s",
        f"- reconstruction later on {out['share_recon_later']:.1%} of nodes, earlier on "
        f"{out['share_recon_earlier']:.1%}", "",
    ]
    text = "\n".join(lines)
    print("\n" + text, flush=True)
    append_results("g1-routing.md", text)
    (DATA / f"s1_node_fidelity_{args.category}_{args.mode}.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
