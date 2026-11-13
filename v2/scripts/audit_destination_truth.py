"""Step 7 — the grocery destination truth audit: validity, resolution, coverage.

**The failure class no estimand here can see.** E1 and E2 compare our pipeline against an engine,
and both sides read the **same destination list**. A grocery that is closed, that does not exist,
that sits at the wrong coordinate, or that is **missing from the list entirely** produces perfect
agreement and two wrong answers. Design §3 states that blind spot; this measures it.

Three parts, and only the third needs a human.

**1. Validity — and the first finding needed no external source at all.** Overture publishes an
`operating_status` for each place and a `confidence`. Nothing in this pipeline reads either one. So
the published destination set contains places Overture itself marks `permanently_closed`, and the
product routes households to them. That is the design's own "closed grocery" example, found in data
we had already ingested.

**2. Resolution.** A place becomes a destination by snapping to a road node within
`POI_SNAP_MAX_M` = 300 m. A store 290 m from its nearest node is a different claim from one 10 m
away, and several stores sharing one node are indistinguishable in the answer. Both are measured
here rather than assumed small.

**3. Coverage, which is the omission question.** OSM is an independent, free source already on disk
(`osm_pois.parquet`), so the two lists can be compared without scraping anything. An OSM
supermarket with no Overture grocery near it is a **candidate omitted destination** — a store
households near it cannot be routed to.

**Candidate, not finding.** OSM's `shop=supermarket` in this extract includes obvious mistags: "Tar
Heels Termite Removal" and "Wiley's Workshop on Wheels", both `opening_hours=24/7`. So the
unmatched set is an upper bound that needs human triage, and this script writes it as a **sheet to
check** rather than quietly adding it to the destination list. The impact figure is therefore
conditional: *if* these are real, this many structures are currently excluded wrongly.

The impact measurements cost one graph load and one Dijkstra per destination set.

    python scripts/audit_destination_truth.py --no-impact    # the cheap checks only
    python scripts/audit_destination_truth.py                # with the routed impact
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import sys
import time
from collections import Counter

import geopandas as gpd
import numpy as np
import osmnx as ox
from shapely.strtree import STRtree

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "spikes"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _common import METRO, METRO_DIR, load_roads_graph, stamp      # noqa: E402
from locfinder.measure.frames import structure_population          # noqa: E402
from locfinder.places.categories import select_osm, select_overture  # noqa: E402
from locfinder.status import Verdict                               # noqa: E402

#: Brands a household in the Triangle would call a grocery, drawn from what is actually present
#: in this extract rather than from a national list -- so every row the table below prints is a
#: store that exists here. The question this set answers is not "what is a grocery in general" but
#: "does our destination list contain the shops people actually buy food at".
HOUSEHOLD_BRANDS = (
    "Harris Teeter", "Food Lion", "Publix", "Kroger", "Aldi", "Lidl", "Trader Joe",
    "Whole Foods", "Walmart Supercenter", "Walmart Neighborhood", "Target", "Wegmans",
    "Weaver Street", "Sprouts", "Fresh Market", "Compare Foods", "Grand Asia", "H Mart",
    "Costco", "Sam's Club", "BJ's",
)

#: Primaries that can plausibly be the store itself rather than a concession inside it. A brand
#: name alone is not enough: "WALMART #003182" is a money-transfer desk and "Harris Teeter Fuel"
#: is a petrol station, and admitting those as groceries would be a different error.
STORE_PRIMARIES = frozenset({
    "superstore", "department_store", "discount_store", "warehouse_club_store",
    "wholesale_grocer", "specialty_foods_store", "health_food_store", "produce_store",
    "food_and_beverage_store", "grocery_store", None,
})

CATEGORY = "grocery"
MODE = "walk"
POI_SNAP_MAX_M = 300.0
THRESHOLDS_MIN = (10, 15, 25, 45)
#: How far an OSM supermarket may sit from an Overture grocery and still be the same shop. Chosen
#: as the destination snap cap, because two representations of one store further apart than that
#: would snap to different nodes and so are different destinations to this pipeline.
SAME_SHOP_M = 300.0

V2 = pathlib.Path(__file__).resolve().parents[1]
ARTIFACT = V2.parent / "docs" / "experiments" / "s3-7-destination-truth.json"
SHEET = V2.parent / "docs" / "experiments" / "audit" / "s3-7-destinations-to-check.csv"


def overture_name(names) -> str:
    """Overture packs names as a struct; take the primary and fall back to anything present."""
    if names is None:
        return ""
    if isinstance(names, dict):
        v = names.get("primary")
        if v:
            return str(v)
        for key in ("common", "rules"):
            got = names.get(key)
            if isinstance(got, dict) and got:
                return str(next(iter(got.values())))
            if isinstance(got, (list, tuple)) and got:
                return str(got[0])
        return ""
    return str(names)


def lonlat(points, crs) -> list[tuple[float, float]]:
    s = gpd.GeoSeries(points, crs=crs).to_crs("EPSG:4326")
    return [(float(p.x), float(p.y)) for p in s]


# --------------------------------------------------------------------------- 1. validity


def validity(grocery: gpd.GeoDataFrame) -> dict:
    status = [str(s) for s in grocery["operating_status"]]
    conf = np.asarray(grocery["confidence"], dtype=float)
    closed = grocery[np.array([s == "permanently_closed" for s in status])]
    pts = lonlat(list(closed.geometry.centroid.values), grocery.crs)
    return {
        "places": int(len(grocery)),
        "operating_status": dict(Counter(status)),
        "nothing_in_the_pipeline_reads_operating_status": True,
        "permanently_closed": [
            {"id": str(r.id), "name": overture_name(r.names), "confidence": float(r.confidence),
             "lon": p[0], "lat": p[1]}
            for r, p in zip(closed.itertuples(), pts)],
        "confidence": {"min": float(conf.min()), "p05": float(np.percentile(conf, 5)),
                       "median": float(np.median(conf)), "max": float(conf.max()),
                       "below_0_3": int((conf < 0.3).sum()), "below_0_5": int((conf < 0.5).sum()),
                       "below_0_6": int((conf < 0.6).sum())},
    }


# --------------------------------------------------------------------------- 2. resolution


def resolution(G, grocery: gpd.GeoDataFrame) -> dict:
    cen = grocery.geometry.centroid
    nodes, dists = ox.nearest_nodes(G, cen.x.to_numpy(), cen.y.to_numpy(), return_dist=True)
    dists = np.asarray(dists, dtype=float)
    kept = dists <= POI_SNAP_MAX_M
    node_counts = Counter(n for n, k in zip(nodes, kept) if k)
    shared = {n: c for n, c in node_counts.items() if c > 1}
    return {
        "snap_cap_m": POI_SNAP_MAX_M,
        "places": int(len(grocery)),
        "kept_by_the_cap": int(kept.sum()),
        "dropped_by_the_cap": int((~kept).sum()),
        "snap_distance_m": {"median": float(np.median(dists)),
                            "p90": float(np.percentile(dists, 90)),
                            "p99": float(np.percentile(dists, 99)),
                            "max": float(dists.max()),
                            "within_10m": int((dists <= 10).sum()),
                            "between_200_and_300m": int(((dists > 200) & (dists <= 300)).sum())},
        "distinct_nodes": len(node_counts),
        "nodes_serving_more_than_one_place": len(shared),
        "places_sharing_a_node": int(sum(shared.values())),
        "largest_node_share": max(node_counts.values()) if node_counts else 0,
        "why_this_matters": ("a place beyond the cap is not a destination at all, and places "
                             "sharing a node are indistinguishable in the published answer -- the "
                             "layer reports the cost-selected one and cannot name which"),
    }


# --------------------------------------------------------------------------- 3. coverage


def coverage(grocery: gpd.GeoDataFrame, osm_grocery: gpd.GeoDataFrame, grid) -> dict:
    def inside(gdf):
        c = gdf.geometry.centroid
        x, y = c.x.to_numpy(), c.y.to_numpy()
        return ((x >= grid.x_min) & (x < grid.x_min + grid.ncols * grid.cell_m)
                & (y > grid.y_max - grid.nrows * grid.cell_m) & (y <= grid.y_max))

    ov_in, osm_in = grocery[inside(grocery)], osm_grocery[inside(osm_grocery)]
    A = list(ov_in.geometry.centroid.values)
    B = list(osm_in.geometry.centroid.values)
    if not A or not B:
        return {"note": "one of the two sets is empty inside the footprint"}
    near_ov = STRtree(A).nearest(B)
    d_osm = np.array([B[i].distance(A[j]) for i, j in enumerate(near_ov)])
    near_osm = STRtree(B).nearest(A)
    d_ov = np.array([A[i].distance(B[j]) for i, j in enumerate(near_osm)])

    unmatched = osm_in[d_osm > SAME_SHOP_M]
    pts = lonlat(list(unmatched.geometry.centroid.values), grocery.crs)
    cols = [c for c in ("name", "brand", "shop", "operator", "addr:street", "addr:city",
                        "opening_hours") if c in unmatched.columns]
    rows = []
    for (fid, r), p, dist in zip(unmatched.iterrows(), pts,
                                 d_osm[d_osm > SAME_SHOP_M]):
        row = {"osm_feature_id": str(fid), "lon": p[0], "lat": p[1],
               "metres_to_nearest_overture_grocery": round(float(dist), 1)}
        row.update({c: (None if r[c] is None else str(r[c])) for c in cols})
        rows.append(row)
    rows.sort(key=lambda r: -r["metres_to_nearest_overture_grocery"])

    return {
        "inside_the_footprint": {"overture_grocery": int(len(ov_in)),
                                 "osm_grocery": int(len(osm_in))},
        "osm_to_nearest_overture_m": {
            "median": float(np.median(d_osm)), "p90": float(np.percentile(d_osm, 90)),
            "beyond_50m": int((d_osm > 50).sum()), "beyond_100m": int((d_osm > 100).sum()),
            "beyond_300m": int((d_osm > SAME_SHOP_M).sum())},
        "overture_to_nearest_osm_m": {
            "beyond_100m": int((d_ov > 100).sum()), "beyond_300m": int((d_ov > 300).sum()),
            "note": ("this direction is mostly a DEFINITIONAL difference, not evidence of "
                     "nonexistence: the Overture selector admits ethnic and organic grocery "
                     "stores through the taxonomy hierarchy, which OSM tags as shop=convenience, "
                     "shop=grocery or a deli rather than shop=supermarket")},
        "candidate_omitted_destinations": rows,
        "candidate_not_finding": ("OSM shop=supermarket in this extract includes obvious mistags "
                                  "-- 'Tar Heels Termite Removal' and 'Wiley's Workshop on "
                                  "Wheels', both opening_hours=24/7 -- so this is an upper bound "
                                  "needing human triage, written as a sheet to check rather than "
                                  "added to the destination list"),
    }


# --------------------------------------------------------------------------- brands


def brand_coverage(grocery: gpd.GeoDataFrame, ov_inside: gpd.GeoDataFrame) -> dict:
    """For each brand a household would name, how many of its stores are destinations.

    **Taxonomy is the wrong level to argue at.** `discount_store` holds 195 places inside the
    footprint, almost all dollar stores, and one of them is Aldi. A brand is unambiguous.

    The finding this exposes is sharper than a missing category: **the same chain appears on both
    sides of the wedge**. Overture tags some Aldi branches `grocery_store` and others
    `discount_store`, so our destination list admits some branches of one chain and not others —
    which makes the published answer arbitrary at the branch level, not merely conservative.
    """
    ids = set(grocery["id"])
    names = [overture_name(n) for n in ov_inside["names"]]
    prims = [t.get("primary") if isinstance(t, dict) else None for t in ov_inside["taxonomy"]]
    in_wedge = [i in ids for i in ov_inside["id"]]

    rows = []
    for brand in HOUSEHOLD_BRANDS:
        low = brand.lower()
        hits = [k for k, n in enumerate(names) if low in n.lower()]
        if not hits:
            continue
        inside_n = sum(1 for k in hits if in_wedge[k])
        outside = [k for k in hits if not in_wedge[k] and prims[k] in STORE_PRIMARIES]
        if inside_n == 0 and not outside:
            continue
        rows.append({
            "brand": brand,
            "in_the_destination_list": inside_n,
            "store_rows_not_in_it": len(outside),
            "their_primaries": dict(Counter(p or "(none)" for p in (prims[k] for k in outside))),
        })
    absent = [r["brand"] for r in rows
              if r["in_the_destination_list"] == 0 and r["store_rows_not_in_it"] > 0]
    split = [r["brand"] for r in rows
             if r["in_the_destination_list"] > 0 and r["store_rows_not_in_it"] > 0]
    return {
        "brands": rows,
        "brands_with_no_store_in_the_destination_list": absent,
        "brands_split_across_the_wedge": split,
        "why_split_matters": ("a chain on both sides means the wedge admits some branches and "
                              "not others, so two households the same distance from the same "
                              "chain get different answers -- arbitrary rather than conservative"),
        "name_matching_caveat": ("a brand name also appears on concessions inside a store -- a "
                                 "money-transfer desk, a fuel station, a pharmacy -- so rows are "
                                 "restricted to primaries that can be the store itself, and the "
                                 "counts are still an upper bound"),
    }


def brand_candidates(ov_inside: gpd.GeoDataFrame, grocery: gpd.GeoDataFrame):
    """The store rows a brand-based definition would add, as a frame to route and to inspect."""
    ids = set(grocery["id"])
    names = [overture_name(n) for n in ov_inside["names"]]
    prims = [t.get("primary") if isinstance(t, dict) else None for t in ov_inside["taxonomy"]]
    keep = []
    for k, (name, prim, pid) in enumerate(zip(names, prims, ov_inside["id"])):
        if pid in ids or prim not in STORE_PRIMARIES:
            continue
        low = name.lower()
        if any(b.lower() in low for b in HOUSEHOLD_BRANDS):
            keep.append(k)
    return ov_inside.iloc[keep]


# --------------------------------------------------------------------------- the routed impact


def destination_nodes(G, index, points) -> list[int]:
    if len(points) == 0:
        return []
    xs = np.array([p.x for p in points]); ys = np.array([p.y for p in points])
    nodes, dists = ox.nearest_nodes(G, xs, ys, return_dist=True)
    keep = np.asarray(dists, dtype=float) <= POI_SNAP_MAX_M
    return sorted({index[n] for n, k in zip(nodes, keep) if k})


def impact(G, csr, index, grocery, osm_unmatched, grid, limit=None, brand_frame=None) -> dict:
    """Verdicts at the structure population under three destination sets.

    Removing destinations can only lengthen a time, and adding them can only shorten one, so each
    comparison has a direction and the direction is what makes it a harm statement.
    """
    from locfinder.status import (CATEGORY_COST_SELECTED, Criterion, Reason,  # noqa: PLC0415
                                  Surface, evaluate)
    from locfinder.traveltime.arrival import (arrival_seconds,               # noqa: PLC0415
                                              arrival_seconds_two_weight)
    from locfinder.traveltime.snap import (EdgeIndex,                        # noqa: PLC0415
                                           cell_arrival_with_provenance)
    from locfinder.status import ENGINES, node_reasons                       # noqa: PLC0415

    ids, pts, _total = structure_population(
        METRO_DIR / "overture_buildings_accepted.parquet", grid)
    if limit:
        pts = pts[:limit]
    cost_csr, time_csr = csr
    idx = EdgeIndex.from_graph(G, index)

    cen = grocery.geometry.centroid
    published = destination_nodes(G, index, list(cen.values))
    status = np.array([str(s) == "permanently_closed" for s in grocery["operating_status"]])
    open_only = destination_nodes(G, index, list(cen[~status].values))
    plus_osm = sorted(set(published) | set(destination_nodes(
        G, index, list(osm_unmatched.geometry.centroid.values))))

    def surface_for(dest):
        T = arrival_seconds_two_weight(cost_csr, time_csr, dest_idx=dest)
        node_cost = arrival_seconds(cost_csr, dest_idx=dest)
        reasons = node_reasons(T, ENGINES["own-graph"], search_bounded=False)
        secs, reason, lower = cell_arrival_with_provenance(
            idx, T, pts[:, 0], pts[:, 1], mode=MODE, max_access_m=200.0, horizon_s=7200.0,
            node_reason=reasons, node_cost=node_cost)
        return Surface(mode=MODE, engine="own-graph", target=CATEGORY,
                       aggregation=CATEGORY_COST_SELECTED, horizon_s=7200.0,
                       seconds=secs, reason=reason, min_possible_s=lower).validate()

    plus_brands = sorted(set(published) | set(destination_nodes(
        G, index, list(brand_frame.geometry.centroid.values)))) if brand_frame is not None \
        else published
    surfaces = {"published": surface_for(published), "open_only": surface_for(open_only),
                "plus_unmatched_osm": surface_for(plus_osm),
                "plus_household_brands": surface_for(plus_brands)}
    out = {"structures": int(len(pts)),
           "destination_nodes": {"published": len(published), "open_only": len(open_only),
                                 "plus_unmatched_osm": len(plus_osm),
                                 "plus_household_brands": len(plus_brands)},
           "thresholds": {}}
    for t_min in THRESHOLDS_MIN:
        crit = Criterion(label=f"g{t_min}", mode=MODE, target=CATEGORY, kind="category",
                         threshold_s=float(t_min) * 60.0)
        v = {k: evaluate(crit, s) for k, s in surfaces.items()}
        inc = int(Verdict.INCLUDED)
        out["thresholds"][str(t_min)] = {
            "included_as_published": int((v["published"] == inc).sum()),
            "structures_served_only_by_a_closed_grocery":
                int(((v["published"] == inc) & (v["open_only"] != inc)).sum()),
            "structures_that_would_gain_if_the_unmatched_osm_shops_are_real":
                int(((v["published"] != inc) & (v["plus_unmatched_osm"] == inc)).sum()),
            "structures_that_would_gain_from_a_brand_based_definition":
                int(((v["published"] != inc) & (v["plus_household_brands"] == inc)).sum()),
        }
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-impact", action="store_true", help="skip the graph load")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", type=pathlib.Path, default=ARTIFACT)
    ap.add_argument("--sheet", type=pathlib.Path, default=SHEET)
    args = ap.parse_args(argv)

    grid = METRO.grid()
    ov = gpd.read_parquet(METRO_DIR / "overture_places_accepted.parquet").to_crs(grid.crs)
    osm = gpd.read_parquet(METRO_DIR / "osm_pois.parquet").to_crs(grid.crs)
    grocery = select_overture(ov, CATEGORY)
    osm_grocery = select_osm(osm, CATEGORY)

    report = {
        "what_this_is": ("step 7: the destination truth audit. E1 and E2 read one destination "
                         "list on both sides, so a closed, absent, misplaced or omitted grocery "
                         "produces agreement and two wrong answers"),
        "built": stamp(), "category": CATEGORY, "mode": MODE,
        "validity": validity(grocery),
    }

    G = None
    if not args.no_impact:
        t0 = time.perf_counter()
        from locfinder.traveltime.components import largest_component
        from locfinder.traveltime.csr import graph_to_cost_time_csr
        from locfinder.traveltime.speeds import add_travel_times, symmetrise
        G = load_roads_graph()
        G = ox.project_graph(G, to_crs=grid.crs)
        G = add_travel_times(G, mode=MODE)
        G = symmetrise(G)
        G.remove_nodes_from([n for n, d in G.degree() if d == 0])
        G, _comp = largest_component(G)
        cost_csr, time_csr, index = graph_to_cost_time_csr(G)
        print(f"graph ready in {time.perf_counter() - t0:.0f}s", flush=True)
        report["resolution"] = resolution(G, grocery)

    report["coverage"] = coverage(grocery, osm_grocery, grid)

    def inside_footprint(gdf):
        c = gdf.geometry.centroid
        x, y = c.x.to_numpy(), c.y.to_numpy()
        return ((x >= grid.x_min) & (x < grid.x_min + grid.ncols * grid.cell_m)
                & (y > grid.y_max - grid.nrows * grid.cell_m) & (y <= grid.y_max))

    ov_inside = ov[inside_footprint(ov)]
    report["brand_coverage"] = brand_coverage(grocery, ov_inside)
    brands = brand_candidates(ov_inside, grocery)
    report["brand_coverage"]["store_rows_a_brand_definition_would_add"] = int(len(brands))

    if G is not None:
        unmatched_ids = {r["osm_feature_id"]
                         for r in report["coverage"]["candidate_omitted_destinations"]}
        osm_unmatched = osm_grocery[[str(i) in unmatched_ids for i in osm_grocery.index]]
        report["impact"] = impact(G, (cost_csr, time_csr), index, grocery, osm_unmatched,
                                  grid, limit=args.limit, brand_frame=brands)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    rows = report["coverage"]["candidate_omitted_destinations"]
    if rows:
        args.sheet.parent.mkdir(parents=True, exist_ok=True)
        fields = sorted({k for r in rows for k in r})
        with args.sheet.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields + ["is_a_real_grocery", "checked_on", "note"])
            w.writeheader()
            for r in rows:
                w.writerow({**r, "is_a_real_grocery": "", "checked_on": "", "note": ""})
    print_summary(report, args)
    return 0


def print_summary(report: dict, args) -> None:
    v = report["validity"]
    print(f"\nVALIDITY -- {v['places']} grocery places")
    print(f"  operating_status: {v['operating_status']}")
    print(f"  PERMANENTLY CLOSED and still published as destinations: "
          f"{len(v['permanently_closed'])}")
    for p in v["permanently_closed"]:
        print(f"      {p['name'] or '(unnamed)':38s} conf {p['confidence']:.2f}  "
              f"{p['lat']:.5f},{p['lon']:.5f}")
    print(f"  confidence below 0.5: {v['confidence']['below_0_5']}, "
          f"below 0.3: {v['confidence']['below_0_3']}")

    if "resolution" in report:
        r = report["resolution"]
        print(f"\nRESOLUTION -- snap cap {r['snap_cap_m']:.0f} m")
        print(f"  dropped by the cap: {r['dropped_by_the_cap']}  "
              f"| 200-300 m from a node: {r['snap_distance_m']['between_200_and_300m']}")
        print(f"  {r['kept_by_the_cap']} places on {r['distinct_nodes']} nodes; "
              f"{r['places_sharing_a_node']} share a node with another place "
              f"(largest share {r['largest_node_share']})")

    b = report.get("brand_coverage")
    if b:
        print("\nBRAND COVERAGE -- stores a household would name:")
        print(f"  {'brand':24s} {'destinations':>12s} {'store rows not in the list':>28s}")
        for r in b["brands"]:
            if r["store_rows_not_in_it"]:
                print(f"  {r['brand']:24s} {r['in_the_destination_list']:>12d} "
                      f"{r['store_rows_not_in_it']:>28d}  "
                      f"{', '.join(f'{k}x{v}' for k, v in r['their_primaries'].items())}")
        print(f"  NO store in the destination list: "
              f"{', '.join(b['brands_with_no_store_in_the_destination_list']) or 'none'}")
        print(f"  SPLIT across the wedge (some branches in, some out): "
              f"{', '.join(b['brands_split_across_the_wedge']) or 'none'}")
        print(f"  store rows a brand-based definition would add: "
              f"{b['store_rows_a_brand_definition_would_add']}")

    c = report["coverage"]
    print(f"\nCOVERAGE -- inside the footprint: {c['inside_the_footprint']}")
    print(f"  OSM supermarkets with no Overture grocery within 300 m: "
          f"{len(c['candidate_omitted_destinations'])}")
    print(f"  wrote the sheet to check: {args.sheet}")

    if "impact" in report:
        print(f"\nIMPACT over {report['impact']['structures']:,} structures:")
        for t_min, row in report["impact"]["thresholds"].items():
            print(f"  T={t_min:>2} min: {row['included_as_published']:,} included; "
                  f"{row['structures_served_only_by_a_closed_grocery']:,} served ONLY by a "
                  f"closed grocery; "
                  f"{row['structures_that_would_gain_if_the_unmatched_osm_shops_are_real']:,} "
                  f"would gain from the unmatched OSM shops; "
                  f"{row['structures_that_would_gain_from_a_brand_based_definition']:,} "
                  f"from a brand-based definition")
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
