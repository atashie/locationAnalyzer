"""A failed lookup must never be cached as a negative result.

This is the defect that shipped in V1's TripAdvisor client. `_make_request`
caught `httpx.HTTPStatusError`, logged a warning and returned `None`;
`search_location` passed the `None` through; `enrich_poi` then wrote
`{"found": false, "error": null}` to disk. A retired API and a genuine "no
such place" were indistinguishable, so the cache filled up with the claim
that real places do not exist.

The real cache held exactly one entry when this was found, and it was that
lie: `gonza_tacos_y_tequila_35.994_-78.899.json` recorded
`{"found": false, "error": null}` for a restaurant that plainly exists.

These tests pin the rule down so the next provider cannot inherit the bug.
"""

from datetime import datetime

import pytest

from app.services.places import ProviderUnavailable, ResultCache, lookup_cached


class Clock:
    """An injected clock, so expiry can be tested without a test-only method."""

    def __init__(self, start: datetime):
        self.now = start

    def __call__(self) -> datetime:
        return self.now

    def advance_days(self, days: int) -> None:
        self.now = self.now.replace(day=self.now.day + days)


@pytest.fixture()
def clock():
    return Clock(datetime(2026, 11, 1, 12, 0, 0))


@pytest.fixture()
def cache(tmp_path, clock):
    return ResultCache(tmp_path / "places", ttl_days=7, now=clock)


def test_a_successful_lookup_is_cached(cache):
    calls = []

    def fetch():
        calls.append(1)
        return {"name": "Gonza Tacos y Tequila", "rating": 4.5}

    first = lookup_cached(cache, "gonza", fetch)
    second = lookup_cached(cache, "gonza", fetch)

    assert first == {"name": "Gonza Tacos y Tequila", "rating": 4.5}
    assert second == first
    assert len(calls) == 1, "the second lookup should have been served from cache"


def test_a_genuine_miss_is_cached(cache):
    """The provider answered, and its answer was 'no such place'. Worth keeping."""
    calls = []

    def fetch():
        calls.append(1)
        return None

    assert lookup_cached(cache, "no-such-shop", fetch) is None
    assert lookup_cached(cache, "no-such-shop", fetch) is None
    assert len(calls) == 1, "a genuine miss should be cached, not re-asked"


def test_a_provider_failure_is_not_cached_and_is_raised(cache):
    """THE FIX. A failure is not an answer, so it must not be stored as one."""

    def fetch():
        raise ProviderUnavailable("HTTP 403: explicit deny in an identity-based policy")

    with pytest.raises(ProviderUnavailable) as excinfo:
        lookup_cached(cache, "gonza", fetch)

    assert "403" in str(excinfo.value)
    assert cache.load("gonza") is None, "a failed lookup must leave the cache untouched"


def test_a_failure_does_not_poison_a_later_success(cache):
    """The regression that mattered: the lie outlived the outage."""

    def failing():
        raise ProviderUnavailable("provider down")

    def working():
        return {"name": "Gonza Tacos y Tequila"}

    with pytest.raises(ProviderUnavailable):
        lookup_cached(cache, "gonza", failing)

    assert lookup_cached(cache, "gonza", working) == {"name": "Gonza Tacos y Tequila"}


def test_an_expired_entry_is_ignored(cache, clock):
    cache.store("gonza", {"name": "old"})
    clock.advance_days(8)

    assert cache.load("gonza") is None


def test_an_unexpired_entry_is_kept(cache, clock):
    cache.store("gonza", {"name": "fresh"})
    clock.advance_days(6)

    entry = cache.load("gonza")
    assert entry is not None
    assert entry.payload == {"name": "fresh"}


def test_a_corrupt_cache_file_is_a_miss_not_a_crash(cache, tmp_path):
    cache.store("gonza", {"name": "fine"})
    path = next((tmp_path / "places").glob("*.json"))
    path.write_text("{ this is not json", encoding="utf-8")

    assert cache.load("gonza") is None
