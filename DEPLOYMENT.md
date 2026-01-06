# Distance Finder - Deployment Guide

## Overview

- **Backend**: Railway (FastAPI + Docker)
- **Frontend**: Vercel (React + Vite)

---

## Step 1: Deploy Backend to Railway

### 1.1 Create Railway Account
1. Go to https://railway.app
2. Sign up with GitHub (recommended for easy repo connection)

### 1.2 Create New Project
1. Click "New Project" → "Deploy from GitHub repo"
2. Select `atashie/locationAnalyzer` repository
3. Railway will detect the Dockerfile in `/backend`

### 1.3 Configure Root Directory
1. Go to project Settings
2. Set **Root Directory** to `backend`
3. Railway will use the Dockerfile in that directory

### 1.4 Set Environment Variables
In Railway project → Variables tab, add:

```
DEBUG=false
ENVIRONMENT=production
LOG_LEVEL=INFO
CORS_ORIGINS=https://your-vercel-url.vercel.app
MAX_SEARCH_RADIUS_MILES=25
MAX_CRITERIA_COUNT=8
OSMNX_TIMEOUT=300
```

**Note**: Update `CORS_ORIGINS` after deploying frontend to Vercel.

### 1.5 Get Backend URL
After deployment, Railway provides a URL like:
`https://your-project.up.railway.app`

Test it: `https://your-project.up.railway.app/api/v1/health`

---

## Step 2: Deploy Frontend to Vercel

### 2.1 Create Vercel Account
1. Go to https://vercel.com
2. Sign up with GitHub (recommended)

### 2.2 Import Project
1. Click "Add New" → "Project"
2. Import `atashie/locationAnalyzer` repository
3. Configure:
   - **Root Directory**: `frontend`
   - **Framework Preset**: Vite (auto-detected)

### 2.3 Set Environment Variables
In Vercel project → Settings → Environment Variables:

```
VITE_API_BASE_URL=https://your-railway-url.up.railway.app/api/v1
```

### 2.4 Deploy
Click "Deploy" and wait for build to complete.

---

## Step 3: Update Backend CORS

After getting your Vercel URL:

1. Go to Railway project → Variables
2. Update `CORS_ORIGINS` to include your Vercel URL:
   ```
   CORS_ORIGINS=https://distance-finder-xyz.vercel.app
   ```
3. Railway will auto-redeploy with new settings

---

## Verification

1. Visit your Vercel frontend URL
2. Enter a location (e.g., "Durham, NC")
3. Add a criterion (e.g., "Within 2 miles of Duke University")
4. Click "Find Areas"
5. Verify map displays the result polygon

---

## Troubleshooting

### CORS Errors
- Ensure `CORS_ORIGINS` in Railway exactly matches your Vercel URL
- Include `https://` prefix
- No trailing slash

### Build Failures
- Check Railway logs for backend errors
- Check Vercel deployment logs for frontend errors

### Slow Queries
- First-time POI queries can take 1-5+ minutes
- Subsequent queries for same area are cached by OSM
- Use "Specific Place" criteria for faster results

---

## Production URLs

- **Backend API**: https://locationanalyzer-production.up.railway.app
- **Frontend App**: https://location-analyzer-three.vercel.app
- **API Documentation**: https://locationanalyzer-production.up.railway.app/docs
