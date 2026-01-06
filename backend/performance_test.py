"""
Performance testing script for Distance Finder analysis.
Runs 100 random tests with detailed timing instrumentation.
"""

import json
import logging
import random
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import geopandas as gpd
import osmnx as ox
from shapely.geometry import Point

# Configure OSMnx
ox.settings.use_cache = True
ox.settings.log_console = False
ox.settings.requests_timeout = 300

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# POI types from constants
POI_TYPES: Dict[str, Dict[str, str]] = {
    "Grocery Store": {"shop": "supermarket"},
    "School": {"amenity": "school"},
    "Park": {"leisure": "park"},
    "Restaurant": {"amenity": "restaurant"},
    "Coffee Shop": {"amenity": "cafe"},
    "Hospital": {"amenity": "hospital"},
    "Pharmacy": {"amenity": "pharmacy"},
    "Library": {"amenity": "library"},
    "Gym/Fitness": {"leisure": "fitness_centre"},
    "Bus Stop": {"highway": "bus_stop"},
    "Bank": {"amenity": "bank"},
    "Bar": {"amenity": "bar"},
    "Gas Station": {"amenity": "fuel"},
    "Playground": {"leisure": "playground"},
}

TRAVEL_SPEEDS = {"walk": 3.0, "bike": 12.0, "drive": 30.0}
BUFFER_ADJUSTMENTS = {"walk": 1.2, "bike": 1.3, "drive": 1.5}

# Test locations (cities in NC for variety)
TEST_LOCATIONS = [
    "Durham, NC",
    "Raleigh, NC",
    "Chapel Hill, NC",
    "Cary, NC",
    "Apex, NC",
]

# Sample specific locations for location-type criteria
SPECIFIC_LOCATIONS = [
    "Duke University, Durham, NC",
    "NC State University, Raleigh, NC",
    "UNC Chapel Hill, NC",
    "RDU Airport, NC",
    "Durham Bulls Athletic Park, Durham, NC",
]


@dataclass
class TimingResult:
    """Timing data for a single operation."""
    operation: str
    duration_ms: float
    details: str = ""


@dataclass
class CriterionTiming:
    """Timing data for a single criterion."""
    criterion_name: str
    criterion_type: str  # 'poi' or 'location'
    poi_query_ms: float = 0.0
    location_geocode_ms: float = 0.0
    crs_projection_ms: float = 0.0
    buffer_creation_ms: float = 0.0
    unary_union_ms: float = 0.0
    intersection_ms: float = 0.0
    total_ms: float = 0.0
    poi_count: int = 0
    success: bool = True
    error: str = ""


@dataclass
class TestResult:
    """Complete timing results for a single test."""
    test_id: int
    center_location: str
    radius_miles: float
    num_criteria: int

    # Initialization timings
    center_geocode_ms: float = 0.0
    boundary_creation_ms: float = 0.0

    # Criterion timings
    criteria_timings: List[CriterionTiming] = field(default_factory=list)

    # Final processing
    result_processing_ms: float = 0.0
    geojson_conversion_ms: float = 0.0

    # Totals
    total_time_ms: float = 0.0
    success: bool = True
    error: str = ""

    # Results
    initial_area_sq_miles: float = 0.0
    final_area_sq_miles: float = 0.0


class InstrumentedLocationAnalyzer:
    """Location analyzer with detailed timing instrumentation."""

    def __init__(self, center_location: str, max_radius_miles: float = 25.0):
        self.timings: Dict[str, float] = {}
        self.center_location = center_location
        self.max_radius_miles = max_radius_miles
        self.crs = "EPSG:4326"
        self.criteria_results: List[Dict[str, Any]] = []

        # Time center geocoding
        start = time.perf_counter()
        try:
            location_gdf = ox.geocode_to_gdf(center_location)
            self.center_point = location_gdf.geometry.iloc[0].centroid
        except Exception:
            lat, lon = ox.geocode(center_location)
            self.center_point = Point(lon, lat)
        self.timings["center_geocode"] = (time.perf_counter() - start) * 1000

        # Time boundary creation
        start = time.perf_counter()
        self.utm_crs = self._estimate_utm_crs(self.center_point.x, self.center_point.y)
        center_gdf = gpd.GeoDataFrame([{"geometry": self.center_point}], crs=self.crs)
        center_projected = center_gdf.to_crs(self.utm_crs)
        buffer_meters = max_radius_miles * 1609.34
        search_boundary = center_projected.buffer(buffer_meters)
        self.search_boundary = search_boundary.to_crs(self.crs).iloc[0]
        self.current_search_area = self.search_boundary
        self.timings["boundary_creation"] = (time.perf_counter() - start) * 1000

    def _estimate_utm_crs(self, lon: float, lat: float) -> str:
        utm_zone = int((lon + 180) / 6) + 1
        return f"EPSG:326{utm_zone:02d}" if lat >= 0 else f"EPSG:327{utm_zone:02d}"

    def _calculate_area_sq_miles(self, geometry) -> float:
        gdf = gpd.GeoDataFrame([{"geometry": geometry}], crs=self.crs)
        gdf_projected = gdf.to_crs(self.utm_crs)
        area_sq_m = gdf_projected.geometry.area.iloc[0]
        return area_sq_m / 2589988.11

    def add_criterion_with_timing(
        self,
        poi_type: Optional[Dict[str, str]] = None,
        specific_location: Optional[str] = None,
        max_distance_miles: float = 1.0,
        travel_mode: Optional[str] = None,
        max_time_minutes: Optional[int] = None,
        criterion_name: str = "",
    ) -> CriterionTiming:
        """Add criterion with detailed timing for each step."""

        timing = CriterionTiming(
            criterion_name=criterion_name,
            criterion_type="location" if specific_location else "poi",
        )

        total_start = time.perf_counter()

        try:
            # Step 1: Get POIs or geocode location
            start = time.perf_counter()
            pois = None

            if specific_location:
                try:
                    location_gdf = ox.geocode_to_gdf(specific_location)
                    location_point = location_gdf.geometry.iloc[0].centroid
                except Exception:
                    lat, lon = ox.geocode(specific_location)
                    location_point = Point(lon, lat)
                pois = gpd.GeoDataFrame(
                    [{"name": specific_location, "geometry": location_point}],
                    crs=self.crs,
                )
                timing.location_geocode_ms = (time.perf_counter() - start) * 1000
                timing.poi_count = 1
            elif poi_type:
                pois = ox.features_from_polygon(self.current_search_area, tags=poi_type)
                timing.poi_query_ms = (time.perf_counter() - start) * 1000
                timing.poi_count = len(pois) if pois is not None else 0

            if pois is None or len(pois) == 0:
                timing.success = False
                timing.error = "No POIs found"
                timing.total_ms = (time.perf_counter() - total_start) * 1000
                return timing

            # Calculate distance
            if travel_mode and max_time_minutes:
                speed_mph = TRAVEL_SPEEDS.get(travel_mode, 3.0)
                max_distance_miles = (max_time_minutes / 60) * speed_mph
                adjustment = BUFFER_ADJUSTMENTS.get(travel_mode, 1.2)
                max_distance_miles = max_distance_miles / adjustment

            # Step 2: CRS projection
            start = time.perf_counter()
            pois_projected = pois.to_crs(self.utm_crs)
            timing.crs_projection_ms = (time.perf_counter() - start) * 1000

            # Step 3: Buffer creation
            start = time.perf_counter()
            buffer_meters = max_distance_miles * 1609.34
            buffers = pois_projected.geometry.buffer(buffer_meters)
            timing.buffer_creation_ms = (time.perf_counter() - start) * 1000

            # Step 4: Unary union
            start = time.perf_counter()
            combined_buffer = buffers.unary_union
            timing.unary_union_ms = (time.perf_counter() - start) * 1000

            # Step 5: Intersection
            start = time.perf_counter()
            result_gdf = gpd.GeoDataFrame(
                [{"geometry": combined_buffer}], crs=self.utm_crs
            ).to_crs(self.crs)
            result_geometry = result_gdf.geometry.iloc[0].intersection(self.current_search_area)
            timing.intersection_ms = (time.perf_counter() - start) * 1000

            self.current_search_area = result_geometry
            self.criteria_results.append({
                "name": criterion_name,
                "geometry": result_geometry,
                "description": f"Within {max_distance_miles:.1f} miles",
            })

        except Exception as e:
            timing.success = False
            timing.error = str(e)

        timing.total_ms = (time.perf_counter() - total_start) * 1000
        return timing

    def get_current_result_with_timing(self) -> tuple:
        """Get result with timing."""
        start = time.perf_counter()
        result_gdf = gpd.GeoDataFrame(
            [{
                "geometry": self.current_search_area,
                "criteria_count": len(self.criteria_results),
                "area_sq_miles": self._calculate_area_sq_miles(self.current_search_area),
            }],
            crs=self.crs,
        )
        result_time = (time.perf_counter() - start) * 1000

        start = time.perf_counter()
        geojson = result_gdf.__geo_interface__
        geojson_time = (time.perf_counter() - start) * 1000

        return result_gdf, geojson, result_time, geojson_time


def generate_random_criterion() -> dict:
    """Generate a random criterion for testing."""
    criterion_type = random.choice(["poi", "location"])

    if criterion_type == "poi":
        poi_name = random.choice(list(POI_TYPES.keys()))
        mode = random.choice(["distance", "walk", "bike", "drive"])

        if mode == "distance":
            value = round(random.uniform(0.5, 3.0), 1)
        else:
            value = random.randint(5, 20)

        return {
            "type": "poi",
            "poi_type": poi_name,
            "poi_tags": POI_TYPES[poi_name],
            "mode": mode,
            "value": value,
        }
    else:
        location = random.choice(SPECIFIC_LOCATIONS)
        mode = random.choice(["distance", "walk", "bike", "drive"])

        if mode == "distance":
            value = round(random.uniform(1.0, 5.0), 1)
        else:
            value = random.randint(5, 30)

        return {
            "type": "location",
            "location": location,
            "mode": mode,
            "value": value,
        }


def run_single_test(test_id: int) -> TestResult:
    """Run a single test with random parameters."""
    center = random.choice(TEST_LOCATIONS)
    radius = random.uniform(5, 15)
    num_criteria = random.randint(0, 4)

    result = TestResult(
        test_id=test_id,
        center_location=center,
        radius_miles=radius,
        num_criteria=num_criteria,
    )

    total_start = time.perf_counter()

    try:
        # Initialize analyzer
        analyzer = InstrumentedLocationAnalyzer(center, radius)
        result.center_geocode_ms = analyzer.timings["center_geocode"]
        result.boundary_creation_ms = analyzer.timings["boundary_creation"]

        # Generate and apply criteria
        for i in range(num_criteria):
            criterion = generate_random_criterion()

            if criterion["type"] == "poi":
                timing = analyzer.add_criterion_with_timing(
                    poi_type=criterion["poi_tags"],
                    max_distance_miles=criterion["value"] if criterion["mode"] == "distance" else None,
                    travel_mode=criterion["mode"] if criterion["mode"] != "distance" else None,
                    max_time_minutes=int(criterion["value"]) if criterion["mode"] != "distance" else None,
                    criterion_name=criterion["poi_type"],
                )
            else:
                timing = analyzer.add_criterion_with_timing(
                    specific_location=criterion["location"],
                    max_distance_miles=criterion["value"] if criterion["mode"] == "distance" else None,
                    travel_mode=criterion["mode"] if criterion["mode"] != "distance" else None,
                    max_time_minutes=int(criterion["value"]) if criterion["mode"] != "distance" else None,
                    criterion_name=criterion["location"][:30],
                )

            result.criteria_timings.append(timing)

        # Get results
        result_gdf, geojson, result_time, geojson_time = analyzer.get_current_result_with_timing()
        result.result_processing_ms = result_time
        result.geojson_conversion_ms = geojson_time

        result.initial_area_sq_miles = analyzer._calculate_area_sq_miles(analyzer.search_boundary)
        result.final_area_sq_miles = result_gdf["area_sq_miles"].iloc[0]

    except Exception as e:
        result.success = False
        result.error = str(e)

    result.total_time_ms = (time.perf_counter() - total_start) * 1000
    return result


def analyze_results(results: List[TestResult]) -> dict:
    """Analyze timing results and identify bottlenecks."""

    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    # Aggregate timings
    center_geocode_times = [r.center_geocode_ms for r in successful]
    boundary_times = [r.boundary_creation_ms for r in successful]
    total_times = [r.total_time_ms for r in successful]

    # Criterion-level analysis
    all_criterion_timings = []
    poi_query_times = []
    location_geocode_times = []
    projection_times = []
    buffer_times = []
    union_times = []
    intersection_times = []

    for r in successful:
        for ct in r.criteria_timings:
            all_criterion_timings.append(ct)
            if ct.poi_query_ms > 0:
                poi_query_times.append(ct.poi_query_ms)
            if ct.location_geocode_ms > 0:
                location_geocode_times.append(ct.location_geocode_ms)
            if ct.crs_projection_ms > 0:
                projection_times.append(ct.crs_projection_ms)
            if ct.buffer_creation_ms > 0:
                buffer_times.append(ct.buffer_creation_ms)
            if ct.unary_union_ms > 0:
                union_times.append(ct.unary_union_ms)
            if ct.intersection_ms > 0:
                intersection_times.append(ct.intersection_ms)

    def stats(times: List[float]) -> dict:
        if not times:
            return {"count": 0, "mean": 0, "min": 0, "max": 0, "median": 0, "total": 0}
        times_sorted = sorted(times)
        return {
            "count": len(times),
            "mean": sum(times) / len(times),
            "min": min(times),
            "max": max(times),
            "median": times_sorted[len(times) // 2],
            "total": sum(times),
        }

    analysis = {
        "summary": {
            "total_tests": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "total_criteria_tested": len(all_criterion_timings),
        },
        "total_test_time": stats(total_times),
        "initialization": {
            "center_geocode": stats(center_geocode_times),
            "boundary_creation": stats(boundary_times),
        },
        "criteria_operations": {
            "poi_query_osm": stats(poi_query_times),
            "location_geocode": stats(location_geocode_times),
            "crs_projection": stats(projection_times),
            "buffer_creation": stats(buffer_times),
            "unary_union": stats(union_times),
            "intersection": stats(intersection_times),
        },
        "bottleneck_ranking": [],
    }

    # Rank bottlenecks by total time spent
    operations = [
        ("Center Geocoding", stats(center_geocode_times)["total"]),
        ("POI Query (OSM)", stats(poi_query_times)["total"]),
        ("Location Geocoding", stats(location_geocode_times)["total"]),
        ("CRS Projection", stats(projection_times)["total"]),
        ("Buffer Creation", stats(buffer_times)["total"]),
        ("Unary Union", stats(union_times)["total"]),
        ("Intersection", stats(intersection_times)["total"]),
        ("Boundary Creation", stats(boundary_times)["total"]),
    ]

    operations.sort(key=lambda x: x[1], reverse=True)
    analysis["bottleneck_ranking"] = [
        {"operation": op, "total_time_ms": time, "percentage": (time / sum(t for _, t in operations)) * 100 if sum(t for _, t in operations) > 0 else 0}
        for op, time in operations
    ]

    return analysis


def main():
    """Run performance tests."""
    logger.info("=" * 60)
    logger.info("Distance Finder Performance Test")
    logger.info("=" * 60)
    logger.info(f"Running 100 tests with 0-4 criteria each...")
    logger.info("")

    results: List[TestResult] = []

    for i in range(100):
        logger.info(f"Test {i+1}/100...")
        result = run_single_test(i + 1)
        results.append(result)

        status = "OK" if result.success else f"FAILED: {result.error}"
        logger.info(f"  Center: {result.center_location}, Criteria: {result.num_criteria}, "
                   f"Time: {result.total_time_ms:.0f}ms - {status}")

    # Save raw results
    output_dir = Path("performance_results")
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save detailed results as JSON
    results_data = []
    for r in results:
        data = {
            "test_id": r.test_id,
            "center_location": r.center_location,
            "radius_miles": r.radius_miles,
            "num_criteria": r.num_criteria,
            "center_geocode_ms": r.center_geocode_ms,
            "boundary_creation_ms": r.boundary_creation_ms,
            "result_processing_ms": r.result_processing_ms,
            "geojson_conversion_ms": r.geojson_conversion_ms,
            "total_time_ms": r.total_time_ms,
            "success": r.success,
            "error": r.error,
            "initial_area_sq_miles": r.initial_area_sq_miles,
            "final_area_sq_miles": r.final_area_sq_miles,
            "criteria_timings": [asdict(ct) for ct in r.criteria_timings],
        }
        results_data.append(data)

    with open(output_dir / f"raw_results_{timestamp}.json", "w") as f:
        json.dump(results_data, f, indent=2)

    # Analyze and save analysis
    analysis = analyze_results(results)

    with open(output_dir / f"analysis_{timestamp}.json", "w") as f:
        json.dump(analysis, f, indent=2)

    # Print analysis
    logger.info("")
    logger.info("=" * 60)
    logger.info("PERFORMANCE ANALYSIS")
    logger.info("=" * 60)

    logger.info(f"\nSUMMARY:")
    logger.info(f"  Total tests: {analysis['summary']['total_tests']}")
    logger.info(f"  Successful: {analysis['summary']['successful']}")
    logger.info(f"  Failed: {analysis['summary']['failed']}")
    logger.info(f"  Total criteria tested: {analysis['summary']['total_criteria_tested']}")

    logger.info(f"\nTOTAL TEST TIME (ms):")
    tt = analysis['total_test_time']
    logger.info(f"  Mean: {tt['mean']:.1f}ms")
    logger.info(f"  Min: {tt['min']:.1f}ms")
    logger.info(f"  Max: {tt['max']:.1f}ms")
    logger.info(f"  Median: {tt['median']:.1f}ms")

    logger.info(f"\nINITIALIZATION:")
    cg = analysis['initialization']['center_geocode']
    logger.info(f"  Center Geocoding - Mean: {cg['mean']:.1f}ms, Total: {cg['total']:.0f}ms")
    bc = analysis['initialization']['boundary_creation']
    logger.info(f"  Boundary Creation - Mean: {bc['mean']:.1f}ms, Total: {bc['total']:.0f}ms")

    logger.info(f"\nCRITERIA OPERATIONS:")
    for op_name, op_stats in analysis['criteria_operations'].items():
        if op_stats['count'] > 0:
            logger.info(f"  {op_name}:")
            logger.info(f"    Count: {op_stats['count']}, Mean: {op_stats['mean']:.1f}ms, "
                       f"Total: {op_stats['total']:.0f}ms")

    logger.info(f"\nBOTTLENECK RANKING (by total time spent):")
    for i, item in enumerate(analysis['bottleneck_ranking'], 1):
        logger.info(f"  {i}. {item['operation']}: {item['total_time_ms']:.0f}ms ({item['percentage']:.1f}%)")

    logger.info("")
    logger.info(f"Results saved to: {output_dir}/")
    logger.info(f"  - raw_results_{timestamp}.json")
    logger.info(f"  - analysis_{timestamp}.json")

    return analysis


if __name__ == "__main__":
    main()
