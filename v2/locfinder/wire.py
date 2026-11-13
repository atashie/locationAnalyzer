"""The published wire format — S3.5's encoding, and the decode algebra that goes with it.

**Why this module exists.** `docs/plans/layer-contract.md` is explicit: the integers in
`status.Reason` are in-memory array codes, **not** a wire format, and "must never be written into a
raster". S3.5 assigns the wire codes, and does it in a versioned format because minute values
251–254 are real answers in artifacts already on disk and may not be reinterpreted as sentinels.

**What a browser needs, and what one uint8 plane cannot give it.** `status.evaluate` decides a
cell from four things: the reason, the seconds, a lower bound on the seconds, and the layer's
horizon. The format on disk today carries one of them — minutes, with a single `NODATA` for every
missing value — so the browser cannot distinguish

* a cell with **no road within 200 m**, whose answer is genuinely unknown, from
* a cell **past the built horizon**, which is a *known* failure at any threshold below it, from
* a cell **off network but provably too far**, whose lower bound already settles the question.

Measured on the published Triangle walk layer, 330,502 cells: 57,541 `OFF_NETWORK` and 16,209
`BEYOND_HORIZON`. At a ten-minute threshold **18,648 of them are known failures** — every
`BEYOND_HORIZON` cell plus 2,439 `OFF_NETWORK` cells whose bound exceeds ten minutes — and the
current format cannot say so.

## The format: `published-v2`

Two uint8 planes of identical shape per layer.

| plane | meaning |
|---|---|
| `value` | where `status` is `OK`, the travel time in whole minutes, **rounded up**. Where `status` is `OFF_NETWORK`, `BEYOND_HORIZON` or `NO_PATH`, a **lower bound** on the travel time in whole minutes, rounded up. Otherwise meaningless, and written as `VALUE_NONE` |
| `status` | one wire code, below |

The wire codes are assigned here and are **not** `Reason`'s values, even where they happen to
coincide. `LAYER_UNKNOWN` deliberately merges the three layer-wide reasons, which differ in cause
but not in anything a decoder may do about them; the cause is named in the manifest, where it can
be read by a person. `OUTSIDE` is new at this layer: it is a pixel the exported grid covers and the
source raster did not, which the old format could only express as `NODATA` — the same code it used
for a cell that is merely off-network. `UNKNOWN_CAUSE` is how a **v1 artifact** is lifted into this
format without inventing provenance it never carried: its one `NODATA` becomes a cell that is
missing for an unrecorded reason, which can never be a known failure. That is precisely what v1
could assert, so lifting an old layer changes no verdict.

**Rounding up is what makes the bound exact rather than approximate.** For an integer-minute
threshold `T`, `ceil(x/60) > T` is equivalent to `x > 60T`, which is `evaluate`'s own comparison.
So a decoder working in whole minutes reaches `evaluate`'s verdict exactly, not nearly. The same
identity for the `OK` plane is why `encode_minutes` rounds up.

**Capping is sound in one direction only.** A bound above `VALUE_MAX` is written as `VALUE_MAX`,
which *weakens* it and can only turn a known failure into an unknown — it can never manufacture an
exclusion. An `OK` minute above `VALUE_MAX` would do the opposite, so `encode_planes` refuses one
instead of capping. The built horizon is 120 minutes, so no `OK` cell can reach the cap today, and
this is a guard rather than a live path.
"""
from __future__ import annotations

import numpy as np

from .status import LAYER_REASONS, Outcome, Reason, Verdict

#: Bumped whenever a code's meaning changes. The browser refuses a manifest it does not know.
ENCODING = "published-v2"

# --------------------------------------------------------------------------- the wire codes
OK = 0
OFF_NETWORK = 1
BEYOND_HORIZON = 2
NO_PATH = 3
LAYER_UNKNOWN = 4
OUTSIDE = 5
#: Missing, with **no recorded cause**. This is what a v1 artifact's single `NODATA` becomes when
#: it is lifted into this format: the bytes on disk record that there was no time and nothing
#: about why, and `OFF_NETWORK` or `BEYOND_HORIZON` would be an invention. It can never be a known
#: failure, which is exactly what v1 could assert and no more — so the lift changes no verdict.
UNKNOWN_CAUSE = 6

#: Every code a `status` plane may hold. A decoder must reject anything else rather than guess.
STATUS_CODES = {
    OK: "OK",
    OFF_NETWORK: "OFF_NETWORK",
    BEYOND_HORIZON: "BEYOND_HORIZON",
    NO_PATH: "NO_PATH",
    LAYER_UNKNOWN: "LAYER_UNKNOWN",
    OUTSIDE: "OUTSIDE",
    UNKNOWN_CAUSE: "UNKNOWN_CAUSE",
}

#: Codes a decoder must treat as "nothing is known here". None of them can carry a bound.
UNKNOWN_CODES = (LAYER_UNKNOWN, OUTSIDE, UNKNOWN_CAUSE)

#: The largest representable minute. 255 is reserved for "this plane says nothing here".
VALUE_MAX = 254
VALUE_NONE = 255

_FROM_REASON = {
    int(Reason.OK): OK,
    int(Reason.OFF_NETWORK): OFF_NETWORK,
    int(Reason.BEYOND_HORIZON): BEYOND_HORIZON,
    int(Reason.NO_PATH): NO_PATH,
}


def _ceil_minutes(seconds: np.ndarray) -> np.ndarray:
    """`ceil(s/60)` as float, with non-finite left as-is for the caller to place."""
    with np.errstate(invalid="ignore"):
        return np.ceil(np.asarray(seconds, dtype=np.float64) / 60.0)


def encode_planes(surface) -> tuple[np.ndarray, np.ndarray]:
    """`(value, status)` uint8 planes for one `status.Surface`.

    Raises rather than capping an `OK` minute above `VALUE_MAX`: capping one downward would turn a
    cell that fails a high threshold into one that passes it, which is the single direction of
    error this format must not have.
    """
    reason = np.asarray(surface.reason)
    status = np.full(reason.shape, OUTSIDE, dtype=np.uint8)
    for r, code in _FROM_REASON.items():
        status[reason == r] = code
    for r in LAYER_REASONS:
        status[reason == int(r)] = LAYER_UNKNOWN

    value = np.full(reason.shape, VALUE_NONE, dtype=np.uint8)

    ok = status == OK
    if ok.any():
        minutes = _ceil_minutes(surface.seconds)[ok]
        if not np.all(np.isfinite(minutes)):
            raise ValueError("an OK cell has a non-finite travel time")
        if minutes.max() > VALUE_MAX:
            raise ValueError(
                f"an OK cell needs {minutes.max():.0f} minutes, above the format's {VALUE_MAX}. "
                "Capping it downward would turn a failing cell into a passing one, so the format "
                "refuses rather than silently narrowing the domain it can publish.")
        value[ok] = minutes.astype(np.uint8)

    bounded = np.isin(status, [OFF_NETWORK, BEYOND_HORIZON, NO_PATH])
    if bounded.any():
        lower = _ceil_minutes(surface.min_possible_s)[bounded]
        # A weaker bound is always safe, so an infinite or oversized one saturates.
        lower = np.where(np.isfinite(lower), lower, float(VALUE_MAX))
        value[bounded] = np.minimum(lower, float(VALUE_MAX)).astype(np.uint8)
    return value, status


def outcome_planes(value: np.ndarray, status: np.ndarray, *, threshold_min: int,
                   horizon_s: float) -> np.ndarray:
    """`status.Outcome` per cell, from the wire planes alone.

    This is `status.evaluate` rewritten against what a browser actually holds, and
    `tests/test_wire.py` asserts the two agree cell for cell on the published layer at every
    threshold a slider can produce. The JavaScript in `spikes/g3-render/worker.js` implements this
    same function, and `selftest.mjs` checks it against vectors generated here.
    """
    value = np.asarray(value)
    status = np.asarray(status)
    unknown_codes = np.isin(status, list(UNKNOWN_CODES))
    if not np.isin(status, list(STATUS_CODES)).all():
        raise ValueError("the status plane holds a code this decoder does not define")

    t = int(threshold_min)
    ok = status == OK
    out = np.full(status.shape, np.int8(Outcome.UNKNOWN), dtype=np.int8)
    out[ok & (value <= t)] = np.int8(Outcome.PASS)
    out[ok & (value > t)] = np.int8(Outcome.FAIL)

    # A known failure needs no route. `value` carries a lower bound for these three codes.
    out[(status == NO_PATH)] = np.int8(Outcome.FAIL)
    out[(status == OFF_NETWORK) & (value > t)] = np.int8(Outcome.FAIL)
    # BEYOND_HORIZON compares against the horizon itself, never the stored bound, so a malformed
    # bound cannot change an eligibility answer — status.py's pass-8 M2 rule, kept here.
    out[(status == BEYOND_HORIZON) & (horizon_s >= 60.0 * t)] = np.int8(Outcome.FAIL)
    out[unknown_codes] = np.int8(Outcome.UNKNOWN)
    return out


def combine_planes(outcomes) -> np.ndarray:
    """`status.Verdict` per cell. **One known failure beats any number of unknowns.**

    The browser's loop used to `break` on the first missing value, which is exactly this rule
    inverted: a cell unknown in one layer and excluded in another came out unknown.
    """
    stack = [np.asarray(o) for o in outcomes]
    if not stack:
        raise ValueError("combine_planes needs at least one outcome plane")
    arr = np.stack(stack)
    any_fail = (arr == int(Outcome.FAIL)).any(axis=0)
    any_unknown = (arr == int(Outcome.UNKNOWN)).any(axis=0)
    out = np.where(any_fail, np.int8(Verdict.EXCLUDED),
                   np.where(any_unknown, np.int8(Verdict.UNKNOWN), np.int8(Verdict.INCLUDED)))
    return out.astype(np.int8)
