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
}


def drop_excluded(gdf):
    """Remove any listed record. A no-op on a frame with no `id` column.

    Frames from `select_named` are built by hand and carry no Overture id, so the absence of the
    column is normal rather than an error worth raising on.
    """
    if "id" not in getattr(gdf, "columns", ()):
        return gdf
    return gdf[~gdf["id"].isin(EXCLUDED_PLACE_IDS)]
