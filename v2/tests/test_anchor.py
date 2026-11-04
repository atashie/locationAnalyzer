"""Phase 1 S2.2. Anchor routability: the RDU stub, the one-way case weak connectivity misses, and
the fence a short nudge can cross.

The fixtures encode the three failure modes the plan names, rather than testing a distance formula:

1. the anchor snaps to a disconnected stub — three of twelve Phase 0 spot-check journeys failed
   this way, 4 m from the right place;
2. the anchor snaps to a node the core cannot reach *in the required direction*, which weak
   connectivity calls connected;
3. the nearest routable node is on the other side of a wall.
"""
import math

import networkx as nx
import numpy as np
import pytest
import shapely

from locfinder.places.anchor import (CoreReachability, AnchorFix, fix_anchor, node_coordinates)
from locfinder.traveltime.csr import graph_to_csr
from locfinder.traveltime.snap import EdgeIndex


def G_with(edges, nodes):
    """`edges` are (u, v, seconds) directed; `nodes` are name -> (x, y) in metres."""
    G = nx.MultiDiGraph()
    for n, (x, y) in nodes.items():
        G.add_node(n, x=float(x), y=float(y))
    for u, v, t in edges:
        G.add_edge(u, v, travel_time=float(t), length=float(t) * 10.0)
    G.graph["crs"] = "EPSG:32617"
    return G


def prepared(G):
    csr, index = graph_to_csr(G)
    return EdgeIndex.from_graph(G, index), CoreReachability.from_csr(csr), index


# A main two-way corridor A-B-C-D, plus an isolated stub S1-S2 near B (the RDU shape).
MAIN = {"A": (0, 0), "B": (100, 0), "C": (200, 0), "D": (300, 0)}
STUB = {"S1": (104, 0), "S2": (104, 40)}
MAIN_EDGES = [("A", "B", 10), ("B", "A", 10), ("B", "C", 10), ("C", "B", 10),
              ("C", "D", 10), ("D", "C", 10)]
STUB_EDGES = [("S1", "S2", 5), ("S2", "S1", 5)]


# ---------------------------------------------------------------- directed reachability

def test_the_core_is_the_largest_strongly_connected_component():
    idx, reach, index = prepared(G_with(MAIN_EDGES + STUB_EDGES, {**MAIN, **STUB}))
    assert reach.core_size == 4, "the four-node corridor, not the two-node stub"
    assert reach.usable_share == pytest.approx(4 / 6)


def test_a_disconnected_stub_is_not_reachable_from_the_core():
    """The RDU failure. The stub is 4 m away and perfectly connected to itself."""
    idx, reach, index = prepared(G_with(MAIN_EDGES + STUB_EDGES, {**MAIN, **STUB}))
    assert not reach.reachable_from_core[index["S1"]]
    assert not reach.reachable_from_core[index["S2"]]
    assert reach.reachable_from_core[index["B"]]


def test_a_one_way_sink_is_reachable_and_a_one_way_source_is_not():
    """The case weak connectivity cannot see, and the one most easily got backwards.

    `IN` can only be *left* towards the corridor, so the core cannot reach it — useless as a
    destination. `OUT` can only be *entered* from the corridor, so the core can reach it — usable.
    `components.largest_component` calls both connected.
    """
    nodes = {**MAIN, "IN": (100, 50), "OUT": (200, 50)}
    edges = MAIN_EDGES + [("IN", "B", 5), ("C", "OUT", 5)]
    idx, reach, index = prepared(G_with(edges, nodes))
    assert not reach.reachable_from_core[index["IN"]], "nothing can drive TO a one-way source"
    assert reach.reachable_from_core[index["OUT"]], "the core can drive to a one-way sink"
    # and weak connectivity would not have separated them
    Gw = G_with(edges, nodes)
    assert nx.number_weakly_connected_components(Gw) == 1


# ---------------------------------------------------------------- the nudge

def test_an_anchor_on_a_stub_is_nudged_to_the_reachable_corridor():
    G = G_with(MAIN_EDGES + STUB_EDGES, {**MAIN, **STUB})
    idx, reach, index = prepared(G)
    # 4 m from the stub, ~100 m along the corridor from A
    fix = fix_anchor(104.0, 2.0, edge_index=idx, reach=reach, barriers=None)
    assert fix.status == "nudged" and fix.usable
    assert fix.node == index["B"], "moved onto the corridor, not the stub"
    assert fix.rejected_unreachable >= 1
    assert fix.moved_m < 10.0, "the corridor was close by; the move is small"


def test_an_anchor_already_on_the_core_is_not_moved():
    idx, reach, index = prepared(G_with(MAIN_EDGES, MAIN))
    fix = fix_anchor(100.0, 0.0, edge_index=idx, reach=reach, barriers=None)
    assert fix.status == "ok" and fix.moved_m == pytest.approx(0.0)
    assert fix.node == index["B"] and fix.rejected_unreachable == 0


def test_the_nudge_is_capped_and_failure_is_reported_rather_than_forced():
    """Better to say the anchor cannot be used than to move it somewhere a household never meant."""
    G = G_with(MAIN_EDGES + STUB_EDGES, {**MAIN, **STUB})
    idx, reach, _ = prepared(G)
    # sitting on the stub, with the cap too tight to reach the corridor
    fix = fix_anchor(104.0, 38.0, edge_index=idx, reach=reach, barriers=None, max_nudge_m=10.0)
    assert fix.status == "unreachable" and not fix.usable
    assert fix.x is None and "none reachable from the core" in fix.reason


def test_no_network_at_all_is_distinguished_from_unreachable_network():
    """Two different causes with two different remedies: move the pin, or fix the data."""
    idx, reach, _ = prepared(G_with(MAIN_EDGES, MAIN))
    fix = fix_anchor(5000.0, 5000.0, edge_index=idx, reach=reach, barriers=None)
    assert fix.status == "off_network" and math.isinf(fix.moved_m)
    assert "no network within" in fix.reason


# ---------------------------------------------------------------- barriers

def wall(x, y0, y1):
    return shapely.linestrings([[x, y0], [x, y1]])


def test_a_short_nudge_that_crosses_a_wall_is_rejected_for_a_longer_one():
    """A displacement validated on distance alone is not validated. The nearest node is 10 m away
    but behind a wall; the next is 90 m away on the same side."""
    nodes = {"NEAR": (10, 0), "FAR": (-90, 0), "N2": (10, 100), "F2": (-90, 100)}
    edges = [("NEAR", "N2", 5), ("N2", "NEAR", 5), ("FAR", "F2", 5), ("F2", "FAR", 5),
             ("N2", "F2", 5), ("F2", "N2", 5)]
    idx, reach, index = prepared(G_with(edges, nodes))
    barriers = shapely.STRtree([wall(5.0, -200.0, 50.0)])    # between the anchor and NEAR

    without = fix_anchor(0.0, 0.0, edge_index=idx, reach=reach, barriers=None, max_nudge_m=200.0)
    assert without.node == index["NEAR"] and without.barriers_checked is False

    withb = fix_anchor(0.0, 0.0, edge_index=idx, reach=reach, barriers=barriers, max_nudge_m=200.0)
    assert withb.barriers_checked is True
    assert withb.node == index["FAR"], "the wall sends us to the node on our own side"
    assert withb.rejected_by_barrier >= 1
    assert withb.moved_m > without.moved_m


def test_omitting_barriers_is_recorded_not_silently_treated_as_a_pass():
    idx, reach, _ = prepared(G_with(MAIN_EDGES, MAIN))
    assert fix_anchor(100.0, 0.0, edge_index=idx, reach=reach,
                      barriers=None).barriers_checked is False
    assert fix_anchor(100.0, 0.0, edge_index=idx, reach=reach,
                      barriers=shapely.STRtree([])).barriers_checked is True


def test_barriers_has_no_default_so_the_decision_cannot_be_skipped():
    idx, reach, _ = prepared(G_with(MAIN_EDGES, MAIN))
    with pytest.raises(TypeError):
        fix_anchor(100.0, 0.0, edge_index=idx, reach=reach)


# ---------------------------------------------------------------- plumbing

def test_node_coordinates_round_trip_from_the_index():
    G = G_with(MAIN_EDGES, MAIN)
    idx, _, index = prepared(G)
    xy = node_coordinates(idx)
    for name, (x, y) in MAIN.items():
        assert xy[index[name]] == pytest.approx((x, y))


def test_a_graph_with_no_cross_component_edges_still_builds():
    """`breadth_first_order` is skipped when the condensation has no edges at all."""
    idx, reach, index = prepared(G_with([("A", "B", 5), ("B", "A", 5)], {"A": (0, 0), "B": (10, 0)}))
    assert reach.core_size == 2 and reach.usable_share == 1.0


# ---------------------------------------------------------------- found on the real payload

def test_a_fully_fenced_site_is_still_usable_and_says_its_approach_crosses_a_barrier():
    """The RDU defect, and it was mine. Vetoing any barrier-crossing candidate made the airport
    unusable: all six nodes within 150 m are core-reachable and every one is cut off by the
    perimeter `barrier=fence`. The straight segment is a proxy for an approach that really loops
    round the terminal road, so a barrier must rank candidates rather than veto them."""
    nodes = {"R1": (100, 0), "R2": (100, 100)}
    idx, reach, index = prepared(G_with([("R1", "R2", 5), ("R2", "R1", 5)], nodes))
    ring = shapely.STRtree([wall(50.0, -500.0, 500.0)])     # a perimeter between anchor and road
    fix = fix_anchor(0.0, 0.0, edge_index=idx, reach=reach, barriers=ring, max_nudge_m=200.0)
    assert fix.usable, "a real place must not become unusable because it has a fence"
    assert fix.crossed_barrier is True
    assert fix.node == index["R1"], "the nearest reachable node, taken anyway"
    assert "behind a barrier" in fix.reason


def test_a_clear_candidate_is_still_preferred_over_a_nearer_fenced_one():
    """The fallback must not weaken the original intent: with a choice, stay on our own side."""
    nodes = {"NEAR": (10, 0), "FAR": (-90, 0), "N2": (10, 100), "F2": (-90, 100)}
    edges = [("NEAR", "N2", 5), ("N2", "NEAR", 5), ("FAR", "F2", 5), ("F2", "FAR", 5),
             ("N2", "F2", 5), ("F2", "N2", 5)]
    idx, reach, index = prepared(G_with(edges, nodes))
    fix = fix_anchor(0.0, 0.0, edge_index=idx, reach=reach,
                     barriers=shapely.STRtree([wall(5.0, -200.0, 50.0)]), max_nudge_m=200.0)
    assert fix.node == index["FAR"] and fix.crossed_barrier is False


def test_ordinary_snapping_is_not_reported_as_a_nudge():
    """`nudged` has to mean something. The first version called all twelve spot-check anchors
    nudged, because every POI is more than a metre from a road node — so the status carried no
    information at all. It now means a *nearer* candidate was rejected."""
    idx, reach, index = prepared(G_with(MAIN_EDGES, MAIN))
    fix = fix_anchor(100.0, 40.0, edge_index=idx, reach=reach, barriers=None)
    assert fix.status == "ok", "40 m from a POI to the nearest road node is snapping"
    assert fix.moved_m == pytest.approx(40.0), "the displacement is still reported for display"
    assert fix.rejected_unreachable == 0 and fix.crossed_barrier is False
