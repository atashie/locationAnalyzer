"""Wedge categories -> Overture primary categories and OSM tags. Kept explicit so the
mapping is auditable; Gate G6 decides the preferred source per category."""
from __future__ import annotations

WEDGE_CATEGORIES: dict[str, dict] = {
    "grocery": {
        "overture": {"grocery_store", "supermarket"},
        "osm": {("shop", "supermarket"), ("shop", "greengrocer")},
    },
    "park": {
        "overture": {"park"},
        "osm": {("leisure", "park"), ("leisure", "nature_reserve")},
    },
    "playground": {
        "overture": {"playground"},
        "osm": {("leisure", "playground")},
    },
    "coffee": {
        "overture": {"coffee_shop", "cafe"},
        "osm": {("amenity", "cafe")},
    },
    "pharmacy": {
        "overture": {"pharmacy", "drugstore"},
        "osm": {("amenity", "pharmacy")},
    },
    "school": {
        "overture": {"elementary_school", "school"},
        "osm": {("amenity", "school")},
    },
    "library": {
        "overture": {"library"},
        "osm": {("amenity", "library")},
    },
    "transit_stop": {
        "overture": {"bus_stop", "bus_station", "train_station"},
        "osm": {("highway", "bus_stop"), ("railway", "station")},
    },
}


def overture_primary(categories) -> str | None:
    """Extract the primary category from an Overture `categories` cell, which may be a
    dict (struct) or a JSON-ish string depending on the reader."""
    if categories is None:
        return None
    if isinstance(categories, dict):
        return categories.get("primary")
    if hasattr(categories, "get"):
        return categories.get("primary")
    return None
