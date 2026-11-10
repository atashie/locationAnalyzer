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

Restricted access is handled by `access.py`'s three-valued classification rather than a
single allow/deny: `access=no` is removed, `access=private` and friends are **kept with a
cost penalty** so a home on a private drive is reachable while a gated cut-through does not
become a public shortcut. Every edge therefore carries two weights, `travel_time` (real
seconds, what a user is shown) and `cost` (what path selection minimises). They are equal on
open edges. Use `csr.graph_to_cost_time_csr` and `arrival.arrival_seconds_two_weight` to
consume them; using the single-weight path on a penalised graph reports inflated minutes.
"""
from __future__ import annotations

import networkx as nx

from .access import FORBIDDEN, RESTRICTED, access_penalty_s, classify_access

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

# Access classification lives in access.py (three-valued: open / restricted / forbidden).
# The old single allow/deny blocked 126,157 restricted edges outright and made every home on a
# private drive unreachable; see access.py for the measurements and the fix.

ACCESS_SPEED_FACTOR = {"walk": 0.9, "bike": 0.8, "drive": 0.2}

# Extra OSM way tags osmnx must keep for these rules (set before parsing the XML).
#
# `surface` is retained even though no rule reads it yet. The owner walked an audited journey and
# found 25 minutes against a published 13.5; two rounds of measurement then asked which *highway
# classes* to delete, because class was the only evidence the extracted graph held. It is the wrong
# evidence -- `track` says nothing about whether a way is paved or passable -- and the tag that
# would say was never pulled out of the PBF. A tag the graph does not carry cannot be honoured by
# any rule, so extraction comes first and a decision about unpaved ways second. 166,067 way tags
# in the Triangle extract carry it. See
# docs/engineering-notes/project-phase1-s3-soft-way-dependence.md.
# `vehicle` is a straight defect fix, found by writing the invariant down as a test rather than by
# looking for it: `access._MODE_TAG_ORDER` consults it for the drive and bike modes -- it is the
# middle tier of OSM's `access` < `vehicle` < `motor_vehicle` < `motorcar` hierarchy -- and it was
# never extracted, so that branch could not fire. 102 way tags in the Triangle XML carry it, which
# is 332 directed edges in the simplified graph (278 `no`, 38 `yes`, 16 `forestry`).
#
# Measured, not assumed (`scripts/measure_vehicle_tag_effect.py`): the walk layer is **unaffected**,
# 0 edges changing class, because walk consults `foot` alone. Drive changes 234 edges but only 24 on
# a highway drive may use, and those 24 split **12 stricter and 12 more permissive** -- a
# `vehicle=forestry` on an `access=no` way goes forbidden -> restricted, which *restores* an edge
# the old rule removed outright. Bike changes 28, all usable: 14 forbidden -> restricted,
# 12 open -> forbidden, 2 open -> restricted. So this is not a one-directional tightening, which is
# what I first wrote before measuring it.
EXTRA_WAY_TAGS = ["foot", "bicycle", "motor_vehicle", "motorcar", "oneway:bicycle", "sidewalk",
                  "surface", "vehicle"]


def _values(data, key: str) -> list[str]:
    v = data.get(key)
    if v is None:
        return []
    return [str(x) for x in v] if isinstance(v, list) else [str(v)]


def highway_values(data) -> list[str]:
    vals = _values(data, "highway")
    return vals or ["unclassified"]


def highway_allowed(data, mode: str) -> bool:
    """Whether the edge's highway tag(s) permit this mode at all, ignoring access tags."""
    hws = highway_values(data)
    if mode == "drive":
        return all(h in DRIVE_HIGHWAYS for h in hws)
    if mode == "bike":
        return not any(h in BIKE_EXCLUDE for h in hws)
    if mode == "walk":
        return not any(h in WALK_EXCLUDE for h in hws)
    raise ValueError(mode)


def edge_allowed(data, mode: str) -> bool:
    """Usable by this mode at all. Restricted edges ARE allowed: they are penalised in `cost`,
    not removed, so destinations behind them stay reachable (see access.py)."""
    return highway_allowed(data, mode) and classify_access(data, mode) != FORBIDDEN


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
        travel_time = max(length / speed, 0.1)
        data["travel_time"] = travel_time
        # `cost` is what path selection minimises; `travel_time` is what a user is shown.
        penalty = access_penalty_s(data, mode)
        data["cost"] = travel_time + penalty
        if penalty:
            data["access_restricted"] = True
        if mode == "bike" and "no" in _values(data, "oneway:bicycle") and not G.has_edge(v, u):
            contraflow.append((v, u, dict(data)))
    G.remove_edges_from(to_remove)
    for v, u, data in contraflow:
        if not G.has_edge(v, u):
            G.add_edge(v, u, **data)
    return G


def _physical_key(data) -> tuple:
    """Identity of the *road*, not of the node pair.

    `osmid` names the way; a simplified edge carries a list of them. Length disambiguates two
    distinct ways that happen to share an id list, and is rounded because reprojection is not
    bit-exact.
    """
    osmid = data.get("osmid")
    if isinstance(osmid, (list, tuple)):
        osmid = tuple(osmid)
    return (osmid, round(float(data.get("length", 0.0)), 2))


def symmetrise(G: nx.MultiDiGraph) -> nx.MultiDiGraph:
    """Add a reverse edge for every road that lacks one. ONLY valid for walk graphs: pedestrians
    ignore one-way restrictions; cyclists and drivers do not.

    **Deduplicated per physical road, not per node pair** (Codex pass-14 H3). The first version
    asked `G.has_edge(v, u)`, so the existence of *any* edge from `v` to `u` suppressed the reverse
    of *every* road from `u` to `v`. Where those are different roads with different access classes,
    a legitimate pedestrian route disappears: Codex's executed case had an **open** `A->B` at 100 s
    and a **restricted** `B->A` at 1 s, so the open road got no walkable reverse and a node behind
    it became unreachable under any policy that declines the restricted one. Adding the missing open
    reverse makes that journey 110 s.

    This matters beyond the access audit, because it silently removed pedestrian edges from the
    shipped walk graph. Separating access classes downstream cannot recover an alternative that was
    already discarded here.
    """
    present = {(u, v, _physical_key(data)) for u, v, data in G.edges(data=True)}
    missing = []
    for u, v, data in G.edges(data=True):
        if (v, u, _physical_key(data)) not in present:
            missing.append((v, u, dict(data)))
    for v, u, data in missing:
        G.add_edge(v, u, **data)
    return G


def access_speed_mps(mode: str) -> float:
    base = DEFAULT_DRIVE_FRICTION_MPH * MPH_TO_MPS if mode == "drive" else MODE_SPEED_MPS[mode]
    return ACCESS_SPEED_FACTOR[mode] * base


def max_speed_mps(mode: str) -> float:
    """The fastest speed this model can assign for `mode`, over every edge and the access leg.

    Used to turn an off-network distance into a sound lower bound on travel time (`status.py`).
    `access_speed_mps` is deliberately *not* that bound: the access factors are all below 1, so an
    access-speed estimate exceeds the time a journey covering the same distance on a road would
    take, and an over-estimate used as a lower bound would exclude cells that should be unknown.
    """
    if mode == "drive":
        return max(DRIVE_FRICTION_MPH.values()) * MPH_TO_MPS
    return max(MODE_SPEED_MPS[mode], access_speed_mps(mode))
