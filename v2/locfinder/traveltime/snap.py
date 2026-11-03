"""Nearest-edge snapping of grid cells onto a projected (metre) graph, with
arrival-time interpolation along the matched edge.

Port of CHCCS school_desert.py `_build_edge_index` / `compute_travel_scores`,
corrected for arrival (to-destination) semantics and one-way edges:

    a point on edge geometry S->E at fraction f (from S) reaches a destination
    either forward via E:   (1 - f) * t(S->E) + T[E]   if the edge S->E exists
    or backward via S:      f * t(E->S) + T[S]         only if the edge E->S exists

where T[n] is the arrival time (seconds) from node n to the nearest destination.
"""
from __future__ import annotations

from dataclasses import dataclass

import networkx as nx
import numpy as np
import shapely
from shapely.geometry import LineString

from .speeds import access_speed_mps


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
            key = (min(u, v), max(u, v), k)
            t = float(data["travel_time"])
            if key not in seen:
                geom = data.get("geometry")
                if geom is None:
                    geom = LineString([(G.nodes[u]["x"], G.nodes[u]["y"]), (G.nodes[v]["x"], G.nodes[v]["y"])])
                g0 = geom.coords[0]
                if abs(g0[0] - G.nodes[u]["x"]) + abs(g0[1] - G.nodes[u]["y"]) < 1e-6:
                    s, e = u, v
                else:
                    s, e = v, u
                seen[key] = len(geoms)
                geoms.append(geom)
                starts.append(index[s])
                ends.append(index[e])
                fwd.append(np.inf)
                rev.append(np.inf)
            i = seen[key]
            if index[u] == starts[i]:
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
    any edge are inf. Output has the shape of `xs`."""
    x = np.asarray(xs, dtype=np.float64).ravel()
    y = np.asarray(ys, dtype=np.float64).ravel()
    pts = shapely.points(x, y)
    nearest = idx.tree.nearest(pts)
    geoms = idx.geoms[nearest]
    access_m = shapely.distance(pts, geoms)
    frac = shapely.line_locate_point(geoms, pts, normalized=True)
    s_idx = idx.start_idx[nearest]
    e_idx = idx.end_idx[nearest]
    via_end = (1.0 - frac) * idx.fwd_time[nearest] + T[e_idx]
    via_start = frac * idx.rev_time[nearest] + T[s_idx]
    network = np.minimum(via_end, via_start)
    total = network + access_m / access_speed_mps(mode)
    total = np.where(access_m > max_access_m, np.inf, total)
    return total.reshape(np.shape(xs))
