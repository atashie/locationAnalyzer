"""E3 — real-world accuracy, scored as `failed` or UNVERIFIED. Design §3.

E3 is the one estimand that can **only** fail. 5–8 owner-chosen journeys are a convenience sample, so
no population-rate claim follows from them: with 8 observations and no discrepancy the one-sided 95%
exact bound is **31.2344%**, which is not evidence of anything. The outcome is therefore `FAILED` or
`UNVERIFIED`, and **never "supported"** — a word this module does not contain.

## Why the rule is a disjunction, and why that matters for the tests

> E3 returns `failed` if **either** (i) any single journey's observed time exceeds its reported time
> by more than a factor of **1.5** *and* by more than **5 minutes**, **or** (ii) the median signed
> difference across journeys taken exceeds **25%** of the median reported time.

Limb (i) catches one badly wrong journey; limb (ii) catches a systematic bias too small to trip (i)
on any single journey. They are independent and either suffices.

Plan revision 2's fixture for this was **impossible**, which is the reason the tests here are
structured the way they are: it asserted that a journey 1.6× over but only 3 minutes over does *not*
fail, but for a single journey of reported 5 min and observed 8 min the **median limb fires** — the
median signed difference is 3 min and 25% of the median reported time is 1.25 min. A fixture written
against one limb while the other is live is a fixture that cannot be satisfied by any correct
implementation. So each limb is tested in isolation *and* the complete disjunction is tested on that
exact singleton.

## An unwalked journey is not evidence of success

A planned journey that was not walked leaves the outcome UNVERIFIED and **can never erase a failure**
established by the journeys that were walked. That is a one-way rule: adding `observed_s=None` rows
to a failing set keeps it failing. The medians are taken over **walked** journeys only, because a
missing observation is not a zero difference.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np

from .stats import QUANTILE_METHOD

#: Design §3, limb (i).
RATIO_LIMIT = 1.5
ABSOLUTE_LIMIT_S = 300.0        # five minutes

#: Design §3, limb (ii).
MEDIAN_SHARE_LIMIT = 0.25


class E3Outcome(str, Enum):
    """Two values, deliberately. There is no `SUPPORTED`, and adding one would be a design
    amendment — §3 says the population-rate claim is UNVERIFIED and the published label says so."""

    FAILED = "FAILED"
    UNVERIFIED = "UNVERIFIED"


@dataclass(frozen=True)
class Journey:
    """One owner-chosen journey. `observed_s = None` means **planned but not walked**.

    `reported_s` is what the product said; both are seconds. A journey is identified so a failure can
    be pointed at rather than merely counted.
    """

    label: str
    reported_s: float
    observed_s: float | None = None

    def __post_init__(self) -> None:
        if not np.isfinite(self.reported_s) or self.reported_s <= 0:
            raise ValueError(f"{self.label}: reported_s must be positive and finite")
        if self.observed_s is not None and (not np.isfinite(self.observed_s)
                                            or self.observed_s < 0):
            raise ValueError(f"{self.label}: observed_s must be non-negative and finite, or None")

    @property
    def walked(self) -> bool:
        return self.observed_s is not None

    @property
    def difference_s(self) -> float | None:
        """Signed, observed minus reported. Positive means the journey took longer than promised,
        which is the direction that can fail."""
        return None if self.observed_s is None else self.observed_s - self.reported_s

    @property
    def ratio(self) -> float | None:
        return None if self.observed_s is None else self.observed_s / self.reported_s

    @property
    def trips_single_journey_limb(self) -> bool:
        """Limb (i): **both** conditions, not either. A 1.6x overrun of a 5-minute journey is 3
        minutes and does not trip this limb on its own."""
        if self.observed_s is None:
            return False
        return (self.ratio > RATIO_LIMIT) and (self.difference_s > ABSOLUTE_LIMIT_S)


@dataclass(frozen=True)
class E3Result:
    outcome: E3Outcome
    reasons: tuple[str, ...]            # why it failed; empty when UNVERIFIED
    walked: int
    planned: int
    median_difference_s: float | None
    median_reported_s: float | None
    median_limit_s: float | None        # 25% of the median reported time
    offending: tuple[str, ...]          # journeys tripping limb (i), by label

    @property
    def failed(self) -> bool:
        return self.outcome is E3Outcome.FAILED


def score_e3(journeys) -> E3Result:
    """Design §3's disjunction. Returns `FAILED` or `UNVERIFIED`, never anything else.

    With no walked journey the outcome is UNVERIFIED and both medians are `None` — not zero, which
    would be a claim that the product was accurate.
    """
    journeys = tuple(journeys)
    labels = [j.label for j in journeys]
    if len(set(labels)) != len(labels):
        raise ValueError("journeys must have distinct labels, so a failure can be pointed at")

    walked = [j for j in journeys if j.walked]
    reasons: list[str] = []

    offending = tuple(j.label for j in walked if j.trips_single_journey_limb)
    for j in walked:
        if j.trips_single_journey_limb:
            reasons.append(
                f"{j.label}: observed {j.observed_s:.0f} s against {j.reported_s:.0f} s reported — "
                f"{j.ratio:.2f}x and {j.difference_s / 60.0:.1f} min over, past both "
                f"{RATIO_LIMIT}x and {ABSOLUTE_LIMIT_S / 60.0:.0f} min"
            )

    median_difference = median_reported = median_limit = None
    if walked:
        median_difference = float(np.quantile([j.difference_s for j in walked], 0.5,
                                              method=QUANTILE_METHOD))
        median_reported = float(np.quantile([j.reported_s for j in walked], 0.5,
                                            method=QUANTILE_METHOD))
        median_limit = MEDIAN_SHARE_LIMIT * median_reported
        if median_difference > median_limit:
            reasons.append(
                f"median signed difference {median_difference / 60.0:.2f} min exceeds "
                f"{MEDIAN_SHARE_LIMIT:.0%} of the median reported time "
                f"({median_limit / 60.0:.2f} min)"
            )

    return E3Result(
        outcome=E3Outcome.FAILED if reasons else E3Outcome.UNVERIFIED,
        reasons=tuple(reasons),
        walked=len(walked),
        planned=len(journeys) - len(walked),
        median_difference_s=median_difference,
        median_reported_s=median_reported,
        median_limit_s=median_limit,
        offending=offending,
    )
