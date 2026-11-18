"""Records excluded by an owner decision about what counts as the thing, not by a tag.

The owner's rule, 2026-11-17, on the Overture park points inside the Shearon Harris nuclear
plant site: *"if it is designated as a public park then yes, if it is just open space but not
designated as a park then no."*

The data answers it cleanly. The plant's OSM polygon is 9,627.8 ha and contains **nine** accepted
park records. **Seven** of them also fall inside `Harris Lake County Park` (`leisure=park`,
`access=yes`, `ownership=county`, 256.3 ha) and are designated public park. **Two** -- the lake
and the reservoir themselves -- fall only inside the plant, which carries no park designation at
all.

**Why this is a list and not a rule.** A containment rule looked obvious and was measured before
being written: screening every park record whose containing OSM polygons carry no park designation
would drop **25** records, and almost all of them are real parks that happen to sit inside a school
ground or a state recreation area whose polygon lacks the tag -- Lynn Road Park, Barwell Road Park,
Sandling Beach State Recreation Area, Falls Dam Playground. It would delete roughly twenty-three
genuine parks to remove two. The OSM designation tags are not reliable enough to carry a general
rule, so the decision is recorded per record, with its evidence, where it can be reviewed.
"""
import geopandas as gpd
import pytest
from shapely.geometry import Point

from locfinder.places.categories import select_overture
from locfinder.places.exclusions import (
    DROPPED_PLACE_IDS,
    EXCLUDED_PLACE_IDS,
    drop_excluded,
)

HARRIS_LAKE = "5a1c8da5-ce62-41fc-af4a-fa2c0c4bd703"
HARRIS_RESERVOIR = "dc218eca-83a0-4889-acde-0ec39b54224d"
HARRIS_COUNTY_PARK = "ba9952f9-4b3b-4812-bd57-faa21fa2928b"


def park_frame(ids):
    """A minimal Overture-shaped frame: `id`, `taxonomy`, geometry."""
    tax = {"primary": "park", "hierarchy": ["sports_and_recreation", "park"]}
    return gpd.GeoDataFrame(
        {"id": list(ids), "taxonomy": [tax] * len(ids)},
        geometry=[Point(i, 0) for i in range(len(ids))],
        crs="EPSG:32617",
    )


def test_every_exclusion_records_why_it_is_there():
    """An id with no reason beside it is unreviewable, which is the whole point of a list."""
    assert EXCLUDED_PLACE_IDS, "the table is empty"
    for place_id, reason in EXCLUDED_PLACE_IDS.items():
        assert len(place_id) == 36, f"{place_id!r} is not an Overture uuid"
        assert len(reason) > 40, f"{place_id} has no usable reason: {reason!r}"


def test_the_two_harris_water_bodies_are_excluded():
    assert HARRIS_LAKE in EXCLUDED_PLACE_IDS
    assert HARRIS_RESERVOIR in EXCLUDED_PLACE_IDS


def test_the_county_park_on_the_same_site_is_not_excluded():
    """Seven of the nine records on the plant site are inside a designated county park, and the
    owner's rule keeps them. Excluding by site rather than by designation would lose all nine."""
    assert HARRIS_COUNTY_PARK not in EXCLUDED_PLACE_IDS


def test_drop_excluded_removes_exactly_the_listed_records():
    g = park_frame([HARRIS_LAKE, HARRIS_COUNTY_PARK, HARRIS_RESERVOIR, "kept-id"])
    out = drop_excluded(g)
    assert list(out["id"]) == [HARRIS_COUNTY_PARK, "kept-id"]


def test_drop_excluded_is_a_no_op_on_a_frame_with_no_listed_records():
    g = park_frame(["a", "b"])
    assert len(drop_excluded(g)) == 2


def test_drop_excluded_survives_a_frame_without_an_id_column():
    """`select_named` returns frames built by hand, which carry no Overture id."""
    g = gpd.GeoDataFrame({"name": ["x"]}, geometry=[Point(0, 0)], crs="EPSG:32617")
    assert len(drop_excluded(g)) == 1


def test_select_overture_applies_the_exclusions():
    """The chokepoint, so no builder or script can route around it by accident."""
    g = park_frame([HARRIS_LAKE, HARRIS_COUNTY_PARK])
    out = select_overture(g, "park")
    assert list(out["id"]) == [HARRIS_COUNTY_PARK]


@pytest.mark.parametrize("place_id", [HARRIS_LAKE, HARRIS_RESERVOIR])
def test_the_excluded_ids_name_the_owner_decision_that_made_them(place_id):
    reason = EXCLUDED_PLACE_IDS[place_id]
    assert "2026-11-17" in reason, "the reason does not date the decision"
    assert "Harris" in reason
# --------------------------------------------------------------------------- FSQ closures, 2026-11-18
# Owner decision 2026-11-18: *"accept the 10 closures"* -- the 12 name-agreeing, within-60 m
# `date_closed` records from `measure_fsq_coverage.py`, MINUS the two held back for an OSM
# cross-check. See `docs/engineering-notes/project-phase1-s3-fsq-coverage.md`.
#
# SUPERSEDED THE SAME DAY. The cross-check ran, both held records went back to the owner with
# what it found, and the owner answered *"1-4) yes, proceed"*. ALL TWELVE ARE NOW APPLIED.
#
# These tests are about the SHAPE of the decision, not about FSQ being right:
#   * all twelve are applied, so a household is not routed to a shop that closed;
#   * the two that were held carry the cross-check that released them, and Sam's Club carries the
#     objection that was NEVER resolved -- it was accepted over a stated doubt, which is the
#     owner's call to make and the record's job to keep;
#   * each entry names its date and its source, so a reader can re-check it without the sheet;
#   * the table stays SEPARATE from `EXCLUDED_PLACE_IDS`, because it is a regenerable derivation
#     from a dated snapshot and a hand-curated judgement is not.
from locfinder.places.exclusions import (  # noqa: E402
    FSQ_CLOSURES_HELD,
    FSQ_CONFIRMED_CLOSURES,
    FSQ_FLAGGED_CLOSURES,
    flagged_closure_reason,
)

#: All twelve, with FSQ's `date_closed`. The last two were accepted on a second pass the same
#: day, after the cross-check.
ACCEPTED = {
    "790e99cf-ceef-415a-babb-849e75732fa4": "2013-06-25",   # Kroger
    "3e8b0d81-ca69-4cd5-9948-c8d858ff0a59": "2016-09-27",   # Southern Season
    "4fe3f836-f1f6-45e9-9553-a92a6c9f8752": "2024-06-26",   # El Atoron
    "2f30a8c1-497f-4ca7-9be4-0654fe808c57": "2024-07-07",   # Family Market
    "0aa4c24d-6a8f-4d54-a1b3-bd684db6bbfc": "2024-11-04",   # Usf Sales
    "d3de68dd-7695-47a3-bff5-ece45da1a8b1": "2019-08-02",   # Kroger Pharmacy
    "f389d1a5-5f4a-48a5-8055-e00206faba86": "2020-02-11",   # Rite Aid
    "837e9f0d-d5b0-4e16-b3c4-9119c9700e9a": "2021-02-08",   # Walgreens Pharmacy
    "6ee316ab-d82f-4890-9a1e-84874d0438c7": "2021-03-13",   # Walgreens
    "13e62ef8-c843-42c7-8be0-7bbaa070a70d": "2024-01-26",   # Rite Aid
    # Released by the cross-check and accepted on the owner's second pass, 2026-11-18.
    "1937d785-1a98-49c5-9d32-51b7ec7c97af": "2017-09-25",   # Harris Teeter
}

#: Sam's Club, 2018-02-03. Applied on the second pass and then **turned into a flag on the third**
#: -- owner, *"1-4) yes, proceed"*, taking the adversarial review's argument that the record was
#: being removed more decisively than the evidence warranted. It is believed closed and it stays
#: in the layer, with the doubt carried as data rather than as a source comment.
SAMS_CLUB = "c7c31e4e-79a8-43d3-aa0c-4c1bf098747e"

#: The two that were held for one day, and what released each.
#:
#: **Harris Teeter: the hold had no subject.** It was held because a Kroger in
#: `EXCLUDED_PLACE_IDS` was dropped precisely BECAUSE OSM shows a Harris Teeter trading on its
#: site, so a closed Harris Teeter had to be shown to be a different address first. It is
#: 15,249 m from that Kroger.
#:
#: **Sam's Club: the objection was never resolved.** FSQ's closed record is the WAREHOUSE CLUB
#: rather than a pharmacy counter, and a counter closing inside a club that keeps trading looks
#: identical in this data. All the cross-check added is that OSM holds no Sam's Club within 300 m,
#: which is CONSISTENT with the club having closed but is absence, not observation. It was
#: accepted over the doubt, so the entry has to keep saying so.
LATE = {
    "c7c31e4e-79a8-43d3-aa0c-4c1bf098747e": "Sam's Club",
    "1937d785-1a98-49c5-9d32-51b7ec7c97af": "Harris Teeter",
}


def test_the_applied_closures_are_exactly_the_twelve():
    """Set equality both ways. A missing entry fails to drop a shop that closed; an extra one
    removes a shop nobody decided about, from a PUBLISHED layer."""
    assert set(FSQ_CONFIRMED_CLOSURES) == set(ACCEPTED), (
        "missing: " + ", ".join(sorted(set(ACCEPTED) - set(FSQ_CONFIRMED_CLOSURES)))
        + " | unexpected: " + ", ".join(sorted(set(FSQ_CONFIRMED_CLOSURES) - set(ACCEPTED)))
    )


def test_exactly_eleven_are_applied_and_one_is_flagged():
    """Ten on the first pass, two on the second, one turned back into a flag on the third.
    Twelve applied would mean the flag decision was quietly reversed."""
    assert len(FSQ_CONFIRMED_CLOSURES) == 11
    assert len(FSQ_FLAGGED_CLOSURES) == 1


def test_the_flagged_record_is_not_removed_from_the_layer():
    """THE WHOLE POINT OF THE FLAG. A household still sees this place."""
    g = park_frame([SAMS_CLUB, "kept-id"])
    assert list(drop_excluded(g)["id"]) == [SAMS_CLUB, "kept-id"]


def test_the_flagged_record_is_not_in_the_applied_table():
    assert SAMS_CLUB not in FSQ_CONFIRMED_CLOSURES
    assert SAMS_CLUB in FSQ_FLAGGED_CLOSURES


def test_a_flagged_record_can_be_asked_for_its_reason():
    """A flag nothing can read is a comment. This is the seam a renderer would use."""
    reason = flagged_closure_reason(SAMS_CLUB)
    assert reason is not None
    assert "2018-02-03" in reason
    assert flagged_closure_reason("not-a-real-id") is None


def test_the_flag_says_what_is_believed_and_what_is_doubted():
    reason = FSQ_FLAGGED_CLOSURES[SAMS_CLUB]
    assert "arehouse" in reason, "the category doubt is not stated"
    assert "NOT RESOLVED" in reason
    assert "crosscheck_fsq_closures" in reason


def test_nothing_is_both_dropped_and_flagged():
    """The two tables answer opposite questions; an id in both would make the layer's behaviour
    depend on which one a reader happened to look at."""
    assert not (set(FSQ_FLAGGED_CLOSURES) & set(DROPPED_PLACE_IDS))


def test_nothing_is_held_any_more_and_the_table_still_exists():
    """The hold is resolved, so the table is empty -- but it still EXISTS, so a later session
    reads "this was decided" rather than having to reconstruct that it ever happened."""
    assert FSQ_CLOSURES_HELD == {}


def test_the_late_closure_names_the_cross_check_that_released_it():
    """Harris Teeter's evidence is not in the FSQ sheet, so the entry points at the script that
    produced it. Sam's Club is now flagged rather than applied and is checked separately."""
    for place_id, name in LATE.items():
        table = FSQ_CONFIRMED_CLOSURES if place_id in FSQ_CONFIRMED_CLOSURES \
            else FSQ_FLAGGED_CLOSURES
        assert "crosscheck_fsq_closures" in table[place_id], f"{name} misses the cross-check"


def test_each_applied_closure_is_actually_dropped():
    """The applied table exists to remove records. An entry that is not in `DROPPED_PLACE_IDS`
    would read as applied while changing nothing."""
    for place_id in FSQ_CONFIRMED_CLOSURES:
        assert place_id in DROPPED_PLACE_IDS, f"{place_id} is listed but never removed"


def test_each_closure_names_its_date_and_its_source():
    """A date and a source are what make the entry re-checkable without the sheet."""
    for place_id, reason in FSQ_CONFIRMED_CLOSURES.items():
        assert len(place_id) == 36, f"{place_id!r} is not an Overture uuid"
        assert "FSQ" in reason, f"{place_id} does not name the source"
        assert ACCEPTED[place_id] in reason, (
            f"{place_id} does not carry its date_closed {ACCEPTED[place_id]}"
        )
        assert "2026-11-18" in reason, f"{place_id} does not date the owner decision"
        assert len(reason) > 60, f"{place_id} has no usable reason: {reason!r}"


def test_the_closures_are_kept_apart_from_the_curated_exclusions():
    """A regenerable derivation from a dated snapshot is not a hand-made judgement, and a data
    refresh must not be able to overwrite one by touching the other."""
    assert not (set(FSQ_CONFIRMED_CLOSURES) & set(EXCLUDED_PLACE_IDS))


def test_drop_excluded_removes_an_accepted_closure():
    kept = "kept-id"
    closed = next(iter(ACCEPTED))
    g = park_frame([closed, kept])
    assert list(drop_excluded(g)["id"]) == [kept]


def test_drop_excluded_removes_harris_teeter_but_keeps_sams_club():
    """The two that were held together ended up on opposite sides, which is the clearest single
    assertion of where this landed."""
    harris = "1937d785-1a98-49c5-9d32-51b7ec7c97af"
    g = park_frame([harris, SAMS_CLUB, "kept-id"])
    assert list(drop_excluded(g)["id"]) == [SAMS_CLUB, "kept-id"]


def test_select_overture_applies_the_closures_too():
    """Same chokepoint as the curated exclusions, so no builder can route around it."""
    closed = next(iter(ACCEPTED))
    g = park_frame([closed, HARRIS_COUNTY_PARK])
    assert list(select_overture(g, "park")["id"]) == [HARRIS_COUNTY_PARK]
