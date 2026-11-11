import sys, random, json
from pathlib import Path
from fractions import Fraction as F
import shapely
V2=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(V2),str(V2/'scripts')]
import t0_attachment_pilot as p
rng=random.Random(36)
for i in range(10000):
    a=(rng.uniform(-100,-1),rng.uniform(1,3))
    b=(rng.uniform(1,100),rng.uniform(1,3))
    c=tuple(2*y-x for x,y in zip(a,b))
    if any(F(z)!=2*F(y)-F(x) for x,y,z in zip(a,b,c)):continue
    geoms=[shapely.LineString([a,b]),shapely.LineString([tuple(-v for v in a),tuple(-v for v in c)])]
    before=p.measure_point(geoms,shapely.STRtree(geoms),0.,0.,200.)
    if len(before['_sets']['D'])!=2:continue
    sub=[p.subdivide(g)[0] for g in geoms]
    after=p.measure_point(sub,shapely.STRtree(sub),0.,0.,200.)
    if p.positions_differ(before['_sets']['D'],after['_sets']['D']):
        print(json.dumps({'geometries':[g.wkt for g in geoms],
            'subdivided':[g.wkt for g in sub],
            'before':[(q.x,q.y,str(q.exact_sq)) for q in before['_sets']['D']],
            'after':[(q.x,q.y,str(q.exact_sq)) for q in after['_sets']['D']]},indent=2))
        break
else:print('no case')
