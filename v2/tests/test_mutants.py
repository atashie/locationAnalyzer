"""Every historical wrong implementation must still be caught by at least one layer.

**This is the guard on the guards.** `feedback-benchmark-over-point-fixes` records the experiment
that matters here: pass 14 reverted four historical fixes and found the benchmark I had called the
guard turned **none** of its assertions red — the unit tests were the real guard all along. So a
claim that a suite protects something is worth nothing until the fix is reverted and the suite is
watched. That is what this file does, on a schedule: every time it runs.

It is also how three unguarded fixes were found. When this check first ran, the orientation bit, the
zero-span branch and the route's partial traversals were all repaired and **nothing anywhere would
have noticed if they regressed**. The absolute anchors in `test_invariants.py` exist because of this
file.
"""

from __future__ import annotations

import pytest

from locfinder.measure.conformance import check
from locfinder.measure.conformance_cases import CASES
from locfinder.measure.invariants import invariant_violations
from locfinder.measure.mutants import MUTANTS


def corpus_failures() -> list[str]:
    return [f"{case.name}: {problem}" for case in CASES for problem in check(case)]


def test_both_layers_are_clean_on_the_real_implementation():
    """The control. Without this, "the mutant is caught" could mean "everything always fails"."""
    assert invariant_violations() == []
    assert corpus_failures() == []


@pytest.mark.parametrize("name", sorted(MUTANTS), ids=sorted(MUTANTS))
def test_every_historical_mutant_is_caught_by_at_least_one_layer(name):
    """Install the wrong implementation and require some layer to reject it.

    The two layers are **complementary**, and this test deliberately does not demand that both
    catch everything: the corpus catches boundary and value defects, the invariants catch domain and
    representation defects. Demanding both would force padding one suite with the other's cases.
    """
    with MUTANTS[name]():
        invariants = invariant_violations()
        corpus = corpus_failures()
    assert invariants or corpus, (
        f"{name} passes both the conformance corpus and the invariant layer. It is a defect a "
        "review already found, so nothing guards it: add the check that separates it before "
        "treating the fix as protected."
    )


#: The division of labour, as it actually measures — recorded so a change in it is visible rather
#: than discovered later. `True` means that layer rejects the mutant.
EXPECTED_COVERAGE = {
    # (caught by invariants, caught by the conformance corpus)
    #
    # The connector-free cost moved from (False, True) to (True, True) when the absolute connector
    # anchor was added. That row escaping the invariants was the evidence, available all along, that
    # no scaling check could establish connector inclusion -- a zero intercept is affine and
    # non-negative. Pass-22 F3 had to point it out before I read my own table.
    "pass20-F1-connector-free-cost": (True, True),
    "pass20-F4-identity-keyed-dedup": (True, True),
    "pass20-F5-strict-cap": (False, True),
    "pass21-F1-rounded-occurrence-bucket": (True, False),
    "pass21-F4-dropped-zero-span": (True, False),
    "pass21-F5-route-without-partials": (True, False),
    "pass21-F6-rank-without-cost": (True, False),
    "pass21-F7-bit-complemented-orientation": (True, False),
    # The mutant that defeated the whole instrument, now caught by the hop-depth anchors. It still
    # escapes the corpus, because no named case needs a journey more than four edges deep -- which
    # is worth keeping visible rather than fixing by padding the corpus.
    "pass22-F2-bounded-path-enumeration": (True, False),
    # The sentinel. Caught by both, and if it ever stops being caught by both, every other row here
    # is unsupported -- see `test_a_sentinel_evaluator_mutation_reaches_both_layers`.
    "pass22-F8-inflated-evaluate": (True, True),
    # Pass 23's three. F1 and F4 each defeated the entire instrument as it stood after pass 22, and
    # for the same reason as F2 before them: an undeclared dimension. F1's was destination
    # cardinality, F4's was absolute-coordinate dependence of identity. Both are now caught by
    # absolute anchors, because a relative invariant sees neither a positional truncation nor a
    # defect that only appears far from the origin.
    "pass23-F1-bounded-destinations": (True, False),
    "pass23-F4-coordinate-dependent-orientation": (True, False),
    "pass23-F8-connector-free-reported-cost": (True, True),
    # The estimand design revision 9 replaced, not a defect a review found. The invariant layer
    # catches it through the subdivision signature and the `subdivision_sensitive` scenario; the
    # corpus does not, because both reading-marked cases survive the amendment unchanged -- which
    # is part of the evidence that settled it.
    "revision9-per-segment-candidate-band": (True, False),
}


@pytest.mark.parametrize("name", sorted(EXPECTED_COVERAGE), ids=sorted(EXPECTED_COVERAGE))
def test_the_division_of_labour_between_the_two_layers_is_as_recorded(name):
    """Which layer catches which, pinned.

    Not because the split matters in itself, but because a drift in it is information: if the
    invariant layer starts catching the strict cap, some invariant has become absolute and that is
    worth knowing; if it stops catching the occurrence bucket, the domain has shrunk.
    """
    want_invariants, want_corpus = EXPECTED_COVERAGE[name]
    with MUTANTS[name]():
        got_invariants = bool(invariant_violations())
        got_corpus = bool(corpus_failures())
    assert (got_invariants, got_corpus) == (want_invariants, want_corpus), (
        f"{name}: invariants {got_invariants} (recorded {want_invariants}), "
        f"corpus {got_corpus} (recorded {want_corpus})"
    )


def test_the_invariant_layer_catches_what_no_named_case_does():
    """The argument for the approach change, as an assertion.

    Five of the eight mutants escape the conformance corpus entirely, and the invariant layer
    catches all five. Three of those were pass 21's, found in code that had just been fixed in
    response to pass 20 — which is the pattern the invariant layer was built to break.
    """
    corpus_blind, invariant_blind = [], []
    for name, mutant in MUTANTS.items():
        with mutant():
            corpus, invariants = bool(corpus_failures()), bool(invariant_violations())
        if not corpus:
            corpus_blind.append((name, invariants))
        if not invariants:
            invariant_blind.append((name, corpus))

    assert len(corpus_blind) == 9, f"{len(corpus_blind)} mutants escape the corpus, recorded 9"
    assert [n for n, caught in corpus_blind if not caught] == []

    # and the other direction, which is why neither layer may be dropped: a uniformly tightened cap
    # preserves every relative property, and only an exact-boundary case sees it. The
    # connector-free cost used to be the second entry here and is now caught by both, because
    # pass-22 F3 made the connector an absolute anchor instead of an inference from an intercept.
    assert len(invariant_blind) == 1, (
        f"{len(invariant_blind)} mutants escape the invariants, recorded 1")
    assert [n for n, caught in invariant_blind if not caught] == []


def test_a_sentinel_evaluator_mutation_reaches_both_layers():
    """The guard on the harness, which pass-22 F8 showed was absent.

    A harness that cannot reach the code it patches reports every mutant as caught by somebody else,
    and every row of `EXPECTED_COVERAGE` then measures nothing. This installs the grossest possible
    mutation -- 1000 s added to every finite reported time, turning a 100 s PASS into an 1100 s FAIL
    -- and requires **both** layers to reject it. It is the only mutant for which both are demanded.

    It is here because the same defect was fixed once and not generalised. Pass 21's orientation
    mutant read as uncaught by everything until `invariants.py` stopped importing
    `directed_identity` by name. I fixed that one binding. Pass 22 then patched `toy.evaluate` and
    found `invariant_violations()` returning `[]` and every corpus `check()` clean, because both
    modules still bound `evaluate` at import. Fixing the example instead of the domain, in the file
    whose docstring is about not doing that.
    """
    from locfinder.measure.mutants import inflated_evaluate
    with inflated_evaluate():
        invariants = invariant_violations()
        corpus = corpus_failures()
    assert invariants, (
        "the invariant layer cannot see a `toy.evaluate` replacement, so it is not calling the "
        "module attribute and its coverage measurements are unsupported"
    )
    assert corpus, (
        "the conformance corpus cannot see a `toy.evaluate` replacement, so `Case.run` is not "
        "calling the module attribute and its coverage measurements are unsupported"
    )
