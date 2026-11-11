from pathlib import Path
import sys, random, math, json
import shapely
V2=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(V2),str(V2/'scripts')]
import t0_attachment_pilot as p
rng=random.Random(36)
for it in range(10000):
    coords=[[-1.,2.],[195.,-145.],[189.,-143.],[-7.,4.]]
    for a in coords:
        for j in range(2):
            n=rng.randrange(-2,3)
            for _ in range(abs(n)):a[j]=math.nextafter(a[j],math.inf if n>0 else -math.inf)
    g=shapely.LineString(coords)
    r=p.measure_point([g],shapely.STRtree([g]),0.,0.,200.)
    if r['c_drops_a_genuine_exact_tie'] and len(set(q.exact_sq for q in r['_sets']['A']))>1:
        print(json.dumps({'geometry':coords,'reported_genuine_ties':r['c_drops_a_genuine_exact_tie'],
          'A':[(q.seg,q.residual,str(q.exact_sq)) for q in r['_sets']['A']],
          'C':[(q.seg,q.residual,str(q.exact_sq)) for q in r['_sets']['C']]},indent=2))
        break
else:print('no case')
