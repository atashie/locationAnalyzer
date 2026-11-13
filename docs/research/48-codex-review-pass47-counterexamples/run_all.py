"""Codex pass 47's reproducers, re-run from our own checkout.

    v2/.venv/Scripts/python.exe -B docs/research/48-codex-review-pass47-counterexamples/run_all.py

No graph needed. The point of this file is the first block: the record does not contain what `E3`
compares, so the scorer's output on it is a number rather than a measurement.
"""
from __future__ import annotations

import csv
import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "v2"))

from locfinder.measure.e3 import Journey, score_e3                  # noqa: E402

SHEET = (ROOT / "docs" / "experiments" / "audit"
         / "triangle-grocery-walk-chapelhill-with-destinations.csv")


def f1_the_record_lacks_what_e3_compares() -> dict:
    """HIGH. A journey identity is the input E3 needs and no type signature enforces."""
    if not SHEET.exists():
        return {"note": f"{SHEET.name} is not on this checkout"}
    with SHEET.open(encoding="utf-8-sig") as fh:
        row = next((r for r in csv.DictReader(fh)
                    if r.get("journey_id") == "band15min_pass-03"), None)
    if row is None:
        return {"note": "band15min_pass-03 not in the sheet"}
    wanted = ("start_lon", "start_lat", "destination_used", "walked_seconds", "notes")
    present = {k: (row.get(k) or "") for k in wanted if k in row}
    return {"fields_E3_would_need": present,
            "columns_available": sorted(row)[:14],
            # The IDENTITY fields are what is missing. `walked_seconds` is populated, which is
            # why requiring every field to be empty was the wrong test.
            "identity_fields_absent": [k for k in ("start_lon", "start_lat", "destination_used")
                                       if not (present.get(k) or "").strip()],
            "the_sheet_already_says_so": "not proof of the route walked" in present.get("notes", "")}


def f2_the_reported_input_is_the_published_answer() -> dict:
    """MEDIUM. `reported_s` is documented as what the product said: the encoded 840 s."""
    arr = np.load(ROOT / "v2" / "data" / "layers" / "own_triangle_grocery_walk.npy")
    stored = float(arr[286, 129])
    encoded = float(np.ceil(stored / 60.0) * 60.0)
    out = {"stored_cell_value_s": stored, "published_encoded_s": encoded,
            "journey_fields": list(Journey.__dataclass_fields__),
            "boundaries_min": {}}
    for reported, label in ((stored, "raw_model"), (encoded, "published")):
        out["boundaries_min"][label] = {
            "median_limb": 1.25 * reported / 60.0,
            "single_journey_limb": max(1.5 * reported, reported + 300.0) / 60.0}
    out["at_17_minutes_with_the_published_input"] = score_e3(
        [Journey("focus", encoded, 17 * 60.0)]).outcome.value
    out["at_25_minutes_with_the_published_input"] = score_e3(
        [Journey("focus", encoded, 25 * 60.0)]).outcome.value
    return out


def f3_more_accurate_walks_cannot_clear_a_failed_set() -> dict:
    """MEDIUM. "More walks can move the verdict" was false."""
    bad = Journey("existing", 840.0, 1500.0)
    rows = {}
    for n in (0, 8, 1000):
        good = [Journey(str(i), 840.0, 840.0) for i in range(n)]
        rows[f"1_offending_plus_{n}_accurate"] = score_e3([bad] + good).outcome.value
    rows["a_revalidated_prediction_of_1201s"] = score_e3(
        [Journey("revised", 1201.0, 1500.0)]).outcome.value
    return rows


def f4_engine_disagreement_was_measured_historically() -> dict:
    """LOW. "Not measured" omitted G1's 599 finite comparisons on the old slice."""
    path = ROOT / "v2" / "data" / "layers" / "matrix_grocery_walk_controlled.json"
    if not path.exists():
        return {"note": "the G1 matrix is not on this checkout"}
    p = json.loads(path.read_text(encoding="utf-8"))
    d = (np.array(p["own_min"]) - np.array(p["ref_min"])) * 60.0
    d = d[np.isfinite(d)]
    return {"finite_comparisons": int(len(d)),
            "signed_median_s": float(np.median(d)),
            "median_absolute_s": float(np.median(np.abs(d))),
            "p90_absolute_s": float(np.quantile(np.abs(d), 0.9)),
            "qualifications": ("old 401x550 slice, old configuration, speed-controlled "
                               "reference, different access treatment, no real-world accuracy "
                               "implication, not replicated at the current extent")}


def f5_the_reports_keyword_form_does_not_run() -> dict:
    """LOW. The published code block raised TypeError."""
    try:
        Journey("x", reported=810.8186, walked=1500)  # type: ignore[call-arg]
        return {"raised": False}
    except TypeError as exc:
        return {"raised": True, "message": str(exc)[:90],
                "actual_fields": list(Journey.__dataclass_fields__)}


def main() -> int:
    out = {}
    for fn in (f1_the_record_lacks_what_e3_compares,
               f2_the_reported_input_is_the_published_answer,
               f3_more_accurate_walks_cannot_clear_a_failed_set,
               f4_engine_disagreement_was_measured_historically,
               f5_the_reports_keyword_form_does_not_run):
        print(f"--- {fn.__name__}")
        out[fn.__name__] = fn()
        print(json.dumps(out[fn.__name__], indent=2, default=str))
    (pathlib.Path(__file__).parent / "results.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
