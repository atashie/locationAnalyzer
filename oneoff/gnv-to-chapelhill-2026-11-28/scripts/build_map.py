"""Build the inline SVG map data for planner.html.

Artifact pages run under a CSP that blocks every external image, so a tile-based
map (Leaflet et al.) renders blank. Everything here is therefore baked into the
page: state outlines simplified from public GeoJSON, and real route geometry
pulled from the same Valhalla server used for the drive times.

Writes build/mapdata.json, which scripts/inject_map.py splices into the page.
"""

import json
import math
import pathlib
import time

import requests

HERE = pathlib.Path(__file__).resolve().parent.parent
BUILD = HERE / "build"
VALHALLA = "https://valhalla1.openstreetmap.de"

GNV = (29.6516, -82.3248)
CHP = (35.9132, -79.0558)

STOPS = {
    "columbia":   ("Columbia",       34.0007, -81.0348),
    "orangeburg": ("Orangeburg",     33.4918, -80.8556),
    "savannah":   ("Savannah",       32.0809, -81.0912),
    "charleston": ("Charleston",     32.7765, -79.9311),
    "pines":      ("Southern Pines", 35.1740, -79.3947),
}

# Sunday legs that deliberately avoid I-95 need their via point, or Valhalla
# returns the I-95 line instead. Blythewood, on I-77 north of Columbia.
I77_VIA = (34.2126, -80.9735)
SUNDAY_VIA = {"orangeburg": I77_VIA}

LABELS = [
    ("Gainesville", 29.6516, -82.3248, "start"),
    ("Chapel Hill", 35.9132, -79.0558, "end"),
    ("Jacksonville", 30.3322, -81.6557, "ref"),
    ("Charlotte", 35.2271, -80.8431, "ref"),
    ("Fayetteville", 35.0527, -78.8784, "ref"),
]


def decode_polyline(enc, precision=6):
    """Decode a Valhalla-encoded polyline. Valhalla uses precision 6."""
    factor = 10 ** precision
    coords, idx, lat, lon = [], 0, 0, 0
    while idx < len(enc):
        for which in (0, 1):
            result, shift = 0, 0
            while True:
                b = ord(enc[idx]) - 63
                idx += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            delta = ~(result >> 1) if result & 1 else (result >> 1)
            if which == 0:
                lat += delta
            else:
                lon += delta
        coords.append((lat / factor, lon / factor))
    return coords


def rdp(pts, eps):
    """Ramer-Douglas-Peucker, iterative so long routes cannot blow the stack."""
    if len(pts) < 3:
        return pts[:]
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        lo, hi = stack.pop()
        if hi <= lo + 1:
            continue
        ax, ay = pts[lo]
        bx, by = pts[hi]
        dx, dy = bx - ax, by - ay
        norm = math.hypot(dx, dy)
        worst, worst_i = -1.0, -1
        for i in range(lo + 1, hi):
            px, py = pts[i]
            if norm == 0:
                d = math.hypot(px - ax, py - ay)
            else:
                d = abs(dy * (px - ax) - dx * (py - ay)) / norm
            if d > worst:
                worst, worst_i = d, i
        if worst > eps:
            keep[worst_i] = True
            stack.append((lo, worst_i))
            stack.append((worst_i, hi))
    return [p for p, k in zip(pts, keep) if k]


def route_shape(points):
    body = {
        "locations": [{"lat": a, "lon": o} for a, o in points],
        "costing": "auto",
        "directions_options": {"units": "miles"},
    }
    r = requests.post(f"{VALHALLA}/route", json=body, timeout=90)
    r.raise_for_status()
    trip = r.json()["trip"]
    pts = []
    for leg in trip["legs"]:
        seg = decode_polyline(leg["shape"])
        if pts and seg and seg[0] == pts[-1]:
            seg = seg[1:]
        pts.extend(seg)
    return pts, trip["summary"]


def main():
    BUILD.mkdir(exist_ok=True)

    # ---- state outlines -------------------------------------------------
    raw = json.loads((BUILD / "states_raw.json").read_text())
    states = []
    for f in raw["features"]:
        name = f["properties"]["name"]
        geom = f["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        rings = []
        for poly in polys:
            outer = poly[0]
            ring = [(lat, lon) for lon, lat in outer]
            ring = rdp(ring, 0.02)
            if len(ring) > 6:
                rings.append(ring)
        states.append({"name": name, "rings": rings})
        print(f"{name:<16} {sum(len(r) for r in states[-1]['rings']):4d} pts")

    # ---- routes ---------------------------------------------------------
    routes = {}
    for key, (label, la, lo) in STOPS.items():
        sat, s1 = route_shape([GNV, (la, lo)])
        time.sleep(0.6)
        sun_pts = [(la, lo)]
        if key in SUNDAY_VIA:
            sun_pts.append(SUNDAY_VIA[key])
        sun_pts.append(CHP)
        sun, s2 = route_shape(sun_pts)
        time.sleep(0.6)
        sat_s, sun_s = rdp(sat, 0.012), rdp(sun, 0.012)
        routes[key] = {
            "label": label,
            "lat": la,
            "lon": lo,
            "sat": sat_s,
            "sun": sun_s,
            "satHours": round(s1["time"] / 3600, 2),
            "sunHours": round(s2["time"] / 3600, 2),
        }
        print(f"{label:<16} sat {len(sat):5d}->{len(sat_s):4d} pts  "
              f"sun {len(sun):5d}->{len(sun_s):4d} pts")

    # ---- projection -----------------------------------------------------
    allpts = [p for s in states for r in s["rings"] for p in r]
    for r in routes.values():
        allpts += r["sat"] + r["sun"]
    lats = [p[0] for p in allpts]
    lons = [p[1] for p in allpts]
    # clip the frame to the corridor; the states extend well past it
    lat0, lat1 = 28.6, 36.8
    lon0, lon1 = -85.4, -77.6
    mean_lat = (lat0 + lat1) / 2
    kx = math.cos(math.radians(mean_lat))
    W = 1000.0
    H = W * ((lat1 - lat0) / ((lon1 - lon0) * kx))

    def proj(lat, lon):
        x = (lon - lon0) * kx / ((lon1 - lon0) * kx) * W
        y = (lat1 - lat) / (lat1 - lat0) * H
        return round(x, 1), round(y, 1)

    def path(pts):
        d = []
        for i, (la, lo) in enumerate(pts):
            x, y = proj(la, lo)
            d.append(("M" if i == 0 else "L") + f"{x} {y}")
        return "".join(d)

    out = {
        "viewBox": f"0 0 {round(W)} {round(H,1)}",
        "states": [{"name": s["name"], "d": " ".join(path(r) + "Z" for r in s["rings"])}
                   for s in states],
        "routes": {k: {"label": v["label"],
                       "sat": path(v["sat"]),
                       "sun": path(v["sun"]),
                       "pt": proj(v["lat"], v["lon"])}
                   for k, v in routes.items()},
        "labels": [{"name": n, "pt": proj(la, lo), "kind": kind}
                   for n, la, lo, kind in LABELS],
    }
    (BUILD / "mapdata.json").write_text(json.dumps(out, separators=(",", ":")))
    print(f"\nviewBox {out['viewBox']}")
    print("mapdata.json bytes:", len((BUILD / 'mapdata.json').read_text()))
    print("lat range seen", round(min(lats), 2), round(max(lats), 2),
          "lon range seen", round(min(lons), 2), round(max(lons), 2))


if __name__ == "__main__":
    main()
