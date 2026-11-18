"""Where OSM and Foursquare both speak, do they agree -- and is the agreement independent?

**Owner decision 2026-11-18:** *"proceed with 1-3"*, of which this is the first: the measurement
`project-phase1-s3-fsq-coverage.md` named as "the right next measurement if anyone wants to trust
FSQ further".

**What the coverage run measured, and what it could not.** `measure_fsq_coverage.py` asked whether
FSQ holds anything for the 334 records where OSM is silent. It does, for 321. But a source that
fills gaps is not thereby a source that is *right*, and nothing in that run compared FSQ against a
second opinion, because by construction there was none. This run inverts the selection: the records
OSM **did** reach, where both sources propose a class for the same record and can be put side by
side.

**The prediction this is built to test, which is the real reason to run it.** Foursquare
contributes to Overture and our places are Overture-derived, so FSQ agreeing with our record can be
FSQ agreeing with *itself* -- recorded in `785e76a` after `KBI Biopharma`, a contract biologics
manufacturer, came back from FSQ as `Retail > Pharmacy` at 0.0 m with name agreement 1.00. If that
shared lineage is substantial then two things follow, and both are checkable here:

1. A large share of matches sit at **essentially zero distance**. Two independently surveyed
   datasets do not place the same storefront at the same coordinates to the centimetre; a shared
   upstream record does. This run reports the distance-zero share outright.
2. Agreement is **higher** where the Overture record carries a `brand`, because those are the
   chains every source has, and disagreement concentrates in the brandless records -- which are
   exactly the 323 the grocery rule is still waiting on.

A high agreement rate is therefore **not** automatically good news, and this script refuses to
print one without the two figures that say whether it means anything.

**Every gate reports how many times it was REACHED, not only what it found.** The coverage run's
grocery contradiction check printed nothing, and "nothing" was read as "no contradictions" when it
actually meant FSQ had made zero negative grocery proposals -- the gate never fired. That lesson is
in `feedback-a-predeclared-gate-must-be-shown-reachable.md`, and it is enforced here rather than
remembered: a diagnostic that was never exercised says so in its own line.

**What it does not do.** It edits no table. The sheet carries a blank `verdict` column. Neither
source is treated as ground truth -- this measures AGREEMENT, and where they differ the script says
which way without ruling.

Run from `v2/`:
    python scripts/measure_fsq_accuracy.py --category grocery
    python scripts/measure_fsq_accuracy.py --category pharmacy
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import geopandas as gpd

V2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V2 / "spikes"))
sys.path.insert(0, str(V2))
sys.path.insert(0, str(V2 / "scripts"))

from _common import ACCEPTED_PLACES, GRID  # noqa: E402
from locfinder.places.categories import select_target  # noqa: E402
from locfinder.places.grocery import _brand_name  # noqa: E402
from measure_fsq_coverage import (  # noqa: E402
    AGREE,
    FSQ_RELEASE,
    PROPOSALS as FSQ_PROPOSALS,
    labels_of,
    load_fsq,
    propose as fsq_propose,
)
from prefill_from_osm import (  # noqa: E402
    OSM_POIS,
    PROPOSALS as OSM_PROPOSALS,
    name_agreement,
    osm_name,
    place_name,
)

AUDIT = V2.parent / "docs" / "experiments" / "audit"

#: Proposal text -> comparable class. The two source tables were written for their own sources and
#: word things differently, so a string comparison would manufacture disagreement. Matched by
#: longest prefix, because the OSM pass appends a "(weak: ...)" rider to its convenience proposal.
CLASSES: dict[str, str] = {
    # grocery
    "supermarket": "supermarket",
    "grocery store": "grocery-unspecified",
    "convenience": "convenience",
    "specialty": "specialty",
    "market (unspecific": "unspecific",
    "food retail (unspecific": "unspecific",
    "not a grocery": "not-a-grocery",
    # pharmacy
    "pharmacy": "pharmacy",
    "drugstore": "drugstore",
    "chemist": "drugstore",
    "not a retail pharmacy": "not-a-pharmacy",
    "health (unspecific": "unspecific",
}

#: Classes that say "this is not the thing at all". A proposal of one of these against a positive
#: proposal from the other source is a CONTRADICTION, not a difference of resolution.
NEGATIVE = {"not-a-grocery", "not-a-pharmacy"}

#: Classes that are a coarser view of another rather than a rival claim. `grocery-unspecified` is
#: the measured case: FSQ's `Grocery Store` label lands on Harris Teeter, Food Lion and Kroger, so
#: it cannot be read as "smaller than a supermarket" and it does not contradict `supermarket`.
COARSER: dict[str, set[str]] = {
    "unspecific": {"supermarket", "convenience", "specialty", "grocery-unspecified",
                   "pharmacy", "drugstore"},
    "grocery-unspecified": {"supermarket", "convenience", "specialty"},
    "drugstore": {"pharmacy"},
}

#: Two records this close cannot have been surveyed independently.
COINCIDENT_M = 0.5


def classify(proposal: str) -> str:
    """The comparable class of a proposal, or "" when the source proposed nothing."""
    if not proposal:
        return ""
    best = ""
    for prefix in CLASSES:
        if proposal.startswith(prefix) and len(prefix) > len(best):
            best = prefix
    return CLASSES[best] if best else "unmapped"


def compare(osm_class: str, fsq_class: str) -> str:
    """How the two proposals relate. Neither source is ground truth, so this never says who wins."""
    if osm_class == fsq_class:
        return "same"
    if osm_class in NEGATIVE or fsq_class in NEGATIVE:
        return "contradiction"
    if fsq_class in COARSER.get(osm_class, set()) or osm_class in COARSER.get(fsq_class, set()):
        return "coarser"
    return "differ"


def best_osm(rec, feats, sidx, tag_cols, radius):
    """The OSM feature the prefill pass would pick, by the same score."""
    pname = place_name(rec)
    hits = list(sidx.query(rec.geometry.buffer(radius), predicate="intersects"))
    best, best_score, best_dist, best_agree = None, -1.0, 0.0, 0.0
    for h in hits:
        feat = feats.iloc[h]
        dist = float(rec.geometry.distance(feat.geometry))
        agree = name_agreement(pname, osm_name(feat))
        score = agree * 2.0 + max(0.0, 1.0 - dist / radius)
        if score > best_score:
            best, best_score, best_dist, best_agree = feat, score, dist, agree
    return best, best_dist, best_agree


def best_fsq(rec, fsq, fsq_sidx, radius):
    """The FSQ place the coverage pass would pick, by the same score."""
    pname = place_name(rec)
    hits = list(fsq_sidx.query(rec.geometry.buffer(radius), predicate="intersects"))
    best, best_score, best_dist, best_agree = None, -1.0, 0.0, 0.0
    for h in hits:
        cand = fsq.iloc[h]
        dist = float(rec.geometry.distance(cand.geometry))
        agree = name_agreement(pname, str(cand.get("name") or ""))
        score = agree * 2.0 + max(0.0, 1.0 - dist / radius)
        if score > best_score:
            best, best_score, best_dist, best_agree = cand, score, dist, agree
    return best, best_dist, best_agree


def brand_of(rec) -> str:
    """The Overture brand, read through `places.grocery`'s own accessor rather than a second
    guess at the nested shape -- a divergence here would silently mis-stratify the brand split."""
    return _brand_name(rec) or ""


def gate(name: str, reached: int, found: int, detail: str = "") -> None:
    """Report a diagnostic's REACH as well as its result, so silence is never ambiguous."""
    if reached == 0:
        print(f"  [gate] {name}: NEVER REACHED (0 opportunities). This says nothing about the "
              f"data; it says the check could not run.")
        return
    print(f"  [gate] {name}: reached {reached}, found {found}"
          f"{(' -- ' + detail) if detail else ''}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--category", default="grocery")
    ap.add_argument("--radius", type=float, default=120.0)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument(
        "--snapshot",
        type=Path,
        default=V2 / "data" / "triangle" / f"fsq_os_places_{FSQ_RELEASE}.parquet",
    )
    args = ap.parse_args()
    out = (args.out or (AUDIT / f"{args.category}-fsq-accuracy.csv")).resolve()
    osm_table = OSM_PROPOSALS.get(args.category, {})
    fsq_table = FSQ_PROPOSALS.get(args.category, {})

    # ------------------------------------------------------- the records OSM DID reach, this time
    places = gpd.read_parquet(ACCEPTED_PLACES).to_crs(GRID.crs)
    sel = select_target(places, args.category)
    osm = gpd.read_parquet(OSM_POIS).to_crs(GRID.crs)
    tag_cols = [c for c in ("shop", "amenity", "healthcare", "leisure") if c in osm.columns]
    feats = osm[osm[tag_cols].notna().any(axis=1)]
    osm_sidx = feats.sindex

    reached = [
        rec for _, rec in sel.iterrows()
        if list(osm_sidx.query(rec.geometry.buffer(args.radius), predicate="intersects"))
    ]
    print(f"{args.category}: {len(sel)} considered, {len(reached)} WITH an OSM feature within "
          f"{args.radius:.0f} m -- the inverse of the coverage run's selection")
    if not reached:
        print("nothing to measure")
        return

    wgs = gpd.GeoSeries([r.geometry for r in reached], crs=GRID.crs).to_crs(4326)
    minx, miny, maxx, maxy = wgs.total_bounds
    pad = 0.05
    fsq = load_fsq(args.snapshot, (minx - pad, miny - pad, maxx + pad, maxy + pad))
    print(f"FSQ snapshot {FSQ_RELEASE}: {len(fsq):,} places in the bbox")
    fsq_sidx = fsq.sindex

    rows: list[dict] = []
    for rec in reached:
        pname = place_name(rec)
        o, o_dist, o_agree = best_osm(rec, feats, osm_sidx, tag_cols, args.radius)
        f, f_dist, f_agree = best_fsq(rec, fsq, fsq_sidx, args.radius)

        o_tag = ("", "")
        o_proposal = ""
        if o is not None:
            o_tag = next(((c, str(o[c])) for c in tag_cols
                          if o.get(c) is not None and str(o.get(c)) != "nan"), ("", ""))
            o_proposal = osm_table.get(o_tag, "")

        f_proposal, f_label = "", ""
        f_closed = ""
        if f is not None:
            f_proposal, f_label = fsq_propose(labels_of(f), fsq_table)
            raw = f.get("date_closed")
            f_closed = "" if raw is None or str(raw) == "nan" else str(raw)

        o_class, f_class = classify(o_proposal), classify(f_proposal)
        verdict = compare(o_class, f_class) if (o_class and f_class) else ""

        rows.append({
            "id": rec.get("id"), "name": pname, "brand": brand_of(rec),
            "osm_name": osm_name(o) if o is not None else "",
            "osm_tag": f"{o_tag[0]}={o_tag[1]}" if o_tag[0] else "",
            "osm_distance_m": f"{o_dist:.1f}" if o is not None else "",
            "osm_agreement": f"{o_agree:.2f}" if o is not None else "",
            "osm_proposal": o_proposal, "osm_class": o_class,
            "fsq_name": str(f.get("name") or "") if f is not None else "",
            "fsq_category": f_label,
            "fsq_distance_m": f"{f_dist:.1f}" if f is not None else "",
            "fsq_agreement": f"{f_agree:.2f}" if f is not None else "",
            "fsq_proposal": f_proposal, "fsq_class": f_class,
            "comparison": verdict,
            "fsq_date_closed": f_closed,
            "verdict": "", "notes": "",
        })

    # -------------------------------------------------------------------------------- the report
    both = [r for r in rows if r["comparison"]]
    counts = {k: sum(1 for r in both if r["comparison"] == k)
              for k in ("same", "coarser", "differ", "contradiction")}
    agreeing = counts["same"] + counts["coarser"]

    print(f"\n{args.category}: of {len(reached)} records OSM reached,")
    print(f"  {sum(1 for r in rows if r['osm_proposal']):5} got a proposal from OSM")
    print(f"  {sum(1 for r in rows if r['fsq_proposal']):5} got a proposal from FSQ")
    print(f"  {len(both):5} got one from BOTH  <- the only comparable set")
    if not both:
        print("\n  Nothing is comparable, so no agreement rate is reportable.")
        return
    print(f"\n  same class            {counts['same']:5}")
    print(f"  compatible, coarser   {counts['coarser']:5}")
    print(f"  differ                {counts['differ']:5}")
    print(f"  CONTRADICT            {counts['contradiction']:5}")
    print(f"  -> {agreeing}/{len(both)} = {100 * agreeing / len(both):.1f}% agree or are "
          f"compatible")

    # ---------------------------------------------- is that agreement independent? the two checks
    print("\n  IS THE AGREEMENT INDEPENDENT? The number above means nothing without these.")
    coincident = [r for r in both if float(r["fsq_distance_m"] or 999) < COINCIDENT_M]
    pct = 100 * len(coincident) / len(both)
    print(f"  {len(coincident)}/{len(both)} = {pct:.1f}% of FSQ matches sit within "
          f"{COINCIDENT_M} m of our record.")
    print("     Independently surveyed datasets do not place a storefront at the same point to "
          "the centimetre.\n     A high share here is the signature of a SHARED UPSTREAM RECORD, "
          "not of corroboration.")

    branded = [r for r in both if r["brand"]]
    brandless = [r for r in both if not r["brand"]]
    for label, group in (("with an Overture brand", branded), ("brandless", brandless)):
        if not group:
            print(f"  {label}: none in the comparable set")
            continue
        ok = sum(1 for r in group if r["comparison"] in ("same", "coarser"))
        print(f"  {label}: {ok}/{len(group)} = {100 * ok / len(group):.1f}% agree")
    if branded and brandless:
        b_rate = sum(1 for r in branded if r["comparison"] in ("same", "coarser")) / len(branded)
        n_rate = sum(1 for r in brandless if r["comparison"] in ("same", "coarser")) / len(brandless)
        gap = 100 * (b_rate - n_rate)
        print(f"     gap = {gap:+.1f} points. The prediction was that branded records agree MORE, "
              f"because\n     those are the chains every source holds; a large positive gap "
              f"supports the echo reading.")

    # ------------------------------------------------------------------- gates, with their reach
    print("\n  DIAGNOSTIC GATES (reach reported, so silence is never read as a clean result):")
    neg_fsq = [r for r in both if r["fsq_class"] in NEGATIVE]
    neg_osm = [r for r in both if r["osm_class"] in NEGATIVE]
    gate("FSQ denies what OSM proposes", len(neg_fsq),
         sum(1 for r in neg_fsq if r["comparison"] == "contradiction"),
         "this is the half the coverage run could not exercise for grocery")
    gate("OSM denies what FSQ proposes", len(neg_osm),
         sum(1 for r in neg_osm if r["comparison"] == "contradiction"))
    closed_rows = [r for r in rows if r["fsq_date_closed"]]
    gate("FSQ marks a record OSM still tags as trading", len(closed_rows),
         sum(1 for r in closed_rows if r["osm_proposal"]),
         "a storefront OSM carries a live tag for, that FSQ dates as closed")

    if counts["contradiction"]:
        print("\n  The contradictions, which are the rows worth a human eye:")
        for r in [r for r in both if r["comparison"] == "contradiction"][:12]:
            print(f"    {(r['name'] or '')[:30]:30s} OSM {r['osm_class']:20s} "
                  f"FSQ {r['fsq_class']}")

    rows.sort(key=lambda r: ({"contradiction": 0, "differ": 1, "coarser": 2, "same": 3,
                              "": 4}[r["comparison"]], r["name"] or ""))
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nwrote {out}")
    print("No table edited. The `verdict` column is blank.")


if __name__ == "__main__":
    main()
