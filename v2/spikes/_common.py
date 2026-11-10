"""Shared constants and helpers for Phase 0 / Phase 1 spike scripts.

Metro-aware: set `LOCFINDER_METRO=slice` to reproduce the original Phase 0 results, or leave it
unset for the default `triangle` metro (widened south and east, with a routing buffer). Data lives
under `v2/data/<metro>/` and layers under `v2/data/layers/` with the metro in the filename when it
is not the slice, so earlier artifacts stay valid.
"""
from __future__ import annotations

import json
import os
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
# measurement would have run on the old graph and agreed with itself. The sidecar below records the
# tag set beside the cache so that reuse is checked instead of assumed.
#
# The rule is asymmetric on purpose. A cache parsed with MORE tags than today's rules need carries
# everything they ask for and is usable; one MISSING a tag cannot answer for a rule that reads it,
# whether or not any rule reads it yet.


REBUILD_HINT = ("\nRebuild it with `uv run python spikes/g1_own_graph_layer.py grocery walk`, which re-parses the "
                "XML and writes the manifest.")


def graph_cache_manifest() -> dict:
    """What a cache would have to have been built from to answer for today's rules."""
    from locfinder.traveltime.speeds import EXTRA_WAY_TAGS

    return {"extra_way_tags": sorted(EXTRA_WAY_TAGS), "source": ROADS_XML.name}


def graph_cache_complaint(stored: dict | None) -> str | None:
    """Why a cache built under `stored` cannot be reused, or None if it can."""
    want = graph_cache_manifest()
    if stored is None:
        return ("no tag manifest beside it, so the way tags it was parsed with are unknown "
                f"(today's rules need {', '.join(want['extra_way_tags'])})")
    missing = sorted(set(want["extra_way_tags"]) - set(stored.get("extra_way_tags") or []))
    if missing:
        return f"built without the way tag(s) {', '.join(missing)}, which today's rules require"
    if stored.get("source") != want["source"]:
        return f"built from {stored.get('source')!r}, not {want['source']!r}"
    return None


def read_graph_cache_manifest(cache: Path | None = None) -> dict | None:
    path = (Path(cache) if cache is not None else GRAPH_CACHE).with_suffix(".tags.json")
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_graph_cache_manifest(cache: Path | None = None) -> Path:
    path = (Path(cache) if cache is not None else GRAPH_CACHE).with_suffix(".tags.json")
    body = dict(graph_cache_manifest(), written_at=stamp())
    blob = json.dumps(body, indent=2, sort_keys=True) + "\n"
    path.write_text(blob, encoding="utf-8", newline="\n")
    return path


def load_roads_graph(cache: Path | None = None):
    """The cached road graph, refusing one built under a tag set today's rules outgrew.

    Only `spikes/g1_own_graph_layer.py` rebuilds the cache; everything else fails loudly rather
    than measuring on a graph that silently lacks a tag.
    """
    import osmnx as ox

    path = Path(cache) if cache is not None else GRAPH_CACHE
    if not path.exists():
        raise SystemExit(f"no cached graph at {path}; build it with "
                         "`uv run python spikes/g1_own_graph_layer.py grocery walk`")
    why = graph_cache_complaint(read_graph_cache_manifest(path))
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
