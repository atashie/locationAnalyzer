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

## What this oracle implements, and where the rule lives

Design **§2.2** is the normative text and this module follows it; the counterexamples that forced
each rule are in design §13, not repeated here. Three of its decisions are worth restating because
they are the ones an implementation gets wrong:

1. **An attachment is an occurrence along a polyline, not a point on the map.** The candidate key is
   structural and exact — `(edge, vertex index)` or `(edge, segment index, parameter)` — so a
   self-crossing road's two passes through one place stay two candidates, and the two descriptions
   of one shared vertex become one. No rounding enters it, because the time a merge discards scales
   with the edge's weight without bound.
2. **Candidates compete per edge record.** Two parallel records can share a canonical identity and
   differ in exactly the weight an objective minimises, so nothing upstream of ranking may collapse
   them.
3. **The band is applied around the global minimum first and each cap after**, per candidate, both
   caps inclusive. The *measured* nearest distance survives cap filtering, because `OFF_NETWORK`'s
   bound is computed from it and never from the cap.

`ATTACH_TIE_M` is a threshold, so the answer is well defined but **not continuous** in the geometry;
§2.2 says so and no output may claim otherwise.

The candidate universe is **per-segment minima, then the tie band across all records** — design
revision 10, which **reverted** revision 9's per-record exact filter. Revision 9 compared computed
residuals for exact equality, which discards genuine geometric ties (996.764 s FAIL against 16.912 s
PASS on two arms at exact squared distance 1), still moved under subdivision through the projection
arithmetic, and made the answer depend on record segmentation (600.035 s FAIL on one record against
599.979 s PASS on two degree-two records).

It is a **declared convention** and not a property of the road: the answer is a function of the
supplied geometry as given. Its sensitivities are listed on `nearest_on_graph` and are stated, not
denied. The cases marked `reading=` are the ones a different choice of universe would bear on; both
survive either choice unchanged, so the corpus does not distinguish them.

## Why node-simple paths suffice, and for what

Every weight here is non-negative, so a journey whose node sequence repeats a node contains a
non-negative cycle that can be excised without changing its endpoints or its partial-edge terms. The
excised journey is no worse, so restricting the enumeration to node-simple paths cannot miss a
numeric optimum, and the enumeration is finite.

That argument covers the **numbers** and not the **provenance**: lexicographic order is not a
well-order over unrestricted walks, since a zero-weight cycle can be inserted indefinitely to get a
smaller sequence. §2.4 therefore declares the provenance route domain node-simple as well, which is
what makes the selected route exist.
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
        # The **admissible-input contract**. Pass-21: a claim of total ordering over floats needs a
        # finite-input contract to stand on, and not every constructor enforced one. Comparisons,
        # `fsum` and the geometry arithmetic are all well defined on finite values and none of them
        # is on NaN, so a non-finite input is rejected here rather than producing a silently
        # unordered result later.
        for x, y in self.geometry:
            if not (math.isfinite(x) and math.isfinite(y)):
                raise ValueError(f"edge coordinates must be finite, got ({x!r}, {y!r})")
        for name, value in (("time_s", self.time_s), ("cost_base", self.cost_base),
                            ("penalty", self.penalty)):
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite, got {value!r}")
            if value < 0:
                raise ValueError(f"{name} must be non-negative, got {value!r}")

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

        Design §2.4. For an open edge `(u, v)` the endpoints already separate the two directions, so
        this adds nothing. For a **closed** edge `u == v` — a ring, a loop — swapping the endpoints
        does nothing and canonicalising the geometry against reversal removes the only remaining
        direction information, so the two traversals had **identical** identities (pass-20 F3: two
        one-way square loops gave 3,800 s or 200 s purely on insertion order).

        **For a palindromic geometry — one equal to its own reversal — both traversals get 0, and
        that is correct.** Pass-21 F7: on `((0,0),(1,0),(0,0))` the reverse traces the same ordered
        coordinate sequence, so the two descriptions *are* interchangeable and must share an
        identity. The field is derived from the geometry, so it cannot also be guaranteed different
        under reversal; requiring both was the error.
        """
        return 0 if self.rounded_geometry == self.geometry_key else 1

    @property
    def rounded_geometry(self) -> tuple[tuple[float, float], ...]:
        return tuple((round(x, ROUND_DP), round(y, ROUND_DP)) for x, y in self.geometry)

    @property
    def identity(self) -> tuple:
        """Design §2.4's canonical **directed**-edge identity: start node, end node, canonical
        geometry key, traversal orientation, osmid normalised to a sorted tuple, length at 2 dp.

        The orientation field exists for closed edges; see `orientation`. It is placed before `osmid`
        so that the comparison order remains structural-then-attributive.
        """
        return directed_identity(self, forward=True)

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
    arclength_m: float  # fraction x length
    residual_m: float   # straight-line from the coordinate to the attached position
    position: tuple[float, float]

    #: The occurrence's **exact structural** identity — `(edge, "v", vertex index)` for a position
    #: at a vertex, `(edge, "s", segment index, parameter)` for one interior to a segment. This is
    #: what deduplication keys on, and it involves **no rounding at all**.
    #:
    #: Revision 8, after pass-21 F1. Keying on a rounded arclength merged occurrences that are not
    #: interchangeable: on the 1.004 m out-and-back `(0,0),(0.002,0),(0,0),(0,1)` of 602 s, the two
    #: zero-residual origin occurrences at arclengths 0 and 0.004 m both round to 0.00, and keeping
    #: the first returns **602 s** where keeping the other returns **599.6015936255 s** — FAIL
    #: against PASS at ten minutes, from 4 mm of arclength. Scaling the edge weight scales the loss
    #: without bound, so no tolerance on metres can be safe. Two *descriptions* of one occurrence
    #: still collapse, because that is what they are.
    occurrence: tuple = ()


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

    The candidate set is, in this order:

    1. the nearest position on **each polyline segment** of each edge;
    2. those within `ATTACH_TIE_M` of the **global** minimum across all edges;
    3. deduplicated by **occurrence** — `(edge, "v", vertex index)` or `(edge, "s", segment index,
       parameter)`, with no rounding;
    4. filtered to those independently within `cap_m`.

    **This is a declared convention, not a property of the road.** Design revision 10 withdrew the
    ambition that it could be the latter. The candidate set is a function of the **supplied geometry
    as given**, computed by this sequence of operations, and the sensitivities below are its stated
    consequences rather than defects awaiting repair.

    **The known sensitivities of this convention, stated rather than denied.** Each is measured; none
    is claimed to be absent.

    * **Segment subdivision can move a verdict.** On one one-way edge `(0,0)→(100,0)` of time/cost
      **1199.95** with the origin at `(49.995,0)`, inserting the midpoint `(50,0)` creates a segment
      whose clamped start sits 0.005 m away, inside the band, and reports **599.9789682540 s** where
      the undivided edge reports **600.0349975000 s** — PASS against FAIL at an exact ten-minute
      comparator threshold, candidate count 1→2. Revision 9 was adopted to remove this and **did**
      remove it on this input; revision 10 reinstates it deliberately, because revision 9's way of
      removing it discarded genuine geometric ties and introduced a record-segmentation dependence
      instead. Note both values round to the **same whole minute**, so this is a comparator-verdict
      flip and not necessarily an encoded-map flip.
    * **The band is a threshold, so the answer is not continuous.** Two roads at residuals 1 m and
      1.009 m give 100.8007936510 s; at 1 m and 1.011 m, 1000.7936507940 s. An **899.99 s** jump
      across 2 mm.
    * **Projection arithmetic can drop a genuine tie.** Two arms whose exact rational squared
      distances are both exactly 1 compute as 0.9999999999999999 and 1.0. Under this convention the
      band admits both, so the tie survives *here* — but nothing in the arithmetic guarantees that,
      and a narrower band would not.
    * **Zero-length segments and curved re-expression.** Subdividing a zero-length segment adds
      vertices at one position, so the occurrence count changes (2→3 on `zero_length_segment`, with
      the reported time unchanged at 100.0 s); re-expressing a curved geometry moves the answer about
      **1.4e-14 s**. Neither moves a verdict on the declared scenarios.

    `measure_split_divergence` reports these rather than asserting them away. **What determines
    whether this convention is acceptable is a prevalence-and-impact measurement on the real Triangle
    graph, which has not been run.** Until it has, this rule is a *provisional development baseline*
    chosen for simplicity, not a demonstrated improvement over the alternatives.

    **Two things in the occurrence key are load-bearing, and both were wrong in revision 6.**

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
        per_edge: list[Attachment] = []
        for seg_index, (a, b) in enumerate(itertools.pairwise(e.geometry)):
            seg = math.hypot(b[0] - a[0], b[1] - a[1])
            d, t = _segment_nearest(px, py, a[0], a[1], b[0], b[1])
            along = run + t * seg
            # The occurrence key. A position at a *vertex* is keyed by that vertex's index, so the
            # two descriptions of one shared vertex — t = 1 on segment k and t = 0 on segment k+1 —
            # collapse exactly, and so does a zero-length segment's endpoint. An interior position
            # is keyed by its segment and parameter and never collapses with anything.
            if t == 0.0:
                key: tuple = (i, "v", seg_index)
            elif t == 1.0:
                key = (i, "v", seg_index + 1)
            else:
                key = (i, "s", seg_index, t)
            per_edge.append(Attachment(
                edge=i,
                fraction=0.0 if total == 0.0 else along / total,
                arclength_m=along,
                residual_m=d,
                position=(a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])),
                occurrence=key,
            ))
            run += seg
        # Design revision 10 **reverted** revision 9's per-record exact filter, which used to sit
        # here. It compared *computed* residuals for exact equality, and pass-24 F1 showed that
        # discards genuine geometric ties: two arms whose exact rational squared distances are both
        # exactly 1 compute as 0.9999999999999999 and 1.0, one ulp apart, so one was dropped --
        # 996.7640294933123 s FAIL where keeping both gives 16.912 s PASS. It also did not fix what
        # it was adopted for: `split_segments` on that same input still moves 996.764 FAIL to
        # 16.912 PASS, because the sensitivity was in the projection arithmetic and not in the band.
        # And it made the answer depend on **record segmentation** instead: one record reports
        # 600.0349975000001 s FAIL where two degree-two records report 599.9789682539683 s PASS on
        # the same road with the same weights (pass-24 F2).
        raw.extend(per_edge)
    if not raw:
        return NearestOnGraph(candidates=(), global_min_m=None)

    best = min(a.residual_m for a in raw)
    window = [a for a in raw if a.residual_m <= best + ATTACH_TIE_M]
    merged: dict[tuple, Attachment] = {}
    for a in window:
        current = merged.get(a.occurrence)
        if current is None or (a.residual_m, a.arclength_m) < (current.residual_m,
                                                               current.arclength_m):
            merged[a.occurrence] = a
    kept = sorted(merged.values(), key=lambda a: (a.edge, a.arclength_m))
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

    #: The journey's **network** seconds: the sum of its own network terms, not a subtraction of
    #: connectors from a rounded total. Exposed because the route invariant needs it — pass-22 F4
    #: showed that "a journey whose endpoints differ has a non-empty route" rejects a legal answer,
    #: since two points can attach at one position on one edge and move only through their
    #: connectors.
    #:
    #: The statement it supports is an **implication**, not an equivalence: an empty route implies
    #: zero network seconds. The converse is false on a zero-weight edge, which has a real
    #: one-element route and no network time.
    #:
    #: `compare=False`, so it enters neither `Journey` equality nor `rank_key`, and it is **not**
    #: compared across representations. Pass-23 F3: it is not determined by the declared ranking
    #: fields, so two winners that tie on every one of them can carry different network
    #: decompositions — 1 against 0.9968253968355556 on two records sharing a rounded identity —
    #: and edge order alone would then decide a reported number. Whether that tie should be broken
    #: is design revision 9's item 2.
    network_s: float = field(compare=False, default=0.0)

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
        return (self.time_s, self.destination_id, self.route, self.cost)


def directed_identity(edge: ToyEdge, *, forward: bool) -> tuple:
    """Design §2.4's identity for a traversal of `edge` in the given direction.

    **The reverse is derived by actually reversing the geometry and renormalising**, not by
    complementing the orientation bit. Pass-21 F7: on the palindrome `((0,0),(1,0),(0,0))` the bit
    flip produced orientation 1, while *constructing* the explicitly reversed edge produced
    orientation 0 — so one traversal had two identities depending on which representation the caller
    used, breaking reverse pairing and route identity. Deriving it the same way for both
    representations makes them agree, and makes a palindrome's two directions share an identity,
    which is correct because they trace the same ordered coordinates.
    """
    geometry = edge.geometry if forward else edge.geometry[::-1]
    u, v = (edge.u, edge.v) if forward else (edge.v, edge.u)
    rounded = tuple((round(x, ROUND_DP), round(y, ROUND_DP)) for x, y in geometry)
    key = min(rounded, rounded[::-1])
    return (u, v, key, 0 if rounded == key else 1,
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


def _partial_route(edge: ToyEdge, *, forward: bool, span: float) -> tuple:
    """The route-identity contribution of a partial traversal: its directed identity when the span
    is nonzero, and nothing when it is zero.

    Pass-21 F5: endpoint journeys carried only the intervening path's identities and omitted both
    partial traversals, so `rank_key` compared different *representations* of a route. On a
    zero-weight edge the selected route came back as the **empty tuple** — a route that travels from
    arclength 20 to 80 without traversing anything. A zero-span traversal contributes no identity
    because nothing is traversed, and that convention is declared rather than left implicit.
    """
    return () if span == 0.0 else (directed_identity(edge, forward=forward),)


def _entries(graph: ToyGraph, att: Attachment):
    """Leaving the origin's attached position: `(node, time, cost)` for each legal direction.

    Forward pays `(1 - f)` of the edge to reach `v`; reverse pays `f` to reach `u` and is legal only
    where the edge permits it. Apportionment is by the **same** fraction for time, base cost and
    penalty, with no exceptions (design §2.2).
    """
    e = graph.edges[att.edge]
    out = [(e.v, (1.0 - att.fraction) * e.time_s, (1.0 - att.fraction) * e.total_cost,
            _partial_route(e, forward=True, span=1.0 - att.fraction))]
    if e.permits(forward=False):
        out.append((e.u, att.fraction * e.time_s, att.fraction * e.total_cost,
                    _partial_route(e, forward=False, span=att.fraction)))
    return out


def _exits(graph: ToyGraph, att: Attachment):
    """Arriving at the destination's attached position: `(node, time, cost)` for each legal approach.

    From `u` the remaining `f` is traversed forward; from `v` the remaining `(1 - f)` is traversed in
    reverse, which a one-way edge forbids.
    """
    e = graph.edges[att.edge]
    out = [(e.u, att.fraction * e.time_s, att.fraction * e.total_cost,
            _partial_route(e, forward=True, span=att.fraction))]
    if e.permits(forward=False):
        out.append((e.v, (1.0 - att.fraction) * e.time_s, (1.0 - att.fraction) * e.total_cost,
                    _partial_route(e, forward=False, span=1.0 - att.fraction)))
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
                        network_s=direct[0],
                        route=_partial_route(e, forward=da.fraction >= oa.fraction,
                                             span=abs(da.fraction - oa.fraction))))
                for en, et, ec, entry_route in _entries(graph, oa):
                    for xn, xt, xc, exit_route in _exits(graph, da):
                        for pt, pc, path_ids in _simple_paths(graph, en, xn):
                            out.append(Journey(
                                time_s=math.fsum((access_o, access_d, et, xt, *pt)),
                                cost=math.fsum((access_o, access_d, ec, xc, *pc)),
                                destination=di, destination_id=ids[di],
                                network_s=math.fsum((et, xt, *pt)),
                                route=entry_route + path_ids + exit_route))
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
    objective1_route: tuple = ()
    objective2_route: tuple = ()

    #: The selected journeys' **network** seconds — the sum of their network terms. See
    #: `Journey.network_s`: the route invariant is an *implication* from this, not a test on whether
    #: the endpoints differ, and it is deliberately not compared across representations.
    objective1_network_s: float | None = None
    objective2_network_s: float | None = None

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
        objective1_route=best_t.route,
        objective2_route=best_c.route,
        objective1_network_s=best_t.network_s,
        objective2_network_s=best_c.network_s,
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
