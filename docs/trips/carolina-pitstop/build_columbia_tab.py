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
    "standing": "usual hours, not checked for the 28th",
    "confirmed": "confirmed for the 28th",
    "unknown": "couldn't find",
}
VERDICT = {"open": "Open", "opens": "Opens while you're there", "shut": "Shut", "closed": "Shut",
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
        desc="""Shrimp boats tie up on the Darien River by the waterfront park. A mile away is Fort
          King George, a rebuilt wooden fort from 1721, with a small museum and wide views over the
          marsh. Eat lunch by the river, then let the kids run around the fort.""",
        cost="Fort tickets: <b>about $26 for four</b> ($8.25 adult, $4.75 ages 6–17). From the Explore Georgia listing, standing",
        costShort="~$26 + lunch",
        lunch="""<a href="https://www.exploregeorgia.org/darien/food-drink/casual-full-service/skippers-fish-camp"
          target="_blank" rel="noopener">Skipper's Fish Camp</a>, on the river where the boats dock.
          Local shrimp, and a turtle pond outside that kids like.""",
        note="""Websites disagree on which days the fort opens, but all say Saturday, 9–5. To be
          sure, call 912-437-4770. This stop is before the halfway point, so the second drive is
          the longer one.""",
        url_fix={"Fort King George State Historic Site":
                 "https://exploregeorgia.org/darien/general/historic-sites-trails-tours/fort-king-george-state-historic-site"},
    ),
    "trains": dict(
        name="Savannah railroad museum", place="Savannah, GA · off I-16", tag="Most to do indoors",
        short="Trains",
        desc="""The Georgia State Railroad Museum is in the old railroad works. It has a roundhouse
          with a turntable, old engines and the original workshops, plus a hands-on science area
          that the ticket covers. Great for kids who like trains, and some of it is indoors.""",
        cost="Tickets: <b>$68 for four</b> ($20 adult, $14 ages 3–12). From the museum's own page, standing",
        costShort="$68",
        lunch="""The museum has picnic tables. A family travel guide suggests the Whistlestop Café
          across the street. We didn't check either.""",
        note="""Short train rides run on "select days"; we couldn't find out if the 28th is one.
          Outdoor areas close in bad weather. Call 912-651-6823 that morning.""",
    ),
    "planes": dict(
        name="Mighty Eighth museum", place="Pooler, GA · I-95 exit 102", tag="Right off the interstate",
        short="B-17",
        desc="""The National Museum of the Mighty Eighth Air Force, a minute off I-95. It tells the
          story of the WWII bomber crews, and a restored B-17 bomber, the
          <em>City of Savannah</em>, sits inside the main hall.""",
        cost="Tickets: <b>about $47 for four</b> ($13.91 adult, $9.63 ages 6–12). From another site's list, year unknown",
        costShort="~$47 (unconfirmed)",
        lunch="We didn't look for lunch at this exit. Downtown Savannah is the nearest local food.",
        note="We couldn't get prices from the museum's own site. Call 912-748-8888.",
    ),
    "back-roads": dict(
        name="Statesboro", place="Georgia · I-16, then US-301", tag="Different road · off I-95",
        short="Raptors",
        desc="""The only option that leaves I-95. It goes up through country roads in South
          Carolina on US-301. Eat lunch at an old downtown barbecue place, then visit Georgia
          Southern's wildlife center, where owls, hawks and eagles live in outdoor homes.""",
        cost="Wildlife center tickets: <b>could not find</b>",
        costShort="unknown + lunch",
        lunch="""<a href="https://visitstatesboro.org/places-to-eat/vandys-bar-b-q-downtown"
          target="_blank" rel="noopener">Vandy's Bar-B-Q</a>, the oldest barbecue place in town,
          says local news. Eat first: the newest report says it closes at 2pm (an older one says
          3pm).""",
        note="""The university is on Thanksgiving break. We couldn't find out if the center keeps its
          usual Saturday hours (1–4:45pm) on the 28th. Call 912-478-0831 before you pick this one.""",
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
    dict(name="Gather COLA", url="https://www.gathercola.com", pill=["good", "Next to the park"],
         walk=walk("gather"), meta="Sat 10am–11pm (standing) · order at the counter · $–$$",
         desc="""A food hall with an open courtyard and about a dozen local stalls: burgers,
           barbecue, Tex-Mex, chicken and waffles, gyros, bánh mì, Cajun seafood and more. Everyone
           can pick something different. The easiest dinner before or after the lights.""",
         note="Last winter it closed earlier (10pm on Saturdays)."),
    dict(name="Coastal Crust", url="https://www.coastalcrust.com/columbia", pill=["flat", "Pizza"],
         walk=["next door to Gather COLA"], meta="Sat 11am–10pm (standing) · no bookings",
         desc="""Wood-fired pizza in a restored building on the BullStreet site. Opened in August 2026.""",
         note="All the seats are outside, so it may be cold. It's a small local chain."),
    dict(name="The War Mouth", url="https://www.thewarmouth.com", pill=["flat", "Southern food"],
         walk=walk("warmouth"), meta="Sat 11:30am–10pm (standing) · $$ · call ahead for 6 or more",
         desc="""Local barbecue and Southern cooking from a chef-run kitchen. The closest real
           sit-down dinner to the park."""),
    dict(name="Villa Tronco", url="https://www.villatronco.com", pill=["flat", "In an old firehouse"],
         walk=walk("villa"), meta="Sat 5–9pm (standing) · $$–$$$ · book on Tock or call 803-256-7677",
         desc="""A family Italian place, open since 1940, in an old firehouse. It says it's the
           oldest restaurant in South Carolina.""",
         note="It closes at 9pm, so go before the lights."),
    dict(name="Transmission Arcade", url="https://www.transmissionarcade.com", pill=["good", "Games + food"],
         walk=walk("transmission"), meta="Sat noon–2am (standing) · $ · kids welcome until 8pm",
         desc="""Pinball and arcade games, with food, homemade ice cream and beignets. Lots of fun
           for not much money.""",
         note="Kids must leave by 8pm, so go before the lights, not after."),
    dict(name="The Grand on Main", url="https://www.thegrandonmain.com", pill=["flat", "Bowling"],
         walk=walk("grand"), meta="Hours: couldn't find on its site · book lanes online",
         desc="""A small bowling alley with a restaurant. You can book a lane and dinner together.""",
         note="Some sites say adults only after 10pm. Check family hours before you book."),
]
dessert = [
    dict(name="Sweet Cream Co.", url="https://www.sweetcreamcompany.com", pill=["good", "Open after the lights"],
         walk=walk("sweetcream"), meta="Sat 1–10pm (standing) · 1627 Main St",
         desc="""Homemade ice cream on Main Street. Open late, so you can stop on the way back from the lights."""),
    dict(name="Kaminsky's Dessert Café", url="https://www.kaminskys.com/location/columbia/",
         pill=["good", "Open late"], walk=walk("kaminskys"), meta="Sat noon–1am (standing) · Gervais St, Vista",
         desc="""Huge slices of cake, sundaes and cookie pie. Closer to the hotel than Sweet Cream.
           It also has a bar, so it gets busier later at night."""),
    dict(name="Transmission Arcade", url="https://www.transmissionarcade.com", pill=["flat", "Before 8pm only"],
         walk=walk("transmission"), meta="Homemade ice cream, beignets",
         desc="Have dessert with the games before the lights. Kids must leave by 8pm."),
    dict(name="Cocobowlz at Gather COLA", url="https://www.gathercola.com/vendors", pill=["flat", "Next to the park"],
         walk=walk("gather"), meta="Food hall open to 11pm; this stall's closing time unknown",
         desc="Smoothies, açaí bowls and fruit treats, a short walk from the gate."),
]
free = [
    dict(name="Finlay Park", url="https://parksandrec.columbiasc.gov/regionalparks/", pill=["good", "Free · playground"],
         walk=walk("finlay"), meta="6am–9pm (standing) · free",
         desc="""Downtown's big park. It reopened in November 2025 after a $25 million rebuild, with
           a large playground on the hillside and a waterfall. The best free hour of the trip, if
           you get there while it's still light.""",
         note="The splash pad is only open in summer. We couldn't check the park's own website."),
    dict(name="Riverfront Park & the canal", url="https://parksandrec.columbiasc.gov/regionalparks/",
         pill=["good", "Free · nearest the hotel"], walk=walk("riverfront"), meta="Dawn to dusk (standing) · free",
         desc="""A flat, paved path along the old canal and the river. The closest thing to the
           hotel. A good place to stretch your legs after you check in."""),
    dict(name="Page Ellington Park", url="https://parksandrec.columbiasc.gov/regionalparks/",
         pill=["flat", "Free · next to the park"], walk=["walk time not measured"],
         meta="Hours: couldn't find · free",
         desc="""Paths around a pond, right by Segra Park. A short walk before the gates open, if
           it's still light.""",
         note="We found no playground. We couldn't pin down the address, so there's no walk time."),
    dict(name="Boyd Plaza & Columbia Museum of Art", url="https://www.columbiamuseum.org/visit",
         pill=["flat", "Plaza free"], walk=walk("cma"),
         meta="Museum Sat 10am–5pm · about $40 for four (under-7s free), standing",
         desc="""The plaza on Main Street is free to walk around. The museum costs money and closes at 5."""),
    dict(name="SC State House grounds", url="https://scstatehouse.gov/visit.php", pill=["flat", "Outside only"],
         walk=walk("statehouse"), meta="No tours on the Saturday after Thanksgiving (confirmed)",
         desc="""You can walk past the monuments and find the bronze stars that mark where
           cannonballs hit the walls in the Civil War. No tours this Saturday.""",
         note="We couldn't find the grounds' opening hours."),
    dict(name="EdVenture Children's Museum", url="https://edventure.org", pill=["warn", "Paid · closes 5pm"],
         walk=walk("edventure"), meta="Sat 9am–5pm · $15 each, about $60 for four (standing)",
         desc="""A big hands-on children's museum. Only worth it if you get to the hotel well
           before 4pm, and none of the stops above does that if you leave at 9am."""),
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
    "mapNote": """The Darien, Savannah and Pooler routes use the same roads (I-95, then I-26), so
      their lines overlap on the map. Only the Statesboro route takes a different road.""",
    "hotel": {"name": "Staybridge Suites Columbia", "address": "1913 Huger St, Columbia SC 29201",
              "checkin": "3pm", "checkin_h": 15, "checkout": "noon", "phone": "803-451-5900"},
    "lights": {"name": "Fireflies Holiday Lights", "window": [18, 21],
               "url": "https://www.milb.com/columbia/news/260724-fireflies-holiday-lights-to-make-spirits-even-brighter-at-segra-park-this-winter",
               "when": "Segra Park · 6–9pm, <b>last entry 8:30pm</b>",
               "price": "<b>Tickets bought for all four of us.</b> Inside: s'mores fire pits, "
                        "light tunnels and a kids' train (ages 12 and under; we don't know if it costs extra)."},
    "hotelSegra": {"mi": round(hs[0], 1), "min": hs[1]},
    "parkingNote": "We couldn't find any parking details for the lights. Plan to drive, and ask the box office.",
    "standfirst": f"""We're booked at the Staybridge Suites on Huger Street, and we have tickets for
      the Fireflies lights at Segra Park. The drive takes {round(direct_s/3600, 1)} hours with no
      stops, so one good stop near the middle, with lunch, splits it into two shorter drives.
      Here are {["no", "one", "two", "three", "four", "five", "six"][len(options)]} different
      places to stop. Pick one, and the map, the timeline and the numbers all update.""",
    "evening": f"""The hotel and the ballpark are {round(hs[0], 1)} miles apart on foot, so there are
      three ways to do dinner: <strong>eat next to the park</strong> (Gather COLA is
      {W["gather"]["to_segra"][1]} minutes' walk from the gate), <strong>eat on Main Street</strong>,
      {min(mid)}–{max(mid)} minutes' walk from either, or eat near the hotel. If you leave at
      {h_to_clock(options[0]["depart_h"])}, the earliest you reach Columbia is
      {h_to_clock(earliest)}, and sunset is {h_to_clock(sunset_h)}. So the outdoor things below only
      work if you leave earlier: every hour earlier from Gainesville gives you an hour more
      daylight in Columbia. The Soda City market ends at 1pm, and we found no parade or tree
      lighting downtown on the 28th.""",
    "dine": dine, "dessert": dessert, "free": free,
    "calls": [
        {"who": "Fireflies box office", "tel": "803-726-4487",
         "why": "Tickets are done. Ask about parking, and whether Santa is there on the 28th (this year's announcement doesn't say)."},
        {"who": "Your halfway stop", "tel": "",
         "why": "Each stop above lists its phone number and what to ask. Statesboro is the riskiest: it may be closed for Thanksgiving break."},
        {"who": "Not checked", "tel": "",
         "why": "Coastal Crust's winter hours; family hours at The Grand on Main; whether Soda City runs on a holiday weekend; when Vandy's closes (2pm or 3pm); the Mighty Eighth's 2026 prices."},
    ],
    "footer": f"""<p>Drive times all come from the same free route planner (Valhalla, using
      OpenStreetMap). They assume no traffic. The Saturday after Thanksgiving will be busier on
      I-95, so expect longer. Arrival times assume you leave at
      {h_to_clock(options[0]['depart_h'])} and make just the one stop. Walk times are for an
      adult; a six-year-old will be slower. Sunset time is calculated, not looked up.</p>
      <p>Opening hours are each place's usual hours. We only confirmed the lights and the State
      House tours for 28 November itself. Prices are as listed online, not live quotes.</p>
      <p>The booking confirmation number is not on this page, because anyone with the link can
      see it. The files that build this tab are in <code>docs/trips/carolina-pitstop/</code> in
      the locationAnalyzer repo.</p>""",
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
