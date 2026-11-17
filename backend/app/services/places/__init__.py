"""Premium places search, kept as a module with no provider behind it.

TripAdvisor's Content API was retired and its client removed on 2026-11-17.
The search option stays: the endpoint, the schemas and the frontend panel are
all live, and this package is the seam an alternative API plugs into. Nothing
here talks to a network.

To add a provider: implement `PlacesProvider`, then call
`register_provider(...)` at startup.
"""

from app.services.places.cache import CacheEntry, Payload, ResultCache, lookup_cached
from app.services.places.provider import (
    PlacesProvider,
    ProviderNotConfigured,
    ProviderPlace,
    ProviderUnavailable,
    get_places_provider,
    register_provider,
    require_places_provider,
)

__all__ = [
    "CacheEntry",
    "Payload",
    "PlacesProvider",
    "ProviderNotConfigured",
    "ProviderPlace",
    "ProviderUnavailable",
    "ResultCache",
    "get_places_provider",
    "lookup_cached",
    "register_provider",
    "require_places_provider",
]
