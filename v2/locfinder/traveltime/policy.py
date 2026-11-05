"""Access policy as a language over edge classes, and shortest paths that respect it.

`access.py` models restricted roads by *penalising* their selection: a restricted edge costs extra
to choose and takes its real time to travel, which is what mainstream engines do and what makes a
home on a private drive reachable at all. That answers "what route would a router pick"; it does not
answer "is this route one the traveller may lawfully take", because a penalty discourages
through-routing over private land without forbidding it.

This module answers the second question for a stated policy.

## The policy

A lawful journey may leave along a restricted road it is entitled to use, must travel the middle of
its journey on open roads, and may enter a restricted road at the far end. Writing **R** for
restricted and **O** for open, the lawful journeys are exactly

        R* O* R*

with any of the three blocks empty.

**Why a chain and not a single edge.** The first attempt at this exempted the journey's first and
last restricted *edge*. That makes the verdict depend on how a driveway happens to be divided into
OSM ways: split one driveway in two and the second half is no longer "first", so the same journey
becomes through traffic (Codex pass-13 H3). A chain has no such dependence, and
`spikes/s2_access_lawfulness_v2.py --split-check` subdivides every restricted edge to demonstrate
it.

**What this does not establish, stated carefully because I got it wrong twice.**

This module decides **membership in an edge-class language**. That is all it decides.

It does *not* establish "this journey is not through-traffic over private land" — which is what I
claimed next, and Codex pass-14 H1 gives the counterexample: an origin in estate A and a destination
in estate C, joined by a continuous restricted road through unrelated estate B, is `RRR` and is
**accepted**, while B is plainly being used for through-traffic. The automaton sees edge *classes*;
it cannot see whose access chain an edge belongs to, so it cannot tell a driveway from a private
road belonging to someone else.

Nor does rejection establish unlawfulness: `ORO` can perfectly well describe an entitled traveller
using a restricted connection they are allowed to use. `access=private` records restricted *public*
access, not who is entitled.

And the tempting repair does not work either: **requiring a non-empty open middle would wrongly
reject journeys that legitimately stay inside one private area** — a resident walking from one side
of an estate to a shop on the other.

So a result from here supports statements of the form "N nodes have no journey in `R* O* R*`", and
no stronger. A claim about lawfulness needs access-area and entitlement data, which OSM does not
carry. That is a limit of the available data, not a task to schedule.

## Recognising it

`R* O* R*` is a three-state automaton. Shortest paths that respect it are shortest paths on the
**product** of the graph and the automaton: a search state is `(node, automaton state)`.

Arrival surfaces search backwards from the destinations, so the automaton has to run backwards too.
The language is its own reverse — reading `R* O* R*` right to left gives `R* O* R*` — so the same
three states serve, with the two chains exchanged. Backwards from a destination:

| state | the forward path from here to a destination is... | may traverse |
|---|---|---|
| 0 | all restricted — still inside the destination's own access chain | R (stay), O (go to 1) |
| 1 | `O* R*` — an open middle, then the destination's chain | O (stay), R (go to 2) |
| 2 | `R* O* R*` — the origin's own chain, then all of the above | R only |

State 2 has no open transition: an open edge after the origin's chain has begun would mean a second
open block, which the language does not contain.

**Costs are times.** A forbidding policy has nothing to discourage, so there is no penalty to apply,
and using `access.py`'s penalised costs here would charge for a traversal the policy has already
decided is permitted (Codex pass-13 H2).
"""
from __future__ import annotations

import networkx as nx
import numpy as np
import scipy.sparse as sp
from scipy.sparse.csgraph import dijkstra

from .access import RESTRICTED, classify_access

#: Number of automaton states.
N_STATES = 3

#: `(reverse state, edge is restricted) -> next state`, or `None` where the policy forbids it.
TRANSITIONS: dict[tuple[int, bool], int | None] = {
    (0, True): 0,    # still in the destination's chain
    (0, False): 1,   # the open middle begins
    (1, False): 1,   # still in the open middle
    (1, True): 2,    # the origin's chain begins
    (2, True): 2,    # still in the origin's chain
    (2, False): None,  # an open edge here would start a second open block
}


def class_separated_times(G: nx.MultiDiGraph, index: dict, *, mode: str) -> dict[bool, sp.csr_matrix]:
    """Minimum traversal time per directed pair, kept **separately by access class**.

    Two matrices over one index: `False` for open edges, `True` for restricted ones.

    This has to happen on the multigraph, and that is the whole point. `csr.graph_to_cost_time_csr`
    keeps one edge per directed pair — the cost-minimal one — so wherever a fast restricted edge beat
    a slower public parallel edge, the public edge is absent from the matrix entirely. Filtering
    *that* by class then deletes the pair, and a policy counterfactual reports no route where a
    perfectly lawful public one exists (Codex pass-13 H4). Separating the classes before any collapse
    makes the alternative available to whichever policy wants it.

    `forbidden` edges are not represented: they are removed from the graph upstream and are not
    lawful under any policy.
    """
    n = len(index)
    best: dict[bool, dict[tuple[int, int], float]] = {False: {}, True: {}}
    for u, v, data in G.edges(data=True):
        t = float(data["travel_time"])
        if not np.isfinite(t) or t <= 0.0:
            raise ValueError(f"edge {u}->{v} has travel_time={t}; times must be positive and finite")
        bucket = best[classify_access(data, mode=mode) == RESTRICTED]
        k = (index[u], index[v])
        if k not in bucket or t < bucket[k]:
            bucket[k] = t
    out: dict[bool, sp.csr_matrix] = {}
    for restricted, d in best.items():
        if d:
            rows, cols = zip(*d.keys())
            out[restricted] = sp.coo_matrix((list(d.values()), (rows, cols)),
                                            shape=(n, n), dtype=np.float64).tocsr()
        else:
            out[restricted] = sp.csr_matrix((n, n), dtype=np.float64)
    return out


def product_graph(by_class: dict[bool, sp.csr_matrix]) -> sp.csr_matrix:
    """The transposed graph x automaton product, ready for a multi-source arrival search.

    A forward edge `u -> v` is traversed from `v` towards `u` by an arrival search, so the product
    edge runs `(v, state) -> (u, TRANSITIONS[state, class])`.
    """
    n = next(iter(by_class.values())).shape[0]
    rows: list[np.ndarray] = []
    cols: list[np.ndarray] = []
    vals: list[np.ndarray] = []
    for restricted, csr in by_class.items():
        if csr.nnz == 0:
            continue
        coo = csr.tocoo()
        for state in range(N_STATES):
            nxt = TRANSITIONS[(state, restricted)]
            if nxt is None:
                continue
            rows.append(state * n + coo.col)      # at v, in `state`
            cols.append(nxt * n + coo.row)        # arriving at u, in `nxt`
            vals.append(coo.data)
    if not vals:
        return sp.csr_matrix((N_STATES * n, N_STATES * n), dtype=np.float64)
    return sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
                         shape=(N_STATES * n, N_STATES * n), dtype=np.float64).tocsr()


def lawful_arrival(by_class: dict[bool, sp.csr_matrix], *, dest_idx
                   ) -> tuple[np.ndarray, np.ndarray]:
    """Arrival times under `R* O* R*`. Returns `(seconds, state)`, both length *n*.

    `seconds` is `+inf` where no journey in the language exists. `state` is the automaton state the
    best journey was found in, and is meaningless where the time is infinite.

    Destinations start in **state 0**, because nothing has been travelled yet and the destination's
    own access chain is still available.
    """
    n = next(iter(by_class.values())).shape[0]
    dest = np.asarray(list(dest_idx), dtype=np.int64)
    if dest.size == 0:
        return np.full(n, np.inf), np.zeros(n, dtype=np.int64)
    if dest.min() < 0 or dest.max() >= n:
        raise ValueError("dest_idx out of range for this index")
    dist = np.asarray(
        dijkstra(product_graph(by_class), directed=True, indices=dest, min_only=True),
        dtype=np.float64)
    per_state = dist.reshape(N_STATES, n)
    return per_state.min(axis=0), per_state.argmin(axis=0)


def min_time(by_class: dict[bool, sp.csr_matrix]) -> sp.csr_matrix:
    """Elementwise minimum traversal time per directed pair, ignoring class.

    The **baseline** for a policy counterfactual, and it has to be built rather than borrowed.
    `arrival_seconds_two_weight` reports the time along the *cost*-selected path, which is an upper
    bound on the minimum time and not the minimum itself (pass-8 H2). Comparing a time-minimising
    lawful search against it mixes the policy's effect with that bound, and the mixture is large
    enough to make the lawful answer look *faster* than the unrestricted one — which a subset can
    never be. The invariant in `tests/test_policy.py` caught exactly that.

    So: policy effects are measured time-minimum against time-minimum, and the shipped surface is
    reported beside them as what the product says, never as the baseline.

    `sp.csr_matrix.minimum` is not usable here: it treats a missing entry as a stored zero, and zero
    wins a minimum.
    """
    n = next(iter(by_class.values())).shape[0]
    coos = [c.tocoo() for c in by_class.values() if c.nnz]
    if not coos:
        return sp.csr_matrix((n, n), dtype=np.float64)
    rows = np.concatenate([c.row.astype(np.int64) for c in coos])
    cols = np.concatenate([c.col.astype(np.int64) for c in coos])
    data = np.concatenate([c.data for c in coos])
    lin = rows * n + cols
    order = np.argsort(lin, kind="stable")
    lin, data = lin[order], data[order]
    uniq, start = np.unique(lin, return_index=True)
    best = np.minimum.reduceat(data, start)
    return sp.coo_matrix((best, (uniq // n, uniq % n)), shape=(n, n),
                         dtype=np.float64).tocsr()


def unrestricted_arrival(by_class: dict[bool, sp.csr_matrix], *, dest_idx) -> np.ndarray:
    """Minimum-**time** arrival with no policy at all: the baseline `lawful_arrival` is measured
    against, so that the only difference between them is the policy."""
    n = next(iter(by_class.values())).shape[0]
    dest = np.asarray(list(dest_idx), dtype=np.int64)
    if dest.size == 0:
        return np.full(n, np.inf)
    return np.asarray(
        dijkstra(min_time(by_class).transpose().tocsr(), directed=True, indices=dest,
                 min_only=True), dtype=np.float64)


def accepts(classes) -> bool:
    """Is this sequence of edge classes a lawful journey? `True` for restricted, `False` for open.

    The forward automaton, for testing and for explaining a single path. Kept separate from the
    search so the search's reversed machine can be checked against a direct reading of the language.
    """
    state = 0           # 0 = origin chain, 1 = open middle, 2 = destination chain
    for restricted in classes:
        if state == 0:
            state = 0 if restricted else 1
        elif state == 1:
            state = 2 if restricted else 1
        else:
            if not restricted:
                return False
    return True
