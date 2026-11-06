"""Arrival time vs remaining daylight for each candidate stop on 2026-11-28.

The binding constraint on this trip is not distance, it is light. A stop is only
useful for an outdoor "explore somewhere new" window if the family arrives with
enough daylight left. This pairs the Valhalla drive times with NOAA sunset.

All candidates are in US Eastern; DST ended 2026-11-01, so the offset is EST
(UTC-5) for the whole trip.

Sunset here is the standard -0.833 deg geometric altitude (refraction + solar
radius). Civil twilight end is -6 deg: usable light for a walk, too dark for
much else.
"""

import json
import math
import pathlib

HERE = pathlib.Path(__file__).resolve().parent.parent
DATA = HERE / "data"

DEPART_LOCAL = 9.5          # 09:30 from Gainesville ("mid morning")
BREAK_FRACTION = 0.18       # gas/lunch/bathroom overhead with a 6- and 9-year-old
UTC_OFFSET = -5.0           # EST

DOY = 332                   # 2026-11-28 is day 332 of a non-leap year
YEAR, MONTH, DAY = 2026, 11, 28


def julian_day(y, m, d):
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4
    return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + b - 1524.5


def sun_event(lat, lon, jd, altitude_deg):
    """Local standard time (hours) of the evening crossing of `altitude_deg`.
    NOAA solar-position algorithm, iterated twice for the equation of time."""
    t = (jd - 2451545.0) / 36525.0
    # geometric mean longitude and anomaly of the sun
    L0 = (280.46646 + t * (36000.76983 + t * 0.0003032)) % 360.0
    M = 357.52911 + t * (35999.05029 - 0.0001537 * t)
    Mr = math.radians(M)
    # equation of the centre -> true longitude -> apparent longitude
    C = (math.sin(Mr) * (1.914602 - t * (0.004817 + 0.000014 * t))
         + math.sin(2 * Mr) * (0.019993 - 0.000101 * t)
         + math.sin(3 * Mr) * 0.000289)
    true_long = L0 + C
    omega = 125.04 - 1934.136 * t
    app_long = true_long - 0.00569 - 0.00478 * math.sin(math.radians(omega))
    # obliquity
    e0 = (23.0 + (26.0 + ((21.448 - t * (46.815 + t * (0.00059 - t * 0.001813)))) / 60.0) / 60.0)
    eps = e0 + 0.00256 * math.cos(math.radians(omega))
    decl = math.degrees(math.asin(math.sin(math.radians(eps))
                                  * math.sin(math.radians(app_long))))
    # equation of time (minutes)
    y = math.tan(math.radians(eps / 2.0)) ** 2
    eot = 4 * math.degrees(
        y * math.sin(2 * math.radians(L0))
        - 2 * 0.016708634 * math.sin(Mr)
        + 4 * 0.016708634 * y * math.sin(Mr) * math.cos(2 * math.radians(L0))
        - 0.5 * y * y * math.sin(4 * math.radians(L0))
        - 1.25 * 0.016708634 ** 2 * math.sin(2 * Mr))
    # hour angle at the target altitude
    lat_r, decl_r = math.radians(lat), math.radians(decl)
    cos_ha = ((math.sin(math.radians(altitude_deg)) - math.sin(lat_r) * math.sin(decl_r))
              / (math.cos(lat_r) * math.cos(decl_r)))
    if not -1.0 <= cos_ha <= 1.0:
        return None
    ha = math.degrees(math.acos(cos_ha))
    solar_noon_utc = (720 - 4 * lon - eot) / 60.0
    return solar_noon_utc + ha / 15.0 + UTC_OFFSET


def hhmm(h):
    if h is None:
        return "--:--"
    h = h % 24
    m = int(round((h - int(h)) * 60))
    hr = int(h) + (1 if m == 60 else 0)
    m = 0 if m == 60 else m
    return f"{hr:02d}:{m:02d}"


def main():
    rows = json.loads((DATA / "candidates.json").read_text())["rows"]
    jd = julian_day(YEAR, MONTH, DAY)

    out = []
    for r in rows:
        drive = r["sat_hours"]
        elapsed = drive * (1 + BREAK_FRACTION)
        arrive = DEPART_LOCAL + elapsed
        sunset = sun_event(r["lat"], r["lon"], jd, -0.833)
        civil = sun_event(r["lat"], r["lon"], jd, -6.0)
        out.append({
            **r,
            "elapsed_hours": round(elapsed, 2),
            "arrive_local": hhmm(arrive),
            "sunset_local": hhmm(sunset),
            "civil_dusk_local": hhmm(civil),
            "daylight_left_hours": round(sunset - arrive, 2) if sunset else None,
            "usable_light_left_hours": round(civil - arrive, 2) if civil else None,
        })

    (DATA / "daylight.json").write_text(json.dumps(
        {"depart_local": hhmm(DEPART_LOCAL), "break_fraction": BREAK_FRACTION,
         "date": f"{YEAR}-{MONTH:02d}-{DAY:02d}", "rows": out}, indent=2))

    # Report only the stops inside a sane halfway band and detour budget.
    band = [o for o in out if 0.40 <= o["frac_of_trip"] <= 0.68 and o["detour_min"] <= 60]
    band.sort(key=lambda o: -o["daylight_left_hours"])

    print(f"Depart Gainesville {hhmm(DEPART_LOCAL)} EST, "
          f"{int(BREAK_FRACTION*100)}% break overhead, {YEAR}-{MONTH}-{DAY}\n")
    print("{:<34} {:>5} {:>7} {:>7} {:>7} {:>7} {:>6} {:>5}".format(
        "stop", "sat_h", "arrive", "sunset", "daylt", "dusk+", "det_m", "frac"))
    print("-" * 92)
    for o in band:
        print("{:<34} {:>5.2f} {:>7} {:>7} {:>7.2f} {:>7.2f} {:>6.0f} {:>5.2f}".format(
            o["stop"], o["sat_hours"], o["arrive_local"], o["sunset_local"],
            o["daylight_left_hours"], o["usable_light_left_hours"],
            o["detour_min"], o["frac_of_trip"]))

    print("\nSunday drive home from each (hours):")
    for o in sorted(band, key=lambda x: x["sun_hours"]):
        print(f"  {o['stop']:<34} {o['sun_hours']:.2f}  ({o['sun_miles']:.0f} mi)")


if __name__ == "__main__":
    main()
