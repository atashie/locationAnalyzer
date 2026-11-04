"""Phase 1 S2.1. The resolver, with the measured geocoding failures as fixtures.

Decision D4's benchmark is the source of these cases. Census resolved **none** of ten place-name
queries; unbounded Nominatim returned "UNC Hospitals" in Morganton (180 km away) and "Southpoint"
in Wisconsin. Both failures are the same two mistakes — no metro bound, and auto-picking a single
global best — so the tests check those behaviours directly rather than checking a similarity score.
"""
import pytest

from locfinder.places.resolve import (AMBIGUITY_MARGIN, Place, PlaceIndex, normalise, pin,
                                      strip_region_noise)


def P(name, lon, lat, *, source="osm", sid=None, aliases=(), brand=None, locality=None,
      licence="ODbL-1.0", category=None):
    return Place(source=source, source_id=sid or f"{source}:{name}", name=name, lon=lon, lat=lat,
                 aliases=tuple(aliases), brand=brand, locality=locality, licence=licence,
                 category=category)


# A miniature Triangle: two Whole Foods, a Harris Teeter, two hospitals, a mall, an area acronym.
TRIANGLE = [
    P("Whole Foods Market", -79.0205, 35.9132, sid="osm:node/1", locality="Chapel Hill",
      brand="Whole Foods Market"),
    P("Whole Foods Market", -78.9180, 36.0090, sid="osm:node/2", locality="Durham",
      brand="Whole Foods Market"),
    P("Harris Teeter", -79.0760, 35.9140, locality="Carrboro", brand="Harris Teeter"),
    P("UNC Hospitals", -79.0520, 35.9040, locality="Chapel Hill", aliases=("UNC Medical Center",)),
    P("Duke University Hospital", -78.9380, 36.0070, locality="Durham", aliases=("Duke Hospital",)),
    P("The Streets at Southpoint", -78.9480, 35.9100, locality="Durham"),
    P("Research Triangle Park", -78.8600, 35.8990, locality="Durham", aliases=("RTP",)),
    P("Weaver Street Market", -79.0750, 35.9120, locality="Carrboro"),
    P("Carrboro Farmers Market", -79.0755, 35.9105, locality="Carrboro"),
]
IDX = PlaceIndex(TRIANGLE)


# ---------------------------------------------------------------- normalisation

def test_normalisation_folds_case_accents_and_punctuation():
    assert normalise("Carrboro Farmers' Market") == "carrboro farmers market"
    assert normalise("CAFÉ  Driade") == "cafe driade"
    assert normalise("") == ""


def test_trailing_region_words_are_dropped():
    assert strip_region_noise(["whole", "foods", "chapel", "hill", "nc"]) == \
        ["whole", "foods", "chapel", "hill"]
    assert strip_region_noise(["rtp", "north", "carolina"]) == ["rtp"]
    # a region word in the middle of a name is not noise
    assert strip_region_noise(["north", "carolina", "museum"]) == ["north", "carolina", "museum"]


# ---------------------------------------------------------------- the measured failures

def test_the_morganton_failure_cannot_happen_because_the_index_is_the_metro():
    """Unbounded Nominatim answered "UNC Hospitals" with a hospital 180 km away. The index holds
    only this metro, so the wrong entity is not reachable by construction — which is why the bound
    is a property of the index rather than a filter applied afterwards."""
    r = IDX.resolve("UNC Hospitals")
    assert r.outcome == "resolved"
    assert r.anchor.place.name == "UNC Hospitals"
    assert r.anchor.place.locality == "Chapel Hill"


def test_southpoint_resolves_through_a_partial_name():
    """The second Nominatim failure: "Southpoint" went to Wisconsin. Here the typed word is a
    subset of the real name, which is the common way people refer to a place."""
    r = IDX.resolve("Southpoint")
    assert r.anchor is not None
    assert r.anchor.place.name == "The Streets at Southpoint"
    assert "contains" in r.anchor.matched_on


def test_an_acronym_resolves_through_an_alias():
    r = IDX.resolve("RTP")
    assert r.anchor is not None and r.anchor.place.name == "Research Triangle Park"
    assert r.anchor.matched_on.startswith("alias")


def test_a_brand_with_several_shops_is_ambiguous_not_a_guess():
    """Two Whole Foods in the metro. Returning one silently is how a household ends up routed to
    the wrong side of town, so the outcome is `ambiguous` and `anchor` is deliberately None."""
    r = IDX.resolve("Whole Foods")
    assert r.outcome == "ambiguous"
    assert r.anchor is None
    names = {c.place.locality for c in r.candidates}
    assert {"Chapel Hill", "Durham"} <= names


def test_a_typed_locality_ranks_but_does_not_filter():
    """"Whole Foods Durham" should put Durham first and still offer Chapel Hill, because the typed
    locality may be the user's mistake rather than the index's."""
    r = IDX.resolve("Whole Foods Durham")
    assert r.outcome == "resolved", "the locality breaks the tie"
    assert r.anchor.place.locality == "Durham"
    assert "locality" in r.anchor.matched_on
    offered = {c.place.locality for c in r.candidates}
    assert "Chapel Hill" in offered, "the other shop is still a candidate"


def test_the_chapel_hill_form_resolves_too():
    r = IDX.resolve("Whole Foods, Chapel Hill NC")
    assert r.outcome == "resolved"
    assert r.anchor.place.locality == "Chapel Hill"


def test_two_similar_market_names_in_one_town_stay_ambiguous():
    """Weaver Street Market and Carrboro Farmers Market are different places; a query that does not
    distinguish them must not pick one."""
    r = IDX.resolve("market carrboro")
    assert r.outcome == "ambiguous"
    assert len(r.candidates) >= 2


def test_an_unknown_name_is_not_found_rather_than_nearest_guess():
    r = IDX.resolve("Trader Joes")
    assert r.outcome == "not_found" and r.candidates == ()
    assert IDX.resolve("").outcome == "not_found"
    assert IDX.resolve("   ,, ").outcome == "not_found"


def test_a_locality_on_its_own_is_still_a_place_query():
    """"Durham" must not become an empty name with a locality hint, which would match everything
    in Durham."""
    r = IDX.resolve("Durham")
    assert all("Durham" in (c.place.name or "") or "Durham" in (c.place.aliases or ())
               for c in r.candidates) or r.outcome == "not_found"


# ---------------------------------------------------------------- corroboration and provenance

def test_the_same_shop_in_both_sources_becomes_one_candidate_preferring_osm():
    """The same place is usually in Overture and OSM. Two entries is bad for a chooser, and OSM is
    the record to keep: its geometry is the ODbL truth and it is the contributable one under
    decision 17. The other source is recorded, not discarded."""
    both = PlaceIndex([
        P("Weaver Street Market", -79.0750, 35.9120, source="overture", sid="ovt:1",
          licence="CDLA-Permissive-2.0", locality="Carrboro"),
        P("Weaver Street Market", -79.07502, 35.91201, source="osm", sid="osm:node/42",
          licence="ODbL-1.0", locality="Carrboro"),
    ])
    r = both.resolve("Weaver Street Market")
    assert len(r.candidates) == 1, "one physical place, one candidate"
    c = r.candidates[0]
    assert c.place.source == "osm" and c.place.source_id == "osm:node/42"
    assert c.corroborated_by == ("overture",)


def test_two_shops_of_the_same_brand_far_apart_are_not_merged():
    """Corroboration is a distance test, not a name test — the two Whole Foods share a name."""
    r = IDX.resolve("Whole Foods")
    assert len({c.place.source_id for c in r.candidates}) >= 2


def test_a_candidate_carries_its_source_identity_and_licence():
    """Decision 17 forbids OSM contributions sourced from Overture, so provenance must survive
    resolution rather than being flattened here."""
    ovt = PlaceIndex([P("Fidelity Investments", -78.8700, 35.8900, source="overture",
                        sid="ovt:abc", licence="CDLA-Permissive-2.0", locality="Durham")])
    c = ovt.resolve("Fidelity Investments Durham").anchor
    assert c.place.source == "overture" and c.place.source_id == "ovt:abc"
    assert c.place.licence == "CDLA-Permissive-2.0"


# ---------------------------------------------------------------- the correction flow

def test_a_dropped_pin_infers_nothing():
    c = pin(-79.0, 35.9, label="my office")
    assert c.place.source == "user_pin" and c.score == 1.0
    assert c.lonlat == (-79.0, 35.9)
    assert c.place.licence is None, "a user's own pin carries no source licence"


def test_the_ambiguity_margin_is_the_documented_one():
    """A guard on the number that decides whether a household sees a chooser."""
    assert 0.0 < AMBIGUITY_MARGIN < 0.2


def test_an_empty_index_resolves_nothing_without_raising():
    assert PlaceIndex([]).resolve("anything").outcome == "not_found"


# ---------------------------------------------------------------- found on the real index

def test_a_typed_locality_beats_several_exact_name_matches():
    """The defect the real index exposed. Four Harris Teeters match "Harris Teeter" exactly, so
    with locality as a score *bonus* the `min(1.0, ...)` cap erased it and the Carrboro shop was
    not even in the top four. Locality is now an explicit tiebreaker."""
    many = PlaceIndex([
        P("Harris Teeter", -78.51, 35.98, sid="a", locality="Wake Forest"),
        P("Harris Teeter", -78.78, 35.79, sid="b", locality="Cary"),
        P("Harris Teeter", -78.64, 35.78, sid="c", locality="Raleigh"),
        P("Harris Teeter", -79.076, 35.914, sid="d", locality="Carrboro"),
    ])
    r = many.resolve("Harris Teeter Carrboro")
    assert r.outcome == "resolved", "one shop is named, despite four exact name matches"
    assert r.anchor.place.locality == "Carrboro" and r.anchor.place.source_id == "d"
    assert r.anchor.locality_match is True
    # without the locality it is correctly ambiguous
    assert many.resolve("Harris Teeter").outcome == "ambiguous"


def test_two_candidates_matching_the_typed_locality_stay_ambiguous():
    """The tiebreaker is only decisive when it picks out exactly one."""
    two = PlaceIndex([
        P("Harris Teeter", -78.90, 35.99, sid="a", locality="Durham"),
        P("Harris Teeter", -78.88, 36.02, sid="b", locality="Durham"),
    ])
    assert two.resolve("Harris Teeter Durham").outcome == "ambiguous"


def test_osm_outranks_overture_on_an_exact_tie():
    """An OSM POI is a surveyed feature; Overture carries business-listing noise that competes with
    real answers on the live index. A preference, not a quality claim."""
    both = PlaceIndex([
        P("Duke Hospital", -78.80, 36.10, source="overture", sid="ovt:x", locality="Durham"),
        P("Duke Hospital", -78.94, 36.01, source="osm", sid="osm:way/7", locality="Durham"),
    ])
    r = both.resolve("Duke Hospital")
    assert r.candidates[0].place.source == "osm"


def test_a_candidate_carries_an_address_so_a_chooser_can_distinguish_duplicates():
    """On the real index "Harris Teeter [Wake Forest]" appeared twice with nothing on screen to
    tell the two apart."""
    idx = PlaceIndex([
        Place(source="osm", source_id="1", name="Harris Teeter", lon=-78.51, lat=35.98,
              locality="Wake Forest", address="1234 Main St"),
        Place(source="osm", source_id="2", name="Harris Teeter", lon=-78.55, lat=35.95,
              locality="Wake Forest", address="90 Capital Blvd"),
    ])
    r = idx.resolve("Harris Teeter")
    assert r.outcome == "ambiguous"
    assert {c.place.address for c in r.candidates} == {"1234 Main St", "90 Capital Blvd"}
