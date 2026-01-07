"""Analysis API endpoints."""

import json
import logging

import numpy as np
import osmnx as ox
from fastapi import APIRouter, HTTPException, Query
from typing import Any, List, Optional

from app.core.constants import POI_TYPES

logger = logging.getLogger(__name__)


def _safe_str(value: Any) -> Optional[str]:
    """Convert value to string, returning None for NaN/None/empty values."""
    if value is None:
        return None
    if isinstance(value, float) and np.isnan(value):
        return None
    if value == "":
        return None
    return str(value)


from app.models.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    Criterion,
    CriterionResult,
    ErrorResponse,
    LocationValidation,
    POIFeature,
    POIRequest,
    POIsResponse,
    POIType,
    POITypesResponse,
)
from app.services.geocoding import validate_location
from app.services.location_analyzer import LocationAnalyzer

router = APIRouter(prefix="/api/v1", tags=["analysis"])


def _calculate_criterion_priority(criterion: Criterion) -> tuple:
    """
    Calculate priority score for smart query ordering.

    Lower score = higher priority (applied first).

    Priority rules:
    1. Single location > POI type (single locations are very restrictive)
    2. Distance mode > Walk > Bike > Drive (smaller effective radius first)
    3. Smaller value = higher priority

    Returns tuple for sorting: (type_score, mode_score, value)
    """
    # Type score: location (single point) is more restrictive than POI (many points)
    type_score = 0 if criterion.type.value == "location" else 1

    # Mode score: distance is most restrictive, then walk, bike, drive
    mode_scores = {
        "distance": 0,
        "walk": 1,
        "bike": 2,
        "drive": 3,
    }
    mode_score = mode_scores.get(criterion.mode.value, 0)

    # Value: smaller values are more restrictive
    # Normalize: for distance use miles directly, for time convert to equivalent miles
    if criterion.mode.value == "distance":
        normalized_value = criterion.value
    elif criterion.mode.value == "walk":
        # 3 mph walking speed, adjusted
        normalized_value = (criterion.value / 60) * 3 / 1.2
    elif criterion.mode.value == "bike":
        # 12 mph biking speed, adjusted
        normalized_value = (criterion.value / 60) * 12 / 1.3
    else:  # drive
        # 30 mph driving speed, adjusted
        normalized_value = (criterion.value / 60) * 30 / 1.5

    return (type_score, mode_score, normalized_value)


def _order_criteria_smart(criteria: List[Criterion]) -> List[Criterion]:
    """
    Reorder criteria to apply most restrictive first.

    This optimization reduces the polygon size early, making subsequent
    POI queries faster since they query a smaller geographic area.
    """
    return sorted(criteria, key=_calculate_criterion_priority)


@router.post(
    "/analyze",
    response_model=AnalysisResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def analyze_location(request: AnalysisRequest) -> AnalysisResponse:
    """
    Analyze a location with multiple proximity criteria.

    - **center**: City or address to center search on
    - **radius_miles**: Maximum search radius (1-25 miles)
    - **criteria**: List of proximity criteria to apply

    Returns a GeoJSON polygon of the matching area.
    """
    try:
        # Initialize analyzer
        analyzer = LocationAnalyzer(
            center_location=request.center,
            max_radius_miles=request.radius_miles,
        )

        # Smart ordering: apply most restrictive criteria first
        # This reduces polygon size early, making subsequent POI queries faster
        ordered_criteria = _order_criteria_smart(request.criteria)

        # Apply each criterion in optimized order
        for criterion in ordered_criteria:
            if criterion.type.value == "poi":
                analyzer.add_simple_buffer_criterion(
                    poi_type=POI_TYPES.get(criterion.poi_type),
                    max_distance_miles=criterion.value,
                    criterion_name=criterion.poi_type,
                )
            else:  # location
                if criterion.mode.value == "distance":
                    analyzer.add_simple_buffer_criterion(
                        specific_location=criterion.location,
                        max_distance_miles=criterion.value,
                        criterion_name=criterion.location[:30],
                    )
                else:
                    analyzer.add_travel_time_criterion(
                        specific_location=criterion.location,
                        max_time_minutes=int(criterion.value),
                        travel_mode=criterion.mode.value,
                        criterion_name=criterion.location[:30],
                    )

        # Get results
        result_gdf = analyzer.get_current_result()
        geojson = result_gdf.__geo_interface__

        # Build response
        criteria_results = [
            CriterionResult(
                name=cr["name"],
                description=cr["description"],
                area_sq_miles=analyzer._calculate_area_sq_miles(cr["geometry"]),
            )
            for cr in analyzer.criteria_results
        ]

        initial_area = analyzer._calculate_area_sq_miles(analyzer.search_boundary)
        final_area = result_gdf["area_sq_miles"].iloc[0]
        reduction = (1 - final_area / initial_area) * 100 if initial_area > 0 else 0

        return AnalysisResponse(
            success=True,
            center=request.center,
            center_lat=analyzer.center_point.y,
            center_lon=analyzer.center_point.x,
            initial_area_sq_miles=initial_area,
            final_area_sq_miles=final_area,
            area_reduction_percent=reduction,
            criteria_applied=criteria_results,
            geojson=geojson,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/validate-location", response_model=LocationValidation)
async def validate_location_endpoint(
    q: str = Query(..., min_length=2, description="Location to validate"),
) -> LocationValidation:
    """
    Validate and geocode a location string.

    Returns coordinates and display name if valid.
    """
    result = validate_location(q)
    return LocationValidation(
        valid=result["valid"],
        query=q,
        lat=result.get("lat"),
        lon=result.get("lon"),
        display_name=result.get("display_name"),
        error_message=result.get("error_message"),
    )


@router.get("/poi-types", response_model=POITypesResponse)
async def get_poi_types() -> POITypesResponse:
    """
    Get list of available POI types.

    Returns all supported POI categories with their OSM tags.
    """
    poi_types = [POIType(name=name, tags=tags) for name, tags in POI_TYPES.items()]
    return POITypesResponse(poi_types=poi_types)


@router.post(
    "/pois",
    response_model=POIsResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def query_pois(request: POIRequest) -> POIsResponse:
    """
    Query POIs within a GeoJSON polygon.

    - **polygon**: GeoJSON Feature, FeatureCollection, or Geometry
    - **poi_type**: Type of POI to search for (e.g., 'Restaurant')

    Returns a list of POIs with business details and a GeoJSON FeatureCollection.
    """
    from shapely.geometry import shape

    try:
        # Parse polygon from GeoJSON (handle Feature, FeatureCollection, or raw geometry)
        polygon_data = request.polygon
        if polygon_data.get("type") == "FeatureCollection":
            if not polygon_data.get("features"):
                raise ValueError("FeatureCollection has no features")
            geom = shape(polygon_data["features"][0]["geometry"])
        elif polygon_data.get("type") == "Feature":
            geom = shape(polygon_data["geometry"])
        else:
            # Assume it's a raw geometry
            geom = shape(polygon_data)

        # Get POI tags for the requested type
        poi_tags = POI_TYPES.get(request.poi_type)
        if not poi_tags:
            raise ValueError(f"Unknown POI type: {request.poi_type}")

        # Query OSM directly with the provided polygon
        try:
            pois_gdf = ox.features_from_polygon(geom, tags=poi_tags)
        except Exception as e:
            logger.warning(f"No POIs found for {request.poi_type}: {e}")
            return POIsResponse(
                success=True,
                poi_type=request.poi_type,
                total_found=0,
                pois=[],
                geojson={"type": "FeatureCollection", "features": []},
            )

        if pois_gdf.empty:
            return POIsResponse(
                success=True,
                poi_type=request.poi_type,
                total_found=0,
                pois=[],
                geojson={"type": "FeatureCollection", "features": []},
            )

        # Extract structured POI data
        poi_list = []
        for idx, row in pois_gdf.iterrows():
            geom_row = row.geometry

            # Handle both Point and Polygon geometries (buildings are often polygons)
            if geom_row.geom_type == "Polygon" or geom_row.geom_type == "MultiPolygon":
                centroid = geom_row.centroid
                lat, lon = centroid.y, centroid.x
            else:
                lat, lon = geom_row.y, geom_row.x

            # Build address from components if available
            address_parts = []
            housenumber = _safe_str(row.get("addr:housenumber")) if "addr:housenumber" in row else None
            street = _safe_str(row.get("addr:street")) if "addr:street" in row else None
            if housenumber:
                address_parts.append(housenumber)
            if street:
                address_parts.append(street)
            address = " ".join(address_parts) if address_parts else None

            # Get name, handling NaN values
            name = _safe_str(row.get("name")) if "name" in row else None
            if not name:
                name = "Unknown"

            poi_list.append({
                "id": str(idx),
                "name": name,
                "poi_type": request.poi_type,
                "lat": lat,
                "lon": lon,
                "address": address,
                "opening_hours": _safe_str(row.get("opening_hours")) if "opening_hours" in row else None,
                "phone": _safe_str(row.get("phone")) if "phone" in row else None,
                "website": _safe_str(row.get("website")) if "website" in row else None,
            })

        # Convert to GeoJSON
        geojson_data = json.loads(pois_gdf.to_json())

        logger.info(f"Found {len(poi_list)} POIs of type {request.poi_type}")

        return POIsResponse(
            success=True,
            poi_type=request.poi_type,
            total_found=len(poi_list),
            pois=[POIFeature(**p) for p in poi_list],
            geojson=geojson_data,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"POI query failed: {e}")
        raise HTTPException(status_code=500, detail=f"POI query failed: {str(e)}")


@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy"}
