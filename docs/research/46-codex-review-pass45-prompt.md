# Codex adversarial review, pass 45 — the destination truth audit

You are an adversarial reviewer. Your job is to find what is wrong, not to confirm what is right.

Repository: `C:\Users\arikt\documents\github\distanceFinder`, branch `v2-rethink`, at commit
`b02d857`. Python: `v2/.venv/Scripts/python.exe`. **Do not create temporary directories inside the
repository** — pass pytest an explicit `--basetemp` outside it, or skip the full suite and say so.
A graph load takes about two minutes; `--no-impact` skips it.

## What to review: step 7's destination half

`v2/scripts/audit_destination_truth.py`, `docs/experiments/s3-7-destination-truth.md` and `.json`,
the sheet `docs/experiments/audit/s3-7-destinations-to-check.csv`, and the step 7 row and outcome
block in `docs/plans/2026-11-04-s3-execution-plan.md`.

Context: design §3's destination-validity blind spot, `v2/locfinder/places/categories.py`
(`WEDGE_CATEGORIES`, `select_overture`, `select_osm`), and
`docs/engineering-notes/project-phase1-s3-audit-destination-recovery.md`, which already found that
7 of 16 audit journeys route to a specialty market.

## The claims to attack, hardest first

**A. The one I am least comfortable with: I am proposing to trust Overture's closure flag.** The
report treats `operating_status == "permanently_closed"` as ground truth and prices removing those
nine places. But that field has its own error rate, and I have not measured or bounded it. If a
flag is stale and the shop is open, filtering it **removes a real destination** and wrongly
excludes households — the opposite harm, in the same direction as every other omission in this
report. Attack the asymmetry: is there evidence in the repository (the audit sheet, the recovery
note, OSM agreement, `confidence`) that bears on whether these nine are really shut? Does any of
the nine have an OSM supermarket at the same coordinate, which would be evidence **against** the
flag? Say whether the amendment should filter on this field at all, or require corroboration.

**B. Is "1,473 structures served only by a closed grocery" the right number and the right
counterfactual?** `impact()` compares `published` against `open_only`, where `open_only` drops only
`permanently_closed` and **keeps** the 106 places with no status at all. Check that choice. Check
the arithmetic too: nine stores accounting for 1,473 structures at ten minutes and **zero** at
forty-five is a shape worth explaining or refuting. And the structures are evaluated at their own
coordinates, not at cell centres — step 5 measured those differing on 2.2–2.5% of structures, so
say whether this unit is the right one for a harm statement about published answers.

**C. The brand table, which is the basis of the owner's decision.** Matching is
`brand.lower() in name.lower()` filtered to `STORE_PRIMARIES`. Attack it:
* false positives — does "Target" catch Target Optical, "BJ's" a BJ's Restaurant, "Fresh Market" a
  farmers' market? Does `STORE_PRIMARIES` including `None` admit rows that are not stores at all?
* false negatives — a store whose Overture name does not contain the brand string, or a brand
  present in the Triangle that my 21-name list omits. Is the list biased toward confirming the
  finding?
* **the "nine chains split across the wedge" claim is the sharpest thing in the report.** Verify it
  per chain. For each of Harris Teeter, Publix, Kroger, Aldi, Lidl, Trader Joe's, Whole Foods,
  Weaver Street and Compare Foods, is the "not in it" row an actual store of that chain, or a fuel
  station, pharmacy or concession that name matching dragged in? If even a few are concessions, the
  claim must be restated.

**D. The 49 store rows and their 4,318 / 7,128 structures.** Does `brand_candidates` build the set
the table describes? Are those rows deduplicated against each other and against the existing 550 —
two Overture rows for one Walmart would double-count a destination node. And does admitting them
change any *existing* answer for the worse, which the report does not consider?

**E. The OSM coverage comparison.** `SAME_SHOP_M = 300` is justified as the destination snap cap.
Attack that reasoning. Both sets are filtered to the footprint with a hand-written bounds test
rather than `GridSpec.cell_for_xy` — check it matches, including the half-open edges. Centroids are
taken of whatever geometry each source has, so an OSM building polygon and an Overture point for
one store could be 200 m apart; does that inflate or deflate the 28? And is `select_osm`'s
`shop=supermarket`/`greengrocer` the right comparator at all, given OSM also has `shop=grocery`
and `shop=convenience`?

**F. The claim that the two impact figures "overlap rather than adding".** I assert it from the top
of the sheet being the same stores as §2. Verify or refute it with a number: how much do the
structures gained from the OSM set and from the brand set actually overlap?

**G. The write-up.** Find any sentence stating more than the evidence supports, in the way your
passes 38–44 repeatedly did. Specifically: "needed no walk and no external source" (true?),
"resolution is not the problem" (does 75 places sharing a node really not matter?), "arbitrary, not
cautious", and the claim that the brand list "is not a general rule" — is that disclaimer enough,
or does the report still rest on it?

**H. What step 7 has not done.** The geocoding half is unstarted and the report says so. Is
anything else in §0's step 7 scope — "destination validity, resolution, coverage" — silently
unaddressed? Does `confidence` deserve more than the paragraph it gets?

## Output

For each finding: severity, the exact file and line, a **runnable reproducer**, and what it costs —
a number that moves, or a claim that must be withdrawn. Say which of my claims you checked and
could not break; that is as useful as a finding. If the nine closed places should not be filtered
on this evidence, say so in those words.
