"""Constants and POI type definitions."""

from typing import Dict

# POI types mapped to OSM tags
POI_TYPES: Dict[str, Dict[str, str]] = {
    "Grocery Store": {"shop": "supermarket"},
    "School": {"amenity": "school"},
    "Elementary School": {"amenity": "school"},
    "Park": {"leisure": "park"},
    "Restaurant": {"amenity": "restaurant"},
    "Italian Restaurant": {"amenity": "restaurant", "cuisine": "italian"},
    "Coffee Shop": {"amenity": "cafe"},
    "Hospital": {"amenity": "hospital"},
    "Pharmacy": {"amenity": "pharmacy"},
    "Library": {"amenity": "library"},
    "Gym/Fitness": {"leisure": "fitness_centre"},
    "Bus Stop": {"highway": "bus_stop"},
    "Subway Station": {"station": "subway"},
    "Bank": {"amenity": "bank"},
    "Bar": {"amenity": "bar"},
    "Cocktail Bar": {"amenity": "bar"},
    "Gas Station": {"amenity": "fuel"},
    "Shopping Mall": {"shop": "mall"},
    "Post Office": {"amenity": "post_office"},
    "Fire Station": {"amenity": "fire_station"},
    "Police Station": {"amenity": "police"},
    "Playground": {"leisure": "playground"},
    "Swimming Pool": {"leisure": "swimming_pool"},
    "Museum": {"tourism": "museum"},
    "Hotel": {"tourism": "hotel"},
}

# Travel speeds in miles per hour
TRAVEL_SPEEDS: Dict[str, float] = {
    "walk": 3.0,    # ~20 min/mile
    "bike": 12.0,   # ~5 min/mile
    "drive": 30.0,  # Urban average
}

# Buffer adjustments for non-straight-line travel
BUFFER_ADJUSTMENTS: Dict[str, float] = {
    "walk": 1.2,    # Walking paths deviate ~20%
    "bike": 1.3,    # Cycling paths deviate ~30%
    "drive": 1.5,   # Roads deviate ~50%
}

# Maximum distance to expand query area beyond current search polygon
# This ensures we capture POIs just outside the boundary that could still
# serve points within the boundary. Capped to prevent massive OSM queries.
MAX_QUERY_EXPANSION_MILES: float = 5.0
