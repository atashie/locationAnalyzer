"""Re-enumerate T4 terms without editing the oracle; exact rational cost audit.

Uses the oracle's attachment universe and path enumeration order. Independently
recovers each occurrence's exact parameter and constructs the cost terms. Every
used partial length and connector is rational in this frozen corpus (asserted).
"""
import itertools
import json
import math
import pathlib
import sys
from fractions import Fraction as F

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "v2"), str(ROOT / "v2/scripts")]
from locfinder.measure import certify as c, toy
from locfinder.measure.conformance_cases import CASES
from measure_certified_argmin import t4_margins


def occurrence(graph, att, query):
    edge, kind, idx, *rest = att.occurrence
    g = graph.edges[edge].geometry
    if kind == "v":
        seg, t = (idx, F(0)) if idx < len(g)-1 else (idx-1, F(1))
    else:
        seg = idx
        ax, ay = map(F, g[seg])
        bx, by = map(F, g[seg+1])
        qx, qy = map(F, query)
        dx, dy = bx-ax, by-ay
        denom = dx*dx+dy*dy
        t = max(F(0), min(F(1), ((qx-ax)*dx+(qy-ay)*dy)/denom)) if denom else F(0)
        # In these fixtures the binary64 t is allowed to differ from the exact t.
    a, b = g[seg], g[seg+1]
    x = F(a[0]) + t*(F(b[0])-F(a[0]))
    y = F(a[1]) + t*(F(b[1])-F(a[1]))
    sq = (F(query[0])-x)**2 + (F(query[1])-y)**2
    residual = root_exact(sq)
    return seg, t, residual/F(126, 100)


def root_exact(q):
    n, d = math.isqrt(q.numerator), math.isqrt(q.denominator)
    assert n*n == q.numerator and d*d == q.denominator, q
    return F(n, d)


def partial(edge, start, end):
    return c.Partial(edge.geometry, *start, *end, edge.total_cost)


def rational(part):
    # Zero coefficients multiply even an irrational length to exactly zero.
    if (part.seg_o, part.t_o) == (part.seg_d, part.t_d):
        return F(0)
    roots = [root_exact((F(bx)-F(ax))**2+(F(by)-F(ay))**2)
             for (ax,ay),(bx,by) in itertools.pairwise(part.geometry)]
    (so,to), (sd,td) = sorted(((part.seg_o,part.t_o),(part.seg_d,part.t_d)))
    if not sum(roots):
        return F(0)
    span = (td-to)*roots[so] if so == sd else (1-to)*roots[so]+sum(roots[so+1:sd])+td*roots[sd]
    return span/sum(roots)*F(part.cost)


def exact_costs(case):
    graph = case.graph
    out = []
    for di, dxy in enumerate(case.destinations):
        for oa in toy.attachments(graph, case.origin, cap_m=toy.MAX_ACCESS_M):
            so, to, co = occurrence(graph, oa, case.origin)
            eo = graph.edges[oa.edge]
            for da in toy.attachments(graph, dxy, cap_m=toy.POI_SNAP_MAX_M):
                sd, td, cd = occurrence(graph, da, dxy)
                ed = graph.edges[da.edge]
                direct = toy._same_edge_direct(graph, oa, da)
                if direct is not None:
                    out.append(co+cd+rational(partial(eo, (so,to), (sd,td))))
                entries = [(eo.v, (len(eo.geometry)-2, F(1)))]
                if eo.permits(forward=False):
                    entries.append((eo.u, (0, F(0))))
                exits = [(ed.u, (0, F(0)))]
                if ed.permits(forward=False):
                    exits.append((ed.v, (len(ed.geometry)-2, F(1))))
                for en, endpoint_o in entries:
                    ec = rational(partial(eo, (so,to), endpoint_o))
                    for xn, endpoint_d in exits:
                        dc = rational(partial(ed, (sd,td), endpoint_d))
                        for pt, pc, ids in toy._simple_paths(graph, en, xn):
                            out.append(co+cd+ec+dc+sum(map(F, pc), F(0)))
    return out


def main():
    rows = []
    for case in CASES:
        js = toy.journeys(case.graph, case.origin, list(case.destinations))
        reals = exact_costs(case)
        assert len(js) == len(reals)
        row = {"case": case.name, "journeys": len(js)}
        if js:
            best = min(j.cost for j in js)
            at_min = [i for i,j in enumerate(js) if j.cost == best]
            picked = min(range(len(js)), key=lambda i: (js[i].cost, js[i].rank_key))
            row.update({"minimum_binary64_ties_have_one_real_cost": len({reals[i] for i in at_min}) == 1,
                "selected_cost_is_real_minimum": reals[picked] == min(reals),
                "distinct_destinations_at_min": len({js[i].destination for i in at_min}),
                "distinct_routes_at_min": len({js[i].route for i in at_min}),
                "distinct_times_at_min": len({js[i].time_s for i in at_min})})
            hidden = [(i,k) for i,k in itertools.combinations(range(len(js)), 2)
                      if js[i].cost == js[k].cost and reals[i] != reals[k]]
            row["binary64_equal_real_unequal_pairs"] = hidden
            costs = sorted(set(j.cost for j in js))
            close = [(a,b,(b-a)/math.ulp(a)) for a,b in itertools.pairwise(costs)
                     if a > 0 and (b-a)/math.ulp(a) < 1e6]
            row["near_ties_anywhere"] = close
        rows.append(row)
    margins = t4_margins()
    print(json.dumps({"reported_margin_counts": {k:v for k,v in margins.items() if k not in ("note", "cases")},
                      "rational_cost_audit": rows}, indent=2))


if __name__ == "__main__":
    main()
