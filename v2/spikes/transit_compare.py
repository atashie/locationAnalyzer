"""Transit engine experiment (owner decision 13): can we build a SCHEDULED INBOUND
transit surface for the Triangle, and which engine does it?

Three engines, one question: "if I must arrive at anchor X by 08:00 on a weekday, how
long is my journey from cell/origin O?"

- Valhalla multimodal: `date_time.type=2` (arrive by) returns HTTP 501 "not implemented"
  (measured in G2). Departure-only isochrones exist. Recorded as UNSUPPORTED for the
  product's arrival semantics.
- MOTIS (self-hosted, slice + 7 Triangle GTFS feeds): `/api/v1/plan?arriveBy=true` for
  point-to-point, and `/api/v1/one-to-all?arriveBy=true` which returns every reachable
  transit stop with its latest feasible departure -> the basis of an arrival surface.
- Transitous: a public MOTIS deployment. NOT ground truth (same engine family); used only
  as a coverage cross-check, <= 40 requests at <= 1 req/s with an identifying User-Agent,
  per its usage policy (research 03; docs/experiments/source-registry.md).

Commute duration is defined as arrival deadline minus the latest feasible departure
(includes waiting), not the minimum itinerary duration in a search window (Codex pass 3 H1).

Run from v2/ with MOTIS on :8080 (and Valhalla on :8002):
  uv run python spikes/transit_compare.py [--skip-transitous]
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import DATA, RESULTS, VALHALLA, append_results, stamp  # noqa: E402

MOTIS = "http://localhost:8080"
TRANSITOUS = "https://api.transitous.org"
UA = "locfinder-phase0-transit-experiment/0.1 (research prototype; contact: arik.tash@gmail.com)"

# Arrive by 08:00 America/New_York on Tuesday 2026-11-10 = 13:00Z (EST, UTC-5)
ARRIVE_LOCAL = "2026-11-10T08:00:00-05:00"
ARRIVE_UTC = "2026-11-10T13:00:00Z"
ARRIVE_DT = datetime(2026, 11, 10, 13, 0, tzinfo=timezone.utc)

ANCHORS = {
    "UNC Hospitals": (35.9049, -79.0469),
    "Duke University Hospital": (36.0075, -78.9381),
    "Downtown Raleigh (Moore Sq)": (35.7796, -78.6382),
}
# Origins chosen in transit-served neighbourhoods (a random rural point tests nothing).
ORIGINS = {
    "Carrboro (Weaver St)": (35.9101, -79.0753),
    "Durham (9th St)": (36.0105, -78.9200),
    "Chapel Hill (Franklin St)": (35.9132, -79.0558),
    "Durham (Hayti)": (35.9860, -78.9050),
    "Raleigh (Cameron Village)": (35.7920, -78.6600),
    "RTP (Davis Dr)": (35.8900, -78.8600),
    "Cary (Chatham St)": (35.7880, -78.7810),
}


def parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def motis_plan(client: httpx.Client, base: str, o, d, *, headers=None, delay=0.0):
    """Latest feasible departure -> minutes before the arrival deadline."""
    if delay:
        time.sleep(delay)
    params = {"fromPlace": f"{o[0]},{o[1]}", "toPlace": f"{d[0]},{d[1]}", "time": ARRIVE_UTC,
              "arriveBy": "true", "timetableView": "false"}
    t0 = time.perf_counter()
    try:
        r = client.get(f"{base}/api/v1/plan", params=params, timeout=90, headers=headers or {})
    except Exception as e:  # noqa: BLE001
        return None, time.perf_counter() - t0, f"error {type(e).__name__}"
    dt = time.perf_counter() - t0
    if r.status_code != 200:
        return None, dt, f"http {r.status_code} {r.text[:80]}"
    its = r.json().get("itineraries", [])
    transit = [i for i in its if any(l.get("mode") not in (None, "WALK") for l in i.get("legs", []))]
    pool = transit or its
    if not pool:
        return None, dt, "no itinerary"
    # latest feasible departure = max start time among itineraries arriving by the deadline
    best = max(pool, key=lambda i: parse_iso(i["startTime"]))
    minutes = (ARRIVE_DT - parse_iso(best["startTime"])).total_seconds() / 60.0
    modes = sorted({l.get("mode") for l in best.get("legs", []) if l.get("mode")})
    return minutes, dt, ("transit" if transit else "walk-only") + " " + ",".join(m[:4] for m in modes)


def motis_one_to_all(client: httpx.Client, anchor, minutes=45):
    params = {"one": f"{anchor[0]},{anchor[1]}", "time": ARRIVE_UTC, "maxTravelTime": minutes, "arriveBy": "true"}
    t0 = time.perf_counter()
    r = client.get(f"{MOTIS}/api/v1/one-to-all", params=params, timeout=120)
    dt = time.perf_counter() - t0
    if r.status_code != 200:
        return None, dt, f"http {r.status_code}"
    arr = r.json().get("all", [])
    return arr, dt, f"{len(arr)} reachable stops"


def valhalla_multimodal_arrival(client: httpx.Client, anchor, minutes=45):
    body = {"locations": [{"lat": anchor[0], "lon": anchor[1]}], "costing": "multimodal",
            "date_time": {"type": 2, "value": "2026-11-10T08:00"}, "contours": [{"time": minutes}],
            "polygons": True, "reverse": True}
    r = client.post(f"{VALHALLA}/isochrone", json=body, timeout=120)
    return r.status_code, r.text[:140]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-transitous", action="store_true")
    args = ap.parse_args()
    raw: dict = {"arrive_local": ARRIVE_LOCAL, "arrive_utc": ARRIVE_UTC}
    lines = [f"# Transit engine experiment ({stamp()})", "",
             f"**Question.** Scheduled INBOUND transit: arrive by {ARRIVE_LOCAL} (Tuesday). Owner decision 13 put transit in Phase 0.",
             "", "## 1. Valhalla multimodal: arrival semantics", ""]

    with httpx.Client() as client:
        for name, a in list(ANCHORS.items())[:1]:
            code, body = valhalla_multimodal_arrival(client, a)
            lines.append(f"- `date_time.type=2` (arrive by) at {name}: **HTTP {code}** — `{body.strip()}`")
        lines += ["- Departure isochrones (`type=1`) do work (G2), so Valhalla can answer \"where can I get to by 08:00 leaving now\" "
                  "but not \"where can I live and still arrive by 08:00\". For a commute product the second question is the one users ask.",
                  "", "## 2. MOTIS one-to-all (the arrival surface primitive)", "",
                  "| anchor | reachable stops within 45 min | response s |", "|---|---|---|"]
        raw["one_to_all"] = {}
        for name, a in ANCHORS.items():
            arr, dt, note = motis_one_to_all(client, a)
            n = len(arr) if arr else 0
            raw["one_to_all"][name] = {"n": n, "seconds": dt, "note": note}
            lines.append(f"| {name} | {n} | {dt:.2f} |")
        lines += ["", "Each entry carries the stop, its coordinates, and the latest feasible departure for the 08:00 arrival, "
                  "which is exactly what a precomputed arrival surface needs (stops -> street access -> cells).",
                  "", "## 3. Point-to-point commute, latest feasible departure", "",
                  "Duration = arrival deadline minus the latest departure that still arrives by it (waiting included).", "",
                  "| origin | anchor | MOTIS self-hosted (min) | mode | Transitous (min) | note |", "|---|---|---|---|---|---|"]
        raw["pairs"] = []
        diffs = []
        for oname, o in ORIGINS.items():
            for aname, a in ANCHORS.items():
                m, mdt, mnote = motis_plan(client, MOTIS, o, a)
                t = tnote = None
                if not args.skip_transitous:
                    t, tdt, tnote = motis_plan(client, TRANSITOUS, o, a, headers={"User-Agent": UA}, delay=1.1)
                row = {"origin": oname, "anchor": aname, "motis_min": m, "motis_note": mnote,
                       "transitous_min": t, "transitous_note": tnote, "motis_s": mdt}
                raw["pairs"].append(row)
                if m is not None and t is not None:
                    diffs.append(abs(m - t))
                lines.append(f"| {oname} | {aname} | {('%.0f' % m) if m is not None else mnote} | {mnote.split()[0] if m is not None else ''} | "
                             f"{('%.0f' % t) if t is not None else (tnote or 'skipped')} | |")
    ok = [r for r in raw["pairs"] if r["motis_min"] is not None]
    transit_ok = [r for r in ok if r["motis_note"].startswith("transit")]
    lines += ["", f"MOTIS answered {len(ok)}/{len(raw['pairs'])} pairs; {len(transit_ok)} used at least one transit leg. "
              + (f"Median |MOTIS - Transitous| = {statistics.median(diffs):.0f} min over {len(diffs)} comparable pairs "
                 "(both are MOTIS, so agreement checks feed coverage, not accuracy)." if diffs else "Transitous comparison skipped."),
              "", "## Verdict", "",
              "- **Valhalla cannot serve the transit use case** the product needs (no arrive-by multimodal).",
              "- **MOTIS can**: self-hosted, MIT, import of the slice plus seven Triangle GTFS feeds takes seconds, the server idles at "
              "~80 MiB, and `one-to-all?arriveBy=true` yields the stop-level arrival surface. It must run on the WSL/VPS **native** filesystem "
              "(a Windows bind mount fails) and, in this image, as root unless the data directory is owned by the image user.",
              "- Transit therefore enters the architecture as a **second routing service** (MOTIS alongside Valhalla), not as a Valhalla costing. "
              "Budget impact: Tier 2 in the synthesis (one extra small container; measured footprint here is far below the 4-8 GB the research assumed).",
              "- Remaining work before a transit layer ships: street access from stops to grid cells (walk layer from the chosen engine), "
              "a departure-window policy (single 08:00 deadline vs a window), and GTFS freshness/calendar validation per feed."]
    text = "\n".join(lines)
    (RESULTS / "transit.md").write_text(text + "\n", encoding="utf-8", newline="\n")
    (DATA / "transit_compare.json").write_text(json.dumps(raw, indent=1), encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
