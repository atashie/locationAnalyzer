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
from locfinder.places.exclusions import EXCLUDED_PLACE_IDS, drop_excluded

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
