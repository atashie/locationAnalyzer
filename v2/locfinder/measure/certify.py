"""Certified cost comparison — design §12 amendment item 5, step 4 phase 4a.2.

**Why this exists.** §2.4 item 7 fixes the geometry arithmetic, and Codex pass 37 F1 showed what it
cannot fix: correctly rounding every operand does not make the convention's argmin the argmin real
arithmetic would choose. The traversal fraction is irrational, so two candidates whose exact costs
differ by less than one ulp of it can tie or invert, and **no binary64 convention avoids that**.
Item 5 is therefore disclosed and *measured* rather than closed, and this module is what measures
it.

**What a real cost is.** Per §2.4 item 6 a journey total is formed from three kinds of term:

* a **full edge** contributes `cost_base + penalty`, a binary64 — so an exact rational;
* a **partial edge** of fraction *f* contributes `f * (cost_base + penalty)`, where
  `f = span / total` and both are sums of square roots of rationals;
* a **connector** contributes `residual / access_speed`, and the residual is a square root.

So the real cost is a sum of rationals and of rational multiples of quotients of sums of radicals.
It is **not** rational, and no amount of rational arithmetic represents it exactly.

**The method: exact rational intervals, refined.** Every square root is bracketed by two exact
`Fraction`s whose width is exactly `2**-k`, the brackets are propagated through the sums, products
and quotients above with exact rational endpoints, and the two cost intervals are compared. Disjoint
intervals decide the comparison and the decision is **certified**. Overlapping intervals double `k`
and try again, up to a **declared limit**, after which the answer is `UNRESOLVED`.

Termination is honest in both directions. If the two real costs differ, the widths go to zero while
the gap does not, so refinement separates them in finitely many steps. If they are **exactly equal**
it never separates them, and `UNRESOLVED` is then the correct report rather than a failure — at
which point §2.4's travel-time discriminator applies, over the same machinery on the time terms.

**`UNRESOLVED` is never agreement.** Counting it as agreement would be Codex pass 38 F4 over again:
a figure named after one thing measuring another. It is a retained status, the same rule phase 4c
applies to timeouts.
"""
from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, field
from fractions import Fraction

__all__ = [
    "sqrt_interval",
    "Interval",
    "Partial",
    "Journey",
    "AGREES",
    "DIFFERS",
    "UNRESOLVED",
    "Certification",
    "FIRST",
    "SECOND",
    "convention_selection",
    "certify_cheaper",
    "certify_selection",
    "ACCESS_SPEED_MPS",
    "DEFAULT_MAX_PRECISION",
]

#: `access.py`'s straight-line connector speed. §2.2 charges the residual at this speed and §2.6
#: notes the independent engine uses a different one.
ACCESS_SPEED_MPS = Fraction(126, 100)

#: Where refinement stops, stated here rather than buried because the plan's invalidation condition
#: for this phase is about how often it is reached.
#:
#: **It is a budget, not a bound.** The first version of this comment claimed `2**-192` was "far
#: below any gap a binary64 cost can express", and Codex pass 40 F2 refuted it: binary64's smallest
#: positive gap is `2**-1074`, and an admissible query such as `(0, 1e-100)` against a unit segment
#: produces *reported* costs of `7.936507936507937e-101` and `2e-100` that this cap cannot separate
#: — they resolve at 512. So reaching the cap means **refinement ran out of budget**, which is
#: exactly why `UNRESOLVED` is a retained status and is never counted as agreement. A caller who
#: needs more can pass more.
DEFAULT_MAX_PRECISION = 192

AGREES = "AGREES"
DIFFERS = "DIFFERS"
UNRESOLVED = "UNRESOLVED"

Point = tuple[float, float]


def sqrt_interval(q: Fraction | int, k: int) -> tuple[Fraction, Fraction]:
    """Exact rational bounds on `sqrt(q)`, of width exactly `2**-k`.

    With `N = floor(q * 4**k)` and `s = isqrt(N)`:

        s / 2**k  <=  sqrt(q)  <  (s + 1) / 2**k

    **Lower bound:** `s**2 <= N <= q * 4**k`, so `(s / 2**k)**2 <= q`.
    **Upper bound:** `(s + 1)**2 > N = floor(q * 4**k)`, and both sides are integers, so
    `(s + 1)**2 >= floor(q * 4**k) + 1 > q * 4**k`, hence `((s + 1) / 2**k)**2 > q`.

    Both endpoints are exact and no binary64 appears anywhere. Pass 37's lesson applies directly
    here: integer scaling alone is not a rounding proof, so the property above is asserted by
    `test_sqrt_interval_brackets_the_root` on random rationals rather than inferred from the
    construction.

    The intervals are also **nested** in `k`, which is what makes refinement sound:
    `4 * floor(x) <= floor(4x)` gives `s_{k+1} >= 2 * s_k`, and `(s_k + 1)**2 > q * 4**k` gives
    `s_{k+1} <= 2 * s_k + 1`.
    """
    q = Fraction(q)
    if q < 0:
        raise ValueError(f"no real square root of a negative rational: {q}")
    if k < 0:
        raise ValueError(f"precision must be non-negative: {k}")
    scale = 1 << (2 * k)
    unit = Fraction(1, 1 << k)
    n = (q * scale).numerator // (q * scale).denominator      # floor, exactly
    s = math.isqrt(n)
    return (s * unit, (s + 1) * unit)


@dataclass(frozen=True)
class Interval:
    """A closed rational interval. Endpoints are exact, so no operation here rounds."""

    lo: Fraction
    hi: Fraction

    def __post_init__(self) -> None:
        if self.lo > self.hi:
            raise ValueError(f"an inverted interval: [{self.lo}, {self.hi}]")

    @property
    def width(self) -> Fraction:
        return self.hi - self.lo

    def __add__(self, other: "Interval") -> "Interval":
        return Interval(self.lo + other.lo, self.hi + other.hi)

    def scaled(self, c: Fraction) -> "Interval":
        """Multiply by a rational. Negative scalars swap the endpoints rather than invert them."""
        return Interval(c * self.lo, c * self.hi) if c >= 0 else Interval(c * self.hi, c * self.lo)

    def divided_by(self, other: "Interval") -> "Interval":
        """Divide by an interval that does not contain zero, by the extrema of the four quotients.

        Codex pass 40 F4: the first version returned `[lo/other.hi, hi/other.lo]`, which is only the
        enclosure when the numerator is non-negative. On `[-1,1] / [1,2]` it returned `[-1/2, 1]`
        and **excluded the attainable -1**; on `[-2,-1] / [1,4]` it built an inverted interval and
        raised. Every traversal span this module forms is non-negative, so no published figure went
        through those cases — but an unsound public primitive is a defect whether or not today's
        caller reaches it.

        Pass 40 F6 also showed the guard was wrong about its own scope: it rejected only a
        non-positive *lower* endpoint, so a wholly negative denominator such as `[-2,-1]` passed
        and divided. The condition is now "contains zero", which is what division cannot survive.
        """
        if other.lo <= 0 <= other.hi:
            raise ZeroDivisionError(
                f"a denominator interval containing zero: [{other.lo}, {other.hi}]. A zero-length "
                "record contributes the normative fraction 0 and must not reach a division")
        quotients = (self.lo / other.lo, self.lo / other.hi,
                     self.hi / other.lo, self.hi / other.hi)
        return Interval(min(quotients), max(quotients))

    def contains(self, value: Fraction) -> bool:
        return self.lo <= value <= self.hi

    def strictly_below(self, other: "Interval") -> bool:
        return self.hi < other.lo


def _exact(value: float) -> Fraction:
    """A binary64 as the rational it is. Every finite binary64 is one; non-finite ones are refused."""
    if not math.isfinite(value):
        raise ValueError(f"a non-finite quantity has no exact rational value: {value!r}")
    return Fraction(value)


def _radicands(geometry: tuple[Point, ...]) -> list[Fraction]:
    """Each segment's `dx**2 + dy**2`, exactly. The lengths are their square roots."""
    out: list[Fraction] = []
    for (ax, ay), (bx, by) in itertools.pairwise(geometry):
        dx, dy = _exact(bx) - _exact(ax), _exact(by) - _exact(ay)
        out.append(dx * dx + dy * dy)
    return out


@dataclass(frozen=True)
class Partial:
    """A traversal of part of one record, as §2.2 describes an occurrence pair on it.

    `cost` is `cost_base + penalty` **already formed**, which is §2.4 item 6's rule: the fraction
    multiplies the formed total and never the components separately.
    """

    geometry: tuple[Point, ...]
    seg_o: int
    t_o: Fraction
    seg_d: int
    t_d: Fraction
    cost: float

    def fraction_interval(self, k: int) -> Interval:
        """The real traversal fraction, bracketed. Zero total length is the normative 0."""
        qs = _radicands(self.geometry)
        if not qs:
            return Interval(Fraction(0), Fraction(0))
        # §2.4 item 7's zero-total rule, decided on the EXACT radicands and not on their brackets.
        # `sqrt_interval(0, k)` is `(0, 2**-k)`, so a bracketed total is never exactly zero and a
        # test on it would miss every zero-length record -- then divide by an interval reaching zero.
        if all(q == 0 for q in qs):
            return Interval(Fraction(0), Fraction(0))
        total = Interval(Fraction(0), Fraction(0))
        for q in qs:
            lo, hi = sqrt_interval(q, k)
            total = total + Interval(lo, hi)

        seg_o, t_o, seg_d, t_d = self.seg_o, self.t_o, self.seg_d, self.t_d
        if (seg_o, t_o) > (seg_d, t_d):
            seg_o, t_o, seg_d, t_d = seg_d, t_d, seg_o, t_o

        def part(idx: int, frac: Fraction) -> Interval:
            lo, hi = sqrt_interval(frac * frac * qs[idx], k)
            return Interval(lo, hi)

        if seg_o == seg_d:
            span = part(seg_o, abs(t_d - t_o))
        else:
            span = part(seg_o, Fraction(1) - t_o)
            for q in qs[seg_o + 1:seg_d]:
                lo, hi = sqrt_interval(q, k)
                span = span + Interval(lo, hi)
            span = span + part(seg_d, t_d)
        if total.lo <= 0:
            # The bracket on a positive total has not yet excluded zero; refine rather than divide.
            raise _NeedsPrecision(k)
        return span.divided_by(total)


class _NeedsPrecision(Exception):
    """A bracket is too loose to divide by. Raised inward, never out of this module."""


@dataclass(frozen=True)
class Journey:
    """A journey's cost as §2.4 item 6 forms it: full edges, partial edges, connectors.

    `label` carries whatever the caller uses to name the selection — a destination id, a fixture
    name — so a `DIFFERS` result can record *both* selections rather than only that they differ.
    """

    full_edge_costs: tuple[float, ...] = ()
    partials: tuple[Partial, ...] = ()
    #: exact squared residuals; each contributes `sqrt(sq) / access_speed`
    connector_sq: tuple[Fraction, ...] = ()
    label: str = ""
    access_speed: Fraction = field(default=ACCESS_SPEED_MPS)
    #: The journey's reported travel time, which is what §2.4's key uses to break an exact cost tie.
    #: Codex pass 40 F8: this class had no time at all, so a caller could only **stipulate** which
    #: journey the convention selects. `convention_selection` below derives it instead.
    time_s: float = 0.0

    def cost_interval(self, k: int) -> Interval:
        exact_part = sum((_exact(c) for c in self.full_edge_costs), Fraction(0))
        out = Interval(exact_part, exact_part)
        for p in self.partials:
            out = out + p.fraction_interval(k).scaled(_exact(p.cost))
        for sq in self.connector_sq:
            lo, hi = sqrt_interval(sq, k)
            out = out + Interval(lo, hi).scaled(Fraction(1) / self.access_speed)
        return out

    def rounded_cost(self) -> float:
        """What the normative convention computes: §2.4 item 6's exactly-rounded sum of its terms.

        Imported lazily so this module can be read, and `sqrt_interval` used, without pulling in the
        geometry primitives.
        """
        from locfinder.measure import exact as ex

        terms: list[float] = list(self.full_edge_costs)
        for p in self.partials:
            f = ex.same_edge_fraction(p.geometry, p.seg_o, p.t_o, p.seg_d, p.t_d)
            terms.append(f * p.cost)
        for sq in self.connector_sq:
            terms.append(ex.rational_sqrt(sq) / float(self.access_speed))
        return math.fsum(terms)


@dataclass(frozen=True)
class Certification:
    """The result of certifying one selection against its alternatives."""

    status: str
    #: the label the convention selected
    convention: str
    #: the label the certified comparison selected, when it could
    certified: str | None
    #: the precision reached, as the exponent `k` of the final interval width `2**-k`
    precision: int
    #: set when `UNRESOLVED`: whether the two costs are in fact **exactly equal**, which is the
    #: difference between the correct answer and the failure this phase is boxed against
    exactly_tied: bool | None = None

    @property
    def agrees(self) -> bool:
        """True only for `AGREES`. `UNRESOLVED` is not agreement and must not be counted as it."""
        return self.status == AGREES


#: What `certify_cheaper` returns: which of its two *arguments* won, never a label.
FIRST = "FIRST"
SECOND = "SECOND"


def certify_cheaper(a: Journey, b: Journey, *,
                    max_precision: int = DEFAULT_MAX_PRECISION) -> tuple[str | None, int]:
    """Which of two journeys is cheaper in **real** arithmetic, or `None` if undecided.

    Returns `FIRST`, `SECOND` or `None`, with the largest precision **actually evaluated**.

    **It identifies the winner positionally, not by label.** Codex pass 40 F1: the first version
    returned `a.label` or `b.label` and the caller tested `winner == other.label`, so two journeys
    sharing a label — and `label` defaults to `""` — made a win for the selected journey read as a
    win for its alternative. `certify_selection([Journey(cost 1), Journey(cost 2)], chosen=0)`
    returned **DIFFERS** where the answer is plainly AGREES. A label is for reporting; it must never
    carry identity.

    **Every precision reported here was evaluated.** Pass 40 F2: the loop used to double past the
    cap and then report `min(k, max_precision)`, so a default run reported precision 192 having
    tried only 8, 16, 32, 64 and 128 — and the comparison it declared undecided was in fact decided
    at 192. The sequence now ends *on* the cap.
    """
    k, tried = 8, 0
    while True:
        k = min(k, max_precision)
        try:
            ia, ib = a.cost_interval(k), b.cost_interval(k)
            tried = k
            if ia.strictly_below(ib):
                return (FIRST, k)
            if ib.strictly_below(ia):
                return (SECOND, k)
        except _NeedsPrecision:
            pass
        if k >= max_precision:
            return (None, tried)
        k *= 2


def convention_selection(candidates: list[Journey]) -> int:
    """The index §2.4's convention selects for objective 2: the cost argmin, then smallest time.

    This exists because of Codex pass 40 F8. The divergence measurement used to pass `chosen=1`
    directly, on the stated ground that the competing journey "is given the smaller travel time, so
    the convention always selects B" — while `Journey` carried **no time field**, so nothing in the
    experiment tested that. The claim was a stipulation dressed as a consequence. Deriving the
    selection here makes it a consequence.

    The rule implemented is §2.4's first two keys on the rounded quantities, which is what
    `toy.evaluate` computes: `cheapest = min(cost)`, then the smallest `time_s` among journeys of
    exactly that cost. The destination and route keys are not modelled here — this module compares
    costs, and a caller needing those must break the remaining tie itself.
    """
    if not candidates:
        raise ValueError("no candidates to select from")
    costs = [j.rounded_cost() for j in candidates]
    cheapest = min(costs)
    tied = [i for i, cost in enumerate(costs) if cost == cheapest]
    return min(tied, key=lambda i: candidates[i].time_s)


def certify_selection(candidates: list[Journey], chosen: int, *,
                      max_precision: int = DEFAULT_MAX_PRECISION) -> Certification:
    """Did the convention's selection match the real argmin?

    `chosen` is the index the normative convention selected. Every other candidate is compared
    against it; the first that is certified **strictly cheaper** makes this `DIFFERS`, and an
    undecided comparison makes it `UNRESOLVED` — which takes precedence over `AGREES`, because an
    undecided pair is exactly the case where agreement is unknown.
    """
    if not candidates:
        raise ValueError("no candidates to certify")
    if not 0 <= chosen < len(candidates):
        raise IndexError(f"selection {chosen} is not among {len(candidates)} candidates")
    picked = candidates[chosen]
    worst_k = 0
    undecided: list[Journey] = []
    for i, other in enumerate(candidates):
        if i == chosen:
            continue
        winner, k = certify_cheaper(picked, other, max_precision=max_precision)
        worst_k = max(worst_k, k)
        if winner is None:
            undecided.append(other)
            continue
        if winner is SECOND:
            return Certification(DIFFERS, picked.label, other.label, k)
    if undecided:
        # Every undecided alternative is examined, not only the first. Pass 40 F3: with one
        # recognisable tie and one unrecognisable unequal pair, the answer used to depend on which
        # came first in the list -- so a diagnostic treating "tied" as harmless could be handed a
        # True while an unequal pair sat unresolved behind it. `None` means unknown, and unknown is
        # the answer whenever any alternative cannot be settled either way.
        verdicts = [_exactly_tied(picked, other) for other in undecided]
        tied: bool | None
        if any(v is None for v in verdicts):
            tied = None
        elif all(v for v in verdicts):
            tied = True
        else:
            tied = False
        return Certification(UNRESOLVED, picked.label, None, worst_k, exactly_tied=tied)
    return Certification(AGREES, picked.label, picked.label, worst_k)


def _exactly_tied(a: Journey, b: Journey) -> bool | None:
    """`True` if two undecided costs are provably equal, `False` if provably unequal, else `None`.

    This is what the phase's invalidation condition needs: `UNRESOLVED` on an exact tie is the
    correct answer, while `UNRESOLVED` on an **unequal** pair is the approach failing. Codex pass 40
    F3: the first version returned a plain `bool` and answered `False` both for "provably unequal"
    and for "cannot tell", so the measurement's "NOT tied" column silently included every pair with
    an irrational term — which is most of them — and the invalidation message could not be relied
    on. Unknown is now its own answer.

    **What this actually decides, narrowly.** A journey whose every term is rational has a
    *degenerate* cost interval — a point — so two such journeys separate at the first precision
    unless their costs are equal. The `ra == rb` below is therefore reached only when both costs are
    rational **and** the comparison was undecided, which for point intervals means they are equal:
    it returns `True` every time it is evaluated. So this function's real content is "are both costs
    recognisably rational", and the equality test records the intent rather than discriminating. The
    mutation harness proves that by being unable to distinguish `return True`, and says so instead
    of reporting an uncaught mutation forever.
    """
    ra, rb = _rational_cost(a), _rational_cost(b)
    if ra is None or rb is None:
        return None
    return ra == rb


def _rational_cost(j: Journey) -> Fraction | None:
    """A journey's exact cost when every term happens to be rational, else `None`.

    Pass 40 F3: connectors used to disqualify a journey outright, so two identical journeys with
    `connector_sq=(Fraction(1),)` — whose costs are both exactly `50/63` — were reported as not
    tied. A connector's residual is rational exactly when its squared residual is a perfect
    rational square, which is cheap to test, so those cases are now recognised.
    """
    total = sum((_exact(c) for c in j.full_edge_costs), Fraction(0))
    for sq in j.connector_sq:
        root = _rational_sqrt_exact(Fraction(sq))
        if root is None:
            return None
        total += root / j.access_speed
    for p in j.partials:
        qs = _radicands(p.geometry)
        # Rational only if every length involved is rational, which needs every radicand to be a
        # perfect rational square. Checked, not assumed.
        roots: list[Fraction] = []
        for q in qs:
            r = _rational_sqrt_exact(q)
            if r is None:
                return None
            roots.append(r)
        if not roots or sum(roots) == 0:
            continue
        seg_o, t_o, seg_d, t_d = p.seg_o, p.t_o, p.seg_d, p.t_d
        if (seg_o, t_o) > (seg_d, t_d):
            seg_o, t_o, seg_d, t_d = seg_d, t_d, seg_o, t_o
        if seg_o == seg_d:
            span = abs(t_d - t_o) * roots[seg_o]
        else:
            span = (Fraction(1) - t_o) * roots[seg_o] + sum(roots[seg_o + 1:seg_d]) \
                + t_d * roots[seg_d]
        total += (span / sum(roots)) * _exact(p.cost)
    return total


def _rational_sqrt_exact(q: Fraction) -> Fraction | None:
    """`sqrt(q)` when it is rational, else `None`. Exact: no floats, no tolerance."""
    if q < 0:
        return None
    if q == 0:
        return Fraction(0)
    n, d = q.numerator, q.denominator
    rn, rd = math.isqrt(n), math.isqrt(d)
    return Fraction(rn, rd) if rn * rn == n and rd * rd == d else None
