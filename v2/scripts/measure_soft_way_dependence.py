"""How much of the published walk layer depends on OSM `track` and `path` ways?

**Named product risk** (plan §0's rule: no apparatus without one): a PASS that rests on an unpaved
forestry track or an informal trail is a recommendation a household cannot use, and neither E1 nor
E2 can see it -- both sides of those estimands read the same road graph. The owner walked
band15min_pass-03, found ~25 minutes against a published 13.5, and
`diagnose_track_dependence.py` showed the cell's whole PASS resting on an unnamed `track` 35.5 m
away: 811 s published against 1,787 s with `track` removed.

One row is an anecdote. This measures the whole surface:

* cells and **buildings** passing each released threshold, as published and with the soft classes
  removed;
* the share of each threshold's PASS that does not survive;
* how many cells become UNKNOWN because their only access was a soft way.

The fourth variant exists because the third was not the right question. Removing `track` from the
walked cell moved its route onto **476 m of an unnamed 531 m `footway`** — same verification
problem, different class — so a class-only knob relocates the dependence instead of removing it.
`no_unnamed_informal` drops `track`/`path`/`footway`/`service` **only where the way has no name**,
which separates a sidewalk from a trail about as well as the tags allow.

Writes `data/soft_way_dependence_grocery_walk.json`. Read-only on the layers. Four graph
preparations plus four full surfaces, about 11 minutes.
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
from _common import ACCEPTED_PLACES, GRAPH_CACHE, GRID  # noqa: E402

from locfinder.places.categories import select_overture  # noqa: E402
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
RASTER = V2 / "data" / "layers" / "own_triangle_grocery_walk.npy"
OUT = V2 / "data" / "soft_way_dependence_grocery_walk.json"

# A highway class alone does not say whether a way exists and is usable on the ground. A **named**
# footway beside a street is a sidewalk, and removing those would cripple a pedestrian graph and
# make the resulting number meaningless. An **unnamed** 531 m footway through woods is a trail --
# and the no-track counterfactual for the cell the owner walked leaned on exactly that, which is
# how this variant came to be needed. So the sharper knob is class AND namelessness, measured here
# beside the class-only ones rather than substituted for them.
INFORMAL = {"track", "path", "footway", "service"}

VARIANTS = {
    "as_published": (set(), False),
    "no_track": ({"track"}, False),
    "no_track_or_path": ({"track", "path"}, False),
    "no_unnamed_informal": (INFORMAL, True),
}


def classes(data) -> set:
    hw = data.get("highway")
    if isinstance(hw, (list, tuple)):
        return {str(x) for x in hw}
    return {str(hw)} if hw else set()


def unnamed(data) -> bool:
    n = data.get("name")
    if isinstance(n, (list, tuple)):
        return not any(str(x).strip() for x in n)
    return not (n and str(n).strip())


def surface(drop: set, only_unnamed: bool = False) -> tuple[np.ndarray, dict]:
    G = ox.load_graphml(GRAPH_CACHE)
    G = ox.project_graph(G, to_crs=GRID.crs)
    removed = 0
    if drop:
        doomed = [(u, v, k) for u, v, k, d in G.edges(keys=True, data=True)
                  if (classes(d) & drop) and (unnamed(d) if only_unnamed else True)]
        removed = len(doomed)
        G.remove_edges_from(doomed)
    G = add_travel_times(G, mode=MODE)
    if MODE == "walk":
        G = symmetrise(G)
    G.remove_nodes_from([n for n, d in G.degree() if d == 0])
    G, comp = largest_component(G)
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)

    places = gpd.read_parquet(ACCEPTED_PLACES).to_crs(GRID.crs)
    sel = select_overture(places, CATEGORY)
    cent = sel.geometry.centroid
    nodes, dists = ox.nearest_nodes(G, cent.x.to_numpy(), cent.y.to_numpy(), return_dist=True)
    keep = np.asarray(dists) <= POI_SNAP_MAX_M
    dest_idx = sorted({index[n] for n, k in zip(nodes, keep) if k})

    # Call the published builder rather than reassembling its steps. My first version did the
    # latter and passed `cutoff_s` into the arrival search; `layer.py:139` runs that search
    # UNBOUNDED on purpose -- "which is what entitles this call to NO_PATH" -- and applies the
    # horizon to the final per-cell total instead. Truncating node times first moved 7,246 cells,
    # so the baseline was not the shipped surface.
    surf = build_layer_surface(
        G, (cost_csr, time_csr), index, GRID, dest_idx=dest_idx, mode=MODE,
        target=CATEGORY, engine="own-graph", cutoff_min=HORIZON_S / 60.0,
        max_access_m=MAX_ACCESS_M, places_selected=len(sel),
    )
    meta = {"edges_removed": removed, "edges": G.number_of_edges(),
            "destination_nodes": len(dest_idx), "components": comp.summary}
    return np.asarray(surf.seconds, dtype=np.float64), meta


def main() -> int:
    buildings = np.load(BUILDINGS)
    total_buildings = int(buildings.sum())
    print(f"grid {GRID.nrows}x{GRID.ncols} = {GRID.nrows * GRID.ncols:,} cells, "
          f"{total_buildings:,} buildings")

    out: dict = {"thresholds_min": list(THRESHOLDS_MIN),
                 "total_cells": int(GRID.nrows * GRID.ncols),
                 "total_buildings": total_buildings, "variants": {}}
    surfaces: dict[str, np.ndarray] = {}

    for name, (drop, only_unnamed) in VARIANTS.items():
        t = time.perf_counter()
        secs, meta = surface(drop, only_unnamed)
        surfaces[name] = secs
        meta["seconds_s"] = round(time.perf_counter() - t, 1)
        if name == "as_published":
            # The baseline is CURRENT CODE on the full graph, because that is what the three
            # variants have to be compared against for the counterfactual to mean anything.
            #
            # It does NOT reproduce the committed raster, and that is a separate finding rather
            # than a failure here: the raster was built 2026-11-04 13:42 and verified
            # bit-identical at 14:43, and `ab01ffa` at 21:12 then fixed `symmetrise`, which had
            # been suppressing legitimate pedestrian reverse edges in the shipped walk graph.
            # 7,246 cells (2.19%) holding 11,436 buildings differ; verdict movement is 6-15 cells
            # per threshold. Reported, not absorbed.
            stored = np.load(RASTER)
            identical = bool(np.array_equal(stored, secs.astype(np.float32), equal_nan=True))
            meta["matches_committed_raster"] = identical
            meta["cells_differing_from_committed"] = int(
                (stored != secs.astype(np.float32)).sum())
            print(f"  baseline is current code. Matches the committed {RASTER.name}: "
                  f"{identical}" + ("" if identical else
                  f" ({meta['cells_differing_from_committed']:,} cells differ -- the raster "
                  "predates the ab01ffa symmetrise fix and needs a rebuild)"))
        per_threshold = {}
        for tmin in THRESHOLDS_MIN:
            lim = 60.0 * tmin
            ok = np.isfinite(secs) & (secs <= lim)
            per_threshold[str(tmin)] = {
                "pass_cells": int(ok.sum()),
                "pass_buildings": int(buildings[ok].sum()),
            }
        meta["per_threshold"] = per_threshold
        meta["unknown_cells"] = int((~np.isfinite(secs)).sum())
        meta["unknown_buildings"] = int(buildings[~np.isfinite(secs)].sum())
        out["variants"][name] = meta
        print(f"{name:<18} {meta['seconds_s']:>6.1f}s  {meta['edges_removed']:>7,} edges removed  "
              f"{meta['unknown_cells']:>7,} unknown cells", flush=True)

    # ---- what the soft ways are holding up ---------------------------------------------------
    pub = surfaces["as_published"]
    out["lost"] = {}
    print(f"\n{'T':>4}  {'PASS cells':>12} {'lost(trk)':>11} {'lost(t+p)':>11} "
          f"{'lost(unnamed)':>14}   {'PASS buildings':>15} {'bldg lost':>11}  {'share':>7}")
    print("-" * 108)
    for tmin in THRESHOLDS_MIN:
        lim = 60.0 * tmin
        base = np.isfinite(pub) & (pub <= lim)
        row = {"pass_cells": int(base.sum()), "pass_buildings": int(buildings[base].sum())}
        for name in ("no_track", "no_track_or_path", "no_unnamed_informal"):
            s = surfaces[name]
            still = np.isfinite(s) & (s <= lim)
            lost = base & ~still
            row[name] = {
                "lost_cells": int(lost.sum()),
                "lost_buildings": int(buildings[lost].sum()),
                "lost_cell_share": float(lost.sum() / base.sum()) if base.any() else 0.0,
                "lost_building_share": (float(buildings[lost].sum() / buildings[base].sum())
                                        if buildings[base].sum() else 0.0),
            }
        out["lost"][str(tmin)] = row
        a, b, c = row["no_track"], row["no_track_or_path"], row["no_unnamed_informal"]
        print(f"{tmin:>4}  {row['pass_cells']:>12,} {a['lost_cells']:>11,} "
              f"{b['lost_cells']:>11,} {c['lost_cells']:>14,}   "
              f"{row['pass_buildings']:>15,} {c['lost_buildings']:>11,}  "
              f"{c['lost_building_share']:>6.2%}")

    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\nwrote {OUT.relative_to(V2)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
