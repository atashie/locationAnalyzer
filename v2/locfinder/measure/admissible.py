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

#: Mean Earth radius, for the arrival-coordinate check below.
EARTH_RADIUS_M = 6371008.8

#: How far the recorded arrival may be from the destination the layer selected, in metres.
#:
#: **A name is not an identity**, which is pass 51 finding A2. The committed metro sheet holds two
#: different shops both called `Food Lion`, 11 km apart, and one journey's own
#: `predicted_destination_alternatives` is *also* `Food Lion` — a second shop of that name on the
#: same road node. So a string comparison accepts a walk to the wrong branch and cannot tell the
#: right branch from its namesake.
#:
#: 300 m is the acquisition cap from a place to its road node, so every place sharing the selected
#: node is within 300 m of the node and therefore within 600 m of any other such place. This
#: tolerance is measured from the **selected place's** coordinate and admits a shared-node
#: alternative comfortably while refusing a different branch of the same chain.
DESTINATION_IDENTITY_M = 600.0

#: The separator `recover_audit_destinations.py` writes between alternative place names.
ALTERNATIVES_SEPARATOR = ";"

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


def metres_between(lon_a, lat_a, lon_b, lat_b) -> float:
    """Great-circle metres. Exact enough for a few hundred metres on a 100 m grid."""
    phi_a, phi_b = math.radians(float(lat_a)), math.radians(float(lat_b))
    d_phi = phi_b - phi_a
    d_lam = math.radians(float(lon_b) - float(lon_a))
    h = (math.sin(d_phi / 2) ** 2
         + math.cos(phi_a) * math.cos(phi_b) * math.sin(d_lam / 2) ** 2)
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(h)))


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
    #: The walk's duration. `None` = no usable duration was recorded, which is **not** the same as
    #: "no walk happened" — see `evidence_of_a_walk`.
    walked_seconds: float | None = None
    #: `True` = timed, `False` = recorded as not timed, `None` = the record does not say.
    duration_timed: bool | None = None
    start_lon: float | None = None
    start_lat: float | None = None
    destination_used: str | None = None
    #: Where the walk actually ended. Required, because a name is not an identity (A2).
    destination_used_lon: float | None = None
    destination_used_lat: float | None = None
    predicted_destination: str | None = None
    #: The selected place's own coordinate, from the sheet's `predicted_destination_lat`/`_lon`.
    predicted_destination_lon: float | None = None
    predicted_destination_lat: float | None = None
    #: Other places on the selected node. The audit README explicitly permits walking to any of
    #: them, so refusing one by name was a defect in the other direction (A2).
    destination_alternatives: tuple[str, ...] = ()
    #: Free text: which way the walk actually went. Detail for a reader, not something a predicate
    #: can check — which is why `route_identified` exists beside it.
    route_followed: str | None = None
    #: `True` = the walker can say which way they went, `False` = they cannot, `None` = the record
    #: does not say. Pass 51 A3: "I cannot remember whether I used the private track or avoided
    #: it" is non-blank prose that admits the approach is unresolved, and a non-blank check
    #: accepted it.
    route_identified: bool | None = None
    #: Columns that record an observation without being the duration. They decide whether a walk
    #: HAPPENED, which is a separate question from whether it can be scored.
    walked_date: str | None = None
    destination_qualifies: str | None = None
    destination_open: str | None = None
    route_usable: str | None = None
    witness_within_10min: str | None = None
    witness_within_15min: str | None = None

    #: Every field whose presence is evidence that somebody walked this journey.
    EVIDENCE_FIELDS = ("walked_seconds", "walked_date", "start_lon", "start_lat",
                       "destination_used", "destination_used_lon", "destination_used_lat",
                       "destination_qualifies", "destination_open", "route_usable",
                       "witness_within_10min", "witness_within_15min", "route_followed")

    @property
    def evidence_of_a_walk(self) -> tuple[str, ...]:
        """Which columns record that somebody actually walked this journey.

        **`walked_seconds` is not the only one, and treating it as the only one lost a walk.**
        Pass 51 finding A1: a row dated, with a door, a destination and a route recorded, but no
        usable duration, was reported as "planned, not walked" — `walked=0, planned=1`, nothing
        inadmissible, `no_admissible_observation` false. The walk vanished from the record of what
        could not be scored, which is the one thing this module exists to prevent.
        """
        return tuple(name for name in self.EVIDENCE_FIELDS
                     if not _blank(getattr(self, name, None)))

    @property
    def walked(self) -> bool:
        return bool(self.evidence_of_a_walk)


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
    | that a walk happened at all | any of `EVIDENCE_FIELDS` is filled in |
    | the door the walk started from, inside the cell | `start_lon`/`start_lat` place the door in cell `(row, col)` |
    | the destination actually reached | `destination_used` is the selected place or one of its node's others, **and** `destination_used_lon`/`_lat` is within `DESTINATION_IDENTITY_M` of the selected place |
    | whether the private approach was used or avoided | `route_followed` is on the record **and** `route_identified` is `True` |
    | a timed duration | `walked_seconds` is present and `duration_timed` is `True` |

    Rows two to four are `docs/s3-decision-report.md`'s table. Row one and the second halves of
    rows three and four are pass 51's findings A1, A2 and A3: a walk with no duration disappeared
    into "planned", a name accepted the wrong branch of a chain, and prose admitting the approach
    was unresolved satisfied a non-blank test.

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

    # 0. a walk happened, and its duration is on the record (pass 51 A1)
    if record.walked_seconds is None:
        reasons.append(
            "a walk is recorded ("
            + ", ".join(record.evidence_of_a_walk)
            + ") and no duration is, so there is nothing to compare it with"
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
    #
    # **A name is not an identity**, which is pass 51 A2 and is why this takes a coordinate. The
    # permitted set is the selected place plus the other places on its node, because the audit
    # README explicitly says to walk to whichever of them you would use — refusing a named
    # alternative was the same defect pointing the other way.
    permitted = {str(record.predicted_destination).strip()} if not _blank(
        record.predicted_destination) else set()
    permitted |= {str(a).strip() for a in record.destination_alternatives if not _blank(a)}
    if _blank(record.destination_used):
        reasons.append("the destination reached is not recorded")
    elif not permitted:
        reasons.append("the record does not say which destination the product selected")
    elif str(record.destination_used).strip() not in permitted:
        reasons.append(
            f"walked to {str(record.destination_used).strip()!r}; the product routed to "
            f"{str(record.predicted_destination).strip()!r}"
            + (f" (or one of {sorted(permitted - {str(record.predicted_destination).strip()})})"
               if len(permitted) > 1 else "")
            + ", so this is a different journey"
        )

    if _blank(record.destination_used_lon) or _blank(record.destination_used_lat):
        reasons.append(
            "where the walk ended is not recorded, so the shop reached is identified by name "
            "only and a name does not identify a shop"
        )
    elif _blank(record.predicted_destination_lon) or _blank(record.predicted_destination_lat):
        reasons.append(
            "the record does not say where the selected destination is, so the arrival cannot be "
            "checked against it"
        )
    else:
        try:
            gap = metres_between(record.destination_used_lon, record.destination_used_lat,
                                 record.predicted_destination_lon,
                                 record.predicted_destination_lat)
        except (ValueError, TypeError) as exc:
            reasons.append(f"the arrival coordinate is not a usable coordinate: {exc}")
        else:
            if gap > DESTINATION_IDENTITY_M:
                reasons.append(
                    f"the walk ended {gap:.0f} m from the destination the layer selected, past "
                    f"the {DESTINATION_IDENTITY_M:.0f} m a place on the selected node can be, so "
                    "this is a different shop whatever it is called"
                )

    # 3. which way the walk went
    #
    # `route_followed` is prose and carries the detail; `route_identified` is what a predicate can
    # check. Pass 51 A3: "I cannot remember whether I used the private track or avoided it" is
    # non-blank, admits the approach is unresolved, and satisfied a non-blank test.
    if _blank(record.route_followed):
        reasons.append("the route walked is not on the record")
    if record.route_identified is None:
        reasons.append("the record does not say whether the route walked could be identified")
    elif not record.route_identified:
        reasons.append(
            "the route walked is recorded as not identifiable, so whether the journey used the "
            "approach the layer routed through is unresolved"
        )

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
