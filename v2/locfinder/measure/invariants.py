"""Invariants over the admissible-input domain, and the representation transforms that must preserve
them.

**Why this module exists, in Codex pass 21's words:** *"The recurring process problem is treating
repair of the motivating example as evidence that a replacement rule's domain is settled."* Three
consecutive passes found that a fix closing the reviewed case opened an adjacent one — pass 19's two
blockers became four of pass 20's findings, which became three of pass 21's — and each time the
mechanism was the same: a named case proves a point, and a rule's *domain* is a different thing from
a point in it. Pass 21's recommendation was explicit: *"a compact set of invariants and
admissible-input rules exercised across representations, rather than another claim that the previous
named examples now pass."*

So this module is the instrument, not another case. It says three things:

1. **what an admissible input is** — `ToyEdge` and `ToyGraph` enforce it; `SCENARIOS` enumerates the
   shapes that have ever mattered;
2. **what must be true of every admissible input** — `INVARIANTS`, each a predicate on one
   evaluation;
3. **which re-expressions of one input must give the same answer** — `TRANSFORMS`, each a function
   from a scenario to an equivalent scenario.

The same lesson as the resolver benchmark, which `feedback-benchmark-over-point-fixes` records: when
a second round of fixes in one area breaks something new, stop and build the instrument instead of
attempting a third. This is the third round.

## What is deliberately *not* an invariant

Recorded here rather than silently absent, because an invariant that correct code cannot satisfy is
worse than no invariant:

* **Objective 2 is not monotone** in the destination set. Adding a *cheaper* destination correctly
  raises its reported time, 10 s → 100 s.
* **Splitting a segment is not answer-preserving.** Design §2.2's candidate rule is "the nearest
  position on each polyline *segment*", so subdividing a segment can add a candidate. That is a real
  property of the chosen rule, not a defect in the implementation of it, and
  `measure_split_divergence` quantifies it rather than asserting it away. If the design ever wants
  subdivision invariance it has to choose the exact per-geometry reading instead, and pass 20
  measured what that costs: 599.9747619048 s against 600.0399682540 s on its L-shaped edge, PASS
  against FAIL.
* **The answer is not continuous in the geometry.** 2 mm of movement can move it 899.99 s, because
  `attach_tie_m` is a threshold. §2.2 says so.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, field, replace

from .conformance import TIME_TOL_S, tolerance_is_decision_irrelevant
from . import toy
from .toy import ToyEdge, ToyGraph


@dataclass(frozen=True)
class Scenario:
    """One admissible input: a graph, an origin, and identified destinations."""

    name: str
    graph: ToyGraph
    origin: tuple[float, float]
    destinations: tuple[tuple[float, float], ...]
    destination_ids: tuple[str, ...] | None = None
    shapes: tuple[str, ...] = ()        # which structural features this scenario carries

    def run(self):
        ids = list(self.destination_ids) if self.destination_ids else None
        # Through the module attribute, never a name imported here -- see `invariant_violations`.
        return toy.evaluate(self.graph, self.origin, list(self.destinations), ids)


def _route(result, objective: int) -> tuple:
    """A **reduction** of the selected route, not its identity.

    Pass-22 F6 is right that this is lossy and that the previous docstring overclaimed: the node
    pair and the geometry key are both dropped, so two different roads of the same osmid,
    orientation and rounded length are indistinguishable here, and traversal intervals never appear
    at all. It is a comparison key for the transforms below, and nothing in the design says the
    reported route identity is this tuple.

    The two fields are dropped for different reasons. `translate` changes every coordinate, so the
    geometry key cannot survive it. `explicit_reverses` re-expresses a reverse traversal as a
    forward traversal of a reversed record, which legitimately swaps the endpoint pair while
    describing the same physical traversal.
    """
    route = result.objective1_route if objective == 1 else result.objective2_route
    return tuple((ident[3], ident[4], ident[5]) for ident in (route or ()))


#: Fields whose equality across representations must be **exact**. These are identities and counts;
#: nothing about re-expressing an input may perturb a discrete choice.
DISCRETE_FIELDS = ("objective1_destination_id", "objective2_destination_id", "eligible_ids",
                   "objective1_route", "objective2_route", "origin_candidates")

#: Seconds. Compared at `TIME_TOL_S` and additionally required to be decision-irrelevant against the
#: published minute thresholds, which is the only unit where that proof is available.
SECONDS_FIELDS = ("objective1_s", "objective2_s", "objective1_network_s", "objective2_network_s")

#: Metres. Compared at `DISTANCE_TOL_M` and checked against the thresholds a residual actually
#: faces — the two caps and the tie band — rather than against a time.
METRE_FIELDS = ("origin_nearest_m",)

#: Our cost, which is in seconds but is **not** compared against a time threshold. Pass-22 F7: a
#: cost never faces a published threshold, it only ever enters an argmin, so no tolerance on it can
#: be shown decision-irrelevant. A competing cost 2e-10 away flips which journey wins while a 5e-10
#: change passes any such test. The tolerance here is therefore an **admission**, recorded as one:
#: it says these two runs agree to within float noise, not that no selection could have moved.
#: `NOT_PROVEN` names it so the limitation is visible where the number is used.
COST_FIELDS = ("objective1_cost", "objective2_cost")

#: Metres tolerance, carried separately from the seconds one. A residual's smallest threshold is the
#: 0.01 m tie band, so this must stay well below it.
DISTANCE_TOL_M = 1e-9

#: The thresholds a metre quantity faces: both caps, inclusive, and the tie band.
DISTANCE_THRESHOLDS_M = (toy.ATTACH_TIE_M, toy.MAX_ACCESS_M, toy.POI_SNAP_MAX_M)

#: What a tolerance on a cost does not establish. Referenced by the build record.
NOT_PROVEN = ("A cost tolerance is not decision-irrelevant: cost faces no published threshold, "
              "only an argmin, so an accepted difference can coexist with a flipped selection.")


def _distance_is_decision_irrelevant(metres: float, *, tol: float = DISTANCE_TOL_M) -> bool:
    """True when `metres ± tol` falls the same side of every threshold a residual faces."""
    for t in DISTANCE_THRESHOLDS_M:
        if (metres - tol <= t) != (metres + tol <= t):
            return False
    return True


def differences(before: dict, after: dict) -> dict:
    """Fields that differ: discrete ones exactly, continuous ones in their own unit.

    Four things in order, and the order is the fix for pass-22 F7:

    1. **Exact equality is never a difference.** The previous version asked whether the value was
       decision-irrelevant *before* asking whether it had moved, so two identical answers of exactly
       600.0 s were reported as differing — the threshold test fails on a value sitting on a
       threshold, even when the difference is zero. It rejected correct implementations at precisely
       the values a verdict turns on.
    2. **A non-finite value is always a difference.** `abs(a - nan) > tol` is false, so a finite
       answer replaced by NaN or an infinity passed clean. A non-result is not a small change.
    3. **Magnitude, in the field's own unit.**
    4. **Decision relevance, where it can be established** — against minute thresholds for seconds
       and against the caps and tie band for metres. For a cost it cannot be, and `COST_FIELDS`
       records that rather than borrowing the seconds test.
    """
    out = {}
    for key in before:
        a, b = before[key], after[key]
        if a is b or a == b:
            continue                                        # (1)
        unit = ("s" if key in SECONDS_FIELDS else "m" if key in METRE_FIELDS
                else "cost" if key in COST_FIELDS else None)
        if unit is None or not isinstance(a, float) or not isinstance(b, float):
            out[key] = (a, b)
            continue
        if not (math.isfinite(a) and math.isfinite(b)):
            out[key] = (a, b)                               # (2)
            continue
        tol = DISTANCE_TOL_M if unit == "m" else TIME_TOL_S
        if abs(a - b) > tol:                                # (3)
            out[key] = (a, b)
            continue
        if unit == "s" and not (tolerance_is_decision_irrelevant(a)      # (4)
                                and tolerance_is_decision_irrelevant(b)):
            out[key] = (a, b)
        elif unit == "m" and not (_distance_is_decision_irrelevant(a)
                                  and _distance_is_decision_irrelevant(b)):
            out[key] = (a, b)
    return out


def answers(scenario: Scenario) -> dict:
    """The **measured quantities** — every number and identity an S3 output reports about a point.

    An invariant that compared only times would miss the two defects pass 21 found in provenance: a
    falsely empty selected route, and an objective-1 cost decided by insertion order. So the selected
    destination and both selected costs are in here.
    """
    r = scenario.run()
    return {
        "objective1_s": r.objective1_s,
        "objective1_cost": r.objective1_cost,
        "objective1_destination_id": r.objective1_destination_id,
        "objective2_s": r.objective2_s,
        "objective2_cost": r.objective2_cost,
        "objective2_destination_id": r.objective2_destination_id,
        "eligible_ids": tuple(sorted(_ids(scenario)[i] for i in r.eligible)),
        "origin_nearest_m": r.origin_nearest_m,
        # The selected routes are measured quantities, not bookkeeping: design §12 requires route
        # references in the manifest. They are here because the mutation check showed three fixes
        # with no guard at all once they were absent -- a bit-complemented orientation, a dropped
        # zero-span branch and a route missing its partial traversals all survived both suites.
        # Under `explicit_reverses` a reverse traversal becomes a forward traversal of an
        # explicitly reversed edge, so the same physical traversal is reached two ways and its
        # identity must agree: that is what catches the orientation defect.
        "objective1_route": _route(r, 1),
        "objective2_route": _route(r, 2),
        # Network seconds, so the route check can be the equivalence it should always have been
        # (pass-22 F4) rather than a test on whether the endpoints differ.
        "objective1_network_s": r.objective1_network_s,
        "objective2_network_s": r.objective2_network_s,
    }


def provenance(scenario: Scenario) -> dict:
    """What the manifest records *about how* the answer was reached.

    Held separately from `answers` because the two are invariant under different things, and
    building this module is what made that distinction necessary. `explicit_reverses` replaces one
    bidirectional edge with two opposed one-way records; the answers are identical, and
    `origin_candidates` **doubles**, because there genuinely are two routing records attached at that
    position. §2.2's candidates compete per record — pass-20 F4 is the reason they must — so a
    representation carrying more records has more candidates.

    That is a property of the *input*, not of the implementation. §12's equivalence contract is about
    implementations varying on one input; two ways of writing the same roads are two inputs. So
    provenance is required invariant only under transforms that leave the record structure alone.
    """
    r = scenario.run()
    return {"origin_candidates": r.origin_candidates}


def reported(scenario: Scenario) -> dict:
    """`answers` and `provenance` together, for the transforms that must preserve both."""
    return {**answers(scenario), **provenance(scenario)}


def _ids(scenario: Scenario) -> list[str]:
    if scenario.destination_ids:
        return list(scenario.destination_ids)
    return [str(i) for i in range(len(scenario.destinations))]


# ----------------------------------------------------------------------------- the admissible domain


def _e(u, v, geometry, time_s, cost_base, *, penalty=0.0, osmid=(1,), oneway=False) -> ToyEdge:
    return ToyEdge(u, v, geometry, time_s=time_s, cost_base=cost_base, penalty=penalty,
                   osmid=osmid, oneway=oneway)


def _chain(depth: int, *, each_s: float = 80.0) -> Scenario:
    """A one-way chain of `depth` edges, origin and destination on its two end nodes.

    The reachable total is `depth * each_s` exactly, with both connectors zero, so a bound on path
    enumeration shows up as a *reported absence* on a graph whose answer is a single number.
    """
    edges = tuple(_e(i, i + 1, ((100.0 * i, 0.0), (100.0 * (i + 1), 0.0)), each_s, each_s,
                     osmid=(i + 1,), oneway=True) for i in range(depth))
    return Scenario(f"chain_{depth}", ToyGraph(edges=edges), (0.0, 0.0),
                    ((100.0 * depth, 0.0),), shapes=("chain", f"hop-depth-{depth}"))


#: Every structural shape that has mattered in a review, each as one small scenario. These are not
#: expected-answer fixtures — the conformance corpus holds those — they are the **domain** the
#: invariants below are quantified over.
SCENARIOS: tuple[Scenario, ...] = (
    Scenario("single_edge", ToyGraph(edges=(_e(0, 1, ((0, 0), (100, 0)), 100.0, 100.0),)),
             (10.0, 5.0), ((90.0, 5.0),), shapes=("open",)),
    Scenario("parallel_alternatives", ToyGraph(edges=(
        _e(0, 1, ((0, 0), (100, 0)), 1.0, 100.0, osmid=(1,)),
        _e(0, 1, ((0, 0), (100, 0)), 10.0, 10.0, osmid=(2,)),
        _e(0, 1, ((0, 0), (100, 0)), 5.0, 50.0, osmid=(3,)),
    )), (50.0, 0.0), ((100.0, 0.0),), shapes=("parallel", "three-way-tie")),
    Scenario("same_identity_alternatives", ToyGraph(edges=(
        _e(0, 1, ((0, 0), (100, 0)), 100.0, 1.0, osmid=(7,)),
        _e(0, 1, ((0, 0), (100, 0)), 100.0, 2.0, osmid=(7,)),
    )), (0.0, 0.0), ((100.0, 0.0),), shapes=("parallel", "shared-identity")),
    Scenario("one_way_with_return", ToyGraph(edges=(
        _e(0, 1, ((0, 0), (100, 0)), 100.0, 100.0, oneway=True),
        _e(1, 2, ((100, 0), (100, 50)), 100.0, 100.0, osmid=(2,), oneway=True),
        _e(2, 0, ((100, 50), (0, 0)), 100.0, 100.0, osmid=(3,), oneway=True),
    )), (80.0, 0.0), ((20.0, 0.0),), shapes=("oneway", "partial-edge")),
    Scenario("multi_segment", ToyGraph(edges=(
        _e(0, 1, ((0, 0), (100, 0), (100, 100)), 200.0, 200.0),)),
        (0.0, 0.0), ((100.0, 50.0),), shapes=("multi-segment",)),
    Scenario("self_crossing", ToyGraph(edges=(
        _e(0, 1, ((-100, 0), (0, 0), (0, 100), (100, 100), (100, 0), (0, 0), (0, -100)),
           1000.0, 1000.0, oneway=True),)),
        (0.0, 0.0), ((0.0, -100.0),), shapes=("self-crossing", "repeated-position")),
    Scenario("closed_ring", ToyGraph(edges=(
        _e(0, 0, ((0, 0), (100, 0), (100, 100), (0, 100), (0, 0)), 400.0, 400.0),)),
        (10.0, 0.0), ((0.0, 10.0),), shapes=("closed", "self-loop")),
    Scenario("two_closed_rings_opposed", ToyGraph(edges=(
        _e(0, 0, ((0, 0), (100, 0), (100, 100), (0, 100), (0, 0)), 4000.0, 4000.0, osmid=(7,),
           oneway=True),
        _e(0, 0, ((0, 0), (0, 100), (100, 100), (100, 0), (0, 0)), 4000.0, 4000.0, osmid=(7,),
           oneway=True),
    )), (10.0, 0.0), ((0.0, 10.0),), shapes=("closed", "opposed-orientations")),
    Scenario("palindrome_loop", ToyGraph(edges=(
        _e(0, 0, ((0, 0), (50, 0), (0, 0)), 100.0, 100.0),)),
        (25.0, 0.0), ((0.0, 0.0),), shapes=("closed", "palindrome")),
    Scenario("zero_length_segment", ToyGraph(edges=(
        _e(0, 1, ((0, 0), (0, 0), (100, 0)), 100.0, 100.0),)),
        (0.0, 0.0), ((100.0, 0.0),), shapes=("zero-length-segment",)),
    Scenario("zero_weight_edge", ToyGraph(edges=(
        _e(0, 1, ((0, 0), (100, 0)), 0.0, 0.0),)),
        (20.0, 0.0), ((80.0, 0.0),), shapes=("zero-weight",)),
    Scenario("reverse_palindrome", ToyGraph(edges=(
        _e(0, 1, ((0, 0), (50, 0), (0, 0)), 100.0, 100.0),)),
        (25.0, 1.0), ((0.0, 0.0),), shapes=("palindrome", "reverse-traversal")),
    Scenario("reverse_traversal", ToyGraph(edges=(
        _e(0, 1, ((0, 0), (100, 0)), 100.0, 100.0),)),
        (80.0, 0.0), ((20.0, 0.0),), shapes=("reverse-traversal", "partial-edge")),
    Scenario("reverse_traversal_curved", ToyGraph(edges=(
        _e(0, 1, ((0, 0), (40, 30), (100, 0)), 100.0, 100.0),)),
        (95.0, 5.0), ((5.0, 5.0),), shapes=("reverse-traversal", "multi-segment")),
    Scenario("zero_span", ToyGraph(edges=(
        _e(0, 1, ((0, 0), (100, 0)), 1000.0, 1000.0),)),
        (50.0, 0.0), ((50.0, 0.0),), shapes=("zero-span",)),
    Scenario("disconnected_tie", ToyGraph(edges=(
        _e(0, 1, ((0, 1), (100, 1)), 100.0, 100.0, osmid=(1,)),
        _e(2, 3, ((0, -1), (100, -1)), 1000.0, 1000.0, osmid=(2,)),
    )), (0.0, 0.0), ((100.0, 0.0),), shapes=("disconnected", "geometric-tie")),
    Scenario("penalty_bearing", ToyGraph(edges=(
        _e(0, 1, ((0, 0), (100, 0)), 1000.0, 1.0, penalty=120.0, osmid=(1,)),
        _e(0, 2, ((0, 0), (0, 50)), 5.0, 5.0, osmid=(2,)),
    )), (0.0, 0.0), ((1.0, 0.0), (0.0, 50.0)), shapes=("penalty", "two-destinations")),
    Scenario("unequal_connectors", ToyGraph(edges=(
        _e(0, 1, ((0, 0), (100, 0)), 10.0, 10.0, osmid=(1,)),
        _e(0, 2, ((0, 0), (0, -100)), 650.0, 20.0, osmid=(2,)),
    )), (0.0, 0.0), ((100.0, 100.0), (0.0, -100.0)), shapes=("unequal-connectors",)),
    Scenario("coincident_destinations", ToyGraph(edges=(
        _e(0, 1, ((0, 0), (100, 0)), 10.0, 10.0),)),
        (0.0, 0.0), ((100.0, 0.0), (100.0, 0.0)), destination_ids=("z", "a"),
        shapes=("coincident-destinations",)),
    Scenario("off_network_origin", ToyGraph(edges=(
        _e(0, 1, ((0, 0), (100, 0)), 100.0, 100.0),)),
        (50.0, 250.0), ((100.0, 0.0),), shapes=("off-network",)),
    Scenario("no_route", ToyGraph(edges=(
        _e(0, 1, ((0, 0), (100, 0)), 100.0, 100.0, oneway=True),)),
        (80.0, 0.0), ((20.0, 0.0),), shapes=("no-path", "oneway")),
    Scenario("empty_graph", ToyGraph(edges=()), (0.0, 0.0), ((10.0, 0.0),),
             shapes=("empty-graph",)),
    # --- hop depth. Pass-22 F2: a uniform <=4-edge cutoff in `_simple_paths` passed all 423 tests
    # in this layer and the corpus together, because no scenario above needs a journey more than
    # four edges deep. The missing thing was not an input but a **coverage dimension**, so these are
    # parameterised by depth and `CHAIN_DEPTHS` names the dimension. A cutoff anywhere in the range
    # now turns a reachable destination into a reported absence, which design §2.5 forbids:
    # `NO_PATH` may never come from a bounded search.
    *tuple(_chain(depth) for depth in (2, 4, 5, 7, 9)),
)

#: The hop depths `SCENARIOS` exercises, as a declared dimension rather than an accident of which
#: inputs reviews happened to produce. A chain of `depth` edges spends its first and last on entry
#: and exit, so it needs `depth - 2` intervening path edges.
CHAIN_DEPTHS = (2, 4, 5, 7, 9)


# ----------------------------------------------------------------------------- transforms


def permute_edges(scenario: Scenario) -> Scenario:
    """Reverse the edge list. Nothing reported may change — design §2.4 exists for this."""
    return replace(scenario, name=f"{scenario.name}+permuted",
                   graph=ToyGraph(edges=tuple(reversed(scenario.graph.edges))))


def translate(scenario: Scenario, dx: float = 12345.678, dy: float = -98765.432) -> Scenario:
    """Offset every coordinate. Weights are carried, not derived from position, so nothing reported
    may change — this catches an accidental dependence on absolute coordinates, which a grid-aligned
    fixture set would never show."""
    def shift(geometry):
        return tuple((x + dx, y + dy) for x, y in geometry)
    return replace(
        scenario, name=f"{scenario.name}+translated",
        graph=ToyGraph(edges=tuple(replace(e, geometry=shift(e.geometry))
                                   for e in scenario.graph.edges)),
        origin=(scenario.origin[0] + dx, scenario.origin[1] + dy),
        destinations=tuple((x + dx, y + dy) for x, y in scenario.destinations),
    )


def explicit_reverses(scenario: Scenario) -> Scenario:
    """Replace each bidirectional edge with two one-way edges, the second carrying the explicitly
    reversed geometry.

    This is the transform pass-21 F7 was about: the same traversal reached through two supported
    representations must get the same identity, and a bit-complemented orientation gave it two.
    """
    edges = []
    for e in scenario.graph.edges:
        if e.oneway:
            edges.append(e)
            continue
        edges.append(replace(e, oneway=True))
        edges.append(replace(e, u=e.v, v=e.u, geometry=e.geometry[::-1], oneway=True))
    return replace(scenario, name=f"{scenario.name}+explicit-reverses",
                   graph=ToyGraph(edges=tuple(edges)))


def scale_weights(scenario: Scenario, factor: float = 7.0) -> Scenario:
    """Multiply every time and cost by one positive constant.

    **Selection is not scale-invariant, and the reported total is not proportional** — the first
    version of this asserted both and pass-22 F3 refuted them with two edges from one origin whose
    destinations carry a 100 m connector and none. Scaling the network weights but not the
    connectors moves the two journeys' totals along lines with different intercepts, so they cross:
    the selection is B, B, A at scales 1, 3 and 7, reporting 20, 60 and `7 + 100/1.26` =
    **86.3650793651 s**. Continuing the supposedly invariant selection reports 140 s instead, which
    flips FAIL to PASS at a 100 s threshold.

    What *is* implied, and what `invariant_violations` now checks instead, is in
    `SCALE_LAW`: a minimum over journeys whose totals are affine in the scale is **concave** in the
    scale, with equality exactly where the selection holds; and a journey held fixed has an affine
    total. The crossing is the correct behaviour, so the invariant has to permit it and the
    concavity still constrains it.
    """
    return replace(scenario, name=f"{scenario.name}+scaled",
                   graph=ToyGraph(edges=tuple(
                       replace(e, time_s=e.time_s * factor, cost_base=e.cost_base * factor,
                               penalty=e.penalty * factor) for e in scenario.graph.edges)))


def split_segments(scenario: Scenario) -> Scenario:
    """Insert the midpoint of every segment as an explicit vertex.

    **Not** answer-preserving, by design: §2.2's candidate rule is per *segment*, so subdividing can
    add a candidate. `measure_split_divergence` reports where it does rather than asserting it does
    not.
    """
    def split(geometry):
        out = [geometry[0]]
        for a, b in itertools.pairwise(geometry):
            out.append(((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0))
            out.append(b)
        return tuple(out)
    return replace(scenario, name=f"{scenario.name}+split",
                   graph=ToyGraph(edges=tuple(replace(e, geometry=split(e.geometry))
                                              for e in scenario.graph.edges)))


#: Transforms that must leave every **measured quantity** identical. `explicit_reverses` changes the
#: record structure, so it preserves `answers` but not `provenance` — see `provenance`.
ANSWER_PRESERVING: tuple = (permute_edges, translate, explicit_reverses)

#: Transforms that must additionally leave the **provenance** identical, because they do not change
#: how many edge records the input holds.
FULLY_PRESERVING: tuple = (permute_edges, translate)

#: Transforms that preserve the *selection* but scale the reported magnitudes.
SCALING: tuple = (scale_weights,)

#: Where a transform is only required to preserve a **weakened** correspondence, and why. Pass-22 F4:
#: orientation is chosen by a lexicographic comparison of the geometry *after rounding*, so a
#: translation can legitimately change it — on the edge `((.003,0),(.006,0))` both endpoints round to
#: 12345.68 after the offset, making the rounded geometry palindromic and the orientation 0 where it
#: was 1. Monotonicity of addition proves nothing about a choice made after rounding. Orientation is
#: still compared under the two transforms that leave coordinates alone, which is where the
#: bit-complemented-orientation mutant lives, so this costs no coverage.
WEAKENED: dict = {
    "translate": (("objective1_route", "objective2_route", "orientation"),
                  "orientation is decided lexicographically on the rounded geometry, which a "
                  "coordinate offset may legitimately change"),
}


def _drop_orientation(value):
    """A route reduction with its leading orientation field removed."""
    return tuple(ident[1:] for ident in (value or ()))


def compare(before: dict, after: dict, transform_name: str = "") -> dict:
    """`differences`, through the correspondence that `transform_name` actually preserves."""
    weakened = WEAKENED.get(transform_name)
    if not weakened:
        return differences(before, after)
    fields = weakened[0]
    if fields[-1] == "orientation":
        before = {k: (_drop_orientation(v) if k in fields[:-1] else v) for k, v in before.items()}
        after = {k: (_drop_orientation(v) if k in fields[:-1] else v) for k, v in after.items()}
    return differences(before, after)

#: Transforms deliberately **not** required to preserve the answer, with the reason.
NOT_PRESERVING: dict = {
    "split_segments": "design §2.2's candidate rule is per polyline segment, so subdividing a "
                      "segment can add a candidate. A subdivision-invariant rule would have to be "
                      "the exact per-geometry one. Pass-22 F5 shows the exposure is not small: on "
                      "one straight one-way edge of 1199.95 s, an origin at (49.995,0) has one "
                      "candidate and reports 600.0349975000 s, FAIL; inserting the midpoint (50,0) "
                      "puts a clamped segment start 0.005 m away, inside the tie band, giving "
                      "599.9789682540 s, PASS. No road changed.",
    "scale_weights": "selection is not scale-invariant and the total is not proportional, because "
                     "connectors do not scale. See `scale_weights` and `SCALE_LAW`.",
}

#: The three collinear scales the law is checked on. Collinear so the middle one has a chord.
SCALE_POINTS = (1.0, 3.0, 7.0)

#: What a uniform positive weight scaling *does* imply, stated so the false version cannot come
#: back. Both limbs are properties of a minimum over affinely-parameterised journeys.
SCALE_LAW = (
    "objective 1's reported time and objective 2's reported cost are each a minimum over journeys "
    "whose totals are affine in the scale, hence **concave** in the scale, with equality exactly "
    "where the argmin does not switch. Objective 2's reported *time* and objective 1's reported "
    "*cost* are the other quantity of the selected journey and are concave in nothing: the argmin "
    "can switch either way. A journey held fixed has an affine total, up to rounding."
)


def measure_split_divergence():
    """Where subdivision changes the answer, and by how much. Reported, not asserted."""
    out = []
    for scenario in SCENARIOS:
        before, after = reported(scenario), reported(split_segments(scenario))
        differing = differences(before, after)
        if differing:
            out.append((scenario.name, differing))
    return out

# ----------------------------------------------------------------------------- programmatic checks


def invariant_violations() -> list[str]:
    """Run the invariants directly, returning a violation list rather than asserting.

    `test_mutants.py` needs to ask "would this layer have caught that?" without starting a nested
    pytest, and a guard nobody checks is not a guard.

    **Every call into `toy` goes through the module attribute**, never through a name imported here.
    A mutation harness patches `toy.evaluate` or `toy.directed_identity`, and a `from .toy import
    evaluate` keeps the original binding — so the check compares correct output against correct
    output and reports that the mutant was caught by someone else. That has now happened twice.
    Pass 21's orientation mutant read as uncaught by every layer until this module stopped holding
    its own `directed_identity`; pass-22 F8 then found that `evaluate` was *still* imported by name
    in both this module and `conformance.py`, so a wrapper adding 1000 s to every journey — PASS to
    FAIL — left `invariant_violations()` returning `[]`. Fixing the one binding that had bitten me
    and not the others is the same error this whole module exists to stop, one level up.
    `test_mutants.py::test_a_sentinel_evaluator_mutation_reaches_both_layers` is the guard.
    """
    bad: list[str] = []
    for scenario in SCENARIOS:
        base_answers = answers(scenario)
        base_reported = reported(scenario)
        for transform in ANSWER_PRESERVING:
            diff = compare(base_answers, answers(transform(scenario)), transform.__name__)
            if diff:
                bad.append(f"{scenario.name}/{transform.__name__}: answers changed {diff}")
        for transform in FULLY_PRESERVING:
            diff = compare(base_reported, reported(transform(scenario)), transform.__name__)
            if diff:
                bad.append(f"{scenario.name}/{transform.__name__}: provenance changed {diff}")

        result = scenario.run()
        if result.objective1_s is not None:
            if result.objective1_s > result.objective2_s + 1e-12:
                bad.append(f"{scenario.name}: objective 1 slower than objective 2")
            if result.objective2_cost > result.objective1_cost + 1e-12:
                bad.append(f"{scenario.name}: objective 2 dearer than objective 1")
            legal = {toy.directed_identity(e, forward=f) for e in scenario.graph.edges
                     for f in (True, False) if e.permits(forward=f)}
            for route in (result.objective1_route, result.objective2_route):
                if any(ident not in legal for ident in route):
                    bad.append(f"{scenario.name}: route names an impermissible traversal")
            # **An empty route implies zero network seconds**, and only that direction. Pass-22 F4:
            # the previous form asked whether the endpoints differed, and rejected a correct
            # 2.3809523810 s answer where both points attach at arclength 50 on one 1000 s edge and
            # all movement is in the two connectors.
            #
            # I first wrote this as an equivalence, and the `zero_weight_edge` scenario refused it
            # within the minute: a journey across a 0 s edge has a real one-element route and zero
            # network seconds, so a non-empty route with no network time is legal. The implication
            # still catches what the equivalence was for — `route_without_partials` empties the
            # route of a journey carrying a weighted partial traversal — without asserting a
            # converse the design does not give.
            for n, (route, network) in enumerate(
                    ((result.objective1_route, result.objective1_network_s),
                     (result.objective2_route, result.objective2_network_s)), start=1):
                if not route and network != 0.0:
                    bad.append(f"{scenario.name}: objective {n} has an empty route but "
                               f"{network!r} network seconds")

        # The scale law, in the form `SCALE_LAW` states and no stronger. Concavity of a minimum of
        # affine functions, checked on three collinear scales: the middle value may not fall below
        # the chord. Pass-22 F3 refuted the proportionality and selection-invariance this replaces.
        points = [answers(scale_weights(scenario, float(k))) for k in SCALE_POINTS]
        lo, mid, hi = SCALE_POINTS
        weight = (hi - mid) / (hi - lo)
        for key in ("objective1_s", "objective2_cost"):
            values = [p[key] for p in points]
            if any(v is None for v in values):
                continue
            chord = weight * values[0] + (1.0 - weight) * values[2]
            if values[1] < chord - 1e-9:
                bad.append(f"{scenario.name}: {key} is not concave in the weight scale — "
                           f"{values[1]!r} at scale {mid} is below the chord {chord!r}")
        # Affinity, conditioned on the journey actually holding. Where the selection is stable the
        # law is exact arithmetic and worth asserting; where it switches, the switch is correct.
        if all(p["objective1_route"] == points[0]["objective1_route"]
               and p["objective1_destination_id"] == points[0]["objective1_destination_id"]
               for p in points):
            values = [p["objective1_s"] for p in points]
            if not any(v is None for v in values):
                first = (values[1] - values[0]) / (mid - lo)
                second = (values[2] - values[1]) / (hi - mid)
                if abs(first - second) > 1e-9:
                    bad.append(f"{scenario.name}: objective1_s is not affine in the weight scale "
                               f"although the selected journey held — slopes {first!r}, {second!r}")

    # The subdivision *signature*, not an invariance claim. Pass-21 F1's bucket mutant is caught
    # here and nowhere else: merging occurrences also merges the extra vertex subdivision adds, so
    # the measured divergence silently becomes empty. A change in this signature is information.
    divergence = {name for name, _ in measure_split_divergence()}
    if divergence != {"zero_length_segment"}:
        bad.append(f"subdivision divergence is now {sorted(divergence)}, not "
                   "{'zero_length_segment'}")

    bad.extend(_absolute_violations())
    return bad


def _absolute_violations() -> list[str]:
    """The anchors that do not compare two runs. A uniformly wrong implementation satisfies every
    relative invariant, so some checks have to name a number."""
    bad: list[str] = []
    graph = ToyGraph(edges=(_e(0, 1, ((0, 0), (100, 0)), 1000.0, 1000.0),))
    for at in ((50.0, 0.0), (0.0, 0.0), (100.0, 0.0)):
        r = toy.evaluate(graph, at, [at])
        if r.objective1_s is None or abs(r.objective1_s) > 1e-12:
            bad.append(f"coincident origin and destination at {at}: {r.objective1_s!r}, not 0")

    # Both connectors are in both totals, as an absolute number. This replaces the claim pass-22 F3
    # withdrew: a zero intercept is affine and non-negative, so no scaling check could ever have
    # established connector inclusion — and `EXPECTED_COVERAGE` already recorded the connector-free
    # mutant escaping this layer, which should have been read as the refutation it was.
    # Two destinations, one reached over a 100 m connector and one with none. Own costs are
    # 10 + 100/1.26 = 89.3650793651 against 20, so objective 2 must select the second and report
    # 650 s; dropping the connector from cost selects the first and reports 89.3650793651 s.
    connectors = ToyGraph(edges=(_e(0, 1, ((0, 0), (100, 0)), 10.0, 10.0, osmid=(1,)),
                                 _e(0, 2, ((0, 0), (0, -100)), 650.0, 20.0, osmid=(2,))))
    r = toy.evaluate(connectors, (0.0, 0.0), [(100.0, 100.0), (0.0, -100.0)])
    if r.objective2_s is None or abs(r.objective2_s - 650.0) > 1e-9:
        bad.append(f"connector omitted from the cost objective selects on: objective 2 reports "
                   f"{r.objective2_s!r}, not 650.0")
    want = math.fsum((10.0, 100.0 / toy.ACCESS_SPEED_MPS))
    if r.objective1_s is None or abs(r.objective1_s - want) > 1e-9:
        bad.append(f"connector omitted from the reported time: objective 1 reports "
                   f"{r.objective1_s!r}, not {want!r}")

    # Reachability at depth, as named numbers. Adding the chain *scenarios* was not enough on its
    # own and the measurement said so: a mutant that removes journeys makes every reported field
    # `None`, the transform comparisons then find `None` equal to `None`, and the per-result checks
    # are all behind `objective1_s is not None`. **A relative invariant cannot see an absence.** So
    # the hop-depth dimension has to be anchored, which is the same lesson as the cap and the
    # connector: a uniformly wrong implementation satisfies every relative property.
    for depth in CHAIN_DEPTHS:
        scenario = _chain(depth)
        r = scenario.run()
        want = 80.0 * depth
        if r.objective1_s is None:
            bad.append(f"chain of {depth} edges: reported no journey, but its destination is "
                       f"reachable at {want} s — design §2.5 forbids NO_PATH from a bounded search")
        elif abs(r.objective1_s - want) > 1e-9:
            bad.append(f"chain of {depth} edges: {r.objective1_s!r}, not {want!r}")
        elif len(r.objective1_route) != depth:
            bad.append(f"chain of {depth} edges: route has {len(r.objective1_route)} elements, "
                       f"not {depth}")

    for geometry in (((0, 0), (100, 0)), ((0, 0), (50, 10), (100, 0)), ((0, 0), (50, 0), (0, 0))):
        edge = ToyEdge(0, 1, geometry, time_s=1.0, cost_base=1.0, osmid=(7,))
        mirrored = ToyEdge(1, 0, geometry[::-1], time_s=1.0, cost_base=1.0, osmid=(7,))
        if toy.directed_identity(edge, forward=False) != mirrored.identity:
            bad.append(f"reverse identity disagrees with the explicit reverse on {geometry}")
    return bad
