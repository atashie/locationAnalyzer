"""Executable counterexample to 'a penalised track loses to any paved alternative'."""
import sys,pathlib,json
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import networkx as nx
from locfinder.traveltime.speeds import add_travel_times
from locfinder.traveltime.access import access_penalty_s
from locfinder.traveltime.csr import graph_to_cost_time_csr
G=nx.MultiDiGraph()
G.add_edge(0,1,key='track',highway='track',length=140.)
G.add_edge(0,1,key='paved',highway='residential',surface='asphalt',length=1400.)
add_travel_times(G,mode='walk')
before={k:d['cost'] for _,_,k,d in G.edges(keys=True,data=True)}
G[0][1]['track']['cost']+=120.
C,T,index=graph_to_cost_time_csr(G)
out=dict(existing_class_penalties={h:access_penalty_s({'highway':h},'walk') for h in ['track','path','footway','service']},before_costs=before,with_explicit_track_penalty=dict(selected_cost=float(C[0,1]),reported_time=float(T[0,1]),paved_cost=1000.))
from locfinder import profile
from locfinder.traveltime import speeds
before_profile=profile.profile_version(); original=speeds.symmetrise
speeds.symmetrise=lambda g:g
out['profile_before_and_after_replacing_symmetrise']=[before_profile,profile.profile_version()]
speeds.symmetrise=original
print(json.dumps(out,indent=2))
