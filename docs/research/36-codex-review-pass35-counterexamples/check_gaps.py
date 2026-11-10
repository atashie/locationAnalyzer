import contextlib,importlib.util,json,sys
from pathlib import Path
V2=Path(__file__).resolve().parents[1];OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(V2),str(V2/'spikes'),str(V2/'scripts')]
import networkx as nx
import numpy as np
import osmnx as ox
from shapely.geometry import LineString,Point
from locfinder.traveltime.snap import EdgeIndex
from explain_journey import sel_cost,edge_name

G=nx.MultiDiGraph(crs='EPSG:32617')
G.add_node(1,x=0.,y=0.);G.add_node(2,x=100.,y=0.)
G.add_edge(1,2,name='cheap straight road',highway='service',length=100.,travel_time=10.,cost=10.,geometry=LineString([(0,0),(100,0)]))
G.add_edge(1,2,name='matched footway',highway='footway',length=120.,travel_time=20.,cost=20.,geometry=LineString([(0,0),(0,10),(100,10),(100,0)]))
idx=EdgeIndex.from_graph(G,{1:0,2:1});gi=int(idx.tree.nearest(Point(50,10)))
data=min(G.get_edge_data(1,2).values(),key=sel_cost)
print('REPORT_GEOMETRY_MISMATCH',dict(matched_geometry=idx.geoms[gi].wkt,matched_edge_time=float(idx.fwd_time[gi]),reported_name=edge_name(data),reported_time=data['travel_time']))

# Exercise the actual comparator against a deliberately broken prediction, redirecting
# every possible write into .review35 and omitting the real audit sheets entirely.
import compare_rebuild_to_stored as compare
compare.PREDICTED_CELLS_DIFFERING=7245
compare.DATA=OUT
compare.SHEETS=OUT/'empty_sheets';compare.SHEETS.mkdir(exist_ok=True)
with (OUT/'prediction_guard.txt').open('w',encoding='utf-8') as f,contextlib.redirect_stdout(f):
    code=compare.main()
print('WRONG_PREDICTION_EXIT',code)
print((OUT/'prediction_guard.txt').read_text(encoding='utf-8'))

# Demonstrate the derived invariant's actual boundary without editing the tests.
spec=importlib.util.spec_from_file_location('tag_test',V2/'tests/test_graph_cache_manifest.py');tests=importlib.util.module_from_spec(spec);spec.loader.exec_module(tests)
old=list(ox.settings.useful_tags_way)
try:
    ox.settings.useful_tags_way=[t for t in old if t!='oneway']
    tests.test_every_tag_the_access_rules_consult_is_one_extraction_keeps()
    print('DROP_ONEWAY_INVARIANT_SURVIVES')
finally:ox.settings.useful_tags_way=old
from locfinder.traveltime import access
old=access._MODE_TAG_ORDER
try:
    access._MODE_TAG_ORDER={**old,'drive':('unextracted_new_tier',*old['drive'])}
    try:tests.test_every_tag_the_access_rules_consult_is_one_extraction_keeps()
    except AssertionError:print('ADD_UNEXTRACTED_ACCESS_TIER_CAUGHT')
finally:access._MODE_TAG_ORDER=old

from locfinder.traveltime import speeds
from locfinder.traveltime.csr import graph_to_cost_time_csr
for mode in ['walk','drive','bike']:
    times=[]
    for keep_vehicle in [False,True]:
        H=nx.MultiDiGraph()
        H.add_edge(1,2,length=140.,highway='residential',**({'vehicle':'no'} if keep_vehicle else {}))
        H.add_edge(1,2,length=420.,highway='residential')
        speeds.add_travel_times(H,mode=mode)
        C,T,index=graph_to_cost_time_csr(H)
        times.append(float(T[index[1],index[2]]))
    print('REPORTED_TIME_VEHICLE',mode,times)

H=nx.MultiDiGraph(crs='EPSG:4326')
for n in range(3):H.add_node(n,x=n*.001,y=0.)
for u,v,surface,vehicle in [(0,1,'asphalt','yes'),(1,2,'gravel','no')]:
    H.add_edge(u,v,osmid=u+100,length=140.,highway='residential',surface=surface,vehicle=vehicle)
H=ox.simplify_graph(H)
ox.save_graphml(H,OUT/'simplified.graphml');R=ox.load_graphml(OUT/'simplified.graphml')
for tag in ['surface','vehicle']:
    assert isinstance(H[0][2][0][tag],list)
    assert H[0][2][0][tag]==R[0][2][0][tag]
print('SIMPLIFIED_LIST_ROUNDTRIP',R[0][2][0]['surface'],R[0][2][0]['vehicle'])
