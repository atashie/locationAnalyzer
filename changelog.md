# Distance Finder - Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

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
- Project documentation:
  - `CLAUDE.md` - Claude Code context
  - `project_spec.md` - Full requirements and setup checklist
  - `architecture.md` - System design documentation
  - `changelog.md` - Version history (this file)
  - `project_status.md` - Current progress tracking
- Configuration:
  - `.env.example` - Environment variable template
  - `.gitignore` - Git ignore rules

### Changed
- N/A (initial release)

### Deprecated
- N/A

### Removed
- N/A

### Fixed
- N/A

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
| Unreleased | - | Backend structure, API endpoints |

---

## Upcoming Releases

### v0.1.0 (MVP Target)
- [ ] Working backend with all API endpoints
- [ ] React frontend with map and search form
- [ ] End-to-end analysis flow
- [ ] Deployment to free-tier hosting

### v1.0.0 (V1 Target)
- [ ] Valhalla isochrone integration
- [ ] Yelp API for business details
- [ ] Pre-computed tiles for RDU area
- [ ] User accounts and saved searches
