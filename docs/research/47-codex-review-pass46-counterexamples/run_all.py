"""Codex pass 46's reproducers, re-run from our own checkout.

    v2/.venv/Scripts/python.exe -B docs/research/47-codex-review-pass46-counterexamples/run_all.py

All four blocks run without a graph. The routed figures are read back from
`docs/experiments/s3-8-restricted-routes.json`.
"""
from __future__ import annotations

import json
import pathlib
import sys

import networkx as nx
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "v2"))

from locfinder.measure.e3 import Journey, score_e3                  # noqa: E402
from locfinder.traveltime.arrival import (arrival_with_selected_destination,  # noqa: E402
                                          arrival_with_route_flag)
from locfinder.traveltime.csr import (graph_to_cost_time_csr,        # noqa: E402
                                      graph_to_cost_time_flag_csr)
from locfinder.traveltime.snap import (EdgeIndex, cell_route_flag,   # noqa: E402
                                       cell_seconds_from_arrival)


def f1_the_predeclared_scorer_says_failed() -> dict:
    """HIGH, and the one that mattered: the report said UNVERIFIED while this existed."""
    r = score_e3([Journey("band15min_pass-03", 810.8186, 1500)])
    return {"outcome": str(r.outcome), "reasons": list(r.reasons),
            "median_difference_s": r.median_difference_s,
            "median_limit_s": r.median_limit_s,
            "one_observation_can_refute_what_it_cannot_confirm": True}


def f2_the_published_cell_is_a_different_unit() -> dict:
    """HIGH. Passes 44, 45 and 46 each caught a claim resting on the coordinate unit."""
    path = ROOT / "docs" / "experiments" / "s3-8-restricted-routes.json"
    if not path.exists():
        return {"note": "run v2/scripts/flag_restricted_routes.py"}
    d = json.loads(path.read_text(encoding="utf-8"))
    out = {}
    for unit in ("structures_at_their_own_coordinate", "structures_at_their_published_cell"):
        rows = d["units"][unit]["thresholds"]
        out[unit] = {t: {"included": r["included"],
                         "flagged": r["included_on_a_restricted_route"],
                         "share": round(r["share_of_included"], 4)}
                     for t, r in rows.items()}
    return out


def f3_a_point_at_an_endpoint_discloses_nothing() -> dict:
    """MEDIUM, a real defect: a journey existing is not the matched edge being walked."""
    G = nx.MultiDiGraph()
    G.add_node(0, x=0.0, y=0.0)
    G.add_node(1, x=100.0, y=0.0)
    G.add_edge(0, 1, travel_time=100.0, cost=220.0, access_restricted=True)
    idx = EdgeIndex.from_graph(G, {0: 0, 1: 1})
    x, y = np.array([0.0, 50.0, 100.0]), np.zeros(3)
    kw = dict(mode="walk", max_access_m=200.0, node_cost=np.array([220.0, 0.0]))
    seconds = cell_seconds_from_arrival(idx, np.array([100.0, 0.0]), x, y, **kw)
    flags = cell_route_flag(idx, np.array([100.0, 0.0]), x, y,
                            node_flag=np.array([True, False]), **kw)
    return {"seconds": [float(s) for s in seconds],
            "flags": [bool(f) for f in flags],
            "the_point_at_its_destination_is_not_flagged": not bool(flags[2])}


def f6_the_rule_selects_on_cost_not_on_walking_time() -> dict:
    """MEDIUM. "Walking time to the nearest grocery" is not what the implementation computes."""
    G = nx.MultiDiGraph()
    G.add_edge("home", "fast", cost=700.0, travel_time=500.0)
    G.add_edge("home", "slow", cost=650.0, travel_time=650.0)
    cost, time, index = graph_to_cost_time_csr(G)
    seconds, chosen = arrival_with_selected_destination(
        cost, time, dest_idx=[index["fast"], index["slow"]])
    names = list(index)
    return {"reported_seconds": float(seconds[index["home"]]),
            "selected": names[chosen[index["home"]]],
            "a_faster_journey_existed": 500.0}


def the_flag_rides_the_same_forest_as_the_time() -> dict:
    """What the reviewer could not break, kept as a standing check: among equal-cost paths the
    reported time is insertion-order dependent, and the flag must move WITH it rather than
    describing a different path."""
    out = []
    for order in (False, True):
        G = nx.MultiDiGraph()
        rows = [(0, 1, 100.0, 10.0, True), (0, 1, 100.0, 90.0, False)]
        for u, v, c, t, f in (reversed(rows) if order else rows):
            G.add_edge(u, v, cost=c, travel_time=t, access_restricted=f)
        G.add_edge(1, 2, cost=1.0, travel_time=1.0)
        cost, time, flag, index = graph_to_cost_time_flag_csr(G)
        sec, _sel, flg = arrival_with_route_flag(cost, time, flag, dest_idx=[index[2]])
        out.append({"reported_seconds": float(sec[index[0]]), "flagged": bool(flg[index[0]])})
    return {"both_orders": out,
            "time_and_flag_agree_in_each_order": all(
                (o["reported_seconds"] == 11.0) == o["flagged"] for o in out)}


def main() -> int:
    out = {}
    for fn in (f1_the_predeclared_scorer_says_failed,
               f2_the_published_cell_is_a_different_unit,
               f3_a_point_at_an_endpoint_discloses_nothing,
               f6_the_rule_selects_on_cost_not_on_walking_time,
               the_flag_rides_the_same_forest_as_the_time):
        print(f"--- {fn.__name__}")
        out[fn.__name__] = fn()
        print(json.dumps(out[fn.__name__], indent=2, default=str))
    (pathlib.Path(__file__).parent / "results.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
