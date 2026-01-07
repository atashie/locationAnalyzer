"""Pydantic schemas for API requests and responses."""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TravelMode(str, Enum):
    """Supported travel modes."""

    WALK = "walk"
    BIKE = "bike"
    DRIVE = "drive"
    DISTANCE = "distance"  # Straight-line distance


class CriterionType(str, Enum):
    """Type of search criterion."""

    POI = "poi"  # Search for POI type (e.g., "Grocery Store")
    LOCATION = "location"  # Search for specific location (e.g., "Duke University")


class Criterion(BaseModel):
    """A single search criterion."""

    type: CriterionType
    poi_type: Optional[str] = Field(None, description="POI type name (e.g., 'Grocery Store')")
    location: Optional[str] = Field(None, description="Specific location/address")
    mode: TravelMode = TravelMode.DISTANCE
    value: float = Field(..., description="Distance in miles or time in minutes")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "type": "poi",
                    "poi_type": "Grocery Store",
                    "mode": "distance",
                    "value": 1.0
                },
                {
                    "type": "location",
                    "location": "Duke University, Durham, NC",
                    "mode": "drive",
                    "value": 15
                }
            ]
        }


class AnalysisRequest(BaseModel):
    """Request body for location analysis."""

    center: str = Field(..., description="Center location (city or address)")
    radius_miles: float = Field(
        default=10.0,
        ge=1.0,
        le=25.0,
        description="Search radius in miles"
    )
    criteria: List[Criterion] = Field(
        default=[],
        max_length=8,
        description="List of search criteria"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "center": "Durham, NC",
                "radius_miles": 10,
                "criteria": [
                    {"type": "poi", "poi_type": "Park", "mode": "distance", "value": 1.0},
                    {"type": "poi", "poi_type": "Grocery Store", "mode": "distance", "value": 2.0}
                ]
            }
        }


class CriterionResult(BaseModel):
    """Result for a single applied criterion."""

    name: str
    description: str
    area_sq_miles: float


class AnalysisResponse(BaseModel):
    """Response body for location analysis."""

    success: bool
    center: str
    center_lat: float
    center_lon: float
    initial_area_sq_miles: float
    final_area_sq_miles: float
    area_reduction_percent: float
    criteria_applied: List[CriterionResult]
    geojson: Dict[str, Any] = Field(..., description="GeoJSON of result polygon")


class LocationValidation(BaseModel):
    """Response for location validation."""

    valid: bool
    query: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    display_name: Optional[str] = None
    error_message: Optional[str] = None


class POIType(BaseModel):
    """A POI type definition."""

    name: str
    tags: Dict[str, str]


class POITypesResponse(BaseModel):
    """Response for POI types list."""

    poi_types: List[POIType]


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    detail: Optional[str] = None


class POIFeature(BaseModel):
    """A single POI with business details from OpenStreetMap."""

    id: str
    name: str
    poi_type: str
    lat: float
    lon: float
    address: Optional[str] = None
    opening_hours: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None


class POIRequest(BaseModel):
    """Request for POI query within a polygon."""

    polygon: Dict[str, Any] = Field(..., description="GeoJSON Feature or FeatureCollection")
    poi_type: str = Field(..., description="POI type name (e.g., 'Restaurant')")

    class Config:
        json_schema_extra = {
            "example": {
                "polygon": {
                    "type": "FeatureCollection",
                    "features": [{"type": "Feature", "geometry": {"type": "Polygon", "coordinates": []}}]
                },
                "poi_type": "Restaurant"
            }
        }


class POIsResponse(BaseModel):
    """Response for POI query within a polygon."""

    success: bool
    poi_type: str
    total_found: int
    pois: List[POIFeature]
    geojson: Dict[str, Any] = Field(..., description="GeoJSON FeatureCollection of POIs")


class TripAdvisorEnrichment(BaseModel):
    """TripAdvisor enrichment data for a POI."""

    found: bool = Field(..., description="Whether a TripAdvisor match was found")
    location_id: Optional[str] = Field(None, description="TripAdvisor location ID")
    rating: Optional[float] = Field(None, description="Average rating (1-5)")
    num_reviews: Optional[int] = Field(None, description="Number of reviews")
    price_level: Optional[str] = Field(None, description="Price level ($, $$, $$$, $$$$)")
    ranking_string: Optional[str] = Field(None, description="Ranking (e.g., '#1 of 150 Restaurants')")
    tripadvisor_url: Optional[str] = Field(None, description="URL to TripAdvisor page")
    photos: List[str] = Field(default=[], description="Photo URLs (up to 3)")
    cuisine: Optional[List[str]] = Field(None, description="Cuisine types")
    error: Optional[str] = Field(None, description="Error message if enrichment failed")
