"""Which real supermarkets does the published `grocery` layer MISS, and can we prove each one?

This replaces the search that produced owner ask 5 on 2026-11-18, which the fifth adversarial
review destroyed for two independent reasons:

* It required the NAME to contain "Supercenter" or "Neighborhood Market". The stores actually
  missing from the layer are recorded as plain `Walmart`, so the search could not have found them.
  **It searched for the shape of a name instead of for the thing at the place.**
* It never checked whether the shops were still open. One of the five it proposed, the Walmart at
  1010 Martin Luther King Pkwy in Durham, closed in 2016 -- and `fsq_os_places_2025-01-10.parquet`
  carries a `date_closed` at that very address. The evidence was already on disk.

**The asymmetry that sets every threshold below.** A wrong ADDITION sends a household to a shop
that is not there. A wrong REFUSAL leaves the layer exactly as it is today. The first is a new
harm, the second is the status quo, so every gate here fails closed: ambiguity refuses.

**Why this is a screen and not a list.** `EXCLUDED_PLACE_IDS` is a short hand-curated list because
its population is a handful of judgement calls. This population is different: it is produced by a
systematic taxonomy gap -- Overture files a Walmart Supercenter under `department_store`,
`superstore` or `warehouse_club_store`, and the `grocery` wedge matches only the `grocery_store`
hierarchy -- so the same failure will recur for other brands and other releases. A screen that can
be re-run is the right shape; a list would go stale silently.

**Each gate is counted and printed, including the ones nothing reaches.** A predeclared gate that
is never exercised is not a safeguard, it is decoration, so the diagnostics say `NEVER REACHED`
in those words rather than printing a reassuring zero.

**What this script does NOT do.** It proposes nothing into any published layer. Adding a record is
a decision about what a record IS and it moves a published number upward, which is the owner's
call. `--emit` prints the table entries so that applying an approved decision is mechanical rather
than retyped.

Run:
    python scripts/rebuild_missing_grocery_stores.py
    python scripts/rebuild_missing_grocery_stores.py --emit
"""
from __future__ import annotations

import argparse
import csv
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
from locfinder.places.exclusions import (  # noqa: E402
    EXCLUDED_PLACE_IDS,
    HELD_SERVICE_POINTS,
)
from locfinder.places.grocery import (  # noqa: E402
    SUPERMARKET_BRANDS,
    _brand_name,
    chain_in_name,
    names_a_service_point,
)

# `_brand_name` is private to `places.grocery`. It is imported rather than reimplemented because
# reading Overture's nested brand structure in two places is how the two copies drift apart, and
# the duplicate gate below depends on reading it exactly as the classifier does.
from locfinder.places.name_match import clears_the_floor, match_verdict  # noqa: E402

CRS = 32617
FSQ_PATH = ROOT / "data" / "triangle" / "fsq_os_places_2025-01-10.parquet"
OSM_PATH = ROOT / "data" / "triangle" / "osm_pois.parquet"
AUDIT = ROOT.parent / "docs" / "experiments" / "audit"
SHEET = AUDIT / "missing-grocery-stores.csv"

#: Overture primaries where a weekly shop could plausibly happen. A POSITIVE allowlist, because
#: the alternative -- listing the categories to reject -- silently admits every new category
#: Overture invents. `convenience_store` is deliberately absent: the project's own OSM map calls
#: `shop=convenience` "not a weekly shop", and admitting it would sweep in the 28 North Carolina
#: `Family Fare` petrol-station records whose brand collides with a Michigan supermarket.
STORE_FORMATS = frozenset({
    "department_store", "superstore", "warehouse_club_store", "discount_store",
    "grocery_store", "supermarket", "wholesale_store",
})

#: OSM tags that corroborate a weekly shop, taken from `scripts/prefill_from_osm.py`'s own map so
#: the two scripts cannot drift apart. `shop=department_store` is included there for exactly the
#: reason this script exists: that is how a Supercenter gets tagged.
OSM_SUPERMARKET_TAGS = (("shop", "supermarket"), ("shop", "wholesale"),
                        ("shop", "department_store"))

NEAR_M = 150.0        #: how far a corroborating record may sit from the candidate
DUPLICATE_M = 200.0   #: a published record of the same brand this close means we already have it

#: A published grocery record this close with NO brand agreement is not proof of a duplicate, but
#: it is enough doubt to refuse a silent addition. The Lidl at 1105 N Harrison Ave is why: the same
#: store is already published as *'Cary NC - N. Harrison Ave'* 99.6 m away, a store-code name that
#: carries no chain, so a name-based duplicate test cannot see it. The brand FIELD catches that one;
#: this backstop catches the next one whose brand field is also empty.
DOUBT_M = 150.0


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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--emit", action="store_true",
                    help="print table entries for an approved decision, instead of the sheet")
    args = ap.parse_args()

    places = gpd.read_parquet(ACCEPTED_PLACES)
    published = set(select_overture(places, "grocery")["id"])
    metric = places.to_crs(CRS)

    fsq = pd.read_parquet(FSQ_PATH)
    fsq_g = gpd.GeoDataFrame(
        fsq, geometry=gpd.points_from_xy(fsq["longitude"], fsq["latitude"]), crs="EPSG:4326"
    ).to_crs(CRS)

    osm = gpd.read_parquet(OSM_PATH).to_crs(CRS)
    osm_mask = None
    for key, value in OSM_SUPERMARKET_TAGS:
        if key not in osm.columns:
            continue
        m = osm[key].astype("string").str.lower() == value
        osm_mask = m if osm_mask is None else (osm_mask | m)
    osm_shops = osm[osm_mask] if osm_mask is not None else osm.iloc[0:0]

    published_metric = metric[metric["id"].isin(published)]
    #: id -> brand, read from Overture's brand FIELD first and the name lookup only as a fallback.
    #: Brand-field first is what catches a published record named by store code rather than chain.
    published_brands = {
        rec["id"]: (_brand_name(rec) or chain_in_name(name_of(rec)))
        for _, rec in places[places["id"].isin(published)].iterrows()
    }

    gates = Counter()
    gate_order = ["owner_excluded", "considered", "brand", "service_point",
                  "REVIEW: no category", "store_format", "fsq_closure",
                  "closure_overridden_by_open_record", "duplicate",
                  "REVIEW: possible duplicate", "uncorroborated", "PROPOSED"]
    rows = []

    for i, (_, rec) in enumerate(places.iterrows()):
        if rec["id"] in published:
            continue
        # A record the owner has already decided is NOT a shop must never come back as a missing
        # one. Without this the screen re-proposes the Food House, whose whole entry says it is a
        # meat-processing plant -- and refuses it for the accidental reason that its own office
        # record sits 0.0 m away. Right outcome, wrong reason, and only by luck.
        if rec["id"] in EXCLUDED_PLACE_IDS:
            gates["owner_excluded"] += 1
            continue
        gates["considered"] += 1
        name = name_of(rec)

        # The name lookup first, because it returns the table's canonical spelling. Overture's
        # brand FIELD is consulted only when the name carries no chain -- that is what finds a
        # store recorded under a store code rather than a chain name.
        brand = chain_in_name(name)
        if not brand:
            field = _brand_name(rec)
            if field and field in SUPERMARKET_BRANDS:
                brand = field
        if not brand:
            gates["brand"] += 1
            continue
        if names_a_service_point(name):
            gates["service_point"] += 1
            continue

        primary = primary_of(rec)
        here = metric.iloc[i].geometry
        d_pub_all = published_metric.geometry.distance(here)

        # No Overture category at all is ABSENCE OF INFORMATION, not a claim to be a concession,
        # so these are listed for a human rather than refused silently -- two of them are real
        # Publix stores. They are NOT proposed, because `Manpower at Walmart`, a staffing desk
        # inside a Walmart, is in the same bucket and would clear the name floor against the
        # Supercenter's own OSM tag. A category gate cannot separate those two; a person can.
        if primary == "":
            gates["REVIEW: no category"] += 1
            rows.append({
                "place_id": rec["id"], "name": name, "address": address_of(rec),
                "primary": "(none)", "brand": brand, "outcome": "REVIEW: no category",
                "evidence": "no Overture primary; needs a human decision, not a rule",
                "nearest_published_m": f"{d_pub_all.min():.1f}", "verdict": "",
            })
            continue
        if primary not in STORE_FORMATS:
            gates["store_format"] += 1
            continue

        # ---- GATE: refuted by a Foursquare closure. The gate ask 5 did not have. ----
        #
        # A CLOSURE ONLY REFUSES IF NOTHING AGREEING IS STILL OPEN AT THE SAME SITE. This is the
        # Sam's Club category objection pointing the other way: a department closing inside a
        # store that keeps trading is not the store closing. The first version of this gate
        # refused three real Walmarts because FSQ lists `Walmart Garden Center` (closed 2019-02-13,
        # twice) and `Walmart Photo Printing` (closed 2017-12-15) at their addresses -- those names
        # share the word "Walmart" and so clear the agreement floor against a record named
        # `Walmart`. The discriminator is evidence rather than a word list: if an AGREEING FSQ
        # record is still open at the same site, the shop trades on and the closed row is a
        # counter. Durham's 1010 Martin Luther King Pkwy still refuses, because the records open
        # there are Triangle Rock Club and Planet Fitness, whose names do not agree with Walmart.
        d_fsq = fsq_g.geometry.distance(here)
        near_fsq = fsq_g[d_fsq <= NEAR_M]
        closed_evidence = ""
        open_agreeing = ""
        for _, f in near_fsq.iterrows():
            if not clears_the_floor(match_verdict(name, str(f["name"]))):
                continue
            if pd.isna(f["date_closed"]):
                if not open_agreeing:
                    open_agreeing = f"FSQ '{f['name']}' is OPEN at {f['address']}"
            elif not closed_evidence:
                closed_evidence = (f"FSQ '{f['name']}' at {f['address']} carries "
                                   f"date_closed={f['date_closed']}")
        closure_note = ""
        if closed_evidence and not open_agreeing:
            gates["fsq_closure"] += 1
            rows.append({
                "place_id": rec["id"], "name": name, "address": address_of(rec),
                "primary": primary, "brand": brand, "outcome": "REFUSED: closed",
                "evidence": f"{closed_evidence}, and no agreeing FSQ record is open at this site",
                "nearest_published_m": f"{d_pub_all.min():.1f}", "verdict": "",
            })
            continue
        if closed_evidence:
            gates["closure_overridden_by_open_record"] += 1
            closure_note = (f"note: a DEPARTMENT closed here -- {closed_evidence} -- but "
                            f"{open_agreeing}, so the shop trades on")

        # ---- GATE: we already publish this shop under another record ----
        #
        # A HELD COLLECTION BAY IS NOT THE SHOP, so it cannot count as already publishing it.
        # Without this exception the screen refuses the three stores whose bays were held on
        # 2026-11-19 -- the bay sits 20-63 m from its own Supercenter and carries the same brand --
        # and the hold could then never be lifted, because the replacement it waits for would be
        # refused as a duplicate of the placeholder. The bay is the placeholder; the store is the
        # shop.
        d_pub = d_pub_all
        dup = ""
        replaces = ""
        for j, dist in d_pub[d_pub <= DUPLICATE_M].sort_values().items():
            other = published_metric.loc[j, "id"]
            if other in HELD_SERVICE_POINTS:
                if not replaces:
                    replaces = (f"REPLACEMENT FOR HELD BAY {other} at {dist:.1f} m -- approving "
                                "this store is what allows that bay to be removed")
                continue
            if published_brands.get(other) == brand:
                dup = (f"already published as {other} at {dist:.1f} m, same brand {brand} "
                       f"(brand field, not name -- the published record may be named by store code)")
                break
        if dup:
            gates["duplicate"] += 1
            rows.append({
                "place_id": rec["id"], "name": name, "address": address_of(rec),
                "primary": primary, "brand": brand, "outcome": "REFUSED: duplicate",
                "evidence": dup, "nearest_published_m": f"{d_pub.min():.1f}", "verdict": "",
            })
            continue

        # ---- GATE: close to something published, with no brand agreement to settle it ----
        # Not proof of a duplicate; enough doubt to refuse a silent addition. Fails closed,
        # because a wrong addition is a new harm and a wrong refusal is today's behaviour.
        # Only when the neighbour has NO brand at all, so it could be this same shop under a
        # store-code name. A neighbour carrying a DIFFERENT known brand is a different shop: an
        # ALDI 138.6 m from a `Lowes Foods of Garner` is two shops in one retail park, and
        # doubting it was noise rather than caution.
        near_doubt = d_pub[d_pub <= DOUBT_M].sort_values()
        near_doubt = near_doubt[[not published_brands.get(published_metric.loc[j, "id"])
                                 for j in near_doubt.index]]
        if len(near_doubt):
            j = near_doubt.index[0]
            neighbour = places.loc[j]
            gates["REVIEW: possible duplicate"] += 1
            rows.append({
                "place_id": rec["id"], "name": name, "address": address_of(rec),
                "primary": primary, "brand": brand, "outcome": "REVIEW: possible duplicate",
                "evidence": ((replaces + "; ") if replaces else "")
                            + (f"a published grocery record sits {near_doubt.iloc[0]:.1f} m away, "
                             f"'{name_of(neighbour)}', brand "
                             f"{published_brands.get(neighbour['id'])!r} -- the neighbour carries "
                             "no brand at all, so it may be this same shop under a store code"),
                "nearest_published_m": f"{d_pub.min():.1f}", "verdict": "",
            })
            continue

        # ---- GATE: corroborated by a second dataset, or refused ----
        support = []
        d_osm = osm_shops.geometry.distance(here) if len(osm_shops) else None
        if d_osm is not None:
            for j, dist in d_osm[d_osm <= NEAR_M].sort_values().items():
                osm_name = str(osm_shops.loc[j].get("name") or "")
                if clears_the_floor(match_verdict(name, osm_name)):
                    tag = next((f"{k}={v}" for k, v in OSM_SUPERMARKET_TAGS
                                if str(osm_shops.loc[j].get(k) or "").lower() == v), "shop")
                    support.append(f"OSM `{tag}` named '{osm_name}' at {dist:.1f} m")
                    break
        for _, f in near_fsq.iterrows():
            if not pd.isna(f["date_closed"]):
                continue
            if clears_the_floor(match_verdict(name, str(f["name"]))):
                support.append(f"FSQ '{f['name']}' open at "
                               f"{fsq_g.geometry.distance(here).loc[_]:.1f} m")
                break
        if not support:
            gates["uncorroborated"] += 1
            rows.append({
                "place_id": rec["id"], "name": name, "address": address_of(rec),
                "primary": primary, "brand": brand, "outcome": "REFUSED: uncorroborated",
                "evidence": "no OSM supermarket tag and no open FSQ record with an agreeing name "
                            f"within {NEAR_M:.0f} m",
                "nearest_published_m": f"{d_pub.min():.1f}", "verdict": "",
            })
            continue

        gates["PROPOSED"] += 1
        rows.append({
            "place_id": rec["id"], "name": name, "address": address_of(rec),
            "primary": primary, "brand": brand, "outcome": "PROPOSED",
            "evidence": "; ".join(support + [n for n in (closure_note, replaces) if n]),
            "nearest_published_m": f"{d_pub.min():.1f}", "verdict": "",
        })

    proposed = [r for r in rows if r["outcome"] == "PROPOSED"]

    if args.emit:
        print("#: Proposed additions. NOT applied: adding a record moves a published number "
              "upward and is the owner's decision.")
        for r in sorted(proposed, key=lambda r: r["place_id"]):
            print(f'    "{r["place_id"]}":')
            print(f'        "{r["name"]} at {r["address"]}, Overture primary={r["primary"]} '
                  f'so outside the `grocery_store` hierarchy. Corroborated: {r["evidence"]}. '
                  f'Nearest published grocery {r["nearest_published_m"]} m.",')
        return

    AUDIT.mkdir(parents=True, exist_ok=True)
    with SHEET.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else
                           ["place_id", "name", "address", "primary", "brand", "outcome",
                            "evidence", "nearest_published_m", "verdict"])
        w.writeheader()
        for r in sorted(rows, key=lambda r: (r["outcome"], r["name"])):
            w.writerow(r)

    print(f"published `grocery`: {len(published)}   accepted places: {len(places)}")
    print(f"OSM supermarket-tagged POIs: {len(osm_shops)}   FSQ rows: {len(fsq_g)}")
    print("\n--- gates, in order. A gate nothing reaches is not a safeguard. ---")
    for g in gate_order:
        n = gates[g]
        label = f"{n}" if n else "NEVER REACHED"
        print(f"  {g:<16} {label}")
    print(f"\nsheet: {SHEET}")
    print(f"PROPOSED: {len(proposed)}   refused: {len(rows) - len(proposed)}")
    for r in sorted(proposed, key=lambda r: r["name"]):
        print(f"  {r['place_id']}  {r['name'][:26]:<26} {r['address'][:38]:<38} "
              f"{r['primary']:<20} {r['evidence'][:60]}")


if __name__ == "__main__":
    main()
