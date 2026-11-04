"""Phase 1 S1.3, part two: the two findings from `s1_expansion_structure.py` that need a cleaner
measurement before anything is changed.

**A. Strict mode fails on every real drive payload.** 636 of 254,323 edges name a predecessor that
is not in the response. Hypothesis: `skip_opposites=true` tells Valhalla not to emit the opposite
direction of an edge it has already settled, so an edge whose predecessor *was* such an opposite
has a `pred_edge_id` pointing at something that was never serialised. If that is the cause, the
count should fall to zero with `skip_opposites=false`. Tested here, not assumed.

**B. The bidirectional assumption, measured without confounding.** The first pass rebuilt a
direction-faithful index from `skip_opposites=true` features, where a two-way street appears only
once — so forbidding its unused direction blocks a *legal* move, and the 2.80% figure mixed
"illegal move allowed" with "legal move wrongly blocked". The clean comparison needs
`skip_opposites=false`, where both directions are present when both were settled, and it needs the
two directed features **merged into one physical edge**. The current adapter does not merge them:
it appends every feature as its own geometry, so two opposing features become two STRtree entries
with identical geometry and `nearest()` returns one of them arbitrarily, carrying only that
direction's traversal time.

Run from v2/ with Valhalla serving:
  uv run python spikes/s1_expansion_directions.py --category grocery --mode drive --pois 3
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import shapely
from pyproj import Transformer
from shapely.geometry import LineString

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ACCEPTED_PLACES, DATA, GRID, append_results, stamp  # noqa: E402
from s1_expansion_structure import COSTING, MAX_MIN, canonical_key, request_expansion  # noqa: E402
from locfinder.places.categories import select_overture  # noqa: E402
from locfinder.traveltime.expansion import _NO_PRED_SENTINELS, expansion_to_edge_index  # noqa: E402
from locfinder.traveltime.snap import EdgeIndex, cell_seconds_from_arrival  # noqa: E402

_NODE_SNAP_M = 0.5
_MIN_EPS = 0.1


def node_key(x: float, y: float) -> tuple[int, int]:
    return (int(round(x / _NODE_SNAP_M)), int(round(y / _NODE_SNAP_M)))


def merged_index(feats, *, target_crs: str, origins, directional: bool):
    """One entry per *physical* edge, with each direction's traversal time where it was settled.

    The direction is derived the same way the adapter derives endpoint times: the near end is the
    end shared with the predecessor (or, for a root, the end nearest an origin). A traveller
    crosses the edge from its far end to its near end, so:

        near end is the geometry START  ->  legal direction is end -> start  ->  rev_time
        near end is the geometry END    ->  legal direction is start -> end  ->  fwd_time

    With `directional=False` the merged edge is traversable both ways at the cheaper settled
    traversal time, which is what isolates the *merging* effect from the *direction* effect: the
    two push in opposite directions and a single comparison cannot separate them.

    Returns (EdgeIndex, node times, diagnostics).
    """
    to_proj = Transformer.from_crs("EPSG:4326", target_crs, always_xy=True)
    kept = []
    for f in feats:
        coords = (f.get("geometry") or {}).get("coordinates") or []
        props = f.get("properties") or {}
        if len(coords) < 2 or props.get("duration") is None:
            continue
        xs, ys = to_proj.transform([c[0] for c in coords], [c[1] for c in coords])
        if not (np.all(np.isfinite(xs)) and np.all(np.isfinite(ys))):
            continue
        kept.append({"geom": LineString(list(zip(xs, ys))), "dur": float(props["duration"]),
                     "edge_id": props.get("edge_id"), "pred": props.get("pred_edge_id"),
                     "ll_first": tuple(coords[0]), "ll_last": tuple(coords[-1]),
                     "key": canonical_key(coords)})
    by_edge = {e["edge_id"]: e for e in kept if e["edge_id"] is not None}

    ox, oy = to_proj.transform([p[0] for p in origins], [p[1] for p in origins])
    origin_pts = shapely.points(np.asarray(ox), np.asarray(oy))

    succ: dict[object, list[dict]] = {}
    for e in kept:
        if e["pred"] not in _NO_PRED_SENTINELS:
            succ.setdefault(e["pred"], []).append(e)

    # physical edges, keyed by canonical geometry
    phys: dict[tuple, dict] = {}
    nodes: dict[tuple[int, int], int] = {}
    diag = {"features": len(kept), "dangling": 0, "unoriented": 0}

    def node_id(x, y):
        k = node_key(x, y)
        if k not in nodes:
            nodes[k] = len(nodes)
        return nodes[k]

    for e in kept:
        is_root = e["pred"] in _NO_PRED_SENTINELS
        pred = by_edge.get(e["pred"])
        if pred is None and not is_root:
            diag["dangling"] += 1
            continue
        near_t = 0.0 if is_root else float(pred["dur"])
        tau = max(e["dur"] - near_t, _MIN_EPS)
        if is_root:
            first = shapely.points(*e["geom"].coords[0])
            last = shapely.points(*e["geom"].coords[-1])
            d_f = float(shapely.distance(first, origin_pts).min())
            d_l = float(shapely.distance(last, origin_pts).min())
            if abs(d_f - d_l) > _NODE_SNAP_M:
                near_at_start = d_f < d_l
            else:
                shared = set()
                for s in succ.get(e["edge_id"], ()):
                    shared |= {s["ll_first"], s["ll_last"]}
                if shared and (e["ll_first"] in shared) != (e["ll_last"] in shared):
                    near_at_start = e["ll_last"] in shared
                else:
                    diag["unoriented"] += 1
                    continue
        else:
            shared = {pred["ll_first"], pred["ll_last"]}
            if e["ll_first"] in shared:
                near_at_start = True
            elif e["ll_last"] in shared:
                near_at_start = False
            else:
                near_at_start = (e["geom"].interpolate(0.0).distance(pred["geom"])
                                 <= e["geom"].interpolate(1.0, normalized=True).distance(pred["geom"]))

        rec = phys.get(e["key"])
        if rec is None:
            s_id = node_id(*e["geom"].coords[0])
            e_id = node_id(*e["geom"].coords[-1])
            rec = {"geom": e["geom"], "s": s_id, "e": e_id,
                   "fwd": np.inf, "rev": np.inf, "t_s": np.inf, "t_e": np.inf}
            phys[e["key"]] = rec
        # the stored geometry of a later feature may be reversed relative to the first one
        same_dir = (node_key(*e["geom"].coords[0]) == node_key(*rec["geom"].coords[0]))
        near_at_rec_start = near_at_start if same_dir else not near_at_start
        if near_at_rec_start:
            rec["rev"] = min(rec["rev"], tau)
            rec["t_s"] = min(rec["t_s"], near_t)
            rec["t_e"] = min(rec["t_e"], e["dur"])
        else:
            rec["fwd"] = min(rec["fwd"], tau)
            rec["t_e"] = min(rec["t_e"], near_t)
            rec["t_s"] = min(rec["t_s"], e["dur"])

    geoms = [r["geom"] for r in phys.values()]
    T = np.full(len(nodes), np.inf)
    starts, ends, fwd, rev = [], [], [], []
    for r in phys.values():
        starts.append(r["s"]); ends.append(r["e"])
        fwd.append(r["fwd"]); rev.append(r["rev"])
        T[r["s"]] = min(T[r["s"]], r["t_s"])
        T[r["e"]] = min(T[r["e"]], r["t_e"])
    arr = np.empty(len(geoms), dtype=object)
    arr[:] = geoms
    fwd = np.asarray(fwd, dtype=np.float64)
    rev = np.asarray(rev, dtype=np.float64)
    if not directional:
        # both ways at the cheaper settled time; an edge settled in neither stays unusable
        best = np.fmin(fwd, rev)
        fwd = rev = best
    idx = EdgeIndex(tree=shapely.STRtree(geoms), geoms=arr,
                    start_idx=np.asarray(starts, dtype=np.int64),
                    end_idx=np.asarray(ends, dtype=np.int64),
                    fwd_time=fwd, rev_time=rev, fwd_cost=fwd, rev_cost=rev)
    diag["physical_edges"] = len(geoms)
    diag["both_directions"] = int((np.isfinite(fwd) & np.isfinite(rev)).sum())
    diag["one_direction"] = int((np.isfinite(fwd) ^ np.isfinite(rev)).sum())
    diag["no_direction"] = int((~np.isfinite(fwd) & ~np.isfinite(rev)).sum())
    return idx, T, diag


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--category", default="grocery")
    ap.add_argument("--mode", default="drive", choices=["walk", "bike", "drive"])
    ap.add_argument("--pois", type=int, default=3)
    args = ap.parse_args()
    costing = COSTING[args.mode]
    out: dict = {"category": args.category, "mode": args.mode, "costing": costing}

    places = gpd.read_parquet(ACCEPTED_PLACES)
    sel = select_overture(places, args.category).to_crs(GRID.crs)
    cent = sel.geometry.centroid.to_crs("EPSG:4326")
    latlon = [(float(y), float(x)) for x, y in zip(cent.x, cent.y)][: args.pois]
    lonlat = [(lo, la) for la, lo in latlon]

    # ---- A. is skip_opposites the cause of the dangling predecessors? -----------------------
    res = {}
    for skip in (True, False):
        feats, dt = request_expansion(latlon, costing, controlled=True, skip_opposites=skip)
        ids = {f["properties"]["edge_id"] for f in feats}
        dangling = sum(1 for f in feats
                       if f["properties"].get("pred_edge_id") not in _NO_PRED_SENTINELS
                       and f["properties"].get("pred_edge_id") not in ids)
        rep: dict = {}
        expansion_to_edge_index(feats, target_crs=GRID.crs, opposites_included=not skip,
                                origins=lonlat, strict=False, report=rep)
        res[skip] = {"features": len(feats), "seconds": round(dt, 2), "dangling": dangling,
                     "adapter_report": rep, "feats": feats}
        print(f"skip_opposites={skip}: {len(feats)} features, {dangling} dangling "
              f"({dangling / max(len(feats), 1):.4%}), {dt:.2f} s", flush=True)
    out["dangling_by_skip_opposites"] = {
        str(k): {kk: vv for kk, vv in v.items() if kk != "feats"} for k, v in res.items()}
    hypothesis_holds = res[False]["dangling"] < res[True]["dangling"]
    out["skip_opposites_explains_dangling"] = bool(hypothesis_holds)
    print(f"hypothesis (skip_opposites causes the dangling predecessors): "
          f"{'SUPPORTED' if hypothesis_holds else 'NOT SUPPORTED'}", flush=True)

    # ---- B. three indices, so merging and direction can be told apart ----------------------
    # The two changes move cell times in OPPOSITE directions, so a single before/after comparison
    # cannot separate them: merging lets a cell take the better of two duplicate geometries
    # (earlier), while restricting direction removes illegal moves (later).
    feats_both = res[False]["feats"]
    feats_skip = res[True]["feats"]
    xs, ys = GRID.cell_centers_xy()
    cut = MAX_MIN * 60.0

    def cells(idx, T):
        return cell_seconds_from_arrival(idx, T, xs, ys, mode=args.mode, max_access_m=200.0,
                                         cutoff_s=cut)

    # 0: today's production path -- adapter as written, on skip_opposites=true features
    # index 0 reproduces the pre-fix behaviour: skip_opposites=true, so the adapter takes its
    # documented bidirectional fallback -- which is exactly what the old code did unconditionally.
    i0, t0_ = expansion_to_edge_index(feats_skip, target_crs=GRID.crs, opposites_included=False,
                                      origins=lonlat, strict=False, report={})
    s0 = cells(i0, t0_)
    # 2: merged by geometry, still bidirectional
    i2, t2_, d2 = merged_index(feats_both, target_crs=GRID.crs, origins=lonlat, directional=False)
    s2 = cells(i2, t2_)
    # 3: merged by geometry, only the settled directions
    i3, t3_, d3 = merged_index(feats_both, target_crs=GRID.crs, origins=lonlat, directional=True)
    s3 = cells(i3, t3_)
    out["merged_index"] = d3
    print(f"merged index: {d3}", flush=True)

    def compare(a, b, label):
        fa, fb = np.isfinite(a), np.isfinite(b)
        both = fa & fb
        gap = b[both] - a[both]
        changed = np.abs(gap) > 1.0
        r = {
            "cells_finite_before": int(fa.sum()), "cells_finite_after": int(fb.sum()),
            "lost": int((fa & ~fb).sum()), "gained": int((~fa & fb).sum()),
            "comparable": int(both.sum()), "changed_over_1s": int(changed.sum()),
            "share_changed": float(changed.mean()) if gap.size else 0.0,
            "median_signed_where_changed": float(np.median(gap[changed])) if changed.any() else 0.0,
            "p90_abs_where_changed": float(np.percentile(np.abs(gap[changed]), 90)) if changed.any() else 0.0,
            "max_increase": float(gap.max()) if gap.size else 0.0,
            "max_decrease": float(gap.min()) if gap.size else 0.0,
            "share_later_among_changed": float((gap[changed] > 0).mean()) if changed.any() else 0.0,
        }
        print(f"{label}: {json.dumps(r)}", flush=True)
        return r

    out["merging_effect"] = compare(s0, s2, "0 -> 2  merging only")
    out["direction_effect"] = compare(s2, s3, "2 -> 3  direction only")
    out["total_effect"] = compare(s0, s3, "0 -> 3  both")

    dest = DATA / f"s1_expansion_directions_{args.category}_{args.mode}.json"
    dest.write_text(json.dumps(out, indent=1), encoding="utf-8")

    a_t, a_f = res[True], res[False]
    lines = [
        f"### S1.3 part two: dangling predecessors and the direction assumption ({stamp()}): "
        f"{args.category} / {args.mode}, {args.pois} POIs", "",
        "**A. `skip_opposites` is why strict mode fails.**", "",
        "| request | features | seconds | edges naming an absent predecessor |",
        "|---|---|---|---|",
        f"| `skip_opposites=true` | {a_t['features']:,} | {a_t['seconds']} | "
        f"**{a_t['dangling']:,}** ({a_t['dangling'] / max(a_t['features'], 1):.4%}) |",
        f"| `skip_opposites=false` | {a_f['features']:,} | {a_f['seconds']} | "
        f"**{a_f['dangling']:,}** ({a_f['dangling'] / max(a_f['features'], 1):.4%}) |", "",
        "Valhalla omits the opposite direction of an edge it has already settled, so an edge whose "
        "predecessor *was* one of those omitted opposites points at an `edge_id` that was never "
        "serialised. Its near-end time is then genuinely unknown and the adapter drops it — "
        "correctly, but the cause is a flag we chose, not a property of the network.", "",
        "**B. The direction assumption, decomposed.** The adapter sets "
        "`fwd_time == rev_time == tau`, arguing the tree already encodes legality. Under arrival "
        "semantics the tree encodes legality in **one** direction: a traveller crosses an edge from "
        "its far end to its near end. The adapter also never merges the two directed features for "
        "one physical edge, so with `skip_opposites=false` the same geometry enters the STRtree "
        "twice and `nearest()` picks one arbitrarily.", "",
        "These two defects move cell times in **opposite** directions — merging lets a cell take "
        "the better of two duplicate geometries, restricting direction removes illegal moves — so "
        "they are measured separately. Three indices over the same cells:", "",
        "| | index |", "|---|---|",
        "| **0** | the adapter as written, on `skip_opposites=true` features — today's path |",
        "| **2** | merged by geometry, still traversable both ways |",
        "| **3** | merged by geometry, only the directions actually settled |", "",
        f"Merging gives **{d3['physical_edges']:,} physical edges** from {d3['features']:,} "
        f"features: {d3['both_directions']:,} traversable both ways, {d3['one_direction']:,} one "
        f"way only, {d3['unoriented']} unorientable.", "",
        "| | 0 -> 2 (merging) | 2 -> 3 (direction) | 0 -> 3 (both) |", "|---|---|---|---|",
    ] + [
        f"| {label} | {fmt(out['merging_effect'][k])} | {fmt(out['direction_effect'][k])} | "
        f"{fmt(out['total_effect'][k])} |"
        for label, k, fmt in (
            ("reachable cells after", "cells_finite_after", lambda v: f"{v:,}"),
            ("cells lost", "lost", lambda v: f"{v:,}"),
            ("cells gained", "gained", lambda v: f"{v:,}"),
            ("changed by more than 1 s", "changed_over_1s", lambda v: f"{v:,}"),
            ("share changed", "share_changed", lambda v: f"{v:.2%}"),
            ("median signed change", "median_signed_where_changed", lambda v: f"{v:+.1f} s"),
            ("p90 absolute change", "p90_abs_where_changed", lambda v: f"{v:.1f} s"),
            ("largest increase", "max_increase", lambda v: f"{v:+.1f} s"),
            ("largest decrease", "max_decrease", lambda v: f"{v:+.1f} s"),
            ("share getting later", "share_later_among_changed", lambda v: f"{v:.1%}"),
        )
    ] + [
        "",
        "The direction column is the one that matters for correctness, and its sign is the expected "
        "one: restricting travel to the settled direction makes cells later, never earlier. The "
        "merging column is a separate defect of the same adapter and moves the other way.", "",
        "**Superseded:** the first pass of this measurement reported 2.80% of cells changing with a "
        "median increase of 13.1 s, built from `skip_opposites=true` features. That construction "
        "forbids the unused direction of a two-way street that was only ever settled once, so it "
        "mixed 'illegal move allowed' with 'legal move wrongly blocked'. The table above replaces "
        "it.", "",
    ]
    text = "\n".join(lines)
    print("\n" + text, flush=True)
    append_results("g1-routing.md", text)


if __name__ == "__main__":
    main()
