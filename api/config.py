"""Application configuration sourced from environment / .env."""
from __future__ import annotations

import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Backend settings. Values come from env vars or a `.env` file."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    SESSION_SECRET: str = "dev-insecure-change-me"
    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000"
    BEST7DAYS_DB_PATH: str = os.path.join("data", "best7days.duckdb")

    SESSION_COOKIE_NAME: str = "b7dm_session"
    SESSION_TTL_DAYS: int = 30
    NEWS_TTL_SEC: int = 15 * 60
    SYMBOL_VALIDATION_TTL_SEC: int = 24 * 60 * 60


@lru_cache
def get_settings() -> Settings:
    return Settings()
