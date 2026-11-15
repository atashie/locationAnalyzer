"""Build the Carolina Pitstop page: tab 1 (five towns, unchanged) + tab 2 (booked Columbia Saturday).

    python build_columbia_tab.py            # writes carolina-pitstop.html next to this file

Inputs (all in this folder):
  page_base.html  - the published page with the tab shell; contains the /*COLA_DATA*/ marker
  measured.json   - itinerary_compare.py output for spec.json (drive legs, arrivals, hours verdicts)
  walks.json      - walk.py output (Valhalla pedestrian, venue -> Segra Park / hotel)
  cola_map.json   - project.py output (routes projected into the page's existing map frame)

Every number shown on tab 2 is derived here or in the page from those files. Hand-written
copy below carries facts from research (hours, prices) with their status; it carries no
drive or walk figures of its own -- grep this file for digits before publishing.
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
M = json.loads((HERE / "measured.json").read_text())
W = json.loads((HERE / "walks.json").read_text())
MAP = json.loads((HERE / "cola_map.json").read_text())

STATUS = {
    "standing": "standing hours, date not checked",
    "confirmed": "confirmed for the 28th",
    "unknown": "could not determine",
}
VERDICT = {"open": "Open", "opens": "Opens during stop", "shut": "Shut", "closed": "Shut",
           "unknown": "Hours unknown"}


def walk(key: str) -> list[str]:
    v = W[key]
    return [f"<b>{v['to_segra'][1]} min</b> to Segra", f"<b>{v['to_hotel'][1]} min</b> to hotel"]


def h_to_clock(h: float) -> str:
    m = round(h * 60)
    hh, mm = divmod(m, 60)
    return f"{hh % 12 or 12}:{mm:02d}{'am' if hh < 12 else 'pm'}"


# ---------------------------------------------------------------- halfway options
CONTENT = {
    "fort-and-shrimp-boats": dict(
        name="Darien", place="Georgia · I-95 exit 49", tag="Earliest · outdoors", short="Darien",
        desc="""Shrimp boats tie up along the Darien River right by the waterfront park, and a mile
          away Fort King George is a rebuilt 1721 cypress blockhouse — the oldest English fort on
          the Georgia coast — with a small museum, earthworks and big marsh views. Lunch on the
          river, then let the boys run the fort.""",
        cost="Fort admission: <b>about $26 for four</b> ($8.25 adult, $4.75 ages 6–17) — Explore Georgia listing, standing",
        costShort="~$26 + lunch",
        lunch="""<a href="https://www.exploregeorgia.org/darien/food-drink/casual-full-service/skippers-fish-camp"
          target="_blank" rel="noopener">Skipper's Fish Camp</a>, on the river where the boats dock —
          local wild-caught shrimp, and a turtle pond outside that one travel writer says kids love.""",
        note="""Sources disagree on the fort's days (Thu–Sat or Tue–Sat, 9–5) — Saturday is open in
          both, but ring 912-437-4770. This stop comes earlier than halfway, so the second leg is
          the long one.""",
        url_fix={"Fort King George State Historic Site":
                 "https://exploregeorgia.org/darien/general/historic-sites-trails-tours/fort-king-george-state-historic-site"},
    ),
    "trains": dict(
        name="Savannah railroad museum", place="Savannah, GA · off I-16", tag="Most to do indoors",
        short="Trains",
        desc="""The Georgia State Railroad Museum is the old Central of Georgia railroad works: a
          roundhouse with a turntable, engines and the original shop buildings, plus a STEAM Center
          that's included in the ticket. A real train-kid afternoon, and partly under cover.""",
        cost="Admission: <b>$68 for four</b> ($20 adult, $14 ages 3–12) — museum's own page, standing",
        costShort="$68",
        lunch="""The museum has picnic tables, and a family-travel guide points to the Whistlestop Café
          across the street — neither was checked.""",
        note="""Short train rides run "select days, 10am–3pm hourly"; whether the 28th is one wasn't
          published. Outdoor sections close in bad weather — ring 912-651-6823 that morning.""",
    ),
    "planes": dict(
        name="Mighty Eighth museum", place="Pooler, GA · I-95 exit 102", tag="Right off the interstate",
        short="B-17",
        desc="""The National Museum of the Mighty Eighth Air Force, a minute off I-95: the story of
          the WWII bomber crews, built around a restored B-17 Flying Fortress, the
          <em>City of Savannah</em>, parked inside the main hall.""",
        cost="Admission: <b>about $47 for four</b> ($13.91 adult, $9.63 ages 6–12) — a third-party list of unknown year",
        costShort="~$47 (unconfirmed)",
        lunch="Not researched for this exit; downtown Savannah is the nearest local food.",
        note="The museum's own page wouldn't show prices to an automated check. Ring 912-748-8888.",
    ),
    "back-roads": dict(
        name="Statesboro", place="Georgia · I-16, then US-301", tag="Different road · off I-95",
        short="Raptors",
        desc="""The only option that leaves I-95 in Georgia and comes up through rural South
          Carolina on US-301 instead. The stop is Georgia Southern's Center for Wildlife Education
          and its raptor center — owls, hawks and eagles in outdoor habitats — after lunch at a
          downtown barbecue institution.""",
        cost="Wildlife center admission: <b>could not determine</b>",
        costShort="unknown + lunch",
        lunch="""<a href="https://visitstatesboro.org/places-to-eat/vandys-bar-b-q-downtown"
          target="_blank" rel="noopener">Vandy's Bar-B-Q</a>, which local news calls Statesboro's
          oldest barbecue restaurant. Eat first: the latest local report has it closing at 2pm (an older listing
          says 3pm).""",
        note="""The university is on Thanksgiving break, and whether the center keeps its Saturday
          1–4:45pm opening on the 28th wasn't published. Ring 912-478-0831 before choosing this.""",
    ),
}

options = []
for key, o in M["options"].items():
    c = CONTENT[key]
    stop_key = o["stops"][0]
    sched = o["schedule"][0]
    facs = []
    for f in sched["hours"]["facilities"]:
        facs.append({
            "name": f["name"],
            "url": c.get("url_fix", {}).get(f["name"], f.get("url")),
            "verdict": f["verdict"],
            "verdictLabel": VERDICT.get(f["verdict"], f["verdict"]),
            "detail": f["detail"].replace(" -- ", " — "),
            "statusLabel": STATUS[f.get("status", "unknown")],
        })
    options.append({
        "id": key, "stop": stop_key, "name": c["name"], "place": c["place"], "tag": c["tag"],
        "short": c["short"], "desc": c["desc"], "cost": c["cost"], "costShort": c["costShort"],
        "lunch": c.get("lunch"), "note": c.get("note"),
        "corridor": o["corridor"], "legs_s": o["legs_s"], "total_s": o["total_s"],
        "detour_s": o["detour_s"], "miles": round(o["miles"]), "depart_h": o["depart_h"],
        "arrive_h": o["arrive_h"], "arrive": h_to_clock(o["arrive_h"]),
        "stopArrive": h_to_clock(sched["arrive_h"]), "dwell_min": round(sched["dwell_min"]),
        "share": o["legs_s"][0] / o["total_s"], "facilities": facs,
    })

# ---------------------------------------------------------------- evening venues
dine = [
    dict(name="Gather COLA", url="https://www.gathercola.com", pill=["good", "Beside the park"],
         walk=walk("gather"), meta="Sat 10am–11pm (standing) · counter service · $–$$",
         desc="""A food hall with an open courtyard and a dozen local vendors — burgers, cheesesteaks,
           Tex-Mex, chicken and waffles, barbecue, gyros, bánh mì, Cajun seafood, açaí — so all four
           of you order something different. The easiest dinner before or after the lights.""",
         note="Its winter hours in January 2026 were shorter (to 10pm on Saturdays)."),
    dict(name="Coastal Crust", url="https://www.coastalcrust.com/columbia", pill=["flat", "Pizza"],
         walk=["next door to Gather COLA"], meta="Sat 11am–10pm (standing) · no reservations",
         desc="""Wood-fired Neapolitan pizza in the Williams Building on the BullStreet campus,
           opened in August 2026.""",
         note="All seating is outdoors — cold in late November. It's a small SC chain, not a one-off."),
    dict(name="The War Mouth", url="https://www.thewarmouth.com", pill=["flat", "Local Southern"],
         walk=walk("warmouth"), meta="Sat 11:30am–10pm (standing) · $$ · call ahead for 6+",
         desc="""Whole-hog barbecue and Southern cooking in Cottontown, a local chef-run place, and the
           closest proper sit-down meal to the park."""),
    dict(name="Villa Tronco", url="https://www.villatronco.com", pill=["flat", "In an old firehouse"],
         walk=walk("villa"), meta="Sat 5–9pm (standing) · $$–$$$ · book on Tock or 803-256-7677",
         desc="""Family Italian since 1940, in a 19th-century firehouse; it bills itself as the
           oldest restaurant in South Carolina.""",
         note="Closes at 9pm, so it only works as dinner before the lights."),
    dict(name="Transmission Arcade", url="https://www.transmissionarcade.com", pill=["good", "Games + food"],
         walk=walk("transmission"), meta="Sat noon–2am (standing) · $ · all ages until 8pm",
         desc="""Pinball and arcade cabinets with a kitchen — and homemade ice cream and beignets.
           The most fun the boys will have per dollar on Main Street.""",
         note="Kids are allowed only until 8pm: go before the lights, not after."),
    dict(name="The Grand on Main", url="https://www.thegrandonmain.com", pill=["flat", "Bowling"],
         walk=walk("grand"), meta="Hours: could not determine from its own site · lanes bookable online",
         desc="""A boutique bowling alley with a restaurant attached, rebuilt after a 2022 fire. Book a
           lane and dinner together.""",
         note="Listings say 21+ after 10pm; check the family hours before booking."),
]
dessert = [
    dict(name="Sweet Cream Co.", url="https://www.sweetcreamcompany.com", pill=["good", "Open after the lights"],
         walk=walk("sweetcream"), meta="Sat 1–10pm (standing) · 1627 Main St",
         desc="""Small-batch ice cream on Main Street. Open late enough for a stop on the way back from Segra Park."""),
    dict(name="Kaminsky's Dessert Café", url="https://www.kaminskys.com/location/columbia/",
         pill=["good", "Open late"], walk=walk("kaminskys"), meta="Sat noon–1am (standing) · Gervais St, Vista",
         desc="""Towering cakes, sundaes and cookie pie in the Vista — the closer of the two to the
           hotel. Also serves cocktails, so it gets livelier as the night goes on."""),
    dict(name="Transmission Arcade", url="https://www.transmissionarcade.com", pill=["flat", "Before 8pm only"],
         walk=walk("transmission"), meta="Homemade ice cream, beignets",
         desc="Pair it with the arcade before the lights — under-21s must be out by 8pm."),
    dict(name="Cocobowlz at Gather COLA", url="https://www.gathercola.com/vendors", pill=["flat", "Beside the park"],
         walk=walk("gather"), meta="Hall open to 11pm; the vendor's own closing time unknown",
         desc="Smoothies, açaí bowls and fruit treats, a few minutes' walk from the gate."),
]
free = [
    dict(name="Finlay Park", url="https://parksandrec.columbiasc.gov/regionalparks/", pill=["good", "Free · playground"],
         walk=walk("finlay"), meta="6am–9pm (standing) · free",
         desc="""Downtown's big park, reopened in November 2025 after a $25 million rebuild: a
           destination playground built into the hillside and the restored waterfall. The best
           free hour of the trip, if you arrive with daylight to spare.""",
         note="The splash pad is summer-only. The park's own site blocks automated checks."),
    dict(name="Riverfront Park & the canal", url="https://parksandrec.columbiasc.gov/regionalparks/",
         pill=["good", "Free · nearest the hotel"], walk=walk("riverfront"), meta="Dawn to dusk (standing) · free",
         desc="""A flat paved path along the old Columbia Canal and the Congaree, closest of anything
           to the hotel. A good leg-stretch the minute you've checked in."""),
    dict(name="Page Ellington Park", url="https://parksandrec.columbiasc.gov/regionalparks/",
         pill=["flat", "Free · beside the park"], walk=["walk not measured — address unclear"],
         meta="Hours: could not determine · free",
         desc="""Twenty acres of paths around a two-acre pond on the BullStreet campus, the only green
           space right by Segra Park. A short loop before the gates open, if it's still light.""",
         note="No playground found, and the address geocoded to the wrong place, so no walk time."),
    dict(name="Boyd Plaza & Columbia Museum of Art", url="https://www.columbiamuseum.org/visit",
         pill=["flat", "Plaza free"], walk=walk("cma"),
         meta="Museum Sat 10am–5pm · about $40 for four (under-7s free) — standing",
         desc="""The plaza on Main Street is free to wander; the museum itself is paid, and closes at 5."""),
    dict(name="SC State House grounds", url="https://scstatehouse.gov/visit.php", pill=["flat", "Grounds only"],
         walk=walk("statehouse"), meta="Tours: not offered on the Saturday after Thanksgiving — confirmed",
         desc="""The grounds, monuments and the bronze stars marking where Sherman's shells hit the
           walls are a walk-by. No tour this particular Saturday.""",
         note="Grounds hours could not be determined."),
    dict(name="EdVenture Children's Museum", url="https://edventure.org", pill=["warn", "Paid · closes 5pm"],
         walk=walk("edventure"), meta="Sat 9am–5pm · $15 per person, ~$60 for four — standing",
         desc="""A big hands-on children's museum in the Vista. Only worth it if you reach the hotel
           well before 4pm, which none of the halfway options does at a 9am start."""),
]

direct_s = M["direct"]["total_s"]
earliest = min(o["arrive_h"] for o in options)
sunset_h = 17 + 16 / 60  # NOAA calculation for Columbia on 28 Nov, from itinerary_compare.py
assert all(o["sunset"] == "17:16" for o in M["options"].values())
hs = W["hotel_segra"]
mid = [W[k][d][1] for k in ("transmission", "grand", "sweetcream") for d in ("to_segra", "to_hotel")]
assert all(o["arrive_h"] >= int(earliest) for o in options)

COLA = {
    "options": options,
    "direct_s": direct_s,
    "sunset_h": sunset_h,
    "map": MAP,
    "mapNote": """The Darien, Savannah and Pooler routes are the same road — I-95, then I-26 from
      Walterboro — and overlap on the map almost all the way. Statesboro's is the one genuinely
      different road.""",
    "hotel": {"name": "Staybridge Suites Columbia", "address": "1913 Huger St, Columbia SC 29201",
              "checkin": "3pm", "checkin_h": 15, "checkout": "noon", "phone": "803-451-5900"},
    "lights": {"name": "Fireflies Holiday Lights", "window": [18, 21],
               "url": "https://www.milb.com/columbia/news/260724-fireflies-holiday-lights-to-make-spirits-even-brighter-at-segra-park-this-winter",
               "when": "Segra Park · 6–9pm, <b>last entry 8:30pm</b> · the 28th is a regular open night",
               "price": "<b>$10 a ticket</b> in November, +$2 each if bought on the day, under-2s free — "
                        "about $40 for four plus fees. S'mores pits, light tunnels and a kids' train (12 and under, price not stated) inside."},
    "hotelSegra": {"mi": round(hs[0], 1), "min": hs[1]},
    "parkingNote": "Parking arrangements for the lights weren't published in anything found — plan to drive and ask the box office.",
    "standfirst": f"""We're booked: Staybridge Suites on Huger Street, then the Fireflies lights at
      Segra Park. Direct, the drive is {round(direct_s/3600, 1)} hours — so one proper stop near
      the middle, with lunch, turns a long haul into two short ones. {["No", "One", "Two", "Three", "Four", "Five", "Six"][len(options)]} places that do that, each
      different: pick one and the map, the day and the totals all change.""",
    "evening": f"""The hotel and the ballpark are {round(hs[0], 1)} miles apart on foot, so the
      evening splits three ways: <strong>eat beside the park</strong> (Gather COLA is {W["gather"]["to_segra"][1]} minutes' walk from
      the gate), <strong>eat in the middle</strong> on the 1600–1700 blocks of Main
      Street, {min(mid)}–{max(mid)} minutes' walk from either, or eat near the hotel. Every option reaches Columbia
      after {h_to_clock(int(earliest))} at a {h_to_clock(options[0]["depart_h"])} start — the earliest is {h_to_clock(earliest)}, with sunset at
      {h_to_clock(sunset_h)} — so the daylight things here only fit if you leave earlier: each hour
      sooner out of Gainesville is an hour more light in Columbia. Soda City market is over by 1pm,
      and nothing else downtown — no parade, no tree lighting — was found for the 28th.""",
    "dine": dine, "dessert": dessert, "free": free,
    "calls": [
        {"who": "Fireflies box office", "tel": "803-726-4487",
         "why": "Buy ahead (the price rises $2 a ticket on the day), and ask about parking and whether Santa is there on the 28th — the 2026 release doesn't mention him."},
        {"who": "Your halfway stop", "tel": "",
         "why": "Each stop card above has its own number and the one thing worth asking. Statesboro's Thanksgiving-break opening is the one that could sink a plan."},
        {"who": "Not verified", "tel": "",
         "why": "Coastal Crust's winter hours; The Grand on Main's family hours; whether Soda City runs on a holiday weekend; Vandy's closing time (2pm or 3pm); the Mighty Eighth's 2026 prices."},
    ],
    "footer": f"""<p>Drive times come from one routing engine (public Valhalla on OpenStreetMap
      data), free-flow, with no traffic: the Saturday after Thanksgiving on I-95 will be slower, so
      treat them as a floor. Arrivals assume leaving at {h_to_clock(options[0]['depart_h'])} with
      the one stop and no other break. Walk times use the same engine's pedestrian routing at an
      adult pace — expect a six-year-old to be slower. Sunset is calculated, not published.</p>
      <p>Opening hours are each venue's standing published hours unless marked otherwise; no
      restaurant or museum here was confirmed for 28 November itself, apart from the lights and the
      State House tour closure. Prices are as published, not live quotes.</p>
      <p>The booking confirmation number is deliberately left off this page, since the link can be
      shared. Source for this tab: <code>docs/trips/carolina-pitstop/</code> in the locationAnalyzer
      repo — spec.json, measured.json, walks.json and build_columbia_tab.py rebuild it.</p>""",
}

base = (HERE / "page_base.html").read_text(encoding="utf-8")
assert base.count("/*COLA_DATA*/null") == 1
out = base.replace("/*COLA_DATA*/null", json.dumps(COLA, ensure_ascii=False))
(HERE / "carolina-pitstop.html").write_text(out, encoding="utf-8")

# checks on the figures this script computed
for o in options:
    assert abs(sum(o["legs_s"]) - o["total_s"]) < 1, o["id"]
    assert o["arrive_h"] > 15, "every option should reach the hotel after check-in opens"
    assert 0.3 < o["share"] < 0.7, o["id"]
print({o["id"]: (o["stopArrive"], o["arrive"], round(o["share"] * 100)) for o in options})
print("hotel<->segra", hs, "| wrote", len(out), "bytes")
