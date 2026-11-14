"""Pass 50 finding A2: the surface-binding gate, and the controls that show it can fail.

The gate exists because a fingerprint was being stamped on a plane that had never been compared
with the surface it names. Pass 50 then showed the first version compared only the journey
masks, which 256,276 cells of this layer can slip past.
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

import persist_selected_destination as persist                  # noqa: E402
from locfinder import wire                                      # noqa: E402

HORIZON = 7200.0


def _surface():
    """Three cells with a journey, one unreachable."""
    stored = np.array([[300.0, 600.0], [900.0, np.inf]], dtype=np.float32)
    ordinals = np.array([[0, 1], [1, wire.DEST_NONE]], dtype=wire.DEST_DTYPE)
    return stored, ordinals


def test_the_gate_accepts_a_plane_that_describes_its_surface():
    stored, ordinals = _surface()
    got = persist.check_plane_describes_the_surface(
        ordinals, stored, stored.astype(np.float64), HORIZON, label="s.npy")
    assert got["cells_compared"] == 3
    assert got["cells_differing"] == 0
    assert got["reachability_differing"] == 0
    assert got["compared_as"] == "float32"


def test_the_gate_catches_times_that_changed_while_the_mask_did_not():
    """**The control the first version of this gate failed.**

    Sixty seconds are added to every cell with a journey. Every one stays finite and within the
    horizon, so the journey-presence mask is untouched and the mask-only check passed -- while
    every published minute moved. This is Codex's construction, at three cells instead of
    256,276.
    """
    stored, ordinals = _surface()
    altered = stored.astype(np.float64)
    moved = np.isfinite(altered) & (altered <= HORIZON - 60)
    altered[moved] += 60.0
    assert int(moved.sum()) == 3, "the control did not move anything"
    # The mask is genuinely unchanged, which is why the old check could not see this.
    old_mask = np.isfinite(stored) & (stored <= HORIZON)
    new_mask = np.isfinite(altered) & (altered <= HORIZON)
    assert np.array_equal(old_mask, new_mask), "the control changed the mask, so it is the wrong "\
        "control -- the point is a change the mask cannot see"
    with pytest.raises(SystemExit, match="journey times recomputed here disagree"):
        persist.check_plane_describes_the_surface(
            ordinals, stored, altered, HORIZON, label="s.npy")


def test_the_gate_catches_a_difference_of_one_float32_bit():
    """No tolerance to argue about: the comparison is exact after the storage cast."""
    stored, ordinals = _surface()
    altered = stored.astype(np.float64)
    altered[0, 0] = float(np.nextafter(np.float32(300.0), np.float32(400.0)))
    assert altered[0, 0] != 300.0
    with pytest.raises(SystemExit, match="journey times recomputed here disagree"):
        persist.check_plane_describes_the_surface(
            ordinals, stored, altered, HORIZON, label="s.npy")


def test_the_gate_catches_reachability_that_changed():
    stored, ordinals = _surface()
    altered = stored.astype(np.float64)
    altered[1, 1] = 1200.0           # was unreachable
    with pytest.raises(SystemExit, match="reachability differs|journey times recomputed"):
        persist.check_plane_describes_the_surface(
            ordinals, stored, altered, HORIZON, label="s.npy")


def test_the_gate_still_catches_a_mask_disagreement():
    """The pass 49 half of the gate, kept and controlled."""
    stored, ordinals = _surface()
    orphaned = ordinals.copy()
    orphaned[1, 1] = 0               # names a destination where there is no journey
    with pytest.raises(SystemExit, match="names 1 cells the surface gives no journey"):
        persist.check_plane_describes_the_surface(
            orphaned, stored, stored.astype(np.float64), HORIZON, label="s.npy")
    unnamed = ordinals.copy()
    unnamed[0, 0] = wire.DEST_NONE   # publishes a time and names nothing
    with pytest.raises(SystemExit, match="leaves 1 of the surface's journeys unnamed"):
        persist.check_plane_describes_the_surface(
            unnamed, stored, stored.astype(np.float64), HORIZON, label="s.npy")


def test_the_tie_control_pins_its_known_answer():
    """Pass 50 finding G5: the control accepted movement from an algorithm that never solved it.

    `destination_tie_control` required "more than one destination selected" and "one seconds
    value". A broken solver returning zeros everywhere satisfies both -- the constant selected
    index maps back to three different original nodes under relabelling, and the seconds never
    move. So the control now pins the ABSOLUTE answer: 300 seconds, destinations exactly {0, 1}.
    """
    got = persist.destination_tie_control()
    assert got["published_seconds_at_the_target"] == [300.0], got
    assert got["destinations_selected_across_relabellings"] == [0, 1], got
    assert got["total_destination_moves"] == 1
    assert got["total_seconds_moves"] == 0


def test_the_tie_gate_refuses_a_solver_that_never_solves_the_construction(monkeypatch):
    """**The control on the control** -- pass 50 finding G5's own reproducer.

    A solver that ignores costs and candidates and returns zeros everywhere satisfied the two
    original acceptance conditions: one seconds value, and more than one "selected" destination
    once the relabelling is mapped back. The gate now pins the known answer, so it refuses.
    """
    def broken(cost, time, **kwargs):
        n = cost.shape[0]
        return np.zeros(n), np.zeros(n, dtype=np.int64)

    monkeypatch.setattr(persist, "arrival_with_selected_destination", broken)
    got = persist.destination_tie_control()
    # The broken solver does satisfy the ORIGINAL two conditions, which is the finding.
    assert got["total_destination_moves"] > 0, got
    assert got["total_seconds_moves"] == 0, got
    # And it fails the pinned answer, which is the repair.
    assert got["published_seconds_at_the_target"] != [persist.CONTROL_SECONDS]
