"""Sunday leg: hotel (Columbia) -> Chapel Hill, measured bare on each plausible corridor.

One engine (public Valhalla, free-flow), same as every other drive figure on the page.
Writes sunday.json: per corridor, time, miles, the main roads used, and decoded geometry.

    python sunday.py
"""
import json
import time
import urllib.request
from collections import Counter

UA = "route-planner-script/1.0"
HOTEL = (34.0077, -81.0498)
CHAPEL_HILL = (35.9132, -79.0558)  # same point as the page's Chapel Hill label
CORRIDORS = {
    "direct": ("Router's choice", []),
    "charlotte": ("I-77 and I-85 via Charlotte", [(35.2271, -80.8431)]),
    "us1": ("US-1 via Cheraw and Sanford", [(34.6976, -79.8834), (35.4799, -79.1803)]),
    "i95": ("I-20, I-95 and I-40 via Florence", [(34.1954, -79.7626), (35.3810, -78.5530)]),
}


def decode(enc: str, prec: int = 6) -> list[tuple[float, float]]:
    pts, lat, lon, i, f = [], 0, 0, 0, 10 ** prec
    while i < len(enc):
        for which in (0, 1):
            shift = res = 0
            while True:
                b = ord(enc[i]) - 63; i += 1
                res |= (b & 0x1F) << shift; shift += 5
                if b < 0x20:
                    break
            d = ~(res >> 1) if res & 1 else res >> 1
            if which == 0:
                lat += d
            else:
                lon += d
        pts.append((lat / f, lon / f))
    return pts


def route(points):
    body = json.dumps({"locations": [{"lat": a, "lon": b, "type": "break" if k in (0, len(points) - 1) else "through"}
                                     for k, (a, b) in enumerate(points)],
                       "costing": "auto", "units": "miles"}).encode()
    req = urllib.request.Request("https://valhalla1.openstreetmap.de/route", data=body,
                                 headers={"User-Agent": UA, "Content-Type": "application/json"})
    t = json.load(urllib.request.urlopen(req, timeout=60))["trip"]
    geom, roads = [], Counter()
    for leg in t["legs"]:
        geom += decode(leg["shape"])
        for m in leg["maneuvers"]:
            for n in m.get("street_names", [])[:1]:
                roads[n] += m.get("length", 0)
    return t["summary"]["time"], t["summary"]["length"], roads, geom


def encode(pts, prec: int = 6) -> str:
    out, plat, plon, f = [], 0, 0, 10 ** prec
    for lat, lon in pts:
        for v, prev in ((round(lat * f), plat), (round(lon * f), plon)):
            d = v - prev; d = ~(d << 1) if d < 0 else d << 1
            while d >= 0x20:
                out.append(chr((0x20 | (d & 0x1F)) + 63)); d >>= 5
            out.append(chr(d + 63))
        plat, plon = round(lat * f), round(lon * f)
    return "".join(out)


# round-trip check on the decoder (Valhalla precision 6), including negatives
_t = [(34.0077, -81.0498), (35.9132, -79.0558), (35.913201, -79.055799)]
assert all(abs(a - c) < 1e-6 and abs(b - d) < 1e-6 for (a, b), (c, d) in zip(decode(encode(_t)), _t))

out = {}
for k, (label, via) in CORRIDORS.items():
    s, mi, roads, geom = route([HOTEL, *via, CHAPEL_HILL])
    top = [r for r, _ in roads.most_common(4)]
    out[k] = {"label": label, "time_s": s, "miles": mi, "roads": top,
              "geometry": [[round(a, 5), round(b, 5)] for a, b in geom[::4]] + [[round(geom[-1][0], 5), round(geom[-1][1], 5)]]}
    print(k, round(s / 60), "min", round(mi), "mi", top)
    time.sleep(1.2)
json.dump(out, open("sunday.json", "w"), indent=0)
