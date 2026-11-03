import math

import numpy as np
import pytest

from locfinder.traveltime.expansion import expansion_to_edge_index
from locfinder.traveltime.snap import cell_seconds_from_arrival

CRS = "EPSG:32617"
NO_PRED = 70368744177663  # Valhalla's "no predecessor" sentinel


def feat(coords, duration, distance_m, edge_id, pred_edge_id=NO_PRED):
    """Mimic a Valhalla expansion feature: duration/distance are CUMULATIVE at the far end."""
    return {"type": "Feature", "geometry": {"type": "LineString", "coordinates": coords},
            "properties": {"duration": duration, "distance": distance_m,
                           "edge_id": edge_id, "pred_edge_id": pred_edge_id}}


def chain():
    """Destination at the first vertex. Three chained edges settled at 100/200/300 s."""
    return [
        feat([[-79.000, 35.900], [-79.001, 35.900]], 100.0, 90.0, 1),
        feat([[-79.001, 35.900], [-79.002, 35.900]], 200.0, 180.0, 2, 1),
        feat([[-79.002, 35.900], [-79.003, 35.900]], 300.0, 270.0, 3, 2),
    ]


def test_chain_reconstructs_exact_node_times():
    idx, T = expansion_to_edge_index(chain(), target_crs=CRS)
    assert len(T) == 4
    assert sorted(round(t) for t in T) == [0, 100, 200, 300]


def test_edge_traversal_times_are_duration_differences():
    idx, _ = expansion_to_edge_index(chain(), target_crs=CRS)
    assert sorted(round(t) for t in idx.fwd_time) == [100, 100, 100]


def test_midpoint_is_interpolated_not_charged_a_whole_edge():
    """A cell at the midpoint of the second edge (endpoints 100 s and 200 s) should read ~150 s."""
    idx, T = expansion_to_edge_index(chain(), target_crs=CRS)
    second = idx.geoms[1]
    mid = second.interpolate(0.5, normalized=True)
    secs = cell_seconds_from_arrival(idx, T, np.array([mid.x]), np.array([mid.y]),
                                     mode="walk", max_access_m=20.0)
    assert 140.0 <= secs[0] <= 160.0, secs[0]


def test_node_at_destination_is_zero():
    idx, T = expansion_to_edge_index(chain(), target_crs=CRS)
    assert T.min() == 0.0


def test_reversed_geometry_still_identifies_the_near_end():
    """If a successor's geometry is stored tail-first, the shared vertex must still win."""
    feats = [
        feat([[-79.000, 35.900], [-79.001, 35.900]], 100.0, 90.0, 1),
        feat([[-79.002, 35.900], [-79.001, 35.900]], 200.0, 180.0, 2, 1),  # reversed
    ]
    idx, T = expansion_to_edge_index(feats, target_crs=CRS)
    assert sorted(round(t) for t in T) == [0, 100, 200]


def test_unresolvable_predecessor_is_treated_as_a_root():
    feats = [feat([[-79.000, 35.900], [-79.001, 35.900]], 100.0, 90.0, 7, pred_edge_id=99999)]
    idx, T = expansion_to_edge_index(feats, target_crs=CRS)
    assert sorted(round(t) for t in T) == [0, 100]
    assert math.isclose(idx.fwd_time[0], 100.0)


def test_missing_duration_and_degenerate_geometry_are_skipped():
    feats = [
        {"geometry": {"type": "LineString", "coordinates": [[-79.0, 35.9], [-79.001, 35.9]]}, "properties": {"edge_id": 1}},
        feat([[-79.000, 35.900]], 50.0, 10.0, 2),
        feat([[-79.000, 35.900], [-79.001, 35.900]], 100.0, 90.0, 3),
    ]
    idx, _ = expansion_to_edge_index(feats, target_crs=CRS)
    assert len(idx.geoms) == 1


def test_coordinates_outside_the_projection_are_skipped():
    far = feat([[0.0, 0.0], [0.001, 0.0]], 100.0, 90.0, 1)
    good = feat([[-79.000, 35.900], [-79.001, 35.900]], 100.0, 90.0, 2)
    idx, _ = expansion_to_edge_index([far, good], target_crs=CRS)
    assert len(idx.geoms) == 1


def test_empty_expansion_raises():
    with pytest.raises(ValueError):
        expansion_to_edge_index([], target_crs=CRS)


def test_branching_tree_resolves_every_node():
    """One root edge with two successors branching off its far end."""
    feats = [
        feat([[-79.000, 35.900], [-79.001, 35.900]], 100.0, 90.0, 1),
        feat([[-79.001, 35.900], [-79.001, 35.901]], 160.0, 200.0, 2, 1),
        feat([[-79.001, 35.900], [-79.001, 35.899]], 180.0, 210.0, 3, 1),
    ]
    idx, T = expansion_to_edge_index(feats, target_crs=CRS)
    assert sorted(round(t) for t in T) == [0, 100, 160, 180]
