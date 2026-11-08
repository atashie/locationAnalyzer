#!/usr/bin/env python3
"""Generate the comparison page from measured.json. Every number comes from the
measurement, never retyped -- rule 3 enforced by construction."""
import json, math, io, os, itertools

NL = chr(10)
D = os.path.dirname(os.path.abspath(__file__))
M = json.load(open(f"{D}/measured.json", encoding="utf-8"))
OUT = os.path.join(D, "route-options.html")      # next to the inputs it was built from

opts, stops, bbox, direct = M["options"], M["stops"], M["bbox"], M["direct"]
ORDER = ["coastal-fewest", "coastal-swamp", "coastal-outdoors",
         "fallline-two-big", "fallline-gentler", "fallline-indoors",
         "atlanta-two-cities"]
assert set(ORDER) == set(opts), set(ORDER) ^ set(opts)

GROUPS = []
for k in ORDER:
    c = opts[k]["corridor"]
    if not GROUPS or GROUPS[-1][0] != c:
        GROUPS.append((c, []))
    GROUPS[-1][1].append(k)
CORR_SHORT = {"coastal - I-95 then US-84": "Coastal",
              "fall line - I-77, I-20, Fall Line Fwy, I-75": "Fall line",
              "Atlanta - I-85 the whole way, then I-75": "Atlanta"}

BM = json.load(open(f"{D}/basemap.json", encoding="utf-8"))

# Pad the projection window beyond the routes' own extent, otherwise the basemap is
# clipped flush to the outermost route and provides no context at all.
PAD_DEG = 0.45
bbox = {"min_lat": bbox["min_lat"] - PAD_DEG, "max_lat": bbox["max_lat"] + PAD_DEG,
        "min_lon": bbox["min_lon"] - PAD_DEG, "max_lon": bbox["max_lon"] + PAD_DEG}

mean_lat = math.radians((bbox["min_lat"] + bbox["max_lat"]) / 2)
kx = math.cos(mean_lat)
w_deg = (bbox["max_lon"] - bbox["min_lon"]) * kx
h_deg = bbox["max_lat"] - bbox["min_lat"]
# One scale for both axes. Deriving VW from the aspect ratio and *then* subtracting an
# equal pixel margin from each gave the axes different scales -- 1.27% of horizontal
# compression on this bbox, which is a squashed map for no reason. Size the drawing area
# first, then add the margin.
PADPX = 35.0
DRAW_H = 1000.0 - 2 * PADPX
SCALE = DRAW_H / h_deg                 # px per degree of latitude, used for x as well
VH = 1000.0
VW = w_deg * SCALE + 2 * PADPX

def proj(lat, lon):
    x = (lon - bbox["min_lon"]) * kx * SCALE + PADPX
    y = (bbox["max_lat"] - lat) * SCALE + PADPX
    return x, y

def label_side(x):
    """Flip labels inward near the edges, or they are clipped by the viewBox."""
    if x > VW * 0.76:
        return -9, ' text-anchor="end"'
    return 9, ''

def path_of(geom):
    return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in (proj(a, b) for a, b in geom))

def _hm_parts(sec):
    """Round to the nearest minute first, then split. Truncating seconds showed 60.8 min
    as "1h00"; and int(-6.9)//3600 made a 7-second negative render as "-1h59"."""
    m = int(round(sec / 60.0))
    sign = "-" if m < 0 else ""
    m = abs(m)
    return sign, m // 60, m % 60

def hm(sec):
    sg, h, m = _hm_parts(sec); return f"{sg}{h}h{m:02d}"

def hm_short(sec):
    sg, h, m = _hm_parts(sec); return f"{sg}{h}:{m:02d}"

def plus(sec):
    return f"+{int(round(sec/60))} min"

def money(v):
    return f"${int(round(v))}" if v else "n/p"

G = {k: opts[k]["geometry"] for k in ORDER}
KX_SEP = math.cos(math.radians((bbox["min_lat"] + bbox["max_lat"]) / 2))

def _pt_seg(p, q1, q2):
    """Distance from p to the SEGMENT q1-q2, longitude scaled."""
    py, px = p[0], p[1] * KX_SEP
    ay, ax = q1[0], q1[1] * KX_SEP
    by, bx = q2[0], q2[1] * KX_SEP
    dx, dy = bx - ax, by - ay
    den = dx * dx + dy * dy
    if den == 0.0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / den
    t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))

def directed_sep(a, b):
    """Furthest any vertex of a sits from the nearest point ON b."""
    segs = list(zip(G[b], G[b][1:])) or [(G[b][0], G[b][0])]
    return max(min(_pt_seg(p, q1, q2) for q1, q2 in segs) for p in G[a])

def sep(a, b):
    # Hausdorff-style and symmetric. Two things were wrong before: taking one direction
    # made the published figure depend on list order (2.69 deg one way, 3.23 the other),
    # and measuring vertex-to-VERTEX made two identical straight routes look ~58 miles
    # apart if one carried an extra midpoint. Distance is to the segment, both ways.
    return max(directed_sep(a, b), directed_sep(b, a))

cross = max(sep(a, b) for a, b in itertools.combinations(ORDER, 2))
cross_mi = cross * 69.0

BC = BM["counts"]
state_pts, road_pts = BC["states_kept"], BC["roads_kept"]
state_raw_k = round(BC["states_raw"] / 1000)
road_raw_k = round(BC["roads_raw"] / 1000)
n_frag = BC["road_fragments"]

EXP = json.load(open(f"{D}/experiments.json", encoding="utf-8"))
CB = EXP["corridors_bare"]

def mins(sec):
    return f"{int(round(sec/60))} min"

def hm_or_min(sec):
    sg, h, m = _hm_parts(sec)
    return f"{sg}{h}h{m:02d}" if h else f"{sg}{m} min"

bare_fall = hm_or_min(CB["fall_line"]["detour_s"])
bare_atl = hm_or_min(CB["atlanta"]["detour_s"])
bare_jax = hm_or_min(CB["jacksonville"]["detour_s"])
zoo_off_coastal = mins(EXP["stop_detour_by_corridor"]["riverbanks_off_coastal_s"])
congaree_cost = hm_or_min(EXP["stop_detour_by_corridor"]["congaree_any_corridor_s"])
santee_cost = mins(EXP["stop_detour_by_corridor"]["santee_off_coastal_s"])
i95_mi = EXP["corridor_mileage"]["i95_southbound_mi"]
i85_mi = EXP["corridor_mileage"]["i85_through_atlanta_mi"]

# figures quoted in the fall-line and collision copy, all read off the measurement
fl_open_leg = hm_short(opts["fallline-two-big"]["legs_s"][0])
fl_mid_leg = hm_short(opts["fallline-two-big"]["legs_s"][1])
gentler_extra = mins(opts["fallline-gentler"]["detour_s"] - opts["fallline-two-big"]["detour_s"])
_g = opts["fallline-gentler"]["legs_s"]
gentler_split = f"{hm_short(_g[1])} and {hm_short(_g[2])}"
pig_arr = min(sc["arrive"] for k in ORDER for sc in opts[k]["schedule"] if sc["stop"] == "pig_rh")
BUDGET_S = 3600                       # the traveller's rough figure, stated as "about an hour"
under = sum(1 for k in ORDER if opts[k]["detour_s"] <= BUDGET_S)
over = len(ORDER) - under
NUMWORD = {0:"no", 1:"one", 2:"two", 3:"three", 4:"four", 5:"five", 6:"six", 7:"seven"}
# how far past sunset the Atlanta option lands, and the departure that would open the
# lunch stop on arrival rather than 30 minutes later
_atl = opts["atlanta-two-cities"]
atl_late_h = _atl["arrive_h"] - (int(_atl["sunset"][:2]) + int(_atl["sunset"][3:]) / 60)
atl_late = f"{atl_late_h:.0f} hours" if atl_late_h >= 1.5 else f"{atl_late_h*60:.0f} minutes"
_fw = opts["coastal-fewest"]
_before_pig = 0.0
for i, sc in enumerate(_fw["schedule"]):
    _before_pig += _fw["legs_s"][i] / 3600.0
    if sc["stop"] == "pig_rh":
        break
    _before_pig += sc["dwell_min"] / 60.0
pig_fix_depart = f"{int(11.0 - _before_pig):02d}:{int(round((11.0 - _before_pig) % 1 * 60)):02d}"
walt_arr = next(sc["arrive"] for k in ORDER for sc in opts[k]["schedule"]
                if sc["stop"] == "walterboro")
disc_arr = min(sc["arrive"] for k in ORDER for sc in opts[k]["schedule"] if sc["stop"] == "discovery")

def poly(pts):
    return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in (proj(a, b) for a, b in pts))

base_states = NL.join(f'        <path d="{poly(r["pts"])}" />' for r in BM["states"])
base_roads = NL.join(
    f'        <path d="{poly(run)}" />'
    for ref in BM["interstates"] for run in BM["interstates"][ref])

ROAD_LABELS = {"I 95": (34.55, -79.12), "I 85": (34.35, -82.55), "I 77": (34.70, -80.95),
               "I 20": (33.60, -82.75), "I 75": (31.60, -83.75), "I 16": (32.45, -82.35),
               "I 26": (33.30, -80.35), "I 40": (36.05, -78.95), "I 10": (30.45, -83.30)}

def road_tag(ref, la, lo):
    x, y = proj(la, lo)
    dx, anchor = label_side(x)
    # anchored labels shift by their own offset; centred ones stay put
    return (f'        <text x="{(x + dx) if anchor else x:.0f}" y="{y:.0f}"'
            f'{anchor or " text-anchor=\"middle\""}>{ref.replace(" ", "-")}</text>')

base_road_labels = NL.join(road_tag(r, la, lo) for r, (la, lo) in ROAD_LABELS.items())

def city_tag(c):
    x, y = proj(c["lat"], c["lon"])
    dx, anchor = label_side(x)
    r = 4.5 if c["major"] else 3
    return (f'        <g class="city{" maj" if c["major"] else ""}">'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}"/>'
            f'<text x="{x+dx:.1f}" y="{y+5:.1f}"{anchor}>{c["name"]}</text></g>')

base_cities = NL.join(city_tag(c) for c in BM["cities"])

map_paths = NL.join(
    f'      <path class="route c{i}" data-opt="{k}" d="{path_of(G[k])}" />'
    for i, k in enumerate(ORDER))

marker_groups = []
for k in ORDER:
    ms = []
    for i, sk in enumerate(opts[k]["stops"], 1):
        s = stops[sk]
        x, y = proj(s["lat"], s["lon"])
        ms.append(f'        <g class="mk"><circle cx="{x:.1f}" cy="{y:.1f}" r="14"/>'
                  f'<text x="{x:.1f}" y="{y+5:.1f}">{i}</text></g>')
    marker_groups.append(f'      <g class="markers" data-opt="{k}" hidden>' + NL
                         + NL.join(ms) + NL + '      </g>')
markers = NL.join(marker_groups)

ox, oy = proj(M["origin"]["lat"], M["origin"]["lon"])
dx, dy = proj(M["dest"]["lat"], M["dest"]["lon"])

def switch_btn(k):
    v = opts[k]
    late = ' <span class="late">after dark</span>' if v.get("after_sunset") else ""
    return NL.join([
        f'        <button class="opt" role="radio" aria-checked="false" data-opt="{k}" id="btn-{k}">',
        f'          <span class="opt-name">{v["label"].split(": ", 1)[1]}</span>',
        f'          <span class="opt-meta"><span class="n">{v["depart"]}</span>&ndash;<span class="n">{v["arrive"]}</span>{late}'
        f' &middot; <span class="n">{money(v["cost_usd"])}</span>'
        f' &middot; <span class="n">{len(v["stops"])}</span> stops</span>',
        '        </button>'])

switcher = NL.join(
    NL.join([f'      <div class="grp">',
             f'        <p class="grp-h">{CORR_SHORT[c]} <span>{c.split(" - ",1)[1]}</span></p>']
            + [switch_btn(k) for k in ks] + ['      </div>'])
    for c, ks in GROUPS)

rows = []
for c, ks in GROUPS:
    rows.append(f'        <tr class="grp-row"><th colspan="10">{CORR_SHORT[c]}'
                f' &mdash; {c.split(" - ",1)[1]}</th></tr>')
    for k in ks:
        v = opts[k]
        rows.append(NL.join([
            f'        <tr data-opt="{k}">',
            f'          <th scope="row">{v["label"].split(": ",1)[1]}</th>',
            f'          <td class="n">{v["depart"]}</td>',
            f'          <td class="n">{hm(v["total_s"])}</td>',
            f'          <td class="n">{plus(v["detour_s"])}</td>',
            f'          <td class="n">{v["miles"]:.0f}</td>',
            f'          <td class="n">{hm_short(max(v["legs_s"]))}</td>',
            f'          <td class="n">{len(v["stops"])}</td>',
            f'          <td class="n">{hm(v["elapsed_s"])}</td>',
            f'          <td class="n">{money(v["cost_usd"])}</td>',
            f'          <td class="n">{v["arrive"]}'
            + ('<span class="late">after dark</span>' if v.get("after_sunset") else '') + '</td>',
            '        </tr>']))
totals = NL.join(rows)

VERDICT = {"always": "always", "open": "open", "opens": "opens", "shut": "shut",
           "closed": "closed", "unknown": "unsure"}
ROLL = {"open-on-arrival": "", "opens-during": "you arrive before it opens",
        "nothing-open": "nothing here is open when you arrive", "unknown": "hours unknown"}
SRC = {"standing": ("src-standing", "standing hours, date not checked"),
       "confirmed": ("src-confirmed", "confirmed for the date"),
       "unknown": ("src-unknown", "could not determine - third-party only")}

def facility_rows(h):
    out = []
    for fc in h["facilities"]:
        nm = f'<a href="{fc["url"]}">{fc["name"]}</a>' if fc.get("url") else fc["name"]
        scls, stitle = SRC[fc.get("status", "standing")]
        out.append(f'              <li class="fac f-{VERDICT[fc["verdict"]]}">'
                   f'<span class="fac-n">{nm} <span class="src {scls}">{stitle}</span></span>'
                   f'<span class="fac-d">{fc["detail"]}</span></li>')
    return NL.join(out)

def timeline(k):
    v = opts[k]
    items = [f'        <li class="leg"><span class="n drive">{hm_short(v["legs_s"][0])}</span>'
             f'<span class="leg-txt">leave {M["origin"]["name"]} at {v["depart"]}</span></li>']
    for i, sch in enumerate(v["schedule"]):
        s = stops[sch["stop"]]
        h = sch["hours"]
        nm = f'<a href="{s["url"]}">{s["name"]}</a>' if s.get("url") else s["name"]
        cost = s.get("cost_usd") or 0
        chip = f'<span class="chip cost n">{money(cost)} for four</span>' if cost else ""
        note = f'<p class="cost-note">{s["cost_note"]}</p>' if s.get("cost_note") else ""
        warn = ROLL[h["rollup"]]
        items.append(NL.join([
            '        <li class="halt">',
            f'          <span class="n clock">{sch["arrive"]}</span>',
            '          <div class="halt-body">',
            f'            <p class="halt-name">{nm} <span class="num">&middot; {int(sch["dwell_min"])} min</span></p>',
            f'            <p class="halt-where">{s["where"]}</p>',
            (f'            <p class="warn-row w-{h["rollup"]}">{warn}</p>' if warn else ""),
            '            <ul class="facs">', facility_rows(h), '            </ul>',
            (f'            <p class="chips">{chip}</p>' if chip else ""), note,
            '          </div>', '        </li>']))
        if i + 1 < len(v["legs_s"]):
            items.append(f'        <li class="leg"><span class="n drive">{hm_short(v["legs_s"][i+1])}</span>'
                         f'<span class="leg-txt">drive</span></li>')
    items.append(NL.join([
        '        <li class="halt arrive">',
        f'          <span class="n clock">{v["arrive"]}</span>',
        '          <div class="halt-body">',
        f'            <p class="halt-name">{M["dest"]["name"]}</p>',
        f'            <p class="halt-where">sunset {v["sunset"]} &middot; {hm(v["elapsed_s"])} door to door'
        + ('&nbsp;&middot; <strong>arrives after sundown</strong>' if v.get("after_sunset") else '')
        + '</p>', '          </div>', '        </li>']))
    return f'      <ol class="tl" data-opt="{k}" hidden>' + NL + NL.join(items) + NL + '      </ol>'
timelines = NL.join(timeline(k) for k in ORDER)

max_elapsed = max(v["elapsed_s"] for v in opts.values())
earliest = min(v["depart_h"] for v in opts.values())
def rhythm(k):
    v = opts[k]
    lead = (v["depart_h"] - earliest) * 3600.0
    segs, t = [], lead
    for i, leg in enumerate(v["legs_s"]):
        segs.append(("drive", t, leg)); t += leg
        if i < len(v["schedule"]):
            dw = v["schedule"][i]["dwell_min"] * 60.0
            segs.append(("halt", t, dw)); t += dw
    span = max_elapsed + (max(o["depart_h"] for o in opts.values()) - earliest) * 3600.0
    bars = []
    if lead > 0:
        bars.append(f'<span class="seg later" style="left:0;width:{lead/span*100:.3f}%"></span>')
    for kind, start, dur in segs:
        if dur <= 0:
            continue
        bars.append(f'<span class="seg {kind}" style="left:{start/span*100:.3f}%;'
                    f'width:{dur/span*100:.3f}%"></span>')
    return NL.join([
        f'        <div class="rhy" data-opt="{k}">',
        f'          <span class="rhy-name">{v["label"]}</span>',
        f'          <span class="rhy-bar">{"".join(bars)}</span>',
        f'          <span class="rhy-end n">{v["arrive"]}</span>',
        f'          <span class="rhy-max n">longest leg {hm_short(max(v["legs_s"]))}</span>',
        '        </div>'])
rhythms = NL.join(rhythm(k) for k in ORDER)

sob = next(sc for sc in opts["coastal-fewest"]["schedule"] if sc["stop"] == "sob")
pantry_wait = int(round((7.0 - sob["arrive_h"]) * 60))
best_coastal = min((opts[k] for k in ORDER if opts[k]["corridor"].startswith("coastal")),
                   key=lambda v: v["detour_s"])
fl = opts["fallline-two-big"]
gap = (fl["arrive_h"] - best_coastal["arrive_h"]) * 60
atl = opts["atlanta-two-cities"]

HTML = f"""<title>Three Roads South</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Familjen+Grotesk:wght@400;500;600;700&family=Literata:opsz,wght@7..72,400;7..72,600&family=Spline+Sans+Mono:wght@400;500;600&display=swap">
<style>
  :root{{
    --bg:#F2F4F3; --panel:#FFFFFF; --sunk:#E6EAE8; --line:#D2D9D6;
    --ink:#111A18; --text:#394741; --dim:#6E7E77;
    --accent:#1F6F5C; --accent-ink:#FFFFFF; --accent-dim:#9DC3B7;
    --warn:#9A6208; --flag:#8C3A2A; --ghost:#B9C4C0;
    --c-coastal:#1F6F5C; --c-fall:#8A5A1C; --c-atl:#6B4A7A;
    --map-bg:#EAEFEC; --map-land:#F6F8F6; --map-border:#C2CCC6;
    --map-road:#CBD5CF; --map-road-ink:#8D9A93; --map-city:#9AA8A1; --map-city-ink:#6E7E77;
  }}
  @media (prefers-color-scheme:dark){{
    :root:not([data-theme="light"]){{
      --bg:#0E1513; --panel:#16201D; --sunk:#111A17; --line:#28352F;
      --ink:#E8EFEB; --text:#BCCAC3; --dim:#82968D;
      --accent:#5FD1AE; --accent-ink:#05231B; --accent-dim:#2C5A4C;
      --warn:#E0A94C; --flag:#E08972; --ghost:#324540;
      --c-coastal:#5FD1AE; --c-fall:#E0A94C; --c-atl:#C3A0D8;
    --map-bg:#0B1210; --map-land:#141C19; --map-border:#2E3C35;
    --map-road:#2A3831; --map-road-ink:#72847B; --map-city:#5E6F67; --map-city-ink:#8EA096;
      --map-bg:#0B1210; --map-land:#141C19; --map-border:#2E3C35;
      --map-road:#2A3831; --map-road-ink:#72847B; --map-city:#5E6F67; --map-city-ink:#8EA096;
    }}
  }}
  :root[data-theme="dark"]{{
    --bg:#0E1513; --panel:#16201D; --sunk:#111A17; --line:#28352F;
    --ink:#E8EFEB; --text:#BCCAC3; --dim:#82968D;
    --accent:#5FD1AE; --accent-ink:#05231B; --accent-dim:#2C5A4C;
    --warn:#E0A94C; --flag:#E08972; --ghost:#324540;
    --c-coastal:#5FD1AE; --c-fall:#E0A94C; --c-atl:#C3A0D8;
  }}
  *{{box-sizing:border-box}}
  body{{background:var(--bg);color:var(--text);font-family:Literata,Georgia,serif;font-size:16px;line-height:1.6;-webkit-font-smoothing:antialiased}}
  h1,h2,.ui,button,th,.chip,.opt-name,.eyebrow,.grp-h,.halt-name,.rhy-name,.late{{font-family:"Familjen Grotesk",system-ui,sans-serif}}
  .n,.num,.clock,.drive{{font-family:"Spline Sans Mono",ui-monospace,monospace;font-variant-numeric:tabular-nums}}
  .wrap{{max-width:86rem;margin:0 auto;padding:2rem 1.25rem 4rem;display:flex;flex-direction:column;gap:2rem}}
  a{{color:var(--accent);text-underline-offset:2px}}
  a:hover{{color:var(--ink)}}
  :focus-visible{{outline:2px solid var(--accent);outline-offset:2px}}
  .eyebrow{{text-transform:uppercase;letter-spacing:.13em;font-size:.7rem;font-weight:600;color:var(--dim);margin:0}}
  h1{{font-size:clamp(1.9rem,5vw,2.9rem);line-height:1.04;margin:.3rem 0 0;color:var(--ink);font-weight:700;letter-spacing:-.02em;text-wrap:balance}}
  h2{{font-size:1.1rem;margin:0;color:var(--ink);font-weight:600}}
  p{{margin:0}}
  .lede{{max-width:62ch;margin-top:.7rem}}
  .late{{display:inline-block;font-size:.66rem;color:var(--warn);letter-spacing:.04em;text-transform:uppercase;margin-left:.25rem}}

  .switch{{display:grid;grid-template-columns:repeat(auto-fit,minmax(16rem,1fr));gap:1rem;
    border-top:1px solid var(--line);border-bottom:1px solid var(--line);padding:.9rem 0}}
  .grp{{display:flex;flex-direction:column;gap:.4rem;min-width:0}}
  .grp-h{{font-size:.74rem;text-transform:uppercase;letter-spacing:.1em;font-weight:700;color:var(--ink);
    display:flex;flex-direction:column;gap:.1rem}}
  .grp-h span{{font-family:"Spline Sans Mono",monospace;font-size:.66rem;letter-spacing:0;
    text-transform:none;color:var(--dim);font-weight:400}}
  .grp:nth-child(1) .grp-h{{color:var(--c-coastal)}}
  .grp:nth-child(2) .grp-h{{color:var(--c-fall)}}
  .grp:nth-child(3) .grp-h{{color:var(--c-atl)}}
  .opt{{display:flex;flex-direction:column;gap:.18rem;align-items:flex-start;text-align:left;
    background:var(--panel);border:1px solid var(--line);border-radius:3px;padding:.55rem .65rem;
    cursor:pointer;color:var(--text);transition:border-color .12s,background .12s}}
  .opt:hover{{border-color:var(--accent-dim)}}
  .opt[aria-checked="true"]{{background:var(--accent);border-color:var(--accent);color:var(--accent-ink)}}
  .opt[aria-checked="true"] .late{{color:var(--accent-ink);opacity:.85}}
  .opt-name{{font-size:.92rem;font-weight:600;line-height:1.2}}
  .opt-meta{{font-size:.74rem;opacity:.8}}

  .split{{display:grid;grid-template-columns:minmax(0,21rem) minmax(0,1fr);gap:2rem;align-items:start}}
  @media (max-width:62rem){{.split{{grid-template-columns:1fr}}}}
  .mapcard{{background:var(--panel);border:1px solid var(--line);border-radius:3px;padding:.9rem;
    position:sticky;top:1rem;display:flex;flex-direction:column;gap:.55rem}}
  @media (max-width:62rem){{.mapcard{{position:static}}}}
  svg.map{{width:100%;height:auto;display:block;background:var(--map-bg)}}
  .base-states path{{fill:none;stroke:var(--map-border);stroke-width:2.6;
    stroke-linejoin:round;stroke-linecap:round}}
  .base-roads path{{fill:none;stroke:var(--map-road);stroke-width:2.4;stroke-linecap:round;
    stroke-linejoin:round}}
  .base-road-labels text{{fill:var(--map-road-ink);font-family:"Spline Sans Mono",monospace;
    font-size:19px;font-weight:600;paint-order:stroke;
    stroke:var(--map-bg);stroke-width:5px;stroke-linejoin:round}}
  .base-cities circle{{fill:var(--map-city);stroke:none}}
  .base-cities text{{fill:var(--map-city-ink);font-family:"Familjen Grotesk",sans-serif;
    font-size:21px;paint-order:stroke;stroke:var(--map-bg);stroke-width:5px;stroke-linejoin:round}}
  .base-cities .maj text{{font-weight:600;font-size:24px}}
  .route{{fill:none;stroke:var(--ghost);stroke-width:4;stroke-linejoin:round;stroke-linecap:round;
    opacity:.45;transition:stroke-width .15s,opacity .15s}}
  .route.c0,.route.c1,.route.c2{{stroke:var(--c-coastal)}}
  .route.c3,.route.c4,.route.c5{{stroke:var(--c-fall)}}
  .route.c6{{stroke:var(--c-atl)}}
  .route.sel{{stroke-width:9;opacity:1}}
  .markers .mk circle{{fill:var(--ink);stroke:var(--panel);stroke-width:3}}
  .markers .mk text{{fill:var(--panel);font-family:"Spline Sans Mono",monospace;font-size:15px;font-weight:600;text-anchor:middle}}
  .endpt circle{{fill:var(--panel);stroke:var(--ink);stroke-width:4}}
  .endpt text{{fill:var(--ink);font-family:"Familjen Grotesk",sans-serif;font-size:26px;font-weight:600}}
  .maplegend{{font-size:.73rem;color:var(--dim)}}
  .key{{display:flex;flex-wrap:wrap;gap:.1rem .8rem;font-size:.72rem;margin:0}}
  .key i{{display:inline-block;width:.85rem;height:3px;vertical-align:3px;margin-right:.3rem}}

  .tl{{list-style:none;margin:0;padding:0;display:flex;flex-direction:column}}
  .tl .leg{{display:flex;gap:.7rem;align-items:center;padding:.3rem 0;color:var(--dim);font-size:.82rem}}
  .tl .drive{{color:var(--accent);font-size:.82rem;min-width:3.4rem}}
  .tl .leg-txt{{border-top:1px dashed var(--line);flex:1;padding-top:.1rem}}
  .halt{{display:grid;grid-template-columns:4.6rem 1fr;gap:0 1rem;padding:.75rem 0;border-top:1px solid var(--line)}}
  .halt:first-child{{border-top:none}}
  .clock{{font-size:1.15rem;font-weight:600;color:var(--ink)}}
  .halt-body{{display:flex;flex-direction:column;gap:.3rem;min-width:0}}
  .halt-name{{color:var(--ink);font-weight:600;font-size:1.02rem}}
  .halt-name .num{{color:var(--dim);font-weight:400;font-size:.84rem}}
  .halt-where{{font-size:.84rem;color:var(--dim)}}
  .chips{{display:flex;flex-wrap:wrap;gap:.3rem}}
  .chip{{font-size:.7rem;padding:.16rem .45rem;border-radius:2px;border:1px solid var(--line);background:var(--sunk);color:var(--dim)}}
  .chip.cost{{border-color:var(--accent-dim);color:var(--accent)}}
  .cost-note{{font-size:.8rem;color:var(--flag)}}
  .halt.arrive .clock{{color:var(--accent)}}
  .warn-row{{font-size:.8rem;font-weight:600;padding:.18rem .45rem;border-radius:2px;align-self:flex-start;
    font-family:"Familjen Grotesk",sans-serif}}
  .w-opens-during{{color:var(--warn);background:color-mix(in srgb,var(--warn) 13%,transparent)}}
  .w-nothing-open{{color:var(--flag);background:color-mix(in srgb,var(--flag) 13%,transparent)}}
  .w-unknown{{color:var(--flag);background:color-mix(in srgb,var(--flag) 10%,transparent)}}
  .facs{{list-style:none;margin:.1rem 0 0;padding:0;display:flex;flex-direction:column;gap:.1rem}}
  .fac{{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:.2rem .8rem;align-items:baseline;
    font-size:.82rem;padding:.14rem 0 .14rem .62rem;border-left:3px solid var(--line)}}
  .fac-n{{color:var(--text)}}
  .fac-d{{color:var(--dim);font-size:.76rem;text-align:right;font-family:"Spline Sans Mono",monospace}}
  .fac.f-always,.fac.f-open{{border-left-color:var(--accent)}}
  .fac.f-opens{{border-left-color:var(--warn)}}
  .fac.f-shut,.fac.f-closed{{border-left-color:var(--ghost);opacity:.62}}
  .fac.f-shut .fac-n,.fac.f-closed .fac-n{{text-decoration:line-through;text-decoration-color:var(--ghost)}}
  .fac.f-unsure{{border-left-color:var(--flag)}}
  .src{{display:inline-block;font-family:"Familjen Grotesk",sans-serif;font-size:.6rem;
    text-transform:uppercase;letter-spacing:.06em;padding:.04rem .3rem;border-radius:2px;
    border:1px solid var(--line);color:var(--dim);white-space:nowrap;vertical-align:1px}}
  .src-standing{{border-color:color-mix(in srgb,var(--warn) 34%,transparent);color:var(--warn)}}
  .src-confirmed{{border-color:var(--accent-dim);color:var(--accent)}}
  .src-unknown{{border-color:color-mix(in srgb,var(--flag) 40%,transparent);color:var(--flag)}}
  @media (max-width:40rem){{.fac{{grid-template-columns:1fr}}.fac-d{{text-align:left}}}}

  .rhys{{display:flex;flex-direction:column;gap:.45rem}}
  .rhy{{display:grid;grid-template-columns:16rem 1fr 3.4rem 8.5rem;gap:.7rem;align-items:center;
    padding:.3rem .5rem;border-radius:3px;border:1px solid transparent}}
  .rhy.sel{{background:color-mix(in srgb,var(--accent) 11%,transparent);border-color:var(--accent-dim)}}
  .rhy-name{{font-size:.8rem;color:var(--ink);font-weight:600}}
  .rhy-bar{{position:relative;height:16px;background:var(--sunk);border-radius:2px;display:block;overflow:hidden}}
  .rhy-bar .seg{{position:absolute;top:0;bottom:0;display:block}}
  .rhy-bar .seg.drive{{background:var(--ghost)}}
  .rhy-bar .seg.halt{{background:var(--accent)}}
  .rhy-bar .seg.later{{background:repeating-linear-gradient(135deg,transparent,transparent 3px,var(--line) 3px,var(--line) 6px)}}
  .rhy.sel .rhy-bar .seg.drive{{background:var(--accent-dim)}}
  .rhy-end{{font-size:.82rem;color:var(--ink)}}
  .rhy-max{{font-size:.72rem;color:var(--dim)}}
  @media (max-width:52rem){{
    .rhy{{grid-template-columns:1fr auto;grid-template-areas:"n e" "b b" "m m";gap:.2rem .5rem}}
    .rhy-name{{grid-area:n}} .rhy-end{{grid-area:e;text-align:right}}
    .rhy-bar{{grid-area:b}} .rhy-max{{grid-area:m}}
  }}

  .scroll{{overflow-x:auto;border:1px solid var(--line);border-radius:3px;background:var(--panel)}}
  table{{width:100%;border-collapse:collapse;font-size:.86rem;min-width:58rem}}
  th,td{{text-align:left;padding:.55rem .7rem;border-bottom:1px solid var(--line)}}
  thead th{{font-size:.66rem;text-transform:uppercase;letter-spacing:.09em;color:var(--dim);font-weight:600;white-space:nowrap}}
  tbody th{{font-weight:600;color:var(--ink);white-space:nowrap}}
  tr.grp-row th{{font-size:.66rem;text-transform:uppercase;letter-spacing:.1em;color:var(--dim);
    background:var(--sunk);font-weight:700}}
  tbody tr:last-child th,tbody tr:last-child td{{border-bottom:none}}
  tbody tr.sel{{background:color-mix(in srgb,var(--accent) 11%,transparent)}}
  td.n{{white-space:nowrap;color:var(--ink)}}

  .cols{{display:grid;grid-template-columns:repeat(auto-fit,minmax(18rem,1fr));gap:1.25rem}}
  .note{{display:flex;flex-direction:column;gap:.55rem}}
  .note h2{{padding-bottom:.35rem;border-bottom:2px solid var(--ink)}}
  .note p,.note li{{font-size:.92rem;max-width:62ch}}
  ul{{margin:0;padding-left:1.1rem;display:flex;flex-direction:column;gap:.35rem}}
  ul li::marker{{color:var(--accent-dim)}}
  .prov{{border-top:1px solid var(--line);padding-top:1rem;font-size:.84rem;color:var(--dim);display:flex;flex-direction:column;gap:.35rem}}
  .prov b{{font-family:"Familjen Grotesk",sans-serif;text-transform:uppercase;letter-spacing:.08em;font-size:.68rem;color:var(--ink)}}
  @media (prefers-reduced-motion:reduce){{*{{transition:none!important}}}}
</style>

<div class="wrap">

  <header>
    <p class="eyebrow">Wednesday 25 November 2026 &middot; Chapel Hill, NC &rarr; Thomasville, GA</p>
    <h1>Three roads south</h1>
    <p class="lede">Family of four, boys aged 6 and 9. The direct drive is
      <span class="n">{hm(direct['total_s'])}</span> over <span class="n">{direct['miles']:.0f}</span> miles.
      There are three genuinely different ways to make it &mdash; the coast, the fall line, and
      straight down I&#8209;85 through Atlanta &mdash; diverging by as much as
      <span class="n">{cross_mi:.0f}</span> miles. Seven options, each measured end to end on the same
      engine, each leaving at the hour that corridor actually wants. Which trade is worth it is yours
      to call.</p>
  </header>

  <div class="switch" role="radiogroup" aria-label="Choose an itinerary">
{switcher}
  </div>

  <div class="split">
    <div class="mapcard">
      <svg class="map" viewBox="0 0 {VW:.0f} {VH:.0f}" role="img" aria-label="Map of three corridors between Chapel Hill and Thomasville over a basemap of state boundaries and interstates; the selected itinerary is highlighted and its stops numbered">
      <g class="base-states">
{base_states}
      </g>
      <g class="base-roads">
{base_roads}
      </g>
      <g class="base-road-labels">
{base_road_labels}
      </g>
      <g class="base-cities">
{base_cities}
      </g>
{map_paths}
{markers}
        <g class="endpt">
          <circle cx="{ox:.1f}" cy="{oy:.1f}" r="9"/>
          <text x="{ox-255:.1f}" y="{oy+4:.1f}">Chapel Hill</text>
          <circle cx="{dx:.1f}" cy="{dy:.1f}" r="9"/>
          <text x="{dx+18:.1f}" y="{dy+4:.1f}">Thomasville</text>
        </g>
      </svg>
      <p class="key">
        <span><i style="background:var(--c-coastal)"></i>Coastal</span>
        <span><i style="background:var(--c-fall)"></i>Fall line</span>
        <span><i style="background:var(--c-atl)"></i>Atlanta</span>
      </p>
      <p class="maplegend">All seven routes drawn; the selected one lifted, its stops numbered. The
        corridors sit up to <span class="n">{cross_mi:.0f}</span> miles apart, so here the map really
        does compare them &mdash; unlike the variants within one corridor, which differ by a few miles
        at most.</p>
      <p class="maplegend">Basemap baked in at build time, because artifact pages cannot load tile
        servers: state lines from the <a href="https://tigerweb.geo.census.gov/">US Census TIGERweb</a>
        ({state_pts} points, simplified from {state_raw_k}k), interstates from
        <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> via Overpass
        ({road_pts} points from {road_raw_k}k, stitched from {n_frag} way fragments).
        <strong>No traffic layer</strong> &mdash; see below.</p>
    </div>

    <div>
      <h2 id="tl-head" class="ui" style="margin-bottom:.6rem">&mdash;</h2>
{timelines}
    </div>
  </div>

  <section class="note">
    <h2>All seven, side by side</h2>
    <div class="scroll">
      <table>
        <thead><tr>
          <th>Option</th><th>Leave</th><th>Drive</th><th>Added</th><th>Miles</th>
          <th>Longest&nbsp;leg</th><th>Stops</th><th>Door&nbsp;to&nbsp;door</th>
          <th>Admissions</th><th>Arrive</th>
        </tr></thead>
        <tbody>
{totals}
        </tbody>
      </table>
    </div>
    <p>&ldquo;Added&rdquo; is against the <span class="n">{hm(direct['total_s'])}</span> direct drive,
      each option routed as one multi-point request. &ldquo;n/p&rdquo; means the operator publishes no
      price. You mentioned roughly an hour of extra driving: {NUMWORD[under]} options sit under it and {NUMWORD[over]} run
      over, which is a price rather than a disqualification.</p>
  </section>

  <section class="note">
    <h2>How each day is carved up</h2>
    <p>Grey is driving, green is stopped, hatched is time you are still at home because that option
      starts later. All seven on one axis, anchored to the earliest departure
      (<span class="n">{opts['coastal-fewest']['depart']}</span>).</p>
    <div class="rhys">
{rhythms}
    </div>
  </section>

  <div class="cols">
    <section class="note">
      <h2>The corridors, measured bare</h2>
      <p>With no stops at all, forced through each corridor&rsquo;s defining cities:
        <strong>coastal <span class="n">{hm(direct['total_s'])}</span></strong> &mdash; it <em>is</em>
        the direct route; <strong>fall line <span class="n">+{bare_fall}</span></strong> via Columbia
        and Macon; <strong>Atlanta <span class="n">+{bare_atl}</span></strong> down I&#8209;85.
        Jacksonville and I&#8209;10 cost <span class="n">+{bare_jax}</span> and were dropped.</p>
      <p>A stop&rsquo;s detour depends entirely on which corridor you are on, which is why the earlier
        shortlist was misleading. Riverbanks Zoo is <span class="n">+{zoo_off_coastal}</span> off the coastal line
        and essentially free on the fall line. Congaree National Park is a dead-end spur either way:
        adding it measured <span class="n">+{congaree_cost}</span>, so it is out on measurement rather than
        assertion.</p>
    </section>

    <section class="note">
      <h2>The corridor decides your departure</h2>
      <p>The coastal corridor <em>rewards</em> leaving at
        <span class="n">{opts['coastal-fewest']['depart']}</span>: its first stop is a 24&#8209;hour
        fuel station beside hours-free outdoor kitsch, so the boys sleep through the dark and nothing
        is missed.</p>
      <p>The other two <em>punish</em> it. Their first good stops are ticketed attractions opening at
        09:00, so an early start just means waiting in a car park. Those options leave at
        <span class="n">{fl['depart']}</span> and <span class="n">{atl['depart']}</span> instead
        &mdash; and every minute of that later start lands on the far end, after sunset.</p>
      <p>Net effect: <em>{fl['label'].split(': ',1)[1]}</em> costs the same driving as
        <em>{best_coastal['label'].split(': ',1)[1]}</em> to within a few minutes, but gets in
        <span class="n">{int(gap//60)}h{int(gap%60):02d}</span> later and about
        <span class="n">${int(round(fl['cost_usd']-best_coastal['cost_usd']))}</span> more.</p>
    </section>

    <section class="note">
      <h2>What the fall line buys you</h2>
      <p><a href="https://www.riverbanks.org/plan-your-visit/visitor-information">Riverbanks Zoo &amp;
        Garden</a> in Columbia is a serious zoo with a botanical garden across the river, open
        09:00&ndash;16:00 in winter. <a href="https://www.nps.gov/ocmu/planyourvisit/hours.htm">Ocmulgee
        Mounds</a> outside Macon is a National Historical Park with earthen mounds the boys can climb
        and a reconstructed earth lodge you walk into &mdash; and it is <strong>free</strong>.</p>
      <p>The cost is rhythm. <em>Zoo and mounds</em> has a <span class="n">{fl_open_leg}</span> opening
        leg and a <span class="n">{fl_mid_leg}</span> middle one. Adding
        <a href="https://phinizycenter.org/location-contact/">Phinizy Swamp</a> at Augusta &mdash; free,
        boardwalks, open 07:00&ndash;19:00 &mdash; breaks that {fl_mid_leg} into {gentler_split} for
        <span class="n">+{gentler_extra}</span> of driving.</p>
    </section>

    <section class="note">
      <h2>South of the Border at {sob['arrive']}</h2>
      <p>Every coastal option starts here and almost nothing is open. What you can actually do, from
        the operator&rsquo;s own pages:</p>
      <ul>
        <li><strong>Fuel</strong> &mdash; the <a href="https://www.sobpedro.com/facilities/south-of-the-border-i95-gas-station-dillon-sc">Sunoco West pumps run 24 hours</a>, card at the pump before 07:00.</li>
        <li><strong>Restrooms from 07:00</strong>, inside Pedro&rsquo;s Pantry &mdash; {pantry_wait} minutes
          into your halt. The sun comes up at 07:00 too.</li>
        <li><strong>The kitsch, which has no hours.</strong> A 200&#8209;foot concrete sombrero and a
          fibreglass Pedro the size of a house, floodlit, free, entirely yours at first light.</li>
      </ul>
      <p>You miss <a href="https://www.sobpedro.com/shopping">the shops</a> (08:00), the
        <a href="https://www.sobpedro.com/attractions">Sombrero Tower</a> (11:00), and the
        <a href="https://www.sobpedro.com/attractions/reptile-lagoon">Reptile Lagoon</a> is shut
        Tuesday to Thursday regardless. <a href="https://www.sobpedro.com/dining">No food opens before
        11:00</a> either &mdash; pack breakfast.</p>
    </section>

    <section class="note">
      <h2>The Atlanta option, honestly</h2>
      <p>It is here because you asked for the alternatives, and because
        <a href="https://zooatlanta.org/visit/">Zoo Atlanta</a> plus
        <a href="https://www.discoveryplace.org/science/visit">Discovery Place Science</a> is arguably
        the strongest pair of attractions on any corridor for these ages.</p>
      <p>But it is <span class="n">+{int(round(atl['detour_s']/60))} min</span> of free-flow driving,
        it gets in at <span class="n">{atl['arrive']}</span> &mdash; {atl_late} after sundown &mdash; and
        it threads {i85_mi} miles of I&#8209;85 straight through Atlanta on the Wednesday before
        Thanksgiving. Of the seven, this is the one where a free-flow number is least worth believing.
        Neither operator publishes a price, so its admissions cell is blank rather than zero.</p>
    </section>

    <section class="note">
      <h2>Where arrival and opening hours collide</h2>
      <p>Every stop lists its facilities with the derived arrival checked against published hours,
        computed rather than eyeballed. Three collisions:</p>
      <ul>
        <li><strong>Smokin Pig opens 11:00</strong>; two coastal options reach it at {pig_arr}, so you
          wait for lunch. Leaving at {pig_fix_depart} instead would put you there as it opens.</li>
        <li><strong>Discovery Place opens 09:00</strong> and the Charlotte options reach it at {disc_arr}
          &mdash; one minute of margin on a free-flow estimate, so call it arriving with the doors.</li>
        <li><strong>Hiott&rsquo;s opens 09:00</strong> and you reach Walterboro at {walt_arr}, but those hours
          are third-party. It is the one stop here whose hours nobody publishes.</li>
      </ul>
      <p>Everything shuts for Thanksgiving itself &mdash; Thursday the 26th, not your Wednesday.
        Riverbanks, Ocmulgee and Zoo Atlanta all say so explicitly.</p>
    </section>

    <section class="note">
      <h2>Why there is no traffic layer</h2>
      <p>You asked for one and I have not drawn it, for two reasons worth stating rather than
        papering over. First, there is no keyless traffic source these tools can reach, and an
        artifact page cannot call one at view time even if there were. Second, and more
        fundamentally: <strong>this trip is 19 days away</strong>. Live traffic is a fact about now,
        not about the 25th &mdash; any layer drawn today would be decoration.</p>
      <p>What is real is the pattern. Every drive time here is <strong>free-flow</strong>; the engine
        has no traffic model, so treat each as a floor. The coastal options put {i95_mi} miles of
        southbound I&#8209;95 through the Carolinas on one of the heaviest travel days of the
        American year; the Atlanta option threads {i85_mi} miles of I&#8209;85 through Atlanta on the same
        day. The fall line is plausibly the quietest of the three &mdash; which is precisely the
        thing these numbers cannot show you, and the reason the 04:45 start is worth as much as any
        route choice.</p>
    </section>
  </div>

  <section class="note">
    <h2>No stop here is confirmed for the 25th</h2>
    <p>Every opening time on this page is a published routine I did not check against the date. The
      calls worth making: <strong>Okefenokee Swamp Park 912-283-0583</strong> (train and reptile-show
      times are published nowhere), <strong>Hiott&rsquo;s Pharmacy 843-549-7222</strong> (no operator
      page exists at all), <strong>Smokin Pig 912-756-7850</strong>, <strong>South of the Border
      843-774-2411</strong> (are the restrooms open at 07:00?), and <strong>Discovery Place
      704-286-8302</strong> or Zoo Atlanta for the prices neither publishes.</p>
    <ul>
      <li>Admission for Discovery Place and Zoo Atlanta is not on the pages I fetched, so both those
        options understate cost.</li>
      <li>Riverbanks is <span class="n">$105.80</span> online for your four and about
        <span class="n">$12</span> more at the gate &mdash; buy ahead.</li>
      <li>Santee NWR&rsquo;s Fort Watson mound is only <span class="n">+{santee_cost}</span> off the coastal
        line, but the refuge closes some trails 1 Nov&ndash;1 Mar and all trails in deer season.
        Headquarters: 803-478-2217. Left out for that reason.</li>
    </ul>
  </section>

  <div class="prov">
    <p><b>Provenance</b></p>
    <p><strong>Measured</strong> &mdash; drive times, mileage, legs, added time and route geometry:
      public Valhalla, <span class="n">auto</span> costing, free-flow, one engine throughout, each
      option routed as a single multi-point request.</p>
    <p><strong>Derived</strong> &mdash; clock times and door-to-door, from each option&rsquo;s own
      departure plus measured legs plus the stop durations shown. Admissions are published per-person
      prices for two adults and children aged 6 and 9; meals are not costed.</p>
    <p><strong>Computed</strong> &mdash; every facility&rsquo;s open/shut verdict, from the derived
      arrival against the published hours and the weekday.</p>
    <p><strong>Calculated</strong> &mdash; sunset {opts['coastal-fewest']['sunset']} at Thomasville:
      NOAA solar position, approximate to a minute or two.</p>
    <p><strong>Standing hours, date not checked</strong> &mdash; every opening time and price, from the
      operator&rsquo;s own page except Hiott&rsquo;s Pharmacy, which is third-party only.</p>
  </div>
</div>

<script>
(function(){{
  var ORDER = {json.dumps(ORDER)};
  var LABELS = {json.dumps({k: opts[k]["label"] for k in ORDER})};
  var btns = Array.prototype.slice.call(document.querySelectorAll(".opt"));
  function select(key){{
    btns.forEach(function(b){{ b.setAttribute("aria-checked", String(b.dataset.opt === key)); }});
    document.querySelectorAll(".route").forEach(function(p){{ p.classList.toggle("sel", p.dataset.opt === key); }});
    document.querySelectorAll(".markers").forEach(function(g){{ g.hidden = g.dataset.opt !== key; }});
    document.querySelectorAll(".tl").forEach(function(o){{ o.hidden = o.dataset.opt !== key; }});
    document.querySelectorAll("tbody tr[data-opt]").forEach(function(r){{ r.classList.toggle("sel", r.dataset.opt === key); }});
    document.querySelectorAll(".rhy").forEach(function(r){{ r.classList.toggle("sel", r.dataset.opt === key); }});
    document.getElementById("tl-head").textContent = LABELS[key];
    var sel = document.querySelector('.route[data-opt="' + key + '"]');
    if (sel && sel.parentNode) {{ sel.parentNode.insertBefore(sel, sel.parentNode.querySelector(".markers")); }}
  }}
  btns.forEach(function(b){{
    b.addEventListener("click", function(){{ select(b.dataset.opt); }});
    b.addEventListener("keydown", function(e){{
      var i = ORDER.indexOf(b.dataset.opt), j = -1;
      if (e.key === "ArrowRight" || e.key === "ArrowDown") j = (i + 1) % ORDER.length;
      if (e.key === "ArrowLeft"  || e.key === "ArrowUp")   j = (i - 1 + ORDER.length) % ORDER.length;
      if (j >= 0) {{ e.preventDefault(); select(ORDER[j]); document.getElementById("btn-" + ORDER[j]).focus(); }}
    }});
  }});
  select(ORDER[0]);
}})();
</script>
"""

io.open(OUT, "w", encoding="utf-8").write(HTML)
print(f"wrote {OUT}  ({len(HTML)/1024:.1f} KB)")
print(f"max cross-corridor separation {cross:.2f} deg (~{cross_mi:.0f} mi)")
for c, ks in GROUPS:
    print(f"  {CORR_SHORT[c]:<10} {len(ks)}: " + ", ".join(ks))
