"""The published wire format, S3.5.

The claim these pin down is not "the encoder runs". It is that **a browser holding only the two
planes reaches the same verdict as `status.evaluate` on the full surface**, for every threshold a
slider can produce. Everything else here exists to stop that claim being true by accident.
"""
from __future__ import annotations

import json
import math
import pathlib

import numpy as np
import pytest

from locfinder import wire
from locfinder.status import (CATEGORY_COST_SELECTED, Criterion, Outcome, Reason,
                              Surface, Verdict, combine, evaluate)

LAYERS = pathlib.Path(__file__).resolve().parents[1] / "data" / "layers"
PUBLISHED = LAYERS / "own_triangle_grocery_walk.npy"


def surface_from(seconds, reason, lower, horizon_s=7200.0) -> Surface:
    return Surface(mode="walk", engine="own-graph", target="grocery",
                   aggregation=CATEGORY_COST_SELECTED, horizon_s=horizon_s,
                   seconds=np.asarray(seconds, dtype=np.float64),
                   reason=np.asarray(reason, dtype=np.int8),
                   min_possible_s=np.asarray(lower, dtype=np.float64)).validate()


def criterion(t_min: int) -> Criterion:
    return Criterion(label=f"grocery-{t_min}", mode="walk", target="grocery",
                     kind="category", threshold_s=float(t_min) * 60.0)


def hand_built() -> Surface:
    """One cell per case the format has to tell apart, with the bounds that decide them.

    No layer-wide reason appears here, and that is not an oversight: `Surface.validate` requires a
    layer-wide reason to cover **every** cell, so `LAYER_UNKNOWN` is an all-or-nothing plane and
    gets its own test below.
    """
    seconds = [300.0, 600.0, 601.0, np.inf, np.inf, np.inf, np.inf]
    reason = [Reason.OK, Reason.OK, Reason.OK, Reason.OFF_NETWORK, Reason.OFF_NETWORK,
              Reason.BEYOND_HORIZON, Reason.NO_PATH]
    #                 a 3-minute bound        a 40-minute bound    the horizon     unreachable
    lower = [300.0, 600.0, 601.0, 180.0, 2400.0, 7200.0, np.inf]
    return surface_from(seconds, reason, lower)


# --------------------------------------------------------------------------- the central claim


@pytest.mark.skipif(not PUBLISHED.exists(), reason="the published layer is not on this checkout")
@pytest.mark.parametrize("t_min", [1, 5, 10, 15, 25, 45, 60, 119, 120, 121])
def test_the_wire_planes_reach_evaluates_verdict_on_the_published_layer(t_min):
    """The whole point of the format. 330,502 real cells, every threshold a slider can produce,
    and the two decoders must agree **cell for cell** — not in aggregate, which would let an
    over-exclusion in one place cancel an under-exclusion in another."""
    seconds = np.load(PUBLISHED).astype(np.float64)
    reason = np.load(LAYERS / "own_triangle_grocery_walk_reason.npy")
    lower = np.load(LAYERS / "own_triangle_grocery_walk_min_possible_s.npy").astype(np.float64)
    horizon = json.loads(
        (LAYERS / "own_triangle_grocery_walk_build.json").read_text())["horizon_s"]
    surf = surface_from(seconds, reason, lower, horizon_s=horizon)

    value, status = wire.encode_planes(surf)
    from_wire = wire.outcome_planes(value, status, threshold_min=t_min, horizon_s=horizon)
    from_surface = evaluate(criterion(t_min), surf)
    disagreements = int((from_wire != from_surface).sum())
    assert disagreements == 0, f"{disagreements} cells differ at T={t_min}"


def test_every_distinguishable_case_survives_the_round_trip():
    surf = hand_built()
    value, status = wire.encode_planes(surf)
    assert list(status) == [wire.OK, wire.OK, wire.OK, wire.OFF_NETWORK, wire.OFF_NETWORK,
                            wire.BEYOND_HORIZON, wire.NO_PATH]
    # minutes rounded UP, and the bound rounded up too; an infinite bound saturates
    assert list(value) == [5, 10, 11, 3, 40, 120, wire.VALUE_MAX]


@pytest.mark.parametrize("t_min", [1, 3, 5, 10, 11, 39, 40, 41, 120, 121])
def test_the_hand_built_cases_match_evaluate(t_min):
    surf = hand_built()
    value, status = wire.encode_planes(surf)
    got = wire.outcome_planes(value, status, threshold_min=t_min, horizon_s=surf.horizon_s)
    assert list(got) == list(evaluate(criterion(t_min), surf))


# --------------------------------------------------------------------------- what v1 could not say


def test_a_bounded_off_network_cell_is_a_known_failure_and_not_an_unknown():
    """The defect the second plane exists to fix. A cell with no road within 200 m but a 40-minute
    lower bound is **excluded** at ten minutes. The old format carried one NODATA code, so the
    browser could only call it unknown."""
    surf = hand_built()
    value, status = wire.encode_planes(surf)
    at10 = wire.outcome_planes(value, status, threshold_min=10, horizon_s=surf.horizon_s)
    assert at10[4] == int(Outcome.FAIL)      # off network, 40-minute bound
    assert at10[3] == int(Outcome.UNKNOWN)   # off network, 3-minute bound: genuinely unknown
    assert at10[5] == int(Outcome.FAIL)      # beyond a 120-minute horizon


def test_beyond_horizon_becomes_unknown_only_above_the_horizon():
    """It is a known failure at every threshold at or below the horizon, and unknown above it —
    the one case `needs_recomputation` exists for."""
    surf = hand_built()
    value, status = wire.encode_planes(surf)
    assert wire.outcome_planes(value, status, threshold_min=120,
                               horizon_s=surf.horizon_s)[5] == int(Outcome.FAIL)
    assert wire.outcome_planes(value, status, threshold_min=121,
                               horizon_s=surf.horizon_s)[5] == int(Outcome.UNKNOWN)


def test_a_known_failure_beats_an_unknown_across_layers():
    """The browser's `break` on the first missing value inverted exactly this rule."""
    unknown = np.array([int(Outcome.UNKNOWN)])
    fail = np.array([int(Outcome.FAIL)])
    ok = np.array([int(Outcome.PASS)])
    assert wire.combine_planes([unknown, fail])[0] == int(Verdict.EXCLUDED)
    assert wire.combine_planes([unknown, ok])[0] == int(Verdict.UNKNOWN)
    assert wire.combine_planes([ok, ok])[0] == int(Verdict.INCLUDED)
    assert wire.combine_planes([fail, unknown])[0] == int(Verdict.EXCLUDED)


def test_combine_planes_agrees_with_status_combine():
    rng = np.random.default_rng(11)
    for _ in range(50):
        planes = [rng.integers(0, 3, size=97).astype(np.int8) for _ in range(rng.integers(1, 4))]
        assert np.array_equal(wire.combine_planes(planes), combine(planes))


# --------------------------------------------------------------------------- the safe direction


def test_an_oversized_bound_saturates_because_a_weaker_bound_is_always_safe():
    surf = surface_from([np.inf], [Reason.OFF_NETWORK], [1e9])
    value, status = wire.encode_planes(surf)
    assert value[0] == wire.VALUE_MAX
    # saturated downward, so it can only fail to exclude — never wrongly exclude
    assert wire.outcome_planes(value, status, threshold_min=wire.VALUE_MAX,
                               horizon_s=surf.horizon_s)[0] == int(Outcome.UNKNOWN)


def test_an_ok_minute_above_the_cap_is_refused_rather_than_capped():
    """Capping an OK minute downward would turn a failing cell into a passing one. The format
    refuses instead, which narrows what it can publish and never misreports what it does."""
    surf = surface_from([wire.VALUE_MAX * 60.0 + 60.0], [Reason.OK],
                        [wire.VALUE_MAX * 60.0 + 60.0], horizon_s=1e9)
    with pytest.raises(ValueError, match="above the format"):
        wire.encode_planes(surf)


def test_a_status_code_the_decoder_does_not_define_is_refused():
    with pytest.raises(ValueError, match="does not define"):
        wire.outcome_planes(np.array([5], dtype=np.uint8), np.array([99], dtype=np.uint8),
                            threshold_min=10, horizon_s=7200.0)


def test_outside_is_unknown_and_is_not_the_same_code_as_off_network():
    """A pixel the export covers and the source did not is not a cell with no road near it. v1 had
    one code for both."""
    assert wire.OUTSIDE != wire.OFF_NETWORK
    got = wire.outcome_planes(np.array([wire.VALUE_NONE], dtype=np.uint8),
                              np.array([wire.OUTSIDE], dtype=np.uint8),
                              threshold_min=10, horizon_s=7200.0)
    assert got[0] == int(Outcome.UNKNOWN)


def test_legacy_minute_values_are_still_minute_values():
    """S3.5's constraint: 251–254 are real answers in artifacts on disk, so no sentinel scheme may
    reinterpret them. In this format they are ordinary minutes and the status plane carries the
    sentinels instead."""
    surf = surface_from([251 * 60.0, 254 * 60.0], [Reason.OK, Reason.OK],
                        [251 * 60.0, 254 * 60.0], horizon_s=1e9)
    value, status = wire.encode_planes(surf)
    assert list(value) == [251, 254]
    assert list(status) == [wire.OK, wire.OK]
    got = wire.outcome_planes(value, status, threshold_min=252, horizon_s=1e9)
    assert list(got) == [int(Outcome.PASS), int(Outcome.FAIL)]

def test_a_layer_wide_failure_encodes_to_an_all_unknown_plane():
    """`Surface.validate` requires a layer-wide reason to cover every cell, so this code can never
    appear beside a per-cell one. A layer that could not be built knows nothing anywhere, and the
    format says so rather than publishing a region."""
    surf = Surface.layer_failure(
        mode="walk", engine="own-graph", target="grocery",
        aggregation=CATEGORY_COST_SELECTED, horizon_s=7200.0, shape=(3, 4),
        reason=Reason.NO_DESTINATIONS).validate()
    value, status = wire.encode_planes(surf)
    assert (status == wire.LAYER_UNKNOWN).all()
    assert (value == wire.VALUE_NONE).all()
    got = wire.outcome_planes(value, status, threshold_min=10, horizon_s=7200.0)
    assert (got == int(Outcome.UNKNOWN)).all()
    assert np.array_equal(got, evaluate(criterion(10), surf))


def test_no_path_is_a_known_failure_at_every_threshold():
    surf = hand_built()
    value, status = wire.encode_planes(surf)
    for t_min in (1, 10, 120, 254):
        got = wire.outcome_planes(value, status, threshold_min=t_min, horizon_s=surf.horizon_s)
        assert got[6] == int(Outcome.FAIL), t_min


def test_a_v1_artifact_lifts_without_inventing_provenance():
    """`UNKNOWN_CAUSE` is what v1's single NODATA becomes. It can never be a known failure, which
    is exactly what v1 could assert — so lifting an old layer changes no verdict, and the 10,000
    structures v1 had to call unknown stay unknown rather than being guessed into an exclusion."""
    value = np.array([5, wire.VALUE_NONE], dtype=np.uint8)
    status = np.array([wire.OK, wire.UNKNOWN_CAUSE], dtype=np.uint8)
    for t_min in (1, 10, 254):
        got = wire.outcome_planes(value, status, threshold_min=t_min, horizon_s=7200.0)
        assert got[1] == int(Outcome.UNKNOWN), t_min
    assert wire.UNKNOWN_CAUSE not in (wire.OFF_NETWORK, wire.BEYOND_HORIZON, wire.OUTSIDE)


def test_every_unknown_code_is_unknown_at_every_threshold():
    for code in wire.UNKNOWN_CODES:
        got = wire.outcome_planes(np.array([0], dtype=np.uint8),
                                  np.array([code], dtype=np.uint8),
                                  threshold_min=1, horizon_s=7200.0)
        assert got[0] == int(Outcome.UNKNOWN), code


def test_a_fractional_threshold_is_refused_rather_than_truncated():
    """Pass 43 F7. `ceil(x/60) > T` is equivalent to `x > 60T` only for integer `T`, so the minute
    planes cannot answer a fractional threshold exactly. Truncating one turned a 610-second cell
    that passes 10.5 minutes into a failure, and turned a non-strict bound into an exclusion —
    manufacturing the one direction of error this format must not have."""
    surf = surface_from([610.0, np.inf], [Reason.OK, Reason.OFF_NETWORK], [610.0, 610.0])
    value, status = wire.encode_planes(surf)
    assert list(evaluate(Criterion(label="g", mode="walk", target="grocery", kind="category",
                                   threshold_s=630.0), surf)) == [int(Outcome.PASS),
                                                                  int(Outcome.UNKNOWN)]
    with pytest.raises(ValueError, match="whole number of minutes"):
        wire.outcome_planes(value, status, threshold_min=10.5, horizon_s=surf.horizon_s)
    # An integer-valued float is still a whole number of minutes and is accepted.
    assert len(wire.outcome_planes(value, status, threshold_min=10.0,
                                   horizon_s=surf.horizon_s)) == 2


def test_a_beyond_horizon_cell_carries_the_horizon_as_its_bound():
    """Which makes the value plane redundant for that code — and therefore a checksum. The
    decoder compares against the manifest's horizon and never against the stored bound, so if the
    two disagree the manifest is not describing these planes. `worker.js` refuses that at init."""
    surf = hand_built()
    value, status = wire.encode_planes(surf)
    bh = status == wire.BEYOND_HORIZON
    assert bh.any()
    assert (value[bh] == min(int(math.ceil(surf.horizon_s / 60.0)), wire.VALUE_MAX)).all()


# --------------------------------------------------------------------------- the route flag


def test_a_route_flag_may_only_be_set_where_there_is_a_published_journey():
    """Step 8's disclosure. Only an `OK` cell has a route to describe, so a flag anywhere else
    asserts something the format denies — and this invariant caught a real defect before the plane
    shipped: the flag had been computed without the surface's horizon, so 5,145 cells disclosed a
    route for a journey that had become BEYOND_HORIZON."""
    status = np.array([wire.OK, wire.OFF_NETWORK, wire.BEYOND_HORIZON], dtype=np.uint8)
    good = wire.encode_route_flag(np.array([True, False, False]), status)
    assert list(good) == [wire.ROUTE_RESTRICTED, wire.ROUTE_CLEAR, wire.ROUTE_CLEAR]
    for bad in ([False, True, False], [False, False, True]):
        with pytest.raises(ValueError, match="no route"):
            wire.encode_route_flag(np.array(bad), status)


def test_the_flag_is_never_an_eligibility_input():
    """A disclosure must not be able to move a verdict, and the guarantee is structural:
    `outcome_planes` does not take the flag as an argument at all."""
    import inspect
    assert "flag" not in inspect.signature(wire.outcome_planes).parameters
    assert "flag" not in inspect.signature(wire.combine_planes).parameters


def test_disclosed_restricted_reads_the_flag_only_where_the_outcome_passes():
    outcomes = np.array([int(Outcome.PASS), int(Outcome.FAIL), int(Outcome.UNKNOWN)],
                        dtype=np.int8)
    flag = np.array([wire.ROUTE_RESTRICTED] * 3, dtype=np.uint8)
    got = wire.disclosed_restricted(flag, outcomes)
    assert list(got) == [True, False, False]


def test_a_layer_with_no_flag_plane_discloses_nothing_rather_than_being_clean():
    """The `UNKNOWN_CAUSE` lesson again: absence of provenance is not evidence of cleanliness. A
    caller asking about a layer that carries no plane gets an error, not a `False`."""
    with pytest.raises(ValueError, match="discloses nothing"):
        wire.disclosed_restricted(None, np.array([int(Outcome.PASS)], dtype=np.int8))


def test_every_earlier_encoding_is_readable_and_v4_is_the_one_written():
    """Each version adds an optional plane and reinterprets no code, so every earlier bundle
    stays readable and simply carries fewer facts. The written encoding is the newest."""
    assert wire.ENCODING == "published-v4"
    assert set(wire.READABLE_ENCODINGS) == {"published-v2", "published-v3", "published-v4"}
    assert wire.ENCODING in wire.READABLE_ENCODINGS

# --------------------------------------------------------------- the selected-destination plane


def test_a_destination_may_only_be_named_where_the_status_is_ok():
    status = np.array([wire.OK, wire.OFF_NETWORK], dtype=np.uint8)
    with pytest.raises(ValueError, match="no published journey for it to be the destination OF"):
        wire.encode_selected_destination(np.array([3, 4]), status)


def test_a_published_time_with_no_destination_is_a_contradiction_not_a_silence():
    """**The direction the route-flag plane cannot have.**

    Pass 48 F3: a *clear* flag asserts nothing, so a flag plane cannot be validated from its own
    contents -- one flag flipped down and one up passed every check in the pipeline. `DEST_NONE`
    beside a published time is a different kind of value. A published time is a time *to
    somewhere*, so this is the plane and the surface disagreeing about whether a journey exists,
    and it is refusable.
    """
    status = np.array([wire.OK, wire.OK], dtype=np.uint8)
    with pytest.raises(ValueError, match="publish a time and name no destination"):
        wire.encode_selected_destination(np.array([wire.DEST_NONE, wire.DEST_NONE]), status)


def test_both_directions_together_accept_only_the_consistent_plane():
    status = np.array([wire.OK, wire.OFF_NETWORK, wire.OK, wire.BEYOND_HORIZON], dtype=np.uint8)
    got = wire.encode_selected_destination(
        np.array([0, wire.DEST_NONE, 509, wire.DEST_NONE]), status)
    assert list(got) == [0, wire.DEST_NONE, 509, wire.DEST_NONE]
    assert got.dtype == np.dtype(wire.DEST_DTYPE)


def test_a_destination_plane_of_the_wrong_shape_is_refused():
    with pytest.raises(ValueError, match="cell for cell"):
        wire.encode_selected_destination(np.zeros((2, 2), dtype=np.uint16),
                                         np.zeros(4, dtype=np.uint8))


def test_an_ordinal_outside_the_representable_range_is_refused():
    status = np.array([wire.OK], dtype=np.uint8)
    with pytest.raises(ValueError, match="outside"):
        wire.encode_selected_destination(np.array([wire.DEST_NONE + 1]), status)


def test_the_destination_plane_goes_on_the_wire_little_endian_whatever_the_host():
    """**The only plane with a byte order, and the reason is the failure mode.**

    A `uint16` plane read with the wrong order yields ordinals that are *valid* -- they index real
    destinations -- and wrong. That produces a confident incorrect shop name rather than an error,
    which is why the order is declared in the manifest and written through an explicit dtype
    rather than through `tobytes()` on whatever the caller happened to hold.
    """
    plane = np.array([[1, 258], [wire.DEST_NONE, 0]], dtype=wire.DEST_DTYPE)
    raw = wire.destination_plane_bytes(plane)
    assert raw[:4] == bytes([0x01, 0x00, 0x02, 0x01])          # 1, then 258 = 0x0102
    assert np.array_equal(wire.decode_destination_plane(raw, plane.shape), plane)
    # Big-endian input is the counterfactual: the same bytes read the wrong way round are a
    # DIFFERENT valid plane, not an error. Nothing in the bytes themselves can catch it.
    swapped = np.frombuffer(raw, dtype=np.dtype(">u2")).reshape(plane.shape)
    assert not np.array_equal(swapped, plane)
    assert int(swapped[0, 0]) == 256


def test_a_destination_plane_that_does_not_fit_the_layer_is_refused_rather_than_reshaped():
    raw = wire.destination_plane_bytes(np.zeros(5, dtype=wire.DEST_DTYPE))
    with pytest.raises(ValueError, match="refusing to reshape"):
        wire.decode_destination_plane(raw, (2, 3))


def test_the_destination_is_never_an_eligibility_input():
    """Same structural guarantee as the flag, and the same limit on what a signature proves:
    pass 48 found a coupling that changes no signature, so `mutate_worker.mjs` carries the
    mutation and the two-layer fixtures that catch it."""
    import inspect
    for name in ("dest", "destination", "selected"):
        assert name not in inspect.signature(wire.outcome_planes).parameters
        assert name not in inspect.signature(wire.combine_planes).parameters


def test_named_destination_reads_the_plane_only_where_the_outcome_passes():
    outcomes = np.array([int(Outcome.PASS), int(Outcome.FAIL), int(Outcome.UNKNOWN)],
                        dtype=np.int8)
    plane = np.array([7, 8, 9], dtype=wire.DEST_DTYPE)
    got = wire.named_destination(plane, outcomes)
    assert list(got) == [7, wire.DEST_NONE, wire.DEST_NONE]


def test_a_layer_with_no_destination_plane_says_nothing_rather_than_having_no_destination():
    """*Absence is not evidence of cleanliness*, for the fourth plane as for the third."""
    with pytest.raises(ValueError, match="does not say"):
        wire.named_destination(None, np.array([int(Outcome.PASS)], dtype=np.int8))


def test_v4_reads_every_earlier_encoding():
    assert wire.ENCODING == "published-v4"
    for older in ("published-v2", "published-v3"):
        assert older in wire.READABLE_ENCODINGS

def test_the_javascript_encoding_lists_match_the_python_one():
    """**The encoding set lives in five places and a bump missed three of them.**

    `wire.py` is the source. `worker.js` and `app.js` each hold their own literal, because a
    browser worker cannot import Python, and two tests used to hold a third and fourth. Adding
    `published-v4` broke the conformance harness on the worker's copy and would have shipped a
    page that refused the manifest it had just helped produce.

    The duplication is unavoidable; going unchecked was not. This fails once, here, with the two
    lists printed side by side.
    """
    import re
    spike = pathlib.Path(__file__).resolve().parents[1] / "spikes" / "g3-render"
    for name, pattern in (
        ("worker.js", r"const READABLE_ENCODINGS = \[([^\]]*)\]"),
        ("app.js", r"const READABLE = \[([^\]]*)\]"),
    ):
        source = (spike / name).read_text(encoding="utf-8")
        found = re.search(pattern, source)
        assert found, f"{name} no longer declares a readable-encoding list under a known name"
        listed = tuple(s.strip().strip("'\"") for s in found.group(1).split(",") if s.strip())
        assert listed == tuple(wire.READABLE_ENCODINGS), (
            f"{name} reads {listed} and locfinder.wire reads "
            f"{tuple(wire.READABLE_ENCODINGS)}")
