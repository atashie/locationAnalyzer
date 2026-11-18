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
