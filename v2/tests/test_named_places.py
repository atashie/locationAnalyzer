"""A specific place can be a layer target, and its coordinate is in git with its provenance.

Two of the six criteria the owner asked for on 2026-11-16 are single destinations -- a place of
work and an airport -- not wedge categories. These tests pin the three things that make that safe:
the slug is filename-safe, the frame is shaped like the one the builders already consume, and the
registry says where each point came from.
"""
import geopandas as gpd
import pytest
import shapely

from locfinder.places.categories import select_target
from locfinder.places.named_places import (NAMED_PLACES, is_named_place, named_place,
                                           select_named)


def a_places_frame(crs="EPSG:32617"):
    """A frame shaped like the accepted-places parquet, so `select_target` can dispatch on it."""
    return gpd.GeoDataFrame(
        {"id": ["a", "b"],
         "names": [{"primary": "A Grocery"}, {"primary": "B Grocery"}],
         "taxonomy": [{"primary": "grocery_store", "hierarchy": ["grocery_store"]},
                      {"primary": "restaurant", "hierarchy": ["restaurant"]}]},
        geometry=[shapely.Point(-79.0, 35.9), shapely.Point(-79.1, 35.95)],
        crs="EPSG:4326").to_crs(crs)


def test_every_slug_is_filename_safe():
    """The slug becomes the layer's `category`, which lands in every filename the build writes.
    A colon or a comma in it is unopenable on Windows, and the first design put the coordinate
    itself in the target string."""
    for slug in NAMED_PLACES:
        assert slug == slug.lower()
        assert all(c.isalnum() or c == "-" for c in slug), slug


def test_every_named_place_says_where_its_points_came_from():
    """A coordinate with no provenance is one somebody typed from memory. Ledger instance 52 was
    exactly that: a query point promoted into a recorded door."""
    for slug, entry in NAMED_PLACES.items():
        assert entry["source"].strip(), slug
        assert entry["label"].strip(), slug
        assert entry["points"], slug
        for lon, lat in entry["points"]:
            assert -180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0, (slug, lon, lat)


def test_every_named_place_is_inside_the_published_bounds():
    """A destination outside the published raster cannot be routed to from any cell in it, and the
    layer would be uniformly unreachable rather than visibly broken."""
    from locfinder.metros import get_metro
    e = get_metro("triangle").evaluation
    for slug, entry in NAMED_PLACES.items():
        for lon, lat in entry["points"]:
            assert e.west <= lon <= e.east, (slug, lon)
            assert e.south <= lat <= e.north, (slug, lat)


def test_the_frame_is_shaped_like_the_one_the_builders_consume():
    """`g1_own_graph_layer` and `s2_building_weighted_coverage` read `.geometry` and `names` off
    whatever the selector returns. If a named place returned a different shape the builders would
    need a branch, and the branch is the thing this design exists to avoid."""
    got = select_named("duke-hospital", "EPSG:32617")
    assert list(got.columns) == ["names", "geometry"]
    assert got.crs.to_epsg() == 32617
    assert len(got) == len(NAMED_PLACES["duke-hospital"]["points"])
    assert got["names"].iloc[0] == {"primary": "Duke University Hospital"}


def test_the_airport_is_two_points_under_one_label():
    """"The airport" is two terminals. Labelling them separately would invite a consumer to answer
    "RDU Terminal 1" when the household asked for the airport."""
    got = select_named("rdu-airport", "EPSG:4326")
    assert len(got) == 2
    assert {n["primary"] for n in got["names"]} == {"RDU airport"}


def test_select_target_dispatches_on_the_slug_not_the_frame():
    """One selector, two kinds of target. A category still selects from the frame; a named place
    ignores the frame entirely and returns its own points."""
    places = a_places_frame()
    by_category = select_target(places, "grocery")
    assert len(by_category) == 1 and by_category["names"].iloc[0]["primary"] == "A Grocery"

    by_place = select_target(places, "duke-hospital")
    assert by_place["names"].iloc[0]["primary"] == "Duke University Hospital"
    assert by_place.crs == places.crs


def test_an_unknown_target_raises_rather_than_selecting_nothing():
    """A typo returning an empty frame would build a layer with no destinations -- every cell
    unreachable, and nothing saying why."""
    with pytest.raises(KeyError):
        select_target(a_places_frame(), "duke_hospital")
    with pytest.raises(KeyError):
        named_place("not-a-place")


def test_is_named_place_is_exact_not_prefix():
    assert is_named_place("rdu-airport")
    assert not is_named_place("rdu")
    assert not is_named_place("grocery")
