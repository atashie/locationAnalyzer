#!/usr/bin/env python3
"""Build a bakeable basemap: state outlines, interstate centrelines, city points.

Artifact pages block every external fetch, so tiles can never load. Everything here is
fetched once at build time, simplified hard, and written into basemap.json for the page
generator to inline as SVG path data.

Point budgets matter: the raw Census state polygons are 193k points. At this map's scale
(~7 deg wide rendered under 900 px) anything finer than ~1.5 km is invisible, so RDP takes
the whole basemap to a couple of thousand points -- about 1% of the raw data.
"""
import json, math, io, os, sys, time, urllib.request, urllib.parse

D = os.path.dirname(os.path.abspath(__file__))
UA = "route-planner/1.0 (arik.tash@gmail.com)"
# view window, with margin: everything outside is clipped by the SVG viewBox anyway,
# but trimming here is what keeps the baked path data small.
VIEW = dict(min_lat=30.2, max_lat=36.5, min_lon=-85.2, max_lon=-78.3)
KEEP_STATES = {"North Carolina", "South Carolina", "Georgia", "Florida",
               "Tennessee", "Alabama", "Virginia"}


def rdp(points, eps):
    """Iterative Ramer-Douglas-Peucker; recursion blows the stack on long rings."""
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
            d = (math.hypot(px - ax, py - ay) if norm == 0.0
                 else abs(dy * (px - ax) - dx * (py - ay)) / norm)
            if d > worst_d:
                worst_d, worst_i = d, i
        if worst_d > eps:
            keep[worst_i] = True
            stack.append((lo, worst_i))
            stack.append((worst_i, hi))
    return [p for p, k in zip(points, keep) if k]


def clip_runs(ring, pad=0.6):
    """Split a ring into the runs that fall inside the padded view.

    Dropping off-view points outright would draw a false straight line across the map;
    splitting into runs keeps each visible stretch honest and discards the rest.
    """
    inside = [(VIEW["min_lat"] - pad <= a <= VIEW["max_lat"] + pad
               and VIEW["min_lon"] - pad <= b <= VIEW["max_lon"] + pad)
              for a, b in ring]
    runs, cur = [], []
    for i, p in enumerate(ring):
        if inside[i]:
            if not cur and i > 0:
                cur.append(ring[i - 1])      # one point of lead-in, so the run reaches the edge
            cur.append(p)
        else:
            if cur:
                cur.append(p)                # and one of lead-out
                runs.append(cur)
                cur = []
    if cur:
        runs.append(cur)
    return [r for r in runs if len(r) >= 2]


def fetch(url, data=None, timeout=180, tries=3):
    last = None
    for a in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as exc:
            last = exc
            if a < tries - 1:
                time.sleep(3 + 3 * a)
    raise RuntimeError(f"fetch failed: {last}")


# ---------------------------------------------------------- state outlines
def states(eps):
    path = f"{D}/states_raw.json"
    if not os.path.exists(path):
        q = {"where": "NAME IN (" + ",".join(f"'{n}'" for n in sorted(KEEP_STATES)) + ")",
             "outFields": "NAME,STUSAB", "returnGeometry": "true", "f": "geojson",
             "geometryPrecision": "3", "outSR": "4326"}
        url = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
               "State_County/MapServer/0/query?" + urllib.parse.urlencode(q))
        io.open(path, "wb").write(fetch(url, timeout=120))
    j = json.load(open(path, encoding="utf-8"))
    out, raw_n, kept_n = [], 0, 0
    for f in j["features"]:
        nm = f["properties"]["NAME"]
        if nm not in KEEP_STATES:
            continue
        g = f["geometry"]
        rings = ([g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"])
        for poly in rings:
            for ring in (poly if isinstance(poly[0][0], (int, float)) is False else [poly]):
                pts = [(la, lo) for lo, la in ring]   # geojson is lon,lat
                raw_n += len(pts)
                for run in clip_runs(pts):
                    s = rdp(run, eps)
                    if len(s) >= 2:
                        kept_n += len(s)
                        out.append({"state": nm,
                                    "pts": [[round(a, 4), round(b, 4)] for a, b in s]})
    return out, raw_n, kept_n


# ---------------------------------------------------------- interstates
# Spurs and loops are deliberately excluded: they add clutter at this scale and none of
# them is a corridor anyone chooses between.
INTERSTATES = ["I 95", "I 85", "I 77", "I 20", "I 75", "I 26", "I 16", "I 40", "I 10"]


def stitch(segments, snap=5):
    """Chain OSM way fragments end-to-end into long polylines.

    OSM splits a motorway at every junction and carries each carriageway separately, so a
    ref query returns thousands of 2-point fragments -- 8921 of them here, which RDP cannot
    simplify because nothing is longer than a single span. Joining them first is what turns
    77k raw points into a few hundred. Endpoints are matched on a rounded key (1e-5 deg,
    about a metre) rather than exact equality, since shared nodes differ in the last digit.
    """
    def key(p):
        return (round(p[0], snap), round(p[1], snap))

    ends = {}
    for i, s in enumerate(segments):
        ends.setdefault(key(s[0]), []).append((i, False))
        ends.setdefault(key(s[-1]), []).append((i, True))

    used, chains = [False] * len(segments), []
    for i in range(len(segments)):
        if used[i]:
            continue
        used[i] = True
        chain = list(segments[i])
        # extend from both ends until no unused fragment shares an endpoint
        for _ in range(2):
            while True:
                for j, rev in ends.get(key(chain[-1]), []):
                    if used[j]:
                        continue
                    seg = segments[j]
                    used[j] = True
                    chain.extend(reversed(seg[:-1]) if rev else seg[1:])
                    break
                else:
                    break
            chain.reverse()
        chains.append(chain)
    return chains

def motorways(eps):
    path = f"{D}/motorways_raw.json"
    if not os.path.exists(path):
        bb = f'{VIEW["min_lat"]},{VIEW["min_lon"]},{VIEW["max_lat"]},{VIEW["max_lon"]}'
        refs = "|".join(f"^{r}$" for r in INTERSTATES)
        q = (f'[out:json][timeout:300];'
             f'way["highway"="motorway"]["ref"~"{refs}"]({bb});'
             f'out geom;')
        last = None
        for mirror in ["https://overpass-api.de/api/interpreter",
                       "https://overpass.kumi.systems/api/interpreter",
                       "https://overpass.private.coffee/api/interpreter"]:
            try:
                io.open(path, "wb").write(
                    fetch(mirror, data=urllib.parse.urlencode({"data": q}).encode(),
                          timeout=300, tries=1))
                break
            except Exception as exc:
                last = exc
                print(f"  mirror {mirror} failed: {type(exc).__name__}")
        else:
            raise RuntimeError(f"all Overpass mirrors failed: {last}")
    j = json.load(open(path, encoding="utf-8"))
    frags, raw_n = {}, 0
    for e in j["elements"]:
        g = e.get("geometry")
        if not g:
            continue
        ref = (e.get("tags", {}).get("ref") or "?").strip()
        if ref not in INTERSTATES:
            continue
        pts = [(p["lat"], p["lon"]) for p in g if p]
        if len(pts) >= 2:
            raw_n += len(pts)
            frags.setdefault(ref, []).append(pts)

    by_ref, kept_n, n_frag, n_chain = {}, 0, 0, 0
    for ref, segs in frags.items():
        n_frag += len(segs)
        chains = stitch(segs)
        n_chain += len(chains)
        # longest chains first, then keep only what reads as a road at this scale
        chains.sort(key=len, reverse=True)
        for chain in chains:
            for run in clip_runs(chain, pad=0.1):
                s = rdp(run, eps)
                if len(s) >= 4:           # drop ramp stubs that survived stitching
                    kept_n += len(s)
                    by_ref.setdefault(ref, []).append(
                        [[round(a, 4), round(b, 4)] for a, b in s])
    print(f"  stitched {n_frag} fragments into {n_chain} chains")
    return by_ref, raw_n, kept_n


# ---------------------------------------------------------- cities
CITIES = [
    ("Raleigh", 35.7796, -78.6382, 0), ("Charlotte", 35.2271, -80.8431, 1),
    ("Fayetteville", 35.0527, -78.8784, 0), ("Wilmington", 34.2257, -77.9447, 0),
    ("Columbia", 34.0007, -81.0348, 1), ("Charleston", 32.7765, -79.9311, 0),
    ("Florence", 34.1954, -79.7626, 0), ("Augusta", 33.4735, -81.9748, 0),
    ("Atlanta", 33.7490, -84.3880, 1), ("Macon", 32.8407, -83.6324, 0),
    ("Savannah", 32.0809, -81.0912, 1), ("Albany", 31.5785, -84.1557, 0),
    ("Valdosta", 30.8327, -83.2785, 0), ("Tallahassee", 30.4383, -84.2807, 0),
    ("Jacksonville", 30.3322, -81.6557, 1),
]


def main():
    eps_state = float(sys.argv[1]) if len(sys.argv) > 1 else 0.02
    eps_road = float(sys.argv[2]) if len(sys.argv) > 2 else 0.012
    st, s_raw, s_kept = states(eps_state)
    print(f"states     {s_raw:>7} raw -> {s_kept:>5} pts in {len(st)} runs "
          f"({100*s_kept/max(s_raw,1):.2f}%, eps={eps_state})")
    rd, r_raw, r_kept = motorways(eps_road)
    print(f"interstates {r_raw:>6} raw -> {r_kept:>5} pts in "
          f"{sum(len(v) for v in rd.values())} runs across {len(rd)} refs "
          f"({100*r_kept/max(r_raw,1):.2f}%, eps={eps_road})")
    for ref in sorted(rd, key=lambda r: -sum(len(x) for x in rd[r])):
        print(f"   {ref:<8} {len(rd[ref]):>3} runs, {sum(len(x) for x in rd[ref]):>4} pts")
    payload = {"view": VIEW, "states": st, "interstates": rd,
               "cities": [{"name": n, "lat": la, "lon": lo, "major": m}
                          for n, la, lo, m in CITIES],
               "simplify": {"state_eps_deg": eps_state, "road_eps_deg": eps_road},
               "provenance": {
                   "states": "US Census TIGERweb State_County MapServer, geometryPrecision 3",
                   "interstates": "OpenStreetMap via Overpass, highway=motorway filtered by ref",
                   "cities": "hand-placed coordinates",
                   "traffic": "NONE -- no keyless traffic source; drive times are free-flow"}}
    io.open(f"{D}/basemap.json", "w", encoding="utf-8").write(json.dumps(payload))
    kb = os.path.getsize(f"{D}/basemap.json") / 1024
    print(f"wrote basemap.json  {kb:.0f} KB  "
          f"({s_kept + r_kept} geometry points total)")


if __name__ == "__main__":
    main()
