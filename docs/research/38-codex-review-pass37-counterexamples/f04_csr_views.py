"""F4: the production pair is one cost-selected view, with missing reference behavior."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "v2"))
import networkx as nx
from locfinder.traveltime.csr import graph_to_cost_time_csr
from locfinder.measure.toy import ToyEdge, ToyGraph


def pair(edges):
    g = nx.MultiDiGraph()
    for time, cost in edges:
        g.add_edge(0, 1, travel_time=time, cost=cost)
    c, t, ix = graph_to_cost_time_csr(g)
    return float(c[ix[0], ix[1]]), float(t[ix[0], ix[1]])


def main():
    actual = pair(((1., 100.), (10., 10.)))
    assert actual == (10., 10.)
    print(f"ACTUAL production pair={actual}; objective 1 needs time=1, erased from both matrices")
    a = pair(((10., 50.), (1., 50.)))
    b = pair(((1., 50.), (10., 50.)))
    assert a[1] == 10. and b[1] == 1.
    print(f"ACTUAL equal-cost insertion order changes selected time: {a[1]} vs {b[1]}; normative=1")
    # Nonnegative, including zero, is the declared reference domain.
    ToyGraph((ToyEdge(0, 1, ((0., 0.), (1., 0.)), 0., 0.),))
    try:
        pair(((0., 0.),))
    except ValueError as exc:
        print(f"ACTUAL admissible zero-weight reference edge rejected by production CSR: {exc}")
    else:
        raise AssertionError("expected production rejection")
    print("PASS F4: paired weights alone lack objective views, normative tie choice, and zero-weight support")


if __name__ == "__main__":
    main()
