"""Run the supplied harness and extra attacks in a disposable OUTSIDE-repo copy.

No tracked source is edited. Uses ordinary mkdir permissions because Windows'
restricted runner cannot reopen directories created with mode 0700.
"""
import hashlib
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[3]


def main():
    scratch = pathlib.Path(tempfile.gettempdir()) / ("distancefinder-pass40-mutations-" + uuid.uuid4().hex)
    assert ROOT not in scratch.resolve().parents
    scratch.mkdir()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(scratch),
               PYTEST_ADDOPTS="--basetemp=" + str(scratch / "pytest-temp"))
    files = ["locfinder/__init__.py", "locfinder/measure/__init__.py", "locfinder/measure/certify.py",
             "locfinder/measure/exact.py", "tests/test_certify.py", "scripts/mutate_certify.py"]
    try:
        for relative in files:
            dest = scratch / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / "v2" / relative, dest)
        target = scratch / "locfinder/measure/certify.py"
        original = target.read_bytes()
        source = original.decode("utf-8")
        def command(args):
            p = subprocess.run([sys.executable, "-B", *args], cwd=scratch, env=env,
                               text=True, capture_output=True)
            return {"returncode": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}
        out = {"supplied_harness": command(["scripts/mutate_certify.py"]),
               "supplied_self_test": command(["scripts/mutate_certify.py", "--self-test"])}
        assert target.read_bytes() == original
        extra = [
            ("label every unresolved rational pair exactly tied", "    return ra == rb", "    return True"),
            ("accept non-square radicands as rational roots",
             "    return Fraction(rn, rd) if rn * rn == n and rd * rd == d else None",
             "    return Fraction(rn, rd)"),
            ("replace insufficient precision by a fictitious zero span", "            raise _NeedsPrecision(k)",
             "            return Interval(Fraction(0), Fraction(0))"),
            ("falsify exhausted precision", "    return (None, min(k, max_precision))",
             "    return (None, max_precision + 123)"),
        ]
        out["extra_mutants"] = []
        witness_codes = [
            "a=c.Journey(full_edge_costs=(1.,),label='a'); b=c.Journey(full_edge_costs=(2.,),label='b'); print(c.certify_selection([a,b],0,max_precision=7))",
            "p=c.Partial(((0.,0.),(1.,0.),(2.,1.)),0,F(0),0,F(1),1.); a=c.Journey(partials=(p,)); b=c.Journey(full_edge_costs=(.5,)); print(c._exactly_tied(a,b))",
            "p=c.Partial(((0.,0.),(2.**-200,0.)),0,F(0),0,F(1),1.); a=c.Journey(partials=(p,),label='actual cost 1'); b=c.Journey(full_edge_costs=(.5,),label='actual cost .5'); print(c.certify_selection([a,b],0))",
            "a=c.Journey(full_edge_costs=(1.,),label='a'); b=c.Journey(full_edge_costs=(1.,),label='b'); print(c.certify_selection([a,b],0))",
        ]
        for (label, old, new), witness in zip(extra, witness_codes):
            assert source.count(old) == 1
            target.write_bytes(source.replace(old, new).encode("utf-8"))
            result = command(["-m", "pytest", "tests/test_certify.py", "-q", "-p", "no:cacheprovider"])
            observed = command(["-c", "from fractions import Fraction as F; from locfinder.measure import certify as c; " + witness])
            out["extra_mutants"].append({"mutation": label, **result, "wrong_behavior": observed})
            target.write_bytes(original)

        # A genuinely broken mutant raises NameError only on the suite's three-full-edge case.
        # SMOKE has only two full edges, so the supplied harness banks the crash as a catch.
        spec = importlib.util.spec_from_file_location("review_mutator", scratch / "scripts/mutate_certify.py")
        harness = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(harness)
        old = "        exact_part = sum((_exact(c) for c in self.full_edge_costs), Fraction(0))"
        bad = "        if len(self.full_edge_costs) == 3:\n            return nonexistent_review40_name\n" + old
        driver = scratch / "crash_driver.py"
        driver.write_text(
            "import importlib.util\n"
            "s=importlib.util.spec_from_file_location('h','scripts/mutate_certify.py')\n"
            "h=importlib.util.module_from_spec(s);s.loader.exec_module(h)\n"
            f"h.MUTATIONS=[('NameError outside smoke', {old!r}, {bad!r})]\n"
            "raise SystemExit(h.main())\n", encoding="utf-8")
        out["invalid_mutant_outside_smoke"] = command(["crash_driver.py"])
        # Capture the suite failure the harness discarded.
        target.write_bytes(source.replace(old, bad).encode("utf-8"))
        out["discarded_failure"] = command(["-m", "pytest", "tests/test_certify.py", "-x", "-q", "-p", "no:cacheprovider"])
        target.write_bytes(original)

        # The two retired guards are not equivalent over their documented domains.
        zero_guard = "        if other.lo <= 0:\n            raise ZeroDivisionError(\n"
        no_zero_guard = "        if False:\n            raise ZeroDivisionError(\n"
        index_guard = "    if not 0 <= chosen < len(candidates):\n        raise IndexError("
        no_index_guard = "    if False:\n        raise IndexError("
        # Accommodate either checkout newline style, as the supplied harness does.
        for old, new, code, name in [
            (zero_guard, no_zero_guard,
             "from fractions import Fraction as F; from locfinder.measure.certify import Interval; print(Interval(F(1),F(2)).divided_by(Interval(F(-2),F(-1))))",
             "removed_denominator_guard"),
            (index_guard, no_index_guard,
             "from locfinder.measure.certify import *; a=Journey(full_edge_costs=(1.,),label='a'); print(certify_selection([a],-1))",
             "removed_index_guard")]:
            old, new = harness.localise(old, source), harness.localise(new, source)
            assert source.count(old) == 1
            target.write_bytes(source.replace(old, new).encode("utf-8"))
            out[name] = command(["-c", code])
            target.write_bytes(original)
        out["copy_restored_byte_identically"] = hashlib.sha256(target.read_bytes()).hexdigest() == hashlib.sha256(original).hexdigest()
        print(json.dumps(out, indent=2))
    finally:
        # Absolute checked path was created here; native Python operations only.
        assert scratch.name.startswith("distancefinder-pass40-mutations-") and ROOT not in scratch.resolve().parents
        shutil.rmtree(scratch)


if __name__ == "__main__":
    main()
