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
allrows=[]
for sheet in ['triangle-grocery-walk-chapelhill','triangle-grocery-walk']:
    rows=list(csv.DictReader(open('../docs/experiments/audit/'+sheet+'-with-destinations.csv',encoding='utf-8')))
    allrows+=rows
    ids=[(int(x['row']),int(x['col'])) for x in rows]; xx=np.array([xs[a,b] for a,b in ids]); yy=np.array([ys[a,b] for a,b in ids])
    secs=r.cell_seconds_from_arrival(e,T,xx,yy,mode='walk',max_access_m=200.,cutoff_s=7200.,node_cost=nc)
    chosen=r.cell_selected_destination(e,T,xx,yy,mode='walk',max_access_m=200.,cutoff_s=7200.,node_cost=nc,selected=selected)
    point=shapely.points(xx,yy); matches,dists=e.tree.query_nearest(point,all_matches=True,return_distance=True)
    counts=collections.Counter(matches[0].tolist())
    print(sheet,'counts:',dict(collections.Counter(x['predicted_destination'] for x in rows)),'distinct coordinates:',len({(x['predicted_destination_lat'],x['predicted_destination_lon']) for x in rows}), 'equal-nearest:', {rows[i]['journey_id']:n for i,n in counts.items() if n>1},flush=True)
    qx,qy=r.Transformer.from_crs('EPSG:4326',r.GRID.crs,always_xy=True).transform([float(x['query_lon']) for x in rows],[float(x['query_lat']) for x in rows])
    rounded=r.cell_seconds_from_arrival(e,T,qx,qy,mode='walk',max_access_m=200.,cutoff_s=7200.,node_cost=nc)
    print('rounding max delta seconds:',max(abs(rounded[np.isfinite(rounded)]-secs[np.isfinite(rounded)])), 'rows > .05 vs CSV:',[(rows[i]['journey_id'],float(rounded[i])-float(row['seconds'])) for i,row in enumerate(rows) if row['seconds'] and abs(rounded[i]-float(row['seconds']))>.05],flush=True)
    inverse={v:k for k,v in idx.items()}
    print('destination snap offsets:',[(rows[i]['journey_id'],round(float(np.hypot(G.nodes[inverse[int(node)]]['x']-s['sel'].geometry.iloc[s['node_to_places'][int(node)][0]].centroid.x,G.nodes[inverse[int(node)]]['y']-s['sel'].geometry.iloc[s['node_to_places'][int(node)][0]].centroid.y)),2)) for i,node in enumerate(chosen) if node>=0],flush=True)
    if 'chapelhill' in sheet: chapel=(xx,yy,chosen,rows)
print('grocery basic_category:',s['sel']['basic_category'].value_counts().to_dict(),'taxonomy primary:',s['sel']['taxonomy'].apply(lambda t:t.get('primary')).value_counts().to_dict(),flush=True)
# A changed access configuration can pass every sampled comparison.
alt=r.cell_seconds_from_arrival(e,T,xs,ys,mode='walk',max_access_m=201.,cutoff_s=7200.,node_cost=nc)
print('ACCESS201: sampled cells changed:',sum(alt[int(z['row']),int(z['col'])]!=pub[int(z['row']),int(z['col'])] for z in allrows),'full cells changed:',np.count_nonzero(alt!=pub),flush=True)
# Reverse destination order: check if any sampled selected identities move on equal cost.
Trev,Srev=r.arrival_with_selected_destination(cost,tm,dest_idx=dest[::-1])
xx,yy,chosen,rows=chapel
revchosen=r.cell_selected_destination(e,Trev,xx,yy,mode='walk',max_access_m=200.,cutoff_s=7200.,node_cost=nc,selected=Srev)
print('REVERSE SOURCE ORDER: chapel identities changed:',np.count_nonzero(revchosen!=chosen), 'node identities changed:',np.count_nonzero(Srev!=selected),flush=True)
# Alter one destination node unused by either sheet, retaining the counts used by the gate.
used=set(selected[_snap_network(e,T,np.array([xs[int(z['row']),int(z['col'])] for z in allrows]),np.array([ys[int(z['row']),int(z['col'])] for z in allrows]),node_cost=nc).chosen_idx].tolist())
for old in dest[::-1]:
    if old in used: continue
    neighbours=cost.indices[cost.indptr[old]:cost.indptr[old+1]]
    candidates=[int(z) for z in neighbours if z not in dest]
    if not candidates: continue
    new=candidates[0]; alt_dest=sorted((set(dest)-{old})|{new})
    Ta,Sa=r.arrival_with_selected_destination(cost,tm,dest_idx=alt_dest)
    na=r.arrival_seconds(cost,dest_idx=alt_dest)
    ax=np.array([xs[int(z['row']),int(z['col'])] for z in allrows]); ay=np.array([ys[int(z['row']),int(z['col'])] for z in allrows])
    asecs=r.cell_seconds_from_arrival(e,Ta,ax,ay,mode='walk',max_access_m=200.,cutoff_s=7200.,node_cost=na)
    expect=np.array([s['raster'][int(z['row']),int(z['col'])] for z in allrows])
    print('CHANGED DESTINATION SET:',old,'->',new, 'count:',len(alt_dest),'sample match:',np.array_equal(asecs.astype(np.float32),expect),'node times changed:',np.count_nonzero(Ta!=T),flush=True)
    break
# Reuse the loaded/prepared graph for write-safety and sheet-validation counterexamples.
r.ox.load_graphml=lambda *a,**k:G
r.ox.project_graph=lambda *a,**k:G
r.add_travel_times=lambda *a,**k:G
r.symmetrise=lambda *a,**k:G
r.largest_component=lambda *a,**k:(G,s['comp'])
r.graph_to_cost_time_csr=lambda *a,**k:(cost,tm,idx)
r.EdgeIndex.from_graph=lambda *a,**k:e
# Existing walked output: default path is silently overwritten from bare input.
base=Path('.review33/overwrite.csv'); base.write_bytes(Path('../docs/experiments/audit/triangle-grocery-walk-chapelhill.csv').read_bytes())
out=base.with_name('overwrite-with-destinations.csv'); out.write_text('walked_seconds,notes\n999,owner observation\n',encoding='utf-8')
sys.argv=['recover',str(base)]; result=r.main(); print('OVERWRITE: rc',result,'owner observation retained:', 'owner observation' in out.read_text(),flush=True)
# A mismatch still writes the output.
def shifted(*a,**k):
    v=r.cell_seconds_original(*a,**k); return v+1.
r.cell_seconds_original=r.cell_seconds_from_arrival; r.cell_seconds_from_arrival=shifted
sys.argv=['recover',str(base),'--out','.review33/mismatch.csv']; result=r.main(); print('MISMATCH: rc',result,'output exists:',Path('.review33/mismatch.csv').exists(),flush=True)
r.cell_seconds_from_arrival=r.cell_seconds_original
# The printed seconds column is never checked.
rr=list(csv.DictReader(base.open(encoding='utf-8'))); rr[0]['seconds']='1.0'; rr[0]['outcome_10min']='FAIL'
with Path('.review33/altered-sheet.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(rr[0])); w.writeheader(); w.writerows(rr)
sys.argv=['recover','.review33/altered-sheet.csv','--out','.review33/altered-output.csv']; result=r.main(); bad=list(csv.DictReader(open('.review33/altered-output.csv')))[0]; print('ALTERED SHEET: rc',result, 'seconds',bad['seconds'],'outcome_10min',bad['outcome_10min'],'recheck',bad['predicted_seconds_recheck'],'match',bad['recheck_matches_sheet'],flush=True)
