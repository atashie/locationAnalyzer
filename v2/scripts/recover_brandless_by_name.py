"""Recover the brandless chain stores from the NAME field, corroborated by a footprint.

**Owner decision 2026-11-18, third pass**, *"1-4) yes, proceed"*. The lead came out of
`shortlist_brandless_grocery.py`: **34 of the 272** unclassified brandless grocery records are
named after a chain that `SUPERMARKET_BRANDS` already holds, with an **empty `brand` field**. So
roughly an eighth of the "brandless" blocker is not a classification problem at all -- it is a
*brand-field* gap, and the answer is already in the tables.

**This is a lookup, not a heuristic**, and `locfinder/places/grocery.py` now draws that line
explicitly. Only `SUPERMARKET_BRANDS` is consulted, so `Kroger Store` and `Wegmans` -- both real,
both trading in this metro, neither in the table -- match nothing until somebody edits the table.
Adding a chain stays a decision.

## Two screens, and each one exists because the data broke the rule without it

1. **The service-point screen.** Nine of the 34 are `Walmart Grocery Pickup and Delivery`, and
   several sit on the Supercenter's own ~20,000 m² footprint. **Every geometric signal says
   supermarket; only the name says collection bay.** `Weaver Street Market Administration` is the
   same shape -- an office, on the shop's own site, and the destination audit has already caught
   it being chosen as a household's destination. A household sent to a pickup bay has been sent to
   the wrong place.
2. **The footprint corroboration.** Five of the 34 -- `Food Lion` at 536 m², `ALDI` at 489,
   `Walmart` at 446, `Lowes Foods` at 256, `Lidl` at 224 -- have **no building over the floor
   anywhere within 120 m**. Whatever those records are (defunct stores, lockers, phantom rows), no
   supermarket stands there, and the name alone would have promoted all five into a published
   layer. So a name match is accepted only where a building big enough to be a supermarket is
   actually present.

The two screens catch different things and neither subsumes the other, which is why both are
applied and why the sheet reports which one fired.

## What it writes

A generated block for `NAME_CONFIRMED_SUPERMARKETS` in `locfinder/places/grocery.py`, on the same
footing as `OSM_CONFIRMED_SUPERMARKETS`: a **regenerable derivation**, kept apart from the
hand-curated tables so a data refresh cannot overwrite somebody's judgement. Plus
`docs/experiments/audit/grocery-name-recovery.csv` with every one of the 34 and what happened to
it, blank `verdict` column.

**Licence.** This uses ODbL building footprints to corroborate a classification that feeds a
**published** layer. That use was authorised by the owner on 2026-11-18 and the Buildings row in
`docs/experiments/source-registry.md` was widened to say so: the published artifact is an
ODbL-derived database and is therefore share-alike. Footprints themselves are still never
republished, and the CC BY 4.0 rows still need their own attribution.

Run from `v2/`:
    python scripts/recover_brandless_by_name.py            # report + sheet
    python scripts/recover_brandless_by_name.py --emit     # also print the table block
"""
from __future__ import annotations

import argparse
import collections
import csv
import sys
from pathlib import Path

import geopandas as gpd

V2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V2 / "spikes"))
sys.path.insert(0, str(V2))

from _common import ACCEPTED_PLACES, GRID  # noqa: E402
from locfinder.places.categories import select_target  # noqa: E402
from locfinder.places.grocery import (  # noqa: E402
    chain_in_name,
    classify_grocery,
    names_a_service_point,
)

BUILDINGS = V2 / "data" / "triangle" / "overture_buildings_accepted.parquet"
AUDIT = V2.parent / "docs" / "experiments" / "audit"

#: Square metres, from the clean polygon-only calibration in
#: `scripts/measure_footprint_separation.py`: 94.2% of OSM `shop=supermarket` footprints are at or
#: above it. Same constant as `shortlist_brandless_grocery.py` and the same justification.
FLOOR_M2 = 650.0

#: How far to look for a building big enough to be a supermarket. 120 m is what separated the five
#: chain-named records with nothing near them from the two real Walmarts with displaced points.
NEAR_LOOK_M = 120.0


def place_name(rec) -> str:
    try:
        return str(dict(rec.get("names")).get("primary") or "")
    except Exception:
        return ""


def gate(name: str, reached: int, found: int) -> None:
    """Every gate reports how often it was REACHED, not only what it caught; ledger 47."""
    if reached == 0:
        print(f"  [gate] {name}: NEVER REACHED (0 opportunities)")
        return
    print(f"  [gate] {name}: reached {reached}, fired {found} ({found / reached * 100:.1f}%)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--emit", action="store_true", help="print the table block for grocery.py")
    args = ap.parse_args()

    print("loading places and buildings ...")
    places = gpd.read_parquet(ACCEPTED_PLACES).to_crs(GRID.crs)
    bld = gpd.read_parquet(BUILDINGS).to_crs(GRID.crs)
    bld = bld[bld.geometry.notna() & bld.geometry.is_valid].reset_index(drop=True)
    bld["footprint_m2"] = bld.geometry.area
    bidx = bld.sindex

    grocery = select_target(places, "grocery")
    rows, accepted = [], {}
    reached = {"named": 0, "service": 0, "footprint": 0}
    fired = {"service": 0, "footprint": 0}

    for _, rec in grocery.iterrows():
        if classify_grocery(rec) != "unclassified":
            continue
        name = place_name(rec)
        brand = chain_in_name(name)
        if brand is None:
            continue
        reached["named"] += 1
        pid = str(rec.get("id"))

        near = list(bidx.query(rec.geometry.buffer(NEAR_LOOK_M), predicate="intersects"))
        biggest = max((float(bld["footprint_m2"].iloc[h]) for h in near), default=0.0)

        reached["service"] += 1
        if names_a_service_point(name):
            fired["service"] += 1
            outcome, why = "", (
                f"named for {brand}, but the name says this is a service point -- a collection "
                "bay, office or counter, not a shop. No geometry can tell these apart: several "
                "sit on the chain's own full-size footprint"
            )
        else:
            reached["footprint"] += 1
            if biggest < FLOOR_M2:
                fired["footprint"] += 1
                outcome, why = "", (
                    f"named for {brand}, but the largest building within {NEAR_LOOK_M:.0f} m is "
                    f"{biggest:,.0f} m2, under the {FLOOR_M2:,.0f} m2 floor. No supermarket stands "
                    "here, whatever this record calls itself"
                )
            else:
                outcome = "supermarket"
                why = (
                    f"name carries '{brand}', which is already in SUPERMARKET_BRANDS, while the "
                    f"Overture `brand` field is EMPTY. Corroborated by a {biggest:,.0f} m2 "
                    f"building within {NEAR_LOOK_M:.0f} m."
                )
                accepted[pid] = f"{name} -- {why}"

        rows.append({
            "id": pid, "name": name, "chain_in_name": brand,
            "service_point": "yes" if names_a_service_point(name) else "",
            "biggest_within_120m": f"{biggest:,.0f}" if biggest else "",
            "proposal": outcome, "evidence": why, "verdict": "", "notes": "",
        })

    rows.sort(key=lambda r: (r["proposal"] == "", r["name"]))
    out = (AUDIT / "grocery-name-recovery.csv").resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    print(f"\n{reached['named']} unclassified brandless records carry a chain name")
    gate("the service-point screen", reached["service"], fired["service"])
    gate("the footprint corroboration", reached["footprint"], fired["footprint"])
    print(f"\n  {len(accepted):>4} ACCEPTED as supermarkets")
    print(f"  {reached['named'] - len(accepted):>4} left unclassified, each with the reason")
    by_brand = collections.Counter(r["chain_in_name"] for r in rows if r["proposal"])
    print(f"  by chain: {dict(by_brand)}")
    print(f"\nwrote {out}")

    if args.emit:
        print("\n# ---- paste into locfinder/places/grocery.py ----")
        print("NAME_CONFIRMED_SUPERMARKETS: dict[str, str] = {")
        for pid, why in sorted(accepted.items(), key=lambda kv: kv[1]):
            print(f'    "{pid}":')
            print(f'        "{why}",')
        print("}")


if __name__ == "__main__":
    main()
