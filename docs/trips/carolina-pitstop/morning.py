"""Sunday-morning venues: walk (Valhalla pedestrian) and drive (Valhalla auto) from the hotel.

Same engine as walk.py and every drive on the page. Writes morning.json.
Check the printed geocode matches by eye: a wrong match is a wrong walk time.

    python morning.py
"""
import json
import time
import urllib.parse
import urllib.request

UA = "route-planner-script/1.0"
HOTEL = (34.0077, -81.0498)
V = [
    ("motorsupply", "920 Gervais Street, Columbia, SC 29201"),
    ("gourmet", "724 Saluda Avenue, Columbia, SC 29205"),
    ("drip", "729 Saluda Avenue, Columbia, SC 29205"),
    ("methodical", "2149 Pickens Street, Columbia, SC 29201"),
    ("strudel", "300 State Street, West Columbia, SC 29169"),
    ("lizards", "818 Elmwood Avenue, Columbia, SC 29201"),
    ("riverwalk", "West Columbia Riverwalk, West Columbia, SC"),
    ("zoo", "500 Wildlife Parkway, Columbia, SC 29210"),
]


def get(url, data=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=30))


def leg(a, b, costing):
    body = json.dumps({"locations": [{"lat": a[0], "lon": a[1]}, {"lat": b[0], "lon": b[1]}],
                       "costing": costing, "units": "miles"}).encode()
    s = get("https://valhalla1.openstreetmap.de/route", body)["trip"]["summary"]
    time.sleep(1)
    return round(s["length"], 2), round(s["time"] / 60)


out = {}
for k, q in V:
    g = get("https://nominatim.openstreetmap.org/search?format=json&limit=1&q=" + urllib.parse.quote(q))
    time.sleep(1.1)
    if not g:
        out[k] = {"geocode": None}; print(k, "NO GEOCODE"); continue
    p = (float(g[0]["lat"]), float(g[0]["lon"]))
    out[k] = {"lat": p[0], "lon": p[1], "matched": g[0]["display_name"][:100],
              "walk": leg(HOTEL, p, "pedestrian"), "drive": leg(HOTEL, p, "auto")}
    print(k, out[k]["walk"], out[k]["drive"], out[k]["matched"][:70])
json.dump(out, open("morning.json", "w"), indent=1)
