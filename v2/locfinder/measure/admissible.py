"""What a walked audit record must document before E3 may score it.

E3 compares a walked duration with what the product said. **Codex pass 47 established that the one
walked journey cannot be scored at all**, and the reason was not arithmetic: the record does not
document the journey the comparison is about. `docs/s3-decision-report.md` states the four things
missing, and this module is that table in code.

## Why this is a separate state and not a flag

`e3.py`'s `Journey` has three fields — `label`, `reported_s`, `observed_s` — and therefore **two**
states: `observed_s is None` means planned but not walked, anything else means walked and scorable.
"Walked but not admissible" is a third thing, and because the scorer could not represent it, it was
reached by a human reading the audit README. That happened three times and the first two were
wrong in opposite directions: the decision report first said real-world accuracy was "UNVERIFIED,
the owner's call" (pass 46: that bypasses the project's own scorer and understates the evidence),
then said `FAILED` (pass 47: the scorer cannot be applied to this observation at all).

A binary where a third state is load-bearing is the same defect this project has already paid for
in `status.Reason`, in the browser's `Verdict`, and in `feedback-verify-the-shape-of-the-risk`
instance 32. So the third state is written down, named, and reported.

## The refusal, and what it must not become

An inadmissible walk is **not** turned into a planned journey. That would be the cheap fix and it
is a lie: `E3Result.planned` would count it, nothing would say a walk had happened, and E3 would
report UNVERIFIED with no trace of the discrepancy. "Absence is not evidence of cleanliness" —
the record goes into `ScoringSet.inadmissible` with its reasons, and
`e3.score_walked_records` carries that list into the result so an outcome cannot be reported
without it.

## What this module does not decide

Whether a given walk *should* have been admissible, and whether any threshold moves. It reads a
record and says whether the comparison E3 defines is documented. Admissibility is not agreement: an
admissible record can still fail, and making a record admissible is what lets it fail.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

#: `docs/s3-decision-report.md`: E3's `reported_s` is **what the product said**, which is the
#: published whole minute, not the model's float. For `band15min_pass-03` that is 840 s and not
#: 810.8185424804688 — a distinction that moves the binding boundary from 16.9 to 17.5 minutes, so
#: it is not cosmetic.
SECONDS_PER_MINUTE = 60.0


class Admissibility(str, Enum):
    """Three states, because two were not enough. See the module docstring."""

    ADMISSIBLE = "ADMISSIBLE"
    NOT_ADMISSIBLE = "NOT_ADMISSIBLE"
    NOT_WALKED = "NOT_WALKED"


class Grid(Protocol):
    """Just enough of `locfinder.grid.GridSpec` to place a door in a cell.

    A protocol rather than an import so this module does not pull in rasterio and pyproj, but the
    tests pass a **real** `GridSpec`: a stub grid could agree with a wrong implementation of the
    thing being checked.
    """

    def cell_for_lonlat(self, lon: float, lat: float) -> tuple[int, int] | None: ...


def reported_seconds(encoded_minutes: float | int | None) -> float | None:
    """Seconds the product published for a cell, from its encoded whole minute.

    `None` in, `None` out: a cell with no published minute makes no claim, and inventing one would
    manufacture the thing E3 is supposed to be testing.
    """
    if encoded_minutes is None:
        return None
    m = float(encoded_minutes)
    if not math.isfinite(m) or m < 0:
        raise ValueError(f"encoded_minutes must be a non-negative whole number of minutes, got {m!r}")
    return m * SECONDS_PER_MINUTE


@dataclass(frozen=True)
class WalkedRecord:
    """One row of a walked-audit sheet, as the sheet holds it.

    Every observation field defaults to `None`, which means **the record does not say** — never
    "no" and never zero. A blank cell in a sheet is an absence of evidence and the predicate below
    treats it as one.
    """

    label: str
    row: int
    col: int
    #: What the product published for this cell, in seconds. `None` = it published nothing.
    reported_s: float | None = None
    #: The walk. `None` = not walked.
    walked_seconds: float | None = None
    #: `True` = timed, `False` = recorded as not timed, `None` = the record does not say.
    duration_timed: bool | None = None
    start_lon: float | None = None
    start_lat: float | None = None
    destination_used: str | None = None
    predicted_destination: str | None = None
    #: Free text: which way the walk actually went. Required only to be **on the record**, because
    #: no predicate can check prose. `docs/s3-decision-report.md` asks for "whether the private
    #: approach was used or avoided".
    route_followed: str | None = None

    @property
    def walked(self) -> bool:
        return self.walked_seconds is not None


@dataclass(frozen=True)
class Inadmissible:
    """A walk that happened and cannot be scored, with every reason it cannot."""

    label: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ScoringSet:
    """The result of applying the predicate to a set of records.

    Three buckets, and a record is in exactly one. `journeys` holds what E3 may score — admissible
    walks and journeys that were never walked. `inadmissible` holds walks that happened and cannot
    be compared. `without_a_published_time` holds rows the product made no claim about, which are
    not E3 journeys at all: an `OFF_NETWORK` cell has no published minute, so there is nothing to
    be right or wrong about.
    """

    journeys: tuple
    inadmissible: tuple[Inadmissible, ...]
    without_a_published_time: tuple[str, ...]


def _blank(value) -> bool:
    """A sheet's blank. Treats the empty string as absent, because `csv` gives `''` and not `None`."""
    return value is None or (isinstance(value, str) and value.strip() == "")


def admissibility(record: WalkedRecord, *, grid: Grid) -> tuple[Admissibility, tuple[str, ...]]:
    """Whether E3 may score this record, and if not, every reason why.

    The four requirements are `docs/s3-decision-report.md`'s table, in its order:

    | what E3 needs | checked here as |
    |---|---|
    | the door the walk started from, inside the cell | `start_lon`/`start_lat` place the door in cell `(row, col)` |
    | the destination actually reached | `destination_used` names the destination the product selected |
    | whether the private approach was used or avoided | `route_followed` is on the record |
    | a timed duration | `duration_timed` is `True` |

    **Every reason is collected, not the first.** A record missing three things should say so once,
    rather than being fixed and refused three times.
    """
    if not record.walked:
        return Admissibility.NOT_WALKED, ()

    reasons: list[str] = []

    if record.reported_s is None:
        reasons.append(
            "the product published no time for this cell, so there is nothing to compare"
        )

    # 1. the door, inside the cell the published answer is for
    if _blank(record.start_lon) or _blank(record.start_lat):
        reasons.append("no start door recorded, so the walk's origin is unknown")
    else:
        # A sheet is typed by hand, so the coordinate may not be one. `cell_for_lonlat` raises on a
        # non-finite or unprojectable point, and a crash here would take down the whole ingestion
        # over one bad cell — refuse that row and report the rest.
        try:
            where = grid.cell_for_lonlat(float(record.start_lon), float(record.start_lat))
        except (ValueError, TypeError) as exc:
            reasons.append(
                f"the start door ({record.start_lon!r}, {record.start_lat!r}) is not a usable "
                f"coordinate: {exc}"
            )
        else:
            if where is None:
                reasons.append(
                    f"the start door ({record.start_lon}, {record.start_lat}) is outside the grid, "
                    "so no published answer covers it"
                )
            elif where != (record.row, record.col):
                reasons.append(
                    f"the start door is in cell {where}, not cell "
                    f"({record.row}, {record.col}) that this answer is for"
                )

    # 2. the destination actually reached, and that it is ours
    if _blank(record.destination_used):
        reasons.append("the destination reached is not recorded")
    elif _blank(record.predicted_destination):
        reasons.append("the record does not say which destination the product selected")
    elif str(record.destination_used).strip() != str(record.predicted_destination).strip():
        reasons.append(
            f"walked to {str(record.destination_used).strip()!r}; the product routed to "
            f"{str(record.predicted_destination).strip()!r}, so this is a different journey"
        )

    # 3. which way the walk went
    if _blank(record.route_followed):
        reasons.append("the route walked is not on the record")

    # 4. a timed duration
    if record.duration_timed is None:
        reasons.append("the record does not say whether the duration was timed")
    elif not record.duration_timed:
        reasons.append("the duration is recorded as not timed, so it is an estimate")

    if reasons:
        return Admissibility.NOT_ADMISSIBLE, tuple(reasons)
    return Admissibility.ADMISSIBLE, ()


def sort_records(records, *, grid: Grid) -> ScoringSet:
    """Split records into what E3 may score, what it may not, and what makes no claim.

    An inadmissible walk **never** becomes a planned journey. See the module docstring: that
    substitution would hide a walk inside `E3Result.planned`.
    """
    from .e3 import Journey          # local: e3 imports nothing from here, and this keeps it so

    journeys: list[Journey] = []
    inadmissible: list[Inadmissible] = []
    no_claim: list[str] = []

    seen: set[str] = set()
    for record in records:
        if record.label in seen:
            raise ValueError(
                f"{record.label}: duplicate label, so a refusal could not be pointed at a row"
            )
        seen.add(record.label)

        verdict, reasons = admissibility(record, grid=grid)
        if verdict is Admissibility.ADMISSIBLE:
            journeys.append(Journey(label=record.label, reported_s=float(record.reported_s),
                                    observed_s=float(record.walked_seconds)))
        elif verdict is Admissibility.NOT_ADMISSIBLE:
            inadmissible.append(Inadmissible(label=record.label, reasons=reasons))
        elif record.reported_s is None:
            no_claim.append(record.label)
        else:
            journeys.append(Journey(label=record.label, reported_s=float(record.reported_s)))

    return ScoringSet(journeys=tuple(journeys), inadmissible=tuple(inadmissible),
                      without_a_published_time=tuple(no_claim))
