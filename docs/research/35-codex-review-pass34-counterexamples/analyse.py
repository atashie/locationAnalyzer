"""Summarise saved surfaces without loading a graph. Run after reproduce.py and controlled.py."""
import pathlib,json,csv,sys,importlib.util
from collections import Counter
import numpy as np
P=pathlib.Path(__file__).resolve().parent;V=P.parent
sys.path[:0]=[str(V),str(V/'spikes')]
from _common import GRID
B=np.load(P/'baseline.npy');weights=np.load(V/'data/layers/own_triangle_buildings_per_cell.npy')
out={}
for f in P.glob('*.npy'):
    if f.stem in ('baseline','old') or f.stem.endswith('_reason'):continue
    s=np.load(f)
    if s.shape!=B.shape:continue
    v={}
    for t in (600,900,1500,2700):
        base=B<=t;lost=base&~(s<=t);gain=~base&(s<=t)
        v[str(t)]=dict(pass_cells=int(base.sum()),lost_cells=int(lost.sum()),lost_buildings=int(weights[lost].sum()),lost_share=float(lost.sum()/base.sum()),lost_building_share=float(weights[lost].sum()/weights[base].sum()),gained_cells=int(gain.sum()),gained_buildings=int(weights[gain].sum()))
        if t in (600,900):
            for name,mask in [('band_pass',base&(B>=t-90)),('band_both',abs(B-t)<=90),('building_cells_pass',base&(weights>0)),('building_cells_band',base&(B>=t-90)&(weights>0))]:
                n=int(mask.sum());v[str(t)][name]=dict(n=n,lost=int((lost&mask).sum()),share=float((lost&mask).sum()/n) if n else None,buildings=int(weights[mask].sum()),lost_buildings=int(weights[mask&lost].sum()))
    v['finite_to_missing']=int((np.isfinite(B)&~np.isfinite(s)).sum());v['missing_to_finite']=int((~np.isfinite(B)&np.isfinite(s)).sum());out[f.stem]=v
if (P/'no_track_path.npy').exists():
    s=np.load(P/'no_track_path.npy');rows=list(csv.DictReader((V.parent/'docs/experiments/audit/triangle-grocery-walk-chapelhill.csv').open(encoding='utf-8-sig')))
    changes=[]
    for r in rows:
        rc=int(r['row']),int(r['col']);a,b=B[rc],s[rc]
        if not np.isfinite(b) or abs(b-a)>=.5:changes.append(dict(id=r['journey_id'],baseline=float(a),without=float(b),lost10=bool(a<=600 and b>600),lost15=bool(a<=900 and b>900)))
    out['sheet_changes']=changes
if (P/'no_track_path_control_reason.npy').exists():
    u=np.load(P/'no_track_path_unpruned.npy');s=np.load(P/'no_track_path.npy')
    out['pruning_effect']={str(t):dict(lost_pruned=int(((B<=t)&(s>t)).sum()),lost_unpruned=int(((B<=t)&(u>t)).sum()),lost_only_with_pruning=int(((B<=t)&(s>t)&(u<=t)).sum()),lost_only_without_pruning=int(((B<=t)&(u>t)&(s<=t)).sum())) for t in (600,900,1500,2700)}
    r=np.load(P/'no_track_path_control_reason.npy');br=np.load(V/'data/layers/own_triangle_grocery_walk_reason.npy')
    out['reason_transitions']={f'{a}->{b}':int(((br==a)&(r==b)).sum()) for a in range(4) for b in range(4)}
# Demonstrate exactly which source rasters the current browser exporter sees.
spec=importlib.util.spec_from_file_location('review34_export',V/'spikes/g3-render/export_layers.py');mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
out['browser_sources']=[str(l.path.relative_to(V)) for l in mod.select_layers(mod.discover_real_layers())]
from locfinder.traveltime.access import access_penalty_s
out['class_penalties']={h:access_penalty_s({'highway':h},'walk') for h in ['track','path','footway','service']}
(P/'metrics.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out,indent=2))
