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

That sort is enforced in **`validate_population`**, which every path runs, because pass-19 F5 found
the claim was true only of the uncached path: `build_frame_b(population=...)` took the caller's order
as given, so the same grid, seed and source digest returned two different frames depending on which
way round two units were passed. A guarantee that holds on one of two entry points is not a
guarantee.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from dataclasses import dataclass, field
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
    spans `[y_max - cell, y_max)` and the last row spans `[y_min, y_min + cell)`.

    The interval is **half-open at the upper edge on both axes**, matching `structure_population`'s
    `[x_min, x_max) x [y_min, y_max)` filter and frame C's draw, which places a point at
    `y0 + u * cell` for `u` in `[0, 1)`. Pass-19 noted the first version of this docstring claimed
    `(y0, y1]` while the code did the opposite on both counts; the arithmetic was right and the
    stated convention was wrong, so the published raster lookup's boundary rule is the one written
    here.
    """
    row, col = cell_row_col(flat_index, grid)
    x0 = grid.x_min + col * grid.cell_m
    y1 = grid.y_max - row * grid.cell_m
    return np.column_stack([x0, y1 - grid.cell_m, x0 + grid.cell_m, y1])


# ----------------------------------------------------------------------------- the frame


def _frozen(array: np.ndarray) -> np.ndarray:
    """An array with the same contents whose buffer is an immutable `bytes` object.

    Nothing in the returned array's base chain owns a writable buffer, so `setflags(write=True)`
    raises at every level. That is the difference between "not currently writable" and "cannot be
    made writable", and two reviews got through the former.
    """
    contiguous = np.ascontiguousarray(array)
    return np.frombuffer(contiguous.tobytes(), dtype=contiguous.dtype)


#: Bumped when the digest's *byte layout* changes, so a stale recorded digest is recognisable as
#: belonging to an older identity rather than mistaken for a different frame. Version 2 adds `kind`
#: and `crs`, fixes little-endian float bytes and length-delimits the ids (pass-19 F7, F10).
DIGEST_VERSION = 2


@dataclass(frozen=True)
class Frame:
    """A drawn frame. `frozen=True` is **not** sufficient on its own and the arrays are made
    read-only here, because pass-19 F7 mutated `points` in place through a frozen dataclass: a
    999 m move left the recorded `digest` unchanged, and `write_frame` would have serialised the
    moved points under the old identity. A declared identity that its own holder can invalidate is
    not an identity.

    The digest is also **verified on construction**, so a Frame whose digest does not describe its
    contents cannot exist.
    """

    kind: str                   # "structures" | "area"
    points: np.ndarray          # (n, 2) float64, in `crs`
    source_ids: np.ndarray      # Overture id (frame B) or flat cell index (frame C)
    seed: int
    population_n: int
    crs: str
    source_digest: str          # what the population was derived from
    digest: str                 # this frame's own content

    #: The population's defining parameters, recorded for a reader who no longer holds the
    #: source. Deliberately **outside** the digest: pass-19 F10 is that "a digest is an
    #: identifier, not those missing inputs" — a grid hash does not reveal x_min 661900, y_max
    #: 4003500, cell 100 m, 643 x 514 to anyone without that grid in hand.
    source_spec: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.points.shape != (len(self.source_ids), 2):
            raise ValueError(f"points {self.points.shape} do not match "
                             f"{len(self.source_ids)} source ids")
        pts = np.array(self.points, dtype=np.float64, copy=True)
        if not np.isfinite(pts).all():
            raise ValueError("frame points must all be finite")
        # An **object** array is converted to fixed-width text, because copying one copies the
        # pointers and not the referents, so freezing it would not freeze what it points at
        # (pass-20 F8). Frame B's Overture ids arrive from pandas as `dtype=object`; frame C's cell
        # indices are integers and keep their dtype. The digest stringifies ids either way, so this
        # does not change any frame's identity.
        raw_ids = np.asarray(self.source_ids)
        ids = (np.array([str(s) for s in raw_ids], dtype=np.str_) if raw_ids.dtype == object
               else np.asarray(raw_ids))

        # **Arrays backed by immutable `bytes`.** Clearing the writeable flag is not enough, and
        # neither is handing out a view: pass-20 F8 re-enabled writing on an owning array, and
        # pass-21 F3 then reached the owner straight back through the view's public `.base` and
        # moved a point 999 m under an unchanged digest. `np.frombuffer` over a `bytes` object has
        # no writable array anywhere in its base chain, so `setflags(write=True)` raises at every
        # level — there is no owner to ask.
        object.__setattr__(self, "points", _frozen(pts).reshape(len(ids), 2))
        object.__setattr__(self, "source_ids", _frozen(ids))
        if self.digest != self.recomputed_digest:
            raise ValueError("the supplied digest does not describe these points and ids")

    def __reduce__(self):
        """Rebuild through `__init__`, so unpickling re-runs validation and re-freezes the arrays.

        Pass-21 F3: `pickle.loads(pickle.dumps(frame))` returned a frame whose arrays were both
        **writeable**, because unpickling a dataclass restores `__dict__` without calling
        `__post_init__`. Direct assignment then invalidated its digest silently.
        """
        return (self.__class__, (self.kind, self.points, self.source_ids, self.seed,
                                 self.population_n, self.crs, self.source_digest, self.digest,
                                 self.source_spec))

    def verify(self) -> None:
        """Raise unless the contents still match the recorded digest.

        Called before writing, and **to be called where a measurement consumes a frame**: in-memory
        protection is a guard, not a proof, and the identity a measurement reports should be checked
        against the data it actually used.
        """
        if self.digest != self.recomputed_digest:
            raise ValueError("this frame's contents no longer match its digest")

    @property
    def n(self) -> int:
        return len(self.source_ids)

    @property
    def recomputed_digest(self) -> str:
        return frame_digest(kind=self.kind, points=self.points, source_ids=self.source_ids,
                            seed=self.seed, population_n=self.population_n, crs=self.crs,
                            source_digest=self.source_digest)


def frame_digest(*, kind: str, points: np.ndarray, source_ids: np.ndarray, seed: int,
                 population_n: int, crs: str, source_digest: str) -> str:
    """Content digest over **canonical** bytes, not native memory.

    Three things pass-19 found wrong with the first version, each of which let two different frames
    share one identity or one frame acquire two:

    * **`kind` and `crs` were omitted.** Two frames with identical arrays, seed, population size and
      source digest but CRS `EPSG:32617` against `EPSG:4326` described different locations on Earth
      and digested the same (F7). The public constructor accepts those fields independently, so they
      belong in the identity.
    * **Float bytes were native-endian.** The double 1.0 contributes
      `000000000000f03f` on a little-endian machine and `3ff0000000000000` on a big-endian one, so
      moving an artifact to another architecture failed digest recomputation on numerically
      identical points (F10). `"<f8"` fixes the layout.
    * **Ids were fixed-width `U64` in native memory**, which is endian-dependent in the same way and
      silently truncates an id longer than 64 characters. They are now length-delimited UTF-8, so
      neither truncation nor concatenation ambiguity is possible: `("ab", "c")` and `("a", "bc")`
      digest differently.
    """
    h = hashlib.sha256()
    h.update(f"locfinder.frame.v{DIGEST_VERSION}\n".encode())
    h.update(np.ascontiguousarray(points, dtype="<f8").tobytes())
    for s in source_ids:
        raw = str(s).encode("utf-8")
        h.update(len(raw).to_bytes(4, "little"))
        h.update(raw)
    h.update(json.dumps({"kind": kind, "crs": crs, "seed": seed, "n": len(source_ids),
                         "population_n": population_n, "source_digest": source_digest},
                        sort_keys=True).encode())
    return h.hexdigest()


def file_digest(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def grid_spec_dict(grid: GridSpec) -> dict:
    """The grid's defining parameters, so a manifest reader can rebuild it without the object.

    Pass-19 F10: "a seed plus a grid hash does not reveal `x_min=661900, y_max=4003500, cell=100,
    ncols=643, nrows=514` to a reader who no longer has that grid."
    """
    return {"crs": grid.crs, "x_min": grid.x_min, "y_max": grid.y_max,
            "cell_m": grid.cell_m, "ncols": grid.ncols, "nrows": grid.nrows}


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
                 digest=frame_digest(kind="area", points=points, source_ids=cells, seed=seed,
                                     population_n=population_n, crs=grid.crs, source_digest=sd),
                 source_spec=grid_spec_dict(grid))


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


def validate_population(ids: np.ndarray, pts: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Put a supplied population into the **intrinsic order the draw is specified against**, and
    reject one that cannot be a population.

    Pass-19 F5: the cached-population path accepted arbitrary ids and points unsorted, so the
    module's own claim — "frame B's population is sorted by Overture `id` before any draw" — held
    only on the uncached path. Executed there: the same grid, *n* = 1, seed 7 and source digest,
    with the two units supplied as `[b, a]` and as `[a, b]`, selected **b** in one case and **a** in
    the other and returned two different frame digests. The order of the caller's arrays was
    deciding which structure the sample contained.

    Sorting here is idempotent when the population already came from `structure_population`, so the
    frames already built are unaffected by this fix.
    """
    ids = np.asarray(ids)
    pts = np.asarray(pts, dtype=np.float64)
    if ids.ndim != 1 or pts.shape != (len(ids), 2):
        raise ValueError(f"population shapes do not match: ids {ids.shape}, points {pts.shape}")
    if len(ids) == 0:
        raise ValueError("an empty population cannot be sampled")
    if not np.isfinite(pts).all():
        raise ValueError("population points must all be finite")
    as_text = np.asarray([str(s) for s in ids])
    if len(np.unique(as_text)) != len(ids):
        raise ValueError("the population contains duplicate source ids")
    order = np.argsort(ids, kind="stable")      # intrinsic order, not caller order (F5) or file (S2.5)
    return ids[order], pts[order]


def build_frame_b(parquet: Path, grid: GridSpec, *, n: int, seed: int,
                  population: tuple[np.ndarray, np.ndarray] | None = None,
                  source_digest: str | None = None,
                  expect_population_n: int | None = None) -> Frame:
    """Design §1's structure frame. `population` and `source_digest` may be supplied to avoid
    re-reading and re-projecting 522,160 geometries, which takes minutes.

    `expect_population_n` is the guard pass-19 F5 asked for at the **builder** boundary rather than
    in a build script: a 500-unit cached subset is otherwise indistinguishable from the full
    population here, and would be sampled exhaustively while being labelled with the real source
    digest and omitting 512,133 eligible structures. A production call passes the frozen count; a
    unit-test helper legitimately does not.
    """
    if population is None:
        ids, pts, _ = structure_population(parquet, grid)
    else:
        ids, pts = population
    ids, pts = validate_population(ids, pts)
    sd = source_digest if source_digest is not None else file_digest(parquet)
    population_n = len(ids)
    if expect_population_n is not None and population_n != expect_population_n:
        raise ValueError(f"population is {population_n:,} units, not the expected "
                         f"{expect_population_n:,} — the frame would not be the frozen one")
    if not 0 < n <= population_n:
        raise ValueError(f"require 0 < n <= {population_n}, got {n}")
    rng = np.random.Generator(BIT_GENERATOR(seed))
    idx = rng.permutation(population_n)[:n]
    points = pts[idx]
    chosen = ids[idx]
    return Frame(kind="structures", points=points, source_ids=chosen, seed=seed,
                 population_n=population_n, crs=grid.crs, source_digest=sd,
                 digest=frame_digest(kind="structures", points=points, source_ids=chosen,
                                     seed=seed, population_n=population_n, crs=grid.crs,
                                     source_digest=sd),
                 source_spec={"grid": grid_spec_dict(grid),
                              "parquet": None if parquet is None else str(parquet)})


# ----------------------------------------------------------------------------- persistence


def read_frame(manifest_path: Path) -> Frame:
    """Load a written frame, **verifying its digest against its contents**.

    `Frame.__post_init__` recomputes the digest and refuses to construct a frame whose recorded
    identity does not describe its points, so the check is the construction. Design §12: the
    identity a measurement reports has to be checked against the data it actually used, and
    "in-memory protection is a guard, not a proof".

    The parquet stores every id as text, and `frame_digest` keys on `str(id)`, so a frame whose ids
    were integers (frame C's flat cell indices) reproduces its digest through this round trip.
    """
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if manifest.get("digest_version") != DIGEST_VERSION:
        raise ValueError(f"{manifest_path.name} is digest version "
                         f"{manifest.get('digest_version')!r}, not {DIGEST_VERSION}")
    data_path = Path(manifest_path).with_suffix(".parquet")
    table = pd.read_parquet(data_path)
    frame = Frame(
        kind=manifest["kind"],
        points=np.column_stack([table["x"].to_numpy(dtype=np.float64),
                                table["y"].to_numpy(dtype=np.float64)]),
        source_ids=table["source_id"].to_numpy(),
        seed=int(manifest["seed"]),
        population_n=int(manifest["population_n"]),
        crs=manifest["crs"],
        source_digest=manifest["source_digest"],
        digest=manifest["digest"],
        source_spec=manifest.get("source_spec", {}),
    )
    frame.verify()
    return frame


def write_frame(frame: Frame, directory: Path) -> tuple[Path, Path]:
    """Write `frame_<kind>_<digest8>.parquet` plus its manifest. **Never overwrites**: a new sample
    is a new digest, so a collision means an attempt to rewrite an existing frame.

    The digest is **recomputed and compared** before anything is written. `Frame.__post_init__`
    already blocks the mutation pass-19 F7 executed, and this is the second layer: a writer that
    serialises current contents under a recorded identity it never checked is the mechanism by which
    a moved point keeps a frame's name.

    **The saved points are the artifact.** The manifest records the draw and the runtime so a redraw
    can be *attempted* and compared, but it does not promise bit-identical regeneration on another
    NumPy or another platform — `numpy.random.Generator` carries an explicit "No Compatibility
    Guarantee", and PCG64's stream guarantee does not freeze `permutation`'s internal shuffle
    (pass-19 F10). That is why the parquet is written rather than the seed alone being recorded.
    """
    if frame.digest != frame.recomputed_digest:
        raise ValueError("refusing to write: the frame's contents do not match its digest")
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
        "source_spec": frame.source_spec,
        "digest": frame.digest,
        "digest_version": DIGEST_VERSION,
        "digest_bytes": "sha256 over: version tag, points as little-endian float64, "
                        "length-delimited UTF-8 source ids, then sorted-key JSON of kind, crs, "
                        "seed, n, population_n and source_digest",
        "sampling": "numpy.random.Generator(PCG64(seed)); permutation(N)[:n]"
                    + ("; then random((n, 2)) for the two independent within-cell offsets"
                       if frame.kind == "area" else ""),
        "runtime": {"python": sys.version.split()[0], "numpy": np.__version__,
                    "platform": platform.platform(), "byte_order": sys.byteorder},
        "regeneration": "The saved points are authoritative. numpy.random.Generator gives no "
                        "cross-version compatibility guarantee, so a redraw on another NumPy or "
                        "platform is a check to run, not a promise this manifest makes.",
    }, indent=2, sort_keys=True), encoding="utf-8")
    return data_path, manifest_path
