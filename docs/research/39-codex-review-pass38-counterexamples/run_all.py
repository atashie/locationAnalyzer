"""Run all review checks. PASS means the claimed counterexample was reproduced.

No implementation files are edited. The original mutation harness was run separately
and restores its source; this runner uses the isolated, in-memory mutations instead.
"""
from common import ROOT
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
programs = [
    'f01_caps_and_band.py', 'f02_exact_prefixes.py', 'f03_mutation_coverage.py',
    'f04_adoption_blind_spots.py', 'f06_graph_guard.py', 'f07_artifact_comparison.py',
    'f08_zero_length_contract.py', 'verify_surviving_claims.py', 'verify_real_witnesses.py',
]
logs = []
for program in programs:
    proc = subprocess.run([sys.executable, '-B', str(HERE / program)], cwd=ROOT,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    logs.append(f'=== {program}: exit {proc.returncode} ===\n{proc.stdout}')
    print(program, 'PASS' if proc.returncode == 0 else 'FAIL', flush=True)
    if proc.returncode:
        print(proc.stdout)
        raise SystemExit(proc.returncode)
for command in ([sys.executable, '-B', '-m', 'pytest', 'tests/test_exact_geometry.py',
                 '-q', '-p', 'no:cacheprovider'],
                [sys.executable, '-B', 'scripts/render_t0_results.py', '--check']):
    proc = subprocess.run(command, cwd=ROOT/'v2', stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True)
    logs.append(f'=== {command[3:]}: exit {proc.returncode} ===\n{proc.stdout}')
    print(command[3:], 'PASS' if proc.returncode == 0 else 'FAIL', flush=True)
    assert proc.returncode == 0, proc.stdout
(HERE/'RESULTS.txt').write_text('\n'.join(logs), encoding='utf-8', newline='\n')
print('Wrote RESULTS.txt')
