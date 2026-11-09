"""Frozen raster grid contract for travel-time layers.

Square cells in a projected CRS (UTM 17N for the Triangle). Minutes are uint8:
0..254 minutes, NODATA (255) = unreachable / off-network / missing.
Row 0 is the north edge, matching GeoTIFF conventions.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

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
        cls,
        *,
        west: float,
        south: float,
        east: float,
        north: float,
        cell_m: float = 100.0,
        crs: str = DEFAULT_CRS,
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

    def cell_for_xy(self, x: float, y: float) -> tuple[int, int] | None:
        """`(row, col)` of the cell containing a projected coordinate, or `None` if outside.

        The inverse of `cell_centers_xy`, and the mapping a query needs: a household gives a
        point, and the product must say which cell's published answer applies to it. Until S3 step
        0 this class went centre-outward only, and the one place that needed the reverse
        (`spikes/s2_building_weighted_coverage.py:69`) inlined the arithmetic.

        **Half-open bounds, closed on the north and west edges.** Cell `(row, col)` covers
        `x` in `[x_min + col*cell_m, x_min + (col+1)*cell_m)` and
        `y` in `(y_max - (row+1)*cell_m, y_max - row*cell_m]`. So `(x_min, y_max)` is cell
        `(0, 0)`, while a point exactly on `x_max` or on `y_min` belongs to a cell one past the
        edge and is therefore **outside**. The property that matters is that every point belongs to
        at most one cell; which side of a measure-zero boundary it falls on is a convention, and
        this one is chosen to match `rasterio_profile`'s origin-at-north-west transform.

        **Outside returns `None`, and never clamps to an edge cell.** Clamping would manufacture a
        verdict for a place the layer does not cover: the household would be handed the travel time
        of whatever cell we happen to hold nearest, with nothing in the answer marking the
        substitution. An absent answer is recoverable; a confident wrong one is not.

        A **non-finite** coordinate raises rather than returning `None`. NaN is not a point outside
        the footprint — it is not a point — and reporting "outside" for it would launder a
        malformed input into an ordinary negative answer.

        **Interior boundaries are exact only to the grid's own precision.** `(x - x_min) / cell_m`
        is floating-point, so a grid whose cell is tiny next to its origin — `x_min = 450000.1`
        with `cell_m = 0.1` — can place a point exactly on an interior edge in the cell below it.
        The metro grids are 100 m or 200 m cells on origins that are multiples of the cell size at
        UTM magnitudes, where the division has about four orders of magnitude of margin, so this
        does not arise; a grid outside that regime needs exact edge arithmetic rather than an
        epsilon.
        """
        if not (math.isfinite(x) and math.isfinite(y)):
            raise ValueError(f"non-finite projected coordinate ({x!r}, {y!r})")
        # The footprint decides membership, and the index is derived only afterwards. Testing the
        # derived index instead lets rounding in `(x - x_min) / cell_m` contradict the declared
        # bounds in both directions, which Codex pass 26 exhibited: with `x_min=450000.1` and
        # `cell_m=123.4`, `x_max` itself divided into column `ncols - 1` and so read as *inside*,
        # while a value one ulp below `x_max` on another grid divided into `ncols` and read as
        # outside. Comparing the coordinate first and clamping the index second cannot do either.
        if not (self.x_min <= x < self.x_max and self.y_min < y <= self.y_max):
            return None
        col = min(math.floor((x - self.x_min) / self.cell_m), self.ncols - 1)
        row = min(math.floor((self.y_max - y) / self.cell_m), self.nrows - 1)
        return row, col

    def cell_for_lonlat(self, lon: float, lat: float) -> tuple[int, int] | None:
        """`(row, col)` for a WGS84 coordinate, or `None` if outside. See `cell_for_xy`.

        A coordinate that does not project into this CRS at all raises, for the same reason a NaN
        does: pyproj returns `inf` for an unprojectable point, and `inf` would otherwise read as a
        well-formed point that happens to lie outside the grid.
        """
        if not (math.isfinite(lon) and math.isfinite(lat)):
            raise ValueError(f"non-finite coordinate ({lon!r}, {lat!r})")
        to_proj = Transformer.from_crs("EPSG:4326", self.crs, always_xy=True)
        x, y = to_proj.transform(lon, lat)
        if not (math.isfinite(x) and math.isfinite(y)):
            raise ValueError(f"({lon!r}, {lat!r}) does not project into {self.crs}")
        return self.cell_for_xy(x, y)

    #: Points per side when reprojecting the rectangle's boundary. A projected rectangle's edges
    #: are curves in geographic coordinates, so its geographic extremes need not be at its corners.
    ENVELOPE_SAMPLES = 256

    def envelope_wgs84(self, *, pad_deg: float = 1e-6) -> tuple[float, float, float, float]:
        """`(west, south, east, north)` actually covered by this grid's cells.

        `from_bbox_wgs84` encloses the projected geographic box in an axis-aligned, rounded UTM
        rectangle, and nothing masks the cells that fall outside the original geographic bbox —
        **15,015 of the Triangle's 330,502 cells, 4.54%** (Codex pass-11 M4). The published surface
        uses the whole rectangle as its denominator, so an input acquired for the geographic bbox
        covers less ground than the cells it is meant to describe. Any audit that weights coverage
        by an acquired input must acquire it for *this* envelope.

        **The four corners do not bound it** (Codex pass-12 M6). A UTM rectangle's top edge is a
        curve in latitude whose maximum sits in the *interior* of the edge, near the central
        meridian, not at either corner. Codex's counterexample —
        `GridSpec("EPSG:32617", 450000, 4000000, 100, 1000, 10)` — put **806 cell centres north of
        a corner-derived bound**. The Triangle's own envelope happened to agree with a dense check,
        so the acquired building footprint was never actually short; the method was still wrong, and
        would have been quietly wrong for a differently placed metro.

        So the whole boundary is sampled, and the result is padded outward by `pad_deg` because an
        acquisition bound must never be tighter than the thing it is meant to cover. Sampling the
        boundary is sufficient: the forward projection is continuous and monotone in each coordinate
        over a single UTM zone, so no interior point exceeds every boundary point.
        """
        to_wgs = Transformer.from_crs(self.crs, "EPSG:4326", always_xy=True)
        n = self.ENVELOPE_SAMPLES
        ex = np.linspace(self.x_min, self.x_max, n)
        ey = np.linspace(self.y_min, self.y_max, n)
        xs = np.concatenate([ex, ex, np.full(n, self.x_min), np.full(n, self.x_max)])
        ys = np.concatenate([np.full(n, self.y_min), np.full(n, self.y_max), ey, ey])
        lons, lats = to_wgs.transform(xs, ys)
        return (float(np.min(lons)) - pad_deg, float(np.min(lats)) - pad_deg,
                float(np.max(lons)) + pad_deg, float(np.max(lats)) + pad_deg)

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
