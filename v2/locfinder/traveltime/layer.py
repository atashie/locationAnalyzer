"""Build one uint8 minutes raster: minutes from every grid cell to the nearest
destination node, for one mode. Destinations are node indices (snap POIs to nodes
with osmnx.nearest_nodes before calling)."""
from __future__ import annotations

import time

import numpy as np
import rasterio

from ..grid import GridSpec, encode_minutes
from .arrival import arrival_seconds
from .snap import EdgeIndex, cell_seconds_from_arrival


def build_layer(
    G,
    csr,
    index,
    grid: GridSpec,
    *,
    dest_idx,
    mode: str,
    cutoff_min: float = 120.0,
    max_access_m: float = 200.0,
    timings: dict | None = None,
) -> np.ndarray:
    t0 = time.perf_counter()
    T = arrival_seconds(csr, dest_idx=dest_idx, cutoff_s=cutoff_min * 60.0)
    t1 = time.perf_counter()
    idx = EdgeIndex.from_graph(G, index)
    t2 = time.perf_counter()
    xs, ys = grid.cell_centers_xy()
    secs = cell_seconds_from_arrival(idx, T, xs, ys, mode=mode, max_access_m=max_access_m)
    t3 = time.perf_counter()
    if timings is not None:
        timings.update(dijkstra_s=t1 - t0, edge_index_s=t2 - t1, snap_s=t3 - t2)
    return encode_minutes(secs)


def write_layer(path, arr: np.ndarray, grid: GridSpec, *, tags: dict) -> None:
    """Write a uint8 minutes GeoTIFF with provenance tags (engine, mode, category,
    direction=arrival, profile, grid version, built_at)."""
    profile = grid.rasterio_profile()
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(arr, 1)
        dst.update_tags(**{k: str(v) for k, v in tags.items()})
