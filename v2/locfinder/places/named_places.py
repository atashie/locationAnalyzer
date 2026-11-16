"""Specific places as layer targets — "drive to work", "drive to the airport".

A household's criteria are not all categories. Two of the six the owner asked for on 2026-11-16
are single destinations: a place of work and an airport. The layer builder already accepts an
arbitrary `dest_idx`, so nothing about the routing needed to change; the only thing missing was a
way to *name* one of these so it can be a layer like any other.

**The coordinates live here, in git, with their provenance.** An artifact nobody can rebuild is one
cleanup away from unrecoverable, and a coordinate typed from memory is exactly the kind of invented
precision this project has shipped before (ledger instance 52). Every entry says where its points
came from, and `points` is a list because "the airport" is two terminals, not one door.

Points are `(lon, lat)` in WGS84, matching the Overture places frame they sit beside.
"""
from __future__ import annotations

import geopandas as gpd
import shapely

#: Slug -> one named destination. The slug is the layer's `category` on the command line and in
#: every filename, so it must be filename-safe: lowercase, hyphens, no colons or commas.
NAMED_PLACES: dict[str, dict] = {
    "duke-hospital": {
        "label": "Duke University Hospital",
        "points": [(-78.93735, 36.00702)],
        "source": (
            "OSM way 305879102, `amenity=hospital`, 2301 Erwin Road, Durham. Centroid read from "
            "the OSM Nominatim search API on 2026-11-16. Overture's records for this campus are "
            "per-department (`Duke Pediatric Eye Center`, `Duke Central Tower`), so none of them "
            "is the hospital."
        ),
    },
    "rdu-airport": {
        "label": "RDU airport",
        "points": [(-78.79041, 35.87423), (-78.78555, 35.87977)],
        "source": (
            "Overture 2026-10-21.0: `RDU Terminal 1` (`airport_terminal`) and `Raleigh-Durham "
            "International Airport` (`airport`), the two terminal buildings. The OSM aerodrome "
            "centroid (way 209063360, 35.88036/-78.78724) is deliberately NOT used: it lies "
            "inside the airfield, where there is no road a household drives on. Overture also "
            "holds `JFK Airport New York` and `Fort Lauderdale Int Airport` at this location, "
            "which is why these points are pinned here rather than matched by name at build time."
        ),
    },
}


def is_named_place(target: str) -> bool:
    """Whether this layer target names a specific place rather than a wedge category."""
    return target in NAMED_PLACES


def named_place(target: str) -> dict:
    """The registry entry, or a message naming every slug there is."""
    try:
        return NAMED_PLACES[target]
    except KeyError:
        raise KeyError(
            f"{target!r} is not a named place; known slugs are {sorted(NAMED_PLACES)}") from None


def select_named(target: str, crs):
    """The named place's points as a frame shaped like `select_overture`'s result.

    Same columns the builders read -- `geometry` and `names` -- so `g1_own_graph_layer` and
    `s2_building_weighted_coverage` need no branch of their own beyond choosing the selector.
    `names` carries the registry's label rather than a per-point name: the two RDU rows are one
    destination with two doors, and labelling them separately would invite a consumer to present
    "RDU Terminal 1" as the answer when the household asked for the airport.
    """
    entry = named_place(target)
    pts = [shapely.Point(lon, lat) for lon, lat in entry["points"]]
    gdf = gpd.GeoDataFrame(
        {"names": [{"primary": entry["label"]} for _ in pts]},
        geometry=pts, crs="EPSG:4326")
    return gdf.to_crs(crs) if crs is not None else gdf
