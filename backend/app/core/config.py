"""Application configuration using Pydantic settings."""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App settings
    debug: bool = True
    environment: str = "development"
    log_level: str = "INFO"

    # API Keys
    yelp_api_key: str = ""

    # OSMnx settings
    osmnx_cache_folder: str = "./cache/osmnx"
    osmnx_timeout: int = 300

    # Server settings
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:3000"

    # Rate limits
    max_search_radius_miles: float = 25.0
    max_criteria_count: int = 8

    # Valhalla settings (API at valhalla1, not valhalla)
    valhalla_url: str = "https://valhalla1.openstreetmap.de"
    valhalla_timeout: int = 30
    valhalla_enabled: bool = True

    # TripAdvisor API settings
    tripadvisor_api_key: str = ""
    tripadvisor_enabled: bool = True
    tripadvisor_monthly_limit: int = 5000
    tripadvisor_cache_dir: str = "./cache/tripadvisor"
    tripadvisor_timeout: int = 10

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins string into list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra env vars (e.g., VITE_ frontend vars)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
