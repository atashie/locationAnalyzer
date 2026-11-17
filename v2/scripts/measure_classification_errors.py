"""Which accepted places are not the kind of thing their category says they are?

**The owner asked for this on 2026-11-17**, after "Roofing Inc." turned up in the grocery
destination set: *"we need a systematic review of classification errors like this."*

Every estimand in the project compares our pipeline to our own engine, and both sides read the same
place list. A record that is in the wrong category produces perfect agreement and a wrong answer to
a household — the same blind spot `audit_destination_truth.py` was written for, one level up: that
script asks whether a destination is still *open*, this one asks whether it was ever the *right
kind of thing*.

**This flags candidates and changes nothing.** It writes a sheet to triage, exactly as the
destination-truth audit does, because every signal here has a known false-positive mode:

* A legal suffix is normal for a real shop. "Kinstar International Food Inc" is probably a grocery;
  "Roofing Inc." is not. The suffix alone cannot tell them apart, so it is scored, not acted on.
* Absence of a nearby OSM shop is weak evidence. OSM's coverage of small independent grocers is
  itself patchy, which is why it is a point of suspicion rather than a verdict.
* A low Overture confidence is a statement about the record, not about the world.

So each record gets a list of reasons and a count, and a human decides. Anything scoring two or
more reasons is worth a look; one reason on its own usually is not.

Run from `v2/`:
    python scripts/measure_classification_errors.py
    python scripts/measure_classification_errors.py --category grocery --min-score 1
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

import geopandas as gpd

V2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V2 / "spikes"))
sys.path.insert(0, str(V2))

from _common import ACCEPTED_PLACES, GRID  # noqa: E402
from locfinder.places.categories import WEDGE_CATEGORIES, select_target  # noqa: E402

OSM_POIS = V2 / "data" / "triangle" / "osm_pois.parquet"
OUT = V2.parent / "docs" / "experiments" / "audit" / "classification-errors-to-check.csv"

#: Words that name a trade or a facility rather than a shop a household visits. Matched on the
#: place's own name, case-insensitively, as whole words.
TRADE_WORDS = (
    "roofing", "plumbing", "hvac", "electric", "electrical", "construction", "contractor",
    "landscaping", "paving", "towing", "insurance", "realty", "realtor", "mortgage", "staffing",
    "consulting", "logistics", "trucking", "distribution center", "distribution centre",
    "warehouse", "storage", "wholesale", "manufacturing", "laboratory", "clinic", "dental",
    "attorney", "law office", "accounting", "tax service", "salon", "barber", "car wash",
    "auto repair", "body shop", "funeral",
)

#: A corporate suffix. Normal on a real shop, so worth only one point and never alone.
SUFFIX = re.compile(r"\b(inc|llc|l\.l\.c|corp|incorporated|co|ltd|lp|llp)\b\.?", re.I)


def place_name(rec) -> str:
    names = rec.get("names")
    try:
        return str(dict(names).get("primary") or "")
    except Exception:
        return ""


def brand_name(rec) -> str:
    brand = rec.get("brand")
    if brand is None:
        return ""
    try:
        names = dict(brand).get("names")
        return str(dict(names).get("primary") or "") if names is not None else ""
    except Exception:
        return ""


def reasons_for(rec, name: str, brand: str, osm_near: int, category: str) -> list[str]:
    out: list[str] = []
    low = name.lower()
    hits = [w for w in TRADE_WORDS if w in low]
    if hits:
        out.append(f"name names a trade or facility ({'; '.join(hits)})")
    if SUFFIX.search(name):
        out.append("name carries a corporate suffix")
    if not name:
        out.append("no name at all")
    try:
        conf = float(rec.get("confidence"))
        if conf < 0.70:
            out.append(f"low Overture confidence {conf:.2f}")
    except Exception:
        pass
    if osm_near == 0:
        out.append("no corroborating OSM feature within 100 m")
    if brand and category in ("grocery", "supermarket"):
        from locfinder.places.grocery import NOT_A_GROCERY_BRANDS
        if brand in NOT_A_GROCERY_BRANDS:
            out.append(f"brand names a different business entirely ({brand})")
    if brand and name and brand.split()[0].lower() not in name.lower():
        out.append(f"brand '{brand[:28]}' does not appear in the name")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--category", action="append", default=None,
                    help="repeatable; default: every wedge category with places")
    ap.add_argument("--min-score", type=int, default=2,
                    help="how many reasons before a record is written to the sheet (default 2)")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    args.out = args.out.resolve()

    places = gpd.read_parquet(ACCEPTED_PLACES).to_crs(GRID.crs)
    osm = gpd.read_parquet(OSM_POIS).to_crs(GRID.crs)
    # Anything OSM considers a going concern, not only shops: a school, a cafe or an amenity all
    # corroborate that SOMETHING is there.
    cols = [c for c in ("shop", "amenity", "leisure", "tourism", "office") if c in osm.columns]
    mask = osm[cols].notna().any(axis=1) if cols else osm.index == -1
    features = osm[mask]
    sidx = features.sindex

    categories = args.category or [c for c in WEDGE_CATEGORIES
                                   if c not in ("supermarket", "specialty_grocery")]
    rows: list[dict] = []
    print(f"{len(features):,} OSM features used for corroboration\n")
    for category in categories:
        try:
            sel = select_target(places, category)
        except Exception as exc:  # a named place, or a category with no Overture mapping
            print(f"  {category:<16} skipped ({type(exc).__name__})")
            continue
        if not len(sel):
            print(f"  {category:<16} no records")
            continue
        flagged = 0
        for _, rec in sel.iterrows():
            name, brand = place_name(rec), brand_name(rec)
            near = len(list(sidx.query(rec.geometry.buffer(100.0), predicate="intersects")))
            why = reasons_for(rec, name, brand, near, category)
            if len(why) >= args.min_score:
                flagged += 1
                rows.append({
                    "category": category, "id": rec.get("id"), "name": name, "brand": brand,
                    "confidence": rec.get("confidence"), "osm_features_within_100m": near,
                    "score": len(why), "reasons": " | ".join(why),
                    "verdict": "", "notes": "",
                })
        print(f"  {category:<16} {len(sel):>5,} records, {flagged:>4} flagged "
              f"({flagged / len(sel) * 100:.1f}%)")

    rows.sort(key=lambda r: (-r["score"], r["category"], r["name"]))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]) if rows else
                           ["category", "id", "name", "brand", "confidence",
                            "osm_features_within_100m", "score", "reasons", "verdict", "notes"])
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {len(rows):,} candidates to {args.out}")
    print("`verdict` is for a human: keep / wrong-category / not-a-place / unsure.")


if __name__ == "__main__":
    main()
