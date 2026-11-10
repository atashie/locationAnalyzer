"""Verify design §3's E1c subsection: its figures, their placement, and its required claims.

E1c (design revision 12, plan §0 step 2) is a draft awaiting an owner decision. Its argument rests
on measured numbers, so a wrong or misplaced number makes the argument wrong.

## Why this script was rewritten

The first version searched the subsection for each computed figure as a **substring**. Codex pass 31
defeated it with three mutations, two of which it could not see:

| mutation | first version | now |
|---|---|---|
| swap the *T* = 10 and *T* = 15 table rows wholesale | **passed** | caught |
| delete the entire interval-method passage | **passed** | caught |
| flip the conditioning event from product PASS to product FAIL | **passed** | caught |

Every figure was still *present* after the swap — on the wrong row. Presence is not association, and
a check that binds only presence certifies nothing about structure. I had "tested" the first version
by perturbing one digit, which is the single way I had imagined it failing; that is the fourth time
in this project a check has been trusted because it failed in the one way its author pictured. See
`docs/engineering-notes/feedback-verify-the-shape-of-the-risk.md`.

So this version does three things instead of one:

1. **binds each figure to its row, frame and threshold** by parsing the markdown table;
2. **asserts required claims are present**, so deleting a passage fails rather than passing;
3. **self-tests**: `--self-test` applies the mutations above to a scratch copy and fails unless each
   one is caught. The ability to fail is executable, not a sentence in a docstring.

## What it still cannot do

It cannot tell whether the statistics are *right*. It reuses `locfinder.measure.stats` for the
Clopper-Pearson arithmetic, so that part is a consistency check and not an independent validation.
It cannot detect a wrong sampling law, inadequate interval coverage, a bootstrap that is degenerate
at the boundary, an expectation quoted where an assurance is needed, or an invalid inference drawn
from a correct number — pass 31 found one of each, and none of them is reachable from here. Those
need a reviewer.

    python v2/scripts/verify_e1c_figures.py
    python v2/scripts/verify_e1c_figures.py --self-test

Exits non-zero with the offending item named.
"""
from __future__ import annotations

import argparse
import pathlib
import shutil
import sys
import tempfile

import numpy as np

HERE = pathlib.Path(__file__).resolve()
V2 = HERE.parents[1]
ROOT = V2.parent
sys.path.insert(0, str(V2))

from locfinder.measure import stats  # noqa: E402

LAYERS = V2 / "data" / "layers"
DESIGN = ROOT / "docs" / "plans" / "2026-11-04-s3-measurement-design.md"

# Design §1's two frame sizes. Asserted, not read, so pointing this at another layer fails loudly
# instead of quietly re-deriving a different population's figures.
FRAME_C_CELLS = 330_502
FRAME_B_BUILDINGS = 512_633
PUBLISHED_THRESHOLDS_MIN = (10, 15, 25, 45)
ALLOCATION_N = 500
GATE = 0.01

# Claim denominators the subsection's bounds are computed at, rounded from `ALLOCATION_N` x the
# measured PASS share. Hard-coded so a drift in the arrays fails the equality, not just the text.
CLAIM_DENOMINATORS = {("C", 10): 37, ("C", 15): 72, ("B", 10): 78, ("B", 15): 160}

# Claims the subsection must make. Deleting any passage removes its phrase and fails the run.
REQUIRED_CLAIMS = [
    ("the conditioning event", "`= Pr(comparator = FAIL | product = PASS)`"),
    ("the interval method is decided", "The interval, decided 2026-11-10: Clopper-Pearson"),
    ("the bound is labelled approximate", 'Why "approximate", and where it is nonetheless'),
    ("conservative at zero by proof", "conservative on both frames, by proof"),
    ("away from zero it is not established", "the direction is not established"),
    ("inversion is deferred with a condition", "must be revisited in the same"),
    ("E1c is never gated", "**Reported, never gated**"),
    ("the type cannot carry a verdict", "has no verdict field"),
    ("the withdrawn bootstrap is named", "**percentile bootstrap resampling whole cells**"),
    ("its degeneracy is quantified", "`(0.0, 0.0)`"),
    ("frame B's law is hypergeometric", "hypergeometric, not binomial"),
    ("CP is not universally conservative", "is not universally conservative under it"),
    ("the known PASS margin", "computable from the frozen product"),
    ("both candidate interval routes", "Hypergeometric inversion against the known PASS margin"),
    ("the three are now specified", "The three things the first draft left silent, now specified"),
    ("u is numerator only", "enters the **numerator only**"),
    ("expectation is not assurance", "an expectation and not an assurance"),
    ("a reachable threshold exists", "`tolerated_failures(37, 0.08)` = **0**"),
    ("the overreach is withdrawn", '"settled by measurement, not preference" is withdrawn'),
    ("the asymmetry reverses in-layer", "it is the other way round"),
    ("E0 already reports abstention", "E0 already reports **100% `UNKNOWN`**"),
    ("two kinds of undefined", "Two different undefineds"),
    ("the shared-error class is broader", "omitted valid destinations"),
    ("the walk is existence evidence", "**existence evidence**"),
    ("populations are not users", "not users or households"),
    ("the eight published combinations", "There are **eight** published combinations"),
]

# Claims that live in the document header rather than in §3's subsection, so they are matched
# against the whole file. Both record the owner's decision and must not be lost in a re-edit.
HEADER_CLAIMS = [
    ("the owner's decisions are recorded", "The owner's three decisions, 2026-11-10"),
    ("the cheap route to a bar is recorded", "conditional sample drawn from the PASS domain"),
    ("revision 12 is adopted", "ADOPTED by the owner 2026-11-10"),
]

MUTATIONS = {
    "swap the T=10 and T=15 table rows": (
        ("| 10 | 24,245 | **7.3358%** | 80,051 | **15.6157%** | **36.7** | **78.1** |",
         "| 10 | 47,495 | **14.3706%** | 163,850 | **31.9624%** | **71.9** | **159.8** |"),
        ("| 15 | 47,495 | 14.3706% | 163,850 | 31.9624% | 71.9 | 159.8 |",
         "| 15 | 24,245 | 7.3358% | 80,051 | 15.6157% | 36.7 | 78.1 |"),
    ),
    "delete the interval-method passage": (
        ("**The interval, decided 2026-11-10: Clopper-Pearson", "**DELETED:"),
    ),
    # The rule most consequential to lose: owner decision 2 is "report it, no bar".
    "quietly turn E1c into a gate": (
        ("**Reported, never gated**", "**Reported, and gated at 1.0%**"),
    ),
    # The withdrawal must stay on the record so the degenerate method cannot drift back in.
    "erase the record of the withdrawn bootstrap": (
        ("**percentile bootstrap resampling whole cells**", "the method"),
    ),
    "flip the conditioning event to product FAIL": (
        ("`= Pr(comparator = FAIL | product = PASS)`",
         "`= Pr(comparator = PASS | product = FAIL)`"),
    ),
}


def parse_pass_table(section: str) -> dict[int, list[str]]:
    """The PASS table, as {threshold: [cells, area share, buildings, structure share, mC, mB]}.

    Parsed rather than substring-searched, because the defect this exists to catch is a correct
    figure on the wrong row.
    """
    rows: dict[int, list[str]] = {}
    for line in section.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 7:
            continue
        head = cells[0].strip("*` ")
        if not head.isdigit():
            continue
        rows[int(head)] = [c.replace("**", "").replace("`", "").strip() for c in cells[1:]]
    return rows


def check(design_path: pathlib.Path) -> tuple[int, list[str]]:
    text = design_path.read_text(encoding="utf-8")
    problems: list[str] = []
    passed = 0
    try:
        section = text[text.index("### E1c —"):text.index("### E2 — engine disagreement")]
        log = text[text.index("### Revision 12 —"):text.index("### Revision 11 —")]
    except ValueError as exc:
        return 0, [f"cannot locate the E1c subsection or its change-log row: {exc}"]

    def equals(label: str, got: object, want: object) -> None:
        nonlocal passed
        if got == want:
            passed += 1
        else:
            problems.append(f"{label}: document says {want!r}, recomputed {got!r}")

    def contains(label: str, phrase: str, where: str, body: str) -> None:
        nonlocal passed
        if phrase in body:
            passed += 1
        else:
            problems.append(f"missing from the {where}: {label} — expected {phrase!r}")

    seconds = np.load(LAYERS / "own_triangle_grocery_walk.npy")
    reason = np.load(LAYERS / "own_triangle_grocery_walk_reason.npy")
    buildings = np.load(LAYERS / "own_triangle_buildings_per_cell.npy")
    answered = reason == 0                       # OK; 1 is OFF_NETWORK, 2 is BEYOND_HORIZON
    off = reason == 1
    beyond = reason == 2                         # a known FAIL at every published threshold
    cells = int(seconds.size)
    total_buildings = int(buildings.sum())

    equals("frame C cell count", cells, FRAME_C_CELLS)
    equals("frame B building count", total_buildings, FRAME_B_BUILDINGS)
    contains("frame sizes named", f"{FRAME_C_CELLS:,} cells and {FRAME_B_BUILDINGS:,} buildings",
             "section", section)

    # ---- the PASS table, each figure bound to its own row and column
    table = parse_pass_table(section)
    equals("the PASS table's thresholds", sorted(table), sorted(PUBLISHED_THRESHOLDS_MIN))
    for minutes in PUBLISHED_THRESHOLDS_MIN:
        if minutes not in table:
            problems.append(f"the PASS table has no row for T = {minutes}")
            continue
        passing = answered & (seconds <= 60.0 * minutes)
        c_count, b_count = int(passing.sum()), int(buildings[passing].sum())
        want = [f"{c_count:,}", f"{100 * c_count / cells:.4f}%",
                f"{b_count:,}", f"{100 * b_count / total_buildings:.4f}%"]
        if minutes in (10, 15):
            want += [f"{ALLOCATION_N * c_count / cells:.1f}",
                     f"{ALLOCATION_N * b_count / total_buildings:.1f}"]
        else:
            want += ["—", "—"]
        equals(f"the T = {minutes} row", table[minutes], want)

    # ---- the bounds, and the unreachable-gate verdict that is the argument for not gating
    for (frame, minutes), m in CLAIM_DENOMINATORS.items():
        passing = answered & (seconds <= 60.0 * minutes)
        share = (int(passing.sum()) / cells if frame == "C"
                 else int(buildings[passing].sum()) / total_buildings)
        equals(f"claim denominator, frame {frame} T={minutes}", round(ALLOCATION_N * share), m)
        equals(f"tolerated_failures({m}, {GATE})", stats.tolerated_failures(m, GATE), -1)
        contains(f"zero-error bound at m={m}",
                 f"{100 * stats.clopper_pearson_upper(0, m):.4f}%", "section", section)

    # ---- the cost of a reachable gate, on the binding frame and threshold
    needed = next(m for m in range(1, 100_000) if stats.clopper_pearson_upper(0, m) <= GATE)
    equals("smallest reachable 1.0% denominator", needed, 299)
    contains("that denominator", "`n_claim` ≥ **299**", "section", section)
    pass_share_c10 = int((answered & (seconds <= 600.0)).sum()) / cells
    binding_n = needed / pass_share_c10
    equals("n for a reachable gate", round(binding_n), 4076)
    equals("as a multiple of the allocation", f"{binding_n / ALLOCATION_N:.1f}", "8.2")
    contains("the allocation multiple", "**8.2×**", "section", section)

    # ---- E[n_claim] and its SD, which is why 4,076 is an expectation and not an assurance
    expected_m = ALLOCATION_N * pass_share_c10
    sd = (ALLOCATION_N * pass_share_c10 * (1 - pass_share_c10)
          * (cells - ALLOCATION_N) / (cells - 1)) ** 0.5
    contains("E[n_claim]", f"**{expected_m:.4f}**", "section", section)
    contains("SD of n_claim", f"**{sd:.4f}**", "section", section)

    # ---- the T = 45 frame B reversal, the case the first draft generalised away
    b45 = int(buildings[answered & (seconds <= 2700.0)].sum())
    equals("a 1.0% gate at frame B T=45",
           stats.tolerated_failures(round(ALLOCATION_N * b45 / total_buildings), GATE), 0)
    pass45 = b45 / total_buildings
    fail45_lo = (int(buildings[answered & (seconds > 2700.0)].sum())
                 + int(buildings[beyond].sum())) / total_buildings
    fail45_hi = fail45_lo + int(buildings[off].sum()) / total_buildings
    equals("PASS shrink at frame B T=45", f"{1 / pass45:.4f}", "1.2065")
    equals("FAIL share at frame B T=45", f"{100 * fail45_lo:.4f}%", "16.4035%")
    equals("FAIL share ceiling there", f"{100 * fail45_hi:.4f}%", "17.1169%")
    equals("minimum FAIL shrink there", f"{1 / fail45_hi:.2f}", "5.84")
    for rendered in ("**82.8831%**", "**1.2065×**", "**16.4035%**", "**17.1169%**", "**5.84×**"):
        contains("a T=45 reversal figure", rendered, "section", section)

    # ---- the ten-minute asymmetry the draft argued from
    fail_c = (int((answered & (seconds > 600.0)).sum()) + int(beyond.sum())) / cells
    fail_b = (int(buildings[answered & (seconds > 600.0)].sum())
              + int(buildings[beyond].sum())) / total_buildings
    equals("PASS shrink at frame C T=10", f"{1 / pass_share_c10:.1f}", "13.6")
    equals("FAIL shrink at frame C T=10", f"{1 / fail_c:.1f}", "1.3")
    contains("the PASS shrink", "**13.6×**", "section", section)
    contains("the FAIL shrink", "**1.3×**", "section", section)
    contains("FAIL share of area", f"{100 * fail_c:.4f}% of area", "section", section)
    contains("FAIL share of structures", f"{100 * fail_b:.4f}% of structures", "section", section)

    # ---- figures carried over from the design's existing text
    equals("the all-UNKNOWN full-frame bound",
           f"{100 * stats.clopper_pearson_upper(0, ALLOCATION_N):.4f}%", "0.5974%")
    contains("that bound", "0.5974%", "section", section)
    contains("the corrected 417", "500 × (1 − 0.166722)", "section", section)

    # ---- every claim the subsection is required to make, so a deletion fails.
    # Matched against a whitespace-normalised copy: a required claim must survive re-wrapping the
    # paragraph it lives in, and the first version's phrases broke on exactly that.
    flat = " ".join(section.split())
    for label, phrase in REQUIRED_CLAIMS:
        contains(label, " ".join(phrase.split()), "section (normalised)", flat)

    flat_all = " ".join(text.split())
    for label, phrase in HEADER_CLAIMS:
        contains(label, " ".join(phrase.split()), "document header (normalised)", flat_all)

    # ---- the change-log row must carry the decisive figures, not a drifted copy
    for rendered in ("**-1**", "7.7775%", "`n_claim` ≥ 299", "4,076", "**8.2×**",
                     "13.6×", "1.3×", "≈ **37**"):
        contains("a change-log figure", rendered, "log", log)

    return passed, problems


def self_test() -> int:
    """Apply pass 31's three mutations to a scratch copy and require each to be caught."""
    original = DESIGN.read_text(encoding="utf-8")
    backup = pathlib.Path(tempfile.gettempdir()) / "verify_e1c_selftest_backup.md"
    shutil.copy(DESIGN, backup)
    failures = 0
    try:
        for label, swaps in MUTATIONS.items():
            mutated = original
            for old, new in swaps:
                if mutated.count(old) != 1:
                    print(f"SKIP         {label}: anchor not unique ({mutated.count(old)}); "
                          "the mutation needs updating to match the current text")
                    failures += 1
                    break
                mutated = mutated.replace(old, new, 1)
            else:
                DESIGN.write_text(mutated, encoding="utf-8")
                _, problems = check(DESIGN)
                if problems:
                    print(f"caught       {label}")
                else:
                    print(f"NOT CAUGHT   {label}  <-- the check is blind to this")
                    failures += 1
    finally:
        shutil.copy(backup, DESIGN)
    passed, problems = check(DESIGN)
    if problems:
        print(f"\nFAIL: the restored document does not pass: {problems[:3]}")
        return 1
    print(f"\nrestored and passing ({passed} checks)")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify design §3's E1c subsection.")
    parser.add_argument("--self-test", action="store_true",
                        help="mutate the document and require each mutation to be caught")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    passed, problems = check(DESIGN)
    for problem in problems:
        print("FAIL:", problem)
    if problems:
        print(f"\n{len(problems)} problem(s); {passed} checks passed")
        return 1
    print(f"all {passed} checks passed: figures re-derived, bound to their rows, claims present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
