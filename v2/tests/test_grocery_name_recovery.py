"""Reading the chain out of the NAME when the `brand` field is empty.

**Owner decision 2026-11-18, third pass**, *"1-4) yes, proceed"*. `grocery.py` had said, in as
many words, *"there is deliberately no heuristic on the name, because the name and the brand are
exactly where this data is worst."* That instruction is now narrowed rather than reversed, and the
distinction is the whole design:

* **Not adopted:** parsing a name to guess what kind of shop it is.
* **Adopted:** looking up a name in the **same explicit table** the `brand` field is looked up in.

The case for it is that all three examples `grocery.py` gives for distrusting the data are cases
where the **brand** is wrong and the **name** is right -- `Bitcoin Depot` branded onto a place
*named* `Casablanca Market`, `Ray's Food Place` onto `Ray's Supermarket`, `Food Lion-
Summersville, WV` onto `Food Line Distribution Center`. Measured: **34 of the 272** unclassified
brandless grocery records are named after a chain already in `SUPERMARKET_BRANDS`, with an empty
`brand`.

Every test below is a real row from
`docs/experiments/audit/grocery-brandless-footprint-shortlist.csv`.
"""
from __future__ import annotations

import pytest

from locfinder.places.grocery import (
    BRAND_NAME_ALIASES,
    CURATED_INDEPENDENT_SUPERMARKETS,
    NOT_A_WEEKLY_SHOP_SITES,
    NAME_CONFIRMED_SUPERMARKETS,
    OSM_CONFIRMED_SPECIALTY,
    OSM_CONFIRMED_SUPERMARKETS,
    SUPERMARKET_BRANDS,
    chain_in_name,
    classify_grocery,
    names_a_service_point,
)


# ------------------------------------------------------------------ the table, through the name
@pytest.mark.parametrize(
    "name,brand",
    [
        ("Food Lion", "Food Lion"),
        ("Harris Teeter Supermarkets", "Harris Teeter"),
        ("Lowes Foods On Rowlock Way", "Lowes Foods"),
        ("Lowes Foods Of Cary On High House Road", "Lowes Foods"),
        ("Brier Creek Walmart", "Walmart"),
        ("Wal Mart", "Walmart"),
        ("ALDI", "ALDI"),
        ("Lidl", "Lidl"),
        ("Weaver Street Market, Inc", "Weaver Street Market"),
    ],
)
def test_a_chain_already_in_the_table_is_found_in_the_name(name, brand):
    assert chain_in_name(name) == brand


def test_the_apostrophe_and_the_mojibake_do_not_matter():
    """`Carlie C's Iga` arrives with a mangled apostrophe. IGA is in `SUPERMARKET_BRANDS`."""
    assert chain_in_name("Carlie C�s Iga") == "IGA"
    assert chain_in_name("Carlie C's IGA") == "IGA"


def test_only_the_existing_table_is_consulted():
    """THE POINT OF THE RULE. Kroger and Wegmans trade nearby and are NOT in `SUPERMARKET_BRANDS`,
    so the name must not conjure them. Adding a chain stays an edit to the table."""
    assert "Kroger" not in SUPERMARKET_BRANDS
    assert chain_in_name("Kroger Store") is None
    assert chain_in_name("Wegmans") is None


def test_a_chain_name_must_be_whole_words():
    """`iga` is three letters and would otherwise match inside other words."""
    assert chain_in_name("Rigaud Fine Foods") is None
    assert chain_in_name("Aldine Supply") is None


def test_a_place_with_no_chain_in_its_name_matches_nothing():
    assert chain_in_name("Tienda La Esperanza") is None
    assert chain_in_name("") is None
    assert chain_in_name("Food Line Distribution Center") is None


# ------------------------------------------------------------------- the service-point screen
@pytest.mark.parametrize(
    "name",
    [
        "Walmart Grocery Pickup and Delivery",
        "Walmart Grocery Pick Up and Delivery",
        "Weaver Street Market Administration",
        "Food Line Distribution Center",
        "Harris Teeter Corporate Office",
        "Walmart Pharmacy",
        "Food Lion Warehouse",
    ],
)
def test_a_service_point_is_not_a_place_to_do_a_weekly_shop(name):
    """NINE of the 34 are `Walmart Grocery Pickup and Delivery`, and several sit on the
    Supercenter's own 20,000 m2 footprint -- so footprint evidence CANNOT catch them and the name
    is the only thing that can. A household sent to a collection bay has been sent to the wrong
    place."""
    assert names_a_service_point(name)


@pytest.mark.parametrize(
    "name",
    [
        "Food Lion",
        "Brier Creek Walmart",
        "Harris Teeter Supermarkets",
        "Weaver Street Market, Inc",
        "Lowes Foods On Rowlock Way",
    ],
)
def test_a_real_store_is_not_screened_out(name):
    assert not names_a_service_point(name)


def test_the_screen_matches_whole_words_too():
    """`Pickupville Market` is not a collection point, and `officers` is not an office."""
    assert not names_a_service_point("Officers Club Market")
    assert not names_a_service_point("Delivered Fresh Market")


# ------------------------------------------------- the two screens are independent and both bind
def test_a_chain_name_on_a_service_point_is_found_and_then_screened():
    """`chain_in_name` deliberately still reports Walmart here. Suppressing the match inside the
    matcher would hide WHY the record was skipped, and the sheet has to show both."""
    assert chain_in_name("Walmart Grocery Pickup and Delivery") == "Walmart"
    assert names_a_service_point("Walmart Grocery Pickup and Delivery")
# ------------------------------------------------------------------- the generated table itself
def test_the_recovered_table_is_kept_apart_from_the_curated_ones():
    """A regenerable derivation is not a hand-made judgement, and a refresh of one must not be
    able to overwrite the other."""
    assert not (set(NAME_CONFIRMED_SUPERMARKETS) & set(CURATED_INDEPENDENT_SUPERMARKETS))
    assert not (set(NAME_CONFIRMED_SUPERMARKETS) & set(OSM_CONFIRMED_SUPERMARKETS))
    assert not (set(NAME_CONFIRMED_SUPERMARKETS) & set(OSM_CONFIRMED_SPECIALTY))


def test_a_recovered_record_classifies_as_a_supermarket():
    """The point of the table. Without it these records stay `unclassified` and a household
    looking for a weekly shop is not shown a Food Lion that is plainly there."""
    place_id = next(iter(NAME_CONFIRMED_SUPERMARKETS))
    assert classify_grocery({"id": place_id}) == "supermarket"


def test_an_unknown_record_is_still_unclassified():
    """`unclassified` has to stay the default, or the table would be doing nothing."""
    assert classify_grocery({"id": "not-a-real-id"}) == "unclassified"


def test_no_service_point_reached_the_table():
    """Eleven candidates were screened out as service points. If one appears here, the screen was
    bypassed somewhere between the script and the table."""
    for reason in NAME_CONFIRMED_SUPERMARKETS.values():
        assert not names_a_service_point(reason.split(" -- ")[0]), reason


def test_every_entry_names_its_chain_and_its_corroboration():
    """An entry a reader cannot re-check without re-running the script is not evidence."""
    for place_id, reason in NAME_CONFIRMED_SUPERMARKETS.items():
        assert len(place_id) == 36, f"{place_id!r} is not an Overture uuid"
        assert "SUPERMARKET_BRANDS" in reason, f"{place_id} does not say where the chain came from"
        assert "Corroborated by" in reason, f"{place_id} has no footprint corroboration"
        assert "`brand` field is EMPTY" in reason


def test_every_recovered_name_really_does_carry_a_table_chain():
    """Closes the loop: the table is only allowed to hold records the matcher would match."""
    for reason in NAME_CONFIRMED_SUPERMARKETS.values():
        assert chain_in_name(reason.split(" -- ")[0]) is not None, reason
# ==============================================================================================
# What the third adversarial review found, 2026-11-18.
# docs/reviews/2026-11-18-name-recovery-review-findings.md
# ==============================================================================================


def _bare(place_id: str) -> dict:
    """A record carrying nothing but an id: no brand, no taxonomy. The table is all that can
    classify it, which is what these tests are about."""
    return {"id": place_id, "brand": None, "taxonomy": None}


def test_the_recovery_can_be_recomputed_without_its_own_answers():
    """**Review P2-4.** `recover_brandless_by_name.py` picks its candidates by asking
    `classify_grocery` which records are still `unclassified`. Once it has written its 13 answers
    into `NAME_CONFIRMED_SUPERMARKETS`, those 13 are no longer unclassified, so a re-run skips
    them and `--emit` prints a table **without** them.

    Measured on the real data before this fix: **20 candidates where there should be 33**, so
    following the documented regeneration workflow would have silently deleted the recovery. The
    commit that created the table called it "a regenerable derivation"; that was false when it was
    written. So the question has to be askable without the answer."""
    place_id = next(iter(NAME_CONFIRMED_SUPERMARKETS))
    assert classify_grocery(_bare(place_id)) == "supermarket"
    assert classify_grocery(_bare(place_id), consult_name_table=False) == "unclassified"


def test_every_single_recovered_record_comes_back_as_a_candidate():
    """Not just one: the whole table must be re-derivable, or the next refresh loses part of it."""
    for place_id in NAME_CONFIRMED_SUPERMARKETS:
        assert classify_grocery(_bare(place_id), consult_name_table=False) == "unclassified", (
            f"{place_id} would be skipped by its own script"
        )


def test_switching_off_the_name_table_leaves_the_other_tables_alone():
    """The seam is for one table only. A refresh that also forgot the curated judgements would
    be a far worse bug than the one it fixes."""
    for table in (OSM_CONFIRMED_SUPERMARKETS, CURATED_INDEPENDENT_SUPERMARKETS):
        place_id = next(iter(table))
        assert classify_grocery(_bare(place_id), consult_name_table=False) == "supermarket"
    specialty = next(iter(OSM_CONFIRMED_SPECIALTY))
    assert classify_grocery(_bare(specialty), consult_name_table=False) == "specialty"


def test_the_default_still_consults_the_name_table():
    """Callers that do not pass the flag -- every caller but the one script -- must be unchanged."""
    place_id = next(iter(NAME_CONFIRMED_SUPERMARKETS))
    assert classify_grocery(_bare(place_id)) == "supermarket"


# ---------------------------------------------------------------- the spaced spelling, review P2-7

@pytest.mark.parametrize("name", [
    "Wal Mart",
    "Wal Mart Supercenter",
    "Wal-Mart Supercenter",
    "Walmart Supercenter",
    "Wal Mart Neighborhood Market",
])
def test_the_spaced_spelling_matches_even_with_a_suffix(name):
    """**Review P2-7.** The old space-insensitive fallback compared the **whole** collapsed name
    with the brand, so `Wal Mart` matched and `Wal Mart Supercenter` matched nothing -- and nor did
    `Wal-Mart Supercenter`, which is the common historical spelling. A wrong negative is free
    under this project's asymmetry, so it was P2; it is also free to fix."""
    assert chain_in_name(name) == "Walmart"


def test_the_alias_is_a_lookup_and_not_a_space_insensitive_rule():
    """The fix must not become "ignore spaces", which would match anything spelled apart.
    `Food Li on` is not Food Lion, and no entry in the alias table says it is."""
    assert chain_in_name("Food Li on") is None
    assert chain_in_name("Har ris Teeter") is None


def test_the_alias_still_respects_word_boundaries():
    assert chain_in_name("Wall Martin Realty") is None
    assert chain_in_name("Walton Market Research") is None


def test_every_alias_points_at_a_brand_that_is_really_in_the_table():
    """An alias for a chain nobody has adopted would smuggle a brand in through the back door."""
    assert BRAND_NAME_ALIASES, "the table exists so that adding a spelling stays a decision"
    for alias, brand in BRAND_NAME_ALIASES.items():
        assert brand in SUPERMARKET_BRANDS, f"alias {alias!r} names {brand!r}, which is not a brand"
        assert alias == alias.lower(), f"{alias!r} must be given normalised"
# -------------------------------------------- the chain's own production site, review P1-1

#: `Weaver Street Market, Inc`, at `437 Dimmocks Mill Rd Ste 10`: the co-op's **Food House**.
WEAVER_FOOD_HOUSE = "1e99e399-b118-4d95-8c78-6770a47287c8"


def test_the_food_house_is_not_a_shop():
    """**Review P1-1.** The name recovery promoted this record to `supermarket`. The address is
    the co-op's Food House -- a commercial kitchen, an NC Dept of Agriculture meat-processing
    plant (P-317), a bread bakery, a pastry bakery and warehousing, which delivers to the four
    shops twice a day. It is a **supplier**, and our own record says `operating_status: open`.

    Nothing already in the module could catch it: the name carries no service-point word, it is
    the co-op's real legal name, and the 13,127 m2 Eno Mill footprint it borrowed proves neither
    retail access nor identity. So it is a judgement, recorded as one."""
    assert classify_grocery(_bare(WEAVER_FOOD_HOUSE)) == "not_a_grocery"


def test_the_food_house_stays_excluded_when_the_name_table_is_off():
    """The regeneration seam must not re-open a record that was ruled out on its identity."""
    assert classify_grocery(_bare(WEAVER_FOOD_HOUSE), consult_name_table=False) == "not_a_grocery"


def test_the_food_house_is_not_in_the_recovered_table():
    assert WEAVER_FOOD_HOUSE not in NAME_CONFIRMED_SUPERMARKETS


def test_a_site_cannot_be_ruled_out_and_recovered_at_once():
    """For these two tables that overlap would be the decision silently reversed, which is the
    same guard the FSQ closures carry."""
    overlap = set(NOT_A_WEEKLY_SHOP_SITES) & set(NAME_CONFIRMED_SUPERMARKETS)
    assert not overlap, f"ruled out and recovered at the same time: {overlap}"


def test_every_ruled_out_site_says_why_in_enough_detail_to_check():
    for place_id, why in NOT_A_WEEKLY_SHOP_SITES.items():
        assert len(place_id) == 36, f"{place_id!r} is not an Overture uuid"
        assert len(why) > 60, f"{place_id} gives no checkable reason"
