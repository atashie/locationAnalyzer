"""The routing profile, as a value that can be hashed. Phase 1 stage S0.4.

`SurfaceKey` carries a `profile_version` and a `grid_version`. If those are strings a human types,
nothing forces them to change when the thing they describe changes — and the failure mode is a
cache or a manifest that confidently serves an answer built under different rules. The speed tables,
the access classification and the penalties are all module constants, so the version can be
*derived* from them instead.

This is S4.1's "keyed by input hashes" applied to the parameters rather than the data. It does not
cover the data: the OSM extract and the Overture release are separate key fields.

Deliberately out of scope: `max_access_m` and the destination snap bound are per-build choices, not
properties of the model, so they are explicit `SurfaceKey` fields where a reader can see them.
"""
from __future__ import annotations

import hashlib
import json

from .grid import GridSpec
from .traveltime import access, expansion, snap, speeds


def profile_params() -> dict:
    """Every model constant that changes a reported travel time, as JSON-safe values.

    Read at call time, so a changed constant changes the digest — that is the point.
    """
    return {
        "mode_speed_mps": dict(sorted(speeds.MODE_SPEED_MPS.items())),
        "drive_friction_mph": dict(sorted(speeds.DRIVE_FRICTION_MPH.items())),
        "default_drive_friction_mph": speeds.DEFAULT_DRIVE_FRICTION_MPH,
        "access_speed_factor": dict(sorted(speeds.ACCESS_SPEED_FACTOR.items())),
        "bike_exclude": sorted(speeds.BIKE_EXCLUDE),
        "walk_exclude": sorted(speeds.WALK_EXCLUDE),
        "drive_highways": sorted(speeds.DRIVE_HIGHWAYS),
        "extra_way_tags": sorted(speeds.EXTRA_WAY_TAGS),
        "forbidden_access": sorted(access.FORBIDDEN_ACCESS),
        "restricted_access": sorted(access.RESTRICTED_ACCESS),
        "permitted_access": sorted(access.PERMITTED_ACCESS),
        "restricted_penalty_s": dict(sorted(access.RESTRICTED_PENALTY_S.items())),
        "node_eps": snap._NODE_EPS,
        # The expansion adapter's quantisation decides which endpoints merge into one node, so it
        # changes reported times for the drive and bike layers (Codex pass-8 H3).
        "expansion_node_snap_m": expansion._NODE_SNAP_M,
        "expansion_min_epsilon_s": expansion._MIN_EPSILON_S,
        # Policy choices that change which network is routed on, not just how fast it is.
        "walk_symmetrised": True,
        "largest_component_only": True,
    }


def _digest(obj) -> str:
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.blake2b(blob, digest_size=8).hexdigest()


def profile_version() -> str:
    """`speeds-v0+<digest>`. The prefix is for humans; the digest is what actually identifies it."""
    return f"speeds-v0+{_digest(profile_params())}"


def grid_version(grid: GridSpec) -> str:
    """Derived from the grid's own geometry, so a re-origined or re-resolutioned grid cannot reuse
    a cached surface. The 100 m and 200 m Triangle grids are **not** nested (origins 661900/4003500
    and 661800/4003600), which is exactly why the origin is in the digest and not just the cell
    size (Codex pass-7 C3)."""
    return "grid-v0+" + _digest({
        "crs": grid.crs, "x_min": grid.x_min, "y_max": grid.y_max,
        "cell_m": grid.cell_m, "ncols": grid.ncols, "nrows": grid.nrows,
    })
