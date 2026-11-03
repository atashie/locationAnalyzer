"""Path selection on cost, reporting on real time: the behaviour that lets a restricted driveway
cost extra to choose without inflating the minutes a user sees."""
import math

import networkx as nx
import numpy as np
import pytest

from locfinder.traveltime.access import RESTRICTED_PENALTY_S
from locfinder.traveltime.arrival import arrival_seconds, arrival_seconds_two_weight
from locfinder.traveltime.csr import graph_to_cost_time_csr, graph_to_csr
from locfinder.traveltime.speeds import add_travel_times, symmetrise


def edge(G, u, v, *, time, cost=None, both=False):
    G.add_edge(u, v, travel_time=time, cost=time if cost is None else cost)
    if both:
        G.add_edge(v, u, travel_time=time, cost=time if cost is None else cost)


def test_reported_time_excludes_the_penalty():
    """A home on a private drive: reaching it costs extra to choose, but the drive itself is 30 s."""
    G = nx.MultiDiGraph()
    edge(G, "road", "home", time=30.0, cost=30.0 + 450.0, both=True)
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
    t = arrival_seconds_two_weight(cost_csr, time_csr, dest_idx=[index["road"]])
    assert t[index["home"]] == 30.0           # real seconds, not 480
    single = arrival_seconds(cost_csr, dest_idx=[index["road"]])
    assert single[index["home"]] == 480.0      # what the old single-weight path would have reported


def test_the_home_is_reachable_at_all_which_is_the_whole_point():
    """Before the fix, a restricted edge was deleted and the home was simply unreachable."""
    G = nx.MultiDiGraph()
    edge(G, "road", "home", time=30.0, cost=480.0, both=True)
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
    t = arrival_seconds_two_weight(cost_csr, time_csr, dest_idx=[index["road"]])
    assert math.isfinite(t[index["home"]])


def test_a_private_shortcut_is_not_used_when_an_open_detour_is_cheaper():
    """A gated cut-through must not become a public shortcut."""
    G = nx.MultiDiGraph()
    # shortcut: 60 s of travel but penalised; detour: 200 s of open road
    edge(G, "A", "B", time=60.0, cost=60.0 + 450.0, both=True)
    edge(G, "A", "M", time=100.0, both=True)
    edge(G, "M", "B", time=100.0, both=True)
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
    t = arrival_seconds_two_weight(cost_csr, time_csr, dest_idx=[index["B"]])
    assert t[index["A"]] == 200.0, "should take the open detour and report its real time"


def test_a_private_shortcut_is_used_when_there_is_no_alternative():
    """Penalised, not forbidden: if it is the only way, it is the answer, at its real time."""
    G = nx.MultiDiGraph()
    edge(G, "A", "B", time=60.0, cost=60.0 + 450.0, both=True)
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
    t = arrival_seconds_two_weight(cost_csr, time_csr, dest_idx=[index["B"]])
    assert t[index["A"]] == 60.0


def test_penalty_can_flip_the_choice_toward_a_slower_but_open_route():
    """And the reported time is then the slower route's real time, not the faster penalised one."""
    G = nx.MultiDiGraph()
    edge(G, "A", "B", time=10.0, cost=10.0 + 450.0, both=True)   # fast private
    edge(G, "A", "C", time=200.0, both=True)                      # slow open
    edge(G, "C", "B", time=200.0, both=True)
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
    t = arrival_seconds_two_weight(cost_csr, time_csr, dest_idx=[index["B"]])
    assert t[index["A"]] == 400.0


def test_multi_hop_time_accumulates_along_the_chosen_path():
    G = nx.MultiDiGraph()
    edge(G, "A", "B", time=10.0, both=True)
    edge(G, "B", "C", time=20.0, both=True)
    edge(G, "C", "D", time=30.0, both=True)
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
    t = arrival_seconds_two_weight(cost_csr, time_csr, dest_idx=[index["D"]])
    assert t[index["C"]] == 30.0 and t[index["B"]] == 50.0 and t[index["A"]] == 60.0


def test_destinations_are_zero_and_unreachable_are_inf():
    G = nx.MultiDiGraph()
    edge(G, "A", "B", time=10.0, both=True)
    G.add_node("island")
    edge(G, "island", "island2", time=5.0, both=True)
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
    t = arrival_seconds_two_weight(cost_csr, time_csr, dest_idx=[index["A"]])
    assert t[index["A"]] == 0.0
    assert math.isinf(t[index["island"]])


def test_cutoff_applies_to_real_time_not_to_cost():
    """A penalised path inside the time budget must survive the cutoff."""
    G = nx.MultiDiGraph()
    edge(G, "A", "B", time=100.0, cost=100.0 + 450.0, both=True)
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
    t = arrival_seconds_two_weight(cost_csr, time_csr, dest_idx=[index["B"]], cutoff_s=200.0)
    assert t[index["A"]] == 100.0, "cost 550 exceeds the budget but real time 100 does not"
    t2 = arrival_seconds_two_weight(cost_csr, time_csr, dest_idx=[index["B"]], cutoff_s=50.0)
    assert math.isinf(t2[index["A"]])


def test_parallel_edges_report_the_time_of_the_cost_minimal_one():
    G = nx.MultiDiGraph()
    G.add_edge("A", "B", travel_time=10.0, cost=460.0)   # fast but penalised
    G.add_edge("A", "B", travel_time=90.0, cost=90.0)    # slower, open, cheaper to choose
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
    assert cost_csr[index["A"], index["B"]] == 90.0
    assert time_csr[index["A"], index["B"]] == 90.0, "must not pair the open cost with the fast time"


def test_missing_cost_falls_back_to_time_so_unpenalised_graphs_still_work():
    G = nx.MultiDiGraph()
    G.add_edge("A", "B", travel_time=42.0)
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
    assert cost_csr[index["A"], index["B"]] == 42.0 == time_csr[index["A"], index["B"]]


def test_mismatched_matrices_are_rejected():
    import scipy.sparse as sp
    with pytest.raises(ValueError, match="must match"):
        arrival_seconds_two_weight(sp.csr_matrix((2, 2)), sp.csr_matrix((3, 3)), dest_idx=[0])


def test_empty_destinations_are_all_unreachable():
    G = nx.MultiDiGraph()
    edge(G, "A", "B", time=10.0, both=True)
    cost_csr, time_csr, _ = graph_to_cost_time_csr(G)
    t = arrival_seconds_two_weight(cost_csr, time_csr, dest_idx=[])
    assert np.all(np.isinf(t))


def test_one_way_direction_is_still_respected_with_two_weights():
    """The C1 regression, re-tested on the two-weight path."""
    G = nx.MultiDiGraph()
    edge(G, "A", "B", time=60.0)                 # one-way A->B
    edge(G, "B", "C", time=30.0, both=True)
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
    to_b = arrival_seconds_two_weight(cost_csr, time_csr, dest_idx=[index["B"]])
    assert to_b[index["A"]] == 60.0 and to_b[index["C"]] == 30.0
    to_a = arrival_seconds_two_weight(cost_csr, time_csr, dest_idx=[index["A"]])
    assert math.isinf(to_a[index["B"]]) and math.isinf(to_a[index["C"]])


def test_speeds_sets_both_weights_and_penalises_only_restricted_edges():
    G = nx.MultiDiGraph()
    for n, (x, y) in {"U": (0.0, 0.0), "V": (100.0, 0.0), "W": (200.0, 0.0)}.items():
        G.add_node(n, x=x, y=y)
    G.add_edge("U", "V", length=100.0, highway="residential")
    G.add_edge("V", "W", length=100.0, highway="service", access="private")
    G = add_travel_times(G, mode="drive")
    open_e = G.edges["U", "V", 0]
    rest_e = G.edges["V", "W", 0]
    assert open_e["cost"] == pytest.approx(open_e["travel_time"])
    assert rest_e["cost"] == pytest.approx(rest_e["travel_time"] + RESTRICTED_PENALTY_S["drive"])
    assert rest_e["travel_time"] < rest_e["cost"]
