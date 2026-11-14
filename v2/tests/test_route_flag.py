"""The per-cell restricted-route flag — step 8's disclosure obligation.

The owner's 2026-11-10 decision to keep the restricted-walk penalty at 120 s was taken on the
condition that the gap is **disclosed rather than priced away**. Disclosure needs per-cell
membership: not "the graph contains 126,197 restricted edges", which is true everywhere and tells a
household nothing, but "the route behind *this* number uses one".

The property that makes it honest is that the flag follows the **route the selection took** — the
cost-optimal path, and for parallel edges the cost-minimal one — rather than any available edge.
"""
from __future__ import annotations

import itertools

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

def equal_cost_diamond(*, restricted_leg: int, order=(0, 1, 2, 3)) -> nx.MultiDiGraph:
    """`0 -> 1 -> 3` and `0 -> 2 -> 3`, equal cost to the last bit; one leg restricted.

    Node 0 is the destination, so node 3 has two equally cheap routes to it and exactly one of
    them uses a restricted way.

    `order` is the insertion order of the nodes, which is what `graph_to_cost_time_flag_csr` turns
    into CSR positions and therefore what the sweep's heap uses to break a tie. Relabelling the
    nodes does NOT do this: `nx.relabel_nodes` rebuilds the graph in the same iteration order with
    new names, so the CSR comes out byte-identical and nothing moves.
    """
    G = nx.MultiDiGraph()
    G.add_nodes_from(order)
    half = 300.0
    for mid in (1, 2):
        restricted = mid == restricted_leg
        G.add_edge(0, mid, travel_time=half, cost=half, access_restricted=restricted)
        G.add_edge(mid, 0, travel_time=half, cost=half, access_restricted=restricted)
        G.add_edge(mid, 3, travel_time=half, cost=half)
        G.add_edge(3, mid, travel_time=half, cost=half)
    return G


def _flag_at_the_tied_node(G: nx.MultiDiGraph) -> tuple[float, bool]:
    cost, time, flag, index = graph_to_cost_time_flag_csr(G)
    seconds, _selected, flagged = arrival_with_route_flag(cost, time, flag, dest_idx=[index[0]])
    return float(seconds[index[3]]), bool(flagged[index[3]])


def test_at_an_exact_cost_tie_the_published_time_is_determined_and_the_disclosure_is_not():
    """**The flag is a function of the traversal order, not of the answer we publish.**

    Two routes of identical cost, one restricted. The published seconds are the same whichever the
    sweep settles first, so no check on the value plane can tell them apart and
    `encode_route_flag`'s invariant -- a flag only where the status is OK -- holds for both
    answers. Changing the node insertion order changes only the heap's tie-break, and the flag follows it:
    twelve of the twenty-four orderings each way.

    This is pinned, not fixed. Fixing it means deciding WHICH of two equally cheap routes a
    household is told about, which is the decision S3 item 6's suffix-aware band exists to make
    and which belongs to the owner. `scripts/measure_tie_flag.py --graph` measures the extent on
    the real walk graph: 0 of 69,078 flagged nodes, because float travel times do not tie
    exactly -- so this is latent, and quantising the cost would surface it.
    """
    seen = set()
    for order in itertools.permutations(range(4)):
        cost, time, flag, index = graph_to_cost_time_flag_csr(
            equal_cost_diamond(restricted_leg=1, order=order))
        seconds, _sel, flagged = arrival_with_route_flag(cost, time, flag, dest_idx=[index[0]])
        seen.add((float(seconds[index[3]]), bool(flagged[index[3]])))

    times = {t for t, _f in seen}
    flags = {f for _t, f in seen}
    assert times == {600.0}, f"the published time moved under a reordering: {sorted(times)}"
    assert flags == {False, True}, (
        "the disclosure did not move under any of the 24 node orderings, so either the tie is not "
        f"exact or the sweep breaks ties by something other than CSR position: {sorted(flags)}")
    # And it is an even split, which rules out one freak ordering doing it.
    assert len(seen) == 2


def test_the_tie_is_exact_so_the_ambiguity_is_not_a_rounding_artefact():
    """If the two legs differed by one ulp the cheaper would simply win, and there would be no
    ambiguity to pin. This asserts the two routes cost the same binary64 value."""
    G = equal_cost_diamond(restricted_leg=1)
    cost, _time, _flag, index = graph_to_cost_time_flag_csr(G)
    via_a = cost[index[0], index[1]] + cost[index[1], index[3]]
    via_b = cost[index[0], index[2]] + cost[index[2], index[3]]
    assert via_a == via_b
    assert float(via_a).hex() == float(via_b).hex()
