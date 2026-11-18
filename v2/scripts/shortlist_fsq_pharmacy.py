"""Turn the 72 FSQ pharmacy confirmations into a reviewable shortlist, with the bad rows flagged.

**Owner decision 2026-11-18:** *"proceed with 1-3"*, of which this is the third -- re-derive the
pharmacy shortlist with the known-bad rows flagged in the `notes` column. **Not** in `verdict`:
that column is the owner's and stays blank.

**Why this is not just a filter on the coverage sheet.** The coverage run reported 72 `pharmacy`
proposals and called the positives corroborated. Reading the rows showed that is true of the set
and false of the members, so the name of the artefact matters: this writes
`pharmacy-fsq-shortlist.csv`, a SHORTLIST TO REVIEW, and deliberately not an
`FSQ_CONFIRMED_PHARMACY` table. Whether such a table should exist at all is still the owner's
decision.

**The rule it applies** is the one the accuracy run established
(`project-phase1-s3-fsq-accuracy.md`), which replaced "FSQ confirms, never rejects":

> A proposal is worth what its match is worth, and a proposal that denies what the record's own
> name asserts is evidence against the proposal.

For positive proposals that gives two independent screens -- the match quality, and whether the
record's own name (or a brand that is a pharmacy) agrees with the proposal. A row passing both is
corroborated twice over; a row failing either needs a human. Both screens are reported with their
REACH, so a clean run cannot be confused with a run that had nothing to check.

Run from `v2/`:
    python scripts/shortlist_fsq_pharmacy.py
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

V2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V2))
sys.path.insert(0, str(V2 / "scripts"))

from measure_fsq_coverage import AGREE, SELF_DESCRIBING  # noqa: E402

AUDIT = V2.parent / "docs" / "experiments" / "audit"

#: Brands that ARE pharmacies, so a bare brand name corroborates the proposal even though the name
#: carries no word asserting it. Kept short and explicit rather than inferred.
PHARMACY_BRANDS = (
    "cvs", "walgreens", "rite aid", "duane reade", "kroger", "harris teeter", "walmart",
    "target", "costco", "sam's club", "publix", "food lion", "kerr drug",
)

#: Rows established as wrong by inspection, with why. A flag computed from the data cannot catch
#: these, so they are listed -- and listed by id, so a re-run cannot lose them to a renamed record.
KNOWN_BAD: dict[str, str] = {
    "a6a8f2de-2465-4b1e-bb7e-87b8e6536199":
        "KNOWN FALSE POSITIVE. KBI Biopharma is a biologics contract development and "
        "manufacturing organisation in RTP, not a dispensing pharmacy; no household fills a "
        "prescription there. FSQ labels it `Retail > Pharmacy` at 0.0 m with name agreement 1.00, "
        "so BOTH screens below pass and both are wrong. Our own candidate list carries the same "
        "record. Established 2026-11-18.",
}


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--source", type=Path, default=AUDIT / "pharmacy-fsq-coverage.csv")
    ap.add_argument("--out", type=Path, default=AUDIT / "pharmacy-fsq-shortlist.csv")
    args = ap.parse_args()

    pattern, _denial = SELF_DESCRIBING["pharmacy"]
    asserts = re.compile(pattern, re.I)

    with open(args.source, encoding="utf-8-sig", newline="") as handle:
        source = list(csv.DictReader(handle))
    confirmations = [r for r in source if r["proposal"].strip() == "pharmacy"]
    print(f"{args.source.name}: {len(source)} rows, {len(confirmations)} `pharmacy` proposals")

    rows: list[dict] = []
    weak_match = weak_name = known_bad = clean = 0
    for rec in confirmations:
        agreement = float(rec["name_agreement"] or 0)
        name = rec["name"] or ""
        flags: list[str] = []

        if rec["id"] in KNOWN_BAD:
            flags.append(KNOWN_BAD[rec["id"]])
            known_bad += 1

        if agreement < AGREE:
            flags.append(
                f"PROXIMITY ONLY: name agreement {agreement:.2f} is below the {AGREE} threshold, "
                f"so the FSQ match at {rec['distance_m']} m may be a neighbour rather than this "
                f"business. Matched FSQ name: {rec['fsq_name']!r}."
            )
            weak_match += 1

        self_describing = bool(asserts.search(name))
        brand = next((b for b in PHARMACY_BRANDS if b in name.lower()), "")
        if not self_describing and not brand:
            flags.append(
                "NAME DOES NOT ASSERT PHARMACY: the record's own name neither says pharmacy nor "
                "names a brand that is one, so the proposal rests on FSQ's category alone -- and "
                "FSQ's categories were measured wrong at name agreement 1.00 elsewhere."
            )
            weak_name += 1

        if not flags:
            clean += 1
            why = ("the record's own name asserts pharmacy" if self_describing
                   else f"{brand!r} is a pharmacy brand")
            note = f"corroborated twice: {why}, and the FSQ match agrees on name ({agreement:.2f})."
        else:
            note = "  ||  ".join(flags)

        out = dict(rec)
        out["notes"] = note
        out["needs_a_human"] = "yes" if flags else ""
        out["verdict"] = ""
        rows.append(out)

    rows.sort(key=lambda r: (r["needs_a_human"] == "", -float(r["name_agreement"] or 0)))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    flagged = sum(1 for r in rows if r["needs_a_human"])
    print(f"\n  {clean:3} corroborated twice over -- name and match both agree")
    print(f"  {flagged:3} need a human")
    print("\n  SCREENS (reach reported, so a clean run is not confused with an idle one):")
    print(f"  [gate] match quality, agreement < {AGREE}: reached {len(confirmations)}, "
          f"found {weak_match}")
    print(f"  [gate] name does not assert pharmacy:     reached {len(confirmations)}, "
          f"found {weak_name}")
    print(f"  [gate] listed as known-bad by inspection: reached {len(KNOWN_BAD)}, "
          f"found {known_bad}")
    if known_bad < len(KNOWN_BAD):
        missing = set(KNOWN_BAD) - {r["id"] for r in rows}
        print(f"         !! {len(missing)} known-bad id(s) are NOT in this run's confirmations: "
              f"{', '.join(sorted(missing))}")
        print("            Either the source sheet changed or the proposal did. Check before "
              "trusting the counts.")
    print(f"\nwrote {args.out}")
    print("The `verdict` column is blank. No table was edited, and this is a SHORTLIST, "
          "not a confirmed set.")


if __name__ == "__main__":
    main()
