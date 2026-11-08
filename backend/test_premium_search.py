"""Test premium search endpoint."""
import httpx
import time

base_url = 'https://locationanalyzer-production.up.railway.app/api/v1'

print('=== Premium Search Test ===')
print()

# Step 1: Run analysis to get polygon
print('1. Running analysis to get polygon...')
analysis_payload = {
    'center': 'Durham, NC',
    'radius_miles': 3,
    'criteria': [
        {'type': 'poi', 'poi_type': 'Restaurant', 'mode': 'distance', 'value': 0.5, 'name': 'Near restaurants'}
    ]
}

start = time.perf_counter()
with httpx.Client(timeout=120) as client:
    r = client.post(f'{base_url}/analyze', json=analysis_payload)
elapsed = time.perf_counter() - start

print(f'   Status: {r.status_code}')
print(f'   Time: {elapsed:.2f}s')

if r.status_code != 200:
    print(f'   Error: {r.text[:500]}')
    exit(1)

analysis_result = r.json()
geojson = analysis_result.get('geojson')
print(f'   Got polygon')
print()

# Step 2: Run premium search
print('2. Running premium search for restaurants...')
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
    print(f'   Success: {data.get("success")}')
    print(f'   Total found: {data.get("total_found")}')
    print(f'   Centroids searched: {data.get("centroids_searched")}')
    print(f'   API calls used: {data.get("api_calls_used")}')
    print()

    locations = data.get('locations', [])
    if locations:
        print('   Locations:')
        for loc in locations[:5]:
            rating = loc.get('rating', 'N/A')
            reviews = loc.get('num_reviews', 0)
            price = loc.get('price_level', 'N/A')
            photos = len(loc.get('photos', []))
            print(f'   - {loc.get("name")}')
            print(f'     Rating: {rating} | Reviews: {reviews} | Price: {price} | Photos: {photos}')
else:
    print(f'   Error: {r.text[:500]}')

print()
print('=== Test Complete ===')
