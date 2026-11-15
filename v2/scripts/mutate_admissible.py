"""Revert each admissibility rule in turn and watch the suite. Run from anywhere:

    python v2/scripts/mutate_admissible.py

`feedback-benchmark-over-point-fixes` records the experiment that makes this necessary: pass 14
reverted four historical fixes and the benchmark I had called the guard turned **none** of its
assertions red. So a claim that a suite guards something is worth nothing until the rule is removed
and the suite is watched.

Ten mutations: the four requirements `docs/s3-decision-report.md` lists, three ways to half-apply
them, and three structural rules — that a refused walk is not recounted as planned, that every
reason is reported rather than the first, and that a walk against no published claim is refused.

A mutation nothing catches is reported as **INERT** and fails the run. It is reported separately
from a catch because the two mean opposite things, and the one time that distinction was collapsed
in `mutate_worker.mjs` it hid two mutations that never applied at all.

The module is restored from the original text in a `finally`, and the restoration is asserted.
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

V2 = Path(__file__).resolve().parents[1]
TARGET = V2 / "locfinder" / "measure" / "admissible.py"

#: Anchors are regexes with `\r?\n`, never string literals: the working copy is CRLF, and an LF
#: anchor matches nothing while every single-line anchor matches fine. Two mutations in
#: `mutate_worker.mjs` were reported INERT for exactly this.
MUTATIONS = {
    "drop the start-door check": (
        r'    if _blank\(record\.start_lon\) or _blank\(record\.start_lat\):\r?\n'
        r'        reasons\.append\("no start door recorded, so the walk\'s origin is unknown"\)',
        '    if False:\n        pass',
    ),
    "accept any recorded door, wherever it is": (
        r'            elif where != \(record\.row, record\.col\):',
        '            elif False:',
    ),
    "drop the destination check": (
        r'    if used is None:\r?\n        reasons\.append\("the destination reached is not '
        r'recorded"\)',
        '    if False:\n        pass',
    ),
    # Re-anchored twice: pass 51 A2 turned the comparison from `!=` into a permitted-set test,
    # and pass 52 F3 turned the set into a name-to-place lookup. Each change was reported DID NOT
    # APPLY on the first run after it, which is what that report is for.
    "accept a walk to any destination": (
        r'    elif used not in by_name:',
        '    elif False:',
    ),
    "drop the route check": (
        r'    if _blank\(record\.route_followed\):',
        '    if False and _blank(record.route_followed):',
    ),
    "drop the timing check": (
        r'    if record\.duration_timed is None:',
        '    if False and record.duration_timed is None:',
    ),
    "treat an untimed duration as timed": (
        r'    elif not record\.duration_timed:',
        '    elif False:',
    ),
    "count a refused walk as planned": (
        r'            inadmissible\.append\(Inadmissible\(label=record\.label, reasons=reasons\)\)',
        '            journeys.append(Journey(label=record.label, '
        'reported_s=float(record.reported_s)))',
    ),
    "report only the first reason": (
        r'        return Admissibility\.NOT_ADMISSIBLE, tuple\(reasons\)',
        '        return Admissibility.NOT_ADMISSIBLE, tuple(reasons[:1])',
    ),
    "score a walk with no published time": (
        r'    if record\.reported_s is None:\r?\n'
        r'        reasons\.append\(\r?\n'
        r'            "the product published no time for this cell, so there is nothing to '
        r'compare"\r?\n'
        r'        \)',
        '    if False:\n        pass',
    ),
    # ------------------------------------------------------------------ Codex pass 51
    "a walk is only a walk if its duration was recorded": (
        r'        found = \[\]',
        "        return () if self.walked_seconds is None else ('walked_seconds',)\n        found = []",
    ),
    # pass 52 F2, both halves
    "the self-report columns are not evidence of a walk": (
        r'                       "duration_timed", "route_identified"\)',
        '                       )',
    ),
    "an untested witness counts as evidence that somebody walked": (
        r'            if excluded and isinstance\(value, str\) and value\.strip\(\)\.lower\(\) '
        r'in excluded:\r?\n                continue',
        '            if False:\n                continue',
    ),
    "drop the missing-duration refusal": (
        r'    if record\.walked_seconds is None:\r?\n        reasons\.append\(',
        '    if False:\n        reasons.append(',
    ),
    "identify the shop reached by its name alone": (
        r'    if _blank\(record\.destination_used_lon\) or _blank\(record\.destination_used_lat\):',
        '    if False:',
    ),
    "accept an arrival anywhere": (
        r'            if gap > DESTINATION_ARRIVAL_M:',
        '            if False:',
    ),
    # pass 52 F3: the arrival matched against the SELECTED place rather than the named one
    "match the arrival against the selected place instead of the named one": (
        r'    target = by_name\.get\(used\) if used is not None else None',
        '    target = permitted[0] if permitted else None',
    ),
    "accept a named place whose location the record does not give": (
        r'    elif _blank\(target\.lon\) or _blank\(target\.lat\):',
        '    elif False:',
    ),
    # pass 52 F9
    "skip the geographic range check on a coordinate": (
        r'    if not \(-180\.0 <= lon_f <= 180\.0 and -90\.0 <= lat_f <= 90\.0\):',
        '    if False:',
    ),
    "accept a route the walker cannot identify": (
        r'    if record\.route_identified is None:',
        '    if False and record.route_identified is None:',
    ),
    "treat an unidentifiable route as identified": (
        r'    elif not record\.route_identified:',
        '    elif False:',
    ),
    "ignore the permitted alternatives on the selected node": (
        r'        for alt in self\.destination_alternatives:',
        '        for alt in ():',
    ),
}


def run() -> tuple[int, str]:
    p = subprocess.run([sys.executable, "-I", "-m", "pytest", "tests/test_admissible.py",
                        "-p", "no:cacheprovider", "--no-header", "-q"],
                       cwd=V2, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def main() -> int:
    original = TARGET.read_text(encoding="utf-8", newline="")
    shutil.copy2(TARGET, Path(tempfile.gettempdir()) / "admissible.py.bak")

    code, out = run()
    if code != 0:
        print("BASELINE IS NOT CLEAN -- nothing below means anything")
        print(out[-3000:])
        return 1
    print("baseline clean\n")

    caught = inert = failed_to_apply = 0
    try:
        for name, (pattern, replacement) in MUTATIONS.items():
            mutated, n = re.subn(pattern, replacement.replace("\\", "\\\\"), original, count=1)
            if n != 1:
                print(f"  DID NOT APPLY  {name}")
                failed_to_apply += 1
                continue
            TARGET.write_text(mutated, encoding="utf-8", newline="")
            code, out = run()
            TARGET.write_text(original, encoding="utf-8", newline="")
            if code == 0:
                print(f"  INERT          {name}  -- nothing caught it")
                inert += 1
            else:
                names = sorted(set(re.findall(r"FAILED tests/test_admissible\.py::(\w+)", out)))
                print(f"  caught         {name}")
                for t in names[:4]:
                    print(f"                   by {t}")
                caught += 1
    finally:
        TARGET.write_text(original, encoding="utf-8", newline="")
        assert TARGET.read_text(encoding="utf-8", newline="") == original, "did not restore!"

    print(f"\n{caught} caught, {inert} inert, {failed_to_apply} did not apply, "
          f"{len(MUTATIONS)} attempted")
    return 1 if (inert or failed_to_apply) else 0


if __name__ == "__main__":
    raise SystemExit(main())
