"""Phase 1 S2.1. The resolver, with the measured geocoding failures as fixtures.

Decision D4's benchmark is the source of these cases. Census resolved **none** of ten place-name
queries; unbounded Nominatim returned "UNC Hospitals" in Morganton (180 km away) and "Southpoint"
in Wisconsin. Both failures are the same two mistakes — no metro bound, and auto-picking a single
global best — so the tests check those behaviours directly rather than checking a similarity score.
"""
import pytest

from locfinder.places.resolve import (AMBIGUITY_MARGIN, Place, PlaceIndex, names_a_stop,
                                      normalise, pin, role_of, strip_region_noise)


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


def test_a_query_whose_words_all_appear_in_one_name_resolves_to_it():
    """This test used to assert that "market carrboro" stays ambiguous, and it did — but only
    because the parser stripped "carrboro" as a locality and then scored the remainder, which made
    Carrboro Farmers Market and Weaver Street Market tie. Scoring the intact query as well (pass-11
    H2) separates them properly: both typed words appear in one of the names and only one appears
    in the other."""
    r = IDX.resolve("market carrboro")
    assert r.outcome == "resolved"
    assert r.anchor.place.name == "Carrboro Farmers Market"
    assert r.candidates[1].place.name == "Weaver Street Market", "the other is still offered"
    assert r.anchor.score > r.candidates[1].score


def test_a_query_that_genuinely_cannot_distinguish_two_places_stays_ambiguous():
    r = IDX.resolve("Weaver Street Market")
    assert r.outcome == "resolved", "a full exact name is not ambiguous"
    two = PlaceIndex([
        P("Village Market", -79.07, 35.91, sid="a", locality="Carrboro"),
        P("Village Market", -79.08, 35.92, sid="b", locality="Carrboro"),
    ])
    assert two.resolve("Village Market Carrboro").outcome == "ambiguous"


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


# ---------------------------------------------------------------- Codex pass-11 regressions

def test_a_locality_word_inside_a_name_is_not_stripped_away():
    """Pass-11 H2, and a regression I introduced with my own pass-10 H2 fix. The parser committed
    to one reading before scoring, so "Durham Coffee" stripped "Durham" as a locality and resolved
    confidently to a place called **"Coffee"** at 1.000, beating the actual "Durham Coffee" at
    0.725. Every plausible reading is scored now and the best explanation wins."""
    idx = PlaceIndex([
        P("Coffee", -78.90, 36.00, sid="plain", locality="Durham", category="cafe"),
        P("Durham Coffee", -78.91, 36.01, sid="named", locality="Durham", category="cafe"),
    ])
    r = idx.resolve("Durham Coffee")
    assert r.candidates[0].place.source_id == "named",         "the exact full name must outrank a destructive parse of the same query"
    assert r.candidates[0].reading == 0, "it matched the intact query"
    # Both are plausible — there really is a shop called "Coffee" in Durham — so offering a chooser
    # is the honest outcome. What matters is that the destructive reading no longer *wins*.
    assert r.outcome == "ambiguous" and {c.place.source_id for c in r.candidates} == {"named", "plain"}


def test_a_name_that_begins_with_a_connective_survives_a_trailing_locality():
    """The other half of H2: `_strip_connectives` removed words belonging to the name. On the real
    index "The Streets At Southpoint Durham" ranked a computer wholesaler level with the mall."""
    idx = PlaceIndex([
        P("The Streets At Southpoint", -78.9480, 35.9100, sid="mall", locality="Durham",
          category="shopping_mall"),
        P("Streets At Southpoint", -78.9490, 35.9110, sid="other", locality="Durham",
          category="office"),
    ])
    r = idx.resolve("The Streets At Southpoint Durham")
    assert r.candidates[0].place.source_id == "mall",         f"got {r.candidates[0].place.name!r} at {r.candidates[0].score}"


def test_a_stop_cannot_be_the_confident_answer_when_a_real_place_also_matches():
    """Pass-11 H4. Demotion is only a tie-break, and the Duke Hospital platform scores 1.000
    against hospitals at 0.7833 — so it won outright and was presented as the single answer to a
    hospital query. The resolver knows it picked a reference feature, so it can withhold
    confidence instead."""
    idx = PlaceIndex([
        P("Duke Hospital", -78.9375, 36.0076, sid="stop", category="platform"),
        P("Duke Hospital South", -78.9380, 36.0070, sid="hosp", category="hospital"),
    ])
    r = idx.resolve("Duke Hospital")
    assert r.outcome == "ambiguous" and r.anchor is None
    assert {c.place.source_id for c in r.candidates} == {"stop", "hosp"}

    # a transit query with nothing else to offer still resolves
    only = PlaceIndex([P("Duke Hospital", -78.9375, 36.0076, sid="stop", category="bus_stop")])
    assert only.resolve("Duke Hospital").anchor is not None


def test_one_record_cannot_absorb_several_from_the_same_other_source():
    """Pass-11 H3. Only the surviving representative's source was checked, so after one merge the
    representative was still OSM and the next Overture record passed the same test — two
    independent places vanishing into one confident answer."""
    idx = PlaceIndex([
        P("Acme", -79.0, 35.9, source="osm", sid="osm/1", category="bank"),
        P("Acme", -79.00005, 35.9, source="overture", sid="ovt/1", category="bank"),
        P("Acme", -79.0001, 35.9, source="overture", sid="ovt/2", category="bank"),
    ])
    r = idx.resolve("Acme")
    assert len(r.candidates) == 2, "one cross-source pair merges; the third stays separate"
    assert r.outcome == "ambiguous"


def test_categories_are_compared_as_roles_not_raw_strings():
    """Pass-11 M1, the third time raw categories have gone wrong across vocabularies. OSM says
    `station` and `fuel` where Overture says `train_station` and `gas_station`, so a raw-set
    membership test blocked exactly the merges it was meant to allow."""
    from locfinder.places.resolve import role_of
    assert role_of("station") == role_of("train_station") == "station"
    assert role_of("fuel") == role_of("gas_station") == "fuel"
    assert role_of("supermarket") == role_of("grocery_store") == "facility"
    assert role_of("platform") == role_of("bus_stop") == "stop"
    assert role_of(None) == "facility"

    # a whole station is a destination, so the two sources' records merge
    station = PlaceIndex([
        P("Durham", -78.9062, 35.9976, source="overture", sid="ovt", category="train_station"),
        P("Durham", -78.90646, 35.99753, source="osm", sid="osm/1", category="station"),
    ])
    assert len(station.resolve("Durham").candidates) == 1

    # and so does a filling station
    fuel = PlaceIndex([
        P("Sky Mart", -79.00615, 35.64282, source="overture", sid="ovt", category="gas_station"),
        P("Sky Mart", -79.00617, 35.64296, source="osm", sid="osm/1", category="fuel"),
    ])
    assert len(fuel.resolve("Sky Mart").candidates) == 1

    # a platform still never merges with its parent
    parent = PlaceIndex([
        P("Duke Hospital", -78.9375, 36.0076, source="overture", sid="ovt", category="hospital"),
        P("Duke Hospital", -78.93751, 36.00761, source="osm", sid="osm/1", category="platform"),
    ])
    assert len(parent.resolve("Duke Hospital").candidates) == 2


# --------------------------------------------------------------------------------------------
# Codex pass 12. Each of these is a case one of my pass-11 fixes broke, written as the input
# Codex used rather than as a paraphrase of the rule.
# --------------------------------------------------------------------------------------------


def test_a_connective_that_begins_a_name_survives_locality_stripping():
    """pass-12 H3. "Durham The Coffee" lost its "The" inside `_split_locality`, so the ladder never
    scored "The Coffee" intact and the query resolved confidently to a different shop called
    "Coffee". The trimmed reading is still offered, but only as a further rung."""
    idx = PlaceIndex([
        P("The Coffee", -78.9000, 35.9900, sid="osm:a", locality="Durham"),
        P("Coffee", -78.9100, 36.0000, sid="osm:b", locality="Durham"),
    ])
    r = idx.resolve("Durham The Coffee")
    assert r.candidates, r.outcome
    assert r.candidates[0].place.name == "The Coffee", [
        (c.place.name, c.score, c.reading) for c in r.candidates]


def test_the_locality_stripped_reading_is_still_available():
    """The rung added above must not displace the one beside it: with no connective in play,
    stripping the locality still has to find the shop."""
    r = IDX.resolve("Harris Teeter Carrboro")
    assert r.outcome == "resolved" and r.candidates[0].place.name == "Harris Teeter"


def test_a_car_park_does_not_corroborate_the_airport_it_serves():
    """pass-12 H4, and the third attempt at this rule. Equal *categories* broke real
    de-duplication; a subsidiary-vs-parent boolean let these two through, because `parking` is
    deliberately not subsidiary — a car park is a destination in its own right. Equal *roles*
    separates them."""
    idx = PlaceIndex([
        P("RDU", -78.7880, 35.8790, sid="osm:p", category="parking"),
        P("RDU", -78.7881, 35.8791, source="overture", sid="ov:a", category="airport"),
    ])
    r = idx.resolve("RDU")
    assert r.n_matched == 2, [(c.place.category, c.corroborated_by) for c in r.candidates]
    assert all(not c.corroborated_by for c in r.candidates)


def test_a_pharmacy_counter_does_not_corroborate_its_pharmacy():
    """pass-12 H4. `pharmacy_counter` was separated by the old raw-category set and fell through to
    `facility` when roles replaced it, so the counter began corroborating the shop it sits in."""
    idx = PlaceIndex([
        P("Acme", -78.9000, 35.9900, sid="osm:c", category="pharmacy_counter"),
        P("Acme", -78.9001, 35.9901, source="overture", sid="ov:c", category="pharmacy"),
    ])
    r = idx.resolve("Acme")
    assert r.n_matched == 2
    assert all(not c.corroborated_by for c in r.candidates)


def test_two_vocabularies_for_one_shop_still_merge():
    """The regression guard for the rule above: role equality has to stay coarse enough to span two
    taxonomies, or it repeats the pass-10 over-correction."""
    idx = PlaceIndex([
        P("Harris Teeter", -79.0800, 35.9100, sid="osm:h", category="supermarket"),
        P("Harris Teeter", -79.0801, 35.9101, source="overture", sid="ov:h",
          category="grocery_store"),
    ])
    r = idx.resolve("Harris Teeter")
    assert r.n_matched == 1 and r.outcome == "resolved"
    assert r.candidates[0].corroborated_by == ("overture",)


def test_asking_for_a_bus_stop_is_not_ambiguous():
    """pass-12 M5. The mixed-reference abstention is right for "Duke Hospital" and wrong here: the
    user named the stop, so offering it as one of two options invents an ambiguity."""
    idx = PlaceIndex([
        P("Franklin Street bus stop", -79.0550, 35.9120, sid="osm:s", category="bus_stop"),
        P("Franklin Street bus stop cafe", -79.0560, 35.9130, sid="osm:t", category="cafe"),
    ])
    r = idx.resolve("Franklin Street bus stop")
    assert r.outcome == "resolved", [(c.place.name, c.score) for c in r.candidates]
    assert r.candidates[0].place.category == "bus_stop"


def test_a_place_named_after_a_stop_is_still_abstained_on():
    """The guard the exemption must not remove: no transport word in the query, so a platform
    leading the field still abstains in favour of the place it is named after (pass-10 H1)."""
    idx = PlaceIndex([
        P("Duke Hospital", -78.9370, 36.0070, sid="osm:d", category="platform"),
        P("Duke University Hospital", -78.9380, 36.0080, source="overture", sid="ov:d",
          category="hospital", aliases=("Duke Hospital",)),
    ])
    r = idx.resolve("Duke Hospital")
    assert r.outcome == "ambiguous", [(c.place.name, c.place.category) for c in r.candidates]


def test_corroboration_cannot_manufacture_an_intact_query_match():
    """pass-12 H2. The merged `Candidate` was rebuilt without `reading`, so it defaulted to 0 — the
    intact-query value. Merging two records that had only matched a *stripped* reading therefore
    promoted them to the rank of a genuine intact match: "Durham Coffee" was correctly ambiguous
    between a Durham Coffee in Raleigh and a Coffee in Durham, until an Overture copy of the latter
    arrived within 60 m and it resolved confidently to "Coffee"."""
    base = [
        P("Durham Coffee", -78.6382, 35.7796, sid="osm:1", locality="Raleigh", category="cafe"),
        P("Coffee", -78.9000, 35.9940, sid="osm:2", locality="Durham", category="cafe"),
    ]
    before = PlaceIndex(base).resolve("Durham Coffee")
    assert before.outcome == "ambiguous"

    corroborated = PlaceIndex(base + [
        P("Coffee", -78.90045, 35.99400, source="overture", sid="ov:2", locality="Durham",
          category="cafe")]).resolve("Durham Coffee")
    # the copy is recognised as the same shop...
    assert any(c.corroborated_by == ("overture",) for c in corroborated.candidates)
    # ...and that changes nothing about which reading matched, so the outcome is unchanged
    assert corroborated.outcome == "ambiguous", [
        (c.place.name, c.score, c.reading) for c in corroborated.candidates]
    assert corroborated.candidates[0].place.name == "Durham Coffee"


# --------------------------------------------------------------------------------------------
# Codex pass 13. The fourth consecutive pass to find over-corrections in this file, which is why
# the graded benchmark is being expanded rather than another round of point fixes being trusted.
# --------------------------------------------------------------------------------------------


def test_a_locality_repeated_inside_the_name_does_not_lose_a_reading():
    """pass-13 M5. `at_end` was inferred by comparing tokens, which misreads a query whose
    remaining name *begins* with the same word as the locality removed from its *end*: "Durham
    Coffee in Durham" dropped the trailing "Durham", concluded the locality had been a prefix, and
    so never produced the trimmed "Durham Coffee" reading. It resolved confidently to a different
    shop called "Durham Coffee In" (score 1.0 against a 0.5667 runner-up).

    The split side is now returned by the split. Both readings are produced, both match a place
    exactly, and the outcome is `ambiguous` with the two offered — which is the honest answer and
    is what this resolver exists to do, rather than picking one of two exact matches."""
    idx = PlaceIndex([
        P("Durham Coffee", -78.9000, 35.9940, sid="osm:1", locality="Durham", category="cafe"),
        P("Durham Coffee In", -78.9100, 36.0000, sid="osm:2", locality="Durham", category="cafe"),
    ])
    tokens = ["durham", "coffee", "in", "durham"]
    readings = [r for r, _ in idx._readings(tokens)]
    assert ["durham", "coffee"] in readings, readings

    r = idx.resolve("Durham Coffee in Durham")
    assert r.outcome == "ambiguous", [(c.place.name, c.score, c.reading) for c in r.candidates]
    assert {c.place.name for c in r.candidates} == {"Durham Coffee", "Durham Coffee In"}


def test_an_ordinary_name_containing_a_transport_word_is_not_transport_intent():
    """pass-13 M6. `STOP_INTENT_WORDS` listed single nouns including `bus`, `bay`, `stand` and
    `shelter`, so a bus stop named "Bay Leaf Indian Cuisine" beat the restaurant of that name
    1.0 to 0.83 *and* suppressed the abstention, returning the stop confidently."""
    for query in ("Bay Leaf Indian Cuisine", "Bus Boys and Poets", "Shelter Club", "Grandstand",
                  "The Bus Stop Cafe Company"):
        assert not names_a_stop(normalise(query).split()), query
    for query in ("Franklin Street bus stop", "Durham train station", "RDU park and ride"):
        assert names_a_stop(normalise(query).split()), query


def test_a_stop_named_after_a_restaurant_does_not_win_confidently():
    idx = PlaceIndex([
        P("Bay Leaf Indian Cuisine", -78.80, 35.90, sid="osm:s", category="bus_stop"),
        P("Bay Leaf Indian Cuisine Restaurant", -78.81, 35.91, sid="osm:t", category="restaurant"),
    ])
    assert idx.resolve("Bay Leaf Indian Cuisine").outcome == "ambiguous"


@pytest.mark.parametrize("osm_cat, other_cat", [
    ("halt", "train_station"),        # a railway halt IS a small station
    ("kiosk", "newsstand"),           # shop=kiosk is an ordinary standalone shop
    ("information", "visitor_center"),  # an information centre is somewhere you go
])
def test_cross_source_copies_whose_roles_were_mis_assigned_merge_again(osm_cat, other_cat):
    """pass-13 M7. Role *equality* is only as good as the role assignment, and I had added a batch
    of plausible-sounding categories to the fixture list at once. `halt` sat with the platforms and
    `kiosk`/`information` were called fixtures, so three real cross-source copies stopped
    corroborating each other."""
    idx = PlaceIndex([
        P("X", -78.9000, 35.9900, sid="osm:a", category=osm_cat),
        P("X", -78.9001, 35.9901, source="overture", sid="ov:a", category=other_cat),
    ])
    r = idx.resolve("X")
    assert r.n_matched == 1, [(c.place.category, role_of(c.place.category)) for c in r.candidates]
    assert r.candidates[0].corroborated_by == ("overture",)


def test_the_merged_explanation_names_the_evidence_that_earned_the_score():
    """pass-13 L2. `matched_on` came from the geometry winner, so a candidate scored 0.95 from an
    alias only the Overture record carried reported `name:contains` from the OSM representative."""
    idx = PlaceIndex([
        P("Northside Coffee Roasters", -78.9000, 35.9900, sid="osm:n"),
        P("Northside Coffee Roasters", -78.9001, 35.9901, source="overture", sid="ov:n",
          aliases=("Northside",)),
    ])
    r = idx.resolve("Northside")
    assert r.n_matched == 1, [(c.place.source, c.matched_on) for c in r.candidates]
    lead = r.candidates[0]
    assert lead.corroborated_by == ("overture",)
    assert "alias" in lead.matched_on, lead.matched_on


# --------------------------------------------------------------------------------------------
# Found by the EXPANDED BENCHMARK (benchmarks/resolver_queries.json), not by a review. This is
# the point of having built it: 41 graded assertions caught six live defects on their first run,
# where the five-query benchmark had been green through four rounds of over-correction.
# --------------------------------------------------------------------------------------------


def test_an_apostrophe_does_not_split_a_word():
    """A *medial* apostrophe was replaced by a space, so "Trader Joe's" tokenised as
    `['trader', 'joe', 's']` while "Trader Joes" gave `['trader', 'joes']`, and the two spellings
    of one query returned different leading candidates. The pre-existing test used a *trailing*
    apostrophe ("Carrboro Farmers' Market"), where a space is harmless — which is why this
    survived."""
    assert normalise("Trader Joe's") == "trader joes"
    assert normalise("McDonald's") == "mcdonalds"
    assert normalise("Lowe's Home Improvement") == "lowes home improvement"
    # and the trailing case the old test covered still works
    assert normalise("Carrboro Farmers' Market") == "carrboro farmers market"


def test_two_spellings_of_one_query_find_the_same_place():
    idx = PlaceIndex([P("Trader Joe's", -79.0200, 35.9130, sid="osm:tj", locality="Chapel Hill")])
    a = idx.resolve("Trader Joes")
    b = idx.resolve("Trader Joe's")
    assert a.candidates and b.candidates
    assert a.candidates[0].place.source_id == b.candidates[0].place.source_id
    assert a.candidates[0].score == b.candidates[0].score == 1.0


def test_a_near_tie_prefers_a_real_place_over_a_feature_that_refers_to_one():
    """The leading-tier demotion. `_rank_key` carried this already but only broke an *exact* tie,
    which essentially never happens between a name match and an alias match."""
    idx = PlaceIndex([
        P("Elm Street Clinic", -78.9000, 35.9900, sid="osm:stop", category="platform"),
        P("Elm Clinic", -78.9010, 35.9910, sid="osm:clinic", category="clinic",
          aliases=("Elm Street Clinic",)),
    ])
    r = idx.resolve("Elm Street Clinic")
    lead, second = r.candidates[0], r.candidates[1]
    # An exact *alias* match scores 0.95 against an exact *name* match's 1.00: a 0.05 gap, inside
    # the 0.08 ambiguity margin and well outside the exact equality the old rule required. So the
    # clinic leads despite scoring lower, which is the whole point of widening the rule.
    assert (second.score, lead.score) == (1.0, 0.95), (lead.score, second.score)
    assert second.score - lead.score < AMBIGUITY_MARGIN
    assert lead.place.category == "clinic", [(c.place.name, c.place.category, c.score)
                                             for c in r.candidates]


def test_a_stop_still_leads_when_it_wins_outside_the_tier():
    """The demotion must not fire on a decisive margin, or an explicit transport query breaks."""
    idx = PlaceIndex([
        P("Franklin Street bus stop", -79.0550, 35.9120, sid="osm:s", category="bus_stop"),
        P("Franklin Street bus stop cafe", -79.0560, 35.9130, sid="osm:t", category="cafe"),
    ])
    r = idx.resolve("Franklin Street bus stop")
    assert r.candidates[0].place.category == "bus_stop"
    assert r.outcome == "resolved"


def test_a_stop_that_is_the_only_candidate_still_resolves():
    idx = PlaceIndex([P("Elm Street", -78.90, 35.99, sid="osm:only", category="platform")])
    r = idx.resolve("Elm Street")
    assert r.outcome == "resolved" and r.candidates[0].place.category == "platform"


def test_a_bare_locality_query_is_never_answered_confidently():
    """An index of POIs cannot represent an area, so a confident answer to an area query is a false
    claim — the "RTP" gap generalised. The benchmark exposed the mechanism: Overture listing noise
    contains records whose *name* is exactly a place name, and a sole exact match scores 1.000 and
    wins outright, so "Chapel Hill" resolved confidently to a **gym** 6.2 km away."""
    idx = PlaceIndex([
        P("Chapel Hill", -78.9873, 35.9097, source="overture", sid="ov:gym", category="gym"),
        P("Alexan Chapel Hill", -79.0278, 35.9331, source="overture", sid="ov:lodge",
          category="lodging", locality="Chapel Hill"),
    ])
    r = idx.resolve("Chapel Hill")
    assert r.outcome == "ambiguous", [(c.place.name, c.score) for c in r.candidates]
    # the candidates are still offered, because they are worth showing
    assert r.candidates and r.candidates[0].place.name == "Chapel Hill"


def test_a_locality_word_inside_a_longer_query_is_unaffected():
    """The rule applies only when the query *is* a locality, or it would break every
    name-plus-locality query — which is most of them."""
    idx = PlaceIndex([P("Harris Teeter", -79.0760, 35.9140, locality="Carrboro",
                        category="supermarket")])
    assert idx.resolve("Harris Teeter Carrboro").outcome == "resolved"
    assert idx.resolve("Carrboro Farmers Market").outcome in {"resolved", "ambiguous", "not_found"}


# --------------------------------------------------------------------------------------------
# Codex pass 14, plus the defects the TIGHTENED benchmark exposed once its assertions could no
# longer be satisfied by a different candidate than the one they were written about.
# --------------------------------------------------------------------------------------------


def test_presentation_reordering_cannot_manufacture_confidence():
    """pass-14 H4, its executed input. Promotion ran inside `_merge_corroborating`, so `_decide`
    saw the reordered list: for "Northside Durham" the bus stop named exactly that scored 1.00 on
    the intact reading and a restaurant aliased "Northside" scored 0.95 on a stripped one, and
    after promotion `_decide` read the restaurant's sole locality match as decisive — **resolved**.
    A reordering meant to improve a chooser must never be able to remove the chooser."""
    idx = PlaceIndex([
        P("Northside Durham", -78.9000, 35.9900, sid="osm:stop", category="bus_stop",
          locality="Durham"),
        P("Acme", -78.9010, 35.9910, sid="osm:rest", category="restaurant",
          aliases=("Northside",), locality="Durham"),
    ])
    r = idx.resolve("Northside Durham")
    assert r.outcome == "ambiguous", [(c.place.name, c.score, c.reading) for c in r.candidates]
    # the presentation benefit is kept: the real place is still shown first
    assert r.candidates[0].place.category == "restaurant"


def test_an_explicit_transport_phrase_is_intent_not_part_of_the_name():
    """The tightened benchmark's find. "Duke Hospital bus stop" led with a stop named "Duke Raleigh
    Hospital CAT Bus Stop" **34.9 km away**, because that name contains all four query words while
    the platform actually called "Duke Hospital" matches only two. The phrase-free form is now a
    further reading, so the intent words stop inflating names that happen to contain them."""
    idx = PlaceIndex([
        P("Duke Hospital", -78.9370, 36.0070, sid="osm:near", category="platform"),
        P("Duke Raleigh Hospital CAT Bus Stop", -78.6400, 35.7900, sid="osm:far",
          category="bus_stop", locality="Raleigh"),
    ])
    r = idx.resolve("Duke Hospital bus stop")
    assert r.candidates[0].place.source_id == "osm:near", [
        (c.place.name, c.score, c.reading) for c in r.candidates]


def test_a_reading_that_is_nothing_but_a_locality_is_not_offered():
    """Stripping "train station" from "Durham train station" leaves the bare locality, which then
    matched a place literally named Durham at 1.000. That looks like disambiguation and is
    coincidence."""
    idx = PlaceIndex([P("Durham Station", -78.9010, 35.9950, sid="osm:s",
                        category="bus_station", locality="Durham")])
    readings = [r for r, _ in idx._readings(["durham", "train", "station"])]
    assert ["durham"] not in readings, readings


def test_a_typed_locality_must_be_confirmed_for_a_confident_answer():
    """The tightened benchmark's other find. "Durham train station" resolved **confidently** to a
    place named "Train Station" 32 km away whose locality field is empty — so a contradiction test
    would not have fired. A typed locality has to be confirmed, not merely un-contradicted; this is
    the Morganton failure mode in miniature."""
    idx = PlaceIndex([
        P("Train Station", -78.6382, 35.7796, sid="osm:far", category="station"),
        P("Durham Station", -78.9010, 35.9950, sid="osm:near", category="bus_station",
          locality="Durham"),
    ])
    r = idx.resolve("Durham train station")
    assert r.outcome == "ambiguous", [(c.place.name, c.place.locality) for c in r.candidates]
    # both are still offered: locality ranks, it does not filter
    assert {c.place.source_id for c in r.candidates} == {"osm:far", "osm:near"}


def test_a_confirmed_locality_still_resolves_confidently():
    """The guard on the rule above, and the case that caught my first version of it: a leader that
    won on the *intact* query has `locality_match=False` even when its locality is exactly what was
    typed, so the rule has to read the locality **field**, not the per-reading flag. Using the flag
    made "market carrboro" ambiguous although Carrboro Farmers Market is in Carrboro."""
    assert IDX.resolve("market carrboro").outcome == "resolved"
    assert IDX.resolve("Harris Teeter Carrboro").outcome == "resolved"
    assert IDX.resolve("Whole Foods Durham").outcome == "resolved"


def test_every_apostrophe_variant_normalises_the_same_way():
    """pass-14 L1. `_INTRAWORD` ran *after* NFKD, which decomposes U+00B4 into a space plus a
    combining acute; the mark was stripped and the space survived, so "Trader Joe´s" became
    "trader joe s" while the ASCII form became "trader joes"."""
    for variant in ("Trader Joe's", "Trader Joe’s", "Trader Joe´s", "Trader Joeʼs",
                    "Trader Joes"):
        assert normalise(variant) == "trader joes", variant
