"""The name-agreement floor, and why it is a verdict rather than a number.

Owner decision 2026-11-18, *"1-4) yes, proceed"*, answering *"whether to put a name-agreement
floor on the OSM prefill"*. The measurement that produced the question is
`docs/engineering-notes/project-phase1-s3-fsq-accuracy.md`; the measurement that shaped the ANSWER
is in `project-phase1-s3-osm-name-floor.md`.

Two findings from that second measurement are encoded here as tests, because both are
counter-intuitive and a later session will otherwise "simplify" them back out:

1. **0.00 agreement is two different facts.** Either both names carry informative words and share
   none -- a different business -- or one side has no informative word at all, which is UNKNOWN.
   82% of the 0.00 proposals in the grocery sheet are the first; 18% are the second. A single
   float cannot tell them apart, so the gate is a three-valued verdict and the float is only ever
   reported.
2. **Jaccard magnitude is the wrong knob.** The partial-agreement band is almost entirely CORRECT
   matches -- `Walmart Grocery Pickup and Delivery` against `Walmart Supercenter` at 0.0 m scores
   0.25 -- while the wrong ones in that band are wrong because they share a GENERIC word (`han`,
   `mandi`, `produce`), not because their score is low. So the floor is "at least one shared
   informative word", and raising it to the 0.34 this project used elsewhere would have rejected
   12 matches that are plainly the same shop.
"""
from __future__ import annotations

import pytest

from locfinder.places.name_match import (
    AGREES,
    DIFFERS,
    UNVERIFIED,
    clears_the_floor,
    match_verdict,
    name_agreement,
    tokens,
)


# --------------------------------------------------------------------------- the three verdicts
def test_a_shared_informative_word_agrees():
    assert match_verdict("Larry's Super Market", "Larry's Supermarket") == AGREES


def test_two_informative_names_sharing_nothing_differ():
    """`Flower Gallery` sat 32.6 m from an OSM `Harris Teeter` and was proposed as a supermarket."""
    assert match_verdict("Flower Gallery", "Harris Teeter") == DIFFERS


def test_an_unnamed_osm_feature_is_unverified_rather_than_a_disagreement():
    """OSM shops mapped off a building often carry no name. That is silence, not contradiction,
    and calling it a disagreement would throw away the only signal those rows have."""
    assert match_verdict("Flower Gallery", "") == UNVERIFIED


def test_a_name_made_only_of_category_words_is_unverified():
    """"Grocery Store" tells us nothing about WHICH grocery store, so it can neither confirm nor
    contradict the feature it sits on."""
    assert match_verdict("Grocery Store", "Food Lion") == UNVERIFIED


def test_only_agreement_clears_the_floor():
    assert clears_the_floor(AGREES)
    assert not clears_the_floor(DIFFERS)
    assert not clears_the_floor(UNVERIFIED)


# ------------------------------------------------- finding 1: the float cannot be the gate
def test_both_kinds_of_zero_score_zero_which_is_why_the_gate_is_not_the_number():
    """This is the whole argument for `match_verdict` existing. If a future session replaces the
    verdict with `agreement > 0`, this test still passes -- and the next one fails."""
    assert name_agreement("Flower Gallery", "Harris Teeter") == 0.0
    assert name_agreement("Flower Gallery", "") == 0.0


def test_the_two_kinds_of_zero_get_different_verdicts():
    assert match_verdict("Flower Gallery", "Harris Teeter") != match_verdict("Flower Gallery", "")


# ------------------------------------- finding 2: a Jaccard threshold would reject real matches
@pytest.mark.parametrize(
    "ours,theirs,score",
    [
        # Measured rows from grocery-unclassified-prefill.csv, with the score the old
        # 0.34 "names agree" threshold scored them at. Every one is the same shop.
        ("Walmart Grocery Pickup and Delivery", "Walmart Supercenter", 0.25),
        ("Handee Hugo 77", "Han Dee Hugo", 0.25),
        ("Angadi Halal Meat Market", "Angadi - Indian Grocery Store", 0.25),
        ("Brier Creek Walmart", "Walmart Supercenter", 0.25),
        ("Apna Bazar", "Apna Bazaar", 0.33),
        ("La Marqueta Tienda y Carniceria", "La Marqueta", 0.33),
    ],
)
def test_real_matches_below_the_old_034_threshold_still_clear_the_floor(ours, theirs, score):
    assert name_agreement(ours, theirs) < 0.34, "this case is no longer below the old threshold"
    assert clears_the_floor(match_verdict(ours, theirs)), (
        f"{ours!r} vs {theirs!r} scored {score} and is the same shop; a Jaccard floor loses it"
    )


# ------------------------------------------------------------------------ the token rules
def test_category_words_carry_no_information():
    assert tokens("Grocery Store Market Food Supermarket Pharmacy") == set()


def test_words_of_two_letters_or_fewer_are_dropped():
    assert tokens("H Mart Cary") == {"mart", "cary"}


def test_agreement_is_symmetric():
    a, b = "H Mart Cary", "H Mart"
    assert name_agreement(a, b) == name_agreement(b, a)


def test_agreement_is_reported_as_a_fraction_not_a_verdict():
    """The float is still published in every sheet, because a reader disagreeing with the gate
    needs to see how close the call was."""
    assert name_agreement("Food Lion", "Food Lion") == 1.0
    assert 0.0 < name_agreement("H Mart Cary", "H Mart") < 1.0
    # 0.5, not 1.0: both `market` and `supermarket` are category words, so the union is
    # {larry, super} against {larry}. The sheet prints 0.50 for this row.
    assert name_agreement("Larry's Super Market", "Larry's Supermarket") == 0.5


# ------------------------------------------------------------- the four scripts that import these
def test_the_prefill_script_still_exports_what_four_other_scripts_import():
    """`measure_fsq_accuracy`, `measure_fsq_coverage`, `crosscheck_fsq_closures` and
    `shortlist_fsq_pharmacy` all do `from prefill_from_osm import name_agreement`. Moving the
    function into the library must not break them."""
    import pathlib
    import sys

    scripts = pathlib.Path(__file__).resolve().parent.parent / "scripts"
    sys.path.insert(0, str(scripts))
    try:
        import prefill_from_osm
    finally:
        sys.path.remove(str(scripts))
    assert prefill_from_osm.name_agreement is name_agreement
    assert prefill_from_osm.tokens is tokens
# --------------------------------------------------------------------------------------------
# Found by the adversarial review of 2026-11-18 (`docs/reviews/2026-11-18-name-floor-review-
# prompt.md`, finding 2), which is the whole reason that review was run. The floor withheld a
# CORRECT supermarket proposal for two IDENTICAL names 12.0 m apart, because every word in them
# is erased: `a` and `c` by the length rule, `supermarket` by the stop list. "Nothing to compare"
# was the wrong reading -- there was plenty to compare, the tokeniser had just thrown it away.
#
# The fix is a fallback, not a special case for equality: when the strict token set is empty on
# either side, both sides are retried WITHOUT the length filter. An initialism is a name.
def test_two_identical_names_agree_even_when_every_word_is_erased():
    """`A&C Supermarket` against itself, 12.0 m apart in grocery-unclassified-prefill.csv."""
    assert tokens("A&C Supermarket") == set(), "the premise of the bug has changed"
    assert match_verdict("A&C Supermarket", "A&C Supermarket") == AGREES


def test_the_fallback_survives_punctuation_and_spacing():
    assert match_verdict("A&C Supermarket", "A & C Supermarket") == AGREES


def test_the_fallback_still_separates_two_different_initialisms():
    """The fallback must not turn into "any short name matches any other"."""
    assert match_verdict("A&C Supermarket", "B&B Supermarket") == DIFFERS
    assert match_verdict("A1 Grocery", "A2 Grocery") == DIFFERS
    # NOT `A1 Food Mart` vs `A2 Food Mart`, which was this test's first version and was wrong:
    # those two share the informative token `mart` and never reach the fallback at all. That
    # raised the question of whether `mart` belongs in STOP_WORDS; measured across both sheets,
    # exactly ONE agreement rests on `mart` alone -- `H Mart Cary` against `H Mart` at 2.2 m,
    # which is correct -- so adding it would break the only case it touches. It stays.


def test_a_name_that_is_only_category_words_is_still_unverified_after_the_fallback():
    """The fallback drops the LENGTH rule, not the stop list. `Grocery Store` still says nothing
    about which grocery store, so the unverified case is preserved rather than papered over."""
    assert match_verdict("Grocery Store", "Food Lion") == UNVERIFIED
    assert match_verdict("Flower Gallery", "") == UNVERIFIED


def test_the_fallback_only_fires_when_the_strict_pass_is_empty():
    """A long informative name must not be re-scored on short words it happens to share."""
    assert match_verdict("Harris Teeter", "H Mart") == DIFFERS
# --------------------------------------------------------------------------------------------
# Adversarial review finding 5: the `weak` suffix was concatenated onto an EMPTY proposal, so a
# pharmacy row matched to an OSM `shop=convenience` -- a tag with no pharmacy mapping -- produced
# a non-empty cell containing nothing but the warning text. Twelve pharmacy rows had this shape,
# and the measurement I wrote then counted all twelve as proposals: 102/29 (28.4%) instead of
# 90/17 (18.9%). A warning is not a proposal.
def test_a_warning_suffix_is_never_a_proposal_on_its_own():
    import pathlib
    import sys

    scripts = pathlib.Path(__file__).resolve().parent.parent / "scripts"
    sys.path.insert(0, str(scripts))
    try:
        from prefill_from_osm import proposal_text
    finally:
        sys.path.remove(str(scripts))

    assert proposal_text("", ("shop", "convenience")) == ""
    assert proposal_text("pharmacy", ("shop", "convenience")).startswith("pharmacy")
    assert "weak" in proposal_text("pharmacy", ("shop", "convenience"))
    assert proposal_text("pharmacy", ("amenity", "pharmacy")) == "pharmacy"
