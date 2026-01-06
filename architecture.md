# Distance Finder - Architecture

## System Overview

Distance Finder is a web application that helps users find geographic areas meeting multiple proximity criteria. The system uses a React frontend for user interaction and map display, with a FastAPI backend handling geospatial computations.

```
┌─────────────────────────────────────────────────────────────────────┐
│                           USER BROWSER                               │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    React Frontend                            │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │    │
│  │  │ SearchForm   │  │   Map        │  │ ResultsSummary   │   │    │
│  │  │ Component    │  │  (Leaflet)   │  │   Component      │   │    │
│  │  └──────────────┘  └──────────────┘  └──────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                │ HTTP/REST (JSON)
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         FastAPI Backend                              │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                      API Layer                               │    │
│  │  /api/v1/analyze  │  /api/v1/validate-location  │  /poi-types│   │
│  └─────────────────────────────────────────────────────────────┘    │
│                                │                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    Service Layer                             │    │
│  │  ┌──────────────────────┐  ┌────────────────────────────┐   │    │
│  │  │  LocationAnalyzer    │  │     GeocodingService       │   │    │
│  │  │  - Buffer creation   │  │     - Location validation  │   │    │
│  │  │  - Area intersection │  │     - Coordinate lookup    │   │    │
│  │  │  - Travel time calc  │  │                            │   │    │
│  │  └──────────────────────┘  └────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                │ HTTP (Nominatim/Overpass)
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     External Services                                │
│  ┌──────────────────────┐  ┌────────────────────────────────────┐   │
│  │   OpenStreetMap      │  │         Yelp Fusion API            │   │
│  │   - Geocoding        │  │         (V1 only)                  │   │
│  │   - POI data         │  │         - Business details         │   │
│  │   - Road networks    │  │         - Ratings, hours           │   │
│  └──────────────────────┘  └────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### Frontend (React + TypeScript)

```
frontend/src/
├── api/
│   └── client.ts           # Axios/fetch wrapper for API calls
├── components/
│   ├── Map/
│   │   ├── Map.tsx         # Leaflet map container
│   │   └── MapLayers.tsx   # Polygon/marker layers
│   ├── SearchForm/
│   │   ├── SearchForm.tsx  # Main form container
│   │   ├── LocationInput.tsx   # Autocomplete location field
│   │   └── CriteriaList.tsx    # Add/remove criteria
│   └── ResultsSummary/
│       └── ResultsSummary.tsx  # Area stats, applied criteria
├── hooks/
│   └── useAnalysis.ts      # React Query hook for API
├── types/
│   └── index.ts            # TypeScript interfaces
└── App.tsx                 # Main app layout
```

**Key Libraries:**
- `react-leaflet` - Map rendering
- `@tanstack/react-query` - Server state management
- `tailwindcss` - Styling

### Backend (FastAPI + Python)

```
backend/app/
├── core/
│   ├── config.py           # Pydantic settings (from .env)
│   └── constants.py        # POI types, travel speeds
├── models/
│   └── schemas.py          # Request/response Pydantic models
├── routers/
│   └── analysis.py         # API endpoint handlers
├── services/
│   ├── geocoding.py        # Location validation service
│   └── location_analyzer.py    # Core geospatial logic
└── main.py                 # FastAPI app initialization
```

**Key Libraries:**
- `osmnx` - OpenStreetMap data access
- `geopandas` - Geospatial DataFrames
- `shapely` - Geometric operations

---

## Data Flow

### Analysis Request Flow

```
1. User Input
   ├── Center location: "Durham, NC"
   ├── Radius: 10 miles
   └── Criteria: [Park within 1mi, Grocery within 2mi]
              │
              ▼
2. Frontend Validation
   ├── Validate location via /api/v1/validate-location
   ├── Build request payload
   └── Submit to /api/v1/analyze
              │
              ▼
3. Backend Processing (LocationAnalyzer)
   ├── Geocode center → (lat, lon)
   ├── Create initial search boundary (circle buffer)
   ├── For each criterion:
   │   ├── Query OSM for POIs (or geocode specific location)
   │   ├── Create buffer around POIs
   │   └── Intersect with current search area
   └── Return final polygon as GeoJSON
              │
              ▼
4. Frontend Display
   ├── Render GeoJSON on Leaflet map
   ├── Display area statistics
   └── List applied criteria
```

### Progressive Filtering Strategy

The core optimization is **progressive filtering** - each criterion narrows the search area before the next query runs:

```
Initial Area: 314 sq mi (10-mile radius circle)
        │
        ▼
After "Park within 1mi": 180 sq mi
        │
        ▼
After "Grocery within 2mi": 95 sq mi
        │
        ▼
After "School within 1mi": 42 sq mi (final result)
```

This reduces OSM query sizes and computation time for each subsequent criterion.

---

## API Design

### RESTful Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/v1/analyze` | Run multi-criteria analysis |
| GET | `/api/v1/validate-location` | Geocode and validate location |
| GET | `/api/v1/poi-types` | List available POI categories |
| GET | `/api/v1/health` | Health check |

### Request/Response Models

```python
# Analysis Request
{
    "center": "Durham, NC",
    "radius_miles": 10.0,
    "criteria": [
        {"type": "poi", "poi_type": "Park", "mode": "distance", "value": 1.0},
        {"type": "location", "location": "Duke University", "mode": "drive", "value": 15}
    ]
}

# Analysis Response
{
    "success": true,
    "center": "Durham, NC",
    "center_lat": 35.994,
    "center_lon": -78.899,
    "initial_area_sq_miles": 314.16,
    "final_area_sq_miles": 42.5,
    "area_reduction_percent": 86.5,
    "criteria_applied": [...],
    "geojson": { "type": "FeatureCollection", ... }
}
```

---

## MVP vs V1 Architecture Differences

### MVP (Current)
- Simple convex-hull buffers for travel time
- Direct OSM queries (no caching layer)
- Single-process FastAPI server
- No persistent storage

### V1 (Planned)
- Valhalla for accurate isochrone generation
- Redis caching for OSM data
- Background task queue for long queries
- PostgreSQL/PostGIS for saved searches
- Yelp API integration for business details

```
V1 Architecture Addition:

┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Valhalla   │     │    Redis     │     │  PostgreSQL  │
│  (Isochrone) │     │   (Cache)    │     │   (Storage)  │
└──────────────┘     └──────────────┘     └──────────────┘
```

---

## Deployment Architecture

### Development
```
localhost:5173 (Frontend - Vite dev server)
       │
       ▼
localhost:8000 (Backend - Uvicorn)
       │
       ▼
OpenStreetMap APIs (External)
```

### Production (Planned)
```
Vercel/Netlify (Frontend CDN)
       │
       ▼
Railway/Render (Backend container)
       │
       ├── OSM APIs
       └── Yelp API (V1)
```

---

## Security Considerations

- **CORS:** Restricted to known frontend origins
- **Rate Limiting:** Planned for V1 (prevent OSM API abuse)
- **Input Validation:** Pydantic models enforce schema
- **No Auth (MVP):** Single-user, no sensitive data
- **API Keys:** Stored in environment variables, never committed
