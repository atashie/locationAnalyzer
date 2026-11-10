"""The road-graph cache has to say which file it describes, and the rules have to say what they read.

Three instances of one failure:

* `spikes/g1_own_graph_layer.load_graph` returned the 670 MB graphml cache whenever the file
  existed. Adding a tag to `EXTRA_WAY_TAGS` therefore changed nothing until somebody deleted the
  cache by hand, and no script said so -- every measurement would have run on the old graph and
  agreed with itself.
* `access.classify_access` consults `vehicle` for the drive and bike modes, and `vehicle` was never
  in `EXTRA_WAY_TAGS` nor in osmnx's defaults, so the extract never carried it and that branch
  could not fire. 98 ways in the Triangle extract are tagged `vehicle`, 88 of them `vehicle=no`.
  A rule that reads a tag the extract drops is not a conservative rule; it is a dead one.
* **And the first fix had the same shape as the bug.** The manifest declared a tag set and nothing
  said which graph it described, so Codex pass 35 wrote a valid pair, swapped in a graph lacking
  `vehicle`, and `load_roads_graph` accepted it. A claim about a file that is not bound to the file
  establishes nothing. The manifest now records the graphml's size and sha256 and both are checked.

The shared shape is a claim about data that nothing compared with the data. These tests check each
half: that a cache cannot be reused on trust, that reuse is refused *before* the graph is read, and
that every tag a rule consults is one extraction keeps.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from locfinder.traveltime import access, speeds

_PATH = Path(__file__).resolve().parents[1] / "spikes" / "_common.py"
_SPEC = importlib.util.spec_from_file_location("spikes_common", _PATH)
common = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(common)

REQUIRED = common.graph_cache_requirements()["required_way_tags"]
GRAPHML_HEAD = """<?xml version='1.0' encoding='utf-8'?>
<graphml xmlns="http://graphml.graphdrawing.org/xmlns">
{keys}
  <graph edgedefault="directed" id="G" />
</graphml>
"""


def a_graph(tmp_path: Path, *, declares=None, name: str = "roads.graphml",
            filler: str = "") -> Path:
    """A file shaped like an osmnx graphml: edge key declarations and nothing else that matters."""
    tags = sorted(set(REQUIRED if declares is None else declares))
    keys = "\n".join(f'  <key id="d{i}" for="edge" attr.name="{t}" attr.type="string" />'
                     for i, t in enumerate(tags))
    path = tmp_path / name
    path.write_text(GRAPHML_HEAD.format(keys=keys) + filler, encoding="utf-8")
    return path


def a_pair(tmp_path: Path, **kw) -> tuple[Path, dict]:
    """A graph and the manifest that describes it, both valid."""
    graph = a_graph(tmp_path, **kw)
    common.write_graph_cache_manifest(graph)
    return graph, common.read_graph_cache_manifest(graph)


class Recorder:
    """Stands in for `ox.load_graphml` and counts calls.

    The first version of the before-reading test monkeypatched a function that raised. That catches
    an unsuppressed premature call and nothing else: an implementation that called, swallowed the
    exception and then validated passed it (Codex pass 35). Counting is the assertion that was
    meant.
    """

    def __init__(self) -> None:
        self.calls: list[Path] = []

    def __call__(self, path, **kw):
        self.calls.append(Path(path))
        return ("loaded", Path(path))


@pytest.fixture
def recorder(monkeypatch):
    import osmnx as ox

    rec = Recorder()
    monkeypatch.setattr(ox, "load_graphml", rec)
    return rec


# ---------------------------------------------------------------- the declared tag set
def test_a_cache_with_no_manifest_cannot_be_reused(tmp_path):
    graph = a_graph(tmp_path)
    why = common.graph_cache_complaint(None, graph)
    assert why is not None and "unknown" in why
    for tag in REQUIRED:
        assert tag in why, "the complaint should name what the rules need"


@pytest.mark.parametrize("dropped", REQUIRED)
def test_a_cache_missing_any_required_tag_is_rejected_by_name(tmp_path, dropped):
    """Parameterised over the whole required set, not over `surface` alone: a guard that rejects
    one named tag and waves every other through passed the single-tag version of this test."""
    graph, manifest = a_pair(tmp_path)
    manifest["way_tags"] = [t for t in manifest["way_tags"] if t != dropped]
    why = common.graph_cache_complaint(manifest, graph)
    assert why is not None and dropped in why


def test_a_matching_cache_is_accepted(tmp_path):
    graph, manifest = a_pair(tmp_path)
    assert common.graph_cache_complaint(manifest, graph) is None


def test_a_cache_parsed_with_more_tags_than_we_need_is_accepted(tmp_path):
    """Asymmetric on purpose: a superset carries everything the rules ask for."""
    graph, manifest = a_pair(tmp_path)
    manifest["way_tags"] = sorted(manifest["way_tags"] + ["tracktype"])
    assert common.graph_cache_complaint(manifest, graph) is None


def test_a_cache_built_from_a_different_source_file_is_rejected(tmp_path):
    graph, manifest = a_pair(tmp_path)
    manifest["source"] = "some-other-roads.osm"
    why = common.graph_cache_complaint(manifest, graph)
    assert why is not None and "some-other-roads.osm" in why


def test_a_cache_parsed_with_different_options_is_rejected(tmp_path):
    graph, manifest = a_pair(tmp_path)
    manifest["parse"] = {"simplify": False, "retain_all": True}
    why = common.graph_cache_complaint(manifest, graph)
    assert why is not None and "simplify" in why


# ---------------------------------------------------------------- binding to the file
def test_a_manifest_not_bound_to_a_file_decides_nothing(tmp_path):
    _, manifest = a_pair(tmp_path)
    why = common.graph_cache_complaint(manifest)
    assert why is not None and "not bound" in why


def test_swapping_the_graph_under_a_valid_manifest_is_rejected(tmp_path):
    """Codex pass 35's counterexample, which the first version of this guard accepted.

    The manifest stays valid and complete; only the graphml is replaced, with one that does not
    carry `vehicle`. Nothing in the tag set, the source or the parse options can see that.
    """
    graph, manifest = a_pair(tmp_path)
    swapped = [t for t in REQUIRED if t != "vehicle"]
    graph.write_text(a_graph(tmp_path, declares=swapped, name="other.graphml")
                     .read_text(encoding="utf-8"), encoding="utf-8")
    why = common.graph_cache_complaint(manifest, graph)
    assert why is not None
    assert "different file" in why or "bytes" in why


def test_a_graph_of_a_different_length_is_rejected_without_hashing(tmp_path):
    graph, manifest = a_pair(tmp_path)
    graph.write_text(graph.read_text(encoding="utf-8") + "<!-- one more comment -->",
                     encoding="utf-8")
    why = common.graph_cache_complaint(manifest, graph)
    assert why is not None and "bytes" in why


def test_a_graph_of_the_same_length_but_different_bytes_is_rejected(tmp_path):
    """Only the sha256 can see this, and nothing else in this file could.

    Every other swap test changes the file's length too, so an implementation that checked the size
    and ignored the digest passed all of them -- `scripts/mutate_graph_cache_guard.py` found that
    mutation surviving eleven tests.
    """
    graph, manifest = a_pair(tmp_path, filler="<!-- aaaa -->")
    graph.write_text(graph.read_text(encoding="utf-8").replace("<!-- aaaa -->", "<!-- bbbb -->"),
                     encoding="utf-8")
    assert graph.stat().st_size == manifest["graphml_bytes"], "the point is an equal size"
    why = common.graph_cache_complaint(manifest, graph)
    assert why is not None and "different file" in why


def test_load_refuses_an_equal_length_swap_without_reading_it(tmp_path, recorder):
    graph, _ = a_pair(tmp_path, filler="<!-- aaaa -->")
    graph.write_text(graph.read_text(encoding="utf-8").replace("<!-- aaaa -->", "<!-- bbbb -->"),
                     encoding="utf-8")
    with pytest.raises(SystemExit):
        common.load_roads_graph(graph)
    assert recorder.calls == []


def test_the_same_bytes_at_a_different_path_still_match(tmp_path):
    """The binding is to content, not to location: a moved or copied cache is still that cache."""
    graph, manifest = a_pair(tmp_path)
    moved = tmp_path / "elsewhere.graphml"
    moved.write_bytes(graph.read_bytes())
    assert common.graph_cache_complaint(manifest, moved) is None


# ---------------------------------------------------------------- the writer
def test_the_writer_refuses_a_graph_that_does_not_declare_an_added_tag(tmp_path):
    """`EXTRA_WAY_TAGS` are the tags we added deliberately. A graph that does not carry one is
    evidence the addition did nothing, which is the whole failure this guard exists for."""
    graph = a_graph(tmp_path, declares=[t for t in REQUIRED if t != "surface"])
    with pytest.raises(SystemExit) as e:
        common.write_graph_cache_manifest(graph)
    assert "surface" in str(e.value)


def test_the_writer_accepts_an_added_tag_the_parser_says_is_absent_from_the_data(tmp_path):
    """Only the process that parsed can tell "not retained" from "nothing had it", so it has to
    say which. A re-stamp of a file it did not parse cannot make that claim."""
    graph = a_graph(tmp_path, declares=[t for t in REQUIRED if t != "surface"])
    path = common.write_graph_cache_manifest(graph, requested_but_absent=["surface"])
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored["way_tags_requested_but_absent"] == ["surface"]
    assert common.graph_cache_complaint(stored, graph) is None


def test_the_writer_does_not_require_osmnx_defaults_to_be_declared(tmp_path):
    """`landuse` is an osmnx default and no highway way in the Triangle carries it, so requiring
    every default to be declared would refuse every real graph."""
    graph = a_graph(tmp_path, declares=[t for t in REQUIRED if t != "landuse"])
    path = common.write_graph_cache_manifest(graph)
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert "landuse" in stored["way_tags_required_but_not_declared"]
    assert common.graph_cache_complaint(stored, graph) is None


def test_what_the_writer_writes_the_checker_accepts(tmp_path):
    graph, manifest = a_pair(tmp_path)
    assert (tmp_path / "roads.tags.json").exists()
    assert common.graph_cache_complaint(manifest, graph) is None
    assert manifest["graphml_bytes"] == graph.stat().st_size


def test_the_declared_attribute_reader_sees_edge_keys_only(tmp_path):
    graph = tmp_path / "roads.graphml"
    graph.write_text(
        '<graphml>\n'
        '  <key id="d0" for="edge" attr.name="surface" attr.type="string" />\n'
        '  <key id="d1" for="node" attr.name="railway" attr.type="string" />\n'
        '</graphml>\n', encoding="utf-8")
    assert common.graph_declared_edge_attrs(graph) == {"surface"}


# ---------------------------------------------------------------- the load path
def test_load_refuses_a_missing_cache_and_says_how_to_build_one(tmp_path, recorder):
    with pytest.raises(SystemExit) as e:
        common.load_roads_graph(tmp_path / "absent.graphml")
    assert "g1_own_graph_layer" in str(e.value)
    assert recorder.calls == []


def test_load_refuses_a_stale_cache_without_reading_the_graph(tmp_path, recorder):
    """The refusal has to come first. Loading 695 MB and *then* complaining is not a guard, and
    neither is loading, swallowing the error, and then complaining."""
    graph, _ = a_pair(tmp_path)
    (tmp_path / "roads.tags.json").write_text(json.dumps(
        {"way_tags": ["foot"], "source": common.ROADS_XML.name}), encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        common.load_roads_graph(graph)
    assert "stale" in str(e.value)
    assert recorder.calls == [], "no read may happen on a refusal, suppressed or not"


def test_load_refuses_a_swapped_graph_without_reading_it(tmp_path, recorder):
    graph, _ = a_pair(tmp_path)
    graph.write_text(graph.read_text(encoding="utf-8") + "<!-- swapped -->", encoding="utf-8")
    with pytest.raises(SystemExit):
        common.load_roads_graph(graph)
    assert recorder.calls == []


def test_load_reads_the_graph_exactly_once_when_the_manifest_is_satisfied(tmp_path, recorder):
    """The companion to the refusals: a satisfied manifest must not block a real load, and must not
    provoke a second one either."""
    graph, _ = a_pair(tmp_path)
    assert common.load_roads_graph(graph) == ("loaded", graph)
    assert recorder.calls == [graph]


# ---------------------------------------------------------------- the rules and the extract
def test_every_tag_the_access_rules_consult_is_one_extraction_keeps():
    """This is the test that found `vehicle` missing. `_MODE_TAG_ORDER` is the authority on which
    tags `classify_access` reads, so the invariant is derived from it rather than retyped.

    Scope: OSM way tags read by the access and speed rules. It does **not** cover attributes osmnx
    derives (`osmid`, `length`, `geometry`, node coordinates) or the expansion adapter's response
    fields, and it cannot say how a retained tag was interpreted (pass 35).
    """
    import osmnx as ox

    consulted = {k for keys in access._MODE_TAG_ORDER.values() for k in keys}
    consulted |= {"access"}            # the generic fallback in classify_access
    consulted |= {"highway"}           # highway_allowed, and the drive friction table
    consulted |= {"oneway:bicycle"}    # add_travel_times' contraflow rule
    consulted |= {"oneway"}            # how the XML parser orients every edge
    available = set(ox.settings.useful_tags_way) | set(speeds.EXTRA_WAY_TAGS)
    assert consulted <= available, f"rules read tags the extract drops: {sorted(consulted - available)}"


def test_the_required_set_covers_osmnx_defaults_too():
    """Removing a default osmnx retains -- `oneway`, which orients every edge -- used to survive
    this file, because the requirement was `EXTRA_WAY_TAGS` alone (pass 35)."""
    assert "oneway" in REQUIRED and "highway" in REQUIRED and "access" in REQUIRED


def test_surface_is_extracted_although_no_rule_reads_it_yet():
    """Owner decision 2026-11-10. The walked journey could not be judged on paving because the tag
    that judges it was absent from the graph, so extraction comes first and the rule second. If a
    future change drops it, this test is the record of why it was added."""
    assert "surface" in speeds.EXTRA_WAY_TAGS
