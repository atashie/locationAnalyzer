"""Read-only imports and independent term-preserving oracle; no temporary files."""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'v2'), str(ROOT / 'v2/scripts')]

import spike_search_semantics as spike
import math


def paths(edges, start, goal, limit=400_000):
    """Keep individual terms and edge indices; round once only at the whole path."""
    adj = {}
    for i, (u, v, t, c) in enumerate(edges):
        adj.setdefault(u, []).append((i, v, t, c))
    stack = [(start, (start,), (), (), ())]
    out = []
    while stack:
        u, ns, ts, cs, ids = stack.pop()
        if u == goal:
            out.append((math.fsum(cs), math.fsum(ts), ns, ids, cs, ts))
            if len(out) > limit:
                raise RuntimeError('path limit')
            continue
        for i, v, t, c in adj.get(u, ()):
            if v not in ns:
                stack.append((v, ns + (v,), ts + (t,), cs + (c,), ids + (i,)))
    return out


def original_population():
    import random
    rng = random.Random(20261112)
    for _ in range(4000):
        n = rng.choice([5, 6, 7])
        edges = spike.random_graph(rng, n, rng.randrange(3, 9), rng.choice([3, 4, 6]))
        yield n, edges


def diamond(scale=1.0):
    # Q is strictly costlier at the merge. Its gap is half an ulp of the final cost.
    half = scale / 2
    expensive_half = math.nextafter(math.nextafter(half, math.inf), math.inf)
    return [(0, 1, 500., half), (1, 3, 500., half),
            (0, 2, .5, half), (2, 3, .5, expensive_half), (3, 4, 1., scale)]
