"""Name the grocery each audited journey was actually routed to.

The walked-audit sheet gives a start coordinate and no destination, so the owner cannot time our
journey -- only their own. `docs/experiments/audit/README.md` calls recovering the destination
"the decisive version of this audit". This is that recovery.

It rebuilds the published layer's exact configuration, keeps the destination identity that
`arrival_with_selected_destination` now returns, and resolves it to the grocery places that snap
to that node. Then it **re-derives each row's seconds and checks them against the sheet**: a
destination recovered from a different graph than the one that produced the number would be a
confident wrong answer, which is worse than the blank column it replaces.

One graph load, about a minute. Writes a new sheet rather than editing the owner's, which may be
open in a spreadsheet.

    python scripts/recover_audit_destinations.py \
        ../docs/experiments/audit/triangle-grocery-walk-chapelhill.csv

A destination node can carry several places (550 grocery places snap to 510 nodes), so the
resolution is one-to-many and every candidate at the chosen node is listed. The owner walks to the
one they would use and records which.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import pathlib
import sys
import time

import geopandas as gpd
import numpy as np
import osmnx as ox
from pyproj import Transformer

# The spikes are normally run as `uv run python spikes/...` from v2/, where the package is
# installed. Run as a plain script, only scripts/ lands on sys.path, so both the package root and
# spikes/ have to be added before `_common` -- which itself imports locfinder.
V2 = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V2))
sys.path.insert(1, str(V2 / "spikes"))
from _common import ACCEPTED_PLACES, GRAPH_CACHE, GRID  # noqa: E402

from locfinder.places.categories import select_overture  # noqa: E402
from locfinder.traveltime.arrival import arrival_seconds, arrival_with_selected_destination  # noqa: E402
from locfinder.traveltime.components import largest_component  # noqa: E402
from locfinder.traveltime.csr import graph_to_cost_time_csr  # noqa: E402
from locfinder.traveltime.snap import (  # noqa: E402
    EdgeIndex,
    cell_selected_destination,
    cell_seconds_from_arrival,
)
from locfinder.traveltime.speeds import add_travel_times, symmetrise  # noqa: E402

# These must match the published layer. They are duplicated from spikes/s0_status_on_real_layer.py
# deliberately and asserted against that run's recorded provenance below, so a drift shows up as a
# failure rather than as a quietly different answer.
POI_SNAP_MAX_M = 300.0
MAX_ACCESS_M = 200.0
CUTOFF_MIN = 120.0
HORIZON_S = CUTOFF_MIN * 60.0
MODE = "walk"
CATEGORY = "grocery"

PROVENANCE = V2 / "data" / "s0_status_triangle_grocery_walk.json"
RASTER = V2 / "data" / "layers" / "own_triangle_grocery_walk.npy"

# Added columns, in order. The owner's observation columns are untouched.
NEW_COLUMNS = [
    "predicted_destination",
    "predicted_destination_lat",
    "predicted_destination_lon",
    "predicted_destination_osm_link",
    "predicted_destination_alternatives",
    "predicted_seconds_recheck",
    "recheck_matches_sheet",
]


def place_label(names) -> str:
    """Overture stores `names` as a struct; `primary` is the display name.

    All 550 Triangle grocery places have one, but an unnamed destination must still produce a
    walkable row -- the coordinate is what the owner navigates to, the name only helps them
    recognise it.
    """
    if isinstance(names, dict):
        name = names.get("primary") or names.get("common") or ""
    else:
        name = names or ""
    return str(name).strip() or "(unnamed grocery)"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet", type=pathlib.Path)
    ap.add_argument("--out", type=pathlib.Path, default=None,
                    help="default: alongside the input, with -with-destinations appended")
    ap.add_argument("--force", action="store_true",
                    help="overwrite an existing output sheet, discarding anything written into it")
    args = ap.parse_args()

    rows = list(csv.DictReader(args.sheet.open(encoding="utf-8-sig")))
    if not rows:
        print(f"{args.sheet}: no rows")
        return 1
    print(f"{args.sheet.name}: {len(rows)} journeys")

    # ---- rebuild the published configuration -------------------------------------------------
    t = time.perf_counter()
    G = ox.load_graphml(GRAPH_CACHE)
    print(f"graph loaded in {time.perf_counter() - t:.1f}s: {G.number_of_nodes():,} nodes",
          flush=True)
    t = time.perf_counter()
    G = ox.project_graph(G, to_crs=GRID.crs)
    G = add_travel_times(G, mode=MODE)
    if MODE == "walk":
        G = symmetrise(G)
    G.remove_nodes_from([n for n, d in G.degree() if d == 0])
    G, comp = largest_component(G)
    print(f"prepared in {time.perf_counter() - t:.1f}s: {comp.summary}", flush=True)

    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
    places = gpd.read_parquet(ACCEPTED_PLACES).to_crs(GRID.crs)
    sel = select_overture(places, CATEGORY)
    cent = sel.geometry.centroid
    nodes, dists = ox.nearest_nodes(G, cent.x.to_numpy(), cent.y.to_numpy(), return_dist=True)
    keep = np.asarray(dists) <= POI_SNAP_MAX_M

    # node index -> the places that snapped to it. This association is the thing the layer build
    # never kept; without it a recovered node id is not a shop.
    node_to_places: dict[int, list[int]] = {}
    for pos, (n, k) in enumerate(zip(nodes, keep)):
        if k:
            node_to_places.setdefault(index[n], []).append(pos)
    dest_idx = sorted(node_to_places)
    print(f"destinations: {len(dest_idx)} nodes from {len(sel)} places "
          f"({int((~keep).sum())} dropped beyond {POI_SNAP_MAX_M:.0f} m)", flush=True)

    # What this check is and is not. It compares three COUNTS against s0's recorded provenance.
    # Codex pass 33 F2 showed that is much weaker than I claimed: swapping destination node
    # 539680 for 500268 preserves every sampled value in both sheets while changing 1,798 node
    # times, so matching counts cannot establish that the destination SET is the published one.
    # The recorded provenance does not store the set itself, so with the artifacts on hand this
    # is the strongest available check, not a proof. The honest claim is "nothing detectably
    # differs", and the full-raster comparison below is what actually bounds the disagreement.
    if PROVENANCE.exists():
        prov = json.loads(PROVENANCE.read_text(encoding="utf-8"))
        expect = prov.get("destinations", {})
        got = {"places": int(len(sel)), "nodes": len(dest_idx),
               "dropped_beyond_snap": int((~keep).sum())}
        if expect and expect != got:
            print(f"FAIL: destination counts differ from {PROVENANCE.name}\n"
                  f"  recorded: {expect}\n  rebuilt : {got}\n"
                  "A destination recovered from a different graph than the published numbers "
                  "would be a confident wrong answer. Refusing to write the sheet.")
            return 1
        print(f"destination counts match {PROVENANCE.name}: {got}", flush=True)
        print("  (counts only -- the recorded provenance does not store the node set, so this "
              "cannot prove set identity)", flush=True)

    t = time.perf_counter()
    # Unbounded, matching `layer.py:139` -- the published builder runs the arrival search with no
    # cutoff ("which is what entitles this call to NO_PATH") and applies the horizon to the final
    # per-cell total instead. Codex pass 33 confirmed the two give identical seconds on all
    # 330,502 cells, but matching the builder's call removes the question rather than relying on
    # the equivalence holding.
    T, selected = arrival_with_selected_destination(cost_csr, time_csr, dest_idx=dest_idx)
    node_cost = np.asarray(arrival_seconds(cost_csr, dest_idx=dest_idx))
    print(f"arrival + selection in {time.perf_counter() - t:.1f}s", flush=True)
    eidx = EdgeIndex.from_graph(G, index)

    # ---- resolve each journey, at the exact cell centre --------------------------------------
    # The published answer is the CELL's, computed at the centre in projected metres. The sheet's
    # query_lon/query_lat are that centre rendered to six decimal places, which is about 0.1 m --
    # enough to move the snapped journey by about a tenth of a second. Re-projecting the rounded
    # pair therefore does NOT reproduce the published number: it disagreed on 3 of 16 rows, which
    # my first tolerance-based check reported as a configuration mismatch. Rebuilding from
    # (row, col) removes the round trip, so the comparison below can be exact.
    rc = [(int(r["row"]), int(r["col"])) for r in rows]
    for i, (rr, cc) in enumerate(rc):
        if not (0 <= rr < GRID.nrows and 0 <= cc < GRID.ncols):
            print(f"FAIL: {rows[i]['journey_id']} names cell ({rr}, {cc}), outside the "
                  f"{GRID.nrows}x{GRID.ncols} grid")
            return 1
    # Indexed out of the grid's own centres rather than recomputed here: the layer used this
    # function, and a second copy of the arithmetic is a second thing to keep in step.
    centre_x, centre_y = GRID.cell_centers_xy()
    sel_rows = np.array([r for r, _c in rc])
    sel_cols = np.array([c for _r, c in rc])
    xs = centre_x[sel_rows, sel_cols]
    ys = centre_y[sel_rows, sel_cols]

    # The sheet's own coordinate must still land in the row it claims, or the two halves of the
    # sheet describe different places.
    lon = np.array([float(r["query_lon"]) for r in rows])
    lat = np.array([float(r["query_lat"]) for r in rows])
    for i, r in enumerate(rows):
        where = GRID.cell_for_lonlat(float(lon[i]), float(lat[i]))
        if where != rc[i]:
            print(f"FAIL: {r['journey_id']} says cell {rc[i]} but its coordinate is in {where}")
            return 1
    tr = Transformer.from_crs("EPSG:4326", GRID.crs, always_xy=True)
    qx, qy = (np.asarray(a, dtype=np.float64) for a in tr.transform(lon, lat))
    rounding_m = np.hypot(qx - xs, qy - ys)
    print(f"sheet coordinate vs exact cell centre: max {rounding_m.max():.4f} m "
          f"(six-decimal rendering)", flush=True)

    kw = dict(mode=MODE, max_access_m=MAX_ACCESS_M, node_cost=node_cost, cutoff_s=HORIZON_S)
    secs = cell_seconds_from_arrival(eidx, T, xs, ys, **kw)
    dest_node = cell_selected_destination(eidx, T, xs, ys, selected=selected, **kw)

    places_ll = sel.to_crs("EPSG:4326")
    raster = np.load(RASTER)
    if raster.shape != (GRID.nrows, GRID.ncols):
        print(f"FAIL: {RASTER.name} is {raster.shape}, grid is "
              f"{(GRID.nrows, GRID.ncols)}; these are different layers")
        return 1

    # The whole layer, not just the sampled rows. Codex pass 33 F2: agreement on 35 sampled cells
    # was being read as "this is the published configuration", and the full surface disagrees on
    # 7,246 cells. Measuring it here means the sheet can never again be produced with that
    # disagreement unstated.
    full = np.asarray(
        cell_seconds_from_arrival(eidx, T, *GRID.cell_centers_xy(), **kw), dtype=np.float64)
    differing = int((raster != full.astype(np.float32)).sum())
    if differing:
        same_finite = bool(np.array_equal(np.isfinite(raster), np.isfinite(full)))
        print(f"\nWARNING: the committed {RASTER.name} differs from a current-code rebuild on "
              f"{differing:,} of {raster.size:,} cells ({differing / raster.size:.3%}); "
              f"finiteness identical: {same_finite}.")
        print("  The raster was built 2026-11-04 13:42 and `ab01ffa` at 21:12 then fixed "
              "`symmetrise`, which had been suppressing pedestrian reverse edges.")
        print("  The sheet's numbers came from the committed raster, so the destinations below "
              "are recovered with CURRENT code and agree with it on every sampled row -- which is "
              "consistent with, but not proof of, the historical choice. Rebuild the layer to "
              "remove the question.")
    else:
        print(f"\nthe committed {RASTER.name} matches a current-code rebuild on all "
              f"{raster.size:,} cells")
    mismatches = 0
    for i, row in enumerate(rows):
        node = int(dest_node[i])
        if node < 0:
            row["predicted_destination"] = "(none: no published journey)"
            for c in NEW_COLUMNS[1:5]:
                row[c] = ""
        else:
            cands = node_to_places[node]
            first = cands[0]
            p = places_ll.iloc[first]
            row["predicted_destination"] = place_label(sel["names"].iloc[first])
            row["predicted_destination_lat"] = f"{p.geometry.centroid.y:.6f}"
            row["predicted_destination_lon"] = f"{p.geometry.centroid.x:.6f}"
            row["predicted_destination_osm_link"] = (
                f"https://www.openstreetmap.org/?mlat={p.geometry.centroid.y:.6f}"
                f"&mlon={p.geometry.centroid.x:.6f}#map=18/"
                f"{p.geometry.centroid.y:.6f}/{p.geometry.centroid.x:.6f}")
            others = [place_label(sel["names"].iloc[j]) for j in cands[1:]]
            row["predicted_destination_alternatives"] = "; ".join(others)

        # Against the committed raster, cast the same way it was stored. Quantisation to float32
        # is a known function, not an unknown error to absorb in a tolerance: s0's check learned
        # that a 0.01 s tolerance accepted stored 600.005 against rebuilt 599.999, a pair that
        # straddles a threshold and so changes the published verdict. Equality after the same cast
        # cannot do that.
        got = float(secs[i])
        row["predicted_seconds_recheck"] = "" if not math.isfinite(got) else f"{got:.1f}"
        i_row, i_col = rc[i]
        stored = float(raster[i_row, i_col])
        rebuilt32 = float(np.float32(got))

        # BOTH comparisons, because they can disagree and each catches a different thing.
        # Codex pass 33 F4: the first version compared the rebuild only against the raster, so a
        # sheet whose own `seconds` column had been edited to 1.0 still got
        # `recheck_matches_sheet = yes`. A stale or hand-edited sheet would receive destinations
        # belonging to a different prediction, and be told they agreed.
        vs_raster = (rebuilt32 == stored) if (math.isfinite(stored) and math.isfinite(rebuilt32)) \
            else (not math.isfinite(stored) and not math.isfinite(rebuilt32))
        sheet_s = (row.get("seconds") or "").strip()
        if sheet_s:
            # The sheet renders one decimal place, so compare at that rendering rather than
            # inventing a tolerance.
            vs_sheet = math.isfinite(rebuilt32) and f"{rebuilt32:.1f}" == f"{float(sheet_s):.1f}"
        else:
            vs_sheet = not math.isfinite(rebuilt32)

        row["recheck_matches_sheet"] = "yes" if (vs_raster and vs_sheet) else "NO"
        if not (vs_raster and vs_sheet):
            mismatches += 1
            why = []
            if not vs_raster:
                why.append(f"raster {stored!r} vs rebuilt {rebuilt32!r}")
            if not vs_sheet:
                why.append(f"sheet column {sheet_s!r} vs rebuilt {rebuilt32:.1f}")
            print(f"  {row['journey_id']}: " + "; ".join(why))

    # ---- verify BEFORE opening the output ----------------------------------------------------
    # Codex pass 33 F3: the first version checked `mismatches` after writing, so a run that
    # reported a verification failure had already written the sheet -- and could have replaced a
    # good one with unverified destinations. The docstring claimed it refused to write. Now it
    # does.
    named = sum(1 for r in rows if r["predicted_destination"]
                and not r["predicted_destination"].startswith("(none"))
    agreed = sum(1 for r in rows if r["recheck_matches_sheet"] == "yes")
    print(f"\n  {named} of {len(rows)} journeys name a destination")
    print(f"  seconds agree with both the raster and the sheet on {agreed} rows, "
          f"{mismatches} mismatched")
    if mismatches:
        print("\nREFUSING TO WRITE. A mismatch means this rebuild is not the configuration behind "
              "the sheet, so the destinations would not be the ones its numbers describe.")
        return 1

    out = args.out or args.sheet.with_name(args.sheet.stem + "-with-destinations.csv")
    # Codex pass 33 F1: the first version opened this with "w" and no guard, so rerunning the
    # documented command would erase walked observations the owner had typed into it.
    # `audit_recommendations.py` already refuses to overwrite a sheet for exactly this reason and
    # this script did not copy that.
    if out.exists() and not args.force:
        print(f"\n{out} already exists and may hold walked observations. "
              f"Refusing to overwrite it; pass --force if you mean to.")
        return 1
    fieldnames = list(rows[0].keys())
    for c in NEW_COLUMNS:
        if c not in fieldnames:
            fieldnames.append(c)
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
