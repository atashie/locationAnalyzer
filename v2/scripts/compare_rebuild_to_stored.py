"""What the 2026-11-10 rebuild changed, against the surface the audit sheets were drawn from.

Two questions, which are not the same question:

1. **Over the whole surface**, how much moved? The stored raster predates `ab01ffa`, which fixed
   `symmetrise` eight hours after the raster was built; a current-code rebuild differed from it on
   **7,246 of 330,502 cells**, and Codex pass 34 reproduced the stored raster bit-for-bit by
   reinstating the historical `symmetrise`. The two way tags added on 2026-11-10 should move
   *nothing* in the walk layer -- no rule reads `surface`, and `classify_access` consults `vehicle`
   only for drive and bike -- so this rebuild should differ from the stored raster by **exactly**
   the symmetrise fix. 7,246 is therefore a prediction, not a summary: a different number means
   something changed that I have not accounted for, and the script says so rather than reporting
   whatever it finds as the answer.

2. **On the sixteen audited journeys**, did any number the owner was told change? The sheet carries
   the seconds, reason, encoded minute and both outcomes as they stood when it was drawn, so the
   comparison needs no pre-rebuild array -- but it checks against one anyway, because a sheet whose
   stored values do not match the bundle it claims to come from is not evidence of anything.

The per-journey verdicts come from `audit_recommendations.load_surface` and `status.evaluate`, the
same two calls that wrote the sheet, rather than from a rule retyped here. A second implementation
of "what counts as PASS" is a second thing that can be wrong, and the first version of this script
had one.

Writes a per-journey delta beside the sheet rather than editing it. The sheet is mid-use: one of
its sixteen journeys has been walked, and rewriting the columns that say what the product predicted
would destroy the comparison that walk exists to make.

Run from v2/:  uv run python scripts/compare_rebuild_to_stored.py
"""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "spikes"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import DATA, GRID, LAYERS, METRO  # noqa: E402
from locfinder.grid import encode_minutes  # noqa: E402
from locfinder import profile  # noqa: E402
from locfinder.measure.frames import file_digest  # noqa: E402
from locfinder.status import Criterion, Outcome, Reason, evaluate  # noqa: E402

_PATH = Path(__file__).resolve().parent / "audit_recommendations.py"
_SPEC = importlib.util.spec_from_file_location("audit_recommendations", _PATH)
audit = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(audit)

STORED = LAYERS / "prerebuild-2026-11-10"
SHEETS = Path(__file__).resolve().parents[2] / "docs" / "experiments" / "audit"
THRESHOLDS_MIN = (10, 15)
PREDICTED_CELLS_DIFFERING = 7246   # the symmetrise fix alone, confirmed by Codex pass 34
STEM = f"own_{METRO.name}_grocery_walk"


def main() -> int:
    new_s = np.load(LAYERS / f"{STEM}.npy")
    new_r = np.load(LAYERS / f"{STEM}_reason.npy")
    old_s = np.load(STORED / f"{STEM}.npy")
    old_r = np.load(STORED / f"{STEM}_reason.npy")
    counts = np.load(STORED / f"own_{METRO.name}_buildings_per_cell.npy")
    assert new_s.shape == old_s.shape == (GRID.nrows, GRID.ncols), (new_s.shape, old_s.shape)

    # ---- question 1: the whole surface ---------------------------------------------------------
    finite_both = np.isfinite(new_s) & np.isfinite(old_s)
    differs = (finite_both & (new_s != old_s)) | (np.isfinite(new_s) != np.isfinite(old_s))
    n_diff = int(differs.sum())
    matches = n_diff == PREDICTED_CELLS_DIFFERING
    print(f"cells differing            {n_diff:,} of {new_s.size:,} ({n_diff / new_s.size:.4%})")
    print(f"  predicted (symmetrise)   {PREDICTED_CELLS_DIFFERING:,}  "
          f"{'AS PREDICTED' if matches else 'NOT PREDICTED -- something else moved'}")
    print(f"finiteness changes         {int((np.isfinite(new_s) != np.isfinite(old_s)).sum()):,}")
    if n_diff:
        m = differs & finite_both
        d = new_s[m] - old_s[m]          # masked first: inf - inf is nan, and warns
        print(f"  faster now               {int((d < 0).sum()):,}   slower now {int((d > 0).sum()):,}")
        print(f"  largest change           {np.abs(d).max():,.1f} s")
    print(f"buildings in changed cells {int(counts[differs].sum()):,}")
    print(f"reason cells differing     {int((new_r != old_r).sum()):,}")

    out: dict = {
        "cells_total": int(new_s.size), "cells_differing": n_diff,
        "cells_differing_predicted": PREDICTED_CELLS_DIFFERING, "matches_prediction": matches,
        "finiteness_changes": int((np.isfinite(new_s) != np.isfinite(old_s)).sum()),
        "buildings_in_changed_cells": int(counts[differs].sum()),
        "reason_cells_differing": int((new_r != old_r).sum()),
        "by_threshold": {},
    }
    for t_min in THRESHOLDS_MIN:
        t = t_min * 60.0
        old_pass = np.isfinite(old_s) & (old_s <= t)
        new_pass = np.isfinite(new_s) & (new_s <= t)
        gained, lost = new_pass & ~old_pass, old_pass & ~new_pass
        b = {
            "cells_pass_before": int(old_pass.sum()), "cells_pass_after": int(new_pass.sum()),
            "cells_gaining_pass": int(gained.sum()), "cells_losing_pass": int(lost.sum()),
            "buildings_gaining_pass": int(counts[gained].sum()),
            "buildings_losing_pass": int(counts[lost].sum()),
        }
        out["by_threshold"][f"{t_min}min"] = b
        print(f"T={t_min:>2} min  PASS cells {b['cells_pass_before']:,} -> "
              f"{b['cells_pass_after']:,}   gained {b['cells_gaining_pass']:,} "
              f"lost {b['cells_losing_pass']:,}   buildings +{b['buildings_gaining_pass']:,} "
              f"-{b['buildings_losing_pass']:,}")

    # ---- question 2: the audited journeys ------------------------------------------------------
    # The same two calls that wrote the sheet, so the verdict rule is not reimplemented here.
    surf, prov = audit.load_surface(
        GRID, category="grocery", mode="walk", metro=METRO.name,
        thresholds_s=tuple(t * 60.0 for t in THRESHOLDS_MIN))
    print(f"\nmin_possible_s origin: {prov['min_possible_s']['origin']}")
    outcomes = {
        t_min: evaluate(Criterion(label=f"grocery within {t_min} min", mode="walk",
                                  target="grocery", kind="category", threshold_s=t_min * 60.0),
                        surf)
        for t_min in THRESHOLDS_MIN
    }

    failures = 0
    for name in ("triangle-grocery-walk-chapelhill", "triangle-grocery-walk"):
        sheet = SHEETS / f"{name}.csv"
        if not sheet.exists():
            continue
        rows = list(csv.DictReader(sheet.open(encoding="utf-8")))
        consistent, deltas = 0, []
        for r in rows:
            i, j = int(r["row"]), int(r["col"])
            old_cell, new_cell = float(old_s[i, j]), float(new_s[i, j])
            # Compare RENDERINGS, not values. The sheet stores `f"{sec:.1f}"`, so "578.0" is a
            # one-decimal rendering of 578.0353 and an exact float32 comparison against the array
            # fails on almost every row -- which is what the first version of this check did, and
            # it reported 0 of 16 rows consistent for a sheet that is in fact consistent. The
            # column is a rendering; the thing to check is that it is a rendering OF THIS ARRAY.
            rendered = f"{old_cell:.1f}" if np.isfinite(old_cell) else ""
            if rendered == r["seconds"]:
                consistent += 1
            enc = (int(encode_minutes(np.array([[new_cell]], dtype=np.float64))[0, 0])
                   if np.isfinite(new_cell) else "")
            d = {
                "journey_id": r["journey_id"], "stratum": r["stratum"], "row": i, "col": j,
                "seconds_sheet": r["seconds"],
                "seconds_rebuilt": f"{new_cell:.1f}" if np.isfinite(new_cell) else "",
                "delta_s": (f"{new_cell - old_cell:+.1f}"
                            if np.isfinite(new_cell) and np.isfinite(old_cell) else ""),
                "reason_sheet": r["reason"], "reason_rebuilt": Reason(int(new_r[i, j])).name,
                "encoded_minutes_sheet": r["encoded_minutes"], "encoded_minutes_rebuilt": enc,
                "walked_seconds": r.get("walked_seconds", ""),
            }
            for t_min in THRESHOLDS_MIN:
                d[f"outcome_{t_min}min_sheet"] = r[f"outcome_{t_min}min"]
                d[f"outcome_{t_min}min_rebuilt"] = Outcome(int(outcomes[t_min][i, j])).name
            d["changed"] = "no" if d["delta_s"] in ("+0.0", "-0.0", "") else "yes"
            d["changed_a_verdict"] = "yes" if any(
                d[f"outcome_{t}min_sheet"] != d[f"outcome_{t}min_rebuilt"]
                for t in THRESHOLDS_MIN) else "no"
            deltas.append(d)

        changed = [x for x in deltas if x["changed"] == "yes"]
        flipped = [x for x in deltas if x["changed_a_verdict"] == "yes"]
        print(f"\n{name}.csv")
        print(f"  rows reproducing the pre-rebuild bundle: {consistent} of {len(rows)}")
        print(f"  journeys whose seconds moved:            {len(changed)} of {len(rows)}")
        print(f"  journeys whose verdict moved:            {len(flipped)} of {len(rows)}")
        for x in changed:
            print(f"    {x['journey_id']:<24} {x['seconds_sheet']:>8} -> "
                  f"{x['seconds_rebuilt']:>8} s ({x['delta_s']:>8})  "
                  f"15 min {x['outcome_15min_sheet']}->{x['outcome_15min_rebuilt']}")
        out.setdefault("sheets", {})[name] = {
            "rows": len(rows), "reproducing_pre_rebuild_bundle": consistent,
            "seconds_moved": len(changed), "verdict_moved": len(flipped),
            "moved": [x["journey_id"] for x in changed],
            "verdict_moved_ids": [x["journey_id"] for x in flipped],
        }
        if consistent != len(rows):
            print("  REFUSING to write this delta: the sheet does not reproduce the bundle it "
                  "names, so the comparison would be between two unrelated things.")
            failures += 1
            continue
        dest = SHEETS / f"{name}-rebuild-delta.csv"
        with dest.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(deltas[0]))
            w.writeheader()
            w.writerows(deltas)
        print(f"  wrote {dest.name}")

        # The sheet's meta names sha256s of arrays that have since been rebuilt. The sample was
        # deliberately NOT redrawn -- one journey has been walked against it, and a redraw against
        # a changed surface would draw different cells and discard that observation -- so the meta
        # stays the record of the draw and says so, rather than leaving a reader to discover that
        # a digest it names matches nothing on disk. Fabricating a redraw would be worse; so would
        # silently rewriting the digests, which would claim a provenance the sample does not have.
        meta_path = SHEETS / f"{name}.meta.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            meta["superseded_by_rebuild"] = {
                "rebuilt": "2026-11-10",
                "why": ("ab01ffa fixed `symmetrise` eight hours after the stored raster was built; "
                        "`surface` and `vehicle` were also added to EXTRA_WAY_TAGS, which changes "
                        "the profile digest and no walk-layer answer"),
                "sample_redrawn": False,
                "sample_not_redrawn_because": ("one journey has been walked against this draw; a "
                                               "redraw on the changed surface would select "
                                               "different cells and discard that observation"),
                "digests_above_describe": ("v2/data/layers/prerebuild-2026-11-10/, where the "
                                           "arrays this sheet was drawn from are preserved"),
                "cells_differing_whole_surface": n_diff,
                "audited_rows_whose_seconds_moved": len(changed),
                "audited_rows_whose_verdict_moved": len(flipped),
                "profile_version_now": profile.profile_version(),
                "arrays_now": {
                    k: file_digest(LAYERS / f"{STEM}{suffix}")
                    for k, suffix in (("seconds", ".npy"), ("reason", "_reason.npy"),
                                      ("min_possible_s", "_min_possible_s.npy"))
                },
                "delta": f"docs/experiments/audit/{name}-rebuild-delta.csv",
            }
            meta_path.write_text(json.dumps(meta, indent=1) + "\n",
                                 encoding="utf-8", newline="\n")
            print(f"  stamped {meta_path.name}")

    path = DATA / "rebuild_2026_11_10_delta.json"
    path.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"\nwrote {path}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
