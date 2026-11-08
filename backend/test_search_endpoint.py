"""Test TripAdvisor location/search endpoint."""
import httpx

from tripadvisor_test_env import load_api_key, masked

api_key = load_api_key()
base = 'https://api.content.tripadvisor.com/api/v1'

# Test coordinates (Durham, NC)
lat, lon = 35.994, -78.899

params = {
    'key': api_key,
    'searchQuery': 'restaurant',
    'latLong': f'{lat},{lon}',
    'category': 'restaurants',
    'language': 'en'
}

print('Testing TripAdvisor location/search...')
print(f'Params: {masked(params)}')
print()

try:
    with httpx.Client(timeout=30) as client:
        response = client.get(f'{base}/location/search', params=params)
        print(f'Status: {response.status_code}')

        if response.status_code == 200:
            data = response.json()
            locations = data.get('data', [])
            print(f'Locations found: {len(locations)}')
            print()

            for loc in locations[:5]:
                print(f'- {loc.get("name")}')
                print(f'  ID: {loc.get("location_id")}')
                addr = loc.get('address_obj', {})
                print(f'  Address: {addr.get("address_string", "N/A")}')
                print()
        else:
            print(f'Error: {response.text[:500]}')
except Exception as e:
    print(f'Exception: {e}')
