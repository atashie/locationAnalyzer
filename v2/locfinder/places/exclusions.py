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


def drop_excluded(gdf):
    """Remove any listed record. A no-op on a frame with no `id` column.

    Frames from `select_named` are built by hand and carry no Overture id, so the absence of the
    column is normal rather than an error worth raising on.
    """
    if "id" not in getattr(gdf, "columns", ()):
        return gdf
    return gdf[~gdf["id"].isin(EXCLUDED_PLACE_IDS)]
