import numpy as np

from locfinder.grid import GridSpec, NODATA, encode_minutes


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


def test_encode_minutes_rounds_caps_and_marks_nodata():
    seconds = np.array([0.0, 59.0, 61.0, 254 * 60.0, 300 * 60.0, np.inf, np.nan])
    out = encode_minutes(seconds)
    assert out.dtype == np.uint8
    assert list(out[:4]) == [0, 1, 1, 254]
    assert out[4] == 254          # capped, still "reachable"
    assert out[5] == NODATA       # unreachable
    assert out[6] == NODATA       # missing


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
