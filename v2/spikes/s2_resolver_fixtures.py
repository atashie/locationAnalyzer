"""Phase 1 S2.1: run the resolver against the REAL metro index on the measured failure cases.

The ten queries below are verbatim from `docs/experiments/geocoding.md`'s benchmark, where the
Census geocoder resolved **none** of them and unbounded Nominatim returned "UNC Hospitals" in
Morganton (180 km away) and "Southpoint" in Wisconsin.

Unit tests cover the resolver over a nine-row synthetic index. That is not the same as running it
over 90,000 real places, and the `expansion.py` lesson was exactly that gap — a module certified by
fixtures that had never met a real payload. So this builds the index from
`overture_places_accepted.parquet` plus `osm_pois.parquet`, bounded by the metro's **routing** bbox,
and prints what a household would actually be shown.

There is no pass/fail here. A resolver's job on an ambiguous query is to *be* ambiguous, so the
output is the candidate list and the outcome, for reading.

Run from v2/:  uv run python spikes/s2_resolver_fixtures.py
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import geopandas as gpd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ACCEPTED_PLACES, METRO, METRO_DIR, append_results, stamp  # noqa: E402
from locfinder.places.resolve import build_metro_index  # noqa: E402

#: Verbatim from the geocoding benchmark's "Ambiguous and POI-style queries" table.
FIXTURES = [
    "Whole Foods, Chapel Hill NC",
    "Whole Foods Durham",
    "Harris Teeter Carrboro",
    "UNC Hospitals",
    "Duke Hospital",
    "RTP",
    "Fidelity Investments Durham NC",
    "Southpoint",
    "Carrboro Farmers Market",
    "Weaver Street Market",
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=4, help="candidates to show per query")
    args = ap.parse_args()

    t = time.perf_counter()
    ovt = gpd.read_parquet(ACCEPTED_PLACES)
    osm_path = METRO_DIR / "osm_pois.parquet"
    osm = gpd.read_parquet(osm_path) if osm_path.exists() else None
    load_s = time.perf_counter() - t

    t = time.perf_counter()
    idx = build_metro_index(ovt, osm, bbox=METRO.routing)
    build_s = time.perf_counter() - t
    print(f"index: {len(idx):,} places from {len(ovt):,} Overture + "
          f"{0 if osm is None else len(osm):,} OSM rows, bounded by the {METRO.name} ROUTING bbox "
          f"({load_s:.1f} s to read, {build_s:.1f} s to index); "
          f"{len(idx.localities):,} distinct localities", flush=True)

    rows = []
    for q in FIXTURES:
        t = time.perf_counter()
        r = idx.resolve(q, limit=args.limit)
        ms = (time.perf_counter() - t) * 1000.0
        top = r.candidates[0] if r.candidates else None
        rows.append({
            "query": q, "outcome": r.outcome, "ms": round(ms, 1),
            "n_candidates": len(r.candidates),
            "candidates": [
                {"name": c.place.name, "locality": c.place.locality, "source": c.place.source,
                 "source_id": c.place.source_id, "score": c.score, "matched_on": c.matched_on,
                 "corroborated_by": list(c.corroborated_by), "licence": c.place.licence,
                 "lonlat": [round(c.place.lon, 6), round(c.place.lat, 6)]}
                for c in r.candidates],
        })
        print(f"\n{q!r} -> {r.outcome} ({ms:.1f} ms, {len(r.candidates)} candidates)", flush=True)
        for c in r.candidates:
            corr = f" +{','.join(c.corroborated_by)}" if c.corroborated_by else ""
            print(f"    {c.score:.3f}  {c.place.name}  [{c.place.locality or '-'}]  "
                  f"{c.place.source}{corr}  {c.matched_on}", flush=True)

    resolved = sum(1 for r in rows if r["outcome"] == "resolved")
    ambiguous = sum(1 for r in rows if r["outcome"] == "ambiguous")
    missing = sum(1 for r in rows if r["outcome"] == "not_found")
    answered = resolved + ambiguous
    med_ms = sorted(r["ms"] for r in rows)[len(rows) // 2]
    print(f"\n{answered}/{len(rows)} produced candidates "
          f"({resolved} single, {ambiguous} ambiguous, {missing} not found); "
          f"median {med_ms:.1f} ms", flush=True)

    out = {"metro": METRO.name, "index_size": len(idx), "localities": len(idx.localities),
           "load_s": load_s, "build_s": build_s, "results": rows}
    (METRO_DIR.parent / f"s2_resolver_fixtures_{METRO.name}.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")

    lines = [
        f"### S2.1 place-name resolver on the real metro index ({stamp()})", "",
        f"Index: **{len(idx):,} places** from {len(ovt):,} Overture accepted rows + "
        f"{0 if osm is None else len(osm):,} OSM POIs, bounded by the **{METRO.name} routing "
        f"bbox** — not the evaluation bbox, because a workplace can legitimately sit outside the "
        f"area we grid. {len(idx.localities):,} distinct localities. Built in {build_s:.1f} s; "
        f"median query **{med_ms:.1f} ms**.", "",
        "The ten queries are verbatim from `geocoding.md`, where **Census resolved none of them** "
        "and unbounded Nominatim answered two of them with places in other states.", "",
        f"**{answered} of {len(rows)} produce candidates** — {resolved} a single confident answer, "
        f"{ambiguous} ambiguous (a chooser), {missing} not found. Ambiguity is the correct outcome "
        "for a brand with several shops; being decisive there is exactly the Morganton failure.", "",
        "| query | outcome | top candidate | locality | source | matched on |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        c = r["candidates"][0] if r["candidates"] else None
        if c is None:
            lines.append(f"| `{r['query']}` | **{r['outcome']}** | — | — | — | — |")
            continue
        corr = f" +{','.join(c['corroborated_by'])}" if c["corroborated_by"] else ""
        lines.append(
            f"| `{r['query']}` | **{r['outcome']}** | {c['name']} | {c['locality'] or '—'} | "
            f"{c['source']}{corr} | `{c['matched_on']}` |")
    lines += ["", "Full candidate lists, scores, source-native ids and licences are in "
              f"`v2/data/s2_resolver_fixtures_{METRO.name}.json`.", ""]
    append_results("geocoding.md", "\n".join(lines))


if __name__ == "__main__":
    main()
