"""Phase 1 S0. The truth table row by row, plus proof that the real pipeline *produces* each
status rather than merely declaring it.

The second half exists because of `expansion.py`: that module's reconstruction was certified by
unit tests for weeks while nothing outside the tests ever called it, and when a real payload was
finally fed in it was wrong. A status enum nothing produces is the same trap.
"""
import math

import networkx as nx
import numpy as np
import pytest

from locfinder import status as st
from locfinder.status import Criterion, Outcome, Reason, Surface, Verdict
from locfinder.traveltime.arrival import arrival_seconds, arrival_seconds_two_weight
from locfinder.traveltime.csr import graph_to_cost_time_csr
from locfinder.traveltime.snap import EdgeIndex, cell_arrival_with_provenance
from locfinder.traveltime.speeds import add_travel_times, max_speed_mps

H = 120 * 60.0  # the built horizon of the shipped own-graph layers


def surface(reason, *, seconds=np.inf, min_possible=0.0, horizon_s=H, mode="walk",
            engine="own-graph", aggregation=st.CATEGORY_COST_SELECTED, target="grocery"):
    """A one-cell surface in a given state, validated — producers must satisfy the invariants."""
    return Surface(
        mode=mode, engine=engine, target=target, aggregation=aggregation, horizon_s=horizon_s,
        seconds=np.array([seconds]), reason=np.array([int(reason)], dtype=np.int8),
        min_possible_s=np.array([min_possible]),
    ).validate()


def crit(threshold_s, *, kind="category", target="grocery", mode="walk"):
    return Criterion(label="t", mode=mode, target=target, kind=kind, threshold_s=threshold_s)


# ---------------------------------------------------------------- the taxonomy

def test_only_statuses_the_pipeline_can_produce_exist():
    """S0.1's pass criterion, executable. Adding a member here must mean a producer exists; the
    module docstring names the two causes that are deliberately absent (component pruning and
    extract truncation) because the pipeline cannot produce them."""
    assert set(Reason) == st.PER_CELL_REASONS | st.LAYER_REASONS
    assert not st.PER_CELL_REASONS & st.LAYER_REASONS
    assert {r.name for r in st.PER_CELL_REASONS} == {
        "OK", "OFF_NETWORK", "BEYOND_HORIZON", "NO_PATH"}
    assert {r.name for r in st.LAYER_REASONS} == {
        "NO_DESTINATIONS", "NO_ROUTABLE_DESTINATIONS", "SOURCE_MISSING"}


def test_no_path_is_weakened_for_an_engine_that_cannot_prove_it():
    """Valhalla /expansion is bounded by its contour, so an absent edge is indistinguishable from
    an unreachable one; the honest published status is the weaker 'not reached within the horizon'."""
    assert st.engine_for("walk").proves_no_path is True
    for mode in ("drive", "bike", "transit"):
        assert st.engine_for(mode).proves_no_path is False
        assert st.honest_reason(Reason.NO_PATH, st.engine_for(mode)) == Reason.BEYOND_HORIZON
    assert st.honest_reason(Reason.NO_PATH, st.engine_for("walk")) == Reason.NO_PATH
    # the weakening is not a general downgrade: everything else passes through untouched
    for r in Reason:
        if r != Reason.NO_PATH:
            assert st.honest_reason(r, st.engine_for("drive")) == r


def test_a_bounded_engine_may_not_publish_no_path_at_all():
    with pytest.raises(ValueError, match="cannot prove NO_PATH"):
        surface(Reason.NO_PATH, min_possible=np.inf, mode="drive", engine="valhalla-expansion")


def test_node_reasons_follow_the_engine():
    T = np.array([0.0, 60.0, np.inf])
    own = st.node_reasons(T, st.engine_for("walk"), search_bounded=False)
    val = st.node_reasons(T, st.engine_for("drive"), search_bounded=False)
    assert list(own) == [Reason.OK, Reason.OK, Reason.NO_PATH]
    assert list(val) == [Reason.OK, Reason.OK, Reason.BEYOND_HORIZON]


# ---------------------------------------------------------------- one criterion, one cell

def test_ok_cell_passes_at_or_below_the_threshold_and_fails_above():
    s = surface(Reason.OK, seconds=600.0)
    assert st.evaluate(crit(600.0), s)[0] == Outcome.PASS, "the threshold is inclusive"
    assert st.evaluate(crit(601.0), s)[0] == Outcome.PASS
    assert st.evaluate(crit(599.0), s)[0] == Outcome.FAIL


def test_no_path_fails_every_threshold():
    s = surface(Reason.NO_PATH, min_possible=np.inf)
    for t in (60.0, H, 10 * H):
        assert st.evaluate(crit(t), s)[0] == Outcome.FAIL


def test_beyond_horizon_fails_a_threshold_inside_the_horizon_and_is_unknown_outside_it():
    """The row that makes the table worth writing. 'Not reached within 120 minutes' is a *known*
    failure for any criterion of 120 minutes or less -- the time is provably greater -- and is
    unknown only for a threshold the surface was never built to answer."""
    s = surface(Reason.BEYOND_HORIZON, min_possible=H)
    assert st.evaluate(crit(30 * 60.0), s)[0] == Outcome.FAIL
    assert st.evaluate(crit(H), s)[0] == Outcome.FAIL, "t > H and T == H, so the criterion fails"
    assert st.evaluate(crit(H + 1.0), s)[0] == Outcome.UNKNOWN


def test_beyond_the_horizon_is_answerable_and_says_so():
    s = surface(Reason.BEYOND_HORIZON, min_possible=H)
    assert not st.needs_recomputation(crit(H), s)[0]
    assert st.needs_recomputation(crit(H + 1.0), s)[0]
    # an off-network cell is not answerable by searching further, so it must not be offered
    assert not st.needs_recomputation(
        crit(H + 1.0), surface(Reason.OFF_NETWORK, min_possible=10.0))[0]


def test_off_network_is_unknown_unless_the_distance_alone_already_fails():
    far_s = 400.0 / max_speed_mps("walk")          # 400 m from any edge, walking
    s = surface(Reason.OFF_NETWORK, min_possible=far_s)
    assert st.evaluate(crit(far_s - 1.0), s)[0] == Outcome.FAIL, "the walk alone exceeds the budget"
    assert st.evaluate(crit(far_s + 1.0), s)[0] == Outcome.UNKNOWN
    assert st.evaluate(crit(15 * 60.0), s)[0] == Outcome.UNKNOWN


def test_the_lower_bound_uses_the_fastest_speed_not_the_access_speed():
    """A bound must not over-estimate, or it excludes cells that should be unknown. The access
    speed factors are all below 1, so an access-speed estimate is an over-estimate."""
    from locfinder.traveltime.speeds import access_speed_mps
    for mode in ("walk", "bike", "drive"):
        assert max_speed_mps(mode) >= access_speed_mps(mode)
    assert max_speed_mps("drive") > 20 * 0.44704, "the model's fastest road is not a residential street"


def test_layer_wide_failures_are_unknown_everywhere_never_excluded():
    """A metro with no groceries is a data defect, not a fact about the metro, so it may not
    exclude a single cell. S4.4 blocks publication instead."""
    for reason in st.LAYER_REASONS:
        s = Surface.layer_failure(mode="walk", engine="own-graph", target="grocery",
                                  aggregation=st.CATEGORY_COST_SELECTED, horizon_s=H, shape=(1,),
                                  reason=reason).validate()
        assert st.evaluate(crit(15 * 60.0), s)[0] == Outcome.UNKNOWN
        assert st.evaluate(crit(10 * H), s)[0] == Outcome.UNKNOWN


# ---------------------------------------------------------------- combining criteria

def test_one_known_failure_beats_any_number_of_unknowns():
    """Codex pass-7 C4. A cell definitely 50 minutes from work does not become a maybe because we
    are unsure about its walk to a grocery."""
    fail = np.array([Outcome.FAIL], dtype=np.int8)
    unknown = np.array([Outcome.UNKNOWN], dtype=np.int8)
    assert st.combine([fail, unknown, unknown])[0] == Verdict.EXCLUDED
    assert st.combine([unknown, fail])[0] == Verdict.EXCLUDED


def test_the_full_verdict_table():
    P, F, U = Outcome.PASS, Outcome.FAIL, Outcome.UNKNOWN
    rows = [
        ([P], Verdict.INCLUDED),
        ([F], Verdict.EXCLUDED),
        ([U], Verdict.UNKNOWN),
        ([P, P], Verdict.INCLUDED),
        ([P, F], Verdict.EXCLUDED),
        ([P, U], Verdict.UNKNOWN),
        ([F, U], Verdict.EXCLUDED),
        ([F, F], Verdict.EXCLUDED),
        ([U, U], Verdict.UNKNOWN),
        ([P, F, U], Verdict.EXCLUDED),
    ]
    for outcomes, expected in rows:
        got = st.combine([np.array([o], dtype=np.int8) for o in outcomes])[0]
        assert got == expected, f"{[Outcome(o).name for o in outcomes]} -> {Verdict(got).name}"


def test_no_criteria_excludes_nothing():
    assert st.combine([], shape=(3,)).tolist() == [Verdict.INCLUDED] * 3
    with pytest.raises(ValueError, match="explicit shape"):
        st.combine([])


def test_why_is_this_out_lists_every_failing_criterion_not_the_first():
    a = np.array([Outcome.FAIL, Outcome.PASS], dtype=np.int8)
    b = np.array([Outcome.FAIL, Outcome.FAIL], dtype=np.int8)
    f = st.failing([a, b])
    assert f.shape == (2, 2)
    assert f[:, 0].tolist() == [True, True], "both criteria fail at cell 0 and both are reported"
    assert f[:, 1].tolist() == [False, True]


# ---------------------------------------------------------------- per-anchor semantics (S0.3)

def test_a_category_minimum_cannot_answer_an_anchor_criterion():
    """`min(t_A, t_B)` asks whether *either* workplace is close enough. A two-earner household
    means both, which is two anchor criteria combined with AND -- a different query, and the type
    refuses the substitution rather than silently answering the wrong one."""
    cat = surface(Reason.OK, seconds=600.0, aggregation=st.CATEGORY_COST_SELECTED, target="workplaces")
    with pytest.raises(ValueError, match="anchor"):
        st.evaluate(crit(900.0, kind="anchor", target="workplaces"), cat)


def test_an_anchor_surface_cannot_answer_a_category_criterion():
    anchor = surface(Reason.OK, seconds=600.0, aggregation=st.SINGLE_ANCHOR, target="office-a")
    with pytest.raises(ValueError, match="category"):
        st.evaluate(crit(900.0, kind="category", target="office-a"), anchor)


def test_two_workplaces_mean_and_of_two_anchor_surfaces():
    """The cell is 10 minutes from office A and 40 from office B. 'Within 20 minutes of each'
    excludes it; a min-over-both surface would have included it."""
    a = surface(Reason.OK, seconds=600.0, aggregation=st.SINGLE_ANCHOR, target="office-a")
    b = surface(Reason.OK, seconds=2400.0, aggregation=st.SINGLE_ANCHOR, target="office-b")
    both = st.combine([
        st.evaluate(crit(1200.0, kind="anchor", target="office-a"), a),
        st.evaluate(crit(1200.0, kind="anchor", target="office-b"), b),
    ])
    assert both[0] == Verdict.EXCLUDED
    assert min(a.seconds[0], b.seconds[0]) <= 1200.0, "the either-workplace reading would pass"


def test_mode_and_target_mismatches_are_refused():
    s = surface(Reason.OK, seconds=600.0)
    with pytest.raises(ValueError, match="mode"):
        st.evaluate(crit(900.0, mode="drive"), s)
    with pytest.raises(ValueError, match="target"):
        st.evaluate(crit(900.0, target="park"), s)


def test_a_criterion_needs_a_positive_threshold_and_a_known_kind():
    with pytest.raises(ValueError, match="kind"):
        Criterion(label="t", mode="walk", target="grocery", kind="nearby", threshold_s=60.0)
    with pytest.raises(ValueError, match="threshold"):
        crit(0.0)


# ---------------------------------------------------------------- surface invariants

def test_a_finite_time_must_be_ok_and_an_ok_cell_must_have_a_finite_time():
    with pytest.raises(ValueError, match="finite"):
        surface(Reason.OFF_NETWORK, seconds=600.0, min_possible=1.0)
    with pytest.raises(ValueError, match="finite"):
        surface(Reason.OK, seconds=np.inf)


def test_an_ok_cell_past_the_horizon_means_the_cutoff_was_not_applied():
    with pytest.raises(ValueError, match="cutoff"):
        surface(Reason.OK, seconds=H + 1.0)


def test_nan_is_never_a_missing_value():
    with pytest.raises(ValueError, match="NaN"):
        surface(Reason.OK, seconds=float("nan"))


def test_a_layer_wide_reason_must_cover_every_cell():
    s = Surface(mode="walk", engine="own-graph", target="grocery", aggregation=st.CATEGORY_COST_SELECTED,
                horizon_s=H, seconds=np.array([np.inf, 60.0]),
                reason=np.array([int(Reason.NO_DESTINATIONS), int(Reason.OK)], dtype=np.int8),
                min_possible_s=np.zeros(2))
    with pytest.raises(ValueError, match="every cell"):
        s.validate()


def test_beyond_horizon_and_no_path_must_carry_their_bounds():
    with pytest.raises(ValueError, match="horizon exactly as their bound"):
        surface(Reason.BEYOND_HORIZON, min_possible=0.0)
    with pytest.raises(ValueError, match=r"\+inf as their lower bound"):
        surface(Reason.NO_PATH, min_possible=H)


def test_layer_failure_refuses_a_per_cell_reason():
    with pytest.raises(ValueError, match="per-cell reason"):
        Surface.layer_failure(mode="walk", engine="own-graph", target="grocery",
                              aggregation=st.CATEGORY_COST_SELECTED, horizon_s=H, shape=(1,),
                              reason=Reason.OFF_NETWORK)


# ---------------------------------------------------------------- the pipeline really produces them

def island_graph() -> nx.MultiDiGraph:
    """A mainland segment holding the destination, and a disconnected island 5 km east. Both are
    real roads in the graph; no edge joins them, so the island has no path at any budget."""
    G = nx.MultiDiGraph()
    coords = {"A": (0.0, 0.0), "B": (500.0, 0.0),          # mainland, destination at A
              "I": (5000.0, 0.0), "J": (5500.0, 0.0)}      # island
    for n, (x, y) in coords.items():
        G.add_node(n, x=x, y=y)
    for u, v in (("A", "B"), ("B", "A"), ("I", "J"), ("J", "I")):
        G.add_edge(u, v, length=500.0, highway="residential", oneway=False)
    G.graph["crs"] = "EPSG:32617"
    return G


def prepared_island(mode="walk"):
    G = add_travel_times(island_graph(), mode=mode)
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
    T = arrival_seconds_two_weight(cost_csr, time_csr, dest_idx=[index["A"]])
    D = arrival_seconds(cost_csr, dest_idx=[index["A"]])
    return EdgeIndex.from_graph(G, index), T, D, index


def provenance(xs, ys, *, mode="walk", horizon_s=H, max_access_m=200.0, engine="own-graph"):
    idx, T, D, _ = prepared_island(mode)
    reasons = st.node_reasons(T, st.ENGINES[engine], search_bounded=False)
    return cell_arrival_with_provenance(
        idx, T, np.asarray(xs), np.asarray(ys), mode=mode, max_access_m=max_access_m,
        horizon_s=horizon_s, node_reason=reasons, node_cost=D,
    )


def test_the_pipeline_produces_ok_with_the_same_seconds_as_before():
    """The provenance path must not change a single reported time."""
    from locfinder.traveltime.snap import cell_seconds_from_arrival
    idx, T, D, _ = prepared_island()
    xs, ys = np.array([250.0, 5250.0, 0.0]), np.array([10.0, 10.0, 900.0])
    before = cell_seconds_from_arrival(idx, T, xs, ys, mode="walk", max_access_m=200.0,
                                       node_cost=D, cutoff_s=H)
    secs, _, _ = provenance(xs, ys)
    assert np.array_equal(np.isfinite(before), np.isfinite(secs))
    assert np.allclose(before[np.isfinite(before)], secs[np.isfinite(secs)])


def test_the_pipeline_produces_off_network():
    secs, reason, lower = provenance([0.0], [900.0])    # 900 m north of the only road
    assert reason[0] == Reason.OFF_NETWORK
    assert math.isinf(secs[0])
    assert math.isclose(lower[0], 900.0 / max_speed_mps("walk"), rel_tol=1e-9)


def test_the_pipeline_produces_no_path_on_the_own_graph():
    """The own-graph search is unbounded on cost (`layer.py:38-39` pass no cutoff), so an infinite
    arrival time there really does mean no path exists in the built network."""
    secs, reason, lower = provenance([5250.0], [10.0])   # on the island
    assert reason[0] == Reason.NO_PATH
    assert math.isinf(secs[0]) and math.isinf(lower[0])


def test_the_same_cell_is_only_beyond_the_horizon_for_a_bounded_engine():
    """Same graph, same cell. Nothing about the world changed -- only which engine is entitled to
    claim exhaustiveness."""
    _, reason, lower = provenance([5250.0], [10.0], engine="valhalla-expansion")
    assert reason[0] == Reason.BEYOND_HORIZON
    assert lower[0] == H


def test_the_pipeline_produces_beyond_horizon_from_the_cutoff():
    secs, reason, lower = provenance([250.0], [10.0], horizon_s=60.0)  # ~180 s walk, 60 s budget
    assert reason[0] == Reason.BEYOND_HORIZON
    assert math.isinf(secs[0]) and lower[0] == 60.0


def test_every_per_cell_reason_is_produced_by_the_real_pipeline():
    """All four in one call, on one graph, through the function the layer builder will use."""
    secs, reason, _ = provenance([250.0, 5250.0, 0.0], [10.0, 10.0, 900.0], horizon_s=H)
    assert set(reason.tolist()) == {Reason.OK, Reason.NO_PATH, Reason.OFF_NETWORK}
    tight, r2, _ = provenance([250.0], [10.0], horizon_s=60.0)
    assert r2[0] == Reason.BEYOND_HORIZON
    assert set(st.PER_CELL_REASONS) == set(reason.tolist()) | {Reason(r2[0])}


def test_a_surface_built_from_the_pipeline_validates():
    """End to end: the producer's output satisfies the consumer's invariants. This is the check
    that would have caught `expansion.py` being wired to nothing."""
    secs, reason, lower = provenance([250.0, 5250.0, 0.0], [10.0, 10.0, 900.0])
    Surface(mode="walk", engine="own-graph", target="grocery", aggregation=st.CATEGORY_COST_SELECTED,
            horizon_s=H, seconds=secs, reason=reason, min_possible_s=lower).validate()


def test_an_off_network_cell_beyond_a_dead_destination_is_unknown_not_excluded():
    """A cell 900 m from the only road, with a 15-minute walk criterion: we do not know its time,
    and 900 m at walking pace is well inside 15 minutes, so the honest answer is unknown."""
    secs, reason, lower = provenance([0.0], [900.0])
    s = Surface(mode="walk", engine="own-graph", target="grocery", aggregation=st.CATEGORY_COST_SELECTED,
                horizon_s=H, seconds=secs, reason=reason, min_possible_s=lower).validate()
    assert st.evaluate(crit(15 * 60.0), s)[0] == Outcome.UNKNOWN
    assert st.combine([st.evaluate(crit(15 * 60.0), s)])[0] == Verdict.UNKNOWN


def test_the_off_network_bound_is_sound_against_the_time_we_would_have_reported():
    """The bound's whole job is to never exceed the truth, because an over-estimate used as a
    lower bound *excludes* cells that should be unknown.

    Tested directly rather than argued: compute the bound for cells that are off-network at a
    200 m access cap, then raise the cap so the same cells get a real time, and check the bound
    never exceeds it. Points are sampled all round the island fixture, including far outside it.
    """
    rng = np.random.default_rng(20261104)
    xs = rng.uniform(-1500.0, 7000.0, 4000)
    ys = rng.uniform(-1500.0, 1500.0, 4000)

    _, tight_reason, bound = provenance(xs, ys, max_access_m=200.0)
    loose_secs, _, _ = provenance(xs, ys, max_access_m=10_000.0)

    off = tight_reason == Reason.OFF_NETWORK
    comparable = off & np.isfinite(loose_secs)
    assert comparable.sum() > 100, f"only {int(comparable.sum())} comparable cells"
    assert (bound[comparable] <= loose_secs[comparable] + 1e-9).all(), (
        "the bound exceeded the time the pipeline reports once the cell is on-network"
    )
    # and it is not a vacuous bound: on a 900 m-off cell it is minutes, not zero
    assert bound[comparable].max() > 60.0


# ---------------------------------------------------------------- Codex pass-8 regressions

def test_a_bounded_call_on_our_own_graph_may_not_claim_no_path():
    """Pass-8 H1, reproduced. `arrival_seconds` accepts a cutoff and scipy's `limit` prunes the
    search, so a bounded call returns inf for nodes that are merely distant. Exhaustiveness is a
    property of the invocation, not of the engine name."""
    G = nx.MultiDiGraph()
    for n, (x, y) in {"P": (0.0, 0.0), "Q": (100.0, 0.0), "R": (200.0, 0.0)}.items():
        G.add_node(n, x=x, y=y)
    for u, v, t in (("P", "Q", 10.0), ("Q", "R", 200.0)):
        G.add_edge(u, v, travel_time=t, cost=t, length=100.0)
        G.add_edge(v, u, travel_time=t, cost=t, length=100.0)
    from locfinder.traveltime.csr import graph_to_csr
    csr, index = graph_to_csr(G)
    unbounded = arrival_seconds(csr, dest_idx=[index["R"]])
    bounded = arrival_seconds(csr, dest_idx=[index["R"]], cutoff_s=100.0)
    assert unbounded[index["P"]] == 210.0 and np.isinf(bounded[index["P"]])

    own = st.ENGINES["own-graph"]
    assert st.node_reasons(bounded, own, search_bounded=True)[index["P"]] == Reason.BEYOND_HORIZON
    assert st.node_reasons(unbounded, own, search_bounded=False)[index["P"]] == Reason.OK
    # and the keyword has no default, so the question cannot be skipped
    with pytest.raises(TypeError):
        st.node_reasons(bounded, own)


def test_the_production_builder_runs_the_node_search_unbounded():
    """The fix for H1 on the producer side: `layer.py`'s single-weight branch no longer passes a
    node cutoff, which is what makes its NO_PATH claim sound. Output is unchanged because a node
    past the horizon cannot yield a cell inside it."""
    import inspect

    from locfinder.traveltime import layer
    src = inspect.getsource(layer.build_layer_seconds)
    # the NODE search takes no cutoff ...
    assert "arrival_seconds(csr, dest_idx=dest_idx)" in src
    assert "arrival_seconds(csr, dest_idx=dest_idx, cutoff_s" not in src
    # ... while the CELL stage still applies one, after the access leg, which is the point
    assert "cutoff_s=cutoff_min * 60.0" in src


def test_a_category_surface_is_an_upper_bound_not_a_minimum_over_destinations():
    """Pass-8 H2, reproduced. The search picks the destination nearest by **cost** and reports that
    path's time, so a 20 s destination behind a penalised private edge is reported as the 100 s open
    one. The surface over-reports, which means category criteria can produce false exclusions."""
    from locfinder.traveltime.speeds import symmetrise
    G = nx.MultiDiGraph()
    for n, (x, y) in {"A": (0.0, 0.0), "C": (28.0, 0.0), "B": (168.0, 0.0)}.items():
        G.add_node(n, x=x, y=y)
    G.add_edge("C", "A", length=28.0, highway="residential", access="private")
    G.add_edge("C", "B", length=140.0, highway="residential")
    G = symmetrise(add_travel_times(G, mode="walk"))
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)

    alone = {n: arrival_seconds_two_weight(cost_csr, time_csr, dest_idx=[index[n]])[index["C"]]
             for n in ("A", "B")}
    assert alone["A"] == 20.0 and alone["B"] == 100.0

    category = arrival_seconds_two_weight(
        cost_csr, time_csr, dest_idx=[index["A"], index["B"]])[index["C"]]
    assert category == 100.0, "the cost-nearest destination wins, not the time-nearest"
    assert category > min(alone.values()), "so the surface is an UPPER bound on min over destinations"

    # the bracket: both sides are one Dijkstra, and they contain the honest answer
    time_min = arrival_seconds(time_csr, dest_idx=[index["A"], index["B"]])[index["C"]]
    assert time_min == 20.0
    assert time_min <= min(alone.values()) <= category

    # the name no longer claims otherwise
    assert st.CATEGORY_COST_SELECTED == "cost_selected_category"
    assert st.CATEGORY_TIME_MIN in st.CATEGORY_AGGREGATIONS


def test_a_layer_wide_failure_cannot_exclude_even_with_a_malformed_bound():
    """Pass-8 M1. `validate` used to accept a mixed layer array, and a positive lower bound on a
    layer-wide reason turned into an exclusion -- breaking the one guarantee the class makes."""
    bad_bound = Surface(
        mode="walk", engine="own-graph", target="grocery", aggregation=st.CATEGORY_COST_SELECTED,
        horizon_s=H, seconds=np.array([np.inf]),
        reason=np.array([int(Reason.NO_DESTINATIONS)], dtype=np.int8),
        min_possible_s=np.array([10 * H]))
    with pytest.raises(ValueError, match="lower bound must be exactly 0"):
        bad_bound.validate()
    # and even unvalidated input cannot exclude: the reason decides, not the array
    assert st.evaluate(crit(60.0), bad_bound)[0] == Outcome.UNKNOWN

    mixed = Surface(
        mode="walk", engine="own-graph", target="grocery", aggregation=st.CATEGORY_COST_SELECTED,
        horizon_s=H, seconds=np.array([np.inf, np.inf]),
        reason=np.array([int(Reason.NO_DESTINATIONS), int(Reason.SOURCE_MISSING)], dtype=np.int8),
        min_possible_s=np.zeros(2))
    with pytest.raises(ValueError, match="uniform over every cell"):
        mixed.validate()


def test_an_eligibility_answer_never_depends_on_an_approximate_bound():
    """Pass-8 M2. `np.allclose` admitted ~0.07 s of error at H = 7200 s, and the outcome was read
    from the stored bound while recomputation was read from the horizon, so one cell could be both
    FAIL and marked answerable."""
    overstated = Surface(
        mode="walk", engine="own-graph", target="grocery", aggregation=st.CATEGORY_COST_SELECTED,
        horizon_s=H, seconds=np.array([np.inf]),
        reason=np.array([int(Reason.BEYOND_HORIZON)], dtype=np.int8),
        min_possible_s=np.array([H + 0.05]))
    with pytest.raises(ValueError, match="exactly"):
        overstated.validate()
    c = crit(H + 0.025)
    assert st.evaluate(c, overstated)[0] == Outcome.UNKNOWN, "decided by the horizon, not the bound"
    assert st.needs_recomputation(c, overstated)[0], "and consistently so"


def test_an_infinite_threshold_is_refused_and_no_path_fails_regardless():
    """Pass-8 L1. `inf > inf` is false, so an infinite threshold made NO_PATH unknown."""
    with pytest.raises(ValueError, match="finite"):
        crit(float("inf"))
    # the rule no longer depends on that check
    s = surface(Reason.NO_PATH, min_possible=np.inf)
    forged = Criterion.__new__(Criterion)
    object.__setattr__(forged, "label", "t")
    object.__setattr__(forged, "mode", "walk")
    object.__setattr__(forged, "target", "grocery")
    object.__setattr__(forged, "kind", "category")
    object.__setattr__(forged, "threshold_s", float("inf"))
    assert st.evaluate(forged, s)[0] == Outcome.FAIL


def test_the_builder_uses_the_engine_it_is_given_not_one_derived_from_the_mode():
    """`engine_for("drive")` is valhalla-expansion, so deriving the engine inside the builder would
    misdescribe a drive layer built from our own graph. H1's point is that the claim must match the
    actual call, and that applies to the engine as much as to the cutoff."""
    import inspect

    from locfinder.traveltime import layer
    src = inspect.getsource(layer.build_layer_surface)
    assert "ENGINES[engine]" in src
    assert "engine_for(mode)" not in src


def test_the_builder_distinguishes_an_empty_category_from_unsnappable_destinations():
    """Both look identical from a cell's point of view and have different causes; both are unknown
    everywhere and both block publication (S4.4)."""
    from locfinder.grid import GridSpec
    from locfinder.traveltime import layer

    grid = GridSpec(crs="EPSG:32617", x_min=0.0, y_max=100.0, cell_m=50.0, ncols=2, nrows=2)
    G = add_travel_times(island_graph(), mode="walk")
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)

    empty = layer.build_layer_surface(G, (cost_csr, time_csr), index, grid, dest_idx=[],
                                      mode="walk", target="grocery", places_selected=0)
    assert set(np.unique(empty.reason)) == {Reason.NO_DESTINATIONS}

    unsnappable = layer.build_layer_surface(G, (cost_csr, time_csr), index, grid, dest_idx=[],
                                            mode="walk", target="grocery", places_selected=12)
    assert set(np.unique(unsnappable.reason)) == {Reason.NO_ROUTABLE_DESTINATIONS}

    for s in (empty, unsnappable):
        assert s.shape == (2, 2), 'the layer-failure surface takes the grid shape'
        assert (st.evaluate(crit(15 * 60.0), s) == Outcome.UNKNOWN).all()
