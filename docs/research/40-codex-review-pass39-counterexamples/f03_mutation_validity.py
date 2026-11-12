"""F3: false INVALID, unexecuted smoke sites, and a surviving summation defect.

All mutations are compiled in memory. --suite runs the extra mutant through the 43 fixtures.
"""
from common import ROOT, script, exact_mutant
from fractions import Fraction as F
from unittest.mock import patch
import subprocess
import sys
from locfinder.measure import exact

h = script('mutate_exact_geometry')
source = (ROOT / 'v2/locfinder/measure/exact.py').read_text(encoding='utf-8')


def run_smoke(module):
    # Execute precisely the harness's smoke string, replacing only its module import.
    code = h.SMOKE.replace('import locfinder.measure.exact as e;', '')
    exec(code, {'e': module})


if '--suite' in sys.argv:
    old = '    return math.fsum(terms) / total'
    new = ('    span = 0.0\n    for term in terms:\n        span += term\n'
           '    return span / total')
    exec(compile(source.replace(old, new), str(exact.__file__), 'exec'), exact.__dict__)
    import pytest
    result = pytest.main([str(ROOT / 'v2/tests/test_exact_geometry.py'), '-q',
                          '--tb=short', '-p', 'no:cacheprovider'])
    g = ((0., 0.), (.1, 0.), (.1, .2), (.1, .5))
    got = exact.same_edge_fraction(g, 0, F(0), 2, F(1))
    print('left-accumulated span fraction:', repr(got), '; required 1.0')
    assert got == 1.0000000000000002
    assert result == 0, 'this witness is expected to survive the existing fixtures'
    raise SystemExit(0)

# A plausible behavioural regression: use true division instead of integer floor
# as the argument to isqrt. Python correctly reports the wrong operand type.
m = exact_mutant('math.isqrt(scaled.numerator // scaled.denominator)',
                 'math.isqrt(scaled.numerator / scaled.denominator)')
try:
    run_smoke(m)
except TypeError as exc:
    print('integer-floor-to-division mutant:', type(exc).__name__, str(exc))
    # Feed its actual exception through the harness's actual classifier.
    stderr = 'Traceback\nTypeError: ' + str(exc)
    with patch.object(h.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, '', stderr)):
        assert h.smoke() == 'TypeError'
    print('harness classification: INVALID; this is an executable arithmetic defect')
else:
    raise AssertionError('wrong division must cause TypeError')

# One current mutation anchors the same-segment branch; smoke uses ONLY a cross-segment span.
old = '    if seg_o == seg_d:\n        span = _partial(seg_o, abs(t_d - t_o))\n        return span / total'
m = exact_mutant(old, '    if seg_o == seg_d:\n        return undefined_span_from_another_scope')
run_smoke(m)
print('broken same-segment branch: smoke passes')
try:
    m.same_edge_fraction(((0., 0.), (10., 0.)), 0, F(1, 4), 0, F(3, 4))
except NameError:
    print('same-segment call: NameError (would be counted caught after passing smoke)')
else:
    raise AssertionError('must reach broken line')

# Same-edge span fsum is a distinct rule from total/prefix fsum. None of the
# 24 mutations attacks this call. Its naive replacement survives all fixtures.
old = '    return math.fsum(terms) / total'
assert all(old not in before for _, before, _ in h.MUTATIONS)
proc = subprocess.run([sys.executable, '-B', __file__, '--suite'], cwd=ROOT,
                      capture_output=True, text=True)
print(proc.stdout)
assert proc.returncode == 0, proc.stderr
