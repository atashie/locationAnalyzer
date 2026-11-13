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

    Requires strictly positive costs, which is what makes increasing-cost order a valid
    topological order over the shortest-path forest. Among equal-cost paths scipy's choice is
    taken as given, so the reported time of a tie is insertion-order dependent; that is
    acceptable here because any tied path is equally preferred, but it means a bit-identical
    result across graph rebuilds is not guaranteed.

    Returns +inf for unreachable nodes. Never returns a penalty-inflated time.

    `arrival_with_selected_destination` returns these same seconds plus *which* destination each
    node's chosen path leads to. This function delegates to it, so there is one search and one
    selection rule rather than two that can drift apart.
    """
    seconds, _selected = arrival_with_selected_destination(
        cost_csr, time_csr, dest_idx=dest_idx, cutoff_s=cutoff_s
    )
    return seconds


def arrival_with_route_flag(
    cost_csr: sp.csr_matrix,
    time_csr: sp.csr_matrix,
    flag_csr: sp.csr_matrix,
    *,
    dest_idx,
    cutoff_s: float | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """`(seconds, selected, flagged)` — arrival seconds, the chosen destination, and whether the
    cost-optimal path from each node uses at least one flagged edge.

    **Step 8 owes this to households.** The owner's 2026-11-10 decision to keep the restricted-walk
    penalty at 120 s was taken on the condition that the gap is **disclosed rather than priced
    away**, and disclosure needs per-cell membership: not "the graph contains restricted edges",
    which is true everywhere, but "the route behind *this* number uses one". The soft-way note
    recorded that as specified and manual — computable one journey at a time by
    `explain_journey.py`, with no aggregation anywhere. This is the aggregation.

    The flag propagates along the same predecessor forest the reported time does, in the same
    increasing-cost sweep, so a node is flagged exactly when its chosen path is. It is therefore
    **not** monotone in anything a caller might expect: a cheaper path may be flagged where a
    dearer one is not, and that is the point — the flag describes the route the selection took.
    """
    seconds, selected, flagged = _arrival_sweep(
        cost_csr, time_csr, flag_csr, dest_idx=dest_idx, cutoff_s=cutoff_s)
    return seconds, selected, flagged


def arrival_with_selected_destination(
    cost_csr: sp.csr_matrix,
    time_csr: sp.csr_matrix,
    *,
    dest_idx,
    cutoff_s: float | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """`(seconds, selected)` — the arrival seconds, and the destination node each path leads to.

    `selected[i]` is the **node index** of the destination whose cost-optimal path node `i` was
    assigned, or **-1** where `seconds[i]` is not finite. It is a node id drawn from `dest_idx`,
    never a position within it.

    This exists because the identity of the chosen destination was already being computed and
    thrown away. `scipy`'s `min_only=True` search returns a `sources` array alongside the
    distances and predecessors, and the two-weight variant discarded it as `_sources`. Every
    published layer therefore knew which grocery it had routed each household to and kept no
    record of it, which is what made the owner's walked audit unable to check our number: the
    sheet could say "ten minutes" but not "ten minutes to where".

    A destination node can carry several places (550 grocery places snap to 510 nodes on the
    Triangle walk graph), so a node id identifies the journey, not a single shop. Resolving it to
    a shop is the caller's job and is one-to-many.

    `selected` is masked to -1 wherever the returned seconds are infinite — including by
    `cutoff_s`, so a node cut by the horizon reports no destination rather than one it cannot
    reach in the advertised budget.
    """
    seconds, selected, _flagged = _arrival_sweep(
        cost_csr, time_csr, None, dest_idx=dest_idx, cutoff_s=cutoff_s)
    return seconds, selected


def _arrival_sweep(cost_csr, time_csr, flag_csr, *, dest_idx, cutoff_s):
    """One search and one sweep, carrying time and optionally a route flag.

    Extracted when step 8 needed a third quantity on the same forest. Two sweeps over the same
    predecessors would be two chances to disagree about which path was chosen, which is the defect
    pass-6 M4 found between the cost and time matrices.
    """
    if cost_csr.shape != time_csr.shape:
        raise ValueError(f"cost {cost_csr.shape} and time {time_csr.shape} matrices must match")
    # Same shape is not enough: the two must describe the SAME edges, or a reported time would be
    # read from an edge the search never used (Codex pass-6 M4).
    if cost_csr.nnz != time_csr.nnz or not (
        np.array_equal(cost_csr.indptr, time_csr.indptr)
        and np.array_equal(cost_csr.indices, time_csr.indices)
    ):
        raise ValueError(
            "cost and time matrices must share sparsity; build them with graph_to_cost_time_csr")
    if flag_csr is not None and flag_csr.shape != cost_csr.shape:
        raise ValueError(f"flag {flag_csr.shape} must match cost {cost_csr.shape}")
    if cost_csr.nnz and float(cost_csr.data.min()) <= 0.0:
        raise ValueError("costs must be strictly positive: the increasing-cost sweep relies on it")
    dest = np.asarray(list(dest_idx), dtype=np.int64)
    n = cost_csr.shape[0]
    empty_flags = np.zeros(n, dtype=bool)
    if dest.size == 0:
        return np.full(n, np.inf), np.full(n, -1, dtype=np.int64), empty_flags

    cost_t = cost_csr.transpose().tocsr()
    time_t = time_csr.transpose().tocsr()
    flag_t = None if flag_csr is None else flag_csr.transpose().tocsr()
    dist, pred, sources = dijkstra(
        cost_t, directed=True, indices=dest, min_only=True, return_predecessors=True
    )
    dist = np.asarray(dist, dtype=np.float64)
    pred = np.asarray(pred, dtype=np.int64)
    # scipy returns the source as a NODE id (verified against a two-source fixture, not assumed),
    # with -9999 for unreached. Widen to int64 before masking so the sentinel cannot collide with
    # a legitimate index on a graph large enough to matter.
    selected = np.asarray(sources, dtype=np.int64)

    out = np.full(n, np.inf)
    flagged = np.zeros(n, dtype=bool)
    reachable = np.flatnonzero(np.isfinite(dist))
    if reachable.size == 0:
        return out, np.full(n, -1, dtype=np.int64), flagged
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
        if flag_t is not None:
            flagged[node] = bool(flagged[p]) or bool(flag_t[p, node])

    if cutoff_s is not None:
        out[out > float(cutoff_s)] = np.inf
    # The destination record must agree with the seconds it explains. A node can be reachable on
    # cost yet have no finite reported time -- the cutoff is applied to time, and the sweep leaves
    # +inf where a predecessor's time was unavailable -- so mask on `out`, not on `dist`.
    selected = np.where(np.isfinite(out), selected, -1)
    # A node with no reported time discloses no route, so its flag is not an assertion about one.
    flagged = flagged & np.isfinite(out)
    return out, selected, flagged
