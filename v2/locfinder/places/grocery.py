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

    `unclassified` is the answer for the 323 records that carry no brand and are not on the
    curated list. It is deliberately NOT `supermarket` -- that would put a corner shop in the
    weekly-shop layer -- and deliberately NOT `specialty` either, because nobody has looked at
    them and asserting a category nobody checked is how "Roofing Inc." became a grocery.
    """
    brand = _brand_name(record)
    if brand in NOT_A_GROCERY_BRANDS:
        return "not_a_grocery"
    if brand in SUPERMARKET_BRANDS:
        return "supermarket"
    if str(record.get("id")) in CURATED_INDEPENDENT_SUPERMARKETS:
        return "supermarket"
    if brand in SPECIALTY_BRANDS:
        return "specialty"
    if _primary(record) in SPECIALTY_PRIMARIES:
        return "specialty"
    return "unclassified"
