import numpy as np
import pytest

from locfinder.grid import MAX_MINUTES, NODATA, GridSpec, encode_minutes


def test_grid_from_bbox_covers_bbox_with_whole_cells():
    g = GridSpec.from_bbox_wgs84(west=-79.15, south=35.80, east=-78.55, north=36.15, cell_m=100)
    assert g.crs == "EPSG:32617"
    assert g.cell_m == 100
    # ~54 km x ~39 km slice -> on the order of 540 x 390 cells, never fewer
    assert g.ncols >= 540 and g.nrows >= 390
    assert g.ncols < 700 and g.nrows < 500


def test_cell_centers_are_inside_bounds_and_row_major():
    g = GridSpec.from_bbox_wgs84(west=-79.0, south=36.0, east=-78.99, north=36.01, cell_m=100)
    xs, ys = g.cell_centers_xy()
    assert xs.shape == (g.nrows, g.ncols)
    assert np.all(xs > g.x_min) and np.all(xs < g.x_max)
    assert np.all(ys > g.y_min) and np.all(ys < g.y_max)
    # row 0 is the NORTH edge (raster convention)
    assert ys[0, 0] > ys[-1, 0]


def test_cell_centers_wgs84_round_trip():
    g = GridSpec.from_bbox_wgs84(west=-79.0, south=36.0, east=-78.99, north=36.01, cell_m=100)
    lons, lats = g.cell_centers_lonlat()
    assert lons.min() > -79.002 and lons.max() < -78.988
    assert lats.min() > 35.998 and lats.max() < 36.012


def test_encode_minutes_rounds_up_caps_and_marks_nodata():
    """`ceil`, not `rint`: 61 s is 2 minutes, because the byte is a decision input and
    `ceil(s/60) <= T` has to mean `s <= 60T`. See `encode_minutes`'s docstring."""
    seconds = np.array([0.0, 59.0, 61.0, 254 * 60.0, 300 * 60.0, np.inf, np.nan])
    out = encode_minutes(seconds)
    assert out.dtype == np.uint8
    assert list(out[:4]) == [0, 1, 2, 254]
    assert out[4] == 254          # capped, still "reachable"
    assert out[5] == NODATA       # unreachable
    assert out[6] == NODATA       # missing
    # Exactly zero stays zero; anything positive is at least one minute, which is the upper-bound
    # reading of the value and the reason it is safe to threshold.
    assert encode_minutes(np.array([0.0]))[0] == 0
    assert encode_minutes(np.array([0.1]))[0] == 1


def test_rasterio_profile_matches_grid():
    g = GridSpec.from_bbox_wgs84(west=-79.0, south=36.0, east=-78.99, north=36.01, cell_m=100)
    p = g.rasterio_profile()
    assert p["width"] == g.ncols and p["height"] == g.nrows
    assert p["dtype"] == "uint8" and p["nodata"] == NODATA
    assert p["crs"].to_string() == "EPSG:32617"
    assert p["transform"].a == 100 and p["transform"].e == -100


def test_the_grid_covers_more_ground_than_the_bbox_it_was_built_from():
    """Codex pass-11 M4. `from_bbox_wgs84` encloses the projected geographic box in an axis-aligned
    rounded UTM rectangle, and nothing masks the cells outside the original geographic bbox — 4.54%
    of the Triangle's cells. An input acquired for the geographic bbox therefore covers less ground
    than the cells it is meant to describe, so the envelope has to be derivable."""
    from locfinder.metros import TRIANGLE

    g = TRIANGLE.grid()
    w, s, e, n = g.envelope_wgs84()
    ev = TRIANGLE.evaluation
    assert w <= ev.west and s <= ev.south and e >= ev.east and n >= ev.north

    lons, lats = g.cell_centers_lonlat()
    inside = ((lons >= ev.west) & (lons <= ev.east) & (lats >= ev.south) & (lats <= ev.north))
    assert (~inside).any(), "some cell centres fall outside the geographic evaluation bbox"
    # and every cell centre is inside the derived envelope, which is the point of it
    assert ((lons >= w) & (lons <= e) & (lats >= s) & (lats <= n)).all()


def test_the_envelope_bounds_every_cell_even_when_the_corners_do_not():
    """Codex pass-12 M6. A UTM rectangle's top edge is a curve in latitude whose maximum sits in
    the *interior* of the edge, near the central meridian, so the four corners are not a bound.
    This is Codex's counterexample: 806 cell centres fell north of the corner-derived bound."""
    import numpy as np
    from locfinder.grid import GridSpec
    g = GridSpec("EPSG:32617", 450000, 4000000, 100, 1000, 10)
    west, south, east, north = g.envelope_wgs84()
    lon, lat = g.cell_centers_lonlat()
    outside = int(((lat > north) | (lat < south) | (lon > east) | (lon < west)).sum())
    assert outside == 0, f"{outside} cell centres fall outside the envelope"

    # and the corner-only method really does fail here, so the test is not vacuous
    from pyproj import Transformer
    to_wgs = Transformer.from_crs(g.crs, "EPSG:4326", always_xy=True)
    _, corner_lats = to_wgs.transform([g.x_min, g.x_max, g.x_min, g.x_max],
                                      [g.y_min, g.y_min, g.y_max, g.y_max])
    assert float(lat.max()) > max(corner_lats), \
        "the counterexample no longer exercises the defect"


def test_the_envelope_is_padded_outward_not_inward():
    """An acquisition bound must never be tighter than the ground it is meant to cover."""
    from locfinder.grid import GridSpec
    g = GridSpec("EPSG:32617", 450000, 4000000, 100, 1000, 10)
    tight = g.envelope_wgs84(pad_deg=0.0)
    padded = g.envelope_wgs84()
    assert padded[0] < tight[0] and padded[1] < tight[1]
    assert padded[2] > tight[2] and padded[3] > tight[3]


# --------------------------------------------------------------------------------------------
# cell_for_xy / cell_for_lonlat: the reverse mapping, added for S3 step 0's walked-journey audit.
# A grid with no footprint test cannot answer "which published cell applies to this address", and
# the audit's whole purpose is to compare a published cell against a journey walked from a door
# inside it.
# --------------------------------------------------------------------------------------------

def _small() -> GridSpec:
    """A hand-built grid, so the expected answers are arithmetic rather than projection output."""
    return GridSpec("EPSG:32617", 450000.0, 4000000.0, 100.0, 10, 8)


def test_cell_for_xy_maps_the_four_corners():
    g = _small()
    # Only the north-west corner is inside: the bounds are closed on the north and west edges.
    assert g.cell_for_xy(g.x_min, g.y_max) == (0, 0)
    assert g.cell_for_xy(g.x_max, g.y_max) is None
    assert g.cell_for_xy(g.x_min, g.y_min) is None
    assert g.cell_for_xy(g.x_max, g.y_min) is None
    # A hair inside each of the other three is the corresponding corner cell, so the exclusions
    # above are the half-open convention and not a missing column or row.
    e = 1e-6
    assert g.cell_for_xy(g.x_max - e, g.y_max) == (0, g.ncols - 1)
    assert g.cell_for_xy(g.x_min, g.y_min + e) == (g.nrows - 1, 0)
    assert g.cell_for_xy(g.x_max - e, g.y_min + e) == (g.nrows - 1, g.ncols - 1)


def test_cell_for_xy_bounds_are_half_open_in_both_directions():
    g = _small()
    # x increases eastward with the column index: a boundary belongs to the cell east of it.
    assert g.cell_for_xy(450100.0, 3999950.0) == (0, 1)
    assert g.cell_for_xy(450099.999, 3999950.0) == (0, 0)
    # y decreases southward as the row index increases: a boundary belongs to the cell south of
    # it, which is the direction a sign error would invert.
    assert g.cell_for_xy(450050.0, 3999900.0) == (1, 0)
    assert g.cell_for_xy(450050.0, 3999900.001) == (0, 0)


def test_cell_for_xy_returns_none_outside_and_never_clamps():
    """Clamping would manufacture a verdict for a place the layer does not cover."""
    g = _small()
    mid_x, mid_y = g.x_min + 500.0, g.y_max - 400.0
    outside = [
        (g.x_min - 0.001, mid_y), (g.x_max, mid_y), (g.x_max + 10_000.0, mid_y),
        (mid_x, g.y_max + 0.001), (mid_x, g.y_min), (mid_x, g.y_min - 10_000.0),
        (g.x_min - 1.0, g.y_max + 1.0),
    ]
    for x, y in outside:
        assert g.cell_for_xy(x, y) is None, f"({x}, {y}) was placed in a cell"


def test_cell_for_lonlat_recovers_every_cell_from_its_own_centre():
    """The round trip against `cell_centers_lonlat`, exhaustively on a small grid."""
    g = GridSpec.from_bbox_wgs84(west=-79.0, south=36.0, east=-78.99, north=36.01, cell_m=100)
    lons, lats = g.cell_centers_lonlat()
    assert g.nrows * g.ncols > 50, "the grid shrank; this test is no longer exhaustive enough"
    for row in range(g.nrows):
        for col in range(g.ncols):
            got = g.cell_for_lonlat(float(lons[row, col]), float(lats[row, col]))
            assert got == (row, col), f"centre of {(row, col)} came back as {got}"


def test_cell_for_lonlat_recovers_sampled_cells_of_the_real_triangle_grid():
    """And on the grid the published layers actually use, where the projection is not the
    identity and a row/column transposition would survive a square test grid."""
    from locfinder.metros import TRIANGLE

    g = TRIANGLE.grid()
    assert g.nrows != g.ncols, "a transposition would be invisible on a square grid"
    lons, lats = g.cell_centers_lonlat()
    rng = np.random.default_rng(20261109)
    rows = rng.integers(0, g.nrows, 300)
    cols = rng.integers(0, g.ncols, 300)
    for row, col in zip(rows.tolist(), cols.tolist()):
        got = g.cell_for_lonlat(float(lons[row, col]), float(lats[row, col]))
        assert got == (row, col), f"centre of {(row, col)} came back as {got}"


def test_cell_for_xy_rejects_a_non_finite_coordinate():
    """NaN is not a point outside the footprint - it is not a point. Returning `None` would
    launder a malformed input into an ordinary negative answer, which is the same defect as the
    NaN origin that manufactures an authoritative `NO_PATH` (plan 0, step 1)."""
    g = _small()
    for bad in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError, match="non-finite"):
            g.cell_for_xy(bad, 4000000.0)
        with pytest.raises(ValueError, match="non-finite"):
            g.cell_for_xy(450000.0, bad)
        with pytest.raises(ValueError, match="non-finite"):
            g.cell_for_lonlat(bad, 36.0)
        with pytest.raises(ValueError, match="non-finite"):
            g.cell_for_lonlat(-79.0, bad)


def test_cell_for_lonlat_rejects_a_coordinate_that_does_not_project():
    """pyproj returns `inf` for a latitude past the pole, which would otherwise read as a
    well-formed point that happens to lie outside the grid."""
    g = _small()
    for lat in (95.0, 91.0, -95.0):
        with pytest.raises(ValueError, match="does not project"):
            g.cell_for_lonlat(-79.0, lat)
    # A longitude outside [-180, 180] does project, to somewhere far away, so it is merely
    # outside. Declaring the admissible input domain is plan 0 step 1's job, not this method's.
    assert g.cell_for_lonlat(500.0, 36.0) is None


def test_cell_for_xy_bounds_survive_an_awkward_origin_and_cell_size():
    """Codex pass 26: testing the *derived index* instead of the coordinate lets rounding in
    `(x - x_min) / cell_m` contradict the declared bounds in both directions."""
    g = GridSpec("EPSG:32617", 450000.1, 4000000.0, 123.4, 643, 5)
    y = g.y_max - 1.0
    # x_max is outside by the half-open rule, and used to divide into column ncols - 1.
    assert g.cell_for_xy(g.x_max, y) is None
    # One ulp inside is the last column, and used to divide into ncols and read as outside.
    assert g.cell_for_xy(float(np.nextafter(g.x_max, -np.inf)), y) == (0, g.ncols - 1)
    # Same in the other axis.
    assert g.cell_for_xy(g.x_min, g.y_min) is None
    assert g.cell_for_xy(g.x_min, float(np.nextafter(g.y_min, np.inf))) == (g.nrows - 1, 0)

    # A cell far smaller than its origin's magnitude, where the division has no margin at all.
    tiny = GridSpec("EPSG:32617", 0.1, 4000000.0, 0.3, 643, 2)
    assert tiny.cell_for_xy(float(np.nextafter(tiny.x_max, -np.inf)), tiny.y_max) == (
        0, tiny.ncols - 1)
    assert tiny.cell_for_xy(tiny.x_max, tiny.y_max) is None


def test_the_encoded_minute_reproduces_the_float_verdict_at_every_ui_threshold():
    """The property the switch to `ceil` buys, over the whole domain the UI can produce.

    The browser thresholds the minute byte directly against an integer-minute slider
    (`min="1" max="60" step="1"`), so `encode_minutes(s) <= T` must agree with `s <= 60T` for every
    one of those thresholds or the published region is not the region we computed. `rint` disagreed
    101,199 times over this sample and `floor` 201,958; the point of `ceil` is that it is exact by
    construction, so this is a regression test rather than a measurement.
    """
    rng = np.random.default_rng(7)
    seconds = np.concatenate([rng.uniform(0.0, 3700.0, 50_000),
                              np.arange(0.0, 3700.0, 0.5)])   # every half-second boundary too
    enc = encode_minutes(seconds)
    for t_min in range(1, 61):
        assert np.array_equal(enc <= t_min, seconds <= 60.0 * t_min), \
            f"the encoded verdict differs from the float verdict at {t_min} min"


def test_the_encoded_minute_cannot_be_reproduced_under_rint():
    """Why this was a correctness fix and not a calibration one: `rint` gives cells at 590 s and
    610 s the same code, so at a 10-minute threshold no decoding rule can separate a pass from a
    fail. The information is not in the raster. `ceil` keeps them apart."""
    assert np.rint(590.0 / 60.0) == np.rint(610.0 / 60.0) == 10
    assert list(encode_minutes(np.array([590.0, 610.0]))) == [10, 11]
    assert (590.0 <= 600.0) and not (610.0 <= 600.0)


def test_encode_minutes_clips_so_a_capped_cell_can_pass_a_threshold_it_fails():
    """The clip at 254 is the one place the exactness above does not hold, which is why the claim
    is stated for thresholds below `MAX_MINUTES`: a 300-minute journey encodes to 254 and would
    pass a 254-minute threshold it fails by three quarters of an hour. The UI's slider stops at 60,
    so nothing reaches it today."""
    assert encode_minutes(np.array([300.0 * 60.0]))[0] == MAX_MINUTES
    assert encode_minutes(np.array([254.0 * 60.0]))[0] == MAX_MINUTES
    # And NODATA is not a minute at all, so it must be masked rather than compared.
    assert encode_minutes(np.array([np.inf]))[0] == NODATA
    assert NODATA > MAX_MINUTES, "NODATA must not be comparable as a minute value"
