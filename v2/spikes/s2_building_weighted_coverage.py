"""S2.4: coverage weighted by buildings, and the missing region decomposed into named places.

Cell coverage is the number we have been quoting — 77.69% of 330,502 cells have a walk time to a
grocery. It is the wrong denominator for the question a household asks. Cells are uniform; people
are not. A grid over the Triangle spends a large share of its area on Jordan Lake, farmland and
forest, and a coverage figure computed over area therefore reports mostly the emptiness of the
countryside.

So this reports coverage weighted by **building count** alongside it. Two cautions, both of which
belong in anything published from this:

1. It is **building-weighted, not home-weighted** (plan M1). Overture Buildings carries no reliable
   residential flag in this metro, and the set includes sheds, barns, warehouses and the several
   hundred structures of a single hospital campus. A building is not a household and the two are not
   proportional.
2. The weights come from an **ODbL and CC BY** source, admitted to this one use by
   `fetch_buildings.py`'s `DIAGNOSTIC_LICENCES` under owner decision 17. Counts per cell are a
   Produced Work; the footprints themselves are not republished, and must not be.

The second half is the missing region, which until S0 was one undifferentiated blob and now has a
reason per cell. A single percentage cannot be acted on, but "this contiguous region of N cells
holds M buildings and is missing because there is no road within 200 m" can be: that is either a
graph defect to fix or genuinely empty land to leave alone, and the building count is what separates
the two.

Run from v2/:  uv run python spikes/s2_building_weighted_coverage.py grocery walk
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
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (ACCEPTED_PLACES, GRAPH_CACHE, GRID, LAYERS, METRO, METRO_DIR,  # noqa: E402
                     append_results, stamp)
from locfinder import profile  # noqa: E402
from locfinder.places.categories import select_overture  # noqa: E402
from locfinder.status import Reason  # noqa: E402
from locfinder.traveltime.components import largest_component  # noqa: E402
from locfinder.traveltime.csr import graph_to_cost_time_csr  # noqa: E402
from locfinder.traveltime.layer import build_layer_surface  # noqa: E402
from locfinder.traveltime.snap import EdgeIndex  # noqa: E402
from locfinder.traveltime.speeds import add_travel_times, symmetrise  # noqa: E402

BUILDINGS = METRO_DIR / "overture_buildings_accepted.parquet"
POI_SNAP_MAX_M = 300.0
MAX_ACCESS_M = 200.0
CUTOFF_MIN = 120.0
THRESHOLDS_MIN = (10, 15, 25, 45)
N_REGIONS = 10


def building_counts() -> tuple[np.ndarray, dict]:
    """Buildings per cell, by centroid. Returns the raster and what fell outside the grid.

    Centroids are taken in the grid's own projected CRS. A footprint straddling a cell boundary is
    counted once, in the cell holding its centroid — for a count that is the right choice, and it
    is why this is a count and not an area share.
    """
    gdf = gpd.read_parquet(BUILDINGS, columns=["geometry"]).to_crs(GRID.crs)
    c = gdf.geometry.centroid
    col = np.floor((c.x.to_numpy() - GRID.x_min) / GRID.cell_m).astype(np.int64)
    row = np.floor((GRID.y_max - c.y.to_numpy()) / GRID.cell_m).astype(np.int64)
    inside = (col >= 0) & (col < GRID.ncols) & (row >= 0) & (row < GRID.nrows)
    counts = np.zeros((GRID.nrows, GRID.ncols), dtype=np.int64)
    np.add.at(counts, (row[inside], col[inside]), 1)
    return counts, {"buildings_total": int(len(gdf)), "inside_grid": int(inside.sum()),
                    "outside_grid": int((~inside).sum())}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("category")
    ap.add_argument("mode", choices=["walk", "bike", "drive"])
    args = ap.parse_args()
    out: dict = {"metro": METRO.name, "category": args.category, "mode": args.mode}

    t = time.perf_counter()
    counts, bstats = building_counts()
    out["buildings"] = bstats
    print(f"buildings binned in {time.perf_counter() - t:.1f}s: {bstats}", flush=True)

    t = time.perf_counter()
    G = ox.load_graphml(GRAPH_CACHE)
    G = ox.project_graph(G, to_crs=GRID.crs)
    G = add_travel_times(G, mode=args.mode)
    if args.mode == "walk":
        G = symmetrise(G)
    G.remove_nodes_from([n for n, d in G.degree() if d == 0])
    G, comp = largest_component(G)
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
    places = gpd.read_parquet(ACCEPTED_PLACES).to_crs(GRID.crs)
    sel = select_overture(places, args.category)
    cent = sel.geometry.centroid
    nodes, dists = ox.nearest_nodes(G, cent.x.to_numpy(), cent.y.to_numpy(), return_dist=True)
    dest_idx = sorted({index[n] for n, d in zip(nodes, dists) if d <= POI_SNAP_MAX_M})
    surf = build_layer_surface(
        G, (cost_csr, time_csr), index, GRID, dest_idx=dest_idx, mode=args.mode,
        target=args.category, engine="own-graph", cutoff_min=CUTOFF_MIN,
        max_access_m=MAX_ACCESS_M, timings={}, edge_index=EdgeIndex.from_graph(G, index),
        places_selected=len(sel))
    print(f"surface built in {time.perf_counter() - t:.1f}s", flush=True)

    ok = surf.reason == Reason.OK
    total_b = int(counts.sum())
    out["coverage"] = {
        "cells_total": int(ok.size), "cells_ok": int(ok.sum()), "cells_share": float(ok.mean()),
        "buildings_total": total_b, "buildings_ok": int(counts[ok].sum()),
        "buildings_share": float(counts[ok].sum() / total_b),
    }
    c = out["coverage"]
    print(f"\ncells      {c['cells_ok']:>9,} / {c['cells_total']:,}  {c['cells_share']:7.4%}")
    print(f"buildings  {c['buildings_ok']:>9,} / {c['buildings_total']:,}  "
          f"{c['buildings_share']:7.4%}", flush=True)

    # Per-reason, both ways, because which reason holds the buildings decides what to fix.
    out["by_reason"] = {}
    for v in sorted({int(x) for x in np.unique(surf.reason)}):
        m = surf.reason == v
        out["by_reason"][Reason(v).name] = {
            "cells": int(m.sum()), "cells_share": float(m.mean()),
            "buildings": int(counts[m].sum()),
            "buildings_share": float(counts[m].sum() / total_b)}
    print("\n| reason | cells | share | buildings | share |", flush=True)
    for k, v in out["by_reason"].items():
        print(f"  {k:<16} {v['cells']:>9,} {v['cells_share']:7.4%} "
              f"{v['buildings']:>9,} {v['buildings_share']:7.4%}", flush=True)

    # Thresholds, weighted. A household sets a threshold, not a horizon.
    out["thresholds"] = {}
    for m in THRESHOLDS_MIN:
        p = ok & (surf.seconds <= m * 60.0)
        out["thresholds"][f"{m}min"] = {
            "cells": int(p.sum()), "cells_share": float(p.mean()),
            "buildings": int(counts[p].sum()),
            "buildings_share": float(counts[p].sum() / total_b)}
    print("\nthresholds (cells vs buildings):", flush=True)
    for k, v in out["thresholds"].items():
        print(f"  {k:<6} {v['cells_share']:7.4%} of cells   {v['buildings_share']:7.4%} of "
              f"buildings  ({v['buildings']:,})", flush=True)

    # ---- the missing region, as places rather than a percentage ------------------------------
    missing = ~ok
    # 4-connectivity: the conservative reading, so a region is not joined to its neighbour through
    # a single diagonal touch. It yields more and smaller regions than 8-connectivity would.
    labels, n = ndimage.label(missing)
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    order = np.argsort(sizes)[::-1][:N_REGIONS]
    lon, lat = GRID.cell_centers_lonlat()
    out["missing_regions"] = {"count": int(n), "largest": []}
    for lab in order:
        if sizes[lab] == 0:
            continue
        m = labels == lab
        reasons = {Reason(int(v)).name: int(cc) for v, cc
                   in zip(*np.unique(surf.reason[m], return_counts=True))}
        # Cells and buildings split differently, and the building split is the actionable one: a
        # region can be mostly off-network by area while its buildings sit in the part that merely
        # exceeds the horizon, or the reverse.
        by_reason_b = {Reason(int(v)).name: int(counts[m & (surf.reason == v)].sum())
                       for v in sorted({int(x) for x in np.unique(surf.reason[m])})}
        dominant = max(reasons, key=reasons.get)
        out["missing_regions"]["largest"].append({
            "cells": int(sizes[lab]), "buildings": int(counts[m].sum()),
            "dominant_reason": dominant,
            "dominant_share": reasons[dominant] / int(sizes[lab]),
            "reasons": reasons, "buildings_by_reason": by_reason_b,
            "centroid_lonlat": [round(float(lon[m].mean()), 5), round(float(lat[m].mean()), 5)],
        })
    print(f"\n{n:,} contiguous missing regions; the {N_REGIONS} largest:", flush=True)
    for r in out["missing_regions"]["largest"]:
        print(f"  {r['cells']:>7,} cells  {r['buildings']:>7,} buildings  "
              f"{r['dominant_reason']:<16} {r['dominant_share']:6.1%}  "
              f"{r['centroid_lonlat']}  by reason {r['buildings_by_reason']}", flush=True)

    # The rebuild costs two minutes; a follow-up asking a different question of the same surface
    # should not have to pay it again, and should not be tempted to re-derive reasons from seconds.
    np.save(LAYERS / f"own_{METRO.name}_{args.category}_{args.mode}_reason.npy", surf.reason)
    # And the lower bound, which was not saved before. Without it a follow-up cannot rebuild a
    # `status.Surface` at all, and `scripts/audit_recommendations.py` has to reconstruct one under
    # an assertion that only holds while this metro's reason array stops at BEYOND_HORIZON. The
    # bound is what turns a missing value into a *known* failure, so re-deriving it by guesswork is
    # exactly the error the reasons exist to prevent.
    np.save(LAYERS / f"own_{METRO.name}_{args.category}_{args.mode}_min_possible_s.npy",
            surf.min_possible_s)
    np.save(LAYERS / f"own_{METRO.name}_buildings_per_cell.npy", counts)

    out["versions"] = {"profile": profile.profile_version(), "grid": profile.grid_version(GRID)}
    append_results("spotcheck-engines.md", render(out, args))
    print("\nappended to docs/experiments/spotcheck-engines.md", flush=True)
    print(json.dumps(out, indent=1, default=str), flush=True)


def render(out: dict, args) -> str:
    c, b = out["coverage"], out["buildings"]
    lines = [f"### S2.4 building-weighted coverage: {args.category} / {args.mode} ({stamp()})", "",
             "Cell coverage weights Jordan Lake the same as downtown Durham. This reports coverage "
             "weighted by **building count** alongside it. It is **building-weighted, not "
             "home-weighted**: Overture carries no reliable residential flag here, so sheds, barns "
             "and a hospital campus's several hundred structures all count as one building each. "
             "The weights are ODbL/CC BY rows admitted to this use only, as counts — a Produced "
             "Work, republishing no footprints.", "",
             f"- {b['buildings_total']:,} accepted buildings, **{b['inside_grid']:,} inside the "
             f"grid** and {b['outside_grid']:,} outside it (the download covers the grid's own "
             f"WGS84 envelope, which is larger than the grid's UTM rectangle)", "",
             "| denominator | covered | total | share |", "|---|---|---|---|",
             f"| cells | {c['cells_ok']:,} | {c['cells_total']:,} | **{c['cells_share']:.4%}** |",
             f"| buildings | {c['buildings_ok']:,} | {c['buildings_total']:,} | "
             f"**{c['buildings_share']:.4%}** |", "",
             "| reason | cells | of cells | buildings | of buildings |", "|---|---|---|---|---|"]
    for k, v in out["by_reason"].items():
        lines.append(f"| `{k}` | {v['cells']:,} | {v['cells_share']:.4%} | {v['buildings']:,} | "
                     f"{v['buildings_share']:.4%} |")
    lines += ["", "| threshold | of cells | of buildings |", "|---|---|---|"]
    for k, v in out["thresholds"].items():
        lines.append(f"| {k} | {v['cells_share']:.4%} | **{v['buildings_share']:.4%}** |")
    r = out["missing_regions"]
    lines += ["", f"**The missing region as places.** {r['count']:,} contiguous components "
                  f"(4-connectivity, the conservative reading). The ten largest. `dominant` is the "
                  f"reason holding most of the region's *cells*; the two building columns split "
                  f"the same region by reason, which is the breakdown that can be acted on:", "",
              "| cells | buildings | dominant reason (cells) | share | off-network buildings | "
              "beyond-horizon buildings | centre (lon, lat) |",
              "|---|---|---|---|---|---|---|"]
    for q in r["largest"]:
        bb = q["buildings_by_reason"]
        lines.append(f"| {q['cells']:,} | {q['buildings']:,} | `{q['dominant_reason']}` | "
                     f"{q['dominant_share']:.1%} | {bb.get('OFF_NETWORK', 0):,} | "
                     f"{bb.get('BEYOND_HORIZON', 0):,} | {q['centroid_lonlat'][0]}, "
                     f"{q['centroid_lonlat'][1]} |")
    lines += ["", f"- profile `{out['versions']['profile']}`, grid `{out['versions']['grid']}`"]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
