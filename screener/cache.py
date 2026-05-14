"""Postgres-backed OHLCV cache with TTL-based invalidation.

Stores DataFrames as parquet bytes in a ``BYTEA`` column. Postgres handles
multi-writer concurrency natively, so the previous DuckDB-era write lock is
gone. A small connection pool keeps cold-start latency low on Vercel lambdas.
"""
from __future__ import annotations

import io
import os
import threading
import time
from contextlib import contextmanager
from typing import Dict, List, Optional

import pandas as pd
import psycopg2
import psycopg2.pool


_DEFAULT_TTL_SEC = 60 * 60  # 1 hour

# One pool per (db_url) — keyed so tests targeting a temp DB don't clash with a
# warm production pool. Sized 1..5; Neon free-tier caps are tight.
_POOLS: Dict[str, psycopg2.pool.SimpleConnectionPool] = {}
_POOL_LOCK = threading.Lock()
_SCHEMA_DONE: set[str] = set()


def _df_to_parquet_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    out = df.copy()
    out.index.name = out.index.name or "index"
    out = out.reset_index()
    out.to_parquet(buf, engine="pyarrow", index=False)
    return buf.getvalue()


def _parquet_bytes_to_df(payload: bytes) -> pd.DataFrame:
    buf = io.BytesIO(payload)
    df = pd.read_parquet(buf, engine="pyarrow")
    if df.columns.size and df.columns[0] in ("index", "Date", "Datetime"):
        df = df.set_index(df.columns[0])
    return df


class OHLCVCache:
    """Postgres cache for ticker OHLCV DataFrames keyed by (ticker, period).

    Public API is unchanged from the DuckDB version:
      get(ticker, period), get_many(tickers, period), put(ticker, period, df),
      put_many(items, period), purge_stale(), stats().
    """

    def __init__(self, db_url: Optional[str] = None, ttl_sec: int = _DEFAULT_TTL_SEC):
        self.db_url = db_url or os.environ.get("DATABASE_URL")
        if not self.db_url:
            raise RuntimeError(
                "DATABASE_URL not set. OHLCVCache requires a Postgres connection."
            )
        self.ttl_sec = ttl_sec
        self._init_schema()

    def _get_pool(self) -> psycopg2.pool.SimpleConnectionPool:
        with _POOL_LOCK:
            pool = _POOLS.get(self.db_url)
            if pool is None:
                pool = psycopg2.pool.SimpleConnectionPool(1, 5, self.db_url)
                _POOLS[self.db_url] = pool
        return pool

    @contextmanager
    def _conn(self):
        pool = self._get_pool()
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

    def _init_schema(self) -> None:
        if self.db_url in _SCHEMA_DONE:
            return
        with self._conn() as c:
            with c.cursor() as cur:
                cur.execute(
                    """CREATE TABLE IF NOT EXISTS ohlcv_cache (
                        ticker     TEXT NOT NULL,
                        period     TEXT NOT NULL,
                        data       BYTEA NOT NULL,
                        fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                        PRIMARY KEY (ticker, period)
                    )"""
                )
        _SCHEMA_DONE.add(self.db_url)

    def get(self, ticker: str, period: str) -> Optional[pd.DataFrame]:
        with self._conn() as c:
            with c.cursor() as cur:
                cur.execute(
                    """SELECT data FROM ohlcv_cache
                       WHERE ticker=%s AND period=%s
                         AND fetched_at >= now() - (%s || ' seconds')::interval""",
                    [ticker, period, str(self.ttl_sec)],
                )
                row = cur.fetchone()
        if row is None:
            return None
        try:
            return _parquet_bytes_to_df(bytes(row[0]))
        except Exception:
            return None

    def get_many(self, tickers: List[str], period: str) -> Dict[str, pd.DataFrame]:
        if not tickers:
            return {}
        with self._conn() as c:
            with c.cursor() as cur:
                cur.execute(
                    """SELECT ticker, data FROM ohlcv_cache
                       WHERE period=%s
                         AND ticker = ANY(%s)
                         AND fetched_at >= now() - (%s || ' seconds')::interval""",
                    [period, list(tickers), str(self.ttl_sec)],
                )
                rows = cur.fetchall()
        out: Dict[str, pd.DataFrame] = {}
        for ticker, payload in rows:
            try:
                out[ticker] = _parquet_bytes_to_df(bytes(payload))
            except Exception:
                continue
        return out

    def put(self, ticker: str, period: str, df: pd.DataFrame) -> None:
        payload = _df_to_parquet_bytes(df)
        with self._conn() as c:
            with c.cursor() as cur:
                cur.execute(
                    """INSERT INTO ohlcv_cache(ticker, period, data, fetched_at)
                       VALUES (%s, %s, %s, now())
                       ON CONFLICT (ticker, period) DO UPDATE
                         SET data = EXCLUDED.data,
                             fetched_at = EXCLUDED.fetched_at""",
                    [ticker, period, psycopg2.Binary(payload)],
                )

    def put_many(self, items: Dict[str, pd.DataFrame], period: str) -> None:
        if not items:
            return
        rows = [
            (t, period, psycopg2.Binary(_df_to_parquet_bytes(df)))
            for t, df in items.items()
        ]
        with self._conn() as c:
            with c.cursor() as cur:
                cur.executemany(
                    """INSERT INTO ohlcv_cache(ticker, period, data, fetched_at)
                       VALUES (%s, %s, %s, now())
                       ON CONFLICT (ticker, period) DO UPDATE
                         SET data = EXCLUDED.data,
                             fetched_at = EXCLUDED.fetched_at""",
                    rows,
                )

    def purge_stale(self, ttl_seconds: Optional[int] = None) -> int:
        # Purge cutoff is generous (default = 24× the read TTL) so a temporarily
        # offline yfinance can still serve "older but recent" data.
        ttl = ttl_seconds if ttl_seconds is not None else self.ttl_sec * 24
        with self._conn() as c:
            with c.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM ohlcv_cache")
                before = cur.fetchone()[0]
                cur.execute(
                    "DELETE FROM ohlcv_cache WHERE fetched_at < now() - (%s || ' seconds')::interval",
                    [str(ttl)],
                )
                cur.execute("SELECT COUNT(*) FROM ohlcv_cache")
                after = cur.fetchone()[0]
        return int(before - after)

    def stats(self) -> Dict[str, int]:
        with self._conn() as c:
            with c.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM ohlcv_cache")
                total = cur.fetchone()[0]
                cur.execute(
                    """SELECT COUNT(*) FROM ohlcv_cache
                       WHERE fetched_at >= now() - (%s || ' seconds')::interval""",
                    [str(self.ttl_sec)],
                )
                fresh = cur.fetchone()[0]
        return {"total": int(total), "fresh": int(fresh), "stale": int(total - fresh)}


def reset_pool_cache() -> None:
    """Test helper: close all pools so the next OHLCVCache() rebuilds them."""
    with _POOL_LOCK:
        for url, pool in list(_POOLS.items()):
            try:
                pool.closeall()
            except Exception:
                pass
        _POOLS.clear()
        _SCHEMA_DONE.clear()
