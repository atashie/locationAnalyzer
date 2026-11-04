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


# ---------------------------------------------------------------- Codex pass-10 regressions

def test_a_transport_stop_named_after_a_place_loses_a_tie_to_the_place():
    """Pass-10 H1. `Duke Hospital` resolved confidently to `node/6509747409` — a bus platform
    (`highway=bus_stop`, `public_transport=platform`, `network=Duke`) sitting at the hospital. It
    is a reference to the hospital, not the hospital. Demoted on a tie, never excluded, because a
    transit anchor is a legitimate query."""
    idx = PlaceIndex([
        P("Duke Hospital", -78.9375, 36.0076, sid="node/stop", category="bus_stop"),
        P("Duke Hospital", -78.9380, 36.0070, sid="node/hosp", category="hospital"),
    ])
    r = idx.resolve("Duke Hospital")
    assert r.candidates[0].place.category == "hospital"
    # a stop on its own still resolves
    only = PlaceIndex([P("Duke Hospital", -78.9375, 36.0076, sid="s", category="bus_stop")])
    assert only.resolve("Duke Hospital").anchor is not None


def test_a_leading_locality_does_not_hand_the_query_to_a_station():
    """Pass-10 H2, reproduced. "Durham Whole Foods" resolved to **"Durham", the Amtrak station**,
    because the subset branch gave a one-word name a flat 0.85 however much of the query it
    ignored."""
    idx = PlaceIndex([
        P("Durham", -78.9065, 35.9975, sid="node/station", category="station", locality="Durham"),
        P("Whole Foods Market", -78.9180, 36.0090, sid="node/wf", category="supermarket",
          locality="Durham"),
    ])
    for q in ("Durham Whole Foods", "Whole Foods Durham", "the Whole Foods in Durham"):
        r = idx.resolve(q)
        assert r.candidates, f"{q!r} found nothing"
        assert r.candidates[0].place.category == "supermarket", f"{q!r} -> {r.candidates[0].place.name}"


def test_a_subset_match_is_scored_by_how_much_of_the_query_it_covers():
    idx = PlaceIndex([P("Durham", -78.9, 36.0, sid="a"), P("Durham Bulls Ballpark", -78.9, 36.0,
                                                           sid="b")])
    one_word = idx.resolve("Durham Bulls Ballpark Something")
    scores = {c.place.source_id: c.score for c in one_word.candidates}
    assert scores.get("b", 0) > scores.get("a", 0), "the fuller name must outrank the single word"


def test_the_presentation_limit_cannot_turn_ambiguous_into_resolved():
    """Pass-10 H3. `[:limit]` was applied before the decision, so `limit=1` produced a confident
    answer from an ambiguous pair."""
    idx = PlaceIndex([P("Shop", -79.0, 35.9, sid="a"), P("Shop", -78.9, 35.9, sid="b")])
    for lim in (1, 2, 8):
        r = idx.resolve("Shop", limit=lim)
        assert r.outcome == "ambiguous", f"limit={lim} changed the outcome"
        assert len(r.candidates) == min(lim, 2)
        assert r.n_matched == 2, "the caller can see how many matched before truncation"
    with pytest.raises(ValueError, match="at least 1"):
        idx.resolve("Shop", limit=0)


def test_a_bank_and_its_own_atm_are_not_merged():
    """Pass-10 H4. Name plus 60 m merged two *different* OSM records — a bank and its ATM 9 m
    apart — and the ambiguity vanished. Merging now needs cross-source agreement and compatible
    categories; two records from one source are two records."""
    idx = PlaceIndex([
        P("Acme", -79.0, 35.9, source="osm", sid="bank", category="bank"),
        P("Acme", -79.0001, 35.9, source="osm", sid="atm", category="atm"),
    ])
    r = idx.resolve("Acme")
    assert len(r.candidates) == 2 and r.outcome == "ambiguous"

    # a genuine cross-source duplicate still merges
    dup = PlaceIndex([
        P("Acme", -79.0, 35.9, source="overture", sid="ovt", category="bank"),
        P("Acme", -79.00001, 35.9, source="osm", sid="osm/1", category="bank"),
    ])
    m = dup.resolve("Acme")
    assert len(m.candidates) == 1 and m.candidates[0].corroborated_by == ("overture",)

    # the cross-source form of the same defect: a subsidiary never merges with its parent
    cross = PlaceIndex([
        P("Acme", -79.0, 35.9, source="overture", sid="ovt", category="bank"),
        P("Acme", -79.00001, 35.9, source="osm", sid="osm/1", category="atm"),
    ])
    assert len(cross.resolve("Acme").candidates) == 2


def test_categories_are_not_compared_across_taxonomies():
    """My first H4 fix demanded *equal* categories and broke real de-duplication at once: the one
    Harris Teeter in Carrboro arrives as OSM `supermarket` and Overture `grocery_store`, stopped
    merging, and "Harris Teeter Carrboro" became ambiguous between a single shop counted twice.
    The two sources use different vocabularies, so only the subsidiary/parent distinction blocks a
    merge."""
    same_shop = PlaceIndex([
        P("Harris Teeter", -79.0710, 35.9124, source="osm", sid="osm/1",
          category="supermarket", locality="Carrboro"),
        P("Harris Teeter", -79.07098, 35.91235, source="overture", sid="ovt",
          category="grocery_store", locality="Carrboro"),
        P("Harris Teeter", -78.64, 35.78, source="osm", sid="osm/2",
          category="supermarket", locality="Raleigh"),
    ])
    r = same_shop.resolve("Harris Teeter Carrboro")
    assert r.outcome == "resolved", "one Carrboro shop, counted once"
    assert r.anchor.place.locality == "Carrboro"
    assert r.anchor.corroborated_by == ("overture",)


def test_a_locality_match_must_be_unique_in_the_leading_tier_not_just_beat_the_runner_up():
    """Pass-10 M1. `_decide` compared the leader only against the *second* candidate, and score
    sorts before locality — so a third candidate in the same tier could also match the locality
    and nothing had actually been disambiguated."""
    idx = PlaceIndex([
        P("Acme", -79.0, 35.9, sid="a", locality="Durham"),
        P("Acme", -78.9, 35.9, sid="b", locality="Raleigh"),
        P("Acme", -78.8, 35.9, sid="c", locality="Durham"),
    ])
    assert idx.resolve("Acme Durham").outcome == "ambiguous", "two Durham candidates tie"
    one = PlaceIndex([
        P("Acme", -79.0, 35.9, sid="a", locality="Durham"),
        P("Acme", -78.9, 35.9, sid="b", locality="Raleigh"),
    ])
    assert one.resolve("Acme Durham").outcome == "resolved"


def test_arrow_style_common_names_become_aliases():
    """Pass-10 M4. `names.common` is a `map<string,string>`, which Arrow gives pandas as a list of
    key/value tuples — so a dict-only reader dropped every alias silently."""
    from locfinder.places.resolve import _common_names
    assert _common_names({"primary": "X", "common": {"en": "Alias"}}) == ["Alias"]
    assert _common_names({"primary": "X", "common": [("en", "Alias")]}) == ["Alias"]
    assert _common_names({"primary": "X", "common": [{"key": "en", "value": "Alias"}]}) == ["Alias"]
    assert _common_names({"primary": "X", "common": None}) == []


def test_missing_values_do_not_abort_the_index_build():
    """Pass-10 M5. `len(addrs)` raised on a scalar NaN, and `pandas.NA` was stringified into the
    literal place name `<NA>`."""
    from locfinder.places.resolve import _as_sequence, _first, _missing
    assert _as_sequence(float("nan")) == [] and _as_sequence(None) == []
    assert _as_sequence([{"locality": "Durham"}]) == [{"locality": "Durham"}]
    assert _first(float("nan"), "Real") == "Real"
    assert _first("<NA>", "Real") == "Real"
    assert _missing(float("nan")) and _missing(None) and not _missing("x")
