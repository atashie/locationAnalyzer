"""Convert a weighted networkx MultiDiGraph into a scipy CSR matrix.

Parallel edges keep the minimum weight. Direction is preserved exactly as in the
graph: no reverse edges are added here. Pedestrian graphs must be symmetrised by
the caller (see speeds.symmetrise), never drive or bike graphs.
"""
from __future__ import annotations

import networkx as nx
import numpy as np
import scipy.sparse as sp


def graph_to_csr(G: nx.MultiDiGraph, *, weight: str = "travel_time") -> tuple[sp.csr_matrix, dict]:
    """Return (csr, index) where index maps node id -> row/column position.

    Raises ValueError on a non-positive or non-finite weight, because a zero-cost
    edge would be dropped by the sparse representation and an infinite one would
    poison Dijkstra.
    """
    nodes = list(G.nodes())
    index = {n: i for i, n in enumerate(nodes)}
    best: dict[tuple[int, int], float] = {}
    for u, v, data in G.edges(data=True):
        w = float(data[weight])
        if w <= 0 or not np.isfinite(w):
            raise ValueError(f"edge {u}->{v} has non-positive or non-finite {weight}={w}")
        key = (index[u], index[v])
        prev = best.get(key)
        if prev is None or w < prev:
            best[key] = w
    n = len(nodes)
    if not best:
        return sp.csr_matrix((n, n), dtype=np.float64), index
    rows, cols = zip(*best.keys())
    coo = sp.coo_matrix((list(best.values()), (rows, cols)), shape=(n, n), dtype=np.float64)
    return coo.tocsr(), index
