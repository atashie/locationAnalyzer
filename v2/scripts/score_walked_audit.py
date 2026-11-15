"""Score a walked-audit sheet against E3, refusing the walks whose records cannot be compared.

**This is the path that did not exist.** The sheets have carried `start_lon`, `start_lat`,
`destination_used` and `walked_seconds` since step 0, and nothing read them into
`locfinder/measure/e3.py`: the only consumers of those columns were `audit_recommendations.py`,
which writes them blank, and `compare_rebuild_to_stored.py`, which compares rasters. So the one
walked journey reached E3 by hand, three times, and the first two attempts got its status wrong in
opposite directions — pass 46 said the draft understated a failure, pass 47 said the correction
overstated it and the scorer cannot be applied to that observation at all.

What this script does, and the order matters:

1. reads a sheet, refusing one that lacks a column the predicate needs;
2. takes each row's **published whole minute** as what the product said, not the model's float
   seconds — `docs/s3-decision-report.md`, and the difference moves the binding boundary from 16.9
   to 17.5 minutes on the one journey we have;
3. applies `measure/admissible.py` and scores only what survives it;
4. prints and records every refused walk **with its reasons**, because UNVERIFIED on an empty set
   and UNVERIFIED after refusing every walk are different claims about the world.

It needs the grid and the sheet. No graph load, no layers, about a second.

Run from `v2/`:

    python scripts/score_walked_audit.py \
        ../docs/experiments/audit/triangle-grocery-walk-chapelhill-with-destinations.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict
from pathlib import Path

V2 = Path(__file__).resolve().parents[1]
if str(V2) not in sys.path:
    sys.path.insert(0, str(V2))

from locfinder.measure.admissible import (  # noqa: E402
    ALTERNATIVES_SEPARATOR,
    PermittedPlace,
    WalkedRecord,
    reported_seconds,
)
from locfinder.measure.e3 import (  # noqa: E402
    ABSOLUTE_LIMIT_S,
    MEDIAN_SHARE_LIMIT,
    RATIO_LIMIT,
    score_walked_records,
)
from locfinder.metros import get_metro  # noqa: E402

#: Columns the predicate reads. A sheet missing any of them cannot produce an admissible record, so
#: scoring it would report "no admissible observation" for the wrong reason entirely.
REQUIRED = (
    "journey_id", "row", "col", "encoded_minutes",
    "start_lon", "start_lat", "destination_used", "predicted_destination",
    "route_followed", "walked_seconds", "duration_timed",
    # Added after Codex pass 51. `walked_date` and the four observation columns say a walk
    # HAPPENED even when no duration was recorded (A1); the arrival coordinate and the
    # alternatives identify the shop rather than labelling it (A2); `route_identified` is the
    # structured half of the approach question, since prose cannot be checked (A3).
    "walked_date", "destination_qualifies", "destination_open", "route_usable",
    "witness_within_10min", "witness_within_15min",
    "destination_used_lon", "destination_used_lat",
    "predicted_destination_lat", "predicted_destination_lon",
    "predicted_destination_alternatives",
    "predicted_destination_alternatives_lonlat", "route_identified",
)

#: `yes`/`no` as the sheet spells them. Anything else is **not** read as a no: an unrecognised value
#: means the record does not say, which is what the blank means too.
YES = {"yes", "y", "true"}
NO = {"no", "n", "false"}


class Refused(SystemExit):
    """Raised instead of producing a score whose inputs are not what they look like."""


def tri_state(value: str | None) -> bool | None:
    text = (value or "").strip().lower()
    if text in YES:
        return True
    if text in NO:
        return False
    return None


def blank_to_none(value: str | None) -> str | None:
    text = (value or "").strip()
    return text or None


def alternatives(names: str | None, lonlats: str | None) -> tuple[PermittedPlace, ...]:
    """The other places on the selected node, each paired with its own coordinate.

    `recover_audit_destinations.py` writes `"; ".join(...)` for both columns in the same order. A
    name with no coordinate is kept as a `PermittedPlace` with `lon`/`lat` `None`: the predicate
    then refuses an arrival that claims to be it, which is the honest outcome for a sheet produced
    before the coordinate column existed. **The lists are zipped, never indexed separately**, and
    a length mismatch raises rather than silently pairing a name with another place's location
    (pass 52 F3).
    """
    def split(value):
        text = (value or "").strip()
        if not text:
            return []
        return [part.strip() for part in text.split(ALTERNATIVES_SEPARATOR) if part.strip()]

    got_names = split(names)
    got_lonlats = split(lonlats)
    if got_lonlats and len(got_lonlats) != len(got_names):
        raise Refused(
            f"{len(got_names)} alternative names and {len(got_lonlats)} coordinates; they are "
            "written in the same order and must be the same length, or a name would be paired "
            "with another place's location")
    out = []
    for i, name in enumerate(got_names):
        lon = lat = None
        if i < len(got_lonlats):
            parts = got_lonlats[i].split(",")
            if len(parts) != 2:
                raise Refused(f"alternative coordinate {got_lonlats[i]!r} is not 'lon,lat'")
            lon, lat = parts[0].strip(), parts[1].strip()
        out.append(PermittedPlace(name=name, lon=lon or None, lat=lat or None))
    return tuple(out)


def record_for(row: dict, *, label_column: str = "journey_id") -> WalkedRecord:
    minutes = blank_to_none(row.get("encoded_minutes"))
    walked = blank_to_none(row.get("walked_seconds"))
    return WalkedRecord(
        label=row[label_column],
        row=int(row["row"]),
        col=int(row["col"]),
        reported_s=reported_seconds(int(minutes)) if minutes is not None else None,
        walked_seconds=float(walked) if walked is not None else None,
        duration_timed=tri_state(row.get("duration_timed")),
        start_lon=blank_to_none(row.get("start_lon")),
        start_lat=blank_to_none(row.get("start_lat")),
        destination_used=blank_to_none(row.get("destination_used")),
        destination_used_lon=blank_to_none(row.get("destination_used_lon")),
        destination_used_lat=blank_to_none(row.get("destination_used_lat")),
        predicted_destination=blank_to_none(row.get("predicted_destination")),
        predicted_destination_lon=blank_to_none(row.get("predicted_destination_lon")),
        predicted_destination_lat=blank_to_none(row.get("predicted_destination_lat")),
        destination_alternatives=alternatives(
            row.get("predicted_destination_alternatives"),
            row.get("predicted_destination_alternatives_lonlat")),
        route_followed=blank_to_none(row.get("route_followed")),
        route_identified=tri_state(row.get("route_identified")),
        # Evidence that a walk happened, carried so a walk with no duration cannot be filed as
        # "planned, not walked" (pass 51 A1).
        walked_date=blank_to_none(row.get("walked_date")),
        destination_qualifies=blank_to_none(row.get("destination_qualifies")),
        destination_open=blank_to_none(row.get("destination_open")),
        route_usable=blank_to_none(row.get("route_usable")),
        witness_within_10min=blank_to_none(row.get("witness_within_10min")),
        witness_within_15min=blank_to_none(row.get("witness_within_15min")),
    )


def short_name(path: Path) -> str:
    """A readable artifact name for a sheet: `chapelhill`, or `metro` for the unrestricted draw."""
    stem = path.stem
    for drop in ("triangle-grocery-walk", "-with-destinations"):
        stem = stem.replace(drop, "")
    return stem.strip("-") or "metro"


def read_sheet(path: Path) -> list[WalkedRecord]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        header = list(reader.fieldnames or ())
        rows = list(reader)
    missing = [c for c in REQUIRED if c not in header]
    if missing:
        # **Not "regenerate it"** -- pass 52 finding F7. `audit_recommendations.py` writes every
        # owner column blank, so the only way past its overwrite guard destroys a filled sheet's
        # observations. `migrate_audit_sheet.py` adds the missing columns and changes nothing else.
        raise Refused(
            f"{path.name} has no {', '.join(missing)} column, so the walks it records cannot be "
            "scored. Add the missing columns without touching anything already recorded:\n"
            f"    python scripts/migrate_audit_sheet.py {path}\n"
            "Do NOT regenerate the sheet: that writes every owner column blank."
        )
    if not rows:
        raise Refused(f"{path.name} has no rows")
    return [record_for(r) for r in rows]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("sheet", type=Path, help="a walked-audit sheet CSV")
    ap.add_argument("--metro", default="triangle")
    ap.add_argument("--out", type=Path, default=None,
                    help="where to write the JSON record (default: docs/experiments/)")
    args = ap.parse_args(argv)

    records = read_sheet(args.sheet)
    grid = get_metro(args.metro).grid()
    result = score_walked_records(records, grid=grid)

    print(f"{args.sheet.name}: {len(records)} rows")
    print(f"  scored          {result.walked} walked, {result.planned} planned and not walked")
    print(f"  refused         {len(result.inadmissible)} walked, not admissible")
    print(f"  no claim        {len(result.without_a_published_time)} rows the product did not answer")
    print()
    print(f"  E3 outcome      {result.outcome.value}"
          + ("  (no admissible observation)" if result.no_admissible_observation else ""))
    for reason in result.reasons:
        print(f"    - {reason}")
    if result.median_difference_s is not None:
        print(f"  median signed   {result.median_difference_s / 60.0:+.2f} min against a limit of "
              f"{result.median_limit_s / 60.0:.2f} min")
    else:
        print("  median signed   none: no admissible walk to take a median over")

    if result.inadmissible:
        print()
        print("  Refused, and why. Each line is a thing the record does not document:")
        for item in result.inadmissible:
            print(f"    {item.label}")
            for reason in item.reasons:
                print(f"      - {reason}")
    if result.without_a_published_time:
        print()
        print("  No published time, so no claim to test: "
              + ", ".join(result.without_a_published_time))

    out = args.out or (V2.parent / "docs" / "experiments"
                       / f"s3-e3-admissibility-{short_name(args.sheet)}.json")
    payload = {
        "script": "v2/scripts/score_walked_audit.py",
        "sheet": args.sheet.name,
        "metro": args.metro,
        "rows": len(records),
        "reported_time_is": "the published whole minute, in seconds, not the model's float "
                            "(docs/s3-decision-report.md)",
        "limits": {
            "single_journey_ratio": RATIO_LIMIT,
            "single_journey_absolute_s": ABSOLUTE_LIMIT_S,
            "median_share_of_reported": MEDIAN_SHARE_LIMIT,
        },
        "outcome": result.outcome.value,
        "no_admissible_observation": result.no_admissible_observation,
        "reasons": list(result.reasons),
        "walked_and_scored": result.walked,
        "planned_not_walked": result.planned,
        "median_difference_s": result.median_difference_s,
        "median_reported_s": result.median_reported_s,
        "median_limit_s": result.median_limit_s,
        "offending": list(result.offending),
        "refused": [asdict(i) for i in result.inadmissible],
        "without_a_published_time": list(result.without_a_published_time),
        "what_this_does_not_establish": (
            "Admissibility is not agreement. A refused walk is not evidence the product was right, "
            "and an admissible one that does not trip either limb is not evidence that it was: E3 "
            "returns FAILED or UNVERIFIED and never 'supported'."
        ),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print()
    print(f"  wrote {out.relative_to(V2.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
