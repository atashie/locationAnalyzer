"""Toy graphs and an **exhaustive** oracle for the comparator's two objectives.

This module exists to give T4's conformance suite a second route to every expected answer, and it is
written to be independent of the reference comparator (T3) in a way that can be *checked* rather than
asserted:

* it enumerates **every** journey — every attachment candidate, every entry and exit choice, every
  simple path — and takes the extremum, so it contains no shortest-path algorithm, no spatial index,
  no CSR and no "objective view". Design §2.3's hybrid defect (a time-selected index paired with
  cost-selected nodes, giving 10.5 or 6 where the answers are 1.5 and 15) is **unrepresentable**
  here, because every candidate carries its own `(time, cost)` pair and the two are never selected
  separately;
* it imports nothing from `locfinder.traveltime`. The access speed is restated as a literal and
  pinned to `access_speed_mps("walk")` by a test, so a change there is a test failure rather than a
  silent change of the oracle;
* it is exponential in graph size and says so. The cases are hand-sized (≤ 8 edges) on purpose.

**The oracle is the second authority, not the first.** Each conformance case carries a hand-derived
expected value with its arithmetic shown, taken where possible from a review pass's own worked
counterexample. The suite requires hand and oracle to **agree**; where they disagree the case is a
finding, which is the whole point of having two routes. Pass 17's warning is the reason for this
structure: *"a program can faithfully implement each defective instruction"*, and fixtures derived
from the same mistaken premise enforce the defect rather than catching it. One oracle derived from
one reading of the design would be exactly that.

## Two places where §2.2 is read, and the reading is recorded

The first is **not** a micro-ambiguity. Pass 19's F1 established that, and the design has to settle
it before a normative comparator can exist:

1. **Which positions are candidates on a single geometry.** §2.2's text alternates between retaining
   geometric *minimisers* and retaining "every attachment whose distance is within 0.01 m of the
   minimum". Those are different sets, and the second is a **continuum**, even on one straight edge.
   Pass 19's counterexample: a directed edge `(0,0) -> (100,0)` of time 100,000 s, origin `(0,1)`,
   destination `(100,0)`. The nearest projection `(0,0)` is 1 m away and gives
   `1/1.26 + 100000 = 100000.7936507940 s`. But `(0.1417744688, 0)` is 1.01 m away — inside the
   literal tolerance band — and gives `1.01/1.26 + 0.9985822553 x 100000 = 99859.0271185140 s`. The
   gap is **141.7665322800 s**, and at a 99,900 s threshold the two readings are FAIL and PASS.
   There is no bound on that gap obtained by dividing the spatial tolerance by the access speed.

   **Design revision 6 settled this**, choosing the reading this oracle had adopted: a candidate is
   the nearest position on a polyline **segment**, the set is those segment positions within
   `ATTACH_TIE_M` of the global minimum, and duplicates are removed by *(canonical directed-edge
   identity, position rounded to `ROUND_DP` in metres)*. It was one of three readings — exact
   per-geometry minima, per-segment minima, the whole tolerance sublevel set — and choosing it was
   an amendment with a §13 row, not an interpretation this module was entitled to make. The cases
   marked `reading="per-segment minima"` are the ones a different choice would have invalidated.

   Related, and separately true: the 0.01 m rule **relocates** the discontinuity rather than
   removing it. Two disconnected roads of 100 s and 1000 s with origin residuals 1 m and 1.009 m
   give `100 + 1.009/1.26 = 100.8007936510 s`; moving the second to 1.011 m excludes it and leaves
   `1000 + 1/1.26 = 1000.7936507940 s` — an **899.9928571430 s** jump across 2 mm, and PASS to FAIL
   at ten minutes. Keeping every candidate makes the answer well defined once the candidate universe
   is specified; it does not make the answer continuous in the geometry, and §2.2 may not be defended
   as though it did.

2. **Order of the tie window and the cap.** The window is taken around the global minimum **first**,
   and the distance cap applied **after**, so each retained candidate is independently inside the
   cap. A nearest origin candidate at 199.995 m does **not** authorise a second at 200.004 m merely
   because it is inside the geometric tie band. Pass 19 asked for this explicitly and it is tested.

## Why simple paths suffice

Every weight here is non-negative, so a journey whose node sequence repeats a node contains a
non-negative cycle that can be excised without changing its endpoints or its partial-edge terms. The
excised journey is no worse. So restricting the enumeration to node-simple paths cannot miss an
optimum, and the enumeration is finite.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, field

#: Design §2: the walk access speed. Pinned to `speeds.access_speed_mps("walk")` by a test rather
#: than imported, so that this oracle does not move when the production constant does.
ACCESS_SPEED_MPS = 1.26

#: Design §2.2.
ATTACH_TIE_M = 0.01

#: Design §2: the origin access cap and the destination eligibility cap. Different quantities.
MAX_ACCESS_M = 200.0
POI_SNAP_MAX_M = 300.0

#: Design §2.4: "Rounding precision is 2 dp on metres everywhere, stated once."
ROUND_DP = 2


# ----------------------------------------------------------------------------- geometry


def _segment_nearest(px: float, py: float, ax: float, ay: float,
                     bx: float, by: float) -> tuple[float, float]:
    """`(distance, t)` for the nearest point on segment `a->b` to `p`, with `t` clamped to [0, 1].

    A zero-length segment returns `t = 0.0` and the distance to the shared endpoint, rather than
    dividing by zero.
    """
    dx, dy = bx - ax, by - ay
    denom = dx * dx + dy * dy
    t = 0.0 if denom == 0.0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / denom))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy)), t


# ----------------------------------------------------------------------------- the graph


@dataclass(frozen=True)
class ToyEdge:
    """One directed edge, with time and cost carried **separately** at every stage.

    `penalty` is separate from `cost_base` so that design §2.2's apportionment rule is testable
    against the rejected alternative. `access.py` adds a fixed 120 s per restricted walking edge to
    cost, so on a 1% traversal apportionment charges `0.01 x 121 = 1.21` while an entry charge would
    charge `0.01 x 1 + 120 = 120.01`, and against a 5 s open bypass the two select different routes.
    An implementation that keeps only the summed cost cannot distinguish them.

    `oneway` models the state **after** walk symmetrisation: a bidirectional pedestrian edge is
    `oneway=False`. Design §2.2 — bike and drive do not inherit the pedestrian reverse.
    """

    u: int
    v: int
    geometry: tuple[tuple[float, float], ...]
    time_s: float
    cost_base: float
    penalty: float = 0.0
    osmid: tuple[int, ...] = ()
    oneway: bool = False

    def __post_init__(self) -> None:
        if len(self.geometry) < 2:
            raise ValueError("an edge geometry needs at least two coordinates")
        if self.time_s < 0 or self.cost_base < 0 or self.penalty < 0:
            raise ValueError("times, costs and penalties are non-negative")

    @property
    def total_cost(self) -> float:
        """The selection weight. Penalties are **inside** cost, per `access.py`."""
        return self.cost_base + self.penalty

    @property
    def length_m(self) -> float:
        return sum(math.hypot(b[0] - a[0], b[1] - a[1])
                   for a, b in itertools.pairwise(self.geometry))

    @property
    def geometry_key(self) -> tuple[tuple[float, float], ...]:
        """Design §2.4: canonicalised so a reversed traversal of the same geometry maps to the
        **same physical road**. The directed identity below then separates the two directions by
        their endpoints, which is what `_physical_key` and `_canonical_geometry_key` disagreed about.
        """
        fwd = tuple((round(x, ROUND_DP), round(y, ROUND_DP)) for x, y in self.geometry)
        return min(fwd, fwd[::-1])

    @property
    def orientation(self) -> int:
        """0 if this traversal's rounded geometry *is* the canonical key, 1 if it is the reversal.

        Design §2.4 revision 7. For an open edge `(u, v)` the endpoints already separate the two
        directions, so this adds nothing. For a **closed** edge `u == v` — a ring, a loop — swapping
        the endpoints does nothing and canonicalising the geometry against reversal removes the only
        remaining direction information, so the two traversals had **identical** identities.

        Pass-20 F3: two one-way self-loops around the square `(0,0),(100,0),(100,100),(0,100),(0,0)`
        with the same `osmid`, origin `(10,0)`, destination `(0,10)`. The correct journey is
        **200 s** the reverse way round. With the forward loop first, attachment dedup discarded the
        reverse and the answer was **3,800 s**; reversing the input order gave 200 s. A PASS/FAIL
        flip at ten minutes decided entirely by insertion order.
        """
        fwd = tuple((round(x, ROUND_DP), round(y, ROUND_DP)) for x, y in self.geometry)
        return 0 if fwd == self.geometry_key else 1

    @property
    def identity(self) -> tuple:
        """Design §2.4's canonical **directed**-edge identity: start node, end node, canonical
        geometry key, traversal orientation, osmid normalised to a sorted tuple, length at 2 dp.

        The orientation field is revision 7's addition and exists only for closed edges; see
        `orientation`. It is placed before `osmid` so that the comparison order remains
        structural-then-attributive.
        """
        return (self.u, self.v, self.geometry_key, self.orientation,
                tuple(sorted(self.osmid)), round(self.length_m, ROUND_DP))

    def permits(self, *, forward: bool) -> bool:
        return True if forward else not self.oneway


@dataclass(frozen=True)
class ToyGraph:
    edges: tuple[ToyEdge, ...]

    def __post_init__(self) -> None:
        coords: dict[int, tuple[float, float]] = {}
        for e in self.edges:
            for node, xy in ((e.u, e.geometry[0]), (e.v, e.geometry[-1])):
                prev = coords.setdefault(node, xy)
                if prev != xy:
                    raise ValueError(f"node {node} has two coordinates: {prev} and {xy}")

    @property
    def nodes(self) -> tuple[int, ...]:
        return tuple(sorted({n for e in self.edges for n in (e.u, e.v)}))


# ----------------------------------------------------------------------------- attachment


@dataclass(frozen=True)
class Attachment:
    """One retained attachment candidate. Design §2.2 keeps **every** geometric minimiser, so this
    is one of a set and the set is part of what determines the answer.

    `arclength_m` is the identifying coordinate, not `position`. An XY point is not an *occurrence*
    along a polyline: a self-crossing road passes the same place twice with different remaining
    route, and merging the two loses that route (pass-20 F2).
    """

    edge: int           # index into ToyGraph.edges
    fraction: float     # along the whole polyline, by length, from the `u` end
    arclength_m: float  # fraction x length, the occurrence's identifying coordinate
    residual_m: float   # straight-line from the coordinate to the attached position
    position: tuple[float, float]


@dataclass(frozen=True)
class NearestOnGraph:
    """What `attachments` found, including what it then discarded at the cap.

    `global_min_m` exists because an empty candidate set is a **status with a bound**, not an
    absence. Pass-20: at a global minimum of 200.5 m there is no in-cap attachment, and the sound
    `OFF_NETWORK` bound is `200.5 / 1.40 = 143.2142857143 s` — computed from the *measured* nearest
    distance, never from the 200 m cap (which would give a different number) and never invented when
    the graph has no edges at all (where there is no nearest distance and the absence must be
    reported as such). 840.5 m gives 600.3571 s and proves failure at ten minutes; 200 m does not.
    """

    candidates: tuple[Attachment, ...]
    global_min_m: float | None      # None only when the graph has no edge geometry at all


def nearest_on_graph(graph: ToyGraph, point: tuple[float, float], *,
                     cap_m: float) -> NearestOnGraph:
    """Design §2.2's candidate set, plus the measured nearest distance for the off-network bound.

    The candidate set is: the nearest position on **each polyline segment**; those within
    `ATTACH_TIE_M` of the global minimum; deduplicated by **(edge record, along-edge arclength
    rounded to `ROUND_DP` metres)**; then filtered to those independently within `cap_m`.

    **Two things in that key are load-bearing, and both were wrong in revision 6.**

    *Arclength, not position.* Pass-20 F2: one one-way edge with geometry
    `(-100,0),(0,0),(0,100),(100,100),(100,0),(0,0),(0,-100)` — length 600 m, time 1,000 s — has two
    zero-distance occurrences of the origin `(0,0)`, at arclengths **100 m and 500 m**. Keeping both
    gives `100/600 x 1000` = **166.6666666667 s**; a rounded-XY key merges them, keeps one, and
    returns **833.3333333333 s**. PASS becomes FAIL at ten minutes, from merging two points that are
    the same place and not the same decision.

    *Per edge record, not per canonical identity.* Pass-20 F4: identity excludes time and cost, so
    two parallel `0 → 1` edges with the same `osmid` and geometry but weights 2000/2000 and 2/2 share
    an identity. Keying on it discarded one by input order **before either objective could compete**:
    with the slow edge first the answer was **802 s**, with the fast edge first **1.2 s**. Design §2.4
    freezes identity and grouping *separately from* ranking precisely so that grouping cannot decide
    a ranking question.

    The representative of a merged bucket is the candidate with the **smallest residual**, then the
    smallest exact arclength. Taking the earliest instead interacts with the cap: on
    `(-100,-.004),(100,-.004),(100,.004),(-100,.004)` from `(0,200)` the two horizontal projections
    are **200.004 m and 199.996 m**, and keeping the first then dropping it at the 200 m cap returned
    **zero** candidates where one is attached.
    """
    px, py = point
    raw: list[Attachment] = []
    for i, e in enumerate(graph.edges):
        total = e.length_m
        run = 0.0
        for a, b in itertools.pairwise(e.geometry):
            seg = math.hypot(b[0] - a[0], b[1] - a[1])
            d, t = _segment_nearest(px, py, a[0], a[1], b[0], b[1])
            along = run + t * seg
            raw.append(Attachment(
                edge=i,
                fraction=0.0 if total == 0.0 else along / total,
                arclength_m=along,
                residual_m=d,
                position=(a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])),
            ))
            run += seg
    if not raw:
        return NearestOnGraph(candidates=(), global_min_m=None)

    best = min(a.residual_m for a in raw)
    window = [a for a in raw if a.residual_m <= best + ATTACH_TIE_M]
    buckets: dict[tuple[int, float], Attachment] = {}
    for a in window:
        key = (a.edge, round(a.arclength_m, ROUND_DP))
        current = buckets.get(key)
        if current is None or (a.residual_m, a.arclength_m) < (current.residual_m,
                                                               current.arclength_m):
            buckets[key] = a
    kept = sorted(buckets.values(), key=lambda a: (a.edge, a.arclength_m))
    return NearestOnGraph(
        candidates=tuple(a for a in kept if a.residual_m <= cap_m),
        global_min_m=best,
    )


def attachments(graph: ToyGraph, point: tuple[float, float], *, cap_m: float) -> tuple[Attachment, ...]:
    """The candidate set alone. An empty result is a **status**, not a missing value — use
    `nearest_on_graph` when the off-network bound is needed, since the cap discards the distance the
    bound is computed from."""
    return nearest_on_graph(graph, point, cap_m=cap_m).candidates


# ----------------------------------------------------------------------------- enumeration


@dataclass(frozen=True)
class Journey:
    """One complete enumerated journey, with time and cost kept as a pair throughout.

    `route` is the sequence of design §2.4 canonical directed-edge identities, which is the design's
    route identity, and is what breaks a cost tie after travel time.
    """

    time_s: float
    cost: float
    destination: int
    destination_id: str = ""
    route: tuple = field(compare=False, default=())

    @property
    def rank_key(self) -> tuple:
        """Design §2.4's ranking, lifted to a whole journey: smallest travel time, then smallest
        **destination id**, then the smallest route-identity sequence compared element-wise.

        Pass-20 F9 found two defects in the first version, which keyed on
        `tuple(repr(r) for r in route)`:

        * **`repr` is the wrong order.** Route identities beginning with node pairs `(2, 3)` and
          `(10, 11)` compare `2 < 10` structurally and `'10' < '2'` as text, so the string key
          selected the wrong one. Element-wise comparison on the tuples themselves is well defined
          here — every position holds a like-typed field — and is what the design means.
        * **destination identity was missing, and route order came first.** Revision 6 added the
          destination `id` as key 5 *before* the route sequence, exactly because two ids at one
          coordinate reached identically tie on every edge key. No reported number moves, but the
          manifest would name different destinations on two runs of the same code.
        """
        return (self.time_s, self.destination_id, self.route)


def directed_identity(edge: ToyEdge, *, forward: bool) -> tuple:
    """`edge.identity` for a forward traversal, and the same shape with the endpoints and the
    orientation flipped for a reverse one."""
    if forward:
        return edge.identity
    return (edge.v, edge.u, edge.geometry_key, 1 - edge.orientation,
            tuple(sorted(edge.osmid)), round(edge.length_m, ROUND_DP))


def _simple_paths(graph: ToyGraph, start: int, goal: int):
    """Every node-simple directed path `start -> goal`, as `(time terms, cost terms, identities)`.

    **The terms are returned, not their running sums**, so the caller can total them with an
    order-independent summation. Design §2.4 revision 7, after pass-20 F7: with ordinary left
    accumulation two routes carrying the *same multiset* of weights can compare unequal. Its
    counterexample is a fast route of per-edge costs `(.1, .2, .3)` taking 1 s against a slow route
    of `(.3, .2, .1)` taking 1,000 s — the same three binary floats in a different order. Left
    accumulation gives **0.6000000000000001** and **0.6**, so the slow route wins the cost argmin and
    the answer is **1,000 s**; an exactly-rounded sum gives **0.6** for both, they tie, and §2.4's
    travel-time key selects **1 s**. A FAIL/PASS flip at ten minutes decided by summation order.

    That mattered because §12's contract says implementations may vary while preserving the rules.
    Under left accumulation reassociation changes the answer, so no two implementations could be
    shown equivalent; under an exactly-rounded sum the total of a multiset is a well-defined number
    and the contract is true.

    Yields the empty path when `start == goal`. Non-negative weights make node-simple sufficient; see
    the module docstring.
    """
    results: list[tuple[tuple, tuple, tuple]] = []

    def walk(node: int, visited: frozenset[int], times: tuple, costs: tuple, ids: tuple) -> None:
        if node == goal:
            results.append((times, costs, ids))
            # a longer path to the same goal would have to revisit `goal`, so there is nothing more
            # to explore from here.
            return
        for e in graph.edges:
            for forward in (True, False):
                if not e.permits(forward=forward):
                    continue
                a, b = (e.u, e.v) if forward else (e.v, e.u)
                if a != node or b in visited:
                    continue
                walk(b, visited | {b}, times + (e.time_s,), costs + (e.total_cost,),
                     ids + (directed_identity(e, forward=forward),))

    walk(start, frozenset({start}), (), (), ())
    return results


def _entries(graph: ToyGraph, att: Attachment):
    """Leaving the origin's attached position: `(node, time, cost)` for each legal direction.

    Forward pays `(1 - f)` of the edge to reach `v`; reverse pays `f` to reach `u` and is legal only
    where the edge permits it. Apportionment is by the **same** fraction for time, base cost and
    penalty, with no exceptions (design §2.2).
    """
    e = graph.edges[att.edge]
    out = [(e.v, (1.0 - att.fraction) * e.time_s, (1.0 - att.fraction) * e.total_cost)]
    if e.permits(forward=False):
        out.append((e.u, att.fraction * e.time_s, att.fraction * e.total_cost))
    return out


def _exits(graph: ToyGraph, att: Attachment):
    """Arriving at the destination's attached position: `(node, time, cost)` for each legal approach.

    From `u` the remaining `f` is traversed forward; from `v` the remaining `(1 - f)` is traversed in
    reverse, which a one-way edge forbids.
    """
    e = graph.edges[att.edge]
    out = [(e.u, att.fraction * e.time_s, att.fraction * e.total_cost)]
    if e.permits(forward=False):
        out.append((e.v, (1.0 - att.fraction) * e.time_s, (1.0 - att.fraction) * e.total_cost))
    return out


def _same_edge_direct(graph: ToyGraph, origin: Attachment, dest: Attachment):
    """Design §2.2: a same-physical-edge direct traversal is a **candidate**, not the route.

    Returns `(time, cost)` or `None` when the direction forbids it — a one-way `u->v` with an origin
    at 0.8 and a destination at 0.2 cannot reach it directly at all.
    """
    if origin.edge != dest.edge:
        return None
    e = graph.edges[origin.edge]
    span = dest.fraction - origin.fraction
    if span < 0 and not e.permits(forward=False):
        return None
    f = abs(span)
    return f * e.time_s, f * e.total_cost


def journeys(graph: ToyGraph, origin: tuple[float, float],
             destinations: list[tuple[float, float]],
             destination_ids=None) -> list[Journey]:
    """Every journey from `origin` to every **eligible** destination. Design §2.2 in full.

    **Both connectors are charged at the access speed and enter BOTH objectives' totals** — design
    §2.1 ("Both include both connectors") and §2.2 ("part of both objectives' totals"). That means
    the connector is in the **cost** objective 2 selects on, not only in the reported time.

    Pass-20 F1 found this module adding the connectors to `time_s` and omitting them from `cost`, and
    the defect survived all twelve conformance cases: two edges from `(0,0)`, A to `(100,0)` at
    time/cost 10/10 and B to `(0,-100)` at 650/20, with destination A at `(100,100)` carrying a 100 m
    connector and B none. The own costs are `10 + 100/1.26` = **89.3650793651** and **20**, so
    objective 2 must select B and report **650 s**; omitting the connector selects A at cost 10 and
    reports 89.3650793651 s — **FAIL becomes PASS at ten minutes**. Objective 1 is unaffected, which
    is why only a case with *unequal* connectors and *different* destinations separates it.

    Revision 6's time-only connector policy is for the **independent engine** (§2.6), where seconds
    share no unit with that engine's generalised cost. It does not repeal §2.2 for ours, whose cost
    is already in seconds — `access.py` adds 120 s per restricted edge to it.
    """
    ids = ([str(i) for i in range(len(destinations))] if destination_ids is None
           else [str(d) for d in destination_ids])
    if len(ids) != len(destinations):
        raise ValueError("one destination id per destination")
    origin_atts = attachments(graph, origin, cap_m=MAX_ACCESS_M)
    out: list[Journey] = []
    for di, dxy in enumerate(destinations):
        dest_atts = attachments(graph, dxy, cap_m=POI_SNAP_MAX_M)
        for oa in origin_atts:
            access_o = oa.residual_m / ACCESS_SPEED_MPS
            for da in dest_atts:
                access_d = da.residual_m / ACCESS_SPEED_MPS
                direct = _same_edge_direct(graph, oa, da)
                if direct is not None:
                    e = graph.edges[oa.edge]
                    out.append(Journey(
                        time_s=math.fsum((access_o, access_d, direct[0])),
                        cost=math.fsum((access_o, access_d, direct[1])),
                        destination=di, destination_id=ids[di],
                        route=(directed_identity(e, forward=da.fraction >= oa.fraction),)))
                for en, et, ec in _entries(graph, oa):
                    for xn, xt, xc in _exits(graph, da):
                        for pt, pc, path_ids in _simple_paths(graph, en, xn):
                            out.append(Journey(
                                time_s=math.fsum((access_o, access_d, et, xt, *pt)),
                                cost=math.fsum((access_o, access_d, ec, xc, *pc)),
                                destination=di, destination_id=ids[di], route=path_ids))
    return out


# ----------------------------------------------------------------------------- the two objectives


@dataclass(frozen=True)
class OracleResult:
    """Design §2.1's two objectives, plus the bookkeeping the manifest requires (§12).

    `None` means **no finite time was found by exhaustive enumeration** — which on this toy graph is
    a genuine `NO_PATH`, since the enumeration is unbounded (design §2.5: `NO_PATH` may never be
    reported from a bounded search).
    """

    objective1_s: float | None
    objective1_destination: int | None
    objective2_s: float | None
    objective2_cost: float | None
    objective2_destination: int | None
    eligible: tuple[int, ...]
    ineligible: tuple[int, ...]
    origin_candidates: int
    n_journeys: int
    objective1_destination_id: str | None = None
    objective2_destination_id: str | None = None
    objective1_cost: float | None = None

    #: The measured nearest distance to the graph, retained even when the cap left no candidate,
    #: because `OFF_NETWORK`'s bound is `nearest / max_speed_mps` and the cap discards the distance
    #: it is computed from. `None` only when the graph holds no edge geometry at all, where there is
    #: no nearest distance and the absence must be reported rather than a number invented.
    origin_nearest_m: float | None = None


def evaluate(graph: ToyGraph, origin: tuple[float, float],
             destinations: list[tuple[float, float]],
             destination_ids=None) -> OracleResult:
    """Objective 1 by exhaustive minimisation of **time**; objective 2 by exhaustive minimisation of
    **cost**, then reporting *that* journey's time. Both totals carry both connectors.

    Objective 2 is deliberately **not** a minimum over the times of cost-optimal paths. Design §2.1:
    with identical engines on destinations `(cost, time) = (10, 10)` and `(100, 1)` the wrong
    functional reports -9 s of disagreement where there is none.

    Cost ties are broken by design §2.4 — smallest travel time, then destination id, then the route
    identity sequence — which matters because the production code is non-deterministic on insertion
    order, returning 10 or 1 for equal-cost coincident alternatives of time 10 and 1.

    **Cost equality is exact, and that is now safe.** It was not when costs accumulated left to
    right: pass-20 F7 built two routes carrying the same multiset of weights whose running sums
    differed in the last bit, selecting a 1,000 s route over a 1 s one. Totals are now computed with
    `math.fsum`, which is exactly rounded, so the sum of a multiset is one number whatever order it
    is presented in and genuinely equal costs compare equal. An epsilon is still *not* introduced —
    §2.4 declares no cost tolerance, and inventing one here would be this module making a rule.
    """
    nearest = nearest_on_graph(graph, origin, cap_m=MAX_ACCESS_M)
    eligible = tuple(i for i, d in enumerate(destinations)
                     if attachments(graph, d, cap_m=POI_SNAP_MAX_M))
    ineligible = tuple(i for i in range(len(destinations)) if i not in eligible)
    js = journeys(graph, origin, destinations, destination_ids)
    if not js:
        return OracleResult(None, None, None, None, None, eligible, ineligible,
                            len(nearest.candidates), 0,
                            origin_nearest_m=nearest.global_min_m)

    best_t = min(js, key=lambda j: j.rank_key)
    cheapest = min(j.cost for j in js)
    best_c = min((j for j in js if j.cost == cheapest), key=lambda j: j.rank_key)
    return OracleResult(
        objective1_s=best_t.time_s,
        objective1_destination=best_t.destination,
        objective1_cost=best_t.cost,
        objective1_destination_id=best_t.destination_id,
        objective2_s=best_c.time_s,
        objective2_cost=best_c.cost,
        objective2_destination=best_c.destination,
        objective2_destination_id=best_c.destination_id,
        eligible=eligible,
        ineligible=ineligible,
        origin_candidates=len(nearest.candidates),
        n_journeys=len(js),
        origin_nearest_m=nearest.global_min_m,
    )
