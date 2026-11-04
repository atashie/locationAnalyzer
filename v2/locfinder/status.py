"""What a cell value *means*, why it can be missing, and how criteria combine.

This is Phase 1 stage S0. It deliberately contains **no encoding**: the integer values of the
enums below are in-memory array codes, chosen so 330,502 cells can be evaluated vectorised. They
are **not a wire format** and must never be written into a raster. S3.5 assigns wire codes once the
format is versioned, because legacy minute values 251-254 are real answers in artifacts already on
disk and a sentinel scheme that reinterprets them would corrupt them (Codex pass-7 H1).

## Why provenance, and not just `inf`

`layer.py` and `snap.py` between them collapse at least four distinct causes into one `inf`, and
`grid.encode_minutes` then collapses those into one `NODATA`. The product cannot say "no road near
this cell" versus "we did not search this far" without carrying the cause forward, and guessing
is worse than silence: a household told "unreachable" about a cell that is merely past our search
horizon has been told something false.

Causes a cell can have no time, and whether this pipeline can *produce* each (Codex pass-7 C4:
decide producibility before allocating a code):

| cause | arises at | producible |
|---|---|---|
| no graph edge within `max_access_m` | `snap.py:184` | **yes** — `access_m` is in hand |
| a path exists but is past the built horizon | `arrival.py:100`, `snap.py:186` | **yes** |
| no path exists in the built network | `arrival.py` | **only if the search was unbounded** |
| the category selected no destination | `arrival.py:29` | yes, build time, layer-wide |
| destinations exist but none snapped to a node | `g1_own_graph_layer.py:86` | yes, build time, layer-wide |
| a required source was missing or stale | S4.3, unimplemented | yes, build time, layer-wide |
| the cell's local network was dropped by component pruning | `components.py:77` | **no, not from the layer** |
| the true route left the routing bbox and was truncated | `metros.py` buffer | **no, not per cell** |

The last two get no status. Component pruning is knowable at build time but not afterwards — the
dropped nodes are gone — so it is a build-time diagnostic (S2.4), not a published per-cell cause.
Extract truncation would need the arrival path's node sequence, which the pipeline discards; S3
owns the build-time diagnostic. Inventing codes for either would publish a fiction.

## `NO_PATH` is not always available, and it depends on the *call*

Proving no path exists requires an exhaustive search. Measured against the code:

* our own graph's two-weight search runs **unbounded** on cost (`layer.py:38-39` pass no
  `cutoff_s`; the cutoff is applied to the final per-cell total in `snap.py`), so `inf` there
  really does mean *no path in the built network*;
* Valhalla `/expansion` is bounded by its contour (`g1_valhalla_layer.py:72`,
  `g1_expansion_primitive.py:46` both request `contours: [{"time": minutes}]`) — an edge beyond it
  is simply absent from the response, which is indistinguishable from unreachable;
* MOTIS `one-to-all` is likewise capped.

So the own-graph engine *can* prove `NO_PATH` and the bounded engines cannot, and `honest_reason`
publishes the **weaker** status, `BEYOND_HORIZON` — "not reached within the built horizon" — for
them. That is the S0.1 rule in executable form.

But the engine is not the whole story, which is Codex pass-8 H1: `arrival_seconds` accepts a
`cutoff_s`, and scipy's `limit` prunes the search, so a *bounded call on our own graph* returns
`inf` for nodes that are merely distant. Reading exhaustiveness off the engine name labelled a node
210 s away as having no route at all. `node_reasons` therefore takes `search_bounded` as a required
keyword: exhaustiveness is a property of the invocation.

The horizon is also a **per-layer** field, not a constant: the own-graph layers were built to
120 minutes and the Valhalla reference layers to 60 (`g1_valhalla_layer.py:40`). Comparing them
without carrying each horizon would read one engine's missing data as the other's disagreement.

## The algebra

Per criterion a cell is PASS, FAIL or UNKNOWN; per cell the criteria combine to INCLUDED, EXCLUDED
or UNKNOWN. The precedence rule is Codex pass-7 C4 and it matters more than the codes: **one known
failure beats any number of unknowns.** A cell that is definitely 50 minutes from work does not
become a maybe because we are unsure about its walk to a grocery.

What makes the table non-trivial is that a missing value is not automatically unknown. Each
non-OK reason carries a **sound lower bound** on the time our model would have reported, and a
lower bound above the threshold is a *known* failure with no route computed at all:

* `OFF_NETWORK` — the cell is `access_m` from the nearest edge, every destination is on the
  network, so the journey covers at least `access_m` at no more than the mode's fastest speed.
* `BEYOND_HORIZON` — the time exceeds the horizon `H`. Its bound is **strict** (`t > H`), which is
  why it needs the one extra comparison below; the others are non-strict (`t >= L`).
* `NO_PATH` — no finite time at any budget, so the criterion always fails.

These bounds are bounds on **our model's** answer, not on reality. They say whether this pipeline
could possibly have returned a passing value, which is the right question for a published region.

A correction to an earlier rationale here, from Codex pass-8 L2. This module used to claim that an
access-*speed* bound would be unsound. That is wrong for the model as implemented: the cell total is
`network + access_m / access_speed` with `network >= 0`, so the charged access time is itself a
valid — and tighter — lower bound. The weaker `max_speed_mps` bound is kept **deliberately**, not
for soundness: the off-network access leg is a straight-line fiction over unmapped ground, and a
tighter bound would use that fiction to *exclude* households rather than call them unknown. S2.4's
building-weighted coverage is what should decide whether to tighten it.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

import numpy as np


class Reason(IntEnum):
    """Why a cell has, or has not, a time. **In-memory codes only** — see the module docstring."""

    OK = 0
    OFF_NETWORK = 1
    BEYOND_HORIZON = 2
    NO_PATH = 3
    NO_DESTINATIONS = 4
    NO_ROUTABLE_DESTINATIONS = 5
    SOURCE_MISSING = 6


#: Reasons that vary cell by cell.
PER_CELL_REASONS = frozenset({Reason.OK, Reason.OFF_NETWORK, Reason.BEYOND_HORIZON, Reason.NO_PATH})

#: Reasons that are uniform over an entire layer. Each one blocks publication (S4.4): a metro with
#: no groceries is a data defect, never a fact about the metro.
LAYER_REASONS = frozenset(
    {Reason.NO_DESTINATIONS, Reason.NO_ROUTABLE_DESTINATIONS, Reason.SOURCE_MISSING}
)


class Outcome(IntEnum):
    """One criterion at one cell."""

    PASS = 0
    FAIL = 1
    UNKNOWN = 2


class Verdict(IntEnum):
    """All criteria at one cell."""

    INCLUDED = 0
    EXCLUDED = 1
    UNKNOWN = 2


@dataclass(frozen=True)
class Engine:
    name: str
    proves_no_path: bool
    note: str


#: S0.5: the engine for each mode, stated once, in one place. Revision 1 of the Phase 1 plan named
#: only Valhalla and MOTIS in its architecture paragraph while other sections relied on the
#: own-graph walk path.
ENGINES = {
    "own-graph": Engine(
        "own-graph",
        proves_no_path=True,
        note="transposed-graph multi-source Dijkstra, unbounded on cost; cutoff applied per cell",
    ),
    "valhalla-expansion": Engine(
        "valhalla-expansion",
        proves_no_path=False,
        note="/expansion action=isochrone, bounded by the requested contour",
    ),
    "motis-one-to-all": Engine(
        "motis-one-to-all",
        proves_no_path=False,
        note="one-to-all arriveBy, bounded by the requested maximum travel time",
    ),
}

ENGINE_BY_MODE = {
    "walk": "own-graph",
    "bike": "valhalla-expansion",
    "drive": "valhalla-expansion",
    "transit": "motis-one-to-all",
}


def engine_for(mode: str) -> Engine:
    return ENGINES[ENGINE_BY_MODE[mode]]


def honest_reason(reason: Reason, engine: Engine) -> Reason:
    """Weaken `NO_PATH` to `BEYOND_HORIZON` for an engine that cannot prove it (S0.1)."""
    if reason == Reason.NO_PATH and not engine.proves_no_path:
        return Reason.BEYOND_HORIZON
    return reason


def node_reasons(T: np.ndarray, engine: Engine, *, search_bounded: bool) -> np.ndarray:
    """Per-node reason array from arrival times: OK where finite, else the strongest claim this
    *invocation* is entitled to make about an infinite one.

    `search_bounded` has no default on purpose (Codex pass-8 H1). Exhaustiveness belongs to the
    call, not to the engine name: `layer.py`'s single-weight branch could run a cutoff-limited
    search on our own graph, and scipy's `limit` makes a merely-distant node indistinguishable from
    an unreachable one. Reading exhaustiveness off the engine labelled a node 210 s away as having
    no route at all.
    """
    missing = Reason.BEYOND_HORIZON if search_bounded else honest_reason(Reason.NO_PATH, engine)
    return np.where(np.isfinite(T), np.int8(Reason.OK), np.int8(missing)).astype(np.int8)


# Aggregation: what a surface's value is the time *to*. S0.3: a category query and an anchor query
# are different questions, and substituting one for the other silently answers the wrong one, so
# `evaluate` refuses the mismatch rather than trusting the caller.
#
# The two category aggregations are NOT interchangeable, and the difference is a real finding
# (Codex pass-8 H2, reproduced): `arrival_seconds_two_weight` picks the destination that is nearest
# by **cost** and then reports that path's time. With a 20 s destination behind a penalised private
# edge and a 100 s destination on an open road, the surface reads **100 s** — so it is not
# `min_d t(cell -> d)`, it is an **upper bound** on it. Category criteria evaluated on it can
# therefore produce false *exclusions*, never false inclusions.
#
# The two bracket the honest answer, and both are one Dijkstra:
#     time_min  <=  the best time over a legal route  <=  cost_selected
CATEGORY_COST_SELECTED = "cost_selected_category"   # the shipped layer; an upper bound
CATEGORY_TIME_MIN = "time_min_category"             # min over destinations, access cost ignored
SINGLE_ANCHOR = "single_anchor"
CATEGORY_AGGREGATIONS = frozenset({CATEGORY_COST_SELECTED, CATEGORY_TIME_MIN})
REQUIRED_AGGREGATION = {"category": CATEGORY_AGGREGATIONS,
                        "anchor": frozenset({SINGLE_ANCHOR})}


@dataclass(frozen=True)
class Surface:
    """One arrival-time surface over a grid, with provenance for every missing value.

    `seconds` is `+inf` wherever `reason != OK` — evaluation uses the float seconds, never the
    uint8 encoding, so rounding cannot move a threshold (Codex pass-3 H6).

    `min_possible_s` is a sound lower bound on the time our model would have reported. It is `0`
    where nothing is known, `+inf` where no path exists, and is what turns some missing values into
    *known* failures.
    """

    mode: str
    engine: str
    target: str
    aggregation: str
    horizon_s: float
    seconds: np.ndarray
    reason: np.ndarray
    min_possible_s: np.ndarray

    @property
    def shape(self) -> tuple[int, ...]:
        return self.seconds.shape

    @classmethod
    def layer_failure(
        cls,
        *,
        mode: str,
        engine: str,
        target: str,
        aggregation: str,
        horizon_s: float,
        shape: tuple[int, ...],
        reason: Reason,
    ) -> "Surface":
        """A layer that could not be built at all. Every cell is unknown — never excluded."""
        if reason not in LAYER_REASONS:
            raise ValueError(f"{reason!r} is a per-cell reason, not a layer-wide one")
        return cls(
            mode=mode,
            engine=engine,
            target=target,
            aggregation=aggregation,
            horizon_s=horizon_s,
            seconds=np.full(shape, np.inf),
            reason=np.full(shape, np.int8(reason), dtype=np.int8),
            min_possible_s=np.zeros(shape),
        )

    def validate(self) -> "Surface":
        """Check the invariants a producer must satisfy. Cheap enough to call on every build."""
        if self.engine not in ENGINES:
            raise ValueError(f"unknown engine {self.engine!r}")
        if self.aggregation not in CATEGORY_AGGREGATIONS | {SINGLE_ANCHOR}:
            raise ValueError(f"unknown aggregation {self.aggregation!r}")
        if not (self.reason.shape == self.min_possible_s.shape == self.seconds.shape):
            raise ValueError("seconds, reason and min_possible_s must share a shape")
        if np.isnan(self.seconds).any() or np.isnan(self.min_possible_s).any():
            raise ValueError("NaN in a surface; missing values are +inf, never NaN")

        r = self.reason
        valid = np.isin(r, [int(x) for x in Reason])
        if not valid.all():
            raise ValueError(f"{int((~valid).sum())} cell(s) carry a reason outside the enum")

        finite = np.isfinite(self.seconds)
        if not np.array_equal(finite, r == Reason.OK):
            raise ValueError("a finite time must be OK and an OK cell must have a finite time")
        if finite.any() and float(self.seconds[finite].max()) > self.horizon_s:
            raise ValueError("an OK cell exceeds the horizon; the cutoff was not applied")

        layer_hit = np.isin(r, [int(x) for x in LAYER_REASONS])
        if layer_hit.any():
            # Codex pass-8 M1: checking only that every cell is *some* layer-wide reason let a
            # mixed array through, and let one carry a positive lower bound -- which `evaluate`
            # would then turn into an exclusion, breaking the one guarantee this class makes.
            if not layer_hit.all():
                raise ValueError(
                    "a layer-wide reason must cover every cell; use Surface.layer_failure")
            if len(np.unique(r)) != 1:
                raise ValueError(
                    "a layer-wide failure must be one reason, uniform over every cell")
            if np.any(self.min_possible_s != 0.0):
                raise ValueError(
                    "a layer-wide failure knows nothing, so its lower bound must be exactly 0")

        if (self.min_possible_s < 0).any():
            raise ValueError("min_possible_s must be non-negative")
        if (self.min_possible_s[finite] > self.seconds[finite]).any():
            raise ValueError("min_possible_s exceeds the reported time at an OK cell")

        bh = r == Reason.BEYOND_HORIZON
        # Exact, not `allclose`: at H = 7200 s the default tolerance admits ~0.07 s of error, and
        # an eligibility comparison cannot be approximate (Codex pass-8 M2). `evaluate` reads
        # `horizon_s` rather than this array anyway, so the two cannot drift apart.
        if bh.any() and np.any(self.min_possible_s[bh] != self.horizon_s):
            raise ValueError("BEYOND_HORIZON cells must carry the horizon exactly as their bound")
        npath = r == Reason.NO_PATH
        if npath.any():
            if not ENGINES[self.engine].proves_no_path:
                raise ValueError(
                    f"engine {self.engine!r} cannot prove NO_PATH; publish BEYOND_HORIZON instead "
                    "(see honest_reason)"
                )
            if not np.isinf(self.min_possible_s[npath]).all():
                raise ValueError("NO_PATH cells must carry +inf as their lower bound")
        return self


@dataclass(frozen=True)
class Criterion:
    """One constraint a household stated.

    `kind` is `"category"` ("any qualifying grocery") or `"anchor"` ("this specific office"). Two
    workplaces are **two anchor criteria combined with AND** — never one surface holding
    `min(t_A, t_B)`, which asks whether *either* workplace is close enough (S0.3).
    """

    label: str
    mode: str
    target: str
    kind: str
    threshold_s: float

    def __post_init__(self) -> None:
        if self.kind not in REQUIRED_AGGREGATION:
            raise ValueError(f"kind must be 'category' or 'anchor', not {self.kind!r}")
        if not (self.threshold_s > 0) or not np.isfinite(self.threshold_s):
            raise ValueError("threshold_s must be positive and finite")


def _check_match(crit: Criterion, surf: Surface) -> None:
    if crit.mode != surf.mode:
        raise ValueError(f"criterion mode {crit.mode!r} against a {surf.mode!r} surface")
    if crit.target != surf.target:
        raise ValueError(f"criterion target {crit.target!r} against a {surf.target!r} surface")
    want = REQUIRED_AGGREGATION[crit.kind]
    if surf.aggregation not in want:
        raise ValueError(
            f"a {crit.kind!r} criterion needs one of {sorted(want)}, got {surf.aggregation!r}: "
            "a category surface answers 'any of these', an anchor surface answers 'this one'"
        )


def evaluate(crit: Criterion, surf: Surface) -> np.ndarray:
    """PASS / FAIL / UNKNOWN per cell for one criterion."""
    _check_match(crit, surf)
    t = crit.threshold_s
    r = surf.reason
    ok = r == Reason.OK
    # A lower bound above the threshold is a known failure with no route computed. The bounds are
    # non-strict (`time >= L`) except BEYOND_HORIZON's, which is strict (`time > H`) and therefore
    # also fails when the threshold sits exactly on the horizon. BEYOND_HORIZON compares against
    # `horizon_s` directly rather than the stored bound, so a malformed bound cannot change an
    # eligibility answer (Codex pass-8 M2).
    # Each reason is decided by exactly one rule, so an overstated stored bound cannot change an
    # eligibility answer for a reason whose bound is the horizon.
    bh = r == Reason.BEYOND_HORIZON
    proven_over = (surf.min_possible_s > t) & ~bh
    proven_over |= bh & (surf.horizon_s >= t)
    # NO_PATH fails unconditionally. The bound comparison alone would not: `inf > inf` is false,
    # so an infinite threshold made it unknown (Codex pass-8 L1). `Criterion` now rejects such a
    # threshold, and this makes the rule independent of that check.
    proven_over |= r == Reason.NO_PATH
    # A layer-wide failure knows nothing, so it is unknown whatever any array says (pass-8 M1).
    layer_hit = np.isin(r, [int(x) for x in LAYER_REASONS])
    out = np.where(
        ok,
        np.where(surf.seconds <= t, np.int8(Outcome.PASS), np.int8(Outcome.FAIL)),
        np.where(proven_over & ~layer_hit, np.int8(Outcome.FAIL), np.int8(Outcome.UNKNOWN)),
    )
    return out.astype(np.int8)


def needs_recomputation(crit: Criterion, surf: Surface) -> np.ndarray:
    """Cells whose outcome is unknown *only* because the threshold is past the built horizon.

    These are answerable — by searching further — unlike an off-network cell, so the product must
    offer a fresh computation rather than reporting "unknown" (S0.2). Raising a threshold above the
    horizon does not invalidate the cells that already passed; only this fringe.
    """
    _check_match(crit, surf)
    return (surf.reason == Reason.BEYOND_HORIZON) & (surf.horizon_s < crit.threshold_s)


def combine(outcomes, *, shape: tuple[int, ...] | None = None) -> np.ndarray:
    """Per-cell verdict. **One known failure beats any number of unknowns** (Codex pass-7 C4).

    No criteria means everything is included: a search with no constraints excludes nothing.
    """
    stack = [np.asarray(o) for o in outcomes]
    if not stack:
        if shape is None:
            raise ValueError("combine() with no criteria needs an explicit shape")
        return np.full(shape, np.int8(Verdict.INCLUDED), dtype=np.int8)
    arr = np.stack(stack)
    any_fail = (arr == Outcome.FAIL).any(axis=0)
    any_unknown = (arr == Outcome.UNKNOWN).any(axis=0)
    out = np.where(
        any_fail,
        np.int8(Verdict.EXCLUDED),
        np.where(any_unknown, np.int8(Verdict.UNKNOWN), np.int8(Verdict.INCLUDED)),
    )
    return out.astype(np.int8)


def failing(outcomes) -> np.ndarray:
    """Boolean `(n_criteria, *shape)`: which criteria fail at each cell.

    S6.2 lists **every** failing constraint, never the first one found, so the answer to "why is
    this out?" is complete.
    """
    return np.stack([np.asarray(o) == Outcome.FAIL for o in outcomes])
