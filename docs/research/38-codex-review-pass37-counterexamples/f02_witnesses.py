"""F2 and audit of all three named witnesses, on repository Python."""
import math
import sys
from fractions import Fraction as F
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "v2"))
from locfinder.measure import toy


def main():
    a = toy.ToyEdge(0, 1, ((0., 0.), (.1, 0.), (.1, .2), (.1, .5)), 6., 1., oneway=True)
    b = toy.ToyEdge(0, 2, ((0., 0.), (.1, 0.)), 1000., 1/6, oneway=True)
    graph = toy.ToyGraph((a, b))
    lengths = [math.hypot(q[0]-p[0], q[1]-p[1]) for p, q in zip(a.geometry, a.geometry[1:])]
    ordinary = toy.evaluate(graph, (0., 0.), [(.1, 0.)]).objective2_s
    original = toy.ToyEdge.length_m
    try:
        toy.ToyEdge.length_m = property(lambda e: math.fsum(
            math.hypot(q[0]-p[0], q[1]-p[1]) for p, q in zip(e.geometry, e.geometry[1:])))
        adopted = toy.evaluate(graph, (0., 0.), [(.1, 0.)]).objective2_s
        def left(e):
            total = 0.
            for p, q in zip(e.geometry, e.geometry[1:]):
                total += math.hypot(q[0]-p[0], q[1]-p[1])
            return total
        toy.ToyEdge.length_m = property(left)
        alternative = toy.evaluate(graph, (0., 0.), [(.1, 0.)]).objective2_s
    finally:
        toy.ToyEdge.length_m = original
    assert ordinary == adopted == 1000. and alternative == 1.
    print(f"W1 lengths={lengths!r}, sum={sum(lengths)!r}, fsum={math.fsum(lengths)!r}")
    print(f"CLAIM W1 required=1 s; ACTUAL adopted fsum={adopted} s, left accumulation={alternative} s")

    px, py, d = 122.09, -122.08999999999999, 1e-6
    dot = (F(px) + F(py)) * F(d)
    t = dot / (2 * F(d)**2)
    assert px*d + py*d == math.fsum((px*d, py*d)) == 0.
    old = toy.evaluate(toy.ToyGraph((toy.ToyEdge(0, 1, ((0., 0.), (d, d)),
                       1e11, 1e11),)), (px, py), [(0., 0.)])
    # Independent rational residual and parameter, with norm used only for printed totals.
    rx, ry = F(px)-t*F(d), F(py)-t*F(d)
    connector = math.sqrt(float(rx*rx+ry*ry)) / 1.26
    exact_net = float(t * F(1e11))
    print(f"W2 dot={float(dot)!r}, t={float(t)!r}, network={exact_net:.12f} s")
    print(f"W2 current total={old.objective2_s:.12f} s, exact-projection total={connector+exact_net:.12f} s")
    assert old.objective2_s < 600 < connector+exact_net
    assert abs(exact_net - 710.5427357601002) < 1e-10

    x = math.nextafter(1e7, 0.)
    net = float((F(1e7)-F(x)) / F(2e7) * F(1e19))
    old3 = toy.evaluate(toy.ToyGraph((toy.ToyEdge(0, 1, ((-1e7, 0.), (1e7, 0.)),
                        1e19, 1e19),)), (x, 0.), [(1e7, 0.)])
    print(f"W3 endpoint gap={1e7-x!r} m, current total={old3.objective2_s!r} s, real network={net!r} s")
    assert old3.objective2_s < 1e-8 and abs(net-931.3225746154785) < 1e-10
    print("PASS F2: W1's required result contradicts the rule; W2 and W3 stated figures reproduce")


if __name__ == "__main__":
    main()
