import networkx as nx
import pytest

from locfinder.traveltime.components import component_report, largest_component


def graph_with_stub(stub_nodes: int = 2, main_nodes: int = 20) -> nx.MultiDiGraph:
    G = nx.MultiDiGraph()
    for i in range(main_nodes):
        G.add_node(f"m{i}", x=float(i), y=0.0)
        if i:
            G.add_edge(f"m{i-1}", f"m{i}", travel_time=10.0)
            G.add_edge(f"m{i}", f"m{i-1}", travel_time=10.0)
    for j in range(stub_nodes):
        G.add_node(f"s{j}", x=1000.0 + j, y=1000.0)
        if j:
            G.add_edge(f"s{j-1}", f"s{j}", travel_time=10.0)
    return G


def test_report_counts_components_and_share():
    r = component_report(graph_with_stub(stub_nodes=2, main_nodes=20))
    assert r.n_components == 2
    assert r.kept_nodes == 20 and r.dropped_nodes == 2
    assert r.largest_share == pytest.approx(20 / 22)
    assert "2 components" in r.summary


def test_largest_component_drops_the_stub():
    G, r = largest_component(graph_with_stub())
    assert G.number_of_nodes() == 20
    assert all(not n.startswith("s") for n in G.nodes())
    assert r.dropped_nodes == 2


def test_refuses_to_prune_when_the_graph_is_mostly_fragments():
    """A large drop means the mode filter or the extract bounds are wrong, not that the city is."""
    G = graph_with_stub(stub_nodes=30, main_nodes=20)
    with pytest.raises(ValueError, match="largest component holds only"):
        largest_component(G)


def test_threshold_can_be_relaxed_deliberately():
    G, r = largest_component(graph_with_stub(stub_nodes=30, main_nodes=20), max_dropped_share=0.9)
    assert G.number_of_nodes() == 30  # the stub chain is now the largest


def test_the_airport_failure_mode_is_what_this_prevents():
    """A node that is geometrically nearest but topologically marooned must not survive pruning,
    which is exactly how RDU Terminal 2 became unreachable in the drive spot check."""
    G = graph_with_stub(stub_nodes=4, main_nodes=50)
    marooned = "s0"
    assert marooned in G
    pruned, _ = largest_component(G)
    assert marooned not in pruned


def test_empty_graph_raises():
    with pytest.raises(ValueError, match="no nodes"):
        largest_component(nx.MultiDiGraph())


def test_undirected_graphs_are_handled():
    r = component_report(nx.Graph([(1, 2), (3, 4)]))
    assert r.n_components == 2
