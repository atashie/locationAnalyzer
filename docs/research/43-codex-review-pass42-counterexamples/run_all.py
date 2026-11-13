"""Codex pass 42's reproducers against the suffix-aware band, run from our own checkout.

Each block is the reviewer's, re-run here so the findings do not depend on their session. Run from
the repository root:

    v2/.venv/Scripts/python.exe -B docs/research/43-codex-review-pass42-counterexamples/run_all.py

The band has since been repaired, so F1's unsound-bound block still shows the bad answer (it is
reproducing the *refutation*, and the band still obeys a bound it is told to use), while F2's
overflow block now answers instead of raising. The expected lines are in RESULTS.txt.
"""
from __future__ import annotations

import dataclasses
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "v2"))
sys.path.insert(0, str(ROOT / "v2" / "scripts"))

import spike_suffix_band as b                          # noqa: E402
from locfinder.measure import toy                      # noqa: E402


def f1_a_time_threshold_is_not_a_cost_bound() -> dict:
    """HIGH. Cost is travel time plus access penalties. Scale the witness's costs 16x and leave
    its times alone: a band sized from a 600 s travel-time threshold reports 1,004 s where the
    rule says 5 s."""
    graph, origin, dests, ids = b.witness_graph()
    graph = toy.ToyGraph(tuple(dataclasses.replace(e, cost_base=16 * e.cost_base,
                                                   penalty=16 * e.penalty)
                               for e in graph.edges))
    oracle = b.oracle_answer(graph, origin, dests, ids)
    default = b.band_answer(graph, origin, dests, ids, both_bands=True)
    feasible = b.feasible_cost_bound(graph, origin, dests, ids)
    repaired = b.band_answer(graph, origin, dests, ids, both_bands=True, cost_ceiling=feasible)
    unsound = b.band_answer(graph, origin, dests, ids, both_bands=True, cost_ceiling=600.0)
    return {"oracle_cost": oracle["cost"], "oracle_seconds": oracle["time_s"],
            "graph_bound_seconds": default["time_s"],
            "feasible_cost_bound": feasible, "feasible_bound_seconds": repaired["time_s"],
            "unsound_600s_threshold_seconds": unsound["time_s"],
            "verdicts": {"normative": "PASS" if oracle["time_s"] <= 600 else "FAIL",
                         "from_the_threshold": "PASS" if unsound["time_s"] <= 600 else "FAIL"}}


def f2_an_admissible_graph_overflows_the_bound() -> dict:
    """HIGH. ToyGraph admits a single edge of cost 7e307 and the oracle answers it, while twice
    the graph total is infinite. Before the repair the band raised OverflowError; the bound now
    saturates at the largest finite binary64."""
    out = []
    for cost in (3e307, 7e307):
        graph = toy.ToyGraph((toy.ToyEdge(0, 1, ((0.0, 0.0), (1000.0, 0.0)),
                                          time_s=1.0, cost_base=cost, oneway=True),))
        args = (graph, (0.0, 0.0), [(1000.0, 0.0)], ["a"])
        oracle = b.oracle_answer(*args)
        try:
            got = b.band_answer(*args, both_bands=True)
            out.append({"edge_cost": cost, "oracle_cost": oracle["cost"],
                        "band_cost": got["cost"],
                        "agrees": b.agree(got, oracle, with_route=True), "raised": None})
        except OverflowError as exc:                 # pragma: no cover - the pre-repair behaviour
            out.append({"edge_cost": cost, "oracle_cost": oracle["cost"],
                        "band_cost": None, "agrees": False,
                        "raised": f"{type(exc).__name__}: {exc}"})
    return {"cases": out}


def f3_the_route_repair_is_exponential() -> dict:
    """HIGH. Equal costs on every arm, a different tiny time difference in each diamond: one cost
    bucket holding 2**k exact times, all inside the time band."""
    rows = b.price_equal_cost_chain([2, 4, 6, 8, 10, 12])
    return {"rows": rows,
            "closed_form_matches": [r["two_band_labels"] == 5 * 2 ** r["diamonds"] - 3
                                    for r in rows]}


def f4_the_band_is_a_prefix_pruning_search() -> dict:
    """MEDIUM. Two prefixes to one node, costs 1 and 2, a width of 1e-12. The cost-2 prefix is
    pruned. Retaining some strictly costlier prefixes does not stop this being prefix pruning."""
    from fractions import Fraction as F
    arcs = {0: [(1, F(1), F(1), (0, 1)), (1, F(2), F(2), (0, 1))]}
    starts = [b.Terminal(0, F(0), F(0), ())]
    sigma = b.exact_min_costs(arcs, starts)
    labels, _ = b.band_labels(arcs, starts, sigma, {0: 1e-12, 1: 1e-12}, cap=10)
    return {"labels_at_the_merge": [str(k) for k in labels[1]],
            "the_cost_2_prefix_was_pruned": len(labels[1]) == 1}


def f5_the_advertised_flag_did_not_exist() -> dict:
    """LOW. `--verify-totals` was named in the module docstring after the function behind it was
    replaced. The arithmetic it claimed to check is sound; only the flag was fiction."""
    import argparse
    try:
        b.main(["--verify-totals"])
        return {"still_advertised": True}
    except SystemExit as exc:
        # The docstring still NAMES the flag -- it now records that it never existed -- so the
        # test is whether it is offered, not whether the string appears.
        return {"argparse_rejects_it": True,
                "docstring_records_the_removal": "Pass 42 F5" in b.__doc__,
                "exit_code": exc.code if isinstance(exc.code, int) else str(exc.code)}
    except argparse.ArgumentError as exc:            # pragma: no cover
        return {"still_advertised": "--verify-totals" in b.__doc__, "error": str(exc)}


def main() -> int:
    out = {}
    for fn in (f1_a_time_threshold_is_not_a_cost_bound,
               f2_an_admissible_graph_overflows_the_bound,
               f3_the_route_repair_is_exponential,
               f4_the_band_is_a_prefix_pruning_search,
               f5_the_advertised_flag_did_not_exist):
        name = fn.__name__
        print(f"--- {name}")
        try:
            out[name] = fn()
        except SystemExit as exc:
            out[name] = {"SystemExit": str(exc)}
        print(json.dumps(out[name], indent=2, default=str))
    (pathlib.Path(__file__).parent / "results.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
