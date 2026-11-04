"""Phase 1 S2.1: are the resolver's confident answers the RIGHT places?

`s2_resolver_fixtures.py` reports "10/10 produce candidates, 7 single". That measures **confidence,
not correctness**, and the two are easy to confuse — "Southpoint" resolves to something named
exactly "Southpoint" with a score of 1.000, which says nothing about whether it is the shopping
mall a household means rather than a neighbourhood, a business park or a bus stop.

This checks the answers against independent reference coordinates. The references are the hand-chosen
spot-check points in `spotcheck_engines.PLACES`, which are not POI centroids, so the test is
deliberately coarse: **is the resolved answer the same place, or somewhere else entirely?** A few
hundred metres is agreement; kilometres is not.

For the queries with no reference coordinate, the category and locality are printed for reading. A
resolver cannot be graded on a query whose right answer was never written down.

Run from v2/:  uv run python spikes/s2_resolver_correctness.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import geopandas as gpd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ACCEPTED_PLACES, METRO, METRO_DIR, append_results, stamp  # noqa: E402
from locfinder.places.resolve import build_metro_index, is_subsidiary_feature  # noqa: E402
from s2_resolver_fixtures import FIXTURES  # noqa: E402
from spotcheck_engines import PLACES  # noqa: E402

#: query -> the independent reference point it should land near, from the spot-check set.
#: Only queries whose intended answer was written down beforehand can be graded.
REFERENCE = {
    "UNC Hospitals": "UNC Hospitals",
    "Duke Hospital": "Duke University Hospital",
    "Southpoint": "Southpoint Mall",
    "Carrboro Farmers Market": "Carrboro Town Hall",      # ~200 m apart in reality
    "RTP": "RTP (Kit Creek Rd)",
}
#: Metres. Generous, because the references are not POI centroids: this separates "same place" from
#: "somewhere else", not "accurate" from "inaccurate".
SAME_PLACE_M = 800.0


def metres(lon1, lat1, lon2, lat2) -> float:
    lat = math.radians((lat1 + lat2) / 2.0)
    return math.hypot((lon1 - lon2) * 111_320.0 * math.cos(lat), (lat1 - lat2) * 110_540.0)


def main() -> None:
    ovt = gpd.read_parquet(ACCEPTED_PLACES)
    osm_path = METRO_DIR / "osm_pois.parquet"
    osm = gpd.read_parquet(osm_path) if osm_path.exists() else None
    idx = build_metro_index(ovt, osm, bbox=METRO.routing)

    rows = []
    for q in FIXTURES:
        r = idx.resolve(q, limit=4)
        top = r.candidates[0] if r.candidates else None
        ref_name = REFERENCE.get(q)
        verdict, dist = "ungraded", None
        if top is not None and ref_name:
            rlat, rlon = PLACES[ref_name]
            dist = metres(top.place.lon, top.place.lat, rlon, rlat)
            if r.outcome == "ambiguous":
                # Ambiguity is a legitimate answer; grade whether the RIGHT place is offered at all.
                near = [c for c in r.candidates
                        if metres(c.place.lon, c.place.lat, rlon, rlat) <= SAME_PLACE_M
                        and not is_subsidiary_feature(c.place)]
                verdict = "right place offered" if near else "right place NOT offered"
            elif is_subsidiary_feature(top.place):
                # Distance alone is the wrong criterion, which Codex pass-10 H1 pointed out about my
                # own grading: "Duke Hospital" resolves to a bus platform 56 m from the hospital, so
                # a distance test calls it correct while the entity is wrong.
                verdict = "WRONG ENTITY (a stop or subsidiary feature, not the place)"
            else:
                verdict = "correct" if dist <= SAME_PLACE_M else "WRONG PLACE"
        rows.append({
            "query": q, "outcome": r.outcome,
            "top": None if top is None else top.place.name,
            "locality": None if top is None else top.place.locality,
            "category": None if top is None else top.place.category,
            "source": None if top is None else top.place.source,
            "reference": ref_name, "distance_m": None if dist is None else round(dist, 1),
            "verdict": verdict,
        })
        d = "" if dist is None else f"  {dist:7.0f} m from {ref_name}"
        print(f"{q!r:<34} {r.outcome:<10} {str(rows[-1]['top'])[:38]:<38} "
              f"[{rows[-1]['category'] or '-'}]{d}  -> {verdict}", flush=True)

    graded = [r for r in rows if r["verdict"] != "ungraded"]
    correct = [r for r in graded if r["verdict"] in ("correct", "right place offered")]
    # Also report, for every resolved answer, whether the chosen feature type is one that merely
    # *refers* to a place. A confident answer on a platform or an ATM is not an anchor.
    refs = [r for r in rows if r["verdict"].startswith("WRONG ENTITY")]
    print(f"\ngraded {len(graded)} of {len(rows)} (only queries with a written-down intended "
          f"answer can be graded); {len(correct)} correct", flush=True)
    for r in graded:
        if r["verdict"] not in ("correct", "right place offered"):
            print(f"  FAILED: {r['query']!r} -> {r['top']!r} at {r['distance_m']} m", flush=True)

    (METRO_DIR.parent / f"s2_resolver_correctness_{METRO.name}.json").write_text(
        json.dumps({"same_place_m": SAME_PLACE_M, "rows": rows}, indent=1), encoding="utf-8")

    lines = [
        f"### S2.1 correctness, not confidence ({stamp()})", "",
        "`s2_resolver_fixtures.py` reports 10/10 candidates and 7 single answers. That measures "
        "**confidence**. This checks the answers against the independent spot-check reference "
        f"points, with a deliberately coarse {SAME_PLACE_M:.0f} m threshold — the references are "
        "not POI centroids, so this separates *same place* from *somewhere else entirely*.", "",
        "| query | outcome | top candidate | category | distance from reference | verdict |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        dm = "—" if r["distance_m"] is None else f"{r['distance_m']:.0f} m"
        lines.append(f"| `{r['query']}` | {r['outcome']} | {r['top'] or '—'} | "
                     f"{r['category'] or '—'} | {dm} | **{r['verdict']}** |")
    lines += [
        "", f"**{len(correct)} of {len(graded)} graded queries land on the right place**, and "
        f"{len(refs)} resolve confidently onto a feature that merely *refers* to a place (a stop, "
        "a platform, an ATM) rather than the place itself — a distance test calls those correct, "
        "which is why identity is checked separately. Only "
        "queries whose intended answer was written down beforehand can be graded; the rest are "
        "printed for reading rather than scored, because a resolver cannot be marked against an "
        "answer nobody recorded. For an *ambiguous* outcome the grading asks whether the right "
        "place is **offered** at all, since ambiguity is a legitimate answer and a chooser the "
        "household resolves.", "",
    ]
    append_results("geocoding.md", "\n".join(lines))


if __name__ == "__main__":
    main()
