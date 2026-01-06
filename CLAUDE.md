# Distance Finder - Claude Code Context

## Project Overview

Location finder web app helping non-tech-savvy users find areas based on proximity criteria (distance, walk/bike/drive time) to amenities and specific places.

- **Frontend:** React + TypeScript + Vite + Leaflet
- **Backend:** FastAPI + Python + GeoPandas + OSMnx
- **Data Sources:** OpenStreetMap (MVP), Yelp Fusion API (V1)

## Repository

- **GitHub:** git@github.com:atashie/locationAnalyzer.git

## Production URLs

| Environment | URL |
|-------------|-----|
| **Frontend** | https://location-analyzer-three.vercel.app |
| **Backend API** | https://locationanalyzer-production.up.railway.app |
| **API Docs** | https://locationanalyzer-production.up.railway.app/docs |

## Key Files

| File | Purpose |
|------|---------|
| `/backend/app/services/location_analyzer.py` | Core geospatial logic (ported from PoC) |
| `/backend/app/routers/analysis.py` | API endpoints + smart query ordering |
| `/backend/app/core/constants.py` | POI types, travel speeds, config |
| `/backend/performance_test.py` | Performance benchmarking suite |
| `/frontend/src/components/Map/Map.tsx` | Leaflet map with dynamic updates |
| `/frontend/src/components/SearchForm/SearchForm.tsx` | Criteria form + loading indicator |
| `/frontend/src/components/SearchForm/CriterionCard.tsx` | Individual criterion editor |
| `/Dockerfile` | Production container config for Railway |
| `/railway.toml` | Railway deployment configuration |
| `/DEPLOYMENT.md` | Step-by-step deployment guide |
| `/distanceFinder/app.py` | Original Streamlit PoC (reference only) |

## Commands

```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Mac/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev

# Tests
cd backend && pytest
cd frontend && npm test
```

## Architecture Notes

- **Progressive filtering:** Each criterion narrows the search area, making subsequent queries faster
- **Smart query ordering:** Backend reorders criteria (single location → POI, distance → walk → bike → drive)
- **Convex-hull isochrones:** MVP uses simple convex hull; V1 will use Valhalla for accurate road-network isochrones
- **Data flow:** User input → FastAPI → OSMnx/GeoPandas → GeoJSON → Leaflet map
- **Map updates:** Uses `useMap()` hook + dynamic `key` on GeoJSON to handle react-leaflet immutability
- **Performance:** OSM POI queries are the bottleneck (95%+ of time); use "Specific Place" when possible

## API Endpoints

```
POST /api/v1/analyze
  Input: { center, radius_miles, criteria[] }
  Output: { geojson, area_sq_miles, criteria_applied[] }

GET /api/v1/validate-location?q={query}
  Output: { valid, lat, lon, display_name, error_message }

GET /api/v1/poi-types
  Output: { poi_types: [{name, tags}] }
```

## Code Style

- **Python:** Black formatter, type hints required, no bare `except:` clauses
- **TypeScript:** Strict mode, Prettier formatter
- **General:** Prefer explicit error handling over silent failures

## Common Tasks

### Adding a new POI type
Edit `/backend/app/core/constants.py`:
```python
POI_TYPES = {
    "New Category": {"amenity": "new_type"},
    # ...
}
```

### Adding a new API endpoint
1. Create route in `/backend/app/routers/`
2. Add Pydantic models in `/backend/app/models/schemas.py`
3. Register router in `/backend/app/main.py`

### Adding a new React component
1. Create component in `/frontend/src/components/`
2. Add TypeScript interfaces in `/frontend/src/types/`

## Environment Variables

See `.env.example` for all configuration options. Key variables:
- `YELP_API_KEY` - Required for V1 business details
- `MAX_SEARCH_RADIUS_MILES` - Limits query size for performance
- `CORS_ORIGINS` - Allowed frontend origins

## MVP vs V1 Scope

| Feature | MVP | V1 |
|---------|-----|-----|
| Polygon visualization | Yes | Yes |
| Distance-based criteria | Yes | Yes |
| Travel-time criteria | Convex hull | Valhalla isochrones |
| List businesses in results | No | Yes (Yelp) |
| User accounts | No | Planned |

## Troubleshooting

### OSMnx queries timing out
- Reduce `MAX_SEARCH_RADIUS_MILES` in `.env`
- Check internet connection (OSM API requires network access)
- Clear cache: delete `./cache/osmnx/` folder

### CORS errors in browser
- Verify `CORS_ORIGINS` in backend `.env` includes frontend URL
- Ensure backend is running on expected port

### Geocoding failures
- Use specific format: "City, State" or "Address, City, State ZIP"
- Check OSM has coverage for the area (rural areas may have sparse data)

---

## Documentation

Project documentation is maintained in the following files. Update these after major milestones and significant additions.

| Document | Description |
|----------|-------------|
| [project_spec.md](./project_spec.md) | Full requirements, API specs, tech decisions, and setup checklist |
| [architecture.md](./architecture.md) | System design, component interactions, and data flow diagrams |
| [changelog.md](./changelog.md) | Version history and release notes |
| [project_status.md](./project_status.md) | Current progress, completed tasks, and next steps |
| [DEPLOYMENT.md](./DEPLOYMENT.md) | Step-by-step deployment guide for Railway and Vercel |
