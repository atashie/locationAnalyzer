"""Static speed model ported from CHCCS_geospatial/src/school_desert.py (sources
documented there: MUTCD 4E.06, FHWA-HRT-06-042, HCM6 Ch.16/19/20). Adult walk speed
replaces the K-5 value. These are PRIORS; Gate G1 measures them against Valhalla.
"""
from __future__ import annotations

import networkx as nx

MODE_SPEED_MPS = {
    "walk": 1.40,  # adult, ~3.1 mph
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

# Highway values each mode may use (explicit, so the filter is auditable).
DRIVE_HIGHWAYS = set(DRIVE_FRICTION_MPH)
BIKE_EXCLUDE = {"motorway", "motorway_link", "steps"}
WALK_EXCLUDE = {"motorway", "motorway_link", "trunk", "trunk_link"}

ACCESS_SPEED_FACTOR = {"walk": 0.9, "bike": 0.8, "drive": 0.2}


def _highway(data) -> str:
    h = data.get("highway", "unclassified")
    return h[0] if isinstance(h, list) else h


def edge_allowed(data, mode: str) -> bool:
    h = _highway(data)
    if mode == "drive":
        return h in DRIVE_HIGHWAYS
    if mode == "bike":
        return h not in BIKE_EXCLUDE
    if mode == "walk":
        return h not in WALK_EXCLUDE
    raise ValueError(mode)


def add_travel_times(G: nx.MultiDiGraph, *, mode: str) -> nx.MultiDiGraph:
    """Set `travel_time` (seconds) on every edge from `length` (metres) and the mode
    speed. Edges not allowed for the mode are removed. Mutates and returns G."""
    to_remove = []
    for u, v, k, data in G.edges(keys=True, data=True):
        if not edge_allowed(data, mode):
            to_remove.append((u, v, k))
            continue
        length = float(data["length"])
        if mode == "drive":
            mph = DRIVE_FRICTION_MPH.get(_highway(data), DEFAULT_DRIVE_FRICTION_MPH)
            speed = mph * MPH_TO_MPS
        else:
            speed = MODE_SPEED_MPS[mode]
        data["travel_time"] = max(length / speed, 0.1)
    G.remove_edges_from(to_remove)
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
