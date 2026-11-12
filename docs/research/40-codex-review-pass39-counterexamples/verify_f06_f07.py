"""Positive and negative checks of the fingerprint and structural comparator repairs."""
from common import script
from types import SimpleNamespace
import itertools
import math
import random
import struct
import numpy as np
import shapely

p = script('t0_attachment_pilot')
c = script('compare_t0_artifacts')
rng = random.Random(39)
checks = 0
# Finite 2D coordinates include signed zero, adjacent floats and subnormals.
values = [0., -0., math.ulp(0.), -math.ulp(0.), math.nextafter(1., 0.), 1.,
          math.nextafter(1., math.inf), 1e7, -1e7]
values += [rng.uniform(-1e7, 1e7) for _ in range(1000)]
for x in values:
    coords = [(x, -0.), (1., 2.)]
    geom = shapely.LineString(coords)
    wkb = shapely.to_wkb(geom, flavor='iso')
    expected = struct.pack('<dddd', x, -0., 1., 2.)
    assert wkb[9:] == expected
    restored = shapely.from_wkb(wkb)
    assert b''.join(struct.pack('<dd', *pt) for pt in restored.coords) == expected
    checks += 1
print('finite 2D coordinate-bit round trips:', checks)

def records(coords, time=10.):
    gs = np.array([shapely.LineString(coords)], dtype=object)
    return SimpleNamespace(geoms=gs, fwd_time=np.array([time]), rev_time=np.array([time]))

a = records([(0., 0.), (100., 0.)])
for b in (records([(-0., 0.), (100., 0.)]),
          records([(0., 0.), (math.nextafter(100., math.inf), 0.)]),
          records([(0., 0.), (100., 0.)], math.nextafter(10., math.inf))):
    assert p.records_fingerprint(a) != p.records_fingerprint(b)
print('fingerprint detects signed coordinate zero, one coordinate ulp, one time ulp: 3/3')

# Scope: record equality does not certify policy equality. This is a guard limit,
# not a coordinate-bit collision and not an assertion that the copied preparation drifts.
gs = np.array([shapely.LineString([(1., 0.), (1., 1.)]),
               shapely.LineString([(1.005, 0.), (1.005, 1.)])], dtype=object)
tree = shapely.STRtree(gs)
raw = p.raw_positions(gs, [0, 1], 0., 0., arithmetic='exact')
before = len(p.convention_a(raw, 1.))
band = p.ATTACH_TIE_M
try:
    p.ATTACH_TIE_M = 0.
    after = len(p.convention_a(raw, 1.))
finally:
    p.ATTACH_TIE_M = band
assert (before, after) == (2, 1)
print('unchanged records, changed band: A count', before, '->', after,
      '(fingerprint binds records, not rules or query points)')

# bool's bypass of TYPE is followed by a typed _leaf check. Exhaustive small
# JSON values test equality without volatile fields, including container shape.
atoms = [None, False, True, 0, 1, 0., -0., 1., '', 'x']
vals = atoms + [[], {}] + [[x] for x in atoms] + [{'x': x} for x in atoms]
def identity(v):
    if isinstance(v, dict):
        return ('dict', tuple((k, identity(x)) for k, x in sorted(v.items())))
    if isinstance(v, list):
        return ('list', tuple(map(identity, v)))
    return type(v).__name__, repr(v)
for a, b in itertools.product(vals, repeat=2):
    assert bool(c.diff(a, b, ())) == (identity(a) != identity(b)), (a, b)
print('typed structural pairs:', len(vals)**2, '; false equalities: 0')

for before, after, changes in [
    ({'sets': {'s': {'seconds': 1}}}, {'sets': {'s': {'seconds': {'new': []}}}}, False),
    ({'sets': {'s': {'seconds_extra': 1}}}, {'sets': {'s': {'seconds_extra': 2}}}, True),
    ({'sets.s.seconds': 1}, {'sets.s.seconds': 2}, True),
    ({'sets': {'s.seconds': 1}}, {'sets': {'s.seconds': 2}}, True),
    ({'sets': {'s': {'x': {'seconds': 1}}}}, {'sets': {'s': {'x': {'seconds': 2}}}}, True),
    ({'pinned': {'runtime_extra': 1}}, {'pinned': {'runtime_extra': 2}}, True),
]:
    assert bool(c.diff(before, after, c.VOLATILE)) == changes
print('volatile path boundary/subtree checks: 6/6')
assert c.self_test() == 0
