"""Can Foursquare OS Places reach the records OSM cannot?

**Owner decision, 2026-11-17**: run this measurement. It is the one named in
`docs/engineering-notes/reference-places-provider-needed.md` as the thing to do before choosing a
places provider, because it settles the only objection to FSQ with a number instead of an argument.

**The question.** `prefill_from_osm.py` leaves 154 grocery and 180 pharmacy records with *no OSM
feature within 120 m* -- OSM is silent, not negative. Does FSQ OS Places hold anything for them?

**Why FSQ and not Yelp.** Yelp's API terms cap storage of Yelp content at 24 hours, so a Yelp
category cannot be written into a committed table and published; FSQ OS Places is Apache 2.0, free,
and distributed as Parquet. See the note for the full reasoning and for Decision 17.

**The objection this tests.** Foursquare also contributes to Overture, and our places come *from*
Overture. If FSQ's records are already in our extract, FSQ adds nothing for exactly the records
that need it. That is a real possibility and nobody had measured it.

**Comparability is the point.** This reuses `prefill_from_osm`'s own `name_agreement`, its score
formula and its 0.34 agreement threshold, and the same 120 m radius. A second scoring rule would
make the two passes incomparable, which would defeat the measurement.

**What it does not do.** It does not edit any table. It writes a sheet with a blank `verdict`
column, exactly as the OSM pass does. A proposal is a starting point for a human.

Run from `v2/`:
    python scripts/measure_fsq_coverage.py --category grocery
    python scripts/measure_fsq_coverage.py --category pharmacy

The FSQ snapshot is downloaded once into `--snapshot` (default: under `data/triangle/`) and reused.
Source: the public Source Cooperative mirror of FSQ OS Places, which needs no credentials.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

V2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V2 / "spikes"))
sys.path.insert(0, str(V2))
sys.path.insert(0, str(V2 / "scripts"))

from _common import ACCEPTED_PLACES, GRID  # noqa: E402
from locfinder.places.categories import select_target  # noqa: E402
from prefill_from_osm import OSM_POIS, name_agreement, place_name  # noqa: E402

AUDIT = V2.parent / "docs" / "experiments" / "audit"

#: The public mirror. Apache 2.0, no credentials, dated release path so a build can name its
#: snapshot -- which a live API can never offer.
FSQ_RELEASE = "2025-01-10"
FSQ_PARQUET = (
    "s3://us-west-2.opendata.source.coop/fused/fsq-os-places/"
    f"{FSQ_RELEASE}/places/*.parquet"
)

#: FSQ category label -> what it proposes. Built from the labels actually present in the Triangle
#: bbox, not guessed. Anything unlisted proposes nothing AND IS REPORTED, so a label we have never
#: seen cannot be silently dropped into "no match".
#:
#: The entry worth noticing: FSQ separates **Supermarket** from **Grocery Store** from
#: **Convenience Store**. OSM's single `shop=supermarket` cannot make that distinction, and it is
#: exactly the "range" signal `OSM_CONFIRMED_SPECIALTY` records as missing. FSQ's own line between
#: supermarket and grocery store is its editorial judgement rather than a measurement, so a
#: `Grocery Store` proposal is deliberately NOT called a supermarket here.
PROPOSALS: dict[str, dict[str, str]] = {
    "grocery": {
        "Retail > Food and Beverage Retail > Supermarket": "supermarket",
        "Retail > Food and Beverage Retail > Grocery Store": (
            "grocery store (FSQ separates this from supermarket -- needs a human)"
        ),
        "Retail > Food and Beverage Retail > Grocery Store > Organic Grocery": "specialty",
        "Retail > Food and Beverage Retail > Health Food Store": "specialty",
        "Retail > Food and Beverage Retail > Gourmet Store": "specialty",
        "Retail > Food and Beverage Retail > Farmers Market": "specialty",
        "Retail > Food and Beverage Retail > Fish Market": "specialty",
        "Retail > Food and Beverage Retail > Butcher": "specialty",
        "Retail > Food and Beverage Retail > Bakery": "specialty",
        "Retail > Food and Beverage Retail > Candy Store": "specialty",
        "Retail > Food and Beverage Retail > Dairy Store": "specialty",
        "Retail > Convenience Store": "convenience (not a weekly shop)",
        "Retail > Market": "market (unspecific -- needs a human)",
        "Retail > Food and Beverage Retail": "food retail (unspecific -- needs a human)",
        "Retail > Food and Beverage Retail > Liquor Store": "not a grocery",
        "Retail > Food and Beverage Retail > Beer Store": "not a grocery",
        "Retail > Food and Beverage Retail > Wine Store": "not a grocery",
        "Retail > Warehouse or Wholesale Store": "supermarket",
    },
    "pharmacy": {
        "Retail > Pharmacy": "pharmacy",
        "Retail > Drugstore": "drugstore (may not dispense -- needs a human)",
        "Health and Medicine > Hospital": "not a retail pharmacy",
        "Health and Medicine > Medical Center": "not a retail pharmacy",
        "Health and Medicine > Healthcare Clinic": "not a retail pharmacy",
        "Health and Medicine > Urgent Care Center": "not a retail pharmacy",
        "Health and Medicine > Physician": "not a retail pharmacy",
        "Health and Medicine > Physician > Doctor's Office": "not a retail pharmacy",
        "Health and Medicine > Dentist": "not a retail pharmacy",
        "Health and Medicine > Veterinarian": "not a retail pharmacy",
        "Health and Medicine > Medical Lab": "not a retail pharmacy",
        "Health and Medicine > Home Health Care Service": "not a retail pharmacy",
        "Health and Medicine": "health (unspecific -- needs a human)",
    },
}

#: Same threshold the OSM pass prints its "names agree" verdict at.
AGREE = 0.34

#: Words by which a record's OWN name asserts the category, and the proposals that DENY it.
#:
#: A proposal that denies what the name asserts is evidence against the PROVIDER'S CATEGORY, not
#: against the record. This check exists because spot-checking found FSQ calling "Fuquay Pharmacy"
#: a dentist and "Kroger Pharmacy" a doctor's office. Without it, a headline count of proposals
#: hides the ones that would delete a real destination.
SELF_DESCRIBING: dict[str, tuple[str, str]] = {
    "grocery": (r"supermarket|grocer|market|foods?\b", "not a grocery"),
    "pharmacy": (r"pharmac|drug|apothecar|\brx\b", "not a retail pharmacy"),
}


def fetch_snapshot(snapshot: Path, bounds: tuple[float, float, float, float]) -> None:
    """Download the FSQ places inside `bounds` once, to a local parquet."""
    import duckdb

    minx, miny, maxx, maxy = bounds
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs; SET enable_progress_bar=false;")
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    con.execute(
        f"""
        COPY (
            SELECT fsq_place_id, name, latitude, longitude, address, locality, region,
                   date_closed, fsq_category_labels
            FROM read_parquet('{FSQ_PARQUET}')
            WHERE bbox.xmin BETWEEN {minx} AND {maxx}
              AND bbox.ymin BETWEEN {miny} AND {maxy}
        ) TO '{snapshot.as_posix()}' (FORMAT PARQUET)
        """
    )
    con.close()


def load_fsq(snapshot: Path, bounds) -> gpd.GeoDataFrame:
    if not snapshot.exists():
        print(f"downloading FSQ OS Places {FSQ_RELEASE} for the bbox -> {snapshot.name}")
        fetch_snapshot(snapshot, bounds)
    df = pd.read_parquet(snapshot)
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["longitude"], df["latitude"]),
        crs="EPSG:4326",
    )
    return gdf.to_crs(GRID.crs)


def labels_of(row) -> list[str]:
    raw = row.get("fsq_category_labels")
    if raw is None:
        return []
    try:
        return [str(x) for x in list(raw)]
    except TypeError:
        return []


def propose(labels: list[str], table: dict[str, str]) -> tuple[str, str]:
    """Return (proposal, label_used). Prefers the most specific label that maps."""
    for label in sorted(labels, key=len, reverse=True):
        if label in table:
            return table[label], label
    return "", (labels[0] if labels else "")


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--category", default="grocery")
    ap.add_argument("--radius", type=float, default=120.0)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument(
        "--snapshot",
        type=Path,
        default=V2 / "data" / "triangle" / f"fsq_os_places_{FSQ_RELEASE}.parquet",
    )
    args = ap.parse_args()
    out = (args.out or (AUDIT / f"{args.category}-fsq-coverage.csv")).resolve()
    table = PROPOSALS.get(args.category, {})

    # ---------------------------------------------------------------- the records OSM cannot reach
    places = gpd.read_parquet(ACCEPTED_PLACES).to_crs(GRID.crs)
    sel = select_target(places, args.category)
    if args.category == "grocery":
        from locfinder.places.grocery import classify_grocery

        sel = sel[[classify_grocery(r) == "unclassified" for _, r in sel.iterrows()]]

    osm = gpd.read_parquet(OSM_POIS).to_crs(GRID.crs)
    tag_cols = [c for c in ("shop", "amenity", "healthcare", "leisure") if c in osm.columns]
    feats = osm[osm[tag_cols].notna().any(axis=1)]
    osm_sidx = feats.sindex

    # `best is None` in the OSM pass happens exactly when the radius query is empty, so this is
    # the same set, derived the same way rather than parsed back out of a CSV.
    unreached = [
        rec
        for _, rec in sel.iterrows()
        if not list(osm_sidx.query(rec.geometry.buffer(args.radius), predicate="intersects"))
    ]
    print(f"{args.category}: {len(sel)} considered, {len(unreached)} with no OSM feature "
          f"within {args.radius:.0f} m")
    if not unreached:
        print("nothing to measure")
        return

    # ---------------------------------------------------------------- FSQ, same radius, same score
    wgs = gpd.GeoSeries([r.geometry for r in unreached], crs=GRID.crs).to_crs(4326)
    minx, miny, maxx, maxy = wgs.total_bounds
    pad = 0.05
    fsq = load_fsq(args.snapshot, (minx - pad, miny - pad, maxx + pad, maxy + pad))
    print(f"FSQ snapshot: {len(fsq):,} places in the bbox")
    fsq_sidx = fsq.sindex

    rows: list[dict] = []
    matched = proposed = agreed = closed = 0
    unmapped: dict[str, int] = {}

    for rec in unreached:
        pname = place_name(rec)
        hits = list(fsq_sidx.query(rec.geometry.buffer(args.radius), predicate="intersects"))
        best, best_score = None, -1.0
        best_dist = best_agree = 0.0
        for h in hits:
            cand = fsq.iloc[h]
            dist = float(rec.geometry.distance(cand.geometry))
            agree = name_agreement(pname, str(cand.get("name") or ""))
            score = agree * 2.0 + max(0.0, 1.0 - dist / args.radius)
            if score > best_score:
                best, best_score, best_dist, best_agree = cand, score, dist, agree

        if best is None:
            rows.append({
                "id": rec.get("id"), "name": pname, "fsq_name": "", "fsq_category": "",
                "distance_m": "", "name_agreement": "", "proposal": "",
                "evidence": f"no FSQ place within {args.radius:.0f} m either",
                "date_closed": "", "verdict": "", "notes": "",
            })
            continue

        matched += 1
        labels = labels_of(best)
        proposal, label_used = propose(labels, table)
        if proposal:
            proposed += 1
            if best_agree >= AGREE:
                agreed += 1
        elif label_used:
            unmapped[label_used] = unmapped.get(label_used, 0) + 1

        date_closed = best.get("date_closed")
        date_closed = "" if date_closed is None or str(date_closed) == "nan" else str(date_closed)
        if date_closed:
            closed += 1

        rows.append({
            "id": rec.get("id"), "name": pname,
            "fsq_name": str(best.get("name") or ""),
            "fsq_category": label_used or "; ".join(labels),
            "distance_m": f"{best_dist:.1f}",
            "name_agreement": f"{best_agree:.2f}",
            "proposal": proposal,
            "evidence": ("names agree" if best_agree >= AGREE else
                         "names do NOT agree -- the match may be a neighbour"),
            "date_closed": date_closed,
            "verdict": "", "notes": "",
        })

    # ------------------------------------------------- does any proposal deny the record's name?
    contradictions: list[dict] = []
    pattern, denial = SELF_DESCRIBING.get(args.category, ("", ""))
    if pattern:
        asserts = re.compile(pattern, re.I)
        contradictions = [
            r for r in rows
            if r["proposal"].startswith(denial) and asserts.search(r["name"] or "")
        ]

    rows.sort(key=lambda r: (r["proposal"] == "", -float(r["name_agreement"] or 0)))
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    n = len(unreached)
    print(f"\n{args.category}: of {n} records OSM could not reach,")
    print(f"  {matched:5} have an FSQ place within {args.radius:.0f} m")
    print(f"  {proposed:5} got a PROPOSAL from an FSQ category  <- the answer")
    print(f"  {agreed:5} of those ALSO agree on the name")
    print(f"  {n - matched:5} have no FSQ place either -- both sources are silent")
    if closed:
        print(f"  {closed:5} are marked CLOSED by FSQ (date_closed set)")
    if contradictions:
        denied = sum(1 for r in rows if r["proposal"].startswith(denial))
        print(f"\n  !! {len(contradictions)} of {denied} \"{denial}\" proposals DENY what the "
              f"record's own name asserts.")
        print("     That is evidence against FSQ's category, not against the record. Treat FSQ "
              "as a source that\n     CONFIRMS and never REJECTS:")
        for r in contradictions[:12]:
            print(f"       {(r['name'] or '')[:38]:38} | FSQ: {r['fsq_category'][:42]}")

    if unmapped:
        print("\n  FSQ categories matched but NOT in the proposal table "
              "(reported so none is silently dropped):")
        for label, count in sorted(unmapped.items(), key=lambda kv: -kv[1])[:15]:
            print(f"    {count:4}  {label}")
    try:
        shown = out.relative_to(Path.cwd())
    except ValueError:
        shown = out
    print(f"\nwrote {shown}")


if __name__ == "__main__":
    main()
