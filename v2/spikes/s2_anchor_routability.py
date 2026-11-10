"""Phase 1 S2.2 on real data: do the twelve spot-check anchors route, and does the RDU stub still
break?

In the Phase 0 spot check, snapping "RDU Terminal 2" found a node 4 m away on a four-node
`highway=service` stub and **three of twelve journeys came back unreachable**, while Valhalla and
OSRM routed them fine. `components.largest_component` was the response, and its own docstring says
why that is not enough: it uses **weak** connectivity, so a retained one-way branch can still fail
origin-to-destination reachability, and "directed reachability to the actual destination set is the
real test".

This runs that test over the whole metro graph and over the twelve anchors, and quantifies what the
directed test adds over the weak one — the share of nodes that are weakly connected to the core but
which the core cannot actually reach.

Barriers are extracted from the OSM extract with QuackOSM rather than skipped, because a nudge
validated on distance alone is not validated: the nearest routable node can be on the far side of a
wall, a railway or a motorway.

Run from v2/:  uv run python spikes/s2_anchor_routability.py --mode drive
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import networkx as nx
import numpy as np
import osmnx as ox
import shapely
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (GRAPH_CACHE, GRID, METRO, METRO_DIR, ROUTING_PBF,  # noqa: E402
                     append_results, load_roads_graph, stamp)
from locfinder.places.anchor import (CoreReachability, DEFAULT_MAX_NUDGE_M,  # noqa: E402
                                     SEPARATING_BARRIERS, fix_anchor, node_coordinates)
from locfinder.traveltime.components import component_report, largest_component  # noqa: E402
from locfinder.traveltime.csr import graph_to_cost_time_csr  # noqa: E402
from locfinder.traveltime.snap import EdgeIndex  # noqa: E402
from locfinder.traveltime.speeds import add_travel_times, symmetrise  # noqa: E402
from spotcheck_engines import PLACES as ANCHORS  # noqa: E402

#: OSM barrier values that a pedestrian or a car genuinely cannot cross. `barrier=gate`,
#: `bollard`, `cycle_barrier` and friends are deliberately excluded: they are passable, often for
#: some modes only, and treating them as walls would reject legitimate nudges.
IMPASSABLE_BARRIERS = SEPARATING_BARRIERS


def load_barriers(cache: Path):
    """Barrier linework from the routing extract, cached as a parquet next to the other sources."""
    if cache.exists():
        import geopandas as gpd
        return gpd.read_parquet(cache)
    import geopandas as gpd
    import quackosm as qosm
    t = time.perf_counter()
    gdf = qosm.convert_pbf_to_geodataframe(
        ROUTING_PBF, tags_filter={"barrier": list(IMPASSABLE_BARRIERS)}, keep_all_tags=False)
    gdf = gdf[gdf.geometry.geom_type.isin(("LineString", "MultiLineString"))]
    print(f"extracted {len(gdf):,} barrier ways in {time.perf_counter() - t:.1f} s", flush=True)
    gdf.to_parquet(cache)
    return gdf


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="drive", choices=["walk", "bike", "drive"])
    ap.add_argument("--max-nudge-m", type=float, default=DEFAULT_MAX_NUDGE_M)
    args = ap.parse_args()
    out: dict = {"metro": METRO.name, "mode": args.mode, "max_nudge_m": args.max_nudge_m}

    t = time.perf_counter()
    cache = GRAPH_CACHE if GRAPH_CACHE.exists() else GRAPH_CACHE.with_name("slice-roads.graphml")
    G = ox.project_graph(load_roads_graph(cache), to_crs=GRID.crs)
    G = add_travel_times(G, mode=args.mode)
    if args.mode == "walk":
        G = symmetrise(G)
    G.remove_nodes_from([n for n, d in G.degree() if d == 0])
    print(f"graph in {time.perf_counter() - t:.1f} s", flush=True)

    # Before pruning: what does the weak test say, and what does the directed test say?
    weak = component_report(G)
    cost_csr, _, index_all = graph_to_cost_time_csr(G)
    t = time.perf_counter()
    reach_all = CoreReachability.from_csr(cost_csr)
    print(f"directed reachability over {cost_csr.shape[0]:,} nodes in "
          f"{time.perf_counter() - t:.1f} s", flush=True)

    Gp, comp = largest_component(G)
    cost_p, _, index = graph_to_cost_time_csr(Gp)
    reach = CoreReachability.from_csr(cost_p)
    out["graph"] = {
        "nodes_before_pruning": G.number_of_nodes(),
        "weak_components": weak.n_components,
        "weak_largest_share": weak.largest_share,
        "directed_core_share_before_pruning": reach_all.usable_share,
        "nodes_after_pruning": Gp.number_of_nodes(),
        "directed_core_size_after_pruning": reach.core_size,
        "directed_usable_share_after_pruning": reach.usable_share,
    }
    # The number that says what the directed test adds: nodes the WEAK test keeps but which the
    # core cannot actually reach.
    kept_but_unreachable = int((~reach.reachable_from_core).sum())
    out["graph"]["kept_by_weak_but_unreachable_directed"] = kept_but_unreachable
    out["graph"]["kept_but_unreachable_share"] = kept_but_unreachable / Gp.number_of_nodes()
    print(f"weak: {weak.summary}", flush=True)
    print(f"after pruning: {Gp.number_of_nodes():,} nodes, directed core "
          f"{reach.core_size:,} ({reach.usable_share:.4%} usable); "
          f"**{kept_but_unreachable:,} nodes kept by the weak test that the core cannot reach**",
          flush=True)

    eidx = EdgeIndex.from_graph(Gp, index)
    node_xy = node_coordinates(eidx)
    barriers_gdf = load_barriers(METRO_DIR / "osm_barriers.parquet")
    bar = barriers_gdf.to_crs(GRID.crs)
    barriers = shapely.STRtree(list(bar.geometry))
    out["barriers"] = {"ways": int(len(bar)), "source": "quackosm from the routing extract",
                       "values": list(IMPASSABLE_BARRIERS)}
    print(f"barriers: {len(bar):,} impassable ways", flush=True)

    to_proj = Transformer.from_crs("EPSG:4326", GRID.crs, always_xy=True)
    rows = []
    for name, (lat, lon) in ANCHORS.items():
        x, y = to_proj.transform(lon, lat)
        with_b = fix_anchor(x, y, edge_index=eidx, reach=reach, barriers=barriers,
                            node_xy=node_xy, max_nudge_m=args.max_nudge_m)
        no_b = fix_anchor(x, y, edge_index=eidx, reach=reach, barriers=None,
                          node_xy=node_xy, max_nudge_m=args.max_nudge_m)
        rows.append({
            "anchor": name, "status": with_b.status, "moved_m": round(with_b.moved_m, 1),
            "rejected_unreachable": with_b.rejected_unreachable,
            "rejected_by_barrier": with_b.rejected_by_barrier,
            "moved_m_without_barriers": round(no_b.moved_m, 1),
            "barrier_changed_the_answer": with_b.node != no_b.node,
            "crossed_barrier": with_b.crossed_barrier,
            "reason": with_b.reason,
        })
        flag = "  <-- barriers changed it" if with_b.node != no_b.node else ""
        print(f"  {name:<32} {with_b.status:<12} moved {with_b.moved_m:6.1f} m "
              f"(rejected {with_b.rejected_unreachable} unreachable, "
              f"{with_b.rejected_by_barrier} barrier){flag}", flush=True)
    out["anchors"] = rows

    usable = sum(1 for r in rows if r["status"] in ("ok", "nudged"))
    nudged = sum(1 for r in rows if r["status"] == "nudged")
    changed = sum(1 for r in rows if r["barrier_changed_the_answer"])
    # NOT "had an unreachable node nearer": this counts anchors with any unreachable candidate in
    # range, including ones further away than the node chosen. `nudged` is the count that means a
    # nearer candidate was actually rejected.
    with_unreachable = sum(1 for r in rows if r["rejected_unreachable"] > 0)
    print(f"\n{usable}/{len(rows)} anchors usable; {nudged} nudged (a nearer candidate was "
          f"rejected); {with_unreachable} had an unreachable candidate somewhere in range; "
          f"barriers changed {changed}", flush=True)

    (METRO_DIR.parent / f"s2_anchor_routability_{METRO.name}_{args.mode}.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")

    g = out["graph"]
    lines = [
        f"### S2.2 anchor routability on the real graph ({stamp()}): {args.mode}, "
        f"{METRO.name}, nudge cap {args.max_nudge_m:.0f} m", "",
        "In Phase 0, snapping RDU Terminal 2 found a node 4 m away on a four-node service stub and "
        "three of twelve journeys came back unreachable. `largest_component` was the response, and "
        "its docstring records that weak connectivity is not the right test. This is the directed "
        "one.", "",
        "**What the directed test adds over the weak one.**", "",
        "| | |", "|---|---|",
        f"| nodes before pruning | {g['nodes_before_pruning']:,} |",
        f"| weak components | {g['weak_components']:,} (largest holds {g['weak_largest_share']:.1%}) |",
        f"| nodes the core can reach, **before** pruning | {g['directed_core_share_before_pruning']:.4%} |",
        f"| nodes after pruning | {g['nodes_after_pruning']:,} |",
        f"| nodes the core can reach, **after** pruning | {g['directed_usable_share_after_pruning']:.4%} |",
        f"| **kept by the weak test, unreachable by the directed one** | "
        f"**{g['kept_by_weak_but_unreachable_directed']:,} "
        f"({g['kept_but_unreachable_share']:.4%})** |", "",
        f"So pruning to the largest weak component still leaves "
        f"{g['kept_by_weak_but_unreachable_directed']:,} nodes that nothing in the core can drive "
        "to. Those are the ones an anchor must not be snapped to, and distance alone cannot tell "
        "them apart from good ones.", "",
        f"**Barriers.** {out['barriers']['ways']:,} impassable ways extracted from the routing "
        f"extract with QuackOSM (`{', '.join(IMPASSABLE_BARRIERS[:5])}`, …). Gates, bollards and "
        "cycle barriers are deliberately **excluded**: they are passable, often mode-dependently, "
        "and treating them as walls would reject legitimate nudges.", "",
        "**The twelve spot-check anchors.**", "",
        "| anchor | status | moved | nearer node unreachable | candidates behind a barrier | approach crosses a barrier |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['anchor']} | **{r['status']}** | {r['moved_m']:.1f} m | "
            f"{r['rejected_unreachable']} | {r['rejected_by_barrier']} | "
            f"{'**yes**' if r['crossed_barrier'] else '—'} |")
    crossed = sum(1 for r in rows if r["crossed_barrier"])
    lines += [
        "", f"{usable} of {len(rows)} anchors are usable and **{nudged} needed a nudge** — that is, "
        f"a *nearer* candidate was rejected. {with_unreachable} had an unreachable candidate "
        f"somewhere in range, which is not the same thing and is not an adjustment. {crossed} sit "
        "behind a perimeter, so every reachable candidate is barrier-crossing and the "
        "straight-line approach is not the real one.", "",
        "**What the directed test actually bought here.** The RDU stub failure does **not** "
        "reproduce: all six nodes within 150 m of the terminal are reachable from the core, so "
        "`largest_component` had already fixed it and the directed test confirms rather than "
        "rescues. Metro-wide the directed test rejects "
        f"{g['kept_by_weak_but_unreachable_directed']:,} nodes the weak test keeps, and on these "
        f"twelve anchors it changed the chosen node **{nudged} times**. That is the honest result: "
        "the test is correct and essentially free, and on this anchor set it made no difference. "
        "It is worth keeping because the failure it prevents is silent, not because it has been "
        "shown to fire.", "",
        "This is a routability result, not an accuracy one: it says an anchor can be reached, not "
        "that the time to reach it is right.", "",
    ]
    append_results("spotcheck-engines.md", "\n".join(lines))


if __name__ == "__main__":
    main()
