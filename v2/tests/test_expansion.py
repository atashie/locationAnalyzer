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


def test_dangling_predecessor_does_not_become_a_zero_time_root():
    """Codex pass-7 C5, second half. An edge naming a predecessor that is NOT in the response has
    an UNKNOWN near-end time -- the predecessor's cumulative duration was the only way to get it.
    The old code treated it as a search root at 0 s, which plants a spurious "instantly reachable"
    node in the middle of the network. The earlier test asserted that mistake."""
    feats = [
        feat([[-79.000, 35.900], [-79.001, 35.900]], 100.0, 90.0, 1),
        feat([[-79.001, 35.900], [-79.002, 35.900]], 200.0, 180.0, 2, 1),
        feat([[-79.010, 35.900], [-79.011, 35.900]], 400.0, 360.0, 7, pred_edge_id=99999),
    ]
    with pytest.raises(ValueError, match="not self-consistent"):
        expansion_to_edge_index(feats, target_crs=CRS)

    rep = {}
    idx, T = expansion_to_edge_index(feats, target_crs=CRS, strict=False, report=rep)
    assert rep["dangling_predecessors"] == 1 and rep["dropped"] == 1
    assert len(idx.geoms) == 2, "the orphan edge is removed, not kept with an invented time"
    assert sorted(round(t) for t in T if math.isfinite(t)) == [0, 100, 200]
    assert np.isinf(T).sum() == 2, "the orphan's own nodes stay unknown"


def test_root_orientation_is_derived_from_origins_when_geometry_points_inward():
    """Codex pass-7 C5, first half, reproduced. The root's stored geometry runs TOWARD the
    destination, so its near end is coords[-1]. The old code assumed coords[0] unconditionally and
    put 0 s at the far node while giving the destination itself a full edge traversal."""
    dest = (-79.000, 35.900)
    feats = [feat([[-79.001, 35.900], [-79.000, 35.900]], 100.0, 90.0, 1)]   # points inward
    idx, T = expansion_to_edge_index(feats, target_crs=CRS, origins=[dest])
    near = idx.end_idx[0]      # coords[-1] is the destination
    far = idx.start_idx[0]
    assert T[near] == 0.0, "the destination is at time zero"
    assert T[far] == 100.0


def test_root_orientation_falls_back_to_successors_without_origins():
    feats = [
        feat([[-79.001, 35.900], [-79.000, 35.900]], 100.0, 90.0, 1),        # points inward
        feat([[-79.001, 35.900], [-79.002, 35.900]], 200.0, 180.0, 2, 1),    # leaves via -79.001
    ]
    idx, T = expansion_to_edge_index(feats, target_crs=CRS)
    assert sorted(round(t) for t in T) == [0, 100, 200]


def test_origins_outrank_successors_when_they_disagree():
    """The origins are authoritative: they say where the search actually started."""
    feats = [
        feat([[-79.001, 35.900], [-79.000, 35.900]], 100.0, 90.0, 1),
        feat([[-79.000, 35.900], [-79.002, 35.900]], 200.0, 180.0, 2, 1),
    ]
    # successors alone would read the shared vertex -79.000 as the FAR end, i.e. near = -79.001
    idx, T = expansion_to_edge_index(feats, target_crs=CRS)
    assert T[idx.start_idx[0]] == 0.0
    # but the origin is at -79.000, so that endpoint must be the zero
    idx2, T2 = expansion_to_edge_index(feats, target_crs=CRS, origins=[(-79.000, 35.900)])
    assert T2[idx2.end_idx[0]] == 0.0


def test_an_unorientable_root_raises_rather_than_guessing():
    """A lone root with no successor and no supplied origin is genuinely undetermined, and a guess
    lands on the destination itself where an error is maximally visible."""
    feats = [feat([[-79.000, 35.900], [-79.001, 35.900]], 100.0, 90.0, 1)]
    with pytest.raises(ValueError, match="not self-consistent"):
        expansion_to_edge_index(feats, target_crs=CRS)
    rep = {}
    with pytest.raises(ValueError, match="every expansion edge was unusable"):
        expansion_to_edge_index(feats, target_crs=CRS, strict=False, report=rep)
    assert rep["roots_unoriented"] == 1


def test_missing_duration_and_degenerate_geometry_are_skipped():
    feats = [
        {"geometry": {"type": "LineString", "coordinates": [[-79.0, 35.9], [-79.001, 35.9]]}, "properties": {"edge_id": 1}},
        feat([[-79.000, 35.900]], 50.0, 10.0, 2),
        feat([[-79.000, 35.900], [-79.001, 35.900]], 100.0, 90.0, 3),
    ]
    idx, _ = expansion_to_edge_index(feats, target_crs=CRS, origins=[(-79.000, 35.900)])
    assert len(idx.geoms) == 1


def test_coordinates_outside_the_projection_are_skipped():
    far = feat([[0.0, 0.0], [0.001, 0.0]], 100.0, 90.0, 1)
    good = feat([[-79.000, 35.900], [-79.001, 35.900]], 100.0, 90.0, 2)
    idx, _ = expansion_to_edge_index([far, good], target_crs=CRS,
                                     origins=[(-79.000, 35.900)])
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
