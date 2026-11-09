"""Gate G1 candidate: seconds-to-nearest-<category> from our own directed graph
(osmnx graph from the clipped roads XML, per-mode access rules, transposed-graph
multi-source Dijkstra, arrival-aware nearest-edge snapping), with stage timings.

Outputs (v2/data/layers/): own_<cat>_<mode>.tif (uint8 minutes), .npy (float32 seconds),
own_<mode>_oneway_mask.npy (True where a cell's nearest edge is one-way, for the audit),
and a results section appended to docs/experiments/g1-routing.md.

Run from v2/:  uv run python spikes/g1_own_graph_layer.py grocery walk
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
import rasterio
import shapely

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (ACCEPTED_PLACES, GRAPH_CACHE, GRID, LAYERS, METRO, ROADS_XML, append_results,  # noqa: E402
                     layer_path, stamp)
from locfinder.grid import encode_minutes  # noqa: E402
from locfinder.places.categories import select_overture  # noqa: E402
from locfinder.traveltime.components import largest_component  # noqa: E402
from locfinder.traveltime.csr import graph_to_cost_time_csr  # noqa: E402
from locfinder.traveltime.layer import build_layer_seconds  # noqa: E402
from locfinder.traveltime.snap import EdgeIndex  # noqa: E402
from locfinder.traveltime.speeds import EXTRA_WAY_TAGS, add_travel_times, symmetrise  # noqa: E402

POI_SNAP_MAX_M = 300.0  # drop POIs farther than this from any node (Codex pass 3: bound the access leg)


def load_graph(timings: dict):
    t = time.perf_counter()
    if GRAPH_CACHE.exists():
        G = ox.load_graphml(GRAPH_CACHE)
        timings["load_graph_s"] = time.perf_counter() - t
        timings["graph_source"] = "graphml cache"
        return G
    ox.settings.useful_tags_way = sorted(set(ox.settings.useful_tags_way) | set(EXTRA_WAY_TAGS))
    G = ox.graph_from_xml(ROADS_XML, simplify=True, retain_all=True)
    timings["load_graph_s"] = time.perf_counter() - t
    timings["graph_source"] = f"{ROADS_XML.name} (xml)"
    t = time.perf_counter()
    ox.save_graphml(G, GRAPH_CACHE)
    timings["save_graphml_s"] = time.perf_counter() - t
    return G


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("category")
    ap.add_argument("mode", choices=["walk", "bike", "drive"])
    args = ap.parse_args()
    timings: dict = {}

    G = load_graph(timings)
    n0, e0 = G.number_of_nodes(), G.number_of_edges()
    t = time.perf_counter()
    G = ox.project_graph(G, to_crs=GRID.crs)
    G = add_travel_times(G, mode=args.mode)
    if args.mode == "walk":
        G = symmetrise(G)
    G.remove_nodes_from([n for n, d in G.degree() if d == 0])
    G, comp = largest_component(G)   # geometric snapping can land on a marooned stub
    timings["components"] = comp.summary
    timings["prepare_graph_s"] = time.perf_counter() - t
    t = time.perf_counter()
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
    timings["csr_s"] = time.perf_counter() - t
    n_restricted = sum(1 for _, _, d in G.edges(data=True) if d.get("access_restricted"))
    timings["restricted_edges"] = n_restricted
    print(f"graph: {n0} nodes/{e0} edges raw -> {G.number_of_nodes()} nodes/{G.number_of_edges()} edges for {args.mode}")

    t = time.perf_counter()
    places = gpd.read_parquet(ACCEPTED_PLACES).to_crs(GRID.crs)
    sel = select_overture(places, args.category)
    cent = sel.geometry.centroid
    nodes, dists = ox.nearest_nodes(G, cent.x.to_numpy(), cent.y.to_numpy(), return_dist=True)
    keep = np.asarray(dists) <= POI_SNAP_MAX_M
    dest_idx = sorted({index[n] for n, k in zip(nodes, keep) if k})
    timings["snap_pois_s"] = time.perf_counter() - t
    print(f"{args.category}: {len(sel)} places, {int(keep.sum())} within {POI_SNAP_MAX_M:.0f} m of a node -> {len(dest_idx)} destination nodes")

    t = time.perf_counter()
    eidx = EdgeIndex.from_graph(G, index)
    timings["edge_index_s"] = time.perf_counter() - t
    secs = build_layer_seconds(G, (cost_csr, time_csr), index, GRID, dest_idx=dest_idx, mode=args.mode, timings=timings, edge_index=eidx)

    # one-way audit mask: cells whose nearest physical edge is one-way for this mode
    xs, ys = GRID.cell_centers_xy()
    nearest = eidx.tree.nearest(shapely.points(xs.ravel(), ys.ravel()))
    oneway = (np.isfinite(eidx.fwd_time[nearest]) ^ np.isfinite(eidx.rev_time[nearest])).reshape(xs.shape)
    np.save(layer_path("own", "oneway-mask", args.mode, ".npy"), oneway)

    base = layer_path("own", args.category, args.mode, "")
    np.save(base.with_suffix(".npy"), secs.astype(np.float32))
    # Through `write_layer`, not `rasterio.open` directly: this bypassed the writer and so wrote
    # an **unstamped** raster, which made "an artifact with no encoding tag is the old rint rule"
    # false for anything this script produced after the encoding changed (pass 28).
    #
    # And encoded from the array just written, not from the in-memory float64: the .npy is float32,
    # so 600.00001 s is stored as 600.0 and the two encodings disagree at a threshold. Making the
    # raster a function of the stored seconds is what lets it be re-encoded later.
    arr = encode_minutes(np.load(base.with_suffix(".npy")).astype(np.float64))
    write_layer(base.with_suffix(".tif"), arr, GRID, tags=dict(
        engine="own-csgraph-transposed", category=args.category, mode=args.mode,
        direction="arrival",
        profile="locfinder.speeds v0 (no intersection penalties, no turn restrictions)",
        built_at=stamp(),
        **{k: (f"{v:.2f}" if isinstance(v, float) else str(v)) for k, v in timings.items()}))
    total = sum(v for v in timings.values() if isinstance(v, float))
    text = (f"### Own-graph layer: {args.category} / {args.mode} ({stamp()})\n"
            f"- graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges ({timings['graph_source']}; {comp.summary}); "
            f"destinations {len(dest_idx)} nodes from {len(sel)} places ({int((~keep).sum())} dropped > {POI_SNAP_MAX_M:.0f} m)\n"
            f"- reachable cells {np.isfinite(secs).mean():.1%}; one-way-adjacent cells {oneway.mean():.1%}\n"
            f"- timings (s): " + json.dumps({k: round(v, 2) for k, v in timings.items() if isinstance(v, float)}) + f"; total {total:.1f}\n"
            "- profile: static speeds, access tags honoured, no intersection penalties, no turn restrictions\n")
    print(text)
    append_results("g1-routing.md", text)


if __name__ == "__main__":
    main()
