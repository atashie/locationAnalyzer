"""F7: exact squared distance does not make T0's returned attachment exact."""
import sys
from fractions import Fraction as F
from pathlib import Path

root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root / "v2" / "scripts"))
sys.path.insert(0, str(root / "v2"))
import shapely
import t0_attachment_pilot as pilot


def main():
    x, y, d = 122.09, -122.08999999999999, 1e-6
    raw = pilot.raw_positions({0: shapely.LineString(((0., 0.), (d, d)))}, [0], x, y)
    t = (F(x)+F(y)) / (2*F(d))
    sq = pilot.exact_segment_sq(x, y, 0., 0., d, d)
    assert raw[0].t == 0. and raw[0].occurrence == (0, "v", 0)
    assert 0 < t < 1
    assert sq == (F(x)-t*F(d))**2 + (F(y)-t*F(d))**2
    assert sq < F(x)**2 + F(y)**2
    print(f"ACTUAL T0 raw t={raw[0].t}, occurrence={raw[0].occurrence}; exact t={float(t)!r} is interior")
    print(f"ACTUAL exact_segment_sq returns {type(sq).__name__} only, not t/position/occurrence/arclength")
    print("PASS F7: exact distance diagnostic is sound, but it does not certify the attachment pipeline")


if __name__ == "__main__":
    main()
