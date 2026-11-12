"""A third step-4 rule contradicts revision 13 and is not marked superseded."""
from common import script
from fractions import Fraction as F
from locfinder.measure import exact
import numpy as np
import shapely

geometry = ((5.,5.), (5.,5.), (5.,5.))
fraction = exact.same_edge_fraction(geometry, 0, F(0), 1, F(1))
assert fraction == 0.
print('Revision 13 / exact.py: fraction=', fraction, '; apportioned cost at weight 1000=', fraction*1000)
print('Unsuperseded step-4 zero-total row: charge cost_base+penalty once =', 1000)
pilot = script('t0_attachment_pilot')
geoms = np.empty(1, dtype=object)
geoms[:] = [shapely.LineString(geometry)]
m = pilot.measure_point(geoms, shapely.STRtree(geoms), 5., 5., 200., arithmetic='exact')
assert len(m['_sets']['A']) == 2
print('Actual exact-path structural occurrences:', [p.occurrence for p in m['_sets']['A']])
print('Unsuperseded step-4 zero-total row requires all structural vertices to be ONE occurrence.')
