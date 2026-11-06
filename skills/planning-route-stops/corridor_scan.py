#!/usr/bin/env python3
"""Score candidate stops along a journey, with one instrument and no API keys.

For each candidate it routes origin -> candidate -> destination as a single
three-point request, which yields both legs and therefore the exact detour cost
against the unconstrained fastest route. Optionally reports arrival time against
local sunset, which is usually the constraint that actually decides a stop.

Everything comes from one engine (public Valhalla) so the numbers stay
comparable. Mixing engines across a comparison is the failure this exists to
prevent.

    python corridor_scan.py --origin 29.6516,-82.3248 --dest 35.9132,-79.0558 \
        --candidates candidates.csv --date 2026-11-28 --depart 9.5

candidates.csv: one "Name,lat,lon" per line, '#' comments allowed.

Output: a table sorted by detour, plus JSON to --out. Routed columns are measured;
arrival is DERIVED from an assumed break fraction and any time-zone shift, and sunset
is CALCULATED. The run prints which is which -- carry those labels downstream.
Free-flow only: no traffic model, so treat the times as a floor and say so.
"""

import argparse
import csv
import datetime
import json
import math
import pathlib
import re
import sys
import time

import requests

VALHALLA = "https://valhalla1.openstreetmap.de"


# ---------------------------------------------------------------- routing
def route(points, costing="auto", timeout=90):
    body = {
        "locations": [{"lat": a, "lon": o} for a, o in points],
        "costing": costing,
        "directions_options": {"units": "miles"},
    }
    r = requests.post(f"{VALHALLA}/route", json=body, timeout=timeout)
    r.raise_for_status()
    return r.json()["trip"]


def legs_of(trip):
    return [(l["summary"]["time"] / 3600.0, l["summary"]["length"])
            for l in trip["legs"]]


ROAD_REF = re.compile(r"\b(I|US|SR|CR|[A-Z]{2})[\s-]?(\d{1,3}[A-Z]?)\b")


def roads_seen(trip):
    """Best-effort road references per leg, normalised to I-85 form.

    BEST EFFORT ONLY -- never use an absence here to claim a road was avoided.
    Valhalla's street_names are display names, not a complete reference inventory:
    "County Road 42" and "State Route 7" do not reliably surface, and names appear
    only where a maneuver carries them. To *prove* avoidance, test the route geometry
    against that road's geometry instead.
    """
    out = []
    for leg in trip["legs"]:
        refs, seen = [], set()
        for m in leg["maneuvers"]:
            names = (m.get("street_names") or []) + (m.get("begin_street_names") or [])
            for s in names:
                for pre, num in ROAD_REF.findall(s):
                    ref = pre + "-" + num
                    if ref not in seen:
                        seen.add(ref)
                        refs.append(ref)
        out.append(refs)
    return out


# ---------------------------------------------------------------- sun
def _julian(y, m, d):
    if m <= 2:
        y, m = y - 1, m + 12
    a = y // 100
    b = 2 - a + a // 4
    return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + b - 1524.5


def sunset(lat, lon, y, m, d, utc_offset, altitude=-0.833):
    """NOAA solar position. Returns local decimal hours, or None (polar day/night).

    Solar parameters are evaluated once at the date's *UTC* midnight (not local midnight)
    rather than iterated to the event. Measured against an iterated solution at 31 N,
    -82.27, UTC-5 in late November that costs about 26 s on sunrise and 13 s on sunset --
    finer than the "minute or two" this once claimed, and far finer than the uncertainty
    in any arrival time it is compared against. Do not quote it as exact; NOAA's accuracy
    statement describes NOAA's code, not this.
    """
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
    if not -1.0 <= cos_ha <= 1.0:
        return None
    ha = math.degrees(math.acos(cos_ha))
    return (720 - 4 * lon - eot) / 60.0 + ha / 15.0 + utc_offset


def hhmm(h):
    """Local clock time. Round to whole minutes FIRST, then wrap -- rounding the hour and
    the minute separately turns 23.999 into 24:00 instead of 00:00. '+1d' marks next day."""
    if h is None:
        return "--:--"
    total = int(round(h * 60))
    day, total = divmod(total, 24 * 60)
    hh, mm = divmod(total, 60)
    return f"{hh:02d}:{mm:02d}" + ("+1d" if day >= 1 else "")


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--origin", required=True, help="lat,lon")
    ap.add_argument("--dest", required=True, help="lat,lon")
    ap.add_argument("--candidates", required=True, help="CSV: Name,lat,lon")
    ap.add_argument("--date", help="YYYY-MM-DD, enables the sunset column")
    ap.add_argument("--depart", type=float, default=9.5,
                    help="local decimal hour of departure (default 9.5)")
    ap.add_argument("--break-frac", type=float, default=0.18,
                    help="fraction added for fuel/food/bathroom stops (default 0.18). "
                         "This is an ASSUMPTION -- disclose it wherever you quote arrivals.")
    ap.add_argument("--utc-offset", type=float, default=-5.0,
                    help="UTC offset at the CANDIDATES, e.g. -6 for US Central")
    ap.add_argument("--origin-utc-offset", type=float, default=None,
                    help="UTC offset at the ORIGIN. Defaults to --utc-offset. Set it when "
                         "the journey crosses a time zone, or every arrival is wrong by "
                         "the difference.")
    ap.add_argument("--costing", default="auto",
                    help="auto | bicycle | pedestrian | truck | motor_scooter")
    ap.add_argument("--out", default="corridor_scan.json")
    a = ap.parse_args()

    o = tuple(float(x) for x in a.origin.split(","))
    d = tuple(float(x) for x in a.dest.split(","))

    cands = []
    with open(a.candidates, newline="", encoding="utf-8") as fh:
        for row in csv.reader(fh):
            if not row or row[0].lstrip().startswith("#"):
                continue
            cands.append((row[0].strip(), float(row[1]), float(row[2])))
    if not cands:
        sys.exit("no candidates parsed")

    base = route([o, d], a.costing)["summary"]["time"] / 3600.0
    print(f"direct {o} -> {d}: {base:.2f} h  ({a.costing}, free-flow, no traffic model)\n")

    y = m = dd = None
    if a.date:
        try:
            y, m, dd = (int(v) for v in a.date.split("-"))
            datetime.date(y, m, dd)
        except ValueError as e:
            sys.exit(f"--date must be a real calendar date (YYYY-MM-DD): {e}")
    origin_off = a.origin_utc_offset if a.origin_utc_offset is not None else a.utc_offset
    tz_shift = a.utc_offset - origin_off
    if a.date and tz_shift:
        print(f"time zone: candidates are {tz_shift:+g} h from the origin; "
              f"arrivals below are LOCAL TIME AT THE STOP\n")

    rows, failed = [], []
    for name, la, lo in cands:
        try:
            trip = route([o, (la, lo), d], a.costing)
        except Exception as e:                       # public endpoint; keep going
            failed.append((name, f"{type(e).__name__}: {e}"))
            continue
        (t1, d1), (t2, d2) = legs_of(trip)[:2]
        total = t1 + t2
        row = {
            "stop": name, "lat": la, "lon": lo,
            "leg1_hours": round(t1, 2), "leg1_miles": round(d1, 1),
            "leg2_hours": round(t2, 2), "leg2_miles": round(d2, 1),
            "total_hours": round(total, 2),
            "detour_min": round((total - base) * 60),
            "share_of_trip": round(t1 / total, 3) if total else None,
            "roads_seen_best_effort": roads_seen(trip),
        }
        if a.date:
            # depart is origin-local; add the zone shift so arrival is local AT THE STOP,
            # the only clock that can legitimately be compared with the stop's sunset
            arrive = a.depart + t1 * (1 + a.break_frac) + tz_shift
            # Advance the solar date with the arrival and compare against the wrapped
            # clock. Using the departure date's sunset against an unwrapped hour-25
            # arrival reported -7.5 hours of daylight left instead of +16.5 -- a 24-hour
            # error whose sign looked plausible enough to go unnoticed.
            day_off = int(math.floor(arrive / 24.0))
            local = arrive - 24.0 * day_off
            sol = datetime.date(y, m, dd) + datetime.timedelta(days=day_off)
            ss = sunset(la, lo, sol.year, sol.month, sol.day, a.utc_offset)
            row.update(arrive_local=hhmm(local),
                       sunset_local=hhmm(ss) if ss is not None else "--",
                       arrive_day_offset=day_off,
                       arrive_next_day=day_off >= 1,
                       daylight_left_hours=round(ss - local, 2) if ss is not None else None)
        rows.append(row)
        time.sleep(0.6)

    rows.sort(key=lambda r: r["detour_min"])
    hdr = f"{'stop':<28}{'leg1':>7}{'leg2':>7}{'total':>7}{'detour':>8}{'share':>7}"
    if a.date:
        hdr += f"{'arrive':>8}{'sunset':>8}{'light':>7}"
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        line = (f"{r['stop'][:27]:<28}{r['leg1_hours']:>7.2f}{r['leg2_hours']:>7.2f}"
                f"{r['total_hours']:>7.2f}{r['detour_min']:>+8d}{r['share_of_trip']:>7.2f}")
        if a.date:
            dl = r["daylight_left_hours"]
            line += (f"{r['arrive_local']:>9}{r['sunset_local']:>8}"
                     + (f"{dl:>7.2f}" if dl is not None else f"{'n/a':>7}"))
        print(line)

    if failed:
        print("\nFAILED (report these, do not silently drop them):")
        for n, e in failed:
            print(f"  {n}: {e}")

    pathlib.Path(a.out).write_text(json.dumps({
        "engine": "valhalla-public", "costing": a.costing,
        "traffic_model": False, "direct_hours": round(base, 2),
        "depart_local": a.depart, "break_frac": a.break_frac,
        "date": a.date, "rows": rows, "failed": failed,
    }, indent=2))
    print(f"\nwrote {a.out}  ({len(rows)} routed, {len(failed)} failed)")
    print("Provenance, so these get labelled correctly downstream:")
    print("  leg1/leg2/total/detour/share  MEASURED   routed, one engine, free-flow")
    print("                                           (no traffic model -- quote as a floor)")
    print(f"  arrive                        DERIVED    leg1 + {a.break_frac:.0%} break assumption"
          + (f" {tz_shift:+g} h zone" if a.date and tz_shift else ""))
    print("  sunset                        CALCULATED NOAA solar position, approximate")
    if not rows:
        sys.exit("no candidate produced a usable comparison")


if __name__ == "__main__":
    main()
