"""DuckDB connection helpers and schema initialization for the API.

DuckDB connections are not threadsafe — a fresh connection is opened per request
or per write. A module-level lock serializes writes (DuckDB is single-writer).
"""
from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from typing import Iterator, Optional

import duckdb

from .config import get_settings

_WRITE_LOCK = threading.Lock()
_SCHEMA_INIT_DONE: set[str] = set()
_SCHEMA_LOCK = threading.Lock()


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id         TEXT PRIMARY KEY,
    email      TEXT NOT NULL,
    name       TEXT,
    picture    TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    token      TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS watchlists (
    user_id  TEXT NOT NULL,
    symbol   TEXT NOT NULL,
    note     TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, symbol)
);

CREATE TABLE IF NOT EXISTS ohlcv_cache (
    ticker     TEXT NOT NULL,
    period     TEXT NOT NULL,
    fetched_at BIGINT NOT NULL,
    payload    BLOB NOT NULL,
    PRIMARY KEY (ticker, period)
);

CREATE TABLE IF NOT EXISTS news_cache (
    cache_key  TEXT PRIMARY KEY,
    payload    TEXT NOT NULL,
    fetched_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS symbol_validation_cache (
    symbol     TEXT PRIMARY KEY,
    valid      BOOLEAN NOT NULL,
    fetched_at TIMESTAMP NOT NULL
);
"""


def _resolve_db_path(db_path: Optional[str] = None) -> str:
    if db_path:
        return db_path
    return get_settings().BEST7DAYS_DB_PATH


def init_schema(db_path: Optional[str] = None) -> None:
    """Create tables (idempotent). Safe to call once per process per DB."""
    path = _resolve_db_path(db_path)
    with _SCHEMA_LOCK:
        if path in _SCHEMA_INIT_DONE:
            return
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with _WRITE_LOCK:
            conn = duckdb.connect(path)
            try:
                # DuckDB requires statements to be executed individually for some versions.
                for stmt in SCHEMA_SQL.strip().split(";"):
                    s = stmt.strip()
                    if s:
                        conn.execute(s)
            finally:
                conn.close()
        _SCHEMA_INIT_DONE.add(path)


@contextmanager
def get_conn(db_path: Optional[str] = None) -> Iterator[duckdb.DuckDBPyConnection]:
    """Yield a fresh DuckDB connection. Caller is responsible for transactions."""
    path = _resolve_db_path(db_path)
    init_schema(path)
    conn = duckdb.connect(path)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def get_write_conn(db_path: Optional[str] = None) -> Iterator[duckdb.DuckDBPyConnection]:
    """Yield a fresh DuckDB connection guarded by the global write lock."""
    path = _resolve_db_path(db_path)
    init_schema(path)
    with _WRITE_LOCK:
        conn = duckdb.connect(path)
        try:
            yield conn
        finally:
            conn.close()


def reset_schema_cache() -> None:
    """Test helper: forget which DB paths have been initialized."""
    with _SCHEMA_LOCK:
        _SCHEMA_INIT_DONE.clear()
