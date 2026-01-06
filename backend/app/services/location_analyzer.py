"""Location analysis service - core geospatial logic."""

import logging
from typing import Any, Dict, List, Optional

import geopandas as gpd
import osmnx as ox
from shapely.geometry import Point

from app.core.constants import BUFFER_ADJUSTMENTS, TRAVEL_SPEEDS

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
        utm_crs = self._estimate_utm_crs(self.center_point.x, self.center_point.y)

        # Create initial search boundary
        center_gdf = gpd.GeoDataFrame(
            [{"geometry": self.center_point}], crs=self.crs
        )
        center_projected = center_gdf.to_crs(utm_crs)

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
        utm_crs = self._estimate_utm_crs(self.center_point.x, self.center_point.y)
        gdf = gpd.GeoDataFrame([{"geometry": geometry}], crs=self.crs)
        gdf_projected = gdf.to_crs(utm_crs)
        area_sq_m = gdf_projected.geometry.area.iloc[0]
        return area_sq_m / 2589988.11  # Square meters to square miles

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
        pois = self._get_pois(poi_type, specific_location)
        if pois is None or len(pois) == 0:
            logger.warning(f"No POIs found for criterion: {criterion_name}")
            return None

        utm_crs = self._estimate_utm_crs(self.center_point.x, self.center_point.y)
        pois_projected = pois.to_crs(utm_crs)
        buffer_meters = max_distance_miles * 1609.34
        buffers = pois_projected.geometry.buffer(buffer_meters)

        combined_buffer = buffers.unary_union
        result_gdf = gpd.GeoDataFrame(
            [{"geometry": combined_buffer}], crs=utm_crs
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

        pois = self._get_pois(poi_type, specific_location)
        if pois is None or len(pois) == 0:
            logger.warning(f"No POIs found for criterion: {criterion_name}")
            return None

        utm_crs = self._estimate_utm_crs(self.center_point.x, self.center_point.y)
        pois_projected = pois.to_crs(utm_crs)
        buffer_meters = adjusted_distance * 1609.34
        buffers = pois_projected.geometry.buffer(buffer_meters)

        combined_buffer = buffers.unary_union
        result_gdf = gpd.GeoDataFrame(
            [{"geometry": combined_buffer}], crs=utm_crs
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
    ) -> Optional[gpd.GeoDataFrame]:
        """Get POIs from either type search or specific location."""
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
            try:
                pois = ox.features_from_polygon(
                    self.current_search_area, tags=poi_type
                )
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
