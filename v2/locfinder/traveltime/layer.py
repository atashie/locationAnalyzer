"""Build one travel-time layer: seconds (float) and uint8 minutes from every grid cell
to the nearest destination node, for one mode. Destinations are node indices (snap
POIs to nodes with osmnx.nearest_nodes, with a distance bound, before calling)."""
from __future__ import annotations

import time

import numpy as np
import rasterio

from ..grid import GridSpec, encode_minutes
from .arrival import arrival_seconds
from .snap import EdgeIndex, cell_seconds_from_arrival


def build_layer_seconds(
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
    edge_index: EdgeIndex | None = None,
) -> np.ndarray:
    """Float seconds per cell (inf = unreachable). Evaluation should use this, not the
    uint8 encoding, so rounding cannot move a threshold (Codex pass-3 H6)."""
    t0 = time.perf_counter()
    T = arrival_seconds(csr, dest_idx=dest_idx, cutoff_s=cutoff_min * 60.0)
    t1 = time.perf_counter()
    idx = edge_index if edge_index is not None else EdgeIndex.from_graph(G, index)
    t2 = time.perf_counter()
    xs, ys = grid.cell_centers_xy()
    secs = cell_seconds_from_arrival(idx, T, xs, ys, mode=mode, max_access_m=max_access_m)
    t3 = time.perf_counter()
    if timings is not None:
        timings.update(dijkstra_s=t1 - t0, edge_index_s=t2 - t1, snap_s=t3 - t2)
    return secs


def build_layer(G, csr, index, grid: GridSpec, *, dest_idx, mode: str, cutoff_min: float = 120.0,
                max_access_m: float = 200.0, timings: dict | None = None, edge_index: EdgeIndex | None = None) -> np.ndarray:
    secs = build_layer_seconds(G, csr, index, grid, dest_idx=dest_idx, mode=mode, cutoff_min=cutoff_min,
                               max_access_m=max_access_m, timings=timings, edge_index=edge_index)
    return encode_minutes(secs)


def write_layer(path, arr: np.ndarray, grid: GridSpec, *, tags: dict) -> None:
    """Write a uint8 minutes GeoTIFF with provenance tags (engine, mode, category,
    direction=arrival, profile, grid version, built_at)."""
    profile = grid.rasterio_profile()
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(arr, 1)
        dst.update_tags(**{k: str(v) for k, v in tags.items()})
