"""Location analysis service - core geospatial logic."""

import logging
import math
import json
from typing import Any, Dict, List, Optional, Tuple

import geopandas as gpd
import osmnx as ox
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

from app.core.constants import (
    BUFFER_ADJUSTMENTS,
    MAX_QUERY_EXPANSION_MILES,
    TRAVEL_SPEEDS,
)

logger = logging.getLogger(__name__)


class LocationAnalyzer:
    """Location analysis tool with progressive filtering."""

    def __init__(self, center_location: str, max_radius_miles: float = 25.0):
        """
        Initialize with a center point and maximum search radius.

        Args:
            center_location: City or address to center search on
            max_radius_miles: Maximum search radius in miles

        Raises:
            ValueError: If location cannot be geocoded
        """
        logger.info(f"Initializing analyzer for: {center_location}")

        # Geocode center location
        try:
            location_gdf = ox.geocode_to_gdf(center_location)
            self.center_point = location_gdf.geometry.iloc[0].centroid
        except Exception:
            try:
                lat, lon = ox.geocode(center_location)
                self.center_point = Point(lon, lat)
            except Exception as e:
                raise ValueError(f"Could not geocode location: {center_location}") from e

        self.center_location = center_location
        self.max_radius_miles = max_radius_miles
        self.crs = "EPSG:4326"

        # Get UTM CRS for accurate distance calculations
        self.utm_crs = self._estimate_utm_crs(self.center_point.x, self.center_point.y)

        # Create initial search boundary
        center_gdf = gpd.GeoDataFrame(
            [{"geometry": self.center_point}], crs=self.crs
        )
        center_projected = center_gdf.to_crs(self.utm_crs)

        buffer_meters = max_radius_miles * 1609.34
        search_boundary = center_projected.buffer(buffer_meters)

        self.search_boundary = search_boundary.to_crs(self.crs).iloc[0]
        self.current_search_area = self.search_boundary

        # Storage for results
        self.criteria_results: List[Dict[str, Any]] = []

        logger.info(f"Search area initialized: {max_radius_miles} mile radius")

    def _estimate_utm_crs(self, lon: float, lat: float) -> str:
        """Estimate appropriate UTM CRS for given coordinates."""
        utm_zone = int((lon + 180) / 6) + 1
        if lat >= 0:
            return f"EPSG:326{utm_zone:02d}"
        else:
            return f"EPSG:327{utm_zone:02d}"

    def _calculate_area_sq_miles(self, geometry) -> float:
        """Calculate area in square miles."""
        gdf = gpd.GeoDataFrame([{"geometry": geometry}], crs=self.crs)
        gdf_projected = gdf.to_crs(self.utm_crs)
        area_sq_m = gdf_projected.geometry.area.iloc[0]
        return area_sq_m / 2589988.11  # Square meters to square miles

    def _create_realistic_buffer(
        self, centroid_x: float, centroid_y: float, distance_meters: float, travel_mode: str
    ) -> Polygon:
        """
        Create a realistic irregular buffer instead of a perfect circle.

        Uses smooth mathematical variation to approximate real isochrones,
        which are never perfectly circular due to road network patterns.

        Args:
            centroid_x: X coordinate of center point (in projected CRS)
            centroid_y: Y coordinate of center point (in projected CRS)
            distance_meters: Base buffer distance in meters
            travel_mode: 'walk', 'bike', or 'drive'

        Returns:
            Polygon with irregular shape approximating real travel patterns
        """
        num_vertices = 36

        # Mode-specific variation intensity
        # Walking is more uniform, driving varies more with road networks
        mode_variation = {"walk": 0.15, "bike": 0.20, "drive": 0.25}
        variation_intensity = mode_variation.get(travel_mode, 0.20)

        vertices = []
        for i in range(num_vertices):
            angle = (2 * math.pi * i) / num_vertices

            # Apply smooth variation using sine waves at different frequencies
            # This creates organic, realistic shapes without randomness
            variation = (
                0.12 * math.sin(2 * angle + 0.3)        # 2-fold pattern (elongation)
                + 0.08 * math.sin(4 * angle + 1.2)     # 4-fold (cardinal directions)
                + 0.05 * math.sin(3 * angle + 2.1)     # 3-fold asymmetry
                + 0.04 * math.sin(5 * angle + 0.7)     # Higher frequency detail
            )

            # Scale variation by mode intensity
            variation *= variation_intensity / 0.20  # Normalize to base intensity

            adjusted_distance = distance_meters * (1 + variation)

            x = centroid_x + adjusted_distance * math.cos(angle)
            y = centroid_y + adjusted_distance * math.sin(angle)
            vertices.append((x, y))

        polygon = Polygon(vertices)

        # Slight buffer/unbuffer to smooth any sharp edges
        smoothed = polygon.buffer(distance_meters * 0.01).buffer(-distance_meters * 0.01)

        return smoothed

    def _create_expanded_query_area(self, expansion_miles: float) -> Any:
        """
        Create an expanded query area for POI searches.

        This ensures we capture POIs just outside the current boundary that
        could still serve points within the boundary (important for travel-time
        criteria where a POI outside the boundary may be within travel time of
        interior points).

        Args:
            expansion_miles: How many miles to expand beyond current area

        Returns:
            Expanded polygon geometry for querying
        """
        # Cap the expansion to avoid massive queries
        capped_expansion = min(expansion_miles, MAX_QUERY_EXPANSION_MILES)

        if capped_expansion <= 0:
            return self.current_search_area

        # Convert current area to UTM, buffer, convert back
        current_gdf = gpd.GeoDataFrame(
            [{"geometry": self.current_search_area}], crs=self.crs
        )
        current_projected = current_gdf.to_crs(self.utm_crs)

        expansion_meters = capped_expansion * 1609.34
        expanded = current_projected.geometry.buffer(expansion_meters)

        expanded_gdf = gpd.GeoDataFrame(
            [{"geometry": expanded.iloc[0]}], crs=self.utm_crs
        ).to_crs(self.crs)

        # Also cap to original search boundary to avoid querying beyond user's intent
        expanded_area = expanded_gdf.geometry.iloc[0].intersection(self.search_boundary)

        logger.debug(f"Expanded query area by {capped_expansion:.1f} miles")
        return expanded_area

    def add_simple_buffer_criterion(
        self,
        poi_type: Optional[Dict[str, str]] = None,
        specific_location: Optional[str] = None,
        max_distance_miles: float = 1.0,
        criterion_name: Optional[str] = None,
    ) -> Optional[gpd.GeoDataFrame]:
        """
        Add a simple distance buffer criterion.

        Args:
            poi_type: OSM tags for POI search
            specific_location: Specific location/address
            max_distance_miles: Maximum distance in miles
            criterion_name: Display name for this criterion

        Returns:
            GeoDataFrame with result geometry, or None if no POIs found
        """
        # For distance criteria, expand query area by the buffer distance
        # This captures POIs just outside current boundary that could serve interior points
        if poi_type and not specific_location:
            query_area = self._create_expanded_query_area(max_distance_miles)
        else:
            query_area = self.current_search_area

        pois = self._get_pois(poi_type, specific_location, query_area)
        if pois is None or len(pois) == 0:
            logger.warning(f"No POIs found for criterion: {criterion_name}")
            return None

        pois_projected = pois.to_crs(self.utm_crs)
        buffer_meters = max_distance_miles * 1609.34
        buffers = pois_projected.geometry.buffer(buffer_meters)

        combined_buffer = buffers.union_all()
        result_gdf = gpd.GeoDataFrame(
            [{"geometry": combined_buffer}], crs=self.utm_crs
        ).to_crs(self.crs)
        result_geometry = result_gdf.geometry.iloc[0].intersection(
            self.current_search_area
        )

        self.current_search_area = result_geometry
        self.criteria_results.append(
            {
                "name": criterion_name or "Buffer",
                "geometry": result_geometry,
                "description": f"Within {max_distance_miles} miles (straight-line)",
            }
        )

        area_sq_miles = self._calculate_area_sq_miles(result_geometry)
        logger.info(f"Applied {criterion_name}. New area: {area_sq_miles:.1f} sq miles")

        return gpd.GeoDataFrame([{"geometry": result_geometry}], crs=self.crs)

    def add_travel_time_criterion(
        self,
        poi_type: Optional[Dict[str, str]] = None,
        specific_location: Optional[str] = None,
        max_time_minutes: int = 10,
        travel_mode: str = "walk",
        criterion_name: Optional[str] = None,
    ) -> Optional[gpd.GeoDataFrame]:
        """
        Add travel time criterion with mode-specific calculations.

        For MVP, uses adjusted buffer based on travel speed.
        V1 will use Valhalla for accurate isochrones.

        Args:
            poi_type: OSM tags for POI search
            specific_location: Specific location/address
            max_time_minutes: Maximum travel time in minutes
            travel_mode: 'walk', 'bike', or 'drive'
            criterion_name: Display name for this criterion

        Returns:
            GeoDataFrame with result geometry, or None if no POIs found
        """
        speed_mph = TRAVEL_SPEEDS.get(travel_mode, TRAVEL_SPEEDS["walk"])
        max_distance_miles = (max_time_minutes / 60) * speed_mph

        # Apply buffer adjustment for realistic travel patterns
        adjustment = BUFFER_ADJUSTMENTS.get(travel_mode, 1.2)
        adjusted_distance = max_distance_miles / adjustment

        # For travel-time criteria, expand query area by the max travel distance
        # This ensures we capture POIs outside the current boundary that are still
        # within travel time of points inside the boundary
        if poi_type and not specific_location:
            query_area = self._create_expanded_query_area(adjusted_distance)
        else:
            query_area = self.current_search_area

        pois = self._get_pois(poi_type, specific_location, query_area)
        if pois is None or len(pois) == 0:
            logger.warning(f"No POIs found for criterion: {criterion_name}")
            return None

        pois_projected = pois.to_crs(self.utm_crs)
        buffer_meters = adjusted_distance * 1609.34

        # Create realistic irregular buffers for each POI
        realistic_buffers = []
        for geom in pois_projected.geometry:
            centroid = geom.centroid
            realistic_buffer = self._create_realistic_buffer(
                centroid.x, centroid.y, buffer_meters, travel_mode
            )
            realistic_buffers.append(realistic_buffer)

        # Combine all buffers
        combined_buffer = unary_union(realistic_buffers)

        result_gdf = gpd.GeoDataFrame(
            [{"geometry": combined_buffer}], crs=self.utm_crs
        ).to_crs(self.crs)
        result_geometry = result_gdf.geometry.iloc[0].intersection(
            self.current_search_area
        )

        self.current_search_area = result_geometry
        self.criteria_results.append(
            {
                "name": criterion_name or "Travel Time",
                "geometry": result_geometry,
                "description": f"{travel_mode}: {max_time_minutes} min",
            }
        )

        area_sq_miles = self._calculate_area_sq_miles(result_geometry)
        logger.info(f"Applied {criterion_name}. New area: {area_sq_miles:.1f} sq miles")

        return gpd.GeoDataFrame([{"geometry": result_geometry}], crs=self.crs)

    def _get_pois(
        self,
        poi_type: Optional[Dict[str, str]] = None,
        specific_location: Optional[str] = None,
        query_area: Optional[Any] = None,
    ) -> Optional[gpd.GeoDataFrame]:
        """
        Get POIs from either type search or specific location.

        Args:
            poi_type: OSM tags for POI search
            specific_location: Specific location/address
            query_area: Optional custom query area (defaults to current_search_area)

        Returns:
            GeoDataFrame of POIs or None if not found
        """
        if specific_location:
            try:
                location_gdf = ox.geocode_to_gdf(specific_location)
                location_point = location_gdf.geometry.iloc[0].centroid
            except Exception:
                try:
                    lat, lon = ox.geocode(specific_location)
                    location_point = Point(lon, lat)
                except Exception as e:
                    logger.error(f"Could not geocode: {specific_location} - {e}")
                    return None

            return gpd.GeoDataFrame(
                [{"name": specific_location, "geometry": location_point}],
                crs=self.crs,
            )
        elif poi_type:
            # Use provided query_area or fall back to current_search_area
            search_polygon = query_area if query_area is not None else self.current_search_area
            try:
                pois = ox.features_from_polygon(search_polygon, tags=poi_type)
                return pois
            except Exception as e:
                logger.error(f"No POIs found: {e}")
                return None
        else:
            return None

    def get_current_result(self) -> gpd.GeoDataFrame:
        """Get the current filtered area as GeoDataFrame."""
        return gpd.GeoDataFrame(
            [
                {
                    "geometry": self.current_search_area,
                    "criteria_count": len(self.criteria_results),
                    "area_sq_miles": self._calculate_area_sq_miles(
                        self.current_search_area
                    ),
                }
            ],
            crs=self.crs,
        )

    def query_pois_in_polygon(
        self, polygon: Polygon, poi_type_key: str
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Query POIs within a polygon and return structured data.

        Args:
            polygon: Shapely Polygon to search within
            poi_type_key: POI type name from POI_TYPES (e.g., 'Restaurant')

        Returns:
            Tuple of (list of POI dicts, GeoJSON FeatureCollection)

        Raises:
            ValueError: If poi_type_key is not recognized
        """
        from app.core.constants import POI_TYPES

        poi_tags = POI_TYPES.get(poi_type_key)
        if not poi_tags:
            raise ValueError(f"Unknown POI type: {poi_type_key}")

        try:
            pois_gdf = ox.features_from_polygon(polygon, tags=poi_tags)
        except Exception as e:
            logger.warning(f"No POIs found for {poi_type_key}: {e}")
            return [], {"type": "FeatureCollection", "features": []}

        if pois_gdf.empty:
            return [], {"type": "FeatureCollection", "features": []}

        # Extract structured POI data
        poi_list = []
        for idx, row in pois_gdf.iterrows():
            geom = row.geometry

            # Handle both Point and Polygon geometries (buildings are often polygons)
            if geom.geom_type == "Polygon" or geom.geom_type == "MultiPolygon":
                centroid = geom.centroid
                lat, lon = centroid.y, centroid.x
            else:
                lat, lon = geom.y, geom.x

            # Build address from components if available
            address_parts = []
            if "addr:housenumber" in row and row["addr:housenumber"]:
                address_parts.append(str(row["addr:housenumber"]))
            if "addr:street" in row and row["addr:street"]:
                address_parts.append(str(row["addr:street"]))
            address = " ".join(address_parts) if address_parts else None

            poi_list.append({
                "id": str(idx),
                "name": row.get("name", "Unknown") if "name" in row else "Unknown",
                "poi_type": poi_type_key,
                "lat": lat,
                "lon": lon,
                "address": address,
                "opening_hours": row.get("opening_hours") if "opening_hours" in row else None,
                "phone": row.get("phone") if "phone" in row else None,
                "website": row.get("website") if "website" in row else None,
            })

        # Convert to GeoJSON
        geojson = json.loads(pois_gdf.to_json())

        logger.info(f"Found {len(poi_list)} POIs of type {poi_type_key}")
        return poi_list, geojson
