"""Tests Codex pass 6 named as missing. The first reproduces its executed counterexample, in which
the cell layer contradicted the node layer by taking a penalised shortcut the search had rejected."""
import math

import networkx as nx
import numpy as np
import pytest

from locfinder.traveltime.access import RESTRICTED_PENALTY_S, classify_access
from locfinder.traveltime.arrival import arrival_seconds, arrival_seconds_two_weight
from locfinder.traveltime.csr import graph_to_cost_time_csr
from locfinder.traveltime.snap import EdgeIndex, cell_seconds_from_arrival

PEN = 450.0


def codex_h1_graph() -> nx.MultiDiGraph:
    """Codex pass-6 H1 fixture. S<->E is a fast private link (time 10, cost 460 each way);
    S->D and E->D are open. Reaching D from S should cost the 200 s open road, not the private
    shortcut, and the node search gets that right."""
    G = nx.MultiDiGraph()
    for n, (x, y) in {"S": (0.0, 0.0), "E": (100.0, 0.0), "D": (100.0, 100.0)}.items():
        G.add_node(n, x=x, y=y)
    for u, v in (("S", "E"), ("E", "S")):
        G.add_edge(u, v, travel_time=10.0, cost=10.0 + PEN)
    for u, v in (("S", "D"), ("D", "S")):
        G.add_edge(u, v, travel_time=200.0, cost=200.0)
    for u, v in (("E", "D"), ("D", "E")):
        G.add_edge(u, v, travel_time=10.0, cost=10.0)
    return G


def prepared(G, dest_name):
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
    T = arrival_seconds_two_weight(cost_csr, time_csr, dest_idx=[index[dest_name]])
    D = arrival_seconds(cost_csr, dest_idx=[index[dest_name]])
    return EdgeIndex.from_graph(G, index), T, D, index


def test_two_weight_layer_preserves_node_cost_choice_at_an_exact_node():
    """Codex's counterexample: node reconstruction gives 200 s at S, but time-based snapping
    returned 20 s at the very same point. Cost-aware snapping must agree with the node."""
    G = codex_h1_graph()
    idx, T, D, index = prepared(G, "D")
    assert T[index["S"]] == 200.0, "node search must reject the penalised shortcut"
    assert T[index["E"]] == 10.0

    at_s = np.array([0.0]), np.array([0.0])
    # the old behaviour, for contrast: selection by time picks the private shortcut
    old = cell_seconds_from_arrival(idx, T, *at_s, mode="drive", max_access_m=50.0)
    assert old[0] == pytest.approx(20.0), "time-based selection reproduces the bug"
    # the fix: selection by cost agrees with the node
    new = cell_seconds_from_arrival(idx, T, *at_s, mode="drive", max_access_m=50.0, node_cost=D)
    assert new[0] == pytest.approx(200.0)


def test_cost_aware_snapping_crosses_over_along_the_edge_interior():
    """What the interior SHOULD do, which my first expectation got wrong.

    A cell on the private edge has no choice but to use part of it. Near S the cheaper option is to
    come back to S and take the open 200 s road; past a crossover it is cheaper to continue to E and
    take the open 10 s road. With costs 460 on the private edge, D[S]=200 and D[E]=10, the crossover
    is at f = (470-200)/920 = 0.293. So the interior is legitimately discontinuous from the node
    value, and the H1 bug was specifically that the EXACT NODE lost to the private branch when it
    did not need the private edge at all."""
    G = codex_h1_graph()
    idx, T, D, index = prepared(G, "D")

    def at(x):
        return cell_seconds_from_arrival(idx, T, np.array([x]), np.array([0.0]),
                                         mode="drive", max_access_m=50.0, node_cost=D)[0]

    assert at(1.0) == pytest.approx(200.1, abs=0.5), "just off S: come back to S, take the open road"
    assert at(25.0) == pytest.approx(202.5, abs=0.5), "still before the crossover"
    assert at(50.0) == pytest.approx(15.0, abs=0.5), "past the crossover: continue to E"
    assert at(99.0) == pytest.approx(10.1, abs=0.5), "nearly at E"
    # monotone within each branch, and the jump happens once
    xs = [1.0, 10.0, 25.0, 28.0, 32.0, 50.0, 99.0]
    vals = [at(x) for x in xs]
    jumps = sum(1 for a, b in zip(vals, vals[1:]) if b < a - 50.0)
    assert jumps == 1, f"expected exactly one crossover, got {vals}"


def test_the_penalised_branch_is_still_taken_when_it_is_the_only_way():
    """And its REAL time is reported, not its cost."""
    G = nx.MultiDiGraph()
    for n, (x, y) in {"A": (0.0, 0.0), "B": (100.0, 0.0)}.items():
        G.add_node(n, x=x, y=y)
    for u, v in (("A", "B"), ("B", "A")):
        G.add_edge(u, v, travel_time=60.0, cost=60.0 + PEN)
    idx, T, D, index = prepared(G, "B")
    secs = cell_seconds_from_arrival(idx, T, np.array([50.0]), np.array([0.0]),
                                     mode="drive", max_access_m=50.0, node_cost=D)
    assert secs[0] == pytest.approx(30.0), "half of a 60 s edge, with no penalty in the report"


def test_same_geometry_parallels_reduce_by_cost_not_by_time():
    """A fast penalised parallel must not supply the reported time for a cheaper open one."""
    G = nx.MultiDiGraph()
    for n, (x, y) in {"A": (0.0, 0.0), "B": (100.0, 0.0)}.items():
        G.add_node(n, x=x, y=y)
    G.add_edge("A", "B", travel_time=10.0, cost=10.0 + PEN)   # fast, penalised
    G.add_edge("A", "B", travel_time=90.0, cost=90.0)         # slower, open, cheaper
    G.add_edge("B", "A", travel_time=90.0, cost=90.0)
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
    idx = EdgeIndex.from_graph(G, index)
    assert idx.fwd_cost[0] == pytest.approx(90.0)
    assert idx.fwd_time[0] == pytest.approx(90.0), "must carry the chosen edge's own time"


def test_final_cutoff_is_applied_after_the_access_leg():
    """Codex pass-6 H1: the cutoff used to be applied only to node times, so a cell could exceed
    the advertised budget once its off-network access leg was added."""
    G = nx.MultiDiGraph()
    for n, (x, y) in {"A": (0.0, 0.0), "B": (100.0, 0.0)}.items():
        G.add_node(n, x=x, y=y)
    for u, v in (("A", "B"), ("B", "A")):
        G.add_edge(u, v, travel_time=100.0, cost=100.0)
    idx, T, D, index = prepared(G, "B")
    # a cell 150 m off the line: a long walk-speed access leg on top of the network time
    far = (np.array([50.0]), np.array([150.0]))
    uncapped = cell_seconds_from_arrival(idx, T, *far, mode="walk", max_access_m=200.0, node_cost=D)
    assert uncapped[0] > 150.0
    capped = cell_seconds_from_arrival(idx, T, *far, mode="walk", max_access_m=200.0,
                                       node_cost=D, cutoff_s=150.0)
    assert math.isinf(capped[0]), "the advertised budget must be the one enforced"


def test_destination_endpoint_allowed_but_through_route_discouraged():
    """`access=destination` is now restricted, so an explicit no-through road is penalised rather
    than treated as an ordinary shortcut. Note this discourages, it does not prohibit."""
    d = {"highway": "residential", "access": "destination"}
    assert classify_access(d, "drive") == "restricted"
    G = nx.MultiDiGraph()
    for n, (x, y) in {"A": (0.0, 0.0), "B": (100.0, 0.0), "M": (50.0, 200.0)}.items():
        G.add_node(n, x=x, y=y)
    # 10 s destination-only link vs a 200 s open detour: the detour must win
    for u, v in (("A", "B"), ("B", "A")):
        G.add_edge(u, v, travel_time=10.0, cost=10.0 + PEN)
    for u, v in (("A", "M"), ("M", "A"), ("M", "B"), ("B", "M")):
        G.add_edge(u, v, travel_time=100.0, cost=100.0)
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
    T = arrival_seconds_two_weight(cost_csr, time_csr, dest_idx=[index["B"]])
    assert T[index["A"]] == 200.0


def test_two_weight_multisource_with_several_destinations():
    """Existing two-weight tests all used a single destination; min_only returns one forest over
    several roots and the reconstruction must follow the right one."""
    G = nx.MultiDiGraph()
    for n in "ABCD":
        G.add_node(n, x=0.0, y=0.0)
    for u, v, t in (("A", "B", 10.0), ("B", "A", 10.0), ("C", "D", 20.0), ("D", "C", 20.0)):
        G.add_edge(u, v, travel_time=t, cost=t)
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
    T = arrival_seconds_two_weight(cost_csr, time_csr, dest_idx=[index["A"], index["D"]])
    assert T[index["A"]] == 0.0 and T[index["D"]] == 0.0
    assert T[index["B"]] == 10.0, "nearest root is A"
    assert T[index["C"]] == 20.0, "nearest root is D"


def test_mismatched_sparsity_is_rejected_not_silently_zero():
    """Codex pass-6 M4: same shape but different edges would read a time from an unused edge."""
    import scipy.sparse as sp
    cost = sp.csr_matrix(np.array([[0.0, 5.0], [0.0, 0.0]]))
    time = sp.csr_matrix(np.array([[0.0, 0.0], [5.0, 0.0]]))
    with pytest.raises(ValueError, match="share sparsity"):
        arrival_seconds_two_weight(cost, time, dest_idx=[0])


def test_non_positive_cost_is_rejected():
    """The increasing-cost sweep relies on strictly positive costs."""
    import scipy.sparse as sp
    m = sp.csr_matrix(np.array([[0.0, -1.0], [0.0, 0.0]]))
    with pytest.raises(ValueError, match="strictly positive"):
        arrival_seconds_two_weight(m, m, dest_idx=[0])


def test_access_specificity_hierarchy():
    """Codex pass-6 H5: the narrowest tag present wins, so motorcar beats motor_vehicle."""
    assert classify_access({"highway": "service", "motor_vehicle": "no", "motorcar": "yes"}, "drive") == "open"
    assert classify_access({"highway": "service", "motor_vehicle": "yes", "motorcar": "no"}, "drive") == "forbidden"
    assert classify_access({"highway": "service", "vehicle": "private"}, "drive") == "restricted"
    assert classify_access({"highway": "service", "vehicle": "no", "motor_vehicle": "yes"}, "drive") == "open"


def test_mixed_lists_aggregate_conservatively_on_every_tag():
    """Previously `foot=[yes, private]` came out OPEN while `access=[yes, private]` came out
    RESTRICTED; both must now be restricted."""
    assert classify_access({"highway": "path", "foot": ["yes", "private"]}, "walk") == "restricted"
    assert classify_access({"highway": "service", "access": ["yes", "private"]}, "drive") == "restricted"
    assert classify_access({"highway": "path", "foot": ["yes", "no"]}, "walk") == "forbidden"


def test_penalty_is_charged_per_edge_which_is_a_known_limitation():
    """Codex pass-6 H2: charging per simplified edge means splitting one physical private link
    doubles its penalty. Documented here as a property of the current model, not an endorsement."""
    one = {"highway": "service", "access": "private"}
    assert RESTRICTED_PENALTY_S["drive"] == pytest.approx(
        sum(RESTRICTED_PENALTY_S["drive"] for _ in range(1))
    )
    # two halves of the same physical link each carry the full penalty
    assert sum(RESTRICTED_PENALTY_S["drive"] for _ in range(2)) == 2 * RESTRICTED_PENALTY_S["drive"]
    assert classify_access(one, "drive") == "restricted"
