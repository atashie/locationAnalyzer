"""Read-only pass 36 counterexamples; writes only inside .review36."""
from pathlib import Path
import sys, json, math, importlib.util, subprocess, tempfile
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import shapely
import networkx as nx

V2 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(V2))
sys.path.insert(0, str(V2 / 'scripts'))
import t0_attachment_pilot as p
import render_t0_results as render
from locfinder.measure import toy
from locfinder.measure.frames import build_frame_c, write_frame, read_frame
from locfinder.grid import GridSpec

def show(name, value):
    print(name + ': ' + json.dumps(value, default=str))

def measure(geoms, xy):
    return p.measure_point(geoms, shapely.STRtree(geoms), *xy, 200)

def oracle(graph, xy, dest, variant):
    geoms = [shapely.LineString(e.geometry) for e in graph.edges]
    selected = measure(geoms, xy)['_sets'][variant]
    atts = tuple(toy.Attachment(edge=q.record, fraction=q.arclength/graph.edges[q.record].length_m,
                 arclength_m=q.arclength, residual_m=q.residual,
                 position=(q.x,q.y), occurrence=q.occurrence) for q in selected)
    original = toy.attachments
    def replacements(g, point, *, cap_m):
        return atts if tuple(point) == tuple(xy) else original(g, point, cap_m=cap_m)
    with patch.object(toy, 'attachments', replacements):
        result = toy.evaluate(graph, xy, [dest])
    return result

# Same-record bound fails on a bidirectional edge when cost chooses the journey.
geom = ((0., 0.), (50., 0.), (100., 0.))
graph = toy.ToyGraph((
    toy.ToyEdge(0,1,geom,time_s=100.,cost_base=100.,penalty=120.),
    toy.ToyEdge(0,2,((0.,0.),(0.,100.)),time_s=200.,cost_base=200.),
    toy.ToyEdge(1,2,((100.,0.),(0.,100.)),time_s=79.98,cost_base=79.98,penalty=120.),
))
xy=(49.995,0.); dest=(0.,100.)
r = measure([shapely.LineString(e.geometry) for e in graph.edges],xy)
idx=SimpleNamespace(geoms=[shapely.LineString(e.geometry) for e in graph.edges],
                    fwd_time=[100.,200.,79.98],rev_time=[100.,200.,79.98])
a=oracle(graph,xy,dest,'A'); c=oracle(graph,xy,dest,'C')
show('cost_selected_time_bound', {'bound':p.impact_bound(idx,r['_sets']['A'],r['_sets']['C']),
    'A_objective1':a.objective1_s,'C_objective1':c.objective1_s,
    'A_objective2':a.objective2_s,'C_objective2':c.objective2_s,
    'A_cost':a.objective2_cost,'C_cost':c.objective2_cost})

# A one-way same-edge destination can lose reachability across a zero span.
one = toy.ToyGraph((toy.ToyEdge(0,1,geom,time_s=100.,cost_base=100.,oneway=True),))
xy=(50.005,0.); dest=(50.,0.)
r=measure([shapely.LineString(geom)],xy)
idx=SimpleNamespace(geoms=[shapely.LineString(geom)],fwd_time=[100.],rev_time=[np.inf])
a=oracle(one,xy,dest,'A'); c=oracle(one,xy,dest,'C')
show('oneway_zero_span_bound', {'bound':p.impact_bound(idx,r['_sets']['A'],r['_sets']['C']),
                              'A_time':a.objective1_s,'C_time':c.objective1_s})

# Change both origin and destination conventions: unchanged origins still need routing.
original=toy.attachments
destination_results={}
for variant in ['A','C']:
    def attachment_variant(g, point, *, cap_m):
        shapes=[shapely.LineString(e.geometry) for e in g.edges]
        selected=p.measure_point(shapes,shapely.STRtree(shapes),*point,cap_m)['_sets'][variant]
        return tuple(toy.Attachment(edge=q.record,fraction=q.arclength/g.edges[q.record].length_m,
                     arclength_m=q.arclength,residual_m=q.residual,position=(q.x,q.y),occurrence=q.occurrence)
                     for q in selected)
    with patch.object(toy,'attachments',attachment_variant):
        res=toy.evaluate(one,(50.,0.),[(49.995,0.)])
    destination_results[variant]=res.objective1_s
show('unchanged_origin_changed_destination',{'origin_counts':measure([shapely.LineString(geom)],(50.,0.))['counts'],
                                          'times':destination_results})

# Midpoint splitting duplicates a segment at an existing midpoint vertex.
for coords in [[(0,0),(1,0),(2,0)], [(0,0),(1,0),(2.000001,0)],
               [(0,0),(1,0),(1.999999,0)]]:
    g=shapely.LineString(coords)
    halves,_=p.split_record(g,0)
    show('split_midpoint', {'before':g.wkt,'after':[v.wkt for v in halves.values()],
                          'old_length':g.length,'new_length':sum(v.length for v in halves.values())})

# An inserted binary64 cut perturbs a genuine exact tie, which D then loses.
g=shapely.LineString([(-401,302),(195,-145),(189,-143),(-7,4)])
before=measure([g],(0.,0.))
pieces,_=p.split_record(g,0)
after=measure(list(pieces.values()),(0.,0.))
show('D_midpoint_split_moves',{'before':[(q.x,q.y) for q in before['_sets']['D']],
    'after':[(q.x,q.y) for q in after['_sets']['D']],
    'moves':p.positions_differ(before['_sets']['D'],after['_sets']['D'])})

# Collapsing parallel weight alternatives changes attachment multiplicity.
G=nx.MultiDiGraph()
G.add_node(0,x=0.,y=0.); G.add_node(1,x=100.,y=0.)
for t in [2000.,2.]:
    G.add_edge(0,1,geometry=shapely.LineString([(0,0),(100,0)]),travel_time=t,cost=t)
index=p.EdgeIndex.from_graph(G,{0:0,1:1})
physical=measure(index.geoms,(50.,0.))
edges=toy.ToyGraph(tuple(toy.ToyEdge(0,1,((0.,0.),(100.,0.)),time_s=t,cost_base=t,oneway=True)
                         for t in [2000.,2.]))
show('parallel_record_count',{'pilot':physical['counts'],'design_A':len(toy.attachments(edges,(50.,0.),cap_m=200)),
                              'index_kept_times':index.fwd_time.tolist()})

def fake(coords):
    return [SimpleNamespace(x=x,y=y) for x,y in coords]
eps=1e-7
show('position_false_positive',p.positions_differ(fake([(0,0),(0,10)]),fake([(-eps,10),(eps,0)])))
# With a valid <= 1 micrometre correspondence, an intervening far-y point prevents dedup.
show('dedup_nonadjacent',p.positions_differ(fake([(0,0),(0.5e-7,10),(1e-7,0)]),
                                          fake([(0,0),(0.5e-7,10)])))
# An occurrence loss at the same XY is invisible, despite very different arclengths.
selfgeom=shapely.LineString([(-100,0),(0,0),(0,100),(100,100),(100,0),(0,0),(0,-100)])
selfraw=p.raw_positions([selfgeom],[0],0.,0.)
selfa=p.dedup_and_cap(p.convention_a(selfraw,0.),200.)
show('position_false_negative',{'arcs':[q.arclength for q in selfa],
    'differ':p.positions_differ(selfa,selfa[:1]),'oneway_times':[(selfgeom.length-q.arclength)/selfgeom.length*1000 for q in selfa]})

# Degenerate bounding boxes, zero-length segments, ties, and an independent full scan.
geoms=[shapely.LineString([(0,1),(2,1)]),shapely.LineString([(1,0),(1,2)]),
       shapely.LineString([(1,1),(1,1)]),shapely.LineString([(1,1.01),(2,1.01)])]
r=measure(geoms,(1.,1.))
show('degenerate_window',{'counts':r['counts'],'records':r['records'],'window':r['window_records']})
rng=np.random.default_rng(36)
geoms=[shapely.LineString(a) for a in rng.uniform(-1e7,1e7,(300,4,2))]
tree=shapely.STRtree(geoms)
miss=0
for xy in rng.uniform(-1e7,1e7,(100,2)):
    r=p.measure_point(geoms,tree,*xy,2e7)
    raw=p.raw_positions(geoms,range(len(geoms)),*xy)
    for q in raw:q.exact_sq=p.exact_segment_sq(*xy,*p._seg_ends(geoms,q))
    mn=min(q.residual for q in raw)
    for k,kept in [('A',p.convention_a(raw,mn)),('C',p.convention_c(raw,mn)),('D',p.convention_d(raw))]:
        miss+=p.signature(p.dedup_and_cap(kept,2e7))!=p.signature(r['_sets'][k])
show('enumeration_full_scan_disagreements',miss)

# Exercise --check on a copy, leaving tracked files untouched.
old_doc=render.DOC
copy=Path(__file__).parent/'render_copy.md'
copy.write_text(old_doc.read_text(encoding='utf-8'),encoding='utf-8')
with patch.object(render,'DOC',copy),patch.object(sys,'argv',['render','--check']):
    clean=render.main()
    copy.write_text(copy.read_text(encoding='utf-8').replace('539,814 nodes','539,815 nodes'),encoding='utf-8')
    drift=render.main()
show('renderer_check',{'clean':clean,'drift':drift})
artifact=json.loads(render.ART.read_text(encoding='utf-8'))
show('handwritten_disagreement_rates',{k:{'multi_A':100*v['A']['points_with_multiple_candidates']/v['points'],
    'A_C':100*v['A_vs_C_set_differs']/v['points'],'A_D':100*v['A_vs_D_set_differs']/v['points']}
    for k,v in artifact['sets'].items()})
show('census_seconds',sum(v['seconds'] for k,v in artifact['sets'].items() if k.startswith('census')))
show('artifact_top_level_keys',list(artifact))

# Frozen frame disk contents fail digest verification after tampering.
from locfinder.metros import get_metro
import pandas as pd
directory=Path(__file__).parent / ('frames_run_' + str(len(list(Path(__file__).parent.glob('frames_run_*')))))
directory.mkdir()
frame=build_frame_c(get_metro().grid(),n=2,seed=36)
parquet,manifest=write_frame(frame,directory)
loaded=read_frame(manifest)
table=pd.read_parquet(parquet);table.loc[0,'x']+=1.;table.to_parquet(parquet,index=False)
try:read_frame(manifest);tamper='ACCEPTED'
except ValueError as exc:tamper=str(exc)
show('read_frame',{'roundtrip':loaded.digest==frame.digest,'tamper':tamper})
