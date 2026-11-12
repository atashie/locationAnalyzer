"""Check the historical comparison and demonstrate its structural blind spots."""
from common import ROOT, script
from copy import deepcopy
import json
import math
import subprocess

compare = script('compare_t0_artifacts')

def revision_json(rev):
    return json.loads(subprocess.check_output(
        ['git', 'show', f'{rev}:docs/experiments/t0-attachment-pilot.json'], cwd=ROOT))

before, after = [revision_json(r) for r in ('df38f99^', 'df38f99')]
assert compare.flatten(before) == compare.flatten(after)
print('Historical refactor:', len(compare.flatten(before)), 'equal nonvolatile leaves')

for a, b in (({'x': []}, {'x': [{}]}),
             ({'x': {}}, {}),
             ({'x': [False]}, {'x': [0]}),
             ({'x': [0.]}, {'x': [-0.]}),
             ({'a.b': 1}, {'a': {'b': 1}})):
    assert compare.flatten(a) == compare.flatten(b)
    print('Undetected:', a, '->', b)

changed = deepcopy(after)
changed['pinned']['runtime']['python'] = 'different arithmetic runtime'
assert compare.flatten(after) == compare.flatten(changed)
print('Runtime metadata is stripped wholesale (documented; versions are provenance, not durations).')

for old, new in ((1., math.nextafter(1., math.inf)),):
    assert compare.flatten({'a': [{'b': old}]}) != compare.flatten({'a': [{'b': new}]})
print('Nested dict/list finite float changes of one ulp ARE detected.')
