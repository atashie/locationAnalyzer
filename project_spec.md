# Distance Finder - Project Specification & Setup Checklist

---

# PART 1: Implementation Plan

## Project Summary

Build a web application that helps non-tech-savvy users find locations based on proximity criteria (distance, walk/bike/drive time) to amenities and specific places. Initial focus: **Real Estate** (area identification) and **Dining/Entertainment** (with Yelp integration).

---

## Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   React App     │────▶│   FastAPI       │────▶│   External APIs │
│   (Frontend)    │     │   (Backend)     │     │                 │
│   - Vite        │     │   - OSMnx       │     │   - OSM         │
│   - Leaflet     │     │   - GeoPandas   │     │   - TripAdvisor │
│   - Tailwind    │     │   - Shapely     │     │   - Valhalla    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │
        ▼                       ▼
   Interactive Map       Geospatial Analysis
   Premium Search        Polygon Filtering
```

---

## MVP Scope

### What's In
- User selects a city/region as search center
- User adds up to 4 criteria (POI type + distance OR specific location + travel mode/time)
- Backend computes intersecting polygons using convex-hull isochrones
- Frontend displays result polygon on interactive map
- Area limited to ~25 sq miles to ensure performance

### What's Out (Deferred to V1)
- Listing specific businesses within results
- Yelp API integration
- User accounts / saved searches
- Pre-computed isochrone tiles
- Valhalla routing

---

## Implementation Phases

### Phase 1: Project Setup
**Files to create:**
- `/backend/` - FastAPI application
- `/frontend/` - React application
- `/backend/requirements.txt` - Python dependencies
- `/frontend/package.json` - Node dependencies

**Tasks:**
1. Initialize FastAPI project structure
2. Initialize React project (Vite + TypeScript)
3. Set up development environment (hot reload, CORS)
4. Configure linting/formatting (Black, ESLint, Prettier)

### Phase 2: Backend Core - Geospatial Engine
**Port from:** `distanceFinder/app.py` (LocationAnalyzer class)

**Files to create:**
- `/backend/app/main.py` - FastAPI app entry
- `/backend/app/routers/analysis.py` - Analysis endpoints
- `/backend/app/services/location_analyzer.py` - Core geospatial logic
- `/backend/app/services/geocoding.py` - Location validation/geocoding
- `/backend/app/models/schemas.py` - Pydantic models for API
- `/backend/app/core/config.py` - Configuration management

**Key Endpoints:**
```
POST /api/v1/analyze
  - Input: center location, radius, list of criteria
  - Output: GeoJSON polygon, area stats, criteria summary

GET /api/v1/validate-location?q={query}
  - Input: location string
  - Output: validated location with lat/lon

GET /api/v1/poi-types
  - Output: list of available POI categories
```

**Improvements over PoC:**
- Proper error handling (no bare `except:`)
- Async endpoints where beneficial
- Request validation with Pydantic
- Configurable area limits
- Structured logging

### Phase 3: Frontend - React Application
**Files to create:**
- `/frontend/src/App.tsx` - Main app component
- `/frontend/src/components/Map/` - Leaflet map wrapper
- `/frontend/src/components/SearchForm/` - Criteria input form
- `/frontend/src/components/ResultsSummary/` - Analysis results display
- `/frontend/src/hooks/useAnalysis.ts` - API integration hook
- `/frontend/src/types/` - TypeScript interfaces
- `/frontend/src/api/client.ts` - API client

**UI Components:**
1. **Location Input** - Autocomplete with validation feedback
2. **Criteria Builder** - Add/remove criteria cards
3. **Map View** - Leaflet with layer controls
4. **Results Panel** - Area stats, applied criteria list

### Phase 4: Integration & Polish
**Tasks:**
1. Connect frontend to backend API
2. Add loading states and error handling
3. Implement map interactions (zoom to results, layer toggle)
4. Add export functionality (GeoJSON download)
5. Mobile-responsive layout
6. Basic analytics/logging

### Phase 5: Deployment
**Target:** Free/low-cost hosting

**Options:**
- **Backend:** Railway, Render, or Fly.io (free tier)
- **Frontend:** Vercel or Netlify (free tier)
- **Alternative:** Single deployment on Railway with FastAPI serving React build

---

## Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Frontend framework | React + TypeScript | Type safety, ecosystem, your stated preference |
| Build tool | Vite | Fast dev server, simple config |
| Mapping library | Leaflet + react-leaflet | Free, OSM-native, sufficient for MVP |
| State management | React Query | Handles API caching, loading states |
| Styling | Tailwind CSS | Rapid development, responsive utilities |
| Backend framework | FastAPI | Async support, auto docs, Pydantic integration |
| Geospatial | OSMnx + GeoPandas + Shapely | Proven in PoC, free OSM data |

---

## File Structure

```
distanceFinder/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── constants.py
│   │   ├── models/
│   │   │   └── schemas.py
│   │   ├── routers/
│   │   │   └── analysis.py
│   │   └── services/
│   │       ├── location_analyzer.py
│   │       └── geocoding.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── api/
│   │   ├── components/
│   │   ├── hooks/
│   │   └── types/
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
├── brainstorm.md
└── README.md
```

---

## V1 Roadmap (Post-MVP) - COMPLETED

1. ~~**Yelp Integration**~~ **TripAdvisor Integration** - Premium Search with ratings, reviews, photos
2. **Valhalla Isochrones** - Accurate road-network isochrones via public Valhalla server
3. **POI Explorer** - Browse OSM businesses within analysis polygon
4. **Enhanced UI** - Business cards with TripAdvisor data, cuisine tags, price levels
5. **Polygon Filtering** - Premium results filtered to only show locations inside analysis area

## Current Features (as of v1.4)

### Core Analysis
- Multi-criteria search with up to 8 criteria
- POI-based and location-based filtering
- Travel time isochrones (walk/bike/drive) via Valhalla
- Distance-based buffers as fallback
- Smart query ordering for performance

### Premium Search (TripAdvisor)
- Search restaurants, hotels, attractions within analysis polygon
- Centroid-based search algorithm (up to 5 polygon areas)
- Polygon containment filtering - only shows locations inside your area
- Rich data: ratings, reviews, price levels, photos, cuisine tags
- API usage tracking (5000 calls/month limit)

### POI Explorer
- Query OSM POIs within result polygon
- View business details from OpenStreetMap data

### Limitations
- **Centroid limit**: Premium Search queries up to 5 polygon centroids
- **API budget**: TripAdvisor free tier = 5000 calls/month
- **Search radius**: Maximum 25 miles

## V2 Roadmap (Future)

1. **Pre-computed Tiles** - Cache isochrones for RDU metro area
2. **Saved Searches** - User accounts with search history
3. **AI Integration** - Natural language query interface
4. **Additional Providers** - Google Places, Yelp as Premium Search options

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| OSMnx queries slow/timeout | Enforce area limits, add request timeouts, cache geocoding |
| OSM POI data incomplete | Show disclaimer, allow fallback to "any" POI in category |
| Convex hull overestimates area | Acceptable for MVP; V1 Valhalla will fix |
| Yelp rate limits (500/day) | Implement caching, defer to V1 |

---

## Next Steps

1. Complete setup checklist (Part 2 below)
2. Create backend project structure and FastAPI skeleton
3. Port LocationAnalyzer to `/backend/app/services/`
4. Build API endpoints with proper error handling
5. Create React frontend with map and form components
6. Integrate and test end-to-end
7. Deploy to free-tier hosting

---

# PART 2: Setup Checklist

## 1. GitHub Repository

### Tasks
- [ ] Initialize git repository (if not already done)
- [ ] Create `.gitignore` for Python + Node + IDE files
- [ ] Set up branch protection rules (optional for solo dev)
- [ ] Create initial commit with project structure

### `.gitignore` contents
```gitignore
# Python
__pycache__/
*.py[cod]
.venv/
venv/
.env
*.egg-info/

# Node
node_modules/
dist/
.next/

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db

# Project specific
*.geojson
*.log
```

---

## 2. Environment Variables (.env)

### Backend `.env` (create at `/backend/.env`)
```env
# App Settings
DEBUG=true
ENVIRONMENT=development
LOG_LEVEL=INFO

# API Keys (add when needed)
YELP_API_KEY=           # For V1 - get from https://www.yelp.com/developers
# GOOGLE_PLACES_KEY=    # Optional future integration

# OSMnx Settings
OSMNX_CACHE_FOLDER=./cache/osmnx
OSMNX_TIMEOUT=300

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Rate Limits
MAX_SEARCH_RADIUS_MILES=25
MAX_CRITERIA_COUNT=8
```

### Frontend `.env` (create at `/frontend/.env`)
```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_MAP_TILE_URL=https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png
```

---

## 3. Claude Code Configuration (CLAUDE.md)

Create `CLAUDE.md` in project root with project context:

```markdown
# Distance Finder - Claude Code Context

## Project Overview
Location finder web app helping users find areas based on proximity criteria.
- **Frontend:** React + TypeScript + Vite + Leaflet
- **Backend:** FastAPI + Python + GeoPandas + OSMnx

## Key Files
- `/backend/app/services/location_analyzer.py` - Core geospatial logic
- `/backend/app/routers/analysis.py` - API endpoints
- `/frontend/src/components/Map/` - Map display components
- `/frontend/src/components/SearchForm/` - Criteria input UI

## Commands
- Backend: `cd backend && uvicorn app.main:app --reload`
- Frontend: `cd frontend && npm run dev`
- Tests: `cd backend && pytest`

## Architecture Notes
- Progressive filtering: each criterion narrows search area
- Convex-hull isochrones for MVP (Valhalla in V1)
- OSM data via OSMnx, Yelp API for V1 business details

## Code Style
- Python: Black formatter, type hints required
- TypeScript: Strict mode, Prettier formatter
- Prefer explicit error handling over silent failures

## Common Tasks
- Adding new POI type: Update `POI_TYPES` in `/backend/app/core/constants.py`
- Adding new endpoint: Create in `/backend/app/routers/`, register in `main.py`
- Adding new component: Create in `/frontend/src/components/`
```

---

## 4. Automated Documentation

### Backend (FastAPI auto-docs)
FastAPI provides automatic documentation at:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

Enhance with docstrings in endpoints:
```python
@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_location(request: AnalysisRequest):
    """
    Analyze a location with multiple proximity criteria.

    - **center**: City or address to center search on
    - **radius_miles**: Maximum search radius (1-25 miles)
    - **criteria**: List of proximity criteria to apply

    Returns a GeoJSON polygon of the matching area.
    """
```

### Frontend (TypeDoc - optional)
```bash
npm install -D typedoc
npx typedoc --entryPoints src --out docs
```

### README auto-generation (optional)
Consider `readme-md-generator` for keeping README in sync.

---

## 5. VS Code Extensions / Plugins

### Recommended Extensions (create `.vscode/extensions.json`)
```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.black-formatter",
    "charliermarsh.ruff",
    "bradlc.vscode-tailwindcss",
    "esbenp.prettier-vscode",
    "dbaeumer.vscode-eslint",
    "ms-azuretools.vscode-docker"
  ]
}
```

### Workspace Settings (create `.vscode/settings.json`)
```json
{
  "python.defaultInterpreterPath": "./backend/.venv/bin/python",
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.formatOnSave": true
  },
  "[typescript][typescriptreact]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.formatOnSave": true
  },
  "editor.codeActionsOnSave": {
    "source.organizeImports": "explicit"
  }
}
```

---

## 6. MCP Servers

**Status: Not needed for MVP**

Potential future uses:
- **Database MCP** - If adding PostgreSQL/PostGIS for persistent storage
- **Yelp MCP** - Custom MCP for Yelp API integration (V1)
- **Geospatial MCP** - For complex spatial queries

For now, direct API calls in FastAPI are sufficient.

---

## 7. Slash Commands & Sub-Agents

### Custom Slash Commands (create `.claude/commands/`)

#### `/analyze-geo` - Test geospatial queries
```markdown
# .claude/commands/analyze-geo.md
Run a test analysis query with the backend:
1. Ensure backend is running (`uvicorn app.main:app --reload`)
2. Execute: `curl -X POST http://localhost:8000/api/v1/analyze -H "Content-Type: application/json" -d '{"center": "Durham, NC", "radius_miles": 10, "criteria": []}'`
3. Report the response time and result summary
```

#### `/check-osm` - Verify OSM data availability
```markdown
# .claude/commands/check-osm.md
Check OSM data coverage for a location:
1. Query OSMnx for POI counts in the target area
2. Report which POI types have good coverage vs sparse data
3. Flag any potential data quality issues
```

#### `/deploy-check` - Pre-deployment verification
```markdown
# .claude/commands/deploy-check.md
Verify the app is ready for deployment:
1. Run backend tests: `cd backend && pytest`
2. Run frontend build: `cd frontend && npm run build`
3. Check for environment variable issues
4. Verify no secrets in committed code
5. Report any blockers
```

### Sub-Agent Configuration

For this project, the built-in agents are sufficient:
- **Explore** - For codebase navigation
- **Plan** - For architecture decisions

Custom sub-agents to consider later:
- **Geospatial Expert** - Specialized prompts for OSMnx/GeoPandas issues
- **API Designer** - For endpoint design decisions

---

## Setup Execution Order

1. **Initialize Git repo** - `git init` (if needed)
2. **Create `.gitignore`**
3. **Create project structure** (backend/, frontend/ folders)
4. **Create CLAUDE.md** in project root
5. **Set up backend**:
   - `cd backend && python -m venv .venv`
   - Create `requirements.txt`
   - Create `.env`
6. **Set up frontend**:
   - `npm create vite@latest frontend -- --template react-ts`
   - Create `.env`
7. **Create VS Code config** (`.vscode/` folder)
8. **Create slash commands** (`.claude/commands/` folder)
9. **Initial commit**

---

## Post-Setup Verification

- [ ] `git status` shows clean working tree
- [ ] Backend starts: `cd backend && uvicorn app.main:app --reload`
- [ ] Frontend starts: `cd frontend && npm run dev`
- [ ] FastAPI docs accessible at `http://localhost:8000/docs`
- [ ] Frontend connects to backend (check browser console)
- [ ] CLAUDE.md is readable and accurate
