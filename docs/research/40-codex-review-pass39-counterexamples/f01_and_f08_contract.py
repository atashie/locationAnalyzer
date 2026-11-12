"""F1/F8: production residuals are not correctly rounded; the plan keeps the blanket claim."""
from common import ROOT, script
from fractions import Fraction as F
from types import SimpleNamespace
import math
import numpy as np
import shapely
from locfinder.measure import exact as e
from locfinder.traveltime.snap import _snap_network

p = script('t0_attachment_pilot')
# The production implementation calls shapely.distance, not rational_sqrt.
dx, dy = 56.31181001463545, 64.61649631867172
geoms = np.array([shapely.LineString([(dx, dy), (2*dx, 2*dy)])], dtype=object)
idx = SimpleNamespace(geoms=geoms, tree=shapely.STRtree(geoms),
                      start_idx=np.array([0]), end_idx=np.array([1]),
                      fwd_time=np.array([1.]), rev_time=np.array([1.]),
                      fwd_cost=np.array([1.]), rev_cost=np.array([1.]))
got = float(_snap_network(idx, np.zeros(2), np.array([0.]), np.array([0.]),
                          node_cost=None).access_m[0])
sq = e.exact_segment_sq(0., 0., dx, dy, 2*dx, 2*dy)
correct = e.rational_sqrt(sq)
# Independent exact rounding-cell certificate, rather than trusting this module.
lo = (F(math.nextafter(correct, 0.)) + F(correct)) / 2
hi = (F(correct) + F(math.nextafter(correct, math.inf))) / 2
assert lo*lo < sq < hi*hi
assert got != correct
print('production _snap_network residual:', repr(got))
print('certified correctly rounded residual:', repr(correct), '; error in ulps:',
      (got-correct)/math.ulp(correct))

for cap in (200., 300.):
    geoms = np.array([shapely.LineString([(0., -1.), (0., 0.)])], dtype=object)
    m = p.measure_point(geoms, shapely.STRtree(geoms), cap, 1e-6, cap, arithmetic='exact')
    q = m['_raw'][0]
    assert q.exact_sq > F(cap)**2 and q.residual == cap
    assert all(m['eligible'].values())
    print('cap', cap, '; exact squared excess:', float(q.exact_sq-F(cap)**2),
          '; rounded admission:', m['eligible'])

plan = (ROOT / 'docs/plans/2026-11-11-step4-comparator-plan.md').read_text(encoding='utf-8')
blanket = ('every comparison that *decides* something made on\n'
           '> the exact value where one exists')
assert blanket in plan
print('plan retains blanket every-comparison clause:', True)
assert '**Three rows of this table were superseded' in plan
assert 'Two rows of 4a.1' in plan
print('plan supersession counts: callout 3; task 4 still 2')

# F2's replacement reason is reproducible and sufficient on the stated witness.
geom = ((-1e7, 0.), (1e7, 0.))
t = e.exact_projection(math.nextafter(1e7, 0.), 0., *geom[0], *geom[1])
so, sd = e.prefix_arclength(geom, 0, t), e.prefix_arclength(geom, 0, F(1))
span = e.same_edge_fraction(geom, 0, t, 0, F(1))
assert so == sd == 20000000.
assert F(sd)-F(so) == 0 and (1-t)*20000000 == F(1, 2**29)
assert span*6e18 == 558.7935447692871
print('F2 confirmed: prefixes', so, sd, '; exact difference', F(sd)-F(so),
      '; span seconds', span*6e18)
