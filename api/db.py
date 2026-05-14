"""Postgres connection pool + schema initialization for the API.

Uses ``psycopg2.pool.SimpleConnectionPool`` so each request borrows a connection
and returns it — works under Vercel's stateless lambdas because the pool lives
inside the warm process; cold starts re-create it. Postgres' MVCC handles
multi-writer concurrency, so the previous DuckDB-era write lock is gone.
"""
from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from typing import Iterator, Optional

import psycopg2
import psycopg2.extras
import psycopg2.pool


# Per-process pool. Created lazily on first request; survives across requests in
# a warm Vercel lambda. We keep the pool small (1..5) — Neon/Supabase free tiers
# cap concurrent connections aggressively and pooled lambdas don't need many.
_POOL: Optional[psycopg2.pool.SimpleConnectionPool] = None
_POOL_LOCK = threading.Lock()
_SCHEMA_INIT_DONE = False
_SCHEMA_LOCK = threading.Lock()


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id         TEXT PRIMARY KEY,
    email      TEXT NOT NULL,
    name       TEXT,
    picture    TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sessions (
    token      TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS watchlists (
    user_id  TEXT NOT NULL,
    symbol   TEXT NOT NULL,
    note     TEXT,
    added_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (user_id, symbol)
);

CREATE TABLE IF NOT EXISTS ohlcv_cache (
    ticker     TEXT NOT NULL,
    period     TEXT NOT NULL,
    data       BYTEA NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (ticker, period)
);

CREATE TABLE IF NOT EXISTS news_cache (
    cache_key  TEXT PRIMARY KEY,
    payload    TEXT NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS movers_cache (
    cache_key  TEXT PRIMARY KEY,
    payload    TEXT NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS user_preferences (
    user_id          TEXT PRIMARY KEY,
    digest_frequency TEXT NOT NULL DEFAULT 'none',
    digest_email     TEXT,
    last_sent_at     TIMESTAMPTZ,
    updated_at       TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS screener_results (
    id      BIGSERIAL PRIMARY KEY,
    ran_at  TIMESTAMPTZ DEFAULT now(),
    payload JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS symbol_validation_cache (
    symbol     TEXT PRIMARY KEY,
    valid      BOOLEAN NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def _resolve_db_url(db_url: Optional[str] = None) -> str:
    if db_url:
        return db_url
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL not set. Configure your Neon/Postgres connection string."
        )
    return url


def _get_pool(db_url: Optional[str] = None) -> psycopg2.pool.SimpleConnectionPool:
    """Lazy singleton: create the pool on first use, reuse forever after."""
    global _POOL
    if _POOL is not None:
        return _POOL
    with _POOL_LOCK:
        if _POOL is None:
            url = _resolve_db_url(db_url)
            _POOL = psycopg2.pool.SimpleConnectionPool(1, 5, url)
    return _POOL


def reset_pool() -> None:
    """Test helper: tear down the current pool so the next call rebuilds it."""
    global _POOL
    with _POOL_LOCK:
        if _POOL is not None:
            try:
                _POOL.closeall()
            except Exception:
                pass
            _POOL = None


def reset_schema_cache() -> None:
    """Test helper: forget the schema-init memoization."""
    global _SCHEMA_INIT_DONE
    with _SCHEMA_LOCK:
        _SCHEMA_INIT_DONE = False


def init_schema(db_url: Optional[str] = None) -> None:
    """Create all tables (idempotent). Call from scripts/migrate.py post-deploy.

    Not invoked on cold-start to keep lambdas snappy. Tests call this explicitly
    via the ``pg_conn`` fixture.
    """
    global _SCHEMA_INIT_DONE
    with _SCHEMA_LOCK:
        if _SCHEMA_INIT_DONE:
            return
        pool = _get_pool(db_url)
        conn = pool.getconn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(SCHEMA_SQL)
        finally:
            pool.putconn(conn)
        _SCHEMA_INIT_DONE = True


@contextmanager
def get_conn(db_url: Optional[str] = None) -> Iterator[psycopg2.extensions.connection]:
    """Borrow a connection from the pool. Commits on success, rolls back on error.

    Caller uses the connection's cursor() for queries. Postgres handles
    concurrent reads + writes natively so there's no write-lock anymore.
    """
    pool = _get_pool(db_url)
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        pool.putconn(conn)


# Backwards-compat alias — the previous DuckDB layer exposed a separate
# ``get_write_conn`` because DuckDB serialized writes. Postgres doesn't need it,
# but old call sites still import the name. Both return the same context manager.
get_write_conn = get_conn
