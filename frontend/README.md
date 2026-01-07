# Location Analyzer - Frontend

React + TypeScript frontend for the Location Analyzer application.

## Tech Stack

- **React 18** with TypeScript
- **Vite** for fast development and builds
- **Tailwind CSS** for styling
- **Leaflet** + react-leaflet for maps
- **Axios** for API calls
- **React Query** for data fetching

## Getting Started

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## Environment Variables

Create a `.env` file:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_MAP_TILE_URL=https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png
```

For production (Vercel), set `VITE_API_BASE_URL` to your Railway backend URL.

## Project Structure

```
src/
├── api/
│   └── client.ts          # API client with all endpoints
├── components/
│   ├── Map/               # Leaflet map with markers and popups
│   ├── SearchForm/        # Criteria input form
│   ├── ResultsSummary/    # Analysis results display
│   └── PremiumSearchPanel/ # TripAdvisor Premium Search
├── hooks/
│   └── useAnalysis.ts     # React Query hook for analysis
├── types/
│   └── index.ts           # TypeScript interfaces
├── App.tsx                # Main app component
└── main.tsx               # Entry point
```

## Key Components

### Map
- Displays analysis polygon (blue)
- Shows OSM POI markers (red circles)
- Shows Premium Search results (purple/gold circles)
- Interactive popups with business details

### SearchForm
- Location input with validation
- Radius selector (1-25 miles)
- Multi-criteria builder (POI type or specific location)
- Travel mode selection (distance/walk/bike/drive)

### PremiumSearchPanel
- Toggle to enable Premium features
- TripAdvisor category/subcategory selection
- Max locations input
- Results summary with API usage stats

> **Note**: Premium Search is limited to 5 polygon areas. Complex multi-polygon results may not cover all regions.

## Deployment

The frontend is deployed to Vercel with automatic deploys from the `master` branch.

Production URL: Set in Vercel environment variables.
