"""Test TripAdvisor nearby_search directly."""
import httpx

from tripadvisor_test_env import load_api_key

# Test coordinates (Durham, NC area)
lat, lon = 35.994, -78.899

api_key = load_api_key()
url = 'https://api.content.tripadvisor.com/api/v1/location/nearby_search'
params = {
    'key': api_key,
    'latLong': f'{lat},{lon}',
    'category': 'restaurants',
    'language': 'en'
}

print('Testing TripAdvisor nearby_search directly...')
print(f'URL: {url}')
print(f'Lat/Lon: {lat}, {lon}')
print()

try:
    with httpx.Client(timeout=30) as client:
        response = client.get(url, params=params)
        print(f'Status: {response.status_code}')

        if response.status_code == 200:
            data = response.json()
            locations = data.get('data', [])
            print(f'Locations found: {len(locations)}')
            print()

            for loc in locations[:5]:
                print(f'- {loc.get("name")}')
                print(f'  ID: {loc.get("location_id")}')
                print(f'  Lat/Lon: {loc.get("latitude")}, {loc.get("longitude")}')
                addr = loc.get('address_obj', {})
                print(f'  Address: {addr.get("address_string", "N/A")}')
                print()
        else:
            print(f'Error: {response.text[:500]}')
except Exception as e:
    print(f'Exception: {e}')
