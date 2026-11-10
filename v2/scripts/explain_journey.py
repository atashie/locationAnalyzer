"""Print the whole journey behind one audited number: what it snapped to, and the route it took.

Built because the owner walked a sheet row and found it much slower than predicted. When a walked
result disagrees with the model, "which number is wrong" is not the useful question -- the useful
question is *which street did we think you would use*. This prints that, street by street, with
lengths and times, plus every edge near the query point that we could have snapped to instead.

    cd v2
    python scripts/explain_journey.py ../docs/experiments/audit/triangle-grocery-walk-chapelhill.csv \
        band15min_pass-03

Reports, for the named journey:

* every graph edge within `--near-m` of the cell centre, with its OSM name and distance, so a
  wrong snap is visible rather than inferred;
* which edge was actually matched, the access leg, and which endpoint supplied the answer;
* the full route to the selected destination, each segment named, with metres and seconds;
* the total route length and the implied average speed, which is the check that catches a route
  passing through geometry a pedestrian cannot use.

Read-only. One graph load, about 1.5 minutes.
"""
import argparse
import csv
import math
import pathlib
import sys
import time
from collections import Counter

import geopandas as gpd
import numpy as np
import osmnx as ox
import shapely
from scipy.sparse.csgraph import dijkstra

V2 = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V2))
sys.path.insert(1, str(V2 / "spikes"))
from _common import ACCEPTED_PLACES, GRID, load_roads_graph  # noqa: E402

from locfinder.places.categories import select_overture  # noqa: E402
from locfinder.traveltime.arrival import arrival_seconds  # noqa: E402
from locfinder.traveltime.components import largest_component  # noqa: E402
from locfinder.traveltime.csr import graph_to_cost_time_csr  # noqa: E402
from locfinder.traveltime.snap import EdgeIndex, _snap_network  # noqa: E402
from locfinder.traveltime.speeds import access_speed_mps, add_travel_times, symmetrise  # noqa: E402

POI_SNAP_MAX_M = 300.0
MAX_ACCESS_M = 200.0
HORIZON_S = 120.0 * 60.0
MODE = "walk"
CATEGORY = "grocery"
NO_PREDECESSOR = -9999


def sel_cost(data) -> float:
    """What path selection minimises, for one parallel edge.

    `csr.graph_to_cost_time_csr` keeps the **cost**-minimal parallel edge and carries that edge's
    own time, so a report that picks the *fastest* parallel edge can describe an edge the route
    did not use. This tool picked by `travel_time` in every parallel-edge report for two
    revisions. `cost` falls back to `travel_time` exactly as the CSR builder does, so an
    unpenalised graph is unaffected.
    """
    t = float(data.get("travel_time", math.inf))
    return float(data.get("cost", t))


def classes_of(data) -> set:
    hw = data.get("highway")
    if isinstance(hw, (list, tuple)):
        return {str(x) for x in hw}
    return {str(hw)} if hw else set()


def edge_name(data) -> str:
    n = data.get("name")
    if isinstance(n, (list, tuple)):
        n = ", ".join(str(x) for x in n)
    hw = data.get("highway")
    if isinstance(hw, (list, tuple)):
        hw = "/".join(str(x) for x in hw)
    return f"{n or '(unnamed)'} [{hw or '?'}]"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet", type=pathlib.Path)
    ap.add_argument("journey")
    ap.add_argument("--near-m", type=float, default=120.0,
                    help="list every edge within this distance of the cell centre")
    ap.add_argument("--drop", default="",
                    help="comma-separated OSM highway classes to remove first, e.g. track,path. "
                         "Use this to inspect the counterfactual route, not just assert its time.")
    args = ap.parse_args()
    drop = {c.strip() for c in args.drop.split(",") if c.strip()}

    rows = {r["journey_id"]: r for r in csv.DictReader(args.sheet.open(encoding="utf-8-sig"))}
    if args.journey not in rows:
        print(f"no journey {args.journey!r}; have {sorted(rows)[:5]}...")
        return 1
    row = rows[args.journey]
    rr, cc = int(row["row"]), int(row["col"])
    print(f"=== {args.journey} ===")
    print(f"cell ({rr}, {cc})  published {row['seconds']} s "
          f"= {float(row['seconds']) / 60:.1f} min  reason {row['reason']}")
    print(f"10 min: {row['outcome_10min']}   15 min: {row['outcome_15min']}")

    t = time.perf_counter()
    G = load_roads_graph()
    G = ox.project_graph(G, to_crs=GRID.crs)
    if drop:
        doomed = [(u, v, k) for u, v, k, d in G.edges(keys=True, data=True)
                  if classes_of(d) & drop]
        G.remove_edges_from(doomed)
        print(f"removed {len(doomed):,} edges of class {sorted(drop)}")
    G = add_travel_times(G, mode=MODE)
    if MODE == "walk":
        G = symmetrise(G)
    G.remove_nodes_from([n for n, d in G.degree() if d == 0])
    G, _comp = largest_component(G)
    print(f"\ngraph prepared in {time.perf_counter() - t:.1f}s", flush=True)

    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
    rev = {v: k for k, v in index.items()}
    places = gpd.read_parquet(ACCEPTED_PLACES).to_crs(GRID.crs)
    sel = select_overture(places, CATEGORY)
    cent = sel.geometry.centroid
    pnodes, pdists = ox.nearest_nodes(G, cent.x.to_numpy(), cent.y.to_numpy(), return_dist=True)
    keep = np.asarray(pdists) <= POI_SNAP_MAX_M
    node_to_places: dict[int, list[int]] = {}
    for pos, (n, k) in enumerate(zip(pnodes, keep)):
        if k:
            node_to_places.setdefault(index[n], []).append(pos)
    dest_idx = sorted(node_to_places)

    centre_x, centre_y = GRID.cell_centers_xy()
    qx, qy = float(centre_x[rr, cc]), float(centre_y[rr, cc])

    # ---- what is near the query point -------------------------------------------------------
    print(f"\n--- every edge within {args.near_m:.0f} m of the cell centre ---")
    eidx = EdgeIndex.from_graph(G, index)
    pt = shapely.points([qx], [qy])[0]
    near = eidx.tree.query(pt.buffer(args.near_m))
    cand = []
    for gi in np.atleast_1d(near):
        geom = eidx.geoms[gi]
        d = shapely.distance(pt, geom)
        s_osm, e_osm = rev[eidx.start_idx[gi]], rev[eidx.end_idx[gi]]
        data = min(G.get_edge_data(s_osm, e_osm, default={0: {}}).values(),
                   key=sel_cost) or {}
        if not data:
            data = min(G.get_edge_data(e_osm, s_osm, default={0: {}}).values(),
                       key=sel_cost) or {}
        cand.append((d, gi, edge_name(data)))
    cand.sort()
    # Print the count before the list, and say when the list is cut. The first version printed the
    # nearest 14 with no total, and I then wrote "every one of the 14 edges within 120 m is a
    # track, path, footway or service way" into an engineering note -- there were 17, and 14 was my
    # own slice presented as the population (Codex pass 34).
    print(f"  {len(cand)} edges qualify; showing the nearest {min(len(cand), 14)}")
    for d, gi, name in cand[:14]:
        print(f"  {d:7.1f} m  geom#{gi:<7} {name}")
    if len(cand) > 14:
        print(f"  ... {len(cand) - 14} more, farther than {cand[13][0]:.1f} m")
    if not cand:
        print("  (none)")

    # ---- what it actually snapped to ---------------------------------------------------------
    T = np.asarray(dijkstra(cost_csr.transpose().tocsr(), directed=True, indices=dest_idx,
                            min_only=True))
    dist, pred, sources = dijkstra(cost_csr.transpose().tocsr(), directed=True,
                                  indices=np.asarray(dest_idx, dtype=np.int64),
                                  min_only=True, return_predecessors=True)
    # arrival times in real seconds along the cost-optimal path, same sweep as arrival.py
    time_t = time_csr.transpose().tocsr()
    dist = np.asarray(dist, dtype=np.float64)
    pred = np.asarray(pred, dtype=np.int64)
    Treal = np.full(cost_csr.shape[0], np.inf)
    order = np.flatnonzero(np.isfinite(dist))
    order = order[np.argsort(dist[order], kind="stable")]
    for node in order:
        p = pred[node]
        if p == NO_PREDECESSOR:
            Treal[node] = 0.0
        else:
            prev = Treal[p]
            Treal[node] = prev + time_t[p, node] if np.isfinite(prev) else np.inf

    node_cost = np.asarray(arrival_seconds(cost_csr, dest_idx=dest_idx))
    snapped = _snap_network(eidx, Treal, np.array([qx]), np.array([qy]), node_cost=node_cost)
    gi = int(np.atleast_1d(eidx.tree.nearest(shapely.points([qx], [qy])))[0])
    chosen = int(snapped.chosen_idx[0])
    access_m = float(snapped.access_m[0])
    s_osm, e_osm = rev[eidx.start_idx[gi]], rev[eidx.end_idx[gi]]
    matched = min(G.get_edge_data(s_osm, e_osm, default={0: {}}).values(),
                  key=sel_cost) or \
        min(G.get_edge_data(e_osm, s_osm, default={0: {}}).values(),
            key=sel_cost)
    frac = float(shapely.line_locate_point(eidx.geoms[gi], pt, normalized=True))

    print(f"\n--- what we snapped to ---")
    # The matched edge's own OSM way id. Without it I read the way id off the first ROUTE segment
    # and reported way 1254722642 as "what it snapped to"; the snapped way is 430448289 and
    # 1254722642 is the next full segment along (Codex pass 34).
    matched_osmid = matched.get("osmid")
    print(f"  matched edge      {edge_name(matched)}  way {matched_osmid}")
    print(f"  access leg        {access_m:.1f} m straight line, "
          f"{access_m / access_speed_mps(MODE):.1f} s at {access_speed_mps(MODE):.2f} m/s"
          f"   (cap {MAX_ACCESS_M:.0f} m)")
    matched_len = float(eidx.geoms[gi].length)
    # Which END of the matched edge, and therefore how much of it is walked. This matters more
    # than it looks: on the no-track counterfactual the matched edge is a 531 m footway and the
    # cell sits near its far end, so 476 m of the journey is on the matched edge alone and the
    # "partial first edge" accounts for 340 s. Without this line that figure reads as a defect.
    on_edge_m = matched_len * (frac if chosen == eidx.start_idx[gi] else (1.0 - frac))
    print(f"  position on edge  fraction {frac:.4f} of a {matched_len:,.0f} m geometry")
    print(f"  walked on it      {on_edge_m:,.0f} m to reach the chosen endpoint")
    print(f"  endpoint used     {'end' if chosen == eidx.end_idx[gi] else 'start'} "
          f"= OSM node {rev.get(chosen, chosen)}")
    print(f"  on-network part   {float(snapped.network[0]):.1f} s")

    # ---- the route, segment by segment -------------------------------------------------------
    if chosen < 0 or not np.isfinite(Treal[chosen]):
        print("\n  no route from that endpoint")
        return 0
    print(f"\n--- the route we expect you to walk ---")
    total_m = 0.0
    total_s = 0.0
    hops = 0
    node = chosen
    names = Counter()
    while True:
        p = int(pred[node])
        if p == NO_PREDECESSOR:
            break
        u, v = rev[node], rev[p]
        best = None
        for data in (G.get_edge_data(u, v) or {}).values():
            if best is None or sel_cost(data) < sel_cost(best):
                best = data
        if best is None:
            for data in (G.get_edge_data(v, u) or {}).values():
                if best is None or sel_cost(data) < sel_cost(best):
                    best = data
        length = float(best.get("length", 0.0)) if best else 0.0
        secs = float(best.get("travel_time", 0.0)) if best else 0.0
        total_m += length
        total_s += secs
        hops += 1
        names[edge_name(best or {})] += 1
        if hops <= 40:
            print(f"  {hops:>3}. {length:7.1f} m  {secs:6.1f} s  {edge_name(best or {})}")
        node = p
    if hops > 40:
        print(f"  ... {hops - 40} more segments")

    dest_node = int(sources[chosen])
    shop = "(unknown)"
    if dest_node in node_to_places:
        nm = sel["names"].iloc[node_to_places[dest_node][0]]
        shop = nm.get("primary") if isinstance(nm, dict) else str(nm)
    print(f"\n  destination       {shop}  (node {rev.get(dest_node, dest_node)})")
    # The authoritative number is `snapped.network`, measured from the matched POINT. The segment
    # sum starts at the chosen ENDPOINT, so it omits the partial first edge. Printing both and
    # their difference makes a disagreement visible instead of leaving two plausible totals -- the
    # first version printed only the sum, and when a defect made it 340 s low it read as two tools
    # contradicting each other rather than as one of them being wrong.
    network_s = float(snapped.network[0])
    access_s = access_m / access_speed_mps(MODE)
    print(f"  segments          {hops}")
    print(f"  segment sum       {total_m:,.0f} m = {total_m / 1609.344:.2f} miles, "
          f"{total_s:,.1f} s")
    print(f"  on-network        {network_s:,.1f} s  (from the matched point, authoritative)")
    print(f"    difference      {network_s - total_s:+.1f} s = the partial first edge")
    print(f"  + access leg      {access_s:.1f} s over {access_m:.1f} m")
    print(f"  PUBLISHED TOTAL   {network_s + access_s:,.1f} s = "
          f"{(network_s + access_s) / 60:.1f} min")
    if total_s > 0:
        print(f"  implied speed     {total_m / total_s:.2f} m/s on the network")
    print(f"\n  streets used, most segments first:")
    for name, n in names.most_common(12):
        print(f"    {n:>3}x  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
