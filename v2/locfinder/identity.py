"""What identifies a surface. Phase 1 stage S0.4.

A surface is not identified by `(mode, category)`. Two transit surfaces for the same category are
different answers if they were built for a different service date, a different deadline, or a
different search window — and a cached drive surface for the same anchor is a different answer if
the road extract, the speed profile or the grid changed under it. Getting this wrong shows up as a
cache that serves last month's timetable, or a manifest that cannot say what it published.

These fields become manifest entries (S4.2) and cache-key components (S5.3). They are fixed here,
before any of that is built, because A6's freshness gate cannot be written against an unspecified
"requested service date" (Codex pass-7 H8).

## Transit semantics, decided

**Timezone.** `America/New_York`, which is what all seven adopted Triangle feeds declare
(`data/gtfs_extracted/feeds_report.json`). A deadline is a **local wall-clock** time, because that
is what a household means by "at the office by 08:45", and local wall clock is what GTFS
`stop_times` are expressed in.

**Service date.** A local calendar date, not an instant. The reference weekday is **2026-11-10**, a
Tuesday, already used by the transit spike (`spikes/transit_compare.py:45`).

**Overnight service.** GTFS `stop_times` may exceed `24:00:00`, so a journey arriving at 08:45 can
belong to the *previous* service day. Any router querying a deadline must have the service day
before `service_date` loaded as well. This is a statement about the build, enforced in S4.3.

**DST.** A local wall-clock deadline is not always a unique instant. US transitions occur at 02:00
local: in autumn the hour 01:00-02:00 occurs twice, in spring 02:00-03:00 does not occur at all. An
08:45 deadline is unaffected on every date, but the code will accept any deadline, so the rule is
stated and enforced rather than left to the next person: a deadline that is **ambiguous or
nonexistent** on its service date is refused. 2026-11-01 and 2027-03-14 are the fixtures.

**Duration semantics.** A cell's value is the **total journey time**: the walk from the cell to the
first stop, waiting there, riding, transfers, and the final walk to the destination — ending at the
deadline. Waiting is included, so a cell whose only bus leaves 40 minutes before the deadline reads
over 40 minutes even if the ride is 10. That is the honest number for "when must I leave", and the
alternative presentation, the latest feasible departure time, is recoverable exactly as
`deadline - duration`, so storing duration loses nothing.

**Window.** `window_s` is the longest journey the search considers, and is the surface's horizon:
beyond it, cells are `BEYOND_HORIZON` and nothing stronger (`status.py`). MOTIS `one-to-all` takes
it as `maxTravelTime`.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

#: Every adopted Triangle feed declares this; a feed that does not must be converted or rejected.
METRO_TZ = "America/New_York"

#: The reference weekday for the Triangle transit build. A Tuesday, in EST (2026 DST ended 11-01).
REFERENCE_SERVICE_DATE = date(2026, 11, 10)


@dataclass(frozen=True)
class TransitQuery:
    """The part of a surface's identity that only transit has."""

    service_date: date
    deadline_local: time
    window_s: float
    timezone: str = METRO_TZ

    def __post_init__(self) -> None:
        # `not (x > 0)` rather than `x <= 0`: NaN fails every comparison, so the old check let
        # both NaN and +inf through (Codex pass-8 M3).
        if not (self.window_s > 0) or not math.isfinite(self.window_s):
            raise ValueError("window_s must be positive and finite")
        self.validate_wall_clock()

    def validate_wall_clock(self) -> datetime:
        """Resolve the deadline to a single instant, or refuse.

        Both failure modes make the two PEP 495 folds disagree about the UTC offset, so the folds
        alone cannot tell them apart. The round trip does: a **nonexistent** local time comes back
        as a different local time after normalising through UTC, while an **ambiguous** one comes
        back unchanged and merely has two valid offsets. Check nonexistence first.
        """
        tz = ZoneInfo(self.timezone)
        utc = ZoneInfo("UTC")
        naive = datetime.combine(self.service_date, self.deadline_local)
        first = naive.replace(tzinfo=tz, fold=0)
        second = naive.replace(tzinfo=tz, fold=1)
        if first.astimezone(utc).astimezone(tz).replace(tzinfo=None) != naive:
            raise ValueError(
                f"{naive} does not exist in {self.timezone} (the clock skips this hour); "
                "choose a deadline outside the DST transition"
            )
        if first.utcoffset() != second.utcoffset():
            raise ValueError(
                f"{naive} is ambiguous in {self.timezone} (the clock repeats this hour); "
                "choose a deadline outside the DST transition"
            )
        return first

    @property
    def deadline_utc(self) -> datetime:
        return self.validate_wall_clock().astimezone(ZoneInfo("UTC"))

    def fields(self) -> dict:
        d = asdict(self)
        d["service_date"] = self.service_date.isoformat()
        d["deadline_local"] = self.deadline_local.isoformat()
        # The service day before is loaded too, because an overnight trip can serve this deadline.
        d["requires_prior_service_day"] = True
        return d


@dataclass(frozen=True)
class SurfaceKey:
    """Everything that makes one published or cached surface a different answer from another.

    `transit` is `None` for walk, bike and drive. `direction` is `"arrival"` throughout this
    product — the whole routing model is to-destination (see `arrival.py`) — and is carried
    explicitly so a future departure-time surface cannot silently reuse an arrival cache.

    A coordinate alone is **not** an identity (Codex pass-7 H6): rounding an anchor can move it
    across a divided road or a barrier, so the rounding applied is part of the key and S5.3 must
    bound how far it can move a point.

    `grid_version` and `profile_version` should come from `profile.grid_version()` and
    `profile.profile_version()`, which **derive** them from the grid geometry and the model
    constants. A hand-typed version string does not change when the thing it describes changes, and
    the failure mode is a cache that serves an answer built under different rules.

    `max_access_m` and `poi_snap_max_m` are per-build choices that move values — the first decides
    which cells are `OFF_NETWORK`, the second which destinations exist at all — so they are carried
    explicitly rather than hidden in the profile digest.
    """

    metro: str
    mode: str
    engine: str
    target: str
    aggregation: str
    horizon_s: float
    grid_version: str
    source_release: str
    profile_version: str
    code_version: str
    max_access_m: float
    poi_snap_max_m: float
    direction: str = "arrival"
    anchor_lonlat: tuple[float, float] | None = None
    anchor_round_dp: int | None = None
    transit: TransitQuery | None = None

    def __post_init__(self) -> None:
        if self.direction != "arrival":
            raise ValueError("only arrival surfaces exist; a departure model needs its own review")
        if (self.transit is None) != (self.mode != "transit"):
            raise ValueError("mode 'transit' requires a TransitQuery, and nothing else may carry one")
        if not (self.horizon_s > 0) or not math.isfinite(self.horizon_s):
            raise ValueError("horizon_s must be positive and finite")
        if self.transit is not None and self.transit.window_s != self.horizon_s:
            # The contract says `window_s` *is* the surface horizon. Two numbers mean two
            # definitions of "past the horizon", and `snap.py` requires one (pass-8 M3).
            raise ValueError(
                f"transit window {self.transit.window_s} s and horizon {self.horizon_s} s must be "
                "the same number: the search bound and the published horizon are one thing"
            )
        if (self.anchor_lonlat is None) != (self.anchor_round_dp is None):
            raise ValueError("an anchor and its rounding are recorded together or not at all")
        # Convention is not enforcement (Codex pass-8 H3). A version must look derived -- the
        # prefixes `profile.profile_version()` and `profile.grid_version()` produce -- so a
        # hand-typed "speeds-v0" cannot stand in for a digest of the constants it names.
        for field, prefix in (("profile_version", "speeds-v"), ("grid_version", "grid-v")):
            value = getattr(self, field)
            if not (value.startswith(prefix) and "+" in value):
                raise ValueError(
                    f"{field}={value!r} is not a derived version; use locfinder.profile."
                    f"{field}() so it changes when the thing it names changes"
                )

    def fields(self) -> dict:
        """Flat, JSON-safe, ordered — the manifest entry and the hashed cache key."""
        d = {k: v for k, v in asdict(self).items() if k != "transit"}
        if self.anchor_lonlat is not None:
            dp = self.anchor_round_dp
            d["anchor_lonlat"] = [round(float(c), dp) for c in self.anchor_lonlat]
        d["transit"] = self.transit.fields() if self.transit else None
        return dict(sorted(d.items()))

    def digest(self) -> str:
        """Stable 16-hex cache key. Stable across processes: `hash()` is not."""
        blob = json.dumps(self.fields(), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.blake2b(blob, digest_size=8).hexdigest()
