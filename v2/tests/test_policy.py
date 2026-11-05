"""The access-policy language and its product-graph search.

Every case here is one Codex pass 13 used to break the first version of this audit, so the tests
are the counterexamples rather than paraphrases of the rule.
"""
import networkx as nx
import numpy as np
import pytest

from locfinder.traveltime.csr import graph_to_cost_time_csr
from locfinder.traveltime.policy import (accepts, class_separated_times, lawful_arrival, min_time,
                                         product_graph, unrestricted_arrival)

O, R = False, True           # noqa: E741 — open, restricted


def G_from(edges, coords=None):
    """`edges` is a list of `(u, v, seconds, restricted)`."""
    G = nx.MultiDiGraph()
    for u, v, t, restricted in edges:
        for node in (u, v):
            if node not in G:
                xy = (coords or {}).get(node, (0.0, 0.0))
                G.add_node(node, x=xy[0], y=xy[1])
        data = {"travel_time": float(t)}
        if restricted:
            data["access"] = "private"
        G.add_edge(u, v, **data)
    return G


# ---------------------------------------------------------------- the language itself

@pytest.mark.parametrize("classes, lawful", [
    ([], True),                          # already there
    ([O], True),                         # one open edge
    ([R], True),                         # one restricted edge: a driveway to the door
    ([R, O], True),                      # out of the drive, onto the road
    ([O, R], True),                      # along the road, into the destination's drive
    ([R, O, R], True),                   # the canonical lawful journey
    ([R, R, O, O, R, R], True),          # chains of any length
    ([O, R, O], False),                  # through traffic: private shortcut between open roads
    ([R, O, R, O], False),               # an open block after the destination's chain began
    ([O, R, R, O], False),               # the same, with a longer private shortcut
    ([R, O, O, R, O, R], False),         # two open blocks
])
def test_the_lawful_language_is_restricted_open_restricted(classes, lawful):
    assert accepts(classes) is lawful


def test_the_language_is_its_own_reverse():
    """Which is why the arrival search can use the same three states with the chains exchanged."""
    import itertools
    for n in range(0, 7):
        for seq in itertools.product([O, R], repeat=n):
            assert accepts(seq) == accepts(tuple(reversed(seq))), seq


# ---------------------------------------------------------------- the search

def test_a_private_shortcut_between_open_roads_has_no_lawful_journey():
    """Codex pass-13 H1's graph. A->B open, B->C restricted, C->D open, every edge 10 s, D the
    destination. B is lawful at 20 s (restricted then open is `R* O*`). A is not: its only journey
    is open-restricted-open, which is through traffic over private land."""
    G = G_from([("A", "B", 10, O), ("B", "C", 10, R), ("C", "D", 10, O)])
    _, _, index = graph_to_cost_time_csr(G)
    by_class = class_separated_times(G, index, mode="walk")
    seconds, _ = lawful_arrival(by_class, dest_idx=[index["D"]])
    assert seconds[index["D"]] == 0.0
    assert seconds[index["C"]] == pytest.approx(10.0)
    assert seconds[index["B"]] == pytest.approx(20.0)
    assert not np.isfinite(seconds[index["A"]]), seconds[index["A"]]


def test_a_lawful_public_parallel_edge_is_not_discarded_with_its_restricted_twin():
    """Codex pass-13 H4, which is why the classes are separated on the multigraph. A->B has a fast
    private edge (1 s) and a slow public one (200 s). The shipped CSR keeps only the private one, so
    filtering the CSR by class removes the pair and reports no route — although the public edge
    makes the whole journey open and therefore lawful."""
    G = G_from([("P", "A", 5, O), ("A", "B", 1, R), ("A", "B", 200, O), ("B", "D", 10, O)])
    cost_csr, _, index = graph_to_cost_time_csr(G)
    # the CSR really does keep only one A->B edge, and it is the fast private one
    assert cost_csr[index["A"], index["B"]] == pytest.approx(1.0)

    by_class = class_separated_times(G, index, mode="walk")
    assert by_class[R][index["A"], index["B"]] == pytest.approx(1.0)
    assert by_class[O][index["A"], index["B"]] == pytest.approx(200.0)

    seconds, _ = lawful_arrival(by_class, dest_idx=[index["D"]])
    # P -> A -> B -> D, all open: 5 + 200 + 10
    assert seconds[index["P"]] == pytest.approx(215.0)


def test_the_policy_charges_real_time_not_the_access_penalty():
    """Codex pass-13 H2. A forbidding policy has nothing to discourage, so a permitted traversal is
    charged its travel time. `cost` is deliberately absurd here and must not appear in the answer."""
    G = nx.MultiDiGraph()
    for node in ("A", "B"):
        G.add_node(node, x=0.0, y=0.0)
    G.add_edge("A", "B", travel_time=10.0, cost=130.0, access="private")
    _, _, index = graph_to_cost_time_csr(G)
    by_class = class_separated_times(G, index, mode="walk")
    seconds, _ = lawful_arrival(by_class, dest_idx=[index["B"]])
    assert seconds[index["A"]] == pytest.approx(10.0)


def test_subdividing_a_restricted_edge_changes_nothing():
    """Codex pass-13 H3, the defect that motivated the whole rewrite. A one-edge driveway and the
    same driveway drawn as two ways describe the same journey, so they must give the same answer.
    The withdrawn first-edge rule did not: it exempted one edge, so the second half of a split
    driveway became through traffic."""
    single = G_from([("H", "J", 20, R), ("J", "D", 30, O)])
    split = G_from([("H", "M", 10, R), ("M", "J", 10, R), ("J", "D", 30, O)])
    out = {}
    for name, G in (("single", single), ("split", split)):
        _, _, index = graph_to_cost_time_csr(G)
        seconds, _ = lawful_arrival(class_separated_times(G, index, mode="walk"),
                                    dest_idx=[index["D"]])
        out[name] = seconds[index["H"]]
    assert out["single"] == pytest.approx(out["split"]) == pytest.approx(50.0)


def test_a_lawful_journey_is_never_faster_than_an_unrestricted_one():
    """The lawful set is a subset of all journeys, so this is a soundness invariant of the product
    construction rather than a property of any graph.

    The baseline must be the unrestricted **time** minimum. Using the shipped surface instead fails
    this on real data for a reason that has nothing to do with the policy:
    `arrival_seconds_two_weight` reports the time along the *cost*-selected path, which is an upper
    bound on the minimum time (pass-8 H2), so a time-minimising lawful search comes out ahead of it.
    On the Triangle walk graph that produced 26,376 apparent violations — this invariant caught the
    confound before it became a published number."""
    rng = np.random.default_rng(11)
    checked = 0
    for _ in range(25):
        edges = []
        for u in range(8):
            for v in range(8):
                if u != v and rng.random() < 0.3:
                    edges.append((u, v, float(rng.integers(5, 60)), bool(rng.random() < 0.4)))
        if not edges:
            continue
        G = G_from(edges)
        _, _, index = graph_to_cost_time_csr(G)
        by_class = class_separated_times(G, index, mode="walk")
        dest = [index[sorted(index)[0]]]
        unrestricted = unrestricted_arrival(by_class, dest_idx=dest)
        lawful, _ = lawful_arrival(by_class, dest_idx=dest)
        both = np.isfinite(lawful)
        assert np.all(lawful[both] >= unrestricted[both] - 1e-9)
        checked += int(both.sum())
    assert checked > 0, "the random graphs produced nothing reachable; the test proved nothing"


def test_the_baseline_is_a_time_minimum_not_the_cost_selected_time():
    """Why `unrestricted_arrival` exists rather than reusing the shipped surface. A fast restricted
    edge with a large penalty is chosen *against* by the shipped surface, which then reports the
    slow open path's time; a time minimum takes the fast one. Comparing a lawful time minimum
    against the former attributes that difference to the policy, which did not cause it."""
    from locfinder.traveltime.arrival import arrival_seconds_two_weight
    G = nx.MultiDiGraph()
    for node in ("A", "B", "D"):
        G.add_node(node, x=0.0, y=0.0)
    G.add_edge("A", "D", travel_time=10.0, cost=460.0, access="private")   # fast, penalised
    G.add_edge("A", "B", travel_time=100.0, cost=100.0)
    G.add_edge("B", "D", travel_time=100.0, cost=100.0)
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
    by_class = class_separated_times(G, index, mode="walk")
    shipped = arrival_seconds_two_weight(cost_csr, time_csr, dest_idx=[index["D"]])
    baseline = unrestricted_arrival(by_class, dest_idx=[index["D"]])
    assert shipped[index["A"]] == pytest.approx(200.0)    # avoided the private edge
    assert baseline[index["A"]] == pytest.approx(10.0)     # took it
    # and the lawful answer equals the baseline here, because one restricted edge is lawful
    lawful, _ = lawful_arrival(by_class, dest_idx=[index["D"]])
    assert lawful[index["A"]] == pytest.approx(10.0)


def test_min_time_treats_a_missing_pair_as_absent_not_as_zero():
    """`sp.csr_matrix.minimum` would return 0 for a pair only one class has."""
    G = G_from([("A", "B", 30, O), ("B", "C", 40, R)])
    _, _, index = graph_to_cost_time_csr(G)
    m = min_time(class_separated_times(G, index, mode="walk"))
    assert m[index["A"], index["B"]] == pytest.approx(30.0)
    assert m[index["B"], index["C"]] == pytest.approx(40.0)
    assert m.nnz == 2


def test_min_time_takes_the_faster_of_two_parallel_classes():
    G = G_from([("A", "B", 1, R), ("A", "B", 200, O)])
    _, _, index = graph_to_cost_time_csr(G)
    m = min_time(class_separated_times(G, index, mode="walk"))
    assert m[index["A"], index["B"]] == pytest.approx(1.0) and m.nnz == 1


def test_the_state_reported_is_the_one_the_journey_was_found_in():
    """A journey that is entirely open is found in state 1 — the open middle — and one that is
    entirely restricted in state 0, the destination's own chain."""
    G = G_from([("A", "D", 10, O)])
    _, _, index = graph_to_cost_time_csr(G)
    _, state = lawful_arrival(class_separated_times(G, index, mode="walk"),
                              dest_idx=[index["D"]])
    assert state[index["A"]] == 1

    G = G_from([("A", "D", 10, R)])
    _, _, index = graph_to_cost_time_csr(G)
    _, state = lawful_arrival(class_separated_times(G, index, mode="walk"),
                              dest_idx=[index["D"]])
    assert state[index["A"]] == 0


def test_no_destinations_means_no_lawful_times():
    G = G_from([("A", "B", 10, O)])
    _, _, index = graph_to_cost_time_csr(G)
    seconds, _ = lawful_arrival(class_separated_times(G, index, mode="walk"), dest_idx=[])
    assert not np.isfinite(seconds).any()


def test_state_two_has_no_open_transition():
    """The structural claim behind the whole construction: once the origin's chain has begun,
    an open edge would start a second open block, which the language does not contain."""
    from locfinder.traveltime.policy import TRANSITIONS
    assert TRANSITIONS[(2, False)] is None
    assert TRANSITIONS[(2, True)] == 2


def test_the_product_graph_has_three_blocks_per_node():
    G = G_from([("A", "B", 10, O), ("B", "C", 10, R)])
    _, _, index = graph_to_cost_time_csr(G)
    p = product_graph(class_separated_times(G, index, mode="walk"))
    assert p.shape == (3 * len(index), 3 * len(index))


def test_symmetrise_adds_a_reverse_per_road_not_per_node_pair():
    """Codex pass-14 H3, its executed input. `symmetrise` asked `G.has_edge(v, u)`, so the presence
    of *any* v->u edge suppressed the reverse of *every* u->v road. Here the only B->A edge is a
    1 s **restricted** one, so the 100 s **open** A->B road got no walkable reverse and P could not
    reach D under any policy that declines the restricted edge. Separating access classes downstream
    cannot recover an alternative already discarded upstream."""
    from locfinder.traveltime.speeds import symmetrise
    G = nx.MultiDiGraph()
    for node in ("P", "A", "B", "D"):
        G.add_node(node, x=0.0, y=0.0)
    G.add_edge("P", "B", travel_time=5.0, length=5.0, osmid=1)
    G.add_edge("A", "B", travel_time=100.0, length=100.0, osmid=2)
    G.add_edge("B", "A", travel_time=1.0, length=1.0, osmid=3, access="private")
    G.add_edge("A", "D", travel_time=5.0, length=5.0, osmid=4)

    H = symmetrise(G.copy())
    # the open road now has a walkable reverse, distinct from the restricted one
    reverses = [d for _, _, d in H.edges(data=True)
                if d.get("osmid") == 2 and d["travel_time"] == 100.0]
    assert len(reverses) == 2, "the open A->B road should exist in both directions"

    _, _, index = graph_to_cost_time_csr(H)
    seconds, _ = lawful_arrival(class_separated_times(H, index, mode="walk"),
                                dest_idx=[index["D"]])
    # P -> B -> A (open, 100) -> D (5): the restricted shortcut is not needed
    assert seconds[index["P"]] == pytest.approx(110.0), seconds[index["P"]]


def test_symmetrise_does_not_duplicate_a_road_that_is_already_two_way():
    """The other half: a genuine two-way street must not gain a third edge."""
    from locfinder.traveltime.speeds import symmetrise
    G = nx.MultiDiGraph()
    for node in ("A", "B"):
        G.add_node(node, x=0.0, y=0.0)
    G.add_edge("A", "B", travel_time=10.0, length=10.0, osmid=7)
    G.add_edge("B", "A", travel_time=10.0, length=10.0, osmid=7)
    H = symmetrise(G.copy())
    assert H.number_of_edges() == 2
