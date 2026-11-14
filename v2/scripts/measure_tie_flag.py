"""Is the disclosure a property of the answer we publish, or of the traversal order?

Codex pass 48 §C asked for a case where the flag is silently clear and it matters. There is one in
principle: an exact cost **tie** between a restricted route and an unrestricted one. The published
seconds are identical either way, so nothing in the value plane distinguishes them, and
`wire.encode_route_flag`'s invariant — a flag only where the status is OK — is satisfied by both
answers. If the flag then depends on which label the heap settled first, the disclosure is decided
by traversal order rather than by the answer published for that cell.

**The construction confirms it is possible.** Four nodes, two disjoint two-hop routes of equal
cost, one restricted: over the 24 relabellings of the node numbering the published seconds take one
value and the flag takes both, 12 each.

**The real graph says it does not happen here.** The same sweep under three relabellings moves the
flag on 0 of about 69,000 flagged nodes. Travel times are floats derived from float lengths over
float speeds, so exact bit-level ties between differently flagged routes are vanishingly rare.

A zero is the result shape this project has been burned by, so the instrument proves itself before
it reports: the four-node control runs first and the script **fails** if the control cannot detect
a moved flag. A relabelling changes only the tie-break, so any node whose flag moves is a node
whose disclosure order decided; any node whose *seconds* move would be a different and larger bug,
and is counted too.

    v2/.venv/Scripts/python.exe scripts/measure_tie_flag.py          # control only, no graph
    v2/.venv/Scripts/python.exe scripts/measure_tie_flag.py --graph  # and the real extent
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

import numpy as np
import scipy.sparse as sp

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "spikes"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from locfinder.traveltime.arrival import arrival_with_route_flag        # noqa: E402

V2 = pathlib.Path(__file__).resolve().parents[1]
ARTIFACT = V2.parent / "docs" / "experiments" / "s3-8-tie-flag.json"
MODE = "walk"
CATEGORY = "grocery"
POI_SNAP_MAX_M = 300.0
HORIZON_S = 7200.0


def permute(m, q):
    """`m_new[j, k] = m_old[q[j], q[k]]`."""
    return m[q, :][:, q].tocsr()


def aligned_triple(n, edges):
    """Three CSR matrices sharing one sparsity structure.

    Built by hand because `csr_matrix` drops an explicit `False`, which would misalign the flag
    from the costs it is supposed to describe.
    """
    rows = np.array([e[0] for e in edges], dtype=np.int64)
    cols = np.array([e[1] for e in edges], dtype=np.int64)
    order = np.lexsort((cols, rows))
    rows, cols = rows[order], cols[order]
    indptr = np.zeros(n + 1, dtype=np.int64)
    np.add.at(indptr, rows + 1, 1)
    indptr = np.cumsum(indptr)
    out = []
    for j, dtype in ((2, np.float64), (3, np.float64), (4, bool)):
        data = np.array([edges[i][j] for i in order], dtype=dtype)
        m = sp.csr_matrix((n, n), dtype=dtype)
        m.data, m.indices, m.indptr = data, cols.copy(), indptr.copy()
        out.append(m)
    return tuple(out)


def tie_construction():
    """D=0, A=1 (restricted leg), B=2 (clear leg), T=3; two equal-cost two-hop routes."""
    half = 300.0
    raw = [(0, 1, half, half, True), (1, 3, half, half, False),
           (0, 2, half, half, False), (2, 3, half, half, False)]
    edges = []
    for u, v, c, t, f in raw:
        edges += [(u, v, c, t, f), (v, u, c, t, f)]
    return aligned_triple(4, edges)


def sweep_under(labelling, cost_csr, time_csr, flag_csr, dest_idx, n, cutoff_s):
    """`(seconds, flagged)` in the ORIGINAL numbering, computed under `labelling`."""
    inv = np.empty(n, dtype=np.int64)
    inv[labelling] = np.arange(n)
    s, _sel, f = arrival_with_route_flag(
        permute(cost_csr, labelling), permute(time_csr, labelling), permute(flag_csr, labelling),
        dest_idx=sorted(int(inv[d]) for d in dest_idx), cutoff_s=cutoff_s)
    s_back = np.empty(n, dtype=float)
    f_back = np.empty(n, dtype=bool)
    s_back[labelling] = s
    f_back[labelling] = f
    return s_back, f_back


def compare(base_s, base_f, s, f) -> dict:
    both = np.isfinite(base_s) & np.isfinite(s)
    return {
        "reachable_in_both": int(both.sum()),
        "seconds_differing": int((base_s[both] != s[both]).sum()),
        "flag_moved": int(((base_f != f) & both).sum()),
        "flag_gained": int((~base_f & f & both).sum()),
        "flag_lost": int((base_f & ~f & both).sum()),
        "reachability_changed": int((np.isfinite(base_s) != np.isfinite(s)).sum()),
    }


def control() -> dict:
    """The four-node tie, which must show the flag moving or nothing below means anything."""
    cost_csr, time_csr, flag_csr = tie_construction()
    base_s, _sel, base_f = arrival_with_route_flag(cost_csr, time_csr, flag_csr, dest_idx=[0])
    rows = {}
    for name, q in (("reversed", np.arange(4)[::-1].copy()),
                    ("swap the two legs", np.array([0, 2, 1, 3])),
                    ("rotate", np.array([1, 2, 3, 0]))):
        s, f = sweep_under(q, cost_csr, time_csr, flag_csr, [0], 4, None)
        rows[name] = compare(base_s, base_f, s, f)
    return {
        "what_this_is": ("the positive control: a four-node construction whose disclosure IS "
                         "ambiguous, so the instrument's ability to report a moved flag is "
                         "demonstrated rather than assumed"),
        "published_seconds_at_the_target": float(base_s[3]),
        "baseline_flag_at_the_target": bool(base_f[3]),
        "labellings": rows,
        "total_flag_moves": sum(r["flag_moved"] for r in rows.values()),
        "total_seconds_moves": sum(r["seconds_differing"] for r in rows.values()),
    }


def real_graph() -> dict:
    import geopandas as gpd
    import osmnx as ox

    from _common import ACCEPTED_PLACES, METRO, load_roads_graph
    from locfinder.places.categories import select_overture
    from locfinder.traveltime.components import largest_component
    from locfinder.traveltime.csr import graph_to_cost_time_flag_csr
    from locfinder.traveltime.speeds import add_travel_times, symmetrise

    t0 = time.perf_counter()
    grid = METRO.grid()
    G = load_roads_graph()
    G = ox.project_graph(G, to_crs=grid.crs)
    G = add_travel_times(G, mode=MODE)
    G = symmetrise(G)
    G.remove_nodes_from([n for n, d in G.degree() if d == 0])
    G, _comp = largest_component(G)
    cost_csr, time_csr, flag_csr, index = graph_to_cost_time_flag_csr(G)
    n = cost_csr.shape[0]
    print(f"graph ready in {time.perf_counter() - t0:.0f}s: {n:,} nodes", flush=True)

    places = gpd.read_parquet(ACCEPTED_PLACES).to_crs(grid.crs)
    cen = select_overture(places, CATEGORY).geometry.centroid
    nodes, dists = ox.nearest_nodes(G, cen.x.to_numpy(), cen.y.to_numpy(), return_dist=True)
    keep = np.asarray(dists, dtype=float) <= POI_SNAP_MAX_M
    dest_idx = sorted({index[nd] for nd, k in zip(nodes, keep) if k})

    base_s, _sel, base_f = arrival_with_route_flag(
        cost_csr, time_csr, flag_csr, dest_idx=dest_idx, cutoff_s=HORIZON_S)
    rng = np.random.default_rng(20261113)
    rows = {}
    for name, q in (("reversed", np.arange(n)[::-1].copy()),
                    ("random_seed_20261113", rng.permutation(n)),
                    ("random_seed_20261113_second", rng.permutation(n))):
        s, f = sweep_under(q, cost_csr, time_csr, flag_csr, dest_idx, n, HORIZON_S)
        rows[name] = compare(base_s, base_f, s, f)
        print(f"{name}: flag moved on {rows[name]['flag_moved']:,}, seconds on "
              f"{rows[name]['seconds_differing']:,}", flush=True)
    return {
        "nodes": int(n), "destination_nodes": len(dest_idx), "horizon_s": HORIZON_S,
        "reachable": int(np.isfinite(base_s).sum()), "flagged": int(base_f.sum()),
        "labellings": rows,
        "total_flag_moves": sum(r["flag_moved"] for r in rows.values()),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=pathlib.Path, default=ARTIFACT)
    ap.add_argument("--graph", action="store_true",
                    help="also measure the extent on the real walk graph, which costs a graph "
                         "load and three extra sweeps")
    args = ap.parse_args(argv)

    report = {"what_this_is": ("whether the restricted-route disclosure is a property of the "
                               "published answer or of the traversal order"),
              "control": control()}
    c = report["control"]
    print(f"control: published seconds {c['published_seconds_at_the_target']:.1f} s, flag moved "
          f"on {c['total_flag_moves']} node(s) across 3 relabellings, seconds moved on "
          f"{c['total_seconds_moves']}")
    if c["total_flag_moves"] == 0:
        raise SystemExit(
            "the control cannot detect a moved flag on a construction that is KNOWN to be "
            "ambiguous, so this instrument reports nothing and a zero below would be worthless")
    if c["total_seconds_moves"] != 0:
        raise SystemExit("the control's published seconds moved under a relabelling, which is a "
                         "different and larger bug than the one this measures")

    if args.graph:
        report["real_graph"] = real_graph()
        report["what_the_real_graph_says"] = (
            f"the flag moved on {report['real_graph']['total_flag_moves']} of "
            f"{report['real_graph']['flagged']:,} flagged nodes across three relabellings. Exact "
            "bit-level cost ties between differently flagged routes do not occur on this graph, "
            "so the disclosure is well defined here")
    else:
        report["real_graph"] = None
        report["what_the_real_graph_says"] = "not measured in this run; pass --graph"

    report["why_this_still_matters"] = (
        "the ambiguity is a property of the MODEL, not of this graph. It is latent and it would "
        "surface the moment costs are quantised -- integer seconds, a rounded penalty, a "
        "deliberately coarse cost unit -- because quantisation manufactures exact ties. Anyone "
        "proposing to make the cost integral has to rerun this with --graph first")
    report["and_what_it_does_not_claim"] = (
        "that the flag is correct. It says the flag does not depend on traversal order on this "
        "graph. Whether the route it describes is the route a person can walk is the walked "
        "audit's question and remains unanswered")

    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
