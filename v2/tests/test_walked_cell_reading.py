"""What the page says at the walked cell, and the index collision that hid it.

`docs/experiments/s3-12-what-the-page-says-at-the-walked-cell.json` records a browser reading.
A reading cannot be recomputed, so the browser half is pinned as recorded; but everything the
record claims about the PUBLISHED bundle is re-derived here from the bytes, by a different path
from the writer's, so the record cannot drift away from the artifact it describes.

**The defect this exists to keep closed.** The audit sheet's columns are named `row` and `col`
and name no grid. They index the UTM `GridSpec`. The published raster is a WGS84 lon/lat grid
with its own indexing, and it also has a cell (286, 129) -- about 400 m from the UTM one. The
s3-10 probe called `the_walked_cell` read the sheet's numbers as published indices for five days,
while its own text called its card "the one a person can check against a walk". The two cells
disagree about the minute, the outcome at the band, the restricted-route flag and the shop. A
test that only checked the probe was self-consistent would have found nothing, so this checks the
two cells against each other and requires them to still disagree -- if they ever agree, this
record's whole account of the defect is wrong and should fail loudly rather than quietly pass.
"""
from __future__ import annotations

import csv
import json
import pathlib

import numpy as np
import pytest

V2 = pathlib.Path(__file__).resolve().parents[1]
DOCS = V2.parent / "docs"
ARTIFACT = DOCS / "experiments" / "s3-12-what-the-page-says-at-the-walked-cell.json"
SHEET = DOCS / "experiments" / "audit" / "triangle-grocery-walk-chapelhill-with-destinations.csv"
PUBLISHED = V2 / "spikes" / "g3-render" / "fixtures" / "published"
STEM = "own_triangle_grocery_walk"


@pytest.fixture(scope="module")
def doc() -> dict:
    if not ARTIFACT.exists():
        pytest.skip(f"{ARTIFACT.name} has not been written")
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def planes() -> dict:
    if not (PUBLISHED / "manifest.json").exists():
        pytest.skip("run scripts/export_published_layers.py to build the bundle")
    man = json.loads((PUBLISHED / "manifest.json").read_text(encoding="utf-8"))
    entry = next(l for l in man["layers"] if l["id"] == STEM)
    nrows, ncols = man["nrows"], man["ncols"]

    def read(key, dtype):
        return np.frombuffer((PUBLISHED / entry[key]).read_bytes(),
                             dtype=dtype).reshape(nrows, ncols)

    return {"bounds": man["bounds_wgs84"], "nrows": nrows, "ncols": ncols,
            "value": read("value_file", np.uint8), "status": read("status_file", np.uint8),
            "flag": read("flag_file", np.uint8), "dest": read("dest_file", np.dtype("<u2")),
            "table": json.loads(
                (PUBLISHED / entry["dest_table"]).read_text(encoding="utf-8"))["destinations"]}


@pytest.fixture(scope="module")
def sheet_row() -> dict:
    if not SHEET.exists():
        pytest.skip(f"{SHEET.name} is not present")
    with SHEET.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["journey_id"] == "band15min_pass-03":
                return row
    pytest.skip("band15min_pass-03 is not in the sheet")
    raise AssertionError  # unreachable; for the type checker


def published_cell(planes: dict, lon: float, lat: float) -> tuple[int, int]:
    W, S, E, N = planes["bounds"]
    assert W <= lon < E and S < lat <= N, (lon, lat)
    return (int((N - lat) / (N - S) * planes["nrows"]),
            int((lon - W) / (E - W) * planes["ncols"]))


def test_the_query_coordinate_is_in_the_cell_the_record_names(doc, planes, sheet_row):
    """The sheet's own lon/lat columns, which is what the broken probe failed to read."""
    lon, lat = float(sheet_row["query_lon"]), float(sheet_row["query_lat"])
    assert (lon, lat) == (-79.062476, 35.902334), "the sheet's query coordinate moved"
    row, col = published_cell(planes, lon, lat)
    named = doc["the_defect_this_reading_found"]["the_cell_the_door_is_in"]["published_cell"]
    assert (row, col) == (named["row"], named["col"]) == (282, 126)


def test_no_door_has_been_recorded_for_this_journey(sheet_row):
    """**Codex pass 55, F4.** For one day this repository called `query_lon`/`query_lat` "the
    recorded door", in six places including the instruction telling the owner where to walk from.

    It is the journey's query point -- the centre of the UTM cell the time was computed for. The
    row's start fields are blank, and filling them is the entire purpose of the re-walk. If a
    door is ever recorded, this test fails and the wording everywhere can finally be made true.
    """
    assert sheet_row["start_lon"] == "" and sheet_row["start_lat"] == "", (
        "a start door has been recorded for band15min_pass-03. The claim that this journey has "
        "no recorded door is now stale: update s3-12, the probe's text in measure_drawn_pixel.py "
        "and the walk instruction in the progress note, the audit README and the decision report")
    assert sheet_row["duration_timed"] == "no"
    assert sheet_row["destination_used"] == "", (
        "a destination was recorded; the E3 record may now hold an admissible observation")


def test_the_two_cells_that_share_an_index_still_contradict_each_other(doc, planes):
    """The witness for the defect. If these ever agree, the record's account is wrong."""
    walked = published_cell(planes, -79.062476, 35.902334)
    lookalike = (int(286), int(126 + 3))  # (286, 129), the sheet's index read as a published one
    assert lookalike == (286, 129)
    assert walked != lookalike

    def at(cell):
        r, c = cell
        di = int(planes["dest"][r, c])
        rec = planes["table"][di] if di != 65535 else None
        return {"minutes": int(planes["value"][r, c]), "flag": int(planes["flag"][r, c]),
                "names": [p.get("name") for p in (rec or {}).get("places", []) if p.get("name")]}

    a, b = at(walked), at(lookalike)
    assert a["minutes"] != b["minutes"], (a, b)
    assert (a["minutes"] <= 15) and not (b["minutes"] <= 15), (
        "the point of the defect is that one passes the 15-minute band and the other does not")
    assert a["flag"] != b["flag"], "one route is flagged restricted and the other is not"
    assert a["names"] != b["names"], "the two cells name the same shop"

    rec = doc["the_defect_this_reading_found"]
    assert rec["the_cell_the_door_is_in"]["value_byte_minutes"] == a["minutes"]
    assert rec["the_cell_the_index_pointed_at"]["value_byte_minutes"] == b["minutes"]


def test_the_recorded_card_is_the_sheet_row_rendered(doc, sheet_row):
    """Four things a walker would check, in the words the page used."""
    card = doc["the_reading"]["at_the_15_min_band_this_journey_is_in"]
    assert f"{sheet_row['encoded_minutes']} min" in card
    assert sheet_row["outcome_15min"] in card
    assert sheet_row["predicted_destination"] in card
    assert "not clearly public" in card, "the restricted-route disclosure is not in the card"
    assert "your limit 15 min" in card, "the card was not read at the band this journey is in"
    # The page's own heading, which is how the reading is checkable without trusting the pointer.
    assert doc["the_reading"]["cell_label_the_page_printed"] == "(row 282, col 126)"
    assert (DOCS / "experiments" / doc["the_reading"]["screenshot"]).exists()


def test_the_cost_that_was_measured_is_kept_apart_from_the_one_that_was_not(doc):
    """**The failure this guards is a quotable wrong number.**

    The page reported a whole second per slider change. It was a frame clock: Chrome throttles
    animation frames in an occluded window, `visibilityState` says "visible" throughout, and
    paint completion is detected on a frame. A later reader quoting 1002 ms as the product's
    repaint cost would be quoting the automation. The record has to keep the two apart, and say
    which sample is which.
    """
    measured = doc["the_costs_this_session_could_measure"]
    assert "17 hovers" in measured["card_round_trip_one_cell"]
    assert "20 scripted changes" in measured["worker_compute_whole_raster"]

    not_measured = doc["the_cost_this_session_could_not_measure"]
    assert "1002" in not_measured["what_the_page_reported"]
    why = not_measured["why_that_number_is_the_instrument"]
    assert "requestAnimationFrame" in why and "occluded" in why.lower()
    assert "visible" in why, "the record must say the page called itself visible throughout"
    control = not_measured["the_control"]
    assert "17" in control and "1000" in control, control
    assert "screenshot" in control, "the control is the capture burst; without it this is a story"
    # **Renamed after pass 55 F5.** It was "the_one_untainted_sample", and it was taken
    # immediately after the capture that is said to change frame scheduling, so "untainted" was
    # the one word it could not carry.
    assert "the_one_untainted_sample" not in not_measured, (
        "the sample is called untainted again; it was taken right after the intervention")
    sample = not_measured["the_one_sample_taken_after_a_capture"]
    assert "n=1" in sample
    assert "not an unconfounded baseline" in sample
    # And both readings of the 1002 ms must stay on the record, not just the flattering one.
    assert "BOTH readings are live" in not_measured["the_control"], not_measured["the_control"]


def test_the_record_says_what_it_does_not_establish(doc):
    nots = " ".join(doc["what_this_does_not_establish"])
    assert "about 25" in nots, "the owner's own report is no longer beside the page's claim"
    assert "what the page SAYS" in nots
    assert "phone" in nots
    establishes = " ".join(doc["what_this_establishes"])
    assert "400 m" in establishes
