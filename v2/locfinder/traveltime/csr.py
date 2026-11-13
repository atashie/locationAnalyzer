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


def graph_to_cost_time_flag_csr(
    G: nx.MultiDiGraph, *, cost: str = "cost", time: str = "travel_time",
    flag: str = "access_restricted",
) -> tuple[sp.csr_matrix, sp.csr_matrix, sp.csr_matrix, dict]:
    """`(cost_csr, time_csr, flag_csr, index)` — as `graph_to_cost_time_csr`, plus a 0/1 matrix
    carrying the **selected** edge's flag.

    Step 8 owes households disclosure when an estimate's route depends on a restricted way, and
    that cannot be read off the edges alone: a cell's answer depends on the edges its own
    cost-optimal path uses. This carries the flag of the edge the selection actually took.

    **For parallel edges the flag follows the cost-minimal one**, exactly as the reported time
    does. "Any parallel edge is restricted" would be a different and wrong claim — the journey
    uses one of them, and which one is decided by cost.

    Restricted edges are stored as `1.0`, so they are never dropped as structural zeros; an
    unrestricted or absent entry reads as `0.0`, which is the same answer either way.
    """
    cost_csr, time_csr, index, best = _cost_time_core(G, cost=cost, time=time, flag=flag)
    n = len(index)
    if not best:
        empty = sp.csr_matrix((n, n), dtype=np.float64)
        return cost_csr, time_csr, empty, index
    rows, cols = zip(*best.keys())
    flags = [1.0 if v[2] else 0.0 for v in best.values()]
    flag_csr = sp.coo_matrix((flags, (rows, cols)), shape=(n, n), dtype=np.float64).tocsr()
    return cost_csr, time_csr, flag_csr, index


def graph_to_cost_time_csr(
    G: nx.MultiDiGraph, *, cost: str = "cost", time: str = "travel_time"
) -> tuple[sp.csr_matrix, sp.csr_matrix, dict]:
    """Return (cost_csr, time_csr, index) over identical sparsity.

    For parallel edges the **cost**-minimal one wins and its own time is carried, so the reported
    time always belongs to the path actually chosen rather than to a cheaper-but-unused parallel
    edge. Edges missing `cost` fall back to their time, which keeps unpenalised graphs working.
    """
    cost_csr, time_csr, index, _best = _cost_time_core(G, cost=cost, time=time, flag=None)
    return cost_csr, time_csr, index


def _cost_time_core(G, *, cost: str, time: str, flag: str | None):
    """The shared selection: per node pair, the cost-minimal edge and what it carries."""
    nodes = list(G.nodes())
    index = {n: i for i, n in enumerate(nodes)}
    best: dict[tuple[int, int], tuple[float, float, bool]] = {}
    for u, v, data in G.edges(data=True):
        t = _validate(u, v, time, float(data[time]))
        c = float(data.get(cost, t))
        if c <= 0 or not np.isfinite(c):
            raise ValueError(f"edge {u}->{v} has non-positive or non-finite {cost}={c}")
        k = (index[u], index[v])
        prev = best.get(k)
        if prev is None or c < prev[0]:
            best[k] = (c, t, bool(data.get(flag)) if flag else False)
    n = len(nodes)
    if not best:
        empty = sp.csr_matrix((n, n), dtype=np.float64)
        return empty, empty.copy(), index, best
    rows, cols = zip(*best.keys())
    costs = [v[0] for v in best.values()]
    times = [v[1] for v in best.values()]
    cost_csr = sp.coo_matrix((costs, (rows, cols)), shape=(n, n), dtype=np.float64).tocsr()
    time_csr = sp.coo_matrix((times, (rows, cols)), shape=(n, n), dtype=np.float64).tocsr()
    return cost_csr, time_csr, index, best
