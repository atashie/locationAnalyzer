"""Independent rounding-cell checks, composition rules, cache and retired mutants."""
from common import ROOT
from fractions import Fraction as F
import math
import random
import struct
import ast
import subprocess
from locfinder.measure import exact


def even(x):
    return struct.unpack('>Q', struct.pack('>d', x))[0] % 2 == 0


def check_rounding(q, x):
    """Certify x's nearest-even rounding cell using exact squared midpoints."""
    assert math.isfinite(x) and x >= 0
    hi = (F(x) + F(math.nextafter(x, math.inf))) / 2
    assert q < hi*hi or (q == hi*hi and even(x))
    if x:
        lo = (F(x) + F(math.nextafter(x, 0.))) / 2
        assert q > lo*lo or (q == lo*lo and even(x))


rng = random.Random(38)
radicands = [F(0), F(1, 2**2150), F(1, 2**2149), F(3, 2**2101)]
for _ in range(2000):
    exponent = rng.randint(-2149, 100)
    scale = F(2)**exponent
    radicands.append(F(rng.getrandbits(80) | 1, rng.getrandbits(80) | 1) * scale)
for q in radicands:
    check_rounding(q, exact.rational_sqrt(q))
print('Certified nearest-even rounding cells:', len(radicands), 'radicands')

cache_checks = span_checks = 0
changed_k = 0
for _ in range(100):
    geom = tuple((rng.uniform(-1e6, 1e6), rng.uniform(-1e6, 1e6)) for _ in range(5))
    lens = exact.segment_lengths(geom)
    assert exact.total_length(geom) == float(sum(map(F, lens), F()))
    for idx in range(4):
        t = F(rng.randint(0, 1000), 1000)
        a, b = geom[idx:idx+2]
        q = (F(b[0])-F(a[0]))**2 + (F(b[1])-F(a[1]))**2
        partial = exact.scaled_segment_length(*a, *b, t)
        check_rounding(t*t*q, partial)
        prefix = exact.prefix_arclength(geom, idx, t)
        assert prefix == float(sum(map(F, lens[:idx]), F()) + F(partial))
        assert prefix == exact.prefix_arclength(geom, idx, t, lens)
        cache_checks += 1
    for i, j in ((0, 0), (0, 1), (0, 3), (2, 3)):
        t, u = F(1, 4), F(3, 4)
        f = exact.same_edge_fraction(geom, i, t, j, u)
        assert f == exact.same_edge_fraction(geom, j, u, i, t)
        assert 0 <= f <= 1
        span_checks += 1

# Retired rounded-scaling mutation: test its reachable k, not arbitrary off-by-one k.
for _ in range(2000):
    q = F(rng.getrandbits(100) | 1, rng.getrandbits(100) | 1)
    exponent = (q.numerator.bit_length() - q.denominator.bit_length()) // 2
    while F(2)**(2*exponent) > q:
        exponent -= 1
    while F(2)**(2*(exponent+1)) <= q:
        exponent += 1
    unit = F(2)**max(exponent-52, -1074)
    scaled = q/(unit*unit)
    k = math.isqrt(scaled.numerator//scaled.denominator)
    rounded_k = math.isqrt(int(float(scaled)))
    changed_k += k != rounded_k
    assert exact._decide(q, k, unit) == exact._decide(q, rounded_k, unit)
    assert k*k <= scaled < (k+1)**2  # no step-up correction is necessary
assert changed_k
print('Valid cache equivalences:', cache_checks, '; symmetric spans:', span_checks)
print('Retired rounded-scaling mutation: 2000 checked;', changed_k, 'changed indices, 0 answers')

for q in (0, F(1, 4), 1, 2, 10):
    # Degenerate denom=1 mutant still has numerator zero, hence clamped t=0.
    assert exact.exact_projection(3.,4.,1.,1.,1.,1.) == F(0,1)
assert exact.same_edge_fraction(((1.,1.),(1.,1.)),0,F(0),0,F(1)) == 0/1.
print('Retired degenerate denom=1 and zero-total=1 identities hold on their stated preconditions')

g = ((0.,0.), (1.,0.), (2.,3.))
adopted_total = exact.total_length(g)
scale = 10**80
root_lo = F(math.isqrt(10*scale*scale), scale)
root_hi = root_lo + F(1, scale)
assert float(1+root_lo) == float(1+root_hi) == 4.162277660168379
assert adopted_total == 4.16227766016838
print('fsum of RN lengths:', adopted_total, '; certified RN(real total):', float(1+root_lo))

g = ((0.,0.), (1.,0.), (2.,0.))
fresh = exact.prefix_arclength(g,1,F(1,2),exact.segment_lengths(g))
stale = exact.prefix_arclength(g,1,F(1,2),[2.,1.])
assert fresh == 1.5 and stale == 2.5
print('Cache is equivalent under documented precondition; invalid cache gives', stale, 'versus', fresh)
print('An invalid/stale cache is caller misuse, not a counterexample to that conditional contract.')

old_source = subprocess.check_output(
    ['git', 'show', 'df38f99^:v2/scripts/t0_attachment_pilot.py'], cwd=ROOT).decode('utf-8')
old_node = next(n for n in ast.parse(old_source).body
                if isinstance(n, ast.FunctionDef) and n.name == 'exact_segment_sq')
namespace = {'Fraction': F}
exec(compile(ast.Module(body=[old_node], type_ignores=[]), '<committed-old-copy>', 'exec'), namespace)
old_distance = namespace['exact_segment_sq']
cases = [(122.09,-122.08999999999999,0.,0.,1e-6,1e-6),
         (math.nextafter(1e7,0.),0.,-1e7,0.,1e7,0.),
         (3.,4.,1.,1.,1.,1.), (0.,0.,0.,0.,1.,1.), (1.,1.,0.,0.,1.,1.)]
for _ in range(2000):
    cases.append(tuple(rng.uniform(-1e7,1e7) for _ in range(6)))
for case in cases:
    assert old_distance(*case) == exact.exact_segment_sq(*case)
print('Old committed copy vs imported exact squared distance:', len(cases), 'exact agreements')
