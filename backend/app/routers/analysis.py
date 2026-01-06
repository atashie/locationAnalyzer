"""Analysis API endpoints."""

from fastapi import APIRouter, HTTPException, Query

from app.core.constants import POI_TYPES
from app.models.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    CriterionResult,
    ErrorResponse,
    LocationValidation,
    POIType,
    POITypesResponse,
)
from app.services.geocoding import validate_location
from app.services.location_analyzer import LocationAnalyzer

router = APIRouter(prefix="/api/v1", tags=["analysis"])


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

        # Apply each criterion
        for criterion in request.criteria:
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


@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy"}
