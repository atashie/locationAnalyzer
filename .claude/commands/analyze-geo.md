# Test Geospatial Analysis

Run a test analysis query against the backend API to verify geospatial functionality.

## Steps

1. Check if the backend server is running on port 8000
2. If not running, start it with: `cd backend && .venv/Scripts/python.exe -m uvicorn app.main:app --reload`
3. Execute a test query using curl or httpx:
   ```
   curl -X POST http://localhost:8000/api/v1/analyze \
     -H "Content-Type: application/json" \
     -d '{"center": "Durham, NC", "radius_miles": 5, "criteria": []}'
   ```
4. Report the response including:
   - HTTP status code
   - Response time
   - Center coordinates found
   - Initial and final area in square miles
5. If the query includes criteria, verify each criterion was applied correctly

## Expected Output

A successful response should include:
- `success: true`
- Valid `center_lat` and `center_lon` coordinates
- `initial_area_sq_miles` approximately matching π × radius²
- `geojson` containing a valid FeatureCollection

## Common Issues

- **Connection refused**: Backend not running
- **Timeout**: OSM API may be slow, increase timeout
- **Geocoding failed**: Try a more specific location string
