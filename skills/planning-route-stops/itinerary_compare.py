#!/usr/bin/env python3
"""Measure several whole itineraries side by side, with one instrument and no API keys.

Where corridor_scan.py scores individual candidate stops, this scores *options*: each
named itinerary is routed as a single multi-point request, so its detour against the
unconstrained fastest route is exact rather than a sum of per-stop excursions. In one
real comparison those two numbers differed by 8 minutes (+43 summed vs +51 routed),
which is the whole reason this exists.

It also returns simplified route geometry, because a route comparison needs a map and
Artifact pages block tile servers -- so the geometry has to be baked into the page.

    python itinerary_compare.py --spec trip.json --depart 4.75 --out measured.json

The spec is JSON:

    {
      "origin": {"name": "Chapel Hill, NC", "lat": 35.9132, "lon": -79.0558},
      "dest":   {"name": "Thomasville, GA", "lat": 30.8366, "lon": -83.9788},
      "stops": {
        "sob":       {"name": "South of the Border", "lat": 34.4985, "lon": -79.3093,
                      "dwell_min": 15, "url": "https://...", "status": "standing"},
        "okefenokee":{"name": "Okefenokee Swamp Park", "lat": 31.0578, "lon": -82.2725,
                      "dwell_min": 75, "cost_usd": 98}
      },
      "options": {
        "fewest-stops": {"label": "Fewest stops, earliest arrival",
                         "stops": ["sob", "okefenokee"]},
        "most-outdoors":{"label": "Most time outdoors",
                         "stops": ["sob", "walterboro", "okefenokee"],
                         "dwell_min": {"okefenokee": 90}}
      }
    }

Name options by what distinguishes them, never by rank. A key called "recommended"
means the comparison stopped before it started -- the script will say so and refuse.

Output: a table per option plus JSON to --out containing measured legs, totals, detour,
derived arrival clocks, per-option simplified geometry and a shared bbox.

Routed columns are MEASURED. Arrival is DERIVED from the departure hour plus the dwell
times in the spec. Sunset is CALCULATED. Free-flow only: no traffic model, so treat
every drive time as a floor and say so wherever you quote it.
"""

import argparse
import json
import math
import sys
import time
import urllib.error
import urllib.request

ROUTE_URL = "https://valhalla1.openstreetmap.de/route"
UA = "planning-route-stops/itinerary_compare (+https://github.com/anthropics/skills)"
RANK_WORDS = {"recommended", "recommend", "best", "winner", "preferred", "optimal",
              "top", "first-choice", "the-plan", "primary"}


# ---------------------------------------------------------------- routing

def _post(points, costing, timeout=120, tries=3):
    body = {
        "locations": [{"lat": p[0], "lon": p[1]} for p in points],
        "costing": costing,
        "directions_options": {"units": "miles"},
    }
    req = urllib.request.Request(
        ROUTE_URL, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "User-Agent": UA})
    last = None
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            last = exc
            if attempt < tries - 1:
                time.sleep(2 + 2 * attempt)
    raise RuntimeError(f"routing failed after {tries} attempts: {last}")


def decode_polyline6(encoded):
    """Valhalla shapes are precision 6, not the usual 5. Decoding at 5 lands you in
    roughly the wrong hemisphere, which is a surprisingly quiet failure on a blank map."""
    coords, lat, lon, i = [], 0, 0, 0
    n = len(encoded)
    while i < n:
        for _ in range(2):
            shift, result = 0, 0
            while True:
                b = ord(encoded[i]) - 63
                i += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            delta = ~(result >> 1) if result & 1 else (result >> 1)
            if _ == 0:
                lat += delta
            else:
                lon += delta
        coords.append((lat / 1e6, lon / 1e6))
    return coords


# ---------------------------------------------------------------- geometry

def rdp(points, epsilon):
    """Iterative Ramer-Douglas-Peucker. Recursion blows the stack on long routes."""
    if len(points) < 3:
        return list(points)
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        lo, hi = stack.pop()
        if hi <= lo + 1:
            continue
        ax, ay = points[lo]
        bx, by = points[hi]
        dx, dy = bx - ax, by - ay
        norm = math.hypot(dx, dy)
        worst_d, worst_i = -1.0, -1
        for i in range(lo + 1, hi):
            px, py = points[i]
            if norm == 0.0:
                d = math.hypot(px - ax, py - ay)
            else:
                d = abs(dy * (px - ax) - dx * (py - ay)) / norm
            if d > worst_d:
                worst_d, worst_i = d, i
        if worst_d > epsilon:
            keep[worst_i] = True
            stack.append((lo, worst_i))
            stack.append((worst_i, hi))
    return [p for p, k in zip(points, keep) if k]


def simplify_route(legs_shapes, epsilon, cap):
    """One flat, de-duplicated, simplified polyline for the whole option."""
    pts = []
    for shape in legs_shapes:
        for p in decode_polyline6(shape):
            if not pts or (abs(p[0] - pts[-1][0]) > 1e-9 or abs(p[1] - pts[-1][1]) > 1e-9):
                pts.append(p)
    eps = epsilon
    out = rdp(pts, eps)
    # Tighten until it fits the cap; a map at state scale needs far fewer points than
    # people expect, and an oversized array is the thing that bloats a baked page.
    while len(out) > cap and eps < 1.0:
        eps *= 1.6
        out = rdp(pts, eps)
    return [[round(a, 5), round(b, 5)] for a, b in out], len(pts), round(eps, 6)


# ---------------------------------------------------------------- sun

def _julian(y, m, d):
    if m <= 2:
        y, m = y - 1, m + 12
    a = y // 100
    b = 2 - a + a // 4
    return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + b - 1524.5


def sun_events(lat, lon, y, m, d, utc_offset, altitude=-0.833):
    """Local decimal hours (sunrise, solar noon, sunset), or None in polar day/night.
    NOAA solar position evaluated once at local midnight -- a minute or two of error at
    mid-latitudes, far finer than any arrival time it gets compared against."""
    t = (_julian(y, m, d) - 2451545.0) / 36525.0
    L0 = (280.46646 + t * (36000.76983 + t * 0.0003032)) % 360.0
    M = 357.52911 + t * (35999.05029 - 0.0001537 * t)
    Mr = math.radians(M)
    C = (math.sin(Mr) * (1.914602 - t * (0.004817 + 0.000014 * t))
         + math.sin(2 * Mr) * (0.019993 - 0.000101 * t)
         + math.sin(3 * Mr) * 0.000289)
    omega = 125.04 - 1934.136 * t
    app = L0 + C - 0.00569 - 0.00478 * math.sin(math.radians(omega))
    e0 = 23.0 + (26.0 + (21.448 - t * (46.815 + t * (0.00059 - t * 0.001813))) / 60.0) / 60.0
    eps = e0 + 0.00256 * math.cos(math.radians(omega))
    decl = math.degrees(math.asin(math.sin(math.radians(eps)) * math.sin(math.radians(app))))
    y2 = math.tan(math.radians(eps / 2.0)) ** 2
    eot = 4 * math.degrees(
        y2 * math.sin(2 * math.radians(L0)) - 2 * 0.016708634 * math.sin(Mr)
        + 4 * 0.016708634 * y2 * math.sin(Mr) * math.cos(2 * math.radians(L0))
        - 0.5 * y2 * y2 * math.sin(4 * math.radians(L0))
        - 1.25 * 0.016708634 ** 2 * math.sin(2 * Mr))
    lat_r, dec_r = math.radians(lat), math.radians(decl)
    cos_ha = ((math.sin(math.radians(altitude)) - math.sin(lat_r) * math.sin(dec_r))
              / (math.cos(lat_r) * math.cos(dec_r)))
    noon = (720 - 4 * lon - eot) / 60.0 + utc_offset
    if not -1.0 <= cos_ha <= 1.0:
        return None, noon, None
    ha = math.degrees(math.acos(cos_ha)) / 15.0
    return noon - ha, noon, noon + ha


# ---------------------------------------------------------------- formatting

def hm(seconds):
    s = int(round(seconds))
    sign = "-" if s < 0 else ""
    s = abs(s)
    return f"{sign}{s // 3600}h{s % 3600 // 60:02d}"


def plus_min(seconds):
    s = int(round(seconds / 60.0))
    return f"{s:+d} min"


def clock(h):
    h = h % 24
    total = int(round(h * 60))
    return f"{total // 60 % 24:02d}:{total % 60:02d}"


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(
        description="Measure several whole itineraries side by side, one engine, no keys.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""--spec format:

  {
    "origin": {"name": "Chapel Hill, NC", "lat": 35.9132, "lon": -79.0558},
    "dest":   {"name": "Thomasville, GA", "lat": 30.8366, "lon": -83.9788},
    "stops": {
      "sob":        {"name": "South of the Border", "where": "Dillon, SC",
                     "lat": 34.4985, "lon": -79.3093, "dwell_min": 15,
                     "cost_usd": 0, "url": "https://...",
                     "hours": "daily 09:00-17:00", "status": "standing"},
      "okefenokee": {"name": "Okefenokee Swamp Park", "where": "Waycross, GA",
                     "lat": 31.0578, "lon": -82.2725, "dwell_min": 80,
                     "cost_usd": 98, "url": "https://...",
                     "hours": "daily 09:00-17:00", "status": "standing"}
    },
    "options": {
      "fewest-stops":  {"label": "Fewest stops, earliest arrival",
                        "stops": ["sob"]},
      "one-big-thing": {"label": "One big thing: the swamp",
                        "stops": ["sob", "okefenokee"],
                        "dwell_min": {"okefenokee": 90}}
    }
  }

  status is one of: confirmed | standing | unknown  (carried through to the output)
  cost_usd is per party, as published; omit it rather than guessing.
  Per-option "dwell_min" overrides the stop's own dwell for that option only.

Name options by what distinguishes them -- fewest-stops, most-outdoors, cheapest --
never by rank. A key naming a winner is refused: the traveller weighs, you measure.

Example:
  itinerary_compare.py --spec trip.json --depart 4.75 --date 2026-11-25 \\
      --utc-offset -5 --out measured.json
""")
    ap.add_argument("--spec", required=True, help="JSON spec: origin, dest, stops, options")
    ap.add_argument("--depart", type=float, default=8.0,
                    help="local decimal hour of departure, e.g. 4.75 for 04:45 (default 8.0)")
    ap.add_argument("--date", help="YYYY-MM-DD, enables the sunset column")
    ap.add_argument("--utc-offset", type=float, default=0.0,
                    help="UTC offset at the DESTINATION, e.g. -5 for US Eastern in November")
    ap.add_argument("--costing", default="auto",
                    help="auto | bicycle | pedestrian | truck | motor_scooter")
    ap.add_argument("--rdp-epsilon", type=float, default=0.004,
                    help="initial RDP tolerance in degrees (default 0.004, ~400 m)")
    ap.add_argument("--max-points", type=int, default=120,
                    help="per-option geometry point cap (default 120)")
    ap.add_argument("--out", help="write the full measured JSON here")
    a = ap.parse_args()

    spec = json.load(open(a.spec, encoding="utf-8"))
    origin, dest = spec["origin"], spec["dest"]
    stops, options = spec["stops"], spec["options"]

    bad = [k for k in options if k.strip().lower().replace(" ", "-") in RANK_WORDS]
    if bad:
        sys.exit(f"option key(s) {bad} name a rank, not a difference. Rename them by what\n"
                 f"distinguishes the option (fewest-stops, most-outdoors, cheapest). A winner\n"
                 f"named in the measuring code means the comparison stopped before it started.")

    o = (origin["lat"], origin["lon"])
    d = (dest["lat"], dest["lon"])

    direct = _post([o, d], a.costing)["trip"]["summary"]
    print(f"direct  {origin.get('name', 'origin')} -> {dest.get('name', 'dest')}:  "
          f"{hm(direct['time'])}  {direct['length']:.0f} mi"
          f"   ({a.costing}, free-flow, no traffic model)\n")
    time.sleep(0.8)

    sunset_h = None
    if a.date:
        y, m, dd = (int(x) for x in a.date.split("-"))
        _, _, sunset_h = sun_events(d[0], d[1], y, m, dd, a.utc_offset)

    results, all_pts = {}, []
    for key, opt in options.items():
        seq_keys = opt["stops"]
        missing = [s for s in seq_keys if s not in stops]
        if missing:
            sys.exit(f"option '{key}' references unknown stops: {missing}")
        pts = [o] + [(stops[s]["lat"], stops[s]["lon"]) for s in seq_keys] + [d]

        trip = _post(pts, a.costing)["trip"]
        legs = [leg["summary"]["time"] for leg in trip["legs"]]
        miles = trip["summary"]["length"]
        total = trip["summary"]["time"]
        detour = total - direct["time"]

        dwell_over = opt.get("dwell_min", {})
        dwells, cost = [], 0.0
        for s in seq_keys:
            dwells.append(float(dwell_over.get(s, stops[s].get("dwell_min", 0))))
            cost += float(stops[s].get("cost_usd", 0) or 0)

        # DERIVED: departure + measured legs + spec dwell times.
        t = a.depart
        schedule = []
        for i, s in enumerate(seq_keys):
            t += legs[i] / 3600.0
            schedule.append({"stop": s, "arrive": clock(t), "arrive_h": round(t, 4),
                             "dwell_min": dwells[i], "leg_s": legs[i]})
            t += dwells[i] / 60.0
        t += legs[-1] / 3600.0
        arrive_h = t

        geom, raw_n, eps_used = simplify_route(
            [leg["shape"] for leg in trip["legs"]], a.rdp_epsilon, a.max_points)
        all_pts.extend(geom)

        results[key] = {
            "label": opt.get("label", key),
            "stops": seq_keys,
            "legs_s": legs,
            "total_s": total,
            "miles": round(miles, 1),
            "detour_s": detour,
            "dwell_total_min": sum(dwells),
            "cost_usd": round(cost, 2),
            "depart_h": a.depart,
            "arrive_h": round(arrive_h, 4),
            "arrive": clock(arrive_h),
            "elapsed_s": total + sum(dwells) * 60.0,
            "schedule": schedule,
            "geometry": geom,
            "geometry_raw_points": raw_n,
            "rdp_epsilon_used": eps_used,
        }
        if sunset_h is not None:
            results[key]["sunset"] = clock(sunset_h)
            results[key]["after_sunset"] = arrive_h > sunset_h
        time.sleep(0.8)

    lats = [p[0] for p in all_pts]
    lons = [p[1] for p in all_pts]
    bbox = {"min_lat": min(lats), "max_lat": max(lats),
            "min_lon": min(lons), "max_lon": max(lons)}

    w = max(len(v["label"]) for v in results.values())
    hdr = (f"{'option':<{w}}  {'drive':>6} {'added':>8} {'miles':>6} {'stops':>5} "
           f"{'dwell':>6} {'elapsed':>8} {'cost':>7} {'arrive':>7}")
    if sunset_h is not None:
        hdr += f"  {'sunset':>7}"
    print(hdr)
    print("-" * len(hdr))
    for key, v in sorted(results.items(), key=lambda kv: kv[1]["total_s"]):
        line = (f"{v['label']:<{w}}  {hm(v['total_s']):>6} {plus_min(v['detour_s']):>8} "
                f"{v['miles']:>6.0f} {len(v['stops']):>5} {int(v['dwell_total_min']):>5}m "
                f"{hm(v['elapsed_s']):>8} {('$' + str(int(v['cost_usd']))) if v['cost_usd'] else '-':>7} "
                f"{v['arrive']:>7}")
        if sunset_h is not None:
            line += f"  {v['sunset']:>7}{'  (after)' if v['after_sunset'] else ''}"
        print(line)

    print("\nlegs per option (measured, free-flow):")
    for key, v in results.items():
        chain = " -> ".join(hm(s) for s in v["legs_s"])
        print(f"  {v['label']}: {chain}")

    print("\ngeometry for baking into the page (tiles are blocked in artifacts):")
    for key, v in results.items():
        print(f"  {key:<16} {len(v['geometry']):>4} points "
              f"(from {v['geometry_raw_points']}, eps={v['rdp_epsilon_used']})")
    print(f"  bbox  lat {bbox['min_lat']:.3f}..{bbox['max_lat']:.3f}  "
          f"lon {bbox['min_lon']:.3f}..{bbox['max_lon']:.3f}")

    payload = {"direct": {"total_s": direct["time"], "miles": round(direct["length"], 1),
                          "costing": a.costing},
               "origin": origin, "dest": dest, "stops": stops,
               "options": results, "bbox": bbox,
               "assumptions": {"depart_h": a.depart, "date": a.date,
                               "utc_offset": a.utc_offset,
                               "dwell_source": "spec stops[].dwell_min, per-option overrides"}}
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=1)
        print(f"\nwrote {a.out}")

    print("\nProvenance, so these get labelled correctly downstream:")
    print("  drive/added/miles/legs       MEASURED   routed, one engine, free-flow")
    print("                                          (no traffic model -- quote as a floor)")
    print("  elapsed/arrive               DERIVED    departure hour + measured legs + spec dwells")
    print("  cost                         DERIVED    sum of stops[].cost_usd as given in the spec")
    if a.date:
        print("  sunset                       CALCULATED NOAA solar position, approximate")
    print("\nThe traveller weighs these; you measured them. Ship the options, not a verdict.")


if __name__ == "__main__":
    main()
