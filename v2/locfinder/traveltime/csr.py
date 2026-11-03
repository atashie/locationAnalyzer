"""Convert a weighted networkx MultiDiGraph into scipy CSR matrices.

Parallel edges keep the minimum weight. Direction is preserved exactly as in the graph: no reverse
edges are added here. Pedestrian graphs must be symmetrised by the caller (see speeds.symmetrise),
never drive or bike graphs.

`graph_to_cost_time_csr` returns a **pair** of matrices over the same sparsity: a cost matrix for
choosing paths and a time matrix for reporting them. They differ wherever an edge carries a penalty,
which is how a restricted driveway can cost extra to choose without inflating the minutes a user
sees (see access.py).
"""
from __future__ import annotations

import networkx as nx
import numpy as np
import scipy.sparse as sp


def _validate(u, v, key: str, w: float) -> float:
    if w <= 0 or not np.isfinite(w):
        raise ValueError(f"edge {u}->{v} has non-positive or non-finite {key}={w}")
    return w


def graph_to_csr(G: nx.MultiDiGraph, *, weight: str = "travel_time") -> tuple[sp.csr_matrix, dict]:
    """Single-weight CSR. Use only when cost and time are the same thing."""
    nodes = list(G.nodes())
    index = {n: i for i, n in enumerate(nodes)}
    best: dict[tuple[int, int], float] = {}
    for u, v, data in G.edges(data=True):
        w = _validate(u, v, weight, float(data[weight]))
        k = (index[u], index[v])
        prev = best.get(k)
        if prev is None or w < prev:
            best[k] = w
    n = len(nodes)
    if not best:
        return sp.csr_matrix((n, n), dtype=np.float64), index
    rows, cols = zip(*best.keys())
    coo = sp.coo_matrix((list(best.values()), (rows, cols)), shape=(n, n), dtype=np.float64)
    return coo.tocsr(), index


def graph_to_cost_time_csr(
    G: nx.MultiDiGraph, *, cost: str = "cost", time: str = "travel_time"
) -> tuple[sp.csr_matrix, sp.csr_matrix, dict]:
    """Return (cost_csr, time_csr, index) over identical sparsity.

    For parallel edges the **cost**-minimal one wins and its own time is carried, so the reported
    time always belongs to the path actually chosen rather than to a cheaper-but-unused parallel
    edge. Edges missing `cost` fall back to their time, which keeps unpenalised graphs working.
    """
    nodes = list(G.nodes())
    index = {n: i for i, n in enumerate(nodes)}
    best: dict[tuple[int, int], tuple[float, float]] = {}
    for u, v, data in G.edges(data=True):
        t = _validate(u, v, time, float(data[time]))
        c = float(data.get(cost, t))
        if c <= 0 or not np.isfinite(c):
            raise ValueError(f"edge {u}->{v} has non-positive or non-finite {cost}={c}")
        k = (index[u], index[v])
        prev = best.get(k)
        if prev is None or c < prev[0]:
            best[k] = (c, t)
    n = len(nodes)
    if not best:
        empty = sp.csr_matrix((n, n), dtype=np.float64)
        return empty, empty.copy(), index
    rows, cols = zip(*best.keys())
    costs = [v[0] for v in best.values()]
    times = [v[1] for v in best.values()]
    cost_csr = sp.coo_matrix((costs, (rows, cols)), shape=(n, n), dtype=np.float64).tocsr()
    time_csr = sp.coo_matrix((times, (rows, cols)), shape=(n, n), dtype=np.float64).tocsr()
    return cost_csr, time_csr, index
