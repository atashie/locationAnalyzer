from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import pytest
import runpy
import locfinder.traveltime.snap as snap
source = Path(snap.__file__).read_text(encoding='utf-8')
kind = sys.argv[1]
if kind == 'time':
    source = source.replace('chosen = np.where(take_end, e_idx, s_idx)', 'chosen = np.where(time_end <= time_start, e_idx, s_idx)')
else:
    source = source.replace('    if cutoff_s is not None:\n        total = np.where(total > float(cutoff_s), np.inf, total)\n\n    sel =', '    if False:\n        total = np.where(total > float(cutoff_s), np.inf, total)\n\n    sel =')
exec(compile(source, snap.__file__, 'exec'), snap.__dict__)
t = runpy.run_path('tests/test_selected_destination.py')
g = t['snap_fixture']()
if kind == 'time':
    for data in g['S']['E'].values(): data['cost'] = 1000.
index, dest, T, selected, nc, eidx = t['snap_inputs'](g)
x = np.array([90. if kind == 'time' else 10.]); y=np.array([0.])
kw=dict(mode='walk', max_access_m=200., node_cost=nc, cutoff_s=None if kind=='time' else 15.)
print('mutation:', kind, 'seconds:', snap.cell_seconds_from_arrival(eidx,T,x,y,**kw), 'selected:',snap.cell_selected_destination(eidx,T,x,y,selected=selected,**kw), 'node IDs:',index, flush=True)
raise SystemExit(pytest.main(['tests/test_selected_destination.py','-o','addopts=','-q','-p','no:cacheprovider']))
