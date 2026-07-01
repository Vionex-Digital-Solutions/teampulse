"""Application configuration using pydantic-settings."""

import json
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "Vionex TeamPulse"
    environment: str = "development"
    debug: bool = False

    database_url: str = "sqlite+aiosqlite:///./teampulse.db"

    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60 * 24
    algorithm: str = "HS256"

    allowed_origins: str = '["http://localhost:3000"]'

    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse ALLOWED_ORIGINS JSON string into a list."""
        return json.loads(self.allowed_origins)

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()


settings = get_settings()
