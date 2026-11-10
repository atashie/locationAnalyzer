from pathlib import Path
import sys, csv, collections, json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import shapely
import scripts.recover_audit_destinations as r
src=Path(r.__file__).read_text(encoding='utf-8')
src=src.replace('    return 0\n', "    globals()['_state'] = locals().copy()\n    return 0\n")
exec(compile(src,r.__file__,'exec'),r.__dict__)
sys.argv=['recover','../docs/experiments/audit/triangle-grocery-walk.csv','--out','.review33/metro.csv']
assert r.main()==0
s=r._state
G=s['G']; cost=s['cost_csr']; tm=s['time_csr']; idx=s['index']; e=s['eidx']; dest=s['dest_idx']; selected=s['selected']; nc=s['node_cost']
from locfinder.traveltime.snap import _snap_network, cell_arrival_with_provenance
from locfinder import status as st
T, selected=r.arrival_with_selected_destination(cost,tm,dest_idx=dest)
xs,ys=r.GRID.cell_centers_xy()
pub,reason,lower=cell_arrival_with_provenance(e,T,xs,ys,mode='walk',max_access_m=200.,horizon_s=7200.,node_reason=st.node_reasons(T,st.ENGINES['own-graph'],search_bounded=False),node_cost=nc)
rec=r.cell_seconds_from_arrival(e,s['T'],xs,ys,mode='walk',max_access_m=200.,cutoff_s=7200.,node_cost=nc)
print('FULL GRID: provenance vs recovery bounded T:', np.array_equal(pub,rec), 'vs committed float32:',np.array_equal(pub.astype(np.float32),s['raster']),flush=True)
stored=s['raster']; rebuilt=pub.astype(np.float32)
diff=rebuilt!=stored
print('FULL DIFFERENCES:',np.count_nonzero(diff),'finiteness:',np.count_nonzero(np.isfinite(rebuilt)!=np.isfinite(stored)),flush=True)
for a,b in np.argwhere(diff)[:30]:
    print('CELL',int(a),int(b),'stored',float(stored[a,b]),'rebuilt',float(rebuilt[a,b]),'delta',float(rebuilt[a,b]-stored[a,b]),flush=True)
np.savez_compressed('.review33/full-arrays.npz',stored=stored,rebuilt=rebuilt,seconds=pub,reason=reason,T=T,selected=selected,node_cost=nc,start_idx=e.start_idx,end_idx=e.end_idx)
# Reverse the graph's node insertion order while retaining the same edges and weights.
n=cost.shape[0]; perm=np.arange(n)[::-1]
cost_rev=cost[perm][:,perm].tocsr(); time_rev=tm[perm][:,perm].tocsr()
Trev,Srev=r.arrival_with_selected_destination(cost_rev,time_rev,dest_idx=sorted(n-1-np.asarray(dest)))
Torig=Trev[::-1]; Sorig=np.where(Srev[::-1]>=0,n-1-Srev[::-1],-1)
rows=list(csv.DictReader(open('../docs/experiments/audit/triangle-grocery-walk-chapelhill.csv')))
xx=np.array([xs[int(z['row']),int(z['col'])] for z in rows]); yy=np.array([ys[int(z['row']),int(z['col'])] for z in rows])
kw=dict(mode='walk',max_access_m=200.,cutoff_s=7200.,node_cost=nc)
a=r.cell_selected_destination(e,T,xx,yy,selected=selected,**kw)
b=r.cell_selected_destination(e,Torig,xx,yy,selected=Sorig,**kw)
print('REVERSE NODE ORDER: node destinations changed',np.count_nonzero(Sorig!=selected),'sample identities changed',np.count_nonzero(a!=b),flush=True)
for i in np.flatnonzero(a!=b):print('changed row',rows[i]['journey_id'],int(a[i]),int(b[i]),flush=True)
# Record sample identity and exact node-level provenance at every discrepant cell.
inverse={v:k for k,v in idx.items()}
for a,b in np.argwhere(diff)[:5]:
    sn=_snap_network(e,T,np.array([xs[a,b]]),np.array([ys[a,b]]),node_cost=nc)
    node=int(selected[sn.chosen_idx[0]]) if sn.chosen_idx[0]>=0 else -1
    places=[r.place_label(s['sel']['names'].iloc[j]) for j in s['node_to_places'].get(node,[])]
    print('DIFFERENCE destination',int(a),int(b),node,places,flush=True)
