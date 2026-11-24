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


#: Held on 2026-11-17, then removed under owner ask 15 on 2026-11-23 for a different and stronger
#: reason. Named here so the table shrinking from eight to seven is a fact a test knows, not a
#: number that moved.
SUPERSEDED_PENDING_CLOSURES = (
    "4f318935-7d66-4a5e-833a-1131fdf4b4fe",   # Longview Poole Road -- a municipal asset record
    "dc09b073-d0ac-4141-8275-3127c748878d",   # Roofing Inc. -- a roofing contractor
)


def test_the_registry_closures_are_pending_not_applied():
    """BrightQuery is a business registry. A deregistered entity is not a closed storefront, so
    these are recorded for triage and deliberately NOT removed.

    Six, not the original eight. `Longview Poole Road` and `Roofing Inc.` left the layer under ask
    15, on what the records ARE rather than on whether a registry entity deregistered. A record
    cannot be both held and removed, and the next test asserts both supersessions are written down
    rather than the count merely being smaller.
    """
    from locfinder.places.exclusions import EXCLUDED_PLACE_IDS, PENDING_CLOSURES
    assert len(PENDING_CLOSURES) == 6, f"{len(PENDING_CLOSURES)} pending, expected 6"
    for place_id, reason in PENDING_CLOSURES.items():
        assert place_id not in EXCLUDED_PLACE_IDS, f"{place_id} is pending AND excluded"
        assert "BrightQuery" in reason, f"{place_id} does not record its source"


def test_the_superseded_hold_is_recorded_and_not_merely_dropped():
    """A table that quietly loses a row has lost the decision with it. The record must be out of
    the pending table, in the excluded table, and its history must still be readable."""
    import inspect

    from locfinder.places import exclusions
    from locfinder.places.exclusions import EXCLUDED_PLACE_IDS, PENDING_CLOSURES

    for place_id in SUPERSEDED_PENDING_CLOSURES:
        assert place_id not in PENDING_CLOSURES, place_id
        assert place_id in EXCLUDED_PLACE_IDS, place_id
    module = inspect.getsource(exclusions)
    assert "SIX REMAIN" in module, "the supersessions are not recorded beside the table"
    note = module.split("SIX REMAIN")[1][:3000]
    assert note.count("BrightQuery") >= 2, (
        "the note does not keep what BrightQuery asserted for both records")
    for place_id in SUPERSEDED_PENDING_CLOSURES:
        assert place_id in note, f"{place_id} is not named in the supersession note"
# ----------------------------------------------------------------------------------------------
# Owner ask 18, 2026-11-23: the three admitted chain stores the automatic routes cannot see.

#: Owner admissions that classified as `unclassified` until this table existed, so they were
#: selected into `grocery` and dropped from `supermarket`.
ASK_18_IDS = {
    "5074229c-e884-4097-8759-4308ddbab7e8": "Publix Super Market at Buffaloe Bend",
    "c7fee873-a3c5-4691-8b12-f2c76bb101b9": "Publix Super Market at Middle Creek Crossings",
    "182dc975-ff2e-4be1-8811-0dc710b42547": "Walmart Supercenter",
}


def test_each_ask_18_record_is_a_supermarket():
    """Not `unclassified`. The default layer is the one a household opens with, and these are a
    Publix, a Publix and a Walmart Supercenter."""
    from locfinder.places.grocery import CURATED_CHAIN_SUPERMARKETS, classify_grocery

    for place_id, name in ASK_18_IDS.items():
        assert place_id in CURATED_CHAIN_SUPERMARKETS, name
        assert classify_grocery({"id": place_id}) == "supermarket", name


def test_the_curated_chain_table_is_not_consulted_through_the_name_flag():
    """`classify_grocery(consult_name_table=False)` exists so `recover_brandless_by_name.py` can
    ask what the answer would be WITHOUT its own output, which is how it keeps finding its
    candidates after writing them down. A hand-curated decision is not that script's output and
    must survive the flag being off -- otherwise the recovery script would keep re-proposing these
    three forever."""
    from locfinder.places.grocery import classify_grocery

    for place_id, name in ASK_18_IDS.items():
        assert classify_grocery({"id": place_id}, consult_name_table=False) == "supermarket", name


def test_the_curated_chain_table_is_written_by_no_script():
    """It is a judgement, not a derivation. `NAME_CONFIRMED_SUPERMARKETS` is regenerated by
    `recover_brandless_by_name.py` and `OSM_CONFIRMED_SUPERMARKETS` by `prefill_from_osm.py`, so an
    entry in either is erased by the next data refresh. This asserts no script under `scripts/`
    emits this table's name, which is what "curated" has to mean to be worth anything."""
    import pathlib

    scripts = pathlib.Path(__file__).resolve().parents[1] / "scripts"
    writers = [p.name for p in sorted(scripts.glob("*.py"))
               if "CURATED_CHAIN_SUPERMARKETS" in p.read_text(encoding="utf-8")]
    assert writers == [], f"a script emits the curated table: {writers}"


def test_every_ask_18_entry_names_its_own_evidence():
    """A host building is NOT available for two of the three -- our data holds nothing within
    10.6 km and 2.8 km. So each entry has to name what it actually rests on, and a reader must be
    able to re-check it without this module."""
    from locfinder.places.grocery import CURATED_CHAIN_SUPERMARKETS

    for place_id in ASK_18_IDS:
        reason = CURATED_CHAIN_SUPERMARKETS[place_id]
        assert len(reason) > 120, reason
        assert "2026-11-23" in reason, f"{place_id} does not date the decision"
        assert "OSM" in reason, f"{place_id} does not name the OSM evidence"
        # The footprint may be MENTIONED, but only to say it cannot settle the question -- never
        # as support. For two of the three there is no building data at all; for the third the
        # area is covered and only this store's own footprint is missing. Demanding the phrase
        # "no building data" from all three, as a first draft of this test did, would have forced
        # a false statement into the Buffaloe Bend entry, where 38 buildings stand within 500 m.
        lowered = reason.lower()
        if "footprint" in lowered:
            assert ("says nothing" in lowered or "cannot be consulted" in lowered), reason
        assert "corroborated by" not in lowered, f"{place_id} offers the geometry as support"


def test_the_curated_chain_table_does_not_overlap_the_regenerable_ones():
    """The same id in a curated table and a regenerable one is a contradiction waiting for a data
    refresh to resolve it in the wrong direction."""
    from locfinder.places.grocery import (CURATED_CHAIN_SUPERMARKETS,
                                          CURATED_INDEPENDENT_SUPERMARKETS,
                                          NAME_CONFIRMED_SUPERMARKETS,
                                          OSM_CONFIRMED_SUPERMARKETS)

    curated = set(CURATED_CHAIN_SUPERMARKETS)
    assert not (curated & set(NAME_CONFIRMED_SUPERMARKETS))
    assert not (curated & set(OSM_CONFIRMED_SUPERMARKETS))
    assert not (curated & set(CURATED_INDEPENDENT_SUPERMARKETS))
