"""Shared constants and helpers for Phase 0 / Phase 1 spike scripts.

Metro-aware: set `LOCFINDER_METRO=slice` to reproduce the original Phase 0 results, or leave it
unset for the default `triangle` metro (widened south and east, with a routing buffer). Data lives
under `v2/data/<metro>/` and layers under `v2/data/layers/` with the metro in the filename when it
is not the slice, so earlier artifacts stay valid.
"""
from __future__ import annotations

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
