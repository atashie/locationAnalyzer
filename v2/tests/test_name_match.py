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
