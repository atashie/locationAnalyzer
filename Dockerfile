# Distance Finder Backend - Production Dockerfile
# Located at repo root for Railway deployment

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for geospatial libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libgeos-dev \
    libproj-dev \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching
COPY backend/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/app/ ./app/

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Railway assigns PORT dynamically, default to 8000 for local testing
ENV PORT=8000

# Run the application using shell form to expand $PORT variable
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
