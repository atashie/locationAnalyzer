"""Metro definitions: the evaluation area a product grid covers, and the buffered routing
area whose road data must be loaded so routes may legally leave the evaluation area.

Keeping the two apart is the fix for the Phase 0 defect in which anchors south of the
extract edge produced truncated isochrones that looked like travel-time limits
(see docs/experiments/transit.md and g4-listings.md).
"""
from __future__ import annotations

from dataclasses import dataclass

from .grid import GridSpec


@dataclass(frozen=True)
class BBox:
    west: float
    south: float
    east: float
    north: float

    def buffered(self, degrees: float) -> "BBox":
        return BBox(self.west - degrees, self.south - degrees,
                    self.east + degrees, self.north + degrees)

    def contains(self, lat: float, lon: float) -> bool:
        return self.south <= lat <= self.north and self.west <= lon <= self.east

    def as_osmium(self) -> str:
        return f"{self.west},{self.south},{self.east},{self.north}"


@dataclass(frozen=True)
class Metro:
    name: str
    evaluation: BBox       # the product grid's extent
    routing: BBox          # road data to load; must strictly contain `evaluation`
    cell_m: float
    crs: str

    def grid(self, cell_m: float | None = None) -> GridSpec:
        e = self.evaluation
        return GridSpec.from_bbox_wgs84(west=e.west, south=e.south, east=e.east, north=e.north,
                                        cell_m=cell_m or self.cell_m, crs=self.crs)

    def __post_init__(self) -> None:
        e, r = self.evaluation, self.routing
        assert (r.west < e.west and r.south < e.south
                and r.east > e.east and r.north > e.north), \
            f"{self.name}: routing bbox must strictly contain the evaluation bbox"


# The Phase 0 slice: kept so earlier results stay reproducible. Its evaluation area excluded
# Cary, downtown Raleigh and NC State, and it had no routing buffer at all.
SLICE = Metro(
    name="slice",
    evaluation=BBox(-79.15, 35.80, -78.55, 36.15),
    routing=BBox(-79.16, 35.79, -78.54, 36.16),  # nominal; the Phase 0 extract was unbuffered
    cell_m=100.0,
    crs="EPSG:32617",
)

# The Triangle metro: widened south and east to include Cary, Apex, downtown Raleigh and NC
# State, with a ~15 km routing buffer so journeys may leave the evaluation area.
TRIANGLE = Metro(
    name="triangle",
    evaluation=BBox(-79.20, 35.70, -78.50, 36.15),
    routing=BBox(-79.35, 35.55, -78.35, 36.30),
    cell_m=100.0,
    crs="EPSG:32617",
)

METROS = {m.name: m for m in (SLICE, TRIANGLE)}
DEFAULT_METRO = "triangle"


def get_metro(name: str | None = None) -> Metro:
    return METROS[name or DEFAULT_METRO]
