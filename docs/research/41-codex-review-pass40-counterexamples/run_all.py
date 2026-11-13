"""Reproduce the pass-40 review. All scratch directories are outside the repo.

Usage: v2/.venv/Scripts/python.exe -B docs/research/41-codex-review-pass40-counterexamples/run_all.py [--suite]
"""
import argparse
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import uuid

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def run(args, output, cwd=ROOT):
    proc = subprocess.run([sys.executable, "-B", *map(str, args)], cwd=cwd,
                          env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
                          capture_output=True, text=True)
    (HERE / output).write_text(proc.stdout + proc.stderr, encoding="utf-8")
    if proc.returncode:
        raise RuntimeError(f"{args[0]} exited {proc.returncode}; see {output}")
    print(f"wrote {output}", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--suite", action="store_true")
    args = ap.parse_args()
    for stem in ("core", "population", "t4", "mutations"):
        run([HERE / (stem + ".py")], stem + "-output.json")
    run([ROOT / "v2/scripts/measure_certified_argmin.py", "--draws", "5000", "--out", HERE / "remeasured.json"],
        "measurement-output.txt", cwd=ROOT / "v2")
    if args.suite:
        scratch = pathlib.Path(tempfile.gettempdir()) / ("distancefinder-pass40-suite-" + uuid.uuid4().hex)
        assert ROOT not in scratch.resolve().parents
        # Do not precreate basetemp: pytest will mkdir it. Restrict the Windows
        # permission workaround to this subprocess and its test temp directories.
        wrapper = ("import os,sys; orig=os.mkdir; "
                   "os.mkdir=lambda path,mode=0o777,*,dir_fd=None: orig(path,0o777,dir_fd=dir_fd); "
                   "import pytest; sys.exit(pytest.main(['-o','addopts=','-q','-p','no:cacheprovider',"
                   "'--basetemp',sys.argv[1]]))")
        try:
            run(["-c", wrapper, scratch], "suite-output.txt", cwd=ROOT / "v2")
        finally:
            if scratch.exists():
                shutil.rmtree(scratch)


if __name__ == "__main__":
    main()
