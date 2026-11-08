"""Test which TripAdvisor endpoints are available."""
import httpx

from tripadvisor_test_env import load_api_key

api_key = load_api_key()
base = 'https://api.content.tripadvisor.com/api/v1'

# Test coordinates
lat, lon = 35.994, -78.899

endpoints = [
    ('location/search', {'key': api_key, 'searchQuery': 'restaurant', 'latLong': f'{lat},{lon}', 'language': 'en'}),
    ('location/nearby_search', {'key': api_key, 'latLong': f'{lat},{lon}', 'category': 'restaurants', 'language': 'en'}),
]

print('Testing TripAdvisor API endpoints...')
print()

for endpoint, params in endpoints:
    url = f'{base}/{endpoint}'
    print(f'Testing: {endpoint}')
    try:
        with httpx.Client(timeout=30) as client:
            response = client.get(url, params=params)
            print(f'  Status: {response.status_code}')
            if response.status_code == 200:
                data = response.json()
                count = len(data.get('data', []))
                print(f'  Results: {count}')
                if count > 0:
                    print(f'  First: {data["data"][0].get("name", "?")}')
            else:
                msg = response.json().get('Message', response.text[:100])
                print(f'  Error: {msg}')
    except Exception as e:
        print(f'  Exception: {e}')
    print()
