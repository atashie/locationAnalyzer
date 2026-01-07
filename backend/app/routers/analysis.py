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
    PremiumLocation,
    PremiumSearchRequest,
    PremiumSearchResponse,
    TripAdvisorEnrichment,
)
from app.services.geocoding import validate_location
from app.services.location_analyzer import LocationAnalyzer
from app.services.tripadvisor import enrich_poi_with_tripadvisor, get_tripadvisor_client

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


@router.get(
    "/poi/tripadvisor",
    response_model=TripAdvisorEnrichment,
    responses={400: {"model": ErrorResponse}},
)
async def get_tripadvisor_enrichment(
    name: str = Query(..., description="POI name"),
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    poi_type: str = Query(default="Restaurant", description="POI type"),
) -> TripAdvisorEnrichment:
    """
    Fetch TripAdvisor enrichment data for a POI.

    Returns rating, reviews, price level, photos, and TripAdvisor URL.
    Falls back gracefully if no match found or API limit reached.

    **Rate Limited:** Max 5000 API calls per month (free tier).
    Results are cached to minimize API usage.
    """
    try:
        result = enrich_poi_with_tripadvisor(name, lat, lon, poi_type)
        return TripAdvisorEnrichment(**result)
    except Exception as e:
        logger.exception(f"TripAdvisor enrichment failed: {e}")
        return TripAdvisorEnrichment(
            found=False,
            error=f"Enrichment failed: {str(e)}",
        )


@router.get("/tripadvisor/usage")
async def get_tripadvisor_usage() -> dict:
    """Get TripAdvisor API usage statistics for the current month."""
    client = get_tripadvisor_client()
    return {
        "enabled": client.enabled,
        "monthly_limit": client.monthly_limit,
        "current_usage": client.get_monthly_usage(),
        "limit_reached": client.is_limit_reached(),
    }


def _extract_polygon_centroids(
    geojson: dict, max_centroids: int = 5
) -> List[tuple]:
    """
    Extract centroids from GeoJSON, prioritizing by polygon area.

    For single polygon: returns [centroid]
    For multiple polygons: returns centroids of up to 5 largest, sorted by size

    Args:
        geojson: GeoJSON FeatureCollection or Feature
        max_centroids: Maximum number of centroids to return

    Returns:
        List of (lat, lon) tuples
    """
    from shapely.geometry import shape, MultiPolygon, Polygon
    from shapely.ops import unary_union

    # Parse GeoJSON to shapely geometry
    if geojson.get("type") == "FeatureCollection":
        features = geojson.get("features", [])
        if not features:
            return []
        geometries = [shape(f["geometry"]) for f in features]
        combined = unary_union(geometries)
    elif geojson.get("type") == "Feature":
        combined = shape(geojson["geometry"])
    else:
        combined = shape(geojson)

    # Handle different geometry types
    polygons_with_area = []

    if isinstance(combined, Polygon):
        centroid = combined.centroid
        return [(centroid.y, centroid.x)]  # (lat, lon)
    elif isinstance(combined, MultiPolygon):
        for poly in combined.geoms:
            area = poly.area
            centroid = poly.centroid
            polygons_with_area.append((area, centroid.y, centroid.x))
    else:
        # Single geometry fallback
        centroid = combined.centroid
        return [(centroid.y, centroid.x)]

    # Sort by area (largest first) and take top N
    polygons_with_area.sort(key=lambda x: x[0], reverse=True)
    return [(lat, lon) for _, lat, lon in polygons_with_area[:max_centroids]]


@router.post(
    "/premium-search",
    response_model=PremiumSearchResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def premium_search(request: PremiumSearchRequest) -> PremiumSearchResponse:
    """
    Run premium search using TripAdvisor API within analysis polygon.

    Algorithm:
    1. Extract polygon(s) from GeoJSON
    2. If 1 polygon: use its centroid
    3. If multiple: get centroids of 5 largest, sorted by area
    4. Query nearby_search for each centroid until max_locations reached
    5. Deduplicate by location_id
    6. Fetch details and photos for final results

    **API Usage:** This endpoint makes TripAdvisor API calls.
    - nearby_search: 1 call per centroid searched
    - details: 1 call per location
    - photos: 1 call per location
    """
    try:
        client = get_tripadvisor_client()

        if not client.enabled:
            raise HTTPException(status_code=400, detail="TripAdvisor not configured")

        if client.is_limit_reached():
            raise HTTPException(status_code=429, detail="Monthly API limit reached")

        # Extract centroids
        centroids = _extract_polygon_centroids(request.geojson)
        if not centroids:
            raise HTTPException(status_code=400, detail="No valid polygons in GeoJSON")

        # Batch search with deduplication
        locations, discovery_calls = client.nearby_search_batch(
            centroids=centroids,
            category=request.category.value,
            max_locations=request.max_locations,
        )

        api_calls_used = discovery_calls

        # Enrich with details and photos
        enriched_locations = []
        for loc in locations:
            location_id = loc.get("location_id")
            if not location_id:
                continue

            # Extract basic info from nearby search result
            enriched = PremiumLocation(
                location_id=location_id,
                name=loc.get("name", "Unknown"),
                lat=float(loc.get("latitude", 0)),
                lon=float(loc.get("longitude", 0)),
                category=request.category.value,
                address=loc.get("address_obj", {}).get("address_string"),
            )

            # Get details
            details = client.get_location_details(location_id)
            api_calls_used += 1
            if details:
                enriched.rating = float(details.get("rating")) if details.get("rating") else None
                enriched.num_reviews = int(details.get("num_reviews")) if details.get("num_reviews") else None
                enriched.price_level = details.get("price_level")
                enriched.ranking_string = details.get("ranking_data", {}).get("ranking_string")
                enriched.web_url = details.get("web_url")
                enriched.phone = details.get("phone")
                enriched.website = details.get("website")
                enriched.description = details.get("description")
                cuisine = details.get("cuisine", [])
                if cuisine:
                    enriched.cuisine = [c.get("localized_name") for c in cuisine if c.get("localized_name")]

            # Get photos
            photos = client.get_location_photos(location_id, limit=3)
            api_calls_used += 1
            enriched.photos = photos

            enriched_locations.append(enriched)

        # Build GeoJSON FeatureCollection
        features = []
        for loc in enriched_locations:
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [loc.lon, loc.lat]
                },
                "properties": {
                    "location_id": loc.location_id,
                    "name": loc.name,
                    "category": loc.category,
                    "rating": loc.rating,
                    "num_reviews": loc.num_reviews,
                    "price_level": loc.price_level,
                }
            }
            features.append(feature)

        geojson_result = {
            "type": "FeatureCollection",
            "features": features
        }

        logger.info(
            f"Premium search: {len(enriched_locations)} locations found, "
            f"{len(centroids)} centroids searched, {api_calls_used} API calls"
        )

        return PremiumSearchResponse(
            success=True,
            provider="tripadvisor",
            category=request.category.value,
            total_found=len(enriched_locations),
            locations=enriched_locations,
            centroids_searched=len(centroids),
            api_calls_used=api_calls_used,
            geojson=geojson_result,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Premium search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Premium search failed: {str(e)}")
