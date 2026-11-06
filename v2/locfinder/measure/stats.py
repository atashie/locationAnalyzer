"""Exact interval primitives, the acceptance rule, and the frozen bootstrap convention.

Design §§6 and 8. Everything here is a pure function of counts and arrays, which is the point: the
S3 acceptance verdict must be reproducible from the persisted rows alone (§12), so no function in
this module reads a raster, a graph or a network.

Three decisions are frozen here rather than left to a caller, each because leaving it open admitted
a wrong answer in review:

* **Bounds are one-sided and exact**, on the *actual* sample size. No effective-sample-size
  adjustment exists, because dividing `n` by an estimated design effect destroys Clopper-Pearson's
  coverage guarantee — it is an inversion of the binomial model, not a generic variance correction
  (pass-15 H1). After any such adjustment a bound may not be called exact, which is why revision 2's
  "exact bound on n/DEFF" was a contradiction.
* **Both directions are provided.** Revision 2 shipped only the upper bound, and design §4's
  screening needs the lower one (pass-16 F12). A one-sided lower bound is easy to get wrong in a way
  no obvious test catches: a mistakenly *two-sided* lower bound still returns 0 at k=0 and still
  moves correctly with the confidence level (pass-18 F9).
* **The bootstrap's whole convention is fixed** — statistic, quantile method, generator and
  resampling — because "the 2.5th percentile" does not identify a number. On 2,000 replicates of 50
  zeros and 1,950 ones it is 0.975 by linear interpolation, 0 by the lower convention and 1 by higher
  or nearest (pass-18 F10). A recorded seed alone does not identify a sequence either.

What is deliberately *absent*: any assertion that an interval widens as a sample shrinks. That is
false — `[-1, 0, 1]` gives `[-1, 1]` while the smaller `[0, 0]` gives `[0, 0]` — and revision 2
required it as a test, which is an assertion no correct implementation can satisfy (pass-18 F10).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np
from scipy.stats import beta

#: Design §6: linear interpolation, i.e. `numpy.quantile`'s default. Frozen because the conventions
#: disagree materially on the same replicate vector.
QUANTILE_METHOD = "linear"

#: Design §6: a `numpy.random.Generator` on PCG64. Frozen because a seed without its generator does
#: not identify a sequence.
BIT_GENERATOR = np.random.PCG64

#: Design §6.
BOOTSTRAP_REPLICATES = 2000


# ----------------------------------------------------------------------------- exact bounds


def clopper_pearson_upper(failures: int, n: int, *, confidence: float = 0.95) -> float:
    """One-sided exact upper bound on the failure rate.

    The Beta quantile relation `p_u = BetaInv(c, k + 1, n - k)`. At `k = n` the bound is exactly 1.0,
    where the Beta form is undefined.

    At zero failures this equals `1 - (1 - c) ** (1 / n)` in closed form, which the tests use as an
    independent check of *this* formula — not as the expected value of some other one.
    """
    _check_counts(failures, n)
    _check_confidence(confidence)
    if failures >= n:
        return 1.0
    return float(beta.ppf(confidence, failures + 1, n - failures))


def clopper_pearson_lower(failures: int, n: int, *, confidence: float = 0.95) -> float:
    """One-sided exact lower bound on the failure rate.

    `p_l = BetaInv(1 - c, k, n - k + 1)`, and exactly 0.0 at `k = 0`.

    **One-sided, not two-sided.** At `k = 1, n = 500, c = 0.95` this is 0.000102581; the two-sided
    counterpart is 0.000050634, and it passes the zero-endpoint and confidence-direction checks, so
    the tests pin a non-zero value (pass-18 F9).
    """
    _check_counts(failures, n)
    _check_confidence(confidence)
    if failures <= 0:
        return 0.0
    return float(beta.ppf(1.0 - confidence, failures, n - failures + 1))


def tolerated_failures(n: int, threshold: float, *, confidence: float = 0.95) -> int:
    """The largest observed failure count whose upper bound still satisfies `threshold`.

    Design §4 chooses the allocation by this quantity rather than by the zero-failure bound, because
    the zero-failure figure hides a cliff: at a 1.0% threshold, `n = 400` tolerates **zero** failures
    (k=1 gives 1.1804%), `n = 473` is the minimum tolerating one but at 0.9990%, and `n = 500`
    tolerates one at 0.9452%.

    Returns **-1** when not even zero failures satisfies the threshold — the unreachable-gate
    condition that revision 2 shipped undetected (pass-15 H2). A caller treating -1 as 0 would
    reintroduce it.
    """
    if n <= 0:
        raise ValueError(f"n must be positive, got {n}")
    if not 0.0 < threshold < 1.0:
        raise ValueError(f"threshold must lie in (0, 1), got {threshold}")
    if clopper_pearson_upper(0, n, confidence=confidence) > threshold:
        return -1
    lo, hi = 0, n
    while lo < hi:  # largest k with upper(k) <= threshold; upper is monotone in k
        mid = (lo + hi + 1) // 2
        if clopper_pearson_upper(mid, n, confidence=confidence) <= threshold:
            lo = mid
        else:
            hi = mid - 1
    return lo


# ----------------------------------------------------------------------------- acceptance


class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"


@dataclass(frozen=True)
class Acceptance:
    """One direction's verdict, with the two objects design §7 requires be reported separately."""

    verdict: Verdict
    identified: int                     # k
    unresolved: int                     # u, applicable to *this* direction only
    n: int
    threshold: float
    identification_range: tuple[float, float]   # [k/n, (k+u)/n]
    bound_range: tuple[float, float]            # [upper(k), upper(k+u)]


def acceptance(identified: int, unresolved: int, n: int, threshold: float,
               *, confidence: float = 0.95) -> Acceptance:
    """Design §8, verbatim:

        PASS         if CP_upper(k + u, n) <= threshold
        FAIL         if k / n > threshold
        INCONCLUSIVE otherwise

    `n` is **full-frame** — product `UNKNOWN` is a known non-event for a directional error, not a
    concealed claim, so it never leaves the denominator (pass-16 F5).

    `u` counts only unresolved observations that could be errors of *this* direction: a product PASS
    cannot generate a false exclusion, so comparator ignorance is completed in one direction only.

    Revision 4 said "the point estimate of either exceeds its threshold" without saying which
    completion supplies the point estimate, which left the verdict ambiguous (pass-18 F6): at
    `n = 500, k = 1, u = 1` the completed proportions are 0.2%-0.4%, below 1%, while the completed
    upper bounds are 0.9452%-1.2538%, crossing it. The rule above returns INCONCLUSIVE there, and
    FAIL only on identified errors alone.
    """
    _check_counts(identified, n)
    if unresolved < 0:
        raise ValueError(f"unresolved must be non-negative, got {unresolved}")
    if identified + unresolved > n:
        raise ValueError(f"k + u = {identified + unresolved} exceeds n = {n}")
    if not 0.0 < threshold < 1.0:
        raise ValueError(f"threshold must lie in (0, 1), got {threshold}")

    completed = identified + unresolved
    lo_bound = clopper_pearson_upper(identified, n, confidence=confidence)
    hi_bound = clopper_pearson_upper(completed, n, confidence=confidence)

    if hi_bound <= threshold:
        verdict = Verdict.PASS
    elif identified / n > threshold:
        verdict = Verdict.FAIL
    else:
        verdict = Verdict.INCONCLUSIVE

    return Acceptance(
        verdict=verdict,
        identified=identified,
        unresolved=unresolved,
        n=n,
        threshold=threshold,
        identification_range=(identified / n, completed / n),
        bound_range=(lo_bound, hi_bound),
    )


# ----------------------------------------------------------------------------- variance


def srs_variance(p: float, n: int, N: int) -> float:
    """Exact variance of a proportion under SRS without replacement from a finite frame.

    `p(1-p)/n * (N-n)/(N-1)`. Revision 3 printed `(1 - n/N)`, which is the approximation (pass-16
    F9). Numerically close at n=500, N=512,633 — but the wrong form implies a false limit, so the
    right one is used.
    """
    if not 0 < n <= N:
        raise ValueError(f"require 0 < n <= N, got n={n}, N={N}")
    if N < 2:
        raise ValueError("a finite-population correction needs N >= 2")
    return float(p * (1.0 - p) / n * (N - n) / (N - 1))


def two_stage_variance(q: np.ndarray, n: int, N: int) -> float:
    """Exact variance for frame C: a cell, then a uniform point inside it.

        [ (1 - n/N) * S_q^2 + mean(q_i (1 - q_i)) ] / n,    S_q^2 on N - 1

    with `q_i` the within-cell error probability. **The within-cell term receives no
    finite-population correction**, which is the part revision 3 got wrong: its expression goes to
    zero at `n = N`, whereas if every cell is half erroneous the variance is `0.25/n` even when every
    cell is sampled once (pass-16 F9).
    """
    q = np.asarray(q, dtype=np.float64)
    if q.size != N:
        raise ValueError(f"q must hold one probability per population cell: {q.size} != {N}")
    if not 0 < n <= N:
        raise ValueError(f"require 0 < n <= N, got n={n}, N={N}")
    if N < 2:
        raise ValueError("S_q^2 needs N >= 2")
    between = float(np.var(q, ddof=1))
    within = float(np.mean(q * (1.0 - q)))
    return ((1.0 - n / N) * between + within) / n


# ----------------------------------------------------------------------------- bootstrap


def percentile_interval(replicate_statistics, *, confidence: float = 0.95
                        ) -> tuple[float, float]:
    """The frozen percentile convention, separated from resampling so it can be tested alone.

    `QUANTILE_METHOD` at `(1-c)/2` and `1-(1-c)/2`. Kept as its own function because a single test
    over `percentile_bootstrap` conflates percentile arithmetic with RNG reproduction, and the two
    fail independently (pass-18 F10).
    """
    _check_confidence(confidence)
    stats = np.asarray(replicate_statistics, dtype=np.float64)
    if stats.size == 0:
        raise ValueError("no replicate statistics")
    alpha = 1.0 - confidence
    lo, hi = np.quantile(stats, [alpha / 2.0, 1.0 - alpha / 2.0], method=QUANTILE_METHOD)
    return float(lo), float(hi)


def percentile_bootstrap(values, *, seed: int, replicates: int = BOOTSTRAP_REPLICATES,
                         statistic=np.median, confidence: float = 0.95
                         ) -> tuple[float, float] | None:
    """Design §6's bootstrap: resample **points** with replacement within one frame.

    `values` holds one number per sampled point — for E2, that point's paired difference — so
    pairing is preserved by construction: a resampled point carries its own difference and nothing
    is recombined across points.

    Returns **None** when the domain has fewer than two points, which design §6 reports as "not
    estimable" rather than as an interval. Ties are admissible and may legitimately produce a
    degenerate interval; that is a property of the data, not a defect.
    """
    v = np.asarray(values, dtype=np.float64)
    if v.ndim != 1:
        raise ValueError(f"values must be one-dimensional, got shape {v.shape}")
    if not np.all(np.isfinite(v)):
        raise ValueError("values must be finite: design §3 declares E2's domain as the jointly "
                         "finite pairs, so censored pairs are excluded upstream and counted "
                         "in the status cross-tabulation, never passed in here")
    if v.size < 2:
        return None
    if replicates < 1:
        raise ValueError(f"replicates must be positive, got {replicates}")

    rng = np.random.Generator(BIT_GENERATOR(seed))
    idx = rng.integers(0, v.size, size=(replicates, v.size))
    stats = statistic(v[idx], axis=1)
    return percentile_interval(stats, confidence=confidence)


# ----------------------------------------------------------------------------- guards


def _check_counts(failures: int, n: int) -> None:
    if n <= 0:
        raise ValueError(f"n must be positive, got {n}")
    if not 0 <= failures <= n:
        raise ValueError(f"failures must lie in [0, n], got {failures} of {n}")


def _check_confidence(confidence: float) -> None:
    """A one-sided level below 0.5 does not produce a bound, so it is rejected rather than served.

    Pass-19 found the acceptance rule's three branches are not mutually exclusive on the whole of
    `(0, 1)`: `acceptance(9, 0, 10, 0.8, confidence=0.01)` returns PASS because the 1% upper bound is
    0.6310 and sits below theta, while `k/n = 0.9 > 0.8` satisfies the FAIL predicate at the same
    time. The cause is that a Clopper-Pearson upper bound only dominates the observed proportion
    once the level is at least 0.5; below that it is an upper *quantile of the wrong tail*, and
    calling it a bound is the error.

    At `confidence >= 0.5` the branches are exhaustive and disjoint for every valid `(k, u, n)`, so
    the docstring's claim of mutual exclusivity is true across the accepted domain rather than only
    at the frozen 0.95. S3 uses 0.95 throughout; this guard is what makes the helper safe to reuse.

    The same domain is applied to the **two-sided** percentile interval, where the argument above
    does not apply — a 30% central interval is perfectly well defined. It is restricted anyway
    because S3 reports no such interval and one domain is easier to reason about than two. That is a
    convenience, not a mathematical requirement, and is recorded as one.
    """
    if not 0.5 <= confidence < 1.0:
        raise ValueError(f"confidence must lie in [0.5, 1), got {confidence}: a one-sided level "
                         "below 0.5 gives a 'bound' that can fall below the point estimate")
