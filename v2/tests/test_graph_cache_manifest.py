"""The road-graph cache has to say what it was parsed from, and the rules have to say what they read.

Two instances of one failure, found on the same afternoon:

* `spikes/g1_own_graph_layer.load_graph` returned the 670 MB graphml cache whenever the file
  existed. Adding a tag to `EXTRA_WAY_TAGS` therefore changed nothing until somebody deleted the
  cache by hand, and no script said so -- every measurement would have run on the old graph and
  agreed with itself.
* `access.classify_access` consults `vehicle` for the drive and bike modes, and `vehicle` was never
  in `EXTRA_WAY_TAGS`, so the extract never carried it and that branch could not fire. 102 ways in
  the Triangle extract are tagged `vehicle` (92 of them `vehicle=no`). A rule that reads a tag the
  extract drops is not a conservative rule; it is a dead one.

The shared shape is a claim about data that nothing checked. These tests check both halves: that a
cache cannot be reused on trust, and that every tag a rule consults is one extraction keeps.
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

TODAY = common.graph_cache_manifest()


def test_a_cache_with_no_manifest_cannot_be_reused():
    why = common.graph_cache_complaint(None)
    assert why is not None
    assert "unknown" in why
    for tag in TODAY["extra_way_tags"]:
        assert tag in why, "the complaint should name what the rules need"


def test_a_cache_missing_a_tag_todays_rules_need_is_rejected_by_name():
    stale = dict(TODAY, extra_way_tags=[t for t in TODAY["extra_way_tags"] if t != "surface"])
    why = common.graph_cache_complaint(stale)
    assert why is not None and "surface" in why


def test_a_cache_with_exactly_todays_tags_is_accepted():
    assert common.graph_cache_complaint(dict(TODAY)) is None


def test_a_cache_parsed_with_more_tags_than_we_need_is_accepted():
    """The rule is asymmetric on purpose: a superset carries everything the rules ask for."""
    superset = dict(TODAY, extra_way_tags=sorted(TODAY["extra_way_tags"] + ["tracktype"]))
    assert common.graph_cache_complaint(superset) is None


def test_a_cache_built_from_a_different_source_file_is_rejected():
    why = common.graph_cache_complaint(dict(TODAY, source="some-other-roads.osm"))
    assert why is not None and "some-other-roads.osm" in why


def test_what_the_writer_writes_the_checker_accepts(tmp_path):
    cache = tmp_path / "roads.graphml"
    cache.write_bytes(b"not really a graph")
    written = common.write_graph_cache_manifest(cache)
    assert written.name == "roads.tags.json"
    stored = json.loads(written.read_text(encoding="utf-8"))
    assert common.graph_cache_complaint(stored) is None
    assert common.read_graph_cache_manifest(cache) == stored


def test_load_refuses_a_missing_cache_and_says_how_to_build_one(tmp_path):
    with pytest.raises(SystemExit) as e:
        common.load_roads_graph(tmp_path / "absent.graphml")
    assert "g1_own_graph_layer" in str(e.value)


def test_load_refuses_a_stale_cache_before_reading_the_graph(tmp_path, monkeypatch):
    """The refusal has to come first. Loading 670 MB and *then* complaining is not a guard."""
    import osmnx as ox

    cache = tmp_path / "roads.graphml"
    cache.write_bytes(b"not really a graph")
    (tmp_path / "roads.tags.json").write_text(json.dumps(
        {"extra_way_tags": ["foot"], "source": TODAY["source"]}), encoding="utf-8")

    def explode(*a, **k):
        raise AssertionError("load_graphml must not be reached for a stale cache")

    monkeypatch.setattr(ox, "load_graphml", explode)
    with pytest.raises(SystemExit) as e:
        common.load_roads_graph(cache)
    assert "stale" in str(e.value)


def test_load_reads_the_graph_once_the_manifest_is_satisfied(tmp_path, monkeypatch):
    """The companion to the test above: a satisfied manifest must not block a real load."""
    import osmnx as ox

    cache = tmp_path / "roads.graphml"
    cache.write_bytes(b"not really a graph")
    common.write_graph_cache_manifest(cache)
    monkeypatch.setattr(ox, "load_graphml", lambda path, **k: ("loaded", Path(path)))
    assert common.load_roads_graph(cache) == ("loaded", cache)


def test_every_tag_the_access_rules_consult_is_one_extraction_keeps():
    """This is the test that found `vehicle` missing. `_MODE_TAG_ORDER` is the authority on which
    tags `classify_access` reads, so the invariant is derived from it rather than retyped."""
    import osmnx as ox

    consulted = {k for keys in access._MODE_TAG_ORDER.values() for k in keys}
    consulted |= {"access"}            # the generic fallback in classify_access
    consulted |= {"highway"}           # highway_allowed, and the drive friction table
    consulted |= {"oneway:bicycle"}    # add_travel_times' contraflow rule
    available = set(ox.settings.useful_tags_way) | set(speeds.EXTRA_WAY_TAGS)
    assert consulted <= available, f"rules read tags the extract drops: {sorted(consulted - available)}"


def test_surface_is_extracted_although_no_rule_reads_it_yet():
    """Owner decision 2026-11-10. The walked journey could not be judged on paving because the tag
    that judges it was absent from the graph, so extraction comes first and the rule second. If a
    future change drops it, this test is the record of why it was added."""
    assert "surface" in speeds.EXTRA_WAY_TAGS
