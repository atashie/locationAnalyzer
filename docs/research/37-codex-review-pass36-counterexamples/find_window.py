import sys, random, json
from pathlib import Path
import shapely
V2=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(V2),str(V2/'scripts')]
import t0_attachment_pilot as p
rng=random.Random(36)
pt=shapely.Point(0.,0.)
for _ in range(10000):
    coords=[(rng.uniform(-100,100),rng.uniform(-100,100)) for _ in range(2)]
    nearest=shapely.LineString(coords)
    toy=p.raw_positions([nearest],[0],0.,0.)[0].residual
    geos=nearest.distance(pt)
    if geos+p.ATTACH_TIE_M>=toy+p.ATTACH_TIE_M:continue
    edge=toy+p.ATTACH_TIE_M
    geoms=[nearest,shapely.LineString([(edge,-1.),(edge,1.)])]
    tree=shapely.STRtree(geoms)
    before=p.measure_point(geoms,tree,0.,0.,200.)
    window=tree.query(pt.buffer(geos+p.ATTACH_TIE_M))
    after_raw=p.raw_positions(geoms,window,0.,0.)
    after=p.dedup_and_cap(p.convention_a(after_raw,min(q.residual for q in after_raw)),200.)
    if p.positions_differ(before['_sets']['A'],after):
        print(json.dumps({'geometries':[g.wkt for g in geoms],'GEOS_min':geos,'computed_min':toy,
                          'no_slack_window':window.tolist(),'before_count':before['counts']['A'],
                          'after_count':len(after)},indent=2));break
else:print('no case')
