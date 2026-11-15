"""Add missing columns to a walked-audit sheet without touching a single recorded observation.

**Pass 52 finding F7.** `score_walked_audit.py` refuses a sheet that lacks a column the
admissibility predicate reads, and told the owner to regenerate with
`audit_recommendations.py` — which writes every owner column blank. Its overwrite guard prevents
the damage until somebody passes `--force`, and then a filled sheet's observations are gone.
Regenerating also redraws nothing and re-runs no destination recovery. **"Regenerate it" is not a
migration for a file somebody has filled in.**

What this does, and only this:

* inserts any missing column from `audit_recommendations.OWNER_COLUMNS` and the destination
  columns, each **in its canonical position**, blank;
* keeps every existing value, every existing column, and every column the owner added themselves;
* writes to a new file by default, so the original is still there if the result is wrong;
* refuses rather than guessing when the sheet does not look like an audit sheet at all.

It is idempotent: running it on an already-migrated sheet reports that there is nothing to do.

Run from `v2/`:

    python scripts/migrate_audit_sheet.py ../docs/experiments/audit/my-filled-sheet.csv
    python scripts/migrate_audit_sheet.py --in-place ../docs/experiments/audit/sheet.csv
"""
from __future__ import annotations

import argparse
import csv
import shutil
import sys
from pathlib import Path

V2 = Path(__file__).resolve().parents[1]
if str(V2) not in sys.path:
    sys.path.insert(0, str(V2))

from scripts.audit_recommendations import OWNER_COLUMNS  # noqa: E402
from scripts.recover_audit_destinations import NEW_COLUMNS as DESTINATION_COLUMNS  # noqa: E402

#: Columns that must exist for a file to be an audit sheet at all. Without these there is nothing
#: to migrate and the file is something else.
IDENTIFYING = ("journey_id", "row", "col", "seconds", "encoded_minutes")

#: Where each column belongs, as the generators write them: the column it follows. A sheet is
#: migrated by inserting after an anchor rather than appending, so a migrated sheet and a freshly
#: generated one have the same column order and diff cleanly against each other.
def canonical_order() -> list[str]:
    """The full column list a current sheet has, destinations included."""
    return list(OWNER_COLUMNS), list(DESTINATION_COLUMNS)


class Refused(SystemExit):
    """Raised instead of writing a file whose observations might not survive."""


def insert_after(header: list[str], column: str, canonical: list[str]) -> list[str]:
    """Put `column` where its canonical neighbours say it goes.

    Walk backwards through the canonical list for the nearest preceding column this sheet already
    has, and insert after it. If none is present the column goes at the end, which is correct for
    a sheet that has none of that group.
    """
    i = canonical.index(column)
    for earlier in reversed(canonical[:i]):
        if earlier in header:
            header.insert(header.index(earlier) + 1, column)
            return header
    header.append(column)
    return header


def migrate(path: Path, out: Path, *, in_place: bool) -> int:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        header = list(reader.fieldnames or ())
        rows = list(reader)

    missing_id = [c for c in IDENTIFYING if c not in header]
    if missing_id:
        raise Refused(f"{path.name} has no {', '.join(missing_id)} column, so it is not a "
                      "walked-audit sheet and this script will not rewrite it")
    if not rows:
        raise Refused(f"{path.name} has no rows")

    owner, destinations = canonical_order()
    # The destination columns are only expected where the sheet already carries them: a bare draw
    # has never been through `recover_audit_destinations.py` and should not gain empty ones.
    groups = [owner]
    if any(c in header for c in destinations):
        groups.append(destinations)

    added = []
    for canonical in groups:
        for column in canonical:
            if column in header:
                continue
            insert_after(header, column, canonical)
            for row in rows:
                row[column] = ""
            added.append(column)

    if not added:
        print(f"{path.name}: already has every column this version reads; nothing to do")
        return 0

    # Every value that was there must still be there. Checked rather than asserted in a comment,
    # because the whole point of this script is not losing an observation.
    before = {(r["journey_id"], k): v for r in rows for k, v in r.items() if k not in added}
    target = path if in_place else out
    if in_place:
        backup = path.with_suffix(path.suffix + ".before-migration")
        shutil.copy2(path, backup)
        print(f"  kept the original at {backup.name}")
    with target.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=header)
        w.writeheader()
        w.writerows(rows)

    with target.open(newline="", encoding="utf-8-sig") as fh:
        written = list(csv.DictReader(fh))
    after = {(r["journey_id"], k): v for r in written for k, v in r.items() if k not in added}
    if after != before:
        differing = [k for k in before if before.get(k) != after.get(k)]
        raise Refused(f"the migration changed {len(differing)} existing values, for example "
                      f"{differing[:3]} -- {target.name} must not be used")
    if len(written) != len(rows):
        raise Refused(f"{len(written)} rows written against {len(rows)} read")

    filled = sum(1 for r in written if (r.get("walked_seconds") or "").strip()
                 or (r.get("walked_date") or "").strip())
    print(f"{path.name} -> {target.name}")
    print(f"  added {len(added)} column(s): {', '.join(added)}")
    print(f"  {len(written)} rows preserved, {filled} of them with a walk recorded, "
          f"{len(header)} columns")
    print("  every pre-existing value was read back and compared; none changed")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("sheet", type=Path)
    ap.add_argument("--out", type=Path, default=None,
                    help="where to write (default: alongside, with .migrated before the suffix)")
    ap.add_argument("--in-place", action="store_true",
                    help="rewrite the sheet itself, keeping a .before-migration copy")
    args = ap.parse_args(argv)
    if not args.sheet.exists():
        raise Refused(f"{args.sheet} does not exist")
    out = args.out or args.sheet.with_suffix(".migrated" + args.sheet.suffix)
    return migrate(args.sheet, out, in_place=args.in_place)


if __name__ == "__main__":
    raise SystemExit(main())
