"""Phase 1 S1.4: the paired re-measurement of the expansion primitive.

Originally a Gate G1 candidate comparing Valhalla `/expansion` edges against the isochrone raster.
Its published result — median 69 s, p90 271 s, signed median **+66 s** — described a *different
implementation* from the one decision D1 adopted, because this script requested only
`duration`/`distance` and did its own whole-edge charging; `traveltime/expansion.py`, which needs
`edge_id`/`pred_edge_id`, was never called from outside the unit tests.

This version runs both, paired on the same cells and the same exact `sources_to_targets` values:

* **old** — the published method, reproduced verbatim: `skip_opposites=true`, nearest expansion
  edge, charge its whole settled duration, add the modal access leg. No within-edge interpolation.
* **new** — the adopted primitive: `skip_opposites=false`, `expansion_to_edge_index` (merging the
  two directed features of each road and keeping only the directions the search settled), then
  `snap.cell_seconds_from_arrival`, which interpolates within the matched edge.

Two paired baselines, selected with `--paired`:

* `raster` — `data/raster_primitive_<cat>_<mode>.json`, 240 cells, exact over the **same 3 POIs**.
  This is the baseline the published row used, so it is the one that supersedes it.
* `matrix` — `data/layers/matrix_<cat>_<mode>[_controlled].json`, 304-600 cells banded around the
  user thresholds, exact over **all** category POIs. The expansion is then built over all POIs too,
  which `service_limits.isochrone.max_locations = 1000` permits.

Run from v2/ with Valhalla serving (the slice baselines need `LOCFINDER_METRO=slice`):
  LOCFINDER_METRO=slice uv run python spikes/g1_expansion_primitive.py --mode walk --paired raster
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import geopandas as gpd
import httpx
import numpy as np
import shapely
from pyproj import Transformer
from shapely.geometry import LineString

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (ACCEPTED_PLACES, CONTROLLED_COSTING_OPTIONS, DATA, GRID, LAYERS,  # noqa: E402
                     VALHALLA, VALHALLA_COSTING, append_results, stamp)
from locfinder.places.categories import select_overture  # noqa: E402
from locfinder.traveltime.expansion import expansion_to_edge_index  # noqa: E402
from locfinder.traveltime.snap import cell_seconds_from_arrival  # noqa: E402
from locfinder.traveltime.speeds import access_speed_mps  # noqa: E402

MAX_MIN = 60
THRESHOLDS = [10, 15, 25, 45]
PROPS_OLD = ["duration", "distance"]
PROPS_NEW = ["duration", "distance", "edge_id", "pred_edge_id"]


def expansion_request(locations, costing, *, controlled: bool, skip_opposites: bool,
                      props: list[str], minutes: int = MAX_MIN):
    body = {"locations": [{"lat": a, "lon": b} for a, b in locations], "costing": costing,
            "contours": [{"time": minutes}], "action": "isochrone", "reverse": True,
            "skip_opposites": skip_opposites, "expansion_properties": props}
    if controlled and CONTROLLED_COSTING_OPTIONS.get(costing):
        body["costing_options"] = {costing: CONTROLLED_COSTING_OPTIONS[costing]}
    t0 = time.perf_counter()
    r = httpx.post(f"{VALHALLA}/expansion", json=body, timeout=1800)
    r.raise_for_status()
    return r.json()["features"], time.perf_counter() - t0


def cells_old_method(feats, xs, ys, *, mode: str, max_access_m: float = 200.0) -> np.ndarray:
    """The published method, reproduced: the nearest expansion edge's whole settled duration plus
    the off-network access leg. Within-edge position is not resolved, so a cell is charged the
    arrival time of the edge's settled end however close it is to the other end — the source of
    the +66 s conservative bias."""
    to_utm = Transformer.from_crs("EPSG:4326", GRID.crs, always_xy=True)
    geoms, durs = [], []
    for f in feats:
        coords = f["geometry"]["coordinates"]
        if len(coords) < 2:
            continue
        gx, gy = to_utm.transform([c[0] for c in coords], [c[1] for c in coords])
        geoms.append(LineString(list(zip(gx, gy))))
        durs.append(float(f["properties"]["duration"]))
    durs = np.asarray(durs, dtype=np.float64)
    tree = shapely.STRtree(geoms)
    arr = np.empty(len(geoms), dtype=object)
    arr[:] = geoms
    pts = shapely.points(np.asarray(xs).ravel(), np.asarray(ys).ravel())
    nearest = tree.nearest(pts)
    access_m = shapely.distance(pts, arr[nearest])
    total = durs[nearest] + access_m / access_speed_mps(mode)
    total = np.where(access_m > max_access_m, np.inf, total)
    return total.reshape(np.shape(xs)), len(geoms)


def describe(label: str, d: np.ndarray) -> str:
    if d.size == 0:
        return f"| {label} | 0 | - | - | - | - |"
    return (f"| {label} | {d.size} | {np.median(d):.0f} | {np.percentile(d, 90):.0f} | "
            f"{d.max():.0f} | {(d > 60).mean():.1%} |")


CHUNK = 8   # sources per matrix request; Valhalla caps sources x targets at 2500 pairs


def matrix_exact(sources_lonlat, targets_latlon, costing, controlled) -> np.ndarray:
    """Minimum `sources_to_targets` seconds from each source to any target. inf where none."""
    out = np.full(len(sources_lonlat), np.inf)
    tg = [{"lat": a, "lon": b} for a, b in targets_latlon]
    for i in range(0, len(sources_lonlat), CHUNK):
        chunk = sources_lonlat[i:i + CHUNK]
        body = {"sources": [{"lat": la, "lon": lo} for lo, la in chunk], "targets": tg,
                "costing": costing}
        if controlled and CONTROLLED_COSTING_OPTIONS.get(costing):
            body["costing_options"] = {costing: CONTROLLED_COSTING_OPTIONS[costing]}
        r = httpx.post(f"{VALHALLA}/sources_to_targets", json=body, timeout=900)
        r.raise_for_status()
        for j, row in enumerate(r.json()["sources_to_targets"]):
            vals = [c["time"] for c in row if c.get("time") is not None]
            if vals:
                out[i + j] = float(min(vals))
    return out


def fresh_baseline(category: str, mode: str, costing: str, latlon, n_cells: int = 240):
    """Sample cells from the expansion's own reachable set and get exact values for the same POIs.

    Needed because the adopted modes (drive, bike) have no 3-POI raster baseline, and building an
    expansion over all 285 POIs would return a response far larger than is worth parsing. Sampling
    inside the reachable set keeps every sampled cell comparable rather than trivially unreachable.
    """
    f, dt = expansion_request(latlon, costing, controlled=True, skip_opposites=False,
                              props=PROPS_NEW)
    lonlat = [(lo, la) for la, lo in latlon]
    eidx, T = expansion_to_edge_index(f, target_crs=GRID.crs, opposites_included=True,
                                      origins=lonlat, strict=False, report={})
    xs, ys = GRID.cell_centers_xy()
    secs = cell_seconds_from_arrival(eidx, T, xs, ys, mode=mode, max_access_m=200.0,
                                     cutoff_s=MAX_MIN * 60.0).ravel()
    reachable = np.flatnonzero(np.isfinite(secs))
    rng = np.random.default_rng(20261104)
    pick = rng.choice(reachable, size=min(n_cells, reachable.size), replace=False)
    pick.sort()
    to_wgs = Transformer.from_crs(GRID.crs, "EPSG:4326", always_xy=True)
    lon, lat = to_wgs.transform(xs.ravel()[pick], ys.ravel()[pick])
    exact = matrix_exact(list(zip(lon, lat)), latlon, costing, True)
    return pick, exact, f, dt


def load_paired(kind: str, category: str, mode: str):
    if kind == "raster":
        p = DATA / f"raster_primitive_{category}_{mode}.json"
        if not p.exists():
            raise SystemExit(f"missing {p}; run g1_raster_primitive.py first")
        d = json.loads(p.read_text(encoding="utf-8"))
        return (np.asarray(d["idx"], dtype=np.int64), np.asarray(d["exact"], dtype=np.float64),
                3, p.name, {"A": np.asarray(d["A"], dtype=np.float64),
                            "B": np.asarray(d["B"], dtype=np.float64)})
    for name in (f"matrix_{category}_{mode}_controlled.json", f"matrix_{category}_{mode}.json"):
        p = LAYERS / name
        if p.exists():
            d = json.loads(p.read_text(encoding="utf-8"))
            # `own_min`/`ref_min` are MINUTES (`g1_matrix_compare.py:76,97`), while the raster
            # baseline above is seconds. Convert, or the comparison is out by 60.
            return (np.asarray(d["idx"], dtype=np.int64),
                    np.asarray(d["ref_min"], dtype=np.float64) * 60.0, None, p.name,
                    {"own-graph": np.asarray(d["own_min"], dtype=np.float64) * 60.0})
    raise SystemExit(f"no matrix baseline for {category}/{mode}; run g1_matrix_compare.py first")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--category", default="grocery")
    ap.add_argument("--mode", default="walk", choices=["walk", "bike", "drive"])
    ap.add_argument("--paired", default="raster", choices=["raster", "matrix", "fresh"])
    ap.add_argument("--pois", type=int, default=3)
    args = ap.parse_args()
    costing = VALHALLA_COSTING[args.mode]

    places = gpd.read_parquet(ACCEPTED_PLACES)
    sel = select_overture(places, args.category).to_crs(GRID.crs)
    cent = sel.geometry.centroid.to_crs("EPSG:4326")
    all_latlon = [(float(y), float(x)) for x, y in zip(cent.x, cent.y)]

    others: dict = {}
    if args.paired == "fresh":
        latlon = all_latlon[: args.pois]
        idx_cells, exact, _f, _dt = fresh_baseline(args.category, args.mode, costing, latlon)
        paired_name = f"fresh sample, {args.pois} POIs, seed 20261104"
    else:
        idx_cells, exact, n_pois, paired_name, others = load_paired(args.paired, args.category,
                                                                    args.mode)
        latlon = all_latlon if n_pois is None else all_latlon[:n_pois]
    lonlat = [(lo, la) for la, lo in latlon]
    print(f"{paired_name}: {idx_cells.size} cells, exact over {len(latlon)} POIs", flush=True)

    xs, ys = GRID.cell_centers_xy()

    # ---- old: the published method -----------------------------------------------------------
    f_old, dt_old = expansion_request(latlon, costing, controlled=True, skip_opposites=True,
                                      props=PROPS_OLD)
    E_old_full, n_old = cells_old_method(f_old, xs, ys, mode=args.mode)
    E_old = E_old_full.ravel()[idx_cells]
    print(f"old: {n_old} edges in {dt_old:.2f} s", flush=True)

    # ---- new: the adopted primitive ----------------------------------------------------------
    f_new, dt_new = expansion_request(latlon, costing, controlled=True, skip_opposites=False,
                                      props=PROPS_NEW)
    rep: dict = {}
    eidx, T = expansion_to_edge_index(f_new, target_crs=GRID.crs, opposites_included=True,
                                      origins=lonlat, strict=False, report=rep)
    # No `cutoff_s` here. The old path applies none, so censoring only the new one gave the two
    # rows different finite cohorts -- 195 against 181 points -- while the narrative called them
    # paired (Codex pass-9 M2). Censoring is reported separately below instead.
    E_new_full = cell_seconds_from_arrival(eidx, T, xs, ys, mode=args.mode, max_access_m=200.0)
    E_new = E_new_full.ravel()[idx_cells]
    print(f"new: {rep} in {dt_new:.2f} s", flush=True)

    fin = np.isfinite(exact)
    rows = {"old (published, whole-edge)": E_old, "new (adopted, interpolated)": E_new}
    rows.update(others)
    # One cohort for every time-error row: cells where the reference and BOTH methods are finite.
    common = fin & np.isfinite(E_old) & np.isfinite(E_new)
    stats: dict = {}
    for label, X in rows.items():
        m = common if label.startswith(("old", "new")) else (fin & np.isfinite(X))
        stats[label] = {
            "n": int(m.sum()),
            "median_abs": float(np.median(np.abs(X[m] - exact[m]))) if m.any() else None,
            "p90_abs": float(np.percentile(np.abs(X[m] - exact[m]), 90)) if m.any() else None,
            "max_abs": float(np.abs(X[m] - exact[m]).max()) if m.any() else None,
            "share_over_60s": float((np.abs(X[m] - exact[m]) > 60).mean()) if m.any() else None,
            "signed_median": float(np.median(X[m] - exact[m])) if m.any() else None,
            "p90_signed_abs": float(np.percentile(np.abs(X[m] - exact[m]), 90)) if m.any() else None,
            "max_signed_abs": float(np.abs(X[m] - exact[m]).max()) if m.any() else None,
            "unreachable": int((~np.isfinite(X)).sum()),
            "cohort": "common" if label.startswith(("old", "new")) else "own",
        }
    coverage = {
        "reference_finite": int(fin.sum()),
        "old_finite": int((fin & np.isfinite(E_old)).sum()),
        "new_finite": int((fin & np.isfinite(E_new)).sum()),
        "common_finite": int(common.sum()),
        "new_over_horizon": int((common & (E_new > MAX_MIN * 60.0)).sum()),
    }

    out = {"category": args.category, "mode": args.mode, "paired": paired_name,
           "pois": len(latlon), "cells": int(idx_cells.size),
           "old": {"edges": n_old, "seconds": dt_old},
           "new": {"report": rep, "seconds": dt_new}, "stats": stats, "coverage": coverage,
           "thresholds": {},
           # M3: save the cohort so the conditional sample can be audited and reused.
           "cohort": {"idx": idx_cells.tolist(), "exact_s": exact.tolist(),
                      "new_s": [None if not np.isfinite(v) else float(v) for v in E_new],
                      "old_s": [None if not np.isfinite(v) else float(v) for v in E_old]}}

    lines = [
        f"### S1.4 expansion primitive, re-measured ({stamp()}): {args.category} / {args.mode}, "
        f"{len(latlon)} POIs, paired on `{paired_name}` ({idx_cells.size} cells)", "",
        "Two methods on the same cells against the same exact `sources_to_targets` values. "
        "**old** is the published method reproduced verbatim — `skip_opposites=true`, nearest edge, "
        f"charge its whole settled duration ({n_old:,} edges, {dt_old:.2f} s). **new** is the "
        "adopted primitive — `skip_opposites=false`, `expansion_to_edge_index` with merging and "
        f"direction, then within-edge interpolation ({rep['physical_edges']:,} physical edges from "
        f"{rep['edges']:,} features, {dt_new:.2f} s).", "",
        f"Adapter report: `{rep}`", "",
        f"All time-error rows use **one cohort**: the {coverage['common_finite']} cells where the "
        f"reference and both methods are finite (reference finite {coverage['reference_finite']}, "
        f"old finite {coverage['old_finite']}, new finite {coverage['new_finite']}). Neither method "
        f"applies a final cutoff, so censoring cannot shift the cohort; "
        f"{coverage['new_over_horizon']} of the new values exceed the {MAX_MIN}-minute horizon and "
        "would be censored by a published layer.", "",
        "| difference from exact (seconds) | n | median | p90 | max | share > 60 s | signed median |",
        "|---|---|---|---|---|---|---|",
    ]
    for label, s in stats.items():
        if s["n"] == 0:
            lines.append(f"| {label} | 0 | - | - | - | - | - |")
            continue
        lines.append(f"| {'**' + label + '**' if label.startswith('new') else label} | {s['n']} | "
                     f"{s['median_abs']:.0f} | {s['p90_abs']:.0f} | {s['max_abs']:.0f} | "
                     f"{s['share_over_60s']:.1%} | **{s['signed_median']:+.0f} s** |")
    lines += ["", "Positive signed median = our value is later than exact, i.e. conservative.", "",
              "Threshold classification against exact:", "",
              "| T min | old agrees | new agrees | new false-in | new false-out |",
              "|---|---|---|---|---|"]
    for T in THRESHOLDS:
        t = T * 60.0
        ex_in = fin & (exact <= t)
        ex_out = fin & ~ex_in
        row = {}
        for label, X in (("old", E_old), ("new", E_new)):
            x_in = np.isfinite(X) & (X <= t)
            row[label] = float(((x_in & ex_in) | (~x_in & ex_out))[fin].mean())
        n_in = np.isfinite(E_new) & (E_new <= t)
        fi = float((n_in & ex_out).sum() / max(ex_out.sum(), 1))
        fo = float(((~n_in) & ex_in).sum() / max(ex_in.sum(), 1))
        out["thresholds"][str(T)] = {"old_agrees": row["old"], "new_agrees": row["new"],
                                     "new_false_in": fi, "new_false_out": fo,
                                     "exact_in": int(ex_in.sum())}
        lines.append(f"| {T} | {row['old']:.1%} | {row['new']:.1%} | {fi:.1%} | {fo:.1%} |")

    # ---- where is the residual? the access leg is not in the reference at all ----------------
    pts = shapely.points(xs.ravel()[idx_cells], ys.ravel()[idx_cells])
    nearest = eidx.tree.nearest(pts)
    access_m = shapely.distance(pts, eidx.geoms[nearest])
    access_s = access_m / access_speed_mps(args.mode)
    mnew = fin & np.isfinite(E_new)
    signed_new = E_new[mnew] - exact[mnew]
    a_m, a_s = access_m[mnew], access_s[mnew]
    bands = {}
    for lo, hi in ((0, 5), (5, 20), (20, 50), (50, 100), (100, 200)):
        b = (a_m >= lo) & (a_m < hi)
        if b.any():
            bands[f"{lo}-{hi}"] = {"n": int(b.sum()),
                                   "median_bias_s": float(np.median(signed_new[b])),
                                   "median_access_s": float(np.median(a_s[b]))}
    on_net = E_new[mnew] - a_s
    out["access_leg"] = {
        "bands": bands,
        "access_m_median": float(np.median(a_m)),
        "signed_median_total": float(np.median(signed_new)),
        "signed_median_on_network": float(np.median(on_net - exact[mnew])),
        "median_abs_on_network": float(np.median(np.abs(on_net - exact[mnew]))),
        "ratio_access_to_bias": (float(np.median(a_s) / np.median(signed_new))
                                 if np.median(signed_new) else None),
    }
    al = out["access_leg"]
    sm = stats["new (adopted, interpolated)"]["signed_median"]
    total_verdict = "PASS" if sm is not None and abs(sm) <= 15.0 else "FAIL"
    net_verdict = "PASS" if abs(al["signed_median_on_network"]) <= 15.0 else "FAIL"
    out["signed_median_within_15s"] = {"as_written_total": total_verdict,
                                       "on_network": net_verdict}
    lines += [
        "", "**Where the residual is.** The reference charges nothing for reaching the network — "
        "`sources_to_targets` snaps the cell centre — while we add a straight-line leg at "
        "`access_speed_mps`. So the access leg is in our number and absent from theirs.", "",
        "| access distance | n | median bias | median access charge |", "|---|---|---|---|",
    ] + [
        f"| {band} m | {v['n']} | **{v['median_bias_s']:+.1f} s** | {v['median_access_s']:.1f} s |"
        for band, v in bands.items()
    ] + [
        "", f"Median access charge / median bias = **{al['ratio_access_to_bias']:.2f}** "
        f"({'the access leg accounts for essentially all of it' if al['ratio_access_to_bias'] and 0.8 <= al['ratio_access_to_bias'] <= 1.25 else 'so the access leg is only part of it'}). "
        f"Subtracting our access leg, so both sides describe travel from the network: signed median "
        f"**{al['signed_median_on_network']:+.1f} s**, median absolute "
        f"**{al['median_abs_on_network']:.1f} s**.", "",
        f"**S1.4 pass criterion — signed median within ±15 s.** Against the total: "
        f"**{total_verdict}** ({sm:+.1f} s; the published row was +66 s). Against the on-network "
        f"component, which is what the criterion was meant to test: **{net_verdict}** "
        f"({al['signed_median_on_network']:+.1f} s).", "",
    ]
    if net_verdict == "PASS":
        lines += [
            "So for this mode the reconstruction agrees with the engine it reconstructs **at the "
            f"median**, and the remaining {sm:+.0f} s is our own access-leg model, an unmeasured "
            "prior (`ACCESS_SPEED_FACTOR`) the reference does not contain.", ""]
    else:
        lines += [
            f"So for this mode the residual is **not** explained by the access leg: "
            f"{al['signed_median_on_network']:+.1f} s survives its removal, and the node-level "
            "experiment (`s1_expansion_node_fidelity.py`) reproduces that figure with no grid, no "
            "access leg and no interpolation. The cause is therefore in the tree or the costing, "
            "not in the snapping.", ""]
    lines += [
        "**Read the median with its tails.** A near-zero signed median bounds no individual cell "
        f"(Codex pass-9 H4). On this cohort the new method's absolute difference has p90 "
        f"{stats['new (adopted, interpolated)']['p90_signed_abs']:.1f} s and maximum "
        f"{stats['new (adopted, interpolated)']['max_signed_abs']:.0f} s, and the on-network "
        "residual has its own tail. 'Exact' is the wrong word for a median.", "",
        "**What the threshold table is and is not.** The false-exclusion column is "
        "`reference-positive cells the method misses / reference-positive cells **in this "
        "sample**`, and for the fresh baselines that sample is drawn only from the model's own "
        "reachable set under the horizon — so a truly-close cell the model cannot reach has **zero "
        "probability of being sampled**. The counts are small: "
        + ", ".join(f"T={T} has {out['thresholds'][str(T)]['exact_in']} reference positives"
                    for T in THRESHOLDS)
        + ". These are conditional figures on a fixed-seed sample, not estimated rates for the "
        "grid.", "",
        "This measures **construction fidelity against the same engine**: both sides are "
        "Valhalla. It is a prerequisite for accuracy and is not evidence of it (S3.4), and "
        "zero observed false inclusions on a finite sample is not proof of a zero rate.", ""]
    text = "\n".join(lines)
    print("\n" + text, flush=True)
    append_results("g1-routing.md", text)
    (DATA / f"s1_expansion_remeasure_{args.category}_{args.mode}_{args.paired}.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
