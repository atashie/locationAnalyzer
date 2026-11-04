"""Nearest-edge snapping of grid cells onto a projected (metre) graph, with arrival-time
interpolation along the matched edge.

Port of CHCCS school_desert.py `_build_edge_index` / `compute_travel_scores`, corrected for
arrival (to-destination) semantics and one-way edges:

    a point on edge geometry S->E at fraction f (from S) reaches a destination
    either forward via E:   (1 - f) * t(S->E) + T[E]   if the edge S->E exists
    or backward via S:      f * t(E->S) + T[S]         only if the edge E->S exists

where T[n] is the arrival time (seconds) from node n to the nearest destination. A point exactly at
a node uses that node's T directly, even on a one-way edge (Codex pass-3 H2: the unavailable
direction must be masked, never multiplied as 0 * inf).

**Selection is by cost, reporting is by time** whenever node costs are supplied (Codex pass-6 H1).
Choosing the branch by time while the node search chose by cost made the cell layer contradict the
node layer: a cell could take a penalised shortcut the search had deliberately rejected. Codex's
counterexample had node reconstruction correctly give 200 s at a node while snapping returned 20 s
at the very same point. With `node_cost` supplied, both branches are compared on cost and the
chosen branch's time is reported; without it, behaviour falls back to time-based selection, which is
correct only on an unpenalised graph.

Physical edges are paired by their geometry (forward or reversed coordinates), not by networkx
keys, so parallel roads between the same nodes are never conflated.
"""
from __future__ import annotations

from dataclasses import dataclass

import networkx as nx
import numpy as np
import shapely
from shapely.geometry import LineString

from .speeds import access_speed_mps, max_speed_mps

_NODE_EPS = 1e-6  # normalized fraction below which a point is "at" the node


def _edge_geometry(G: nx.MultiDiGraph, u, v, data) -> LineString:
    geom = data.get("geometry")
    if geom is None:
        geom = LineString([(G.nodes[u]["x"], G.nodes[u]["y"]), (G.nodes[v]["x"], G.nodes[v]["y"])])
    return geom


def _canonical_geometry_key(geom: LineString) -> bytes:
    coords = np.asarray(geom.coords, dtype=np.float64)
    fwd = coords.tobytes()
    rev = np.ascontiguousarray(coords[::-1]).tobytes()
    return fwd if fwd <= rev else rev


@dataclass
class EdgeIndex:
    tree: shapely.STRtree
    geoms: np.ndarray       # object array of LineString (metres)
    start_idx: np.ndarray   # node index at geometry start (fraction 0)
    end_idx: np.ndarray     # node index at geometry end (fraction 1)
    fwd_time: np.ndarray    # seconds start->end, inf if no such edge
    rev_time: np.ndarray    # seconds end->start, inf if no such edge
    fwd_cost: np.ndarray    # selection cost start->end, inf if no such edge
    rev_cost: np.ndarray    # selection cost end->start, inf if no such edge

    @classmethod
    def from_graph(cls, G: nx.MultiDiGraph, index: dict, *, cost_key: str = "cost") -> "EdgeIndex":
        """Build the index. For each physical edge and direction the **cost-minimal** parallel edge
        wins and its own time is carried, matching `csr.graph_to_cost_time_csr` so the two stages
        cannot disagree about which edge a path uses."""
        geoms: list = []
        starts: list[int] = []
        ends: list[int] = []
        fwd_t: list[float] = []
        rev_t: list[float] = []
        fwd_c: list[float] = []
        rev_c: list[float] = []
        seen: dict[tuple, int] = {}
        for u, v, k, data in G.edges(keys=True, data=True):
            t = float(data["travel_time"])
            c = float(data.get(cost_key, t))
            geom = _edge_geometry(G, u, v, data)
            iu, iv = index[u], index[v]
            key = (min(iu, iv), max(iu, iv), _canonical_geometry_key(geom))
            if key not in seen:
                g0 = geom.coords[0]
                if abs(g0[0] - G.nodes[u]["x"]) + abs(g0[1] - G.nodes[u]["y"]) < 1e-6:
                    s, e = iu, iv
                else:
                    s, e = iv, iu
                seen[key] = len(geoms)
                geoms.append(geom)
                starts.append(s)
                ends.append(e)
                fwd_t.append(np.inf); rev_t.append(np.inf)
                fwd_c.append(np.inf); rev_c.append(np.inf)
            i = seen[key]
            if iu == starts[i]:
                if c < fwd_c[i]:
                    fwd_c[i], fwd_t[i] = c, t
            else:
                if c < rev_c[i]:
                    rev_c[i], rev_t[i] = c, t
        arr = np.empty(len(geoms), dtype=object)
        arr[:] = geoms
        return cls(
            tree=shapely.STRtree(geoms),
            geoms=arr,
            start_idx=np.asarray(starts, dtype=np.int64),
            end_idx=np.asarray(ends, dtype=np.int64),
            fwd_time=np.asarray(fwd_t, dtype=np.float64),
            rev_time=np.asarray(rev_t, dtype=np.float64),
            fwd_cost=np.asarray(fwd_c, dtype=np.float64),
            rev_cost=np.asarray(rev_c, dtype=np.float64),
        )


@dataclass
class _Snapped:
    """The geometric match and the on-network part of the journey, shared by both public entry
    points so the branch arithmetic exists in exactly one place."""

    access_m: np.ndarray
    network: np.ndarray      # seconds on the network from the matched point, inf if unavailable
    s_idx: np.ndarray
    e_idx: np.ndarray
    relevant_s: np.ndarray   # whether the start node's arrival time could have been used
    relevant_e: np.ndarray   # whether the end node's arrival time could have been used


def _snap_network(
    idx: EdgeIndex,
    T: np.ndarray,
    x: np.ndarray,
    y: np.ndarray,
    *,
    node_cost: np.ndarray | None,
) -> _Snapped:
    pts = shapely.points(x, y)
    nearest = idx.tree.nearest(pts)
    geoms = idx.geoms[nearest]
    access_m = shapely.distance(pts, geoms)
    frac = shapely.line_locate_point(geoms, pts, normalized=True)
    s_idx = idx.start_idx[nearest]
    e_idx = idx.end_idx[nearest]
    fwd_t, rev_t = idx.fwd_time[nearest], idx.rev_time[nearest]
    fwd_c, rev_c = idx.fwd_cost[nearest], idx.rev_cost[nearest]
    T_s, T_e = T[s_idx], T[e_idx]

    time_end = np.full(frac.shape, np.inf)
    time_start = np.full(frac.shape, np.inf)
    m = np.isfinite(fwd_t)
    time_end[m] = (1.0 - frac[m]) * fwd_t[m] + T_e[m]
    m = np.isfinite(rev_t)
    time_start[m] = frac[m] * rev_t[m] + T_s[m]
    # exactly at a node: no on-edge travel in that direction is needed
    at_start = frac <= _NODE_EPS
    at_end = frac >= 1.0 - _NODE_EPS
    time_start = np.where(at_start, T_s, time_start)
    time_end = np.where(at_end, T_e, time_end)

    if node_cost is None:
        network = np.minimum(time_end, time_start)
    else:
        D_s, D_e = node_cost[s_idx], node_cost[e_idx]
        cost_end = np.full(frac.shape, np.inf)
        cost_start = np.full(frac.shape, np.inf)
        m = np.isfinite(fwd_c)
        cost_end[m] = (1.0 - frac[m]) * fwd_c[m] + D_e[m]
        m = np.isfinite(rev_c)
        cost_start[m] = frac[m] * rev_c[m] + D_s[m]
        cost_start = np.where(at_start, D_s, cost_start)
        cost_end = np.where(at_end, D_e, cost_end)
        # Minimum cost, ties broken by the lower time. The comparison must be *symmetric*, or
        # reversing an edge's stored geometry changes the answer: the previous rule let
        # `cost_end < cost_start` win outright while applying the time preference only inside an
        # `np.isclose` band, so a 0.004 s cost difference reported 90 s one way round and 10 s the
        # other (Codex pass-12 M7). A relative tolerance was also wrong on its own terms — at a
        # 7,000 s cost it treats a 70 ms cost difference as a tie, and the contract says choose on
        # cost. Exact equality makes "cheaper wins, equal costs prefer the quicker" order-invariant.
        tie = cost_end == cost_start
        take_end = np.where(tie, time_end <= time_start, cost_end < cost_start)
        network = np.where(take_end, time_end, time_start)
        network = np.where(np.isfinite(cost_end) | np.isfinite(cost_start), network, np.inf)

    # Which endpoint could have supplied the answer. A one-way edge offers only one, so the other
    # node's reason explains nothing about this cell; at a node, that node always counts.
    return _Snapped(
        access_m=access_m,
        network=network,
        s_idx=s_idx,
        e_idx=e_idx,
        relevant_s=np.isfinite(rev_t) | at_start,
        relevant_e=np.isfinite(fwd_t) | at_end,
    )


def cell_seconds_from_arrival(
    idx: EdgeIndex,
    T: np.ndarray,
    xs: np.ndarray,
    ys: np.ndarray,
    *,
    mode: str,
    max_access_m: float,
    node_cost: np.ndarray | None = None,
    cutoff_s: float | None = None,
) -> np.ndarray:
    """Seconds from each (x, y) metre point to the nearest destination, given node arrival times T
    (inf = unreachable). Points farther than `max_access_m` from any edge are inf. Never NaN.

    `node_cost`: the node-level selection costs that produced T. When given, the forward/backward
    branch is chosen on cost and the chosen branch's **time** is returned, so the cell agrees with
    the node search. When omitted, selection falls back to time, which is correct only if nothing is
    penalised.

    `cutoff_s`: applied to the FINAL time, after the off-network access leg, so the advertised
    budget is the one actually enforced (Codex pass-6 H1).

    Returns seconds only. `cell_arrival_with_provenance` returns the same numbers plus *why* a cell
    has none, which is what a published layer needs (see `locfinder/status.py`).
    """
    x = np.asarray(xs, dtype=np.float64).ravel()
    y = np.asarray(ys, dtype=np.float64).ravel()
    snapped = _snap_network(idx, T, x, y, node_cost=node_cost)
    total = snapped.network + snapped.access_m / access_speed_mps(mode)
    total = np.where(snapped.access_m > max_access_m, np.inf, total)
    if cutoff_s is not None:
        total = np.where(total > float(cutoff_s), np.inf, total)
    return total.reshape(np.shape(xs))


def cell_arrival_with_provenance(
    idx: EdgeIndex,
    T: np.ndarray,
    xs: np.ndarray,
    ys: np.ndarray,
    *,
    mode: str,
    max_access_m: float,
    horizon_s: float,
    node_reason: np.ndarray,
    node_cost: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """`(seconds, reason, min_possible_s)` — the same times as `cell_seconds_from_arrival` plus the
    cause of every missing one, as `locfinder.status.Reason` codes.

    `horizon_s` is the layer's single built horizon: it is both the per-cell cutoff and, for a
    bounded engine, the contour the node search was run to. One number, so "past the horizon" means
    one thing.

    `node_reason` comes from `status.node_reasons(T, engine, search_bounded=...)`. It is what
    makes `NO_PATH` and
    `BEYOND_HORIZON` distinguishable here: only the caller knows whether its search was exhaustive.

    `min_possible_s` is a sound lower bound on the time this model would have reported, which turns
    some missing values into *known* criterion failures rather than unknowns (see `status.py`).
    """
    from ..status import Reason  # local: status imports nothing from traveltime, keep it that way

    x = np.asarray(xs, dtype=np.float64).ravel()
    y = np.asarray(ys, dtype=np.float64).ravel()
    snapped = _snap_network(idx, T, x, y, node_cost=node_cost)
    access_s = snapped.access_m / access_speed_mps(mode)
    total = snapped.network + access_s
    off = snapped.access_m > max_access_m
    # "a route was found but it is too long" requires a route: an infinite network part also
    # satisfies `total > horizon_s`, and letting it through here would relabel every unreachable
    # cell as merely past the horizon.
    over = ~off & np.isfinite(snapped.network) & (total > float(horizon_s))

    nr = np.asarray(node_reason)
    beyond_node = (snapped.relevant_e & (nr[snapped.e_idx] == Reason.BEYOND_HORIZON)) | (
        snapped.relevant_s & (nr[snapped.s_idx] == Reason.BEYOND_HORIZON)
    )
    unreached = ~off & ~np.isfinite(snapped.network)

    reason = np.full(total.shape, np.int8(Reason.OK), dtype=np.int8)
    # Order matters only in that each branch is disjoint from the ones after it. An off-network
    # cell is off-network whatever its (unusable) nearest edge says.
    reason = np.where(unreached & ~beyond_node, np.int8(Reason.NO_PATH), reason)
    reason = np.where(unreached & beyond_node, np.int8(Reason.BEYOND_HORIZON), reason)
    reason = np.where(over, np.int8(Reason.BEYOND_HORIZON), reason)
    reason = np.where(off, np.int8(Reason.OFF_NETWORK), reason)

    seconds = np.where(reason == Reason.OK, total, np.inf)
    # Every cell's journey covers at least its straight-line distance to the network, at no more
    # than the model's fastest speed. A tighter bound is available and sound for this model -- the
    # access leg is charged at `access_speed_mps`, which is slower -- but it is deliberately not
    # used: that leg is a straight line over unmapped ground, and the tighter bound would use the
    # fiction to exclude households rather than call them unknown (Codex pass-8 L2).
    min_possible = snapped.access_m / max_speed_mps(mode)
    min_possible = np.where(reason == Reason.BEYOND_HORIZON, float(horizon_s), min_possible)
    min_possible = np.where(reason == Reason.NO_PATH, np.inf, min_possible)

    shape = np.shape(xs)
    return seconds.reshape(shape), reason.reshape(shape), min_possible.reshape(shape)
