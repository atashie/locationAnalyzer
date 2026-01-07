"""Valhalla isochrone service with fallback to buffer approximation."""

import logging
from typing import Optional, Tuple

import httpx
from shapely.geometry import Polygon, shape

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Map our travel modes to Valhalla costing models
COSTING_MAP = {
    "walk": "pedestrian",
    "bike": "bicycle",
    "drive": "auto",
}


def get_isochrone_sync(
    lat: float,
    lon: float,
    minutes: int,
    travel_mode: str,
    valhalla_url: Optional[str] = None,
) -> Tuple[Optional[Polygon], bool]:
    """
    Get isochrone polygon from Valhalla.

    Args:
        lat: Latitude of center point
        lon: Longitude of center point
        minutes: Travel time in minutes
        travel_mode: 'walk', 'bike', or 'drive'
        valhalla_url: Valhalla API base URL

    Returns:
        Tuple of (polygon, used_valhalla)
        - polygon: Shapely Polygon in EPSG:4326, or None if failed
        - used_valhalla: True if Valhalla succeeded, False if fallback needed
    """
    # Check if Valhalla is enabled
    if not settings.valhalla_enabled:
        logger.debug("Valhalla disabled in settings")
        return None, False

    url = valhalla_url or settings.valhalla_url
    costing = COSTING_MAP.get(travel_mode, "auto")

    request_body = {
        "locations": [{"lat": lat, "lon": lon}],
        "costing": costing,
        "contours": [{"time": minutes}],
        "polygons": True,
        "generalize": 50,  # Simplify geometry (meters)
    }

    try:
        with httpx.Client(timeout=settings.valhalla_timeout) as client:
            response = client.post(
                f"{url}/isochrone",
                json=request_body,
            )
            response.raise_for_status()

            data = response.json()

            if data.get("features"):
                geom = shape(data["features"][0]["geometry"])

                if geom.geom_type == "Polygon":
                    logger.info(
                        f"Valhalla isochrone: {travel_mode} {minutes}min at ({lat:.4f}, {lon:.4f})"
                    )
                    return geom, True
                elif geom.geom_type == "MultiPolygon":
                    # Return largest polygon if MultiPolygon
                    largest = max(geom.geoms, key=lambda p: p.area)
                    logger.info(
                        f"Valhalla isochrone (MultiPolygon): {travel_mode} {minutes}min at ({lat:.4f}, {lon:.4f})"
                    )
                    return largest, True

            logger.warning("Valhalla returned empty isochrone")
            return None, False

    except httpx.TimeoutException:
        logger.warning(
            f"Valhalla timeout for {travel_mode} {minutes}min at ({lat:.4f}, {lon:.4f})"
        )
        return None, False
    except httpx.HTTPStatusError as e:
        logger.warning(f"Valhalla HTTP error: {e.response.status_code}")
        return None, False
    except Exception as e:
        logger.warning(f"Valhalla error: {e}")
        return None, False
