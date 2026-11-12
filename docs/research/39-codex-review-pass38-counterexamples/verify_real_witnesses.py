"""Replay committed witness geometry, or --extract from the local pinned graph (~2 min).

Default needs no local graph/buildings data. --extract verifies all the adoption example
points, and saves just their window geometries and the source graph pin for replay.
"""
from common import ROOT, script
from fractions import Fraction as F
import json
import math
from pathlib import Path
import sys
import numpy as np
import shapely

HERE = Path(__file__).resolve().parent
pilot = script('t0_attachment_pilot')
artifact = json.loads((ROOT / 'docs/experiments/t0-attachment-pilot.json').read_text())

if '--extract' in sys.argv:
    print('Preparing pinned local graph...', flush=True)
    G = pilot.load_roads_graph()
    G = pilot.ox.project_graph(G, to_crs=pilot.GRID.crs)
    G = pilot.add_travel_times(G, mode='walk')
    G = pilot.symmetrise(G)
    G.remove_nodes_from([n for n, d in G.degree() if d == 0])
    G, _ = pilot.largest_component(G)
    records = pilot.Records(G, {n: i for i, n in enumerate(G.nodes())}, kind='design')
    assert len(records) == artifact['graph']['design_records']
    manifest = pilot.read_graph_cache_manifest()
    assert manifest['graphml_sha256'] == artifact['pinned']['graphml_sha256']
    cases = []
    for example in artifact['adoption']['sets']['census_all_structures']['examples']:
        px, py = example['x'], example['y']
        m = pilot.measure_point(records.geoms, records.tree, px, py, 200.)
        cases.append({'point': [px, py], 'records': [int(r) for r in m['_window']],
                      'geometries': [shapely.get_coordinates(records.geoms[r]).tolist()
                                     for r in m['_window']]})
    (HERE / 'real-witnesses.json').write_text(json.dumps({
        'graphml_sha256': manifest['graphml_sha256'], 'cases': cases}, indent=2) + '\n')

data = json.loads((HERE / 'real-witnesses.json').read_text())
assert data['graphml_sha256'] == artifact['pinned']['graphml_sha256']
for case in data['cases']:
    geoms = np.empty(len(case['geometries']), dtype=object)
    geoms[:] = [shapely.LineString(c) for c in case['geometries']]
    tree = shapely.STRtree(geoms)
    pt = case['point']
    both = [pilot.measure_point(geoms, tree, *pt, 200., arithmetic=a) for a in ('float', 'exact')]
    fs, xs = [m['_sets']['C'] for m in both]
    stats = pilot.adoption_stats(geoms, tree, [pt], 200.)
    assert stats['occurrences_changed']['C_exact_vs_C'] == 1
    assert stats['raw']['vertex_or_interior_differs'] == 0
    assert stats['places_changed']['A_exact_vs_A'] == 0
    assert stats['places_changed']['D_exact_vs_D'] == 0
    shifts = [math.hypot(p.x-q.x,p.y-q.y) for p,q in zip(fs,xs)]
    print('Point', pt, 'C selected displacement (m):', shifts)
    for pf, px in zip(fs, xs):
        # Locate the exact nearest foot on the segment the float path discarded.
        record = px.record
        xr = [p for p in both[1]['_raw'] if p.record == record]
        old = next(p for p in xr if p.occurrence[:3] == pf.occurrence[:3])
        best = min(xr, key=lambda p: p.exact_sq)
        error_at_best = next(p for p in both[0]['_raw']
                             if (p.record,p.seg)==(best.record,best.seg)).residual-best.residual
        gap = old.residual - best.residual
        print('  residuals:', old.residual, best.residual,
              '; gap:', gap, '; float error at best:', error_at_best)
    print('  raw clamp flips:', stats['raw']['vertex_or_interior_differs'],
          '; exact C keys:', [p.occurrence[:3] for p in xs])
    rational_changes = sum(F(pf.t) != px.t for pf, px in zip(both[0]['_raw'], both[1]['_raw']))
    print('  parameter changes: reported binary64 images', stats['raw']['parameter_differs'],
          '; exact rational comparison', rational_changes)

sets = artifact['adoption']['sets']
raw = [s['raw'] for s in sets.values()]
for key in ('positions_compared', 'residual_differs', 'arclength_differs', 'parameter_differs',
            'position_differs', 'vertex_or_interior_differs'):
    print('Artifact total', key, sum(r[key] for r in raw))
print('Artifact points:', sum(s['points'] for s in sets.values()))
for key in ('max_abs_residual_diff_m', 'max_abs_arclength_diff_m', 'max_position_shift_m'):
    print('Artifact maximum', key, max(r[key] for r in raw))
print('Quadratic check:', (3.56e-5)**2/(2*21.97))
