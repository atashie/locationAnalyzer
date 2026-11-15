"""Revert each of the migration's rules and watch `tests/test_migrate_audit_sheet.py`.

    python v2/scripts/mutate_migrate.py

`migrate_audit_sheet.py` exists so that an owner's filled sheet can gain a column without losing an
observation, and Codex pass 53 found that its own read-back check could not see a loss: the
snapshot was taken through the same lossy `DictReader` as the write. So the rules it has now are
load-bearing and each one is reverted here.

Reported separately, because they mean different things:

* **caught** -- a test rejected the mutant.
* **SURVIVED** -- nothing did, so that rule is unguarded.
* **INERT** -- the edit matched nothing, so it tested nothing. Not a pass.
* **MISPLACED** -- the edit landed in a different function from the one it names, so whatever
  caught it was a check about something else. Twice this session a mutation reported CAUGHT while
  the rule under test was untouched.
"""
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

V2 = pathlib.Path(__file__).resolve().parents[1]
TARGET = V2 / "scripts" / "migrate_audit_sheet.py"
TESTS = "tests/test_migrate_audit_sheet.py"

#: name -> (anchor regex, replacement, the function it must land in)
MUTATIONS = {
    "read the sheet through a lossy dict instead of positionally": (
        r'    with path\.open\(newline="", encoding="utf-8-sig"\) as fh:\r?\n'
        r'        rows = list\(csv\.reader\(fh\)\)',
        '    with path.open(newline="", encoding="utf-8-sig") as fh:\n'
        '        r = csv.DictReader(fh)\n'
        '        hdr = list(r.fieldnames or ())\n'
        '        return hdr, [[row.get(c, "") for c in hdr] for row in r]\n'
        '        rows = list(csv.reader(fh))',
        "read_positionally",
    ),
    "migrate a sheet with duplicate headers": (
        r'    if duplicates:',
        '    if False:',
        "migrate",
    ),
    "write a row that has more fields than the header": (
        r'    if wide:',
        '    if False:',
        "migrate",
    ),
    # NOT LISTED, deliberately: keying the snapshot positionally rather than by `journey_id`.
    #
    # It is a real strengthening -- the original keyed on `journey_id`, and with two rows sharing a
    # label only the last one's value survived for each key -- but its failure mode needs **two**
    # faults: a duplicated label AND a corruption of the earlier row. Keying alone changes nothing
    # observable, so a one-fault mutation for it cannot be caught for the right reason. The first
    # attempt mutated one side of the comparison and failed it on a key-shape mismatch; the second
    # mutated both sides and was reported "caught" only because the replacement's backreference
    # was mangled and the mutant did not parse, which is what fix (1) above now catches.
    #
    # Recorded as unguarded rather than left to look like coverage. Same decision as
    # `state.lastInCount` in `mutate_worker.mjs`.
    "overwrite an existing output": (
        r'    if not in_place and target\.exists\(\):',
        '    if False:',
        "migrate",
    ),
    "overwrite an existing backup": (
        r'        if backup\.exists\(\):',
        '        if False:',
        "migrate",
    ),
    "let the output be the input": (
        r'    if target\.resolve\(\) == path\.resolve\(\) and not in_place:',
        '    if False:',
        "migrate",
    ),
    "write straight to the target instead of a temporary file": (
        r'        scratch\.replace\(target\)',
        '        pass',
        "migrate",
    ),
    "skip the read-back comparison": (
        r'        if after != before:',
        '        if False:',
        "migrate",
    ),
    "append new columns instead of placing them": (
        r'            header\.insert\(header\.index\(earlier\) \+ 1, column\)\r?\n'
        r'            return header',
        '            header.append(column)\n            return header',
        "insert_after",
    ),
}


def definition_at(source: str, offset: int) -> str:
    name = "(module level)"
    for m in re.finditer(r"^\s*(?:def|class) (\w+)", source, re.M):
        if m.start() > offset:
            break
        name = m.group(1)
    return name


def first_difference(a: str, b: str) -> int:
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return i
    return min(len(a), len(b))


def run() -> tuple[int, str]:
    # Not `-I`: it drops the user site directory where `dateutil` lives, and these tests import
    # the generator, which imports geopandas.
    p = subprocess.run([sys.executable, "-m", "pytest", TESTS, "-p", "no:cacheprovider",
                        "--no-header", "-q"],
                       cwd=V2, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def main() -> int:
    original = TARGET.read_text(encoding="utf-8", newline="")
    shutil.copy2(TARGET, pathlib.Path(tempfile.gettempdir()) / "migrate_audit_sheet.bak")

    code, out = run()
    if code != 0:
        print("BASELINE IS NOT CLEAN -- nothing below means anything")
        print(out[-3000:])
        return 1
    print("baseline clean\n")

    caught = inert = misplaced = 0
    survived = []
    errored = []
    try:
        for name, (pattern, replacement, where) in MUTATIONS.items():
            mutated, n = re.subn(pattern, replacement.replace("\\", "\\\\"),
                                 original, count=1)
            if n != 1:
                print(f"  INERT          {name}  -- the edit matched nothing")
                inert += 1
                continue
            landed = definition_at(original, first_difference(original, mutated))
            if landed != where:
                print(f"  MISPLACED      {name}  -- edited {landed}, not {where}")
                misplaced += 1
                continue
            TARGET.write_text(mutated, encoding="utf-8", newline="")
            code, out = run()
            TARGET.write_text(original, encoding="utf-8", newline="")
            names = sorted(set(re.findall(r"FAILED \S+::(\w+)", out)))
            if code == 0:
                print(f"  SURVIVED       {name}")
                survived.append(name)
            elif not names:
                # **A non-zero exit is not a catch.** Pass 44 found this runner's JavaScript
                # ancestor reporting "9 of 9 caught" with zero mutants executed, because every
                # spawn had failed. A mutant that does not import, or a collection error, exits
                # non-zero without any test having rejected anything.
                print(f"  ERROR          {name}  -- exit {code} with no FAILED line: the mutant "
                      "did not run")
                errored.append(name)
            else:
                print(f"  caught         {name}  [{landed}]")
                for t in names[:3]:
                    print(f"                   by {t}")
                caught += 1
    finally:
        TARGET.write_text(original, encoding="utf-8", newline="")
        assert TARGET.read_text(encoding="utf-8", newline="") == original, "did not restore!"

    print(f"\n{caught} caught, {len(survived)} survived, {inert} inert, {misplaced} misplaced, "
          f"{len(errored)} errored, {len(MUTATIONS)} attempted")
    return 0 if not (survived or inert or misplaced or errored) else 1


if __name__ == "__main__":
    raise SystemExit(main())
