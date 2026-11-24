"""Who may ignore a one-way street, decided in one place.

`symmetrise` adds a reverse edge for every road that lacks one, and its own docstring says it is
*"ONLY valid for walk graphs: pedestrians ignore one-way restrictions; cyclists and drivers do
not."* That rule lived in comments at 26 call sites in three different spellings, and at two of
them -- `persist_selected_destination.py` and `audit_destination_truth.py` -- the call was
unconditional, safe only because a module constant happened to read `"walk"`.

Nothing was wrong while every one of those scripts built a walk layer. The moment one of them
takes a `--mode drive`, an unconditional call makes every one-way street in the Triangle
two-way and quietly shortens drive times -- with no error, no warning, and a plausible-looking
raster at the end of it.

So the rule gets a function and the function gets a test, which is the project's standing
instruction for a rule that has already failed to hold on its own.
"""
import networkx as nx
import pytest

from locfinder.traveltime.speeds import symmetrise, symmetrise_for_mode


def one_way() -> nx.MultiDiGraph:
    """Two nodes, one road, one direction. `_physical_key` reads `osmid` and `length`, so a
    fixture without them would dedupe on `(None, 0.0)` and test nothing."""
    g = nx.MultiDiGraph()
    g.add_node(1, x=0.0, y=0.0)
    g.add_node(2, x=100.0, y=0.0)
    g.add_edge(1, 2, osmid=4242, length=100.0, travel_time_s=72.0)
    return g


def test_a_pedestrian_may_walk_the_wrong_way_up_a_one_way_street():
    g = symmetrise_for_mode(one_way(), "walk")
    assert g.has_edge(2, 1), "the walk graph lost the reverse of a one-way road"
    assert g.number_of_edges() == 2


@pytest.mark.parametrize("mode", ["drive", "bike"])
def test_a_driver_and_a_cyclist_may_not(mode):
    """The failure this prevents is silent. A drive graph with every one-way road reversed still
    produces a complete, plausible raster -- with times that are too short, and nothing in the
    artifact saying so."""
    g = symmetrise_for_mode(one_way(), mode)
    assert not g.has_edge(2, 1), f"{mode} gained a reverse edge on a one-way road"
    assert g.number_of_edges() == 1


def test_it_is_the_same_work_as_calling_symmetrise_directly_for_a_walk():
    """The wrapper must not become a second implementation that drifts from the first."""
    direct = symmetrise(one_way())
    through = symmetrise_for_mode(one_way(), "walk")
    assert sorted(direct.edges()) == sorted(through.edges())


def test_an_unknown_mode_is_refused_rather_than_guessed():
    """Defaulting an unrecognised mode either way is a silent decision about one-way streets.
    `"walking"`, `"car"` and `"Drive"` are all plausible typos at a call site."""
    for bad in ["walking", "car", "Drive", "", "foot"]:
        with pytest.raises(ValueError, match="mode"):
            symmetrise_for_mode(one_way(), bad)
