"""Static speed model and per-mode access rules.

Speeds are ported from CHCCS_geospatial/src/school_desert.py (sources documented
there: MUTCD 4E.06, FHWA-HRT-06-042, HCM6 Ch.16/19/20) with an adult walking speed.
This is a NEW profile, not a faithful port: CHCCS's intersection penalties are not
modelled here. These are PRIORS; Gate G1 measures them against Valhalla.

Access rules (Codex pass-3 H3): a simplified OSM edge may carry list-valued tags;
an edge is allowed for a mode only if EVERY highway value is allowed, and the slowest
value sets the drive speed. `access`, `foot`, `bicycle`, `motor_vehicle` and
`oneway:bicycle` are honoured. Turn restrictions are NOT modelled; that limitation is
an adoption criterion in the G1 verdict.
"""
from __future__ import annotations

import networkx as nx

MODE_SPEED_MPS = {
    "walk": 1.40,  # adult, ~3.1 mph (5.04 km/h)
    "bike": 4.50,  # ~10 mph, utility cycling
}

# Free-flow "friction" speeds by highway tag (mph), mid-block delay included.
DRIVE_FRICTION_MPH = {
    "motorway": 62, "motorway_link": 40, "trunk": 45, "trunk_link": 35,
    "primary": 35, "primary_link": 30, "secondary": 30, "secondary_link": 25,
    "tertiary": 25, "tertiary_link": 22, "unclassified": 22, "residential": 20,
    "living_street": 12, "service": 10,
}
DEFAULT_DRIVE_FRICTION_MPH = 20
MPH_TO_MPS = 0.44704

DRIVE_HIGHWAYS = set(DRIVE_FRICTION_MPH)
BIKE_EXCLUDE = {"motorway", "motorway_link", "steps", "construction", "proposed", "raceway"}
WALK_EXCLUDE = {"motorway", "motorway_link", "trunk", "trunk_link", "construction", "proposed", "raceway"}

# KNOWN LIMITATION (measured 2026-11-03): this is a single allow/deny, but real routers distinguish
# THROUGH traffic from START/END access. `access=private` appears on 118,035 edges in the Triangle
# extract and `access=customers` on 8,003; blocking them outright makes every home on a private
# drive unreachable, which is a systematic coverage hole for a home-search product. Valhalla
# penalises private access instead of forbidding it, which is why it reaches destinations we cannot.
# Fixing this is the first requirement if our own engine is ever revived for driving.
# See docs/experiments/spotcheck-engines.md, "the airport stub was not an OpenStreetMap gap".
NO_ACCESS = {"no", "private", "customers", "delivery", "agricultural", "forestry", "military"}
YES_ACCESS = {"yes", "designated", "permissive", "official", "destination"}

ACCESS_SPEED_FACTOR = {"walk": 0.9, "bike": 0.8, "drive": 0.2}

# Extra OSM way tags osmnx must keep for these rules (set before parsing the XML).
EXTRA_WAY_TAGS = ["foot", "bicycle", "motor_vehicle", "motorcar", "oneway:bicycle", "sidewalk"]


def _values(data, key: str) -> list[str]:
    v = data.get(key)
    if v is None:
        return []
    return [str(x) for x in v] if isinstance(v, list) else [str(v)]


def highway_values(data) -> list[str]:
    vals = _values(data, "highway")
    return vals or ["unclassified"]


def edge_allowed(data, mode: str) -> bool:
    hws = highway_values(data)
    access = _values(data, "access")
    if mode == "drive":
        if any(h not in DRIVE_HIGHWAYS for h in hws):
            return False
        specific = _values(data, "motor_vehicle") or _values(data, "motorcar")
    elif mode == "bike":
        if any(h in BIKE_EXCLUDE for h in hws):
            return False
        specific = _values(data, "bicycle")
    elif mode == "walk":
        if any(h in WALK_EXCLUDE for h in hws):
            return False
        specific = _values(data, "foot")
    else:
        raise ValueError(mode)
    if any(s in NO_ACCESS for s in specific):
        return False
    if any(s in YES_ACCESS for s in specific):
        return True
    if any(a in NO_ACCESS for a in access):
        return False
    return True


def drive_speed_mps(data) -> float:
    mph = min(DRIVE_FRICTION_MPH.get(h, DEFAULT_DRIVE_FRICTION_MPH) for h in highway_values(data))
    return mph * MPH_TO_MPS


def add_travel_times(G: nx.MultiDiGraph, *, mode: str) -> nx.MultiDiGraph:
    """Set `travel_time` (seconds) on every allowed edge from `length` (metres) and the
    mode speed; remove edges the mode may not use. For bike, add contraflow reverse
    edges where `oneway:bicycle=no`. Mutates and returns G."""
    to_remove = []
    contraflow = []
    for u, v, k, data in G.edges(keys=True, data=True):
        if not edge_allowed(data, mode):
            to_remove.append((u, v, k))
            continue
        length = float(data["length"])
        speed = drive_speed_mps(data) if mode == "drive" else MODE_SPEED_MPS[mode]
        data["travel_time"] = max(length / speed, 0.1)
        if mode == "bike" and "no" in _values(data, "oneway:bicycle") and not G.has_edge(v, u):
            contraflow.append((v, u, dict(data)))
    G.remove_edges_from(to_remove)
    for v, u, data in contraflow:
        if not G.has_edge(v, u):
            G.add_edge(v, u, **data)
    return G


def symmetrise(G: nx.MultiDiGraph) -> nx.MultiDiGraph:
    """Add a reverse edge wherever one is missing. ONLY valid for walk graphs:
    pedestrians ignore one-way restrictions; cyclists and drivers do not."""
    missing = []
    for u, v, data in G.edges(data=True):
        if not G.has_edge(v, u):
            missing.append((v, u, dict(data)))
    for v, u, data in missing:
        G.add_edge(v, u, **data)
    return G


def access_speed_mps(mode: str) -> float:
    base = DEFAULT_DRIVE_FRICTION_MPH * MPH_TO_MPS if mode == "drive" else MODE_SPEED_MPS[mode]
    return ACCESS_SPEED_FACTOR[mode] * base
