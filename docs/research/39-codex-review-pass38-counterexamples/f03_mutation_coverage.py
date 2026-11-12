"""Run isolated mutations without modifying any implementation file."""
from common import ROOT, script
from fractions import Fraction
from types import ModuleType
import subprocess
import sys


def main():
    source = (ROOT / 'v2/locfinder/measure/exact.py').read_text(encoding='utf-8')
    harness = script('mutate_exact_geometry')
    _, old, new = next(m for m in harness.MUTATIONS if 'floored scaling' in m[0])
    assert source.count(old) == 1
    broken = ModuleType('broken_exact')
    exec(compile(source.replace(old, new), '<floored-mutant>', 'exec'), broken.__dict__)
    try:
        broken.rational_sqrt(Fraction(2))
    except NameError as error:
        print('advertised floored-scaling mutant:', type(error).__name__, str(error))
    else:
        raise AssertionError('expected the undefined scaled variable')

    if len(sys.argv) == 2:
        # Fresh subprocess: install one mutant in memory before pytest imports the test module.
        from locfinder.measure import exact
        variants = {
            'position': (
                'ay_f + t * (Fraction(by) - ay_f)', 'ay_f'),
            'destination': (
                'terms.append(_partial(seg_d, t_d))',
                'terms.append(_partial(seg_d, 1 - t_d))'),
            'floor_fixed': (old, new.replace('(scaled.numerator // scaled.denominator)',
                                            '((q / (u*u)).numerator // (q / (u*u)).denominator)')),
        }
        before, after = variants[sys.argv[1]]
        assert source.count(before) == 1
        exec(compile(source.replace(before, after), str(exact.__file__), 'exec'), exact.__dict__)
        import pytest
        result = pytest.main([str(ROOT / 'v2/tests/test_exact_geometry.py'), '-q',
                              '--tb=no', '-p', 'no:cacheprovider'])
        if sys.argv[1] == 'position':
            value = exact.exact_segment_sq(1.5, 2., 0., 0., 3., 4.)
            print('diagonal midpoint squared residual:', value, '(required 0)')
            assert value == 4 and result == 0
        elif sys.argv[1] == 'destination':
            value = exact.same_edge_fraction(((0., 0.), (10., 0.), (20., 0.)),
                                             0, Fraction(1, 2), 1, Fraction(1, 4))
            print('cross-segment fraction:', value, '(required 0.375)')
            assert value == .625 and result == 0
        else:
            assert result == 1, 'the repaired, executable mutant should be caught too'
        return

    for name in ('position', 'destination', 'floor_fixed'):
        proc = subprocess.run([sys.executable, '-B', __file__, name],
                              capture_output=True, text=True, cwd=ROOT)
        print(f'\n{name}: exit {proc.returncode}')
        print(proc.stdout)
        assert proc.returncode == 0, proc.stderr


if __name__ == '__main__':
    main()
