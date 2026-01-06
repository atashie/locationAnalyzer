"""Geocoding service for location validation."""

import logging
from functools import lru_cache
from typing import Any, Dict, List

import osmnx as ox

logger = logging.getLogger(__name__)

# Common US state suffixes to try if location not found
US_SUFFIXES: List[str] = [", USA", ", United States", ", US"]


@lru_cache(maxsize=1000)
def validate_location(location_string: str, location_type: str = "general") -> Dict[str, Any]:
    """
    Validate and geocode a location with helpful error messages.

    Args:
        location_string: User input location
        location_type: 'city' or 'address' for specific formatting hints

    Returns:
        dict with 'valid', 'lat', 'lon', 'display_name', 'error_message'
    """
    if not location_string or not location_string.strip():
        return {
            "valid": False,
            "lat": None,
            "lon": None,
            "display_name": None,
            "error_message": "Location cannot be empty",
        }

    location_string = location_string.strip()

    # Attempt 1: Direct geocoding
    result = _try_geocode(location_string)
    if result["valid"]:
        return result

    # Attempt 2: Try with common suffixes if no comma in original
    if "," not in location_string:
        for suffix in US_SUFFIXES:
            result = _try_geocode(location_string + suffix)
            if result["valid"]:
                result["error_message"] = f"Found as: {location_string + suffix}"
                return result

    # All attempts failed
    if location_type == "city":
        error_msg = (
            f"Could not find '{location_string}'. "
            "Try format: 'City, State' or 'City, Country' (e.g., 'Durham, NC')"
        )
    else:
        error_msg = (
            f"Could not find '{location_string}'. "
            "Try being more specific: add city, state, or ZIP code"
        )

    return {
        "valid": False,
        "lat": None,
        "lon": None,
        "display_name": None,
        "error_message": error_msg,
    }


def _try_geocode(location_string: str) -> Dict[str, Any]:
    """Attempt to geocode a location string."""
    try:
        result = ox.geocode_to_gdf(location_string)
        lat = result.geometry.iloc[0].centroid.y
        lon = result.geometry.iloc[0].centroid.x
        display_name = (
            result["display_name"].iloc[0]
            if "display_name" in result.columns
            else location_string
        )

        return {
            "valid": True,
            "lat": lat,
            "lon": lon,
            "display_name": display_name,
            "error_message": None,
        }
    except Exception as e:
        logger.debug(f"Geocoding failed for '{location_string}': {e}")
        return {
            "valid": False,
            "lat": None,
            "lon": None,
            "display_name": None,
            "error_message": str(e),
        }


def clear_geocode_cache() -> None:
    """Clear the geocoding cache."""
    validate_location.cache_clear()
