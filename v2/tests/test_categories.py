import numpy as np

from locfinder.places.categories import WEDGE_CATEGORIES, taxonomy_matches


def test_hierarchy_as_numpy_array_matches_without_truth_value_error():
    tax = {"primary": "organic_grocery_store", "hierarchy": np.array(["retail", "food_and_beverage_store", "grocery_store", "organic_grocery_store"])}
    assert taxonomy_matches(tax, WEDGE_CATEGORIES["grocery"])


def test_hierarchy_none_and_missing_taxonomy_are_false():
    assert not taxonomy_matches(None, WEDGE_CATEGORIES["grocery"])
    assert not taxonomy_matches({"primary": "restaurant", "hierarchy": None}, WEDGE_CATEGORIES["grocery"])


def test_exclusions_beat_hierarchy_membership():
    tax = {"primary": "dog_park", "hierarchy": ["leisure", "park", "dog_park"]}
    assert not taxonomy_matches(tax, WEDGE_CATEGORIES["park"])
    assert taxonomy_matches({"primary": "park", "hierarchy": ["leisure", "park"]}, WEDGE_CATEGORIES["park"])


def test_primary_match_without_hierarchy():
    assert taxonomy_matches({"primary": "coffee_shop", "hierarchy": []}, WEDGE_CATEGORIES["coffee"])
    assert not taxonomy_matches({"primary": "internet_cafe", "hierarchy": []}, WEDGE_CATEGORIES["coffee"])


def test_selection_order_is_deterministic_not_file_order():
    """Several spikes take "the first N POIs". File order is not stable across downloads:
    re-acquiring the Triangle at the routing extent changed both the row count and the ordering,
    which would have silently changed *which* three groceries an experiment used — making a
    re-measurement non-comparable for a reason nothing recorded."""
    import geopandas as gpd
    from shapely.geometry import Point

    from locfinder.places.categories import select_overture

    rows = [
        {"id": "c", "taxonomy": {"primary": "grocery_store", "hierarchy": ["grocery_store"]}},
        {"id": "a", "taxonomy": {"primary": "grocery_store", "hierarchy": ["grocery_store"]}},
        {"id": "b", "taxonomy": {"primary": "grocery_store", "hierarchy": ["grocery_store"]}},
    ]
    g = gpd.GeoDataFrame(rows, geometry=[Point(0, i) for i in range(3)], crs="EPSG:4326")
    assert list(select_overture(g, "grocery")["id"]) == ["a", "b", "c"]
    # the reverse input gives the same answer, which is the whole point
    assert list(select_overture(g.iloc[::-1], "grocery")["id"]) == ["a", "b", "c"]
