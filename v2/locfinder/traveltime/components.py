"""Keep routing on the connected part of the network.

A mode-filtered OSM extract is full of small disconnected stubs: driveways, parking aisles and
service loops whose connecting ways were removed by the access filter or clipped by the extract
boundary. Measured through the production preparation path, the widened Triangle walk graph has
**3,046** components and drops 13,608 nodes (2.5%). An earlier figure of 4,208 in this docstring
was counted *before* the `degree() == 0` removal that strips isolated nodes; the drive figure of
**1,685** has not been re-measured since.

That matters because nearest-node snapping is geometric, not topological. Snapping RDU Terminal 2
found a node 4 m away on a four-node `highway=service` stub, so three of twelve spot-check journeys
to the airport came back unreachable while Valhalla and OSRM both routed them fine
(docs/experiments/spotcheck-engines.md). The anchor was not unreachable; our snap target was.

`largest_component` prunes to the connected core and **reports what it dropped** rather than hiding
it, because a large drop means the mode filter or the extract boundary is wrong, not that the city
is disconnected.

Limitations, per Codex pass 5 (H6), because this is a policy choice and not a general reachability
repair:

* It uses **weak** connectivity, which ignores edge direction, so a retained one-way branch can
  still fail origin-to-destination reachability. Keeping only the largest *strongly* connected
  component is not a universal fix either: it would discard legitimate one-way approaches and exits.
  Directed reachability to the actual destination set is the real test — **implemented in
  `places/anchor.py` as `CoreReachability` (Phase 1 S2.2)**, which asks whether a directed path runs
  from the largest strongly connected component *to* a candidate node, and is what an anchor or an
  entrance must pass. This function stays as it is: it bounds the graph, and the directed test
  decides usability.
* Separate valid networks — islands, campuses, local path networks — can carry real journeys, and a
  small share of nodes may hold a household's entire neighbourhood. `max_dropped_share` is therefore
  a **useful alarm, not a correctness bound**.
* Pruning does not establish access. A formerly stub-snapped cell may now find a reachable road, or
  may exceed the access-leg cap, or may only reach one by crossing a barrier in a straight line.
  Coverage need not move monotonically, so publish finite-to-missing and missing-to-finite
  transitions with snap displacement rather than assuming an improvement.
"""
from __future__ import annotations

from dataclasses import dataclass

import networkx as nx


@dataclass(frozen=True)
class ComponentReport:
    n_components: int
    kept_nodes: int
    dropped_nodes: int
    largest_share: float

    @property
    def summary(self) -> str:
        return (f"{self.n_components} components; kept {self.kept_nodes} nodes "
                f"({self.largest_share:.1%}), dropped {self.dropped_nodes}")


def component_report(G: nx.MultiDiGraph) -> ComponentReport:
    comps = list(nx.weakly_connected_components(G)) if G.is_directed() else list(nx.connected_components(G))
    if not comps:
        return ComponentReport(0, 0, 0, 0.0)
    largest = max(comps, key=len)
    total = G.number_of_nodes()
    return ComponentReport(len(comps), len(largest), total - len(largest), len(largest) / total)


def largest_component(G: nx.MultiDiGraph, *, max_dropped_share: float = 0.10) -> tuple[nx.MultiDiGraph, ComponentReport]:
    """Return the subgraph on the largest weakly-connected component, plus a report.

    Raises if more than `max_dropped_share` of nodes would be discarded: that is a sign the mode
    filter removed something structural, not that the network has stubs.
    """
    rep = component_report(G)
    if rep.kept_nodes == 0:
        raise ValueError("graph has no nodes")
    dropped_share = rep.dropped_nodes / (rep.kept_nodes + rep.dropped_nodes)
    if dropped_share > max_dropped_share:
        raise ValueError(
            f"largest component holds only {rep.largest_share:.1%} of nodes "
            f"({rep.dropped_nodes} would be dropped); check the mode filter and the extract bounds"
        )
    comps = list(nx.weakly_connected_components(G)) if G.is_directed() else list(nx.connected_components(G))
    keep = max(comps, key=len)
    return G.subgraph(keep).copy(), rep
