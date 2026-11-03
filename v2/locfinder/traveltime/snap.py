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

from .speeds import access_speed_mps

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
    """
    x = np.asarray(xs, dtype=np.float64).ravel()
    y = np.asarray(ys, dtype=np.float64).ravel()
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
        # choose on cost, report that branch's time; ties go to the lower time
        take_end = (cost_end < cost_start) | (
            np.isclose(cost_end, cost_start) & (time_end <= time_start)
        )
        network = np.where(take_end, time_end, time_start)
        network = np.where(np.isfinite(cost_end) | np.isfinite(cost_start), network, np.inf)

    total = network + access_m / access_speed_mps(mode)
    total = np.where(access_m > max_access_m, np.inf, total)
    if cutoff_s is not None:
        total = np.where(total > float(cutoff_s), np.inf, total)
    return total.reshape(np.shape(xs))
