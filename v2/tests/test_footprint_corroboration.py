"""A building corroborates the shop inside it, not the shop next door.

**The third adversarial review, 2026-11-18** ([[2026-11-18-name-recovery-review-findings]]) found
that **8 of the 13** records the name recovery accepted rest on a building that does **not contain
the record's point**:

* the 837 m² `Lowes Foods` is **Discount Tire**, 105 m away;
* `ALDI` borrows **New Hope Baptist Church**, 115 m away;
* both `Wal Mart` records borrow **Europa Center**, 67 m and 81 m away.

The rule that produced them took `max(area)` over every building intersecting a **120 m buffer**,
with no containment test and no identity test. That is the strip-mall failure which had already
killed the footprint-only rule the same morning, re-entering through the rule that replaced it.

## The asymmetry this encodes

**A footprint is an upper bound on the shop inside it.** So:

* a building the point is **inside** and which is big enough can corroborate a weekly shop;
* a building **near** the point corroborates nothing, because geometry cannot say whether it is
  this shop or its neighbour;
* **nothing** big anywhere near does refute a weekly shop -- no supermarket stands there.

Hence three verdicts, not a float, for the same reason `name_match` has three: *near a big
building* and *in a small building* are different facts and must not collapse into one number.
`unclassified` is outside the layer, so a wrong negative costs nothing; a wrong positive adds a
record to a layer a household is routed by.
"""
from __future__ import annotations

import pytest
from shapely.geometry import Point, box

from locfinder.places.footprint import (
    CORROBORATED,
    FLOOR_M2,
    NEAR_LOOK_M,
    NEIGHBOUR,
    REFUTED,
    corroboration,
    licenses_supermarket,
    why_not_corroborated,
)


def square(area_m2: float, cx: float = 0.0, cy: float = 0.0):
    """A square of exactly `area_m2`, centred on (cx, cy). Coordinates are metres."""
    half = (area_m2 ** 0.5) / 2.0
    return box(cx - half, cy - half, cx + half, cy + half)


# --------------------------------------------------------------- the point is inside a building

def test_inside_a_big_building_corroborates():
    got = corroboration(Point(0, 0), [square(5_000)])
    assert got.verdict == CORROBORATED
    assert got.host_m2 == pytest.approx(5_000, rel=1e-6)


def test_exactly_on_the_floor_corroborates():
    """The floor is inclusive. Stated so a later edit cannot move it silently."""
    assert corroboration(Point(0, 0), [square(FLOOR_M2)]).verdict == CORROBORATED


def test_just_under_the_floor_does_not_corroborate():
    assert corroboration(Point(0, 0), [square(FLOOR_M2 - 1)]).verdict != CORROBORATED


def test_a_point_on_the_boundary_still_counts_as_inside():
    """A place point digitised onto the wall of its own building is still in it."""
    b = square(5_000)
    on_the_wall = Point(b.exterior.coords[0])
    assert corroboration(on_the_wall, [b]).verdict == CORROBORATED


# ------------------------------------------------------------ the borrowed building: the 8 cases

def test_a_big_building_the_point_is_not_in_corroborates_nothing():
    """`Wal Mart` at 1748 Fordham Blvd, borrowing Europa Center 81 m away."""
    got = corroboration(Point(0, 0), [square(3_943, cx=150)])
    assert got.verdict == NEIGHBOUR
    assert got.host_m2 == 0.0
    assert got.near_m2 == pytest.approx(3_943, rel=1e-6)


def test_a_small_host_with_a_big_neighbour_is_not_refuted():
    """The point may be digitised on the wrong structure, so this is unknown, not a refusal."""
    got = corroboration(Point(0, 0), [square(300), square(5_000, cx=100)])
    assert got.verdict == NEIGHBOUR


def test_the_discount_tire_case():
    """837 m2 clears the floor, and is a tyre shop 105 m from the Lowes Foods record."""
    got = corroboration(Point(0, 0), [square(837, cx=105 + (837 ** 0.5) / 2)])
    assert got.verdict == NEIGHBOUR
    assert licenses_supermarket(got) is False


def test_the_church_case():
    """ALDI's own host building clears the floor, so the church next door is not what decides."""
    got = corroboration(Point(0, 0), [square(1_441), square(5_156, cx=200)])
    assert got.verdict == CORROBORATED
    assert got.host_m2 == pytest.approx(1_441, rel=1e-6)


# ------------------------------------------------------------------------------- the refutations

def test_no_building_at_all_refutes():
    got = corroboration(Point(0, 0), [])
    assert got.verdict == REFUTED
    assert got.host_m2 == 0.0 and got.near_m2 == 0.0


def test_only_small_buildings_refutes():
    """`Food Lion` at 536 m2, `Lidl` at 224 -- nothing big stands here, whatever it calls itself."""
    got = corroboration(Point(0, 0), [square(536), square(224, cx=60)])
    assert got.verdict == REFUTED


def test_a_point_in_nothing_with_only_small_neighbours_refutes():
    assert corroboration(Point(0, 0), [square(300, cx=80)]).verdict == REFUTED


# ------------------------------------------------------------------------- only one verdict licenses

@pytest.mark.parametrize("verdict,allowed", [
    (CORROBORATED, True),
    (NEIGHBOUR, False),
    (REFUTED, False),
])
def test_only_corroborated_licenses_a_supermarket(verdict, allowed):
    got = corroboration(Point(0, 0), [square(5_000)])._replace(verdict=verdict)
    assert licenses_supermarket(got) is allowed


def test_the_two_refusals_say_different_things():
    """A sheet that cannot tell these apart cannot be reviewed by a person."""
    near = corroboration(Point(0, 0), [square(5_000, cx=150)])
    none = corroboration(Point(0, 0), [square(300)])
    assert why_not_corroborated(near) != why_not_corroborated(none)
    assert "neighbour" in why_not_corroborated(near).lower()


def test_a_corroborated_verdict_has_no_refusal_text():
    got = corroboration(Point(0, 0), [square(5_000)])
    assert why_not_corroborated(got) == ""


# ------------------------------------------------------------------------------ the search radius

def test_the_look_radius_is_the_one_the_scripts_use():
    """Both scripts select the candidate buildings; the floor and the radius live here."""
    assert NEAR_LOOK_M == 120.0
    assert FLOOR_M2 == 650.0
def test_the_other_script_keeps_the_same_floor():
    """`shortlist_brandless_grocery.py` still defines its own `FLOOR_M2`, because it reports a
    different thing (a doubt, not a positive) and was not rewritten onto this module. Its comment
    claims the two are kept in step; this is the test that makes the claim true, so the two
    cannot drift and leave a sheet calibrated against a floor nothing else uses."""
    import pathlib
    import re

    src = (pathlib.Path(__file__).resolve().parents[1]
           / "scripts" / "shortlist_brandless_grocery.py").read_text(encoding="utf-8")
    found = re.search(r"^FLOOR_M2 = ([\d.]+)", src, re.MULTILINE)
    assert found, "FLOOR_M2 is no longer defined in shortlist_brandless_grocery.py"
    assert float(found.group(1)) == FLOOR_M2
def small_building():
    """A building well under the weekly-shop floor, for the cases that need data present but
    nothing big. 10 m square, so 100 m2 against a 650 m2 floor."""
    from shapely.geometry import Polygon

    return Polygon([(-5, -5), (5, -5), (5, 5), (-5, 5)])
# ----------------------------------------------------------------------------------------------
# A verdict for "we hold no building data here", 2026-11-23.


def test_an_unsurveyed_place_is_not_refuted():
    """`REFUTED` asserts no supermarket stands here. That is only sayable where the building data
    is PRESENT, and at two of the three sites this was found on, the nearest building of any size
    is 2.8 km and 10.6 km away. An empty `nearby` means one of two completely different things and
    the old rule returned the same verdict for both."""
    from shapely.geometry import Point

    from locfinder.places.footprint import REFUTED, UNSURVEYED, corroboration

    got = corroboration(Point(0, 0), [], surveyed=False)
    assert got.verdict == UNSURVEYED
    assert got.verdict != REFUTED
    assert (got.host_m2, got.near_m2) == (0.0, 0.0)


def test_an_unsurveyed_place_does_not_license_a_weekly_shop_either():
    """The asymmetry is unchanged: not knowing is not a yes. `UNSURVEYED` must fail the licence
    exactly as `REFUTED` does, so this change can only ever REMOVE a false refusal and never add a
    false admission."""
    from shapely.geometry import Point

    from locfinder.places.footprint import corroboration, licenses_supermarket

    assert not licenses_supermarket(corroboration(Point(0, 0), [], surveyed=False))
    assert not licenses_supermarket(corroboration(Point(0, 0), [], surveyed=True))
    assert not licenses_supermarket(corroboration(Point(0, 0), [], surveyed=None))


def test_a_surveyed_empty_site_is_still_refuted():
    """Where the data IS present and nothing big stands there, the verdict is unchanged. This is
    the case the floor was calibrated for."""
    from shapely.geometry import Point

    from locfinder.places.footprint import REFUTED, corroboration

    got = corroboration(Point(0, 0), [small_building()], surveyed=True)
    assert got.verdict == REFUTED


def test_not_saying_whether_a_place_is_surveyed_keeps_the_old_answer():
    """Every existing caller passes no such argument, and silently reclassifying their refusals
    would rewrite conclusions nobody re-measured. Absence of the claim is not the claim."""
    from shapely.geometry import Point

    from locfinder.places.footprint import REFUTED, corroboration

    assert corroboration(Point(0, 0), []).verdict == REFUTED
    assert corroboration(Point(0, 0), [], surveyed=None).verdict == REFUTED


def test_claiming_unsurveyed_while_offering_a_building_is_refused():
    """A building in hand proves the area HAS data. A caller saying both is confused, and guessing
    which half it meant is how a silent wrong verdict gets published."""
    import pytest
    from shapely.geometry import Point

    from locfinder.places.footprint import corroboration

    with pytest.raises(ValueError, match="surveyed"):
        corroboration(Point(0, 0), [small_building()], surveyed=False)


def test_the_unsurveyed_sentence_does_not_say_nothing_is_there():
    """The sentence is the whole point of the verdict. `why_not_corroborated` already keeps *we
    cannot tell* apart from *nothing is here*; this is a third thing, and it must not be readable
    as either."""
    from shapely.geometry import Point

    from locfinder.places.footprint import corroboration, why_not_corroborated

    sentence = why_not_corroborated(corroboration(Point(0, 0), [], surveyed=False))
    assert sentence
    lowered = sentence.lower()
    assert "no supermarket stands here" not in lowered
    assert "no building data" in lowered or "not covered" in lowered
    assert "supports no conclusion" in lowered or "says nothing" in lowered


def test_the_refuted_sentence_now_states_what_it_assumes():
    """It asserted "No supermarket stands here, whatever this record calls itself" with no
    qualifier, and that sentence was written into a sheet for three large chain stores that our
    building data does not cover. The claim is sound only where the data is present, so it says
    so."""
    from shapely.geometry import Point

    from locfinder.places.footprint import corroboration, why_not_corroborated

    sentence = why_not_corroborated(corroboration(Point(0, 0), [small_building()], surveyed=True))
    assert "No supermarket stands here" in sentence
    assert "building data" in sentence.lower()
