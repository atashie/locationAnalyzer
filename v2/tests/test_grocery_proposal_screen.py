"""The screen that proposes additions to the published `grocery` layer, under adversarial input.

**Why this module exists.** Before it, `rebuild_missing_grocery_stores.py` had no tests at all --
the one script in this project whose output argues for making a published number go UP. The sixth
adversarial pass had to drive it by hand with synthetic parquet files to find two defects, and both
were defects of REASONING rather than of arithmetic, which is exactly the kind a sheet of counts
cannot show:

* It read a **missing** `date_closed` as the record being OPEN. The snapshot is dated
  **2025-01-10** and today is twenty-two months later. "No closure was recorded in a file from
  January 2025" is not "the shop is trading in November 2026", and the difference is the whole
  ledger: *an empty field measures the record, not the world.*
* It let a **department** speak for the **store**, in both directions. An open
  `Walmart Vision & Glasses` beside a CLOSED `Walmart Supercenter` was read as the store trading
  on -- Codex built that case and the screen returned PROPOSED, explaining that an optician
  established continued trading. And a closed `Walmart Garden Center` was read as the store
  having closed, which is what made the override look necessary in the first place.

Every test here is about the direction a wrong answer hurts in. A wrong ADDITION sends a household
to a shop that is not there; a wrong REFUSAL leaves the published layer exactly as it is. So the
assertions below are mostly that the screen declines to conclude things.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from locfinder.places.grocery import (  # noqa: E402
    STORE_PART_WORDS,
    _normalise,
    chain_in_name,
    names_a_service_point,
    names_part_of_a_store,
)
from scripts.rebuild_missing_grocery_stores import (  # noqa: E402
    FSQ_PATH,
    FSQ_SNAPSHOT_DATE,
    read_fsq_records,
)

#: A nearby Foursquare row as `read_fsq_records` consumes it: name, `date_closed`, address, metres.
#: `None` is how the parquet's missing closure arrives once `pd.isna` has been applied.
STORE = ("Walmart Supercenter", None, "1001 Example Rd", 12.0)
CLOSED_STORE = ("Walmart Supercenter", "2016-04-15", "1001 Example Rd", 12.0)


# --------------------------------------------------------------------------------------------
# A missing closure date is not a report that the shop is open
# --------------------------------------------------------------------------------------------

def test_a_record_with_no_closure_date_does_not_overrule_a_recorded_closure():
    """Codex's case, verbatim: the optician must not establish that the Supercenter trades on."""
    reading = read_fsq_records("Walmart", [
        CLOSED_STORE,
        ("Walmart Vision & Glasses", None, "1001 Example Rd", 12.0),
    ])
    assert reading.refuses, "a closed store record must refuse whatever else sits at the site"
    assert "2016-04-15" in reading.closure


def test_two_store_records_disagreeing_still_refuses():
    """Not even a second STORE-level record with no closure date may overrule the closure.

    This is the asymmetry rather than a claim about which record is fresher. One of the two is
    wrong and the snapshot does not say which; refusing leaves the layer as it is, admitting
    sends a household to a shop that may have closed ten years ago.
    """
    reading = read_fsq_records("Walmart", [CLOSED_STORE, STORE])
    assert reading.refuses


def test_the_support_sentence_never_claims_the_record_is_open():
    """The wording is the finding. `FSQ 'X' open at 12.0 m` asserts something nobody measured."""
    reading = read_fsq_records("Walmart", [STORE])
    assert reading.support, "an agreeing store record with no recorded closure is still support"
    assert not reading.refuses
    assert " open" not in reading.support.lower(), reading.support
    assert FSQ_SNAPSHOT_DATE in reading.support, (
        "the support must date itself to the snapshot it was read from: " + reading.support
    )


def test_the_snapshot_date_matches_the_file_it_is_read_from():
    """A hard-coded date that drifts from the filename would re-launder the same false claim."""
    assert FSQ_SNAPSHOT_DATE in FSQ_PATH.name


# --------------------------------------------------------------------------------------------
# A part of a store does not speak for the store, in either direction
# --------------------------------------------------------------------------------------------

def test_a_closed_department_is_not_a_closed_store():
    """`Walmart Garden Center` closing in 2019 says nothing about the Walmart."""
    reading = read_fsq_records("Walmart", [
        ("Walmart Garden Center", "2019-02-13", "1001 Example Rd", 12.0),
    ])
    assert not reading.refuses, reading.closure
    assert not reading.closure
    assert reading.parts_skipped == 1


def test_a_bakery_cannot_corroborate_the_store_it_sits_inside():
    """The counter is not the shop. Nine of fourteen proposals once rested on records like it."""
    reading = read_fsq_records("Walmart", [
        ("Walmart Bakery", None, "1001 Example Rd", 12.0),
    ])
    assert not reading.support, reading.support
    assert reading.parts_skipped == 1


@pytest.mark.parametrize("part", [
    "Walmart Bakery",
    "Walmart Garden Center",
    "Walmart Auto Care Centers",
    "Harris Teeter Parking Lot",
    "Lowes Foods Gas Station",
    "The Bar At Harris Teeter",
    "Wal-Mart DC",
])
def test_these_names_are_parts_of_a_store_and_not_the_store(part):
    assert names_part_of_a_store(part), part


@pytest.mark.parametrize("store", [
    "Walmart Supercenter",
    "Walmart Neighborhood Market",
    "Walmart Discount Stores",
    "Food Lion Grocery Store",
    "Food Lion - TW Alexander",
    "Lowes Foods of Chapel Hill",
    "Lowes Foods #274 Pittsboro",
    "Harris Teeter Aberdeen",
    "Publix Super Market",
    "Publix Pointe",
    "Carlie C's IGA",
    "Family Fare Convenience Stores - Garner",
])
def test_these_names_are_the_store_itself(store):
    """Every one of these is a real name in the snapshot. A part word must not reach any of them."""
    assert not names_part_of_a_store(store), store


@pytest.mark.parametrize("standalone", [
    "Sunrise Bakery",
    "Guglhupf Bakery",
    "The Parking Lot Sale",
    "Auto Care Express",
    "Gas Station Deli",
])
def test_a_part_word_without_a_brand_is_not_part_of_a_store(standalone):
    """A STANDALONE bakery is a real shop. The part words only bite beside a brand we hold.

    This is the difference between this predicate and `names_a_service_point`, which is
    brand-independent because a `Grocery Pickup` is a bay whoever runs it.
    """
    assert chain_in_name(standalone) is None, "the fixture must carry no brand for this to bite"
    assert not names_part_of_a_store(standalone), standalone


def test_a_service_point_is_counted_separately_from_a_part():
    """Two tables, two counts, so the diagnostics say which rule did the work."""
    reading = read_fsq_records("Walmart", [
        ("Walmart Grocery Pickup and Delivery", None, "1001 Example Rd", 12.0),
        ("Walmart Bakery", None, "1001 Example Rd", 12.0),
    ])
    assert reading.bays_skipped == 1
    assert reading.parts_skipped == 1
    assert not reading.support


# --------------------------------------------------------------------------------------------
# The part words are read off the data, not invented
# --------------------------------------------------------------------------------------------

@pytest.mark.skipif(not FSQ_PATH.exists(), reason="the Foursquare snapshot is not on this machine")
def test_every_part_word_is_witnessed_beside_a_brand_in_the_snapshot():
    """A word in the table that no real record uses is decoration, and decoration goes stale.

    The companion risk is the opposite one, so this test also prints nothing and asserts
    nothing about words the snapshot has and the table lacks -- that gap is what
    `test_these_names_are_the_store_itself` is for.
    """
    import pandas as pd

    names = pd.read_parquet(FSQ_PATH, columns=["name"])["name"].astype(str)
    witnessed: set[str] = set()
    for name in names:
        if chain_in_name(name) is None:
            continue
        witnessed.update(_normalise(name).split())
    missing = sorted(w for w in STORE_PART_WORDS if w not in witnessed)
    assert not missing, f"part words no branded record in the snapshot uses: {missing}"


def test_the_two_predicates_do_not_overlap_for_the_names_that_drove_them():
    """`names_a_service_point` already caught these, so the part table must not duplicate them."""
    for already in ("Walmart Photo Center", "Walmart Vision & Glasses", "Walmart Pharmacy",
                    "Harris Teeter Fuel Center", "Walmart Grocery Pickup and Delivery"):
        assert names_a_service_point(already), already


# --------------------------------------------------------------------------------------------
# Names that do not agree are not evidence either way
# --------------------------------------------------------------------------------------------

def test_a_disagreeing_name_is_ignored_entirely():
    """Durham's 1010 Martin Luther King Pkwy: Triangle Rock Club and Planet Fitness trade there.

    Their being open is not evidence that the Walmart trades, and their closing would not be
    evidence that it had shut.
    """
    reading = read_fsq_records("Walmart", [
        ("Planet Fitness", None, "1010 Martin Luther King Pkwy", 30.0),
        ("Triangle Rock Club", "2020-01-01", "1010 Martin Luther King Pkwy", 30.0),
    ])
    assert not reading.support
    assert not reading.closure
    assert reading.bays_skipped == 0
    assert reading.parts_skipped == 0


def test_a_plain_brand_record_carrying_a_closure_refuses():
    """The Durham Walmart that closed in 2016 is the reason this screen exists."""
    reading = read_fsq_records("Walmart", [
        ("Walmart", "2016-09-21", "1010 Martin Luther King Pkwy", 8.0),
    ])
    assert reading.refuses
    assert "2016-09-21" in reading.closure


def test_no_nearby_records_at_all_is_neither_support_nor_closure():
    reading = read_fsq_records("Walmart", [])
    assert not reading.support
    assert not reading.closure
    assert not reading.refuses
