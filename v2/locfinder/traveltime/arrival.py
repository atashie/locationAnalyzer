"""Multi-source arrival times: seconds from every node to the NEAREST destination.

Computed as single-source shortest paths from the destinations on the TRANSPOSED
graph (Codex pass-1 finding C1: an outward search from the destination on the
original graph answers "where can the destination reach", which is the wrong
direction on one-way streets). Unreachable nodes, and nodes beyond `cutoff_s`,
are +inf.
"""
from __future__ import annotations

import numpy as np
import scipy.sparse as sp
from scipy.sparse.csgraph import dijkstra


def arrival_seconds(csr: sp.csr_matrix, *, dest_idx, cutoff_s: float | None = None) -> np.ndarray:
    dest = np.asarray(list(dest_idx), dtype=np.int64)
    n = csr.shape[0]
    if dest.size == 0:
        return np.full(n, np.inf)
    transposed = csr.transpose().tocsr()
    limit = np.inf if cutoff_s is None else float(cutoff_s)
    dist = dijkstra(transposed, directed=True, indices=dest, min_only=True, limit=limit)
    dist = np.asarray(dist, dtype=np.float64)
    if cutoff_s is not None:
        # scipy returns inf beyond `limit`; keep that contract explicit in case a
        # future version returns the limit value instead.
        dist[dist > limit] = np.inf
    return dist
