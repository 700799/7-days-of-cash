"""Tests for api/routes/screener.py — /api/screener/* endpoints.

Covers the live /run endpoint (Pro-gated, ticker cap), the /cached endpoint
(DB-backed, free+pro), and the /top + /export + /history endpoints.
No real network or DB calls.
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
# App fixture + shared helpers
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


@pytest.fixture
def pro_client():
    """TestClient with a Pro user injected via dependency override."""
    from api.main import app
    from api import auth as api_auth
    from api.tier import require_pro
    from api.models import User

    FAKE_PRO_USER = User(id="pro_user_1", email="pro@example.com", name="Pro User")

    app.dependency_overrides[api_auth.get_current_user] = lambda: FAKE_PRO_USER
    app.dependency_overrides[require_pro] = lambda: FAKE_PRO_USER

    yield TestClient(app, raise_server_exceptions=False)

    app.dependency_overrides.clear()


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
# /api/screener/run — Pro-only live endpoint
# ---------------------------------------------------------------------------

class TestRunScreener:
    def test_run_requires_pro_unauthenticated_gets_401(self, client):
        """Unauthenticated users cannot use the live screener."""
        resp = client.post("/api/screener/run", json={"tickers": ["AAPL"]})
        assert resp.status_code in (401, 403)

    def test_run_accepts_small_ticker_list(self, pro_client):
        tickers = ["AAPL", "NVDA", "MSFT"]
        with patch("api.routes.screener._run_pipeline", return_value=_fake_pipeline_result()):
            resp = pro_client.post("/api/screener/run", json={"tickers": tickers})
        assert resp.status_code == 200

    def test_run_rejects_over_50_tickers(self, pro_client):
        tickers = [f"T{i:03d}" for i in range(51)]
        resp = pro_client.post("/api/screener/run", json={"tickers": tickers})
        assert resp.status_code == 413

    def test_run_exactly_50_tickers_is_accepted(self, pro_client):
        tickers = [f"T{i:03d}" for i in range(50)]
        with patch("api.routes.screener._run_pipeline", return_value=_fake_pipeline_result()):
            resp = pro_client.post("/api/screener/run", json={"tickers": tickers})
        assert resp.status_code == 200

    def test_run_returns_results_list(self, pro_client):
        with patch("api.routes.screener._run_pipeline", return_value=_fake_pipeline_result()):
            resp = pro_client.post("/api/screener/run", json={"tickers": ["AAPL"]})
        data = resp.json()
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_run_with_no_tickers_uses_universe(self, pro_client):
        fake_out = _fake_pipeline_result()
        with patch("api.routes.screener._run_pipeline", return_value=fake_out) as mock_pipe:
            resp = pro_client.post("/api/screener/run", json={})
        assert resp.status_code == 200
        mock_pipe.assert_called_once()
        assert mock_pipe.call_args[0][0] is None

    def test_run_413_message_mentions_cached(self, pro_client):
        tickers = [f"T{i:03d}" for i in range(51)]
        resp = pro_client.post("/api/screener/run", json={"tickers": tickers})
        assert resp.status_code == 413
        assert "cached" in resp.json().get("detail", "").lower()


# ---------------------------------------------------------------------------
# /api/screener/cached — free + pro endpoint (no auth required)
# ---------------------------------------------------------------------------

class TestCachedScreener:
    CONN_PATCH = "api.routes.screener.get_conn"  # module-level import in screener.py

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
        with patch(self.CONN_PATCH, _make_mock_conn(row=row)):
            resp = client.get("/api/screener/cached")
        assert resp.status_code == 200

    def test_cached_returns_404_when_no_data(self, client):
        with patch(self.CONN_PATCH, _make_mock_conn(row=None)):
            resp = client.get("/api/screener/cached")
        assert resp.status_code == 404

    def test_cached_response_has_results_list(self, client):
        row = self._make_db_row(n_results=3)
        with patch(self.CONN_PATCH, _make_mock_conn(row=row)):
            resp = client.get("/api/screener/cached")
        data = resp.json()
        assert "results" in data
        assert len(data["results"]) == 3

    def test_cached_response_has_ran_at(self, client):
        row = self._make_db_row()
        with patch(self.CONN_PATCH, _make_mock_conn(row=row)):
            resp = client.get("/api/screener/cached")
        assert "ran_at" in resp.json()

    def test_cached_db_error_returns_500(self, client):
        @contextmanager
        def _broken_conn(*args, **kwargs):
            raise RuntimeError("DB is down")
            yield

        with patch(self.CONN_PATCH, _broken_conn):
            resp = client.get("/api/screener/cached")
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# /api/screener/top — free + pro endpoint
# ---------------------------------------------------------------------------

class TestTopScreener:
    CONN_PATCH = "api.routes.screener.get_conn"

    def _make_db_row_top(self, n_results: int = 10):
        payload = {"results": _fake_results(n_results)}
        return (json.dumps(payload),)

    def test_top_returns_list(self, client):
        row = self._make_db_row_top(10)
        with patch(self.CONN_PATCH, _make_mock_conn(row=row)):
            resp = client.get("/api/screener/top")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_top_default_n_is_10(self, client):
        row = self._make_db_row_top(20)
        with patch(self.CONN_PATCH, _make_mock_conn(row=row)):
            resp = client.get("/api/screener/top")
        assert len(resp.json()) == 10

    def test_top_respects_n_param(self, client):
        row = self._make_db_row_top(10)
        with patch(self.CONN_PATCH, _make_mock_conn(row=row)):
            resp = client.get("/api/screener/top?n=5")
        assert len(resp.json()) == 5

    def test_top_returns_minimal_fields(self, client):
        row = self._make_db_row_top(3)
        with patch(self.CONN_PATCH, _make_mock_conn(row=row)):
            resp = client.get("/api/screener/top")
        data = resp.json()
        assert len(data) > 0
        for field in ("ticker", "ret_7d", "score", "best_strategy"):
            assert field in data[0], f"Missing field: {field}"

    def test_top_n_zero_returns_400(self, client):
        assert client.get("/api/screener/top?n=0").status_code == 400

    def test_top_n_over_100_returns_400(self, client):
        assert client.get("/api/screener/top?n=101").status_code == 400

    def test_top_empty_cache_returns_empty_list(self, client):
        with patch(self.CONN_PATCH, _make_mock_conn(row=None)):
            resp = client.get("/api/screener/top")
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# /api/screener/export — Pro-only CSV download
# ---------------------------------------------------------------------------

class TestExportScreener:
    CONN_PATCH = "api.routes.screener.get_conn"

    def _make_db_row(self, n_results: int = 5):
        ran_at = datetime.now(timezone.utc)
        payload = {
            "ran_at": ran_at.isoformat(),
            "results": _fake_results(n_results),
        }
        return (ran_at, json.dumps(payload))

    def test_export_requires_pro(self, client):
        resp = client.get("/api/screener/export")
        assert resp.status_code in (401, 403)

    def test_export_returns_csv(self, pro_client):
        row = self._make_db_row()
        with patch(self.CONN_PATCH, _make_mock_conn(row=row)):
            resp = pro_client.get("/api/screener/export")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")

    def test_export_has_content_disposition(self, pro_client):
        row = self._make_db_row()
        with patch(self.CONN_PATCH, _make_mock_conn(row=row)):
            resp = pro_client.get("/api/screener/export")
        assert "attachment" in resp.headers.get("content-disposition", "")

    def test_export_csv_has_header_row(self, pro_client):
        row = self._make_db_row(3)
        with patch(self.CONN_PATCH, _make_mock_conn(row=row)):
            resp = pro_client.get("/api/screener/export")
        lines = resp.text.strip().split("\n")
        assert len(lines) >= 2  # header + at least 1 data row
        assert "ticker" in lines[0].lower()

    def test_export_404_when_no_cache(self, pro_client):
        with patch(self.CONN_PATCH, _make_mock_conn(row=None)):
            resp = pro_client.get("/api/screener/export")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# /api/screener/history — Pro-only history
# ---------------------------------------------------------------------------

class TestScreenerHistory:
    CONN_PATCH = "api.routes.screener.get_conn"

    def _make_history_rows(self, n: int = 3):
        rows = []
        for i in range(n):
            ran_at = datetime.now(timezone.utc)
            payload = {
                "results": _fake_results(5),
                "error": None,
            }
            rows.append((i + 1, ran_at, json.dumps(payload)))
        return rows

    def _make_multi_conn(self, rows):
        """Mock that returns all rows from fetchall."""
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = lambda s: s
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = rows

        mock_conn = MagicMock()
        mock_conn.__enter__ = lambda s: s
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        @contextmanager
        def _get_conn(*args, **kwargs):
            yield mock_conn

        return _get_conn

    def test_history_requires_pro(self, client):
        resp = client.get("/api/screener/history")
        assert resp.status_code in (401, 403)

    def test_history_returns_list(self, pro_client):
        rows = self._make_history_rows(3)
        with patch(self.CONN_PATCH, self._make_multi_conn(rows)):
            resp = pro_client.get("/api/screener/history")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        assert len(resp.json()) == 3

    def test_history_entries_have_required_fields(self, pro_client):
        rows = self._make_history_rows(2)
        with patch(self.CONN_PATCH, self._make_multi_conn(rows)):
            resp = pro_client.get("/api/screener/history")
        first = resp.json()[0]
        for field in ("id", "ran_at", "results_count", "top_5_tickers"):
            assert field in first, f"Missing field: {field}"

    def test_history_days_capped_at_30(self, pro_client):
        """days param > 30 is silently capped — shouldn't error."""
        rows = self._make_history_rows(1)
        with patch(self.CONN_PATCH, self._make_multi_conn(rows)):
            resp = pro_client.get("/api/screener/history?days=999")
        assert resp.status_code == 200
