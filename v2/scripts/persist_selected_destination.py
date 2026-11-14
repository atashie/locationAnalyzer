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
import math
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
from locfinder.traveltime.snap import (EdgeIndex,                        # noqa: E402
                                       cell_seconds_from_arrival,
                                       cell_selected_destination)
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


def scalar(value):
    """A missing value is `None`, never a float NaN.

    Pass 49 finding 2 was a release blocker this cost. `brand` and `operating_status` arrive from
    the parquet as float NaN where the record has none; `json.dumps` writes those as the bare
    token `NaN`, which is not JSON. 85 of them reached the published table, so `JSON.parse` --
    and therefore the browser's `Response.json()` -- threw before the worker was constructed and
    the page could not display a destination at all. Nothing in 71 conformance checks saw it,
    because every one of them built its own fixture.

    `None` is the right value for the same reason `null` is right in the wire format: "this record
    does not say" is a statement the format has to be able to make.
    """
    if value is None:
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    # numpy scalars and pandas NA both answer to this, and neither is JSON-serialisable.
    try:
        if value != value:  # NaN is the only value that is not equal to itself.
            return None
    except (TypeError, ValueError):
        pass
    return value


# The known answer of `destination_tie_control`, named here so the control and the gate that
# interprets it cannot drift apart. Pass 50 finding G5: movement is only evidence that an
# instrument works if the answer it moves between is the right one.
CONTROL_SECONDS = 300.0
CONTROL_DESTINATIONS = [0, 1]


def check_plane_describes_the_surface(ordinals, stored, recomputed, horizon_s: float,
                                      *, label: str) -> dict:
    """Refuse to stamp a destination plane with a surface fingerprint it has not earned.

    **Pass 49 finding 1** put this check here at all: the fingerprint was taken of whatever
    `<stem>.npy` happened to hold, with nothing establishing that the plane and that surface
    agreed, so a fresh destination computation could be blessed against stale published seconds.
    Pass 48's F3 lesson was to bind a derived plane to its surface; the binding has to be earned.

    **Pass 50 finding A2** showed the first version did not earn it. It compared only the
    journey-PRESENCE masks, and 256,276 of this surface's cells can have 60 seconds added while
    staying finite and within the horizon -- every one of their published minutes changes and the
    mask does not move. So the values are compared too.

    The surface is stored as `float32` and the recomputation is `float64`. Comparing them directly
    disagrees at 251,506 cells by at most one float32 ULP, which is 0.00049 s at 7,200 s: storage
    precision, not disagreement. So the recomputation is cast the way the surface was written and
    compared **exactly**. A cast is deterministic, which leaves no tolerance to argue about: a
    surface written from this computation is bit-identical to it, and one differing bit is a real
    difference.

    It is a function rather than a block inside `main` so it can be given a wrong surface in a
    test. A gate buried in a 400-line build step cannot be shown to fail, and a gate never shown
    to fail is decoration.
    """
    stored = np.asarray(stored)
    as_stored = np.asarray(recomputed).astype(stored.dtype)
    journey = np.isfinite(stored) & (stored <= horizon_s)
    named = np.asarray(ordinals) != wire.DEST_NONE
    orphan = int((named & ~journey).sum())
    missing = int((journey & ~named).sum())
    if orphan or missing:
        raise SystemExit(
            f"this destination plane names {orphan:,} cells the surface gives no journey and "
            f"leaves {missing:,} of the surface's journeys unnamed, so it does not describe "
            f"{label} and must not be stamped with its fingerprint. Rebuild the surface and the "
            "destinations from the same graph")
    finite_differs = int((np.isfinite(stored) != np.isfinite(as_stored)).sum())
    both = np.isfinite(stored) & np.isfinite(as_stored)
    differing = int((stored[both] != as_stored[both]).sum())
    if differing or finite_differs:
        worst = (float(np.abs(stored[both].astype(np.float64)
                              - as_stored[both].astype(np.float64)).max())
                 if both.any() else float("nan"))
        raise SystemExit(
            f"the journey times recomputed here disagree with {label} at {differing:,} cells "
            f"(worst {worst:g} s) and their reachability differs at {finite_differs:,}. The "
            "fingerprint would then bind this plane to a surface it does not describe -- pass 50 "
            "finding A2. Rebuild the surface and the destinations from the same graph")
    return {
        "cells_compared": int(both.sum()),
        "cells_differing": differing,
        "reachability_differing": finite_differs,
        "compared_as": str(stored.dtype),
        "why_this_is_here": (
            "the fingerprint binds this plane to a surface, and binding it after comparing only "
            "the journey-PRESENCE mask was not earned: 256,276 cells can have 60 s added while "
            "that mask holds, changing every one of their published minutes. These are the "
            "recomputed per-cell seconds against the stored ones, from the same function the "
            "surface build uses, compared EXACTLY after the cast the surface was written "
            "through -- pass 50 finding A2"),
    }


def place_record(row) -> dict:
    """The minimum that names a destination. Nothing more leaves the parquet."""
    names = row.get("names") or {}
    brand = (row.get("brand") or {}).get("names") or {}
    return {
        "gers_id": row["id"],
        "name": scalar(names.get("primary") or names.get("common")),
        "brand": scalar(brand.get("primary") or brand.get("common")),
        "category": scalar(row.get("basic_category")),
        "operating_status": scalar(row.get("operating_status")),
        "licence": scalar(row.get("licence")),
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
        recomputed = cell_seconds_from_arrival(
            idx, seconds_n, xs.ravel(), ys.ravel(), mode=MODE, max_access_m=MAX_ACCESS_M,
            node_cost=node_cost, cutoff_s=HORIZON_S,
        ).reshape(grid.nrows, grid.ncols)
        seconds_agreement = check_plane_describes_the_surface(
            ordinals, np.load(LAYERS / f"{STEM}.npy"), recomputed, HORIZON_S,
            label=f"{STEM}.npy")
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
                    "for organisation and for clarity about what came from where, NOT as a legal "
                    "determination. Codex pass 49 finding 4 withdrew the earlier claim that "
                    "keeping the table apart was 'what stops permissively licensed names being "
                    "swept into a share-alike database': ODbL distinguishes a collective from a "
                    "derivative database by the substantive relationship between the parts, not "
                    "by how many files they are stored in, and decision 17 itself permits "
                    "OSM-derived and Overture-derived data in the same tables provided the "
                    "notices travel with them. What IS load-bearing is decision 17's actual "
                    "rule, which this table satisfies: no contractually restricted source"),
                "redistribution": (
                    "these licences carry obligations that a label does not discharge. "
                    "CDLA-Permissive-2.0 2.1 requires the TEXT of the agreement to be made "
                    "available with the shared data, and Apache-2.0 4 requires the licence, a "
                    "statement of modification and the source NOTICE. "
                    "scripts/export_published_layers.py copies them into the published bundle "
                    "and refuses to finish without them -- pass 49 finding 3"),
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
            json.dumps(table, indent=2, default=str, allow_nan=False), encoding="utf-8")

        meta = {
            "built": stamp(), "mode": MODE, "category": CATEGORY,
            "cells": int(ordinals.size),
            "named": int((ordinals != wire.DEST_NONE).sum()),
            "distinct_destinations": len(chosen_nodes),
            "dtype": str(np.dtype(wire.DEST_DTYPE)),
            "dest_none": int(wire.DEST_NONE),
            # Pass 48 F3's lesson, applied at the start this time rather than after a review.
            "horizon_s": float(HORIZON_S),
            "seconds_agreement_with_the_surface": seconds_agreement,
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
            json.dumps(meta, indent=2, default=str, allow_nan=False), encoding="utf-8")
        print(f"\nwrote {path.name}: {meta['named']:,} of {meta['cells']:,} cells named, "
              f"{len(chosen_nodes):,} distinct destinations")

    args.out.write_text(json.dumps(report, indent=2, default=str, allow_nan=False), encoding="utf-8")
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
    control = destination_tie_control()
    if control["total_destination_moves"] == 0:
        raise SystemExit(
            "the positive control cannot detect a moved destination on a construction that is "
            "KNOWN to be ambiguous, so this instrument reports nothing and the figure below "
            "would be worthless")
    if control["total_seconds_moves"] != 0:
        raise SystemExit("the control's published seconds moved under a relabelling, which is a "
                         "different and larger bug than the one this measures")
    # **Pass 50 finding G5.** The two conditions above are satisfied by an algorithm that never
    # solves the construction at all. A solver returning zeros everywhere reports one seconds
    # value (0) and, after the relabelling is mapped back, three different "selected" nodes -- so
    # it looks like a working instrument detecting movement. Movement is only evidence if the
    # answer is RIGHT, so the known answer is pinned: 300 s at the target, and the destination is
    # one of the two candidates and takes both of them.
    if control["published_seconds_at_the_target"] != [CONTROL_SECONDS]:
        raise SystemExit(
            f"the control's target should be {CONTROL_SECONDS} s from either destination and the "
            f"solver reports {control['published_seconds_at_the_target']}. It is not solving the "
            "construction, so its movement says nothing about the instrument")
    if control["destinations_selected_across_relabellings"] != CONTROL_DESTINATIONS:
        raise SystemExit(
            f"the control should select each of {CONTROL_DESTINATIONS} and it selected "
            f"{control['destinations_selected_across_relabellings']}; movement between wrong "
            "answers is not a demonstration that the instrument works")
    return {
        "what_this_is": ("whether the destination a household would be SHOWN is a property of the "
                         "published answer or of the traversal order"),
        "labellings": rows,
        "total_destination_moves": total,
        "positive_control": control,
        "labellings_tried": len(rows),
        "what_it_means": (
            "a non-zero here is a NAME decided by heap order, which is worse than a flag decided "
            "that way because the name is shown"
            if total else
            f"under the {len(rows)} relabellings tried, no cell's selected destination moved. "
            "That is EVIDENCE that exact bit-level cost ties between different destinations are "
            "not being hit on this graph; it is not proof that none exist. Three permutations "
            "sample the space, and a tie whose two orderings both happen to be avoided by these "
            "three is invisible here -- pass 49 finding 8. The positive control above shows the "
            "instrument can report a move, which is what makes this zero worth recording at all"),
        "what_it_does_not_establish": (
            "that the destination is well defined in general. Quantising the cost would "
            "manufacture ties, and then the NAME shown would depend on heap order. The earlier "
            "wording said ties 'do not occur on this graph', which three relabellings cannot "
            "establish"),
    }


def destination_tie_control() -> dict:
    """**The control that makes a zero above mean anything**, run rather than pointed at.

    An earlier version of this file cited `measure_tie_flag.py`'s control instead of running one.
    That control exercises `arrival_with_route_flag`; the destination goes through
    `arrival_with_selected_destination`, a different function, so nothing demonstrated that this
    instrument can report a moved destination at all.

    It also needs a different construction. The flag's four-node diamond has ONE destination, so no
    destination can move in it. Here two destinations sit equidistant from one target --
    `D1 - T - D2`, equal costs -- so the selected destination is decided by heap order and must
    move under some relabelling while the published seconds do not.
    """
    import itertools

    import scipy.sparse as sp

    n = 3
    half = CONTROL_SECONDS
    # D1 = 0, D2 = 1, T = 2. Equal cost from T to each destination.
    raw = [(0, 2, half), (2, 0, half), (1, 2, half), (2, 1, half)]
    rows_i = np.array([u for u, _v, _c in raw], dtype=np.int64)
    cols_i = np.array([v for _u, v, _c in raw], dtype=np.int64)
    order = np.lexsort((cols_i, rows_i))
    rows_i, cols_i = rows_i[order], cols_i[order]
    data = np.array([raw[i][2] for i in order], dtype=np.float64)
    indptr = np.zeros(n + 1, dtype=np.int64)
    np.add.at(indptr, rows_i + 1, 1)
    indptr = np.cumsum(indptr)

    def mat():
        m = sp.csr_matrix((n, n), dtype=np.float64)
        m.data, m.indices, m.indptr = data.copy(), cols_i.copy(), indptr.copy()
        return m

    seen = {}
    for perm in itertools.permutations(range(n)):
        q = np.array(perm, dtype=np.int64)
        inv = np.empty(n, dtype=np.int64)
        inv[q] = np.arange(n)
        cost_p, time_p = (mat()[q, :][:, q].tocsr(), mat()[q, :][:, q].tocsr())
        s, sel = arrival_with_selected_destination(
            cost_p, time_p, dest_idx=sorted((int(inv[0]), int(inv[1]))))
        # Back to the original numbering before reading the target's answer.
        s_back = np.empty(n, dtype=float)
        sel_back = np.empty(n, dtype=np.int64)
        s_back[q] = s
        sel_back[q] = np.where(sel >= 0, q[np.where(sel >= 0, sel, 0)], -1)
        key = (round(float(s_back[2]), 9), int(sel_back[2]))
        seen.setdefault(key, []).append(perm)

    secs = sorted({t for t, _d in seen})
    dests = sorted({d for _t, d in seen})
    return {
        "what_this_is": ("a three-node construction whose selected destination IS ambiguous, so "
                         "the instrument's ability to report a moved destination is demonstrated "
                         "rather than assumed"),
        "published_seconds_at_the_target": secs,
        "destinations_selected_across_relabellings": dests,
        "total_destination_moves": max(len(dests) - 1, 0),
        "total_seconds_moves": max(len(secs) - 1, 0),
        "why_the_flags_control_does_not_cover_this": (
            "measure_tie_flag.py's diamond has ONE destination, so no destination can move in it, "
            "and it drives arrival_with_route_flag rather than "
            "arrival_with_selected_destination"),
    }


if __name__ == "__main__":
    raise SystemExit(main())
