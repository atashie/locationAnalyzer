"""Does adding destinations only ever help? Codex pass-11 M3.

Widening the Overture extent took the grocery set from 452 to 550 and coverage from 253,679 to
256,752 cells, and I wrote that this was "the expected direction: more destinations can only help
reachability". That is false for **what this layer reports**. The monotonicity theorem holds for
the existence of a path, for minimum cost, and for minimum *time*; the shipped surface reports the
time along the path to the **cost-nearest** destination (pass-8 H2), and a new destination that is
cheaper but slower replaces the previous winner and raises the reported time. Past the horizon,
that turns `OK` into `BEYOND_HORIZON`.

Codex's counterexample is two destinations at time 60 / cost 260 and time 180 / cost 180: with a
120 s horizon the origin is `OK` on the first alone and fails once the second is added. So the
question this spike settles is not whether the defect exists — it does, by construction — but
**whether it bites on real data**, and what the +3,073 net actually decomposes into.

A net is not a count. The honest form is a paired cell-by-cell transition matrix, which needs both
surfaces over the *same* grid and graph. The evaluation-extent artifact was overwritten by the
rebuild, but it is reconstructible: the eval-extent download is exactly the routing-extent rows
whose centroid falls inside the evaluation bbox, and that filter returns 452 of 550 — the original
count, so the pairing is faithful rather than approximate.

Both surfaces come from `build_layer_surface`, so this measures the shipped aggregation, not a
model of it.

Run from v2/:  uv run python spikes/s2_destination_monotonicity.py grocery walk
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import osmnx as ox

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ACCEPTED_PLACES, EVAL_BBOX, GRAPH_CACHE, GRID, METRO, append_results, stamp  # noqa: E402
from locfinder import profile  # noqa: E402
from locfinder.places.categories import select_overture  # noqa: E402
from locfinder.status import Reason  # noqa: E402
from locfinder.traveltime.components import largest_component  # noqa: E402
from locfinder.traveltime.csr import graph_to_cost_time_csr  # noqa: E402
from locfinder.traveltime.layer import build_layer_surface  # noqa: E402
from locfinder.traveltime.snap import EdgeIndex  # noqa: E402
from locfinder.traveltime.speeds import add_travel_times, symmetrise  # noqa: E402

POI_SNAP_MAX_M = 300.0
MAX_ACCESS_M = 200.0
CUTOFF_MIN = 120.0
THRESHOLDS_MIN = (10, 15, 25, 45)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("category")
    ap.add_argument("mode", choices=["walk", "bike", "drive"])
    args = ap.parse_args()
    out: dict = {"metro": METRO.name, "category": args.category, "mode": args.mode}

    t = time.perf_counter()
    G = ox.load_graphml(GRAPH_CACHE)
    G = ox.project_graph(G, to_crs=GRID.crs)
    G = add_travel_times(G, mode=args.mode)
    if args.mode == "walk":
        G = symmetrise(G)
    G.remove_nodes_from([n for n, d in G.degree() if d == 0])
    G, comp = largest_component(G)
    print(f"graph prepared in {time.perf_counter() - t:.1f}s: {comp.summary}", flush=True)
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
    eidx = EdgeIndex.from_graph(G, index)

    # ---- the two destination sets, paired on one graph ---------------------------------------
    places = gpd.read_parquet(ACCEPTED_PLACES)
    sel = select_overture(places, args.category).to_crs(GRID.crs)
    # Centroid in the projected CRS, *then* reprojected: a centroid taken in a geographic CRS is
    # computed on degrees and is wrong for anything that is not already a point.
    cent = sel.geometry.centroid
    wgs = cent.to_crs(4326)
    e = EVAL_BBOX
    narrow_mask = ((wgs.x >= e["west"]) & (wgs.x <= e["east"])
                   & (wgs.y >= e["south"]) & (wgs.y <= e["north"])).to_numpy()
    nodes, dists = ox.nearest_nodes(G, cent.x.to_numpy(), cent.y.to_numpy(), return_dist=True)
    keep = np.asarray(dists) <= POI_SNAP_MAX_M

    def dest_nodes(place_mask):
        return sorted({index[n] for n, k, m in zip(nodes, keep, place_mask) if k and m})

    wide_idx = dest_nodes(np.ones(len(sel), dtype=bool))
    narrow_idx = dest_nodes(narrow_mask)
    out["destinations"] = {
        "narrow_places": int(narrow_mask.sum()), "narrow_nodes": len(narrow_idx),
        "wide_places": int(len(sel)), "wide_nodes": len(wide_idx),
        "narrow_is_subset": set(narrow_idx) <= set(wide_idx),
        # The reconstruction replaces a bbox *query* with a point-in-bbox test, which is only the
        # same thing for point geometries. Recorded rather than assumed.
        "geometry_types": {k: int(v) for k, v in
                           sel.geometry.geom_type.value_counts().to_dict().items()},
    }
    print(f"narrow {out['destinations']['narrow_places']} places / {len(narrow_idx)} nodes; "
          f"wide {len(sel)} places / {len(wide_idx)} nodes; "
          f"subset={out['destinations']['narrow_is_subset']}", flush=True)

    def surface(dest_idx, places_selected):
        return build_layer_surface(
            G, (cost_csr, time_csr), index, GRID, dest_idx=dest_idx, mode=args.mode,
            target=args.category, engine="own-graph", cutoff_min=CUTOFF_MIN,
            max_access_m=MAX_ACCESS_M, timings={}, edge_index=eidx,
            places_selected=places_selected)

    narrow = surface(narrow_idx, int(narrow_mask.sum()))
    wide = surface(wide_idx, int(len(sel)))

    # ---- the transition matrix, which is what a net gain hides -------------------------------
    present = sorted({int(v) for v in np.unique(narrow.reason)} | {int(v) for v in np.unique(wide.reason)})
    matrix = {}
    for a in present:
        row = narrow.reason == a
        if not row.any():
            continue
        matrix[Reason(a).name] = {Reason(b).name: int((row & (wide.reason == b)).sum())
                                  for b in present if (row & (wide.reason == b)).any()}
    out["transitions"] = matrix
    print("\ntransition matrix (narrow -> wide):", flush=True)
    for a, row in matrix.items():
        for b, n in sorted(row.items(), key=lambda kv: -kv[1]):
            flag = "" if a == b else ("   <-- GAIN" if b == "OK" else "   <-- LOSS")
            print(f"  {a:<16} -> {b:<16} {n:>9,}{flag}", flush=True)

    ok_n, ok_w = narrow.reason == Reason.OK, wide.reason == Reason.OK
    out["coverage"] = {"narrow_ok": int(ok_n.sum()), "wide_ok": int(ok_w.sum()),
                       "net": int(ok_w.sum() - ok_n.sum()),
                       "gained": int((~ok_n & ok_w).sum()), "lost": int((ok_n & ~ok_w).sum())}
    c = out["coverage"]
    print(f"\ncoverage: {c['narrow_ok']:,} -> {c['wide_ok']:,}  (net {c['net']:+,} = "
          f"{c['gained']:,} gained - {c['lost']:,} lost)", flush=True)

    # A lost cell is the whole point, so name them rather than counting them.
    lost = np.argwhere(ok_n & ~ok_w)
    out["lost_cells"] = [{"row": int(r), "col": int(k),
                          "narrow_s": float(narrow.seconds[r, k]),
                          "wide_s": float(wide.seconds[r, k]),
                          "wide_reason": Reason(int(wide.reason[r, k])).name}
                         for r, k in lost[:20]]
    for d in out["lost_cells"]:
        print(f"  lost cell ({d['row']},{d['col']}): {d['narrow_s']:.1f} s -> "
              f"{d['wide_s']:.1f} s / {d['wide_reason']}", flush=True)

    # ---- and the reported time, where the horizon is not in the way --------------------------
    both = ok_n & ok_w
    delta = wide.seconds[both] - narrow.seconds[both]
    worse, better = delta > 1.0, delta < -1.0
    out["reported_time_on_cells_ok_in_both"] = {
        "cells": int(both.sum()),
        "worse_by_more_than_1s": int(worse.sum()), "better_by_more_than_1s": int(better.sum()),
        "max_increase_s": float(delta.max()), "max_decrease_s": float(delta.min()),
        "median_increase_s": float(np.median(delta[worse])) if worse.any() else 0.0,
    }
    r = out["reported_time_on_cells_ok_in_both"]
    print(f"\nof {r['cells']:,} cells OK in both: {r['worse_by_more_than_1s']:,} report a LONGER "
          f"time with more destinations (max +{r['max_increase_s']:.1f} s), "
          f"{r['better_by_more_than_1s']:,} shorter (max {r['max_decrease_s']:.1f} s)", flush=True)

    # Threshold crossings are what a user would actually notice.
    out["threshold_crossings"] = {}
    for m in THRESHOLDS_MIN:
        s = m * 60.0
        pn, pw = ok_n & (narrow.seconds <= s), ok_w & (wide.seconds <= s)
        out["threshold_crossings"][f"{m}min"] = {
            "narrow_passing": int(pn.sum()), "wide_passing": int(pw.sum()),
            "gained": int((~pn & pw).sum()), "lost": int((pn & ~pw).sum())}
    print("\nthreshold crossings:", flush=True)
    for k, v in out["threshold_crossings"].items():
        print(f"  {k:<6} {v['narrow_passing']:>9,} -> {v['wide_passing']:>9,}  "
              f"+{v['gained']:,} / -{v['lost']:,}", flush=True)

    out["versions"] = {"profile": profile.profile_version(), "grid": profile.grid_version(GRID)}
    append_results("spotcheck-engines.md", render(out, args))
    print("\nappended to docs/experiments/spotcheck-engines.md", flush=True)
    print(json.dumps(out, indent=1, default=str), flush=True)


def render(out: dict, args) -> str:
    d, c, r = out["destinations"], out["coverage"], out["reported_time_on_cells_ok_in_both"]
    lines = [f"### Destination monotonicity, paired: {args.category} / {args.mode} ({stamp()})", "",
             "Codex pass-11 M3. I had claimed more destinations \"can only help reachability\"; the "
             "layer reports the time to the **cost**-nearest destination, so that is not a theorem. "
             "Both surfaces are built by `build_layer_surface` on one graph and grid, with the "
             "evaluation-extent set reconstructed as the routing-extent rows inside the evaluation "
             "bbox.", "",
             f"- narrow: {d['narrow_places']} places / {d['narrow_nodes']} nodes "
             f"(the original evaluation-extent count)",
             f"- wide: {d['wide_places']} places / {d['wide_nodes']} nodes; narrow nodes are a "
             f"subset of wide: **{d['narrow_is_subset']}**",
             f"- geometries: {d['geometry_types']} — the reconstruction replaces Overture's bbox "
             f"query with a point-in-bbox test, which is the same operation only for points", "",
             "| narrow status | wide status | cells |", "|---|---|---|"]
    for a, row in out["transitions"].items():
        for b, n in sorted(row.items(), key=lambda kv: -kv[1]):
            mark = "" if a == b else (" **(gain)**" if b == "OK" else " **(loss)**")
            lines.append(f"| `{a}` | `{b}`{mark} | {n:,} |")
    lines += ["",
              f"Coverage {c['narrow_ok']:,} -> {c['wide_ok']:,}: a net of **{c['net']:+,}** made of "
              f"**{c['gained']:,} gained** and **{c['lost']:,} lost**.", ""]
    for d in out["lost_cells"]:
        lines.append(f"- lost cell ({d['row']}, {d['col']}): {d['narrow_s']:.1f} s with the "
                     f"narrow set, `{d['wide_reason']}` with the wider one "
                     f"({d['wide_s']:.1f} s)")
    lines += ["",
              f"On the {r['cells']:,} cells `OK` in both, the reported time rose by more than a "
              f"second in **{r['worse_by_more_than_1s']:,}** cells (max "
              f"**+{r['max_increase_s']:.1f} s**) and fell in {r['better_by_more_than_1s']:,} "
              f"(max {r['max_decrease_s']:.1f} s).", "",
              "| threshold | narrow passing | wide passing | gained | lost |", "|---|---|---|---|---|"]
    for k, v in out["threshold_crossings"].items():
        lines.append(f"| {k} | {v['narrow_passing']:,} | {v['wide_passing']:,} | "
                     f"+{v['gained']:,} | -{v['lost']:,} |")
    lines += ["", f"- profile `{out['versions']['profile']}`, grid `{out['versions']['grid']}`"]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
