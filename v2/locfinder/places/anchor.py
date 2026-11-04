"""Make a resolved anchor usable: snap it to the network, prove it can actually be *reached*, and
nudge it only as far as is defensible. Phase 1 stage S2.2.

Resolving "RDU Terminal 2" to the right entity is not enough. In the Phase 0 spot check, snapping
that anchor found a node 4 m away on a four-node `highway=service` stub, and **three of twelve
journeys came back unreachable** while Valhalla and OSRM both routed them fine. The anchor was not
unreachable; our snap target was. Every way out of the stub was `access=no`, so the access filter
had correctly removed them and left an island.

`components.largest_component` was the Phase 0 response, and its own docstring records why it is not
the answer:

> It uses **weak** connectivity, which ignores edge direction, so a retained one-way branch can
> still fail origin-to-destination reachability. [...] **Directed reachability to the actual
> destination set is the real test.**

This module is that test. Two things make it more than a connectivity check:

**Direction matters, and it is the one most easily got backwards.** Under arrival semantics the
anchor is a *destination*. The question is whether travellers elsewhere can reach **it** — a
directed path `core -> anchor`. Whether the anchor can reach the core is a different question with a
different answer on a one-way street, and testing the wrong one accepts a node nobody can drive to.

**A nudge that respects only distance can cross a fence** — but a barrier must *rank* candidates,
not veto them. The nearest routable node may be on the far side of a wall, so the displacement has
to be checked against barrier geometry rather than trusted because it is short. `barriers` therefore
has no default and the result records whether it was supplied, because a nudge validated on distance
alone is not validated.

The first version of this module *vetoed* any candidate whose straight segment crossed a barrier,
and the real payload showed immediately why that is wrong: at RDU Terminal 2, **all six** candidate
nodes within 150 m are reachable from the core and **every one is cut off by the airport perimeter
`barrier=fence`**, so the anchor came back unusable. The straight segment is a crude proxy for the
real approach, which loops round through the terminal access road; at any fenced site — an airport,
a campus, a hospital, a gated development — a veto produces a false negative.

So the rule is: **prefer a candidate that crosses nothing; fall back to the nearest core-reachable
one and record that its approach crosses a barrier.** That keeps the intent — do not hop the fence
when a node on your own side exists — without making fenced sites unusable, and `crossed_barrier`
carries the caveat to whoever displays the adjustment.

The same bounded, direction-aware, barrier-aware snapping is what category entrances and transit
stops need (S6.3, S6.4), which is why it takes an `EdgeIndex` rather than anything anchor-specific.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import scipy.sparse as sp
import shapely
from scipy.sparse.csgraph import breadth_first_order, connected_components

from ..traveltime.snap import EdgeIndex

#: How far an anchor may be moved before the move is worse than the failure it fixes.
DEFAULT_MAX_NUDGE_M = 150.0
#: Barrier values that genuinely separate a place from a road. `kerb` (1,113 ways in the Triangle),
#: `guard_rail` (350), `handrail` and `ditch` are deliberately **excluded** along with gates,
#: bollards and cycle barriers: they are crossable, often mode-dependently, and counting them as
#: walls rejects legitimate approaches. This list is advice for the caller that extracts barriers;
#: this module takes whatever geometry it is given.
SEPARATING_BARRIERS = ("fence", "wall", "retaining_wall", "hedge", "city_wall")


@dataclass(frozen=True)
class CoreReachability:
    """Which nodes the network's core can reach, **directionally**.

    Built from the strongly connected components: the core is the largest one, and a node is a
    usable destination exactly when a directed path runs from the core to it. That is one
    `O(V + E)` precomputation for the whole graph and a constant-time test per anchor, rather than
    a Dijkstra per candidate.
    """

    component: np.ndarray            # node -> strongly connected component id
    core: int                        # the largest component
    reachable_from_core: np.ndarray  # bool per node: can the core reach this node?
    core_size: int

    @classmethod
    def from_csr(cls, csr: sp.csr_matrix) -> "CoreReachability":
        n_comp, comp = connected_components(csr, directed=True, connection="strong")
        sizes = np.bincount(comp, minlength=n_comp)
        core = int(sizes.argmax())
        coo = csr.tocoo()
        a, b = comp[coo.row], comp[coo.col]
        cross = a != b
        if cross.any():
            cond = sp.coo_matrix(
                (np.ones(int(cross.sum()), dtype=np.int8), (a[cross], b[cross])),
                shape=(n_comp, n_comp),
            ).tocsr()
            order = breadth_first_order(cond, core, directed=True, return_predecessors=False)
            seen = np.zeros(n_comp, dtype=bool)
            seen[np.asarray(order, dtype=np.int64)] = True
        else:
            seen = np.zeros(n_comp, dtype=bool)
            seen[core] = True
        return cls(component=comp, core=core, reachable_from_core=seen[comp],
                   core_size=int(sizes[core]))

    @property
    def usable_share(self) -> float:
        return float(self.reachable_from_core.mean())


def node_coordinates(edge_index: EdgeIndex) -> dict[int, tuple[float, float]]:
    """Node index -> (x, y), read back from the geometries the index was built from."""
    out: dict[int, tuple[float, float]] = {}
    for i, g in enumerate(edge_index.geoms):
        out.setdefault(int(edge_index.start_idx[i]), tuple(g.coords[0]))
        out.setdefault(int(edge_index.end_idx[i]), tuple(g.coords[-1]))
    return out


@dataclass(frozen=True)
class AnchorFix:
    """Where the anchor actually ended up, and what had to be done to get there.

    `status` is what a caller must branch on:

    * `ok` — the nearest network node was already a usable destination. Moving a few tens of metres
      from a POI to a road node is ordinary snapping, not a nudge: on the twelve spot-check anchors
      the first version called **all twelve** "nudged" because every one of them moved more than a
      metre, which made the status carry no information;
    * `nudged` — a *nearer* candidate was rejected, and `moved_m` is how far we had to go instead;
    * `unreachable` — network was found but nothing within the cap can be reached from the core;
    * `off_network` — no network at all within the cap.
    """

    status: str
    x: float | None
    y: float | None
    requested_x: float
    requested_y: float
    moved_m: float
    node: int | None
    reason: str
    barriers_checked: bool
    rejected_unreachable: int = 0
    rejected_by_barrier: int = 0
    #: True when every core-reachable candidate was behind a barrier and we took the nearest
    #: anyway. The anchor is usable; its straight-line approach is not the real one.
    crossed_barrier: bool = False

    @property
    def usable(self) -> bool:
        return self.status in ("ok", "nudged")


def _crosses_barrier(ax: float, ay: float, bx: float, by: float, barriers) -> bool:
    seg = shapely.linestrings([[ax, ay], [bx, by]])
    hits = barriers.query(seg)
    if len(hits) == 0:
        return False
    return bool(shapely.intersects(seg, barriers.geometries.take(hits)).any())


def fix_anchor(
    x: float,
    y: float,
    *,
    edge_index: EdgeIndex,
    reach: CoreReachability,
    barriers: shapely.STRtree | None,
    node_xy: dict[int, tuple[float, float]] | None = None,
    max_nudge_m: float = DEFAULT_MAX_NUDGE_M,
) -> AnchorFix:
    """Snap `(x, y)` to the nearest node the core can reach, within `max_nudge_m`.

    `barriers` has no default on purpose: passing `None` is a decision to accept a displacement
    validated on distance alone, and the result says so (`barriers_checked=False`) rather than
    letting a silent omission look like a check that passed.
    """
    node_xy = node_coordinates(edge_index) if node_xy is None else node_xy
    here = shapely.points(x, y)
    # Every edge whose geometry comes within the cap, then that edge's endpoint nodes as candidates.
    near = edge_index.tree.query(shapely.buffer(here, max_nudge_m))
    cands: dict[int, float] = {}
    for i in np.asarray(near, dtype=np.int64):
        for node in (int(edge_index.start_idx[i]), int(edge_index.end_idx[i])):
            nx, ny = node_xy.get(node, (None, None))
            if nx is None:
                continue
            d = float(np.hypot(nx - x, ny - y))
            if d <= max_nudge_m and (node not in cands or d < cands[node]):
                cands[node] = d
    if not cands:
        return AnchorFix(status="off_network", x=None, y=None, requested_x=x, requested_y=y,
                         moved_m=float("inf"), node=None, barriers_checked=barriers is not None,
                         reason=f"no network within {max_nudge_m:.0f} m")

    ordered = sorted(cands.items(), key=lambda kv: kv[1])
    n_unreachable = 0
    usable: list[tuple[int, float, bool]] = []       # (node, distance, crosses a barrier)
    for node, dist in ordered:
        if not bool(reach.reachable_from_core[node]):
            n_unreachable += 1
            continue
        nx, ny = node_xy[node]
        crosses = barriers is not None and _crosses_barrier(x, y, nx, ny, barriers)
        usable.append((node, dist, crosses))

    if not usable:
        return AnchorFix(
            status="unreachable", x=None, y=None, requested_x=x, requested_y=y,
            moved_m=float("inf"), node=None, barriers_checked=barriers is not None,
            rejected_unreachable=n_unreachable,
            reason=(f"{len(ordered)} node(s) within {max_nudge_m:.0f} m, none reachable from the "
                    f"core"))

    clear = [u for u in usable if not u[2]]
    n_barrier = sum(1 for u in usable if u[2])
    if clear:
        node, dist, _ = clear[0]
        crossed = False
        skipped = n_unreachable + sum(1 for u in usable
                                      if u[2] and u[1] < dist)
    else:
        # Every reachable candidate is behind a barrier. The approach is not a straight line, so
        # take the nearest rather than declaring a real place unusable (see the module docstring).
        node, dist, _ = usable[0]
        crossed = True
        skipped = n_unreachable

    nudged = skipped > 0
    if crossed:
        reason = (f"all {n_barrier} reachable candidate(s) within {max_nudge_m:.0f} m are behind a "
                  "barrier; took the nearest, so the straight-line approach is not the real one")
    elif nudged:
        reason = (f"rejected {n_unreachable} unreachable and "
                  f"{skipped - n_unreachable} barrier-crossing candidate(s) nearer than this one")
    else:
        reason = "nearest network node is reachable from the core with no barrier between"
    return AnchorFix(status="nudged" if nudged else "ok", x=node_xy[node][0], y=node_xy[node][1],
                     requested_x=x, requested_y=y, moved_m=dist, node=node, reason=reason,
                     barriers_checked=barriers is not None,
                     rejected_unreachable=n_unreachable, rejected_by_barrier=n_barrier,
                     crossed_barrier=crossed)
