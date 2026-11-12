"""F3: scalar node labels do not implement rounded whole-journey ties."""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "v2"))
import networkx as nx
from scipy.sparse.csgraph import dijkstra
from locfinder.traveltime.csr import graph_to_cost_time_csr
from locfinder.measure.toy import ToyEdge, ToyGraph, evaluate


def main():
    # Distinct prefix paths (not parallel edges); suffix cost swallows their cost difference.
    rows = [(0, 1, .5, 500.), (1, 3, .5, 500.),
            (0, 2, .5, .5), (2, 3, .5000000000000002, .5), (3, 4, 2.**54, 1.)]
    xy = {0: (0., 0.), 1: (1., 1.), 2: (1., -1.), 3: (2., 0.), 4: (3., 0.)}
    reference_graph = ToyGraph(tuple(ToyEdge(u, v, (xy[u], xy[v]), t, c, oneway=True)
                                    for u, v, c, t in rows))
    oracle = evaluate(reference_graph, xy[0], [xy[4]])
    assert oracle.objective2_s == 2.
    g = nx.MultiDiGraph()
    for u, v, c, t in rows:
        g.add_edge(u, v, cost=c, travel_time=t)
    cost, time, ix = graph_to_cost_time_csr(g)
    _, pred = dijkstra(cost, directed=True, indices=ix[0], return_predecessors=True)
    j = ix[4]
    selected_time = 0.
    while j != ix[0]:
        i = int(pred[j])
        selected_time += float(time[i, j])
        j = i
    p = math.fsum((.5, .5, 2.**54))
    q = math.fsum((.5, .5000000000000002, 2.**54))
    assert p == q == 2.**54
    assert math.fsum((.5, .5)) < math.fsum((.5, .5000000000000002))
    assert selected_time == 1001.
    print(f"ACTUAL final fsum costs tie at {p!r}; normative time key selects Q=2 s PASS")
    print(f"ACTUAL scalar prefix search discards Q at merge, returns P={selected_time} s FAIL")
    # Independently show left accumulation can change even a final cost.
    assert math.fsum((2.**53, 1., 1.)) == 2.**53 + 2.
    left = 0.
    for term in (2.**53, 1., 1.):
        left += term
    assert left != math.fsum((2.**53, 1., 1.))
    print("PASS F3: post-hoc fsum/reconstruction or a local cost/time tie key cannot restore a discarded prefix")


if __name__ == "__main__":
    main()
