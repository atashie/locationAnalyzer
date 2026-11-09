#!/usr/bin/env python3
"""Assemble spec.json from the committed research candidates plus the choices below.

research/*.json holds every candidate the 2026-11-08 search found (about 100 activity
stops and 100+ lunch places across the three corridors), in the research brief's schema.
This script picks from them, normalises their hours into fields itinerary_compare.py can
check, groups lunch places into "lunch: pick one" stops, and writes spec.json.

Editing a choice here and re-running costs nothing; only a changed route re-measures:

    python assemble_spec.py && python ../../itinerary_compare.py --spec spec.json \\
        --date 2026-11-25 --utc-offset -5 --out measured.json && python build_page.py
"""
import json, os, re

D = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(D, "research")
CAND = {}
for fn in sorted(os.listdir(R)):
    if fn.endswith(".json"):
        if fn.startswith("carried_over"):
            continue
        for c in json.load(open(os.path.join(R, fn), encoding="utf-8")):
            CAND.setdefault(c["key"], c)      # first file wins on a duplicate key

SUNSET = "17:30"   # Thomasville 17:35, inland SC/GA within a few minutes; labelled where used
SUNRISE = "07:00"
HHMM = re.compile(r"^\d{1,2}:\d{2}$")

def norm_fac(fc):
    """Research hours -> checkable fields. 'sunset'/'dusk'/'dark' become 17:30 and say so in
    the name; anything that cannot be made checkable stays without hours, which the tool
    reports as unknown rather than shut."""
    out = {k: fc[k] for k in ("name", "url", "status", "note", "destination") if fc.get(k)}
    out.setdefault("status", "standing")
    if fc.get("always"):
        out["always"] = True
        return out
    days = fc.get("days") or "daily"
    days = re.sub(r"\s*\d{4}-\d{2}-\d{2}", "", days).strip() or "daily"
    o, c = fc.get("open"), fc.get("close")
    if c == "24:00":
        c = "23:59"                          # midnight close; the tool wants a real clock time
    hint = " ".join(str(x) for x in (c, fc.get("note", ""), fc.get("name", ""))).lower()
    if o and not HHMM.match(str(o)) and re.search(r"dawn|sunrise", str(o).lower()):
        o, out["name"] = SUNRISE, out["name"] + " (from dawn)"
    if c and not HHMM.match(str(c)) and re.search(r"sunset|dusk|dark", str(c).lower()) and o == SUNRISE:
        pass
    if (not o) and re.search(r"dawn|sunrise", hint):
        o, out["name"] = SUNRISE, out["name"] + " (from dawn)"
    if c and not HHMM.match(str(c)) and re.search(r"sunset|dusk|dark", str(c).lower()):
        c, out["name"] = SUNSET, out["name"] + " (to sunset)"
    if o and not c and re.search(r"sunset|dusk|dark", hint):
        c, out["name"] = SUNSET, out["name"] + " (to sunset)"
    if o and c and HHMM.match(str(o)) and HHMM.match(str(c)):
        out.update({"days": days, "open": o, "close": c})
        if fc.get("last_entry") and HHMM.match(str(fc["last_entry"])):
            out["last_entry"] = fc["last_entry"]
    elif fc.get("note") is None:
        out["note"] = "hours not published"
    return out

def stop(key, role, dwell=None, name=None, facilities=None, keep=None, **over):
    c = CAND[key]
    facs = facilities if facilities is not None else [norm_fac(f) for f in c.get("facilities", [])]
    if keep is not None:
        facs = [facs[i] for i in keep]
    s = {"name": name or c["name"], "where": c["where"], "lat": c["lat"], "lon": c["lon"],
         "dwell_min": dwell or c.get("suggested_dwell_min") or 30,
         "cost_usd": c.get("cost_usd"), "cost_note": c.get("cost_note", ""),
         "url": c["url"], "status": c.get("status", "standing"), "kind": c.get("kind", "outdoors"),
         "role": role, "facilities": facs}
    s.update(over)
    if s["cost_usd"] is None:
        # The tool sums numbers. An unpublished price is carried as 0 plus an explicit flag,
        # and the page renders the option total with a "+" rather than as free.
        s["cost_usd"], s["cost_unpublished"] = 0, True
    return s

def lunch(anchor_key, name, where, food_keys, dwell=45, extra=()):
    """A lunch stop is a short list of places a few minutes apart, each with its own hours.
    It is routed to the first place that has coordinates."""
    facs, pts = [], []
    for k in food_keys:
        f = CAND[k]
        hrs = [norm_fac(x) for x in f.get("facilities", [])] or [{"name": f["name"]}]
        h = dict(hrs[0])
        h["name"] = f["name"]
        h.setdefault("url", f.get("url"))
        h["status"] = h.get("status", f.get("status", "standing"))
        if f.get("destination") or "destination" in json.dumps(f).lower():
            h["destination"] = True
        facs.append(h)
        if f.get("lat") and f.get("lon"):
            pts.append((f["lat"], f["lon"]))
    facs += list(extra)
    lat, lon = pts[0] if pts else (CAND[anchor_key]["lat"], CAND[anchor_key]["lon"])
    return {"name": name, "where": where, "lat": lat, "lon": lon, "dwell_min": dwell,
            "cost_usd": 0, "cost_note": "meals not costed", "url": facs[0].get("url"),
            "status": "standing", "kind": "food", "role": "lunch", "facilities": facs}

spec = json.load(open(os.path.join(D, "spec.json"), encoding="utf-8"))
# Stops researched and checked in the first pass, kept verbatim so this script can be re-run
# after it has overwritten spec.json.
old = json.load(open(os.path.join(R, "carried_over_stops.keep.json"), encoding="utf-8"))
S = {}

# ---- carried over from the first pass (researched and checked then) -------------------
S["sob"] = dict(old["sob"], role="pit", phone="843-774-2411",
                ask="are the Pantry restrooms open from 07:00?")
S["amonkey"] = dict(old["amonkey"], role="excursion", phone="843-278-5256",
                    ask="closing time on the 25th, grip-sock price, whether a holiday camp shares the floor")
S["treetop"] = dict(old["treetop"], role="excursion", phone="770-365-0356",
                    ask="does a late start still get the full 2.5 h session?")
S["scwelcome"] = dict(old["scwelcome"], role="pit", phone="864-839-6742",
                      ask="is the rebuild under way; are restrooms open before 09:00?")

# ---- coastal --------------------------------------------------------------------------
S["santee_mound"] = stop("santee_nwr_fort_watson", "pit", 35,
    name="Santee Indian Mound / Fort Watson (Santee NWR)", phone="803-478-2217",
    ask="can the mound stairs be climbed, which trails are open on the 25th?")
S["fort_mcallister"] = stop("fort_mcallister_sp", "excursion", 120, cost_usd=40.5,
    cost_note="$10 ParkPass plus fort admission $9.75 per adult and $5.50 per child; "
              "whether fort admission covers parking is not stated", phone="912-727-2339")
S["lunch_richmond_hill"] = lunch("fort_mcallister_sp", "Lunch in Richmond Hill",
    "Richmond Hill, GA - I-95 exit 87, on the way back from the fort",
    ["food_bubbas_bistro", "food_parkers_richmond_hill", "food_kroger_richmond_hill"],
    extra=[dict(old["pig_rh"]["facilities"][0], name="Smokin Pig (BBQ, one option among several)")])
S["jesup_trains"] = stop("jesup_railfan_platform", "pit", 20)
S["oatland"] = stop("oatland_island", "excursion", 105, phone="912-395-1212",   # operator site footer, checked 2026-11-08
    ask="any closure on the 25th (published list names only Thanksgiving and the day after)")
S["lunch_savannah_east"] = lunch("oatland_island", "Lunch on the east side of Savannah",
    "US-80 / Islands Expressway, a few minutes from Oatland Island",
    ["food_wileys_bbq", "food_sandfly_bbq", "food_leopolds"])
S["laura_walker"] = stop("laura_s_walker_sp", "pit", 30, keep=[0])
S["walterboro"] = stop("walterboro_wildlife_sanctuary", "pit", 30, phone="843-538-4353",
    ask="boardwalk status after storm repairs")
S["lunch_tanger"] = {
    "name": "Lunch at Adrenaline Monkey or across at Tanger Outlets",
    "where": "Centre Pointe Dr / Tanger Outlet Blvd, North Charleston",
    "lat": 32.8757911, "lon": -80.0222273, "dwell_min": 40, "cost_usd": 0,
    "cost_note": "meals not costed", "url": "https://chs.adrenalinemonkeyfun.com/drop-ins",
    "status": "standing", "kind": "food", "role": "lunch",
    "facilities": [
        {"name": "Mellow Mushroom, 4855 Tanger Outlet Blvd", "days": "Mon-Thu", "open": "11:00",
         "close": "22:00", "url": "https://www.mellowmushroom.com/locations/sc/north-charleston/4855-tanger-outlet-blvd/",
         "status": "standing"},
        {"name": "Adrenaline Monkey on-site pizza", "url": "https://chs.adrenalinemonkeyfun.com/drop-ins",
         "status": "unknown", "note": "pizza is sold on site; food hours not published"},
        dict(norm_fac(CAND["food_cfa_tanger_nchas"]["facilities"][0]) if CAND["food_cfa_tanger_nchas"].get("facilities")
             else {"status": "unknown", "note": "hours not checked"}, name="Chick-fil-A, next to Adrenaline Monkey"),
    ]}

# ---- fall line ------------------------------------------------------------------------
S["fortmill_welcome"] = stop("sc_welcome_fortmill", "pit", 15, keep=[1, 0], phone="803-548-2880",
    ask="are restrooms open before 09:00?")
S["hitchcock"] = stop("hitchcock_woods", "excursion", 105, phone="803-642-0528",
    ask="best family entrance and parking; no restrooms or water in the woods")
S["lunch_aiken"] = lunch("hitchcock_woods", "Lunch in downtown Aiken",
    "Laurens St, Aiken, SC - five minutes from Hitchcock Woods",
    ["lankys_on_laurens_140", "new_moon_cafe_aiken", "food_lion_aiken_richland_w"])
S["ocmulgee"] = stop("ocmulgee_mounds", "pit", 45, phone="478-752-8257")
S["riverbanks"] = stop("riverbanks_zoo", "excursion", 165, phone="803-779-8717",
    ask="does the Sky-High Safari ropes climb run on the 25th; winter dining hours")
S["lunch_columbia"] = lunch("riverbanks_zoo", "Lunch at the zoo or nearby in Columbia",
    "Riverbanks Zoo and Broad River Rd, Columbia, SC - I-26 exits 106-110",
    ["lizards_thicket_broad_river", "rushs_broad_river", "riverbanks_onsite_dining"], dwell=40)
S["phinizy"] = stop("phinizy_swamp", "pit", 40, keep=[0], phone="706-828-2109")
S["sesqui"] = stop("sesquicentennial_sp", "pit", 35, keep=[0, 1], phone="803-788-2706")
S["lunch_macon"] = lunch("ocmulgee_mounds", "Lunch in Macon, by the mounds",
    "Emery Hwy / downtown Macon - I-16 exit 2, by the Ocmulgee Mounds entrance",
    ["nuway_baconsfield", "hh_restaurant", "rookery_macon"])
S["ocmulgee_big"] = stop("ocmulgee_mounds", "excursion", 100,
    name="Ocmulgee Mounds National Historical Park", phone="478-752-8257")

# ---- shared I-75 afternoon ------------------------------------------------------------
S["peanut"] = stop("big_peanut_ashburn", "pit", 10)
S["rozar"] = stop("rozar_park_perry", "pit", 30)
S["lane_orchards"] = stop("lane_southern_orchards", "pit", 30, kind="playground",
                          phone="800-277-3224", ask="holiday-week hours")
S["high_falls"] = stop("high_falls_sp", "pit", 40, keep=[0], phone="478-993-3053",
    ask="does the lake drawdown change the falls?")
S["cherokee_lake"] = stop("cherokee_lake_park", "pit", 30)

# ---- Atlanta ---------------------------------------------------------------------------
S["cleveland_park"] = stop("cleveland_park_spartanburg", "pit", 30)
# Two passes reported this park. The fall-line pass had only the daylight-saving hours; the
# I-75 pass read the operator's park-rules page, re-checked 2026-11-08: Nov-Feb 07:00-18:00.
S["amerson"] = stop("amerson_river_park", "pit", 30, phone="478-803-0484",
    url="https://amerson.maconbibb.us/park-rules/", status="standing",
    facilities=[{"name": "Park, playground and river trail (Nov-Feb)", "days": "daily", "open": "07:00",
                 "close": "18:00", "url": "https://amerson.maconbibb.us/park-rules/", "status": "standing"}])
S["jf_gregory"] = stop("jf_gregory_park", "pit", 30)

S["lunch_dunwoody"] = lunch("treetop_quest_dunwoody", "Lunch in Dunwoody",
    "around Brook Run Park, Dunwoody, GA",
    [k for k, c in CAND.items() if c.get("kind") == "food" and c.get("near") == "treetop_quest_dunwoody"][:4])
S["unity_park"] = stop("unity_park_greenville", "pit", 35)
S["stone_mountain"] = stop("stone_mountain_park", "excursion", 135, keep=[3, 0, 1],
    name="Stone Mountain Park: Walk-Up Trail to the summit", phone="770-465-3235",
    ask="is the weekday Historic ticket (Skyride) sold on the 25th?")
S["lunch_stone_mountain"] = lunch("stone_mountain_park", "Lunch in Stone Mountain Village",
    "Main St, Stone Mountain, GA - about a mile from the park's West Gate",
    [k for k, c in CAND.items() if c.get("kind") == "food" and c.get("near") == "stone_mountain_park"
     and "crossroads" not in k and "big_rock" not in k][:4])
S["crowders"] = stop("crowders_mountain_sp", "pit", 40, phone="980-460-8042", cost_usd=0,
    cost_note="day use is free (NC State Parks)")
S["tugaloo"] = stop("tugaloo_sp", "excursion", 105, phone="706-356-4362",
    ask="mini-golf hours")
S["lunch_lavonia"] = lunch("tugaloo_sp", "Lunch in Lavonia",
    "Lavonia, GA - I-85 exit 173, on the way back from the park",
    [k for k, c in CAND.items() if c.get("kind") == "food" and c.get("near") == "tugaloo_sp"
     and "smokehouse" not in k][:4])

CO = "coastal - I-95 then US-84"
FL = "fall line - I-77, I-20, Fall Line Fwy, I-75"
AT = "Atlanta - I-85 the whole way, then I-75"
O = {
  "coastal-fort":    {"label": "Coastal: an earthwork fort and its trails", "corridor": CO, "depart_h": 5.25,
                      "stops": ["sob", "santee_mound", "lunch_richmond_hill", "fort_mcallister", "jesup_trains"],
                      "dwell_min": {"santee_mound": 25, "lunch_richmond_hill": 40, "fort_mcallister": 105}},
  "coastal-animals": {"label": "Coastal: a two-mile wildlife walk in Savannah", "corridor": CO, "depart_h": 5.25,
                      "stops": ["sob", "walterboro", "oatland", "lunch_savannah_east", "laura_walker"],
                      "dwell_min": {"walterboro": 25, "oatland": 100, "lunch_savannah_east": 40}},
  "coastal-ninja":   {"label": "Coastal: indoor ninja park in Charleston, rain or shine", "corridor": CO, "depart_h": 5.15,
                      "stops": ["sob", "amonkey", "lunch_tanger", "jesup_trains"]},
  "fallline-woods":  {"label": "Fall line: free woods trails in Aiken", "corridor": FL, "depart_h": 5.0,
                      "stops": ["fortmill_welcome", "hitchcock", "lunch_aiken", "ocmulgee"],
                      "dwell_min": {"hitchcock": 100, "lunch_aiken": 40, "ocmulgee": 40}},
  "fallline-zoo":    {"label": "Fall line: zoo with a ropes course", "corridor": FL, "depart_h": 5.5,
                      "stops": ["fortmill_welcome", "riverbanks", "lunch_columbia", "phinizy", "amerson"],
                      "dwell_min": {"riverbanks": 150, "phinizy": 25, "amerson": 25}},
  "fallline-mounds": {"label": "Fall line: climb the mounds, lunch at Nu-Way", "corridor": FL, "depart_h": 5.0,
                      "stops": ["fortmill_welcome", "phinizy", "lunch_macon", "ocmulgee_big"],
                      "dwell_min": {"phinizy": 35, "lunch_macon": 40, "ocmulgee_big": 90}},
  "atlanta-treetops":{"label": "Atlanta: treetop ropes course in Dunwoody", "corridor": AT, "depart_h": 5.0,
                      "stops": ["cleveland_park", "lunch_dunwoody", "treetop", "lane_orchards"],
                      "dwell_min": {"cleveland_park": 25, "lunch_dunwoody": 40, "lane_orchards": 30}},
  "atlanta-summit":  {"label": "Atlanta: hike up Stone Mountain", "corridor": AT, "depart_h": 5.0,
                      "stops": ["cleveland_park", "lunch_stone_mountain", "stone_mountain", "rozar"],
                      "dwell_min": {"cleveland_park": 25, "lunch_stone_mountain": 40, "stone_mountain": 120, "rozar": 25}},
  "atlanta-lake":    {"label": "Atlanta: a state park on Lake Hartwell", "corridor": AT, "depart_h": 5.3,
                      "stops": ["crowders", "tugaloo", "lunch_lavonia", "high_falls", "peanut"],
                      "dwell_min": {"crowders": 30, "tugaloo": 90, "lunch_lavonia": 40, "high_falls": 30}},
}


# Researched and left out, with the reason. Rendered on the page so the breadth of the search
# is visible and nobody re-researches a dead end.
CONSIDERED = [
  ("Flying Rabbit Adventures, Greenville SC", "https://flyingrabbitadventures.com",
   "closed Monday to Thursday except for groups of 15 or more; the Dunwoody ropes park is Treetop Quest"),
  ("Okefenokee Swamp Park, Waycross", "https://okeswamp.org/general-admission/",
   "observation tower closed for maintenance, $98, and reached at 7 hours in, too late for a lunch stop"),
  ("U.S. National Whitewater Center, Charlotte", "https://whitewater.org/buy/",
   "reached about 2 hours in, before most activities open at 10:00; $329 with all-access passes, and the 6-year-old may be under the 45 lb minimum"),
  ("Urban Air trampoline parks, Columbia / Augusta / Macon", "https://www.urbanair.com/",
   "open only from 15:00 or 16:00 on Wednesdays"),
  ("Fort Pulaski National Monument, Savannah", "https://www.nps.gov/fopu/learn/news/23nr21.htm",
   "closed early on the Wednesday before Thanksgiving in 2023; 2026 hours not published"),
  ("Tybee Island Light Station", "https://www.tybeelighthouse.org/visitor-general-info",
   "178 steps the boys would love, but a long spur east of Savannah"),
  ("Hunting Island State Park lighthouse", "https://southcarolinaparks.com/hunting-island/lighthouse",
   "a 45-mile spur from I-95"),
  ("Congaree National Park", "https://www.nps.gov/cong/",
   "a dead-end spur that measured +2h45 from either corridor"),
  ("Southern Forest World, Waycross", "https://southernforestworld.org",
   "climb-inside model pine and fire tower, but it closes at 14:00, before the afternoon reaches it"),
  ("Georgia Museum of Agriculture, Tifton", "https://gma.abac.edu/visitor-information-hours.html",
   "historic village closes at 15:00 on weekdays"),
  ("Grand Bay WMA boardwalk and tower, Valdosta", "https://georgiawildlife.com/grand-bay-wma",
   "closed until further notice (posted 8 Oct 2026)"),
  ("Zoo Atlanta", "https://zooatlanta.org/visit/",
   "inside I-285 off the corridor, and mostly walking rather than climbing"),
  ("Treetop Quest Gwinnett, Buford", "https://www.treetopquest.com/",
   "open the same hours on the 25th; kept as the backup if Dunwoody is full"),
  ("Sesquicentennial and Saluda Shoals parks, Columbia", "https://southcarolinaparks.com/sesqui",
   "good playgrounds and lake loops, but Columbia comes about 3.5 hours in, too early for lunch; Sesqui is used as a short stop instead"),
  ("The Peachoid, Gaffney", "https://www.roadsideamerica.com/tip/1168",
   "the lot at its base is chained off; it can be seen from I-85 but there is nowhere confirmed to stop"),
  ("Charles Towne Landing, Charleston", "https://southcarolinaparks.com/charles-towne-landing",
   "part of the Animal Forest is closed on weekdays for construction and the replica ship is away"),
]
spec["considered"] = [{"name": n, "url": u, "reason": r} for n, u, r in CONSIDERED]
spec["stops"] = S
spec["options"] = O
json.dump(spec, open(os.path.join(D, "spec.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
open(os.path.join(D, "spec.json"), "a").write("\n")
print(f"{len(S)} stops, {len(O)} options")
