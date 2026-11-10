from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import networkx as nx
import numpy as np
from locfinder.traveltime.csr import graph_to_cost_time_csr
from locfinder.traveltime.arrival import arrival_with_selected_destination
from locfinder.traveltime.snap import EdgeIndex,cell_selected_destination,cell_seconds_from_arrival
for order in [('A','B','home'),('B','A','home')]:
    g=nx.MultiDiGraph()
    for node in order:
        x,y={'home':(0.,0.),'A':(100.,100.),'B':(100.,-100.)}[node]
        g.add_node(node,x=x,y=y)
    for d in ['A','B']:
        g.add_edge('home',d,travel_time=100.,cost=100.)
        g.add_edge(d,'home',travel_time=100.,cost=100.)
    c,t,idx=graph_to_cost_time_csr(g)
    T,S=arrival_with_selected_destination(c,t,dest_idx=sorted([idx['A'],idx['B']]))
    print(order,'home seconds',T[idx['home']],'destination',{v:k for k,v in idx.items()}[S[idx['home']]])
