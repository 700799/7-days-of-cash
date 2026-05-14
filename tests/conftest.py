"""Shared pytest fixtures for the Best7DaysMula test suite."""
from __future__ import annotations

import os
from typing import Iterator

import pytest


@pytest.fixture
def tmp_db_path(tmp_path, monkeypatch) -> Iterator[str]:
    """Point the API & cache at a fresh DuckDB file for the duration of one test.

    Resets module-level singletons that capture settings or schema-init state.
    """
    db_file = tmp_path / "test.duckdb"
    monkeypatch.setenv("BEST7DAYS_DB_PATH", str(db_file))

    # Bust caches that may have already captured the old env value.
    from api import config as api_config
    from api import db as api_db
    from api import auth as api_auth

    api_config.get_settings.cache_clear()  # type: ignore[attr-defined]
    api_db.reset_schema_cache()
    api_auth.reset_oauth_cache()

    yield str(db_file)

    api_config.get_settings.cache_clear()  # type: ignore[attr-defined]
    api_db.reset_schema_cache()
    api_auth.reset_oauth_cache()
