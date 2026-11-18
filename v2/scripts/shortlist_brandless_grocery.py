"""The brandless grocery rule: a footprint is an UPPER BOUND on the shop inside it.

**The decision this is for.** 323 of the 541 grocery records carry no Overture `brand`, and
`grocery_store` covers a supermarket and a corner shop alike. The resume point has said for two
days that splitting them *"needs a rule the owner has not been shown yet"*. Owner, 2026-11-18,
*"1-4) yes, proceed"*. This is the rule, with the measurement that produced it and the one that
nearly produced a much worse one.

`locfinder/places/grocery.py` names what a robust mechanism would need: *"floor area, aisle or
department counts, a product-range signal from a source that holds one, or simply asking people in
the neighbourhood."* Floor area is the first item and 522,160 footprints are on disk. So it was
measured. See `scripts/measure_footprint_separation.py` for the predictions, which were committed
before either run.

## Floor area separates the two populations very well

Calibrated on OSM's own tags, which give sets large enough to decide with, using each feature's
**own polygon** where it has one so no footprint is borrowed:

| | n | median | IQR | max |
|---|---|---|---|---|
| `shop=supermarket` | 103 | 4,081 m² | 2,207 - 5,562 | 20,903 |
| `shop=convenience` | 269 | 289 m² | 224 - 407 | **1,051** |

A single threshold at **650 m²** puts 94.2% of the supermarkets above it and 95.2% of the
convenience stores below. On the wider set that also includes point features borrowing the building
underneath them the optimum is 750 m² at 93.7% / 93.6% — slightly *worse*, and the convenience
maximum rises from 1,051 m² to 13,898 m². That rise is the whole story of this script: the giant
"convenience stores" are units in a parade wearing the parade's footprint.

## Why the obvious rule would have been a disaster

Apply `area >= 750 -> supermarket` to the open records and 133 of 200 become weekly shops. Then
count how many of those records actually have the building to themselves:

| of 211 reachable brandless records | total | >= 750 m² | < 750 m² |
|---|---|---|---|
| **sole place in its footprint** | 30 | **2** | 28 |
| **shares its footprint** | 181 | 135 | 46 |

The shared ones run to 13 places in one polygon and the big ones have a median area of 2,118 m².
So nearly every record the naive rule would have promoted is a small shop in a retail parade, and
the rule would have put 135 corner shops into a **published** weekly-shop layer.

## Two things the spot-check changed, after the rule was first written

Reading the output by name rather than by count moved both branches.

**THE POSITIVE BRANCH IS WITHDRAWN. It produced two records and both are wrong.**
`Big Spoon Roasters` (980 m²) is a nut-butter maker and `C & F Foods` (12,180 m²) is at
warehouse scale. The reason is structural rather than bad luck: a *real* Triangle supermarket sits
in a shopping centre and therefore SHARES its footprint, so "large building, sole occupant" selects
for food production and distribution — the opposite of a weekly shop. 0 of 2 verified, so the
branch proposes nothing and the finding is reported instead.

**THE NEGATIVE BRANCH NEEDED A GUARD, and the probe that found it is worth keeping.** 35 of the
272 brandless records are *named* after a known chain, which makes them a free correctness probe:
the rule's answer for a record named `Food Lion` is checkable without a site visit. It proposed
`not_a_weekly_shop` for 7 of them. Checking each against the buildings nearby:

* **5 are right.** `ALDI` (489 m²), `Lidl` (224), `Lowes Foods` (256), `Food Lion` (536) and
  `Walmart` (446) have **no building over the floor anywhere within 120 m**. Whatever those
  records are — defunct stores, pickup lockers, phantom rows — no supermarket stands there, and
  keeping them out of the weekly-shop layer is the correct call.
* **2 are wrong.** Both `Wal Mart` records sit outside any building with a **3,943 m²** building
  120 m away. That is a real Walmart with a displaced point, and the rule read the wrong structure.

So the negative gets a second condition: **no building over the floor within 120 m either**. If a
supermarket-sized building is nearby, the point may simply be in the wrong place and the record is
left undecided. That is the fix for the only failure mode the probe could find.

## The rule, which is asymmetric because the measurement is

**A footprint is an upper bound on the shop inside it.** That single sentence gives three outcomes
rather than two, and the asymmetry is not a hedge — it follows from what the number is:

* **`not_a_weekly_shop`** — the whole footprint is under the threshold. Sound **whatever** the
  tenancy: if the entire building is smaller than a supermarket, nothing inside it is one. This is
  the rule's main yield.
* **`undecided`** — everything else. Over the threshold but shared, so the polygon is measuring
  the parade and says nothing about the unit; or under the threshold with a large building nearby,
  so the point may be misplaced. Left exactly as it was.

There is **no positive branch**, for the reason above.

The asymmetry is safe because the two directions differ in cost. `unclassified` and
`not_a_weekly_shop` are both **outside** the supermarket layer, so a wrong negative changes a
household's result not at all and only records a judgement that can be revisited. A wrong positive
**adds** a record to a published layer and routes somebody to a nut-butter workshop. So the rule
only speaks in the cheap direction.

## What this does not do

It writes a sheet with a blank `verdict` column. It does not edit `classify_grocery` and does not
add a table to `locfinder/places/grocery.py`, because the owner's decision for that module is
*"use big brands, and a curated list for the independents"* and a machine-generated list of 70+
ids is not a curated list. Naming it a shortlist rather than `FOOTPRINT_CONFIRMED_*` is the same
call made for `pharmacy-fsq-shortlist.csv`: a script must not pre-empt an open decision by picking
a filename.

**Licence, which is a separate question from whether the rule works.** The buildings file was
acquired under the *diagnostic* allowlist and its own report records the use as *"rasterised to
counts, never republished"*; every row is ODbL-1.0 or CC BY 4.0. Measuring is inside that.
**Classifying a published layer from it is not** — it would make the grocery layer an ODbL-derived
database and falsify that registry row. It is the same exposure the project already carries through
`OSM_CONFIRMED_SUPERMARKETS`, which is derived from the ODbL `osm_pois` extract and feeds the same
layer, and decision 17 welcomes ODbL publication of OSM-derived work. But moving that line is the
owner's call, not a script's, so this stops at a sheet.

Run from `v2/`:
    python scripts/shortlist_brandless_grocery.py
"""
from __future__ import annotations

import collections
import csv
import statistics
import sys
from pathlib import Path

import geopandas as gpd

V2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V2 / "spikes"))
sys.path.insert(0, str(V2))

from _common import ACCEPTED_PLACES, GRID  # noqa: E402
from locfinder.places.categories import select_target  # noqa: E402
from locfinder.places.grocery import classify_grocery  # noqa: E402

BUILDINGS = V2 / "data" / "triangle" / "overture_buildings_accepted.parquet"
AUDIT = V2.parent / "docs" / "experiments" / "audit"

#: Square metres. From the clean polygon-only calibration in
#: `scripts/measure_footprint_separation.py`: 94.2% of OSM `shop=supermarket` footprints are at or
#: above it and 95.2% of `shop=convenience` below. The wider calibration that includes borrowed
#: buildings prefers 750 m² and scores slightly worse, so the clean number is used.
FLOOR_M2 = 650.0

#: A footprint further than this from the place point is not the building the place is in.
NEAR_M = 20.0

#: How far to look for a building that is big enough to be a supermarket before trusting a small
#: matched footprint. 120 m is what separated the five correct chain negatives (nothing over the
#: floor anywhere near) from the two wrong ones (a 3,943 m2 building at this range).
NEAR_LOOK_M = 120.0


def place_name(rec) -> str:
    try:
        return str(dict(rec.get("names")).get("primary") or "")
    except Exception:
        return ""


def decide(area: float | None, tenants: int, biggest_near: float) -> tuple[str, str]:
    """The rule. Returns (proposal, why). There is only ever one proposal: the negative.

    A footprint is an upper bound on the shop inside it, so a small footprint refutes a weekly
    shop whatever the tenancy -- PROVIDED the point is on the right building, which the second
    condition checks. The positive direction was withdrawn; see the module docstring.
    """
    if area is None:
        return "", ("no building footprint under this record -- the rule cannot see it, which is "
                    "not the same as a negative")
    if area >= FLOOR_M2:
        if tenants <= 1:
            return "", (
                f"footprint {area:,.0f} m2 and sole occupant. The positive branch is WITHDRAWN: "
                "both records it produced were food production or distribution, because a real "
                "Triangle supermarket sits in a shopping centre and so shares its footprint"
            )
        return "", (
            f"footprint {area:,.0f} m2 but shared with {tenants - 1} other place record(s) -- the "
            "polygon is measuring the parade, not the unit, so it says nothing either way"
        )
    if biggest_near >= FLOOR_M2:
        return "", (
            f"the matched building is only {area:,.0f} m2, but a {biggest_near:,.0f} m2 building "
            f"stands within {NEAR_LOOK_M:.0f} m. The point may be on the wrong structure -- this "
            "is the case that caught two real Walmarts, so the record is left undecided"
        )
    return "not_a_weekly_shop", (
        f"the whole building is {area:,.0f} m2 and NOTHING within {NEAR_LOOK_M:.0f} m is over the "
        f"{FLOOR_M2:,.0f} m2 floor either. A footprint is an upper bound on the shop inside it, so "
        "no weekly shop stands here, whatever this record says it is"
    )


def main() -> None:
    print("loading places and buildings ...")
    places = gpd.read_parquet(ACCEPTED_PLACES).to_crs(GRID.crs)
    bld = gpd.read_parquet(BUILDINGS).to_crs(GRID.crs)
    bld = bld[bld.geometry.notna() & bld.geometry.is_valid].reset_index(drop=True)
    bld["footprint_m2"] = bld.geometry.area
    bidx = bld.sindex

    # Which building each accepted place sits in, over EVERY category, because a supermarket's
    # neighbours in a parade are restaurants and nail bars, not other grocers.
    bld_of: dict[str, int] = {}
    for _, rec in places.iterrows():
        hit = list(bidx.query(rec.geometry, predicate="within"))
        if not hit:
            hit = list(bidx.query(rec.geometry.buffer(NEAR_M), predicate="intersects"))[:1]
        if hit:
            bld_of[str(rec.get("id"))] = int(hit[0])
    tenants = collections.Counter(bld_of.values())

    grocery = select_target(places, "grocery")
    rows, counts, areas = [], collections.Counter(), []
    for _, rec in grocery.iterrows():
        if classify_grocery(rec) != "unclassified":
            continue
        pid = str(rec.get("id"))
        b = bld_of.get(pid)
        area = float(bld["footprint_m2"].iloc[b]) if b is not None else None
        n = tenants.get(b, 0) if b is not None else 0
        near = list(bidx.query(rec.geometry.buffer(NEAR_LOOK_M), predicate="intersects"))
        biggest_near = max((float(bld["footprint_m2"].iloc[h]) for h in near), default=0.0)
        proposal, why = decide(area, n, biggest_near)
        counts[proposal or "undecided"] += 1
        if area is not None:
            areas.append(area)
        rows.append({
            "id": pid,
            "name": place_name(rec),
            "footprint_m2": f"{area:,.0f}" if area is not None else "",
            "places_in_footprint": n or "",
            "biggest_within_120m": f"{biggest_near:,.0f}" if biggest_near else "",
            "proposal": proposal,
            "evidence": why,
            "verdict": "",
            "notes": "",
        })

    order = {"not_a_weekly_shop": 0, "": 1}
    rows.sort(key=lambda r: (order[r["proposal"]], -float((r["footprint_m2"] or "0").replace(",", ""))))
    out = (AUDIT / "grocery-brandless-footprint-shortlist.csv").resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    total = len(rows)
    print(f"\n{total} grocery records are unclassified and brandless")
    print(f"  threshold {FLOOR_M2:,.0f} m2, from the clean polygon-only calibration\n")
    for key, label in (
        ("not_a_weekly_shop", "proposed NOT a weekly shop (nothing big enough here or nearby)"),
        ("undecided", "left undecided"),
    ):
        n = counts[key]
        print(f"  {n:>4}  {label}  ({n / total * 100:.1f}%)")
    decided = counts["not_a_weekly_shop"]
    print(f"\n  {decided} of {total} decided = {decided / total * 100:.1f}% of the blocker, "
          "all in the cheap direction")
    if areas:
        print(f"  footprint reach: {len(areas)} of {total} have one at all "
              f"({len(areas) / total * 100:.1f}%), median {statistics.median(areas):,.0f} m2")
    naive = sum(1 for r in rows if r["footprint_m2"]
                and float(r["footprint_m2"].replace(",", "")) >= 750)
    print(f"\n  the rule NOT adopted -- area >= 750 m2 with no tenancy test -- would have called "
          f"{naive} of these weekly shops and put them in a published layer")

    # The free correctness probe: a record named after a known chain can be checked without a
    # site visit. It is the only external check available on this sheet, so it is printed.
    import re

    from locfinder.places.grocery import SUPERMARKET_BRANDS
    chains = {re.sub(r"[^a-z0-9]+", " ", b.lower()).strip() for b in SUPERMARKET_BRANDS}
    chains |= {"wal mart", "walmart", "aldi", "lidl", "kroger", "wegmans", "costco"}
    named, wrongable = 0, 0
    for r in rows:
        n = re.sub(r"[^a-z0-9]+", " ", r["name"].lower()).strip()
        if any(c and c in n for c in chains):
            named += 1
            if r["proposal"] == "not_a_weekly_shop":
                wrongable += 1
    print(f"\n  PROBE: {named} of these records are NAMED after a known chain, which makes them "
          "checkable")
    print(f"  the rule calls {wrongable} of those not-a-weekly-shop. Before the 120 m guard it "
          "called 7, of which 2 were real Walmarts with a displaced point.")
    print(f"  {named - wrongable} are left undecided, and they are the best lead on this sheet: "
          "see the note.")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
