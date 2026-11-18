"""What a household means by "ten minutes from a grocery".

**Owner decision, 2026-11-17.** The default meaning is *"a supermarket you could do a weekly shop
at"*, with specialty grocers selectable separately or in combination. For the classification:
*"use big brands, and a curated list for the independents that we can build / add to over time."*

So membership is decided by **explicit tables and nothing else**. There is deliberately no
heuristic on the name, because the name and the brand are exactly where this data is worst. The 26
brands carried by the 541 open grocery records include:

* **Bitcoin Depot** -- on a place actually named *Casablanca Market*. The brand is the crypto ATM
  inside the shop.
* **Regency Centers** -- a shopping-centre REIT, on a place named *Market at Colonnade Center*.
  That is the mall, not a shop in it.
* **Pet Dairy** -- a dairy brand.
* **"Food Lion- Summersville, WV"** -- in North Carolina, on a place named *Food Line Distribution
  Center*. A distribution centre, misbranded, in the wrong state.
* **"Ray's Food Place"** -- a west-coast chain, on a place named *Ray's Supermarket*, which is a
  real local independent.

A rule that read any of those strings would get all of them wrong, in both directions. Hence tables.

**Narrowed 2026-11-18, and worth reading against the list above.** Every example in it is a case
where the **brand** is wrong and the **name** is right. So the refusal now applies to *parsing* a
name -- guessing what kind of shop it is from its words -- and not to *looking a name up in these
same tables*. See `chain_in_name` at the end of this module; 34 records with an empty `brand` carry
a chain name that `SUPERMARKET_BRANDS` already holds.

The tables are meant to grow. `CURATED_INDEPENDENT_SUPERMARKETS` is seeded with the independents
that are unambiguous from the data already held; everything else stays **`unclassified`**, which is
an honest answer and not a silent "no".
"""
from __future__ import annotations

#: Chains where a household can do a full weekly shop. Keyed on the Overture `brand` primary name.
SUPERMARKET_BRANDS = frozenset({
    "Food Lion", "Harris Teeter", "Lowes Foods", "Publix", "ALDI", "Lidl",
    "Family Fare", "Walmart", "Trader Joe's", "IGA", "Sprouts Farmers Market",
    "Whole Foods Market",
    # Full-service supermarkets serving a particular community. They are not "specialty" in the
    # sense that matters here -- you can do a weekly shop in them.
    "Compare Foods Apex",
    # Carrboro's co-op. One store, but a full grocery and the obvious weekly shop for its
    # neighbourhood.
    "Weaver Street Market",
})

#: Grocers people make a special trip to, for a particular range. Real shops; not a weekly shop.
SPECIALTY_BRANDS = frozenset({
    "Suvidha Indo-Pak Groceries", "Grand Asia Market", "Patel Brothers",
    "Fresh International Market Group", "Little India",
})

#: Brands that mean the record is not a shoppable grocery at all. These are data defects rather
#: than categories, and they are listed here so the grocery layer does not route a household to
#: a dairy plant, a mall, or a distribution centre.
NOT_A_GROCERY_BRANDS = frozenset({
    "Pet Dairy",                    # a dairy brand
    "Regency Centers",              # a shopping-centre REIT; the place is the mall
    "Food Lion- Summersville, WV",  # "Food Line Distribution Center" -- a depot, wrong state
})

#: Overture taxonomy primaries that declare themselves specialty without needing a brand.
SPECIALTY_PRIMARIES = frozenset({
    "mexican_grocery_store", "organic_grocery_store", "international_grocery_store",
    "indian_grocery_store", "korean_grocery_store", "asian_grocery_store",
})

#: Independent supermarkets, by Overture id, with why. **This list is meant to grow**: the owner
#: adds to it as independents are recognised. Seeded only with ones the held data makes
#: unambiguous.
CURATED_INDEPENDENT_SUPERMARKETS: dict[str, str] = {
    "f260ab10-ef18-42bf-8ace-865d6f674431":
        "Ray's Supermarket. Overture brands it 'Ray's Food Place', a west-coast chain that does "
        "not operate in North Carolina, so the brand is a bad match on a real local independent. "
        "Confidence 1.00 and the place name says Supermarket. Seeded 2026-11-17.",
    "d01fa46e-86cd-44ed-a3a4-57b5990990ba":
        "Tropicana Supermarket. Branded 'Tropicana Supermarket Greenville', with a city 130 km "
        "away in the brand string; the place itself is in the Triangle at confidence 0.98. A "
        "full-service Hispanic supermarket, which is a weekly shop. Seeded 2026-11-17.",
}


#: Records OSM independently confirms as `shop=supermarket`, seeded 2026-11-17 by
#: `scripts/prefill_from_osm.py` on the owner's instruction to "start with osm to
#: prefill". Admitted only where the evidence is unambiguous: OSM carries
#: `shop=supermarket`, the two names agree EXACTLY, and the feature is within 100 m.
#:
#: Kept apart from the hand-curated table above on purpose. These are a REGENERABLE
#: derivation from a dataset -- re-run the script against a newer OSM extract and the set
#: moves -- whereas a hand-curated entry is a judgement somebody made and should not be
#: silently overwritten by a data refresh.
#:
#: Two things a reader should know before trusting the whole table:
#:
#: * It recovers chains the BRAND tables miss entirely. Wegmans appears five times and is
#:   absent from `SUPERMARKET_BRANDS`, because those Overture records carry no brand at
#:   all; the same goes for six Food Lion records, two Lidl, an ALDI and a Trader Joe's.
#: * **The ethnic and international markets in here are the ones most likely to be
#:   disputed.** OSM tags Li Ming's Global Mart, Total Oriental Foods, Toyo Shokuhin,
#:   Harmony Mediterranean Market and friends as `shop=supermarket`. Some are genuinely a
#:   weekly shop; some are a special trip. The tag cannot tell them apart and neither can
#:   this script, so they are admitted on OSM's word and flagged here for the owner to
#:   strike any they disagree with.
OSM_CONFIRMED_SUPERMARKETS: dict[str, str] = {
    "18d18746-17c3-43e5-b274-2246eb402701":
        "ALDI -- OSM `shop=supermarket` named 'ALDI' at 16.1 m, names agree exactly.",
    "8120bde2-f007-49d8-ac6c-2a247082e592":
        "Bobbitt Grocery -- OSM `shop=supermarket` named 'Bobbitt Grocery' at 4.2 m, names agree exactly.",
    "cb3cd813-531c-48f3-9866-4288ca056163":
        "Durham Co-Op Grocery -- OSM `shop=supermarket` named 'Durham Co-op Market' at 11.3 m, names agree exactly.",
    "5426718a-c8eb-4d78-8e39-f493c65cf5ad":
        "Efland Supermarket -- OSM `shop=supermarket` named 'Efland Supermarket' at 4.9 m, names agree exactly.",
    "680bd93b-779d-4d00-8ef0-556625ffc747":
        "El Mandado Supermarket -- OSM `shop=supermarket` named 'El Mandado Supermarket' at 18.1 m, names agree exactly.",
    "2e3448ca-dc0e-491d-89c0-21a7b90a946c":
        "El Super Inc. -- OSM `shop=supermarket` named 'El Super' at 20.4 m, names agree exactly.",
    "92b2a1e9-19ff-456a-bdac-620db78f1786":
        "Food Lion -- OSM `shop=supermarket` named 'Food Lion' at 9.0 m, names agree exactly.",
    "b1e61ea2-feae-4569-959d-3c7304353b45":
        "Food Lion -- OSM `shop=supermarket` named 'Food Lion' at 0.0 m, names agree exactly.",
    "b5850e36-ffa4-4c97-9723-353cf9305f15":
        "Food Lion -- OSM `shop=supermarket` named 'Food Lion' at 17.3 m, names agree exactly.",
    "b7e3fa6b-b24e-47d5-ba68-a425a14bc56b":
        "Food Lion -- OSM `shop=supermarket` named 'Food Lion' at 0.0 m, names agree exactly.",
    "c2190603-0050-4ef8-bad6-8a9b38eb7f83":
        "Food Lion -- OSM `shop=supermarket` named 'Food Lion' at 6.6 m, names agree exactly.",
    "e2dcd014-dcec-43e1-abe9-2b6656c8201f":
        "Food Lion -- OSM `shop=supermarket` named 'Food Lion' at 16.1 m, names agree exactly.",
    "4dd0b255-4049-4181-83a8-7f801c4cf989":
        "Harris Teeter -- OSM `shop=supermarket` named 'Harris Teeter' at 79.8 m, names agree exactly.",
    "2d7cfc39-c292-44dc-b7c0-5d2c83860321":
        "Interfood Plaza Supermarket -- OSM `shop=supermarket` named 'Interfood Plaza Supermarket' at 0.0 m, names agree exactly.",
    "d4993941-48a2-4de2-8545-0e8f7625bf3d":
        "Las Carolinas Supermarket -- OSM `shop=supermarket` named 'Las Carolinas Supermarket' at 15.2 m, names agree exactly.",
    "33cfcc33-53d2-435c-898b-dadd29fab06f":
        "Lidl -- OSM `shop=supermarket` named 'Lidl' at 0.0 m, names agree exactly.",
    "70ada52e-202a-4793-a4d5-08bd07d732a1":
        "Lidl -- OSM `shop=supermarket` named 'Lidl' at 0.0 m, names agree exactly.",
    "2605e7fa-3010-440f-be17-636538f2ff97":
        "The Fresh Market -- OSM `shop=supermarket` named 'The Fresh Market' at 0.0 m, names agree exactly.",
    "2b6dba45-4184-45ea-a387-246bdc12c796":
        "The Fresh Market -- OSM `shop=supermarket` named 'The Fresh Market' at 32.4 m, names agree exactly.",
    "53c1ff38-e72d-499d-885e-c7a9a3572245":
        "The Fresh Market -- OSM `shop=supermarket` named 'The Fresh Market' at 10.3 m, names agree exactly.",
    "7f8f13a4-0120-4d39-a04a-bf644e29fd6f":
        "The Fresh Market -- OSM `shop=supermarket` named 'The Fresh Market' at 3.6 m, names agree exactly.",
    "87c2282b-1f03-4070-95b9-16e2773be120":
        "The Fresh Market -- OSM `shop=supermarket` named 'The Fresh Market' at 18.0 m, names agree exactly.",
    "9c19bf7c-7ff9-4d56-abaa-8d82ecd119ae":
        "Trader Joe's -- OSM `shop=supermarket` named 'Trader Joe's' at 18.0 m, names agree exactly.",
    "ccff8ac5-0b7d-4ac7-8d5d-3a7f5e0fa768":
        "Walmart Neighborhood Market -- OSM `shop=supermarket` named 'Walmart Neighborhood Market' at 14.3 m, names agree exactly.",
    "63bcd4e0-16ce-49a7-a0c6-118a9551367f":
        "Wegmans -- OSM `shop=supermarket` named 'Wegmans' at 92.3 m, names agree exactly.",
    "88d010aa-d027-4f22-a194-79fa4fc606c4":
        "Wegmans -- OSM `shop=supermarket` named 'Wegmans' at 52.8 m, names agree exactly.",
    "e02d2023-cd17-4bc9-aa1f-04d6fc49c8f4":
        "Wegmans -- OSM `shop=supermarket` named 'Wegmans' at 16.1 m, names agree exactly.",
    "eabb0f08-e18a-45a4-85d0-c3dc67ce7793":
        "Wegmans -- OSM `shop=supermarket` named 'Wegmans' at 47.4 m, names agree exactly.",
}

#: Records OSM tags `shop=supermarket` that the owner has placed in **specialty** instead.
#:
#: Owner decision 2026-11-17: *"move to specialty, and note in documentaiton that we'll want to
#: revisit this decision later, and apply a more robust mechanism for categorization."*
#:
#: OSM's `shop=supermarket` is one tag doing two jobs. It is applied to a full-service
#: weekly-shop grocer and to a large ethnic or international market alike, and the tag cannot
#: separate them. Neither can a name. So the eight below are placed by hand, and the decision is
#: a judgement about what a household means rather than a fact about the data.
#:
#: **THIS IS EXPLICITLY A HOLDING POSITION.** The owner asked for it to be recorded as such. The
#: line being drawn here -- "you could do a weekly shop at it" -- is about the range a shop
#: carries, and nothing in Overture or OSM measures range. A more robust mechanism would need
#: something that does: floor area, aisle or department counts, a product-range signal from a
#: source that holds one, or simply asking people in the neighbourhood. Until then this table is
#: a list of calls somebody made, and it should be read that way.
#:
#: **The boundary is genuinely unclear and the two sides are listed so the line is visible.**
#: Four Hispanic full-service supermarkets were deliberately LEFT as supermarkets -- El Mandado
#: Supermarket, El Super, Interfood Plaza Supermarket and Las Carolinas Supermarket -- because
#: they are the same kind of shop as `Compare Foods`, which is already in `SUPERMARKET_BRANDS`.
#: Whether that line is in the right place is exactly what a revisit should test.
OSM_CONFIRMED_SPECIALTY: dict[str, str] = {
    "9b0928de-84cf-4e31-b13c-5b350862e10d":
        "Casablanca Market -- OSM `shop=supermarket` named 'Casablanca Market' at 9.9 m, names agree exactly.",
    "3e8bd78c-2e9c-4df2-8298-cba07a9eb5b1":
        "Harmony Mediterranean Market -- OSM `shop=supermarket` named 'Harmony Mediterranean Market' at 19.4 m, names agree exactly.",
    "e2c81dad-9c7b-470e-9309-d5dcc6d9919b":
        "International Foods -- OSM `shop=supermarket` named 'International Foods' at 14.0 m, names agree exactly.",
    "93963195-26f4-43e9-a83d-0fee5248132c":
        "Li Ming's Global Mart -- OSM `shop=supermarket` named 'Li Ming's Global Mart' at 22.3 m, names agree exactly.",
    "a129a3de-a492-4829-90e4-62deb5d56c54":
        "Nc International Grocery Store -- OSM `shop=supermarket` named 'NC International Grocery Store' at 13.1 m, names agree exactly.",
    "1c3c4e7b-c2b2-409f-9e59-2acde8033977":
        "Oriental Store of Raleigh -- OSM `shop=supermarket` named 'Oriental Store of Raleigh' at 34.3 m, names agree exactly.",
    "033f8604-b9e4-4f3a-a882-a294c71d04ca":
        "Total Oriental Foods -- OSM `shop=supermarket` named 'Total Oriental Foods' at 13.2 m, names agree exactly.",
    "54a8fe50-6043-4814-bca9-52ace122c4eb":
        "Toyo Shokuhin & Gifts -- OSM `shop=supermarket` named 'Toyo Shokuhin & Gifts' at 8.1 m, names agree exactly.",
}


#: Records whose Overture `brand` field is EMPTY but whose NAME carries a chain that
#: `SUPERMARKET_BRANDS` already holds, corroborated by a building big enough to be a supermarket.
#: Generated by `scripts/recover_brandless_by_name.py` on the owner's decision of 2026-11-18.
#:
#: **Kept apart from the hand-curated tables for the usual reason**: this is a REGENERABLE
#: DERIVATION -- re-run the script against newer data and the set moves -- whereas a curated entry
#: is a judgement somebody made and must not be silently overwritten by a refresh. Same footing as
#: `OSM_CONFIRMED_SUPERMARKETS`.
#:
#: **Two screens stand between a chain name and an entry here, and each exists because the data
#: broke the rule without it.** Eleven of the 33 candidates were refused as SERVICE POINTS -- nine
#: `Walmart Grocery Pickup and Delivery` and a `Weaver Street Market Administration`, several of
#: them sitting on the chain's own full-size footprint, so no geometric signal could have caught
#: them. Nine more were refused because NO BUILDING over 650 m2 stands within 120 m of them:
#: defunct stores, lockers or phantom rows, which the name alone would have promoted.
#:
#: **One entry is marginal and is left visible rather than quietly dropped:** a `Lowes Foods`
#: corroborated by an 837 m2 building, just over the floor and small for that chain. It may be a
#: point sitting on a neighbouring structure. The number is in the entry so it can be struck.
#:
#: **Also visible here: two `Wal Mart` records share one 3,943 m2 building.** They are very
#: probably duplicate records for one store. That is a de-duplication problem, not a
#: classification one, and this table does not pretend to solve it.
#:
#: Licence: the corroboration uses ODbL building footprints to classify a record in a PUBLISHED
#: layer, which makes that layer an ODbL-derived database and so share-alike. Authorised by the
#: owner 2026-11-18; the Buildings row in `docs/experiments/source-registry.md` was widened to say
#: so. Footprints themselves are still never republished.
NAME_CONFIRMED_SUPERMARKETS: dict[str, str] = {
    "1630d1dc-61cd-4764-bc2b-2da3ebd2f5af":
        "ALDI -- name carries 'ALDI', which is already in SUPERMARKET_BRANDS, while the Overture `brand` field is EMPTY. Corroborated by a 5,156 m2 building within 120 m.",
    "e59e353c-6e8b-4ca8-b727-e4df899ac824":
        "Brier Creek Walmart -- name carries 'Walmart', which is already in SUPERMARKET_BRANDS, while the Overture `brand` field is EMPTY. Corroborated by a 20,903 m2 building within 120 m.",
    "ac8293ab-9579-45e9-8e1c-d8bcff094fe9":
        "Carlie C’s Iga -- name carries 'IGA', which is already in SUPERMARKET_BRANDS, while the Overture `brand` field is EMPTY. Corroborated by a 7,339 m2 building within 120 m.",
    "d544275c-dfa4-42aa-8ee4-fb789444be83":
        "Food Lion -- name carries 'Food Lion', which is already in SUPERMARKET_BRANDS, while the Overture `brand` field is EMPTY. Corroborated by a 11,617 m2 building within 120 m.",
    "dd182894-0561-4ab9-81a3-1e97f0f78ef2":
        "Harris Teeter -- name carries 'Harris Teeter', which is already in SUPERMARKET_BRANDS, while the Overture `brand` field is EMPTY. Corroborated by a 4,181 m2 building within 120 m.",
    "28efacfc-ccaf-4eda-bbe5-580213dc3d77":
        "Harris Teeter Supermarkets -- name carries 'Harris Teeter', which is already in SUPERMARKET_BRANDS, while the Overture `brand` field is EMPTY. Corroborated by a 8,937 m2 building within 120 m.",
    "b6eafe53-9275-45f9-97df-ce49c87e3d6d":
        "Lowes Foods -- name carries 'Lowes Foods', which is already in SUPERMARKET_BRANDS, while the Overture `brand` field is EMPTY. Corroborated by a 5,228 m2 building within 120 m.",
    "bc7f2c15-586b-4846-afca-b2f12e2c5ac4":
        "Lowes Foods -- name carries 'Lowes Foods', which is already in SUPERMARKET_BRANDS, while the Overture `brand` field is EMPTY. Corroborated by a 837 m2 building within 120 m.",
    "b6ecac05-f6d7-42da-a9c6-a720ae725c32":
        "Lowes Foods Of Cary On High House Road -- name carries 'Lowes Foods', which is already in SUPERMARKET_BRANDS, while the Overture `brand` field is EMPTY. Corroborated by a 4,064 m2 building within 120 m.",
    "8c644ec3-24e8-419a-a81f-90a3bc84d4c6":
        "Lowes Foods On Rowlock Way -- name carries 'Lowes Foods', which is already in SUPERMARKET_BRANDS, while the Overture `brand` field is EMPTY. Corroborated by a 7,056 m2 building within 120 m.",
    "8e0b7fef-449b-4074-854a-a7f7271eb502":
        "Wal Mart -- name carries 'Walmart', which is already in SUPERMARKET_BRANDS, while the Overture `brand` field is EMPTY. Corroborated by a 3,943 m2 building within 120 m.",
    "b046d53b-12cc-4ec8-a951-c15167855a0f":
        "Wal Mart -- name carries 'Walmart', which is already in SUPERMARKET_BRANDS, while the Overture `brand` field is EMPTY. Corroborated by a 3,943 m2 building within 120 m.",
    "1e99e399-b118-4d95-8c78-6770a47287c8":
        "Weaver Street Market, Inc -- name carries 'Weaver Street Market', which is already in SUPERMARKET_BRANDS, while the Overture `brand` field is EMPTY. Corroborated by a 13,127 m2 building within 120 m.",
}


def _brand_name(record) -> str | None:
    brand = record.get("brand") if hasattr(record, "get") else None
    if brand is None:
        return None
    try:
        names = dict(brand).get("names")
        return (dict(names).get("primary") if names is not None else None)
    except Exception:
        return None


def _primary(record) -> str | None:
    tax = record.get("taxonomy") if hasattr(record, "get") else None
    if tax is None:
        return None
    try:
        return dict(tax).get("primary")
    except Exception:
        return None


def classify_grocery(record) -> str:
    """One of `supermarket`, `specialty`, `not_a_grocery`, `unclassified`.

    `unclassified` is the answer for the records that carry no brand and are on none of the
    tables -- 323 when this was written, fewer now that OSM and the name recovery have taken
    their share. It is deliberately NOT `supermarket` -- that would put a corner shop in the
    weekly-shop layer -- and deliberately NOT `specialty` either, because nobody has looked at
    them and asserting a category nobody checked is how "Roofing Inc." became a grocery.
    """
    brand = _brand_name(record)
    if brand in NOT_A_GROCERY_BRANDS:
        return "not_a_grocery"
    if brand in SUPERMARKET_BRANDS:
        return "supermarket"
    place_id = str(record.get("id"))
    if place_id in OSM_CONFIRMED_SPECIALTY:
        return "specialty"
    if (
        place_id in CURATED_INDEPENDENT_SUPERMARKETS
        or place_id in OSM_CONFIRMED_SUPERMARKETS
        or place_id in NAME_CONFIRMED_SUPERMARKETS
    ):
        return "supermarket"
    if brand in SPECIALTY_BRANDS:
        return "specialty"
    if _primary(record) in SPECIALTY_PRIMARIES:
        return "specialty"
    return "unclassified"
# ----------------------------------------------------------------------------------------------
# Reading the chain out of the NAME, when the `brand` field is empty.
#
# Owner decision 2026-11-18: the instruction above is NARROWED, not reversed.
#   * still refused: parsing a name to guess what KIND of shop something is;
#   * now allowed:   looking a name up in the SAME EXPLICIT TABLE the brand is looked up in.
#
# The case for it is in the paragraph above, read again: `Bitcoin Depot` is branded onto a place
# NAMED `Casablanca Market`; `Ray's Food Place` onto `Ray's Supermarket`; `Food Lion-
# Summersville, WV` onto `Food Line Distribution Center`. Every example given for distrusting this
# data is one where the BRAND is wrong and the NAME is right.
#
# Measured: 34 of the 272 unclassified brandless grocery records carry a chain name with an empty
# `brand`, so this is roughly an eighth of that blocker and none of it is new judgement.
# ----------------------------------------------------------------------------------------------

#: Words that mean the record is a place the chain OPERATES rather than a place you can shop.
#:
#: **This screen is not optional and footprint evidence cannot replace it.** Nine of the 34 are
#: `Walmart Grocery Pickup and Delivery`, and several sit on the Supercenter's own 20,000 m2
#: footprint -- so every geometric signal says "supermarket" and only the name says "collection
#: bay". `Weaver Street Market Administration` is the same shape: an office, on the same site as
#: the shop, which the destination audit has already seen chosen as a destination.
SERVICE_POINT_WORDS = frozenset({
    "pickup", "delivery", "administration", "distribution", "warehouse", "depot",
    "corporate", "office", "headquarters", "pharmacy", "fuel", "vision", "photo",
})

#: Two-word forms of the above, matched on the normalised string.
SERVICE_POINT_PHRASES = ("pick up",)


def _normalise(name: str) -> str:
    """Lowercase, and every run of non-alphanumerics becomes one space.

    Punctuation is where these names differ most: `Carlie C's Iga` arrives with a mangled
    apostrophe, `Wal Mart` and `Walmart` are the same chain, `Weaver Street Market, Inc` carries a
    comma. Collapsing all of it means the comparison is about words.
    """
    spaced = "".join(ch if ch.isalnum() else " " for ch in (name or "").lower())
    return " ".join(spaced.split())


def _contains_words(haystack: str, needle: str) -> bool:
    """Whole-word containment on two already-normalised strings.

    Whole words, not substrings: `IGA` is three letters and would otherwise match inside
    `Rigaud`, and `ALDI` inside `Aldine`.
    """
    if not needle:
        return False
    return f" {needle} " in f" {haystack} "


def chain_in_name(name: str) -> str | None:
    """The `SUPERMARKET_BRANDS` entry named in this place's name, or `None`.

    Only that table is consulted, which is the whole point: `Kroger` and `Wegmans` trade in this
    metro and are **not** in it, so a record called `Kroger Store` matches nothing until somebody
    edits the table. Adding a chain stays a decision, not a side effect of a name.

    The longest match wins, so `Weaver Street Market` is preferred over any shorter entry that
    happens to be inside it.

    This reports the match even when the record is a service point; `names_a_service_point` is the
    separate screen, so that a sheet can show both the chain and the reason it was skipped.
    """
    hay = _normalise(name)
    if not hay:
        return None
    for brand in sorted(SUPERMARKET_BRANDS, key=len, reverse=True):
        needle = _normalise(brand)
        if _contains_words(hay, needle):
            return brand
        # `Wal Mart` and `Walmart` are the same chain written two ways, and both are in the data.
        if needle.replace(" ", "") == hay.replace(" ", ""):
            return brand
    return None


def names_a_service_point(name: str) -> bool:
    """True when the name says this is a collection point, office, depot or counter.

    A household sent to a grocery pickup bay has been sent to the wrong place, and no geometry
    distinguishes the bay from the shop it is bolted to.
    """
    hay = _normalise(name)
    if any(phrase in f" {hay} " for phrase in (f" {p} " for p in SERVICE_POINT_PHRASES)):
        return True
    return any(_contains_words(hay, word) for word in SERVICE_POINT_WORDS)
