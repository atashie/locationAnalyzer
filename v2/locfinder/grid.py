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

    def envelope_wgs84(self) -> tuple[float, float, float, float]:
        """`(west, south, east, north)` actually covered by this grid's cells.

        `from_bbox_wgs84` encloses the projected geographic box in an axis-aligned, rounded UTM
        rectangle, and nothing masks the cells that fall outside the original geographic bbox —
        **15,015 of the Triangle's 330,502 cells, 4.54%** (Codex pass-11 M4). The published surface
        uses the whole rectangle as its denominator, so an input acquired for the geographic bbox
        covers less ground than the cells it is meant to describe. Any audit that weights coverage
        by an acquired input must acquire it for *this* envelope.
        """
        to_wgs = Transformer.from_crs(self.crs, "EPSG:4326", always_xy=True)
        xs = [self.x_min, self.x_max, self.x_min, self.x_max]
        ys = [self.y_min, self.y_min, self.y_max, self.y_max]
        lons, lats = to_wgs.transform(xs, ys)
        return (min(lons), min(lats), max(lons), max(lats))

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
