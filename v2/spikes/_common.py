"""Shared constants and helpers for Phase 0 spike scripts (import as `from _common import *`
after adding the spikes directory to sys.path, which the scripts do themselves)."""
from __future__ import annotations

import time
from pathlib import Path

from locfinder.grid import GridSpec

REPO = Path(__file__).resolve().parents[2]
V2 = REPO / "v2"
DATA = V2 / "data"
SLICE = DATA / "slice"
LAYERS = DATA / "layers"
RESULTS = REPO / "docs" / "experiments"
for p in (LAYERS, RESULTS):
    p.mkdir(parents=True, exist_ok=True)

SLICE_BBOX = dict(west=-79.15, south=35.80, east=-78.55, north=36.15)
GRID = GridSpec.from_bbox_wgs84(**SLICE_BBOX, cell_m=100)
VALHALLA = "http://localhost:8002"
OVERTURE_RELEASE = "2026-10-21.0"
ACCEPTED_PLACES = SLICE / "overture_places_accepted.parquet"
OSM_POIS = SLICE / "osm_pois.parquet"

# Valhalla costing names for our modes
VALHALLA_COSTING = {"walk": "pedestrian", "bike": "bicycle", "drive": "auto"}
# Controlled comparison: Valhalla pedestrian walking_speed in km/h matching our 1.4 m/s
CONTROLLED_COSTING_OPTIONS = {"pedestrian": {"walking_speed": 5.04}, "bicycle": {"cycling_speed": 16.2}, "auto": {}}


def append_results(filename: str, text: str) -> None:
    with (RESULTS / filename).open("a", encoding="utf-8", newline="\n") as f:
        f.write("\n" + text + "\n")


def stamp() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")
