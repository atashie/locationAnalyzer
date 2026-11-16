"""The browser run, pinned so it cannot quietly become a claim about nothing.

`docs/experiments/s3-11-browser-placement.json` is the only evidence in this project that a
browser has ever drawn the publication. It is a record of a session, so nothing here can re-run
it; what these tests can do is stop it drifting away from the oracle it was read against and stop
its headline being repeated after the thing it describes has changed.

Three kinds of check:

**It must still be about the shipped oracle.** Every probe id, every expected cell and the grid in
`s3-10-drawn-pixel.json` must match the run. If someone regenerates the oracle -- a different
threshold, a different bundle, a repaired placement -- this run stops being evidence for it, and
the mismatch should be loud rather than discovered in a quoted number.

**The two instrument defects must stay recorded.** They are the reason the first run reported
fourteen disagreements and the second zero, and a reader who sees only the zero would think the
expectation had been relaxed to meet the page. The repairs are in `probe_placement.js`, so the
record of why they are there has to survive beside them.

**The claim must stay inside its evidence.** The run is one desktop Chrome at
devicePixelRatio 1 at one view, and the affine check is read off an image. Those limits are
asserted here because they are exactly what a later summary would drop.
"""
from __future__ import annotations

import json
import pathlib

import pytest

V2 = pathlib.Path(__file__).resolve().parents[1]
DOCS = V2.parent / "docs"
ARTIFACT = DOCS / "experiments" / "s3-11-browser-placement.json"
ORACLE = DOCS / "experiments" / "s3-10-drawn-pixel.json"
PROBE_JS = V2 / "spikes" / "g3-render" / "probe_placement.js"
SELFTEST_JS = V2 / "spikes" / "g3-render" / "probe_placement_selftest.mjs"


@pytest.fixture(scope="module")
def doc() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def oracle() -> dict:
    return json.loads(ORACLE.read_text(encoding="utf-8"))


RERUN = DOCS / "experiments" / "s3-12-what-the-page-says-at-the-walked-cell.json"


@pytest.fixture(scope="module")
def current_run() -> dict:
    """The newest run of the probe, which is the only one the oracle can be checked against.

    **This moved on 2026-11-16 and the move is the point.** The oracle's `the_walked_cell` probe
    was found to be 400 m from the walked cell -- it read the audit sheet's UTM index as a
    published one -- and was re-pointed. That made the 2026-11-15 run a run against a *different*
    oracle, and this test failed, which is what it is for. The probe was re-run against the
    corrected file and the current run lives beside the reading that found the defect.
    """
    if not RERUN.exists():
        pytest.skip(f"{RERUN.name} has not been written")
    return json.loads(RERUN.read_text(encoding="utf-8"))["the_rerun_against_the_corrected_oracle"]


def test_the_run_is_against_the_oracle_that_is_committed(current_run, oracle):
    """A run against a different oracle is not evidence for this one."""
    run = current_run["run"]
    assert run["ran"] is True
    assert run["oracle"]["max_offset_rows"] == oracle["displacement"]["max_offset_rows"]
    assert run["oracle"]["max_offset_metres"] == oracle["displacement"]["max_offset_metres"]
    assert [p["id"] for p in run["probes"]] == [p["id"] for p in oracle["probes"]]
    for seen, want in zip(run["probes"], oracle["probes"]):
        assert seen["sensitive"] == bool(want.get("sensitive")), seen["id"]
        assert seen.get("card_cell") == want.get("expected_published_cell"), seen["id"]
    # **Recomputed from the probes, never read from the summary** -- pass 55 F7. This asserted
    # `current_run["disagreements"] == 0`, which is a number written beside the run at collection
    # time. A run doctored to contain eleven timed-out hovers, wrong card text and explicit
    # per-probe disagreements passed this test, because nothing read the probes. The summary is
    # still checked -- against what the probes say, so a summary that disagrees with its own run
    # is now a failure rather than the thing being trusted.
    counted = sum(len(p.get("disagreements") or []) for p in run["probes"])
    assert counted == 0, f"{counted} disagreements recorded in the probes"
    assert current_run["disagreements"] == counted, (
        f"the summary says {current_run['disagreements']} and the probes say {counted}")
    contradicting = sum(1 for p in run["probes"]
                        if p.get("sensitive") and p.get("the_picture_contradicts_the_card_here"))
    assert contradicting == 3, contradicting
    assert current_run["sensitive_probes_contradicting_the_card"] == contradicting


def test_the_first_run_is_kept_as_what_it_was(doc, oracle):
    """The 2026-11-15 record is not edited to agree with a file written after it.

    It is still a complete run of the same eleven probes with no disagreements. Exactly one of
    them may now name a different cell from the current oracle -- the probe that was re-pointed
    -- and if any other one drifts, something has edited a record rather than added to it.
    """
    run = doc["the_run"]
    assert run["ran"] is True
    assert [p["id"] for p in run["probes"]] == [p["id"] for p in oracle["probes"]]
    moved = [seen["id"] for seen, want in zip(run["probes"], oracle["probes"])
             if seen.get("card_cell") != want.get("expected_published_cell")]
    assert moved == ["the_walked_cell"], moved


@pytest.fixture(scope="module")
def runs(doc, current_run) -> list:
    """Every run this repository presents as evidence, each with a label for the failure message.

    **Pass 55 F7.** The checks below used to take `doc` and therefore only ever examined the
    2026-11-15 run. The 2026-11-16 re-run is the one the oracle is now checked against -- the
    current confirmation -- and it was getting none of them.
    """
    return [("2026-11-15 (s3-11)", doc["the_run"]),
            ("2026-11-16 re-run (s3-12)", current_run["run"])]


def test_every_probe_agreed_and_the_sensitive_ones_showed_the_contradiction(runs):
    """The result itself, and the shape that makes it a result rather than a tautology."""
    for label, run in runs:
        _every_probe_agreed(label, run)


def _every_probe_agreed(label, run):
    counted = sum(len(p["disagreements"]) for p in run["probes"])
    assert counted == 0, f"{label}: {counted} disagreements in the probes"
    assert run["disagreements_with_the_oracle"] == counted, (
        f"{label}: the run's own summary disagrees with its probes")
    sensitive = [p for p in run["probes"] if p["sensitive"]]
    assert len(sensitive) == 3 == run["sensitive_probes"], label
    contradicting = sum(1 for p in sensitive if p["the_picture_contradicts_the_card_here"])
    assert contradicting == 3, f"{label}: {contradicting}"
    assert run["sensitive_probes_where_the_picture_contradicted_the_card"] == contradicting, label
    for p in sensitive:
        assert p["drawn_minus_published_row"] == 1, (label, p["id"])
        assert p["the_picture_contradicts_the_card_here"] is True, (label, p["id"])
    # And the control that makes agreement non-automatic: a cell centre, where the two placement
    # rules agree at all 514 rows, had to agree and did.
    inert = next(p for p in run["probes"] if p["id"] == "inert_interior")
    assert inert["drawn_minus_published_row"] == 0, label
    assert inert["the_picture_contradicts_the_card_here"] is False, label


def test_both_harm_directions_were_seen_in_the_live_page(runs):
    """2,771 of the 5,801 are painted OUT while included. A run that only ever saw the other
    direction would not be evidence for the half that matters."""
    for label, run in runs:
        pairs = {(tuple(p["rgba_of_the_cell_the_card_names"]) == (0, 0, 0, 0),
                  tuple(p["rgba_under_the_pointer"]) == (0, 0, 0, 0))
                 for p in run["probes"] if p["sensitive"]}
        assert (False, True) in pairs, f"{label}: no probe painted out while the card included it"
        assert (True, False) in pairs, f"{label}: no probe painted in while the card excluded it"


def test_the_hover_landed_on_the_cell_it_claims_to_describe(runs):
    """The second instrument defect, inverted into a requirement: a card read one cell away is a
    card about somewhere else, and would have been reported as agreement.

    **Applied to every run, not only the first** -- pass 55 F7. Eleven timed-out hovers in the
    newest run passed every check in this file until this took `runs`.
    """
    for label, run in runs:
        for p in run["probes"]:
            hover = p["hover"]
            assert hover["placed_on_the_probe_cell"] is True, (label, p["id"])
            assert hover["timed_out"] is False, (label, p["id"])
            assert "Reading this spot" not in hover["card_text"], (label, p["id"])
            off = hover["pixels_from_the_probe_point"]
            assert abs(off["x"]) < 1 and abs(off["y"]) < 1, (label, p["id"], off)
            if p.get("card_cell"):
                assert hover["cell_under_the_pixel_the_pointer_reached"] == p["card_cell"], (
                    label, p["id"])


def test_the_card_a_household_gets_carried_all_three_disclosures(doc):
    """boundary_north is a PASS at exactly the default threshold, on a restricted route, to a
    junction carrying two places. This is the sentence those three disclosures were built for."""
    north = next(p for p in doc["the_run"]["probes"] if p["id"] == "boundary_north")
    text = north["hover"]["card_text"]
    assert north["hover"]["cell_label"].strip() == "(row 100, col 73)"
    assert "Weaver Street Market" in text
    assert "2 places at this junction" in text
    assert "restricted access" in text
    assert "20 min" in text


def test_the_two_instrument_defects_stay_recorded_beside_their_repairs(doc):
    """Fourteen disagreements became zero because the instrument was repaired, not because the
    expectation was relaxed. Both halves of that have to be readable together."""
    found = doc["the_first_run_found_two_defects_in_the_instrument_and_none_in_the_page"]
    assert sum(found["disagreements_by_probe_on_the_first_run"].values()) == 14
    assert "GEOMETRY agreed at all eleven probes" in found["what_happened"]
    colour = found["defect_1_translucent_colour_cannot_be_read_back"]
    assert "premultiplied" in colour["cause"]
    assert "OPAQUE" in colour["control_run_in_the_same_call"]
    pointer = found["defect_2_the_pointer_cannot_be_put_on_a_sub_pixel_point"]
    assert "464.378 arrives as 464" in pointer["cause"]

    probe_js = PROBE_JS.read_text(encoding="utf-8")
    assert "sameColour" in probe_js and "placePointer" in probe_js
    selftest = SELFTEST_JS.read_text(encoding="utf-8")
    assert "quantise" in selftest, "the stub no longer reproduces the canvas read-back"
    assert "Math.trunc(init.clientX)" in selftest, "the stub no longer truncates like a browser"


def test_the_affine_check_states_its_margin_and_what_is_judged_by_eye(doc):
    """The one error the probe cannot see, closed by a picture -- and a picture is weaker
    evidence than a number, which the record has to keep saying."""
    affine = doc["the_affine_check_the_probe_declares_it_cannot_make"]
    n = affine["numbers"]
    assert n["one_row_control_px"] == n["screen_pixels_per_row"]
    assert n["screen_pixels_per_row"] / n["published_minus_drawn_px"] > 3, (
        "the one-row control is no longer several times the sub-row gap, so the picture no "
        "longer separates the hypotheses")
    assert 0.2 < n["published_minus_drawn_rows"] < 0.37
    caveat = affine["what_is_still_judged_by_eye"]
    assert "read off an image, not computed" in caveat
    for rel in affine["images"]:
        assert (DOCS.parent / rel).exists(), rel


def test_the_claim_stays_inside_the_evidence(doc):
    """Every one of these is a sentence a later summary would drop."""
    nots = " ".join(doc["what_this_does_not_establish"])
    assert "phone" in nots
    assert "walked route" in nots
    assert "owner's call" in nots
    # Both halves, for the same reason as `test_the_artifact_says_what_it_does_not_establish`
    # in test_drawn_pixel.py: the sentence is what this run RECORDED, and it was changed the next
    # day. Dropping the first half rewrites a record; dropping the second leaves a reader quoting
    # a defect that has been fixed.
    assert "Every criterion you have on is satisfied here" in nots, (
        "the card's opening sentence as this run recorded it is gone, and the screenshot still "
        "shows it")
    assert "CHANGED 2026-11-16" in nots, (
        "the wording change is no longer recorded beside the sentence it replaced, so a reader "
        "of this artifact would report a fixed overclaim as live")
    assert (DOCS / "experiments" / "s3-11" / "card-after-pass54-wording.png").exists(), (
        "the screenshot of the new wording is missing, so the change is recorded only as prose")
    assert doc["where"]["browser"].startswith("Chrome")
    assert "devicePixelRatio 1" in doc["where"]["browser"]
