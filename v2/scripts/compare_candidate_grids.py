"""Step 5 / S3.1 — **the matched 100 m / 200 m grid comparison**, the decision S3 exists to make.

**Why this cannot be done by sampling each grid at its own cell centres.** The two candidate grids
are **not nested**. `TRIANGLE.grid(100)` has origin 661900/4003500 and is 514 × 643;
`TRIANGLE.grid(200)` has origin 661800/4003600 and is 258 × 322. Their cell centres are different
places, so comparing each grid at its own centres confounds three things at once: resolution,
alignment, and which patch of ground was asked about. S3.1's requirement is one set of residential
coordinates evaluated against every candidate.

**So the unit here is a structure, not a cell.** Frame B's population — every Overture structure
centroid inside the published 100 m footprint — is evaluated three ways from **one** graph, one
destination set and one multi-source Dijkstra:

| value | what it is |
|---|---|
| `address` | the answer at the structure's own centroid. What the pipeline would say if it answered per address |
| `cell100` | the answer at the centre of the 100 m cell containing it. **What the product ships today** |
| `cell200` | the answer at the centre of the 200 m cell containing it |

Only the grid varies between the last two. The first is the reference the other two are measured against,
and it is what separates *grid* error from *model* error: `cell100 − address` is what the current
product already costs a household by answering for a cell, and `cell200 − cell100` is what the
candidate would add.

**Paired, signed, and never averaged into a single figure** (S3.2). A median of medians hides the
tail, and the tail is where a verdict flips. Every number below is either a count of structures or
a signed difference distribution.

**The verdict is what matters, not the seconds.** A 40-second difference changes nothing at a
10-minute threshold unless it crosses it, so the headline is the count of structures whose
INCLUDED/EXCLUDED/UNKNOWN answer *moves*, per threshold, on the **encoded** bytes the browser receives as
well as on the float seconds.

Outputs `docs/experiments/s3-1-candidate-grids.json` and the 200 m layer beside the 100 m one.

    python scripts/compare_candidate_grids.py --limit 20000     # a quick pass
    python scripts/compare_candidate_grids.py                   # the census
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import osmnx as ox

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "spikes"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import (ACCEPTED_PLACES, METRO, METRO_DIR,        # noqa: E402
                     load_roads_graph, stamp)
from locfinder import profile                                   # noqa: E402
from locfinder.grid import encode_minutes                       # noqa: E402
from locfinder.measure.frames import structure_population       # noqa: E402
from locfinder.places.categories import select_overture         # noqa: E402
from locfinder.status import (CATEGORY_COST_SELECTED, ENGINES,  # noqa: E402
                              Criterion, Reason, Surface, Verdict, evaluate,
                              node_reasons)
from locfinder.traveltime.components import largest_component   # noqa: E402
from locfinder.traveltime.csr import graph_to_cost_time_csr     # noqa: E402
from locfinder.traveltime.arrival import (arrival_seconds,      # noqa: E402
                                          arrival_seconds_two_weight)
from locfinder.traveltime.snap import (EdgeIndex,               # noqa: E402
                                       cell_arrival_with_provenance)
from locfinder.traveltime.speeds import add_travel_times, symmetrise  # noqa: E402

MODE = "walk"
CATEGORY = "grocery"
POI_SNAP_MAX_M = 300.0
MAX_ACCESS_M = 200.0
CUTOFF_MIN = 120.0
THRESHOLDS_MIN = (10, 15, 25, 45)
CANDIDATES = (100.0, 200.0)

V2 = Path(__file__).resolve().parents[1]
LAYERS = V2 / "data" / "layers"
ACCEPTED_BUILDINGS = METRO_DIR / "overture_buildings_accepted.parquet"
ARTIFACT = V2.parent / "docs" / "experiments" / "s3-1-candidate-grids.json"


# --------------------------------------------------------------------------- the one graph


def prepare():
    """Graph, CSRs, destination node indices — built **once**, so nothing but the grid varies."""
    t0 = time.perf_counter()
    G = load_roads_graph()
    G = ox.project_graph(G, to_crs=METRO.crs)
    G = add_travel_times(G, mode=MODE)
    if MODE == "walk":
        G = symmetrise(G)
    G.remove_nodes_from([n for n, d in G.degree() if d == 0])
    G, comp = largest_component(G)
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)

    places = gpd.read_parquet(ACCEPTED_PLACES).to_crs(METRO.crs)
    sel = select_overture(places, CATEGORY)
    cent = sel.geometry.centroid
    nodes, dists = ox.nearest_nodes(G, cent.x.to_numpy(), cent.y.to_numpy(), return_dist=True)
    keep = np.asarray(dists) <= POI_SNAP_MAX_M
    dest_idx = sorted({index[n] for n, k in zip(nodes, keep) if k})
    if not dest_idx:
        raise SystemExit("no routable destinations; the comparison would be vacuous")

    T = arrival_seconds_two_weight(cost_csr, time_csr, dest_idx=dest_idx)
    node_cost = arrival_seconds(cost_csr, dest_idx=dest_idx)
    idx = EdgeIndex.from_graph(G, index)
    reasons = node_reasons(T, ENGINES["own-graph"], search_bounded=False)
    meta = {"edges": G.number_of_edges(), "nodes": G.number_of_nodes(),
            "components": comp.summary, "places_selected": int(len(sel)),
            "destination_nodes": len(dest_idx),
            "prepared_s": round(time.perf_counter() - t0, 1)}
    return idx, T, node_cost, reasons, meta


def answer_at(idx, T, node_cost, reasons, xs, ys):
    """`(seconds, reason, min_possible_s)` at arbitrary projected coordinates.

    This is the same call `build_layer_surface` makes for its cell centres, with our own points in
    place of `grid.cell_centers_xy()`. Using the published builder's own evaluator is what makes
    the `address` column comparable to the two cell columns rather than a second implementation.
    """
    return cell_arrival_with_provenance(
        idx, T, np.asarray(xs, dtype=np.float64), np.asarray(ys, dtype=np.float64),
        mode=MODE, max_access_m=MAX_ACCESS_M, horizon_s=CUTOFF_MIN * 60.0,
        node_reason=reasons, node_cost=node_cost)


def surface_of(secs, reason, lower) -> Surface:
    return Surface(mode=MODE, engine="own-graph", target=CATEGORY,
                   aggregation=CATEGORY_COST_SELECTED, horizon_s=CUTOFF_MIN * 60.0,
                   seconds=np.asarray(secs), reason=np.asarray(reason),
                   min_possible_s=np.asarray(lower)).validate()


def verdicts(secs, reason, lower, threshold_min: int) -> np.ndarray:
    crit = Criterion(label=f"{CATEGORY}-{threshold_min}", mode=MODE, target=CATEGORY,
                     kind="category", threshold_s=float(threshold_min) * 60.0)
    return evaluate(crit, surface_of(secs, reason, lower))


def encoded_verdicts(secs, reason, threshold_min: int) -> np.ndarray:
    """The verdict a browser reaches from the **encoded byte**, which is what actually ships.

    `encode_minutes` rounds up, so `ceil(s/60) <= T` is `s <= 60T` and a finite cell agrees with
    `evaluate` exactly. What the byte **cannot** carry is the difference between the two missing
    kinds: today's wire format has one NODATA code, so `OFF_NETWORK` and `BEYOND_HORIZON` arrive
    indistinguishable. That is step 6's defect, and it is measured here rather than assumed away:
    every non-OK cell is reported as the browser would see it, UNKNOWN.
    """
    minutes = encode_minutes(np.asarray(secs))
    out = np.full(minutes.shape, int(Verdict.UNKNOWN), dtype=np.int8)
    ok = np.asarray(reason) == Reason.OK
    out[ok & (minutes <= threshold_min)] = int(Verdict.INCLUDED)
    out[ok & (minutes > threshold_min)] = int(Verdict.EXCLUDED)
    return out


# --------------------------------------------------------------------------- the comparison


def cells_for(grid, pts):
    """`(row, col)` per point, and a mask of the points this grid covers at all."""
    rows = np.full(len(pts), -1, dtype=np.int64)
    cols = np.full(len(pts), -1, dtype=np.int64)
    for i, (x, y) in enumerate(pts):
        rc = grid.cell_for_xy(float(x), float(y))
        if rc is not None:
            rows[i], cols[i] = rc
    return rows, cols, rows >= 0


def centres_for(grid, rows, cols, inside):
    """The distinct cell centres the population touches, and each point's index into them.

    Deduplicated because a 100 m cell holds several structures and a 200 m cell holds several
    100 m cells: the census touches 512,633 structures but far fewer cells, and the attachment is
    the expensive part.
    """
    keys = rows.astype(np.int64) * (grid.ncols + 1) + cols
    keys[~inside] = -1
    uniq, back = np.unique(keys, return_inverse=True)
    ur = np.where(uniq >= 0, uniq // (grid.ncols + 1), 0)
    uc = np.where(uniq >= 0, uniq % (grid.ncols + 1), 0)
    xs = grid.x_min + (uc + 0.5) * grid.cell_m
    ys = grid.y_max - (ur + 0.5) * grid.cell_m
    return xs, ys, back, uniq


def difference_summary(a: np.ndarray, b: np.ndarray, both_ok: np.ndarray) -> dict:
    """Signed paired differences `b - a` where both answered, as a distribution and not a mean."""
    # Index first, subtract second: both arrays carry +inf where the reason is not OK, and
    # inf - inf is nan, which would silently poison every percentile below.
    aa = np.asarray(a, dtype=np.float64)[both_ok]
    bb = np.asarray(b, dtype=np.float64)[both_ok]
    d = bb - aa
    if d.size == 0:
        return {"n": 0}
    q = np.percentile(d, [1, 5, 25, 50, 75, 95, 99])
    return {"n": int(d.size),
            "min_s": float(d.min()), "max_s": float(d.max()),
            "p01_s": float(q[0]), "p05_s": float(q[1]), "p25_s": float(q[2]),
            "median_s": float(q[3]), "p75_s": float(q[4]), "p95_s": float(q[5]),
            "p99_s": float(q[6]),
            "mean_abs_s": float(np.abs(d).mean()),
            "within_30s": int((np.abs(d) <= 30).sum()),
            "over_120s": int((np.abs(d) > 120).sum())}


def verdict_moves(base: np.ndarray, other: np.ndarray) -> dict:
    """Every transition, named. A single "disagreement rate" would merge PASS→FAIL, which harms a
    household by excluding a place that qualifies, with PASS→UNKNOWN, which only withholds."""
    names = {int(Verdict.INCLUDED): "INCLUDED", int(Verdict.EXCLUDED): "EXCLUDED",
             int(Verdict.UNKNOWN): "UNKNOWN"}
    out = {}
    for a in names:
        for b in names:
            n = int(((base == a) & (other == b)).sum())
            if n:
                out[f"{names[a]}->{names[b]}"] = n
    same = int((base == other).sum())
    return {"same": same, "moved": int(base.size - same),
            "moved_rate": (base.size - same) / base.size if base.size else 0.0,
            "transitions": out}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=None,
                    help="evaluate only the first N structures, in the population's intrinsic "
                         "order; for a smoke run, never for a published figure")
    ap.add_argument("--no-write-layer", action="store_true")
    ap.add_argument("--out", type=Path, default=ARTIFACT)
    args = ap.parse_args(argv)

    grids = {c: METRO.grid(c) for c in CANDIDATES}
    published = grids[100.0]
    print(f"grids: " + ", ".join(
        f"{int(c)} m {g.nrows}x{g.ncols} origin {g.x_min:.0f}/{g.y_max:.0f}"
        for c, g in grids.items()), flush=True)

    ids, pts, total_rows = structure_population(ACCEPTED_BUILDINGS, published)
    if args.limit:
        ids, pts = ids[:args.limit], pts[:args.limit]
    print(f"population: {len(pts):,} structure centroids inside the published footprint "
          f"(of {total_rows:,} rows)", flush=True)

    idx, T, node_cost, reasons, meta = prepare()
    print(f"graph ready in {meta['prepared_s']}s: {meta['edges']:,} edges, "
          f"{meta['destination_nodes']:,} destination nodes", flush=True)

    t0 = time.perf_counter()
    addr = answer_at(idx, T, node_cost, reasons, pts[:, 0], pts[:, 1])
    print(f"  address answers: {len(pts):,} points in {time.perf_counter() - t0:.0f}s", flush=True)

    per_grid = {}
    for cell_m, grid in grids.items():
        t1 = time.perf_counter()
        rows, cols, inside = cells_for(grid, pts)
        xs, ys, back, uniq = centres_for(grid, rows, cols, inside)
        secs, reason, lower = answer_at(idx, T, node_cost, reasons, xs, ys)
        per_grid[cell_m] = {
            "grid": grid, "inside": inside, "back": back,
            "secs": secs[back], "reason": reason[back], "lower": lower[back],
            "distinct_cells": int((uniq >= 0).sum()),
            "offset_m": np.hypot(pts[:, 0] - xs[back], pts[:, 1] - ys[back]),
        }
        print(f"  {int(cell_m)} m: {int((uniq >= 0).sum()):,} distinct cells touched, "
              f"{int((~inside).sum()):,} structures outside, "
              f"{time.perf_counter() - t1:.0f}s", flush=True)

    covered = per_grid[100.0]["inside"] & per_grid[200.0]["inside"]
    a_ok = addr[1] == Reason.OK
    report = {
        "what_this_is": ("S3.1, the matched candidate-grid comparison: one population of "
                         "structure centroids evaluated at its own coordinate and at the centre "
                         "of the cell containing it in each candidate grid, from one graph and "
                         "one Dijkstra, so that only the grid varies"),
        "built": stamp(), "profile": profile.profile_version(),
        "graph": meta,
        "population": {"structures": int(len(pts)), "overture_rows": int(total_rows),
                       "covered_by_both_grids": int(covered.sum()),
                       "limited_to": args.limit},
        "grids": {str(int(c)): {"nrows": g.nrows, "ncols": g.ncols,
                                "x_min": g.x_min, "y_max": g.y_max, "cell_m": g.cell_m,
                                "cells": g.nrows * g.ncols,
                                "distinct_cells_touched": per_grid[c]["distinct_cells"],
                                "structures_outside": int((~per_grid[c]["inside"]).sum())}
                  for c, g in grids.items()},
        "nested": False,
    }

    # How far a household actually is from the point that answered for it.
    for c in CANDIDATES:
        off = per_grid[c]["offset_m"][per_grid[c]["inside"]]
        report["grids"][str(int(c))]["centroid_to_centre_offset_m"] = {
            "median": float(np.median(off)), "p95": float(np.percentile(off, 95)),
            "max": float(off.max())}

    # Seconds, paired. `address` is the reference for both candidates.
    seconds = {}
    for c in CANDIDATES:
        g = per_grid[c]
        both = covered & a_ok & (g["reason"] == Reason.OK)
        seconds[f"cell{int(c)}_minus_address"] = difference_summary(addr[0], g["secs"], both)
    both_cells = (covered & (per_grid[100.0]["reason"] == Reason.OK)
                  & (per_grid[200.0]["reason"] == Reason.OK))
    seconds["cell200_minus_cell100"] = difference_summary(
        per_grid[100.0]["secs"], per_grid[200.0]["secs"], both_cells)
    report["signed_paired_seconds"] = seconds

    # Verdicts, which is what a household is actually handed.
    report["verdicts"] = {}
    for t_min in THRESHOLDS_MIN:
        v_addr = verdicts(addr[0], addr[1], addr[2], t_min)[covered]
        row = {}
        for c in CANDIDATES:
            g = per_grid[c]
            v = verdicts(g["secs"], g["reason"], g["lower"], t_min)[covered]
            row[f"cell{int(c)}_against_address"] = verdict_moves(v_addr, v)
            row[f"cell{int(c)}_encoded_against_float"] = verdict_moves(
                v, encoded_verdicts(g["secs"], g["reason"], t_min)[covered])
        v100 = verdicts(per_grid[100.0]["secs"], per_grid[100.0]["reason"],
                        per_grid[100.0]["lower"], t_min)[covered]
        v200 = verdicts(per_grid[200.0]["secs"], per_grid[200.0]["reason"],
                        per_grid[200.0]["lower"], t_min)[covered]
        row["cell200_against_cell100"] = verdict_moves(v100, v200)
        report["verdicts"][str(t_min)] = row

    if not args.no_write_layer and not args.limit:
        write_candidate_layer(idx, T, node_cost, reasons, grids[200.0], meta)
        report["layer_written"] = "own_triangle_grocery_walk_cell200"

    args.out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"\nwrote {args.out}")
    print_summary(report)
    return 0


def write_candidate_layer(idx, T, node_cost, reasons, grid, meta) -> None:
    """The 200 m layer itself, beside the 100 m one, so the comparison is re-runnable without a
    graph load — and so step 6 has a second grid to test a mismatched manifest against.

    Named `..._cell200` rather than `own_triangle_grocery_walk`, because the exporter discovers
    layers by `<engine>_<category>_<mode>` and would otherwise treat two resolutions as one layer.
    That discovery rule is itself step 6's defect; this name does not depend on fixing it.
    """
    xs, ys = grid.cell_centers_xy()
    secs, reason, lower = answer_at(idx, T, node_cost, reasons, xs.ravel(), ys.ravel())
    shape = (grid.nrows, grid.ncols)
    surf = surface_of(secs.reshape(shape), reason.reshape(shape), lower.reshape(shape))
    base = LAYERS / "own_triangle_grocery_walk_cell200"
    np.save(base.with_suffix(".npy"), np.asarray(surf.seconds, dtype=np.float32))
    np.save(Path(str(base) + "_reason.npy"), np.asarray(surf.reason, dtype=np.int8))
    np.save(Path(str(base) + "_min_possible_s.npy"),
            np.asarray(surf.min_possible_s, dtype=np.float32))
    Path(str(base) + "_build.json").write_text(json.dumps({
        "metro": METRO.name, "category": CATEGORY, "mode": MODE, "engine": "own-graph",
        "aggregation": CATEGORY_COST_SELECTED, "horizon_s": CUTOFF_MIN * 60.0,
        "cutoff_min": CUTOFF_MIN, "max_access_m": MAX_ACCESS_M,
        "poi_snap_max_m": POI_SNAP_MAX_M, "built": stamp(),
        "cell_m": grid.cell_m, "nrows": grid.nrows, "ncols": grid.ncols,
        "x_min": grid.x_min, "y_max": grid.y_max, "crs": grid.crs,
        "graph": meta,
        "why": ("S3.1's candidate grid. Built from the same graph, destinations and Dijkstra as "
                "the published 100 m layer in the same run, so a difference between them is the "
                "grid and nothing else."),
    }, indent=2, default=str), encoding="utf-8")
    print(f"  wrote {base.name}.npy and its reason/bound/build files", flush=True)


def print_summary(report: dict) -> None:
    print("\nSIGNED PAIRED SECONDS (both answered):")
    for k, v in report["signed_paired_seconds"].items():
        if v.get("n"):
            print(f"  {k:28s} n={v['n']:>7,}  median {v['median_s']:+.1f}s  "
                  f"p05 {v['p05_s']:+.0f}  p95 {v['p95_s']:+.0f}  "
                  f"|d|>120s {v['over_120s']:,}")
    print("\nVERDICTS THAT MOVE, per threshold:")
    for t_min, row in report["verdicts"].items():
        c = row["cell200_against_cell100"]
        a1 = row["cell100_against_address"]
        a2 = row["cell200_against_address"]
        print(f"  T={t_min:>2} min   200m vs 100m: {c['moved']:,} of "
              f"{c['moved'] + c['same']:,} ({c['moved_rate']:.2%})   "
              f"| vs the address itself: 100m {a1['moved_rate']:.2%}, "
              f"200m {a2['moved_rate']:.2%}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
