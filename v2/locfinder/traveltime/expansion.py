"""Turn a Valhalla `/expansion` search tree into the (EdgeIndex, node-times) form that
`snap.cell_seconds_from_arrival` already consumes.

`/expansion` with `action=isochrone` returns one LineString per settled **directed** edge. With
`expansion_properties=["duration", "distance", "edge_id", "pred_edge_id"]` each feature carries:

* `duration` — **cumulative** whole seconds at the far end of this edge (the end the search
  settled),
* `distance` — cumulative metres at that same point,
* `edge_id` / `pred_edge_id` — the search tree, so the predecessor's cumulative duration is the
  time at this edge's **near** end.

That makes the reconstruction exact: an edge's two endpoint times are `pred.duration` (near) and
`duration` (far), its own traversal time is the difference, and the endpoint shared with the
predecessor's geometry identifies which is which. No speed estimate is involved, so the result
inherits Valhalla's costing exactly, and `cell_seconds_from_arrival` can then interpolate within
the matched edge instead of charging a whole edge traversal (the +66 s conservative bias measured
in docs/experiments/g1-routing.md).

Root edges, whose `pred_edge_id` is Valhalla's sentinel, are the search origin: their near end is
the destination itself, at time 0. They are a handful of edges out of a quarter of a million.

## Direction, and why the request matters (Phase 1 S1.3)

A feature is a *directed* edge, and under arrival semantics the traveller crosses it **from its far
end to its near end**. The earlier version of this module marked every edge traversable both ways
with the same traversal time, arguing that the tree "already encodes legality". It encodes legality
in one direction only, so that let a cell drive the wrong way down a one-way street.

It also appended every feature as its own geometry, never merging the two directed features that
describe one physical road. With both directions requested, the same geometry then entered the
STRtree twice and `nearest()` returned one of them arbitrarily, carrying only that direction's time.

Measured on a real drive payload (3 grocery POIs, 60-minute contour, 476,072 features over 253,635
physical edges), against the cells of the Triangle grid:

| defect | cells changed | median | direction of change |
|---|---|---|---|
| not merging duplicate geometries | 13,396 (8.73%) | −2.5 s | 99.4% got **earlier** |
| marking one-way edges bidirectional | 13,970 (9.10%) | +2.5 s | **100%** got **later** |

The two move opposite ways, which is why a single before/after comparison showed only 3.04% and a
misleading sign. The direction column's 100% is the consistency check: removing edges from a graph
can never shorten a shortest path.

**`skip_opposites` must be `false`.** With it on, Valhalla omits the opposite direction of an edge
it has already settled, which has two consequences. An edge whose predecessor *was* one of those
omitted opposites names an `edge_id` that was never serialised — 636 of 254,323 edges (0.25%) on
the payload above, which is why `strict=True` failed on every real request — and a two-way street
appears once, making it impossible to tell from the payload alone whether the unseen direction is
illegal or merely unrequested. With `skip_opposites=false` the dangling count was **0**.

That is why `opposites_included` has no default: it is a property of the request, and the adapter
cannot infer it safely. One tempting inference is provably wrong — `skip_opposites=true` does *not*
suppress every opposite, and 664 of 253,635 physical edges (0.26%) still arrived in both directions
on the payload above — so the adapter records what it found in `report` rather than second-guessing
the caller, and leaves `strict` to refuse a payload whose dangling count betrays the wrong flag.
"""
from __future__ import annotations

import numpy as np
import shapely
from pyproj import Transformer
from shapely.geometry import LineString
from shapely.ops import substring

from .snap import EdgeIndex

# metres: endpoints within this distance are treated as the same node
_NODE_SNAP_M = 0.5
_MIN_EPSILON_S = 0.1
# seconds: cumulative durations must not decrease along the tree beyond whole-second quantisation.
# Clamping a decrease to the epsilon floor used to accept a non-monotone tree silently, so that a
# far endpoint could carry a SMALLER time than its own near end (Codex pass-9 M4).
_MONOTONE_TOL_S = 1.0
# decimal places for the lon/lat key that identifies one physical edge regardless of stored
# direction. Seven places is ~1 cm, far finer than any geometry difference between the two
# directed features Valhalla emits for the same road.
_KEY_DP = 7
# metres: a root whose origin projects this close to an endpoint is not worth splitting
_MIN_SPLIT_M = 0.5
# Valhalla's sentinel for "no predecessor" (kInvalidGraphId). A feature carrying this really is a
# search root. A feature naming a predecessor we do NOT have is a different thing entirely -- its
# near-end time is unknown -- and conflating the two invents a zero-time node (Codex pass-7 C5).
_NO_PRED_SENTINELS = frozenset({None, 70368744177663, -1})


def _node_key(x: float, y: float) -> tuple[int, int]:
    return (int(round(x / _NODE_SNAP_M)), int(round(y / _NODE_SNAP_M)))


def _coord_tuple(coords) -> tuple:
    return tuple((round(float(c[0]), _KEY_DP), round(float(c[1]), _KEY_DP)) for c in coords)


def _physical_key(coords) -> tuple:
    """One key per physical edge: the coordinate list, canonicalised over stored direction."""
    fwd = _coord_tuple(coords)
    rev = tuple(reversed(fwd))
    return fwd if fwd <= rev else rev


def _root_far_from_successors(edge, successors) -> bool | None:
    """Is a root's FAR end its last coordinate? Topological, from the edges it expanded into.

    The reverse search leaves a root through its far end, so the vertex shared with a successor is
    the far end. This is the **strongest** signal and now takes priority over origin proximity: a
    search origin is a POI that is not on the road at all (measured 11-26 m away), so the endpoint
    nearer the POI is not reliably the near end, and Codex pass-9 H1 found two of six real drive
    roots where proximity contradicted this unambiguous signal.
    """
    shared = set()
    for s in successors:
        shared |= {s["ll_first"], s["ll_last"]}
    if not shared:
        return None
    first_shared = edge["ll_first"] in shared
    last_shared = edge["ll_last"] in shared
    if first_shared == last_shared:
        return None
    return last_shared


def _split_root(edge, far_at_end: bool, origin_pts):
    """Cut a root edge at the search origin's position along it, and return the half the search
    actually traversed: `(geometry from the origin to the far end, traversal seconds)`.

    A root is a **partial** edge (Codex pass-9 H1). The origin sits inside the road — Valhalla does
    not split the edge in its output — so neither endpoint is the near end, and the previous version
    put time zero at a vertex that a matrix query showed to be 2-5 s of real travel from the
    destination. Worse, both opposing roots of the same road then chose the *same* nearer endpoint,
    were re-expressed into the same travel direction, and merged into one, deleting a legal
    direction.

    Splitting fixes all three: the virtual node at the origin's projection carries time 0, the
    root's `duration` is the traversal time of exactly the half that was traversed, and the two
    opposing roots become two distinct sub-edges meeting at that node, so neither is lost.

    Returns `None` when the origin projects onto an endpoint (nothing to split).
    """
    geom = edge["geom"]
    nearest_origin = shapely.points(
        *geom.interpolate(geom.project(
            origin_pts[int(np.argmin(shapely.distance(geom, origin_pts)))])).coords[0])
    d = float(geom.project(nearest_origin))
    if d <= _MIN_SPLIT_M or d >= geom.length - _MIN_SPLIT_M:
        return None
    half = substring(geom, d, geom.length) if far_at_end else substring(geom, 0.0, d)
    if half.is_empty or half.length <= _MIN_SPLIT_M:
        return None
    coords = list(half.coords)
    if far_at_end:
        return LineString(coords)           # starts at the origin projection, ends at the far end
    return LineString(list(reversed(coords)))


def expansion_to_edge_index(
    features: list[dict],
    *,
    target_crs: str,
    opposites_included: bool,
    source_crs: str = "EPSG:4326",
    origins: list[tuple[float, float]] | None = None,
    strict: bool = True,
    report: dict | None = None,
) -> tuple[EdgeIndex, np.ndarray]:
    """Build (EdgeIndex, T) from `/expansion` features. `T` holds the arrival time in seconds
    at each node index the EdgeIndex refers to; unreachable nodes are +inf.

    The two directed features describing one physical road are **merged** into one index entry
    carrying each settled direction's own traversal time.

    `opposites_included` says whether the request used `skip_opposites=false`, so that both
    directions of a two-way road are present. It has no default because the adapter cannot infer
    it safely and the consequences are opposite:

    * `True` — an edge is traversable only in the direction(s) actually settled. This is correct and
      is what a published layer should use.
    * `False` — a two-way road appears once, so direction cannot be recovered; every edge is marked
      traversable both ways, which is **over-permissive on one-ways** and is recorded in `report`.
      Use it only for a diagnostic.

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
            "key": _physical_key(coords),
        })
    if not kept:
        raise ValueError("expansion returned no usable edges")

    by_edge = {e["edge_id"]: e for e in kept if e["edge_id"] is not None}

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

    # pass 2: one record per physical edge, accumulating each direction's traversal time
    nodes: dict[tuple[int, int], int] = {}
    phys: dict[tuple, dict] = {}
    dangling: list[object] = []
    roots_unoriented: list[object] = []
    roots_from_proximity: list[object] = []
    roots_split: list[object] = []
    decreasing: list[object] = []

    def node_id(x: float, y: float) -> int:
        k = _node_key(x, y)
        if k not in nodes:
            nodes[k] = len(nodes)
        return nodes[k]

    for e in kept:
        is_root = e["pred"] in _NO_PRED_SENTINELS
        pred = by_edge.get(e["pred"])
        if pred is None and not is_root:
            # A named predecessor we do not have. Its cumulative duration is the only thing that
            # could give this edge's near-end time, so that time is UNKNOWN. Treating it as a root
            # at 0 s would plant a spurious "instantly reachable" node in the middle of the
            # network, which is far worse than omitting the edge. With skip_opposites=false this
            # does not happen at all.
            dangling.append(e["edge_id"])
            continue
        near_t = 0.0 if is_root else float(pred["dur"])
        far_t = e["dur"]
        if far_t < near_t - _MONOTONE_TOL_S:
            decreasing.append(e["edge_id"])
            continue
        tau = max(far_t - near_t, _MIN_EPSILON_S)
        if is_root:
            far_at_end = _root_far_from_successors(e, succ_of.get(e["edge_id"], ()))
            if far_at_end is None:
                # No successor to read the far end from. Fall back to origin proximity, which is
                # weak (the origin is off the road) but better than a coin flip; record it.
                if origin_pts is None or not len(origin_pts):
                    roots_unoriented.append(e["edge_id"])
                    continue
                first = shapely.points(*e["geom"].coords[0])
                last = shapely.points(*e["geom"].coords[-1])
                d_first = float(shapely.distance(first, origin_pts).min())
                d_last = float(shapely.distance(last, origin_pts).min())
                if abs(d_first - d_last) <= _NODE_SNAP_M:
                    roots_unoriented.append(e["edge_id"])
                    continue
                far_at_end = d_first < d_last
                roots_from_proximity.append(e["edge_id"])
            half = (_split_root(e, far_at_end, origin_pts)
                    if origin_pts is not None and len(origin_pts) else None)
            if half is not None:
                # The split half starts at the origin's projection (time 0) and ends at the far
                # end, so the near end IS the geometry start and travel runs end -> start.
                e = {**e, "geom": half, "key": None,
                     "ll_first": None, "ll_last": None}
                e["key"] = _physical_key(half.coords)
                roots_split.append(None)
                near_at_start = True
            else:
                # far at the geometry end means near at the geometry start, and vice versa
                near_at_start = far_at_end
        else:
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

        rec = phys.get(e["key"])
        if rec is None:
            rec = {
                "geom": e["geom"],
                "s": node_id(*e["geom"].coords[0]),
                "e": node_id(*e["geom"].coords[-1]),
                "fwd": np.inf, "rev": np.inf, "t_s": np.inf, "t_e": np.inf, "n": 0,
            }
            phys[e["key"]] = rec
        rec["n"] += 1
        # A later feature for the same physical edge may store its coordinates in the opposite
        # order, so the orientation must be expressed relative to the record's own geometry.
        # Compare the WHOLE sequence, not just the first vertex: for a closed loop both stored
        # directions start at the same point, so an endpoint-only test always said "same order"
        # and merged a loop with its reverse into one direction (Codex pass-9 H3).
        same_order = _coord_tuple(e["geom"].coords) == _coord_tuple(rec["geom"].coords)
        near_at_rec_start = near_at_start if same_order else not near_at_start
        if near_at_rec_start:
            # travel runs far -> near, i.e. record-end -> record-start
            rec["rev"] = min(rec["rev"], tau)
            rec["t_s"] = min(rec["t_s"], near_t)
            rec["t_e"] = min(rec["t_e"], far_t)
        else:
            rec["fwd"] = min(rec["fwd"], tau)
            rec["t_e"] = min(rec["t_e"], near_t)
            rec["t_s"] = min(rec["t_s"], far_t)

    merged_pairs = sum(1 for r in phys.values() if r["n"] > 1)
    # A key groups a SHAPE, not a topological edge. On a real drive payload 519 groups held more
    # than two features and the largest held five, so "one shape = one opposing pair" is an
    # assumption this adapter cannot verify without opposing-edge identities (Codex pass-9 H2).
    # Report it; do not claim identity.
    over_paired = sum(1 for r in phys.values() if r["n"] > 2)
    if report is not None:
        report.update(
            edges=len(kept), physical_edges=len(phys), merged_pairs=merged_pairs,
            groups_over_two_features=over_paired,
            dangling_predecessors=len(dangling), roots_unoriented=len(roots_unoriented),
            roots_oriented_by_proximity=len(roots_from_proximity),
            roots_split_at_origin=len(roots_split),
            decreasing_durations=len(decreasing),
            dropped=len(dangling) + len(roots_unoriented) + len(decreasing),
            origins_supplied=0 if not origins else len(origins),
            opposites_included=opposites_included,
            bidirectional_fallback=not opposites_included,
        )
    if strict and (dangling or roots_unoriented or decreasing):
        raise ValueError(
            f"expansion tree is not self-consistent: {len(dangling)} edge(s) name a predecessor "
            f"not present in the response, {len(roots_unoriented)} root(s) could not be oriented "
            f"and {len(decreasing)} edge(s) have a cumulative duration below their predecessor's. "
            "Endpoint times for these are unknown; request skip_opposites=false (which removes the "
            "dangling case entirely), pass origins=[(lon, lat), ...] to orient and split roots, or "
            "strict=False to drop them and read the counts from report=. `strict` checks tree "
            "self-consistency only -- it is not a validity gate for the whole reconstruction."
        )
    # No cross-check raise. The obvious one -- "opposites_included=False yet some edges appear in
    # both directions" -- is wrong, because `skip_opposites=true` does **not** suppress every
    # opposite: on a real drive payload 664 of 253,635 physical edges (0.26%) still arrived in both
    # directions, presumably settled in separate branches before the skip could apply. The report
    # carries `merged_pairs`, `dangling_predecessors` and `bidirectional_fallback` instead, and
    # `strict` is the gate: a non-zero dangling count is the real signature of `skip_opposites=true`.

    if not phys:
        raise ValueError("every expansion edge was unusable; see report= for the breakdown")

    geoms = [r["geom"] for r in phys.values()]
    T = np.full(len(nodes), np.inf)
    starts: list[int] = []
    ends: list[int] = []
    fwd: list[float] = []
    rev: list[float] = []
    for r in phys.values():
        starts.append(r["s"])
        ends.append(r["e"])
        fwd.append(r["fwd"])
        rev.append(r["rev"])
        T[r["s"]] = min(T[r["s"]], r["t_s"])
        T[r["e"]] = min(T[r["e"]], r["t_e"])

    fwd_arr = np.asarray(fwd, dtype=np.float64)
    rev_arr = np.asarray(rev, dtype=np.float64)
    if not opposites_included:
        # Direction is unrecoverable from this payload, so fall back to the old over-permissive
        # marking rather than inventing a restriction. `report["bidirectional_fallback"]` says so.
        best = np.fmin(fwd_arr, rev_arr)
        fwd_arr = rev_arr = best

    geom_arr = np.empty(len(geoms), dtype=object)
    geom_arr[:] = geoms
    idx = EdgeIndex(
        tree=shapely.STRtree(geoms),
        geoms=geom_arr,
        start_idx=np.asarray(starts, dtype=np.int64),
        end_idx=np.asarray(ends, dtype=np.int64),
        fwd_time=fwd_arr,
        rev_time=rev_arr,
        # Valhalla has already applied its own costing to produce these durations, so there is no
        # separate penalty to carry here: selection cost and reported time coincide. Valhalla does
        # report a distinct `cost` per edge, and carrying it as a selection weight the way the
        # own-graph path does is a named follow-up, not done here.
        fwd_cost=fwd_arr,
        rev_cost=rev_arr,
    )
    return idx, T
