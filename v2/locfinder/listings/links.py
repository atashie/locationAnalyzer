"""Deep links into listing portals, bounded to a region's bounding box.

These URL shapes are UNDOCUMENTED (research 04 §3.1-3.2; Codex C3) and are verified
by hand in Gate G4 on desktop, iOS, and Android. We never fetch these pages from code;
we only hand the user a link. The exact region is always shown on our own map.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import quote


@dataclass(frozen=True)
class BBox:
    west: float
    south: float
    east: float
    north: float


def zillow_url(bb: BBox, *, max_price: int | None = None, min_beds: int | None = None, rentals: bool = False) -> str:
    filter_state: dict = {}
    if max_price:
        filter_state["price"] = {"max": max_price}
    if min_beds:
        filter_state["beds"] = {"min": min_beds}
    if rentals:
        filter_state["fr"] = {"value": True}
        filter_state["fsba"] = {"value": False}
    state = {
        "mapBounds": {"west": bb.west, "east": bb.east, "south": bb.south, "north": bb.north},
        "isMapVisible": True,
        "filterState": filter_state,
        "isListVisible": True,
    }
    return "https://www.zillow.com/homes/?searchQueryState=" + quote(json.dumps(state, separators=(",", ":")))


def redfin_url(bb: BBox) -> str:
    # viewport is north:south:east:west per observed URLs. The path may require a
    # region slug (ZIP or city); G4 records which form actually opens.
    return f"https://www.redfin.com/filter/viewport={bb.north}:{bb.south}:{bb.east}:{bb.west},no-outline"


def realtor_url(bb: BBox) -> str:
    # UNVERIFIED pattern; G4 records what actually works.
    return f"https://www.realtor.com/realestateandhomes-search/?pos={bb.north},{bb.west},{bb.south},{bb.east}"


def trulia_url(bb: BBox) -> str:
    # UNVERIFIED pattern; G4 records what actually works.
    return f"https://www.trulia.com/for_sale/{bb.south},{bb.north},{bb.west},{bb.east}_xy/"


def leakage_ratio(*, bbox_area_km2: float, region_area_km2: float) -> float:
    """How much larger the portal's box is than our region (1.0 = no leakage)."""
    return bbox_area_km2 / region_area_km2
