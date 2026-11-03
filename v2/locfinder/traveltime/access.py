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
RESTRICTED_ACCESS = frozenset({"private", "customers", "delivery", "permit", "agricultural", "forestry",
                               # `destination` literally means "no through traffic", so it is the
                               # clearest case for a through-routing penalty, not an open road
                               # (Codex pass-6 H3; it was previously classified open with no penalty).
                               "destination"})
PERMITTED_ACCESS = frozenset({"yes", "designated", "permissive", "official", "unknown"})

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


# Narrowest tag first: OSM's access hierarchy is `access` < `vehicle` < `motor_vehicle` < `motorcar`,
# and the most specific tag present wins (Codex pass-6 H5: `motor_vehicle=no` + `motorcar=yes` was
# read as forbidden because the broader tag was consulted first).
_MODE_TAG_ORDER = {
    "drive": ("motorcar", "motor_vehicle", "vehicle"),
    "bike": ("bicycle", "vehicle"),
    "walk": ("foot",),
}


def _mode_tag_values(data, mode: str) -> list[str]:
    """Values of the narrowest mode tag present, or [] if none is."""
    for key in _MODE_TAG_ORDER[mode]:
        vals = _values(data, key)
        if vals:
            return vals
    return []


def classify_access(data, mode: str) -> str:
    """Return OPEN, RESTRICTED or FORBIDDEN for this edge and mode.

    A mode-specific tag (`foot`, `bicycle`, `motor_vehicle`) overrides the generic `access` tag,
    which is how OSM intends them to be read: `access=private` + `foot=yes` is a private road that
    pedestrians may use.
    """
    for values in (_mode_tag_values(data, mode), _values(data, "access")):
        if not values:
            continue
        # Conservative within a tag: the strictest value present wins, so a simplified way carrying
        # ["yes", "private"] is restricted rather than open. Previously the specific and generic
        # tags aggregated differently, so `foot=["yes","private"]` came out OPEN while
        # `access=["yes","private"]` came out RESTRICTED (Codex pass-6 H5).
        if any(v in FORBIDDEN_ACCESS for v in values):
            return FORBIDDEN
        if any(v in RESTRICTED_ACCESS for v in values):
            return RESTRICTED
        if any(v in PERMITTED_ACCESS for v in values):
            return OPEN
        # an unrecognised value on the narrowest tag present is not evidence of permission;
        # fall through to the next, broader tag
    return OPEN


def access_penalty_s(data, mode: str) -> float:
    """Cost-only penalty for this edge. Zero unless the edge is restricted."""
    return RESTRICTED_PENALTY_S[mode] if classify_access(data, mode) == RESTRICTED else 0.0
