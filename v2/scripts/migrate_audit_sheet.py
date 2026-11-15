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


def read_positionally(path: Path) -> tuple[list[str], list[list[str]]]:
    """The header and the rows as LISTS, which is the only lossless reading of a CSV.

    **Pass 53 finding F3.** This used `csv.DictReader`, and a duplicate header -- two `notes`
    columns, which is exactly what an owner adding a column of their own produces -- makes it keep
    only the LAST value. The `before` snapshot was then built from that same already-lossy read,
    so the read-back comparison succeeded and the script printed "every pre-existing value was
    read back and compared; none changed" while a value was gone.

    A verification that reads its expectation through the same lossy path as the thing it verifies
    confirms the path, not the data.
    """
    with path.open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.reader(fh))
    if not rows:
        raise Refused(f"{path.name} is empty")
    return rows[0], rows[1:]


def migrate(path: Path, out: Path, *, in_place: bool) -> int:
    header, body = read_positionally(path)

    # Duplicate headers are refused rather than migrated. Whatever the right answer is for a sheet
    # with two `notes` columns, it is not "pick one and copy it over the other".
    duplicates = sorted({c for c in header if header.count(c) > 1})
    if duplicates:
        raise Refused(
            f"{path.name} has more than one column called {', '.join(duplicates)}. Rename or "
            "remove the duplicate first: this script cannot tell which one your observations are "
            "in, and guessing would overwrite one with the other")

    # A row with more fields than the header has values with no column. `DictWriter` would raise
    # on them -- but only AFTER opening and truncating the target, which with `--out` pointing at
    # the input leaves nothing at all.
    wide = [i + 2 for i, r in enumerate(body) if len(r) > len(header)]
    if wide:
        raise Refused(
            f"{path.name} line(s) {wide[:5]} have more fields than the header has columns, so "
            "some values are in no column at all. Fix the file first; this script will not guess "
            "which column they belong to")

    missing_id = [c for c in IDENTIFYING if c not in header]
    if missing_id:
        raise Refused(f"{path.name} has no {', '.join(missing_id)} column, so it is not a "
                      "walked-audit sheet and this script will not rewrite it")
    if not body:
        raise Refused(f"{path.name} has no rows")
    # Short rows are padded, which is a CSV writer's own behaviour and loses nothing.
    rows = [{c: (r[i] if i < len(r) else "") for i, c in enumerate(header)} for r in body]

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

    # **The snapshot is positional**, so it cannot have dropped anything a duplicate column or a
    # repeated `journey_id` would hide. Keyed on the row's index and the column's index, not on a
    # value from the row (pass 53 F3: two rows labelled `x` collapsed to one key).
    before = {(i, c): r[c] for i, r in enumerate(rows) for c in header if c not in added}

    target = path if in_place else out
    # **Nothing is overwritten, and nothing is written in place** -- pass 53 F4. Three paths were
    # destructive: the default output silently overwrote a `.migrated.csv` somebody had since
    # filled in; `--in-place` silently overwrote an existing `.before-migration`; and a malformed
    # row raised after the target had been truncated. So an existing target is refused, the backup
    # is refused if it exists, and the write goes to a temporary file that only replaces the
    # target once it has been read back and compared.
    if target.resolve() == path.resolve() and not in_place:
        raise Refused(f"the output is the input ({path.name}); pass --in-place if that is what "
                      "you mean, and it will keep a copy first")
    if not in_place and target.exists():
        raise Refused(f"{target.name} already exists, and it may be a sheet you have filled in "
                      "since migrating. Move it, or pass --out somewhere else")
    backup = None
    if in_place:
        backup = path.with_suffix(path.suffix + ".before-migration")
        if backup.exists():
            raise Refused(f"{backup.name} already exists, so writing one would overwrite the "
                          "only untouched copy. Move it first")

    scratch = target.with_suffix(target.suffix + ".partial")
    if scratch.exists():
        raise Refused(f"{scratch.name} is in the way; remove it")
    try:
        with scratch.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(header)
            for r in rows:
                w.writerow([r[c] for c in header])

        written_header, written_body = read_positionally(scratch)
        written = [{c: (r[i] if i < len(r) else "") for i, c in enumerate(written_header)}
                   for r in written_body]
        after = {(i, c): r[c] for i, r in enumerate(written) for c in header if c not in added}
        if after != before:
            differing = [k for k in before if before.get(k) != after.get(k)]
            raise Refused(f"the migration would change {len(differing)} existing values, for "
                          f"example {differing[:3]} -- nothing was written")
        if len(written) != len(rows):
            raise Refused(f"{len(written)} rows written against {len(rows)} read")
        if written_header != header:
            raise Refused("the written header is not the one that was built")

        if backup is not None:
            shutil.copy2(path, backup)
            print(f"  kept the original at {backup.name}")
        scratch.replace(target)
    finally:
        if scratch.exists():
            scratch.unlink()

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
