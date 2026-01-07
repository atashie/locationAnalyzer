# Distance Finder - Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [1.2.0] - 2026-01-06 - Performance & Valhalla

### Added
- **Valhalla Isochrone Integration** - Accurate road-network travel time polygons
  - Uses free public Valhalla API at `valhalla1.openstreetmap.de`
  - Real isochrones for specific location criteria (not approximations)
  - Automatic fallback to buffer approximation if Valhalla unavailable
  - Configurable via `VALHALLA_ENABLED` and `VALHALLA_URL` env vars
- **Stable Polygon Caching** - 4-80x faster multi-criteria searches
  - Always queries the original search boundary (stable, cacheable)
  - Filters results to current area using fast Python operations
  - In-memory cache per POI type within each analysis session
  - Eliminates redundant OSM API calls for same POI type across criteria

### Performance
- **Multi-criteria benchmark**: 6 criteria in 3.86s (was ~18s without caching)
- **Cache hit speedup**: 80x faster for repeated POI type queries
- **API load reduction**: Single OSM query per POI type per search area

### Changed
- `_get_pois()` now uses stable polygon caching strategy
- `query_pois_in_polygon()` shares the same POI cache
- Travel time criteria for specific locations use Valhalla by default

---

## [1.1.0] - 2026-01-06 - POI Explorer

### Added
- **POI Explorer** - Browse businesses within your search result polygon
  - New `POST /api/v1/pois` endpoint for querying POIs in a polygon
  - Category dropdown in Results panel to select business type
  - POI list with names and addresses
  - Clickable map markers (red circles) with popup details
  - Shows name, address, hours, phone, and website link
- **Backend POI Query Method** - `query_pois_in_polygon()` in LocationAnalyzer
  - Extracts business metadata (name, address, hours, phone, website)
  - Handles both Point and Polygon geometries
  - Returns structured data + GeoJSON
- **Frontend POI Types** - New TypeScript interfaces for POI data

### Changed
- ResultsSummary component now accepts POI-related props
- Map component renders POI markers with CircleMarker
- App.tsx manages POI state and fetches POI types on mount

---

## [1.0.0] - 2026-01-06 - MVP Release

### Deployment
- **Production deployment complete**
  - Backend deployed to Railway: https://locationanalyzer-production.up.railway.app
  - Frontend deployed to Vercel: https://location-analyzer-three.vercel.app
  - API documentation at: https://locationanalyzer-production.up.railway.app/docs
- **Dockerfile** for containerized backend deployment
- **railway.toml** for Railway-specific configuration
- **DEPLOYMENT.md** guide for step-by-step deployment instructions

### Added
- **Criteria Builder UI** - Full-featured criteria management in SearchForm
  - CriterionCard component with type toggle (Amenity Type / Specific Place)
  - POI type dropdown populated from backend API
  - Travel mode selector (distance, walk, bike, drive)
  - Dynamic value input with mode-appropriate units
  - Summary line showing criterion description
  - Add/remove up to 8 criteria
- **Smart Query Ordering** - Backend automatically reorders criteria for optimal performance
  - Single location criteria applied first (most restrictive)
  - Then by mode: distance > walk > bike > drive
  - Then by value: smaller values first
  - Reduces polygon size early, making subsequent OSM queries faster
- **Loading Indicator with Time Estimation**
  - Estimated query time displayed before running
  - Live elapsed time counter during analysis
  - Progress messages that update based on query duration
  - Slow query warnings for high-density POI types
  - Tips for improving query performance
- **Map Update Fix** - Map now properly updates on subsequent queries
  - Added MapUpdater component using useMap() hook
  - Dynamic key prop on GeoJSON to force re-render
  - Map auto-fits to result polygon bounds
- **Performance Testing Suite** - `performance_test.py` for benchmarking
  - Instrumented LocationAnalyzer with detailed timing
  - Random test generation with 0-4 criteria
  - JSON output with bottleneck analysis
- **Query Area Expansion** - Correctness fix for edge POIs
  - POI queries now expand beyond current polygon boundary
  - Captures POIs just outside boundary that are within travel distance of interior points
  - Capped at 5 miles to prevent massive OSM queries
  - Ensures no valid areas are incorrectly filtered out
- **Complex Query Toggle** - UX improvement for Amenity Type searches
  - "Specific Place" is now default criterion type
  - Walk/bike/drive modes only available when "Complex Query" is enabled
  - Helps users avoid slow queries by default
- **Realistic Travel-Time Buffers** - Organic isochrone shapes
  - Uses sine wave variation instead of perfect circles
  - Mode-specific variation: walk (15%), bike (20%), drive (25%)
  - Creates more realistic-looking travel time polygons

### Changed
- SearchForm now disables inputs during loading
- Map component handles center/bounds updates programmatically
- CORS default now includes port 5174 for Vite fallback
- LocationAnalyzer now uses expanded query areas for POI searches
- Replaced deprecated `unary_union` with `union_all()` in GeoPandas calls
- Default criterion type changed to "Specific Place" (faster queries)

### Fixed
- Map not updating on subsequent queries (react-leaflet immutability issue)
- Results panel updating but map staying static
- GeoJSON layer not re-rendering when data changes
- Dockerfile PORT variable for Railway dynamic port assignment

---

## [0.1.0] - 2025-01-06

### Added
- Initial project structure with backend and frontend scaffolding
- FastAPI backend with core geospatial services
  - `LocationAnalyzer` class for progressive filtering
  - `GeocodingService` for location validation
  - Pydantic models for type-safe API
- API endpoints:
  - `POST /api/v1/analyze` - Multi-criteria location analysis
  - `GET /api/v1/validate-location` - Location geocoding
  - `GET /api/v1/poi-types` - Available POI categories
  - `GET /api/v1/health` - Health check
- React frontend with Vite + TypeScript
  - Map component with Leaflet integration
  - SearchForm with center and radius inputs
  - ResultsSummary component
  - React Query hooks for API integration
  - Tailwind CSS styling
- Project documentation:
  - `CLAUDE.md` - Claude Code context
  - `project_spec.md` - Full requirements and setup checklist
  - `architecture.md` - System design documentation
  - `changelog.md` - Version history (this file)
  - `project_status.md` - Current progress tracking
- Configuration:
  - `.env.example` - Environment variable template
  - `.gitignore` - Git ignore rules
  - VS Code settings and extensions
  - Claude slash commands

### Security
- CORS configuration for frontend origins
- Environment variables for sensitive config

---

## [0.0.1] - 2025-01-06

### Added
- Project initialization
- Original Streamlit proof of concept (`distanceFinder/app.py`)
- Brainstorm document with requirements

---

## Version History Summary

| Version | Date | Milestone |
|---------|------|-----------|
| 0.0.1 | 2025-01-06 | Project initialization, PoC |
| 0.1.0 | 2025-01-06 | Backend + Frontend MVP structure |
| 1.0.0 | 2026-01-06 | MVP Release - Production deployment |
| 1.1.0 | 2026-01-06 | POI Explorer - Browse businesses in area |
| **1.2.0** | **2026-01-06** | **Performance & Valhalla - 4-80x faster queries** |

---

## Upcoming Releases

### v1.3.0 (Tripadvisor Integration)
- [ ] Tripadvisor Locations API integration
- [ ] Display ratings and reviews for POIs
- [ ] Toggle between OSM-only and Tripadvisor-enriched data

### v1.4.0 (Advanced Performance)
- [ ] Pre-computed data for RDU metro area
- [ ] Request timeout handling
- [ ] Partial results on slow queries

### v2.0.0 (V2 Target)
- [ ] User accounts and saved searches
- [ ] Saved search sharing
