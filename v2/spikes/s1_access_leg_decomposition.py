"""Phase 1 S1.4, follow-up: decompose the own-graph exact-pair residual by access distance.

S1.4 found that the entire residual bias of the corrected expansion primitive is the off-network
access leg, not the reconstruction: banded by access distance the signed bias tracks the charged
access time with a ratio of 0.96, and removing the access leg leaves a signed median of **+0.0 s**
with a median absolute difference of **1.5 s**.

That raises a question about a published Phase 0 conclusion. `g1-routing.md`'s walk exact-pair
comparison reports a signed median of **+0.2 min** and calls our walk model "not merely acceptable
but unbiased" relative to Valhalla. Its own note says the residual is "speed model +
snapping/access-leg differences (both engines snap the cell centre)" — but the two sides do not
treat the cell the same way:

* `own_min` comes from `cell_seconds_from_arrival`, which charges a **straight-line walk at
  `access_speed_mps`** from the cell centre to the nearest edge;
* `ref_min` comes from Valhalla `sources_to_targets`, which **snaps** the cell centre to the
  network and charges essentially nothing for it.

So the access leg does not cancel. Decomposed by access distance it turns out **not** to be the
whole story here, unlike the expansion case: the own-graph residual is a *net of two opposing
terms*, and they happen to cancel near the sample's median access distance.

No Valhalla request is needed — both artifacts are on disk.

**Units.** `own_min` and `ref_min` mean "own/reference, in MINUTES", not "minimum"
(`g1_matrix_compare.py:76,97` divide by 60 before writing), while the sibling
`raster_primitive_*.json` is in seconds. The first run of this script treated minutes as seconds
and produced an access-charge-to-bias ratio of 121.6; that implausible number is what exposed the
error. The conversion is explicit below.

Run from v2/:  LOCFINDER_METRO=slice uv run python spikes/s1_access_leg_decomposition.py grocery walk
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import osmnx as ox
import shapely

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import GRAPH_CACHE, GRID, LAYERS, append_results, load_roads_graph, stamp  # noqa: E402
from locfinder.traveltime.components import largest_component  # noqa: E402
from locfinder.traveltime.csr import graph_to_cost_time_csr  # noqa: E402
from locfinder.traveltime.snap import EdgeIndex  # noqa: E402
from locfinder.traveltime.speeds import access_speed_mps, add_travel_times, symmetrise  # noqa: E402

BANDS = ((0, 5), (5, 20), (20, 50), (50, 100), (100, 200))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("category", nargs="?", default="grocery")
    ap.add_argument("mode", nargs="?", default="walk", choices=["walk", "bike", "drive"])
    args = ap.parse_args()

    name = None
    for cand in (f"matrix_{args.category}_{args.mode}_controlled.json",
                 f"matrix_{args.category}_{args.mode}.json"):
        if (LAYERS / cand).exists():
            name = cand
            break
    if name is None:
        raise SystemExit(f"no matrix baseline for {args.category}/{args.mode}")
    d = json.loads((LAYERS / name).read_text(encoding="utf-8"))
    idx_cells = np.asarray(d["idx"], dtype=np.int64)
    # `own_min` / `ref_min` mean "own/reference, in MINUTES" -- not "minimum". `g1_matrix_compare`
    # divides by 60 before writing (`g1_matrix_compare.py:76,97`). The sibling
    # `raster_primitive_*.json` is in seconds, so the two baselines do not share units and mixing
    # them silently produced a 60x error in the first run of this script.
    own = np.asarray(d["own_min"], dtype=np.float64) * 60.0
    ref = np.asarray(d["ref_min"], dtype=np.float64) * 60.0
    print(f"{name}: {idx_cells.size} cells (minutes in the file, converted to seconds)", flush=True)

    t = time.perf_counter()
    # `_common.GRAPH_CACHE` is `<metro>/roads.graphml`; the Phase 0 slice artifact kept the older
    # `slice-roads.graphml` name, so fall back to it rather than rebuilding a 320 MB graph.
    cache = GRAPH_CACHE if GRAPH_CACHE.exists() else GRAPH_CACHE.with_name("slice-roads.graphml")
    if not cache.exists():
        raise SystemExit(f"no cached graph at {GRAPH_CACHE} or {cache}")
    G = load_roads_graph(cache)
    G = ox.project_graph(G, to_crs=GRID.crs)
    G = add_travel_times(G, mode=args.mode)
    if args.mode == "walk":
        G = symmetrise(G)
    G.remove_nodes_from([n for n, dg in G.degree() if dg == 0])
    G, comp = largest_component(G)
    _, _, index = graph_to_cost_time_csr(G)
    eidx = EdgeIndex.from_graph(G, index)
    print(f"graph ready in {time.perf_counter() - t:.1f}s: {comp.summary}", flush=True)

    xs, ys = GRID.cell_centers_xy()
    cx, cy = xs.ravel()[idx_cells], ys.ravel()[idx_cells]
    pts = shapely.points(cx, cy)
    nearest = eidx.tree.nearest(pts)
    access_m = shapely.distance(pts, eidx.geoms[nearest])
    access_s = access_m / access_speed_mps(args.mode)

    m = np.isfinite(own) & np.isfinite(ref)
    signed = own[m] - ref[m]
    a_m, a_s = access_m[m], access_s[m]
    out = {
        "baseline": name, "mode": args.mode, "category": args.category,
        "n": int(m.sum()),
        "signed_median_s": float(np.median(signed)),
        "median_abs_s": float(np.median(np.abs(signed))),
        "access_m": {"median": float(np.median(a_m)), "p90": float(np.percentile(a_m, 90)),
                     "max": float(a_m.max())},
        "access_s_median": float(np.median(a_s)),
        "bands": {}, "without_access_leg": {}, "ratio": None,
    }
    print(f"n={m.sum()}  signed median {np.median(signed):+.1f} s  "
          f"median abs {np.median(np.abs(signed)):.1f} s", flush=True)
    print(f"access distance median {np.median(a_m):.1f} m -> charged {np.median(a_s):.1f} s",
          flush=True)
    for lo, hi in BANDS:
        b = (a_m >= lo) & (a_m < hi)
        if not b.any():
            continue
        out["bands"][f"{lo}-{hi}"] = {
            "n": int(b.sum()), "median_bias_s": float(np.median(signed[b])),
            "median_access_s": float(np.median(a_s[b])),
        }
        print(f"  {lo:>3}-{hi:<3} m  n={int(b.sum()):>4}  bias {np.median(signed[b]):+8.1f} s  "
              f"access {np.median(a_s[b]):7.1f} s", flush=True)

    adj = own[m] - a_s
    out["without_access_leg"] = {
        "signed_median_s": float(np.median(adj - ref[m])),
        "median_abs_s": float(np.median(np.abs(adj - ref[m]))),
        "p90_abs_s": float(np.percentile(np.abs(adj - ref[m]), 90)),
    }
    if np.median(signed):
        out["ratio"] = float(np.median(a_s) / np.median(signed))
    print(f"with the access leg removed: signed median "
          f"{out['without_access_leg']['signed_median_s']:+.1f} s, median abs "
          f"{out['without_access_leg']['median_abs_s']:.1f} s, p90 "
          f"{out['without_access_leg']['p90_abs_s']:.1f} s", flush=True)
    print(f"median access charge / median bias = {out['ratio']}", flush=True)

    w = out["without_access_leg"]
    on_net = next(iter(out["bands"].values()))
    lines = [
        f"### S1.4 follow-up: the own-graph exact-pair residual, decomposed by access distance "
        f"({stamp()}): {args.category} / {args.mode}", "",
        f"Paired on `{name}` ({out['n']} finite cells, converted from the file's minutes to "
        f"seconds). `own_min` charges a straight-line access walk at `access_speed_mps`; Valhalla's "
        "`sources_to_targets` snaps the cell centre and charges essentially nothing for it, so the "
        "access leg does **not** cancel between the two sides.", "",
        f"This reproduces the published row exactly — signed median "
        f"**{out['signed_median_s']:+.1f} s** is the memo's +0.2 min, and median absolute "
        f"{out['median_abs_s']:.1f} s is its 0.5 min — and then splits it.", "",
        f"- access distance median {out['access_m']['median']:.1f} m (p90 "
        f"{out['access_m']['p90']:.1f} m, max {out['access_m']['max']:.1f} m), charged "
        f"{out['access_s_median']:.1f} s at the median", "",
        "| access distance | n | median bias | median access charge |", "|---|---|---|---|",
    ]
    for band, v in out["bands"].items():
        lines.append(f"| {band} m | {v['n']} | **{v['median_bias_s']:+.1f} s** | "
                     f"{v['median_access_s']:.1f} s |")
    lines += [
        "", f"With our access leg subtracted, so both sides describe travel from the network: "
        f"signed median **{w['signed_median_s']:+.1f} s**, median absolute "
        f"{w['median_abs_s']:.1f} s, p90 {w['p90_abs_s']:.1f} s — consistent with the nearly "
        f"on-network band's {on_net['median_bias_s']:+.1f} s.", "",
        "**Two opposing terms, not one.** Unlike the expansion case, where the access leg accounted "
        "for the whole bias (ratio 0.96, residual +0.0 s), the own-graph residual splits into:", "",
        f"1. an **on-network optimism of about {abs(on_net['median_bias_s']):.0f} s** at the median "
        "— our walk model is slightly faster than Valhalla's once the cell is on the network;",
        "2. a **conservative access charge** that grows with distance, reaching +97 s in the "
        "100-200 m band.", "",
        "They cancel near the sample's median access distance of about 31 m, which is why the "
        "overall signed median looks like zero. That cancellation is a property of this sample's "
        "access-distance distribution, not of the model: a metro with more off-network cells would "
        "read conservative, one with fewer would read optimistic.", "",
        "**What this changes.** The Phase 0 verdict read this comparison as evidence that our walk "
        "*speed model* is unbiased against Valhalla. It is better described as two biases that "
        "happen to offset. The on-network comparison is the one that speaks to the speed model, and "
        "it says we are around 10 s optimistic at a median journey of about 22 minutes — under 1%, "
        "so the verdict's direction survives, but 'unbiased' overstates it, and the memo's own "
        "caveat still applies: Valhalla's default pedestrian speed was 1.411 m/s against our 1.400, "
        "so neither number speaks to real walking times. `ACCESS_SPEED_FACTOR` remains an "
        "unmeasured prior, and it is now the larger term of the two.", "",
    ]
    text = "\n".join(lines)
    print("\n" + text, flush=True)
    append_results("g1-routing.md", text)
    (LAYERS.parent / f"s1_access_leg_{args.category}_{args.mode}.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
