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
systematic taxonomy gap -- Overture files these shops outside the `grocery_store` hierarchy, which
is the only one the `grocery` wedge matches -- so the same failure will recur for other brands and
other releases. Of the 23 eventually admitted: 11 `department_store`, 6 `discount_store`, 4
`superstore`, 2 with no primary. `STORE_FORMATS` below is wider than that on purpose, because it
is the set of formats the screen will CONSIDER rather than a description of what it found. A screen that can
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

To regenerate the committed evidence sheet -- the record of why the 23 records were admitted --
the screen has to see the world as it was before them, because its first gate skips anything
already published:

    python scripts/rebuild_missing_grocery_stores.py --pre-admission --write-sheet
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "spikes"))

import geopandas as gpd  # noqa: E402
import pandas as pd  # noqa: E402

from _common import ACCEPTED_PLACES  # noqa: E402
from locfinder.places.categories import select_overture  # noqa: E402
from locfinder.places.exclusions import (  # noqa: E402
    DROPPED_PLACE_IDS,
    EXCLUDED_PLACE_IDS,
    HELD_SERVICE_POINTS,
    INCLUDED_PLACE_IDS,
)
from locfinder.places.grocery import (  # noqa: E402
    SUPERMARKET_BRANDS,
    _brand_name,
    chain_in_name,
    names_a_service_point,
    names_part_of_a_store,
)

# `_brand_name` is private to `places.grocery`. It is imported rather than reimplemented because
# reading Overture's nested brand structure in two places is how the two copies drift apart, and
# the duplicate gate below depends on reading it exactly as the classifier does.
from locfinder.places.name_match import clears_the_floor, match_verdict  # noqa: E402

CRS = 32617
FSQ_PATH = ROOT / "data" / "triangle" / "fsq_os_places_2025-01-10.parquet"
#: The snapshot's own date, named in every claim read out of it. A blank `date_closed` here is
#: "no closure recorded by this date", which is twenty-two months stale, and not "open today".
#: A test asserts this string is in `FSQ_PATH.name`, so the two cannot drift apart.
FSQ_SNAPSHOT_DATE = "2025-01-10"
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


@dataclass(frozen=True)
class FsqReading:
    """What the Foursquare snapshot says about one candidate site, and nothing more than that.

    Four fields rather than a boolean, because the two counts are the diagnostics that made the
    defect findable: `bays_skipped` and `parts_skipped` say which rule did the work, and a run
    whose proposals rest on nothing but skipped rows shows up as support that is empty.
    """

    #: A closure recorded against a record OF THE STORE ITSELF. Non-empty means refuse.
    closure: str = ""
    #: An agreeing store-level record, with the snapshot's own date attached to the claim.
    support: str = ""
    #: Rows skipped by `names_a_service_point` -- a bay, counter, office or depot.
    bays_skipped: int = 0
    #: Rows skipped by `names_part_of_a_store` -- a department, car park, ATM or toilet.
    parts_skipped: int = 0

    @property
    def refuses(self) -> bool:
        """A recorded closure refuses, whatever else is at the site. Gates fail closed."""
        return bool(self.closure)


def read_fsq_records(name: str, rows: Iterable[tuple[str, object, str, float]]) -> FsqReading:
    """Read the nearby Foursquare rows for one candidate. `rows` is (name, date_closed, addr, m).

    **This function exists because the logic it replaces could not be tested.** It was inline in
    `main()`, reachable only by building synthetic parquet files, and the sixth adversarial pass
    had to do exactly that to find the two defects below. Both were defects of reasoning:

    1. **A missing `date_closed` was read as the record being OPEN**, and an "open" record was then
       allowed to OVERRULE a recorded closure. The snapshot is dated 2025-01-10. A blank closure
       field in a file from January 2025 means no closure had been recorded by then -- it is not a
       report that the shop trades today, and it cannot outweigh a date that IS recorded. So there
       is no override any more: a closure on a store-level record refuses, full stop.
    2. **A part of the store was allowed to speak for the store**, in both directions. An open
       `Walmart Vision & Glasses` beside a CLOSED `Walmart Supercenter` returned PROPOSED,
       explaining that an optician established continued trading. And a closed
       `Walmart Garden Center` was read as the store having shut -- which is what made the
       override look necessary, so defect 2 is what manufactured defect 1.

    The replacement rule is symmetric and needs no override: **a record that is not the store is
    evidence about neither the store's existence nor its closure.** It is counted and dropped.
    """
    reading = FsqReading()
    for fsq_name, date_closed, address, metres in rows:
        fsq_name = str(fsq_name)
        if not clears_the_floor(match_verdict(name, fsq_name)):
            continue
        # A bay cannot be evidence for the store it serves, and a department cannot be evidence
        # for the store it sits inside. Counted separately so the diagnostics name the rule.
        if names_a_service_point(fsq_name):
            reading = replace(reading, bays_skipped=reading.bays_skipped + 1)
            continue
        if names_part_of_a_store(fsq_name):
            reading = replace(reading, parts_skipped=reading.parts_skipped + 1)
            continue
        if date_closed is not None and not pd.isna(date_closed):
            if not reading.closure:
                reading = replace(reading, closure=(
                    f"FSQ '{fsq_name}' at {address} carries date_closed={date_closed}"))
        elif not reading.support:
            # **The wording is part of the fix.** This said `FSQ 'X' open at 12.0 m`, which
            # asserts something nobody measured. It says what it knows: a record agreeing by name
            # stood here in a snapshot, and that snapshot recorded no closure for it.
            reading = replace(reading, support=(
                f"FSQ '{fsq_name}' at {metres:.1f} m, no closure recorded in the "
                f"{FSQ_SNAPSHOT_DATE} snapshot"))
    return reading


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--emit", action="store_true",
                    help="print table entries for an approved decision, instead of the sheet")
    ap.add_argument("--write-sheet", action="store_true",
                    help="overwrite the audit sheet. Required, because a rerun AFTER an admission "
                         "no longer screens the admitted records -- the first gate skips anything "
                         "already published -- so an unguarded rerun would replace the sheet that "
                         "records WHY 23 records were admitted with the residual rows only.")
    ap.add_argument("--pre-admission", action="store_true",
                    help="empty INCLUDED_PLACE_IDS['grocery'] FOR THIS RUN ONLY, so the screen "
                         "sees the world as it was before the 23 admissions. This is what "
                         "regenerates docs/experiments/audit/missing-grocery-stores.csv, which is "
                         "the record of why those records were admitted: after the admission the "
                         "first gate skips them as already published, so a plain rerun cannot "
                         "reproduce the sheet. Nothing on disk is changed by the flag.")
    args = ap.parse_args()

    if args.pre_admission:
        # In memory only. The table is a module-level dict and `select_overture` reads it through
        # `forced_into`, so emptying it here is enough and the file is never touched.
        INCLUDED_PLACE_IDS["grocery"] = {}
        print("--pre-admission: INCLUDED_PLACE_IDS['grocery'] emptied for this run only")
        print()

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
                  "fsq_row_is_a_service_point", "fsq_row_is_part_of_a_store",
                  "REVIEW: no category", "store_format", "fsq_closure", "duplicate",
                  "REVIEW: possible duplicate", "uncorroborated", "PROPOSED"]
    rows = []

    for i, (_, rec) in enumerate(places.iterrows()):
        if rec["id"] in published:
            continue
        # A record the owner has already decided is NOT a shop must never come back as a missing
        # one. Without this the screen re-proposes the Food House, whose whole entry says it is a
        # meat-processing plant -- and refuses it for the accidental reason that its own office
        # record sits 0.0 m away. Right outcome, wrong reason, and only by luck.
        # `DROPPED_PLACE_IDS`, not `EXCLUDED_PLACE_IDS`: the second omits the twelve confirmed
        # closures, so a shop already recorded as shut was screened from scratch and refused again
        # by the closure gate -- the right outcome reached at the wrong gate, which is how a gate
        # count stops meaning what it says. Found by the sixth review.
        if rec["id"] in DROPPED_PLACE_IDS:
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
        # **A RECORDED CLOSURE REFUSES. THERE IS NO OVERRIDE.** The previous version let an
        # agreeing record with a BLANK `date_closed` overrule a closure, on the reasoning that a
        # department closing inside a trading store is not the store closing. The reasoning was
        # right and the implementation of it was not: a blank closure field in a snapshot dated
        # 2025-01-10 is not a report that the shop trades today, so it was outweighing a date that
        # IS recorded with the absence of one that is not.
        #
        # The department problem is real and is now solved where it belongs, by asking whether the
        # CLOSING record is the store: `Walmart Garden Center` (closed 2019-02-13, twice) and
        # `Walmart Photo Printing` (closed 2017-12-15) are parts of a store, so they never produce
        # closure evidence and nothing has to overrule them. The three real Walmarts the first
        # version of this gate refused still pass, for a reason that is true. Durham's 1010 Martin
        # Luther King Pkwy still refuses: the closed record there IS the store, and the records
        # standing at the site are Triangle Rock Club and Planet Fitness, which do not agree.
        #
        # `read_fsq_records` holds the rule, so that it can be tested at all --
        # `tests/test_grocery_proposal_screen.py`. It was inline here, and unreachable except by
        # building synthetic parquet files, which is what the sixth review had to do to find it.
        d_fsq = fsq_g.geometry.distance(here)
        near_fsq = fsq_g[d_fsq <= NEAR_M]
        reading = read_fsq_records(name, [
            (f["name"], f["date_closed"], f["address"], d_fsq.loc[j])
            for j, f in near_fsq.iterrows()
        ])
        gates["fsq_row_is_a_service_point"] += reading.bays_skipped
        gates["fsq_row_is_part_of_a_store"] += reading.parts_skipped
        if reading.refuses:
            gates["fsq_closure"] += 1
            rows.append({
                "place_id": rec["id"], "name": name, "address": address_of(rec),
                "primary": primary, "brand": brand, "outcome": "REFUSED: closed",
                "evidence": f"{reading.closure}, and the records agreeing by name at this site "
                            "are parts of a store or carry a closure of their own",
                "nearest_published_m": f"{d_pub_all.min():.1f}", "verdict": "",
            })
            continue

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
        # The same reading, reused rather than recomputed. Before the service-point and
        # store-part tests reached this side, NINE of the fourteen proposed Walmarts were
        # corroborated by a department or a bay -- `Walmart Auto Care Centers`,
        # `Walmart Vision & Glasses`, `Walmart Bakery`, `Walmart Photo Center`, and TWICE by
        # `Walmart Grocery Pickup and Delivery`, which is the exact record type this project
        # removes as not-a-shop. A bay cannot be evidence for the store it serves, and a counter
        # cannot be evidence for the store it sits inside.
        #
        # Reusing one `FsqReading` for both the closure gate and this one is also the fix for a
        # smaller defect: the two loops applied different tests to the same rows, which is how a
        # row could be a department when refusing and a witness when corroborating.
        if reading.support:
            support.append(reading.support)
        if not support:
            gates["uncorroborated"] += 1
            rows.append({
                "place_id": rec["id"], "name": name, "address": address_of(rec),
                "primary": primary, "brand": brand, "outcome": "REFUSED: uncorroborated",
                "evidence": "no OSM supermarket tag, and no FSQ record of the STORE with an "
                            f"agreeing name within {NEAR_M:.0f} m -- "
                            f"{reading.bays_skipped} bay and {reading.parts_skipped} store-part "
                            "rows at this site were skipped",
                "nearest_published_m": f"{d_pub.min():.1f}", "verdict": "",
            })
            continue

        gates["PROPOSED"] += 1
        rows.append({
            "place_id": rec["id"], "name": name, "address": address_of(rec),
            "primary": primary, "brand": brand, "outcome": "PROPOSED",
            "evidence": "; ".join(support + ([replaces] if replaces else [])),
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

    if SHEET.exists() and not args.write_sheet:
        print(f"{SHEET.relative_to(ROOT.parent)} already exists and is the record of an applied "
              "decision.")
        print("A rerun no longer screens the records that were admitted from it, so writing now "
              "would replace that record with the residual rows.")
        print("Pass --write-sheet to overwrite it deliberately. Gate counts for this run:")
        print()
        for g in gate_order:
            n = gates.get(g, 0)
            print(f"  {g:<42} {n}" if n else f"  {g:<42} NEVER REACHED")
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
