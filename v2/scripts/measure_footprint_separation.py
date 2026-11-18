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


---

## SECOND PASS, 2026-11-18, AND WHY THE FIRST RUN DECIDED NOTHING

The first run printed `REFUTED`. **That verdict was not trustworthy and has been replaced**, for
two reasons found by reading the output rather than the headline:

1. **The calibration sets were n=9 and n=3.** "66.7% of convenience stores below the threshold"
   was two shops out of three. Nothing can be concluded either way from that, and `REFUTED` on
   that basis would have been the mirror image of yesterday's error -- believing a mechanism from
   one case, then *rejecting* one from three.
2. **The tenancy partition was wrong.** It sent 169 of 178 supermarkets into the "multi-tenant"
   bucket, because a supermarket with an in-store pharmacy, bank counter or coffee shop has
   several Overture place records inside one footprint. That is not a mall. "Shares a building
   with another place" turned out to be a bad proxy for "is one unit in a retail parade", so it is
   no longer the partition the verdict rests on; it is reported as a covariate.

**The replacement calibration uses OSM's own tags**, which gives two populations large enough to
decide with: **292 `shop=supermarket`** and **431 `shop=convenience`** features in the Triangle
extract, independent of our place records. Where the OSM feature is itself a polygon -- 103 of the
supermarkets and 269 of the convenience stores -- its own geometry is the footprint and no join is
needed at all. For the points, the Overture building under the point is used.

The predictions above stand unchanged and are judged against this larger measurement. The
thresholds that would refute them were fixed before either run.

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


def osm_area(feat, bld, bidx) -> tuple[float | None, str]:
    """The footprint of an OSM feature, and where the number came from.

    A polygon feature IS its own footprint -- that is the cleanest case and needs no join, and it
    keeps the licence story identical to the `osm_pois` extract the project already uses. A point
    feature has to borrow the Overture building underneath it.
    """
    geom = feat.geometry
    if geom is None:
        return None, "no geometry"
    if geom.geom_type in ("Polygon", "MultiPolygon"):
        return float(geom.area), "its own polygon"
    hit = list(bidx.query(geom, predicate="within"))
    if not hit:
        hit = list(bidx.query(geom.buffer(NEAR_M), predicate="intersects"))[:1]
    if not hit:
        return None, "no building under the point"
    return float(bld["footprint_m2"].iloc[hit[0]]), "the building under the point"


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

    # ------------------------------------------------------------ the real calibration
    # OSM's own tags, which give two populations big enough to decide with. The sets above are
    # kept as a secondary check on OUR records, not as the thing the verdict rests on.
    print("\nCALIBRATION -- OSM's own tags, the only sets here large enough to decide with")
    osm_super, osm_conv = [], []
    src = collections.Counter()
    for tag, bucket in (("supermarket", osm_super), ("convenience", osm_conv)):
        feats = osm[osm["shop"] == tag] if "shop" in osm.columns else osm.iloc[0:0]
        reached = 0
        for _, f in feats.iterrows():
            reached += 1
            a, how = osm_area(f, bld, bidx)
            src[f"{tag}: {how}"] += 1
            if a is not None and a > 0:
                bucket.append(a)
        gate(f"OSM shop={tag} has a footprint", reached, len(bucket))
    for k, v in sorted(src.items()):
        print(f"      {k}: {v}")
    print()
    s = describe("OSM shop=supermarket", osm_super)
    c = describe("OSM shop=convenience", osm_conv)

    print("\nSECONDARY -- our own records, too few to decide with, reported for consistency")
    describe("our supermarkets, sole place in bldg", known_super)
    describe("our convenience, sole place in bldg", known_conv)
    describe("our supermarkets, shared bldg", multi_super)
    describe("our convenience, shared bldg", multi_conv)
    print("  (169 of 178 of our supermarkets land in 'shared': an in-store pharmacy or coffee")
    print("   shop is a separate place record, which is NOT the mall confounder this was meant")
    print("   to catch. The partition is a covariate, not the basis of the verdict below.)")

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
    for thr in range(100, 8001, 25):
        tp = sum(1 for a in osm_super if a >= thr) / len(osm_super)
        tn = sum(1 for a in osm_conv if a < thr) / len(osm_conv)
        acc = min(tp, tn)
        if acc > best_acc:
            best, best_acc = thr, acc
    tp = sum(1 for a in osm_super if a >= best) / len(osm_super)
    tn = sum(1 for a in osm_conv if a < best) / len(osm_conv)
    print(f"  best single threshold = {best:,} m2: "
          f"{tp * 100:.1f}% of supermarkets above it, {tn * 100:.1f}% of convenience below it")
    print(f"  worse side = {best_acc * 100:.1f}% (prediction was >=85% on BOTH)")
    verdict = "SUPPORTED" if (ratio >= 3.0 and best_acc >= 0.85) else "REFUTED"
    print(f"\n  => the prediction is {verdict}")
    if verdict == "REFUTED":
        print("     The rule stays owed. Footprint area is not the mechanism, and saying so is "
              "the result -- not a reason to look for a number that agrees with me.")

    # What the threshold would do to the records the rule is actually for. Printed whether the
    # prediction held or not, because the owner needs the size of the effect either way.
    if open_brandless:
        above = sum(1 for a in open_brandless if a >= best)
        print(f"\n  applied to the {len(open_brandless)} open brandless records that HAVE a "
              f"footprint, at {best:,} m2:")
        print(f"    {above} would be proposed a weekly shop, "
              f"{len(open_brandless) - above} a corner shop")
        print(f"    and {323 - len(open_brandless)} of the 323 brandless records are not "
              "reachable this way at all")


if __name__ == "__main__":
    main()
