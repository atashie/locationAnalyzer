"""Two questions the plan turns on.

1. The published `grocery` layer contains 2 records our OWN classifier calls `not_a_grocery`.
   That is not a judgement call, it is a flat contradiction. Which are they, and how many cells?
2. What fields does a place record carry that the screens do not consult? `confidence` in
   particular -- Overture publishes one and nothing here reads it.
"""
from __future__ import annotations

import json
import pathlib
import sys
from collections import Counter

import numpy as np

V2 = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(V2))
sys.path.insert(0, str(V2 / "spikes"))

import geopandas as gpd  # noqa: E402

from _common import ACCEPTED_PLACES  # noqa: E402
from locfinder.places.categories import select_overture  # noqa: E402
from locfinder.places.grocery import classify_grocery  # noqa: E402

PUB = V2 / "spikes" / "g3-render" / "fixtures" / "published"
STEM = "own_triangle_grocery_walk"


def name_of(rec) -> str:
    n = rec.get("names")
    return str(n.get("primary") or "") if hasattr(n, "get") else ""


def main() -> None:
    places = gpd.read_parquet(ACCEPTED_PLACES)
    grocery = set(select_overture(places, "grocery")["id"])
    sel = places[places["id"].isin(grocery)]

    d = json.loads((PUB / f"{STEM}.destinations.json").read_text(encoding="utf-8"))
    ordinal_places = {e["ordinal"]: [p["gers_id"] for p in e["places"]] for e in d["destinations"]}
    de = np.frombuffer((PUB / f"{STEM}.dest.bin").read_bytes(), dtype=np.uint16)
    st = np.frombuffer((PUB / f"{STEM}.status.bin").read_bytes(), dtype=np.uint8)
    cells: Counter[str] = Counter()
    for ordinal, count in Counter(de[st == 0].tolist()).items():
        for pid in ordinal_places.get(ordinal, []):
            cells[pid] += count

    print("=== PUBLISHED as grocery, and our own classifier says not_a_grocery ===")
    for _, rec in sel.iterrows():
        if classify_grocery(rec) == "not_a_grocery":
            pid = str(rec["id"])
            print(f"   {pid}  {name_of(rec)[:44]:<44} cells answered = {cells.get(pid, 0):,}")

    print()
    print("=== cells answered, by what the classifier calls the destination ===")
    by_class: Counter[str] = Counter()
    recs_by_class: Counter[str] = Counter()
    for _, rec in sel.iterrows():
        k = classify_grocery(rec)
        recs_by_class[k] += 1
        by_class[k] += cells.get(str(rec["id"]), 0)
    answered = int((st == 0).sum())
    print(f"   cells with an answer: {answered:,}")
    for k in ("supermarket", "specialty", "unclassified", "not_a_grocery"):
        print(f"   {k:<16} {recs_by_class[k]:>4} records   {by_class[k]:>8,} cells  "
              f"({by_class[k] / answered * 100:5.2f}% of answered cells, counting sets once per place)")

    print()
    print("=== fields on a place record ===")
    print("   ", sorted(places.columns))
    if "confidence" in places.columns:
        conf = places.loc[places["id"].isin(grocery), "confidence"]
        print()
        print(f"   confidence on the published grocery layer: min {conf.min():.3f} "
              f"median {conf.median():.3f} max {conf.max():.3f}")
        import csv
        sheet = V2.parent / "docs" / "experiments" / "audit" / "uncorroborated-grocery.csv"
        unc = {r["place_id"] for r in csv.DictReader(sheet.open(encoding="utf-8"))
               if r["outcome"].startswith("UNCORROBORATED")}
        cu = places.loc[places["id"].isin(unc), "confidence"]
        print(f"   confidence on the 76 uncorroborated:       min {cu.min():.3f} "
              f"median {cu.median():.3f} max {cu.max():.3f}")
        corroborated = grocery - unc
        cc = places.loc[places["id"].isin(corroborated), "confidence"]
        print(f"   confidence on the other {len(corroborated)}:                min {cc.min():.3f} "
              f"median {cc.median():.3f} max {cc.max():.3f}")
        print()
        print("   Is confidence separable? share of each population below a few thresholds:")
        for t in (0.2, 0.3, 0.4, 0.5, 0.6):
            print(f"     < {t:.1f}:  uncorroborated {float((cu < t).mean()) * 100:5.1f}%   "
                  f"corroborated {float((cc < t).mean()) * 100:5.1f}%")


if __name__ == "__main__":
    main()
