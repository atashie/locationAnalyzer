import math

import networkx as nx
from scipy.sparse.csgraph import dijkstra

from locfinder.traveltime.arrival import arrival_seconds
from locfinder.traveltime.csr import graph_to_csr


def one_way_graph() -> nx.MultiDiGraph:
    """A -> B (60 s, one-way), B <-> C (30 s each way)."""
    G = nx.MultiDiGraph()
    for n, (x, y) in {"A": (0, 0), "B": (100, 0), "C": (200, 0)}.items():
        G.add_node(n, x=x, y=y)
    G.add_edge("A", "B", travel_time=60.0)
    G.add_edge("B", "C", travel_time=30.0)
    G.add_edge("C", "B", travel_time=30.0)
    return G


def test_csr_preserves_direction_and_weights():
    G = one_way_graph()
    csr, index = graph_to_csr(G, weight="travel_time")
    a, b, c = index["A"], index["B"], index["C"]
    assert csr[a, b] == 60.0
    assert csr[b, a] == 0.0  # no reverse edge stored
    assert csr[b, c] == 30.0 and csr[c, b] == 30.0


def test_parallel_edges_keep_the_minimum_weight():
    G = one_way_graph()
    G.add_edge("A", "B", travel_time=90.0)  # slower parallel edge
    csr, index = graph_to_csr(G, weight="travel_time")
    assert csr[index["A"], index["B"]] == 60.0


def test_arrival_to_destination_uses_transposed_graph():
    G = one_way_graph()
    csr, index = graph_to_csr(G, weight="travel_time")
    # destination B: A reaches B in 60 (A->B), C reaches B in 30 (C->B)
    t = arrival_seconds(csr, dest_idx=[index["B"]])
    assert t[index["A"]] == 60.0
    assert t[index["C"]] == 30.0
    assert t[index["B"]] == 0.0


def test_one_way_street_is_not_reversible():
    G = one_way_graph()
    csr, index = graph_to_csr(G, weight="travel_time")
    # destination A: nobody can reach A (A->B is one-way)
    t = arrival_seconds(csr, dest_idx=[index["A"]])
    assert t[index["A"]] == 0.0
    assert math.isinf(t[index["B"]]) and math.isinf(t[index["C"]])


def test_naive_outward_dijkstra_would_be_wrong():
    """Documents the CHCCS bug: an OUTWARD search from the destination says B is
    60 s from A, but B cannot reach A at all on the one-way graph."""
    G = one_way_graph()
    csr, index = graph_to_csr(G, weight="travel_time")
    outward = dijkstra(csr, directed=True, indices=[index["A"]], min_only=True)
    assert outward[index["B"]] == 60.0
    correct = arrival_seconds(csr, dest_idx=[index["A"]])
    assert math.isinf(correct[index["B"]])


def test_multi_source_takes_minimum_and_respects_cutoff():
    G = one_way_graph()
    csr, index = graph_to_csr(G, weight="travel_time")
    t = arrival_seconds(csr, dest_idx=[index["B"], index["C"]], cutoff_s=45.0)
    assert t[index["C"]] == 0.0 and t[index["B"]] == 0.0
    assert math.isinf(t[index["A"]])  # 60 s > cutoff 45 s


def test_empty_destinations_are_all_unreachable():
    G = one_way_graph()
    csr, index = graph_to_csr(G, weight="travel_time")
    t = arrival_seconds(csr, dest_idx=[])
    assert t.shape == (3,) and all(math.isinf(v) for v in t)
