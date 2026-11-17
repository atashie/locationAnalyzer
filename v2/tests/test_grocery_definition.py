"""What a household means by "ten minutes from a grocery".

Owner decision, 2026-11-17: *"the general meaning should default to 'a supermarket you could do a
weekly shop at'"*, with specialty grocers selectable separately or in combination; and for the
classification, *"use big brands, and a curated list for the independents that we can build / add
to over time."*

So membership is decided by two explicit tables and nothing else. No heuristic on the name, because
the name is exactly where this data is worst: the 26 brands in the open grocery set include
**Bitcoin Depot**, **Regency Centers** (a shopping-centre REIT), **Pet Dairy**, and a
**"Food Lion- Summersville, WV"** — in North Carolina.
"""
import geopandas as gpd
import pytest
from shapely.geometry import Point

from locfinder.places.grocery import (CURATED_INDEPENDENT_SUPERMARKETS, NOT_A_GROCERY_BRANDS,
                                      SPECIALTY_BRANDS, SUPERMARKET_BRANDS, classify_grocery)


def rec(brand=None, place_id="x", primary="grocery_store"):
    return {"id": place_id,
            "brand": ({"names": {"primary": brand}} if brand else None),
            "taxonomy": {"primary": primary, "hierarchy": ["grocery_store"]}}


def test_the_big_chains_are_supermarkets():
    for b in ("Food Lion", "Harris Teeter", "Lowes Foods", "Publix", "ALDI", "Lidl",
              "Trader Joe's", "Whole Foods Market", "Walmart"):
        assert classify_grocery(rec(brand=b)) == "supermarket", b


def test_specialty_brands_are_not_supermarkets():
    for b in ("Patel Brothers", "Grand Asia Market", "Suvidha Indo-Pak Groceries"):
        assert classify_grocery(rec(brand=b)) == "specialty", b


def test_a_brand_naming_a_non_grocery_BUSINESS_is_rejected():
    """A property REIT on a place named 'Market at Colonnade Center' -- that is the mall, not a
    shop in it -- a dairy brand on a place named 'Pet Dairy', and a misbranded depot."""
    for b in ("Regency Centers", "Pet Dairy", "Food Lion- Summersville, WV"):
        assert classify_grocery(rec(brand=b)) == "not_a_grocery", b


def test_a_brand_naming_a_VENDOR_INSIDE_the_shop_is_not_a_rejection():
    """'Bitcoin Depot' is the crypto ATM standing in a place actually named *Casablanca Market*.

    The brand is junk; the shop may be a perfectly real grocery. Rejecting on it would delete a
    business because of a machine in its corner, so the record falls through to `unclassified`
    and waits for somebody to look at it. The distinction that matters is whether the brand names
    the BUSINESS AT THAT ADDRESS or merely something standing inside it.
    """
    assert classify_grocery(rec(brand="Bitcoin Depot")) == "unclassified"


def test_an_unbranded_record_is_unclassified_until_somebody_curates_it():
    """323 of 541 carry no brand. The owner's rule is a curated list, so the honest default for a
    record nobody has looked at is 'unclassified' -- NOT 'supermarket' and NOT 'specialty'."""
    assert classify_grocery(rec(brand=None, place_id="never-seen")) == "unclassified"


def test_a_curated_independent_is_a_supermarket():
    assert CURATED_INDEPENDENT_SUPERMARKETS, "the curated list is empty"
    some_id = next(iter(CURATED_INDEPENDENT_SUPERMARKETS))
    assert classify_grocery(rec(brand=None, place_id=some_id)) == "supermarket"


def test_every_curated_independent_records_why():
    for place_id, reason in CURATED_INDEPENDENT_SUPERMARKETS.items():
        assert len(place_id) == 36, f"{place_id!r} is not an Overture uuid"
        assert len(reason) > 30, f"{place_id} has no usable reason: {reason!r}"


def test_a_specialty_taxonomy_primary_is_specialty_even_without_a_brand():
    """The 18 records carrying `mexican_grocery_store` and friends are self-declaring."""
    assert classify_grocery(rec(brand=None, primary="mexican_grocery_store")) == "specialty"
    assert classify_grocery(rec(brand=None, primary="organic_grocery_store")) == "specialty"


def test_the_three_brand_tables_do_not_overlap():
    assert not (SUPERMARKET_BRANDS & SPECIALTY_BRANDS)
    assert not (SUPERMARKET_BRANDS & NOT_A_GROCERY_BRANDS)
    assert not (SPECIALTY_BRANDS & NOT_A_GROCERY_BRANDS)


def test_select_target_supermarket_returns_only_supermarkets():
    from locfinder.places.categories import select_target
    tax = {"primary": "grocery_store", "hierarchy": ["grocery_store"]}
    spec = {"primary": "mexican_grocery_store", "hierarchy": ["grocery_store"]}
    g = gpd.GeoDataFrame(
        {"id": ["a", "b", "c"],
         "taxonomy": [tax, spec, tax],
         "brand": [{"names": {"primary": "Food Lion"}}, None,
                   {"names": {"primary": "Bitcoin Depot"}}]},
        geometry=[Point(0, 0), Point(1, 0), Point(2, 0)], crs="EPSG:32617")
    assert list(select_target(g, "supermarket")["id"]) == ["a"]


def test_grocery_still_means_what_it_meant():
    """The published layer is built from `grocery`, and changing its meaning silently would
    change every published grocery number without a rebuild saying so."""
    from locfinder.places.categories import select_target
    tax = {"primary": "grocery_store", "hierarchy": ["grocery_store"]}
    spec = {"primary": "mexican_grocery_store", "hierarchy": ["grocery_store"]}
    g = gpd.GeoDataFrame(
        {"id": ["a", "b"], "taxonomy": [tax, spec], "brand": [None, None]},
        geometry=[Point(0, 0), Point(1, 0)], crs="EPSG:32617")
    assert sorted(select_target(g, "grocery")["id"]) == ["a", "b"]


# ---------------------------------------------------------------- closures

def test_the_confirmed_kroger_closure_is_excluded():
    """Overture-signals at confidence 1.0, and OSM shows a Harris Teeter operating at that spot."""
    from locfinder.places.exclusions import EXCLUDED_PLACE_IDS
    assert any("Kroger" in r for r in EXCLUDED_PLACE_IDS.values())


def test_the_eight_registry_closures_are_pending_not_applied():
    """BrightQuery is a business registry. A deregistered entity is not a closed storefront, so
    these are recorded for triage and deliberately NOT removed."""
    from locfinder.places.exclusions import EXCLUDED_PLACE_IDS, PENDING_CLOSURES
    assert len(PENDING_CLOSURES) == 8, f"{len(PENDING_CLOSURES)} pending, expected 8"
    for place_id, reason in PENDING_CLOSURES.items():
        assert place_id not in EXCLUDED_PLACE_IDS, f"{place_id} is pending AND excluded"
        assert "BrightQuery" in reason, f"{place_id} does not record its source"
