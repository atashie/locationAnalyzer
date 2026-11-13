"""Pass 41 attacks A-F. Run with v2/.venv/Scripts/python.exe -B <this file> [A|B|C|D|E|F]."""
from common import ROOT, spike, paths, original_population, diamond
import contextlib
from fractions import Fraction
import heapq
import io
import json
import math
import random
import sys


def a_journeys():
    from locfinder.measure.toy import ToyEdge, ToyGraph, evaluate, journeys
    xy = {-1: (-2000., 0.), 0: (0., 0.), 1: (100., 100.),
          2: (100., -100.), 3: (200., 0.), 4: (2200., 0.)}
    rows = [(-1, 0, 2., 2.), *diamond(1000.)[:-1], (3, 4, 2., 2000.)]
    graph = ToyGraph(tuple(ToyEdge(u, v, (xy[u], xy[v]), t, c, oneway=True)
                           for u, v, t, c in rows))
    origin = (-1000., 1.26)
    destinations, ids = [(1200., 1.26), (2200., 0.)], ['z', 'a']
    oracle = evaluate(graph, origin, destinations, ids)
    js = journeys(graph, origin, destinations, ids)
    # Expanded query graph: source 5 -> entry node 0; exit nodes -> distinct goal sinks.
    # Combine terms only where their sum is exact (1+1, 1000+1). All query terms are explicit above.
    expanded = [(5, 0, 2., 2.), *diamond(1000.)[:-1],
                (3, 6, 2., 1001.), (3, 7, 2., 2000.)]
    selected = min((*spike.lexicographic(spike.adjacency(expanded), 5, g)[:2], did)
                   for g, did in [(6, 'z'), (7, 'a')])
    assert (oracle.objective2_cost, oracle.objective2_s, oracle.objective2_destination_id) == (2003., 5., 'z')
    assert selected == (2003., 1004., 'z')
    print('A real oracle journeys (destination, cost, seconds):',
          [(j.destination_id, j.cost, j.time_s) for j in js])
    print('A normative (cost,time,id):', (2003., 5., 'z'), '; single-label:', selected)
    print('A entry fraction=1/2, exit fraction=1/2 for z; origin connector=1 s; destination connectors z=1 s, a=0 s')
    print('A exact 600 s verdict: normative PASS, lexicographic FAIL; encoded ceil minutes: 1 versus 17')

    # The multi-goal/id/partial-term abstraction DOES work when arithmetic is exact additive.
    rng = random.Random(41001)
    for _ in range(500):
        n = 7
        edges = spike.random_graph(rng, n, 12, 8)
        # Two origin entries, fractional edge terms, unequal destination connectors, three ids.
        edges += [(7, 0, .5, 1.5), (7, 2, 1.5, .5)]
        terminals = [(8, 4, 'z', .5, 1.), (9, 5, 'a', 1.5, 0.), (10, 6, 'b', 0., 2.)]
        for sink, node, did, partial, connector in terminals:
            edges.append((node, sink, partial + connector, partial + connector))
        truth, got = [], []
        for sink, _, did, _, _ in terminals:
            ps = paths(edges, 7, sink)
            lx = spike.lexicographic(spike.adjacency(edges), 7, sink)
            if ps:
                truth.append((*min(ps)[:2], did))
                got.append((*lx[:2], did))
        assert min(truth) == min(got)
    print('A exact-additive expanded multi-entry/multi-goal/partial/connector checks: 500/500 agree, including destination id')
    return {'oracle': [2003., 5., 'z'], 'lex': list(selected), 'exact_additive_multigoal_agreements': 500}


def b_baseline():
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        spike.main([])
    replay, _ = json.JSONDecoder().raw_decode(out.getvalue())
    committed = json.loads((ROOT / 'docs/experiments/search-semantics-spike.json').read_text(encoding='utf-8'))
    for k, v in replay.items():
        assert v == committed[k], (k, v, committed[k])
    print('B unmodified spike replay matches all committed aggregate fields:', replay)
    print('B fair local time-tie baseline on that population: lexicographic, 0 wrong cost / 0 wrong time')
    print('B arbitrary equal-cost dropping is legal for cost-only optimization, but not the full normative ranking.')
    return replay


def trace_lex(edges, start, goal):
    """Instrument the same update/stale predicates, asserting agreement with the original."""
    adj = spike.adjacency(edges)
    best, heap, popped = {start: (0., 0.)}, [(0., 0., start)], set()
    stale = after_pop = 0
    while heap:
        c, t, u = heapq.heappop(heap)
        if (c, t) != best.get(u):
            stale += 1
            continue
        popped.add(u)
        for _, v, et, ec in adj.get(u, ()):
            candidate = (c + ec, t + et)
            if v not in best or candidate < best[v]:
                after_pop += v in popped
                best[v] = candidate
                heapq.heappush(heap, (*candidate, v))
    got = spike.lexicographic(adj, start, goal)
    assert (got[:2] if got else None) == best.get(goal)
    return stale, after_pop


def c_numeric():
    results = {}
    zero_cycle = [(0, 1, 0., 0.), (1, 0, 0., 0.), (0, 2, 2., 0.), (1, 2, 1., 0.)]
    zero_got = spike.lexicographic(spike.adjacency(zero_cycle), 0, 2)
    assert zero_got == min(paths(zero_cycle, 0, 2))[:3] == (0., 1., (0, 1, 2))
    print('C explicit zero-cost/zero-time cycle terminates with correct pair:', zero_got)
    for name, edges in [('pass37', [(0, 1, 500., .5), (1, 3, 500., .5),
                                    (0, 2, .5, .5), (2, 3, .5, .5000000000000002), (3, 4, 1., 2.**54)]),
                        ('unit_scale', diamond()), ('ordinary_scale', diamond(1000.))]:
        truth = min(paths(edges, 0, 4))[:3]
        got = spike.lexicographic(spike.adjacency(edges), 0, 4)
        assert truth[1] == 2. and got[1] == 1001.
        # Even exact prefix arithmetic cannot fix the dominance relation of rounded complete costs.
        prefix_p = sum((Fraction(e[3]) for e in edges[:2]), Fraction())
        prefix_q = sum((Fraction(e[3]) for e in edges[2:4]), Fraction())
        assert prefix_p < prefix_q
        assert float(prefix_p + Fraction(edges[-1][3])) == float(prefix_q + Fraction(edges[-1][3]))
        print('C', name, 'whole-term oracle:', truth, '; lex:', got,
              '; exact prefix gap:', str(prefix_q - prefix_p))
        results[name] = {'truth': truth, 'lex': got, 'exact_prefix_gap': str(prefix_q - prefix_p)}

    # Shared accumulation bug in search AND oracle can conceal a wrong answer.
    edges = [(0, 1, 1., 2.**53), (1, 2, 1., 1.), (2, 3, 1., 1.), (0, 3, 100., 2.**53)]
    oracle = min(paths(edges, 0, 3))[:3]
    spike_oracle = min(spike.all_simple(spike.adjacency(edges), 0, 3))
    got = spike.lexicographic(spike.adjacency(edges), 0, 3)
    assert got == spike_oracle == (2.**53, 3., (0, 1, 2, 3))
    assert oracle == (2.**53, 100., (0, 3))
    assert math.fsum((2.**53, 1., 1.)) == 2.**53 + 2.
    print('C shared-bug example: spike oracle = lex =', got, '; whole-term oracle =', oracle)
    results['shared_accumulation_bug'] = {'spike_oracle_and_lex': got, 'whole_term_oracle': oracle}

    rng = random.Random(41003)
    families = [('zero_one', 9, 35, 2), ('zero_small', 12, 25, 4),
                ('dense', 9, 60, 8), ('wide_integer', 12, 25, 1000000),
                ('anticorrelated', 10, 35, 1024), ('dyadic', 12, 25, 32),
                ('continuous', 12, 25, 32), ('large_dag', 30, 70, 8)]
    stress = {}
    for name, n, extra, width in families:
        stats = {'attempted': 120, 'compared': 0, 'unreachable': 0, 'path_limit': 0,
                 'wrong_cost': 0, 'right_cost_wrong_time': 0, 'stale_skips': 0,
                 'improvements_after_pop': 0, 'max_paths': 0}
        for _ in range(stats['attempted']):
            if name == 'large_dag':
                pairs = [(i, i + 1) for i in range(n - 1)]
                pairs += [tuple(sorted(rng.sample(range(n), 2))) for _ in range(extra)]
            else:
                pairs = [(e[0], e[1]) for e in spike.random_graph(rng, n, extra, 4)]
            edges = []
            for u, v in pairs:
                c, t = float(rng.randrange(width)), float(rng.randrange(width))
                if name == 'anticorrelated':
                    t = width - c
                if name == 'dyadic':
                    c, t = c / 8, t / 8
                if name == 'continuous':
                    c, t = rng.random() * width, rng.random() * width
                edges.append((u, v, t, c))
            try:
                ps = paths(edges, 0, n - 1)
            except RuntimeError:
                stats['path_limit'] += 1
                continue
            if not ps:
                stats['unreachable'] += 1
                continue
            stats['compared'] += 1
            stats['max_paths'] = max(stats['max_paths'], len(ps))
            truth = min(ps)
            got = spike.lexicographic(spike.adjacency(edges), 0, n - 1)
            stats['wrong_cost'] += got[0] != truth[0]
            stats['right_cost_wrong_time'] += got[0] == truth[0] and got[1] != truth[1]
            stale, after = trace_lex(edges, 0, n - 1)
            stats['stale_skips'] += stale
            stats['improvements_after_pop'] += after
        if name != 'continuous':
            assert stats['wrong_cost'] == stats['right_cost_wrong_time'] == 0
        assert stats['improvements_after_pop'] == 0
        stress[name] = stats
        print('C stress', name, stats)
    results['stress'] = stress
    return results


def canonical_exact_route(edges, start, goal):
    """Fourth-option illustration for EXACT-ADDITIVE graphs only: tight edges + greedy feasibility.

    Edge/node path order coincide here because ids are the ordered node pairs. Avoid visited nodes
    during reachability, so zero-cost cycles cannot make an invalid node-simple reconstruction.
    """
    nodes = {u for u, _, _, _ in edges} | {v for _, v, _, _ in edges}
    dist = {u: spike.lexicographic(spike.adjacency(edges), u, goal) for u in nodes}
    tight = {}
    for u, v, t, c in edges:
        if dist[u] and dist[v] and (c + dist[v][0], t + dist[v][1]) == dist[u][:2]:
            tight.setdefault(u, set()).add(v)

    def feasible(start, banned):
        stack, seen = [start], set(banned)
        while stack:
            u = stack.pop()
            if u in seen:
                continue
            if u == goal:
                return True
            seen.add(u)
            stack.extend(tight.get(u, ()))
        return False

    out = [start]
    while out[-1] != goal:
        u = out[-1]
        out.append(next(v for v in sorted(tight.get(u, ())) if feasible(v, out)))
    return tuple(out)


def d_routes():
    n = ambiguous = distinct = actual_wrong = 0
    for nodes, edges in original_population():
        ps = spike.all_simple(spike.adjacency(edges), 0, nodes - 1)
        if not ps:
            continue
        n += 1
        pair = min((c, t) for c, t, p in ps)
        tied = [p for c, t, p in ps if (c, t) == pair]
        ambiguous += len(tied) > 1
        distinct += len(set(tied)) > 1
        actual_wrong += spike.lexicographic(spike.adjacency(edges), 0, nodes - 1)[2] != min(ps)[2]
    assert (n, ambiguous, distinct, actual_wrong) == (3267, 162, 23, 14)
    print('D original residual:', ambiguous, '/', n, '; distinct node routes:', distinct,
          '; duplicate-only:', ambiguous - distinct, '; actual lex route mismatches:', actual_wrong)
    # Minimal duplicate-edge witness lifted to the real canonical identity.
    from locfinder.measure.toy import ToyEdge, ToyGraph, Journey, evaluate, journeys
    e = ToyEdge(0, 1, ((0., 0.), (100., 0.)), 1., 1., oneway=True)
    ps = spike.all_simple(spike.adjacency([(0, 1, 1., 1.)] * 2), 0, 1)
    js = journeys(ToyGraph((e, e)), (0., 0.), [(100., 0.)], ['z'])
    assert len(ps) == 2 and len({p for c, t, p in ps}) == 1
    assert len({j.rank_key for j in js}) == 1
    print('D identical parallel-edge witness: 2 enumerated paths, 1 route, 1 full normative rank')

    # Abstract order reversal is real, but cannot be a same-root, same-merge node-simple pair.
    p, q, suffix = (1,), (1, 2), (3,)
    assert p < q and p + suffix > q + suffix
    print('D abstract prefix reversal:', p, '<', q, 'but', p + suffix, '>', q + suffix)
    # A legal journey-level reversal IS possible at a variable entry: zero loop entry vs empty entry.
    loop = ToyEdge(0, 0, ((0., 0.), (100., 0.), (0., 0.), (-100., 0.), (0., 0.)),
                   0., 0., oneway=True)
    exit_edge = ToyEdge(0, 1, ((0., 0.), (0., -100.)), 1., 1., oneway=True)
    loop_graph = ToyGraph((loop, exit_edge))
    js = journeys(loop_graph, (0., 0.), [(0., -100.)], ['z'])
    routes = {j.route for j in js if j.cost == j.time_s == 1.}
    empty_prefix, loop_prefix, completion = (), (loop.identity,), (exit_edge.identity,)
    assert empty_prefix < loop_prefix
    assert empty_prefix + completion > loop_prefix + completion
    assert completion in routes and loop_prefix + completion in routes
    assert evaluate(loop_graph, (0., 0.), [(0., -100.)], ['z']).objective2_route == loop_prefix + completion
    print('D admissible partial-loop entry reversal: empty < [loop], but [exit] > [loop,exit]; oracle chooses [loop,exit]')

    # Pure internal node-simple prefixes cannot properly extend one another at the same merge.
    # A two-phase route reconstruction closes exact-additive route identity, including zero cycles.
    rng = random.Random(41004)
    checked = 0
    for _ in range(300):
        edges = [(u, v, float(rng.randrange(2)), float(rng.randrange(2)))
                 for u, v in (rng.sample(range(7), 2) for _ in range(20))]
        ps = paths(edges, 0, 6)
        if ps:
            assert canonical_exact_route(edges, 0, 6) == min(ps)[:3][2]
            checked += 1
    print('D exact-additive tight-edge reconstruction against node-simple oracle:', checked, 'graphs, 0 mismatches')

    # Destination id comes before route, even with identical numeric totals.
    ja = Journey(1., 1., 0, 'a', ((9,),))
    jz = Journey(1., 1., 1, 'z', ((0,),))
    assert min([jz, ja], key=lambda j: (j.cost, *j.rank_key)).destination_id == 'a'
    print('D equal pair, route-first would choose z; full normative rank chooses a')

    # Persisted path identity can change a geometry-derived diagnostic while totals stay fixed.
    xy = {0: (0., 0.), 1: (1., 1.), 2: (1., -1.), 3: (2., 0.)}
    weighted_diamond = [(0, 1, 2., 2.), (1, 3, 0., 0.), (0, 2, 1., 1.), (2, 3, 1., 1.)]
    graph = ToyGraph(tuple(ToyEdge(u, v, (xy[u], xy[v]), t, c, oneway=True)
                           for u, v, t, c in weighted_diamond))
    js = journeys(graph, xy[0], [xy[3]], ['z'])
    upper = min((j for j in js if j.route[0][1] == 1), key=lambda j: j.rank_key)
    lower = min((j for j in js if j.route[0][1] == 2), key=lambda j: j.rank_key)
    assert upper.cost == lower.cost == upper.time_s == lower.time_s == 2.
    # Declared boundary band y >= 0: upper edges are wholly in it; lower touch at endpoints only.
    def share(j):
        lengths = [math.dist(xy[r[0]], xy[r[1]]) for r in j.route]
        touches = [a if min(xy[r[0]][1], xy[r[1]][1]) >= 0 else 0.
                   for a, r in zip(lengths, j.route)]
        return math.fsum(touches) / math.fsum(lengths)
    assert (share(upper), share(lower)) == (1., 0.)
    assert evaluate(graph, xy[0], [xy[3]], ['z']).objective2_route == upper.route
    assert spike.lexicographic(spike.adjacency(weighted_diamond), 0, 3) == (2., 2., (0, 2, 3))
    print('D same totals (2,2), normative upper route versus actual lex lower route: declared-band length share 100% versus 0%')

    zero = ToyGraph((ToyEdge(0, 1, ((0., 0.), (100., 0.), (100., 100.),
                                   (0., 100.), (0., 0.), (100., 0.)),
                             0., 0., oneway=True),))
    samples = journeys(zero, (25., 0.), [(75., 0.)], ['z'])
    assert len(samples) == 3 and len({j.rank_key for j in samples}) == 1
    print('D ONE query, identical full normative rank, three direct traversal lengths: 50 m, 450 m, 50 m')
    return {'graphs': n, 'claimed_route_ties': ambiguous, 'distinct_node_route_ties': distinct,
            'duplicate_only': ambiguous - distinct, 'actual_route_mismatches': actual_wrong,
            'canonical_reconstruction_checked': checked, 'boundary_share': [1., 0.]}


def e_population():
    rows = {}
    for name, width, continuous in [('narrow', 2, False), ('original_width_4', 4, False),
                                     ('wide', 10000, False), ('continuous', 4, True)]:
        rng = random.Random(41005)
        count = wrong = ties = spike_wrong = 0
        for _ in range(2000):
            n = rng.choice([5, 6, 7])
            edges = spike.random_graph(rng, n, rng.randrange(3, 9), width)
            if continuous:
                edges = [(u, v, rng.random() * 4, rng.random() * 4) for u, v, _, _ in edges]
            ps = paths(edges, 0, n - 1)
            if not ps:
                continue
            count += 1
            truth = min(ps)
            co = spike.cost_only(spike.adjacency(edges), 0, n - 1)
            spike_truth = min(spike.all_simple(spike.adjacency(edges), 0, n - 1))
            spike_wrong += co[0] == spike_truth[0] and co[1] != spike_truth[1]
            # Count the spike's advertised conditional event, with the correct oracle.
            wrong += co[0] == truth[0] and co[1] != truth[1]
            ties += len({p for c, t, p, *_ in ps if (c, t) == truth[:2]}) > 1
        rows[name] = {'compared': count, 'spike_oracle_right_cost_wrong_time': spike_wrong,
                      'spike_oracle_rate_percent': 100 * spike_wrong / count,
                      'whole_term_oracle_right_cost_wrong_time': wrong,
                      'whole_term_oracle_rate_percent': 100 * wrong / count, 'distinct_route_ties': ties}
        print('E', name, rows[name])
    return rows


def f_recommendation():
    edges = diamond(1000.)
    left_truth = min(spike.all_simple(spike.adjacency(edges), 0, 4))
    left_lex = spike.lexicographic(spike.adjacency(edges), 0, 4)
    assert left_truth[1] == 2. and left_lex[1] == 1001.
    print('F edge-by-edge cost amendment alone still fails secondary time:', left_truth, 'versus', left_lex)
    results = []
    for es in [edges, list(reversed(edges))]:
        truth = min(paths(es, 0, 4))[:3]
        bd, width = spike.band(spike.adjacency(es), 0, 4)
        results.append({'truth': truth, 'band': bd, 'widest': width})
        print('F order-dependent equal-minimum band:', results[-1])
    assert results[0]['band'][1] == 2. and results[1]['band'][1] == 1001.

    # Fourth option prototype: exact-cost-ordered simple alternatives, stop above winning RN bucket.
    # Enumeration here materializes paths; this validates the stopping rule, NOT scalability.
    def bucket_search(es):
        candidates = paths(es, 0, 4)
        ordered = sorted(candidates, key=lambda p: sum(map(Fraction, p[4]), Fraction()))
        rounded_min = ordered[0][0]
        finalists = []
        for p in ordered:
            if p[0] > rounded_min:
                break
            finalists.append(p)
        return min(finalists)[:3], len(finalists)

    repaired, examined = bucket_search(edges)
    assert repaired == min(paths(edges, 0, 4))[:3]
    print('F exact-cost alternatives within minimum rounded-cost bucket:', repaired,
          '; finalists:', examined, '; no rule amendment')
    return {'band_orders': results, 'bucket_search': repaired, 'finalists': examined}


SECTIONS = {'A': a_journeys, 'B': b_baseline, 'C': c_numeric,
            'D': d_routes, 'E': e_population, 'F': f_recommendation}

if __name__ == '__main__':
    names = sys.argv[1:] or list(SECTIONS)
    for name in names:
        print('\n=== CLAIM', name, '===')
        SECTIONS[name]()
