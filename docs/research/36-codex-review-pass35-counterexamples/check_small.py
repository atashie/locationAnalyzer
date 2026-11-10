"""Pass 35: read-only checks; all writes stay in this directory."""
import ast, csv, hashlib, importlib.util, inspect, json, os, sys, types
from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as ET

V2 = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
sys.path[:0] = [str(V2), str(V2 / 'spikes'), str(V2 / 'scripts')]
import networkx as nx
import numpy as np
import osmnx as ox
import pytest
import rasterio
import _common as common
from locfinder.traveltime import access, speeds
from locfinder.traveltime.csr import graph_to_cost_time_csr
from locfinder.grid import encode_minutes
from explain_journey import sel_cost, edge_name

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(name, p):
    spec = importlib.util.spec_from_file_location(name, p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def mutations():
    tests = load('manifest_tests_review35', V2/'tests/test_graph_cache_manifest.py')
    source = (V2/'spikes/_common.py').read_text(encoding='utf-8')
    mutants = {
        'baseline': source,
        'check_only_surface_missing': source.replace('missing = sorted(set(want["extra_way_tags"]) - set(stored.get("extra_way_tags") or []))', 'missing = sorted({"surface"} - set(stored.get("extra_way_tags") or []))'),
        'read_graph_before_check': source.replace('why = graph_cache_complaint(read_graph_cache_manifest(path))', 'ox.load_graphml(path)\n    why = graph_cache_complaint(read_graph_cache_manifest(path))'),
        'read_first_suppress_failure': source.replace('why = graph_cache_complaint(read_graph_cache_manifest(path))', 'try:\n        ox.load_graphml(path)\n    except Exception:\n        pass\n    why = graph_cache_complaint(read_graph_cache_manifest(path))'),
        'reject_superset': source.replace('if missing:', 'if missing or set(stored.get("extra_way_tags", [])) != set(want["extra_way_tags"]):'),
        'ignore_source': source.replace('if stored.get("source") != want["source"]:', 'if False:'),
        'load_twice_valid': source.replace('return ox.load_graphml(path)', 'ox.load_graphml(path)\n    return ox.load_graphml(path)'),
        'writer_omits_timestamp': source.replace('dict(graph_cache_manifest(), written_at=stamp())','dict(graph_cache_manifest())'),
    }
    results = {}
    for name, code in mutants.items():
        mod = types.ModuleType('review35_mutant')
        mod.__file__ = str(V2/'spikes/_common.py')
        exec(compile(code, mod.__file__, 'exec'), mod.__dict__)
        tests.common = mod
        killed = []
        for tname, fn in vars(tests).items():
            if not tname.startswith('test_') or not callable(fn): continue
            temp = OUT/'mutation_tmp'/name/tname
            temp.mkdir(parents=True, exist_ok=True)
            mp = pytest.MonkeyPatch()
            kwargs = {key: {'tmp_path':temp,'monkeypatch':mp}[key] for key in inspect.signature(fn).parameters}
            try: fn(**kwargs)
            except BaseException as exc: killed.append([tname, type(exc).__name__])
            finally: mp.undo()
        results[name] = killed or 'SURVIVES'
    print('MUTATIONS', json.dumps(results), flush=True)

def tiny_graph(**attrs):
    G = nx.MultiDiGraph(crs='EPSG:4326')
    G.add_node(1,x=0.0,y=0.0); G.add_node(2,x=0.001,y=0.0)
    G.add_edge(1,2,osmid=42,length=140.0,highway='residential',**attrs)
    return G

def cache_checks():
    p=OUT/'replacement.graphml'
    ox.save_graphml(tiny_graph(vehicle='no'),p)
    common.write_graph_cache_manifest(p)
    ox.save_graphml(tiny_graph(),p)  # old payload restored, manifest retained
    g=common.load_roads_graph(p)
    speeds.add_travel_times(g,mode='drive')
    print('STALE_PAYLOAD_ACCEPTED', dict(manifest=common.read_graph_cache_manifest(p), edge_survived=bool(g.edges), vehicle_present=any('vehicle' in d for *_,d in g.edges(data=True))))
    for data in ({'access':'no','vehicle':'forestry'}, {'vehicle':'no'}):
        print('VEHICLE_CLASS',data,{m:[access.classify_access({k:v for k,v in data.items() if k!='vehicle'},m),access.classify_access(data,m)] for m in ['walk','drive','bike']})
    G=tiny_graph(surface=['asphalt','gravel'],vehicle=['yes','no'])
    G.add_edge(2,1,osmid=43,length=140.0,highway='residential',surface='paved',vehicle='forestry')
    p=OUT/'roundtrip.graphml';ox.save_graphml(G,p);H=ox.load_graphml(p)
    print('ROUNDTRIP',[(k,type(H[1][2][0][k]).__name__,H[1][2][0][k]) for k in ['surface','vehicle']],H[2][1][0]['surface'],H[2][1][0]['vehicle'])
    assert H[1][2][0]['surface']==G[1][2][0]['surface'] and H[1][2][0]['vehicle']==G[1][2][0]['vehicle']
    print('DEFAULT_TAGS',ox.settings.useful_tags_way)
    print('UNGUARDED_INPUTS', 'length/geometry/node x,y, oneway (XML parser); expansion reads response fields, not OSM tags')
    print('RESTRICTED_REPORT',edge_name({'name':'private road','highway':'service','access':'private','access_restricted':True}))
    for edges in [[{'travel_time':10,'cost':100},{'travel_time':30,'cost':50}], [{'travel_time':40},{'travel_time':5,'cost':40}], [{'travel_time':5,'cost':40},{'travel_time':40}]]:
        G=nx.MultiDiGraph()
        for d in edges:G.add_edge(1,2,**d)
        C,T,idx=graph_to_cost_time_csr(G)
        best=min(G[1][2].values(),key=sel_cost)
        assert best['travel_time']==T[idx[1],idx[2]]
        print('CSR_SELECTION',edges,'time',best['travel_time'])

def artifacts():
    layers=V2/'data/layers'; old=layers/'prerebuild-2026-11-10'; stem='own_triangle_grocery_walk'
    a=np.load(old/(stem+'.npy'));b=np.load(layers/(stem+'.npy'));m=np.isfinite(a)&np.isfinite(b);d=b[m]-a[m]
    counts=np.load(layers/'own_triangle_buildings_per_cell.npy')
    print('DIFF',dict(cells=int((a!=b).sum()),finiteness=int((np.isfinite(a)!=np.isfinite(b)).sum()), faster=int((d<0).sum()),slower=int((d>0).sum()),max_s=float(abs(d).max()),buildings=int(counts[a!=b].sum())))
    for directory in [old,layers]:
        s=np.load(directory/(stem+'.npy'));r=np.load(directory/(stem+'_reason.npy'))
        with rasterio.open(directory/(stem+'.tif')) as f:
            print('TIF',directory.name,dict(diff=int((f.read(1)!=encode_minutes(s.astype(float))).sum()),tags=f.tags()))
        print('BUNDLE',directory.name,'counts_equal',np.array_equal(counts,np.load(directory/'own_triangle_buildings_per_cell.npy')),'seconds_reason_finite_ok',bool(np.array_equal(np.isfinite(s),r==0)))
    for t in [600,900,1500,2700]:
        print('PASS_DIFF',t,dict(old=int((a<=t).sum()),new=int((b<=t).sum()),gained=int(((b<=t)&(a>t)).sum()),lost=int(((a<=t)&(b>t)).sum()),old_buildings=int(counts[a<=t].sum()),new_buildings=int(counts[b<=t].sum())))
    build=json.loads((layers/(stem+'_build.json')).read_text())
    for key,suffix in [('seconds','.npy'),('reason','_reason.npy'),('min_possible_s','_min_possible_s.npy')]:assert digest(layers/(stem+suffix))==build['arrays'][key]
    from locfinder.status import Reason, Outcome, Criterion, evaluate
    import audit_recommendations as audit
    surf,prov=audit.load_surface(common.GRID,category='grocery',mode='walk',metro='triangle',thresholds_s=(600.,900.))
    verdicts={t:evaluate(Criterion(label='review',mode='walk',target='grocery',kind='category',threshold_s=t*60),surf) for t in [10,15]}
    for meta_p in sorted((V2.parent/'docs/experiments/audit').glob('triangle*.meta.json')):
        meta=json.loads(meta_p.read_text());checks={}
        for key in ['seconds','reason']:
            name=Path(meta['layer'][key]['path']).name
            checks['old_'+key]=digest(old/name)==meta['layer'][key]['sha256']
        checks['old_buildings']=digest(old/'own_triangle_buildings_per_cell.npy')==meta['selection']['buildings']['sha256']
        for key,suffix in [('seconds','.npy'),('reason','_reason.npy'),('min_possible_s','_min_possible_s.npy')]:checks['new_'+key]=digest(layers/(stem+suffix))==meta['superseded_by_rebuild']['arrays_now'][key]
        rows=list(csv.DictReader(meta_p.with_suffix('').with_suffix('.csv').open(encoding='utf-8-sig')))
        enriched=list(csv.DictReader(meta_p.with_suffix('').with_suffix('').with_name(meta_p.name.removesuffix('.meta.json')+'-with-destinations.csv').open(encoding='utf-8-sig')))
        failures=[]
        for row in rows:
            i,j=int(row['row']),int(row['col']);sec=float(b[i,j]);s=f'{sec:.1f}' if np.isfinite(sec) else ''
            if s!=row['seconds'] or row['reason']!=Reason(int(surf.reason[i,j])).name:failures.append(row['journey_id'])
            for t in [10,15]:
                if row[f'outcome_{t}min']!=Outcome(int(verdicts[t][i,j])).name:failures.append(row['journey_id'])
            assert a[i,j]==b[i,j]
        checks['rows']=len(rows);checks['failures']=failures
        checks['enriched_matches_base']=all(all(r[k]==e[k] for k in r) for r,e in zip(rows,enriched))
        print('AUDIT_META',meta_p.name,checks)
    print('BUILD_DIGESTS_OK',build['arrays'])

def xml_counts():
    counts=Counter();vehicles=Counter()
    for _,el in ET.iterparse(V2/'data/triangle/triangle-roads.osm',events=('end',)):
        if el.tag=='way':
            for tag in el.findall('tag'):
                key=tag.get('k')
                if key in ['surface','vehicle']:counts[key]+=1
                if key=='vehicle':vehicles[tag.get('v')]+=1
            el.clear()
        elif el.tag=='node':el.clear()
    print('XML',dict(counts),dict(vehicles))

mutations();cache_checks();artifacts();xml_counts()
