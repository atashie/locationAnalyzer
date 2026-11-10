"""Separate pruning/resnapping from class deletion; test candidate snaps to the same shop."""
exec((__import__('pathlib').Path(__file__).with_name('reproduce.py')).read_text().split('for label,drop in variants.items():')[0])
with cache.open('rb') as f:G=pickle.load(f)
symmetrise(G)
G=G.subgraph(base_nodes).copy()
G.remove_edges_from([(u,v,k) for u,v,k,d in G.edges(keys=True,data=True) if classes(d)&{'track','path'}])
pnodes=base_pnodes;keep=base_keep
for label,prune in [('no_track_path_unpruned',False),('no_track_path_control',True)]:
    if prune:
        G.remove_nodes_from([n for n,d in G.degree() if d==0])
        G,_=largest_component(G,max_dropped_share=1.)
    C,W,idx=graph_to_cost_time_csr(G)
    fixed=[idx[n] for n in base_dest if n in idx]
    T,_=arrival_with_selected_destination(C,W,dest_idx=fixed)
    D,pred,sources=dijkstra(C.T.tocsr(),directed=True,indices=np.array(fixed),min_only=True,return_predecessors=True)
    eidx=EdgeIndex.from_graph(G,idx)
    ss=_snap_network(eidx,T,X.ravel(),Y.ravel(),node_cost=D)
    seconds=ss.network+ss.access_m/1.26
    reason=np.zeros(seconds.shape,dtype=np.int8)
    reason[~np.isfinite(ss.network)]=3
    reason[np.isfinite(ss.network)&(seconds>7200)]=2
    reason[ss.access_m>200]=1
    seconds[reason!=0]=np.inf
    np.save(OUT/(label+'.npy'),seconds.reshape(X.shape))
    np.save(OUT/(label+'_reason.npy'),reason.reshape(X.shape))
    routes=[]
    for gi in eidx.tree.query(pt.buffer(200)):
        if pt.distance(eidx.geoms[gi])<=200:routes.append(journey(G,idx,eidx,T,D,pred,sources,int(gi)))
    save(label+'_nearby.json',sorted(routes,key=lambda r:r['access_m']))
    # Same destination as published: Hill's Family Asian Markets, OSM 2904797599.
    hill=idx[2904797599]
    T,_=arrival_with_selected_destination(C,W,dest_idx=[hill])
    D,pred,sources=dijkstra(C.T.tocsr(),directed=True,indices=np.array([hill]),min_only=True,return_predecessors=True)
    routes=[]
    for gi in eidx.tree.query(pt.buffer(200)):
        if pt.distance(eidx.geoms[gi])<=200:routes.append(journey(G,idx,eidx,T,D,pred,sources,int(gi)))
    save(label+'_hill_nearby.json',sorted(routes,key=lambda r:r['access_m']))
    print(label,Counter(reason),flush=True)
    del C,W,idx,T,D,pred,sources,eidx,ss;gc.collect()
print('DONE',flush=True)
