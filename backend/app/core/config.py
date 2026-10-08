"""Application settings, loaded from environment variables (and backend/.env in development).

All secrets (Mongo URI, JWT secret, Groq API key) live here and are never sent to the frontend.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "BookLeaf Support Portal API"
    app_env: str = "development"
    cors_origins: str = "http://localhost:5173"

    # MongoDB
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "bookleaf_support"

    # Auth
    jwt_secret: str = Field(..., min_length=8)
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7

    # AI (Groq)
    groq_api_key: str = ""
    groq_classify_model: str = "openai/gpt-oss-20b"
    groq_draft_model: str = "openai/gpt-oss-120b"
    groq_timeout_seconds: float = 20.0

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def ai_enabled(self) -> bool:
        return bool(self.groq_api_key)

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
