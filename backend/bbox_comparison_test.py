"""
Comparison test: features_from_polygon() vs features_from_bbox()

Tests whether bounding box queries with Python filtering are more efficient
than direct polygon queries for multi-criteria searches.
"""

import time
import statistics
import osmnx as ox
import geopandas as gpd
from shapely.geometry import Point
from typing import Dict, List, Any

# Configure OSMnx
ox.settings.use_cache = True
ox.settings.log_console = False
ox.settings.requests_timeout = 300

# Test configuration
TEST_LOCATIONS = [
    ("Durham, NC", 10),
    ("Raleigh, NC", 8),
    ("Chapel Hill, NC", 5),
    ("Cary, NC", 7),
]

POI_TYPES = [
    ("Restaurant", {"amenity": "restaurant"}),
    ("Park", {"leisure": "park"}),
    ("School", {"amenity": "school"}),
    ("Grocery Store", {"shop": "supermarket"}),
]


def create_search_boundary(center_location: str, radius_miles: float):
    """Create search boundary polygon from center and radius."""
    # Geocode center
    try:
        location_gdf = ox.geocode_to_gdf(center_location)
        center_point = location_gdf.geometry.iloc[0].centroid
    except Exception:
        lat, lon = ox.geocode(center_location)
        center_point = Point(lon, lat)

    # Estimate UTM CRS
    utm_zone = int((center_point.x + 180) / 6) + 1
    utm_crs = f"EPSG:326{utm_zone:02d}" if center_point.y >= 0 else f"EPSG:327{utm_zone:02d}"

    # Create circular boundary
    center_gdf = gpd.GeoDataFrame([{"geometry": center_point}], crs="EPSG:4326")
    center_projected = center_gdf.to_crs(utm_crs)
    buffer_meters = radius_miles * 1609.34
    search_boundary = center_projected.buffer(buffer_meters).to_crs("EPSG:4326").iloc[0]

    return search_boundary, center_point


def test_polygon_approach(polygon, poi_tags: Dict[str, str]) -> Dict[str, Any]:
    """Test the current polygon-based approach."""
    start = time.perf_counter()
    try:
        pois = ox.features_from_polygon(polygon, tags=poi_tags)
        elapsed = time.perf_counter() - start
        poi_count = len(pois) if pois is not None and not pois.empty else 0
        return {
            "method": "polygon",
            "elapsed_s": elapsed,
            "poi_count": poi_count,
            "success": True,
            "error": None,
        }
    except Exception as e:
        elapsed = time.perf_counter() - start
        return {
            "method": "polygon",
            "elapsed_s": elapsed,
            "poi_count": 0,
            "success": False,
            "error": str(e),
        }


def test_stable_polygon_approach(original_boundary, current_area, poi_tags: Dict[str, str]) -> Dict[str, Any]:
    """Test querying the ORIGINAL boundary, then filtering to current area."""
    start = time.perf_counter()
    try:
        # Always query the stable original boundary (cacheable!)
        all_pois = ox.features_from_polygon(original_boundary, tags=poi_tags)

        # Filter to current search area in Python
        if all_pois is not None and not all_pois.empty:
            filtered_pois = all_pois[all_pois.geometry.intersects(current_area)]
            poi_count = len(filtered_pois)
            total_count = len(all_pois)
        else:
            poi_count = 0
            total_count = 0

        elapsed = time.perf_counter() - start
        return {
            "method": "stable_polygon",
            "elapsed_s": elapsed,
            "poi_count": poi_count,
            "total_fetched": total_count,
            "filter_overhead_pct": ((total_count - poi_count) / total_count * 100) if total_count > 0 else 0,
            "success": True,
            "error": None,
        }
    except Exception as e:
        elapsed = time.perf_counter() - start
        return {
            "method": "stable_polygon",
            "elapsed_s": elapsed,
            "poi_count": 0,
            "total_fetched": 0,
            "filter_overhead_pct": 0,
            "success": False,
            "error": str(e),
        }


def test_stable_polygon_cache_behavior(original_boundary, poi_tags: Dict[str, str]) -> Dict[str, Any]:
    """Test stable polygon approach with cache - simulates multiple criteria."""

    # First query (should be cache miss or hit depending on prior tests)
    start1 = time.perf_counter()
    try:
        all_pois = ox.features_from_polygon(original_boundary, tags=poi_tags)
        elapsed1 = time.perf_counter() - start1
    except Exception as e:
        return {"error": str(e)}

    # Second query (should be cache hit - same polygon!)
    start2 = time.perf_counter()
    try:
        all_pois_2 = ox.features_from_polygon(original_boundary, tags=poi_tags)
        elapsed2 = time.perf_counter() - start2
    except Exception as e:
        return {"error": str(e)}

    # Third query with filter (simulates second criterion with smaller search area)
    start3 = time.perf_counter()
    try:
        all_pois_3 = ox.features_from_polygon(original_boundary, tags=poi_tags)
        # Simulate shrunk search area (after first criterion applied)
        shrunk_area = original_boundary.buffer(-0.02)  # ~2km shrink
        if shrunk_area.is_valid and not shrunk_area.is_empty:
            filtered = all_pois_3[all_pois_3.geometry.intersects(shrunk_area)]
            filtered_count = len(filtered)
        else:
            filtered_count = 0
        elapsed3 = time.perf_counter() - start3
    except Exception as e:
        return {"error": str(e)}

    return {
        "first_query_s": elapsed1,
        "cached_query_s": elapsed2,
        "cached_with_filter_s": elapsed3,
        "cache_speedup": elapsed1 / elapsed2 if elapsed2 > 0 else 0,
        "poi_count": len(all_pois) if all_pois is not None else 0,
        "filtered_count": filtered_count if 'filtered_count' in dir() else 0,
    }


def run_comparison_tests(num_tests: int = 20):
    """Run comparison tests: dynamic polygon vs stable polygon + filter."""
    print("=" * 70)
    print("DYNAMIC POLYGON vs STABLE POLYGON + FILTER")
    print("=" * 70)
    print(f"\nRunning {num_tests} tests...")
    print("Comparing: querying shrinking area vs querying fixed area + Python filter\n")

    dynamic_results = []
    stable_results = []
    cache_results = []

    test_count = 0
    for location, radius in TEST_LOCATIONS:
        print(f"\n--- Testing: {location} ({radius} mile radius) ---")

        # Create search boundary
        try:
            boundary, center = create_search_boundary(location, radius)
            print(f"  Boundary created: {boundary.bounds}")
        except Exception as e:
            print(f"  ERROR creating boundary: {e}")
            continue

        # Simulate a shrunk search area (as if first criterion was applied)
        shrunk_area = boundary.buffer(-0.02)  # ~2km smaller radius

        for poi_name, poi_tags in POI_TYPES:
            if test_count >= num_tests:
                break

            test_count += 1
            print(f"\n  [{test_count}/{num_tests}] {poi_name}...")

            # Test DYNAMIC polygon approach (current - queries shrunk area)
            print(f"    Dynamic (shrunk area)...", end=" ", flush=True)
            dynamic_result = test_polygon_approach(shrunk_area, poi_tags)
            dynamic_results.append(dynamic_result)
            if dynamic_result["success"]:
                print(f"{dynamic_result['elapsed_s']:.2f}s, {dynamic_result['poi_count']} POIs")
            else:
                print(f"FAILED: {dynamic_result['error'][:50]}")

            time.sleep(1)

            # Test STABLE polygon approach (proposed - queries original, filters)
            print(f"    Stable (original + filter)...", end=" ", flush=True)
            stable_result = test_stable_polygon_approach(boundary, shrunk_area, poi_tags)
            stable_results.append(stable_result)
            if stable_result["success"]:
                print(f"{stable_result['elapsed_s']:.2f}s, {stable_result['poi_count']} POIs "
                      f"(fetched {stable_result['total_fetched']}, {stable_result['filter_overhead_pct']:.1f}% filtered)")
            else:
                print(f"FAILED: {stable_result['error'][:50]}")

            time.sleep(1)

            # Test cache behavior with stable approach
            print(f"    Cache test (3 queries)...", end=" ", flush=True)
            cache_result = test_stable_polygon_cache_behavior(boundary, poi_tags)
            cache_results.append(cache_result)
            if "error" not in cache_result:
                print(f"1st: {cache_result['first_query_s']:.2f}s, "
                      f"2nd: {cache_result['cached_query_s']:.3f}s, "
                      f"3rd+filter: {cache_result['cached_with_filter_s']:.3f}s, "
                      f"Speedup: {cache_result['cache_speedup']:.0f}x")
            else:
                print(f"FAILED: {cache_result['error'][:50]}")

            time.sleep(1)

        if test_count >= num_tests:
            break

    # Analyze results
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)

    successful_dynamic = [r for r in dynamic_results if r["success"]]
    successful_stable = [r for r in stable_results if r["success"]]
    successful_cache = [r for r in cache_results if "error" not in r]

    if successful_dynamic:
        dynamic_times = [r["elapsed_s"] for r in successful_dynamic]
        print(f"\nDynamic Polygon (current approach) - {len(successful_dynamic)} successful:")
        print(f"  Mean time: {statistics.mean(dynamic_times):.2f}s")
        print(f"  Median time: {statistics.median(dynamic_times):.2f}s")
        print(f"  Min/Max: {min(dynamic_times):.2f}s / {max(dynamic_times):.2f}s")

    if successful_stable:
        stable_times = [r["elapsed_s"] for r in successful_stable]
        filter_overhead = [r["filter_overhead_pct"] for r in successful_stable]
        print(f"\nStable Polygon + Filter (proposed) - {len(successful_stable)} successful:")
        print(f"  Mean time: {statistics.mean(stable_times):.2f}s")
        print(f"  Median time: {statistics.median(stable_times):.2f}s")
        print(f"  Min/Max: {min(stable_times):.2f}s / {max(stable_times):.2f}s")
        print(f"  Avg filter overhead: {statistics.mean(filter_overhead):.1f}% of POIs filtered out")

    if successful_cache:
        first_times = [r["first_query_s"] for r in successful_cache]
        cached_times = [r["cached_query_s"] for r in successful_cache]
        filter_times = [r["cached_with_filter_s"] for r in successful_cache]
        speedups = [r["cache_speedup"] for r in successful_cache]
        print(f"\nCache Behavior with Stable Polygon ({len(successful_cache)} tests):")
        print(f"  First query mean: {statistics.mean(first_times):.2f}s")
        print(f"  Cached query mean: {statistics.mean(cached_times):.4f}s")
        print(f"  Cached + filter mean: {statistics.mean(filter_times):.4f}s")
        print(f"  Average speedup: {statistics.mean(speedups):.0f}x")

    # Comparison
    if successful_dynamic and successful_stable:
        print(f"\n--- APPROACH COMPARISON ---")
        dynamic_mean = statistics.mean([r["elapsed_s"] for r in successful_dynamic])
        stable_mean = statistics.mean([r["elapsed_s"] for r in successful_stable])
        print(f"  Dynamic (current): {dynamic_mean:.2f}s")
        print(f"  Stable + filter: {stable_mean:.2f}s")
        if stable_mean < dynamic_mean:
            print(f"  Stable is {dynamic_mean/stable_mean:.1f}x FASTER (but both hit OSM)")
        else:
            print(f"  Dynamic is {stable_mean/dynamic_mean:.1f}x faster")

    # Multi-criteria simulation - THE KEY INSIGHT
    if successful_cache:
        print(f"\n--- MULTI-CRITERIA SIMULATION (KEY RESULT) ---")
        avg_first = statistics.mean([r["first_query_s"] for r in successful_cache])
        avg_cached = statistics.mean([r["cached_query_s"] for r in successful_cache])
        avg_filter = statistics.mean([r["cached_with_filter_s"] for r in successful_cache])

        print("Scenario: 4 criteria querying same POI type (e.g., 4 'near restaurant' rules)")
        print(f"\n  CURRENT APPROACH (dynamic polygon each time):")
        print(f"    Each query hits OSM (different polygon = cache miss)")
        print(f"    Estimated time: ~{avg_first * 4:.0f}s (4 × {avg_first:.1f}s)")

        print(f"\n  PROPOSED APPROACH (stable polygon + Python filter):")
        print(f"    1st query: {avg_first:.1f}s (cache miss)")
        print(f"    2nd-4th queries: {avg_filter:.3f}s each (cache HIT + filter)")
        print(f"    Estimated time: ~{avg_first + avg_filter * 3:.1f}s")

        if avg_first > 0:
            current_time = avg_first * 4
            proposed_time = avg_first + avg_filter * 3
            print(f"\n  POTENTIAL SPEEDUP: {current_time/proposed_time:.1f}x faster!")
            print(f"  TIME SAVED: {current_time - proposed_time:.0f}s per search")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    run_comparison_tests(20)
