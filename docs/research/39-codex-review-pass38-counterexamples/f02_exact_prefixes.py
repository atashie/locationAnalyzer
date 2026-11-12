"""Exact rational rounded prefixes and symbolic irrational prefixes both exist."""
from common import ROOT
from collections import defaultdict
from fractions import Fraction as F
import math
from locfinder.measure import exact


geom = ((-1e7, 0.), (1e7, 0.))
t = exact.exact_projection(math.nextafter(1e7, 0.), 0., *geom[0], *geom[1])
rounded_o = exact.prefix_arclength(geom, 0, t)
rounded_d = exact.prefix_arclength(geom, 0, F(1))
original_rule = float(abs(F(rounded_d) - F(rounded_o)) / F(exact.total_length(geom)))
adopted = exact.same_edge_fraction(geom, 0, t, 0, F(1))
assert original_rule == 0. and adopted == 9.313225746154785e-17
print(f'Original table (exact subtraction of its defined, rounded prefixes): {original_rule}')
print(f'Adopted span: {adopted}; at weight 6e18: {adopted * 6e18} s')

# Sparse radical expressions: (radicand, rational coefficient). No prefix is rounded.
# A shared irrational prefix sqrt(2), followed by 2e7*t and 2e7, respectively.
# Coordinates for such a record can stay inside the +/-1e7 domain, e.g.
# (-9999999,1),(-1e7,0),(1e7,0).
prefix_o = {F(2): F(1), F(1): F(20000000)*t}
prefix_d = {F(2): F(1), F(1): F(20000000)}
delta = defaultdict(F)
for radicand, coefficient in prefix_d.items():
    delta[radicand] += coefficient
for radicand, coefficient in prefix_o.items():
    delta[radicand] -= coefficient
delta = {q: c for q, c in delta.items() if c}
assert delta == {F(1): F(1, 2**29)}
print('Exact symbolic subtraction (sqrt(2) cancels):', delta)
print('Exact gap:', float(delta[F(1)]), 'm')
print('Non-rational in general does not mean non-representable exactly. '
      'The old table also explicitly defined rounded prefixes, which ARE rational.')
