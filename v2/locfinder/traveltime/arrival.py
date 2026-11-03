"""Multi-source arrival times: seconds from every node to the NEAREST destination.

Computed as shortest paths from the destinations on the TRANSPOSED graph (Codex pass-1 finding C1:
an outward search from the destination answers "where can the destination reach", which is the wrong
direction on one-way streets).

Two variants:

* `arrival_seconds` selects and reports on one weight. Correct when cost and time are the same
  thing, which is true only when nothing is penalised.
* `arrival_seconds_two_weight` selects paths on **cost** and reports **real time**. This is what a
  product needs the moment any penalty exists: a restricted driveway should cost extra to choose but
  must not inflate the minutes shown to a user. See `access.py` for why that distinction matters —
  126,157 restricted edges in the Triangle extract, and the homes on them.
"""
from __future__ import annotations

import numpy as np
import scipy.sparse as sp
from scipy.sparse.csgraph import dijkstra

_NO_PREDECESSOR = -9999


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
        dist[dist > limit] = np.inf
    return dist


def arrival_seconds_two_weight(
    cost_csr: sp.csr_matrix,
    time_csr: sp.csr_matrix,
    *,
    dest_idx,
    cutoff_s: float | None = None,
) -> np.ndarray:
    """Real travel seconds to the nearest destination, along the **cost**-optimal path.

    The search runs unbounded on cost, because pruning on cost could discard a path whose real time
    is inside the cutoff; `cutoff_s` is applied to the reconstructed time instead.

    Returns +inf for unreachable nodes. Never returns a penalty-inflated time.
    """
    if cost_csr.shape != time_csr.shape:
        raise ValueError(f"cost {cost_csr.shape} and time {time_csr.shape} matrices must match")
    dest = np.asarray(list(dest_idx), dtype=np.int64)
    n = cost_csr.shape[0]
    if dest.size == 0:
        return np.full(n, np.inf)

    cost_t = cost_csr.transpose().tocsr()
    time_t = time_csr.transpose().tocsr()
    dist, pred, _sources = dijkstra(
        cost_t, directed=True, indices=dest, min_only=True, return_predecessors=True
    )
    dist = np.asarray(dist, dtype=np.float64)
    pred = np.asarray(pred, dtype=np.int64)

    out = np.full(n, np.inf)
    reachable = np.flatnonzero(np.isfinite(dist))
    if reachable.size == 0:
        return out
    # Sources (the destinations themselves) are at zero. Every other reachable node is resolved
    # after its predecessor, so processing in increasing cost order is a valid topological order
    # over the shortest-path tree.
    order = reachable[np.argsort(dist[reachable], kind="stable")]
    for node in order:
        p = pred[node]
        if p == _NO_PREDECESSOR:
            out[node] = 0.0
            continue
        edge = time_t[p, node]
        prev = out[p]
        out[node] = prev + edge if np.isfinite(prev) else np.inf

    if cutoff_s is not None:
        out[out > float(cutoff_s)] = np.inf
    return out
