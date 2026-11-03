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
# Valhalla's sentinel for "no predecessor" (kInvalidGraphId), seen as 70368744177663
_MIN_EPSILON_S = 0.1


def _node_key(x: float, y: float) -> tuple[int, int]:
    return (int(round(x / _NODE_SNAP_M)), int(round(y / _NODE_SNAP_M)))


def expansion_to_edge_index(
    features: list[dict],
    *,
    target_crs: str,
    source_crs: str = "EPSG:4326",
) -> tuple[EdgeIndex, np.ndarray]:
    """Build (EdgeIndex, T) from `/expansion` features. `T` holds the arrival time in seconds
    at each node index the EdgeIndex refers to; unreachable nodes are +inf.

    Edges are marked traversable in both directions with their own traversal time, because the
    expansion tree already encodes legality: an edge appears only because the router used it.
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

    # pass 3: endpoint times from (predecessor duration, own duration)
    T = np.full(len(keys), np.inf)
    tau = np.empty(len(kept), dtype=np.float64)
    for i, e in enumerate(kept):
        pred = by_edge.get(e["pred"])
        near_t = float(pred["dur"]) if pred is not None else 0.0
        far_t = e["dur"]
        tau[i] = max(far_t - near_t, _MIN_EPSILON_S)
        near_at_start = True
        if pred is not None:
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
            # root edge: the near end is the search origin, so take the endpoint that is not
            # shared with any successor as "far"; with no information, start is as good as end
            near_at_start = True
        a, b = (start_idx[i], end_idx[i]) if near_at_start else (end_idx[i], start_idx[i])
        if near_t < T[a]:
            T[a] = near_t
        if far_t < T[b]:
            T[b] = far_t

    geoms = [e["geom"] for e in kept]
    geom_arr = np.empty(len(geoms), dtype=object)
    geom_arr[:] = geoms
    idx = EdgeIndex(
        tree=shapely.STRtree(geoms),
        geoms=geom_arr,
        start_idx=start_idx,
        end_idx=end_idx,
        fwd_time=tau,
        rev_time=tau,
    )
    return idx, T
