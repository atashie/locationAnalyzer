"""The owner's `verdict` column on the uncorroborated-grocery sheet, which it could not keep.

**Two defects of classes already written down in this repo, found by reading my own three-day-old
script against the sixth pass's findings rather than by a reviewer.**

1. **`--emit` could never emit.** It iterated the rows it had just computed, every one of which
   carries `verdict: ""` by construction, and never opened the sheet a person had filled in. The
   owner's workflow was: read 121 rows, type `exclude` against the ones that are not shops, run
   `--emit`, and be told *"nothing marked `exclude` in the sheet"*. This is the retired ask-5
   defect exactly -- a mechanism that exists and is unreachable -- and the rule this project wrote
   for it is that a predeclared path must be SHOWN to be reachable.

2. **A rerun silently destroyed the column.** No overwrite guard, so screening again threw away
   every verdict typed into it. `migrate_audit_sheet.py` exists because of this same failure, and
   `dcf3516` had just fixed it in the forward screen. One line of the same class, in a file
   written hours later.

The asymmetry here runs the opposite way from the rest of the project, and that is the point:
these rows are candidates for REMOVAL from the published layer, so the harm of losing a verdict is
not a wrong deletion -- it is that the only record of a human decision is gone and the work is
done again from scratch, which is how a layer ends up with nobody able to say why anything is in
it.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.screen_uncorroborated_grocery import (  # noqa: E402
    SHEET_COLUMNS,
    owner_verdicts,
    read_sheet,
)

ROW = {
    "place_id": "11111111-1111-4111-8111-111111111111",
    "name": "Roofing Inc.",
    "address": "1 Example Rd, Raleigh",
    "primary": "grocery_store",
    "outcome": "UNCORROBORATED",
    "evidence": "no OSM shop and no FSQ grocery within 150 m",
    "verdict": "",
}


def write_sheet(path: Path, rows: list[dict]) -> Path:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=SHEET_COLUMNS)
        w.writeheader()
        w.writerows(rows)
    return path


def test_a_verdict_typed_into_the_sheet_is_read_back(tmp_path):
    """The whole workflow. Before this, the sheet was write-only."""
    sheet = write_sheet(tmp_path / "s.csv", [ROW | {"verdict": "exclude"}])
    assert owner_verdicts(read_sheet(sheet)) == {ROW["place_id"]: "exclude"}


def test_an_empty_column_is_not_a_verdict(tmp_path):
    sheet = write_sheet(tmp_path / "s.csv", [ROW, ROW | {"place_id": "2", "verdict": "   "}])
    assert owner_verdicts(read_sheet(sheet)) == {}


def test_whitespace_and_case_do_not_hide_a_verdict(tmp_path):
    """A person types into a spreadsheet. ` Exclude ` is the same decision as `exclude`."""
    sheet = write_sheet(tmp_path / "s.csv", [ROW | {"verdict": " Exclude "}])
    assert owner_verdicts(read_sheet(sheet)) == {ROW["place_id"]: "exclude"}


def test_a_verdict_that_is_not_exclude_is_still_kept(tmp_path):
    """`keep` is a decision too, and losing it means asking the owner the same question twice."""
    sheet = write_sheet(tmp_path / "s.csv", [ROW | {"verdict": "keep -- tienda, real shop"}])
    assert owner_verdicts(read_sheet(sheet)) == {
        ROW["place_id"]: "keep -- tienda, real shop"}


def test_a_missing_sheet_reads_as_no_rows_rather_than_raising(tmp_path):
    """The first run has no sheet, and that is not an error."""
    assert read_sheet(tmp_path / "absent.csv") == []
    assert owner_verdicts([]) == {}


def test_a_sheet_without_the_verdict_column_is_refused_not_guessed(tmp_path):
    """`migrate_audit_sheet.py` is in this repo because a schema change ate an owner's work."""
    path = tmp_path / "old.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=[c for c in SHEET_COLUMNS if c != "verdict"])
        w.writeheader()
        w.writerow({c: ROW[c] for c in SHEET_COLUMNS if c != "verdict"})
    with pytest.raises(SystemExit):
        read_sheet(path)


def test_the_columns_the_writer_uses_are_the_columns_the_reader_expects():
    """One list, so the two halves cannot drift the way the forward screen's did."""
    assert SHEET_COLUMNS[0] == "place_id"
    assert SHEET_COLUMNS[-1] == "verdict"
    assert set(ROW) == set(SHEET_COLUMNS)
