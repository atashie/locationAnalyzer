"""Three-valued access classification, so restricted roads can be *reached* without becoming
through-routes.

The old rule was a single allow/deny, which is what real routers do not do. Measured on the
Triangle extract:

| class | edges | meaning |
|---|---|---|
| open | 1,291,042 | usable normally |
| restricted | 126,157 | `access=private`, `customers`, `delivery`, `permit`, `agricultural`, `forestry` |
| forbidden | 1,278 | `access=no`, `military` |

Blocking all 126,157 restricted edges made every home on a private drive unreachable, which is a
systematic coverage hole for a home-search product: 98,124 nodes sit on restricted edges, and 92.8%
of them are within one restricted hop of the open network — driveways, in other words, which are
exactly where people live. Allowing them freely is wrong in the other direction, because a gated
community or a parking aisle would become a public shortcut.

The resolution is the one mainstream engines use: a restricted edge costs extra to *choose* but
still takes its real time to *travel*. That needs two weights, which is why `csr.py` builds a cost
matrix and a time matrix over the same sparsity and `arrival.py` selects paths on cost and reports
time. Valhalla does the same thing with its `private_access_penalty`.

`forbidden` edges are removed outright. That is not over-strict: every way leading out of the RDU
Terminal 2 stub was `access=no`, and blocking those was correct (see
docs/experiments/spotcheck-engines.md).
"""
from __future__ import annotations

FORBIDDEN_ACCESS = frozenset({"no", "military"})
RESTRICTED_ACCESS = frozenset({"private", "customers", "delivery", "permit", "agricultural", "forestry"})
PERMITTED_ACCESS = frozenset({"yes", "designated", "permissive", "official", "destination", "unknown"})

# Seconds added to an edge's COST (never to its reported time) for choosing a restricted road.
# PRIORS, not measurements: Valhalla's documented default private-access penalty for driving is
# 450 s, and a pedestrian or cyclist on a private path is less deterred. Gate G1-style measurement
# should revisit these before any layer built on them is published.
RESTRICTED_PENALTY_S = {"drive": 450.0, "bike": 120.0, "walk": 120.0}

OPEN, RESTRICTED, FORBIDDEN = "open", "restricted", "forbidden"


def _values(data, key: str) -> list[str]:
    v = data.get(key)
    if v is None:
        return []
    return [str(x) for x in v] if isinstance(v, list) else [str(v)]


def _mode_tag_values(data, mode: str) -> list[str]:
    if mode == "drive":
        return _values(data, "motor_vehicle") or _values(data, "motorcar")
    if mode == "bike":
        return _values(data, "bicycle")
    if mode == "walk":
        return _values(data, "foot")
    raise ValueError(mode)


def classify_access(data, mode: str) -> str:
    """Return OPEN, RESTRICTED or FORBIDDEN for this edge and mode.

    A mode-specific tag (`foot`, `bicycle`, `motor_vehicle`) overrides the generic `access` tag,
    which is how OSM intends them to be read: `access=private` + `foot=yes` is a private road that
    pedestrians may use.
    """
    specific = _mode_tag_values(data, mode)
    if specific:
        if any(s in FORBIDDEN_ACCESS for s in specific):
            return FORBIDDEN
        if any(s in PERMITTED_ACCESS for s in specific):
            return OPEN
        if any(s in RESTRICTED_ACCESS for s in specific):
            return RESTRICTED
    generic = _values(data, "access")
    if any(a in FORBIDDEN_ACCESS for a in generic):
        return FORBIDDEN
    if any(a in RESTRICTED_ACCESS for a in generic):
        return RESTRICTED
    return OPEN


def access_penalty_s(data, mode: str) -> float:
    """Cost-only penalty for this edge. Zero unless the edge is restricted."""
    return RESTRICTED_PENALTY_S[mode] if classify_access(data, mode) == RESTRICTED else 0.0
