"""Exact occurrence comparison is sound; 'same answers' does not follow from it."""
from common import ROOT, script
from fractions import Fraction as F
import json
import math
import numpy as np
import shapely
from locfinder.measure import exact as e

p = script('t0_attachment_pilot')
assert p.exact_occurrence((7, 'v', 2)) == (7, 'v', 2)
assert p.exact_occurrence((7, 's', 2, .5)) == (7, 's', 2, F(1, 2))
assert p.exact_occurrence((7, 's', 2, .5)) == p.exact_occurrence((7, 's', 2, F(1, 2)))
assert p.exact_occurrence((7, 's', 2, 1/3)) != p.exact_occurrence((7, 's', 2, F(1, 3)))
print('exact_occurrence: vertex, interior, equivalent rational, distinct rational: 4 checks pass')

coords = ((0., 0.), (1., 2.))
g = np.array([shapely.LineString(coords)], dtype=object)
tree = shapely.STRtree(g)
f, x = [p.measure_point(g, tree, 1., 1., 200., arithmetic=a)['_sets']['A'][0]
        for a in ('float', 'exact')]
stats = p.adoption_stats(g, tree, [(1., 1.)], 200.)
assert stats['raw']['parameter_differs'] == 0
assert stats['raw']['exact_parameter_differs'] == 1
print('legacy parameter_differs:', stats['raw']['parameter_differs'],
      '; exact_parameter_differs:', stats['raw']['exact_parameter_differs'])
assert (f.x, f.y) == (x.x, x.y) == (.6, 1.2)
assert float(f.t) == float(x.t) == .6
assert f.residual == x.residual
assert F(f.t) != x.t == F(3, 5)
print('same rounded foot:', (f.x, f.y), '; same parameter image:', float(x.t))
print('unrounded parameters:', F(f.t), x.t)
for name in ('eligibility_changed', 'count_changed', 'occurrences_changed', 'places_changed',
             'exact_occurrences_changed'):
    print(name, stats[name]['A_exact_vs_A'])

# Feed each retained identity into the SAME normative traversal routine. No
# change to rounding, summation, geometry or destination is needed for a number to move.
fracs = [e.same_edge_fraction(coords, 0, F(q.t), 0, F(1)) for q in (f, x)]
assert fracs == [.4, .39999999999999997]
for weight in (1000., 1e19):
    times = [math.fsum([frac * weight, f.residual / p.ACCESS_MPS]) for frac in fracs]
    print('weight', weight, '; reported direct-journey seconds:', times,
          '; absolute difference:', abs(times[0] - times[1]))
    assert times[0] != times[1]

d = json.loads((ROOT / 'docs/experiments/t0-attachment-pilot.json').read_text(encoding='utf-8'))
sets = d['adoption']['sets']
n = sum(s['points'] for s in sets.values())
for convention in ('A_exact_vs_A', 'C_exact_vs_C', 'D_exact_vs_D'):
    changed = sum(s['exact_occurrences_changed'][convention] for s in sets.values())
    print(convention, 'changed point observations:', changed, '/', n,
          '=', f'{100*changed/n:.6f}%')
assert n == 844685
assert sum(s['exact_occurrences_changed']['A_exact_vs_A'] for s in sets.values()) == 573107
print('67.8% is a POINT-observation rate under A; it is not a candidate-identity rate.')

# Replay the two real, committed windows. Distinguish movement of a raw position
# from movement of the candidate C selects. This requires no untracked local data.
data = json.loads((ROOT / 'docs/research/39-codex-review-pass38-counterexamples/real-witnesses.json')
                  .read_text(encoding='utf-8'))
for case in data['cases']:
    gs = np.array([shapely.LineString(c) for c in case['geometries']], dtype=object)
    tr = shapely.STRtree(gs)
    fs, xs = [p.measure_point(gs, tr, *case['point'], 200., arithmetic=a)['_sets']['C']
              for a in ('float', 'exact')]
    shifts = [math.hypot(a.x-b.x, a.y-b.y) for a, b in zip(fs, xs)]
    print('real C retained-candidate displacements (m):', shifts)
    assert max(shifts) > 1e-6
