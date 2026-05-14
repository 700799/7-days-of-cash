"""DuckDB-backed OHLCV cache with TTL-based invalidation.

Stores DataFrames as parquet bytes in a BLOB column. Writes are guarded by
a threading.Lock because DuckDB does not handle high-concurrency writes well
from a single connection. Connections are opened per-call.
"""
from __future__ import annotations

import io
import os
import threading
import time
from contextlib import contextmanager
from typing import Dict, List, Optional

import duckdb
import pandas as pd

_DEFAULT_DB = os.environ.get(
    "BEST7DAYS_DB_PATH", os.path.join("data", "best7days.duckdb")
)
_DEFAULT_TTL_SEC = 60 * 60  # 1 hour

# Module-level write lock (DuckDB single-writer semantics). Per-path locks would
# be ideal but in practice the app uses one DB file.
_WRITE_LOCK = threading.Lock()


def _df_to_parquet_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    # Preserve the (DatetimeIndex) by resetting it into a column then restoring on read.
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
    """DuckDB cache for ticker OHLCV DataFrames keyed by (ticker, period).

    Public API matches the previous SQLite implementation:
      get(ticker, period), get_many(tickers, period), put(ticker, period, df),
      put_many(items, period), purge_stale(), stats()
    """

    def __init__(self, db_path: str = _DEFAULT_DB, ttl_sec: int = _DEFAULT_TTL_SEC):
        self.db_path = db_path
        self.ttl_sec = ttl_sec
        parent = os.path.dirname(self.db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _conn(self):
        conn = duckdb.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with _WRITE_LOCK, self._conn() as c:
            c.execute(
                """CREATE TABLE IF NOT EXISTS ohlcv_cache (
                    ticker     TEXT NOT NULL,
                    period     TEXT NOT NULL,
                    fetched_at BIGINT NOT NULL,
                    payload    BLOB NOT NULL,
                    PRIMARY KEY (ticker, period)
                )"""
            )

    def get(self, ticker: str, period: str) -> Optional[pd.DataFrame]:
        cutoff = int(time.time()) - self.ttl_sec
        with self._conn() as c:
            row = c.execute(
                "SELECT payload FROM ohlcv_cache WHERE ticker=? AND period=? AND fetched_at>=?",
                [ticker, period, cutoff],
            ).fetchone()
        if row is None:
            return None
        try:
            return _parquet_bytes_to_df(bytes(row[0]))
        except Exception:
            return None

    def get_many(self, tickers: List[str], period: str) -> Dict[str, pd.DataFrame]:
        if not tickers:
            return {}
        cutoff = int(time.time()) - self.ttl_sec
        placeholders = ",".join("?" * len(tickers))
        with self._conn() as c:
            rows = c.execute(
                f"SELECT ticker, payload FROM ohlcv_cache "
                f"WHERE period=? AND fetched_at>=? AND ticker IN ({placeholders})",
                [period, cutoff, *tickers],
            ).fetchall()
        out: Dict[str, pd.DataFrame] = {}
        for ticker, payload in rows:
            try:
                out[ticker] = _parquet_bytes_to_df(bytes(payload))
            except Exception:
                continue
        return out

    def put(self, ticker: str, period: str, df: pd.DataFrame) -> None:
        payload = _df_to_parquet_bytes(df)
        now = int(time.time())
        with _WRITE_LOCK, self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO ohlcv_cache(ticker, period, fetched_at, payload) "
                "VALUES (?,?,?,?)",
                [ticker, period, now, payload],
            )

    def put_many(self, items: Dict[str, pd.DataFrame], period: str) -> None:
        if not items:
            return
        now = int(time.time())
        rows = [(t, period, now, _df_to_parquet_bytes(df)) for t, df in items.items()]
        with _WRITE_LOCK, self._conn() as c:
            c.executemany(
                "INSERT OR REPLACE INTO ohlcv_cache(ticker, period, fetched_at, payload) "
                "VALUES (?,?,?,?)",
                rows,
            )

    def purge_stale(self) -> int:
        cutoff = int(time.time()) - (self.ttl_sec * 24)
        with _WRITE_LOCK, self._conn() as c:
            before = c.execute("SELECT COUNT(*) FROM ohlcv_cache").fetchone()[0]
            c.execute("DELETE FROM ohlcv_cache WHERE fetched_at < ?", [cutoff])
            after = c.execute("SELECT COUNT(*) FROM ohlcv_cache").fetchone()[0]
            return int(before - after)

    def stats(self) -> Dict[str, int]:
        with self._conn() as c:
            total = c.execute("SELECT COUNT(*) FROM ohlcv_cache").fetchone()[0]
            fresh = c.execute(
                "SELECT COUNT(*) FROM ohlcv_cache WHERE fetched_at >= ?",
                [int(time.time()) - self.ttl_sec],
            ).fetchone()[0]
        return {"total": int(total), "fresh": int(fresh), "stale": int(total - fresh)}
