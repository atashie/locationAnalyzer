"""Persist **which grocery** each published answer was measured to — the second thing a household
is owed, and the one the layer bundle could not say.

`arrival_with_selected_destination` and `cell_selected_destination` already compute it. Nothing
kept it. So the audit sheet could record "ten minutes" and not "ten minutes to where", which is
what made the owner's walked journey unscorable: `measure/e3.py` needs the reported time and the
observed time *for the same journey*, and nothing in the artifact identified the journey.

**THE PRESENTATION RULE IS THE OWNER'S, 2026-11-13: the node plus the set, and the card chooses.**
A destination *node* is not a shop — 550 grocery places snap to 510 nodes and 75 share one — so the
plane names the node and a side table carries every place on it. That is not a convenience: the
cost model routed to the node, so **the set is the truthful answer** and picking one of them is a
presentation decision the data must not pre-empt. A card may show one, or "one of 3 at this
corner", but the artifact may not assert which.

TWO INVARIANTS, AND THE SECOND IS STRONGER THAN THE FLAG'S.

  A destination may only be named where the status is OK. Same as the route flag: only a published
  journey has a destination.

  **And where the status IS OK a destination MUST be named.** This is the direction the flag plane
  cannot have. Pass 48 F3 established that a *clear* flag asserts nothing and so cannot be checked
  from the plane's own contents. `DEST_NONE` beside a published time is different: it is a
  contradiction, because a published time is a time *to somewhere*. So this plane is checkable in
  both directions and the hole F3 found does not exist for it.

LICENSING, which gates whether the names may be published at all. The grocery rows carry
`CDLA-Permissive-2.0` (98,982), `Apache-2.0` (7,082) and `CC0-1.0` (1,420) — no ODbL, and none of
the contractually restricted sources decision 17 forbids: no Google place ids, no RentCast, no
MLS/IDX, no portal terms. So the names are publishable with attribution. The side table is written
as a **separate artifact with its own licence block** rather than merged into the travel-time
layer, because that layer is ODbL-published and ODbL is share-alike: keeping the two apart is what
stops a permissively licensed name table being swept into a share-alike database. Only the fields
needed to name a destination are carried — GERS id, name, brand, category. Not phones, emails,
websites, socials, or any upstream provider record id.

    v2/.venv/Scripts/python.exe scripts/persist_selected_destination.py --write-raster
    v2/.venv/Scripts/python.exe scripts/persist_selected_destination.py --write-raster --ties
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys
import time

import geopandas as gpd
import numpy as np
import osmnx as ox

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "spikes"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from _common import ACCEPTED_PLACES, METRO, load_roads_graph, stamp      # noqa: E402
from locfinder import wire                                               # noqa: E402
from locfinder.places.categories import select_overture                  # noqa: E402
from locfinder.status import ENGINES, node_reasons                       # noqa: E402
from locfinder.traveltime.arrival import (arrival_seconds,               # noqa: E402
                                          arrival_with_selected_destination)
from locfinder.traveltime.components import largest_component            # noqa: E402
from locfinder.traveltime.csr import graph_to_cost_time_csr              # noqa: E402
from locfinder.traveltime.snap import EdgeIndex, cell_selected_destination  # noqa: E402
from locfinder.traveltime.speeds import add_travel_times, symmetrise     # noqa: E402

MODE = "walk"
CATEGORY = "grocery"
POI_SNAP_MAX_M = 300.0
MAX_ACCESS_M = 200.0
HORIZON_S = 7200.0
#: The published layer this destination plane belongs to, beside its surface triple.
STEM = "own_triangle_grocery_walk"

V2 = pathlib.Path(__file__).resolve().parents[1]
LAYERS = V2 / "data" / "layers"
ARTIFACT = V2.parent / "docs" / "experiments" / "s3-9-selected-destination.json"


def place_record(row) -> dict:
    """The minimum that names a destination. Nothing more leaves the parquet."""
    names = row.get("names") or {}
    brand = (row.get("brand") or {}).get("names") or {}
    return {
        "gers_id": row["id"],
        "name": names.get("primary") or names.get("common"),
        "brand": brand.get("primary") or brand.get("common"),
        "category": row.get("basic_category"),
        "operating_status": row.get("operating_status"),
        "licence": row.get("licence"),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=pathlib.Path, default=ARTIFACT)
    ap.add_argument("--write-raster", action="store_true",
                    help="persist the per-cell destination ordinal and the side table beside the "
                         "layer's surface triple, which is what 'published in the layer bundle' "
                         "means. The exporter is graph-free and reads them from there")
    ap.add_argument("--ties", action="store_true",
                    help="also measure whether the SELECTED DESTINATION moves under a node "
                         "relabelling, which costs three extra sweeps. Pass 48 found the route "
                         "flag is order-dependent at an exact cost tie; the destination is the "
                         "same argmin and it is SHOWN to a household, so it matters more")
    args = ap.parse_args(argv)

    grid = METRO.grid()
    t0 = time.perf_counter()
    G = load_roads_graph()
    G = ox.project_graph(G, to_crs=grid.crs)
    G = add_travel_times(G, mode=MODE)
    G = symmetrise(G)
    G.remove_nodes_from([n for n, d in G.degree() if d == 0])
    G, _comp = largest_component(G)
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
    print(f"graph ready in {time.perf_counter() - t0:.0f}s: {G.number_of_edges():,} edges",
          flush=True)

    places = gpd.read_parquet(ACCEPTED_PLACES).to_crs(grid.crs)
    sel_places = select_overture(places, CATEGORY)
    cen = sel_places.geometry.centroid
    nodes, dists = ox.nearest_nodes(G, cen.x.to_numpy(), cen.y.to_numpy(), return_dist=True)
    keep = np.asarray(dists, dtype=float) <= POI_SNAP_MAX_M

    # node index -> the places that snap to it, in Overture id order so a rebuild reproduces.
    by_node: dict[int, list[dict]] = collections.defaultdict(list)
    for (_pos, row), node, k in zip(sel_places.iterrows(), nodes, keep):
        if k:
            by_node[index[node]].append(place_record(row))
    dest_idx = sorted(by_node)
    print(f"{len(sel_places):,} {CATEGORY} places, {int(keep.sum()):,} within "
          f"{POI_SNAP_MAX_M:g} m of a node, on {len(dest_idx):,} distinct nodes", flush=True)

    seconds_n, selected_n = arrival_with_selected_destination(
        cost_csr, time_csr, dest_idx=dest_idx)
    node_cost = arrival_seconds(cost_csr, dest_idx=dest_idx)
    _reasons = node_reasons(seconds_n, ENGINES["own-graph"], search_bounded=False)
    idx = EdgeIndex.from_graph(G, index)

    xs, ys = grid.cell_centers_xy()
    cell_node = cell_selected_destination(
        idx, seconds_n, xs.ravel(), ys.ravel(), mode=MODE, max_access_m=MAX_ACCESS_M,
        selected=selected_n, node_cost=node_cost, cutoff_s=HORIZON_S,
    ).reshape(grid.nrows, grid.ncols)

    # ---- the ordinal space, assigned over the nodes a published answer ACTUALLY selects ----
    # Ordinals index the side table. They are assigned over the SELECTED nodes in node order, not
    # over every candidate node, because the plane's width is set by how many destinations the
    # product names and not by how many exist.
    chosen_nodes = sorted({int(v) for v in np.unique(cell_node) if v >= 0})
    ordinal_of = {node: i for i, node in enumerate(chosen_nodes)}
    print(f"{len(chosen_nodes):,} of {len(dest_idx):,} destination nodes are selected by at least "
          f"one cell", flush=True)

    set_sizes = collections.Counter(len(by_node[n]) for n in chosen_nodes)
    cells_by_set_size: collections.Counter = collections.Counter()
    for node in chosen_nodes:
        cells_by_set_size[len(by_node[node])] += int((cell_node == node).sum())

    report = {
        "what_this_is": ("which grocery each published answer was measured to. The plane names "
                         "the destination NODE and the side table carries every place on it, "
                         "because a node is not a shop and the cost model routed to the node"),
        "built": stamp(), "mode": MODE, "category": CATEGORY,
        "the_presentation_rule": (
            "the owner's decision, 2026-11-13: THE NODE PLUS THE SET, and the card chooses. The "
            "set is the truthful answer rather than a convenience -- the selection is a "
            "cost-argmin over NODES, so which of the places on the chosen node a household walks "
            "to is not something this pipeline computed and the artifact must not assert it"),
        "graph": {"edges": G.number_of_edges(), "nodes": int(cost_csr.shape[0])},
        "places": {
            "in_category": int(len(sel_places)),
            "within_snap_distance": int(keep.sum()),
            "snap_max_m": POI_SNAP_MAX_M,
            "distinct_destination_nodes": len(dest_idx),
            "nodes_carrying_more_than_one_place": int(
                sum(1 for n in dest_idx if len(by_node[n]) > 1)),
            "largest_set_on_one_node": max(len(v) for v in by_node.values()),
        },
        "cells": {
            "total": int(cell_node.size),
            "with_a_published_destination": int((cell_node >= 0).sum()),
            "distinct_destinations_selected": len(chosen_nodes),
            "why_this_number_sets_the_plane_width": (
                f"{len(chosen_nodes):,} distinct destinations are named by at least one cell. A "
                "dense ordinal over those fits a uint8 plane only if it is at most 254; "
                "scripts/price_destination_encodings.py prices the options on the real plane "
                "rather than assuming"),
        },
        "the_set_a_household_would_be_shown": {
            "destinations_by_set_size": {str(k): v for k, v in sorted(set_sizes.items())},
            "cells_by_set_size": {str(k): v for k, v in sorted(cells_by_set_size.items())},
            "cells_whose_destination_is_ambiguous": int(
                sum(v for k, v in cells_by_set_size.items() if k > 1)),
            "what_ambiguous_means_here": (
                "the cell's journey ends at a node carrying more than one grocery, so the "
                "artifact names a SET and not a shop. That is the honest state of the "
                "computation, not a defect to be resolved by picking one"),
        },
    }

    if args.ties:
        report["ties"] = measure_destination_ties(
            cost_csr, time_csr, dest_idx, selected_n, seconds_n)

    if args.write_raster:
        ordinals = np.full(cell_node.shape, wire.DEST_NONE, dtype=wire.DEST_DTYPE)
        for node, ordinal in ordinal_of.items():
            ordinals[cell_node == node] = ordinal
        if (cell_node >= 0).sum() != int((ordinals != wire.DEST_NONE).sum()):
            raise SystemExit("an ordinal was lost in translation from node ids")
        path = LAYERS / f"{STEM}_selected_destination.npy"
        np.save(path, ordinals)

        table = {
            "what_this_is": ("the side table the destination plane's ordinals index. Ordinal i "
                             "names destinations[i]; a cell holding DEST_NONE has no published "
                             "destination because it has no published journey"),
            "built": stamp(), "mode": MODE, "category": CATEGORY,
            "licence": {
                "this_table": sorted({p["licence"] for n in chosen_nodes for p in by_node[n]
                                      if p["licence"]}),
                "source": f"Overture {places['overture_release'].iloc[0]}",
                "why_it_is_a_separate_artifact": (
                    "the travel-time layer is ODbL-published and ODbL is share-alike. These names "
                    "are CDLA-Permissive-2.0, Apache-2.0 and CC0-1.0 -- permissive, and none of "
                    "the contractually restricted sources decision 17 forbids. Keeping the table "
                    "apart from the layer is what stops permissively licensed names being swept "
                    "into a share-alike database, and keeps decision 17's rule that an "
                    "ODbL-published artifact carries no restricted source"),
                "fields_deliberately_omitted": [
                    "phones", "emails", "websites", "socials", "addresses",
                    "upstream provider record ids"],
            },
            "node_is_not_a_shop": (
                "each entry names a NODE and the places on it. The selection is a cost-argmin "
                "over nodes, so where `places` has more than one entry the pipeline did not "
                "choose between them and neither may a reader of this file"),
            "destinations": [
                {"ordinal": ordinal_of[node], "node_index": node,
                 "place_count": len(by_node[node]), "places": by_node[node]}
                for node in chosen_nodes
            ],
        }
        (LAYERS / f"{STEM}_selected_destination_table.json").write_text(
            json.dumps(table, indent=2, default=str), encoding="utf-8")

        meta = {
            "built": stamp(), "mode": MODE, "category": CATEGORY,
            "cells": int(ordinals.size),
            "named": int((ordinals != wire.DEST_NONE).sum()),
            "distinct_destinations": len(chosen_nodes),
            "dtype": str(np.dtype(wire.DEST_DTYPE)),
            "dest_none": int(wire.DEST_NONE),
            # Pass 48 F3's lesson, applied at the start this time rather than after a review.
            "horizon_s": float(HORIZON_S),
            "surface_fingerprint": wire.surface_fingerprint(
                np.load(LAYERS / f"{STEM}.npy"), np.load(LAYERS / f"{STEM}_reason.npy")),
            "what_it_means": (
                "the ordinal of the destination the cell's PUBLISHED journey ends at, indexing "
                f"{STEM}_selected_destination_table.json. DEST_NONE where the cell has no "
                "published journey. Unlike the route flag, this plane is checkable in BOTH "
                "directions: a destination where the status is not OK is a contradiction, and so "
                "is DEST_NONE where the status IS OK, because a published time is a time to "
                "somewhere"),
        }
        (LAYERS / f"{STEM}_selected_destination_build.json").write_text(
            json.dumps(meta, indent=2, default=str), encoding="utf-8")
        print(f"\nwrote {path.name}: {meta['named']:,} of {meta['cells']:,} cells named, "
              f"{len(chosen_nodes):,} distinct destinations")

    args.out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    p = report["places"]
    print(f"\n{p['in_category']:,} places -> {p['distinct_destination_nodes']:,} nodes, "
          f"{p['nodes_carrying_more_than_one_place']:,} carrying more than one "
          f"(largest {p['largest_set_on_one_node']})")
    amb = report["the_set_a_household_would_be_shown"]["cells_whose_destination_is_ambiguous"]
    named = report["cells"]["with_a_published_destination"]
    print(f"{amb:,} of {named:,} answered cells ({amb / max(named, 1):.1%}) end at a node "
          f"carrying more than one grocery, so their destination is a SET")
    print(f"\nwrote {args.out}")
    return 0


def measure_destination_ties(cost_csr, time_csr, dest_idx, selected_n, seconds_n) -> dict:
    """Does the SELECTED DESTINATION move under a relabelling that cannot move the time?

    Pass 48 found the route flag is order-dependent at an exact cost tie and reaches 0 nodes on
    this graph. The destination is the same argmin and is **shown to a household**, so the same
    question is worth more here: two groceries equally cheap to the last bit means the name we
    print is decided by heap order.
    """
    n = cost_csr.shape[0]

    def permuted(q):
        inv = np.empty(n, dtype=np.int64)
        inv[q] = np.arange(n)
        s, sel = arrival_with_selected_destination(
            cost_csr[q, :][:, q].tocsr(), time_csr[q, :][:, q].tocsr(),
            dest_idx=sorted(int(inv[d]) for d in dest_idx))
        s_back = np.empty(n, dtype=float)
        sel_back = np.empty(n, dtype=np.int64)
        s_back[q] = s
        # `sel` holds permuted node ids; map them back before comparing.
        sel_back[q] = np.where(sel >= 0, q[np.where(sel >= 0, sel, 0)], -1)
        return s_back, sel_back

    rng = np.random.default_rng(20261113)
    rows = {}
    for name, q in (("reversed", np.arange(n)[::-1].copy()),
                    ("random_seed_20261113", rng.permutation(n)),
                    ("random_seed_20261113_second", rng.permutation(n))):
        s, sel = permuted(q)
        both = np.isfinite(seconds_n) & np.isfinite(s)
        rows[name] = {
            "reachable_in_both": int(both.sum()),
            "seconds_differing": int((seconds_n[both] != s[both]).sum()),
            "destination_moved": int(((selected_n != sel) & both).sum()),
        }
        print(f"ties {name}: destination moved on {rows[name]['destination_moved']:,}, "
              f"seconds on {rows[name]['seconds_differing']:,}", flush=True)
    total = sum(r["destination_moved"] for r in rows.values())
    return {
        "what_this_is": ("whether the destination a household would be SHOWN is a property of the "
                         "published answer or of the traversal order"),
        "labellings": rows,
        "total_destination_moves": total,
        "the_control_that_makes_a_zero_meaningful": (
            "scripts/measure_tie_flag.py holds the four-node construction and its positive "
            "control. The instrument is the same permutation; this reuses it on the destination "
            "rather than the flag"),
        "what_it_means": (
            "a non-zero here is a NAME decided by heap order, which is worse than a flag decided "
            "that way because the name is shown. A zero says exact bit-level cost ties between "
            "different destinations do not occur on this graph, and remains latent: quantising "
            "the cost would manufacture them"
            if total else
            "exact bit-level cost ties between different destinations do not occur on this graph, "
            "so the destination is well defined here. It is latent, not absent -- quantising the "
            "cost would manufacture ties, and then the NAME shown would depend on heap order"),
    }


if __name__ == "__main__":
    raise SystemExit(main())
