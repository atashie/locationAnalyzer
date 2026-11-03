# Phase 0 Experiments Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Use superpowers:test-driven-development for every code module (Tasks 1–3, 10, 12). Use superpowers:verification-before-completion before marking any gate passed.

**Goal:** Run the Phase 0 gates from `docs/research/08-synthesis.md` §6 on a Research Triangle slice so that the routing engine, transit engine, rendering path, POI sources, geocoder, and listings mechanism are chosen from measured results rather than priors (owner decision 16).

**Architecture:** A small Python package `v2/locfinder` (Windows, uv, Python 3.13) holds the frozen grid contract, a transposed-graph multi-source Dijkstra, nearest-edge snapping, fail-closed licence resolution, and listing-link builders, all unit-tested on synthetic inputs. Spike scripts under `v2/spikes/` drive the experiments against real data for one slice (Chapel Hill–Durham–RTP–west Raleigh). Valhalla and MOTIS run as Docker containers inside WSL2 Ubuntu (Docker is already installed there; the repo is mounted at `/mnt/c/Users/arikt/documents/github/distanceFinder`). Every experiment writes a results file under `docs/experiments/` with the measured numbers next to its pass criterion.

**Tech Stack:** Python 3.13 + uv; numpy, scipy (csgraph), shapely 2, pyproj, geopandas, rasterio, osmnx 2, duckdb, pyarrow, httpx, pytest; QuackOSM and overturemaps CLIs for data; Docker in WSL2 for `ghcr.io/valhalla/valhalla-scripted` and MOTIS; osmium-tool in WSL2; Node 24 for the rendering spike (MapLibre GL JS, d3-contour).

**Owner-set pass criteria (decision 12):** at a user threshold T, median absolute error ≤ 0.10·T and p90 ≤ 0.20·T, with false inclusion/exclusion rates reported.

**Slice bounding box (WGS84):** west −79.15, south 35.80, east −78.55, north 36.15. Full Triangle later: −79.20, 35.50, −78.25, 36.25.

**Conventions:** run Python from `v2/` with `uv run`; run Docker and osmium from WSL with `wsl -e bash -lc "<cmd>"`; large files live under `v2/data/` (gitignored); results under `docs/experiments/` (committed). Commit after every task. Never commit `backend/test_*.py` or `nul`.

---

## Task 0: Scaffold `v2/` and the experiments log

**Files:**
- Create: `v2/pyproject.toml`
- Create: `v2/locfinder/__init__.py`
- Create: `v2/tests/__init__.py`
- Create: `v2/README.md`
- Create: `v2/.gitignore`
- Create: `docs/experiments/README.md`
- Create: `docs/experiments/source-registry.md`

**Step 1: Create the project files**

`v2/pyproject.toml`:
```toml
[project]
name = "locfinder"
version = "0.0.1"
description = "V2 location finder: Phase 0 experiments and core contracts."
requires-python = ">=3.13,<3.14"
dependencies = [
    "numpy>=2.1",
    "scipy>=1.14",
    "shapely>=2.0",
    "pyproj>=3.7",
    "geopandas>=1.0",
    "rasterio>=1.4",
    "osmnx>=2.0",
    "duckdb>=1.1",
    "pyarrow>=18",
    "httpx>=0.27",
    "pydantic>=2",
]

[project.optional-dependencies]
dev = ["pytest>=8", "pytest-timeout"]
data = ["quackosm>=0.12", "overturemaps>=0.13"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["locfinder"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"
timeout = 120
```

`v2/.gitignore`:
```
.venv/
data/
__pycache__/
*.pyc
.pytest_cache/
spikes/**/out/
```

`v2/README.md`:
```markdown
# locfinder v2

Phase 0: experiments that choose the architecture. See `../docs/plans/2026-11-03-phase0-experiments.md`
and results in `../docs/experiments/`. Core contracts live in `locfinder/`; one-off spike scripts in `spikes/`.

Setup (Windows, from this directory):

    uv sync --extra dev --extra data
    uv run pytest

Heavy tooling runs in WSL2 Ubuntu (Docker, osmium). The repo is visible there at
/mnt/c/Users/arikt/documents/github/distanceFinder.
```

`docs/experiments/README.md`:
```markdown
# Phase 0 experiment results

One file per gate. Each file states the question, the method actually run, the raw numbers,
the pass criterion from `../research/08-synthesis.md` §6 and owner decision 12, and a verdict.
Claims here are measured on this machine on the dates given; they are not research estimates.

| Gate | File | Status |
|---|---|---|
| G6 POI coverage and licence | g6-poi-coverage.md | pending |
| Geocoding contract | geocoding.md | pending |
| G2 Valhalla self-host and anchors | g2-valhalla.md | pending |
| Transit engine (owner decision 13) | transit.md | pending |
| G1 own-graph vs Valhalla category layers | g1-routing.md | pending |
| G4 listings handoff | g4-listings.md | pending |
| G3 browser rendering | g3-rendering.md | pending |
| G5a early interaction comparison | g5a-interaction.md | pending |
| Phase 0 decisions | phase0-decisions.md | pending |
```

`docs/experiments/source-registry.md`:
```markdown
# Source registry

No dataset is downloaded or ingested before it has a row here (synthesis §3.4).

| Source | URL | Licence / terms | Permitted: store / display / commingle / commercial | Access date | Notes |
|---|---|---|---|---|---|
```

**Step 2: Create the environment and verify the geo stack imports**

Run (from repo root):
```powershell
cd v2; uv sync --extra dev --extra data; uv run python -c "import numpy, scipy, shapely, pyproj, geopandas, rasterio, osmnx, duckdb, pyarrow, httpx; print('geo stack ok', rasterio.__version__, osmnx.__version__)"
```
Expected: `geo stack ok 1.4.x 2.0.x` (versions may differ). If rasterio fails to install, run `uv pip install rasterio --only-binary :all:` and record the version used in `v2/README.md`.

**Step 3: Verify WSL2 Docker is usable**

Run: `wsl -e bash -lc "docker info --format '{{.ServerVersion}} {{.NCPU}}cpu {{.MemTotal}}'"`
Expected: a version string, 24cpu, and roughly 33 GB. If the daemon is not running: `wsl -e bash -lc "sudo service docker start"` and retry.

**Step 4: Commit**

```bash
git add v2/pyproject.toml v2/uv.lock v2/locfinder/__init__.py v2/tests/__init__.py v2/README.md v2/.gitignore docs/experiments/README.md docs/experiments/source-registry.md
git commit -m "feat(v2): scaffold locfinder package and Phase 0 experiments log"
```

---

## Task 1: Frozen grid contract (`locfinder/grid.py`)

The grid is a regular square raster in UTM zone 17N (EPSG:32617), 100 m cells for the slice. Minutes are stored as uint8: 0–254 minutes, 255 = nodata (unreachable or off-network). This is the contract every layer, anchor grid, and comparison uses.

**Files:**
- Create: `v2/locfinder/grid.py`
- Test: `v2/tests/test_grid.py`

**Step 1: Write the failing tests**

```python
# v2/tests/test_grid.py
import numpy as np
import pytest

from locfinder.grid import GridSpec, NODATA, encode_minutes


def test_grid_from_bbox_covers_bbox_with_whole_cells():
    g = GridSpec.from_bbox_wgs84(west=-79.15, south=35.80, east=-78.55, north=36.15, cell_m=100)
    assert g.crs == "EPSG:32617"
    assert g.cell_m == 100
    # ~54 km x ~39 km slice -> on the order of 540 x 390 cells, never fewer
    assert g.ncols >= 540 and g.nrows >= 390
    assert g.ncols < 700 and g.nrows < 500


def test_cell_centers_are_inside_bounds_and_row_major():
    g = GridSpec.from_bbox_wgs84(west=-79.0, south=36.0, east=-78.99, north=36.01, cell_m=100)
    xs, ys = g.cell_centers_xy()
    assert xs.shape == (g.nrows, g.ncols)
    assert np.all(xs > g.x_min) and np.all(xs < g.x_max)
    assert np.all(ys > g.y_min) and np.all(ys < g.y_max)
    # row 0 is the NORTH edge (raster convention)
    assert ys[0, 0] > ys[-1, 0]


def test_cell_centers_wgs84_round_trip():
    g = GridSpec.from_bbox_wgs84(west=-79.0, south=36.0, east=-78.99, north=36.01, cell_m=100)
    lons, lats = g.cell_centers_lonlat()
    assert lons.min() > -79.001 and lons.max() < -78.989
    assert lats.min() > 35.999 and lats.max() < 36.011


def test_encode_minutes_rounds_caps_and_marks_nodata():
    seconds = np.array([0.0, 59.0, 61.0, 254 * 60.0, 300 * 60.0, np.inf, np.nan])
    out = encode_minutes(seconds)
    assert out.dtype == np.uint8
    assert list(out[:4]) == [0, 1, 1, 254]
    assert out[4] == 254          # capped, still "reachable"
    assert out[5] == NODATA       # unreachable
    assert out[6] == NODATA       # missing


def test_rasterio_profile_matches_grid():
    g = GridSpec.from_bbox_wgs84(west=-79.0, south=36.0, east=-78.99, north=36.01, cell_m=100)
    p = g.rasterio_profile()
    assert p["width"] == g.ncols and p["height"] == g.nrows
    assert p["dtype"] == "uint8" and p["nodata"] == NODATA
    assert p["crs"].to_string() == "EPSG:32617"
    assert p["transform"].a == 100 and p["transform"].e == -100
```

**Step 2: Run tests to verify they fail**

Run: `cd v2; uv run pytest tests/test_grid.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'locfinder.grid'`

**Step 3: Write the implementation**

```python
# v2/locfinder/grid.py
"""Frozen raster grid contract for travel-time layers.

Square cells in a projected CRS (UTM 17N for the Triangle). Minutes are uint8:
0..254 minutes, NODATA (255) = unreachable / off-network / missing.
Row 0 is the north edge, matching GeoTIFF conventions.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
from pyproj import Transformer
from rasterio.crs import CRS
from rasterio.transform import from_origin

NODATA = 255
MAX_MINUTES = 254
DEFAULT_CRS = "EPSG:32617"  # UTM 17N


@dataclass(frozen=True)
class GridSpec:
    crs: str
    x_min: float
    y_max: float
    cell_m: float
    ncols: int
    nrows: int

    @property
    def x_max(self) -> float:
        return self.x_min + self.ncols * self.cell_m

    @property
    def y_min(self) -> float:
        return self.y_max - self.nrows * self.cell_m

    @classmethod
    def from_bbox_wgs84(
        cls, *, west: float, south: float, east: float, north: float,
        cell_m: float = 100.0, crs: str = DEFAULT_CRS,
    ) -> "GridSpec":
        to_proj = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
        corners = [(west, south), (west, north), (east, south), (east, north)]
        xs, ys = zip(*(to_proj.transform(lon, lat) for lon, lat in corners))
        x_min = math.floor(min(xs) / cell_m) * cell_m
        y_max = math.ceil(max(ys) / cell_m) * cell_m
        ncols = int(math.ceil((max(xs) - x_min) / cell_m))
        nrows = int(math.ceil((y_max - min(ys)) / cell_m))
        return cls(crs=crs, x_min=x_min, y_max=y_max, cell_m=cell_m, ncols=ncols, nrows=nrows)

    def cell_centers_xy(self) -> tuple[np.ndarray, np.ndarray]:
        cols = np.arange(self.ncols)
        rows = np.arange(self.nrows)
        x = self.x_min + (cols + 0.5) * self.cell_m
        y = self.y_max - (rows + 0.5) * self.cell_m
        xs, ys = np.meshgrid(x, y)
        return xs, ys

    def cell_centers_lonlat(self) -> tuple[np.ndarray, np.ndarray]:
        xs, ys = self.cell_centers_xy()
        to_wgs = Transformer.from_crs(self.crs, "EPSG:4326", always_xy=True)
        lons, lats = to_wgs.transform(xs, ys)
        return np.asarray(lons), np.asarray(lats)

    def rasterio_profile(self) -> dict:
        return {
            "driver": "GTiff",
            "dtype": "uint8",
            "count": 1,
            "width": self.ncols,
            "height": self.nrows,
            "crs": CRS.from_string(self.crs),
            "transform": from_origin(self.x_min, self.y_max, self.cell_m, self.cell_m),
            "nodata": NODATA,
            "compress": "deflate",
            "tiled": True,
            "blockxsize": 256,
            "blockysize": 256,
        }


def encode_minutes(seconds: np.ndarray) -> np.ndarray:
    """Seconds -> uint8 minutes; inf/nan -> NODATA; values above 254 min are capped."""
    s = np.asarray(seconds, dtype=np.float64)
    finite = np.isfinite(s)
    minutes = np.rint(np.where(finite, s, 0.0) / 60.0)
    minutes = np.clip(minutes, 0, MAX_MINUTES)
    out = minutes.astype(np.uint8)
    out[~finite] = NODATA
    return out
```

**Step 4: Run tests to verify they pass**

Run: `cd v2; uv run pytest tests/test_grid.py -v`
Expected: 5 passed

**Step 5: Commit**

```bash
git add v2/locfinder/grid.py v2/tests/test_grid.py
git commit -m "feat(v2): frozen UTM grid contract with uint8 minutes encoding"
```

---

## Task 2: Directed graph to CSR and transposed multi-source Dijkstra

This is the fix for Codex finding C1. "Minutes from every node to the nearest destination" must be computed on the **transposed** graph: an edge u→v with cost c means "from v's perspective, u can reach me in c", so arrival times are shortest paths from the destinations on Gᵀ. A tiny one-way graph is the regression test.

**Files:**
- Create: `v2/locfinder/traveltime/__init__.py` (empty)
- Create: `v2/locfinder/traveltime/csr.py`
- Create: `v2/locfinder/traveltime/arrival.py`
- Test: `v2/tests/test_arrival.py`

**Step 1: Write the failing tests**

```python
# v2/tests/test_arrival.py
import math

import networkx as nx
import numpy as np
import pytest

from locfinder.traveltime.csr import graph_to_csr
from locfinder.traveltime.arrival import arrival_seconds


def one_way_graph() -> nx.MultiDiGraph:
    """A -> B (60 s, one-way), B <-> C (30 s each way)."""
    G = nx.MultiDiGraph()
    for n, (x, y) in {"A": (0, 0), "B": (100, 0), "C": (200, 0)}.items():
        G.add_node(n, x=x, y=y)
    G.add_edge("A", "B", travel_time=60.0)
    G.add_edge("B", "C", travel_time=30.0)
    G.add_edge("C", "B", travel_time=30.0)
    return G


def test_csr_preserves_direction_and_weights():
    G = one_way_graph()
    csr, index = graph_to_csr(G, weight="travel_time")
    a, b, c = index["A"], index["B"], index["C"]
    assert csr[a, b] == 60.0
    assert csr[b, a] == 0.0          # no reverse edge stored
    assert csr[b, c] == 30.0 and csr[c, b] == 30.0


def test_arrival_to_destination_uses_transposed_graph():
    G = one_way_graph()
    csr, index = graph_to_csr(G, weight="travel_time")
    # destination B: A reaches B in 60 (A->B), C reaches B in 30 (C->B)
    t = arrival_seconds(csr, dest_idx=[index["B"]])
    assert t[index["A"]] == 60.0
    assert t[index["C"]] == 30.0
    assert t[index["B"]] == 0.0


def test_one_way_street_is_not_reversible():
    G = one_way_graph()
    csr, index = graph_to_csr(G, weight="travel_time")
    # destination A: nobody can reach A (A->B is one-way)
    t = arrival_seconds(csr, dest_idx=[index["A"]])
    assert t[index["A"]] == 0.0
    assert math.isinf(t[index["B"]]) and math.isinf(t[index["C"]])


def test_naive_outward_dijkstra_would_be_wrong():
    """Documents the CHCCS bug: outward search from the destination gives A a time to
    reach B of inf (wrong) and gives B a time to reach A of 60 (wrong)."""
    from scipy.sparse.csgraph import dijkstra
    G = one_way_graph()
    csr, index = graph_to_csr(G, weight="travel_time")
    outward = dijkstra(csr, directed=True, indices=[index["A"]], min_only=True)
    assert outward[index["B"]] == 60.0  # outward says B is 60 from A ...
    correct = arrival_seconds(csr, dest_idx=[index["A"]])
    assert math.isinf(correct[index["B"]])  # ... but B cannot reach A


def test_multi_source_takes_minimum_and_respects_cutoff():
    G = one_way_graph()
    csr, index = graph_to_csr(G, weight="travel_time")
    t = arrival_seconds(csr, dest_idx=[index["B"], index["C"]], cutoff_s=45.0)
    assert t[index["C"]] == 0.0 and t[index["B"]] == 0.0
    assert math.isinf(t[index["A"]])  # 60 s > cutoff 45 s
```

**Step 2: Run tests to verify they fail**

Run: `cd v2; uv run pytest tests/test_arrival.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'locfinder.traveltime'`

**Step 3: Write the implementation**

```python
# v2/locfinder/traveltime/csr.py
"""Convert a weighted networkx MultiDiGraph into a scipy CSR matrix.

Parallel edges keep the minimum weight. Direction is preserved exactly as in the
graph: no reverse edges are added here. Pedestrian graphs must be symmetrised by
the caller (see speeds.py), never drive or bike graphs.
"""
from __future__ import annotations

import numpy as np
import scipy.sparse as sp
import networkx as nx


def graph_to_csr(G: nx.MultiDiGraph, *, weight: str = "travel_time") -> tuple[sp.csr_matrix, dict]:
    nodes = list(G.nodes())
    index = {n: i for i, n in enumerate(nodes)}
    rows, cols, vals = [], [], []
    for u, v, data in G.edges(data=True):
        w = float(data[weight])
        if w <= 0 or not np.isfinite(w):
            raise ValueError(f"edge {u}->{v} has non-positive or non-finite {weight}={w}")
        rows.append(index[u]); cols.append(index[v]); vals.append(w)
    n = len(nodes)
    coo = sp.coo_matrix((vals, (rows, cols)), shape=(n, n))
    # coo->csr sums duplicates; we want the minimum for parallel edges
    if coo.nnz != len(set(zip(rows, cols))):
        best: dict[tuple[int, int], float] = {}
        for r, c, w in zip(rows, cols, vals):
            best[(r, c)] = min(w, best.get((r, c), np.inf))
        rows, cols = zip(*best.keys()); vals = list(best.values())
        coo = sp.coo_matrix((vals, (rows, cols)), shape=(n, n))
    return coo.tocsr(), index
```

```python
# v2/locfinder/traveltime/arrival.py
"""Multi-source arrival times: seconds from every node to the NEAREST destination.

Computed as single-source shortest paths from the destinations on the TRANSPOSED
graph (Codex pass-1 finding C1). Unreachable nodes are +inf.
"""
from __future__ import annotations

import numpy as np
import scipy.sparse as sp
from scipy.sparse.csgraph import dijkstra


def arrival_seconds(csr: sp.csr_matrix, *, dest_idx, cutoff_s: float | None = None) -> np.ndarray:
    dest = np.asarray(list(dest_idx), dtype=np.int64)
    if dest.size == 0:
        return np.full(csr.shape[0], np.inf)
    transposed = csr.transpose().tocsr()
    limit = np.inf if cutoff_s is None else float(cutoff_s)
    dist = dijkstra(transposed, directed=True, indices=dest, min_only=True, limit=limit)
    return np.asarray(dist, dtype=np.float64)
```

**Step 4: Run tests to verify they pass**

Run: `cd v2; uv run pytest tests/test_arrival.py -v`
Expected: 5 passed

**Step 5: Commit**

```bash
git add v2/locfinder/traveltime/ v2/tests/test_arrival.py
git commit -m "feat(v2): transposed-graph multi-source arrival times with one-way regression test"
```

---

## Task 3: Speed model, mode filters, and nearest-edge snapping to the grid

Ports the CHCCS speed constants (documented sources) and nearest-edge snapping, corrected for arrival semantics: a cell snapped to edge u→v at fraction f (from u) reaches a destination either forward via v, cost (1−f)·t(u→v) + T[v], or backward via u, cost f·t(v→u) + T[u] **only if the reverse edge exists**. Walk graphs are symmetrised (pedestrians ignore one-way); bike and drive are not.

**Files:**
- Create: `v2/locfinder/traveltime/speeds.py`
- Create: `v2/locfinder/traveltime/snap.py`
- Create: `v2/locfinder/traveltime/layer.py`
- Test: `v2/tests/test_snap_layer.py`

**Step 1: Write the failing tests**

```python
# v2/tests/test_snap_layer.py
import math

import networkx as nx
import numpy as np

from locfinder.grid import GridSpec, NODATA
from locfinder.traveltime.csr import graph_to_csr
from locfinder.traveltime.arrival import arrival_seconds
from locfinder.traveltime.speeds import add_travel_times, symmetrise, MODE_SPEED_MPS
from locfinder.traveltime.snap import EdgeIndex, cell_seconds_from_arrival


def line_graph_utm() -> nx.MultiDiGraph:
    """Three nodes on a line in projected metres: A(0,0) -> B(1000,0) one-way, B<->C(2000,0)."""
    G = nx.MultiDiGraph()
    for n, (x, y) in {"A": (0.0, 0.0), "B": (1000.0, 0.0), "C": (2000.0, 0.0)}.items():
        G.add_node(n, x=x, y=y)
    G.add_edge("A", "B", length=1000.0, highway="residential", oneway=True)
    G.add_edge("B", "C", length=1000.0, highway="residential", oneway=False)
    G.add_edge("C", "B", length=1000.0, highway="residential", oneway=False)
    G.graph["crs"] = "EPSG:32617"
    return G


def test_add_travel_times_uses_mode_speed():
    G = add_travel_times(line_graph_utm(), mode="walk")
    t = G.edges["A", "B", 0]["travel_time"]
    assert math.isclose(t, 1000.0 / MODE_SPEED_MPS["walk"], rel_tol=1e-6)


def test_symmetrise_adds_missing_reverse_edges_only():
    G = symmetrise(add_travel_times(line_graph_utm(), mode="walk"))
    assert G.has_edge("B", "A")
    assert G.number_of_edges() == 4


def test_snap_point_interpolates_toward_reachable_endpoint():
    G = add_travel_times(line_graph_utm(), mode="drive")
    csr, index = graph_to_csr(G)
    T = arrival_seconds(csr, dest_idx=[index["C"]])          # dest at C
    idx = EdgeIndex.from_graph(G, index)
    # a cell 10 m north of the midpoint of A->B (one-way): must go forward to B then to C
    xs = np.array([500.0]); ys = np.array([10.0])
    secs = cell_seconds_from_arrival(idx, T, xs, ys, mode="drive", max_access_m=200.0)
    t_ab = G.edges["A", "B", 0]["travel_time"]; t_bc = G.edges["B", "C", 0]["travel_time"]
    expected_network = 0.5 * t_ab + t_bc
    assert secs[0] > expected_network                       # plus a small access leg
    assert secs[0] < expected_network + 60.0


def test_snap_point_far_from_network_is_unreachable():
    G = add_travel_times(line_graph_utm(), mode="walk")
    csr, index = graph_to_csr(symmetrise(G))
    T = arrival_seconds(csr, dest_idx=[index["C"]])
    idx = EdgeIndex.from_graph(G, index)
    secs = cell_seconds_from_arrival(idx, T, np.array([500.0]), np.array([900.0]), mode="walk", max_access_m=200.0)
    assert math.isinf(secs[0])


def test_backward_interpolation_requires_reverse_edge():
    G = add_travel_times(line_graph_utm(), mode="drive")
    csr, index = graph_to_csr(G)
    T = arrival_seconds(csr, dest_idx=[index["A"]])          # dest at A: only A itself
    idx = EdgeIndex.from_graph(G, index)
    # a cell on A->B near A: cannot drive backward along the one-way to A
    secs = cell_seconds_from_arrival(idx, T, np.array([100.0]), np.array([0.0]), mode="drive", max_access_m=200.0)
    assert math.isinf(secs[0])
```

**Step 2: Run tests to verify they fail**

Run: `cd v2; uv run pytest tests/test_snap_layer.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'locfinder.traveltime.speeds'`

**Step 3: Write the implementation**

```python
# v2/locfinder/traveltime/speeds.py
"""Static speed model ported from CHCCS_geospatial/src/school_desert.py (documented
sources there: MUTCD 4E.06, FHWA-HRT-06-042, HCM6 Ch.16/19/20). Adult walk speed
replaces the K-5 value. These are PRIORS; Gate G1 measures them against Valhalla.
"""
from __future__ import annotations

import networkx as nx

MODE_SPEED_MPS = {
    "walk": 1.40,   # adult, ~3.1 mph
    "bike": 4.50,   # ~10 mph, utility cycling
}

# Free-flow "friction" speeds by highway tag (mph), mid-block delay included.
DRIVE_FRICTION_MPH = {
    "motorway": 62, "motorway_link": 40, "trunk": 45, "trunk_link": 35,
    "primary": 35, "primary_link": 30, "secondary": 30, "secondary_link": 25,
    "tertiary": 25, "tertiary_link": 22, "unclassified": 22, "residential": 20,
    "living_street": 12, "service": 10,
}
DEFAULT_DRIVE_FRICTION_MPH = 20
MPH_TO_MPS = 0.44704

# Highway values each mode may use (explicit, so the filter is auditable).
DRIVE_HIGHWAYS = set(DRIVE_FRICTION_MPH)
BIKE_EXCLUDE = {"motorway", "motorway_link", "steps"}
WALK_EXCLUDE = {"motorway", "motorway_link", "trunk", "trunk_link"}

ACCESS_SPEED_FACTOR = {"walk": 0.9, "bike": 0.8, "drive": 0.2}


def _highway(data) -> str:
    h = data.get("highway", "unclassified")
    return h[0] if isinstance(h, list) else h


def edge_allowed(data, mode: str) -> bool:
    h = _highway(data)
    if mode == "drive":
        return h in DRIVE_HIGHWAYS
    if mode == "bike":
        return h not in BIKE_EXCLUDE
    if mode == "walk":
        return h not in WALK_EXCLUDE
    raise ValueError(mode)


def add_travel_times(G: nx.MultiDiGraph, *, mode: str) -> nx.MultiDiGraph:
    """Set `travel_time` (seconds) on every edge from `length` (metres) and mode speed.
    Edges not allowed for the mode are removed. Returns the same graph object."""
    to_remove = []
    for u, v, k, data in G.edges(keys=True, data=True):
        if not edge_allowed(data, mode):
            to_remove.append((u, v, k)); continue
        length = float(data["length"])
        if mode == "drive":
            mph = DRIVE_FRICTION_MPH.get(_highway(data), DEFAULT_DRIVE_FRICTION_MPH)
            speed = mph * MPH_TO_MPS
        else:
            speed = MODE_SPEED_MPS[mode]
        data["travel_time"] = max(length / speed, 0.1)
    G.remove_edges_from(to_remove)
    return G


def symmetrise(G: nx.MultiDiGraph) -> nx.MultiDiGraph:
    """Add a reverse edge wherever one is missing. ONLY valid for walk graphs."""
    missing = []
    for u, v, data in G.edges(data=True):
        if not G.has_edge(v, u):
            missing.append((v, u, dict(data)))
    for v, u, data in missing:
        G.add_edge(v, u, **data)
    return G


def access_speed_mps(mode: str) -> float:
    base = DEFAULT_DRIVE_FRICTION_MPH * MPH_TO_MPS if mode == "drive" else MODE_SPEED_MPS[mode]
    return ACCESS_SPEED_FACTOR[mode] * base
```

```python
# v2/locfinder/traveltime/snap.py
"""Nearest-edge snapping of grid cells onto a projected (metre) graph, with
arrival-time interpolation along the matched edge. Port of CHCCS
school_desert.py:_build_edge_index / compute_travel_scores, corrected for
arrival (to-destination) semantics and one-way edges.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import shapely
from shapely.geometry import LineString
import networkx as nx

from .speeds import access_speed_mps


@dataclass
class EdgeIndex:
    tree: shapely.STRtree
    geoms: np.ndarray          # object array of LineString (metres)
    start_idx: np.ndarray      # node index at geometry start (fraction 0)
    end_idx: np.ndarray        # node index at geometry end (fraction 1)
    fwd_time: np.ndarray       # seconds start->end, inf if no such edge
    rev_time: np.ndarray       # seconds end->start, inf if no such edge

    @classmethod
    def from_graph(cls, G: nx.MultiDiGraph, index: dict) -> "EdgeIndex":
        geoms, starts, ends, fwd, rev = [], [], [], [], []
        seen: dict[tuple, int] = {}
        for u, v, k, data in G.edges(keys=True, data=True):
            key = (min(u, v), max(u, v), k)
            t = float(data["travel_time"])
            if key not in seen:
                geom = data.get("geometry")
                if geom is None:
                    geom = LineString([(G.nodes[u]["x"], G.nodes[u]["y"]), (G.nodes[v]["x"], G.nodes[v]["y"])])
                g0 = geom.coords[0]
                if abs(g0[0] - G.nodes[u]["x"]) + abs(g0[1] - G.nodes[u]["y"]) < 1e-6:
                    s, e = u, v
                else:
                    s, e = v, u
                seen[key] = len(geoms)
                geoms.append(geom); starts.append(index[s]); ends.append(index[e])
                fwd.append(np.inf); rev.append(np.inf)
            i = seen[key]
            if index[u] == starts[i]:
                fwd[i] = min(fwd[i], t)
            else:
                rev[i] = min(rev[i], t)
        arr = np.array(geoms, dtype=object)
        return cls(shapely.STRtree(list(arr)), arr, np.array(starts), np.array(ends),
                   np.array(fwd, dtype=np.float64), np.array(rev, dtype=np.float64))


def cell_seconds_from_arrival(idx: EdgeIndex, T: np.ndarray, xs: np.ndarray, ys: np.ndarray,
                              *, mode: str, max_access_m: float) -> np.ndarray:
    """Seconds from each (x, y) metre point to the nearest destination given node
    arrival times T (inf = unreachable). Points farther than max_access_m from any
    edge are inf."""
    pts = shapely.points(np.asarray(xs, float).ravel(), np.asarray(ys, float).ravel())
    nearest = idx.tree.nearest(pts)
    geoms = idx.geoms[nearest]
    access_m = shapely.distance(pts, geoms)
    frac = shapely.line_locate_point(geoms, pts, normalized=True)
    s_idx, e_idx = idx.start_idx[nearest], idx.end_idx[nearest]
    via_end = (1.0 - frac) * idx.fwd_time[nearest] + T[e_idx]      # travel forward to end node
    via_start = frac * idx.rev_time[nearest] + T[s_idx]            # travel backward only if reverse edge exists
    network = np.minimum(via_end, via_start)
    total = network + access_m / access_speed_mps(mode)
    total = np.where(access_m > max_access_m, np.inf, total)
    return total.reshape(np.shape(xs))
```

```python
# v2/locfinder/traveltime/layer.py
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


def build_layer(G, csr, index, grid: GridSpec, *, dest_idx, mode: str,
                cutoff_min: float = 120.0, max_access_m: float = 200.0, timings: dict | None = None) -> np.ndarray:
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
    profile = grid.rasterio_profile()
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(arr, 1)
        dst.update_tags(**tags)   # mode, category, profile, grid_version, direction=arrival, built_at
```

**Step 4: Run tests to verify they pass**

Run: `cd v2; uv run pytest -v`
Expected: all tests pass (grid 5, arrival 5, snap/layer 5)

**Step 5: Commit**

```bash
git add v2/locfinder/traveltime/ v2/tests/test_snap_layer.py
git commit -m "feat(v2): speed model, mode filters, arrival-aware nearest-edge snapping, layer writer"
```

---

## Task 4: Acquire slice data (registry first)

**Files:**
- Modify: `docs/experiments/source-registry.md` (add rows BEFORE downloading)
- Create: `v2/scripts/fetch_slice_data.sh` (runs in WSL)
- Create: `v2/scripts/fetch_places.py` (Overture + OSM POIs)

**Step 1: Add registry rows**

Append to `docs/experiments/source-registry.md` (fill the access date):
```markdown
| Geofabrik North Carolina OSM extract | https://download.geofabrik.de/north-america/us/north-carolina-latest.osm.pbf | ODbL 1.0 (© OpenStreetMap contributors) | store ✓ / display ✓ (attribution) / commingle: keep separable (04 §3.8) / commercial ✓ under ODbL | 2026-11-0_ | routing graphs and OSM POIs |
| Overture Maps Places (release 2026-10-21.0 or current) | https://docs.overturemaps.org/guides/places/ ; CLI https://github.com/OvertureMaps/overturemaps-py | CDLA-Permissive-2.0 (Foursquare rows Apache-2.0 with NOTICE) | store ✓ / display ✓ / commingle ✓ / commercial ✓ | 2026-11-0_ | per-row licence must be present or row is quarantined (Task 10) |
| Triangle GTFS feeds (GoTriangle, GoRaleigh, GoDurham, GoCary, Chapel Hill Transit, Duke, NCSU Wolfline) | https://gotriangle.org/developer-resources/ (record each feed URL below when fetched) | CC BY 3.0 (per GoTriangle developer page; verify per feed) | store ✓ / display ✓ (attribution) / commingle ✓ / commercial ✓ | 2026-11-0_ | transit experiment only |
```

**Step 2: Write the WSL fetch script**

```bash
# v2/scripts/fetch_slice_data.sh  -- run inside WSL2 Ubuntu from the repo root
set -euo pipefail
REPO=/mnt/c/Users/arikt/documents/github/distanceFinder
DATA=$REPO/v2/data
mkdir -p "$DATA/raw" "$DATA/slice" "$DATA/gtfs"
cd "$DATA/raw"
# 1. NC extract (~410 MB)
[ -f north-carolina-latest.osm.pbf ] || wget -q --show-progress https://download.geofabrik.de/north-america/us/north-carolina-latest.osm.pbf
# 2. osmium (no sudo needed if already present; otherwise apt)
command -v osmium >/dev/null || sudo apt-get install -y osmium-tool
# 3. clip to slice bbox and export roads-only XML for osmnx
osmium extract -b -79.15,35.80,-78.55,36.15 north-carolina-latest.osm.pbf -o "$DATA/slice/slice.osm.pbf" --overwrite
osmium tags-filter "$DATA/slice/slice.osm.pbf" w/highway -o "$DATA/slice/slice-roads.osm.pbf" --overwrite
osmium cat "$DATA/slice/slice-roads.osm.pbf" -o "$DATA/slice/slice-roads.osm" --overwrite
ls -la "$DATA/slice"
# 4. GTFS: open https://gotriangle.org/developer-resources/ in a browser, copy each static GTFS zip URL
#    into v2/data/gtfs/feeds.txt (one per line), then:
if [ -f "$DATA/gtfs/feeds.txt" ]; then
  while read -r url; do [ -z "$url" ] && continue; (cd "$DATA/gtfs" && wget -q --content-disposition "$url"); done < "$DATA/gtfs/feeds.txt"
  ls -la "$DATA/gtfs"
else
  echo "NOTE: create v2/data/gtfs/feeds.txt with the GTFS zip URLs from gotriangle.org/developer-resources, then rerun."
fi
```

Run: `wsl -e bash -lc "bash /mnt/c/Users/arikt/documents/github/distanceFinder/v2/scripts/fetch_slice_data.sh"`
Expected: `slice.osm.pbf` (tens of MB), `slice-roads.osm` (XML, a few hundred MB), and the GTFS note or zips.

**Step 3: Fetch places (Windows, uv)**

```python
# v2/scripts/fetch_places.py
"""Overture places + OSM POIs for the slice. Writes GeoParquet under v2/data/slice/."""
import subprocess, sys
from pathlib import Path

BBOX = "-79.15,35.80,-78.55,36.15"
OUT = Path(__file__).resolve().parents[1] / "data" / "slice"
OUT.mkdir(parents=True, exist_ok=True)

# Overture Places via official CLI (GeoParquet, per-row sources[].license retained)
subprocess.run([sys.executable, "-m", "overturemaps.cli", "download", f"--bbox={BBOX}", "-f", "geoparquet",
                "--type=place", "-o", str(OUT / "overture_places.parquet")], check=True)

# OSM POIs for the wedge categories via QuackOSM (reads the clipped PBF, no Overpass)
import quackosm as qosm
tags = {
    "leisure": ["park", "playground", "nature_reserve"],
    "shop": ["supermarket", "greengrocer", "convenience"],
    "amenity": ["cafe", "pharmacy", "school", "library"],
    "highway": ["bus_stop"],
    "railway": ["station", "tram_stop"],
    "public_transport": ["platform", "station"],
}
gdf = qosm.convert_pbf_to_geodataframe(str(OUT / "slice.osm.pbf"), tags_filter=tags, keep_all_tags=True)
gdf.to_parquet(OUT / "osm_pois.parquet")
print("overture:", (OUT / "overture_places.parquet").stat().st_size, "bytes; osm pois:", len(gdf))
```

Run: `cd v2; uv run python scripts/fetch_places.py`
Expected: both parquet files written; a count of OSM POIs in the thousands.

**Step 4: Commit scripts and registry (not data)**

```bash
git add v2/scripts/fetch_slice_data.sh v2/scripts/fetch_places.py docs/experiments/source-registry.md
git commit -m "feat(v2): slice data acquisition scripts and source registry rows"
```

---

## Task 5: Valhalla self-host in WSL2 Docker with an 8 GB memory cap (Gate G2, part 1)

**Files:**
- Create: `v2/infra/valhalla/docker-compose.yml`
- Create: `v2/infra/valhalla/README.md`
- Create: `docs/experiments/g2-valhalla.md`

**Step 1: Compose file**

```yaml
# v2/infra/valhalla/docker-compose.yml
# Run from WSL: cd /mnt/c/Users/arikt/documents/github/distanceFinder/v2/infra/valhalla && docker compose up -d
services:
  valhalla:
    image: ghcr.io/valhalla/valhalla-scripted:latest
    container_name: valhalla-slice
    ports: ["8002:8002"]
    volumes:
      - ../../data/valhalla_custom_files:/custom_files
    environment:
      - use_tiles_ignore_pbf=False
      - force_rebuild=False
      - build_elevation=False
      - build_admins=True
      - build_time_zones=True
      - build_transit=True            # reads /custom_files/gtfs_feeds/*.zip
      - serve_tiles=True
      - server_threads=4
      - update_existing_config=True
    mem_limit: 8g                     # emulate the Tier-1 VPS
    cpus: 2
```

`v2/infra/valhalla/README.md`:
```markdown
Put the OSM extract(s) in v2/data/valhalla_custom_files/ (the slice PBF for G2; NC later) and GTFS zips
in v2/data/valhalla_custom_files/gtfs_feeds/. First `docker compose up` builds tiles (minutes for the
slice, longer for NC); subsequent runs serve. Config is /custom_files/valhalla.json; after the first
build raise `service_limits.isochrone.max_locations` (default is small) and `max_time` if the category
experiment needs it, then `docker compose restart`. Verify env-var names against
https://github.com/valhalla/valhalla/blob/master/docker/README.md if the container exits early.
```

**Step 2: Build and serve**

Run (WSL):
```bash
mkdir -p /mnt/c/Users/arikt/documents/github/distanceFinder/v2/data/valhalla_custom_files/gtfs_feeds
cp /mnt/c/Users/arikt/documents/github/distanceFinder/v2/data/slice/slice.osm.pbf /mnt/c/Users/arikt/documents/github/distanceFinder/v2/data/valhalla_custom_files/
cp /mnt/c/Users/arikt/documents/github/distanceFinder/v2/data/gtfs/*.zip /mnt/c/Users/arikt/documents/github/distanceFinder/v2/data/valhalla_custom_files/gtfs_feeds/ 2>/dev/null || true
cd /mnt/c/Users/arikt/documents/github/distanceFinder/v2/infra/valhalla
time docker compose up -d && docker compose logs -f --tail=50   # Ctrl-C once "Tile loading complete"/"serving" appears
```
Record: wall-clock build time, `du -sh ../../data/valhalla_custom_files`, and peak RSS from `docker stats --no-stream valhalla-slice` during build and while serving.

**Step 3: Smoke-test the API, including arrival semantics and GeoTIFF output**

```bash
curl -s http://localhost:8002/status | head -c 300; echo
# forward (departure) isochrone
curl -s http://localhost:8002/isochrone -d '{"locations":[{"lat":35.9049,"lon":-79.0469}],"costing":"auto","contours":[{"time":25}],"polygons":true}' | head -c 300; echo
# arrival (reverse) isochrone: who can REACH the location in 25 min
curl -s http://localhost:8002/isochrone -d '{"locations":[{"lat":35.9049,"lon":-79.0469}],"costing":"auto","contours":[{"time":25}],"polygons":true,"reverse":true}' | head -c 300; echo
# GeoTIFF travel-time grid (verify support: expect binary GeoTIFF, else an error JSON)
curl -s -o /tmp/iso.tif -w '%{http_code} %{content_type}\n' http://localhost:8002/isochrone -d '{"locations":[{"lat":35.9049,"lon":-79.0469}],"costing":"auto","contours":[{"time":45}],"format":"geotiff","reverse":true}'
file /tmp/iso.tif
```
Expected: status JSON; two GeoJSON responses whose polygons differ (one-ways make them asymmetric); `200 image/tiff` and `TIFF image data` for the GeoTIFF. If `format: geotiff` is rejected, record the Valhalla version and fall back to per-POI polygon isochrones in Task 7.

**Step 4: Record results**

Create `docs/experiments/g2-valhalla.md` with: image digest and Valhalla version (`docker inspect`), build time, tile size, build-peak and serving RSS, whether transit tiles built (log line), whether GeoTIFF output works, and the three curl results. Mark "slice" vs "NC" rows; NC build is repeated in Phase 1 before VPS deployment.

**Step 5: Commit**

```bash
git add v2/infra/valhalla/ docs/experiments/g2-valhalla.md
git commit -m "feat(v2): Valhalla self-host compose for the slice with 8 GB cap; G2 part 1 results"
```

---

## Task 6: Anchor latency benchmark (Gate G2, part 2)

**Files:**
- Create: `v2/spikes/g2_anchor_bench.py`
- Modify: `docs/experiments/g2-valhalla.md`

**Step 1: Write the benchmark**

```python
# v2/spikes/g2_anchor_bench.py
"""p50/p95 isochrone latency for 100 random slice anchors x modes x minutes at concurrency 1 and 8."""
import asyncio, json, random, statistics, time, sys
from pathlib import Path
import httpx

URL = "http://localhost:8002/isochrone"
BBOX = (-79.15, 35.80, -78.55, 36.15)
random.seed(42)
ANCHORS = [(random.uniform(BBOX[1], BBOX[3]), random.uniform(BBOX[0], BBOX[2])) for _ in range(100)]
CASES = [("auto", 25), ("auto", 45), ("bicycle", 15), ("pedestrian", 15)]

async def one(client, lat, lon, costing, minutes):
    body = {"locations": [{"lat": lat, "lon": lon}], "costing": costing,
            "contours": [{"time": minutes}], "polygons": True, "reverse": True}
    t0 = time.perf_counter()
    r = await client.post(URL, json=body, timeout=60)
    dt = time.perf_counter() - t0
    return dt, r.status_code, len(r.content)

async def run(concurrency):
    rows = []
    sem = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient() as client:
        async def guarded(a, c):
            async with sem:
                return (c, *await one(client, a[0], a[1], c[0], c[1]))
        results = await asyncio.gather(*[guarded(a, c) for c in CASES for a in ANCHORS], return_exceptions=True)
    for res in results:
        if isinstance(res, Exception):
            rows.append(("error", None, None, str(res))); continue
        rows.append(res)
    return rows

def summarize(rows, concurrency, out):
    out.append(f"\n### concurrency {concurrency}\n\n| costing | minutes | n | ok | p50 s | p95 s | max s | median bytes |\n|---|---|---|---|---|---|---|---|")
    for case in CASES:
        lat = [r[1] for r in rows if r[0] == case and r[2] == 200]
        bad = sum(1 for r in rows if r[0] == case and r[2] != 200)
        sizes = [r[3] for r in rows if r[0] == case and r[2] == 200]
        if not lat: out.append(f"| {case[0]} | {case[1]} | 0 | 0 | - | - | - | - |"); continue
        lat.sort()
        out.append(f"| {case[0]} | {case[1]} | {len(lat)+bad} | {len(lat)} | {statistics.median(lat):.3f} | {lat[int(0.95*len(lat))-1]:.3f} | {lat[-1]:.3f} | {int(statistics.median(sizes))} |")

if __name__ == "__main__":
    out = ["## Anchor latency (Task 6)", f"anchors={len(ANCHORS)} cases={CASES}"]
    for c in (1, 8):
        rows = asyncio.run(run(c)); summarize(rows, c, out)
    text = "\n".join(out)
    print(text)
    Path("docs/experiments/g2-valhalla.md").open("a", encoding="utf-8").write("\n" + text + "\n")
```

**Step 2: Run it** (from repo root, Valhalla serving)

Run: `cd v2; uv run python spikes/g2_anchor_bench.py` and in WSL during the run: `docker stats --no-stream valhalla-slice` (record RSS).
Expected: tables appended to `docs/experiments/g2-valhalla.md`. Pass criterion: auto 25 min p95 < 0.8 s and auto 45 min p95 < 2 s at concurrency 8 (synthesis G2). Record pass/fail explicitly.

**Step 3: Commit**

```bash
git add v2/spikes/g2_anchor_bench.py docs/experiments/g2-valhalla.md
git commit -m "exp(g2): anchor isochrone latency benchmark results"
```

---

## Task 7: Category layer from Valhalla (reference for Gate G1)

Builds "minutes to nearest grocery" for the slice from Valhalla arrival isochrones, resampled onto the frozen grid. Two methods, use the first that works: (A) one multi-location arrival isochrone with `format: geotiff` (requires raising `service_limits.isochrone.max_locations` in `valhalla.json`); (B) per-POI arrival isochrone GeoTIFFs combined by per-cell minimum.

**Files:**
- Create: `v2/spikes/g1_valhalla_layer.py`
- Create: `v2/locfinder/places/__init__.py` (empty)
- Create: `v2/locfinder/places/categories.py`

**Step 1: Category mapping (small, testable later in Task 10)**

```python
# v2/locfinder/places/categories.py
"""Wedge categories -> Overture primary categories and OSM tags. Keep explicit."""
WEDGE_CATEGORIES = {
    "grocery":    {"overture": {"grocery_store", "supermarket"}, "osm": {("shop", "supermarket"), ("shop", "greengrocer")}},
    "park":       {"overture": {"park"},                          "osm": {("leisure", "park"), ("leisure", "nature_reserve")}},
    "playground": {"overture": {"playground"},                    "osm": {("leisure", "playground")}},
    "coffee":     {"overture": {"coffee_shop", "cafe"},           "osm": {("amenity", "cafe")}},
    "pharmacy":   {"overture": {"pharmacy", "drugstore"},         "osm": {("amenity", "pharmacy")}},
    "school":     {"overture": {"elementary_school", "school"},   "osm": {("amenity", "school")}},
    "library":    {"overture": {"library"},                       "osm": {("amenity", "library")}},
    "transit_stop": {"overture": {"bus_stop", "bus_station", "train_station"}, "osm": {("highway", "bus_stop"), ("railway", "station")}},
}
```

**Step 2: Write the spike**

```python
# v2/spikes/g1_valhalla_layer.py
"""Reference layer: minutes-to-nearest-<category> by Valhalla arrival isochrones, on the frozen grid."""
import io, json, sys, time
from pathlib import Path
import httpx, numpy as np, rasterio
from rasterio.warp import reproject, Resampling
import geopandas as gpd

from locfinder.grid import GridSpec, NODATA, encode_minutes
from locfinder.places.categories import WEDGE_CATEGORIES

CATEGORY = sys.argv[1] if len(sys.argv) > 1 else "grocery"
MODE = sys.argv[2] if len(sys.argv) > 2 else "pedestrian"   # auto|bicycle|pedestrian
MAX_MIN = 60
URL = "http://localhost:8002/isochrone"
DATA = Path(__file__).resolve().parents[1] / "data"
OUT = DATA / "layers"; OUT.mkdir(exist_ok=True)
grid = GridSpec.from_bbox_wgs84(west=-79.15, south=35.80, east=-78.55, north=36.15, cell_m=100)

places = gpd.read_parquet(DATA / "slice" / "overture_places.parquet")
cats = WEDGE_CATEGORIES[CATEGORY]["overture"]
sel = places[places["categories"].apply(lambda c: isinstance(c, dict) and c.get("primary") in cats)]
pts = [(float(g.y), float(g.x)) for g in sel.geometry.centroid]
print(f"{CATEGORY}: {len(pts)} Overture places")

def geotiff_minutes(locations):
    body = {"locations": [{"lat": a, "lon": b} for a, b in locations], "costing": MODE,
            "contours": [{"time": MAX_MIN}], "format": "geotiff", "reverse": True}
    r = httpx.post(URL, json=body, timeout=600); r.raise_for_status()
    with rasterio.open(io.BytesIO(r.content)) as src:
        arr = src.read(1).astype("float64")        # Valhalla grid of seconds (verify units from tags!)
        nod = src.nodata
        arr[arr == nod] = np.inf
        dst = np.full((grid.nrows, grid.ncols), np.inf)
        reproject(arr, dst, src_transform=src.transform, src_crs=src.crs,
                  dst_transform=grid.rasterio_profile()["transform"], dst_crs=grid.crs,
                  resampling=Resampling.nearest, src_nodata=np.inf, dst_nodata=np.inf)
    return dst

t0 = time.perf_counter()
try:
    secs = geotiff_minutes(pts)                       # method A: one call, many locations
    method = "A: single multi-location arrival isochrone"
except httpx.HTTPStatusError as e:
    print("multi-location failed:", e.response.text[:200]); method = "B: per-POI min"
    secs = np.full((grid.nrows, grid.ncols), np.inf)
    for i, p in enumerate(pts):
        secs = np.minimum(secs, geotiff_minutes([p]))
        if i % 25 == 0: print(i, "/", len(pts))
dt = time.perf_counter() - t0
arr = encode_minutes(secs)
path = OUT / f"valhalla_{CATEGORY}_{MODE}.tif"
with rasterio.open(path, "w", **grid.rasterio_profile()) as dst:
    dst.write(arr, 1); dst.update_tags(engine="valhalla", method=method, category=CATEGORY, mode=MODE, direction="arrival", built_s=f"{dt:.1f}")
print(f"wrote {path} in {dt:.1f}s via {method}; reachable cells: {(arr != NODATA).mean():.1%}")
```

**Step 3: Run for grocery/pedestrian and grocery/auto**

Run: `cd v2; uv run python spikes/g1_valhalla_layer.py grocery pedestrian; uv run python spikes/g1_valhalla_layer.py grocery auto`
Expected: two GeoTIFFs under `v2/data/layers/`, build time printed. Record both times and the method used in `docs/experiments/g1-routing.md` (create the file with a "Reference layers" section). Check Valhalla's GeoTIFF units (seconds vs minutes) from the response tags and fix the conversion if needed before proceeding.

**Step 4: Commit**

```bash
git add v2/spikes/g1_valhalla_layer.py v2/locfinder/places/ docs/experiments/g1-routing.md
git commit -m "exp(g1): Valhalla arrival-isochrone category layers on the frozen grid"
```

---

## Task 8: Category layer from the own graph, and the comparison (Gate G1)

**Files:**
- Create: `v2/spikes/g1_own_graph_layer.py`
- Create: `v2/spikes/g1_compare.py`
- Modify: `docs/experiments/g1-routing.md`

**Step 1: Own-graph layer with stage timings**

```python
# v2/spikes/g1_own_graph_layer.py
import sys, time, json
from pathlib import Path
import numpy as np, geopandas as gpd, osmnx as ox, rasterio

from locfinder.grid import GridSpec, NODATA
from locfinder.traveltime.speeds import add_travel_times, symmetrise
from locfinder.traveltime.csr import graph_to_csr
from locfinder.traveltime.layer import build_layer, write_layer
from locfinder.places.categories import WEDGE_CATEGORIES

CATEGORY = sys.argv[1] if len(sys.argv) > 1 else "grocery"
MODE = sys.argv[2] if len(sys.argv) > 2 else "walk"          # walk|bike|drive
DATA = Path(__file__).resolve().parents[1] / "data"
grid = GridSpec.from_bbox_wgs84(west=-79.15, south=35.80, east=-78.55, north=36.15, cell_m=100)
timings = {}

t = time.perf_counter()
G = ox.graph_from_xml(DATA / "slice" / "slice-roads.osm", simplify=True, retain_all=False)
timings["load_xml_s"] = time.perf_counter() - t; t = time.perf_counter()
G = ox.project_graph(G, to_crs=grid.crs)
G = add_travel_times(G, mode=MODE)
if MODE == "walk":
    G = symmetrise(G)
# drop nodes left isolated by the mode filter
G.remove_nodes_from([n for n, d in G.degree() if d == 0])
timings["prepare_graph_s"] = time.perf_counter() - t; t = time.perf_counter()
csr, index = graph_to_csr(G)
timings["csr_s"] = time.perf_counter() - t; t = time.perf_counter()

places = gpd.read_parquet(DATA / "slice" / "overture_places.parquet").to_crs(grid.crs)
cats = WEDGE_CATEGORIES[CATEGORY]["overture"]
sel = places[places["categories"].apply(lambda c: isinstance(c, dict) and c.get("primary") in cats)]
xs = sel.geometry.centroid.x.values; ys = sel.geometry.centroid.y.values
dest_nodes = ox.nearest_nodes(G, xs, ys)
dest_idx = sorted({index[n] for n in dest_nodes})
timings["snap_pois_s"] = time.perf_counter() - t
print(f"nodes={G.number_of_nodes()} edges={G.number_of_edges()} dests={len(dest_idx)}")

arr = build_layer(G, csr, index, grid, dest_idx=dest_idx, mode=MODE, timings=timings)
path = DATA / "layers" / f"own_{CATEGORY}_{MODE}.tif"
write_layer(path, arr, grid, tags=dict(engine="own-csgraph-transposed", category=CATEGORY, mode=MODE, direction="arrival", **{k: f"{v:.2f}" for k, v in timings.items()}))
print(json.dumps(timings, indent=1)); print("reachable:", f"{(arr != NODATA).mean():.1%}")
```

**Step 2: Comparison with owner criterion (decision 12)**

```python
# v2/spikes/g1_compare.py
"""Compare own-graph vs Valhalla minutes rasters near user thresholds."""
import sys, json
from pathlib import Path
import numpy as np, rasterio
from locfinder.grid import NODATA

own, ref = (rasterio.open(p).read(1) for p in sys.argv[1:3])
label = sys.argv[3] if len(sys.argv) > 3 else ""
THRESHOLDS = [10, 15, 20, 30, 45]
both = (own != NODATA) & (ref != NODATA)
o, r = own[both].astype(float), ref[both].astype(float)
lines = [f"### {label}", f"cells compared: {both.sum()}  own-only reachable: {((own!=NODATA)&(ref==NODATA)).sum()}  ref-only reachable: {((own==NODATA)&(ref!=NODATA)).sum()}",
         "", "| T (min) | n near T (ref in [0.8T,1.2T]) | median abs err (min) | p90 abs err | median/T | p90/T | false include | false exclude | pass |", "|---|---|---|---|---|---|---|---|---|"]
for T in THRESHOLDS:
    near = (r >= 0.8 * T) & (r <= 1.2 * T)
    if near.sum() < 50: lines.append(f"| {T} | {near.sum()} | - | - | - | - | - | - | n/a |"); continue
    err = np.abs(o[near] - r[near]); med, p90 = np.median(err), np.percentile(err, 90)
    fi = ((o <= T) & (r > T)).sum() / max((r > T).sum(), 1)      # own says in, ref says out
    fe = ((o > T) & (r <= T)).sum() / max((r <= T).sum(), 1)     # own says out, ref says in
    ok = med <= 0.10 * T and p90 <= 0.20 * T
    lines.append(f"| {T} | {near.sum()} | {med:.1f} | {p90:.1f} | {med/T:.2f} | {p90/T:.2f} | {fi:.1%} | {fe:.1%} | {'PASS' if ok else 'FAIL'} |")
text = "\n".join(lines); print(text)
Path("docs/experiments/g1-routing.md").open("a", encoding="utf-8").write("\n" + text + "\n")
```

**Step 3: Run both modes and compare**

Run (from `v2/`):
```powershell
uv run python spikes/g1_own_graph_layer.py grocery walk
uv run python spikes/g1_own_graph_layer.py grocery drive
uv run python spikes/g1_compare.py data/layers/own_grocery_walk.tif data/layers/valhalla_grocery_pedestrian.tif "grocery walk: own vs Valhalla"
uv run python spikes/g1_compare.py data/layers/own_grocery_drive.tif data/layers/valhalla_grocery_auto.tif "grocery drive: own vs Valhalla"
```
Expected: timing JSON per run; comparison tables appended. Also run a **one-way audit**: pick 50 cells whose nearest edge is `oneway=yes` (drive) and confirm own vs Valhalla agree on reachability direction; record the count of disagreements.

**Step 4: Record the G1 verdict**

In `docs/experiments/g1-routing.md` add a "Verdict" section: stage timings (own) vs build time (Valhalla), per-threshold pass/fail, reachable-cell agreement, one-way audit, and the decision per synthesis §3.3: adopt own-graph for walk/bike/drive individually only where PASS and where its build time is materially better than Valhalla's; otherwise Valhalla is the single engine.

**Step 5: Commit**

```bash
git add v2/spikes/g1_own_graph_layer.py v2/spikes/g1_compare.py docs/experiments/g1-routing.md
git commit -m "exp(g1): own-graph transposed Dijkstra layers vs Valhalla with owner accuracy criterion"
```

---

## Task 9: Transit engine experiment (owner decision 13)

Compare three ways to get a **scheduled** 08:00 weekday arrival isochrone for three anchors (UNC Hospitals 35.9049,−79.0469; Duke University Hospital 36.0075,−78.9381; Downtown Raleigh 35.7796,−78.6382) within 45 minutes: (A) Valhalla `multimodal` with the GTFS feeds built in Task 5; (B) MOTIS self-hosted in WSL Docker; (C) Transitous public API as ground truth for 20 origin–destination pairs (non-commercial, keep under 100 requests).

**Files:**
- Create: `v2/infra/motis/README.md`
- Create: `v2/spikes/transit_compare.py`
- Create: `docs/experiments/transit.md`

**Step 1: Valhalla multimodal queries**

```bash
curl -s http://localhost:8002/isochrone -d '{"locations":[{"lat":35.9049,"lon":-79.0469}],"costing":"multimodal","date_time":{"type":1,"value":"2026-11-10T08:00"},"contours":[{"time":45}],"polygons":true,"reverse":true}' | head -c 400
```
Expected: GeoJSON with a non-trivial polygon if transit tiles built; if the response equals the pedestrian isochrone or errors, record it (transit tiles may not have ingested; check `docker compose logs | grep -i transit`).

**Step 2: MOTIS in WSL Docker**

`v2/infra/motis/README.md`:
```markdown
MOTIS (MIT) single-binary transit router. In WSL:
  mkdir -p /mnt/c/Users/arikt/documents/github/distanceFinder/v2/data/motis && cd $_
  cp ../slice/slice.osm.pbf . && cp ../gtfs/*.zip .
  docker run --rm -v "$PWD:/data" -w /data ghcr.io/motis-project/motis:latest motis config slice.osm.pbf *.zip
  docker run --rm -v "$PWD:/data" -w /data ghcr.io/motis-project/motis:latest motis import
  docker run -d --name motis -p 8080:8080 -v "$PWD:/data" -w /data ghcr.io/motis-project/motis:latest motis server
Then open http://localhost:8080 and use /api/v1/plan and /api/v1/one-to-all (check the served OpenAPI page for exact names).
Verify the image name/tag at https://github.com/motis-project/motis/pkgs/container/motis before running.
```
Record import time, RAM (`docker stats`), and whether one-to-all/isochrone endpoints exist.

**Step 3: Comparison script**

```python
# v2/spikes/transit_compare.py
"""20 OD pairs at 2026-11-10 08:00: Valhalla multimodal vs MOTIS vs Transitous (ground truth)."""
import json, random, time
from pathlib import Path
import httpx

random.seed(7)
ANCHORS = {"UNC Hospitals": (35.9049, -79.0469), "Duke Hospital": (36.0075, -78.9381), "Downtown Raleigh": (35.7796, -78.6382)}
BBOX = (-79.15, 35.80, -78.55, 36.15)
ORIGINS = [(random.uniform(BBOX[1], BBOX[3]), random.uniform(BBOX[0], BBOX[2])) for _ in range(7)]
PAIRS = [(o, a) for a in ANCHORS.values() for o in ORIGINS][:20]
WHEN = "2026-11-10T08:00"

def valhalla(o, d):
    body = {"locations": [{"lat": o[0], "lon": o[1]}, {"lat": d[0], "lon": d[1]}], "costing": "multimodal",
            "date_time": {"type": 1, "value": WHEN}}
    r = httpx.post("http://localhost:8002/route", json=body, timeout=60)
    return r.json()["trip"]["summary"]["time"] / 60 if r.status_code == 200 else None

def motis(o, d):
    r = httpx.get("http://localhost:8080/api/v1/plan", params={"fromPlace": f"{o[0]},{o[1]}", "toPlace": f"{d[0]},{d[1]}", "time": WHEN + ":00Z"}, timeout=60)
    if r.status_code != 200: return None
    its = r.json().get("itineraries", [])
    return min(i["duration"] for i in its) / 60 if its else None

def transitous(o, d):
    time.sleep(1.0)  # polite; non-commercial research use only
    r = httpx.get("https://api.transitous.org/api/v1/plan", params={"fromPlace": f"{o[0]},{o[1]}", "toPlace": f"{d[0]},{d[1]}", "time": WHEN + ":00Z"}, timeout=60,
                  headers={"User-Agent": "locfinder-phase0-experiment (arik.tash@gmail.com)"})
    if r.status_code != 200: return None
    its = r.json().get("itineraries", [])
    return min(i["duration"] for i in its) / 60 if its else None

rows = ["| # | origin | anchor | Valhalla mm (min) | MOTIS (min) | Transitous (min) |", "|---|---|---|---|---|---|"]
diffs = {"valhalla": [], "motis": []}
for i, (o, d) in enumerate(PAIRS, 1):
    v, m, t = valhalla(o, d), motis(o, d), transitous(o, d)
    rows.append(f"| {i} | {o[0]:.4f},{o[1]:.4f} | {d[0]:.4f},{d[1]:.4f} | {v and round(v)} | {m and round(m)} | {t and round(t)} |")
    if v and t: diffs["valhalla"].append(abs(v - t))
    if m and t: diffs["motis"].append(abs(m - t))
summary = [f"\nmedian abs diff vs Transitous: Valhalla={sorted(diffs['valhalla'])[len(diffs['valhalla'])//2] if diffs['valhalla'] else 'n/a'} min (n={len(diffs['valhalla'])}); MOTIS={sorted(diffs['motis'])[len(diffs['motis'])//2] if diffs['motis'] else 'n/a'} min (n={len(diffs['motis'])})"]
text = "\n".join(["## OD comparison (Task 9)"] + rows + summary); print(text)
Path("docs/experiments/transit.md").open("a", encoding="utf-8").write("\n" + text + "\n")
```

**Step 4: Run and record**

Run: `cd v2; uv run python spikes/transit_compare.py`
Record in `docs/experiments/transit.md`: build/import time and RAM for each engine; whether each offers a one-to-all or isochrone endpoint usable for a scheduled anchor; median abs diff vs Transitous; the verdict (engine for the first slice's transit mode, or "no engine ready; transit stays an open experiment").

**Step 5: Commit**

```bash
git add v2/infra/motis/README.md v2/spikes/transit_compare.py docs/experiments/transit.md
git commit -m "exp(transit): Valhalla multimodal vs MOTIS vs Transitous on 20 scheduled OD pairs"
```

---

## Task 10: POI coverage and fail-closed licensing (Gate G6)

**Files:**
- Create: `v2/locfinder/places/licence.py`
- Test: `v2/tests/test_licence.py`
- Create: `v2/spikes/g6_poi_coverage.py`
- Create: `docs/experiments/g6-poi-coverage.md`

**Step 1: Failing tests for fail-closed licence resolution** (replaces localUpdates `_license_for_row`, Codex H4)

```python
# v2/tests/test_licence.py
import pytest
from locfinder.places.licence import resolve_licence, UnknownLicence

def test_explicit_row_licence_wins():
    assert resolve_licence({"sources": [{"dataset": "meta", "license": "CDLA-Permissive-2.0"}]}, release="2026-10-21.0") == "CDLA-Permissive-2.0"

def test_foursquare_rows_are_apache():
    assert resolve_licence({"sources": [{"dataset": "Foursquare", "license": None}]}, release="2026-10-21.0") == "Apache-2.0"

def test_missing_licence_and_unknown_dataset_is_quarantined():
    with pytest.raises(UnknownLicence):
        resolve_licence({"sources": [{"dataset": "someone-new", "license": None}]}, release="2026-10-21.0")

def test_known_dataset_in_pinned_manifest_resolves():
    assert resolve_licence({"sources": [{"dataset": "meta", "license": None}]}, release="2026-10-21.0") == "CDLA-Permissive-2.0"

def test_unpinned_release_is_quarantined():
    with pytest.raises(UnknownLicence):
        resolve_licence({"sources": [{"dataset": "meta", "license": None}]}, release="9999-01-01.0")
```

**Step 2: Run to verify failure**

Run: `cd v2; uv run pytest tests/test_licence.py -v` → FAIL (module missing)

**Step 3: Implementation**

```python
# v2/locfinder/places/licence.py
"""Per-row licence resolution that FAILS CLOSED. A row without an explicit licence is
accepted only if its dataset is listed in the pinned release manifest below; anything
else raises UnknownLicence and the row is quarantined (never silently defaulted)."""
from __future__ import annotations

class UnknownLicence(Exception):
    pass

# Pinned manifests: release -> {dataset name (lowercase) -> licence}. Extend only after
# reading the release notes; record the source in docs/experiments/source-registry.md.
RELEASE_MANIFESTS = {
    "2026-10-21.0": {"meta": "CDLA-Permissive-2.0", "microsoft": "CDLA-Permissive-2.0", "foursquare": "Apache-2.0"},
}

def resolve_licence(row: dict, *, release: str) -> str:
    sources = row.get("sources") or []
    first = sources[0] if sources else {}
    explicit = first.get("license")
    if explicit:
        return explicit
    dataset = (first.get("dataset") or "").lower()
    manifest = RELEASE_MANIFESTS.get(release)
    if manifest is None or dataset not in manifest:
        raise UnknownLicence(f"release={release!r} dataset={dataset!r}: no explicit licence and not in pinned manifest")
    return manifest[dataset]
```

**Step 4: Run tests** → 5 passed. Commit.

```bash
git add v2/locfinder/places/licence.py v2/tests/test_licence.py
git commit -m "feat(v2): fail-closed per-row licence resolution for Overture places"
```

**Step 5: Coverage spike**

```python
# v2/spikes/g6_poi_coverage.py
"""Overture vs OSM per wedge category in the slice: counts, name/proximity matches, duplicates, licence quarantine."""
from pathlib import Path
import geopandas as gpd, numpy as np
from locfinder.places.categories import WEDGE_CATEGORIES
from locfinder.places.licence import resolve_licence, UnknownLicence

DATA = Path(__file__).resolve().parents[1] / "data" / "slice"
ov = gpd.read_parquet(DATA / "overture_places.parquet").to_crs("EPSG:32617")
osm = gpd.read_parquet(DATA / "osm_pois.parquet").to_crs("EPSG:32617")
RELEASE = "2026-10-21.0"   # set to the release actually downloaded (overturemaps CLI prints it)
quar = 0
for _, row in ov.iterrows():
    try: resolve_licence({"sources": list(row["sources"]) if row["sources"] is not None else []}, release=RELEASE)
    except UnknownLicence: quar += 1
lines = [f"## Coverage (Task 10) release={RELEASE} overture rows={len(ov)} quarantined={quar}", "",
         "| category | overture n | osm n | overture matched to osm (≤50 m) | osm matched to overture | overture dup pairs (≤25 m, same name) |", "|---|---|---|---|---|---|"]
def osm_sel(tags):
    m = np.zeros(len(osm), bool)
    for k, v in tags:
        if k in osm.columns: m |= (osm[k] == v).values
    return osm[m]
for cat, spec in WEDGE_CATEGORIES.items():
    o = ov[ov["categories"].apply(lambda c: isinstance(c, dict) and c.get("primary") in spec["overture"])]
    s = osm_sel(spec["osm"])
    if len(o) and len(s):
        j = gpd.sjoin_nearest(o[["geometry"]], s[["geometry"]], max_distance=50, how="left")
        om = j.index_right.notna().groupby(j.index).any().sum()
        j2 = gpd.sjoin_nearest(s[["geometry"]], o[["geometry"]], max_distance=50, how="left")
        sm = j2.index_right.notna().groupby(j2.index).any().sum()
    else: om = sm = 0
    names = o["names"].apply(lambda n: (n or {}).get("primary") if isinstance(n, dict) else None)
    dup = 0
    if len(o) > 1:
        jj = gpd.sjoin_nearest(o[["geometry"]].assign(nm=names.values), o[["geometry"]].assign(nm=names.values), max_distance=25, how="inner", exclusive=True)
        dup = int((jj["nm_left"] == jj["nm_right"]).sum() // 2)
    lines.append(f"| {cat} | {len(o)} | {len(s)} | {om} | {sm} | {dup} |")
text = "\n".join(lines); print(text)
Path("docs/experiments/g6-poi-coverage.md").write_text(text + "\n\nManual audit of 200 POIs (25 per category) goes below with precision/recall per source.\n", encoding="utf-8")
```

Run: `cd v2; uv run python spikes/g6_poi_coverage.py`. Then do the manual audit of 200 POIs (25 per category; spot-check in a map/browser) and write the per-category source preference table into `docs/experiments/g6-poi-coverage.md`. Pass: zero unknown-licence rows after manifest pinning; a chosen source per category.

**Step 6: Commit**

```bash
git add v2/spikes/g6_poi_coverage.py docs/experiments/g6-poi-coverage.md
git commit -m "exp(g6): Overture vs OSM coverage per wedge category and licence quarantine count"
```

---

## Task 11: Geocoding provider contract

**Files:**
- Create: `v2/spikes/geocode_bench.py`
- Create: `docs/experiments/geocoding.md`
- Modify: `docs/experiments/source-registry.md` (Census Geocoder, Nominatim public rows with terms)

**Step 1: Registry rows first** (Census Geocoder: public domain output, attribution disclaimer, no stated rate limit for single-line but be polite; Nominatim public: 1 req/s, dev only, attribution; see 04 §2.5 and localUpdates research for terms).

**Step 2: Benchmark** on 50 slice addresses sampled from OSM `addr:housenumber` nodes (QuackOSM filter `{"addr:housenumber": True}`), comparing Census (`https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?address=...&benchmark=Public_AR_Current&format=json`) and Nominatim (`https://nominatim.openstreetmap.org/search?q=...&format=jsonv2`, 1 req/s, custom User-Agent): match rate, median distance to the OSM point, latency. Write `docs/experiments/geocoding.md` with the table and the chosen dev-time provider and the stated terms, plus the fallback order. (Reuse the request shapes from `localUpdates/src/localupdates/geocode.py:348-553` rather than rewriting them.)

**Step 3: Commit**

```bash
git add v2/spikes/geocode_bench.py docs/experiments/geocoding.md docs/experiments/source-registry.md
git commit -m "exp(geocoding): Census vs Nominatim on 50 slice addresses; provider contract recorded"
```

---

## Task 12: Listings deep links and the G4 checklist

**Files:**
- Create: `v2/locfinder/listings/__init__.py` (empty)
- Create: `v2/locfinder/listings/links.py`
- Test: `v2/tests/test_links.py`
- Create: `v2/spikes/g4_generate_links.py`
- Create: `docs/experiments/g4-listings.md`

**Step 1: Failing tests**

```python
# v2/tests/test_links.py
import json
from urllib.parse import urlparse, parse_qs, unquote
from locfinder.listings.links import BBox, zillow_url, redfin_url, leakage_ratio

BB = BBox(west=-79.10, south=35.88, east=-79.00, north=35.95)

def test_zillow_url_encodes_map_bounds_and_filters():
    u = zillow_url(BB, max_price=600000, min_beds=3)
    q = parse_qs(urlparse(u).query)
    state = json.loads(unquote(q["searchQueryState"][0]))
    assert state["mapBounds"] == {"west": -79.10, "east": -79.00, "south": 35.88, "north": 35.95}
    assert state["isMapVisible"] is True
    assert state["filterState"]["price"]["max"] == 600000
    assert state["filterState"]["beds"]["min"] == 3

def test_redfin_url_uses_north_south_east_west_order():
    u = redfin_url(BB)
    assert "viewport=35.95:35.88:-79.0:-79.1" in u

def test_leakage_ratio_is_bbox_area_over_region_area():
    assert leakage_ratio(bbox_area_km2=10.0, region_area_km2=2.5) == 4.0
```

**Step 2: Run → FAIL. Step 3: Implementation**

```python
# v2/locfinder/listings/links.py
"""Deep links into listing portals, bounded to a region's bounding box. These URL
shapes are UNDOCUMENTED (research 04 §3.1-3.2; Codex C3) and are verified by hand in
Gate G4. We never fetch these pages; we only hand the user a link."""
from __future__ import annotations
from dataclasses import dataclass
import json
from urllib.parse import quote

@dataclass(frozen=True)
class BBox:
    west: float; south: float; east: float; north: float

def zillow_url(bb: BBox, *, max_price: int | None = None, min_beds: int | None = None, rentals: bool = False) -> str:
    filter_state: dict = {}
    if max_price: filter_state["price"] = {"max": max_price}
    if min_beds: filter_state["beds"] = {"min": min_beds}
    if rentals: filter_state["fr"] = {"value": True}; filter_state["fsba"] = {"value": False}
    state = {"mapBounds": {"west": bb.west, "east": bb.east, "south": bb.south, "north": bb.north},
             "isMapVisible": True, "filterState": filter_state, "isListVisible": True}
    return "https://www.zillow.com/homes/?searchQueryState=" + quote(json.dumps(state, separators=(",", ":")))

def redfin_url(bb: BBox) -> str:
    # viewport is north:south:east:west per observed URLs; path needs a region slug, so use the
    # generic search path and let G4 record whether a ZIP/city path segment is required.
    return f"https://www.redfin.com/filter/viewport={bb.north}:{bb.south}:{bb.east}:{bb.west},no-outline"

def realtor_url(bb: BBox) -> str:
    # UNVERIFIED pattern; G4 records what actually works.
    return f"https://www.realtor.com/realestateandhomes-search/?pos={bb.north},{bb.west},{bb.south},{bb.east}"

def trulia_url(bb: BBox) -> str:
    # UNVERIFIED pattern; G4 records what actually works.
    return f"https://www.trulia.com/for_sale/{bb.south},{bb.north},{bb.west},{bb.east}_xy/"

def leakage_ratio(*, bbox_area_km2: float, region_area_km2: float) -> float:
    return bbox_area_km2 / region_area_km2
```

**Step 4: Run tests → 3 passed. Commit.**

```bash
git add v2/locfinder/listings/ v2/tests/test_links.py
git commit -m "feat(v2): listing deep-link builders (undocumented portal URL shapes, verified in G4)"
```

**Step 5: Generate 20 regions and the checklist**

`v2/spikes/g4_generate_links.py`: for 20 anchor pairs sampled in the slice (two anchors, 25 min auto each, via Valhalla arrival isochrone polygons), intersect the polygons (shapely), compute region area and bbox area (UTM), build the four links, and write `docs/experiments/g4-listings.md` with a table: region id | area km² | leakage ratio | zillow | redfin | realtor | trulia | desktop ✓/✗ | iOS ✓/✗ | Android ✓/✗ | filters kept | returned to our page | notes. The owner fills the device columns by hand. Pass per synthesis G4; **fallback acceptance already granted by owner decision 14**, so record which portals work and whether city/ZIP links are needed.

```bash
git add v2/spikes/g4_generate_links.py docs/experiments/g4-listings.md
git commit -m "exp(g4): 20 region deep links with leakage ratios and device checklist"
```

---

## Task 13: Browser rendering spike (Gate G3)

**Files:**
- Create: `v2/spikes/g3-render/index.html`, `worker.js`, `package.json`, `README.md`
- Create: `v2/spikes/g3_export_layers.py` (exports 6 slice layers as raw uint8 `.bin` + a JSON manifest with grid bounds in EPSG:3857 for the canvas overlay)
- Create: `docs/experiments/g3-rendering.md`

**Step 1:** Export 6 layers (grocery/park/coffee × walk/bike or whatever exists) as `Uint8Array` binaries plus `manifest.json` (ncols, nrows, bounds in WGS84 and 3857). Reproject the UTM rasters to EPSG:3857 with rasterio `reproject` first so the canvas aligns with MapLibre.

**Step 2:** Page: MapLibre GL JS (pin the version in `package.json`, e.g. `maplibre-gl@^5`), Protomaps or OSM raster basemap; a `canvas` source covering the 3857 bounds; sliders per layer; a Web Worker that receives the 6 arrays once, then on each slider change computes `mask = AND(layer_i <= t_i)` into an RGBA buffer and posts it back; `performance.now()` timing for compute and paint shown on screen; a "polygonize" button using `d3-contour` on the mask and timing it. Also a check: does the pinned MapLibre expose raster colour-ramp styling for a non-DEM raster (document the answer with the version).

**Step 3:** Serve with `npx serve` on the LAN; test on a mid-range phone over Wi-Fi with Chrome DevTools throttled 4G on desktop as well. Record: slider-to-repaint ms (p50 over 20 drags), first paint s, polygonize ms, memory. Pass: repaint < 100 ms, first paint < 1.5 s throttled, valid polygons. Verdict: Worker/canvas vs server-rendered mask.

```bash
git add v2/spikes/g3-render v2/spikes/g3_export_layers.py docs/experiments/g3-rendering.md
git commit -m "exp(g3): browser raster algebra and polygonization timings on desktop and phone"
```

---

## Task 14: Early interaction comparison protocol and prototypes (Gate G5a)

**Files:**
- Create: `docs/experiments/g5a-interaction.md` (protocol + results)
- Create: `v2/spikes/g5a-protos/address-first.html`, `describe-it.html`

**Step 1:** Two clickable prototypes over the same static map image and the real two-anchor region PNG from Task 12's regions: (A) address-first: two address fields + mode/minutes controls, a result region appears; (B) describe-it: one text box that, for three scripted sentences, produces the same cards and region (scripted, no LLM). Both show identical criteria cards and a "Why is this out?" tap on one grey spot with real numbers from the rasters.

**Step 2:** Protocol per `06 §7` revised by `09 A4`: 3–5 households (couples where possible, at least 2 phone-first), counterbalanced order of A/B on equivalent novel scenarios; tasks include an impossible search, an ambiguous address ("Whole Foods"), an outside-coverage place, and one seeded wrong result; measure time-to-trusted-region, corrections, error detection, SEQ; two interview questions: transit dependence (decision 13) and whether they want to weigh criteria.

**Step 3:** Owner runs sessions; record results and the decision on entry-mode prominence and people grouping.

```bash
git add v2/spikes/g5a-protos docs/experiments/g5a-interaction.md
git commit -m "exp(g5a): address-first vs describe-it prototypes and counterbalanced test protocol"
```

---

## Task 15: Phase 0 decision memo and Codex pass 3

**Files:**
- Create: `docs/experiments/phase0-decisions.md`
- Modify: `docs/experiments/README.md` (statuses)
- Modify: `docs/research/08-synthesis.md` (status line → "Phase 0 complete; see experiments/phase0-decisions.md")

**Step 1:** Fill the gate table with measured numbers and PASS/FAIL; state the decisions: routing engine(s) per mode; transit engine or "open"; rendering path; POI source per category; geocoder; listings mechanism and fallback; grid stays square UTM 100 m unless G3 failed. Separate **measured** from **research-derived** from **assumed** (owner's trust order).

**Step 2:** Codex pass 3 on the memo and on the Phase 1 plan that follows it (prompt file in scratchpad; `--model gpt-6.1-sol`; see memory `reference-codex-runtime-quirks`).

**Step 3: Commit**

```bash
git add docs/experiments/phase0-decisions.md docs/experiments/README.md docs/research/08-synthesis.md
git commit -m "docs(experiments): Phase 0 decision memo"
```

---

## Dependencies and parallelism

- Tasks 0 → 1 → 2 → 3 are sequential (code).
- Task 4 (data) can run in parallel with Tasks 1–3.
- Task 5 (Valhalla build in WSL) can run in parallel with Task 8's graph loading (Windows); both need Task 4.
- Task 10 (G6) must finish its licence check before any Overture row is used beyond the experiments; run it right after Task 4.
- Task 7 needs Task 5; Task 8 needs Tasks 3, 4, 7; Task 9 needs Task 5 (transit tiles) and Task 4 (GTFS).
- Task 12 needs Task 5 (regions); Task 13 needs Tasks 7/8 (layers); Task 14 needs Task 12 (region image).
- Task 15 needs everything.

## Revisions after Codex pass 3 (`docs/research/10-codex-adversarial-review-pass3-plan.md`)

Applied to the code and files already written (the task text above is kept as the original record):

- **H2 snapping (fixed, tested):** `snap.py` masks unavailable directions before arithmetic (no `0 * inf`), treats a point exactly at a node as having zero on-edge travel, and pairs the two directions of a physical edge by canonical geometry rather than networkx keys. New tests: at-node reachability, destination node = 0, reversed-geometry pairing, parallel roads not conflated.
- **C1/H4/H5 acquisition (fixed):** `scripts/fetch_places.py` takes `--release`, writes the observed Arrow schema (the `categories` column was removed in the 2026-09 Overture release; selectors must use `taxonomy`/`basic_category` per the actual schema), partitions rows into an **accepted** artifact and a rejected report using the fail-closed resolver, and reads OSM POIs with `explode_tags=True` behind a `main()` guard. `licence.py` validates **every** source entry against an allowlist of reviewed licences plus a per-release manifest. Tasks 7, 8, 10 must read `overture_places_accepted.parquet`, never the raw file.
- **C3 transit input (fixed):** GTFS zips are renamed by agency and **extracted** to `v2/data/gtfs_extracted/<agency>/`, mounted read-only at `/gtfs_feeds` in the compose file. `feeds_report.json` records agency, timezone, and calendar files.
- **C2 results paths:** every spike resolves `REPO = Path(__file__).resolve().parents[2]` and writes to `REPO / "docs" / "experiments"` with `newline="\n"`.
- **H1 transit semantics:** Valhalla `multimodal` cannot produce an arrival-time isochrone (`date_time.type` 2 unsupported); Task 9 tests MOTIS first with `arriveBy=true` and `time=2026-11-10T08:00:00-05:00`, defines commute as deadline minus latest feasible departure, pins the MOTIS image digest, sends a client name/version/contact to Transitous and treats it as a sibling MOTIS deployment, not ground truth. Valhalla multimodal is recorded as "unsupported capability" if it cannot do arrival.
- **H6/H7/H9 comparison design:** Task 8 compares float seconds (saved alongside the uint8 rasters), builds a union-based confusion table that counts one-sided unreachable cells, reports absolute error and false inclusion/exclusion on a stated boundary sample with denominators, uses fixed workplace anchors at 25 minutes as well as category layers, sets Valhalla pedestrian `walking_speed` to 5.04 km/h for the controlled comparison and reports the intended-profile comparison separately, bounds POI-to-node snapping distance, and documents the speed model as a new profile (intersection penalties from CHCCS were not ported).
- **H3 graph validity:** the own-graph path must preserve mode access tags (`access`, `foot`, `bicycle`, `motor_vehicle`, `oneway:bicycle`), keep disconnected components for the audit, and state that turn restrictions are not modelled; that limitation is an adoption criterion in the G1 verdict.
- **H8 G2:** the slice build with an 8 GB cap informs but cannot pass G2; peak memory is sampled every 5 s for the whole build and benchmark (`data/valhalla_mem_samples.txt`); the NC build on the intended host is a required, separate measurement, and G2 stays pending until it exists.
- **H10 reference path:** Task 7 requires working GeoTIFF output; the polygon fallback is replaced by contour bracketing (contours at 5-minute steps) with the quantization error stated, if GeoTIFF is unavailable.
- **H11/ordering:** G5a prototypes use fixture imagery and scripted explanations and run right after scaffold, before any heavy build; G6 acceptance (accepted artifact) precedes any routing input.
- **M1–M5:** MapLibre version is locked in a lockfile for G3 with explicit nodata masks and coordinate transforms; G6 duplicate counts use a radius query and an independent inventory for recall; Task 11 adds ambiguous/POI cases and provider caching terms, following the Nominatim usage policy (1 req/s, identifying User-Agent, no autocomplete); scripts are LF and idempotent.
- **Task 15:** the review of the decision memo is Codex pass 4 (pass 3 is this plan review).

## Out of scope for Phase 0 (deferred by synthesis §8)

NC-wide Valhalla build and VPS deployment (Phase 1), R2 upload tests (needs a Cloudflare account; Phase 1), NL parsing (Phase 2), neighborhood boundaries, parcels, any context layers.
