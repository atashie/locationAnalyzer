"""Which destination did we route this household to?

The layer has always computed this and thrown it away: `scipy`'s `min_only` search returns a
`sources` array beside the distances, and `arrival_seconds_two_weight` discarded it as `_sources`.
So every published number meant "ten minutes to *some* grocery" and the owner's walked audit could
not check it -- a walk to a shop we did not choose tests the walker's journey, not ours.

These tests pin the two things the recovery can plausibly get wrong:

* `sources` is a **node id**, not a position in `dest_idx`. Those coincide whenever the
  destinations happen to be nodes 0..k-1, which is exactly the shape a small fixture falls into.
* the destination must be the **cost**-selected one, not the time-nearest one. Getting this wrong
  would send the owner to the quicker shop while the layer's seconds describe the cheaper route,
  and the discrepancy would read as a product defect.
"""
import math

import networkx as nx
import numpy as np
import pytest

from locfinder.traveltime.arrival import (
    arrival_seconds_two_weight,
    arrival_with_selected_destination,
)
from locfinder.traveltime.csr import graph_to_cost_time_csr
from locfinder.traveltime.snap import EdgeIndex, cell_selected_destination, cell_seconds_from_arrival

PEN = 450.0


def edge(G, u, v, *, time, cost=None, both=True):
    G.add_edge(u, v, travel_time=time, cost=time if cost is None else cost)
    if both:
        G.add_edge(v, u, travel_time=time, cost=time if cost is None else cost)


# --------------------------------------------------------------------------------------------
# the node-id / position distinction
# --------------------------------------------------------------------------------------------

def test_selected_is_a_node_id_not_a_position_in_dest_idx():
    """The defect this is built to catch, and it is invisible on a fixture whose destinations are
    the first nodes: with destinations at node ids 3 and 4, a position-returning implementation
    would report 0 and 1, which are real nodes elsewhere in the graph."""
    G = nx.MultiDiGraph()
    # chain A - B - C - shopFar, plus D - shopNear, so two separate destination nodes
    edge(G, "A", "B", time=10.0)
    edge(G, "B", "C", time=10.0)
    edge(G, "C", "shopFar", time=10.0)
    edge(G, "D", "shopNear", time=10.0)
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
    dest = [index["shopFar"], index["shopNear"]]
    assert min(dest) >= 2, "fixture must not let node ids coincide with positions 0 and 1"

    seconds, selected = arrival_with_selected_destination(cost_csr, time_csr, dest_idx=dest)

    assert selected[index["A"]] == index["shopFar"]
    assert selected[index["D"]] == index["shopNear"]
    # and the ids are not positions
    assert selected[index["A"]] != 0
    assert selected[index["D"]] != 1


def test_a_destination_selects_itself():
    G = nx.MultiDiGraph()
    edge(G, "A", "shop", time=10.0)
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
    _s, selected = arrival_with_selected_destination(
        cost_csr, time_csr, dest_idx=[index["shop"]])
    assert selected[index["shop"]] == index["shop"]


# --------------------------------------------------------------------------------------------
# cost selection, which is the whole reason the two-weight search exists
# --------------------------------------------------------------------------------------------

def test_the_destination_follows_cost_not_time():
    """Two shops. The time-nearest one is up a private drive; the cost-selected one is further in
    real seconds. The reported destination must be the cost-selected shop, because that is the
    journey whose seconds we publish.

    If this returned the time-nearest shop, the audit sheet would send the owner to `quick` while
    the printed 200 s describes the walk to `open`.
    """
    G = nx.MultiDiGraph()
    edge(G, "A", "quick", time=60.0, cost=60.0 + PEN)   # 60 s real, expensive to choose
    edge(G, "A", "M", time=100.0)
    edge(G, "M", "open", time=100.0)                     # 200 s real, cheap
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
    dest = [index["quick"], index["open"]]

    seconds, selected = arrival_with_selected_destination(cost_csr, time_csr, dest_idx=dest)
    a = index["A"]

    assert seconds[a] == pytest.approx(200.0), "reports the cost-selected route's real time"
    assert selected[a] == index["open"], "and names the shop that route actually reaches"
    assert selected[a] != index["quick"]


def test_the_seconds_are_unchanged_by_the_refactor():
    """`arrival_seconds_two_weight` now delegates. Its numbers must be identical, including the
    penalised and unreachable cases."""
    G = nx.MultiDiGraph()
    edge(G, "A", "B", time=60.0, cost=60.0 + PEN)
    edge(G, "B", "C", time=30.0)
    G.add_node("island", x=0.0, y=0.0)
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
    dest = [index["C"]]

    direct = arrival_seconds_two_weight(cost_csr, time_csr, dest_idx=dest)
    paired, _sel = arrival_with_selected_destination(cost_csr, time_csr, dest_idx=dest)

    assert np.array_equal(direct, paired, equal_nan=True)
    assert direct[index["A"]] == pytest.approx(90.0)


# --------------------------------------------------------------------------------------------
# the record must agree with the seconds it explains
# --------------------------------------------------------------------------------------------

def test_an_unreachable_node_has_no_destination():
    G = nx.MultiDiGraph()
    edge(G, "A", "shop", time=10.0)
    G.add_node("island", x=0.0, y=0.0)
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
    seconds, selected = arrival_with_selected_destination(
        cost_csr, time_csr, dest_idx=[index["shop"]])
    i = index["island"]
    assert not math.isfinite(seconds[i])
    assert selected[i] == -1, "no reachable destination means no destination recorded"


def test_the_cutoff_removes_the_destination_too():
    """A node cut by the horizon must not keep a destination it cannot reach in the budget --
    otherwise a sheet could print a shop beside an UNKNOWN verdict."""
    G = nx.MultiDiGraph()
    edge(G, "A", "shop", time=600.0)
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
    a = index["A"]

    uncut, sel_uncut = arrival_with_selected_destination(
        cost_csr, time_csr, dest_idx=[index["shop"]])
    assert math.isfinite(uncut[a]) and sel_uncut[a] == index["shop"]

    cut, sel_cut = arrival_with_selected_destination(
        cost_csr, time_csr, dest_idx=[index["shop"]], cutoff_s=300.0)
    assert not math.isfinite(cut[a])
    assert sel_cut[a] == -1


def test_every_finite_second_has_a_destination_and_every_infinite_one_does_not():
    """The invariant stated as an invariant, over a graph with all three outcomes present."""
    G = nx.MultiDiGraph()
    edge(G, "A", "B", time=10.0)
    edge(G, "B", "shop", time=10.0)
    edge(G, "far", "shop", time=5000.0)
    G.add_node("island", x=0.0, y=0.0)
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
    seconds, selected = arrival_with_selected_destination(
        cost_csr, time_csr, dest_idx=[index["shop"]], cutoff_s=1800.0)

    finite = np.isfinite(seconds)
    assert finite.any() and (~finite).any(), "fixture must exercise both sides"
    assert (selected[finite] >= 0).all()
    assert (selected[~finite] == -1).all()


def test_no_destinations_means_no_selection():
    G = nx.MultiDiGraph()
    edge(G, "A", "B", time=10.0)
    cost_csr, time_csr, _index = graph_to_cost_time_csr(G)
    seconds, selected = arrival_with_selected_destination(cost_csr, time_csr, dest_idx=[])
    assert not np.isfinite(seconds).any()
    assert (selected == -1).all()
    assert selected.shape == seconds.shape


# --------------------------------------------------------------------------------------------
# from a query point, through the snapped edge, to the shop
# --------------------------------------------------------------------------------------------

def snap_fixture() -> nx.MultiDiGraph:
    """A 100 m east-west road S--E with **a different shop behind each endpoint**.

        shopS --10s-- S =====100 m / 100 s road===== E --10s-- shopE

    The separate shops are the point. My first version of this fixture hung a penalised shop off
    E, which made `T[E]` route back through S to `shopS`: both endpoints then selected the same
    shop, and flipping the chosen endpoint from `e_idx` to `s_idx` was invisible to every test
    here. A fixture has to make the branch choice *observable*, not merely exercise it.
    """
    G = nx.MultiDiGraph()
    coords = {"S": (0.0, 0.0), "E": (100.0, 0.0),
              "shopS": (0.0, -50.0), "shopE": (100.0, -50.0)}
    for n, (x, y) in coords.items():
        G.add_node(n, x=x, y=y)
    edge(G, "S", "E", time=100.0)
    edge(G, "S", "shopS", time=10.0)
    edge(G, "E", "shopE", time=10.0)
    return G


def snap_inputs(G):
    from locfinder.traveltime.arrival import arrival_seconds
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
    dest = [index["shopS"], index["shopE"]]
    T, selected = arrival_with_selected_destination(cost_csr, time_csr, dest_idx=dest)
    node_cost = np.asarray(arrival_seconds(cost_csr, dest_idx=dest))
    return index, dest, T, selected, node_cost, EdgeIndex.from_graph(G, index)


def test_the_two_endpoints_select_different_shops():
    """Guards the fixture itself. If this ever fails, the branch tests below have stopped being
    able to detect a flipped endpoint and are passing for the wrong reason."""
    G = snap_fixture()
    index, _dest, T, selected, _nc, _eidx = snap_inputs(G)
    assert selected[index["S"]] == index["shopS"]
    assert selected[index["E"]] == index["shopE"]
    assert T[index["S"]] == pytest.approx(10.0)
    assert T[index["E"]] == pytest.approx(10.0)


@pytest.mark.parametrize("x_m, expect", [(10.0, "shopS"), (90.0, "shopE")])
def test_the_endpoint_whose_time_was_reported_supplies_the_shop(x_m, expect):
    """A point 10 m from S reaches shopS in 10+10 = 20 s, and going via E would take 90+10 = 100 s;
    90 m along, the two swap. So the shop named must change with the side of the road the point
    is on -- which is what makes 'the endpoint we used' different from 'either endpoint'.
    """
    G = snap_fixture()
    index, _dest, T, selected, node_cost, eidx = snap_inputs(G)
    xs, ys = np.array([x_m]), np.array([0.0])
    kw = dict(mode="walk", max_access_m=200.0, node_cost=node_cost)

    secs = cell_seconds_from_arrival(eidx, T, xs, ys, **kw)
    got = cell_selected_destination(eidx, T, xs, ys, selected=selected, **kw)

    assert secs[0] == pytest.approx(min(x_m, 100.0 - x_m) + 10.0), "the nearer endpoint's journey"
    assert got[0] == index[expect]


@pytest.mark.parametrize("x_m, expect", [(10.0, "shopS"), (90.0, "shopE")])
def test_the_time_fallback_branch_also_names_the_right_shop(x_m, expect):
    """With `node_cost` omitted the branch is chosen on time instead, a separate code path that
    also had to learn which endpoint it picked."""
    G = snap_fixture()
    index, _dest, T, selected, _nc, eidx = snap_inputs(G)
    xs, ys = np.array([x_m]), np.array([0.0])
    got = cell_selected_destination(eidx, T, xs, ys, mode="walk", max_access_m=200.0,
                                    selected=selected)
    assert got[0] == index[expect]


def test_an_off_network_point_has_no_destination():
    G = snap_fixture()
    _index, _dest, T, selected, node_cost, eidx = snap_inputs(G)
    xs, ys = np.array([50.0]), np.array([5000.0])    # 5 km from the road
    got = cell_selected_destination(eidx, T, xs, ys, mode="walk", max_access_m=200.0,
                                    selected=selected, node_cost=node_cost)
    assert got[0] == -1


def test_the_destination_is_absent_wherever_the_seconds_are():
    """Pointwise agreement between the two public calls, over a spread of query points including
    off-network ones. Stated as an invariant rather than a handful of cases."""
    G = snap_fixture()
    _index, dest, T, selected, node_cost, eidx = snap_inputs(G)

    xs, ys = np.meshgrid(np.linspace(-300.0, 400.0, 15), np.linspace(-300.0, 300.0, 15))
    kw = dict(mode="walk", max_access_m=200.0, node_cost=node_cost)
    secs = cell_seconds_from_arrival(eidx, T, xs, ys, **kw)
    got = cell_selected_destination(eidx, T, xs, ys, selected=selected, **kw)

    assert got.shape == secs.shape == xs.shape
    finite = np.isfinite(secs)
    assert finite.any() and (~finite).any(), "the sweep must cover both sides"
    assert (got[finite] >= 0).all(), "a published time must name a destination"
    assert (got[~finite] == -1).all(), "no published time, no destination"
    assert set(np.unique(got[finite]).tolist()) <= set(dest)


def test_a_mismatched_selected_array_is_refused():
    """Passing `selected` from a different graph would silently index the wrong nodes."""
    G = snap_fixture()
    _index, _dest, T, selected, _nc, eidx = snap_inputs(G)
    with pytest.raises(ValueError, match="selected has shape"):
        cell_selected_destination(eidx, T, np.array([10.0]), np.array([0.0]),
                                  mode="walk", max_access_m=200.0, selected=selected[:-1])


def test_chosen_idx_is_absent_where_no_branch_was_available():
    """Reaches into `_snap_network` deliberately.

    `_Snapped.chosen_idx` documents itself as "-1 if neither", and that promise is **not**
    observable through either public entry point: an infinite `network` forces an infinite total,
    so the public masks always fire first and deleting this guard changes no published answer. A
    mutation run showed exactly that -- the guard survived every test while being, from outside,
    dead code.

    It is kept rather than deleted because the field is part of the helper's stated contract and
    the next caller may be a provenance reader that does not recompute finiteness. A documented
    invariant with no test is the thing that disappears the moment someone simplifies it, so the
    test goes where the invariant lives.
    """
    from locfinder.traveltime.snap import _snap_network

    G = nx.MultiDiGraph()
    for n, (x, y) in {"S": (0.0, 0.0), "E": (100.0, 0.0), "shopS": (0.0, -50.0),
                      "orphanA": (0.0, 5000.0), "orphanB": (100.0, 5000.0)}.items():
        G.add_node(n, x=x, y=y)
    edge(G, "S", "E", time=100.0)
    edge(G, "S", "shopS", time=10.0)
    edge(G, "orphanA", "orphanB", time=50.0)      # a road no destination can reach
    cost_csr, time_csr, index = graph_to_cost_time_csr(G)
    T, _selected = arrival_with_selected_destination(
        cost_csr, time_csr, dest_idx=[index["shopS"]])
    eidx = EdgeIndex.from_graph(G, index)

    # directly on the orphan road: access is 0 m, but no branch leads anywhere
    snapped = _snap_network(eidx, T, np.array([50.0]), np.array([5000.0]), node_cost=None)
    assert snapped.access_m[0] == pytest.approx(0.0), "fixture must put the point ON the road"
    assert not math.isfinite(snapped.network[0])
    assert snapped.chosen_idx[0] == -1, "no available branch means no chosen endpoint"

    # and on the reachable road the field is a real endpoint
    ok = _snap_network(eidx, T, np.array([10.0]), np.array([0.0]), node_cost=None)
    assert ok.chosen_idx[0] in (index["S"], index["E"])
