"""Build one travel-time layer: seconds (float) and uint8 minutes from every grid cell
to the nearest destination node, for one mode. Destinations are node indices (snap
POIs to nodes with osmnx.nearest_nodes, with a distance bound, before calling)."""
from __future__ import annotations

import time

import numpy as np
import rasterio

from ..grid import ENCODING, GridSpec, encode_minutes
from .arrival import arrival_seconds, arrival_seconds_two_weight
from .snap import EdgeIndex, cell_arrival_with_provenance, cell_seconds_from_arrival


def build_layer_seconds(
    G,
    csr,   # a single CSR, or a (cost_csr, time_csr) pair for the penalised two-weight path
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
    node_cost = None
    if isinstance(csr, tuple):
        # (cost, time): choose paths on cost, report real seconds (see access.py). The node costs
        # are carried into the cell stage so snapping selects the same branch the search did
        # (Codex pass-6 H1); the cutoff is applied once, at the end, after the access leg.
        cost_csr, time_csr = csr
        T = arrival_seconds_two_weight(cost_csr, time_csr, dest_idx=dest_idx)
        node_cost = arrival_seconds(cost_csr, dest_idx=dest_idx)
    else:
        # No node-level cutoff. Pruning the node search makes a merely-distant node
        # indistinguishable from an unreachable one, which is how a bounded call on our own graph
        # could mint a false NO_PATH (Codex pass-8 H1). Removing it changes no output: a node past
        # the horizon can never yield a cell inside it, since the access leg only adds time --
        # verified over 25 graphs x 400 cells at a deliberately tight horizon, zero cells changed.
        T = arrival_seconds(csr, dest_idx=dest_idx)
    t1 = time.perf_counter()
    idx = edge_index if edge_index is not None else EdgeIndex.from_graph(G, index)
    t2 = time.perf_counter()
    xs, ys = grid.cell_centers_xy()
    secs = cell_seconds_from_arrival(idx, T, xs, ys, mode=mode, max_access_m=max_access_m,
                                     node_cost=node_cost, cutoff_s=cutoff_min * 60.0)
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
    direction=arrival, profile, grid version, built_at).

    `encoding` is stamped here rather than left to the caller: the rounding rule changed from
    `rint` to `ceil`, the two differ by up to 30 s at every threshold, and the rasters are otherwise
    byte-compatible. A caller that forgot the tag would produce an artifact indistinguishable from
    the old rule, so it is not the caller's to forget.
    """
    profile = grid.rasterio_profile()
    stamped = {"encoding": ENCODING, **tags}
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(arr, 1)
        dst.update_tags(**{k: str(v) for k, v in stamped.items()})


def build_layer_surface(
    G,
    csr,
    index,
    grid: GridSpec,
    *,
    dest_idx,
    mode: str,
    target: str,
    engine: str = "own-graph",
    aggregation: str | None = None,
    cutoff_min: float = 120.0,
    max_access_m: float = 200.0,
    timings: dict | None = None,
    edge_index: EdgeIndex | None = None,
    places_selected: int | None = None,
):
    """A validated `status.Surface`: the same seconds as `build_layer_seconds`, plus the cause of
    every missing value.

    This is the builder a published layer should use. `build_layer_seconds` returns seconds alone
    and therefore cannot distinguish "no road near this cell" from "we did not search this far"
    (Codex pass-8 M4).

    `places_selected` separates the two layer-wide destination failures, which look identical from
    a cell's point of view and have different causes: `NO_DESTINATIONS` means the category selector
    found nothing, `NO_ROUTABLE_DESTINATIONS` means it found places but none snapped to a node.
    Both are unknown everywhere and both block publication (S4.4).
    """
    from ..status import CATEGORY_COST_SELECTED, ENGINES, Reason, Surface, node_reasons

    if aggregation is None:
        aggregation = CATEGORY_COST_SELECTED
    horizon_s = cutoff_min * 60.0
    dest = list(dest_idx)
    if not dest:
        reason = (Reason.NO_ROUTABLE_DESTINATIONS if places_selected
                  else Reason.NO_DESTINATIONS)
        return Surface.layer_failure(
            mode=mode, engine=engine, target=target, aggregation=aggregation,
            horizon_s=horizon_s, shape=(grid.nrows, grid.ncols), reason=reason,
        ).validate()

    t0 = time.perf_counter()
    node_cost = None
    if isinstance(csr, tuple):
        cost_csr, time_csr = csr
        T = arrival_seconds_two_weight(cost_csr, time_csr, dest_idx=dest)
        node_cost = arrival_seconds(cost_csr, dest_idx=dest)
    else:
        T = arrival_seconds(csr, dest_idx=dest)
    t1 = time.perf_counter()
    idx = edge_index if edge_index is not None else EdgeIndex.from_graph(G, index)
    t2 = time.perf_counter()
    xs, ys = grid.cell_centers_xy()
    # Both branches above run unbounded, which is what entitles this call to NO_PATH.
    # The engine is the caller's, never derived from the mode: `engine_for("drive")` is
    # valhalla-expansion, so deriving it here would misdescribe a drive layer built from our own
    # graph, and the whole point of H1 is that the claim must match the actual call.
    reasons = node_reasons(T, ENGINES[engine], search_bounded=False)
    secs, reason, lower = cell_arrival_with_provenance(
        idx, T, xs, ys, mode=mode, max_access_m=max_access_m, horizon_s=horizon_s,
        node_reason=reasons, node_cost=node_cost,
    )
    t3 = time.perf_counter()
    if timings is not None:
        timings.update(dijkstra_s=t1 - t0, edge_index_s=t2 - t1, snap_s=t3 - t2)
    return Surface(mode=mode, engine=engine, target=target, aggregation=aggregation,
                   horizon_s=horizon_s, seconds=secs, reason=reason,
                   min_possible_s=lower).validate()
