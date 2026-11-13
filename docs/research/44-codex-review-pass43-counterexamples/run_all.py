"""Codex pass 43's reproducers, re-run from our own checkout.

Each block is the reviewer's, re-run here so the findings do not depend on their session. The
repairs have landed, so most blocks show the FIXED behaviour; the two that reproduce a measurement
rather than a defect (the regrid cost and the corrected size baseline) show numbers.

    v2/.venv/Scripts/python.exe -B docs/research/44-codex-review-pass43-counterexamples/run_all.py
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "v2"))
sys.path.insert(0, str(ROOT / "v2" / "scripts"))

import export_published_layers as e                             # noqa: E402
from locfinder import wire                                      # noqa: E402
from locfinder.status import (CATEGORY_COST_SELECTED, Criterion,  # noqa: E402
                              Reason, Surface, evaluate)


def f1_the_page_boots() -> dict:
    """HIGH. `initWorker` referenced locals of `loadFixtures`, so boot died with a
    ReferenceError before the worker was ever initialised."""
    app = (ROOT / "v2" / "spikes" / "g3-render" / "app.js").read_text(encoding="utf-8")
    return {"loadFixtures_returns_the_planes": "return { manifest, values, statuses };" in app,
            "initWorker_takes_them": "function initWorker(manifest, values, statuses)" in app,
            "caller_passes_them": "fixtures.values, fixtures.statuses" in app}


def f2_the_harness_catches_wrong_decoders() -> dict:
    """HIGH. Two wrong decoders passed all 37 checks: one returning UNKNOWN for NO_PATH, and one
    rotating the whole raster by 10,007 cells. The mutation guard now requires both."""
    out = subprocess.run(["node", str(ROOT / "v2" / "spikes" / "g3-render" / "mutate_worker.mjs")],
                         capture_output=True, text=True, timeout=900)
    lines = [l for l in out.stdout.strip().splitlines() if l]
    return {"exit": out.returncode, "summary": lines[-1] if lines else "",
            "rotation_caught": any("rotated" in l and l.startswith("caught") for l in lines),
            "no_path_caught": any("NO_PATH" in l and l.startswith("caught") for l in lines)}


def f5_the_size_baseline() -> dict:
    """MEDIUM. v1 stored NODATA at missing cells; the baseline compressed v2's own bounds."""
    rows = []
    for stem, _label, cell_m in e.SOURCES:
        if not (e.LAYERS / f"{stem}.npy").exists():
            continue
        surf, _build = e.load_surface(stem)
        value, status = wire.encode_planes(surf)
        v2 = e.deflated(value.tobytes()) + e.deflated(status.tobytes())
        v1 = e.deflated(e.v1_plane(value, status).tobytes())
        rows.append({"cell_m": cell_m, "v2_deflated": v2, "true_v1_deflated": v1,
                     "increase": round(v2 / v1 - 1, 4)})
    return {"source_grid_planes": rows}


def f7_a_fractional_threshold_is_refused() -> dict:
    """MEDIUM. At 10.5 minutes a 610-second OK cell decoded as a failure, and a non-strict bound
    became an exclusion -- the one direction of error the format must not have."""
    surf = Surface(mode="walk", engine="own-graph", target="grocery",
                   aggregation=CATEGORY_COST_SELECTED, horizon_s=7200.0,
                   seconds=np.array([610.0, np.inf]),
                   reason=np.array([int(Reason.OK), int(Reason.OFF_NETWORK)], dtype=np.int8),
                   min_possible_s=np.array([610.0, 610.0])).validate()
    value, status = wire.encode_planes(surf)
    got = {"surface_at_10_5_min": evaluate(
        Criterion(label="g", mode="walk", target="grocery", kind="category",
                  threshold_s=630.0), surf).tolist()}
    try:
        wire.outcome_planes(value, status, threshold_min=10.5, horizon_s=7200.0)
        got["wire_refused"] = False
    except ValueError as exc:
        got["wire_refused"] = True
        got["message"] = str(exc)[:80]
    return got


def f8_a_transposed_build_record_is_refused() -> dict:
    """MEDIUM. The shape guard existed only on the branch that could not get it wrong."""
    build = {"x_min": 661800.0, "y_max": 4003600.0, "cell_m": 200.0,
             "nrows": 258, "ncols": 322, "crs": "EPSG:32617"}
    try:
        e.source_transform(build, (322, 258))
        return {"refused": False}
    except SystemExit as exc:
        return {"refused": True, "message": str(exc)[:90]}


def f3_the_export_regrid() -> dict:
    """MEDIUM. The browser gets a third grid, whose cost S3.1 never measured."""
    path = ROOT / "docs" / "experiments" / "s3-5-export-regrid.json"
    if not path.exists():
        return {"note": "run v2/scripts/measure_export_regrid.py"}
    d = json.loads(path.read_text(encoding="utf-8"))
    return {"omitted_by_the_exported_bounds": d["omitted_by_the_exported_bounds"],
            "moved": {k: v["moved"] for k, v in d["thresholds"].items()}}


def f6_the_peak_is_at_fourteen_minutes() -> dict:
    """MEDIUM. Reporting four thresholds and calling the largest 'the peak' was a claim about the
    four. The sweep over 1..60 puts the maximum at 14 minutes."""
    path = ROOT / "docs" / "experiments" / "s3-1-threshold-sweep.json"
    if not path.exists():
        return {"note": "run compare_candidate_grids.py --thresholds sweep"}
    d = json.loads(path.read_text(encoding="utf-8"))["verdicts"]
    out = {}
    for key in ("cell100_against_address", "cell200_against_address"):
        rows = sorted(((int(t), d[t][key]["moved"]) for t in d), key=lambda r: -r[1])
        out[key] = {"peak_threshold_min": rows[0][0], "peak_moved": rows[0][1],
                    "at_15_min": d["15"][key]["moved"]}
    return out


def main() -> int:
    out = {}
    for fn in (f1_the_page_boots, f2_the_harness_catches_wrong_decoders, f5_the_size_baseline,
               f7_a_fractional_threshold_is_refused, f8_a_transposed_build_record_is_refused,
               f3_the_export_regrid, f6_the_peak_is_at_fourteen_minutes):
        print(f"--- {fn.__name__}")
        out[fn.__name__] = fn()
        print(json.dumps(out[fn.__name__], indent=2, default=str))
    (pathlib.Path(__file__).parent / "results.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
