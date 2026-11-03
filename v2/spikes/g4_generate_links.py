"""Gate G4: generate 20 two-anchor regions and the portal deep links to test by hand.

Metro-aware: anchors are asserted inside the active metro's evaluation bbox before anything is
generated, and outputs carry the metro name.

For each region: two anchors (named Triangle workplaces or random slice points), each a
25-minute AUTO arrival isochrone from self-hosted Valhalla; region = intersection; bbox =
region envelope; leakage = bbox area / region area. Links are GENERATED ONLY, never fetched.
Writes docs/experiments/g4-listings.md with a device checklist the owner fills in, and
v2/data/g4_regions.geojson for the prototypes.

Run from v2/ with Valhalla serving:  uv run python spikes/g4_generate_links.py
"""
from __future__ import annotations

import json
import random
import statistics
import sys
from pathlib import Path

import geopandas as gpd
import httpx
from shapely.geometry import shape
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import DATA, GRID, METRO, RESULTS, VALHALLA, stamp  # noqa: E402
from locfinder.listings.links import BBox, leakage_ratio, realtor_url, redfin_url, trulia_url, zillow_url  # noqa: E402

NAMED = {
    "UNC Hospitals": (35.9049, -79.0469), "Duke University Hospital": (36.0075, -78.9381),
    "RTP (Kit Creek Rd)": (35.8720, -78.8450), "Downtown Durham": (35.9960, -78.9010),
    "Carrboro Town Hall": (35.9100, -79.0750), "Cary Downtown": (35.7880, -78.7810),
    "RDU Terminal 2": (35.8776, -78.7875), "Southpoint Mall": (35.9050, -78.9450),
    "NC State Bell Tower": (35.7860, -78.6630), "Hillsborough": (36.0750, -79.0990),
}
MINUTES = 25


def assert_in_metro() -> None:
    """Anchors must lie inside the metro's evaluation bbox. Six of the original twenty regions were
    invalid because two anchors sat south of the Phase 0 extract edge (Codex pass 4 H7)."""
    bad = [n for n, (lat, lon) in NAMED.items() if not METRO.evaluation.contains(lat, lon)]
    if bad:
        raise SystemExit(f"anchors outside the {METRO.name} evaluation bbox: {bad}")


def arrival_polygon(lat, lon, minutes=MINUTES, costing="auto"):
    body = {"locations": [{"lat": lat, "lon": lon}], "costing": costing, "contours": [{"time": minutes}],
            "polygons": True, "reverse": True, "denoise": 0.3, "generalize": 50}
    r = httpx.post(f"{VALHALLA}/isochrone", json=body, timeout=120)
    r.raise_for_status()
    geoms = [shape(f["geometry"]) for f in r.json()["features"] if f["geometry"]["type"].endswith("Polygon")]
    return unary_union(geoms) if geoms else None


def main() -> None:
    assert_in_metro()
    random.seed(5)
    names = list(NAMED)
    pairs = []
    while len(pairs) < 20:
        a, b = random.sample(names, 2)
        if (a, b) not in pairs and (b, a) not in pairs:
            pairs.append((a, b))
    rows, feats = [], []
    for rid, (a, b) in enumerate(pairs, 1):
        pa, pb = arrival_polygon(*NAMED[a]), arrival_polygon(*NAMED[b])
        if pa is None or pb is None:
            rows.append((rid, a, b, None)); continue
        region = pa.intersection(pb)
        if region.is_empty:
            rows.append((rid, a, b, "empty")); continue
        gs = gpd.GeoSeries([region], crs="EPSG:4326").to_crs(GRID.crs)
        area_km2 = float(gs.area.iloc[0]) / 1e6
        bbox_km2 = float(gs.envelope.area.iloc[0]) / 1e6
        w, s, e, n = region.bounds
        bb = BBox(west=round(w, 5), south=round(s, 5), east=round(e, 5), north=round(n, 5))
        rows.append((rid, a, b, dict(area=area_km2, bbox=bbox_km2, leak=leakage_ratio(bbox_area_km2=bbox_km2, region_area_km2=area_km2),
                                    zillow=zillow_url(bb, max_price=600000), redfin=redfin_url(bb), realtor=realtor_url(bb), trulia=trulia_url(bb),
                                    parts=len(getattr(region, "geoms", [region])))))
        feats.append({"type": "Feature", "properties": {"id": rid, "a": a, "b": b, "minutes": MINUTES, "mode": "auto",
                                                        "area_km2": round(area_km2, 2), "leakage": round(bbox_km2 / area_km2, 2)},
                      "geometry": region.__geo_interface__})
    (DATA / f"g4_regions_{METRO.name}.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats}), encoding="utf-8")

    lines = [f"# G4: listings handoff checklist (generated {stamp()})", "",
             f"20 regions = intersection of two {MINUTES}-minute AUTO arrival isochrones (self-hosted Valhalla 3.9.1, "
             f"metro {METRO.name} via {VALHALLA}). Every anchor is asserted inside the evaluation bbox. "
             "Leakage = bounding-box area / region area (1.0 = no leakage). Links are generated from undocumented portal URL shapes "
             "(research 04; Codex C3) and were NOT fetched by any script; the owner opens them by hand on desktop, iOS, and Android and "
             "records: opens with the right bounds (Y/N), price filter kept (Y/N), app handoff returns cleanly (Y/N). A broken link is a "
             "failure, not a skip. Owner decision 14: a city/ZIP link plus our exact region is an acceptable fallback if bounded links are fragile.",
             "", "| id | anchor A | anchor B | region km² | parts | leakage | zillow | redfin | realtor (unverified) | trulia (unverified) | desktop | iOS | Android | filters kept | returns | notes |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for rid, a, b, d in rows:
        if d is None or d == "empty":
            lines.append(f"| {rid} | {a} | {b} | {'empty intersection' if d == 'empty' else 'isochrone failed'} | | | | | | | | | | | | |")
            continue
        lines.append(f"| {rid} | {a} | {b} | {d['area']:.1f} | {d['parts']} | {d['leak']:.2f} | [zillow]({d['zillow']}) | [redfin]({d['redfin']}) | "
                     f"[realtor]({d['realtor']}) | [trulia]({d['trulia']}) | | | | | | |")
    ok = [d for *_, d in rows if isinstance(d, dict)]
    if ok:
        leaks = sorted(d["leak"] for d in ok)
        lines += ["", f"Leakage over {len(ok)} regions: median {statistics.median(leaks):.2f}, max {leaks[-1]:.2f}. "
                  "Regions with several disconnected parts have the largest leakage; the product must show the exact region on our map regardless.",
                  "", "## Pass criterion", "", "≥ 90% of links open with correct bounds on all three device classes for at least two portals, broken links counted; "
                  "filters and app return recorded; leakage reported. RentCast pins are optional and do not gate the free links.",
                  "", "## Verdict", "", "(owner fills after the device sessions)"]
    (RESULTS / f"g4-listings-{METRO.name}.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines[:12]))
    print(f"... {len(ok)} regions written to docs/experiments/g4-listings-{METRO.name}.md and v2/data/g4_regions_{METRO.name}.geojson")


if __name__ == "__main__":
    main()
