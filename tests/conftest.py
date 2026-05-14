"""Shared pytest fixtures for the Best7DaysMula test suite."""
from __future__ import annotations

import os
from typing import Iterator

import pytest

# Auto-skip Postgres-requiring tests when no DATABASE_URL is configured.
# CI / local runs without Neon get a clean pass on the CLI/screener test bed
# (31 tests). Postgres-backed tests run only when a real DB is wired up.
requires_postgres = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="Postgres-backed test — set DATABASE_URL to enable",
)


@pytest.fixture
def tmp_db_path(tmp_path, monkeypatch) -> Iterator[str]:
    """Legacy fixture from the DuckDB era. Most callers now skip via
    ``requires_postgres`` since the API moved to Postgres. Kept so old test
    files still import cleanly until they're rewritten for psycopg2.
    """
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set — Postgres-backed test")
    db_file = tmp_path / "test.duckdb"
    monkeypatch.setenv("BEST7DAYS_DB_PATH", str(db_file))
    yield str(db_file)
