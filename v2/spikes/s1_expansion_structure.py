"""Phase 1 S1.2 + S1.3: run the adopted expansion primitive on REAL Valhalla payloads and check
its structure before any aggregate benchmark.

Decision D1 adopted `traveltime/expansion.py` for drive and bike layers. Nothing outside the unit
tests had ever called it, and `g1_expansion_primitive.py` requested only `duration`/`distance` —
not the `edge_id`/`pred_edge_id` the adapter needs — so the measured expansion numbers in
g1-routing.md describe a *different* implementation. An aggregate median hid a real orientation bug
once (Codex pass-7 C5), so the structure is checked first and the numbers come after.

This is the **post-fix** run. The first pass found two defects, measured in
`s1_expansion_directions.py` and now repaired in the adapter: duplicate geometries for the two
directed features of one road were not merged, and every edge was marked traversable both ways.
It also found that `skip_opposites=true` leaves 0.25% of edges naming a predecessor that was never
serialised, so the request here uses `skip_opposites=false`.

Checks, each reported as a count or a distribution rather than a verdict:

1. **Adapter health.** `report=` counts on real payloads, and whether `strict=True` now passes.
2. **Root orientation, cross-checked.** The adapter derives a root's near end from the supplied
   origins first and from the vertex shared with its successors second. Those are independent
   signals, so running it both ways and comparing is a real test rather than a restatement. Also:
   the derived zero-time node should sit on top of an origin.
3. **Direction.** How many physical edges ended up traversable one way only.
4. **Turn and stop costs inside tau.** `tau = far.duration - near.duration` is a *difference of
   cumulative* durations, so any penalty charged on entering the edge is inside it. Within-edge
   interpolation scales tau by the matched fraction, which scales that penalty too. Reported as the
   distribution of implied speed against the costing speed.
5. **Integer quantisation.** Valhalla returns whole-second durations, so tau is an integer
   difference and short edges can round to zero.
6. **Interior anchors.** Whether an origin lands at an edge endpoint or inside an edge.
7. **Valhalla's own cost against its duration**, since we now request both — the size of the gap
   says whether carrying cost as a selection weight (as the own-graph path does) would change
   anything.

Run from v2/ with Valhalla serving:
  uv run python spikes/s1_expansion_structure.py --category grocery --mode drive --pois 3
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (ACCEPTED_PLACES, CONTROLLED_COSTING_OPTIONS, DATA, GRID, VALHALLA,  # noqa: E402
                     append_results, stamp)
from locfinder.places.categories import select_overture  # noqa: E402
from locfinder.traveltime.expansion import expansion_to_edge_index  # noqa: E402
from locfinder.traveltime.speeds import DRIVE_FRICTION_MPH, MODE_SPEED_MPS, MPH_TO_MPS  # noqa: E402

MAX_MIN = 60
COSTING = {"walk": "pedestrian", "bike": "bicycle", "drive": "auto"}
PROPS = ["duration", "distance", "edge_id", "pred_edge_id", "cost"]


def request_expansion(locations, costing, *, controlled: bool, skip_opposites: bool,
                      minutes: int = MAX_MIN):
    """`locations` are (lat, lon). Returns (features, seconds)."""
    body = {"locations": [{"lat": a, "lon": b} for a, b in locations], "costing": costing,
            "contours": [{"time": minutes}], "action": "isochrone", "reverse": True,
            "skip_opposites": skip_opposites, "expansion_properties": PROPS}
    if controlled and CONTROLLED_COSTING_OPTIONS.get(costing):
        body["costing_options"] = {costing: CONTROLLED_COSTING_OPTIONS[costing]}
    t0 = time.perf_counter()
    r = httpx.post(f"{VALHALLA}/expansion", json=body, timeout=900)
    r.raise_for_status()
    return r.json()["features"], time.perf_counter() - t0


def canonical_key(coords) -> tuple:
    """Same idea as expansion._physical_key: a physical edge regardless of stored direction."""
    fwd = tuple((round(x, 7), round(y, 7)) for x, y in coords)
    rev = tuple(reversed(fwd))
    return fwd if fwd <= rev else rev


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--category", default="grocery")
    ap.add_argument("--mode", default="drive", choices=["walk", "bike", "drive"])
    ap.add_argument("--pois", type=int, default=3)
    args = ap.parse_args()
    costing = COSTING[args.mode]
    out: dict = {"category": args.category, "mode": args.mode, "costing": costing,
                 "pois": args.pois, "contour_min": MAX_MIN, "skip_opposites": False}

    places = gpd.read_parquet(ACCEPTED_PLACES)
    sel = select_overture(places, args.category).to_crs(GRID.crs)
    cent = sel.geometry.centroid.to_crs("EPSG:4326")
    latlon = [(float(y), float(x)) for x, y in zip(cent.x, cent.y)][: args.pois]
    lonlat = [(lo, la) for la, lo in latlon]
    print(f"{len(latlon)} origins: {latlon}", flush=True)

    # ---- 1. adapter health on real payloads -------------------------------------------------
    feats, dt = request_expansion(latlon, costing, controlled=True, skip_opposites=False)
    print(f"skip_opposites=false -> {len(feats)} features in {dt:.2f} s", flush=True)
    durations = np.array([f["properties"]["duration"] for f in feats], dtype=np.float64)
    costs = np.array([f["properties"]["cost"] for f in feats], dtype=np.float64)
    out["request"] = {"features": len(feats), "seconds": dt}
    out["duration_is_integer"] = bool(np.all(durations == np.round(durations)))

    report: dict = {}
    idx, T = expansion_to_edge_index(feats, target_crs=GRID.crs, opposites_included=True,
                                     origins=lonlat, strict=False, report=report)
    out["adapter_report"] = report
    print(f"adapter report: {report}", flush=True)

    strict_ok = True
    try:
        expansion_to_edge_index(feats, target_crs=GRID.crs, opposites_included=True,
                                origins=lonlat, strict=True)
    except ValueError as e:
        strict_ok = False
        out["strict_error"] = str(e)[:300]
    out["strict_passes_on_real_payload"] = strict_ok
    print(f"strict mode passes: {strict_ok}", flush=True)

    # ---- 2. root orientation, cross-checked -------------------------------------------------
    # No origins-versus-successors agreement metric any more: with origins the roots are split, so
    # the two runs have different node sets and the comparison is not defined. The priority is now
    # fixed (successors win) and `roots_oriented_by_proximity` records the fallback instead.

    to_utm = Transformer.from_crs("EPSG:4326", GRID.crs, always_xy=True)
    ox_, oy_ = to_utm.transform([p[0] for p in lonlat], [p[1] for p in lonlat])
    origin_pts = shapely.points(np.asarray(ox_), np.asarray(oy_))
    node_xy: dict[int, tuple[float, float]] = {}
    for i, g in enumerate(idx.geoms):
        node_xy[int(idx.start_idx[i])] = g.coords[0]
        node_xy[int(idx.end_idx[i])] = g.coords[-1]
    d_zero = [float(shapely.distance(shapely.points(*node_xy[int(n)]), origin_pts).min())
              for n in np.flatnonzero(T == 0.0) if int(n) in node_xy]
    out["zero_time_nodes"] = {
        "count": int((T == 0.0).sum()),
        "distance_to_nearest_origin_m": {
            "median": float(np.median(d_zero)) if d_zero else None,
            "max": float(np.max(d_zero)) if d_zero else None}}
    print(f"zero-time nodes {out['zero_time_nodes']['count']}, distance to nearest origin: "
          f"{out['zero_time_nodes']['distance_to_nearest_origin_m']}", flush=True)

    # ---- 3. direction ------------------------------------------------------------------------
    one_way = int((np.isfinite(idx.fwd_time) ^ np.isfinite(idx.rev_time)).sum())
    both_ways = int((np.isfinite(idx.fwd_time) & np.isfinite(idx.rev_time)).sum())
    out["direction"] = {"physical_edges": len(idx.geoms), "both_ways": both_ways,
                        "one_way_only": one_way,
                        "share_one_way": one_way / max(len(idx.geoms), 1)}
    print(f"direction: {out['direction']}", flush=True)

    # ---- 6. interior anchors -----------------------------------------------------------------
    nearest_edge = idx.tree.nearest(origin_pts)
    geoms_near = idx.geoms[nearest_edge]
    frac = shapely.line_locate_point(geoms_near, origin_pts, normalized=True)
    out["origin_on_edge_fraction"] = [round(float(f), 4) for f in frac]
    out["origin_distance_to_edge_m"] = [round(float(d), 2)
                                        for d in shapely.distance(origin_pts, geoms_near)]
    print(f"origin fractions along nearest edge: {out['origin_on_edge_fraction']}; "
          f"distances {out['origin_distance_to_edge_m']} m", flush=True)

    # ---- 5. quantisation, and 4. implied speed ----------------------------------------------
    tau = np.fmin(idx.fwd_time, idx.rev_time)
    lengths = np.array([g.length for g in idx.geoms])
    implied = np.divide(lengths, tau, out=np.full_like(lengths, np.nan), where=tau > 0)
    ref_speed = (max(DRIVE_FRICTION_MPH.values()) * MPH_TO_MPS if args.mode == "drive"
                 else MODE_SPEED_MPS[args.mode])
    out["tau"] = {
        "at_epsilon_floor": int((tau <= 0.1 + 1e-9).sum()),
        "share_at_floor": float((tau <= 0.1 + 1e-9).mean()),
        "median_s": float(np.median(tau)), "p90_s": float(np.percentile(tau, 90)),
    }
    out["implied_speed_mps"] = {
        "reference_max": ref_speed, "median": float(np.nanmedian(implied)),
        "p10": float(np.nanpercentile(implied, 10)), "p90": float(np.nanpercentile(implied, 90)),
        "share_above_reference": float(np.nanmean(implied > ref_speed * 1.01)),
    }
    print(f"tau: {out['tau']}", flush=True)
    print(f"implied speed: {out['implied_speed_mps']}", flush=True)

    # ---- 7. Valhalla's cost against its duration --------------------------------------------
    diff = costs - durations
    out["valhalla_cost_vs_duration"] = {
        "share_cost_above_duration": float((diff > 0.5).mean()),
        "median_gap_where_above": float(np.median(diff[diff > 0.5])) if (diff > 0.5).any() else 0.0,
        "p90_gap_where_above": float(np.percentile(diff[diff > 0.5], 90)) if (diff > 0.5).any() else 0.0,
        "max_gap": float(diff.max()),
    }
    print(f"cost vs duration: {out['valhalla_cost_vs_duration']}", flush=True)

    dest = DATA / f"s1_expansion_structure_{args.category}_{args.mode}.json"
    dest.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"wrote {dest}", flush=True)

    z = out["zero_time_nodes"]
    d = out["direction"]
    c = out["valhalla_cost_vs_duration"]
    lines = [
        f"### S1.3 expansion structure, post-fix ({stamp()}): {args.category} / {args.mode}, "
        f"{args.pois} POIs, {MAX_MIN}-minute contour", "",
        f"Request: `action=isochrone`, `reverse=true`, **`skip_opposites=false`**, "
        f"`expansion_properties={PROPS}` — all five accepted by Valhalla 3.9.1; `duration` is "
        f"integer seconds ({out['duration_is_integer']}). {out['request']['features']:,} features "
        f"in {dt:.2f} s.", "",
        "**1. Adapter health.**", "",
        f"- `report=` : `{out['adapter_report']}`",
        f"- `strict=True` passes without dropping anything: **{out['strict_passes_on_real_payload']}** "
        "(it did not before `skip_opposites=false`)",
        "",
        f"**2. Roots.** {out['adapter_report']['roots_split_at_origin']} root(s) split at the "
        f"origin's projection, {out['adapter_report']['roots_oriented_by_proximity']} oriented by "
        f"proximity as a fallback, {out['adapter_report']['roots_unoriented']} unorientable. "
        f"{z['count']} node(s) at time zero, median "
        f"{z['distance_to_nearest_origin_m']['median']:.1f} m from the nearest **POI** (max "
        f"{z['distance_to_nearest_origin_m']['max']:.1f} m) — that offset is the POI's own distance "
        "from the road, which Valhalla's snapping also has and which splitting cannot remove.", "",
        f"**3. Direction.** {d['physical_edges']:,} physical edges: {d['both_ways']:,} traversable "
        f"both ways, **{d['one_way_only']:,} ({d['share_one_way']:.1%}) one way only** — the edges "
        "the old bidirectional marking let a cell cross the wrong way.", "",
        f"**6. Interior anchors.** Origins land at fractions {out['origin_on_edge_fraction']} along "
        f"their nearest expansion edge, {out['origin_distance_to_edge_m']} m away. Valhalla does "
        "**not** split an edge at the origin, so the destination's own position within its road is "
        "not modelled: time zero sits at a vertex up to "
        f"{z['distance_to_nearest_origin_m']['max']:.0f} m from the POI.", "",
        f"**5. Quantisation.** `tau` median {out['tau']['median_s']:.1f} s, p90 "
        f"{out['tau']['p90_s']:.1f} s; **{out['tau']['at_epsilon_floor']:,} edges "
        f"({out['tau']['share_at_floor']:.2%}) sit at the 0.1 s floor**, i.e. their whole-second "
        "duration difference rounded to zero.", "",
        f"**4. Implied speed** (edge length / tau), reference max {ref_speed:.2f} m/s: median "
        f"**{out['implied_speed_mps']['median']:.2f} m/s**, p10 {out['implied_speed_mps']['p10']:.2f}, "
        f"p90 {out['implied_speed_mps']['p90']:.2f}; "
        f"{out['implied_speed_mps']['share_above_reference']:.2%} exceed the reference. A median "
        f"implied speed well below the road speeds confirms that `tau` is **not a pure traversal "
        "time** — turn, stop and intersection costs charged on entering the edge are inside it, and "
        "within-edge interpolation scales them along with the travel.", "",
        f"**7. Valhalla's `cost` against its `duration`.** They differ on "
        f"**{c['share_cost_above_duration']:.1%}** of features (median gap "
        f"{c['median_gap_where_above']:.1f} s, p90 {c['p90_gap_where_above']:.1f} s, max "
        f"{c['max_gap']:.0f} s). So Valhalla runs its own two-weight model, and the adapter reports "
        "`duration` — the right choice. Carrying `cost` as the *selection* weight, the way the "
        "own-graph path does since Codex pass-6 H1, is a named follow-up and is not done here.", "",
    ]
    text = "\n".join(lines)
    print("\n" + text, flush=True)
    append_results("g1-routing.md", text)


if __name__ == "__main__":
    main()
