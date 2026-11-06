"""The conformance suite's machinery: case format, the §7 accounting, and the §2.5 bound rule.

Design §12 artifact 3 — "independently derived expected results on constructed cases". The corpus
itself is `conformance_cases.py`; this module holds what the corpus is checked *with*.

## Three authorities, and why

The execution plan requires that "derived independently of T3" be **evidenced, not asserted**, and
notes that "written before T3 is complete" is not evidence and a digest proves immutability rather
than correctness. So every case carries:

* **a hand-derived expected value** with its arithmetic written out in `derivation`, taken where
  possible from a review pass's own executed counterexample rather than computed now;
* **its provenance** — which pass or which design section the case comes from;
* **the oracle's answer**, from `toy.evaluate`, which enumerates every journey and so shares no
  algorithm with the reference comparator.

The suite requires the hand value and the oracle to agree. Neither route calls T3. Where they
disagree the case is a finding about the design or about one of the two routes, and it is resolved
before T3 sees it.

## The tolerance, and why it cannot be the pass-18 defect again

Times are compared at `TIME_TOL_S`, because float accumulation order is an implementation choice the
design explicitly permits: the two-connector case sums `1/1.26 + 100 + 1/1.26` where the hand
derivation writes `2/1.26 + 100`, and those differ by **1.42e-14 s**. A declared tolerance is
therefore necessary.

But a declared tolerance is exactly what pass 18 exploited against T1: at the 0.002 tolerance then
stated, an implementation wrong at a single point passed every fixture while flipping a verdict. A
small number is not an argument. So the tolerance is **proved decision-irrelevant per case**:
`tolerance_is_decision_irrelevant` checks that the PASS/FAIL verdict at every published threshold is
identical at `expected - TIME_TOL_S` and `expected + TIME_TOL_S`, and the suite refuses a case where
it is not. A case whose true time sits within a nanosecond of a threshold cannot be admitted with a
tolerance at all, and the suite says so rather than hiding it.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from enum import Enum

from ..status import Outcome
from . import toy
from .toy import ToyEdge, ToyGraph, OracleResult

#: Declared absolute tolerance on a time in seconds: about **70,400x** the observed
#: float-association spread of 1.42e-14 s, and about 11 orders below the smallest published
#: threshold of 600 s. (An earlier comment here said "~500x", which was simply wrong —
#: pass-20 recomputed the ratio.) Never used without `tolerance_is_decision_irrelevant`,
#: and it bounds only the oracle-versus-hand **time** comparison: it says nothing about
#: cost-argmin stability, cap equality or selected provenance.
TIME_TOL_S = 1e-9

#: Design §1 and the execution plan §1: the published thresholds, in minutes.
PUBLISHED_THRESHOLDS_MIN = (10, 15, 25, 45)


# ----------------------------------------------------------------------------- the comparator's verdict


class ComparatorOutcome(str, Enum):
    """What the comparator decided. Distinct from `status.Outcome`, which is the *product's*.

    `UNRESOLVED` is design §7's third column: timeout, engine error, snap failure, or no sound bound.
    It is not a failure of the point; it is a failure of the measurement at that point, and §7
    bounds it in one direction only.
    """

    PASS = "PASS"
    FAIL = "FAIL"
    UNRESOLVED = "UNRESOLVED"


def comparator_outcome(*, threshold_s: float, time_s: float | None, search_bounded: bool,
                       exhausted: bool, bound_metric: str | None = None,
                       bound_value: float | None = None,
                       bound_strict: bool = False) -> ComparatorOutcome:
    """Design §2.5's four branches, in the design's order.

    The finite-time branch is **first** because the others are only reached when nothing was found —
    revision 3 ordered them the other way and made a found route unreachable behind a bound rule.

    A bound is usable **only** as a sound lower bound on travel time. `bound_metric="cost"` supplies
    nothing: one edge of time 1 and cost 121 under a cost limit of 60 returns `inf`, while objective 2
    returns **1 second**, so treating the cost limit as a bound would fail *T* = 60 for a route that
    passes in one.

    `NO_PATH` may never be reported from a bounded search, so exhaustion only decides when
    `search_bounded` is false — exhaustiveness is a property of the invocation, which is why
    `status.node_reasons` requires keyword-only `search_bounded`.
    """
    if time_s is not None:
        # Design §2.5's first branch is "a finite time **was found**", and `is not None` is not that
        # test. Pass-20 F11: `inf` is how this repository represents a routing non-result, and it
        # arrived here as a definitive **FAIL**, while `-inf` arrived as **PASS**. Ten such points
        # against a product PASS move the gate from INCONCLUSIVE (`k`=0, `u`=10) to FAIL (`k`=10),
        # on no established point failure at all. A non-result must be normalised to `None` by its
        # caller, carrying its termination reason and bound, not passed through as a number.
        if not math.isfinite(time_s):
            raise ValueError(
                f"time_s must be a finite number of seconds or None, got {time_s!r}: a non-result "
                "carries a reason and a bound, and cannot be a verdict"
            )
        if time_s < 0:
            raise ValueError(f"time_s must be non-negative, got {time_s!r}")
        return ComparatorOutcome.PASS if time_s <= threshold_s else ComparatorOutcome.FAIL
    if exhausted and not search_bounded:
        return ComparatorOutcome.FAIL          # NO_PATH: definitive, fails every finite threshold
    if bound_metric == "time" and bound_value is not None:
        over = bound_value > threshold_s or (bound_strict and bound_value >= threshold_s)
        if over:
            return ComparatorOutcome.FAIL
    return ComparatorOutcome.UNRESOLVED


# ----------------------------------------------------------------------------- design §7's accounting


class Bucket(str, Enum):
    """The role each cell of §7's cross-tab plays. Seven roles over nine cells: agreement and
    unwarranted abstention each cover two cells."""

    AGREEMENT = "agreement"
    E1A = "E1a"                                   # product FAIL, comparator PASS — false exclusion
    E1B = "E1b"                                   # product PASS, comparator FAIL — false inclusion
    E1A_UNRESOLVED = "E1a-unresolved"
    E1B_UNRESOLVED = "E1b-unresolved"
    E0_UNWARRANTED = "E0-unwarranted-abstention"  # product UNKNOWN, comparator definitive
    E0_CONFIRMED = "E0-comparator-unresolved"     # product UNKNOWN, comparator unresolved


#: The complete nine-cell table of design §7. Written out rather than computed, so that a reader can
#: check it against the design by eye and a test can assert it is total.
CROSS_TAB: dict[tuple[Outcome, ComparatorOutcome], Bucket] = {
    (Outcome.PASS, ComparatorOutcome.PASS): Bucket.AGREEMENT,
    (Outcome.PASS, ComparatorOutcome.FAIL): Bucket.E1B,
    (Outcome.PASS, ComparatorOutcome.UNRESOLVED): Bucket.E1B_UNRESOLVED,
    (Outcome.FAIL, ComparatorOutcome.PASS): Bucket.E1A,
    (Outcome.FAIL, ComparatorOutcome.FAIL): Bucket.AGREEMENT,
    (Outcome.FAIL, ComparatorOutcome.UNRESOLVED): Bucket.E1A_UNRESOLVED,
    (Outcome.UNKNOWN, ComparatorOutcome.PASS): Bucket.E0_UNWARRANTED,
    (Outcome.UNKNOWN, ComparatorOutcome.FAIL): Bucket.E0_UNWARRANTED,
    (Outcome.UNKNOWN, ComparatorOutcome.UNRESOLVED): Bucket.E0_CONFIRMED,
}


def classify(product: Outcome, comparator: ComparatorOutcome) -> Bucket:
    """Design §7: every sampled point falls in exactly one cell. Nothing is deleted."""
    try:
        return CROSS_TAB[(Outcome(product), ComparatorOutcome(comparator))]
    except KeyError:                                        # pragma: no cover - guarded by a test
        raise ValueError(f"no §7 cell for ({product!r}, {comparator!r})") from None


@dataclass(frozen=True)
class Tally:
    """Design §8's inputs, per direction, with the abstention rows held out.

    `n` is the **full-frame** sample size — every sampled point, including the abstaining ones.
    Abstention is E0's business and contributes to neither direction's `k` nor `u`: that is revision
    5's change, and holding it in code rather than in prose is the point of this class. Revision 3
    counted product `UNKNOWN` into E1b and made the gate unreachable.
    """

    n: int
    k_e1a: int
    u_e1a: int
    k_e1b: int
    u_e1b: int
    abstentions: int
    unwarranted: int
    agreements: int


def tally(pairs) -> Tally:
    """Count §7's cells from `(product_outcome, comparator_outcome)` pairs."""
    counts = dict.fromkeys(Bucket, 0)
    n = 0
    for product, comparator in pairs:
        counts[classify(product, comparator)] += 1
        n += 1
    return Tally(
        n=n,
        k_e1a=counts[Bucket.E1A],
        u_e1a=counts[Bucket.E1A_UNRESOLVED],
        k_e1b=counts[Bucket.E1B],
        u_e1b=counts[Bucket.E1B_UNRESOLVED],
        abstentions=counts[Bucket.E0_UNWARRANTED] + counts[Bucket.E0_CONFIRMED],
        unwarranted=counts[Bucket.E0_UNWARRANTED],
        agreements=counts[Bucket.AGREEMENT],
    )


# ----------------------------------------------------------------------------- the case format


def tolerance_is_decision_irrelevant(time_s: float, *, tol: float = TIME_TOL_S,
                                     thresholds_min=PUBLISHED_THRESHOLDS_MIN) -> bool:
    """True when the PASS/FAIL verdict is the same at `time_s ± tol` for every published threshold.

    This is the check that makes a declared tolerance an argument rather than an assertion. A case
    this returns False for is **refused** by the suite, not quietly admitted.
    """
    for minutes in thresholds_min:
        t = minutes * 60.0
        if (time_s - tol <= t) != (time_s + tol <= t):
            return False
    return True


@dataclass(frozen=True)
class Expected:
    """What a case pins. Every field is optional, so a case about attachment need not assert a cost.

    `None` for `objective1_s` or `objective2_s` means *no finite time exists* — on these graphs an
    exhaustive, unbounded enumeration, so a genuine `NO_PATH` rather than an exhausted budget.
    """

    objective1_s: float | None = None
    objective2_s: float | None = None
    objective2_cost: float | None = None
    objective1_destination: int | None = None
    objective2_destination: int | None = None
    origin_candidates: int | None = None
    eligible: tuple[int, ...] | None = None
    ineligible: tuple[int, ...] | None = None
    no_finite_time: bool = False

    #: Wrong answers this case excludes, as numbers rather than prose. The suite asserts the oracle
    #: is further than `TIME_TOL_S` from each. This is what makes a case evidence: a case that
    #: cannot name a value it separates distinguishes nothing, and `rejects` alone is unchecked text.
    rejected_objective1_s: tuple[float, ...] = ()
    rejected_objective2_s: tuple[float, ...] = ()


@dataclass(frozen=True)
class Case:
    """One conformance case: a constructed graph, a hand-derived answer, and its provenance.

    `derivation` must show the arithmetic, not restate the answer. `provenance` names where the
    expected value comes from — a design section, or the review pass that executed it. `reading`
    records any place where the case depends on a documented interpretation of the design rather than
    on its explicit text, so that a design amendment can find the cases it invalidates.
    """

    name: str
    rule: str                   # which design rule this case is about
    graph: ToyGraph
    origin: tuple[float, float]
    destinations: tuple[tuple[float, float], ...]
    expected: Expected
    derivation: str
    provenance: str
    rejects: str = ""           # the wrong answer this case exists to exclude
    reading: str = ""
    thresholds_min: tuple[int, ...] = PUBLISHED_THRESHOLDS_MIN

    def run(self) -> OracleResult:
        # Through the module attribute: pass-22 F8 found a `toy.evaluate` wrapper
        # invisible to this layer because the name was bound at import.
        return toy.evaluate(self.graph, self.origin, list(self.destinations))


def check(case: Case) -> list[str]:
    """Compare the oracle against the case's hand-derived expectation. Returns failure strings.

    An empty list means the two independent routes agree. Every time comparison is preceded by the
    decision-irrelevance check on the tolerance, so a case cannot pass by virtue of a loose one.
    """
    r = case.run()
    e = case.expected
    bad: list[str] = []

    def cmp_time(label: str, want: float | None, got: float | None) -> None:
        if want is None:
            return
        if got is None:
            bad.append(f"{label}: hand says {want!r}, oracle found no finite time")
            return
        if not tolerance_is_decision_irrelevant(want, thresholds_min=case.thresholds_min):
            bad.append(f"{label}: {want!r} s lies within {TIME_TOL_S} s of a published threshold, "
                       "so no tolerance makes this case decision-safe")
            return
        if abs(got - want) > TIME_TOL_S:
            bad.append(f"{label}: hand says {want!r}, oracle says {got!r} "
                       f"(difference {got - want!r} exceeds {TIME_TOL_S})")

    cmp_time("objective1_s", e.objective1_s, r.objective1_s)
    cmp_time("objective2_s", e.objective2_s, r.objective2_s)

    for label, wrongs, got in (("objective1_s", e.rejected_objective1_s, r.objective1_s),
                               ("objective2_s", e.rejected_objective2_s, r.objective2_s)):
        for wrong in wrongs:
            if got is not None and abs(got - wrong) <= TIME_TOL_S:
                bad.append(f"{label}: oracle returned {got!r}, which this case rejects as {wrong!r}")

    if e.no_finite_time:
        if r.objective1_s is not None:
            bad.append(f"no_finite_time: oracle reached the destination in {r.objective1_s!r} s")
        if r.objective2_s is not None:
            bad.append(f"no_finite_time: oracle's objective 2 is {r.objective2_s!r} s")

    if e.objective2_cost is not None and r.objective2_cost is not None:
        if abs(r.objective2_cost - e.objective2_cost) > TIME_TOL_S:
            bad.append(f"objective2_cost: hand says {e.objective2_cost!r}, "
                       f"oracle says {r.objective2_cost!r}")

    for label, want, got in (
        ("objective1_destination", e.objective1_destination, r.objective1_destination),
        ("objective2_destination", e.objective2_destination, r.objective2_destination),
        ("origin_candidates", e.origin_candidates, r.origin_candidates),
        ("eligible", e.eligible, r.eligible),
        ("ineligible", e.ineligible, r.ineligible),
    ):
        if want is not None and want != got:
            bad.append(f"{label}: hand says {want!r}, oracle says {got!r}")
    return bad


# ----------------------------------------------------------------------------- the frozen digest


def _edge_json(e: ToyEdge) -> dict:
    return {"u": e.u, "v": e.v, "geometry": [list(c) for c in e.geometry],
            "time_s": e.time_s, "cost_base": e.cost_base, "penalty": e.penalty,
            "osmid": list(e.osmid), "oneway": e.oneway}


def case_json(case: Case) -> dict:
    """Canonical serialisation. Includes `derivation` and `provenance`, because the obligation the
    digest protects is that each case *came with* its justification — a digest over the numbers alone
    would let the justification be rewritten without changing the artifact's identity."""
    e = case.expected
    return {
        "name": case.name,
        "rule": case.rule,
        "edges": [_edge_json(x) for x in case.graph.edges],
        "origin": list(case.origin),
        "destinations": [list(d) for d in case.destinations],
        "expected": {
            "objective1_s": e.objective1_s, "objective2_s": e.objective2_s,
            "objective2_cost": e.objective2_cost,
            "objective1_destination": e.objective1_destination,
            "objective2_destination": e.objective2_destination,
            "origin_candidates": e.origin_candidates,
            "eligible": list(e.eligible) if e.eligible is not None else None,
            "ineligible": list(e.ineligible) if e.ineligible is not None else None,
            "no_finite_time": e.no_finite_time,
            "rejected_objective1_s": list(e.rejected_objective1_s),
            "rejected_objective2_s": list(e.rejected_objective2_s),
        },
        "derivation": case.derivation,
        "provenance": case.provenance,
        "rejects": case.rejects,
        "reading": case.reading,
        "thresholds_min": list(case.thresholds_min),
    }


def corpus_digest(cases) -> str:
    """Design §12: the suite is a frozen artifact with a digest.

    A digest proves immutability, not correctness — the plan says so — so this is the weakest of the
    suite's three guarantees and is recorded as such.
    """
    payload = json.dumps([case_json(c) for c in cases], sort_keys=True,
                         separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode()).hexdigest()
