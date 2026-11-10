"""Re-derive every figure quoted in design §3's E1c subsection, and assert it is present there.

E1c (design revision 12, plan §0 step 2) is a draft awaiting an owner decision, and the case for it
being **reported rather than gated** rests entirely on measured numbers: the claim denominator is the
PASS subset, which is an order of magnitude smaller than the "answered" denominator the design's
earlier example used. If any of those figures is wrong, the conclusion is wrong.

The risk in that amendment is therefore a wrong **number**, not wrong syntax or a missing name. So
this is the check shaped like the risk: it recomputes each figure from the saved arrays and from
`locfinder.measure.stats`, renders it the way the document does, and fails if the document does not
contain it. Run it after any edit to that subsection or to §13's revision-12 row.

    python v2/scripts/verify_e1c_figures.py

Exits non-zero with the offending figure named. 43 figures as of 2026-11-09.
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve()
V2 = HERE.parents[1]
ROOT = V2.parent
sys.path.insert(0, str(V2))

from locfinder.measure import stats  # noqa: E402

LAYERS = V2 / "data" / "layers"
DESIGN = ROOT / "docs" / "plans" / "2026-11-04-s3-measurement-design.md"

# The two frame sizes design §1 declares. Asserted rather than read, so that pointing this script at
# a different layer fails loudly instead of quietly re-deriving a different population's figures.
FRAME_C_CELLS = 330_502
FRAME_B_BUILDINGS = 512_633
PUBLISHED_THRESHOLDS_MIN = (10, 15, 25, 45)
ALLOCATION_N = 500
GATE = 0.01

# The claim denominators the subsection's bounds are computed at, rounded from `ALLOCATION_N` times
# the measured PASS share. Hard-coded so a drift in the arrays fails the equality below.
CLAIM_DENOMINATORS = {("C", 10): 37, ("C", 15): 72, ("B", 10): 78, ("B", 15): 160}


def main() -> int:
    text = DESIGN.read_text(encoding="utf-8")
    try:
        section = text[text.index("### E1c —"):text.index("### E2 — engine disagreement")]
        log = text[text.index("### Revision 12 —"):text.index("### Revision 11 —")]
    except ValueError as exc:
        print(f"FAIL: cannot locate the E1c subsection or its change-log row: {exc}")
        return 1

    checked: list[str] = []
    problems: list[str] = []

    def present(rendered: str, where: str = "section") -> None:
        body = section if where == "section" else log
        if rendered in body:
            checked.append(rendered)
        else:
            problems.append(f"missing from the {where}: {rendered!r}")

    def equals(label: str, got: object, want: object) -> None:
        if got == want:
            checked.append(f"{label} == {want}")
        else:
            problems.append(f"{label}: document says {want!r}, recomputed {got!r}")

    seconds = np.load(LAYERS / "own_triangle_grocery_walk.npy")
    reason = np.load(LAYERS / "own_triangle_grocery_walk_reason.npy")
    buildings = np.load(LAYERS / "own_triangle_buildings_per_cell.npy")
    answered = reason == 0                      # OK; 1 is OFF_NETWORK, 2 is BEYOND_HORIZON
    beyond = reason == 2                        # a known FAIL at every published threshold
    cells = int(seconds.size)
    total_buildings = int(buildings.sum())

    equals("frame C cell count", cells, FRAME_C_CELLS)
    equals("frame B building count", total_buildings, FRAME_B_BUILDINGS)
    present(f"{FRAME_C_CELLS:,} cells and {FRAME_B_BUILDINGS:,} buildings")

    # ---- the PASS table: counts, shares and the expected claim denominator on both frames
    for minutes in PUBLISHED_THRESHOLDS_MIN:
        passing = answered & (seconds <= 60.0 * minutes)
        c_count = int(passing.sum())
        b_count = int(buildings[passing].sum())
        present(f"{c_count:,}")
        present(f"{b_count:,}")
        present(f"{100 * c_count / cells:.4f}%")
        present(f"{100 * b_count / total_buildings:.4f}%")
        if minutes in (10, 15):
            present(f"{ALLOCATION_N * c_count / cells:.1f}")
            present(f"{ALLOCATION_N * b_count / total_buildings:.1f}")

    # ---- the bounds, and the unreachable-gate verdict that is the whole argument for not gating
    for (frame, minutes), m in CLAIM_DENOMINATORS.items():
        passing = answered & (seconds <= 60.0 * minutes)
        share = (int(passing.sum()) / cells if frame == "C"
                 else int(buildings[passing].sum()) / total_buildings)
        equals(f"claim denominator, frame {frame} T={minutes}", round(ALLOCATION_N * share), m)
        equals(f"tolerated_failures(m={m}, {GATE})", stats.tolerated_failures(m, GATE), -1)
        present(f"{100 * stats.clopper_pearson_upper(0, m):.4f}%")
    present("returns **-1** at all four published claim denominators")

    # ---- what a 1.0% gate would cost, on the binding frame and threshold
    needed = next(m for m in range(1, 100_000) if stats.clopper_pearson_upper(0, m) <= GATE)
    equals("smallest m with a reachable 1.0% gate", needed, 299)
    present("*m* ≥ **299**")
    pass_share_c10 = int((answered & (seconds <= 600.0)).sum()) / cells
    binding_n = needed / pass_share_c10
    equals("n for a reachable gate on the binding frame", round(binding_n), 4076)
    present("**4,076**")
    equals("that as a multiple of the allocation", f"{binding_n / ALLOCATION_N:.1f}", "8.2")
    present("**8.2×**")

    # ---- the asymmetry that justifies conditioning the inclusion direction only. The FAIL share is
    # a sound LOWER bound: `min_possible_s` is not saved, so OFF_NETWORK cells proven over the
    # threshold cannot be separated here and are left out rather than assumed in.
    fail_c = (int((answered & (seconds > 600.0)).sum()) + int(beyond.sum())) / cells
    fail_b = (int(buildings[answered & (seconds > 600.0)].sum())
              + int(buildings[beyond].sum())) / total_buildings
    equals("PASS-denominator shrink factor", f"{1 / pass_share_c10:.1f}", "13.6")
    equals("FAIL-denominator shrink factor", f"{1 / fail_c:.1f}", "1.3")
    present("**13.6×**")
    present("**1.3×**")
    present(f"{100 * fail_c:.4f}% of area")
    present(f"{100 * fail_b:.4f}% of structures")

    # ---- two figures the subsection carries over from the design's existing text
    equals("the all-UNKNOWN full-frame bound",
           f"{100 * stats.clopper_pearson_upper(0, ALLOCATION_N):.4f}%", "0.5974%")
    present("0.5974%")
    present("500 × (1 − 0.166722)")

    # ---- the change-log row must carry the same decisive figures, not a drifted copy of them
    for rendered in ("**-1**", "7.7775%", "*m* ≥ 299", "4,076", "**8.2×**",
                     "13.6×", "1.3×", "≈ **37**"):
        present(rendered, where="log")

    for problem in problems:
        print("FAIL:", problem)
    if problems:
        print(f"\n{len(problems)} problem(s); {len(checked)} checks passed")
        return 1
    print(f"all {len(checked)} quoted figures re-derived and present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
