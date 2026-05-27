"""Cron endpoint tests — no real DB, no real external calls.

Tests ``POST /api/cron/refresh`` and ``POST /api/cron/digest`` with a
mocked-out news/screener layer and a dummy DATABASE_URL so the env check
inside ``api.db`` does not fire.

The news/screener functions are imported lazily inside the handler body
(``from ..news_provider import ...``), so we patch the source modules
directly (``api.news_provider.*``, ``api.precompute.*``) rather than
the cron module namespace.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    """Guarantee CRON_SECRET and a dummy DATABASE_URL for every test in this
    module, so the env guards in db.py and security.py are satisfied."""
    monkeypatch.setenv("CRON_SECRET", "supersecret")
    monkeypatch.setenv("DATABASE_URL", "postgresql://fake/db")


@pytest.fixture
def client(monkeypatch):
    """TestClient built from create_app() with all external calls patched at
    their source module so lazy imports inside the handler body are intercepted."""
    with (
        patch("api.news_provider.get_ticker_news", return_value=[]),
        patch("api.news_provider.get_trending_news", return_value=[]),
        patch(
            "api.precompute.run_full_screener",
            return_value={"error": None, "results_count": 5},
        ),
    ):
        from api.main import create_app

        app = create_app()
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


# ---------------------------------------------------------------------------
# /api/cron/refresh
# ---------------------------------------------------------------------------


class TestCronRefresh:
    ENDPOINT = "/api/cron/refresh"

    def test_missing_authorization_returns_401(self, client):
        r = client.post(self.ENDPOINT)
        assert r.status_code == 401

    def test_wrong_secret_returns_401(self, client):
        r = client.post(self.ENDPOINT, headers={"Authorization": "Bearer wrongsecret"})
        assert r.status_code == 401

    def test_correct_secret_returns_200_ok(self, client):
        r = client.post(self.ENDPOINT, headers={"Authorization": "Bearer supersecret"})
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True

    def test_refresh_response_has_expected_keys(self, client):
        r = client.post(self.ENDPOINT, headers={"Authorization": "Bearer supersecret"})
        body = r.json()
        for key in ("ok", "warmed_tickers", "screener_ok", "screener_results", "started_at", "duration_sec"):
            assert key in body, f"missing key: {key}"


# ---------------------------------------------------------------------------
# /api/cron/digest
# ---------------------------------------------------------------------------


def _make_digest_conn_mock():
    """Return a mock_get_conn whose nested cursor.fetchall() gives an empty list."""
    mock_cur = MagicMock()
    mock_cur.fetchall.return_value = []

    mock_cursor_cm = MagicMock()
    mock_cursor_cm.__enter__ = MagicMock(return_value=mock_cur)
    mock_cursor_cm.__exit__ = MagicMock(return_value=False)

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor_cm

    mock_conn_cm = MagicMock()
    mock_conn_cm.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn_cm.__exit__ = MagicMock(return_value=False)

    return MagicMock(return_value=mock_conn_cm)


class TestCronDigest:
    ENDPOINT = "/api/cron/digest"

    def _post(self, client, mock_get_conn=None):
        ctx = patch("api.db.get_conn", mock_get_conn) if mock_get_conn else patch("api.db.get_conn", _make_digest_conn_mock())
        with ctx:
            return client.post(self.ENDPOINT, headers={"Authorization": "Bearer supersecret"})

    def test_missing_authorization_returns_401(self, client):
        r = client.post(self.ENDPOINT)
        assert r.status_code == 401

    def test_wrong_secret_returns_401(self, client):
        r = client.post(self.ENDPOINT, headers={"Authorization": "Bearer bad"})
        assert r.status_code == 401

    def test_correct_secret_returns_200_ok(self, client):
        r = self._post(client)
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_digest_response_has_sent_and_skipped_keys(self, client):
        body = self._post(client).json()
        assert "sent" in body
        assert "skipped" in body

    def test_is_monday_utc_is_boolean(self, client):
        body = self._post(client).json()
        assert isinstance(body["is_monday_utc"], bool)
