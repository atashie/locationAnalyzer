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

# Read and write BYTES. `read_text`/`write_text` translate newlines, so the pair rewrites an
# LF file to CRLF on Windows -- and hashing the *decoded* text on both sides, as this script
# first did, compares translated to translated and reports "byte-identical" however much the
# bytes changed. A restore check has to hash what is actually on disk.
original = TARGET.read_bytes().decode("utf-8")
digest = hashlib.sha256(TARGET.read_bytes()).hexdigest()

LF = chr(10)
CRLF = chr(13) + chr(10)


def loc(anchor: str) -> str:
    """Match the file's own line ending.

    The anchors below are written with plain newlines. Now that the file is read as bytes
    and decoded without translation, a multi-line anchor would never match on a CRLF
    checkout -- and an inapplicable mutation reports as surviving, which is indistinguishable
    from a test that cannot see it.
    """
    if CRLF in original:
        return anchor.replace(LF, CRLF)
    return anchor



# the confidence check sits between the ordering guard and the zero-claim branch
conf_old = "    _check_confidence(confidence)\n\n    if claims == 0:"
assert original.count(loc(conf_old)) == 1, "cannot locate the confidence check"
# Not pre-localised: the application loop calls loc() on every anchor, and applying it
# twice would turn each CRLF into CR CR LF.
MUTATIONS["remove the _check_confidence call"] = ((conf_old, "    if claims == 0:"),)

failures = 0
try:
    for label, swaps in MUTATIONS.items():
        mutated = original
        for old, new in swaps:
            old, new = loc(old), loc(new)
            assert mutated.count(old) == 1, f"{label}: anchor count {mutated.count(old)}"
            mutated = mutated.replace(old, new, 1)
        TARGET.write_bytes(mutated.encode("utf-8"))
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
    TARGET.write_bytes(original.encode("utf-8"))
    back = hashlib.sha256(TARGET.read_bytes()).hexdigest()
    print(f"\nrestored byte-identical: {back == digest}")

# No "-q" here: pyproject already sets addopts = "-q", and a second one suppresses the
# summary line this parse is looking for -- which is why it printed an empty list.
r = subprocess.run([sys.executable, "-m", "pytest", "tests/test_stats.py", "--no-header"],
                   capture_output=True, text=True, cwd=str(V2))
print("restored suite:", [l for l in r.stdout.splitlines() if "passed" in l or "failed" in l][:1])
raise SystemExit(1 if failures else 0)
