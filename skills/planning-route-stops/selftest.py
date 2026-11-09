#!/usr/bin/env python3
"""Invariants for the measuring tools. No network, no fixtures -- run it anywhere.

    python selftest.py

Every case here is a defect that actually shipped. Two adversarial reviews of this skill's
tooling returned 20 findings; twelve of them had already reached a published page as
confident statements -- an unknown opening time rendered as "nothing here is open", a
separation figure that changed with list order, a drive time a minute short, two 17-mile
stretches of interstate silently deleted from a map.

None of them were hard to catch. They were never looked for. Run this after touching
itinerary_compare.py or basemap.py, and add a case whenever you fix something new: a fix
without a failing test beside it is a fix that comes back.
"""
import importlib.util
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ic = _load("ic", "itinerary_compare.py")
bm = _load("bm", "basemap.py")

CASES = []


def case(group, name):
    def deco(fn):
        CASES.append((group, name, fn))
        return fn
    return deco


# ------------------------------------------------------------------ opening hours

@case("hours", "unknown hours are not a claim that nothing is open")
def _():
    r = ic.stop_hours_report({"name": "x", "facilities": [{"name": "f"}]}, 10.0, 30, 2)
    assert r["rollup"] == "unknown", r["rollup"]
    assert r["facilities"][0]["verdict"] == "unknown"


@case("hours", "a stop with no facilities keeps always/url/status")
def _():
    f = ic.stop_hours_report(
        {"name": "pump", "always": True, "url": "u", "status": "confirmed"},
        3.0, 15, 2)["facilities"][0]
    assert f["verdict"] == "always" and f["url"] == "u" and f["status"] == "confirmed", f


@case("hours", "the wait is measured from departure, not arrival")
def _():
    _, d, _ = ic.facility_state({"days": "daily", "open": "11:00", "close": "20:00"},
                                10.0, 10.5, 2)
    assert "30 min after you leave" in d, d


@case("hours", "overnight hours match on both sides of midnight")
def _():
    fac = {"days": "Fri", "open": "22:00", "close": "02:00"}
    assert ic.facility_state(fac, 23.0, 23.5, 4)[0] == "open"
    assert ic.facility_state(fac, 25.0, 25.5, 4)[0] == "open"      # 01:00 Saturday
    assert ic.facility_state(fac, 12.0, 13.0, 4)[0] == "shut"


@case("hours", "a weekday closure still closes")
def _():
    v, d, _ = ic.facility_state({"days": "Mon", "open": "09:00", "close": "17:00"},
                                10.0, 11.0, 4)
    assert v == "closed" and "Fri" in d, (v, d)


@case("hours", "last entry is binding, closing time is not")
def _():
    fac = {"days": "daily", "open": "09:00", "close": "17:00", "last_entry": "15:30"}
    assert ic.facility_state(fac, 14.0, 15.0, 2)[0] == "open"
    v, d, u = ic.facility_state(fac, 16.0, 17.0, 2)
    assert v == "shut" and "last entry" in d and u == 0.0, (v, d, u)


@case("hours", "open on arrival still reports how much of the halt is usable")
def _():
    _, d, u = ic.facility_state({"days": "daily", "open": "09:00", "close": "17:00"},
                                16.75, 18.0, 2)
    assert u == 15.0 and "15 min" in d, (d, u)


@case("hours", "wrapped weekday ranges parse")
def _():
    assert bm and ic.parse_days("Fri-Mon") == {4, 5, 6, 0}
    assert ic.parse_days("daily") == set(range(7))
    assert ic.parse_days("Mon,Fri-Sun") == {0, 4, 5, 6}


@case("hours", "a facility open all day is never 'shut'")
def _():
    for h in (0.0, 6.0, 12.0, 23.9):
        assert ic.facility_state({"always": True}, h, h + 0.5, 3)[0] == "always"


@case("hours", "overnight hours work with no weekday known")
def _():
    # the three-day candidate window used to drop yesterday's interval when weekday
    # was None, so a 24h-ish venue read "shut, opens in 1230 min"
    v, _, _ = ic.facility_state({"days": "daily", "open": "22:00", "close": "02:00"},
                                1.0, 1.5, None)
    assert v == "open", v


@case("hours", "closed-today is distinguished from shut-right-now")
def _():
    v, d, _ = ic.facility_state({"days": "Fri", "open": "09:00", "close": "17:00"},
                                10.0, 11.0, 5)
    assert v == "closed" and "Sat" in d, (v, d)


@case("hours", "usable minutes span every interval the halt touches")
def _():
    # a 24 h venue across midnight: 2 h of halt is 2 h of open time, not 1
    assert ic.facility_state({"days": "daily", "open": "00:00", "close": "00:00"},
                             23.0, 25.0, 2)[2] == 120.0
    # Friday 16:00 to Saturday 11:00 at a daily 09:00-17:00 venue: 1 h + 2 h
    assert ic.facility_state({"days": "daily", "open": "09:00", "close": "17:00"},
                             16.0, 35.0, 4)[2] == 180.0


@case("hours", "a halt longer than the candidate window still finds its opening")
def _():
    # Friday 10:00 to Monday 10:00 at a Monday-only venue
    v, _, u = ic.facility_state({"days": "Mon", "open": "09:00", "close": "17:00"},
                                10.0, 82.0, 4)
    assert v == "opens" and u == 60.0, (v, u)


@case("hours", "the no-facilities fallback honours last_entry too")
def _():
    r = ic.stop_hours_report(
        {"name": "zoo", "open": "09:00", "close": "17:00", "last_entry": "15:30"},
        16.0, 60, 2)
    assert r["rollup"] == "nothing-open", r["rollup"]


# ------------------------------------------------------------------ geometry

@case("geometry", "RDP keeps a point beyond the replacement segment")
def _():
    doubling_back = [(0.0, 0.0), (2.0, 0.0), (1.0, 0.0)]
    assert len(ic.rdp(doubling_back, 0.1)) == 3
    assert len(bm.rdp(doubling_back, 0.1)) == 3


@case("geometry", "RDP endpoints survive and order is preserved")
def _():
    pts = [(0.0, 0.0), (0.5, 0.01), (1.0, 0.0), (1.5, 0.02), (2.0, 0.0)]
    out = ic.rdp(pts, 0.5)
    assert out[0] == pts[0] and out[-1] == pts[-1]
    assert out == [p for p in pts if p in out]


@case("geometry", "RDP with a huge epsilon degenerates to the endpoints")
def _():
    pts = [(float(i), math.sin(i) * 0.1) for i in range(50)]
    assert ic.rdp(pts, 1e6) == [pts[0], pts[-1]]


@case("geometry", "longitude scaling changes which points survive, by ~1/cos(lat)")
def _():
    kx = math.cos(math.radians(33.0))                      # 0.8387 at 33 N
    span = [(33.0, 0.0), (33.0, 0.5), (33.0, 1.0)]
    assert len(ic.rdp(span, 1e-9)) == 2, "colinear points should collapse"
    # A bend displaced purely in LONGITUDE: unscaled its deviation measures 0.006 deg,
    # scaled it measures 0.006*kx = 0.0050. A tolerance between the two must keep the
    # point unscaled and drop it scaled. If both agree, kx never reached the distance.
    ew = [(33.0, 0.0), (33.5, 0.006), (34.0, 0.0)]
    tol = 0.0055
    unscaled = len(ic.rdp(ew, tol))
    scaled = len(ic.rdp(ew, tol, kx))
    assert unscaled == 3, unscaled
    assert scaled == 2, f"kx is not reaching the distance computation (got {scaled})"
    assert abs(kx - 0.8387) < 1e-3, kx


@case("geometry", "simplify_route rejects a non-positive or non-finite epsilon")
def _():
    for bad in (0.0, -1.0, float("nan"), float("inf")):
        try:
            ic.simplify_route([], bad, 10)
        except ValueError:
            continue
        raise AssertionError(f"epsilon {bad!r} was accepted")


@case("geometry", "simplify_route rejects a cap below two points")
def _():
    try:
        ic.simplify_route([], 0.004, 1)
    except ValueError:
        return
    raise AssertionError("cap of 1 was accepted")


@case("geometry", "a segment crossing the view with both ends outside is kept")
def _():
    saved = dict(bm.VIEW)
    bm.VIEW.update(min_lat=30.2, max_lat=36.5, min_lon=-85.2, max_lon=-78.3)
    try:
        assert len(bm.clip_runs([(29.0, -81.0), (37.0, -81.0)], pad=0.0)) == 1
        assert bm.clip_runs([(10.0, -81.0), (11.0, -81.0)], pad=0.0) == []
    finally:
        bm.VIEW.update(saved)


@case("geometry", "clipping never invents a point that was not on the line")
def _():
    saved = dict(bm.VIEW)
    bm.VIEW.update(min_lat=30.0, max_lat=36.0, min_lon=-85.0, max_lon=-79.0)
    try:
        ring = [(29.0, -84.0), (33.0, -83.0), (34.0, -82.0), (29.5, -80.0)]
        for run in bm.clip_runs(ring, pad=0.0):
            for p in run:
                assert p in ring, f"{p} is not an input vertex"
    finally:
        bm.VIEW.update(saved)


@case("geometry", "stitching joins fragments and loses none of them")
def _():
    hub = [[(0.0, 0.0), (1.0, 0.0)], [(1.0, 0.0), (2.0, 0.0)],
           [(1.0, 0.0), (1.0, 1.0)], [(1.0, 1.0), (1.0, 2.0)]]
    chains = bm.stitch(hub)
    joined = {tuple(p) for c in chains for p in c}
    original = {tuple(p) for seg in hub for p in seg}
    assert joined == original, joined ^ original
    assert len(chains) == 2, len(chains)


@case("geometry", "stitching a single fragment returns it unchanged")
def _():
    seg = [(0.0, 0.0), (1.0, 1.0)]
    assert bm.stitch([seg]) == [seg]


@case("geometry", "separation is measured to segments, not vertices")
def _():
    # two identical straight routes, one carrying an extra midpoint, must be 0 apart
    kx = math.cos(math.radians(33.0))

    def pt_seg(p, q1, q2):
        py, px = p[0], p[1] * kx
        ay, ax = q1[0], q1[1] * kx
        by, bx = q2[0], q2[1] * kx
        dx, dy = bx - ax, by - ay
        den = dx * dx + dy * dy
        if den == 0.0:
            return math.hypot(px - ax, py - ay)
        t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / den))
        return math.hypot(px - (ax + t * dx), py - (ay + t * dy))

    a = [(33.0, -84.0), (33.0, -82.0)]
    b = [(33.0, -84.0), (33.0, -83.0), (33.0, -82.0)]
    segs = list(zip(a, a[1:]))
    worst = max(min(pt_seg(p, q1, q2) for q1, q2 in segs) for p in b)
    assert worst < 1e-9, f"{worst*69:.1f} miles of artificial separation"


# ------------------------------------------------------------------ decoding

@case("decode", "a valid precision-6 polyline round-trips")
def _():
    def encode6(coords):
        out, plat, plon = [], 0, 0
        for lat, lon in coords:
            ilat, ilon = round(lat * 1e6), round(lon * 1e6)
            for delta in (ilat - plat, ilon - plon):
                v = ~(delta << 1) if delta < 0 else (delta << 1)
                while v >= 0x20:
                    out.append(chr((0x20 | (v & 0x1F)) + 63))
                    v >>= 5
                out.append(chr(v + 63))
            plat, plon = ilat, ilon
        return "".join(out)

    coords = [(35.9132, -79.0558), (34.4985, -79.3093), (30.8366, -83.9788),
              (0.0, 0.0), (-33.8688, 151.2093)]
    got = ic.decode_polyline6(encode6(coords))
    assert len(got) == len(coords)
    for (a, b), (c, d) in zip(got, coords):
        assert abs(a - c) < 1e-6 and abs(b - d) < 1e-6, ((a, b), (c, d))


@case("decode", "a truncated polyline raises ValueError, not IndexError")
def _():
    full = "_izlhA~p~iF_izlhA~p~iF"
    try:
        ic.decode_polyline6(full[:-1])
    except ValueError:
        return
    except IndexError:
        raise AssertionError("still raising a bare IndexError")
    raise AssertionError("truncated input decoded without complaint")


@case("decode", "an out-of-charset byte is rejected")
def _():
    try:
        ic.decode_polyline6("_izlhA\x01zz")
    except ValueError:
        return
    raise AssertionError("control character accepted")


@case("decode", "an over-long chunk is rejected before the eighth byte")
def _():
    try:
        ic.decode_polyline6("_" * 7 + "??")
    except ValueError:
        return
    raise AssertionError("8-byte chunk accepted")


# ------------------------------------------------------------------ formatting

@case("format", "durations round to the nearest minute rather than truncating")
def _():
    assert ic.hm(3648.2) == "1h01", ic.hm(3648.2)       # 60.8 min, once shown as 1h00
    assert ic.hm(3600) == "1h00"
    assert ic.hm(3629) == "1h00"
    assert ic.hm(3631) == "1h01"


@case("format", "a small negative does not render as a huge one")
def _():
    out = ic.hm(-6.9)
    assert out in ("0h00", "-0h00"), out                # once rendered "-1h59"
    assert ic.hm(-3660) == "-1h01", ic.hm(-3660)


@case("format", "clock wraps rather than printing hour 25")
def _():
    assert ic.clock(25.5) == "01:30", ic.clock(25.5)
    assert ic.clock(0.0) == "00:00"
    assert ic.clock(23.999) == "00:00" or ic.clock(23.999) == "23:60"


# ------------------------------------------------------------------ solar

@case("solar", "sunrise precedes noon precedes sunset, and the day is plausible")
def _():
    rise, noon, set_ = ic.sun_events(30.8366, -83.9788, 2026, 11, 25, -5)
    assert rise < noon < set_, (rise, noon, set_)
    assert 6.5 < rise < 7.5 and 17.0 < set_ < 18.0, (rise, set_)
    assert 9.5 < (set_ - rise) < 10.5, set_ - rise      # ~10 h of daylight in late Nov


@case("solar", "a southern-hemisphere November day is long, not short")
def _():
    rise, _, set_ = ic.sun_events(-33.8688, 151.2093, 2026, 11, 25, 11)
    assert (set_ - rise) > 13.5, set_ - rise


# ------------------------------------------------------------------ spec validation

@case("spec", "an option referencing an unknown stop fails before any request")
def _():
    spec = {"origin": {"lat": 1, "lon": 2}, "dest": {"lat": 3, "lon": 4},
            "stops": {"a": {"lat": 1, "lon": 2}},
            "options": {"x": {"stops": ["a", "ghost"]}}}
    try:
        ic.validate_spec(spec, "2026-11-25")
    except SystemExit as e:
        assert "ghost" in str(e), e
        return
    raise AssertionError("unknown stop key accepted")


@case("spec", "a malformed time or weekday range is caught")
def _():
    spec = {"origin": {"lat": 1, "lon": 2}, "dest": {"lat": 3, "lon": 4},
            "stops": {"a": {"lat": 1, "lon": 2, "facilities": [
                {"name": "f", "open": "9am", "close": "17:00", "days": "Funday"}]}},
            "options": {}}
    try:
        ic.validate_spec(spec, None)
    except SystemExit as e:
        msg = str(e).lower()
        assert "9am" in msg and "funday" in msg, e
        return
    raise AssertionError("malformed facility accepted")


@case("spec", "a well-formed spec passes silently")
def _():
    spec = {"origin": {"lat": 35.9, "lon": -79.0}, "dest": {"lat": 30.8, "lon": -83.9},
            "stops": {"a": {"lat": 34.0, "lon": -81.0, "facilities": [
                {"name": "f", "open": "09:00", "close": "17:00", "days": "Mon-Fri"}]}},
            "options": {"only": {"stops": ["a"]}}}
    ic.validate_spec(spec, "2026-11-25")


@case("spec", "an option named for a rank is refused")
def _():
    assert "recommended" in ic.RANK_WORDS and "best" in ic.RANK_WORDS


@case("spec", "malformed specs are collected, never crashed on")
def _():
    base = {"origin": {"lat": 1, "lon": 2}, "dest": {"lat": 3, "lon": 4},
            "stops": {}, "options": {"o": {"stops": []}}}
    bad = [
        ("null stop", {**base, "stops": {"s": None}}),
        ("string latitude", {**base, "origin": {"lat": "north", "lon": 2}}),
        ("latitude 999", {**base, "origin": {"lat": 999, "lon": 2}}),
        ("missing options", {k: v for k, v in base.items() if k != "options"}),
        ("impossible clock", {**base, "stops": {"a": {"lat": 1, "lon": 2, "facilities": [
            {"name": "f", "open": "25:99", "close": "17:00"}]}},
            "options": {"o": {"stops": ["a"]}}}),
        ("last entry before opening", {**base, "stops": {"a": {"lat": 1, "lon": 2,
            "facilities": [{"name": "f", "open": "09:00", "close": "17:00",
                            "last_entry": "08:00"}]}},
            "options": {"o": {"stops": ["a"]}}}),
        ("negative dwell", {**base, "stops": {"a": {"lat": 1, "lon": 2, "dwell_min": -5}},
            "options": {"o": {"stops": ["a"]}}}),
    ]
    for label, spec in bad:
        try:
            ic.validate_spec(spec, "2026-11-25")
        except SystemExit:
            continue
        except Exception as exc:
            raise AssertionError(f"{label}: crashed with {type(exc).__name__}: {exc}")
        raise AssertionError(f"{label}: accepted without complaint")


@case("cache", "a response with no trip is never cached or returned")
def _():
    assert not ic._usable_trip({"error": "no route", "status": 400})
    assert not ic._usable_trip({"trip": {"legs": [], "summary": {}}})
    assert ic._usable_trip({"trip": {"legs": [{"shape": "abc"}],
                                     "summary": {"time": 1, "length": 2}}})


@case("cache", "the key covers the endpoint, not just the waypoints")
def _():
    body = {"locations": [{"lat": 1, "lon": 2}], "costing": "auto"}
    before = ic._cache_key(body)
    saved = ic.ROUTE_URL
    try:
        ic.ROUTE_URL = "https://example.invalid/route"
        assert ic._cache_key(body) != before, "key ignores the endpoint"
    finally:
        ic.ROUTE_URL = saved


@case("solar", "a date with no sunset returns None rather than crashing a caller")
def _():
    rise, noon, set_ = ic.sun_events(78.0, 15.0, 2026, 6, 21, 2)   # polar day
    assert set_ is None and rise is None and noon is not None, (rise, noon, set_)


def main():
    width = max(len(n) for _, n, _ in CASES)
    failed, group = [], None
    for g, name, fn in CASES:
        if g != group:
            group = g
            print(f"\n{g}")
        try:
            fn()
            print(f"  pass  {name}")
        except AssertionError as exc:
            print(f"  FAIL  {name:<{width}}  {exc}")
            failed.append(name)
        except Exception as exc:
            print(f"  ERROR {name:<{width}}  {type(exc).__name__}: {exc}")
            failed.append(name)
    print(f"\n{len(CASES) - len(failed)}/{len(CASES)} pass")
    if failed:
        print("failing: " + ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
