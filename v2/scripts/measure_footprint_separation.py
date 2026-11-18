"""Can a building footprint tell a weekly shop from a corner shop?

**The open decision this is for.** 323 of the 541 grocery records carry no Overture `brand`, and
`grocery_store` covers a supermarket and a corner shop alike. The resume point has said for two
days that splitting them "needs a rule the owner has not been shown yet", and
`locfinder/places/grocery.py` says why nothing in the data can do it:

> nothing in Overture or OSM measures range. A more robust mechanism would need something that
> does: **floor area**, aisle or department counts, a product-range signal from a source that holds
> one, or simply asking people in the neighbourhood.

`data/triangle/overture_buildings_accepted.parquet` holds **522,160 footprint polygons**. Floor
area is the first item on that list and it is already on disk. This script measures whether it
separates the two populations. It decides nothing and writes no table.

---

## THE PREDICTION, WRITTEN AND COMMITTED BEFORE THE SCRIPT WAS RUN

Ledger instance 57: *predict a number before believing a mechanism, and say which number would
refute it.* Yesterday I promoted one false positive to a mechanism and the mechanism failed both
of its own tests. So, in advance:

1. **Separation.** Weekly-shop supermarkets should have a median footprint of **at least
   2,500 m²** (a Food Lion is roughly 3,500 m², an ALDI roughly 1,700 m²). Convenience stores
   should come in **under 400 m²** (a 7-Eleven is roughly 250 m²).
2. **Coverage.** At least **70%** of the open brandless records should have a footprint under them
   at all. Microsoft's ML footprints are dense in this metro.
3. **A usable threshold should exist** somewhere near 1,000 m², classifying **at least 85%** of
   both calibration sets correctly.

**WHICH NUMBERS WOULD REFUTE IT, and in that case the rule stays owed and I say so:**

* the two medians within a **factor of 3** of each other -- then footprint is measuring something
  other than what a household means by a weekly shop;
* no single threshold reaching **85% on both** sets at once;
* footprint coverage of the open records below **50%** -- a rule that cannot see half the records
  is not a rule for this problem, however well it separates the half it can see.

## THE CONFOUNDER I EXPECT TO DOMINATE, AND MEASURE SEPARATELY

A shop in a strip mall or a mall sits inside a footprint that contains *many* units. The polygon
then measures the mall, not the shop, and a corner shop in a retail parade would score as a
supermarket. So every record is bucketed by how many accepted places share its footprint, and the
single-tenant and multi-tenant numbers are reported apart. **If the mechanism only works on
single-tenant buildings, that is a real but much narrower rule, and the note has to say which.**

## LICENCE, WHICH IS A SEPARATE QUESTION FROM WHETHER IT WORKS

The buildings file was acquired under the **diagnostic** allowlist, and its own report records
`"use": "building-weighted coverage diagnostic (S2.4): rasterised to counts, never republished"`.
Every row is ODbL-1.0 or CC BY 4.0. Measuring is a diagnostic use and is clearly inside that.
**Classifying a published layer from it is not** -- it would make the grocery layer an ODbL-derived
database, and the registry row saying "never republished" would stop being true.

That is the same exposure the project already carries, since `OSM_CONFIRMED_SUPERMARKETS` is
derived from the ODbL `osm_pois` extract and feeds the same published layer, and decision 17 says
ODbL publication of OSM-derived work is welcome. But it is the owner's line to move, not a
script's, so this script measures and stops.

Run from `v2/`:
    python scripts/measure_footprint_separation.py
"""
from __future__ import annotations

import collections
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
from locfinder.places.name_match import clears_the_floor, match_verdict  # noqa: E402

BUILDINGS = V2 / "data" / "triangle" / "overture_buildings_accepted.parquet"
OSM_POIS = V2 / "data" / "triangle" / "osm_pois.parquet"

#: A footprint further than this from the place point is not the building the place is in.
NEAR_M = 20.0


def gate(name: str, reached: int, found: int, detail: str = "") -> None:
    """Every gate reports how often it was REACHED, not only what it found. A gate that never
    fires otherwise prints a blank that reads as a clean result; ledger instance 47."""
    if reached == 0:
        print(f"  [gate] {name}: NEVER REACHED (0 opportunities) -- a blank here would read as "
              "a clean result")
        return
    print(f"  [gate] {name}: reached {reached}, found {found} ({found / reached * 100:.1f}%)"
          + (f" -- {detail}" if detail else ""))


def place_name(rec) -> str:
    try:
        return str(dict(rec.get("names")).get("primary") or "")
    except Exception:
        return ""


def describe(label: str, areas: list[float]) -> dict[str, float]:
    if not areas:
        print(f"  {label:<34} NO RECORDS -- nothing to describe")
        return {}
    areas = sorted(areas)
    q = statistics.quantiles(areas, n=4) if len(areas) >= 4 else [areas[0], areas[0], areas[-1]]
    stats = {"n": len(areas), "median": statistics.median(areas), "q1": q[0], "q3": q[2],
             "min": areas[0], "max": areas[-1]}
    print(f"  {label:<34} n={stats['n']:<5} median={stats['median']:>9,.0f} m2   "
          f"IQR {stats['q1']:>8,.0f} - {stats['q3']:>8,.0f}   "
          f"range {stats['min']:>7,.0f} - {stats['max']:>9,.0f}")
    return stats


def main() -> None:
    print("loading places, buildings and OSM POIs ...")
    places = gpd.read_parquet(ACCEPTED_PLACES).to_crs(GRID.crs)
    grocery = select_target(places, "grocery")
    bld = gpd.read_parquet(BUILDINGS).to_crs(GRID.crs)
    bld = bld[bld.geometry.notna() & bld.geometry.is_valid]
    bld = bld.reset_index(drop=True)
    bld["footprint_m2"] = bld.geometry.area
    bidx = bld.sindex

    osm = gpd.read_parquet(OSM_POIS).to_crs(GRID.crs)
    if "shop" in osm.columns:
        conv = osm[osm["shop"] == "convenience"]
    else:
        conv = osm.iloc[0:0]
    cidx = conv.sindex

    # ---------------------------------------------------------------- footprint per place
    print(f"\n{len(grocery):,} grocery records, {len(bld):,} building footprints")
    reached_fp = 0
    found_fp = 0
    footprint: dict[str, float] = {}
    tenants: collections.Counter[int] = collections.Counter()
    # Which building each place sits in, so tenancy can be counted.
    bld_of: dict[str, int] = {}
    all_places = places.reset_index(drop=True)
    for _, rec in all_places.iterrows():
        hit = list(bidx.query(rec.geometry, predicate="within"))
        if not hit:
            near = list(bidx.query(rec.geometry.buffer(NEAR_M), predicate="intersects"))
            hit = near[:1]
        if hit:
            bld_of[str(rec.get("id"))] = int(hit[0])
    for b in bld_of.values():
        tenants[b] += 1

    for _, rec in grocery.iterrows():
        pid = str(rec.get("id"))
        reached_fp += 1
        b = bld_of.get(pid)
        if b is not None:
            found_fp += 1
            footprint[pid] = float(bld["footprint_m2"].iloc[b])

    print("\nCOVERAGE -- can the mechanism see the records at all?")
    gate("a grocery record has a footprint", reached_fp, found_fp,
         f"prediction was >=70%, refuted below 50%")

    # ------------------------------------------------------- the two calibration sets
    known_super, known_conv, open_brandless = [], [], []
    multi_super, multi_conv = [], []
    reached_conv = 0
    for _, rec in grocery.iterrows():
        pid = str(rec.get("id"))
        area = footprint.get(pid)
        cls = classify_grocery(rec)
        alone = tenants.get(bld_of.get(pid, -1), 0) <= 1
        if cls == "supermarket":
            if area is not None:
                (known_super if alone else multi_super).append(area)
            continue
        # The negative set: OSM calls it a convenience store AND the names agree, so the match
        # is worth something. The floor from name_match.py is what makes this set usable.
        pname = place_name(rec)
        near = list(cidx.query(rec.geometry.buffer(60.0), predicate="intersects"))
        reached_conv += 1
        matched = False
        for h in near:
            f = conv.iloc[h]
            nm = f.get("name")
            nm = "" if nm is None or str(nm) == "nan" else str(nm)
            if clears_the_floor(match_verdict(pname, nm)):
                matched = True
                break
        if matched and area is not None:
            (known_conv if alone else multi_conv).append(area)
        elif cls == "unclassified" and area is not None:
            open_brandless.append(area)

    print("\nSEPARATION -- single-tenant buildings only, where the polygon is the shop")
    s = describe("known weekly-shop supermarkets", known_super)
    c = describe("OSM convenience, names agreeing", known_conv)

    print("\nthe confounder: buildings shared with other places")
    describe("supermarkets, multi-tenant", multi_super)
    describe("convenience, multi-tenant", multi_conv)

    print("\nthe population the rule is FOR")
    describe("open brandless, unclassified", open_brandless)

    # ------------------------------------------------------------------ the verdict
    print("\nDOES IT SEPARATE?")
    if not s or not c:
        print("  CANNOT SAY: one calibration set is empty. The mechanism is not refuted, it is "
              "unmeasured, and those are different results.")
        return
    ratio = s["median"] / c["median"] if c["median"] else float("inf")
    print(f"  median ratio supermarket/convenience = {ratio:.2f}x "
          f"(refuted below 3x, as predicted)")

    best, best_acc = None, -1.0
    for thr in range(100, 6001, 50):
        tp = sum(1 for a in known_super if a >= thr) / len(known_super)
        tn = sum(1 for a in known_conv if a < thr) / len(known_conv)
        acc = min(tp, tn)
        if acc > best_acc:
            best, best_acc = thr, acc
    tp = sum(1 for a in known_super if a >= best) / len(known_super)
    tn = sum(1 for a in known_conv if a < best) / len(known_conv)
    print(f"  best single threshold = {best:,} m2: "
          f"{tp * 100:.1f}% of supermarkets above it, {tn * 100:.1f}% of convenience below it")
    print(f"  worse side = {best_acc * 100:.1f}% (prediction was >=85% on BOTH)")
    verdict = "SUPPORTED" if (ratio >= 3.0 and best_acc >= 0.85) else "REFUTED"
    print(f"\n  => the prediction is {verdict}")
    if verdict == "REFUTED":
        print("     The rule stays owed. Footprint area is not the mechanism, and saying so is "
              "the result -- not a reason to look for a number that agrees with me.")


if __name__ == "__main__":
    main()
