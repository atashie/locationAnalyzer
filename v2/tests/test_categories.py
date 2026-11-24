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
# ----------------------------------------------------------------------------------------------
# Owner inclusions and a class-filtered category.
#
# Owner decision 2026-11-23, ask 13(a): the layer a household is served by default becomes
# `supermarket` -- "a supermarket you could do a weekly shop at" -- with the broader grocery set
# switchable on. That makes `supermarket` a PUBLISHED category for the first time, and the 23
# owner admissions were keyed on `grocery` when `grocery` was the only published one.


def _frame(rows):
    import geopandas as gpd
    from shapely.geometry import Point

    return gpd.GeoDataFrame(
        rows, geometry=[Point(0, i) for i in range(len(rows))], crs="EPSG:4326")


#: A record that needs its inclusion to be selected at all: `department_store` is outside the
#: `grocery_store` hierarchy, which is exactly WHY the owner had to admit the real ones by hand.
ADMITTED_WALMART = {
    "id": "admitted-walmart",
    "taxonomy": {"primary": "department_store", "hierarchy": ["shopping", "department_store"]},
    "brand": {"names": {"primary": "Walmart"}},
}
#: Same shape, but the brand puts it in the SPECIALTY class.
ADMITTED_SPECIALTY = {
    "id": "admitted-specialty",
    "taxonomy": {"primary": "department_store", "hierarchy": ["shopping", "department_store"]},
    # A real entry from `SPECIALTY_BRANDS`. `Trader Joe's` is NOT one: this project's table calls
    # it a supermarket, which the first draft of this test got wrong.
    "brand": {"names": {"primary": "Patel Brothers"}},
}


def test_an_owner_admission_reaches_a_class_filtered_category(monkeypatch):
    """Without this, publishing the `supermarket` layer silently drops every record the owner
    admitted by hand -- 20 of the 23 being Aldi, Walmart and Publix stores that
    `classify_grocery` itself calls supermarkets. The admissions exist BECAUSE Overture does not
    file those records under `grocery_store`, so nothing but the inclusion can select them, and a
    default layer missing 20 of the metro's largest shops is the opposite of the decision it
    would be implementing."""
    from locfinder.places import exclusions
    from locfinder.places.categories import select_overture

    monkeypatch.setattr(
        exclusions, "INCLUDED_PLACE_IDS",
        {"grocery": {"admitted-walmart": "owner admission, for the test"}})
    g = _frame([ADMITTED_WALMART])
    assert list(select_overture(g, "grocery")["id"]) == ["admitted-walmart"]
    assert list(select_overture(g, "supermarket")["id"]) == ["admitted-walmart"]


def test_an_admission_still_has_to_pass_the_class_filter(monkeypatch):
    """The admission says *this is a grocery*. It does not say *this is a weekly shop*. A
    specialty grocer the owner admitted belongs in the switchable layer and not in the default
    one, so the class filter must still apply to a forced id -- today it does not, because the
    inclusion is OR-ed in after the filter has already run."""
    from locfinder.places import exclusions
    from locfinder.places.categories import select_overture

    monkeypatch.setattr(
        exclusions, "INCLUDED_PLACE_IDS",
        {"grocery": {"admitted-specialty": "owner admission, for the test"}})
    g = _frame([ADMITTED_SPECIALTY])
    assert list(select_overture(g, "grocery")["id"]) == ["admitted-specialty"]
    assert list(select_overture(g, "supermarket")["id"]) == []
    assert list(select_overture(g, "specialty_grocery")["id"]) == ["admitted-specialty"]


def test_an_exclusion_still_beats_an_admission_in_the_narrow_category(monkeypatch):
    """`EXCLUDED_PLACE_IDS` is the owner saying a record is not what it claims to be, which is a
    stronger statement than "count this one in". `test_place_exclusions` pins that precedence for
    `grocery`; widening inclusions to a second category must not open a route around it."""
    from locfinder.places import exclusions
    from locfinder.places.categories import select_overture

    monkeypatch.setattr(
        exclusions, "INCLUDED_PLACE_IDS",
        {"grocery": {"admitted-walmart": "owner admission, for the test"}})
    # `drop_excluded` reads the DERIVED set, which is frozen at import out of
    # `EXCLUDED_PLACE_IDS` and `FSQ_CONFIRMED_CLOSURES`. Patching the source table alone changes
    # nothing, which is worth knowing: a runtime edit to `EXCLUDED_PLACE_IDS` does not remove a
    # record.
    monkeypatch.setattr(
        exclusions, "DROPPED_PLACE_IDS", frozenset({"admitted-walmart"}))
    g = _frame([ADMITTED_WALMART])
    assert list(select_overture(g, "grocery")["id"]) == []
    assert list(select_overture(g, "supermarket")["id"]) == []
