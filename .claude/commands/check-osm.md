# Check OSM Data Coverage

Verify OpenStreetMap data availability and quality for a target location.

## Steps

1. Activate the backend virtual environment
2. Run a Python script to query OSM for POI counts:
   ```python
   import osmnx as ox
   from app.core.constants import POI_TYPES

   location = "Durham, NC"  # Or specified location

   # Get location boundary
   gdf = ox.geocode_to_gdf(location)
   boundary = gdf.geometry.iloc[0]

   # Check each POI type
   results = {}
   for name, tags in POI_TYPES.items():
       try:
           pois = ox.features_from_polygon(boundary, tags=tags)
           results[name] = len(pois)
       except:
           results[name] = 0

   # Report results
   for name, count in sorted(results.items(), key=lambda x: -x[1]):
       status = "✓" if count > 10 else "⚠" if count > 0 else "✗"
       print(f"{status} {name}: {count}")
   ```

3. Report which POI types have:
   - **Good coverage** (>10 POIs): ✓
   - **Sparse coverage** (1-10 POIs): ⚠
   - **No coverage** (0 POIs): ✗

## Parameters

- `location`: Target city or region (default: "Durham, NC")
- `radius`: Optional radius in miles to limit search area

## Expected Output

```
✓ Restaurant: 847
✓ Park: 234
✓ School: 156
⚠ Swimming Pool: 8
✗ Shopping Mall: 0
```

## Notes

- Rural areas typically have sparser OSM coverage
- Some POI types may use different OSM tags in different regions
- Results are cached by OSMnx, so repeated queries are faster
