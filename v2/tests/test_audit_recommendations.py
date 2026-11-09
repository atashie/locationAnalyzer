"""The audit harness's refusals, and the claim that justifies its shortcut.

`scripts/audit_recommendations.py` reconstructs `Surface.min_possible_s`, which is not stored beside
the committed layers, so that the owner's loop does not pay for a 670 MB graph load. The
reconstruction is only valid for an artifact whose reason array stops at `BEYOND_HORIZON`, and the
script asserts that. An assertion that has never been seen to fire has not been shown to protect
anything — pass-19 F5 found exactly that, a guard living in a scratch directory that protected one
invocation on one afternoon — so each refusal is exercised here against a fabricated layer.

The substantive tests are the two about the `OFF_NETWORK` bound. The first version of them was
**wrong, and passed vacuously**: it generated access distances uniformly in `[0, 200]` m and
concluded that the reconstruction was outcome-identical to the real bound. But a cell is
`OFF_NETWORK` precisely *because* `snapped.access_m > max_access_m` (`traveltime/snap.py:265`), so
`[0, 200]` is the domain in which a cell is **not** `OFF_NETWORK` at all. 200 m is the floor of
those distances, not the ceiling, and the real bound has no upper limit.

What is actually true, and what these now test:

* over any surface the reconstruction is **sound and lossy** — `0` never exceeds the real bound, so
  it can report `UNKNOWN` where the pipeline proves `FAIL` but can never manufacture an exclusion;
* for the cells the audit **emits** it is exact, because every one is adjacent to an `OK` cell and
  adjacency bounds the access distance by `max_access_m + cell_m * sqrt(2)`.
"""
from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import pytest

from locfinder.grid import GridSpec
from locfinder.measure.frames import file_digest
from locfinder.status import (CATEGORY_COST_SELECTED, Criterion, Outcome, Reason, Surface,
                              evaluate)
from locfinder.traveltime.speeds import access_speed_mps, max_speed_mps

_PATH = Path(__file__).resolve().parents[1] / "scripts" / "audit_recommendations.py"
_SPEC = importlib.util.spec_from_file_location("audit_recommendations", _PATH)
audit = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(audit)

HORIZON_S = audit.CUTOFF_MIN * 60.0
THRESHOLDS_S = (600.0, 900.0)


def _grid() -> GridSpec:
    return GridSpec("EPSG:32617", 450000.0, 4000000.0, 100.0, 6, 5)


def _arrays(reason_codes: list[int], *, seconds_for_ok: float = 500.0, saturate: bool = True):
    """A seconds/reason pair that is internally consistent: finite exactly where the reason is OK.

    `saturate` puts one OK cell a millisecond under the horizon, which is what the committed layer
    looks like (its largest finite time is 0.001 s below 7200). `corroborate_horizon` no longer
    *requires* that of anything — it only warns when the gap is large — so `saturate=False` builds
    the layer that trips the warning rather than a refusal.
    """
    reason = np.array(reason_codes, dtype=np.int8).reshape(5, 6)
    seconds = np.where(reason == Reason.OK, seconds_for_ok, np.inf)
    if saturate and (reason == Reason.OK).any():
        first = np.argwhere(reason == Reason.OK)[0]
        seconds[first[0], first[1]] = HORIZON_S - 0.001
    return seconds.astype(np.float32), reason


def _write(tmp_path: Path, seconds, reason, bound=None) -> Path:
    layers = tmp_path / "layers"
    layers.mkdir(exist_ok=True)
    np.save(layers / "own_triangle_grocery_walk.npy", seconds)
    np.save(layers / "own_triangle_grocery_walk_reason.npy", reason)
    if bound is not None:
        np.save(layers / "own_triangle_grocery_walk_min_possible_s.npy", bound)
    return layers


def _load(layers: Path, thresholds_s=THRESHOLDS_S):
    return audit.load_surface(_grid(), category="grocery", mode="walk", metro="triangle",
                              thresholds_s=thresholds_s, layers=layers)


def test_it_reconstructs_the_bound_for_a_layer_that_stops_at_beyond_horizon(tmp_path):
    codes = [0] * 10 + [1] * 10 + [2] * 10
    seconds, reason = _arrays(codes)
    surf, prov = _load(_write(tmp_path, seconds, reason))

    assert prov["min_possible_s"]["origin"] == "reconstructed"
    ok, off, bh = reason == 0, reason == 1, reason == 2
    assert np.array_equal(surf.min_possible_s[ok], surf.seconds[ok])
    assert (surf.min_possible_s[off] == 0.0).all()
    # Exactly the horizon, not merely close to it: `Surface.validate` requires equality, because an
    # eligibility comparison at the horizon cannot be approximate.
    assert (surf.min_possible_s[bh] == HORIZON_S).all()


def test_it_refuses_to_reconstruct_a_bound_when_a_cell_proves_no_path(tmp_path):
    """The refusal fires. It is a fail-fast rather than a correctness barrier — see
    `test_the_no_path_refusal_is_a_fail_fast_not_a_correctness_barrier` for why the claim this
    docstring used to make, that the cell would otherwise read as UNKNOWN, is false."""
    codes = [0] * 10 + [1] * 9 + [3] + [2] * 10      # one NO_PATH
    seconds, reason = _arrays(codes)
    layers = _write(tmp_path, seconds, reason)

    with pytest.raises(audit.Refused, match="NO_PATH"):
        _load(layers)

    # And the test is not vacuous: without that cell the same layer loads.
    codes[19] = 1
    _load(_write(tmp_path, *_arrays(codes)))


def test_it_refuses_when_even_the_adjacency_bound_exceeds_the_threshold(tmp_path):
    """Below 244 s, adjacency stops making the reconstruction exact and the script refuses rather
    than printing UNKNOWN where the pipeline proves FAIL."""
    layers = _write(tmp_path, *_arrays([0] * 10 + [1] * 10 + [2] * 10))
    adjacency_bound = (audit.MAX_ACCESS_M + 100.0 * math.sqrt(2.0)) / max_speed_mps("walk")
    assert 200.0 < adjacency_bound < 600.0, "the arithmetic this test depends on has moved"

    with pytest.raises(audit.Refused, match="not exact even for cells adjacent"):
        _load(layers, thresholds_s=(200.0,))
    _load(layers, thresholds_s=(600.0,))      # and it is accepted above the bound


def _outcomes(seconds, reason, bound, t_s):
    surf = Surface(mode="walk", engine="own-graph", target="grocery",
                   aggregation=CATEGORY_COST_SELECTED, horizon_s=HORIZON_S,
                   seconds=np.asarray(seconds, dtype=np.float64), reason=reason,
                   min_possible_s=np.asarray(bound, dtype=np.float64)).validate()
    crit = Criterion(label="x", mode="walk", target="grocery", kind="category", threshold_s=t_s)
    return evaluate(crit, surf)


def _bounds(seconds, reason, access_m):
    """The real reconstruction pair for a given set of off-network access distances."""
    off = reason == Reason.OFF_NETWORK
    real = np.where(off, access_m / max_speed_mps("walk"), 0.0)
    real = np.where(reason == Reason.OK, seconds, real)
    real = np.where(reason == Reason.BEYOND_HORIZON, HORIZON_S, real)
    weak = np.where(reason == Reason.OK, seconds, 0.0)
    weak = np.where(reason == Reason.BEYOND_HORIZON, HORIZON_S, weak)
    return real, weak


def test_the_reconstructed_off_network_bound_is_sound_but_lossy():
    """Over a surface, `0` can only lose a FAIL - it can never produce an exclusion.

    The access distances here come from the domain a cell is actually `OFF_NETWORK` in: *above*
    `max_access_m`, with no upper limit. Codex pass 26 measured real bounds of 143.6 s, 714.3 s and
    1,428.6 s for origins 201 m, 1 km and 2 km off-network, so at a 600 s threshold the real surface
    says UNKNOWN, FAIL, FAIL where the reconstruction says UNKNOWN three times.
    """
    codes = [0] * 10 + [1] * 10 + [2] * 10
    seconds, reason = _arrays(codes)
    off = reason == Reason.OFF_NETWORK
    # 201 m, 1 km, 2 km and beyond - all genuinely off-network, none of them bounded by 200 m.
    far = np.linspace(201.0, 3000.0, int(off.sum()))
    access_m = np.zeros(reason.shape)
    access_m[off] = far

    real, weak = _bounds(seconds, reason, access_m)
    assert (weak <= real).all(), "the reconstruction must never exceed the real bound"

    for t_s in THRESHOLDS_S:
        r, w = _outcomes(seconds, reason, real, t_s), _outcomes(seconds, reason, weak, t_s)
        # Sound: nothing the reconstruction calls FAIL is anything else in truth.
        assert not ((w == Outcome.FAIL) & (r != Outcome.FAIL)).any(), \
            "the reconstruction manufactured an exclusion"
        # Lossy, and demonstrably so on this surface rather than merely in principle.
        lost = (r == Outcome.FAIL) & (w == Outcome.UNKNOWN)
        assert lost.any(), f"no FAIL was lost at {t_s}s; the test no longer exercises the defect"
        assert (w[off] == Outcome.UNKNOWN).all()


def test_the_reconstruction_is_exact_for_a_cell_adjacent_to_an_ok_cell():
    """Which is the only claim the emitted sheet needs, and the one the script checks.

    An `OFF_NETWORK` cell next to an `OK` cell inherits a bound: the neighbour's own access is at
    most `max_access_m`, and the two centres are at most one cell diagonal apart, so this cell's
    access is at most `max_access_m + cell_m * sqrt(2)` = 341.4 m, a real bound of 243.9 s.
    """
    cell_m = 100.0
    limit_m = audit.MAX_ACCESS_M + cell_m * math.sqrt(2.0)
    assert limit_m == pytest.approx(341.42, abs=0.01)
    assert limit_m / max_speed_mps("walk") == pytest.approx(243.9, abs=0.1)
    assert limit_m / max_speed_mps("walk") < min(THRESHOLDS_S)

    codes = [0] * 10 + [1] * 10 + [2] * 10
    seconds, reason = _arrays(codes)
    off = reason == Reason.OFF_NETWORK
    access_m = np.zeros(reason.shape)
    # Every admissible distance for an adjacent cell: just off-network, up to the adjacency bound.
    access_m[off] = np.linspace(audit.MAX_ACCESS_M + 0.01, limit_m, int(off.sum()))

    real, weak = _bounds(seconds, reason, access_m)
    for t_s in THRESHOLDS_S:
        assert np.array_equal(_outcomes(seconds, reason, real, t_s),
                              _outcomes(seconds, reason, weak, t_s)), \
            f"adjacency does not make the reconstruction exact at {t_s}s"


def test_it_prefers_a_stored_bound_to_the_reconstruction(tmp_path):
    """With the real bound on disk neither assertion is needed, so a NO_PATH layer loads — and its
    NO_PATH cells are the known failures they should be."""
    codes = [0] * 10 + [1] * 9 + [3] + [2] * 10
    seconds, reason = _arrays(codes)
    bound = np.where(reason == Reason.OK, seconds, 0.0).astype(np.float64)
    bound = np.where(reason == Reason.BEYOND_HORIZON, HORIZON_S, bound)
    bound = np.where(reason == Reason.NO_PATH, np.inf, bound)

    surf, prov = _load(_write(tmp_path, seconds, reason, bound))
    assert prov["min_possible_s"]["origin"] == "stored"
    assert "sha256" in prov["min_possible_s"]
    crit = Criterion(label="x", mode="walk", target="grocery", kind="category", threshold_s=600.0)
    assert (evaluate(crit, surf)[reason == Reason.NO_PATH] == Outcome.FAIL).all()


def test_it_refuses_a_seconds_and_reason_pair_that_violate_an_invariant(tmp_path):
    """`Surface.validate` requires a finite time exactly where the reason is OK, which catches the
    common mismatch. It establishes **invariants, not shared provenance** — two builds with the same
    OK mask and different times both pass — so the message says that rather than claiming the files
    were proven to come from one build."""
    seconds, reason = _arrays([0] * 10 + [1] * 10 + [2] * 10)
    reason = reason.copy()
    reason[1, 0] = Reason.OFF_NETWORK          # a finite time now carries a non-OK reason
    with pytest.raises(audit.Refused, match="violate a Surface invariant"):
        _load(_write(tmp_path, seconds, reason))

    # And the limit of it: swapping two infinite cells' reasons passes validation untouched, so
    # nothing here should be read as a provenance check.
    seconds, reason = _arrays([0] * 10 + [1] * 10 + [2] * 10)
    swapped = reason.copy()
    swapped[reason == Reason.OFF_NETWORK] = Reason.BEYOND_HORIZON
    _load(_write(tmp_path, seconds, swapped))


def test_it_refuses_a_layer_whose_shape_is_not_the_grid(tmp_path):
    seconds, reason = _arrays([0] * 30)
    with pytest.raises(audit.Refused, match="grid is"):
        audit.load_surface(GridSpec("EPSG:32617", 450000.0, 4000000.0, 100.0, 7, 5),
                           category="grocery", mode="walk", metro="triangle",
                           thresholds_s=THRESHOLDS_S, layers=_write(tmp_path, seconds, reason))


def test_the_near_threshold_bands_are_split_by_the_side_of_the_threshold():
    """An unsplit band drew six journeys that all sat above 15 minutes, so every row asked the same
    question. Split, one stratum holds cells the product shows as passing and the other cells it
    shows as failing."""
    t = 600.0
    secs = np.array([t - 95.0, t - 30.0, t, t + 0.5, t + 60.0, t + 95.0], dtype=np.float64)
    seconds = np.tile(secs, (5, 1))
    reason = np.zeros((5, 6), dtype=np.int8)
    surf = Surface(mode="walk", engine="own-graph", target="grocery",
                   aggregation=CATEGORY_COST_SELECTED, horizon_s=HORIZON_S, seconds=seconds,
                   reason=reason, min_possible_s=seconds.copy()).validate()
    crit = Criterion(label="x", mode="walk", target="grocery", kind="category", threshold_s=t)
    pools = audit.strata(surf, {10: evaluate(crit, surf)}, thresholds_min=(10,))

    passing, failing = pools["band10min_pass"], pools["band10min_fail"]
    assert passing.any() and failing.any()
    assert not (passing & failing).any(), "a cell landed in both halves of the band"
    assert (seconds[passing] <= t).all() and (seconds[failing] > t).all()
    # The threshold itself passes, matching `evaluate`'s non-strict comparison.
    assert passing[:, 2].all() and not failing[:, 2].any()
    # And nothing outside the +/- 90 s band is drawn in: columns 0 and 5 are 95 s off the
    # threshold and belong to neither half.
    assert not passing[:, 0].any() and not failing[:, 0].any()
    assert not passing[:, 5].any() and not failing[:, 5].any()


def test_it_reads_the_build_parameters_from_a_sidecar_instead_of_assuming_them(tmp_path):
    """A consumer asserting someone else's build parameters is the error shape this stage exists to
    catch, so the builder records them and they win when present."""
    seconds, reason = _arrays([0] * 10 + [1] * 10 + [2] * 10, seconds_for_ok=500.0, saturate=False)
    layers = _write(tmp_path, seconds, reason)
    (layers / "own_triangle_grocery_walk_build.json").write_text(
        '{"horizon_s": 3600.0, "max_access_m": 200.0}', encoding="utf-8")

    surf, prov = _load(layers)
    assert prov["build"]["origin"] == "sidecar"
    assert surf.horizon_s == 3600.0
    # and the bound follows the sidecar's horizon, not the script's constant
    assert (surf.min_possible_s[reason == Reason.BEYOND_HORIZON] == 3600.0).all()


def test_an_implausible_assumed_horizon_warns_and_does_not_refuse(tmp_path, capsys):
    """`Surface.validate` only checks `max finite <= horizon`, so assuming a horizon *larger* than
    the build's passes silently and every BEYOND_HORIZON bound is then wrong. The gap below the
    horizon is a hint about that — and **only** a hint, which is the whole history of this check:
    it refused at a flat 60 s, then at a "derived" 238 s, and pass 28 built legitimate
    `build_layer_surface` output exceeding both. It now reports and carries on."""
    seconds, reason = _arrays([0] * 10 + [1] * 10 + [2] * 10, seconds_for_ok=500.0, saturate=False)
    _, prov = _load(_write(tmp_path, seconds, reason))
    assert prov["build"]["horizon"]["plausible"] is False
    assert "may be wrong" in capsys.readouterr().out

    # Saturated, the same layer looks plausible: the hint is about the gap, not the shape.
    surf, prov = _load(_write(tmp_path, *_arrays([0] * 10 + [1] * 10 + [2] * 10)))
    assert prov["build"]["horizon"]["plausible"] is True
    assert prov["build"]["horizon"]["gap_to_horizon_s"] == pytest.approx(0.001, abs=1e-3)
    # And it is labelled for what it is, so no reader mistakes it for provenance.
    assert prov["build"]["horizon"]["is_a_heuristic"] is True


def test_a_layer_with_nothing_cut_off_needs_no_corroboration(tmp_path):
    """Nothing can be inferred about a horizon that never bound, and nothing needs to be: with no
    BEYOND_HORIZON cell the bound is never read from it."""
    seconds, reason = _arrays([0] * 20 + [1] * 10, seconds_for_ok=500.0, saturate=False)
    _, prov = _load(_write(tmp_path, seconds, reason))
    assert prov["build"]["horizon"]["cells_cut_off"] == 0
    assert prov["build"]["horizon"]["plausible"] is True


def test_no_horizon_gap_is_ever_a_refusal(tmp_path, capsys):
    """Two legitimate `build_layer_surface` outputs that successive versions of this check rejected.

    Pass 27: a straight 11 km edge with cells at 9,990 m and 10,090 m returns `[7135.714, inf]`
    against a **true** 7,200 s horizon — a 64.3 s gap, which the original flat 60 s threshold called
    an inconsistent build.

    Pass 28: two parallel 100 m roads 100 m apart, joined by a 12.1 km detour outside the grid,
    returns `[35.714, inf]` against the same true horizon — a **7,164 s** gap, which the "derived"
    238 s scale also rejected. Neighbouring cells can snap to roads separated by an arbitrarily long
    network journey, so there is no bound here to derive and the formula only ever supplied a
    dimensional scale.

    Both load. Only a sidecar or `--horizon-min` can settle a horizon.
    """
    for frontier_s, note in ((7135.714285714286, "pass 27's 64.3 s gap"),
                             (35.714285714285715, "pass 28's 7,164 s gap")):
        seconds, reason = _arrays([0] * 10 + [1] * 10 + [2] * 10, saturate=False)
        seconds = seconds.copy()
        seconds[:, :] = np.where(reason == Reason.OK, frontier_s, np.inf)
        surf, prov = _load(_write(tmp_path, seconds.astype(np.float32), reason))
        assert surf.horizon_s == HORIZON_S, note
        gap = prov["build"]["horizon"]["gap_to_horizon_s"]
        assert gap == pytest.approx(HORIZON_S - frontier_s, abs=0.01), note
    # The second one is past the scale and still loads, with a warning rather than a refusal.
    assert prov["build"]["horizon"]["plausible"] is False
    assert gap > prov["build"]["horizon"]["gap_scale_s"]
    assert "may be wrong" in capsys.readouterr().out

    # The scale is still derived rather than chosen, which is worth pinning even though it now
    # decides only whether to print.
    assert prov["build"]["horizon"]["gap_scale_s"] == pytest.approx(
        (audit.MAX_ACCESS_M + 100.0) / access_speed_mps("walk"), abs=0.1)


def test_a_declared_horizon_is_recorded_as_a_declaration(tmp_path):
    """`--horizon-min` is what settles a horizon in the absence of a sidecar, and the provenance
    says it was a declaration rather than evidence."""
    seconds, reason = _arrays([0] * 10 + [1] * 10 + [2] * 10, seconds_for_ok=500.0, saturate=False)
    layers = _write(tmp_path, seconds, reason)
    surf, prov = audit.load_surface(_grid(), category="grocery", mode="walk", metro="triangle",
                                    thresholds_s=THRESHOLDS_S, layers=layers,
                                    declared_horizon_s=HORIZON_S)
    assert prov["build"]["origin"] == "declared by the operator"
    assert surf.horizon_s == HORIZON_S
    assert "horizon" not in prov["build"], "no heuristic should run when the horizon is declared"


def test_a_declaration_that_contradicts_the_sidecar_is_refused(tmp_path):
    """The sidecar is evidence and the flag is an assertion, so the sidecar wins — but silently
    ignoring the flag, which is what it did, let `--horizon-min` look authoritative while doing
    nothing (pass 28)."""
    layers = _write(tmp_path, *_arrays([0] * 10 + [1] * 10 + [2] * 10))
    (layers / "own_triangle_grocery_walk_build.json").write_text(
        '{"horizon_s": 7200.0, "max_access_m": 200.0}', encoding="utf-8")
    with pytest.raises(audit.Refused, match="the build sidecar records"):
        audit.load_surface(_grid(), category="grocery", mode="walk", metro="triangle",
                           thresholds_s=THRESHOLDS_S, layers=layers,
                           declared_horizon_s=3600.0)
    # Agreeing is fine.
    audit.load_surface(_grid(), category="grocery", mode="walk", metro="triangle",
                       thresholds_s=THRESHOLDS_S, layers=layers, declared_horizon_s=7200.0)


def test_a_sidecar_digest_that_does_not_match_is_refused(tmp_path):
    """The sidecar binds the arrays into one build only to the extent it records their digests."""
    layers = _write(tmp_path, *_arrays([0] * 10 + [1] * 10 + [2] * 10))
    (layers / "own_triangle_grocery_walk_build.json").write_text(
        '{"horizon_s": 7200.0, "max_access_m": 200.0, "arrays": {"seconds": "%s"}}' % ("0" * 64),
        encoding="utf-8")
    with pytest.raises(audit.Refused, match="does not match the digest"):
        _load(layers)

    # With no digests recorded it loads, and says what the sidecar did and did not establish.
    (layers / "own_triangle_grocery_walk_build.json").write_text(
        '{"horizon_s": 7200.0, "max_access_m": 200.0}', encoding="utf-8")
    _, prov = _load(layers)
    assert "not provenance" in prov["build"]["arrays"]["seconds"]


def test_it_refuses_a_build_whose_access_distance_breaks_the_adjacency_bound(tmp_path):
    """A build with a 1 km access rule puts even an adjacent cell past 600 s, so the exactness the
    emitted rows rely on is gone and the sidecar is what reveals it."""
    layers = _write(tmp_path, *_arrays([0] * 10 + [1] * 10 + [2] * 10))
    (layers / "own_triangle_grocery_walk_build.json").write_text(
        '{"horizon_s": 7200.0, "max_access_m": 1000.0}', encoding="utf-8")
    with pytest.raises(audit.Refused, match="not exact even for cells adjacent"):
        _load(layers)

    (layers / "own_triangle_grocery_walk_build.json").write_text(
        '{"horizon_s": 7200.0, "max_access_m": 600.0}', encoding="utf-8")
    _load(layers)          # 600 + 141 m is 530 s, still inside 600 s


def test_the_no_path_refusal_is_a_fail_fast_not_a_correctness_barrier():
    """The claim this script used to make - that without the refusal a NO_PATH cell would silently
    read as UNKNOWN - is false twice over, and the correction is worth pinning.

    `Surface.validate` rejects a NO_PATH cell whose bound is not `+inf` (`status.py:325`), and
    `evaluate` fails NO_PATH unconditionally whatever its bound (`status.py:380`). So the refusal
    buys a legible message at the point of cause, not correctness.
    """
    seconds, reason = _arrays([0] * 10 + [1] * 9 + [3] + [2] * 10)
    wrong_bound = np.where(reason == Reason.OK, seconds, 0.0).astype(np.float64)
    wrong_bound = np.where(reason == Reason.BEYOND_HORIZON, HORIZON_S, wrong_bound)
    surf = Surface(mode="walk", engine="own-graph", target="grocery",
                   aggregation=CATEGORY_COST_SELECTED, horizon_s=HORIZON_S,
                   seconds=seconds.astype(np.float64), reason=reason, min_possible_s=wrong_bound)

    # 1. validate refuses it outright.
    with pytest.raises(ValueError, match="NO_PATH cells must carry"):
        surf.validate()

    # 2. and even unvalidated, evaluate still fails the cell: the bound is not consulted for
    #    NO_PATH, so the "silent UNKNOWN" could not have happened.
    crit = Criterion(label="x", mode="walk", target="grocery", kind="category", threshold_s=600.0)
    assert (evaluate(crit, surf)[reason == Reason.NO_PATH] == Outcome.FAIL).all()


def test_the_off_network_stratum_sits_beside_a_pass_not_beside_any_answer():
    """It dilated `reason == OK` until Codex pass 26: 24,468 cells qualified and the three drawn
    had nearest answering neighbours an hour from a grocery. "Unknown beside a pass" has to dilate
    the PASS mask."""
    # Row 1 is OFF_NETWORK throughout. Row 0 passes on the left and fails far to the right.
    seconds = np.array([
        [300.0, 300.0, np.inf, 4000.0, 4000.0, 4000.0],
        [np.inf] * 6,
        [300.0, 300.0, np.inf, 4000.0, 4000.0, 4000.0],
        [np.inf] * 6,
        [np.inf] * 6,
    ])
    reason = np.where(np.isfinite(seconds), np.int8(Reason.OK),
                      np.int8(Reason.OFF_NETWORK)).astype(np.int8)
    bound = np.where(reason == Reason.OK, seconds, 0.0)
    surf = Surface(mode="walk", engine="own-graph", target="grocery",
                   aggregation=CATEGORY_COST_SELECTED, horizon_s=HORIZON_S, seconds=seconds,
                   reason=reason, min_possible_s=bound).validate()
    crit = Criterion(label="x", mode="walk", target="grocery", kind="category", threshold_s=900.0)
    pools = audit.strata(surf, {15: evaluate(crit, surf)}, thresholds_min=(15,))

    beside = pools["off_network_beside_pass15min"]
    assert beside.any()
    # Column 0-1 off-network cells are beside a 300 s pass; columns 4-5 are beside 4,000 s fails.
    assert beside[1, 0] and beside[1, 1]
    assert not beside[1, 5], "an off-network cell beside a FAIL was selected as beside a pass"
    assert not beside[4, 5], "a cell with no answering neighbour at all was selected"
    # And it is strictly inside what dilating OK would have given.
    from scipy import ndimage
    beside_any = ((reason == Reason.OFF_NETWORK)
                  & ndimage.binary_dilation(reason == Reason.OK, structure=np.ones((3, 3), bool)))
    assert beside_any.sum() > beside.sum(), "dilating PASS should be strictly tighter than OK"
    assert (beside & ~beside_any).sum() == 0


def test_the_deep_controls_keep_a_margin_and_stay_inside_the_walk_cap():
    """A control is defined by its margin past the threshold, not by an absolute time. The first
    version asked for >= 1,800 s and drew walks of 108, 50 and 56 minutes."""
    t = 900.0
    # `binary_erosion` keeps only cells whose whole 3x3 neighbourhood agrees, so each control needs
    # a region three rows deep before any cell of it can qualify at all.
    secs = np.full((7, 6), t + audit.CONTROL_MARGIN_S + 60.0)   # 1,260 s: fails with margin
    secs[0:3, :] = 100.0                                        # passes with margin
    secs[5, 3] = t + 10.0                                       # fails, but with no margin
    reason = np.zeros((7, 6), dtype=np.int8)
    surf = Surface(mode="walk", engine="own-graph", target="grocery",
                   aggregation=CATEGORY_COST_SELECTED, horizon_s=HORIZON_S, seconds=secs,
                   reason=reason, min_possible_s=secs.copy()).validate()
    crit = Criterion(label="x", mode="walk", target="grocery", kind="category", threshold_s=t)
    pools = audit.strata(surf, {15: evaluate(crit, surf)}, thresholds_min=(15,))

    fail_ctl = pools["deep_fail_control"]
    assert fail_ctl.any()
    assert (secs[fail_ctl] >= t + audit.CONTROL_MARGIN_S).all()
    assert not fail_ctl[5, 3], "a cell 10 s past the threshold is not a control"
    assert fail_ctl[5, 1], "the interior of the failing region should qualify"
    # The deep PASS control needs the margin on the other side.
    pass_ctl = pools["deep_pass_control"]
    assert pass_ctl.any() and (secs[pass_ctl] <= t - audit.CONTROL_MARGIN_S).all()
    assert pass_ctl[1, 1] and not pass_ctl[3, 1]
    assert audit.STRATUM_DRAW_CAP["deep_fail_control"] == 1, \
        "the longest stratum on the sheet should not be drawn three times"


def test_a_recorded_digest_whose_file_is_missing_is_refused(tmp_path):
    """Pass 29 deleted a certified bound file and watched the loader silently reconstruct it.

    The existence check sat *before* the digest lookup, so a sidecar that recorded a
    `min_possible_s` digest for a file since deleted was skipped, `build["arrays"]` said nothing
    about it, and an OFF_NETWORK cell's real 1,000 s bound became 0 — turning FAIL into UNKNOWN at
    ten minutes. Substituting a weaker input for one the build says exists is the downgrade this
    stage exists to refuse.
    """
    seconds, reason = _arrays([0] * 10 + [1] * 10 + [2] * 10)
    bound = np.where(reason == Reason.OK, seconds, 0.0).astype(np.float64)
    bound = np.where(reason == Reason.BEYOND_HORIZON, HORIZON_S, bound)
    layers = _write(tmp_path, seconds, reason, bound)
    digests = {n: file_digest(layers / f"own_triangle_grocery_walk{suffix}.npy")
               for n, suffix in (("seconds", ""), ("reason", "_reason"),
                                 ("min_possible_s", "_min_possible_s"))}
    (layers / "own_triangle_grocery_walk_build.json").write_text(
        json.dumps({"horizon_s": HORIZON_S, "max_access_m": 200.0, "arrays": digests}),
        encoding="utf-8")

    # All three present: loads, and says the bound came from disk rather than a reconstruction.
    _, prov = _load(layers)
    assert prov["min_possible_s"]["origin"] == "stored"
    assert prov["build"]["arrays"]["min_possible_s"] == "digest matched"

    # Delete the certified bound and it refuses instead of quietly reconstructing.
    (layers / "own_triangle_grocery_walk_min_possible_s.npy").unlink()
    with pytest.raises(audit.Refused, match="records a digest for .* but the file is missing"):
        _load(layers)

    # A legacy sidecar that records no bound digest still reconstructs, which is the case the
    # refusal must not catch.
    (layers / "own_triangle_grocery_walk_build.json").write_text(
        json.dumps({"horizon_s": HORIZON_S, "max_access_m": 200.0,
                    "arrays": {k: v for k, v in digests.items() if k != "min_possible_s"}}),
        encoding="utf-8")
    _, prov = _load(layers)
    assert prov["min_possible_s"]["origin"] == "reconstructed"
