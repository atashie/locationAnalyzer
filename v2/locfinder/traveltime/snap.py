"""Nearest-edge snapping of grid cells onto a projected (metre) graph, with
arrival-time interpolation along the matched edge.

Port of CHCCS school_desert.py `_build_edge_index` / `compute_travel_scores`,
corrected for arrival (to-destination) semantics and one-way edges:

    a point on edge geometry S->E at fraction f (from S) reaches a destination
    either forward via E:   (1 - f) * t(S->E) + T[E]   if the edge S->E exists
    or backward via S:      f * t(E->S) + T[S]         only if the edge E->S exists

where T[n] is the arrival time (seconds) from node n to the nearest destination.
A point exactly at a node uses that node's T directly (zero on-edge travel), even
if the edge is one-way (Codex pass-3 H2: the unavailable direction must be masked,
never multiplied as 0 * inf).

Physical edges are paired by their geometry (forward or reversed coordinates), not
by networkx keys, so parallel roads between the same nodes are never conflated.
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

    @classmethod
    def from_graph(cls, G: nx.MultiDiGraph, index: dict) -> "EdgeIndex":
        geoms: list = []
        starts: list[int] = []
        ends: list[int] = []
        fwd: list[float] = []
        rev: list[float] = []
        seen: dict[tuple, int] = {}
        for u, v, k, data in G.edges(keys=True, data=True):
            t = float(data["travel_time"])
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
                fwd.append(np.inf)
                rev.append(np.inf)
            i = seen[key]
            if iu == starts[i]:
                fwd[i] = min(fwd[i], t)
            else:
                rev[i] = min(rev[i], t)
        arr = np.empty(len(geoms), dtype=object)
        arr[:] = geoms
        return cls(
            tree=shapely.STRtree(geoms),
            geoms=arr,
            start_idx=np.asarray(starts, dtype=np.int64),
            end_idx=np.asarray(ends, dtype=np.int64),
            fwd_time=np.asarray(fwd, dtype=np.float64),
            rev_time=np.asarray(rev, dtype=np.float64),
        )


def cell_seconds_from_arrival(
    idx: EdgeIndex,
    T: np.ndarray,
    xs: np.ndarray,
    ys: np.ndarray,
    *,
    mode: str,
    max_access_m: float,
) -> np.ndarray:
    """Seconds from each (x, y) metre point to the nearest destination, given node
    arrival times T (inf = unreachable). Points farther than `max_access_m` from
    any edge are inf. Output has the shape of `xs`. Never produces NaN."""
    x = np.asarray(xs, dtype=np.float64).ravel()
    y = np.asarray(ys, dtype=np.float64).ravel()
    pts = shapely.points(x, y)
    nearest = idx.tree.nearest(pts)
    geoms = idx.geoms[nearest]
    access_m = shapely.distance(pts, geoms)
    frac = shapely.line_locate_point(geoms, pts, normalized=True)
    s_idx = idx.start_idx[nearest]
    e_idx = idx.end_idx[nearest]
    fwd = idx.fwd_time[nearest]
    rev = idx.rev_time[nearest]
    T_s = T[s_idx]
    T_e = T[e_idx]

    via_end = np.full(frac.shape, np.inf)
    via_start = np.full(frac.shape, np.inf)
    m = np.isfinite(fwd)
    via_end[m] = (1.0 - frac[m]) * fwd[m] + T_e[m]
    m = np.isfinite(rev)
    via_start[m] = frac[m] * rev[m] + T_s[m]
    # exactly at a node: no on-edge travel in that direction is needed
    at_start = frac <= _NODE_EPS
    at_end = frac >= 1.0 - _NODE_EPS
    via_start = np.where(at_start, T_s, via_start)
    via_end = np.where(at_end, T_e, via_end)

    network = np.minimum(via_end, via_start)
    total = network + access_m / access_speed_mps(mode)
    total = np.where(access_m > max_access_m, np.inf, total)
    return total.reshape(np.shape(xs))
