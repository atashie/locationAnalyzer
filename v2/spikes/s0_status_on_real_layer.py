"""Phase 1 S0 verification on real data.

Three things, all on the shipped Triangle configuration:

1. **What statuses the production builder actually produces.** Unit tests prove the code can emit
   all four per-cell reasons. That is not the same as the build emitting them, and the
   `expansion.py` lesson was exactly that gap. Runs through `layer.build_layer_surface` — the
   provenance-returning builder — and compares the seconds against the committed artifact.

2. **Whether `NO_PATH` is reachable at all in that configuration.** `speeds.symmetrise` runs before
   `components.largest_component`, so the retained walk component should be *strongly* connected
   and every destination is snapped on the pruned graph, in which case no retained node is
   unreachable and `NO_PATH` cannot occur however correct its code path is.

3. **How far the category surface is from a true minimum over destinations** (Codex pass-8 H2).
   `arrival_seconds_two_weight` picks the destination nearest by **cost** and reports that path's
   time, so the surface is an upper bound on `min_d t(cell -> d)`, not that minimum. Both sides of
   the bracket are one Dijkstra:

       time_min  <=  the best time over a legal route  <=  cost_selected

   so the gap is measurable directly, and what matters is not the gap in seconds but how many
   cells it moves across a real threshold.

Run from v2/:  uv run python spikes/s0_status_on_real_layer.py grocery walk
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import geopandas as gpd
import networkx as nx
import numpy as np
import osmnx as ox

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ACCEPTED_PLACES, GRAPH_CACHE, GRID, METRO, append_results, layer_path, stamp  # noqa: E402
from locfinder import profile, status as st  # noqa: E402
from locfinder.places.categories import select_overture  # noqa: E402
from locfinder.status import Criterion, Outcome, Reason, Surface  # noqa: E402
from locfinder.traveltime.arrival import arrival_seconds  # noqa: E402
from locfinder.traveltime.components import largest_component  # noqa: E402
from locfinder.traveltime.csr import graph_to_cost_time_csr  # noqa: E402
from locfinder.traveltime.layer import build_layer_surface  # noqa: E402
from locfinder.traveltime.snap import EdgeIndex, cell_arrival_with_provenance  # noqa: E402
from locfinder.traveltime.speeds import add_travel_times, symmetrise  # noqa: E402

POI_SNAP_MAX_M = 300.0   # matches g1_own_graph_layer.py
MAX_ACCESS_M = 200.0
CUTOFF_MIN = 120.0
HORIZON_S = CUTOFF_MIN * 60.0
THRESHOLDS_MIN = (10, 15, 25, 45)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("category")
    ap.add_argument("mode", choices=["walk", "bike", "drive"])
    ap.add_argument("--allow-artifact-mismatch", action="store_true",
                    help="do not fail when the committed artifact disagrees; for the window "
                         "between changing inputs and rebuilding it")
    args = ap.parse_args()
    out: dict = {"metro": METRO.name, "category": args.category, "mode": args.mode}

    t = time.perf_counter()
    G = ox.load_graphml(GRAPH_CACHE)
    print(f"graph loaded in {time.perf_counter() - t:.1f}s: {G.number_of_nodes()} nodes", flush=True)

    t = time.perf_counter()
    G = ox.project_graph(G, to_crs=GRID.crs)
    G = add_travel_times(G, mode=args.mode)
    if args.mode == "walk":
        G = symmetrise(G)
    G.remove_nodes_from([n for n, d in G.degree() if d == 0])
    G, comp = largest_component(G)
    out["components"] = comp.summary
    print(f"prepared in {time.perf_counter() - t:.1f}s: {comp.summary}", flush=True)

    # Claim 2, measured rather than argued.
    n_strong = nx.number_strongly_connected_components(G)
    out["strongly_connected_components_after_pruning"] = n_strong
    print(f"strongly connected components: {n_strong}", flush=True)

    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
    places = gpd.read_parquet(ACCEPTED_PLACES).to_crs(GRID.crs)
    sel = select_overture(places, args.category)
    cent = sel.geometry.centroid
    nodes, dists = ox.nearest_nodes(G, cent.x.to_numpy(), cent.y.to_numpy(), return_dist=True)
    keep = np.asarray(dists) <= POI_SNAP_MAX_M
    dest_idx = sorted({index[n] for n, k in zip(nodes, keep) if k})
    out["destinations"] = {"places": int(len(sel)), "nodes": len(dest_idx),
                           "dropped_beyond_snap": int((~keep).sum())}
    print(f"destinations: {len(dest_idx)} nodes from {len(sel)} places", flush=True)

    eidx = EdgeIndex.from_graph(G, index)
    timings: dict = {}

    # ---- claim 1: the production builder, with provenance ------------------------------------
    surf = build_layer_surface(
        G, (cost_csr, time_csr), index, GRID, dest_idx=dest_idx, mode=args.mode,
        target=args.category, engine="own-graph", cutoff_min=CUTOFF_MIN,
        max_access_m=MAX_ACCESS_M, timings=timings, edge_index=eidx,
        places_selected=len(sel),
    )
    print(f"build_layer_surface + validate(): PASS  {timings}", flush=True)

    total = surf.reason.size
    hist = {Reason(int(v)).name: int(c)
            for v, c in zip(*np.unique(surf.reason, return_counts=True))}
    out["cells"] = {"total": int(total), "histogram": hist,
                    "shares": {k: v / total for k, v in hist.items()}}
    print("status histogram:", flush=True)
    for k, v in sorted(hist.items(), key=lambda kv: -kv[1]):
        print(f"  {k:<16} {v:>9,}  {v / total:7.4%}", flush=True)

    node_unreached = int((~np.isfinite(arrival_seconds(cost_csr, dest_idx=dest_idx))).sum())
    out["nodes"] = {"total": cost_csr.shape[0], "unreached": node_unreached}
    print(f"nodes unreached by the unbounded cost search: {node_unreached:,} of "
          f"{cost_csr.shape[0]:,}", flush=True)

    # ---- the seconds must be unchanged from the committed artifact ---------------------------
    prev_path = layer_path("own", args.category, args.mode, ".npy")
    if prev_path.exists():
        prev = np.load(prev_path)
        # The artifact is float32. Quantisation is therefore not an unknown error to be absorbed by
        # a tolerance: it is a *known function*, so the honest test is whether this run's seconds
        # round to the stored bytes exactly. A 0.01 s tolerance accepted stored 600.005 against
        # rebuilt 599.999 — a difference that straddles a 600-second threshold and so changes the
        # published answer (Codex pass-12 L1). Exact equality after the same cast cannot do that.
        rebuilt32 = surf.seconds.astype(np.float32)
        both = np.isfinite(prev) & np.isfinite(rebuilt32)
        out["against_committed_artifact"] = {
            "path": prev_path.name,
            "finiteness_identical": bool(np.array_equal(np.isfinite(prev),
                                                        np.isfinite(rebuilt32))),
            "float32_identical": bool(np.array_equal(prev, rebuilt32, equal_nan=True)),
            "cells_differing": int((prev[both] != rebuilt32[both]).sum()) if both.any() else 0,
            "max_abs_diff_s": float(np.abs(prev[both].astype(np.float64)
                                           - rebuilt32[both].astype(np.float64)).max())
            if both.any() else 0.0,
            "verification_bypassed": bool(args.allow_artifact_mismatch),
        }
        a = out["against_committed_artifact"]
        print(f"vs {a['path']}: float32 identical={a['float32_identical']}, "
              f"finiteness identical={a['finiteness_identical']}, "
              f"{a['cells_differing']:,} cells differ, max abs diff "
              f"{a['max_abs_diff_s']:.6f} s", flush=True)
        # Assert, do not merely print (Codex pass-11 L1). This check reported
        # `finiteness identical=False` with a 4,091 s maximum difference during the re-acquisition
        # and the script carried on to write a full report and exit 0 — a verification that cannot
        # fail is not a verification. `--allow-artifact-mismatch` is for the window between
        # changing the inputs and rebuilding the artifact, when the two genuinely describe
        # different destination sets; the report records that it was used, so a result produced
        # under the bypass cannot be read as verified.
        if args.allow_artifact_mismatch:
            print("NOTE: --allow-artifact-mismatch given, so provenance was NOT verified against "
                  "the committed artifact; `verification_bypassed` is recorded in the report.",
                  flush=True)
        elif not a["float32_identical"]:
            raise SystemExit(
                f"artifact mismatch: {prev_path.name} does not match this run "
                f"(finiteness identical={a['finiteness_identical']}, {a['cells_differing']:,} "
                f"cells differ, max abs diff {a['max_abs_diff_s']:.3f} s). The artifact was almost "
                "certainly built from a different destination set; rebuild it with "
                "g1_own_graph_layer.py, or pass --allow-artifact-mismatch if the difference "
                "is expected.")
    else:
        print(f"NOTE: {prev_path.name} is absent, so provenance was NOT verified against a "
              "committed artifact.", flush=True)

    # ---- claim 3: the H2 bracket -------------------------------------------------------------
    # The lower side: min over destinations of real time, access cost ignored entirely.
    T_time = arrival_seconds(time_csr, dest_idx=dest_idx)
    lo_secs, lo_reason, lo_lower = cell_arrival_with_provenance(
        eidx, T_time, *GRID.cell_centers_xy(), mode=args.mode, max_access_m=MAX_ACCESS_M,
        horizon_s=HORIZON_S, node_reason=st.node_reasons(T_time, st.ENGINES["own-graph"],
                                                         search_bounded=False),
        node_cost=None,
    )
    lo = Surface(mode=args.mode, engine="own-graph", target=args.category,
                 aggregation=st.CATEGORY_TIME_MIN, horizon_s=HORIZON_S,
                 seconds=lo_secs, reason=lo_reason, min_possible_s=lo_lower).validate()

    both_ok = (surf.reason == Reason.OK) & (lo.reason == Reason.OK)
    gap = surf.seconds[both_ok] - lo.seconds[both_ok]
    assert gap.min() >= -1e-6, f"the bracket is inverted somewhere: min gap {gap.min()}"
    differ = gap > 1.0
    bracket = {
        "cells_comparable": int(both_ok.sum()),
        "cells_differing_by_over_1s": int(differ.sum()),
        "share_differing": float(differ.mean()),
        "gap_s_median_where_differing": float(np.median(gap[differ])) if differ.any() else 0.0,
        "gap_s_p90_where_differing": float(np.percentile(gap[differ], 90)) if differ.any() else 0.0,
        "gap_s_max": float(gap.max()),
        "verdict_flips": {},
    }
    for tm in THRESHOLDS_MIN:
        c_hi = Criterion(label=f"{tm}min", mode=args.mode, target=args.category,
                         kind="category", threshold_s=tm * 60.0)
        hi_out = st.evaluate(c_hi, surf)
        lo_out = st.evaluate(c_hi, lo)
        # cells the shipped (upper-bound) surface excludes but the lower bound would include
        flipped = int(((hi_out == Outcome.FAIL) & (lo_out == Outcome.PASS)).sum())
        passing = int((lo_out == Outcome.PASS).sum())
        bracket["verdict_flips"][f"{tm}min"] = {
            "excluded_by_cost_selected_but_passing_on_time_min": flipped,
            "passing_on_time_min": passing,
            "share_of_passing": flipped / passing if passing else 0.0,
        }
    out["h2_bracket"] = bracket
    print("\nH2 bracket (cost-selected minus time-min, seconds):", flush=True)
    print(f"  comparable cells {bracket['cells_comparable']:,}; differing by >1 s "
          f"{bracket['cells_differing_by_over_1s']:,} ({bracket['share_differing']:.4%})", flush=True)
    print(f"  where differing: median {bracket['gap_s_median_where_differing']:.1f} s, "
          f"p90 {bracket['gap_s_p90_where_differing']:.1f} s; max {bracket['gap_s_max']:.1f} s", flush=True)
    for tm, v in bracket["verdict_flips"].items():
        print(f"  at {tm}: {v['excluded_by_cost_selected_but_passing_on_time_min']:,} cells "
              f"excluded that the lower bound would include "
              f"({v['share_of_passing']:.4%} of the {v['passing_on_time_min']:,} passing)", flush=True)

    out["versions"] = {"profile": profile.profile_version(), "grid": profile.grid_version(GRID)}
    dest_path = Path("data") / f"s0_status_{METRO.name}_{args.category}_{args.mode}.json"
    dest_path.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\nwrote {dest_path}", flush=True)

    lines = [f"### S0 status provenance and the H2 bracket: {args.category} / {args.mode} ({stamp()})", "",
             f"- graph after preparation: {comp.summary}; **{n_strong} strongly connected component(s)**",
             f"- destinations: {len(dest_idx)} nodes from {len(sel)} places "
             f"({int((~keep).sum())} beyond the {POI_SNAP_MAX_M:.0f} m snap bound)",
             f"- nodes unreached by the unbounded cost search: **{node_unreached:,}** of "
             f"{cost_csr.shape[0]:,}",
             f"- `build_layer_surface(...).validate()` passes on {total:,} cells", "",
             "| status | cells | share |", "|---|---|---|"]
    for k, v in sorted(hist.items(), key=lambda kv: -kv[1]):
        lines.append(f"| `{k}` | {v:,} | {v / total:.4%} |")
    if "against_committed_artifact" in out:
        a = out["against_committed_artifact"]
        lines += ["", f"- against the committed `{a['path']}`: finiteness identical="
                  f"**{a['finiteness_identical']}**, max abs diff {a['max_abs_diff_s']:.6f} s "
                  "(the artifact is float32, so a sub-millisecond difference is quantisation)"]
    lines += ["", "**The H2 bracket.** `cost_selected` (shipped) minus `time_min` (minimum over "
              "destinations, access cost ignored). The shipped surface is an upper bound, so the "
              "gap is where a category criterion could exclude a cell that a qualifying "
              "destination would have satisfied.", "",
              f"- comparable cells {bracket['cells_comparable']:,}; differing by more than 1 s "
              f"**{bracket['cells_differing_by_over_1s']:,} ({bracket['share_differing']:.4%})**",
              f"- where they differ: median **{bracket['gap_s_median_where_differing']:.1f} s**, "
              f"p90 {bracket['gap_s_p90_where_differing']:.1f} s, max {bracket['gap_s_max']:.1f} s", "",
              "| threshold | cells excluded by the shipped surface that the lower bound includes | share of passing cells |",
              "|---|---|---|"]
    for tm, v in bracket["verdict_flips"].items():
        lines.append(f"| {tm} | {v['excluded_by_cost_selected_but_passing_on_time_min']:,} | "
                     f"{v['share_of_passing']:.4%} |")
    lines += ["", f"- profile `{out['versions']['profile']}`, grid `{out['versions']['grid']}`", ""]
    append_results("g1-routing.md", "\n".join(lines))


if __name__ == "__main__":
    main()
