"""Shared constants and helpers for Phase 0 / Phase 1 spike scripts.

Metro-aware: set `LOCFINDER_METRO=slice` to reproduce the original Phase 0 results, or leave it
unset for the default `triangle` metro (widened south and east, with a routing buffer). Data lives
under `v2/data/<metro>/` and layers under `v2/data/layers/` with the metro in the filename when it
is not the slice, so earlier artifacts stay valid.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

from locfinder.metros import get_metro

REPO = Path(__file__).resolve().parents[2]
V2 = REPO / "v2"
DATA = V2 / "data"
LAYERS = DATA / "layers"
RESULTS = REPO / "docs" / "experiments"

METRO = get_metro(os.environ.get("LOCFINDER_METRO"))
METRO_DIR = DATA / METRO.name
GRID = METRO.grid()

for _p in (LAYERS, RESULTS, METRO_DIR):
    _p.mkdir(parents=True, exist_ok=True)

# Evaluation bbox as a dict, for scripts that pass it to GridSpec or an API
SLICE_BBOX = dict(west=METRO.evaluation.west, south=METRO.evaluation.south,
                  east=METRO.evaluation.east, north=METRO.evaluation.north)
EVAL_BBOX = SLICE_BBOX
ROUTING_BBOX = dict(west=METRO.routing.west, south=METRO.routing.south,
                    east=METRO.routing.east, north=METRO.routing.north)

# Per-metro data artifacts
SLICE = METRO_DIR                      # kept for scripts written during Phase 0
ACCEPTED_PLACES = METRO_DIR / "overture_places_accepted.parquet"
RAW_PLACES = METRO_DIR / "overture_places_raw.parquet"
OSM_POIS = METRO_DIR / "osm_pois.parquet"
ROUTING_PBF = METRO_DIR / ("slice.osm.pbf" if METRO.name == "slice" else "triangle-routing.osm.pbf")
ROADS_XML = METRO_DIR / ("slice-roads.osm" if METRO.name == "slice" else "triangle-roads.osm")
GRAPH_CACHE = METRO_DIR / "roads.graphml"


# ---------------------------------------------------------------- the road graph cache
# A graphml cache does not record which OSM way tags were retained when the XML was parsed, and
# `load_graph` returned the cache whenever it existed. So adding a tag to `EXTRA_WAY_TAGS` changed
# nothing at all until somebody deleted a 670 MB file by hand, and no script said so: every
# measurement would have run on the old graph and agreed with itself.
#
# Revision 2 (Codex pass 35 F1). The first version trusted the sidecar for the tag set, which made
# the pairing the weak link: Codex wrote a valid graph and manifest, swapped in a graph lacking
# `vehicle`, and `load_roads_graph` accepted it. A manifest that does not say WHICH file it
# describes establishes nothing about that file. So the manifest now records the graphml's size and
# sha256 and both are checked, and the writer additionally verifies that the graph's own `<key>`
# declarations carry the tags the rules need -- a parse that quietly failed to retain a tag cannot
# be certified by the same process that asked for it.
#
# Two rules are asymmetric on purpose:
#   * tags -- a cache parsed with MORE than today's rules need carries everything they ask for and
#     is usable; one missing a tag cannot answer for a rule that reads it, whether or not any rule
#     reads it yet;
#   * declarations -- a graphml declares a key only if some element carries it, so a missing
#     declaration means "not requested" OR "requested and nothing had it". `landuse` is in osmnx's
#     defaults and no highway way in the Triangle carries it, so requiring every default to be
#     declared would refuse every real graph. The writer therefore refuses only when a tag from
#     EXTRA_WAY_TAGS is undeclared -- those are the ones we added deliberately, and their absence
#     would mean the addition did nothing -- and records the rest as provenance.
#
# What this still does not establish: parsing *semantics*. A tag's presence does not say how it was
# interpreted, and the manifest records the parse options it knows (`simplify`, `retain_all`) rather
# than every osmnx setting in effect.

REBUILD_HINT = ("\nRebuild it with `uv run python spikes/g1_own_graph_layer.py grocery walk`, which "
                "re-parses the XML and writes the manifest.")
_KEY_DECL = re.compile(r'<key[^>]*\bfor="edge"[^>]*\battr\.name="([^"]+)"')
_GRAPHML_HEAD_BYTES = 1 << 20


def graph_cache_requirements() -> dict:
    """What a cache has to have been built from to answer for today's rules."""
    import osmnx as ox

    from locfinder.traveltime.speeds import EXTRA_WAY_TAGS

    return {
        "required_way_tags": sorted(set(ox.settings.useful_tags_way) | set(EXTRA_WAY_TAGS)),
        "source": ROADS_XML.name,
        "parse": {"simplify": True, "retain_all": True},
    }


def graph_declared_edge_attrs(path: Path, *, head_bytes: int = _GRAPHML_HEAD_BYTES) -> set[str]:
    """Edge attribute names the graphml file itself declares, from its `<key>` elements.

    osmnx writes every declaration before the first node, so the head of the file is enough and a
    695 MB graph need not be parsed. This reads the graph rather than a claim about the graph, which
    is the point.
    """
    with open(path, "rb") as fh:
        head = fh.read(head_bytes).decode("utf-8", errors="replace")
    return set(_KEY_DECL.findall(head))


def graph_cache_complaint(stored: dict | None, graph_path: Path | None = None) -> str | None:
    """Why a cache described by `stored` cannot be reused, or None if it can.

    `graph_path` is what binds the manifest to a file. Omit it only to check the declared tag set in
    isolation; a reuse decision without it is the hole revision 2 exists to close.
    """
    want = graph_cache_requirements()
    if stored is None:
        return ("no tag manifest beside it, so the way tags it was parsed with are unknown "
                f"(today's rules need {', '.join(want['required_way_tags'])})")
    missing = sorted(set(want["required_way_tags"]) - set(stored.get("way_tags") or []))
    if missing:
        return f"built without the way tag(s) {', '.join(missing)}, which today's rules require"
    if stored.get("source") != want["source"]:
        return f"built from {stored.get('source')!r}, not {want['source']!r}"
    if stored.get("parse") != want["parse"]:
        return f"parsed with {stored.get('parse')!r}, not {want['parse']!r}"
    if graph_path is None:
        return "checked without a graph file, so the manifest is not bound to anything"
    size = graph_path.stat().st_size
    if stored.get("graphml_bytes") != size:
        return (f"describes a {stored.get('graphml_bytes')!r}-byte graph; this one is {size} bytes")
    from locfinder.measure.frames import file_digest

    digest = file_digest(graph_path)
    if stored.get("graphml_sha256") != digest:
        return (f"describes sha256 {str(stored.get('graphml_sha256'))[:12]}…; this graph is "
                f"{digest[:12]}… — the manifest belongs to a different file")
    return None


def read_graph_cache_manifest(cache: Path | None = None) -> dict | None:
    path = (Path(cache) if cache is not None else GRAPH_CACHE).with_suffix(".tags.json")
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_graph_cache_manifest(cache: Path | None = None, *,
                               requested_but_absent: list[str] | None = None) -> Path:
    """Stamp the manifest for the graph at `cache`, after checking the graph carries the added tags.

    Refuses when a tag from `EXTRA_WAY_TAGS` is neither declared by the graph nor named in
    `requested_but_absent`: those tags were added on purpose, and a graph that does not carry one
    is evidence the addition did nothing. Only the process that parsed can tell "not retained" from
    "absent from the data" apart, so a re-stamp of somebody else's file cannot assert it.

    osmnx's own defaults are NOT required to be declared -- `landuse` is a default and no highway
    way in the Triangle carries it -- so they are recorded as provenance instead.
    """
    from locfinder.measure.frames import file_digest

    from locfinder.traveltime.speeds import EXTRA_WAY_TAGS

    graph = Path(cache) if cache is not None else GRAPH_CACHE
    want = graph_cache_requirements()
    declared = graph_declared_edge_attrs(graph)
    absent = set(requested_but_absent or ())
    unconfirmed = sorted(t for t in EXTRA_WAY_TAGS if t not in declared and t not in absent)
    if unconfirmed:
        raise SystemExit(
            f"{graph.name} does not declare the way tag(s) {', '.join(unconfirmed)}, which "
            "EXTRA_WAY_TAGS adds deliberately. Either the parse did not retain them, or they are "
            "absent from the data -- and only the process that parsed can tell those apart, so it "
            "must say so via `requested_but_absent`. Refusing to certify a graph that cannot be "
            "shown to carry a tag we went out of our way to extract.")
    # `source` and `parse` describe this build; `required_way_tags` is recomputed at check time
    # and would only be a stale duplicate of `way_tags` here.
    body = dict(
        source=want["source"],
        parse=want["parse"],
        way_tags=want["required_way_tags"],
        way_tags_declared_by_graph=sorted(declared & set(want["required_way_tags"])),
        way_tags_required_but_not_declared=sorted(
            set(want["required_way_tags"]) - declared),
        way_tags_requested_but_absent=sorted(absent),
        graphml_bytes=graph.stat().st_size,
        graphml_sha256=file_digest(graph),
        written_at=stamp(),
    )
    path = graph.with_suffix(".tags.json")
    blob = json.dumps(body, indent=2, sort_keys=True) + "\n"
    path.write_text(blob, encoding="utf-8", newline="\n")
    return path


def load_roads_graph(cache: Path | None = None):
    """The cached road graph, refusing one the rules have outgrown or a manifest it does not match.

    Only `spikes/g1_own_graph_layer.py` writes the cache; everything else fails loudly rather than
    measuring on a graph that silently lacks a tag. The refusal comes before the graph is read: a
    guard that loads 695 MB and then complains is not a guard.
    """
    import osmnx as ox

    path = Path(cache) if cache is not None else GRAPH_CACHE
    if not path.exists():
        raise SystemExit(f"no cached graph at {path}; build it with "
                         "`uv run python spikes/g1_own_graph_layer.py grocery walk`")
    why = graph_cache_complaint(read_graph_cache_manifest(path), path)
    if why:
        raise SystemExit(f"{path.name} is stale: {why}.{REBUILD_HINT}")
    return ox.load_graphml(path)


VALHALLA = os.environ.get("VALHALLA_URL", "http://localhost:8002")
VALHALLA_NC = os.environ.get("VALHALLA_NC_URL", "http://localhost:8003")
MOTIS = os.environ.get("MOTIS_URL", "http://localhost:8080")
OVERTURE_RELEASE = "2026-10-21.0"

VALHALLA_COSTING = {"walk": "pedestrian", "bike": "bicycle", "drive": "auto"}
# Controlled comparison: engine speeds matched to our own static model
CONTROLLED_COSTING_OPTIONS = {"pedestrian": {"walking_speed": 5.04}, "bicycle": {"cycling_speed": 16.2}, "auto": {}}


def layer_path(kind: str, category: str, mode: str, suffix: str = ".tif", *, metro: str | None = None) -> Path:
    """`own`/`valhalla` layer path; the metro name is included unless it is the Phase 0 slice."""
    name = metro or METRO.name
    stem = f"{kind}_{category}_{mode}" if name == "slice" else f"{kind}_{name}_{category}_{mode}"
    return LAYERS / f"{stem}{suffix}"


def append_results(filename: str, text: str) -> None:
    with (RESULTS / filename).open("a", encoding="utf-8", newline="\n") as f:
        f.write("\n" + text + "\n")


def stamp() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")
