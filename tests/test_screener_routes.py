"""Tests for api/routes/screener.py — /api/screener/* endpoints.

Covers the live /run endpoint (ticker cap), the /cached endpoint
(DB-backed), and the /top endpoint. No real network or DB calls.
"""
from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# App fixture
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_rate_limits():
    """Clear slowapi in-memory counters between tests to prevent 429 spillover."""
    from api.security import limiter
    if hasattr(limiter, "_storage") and hasattr(limiter._storage, "storage"):
        limiter._storage.storage.clear()
    yield


@pytest.fixture
def client():
    from api.main import app
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_results(n: int = 3) -> list:
    return [
        {
            "ticker": f"TICK{i}",
            "price": 100.0 + i,
            "change_7d": 10.0 + i,
            "ret_7d": 10.0 + i,
            "score": 80.0 + i,
            "composite_score": 80.0 + i,
            "momentum": 75.0,
            "breakout": 70.0,
            "volume": 65.0,
            "rs": 78.0,
            "mean_reversion": 60.0,
            "best_strategy": "momentum",
            "vs_voo": i * 1.5,
        }
        for i in range(n)
    ]


def _make_mock_conn(row=None):
    mock_cursor = MagicMock()
    mock_cursor.__enter__ = lambda s: s
    mock_cursor.__exit__ = MagicMock(return_value=False)
    mock_cursor.fetchone.return_value = row

    mock_conn = MagicMock()
    mock_conn.__enter__ = lambda s: s
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value = mock_cursor

    @contextmanager
    def _get_conn(*args, **kwargs):
        yield mock_conn

    return _get_conn


def _fake_pipeline_result():
    return {
        "regime": {"trend": "BULL"},
        "benchmarks": {"SPY": 1.0},
        "results": _fake_results(5),
        "ran_at": datetime.now(timezone.utc),
    }


# ---------------------------------------------------------------------------
# /api/screener/run — live endpoint
# ---------------------------------------------------------------------------

class TestRunScreener:
    def test_run_accepts_small_ticker_list(self, client):
        tickers = ["AAPL", "NVDA", "MSFT"]

        with patch("api.routes.screener._run_pipeline", return_value=_fake_pipeline_result()):
            resp = client.post("/api/screener/run", json={"tickers": tickers})

        assert resp.status_code == 200

    def test_run_rejects_over_50_tickers(self, client):
        tickers = [f"T{i:03d}" for i in range(51)]
        resp = client.post("/api/screener/run", json={"tickers": tickers})
        assert resp.status_code == 413

    def test_run_exactly_50_tickers_is_accepted(self, client):
        tickers = [f"T{i:03d}" for i in range(50)]

        with patch("api.routes.screener._run_pipeline", return_value=_fake_pipeline_result()):
            resp = client.post("/api/screener/run", json={"tickers": tickers})

        assert resp.status_code == 200

    def test_run_returns_results_list(self, client):
        with patch("api.routes.screener._run_pipeline", return_value=_fake_pipeline_result()):
            resp = client.post("/api/screener/run", json={"tickers": ["AAPL"]})

        data = resp.json()
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_run_with_no_tickers_uses_universe(self, client):
        """Passing no tickers triggers get_sp500_tickers fallback in pipeline."""
        fake_out = _fake_pipeline_result()

        with patch("api.routes.screener._run_pipeline", return_value=fake_out) as mock_pipe:
            resp = client.post("/api/screener/run", json={})

        assert resp.status_code == 200
        mock_pipe.assert_called_once()
        call_kwargs = mock_pipe.call_args[0]
        # First arg is tickers — should be None when not provided
        assert call_kwargs[0] is None

    def test_run_413_message_mentions_cached(self, client):
        tickers = [f"T{i:03d}" for i in range(51)]
        resp = client.post("/api/screener/run", json={"tickers": tickers})
        assert resp.status_code == 413
        body = resp.json()
        assert "cached" in body.get("detail", "").lower()


# ---------------------------------------------------------------------------
# /api/screener/cached — cache endpoint
# ---------------------------------------------------------------------------

class TestCachedScreener:
    def _make_db_row(self, n_results: int = 5):
        ran_at = datetime.now(timezone.utc)
        payload = {
            "ran_at": ran_at.isoformat(),
            "results_count": n_results,
            "results": _fake_results(n_results),
            "error": None,
        }
        return (ran_at, json.dumps(payload))

    def test_cached_returns_200_when_data_exists(self, client):
        row = self._make_db_row()
        with patch("api.db.get_conn", _make_mock_conn(row=row)):
            resp = client.get("/api/screener/cached")
        assert resp.status_code == 200

    def test_cached_returns_404_when_no_data(self, client):
        with patch("api.db.get_conn", _make_mock_conn(row=None)):
            resp = client.get("/api/screener/cached")
        assert resp.status_code == 404

    def test_cached_response_has_results_list(self, client):
        row = self._make_db_row(n_results=3)
        with patch("api.db.get_conn", _make_mock_conn(row=row)):
            resp = client.get("/api/screener/cached")
        data = resp.json()
        assert "results" in data
        assert len(data["results"]) == 3

    def test_cached_response_has_ran_at(self, client):
        row = self._make_db_row()
        with patch("api.db.get_conn", _make_mock_conn(row=row)):
            resp = client.get("/api/screener/cached")
        data = resp.json()
        assert "ran_at" in data

    def test_cached_db_error_returns_500(self, client):
        @contextmanager
        def _broken_conn(*args, **kwargs):
            raise RuntimeError("DB is down")
            yield  # make it a generator

        with patch("api.db.get_conn", _broken_conn):
            resp = client.get("/api/screener/cached")
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# /api/screener/top — top-N endpoint
# ---------------------------------------------------------------------------

class TestTopScreener:
    def _make_db_row_top(self, n_results: int = 10):
        payload = {
            "results": _fake_results(n_results),
        }
        return (json.dumps(payload),)

    def test_top_returns_list(self, client):
        row = self._make_db_row_top(10)
        with patch("api.db.get_conn", _make_mock_conn(row=row)):
            resp = client.get("/api/screener/top")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_top_default_n_is_10(self, client):
        row = self._make_db_row_top(20)
        with patch("api.db.get_conn", _make_mock_conn(row=row)):
            resp = client.get("/api/screener/top")
        assert len(resp.json()) == 10

    def test_top_respects_n_param(self, client):
        row = self._make_db_row_top(10)
        with patch("api.db.get_conn", _make_mock_conn(row=row)):
            resp = client.get("/api/screener/top?n=5")
        assert len(resp.json()) == 5

    def test_top_returns_minimal_fields(self, client):
        row = self._make_db_row_top(3)
        with patch("api.db.get_conn", _make_mock_conn(row=row)):
            resp = client.get("/api/screener/top")
        data = resp.json()
        assert len(data) > 0
        first = data[0]
        for field in ("ticker", "ret_7d", "score", "best_strategy"):
            assert field in first, f"Missing field: {field}"

    def test_top_n_zero_returns_400(self, client):
        resp = client.get("/api/screener/top?n=0")
        assert resp.status_code == 400

    def test_top_n_over_100_returns_400(self, client):
        resp = client.get("/api/screener/top?n=101")
        assert resp.status_code == 400

    def test_top_empty_cache_returns_empty_list(self, client):
        with patch("api.db.get_conn", _make_mock_conn(row=None)):
            resp = client.get("/api/screener/top")
        assert resp.status_code == 200
        assert resp.json() == []
