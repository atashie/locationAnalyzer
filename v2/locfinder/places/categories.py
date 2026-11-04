"""Wedge categories -> Overture taxonomy (release 2026-10-21.0 schema: `taxonomy`
struct with `primary` and `hierarchy`; the old `categories` column is gone) and OSM
tags. Kept explicit so the mapping is auditable; Gate G6 decides the preferred source
per category. Observed counts for the Phase 0 slice are in docs/experiments/g6-poi-coverage.md.
"""
from __future__ import annotations

import numpy as np

WEDGE_CATEGORIES: dict[str, dict] = {
    "grocery": {
        "overture_primary": set(),
        "overture_hierarchy": {"grocery_store"},            # includes ethnic/organic grocery stores
        "exclude_primary": {"farmers_market"},
        "osm": {("shop", "supermarket"), ("shop", "greengrocer")},
    },
    "park": {
        "overture_primary": {"park", "state_park", "national_park"},
        "overture_hierarchy": {"park"},
        "exclude_primary": {"dog_park", "skate_park", "amusement_park", "mobile_home_park", "rv_park",
                            "water_park", "parking", "parking_lot", "parking_garage", "trailer_park"},
        "osm": {("leisure", "park"), ("leisure", "nature_reserve")},
    },
    "playground": {
        "overture_primary": {"playground"},
        "overture_hierarchy": set(),
        "exclude_primary": set(),
        "osm": {("leisure", "playground")},
    },
    "coffee": {
        "overture_primary": {"coffee_shop", "cafe", "coffee_roastery"},
        "overture_hierarchy": set(),
        "exclude_primary": {"internet_cafe"},
        "osm": {("amenity", "cafe")},
    },
    "pharmacy": {
        "overture_primary": {"pharmacy", "drugstore"},
        "overture_hierarchy": set(),
        "exclude_primary": set(),
        "osm": {("amenity", "pharmacy")},
    },
    "school": {
        "overture_primary": {"elementary_school", "public_school", "school"},
        "overture_hierarchy": set(),
        "exclude_primary": set(),
        "osm": {("amenity", "school")},
    },
    "library": {
        "overture_primary": {"library"},
        "overture_hierarchy": set(),
        "exclude_primary": set(),
        "osm": {("amenity", "library")},
    },
    "transit_stop": {
        # Overture carries stations/facilities but no bus stops; OSM is the stop source.
        "overture_primary": {"bus_station", "train_station", "public_transit_facility_or_service"},
        "overture_hierarchy": set(),
        "exclude_primary": set(),
        "osm": {("highway", "bus_stop"), ("railway", "station"), ("railway", "tram_stop")},
    },
    "trail": {
        "overture_primary": {"hiking_trail", "mountain_bike_trail"},
        "overture_hierarchy": set(),
        "exclude_primary": set(),
        "osm": set(),  # trailheads are sparse in OSM tags; left for a later pass
    },
}


def _as_set(values) -> set:
    """Overture list fields arrive as Python lists, NumPy arrays, or None depending on
    the reader; normalise without ever testing an array's truth value."""
    if values is None:
        return set()
    if hasattr(values, "tolist"):
        values = values.tolist()
    try:
        return {v for v in values if v is not None}
    except TypeError:
        return set()


def taxonomy_matches(taxonomy, spec: dict) -> bool:
    if taxonomy is None or not hasattr(taxonomy, "get"):
        return False
    primary = taxonomy.get("primary")
    hierarchy = _as_set(taxonomy.get("hierarchy"))
    if primary in spec["exclude_primary"]:
        return False
    return primary in spec["overture_primary"] or bool(hierarchy & spec["overture_hierarchy"])


def select_overture(gdf, category: str):
    """Rows matching the category, in a **deterministic order**.

    Sorted by Overture `id`, because several spikes take "the first N POIs" and file order is not
    stable across downloads. Re-acquiring the Triangle at the routing extent changed both the row
    count and the ordering, which would silently have changed *which three* groceries an experiment
    used — so a re-measurement would not have been comparable with the one it replaced, for a
    reason nothing recorded.
    """
    spec = WEDGE_CATEGORIES[category]
    mask = gdf["taxonomy"].apply(lambda t: taxonomy_matches(t, spec)).to_numpy(dtype=bool)
    out = gdf[mask]
    return out.sort_values("id") if "id" in out.columns else out


def select_osm(gdf, category: str):
    """Rows matching the category, in a deterministic order (by `feature_id`, the frame's index).
    Same reason as `select_overture`."""
    spec = WEDGE_CATEGORIES[category]
    mask = np.zeros(len(gdf), dtype=bool)
    for key, value in spec["osm"]:
        if key in gdf.columns:
            mask |= (gdf[key].astype("string") == value).fillna(False).to_numpy(dtype=bool)
    return gdf[mask].sort_index()
