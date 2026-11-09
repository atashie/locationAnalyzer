"""The audit harness's refusals, and the claim that justifies its shortcut.

`scripts/audit_recommendations.py` reconstructs `Surface.min_possible_s`, which is not stored beside
the committed layers, so that the owner's loop does not pay for a 670 MB graph load. The
reconstruction is only valid for an artifact whose reason array stops at `BEYOND_HORIZON`, and the
script asserts that. An assertion that has never been seen to fire has not been shown to protect
anything — pass-19 F5 found exactly that, a guard living in a scratch directory that protected one
invocation on one afternoon — so each refusal is exercised here against a fabricated layer.

The substantive test is `test_the_weak_off_network_bound_gives_the_same_answers...`: it checks the
claim that the weak `OFF_NETWORK` bound of 0 is not merely *sound* but *outcome-identical* to the
bound the pipeline really computes, at the thresholds this audit uses, and that it stops being so
below that bound.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from locfinder.grid import GridSpec
from locfinder.status import (CATEGORY_COST_SELECTED, Criterion, Outcome, Reason, Surface,
                              evaluate)
from locfinder.traveltime.speeds import max_speed_mps

_PATH = Path(__file__).resolve().parents[1] / "scripts" / "audit_recommendations.py"
_SPEC = importlib.util.spec_from_file_location("audit_recommendations", _PATH)
audit = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(audit)

HORIZON_S = audit.CUTOFF_MIN * 60.0
THRESHOLDS_S = (600.0, 900.0)


def _grid() -> GridSpec:
    return GridSpec("EPSG:32617", 450000.0, 4000000.0, 100.0, 6, 5)


def _arrays(reason_codes: list[int], *, seconds_for_ok: float = 500.0):
    """A seconds/reason pair that is internally consistent: finite exactly where the reason is OK."""
    reason = np.array(reason_codes, dtype=np.int8).reshape(5, 6)
    seconds = np.where(reason == Reason.OK, seconds_for_ok, np.inf)
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
    """The refusal the whole shortcut rests on. Reconstructed with a bound of 0, a NO_PATH cell
    would read as UNKNOWN — a proven failure turned into an absence."""
    codes = [0] * 10 + [1] * 9 + [3] + [2] * 10      # one NO_PATH
    seconds, reason = _arrays(codes)
    layers = _write(tmp_path, seconds, reason)

    with pytest.raises(audit.Refused, match="NO_PATH"):
        _load(layers)

    # And the test is not vacuous: without that cell the same layer loads.
    codes[19] = 1
    _load(_write(tmp_path, *_arrays(codes)))


def test_it_refuses_when_the_weak_off_network_bound_could_change_an_answer(tmp_path):
    """A threshold below the largest real access bound makes 0 a *different* answer, not just a
    weaker one, so the script refuses rather than reporting UNKNOWN where the pipeline proves
    FAIL."""
    layers = _write(tmp_path, *_arrays([0] * 10 + [1] * 10 + [2] * 10))
    real_bound_max = audit.MAX_ACCESS_M / max_speed_mps("walk")
    assert 100.0 < real_bound_max < 600.0, "the arithmetic this test depends on has moved"

    with pytest.raises(audit.Refused, match="outcome-equivalent"):
        _load(layers, thresholds_s=(100.0,))
    _load(layers, thresholds_s=(600.0,))      # and it is accepted above the bound


def test_the_weak_off_network_bound_gives_the_same_answers_as_the_real_one(tmp_path):
    """The claim that licenses the reconstruction, tested directly rather than argued.

    The pipeline's real bound is `access_m / max_speed_mps` (`traveltime/snap.py:291`), at most
    `200 / 1.4 = 142.9 s` walking. `evaluate` turns a bound into a known failure only when it
    strictly exceeds the threshold, so at 600 s and 900 s the real bound and 0 agree on every cell.
    """
    rng = np.random.default_rng(20261109)
    codes = [0] * 10 + [1] * 10 + [2] * 10
    seconds, reason = _arrays(codes)
    off = reason == Reason.OFF_NETWORK
    # The real bound, with access distances spread over the whole admissible range.
    access_m = np.where(off, rng.uniform(0.0, audit.MAX_ACCESS_M, size=reason.shape), 0.0)
    real = np.where(off, access_m / max_speed_mps("walk"), 0.0)
    real = np.where(reason == Reason.OK, seconds, real)
    real = np.where(reason == Reason.BEYOND_HORIZON, HORIZON_S, real)
    weak = np.where(reason == Reason.OK, seconds, 0.0)
    weak = np.where(reason == Reason.BEYOND_HORIZON, HORIZON_S, weak)

    def surface(bound):
        return Surface(mode="walk", engine="own-graph", target="grocery",
                       aggregation=CATEGORY_COST_SELECTED, horizon_s=HORIZON_S,
                       seconds=seconds.astype(np.float64), reason=reason,
                       min_possible_s=bound.astype(np.float64)).validate()

    def outcomes(bound, t_s):
        crit = Criterion(label="x", mode="walk", target="grocery", kind="category", threshold_s=t_s)
        return evaluate(crit, surface(bound))

    for t_s in THRESHOLDS_S:
        assert np.array_equal(outcomes(real, t_s), outcomes(weak, t_s)), \
            f"the bounds disagree at {t_s}s, so the reconstruction is not outcome-identical"
        assert (outcomes(weak, t_s)[off] == Outcome.UNKNOWN).all()

    # Below the real bound they genuinely differ, which is what the refusal above protects.
    tight = 60.0
    assert not np.array_equal(outcomes(real, tight), outcomes(weak, tight))
    assert (outcomes(real, tight)[off] == Outcome.FAIL).any()


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


def test_it_refuses_a_seconds_and_reason_pair_from_different_builds(tmp_path):
    """The two files were written by separate runs 43 minutes apart. `Surface.validate` requires a
    finite time exactly where the reason is OK, so an inconsistent pair is caught rather than
    silently mislabelling cells — but the message has to say so."""
    seconds, reason = _arrays([0] * 10 + [1] * 10 + [2] * 10)
    reason = reason.copy()
    reason[0, 0] = Reason.OFF_NETWORK          # a finite time now carries a non-OK reason
    with pytest.raises(audit.Refused, match="do not describe one surface"):
        _load(_write(tmp_path, seconds, reason))


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
