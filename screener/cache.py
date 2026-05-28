"""SQLite-backed OHLCV cache with TTL-based invalidation."""

from __future__ import annotations

import os
import pickle
import sqlite3
import time
from contextlib import contextmanager
from typing import Dict

import pandas as pd

_DEFAULT_DB = os.path.expanduser("~/.best7days_cache.db")
_DEFAULT_TTL_SEC = 60 * 60  # 1 hour


class OHLCVCache:
    """Thread-safe SQLite cache for ticker OHLCV DataFrames.

    Schema:
        cache(ticker TEXT, period TEXT, fetched_at INTEGER, payload BLOB)

    Uses WAL journaling for concurrent reads, pickle for DataFrame payloads.
    """

    def __init__(self, db_path: str = _DEFAULT_DB, ttl_sec: int = _DEFAULT_TTL_SEC):
        self.db_path = db_path
        self.ttl_sec = ttl_sec
        self._init_schema()

    def _init_schema(self) -> None:
        with self._conn() as c:
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA synchronous=NORMAL")
            c.execute(
                """CREATE TABLE IF NOT EXISTS cache (
                    ticker     TEXT NOT NULL,
                    period     TEXT NOT NULL,
                    fetched_at INTEGER NOT NULL,
                    payload    BLOB NOT NULL,
                    PRIMARY KEY (ticker, period)
                )"""
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_fetched ON cache(fetched_at)")

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def get(self, ticker: str, period: str) -> pd.DataFrame | None:
        cutoff = int(time.time()) - self.ttl_sec
        with self._conn() as c:
            row = c.execute(
                "SELECT payload FROM cache WHERE ticker=? AND period=? AND fetched_at>=?",
                (ticker, period, cutoff),
            ).fetchone()
        if row is None:
            return None
        try:
            return pickle.loads(row[0])
        except Exception:
            return None

    def get_many(self, tickers: list, period: str) -> Dict[str, pd.DataFrame]:
        if not tickers:
            return {}
        cutoff = int(time.time()) - self.ttl_sec
        placeholders = ",".join("?" * len(tickers))
        with self._conn() as c:
            rows = c.execute(
                f"SELECT ticker, payload FROM cache WHERE period=? AND fetched_at>=? AND ticker IN ({placeholders})",
                (period, cutoff, *tickers),
            ).fetchall()
        out: Dict[str, pd.DataFrame] = {}
        for ticker, payload in rows:
            try:
                out[ticker] = pickle.loads(payload)
            except Exception:
                continue
        return out

    def put(self, ticker: str, period: str, df: pd.DataFrame) -> None:
        payload = pickle.dumps(df, protocol=pickle.HIGHEST_PROTOCOL)
        now = int(time.time())
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO cache(ticker, period, fetched_at, payload) VALUES (?,?,?,?)",
                (ticker, period, now, payload),
            )

    def put_many(self, items: Dict[str, pd.DataFrame], period: str) -> None:
        if not items:
            return
        now = int(time.time())
        rows = [
            (t, period, now, pickle.dumps(df, protocol=pickle.HIGHEST_PROTOCOL))
            for t, df in items.items()
        ]
        with self._conn() as c:
            c.executemany(
                "INSERT OR REPLACE INTO cache(ticker, period, fetched_at, payload) VALUES (?,?,?,?)",
                rows,
            )

    def purge_stale(self) -> int:
        cutoff = int(time.time()) - (self.ttl_sec * 24)  # purge anything older than 24x TTL
        with self._conn() as c:
            cur = c.execute("DELETE FROM cache WHERE fetched_at < ?", (cutoff,))
            return cur.rowcount

    def stats(self) -> Dict[str, int]:
        with self._conn() as c:
            total = c.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
            fresh = c.execute(
                "SELECT COUNT(*) FROM cache WHERE fetched_at >= ?",
                (int(time.time()) - self.ttl_sec,),
            ).fetchone()[0]
        return {"total": total, "fresh": fresh, "stale": total - fresh}
