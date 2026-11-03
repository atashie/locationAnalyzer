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
