"""Fetch major-road geometry from OpenStreetMap (Overpass) for the basemap.

Artifact pages cannot load map tiles, so the road network has to be baked into
the page like everything else. This pulls motorway and trunk geometry for the
corridor, stitches each route's ways into long polylines by `ref`, simplifies
them, and projects them onto the same frame as build_map.py.

Writes build/roads.json.
"""

import json
import math
import pathlib
import re
import sys
from collections import defaultdict

import requests

HERE = pathlib.Path(__file__).resolve().parent.parent
BUILD = HERE / "build"

# same frame as build_map.py
LAT0, LAT1 = 28.6, 36.8
LON0, LON1 = -85.4, -77.6
MEAN_LAT = (LAT0 + LAT1) / 2
KX = math.cos(math.radians(MEAN_LAT))
W = 1000.0
H = W * ((LAT1 - LAT0) / ((LON1 - LON0) * KX))

ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.osm.ch/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
# Overpass returns 406 to clients that do not identify themselves.
HEADERS = {
    "User-Agent": "distancefinder-oneoff-trip-map/1.0 (one-off personal road-trip map)",
    "Accept": "application/json",
}

QUERY = f"""
[out:json][timeout:240];
(
  way["highway"="motorway"]({LAT0},{LON0},{LAT1},{LON1});
  way["highway"="trunk"]["ref"~"^US"]({LAT0},{LON0},{LAT1},{LON1});
);
out geom;
"""


def fetch():
    cache = BUILD / "overpass_roads.json"
    if cache.exists():
        print("using cached overpass response")
        return json.loads(cache.read_text())
    import time
    last = None
    for attempt in range(2):
        for url in ENDPOINTS:
            try:
                print("querying", url)
                r = requests.post(url, data={"data": QUERY},
                                  headers=HEADERS, timeout=300)
                if r.status_code == 429:
                    raise requests.HTTPError("429 rate limited")
                r.raise_for_status()
                d = r.json()
                cache.write_text(json.dumps(d))
                print(f"  {len(d.get('elements', []))} ways, {len(r.content)/1e6:.1f} MB")
                return d
            except Exception as e:  # public endpoints are flaky; try the mirrors
                print("  failed:", type(e).__name__, e)
                last = e
                time.sleep(3)
        if attempt == 0:
            print("all endpoints failed once; backing off 20s")
            time.sleep(20)
    raise SystemExit(f"all Overpass endpoints failed: {last}")


def rdp(pts, eps):
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
        worst, wi = -1.0, -1
        for i in range(lo + 1, hi):
            px, py = pts[i]
            d = (math.hypot(px - ax, py - ay) if norm == 0
                 else abs(dy * (px - ax) - dx * (py - ay)) / norm)
            if d > worst:
                worst, wi = d, i
        if worst > eps:
            keep[wi] = True
            stack.append((lo, wi))
            stack.append((wi, hi))
    return [p for p, k in zip(pts, keep) if k]


# Two-digit interstates only. They are the through-routes that make the corridor
# legible; three-digit spurs are urban loops that just add noise at this scale,
# and US routes come back from Overpass as hundreds of disconnected `trunk`
# fragments (they are only tagged trunk where limited-access), so they render as
# scattered dashes rather than roads. The itinerary's US routes are named in the
# page's route row instead.
# Shields only for the roads a reader would orient by.
SHIELD_KEEP = {"I-95", "I-26", "I-77", "I-85", "I-40", "I-20",
               "I-16", "I-10", "I-75", "I-4"}


def wanted(ref):
    return bool(re.fullmatch(r"I-\d{1,2}", ref))


def primary_ref(tags):
    """First ref on a way, normalised: 'I 26;I 126' -> 'I-26'."""
    ref = (tags.get("ref") or "").split(";")[0].strip()
    if not ref:
        return None
    m = re.match(r"^(I|US|SC|NC|GA|FL)\s*-?\s*(\d+)", ref)
    return f"{m.group(1)}-{m.group(2)}" if m else None


def stitch(segments):
    """Greedily join segments that share endpoints into long polylines."""
    segs = [list(s) for s in segments if len(s) > 1]
    out = []
    while segs:
        cur = segs.pop()
        joined = True
        while joined:
            joined = False
            for i, s in enumerate(segs):
                if _close(cur[-1], s[0]):
                    cur += s[1:]
                elif _close(cur[-1], s[-1]):
                    cur += s[::-1][1:]
                elif _close(cur[0], s[-1]):
                    cur = s[:-1] + cur
                elif _close(cur[0], s[0]):
                    cur = s[::-1][:-1] + cur
                else:
                    continue
                segs.pop(i)
                joined = True
                break
        out.append(cur)
    return out


def _close(a, b, tol=2e-4):
    return abs(a[0] - b[0]) < tol and abs(a[1] - b[1]) < tol


def proj(lat, lon):
    x = (lon - LON0) * KX / ((LON1 - LON0) * KX) * W
    y = (LAT1 - lat) / (LAT1 - LAT0) * H
    return round(x, 1), round(y, 1)


def path(pts):
    return "".join(("M" if i == 0 else "L") + f"{x} {y}"
                   for i, (x, y) in enumerate(proj(la, lo) for la, lo in pts))


def inframe(pt):
    return -20 <= pt[0] <= W + 20 and -20 <= pt[1] <= H + 20


def main():
    BUILD.mkdir(exist_ok=True)
    data = fetch()

    by_ref = defaultdict(list)
    unlabelled = []
    for el in data.get("elements", []):
        geom = el.get("geometry") or []
        pts = [(g["lat"], g["lon"]) for g in geom if g]
        if len(pts) < 2:
            continue
        ref = primary_ref(el.get("tags", {}))
        (by_ref[ref] if ref else unlabelled).append(pts)

    roads, labels = [], []
    for ref, segs in sorted(by_ref.items()):
        if not wanted(ref):
            continue
        eps = 0.015
        lines = stitch(segs)
        kept = []
        for ln in lines:
            s = rdp(ln, eps)
            if len(s) >= 2 and sum(1 for p in s if inframe(proj(*p))) >= 2:
                kept.append(s)
        if not kept:
            continue
        kept.sort(key=len, reverse=True)
        total = sum(len(k) for k in kept)
        roads.append({
            "ref": ref,
            "cls": "mw",
            "d": " ".join(path(k) for k in kept),
        })
        # one shield per orienting interstate, at the midpoint of its longest run
        if ref in SHIELD_KEEP:
            run = kept[0]
            cand = [proj(*p) for p in run]
            cand = [c for c in cand if 40 <= c[0] <= W - 40 and 40 <= c[1] <= H - 40]
            if cand:
                labels.append({"ref": ref, "pt": cand[len(cand) // 2]})
        print(f"  {ref:<8} {len(segs):4d} ways -> {len(kept):2d} lines, {total:4d} pts")

    out = {"roads": roads, "shields": labels}
    (BUILD / "roads.json").write_text(json.dumps(out, separators=(",", ":")))
    size = len((BUILD / "roads.json").read_text())
    print(f"\n{len(roads)} refs, {len(labels)} shields, {size/1024:.1f} KB")
    print(f"dropped {len(unlabelled)} unlabelled motorway segments")
    if size > 90_000:
        print("WARNING: larger than intended; raise the RDP epsilon", file=sys.stderr)


if __name__ == "__main__":
    main()
