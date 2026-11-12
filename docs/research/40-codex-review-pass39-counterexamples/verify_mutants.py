"""Re-run all 24 existing mutants in memory, including their smoke check.

Unlike the repository harness this never edits exact.py. No temporary files are needed.
"""
from common import ROOT, script, exact_mutant
import os
import subprocess
import sys

h = script('mutate_exact_geometry')
if len(sys.argv) == 2:
    i = int(sys.argv[1])
    label, old, new = h.MUTATIONS[i]
    from locfinder.measure import exact
    m = exact_mutant(old, new)
    # Keep module functions and globals together, then let tests import this module.
    sys.modules['locfinder.measure.exact'] = m
    import locfinder.measure
    locfinder.measure.exact = m
    smoke = h.SMOKE.replace('import locfinder.measure.exact as e;', '')
    exec(smoke, {'e': m})
    import pytest
    code = pytest.main([str(ROOT / 'v2/tests/test_exact_geometry.py'), '-q',
                        '--tb=no', '-p', 'no:cacheprovider'])
    assert code == 1, (label, code)
    print('CAUGHT:', label)
else:
    env = os.environ | {'PYTHONDONTWRITEBYTECODE': '1'}
    for i in range(len(h.MUTATIONS)):
        proc = subprocess.run([sys.executable, '-B', __file__, str(i)], cwd=ROOT,
                              capture_output=True, text=True, env=env)
        print(proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else proc.stderr)
        assert proc.returncode == 0, proc.stdout + proc.stderr
    print('24/24 existing mutants smoke successfully and produce test failures.')
