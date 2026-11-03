"""Keep routing on the connected part of the network.

A mode-filtered OSM extract is full of small disconnected stubs: driveways, parking aisles and
service loops whose connecting ways were removed by the access filter or clipped by the extract
boundary. The widened Triangle walk graph has **4,208** components and the drive graph **1,685**,
with the largest holding 97-99% of nodes.

That matters because nearest-node snapping is geometric, not topological. Snapping RDU Terminal 2
found a node 4 m away on a four-node `highway=service` stub, so three of twelve spot-check journeys
to the airport came back unreachable while Valhalla and OSRM both routed them fine
(docs/experiments/spotcheck-engines.md). The anchor was not unreachable; our snap target was.

`largest_component` prunes to the connected core and **reports what it dropped** rather than hiding
it, because a large drop means the mode filter or the extract boundary is wrong, not that the city
is disconnected.
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
