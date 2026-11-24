"""Can evidence we ALREADY HOLD split the 76 uncorroborated published records?

The screen that found them consults three things: the brand table, OSM name agreement, Foursquare
name agreement. It never consults the **building footprint**, although `locfinder/places/footprint.py`
exists, states the asymmetry in full, and 84 MB of Overture buildings sit in
`data/triangle/overture_buildings_accepted.parquet`.

`footprint.py`'s own words: *"nothing big within reach does refute a weekly shop. No supermarket
stands there, whatever the record calls itself."* That REFUTED verdict is a positive,
evidence-based reason to remove a record, and it is the instrument this problem has been missing.

This script does not decide anything. It asks: how far does evidence already on disk get us, and
what is left over?
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

V2 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(V2))
sys.path.insert(0, str(V2 / "spikes"))

import geopandas as gpd  # noqa: E402
import numpy as np  # noqa: E402

from _common import ACCEPTED_PLACES, GRID  # noqa: E402
from locfinder.places.footprint import (  # noqa: E402
    CORROBORATED,
    FLOOR_M2,
    NEAR_LOOK_M,
    NEIGHBOUR,
    REFUTED,
    SURVEY_LOOK_M,
    UNSURVEYED,
    corroboration,
)

SHEET = V2.parent / "docs" / "experiments" / "audit" / "uncorroborated-grocery.csv"
BUILDINGS = V2 / "data" / "triangle" / "overture_buildings_accepted.parquet"
PUB = V2 / "spikes" / "g3-render" / "fixtures" / "published"
STEM = "own_triangle_grocery_walk"

#: A suite, unit or mailbox number in the address: the record is at an address INSIDE something
#: else. A weekly shop is not in suite 112.
SUITE = re.compile(r"\b(ste|suite|unit|apt|apartment|#\s*\d|pmb|box)\b", re.I)
#: A company-registration suffix. `Jovc Food Corp` is a company; a shop is a place.
COMPANY = re.compile(r"\b(llc|l\.l\.c|inc|incorporated|corp|corporation|co|ltd|lp|llp|"
                     r"enterprises|holdings|partners|group|wholesale|distribut\w*)\b", re.I)
#: Words that name a farm or a producer rather than a shop you do a weekly shop in.
PRODUCER = re.compile(r"\b(farm|farms|orchard|grove|patch|nursery|greenhouse|apiary|"
                      r"creamery|dairy|ranch|gardens?)\b", re.I)


def name_of(rec) -> str:
    n = rec.get("names")
    return str(n.get("primary") or "") if hasattr(n, "get") else ""


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
    rows = [r for r in csv.DictReader(SHEET.open(encoding="utf-8"))
            if r["outcome"].startswith("UNCORROBORATED")]
    wanted = {r["place_id"] for r in rows}
    print(f"uncorroborated published records: {len(wanted)}")

    # ---- cells each one answers, from the republished planes ----
    d = json.loads((PUB / f"{STEM}.destinations.json").read_text(encoding="utf-8"))
    ordinal_places = {e["ordinal"]: [p["gers_id"] for p in e["places"]] for e in d["destinations"]}
    de = np.frombuffer((PUB / f"{STEM}.dest.bin").read_bytes(), dtype=np.uint16)
    st = np.frombuffer((PUB / f"{STEM}.status.bin").read_bytes(), dtype=np.uint8)
    per_ordinal = Counter(de[st == 0].tolist())
    cells: Counter[str] = Counter()
    for ordinal, count in per_ordinal.items():
        for pid in ordinal_places.get(ordinal, []):
            cells[pid] += count

    print("loading places and buildings ...")
    places = gpd.read_parquet(ACCEPTED_PLACES).to_crs(GRID.crs).reset_index(drop=True)
    bld = gpd.read_parquet(BUILDINGS).to_crs(GRID.crs)
    bidx = bld.sindex

    out = []
    for _, rec in places[places["id"].isin(wanted)].iterrows():
        pid = str(rec["id"])
        nm, addr = name_of(rec), address_of(rec)
        near = list(bidx.query(rec.geometry.buffer(NEAR_LOOK_M), predicate="intersects"))
        # Does our building data cover this place AT ALL? An empty `near` means either that
        # nothing big stands here or that the download does not reach here, and before 2026-11-23
        # both came back `REFUTED`. 15 of the 30 refusals in the first run of this sheet were the
        # second kind.
        surveyed = bool(list(bidx.query(rec.geometry.buffer(SURVEY_LOOK_M),
                                        predicate="intersects")))
        got = corroboration(rec.geometry, [bld.geometry.iloc[h] for h in near],
                            surveyed=surveyed)
        out.append({
            "id": pid, "name": nm, "address": addr,
            "cells": cells.get(pid, 0),
            "verdict": got.verdict,
            "host_m2": round(got.host_m2, 1) if hasattr(got, "host_m2") else round(got[1], 1),
            "near_m2": round(got.near_m2, 1) if hasattr(got, "near_m2") else round(got[2], 1),
            "suite": bool(SUITE.search(addr)),
            "company": bool(COMPANY.search(nm)),
            "producer": bool(PRODUCER.search(nm)),
            "no_address": not addr.strip(),
        })

    print()
    print("=== what the FOOTPRINT says about the 76 ===")
    verdicts = (CORROBORATED, NEIGHBOUR, REFUTED, UNSURVEYED)
    for v in verdicts:
        sel = [r for r in out if r["verdict"] == v]
        c = sum(r["cells"] for r in sel)
        print(f"  {v:<13} {len(sel):>3} records   {c:>7,} cells answered")
    print(f"  (floor {FLOOR_M2:.0f} m2, look {NEAR_LOOK_M:.0f} m, "
          f"survey look {SURVEY_LOOK_M:.0f} m)")
    # The first run after UNSURVEYED existed printed 23 + 23 + 15 = 61 of 76 records and said
    # nothing about the missing 15, because this loop named three verdicts and the data now has
    # four. A summary that does not add up to its population is not a summary.
    counted = sum(len([r for r in out if r["verdict"] == v]) for v in verdicts)
    assert counted == len(out), (
        f"{counted} of {len(out)} records are covered by the summary, so a verdict is missing "
        f"from it: {sorted({r['verdict'] for r in out} - set(verdicts))}")

    print()
    print("=== the name/address signals, which cost nothing ===")
    for key, label in (("company", "a company-registration suffix"),
                       ("producer", "a farm or producer word"),
                       ("suite", "a suite/unit/mailbox address"),
                       ("no_address", "NO address at all")):
        sel = [r for r in out if r[key]]
        print(f"  {label:<32} {len(sel):>3} records   "
              f"{sum(r['cells'] for r in sel):>7,} cells")

    print()
    uns = sorted((r for r in out if r["verdict"] == UNSURVEYED), key=lambda r: -r["cells"])
    if uns:
        print("=== UNSURVEYED: we hold no building data here, so the footprint says NOTHING ===")
        print(f"{'cells':>7}  name / address")
        for r in uns:
            print(f"{r['cells']:>7,}  {r['name'][:36]:<36} {r['address'][:44]}")
        print()

    print("=== REFUTED: nothing big enough stands there, and our data DOES cover the place ===")
    ref = sorted((r for r in out if r["verdict"] == REFUTED), key=lambda r: -r["cells"])
    print(f"{'cells':>7}  {'host m2':>8} {'near m2':>8}  name / address")
    for r in ref:
        flags = "".join(c for c, on in (("C", r["company"]), ("P", r["producer"]),
                                        ("S", r["suite"]), ("-", r["no_address"])) if on)
        print(f"{r['cells']:>7,}  {r['host_m2']:>8.0f} {r['near_m2']:>8.0f}  "
              f"{flags:<4} {r['name'][:34]:<34} {r['address'][:40]}")

    print()
    print("=== CORROBORATED by footprint: a big building contains the point ===")
    cor = sorted((r for r in out if r["verdict"] == CORROBORATED), key=lambda r: -r["cells"])
    for r in cor:
        print(f"{r['cells']:>7,}  host {r['host_m2']:>7.0f} m2  {r['name'][:34]:<34} "
              f"{r['address'][:40]}")

    print()
    print("=== NEIGHBOUR: big building nearby, point not inside it (cannot tell) ===")
    nei = sorted((r for r in out if r["verdict"] == NEIGHBOUR), key=lambda r: -r["cells"])
    for r in nei:
        print(f"{r['cells']:>7,}  near {r['near_m2']:>7.0f} m2  {r['name'][:34]:<34} "
              f"{r['address'][:40]}")

    dest = V2.parent / "docs" / "experiments" / "audit" / "uncorroborated-grocery-triage.csv"
    with dest.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(sorted(out, key=lambda r: -r["cells"]))
    print()
    print(f"wrote {dest}")


if __name__ == "__main__":
    main()
