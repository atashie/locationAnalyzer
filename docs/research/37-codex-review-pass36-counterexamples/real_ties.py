from pathlib import Path
import sys, time, json, collections
import numpy as np
import shapely
import osmnx as ox
V2=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(V2),str(V2/'scripts')]
import t0_attachment_pilot as p
print('Loading cached graph read-only',flush=True)
G=ox.load_graphml(V2/'data/triangle/roads.graphml')
G=ox.project_graph(G,to_crs=p.GRID.crs)
G=p.add_travel_times(G,mode='walk');G=p.symmetrise(G)
G.remove_nodes_from([n for n,d in G.degree() if d==0])
G,_=p.largest_component(G)
eidx=p.EdgeIndex.from_graph(G,{n:i for i,n in enumerate(G.nodes())})
print('Prepared graph; reading structures',flush=True)
ids,pts,_=p.structure_population(p.ACCEPTED_BUILDINGS,p.GRID)
hits=[];t=time.monotonic();flagged_candidates=0;true_tie_candidates=0
for i,(xy,sid) in enumerate(zip(pts,ids)):
    # Avoid exact arithmetic until there is actually a C drop.
    cheap=p.measure_point(eidx.geoms,eidx.tree,*xy,200.,want_exact=False)
    if not cheap['same_set']['A_vs_C']:
        r=p.measure_point(eidx.geoms,eidx.tree,*xy,200.)
        if r['c_drops_a_genuine_exact_tie']:
            raw=p.raw_positions(eidx.geoms,range(0),*xy) # filled below using same window
            pt=shapely.Point(*xy)
            window=eidx.tree.query(pt.buffer(r['tree_min_m']+p.ATTACH_TIE_M+1e-6))
            raw=p.raw_positions(eidx.geoms,window,*xy)
            for q in raw:
                if q.residual<=r['global_min_m']+p.ATTACH_TIE_M:
                    q.exact_sq=p.exact_segment_sq(*xy,*p._seg_ends(eidx.geoms,q))
            ckeys={q.occurrence for q in r['_sets']['C']}
            for q in r['_sets']['A']:
                if q.occurrence in ckeys:continue
                bucket=[z for z in raw if z.record==q.record and z.exact_sq is not None]
                if q.exact_sq!=min(z.exact_sq for z in bucket):continue
                peers={z.occurrence for z in bucket if z.exact_sq==q.exact_sq}
                flagged_candidates+=1;true_tie_candidates+=len(peers)>=2
                hit={'id':str(sid),'point':xy.tolist(),'record':int(q.record),'reported_tie':True,
                     'distinct_exact_minimum_occurrences':len(peers),
                     'geometry':eidx.geoms[q.record].wkt,
                     'A':[(z.seg,z.residual,str(z.exact_sq)) for z in r['_sets']['A']],
                     'C':[(z.seg,z.residual,str(z.exact_sq)) for z in r['_sets']['C']]}
                hits.append(hit);print('HIT',json.dumps(hit),flush=True)
    if i and i%100000==0:print('Scanned',i,'in',round(time.monotonic()-t,1),'seconds',flush=True)
result={'points':len(pts),'reported_tie_candidates':flagged_candidates,'true_tie_candidates':true_tie_candidates,'hits':hits}
(Path(__file__).parent/'real_ties_results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('RESULT',json.dumps(result),flush=True)
