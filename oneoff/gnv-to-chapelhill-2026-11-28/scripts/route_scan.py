"""Enumerate Gainesville FL -> Chapel Hill NC corridors and score candidate overnight stops.

Uses the public Valhalla server (same one the main app defaults to) for drive times.
Free-flow times only -- no Thanksgiving-weekend traffic model. Treat as a lower bound.

Outputs:
  data/corridors.json   - the distinct route corridors and their cost
  data/candidates.json  - per-candidate leg1/leg2/detour/halfway-fraction
"""

import json
import pathlib
import time

import requests

VALHALLA = "https://valhalla1.openstreetmap.de"
HERE = pathlib.Path(__file__).resolve().parent.parent
DATA = HERE / "data"

ORIGIN = ("Gainesville, FL", 29.6516, -82.3248)
DEST = ("Chapel Hill, NC", 35.9132, -79.0558)

# Corridor-forcing via points: each entry is the set of waypoints that pins a
# recognisably different way of getting there.
CORRIDORS = {
    "I-95 (Jax / Savannah / Florence / Fayetteville)": [
        (30.3322, -81.6557), (32.0809, -81.0912), (34.1954, -79.7626), (35.0527, -78.8784),
    ],
    "I-95 then US-301 inland (Orangeburg / Columbia / Sanford)": [
        (30.3322, -81.6557), (32.0809, -81.0912), (33.4918, -80.8556), (34.0007, -81.0348),
    ],
    "I-75 inland (Valdosta / Tifton / Macon / Augusta / Columbia)": [
        (30.8327, -83.2785), (31.4505, -83.5085), (32.8407, -83.6324), (33.4735, -82.0105), (34.0007, -81.0348),
    ],
    "I-75 to Macon then I-16/I-95 (Savannah)": [
        (30.8327, -83.2785), (32.8407, -83.6324), (32.0809, -81.0912), (34.1954, -79.7626),
    ],
    "Coastal detour via Charleston": [
        (30.3322, -81.6557), (32.0809, -81.0912), (32.7765, -79.9311), (34.1954, -79.7626),
    ],
    "US-301 Florida bypass of Jacksonville": [
        (30.3048, -82.1637), (31.2136, -82.3540), (32.0809, -81.0912), (34.1954, -79.7626),
    ],
}

CANDIDATES = [
    # name, lat, lon, state
    ("Jacksonville, FL", 30.3322, -81.6557),
    ("St. Augustine, FL", 29.8947, -81.3145),
    ("Fernandina Beach / Amelia Is., FL", 30.6697, -81.4626),
    ("Okefenokee NWR (Folkston, GA)", 30.7390, -82.1370),
    ("Waycross, GA", 31.2136, -82.3540),
    ("Valdosta, GA", 30.8327, -83.2785),
    ("Brunswick, GA", 31.1497, -81.4915),
    ("St. Simons Island, GA", 31.1507, -81.3807),
    ("Jekyll Island, GA", 31.0696, -81.4120),
    ("Tifton, GA", 31.4505, -83.5085),
    ("Pooler, GA", 32.1152, -81.2470),
    ("Savannah, GA", 32.0809, -81.0912),
    ("Statesboro, GA", 32.4488, -81.7832),
    ("Vidalia, GA", 32.2177, -82.4135),
    ("Dublin, GA", 32.5404, -82.9038),
    ("Macon, GA", 32.8407, -83.6324),
    ("Augusta, GA", 33.4735, -82.0105),
    ("Hardeeville, SC", 32.2871, -81.0807),
    ("Ridgeland, SC", 32.4810, -80.9829),
    ("Hilton Head Island, SC", 32.2163, -80.7526),
    ("Beaufort, SC", 32.4316, -80.6698),
    ("Walterboro, SC", 32.9051, -80.6665),
    ("Summerville, SC", 33.0185, -80.1756),
    ("Charleston, SC", 32.7765, -79.9311),
    ("Orangeburg, SC", 33.4918, -80.8556),
    ("Santee, SC", 33.4818, -80.4867),
    ("Congaree NP (Hopkins, SC)", 33.7948, -80.7846),
    ("Columbia, SC", 34.0007, -81.0348),
    ("Aiken, SC", 33.5604, -81.7196),
    ("Sumter, SC", 33.9204, -80.3414),
    ("Camden, SC", 34.2465, -80.6068),
    ("Florence, SC", 34.1954, -79.7626),
    ("Myrtle Beach, SC", 33.6891, -78.8867),
    ("Lumberton, NC", 34.6182, -79.0086),
    ("Fayetteville, NC", 35.0527, -78.8784),
    ("Southern Pines / Pinehurst, NC", 35.1740, -79.3947),
    ("Charlotte, NC", 35.2271, -80.8431),
    ("Wilmington, NC", 34.2257, -77.9447),
]


def valhalla_route(locations, alternates=0):
    body = {
        "locations": [{"lat": la, "lon": lo} for la, lo in locations],
        "costing": "auto",
        "directions_options": {"units": "miles"},
    }
    if alternates:
        body["alternates"] = alternates
    r = requests.post(f"{VALHALLA}/route", json=body, timeout=60)
    r.raise_for_status()
    return r.json()


def summary_of(trip):
    s = trip["summary"]
    return {"miles": round(s["length"], 1), "hours": round(s["time"] / 3600.0, 2)}


def two_legs(stop):
    """Route origin -> stop -> dest in one call. The public matrix endpoint caps
    path distance at 150 km, so /route with a via point is the only option here."""
    la, lo = stop
    t = valhalla_route([(ORIGIN[1], ORIGIN[2]), (la, lo), (DEST[1], DEST[2])])["trip"]
    legs = [(l["summary"]["time"] / 3600.0, l["summary"]["length"]) for l in t["legs"]]
    return legs[0], legs[1]


def main():
    DATA.mkdir(exist_ok=True)
    out = {}

    # --- baseline fastest route, plus whatever alternates Valhalla volunteers
    base = valhalla_route([(ORIGIN[1], ORIGIN[2]), (DEST[1], DEST[2])], alternates=3)
    baseline = summary_of(base["trip"])
    out["baseline_fastest"] = baseline
    out["valhalla_alternates"] = [summary_of(a["trip"]) for a in base.get("alternates", [])]
    print(f"baseline fastest: {baseline['miles']} mi, {baseline['hours']} h")
    for i, a in enumerate(out["valhalla_alternates"], 1):
        print(f"  alternate {i}: {a['miles']} mi, {a['hours']} h")

    # --- forced corridors
    out["corridors"] = {}
    for name, vias in CORRIDORS.items():
        try:
            locs = [(ORIGIN[1], ORIGIN[2])] + vias + [(DEST[1], DEST[2])]
            t = valhalla_route(locs)
            s = summary_of(t["trip"])
            s["penalty_hours"] = round(s["hours"] - baseline["hours"], 2)
            out["corridors"][name] = s
            print(f"corridor {name}: {s['miles']} mi, {s['hours']} h (+{s['penalty_hours']} h)")
        except Exception as e:  # network / server hiccup on a public endpoint
            out["corridors"][name] = {"error": str(e)}
            print(f"corridor {name}: FAILED {e}")
        time.sleep(1.0)

    (DATA / "corridors.json").write_text(json.dumps(out, indent=2))

    # --- candidate stops: leg1 + leg2 vs baseline
    rows = []
    for name, la, lo in CANDIDATES:
        try:
            (t1, d1), (t2, d2) = two_legs((la, lo))
        except Exception as e:
            print(f"  {name}: FAILED {e}")
            continue
        time.sleep(0.6)
        total = t1 + t2
        rows.append({
            "stop": name,
            "lat": la,
            "lon": lo,
            "sat_hours": round(t1, 2),
            "sat_miles": round(d1, 1),
            "sun_hours": round(t2, 2),
            "sun_miles": round(d2, 1),
            "total_hours": round(total, 2),
            "detour_min": round((total - baseline["hours"]) * 60, 0),
            "frac_of_trip": round(t1 / total, 3) if total else None,
        })

    rows.sort(key=lambda r: (r["detour_min"], abs(r["frac_of_trip"] - 0.55)))
    (DATA / "candidates.json").write_text(json.dumps(
        {"baseline": baseline, "origin": ORIGIN[0], "dest": DEST[0], "rows": rows}, indent=2))

    print("\n{:<36} {:>6} {:>6} {:>6} {:>8} {:>6}".format(
        "stop", "sat_h", "sun_h", "tot_h", "detour_m", "frac"))
    for r in rows:
        print("{:<36} {:>6.2f} {:>6.2f} {:>6.2f} {:>8.0f} {:>6.2f}".format(
            r["stop"], r["sat_hours"], r["sun_hours"], r["total_hours"],
            r["detour_min"], r["frac_of_trip"]))


if __name__ == "__main__":
    main()
