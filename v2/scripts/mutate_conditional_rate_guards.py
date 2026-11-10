"""Delete each of `conditional_rate`'s guards in turn and require a test to notice.

Codex pass 32 removed three of them one at a time and **all 146 stats tests passed**: dropping
`confidence` from both Clopper-Pearson calls (so a result labelled 99% could carry a 95% bound),
removing the non-negativity check, and removing `_check_confidence`. The guards were present and
untested, which is the same as absent the moment someone simplifies them.

So the guards now have tests, and this is what shows the tests work. Run it after touching
`conditional_rate` or its tests:

    python v2/scripts/mutate_conditional_rate_guards.py

`stats.py` is restored in a `finally` block and the restoration is verified byte-identical by hash.
Exits non-zero if any mutation survives.
"""
import hashlib
import pathlib
import subprocess
import sys

V2 = pathlib.Path(__file__).resolve().parents[1]
TARGET = V2 / "locfinder/measure/stats.py"

MUTATIONS = {
    "stop forwarding confidence to both CP calls": (
        ("""        bound_range=(clopper_pearson_upper(identified, claims, confidence=confidence),
                     clopper_pearson_upper(completed, claims, confidence=confidence)),""",
         """        bound_range=(clopper_pearson_upper(identified, claims),
                     clopper_pearson_upper(completed, claims)),"""),
    ),
    "remove the non-negativity guard": (
        ("""        if value < 0:
            raise ValueError(f"{name} must be non-negative, got {value}")
    if identified + unresolved > claims:""",
         """    if identified + unresolved > claims:"""),
    ),
    "remove the _check_confidence call": (
        ("""            "bound from an impossible input.")
        if value < 0:""",
         """            "bound from an impossible input.")
        if value < 0:"""),      # placeholder, replaced below
    ),
    "remove the int-count guard": (
        ("""        if isinstance(value, bool) or not isinstance(value, int):""",
         """        if False:"""),
    ),
}

original = TARGET.read_text(encoding="utf-8")
digest = hashlib.sha256(original.encode("utf-8")).hexdigest()

# the confidence check sits between the ordering guard and the zero-claim branch
conf_old = "    _check_confidence(confidence)\n\n    if claims == 0:"
assert original.count(conf_old) == 1, "cannot locate the confidence check"
MUTATIONS["remove the _check_confidence call"] = ((conf_old, "    if claims == 0:"),)

failures = 0
try:
    for label, swaps in MUTATIONS.items():
        mutated = original
        for old, new in swaps:
            assert mutated.count(old) == 1, f"{label}: anchor count {mutated.count(old)}"
            mutated = mutated.replace(old, new, 1)
        TARGET.write_text(mutated, encoding="utf-8")
        r = subprocess.run([sys.executable, "-m", "pytest", "tests/test_stats.py", "-q",
                            "--no-header", "-x"], capture_output=True, text=True, cwd=str(V2))
        if r.returncode:
            caught = [ln.split("::")[-1] for ln in r.stdout.splitlines() if ln.startswith("FAILED")]
            print(f"caught       {label}")
            if caught:
                print(f"               by {caught[0]}")
        else:
            print(f"NOT CAUGHT   {label}  <-- no test sees this")
            failures += 1
finally:
    TARGET.write_text(original, encoding="utf-8")
    back = hashlib.sha256(TARGET.read_text(encoding='utf-8').encode('utf-8')).hexdigest()
    print(f"\nrestored byte-identical: {back == digest}")

r = subprocess.run([sys.executable, "-m", "pytest", "tests/test_stats.py", "-q", "--no-header"],
                   capture_output=True, text=True, cwd=str(V2))
print("restored suite:", [l for l in r.stdout.splitlines() if "passed" in l or "failed" in l][:1])
raise SystemExit(1 if failures else 0)
