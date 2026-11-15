"""The migration for an owner's already-filled sheet.

**Pass 52 finding F7.** `score_walked_audit.py` refuses a sheet missing a column the predicate
reads, and told the owner to regenerate — which writes every owner column blank, so the only way
past the overwrite guard destroys the observations. Two rounds of columns were added in one day,
and there was no path for a file somebody had filled in.

Every test here builds an **old-schema** sheet by deleting the new columns from the committed one,
so the migration is exercised against the schema it exists for rather than against a hand-written
approximation.
"""
from __future__ import annotations

import csv
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.audit_recommendations import OWNER_COLUMNS  # noqa: E402
from scripts.migrate_audit_sheet import (  # noqa: E402
    DESTINATION_COLUMNS,
    Refused,
    main,
    migrate,
)

REPO = Path(__file__).resolve().parents[2]
AUDIT = REPO / "docs" / "experiments" / "audit"
SHEET = AUDIT / "triangle-grocery-walk-chapelhill-with-destinations.csv"

#: The columns added after the first walked row was recorded. An owner's copy predates them.
ADDED_SINCE = ("duration_timed", "route_followed", "destination_used_lon", "destination_used_lat",
               "route_identified", "predicted_destination_alternatives_lonlat")


def old_schema(tmp_path: Path, *, fill: dict | None = None, drop_destinations=False) -> Path:
    """The committed sheet with the new columns removed, and optionally a walk filled in."""
    with SHEET.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        header = [c for c in reader.fieldnames if c not in ADDED_SINCE]
        rows = [{k: v for k, v in r.items() if k in header} for r in reader]
    if drop_destinations:
        # Every column the recovery writes, not only the `predicted_destination*` ones:
        # `recheck_matches_sheet` is in that group too, and leaving it behind made the sheet still
        # look like one the recovery had run on.
        header = [c for c in header if c not in DESTINATION_COLUMNS]
        rows = [{k: v for k, v in r.items() if k in header} for r in rows]
    if fill:
        rows[3].update({k: v for k, v in fill.items() if k in header})
    path = tmp_path / "owners-copy.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=header)
        w.writeheader()
        w.writerows(rows)
    return path


def read(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        return list(reader.fieldnames), list(reader)


def test_a_filled_sheet_gains_the_columns_and_loses_no_observation(tmp_path):
    fill = {"walked_seconds": "900", "walked_date": "2026-11-12", "start_lon": "-79.06",
            "start_lat": "35.90", "destination_used": "Harris Teeter",
            "notes": "an observation that must survive"}
    path = old_schema(tmp_path, fill=fill)
    before_header, before_rows = read(path)
    out = tmp_path / "migrated.csv"

    assert migrate(path, out, in_place=False) == 0
    header, rows = read(out)

    for column in ADDED_SINCE:
        assert column in header, column
    assert len(rows) == len(before_rows)
    # Every cell that existed still holds exactly what it held.
    for old, new in zip(before_rows, rows):
        for key, value in old.items():
            assert new[key] == value, (old["journey_id"], key, value, new[key])
    # Including the filled-in walk, which is the whole point.
    walked = next(r for r in rows if r["walked_seconds"] == "900")
    assert walked["notes"] == "an observation that must survive"
    assert walked["destination_used"] == "Harris Teeter"
    # And the new columns are blank: the owner supplies them, nothing is inferred.
    for column in ADDED_SINCE:
        assert all(r[column] == "" for r in rows), column
    assert before_header != header, "the control: the schema really did change"


def test_the_migrated_header_is_the_generators_order(tmp_path):
    """A migrated sheet and a freshly generated one must have the same column order.

    Appending would have been easier and would have made every later diff between an owner's
    sheet and a regenerated one unreadable.
    """
    path = old_schema(tmp_path)
    out = tmp_path / "migrated.csv"
    migrate(path, out, in_place=False)
    header, _ = read(out)
    committed, _ = read(SHEET)
    assert [c for c in header if c in OWNER_COLUMNS] == \
        [c for c in committed if c in OWNER_COLUMNS]
    assert header == committed, "the migrated schema differs from the committed sheet's"


def test_the_migration_is_idempotent(tmp_path):
    path = old_schema(tmp_path)
    out = tmp_path / "once.csv"
    migrate(path, out, in_place=False)
    header_once, rows_once = read(out)
    again = tmp_path / "twice.csv"
    assert migrate(out, again, in_place=False) == 0
    assert not again.exists(), "a second run must write nothing at all"
    header_twice, rows_twice = read(out)
    assert (header_once, rows_once) == (header_twice, rows_twice)


def test_in_place_keeps_the_original(tmp_path):
    path = old_schema(tmp_path, fill={"walked_seconds": "900"})
    _, before = read(path)
    migrate(path, tmp_path / "unused.csv", in_place=True)
    header, rows = read(path)
    assert "route_identified" in header
    backup = path.with_suffix(path.suffix + ".before-migration")
    assert backup.exists(), "the original must still be there"
    _, kept = read(backup)
    assert kept == before


def test_a_bare_draw_does_not_gain_destination_columns(tmp_path):
    """A sheet that has never been through the destination recovery should not gain empty ones.

    Blank destination columns would make a row look as though the recovery had run and found
    nothing, which is a different statement from "the recovery has not run".
    """
    path = old_schema(tmp_path, drop_destinations=True)
    out = tmp_path / "migrated.csv"
    migrate(path, out, in_place=False)
    header, _ = read(out)
    assert "route_identified" in header, "the owner columns are still added"
    assert not any(c.startswith("predicted_destination") for c in header), header


def test_a_file_that_is_not_an_audit_sheet_is_refused(tmp_path):
    path = tmp_path / "something-else.csv"
    path.write_text("name,value\na,1\n", encoding="utf-8")
    with pytest.raises(Refused, match="not a\n?.*walked-audit sheet|journey_id"):
        migrate(path, tmp_path / "out.csv", in_place=False)


def test_an_empty_sheet_is_refused(tmp_path):
    path = old_schema(tmp_path)
    header, _ = read(path)
    empty = tmp_path / "empty.csv"
    empty.write_text(",".join(header) + "\n", encoding="utf-8")
    with pytest.raises(Refused, match="no rows"):
        migrate(empty, tmp_path / "out.csv", in_place=False)


def test_a_missing_file_is_refused(tmp_path):
    with pytest.raises(Refused, match="does not exist"):
        main([str(tmp_path / "nope.csv")])


def test_the_committed_sheets_need_no_migration(tmp_path):
    """The control on the whole exercise: the sheets in the repo are already current.

    If this fails, a sheet was committed without a column the predicate reads, and the next walk
    recorded on it could not be scored.
    """
    for sheet in sorted(AUDIT.glob("triangle-grocery-walk*.csv")):
        if sheet.name.endswith("-rebuild-delta.csv"):
            continue
        copy = tmp_path / sheet.name
        shutil.copy2(sheet, copy)
        out = tmp_path / f"out-{sheet.name}"
        migrate(copy, out, in_place=False)
        assert not out.exists(), f"{sheet.name} is missing a column the predicate reads"
