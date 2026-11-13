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
import re
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
    "Whole Foods", "Walmart", "Wal-Mart", "Target", "Wegmans",
    "Weaver Street", "Sprouts", "Fresh Market", "Compare Foods", "Grand Asia", "H Mart",
    "Costco", "Sam's Club", "BJ's",
    # Pass 45 F6: the first list omitted chains that are PRESENT AND SELECTED, so the table read
    # as a list of failures rather than a coverage picture. These are here to be counted on the
    # "in the destination list" side as much as the other.
    "Lowes Foods", "Carlie", "Save A Lot", "Chatham Marketplace", "Li Ming", "Food World",
)

#: Name fragments that mean the row is **not the store** even though it carries the brand.
#: Pass 45 F2: `STORE_PRIMARIES` admitting `None` let in "Harris Teeter Fuel Center", and
#: `department_store` let in "TARGET PharmaSolutions", a pharmaceutical company. An included
#: "Weaver Street Market Administration" row is the same error on the other side of the wedge.
NOT_THE_STORE = ("fuel", "gas station", "pharmasolutions", "administration", "corporate",
                 "office", "optical", "vision", "pharmacy", "wireless", "money", "atm",
                 "distribution", "warehouse club services")

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


def brand_hit(name: str, brand: str) -> bool:
    """Whole-word brand matching, and not a substring.

    Pass 45 F2: `"aldi" in name.lower()` matched **Mariachi Garib-ALDI-** NC and counted a mariachi
    band as an omitted Aldi branch. A word boundary fixes that class. It does not fix a genuine
    name collision -- "Las Carolinas Fresh Market" still matches "Fresh Market", because it really
    does contain that phrase -- so the collision is disclosed rather than regexed away.
    """
    return re.search(rf"(?<![A-Za-z]){re.escape(brand)}(?![A-Za-z])", name, re.IGNORECASE) is not None


def is_the_store(name: str) -> bool:
    low = name.lower()
    return not any(frag in low for frag in NOT_THE_STORE)


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
        hits = [k for k, n in enumerate(names) if brand_hit(n, brand)]
        if not hits:
            continue
        inside_n = sum(1 for k in hits if in_wedge[k] and is_the_store(names[k]))
        inside_not_store = sum(1 for k in hits if in_wedge[k] and not is_the_store(names[k]))
        outside = [k for k in hits if not in_wedge[k] and prims[k] in STORE_PRIMARIES
                   and is_the_store(names[k])]
        if inside_n == 0 and not outside:
            continue
        rows.append({
            "brand": brand,
            "in_the_destination_list": inside_n,
            "in_the_list_but_not_a_store_row": inside_not_store,
            "store_rows_not_in_it": len(outside),
            "their_primaries": dict(Counter(p or "(none)" for p in (prims[k] for k in outside))),
            "excluded_row_names": [names[k] for k in outside][:6],
        })
    absent = [r["brand"] for r in rows
              if r["in_the_destination_list"] == 0 and r["store_rows_not_in_it"] > 0]
    # Pass 45 F2: a chain with rows on both sides is not necessarily a chain whose BRANCHES are
    # split -- the excluded row may be a concession, a duplicate representation of an included
    # branch, or a stale record. This counter is therefore named for what it measures.
    split = [r["brand"] for r in rows
             if r["in_the_destination_list"] > 0 and r["store_rows_not_in_it"] > 0]
    return {
        "brands": rows,
        "brands_with_no_store_in_the_destination_list": absent,
        "brands_with_store_rows_on_both_sides": split,
        "what_both_sides_does_and_does_not_mean": (
            "rows on both sides is NOT by itself a split chain. Pass 45 F2 checked each: Harris "
            "Teeter's only excluded row was a fuel centre; Lidl's excluded store shares an "
            "address with an INCLUDED record whose brand is Lidl, so that branch is already "
            "represented; Kroger's excluded record sits 13 m from an included Harris Teeter, so "
            "its current identity is unresolved. Real taxonomy inconsistency remains after those "
            "are removed, but the branch-level claim does not follow from this table"),
        "name_matching_caveat": ("whole-word matching plus a not-the-store name filter, after "
                                 "pass 45 F2 found a mariachi band counted as an Aldi branch "
                                 "(Garib-ALDI), a pharmaceutical company counted as a Target, and "
                                 "a fuel centre counted as a Harris Teeter. Genuine collisions "
                                 "remain -- 'Las Carolinas Fresh Market' really does contain "
                                 "'Fresh Market' -- and the counts are still records, not "
                                 "physical stores: nothing here deduplicates two rows for one "
                                 "shop"),
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
        if is_the_store(name) and any(brand_hit(name, b) for b in HOUSEHOLD_BRANDS):
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
    """Verdicts under four destination sets, at structure coordinates **and** at cell centres.

    **The monotonicity this used to assert is false, and the reason is this project's central
    distinction.** The docstring said "removing destinations can only lengthen a time, and adding
    them can only shorten one". Pass 45 F3 refuted it in three lines: the search minimises **cost**
    and reports **time**, so adding a cheaper destination can select a slower journey. On costs
    `(700, 650)` with times `(500, 650)`, adding the second destination turns 500 s into 650 s --
    a ten-minute pass into a fail. So every comparison below reports **both** directions, and
    "served only by" is replaced with a transition count.

    The two evaluation units are both reported because step 5 measured them differing on 2.2-2.5%
    of structures: the coordinate answer is model sensitivity, and the containing cell's answer is
    what the product publishes for that structure.
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

    # Each structure's containing cell centre, for the published-answer unit.
    col = np.floor((pts[:, 0] - grid.x_min) / grid.cell_m)
    row = np.floor((grid.y_max - pts[:, 1]) / grid.cell_m)
    cx = grid.x_min + (np.clip(col, 0, grid.ncols - 1) + 0.5) * grid.cell_m
    cy = grid.y_max - (np.clip(row, 0, grid.nrows - 1) + 0.5) * grid.cell_m

    def surface_for(dest, at_cell_centres=False):
        T = arrival_seconds_two_weight(cost_csr, time_csr, dest_idx=dest)
        node_cost = arrival_seconds(cost_csr, dest_idx=dest)
        reasons = node_reasons(T, ENGINES["own-graph"], search_bounded=False)
        xs, ys = (cx, cy) if at_cell_centres else (pts[:, 0], pts[:, 1])
        secs, reason, lower = cell_arrival_with_provenance(
            idx, T, xs, ys, mode=MODE, max_access_m=200.0, horizon_s=7200.0,
            node_reason=reasons, node_cost=node_cost)
        return Surface(mode=MODE, engine="own-graph", target=CATEGORY,
                       aggregation=CATEGORY_COST_SELECTED, horizon_s=7200.0,
                       seconds=secs, reason=reason, min_possible_s=lower).validate()

    explicit_open = destination_nodes(
        G, index, list(cen[np.array([str(s) == "open" for s in grocery["operating_status"]])]
                       .values))
    plus_brands = sorted(set(published) | set(destination_nodes(
        G, index, list(brand_frame.geometry.centroid.values)))) if brand_frame is not None \
        else published
    sets = {"published": published,
            # Pass 45: "open_only" was a misleading name -- it keeps the 106 records with NO
            # status. That is the right counterfactual for "remove the flagged records", and it is
            # now named for that. The much stricter "only records explicitly marked open" is
            # reported beside it, because the two differ by an order of magnitude.
            "without_flagged_records": open_only,
            "explicitly_open_only": explicit_open,
            "plus_unmatched_osm": plus_osm,
            "plus_household_brands": plus_brands}
    surfaces = {k: surface_for(v) for k, v in sets.items()}
    cell_surfaces = {k: surface_for(v, at_cell_centres=True) for k, v in sets.items()}
    out = {"structures": int(len(pts)),
           "destination_nodes": {k: len(v) for k, v in sets.items()},
           "nodes_changed_against_published": {
               k: {"removed": len(set(published) - set(v)), "added": len(set(v) - set(published))}
               for k, v in sets.items() if k != "published"},
           "units": ("'direct' evaluates each structure's own coordinate, 'cell' evaluates the "
                     "centre of the cell that structure falls in, which is what the product "
                     "publishes for it"),
           "thresholds": {}}
    inc = int(Verdict.INCLUDED)
    for t_min in THRESHOLDS_MIN:
        crit = Criterion(label=f"g{t_min}", mode=MODE, target=CATEGORY, kind="category",
                         threshold_s=float(t_min) * 60.0)
        row_out = {}
        for unit, surf_set in (("direct", surfaces), ("cell", cell_surfaces)):
            v = {k: evaluate(crit, s) for k, s in surf_set.items()}
            base = v["published"]
            entry = {"included_as_published": int((base == inc).sum())}
            for name in sets:
                if name == "published":
                    continue
                # BOTH directions, because the cost/time split makes neither monotone.
                entry[name] = {
                    "lost_inclusion": int(((base == inc) & (v[name] != inc)).sum()),
                    "gained_inclusion": int(((base != inc) & (v[name] == inc)).sum()),
                }
                entry[name]["net"] = (entry[name]["gained_inclusion"]
                                      - entry[name]["lost_inclusion"])
            # Pass 45 F: the two candidate additions were claimed to "overlap rather than add".
            # That is a number, not an argument -- the top of the OSM sheet is the same stores the
            # brand question is about, so the gain sets intersect.
            gained_osm = (base != inc) & (v["plus_unmatched_osm"] == inc)
            gained_brand = (base != inc) & (v["plus_household_brands"] == inc)
            entry["gains_in_both_osm_and_brand_sets"] = int((gained_osm & gained_brand).sum())
            entry["gains_in_either"] = int((gained_osm | gained_brand).sum())
            row_out[unit] = entry
        out["thresholds"][str(t_min)] = row_out
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
        print(f"  store rows on BOTH sides (not the same as a split chain -- see the note): "
              f"{', '.join(b['brands_with_store_rows_on_both_sides']) or 'none'}")
        print(f"  store rows a brand-based definition would add: "
              f"{b['store_rows_a_brand_definition_would_add']}")

    c = report["coverage"]
    print(f"\nCOVERAGE -- inside the footprint: {c['inside_the_footprint']}")
    print(f"  OSM supermarkets with no Overture grocery within 300 m: "
          f"{len(c['candidate_omitted_destinations'])}")
    print(f"  wrote the sheet to check: {args.sheet}")

    if "impact" in report:
        print(f"\nIMPACT over {report['impact']['structures']:,} structures:")
        print(f"  nodes changed vs published: "
              f"{report['impact']['nodes_changed_against_published']}")
        for t_min, row in report["impact"]["thresholds"].items():
            for unit in ("direct", "cell"):
                e = row[unit]
                bits = "  ".join(
                    f"{k}: -{v['lost_inclusion']:,}/+{v['gained_inclusion']:,}"
                    for k, v in e.items() if isinstance(v, dict))
                print(f"  T={t_min:>2} {unit:6s} included {e['included_as_published']:,}   {bits}")
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
