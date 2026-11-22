"""Which records in the PUBLISHED `grocery` layer has nothing corroborated as a shop at all?

**This is the audit in the harmful direction, and it had not been run.** Every screen so far has
asked *what is MISSING from the layer* — `rebuild_missing_grocery_stores.py` proposes additions,
`shortlist_brandless_grocery.py` and `recover_brandless_by_name.py` sort records already in it.
All three take for granted that a published record is a real shop. A wrong **addition** is the
error that hurts a household: it sends somebody to a shop that is not there. So the layer needs a
screen pointed at itself.

It found its first case before it was written. `4f318935`, published, is named
**'Longview Poole Road'** — a road, not a business — filed by Overture as `grocery_store` at
2405 Poole Rd, Raleigh. Within 200 m OSM has a school and two bus stops and no shop of any kind;
within 120 m Foursquare has a framing business, a child-care centre and a street. A household
routed there is routed to a residential street. Nothing in the project would have surfaced it,
because nothing was looking.

**What counts as corroboration.** A record is corroborated when something other than Overture's
own category says a shop is at that place:

* its name or brand field names a chain in `SUPERMARKET_BRANDS` (a lookup, not a heuristic);
* an OSM feature carrying a `shop` tag within 150 m whose name AGREES with it by
  `name_match.match_verdict`;
* an open Foursquare record within 150 m whose name AGREES with it.

Weaker signals are reported separately rather than counted as corroboration: a shop-tagged OSM
feature or a grocery-categorised FSQ record close by whose NAME does not agree may be a different
business at the same plaza, which is exactly the confusion that put a bay in the layer as a
Supercenter.

**This script proposes nothing and removes nothing.** Removing a published record hides a real
shop if the screen is wrong, which is its own harm, so every row lands in a sheet with an empty
`verdict` column for a person. `--emit` prints exclusion-table entries for rows a person has
marked, so applying a decision is mechanical rather than retyped.

**Each gate is counted, and a gate nothing reaches prints `NEVER REACHED` in those words**, since
a predeclared safeguard that is never exercised is decoration.

Run:
    python scripts/screen_uncorroborated_grocery.py
    python scripts/screen_uncorroborated_grocery.py --emit
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "spikes"))

import geopandas as gpd  # noqa: E402
import pandas as pd  # noqa: E402

from _common import ACCEPTED_PLACES  # noqa: E402
from locfinder.places.categories import select_overture  # noqa: E402
from locfinder.places.exclusions import HELD_SERVICE_POINTS, inclusion_reason  # noqa: E402
from locfinder.places.grocery import (  # noqa: E402
    SUPERMARKET_BRANDS,
    _brand_name,
    chain_in_name,
    names_a_service_point,
    names_part_of_a_store,
)
from locfinder.places.name_match import clears_the_floor, match_verdict  # noqa: E402

CRS = 32617
FSQ_PATH = ROOT / "data" / "triangle" / "fsq_os_places_2025-01-10.parquet"
OSM_PATH = ROOT / "data" / "triangle" / "osm_pois.parquet"
AUDIT = ROOT.parent / "docs" / "experiments" / "audit"
#: The snapshot's own date, named in every claim read out of it, so the age of the
#: claim travels with it. The forward screen holds the same constant for the same reason.
FSQ_SNAPSHOT_DATE = "2025-01-10"
SHEET = AUDIT / "uncorroborated-grocery.csv"

#: One list for the writer and for the reader. The forward screen's two halves drifted apart and a
#: column its predicate read was absent from the file it had written.
SHEET_COLUMNS = ["place_id", "name", "address", "primary", "outcome", "evidence", "verdict"]

#: How far a corroborating feature may sit. 150 m is the same figure the missing-store screen
#: uses, and for the same reason: it is about one shopping-plaza frontage, far enough to reach a
#: tag on the building and near enough that a second business is unlikely to be the match.
NEAR_M = 150.0

#: A tighter radius for the WEAK signals, which are reported and not counted. A shop-tagged
#: feature 40 m away with a different name is worth a person's attention; one 140 m away is just
#: the next unit in the plaza.
WEAK_M = 60.0

#: Names that describe a PLACE rather than a business. This is a suspicion, never a verdict --
#: `Longview Poole Road` is a road, but `Market Street Market` would be a shop, so the pattern
#: only fires when no shop word is present at all.
PLACE_SUFFIX = re.compile(
    r"\b(road|rd|street|st|avenue|ave|drive|dr|boulevard|blvd|lane|ln|court|ct|"
    r"circle|cir|highway|hwy|parkway|pkwy|trail|way|place|pl|terrace|crossing|"
    r"apartments|subdivision)\b",
    re.I,
)
SHOP_WORD = re.compile(
    r"\b(market|supermarket|grocer|grocery|foods?|mart|store|shop|deli|bakery|butcher|"
    r"produce|fruteria|carniceria|supermercado|mercado|tienda|bodega|iga|co-?op)\b",
    re.I,
)


def name_of(rec) -> str:
    n = rec.get("names")
    return str(n.get("primary") or "") if hasattr(n, "get") else ""


def primary_of(rec) -> str:
    t = rec.get("taxonomy")
    return str(t.get("primary") or "") if hasattr(t, "get") else ""


def address_of(rec) -> str:
    a = rec.get("addresses")
    try:
        first = a[0]
        if hasattr(first, "get"):
            return f"{first.get('freeform') or ''}, {first.get('locality') or ''}".strip(", ")
    except Exception:
        pass
    return ""


def looks_like_a_place_not_a_shop(name: str) -> bool:
    return bool(PLACE_SUFFIX.search(name)) and not SHOP_WORD.search(name)


def shown(path) -> str:
    """A path for a person, without raising when it sits outside the repo.

    `relative_to` throws for anything outside `ROOT.parent`, and this is called from the
    guard that protects the owner's verdicts -- a guard that raises inside its own
    explanation is not a guard.
    """
    try:
        return str(path.relative_to(ROOT.parent))
    except ValueError:
        return str(path)


def read_sheet(path) -> list[dict]:
    """The sheet as a PERSON left it, or `[]` when there is no sheet yet.

    **The absence of this function was the defect.** `--emit` iterated the rows the screen had
    just computed, every one of which carries `verdict: ""` by construction, so it could never
    emit anything. The owner's path was to read 121 rows, mark the ones that are not shops, run
    `--emit`, and be told *"nothing marked `exclude` in the sheet"*. A mechanism that exists and
    is unreachable is the defect this project retired owner ask 5 for.
    """
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in SHEET_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            # Refused rather than filled in with blanks. `migrate_audit_sheet.py` exists in this
            # repo because the only way past an earlier version of this check was to regenerate
            # the file, and regenerating wrote every owner column empty.
            sys.exit(f"{path} is missing {missing}. It was written by an older version of this "
                     "screen: keep a copy, then rerun with --write-sheet to regenerate it.")
        return list(reader)


def owner_verdicts(rows) -> dict[str, str]:
    """`place_id` -> the verdict a person typed, stripped and lowercased, blanks dropped.

    Every non-empty verdict counts, not only `exclude`. A typed `keep` is a decision too, and
    discarding it means asking the owner the same question a second time.
    """
    return {r["place_id"]: r["verdict"].strip().lower()
            for r in rows if r.get("verdict", "").strip()}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--emit", action="store_true",
                    help="print exclusion entries for rows marked `exclude` in the sheet")
    ap.add_argument("--write-sheet", action="store_true",
                    help="overwrite the sheet even though somebody has typed verdicts into it. "
                         "Required, because a rerun rewrites every row with an empty verdict, "
                         "and those verdicts are the only record of why a published record was "
                         "kept or dropped.")
    args = ap.parse_args()

    places = gpd.read_parquet(ACCEPTED_PLACES)
    published_ids = set(select_overture(places, "grocery")["id"])
    metric = places.to_crs(CRS).reset_index(drop=True)

    fsq_raw = pd.read_parquet(FSQ_PATH)
    fsq = gpd.GeoDataFrame(
        fsq_raw,
        geometry=gpd.points_from_xy(fsq_raw["longitude"], fsq_raw["latitude"]),
        crs="EPSG:4326",
    ).to_crs(CRS)
    fsq_open = fsq[fsq["date_closed"].isna()].reset_index(drop=True)
    fsq_pts = fsq_open.geometry  # FSQ rows are points, so no polygon question arises here
    fsq_names = fsq_open["name"].astype("string").fillna("")
    fsq_cats = fsq_open["fsq_category_labels"].astype("string").fillna("")

    osm = gpd.read_parquet(OSM_PATH).to_crs(CRS)
    if "shop" in osm.columns:
        osm_shops = osm[osm["shop"].notna()].reset_index(drop=True)
    else:
        osm_shops = osm.iloc[0:0].reset_index(drop=True)
    # **NOT `.centroid`.** OSM supermarkets are polygons, and the sixth review showed that
    # measuring to the centroid gets the answer wrong in both directions: one held bay is INSIDE
    # its store's polygon (0.0 m) and was recorded as 40.0 m away, and another is 209.0 m from one
    # -- inside a 250 m search that reported nothing. `GeoSeries.distance` to the geometry itself
    # returns 0.0 for containment, which is the number that means what it says.
    osm_geoms = osm_shops.geometry
    osm_names = (osm_shops["name"].astype("string").fillna("")
                 if "name" in osm_shops.columns else pd.Series([""] * len(osm_shops)))

    gates = Counter()
    gate_order = [
        "published", "held_bay", "owner_admitted", "brand_in_table",
        "osm_name_agrees", "fsq_name_agrees",
        "WEAK: osm shop nearby, name differs", "WEAK: fsq grocery category only",
        "UNCORROBORATED", "UNCORROBORATED and named like a place not a shop",
    ]
    rows = []

    pub = metric[metric["id"].isin(published_ids)]
    for _, rec in pub.iterrows():
        gates["published"] += 1
        pid = rec["id"]
        name = name_of(rec)
        here = rec.geometry

        # A bay the owner deliberately holds is published BY DECISION, and its own entry says the
        # record is a collection point rather than a shop. Screening it as uncorroborated would
        # re-litigate a decision taken two days ago, so it is counted and set aside.
        if pid in HELD_SERVICE_POINTS:
            gates["held_bay"] += 1
            continue
        # Likewise a record the owner admitted: its entry already carries the corroboration.
        if inclusion_reason("grocery", pid):
            gates["owner_admitted"] += 1
            continue

        brand = chain_in_name(name)
        if not brand:
            field = _brand_name(rec)
            if field and field in SUPERMARKET_BRANDS:
                brand = field
        # A BRAND MATCH IS NOT A SHOP. `Walmart Bakery` carries the brand and is a counter
        # inside the store; `Harris Teeter Parking Lot` carries it and is tarmac. The
        # sixth pass found the same hole in the forward screen, where a bakery was accepted
        # as evidence that a Walmart trades. Here it points the other way -- a part of a
        # store counted as a corroborated published record, which UNDERSTATES how much of
        # the layer has nothing behind it, and understating is the direction that lets you
        # stop looking.
        if brand and not names_a_service_point(name) and not names_part_of_a_store(name):
            gates["brand_in_table"] += 1
            continue

        od = osm_geoms.distance(here)
        onear = od <= NEAR_M
        osm_agree, osm_weak = None, None
        for j in od[onear].sort_values().index:
            their = str(osm_names.iloc[j] or "")
            verdict = match_verdict(name, their)
            if clears_the_floor(verdict):
                osm_agree = (round(float(od.iloc[j]), 1), their, str(osm_shops["shop"].iloc[j]))
                break
            if osm_weak is None and od.iloc[j] <= WEAK_M:
                osm_weak = (round(float(od.iloc[j]), 1), their, str(osm_shops["shop"].iloc[j]))
        if osm_agree:
            gates["osm_name_agrees"] += 1
            continue

        fd = fsq_pts.distance(here)
        fnear = fd <= NEAR_M
        fsq_agree, fsq_weak = None, None
        for j in fd[fnear].sort_values().index:
            their = str(fsq_names.iloc[j] or "")
            verdict = match_verdict(name, their)
            if clears_the_floor(verdict):
                fsq_agree = (round(float(fd.iloc[j]), 1), their)
                break
            if (fsq_weak is None and fd.iloc[j] <= WEAK_M
                    and re.search(r"Grocery|Supermarket|Food and Beverage", fsq_cats.iloc[j] or "",
                                  re.I)):
                fsq_weak = (round(float(fd.iloc[j]), 1), their, (fsq_cats.iloc[j] or "")[:60])
        if fsq_agree:
            gates["fsq_name_agrees"] += 1
            continue

        if osm_weak:
            gates["WEAK: osm shop nearby, name differs"] += 1
            outcome = "WEAK: osm shop nearby, name differs"
            evidence = (f"OSM `shop={osm_weak[2]}` named {osm_weak[1]!r} at {osm_weak[0]} m -- the "
                        "name does NOT agree, so this may be a different business at the same site")
        elif fsq_weak:
            gates["WEAK: fsq grocery category only"] += 1
            outcome = "WEAK: fsq grocery category only"
            evidence = (f"FSQ {fsq_weak[1]!r} at {fsq_weak[0]} m categorised {fsq_weak[2]!r}; the "
                        "name does NOT agree, so the category is the only signal")
        else:
            outcome = "UNCORROBORATED"
            gates["UNCORROBORATED"] += 1
            nearest_osm = f"{float(od.min()):.0f}" if len(od) else "n/a"
            nearest_fsq = f"{float(fd.min()):.0f}" if len(fd) else "n/a"
            evidence = (f"no OSM shop-tagged feature, and no FSQ record with an agreeing name "
                        f"within {NEAR_M:.0f} m; nearest OSM shop of any kind {nearest_osm} m, "
                        f"nearest FSQ record of any kind with no closure recorded {nearest_fsq} m. "
                        f"The FSQ snapshot is dated {FSQ_SNAPSHOT_DATE}: a blank closure field in it "
                        "is not a report that a shop trades today.")
            if looks_like_a_place_not_a_shop(name):
                gates["UNCORROBORATED and named like a place not a shop"] += 1
                outcome = "UNCORROBORATED: name describes a place, not a shop"

        rows.append({
            "place_id": pid,
            "name": name,
            "address": address_of(rec),
            "primary": primary_of(rec) or "(none)",
            "outcome": outcome,
            "evidence": evidence,
            "verdict": "",
        })

    rows.sort(key=lambda r: (not r["outcome"].startswith("UNCORROBORATED"), r["name"].lower()))

    if args.emit:
        for r in read_sheet(SHEET):
            if r["verdict"].strip().lower() != "exclude":
                continue
            print(f'    "{r["place_id"]}":')
            print(f'        "{r["name"]} at {r["address"]}. {r["evidence"]}. '
                  f'Screened by `scripts/screen_uncorroborated_grocery.py`. PRELIMINARY.",')
        if not any(v == "exclude" for v in owner_verdicts(read_sheet(SHEET)).values()):
            print(f"nothing marked `exclude` in {SHEET.name} -- nothing to emit. "
                  "This reads the sheet on disk; it used to read the rows it had "
                  "just computed, whose verdict column is empty by construction.")
        return

    AUDIT.mkdir(parents=True, exist_ok=True)
    held = owner_verdicts(read_sheet(SHEET))
    if held and not args.write_sheet:
        print(f"{shown(SHEET)} carries {len(held)} verdict(s) somebody typed, "
              "and a rerun writes every row back empty.")
        print("Pass --write-sheet to overwrite them deliberately. Gate counts for this run:")
        print()
        for g in gate_order:
            n = gates.get(g, 0)
            print(f"  {g:<46} {n}" if n else f"  {g:<46} NEVER REACHED")
        return
    with SHEET.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=SHEET_COLUMNS)
        w.writeheader()
        w.writerows(rows)

    print(f"{shown(SHEET)}  ({len(rows)} rows for a person)")
    print()
    print("gates:")
    for g in gate_order:
        n = gates.get(g, 0)
        print(f"  {g:<46} {n}" if n else f"  {g:<46} NEVER REACHED")
    print()
    print("Nothing was proposed and nothing was removed. The `verdict` column is empty by design:")
    print("removing a published record hides a real shop if this screen is wrong.")


if __name__ == "__main__":
    main()
