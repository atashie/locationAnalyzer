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
    WalkedRecord,
    admissibility,
    reported_seconds,
    sort_records,
)
from locfinder.measure.e3 import E3Outcome, score_e3, score_walked_records

REPO = Path(__file__).resolve().parents[2]
SHEET = REPO / "docs" / "experiments" / "audit" / "triangle-grocery-walk-chapelhill-with-destinations.csv"


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
        predicted_destination="Hill's Family Asian Markets",
        route_followed="up the private track, OSM way 1254722641",
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
                               route_followed=None, duration_timed=None)
    verdict, reasons = admissibility(bare, grid=grid)
    assert verdict is Admissibility.NOT_ADMISSIBLE
    assert len(reasons) == 4, reasons


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
    planned = dataclasses.replace(good, walked_seconds=None, duration_timed=None,
                                  start_lon=None, start_lat=None, destination_used=None,
                                  route_followed=None)
    verdict, reasons = admissibility(planned, grid=grid)
    assert verdict is Admissibility.NOT_WALKED
    assert reasons == ()

    result = score_walked_records([planned], grid=grid)
    assert (result.walked, result.planned) == (0, 1)
    assert result.inadmissible == ()
    assert not result.no_admissible_observation


def test_a_cell_with_no_published_time_is_not_an_e3_journey(good, grid):
    """An `OFF_NETWORK` row makes no claim, so there is nothing to be right or wrong about."""
    unpublished = dataclasses.replace(good, label="off_network-01", reported_s=None,
                                      walked_seconds=None)
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
                               "duration_timed", "route_followed") if c not in header]
        assert not missing, f"{path.name} is missing {missing}"
        checked += 1
    assert checked >= 4, f"expected at least four walkable sheets, checked {checked}"


def test_an_inadmissible_is_pointed_at_a_row():
    """A refusal that cannot be pointed at a row is a complaint, not a finding."""
    i = Inadmissible(label="band15min_pass-03", reasons=("no start door recorded",))
    assert i.label and i.reasons


# ------------------------------------------------------------------- the ingestion path


def test_an_unrecognised_yes_no_is_read_as_silence_and_not_as_no():
    """Coercion is not validation (ledger 35).

    Mapping an unrecognised value onto `False` would turn "I wrote something the parser did not
    expect" into "the duration was not timed", which is a different claim and a refusal for the
    wrong reason.
    """
    from scripts.score_walked_audit import tri_state
    assert tri_state("yes") is True and tri_state(" YES ") is True
    assert tri_state("no") is False and tri_state("No") is False
    assert tri_state("") is None and tri_state(None) is None
    assert tri_state("probably") is None
    assert tri_state("1") is None, "a bare 1 is not one of the sheet's words"


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
