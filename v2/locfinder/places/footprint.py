"""Does a building footprint corroborate a supermarket at this point?

**The third adversarial review, 2026-11-18**
([[2026-11-18-name-recovery-review-findings]], P1-2) found that **8 of the 13** records
`recover_brandless_by_name.py` had just promoted to `supermarket` rested on a building that does
**not contain the record's point**. Named, from our own buildings table:

* the 837 m² `Lowes Foods` -- the one already flagged as "small for that chain" -- is
  **Discount Tire**, 105 m away;
* `ALDI` borrowed **New Hope Baptist Church**, 115 m away;
* both `Wal Mart` records borrowed **Europa Center**, 67 m and 81 m away.

The rule that produced them was `max(area)` over every building intersecting a **120 m buffer**.
That is the strip-mall failure which had already made `measure_footprint_separation.py` withdraw
its positive branch **the same morning** -- re-entering through the rule written to replace it.
It was in two scripts, not one, which is the usual shape: *a stale claim is a class, not a line*.

---

## The asymmetry, which is the whole module

**A footprint is an upper bound on the shop inside it.** Three consequences, and they do not point
the same way:

* a building the point is **inside**, big enough for a weekly shop, **can corroborate** one;
* a big building the point is **merely near corroborates nothing** -- geometry cannot say whether
  it is this shop or the anchor tenant two doors down;
* **nothing** big within reach **does refute** a weekly shop. No supermarket stands there,
  whatever the record calls itself.

So the answer is three-valued, for the same reason `name_match.match_verdict` is: *near a big
building* and *in a small building* are different facts, and a single number hides which one you
have. The review found the 8 precisely because the old code reported both as one float.

## Why the strict reading is the cheap one

`unclassified` is **outside** the published layer. A record wrongly left there costs a household
nothing -- the shop is simply not offered. A record wrongly promoted is a destination a household
is routed to. So where geometry cannot decide, this module declines, and `NEIGHBOUR` is a
deliberate refusal rather than a weak yes.

The cost is real and was measured, not assumed: requiring containment takes the recovery from 13
accepted to 8, and five records that are probably real shops with displaced points go back to
`unclassified`. That is the trade this module chooses on purpose.
"""
from __future__ import annotations

from typing import NamedTuple, Sequence

# ---------------------------------------------------------------------------------- the verdicts

CORROBORATED = "corroborated"
"""The point lies inside a building big enough to hold a weekly shop."""

NEIGHBOUR = "neighbour"
"""A big building stands nearby but the point is not inside one. Geometry cannot decide."""

REFUTED = "refuted"
"""No building within reach is big enough. No supermarket stands here."""

# ------------------------------------------------------------------------------- the two numbers

FLOOR_M2 = 650.0
"""From the clean polygon-only calibration in `measure_footprint_separation.py`: the area below
which a footprint cannot hold a weekly shop. 94%+ separation, and it decides only 11% of the
brandless blocker, which is why it is a screen and never the whole rule."""

NEAR_LOOK_M = 120.0
"""How far the caller looks for buildings. Kept here with the floor so the two cannot drift apart
in two scripts. A building found at this range can only ever produce `NEIGHBOUR`."""


class Corroboration(NamedTuple):
    """What the geometry says, and the two areas it says it with."""

    verdict: str
    host_m2: float
    """Area of the building containing the point, or 0.0 if the point is in none."""
    near_m2: float
    """Area of the largest building the caller offered, contained or not."""


def corroboration(point, nearby: Sequence) -> Corroboration:
    """Judge a point against the buildings within `NEAR_LOOK_M` of it.

    `point` and `nearby` must be in a projected CRS in **metres** -- areas are read straight off
    the geometry. The caller does the spatial selection, because it holds the index; this function
    holds the rule.
    """
    host = 0.0
    near = 0.0
    for geom in nearby:
        if geom is None or geom.is_empty:
            continue
        area = float(geom.area)
        if area > near:
            near = area
        # `intersects`, not `contains`: a point digitised onto the wall of its own building is
        # still in it, and Overture points sit on building edges often enough to matter.
        if geom.intersects(point) and area > host:
            host = area

    if host >= FLOOR_M2:
        verdict = CORROBORATED
    elif near >= FLOOR_M2:
        verdict = NEIGHBOUR
    else:
        verdict = REFUTED
    return Corroboration(verdict, host, near)


def licenses_supermarket(got: Corroboration) -> bool:
    """Only `CORROBORATED` may put a record into a layer a household is routed by."""
    return got.verdict == CORROBORATED


def why_not_corroborated(got: Corroboration) -> str:
    """The sentence for the audit sheet. Empty when the geometry did corroborate.

    The two refusals must not read alike: one says *we cannot tell*, the other says *nothing is
    here*. A reviewer who cannot separate them cannot check the sheet.
    """
    if got.verdict == CORROBORATED:
        return ""
    if got.verdict == NEIGHBOUR:
        return (
            f"the point is inside no building over {FLOOR_M2:,.0f} m2 -- the largest within "
            f"{NEAR_LOOK_M:.0f} m is {got.near_m2:,.0f} m2 and is a NEIGHBOUR'S building, which "
            f"is how Discount Tire came to corroborate a Lowes Foods. A footprint is an upper "
            f"bound on the shop inside it, so a building the point is not in says nothing"
        )
    return (
        f"the largest building within {NEAR_LOOK_M:.0f} m is {got.near_m2:,.0f} m2, under the "
        f"{FLOOR_M2:,.0f} m2 floor. No supermarket stands here, whatever this record calls itself"
    )
