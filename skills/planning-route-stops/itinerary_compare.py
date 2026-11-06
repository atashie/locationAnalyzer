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
import datetime
import hashlib
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.request

ROUTE_URL = "https://valhalla1.openstreetmap.de/route"
UA = "planning-route-stops/itinerary_compare (+https://github.com/anthropics/skills)"
RANK_WORDS = {"recommended", "recommend", "best", "winner", "preferred", "optimal",
              "top", "first-choice", "the-plan", "primary"}


# ---------------------------------------------------------------- routing

_CACHE_DIR = None
_CACHE_STATS = {"hit": 0, "miss": 0, "bad": 0}
_CACHE_VERSION = 2          # bump when the request body or response handling changes


def _cache_key(body):
    """Key the whole request, not a summary of it.

    Keying only coordinates and costing meant changing ROUTE_URL or directions_options
    silently reused answers from the old endpoint or the old units.
    """
    raw = json.dumps({"v": _CACHE_VERSION, "url": ROUTE_URL, "body": body},
                     separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _usable_trip(payload):
    """Does this response actually contain a routed trip?

    A 200 carrying {"error": ...} is not a route, and caching one makes every later run
    return the same non-answer without ever retrying.
    """
    try:
        trip = payload["trip"]
        return (bool(trip["legs"])
                and "time" in trip["summary"] and "length" in trip["summary"]
                and all("shape" in leg for leg in trip["legs"]))
    except (KeyError, TypeError):
        return False


def _post(points, costing, timeout=120, tries=3):
    """Route a waypoint sequence, reusing a cached response when one exists.

    Only the coordinates and costing determine a route, so editing a dwell time or a
    facility's hours should not re-request anything. Without this, changing one opening
    time re-routed all eight requests -- the network is far and away the dominant cost
    here, and the geometry work is milliseconds beside it.
    """
    body = {
        "locations": [{"lat": p[0], "lon": p[1]} for p in points],
        "costing": costing,
        "directions_options": {"units": "miles"},
    }
    key = _cache_key(body)
    path = os.path.join(_CACHE_DIR, key + ".json") if _CACHE_DIR else None

    if path and os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as fh:
                cached = json.load(fh)
            if _usable_trip(cached):
                _CACHE_STATS["hit"] += 1
                return cached
            raise ValueError("cached entry has no usable trip")
        except (ValueError, OSError) as exc:
            # A truncated or non-route body is a miss, never a hard failure.
            _CACHE_STATS["bad"] += 1
            print(f"  cache entry {key[:8]} unusable ({exc}); re-requesting")

    req = urllib.request.Request(
        ROUTE_URL, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "User-Agent": UA})
    last = None
    out = None
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                out = json.load(r)
            break
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError,
                ValueError) as exc:
            last = exc
            if attempt < tries - 1:
                time.sleep(2 + 2 * attempt)
    if out is None:
        raise RuntimeError(f"routing failed after {tries} attempts: {last}")
    # Be polite to a public endpoint -- but only when a request was actually sent. This
    # used to sit in the caller's loop, so a fully warm run slept 6.4 s for nothing.
    time.sleep(0.8)
    if not _usable_trip(out):
        raise RuntimeError(f"routing returned no usable trip: "
                           f"{json.dumps(out)[:200]}")
    _CACHE_STATS["miss"] += 1

    # Persisting is best-effort and deliberately outside the retry loop: a read-only
    # cache directory once turned three *successful* responses into three more requests
    # and then a hard failure.
    if path:
        try:
            os.makedirs(_CACHE_DIR, exist_ok=True)
            tmp = path + f".{os.getpid()}.tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(out, fh)
            os.replace(tmp, path)            # atomic: no half-written entry to read back
        except OSError as exc:
            print(f"  note: could not cache response ({exc}); continuing")
    return out


def _num(errs, where, value, lo, hi):
    """Coerce to float and range-check, collecting the error instead of raising.

    Validation that crashes is not validation: a stop of `null` or a latitude of "north"
    used to come out as a bare TypeError/ValueError from inside the checker.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        errs.append(f"{where}: expected a number, got {type(value).__name__}")
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        errs.append(f"{where}: {value!r} is not a number")
        return None
    if not math.isfinite(v):
        errs.append(f"{where}: {value!r} is not finite")
        return None
    if not lo <= v <= hi:
        errs.append(f"{where}: {v} is outside [{lo}, {hi}]")
        return None
    return v


def _check_schedule(errs, where, fac):
    times = {}
    for field in ("open", "close", "last_entry"):
        raw = fac.get(field)
        if raw in (None, ""):
            continue
        if not isinstance(raw, str) or not re.fullmatch(r"\d{1,2}:\d{2}", raw.strip()):
            errs.append(f"{where}: {field}={raw!r} is not HH:MM")
            continue
        hh, mm = (int(x) for x in raw.split(":"))
        if hh > 23 or mm > 59:
            errs.append(f"{where}: {field}={raw!r} is not a real clock time")
            continue
        times[field] = hh + mm / 60.0
    if "days" in fac:
        try:
            parse_days(fac["days"])
        except (ValueError, AttributeError, TypeError) as exc:
            errs.append(f"{where}: days={fac.get('days')!r} -- {exc}")
    if ("open" in times) != ("close" in times):
        errs.append(f"{where}: give both open and close, or neither")
    if "last_entry" in times and "open" in times and "close" in times:
        o, c, li = times["open"], times["close"], times["last_entry"]
        span = c + 24.0 if c <= o else c
        li_abs = li if li >= o else li + 24.0
        if not o <= li_abs <= span:
            errs.append(f"{where}: last_entry {fac['last_entry']} is outside "
                        f"{fac['open']}-{fac['close']}")


def validate_spec(spec, date_str):
    """Fail on everything checkable before spending a single request.

    A bad stop key or a malformed date used to surface after seven routing calls; the
    first version of this checker then crashed on the malformed input it was meant to
    report.
    """
    errs = []
    if not isinstance(spec, dict):
        sys.exit("spec must be a JSON object")
    for side in ("origin", "dest"):
        node = spec.get(side)
        if not isinstance(node, dict):
            errs.append(f"{side} must be an object with lat and lon")
            continue
        _num(errs, f"{side}.lat", node.get("lat"), -90, 90)
        _num(errs, f"{side}.lon", node.get("lon"), -180, 180)

    stops = spec.get("stops")
    if not isinstance(stops, dict):
        errs.append("stops must be an object of stop-key -> stop")
        stops = {}
    for key, st in stops.items():
        if not isinstance(st, dict):
            errs.append(f"stop '{key}' must be an object, got {type(st).__name__}")
            continue
        _num(errs, f"stop '{key}'.lat", st.get("lat"), -90, 90)
        _num(errs, f"stop '{key}'.lon", st.get("lon"), -180, 180)
        if "dwell_min" in st:
            _num(errs, f"stop '{key}'.dwell_min", st["dwell_min"], 0, 24 * 60)
        if "utc_offset" in st:
            _num(errs, f"stop '{key}'.utc_offset", st["utc_offset"], -12, 14)
        if "cost_usd" in st:
            _num(errs, f"stop '{key}'.cost_usd", st["cost_usd"], 0, 1e6)
        _check_schedule(errs, f"stop '{key}' (top level)", st)
        facs = st.get("facilities", [])
        if not isinstance(facs, list):
            errs.append(f"stop '{key}'.facilities must be a list")
            continue
        for fac in facs:
            if not isinstance(fac, dict):
                errs.append(f"stop '{key}': each facility must be an object")
                continue
            _check_schedule(errs, f"stop '{key}' facility '{fac.get('name','?')}'", fac)

    options = spec.get("options")
    if not isinstance(options, dict) or not options:
        errs.append("options must be a non-empty object of option-key -> option")
        options = {}
    for okey, opt in options.items():
        if not isinstance(opt, dict):
            errs.append(f"option '{okey}' must be an object")
            continue
        seq = opt.get("stops")
        if not isinstance(seq, list) or not seq:
            errs.append(f"option '{okey}' needs a non-empty 'stops' list")
            seq = []
        missing = [s for s in seq if s not in stops]
        if missing:
            errs.append(f"option '{okey}' references unknown stops: {missing}")
        if "depart_h" in opt:
            _num(errs, f"option '{okey}'.depart_h", opt["depart_h"], 0, 24)
        dw = opt.get("dwell_min", {})
        if not isinstance(dw, dict):
            errs.append(f"option '{okey}'.dwell_min must be an object of stop -> minutes")
        else:
            for s, v in dw.items():
                if s not in seq:
                    errs.append(f"option '{okey}' overrides dwell for '{s}', "
                                f"which it does not visit")
                _num(errs, f"option '{okey}'.dwell_min['{s}']", v, 0, 24 * 60)

    if date_str:
        try:
            datetime.date(*(int(x) for x in str(date_str).split("-")))
        except Exception:
            errs.append(f"--date {date_str!r} is not YYYY-MM-DD")
    if errs:
        sys.exit("spec validation failed, before any routing request:\n  - "
                 + "\n  - ".join(errs))


def decode_polyline6(encoded):
    """Valhalla shapes are precision 6, not the usual 5. Decoding at 5 scales every
    coordinate down by ten, which on a blank map looks like a plausible route somewhere
    else entirely -- which is why the projection is asserted numerically.

    Raises ValueError with a position on a truncated or out-of-charset string rather than
    the bare IndexError the obvious implementation gives you.
    """
    coords, lat, lon, i = [], 0, 0, 0
    n = len(encoded)
    while i < n:
        start = i
        for axis in range(2):
            shift, result = 0, 0
            while True:
                if i >= n:
                    raise ValueError(
                        f"truncated polyline: ran out of input at {i} decoding the "
                        f"{'latitude' if axis == 0 else 'longitude'} chunk starting at {start}")
                b = ord(encoded[i]) - 63
                if b < 0 or b > 63:
                    raise ValueError(
                        f"bad polyline character {encoded[i]!r} (0x{ord(encoded[i]):02x}) "
                        f"at {i}: expected printable ASCII 63..126")
                if shift > 30:               # a 7th byte would overflow a 32-bit delta
                    raise ValueError(f"polyline chunk at {start} exceeds 7 bytes; "
                                     f"input is probably not an encoded polyline")
                i += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            delta = ~(result >> 1) if result & 1 else (result >> 1)
            if axis == 0:
                lat += delta
            else:
                lon += delta
        coords.append((lat / 1e6, lon / 1e6))
    return coords


# ---------------------------------------------------------------- geometry

def rdp(points, epsilon, kx=1.0):
    """Iterative Ramer-Douglas-Peucker. Recursion blows the stack on long routes.

    Distance is to the replacement *segment*, not to the infinite line through its
    endpoints. The difference only shows up where a path doubles back -- but there it is
    severe: [(0,0), (2,0), (1,0)] has the middle point a full unit beyond the segment,
    and the infinite-line form measures it as zero and drops it at any epsilon.

    kx scales the x axis (longitude) so epsilon means the same distance in both
    directions. At 33 deg N, leaving it at 1.0 exaggerates east-west distance by 19%.
    """
    if len(points) < 3:
        return list(points)
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        lo, hi = stack.pop()
        if hi <= lo + 1:
            continue
        ay, ax = points[lo][0], points[lo][1] * kx
        by, bx = points[hi][0], points[hi][1] * kx
        dx, dy = bx - ax, by - ay
        den = dx * dx + dy * dy
        worst_d, worst_i = -1.0, -1
        for i in range(lo + 1, hi):
            py, px = points[i][0], points[i][1] * kx
            if den == 0.0:
                d = math.hypot(px - ax, py - ay)
            else:
                t = ((px - ax) * dx + (py - ay) * dy) / den
                t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)   # clamp to the segment
                d = math.hypot(px - (ax + t * dx), py - (ay + t * dy))
            if d > worst_d:
                worst_d, worst_i = d, i
        if worst_d > epsilon:
            keep[worst_i] = True
            stack.append((lo, worst_i))
            stack.append((worst_i, hi))
    return [p for p, k in zip(points, keep) if k]


def simplify_route(legs_shapes, epsilon, cap, kx=1.0):
    """One flat, de-duplicated, simplified polyline for the whole option."""
    if not (math.isfinite(epsilon) and epsilon > 0):
        raise ValueError(f"rdp epsilon must be finite and positive, got {epsilon!r}")
    if cap < 2:
        raise ValueError(f"max-points cap must be >= 2, got {cap!r}")
    pts = []
    for shape in legs_shapes:
        for p in decode_polyline6(shape):
            if not pts or (abs(p[0] - pts[-1][0]) > 1e-9 or abs(p[1] - pts[-1][1]) > 1e-9):
                pts.append(p)
    eps = epsilon
    out = rdp(pts, eps, kx)
    # Tighten until it fits the cap; a map at state scale needs far fewer points than
    # people expect, and an oversized array is the thing that bloats a baked page.
    # Bounded so a pathological cap cannot spin: the loop can only run while eps < 1 deg.
    while len(out) > cap and eps < 1.0:
        eps *= 1.6
        out = rdp(pts, eps, kx)
    if len(out) > cap:
        print(f"  note: could not reach the {cap}-point cap; kept {len(out)} at eps={eps:.4f}")
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

    NOAA solar position evaluated once at the date's *UTC* midnight rather than iterated
    to each event. Measured against an iterated solution at 31 N, -82.27, UTC-5 in late
    November, that costs ~26 s on sunrise and ~13 s on sunset -- well inside the minute
    this is ever quoted to, and far finer than any arrival time it is compared against.
    Signs follow NOAA: western (negative) longitude delays UTC solar noon, a negative UTC
    offset converts it back to an earlier local hour."""
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

def _hm_parts(sec):
    """Round to the nearest minute first, then split. Truncating seconds showed 60.8 min
    as "1h00"; and int(-6.9)//3600 made a 7-second negative render as "-1h59"."""
    m = int(round(sec / 60.0))
    sign = "-" if m < 0 else ""
    m = abs(m)
    return sign, m // 60, m % 60

def hm(seconds):
    sg, h, m = _hm_parts(seconds)
    return f"{sg}{h}h{m:02d}"


def plus_min(seconds):
    s = int(round(seconds / 60.0))
    return f"{s:+d} min"


def clock(h):
    h = h % 24
    total = int(round(h * 60))
    return f"{total // 60 % 24:02d}:{total % 60:02d}"


# ---------------------------------------------------------------- opening hours

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def parse_days(spec):
    """'daily' | 'Mon-Thu' | 'Mon,Fri-Sun' -> set of weekday indices (Mon=0)."""
    if not spec or spec.strip().lower() in ("daily", "mon-sun", "everyday", "all"):
        return set(range(7))
    out = set()
    for part in spec.split(","):
        part = part.strip().lower()[:]
        if "-" in part:
            a, b = (p.strip()[:3] for p in part.split("-", 1))
            if a not in DAYS or b not in DAYS:
                raise ValueError(f"unknown day range {part!r}")
            i, j = DAYS.index(a), DAYS.index(b)
            out.update((i + k) % 7 for k in range((j - i) % 7 + 1))
        else:
            d = part[:3]
            if d not in DAYS:
                raise ValueError(f"unknown day {part!r}")
            out.add(DAYS.index(d))
    return out


def hhmm_to_h(s):
    hh, mm = s.split(":")
    return int(hh) + int(mm) / 60.0


def facility_state(fac, arrive_h, depart_h, weekday):
    """Where a stop's halt sits against one facility's published hours.

    arrive_h/depart_h are local decimal hours on the arrival day; values >= 24 mean the
    halt has rolled past midnight and are handled by the same wrapped-interval logic.

    Returns (verdict, detail, usable_min). Verdicts:
      always   no hours to miss -- an outdoor space, a 24h pump
      open     open on arrival (usable_min says how much of the halt it stays open)
      opens    shut on arrival but opens during the halt, with the wait
      shut     shut for the whole halt, with when it opens
      closed   not open at all on this weekday
      unknown  no machine-readable hours given; callers must not render this as "shut"
    """
    if fac.get("always"):
        return "always", fac.get("note", "no fixed hours"), (depart_h - arrive_h) * 60.0
    if "open" not in fac or "close" not in fac:
        return "unknown", "hours not published in a form this could check", None
    try:
        days = parse_days(fac.get("days", "daily"))
    except ValueError as exc:
        return "unknown", str(exc), None

    # Last entry is a different fact from closing time, and it is the one that decides
    # whether you get in. A zoo closing at 17:00 with last entry 15:30 is shut to a new
    # arrival at 16:00 while still being open to everyone already inside.
    last_in = hhmm_to_h(fac["last_entry"]) if fac.get("last_entry") else None

    o, c = hhmm_to_h(fac["open"]), hhmm_to_h(fac["close"])
    span = (c + 24.0) if c <= o else c       # 22:00-02:00 -> (22, 26); 00:00-00:00 -> 24 h

    # Every opening interval that could touch the halt, expressed in arrival-day hours.
    #
    # The first version of this generated exactly three candidate days and stopped at the
    # first match, which was wrong three ways: a halt longer than a day saw only part of
    # its open time, an unknown weekday dropped the overnight tail entirely, and the
    # "closed today" branch was unreachable once yesterday's interval existed.
    lo_day = int(math.floor(arrive_h / 24.0)) - 1
    hi_day = int(math.floor(depart_h / 24.0)) + 1
    intervals = []
    for d in range(lo_day, hi_day + 1):
        if weekday is not None and (weekday + d) % 7 not in days:
            continue                         # unknown weekday: no day filtering at all
        intervals.append((o + 24.0 * d, span + 24.0 * d))
    intervals.sort()

    def entry_cut(lo):
        """Last entry placed on the same day as this interval's opening."""
        return None if last_in is None else last_in + (lo - o)

    def open_minutes(frm):
        """Open time inside [frm, depart_h], summed over every interval, not just one."""
        return sum(max(0.0, min(depart_h, hi) - max(frm, lo))
                   for lo, hi in intervals) * 60.0

    covering = [(lo, hi) for lo, hi in intervals if lo <= arrive_h < hi]
    if covering:
        lo, hi = covering[0]
        li = entry_cut(lo)
        if li is not None and arrive_h >= li:
            return ("shut",
                    f"too late to get in: last entry {clock(li)}, shuts {clock(hi)}", 0.0)
        usable = open_minutes(arrive_h)
        entry = f", last entry {clock(li)}" if li is not None else ""
        tail = (f" -- only {int(round(usable))} min of your halt"
                if usable < (depart_h - arrive_h) * 60.0 - 0.5 else "")
        return "open", f"open until {clock(hi)}{entry}{tail}", usable

    later = [(lo, hi) for lo, hi in intervals if lo > arrive_h]
    if later and later[0][0] < depart_h:
        lo, hi = later[0]
        li = entry_cut(lo)
        if li is not None and li >= depart_h:
            return ("shut",
                    f"opens {clock(lo)} but last entry is {clock(li)}, after you leave", 0.0)
        usable = open_minutes(lo)
        wait = (lo - arrive_h) * 60.0
        return ("opens",
                f"opens {clock(lo)}, {int(round(wait))} min into the halt "
                f"({int(round(usable))} min usable)", usable)

    # Nothing open during the halt. Distinguish "shut right now" from "shut all day",
    # which is a different thing to tell a traveller and was being conflated.
    if weekday is not None and weekday not in days:
        return "closed", f"closed {DAYS[weekday].capitalize()}", 0.0
    if later:
        lo = later[0][0]
        return ("shut",
                f"opens {clock(lo)}, {int(round((lo - depart_h) * 60.0))} min after you leave",
                0.0)
    past = [hi for lo, hi in intervals if hi <= arrive_h]
    if past:
        return "shut", f"shut at {clock(max(past))}", 0.0
    return "shut", "not open during your halt", 0.0


def stop_hours_report(stop, arrive_h, dwell_min, weekday):
    """Per-facility verdicts plus a single rollup for the stop."""
    facs = stop.get("facilities")
    if not facs:
        # A stop given without a facilities list still has to keep whatever it declared:
        # dropping "always" turned a 24 h fuel stop into "nothing open" in one run.
        fallback = {k: stop[k] for k in
                    ("open", "close", "last_entry", "days", "always", "note", "url", "status")
                    if k in stop}
        fallback.setdefault("name", stop.get("name", "the stop"))
        facs = [fallback]
    depart_h = arrive_h + dwell_min / 60.0
    rows = []
    for fac in facs:
        verdict, detail, usable = facility_state(fac, arrive_h, depart_h, weekday)
        rows.append({"name": fac.get("name", "?"), "verdict": verdict, "detail": detail,
                     "usable_min": None if usable is None else round(usable),
                     "url": fac.get("url"), "status": fac.get("status", "standing")})
    usable = [r for r in rows if r["verdict"] in ("always", "open", "opens")]
    unknown = [r for r in rows if r["verdict"] == "unknown"]
    missed = [r for r in rows if r["verdict"] in ("shut", "closed")]
    if not rows:
        roll = "unknown"
    elif usable and any(r["verdict"] in ("always", "open") for r in usable):
        roll = "open-on-arrival"
    elif usable:
        roll = "opens-during"
    elif unknown:
        # Nothing is known to be open, but something is merely unchecked -- that is not
        # the same claim as "nothing here is open", and must not render as one.
        roll = "unknown"
    else:
        roll = "nothing-open"
    return {"rollup": roll, "facilities": rows,
            "usable": len(usable), "missed": len(missed), "unknown": len(unknown)}


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
                     "cost_usd": 0,
                     "facilities": [
                       {"name": "Sunoco West pumps", "always": true,
                        "note": "24 h", "status": "standing"},
                       {"name": "Pantry + restrooms", "days": "daily",
                        "open": "07:00", "close": "23:00", "status": "standing"},
                       {"name": "Sombrero Tower", "days": "Mon-Thu",
                        "open": "11:00", "close": "19:00", "status": "standing"},
                       {"name": "Reptile Lagoon", "days": "Mon,Fri-Sun",
                        "open": "10:00", "close": "19:00", "status": "standing"}]},
      "okefenokee": {"name": "Okefenokee Swamp Park", "where": "Waycross, GA",
                     "lat": 31.0578, "lon": -82.2725, "dwell_min": 80,
                     "cost_usd": 98, "url": "https://...",
                     "facilities": [
                       {"name": "Train, boardwalk, reptile show", "days": "daily",
                        "open": "09:00", "close": "17:00", "status": "standing"}]}
    },
    "options": {
      "fewest-stops":  {"label": "Fewest stops, earliest arrival",
                        "stops": ["sob"]},
      "one-big-thing": {"label": "One big thing: the swamp",
                        "stops": ["sob", "okefenokee"],
                        "dwell_min": {"okefenokee": 90}}
    }
  }

  A stop is a SITE, and a site has facilities on different schedules -- pumps open 24 h
  while the tower opens at 11:00 and the best attraction is shut on Wednesdays. Model
  facilities, or "open" and "closed" will both be wrong. Each facility takes either
  "always": true (no fixed hours: an outdoor space, a 24 h pump) or "days" + "open" +
  "close". "days" accepts "daily", "Mon-Thu", "Mon,Fri-Sun". Omit the hours entirely and
  the facility reports as unknown rather than being quietly assumed open.

  Pass --date, or day-of-week closures cannot be checked at all.

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
                    help="UTC offset at the DESTINATION, e.g. -5 for US Eastern in November. "
                         "Also the default for any stop that does not set its own.")
    ap.add_argument("--origin-utc-offset", type=float, default=None,
                    help="UTC offset at the ORIGIN. Defaults to --utc-offset. Set it when the "
                         "journey crosses a time zone, or every arrival clock is wrong by the "
                         "difference. Stops may override individually with a utc_offset field.")
    ap.add_argument("--costing", default="auto",
                    help="auto | bicycle | pedestrian | truck | motor_scooter")
    ap.add_argument("--rdp-epsilon", type=float, default=0.004,
                    help="initial RDP tolerance in degrees of latitude, longitude scaled "
                         "by cos(mean lat) so it is near-isotropic (default 0.004, ~440 m)")
    ap.add_argument("--max-points", type=int, default=120,
                    help="per-option geometry point cap (default 120)")
    ap.add_argument("--out", help="write the full measured JSON here")
    ap.add_argument("--cache-dir", default=".route-cache",
                    help="directory for cached routing responses, keyed on coordinates and "
                         "costing (default .route-cache). Editing dwell times or hours then "
                         "costs no requests at all. Pass an empty string to disable.")
    a = ap.parse_args()

    global _CACHE_DIR
    _CACHE_DIR = a.cache_dir or None

    spec = json.load(open(a.spec, encoding="utf-8"))
    validate_spec(spec, a.date)
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

    origin_off = a.utc_offset if a.origin_utc_offset is None else a.origin_utc_offset
    zones = {float(st.get("utc_offset", a.utc_offset)) for st in stops.values()}
    zones |= {origin_off, a.utc_offset}
    if len(zones) > 1:
        print(f"time zones in play (UTC offsets): {sorted(zones)} -- each stop's hours are "
              f"checked against its own\nlocal clock, and each arrival below is shown in "
              f"local time at that stop.\n")

    sunset_h, weekday = None, None
    if a.date:
        y, m, dd = (int(x) for x in a.date.split("-"))
        _, _, sunset_h = sun_events(d[0], d[1], y, m, dd, a.utc_offset)
        weekday = datetime.date(y, m, dd).weekday()
        print(f"travel date {a.date} is a {DAYS[weekday].capitalize()} -- "
              f"day-of-week closures are checked against it\n")
    else:
        print("no --date given: day-of-week closures CANNOT be checked, so every verdict\n"
              "below ignores which day it is. Each schedule row carries weekday_checked\n"
              "false so nothing downstream mistakes it for a checked result. Pass --date.\n")

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

        # Corridors differ in what they offer at dawn: one built on 24 h fuel and
        # outdoor space rewards a 04:45 start, one built on ticketed attractions that
        # open at 09:00 punishes it. Comparing them fairly means letting each option
        # state its own departure.
        depart = float(opt.get("depart_h", a.depart))

        # DERIVED: departure + measured legs + spec dwell times.
        #
        # t is the ORIGIN's wall clock. Two conversions then matter and were both wrong
        # once: a stop in another time zone keeps its own hours (so the clock used for its
        # opening-hours check must be shifted by its offset), and t accumulates past 24 on
        # a long day, so the weekday has to advance with it or a 01:00 arrival is checked
        # against the previous day's hours.
        t = depart
        schedule = []
        for i, s in enumerate(seq_keys):
            t += legs[i] / 3600.0
            local = t + (float(stops[s].get("utc_offset", a.utc_offset)) - origin_off)
            day_off = int(local // 24)
            local_wd = None if weekday is None else (weekday + day_off) % 7
            hours = stop_hours_report(stops[s], local - 24.0 * day_off, dwells[i], local_wd)
            schedule.append({"stop": s,
                             "arrive": clock(local), "arrive_h": round(local, 4),
                             "arrive_origin_clock": clock(t),
                             "utc_offset": float(stops[s].get("utc_offset", a.utc_offset)),
                             "day_offset": day_off, "weekday_checked": weekday is not None,
                             "dwell_min": dwells[i], "leg_s": legs[i], "hours": hours})
            t += dwells[i] / 60.0
        t += legs[-1] / 3600.0
        arrive_h = t + (a.utc_offset - origin_off)     # destination's own wall clock
        days_spanned = int(arrive_h // 24)
        shut_on_arrival = [r for r in schedule if r["hours"]["rollup"] == "nothing-open"]
        waits = [r for r in schedule if r["hours"]["rollup"] == "opens-during"]

        kx = math.cos(math.radians((o[0] + d[0]) / 2.0))
        geom, raw_n, eps_used = simplify_route(
            [leg["shape"] for leg in trip["legs"]], a.rdp_epsilon, a.max_points, kx)
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
            "depart_h": depart,
            "depart": clock(depart),
            "corridor": opt.get("corridor", ""),
            "arrive_h": round(arrive_h, 4),
            "arrive": clock(arrive_h),
            "days_spanned": days_spanned,
            "elapsed_s": total + sum(dwells) * 60.0,
            "schedule": schedule,
            "shut_on_arrival": [r["stop"] for r in shut_on_arrival],
            "opens_during_halt": [r["stop"] for r in waits],
            "geometry": geom,
            "geometry_raw_points": raw_n,
            "rdp_epsilon_used": eps_used,
        }
        if sunset_h is not None:
            # sunset is computed for the arrival date, which is not the departure date on
            # an itinerary that rolls past midnight
            if days_spanned and a.date:
                yy, mm, dd0 = (int(x) for x in a.date.split("-"))
                arr_date = datetime.date(yy, mm, dd0) + datetime.timedelta(days=days_spanned)
                _, _, ss = sun_events(d[0], d[1], arr_date.year, arr_date.month,
                                      arr_date.day, a.utc_offset)
            else:
                ss = sunset_h
            # High latitudes have dates with no sunset at all; formatting None crashed.
            results[key]["sunset"] = clock(ss) if ss is not None else "--"
            results[key]["after_sunset"] = (
                None if ss is None else (arrive_h - 24.0 * days_spanned) > ss)
            results[key]["arrives_next_day"] = bool(days_spanned)

    lats = [p[0] for p in all_pts]
    lons = [p[1] for p in all_pts]
    bbox = {"min_lat": min(lats), "max_lat": max(lats),
            "min_lon": min(lons), "max_lon": max(lons)}

    w = max(len(v["label"]) for v in results.values())
    cw = max([len(v["corridor"]) for v in results.values()] + [8])
    hdr = (f"{'option':<{w}}  {'corridor':<{cw}} {'leave':>5} {'drive':>6} {'added':>8} "
           f"{'miles':>6} {'stops':>5} {'dwell':>6} {'elapsed':>8} {'cost':>7} {'arrive':>7}")
    if sunset_h is not None:
        hdr += f"  {'sunset':>7}"
    print(hdr)
    print("-" * len(hdr))
    for key, v in sorted(results.items(), key=lambda kv: kv[1]["total_s"]):
        line = (f"{v['label']:<{w}}  {v['corridor']:<{cw}} {v['depart']:>5} "
                f"{hm(v['total_s']):>6} {plus_min(v['detour_s']):>8} "
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

    # The check that matters: does the derived arrival land inside the published hours?
    print("\narrival vs published hours (DERIVED arrival against stated hours):")
    MARK = {"always": "  ", "open": "  ", "opens": " ~", "shut": " !",
            "closed": " X", "unknown": " ?"}
    any_dead = False
    for key, v in results.items():
        print(f"  {v['label']}")
        for row in v["schedule"]:
            h = row["hours"]
            flag = {"open-on-arrival": "", "opens-during": "  <- opens mid-halt",
                    "nothing-open": "  <- NOTHING OPEN ON ARRIVAL",
                    "unknown": "  <- hours unknown"}[h["rollup"]]
            print(f"    {row['arrive']}  {stops[row['stop']].get('name', row['stop'])}"
                  f"  ({int(row['dwell_min'])} min){flag}")
            for f in h["facilities"]:
                print(f"      {MARK[f['verdict']]} {f['name']:<42} {f['detail']}")
        if v["shut_on_arrival"]:
            any_dead = True
    if any(v.get("arrives_next_day") for v in results.values()):
        print("\n  note: at least one option arrives after midnight. Weekday and sunset")
        print("        advance with it, but a single --utc-offset applies throughout, so")
        print("        crossing a time zone shifts every hours verdict by an hour.")
    if any_dead:
        print("\n  ! At least one stop has nothing open when you get there. Either move the")
        print("    stop, change the departure hour, or say plainly on the page what IS")
        print("    reachable at that time -- a 24h pump, an outdoor space, a view.")

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

    tot = _CACHE_STATS["hit"] + _CACHE_STATS["miss"]
    if _CACHE_DIR and tot:
        print(f"\nrouting: {_CACHE_STATS['miss']} request(s) sent, {_CACHE_STATS['hit']} "
              f"served from {_CACHE_DIR}")

    print("\nProvenance, so these get labelled correctly downstream:")
    print("  drive/added/miles/legs       MEASURED   routed, one engine, free-flow")
    print("                                          (no traffic model -- quote as a floor)")
    print("  elapsed/arrive               DERIVED    departure hour + measured legs + spec dwells")
    print("  leave                        GIVEN      per-option depart_h, else --depart")
    print("  cost                         DERIVED    sum of stops[].cost_usd as given in the spec")
    if a.date:
        print("  sunset                       CALCULATED NOAA solar position, approximate")
    print("\nThe traveller weighs these; you measured them. Ship the options, not a verdict.")


if __name__ == "__main__":
    main()
