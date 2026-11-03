import pytest

from locfinder.traveltime.access import (FORBIDDEN, OPEN, RESTRICTED, RESTRICTED_PENALTY_S,
                                         access_penalty_s, classify_access)


def test_plain_road_is_open_for_every_mode():
    for mode in ("drive", "bike", "walk"):
        assert classify_access({"highway": "residential"}, mode) == OPEN
        assert access_penalty_s({"highway": "residential"}, mode) == 0.0


def test_private_is_restricted_not_forbidden():
    """The whole point of the fix: a home on a private drive must be reachable."""
    d = {"highway": "service", "access": "private", "service": "driveway"}
    assert classify_access(d, "drive") == RESTRICTED
    assert access_penalty_s(d, "drive") == RESTRICTED_PENALTY_S["drive"]


def test_access_no_stays_forbidden():
    """Every way out of the RDU Terminal 2 stub was access=no; blocking those was correct."""
    assert classify_access({"highway": "service", "access": "no"}, "drive") == FORBIDDEN
    assert classify_access({"highway": "service", "access": "military"}, "walk") == FORBIDDEN


@pytest.mark.parametrize("value", ["customers", "delivery", "permit", "agricultural", "forestry"])
def test_other_conditional_values_are_restricted(value):
    assert classify_access({"highway": "service", "access": value}, "drive") == RESTRICTED


def test_mode_tag_overrides_the_generic_tag():
    """access=private + foot=yes is a private road pedestrians may use."""
    d = {"highway": "service", "access": "private", "foot": "yes"}
    assert classify_access(d, "walk") == OPEN
    assert classify_access(d, "drive") == RESTRICTED


def test_mode_tag_can_forbid_what_generic_access_allows():
    d = {"highway": "track", "access": "yes", "motor_vehicle": "no"}
    assert classify_access(d, "drive") == FORBIDDEN
    assert classify_access(d, "walk") == OPEN


def test_mode_tag_can_restrict_what_generic_access_omits():
    d = {"highway": "service", "bicycle": "private"}
    assert classify_access(d, "bike") == RESTRICTED
    assert classify_access(d, "drive") == OPEN


def test_list_valued_tags_take_the_strictest_reading():
    assert classify_access({"highway": "service", "access": ["yes", "no"]}, "drive") == FORBIDDEN
    assert classify_access({"highway": "service", "access": ["yes", "private"]}, "drive") == RESTRICTED


def test_destination_is_restricted_not_open():
    """Corrected after Codex pass 6 (H3). `access=destination` literally means "no through
    traffic", so it is the clearest case for a through-routing penalty. It was previously
    classified OPEN with zero penalty, which made an explicit no-through road behave like an
    ordinary shortcut. The earlier test asserted that mistake."""
    d = {"highway": "residential", "access": "destination"}
    assert classify_access(d, "drive") == RESTRICTED
    assert access_penalty_s(d, "drive") > 0


def test_walk_and_bike_penalties_are_lower_than_drive():
    assert RESTRICTED_PENALTY_S["walk"] < RESTRICTED_PENALTY_S["drive"]
    assert RESTRICTED_PENALTY_S["bike"] < RESTRICTED_PENALTY_S["drive"]
