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
#: Where a mutation is expected to land, for the ones whose anchor could match more than one
#: site. `elif not candidates:` occurs TWICE in `admissibility`, which is exactly the shape that
#: produced a confirm-on-the-wrong-cause in the worker runner twice.
EXPECTED_IN = {
    "drop the destination check": "admissibility",
    "accept a walk to any destination": "admissibility",
    "accept an arrival anywhere": "admissibility",
    "match the arrival against the selected place instead of the named one": "admissibility",
    "accept a named place whose location the record does not give": "admissibility",
    "collapse permitted members by name so the last one wins": "admissibility",
    "match the arrival against the furthest namesake instead of the nearest": "admissibility",
    "drop every namesake when one has an unusable coordinate": "admissibility",
    "a walk is only a walk if its duration was recorded": "evidence_of_a_walk",
    "the self-report columns are not evidence of a walk": "WalkedRecord",
    "an untested witness counts as evidence that somebody walked": "evidence_of_a_walk",
    "ignore the permitted alternatives on the selected node": "permitted_destinations",
    "skip the geographic range check on a coordinate": "check_lonlat",
}

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
        r'    elif not candidates:\r?\n        others = sorted',
        '    elif False:\n        others = sorted',
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
        r'            elif min\(gaps\) > DESTINATION_ARRIVAL_M:',
        '            elif False:',
    ),
    # pass 52 F3: the arrival matched against the SELECTED place rather than the named one
    "match the arrival against the selected place instead of the named one": (
        r'        located = \[p for p in candidates if not _blank\(p\.lon\) '
        r'and not _blank\(p\.lat\)\]',
        '        located = [p for p in permitted[:1] if not _blank(p.lon) '
        'and not _blank(p.lat)]',
    ),
    "accept a named place whose location the record does not give": (
        r'        if not located:',
        '        if False:',
    ),
    # **`elif not candidates:` occurs TWICE in `admissibility`** -- once for the name check and
    # once for the arrival check -- so both mutations anchored on it carry the line that follows
    # as well. A bare anchor would match the first site and `re.subn(count=1)` would mutate it
    # silently, which is the defect pass 51 found in a worker mutation: a mutation that reports
    # CAUGHT while the guard under test was never touched. It is also why this runner reports DID
    # NOT APPLY separately from a catch.
    #
    # pass 53 F5: the by-name collapse, restored. Live on two rows of the committed metro sheet.
    "collapse permitted members by name so the last one wins": (
        r'    candidates = \[p for p in permitted if used is not None and p\.name == used\]',
        '    _by_name = {p.name: p for p in permitted}\n'
        '    candidates = ([_by_name[used]] if used is not None and used in _by_name else [])',
    ),
    "match the arrival against the furthest namesake instead of the nearest": (
        r'            elif min\(gaps\) > DESTINATION_ARRIVAL_M:',
        '            elif max(gaps) > DESTINATION_ARRIVAL_M:',
    ),
    "drop every namesake when one has an unusable coordinate": (
        r'            gaps = \[\]',
        '            gaps = []\n            '
        'located = located if len(located) < 2 else []',
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


def _definition_at(source: str, offset: int) -> str:
    """Which definition contains this character offset, by scanning declarations before it.

    **`class` as well as `def`.** The first version tracked only `def`, and its first report was a
    false positive: `EVIDENCE_FIELDS` is a class attribute of `WalkedRecord`, so the nearest
    preceding `def` was the module-level `metres_between` and the guard accused a correctly placed
    mutation. A detector with its own blind spot is the thing it is checking for.
    """
    name = "(module level)"
    for m in re.finditer(r"^\s*(?:def|class) (\w+)", source, re.M):
        if m.start() > offset:
            break
        name = m.group(1)
    return name


def _first_difference(a: str, b: str) -> int:
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return i
    return min(len(a), len(b))


def main() -> int:
    original = TARGET.read_text(encoding="utf-8", newline="")
    shutil.copy2(TARGET, Path(tempfile.gettempdir()) / "admissible.py.bak")

    code, out = run()
    if code != 0:
        print("BASELINE IS NOT CLEAN -- nothing below means anything")
        print(out[-3000:])
        return 1
    print("baseline clean\n")

    caught = inert = failed_to_apply = misplaced = 0
    try:
        for name, (pattern, replacement) in MUTATIONS.items():
            mutated, n = re.subn(pattern, replacement.replace("\\", "\\\\"), original, count=1)
            if n != 1:
                print(f"  DID NOT APPLY  {name}")
                failed_to_apply += 1
                continue
            # Where did it land? See `_definition_at`: a mutation that edits a different
            # function is caught by a check about something else.
            landed = _definition_at(original, _first_difference(original, mutated))
            if name in EXPECTED_IN and landed != EXPECTED_IN[name]:
                print(f"  MISPLACED      {name}  -- edited {landed}, not "
                      f"{EXPECTED_IN[name]}")
                misplaced += 1
                continue
            TARGET.write_text(mutated, encoding="utf-8", newline="")
            code, out = run()
            TARGET.write_text(original, encoding="utf-8", newline="")
            if code == 0:
                print(f"  INERT          {name}  -- nothing caught it")
                inert += 1
            else:
                names = sorted(set(re.findall(r"FAILED tests/test_admissible\.py::(\w+)", out)))
                print(f"  caught         {name}  [{landed}]")
                for t in names[:4]:
                    print(f"                   by {t}")
                caught += 1
    finally:
        TARGET.write_text(original, encoding="utf-8", newline="")
        assert TARGET.read_text(encoding="utf-8", newline="") == original, "did not restore!"

    print(f"\n{caught} caught, {inert} inert, {failed_to_apply} did not apply, "
          f"{misplaced} misplaced, {len(MUTATIONS)} attempted")
    return 1 if (inert or failed_to_apply or misplaced) else 0


if __name__ == "__main__":
    raise SystemExit(main())
