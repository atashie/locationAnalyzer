"""Place records excluded by an owner decision about what the thing IS, not by a tag.

Overture's taxonomy answers "is this record categorised as a park". It does not answer "is this a
park", and for a handful of records those differ in a way no tag in the data distinguishes. Those
records are listed here, by stable Overture id, each with the evidence and the decision that
removed it, so the judgement is reviewable in a diff rather than buried in a builder.

**Why a list and not a rule.** The obvious rule -- drop a park record whose containing OSM polygons
carry no park designation -- was measured before it was written. It would drop **25** records, and
almost all are real parks that happen to sit inside a school ground or a state recreation area
whose OSM polygon lacks the tag: Lynn Road Park, Barwell Road Park, Dixon Drive Park, Anderson
Community Park, Sandling Beach State Recreation Area, Falls Dam Playground. It would delete about
twenty-three genuine parks to remove two. OSM's designation tagging is not consistent enough to
carry a general rule here, and a rule that is wrong twenty-three times out of twenty-five is worse
than no rule.

Keep this list short. If it grows past a handful, that is evidence the acceptance stage needs a
real screen and this file has become a place to hide the need for one.
"""
from __future__ import annotations

#: Overture place id -> why it is not what its taxonomy says, and whose decision removed it.
#:
#: Each entry must carry enough for a reader to re-check it without this module: what the record
#: claims to be, what the evidence says it is, and the date of the decision.
EXCLUDED_PLACE_IDS: dict[str, str] = {
    "5a1c8da5-ce62-41fc-af4a-fa2c0c4bd703":
        "'Shearon  Harris Lake', taxonomy primary=park. It is the cooling reservoir of the Harris "
        "Nuclear Plant, not a park. The only OSM polygon containing it is 'Duke Energy: Harris "
        "Nuclear Plant' (leisure=nature_reserve, 9,627.8 ha), which carries no park designation, "
        "no access tag and no parks operator. Seven of the nine accepted park records on that site "
        "DO fall inside 'Harris Lake County Park' (leisure=park, access=yes, ownership=county) and "
        "are kept. Owner decision 2026-11-17: designated as a public park yes, open space that is "
        "not designated a park no.",
    "dc218eca-83a0-4889-acde-0ec39b54224d":
        "'Shearon Harris Reservoir', taxonomy primary=park. The same water body as the record "
        "above under another name, and the same evidence: contained only by 'Duke Energy: Harris "
        "Nuclear Plant', outside 'Harris Lake County Park'. Owner decision 2026-11-17.",
    "81190996-0ac4-401f-817a-a9ebff1af58c":
        "Kroger, grocery. Overture marks it permanently_closed, and unlike the eight below the "
        "signal is strong: it comes from `Overture-signals` at confidence 1.0 rather than from a "
        "business registry, and OSM shows a `shop=supermarket` named Harris Teeter operating at "
        "the same spot. So the Kroger closed and somebody else trades there -- routing a "
        "household to 'Kroger' names a shop that is not there. Owner decision 2026-11-17: drop "
        "this one, hold the other eight.",
}

#: Closures Overture asserts that we are NOT acting on, with why. Recorded rather than applied.
#:
#: **All eight come from BrightQuery**, a business-registry provider: every one carries confidence
#: 0.55-0.65 and the same single update time, and the signal is about a legal entity rather than
#: an observation of a storefront. An entity can deregister while the shop trades on under new
#: ownership, and it can be registered at an address that was never a shop.
#:
#: Of the eight, two have a different shop within 100 m in OSM and six have no OSM shop within
#: 100 m at all -- which is weak evidence in both directions, because OSM's coverage of small
#: independent grocers is itself patchy.
#:
#: Owner decision 2026-11-17: hold them as pending. The owner also raised building a closure
#: **likelihood index** from several sources (OSM, Google, Yelp) rather than a yes/no list; that
#: is not built, and it carries a licensing question -- Google output may be queried live for
#: validation but must not be persisted as a dataset.
PENDING_CLOSURES: dict[str, str] = {
    "0d5215b0-3192-4bc8-aee5-d5ba6fdb2973":
        "La Tiendita Market. BrightQuery, confidence 0.65. OSM has a `shop=supermarket` named "
        "'ktown market' within 100 m, so something trades there under another name.",
    "27b4e2f0-fc2a-442f-be32-afdaad6fb309":
        "Kinstar International Food Inc. BrightQuery, confidence 0.65. OSM has a "
        "`shop=convenience` named 'Little India' within 100 m -- a different business.",
    "3fed30d2-7538-4f0f-aece-e77ab3a4d484":
        "Carolina Cupboard. BrightQuery, confidence 0.55 -- the lowest of the nine. No OSM shop "
        "within 100 m.",
    "4f318935-7d66-4a5e-833a-1131fdf4b4fe":
        "Longview Poole Road. BrightQuery, confidence 0.65. The name is a street, not a shop, "
        "which is what a registry record looks like. No OSM shop within 100 m.",
    "a4cd9c69-95d2-4170-8433-c5e48adc9406":
        "Bell Tower Mart. BrightQuery, confidence 0.65. No OSM shop within 100 m.",
    "b7b9f517-7f58-4a53-abd2-ac8620a93726":
        "Jinja Fair Trade Llc. BrightQuery, confidence 0.65. 'Llc' in the name is the registry "
        "showing through. No OSM shop within 100 m.",
    "dc09b073-d0ac-4141-8275-3127c748878d":
        "Roofing Inc. BrightQuery, confidence 0.65. **Not a grocery under any definition** -- it "
        "is a roofing company classified as a grocery store, and the closure flag is incidental "
        "to the real defect. See `scripts/measure_classification_errors.py`.",
    "fa488537-1065-4f10-80e6-8e7d978375fb":
        "La Nueva Mexicana. BrightQuery, confidence 0.65. No OSM shop within 100 m.",
}


#: Closures FSQ asserts that we ARE acting on. Ten records, by stable Overture id.
#:
#: Owner decision 2026-11-18: *"accept the 10 closures"*. The measurement
#: (`scripts/measure_fsq_coverage.py`, results in
#: `docs/engineering-notes/project-phase1-s3-fsq-coverage.md`) found 25 records FSQ marks closed,
#: of which **12** both agree on name and sit within 60 m. **All twelve are applied.** Ten were
#: accepted first; the other two were held for a day pending an OSM cross-check, and the owner
#: released both once it had run -- *"1-4) yes, proceed"*. They are the last two entries, and each
#: records what the cross-check found, INCLUDING, for Sam's Club, the objection it did not answer.
#:
#: **Why this table is separate from `EXCLUDED_PLACE_IDS` above.** Same reason
#: `OSM_CONFIRMED_SUPERMARKETS` is separate from `CURATED_INDEPENDENT_SUPERMARKETS`: this is a
#: REGENERABLE DERIVATION from a dated third-party snapshot, and a hand-made judgement is not. Re-run
#: the script against a newer FSQ release and this set moves; a curated entry is somebody's decision
#: and must not be overwritten by a data refresh.
#:
#: **What `date_closed` is and is not.** The snapshot is FSQ OS Places 2025-01-10, so every date is
#: a LOWER BOUND -- a shop that closed after that release still looks open here, and the absence of
#: a date is not evidence of trading. The dates are also not independently verified; what makes
#: them usable is that `date_closed` is a field neither OSM nor Overture carries at all, so unlike
#: FSQ's CATEGORIES it cannot be an echo of our own Overture-derived data. FSQ's categories are
#: reliable in one direction only and must never reject a record; see the coverage note.
#:
#: Licence: FSQ OS Places is Apache-2.0 with attribution. It is cleared for our own ODbL layers and
#: NOT for upload into OpenStreetMap, which needs explicit import permission. Decision 17 stands.
FSQ_CONFIRMED_CLOSURES: dict[str, str] = {
    "790e99cf-ceef-415a-babb-849e75732fa4":
        "'Kroger', grocery. FSQ OS Places 2025-01-10 carries date_closed=2013-06-25 on 'Kroger' at 0.0 "
        "m with name agreement 1.00. Owner decision 2026-11-18. Corroborates the OTHER Kroger dropped "
        "above, which was decided on independent Overture-signals evidence rather than on FSQ.",
    "3e8b0d81-ca69-4cd5-9948-c8d858ff0a59":
        "'Southern Season', grocery. FSQ OS Places 2025-01-10 carries date_closed=2016-09-27 on "
        "'Southern Season' at 6.3 m with name agreement 1.00. Owner decision 2026-11-18. FSQ files it "
        "under Business and Professional Services rather than food retail, so the CATEGORY is "
        "unreliable here; only the closure is being taken.",
    "4fe3f836-f1f6-45e9-9553-a92a6c9f8752":
        "'El Atoron', grocery. FSQ OS Places 2025-01-10 carries date_closed=2024-06-26 on 'El Atoron' "
        "at 19.4 m with name agreement 1.00. Owner decision 2026-11-18.",
    "2f30a8c1-497f-4ca7-9be4-0654fe808c57":
        "'Family Market', grocery. FSQ OS Places 2025-01-10 carries date_closed=2024-07-07 on 'Family "
        "Market' at 0.0 m with name agreement 1.00. Owner decision 2026-11-18.",
    "0aa4c24d-6a8f-4d54-a1b3-bd684db6bbfc":
        "'Usf Sales', grocery. FSQ OS Places 2025-01-10 carries date_closed=2024-11-04 on 'Usf Sales' "
        "at 0.0 m with name agreement 1.00. Owner decision 2026-11-18.",
    "d3de68dd-7695-47a3-bff5-ece45da1a8b1":
        "'Kroger Pharmacy', pharmacy. FSQ OS Places 2025-01-10 carries date_closed=2019-08-02 on "
        "'Kroger Pharmacy' at 0.0 m with name agreement 1.00. Owner decision 2026-11-18. The pharmacy "
        "counter of the same chain, and the second record corroborating the owner's earlier Kroger "
        "call.",
    "f389d1a5-5f4a-48a5-8055-e00206faba86":
        "'Rite Aid', pharmacy. FSQ OS Places 2025-01-10 carries date_closed=2020-02-11 on 'Rite Aid' at "
        "53.3 m with name agreement 1.00. Owner decision 2026-11-18.",
    "837e9f0d-d5b0-4e16-b3c4-9119c9700e9a":
        "'Walgreens Pharmacy', pharmacy. FSQ OS Places 2025-01-10 carries date_closed=2021-02-08 on "
        "'Walgreens' at 1.2 m with name agreement 1.00. Owner decision 2026-11-18.",
    "6ee316ab-d82f-4890-9a1e-84874d0438c7":
        "'Walgreens', pharmacy. FSQ OS Places 2025-01-10 carries date_closed=2021-03-13 on 'Walgreens' "
        "at 4.8 m with name agreement 1.00. Owner decision 2026-11-18.",
    "13e62ef8-c843-42c7-8be0-7bbaa070a70d":
        "'Rite Aid', pharmacy. FSQ OS Places 2025-01-10 carries date_closed=2024-01-26 on 'Rite Aid' at "
        "45.0 m with name agreement 1.00. Owner decision 2026-11-18.",
    # ---- accepted on the second pass the same day, after the cross-check ran ----
    "c7c31e4e-79a8-43d3-aa0c-4c1bf098747e":
        "'Sam's Club', pharmacy candidate. FSQ OS Places 2025-01-10 carries date_closed=2018-02-03 "
        "at 37.6 m with name agreement 1.00. Owner decision 2026-11-18, second pass. **THE "
        "CATEGORY OBJECTION IS NOT RESOLVED**: FSQ's closed record is categorised `Retail > "
        "Warehouse or Wholesale Store` -- the CLUB, not a pharmacy counter -- and a counter that "
        "closes inside a club which keeps trading is indistinguishable in this data from the whole "
        "club closing. The cross-check (`scripts/crosscheck_fsq_closures.py`) added only that OSM "
        "holds no Sam's Club within 300 m, nearest tagged retail a Walmart Supercenter at 279.7 m. "
        "That is CONSISTENT with the club having closed, but it is absence rather than "
        "observation. Accepted over the stated doubt; if this record is ever disputed, this "
        "sentence is the reason why.",
    "1937d785-1a98-49c5-9d32-51b7ec7c97af":
        "'Harris Teeter', grocery. FSQ OS Places 2025-01-10 carries date_closed=2017-09-25 on "
        "'Harris Teeter' at 0.0 m with name agreement 1.00. Owner decision 2026-11-18, second "
        "pass. Held for one day because another Kroger in `EXCLUDED_PLACE_IDS` above was dropped "
        "precisely BECAUSE OSM shows a Harris Teeter trading on its site, so a closed Harris "
        "Teeter had to be shown to be a different address before a second store came out. The "
        "cross-check (`scripts/crosscheck_fsq_closures.py`) found it 15,249 m from that Kroger and "
        "23,476 m from the Kroger accepted above -- three different sites, so the hold had no "
        "subject. OSM is silent within 120 m and holds no Harris Teeter within 300 m.",
}


#: **EMPTY, and kept rather than deleted.** For one day this held the two of the twelve that were
#: not applied. The cross-check in `scripts/crosscheck_fsq_closures.py` ran, both went back to the
#: owner with what it found, and both were released -- *"1-4) yes, proceed"*, 2026-11-18. Their
#: entries moved into `FSQ_CONFIRMED_CLOSURES` above and carry the cross-check with them.
#:
#: The name stays so that a later session reads "this was held and then decided" instead of
#: finding nothing and having to reconstruct whether a hold ever existed. The empty dict is also
#: what the tests assert on, which is why it is not a comment.
FSQ_CLOSURES_HELD: dict[str, str] = {}


#: Everything actually removed, from every table that removes anything. One name so a reader can
#: see the whole effect in one place, and so adding a table cannot forget to apply it.
#:
#: `PENDING_CLOSURES` is deliberately NOT here: it records closures we are not acting on, and
#: folding it in would quietly reverse a decision. `FSQ_CLOSURES_HELD` is now empty, so it would
#: contribute nothing; it is still left out, because the day it stops being empty it would
#: otherwise start removing records nobody had agreed to remove.
DROPPED_PLACE_IDS: frozenset[str] = frozenset(EXCLUDED_PLACE_IDS) | frozenset(
    FSQ_CONFIRMED_CLOSURES
)


def drop_excluded(gdf):
    """Remove any listed record. A no-op on a frame with no `id` column.

    Frames from `select_named` are built by hand and carry no Overture id, so the absence of the
    column is normal rather than an error worth raising on.
    """
    if "id" not in getattr(gdf, "columns", ()):
        return gdf
    return gdf[~gdf["id"].isin(DROPPED_PLACE_IDS)]
