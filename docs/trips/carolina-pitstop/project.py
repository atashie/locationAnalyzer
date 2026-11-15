"""Project measured Gainesville->Columbia geometry into the existing page's map frame.

The original Carolina Pitstop map is a linear lat/lon fit; recovered from two labelled
points (Gainesville, Chapel Hill) and checked against a third (Charlotte) below.
"""
import json, sys
GNV = (29.6516, -82.3248, 394.2, 1089.1)
CHP = (35.9132, -79.0558, 813.4, 135.1)
AX = (CHP[2] - GNV[2]) / (CHP[1] - GNV[1]); BX = GNV[2] - AX * GNV[1]
AY = (CHP[3] - GNV[3]) / (CHP[0] - GNV[0]); BY = GNV[3] - AY * GNV[0]
def proj(lat, lon): return (AX * lon + BX, AY * lat + BY)
# assertion: Charlotte label sits at (584.2, 239.6) in the original page
cx, cy = proj(35.2271, -80.8431)
assert abs(cx - 584.2) < 1.0 and abs(cy - 239.6) < 1.0, (cx, cy)
# and Jacksonville (480.0, 985.4)
jx, jy = proj(30.3322, -81.6557)
assert abs(jx - 480.0) < 3 and abs(jy - 985.4) < 3, (jx, jy)
m = json.load(open(sys.argv[1]))
out = {"routes": {}, "pts": {}}
for k, o in m["options"].items():
    xy = [proj(p[0], p[1]) for p in o["geometry"]]
    out["routes"][k] = "M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in xy)
for k, s in m["stops"].items():
    out["pts"][k] = [round(v, 1) for v in proj(s["lat"], s["lon"])]
out["hotel"] = [round(v, 1) for v in proj(34.0077, -81.0498)]
out["segra"] = [round(v, 1) for v in proj(34.0183, -81.0312)]
out["gnv"] = [GNV[2], GNV[3]]
# bounds check: every point of every route inside the cropped frame used by the tab
VB = (300, 360, 520, 780)  # x, y, w, h
for k, o in m["options"].items():
    for p in o["geometry"]:
        x, y = proj(p[0], p[1])
        assert VB[0] <= x <= VB[0] + VB[2] and VB[1] <= y <= VB[1] + VB[3], (k, x, y)
out["viewBox"] = " ".join(map(str, VB))
json.dump(out, open(sys.argv[2], "w"))
print({k: len(v) for k, v in out["routes"].items()}, out["pts"], out["hotel"])
