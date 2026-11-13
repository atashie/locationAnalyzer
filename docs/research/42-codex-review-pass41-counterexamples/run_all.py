"""Run A-F in order; persist only final evidence beside this script. No temp/cache directories."""
import sys
sys.dont_write_bytecode = True
import contextlib
import io
import json
import platform
from pathlib import Path
import review

here = Path(__file__).resolve().parent
results = {'python': sys.version, 'platform': platform.platform()}
output = io.StringIO()
with contextlib.redirect_stdout(output):
    print('Python:', sys.version)
    print('Platform:', platform.platform())
    for name, run in review.SECTIONS.items():
        print('\n=== CLAIM', name, '===')
        results[name] = run()
(here / 'RESULTS.txt').write_text(output.getvalue(), encoding='utf-8')
(here / 'results.json').write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
print(output.getvalue())
print('All assertions passed; wrote RESULTS.txt and results.json.')
