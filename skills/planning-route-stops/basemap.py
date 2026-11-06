#!/usr/bin/env python3
"""Build a bakeable basemap: state outlines, interstate centrelines, city points.

Artifact pages block every external fetch, so tiles can never load. Everything here is
fetched once at build time, simplified hard, and written into basemap.json for the page
generator to inline as SVG path data.

Point budgets matter: the raw Census state polygons alone are 193k points. Clipping to the
view, stitching, dropping sub-2-mile stubs and RDP together take the whole basemap to about
a thousand points -- roughly 0.4% of the combined input. RDP is only part of that reduction;
the script prints raw and kept counts for each layer so the split stays visible.

Tolerances are in degrees of latitude with longitude scaled by cos(mean lat), so eps 0.02
is about 1.9-2.2 km depending on orientation. That is coarse enough to move a state border
a few pixels at this scale, which is acceptable for orientation and would not be for
anything measured off the map.
"""
import json, math, io, os, sys, time, urllib.request, urllib.parse

D = os.path.dirname(os.path.abspath(__file__))
UA = "route-planner/1.0 (arik.tash@gmail.com)"
# view window, with margin: everything outside is clipped by the SVG viewBox anyway,
# but trimming here is what keeps the baked path data small.
VIEW = dict(min_lat=30.2, max_lat=36.5, min_lon=-85.2, max_lon=-78.3)
KEEP_STATES = {"North Carolina", "South Carolina", "Georgia", "Florida",
               "Tennessee", "Alabama", "Virginia"}


def rdp(points, eps, kx=1.0):
    """Iterative Ramer-Douglas-Peucker; recursion blows the stack on long rings.

    Distance is to the replacement *segment*, clamped, not to the infinite line through
    its endpoints -- otherwise a path that doubles back has its turning point measured as
    zero distance and dropped at any epsilon. kx scales longitude so eps is near-isotropic
    (at 33 N, leaving it 1.0 exaggerates east-west distance by 19%).
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
                t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
                d = math.hypot(px - (ax + t * dx), py - (ay + t * dy))
            if d > worst_d:
                worst_d, worst_i = d, i
        if worst_d > eps:
            keep[worst_i] = True
            stack.append((lo, worst_i))
            stack.append((worst_i, hi))
    return [p for p, k in zip(points, keep) if k]


KX = math.cos(math.radians((VIEW["min_lat"] + VIEW["max_lat"]) / 2))
MIN_RUN_MI = 2.0        # shorter than this is a ramp stub, not a road worth drawing


def run_len_mi(pts):
    return sum(math.hypot(b[0] - a[0], (b[1] - a[1]) * KX) * 69.0
               for a, b in zip(pts, pts[1:]))


def _inside(p, pad):
    return (VIEW["min_lat"] - pad <= p[0] <= VIEW["max_lat"] + pad
            and VIEW["min_lon"] - pad <= p[1] <= VIEW["max_lon"] + pad)


def _crosses(a, b, pad):
    """Does segment a-b intersect the padded view box at all? (Liang-Barsky slab test.)

    Needed because a segment can span the whole view with *both* endpoints outside it --
    a simplified state outline does exactly that -- and an endpoint-only test drops it,
    leaving a visible gap in the border.
    """
    y0, x0 = a
    y1, x1 = b
    dy, dx = y1 - y0, x1 - x0
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x0 - (VIEW["min_lon"] - pad)), (dx, (VIEW["max_lon"] + pad) - x0),
                 (-dy, y0 - (VIEW["min_lat"] - pad)), (dy, (VIEW["max_lat"] + pad) - y0)):
        if p == 0.0:
            if q < 0.0:
                return False
            continue
        r = q / p
        if p < 0.0:
            if r > t1:
                return False
            t0 = max(t0, r)
        else:
            if r < t0:
                return False
            t1 = min(t1, r)
    return t0 <= t1


def clip_runs(ring, pad=0.6):
    """Split a polyline into the runs that touch the padded view.

    Dropping off-view points outright would draw a false straight line across the map;
    splitting into runs keeps each visible stretch honest and discards the rest. A span
    whose endpoints are both outside but which crosses the view is kept whole.
    """
    if len(ring) < 2:
        return []
    inside = [_inside(p, pad) for p in ring]
    runs, cur = [], []
    for i in range(len(ring) - 1):
        a, b = ring[i], ring[i + 1]
        if inside[i] or inside[i + 1] or _crosses(a, b, pad):
            if not cur:
                cur.append(a)
            cur.append(b)
        elif cur:
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
                    s = rdp(run, eps, KX)
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
    ref query returns thousands of 2-point fragments -- 8473 of them here, which RDP cannot
    simplify because nothing is longer than a single span. Joining them first is what turns
    73k raw points into a few hundred.

    Endpoints are matched on a rounded key (5 dp, a grid cell of about 1.1 m by 0.9 m at 33 N).
    On this data that is equivalent to exact matching -- no rounded key merged two distinct
    exact endpoints -- so the rounding buys tolerance that has not yet been needed rather than
    fixing an observed problem. It is also not a true distance snap: points up to ~1.45 m apart
    can share a cell while arbitrarily close points can straddle a boundary. Joining by OSM node
    id would be exact; the ids are in the cached response if this ever matters.
    """
    def key(p):
        return (round(p[0], snap), round(p[1], snap))

    ends = {}
    for i, s in enumerate(segments):
        ends.setdefault(key(s[0]), []).append((i, False))
        ends.setdefault(key(s[-1]), []).append((i, True))

    # A cursor per endpoint, so each adjacency entry is examined at most once across the
    # whole run. Rescanning each list from the start made the cost quadratic in the number
    # of fragments meeting at one node -- harmless on this data (max endpoint degree 3)
    # but a trap at a dense interchange, which is exactly where fragments pile up.
    cursor = {k: 0 for k in ends}

    def take(k):
        lst = ends.get(k)
        if lst is None:
            return None
        i = cursor[k]
        while i < len(lst):
            j, rev = lst[i]
            i += 1
            if not used[j]:
                cursor[k] = i
                return j, rev
        cursor[k] = i
        return None

    used, chains = [False] * len(segments), []
    for i in range(len(segments)):
        if used[i]:
            continue
        used[i] = True
        chain = list(segments[i])
        # grow the tail, reverse so the old head is the tail, grow that, reverse back
        for _ in range(2):
            while True:
                nxt = take(key(chain[-1]))
                if nxt is None:
                    break
                j, rev = nxt
                used[j] = True
                seg = segments[j]
                chain.extend(reversed(seg[:-1]) if rev else seg[1:])
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
                s = rdp(run, eps, KX)
                # Keep by visible LENGTH, not vertex count: a straight interstate
                # simplifies to two points, and a >=4-point filter silently deleted 43
                # runs including two 17-mile stretches of I-75.
                if len(s) >= 2 and run_len_mi(s) >= MIN_RUN_MI:
                    kept_n += len(s)
                    by_ref.setdefault(ref, []).append(
                        [[round(a, 4), round(b, 4)] for a, b in s])
    print(f"  stitched {n_frag} fragments into {n_chain} chains")
    return by_ref, raw_n, kept_n, n_frag, n_chain


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
    rd, r_raw, r_kept, n_frag_total, n_chain_total = motorways(eps_road)
    print(f"interstates {r_raw:>6} raw -> {r_kept:>5} pts in "
          f"{sum(len(v) for v in rd.values())} runs across {len(rd)} refs "
          f"({100*r_kept/max(r_raw,1):.2f}%, eps={eps_road})")
    for ref in sorted(rd, key=lambda r: -sum(len(x) for x in rd[r])):
        print(f"   {ref:<8} {len(rd[ref]):>3} runs, {sum(len(x) for x in rd[ref]):>4} pts")
    total_raw, total_kept = s_raw + r_raw, s_kept + r_kept
    print(f"combined   {total_raw:>7} raw -> {total_kept:>5} pts "
          f"({100*total_kept/total_raw:.2f}%) -- clipping and short-run removal "
          f"contribute alongside RDP")
    payload = {"view": VIEW, "states": st, "interstates": rd,
               "cities": [{"name": n, "lat": la, "lon": lo, "major": m}
                          for n, la, lo, m in CITIES],
               "simplify": {"state_eps_deg": eps_state, "road_eps_deg": eps_road,
                            "lon_scale_kx": round(KX, 5), "min_run_mi": MIN_RUN_MI},
               "counts": {"states_raw": s_raw, "states_kept": s_kept,
                          "roads_raw": r_raw, "roads_kept": r_kept,
                          "road_fragments": n_frag_total, "road_chains": n_chain_total,
                          "combined_raw": s_raw + r_raw, "combined_kept": s_kept + r_kept},
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
