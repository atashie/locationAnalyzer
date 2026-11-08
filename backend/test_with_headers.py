"""Test TripAdvisor API with Referer/Origin headers."""
import httpx

from tripadvisor_test_env import load_api_key, masked

api_key = load_api_key()
referer_domain = 'https://locationanalyzer-production.up.railway.app'
base = 'https://api.content.tripadvisor.com/api/v1'

# Test coordinates (Durham, NC)
lat, lon = 35.994, -78.899

# Headers matching the API key restriction
headers = {
    'Referer': f'{referer_domain}/',
    'Origin': referer_domain,
    'Accept': 'application/json',
}

params = {
    'key': api_key,
    'searchQuery': 'Gonza Tacos',
    'latLong': f'{lat},{lon}',
    'language': 'en'
}

print('Testing TripAdvisor API with Referer/Origin headers...')
print(f'Headers: {headers}')
print(f'Params: {masked(params)}')
print()

try:
    with httpx.Client(timeout=30) as client:
        response = client.get(f'{base}/location/search', params=params, headers=headers)
        print(f'Status: {response.status_code}')

        if response.status_code == 200:
            data = response.json()
            locations = data.get('data', [])
            print(f'SUCCESS! Locations found: {len(locations)}')
            print()

            for loc in locations[:3]:
                print(f'- {loc.get("name")}')
                print(f'  ID: {loc.get("location_id")}')
                addr = loc.get('address_obj', {})
                print(f'  Address: {addr.get("address_string", "N/A")}')
                print()
        else:
            print(f'Error: {response.text[:500]}')
except Exception as e:
    print(f'Exception: {e}')
