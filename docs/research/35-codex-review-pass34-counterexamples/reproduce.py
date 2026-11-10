"""Read-only pass-34 reproduction. Run from v2: python .review34/reproduce.py"""
import sys, pathlib, pickle, json, time, gc, csv
from collections import Counter
import numpy as np
import geopandas as gpd
import osmnx as ox
import shapely
from scipy.sparse.csgraph import dijkstra
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'spikes')]
from _common import GRID, GRAPH_CACHE, ACCEPTED_PLACES
from locfinder.places.categories import select_overture
from locfinder.traveltime.speeds import add_travel_times, symmetrise, access_speed_mps
from locfinder.traveltime.components import largest_component
from locfinder.traveltime.csr import graph_to_cost_time_csr
from locfinder.traveltime.arrival import arrival_with_selected_destination, arrival_seconds
from locfinder.traveltime.snap import EdgeIndex, _snap_network, cell_seconds_from_arrival
OUT = ROOT/'.review34'
def save(name, x):
    (OUT/name).write_text(json.dumps(x, indent=2, default=lambda v: v.item() if hasattr(v,'item') else str(v)), encoding='utf-8')
def classes(d):
    h=d.get('highway',[])
    return set(h if isinstance(h,(list,tuple)) else [h])
def edge(G,u,v):
    return min(G[u][v].values(),key=lambda d:d.get('cost',d['travel_time']))
def desc(d):
    return {k:d.get(k) for k in ['osmid','name','highway','length','travel_time','cost','access','foot','surface','tracktype','smoothness','access_restricted']}
X,Y=GRID.cell_centers_xy()
pt=shapely.Point(X[286,129],Y[286,129])
buildings=np.load(ROOT/'data/layers/own_triangle_buildings_per_cell.npy')
stored=np.load(ROOT/'data/layers/own_triangle_grocery_walk.npy')
sel=select_overture(gpd.read_parquet(ACCEPTED_PLACES).to_crs(GRID.crs),'grocery')
cent=sel.geometry.centroid
cache=OUT/'weighted.pickle'
if not cache.exists():
    print('loading graph',flush=True)
    G=ox.project_graph(ox.load_graphml(GRAPH_CACHE),to_crs=GRID.crs)
    add_travel_times(G,mode='walk')
    with cache.open('wb') as f: pickle.dump(G,f,pickle.HIGHEST_PROTOCOL)
    del G; gc.collect()
    print('cached weighted graph',flush=True)
variants={'baseline':set(),'old':set(),'no_track':{'track'},'no_track_path':{'track','path'},'no_path':{'path'},'no_footway':{'footway'},'no_service':{'service'},'no_footway_service':{'footway','service'},'no_all_four':{'track','path','footway','service'}}
summary=json.loads((OUT/'summary.json').read_text()) if (OUT/'summary.json').exists() else {}
base_nodes=None; base_pnodes=None; base_keep=None; base_dest=None
if 'baseline' in summary:
    b=np.load(OUT/'baseline_nodes.npz');base_nodes=set(b['nodes']);base_pnodes=b['pnodes'];base_keep=b['keep'];base_dest=set(base_pnodes[base_keep])
def journey(G,idx,eidx,T,D,pred,sources,gi=None,point=pt):
    if gi is None: gi=int(eidx.tree.nearest(point))
    # Force an individual physical edge while keeping production branch arithmetic.
    ei=EdgeIndex(shapely.STRtree([eidx.geoms[gi]]),eidx.geoms[[gi]],*[getattr(eidx,k)[[gi]] for k in ['start_idx','end_idx','fwd_time','rev_time','fwd_cost','rev_cost']])
    snap=_snap_network(ei,T,np.array([point.x]),np.array([point.y]),node_cost=D)
    chosen=int(snap.chosen_idx[0]); rev=list(G.nodes())
    frac=float(shapely.line_locate_point(eidx.geoms[gi],point,normalized=True))
    s,e=int(eidx.start_idx[gi]),int(eidx.end_idx[gi])
    u,v=rev[s],rev[e]
    matched=edge(G,u,v) if G.has_edge(u,v) else edge(G,v,u)
    partial=float(snap.network[0]-T[chosen]) if chosen>=0 else float('inf')
    route=[]; node=chosen
    while node>=0 and pred[node]!=-9999:
        p=int(pred[node]); d=edge(G,rev[node],rev[p]); route.append(dict(u=rev[node],v=rev[p],**desc(d)));node=p
    streets=Counter()
    for d in route: streets[str(d['name'] or d['highway'])]+=d['length']
    acc=float(snap.access_m[0]); net=float(snap.network[0]); dest=int(sources[chosen]) if chosen>=0 else -1
    return dict(gi=gi,access_m=acc,access_s=acc/1.26,network_s=net,total_s=net+acc/1.26,model_length_m=acc+1.4*net,partial_s=partial,partial_m=partial*1.4,matched=desc(matched),fraction=frac,chosen=rev[chosen] if chosen>=0 else None,destination_node=rev[dest] if dest>=0 else None,destination_names=[str(sel.iloc[i]['names']) for i,n in enumerate(pnodes) if dest>=0 and n==rev[dest] and keep[i]],streets_m=dict(streets),route=route)
for label,drop in variants.items():
    if label in summary: continue
    t=time.perf_counter()
    with cache.open('rb') as f:G=pickle.load(f)
    doomed=[(u,v,k) for u,v,k,d in G.edges(keys=True,data=True) if classes(d)&drop]
    G.remove_edges_from(doomed)
    if label=='old':
        missing=[(v,u,dict(d)) for u,v,d in G.edges(data=True) if not G.has_edge(v,u)]
        for v,u,d in missing:G.add_edge(v,u,**d)
        del missing
    else:symmetrise(G)
    pre_edges=G.number_of_edges()
    isolated=[n for n,d in G.degree() if d==0];G.remove_nodes_from(isolated)
    G,comp=largest_component(G,max_dropped_share=1.0)
    C,W,idx=graph_to_cost_time_csr(G)
    pnodes,pdists=ox.nearest_nodes(G,cent.x.to_numpy(),cent.y.to_numpy(),return_dist=True)
    pnodes=np.asarray(pnodes); keep=np.asarray(pdists)<=300
    dest=sorted({idx[n] for n,k in zip(pnodes,keep) if k})
    T,selected=arrival_with_selected_destination(C,W,dest_idx=dest)
    D,pred,sources=dijkstra(C.T.tocsr(),directed=True,indices=np.array(dest),min_only=True,return_predecessors=True)
    eidx=EdgeIndex.from_graph(G,idx)
    seconds=cell_seconds_from_arrival(eidx,T,X,Y,mode='walk',max_access_m=200,node_cost=D,cutoff_s=7200)
    np.save(OUT/(label+'.npy'),seconds)
    np.savez_compressed(OUT/(label+'_nodes.npz'),nodes=np.array(list(G.nodes())),T=T,D=D,pred=pred,sources=sources,pnodes=pnodes,keep=keep)
    j=journey(G,idx,eidx,T,D,pred,sources)
    save(label+'_journey.json',j)
    m=dict(nodes=G.number_of_nodes(),edges=G.number_of_edges(),pre_prune_edges=pre_edges,removed_weighted_edges=len(doomed),isolated=len(isolated),components=comp.__dict__,destination_nodes=len(dest),accepted_places=int(keep.sum()),unknown=int((~np.isfinite(seconds)).sum()),journey={k:v for k,v in j.items() if k!='route'})
    if label=='baseline':
        base_nodes=set(G);base_pnodes=pnodes.copy();base_keep=keep.copy();base_dest={n for n,k in zip(pnodes,keep) if k}
        # Accurate nearby count and all candidate forced snaps.
        nearby=[]
        for gi in np.atleast_1d(eidx.tree.query(pt.buffer(300))):
            distance=float(pt.distance(eidx.geoms[gi]))
            if distance<=300: nearby.append(journey(G,idx,eidx,T,D,pred,sources,int(gi)))
        save('nearby_routes.json',sorted(nearby,key=lambda a:a['access_m']))
    else:
        m.update(nodes_lost_from_baseline=len(base_nodes-set(G)),dest_nodes_lost=sorted(base_dest-set(pnodes[keep])),dest_nodes_gained=sorted(set(pnodes[keep])-base_dest),places_resnapped=int((pnodes!=base_pnodes).sum()),places_keep_changed=int((keep!=base_keep).sum()))
    if label in ('baseline','old'):
        cur=seconds.astype(np.float32);both=np.isfinite(cur)&np.isfinite(stored)
        dif=np.zeros(cur.shape);dif[both]=cur[both].astype(float)-stored[both].astype(float)
        m['vs_stored']=dict(differing=int((cur!=stored).sum()),finiteness_changes=int((np.isfinite(cur)!=np.isfinite(stored)).sum()),max_abs_s=float(abs(dif).max()),max_cell=list(np.unravel_index(abs(dif).argmax(),dif.shape)),lost15=np.argwhere((stored<=900)&(cur>900)).tolist())
        if label=='baseline':
            for rr,cc in m['vs_stored']['lost15']+ [m['vs_stored']['max_cell']]:
                save(f'baseline_cell_{rr}_{cc}.json',journey(G,idx,eidx,T,D,pred,sources,point=shapely.Point(X[rr,cc],Y[rr,cc])))
        else:
            baseline=np.load(OUT/'baseline.npy').astype(np.float32)
            for rr,cc in np.argwhere((stored<=900)&(baseline>900)):
                save(f'old_cell_{rr}_{cc}.json',journey(G,idx,eidx,T,D,pred,sources,point=shapely.Point(X[rr,cc],Y[rr,cc])))
    m['elapsed_s']=time.perf_counter()-t; summary[label]=m;save('summary.json',summary)
    print(label,json.dumps({k:v for k,v in m.items() if k!='journey'},default=str),flush=True)
    del G,C,W,idx,eidx,T,D,pred,sources,seconds;gc.collect()
print('DONE',flush=True)
