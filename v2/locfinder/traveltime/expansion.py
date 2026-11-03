"""Turn a Valhalla `/expansion` search tree into the (EdgeIndex, node-times) form that
`snap.cell_seconds_from_arrival` already consumes.

`/expansion` with `action=isochrone` returns one LineString per settled edge. With
`expansion_properties=["duration", "distance", "edge_id", "pred_edge_id"]` each feature carries:

* `duration` — **cumulative** seconds at the far end of this edge (the end the search settled),
* `distance` — cumulative metres at that same point,
* `edge_id` / `pred_edge_id` — the search tree, so the predecessor's cumulative duration is the
  time at this edge's **near** end.

That makes the reconstruction exact: an edge's two endpoint times are `pred.duration` (near) and
`duration` (far), its own traversal time is the difference, and the endpoint shared with the
predecessor's geometry identifies which is which. No speed estimate is involved, so the result
inherits Valhalla's costing exactly, and `cell_seconds_from_arrival` can then interpolate within
the matched edge instead of charging a whole edge traversal (the +66 s conservative bias measured
in docs/experiments/g1-routing.md).

Root edges, whose `pred_edge_id` does not resolve to another feature, are the search origin: their
near end is the destination itself, at time 0. They are a handful of edges out of thousands.
"""
from __future__ import annotations

import numpy as np
import shapely
from pyproj import Transformer
from shapely.geometry import LineString

from .snap import EdgeIndex

# metres: endpoints within this distance are treated as the same node
_NODE_SNAP_M = 0.5
_MIN_EPSILON_S = 0.1
# Valhalla's sentinel for "no predecessor" (kInvalidGraphId). A feature carrying this really is a
# search root. A feature naming a predecessor we do NOT have is a different thing entirely -- its
# near-end time is unknown -- and conflating the two invents a zero-time node (Codex pass-7 C5).
_NO_PRED_SENTINELS = frozenset({None, 70368744177663, -1})


def _node_key(x: float, y: float) -> tuple[int, int]:
    return (int(round(x / _NODE_SNAP_M)), int(round(y / _NODE_SNAP_M)))


def _orient_root(edge: dict, successors, origin_pts) -> bool | None:
    """Is a root edge's near end its first coordinate? Derived, never assumed.

    Two independent signals, strongest first:
    1. the supplied search origins — the near end of a root is the origin itself, so the endpoint
       closer to the nearest origin is the near end;
    2. the root's successors — the search left the root through its FAR end, so the vertex shared
       with a successor is the far end.

    Returns None when neither signal is available, because a guess here lands on the destination
    itself, where the time must be 0 and an error is maximally visible.
    """
    if origin_pts is not None and len(origin_pts):
        first = shapely.points(*edge["geom"].coords[0])
        last = shapely.points(*edge["geom"].coords[-1])
        d_first = float(shapely.distance(first, origin_pts).min())
        d_last = float(shapely.distance(last, origin_pts).min())
        if abs(d_first - d_last) > _NODE_SNAP_M:
            return d_first < d_last
    shared = set()
    for s in successors:
        shared |= {s["ll_first"], s["ll_last"]}
    if shared:
        first_shared = edge["ll_first"] in shared
        last_shared = edge["ll_last"] in shared
        if first_shared != last_shared:
            return last_shared          # the SHARED end is the far end
    return None


def expansion_to_edge_index(
    features: list[dict],
    *,
    target_crs: str,
    source_crs: str = "EPSG:4326",
    origins: list[tuple[float, float]] | None = None,
    strict: bool = True,
    report: dict | None = None,
) -> tuple[EdgeIndex, np.ndarray]:
    """Build (EdgeIndex, T) from `/expansion` features. `T` holds the arrival time in seconds
    at each node index the EdgeIndex refers to; unreachable nodes are +inf.

    Edges are marked traversable in both directions with their own traversal time, because the
    expansion tree already encodes legality: an edge appears only because the router used it.

    `origins` are the (lon, lat) search origins — the destinations we are routing *to* under
    arrival semantics. Supply them: they are the authoritative signal for which end of a root edge
    is at time 0, and without them the orientation must be inferred from successors (Codex pass-7
    C5, where an unoriented root put 0 s at a node 39 m from the destination and the destination's
    own time at a full edge traversal).

    `strict` (default) raises when the tree is not self-consistent — an edge naming an absent
    predecessor, or a root that cannot be oriented — rather than silently inventing a time. Pass
    `strict=False` with `report={}` to drop those edges and read how many there were.
    """
    to_proj = Transformer.from_crs(source_crs, target_crs, always_xy=True)

    # pass 1: keep usable features, project geometry, remember raw lon/lat for adjacency
    kept: list[dict] = []
    for f in features:
        coords = (f.get("geometry") or {}).get("coordinates") or []
        props = f.get("properties") or {}
        if len(coords) < 2 or props.get("duration") is None:
            continue
        xs, ys = to_proj.transform([c[0] for c in coords], [c[1] for c in coords])
        if not (np.all(np.isfinite(xs)) and np.all(np.isfinite(ys))):
            continue  # outside the target projection's domain
        kept.append({
            "geom": LineString(list(zip(xs, ys))),
            "dur": float(props["duration"]),
            "edge_id": props.get("edge_id"),
            "pred": props.get("pred_edge_id"),
            "ll_first": tuple(coords[0]),
            "ll_last": tuple(coords[-1]),
        })
    if not kept:
        raise ValueError("expansion returned no usable edges")

    by_edge = {e["edge_id"]: e for e in kept if e["edge_id"] is not None}

    # pass 2: node indices
    keys: dict[tuple[int, int], int] = {}
    start_idx = np.empty(len(kept), dtype=np.int64)
    end_idx = np.empty(len(kept), dtype=np.int64)
    for i, e in enumerate(kept):
        for slot, (x, y) in ((start_idx, e["geom"].coords[0]), (end_idx, e["geom"].coords[-1])):
            k = _node_key(x, y)
            if k not in keys:
                keys[k] = len(keys)
            slot[i] = keys[k]

    # successors, so a root edge's orientation can be DERIVED rather than assumed: the vertex a
    # root shares with the edges it expanded into is its far end (Codex pass-7 C5).
    succ_of: dict[object, list[dict]] = {}
    for e in kept:
        if e["pred"] not in _NO_PRED_SENTINELS:
            succ_of.setdefault(e["pred"], []).append(e)

    origin_pts = None
    if origins:
        ox, oy = to_proj.transform([p[0] for p in origins], [p[1] for p in origins])
        origin_pts = shapely.points(np.asarray(ox), np.asarray(oy))

    # pass 3: endpoint times from (predecessor duration, own duration)
    T = np.full(len(keys), np.inf)
    tau = np.empty(len(kept), dtype=np.float64)
    dangling: list[object] = []
    roots_unoriented: list[object] = []
    drop = np.zeros(len(kept), dtype=bool)
    for i, e in enumerate(kept):
        pred = by_edge.get(e["pred"])
        is_root = e["pred"] in _NO_PRED_SENTINELS
        if pred is None and not is_root:
            # A named predecessor we do not have. Its cumulative duration is the only thing that
            # could give this edge's near-end time, so that time is UNKNOWN. Treating it as a root
            # at 0 s would plant a spurious "instantly reachable" node in the middle of the
            # network, which is far worse than omitting the edge.
            dangling.append(e["edge_id"])
            drop[i] = True
            tau[i] = _MIN_EPSILON_S
            continue
        near_t = 0.0 if is_root else float(pred["dur"])
        far_t = e["dur"]
        tau[i] = max(far_t - near_t, _MIN_EPSILON_S)
        if not is_root:
            shared = {pred["ll_first"], pred["ll_last"]}
            if e["ll_first"] in shared:
                near_at_start = True
            elif e["ll_last"] in shared:
                near_at_start = False
            else:
                # geometries do not share a vertex (simplification); fall back to whichever
                # endpoint lies closer to the predecessor's geometry
                near_at_start = e["geom"].interpolate(0.0).distance(pred["geom"]) <= \
                    e["geom"].interpolate(1.0, normalized=True).distance(pred["geom"])
        else:
            near_at_start = _orient_root(e, succ_of.get(e["edge_id"], ()), origin_pts)
            if near_at_start is None:
                # No successor and no origin to compare against: the orientation is genuinely
                # undetermined. Guessing is a coin flip that lands on the destination itself, so
                # record the edge's traversal time but assert nothing about which end is which.
                roots_unoriented.append(e["edge_id"])
                drop[i] = True
                continue
        a, b = (start_idx[i], end_idx[i]) if near_at_start else (end_idx[i], start_idx[i])
        if near_t < T[a]:
            T[a] = near_t
        if far_t < T[b]:
            T[b] = far_t

    if report is not None:
        report.update(edges=len(kept), dangling_predecessors=len(dangling),
                      roots_unoriented=len(roots_unoriented), dropped=int(drop.sum()),
                      origins_supplied=0 if not origins else len(origins))
    if strict and (dangling or roots_unoriented):
        raise ValueError(
            f"expansion tree is not self-consistent: {len(dangling)} edge(s) name a predecessor "
            f"not present in the response and {len(roots_unoriented)} root(s) could not be "
            "oriented. Endpoint times for these are unknown; pass origins=[(lon, lat), ...] to "
            "orient roots, or strict=False to drop them and read the count from report=."
        )

    # Edges whose endpoint times are unknown are removed from the index entirely. Leaving them
    # traversable would let a cell snap onto an edge and read a time from a node that was never
    # resolved; nodes they alone touched stay +inf, which is the honest answer.
    keep_mask = ~drop
    if not keep_mask.any():
        raise ValueError("every expansion edge was unusable; see report= for the breakdown")
    geoms = [e["geom"] for e, k in zip(kept, keep_mask) if k]
    start_idx, end_idx, tau = start_idx[keep_mask], end_idx[keep_mask], tau[keep_mask]
    geom_arr = np.empty(len(geoms), dtype=object)
    geom_arr[:] = geoms
    idx = EdgeIndex(
        tree=shapely.STRtree(geoms),
        geoms=geom_arr,
        start_idx=start_idx,
        end_idx=end_idx,
        fwd_time=tau,
        rev_time=tau,
        # Valhalla has already applied its own costing to produce these durations, so there is no
        # separate penalty to carry here: selection cost and reported time coincide.
        fwd_cost=tau,
        rev_cost=tau,
    )
    return idx, T
