"""Walking routes (Valhalla pedestrian, one engine) from each Columbia venue to Segra Park and the hotel."""
import json, time, urllib.parse, urllib.request
UA = "route-planner-script/1.0"
HOTEL = (34.0077, -81.0498); SEGRA = (34.0183, -81.0312)
V = [("gather","Gather COLA","2191 Pickens Street, Columbia, SC"),
 ("crust","Coastal Crust","2158 Pickens Street, Columbia, SC"),
 ("warmouth","The War Mouth","1209 Franklin Street, Columbia, SC"),
 ("transmission","Transmission Arcade","1712 Main Street, Columbia, SC"),
 ("grand","The Grand on Main","1621 Main Street, Columbia, SC"),
 ("villa","Villa Tronco","1213 Blanding Street, Columbia, SC"),
 ("sweetcream","Sweet Cream Co","1627 Main Street, Columbia, SC"),
 ("kaminskys","Kaminsky's","930 Gervais Street, Columbia, SC"),
 ("pearlz","Pearlz","936 Gervais Street, Columbia, SC"),
 ("finlay","Finlay Park","Finlay Park, Columbia, SC"),
 ("riverfront","Riverfront Park","Riverfront Park, Columbia, SC"),
 ("cma","Columbia Museum of Art","1515 Main Street, Columbia, SC"),
 ("statehouse","SC State House","1100 Gervais Street, Columbia, SC"),
 ("edventure","EdVenture","211 Gervais Street, Columbia, SC"),
 ("ellington","Page Ellington Park","Page Ellington Park, Columbia, SC")]
def get(url, data=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=30))
def walk(a, b):
    body = json.dumps({"locations":[{"lat":a[0],"lon":a[1]},{"lat":b[0],"lon":b[1]}],"costing":"pedestrian","units":"miles"}).encode()
    s = get("https://valhalla1.openstreetmap.de/route", body)["trip"]["summary"]
    time.sleep(1); return round(s["length"],2), round(s["time"]/60)
out = {}
for k, name, q in V:
    g = get("https://nominatim.openstreetmap.org/search?format=json&limit=1&q=" + urllib.parse.quote(q)); time.sleep(1.1)
    if not g: out[k] = {"name": name, "geocode": None}; print(k, "NO GEOCODE"); continue
    p = (float(g[0]["lat"]), float(g[0]["lon"]))
    out[k] = {"name": name, "lat": p[0], "lon": p[1], "matched": g[0]["display_name"][:90],
              "to_segra": walk(p, SEGRA), "to_hotel": walk(p, HOTEL)}
    print(k, out[k]["to_segra"], out[k]["to_hotel"], out[k]["matched"][:60])
out["hotel_segra"] = walk(HOTEL, SEGRA); print("hotel->segra", out["hotel_segra"])
json.dump(out, open("walks.json","w"), indent=1)
