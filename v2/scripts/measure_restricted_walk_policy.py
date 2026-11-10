"""What does the walk penalty for `access=private` actually buy, and what would a bigger one cost?

**Named product risk.** The owner walked `band15min_pass-03` (published 13.5 min, observed ~25) and
the route turned out to run 298 m down OSM way 1254722641, tagged **`access=private`**. The chain,
established rather than assumed:

* `classify_access` labels it `restricted` -- correctly;
* `add_travel_times` applies the penalty -- `cost = travel_time + RESTRICTED_PENALTY_S["walk"]`,
  which is **120 s**;
* 120 s over ~4 restricted edges is **480 s** of cost, and the detour it has to beat is **968 s**
  (782.7 s via the track against 1,750.4 s on public roads);
* so the private track still wins on cost, and because "selection is by cost, reporting is by
  time", the household is shown **782.7 s** -- the real time of a walk down a private track.

This is a **calibration** finding, not a missing-mechanism one, which makes it the cheapest of the
three options in [[project-phase1-s3-soft-way-dependence]] to act on. 120 s buys 168 m of tolerated
detour at 1.40 m/s; the question this script answers is what a larger figure costs in PASS coverage.

`no_restricted` is the limit case: every restricted walk edge removed. It bounds the policy rather
than proposing it -- a resident's own driveway is restricted to everyone else and they are still
entitled to walk down it, which is exactly why the design penalises instead of deleting
(see `access.py`).

Writes `data/restricted_walk_policy_grocery_walk.json`. Read-only on the layers; one graph
preparation per variant, about 2 minutes each.
"""
import json
import pathlib
import sys
import time

import geopandas as gpd
import numpy as np
import osmnx as ox

V2 = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V2))
sys.path.insert(1, str(V2 / "spikes"))
from _common import ACCEPTED_PLACES, GRID, load_roads_graph  # noqa: E402

from locfinder.places.categories import select_overture  # noqa: E402
from locfinder.traveltime import access as access_mod  # noqa: E402
from locfinder.traveltime.components import largest_component  # noqa: E402
from locfinder.traveltime.csr import graph_to_cost_time_csr  # noqa: E402
from locfinder.traveltime.layer import build_layer_surface  # noqa: E402
from locfinder.traveltime.speeds import add_travel_times, symmetrise  # noqa: E402

POI_SNAP_MAX_M = 300.0
MAX_ACCESS_M = 200.0
HORIZON_S = 120.0 * 60.0
MODE = "walk"
CATEGORY = "grocery"
THRESHOLDS_MIN = (10, 15, 25, 45)

BUILDINGS = V2 / "data" / "layers" / "own_triangle_buildings_per_cell.npy"
OUT = V2 / "data" / "restricted_walk_policy_grocery_walk.json"

# (label, walk penalty in seconds, drop restricted entirely)
VARIANTS = [
    ("as_published_120s", 120.0, False),
    ("penalty_600s", 600.0, False),
    ("penalty_1800s", 1800.0, False),
    ("no_restricted", 120.0, True),
]


def surface(penalty_s: float, drop_restricted: bool) -> tuple[np.ndarray, dict]:
    # The penalty lives in a module constant that `add_travel_times` reads, so overriding it here
    # exercises the real code path rather than a reimplementation of it. Restored in `finally`.
    original = access_mod.RESTRICTED_PENALTY_S[MODE]
    access_mod.RESTRICTED_PENALTY_S[MODE] = penalty_s
    try:
        G = load_roads_graph()
        G = ox.project_graph(G, to_crs=GRID.crs)
        G = add_travel_times(G, mode=MODE)
        restricted = sum(1 for _u, _v, d in G.edges(data=True) if d.get("access_restricted"))
        if drop_restricted:
            G.remove_edges_from([(u, v, k) for u, v, k, d in G.edges(keys=True, data=True)
                                 if d.get("access_restricted")])
        if MODE == "walk":
            G = symmetrise(G)
        G.remove_nodes_from([n for n, d in G.degree() if d == 0])
        G, comp = largest_component(G)
        cost_csr, time_csr, index = graph_to_cost_time_csr(G)

        places = gpd.read_parquet(ACCEPTED_PLACES).to_crs(GRID.crs)
        sel = select_overture(places, CATEGORY)
        cent = sel.geometry.centroid
        nodes, dists = ox.nearest_nodes(G, cent.x.to_numpy(), cent.y.to_numpy(),
                                        return_dist=True)
        keep = np.asarray(dists) <= POI_SNAP_MAX_M
        dest_idx = sorted({index[n] for n, k in zip(nodes, keep) if k})

        surf = build_layer_surface(
            G, (cost_csr, time_csr), index, GRID, dest_idx=dest_idx, mode=MODE,
            target=CATEGORY, engine="own-graph", cutoff_min=HORIZON_S / 60.0,
            max_access_m=MAX_ACCESS_M, places_selected=len(sel),
        )
        meta = {"restricted_edges": restricted, "edges": G.number_of_edges(),
                "destination_nodes": len(dest_idx), "components": comp.summary}
        return np.asarray(surf.seconds, dtype=np.float64), meta
    finally:
        access_mod.RESTRICTED_PENALTY_S[MODE] = original


def main() -> int:
    buildings = np.load(BUILDINGS)
    # the cell the owner walked, carried through as the worked example
    WALKED = (286, 129)

    out: dict = {"thresholds_min": list(THRESHOLDS_MIN), "walked_cell": list(WALKED),
                 "variants": {}}
    surfaces: dict[str, np.ndarray] = {}
    for label, penalty, drop in VARIANTS:
        t = time.perf_counter()
        secs, meta = surface(penalty, drop)
        surfaces[label] = secs
        meta.update(walk_penalty_s=penalty, dropped_restricted=drop,
                    elapsed_s=round(time.perf_counter() - t, 1),
                    unknown_cells=int((~np.isfinite(secs)).sum()),
                    unknown_buildings=int(buildings[~np.isfinite(secs)].sum()),
                    walked_cell_seconds=(None if not np.isfinite(secs[WALKED])
                                         else round(float(secs[WALKED]), 1)))
        out["variants"][label] = meta
        print(f"{label:<18} {meta['elapsed_s']:>6.1f}s  "
              f"{meta['restricted_edges']:>7,} restricted  "
              f"{meta['unknown_cells']:>7,} unknown  "
              f"walked cell {meta['walked_cell_seconds']}", flush=True)

    base = surfaces["as_published_120s"]
    print(f"\n{'T':>4}  {'PASS bldgs':>12}" +
          "".join(f"{lab.replace('_', ' '):>22}" for lab, _p, _d in VARIANTS[1:]))
    print("-" * (18 + 22 * (len(VARIANTS) - 1)))
    out["lost"] = {}
    for tmin in THRESHOLDS_MIN:
        lim = 60.0 * tmin
        b = np.isfinite(base) & (base <= lim)
        row = {"pass_cells": int(b.sum()), "pass_buildings": int(buildings[b].sum())}
        cells = f"{tmin:>4}  {int(buildings[b].sum()):>12,}"
        for label, _p, _d in VARIANTS[1:]:
            s = surfaces[label]
            still = np.isfinite(s) & (s <= lim)
            lost = b & ~still
            lb = int(buildings[lost].sum())
            share = lb / buildings[b].sum() if buildings[b].sum() else 0.0
            row[label] = {"lost_cells": int(lost.sum()), "lost_buildings": lb,
                          "lost_building_share": float(share)}
            cells += f"{lb:>13,} ({share:>5.2%})"
        out["lost"][str(tmin)] = row
        print(cells)

    print(f"\nthe cell the owner walked, {WALKED}:")
    for label, _p, _d in VARIANTS:
        v = out["variants"][label]["walked_cell_seconds"]
        verdict = "UNKNOWN" if v is None else (
            f"{v / 60:.1f} min, 15-min {'PASS' if v <= 900 else 'FAIL'}")
        print(f"  {label:<18} {verdict}")
    print("  observed             ~25.0 min, 1.3 miles")

    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\nwrote {OUT.relative_to(V2)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
