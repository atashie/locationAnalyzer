"""TripAdvisor API integration service."""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


class TripAdvisorClient:
    """Client for TripAdvisor Content API with caching and rate limiting."""

    BASE_URL = "https://api.content.tripadvisor.com/api/v1"

    # Map our POI types to TripAdvisor categories
    CATEGORY_MAP = {
        "Restaurant": "restaurants",
        "Italian Restaurant": "restaurants",
        "Coffee Shop": "restaurants",
        "Bar": "restaurants",
        "Cocktail Bar": "restaurants",
        "Hotel": "hotels",
        "Museum": "attractions",
        "Park": "attractions",
        "Playground": "attractions",
        "Swimming Pool": "attractions",
    }

    def __init__(self):
        self.api_key = settings.tripadvisor_api_key
        self.enabled = settings.tripadvisor_enabled and bool(self.api_key)
        self.monthly_limit = settings.tripadvisor_monthly_limit
        self.cache_dir = Path(settings.tripadvisor_cache_dir)
        self.timeout = settings.tripadvisor_timeout

        # Ensure cache directory exists
        if self.enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_usage_file(self) -> Path:
        """Get path to monthly usage tracking file."""
        return self.cache_dir / "monthly_usage.json"

    def _get_current_month(self) -> str:
        """Get current month as YYYY-MM string."""
        return datetime.now().strftime("%Y-%m")

    def get_monthly_usage(self) -> int:
        """Get API call count for current month."""
        usage_file = self._get_usage_file()
        if not usage_file.exists():
            return 0

        try:
            with open(usage_file, "r") as f:
                data = json.load(f)
            return data.get(self._get_current_month(), 0)
        except Exception:
            return 0

    def _increment_usage(self, count: int = 1):
        """Increment API call count for current month."""
        usage_file = self._get_usage_file()
        month = self._get_current_month()

        try:
            if usage_file.exists():
                with open(usage_file, "r") as f:
                    data = json.load(f)
            else:
                data = {}

            data[month] = data.get(month, 0) + count

            with open(usage_file, "w") as f:
                json.dump(data, f)
        except Exception as e:
            logger.warning(f"Failed to update usage count: {e}")

    def is_limit_reached(self) -> bool:
        """Check if monthly API limit has been reached."""
        return self.get_monthly_usage() >= self.monthly_limit

    def _get_cache_key(self, name: str, lat: float, lon: float) -> str:
        """Generate cache key for a POI."""
        # Round coordinates to reduce cache misses for nearby searches
        lat_rounded = round(lat, 4)
        lon_rounded = round(lon, 4)
        # Normalize name for caching
        name_normalized = name.lower().strip().replace(" ", "_")[:50]
        return f"{name_normalized}_{lat_rounded}_{lon_rounded}"

    def _get_cache_file(self, cache_key: str) -> Path:
        """Get path to cache file for a POI."""
        return self.cache_dir / f"{cache_key}.json"

    def _load_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Load cached enrichment data if available and not expired."""
        cache_file = self._get_cache_file(cache_key)
        if not cache_file.exists():
            return None

        try:
            with open(cache_file, "r") as f:
                data = json.load(f)

            # Check cache expiry (7 days for found, 7 days for not found)
            cached_at = datetime.fromisoformat(data.get("cached_at", "2000-01-01"))
            age_days = (datetime.now() - cached_at).days

            if age_days > 7:
                return None

            logger.debug(f"Cache hit for {cache_key}")
            return data
        except Exception as e:
            logger.warning(f"Failed to load cache for {cache_key}: {e}")
            return None

    def _save_to_cache(self, cache_key: str, data: Dict[str, Any]):
        """Save enrichment data to cache."""
        cache_file = self._get_cache_file(cache_key)
        try:
            data["cached_at"] = datetime.now().isoformat()
            with open(cache_file, "w") as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Cached data for {cache_key}")
        except Exception as e:
            logger.warning(f"Failed to save cache for {cache_key}: {e}")

    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Make API request to TripAdvisor."""
        params["key"] = self.api_key
        url = f"{self.BASE_URL}{endpoint}"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                self._increment_usage()
                return response.json()
        except httpx.TimeoutException:
            logger.warning(f"TripAdvisor API timeout for {endpoint}")
            return None
        except httpx.HTTPStatusError as e:
            logger.warning(f"TripAdvisor API error: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"TripAdvisor API request failed: {e}")
            return None

    def search_location(
        self, name: str, lat: float, lon: float, category: str = "restaurants"
    ) -> Optional[Dict[str, Any]]:
        """
        Search for a TripAdvisor location matching the given name and coordinates.

        Returns the best matching location or None if no match found.
        """
        params = {
            "searchQuery": name,
            "latLong": f"{lat},{lon}",
            "category": category,
            "language": "en",
        }

        result = self._make_request("/location/search", params)
        if not result or "data" not in result or not result["data"]:
            return None

        # Return the first (best) match
        return result["data"][0]

    def get_location_details(self, location_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information for a TripAdvisor location."""
        params = {
            "language": "en",
            "currency": "USD",
        }

        return self._make_request(f"/location/{location_id}/details", params)

    def get_location_photos(self, location_id: str, limit: int = 3) -> List[str]:
        """Get photo URLs for a TripAdvisor location."""
        params = {
            "language": "en",
            "limit": limit,
        }

        result = self._make_request(f"/location/{location_id}/photos", params)
        if not result or "data" not in result:
            return []

        photos = []
        for photo in result["data"][:limit]:
            # Get the largest available image
            images = photo.get("images", {})
            if "original" in images:
                photos.append(images["original"]["url"])
            elif "large" in images:
                photos.append(images["large"]["url"])
            elif "medium" in images:
                photos.append(images["medium"]["url"])

        return photos

    def enrich_poi(
        self, name: str, lat: float, lon: float, poi_type: str = "Restaurant"
    ) -> Dict[str, Any]:
        """
        Enrich a POI with TripAdvisor data.

        Returns a dictionary with enrichment data or error information.
        """
        # Check if enabled
        if not self.enabled:
            return {
                "found": False,
                "error": "TripAdvisor integration not configured",
            }

        # Check monthly limit
        if self.is_limit_reached():
            return {
                "found": False,
                "error": "Monthly API limit reached",
            }

        # Check cache first
        cache_key = self._get_cache_key(name, lat, lon)
        cached = self._load_from_cache(cache_key)
        if cached is not None:
            # Remove internal cache metadata from response
            result = {k: v for k, v in cached.items() if k != "cached_at"}
            return result

        # Map POI type to TripAdvisor category
        category = self.CATEGORY_MAP.get(poi_type, "restaurants")

        # Search for location
        location = self.search_location(name, lat, lon, category)
        if not location:
            # Cache the "not found" result to avoid repeated searches
            not_found = {"found": False, "error": None}
            self._save_to_cache(cache_key, not_found)
            return not_found

        location_id = location.get("location_id")
        if not location_id:
            not_found = {"found": False, "error": None}
            self._save_to_cache(cache_key, not_found)
            return not_found

        # Get detailed information
        details = self.get_location_details(location_id)

        # Get photos
        photos = self.get_location_photos(location_id)

        # Build enrichment result
        result = {
            "found": True,
            "location_id": location_id,
            "rating": None,
            "num_reviews": None,
            "price_level": None,
            "ranking_string": None,
            "tripadvisor_url": None,
            "photos": photos,
            "cuisine": None,
            "error": None,
        }

        if details:
            result["rating"] = float(details.get("rating")) if details.get("rating") else None
            result["num_reviews"] = (
                int(details.get("num_reviews")) if details.get("num_reviews") else None
            )
            result["price_level"] = details.get("price_level")
            result["ranking_string"] = details.get("ranking_data", {}).get("ranking_string")
            result["tripadvisor_url"] = details.get("web_url")

            # Extract cuisine types
            cuisine = details.get("cuisine", [])
            if cuisine:
                result["cuisine"] = [c.get("localized_name") for c in cuisine if c.get("localized_name")]

        # Cache the result
        self._save_to_cache(cache_key, result)

        logger.info(f"Enriched POI '{name}' with TripAdvisor data (location_id: {location_id})")
        return result


# Singleton instance
_client: Optional[TripAdvisorClient] = None


def get_tripadvisor_client() -> TripAdvisorClient:
    """Get the TripAdvisor client singleton."""
    global _client
    if _client is None:
        _client = TripAdvisorClient()
    return _client


def enrich_poi_with_tripadvisor(
    name: str, lat: float, lon: float, poi_type: str = "Restaurant"
) -> Dict[str, Any]:
    """
    Convenience function to enrich a POI with TripAdvisor data.

    Args:
        name: POI name
        lat: Latitude
        lon: Longitude
        poi_type: POI type (e.g., "Restaurant", "Hotel")

    Returns:
        Dictionary with enrichment data
    """
    client = get_tripadvisor_client()
    return client.enrich_poi(name, lat, lon, poi_type)
