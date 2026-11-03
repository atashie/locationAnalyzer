import math

import networkx as nx

from locfinder.traveltime.speeds import DRIVE_FRICTION_MPH, MPH_TO_MPS, add_travel_times, edge_allowed


def two_node(**tags) -> nx.MultiDiGraph:
    G = nx.MultiDiGraph()
    G.add_node("U", x=0.0, y=0.0)
    G.add_node("V", x=100.0, y=0.0)
    G.add_edge("U", "V", length=100.0, **tags)
    return G


def test_private_access_blocks_every_mode_unless_mode_tag_allows():
    data = {"highway": "service", "access": "private"}
    assert not edge_allowed(data, "drive") and not edge_allowed(data, "bike") and not edge_allowed(data, "walk")
    assert edge_allowed({"highway": "service", "access": "private", "foot": "yes"}, "walk")


def test_mode_specific_no_tags_block_their_mode_only():
    assert not edge_allowed({"highway": "residential", "foot": "no"}, "walk")
    assert edge_allowed({"highway": "residential", "foot": "no"}, "drive")
    assert not edge_allowed({"highway": "residential", "bicycle": "no"}, "bike")
    assert not edge_allowed({"highway": "residential", "motor_vehicle": "no"}, "drive")
    assert edge_allowed({"highway": "residential", "motor_vehicle": "no"}, "walk")


def test_list_valued_highway_requires_every_value_allowed_and_uses_slowest_speed():
    data = {"highway": ["residential", "footway"]}
    assert not edge_allowed(data, "drive")  # footway is not drivable
    G = add_travel_times(two_node(highway=["primary", "residential"]), mode="drive")
    expected = 100.0 / (DRIVE_FRICTION_MPH["residential"] * MPH_TO_MPS)
    assert math.isclose(G.edges["U", "V", 0]["travel_time"], expected, rel_tol=1e-9)


def test_bike_contraflow_adds_reverse_edge_only_when_tagged():
    G = add_travel_times(two_node(highway="residential", oneway=True, **{"oneway:bicycle": "no"}), mode="bike")
    assert G.has_edge("V", "U")
    G2 = add_travel_times(two_node(highway="residential", oneway=True), mode="bike")
    assert not G2.has_edge("V", "U")
    G3 = add_travel_times(two_node(highway="residential", oneway=True, **{"oneway:bicycle": "no"}), mode="drive")
    assert not G3.has_edge("V", "U")  # contraflow is a bicycle rule only
