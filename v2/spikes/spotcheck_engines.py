"""Spot-check our travel times against independent engines on a dozen real journeys.

Why: every G1 number was measured against Valhalla, which is another static model with no traffic
data, and for walk/bike its speed was set equal to ours. See the "What the G1 comparisons actually
measured" section of docs/experiments/g1-routing.md. This script adds engines that are genuinely
independent of both of ours.

Engines, each skipped if unavailable:
  ours      our directed graph + transposed Dijkstra (locfinder.traveltime)
  valhalla  self-hosted, same costing we use for layers
  osrm      the public OSRM demo server: a third INDEPENDENT static implementation with its own
            speed profile. Car profile only. Polite rate: 1 request/second.
  google    Google Routes API v2 `computeRoutes`, requested TWICE per pair:
              TRAFFIC_UNAWARE  -> compares model against model, like OSRM
              TRAFFIC_AWARE    -> the only number here that knows about congestion
            Needs GOOGLE_MAPS_API_KEY. This is the measurement that decomposes "our model is wrong"
            from "nobody here models traffic".

Terms discipline for the Google leg: live queries for a validation sample are ordinary use, but we
do NOT persist a per-pair table of Google values as a dataset, and we do NOT use these numbers to
calibrate our speed model. The results file records aggregate differences plus a few illustrative
rows, and the raw JSON keeps our own and the open engines' values only.

Run from v2/ with Valhalla serving:
  uv run python spikes/spotcheck_engines.py                      # ours + Valhalla + OSRM
  GOOGLE_MAPS_API_KEY=... uv run python spikes/spotcheck_engines.py   # adds both Google legs
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path

import httpx
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import DATA, GRAPH_CACHE, GRID, METRO, VALHALLA, append_results, stamp  # noqa: E402
from locfinder.traveltime.arrival import arrival_seconds_two_weight  # noqa: E402
from locfinder.traveltime.components import largest_component  # noqa: E402
from locfinder.traveltime.csr import graph_to_cost_time_csr  # noqa: E402
from locfinder.traveltime.speeds import EXTRA_WAY_TAGS, add_travel_times, symmetrise  # noqa: E402

OSRM = "https://router.project-osrm.org"
GOOGLE = "https://routes.googleapis.com/directions/v2:computeRoutes"
# A weekday morning in the future, for the traffic-aware leg.
ILLUSTRATIVE_ROWS = 2   # how many example journeys may quote restricted engines
DEPART = "2026-11-10T13:00:00Z"  # 08:00 America/New_York

PLACES = {
    "UNC Hospitals": (35.9049, -79.0469),
    "Duke University Hospital": (36.0075, -78.9381),
    "Carrboro Town Hall": (35.9100, -79.0750),
    "Downtown Durham": (35.9960, -78.9010),
    "Chapel Hill (Franklin St)": (35.9132, -79.0558),
    "RTP (Kit Creek Rd)": (35.8720, -78.8450),
    "RDU Terminal 2": (35.8776, -78.7875),
    "NC State Bell Tower": (35.7860, -78.6630),
    "Downtown Raleigh (Moore Sq)": (35.7796, -78.6382),
    "Cary Downtown": (35.7880, -78.7810),
    "Southpoint Mall": (35.9050, -78.9450),
    "Hillsborough": (36.0750, -79.0990),
}
PAIRS = [
    ("Carrboro Town Hall", "Downtown Durham"),
    ("UNC Hospitals", "Duke University Hospital"),
    ("Chapel Hill (Franklin St)", "RTP (Kit Creek Rd)"),
    ("Downtown Durham", "RDU Terminal 2"),
    ("NC State Bell Tower", "Downtown Raleigh (Moore Sq)"),
    ("Cary Downtown", "RTP (Kit Creek Rd)"),
    ("Southpoint Mall", "UNC Hospitals"),
    ("Hillsborough", "Downtown Durham"),
    ("RDU Terminal 2", "Downtown Raleigh (Moore Sq)"),
    ("Duke University Hospital", "Southpoint Mall"),
    ("Downtown Raleigh (Moore Sq)", "Cary Downtown"),
    ("Carrboro Town Hall", "RDU Terminal 2"),
]


# ---------------------------------------------------------------- our own graph
def ours_point_to_point(mode: str, pairs) -> dict:
    import osmnx as ox

    if not GRAPH_CACHE.exists():
        print(f"  (no graph cache at {GRAPH_CACHE}; skipping our own engine)")
        return {}
    t0 = time.perf_counter()
    G = ox.load_graphml(GRAPH_CACHE)
    ox.settings.useful_tags_way = sorted(set(ox.settings.useful_tags_way) | set(EXTRA_WAY_TAGS))
    G = ox.project_graph(G, to_crs=GRID.crs)
    G = add_travel_times(G, mode=mode)
    if mode == "walk":
        G = symmetrise(G)
    G.remove_nodes_from([n for n, d in G.degree() if d == 0])
    G, comp = largest_component(G)
    print(f"  components: {comp.summary}")
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
    print(f"  our {mode} graph: {G.number_of_nodes()} nodes in {time.perf_counter() - t0:.0f} s")

    from pyproj import Transformer
    to_proj = Transformer.from_crs("EPSG:4326", GRID.crs, always_xy=True)
    out = {}
    cache: dict[str, np.ndarray] = {}
    for a, b in pairs:
        if b not in cache:
            bx, by = to_proj.transform(PLACES[b][1], PLACES[b][0])
            dest = ox.nearest_nodes(G, bx, by)
            cache[b] = arrival_seconds_two_weight(cost_csr, time_csr, dest_idx=[index[dest]])
        ax, ay = to_proj.transform(PLACES[a][1], PLACES[a][0])
        origin = ox.nearest_nodes(G, ax, ay)
        secs = float(cache[b][index[origin]])
        out[(a, b)] = secs / 60.0 if np.isfinite(secs) else None
    return out


# ---------------------------------------------------------------- valhalla
def valhalla_route(client, a, b, costing: str) -> float | None:
    body = {"locations": [{"lat": PLACES[a][0], "lon": PLACES[a][1]},
                          {"lat": PLACES[b][0], "lon": PLACES[b][1]}], "costing": costing}
    r = client.post(f"{VALHALLA}/route", json=body, timeout=60)
    if r.status_code != 200:
        return None
    return r.json()["trip"]["summary"]["time"] / 60.0


# ---------------------------------------------------------------- osrm (car only)
def osrm_route(client, a, b) -> float | None:
    time.sleep(1.05)  # public demo server: be polite
    la, lo = PLACES[a]
    lb, lob = PLACES[b]
    url = f"{OSRM}/route/v1/driving/{lo},{la};{lob},{lb}?overview=false"
    r = client.get(url, timeout=60, headers={"User-Agent": "locfinder-spotcheck/0.1 (research prototype)"})
    if r.status_code != 200:
        return None
    j = r.json()
    if j.get("code") != "Ok" or not j.get("routes"):
        return None
    return j["routes"][0]["duration"] / 60.0


# ---------------------------------------------------------------- google routes v2
GOOGLE_MODE = {"drive": "DRIVE", "walk": "WALK", "bike": "BICYCLE", "transit": "TRANSIT"}


def google_route(client, a, b, mode: str, key: str, traffic_aware: bool) -> float | None:
    body = {
        "origin": {"location": {"latLng": {"latitude": PLACES[a][0], "longitude": PLACES[a][1]}}},
        "destination": {"location": {"latLng": {"latitude": PLACES[b][0], "longitude": PLACES[b][1]}}},
        "travelMode": GOOGLE_MODE[mode],
    }
    if mode == "drive":
        body["routingPreference"] = "TRAFFIC_AWARE" if traffic_aware else "TRAFFIC_UNAWARE"
        if traffic_aware:
            body["departureTime"] = DEPART
    elif mode == "transit":
        body["departureTime"] = DEPART
    r = client.post(GOOGLE, json=body, timeout=60, headers={
        "X-Goog-Api-Key": key,
        "X-Goog-FieldMask": "routes.duration",
        "Content-Type": "application/json",
    })
    if r.status_code != 200:
        print(f"    google {mode} {'traffic' if traffic_aware else 'static'} {a}->{b}: http {r.status_code} {r.text[:120]}")
        return None
    routes = r.json().get("routes") or []
    if not routes:
        return None
    return float(str(routes[0]["duration"]).rstrip("s")) / 60.0


# ---------------------------------------------------------------- reporting
def diffs(rows, left: str, right: str):
    d = [r[left] - r[right] for r in rows if r.get(left) is not None and r.get(right) is not None]
    if not d:
        return None
    return {"n": len(d), "median_signed": statistics.median(d),
            "median_abs": statistics.median([abs(x) for x in d]),
            "p90_abs": sorted(abs(x) for x in d)[max(int(round(0.9 * len(d))) - 1, 0)],
            "left_faster_share": sum(1 for x in d if x < 0) / len(d)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="drive", choices=["drive", "walk", "bike"])
    ap.add_argument("--skip-ours", action="store_true")
    args = ap.parse_args()
    key = os.environ.get("GOOGLE_MAPS_API_KEY")
    costing = {"drive": "auto", "walk": "pedestrian", "bike": "bicycle"}[args.mode]

    print(f"spot check: {len(PAIRS)} journeys, mode {args.mode}, metro {METRO.name}")
    ours = {} if args.skip_ours else ours_point_to_point(args.mode, PAIRS)

    rows = []
    with httpx.Client() as client:
        for a, b in PAIRS:
            row = {"from": a, "to": b, "ours": ours.get((a, b))}
            row["valhalla"] = valhalla_route(client, a, b, costing)
            if args.mode == "drive":
                row["osrm"] = osrm_route(client, a, b)
            if key:
                row["google_static"] = google_route(client, a, b, args.mode, key, traffic_aware=False)
                if args.mode == "drive":
                    row["google_traffic"] = google_route(client, a, b, args.mode, key, traffic_aware=True)
            rows.append(row)
            got = {k: (f"{v:.0f}" if isinstance(v, float) else "-") for k, v in row.items() if k not in ("from", "to")}
            print(f"  {a} -> {b}: {got}")

    engines = [e for e in ("ours", "valhalla", "osrm", "google_static", "google_traffic")
               if any(r.get(e) is not None for r in rows)]
    # Per-pair values for restricted engines never reach a results file or the JSON; only derived
    # statistics and ILLUSTRATIVE_ROWS examples do. Codex pass 5 (H5) found an earlier version
    # writing the full Google table into the repository while claiming otherwise.
    RESTRICTED = {"google_static", "google_traffic"}
    table_engines = [e for e in engines if e not in RESTRICTED]
    lines = [f"### Independent spot check, {args.mode}, {len(PAIRS)} real journeys ({stamp()})",
             "", f"Metro {METRO.name}. Engines present: {', '.join(engines)}.",
             "Minutes, point to point. OSRM is the public demo server (car profile, independent static model).",
             ("Google legs: `TRAFFIC_UNAWARE` is model-vs-model; `TRAFFIC_AWARE` at 08:00 local is the only "
              "congestion-aware number here. Queried live for validation; not stored as a dataset and not used to "
              "calibrate our model." if key else
              "**Google not run: set GOOGLE_MAPS_API_KEY.** Without it there is still no congestion-aware reference."),
             "", "| from | to | " + " | ".join(table_engines) + " |",
             "|---|---|" + "---|" * len(table_engines)]
    for r in rows:
        cells = " | ".join(f"{r[e]:.0f}" if r.get(e) is not None else "-" for e in table_engines)
        lines.append(f"| {r['from']} | {r['to']} | {cells} |")
    restricted_present = [e for e in engines if e in RESTRICTED]
    if restricted_present:
        ill = rows[:ILLUSTRATIVE_ROWS]
        lines += ["", f"Per-pair values for {', '.join(restricted_present)} are deliberately not written here. "
                  f"{len(ill)} illustrative journeys, minutes:"]
        for r in ill:
            bits = ", ".join(f"{e.replace('google_', 'google ')} {r[e]:.0f}" for e in engines if r.get(e) is not None)
            lines.append(f"- {r['from']} to {r['to']}: {bits}")

    lines += ["", "Pairwise differences (minutes; negative median means the first engine is faster):", "",
              "| comparison | n | median signed | median abs | p90 abs | first faster |", "|---|---|---|---|---|---|"]
    comparisons = [("ours", "valhalla"), ("ours", "osrm"), ("valhalla", "osrm"),
                   ("ours", "google_static"), ("valhalla", "google_static"),
                   ("google_static", "google_traffic"), ("ours", "google_traffic")]
    for left, right in comparisons:
        d = diffs(rows, left, right)
        if d:
            lines.append(f"| {left} vs {right} | {d['n']} | {d['median_signed']:+.1f} | {d['median_abs']:.1f} | "
                         f"{d['p90_abs']:.1f} | {d['left_faster_share']:.0%} |")
    text = "\n".join(lines)
    print("\n" + text)
    append_results("spotcheck-engines.md", text)
    keep = [{k: v for k, v in r.items() if not k.startswith("google")} for r in rows]
    (DATA / f"spotcheck_{args.mode}.json").write_text(json.dumps(keep, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
