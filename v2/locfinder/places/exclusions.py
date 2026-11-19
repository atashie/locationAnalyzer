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
    # ---- owner ask 3, 2026-11-18, PARTLY HELD 2026-11-19 ----
    #
    # The ask covered eleven records. ONE is removed here; the ten collection bays are HELD in
    # `HELD_SERVICE_POINTS` below after the fifth adversarial review. Published `grocery`
    # 543 -> 542.
    #
    # `grocery` is taxonomy-based and never calls `classify_grocery`, so `NOT_A_WEEKLY_SHOP_SITES`
    # governed `supermarket` alone while the published layer went on offering a meat-processing
    # plant as a grocery destination. The published cut is by explicit id with evidence per record.
    # The service-point SCREEN only ever DISCOVERED the candidates; what decides membership here is
    # evidence and an owner decision, which is the distinction the fifth review asked for and the
    # reason the id table is not merely a transcript of a heuristic.
    "1e99e399-b118-4d95-8c78-6770a47287c8":
        "'Weaver Street Market, Inc', taxonomy hierarchy=grocery_store. It is the co-op's FOOD HOUSE: a "
        "commercial kitchen, an NCDA-inspected meat-processing plant (P-317), two bakeries and warehousing "
        "that supply the four Weaver Street shops twice a day. A SUPPLIER, not a shop, and nothing in the "
        "data distinguishes them -- the name is the co-op's legal name, so it carries no service-point word "
        "for any screen to catch. Already in `NOT_A_WEEKLY_SHOP_SITES`, which governs `supermarket` only; "
        "this entry is what removes it from the PUBLISHED `grocery` layer. Nearest surviving grocery record "
        "0.0 m, 'Weaver Street Market Administration' -- an office at the SAME COORDINATE, which the "
        "destination audit has already seen chosen as a destination and which the owner has NOT decided on. "
        "**SO THIS REMOVAL DOES NOT RETIRE THE BAD DESTINATION LOCATION**, as the fifth review pointed out; "
        "it removes the record that claims to be a shop and leaves the one that claims to be an office. "
        "Found by the third adversarial review 2026-11-18, owner decision the same day, and KEPT when the "
        "ten bays beside it were held on 2026-11-19: a plant that supplies shops is not a shop by any "
        "reading of the owner's definition, and no judgement about shopping methods turns on it.",
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
#: of which **12** both agree on name and sit within 60 m. **Eleven are applied here and the
#: twelfth is flagged, not dropped** -- see `FSQ_FLAGGED_CLOSURES` below. Ten were accepted first;
#: the other two were held for a day pending an OSM cross-check and then released; then Sam's Club
#: was moved out of this table into the flag on a third pass, because it had been accepted over an
#: objection nobody had answered. The last entry here, Harris Teeter, records what the cross-check
#: found.
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
    "c7c31e4e-79a8-43d3-aa0c-4c1bf098747e":
        "'Sam's Club', pharmacy candidate. FSQ OS Places 2025-01-10 carries date_closed=2018-02-03 at 37.6 "
        "m with name agreement 1.00. **THE CATEGORY OBJECTION IS NOW RESOLVED, and by evidence from outside "
        "this dataset.** It was this: FSQ files the closed record under `Retail > Warehouse or Wholesale "
        "Store` -- the CLUB, not a pharmacy counter -- and a counter closing inside a club that keeps "
        "trading is indistinguishable in this data from the whole club closing. The answer is that THE "
        "WHOLE CLUB CLOSED. North Carolina's 2018 WARN report records Sam's Club #6668, notice 2018-01-11, "
        "EFFECTIVE 2018-01-26, 187 employees, closure type PERMANENT, at 1101 Shiloh Glenn Dr -- this "
        "record's own address; Walmart closed 63 clubs nationally that month. Contemporary reporting "
        "settles the pharmacy specifically: the pharmacies stayed open about two weeks while prescriptions "
        "were transferred. So the evidence is no longer OSM's SILENCE but an affirmative dated public "
        "filing, and the FSQ date sits five weeks after the effective date rather than standing alone. The "
        "cross-check (`scripts/crosscheck_fsq_closures.py`) still adds only that OSM holds no Sam's Club "
        "within 300 m, nearest tagged retail a Walmart Supercenter at 279.7 m. HISTORY, because the entry "
        "should say how it got here: applied on the owner's second pass 2026-11-18, turned into a flag on "
        "the third while the objection stood, applied again the same day once the third adversarial review "
        "found the WARN filing.",
    # ---- accepted on the second pass the same day, after the cross-check ran ----
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


#: Closures we BELIEVE but do not ACT ON. The record **stays in the layer**; the doubt travels
#: with it as data instead of as a comment in this file.
#:
#: **Owner decision 2026-11-18, third pass: *"1-4) yes, proceed"***, taking the argument an
#: adversarial review made against the second pass. Sam's Club had been applied that morning over
#: a category objection nobody had answered, and the review's point was that the entry then read
#: as settled while `DROPPED_PLACE_IDS` removed the record outright -- *"a publication risk, not a
#: demonstrated false closure"*. A flag keeps the record and keeps the doubt attached to it.
#:
#: **WHAT THIS COSTS, SAID PLAINLY.** Nothing renders this flag yet. Until something does, a
#: household searching for a pharmacy is routed to a place that is probably closed, with no
#: warning -- which is a worse outcome than the drop for that one household, and a better one for
#: the project, because the drop was asserting a fact we do not have. The flag is the honest
#: state; it is not yet the finished feature. `flagged_closure_reason` is the seam a renderer
#: would read, and it exists so that "surface the flag" is a UI change rather than a data change.
#: **EMPTY SINCE 2026-11-18, and kept.** Sam's Club was the one entry, for part of one day. The
#: third adversarial review then produced the thing the flag was waiting for -- a dated state
#: filing -- so the record moved into `FSQ_CONFIRMED_CLOSURES` above, where the doubt it carried
#: is answered rather than deleted.
#:
#: The table and `flagged_closure_reason` stay for the same reason `FSQ_CLOSURES_HELD` stays: the
#: mechanism was right, and the next genuinely uncertain closure belongs here rather than in a
#: comment. A later session reads "this was used and then resolved" instead of having to
#: reconstruct whether it ever existed.
FSQ_FLAGGED_CLOSURES: dict[str, str] = {}

#: Service-point records the service-point screen found, which we are NOT removing, and why.
#:
#: **OWNER DECISION 2026-11-19, reversing ask 3 for these ten.** They were removed in `ae89174`
#: and brought back the same week, after the fifth adversarial review measured what the removal
#: cost: SEVEN of the ten sites were left with no published grocery record at all, one of them with
#: nothing inside 2 km. Three of the ten have a survivor within 150 m; the first report said two,
#: which was wrong because `cee0e25b` sits at 147.9 m, inside the threshold.
#:
#: **THE ARGUMENT THAT WON, and it is not a defect argument.** A collection bay is not a shop you
#: walk round, but it IS a way to get a weekly shop: the household orders the same groceries and
#: collects them. So *"a collection bay is not a weekly shop"* is a policy judgement about which
#: shopping methods count, not a fact about food access. Against that, removing the bay erases the
#: only published record at its site while **the shop it serves is not in the layer to replace
#: it** -- so the removal is correct about the record and wrong about the place.
#:
#: **WHY THE SHOP IS MISSING, which is the real defect under all of this.** Overture files these
#: Walmart stores under `department_store`, `superstore` or `warehouse_club_store`, and the
#: `grocery` wedge matches only the `grocery_store` hierarchy. Three parents were identified by
#: the fifth review and are named below; they are recorded as plain `Walmart`, which is why the
#: search behind ask 5 -- requiring 'Supercenter' or 'Neighborhood Market' in the name -- could
#: never have found them. The remaining parents are NOT yet identified, and finding them is part of
#: rebuilding ask 5.
#:
#: **These ten are removed only together with their replacements, or not at all.** Nothing may
#: fold this table into `DROPPED_PLACE_IDS`; a test asserts the two do not intersect.
HELD_SERVICE_POINTS: dict[str, str] = {
    "686a0d8f-b451-45c5-af0b-1dc3cc76a426":
        "'Walmart Grocery Pickup and Delivery', taxonomy hierarchy=grocery_store. A COLLECTION BAY. Nearest "
        "surviving grocery record 0.2 m, 'Walmart Neighborhood Market' -- the shop this bay collects for, "
        "and it IS in the published layer, so removing the bay would cost this site nothing. Held anyway, "
        "because the ten are one decision and splitting them by site would leave the table saying different "
        "things about identical records.",
    "b570ea04-a662-4fee-9823-16d464eb02a2":
        "'Walmart Grocery Pick Up and Delivery', taxonomy hierarchy=grocery_store. A COLLECTION BAY. "
        "Nearest surviving grocery record 75.4 m, 'Walmart Supercenter' -- the shop this bay collects for, "
        "and it IS in the published layer, so removing the bay would cost this site nothing. Held anyway, "
        "because the ten are one decision and splitting them by site would leave the table saying different "
        "things about identical records.",
    "cee0e25b-aef4-410c-ae89-a0be7ad2bf41":
        "'Walmart Grocery Pickup and Delivery', taxonomy hierarchy=grocery_store. A COLLECTION BAY. Nearest "
        "surviving grocery record 147.9 m, 'Total Oriental Foods' -- **which is NOT the shop this bay "
        "collects for.** The real parent is `aec747a0-3bc4-4b87-81fe-94fae9b03f24 at 27.4 m`, a plain "
        "`Walmart` record, ABSENT from the published layer. The 2026-11-18 entry for this record claimed "
        "the shop it collects for was itself in the layer, which was false: it read parentage off "
        "proximity. Removing this bay erases the site.",
    "ea38688f-cdfe-46e4-8ab4-d6373e611d63":
        "'Walmart Grocery Pickup and Delivery', taxonomy hierarchy=grocery_store. A COLLECTION BAY. Nearest "
        "surviving grocery record 256.5 m, 'Tazza Mandi'. **Nothing published remains within 150 m if this "
        "bay goes**, and the parent store has NOT yet been identified -- finding it is part of rebuilding "
        "ask 5. Removing this bay erases the site.",
    "9011ca8b-301c-40d9-a7c1-a61f6894a42d":
        "'Walmart Grocery Pickup and Delivery', taxonomy hierarchy=grocery_store. A COLLECTION BAY. Nearest "
        "surviving grocery record 567.7 m, 'Aldi'. **Nothing published remains within 150 m if this bay "
        "goes**, and the parent store has NOT yet been identified -- finding it is part of rebuilding ask "
        "5. Removing this bay erases the site.",
    "0f2b2452-b74f-422d-b081-ccbf625ad2fb":
        "'Walmart Grocery Pickup and Delivery', taxonomy hierarchy=grocery_store. A COLLECTION BAY. Nearest "
        "surviving grocery record 577.6 m, 'Carlie C's IGA'. **Nothing published remains within 150 m if "
        "this bay goes**, and the parent store has NOT yet been identified -- finding it is part of "
        "rebuilding ask 5. Removing this bay erases the site.",
    "fb500d70-085c-4652-b9bd-fd3545550483":
        "'Walmart Grocery Pickup and Delivery', taxonomy hierarchy=grocery_store. A COLLECTION BAY. Nearest "
        "surviving grocery record 680.8 m, 'a second Carlie C's IGA record'. **Nothing published remains "
        "within 150 m if this bay goes**, and the parent store has NOT yet been identified -- finding it is "
        "part of rebuilding ask 5. Removing this bay erases the site.",
    "8226f374-206c-4e30-88d5-8dfed581b3ee":
        "'Walmart Grocery Pickup and Delivery', taxonomy hierarchy=grocery_store. A COLLECTION BAY. Nearest "
        "surviving grocery record 944.2 m, 'Harris Teeter' -- **which is NOT the shop this bay collects "
        "for.** The real parent is `30614a3f-db5b-4c11-94c6-116a59512152 at 20.0 m`, a plain `Walmart` "
        "record, ABSENT from the published layer. The 2026-11-18 entry for this record claimed the shop it "
        "collects for was itself in the layer, which was false: it read parentage off proximity. Removing "
        "this bay erases the site.",
    "38c97738-83e4-4227-bffe-e352043c8606":
        "'Walmart Grocery Pickup and Delivery', taxonomy hierarchy=grocery_store. A COLLECTION BAY. Nearest "
        "surviving grocery record 1097.8 m, 'Grand India Mart' -- **which is NOT the shop this bay collects "
        "for.** The real parent is `88f1168d-25de-48ae-b495-73dde8fe674e at 63.4 m`, a plain `Walmart` "
        "record, ABSENT from the published layer. The 2026-11-18 entry for this record claimed the shop it "
        "collects for was itself in the layer, which was false: it read parentage off proximity. Removing "
        "this bay erases the site.",
    "2023f7f8-de17-4056-8d77-67f8cf180b0f":
        "'Walmart Grocery Pickup and Delivery', taxonomy hierarchy=grocery_store. A COLLECTION BAY. Nearest "
        "surviving grocery record 2002.3 m, 'Lowes Foods of Clayton'. **Nothing published remains within "
        "150 m if this bay goes**, and the parent store has NOT yet been identified -- finding it is part "
        "of rebuilding ask 5. Removing this bay erases the site.",
}


def flagged_closure_reason(place_id: str) -> str | None:
    """Why this record is doubted, or `None` if it is not.

    The read seam for anything that wants to SHOW the doubt -- a map popup, a result row, an
    export column. It exists so that surfacing a flag is a change to a renderer rather than a
    change to this table, and so that a flag nobody can read is distinguishable from a flag
    nobody has chosen to read yet.
    """
    return FSQ_FLAGGED_CLOSURES.get(place_id)


#: Everything actually removed, from every table that removes anything. One name so a reader can
#: see the whole effect in one place, and so adding a table cannot forget to apply it.
#:
#: `PENDING_CLOSURES`, `FSQ_FLAGGED_CLOSURES` and `HELD_SERVICE_POINTS` are deliberately
#: NOT here. For the held service points that is the owner's 2026-11-19 decision and folding them
#: in would reverse it silently; a test asserts the sets do not intersect. Both record closures
#: we are not acting on, and folding either in would quietly reverse a decision -- for the flag
#: table that reversal is the entire point of it existing, so a test asserts the two sets do not
#: intersect. `FSQ_CLOSURES_HELD` is now empty, so it would contribute nothing; it is still left
#: out, because the day it stops being empty it would otherwise start removing records nobody had
#: agreed to remove.
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
