"""Audit artifact arithmetic, the historical refactor and the generated write-up without writes."""
from common import ROOT, script
import json
import math
from fractions import Fraction as F
import subprocess
import sys

c = script('compare_t0_artifacts')
d = json.loads((ROOT / 'docs/experiments/t0-attachment-pilot.json').read_text(encoding='utf-8'))
sets = d['adoption']['sets']
expected = {
    'positions_compared': 36555718,
    'residual_differs': 2142080,
    'arclength_differs': 16459230,
    'exact_parameter_differs': 2142228,
    'rounded_parameter_image_differs': 1333808,
    'position_differs': 42,
    'vertex_or_interior_differs': 0,
}
assert sum(s['points'] for s in sets.values()) == 844685
for key, value in expected.items():
    got = sum(s['raw'][key] for s in sets.values())
    assert got == value
    print(key, got)
assert all(s['raw']['parameter_differs'] == 0 for s in sets.values())
print('legacy parameter_differs:', sum(s['raw']['parameter_differs'] for s in sets.values()),
      '(dead counter; disagrees with both new counters)')
for key in ('max_abs_residual_diff_m', 'max_abs_arclength_diff_m', 'max_position_shift_m'):
    print(key, max(s['raw'][key] for s in sets.values()))
for key in ('eligibility_changed', 'count_changed', 'occurrences_changed', 'places_changed'):
    print(key, {k: sum(s[key][k] for s in sets.values()) for k in next(iter(sets.values()))[key]})
assert all(not any(s[k].values()) for s in sets.values()
           for k in ('eligibility_changed', 'count_changed'))
assert sum(s['occurrences_changed']['C_exact_vs_C'] for s in sets.values()) == 2
assert sum(s['places_changed']['C_exact_vs_C'] for s in sets.values()) == 2
assert all(s['exact_occurrences_changed']['A_exact_vs_A'] == s['points_with_any_change']
           for s in sets.values())
seconds = sum(s['seconds'] for s in sets.values())
print('adoption recorded runtime seconds:', seconds, '; minutes:', seconds/60)
print('exact / rounded parameter difference count:', 2142228/1333808)
print('graph records:', d['graph']['design_records'], '; fingerprint:',
      d['graph']['design_records_fingerprint'])

def historical(revision):
    return json.loads(subprocess.check_output(
        ['git', 'show', revision + ':docs/experiments/t0-attachment-pilot.json'], cwd=ROOT))

a, b = historical('df38f99^'), historical('df38f99')
assert c.diff(a, b, c.VOLATILE) == []

def leaves(v, path=()):
    if c._volatile(path, c.VOLATILE):
        return 0
    if isinstance(v, dict):
        return sum(leaves(x, path+(k,)) for k, x in v.items())
    if isinstance(v, list):
        return sum(leaves(x, path+(f'#{i}',)) for i, x in enumerate(v))
    return 1

assert leaves(a) == leaves(b) == 610
print('historical refactor: 610 nonvolatile leaves each, 0 structural differences')
proc = subprocess.run([sys.executable, '-B', str(ROOT / 'v2/scripts/render_t0_results.py'), '--check'],
                      cwd=ROOT, capture_output=True, text=True)
print(proc.stdout.strip())
assert proc.returncode == 0, proc.stderr

# Section 6's approximate 'three quarters' is not the measured point rate.
print('point rate under A:', 100*573107/844685,
      '; percentage points below three quarters:', 75-100*573107/844685)
print('The original 135 ms benchmark and pre-cache runtime are not stored in this artifact.')

# Certify the search-derived expected literals without executing the root implementation.
# For a positive non-tie answer x, its rounding cell is bounded by squared
# exact midpoints to its immediate floating-point neighbours.
t = F(93, 1222)
cases = [
    (t*t*(F(1.150468525493579)**2 + F(.6047831353619284)**2), .09891686315900601),
    (F(397655352315, 2**2100), 5.227065821602e-311),
    (F(4194304.125000001)**2 + F(.06250000093132257)**2, 4194304.125000001),
]
for q, value in cases:
    lo = (F(math.nextafter(value, 0.)) + F(value))/2
    hi = (F(math.nextafter(value, math.inf)) + F(value))/2
    assert lo*lo < q < hi*hi
print('search-derived fixture literals independently certified:', len(cases))
