"""Run the real comparison and a sentinel bypass in memory."""
from common import script
from fractions import Fraction as F
from unittest.mock import patch
import math
import numpy as np
import shapely


pilot = script('t0_attachment_pilot')
geoms = np.empty(1, dtype=object)
geoms[:] = [shapely.LineString([(0., 0.), (3., 4.)])]
tree = shapely.STRtree(geoms)
f, x = [pilot.measure_point(geoms, tree, 1., 1., 200., arithmetic=a)
        for a in ('float', 'exact')]
pf, px = [m['_sets']['A'][0] for m in (f, x)]
stats = pilot.adoption_stats(geoms, tree, [(1., 1.)], 200.)
assert F(pf.t) != px.t and float(px.t) == pf.t
assert pilot.coarse_occurrence(pf.occurrence) == pilot.coarse_occurrence(px.occurrence)
assert stats['raw']['parameter_differs'] == 0
assert stats['points_with_any_change'] == 0
assert stats['raw']['position_differs'] == 1
print('Interior occurrence parameters:', repr(pf.t), 'versus', px.t)
print('Exact parameter difference:', F(pf.t) - px.t)
print('Reported parameter differences:', stats['raw']['parameter_differs'])
print('Positions:', (pf.x, pf.y), 'versus', (px.x, px.y))
print('Reported candidate changes:', stats['points_with_any_change'])
print('Raw position changes:', stats['raw']['position_differs'])

# Even position_differs is based on rounded XY, not exact_position. Another
# point has distinct exact parameters/positions but identical rounded coordinates.
geoms[:] = [shapely.LineString([(0., 0.), (1., 1.)])]
tree = shapely.STRtree(geoms)
point = (.1, .2)
f, x = [pilot.measure_point(geoms, tree, *point, 200., arithmetic=a)
        for a in ('float', 'exact')]
pf, px = [m['_raw'][0] for m in (f, x)]
assert F(pf.t) != px.t
print('Second exact parameter difference:', F(pf.t) - px.t)
print('Second rounded positions:', (pf.x, pf.y), (px.x, px.y))

# This changes only measure_point's arithmetic dispatch; the primitive paths
# still exist and the sentinel tests them, but the census no longer uses them.
measure = pilot.measure_point
def misdispatch(*args, **kwargs):
    kwargs['arithmetic'] = 'float'
    return measure(*args, **kwargs)

with patch.object(pilot, 'measure_point', misdispatch):
    sentinels = pilot.adoption_sentinel()
    stats = pilot.adoption_stats(geoms, tree, [point], 200.)
    assert all(s['differs'] for s in sentinels)
    assert all(v == 0 for k, v in stats['raw'].items() if k != 'positions_compared')
    print('Misdispatched exact census: sentinel passes', len(sentinels), 'of', len(sentinels),
          '; compared', stats['raw']['positions_compared'], 'position; every raw delta zero')

# Conversely, like-with-like enumeration DOES detect W2/W3 endpoint clamp flips.
for coords, point in (
    ([(0., 0.), (1e-6, 1e-6)], (122.09, -122.08999999999999)),
    ([(-1e7, 0.), (1e7, 0.)], (math.nextafter(1e7, 0.), 0.)),
):
    geoms[:] = [shapely.LineString(coords)]
    stats = pilot.adoption_stats(geoms, shapely.STRtree(geoms), [point], 200.)
    assert stats['raw']['vertex_or_interior_differs'] == 1
    print('End-to-end clamp counter:', stats['raw']['vertex_or_interior_differs'])
