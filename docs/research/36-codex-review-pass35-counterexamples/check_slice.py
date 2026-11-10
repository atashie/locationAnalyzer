import os,sys
from pathlib import Path
V2=Path(__file__).resolve().parents[1]
os.environ['LOCFINDER_METRO']='slice'
sys.path[:0]=[str(V2),str(V2/'spikes')]
import _common as c
print('METRO',c.METRO.name,'manifest',c.graph_cache_manifest())
fallback=c.GRAPH_CACHE if c.GRAPH_CACHE.exists() else c.GRAPH_CACHE.with_name('slice-roads.graphml')
print('FALLBACK',fallback.name)
try:c.load_roads_graph(fallback)
except SystemExit as e:print('REFUSED',e)
