from pathlib import Path
import sys, time, json, collections
import numpy as np
import shapely
import osmnx as ox
V2=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(V2)); sys.path.insert(0,str(V2/'scripts'))
import t0_attachment_pilot as p
from locfinder.traveltime.snap import _canonical_geometry_key, _edge_geometry
t=time.monotonic()
print('Loading cached graph read-only',flush=True)
G=ox.load_graphml(V2/'data/triangle/roads.graphml')
print('Loaded',round(time.monotonic()-t,1),flush=True)
G=ox.project_graph(G,to_crs=p.GRID.crs)
G=p.add_travel_times(G,mode='walk');G=p.symmetrise(G)
G.remove_nodes_from([n for n,d in G.degree() if d==0])
G,comp=p.largest_component(G)
index={n:i for i,n in enumerate(G.nodes())}
eidx=p.EdgeIndex.from_graph(G,index)
print('Prepared',G.number_of_nodes(),G.number_of_edges(),len(eidx.geoms),round(time.monotonic()-t,1),flush=True)
groups=collections.defaultdict(list)
for u,v,k,d in G.edges(keys=True,data=True):
    geom=_edge_geometry(G,u,v,d)
    key=(min(index[u],index[v]),max(index[u],index[v]),_canonical_geometry_key(geom))
    groups[key].append((u,v,k,float(d['travel_time']),float(d.get('cost',d['travel_time'])),d.get('osmid')))
multi=[v for v in groups.values() if len(v)>2]
same_direction=sum(len(v)-len(set((e[0],e[1]) for e in v)) for v in groups.values())
weighted=[v for v in groups.values() if any(len({(e[3],e[4]) for e in v if e[:2]==uv})>1 for uv in {e[:2] for e in v})]
result={'nodes':len(G),'edges':G.number_of_edges(),'records':len(eidx.geoms),
        'groups_over_two':len(multi),'same_direction_excess':same_direction,
        'groups_with_same_direction_weight_alternatives':len(weighted),
        'example':multi[:3], 'weighted_examples':weighted[:3]}
result['only_one_finite_direction']=int(np.sum(np.isfinite(eidx.fwd_time)^np.isfinite(eidx.rev_time)))
result['zero_length_records']=int(np.sum(shapely.length(eidx.geoms)==0.))
result['self_loop_groups']=sum(k[0]==k[1] for k in groups)
spreads=[max(e[3] for e in v if e[:2]==uv)-min(e[3] for e in v if e[:2]==uv)
         for v in weighted for uv in {e[:2] for e in v}]
result['max_same_direction_time_spread']=max(spreads,default=0.)
result['same_direction_time_spreads_over_1e_9']=sum(x>1e-9 for x in spreads)
# Keep normal forward/reverse pairing, retain coincident parallel alternatives.
# Leave self-loop records alone to avoid making assumptions about their reverse pairing.
multiplicities=[1 if key[0]==key[1] else max(collections.Counter((e[0],e[1]) for e in v).values())
                for key,v in groups.items()]
expanded=np.repeat(eidx.geoms,multiplicities)
expanded_tree=shapely.STRtree(expanded)
result['open_edge_parallel_groups']=sum(m>1 for m in multiplicities)
result['records_after_preserving_open_parallel_alternatives']=len(expanded)
# Compare the pilot with all directed graph records on the frozen sample.
# This intentionally demonstrates design's literal per-edge-record multiplicity, not a new pairing rule.
all_geoms=[_edge_geometry(G,u,v,d) for u,v,k,d in G.edges(keys=True,data=True)]
tree=shapely.STRtree(all_geoms)
for stem in ['frame_b_51a59463','frame_c_7914e80a']:
    frame=p.read_frame(p.FRAMES/(stem+'.json'))
    n=0;oldmulti=0;newmulti=0;eligible_diff=0;parallel_changes=0;parallel_multi=0
    for xy in frame.points:
        a=p.measure_point(eidx.geoms,eidx.tree,*xy,200.)
        b=p.measure_point(all_geoms,tree,*xy,200.)
        c=p.measure_point(expanded,expanded_tree,*xy,200.)
        n+=a['counts']!=b['counts']
        oldmulti+=a['counts']['A']>1;newmulti+=b['counts']['A']>1
        eligible_diff+=a['eligible']!=b['eligible']
        parallel_changes+=a['counts']!=c['counts'];parallel_multi+=c['counts']['A']>1
    result[stem]={'counts_differ':n,'pilot_multi_A':oldmulti,'directed_record_multi_A':newmulti,'eligibility_diff':eligible_diff,
                  'parallel_only_counts_differ':parallel_changes,'parallel_only_multi_A':parallel_multi}
    print(stem,result[stem],flush=True)
(Path(__file__).parent/'real_records_results.json').write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
print(json.dumps(result,default=str),flush=True)
