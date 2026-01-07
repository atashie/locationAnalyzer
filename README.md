# Location Analyzer (Distance Finder)

A web application that helps users find locations based on proximity criteria to amenities and points of interest. Built with React, FastAPI, and geospatial analysis tools.

## Features

### Core Analysis
- **Multi-criteria search**: Combine up to 8 proximity criteria (distance, walk/bike/drive time)
- **POI-based filtering**: Find areas near restaurants, parks, schools, hospitals, etc.
- **Location-based filtering**: Specify exact addresses or landmarks
- **Travel time isochrones**: Accurate road-network routing via Valhalla
- **Interactive map**: View results as polygons on a Leaflet map

### Premium Search (TripAdvisor Integration)
- **Rich business data**: Ratings, reviews, price levels, photos
- **Category filtering**: Restaurants, hotels, attractions
- **Polygon-aware**: Only shows locations within your analysis area
- **Centroid search algorithm**: Searches up to 5 polygon areas for comprehensive coverage

> **Note**: Premium Search is limited to 5 polygon centroids. Complex multi-polygon results may not cover all regions.

### POI Explorer
- **OSM data**: Browse OpenStreetMap points of interest within your results
- **Business details**: Names, addresses, hours, contact info

## Architecture

```
Frontend (React + Vite)     Backend (FastAPI)          External APIs
       |                          |                         |
       +--- /analyze -----------> +--- OSMnx/GeoPandas ---> OSM
       |                          |
       +--- /premium-search ----> +--- TripAdvisor -------> TripAdvisor API
       |                          |
       +--- /pois --------------> +--- Valhalla ----------> Valhalla (isochrones)
```

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- TripAdvisor API key (for Premium Search)

### Backend Setup
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env to add your TRIPADVISOR_API_KEY

# Run
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install

# Create .env file
echo "VITE_API_BASE_URL=http://localhost:8000/api/v1" > .env

# Run
npm run dev
```

### Production Deployment
- **Backend**: Railway (auto-deploys from GitHub)
- **Frontend**: Vercel (auto-deploys from GitHub)

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/analyze` | POST | Run multi-criteria location analysis |
| `/api/v1/premium-search` | POST | Search TripAdvisor within polygon |
| `/api/v1/pois` | POST | Query OSM POIs within polygon |
| `/api/v1/poi-types` | GET | List available POI categories |
| `/api/v1/validate-location` | GET | Geocode/validate a location string |
| `/api/v1/health` | GET | Health check |

## Environment Variables

### Backend
| Variable | Description | Required |
|----------|-------------|----------|
| `TRIPADVISOR_API_KEY` | TripAdvisor Content API key | For Premium Search |
| `TRIPADVISOR_REFERER_DOMAIN` | Domain for API key restriction | Default: production URL |
| `VALHALLA_URL` | Valhalla routing server | Default: public OSM server |
| `CORS_ORIGINS` | Allowed frontend origins | Required |

### Frontend
| Variable | Description |
|----------|-------------|
| `VITE_API_BASE_URL` | Backend API URL |
| `VITE_MAP_TILE_URL` | Map tile server URL |

## Technology Stack

- **Frontend**: React, TypeScript, Vite, Tailwind CSS, Leaflet
- **Backend**: FastAPI, Python, GeoPandas, Shapely, OSMnx
- **APIs**: OpenStreetMap, TripAdvisor Content API, Valhalla
- **Deployment**: Railway (backend), Vercel (frontend)

## Limitations

- **Premium Search centroid limit**: Searches up to 5 polygon areas. Complex multi-polygon results may miss some regions.
- **TripAdvisor API**: 5000 calls/month on free tier
- **Search radius**: Maximum 25 miles to ensure performance
- **Isochrone accuracy**: Uses Valhalla for travel time; falls back to simple buffer if unavailable

## License

MIT
