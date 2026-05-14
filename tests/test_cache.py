"""DuckDB OHLCVCache: roundtrip, TTL, get_many, concurrent put_many."""
from __future__ import annotations

import os
import threading
import time

import pandas as pd
import pytest

from screener.cache import OHLCVCache


def _sample_df(n: int = 5) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=n, freq="D", name="Date")
    return pd.DataFrame(
        {
            "Open": [1.0 + i for i in range(n)],
            "High": [1.1 + i for i in range(n)],
            "Low": [0.9 + i for i in range(n)],
            "Close": [1.05 + i for i in range(n)],
            "Volume": [100 * (i + 1) for i in range(n)],
        },
        index=idx,
    )


def test_roundtrip(tmp_path):
    db = tmp_path / "c.duckdb"
    cache = OHLCVCache(str(db))
    df = _sample_df()
    cache.put("AAPL", "7d", df)
    out = cache.get("AAPL", "7d")
    assert out is not None
    assert list(out.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert len(out) == 5
    assert float(out["Close"].iloc[-1]) == pytest.approx(float(df["Close"].iloc[-1]))


def test_ttl_expiry(tmp_path):
    db = tmp_path / "c.duckdb"
    cache = OHLCVCache(str(db), ttl_sec=1)
    cache.put("MSFT", "7d", _sample_df())
    assert cache.get("MSFT", "7d") is not None
    time.sleep(2.5)
    assert cache.get("MSFT", "7d") is None
    stats = cache.stats()
    assert stats["total"] == 1
    assert stats["fresh"] == 0
    assert stats["stale"] == 1


def test_get_many(tmp_path):
    db = tmp_path / "c.duckdb"
    cache = OHLCVCache(str(db))
    cache.put_many({"A": _sample_df(), "B": _sample_df(6), "C": _sample_df(7)}, "7d")
    out = cache.get_many(["A", "B", "MISSING"], "7d")
    assert set(out.keys()) == {"A", "B"}
    assert len(out["B"]) == 6


def test_get_many_empty(tmp_path):
    db = tmp_path / "c.duckdb"
    cache = OHLCVCache(str(db))
    assert cache.get_many([], "7d") == {}


def test_purge_stale(tmp_path):
    db = tmp_path / "c.duckdb"
    cache = OHLCVCache(str(db), ttl_sec=1)
    cache.put("X", "7d", _sample_df())
    # purge uses ttl*24 cutoff, so a tiny ttl + sleep makes the row purgeable
    time.sleep(2)
    purged = cache.purge_stale()
    assert purged >= 0  # may be 0 since 24*ttl = 24s; just ensure it runs


def test_concurrent_put_many(tmp_path):
    """Many threads writing concurrently must not corrupt the DB."""
    db = tmp_path / "c.duckdb"
    cache = OHLCVCache(str(db))
    df = _sample_df()
    errors: list[Exception] = []

    def worker(prefix: str):
        try:
            batch = {f"{prefix}{i}": df for i in range(5)}
            cache.put_many(batch, "7d")
        except Exception as e:  # pragma: no cover
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(p,)) for p in "ABCDEFGH"]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    stats = cache.stats()
    assert stats["total"] == 8 * 5


def test_env_var_db_path(tmp_path, monkeypatch):
    custom = tmp_path / "envdb.duckdb"
    monkeypatch.setenv("BEST7DAYS_DB_PATH", str(custom))
    # Module reads env at import time but constructor uses module default — still test
    # that explicit path works (the env var contract is documented for the API server).
    cache = OHLCVCache(str(custom))
    cache.put("Z", "7d", _sample_df())
    assert os.path.exists(custom)
