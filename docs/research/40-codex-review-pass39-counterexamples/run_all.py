"""Run pass 39's reproducible attacks/checks; save only this directory's RESULTS.txt.

PASS means the assertions of the review program hold, including when they establish a defect.
No source mutation or repository temporary directories. Runtime is roughly one minute.
"""
from common import ROOT, HERE
import os
import subprocess
import sys

commands = [[sys.executable, '-B', str(HERE / name)] for name in (
    'f01_and_f08_contract.py', 'f03_mutation_validity.py', 'f04_identity_and_answers.py',
    'f05_sentinel.py', 'verify_f06_f07.py', 'verify_numbers.py', 'verify_mutants.py')]
commands += [[sys.executable, '-B', str(ROOT / 'docs/research/39-codex-review-pass38-counterexamples'
                                       / 'verify_surviving_claims.py')],
             [sys.executable, '-B', '-m', 'pytest', str(ROOT / 'v2/tests/test_exact_geometry.py'),
              '-q', '-p', 'no:cacheprovider']]
logs = []
failed = False
for command in commands:
    proc = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, env=os.environ | {'PYTHONDONTWRITEBYTECODE': '1'})
    label = command[2:]
    logs.append(f'=== {label}: exit {proc.returncode} ===\n{proc.stdout}')
    print(label, 'PASS' if proc.returncode == 0 else 'FAIL', flush=True)
    failed |= proc.returncode != 0
(HERE / 'RESULTS.txt').write_text('\n'.join(logs), encoding='utf-8', newline='\n')
raise SystemExit(int(failed))
