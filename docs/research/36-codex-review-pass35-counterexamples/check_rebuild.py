"""Independently rebuild current and historical walk surfaces; no production writes."""
import csv,gc,json,sys,time
from collections import Counter
from pathlib import Path
V2=Path(__file__).resolve().parents[1];OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(V2),str(V2/'spikes')]
import numpy as np
import geopandas as gpd
import networkx as nx
import osmnx as ox
import _common as common
from locfinder.traveltime import access,speeds
from locfinder.traveltime.components import largest_component
from locfinder.traveltime.csr import graph_to_cost_time_csr
from locfinder.traveltime.snap import EdgeIndex,cell_selected_destination,cell_seconds_from_arrival
from locfinder.traveltime.arrival import arrival_with_selected_destination,arrival_seconds
from locfinder.traveltime.layer import build_layer_surface
from locfinder.places.categories import select_overture

t=time.perf_counter();print('LOADING',flush=True)
G=common.load_roads_graph();print('LOADED',time.perf_counter()-t,flush=True)
tagged=[d for *_,d in G.edges(data=True) if 'vehicle' in d]
for mode in ['drive','bike','walk']:
    allc=Counter();usable=Counter()
    for d in tagged:
        old=access.classify_access({k:v for k,v in d.items() if k!='vehicle'},mode);new=access.classify_access(d,mode)
        if old!=new:
            allc[f'{old} -> {new}']+=1
            if speeds.highway_allowed(d,mode):usable[f'{old} -> {new}']+=1
    print('VEHICLE',mode,dict(allc),dict(usable),flush=True)
print('TAGGED',len(tagged),dict(Counter(str(d['vehicle']) for d in tagged)),flush=True)
G=ox.project_graph(G,to_crs=common.GRID.crs);speeds.add_travel_times(G,mode='walk')
# For this extraction, deleting surface/vehicle on the already simplified graph
# cannot change topology. Assert all policy inputs/weights remain identical.
unchanged=all(speeds.classify_access(d,'walk')==speeds.classify_access({k:v for k,v in d.items() if k not in ['surface','vehicle']},'walk') for *_,d in G.edges(data=True))
assert unchanged
places=select_overture(gpd.read_parquet(common.ACCEPTED_PLACES).to_crs(common.GRID.crs),'grocery');cent=places.geometry.centroid

def run(label,graph):
    graph.remove_nodes_from([n for n,d in graph.degree() if d==0]);graph,comp=largest_component(graph)
    C,T,index=graph_to_cost_time_csr(graph)
    ns,ds=ox.nearest_nodes(graph,cent.x.to_numpy(),cent.y.to_numpy(),return_dist=True)
    dest=sorted({index[n] for n,d in zip(ns,ds) if d<=300.})
    ei=EdgeIndex.from_graph(graph,index)
    surf=build_layer_surface(graph,(C,T),index,common.GRID,dest_idx=dest,mode='walk',target='grocery',engine='own-graph',cutoff_min=120.,max_access_m=200.,edge_index=ei,places_selected=len(places))
    directory=common.LAYERS if label=='current' else common.LAYERS/'prerebuild-2026-11-10'
    s=np.load(directory/'own_triangle_grocery_walk.npy');r=np.load(directory/'own_triangle_grocery_walk_reason.npy')
    print('REBUILD',label,dict(seconds_diff=int((s!=surf.seconds.astype(np.float32)).sum()),reason_diff=int((r!=surf.reason).sum()),nodes=len(graph),scc=nx.number_strongly_connected_components(graph),destinations=len(dest)),flush=True)
    assert np.array_equal(s,surf.seconds.astype(np.float32)) and np.array_equal(r,surf.reason)
    if label=='current':
        lower=np.load(directory/'own_triangle_grocery_walk_min_possible_s.npy')
        assert np.array_equal(lower,surf.min_possible_s)
        print('LOWER_BOUND_IDENTICAL',flush=True)
        times,selected=arrival_with_selected_destination(C,T,dest_idx=dest);cost=arrival_seconds(C,dest_idx=dest)
        nodes=list(graph.nodes()); rev={n:i for i,n in enumerate(nodes)}
        xs,ys=common.GRID.cell_centers_xy()
        shops=places.to_crs('EPSG:4326')
        for sheet in (V2.parent/'docs/experiments/audit').glob('triangle*-with-destinations.csv'):
            rows=list(csv.DictReader(sheet.open(encoding='utf-8-sig')));ii=[int(r['row']) for r in rows];jj=[int(r['col']) for r in rows]
            chosen=cell_selected_destination(ei,times,xs[ii,jj],ys[ii,jj],mode='walk',max_access_m=200.,selected=selected,node_cost=cost,cutoff_s=7200.)
            mismatches=[]
            for row,idx in zip(rows,chosen):
                if idx<0:continue
                labels=[p['primary'] for p in places.iloc[[pos for pos,(n,d) in enumerate(zip(ns,ds)) if n==nodes[idx] and d<=300]]['names']]
                if row['predicted_destination'] not in labels:mismatches.append([row['journey_id'],row['predicted_destination'],labels])
            print('DESTINATIONS',sheet.name,'mismatches',mismatches,flush=True)
    return surf.seconds.astype(np.float32)

# Historical symmetrise adds only where no opposing edge of any road exists.
missing=[(v,u,dict(d)) for u,v,d in G.edges(data=True) if not G.has_edge(v,u)]
for v,u,d in missing:G.add_edge(v,u,**d)
del missing
old=run('historical',G)
gc.collect()
speeds.symmetrise(G)
current=run('current',G)
np.save(OUT/'rebuilt_historical.npy',old);np.save(OUT/'rebuilt_current.npy',current)
print('DONE',time.perf_counter()-t,flush=True)
