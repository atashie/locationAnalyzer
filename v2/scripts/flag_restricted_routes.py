"""Step 8 — which published answers depend on a restricted way, and what the owner owes about it.

**The commitment this discharges.** The owner's 2026-11-10 decision kept the restricted-walk
penalty at 120 s rather than raising it, on the condition that the gap is **disclosed rather than
priced away**. `docs/engineering-notes/project-phase1-s3-soft-way-dependence.md` recorded the
disclosure as *specified and manual*: `explain_journey.py` can say whether one journey's route uses
a restricted edge, "but no per-cell flag is recorded in the layer bundle, no aggregation is
defined, and nothing computes the statistic". This is the aggregation.

**Why the edge count is not the answer.** There are 126,197 restricted walk edges in the Triangle
extract, so "the graph contains restricted ways" is true everywhere and tells a household nothing.
The question is whether **the route behind this cell's number** uses one, which depends on the
cost-optimal path and so has to be propagated, not inferred. `arrival_with_route_flag` carries it
along the same predecessor forest that carries the reported time.

**What this cannot do.** It cannot say the estimate is wrong. The one walked journey found ~25
minutes against a published 13.5 because a private track won on cost, so the direction of the known
bias is **optimistic** — but one journey is existence evidence, not a rate, and nothing here
measures the error. The statistic the owner's decision owes is the **signed error on
restricted-route journeys**, and it needs walked journeys: this script computes the denominator and
leaves the numerator empty, which is the honest shape.

Outputs `docs/experiments/s3-8-restricted-routes.json` and prints the one-page report's numbers.

    python scripts/flag_restricted_routes.py
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

import geopandas as gpd
import numpy as np
import osmnx as ox

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "spikes"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from _common import ACCEPTED_PLACES, METRO, METRO_DIR, load_roads_graph, stamp  # noqa: E402
from locfinder.measure.frames import structure_population          # noqa: E402
from locfinder.places.categories import select_overture            # noqa: E402
from locfinder.status import (CATEGORY_COST_SELECTED, ENGINES,      # noqa: E402
                              Criterion, Surface, Verdict, evaluate, node_reasons)
from locfinder.traveltime.arrival import (arrival_seconds,          # noqa: E402
                                          arrival_with_route_flag)
from locfinder.traveltime.components import largest_component       # noqa: E402
from locfinder.traveltime.csr import graph_to_cost_time_flag_csr    # noqa: E402
from locfinder.traveltime.snap import (EdgeIndex,                 # noqa: E402
                                       cell_arrival_with_provenance,
                                       cell_route_flag)
from locfinder.traveltime.speeds import add_travel_times, symmetrise  # noqa: E402

MODE = "walk"
CATEGORY = "grocery"
POI_SNAP_MAX_M = 300.0
MAX_ACCESS_M = 200.0
HORIZON_S = 7200.0
THRESHOLDS_MIN = (10, 15, 25, 45)

V2 = pathlib.Path(__file__).resolve().parents[1]
ARTIFACT = V2.parent / "docs" / "experiments" / "s3-8-restricted-routes.json"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=pathlib.Path, default=ARTIFACT)
    args = ap.parse_args(argv)

    grid = METRO.grid()
    t0 = time.perf_counter()
    G = load_roads_graph()
    G = ox.project_graph(G, to_crs=grid.crs)
    G = add_travel_times(G, mode=MODE)
    G = symmetrise(G)
    G.remove_nodes_from([n for n, d in G.degree() if d == 0])
    G, _comp = largest_component(G)
    restricted_edges = sum(1 for _u, _v, d in G.edges(data=True) if d.get("access_restricted"))
    cost_csr, time_csr, flag_csr, index = graph_to_cost_time_flag_csr(G)
    print(f"graph ready in {time.perf_counter() - t0:.0f}s: {G.number_of_edges():,} edges, "
          f"{restricted_edges:,} restricted", flush=True)

    places = gpd.read_parquet(ACCEPTED_PLACES).to_crs(grid.crs)
    sel = select_overture(places, CATEGORY)
    cen = sel.geometry.centroid
    nodes, dists = ox.nearest_nodes(G, cen.x.to_numpy(), cen.y.to_numpy(), return_dist=True)
    keep = np.asarray(dists, dtype=float) <= POI_SNAP_MAX_M
    dest_idx = sorted({index[n] for n, k in zip(nodes, keep) if k})

    seconds_n, selected_n, flagged_n = arrival_with_route_flag(
        cost_csr, time_csr, flag_csr, dest_idx=dest_idx)
    node_cost = arrival_seconds(cost_csr, dest_idx=dest_idx)
    reasons = node_reasons(seconds_n, ENGINES["own-graph"], search_bounded=False)
    idx = EdgeIndex.from_graph(G, index)

    report = {
        "what_this_is": ("step 8's disclosure aggregation: which published answers depend on a "
                         "restricted way. The owner's 2026-11-10 decision to keep the 120 s "
                         "penalty was conditional on disclosing this gap rather than pricing it "
                         "away"),
        "built": stamp(), "mode": MODE, "category": CATEGORY,
        "graph": {"edges": G.number_of_edges(), "restricted_edges": restricted_edges,
                  "destination_nodes": len(dest_idx)},
        "nodes": {"reachable": int(np.isfinite(seconds_n).sum()),
                  "reachable_with_a_restricted_route": int(flagged_n.sum())},
        "units": {},
        "which_unit_a_disclosure_figure_may_use": (
            "structures_at_their_published_cell. The product answers for a cell, so that is what a "
            "household is told; the coordinate figures are model sensitivity. Pass 46 F2 found the "
            "first version's headline built on the coordinate unit -- 8,033 of 78,627 at T=10 -- "
            "where the published cell gives 7,276 of 80,067, and 23,330 structures carry a "
            "different flag between the two"),
        "what_is_still_not_the_shipped_answer": (
            "even the published-cell figure is the SOURCE grid's. The browser receives a WGS84 "
            "re-tiling and MapLibre places it in Mercator, each of which moves the lookup again "
            "(see s3-5-browser-path). And no flag plane is shipped at all, so every count here is "
            "a CANDIDATE disclosure rather than one any household can currently receive"),
        "the_statistic_this_does_not_compute": (
            "the SIGNED ERROR on restricted-route journeys. That needs walked journeys: this "
            "computes the denominator -- which answers are in the class -- and leaves the "
            "numerator empty. One walked journey found about 25 minutes against a published 13.5, "
            "so the known direction of the bias is OPTIMISTIC, but one journey is existence "
            "evidence and not a rate"),
    }

    # THREE populations, because they answer three different questions, and pass 46 F2 found the
    # headline answering the wrong one. `structures_at_their_own_coordinate` is model sensitivity;
    # `structures_at_their_published_cell` is what the product actually tells that household, and
    # is the only one a disclosure figure may be built on. Passes 44, 45 and 46 each found a claim
    # resting on the coordinate unit where the published unit was meant, so both are now always
    # computed and the published one leads.
    xs, ys = grid.cell_centers_xy()
    populations = {"grid_cells": (xs.ravel(), ys.ravel(), None)}
    ids, pts, _total = structure_population(
        METRO_DIR / "overture_buildings_accepted.parquet", grid)
    populations["structures_at_their_own_coordinate"] = (pts[:, 0], pts[:, 1], len(pts))
    col = np.clip(np.floor((pts[:, 0] - grid.x_min) / grid.cell_m), 0, grid.ncols - 1)
    row = np.clip(np.floor((grid.y_max - pts[:, 1]) / grid.cell_m), 0, grid.nrows - 1)
    populations["structures_at_their_published_cell"] = (
        grid.x_min + (col + 0.5) * grid.cell_m,
        grid.y_max - (row + 0.5) * grid.cell_m,
        len(pts))

    for name, (px, py, count) in populations.items():
        secs, reason, lower = cell_arrival_with_provenance(
            idx, seconds_n, px, py, mode=MODE, max_access_m=MAX_ACCESS_M, horizon_s=HORIZON_S,
            node_reason=reasons, node_cost=node_cost)
        # The published journey's flag, resolved through the same branch choice the seconds came
        # from -- matched edge and network path both -- rather than from the nearest node.
        att_flag = cell_route_flag(
            idx, seconds_n, px, py, mode=MODE, max_access_m=MAX_ACCESS_M,
            node_flag=flagged_n, node_cost=node_cost, cutoff_s=None)
        surf = Surface(mode=MODE, engine="own-graph", target=CATEGORY,
                       aggregation=CATEGORY_COST_SELECTED, horizon_s=HORIZON_S,
                       seconds=secs, reason=reason, min_possible_s=lower).validate()
        entry = {"population": int(count or len(px)), "thresholds": {}}
        for t_min in THRESHOLDS_MIN:
            v = evaluate(Criterion(label=f"g{t_min}", mode=MODE, target=CATEGORY,
                                   kind="category", threshold_s=float(t_min) * 60.0), surf)
            included = v == int(Verdict.INCLUDED)
            entry["thresholds"][str(t_min)] = {
                "included": int(included.sum()),
                "included_on_a_restricted_route": int((included & att_flag).sum()),
                "share_of_included": (float((included & att_flag).sum()) / float(included.sum())
                                      if included.sum() else None),
            }
        entry["answered_at_all"] = int(np.isfinite(secs).sum())
        entry["answered_on_a_restricted_route"] = int((np.isfinite(secs) & att_flag).sum())
        report["units"][name] = entry

    args.out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print_summary(report)
    print(f"\nwrote {args.out}")
    return 0


def print_summary(report: dict) -> None:
    g = report["graph"]
    print(f"\n{g['restricted_edges']:,} of {g['edges']:,} walk edges are restricted, which is why "
          f"an edge count discloses nothing")
    n = report["nodes"]
    print(f"nodes: {n['reachable']:,} reachable, "
          f"{n['reachable_with_a_restricted_route']:,} whose cost-optimal route uses a restricted "
          f"way ({n['reachable_with_a_restricted_route'] / max(n['reachable'], 1):.1%})")
    for name, entry in report["units"].items():
        print(f"\n{name}: {entry['population']:,} in the population, "
              f"{entry['answered_at_all']:,} answered, "
              f"{entry['answered_on_a_restricted_route']:,} of those on a restricted route")
        for t_min, row in entry["thresholds"].items():
            share = row["share_of_included"]
            print(f"  T={t_min:>2} min: {row['included']:>7,} included, "
                  f"{row['included_on_a_restricted_route']:>7,} of them on a restricted route"
                  + (f" ({share:.1%})" if share is not None else ""))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
