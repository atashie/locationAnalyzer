"""Verify soft-class use on the baseline paths of cells losing PASS; inspect exact snap geometry."""
exec((__import__('pathlib').Path(__file__).with_name('reproduce.py')).read_text().split('for label,drop in variants.items():')[0])
from locfinder.traveltime.snap import _canonical_geometry_key,_edge_geometry
with cache.open('rb') as f:G=pickle.load(f)
pair=[6814689349,6801677574]
save('reverse_edge_evidence.json',{str((u,v)):[desc(d) for d in (G.get_edge_data(u,v) or {}).values()] for u,v in [pair,pair[::-1]]})
symmetrise(G);G=G.subgraph(base_nodes).copy()
C,W,idx=graph_to_cost_time_csr(G)
b=np.load(OUT/'baseline_nodes.npz');T=b['T'];D=b['D'];pred=b['pred'];sources=b['sources'];pnodes=b['pnodes'];keep=b['keep'];rev=list(G)
assert np.array_equal(np.array(rev),b['nodes'])
dependency=np.zeros(len(rev),dtype=bool)
for n in np.argsort(D,kind='stable'):
    p=pred[n]
    if p!=-9999:dependency[n]=dependency[p] or bool(classes(edge(G,rev[n],rev[p]))&{'track','path'})
eidx=EdgeIndex.from_graph(G,idx)
base=np.load(OUT/'baseline.npy');s=np.load(OUT/'no_track_path.npy')
mask=(base<=2700)&(s>base)&((s>600)&(base<=600)|(s>900)&(base<=900)|(s>1500)&(base<=1500)|(s>2700)&(base<=2700))
rr,cc=np.where(mask)
snap=_snap_network(eidx,T,X[rr,cc],Y[rr,cc],node_cost=D)
gis=eidx.tree.nearest(shapely.points(X[rr,cc],Y[rr,cc]))
uses=[]
for i,gi in enumerate(gis):
    ch=int(snap.chosen_idx[i]);part=float(snap.network[i]-T[ch]);own=False
    if part>1e-8:
        st,en=int(eidx.start_idx[gi]),int(eidx.end_idx[gi]);u,v=(rev[st],rev[en]) if ch==en else (rev[en],rev[st])
        geomkey=_canonical_geometry_key(eidx.geoms[gi])
        candidates=[d for d in G[u][v].values() if _canonical_geometry_key(_edge_geometry(G,u,v,d))==geomkey]
        chosen=min(candidates,key=lambda d:d['cost']);own=bool(classes(chosen)&{'track','path'})
    uses.append(bool(dependency[ch] or own))
result={'lost_cells_checked':len(uses),'without_any_track_path_on_baseline_route':int((~np.array(uses)).sum())}
gi=int(eidx.tree.nearest(pt));st,en=int(eidx.start_idx[gi]),int(eidx.end_idx[gi]);u,v=rev[st],rev[en]
result['focus_geometry_length']=eidx.geoms[gi].length
result['focus_pair']=[u,v]
result['focus_parallel_edges']={str((a,b)):[dict(**desc(d),distance_to_cell=pt.distance(_edge_geometry(G,a,b,d)),same_geometry=_canonical_geometry_key(_edge_geometry(G,a,b,d))==_canonical_geometry_key(eidx.geoms[gi])) for d in G[a][b].values()] for a,b in [(u,v),(v,u)] if G.has_edge(a,b)}
save('route_checks.json',result);print(result,flush=True)
