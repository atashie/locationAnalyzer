"""F5: a coarse-identity fallback kills the adoption and passes the repaired sentinel."""
from common import ROOT, script
import json
import numpy as np
import shapely
from unittest.mock import patch

p = script('t0_attachment_pilot')
original = p.measure_point


def coarse_fallback(*args, arithmetic='float', **kwargs):
    f = original(*args, arithmetic='float', **kwargs)
    if arithmetic == 'float':
        return f
    x = original(*args, arithmetic='exact', **kwargs)
    # A general, wrong optimisation: keep exact arithmetic only if it moves
    # a raw position between a vertex and an interior, or onto another segment.
    if all(a.occurrence[:3] == b.occurrence[:3]
           for a, b in zip(f['_raw'], x['_raw'])):
        return f
    return x


g = np.array([shapely.LineString([(0., 0.), (3., 4.)])], dtype=object)
tree = shapely.STRtree(g)
point = [(1., 1.)]
live = p.adoption_stats(g, tree, point, 200.)
assert live['raw']['exact_parameter_differs'] == 1
with patch.object(p, 'measure_point', coarse_fallback):
    checks = p.adoption_sentinel()
    dead = p.adoption_stats(g, tree, point, 200.)
    assert [c['counters_fired'] for c in checks] == [True, True, False]
    assert all(v == 0 for k, v in dead['raw'].items() if k != 'positions_compared')
    assert all(v == 0 for name in ('eligibility_changed', 'count_changed',
               'occurrences_changed', 'exact_occurrences_changed', 'places_changed')
               for v in dead[name].values())
    print('sentinel passes:', len(checks), 'of 3; firing pattern:', [c['counters_fired'] for c in checks])
    print('ordinary interior: live exact_parameter_differs =', live['raw']['exact_parameter_differs'],
          '; dead =', dead['raw']['exact_parameter_differs'])
    print('dead adoption: positions compared =', dead['raw']['positions_compared'],
          '; every difference counter = 0')
    cases = json.loads((ROOT / 'docs/research/39-codex-review-pass38-counterexamples/real-witnesses.json')
                       .read_text(encoding='utf-8'))['cases']
    for case in cases:
        gs = np.array([shapely.LineString(c) for c in case['geometries']], dtype=object)
        out = p.adoption_stats(gs, shapely.STRtree(gs), [case['point']], 200.)
        assert all(v == 0 for k, v in out['raw'].items() if k != 'positions_compared')
        assert out['points_with_any_change'] == 0
    print('both committed real census windows also report every difference as zero')

# The negative control checks NOT(P AND V), rather than NOT P AND NOT V.
stats = p.adoption_stats


def stuck_parameter(*args, **kwargs):
    out = stats(*args, **kwargs)
    out['raw']['exact_parameter_differs'] = 1
    return out


with patch.object(p, 'adoption_stats', stuck_parameter):
    checks = p.adoption_sentinel()
    control = checks[-1]
    assert control['exact_parameter_differs'] == 1 and not control['counters_fired']
    print('control passes with exact_parameter_differs stuck at 1:', control['counters_fired'])

def both_stuck(*args, **kwargs):
    out = stuck_parameter(*args, **kwargs)
    out['raw']['vertex_or_interior_differs'] = 1
    return out

with patch.object(p, 'adoption_stats', both_stuck):
    try:
        p.adoption_sentinel()
    except SystemExit:
        print('control DOES reject both counters stuck at 1')
    else:
        raise AssertionError('control should constrain the conjunction')

# The repaired dispatch guard DOES reject pass 38's unconditional fallback.
with patch.object(p, 'measure_point', lambda *a, **kw: original(*a, **(kw | {'arithmetic': 'float'}))):
    try:
        p.adoption_sentinel()
    except SystemExit:
        print('pass-38 unconditional float-dispatch attack: rejected (repair confirmed)')
    else:
        raise AssertionError('old attack should now fail')
