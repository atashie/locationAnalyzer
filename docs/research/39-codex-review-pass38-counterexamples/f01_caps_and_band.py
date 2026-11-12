"""The adopted exact path still makes rounded cap and band decisions."""
from common import script
from fractions import Fraction as F
import numpy as np
import shapely


def measure(coords, point, cap):
    pilot = script('t0_attachment_pilot')
    geoms = np.empty(len(coords), dtype=object)
    geoms[:] = [shapely.LineString(c) for c in coords]
    return pilot.measure_point(geoms, shapely.STRtree(geoms), *point, cap, arithmetic='exact')


for cap in (200., 300.):
    result = measure([[(0., -1.), (0., 0.)]], (cap, 1e-6), cap)
    p = result['_raw'][0]
    excess = p.exact_sq - F(cap)**2
    assert excess > 0 and p.residual == cap
    assert all(result['eligible'][k] for k in ('A', 'C', 'D'))
    print(f'cap={cap:g}: squared distance exceeds cap^2 by {float(excess):.17g}; '
          f'rounded residual={p.residual}; A/C/D all eligible (exact cap rejects)')

result = measure([[(1., 0.), (1., 1.)], [(1.01, 0.), (1.01, 1.)]], (0., 0.), 200.)
excess = F(1.01) - F(1.) - F(.01)
assert excess > 0 and len(result['_sets']['A']) == 2
print(f'band: exact second distance exceeds minimum + binary64 band by {excess} '
      f'({float(excess):.17g} m); A still retains both')
print('This is a rounded-distance band, distinct from an exact-distance predicate; '
      'it does not implement convention B either (no degree-two normalisation).')
