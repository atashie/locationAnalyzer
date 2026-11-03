"""Geocoding provider contract (Task 11): US Census Geocoder vs public Nominatim on slice
addresses, plus ambiguous and POI-style queries (Codex pass 3 M3).

Sources and etiquette (see docs/experiments/source-registry.md):
- Census Geocoder: public-domain output; be polite; attribution disclaimer required.
- Nominatim public API: usage policy requires <= 1 request/s, an identifying User-Agent,
  attribution, no autocomplete, caching of results. We send one request per second.

Writes docs/experiments/geocoding.md. Run from v2/:  uv run python spikes/geocode_bench.py
"""
from __future__ import annotations

import json
import math
import random
import statistics
import sys
import time
from pathlib import Path

import httpx
import quackosm as qosm

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import RESULTS, SLICE, stamp  # noqa: E402

UA = "locfinder-phase0-geocode-bench/0.1 (research prototype; contact: arik.tash@gmail.com)"
N_ADDR = 40
AMBIGUOUS = ["Whole Foods, Chapel Hill NC", "Whole Foods Durham", "Harris Teeter Carrboro", "UNC Hospitals", "Duke Hospital",
             "RTP", "Fidelity Investments Durham NC", "Southpoint", "Carrboro Farmers Market", "Weaver Street Market"]


def haversine_m(lat1, lon1, lat2, lon2):
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def sample_addresses() -> list[dict]:
    gdf = qosm.convert_pbf_to_geodataframe(str(SLICE / "slice.osm.pbf"),
                                           tags_filter={"addr:housenumber": True, "addr:street": True, "addr:city": True},
                                           keep_all_tags=True, explode_tags=True)
    gdf = gdf[gdf.geometry.geom_type == "Point"].dropna(subset=["addr:housenumber", "addr:street", "addr:city"])
    random.seed(11)
    rows = gdf.sample(n=min(N_ADDR, len(gdf)), random_state=11)
    out = []
    for _, r in rows.iterrows():
        pc = r.get("addr:postcode")
        text = f"{r['addr:housenumber']} {r['addr:street']}, {r['addr:city']}, NC" + (f" {pc}" if isinstance(pc, str) else "")
        out.append({"query": text, "lat": float(r.geometry.y), "lon": float(r.geometry.x)})
    return out


def census(client: httpx.Client, q: str):
    t0 = time.perf_counter()
    r = client.get("https://geocoding.geo.census.gov/geocoder/locations/onelineaddress",
                   params={"address": q, "benchmark": "Public_AR_Current", "format": "json"}, timeout=30)
    dt = time.perf_counter() - t0
    if r.status_code != 200:
        return None, dt, f"http {r.status_code}"
    m = r.json().get("result", {}).get("addressMatches", [])
    if not m:
        return None, dt, "no match"
    c = m[0]["coordinates"]
    return (float(c["y"]), float(c["x"])), dt, m[0].get("matchedAddress", "")


def nominatim(client: httpx.Client, q: str):
    time.sleep(1.05)  # usage policy: max 1 request per second
    t0 = time.perf_counter()
    r = client.get("https://nominatim.openstreetmap.org/search", params={"q": q, "format": "jsonv2", "limit": 1, "countrycodes": "us"},
                   headers={"User-Agent": UA}, timeout=30)
    dt = time.perf_counter() - t0
    if r.status_code != 200:
        return None, dt, f"http {r.status_code}"
    j = r.json()
    if not j:
        return None, dt, "no match"
    return (float(j[0]["lat"]), float(j[0]["lon"])), dt, j[0].get("display_name", "")[:80]


def main() -> None:
    addrs = sample_addresses()
    lines = [f"# Geocoding contract benchmark ({stamp()})", "",
             f"{len(addrs)} OSM address points sampled from the slice (truth = the OSM point itself, so this favours Nominatim slightly; "
             f"Codex pass 3 M3) plus {len(AMBIGUOUS)} ambiguous / POI-style queries. One request per second to Nominatim with an identifying User-Agent.", ""]
    with httpx.Client() as client:
        res = {"census": [], "nominatim": []}
        for a in addrs:
            for name, fn in (("census", census), ("nominatim", nominatim)):
                pt, dt, note = fn(client, a["query"])
                err = haversine_m(a["lat"], a["lon"], *pt) if pt else None
                res[name].append({"q": a["query"], "ok": pt is not None, "err_m": err, "s": dt, "note": note})
        lines += ["| provider | n | matched | median err m | p90 err m | > 250 m | median s |", "|---|---|---|---|---|---|---|"]
        for name, rows in res.items():
            ok = [r for r in rows if r["ok"]]
            errs = sorted(r["err_m"] for r in ok)
            if errs:
                lines.append(f"| {name} | {len(rows)} | {len(ok)} | {statistics.median(errs):.0f} | {errs[int(0.9 * len(errs)) - 1]:.0f} | "
                             f"{sum(e > 250 for e in errs)} | {statistics.median(r['s'] for r in rows):.2f} |")
            else:
                lines.append(f"| {name} | {len(rows)} | 0 | - | - | - | {statistics.median(r['s'] for r in rows):.2f} |")
        lines += ["", "## Ambiguous and POI-style queries", "", "| query | census | nominatim |", "|---|---|---|"]
        for q in AMBIGUOUS:
            c = census(client, q)
            n = nominatim(client, q)
            lines.append(f"| {q} | {'match: ' + c[2] if c[0] else c[2]} | {'match: ' + n[2] if n[0] else n[2]} |")
    lines += ["", "## Contract notes", "",
              "- Census Geocoder: street addresses only (no POI names); public-domain output; display the Census disclaimer; no autocomplete endpoint.",
              "- Nominatim public API: 1 req/s application-wide, identifying User-Agent, attribution, results may be cached, autocomplete forbidden; dev-time only.",
              "- A POI/name resolver (for 'Whole Foods', 'UNC Hospitals') must come from our own Overture/OSM place index, not from the geocoder.",
              "- Verdict and chosen fallback order: (fill after reading the tables).",
              "", "Raw results: v2/data/geocode_bench.json"]
    (Path(__file__).resolve().parents[1] / "data" / "geocode_bench.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    (RESULTS / "geocoding.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
