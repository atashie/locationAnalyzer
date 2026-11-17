"""The provider-neutral contract for a places search backend.

No provider is implemented here. TripAdvisor's Content API was retired in
2026 and its client was removed; see
`docs/engineering-notes/reference-tripadvisor-content-api-retired.md` and
`reference-places-provider-needed.md`. This module is the seam a replacement
(Yelp Fusion, Foursquare, Google Places, OSM-only) plugs into.

The one hard rule, learned from the client that was removed: **a transport
failure must raise `ProviderUnavailable`, never return an empty result.**
Returning `[]` or `None` for a failure is what made a dead API look like an
empty neighbourhood.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


class ProviderUnavailable(RuntimeError):
    """The provider could not be reached, refused us, or sent nonsense.

    Distinct from "the provider answered, and the answer was nothing". A
    provider that cannot tell the difference is not finished.
    """


class ProviderNotConfigured(RuntimeError):
    """No places provider is registered, so premium search cannot run."""


@dataclass(frozen=True)
class ProviderPlace:
    """One place, in our own vocabulary rather than any provider's."""

    provider_id: str
    name: str
    lat: float
    lon: float
    address: Optional[str] = None
    rating: Optional[float] = None
    num_reviews: Optional[int] = None
    price_level: Optional[str] = None
    ranking_string: Optional[str] = None
    web_url: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    categories: List[str] = field(default_factory=list)
    photos: List[str] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class PlacesProvider(Protocol):
    """What premium search needs from a provider. Implement all of it.

    `name` identifies the provider in API responses.

    `monthly_usage` / `monthly_limit` report quota. Nothing calls them yet --
    the usage endpoint they were written for belonged to the removed
    TripAdvisor client -- but a metered provider needs somewhere to report
    this, so they stay part of the contract. A provider with no quota reports
    a limit of 0, meaning unlimited.
    """

    name: str

    def nearby_search(
        self,
        lat: float,
        lon: float,
        category: str,
        *,
        limit: int = 10,
        subcategory: Optional[str] = None,
    ) -> List[ProviderPlace]:
        """Places near a point.

        `subcategory` is the optional finer filter the request schema accepts
        (for example "pizza" within "restaurants"). A provider that cannot
        honour it should ignore it rather than fail, but it must accept the
        argument.

        Returns [] **only** when the provider genuinely found nothing.
        Raises `ProviderUnavailable` when the lookup could not be completed.

        That distinction is the whole contract. Returning [] for a failure is
        what made a retired API look like an empty neighbourhood, and no layer
        above can detect it, so it cannot be enforced anywhere but here.
        """
        ...

    def monthly_usage(self) -> int:
        """Calls made this month, or 0 if the provider does not track it."""
        ...

    def monthly_limit(self) -> int:
        """Call ceiling for the month; 0 means unlimited."""
        ...


_provider: Optional[PlacesProvider] = None


def register_provider(provider: Optional[PlacesProvider]) -> None:
    """Install the process-wide provider. Pass None to remove it."""
    global _provider
    _provider = provider


def get_places_provider() -> Optional[PlacesProvider]:
    """The registered provider, or None if premium search has no backend."""
    return _provider


def require_places_provider() -> PlacesProvider:
    """The registered provider, or raise `ProviderNotConfigured`."""
    if _provider is None:
        raise ProviderNotConfigured(
            "No places provider is configured. Premium search is a module "
            "awaiting a provider (Yelp, Foursquare or similar); see "
            "docs/engineering-notes/reference-places-provider-needed.md."
        )
    return _provider
