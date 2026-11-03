import math

import networkx as nx
import numpy as np

from locfinder.traveltime.arrival import arrival_seconds
from locfinder.traveltime.csr import graph_to_csr
from locfinder.traveltime.snap import EdgeIndex, cell_seconds_from_arrival
from locfinder.traveltime.speeds import MODE_SPEED_MPS, add_travel_times, symmetrise


def line_graph_utm() -> nx.MultiDiGraph:
    """Three nodes on a line in projected metres: A(0,0) -> B(1000,0) one-way, B <-> C(2000,0)."""
    G = nx.MultiDiGraph()
    for n, (x, y) in {"A": (0.0, 0.0), "B": (1000.0, 0.0), "C": (2000.0, 0.0)}.items():
        G.add_node(n, x=x, y=y)
    G.add_edge("A", "B", length=1000.0, highway="residential", oneway=True)
    G.add_edge("B", "C", length=1000.0, highway="residential", oneway=False)
    G.add_edge("C", "B", length=1000.0, highway="residential", oneway=False)
    G.graph["crs"] = "EPSG:32617"
    return G


def test_add_travel_times_uses_mode_speed():
    G = add_travel_times(line_graph_utm(), mode="walk")
    t = G.edges["A", "B", 0]["travel_time"]
    assert math.isclose(t, 1000.0 / MODE_SPEED_MPS["walk"], rel_tol=1e-6)


def test_add_travel_times_removes_edges_not_allowed_for_mode():
    G = line_graph_utm()
    G.add_edge("C", "A", length=2000.0, highway="motorway", oneway=True)
    G = add_travel_times(G, mode="walk")
    assert not G.has_edge("C", "A")


def test_symmetrise_adds_missing_reverse_edges_only():
    G = symmetrise(add_travel_times(line_graph_utm(), mode="walk"))
    assert G.has_edge("B", "A")
    assert G.number_of_edges() == 4


def test_snap_point_interpolates_toward_reachable_endpoint():
    G = add_travel_times(line_graph_utm(), mode="drive")
    csr, index = graph_to_csr(G)
    T = arrival_seconds(csr, dest_idx=[index["C"]])  # destination at C
    idx = EdgeIndex.from_graph(G, index)
    # a cell 10 m north of the midpoint of A->B (one-way): must go forward to B then on to C
    secs = cell_seconds_from_arrival(idx, T, np.array([500.0]), np.array([10.0]), mode="drive", max_access_m=200.0)
    t_ab = G.edges["A", "B", 0]["travel_time"]
    t_bc = G.edges["B", "C", 0]["travel_time"]
    expected_network = 0.5 * t_ab + t_bc
    assert secs[0] > expected_network  # plus a small access leg
    assert secs[0] < expected_network + 60.0


def test_snap_point_far_from_network_is_unreachable():
    G = add_travel_times(line_graph_utm(), mode="walk")
    csr, index = graph_to_csr(symmetrise(G))
    T = arrival_seconds(csr, dest_idx=[index["C"]])
    idx = EdgeIndex.from_graph(G, index)
    secs = cell_seconds_from_arrival(idx, T, np.array([500.0]), np.array([900.0]), mode="walk", max_access_m=200.0)
    assert math.isinf(secs[0])


def test_backward_interpolation_requires_reverse_edge():
    G = add_travel_times(line_graph_utm(), mode="drive")
    csr, index = graph_to_csr(G)
    T = arrival_seconds(csr, dest_idx=[index["A"]])  # destination at A: only A itself
    idx = EdgeIndex.from_graph(G, index)
    # a cell on A->B near A: cannot drive backward along the one-way to reach A
    secs = cell_seconds_from_arrival(idx, T, np.array([100.0]), np.array([0.0]), mode="drive", max_access_m=200.0)
    assert math.isinf(secs[0])


def test_backward_interpolation_works_on_two_way_edge():
    G = add_travel_times(line_graph_utm(), mode="drive")
    csr, index = graph_to_csr(G)
    T = arrival_seconds(csr, dest_idx=[index["B"]])  # destination at B
    idx = EdgeIndex.from_graph(G, index)
    # a cell on B<->C at 75% toward C: shortest is backward to B (0.75 * t_bc), allowed on a two-way edge
    secs = cell_seconds_from_arrival(idx, T, np.array([1750.0]), np.array([0.0]), mode="drive", max_access_m=200.0)
    t_bc = G.edges["B", "C", 0]["travel_time"]
    assert math.isclose(secs[0], 0.75 * t_bc, rel_tol=1e-6)


def test_layer_shape_and_encoding():
    from locfinder.grid import GridSpec, NODATA
    from locfinder.traveltime.layer import build_layer

    G = add_travel_times(line_graph_utm(), mode="walk")
    G = symmetrise(G)
    csr, index = graph_to_csr(G)
    grid = GridSpec(crs="EPSG:32617", x_min=-100.0, y_max=200.0, cell_m=100.0, ncols=22, nrows=4)
    timings: dict = {}
    arr = build_layer(G, csr, index, grid, dest_idx=[index["C"]], mode="walk", timings=timings)
    assert arr.shape == (4, 22) and arr.dtype == np.uint8
    # cells within 200 m of the line are reachable; the far north row is not
    assert (arr[1:3, 1:21] != NODATA).all()
    assert set(timings) == {"dijkstra_s", "edge_index_s", "snap_s"}
