import pytest

from locfinder.metros import SLICE, TRIANGLE, BBox, Metro, get_metro


def test_triangle_includes_the_places_the_slice_excluded():
    """The Phase 0 defect: these three were south of the slice edge, so their isochrones were
    truncated by the extract boundary rather than by travel time."""
    missing = {"Downtown Raleigh": (35.7796, -78.6382),
               "Cary Downtown": (35.7880, -78.7810),
               "NC State Bell Tower": (35.7860, -78.6630)}
    for name, (lat, lon) in missing.items():
        assert not SLICE.evaluation.contains(lat, lon), f"{name} should be outside the old slice"
        assert TRIANGLE.evaluation.contains(lat, lon), f"{name} must be inside the Triangle metro"


def test_triangle_keeps_the_original_anchors():
    for lat, lon in [(35.9049, -79.0469), (36.0075, -78.9381), (35.8720, -78.8450),
                     (36.0750, -79.0990), (35.8776, -78.7875)]:
        assert TRIANGLE.evaluation.contains(lat, lon)


def test_routing_bbox_strictly_contains_the_evaluation_bbox():
    for m in (SLICE, TRIANGLE):
        e, r = m.evaluation, m.routing
        assert r.west < e.west and r.south < e.south and r.east > e.east and r.north > e.north


def test_a_metro_without_a_routing_buffer_is_rejected():
    same = BBox(-79.0, 35.9, -78.9, 36.0)
    with pytest.raises(AssertionError):
        Metro(name="bad", evaluation=same, routing=same, cell_m=100.0, crs="EPSG:32617")


def test_triangle_grid_is_larger_than_the_slice_grid():
    s, t = SLICE.grid(), TRIANGLE.grid()
    assert t.ncols > s.ncols and t.nrows > s.nrows
    assert t.cell_m == 100.0 and t.crs == "EPSG:32617"
    # a ~63 km x ~50 km metro at 100 m
    assert 600 <= t.ncols <= 720 and 480 <= t.nrows <= 560


def test_default_metro_is_the_triangle():
    assert get_metro().name == "triangle"
    assert get_metro("slice").name == "slice"


def test_buffered_expands_every_side():
    b = BBox(-79.0, 35.9, -78.9, 36.0).buffered(0.1)
    assert (b.west, b.south, b.east, b.north) == pytest.approx((-79.1, 35.8, -78.8, 36.1))


def test_as_osmium_is_west_south_east_north():
    assert TRIANGLE.routing.as_osmium() == "-79.35,35.55,-78.35,36.3"
