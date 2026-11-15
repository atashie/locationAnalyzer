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

#: How far a recorded arrival may be from the coordinate of the place it **names**, in metres.
#:
#: **A name is not an identity** (pass 51 A2) **and proximity is not identity either** (pass 52
#: F3). The committed metro sheet holds two shops both called `Food Lion` 11 km apart, and one
#: journey's own alternatives list is *also* `Food Lion`, so a string comparison accepts the wrong
#: branch. The first repair compared the arrival with the **selected** place's coordinate inside a
#: 600 m envelope, justified as "a place is within 300 m of its node, so two places on one node
#: are within 600 m of each other" — which is a necessary condition and not a sufficient one. Two
#: different shops of the same name 270 m apart, on different nodes, satisfy it; and a legitimate
#: door 620 m from a *different* member's centroid failed it.
#:
#: So the arrival is matched against **the coordinate of the member whose name was recorded**, and
#: the radius is a door-to-centroid distance rather than a node envelope: a supermarket footprint
#: is of the order of 100 m across, the audit's own centroid-to-door bound on a 100 m cell is
#: 70.7 m, and a phone's fix adds a few tens of metres.
DESTINATION_ARRIVAL_M = 200.0

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


def check_lonlat(lon, lat, *, what: str) -> tuple[float, float]:
    """A finite coordinate inside the geographic ranges, or `ValueError`.

    **Pass 52 finding F9**: without the range check, a latitude of `395.910405` — a typo away from
    `35.910405` — wrapped through 360° in the haversine and produced a distance of about
    1.6e-9 m, so an impossible coordinate read as "you arrived exactly at the shop". A sheet is
    typed by hand and this is the one place a typo in it could *manufacture* agreement rather than
    refuse the row.
    """
    try:
        lon_f, lat_f = float(lon), float(lat)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{what} ({lon!r}, {lat!r}) is not a pair of numbers: {exc}") from exc
    if not (math.isfinite(lon_f) and math.isfinite(lat_f)):
        raise ValueError(f"{what} ({lon!r}, {lat!r}) is not finite")
    if not (-180.0 <= lon_f <= 180.0 and -90.0 <= lat_f <= 90.0):
        raise ValueError(
            f"{what} ({lon_f}, {lat_f}) is outside the geographic ranges, so it is a typo rather "
            "than a place")
    return lon_f, lat_f


def metres_between(lon_a, lat_a, lon_b, lat_b) -> float:
    """Great-circle metres. Exact enough for a few hundred metres on a 100 m grid.

    Both coordinates are range-checked: see `check_lonlat`.
    """
    lon_a, lat_a = check_lonlat(lon_a, lat_a, what="a coordinate")
    lon_b, lat_b = check_lonlat(lon_b, lat_b, what="a coordinate")
    phi_a, phi_b = math.radians(float(lat_a)), math.radians(float(lat_b))
    d_phi = phi_b - phi_a
    d_lam = math.radians(float(lon_b) - float(lon_a))
    h = (math.sin(d_phi / 2) ** 2
         + math.cos(phi_a) * math.cos(phi_b) * math.sin(d_lam / 2) ** 2)
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(h)))


@dataclass(frozen=True)
class PermittedPlace:
    """One place the walk may legitimately have ended at, with its own coordinate.

    A name and a coordinate travel together in one object rather than in two aligned lists,
    because the whole point is that the pair is the identity: matching a recorded name against
    one member and a recorded arrival against a *different* member's coordinate is the defect
    pass 52 F3 describes.
    """

    name: str
    lon: float | None = None
    lat: float | None = None


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
    #: Other places on the selected node, each with its own coordinate. The audit README
    #: explicitly permits walking to any of them, so refusing one by name was a defect in the
    #: other direction (A2); and each needs its own location, or an arrival can be matched to the
    #: wrong member (F3).
    destination_alternatives: tuple[PermittedPlace, ...] = ()
    #: Free text: which way the walk actually went. Detail for a reader, not something a predicate
    #: can check — which is why `route_identified` exists beside it.
    route_followed: str | None = None
    #: `True` = the walker can say which way they went, `False` = they cannot, `None` = the record
    #: does not say. Pass 51 A3: "I cannot remember whether I used the private track or avoided
    #: it" is non-blank prose that admits the approach is unresolved, and a non-blank check
    #: accepted it.
    route_identified: bool | None = None
    #: **Did you make this journey?** `True` from `yes`, `False` from `no`, `None` where the
    #: sheet does not say. Added for pass 53 F2: three passes tried to infer this and each got it
    #: wrong in a new direction, and the README's own instructions make inference unsound, because
    #: the owner records a start door before setting out.
    walk_happened: bool | None = None
    #: Answers that were filled in and not understood — `duration_timed="not timed"`, say. Kept
    #: rather than coerced to `None`: silently erasing a malformed entry is not validation, and it
    #: turned a filled row into an empty one (pass 53 F2).
    malformed: tuple[str, ...] = ()
    #: Columns that record an observation without being the duration.
    walked_date: str | None = None
    #: Centre-to-door distance, which the README asks for in step 2, **before** the walk.
    door_offset_m: float | None = None
    unresolved: str | None = None
    notes: str | None = None
    destination_qualifies: str | None = None
    destination_open: str | None = None
    route_usable: str | None = None
    witness_within_10min: str | None = None
    witness_within_15min: str | None = None

    #: Columns only somebody who made the journey can fill in. **Not every observation column** —
    #: see `PREPARATION_FIELDS`, which is the half that broke the inference.
    WALK_ONLY_FIELDS = ("walked_seconds", "walked_date", "destination_used",
                        "destination_used_lon", "destination_used_lat", "destination_qualifies",
                        "destination_open", "route_usable", "route_followed", "route_identified",
                        "duration_timed", "witness_within_10min", "witness_within_15min")

    #: Columns the audit README tells the owner to fill in **before setting out**. Step 2 is "pick
    #: a real front door inside that cell, record it in `start_lon`, `start_lat`, and put the
    #: distance from the cell centre in `door_offset_m`" — step 3 is the walk. So a sheet prepared
    #: and then abandoned has these filled and nothing else, and reading them as evidence of a
    #: walk classified a planned row as a refused one (pass 53 F2).
    PREPARATION_FIELDS = ("start_lon", "start_lat", "door_offset_m")

    #: Free text that could be either. `notes` on a planned row may read "picked the north door";
    #: on a walked one, "timer failed". Nothing can tell them apart, so neither decides.
    AMBIGUOUS_FIELDS = ("unresolved", "notes")

    #: Answers that are **not** evidence of a walk, per field. `untested` is what the README tells
    #: the owner to write for a witness column when they did not try.
    NON_EVIDENCE_VALUES = {
        "witness_within_10min": {"untested"},
        "witness_within_15min": {"untested"},
    }

    @property
    def evidence_of_a_walk(self) -> tuple[str, ...]:
        """Columns whose contents only somebody who made the journey could have written.

        This is **fallback** evidence, used when `walk_happened` does not say. Three passes tried
        to settle "did a walk happen" by inference and each one got it wrong in a new direction:
        pass 51 A1 lost a walk whose duration was missing; pass 52 F2 lost one recorded only in
        `duration_timed`, and invented one from a witness column reading `untested`; pass 53 F2
        showed the inference is **unsound in principle**, because the README has the owner record
        a start door before setting out. So the sheet now asks, and this only breaks the tie.
        """
        found = []
        for name in self.WALK_ONLY_FIELDS:
            value = getattr(self, name, None)
            if _blank(value):
                continue
            excluded = self.NON_EVIDENCE_VALUES.get(name)
            if excluded and isinstance(value, str) and value.strip().lower() in excluded:
                continue
            found.append(name)
        return tuple(found)

    @property
    def preparation_recorded(self) -> tuple[str, ...]:
        """Columns that are filled in, and that a walk is not needed to fill in."""
        return tuple(name for name in self.PREPARATION_FIELDS
                     if not _blank(getattr(self, name, None)))

    @property
    def walked(self) -> bool:
        """Whether a walk happened. **The sheet's answer first, inference only as a fallback.**

        `walk_happened` is a column the owner fills in: `yes` means they made the journey, `no`
        means they did not, and a blank falls back to `evidence_of_a_walk`. An explicit `no`
        overrides the evidence, because a row can carry a start door, a chosen destination and a
        note about the route while nobody has been anywhere.
        """
        if self.walk_happened is not None:
            return self.walk_happened
        return bool(self.evidence_of_a_walk)

    #: Every owner column, so that the three lists above can be checked against the sheet rather
    #: than against my memory of it. Pass 53 F2 found three columns missing from the one list
    #: there was, and `tests/test_admissible.py` now reconciles these against
    #: `audit_recommendations.OWNER_COLUMNS`.
    ALL_OBSERVATION_FIELDS = WALK_ONLY_FIELDS + PREPARATION_FIELDS + AMBIGUOUS_FIELDS

    def permitted_destinations(self) -> tuple[PermittedPlace, ...]:
        """Every place this walk may legitimately have ended at, each with its own coordinate.

        The selected place first, then the others on its node. The audit README tells the owner to
        walk to whichever of them they would use, so all of them are permitted — and each carries
        its own location, because matching a recorded name to one member and a recorded arrival to
        another member's coordinate is what pass 52 F3 found.
        """
        out = []
        if not _blank(self.predicted_destination):
            out.append(PermittedPlace(name=str(self.predicted_destination).strip(),
                                      lon=self.predicted_destination_lon,
                                      lat=self.predicted_destination_lat))
        for alt in self.destination_alternatives:
            if _blank(alt.name):
                continue
            out.append(PermittedPlace(name=str(alt.name).strip(), lon=alt.lon, lat=alt.lat))
        return tuple(out)


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
    | that a walk happened at all | `walk_happened`, or failing that `evidence_of_a_walk` |
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
        said = ("the sheet says this journey was walked"
                if record.walk_happened else
                "a walk is recorded (" + ", ".join(record.evidence_of_a_walk) + ")")
        reasons.append(f"{said} and no duration is, so there is nothing to compare it with")

    # Answers that were filled in and not understood. Pass 53 F2: `tri_state` mapped an
    # unrecognised value to `None`, so `duration_timed="not timed"` erased itself and a filled row
    # became an empty one. Coercion is not validation (ledger 35), one level down.
    for column in record.malformed:
        reasons.append(
            f"the answer recorded in {column} was not understood, so what it says about this "
            "walk is unknown rather than absent"
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
    permitted = record.permitted_destinations()
    names = [p.name for p in permitted]
    used = None if _blank(record.destination_used) else str(record.destination_used).strip()
    # **Every member with this name, not one of them** — pass 53 finding F5. This was a dict keyed
    # by name, so the LAST member for a name won, and a node carrying two places of the same name
    # lost one of them. That is not hypothetical: `triangle-grocery-walk-with-destinations.csv`
    # selects `Food Lion` on two rows and lists an alternative *also* called `Food Lion`, with no
    # coordinate, so the coordinate-less alternative replaced the selected shop and a legitimate
    # walk to the selected shop was refused for having no coordinate to match. Seven entries in
    # the published side table repeat a name inside one entry.
    candidates = [p for p in permitted if used is not None and p.name == used]
    if used is None:
        reasons.append("the destination reached is not recorded")
    elif not permitted:
        reasons.append("the record does not say which destination the product selected")
    elif not candidates:
        others = sorted(set(names) - {str(record.predicted_destination).strip()})
        reasons.append(
            f"walked to {used!r}; the product routed to "
            f"{str(record.predicted_destination).strip()!r}"
            + (f" (or one of {others})" if others else "")
            + ", so this is a different journey"
        )

    # The arrival is matched against the coordinate of a member whose name was recorded. Pass 52
    # F3: comparing it against the SELECTED place's coordinate inside a node-sized envelope
    # accepts a different shop of the same name 270 m away on another node, and refuses a
    # legitimate door measured from the wrong member.
    #
    # Where several members share the recorded name, arriving at ANY of them is arriving at a
    # place the record names, so the nearest one decides. Refusing because a namesake is further
    # away would refuse a truthful walk, and accepting on the *selected* member alone was F3.
    if _blank(record.destination_used_lon) or _blank(record.destination_used_lat):
        reasons.append(
            "where the walk ended is not recorded, so the shop reached is identified by name "
            "only and a name does not identify a shop"
        )
    elif not candidates:
        pass                      # already refused: the name is not a permitted destination
    else:
        located = [p for p in candidates if not _blank(p.lon) and not _blank(p.lat)]
        if not located:
            reasons.append(
                f"the record does not say where {used!r} is, so the arrival cannot be matched to "
                "it and the name is the only evidence of which shop was reached"
            )
        else:
            gaps = []
            bad = None
            for place in located:
                try:
                    gaps.append(metres_between(record.destination_used_lon,
                                               record.destination_used_lat, place.lon, place.lat))
                except ValueError as exc:
                    bad = exc
            if not gaps:
                reasons.append(f"the arrival coordinate is not usable: {bad}")
            elif min(gaps) > DESTINATION_ARRIVAL_M:
                reasons.append(
                    f"the walk ended {min(gaps):.0f} m from "
                    + (f"the nearest of {len(located)} places called {used!r}"
                       if len(located) > 1 else repr(used))
                    + f", past the {DESTINATION_ARRIVAL_M:.0f} m a door can be from a shop's "
                    "centroid, so the shop reached is not the one the record names"
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
