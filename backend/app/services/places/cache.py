"""A provider-neutral result cache that refuses to cache a failure.

The rule this file exists to enforce: **a lookup that failed is not an
answer, and must never be written to the cache.** V1 broke this rule and
recorded a real restaurant as nonexistent for as long as the entry lived.
See `tests/test_places_cache.py` for the history and the proof.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

#: A cached payload. `payload is None` means the provider answered "no such
#: place" -- a real answer, worth keeping. The absence of an entry means we do
#: not know, which is also what a failed lookup must leave behind.
Payload = Optional[Dict[str, Any]]

_UNSAFE = re.compile(r"[^a-z0-9._-]+")


@dataclass(frozen=True)
class CacheEntry:
    """A stored answer and when it was stored."""

    payload: Payload
    cached_at: datetime


class ResultCache:
    """Disk cache of provider answers, keyed by caller-supplied string."""

    def __init__(
        self,
        cache_dir: Path | str,
        *,
        ttl_days: int = 7,
        now: Callable[[], datetime] = datetime.now,
    ):
        self.cache_dir = Path(cache_dir)
        self.ttl_days = ttl_days
        self._now = now

    def _path(self, key: str) -> Path:
        safe = _UNSAFE.sub("_", key.lower().strip())[:60]
        digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]
        return self.cache_dir / f"{safe}_{digest}.json"

    def load(self, key: str) -> Optional[CacheEntry]:
        """Return the stored entry, or None if absent, expired or unreadable."""
        path = self._path(key)
        if not path.exists():
            return None

        try:
            with open(path, "r", encoding="utf-8") as handle:
                raw = json.load(handle)
            # `raw["payload"]`, never `.get("payload")`. A record without that
            # key is one we CANNOT READ, not an answer of "no such place".
            # A leftover V1 file is exactly that shape --
            # {"found": false, "error": null, "cached_at": ...} -- so reading a
            # missing key as None would quietly reintroduce the defect this
            # module exists to prevent.
            payload = raw["payload"]
            cached_at = datetime.fromisoformat(raw["cached_at"])
            # TypeError if cached_at carries an offset and our clock does not.
            age = self._now() - cached_at
        except (OSError, ValueError, KeyError, TypeError) as exc:
            logger.warning("Discarding unreadable cache entry %s: %s", path.name, exc)
            return None

        # Exact, not rounded down to whole days: `(a - b).days > 7` keeps an
        # entry for 7 days and 23:59:59.
        if age.total_seconds() > self.ttl_days * 86400:
            return None

        return CacheEntry(payload=payload, cached_at=cached_at)

    def store(self, key: str, payload: Payload) -> None:
        """Store a provider ANSWER. `None` means a genuine 'no such place'.

        Never call this for a lookup that failed; there is deliberately no
        method that does.
        """
        path = self._path(key)
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(
                    {"payload": payload, "cached_at": self._now().isoformat()},
                    handle,
                    indent=2,
                )
        except OSError as exc:
            logger.warning("Failed to write cache entry %s: %s", path.name, exc)


def lookup_cached(
    cache: ResultCache,
    key: str,
    fetch: Callable[[], Payload],
) -> Payload:
    """Serve `key` from `cache`, calling `fetch` on a miss.

    `fetch` returns the payload, or None for a genuine "no such place". If it
    raises `ProviderUnavailable` the exception propagates and **nothing is
    written**, so the caller learns the lookup failed and the next attempt
    asks again.

    The limit of that guarantee, stated plainly: this protects a failure that
    is *propagated*. A `fetch` that catches its own `ProviderUnavailable` and
    returns None is indistinguishable from an honest miss, and no caching
    layer can tell the difference -- that is the provider's contract to keep,
    which is why `PlacesProvider.nearby_search` says so in its docstring.
    """
    entry = cache.load(key)
    if entry is not None:
        return entry.payload

    payload = fetch()  # ProviderUnavailable propagates, and we cache nothing
    cache.store(key, payload)
    return payload
