"""Propose a classification for each accepted place from the OSM feature it sits on.

**Owner decision, 2026-11-17**, for both open lists — the 314 unclassified grocery records and the
414 classification candidates: *"start with osm to prefill, then use yelp or a similar service to
confirm / backfill as needed."*

This is the OSM half. It is free, already on disk, and licence-clean (ODbL, which the project
already uses). The Yelp half is **not built** and needs a key the owner holds; see the end of this
docstring.

**What it does.** For each record it finds nearby OSM features carrying a `shop`, `amenity`,
`healthcare` or `leisure` tag, scores each by distance and by how well the names agree, and
proposes a class from the best match's tag. It writes a sheet with the evidence and a blank
`verdict` column.

**What it does not do.** It does not edit any table. A proposal is a starting point for the
curated lists in `locfinder/places/grocery.py` and `locfinder/places/exclusions.py`, which are
meant to be read and agreed to rather than generated.

**Name agreement is the load-bearing signal, not distance.** Two shops forty metres apart in a
strip mall are both "nearby"; only the name says which is which. A match with a strong name
agreement at 80 m is better evidence than a tag collision at 15 m, so the score weights them that
way and the sheet prints both so a reader can disagree.

**THERE IS NOW A FLOOR, and it changes what this script outputs.** Owner decision 2026-11-18,
*"1-4) yes, proceed"*. Until then a proposal was made from the best match's tag however badly the
names disagreed, and on this sheet that was **51 of 117 grocery proposals (43.6%)** and **29 of
102 pharmacy (28.4%)** resting on a match with a different business's name -- `Flower Gallery`
proposed as a supermarket because an OSM Harris Teeter sat 32.6 m away. Those proposals are now
WITHHELD: the row keeps its tag, distance and agreement, the proposal moves to
`withheld_proposal`, and `evidence` says which of the two reasons applies. Nothing is deleted,
because a withheld row is still the best lead a human has for that record.

The rule lives in `locfinder/places/name_match.py` with its own tests and the measurement behind
it. Two things in there are counter-intuitive enough to be worth reading before changing this
script: 0.00 agreement is **two different facts**, and a Jaccard threshold is the **wrong knob** --
the obvious floor of 0.34 would reject `Walmart Grocery Pickup and Delivery` against an OSM
`Walmart Supercenter` at 0.0 m.

**Known limits, so a reader does not over-trust a filled cell.**

* OSM's coverage of small independent grocers is patchy, so `no match` means "OSM is silent", not
  "not a supermarket". Those records stay unclassified and are exactly what the Yelp pass is for.
* `shop=convenience` on a large independent is a common OSM under-tag. A convenience proposal is
  weaker evidence than a supermarket one and the sheet says so.
* An OSM feature can be stale in the same way an Overture record can.

**The Yelp half, and what it needs from the owner.** The Yelp Fusion API is free at low volume but
requires an API key tied to an account. Creating that account is the owner's to do, not a
session's. Once a key exists, the useful fields are the business categories, the price tier and
whether it is marked closed — enough to separate a weekly-shop supermarket from a corner shop where
OSM is silent. Until then this script's `no match` rows are the backlog.

Run from `v2/`:
    python scripts/prefill_from_osm.py --category grocery
    python scripts/prefill_from_osm.py --category pharmacy --out ../docs/experiments/audit/pharmacy-prefill.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

import geopandas as gpd

V2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V2 / "spikes"))
sys.path.insert(0, str(V2))

from _common import ACCEPTED_PLACES, GRID  # noqa: E402
from locfinder.places.categories import select_target  # noqa: E402

# `name_agreement` and `tokens` used to be defined here and are imported from here by
# `measure_fsq_accuracy`, `measure_fsq_coverage`, `crosscheck_fsq_closures` and
# `shortlist_fsq_pharmacy`. They now live in the library, with the floor and the measurement that
# set it. Re-exported under the old names so those four keep working unchanged; a test asserts
# these are the same objects.
from locfinder.places.name_match import (  # noqa: E402,F401
    agreement_used,
    clears_the_floor,
    match_verdict,
    name_agreement,
    tokens,
    why_withheld,
)

OSM_POIS = V2 / "data" / "triangle" / "osm_pois.parquet"
AUDIT = V2.parent / "docs" / "experiments" / "audit"

#: OSM tag -> what it proposes, per wedge category. Anything not listed proposes nothing.
PROPOSALS: dict[str, dict[tuple[str, str], str]] = {
    "grocery": {
        ("shop", "supermarket"): "supermarket",
        ("shop", "wholesale"): "supermarket",
        ("shop", "convenience"): "convenience (not a weekly shop)",
        ("shop", "greengrocer"): "specialty",
        ("shop", "deli"): "specialty",
        ("shop", "butcher"): "specialty",
        ("shop", "bakery"): "specialty",
        ("shop", "health_food"): "specialty",
        ("shop", "farm"): "specialty",
        ("shop", "department_store"): "supermarket",
    },
    "pharmacy": {
        ("amenity", "pharmacy"): "pharmacy",
        ("healthcare", "pharmacy"): "pharmacy",
        ("shop", "chemist"): "chemist (not a dispensing pharmacy)",
        ("amenity", "hospital"): "not a retail pharmacy",
        ("amenity", "doctors"): "not a retail pharmacy",
        ("amenity", "clinic"): "not a retail pharmacy",
    },
}

def proposal_text(proposal: str, tag: tuple[str, str]) -> str:
    """The proposal with its caveat, or the empty string.

    **A WARNING IS NOT A PROPOSAL.** The caveat used to be concatenated unconditionally, so a
    pharmacy record matched to an OSM `shop=convenience` -- a tag with no pharmacy mapping at all
    -- produced a non-empty cell containing nothing but the warning. Twelve pharmacy rows had that
    shape and the first version of
    `docs/engineering-notes/project-phase1-s3-osm-name-floor.md` counted all twelve as proposals,
    reporting 102/29 (28.4%) where the real figures are 90/17 (18.9%). Found by the adversarial
    review of 2026-11-18, finding 5.
    """
    if not proposal:
        return ""
    if tag == ("shop", "convenience"):
        return proposal + " (weak: OSM under-tags large independents as convenience)"
    return proposal


def place_name(rec) -> str:
    try:
        return str(dict(rec.get("names")).get("primary") or "")
    except Exception:
        return ""


def osm_name(row) -> str:
    v = row.get("name")
    return "" if v is None or str(v) == "nan" else str(v)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--category", default="grocery")
    ap.add_argument("--radius", type=float, default=120.0)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--only-unclassified", action="store_true",
                    help="grocery only: skip records `places.grocery` already classifies")
    args = ap.parse_args()
    out = (args.out or (AUDIT / f"{args.category}-prefill-from-osm.csv")).resolve()

    places = gpd.read_parquet(ACCEPTED_PLACES).to_crs(GRID.crs)
    sel = select_target(places, args.category)
    if args.only_unclassified:
        from locfinder.places.grocery import classify_grocery
        sel = sel[[classify_grocery(r) == "unclassified" for _, r in sel.iterrows()]]

    osm = gpd.read_parquet(OSM_POIS).to_crs(GRID.crs)
    tag_cols = [c for c in ("shop", "amenity", "healthcare", "leisure") if c in osm.columns]
    feats = osm[osm[tag_cols].notna().any(axis=1)]
    sidx = feats.sindex
    table = PROPOSALS.get(args.category, {})

    rows, proposed, nomatch = [], 0, 0
    # Every gate reports how often it was REACHED, not only what it caught. A gate that is never
    # reached prints a blank that reads as a clean result; that mistake is ledger instance 47.
    reached: Counter[str] = Counter()
    withheld: Counter[str] = Counter()
    for _, rec in sel.iterrows():
        pname = place_name(rec)
        hits = list(sidx.query(rec.geometry.buffer(args.radius), predicate="intersects"))
        best, best_score = None, -1.0
        for h in hits:
            f = feats.iloc[h]
            dist = float(rec.geometry.distance(f.geometry))
            agree = agreement_used(pname, osm_name(f))
            # Name agreement dominates: a strong name match further away beats a tag collision
            # next door, which is the common failure in a strip mall.
            score = agree * 2.0 + max(0.0, 1.0 - dist / args.radius)
            if score > best_score:
                best, best_score, best_dist, best_agree = f, score, dist, agree
        if best is None:
            nomatch += 1
            rows.append({"id": rec.get("id"), "name": pname, "osm_name": "", "osm_tag": "",
                         "distance_m": "", "name_agreement": "", "proposal": "",
                         "withheld_proposal": "", "match": "no feature",
                         "evidence": "no OSM feature within "
                                     f"{args.radius:.0f} m -- OSM is silent, not negative",
                         "verdict": "", "notes": ""})
            continue
        tag = next(((c, str(best[c])) for c in tag_cols
                    if best.get(c) is not None and str(best.get(c)) != "nan"), ("", ""))
        proposal = table.get(tag, "")

        # THE FLOOR. A proposal is worth what its match is worth, so a tag read off a feature
        # carrying a different business's name proposes nothing. The text is kept in
        # `withheld_proposal` rather than dropped: the row is still the best lead for that record.
        verdict = match_verdict(pname, osm_name(best))
        reached[verdict] += 1
        kept = proposal and clears_the_floor(verdict)
        if kept:
            proposed += 1
        elif proposal:
            withheld[verdict] += 1

        text = proposal_text(proposal, tag)
        rows.append({
            "id": rec.get("id"), "name": pname, "osm_name": osm_name(best),
            "osm_tag": f"{tag[0]}={tag[1]}" if tag[0] else "",
            "distance_m": f"{best_dist:.1f}", "name_agreement": f"{best_agree:.2f}",
            "proposal": text if kept else "",
            "withheld_proposal": "" if kept else text,
            "match": verdict,
            "evidence": why_withheld(verdict),
            "verdict": "", "notes": "",
        })

    rows.sort(key=lambda r: (r["proposal"] == "", -float(r["name_agreement"] or 0)))
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    exact = sum(1 for r in rows if r["proposal"] and float(r["name_agreement"] or 0) == 1.0)
    print(f"{args.category}: {len(sel):,} records considered")
    print(f"  {proposed:>5} got a proposal from an OSM tag whose name AGREES")
    print(f"  {exact:>5} of those agree exactly -- the ones worth taking first")
    print(f"  {nomatch:>5} have no OSM feature within {args.radius:.0f} m -- the Yelp backlog")
    print("  the floor, by how often each verdict was reached:")
    for v in ("agrees", "differs", "unverified"):
        if reached[v] == 0:
            print(f"    [gate] {v:>10}: NEVER REACHED (0 opportunities) -- "
                  "a blank here would otherwise read as a clean result")
        else:
            print(f"    [gate] {v:>10}: reached {reached[v]:>4}, "
                  f"withheld {withheld[v]:>4} proposal(s)")
    total_withheld = sum(withheld.values())
    print(f"  {total_withheld:>5} proposals WITHHELD by the floor "
          f"({total_withheld / (total_withheld + proposed) * 100:.1f}% of what would have been "
          "proposed before 2026-11-18)")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
