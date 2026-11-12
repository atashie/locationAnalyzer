"""F6: original-graph convention comparisons omit representation exposure."""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "v2"))
from locfinder.measure.toy import ToyEdge, ToyGraph, evaluate


def main():
    original = ToyGraph((ToyEdge(0, 1, ((0., 0.), (100., 0.)), 1199.95, 1199.95, oneway=True),))
    transformed = ToyGraph((ToyEdge(0, 1, ((0., 0.), (50., 0.), (100., 0.)),
                                    1199.95, 1199.95, oneway=True),))
    point = (49.995, 0.)
    old = evaluate(original, point, [(100., 0.)]).objective1_s
    new = evaluate(transformed, point, [(100., 0.)]).objective1_s
    # On the original straight segment every convention has exactly the same minimum.
    c_or_d = (1-point[0]/100)*1199.95
    assert abs(old-c_or_d) < 1e-10
    assert old > 600 > new
    assert math.ceil(old/60) == 11 and math.ceil(new/60) == 10
    print(f"ACTUAL original A=C=D={old:.12f} s FAIL, encoded 11; original paired disagreement=0")
    print(f"ACTUAL subdivided A={new:.12f} s PASS, encoded 10; C and D retain exact minimum")
    print("PASS F6: routing all original-graph origins cannot measure this transformation's verdict impact")


if __name__ == "__main__":
    main()
