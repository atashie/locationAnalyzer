"""Attaching a destination to an EDGE rather than only to a node.

The layer builder snaps a destination to its nearest graph NODE and drops it beyond 300 m. Pass 57
measured what that bound actually excludes: park record #456 is 356.44 m from the nearest node and
**0.17 m from the nearest edge**, so it is dropped while sitting on a road. Six of the seven dropped
park records have an edge within 300 m, and **none of the six projects within a metre of an
existing endpoint** -- so every recovery needs the edge split, and the nearest endpoint is never a
usable stand-in.

Splitting is the thing pass 56 proved is not free. `speeds.py` charges the restricted-access
penalty PER EDGE, so a naive split of a restricted edge charges it TWICE and makes every journey
through that edge dearer. One of the six matched edges is restricted, so this is not hypothetical.

The rule these tests pin down is the one `snap.py` already uses for an origin's partial edge:
**prorate the whole cost by the fraction**. A split is then exactly cost-neutral and time-neutral
for any journey traversing the original edge.
"""
import networkx as nx
import pytest

from locfinder.traveltime.attach import split_edge_at
from locfinder.traveltime.csr import graph_to_cost_time_csr

PEN = 120.0


def restricted_edge_graph() -> nx.MultiDiGraph:
    """S->E, 100 m of private track: 100 s to walk, 120 s of penalty, so 220 s of cost."""
    G = nx.MultiDiGraph()
    G.add_node("S", x=0.0, y=0.0)
    G.add_node("E", x=100.0, y=0.0)
    for u, v in (("S", "E"), ("E", "S")):
        G.add_edge(u, v, length=100.0, travel_time=100.0, cost=100.0 + PEN,
                   access_restricted=True)
    return G


def test_splitting_a_restricted_edge_does_not_charge_its_penalty_twice():
    """The pass-56 hazard, as a test. 220 s of cost in must be 220 s of cost out."""
    G = restricted_edge_graph()
    before = G["S"]["E"][0]["cost"]

    new = split_edge_at(G, "S", "E", 0.25)

    halves = [G["S"][new][0], G[new]["E"][0]]
    assert sum(h["cost"] for h in halves) == pytest.approx(before), (
        f"a split charged {sum(h['cost'] for h in halves)} s where the whole edge charged {before}")


def test_a_split_preserves_length_and_travel_time():
    G = restricted_edge_graph()
    new = split_edge_at(G, "S", "E", 0.25)
    halves = [G["S"][new][0], G[new]["E"][0]]
    assert sum(h["length"] for h in halves) == pytest.approx(100.0)
    assert sum(h["travel_time"] for h in halves) == pytest.approx(100.0)
    assert G["S"][new][0]["length"] == pytest.approx(25.0)


def test_the_new_node_sits_at_the_projected_fraction():
    G = restricted_edge_graph()
    new = split_edge_at(G, "S", "E", 0.25)
    assert G.nodes[new]["x"] == pytest.approx(25.0)
    assert G.nodes[new]["y"] == pytest.approx(0.0)


def test_both_halves_still_disclose_the_restriction():
    """The flag is a disclosure about the ground, so both halves carry it even though the
    penalty is shared between them."""
    G = restricted_edge_graph()
    new = split_edge_at(G, "S", "E", 0.25)
    assert G["S"][new][0]["access_restricted"] is True
    assert G[new]["E"][0]["access_restricted"] is True


def test_the_reverse_direction_is_split_too():
    """The walk graph is symmetrised, so an unsplit reverse edge would leave a one-way stub."""
    G = restricted_edge_graph()
    new = split_edge_at(G, "S", "E", 0.25)
    assert G.has_edge("E", new) and G.has_edge(new, "S")
    assert G["E"][new][0]["length"] == pytest.approx(75.0)
    assert G[new]["S"][0]["length"] == pytest.approx(25.0)


def test_an_unrestricted_edge_splits_without_inventing_a_flag():
    G = nx.MultiDiGraph()
    G.add_node("S", x=0.0, y=0.0)
    G.add_node("E", x=100.0, y=0.0)
    G.add_edge("S", "E", length=100.0, travel_time=100.0, cost=100.0)
    new = split_edge_at(G, "S", "E", 0.5)
    assert not G["S"][new][0].get("access_restricted")
    assert G["S"][new][0]["cost"] == pytest.approx(50.0)


def test_a_journey_through_a_split_restricted_edge_costs_what_it_did_before():
    """The property that makes the fallback churn-free, end to end through the CSR."""
    G = restricted_edge_graph()
    cost_before, _time_before, index = graph_to_cost_time_csr(G)
    whole = cost_before[index["S"], index["E"]]

    split_edge_at(G, "S", "E", 0.25)

    cost_after, _t, idx2 = graph_to_cost_time_csr(G)
    import scipy.sparse.csgraph as csgraph
    d = csgraph.dijkstra(cost_after, indices=[idx2["S"]])
    assert d[0][idx2["E"]] == pytest.approx(whole), (
        f"S->E cost {d[0][idx2['E']]} after the split, {whole} before")


def test_splitting_at_an_endpoint_is_refused():
    """Fraction 0 or 1 is already a node; a zero-length half would be a trap for the snapper."""
    G = restricted_edge_graph()
    for f in (0.0, 1.0):
        with pytest.raises(ValueError):
            split_edge_at(G, "S", "E", f)


def test_a_split_uses_the_edge_geometry_when_one_is_present():
    """Real OSM edges carry a `geometry`; the midpoint of a dog-leg is not the midpoint of the
    straight line between its endpoints."""
    from shapely.geometry import LineString
    G = nx.MultiDiGraph()
    G.add_node("S", x=0.0, y=0.0)
    G.add_node("E", x=100.0, y=0.0)
    geom = LineString([(0.0, 0.0), (50.0, 50.0), (100.0, 0.0)])
    for u, v in (("S", "E"), ("E", "S")):
        G.add_edge(u, v, length=geom.length, travel_time=geom.length, cost=geom.length,
                   geometry=geom)
    new = split_edge_at(G, "S", "E", 0.5)
    assert G.nodes[new]["x"] == pytest.approx(50.0)
    assert G.nodes[new]["y"] == pytest.approx(50.0)


# ---------------------------------------------------------------------------------------------
# The fallback itself: find the nearest edge, and attach only where the node rule already failed.

def two_road_graph() -> nx.MultiDiGraph:
    """A 200 m road from (0,0) to (200,0), and a far-away one, with no junction between."""
    G = nx.MultiDiGraph()
    G.add_node("A", x=0.0, y=0.0)
    G.add_node("B", x=200.0, y=0.0)
    G.add_node("C", x=0.0, y=1000.0)
    G.add_node("D", x=200.0, y=1000.0)
    for u, v in (("A", "B"), ("B", "A"), ("C", "D"), ("D", "C")):
        G.add_edge(u, v, length=200.0, travel_time=200.0, cost=200.0)
    return G


def test_the_fallback_attaches_a_point_whose_nearest_node_is_too_far():
    """(100, 20): 102 m from each endpoint of A-B, but only 20 m from the road itself."""
    from shapely.geometry import Point
    from locfinder.traveltime.attach import attach_points_to_edges

    G = two_road_graph()
    attached = attach_points_to_edges(G, [Point(100.0, 20.0)], max_m=50.0)

    assert len(attached) == 1
    node = attached[0]
    assert G.nodes[node]["x"] == pytest.approx(100.0)
    assert G.nodes[node]["y"] == pytest.approx(0.0)


def test_the_fallback_refuses_a_point_beyond_the_cap():
    from shapely.geometry import Point
    from locfinder.traveltime.attach import attach_points_to_edges

    G = two_road_graph()
    n_before = G.number_of_nodes()
    attached = attach_points_to_edges(G, [Point(100.0, 400.0)], max_m=50.0)
    assert attached == [None]
    assert G.number_of_nodes() == n_before, "a refused point still changed the graph"


def test_two_destinations_on_one_edge_both_attach_at_the_right_places():
    """The second point must land on whichever half now carries it, not on a removed edge."""
    from shapely.geometry import Point
    from locfinder.traveltime.attach import attach_points_to_edges

    G = two_road_graph()
    attached = attach_points_to_edges(G, [Point(150.0, 5.0), Point(50.0, 5.0)], max_m=50.0)

    assert all(a is not None for a in attached)
    assert G.nodes[attached[0]]["x"] == pytest.approx(150.0)
    assert G.nodes[attached[1]]["x"] == pytest.approx(50.0)
    # And the road is still 200 m end to end, in three pieces.
    import scipy.sparse.csgraph as csgraph
    cost, _t, idx = graph_to_cost_time_csr(G)
    d = csgraph.dijkstra(cost, indices=[idx["A"]])
    assert d[0][idx["B"]] == pytest.approx(200.0)


def test_the_fallback_does_not_touch_the_rest_of_the_graph():
    from shapely.geometry import Point
    from locfinder.traveltime.attach import attach_points_to_edges

    G = two_road_graph()
    before = {(u, v): dict(d) for u, v, d in G.edges(data=True) if {u, v} == {"C", "D"}}
    attach_points_to_edges(G, [Point(100.0, 20.0)], max_m=50.0)
    after = {(u, v): dict(d) for u, v, d in G.edges(data=True) if {u, v} == {"C", "D"}}
    assert before == after


def test_a_parallel_edge_that_projects_to_its_own_endpoint_is_left_whole():
    """Caught by `graph_to_cost_time_csr`'s validator on the real Triangle graph.

    Two nodes can be joined by more than one physical way. The split point is chosen on the
    nearest geometry, but a PARALLEL way between the same pair can have a shape on which that
    point projects to an end -- a loop or a stub -- and cutting there makes a zero-length half
    with `travel_time=0.0`, which the CSR rejects outright:

        ValueError: edge 7110291587->14341115166 has non-positive or non-finite travel_time=0.0

    Leaving that parallel edge whole is correct, not a compromise: `u` and `v` both still exist
    after the split, so `u -> v` remains a real connection alongside `u -> new -> v`.
    """
    from shapely.geometry import LineString
    G = nx.MultiDiGraph()
    G.add_node("S", x=0.0, y=0.0)
    G.add_node("E", x=100.0, y=0.0)
    straight = LineString([(0.0, 0.0), (100.0, 0.0)])
    # A loop leaving and returning to S before running to E: the midpoint of `straight`
    # projects onto its very start.
    loop = LineString([(0.0, 0.0), (-80.0, 60.0), (-80.0, -60.0), (0.0, 0.0)])
    G.add_edge("S", "E", length=100.0, travel_time=100.0, cost=100.0, geometry=straight)
    G.add_edge("S", "S", length=loop.length, travel_time=loop.length, cost=loop.length,
               geometry=loop)
    G.add_edge("E", "S", length=100.0, travel_time=100.0, cost=100.0,
               geometry=LineString([(100.0, 0.0), (0.0, 0.0)]))

    split_edge_at(G, "S", "E", 0.5)

    for u, v, d in G.edges(data=True):
        assert d["travel_time"] > 0.0, f"edge {u}->{v} has travel_time={d['travel_time']}"
        assert d["length"] > 0.0, f"edge {u}->{v} has length={d['length']}"
    graph_to_cost_time_csr(G)  # must not raise


def test_parallel_ways_between_the_same_nodes_do_not_make_a_zero_length_half():
    """Two different ways join S and E. The split point belongs to ONE of them.

    `split_edge_at` used to re-derive the point from whichever parallel edge `get_edge_data`
    happened to yield first, so the fraction measured on the matched way was applied to a
    different shape -- and on a long detour way, fraction 0.5 of the straight way projects onto
    its end. That is the real source of `travel_time=0.0`.
    """
    from shapely.geometry import LineString, Point
    from locfinder.traveltime.attach import attach_points_to_edges

    G = nx.MultiDiGraph()
    G.add_node("S", x=0.0, y=0.0)
    G.add_node("E", x=100.0, y=0.0)
    straight = LineString([(0.0, 0.0), (100.0, 0.0)])
    detour = LineString([(0.0, 0.0), (0.0, -400.0), (100.0, -400.0), (100.0, 0.0)])
    for geom in (straight, detour):
        for u, v, g in (("S", "E", geom), ("E", "S", LineString(list(geom.coords)[::-1]))):
            G.add_edge(u, v, length=g.length, travel_time=g.length, cost=g.length, geometry=g)

    attach_points_to_edges(G, [Point(50.0, 3.0)], max_m=50.0)

    for u, v, d in G.edges(data=True):
        assert d["travel_time"] > 0.0, f"edge {u}->{v} has travel_time={d['travel_time']}"
        assert d["length"] > 0.0, f"edge {u}->{v} has length={d['length']}"
    graph_to_cost_time_csr(G)  # must not raise
