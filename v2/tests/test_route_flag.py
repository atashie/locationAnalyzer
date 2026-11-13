"""The per-cell restricted-route flag — step 8's disclosure obligation.

The owner's 2026-11-10 decision to keep the restricted-walk penalty at 120 s was taken on the
condition that the gap is **disclosed rather than priced away**. Disclosure needs per-cell
membership: not "the graph contains 126,197 restricted edges", which is true everywhere and tells a
household nothing, but "the route behind *this* number uses one".

The property that makes it honest is that the flag follows the **route the selection took** — the
cost-optimal path, and for parallel edges the cost-minimal one — rather than any available edge.
"""
from __future__ import annotations

import networkx as nx
import numpy as np
import pytest

from locfinder.traveltime.arrival import (arrival_with_route_flag,
                                          arrival_with_selected_destination)
from locfinder.traveltime.csr import graph_to_cost_time_csr, graph_to_cost_time_flag_csr


def chain(*, restricted_hop: bool) -> nx.MultiDiGraph:
    """`0 -> 1 -> 2`, with the first hop optionally restricted. Node 2 is the destination."""
    G = nx.MultiDiGraph()
    G.add_edge(0, 1, travel_time=60.0, cost=60.0, access_restricted=restricted_hop)
    G.add_edge(1, 2, travel_time=60.0, cost=60.0)
    return G


def test_a_node_is_flagged_exactly_when_its_chosen_path_uses_a_restricted_edge():
    for restricted in (False, True):
        cost, time, flag, index = graph_to_cost_time_flag_csr(chain(restricted_hop=restricted))
        seconds, selected, flagged = arrival_with_route_flag(
            cost, time, flag, dest_idx=[index[2]])
        assert list(seconds) == [120.0, 60.0, 0.0]
        assert bool(flagged[index[0]]) is restricted
        # Node 1's own path is the unrestricted second hop either way.
        assert bool(flagged[index[1]]) is False
        assert bool(flagged[index[2]]) is False


def test_the_flag_follows_the_cost_minimal_parallel_edge_and_not_merely_an_available_one():
    """A household's journey uses one of two parallel ways, and cost decides which. "Any parallel
    edge is restricted" would be a different and wrong claim — it would flag a cell whose route
    never touches the restricted way."""
    G = nx.MultiDiGraph()
    # Two ways from 0 to 1. The cheap one is open; the dear one is restricted.
    G.add_edge(0, 1, travel_time=60.0, cost=60.0, access_restricted=False)
    G.add_edge(0, 1, travel_time=10.0, cost=600.0, access_restricted=True)
    G.add_edge(1, 2, travel_time=60.0, cost=60.0)
    cost, time, flag, index = graph_to_cost_time_flag_csr(G)
    seconds, _sel, flagged = arrival_with_route_flag(cost, time, flag, dest_idx=[index[2]])
    # The cheap open edge is selected, so the reported time is its 60 s and the cell is NOT flagged
    # even though a restricted parallel way exists.
    assert seconds[index[0]] == 120.0
    assert bool(flagged[index[0]]) is False


def test_when_the_restricted_way_is_the_cheap_one_the_cell_is_flagged_and_keeps_its_real_time():
    """The audited journey's shape: a penalised private track still wins on cost, and the reported
    minutes must stay the real ones. That is the whole reason cost and time are separate — and it
    is exactly the case a household must be told about."""
    G = nx.MultiDiGraph()
    # The track is fast but penalised; the detour is slow and open. 60 + 120 beats 400.
    G.add_edge(0, 1, travel_time=60.0, cost=180.0, access_restricted=True)
    G.add_edge(0, 1, travel_time=400.0, cost=400.0, access_restricted=False)
    G.add_edge(1, 2, travel_time=60.0, cost=60.0)
    cost, time, flag, index = graph_to_cost_time_flag_csr(G)
    seconds, _sel, flagged = arrival_with_route_flag(cost, time, flag, dest_idx=[index[2]])
    assert seconds[index[0]] == 120.0, "the penalty must not inflate the reported minutes"
    assert bool(flagged[index[0]]) is True


def test_the_flag_is_not_monotone_in_cost_which_is_why_it_must_be_carried_not_inferred():
    """A cheaper path can be flagged where a dearer one is not, so no bound on cost or time
    implies anything about the flag. Instance twenty-two: do not assert a direction of effect
    between a selected quantity and a reported one."""
    G = nx.MultiDiGraph()
    G.add_edge(0, 9, travel_time=10.0, cost=10.0, access_restricted=True)    # cheap, restricted
    G.add_edge(0, 8, travel_time=10.0, cost=1000.0, access_restricted=False)  # dear, open
    G.add_edge(9, 2, travel_time=10.0, cost=10.0)
    G.add_edge(8, 2, travel_time=10.0, cost=10.0)
    cost, time, flag, index = graph_to_cost_time_flag_csr(G)
    _s, _sel, flagged = arrival_with_route_flag(cost, time, flag, dest_idx=[index[2]])
    assert bool(flagged[index[0]]) is True, "the cheapest route is the restricted one"


def test_an_unreachable_node_asserts_nothing_about_a_route():
    G = nx.MultiDiGraph()
    G.add_edge(0, 1, travel_time=60.0, cost=60.0, access_restricted=True)
    G.add_node(7)
    cost, time, flag, index = graph_to_cost_time_flag_csr(G)
    seconds, selected, flagged = arrival_with_route_flag(cost, time, flag, dest_idx=[index[1]])
    assert not np.isfinite(seconds[index[7]])
    assert selected[index[7]] == -1
    assert bool(flagged[index[7]]) is False


def test_a_node_cut_by_the_cutoff_discloses_no_route():
    """The cutoff is applied to the reported time, so a node past it has no answer — and therefore
    no route to describe. A flag left set there would be an assertion about a journey the product
    does not publish."""
    cost, time, flag, index = graph_to_cost_time_flag_csr(chain(restricted_hop=True))
    seconds, selected, flagged = arrival_with_route_flag(
        cost, time, flag, dest_idx=[index[2]], cutoff_s=90.0)
    assert not np.isfinite(seconds[index[0]])
    assert selected[index[0]] == -1
    assert bool(flagged[index[0]]) is False


def test_the_refactor_did_not_change_the_seconds_or_the_selected_destination():
    """`arrival_with_selected_destination` now delegates to the shared sweep. Its two outputs must
    be identical to what the old body produced, which is what the rest of the suite relies on."""
    G = chain(restricted_hop=True)
    cost2, time2, index2 = graph_to_cost_time_csr(G)
    cost3, time3, flag3, index3 = graph_to_cost_time_flag_csr(G)
    assert index2 == index3
    a_sec, a_sel = arrival_with_selected_destination(cost2, time2, dest_idx=[index2[2]])
    b_sec, b_sel, _f = arrival_with_route_flag(cost3, time3, flag3, dest_idx=[index3[2]])
    assert np.array_equal(a_sec, b_sec)
    assert np.array_equal(a_sel, b_sel)


def test_a_flag_matrix_of_the_wrong_shape_is_refused():
    import scipy.sparse as sp
    cost, time, _flag, index = graph_to_cost_time_flag_csr(chain(restricted_hop=False))
    with pytest.raises(ValueError, match="must match cost"):
        arrival_with_route_flag(cost, time, sp.csr_matrix((2, 2)), dest_idx=[index[2]])


def test_a_graph_with_no_flagged_edges_flags_nothing():
    cost, time, flag, index = graph_to_cost_time_flag_csr(chain(restricted_hop=False))
    _s, _sel, flagged = arrival_with_route_flag(cost, time, flag, dest_idx=[index[2]])
    assert not flagged.any()


# --------------------------------------------------------------------------- per-point resolution


def two_edge_graph(*, first_restricted: bool):
    """`0 -(geometry)- 1 -> 2`, so a point attaching mid-first-edge walks along it to node 1."""
    G = nx.MultiDiGraph()
    G.add_node(0, x=0.0, y=0.0)
    G.add_node(1, x=100.0, y=0.0)
    G.add_node(2, x=200.0, y=0.0)
    from shapely.geometry import LineString
    G.add_edge(0, 1, travel_time=100.0, cost=100.0, access_restricted=first_restricted,
               geometry=LineString([(0.0, 0.0), (100.0, 0.0)]))
    G.add_edge(1, 0, travel_time=100.0, cost=100.0, access_restricted=first_restricted,
               geometry=LineString([(100.0, 0.0), (0.0, 0.0)]))
    G.add_edge(1, 2, travel_time=50.0, cost=50.0,
               geometry=LineString([(100.0, 0.0), (200.0, 0.0)]))
    G.add_edge(2, 1, travel_time=50.0, cost=50.0,
               geometry=LineString([(200.0, 0.0), (100.0, 0.0)]))
    return G


@pytest.mark.parametrize("first_restricted", [False, True])
def test_the_matched_edge_counts_toward_the_flag_not_only_the_network_beyond_it(first_restricted):
    """The audited walk's own shape: the household walks along a private approach *before*
    reaching any node. A flag that looked only at the node's onward route would miss it."""
    from locfinder.traveltime.snap import EdgeIndex, cell_route_flag
    G = two_edge_graph(first_restricted=first_restricted)
    cost, time, flag, index = graph_to_cost_time_flag_csr(G)
    seconds, _sel, node_flag = arrival_with_route_flag(cost, time, flag, dest_idx=[index[2]])
    # Node 1's onward route (1 -> 2) is never restricted, so any flag here is the matched edge's.
    assert bool(node_flag[index[1]]) is False
    idx = EdgeIndex.from_graph(G, index)
    got = cell_route_flag(idx, seconds, np.array([50.0]), np.array([5.0]),
                          mode="walk", max_access_m=200.0, node_flag=node_flag)
    assert bool(got[0]) is first_restricted


def test_a_point_with_no_published_time_is_not_flagged():
    from locfinder.traveltime.snap import EdgeIndex, cell_route_flag
    G = two_edge_graph(first_restricted=True)
    cost, time, flag, index = graph_to_cost_time_flag_csr(G)
    seconds, _sel, node_flag = arrival_with_route_flag(cost, time, flag, dest_idx=[index[2]])
    idx = EdgeIndex.from_graph(G, index)
    # 10 km away: beyond any access cap, so there is no journey to describe.
    got = cell_route_flag(idx, seconds, np.array([50.0]), np.array([10000.0]),
                          mode="walk", max_access_m=200.0, node_flag=node_flag)
    assert bool(got[0]) is False


def test_a_node_flag_of_the_wrong_length_is_refused():
    from locfinder.traveltime.snap import EdgeIndex, cell_route_flag
    G = two_edge_graph(first_restricted=False)
    cost, time, flag, index = graph_to_cost_time_flag_csr(G)
    seconds, _sel, _nf = arrival_with_route_flag(cost, time, flag, dest_idx=[index[2]])
    idx = EdgeIndex.from_graph(G, index)
    with pytest.raises(ValueError, match="to match the node"):
        cell_route_flag(idx, seconds, np.array([50.0]), np.array([5.0]), mode="walk",
                        max_access_m=200.0, node_flag=np.zeros(2, dtype=bool))


def test_a_point_at_an_endpoint_walks_none_of_the_matched_edge_and_discloses_none_of_it():
    """Pass 46 F3. A journey existing is not the same as any of the matched edge being walked.
    `_snap_network` permits zero on-edge travel at an endpoint — walking toward `e_idx` covers
    `1 - frac`, which is nothing when the point *is* `e_idx` — so a household standing on its
    destination node must not be told its route depends on the way leading to it."""
    from locfinder.traveltime.snap import (EdgeIndex, cell_route_flag,
                                           cell_seconds_from_arrival)
    G = nx.MultiDiGraph()
    G.add_node(0, x=0.0, y=0.0)
    G.add_node(1, x=100.0, y=0.0)
    G.add_edge(0, 1, travel_time=100.0, cost=220.0, access_restricted=True)
    idx = EdgeIndex.from_graph(G, {0: 0, 1: 1})
    x, y = np.array([0.0, 50.0, 100.0]), np.zeros(3)
    kw = dict(mode="walk", max_access_m=200.0, node_cost=np.array([220.0, 0.0]))
    seconds = cell_seconds_from_arrival(idx, np.array([100.0, 0.0]), x, y, **kw)
    flags = cell_route_flag(idx, np.array([100.0, 0.0]), x, y,
                            node_flag=np.array([True, False]), **kw)
    assert list(seconds) == [100.0, 50.0, 0.0]
    # At x=0 the whole restricted edge is walked; mid-edge, half of it; at x=100, none of it.
    assert [bool(f) for f in flags] == [True, True, False]
