"""The admissibility predicate: what a walked record must document before E3 may score it.

Every refusal test here has a **positive control**: the same record, repaired, is admissible and
scores. A test that only shows nothing happens cannot distinguish a working predicate from one that
refuses everything — and this project has already shipped two controls that confirmed on the wrong
cause (`feedback-verify-the-shape-of-the-risk` instance 30).
"""
from __future__ import annotations

import csv
import dataclasses
from pathlib import Path

import pytest

from locfinder.grid import GridSpec
from locfinder.measure.admissible import (
    Admissibility,
    Inadmissible,
    PermittedPlace,
    WalkedRecord,
    admissibility,
    metres_between,
    reported_seconds,
    sort_records,
)
from locfinder.measure.e3 import E3Outcome, score_e3, score_walked_records

REPO = Path(__file__).resolve().parents[2]
SHEET = REPO / "docs" / "experiments" / "audit" / "triangle-grocery-walk-chapelhill-with-destinations.csv"

#: The destination `band15min_pass-03` was routed to, from the sheet.
SHOP = (-79.065417, 35.910405)


@pytest.fixture
def grid() -> GridSpec:
    """A real `GridSpec`, not a stub. A stub would agree with a wrong cell computation."""
    return GridSpec("EPSG:32617", 450000.0, 4000000.0, 100.0, 50, 40)


@pytest.fixture
def door(grid: GridSpec) -> tuple[float, float]:
    """A lon/lat inside cell (10, 20) of the fixture grid, derived from the grid itself."""
    lons, lats = grid.cell_centers_lonlat()
    return float(lons[10, 20]), float(lats[10, 20])


@pytest.fixture
def good(door: tuple[float, float]) -> WalkedRecord:
    """A walk that documents everything E3 compares. 1,500 s against 840 s: it FAILS limb (i).

    The fixture is deliberately a **failing** journey, so every refusal test below is also a test
    that the refusal is what suppressed the failure rather than the numbers being clean.
    """
    return WalkedRecord(
        label="band15min_pass-03",
        row=10,
        col=20,
        reported_s=840.0,
        walked_seconds=1500.0,
        duration_timed=True,
        start_lon=door[0],
        start_lat=door[1],
        destination_used="Hill's Family Asian Markets",
        destination_used_lon=SHOP[0],
        destination_used_lat=SHOP[1],
        predicted_destination="Hill's Family Asian Markets",
        predicted_destination_lon=SHOP[0],
        predicted_destination_lat=SHOP[1],
        route_followed="up the private track, OSM way 1254722641",
        route_identified=True,
        walked_date="2026-11-20",
    )


# ------------------------------------------------------------------- the control: it can pass, and fail


def test_a_fully_documented_walk_is_admissible_and_scores(good, grid):
    verdict, reasons = admissibility(good, grid=grid)
    assert verdict is Admissibility.ADMISSIBLE
    assert reasons == ()

    result = score_walked_records([good], grid=grid)
    assert result.outcome is E3Outcome.FAILED, "the control must be able to fail, or it proves nothing"
    assert result.walked == 1
    assert result.inadmissible == ()
    assert result.offending == ("band15min_pass-03",)
    assert not result.no_admissible_observation


def test_an_admissible_and_accurate_walk_is_unverified_not_failed(good, grid):
    """The other direction of the control: admissibility is not agreement."""
    accurate = dataclasses.replace(good, walked_seconds=860.0)
    result = score_walked_records([accurate], grid=grid)
    assert result.outcome is E3Outcome.UNVERIFIED
    assert result.walked == 1
    assert not result.no_admissible_observation


# ------------------------------------------------------------------- the four requirements, one at a time


def test_a_walk_with_no_start_door_is_not_admissible(good, grid):
    for blank in (None, "", "   "):
        record = dataclasses.replace(good, start_lon=blank, start_lat=blank)
        verdict, reasons = admissibility(record, grid=grid)
        assert verdict is Admissibility.NOT_ADMISSIBLE
        assert any("no start door recorded" in r for r in reasons), reasons


def test_a_start_door_in_the_wrong_cell_is_not_admissible(good, grid):
    """The check a non-blank test would miss: the door is recorded, and it is somewhere else.

    A walk that began two cells away is a walk from a place this published answer is not about.
    """
    lons, lats = grid.cell_centers_lonlat()
    record = dataclasses.replace(good, start_lon=float(lons[12, 22]), start_lat=float(lats[12, 22]))
    verdict, reasons = admissibility(record, grid=grid)
    assert verdict is Admissibility.NOT_ADMISSIBLE
    assert any("is in cell (12, 22), not cell (10, 20)" in r for r in reasons), reasons


def test_a_start_door_outside_the_grid_is_refused_with_its_own_reason(good, grid):
    """A real coordinate, 100 km east of the grid: it projects fine and no cell covers it."""
    far = GridSpec("EPSG:32617", 550000.0, 4000000.0, 100.0, 10, 10)
    lons, lats = far.cell_centers_lonlat()
    record = dataclasses.replace(good, start_lon=float(lons[5, 5]), start_lat=float(lats[5, 5]))
    assert grid.cell_for_lonlat(record.start_lon, record.start_lat) is None
    verdict, reasons = admissibility(record, grid=grid)
    assert verdict is Admissibility.NOT_ADMISSIBLE
    assert any("outside the grid" in r for r in reasons), reasons


def test_a_start_door_that_is_not_a_coordinate_is_refused_and_does_not_crash(good, grid):
    """`cell_for_lonlat` raises on a non-finite or unprojectable point, by design.

    A sheet is typed by hand, so one bad cell must refuse that row rather than take down the
    ingestion of every other row.
    """
    for lon, lat in ((float("nan"), 35.9), (0.0, 0.0), ("north gate", "by the bins")):
        record = dataclasses.replace(good, start_lon=lon, start_lat=lat)
        verdict, reasons = admissibility(record, grid=grid)
        assert verdict is Admissibility.NOT_ADMISSIBLE, (lon, lat)
        assert any("not a usable coordinate" in r for r in reasons), reasons


def test_an_unrecorded_destination_is_not_admissible(good, grid):
    record = dataclasses.replace(good, destination_used="")
    verdict, reasons = admissibility(record, grid=grid)
    assert verdict is Admissibility.NOT_ADMISSIBLE
    assert any("destination reached is not recorded" in r for r in reasons), reasons


def test_a_walk_to_a_different_destination_is_a_different_journey(good, grid):
    """Named in the audit README: substituting a better shop does not clear the product."""
    record = dataclasses.replace(good, destination_used="Harris Teeter")
    verdict, reasons = admissibility(record, grid=grid)
    assert verdict is Admissibility.NOT_ADMISSIBLE
    reason = next(r for r in reasons if "different journey" in r)
    assert "Harris Teeter" in reason and "Hill's Family Asian Markets" in reason


def test_a_destination_name_is_compared_after_stripping(good, grid):
    record = dataclasses.replace(good, destination_used="  Hill's Family Asian Markets ")
    verdict, _ = admissibility(record, grid=grid)
    assert verdict is Admissibility.ADMISSIBLE


def test_an_unrecorded_route_is_not_admissible(good, grid):
    record = dataclasses.replace(good, route_followed="")
    verdict, reasons = admissibility(record, grid=grid)
    assert verdict is Admissibility.NOT_ADMISSIBLE
    assert any("route walked is not on the record" in r for r in reasons), reasons


def test_an_untimed_duration_and_an_unstated_one_give_different_reasons(good, grid):
    """`False` and `None` are different claims: "I estimated it" and "I did not say"."""
    silent = admissibility(dataclasses.replace(good, duration_timed=None), grid=grid)[1]
    estimated = admissibility(dataclasses.replace(good, duration_timed=False), grid=grid)[1]
    assert any("does not say whether the duration was timed" in r for r in silent), silent
    assert any("recorded as not timed" in r for r in estimated), estimated
    assert silent != estimated


def test_every_reason_is_collected_and_not_just_the_first(good, grid):
    bare = dataclasses.replace(good, start_lon=None, start_lat=None, destination_used=None,
                               destination_used_lon=None, destination_used_lat=None,
                               route_followed=None, route_identified=None, duration_timed=None)
    verdict, reasons = admissibility(bare, grid=grid)
    assert verdict is Admissibility.NOT_ADMISSIBLE
    assert len(reasons) == 6, reasons


# ------------------------------------------------------------------- the refusal must not become a lie


def test_an_inadmissible_walk_does_not_become_a_planned_journey(good, grid):
    """The cheap fix that is a lie: counting a refused walk as "planned but not walked".

    E3 would then report UNVERIFIED with `planned=1` and nothing in the result would record that
    somebody walked 25 minutes against a published 14.
    """
    record = dataclasses.replace(good, duration_timed=None)
    split = sort_records([record], grid=grid)
    assert split.journeys == ()
    assert [i.label for i in split.inadmissible] == ["band15min_pass-03"]

    result = score_walked_records([record], grid=grid)
    assert result.walked == 0
    assert result.planned == 0, "a walk that happened must not be counted as unwalked"
    assert result.outcome is E3Outcome.UNVERIFIED
    assert result.no_admissible_observation, "the third status must be visible on the result"
    assert result.inadmissible[0].reasons


def test_the_suppressed_failure_is_recoverable_from_the_result(good, grid):
    """Refusing a walk hides the arithmetic, so the result must still say a walk was refused."""
    refused = score_walked_records([dataclasses.replace(good, route_followed=None)], grid=grid)
    scored = score_walked_records([good], grid=grid)
    assert refused.outcome is E3Outcome.UNVERIFIED and scored.outcome is E3Outcome.FAILED
    assert refused.no_admissible_observation and not scored.no_admissible_observation
    assert refused.median_difference_s is None, "no median may be formed from a refused walk"


def test_an_unwalked_journey_is_not_inadmissible(good, grid):
    """Not walking is not a defect in the record."""
    planned = dataclasses.replace(good, **dict.fromkeys(WalkedRecord.ALL_OBSERVATION_FIELDS, None))
    verdict, reasons = admissibility(planned, grid=grid)
    assert verdict is Admissibility.NOT_WALKED
    assert reasons == ()

    result = score_walked_records([planned], grid=grid)
    assert (result.walked, result.planned) == (0, 1)
    assert result.inadmissible == ()
    assert not result.no_admissible_observation


def test_a_cell_with_no_published_time_is_not_an_e3_journey(good, grid):
    """An `OFF_NETWORK` row makes no claim, so there is nothing to be right or wrong about.

    Every evidence field is cleared, because this is about a row **nobody walked**. Leaving one
    filled would make it a walked row with no claim, which is the next test.
    """
    unpublished = dataclasses.replace(
        good, label="off_network-01", reported_s=None,
        **dict.fromkeys(WalkedRecord.ALL_OBSERVATION_FIELDS, None))
    result = score_walked_records([unpublished], grid=grid)
    assert result.without_a_published_time == ("off_network-01",)
    assert (result.walked, result.planned) == (0, 0)
    assert result.inadmissible == ()


def test_walking_a_cell_with_no_published_time_is_refused_loudly(good, grid):
    """And if somebody does walk one, the walk is not silently discarded."""
    walked = dataclasses.replace(good, label="off_network-01", reported_s=None)
    result = score_walked_records([walked], grid=grid)
    assert result.without_a_published_time == ()
    assert [i.label for i in result.inadmissible] == ["off_network-01"]
    assert any("published no time" in r for r in result.inadmissible[0].reasons)


def test_an_inadmissible_walk_cannot_erase_a_failure_established_elsewhere(good, grid):
    """The one-way rule of the module docstring, extended to the third state."""
    other = dataclasses.replace(good, label="band10min_pass-01")
    refused = dataclasses.replace(good, label="band15min_pass-03", duration_timed=False)
    result = score_walked_records([other, refused], grid=grid)
    assert result.outcome is E3Outcome.FAILED
    assert result.offending == ("band10min_pass-01",)
    assert [i.label for i in result.inadmissible] == ["band15min_pass-03"]
    assert not result.no_admissible_observation, "one admissible walk was scored"


# ------------------------------------------------------------------- Codex pass 51's witnesses


def test_a_documented_walk_with_no_duration_does_not_become_unwalked(good, grid):
    """**Pass 51 finding A1, verbatim.** A walk happened and had no usable duration.

    Before the fix, `walked` was `walked_seconds is not None` and nothing else, so this row
    returned `NOT_WALKED` immediately: `walked=0, planned=1, inadmissible=(),
    no_admissible_observation=False`. The walk disappeared from the record of what could not be
    scored, which is the one thing this module exists to prevent.
    """
    record = dataclasses.replace(good, walked_seconds=None, duration_timed=False,
                                 walked_date="2026-11-14")
    assert record.evidence_of_a_walk, "the row records a walk"
    verdict, reasons = admissibility(record, grid=grid)
    assert verdict is Admissibility.NOT_ADMISSIBLE
    joined = " | ".join(reasons)
    assert "a walk is recorded" in joined and "no duration is" in joined, reasons
    assert "walked_date" in joined, "the reason must name the evidence that a walk happened"

    result = score_walked_records([record], grid=grid)
    assert (result.walked, result.planned) == (0, 0)
    assert [i.label for i in result.inadmissible] == ["band15min_pass-03"]
    assert result.no_admissible_observation


@pytest.mark.parametrize("evidence", ["walked_date", "destination_qualifies", "destination_open",
                                      "route_usable", "witness_within_10min",
                                      "witness_within_15min", "destination_used",
                                      "route_followed"])
def test_any_single_observation_column_makes_a_row_a_walk(good, grid, evidence):
    """One filled observation column is a walk, whichever column it is.

    A1 was found through `walked_date`, but the class is wider: the sheet has nine columns that
    only get filled in by somebody who went there.
    """
    blank = dict.fromkeys(WalkedRecord.ALL_OBSERVATION_FIELDS, None)
    record = dataclasses.replace(good, **blank)
    assert not record.walked, "the fully blank row must not read as a walk"
    with_one = dataclasses.replace(record, **{evidence: "yes"})
    assert with_one.walked, f"{evidence} alone must mark the row as walked"
    assert admissibility(with_one, grid=grid)[0] is Admissibility.NOT_ADMISSIBLE


def test_a_different_branch_of_the_same_chain_is_refused(good, grid):
    """**Pass 51 finding A2.** The committed metro sheet holds two shops both called `Food Lion`.

    They are 11 km apart, and one journey's own `predicted_destination_alternatives` is *also*
    `Food Lion` — a second shop of that name on the same road node. So a name is not an identity
    even within one node, and a string comparison accepted a walk to the wrong branch.
    """
    a = (-78.660641, 35.886074)      # band10min_fail-02's destination
    b = (-78.611194, 35.794319)      # band15min_fail-02's destination
    gap = metres_between(a[0], a[1], b[0], b[1])
    assert gap > 10_000, f"the two Food Lions are {gap:.0f} m apart"

    record = dataclasses.replace(
        good, destination_used="Food Lion", predicted_destination="Food Lion",
        predicted_destination_lon=a[0], predicted_destination_lat=a[1],
        destination_used_lon=b[0], destination_used_lat=b[1])
    verdict, reasons = admissibility(record, grid=grid)
    assert verdict is Admissibility.NOT_ADMISSIBLE
    assert any("probably not the shop the record names" in r for r in reasons), reasons
    # The control: the same walk, ended at the shop the layer picked, is admissible.
    right = dataclasses.replace(record, destination_used_lon=a[0], destination_used_lat=a[1])
    assert admissibility(right, grid=grid)[0] is Admissibility.ADMISSIBLE


def test_a_permitted_alternative_on_the_same_node_is_accepted(good, grid):
    """The other half of A2: the README explicitly permits walking to any place on the node.

    Refusing a named alternative was the same defect pointing the other way, and the ingestion
    was discarding the column that lists them. The alternative's own coordinate travels with its
    name, so the arrival is matched against the member actually reached.
    """
    nearby = (SHOP[0] + 0.0005, SHOP[1])        # about 45 m away, on the same node
    record = dataclasses.replace(
        good, destination_used="Weaver Street Market",
        destination_used_lon=nearby[0], destination_used_lat=nearby[1],
        destination_alternatives=(
            PermittedPlace("Weaver Street Market", nearby[0], nearby[1]),
            PermittedPlace("Compare Foods", SHOP[0], SHOP[1])))
    assert admissibility(record, grid=grid)[0] is Admissibility.ADMISSIBLE
    # And a shop that is neither the selection nor an alternative is still a different journey.
    other = dataclasses.replace(record, destination_used="Costco")
    verdict, reasons = admissibility(other, grid=grid)
    assert verdict is Admissibility.NOT_ADMISSIBLE
    assert any("different journey" in r for r in reasons), reasons


# ------------------------------------------------------------------- Codex pass 52's witnesses


@pytest.mark.parametrize("field", ["duration_timed", "route_identified"])
def test_the_two_self_report_columns_are_evidence_of_a_walk(good, grid, field):
    """**Pass 52 finding F2.** They were missing from the evidence list.

    A row whose only entry was one of these lost its evidence exactly as before the A1 repair:
    `walked=0, planned=1`, no refusal. They are the two fields that most directly concern having
    gone — one says whether a clock was used, the other whether the walker can say which way.
    """
    blank = dict.fromkeys(WalkedRecord.ALL_OBSERVATION_FIELDS, None)
    record = dataclasses.replace(good, **{**blank, field: True})
    assert record.evidence_of_a_walk == (field,), record.evidence_of_a_walk
    assert admissibility(record, grid=grid)[0] is Admissibility.NOT_ADMISSIBLE
    result = score_walked_records([record], grid=grid)
    assert (result.walked, result.planned) == (0, 0)
    assert result.no_admissible_observation


def test_a_recorded_not_timed_is_evidence_and_an_absent_one_is_not(good, grid):
    """`False` is a thing somebody who went says; `None` is the sheet saying nothing."""
    blank = dict.fromkeys(WalkedRecord.ALL_OBSERVATION_FIELDS, None)
    assert dataclasses.replace(good, **{**blank, "duration_timed": False}).walked
    assert not dataclasses.replace(good, **blank).walked


@pytest.mark.parametrize("field", ["witness_within_10min", "witness_within_15min"])
def test_untested_is_not_evidence_that_somebody_walked(good, grid, field):
    """**The other half of F2.** `untested` is what the README tells the owner to write when they
    did not try, so it can be filled in while planning a sheet rather than walking it. Reading it
    as affirmative evidence turned a planned row into a refused walk — A1's error reversed.
    """
    blank = dict.fromkeys(WalkedRecord.ALL_OBSERVATION_FIELDS, None)
    planned = dataclasses.replace(good, **{**blank, field: "untested"})
    assert planned.evidence_of_a_walk == (), planned.evidence_of_a_walk
    assert admissibility(planned, grid=grid)[0] is Admissibility.NOT_WALKED
    # The control: an answer only a walker could give IS evidence, in the same column.
    for answer in ("yes", "no", " YES "):
        walked = dataclasses.replace(good, **{**blank, field: answer})
        assert walked.evidence_of_a_walk == (field,), (answer, walked.evidence_of_a_walk)


def test_an_arrival_is_matched_to_the_place_it_names_not_to_a_radius(good, grid):
    """**Pass 52 finding F3.** Proximity is not identity either.

    Two different shops of the same name 270 m apart, on different nodes: select the first, walk
    to the second, record it truthfully. The name is in the permitted set and 270 m was inside the
    600 m node envelope the first repair used, so the wrong journey was accepted. The arrival is
    now matched against the coordinate of the member whose name was recorded.
    """
    first = (-79.0, 35.9)
    second = (-78.997, 35.9)
    gap = metres_between(first[0], first[1], second[0], second[1])
    assert 250 < gap < 290, f"{gap:.0f} m"

    record = dataclasses.replace(
        good, destination_used="Food Lion", predicted_destination="Food Lion",
        predicted_destination_lon=first[0], predicted_destination_lat=first[1],
        destination_used_lon=second[0], destination_used_lat=second[1],
        destination_alternatives=())
    verdict, reasons = admissibility(record, grid=grid)
    assert verdict is Admissibility.NOT_ADMISSIBLE
    assert any("past the 200 m a door can plausibly be" in r for r in reasons), reasons
    # The control: arriving at the shop the record names is admissible.
    right = dataclasses.replace(record, destination_used_lon=first[0],
                                destination_used_lat=first[1])
    assert admissibility(right, grid=grid)[0] is Admissibility.ADMISSIBLE


def test_an_alternative_with_no_coordinate_cannot_establish_identity(good, grid):
    """A sheet made before the coordinate column existed names alternatives and locates none.

    The honest outcome is a refusal naming the place, not silent acceptance on the name alone.
    """
    record = dataclasses.replace(
        good, destination_used="Compare Foods",
        destination_alternatives=(PermittedPlace("Compare Foods"),))
    verdict, reasons = admissibility(record, grid=grid)
    assert verdict is Admissibility.NOT_ADMISSIBLE
    assert any("does not say where 'Compare Foods' is" in r for r in reasons), reasons


def test_a_same_name_alternative_does_not_overwrite_the_selected_destination(good, grid):
    """**Pass 53 finding F5, live on the committed sheets.**

    The permitted set was collapsed into a dict keyed by place name, so the LAST member for a name
    won. `triangle-grocery-walk-with-destinations.csv` selects `Food Lion` on two rows and lists
    an alternative **also called `Food Lion`** with no coordinate, so the coordinate-less
    alternative replaced the selected shop and a legitimate walk ending exactly at the selected
    shop was refused for having no coordinate to match.
    """
    record = dataclasses.replace(
        good, destination_used="Food Lion", predicted_destination="Food Lion",
        predicted_destination_lon=SHOP[0], predicted_destination_lat=SHOP[1],
        destination_used_lon=SHOP[0], destination_used_lat=SHOP[1],
        destination_alternatives=(PermittedPlace("Food Lion"),))
    verdict, reasons = admissibility(record, grid=grid)
    assert verdict is Admissibility.ADMISSIBLE, reasons


def test_the_committed_sheet_really_has_that_shape(grid):
    """The witness is the artifact, not my fixture: two rows select a name they also list."""
    import csv
    sheet = SHEET.parent / "triangle-grocery-walk-with-destinations.csv"
    shaped = []
    for row in csv.DictReader(sheet.open(newline="", encoding="utf-8-sig")):
        alts = [a.strip() for a in (row["predicted_destination_alternatives"] or "").split(";")
                if a.strip()]
        if row["predicted_destination"].strip() and row["predicted_destination"].strip() in alts:
            shaped.append(row["journey_id"])
    assert shaped == ["band10min_fail-02", "band15min_fail-02"], shaped


def test_arriving_at_any_place_of_the_recorded_name_is_admissible(good, grid):
    """Several members share the name: arriving at any of them is arriving at one the record names.

    Refusing because a namesake is further away would refuse a truthful walk; accepting on the
    *selected* member alone was pass 52 F3. The nearest member decides.
    """
    far = (SHOP[0] + 0.02, SHOP[1])          # about 1.8 km away, same name, same node
    gap = metres_between(SHOP[0], SHOP[1], far[0], far[1])
    assert gap > 1000, f"{gap:.0f} m"
    record = dataclasses.replace(
        good, destination_used="Food Lion", predicted_destination="Food Lion",
        predicted_destination_lon=far[0], predicted_destination_lat=far[1],
        destination_used_lon=SHOP[0], destination_used_lat=SHOP[1],
        destination_alternatives=(PermittedPlace("Food Lion", SHOP[0], SHOP[1]),))
    assert admissibility(record, grid=grid)[0] is Admissibility.ADMISSIBLE
    # And arriving at neither is still refused, with the count of namesakes stated.
    away = dataclasses.replace(record, destination_used_lon=SHOP[0] + 0.01)
    verdict, reasons = admissibility(away, grid=grid)
    assert verdict is Admissibility.NOT_ADMISSIBLE
    assert any("nearest of 2 places called 'Food Lion'" in r for r in reasons), reasons


def test_an_unusable_coordinate_on_one_namesake_does_not_hide_a_good_match(good, grid):
    """One member has a typo for a coordinate and another is where the walk ended.

    The usable one must still decide. Dropping every member because one is malformed would refuse
    a truthful walk for somebody else's typo.
    """
    record = dataclasses.replace(
        good, destination_used="Food Lion", predicted_destination="Food Lion",
        predicted_destination_lon=SHOP[0], predicted_destination_lat=395.9,
        destination_used_lon=SHOP[0], destination_used_lat=SHOP[1],
        destination_alternatives=(PermittedPlace("Food Lion", SHOP[0], SHOP[1]),))
    assert admissibility(record, grid=grid)[0] is Admissibility.ADMISSIBLE
    # But if EVERY member's coordinate is unusable, the row is refused and says why.
    only_bad = dataclasses.replace(record, destination_alternatives=())
    verdict, reasons = admissibility(only_bad, grid=grid)
    assert verdict is Admissibility.NOT_ADMISSIBLE
    assert any("not usable" in r for r in reasons), reasons


def test_an_impossible_latitude_is_refused_rather_than_producing_zero_distance(good, grid):
    """**Pass 52 finding F9.** A typo that manufactured agreement instead of refusing the row.

    `395.910405` is one keystroke from `35.910405`. The haversine wrapped it through 360° and
    returned about 1.6e-9 m, so the impossible coordinate read as "you arrived exactly at the
    shop" and the record was admissible.
    """
    record = dataclasses.replace(good, destination_used_lat=395.910405)
    verdict, reasons = admissibility(record, grid=grid)
    assert verdict is Admissibility.NOT_ADMISSIBLE
    assert any("outside the geographic ranges" in r for r in reasons), reasons
    with pytest.raises(ValueError, match="outside the geographic ranges"):
        metres_between(-79.0, 395.9, -79.0, 35.9)
    for bad in ((181.0, 35.9), (-79.0, 91.0), (float("inf"), 35.9), (float("nan"), 35.9)):
        with pytest.raises(ValueError):
            metres_between(bad[0], bad[1], -79.0, 35.9)


def test_an_arrival_coordinate_is_required_at_all(good, grid):
    record = dataclasses.replace(good, destination_used_lon=None, destination_used_lat=None)
    verdict, reasons = admissibility(record, grid=grid)
    assert verdict is Admissibility.NOT_ADMISSIBLE
    assert any("a name does not identify a shop" in r for r in reasons), reasons


def test_a_route_the_walker_cannot_identify_is_refused(good, grid):
    """**Pass 51 finding A3**, with its witness as the prose.

    "I cannot remember whether I used the private track or avoided it" is non-blank, admits the
    approach is unresolved, and satisfied the non-blank test. The decision report asks whether the
    private approach was used or avoided; a blank-or-not check cannot answer that.
    """
    unsure = dataclasses.replace(
        good, route_followed="I cannot remember whether I used the private track or avoided it.",
        route_identified=False)
    verdict, reasons = admissibility(unsure, grid=grid)
    assert verdict is Admissibility.NOT_ADMISSIBLE
    assert any("not identifiable" in r for r in reasons), reasons

    silent = dataclasses.replace(good, route_identified=None)
    verdict, reasons = admissibility(silent, grid=grid)
    assert verdict is Admissibility.NOT_ADMISSIBLE
    assert any("does not say whether the route walked could be identified" in r
               for r in reasons), reasons
    # The two are different claims and must not share a sentence.
    assert admissibility(unsure, grid=grid)[1] != reasons


def test_duplicate_labels_are_refused(good, grid):
    with pytest.raises(ValueError, match="duplicate label"):
        sort_records([good, dataclasses.replace(good)], grid=grid)


# ------------------------------------------------------------------- what the product said


def test_the_reported_time_is_the_published_minute_not_the_model_float():
    """`docs/s3-decision-report.md`: E3's `reported_s` is the encoded whole minute.

    For `band15min_pass-03` that is 840 s and not 810.8185424804688. The difference moves the
    binding boundary from 16.9 to 17.5 minutes, which is why it is pinned here.
    """
    assert reported_seconds(14) == 840.0
    assert reported_seconds(None) is None
    with pytest.raises(ValueError):
        reported_seconds(-1)


def test_the_two_states_e3_already_had_are_unchanged(grid):
    """`score_e3` is still design §3's rule: hand it a walked journey and it scores it.

    The admissibility predicate is a gate in front of the scorer, not a change to the scorer.
    """
    from locfinder.measure.e3 import Journey
    plain = score_e3([Journey("a", reported_s=840.0, observed_s=1500.0)])
    assert plain.outcome is E3Outcome.FAILED
    assert plain.inadmissible == () and plain.without_a_published_time == ()
    assert not plain.no_admissible_observation


# ------------------------------------------------------------------- against the real sheet


def test_the_one_walked_journey_in_the_sheet_is_not_admissible():
    """Pass 47's verdict, now reached by the instrument instead of by reading prose.

    This is the test the whole item exists for: the record for `band15min_pass-03` carries
    `walked_seconds=1500` and nothing else E3 needs, and until now the only thing that said so was
    a sentence in `notes` that no predicate can read.
    """
    from locfinder.metros import get_metro
    rows = list(csv.DictReader(SHEET.open(encoding="utf-8-sig")))
    row = next(r for r in rows if r["journey_id"] == "band15min_pass-03")
    assert row["walked_seconds"] == "1500", "the sheet's walked row changed; re-read this test"

    record = WalkedRecord(
        label=row["journey_id"],
        row=int(row["row"]),
        col=int(row["col"]),
        reported_s=reported_seconds(int(row["encoded_minutes"])),
        walked_seconds=float(row["walked_seconds"]),
        duration_timed=None if row.get("duration_timed", "") == "" else row["duration_timed"] == "yes",
        start_lon=row["start_lon"] or None,
        start_lat=row["start_lat"] or None,
        destination_used=row["destination_used"] or None,
        predicted_destination=row["predicted_destination"] or None,
        route_followed=row.get("route_followed") or None,
    )
    assert record.reported_s == 840.0

    verdict, reasons = admissibility(record, grid=get_metro("triangle").grid())
    assert verdict is Admissibility.NOT_ADMISSIBLE
    joined = " | ".join(reasons)
    assert "no start door recorded" in joined
    assert "destination reached is not recorded" in joined
    assert "route walked is not on the record" in joined
    assert "timed" in joined
    # The two rules pass 51 added. The row has no arrival coordinate and does not say whether the
    # route could be identified -- its own `unresolved` column says the approach is open.
    assert "a name does not identify a shop" in joined
    assert "could be identified" in joined


def test_the_sheets_carry_the_columns_the_predicate_needs():
    """The generator and the committed sheets must not drift apart.

    `duration_timed` and `route_followed` were added for this predicate. A sheet without them
    cannot produce an admissible record, so a silent regeneration from an older generator would
    make every future walk unscorable.
    """
    sheets = sorted((REPO / "docs" / "experiments" / "audit").glob("triangle-grocery-walk*.csv"))
    checked = 0
    for path in sheets:
        if path.name.endswith("-rebuild-delta.csv"):
            continue
        header = next(csv.reader(path.open(encoding="utf-8-sig")))
        missing = [c for c in ("start_lon", "start_lat", "destination_used", "walked_seconds",
                               "duration_timed", "route_followed", "walked_date",
                               "destination_used_lon", "destination_used_lat",
                               "route_identified") if c not in header]
        assert not missing, f"{path.name} is missing {missing}"
        checked += 1
    assert checked >= 4, f"expected at least four walkable sheets, checked {checked}"


def test_an_inadmissible_is_pointed_at_a_row():
    """A refusal that cannot be pointed at a row is a complaint, not a finding."""
    i = Inadmissible(label="band15min_pass-03", reasons=("no start door recorded",))
    assert i.label and i.reasons


# ------------------------------------------------------------------- the ingestion path


def test_an_unrecognised_yes_no_is_neither_read_as_no_nor_as_silence():
    """Coercion is not validation (ledger 35), and **"silence" was itself a coercion**.

    The original version of this test asserted that an unrecognised answer reads as `None`. It was
    right that mapping it onto `False` would turn "I wrote something the parser did not expect"
    into "the duration was not timed" — a different claim, and a refusal for the wrong reason.
    **It was wrong to accept `None`**, which pass 53 F2 found: `duration_timed="not timed"` then
    erased itself, and a row somebody had filled in became a planned one with no refusal. Silence
    and an unreadable answer are as different as silence and "no".

    So an unrecognised answer now raises, the ingestion records the column as malformed, and the
    predicate refuses the row naming it.
    """
    from scripts.score_walked_audit import NotUnderstood, tri_state
    assert tri_state("yes") is True and tri_state(" YES ") is True
    assert tri_state("no") is False and tri_state("No") is False
    assert tri_state("") is None and tri_state(None) is None
    for unreadable in ("probably", "1", "not timed", "y/n"):
        with pytest.raises(NotUnderstood):
            tri_state(unreadable)


def test_the_ingestion_takes_the_published_minute_and_not_the_model_seconds():
    """`seconds` is the model's float; `encoded_minutes` is what the page showed."""
    from scripts.score_walked_audit import record_for
    record = record_for({
        "journey_id": "x", "row": "286", "col": "129",
        "seconds": "810.8", "encoded_minutes": "14",
        "walked_seconds": "1500", "duration_timed": "yes",
        "start_lon": "", "start_lat": "", "destination_used": "",
        "predicted_destination": "", "route_followed": "",
    })
    assert record.reported_s == 840.0


def test_the_ingestion_refuses_a_sheet_that_cannot_produce_an_admissible_record(tmp_path):
    """A sheet without the predicate's columns would score as "no admissible observation" for a
    reason that has nothing to do with the walks."""
    from scripts.score_walked_audit import Refused, read_sheet
    path = tmp_path / "stale.csv"
    path.write_text("journey_id,row,col,encoded_minutes,walked_seconds\na,1,2,14,1500\n",
                    encoding="utf-8")
    with pytest.raises(Refused, match="duration_timed"):
        read_sheet(path)


def test_the_ingestion_refuses_an_empty_sheet(tmp_path):
    from scripts.score_walked_audit import REQUIRED, Refused, read_sheet
    path = tmp_path / "empty.csv"
    path.write_text(",".join(REQUIRED) + "\n", encoding="utf-8")
    with pytest.raises(Refused, match="no rows"):
        read_sheet(path)


@pytest.mark.parametrize("sheet,walked,refused,no_claim,third_status", [
    ("triangle-grocery-walk-chapelhill-with-destinations.csv", 0, 1, 0, True),
    ("triangle-grocery-walk-with-destinations.csv", 0, 0, 3, False),
])
def test_the_committed_sheets_score_the_way_the_record_says(sheet, walked, refused, no_claim,
                                                            third_status):
    """End to end on the real sheets, including the distinction the third status exists for.

    Chapel Hill: one walk happened and cannot be scored, so UNVERIFIED **means** "no admissible
    observation". The metro draw: nothing was walked at all, so UNVERIFIED means only that — and
    the two must not read the same.
    """
    from locfinder.metros import get_metro
    from scripts.score_walked_audit import read_sheet
    records = read_sheet(SHEET.parent / sheet)
    result = score_walked_records(records, grid=get_metro("triangle").grid())
    assert result.outcome is E3Outcome.UNVERIFIED
    assert (result.walked, len(result.inadmissible),
            len(result.without_a_published_time)) == (walked, refused, no_claim)
    assert result.no_admissible_observation is third_status


def test_the_committed_json_is_not_stale():
    """The recorded artifact must say what a fresh run says."""
    import json

    from locfinder.metros import get_metro
    from scripts.score_walked_audit import read_sheet
    recorded = json.loads(
        (REPO / "docs" / "experiments" / "s3-e3-admissibility-chapelhill.json")
        .read_text(encoding="utf-8"))
    fresh = score_walked_records(read_sheet(SHEET), grid=get_metro("triangle").grid())
    assert recorded["outcome"] == fresh.outcome.value
    assert recorded["no_admissible_observation"] is fresh.no_admissible_observation
    assert [r["label"] for r in recorded["refused"]] == [i.label for i in fresh.inadmissible]
    assert [tuple(r["reasons"]) for r in recorded["refused"]] == [i.reasons
                                                                  for i in fresh.inadmissible]

# ------------------------------------------------------------------- Codex pass 53's witnesses


def test_the_sheet_is_asked_whether_a_walk_happened(good, grid):
    """**Pass 53 finding F2.** Three passes tried to infer this and each failed differently.

    The README's step 2 has the owner pick a door and record `start_lon`, `start_lat` and
    `door_offset_m` **before** step 3's walk. So a prepared-then-abandoned row carries exactly the
    columns the inference read as proof somebody had been there.
    """
    prepared = dataclasses.replace(good, **{
        **dict.fromkeys(WalkedRecord.ALL_OBSERVATION_FIELDS, None),
        "start_lon": good.start_lon, "start_lat": good.start_lat, "door_offset_m": 23.0})
    assert prepared.preparation_recorded == ("start_lon", "start_lat", "door_offset_m")
    assert prepared.evidence_of_a_walk == (), prepared.evidence_of_a_walk
    assert not prepared.walked, "a prepared row is not a walk"
    assert admissibility(prepared, grid=grid)[0] is Admissibility.NOT_WALKED
    result = score_walked_records([prepared], grid=grid)
    assert (result.walked, result.planned) == (0, 1)
    assert result.inadmissible == ()


def test_an_explicit_no_overrides_the_evidence(good, grid):
    """A row can carry a destination and a route and still not have been walked.

    Somebody can write down which shop they intend to visit and how they mean to get there. Only
    the answer decides.
    """
    record = dataclasses.replace(good, walk_happened=False)
    assert record.evidence_of_a_walk, "the control: the evidence is all there"
    assert not record.walked
    assert admissibility(record, grid=grid)[0] is Admissibility.NOT_WALKED


def test_an_explicit_yes_makes_a_bare_row_a_refused_walk(good, grid):
    """And the other direction: `yes` with nothing else is a walk that cannot be scored."""
    bare = dataclasses.replace(good, **{
        **dict.fromkeys(WalkedRecord.ALL_OBSERVATION_FIELDS, None), "walk_happened": True})
    assert bare.walked and bare.evidence_of_a_walk == ()
    verdict, reasons = admissibility(bare, grid=grid)
    assert verdict is Admissibility.NOT_ADMISSIBLE
    assert any("the sheet says this journey was walked" in r for r in reasons), reasons
    result = score_walked_records([bare], grid=grid)
    assert (result.walked, result.planned) == (0, 0)
    assert result.no_admissible_observation


def test_a_blank_answer_still_falls_back_to_the_evidence(good, grid):
    """The fallback has to keep working: a sheet filled in before this column existed has none."""
    record = dataclasses.replace(good, walk_happened=None, walked_seconds=None,
                                 duration_timed=False)
    assert record.walked, "walk-only columns are still evidence when the sheet does not say"
    assert admissibility(record, grid=grid)[0] is Admissibility.NOT_ADMISSIBLE


def test_an_answer_that_was_not_understood_is_refused_rather_than_erased(good, grid):
    """**The other half of F2.** `tri_state` mapped anything unrecognised to `None`.

    So `duration_timed="not timed"` erased itself and a row somebody had filled in became a
    planned one. Coercion is not validation (ledger 35), one level down from where it was found.
    """
    record = dataclasses.replace(good, duration_timed=None, malformed=("duration_timed",))
    verdict, reasons = admissibility(record, grid=grid)
    assert verdict is Admissibility.NOT_ADMISSIBLE
    assert any("recorded in duration_timed was not understood" in r for r in reasons), reasons


def test_the_ingestion_records_an_unreadable_answer_instead_of_dropping_it():
    from scripts.score_walked_audit import NotUnderstood, tri_state, tri_state_or_malformed
    assert tri_state("") is None and tri_state(None) is None
    assert tri_state("yes") is True and tri_state("no") is False
    with pytest.raises(NotUnderstood):
        tri_state("not timed")
    malformed = []
    assert tri_state_or_malformed({"duration_timed": "not timed"},
                                  "duration_timed", malformed) is None
    assert malformed == ["duration_timed"]


def test_every_owner_column_is_classified():
    """**The check that would have caught F2 before Codex did.**

    The sheet has eighteen owner columns and the old inference list read fifteen. Each column must
    appear in exactly one of the three lists, so adding one to the generator without deciding what
    it means fails here rather than being silently ignored.
    """
    from scripts.audit_recommendations import OWNER_COLUMNS
    classified = list(WalkedRecord.ALL_OBSERVATION_FIELDS)
    assert len(classified) == len(set(classified)), "a column is in two lists"
    # `walked` is the question itself, not an observation about the journey.
    expected = [c for c in OWNER_COLUMNS if c != "walked"]
    assert sorted(classified) == sorted(expected), (
        f"unclassified: {sorted(set(expected) - set(classified))}; "
        f"not in the sheet: {sorted(set(classified) - set(expected))}")


def test_free_text_decides_nothing_either_way(good, grid):
    """`notes` on a planned row may read "picked the north door"; on a walked one, "timer failed".

    Nothing can tell them apart, so neither decides. Treating every note as a walk would invent
    walks from planning notes; ignoring them entirely is what the column list does.
    """
    blank = dict.fromkeys(WalkedRecord.ALL_OBSERVATION_FIELDS, None)
    for column in WalkedRecord.AMBIGUOUS_FIELDS:
        record = dataclasses.replace(good, **{**blank, column: "something written here"})
        assert record.evidence_of_a_walk == (), column
        assert not record.walked, column
