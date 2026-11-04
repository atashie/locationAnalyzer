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
    idx, T = expansion_to_edge_index(chain(), target_crs=CRS, opposites_included=True)
    assert len(T) == 4
    assert sorted(round(t) for t in T) == [0, 100, 200, 300]


def test_edge_traversal_times_are_duration_differences():
    """The traversal time lives in whichever direction the search actually settled, so read it
    from the finite side rather than assuming `fwd_time` (S1.3: the adapter used to set both)."""
    idx, _ = expansion_to_edge_index(chain(), target_crs=CRS, opposites_included=True)
    settled = np.fmin(idx.fwd_time, idx.rev_time)
    assert sorted(round(t) for t in settled) == [100, 100, 100]
    # and the unused direction is closed: this chain runs toward the destination only
    assert np.isinf(np.fmax(idx.fwd_time, idx.rev_time)).all()


def test_midpoint_is_interpolated_not_charged_a_whole_edge():
    """A cell at the midpoint of the second edge (endpoints 100 s and 200 s) should read ~150 s."""
    idx, T = expansion_to_edge_index(chain(), target_crs=CRS, opposites_included=True)
    second = idx.geoms[1]
    mid = second.interpolate(0.5, normalized=True)
    secs = cell_seconds_from_arrival(idx, T, np.array([mid.x]), np.array([mid.y]),
                                     mode="walk", max_access_m=20.0)
    assert 140.0 <= secs[0] <= 160.0, secs[0]


def test_node_at_destination_is_zero():
    idx, T = expansion_to_edge_index(chain(), target_crs=CRS, opposites_included=True)
    assert T.min() == 0.0


def test_reversed_geometry_still_identifies_the_near_end():
    """If a successor's geometry is stored tail-first, the shared vertex must still win."""
    feats = [
        feat([[-79.000, 35.900], [-79.001, 35.900]], 100.0, 90.0, 1),
        feat([[-79.002, 35.900], [-79.001, 35.900]], 200.0, 180.0, 2, 1),  # reversed
    ]
    idx, T = expansion_to_edge_index(feats, target_crs=CRS, opposites_included=True)
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
        expansion_to_edge_index(feats, target_crs=CRS, opposites_included=True)

    rep = {}
    idx, T = expansion_to_edge_index(feats, target_crs=CRS, opposites_included=True, strict=False, report=rep)
    assert rep["dangling_predecessors"] == 1 and rep["dropped"] == 1
    assert len(idx.geoms) == 2, "the orphan edge is removed, not kept with an invented time"
    assert sorted(round(t) for t in T) == [0, 100, 200]
    # The orphan's endpoints are not in the index at all now that nodes are created only for
    # edges that survive, so there is no node a cell could snap to and read a fabricated time.
    assert not np.isinf(T).any(), "every node in the index has a real time"
    orphan_x = idx.geoms[0].coords[0][0]
    assert all(abs(g.coords[0][0] - orphan_x) < 2000 for g in idx.geoms), \
        "the far-away orphan geometry is gone from the index"


def test_root_orientation_is_derived_from_origins_when_geometry_points_inward():
    """Codex pass-7 C5, first half, reproduced. The root's stored geometry runs TOWARD the
    destination, so its near end is coords[-1]. The old code assumed coords[0] unconditionally and
    put 0 s at the far node while giving the destination itself a full edge traversal."""
    dest = (-79.000, 35.900)
    feats = [feat([[-79.001, 35.900], [-79.000, 35.900]], 100.0, 90.0, 1)]   # points inward
    idx, T = expansion_to_edge_index(feats, target_crs=CRS, opposites_included=True, origins=[dest])
    near = idx.end_idx[0]      # coords[-1] is the destination
    far = idx.start_idx[0]
    assert T[near] == 0.0, "the destination is at time zero"
    assert T[far] == 100.0


def test_root_orientation_falls_back_to_successors_without_origins():
    feats = [
        feat([[-79.001, 35.900], [-79.000, 35.900]], 100.0, 90.0, 1),        # points inward
        feat([[-79.001, 35.900], [-79.002, 35.900]], 200.0, 180.0, 2, 1),    # leaves via -79.001
    ]
    idx, T = expansion_to_edge_index(feats, target_crs=CRS, opposites_included=True)
    assert sorted(round(t) for t in T) == [0, 100, 200]


def test_origins_outrank_successors_when_they_disagree():
    """The origins are authoritative: they say where the search actually started."""
    feats = [
        feat([[-79.001, 35.900], [-79.000, 35.900]], 100.0, 90.0, 1),
        feat([[-79.000, 35.900], [-79.002, 35.900]], 200.0, 180.0, 2, 1),
    ]
    # successors alone would read the shared vertex -79.000 as the FAR end, i.e. near = -79.001
    idx, T = expansion_to_edge_index(feats, target_crs=CRS, opposites_included=True)
    assert T[idx.start_idx[0]] == 0.0
    # but the origin is at -79.000, so that endpoint must be the zero
    idx2, T2 = expansion_to_edge_index(feats, target_crs=CRS, opposites_included=True, origins=[(-79.000, 35.900)])
    assert T2[idx2.end_idx[0]] == 0.0


def test_an_unorientable_root_raises_rather_than_guessing():
    """A lone root with no successor and no supplied origin is genuinely undetermined, and a guess
    lands on the destination itself where an error is maximally visible."""
    feats = [feat([[-79.000, 35.900], [-79.001, 35.900]], 100.0, 90.0, 1)]
    with pytest.raises(ValueError, match="not self-consistent"):
        expansion_to_edge_index(feats, target_crs=CRS, opposites_included=True)
    rep = {}
    with pytest.raises(ValueError, match="every expansion edge was unusable"):
        expansion_to_edge_index(feats, target_crs=CRS, opposites_included=True, strict=False, report=rep)
    assert rep["roots_unoriented"] == 1


def test_missing_duration_and_degenerate_geometry_are_skipped():
    feats = [
        {"geometry": {"type": "LineString", "coordinates": [[-79.0, 35.9], [-79.001, 35.9]]}, "properties": {"edge_id": 1}},
        feat([[-79.000, 35.900]], 50.0, 10.0, 2),
        feat([[-79.000, 35.900], [-79.001, 35.900]], 100.0, 90.0, 3),
    ]
    idx, _ = expansion_to_edge_index(feats, target_crs=CRS, opposites_included=True, origins=[(-79.000, 35.900)])
    assert len(idx.geoms) == 1


def test_coordinates_outside_the_projection_are_skipped():
    far = feat([[0.0, 0.0], [0.001, 0.0]], 100.0, 90.0, 1)
    good = feat([[-79.000, 35.900], [-79.001, 35.900]], 100.0, 90.0, 2)
    idx, _ = expansion_to_edge_index([far, good], target_crs=CRS, opposites_included=True,
                                     origins=[(-79.000, 35.900)])
    assert len(idx.geoms) == 1


def test_empty_expansion_raises():
    with pytest.raises(ValueError):
        expansion_to_edge_index([], target_crs=CRS, opposites_included=True)


def test_branching_tree_resolves_every_node():
    """One root edge with two successors branching off its far end."""
    feats = [
        feat([[-79.000, 35.900], [-79.001, 35.900]], 100.0, 90.0, 1),
        feat([[-79.001, 35.900], [-79.001, 35.901]], 160.0, 200.0, 2, 1),
        feat([[-79.001, 35.900], [-79.001, 35.899]], 180.0, 210.0, 3, 1),
    ]
    idx, T = expansion_to_edge_index(feats, target_crs=CRS, opposites_included=True)
    assert sorted(round(t) for t in T) == [0, 100, 160, 180]


# ---------------------------------------------------------------- S1.3: merging and direction

A = [-79.000, 35.900]      # the destination
B = [-79.001, 35.900]
C = [-79.000, 35.901]


def triangle_both_ways():
    """A triangle A-B-C with the destination at A, which is how an edge comes to be settled in
    **both** directions: B-C is on a route to A whichever way you cross it.

    * `B->A` and `C->A` are the two roots, at 100 s and 120 s.
    * `B->C` continues via C, so its near end is C: 120 + 50 = 170 s.
    * `C->B` continues via B, so its near end is B: 100 + 60 = 160 s.

    87.3% of physical edges in a real 60-minute drive payload were settled both ways, so this is
    the common case, not a corner one.
    """
    return [
        feat([B, A], 100.0, 90.0, 1),                 # root
        feat([C, A], 120.0, 110.0, 2),                # root
        feat([B, C], 170.0, 200.0, 3, pred_edge_id=2),
        feat([C, B], 160.0, 200.0, 4, pred_edge_id=1),
    ]


def test_the_two_directed_features_for_one_road_are_merged_into_one_edge():
    """S1.3. The adapter used to append every feature as its own geometry, so the same road entered
    the STRtree twice and `nearest()` picked one arbitrarily, carrying only that direction's time.
    Measured on a real drive payload, that moved 8.73% of cells, 99.4% of them earlier."""
    rep = {}
    idx, T = expansion_to_edge_index(triangle_both_ways(), target_crs=CRS,
                                     opposites_included=True, report=rep)
    assert rep["edges"] == 4 and rep["physical_edges"] == 3 and rep["merged_pairs"] == 1
    assert len(idx.geoms) == 3, "one entry per physical road, not per directed feature"

    bc = [i for i in range(3)
          if np.isfinite(idx.fwd_time[i]) and np.isfinite(idx.rev_time[i])]
    assert len(bc) == 1, "exactly one road here is traversable both ways"
    i = bc[0]
    assert sorted([round(idx.fwd_time[i]), round(idx.rev_time[i])]) == [50, 60], \
        "each direction keeps its own traversal time"
    assert sorted(round(t) for t in T) == [0, 100, 120]


def test_a_one_way_edge_is_closed_in_the_unused_direction():
    """The correctness half of S1.3. A cell on a one-way street must not be allowed to travel
    against it; on a real drive payload that changed 9.10% of cells and **every** change made the
    cell later, which is the only possible sign when edges are removed from a graph."""
    feats = chain()
    idx, T = expansion_to_edge_index(feats, target_crs=CRS, opposites_included=True)
    # this chain runs one way, toward the destination at the first vertex
    assert np.isinf(idx.fwd_time).all(), "the away direction is closed"
    assert np.isfinite(idx.rev_time).all(), "the toward direction is open"
    # a cell at the midpoint can still reach the destination the legal way
    mid = idx.geoms[1].interpolate(0.5, normalized=True)
    secs = cell_seconds_from_arrival(idx, T, np.array([mid.x]), np.array([mid.y]),
                                     mode="walk", max_access_m=20.0)
    assert 140.0 <= secs[0] <= 160.0, secs[0]


def test_bidirectional_fallback_is_used_only_when_opposites_were_not_requested():
    """With `skip_opposites=true` a two-way road appears once, so direction cannot be recovered and
    restricting it would block a legal move. The adapter then falls back to the old over-permissive
    marking and **says so** in the report rather than pretending to know."""
    rep = {}
    idx, _ = expansion_to_edge_index(chain(), target_crs=CRS, opposites_included=False, report=rep)
    assert rep["bidirectional_fallback"] is True
    assert np.isfinite(idx.fwd_time).all() and np.isfinite(idx.rev_time).all()
    assert np.array_equal(idx.fwd_time, idx.rev_time)

    rep2 = {}
    expansion_to_edge_index(chain(), target_crs=CRS, opposites_included=True, report=rep2)
    assert rep2["bidirectional_fallback"] is False


def test_opposites_in_the_payload_do_not_contradict_opposites_included_false():
    """`skip_opposites=true` does NOT suppress every opposite: 664 of 253,635 physical edges
    (0.26%) still arrived both ways on a real drive payload. So "some edges appear in both
    directions" is not evidence the flag was off, and the adapter records what it found instead of
    refusing the payload. The real signature of `skip_opposites=true` is a non-zero dangling count,
    which `strict` already refuses."""
    rep = {}
    idx, T = expansion_to_edge_index(triangle_both_ways(), target_crs=CRS,
                                     opposites_included=False, report=rep)
    assert rep["merged_pairs"] == 1 and rep["bidirectional_fallback"] is True
    assert np.array_equal(idx.fwd_time, idx.rev_time), "the fallback marks both ways"
    # and the merged pair keeps the cheaper of the two directions under the fallback
    i = int(np.argmin(np.abs(idx.fwd_time - 50.0)))
    assert round(float(idx.fwd_time[i])) == 50


def test_a_merged_edge_takes_the_lower_time_for_each_direction():
    """Parallel settlements of the same direction can occur; the cheaper one wins, matching
    `EdgeIndex.from_graph`'s rule so the two index builders cannot disagree."""
    root = feat([[-79.000, 35.900], [-79.001, 35.900]], 100.0, 90.0, 1)
    coords = [[-79.001, 35.900], [-79.002, 35.900]]
    feats = [root,
             feat(coords, 200.0, 100.0, 2, 1),       # tau 100
             feat(coords, 160.0, 100.0, 4, 1)]       # tau 60, same direction
    rep = {}
    idx, T = expansion_to_edge_index(feats, target_crs=CRS, opposites_included=True, report=rep)
    assert rep["physical_edges"] == 2 and rep["merged_pairs"] == 1
    settled = np.fmin(idx.fwd_time, idx.rev_time)
    assert round(float(settled[1])) == 60
