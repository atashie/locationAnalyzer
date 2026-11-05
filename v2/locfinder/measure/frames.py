"""The two S3 sampling frames, as frozen artifacts with digests.

Design §1. Frame **B** is the 512,633 structure centroids whose projected centroid falls inside the
100 m grid; frame **C** is the 330,502 cells of that grid, each sampled cell contributing **one
uniformly random point inside it**.

**Why the draw is specified to the call, not just to the distribution.** "Simple random sample" does
not identify a sequence, and three review passes turned sampling prose into a wrong implementation
that passed its tests. In particular, drawing *one* uniform number and using it for **both**
within-cell offsets gives correct marginal means and spreads — over 100,000 draws, means 49.9574 m
and standard deviations 28.8447 m — with **correlation 1**: every point on a cell diagonal, zero
probability over almost all ground (pass-18 F18). Marginal checks accept it. So the draw itself is
normative:

    rng    = numpy.random.Generator(PCG64(seed))
    frame C: cells   = rng.permutation(N_cells)[:n]      # first
             offsets = rng.random((n, 2))                # then, two independent columns
    frame B: idx     = rng.permutation(N_population)[:n]

`permutation(N)[:n]` rather than `choice(..., replace=False)` because `choice` selects among
internal algorithms by the `n/N` ratio, so it is not a specification. The order of the two frame-C
calls matters and is part of the specification.

**Population order is intrinsic, not file order.** S2.5 recorded that file order is not stable
across downloads and that "the first *N*" silently changed which POIs an experiment used. So frame
B's population is sorted by Overture `id` before any draw, which makes the ordering a property of
the data rather than of the download, and the source file is hashed as well.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

from ..grid import GridSpec

BIT_GENERATOR = np.random.PCG64


# ----------------------------------------------------------------------------- cell geometry


def cell_row_col(flat_index: np.ndarray, grid: GridSpec) -> tuple[np.ndarray, np.ndarray]:
    """Flat C-order index -> (row, col). Row 0 is at `y_max`, because the raster is north-up."""
    flat = np.asarray(flat_index, dtype=np.int64)
    if flat.size and (flat.min() < 0 or flat.max() >= grid.nrows * grid.ncols):
        raise ValueError("flat index outside the grid")
    return flat // grid.ncols, flat % grid.ncols


def cell_bounds(flat_index: np.ndarray, grid: GridSpec) -> np.ndarray:
    """`(n, 4)` of `(x0, y0, x1, y1)` in the grid's CRS, with `y0 < y1`.

    Rows run **downward** from `y_max`, which is the off-by-one this exists to make testable: row 0
    spans `(y_max - cell, y_max]` and the last row spans `(y_min, y_min + cell]`.
    """
    row, col = cell_row_col(flat_index, grid)
    x0 = grid.x_min + col * grid.cell_m
    y1 = grid.y_max - row * grid.cell_m
    return np.column_stack([x0, y1 - grid.cell_m, x0 + grid.cell_m, y1])


# ----------------------------------------------------------------------------- the frame


@dataclass(frozen=True)
class Frame:
    kind: str                   # "structures" | "area"
    points: np.ndarray          # (n, 2) float64, in `crs`
    source_ids: np.ndarray      # Overture id (frame B) or flat cell index (frame C)
    seed: int
    population_n: int
    crs: str
    source_digest: str          # what the population was derived from
    digest: str                 # this frame's own content

    def __post_init__(self) -> None:
        if self.points.shape != (len(self.source_ids), 2):
            raise ValueError(f"points {self.points.shape} do not match "
                             f"{len(self.source_ids)} source ids")

    @property
    def n(self) -> int:
        return len(self.source_ids)


def _digest_points(points: np.ndarray, source_ids: np.ndarray, seed: int,
                   population_n: int, source_digest: str) -> str:
    """Content digest. Includes the seed and population size, so two frames that happen to share
    points but were drawn from different populations do not collide."""
    h = hashlib.sha256()
    h.update(np.ascontiguousarray(points, dtype=np.float64).tobytes())
    h.update(np.ascontiguousarray(
        np.asarray([str(s) for s in source_ids], dtype="U64")).tobytes())
    h.update(json.dumps({"seed": seed, "population_n": population_n,
                         "source_digest": source_digest}, sort_keys=True).encode())
    return h.hexdigest()


def file_digest(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def grid_digest(grid: GridSpec) -> str:
    """The frame-C population is the grid itself, so its identity is the grid's."""
    return hashlib.sha256(json.dumps({
        "crs": grid.crs, "x_min": grid.x_min, "y_max": grid.y_max,
        "cell_m": grid.cell_m, "ncols": grid.ncols, "nrows": grid.nrows,
    }, sort_keys=True).encode()).hexdigest()


# ----------------------------------------------------------------------------- frame C


def build_frame_c(grid: GridSpec, *, n: int, seed: int) -> Frame:
    """Design §1: SRS of cells without replacement, then one uniform point inside each.

    The two offsets are **columns of a single `(n, 2)` draw**, which is what makes them independent
    and what an exact-sequence oracle can check.
    """
    population_n = grid.nrows * grid.ncols
    if not 0 < n <= population_n:
        raise ValueError(f"require 0 < n <= {population_n}, got {n}")
    rng = np.random.Generator(BIT_GENERATOR(seed))
    cells = rng.permutation(population_n)[:n]
    offsets = rng.random((n, 2))
    bounds = cell_bounds(cells, grid)
    xs = bounds[:, 0] + offsets[:, 0] * grid.cell_m
    ys = bounds[:, 1] + offsets[:, 1] * grid.cell_m
    points = np.column_stack([xs, ys])
    sd = grid_digest(grid)
    return Frame(kind="area", points=points, source_ids=cells, seed=seed,
                 population_n=population_n, crs=grid.crs, source_digest=sd,
                 digest=_digest_points(points, cells, seed, population_n, sd))


# ----------------------------------------------------------------------------- frame B


def structure_population(parquet: Path, grid: GridSpec) -> tuple[np.ndarray, np.ndarray, int]:
    """`(ids, points, total_rows)` for every structure whose **projected** centroid is inside the
    grid, ordered by Overture `id`.

    Centroids are computed **after** projecting to the grid's CRS. Computing them in the geographic
    CRS is wrong for an area-weighted quantity and emits a warning that S2.4 already tripped over.
    """
    gdf = gpd.read_parquet(parquet)
    total = len(gdf)
    proj = gdf.geometry.to_crs(grid.crs)
    cen = proj.centroid
    x = cen.x.to_numpy()
    y = cen.y.to_numpy()
    y_min = grid.y_max - grid.nrows * grid.cell_m
    x_max = grid.x_min + grid.ncols * grid.cell_m
    inside = (x >= grid.x_min) & (x < x_max) & (y >= y_min) & (y < grid.y_max)
    ids = gdf["id"].to_numpy()[inside]
    pts = np.column_stack([x[inside], y[inside]])
    order = np.argsort(ids, kind="stable")      # intrinsic order, not file order (S2.5)
    return ids[order], pts[order], total


def build_frame_b(parquet: Path, grid: GridSpec, *, n: int, seed: int,
                  population: tuple[np.ndarray, np.ndarray] | None = None,
                  source_digest: str | None = None) -> Frame:
    """Design §1's structure frame. `population` and `source_digest` may be supplied to avoid
    re-reading and re-projecting 522,160 geometries, which takes minutes."""
    if population is None:
        ids, pts, _ = structure_population(parquet, grid)
    else:
        ids, pts = population
    sd = source_digest if source_digest is not None else file_digest(parquet)
    population_n = len(ids)
    if not 0 < n <= population_n:
        raise ValueError(f"require 0 < n <= {population_n}, got {n}")
    rng = np.random.Generator(BIT_GENERATOR(seed))
    idx = rng.permutation(population_n)[:n]
    points = pts[idx]
    chosen = ids[idx]
    return Frame(kind="structures", points=points, source_ids=chosen, seed=seed,
                 population_n=population_n, crs=grid.crs, source_digest=sd,
                 digest=_digest_points(points, chosen, seed, population_n, sd))


# ----------------------------------------------------------------------------- persistence


def write_frame(frame: Frame, directory: Path) -> tuple[Path, Path]:
    """Write `frame_<kind>_<digest8>.parquet` plus its manifest. **Never overwrites**: a new sample
    is a new digest, so a collision means an attempt to rewrite an existing frame."""
    directory.mkdir(parents=True, exist_ok=True)
    stem = f"frame_{'b' if frame.kind == 'structures' else 'c'}_{frame.digest[:8]}"
    data_path = directory / f"{stem}.parquet"
    manifest_path = directory / f"{stem}.json"
    if data_path.exists() or manifest_path.exists():
        raise FileExistsError(f"{stem} already exists; a frame artifact is never overwritten")
    pd.DataFrame({
        "source_id": [str(s) for s in frame.source_ids],
        "x": frame.points[:, 0],
        "y": frame.points[:, 1],
    }).to_parquet(data_path, index=False)
    manifest_path.write_text(json.dumps({
        "kind": frame.kind,
        "n": frame.n,
        "seed": frame.seed,
        "population_n": frame.population_n,
        "crs": frame.crs,
        "source_digest": frame.source_digest,
        "digest": frame.digest,
        "sampling": "numpy.random.Generator(PCG64(seed)); permutation(N)[:n]"
                    + ("; then random((n, 2)) for the two independent within-cell offsets"
                       if frame.kind == "area" else ""),
    }, indent=2, sort_keys=True), encoding="utf-8")
    return data_path, manifest_path
