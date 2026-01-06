# Start Development Environment

Start both backend and frontend development servers.

## Steps

### 1. Start Backend Server

```bash
cd backend
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
```

The backend will be available at:
- API: http://localhost:8000/api/v1
- Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 2. Start Frontend Server

In a new terminal:

```bash
cd frontend
npm run dev
```

The frontend will be available at:
- App: http://localhost:5173

## Quick Health Check

After both servers are running:

```bash
# Check backend health
curl http://localhost:8000/api/v1/health

# Check frontend is serving
curl -s http://localhost:5173 | head -5
```

## Common Issues

### Backend won't start
- Check if port 8000 is in use: `netstat -ano | findstr :8000`
- Verify .env file exists in backend/
- Check Python path: `.venv/Scripts/python.exe --version`

### Frontend won't start
- Check if port 5173 is in use
- Run `npm install` if node_modules missing
- Check for TypeScript errors: `npm run build`

### CORS errors in browser
- Verify backend CORS_ORIGINS includes http://localhost:5173
- Check browser console for specific error message
