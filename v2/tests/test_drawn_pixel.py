"""The oracle the browser probe is compared against, and the one duplicated constant behind it.

`docs/experiments/s3-10-drawn-pixel.json` is predeclared: `probe_placement.js` reads it in a
browser and compares the live page against it. That makes two things worth pinning here.

**The palette is copied.** `measure_drawn_pixel.paint_rgba` restates `worker.js`'s three pixels and
its hatch, because Python cannot call the worker. If the worker's palette changed, every expected
RGBA in the artifact would be quietly wrong and the browser session would report a page defect that
is really a drift in the oracle. This reads the literals out of `worker.js` with the comment
stripper `test_wire.py` already uses for the encoding lists, and fails with both values printed.

**The artifact can go stale.** A committed expectation file that no longer matches the planes it
was computed from is worse than none, so each probe is re-derived from the `.bin` files here. This
is deliberately a different path from the script's: it reads the bytes directly rather than through
the script's own helpers, so a bug in those helpers cannot agree with itself.

And the probes are checked for the property that makes them worth running: at a cell centre the two
placement rules agree at all 514 rows, so a probe set without points near a row boundary could only
ever report agreement.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

import numpy as np
import pytest

V2 = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(V2 / "scripts"))

from tests.test_wire import declarations, executable_mask  # noqa: E402

SPIKE = V2 / "spikes" / "g3-render"
PUBLISHED = SPIKE / "fixtures" / "published"
ARTIFACT = V2.parent / "docs" / "experiments" / "s3-10-drawn-pixel.json"
STEM = "own_triangle_grocery_walk"


@pytest.fixture(scope="module")
def artifact() -> dict:
    if not ARTIFACT.exists():
        pytest.skip(f"{ARTIFACT.name} has not been generated")
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def planes() -> dict:
    man = json.loads((PUBLISHED / "manifest.json").read_text(encoding="utf-8"))
    entry = next(l for l in man["layers"] if l["id"] == STEM)
    nrows, ncols = man["nrows"], man["ncols"]

    def read(key: str, dtype) -> np.ndarray:
        return np.frombuffer((PUBLISHED / entry[key]).read_bytes(),
                             dtype=dtype).reshape(nrows, ncols)

    return {"manifest": man, "entry": entry,
            "value": read("value_file", np.uint8), "status": read("status_file", np.uint8),
            "flag": read("flag_file", np.uint8), "dest": read("dest_file", np.dtype("<u2")),
            "table": json.loads((PUBLISHED / entry["dest_table"]).read_text(encoding="utf-8"))}


def js_literals() -> dict:
    """`worker.js`'s palette and hatch, from executable code only."""
    text = (SPIKE / "worker.js").read_text(encoding="utf-8")
    body = executable_mask(text)
    assert len(body) == len(text), "the comment stripper changed the file's length"
    out: dict[str, object] = {}
    for name in ("PX_IN", "PX_NODATA"):
        found = declarations(text, rf"const {name} = packRGBA\(([^)]*)\)")
        assert len(found) == 1, f"{name} is declared {len(found)} times in executable code"
        out[name] = [int(v.strip()) for v in found[0].split(",")]
    for name in ("PX_OUT", "HATCH_PERIOD_MASK", "HATCH_WIDTH"):
        found = declarations(text, rf"const {name} = (\d+)")
        assert len(found) == 1, f"{name} is declared {len(found)} times in executable code"
        out[name] = int(found[0])
    return out


def test_the_python_palette_is_the_workers_palette():
    import measure_drawn_pixel as m

    js = js_literals()
    assert m.PX_IN == js["PX_IN"], f"python {m.PX_IN} against worker.js {js['PX_IN']}"
    assert m.PX_NODATA == js["PX_NODATA"], (
        f"python {m.PX_NODATA} against worker.js {js['PX_NODATA']}")
    assert js["PX_OUT"] == 0 and m.PX_OUT == [0, 0, 0, 0], (
        f"worker.js paints an excluded cell {js['PX_OUT']} and python expects {m.PX_OUT}")
    # The worker masks with `& 7`, which is a period of 8. A period written as a mask is one of the
    # two places this could drift without either number looking wrong on its own.
    assert m.HATCH_PERIOD == js["HATCH_PERIOD_MASK"] + 1, (
        f"python hatches with period {m.HATCH_PERIOD} and worker.js masks with "
        f"{js['HATCH_PERIOD_MASK']}, which is a period of {js['HATCH_PERIOD_MASK'] + 1}")
    assert m.HATCH_WIDTH == js["HATCH_WIDTH"]


def test_an_unknown_cell_off_the_stripe_is_painted_like_an_excluded_one():
    """The hatch is sparse, so the pixel alone does not carry the outcome.

    This is why the oracle predeclares the RGBA from the outcome and the cell index instead of
    letting the probe infer an outcome from what it reads.
    """
    import measure_drawn_pixel as m
    from locfinder.status import Outcome

    on = m.paint_rgba(int(Outcome.UNKNOWN), 0, 0)
    off = m.paint_rgba(int(Outcome.UNKNOWN), 0, 4)
    assert on == m.PX_NODATA
    assert off == m.PX_OUT == m.paint_rgba(int(Outcome.FAIL), 0, 4)
    assert m.paint_rgba(int(Outcome.PASS), 0, 4) == m.PX_IN


def test_the_published_row_rule_keeps_its_half_open_edges():
    """`cellForLonLat` includes the north edge and excludes the south one, and so must this."""
    import measure_drawn_pixel as m

    man = json.loads((PUBLISHED / "manifest.json").read_text(encoding="utf-8"))
    _west, south, _east, north = man["bounds_wgs84"]
    nrows = man["nrows"]
    rows = m.published_rows(np.array([north, south + 1e-12, north - 1e-12]),
                            north, south, nrows)
    assert rows[0] == 0, "the north edge must fall in row 0"
    assert rows[1] == nrows - 1, "a latitude just above the south edge must fall in the last row"
    assert rows[2] == 0


def test_every_probe_expectation_still_matches_the_planes(artifact, planes):
    man, value, status = planes["manifest"], planes["value"], planes["status"]
    flag, dest = planes["flag"], planes["dest"]
    records = planes["table"]["destinations"]
    nrows, ncols = man["nrows"], man["ncols"]
    west, south, east, north = man["bounds_wgs84"]
    assert artifact["published"]["bounds_wgs84"] == man["bounds_wgs84"]
    assert (artifact["published"]["nrows"], artifact["published"]["ncols"]) == (nrows, ncols)

    for probe in artifact["probes"]:
        lon, lat = probe["lon"], probe["lat"]
        inside = (west <= lon < east) and (south < lat <= north)
        if not inside:
            assert probe["expected_published_cell"] is None, probe["id"]
            assert probe["expected_card"] == {"outside": True}, probe["id"]
            continue
        # Re-derived here from the bytes, not from the script's helpers.
        row = int((north - lat) / (north - south) * nrows)
        col = int((lon - west) / (east - west) * ncols)
        assert probe["expected_published_cell"] == {"row": row, "col": col}, probe["id"]
        card = probe["expected_card"]
        assert card["value_byte"] == int(value[row, col]), probe["id"]
        assert card["status_byte"] == int(status[row, col]), probe["id"]
        assert card["route_flag_byte"] == int(flag[row, col]), probe["id"]
        di = int(dest[row, col])
        assert card["destination_index"] == (None if di == 65535 else di), probe["id"]
        if di != 65535:
            names = [p.get("name") for p in records[di].get("places", []) if p.get("name")]
            assert card["destination"]["place_names"] == names, probe["id"]
            assert card["destination"]["place_count"] == records[di]["place_count"], probe["id"]


def test_the_probes_can_fail_and_one_of_them_cannot(artifact):
    sensitive = [p for p in artifact["probes"] if p["sensitive"]]
    assert len(sensitive) >= 3, f"{len(sensitive)} probes able to show the displacement"
    for p in sensitive:
        assert p["expected_drawn_minus_published"] != 0, p["id"]
        assert p["the_picture_contradicts_the_card_here"], p["id"]
        assert p["expected_card"]["rgba_of_the_cell_the_card_names"] \
            != p["expected_rgba_under_the_pointer"], p["id"]

    # Both directions, because the two harms are different and a probe set that only ever shows
    # one of them would leave the other unexamined.
    outcomes = {(p["expected_card"]["outcome"], p["expected_outcome_under_the_pointer"])
                for p in sensitive}
    assert ("PASS", "FAIL") in outcomes, (
        f"no probe where the card includes a spot the picture paints out: {sorted(outcomes)}")
    assert ("FAIL", "PASS") in outcomes, (
        f"no probe where the picture paints in a spot the card excludes: {sorted(outcomes)}")

    inert = next((p for p in artifact["probes"] if p["id"] == "inert_interior"), None)
    assert inert is not None, "the control that must report agreement is gone"
    assert inert["expected_drawn_minus_published"] == 0
    assert inert["the_picture_contradicts_the_card_here"] is False


def test_the_displacement_is_sub_pixel_and_invisible_at_cell_centres(artifact):
    d = artifact["displacement"]
    assert d["row_centres_where_the_two_rules_disagree"] == 0, (
        "if the rules now disagree at a cell centre, the reason the probes sit near row "
        "boundaries no longer holds and the probe set needs rethinking")
    assert 0 < d["max_offset_rows"] < 1, d["max_offset_rows"]
    assert 20.0 < d["max_offset_metres"] < 60.0, d["max_offset_metres"]


def test_the_artifact_carries_its_own_controls(artifact):
    null = artifact["controls"]["null"]["result"]
    one_row = artifact["controls"]["one_row"]["result"]
    assert null and one_row
    for t, rec in null.items():
        assert rec["the_colour_contradicts_the_card"] == 0, (
            f"the null control reports {rec['the_colour_contradicts_the_card']} contradictions at "
            f"{t} minutes, so the comparison does not depend on the displacement")
    for t, rec in artifact["exposure"].items():
        assert one_row[t]["the_colour_contradicts_the_card"] > rec[
            "the_colour_contradicts_the_card"], (
            f"a whole-row shift reports no more than the real rule at {t} minutes")
        # The figure a report may quote: a household shown a colour its own card contradicts.
        assert rec["painted_excluded_card_included"] > 0, t
        assert rec["rows_that_move"] > 0, t


def test_the_artifact_says_what_it_does_not_establish(artifact):
    """A measurement of the page nobody had opened had to say so, in the file a reader quotes.

    A browser opened it on 2026-11-15 and agreed at all eleven probes, so the sentence now has to
    carry both halves: that this file alone did not establish the placement, and where the
    confirmation is. Dropping either one misleads in a different direction.
    """
    text = artifact["what_this_does_not_establish"]
    assert re.search(r"no browser had confirmed it when this was written", text), text
    assert "s3-11-browser-placement.json" in text, (
        "the artifact no longer points at the browser session that confirmed it, so a reader "
        "quoting it would under-claim a measured result")
    assert "s3-5-export-regrid.json" in text, (
        "the artifact no longer points at the other half of the comparison, which is how the two "
        "steps get folded back into one number")
