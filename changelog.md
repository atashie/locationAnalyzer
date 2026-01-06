# Distance Finder - Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

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

### Changed
- SearchForm now disables inputs during loading
- Map component handles center/bounds updates programmatically
- CORS default now includes port 5174 for Vite fallback
- LocationAnalyzer now uses expanded query areas for POI searches
- Replaced deprecated `unary_union` with `union_all()` in GeoPandas calls

### Fixed
- Map not updating on subsequent queries (react-leaflet immutability issue)
- Results panel updating but map staying static
- GeoJSON layer not re-rendering when data changes

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
| Unreleased | - | Criteria builder, smart ordering, UX improvements |

---

## Upcoming Releases

### v0.2.0 (Performance Target)
- [ ] POI query caching layer
- [ ] Pre-computed data for RDU metro area
- [ ] Request timeout handling
- [ ] Partial results on slow queries

### v1.0.0 (V1 Target)
- [ ] Valhalla isochrone integration
- [ ] Yelp API for business details
- [ ] User accounts and saved searches
