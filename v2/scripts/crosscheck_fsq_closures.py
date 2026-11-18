"""Cross-check against OSM the two FSQ closures that were held back from the owner's accept.

**OUTCOME, 2026-11-18: BOTH WERE RELEASED AND ARE NOW APPLIED** (`80cec78`). The owner answered
*"1-4) yes, proceed"* once this had run. Harris Teeter because the hold had no subject -- it is
15,249 m from the Kroger it was supposed to contradict. Sam's Club **over an objection this script
did not answer**: its closed FSQ record is the warehouse club, not a pharmacy counter, and all
this added was that OSM holds no Sam's Club within 300 m, which is absence rather than
observation. `FSQ_CLOSURES_HELD` is now `{}`. Everything below describes the state when it ran.

**Owner decision 2026-11-18:** *"accept the 10 closures"* -- ten of the twelve high-confidence
`date_closed` records from `measure_fsq_coverage.py`. Two were held back, each for a specific
reason, and this script is the check that settles them. It is committed rather than run ad hoc
because it is the evidence for removing a record from a **published** layer.

**Why each was held.**

* **Sam's Club.** FSQ's closed record carries the category `Retail > Warehouse or Wholesale
  Store` -- the club, not a pharmacy counter. A counter closing inside a club that keeps trading
  looks identical in this data to the whole club closing.
* **Harris Teeter.** The Kroger in `EXCLUDED_PLACE_IDS` was dropped *because* OSM shows a Harris
  Teeter trading on its site. If this record were that site, "Harris Teeter closed" would
  contradict the evidence that removed the Kroger.

**What the check can and cannot do.** OSM is silent within 120 m of both records -- that is why
they were in the unreached set in the first place -- so this widens the radius and reports what is
actually there. Absence of a trading store in OSM is **weak** evidence, because OSM's coverage of
some retail is patchy; presence of a *different* trading store is stronger. The site-identity
comparison for Harris Teeter is not weak at all: coordinates either coincide or they do not.

Run from `v2/`:
    python scripts/crosscheck_fsq_closures.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import geopandas as gpd

V2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V2 / "spikes"))
sys.path.insert(0, str(V2))
sys.path.insert(0, str(V2 / "scripts"))

from _common import ACCEPTED_PLACES, GRID  # noqa: E402
from prefill_from_osm import OSM_POIS, name_agreement, place_name  # noqa: E402

#: The two held back, and the brand whose presence in OSM would contradict the closure.
HELD: dict[str, tuple[str, str]] = {
    "c7c31e4e-79a8-43d3-aa0c-4c1bf098747e": ("Sam's Club", "sam"),
    "1937d785-1a98-49c5-9d32-51b7ec7c97af": ("Harris Teeter", "teeter"),
}

#: The Kroger already dropped on OSM evidence, and the Kroger FSQ reports closed. If the held
#: Harris Teeter shares a site with either, the closure is contested.
KROGERS: dict[str, str] = {
    "81190996-0ac4-401f-817a-a9ebff1af58c": "already excluded, on Overture-signals + OSM evidence",
    "790e99cf-ceef-415a-babb-849e75732fa4": "accepted 2026-11-18 from FSQ date_closed=2013-06-25",
}

HARRIS_TEETER = "1937d785-1a98-49c5-9d32-51b7ec7c97af"

#: Two records this far apart cannot be the same storefront.
SAME_SITE_M = 100.0


def describe(rec, label: str) -> None:
    wgs = gpd.GeoSeries([rec.geometry], crs=GRID.crs).to_crs(4326).iloc[0]
    print(f"  {label}: {place_name(rec)!r} at {wgs.y:.5f}, {wgs.x:.5f}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--radii", type=float, nargs="+", default=[120.0, 300.0, 600.0])
    args = ap.parse_args()

    places = gpd.read_parquet(ACCEPTED_PLACES).to_crs(GRID.crs)
    osm = gpd.read_parquet(OSM_POIS).to_crs(GRID.crs)
    tag_cols = [c for c in ("shop", "amenity", "healthcare", "leisure") if c in osm.columns]
    feats = osm[osm[tag_cols].notna().any(axis=1)]
    sidx = feats.sindex

    by_id = {r["id"]: r for _, r in places.iterrows() if r.get("id")}

    # ------------------------------------------------------------- is it the already-dropped site?
    print("=" * 78)
    print("HARRIS TEETER: does it share a site with either Kroger?")
    print("=" * 78)
    ht = by_id.get(HARRIS_TEETER)
    if ht is None:
        print("  the Harris Teeter record is not in the accepted frame")
    else:
        describe(ht, "held Harris Teeter")
        for kid, why in KROGERS.items():
            kr = by_id.get(kid)
            if kr is None:
                print(f"  {kid[:8]} ({why}): not in the frame, so already dropped -- "
                      "cannot compare from this frame")
                continue
            describe(kr, f"Kroger {kid[:8]}")
            dist = ht.geometry.distance(kr.geometry)
            same = dist < SAME_SITE_M
            print(f"    -> {dist:,.0f} m apart: "
                  f"{'THE SAME SITE, the closure is contested' if same else 'different sites'}")

    # ------------------------------------------------------------------ what trades there in OSM?
    for pid, (name, brand) in HELD.items():
        print()
        print("=" * 78)
        print(f"{name.upper()}: what OSM holds nearby")
        print("=" * 78)
        rec = by_id.get(pid)
        if rec is None:
            print("  record is not in the accepted frame")
            continue
        pname = place_name(rec)
        for radius in args.radii:
            hits = list(sidx.query(rec.geometry.buffer(radius), predicate="intersects"))
            print(f"  within {radius:4.0f} m: {len(hits)} tagged OSM features")
            if not hits:
                continue
            contradicted = False
            for h in sorted(hits, key=lambda h: rec.geometry.distance(feats.iloc[h].geometry)):
                feat = feats.iloc[h]
                nm = feat.get("name")
                nm = "" if nm is None or str(nm) == "nan" else str(nm)
                if not nm:
                    continue
                tag = next(((c, str(feat[c])) for c in tag_cols
                            if feat.get(c) is not None and str(feat.get(c)) != "nan"), ("", ""))
                dist = rec.geometry.distance(feat.geometry)
                flag = ""
                if brand in nm.lower():
                    flag = "  <== SAME BRAND TRADING: the closure is contradicted"
                    contradicted = True
                print(f"      {dist:6.1f} m  {tag[0]}={tag[1]:<14} {nm[:38]:38s}"
                      f" agr={name_agreement(pname, nm):.2f}{flag}")
            if not contradicted:
                print(f"      -> no {name!r} in OSM within {radius:.0f} m. Weak support for the "
                      "closure: OSM's retail coverage is patchy, so absence is not proof.")
            break
        else:
            print("  OSM is silent at every radius tried -- it cannot settle this either way")


if __name__ == "__main__":
    main()
