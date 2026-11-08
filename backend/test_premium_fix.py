"""Test Premium Search fix - lat/lon and polygon filtering."""
import httpx
import time

base_url = 'https://locationanalyzer-production.up.railway.app/api/v1'

print('=== Premium Search Fix Test ===')
print()

# Step 1: Run analysis
print('1. Running analysis...')
analysis_payload = {
    'center': 'Durham, NC',
    'radius_miles': 3,
    'criteria': [
        {'type': 'poi', 'poi_type': 'Restaurant', 'mode': 'distance', 'value': 0.5}
    ]
}

with httpx.Client(timeout=120) as client:
    r = client.post(f'{base_url}/analyze', json=analysis_payload)

if r.status_code != 200:
    print(f'   Analysis failed: {r.text[:200]}')
    exit(1)

geojson = r.json().get('geojson')
print(f'   Got polygon')
print()

# Step 2: Run premium search
print('2. Running premium search...')
premium_payload = {
    'geojson': geojson,
    'category': 'restaurants',
    'max_locations': 5
}

start = time.perf_counter()
with httpx.Client(timeout=120) as client:
    r = client.post(f'{base_url}/premium-search', json=premium_payload)
elapsed = time.perf_counter() - start

print(f'   Status: {r.status_code}')
print(f'   Time: {elapsed:.2f}s')

if r.status_code == 200:
    data = r.json()
    print(f'   Valid locations: {data.get("total_found")}')
    print(f'   Centroids searched: {data.get("centroids_searched")}')
    print(f'   API calls: {data.get("api_calls_used")}')
    print()

    locations = data.get('locations', [])
    if locations:
        print('   Locations with coordinates:')
        for loc in locations[:5]:
            print(f'   - {loc.get("name")}')
            print(f'     Lat: {loc.get("lat")}, Lon: {loc.get("lon")}')
            print(f'     Rating: {loc.get("rating")} | Reviews: {loc.get("num_reviews")}')
    else:
        print('   No locations found inside polygon')
else:
    print(f'   Error: {r.text[:300]}')

print()
print('=== Test Complete ===')
