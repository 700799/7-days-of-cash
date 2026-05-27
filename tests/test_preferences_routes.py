"""Preferences endpoint tests — no real DB, no real auth.

Tests ``GET /api/preferences`` and ``PATCH /api/preferences`` with:
  - ``get_current_user`` patched to return a synthetic User
  - ``api.db.get_conn`` patched with a context-manager MagicMock so no
    Postgres connection is ever attempted.
"""
from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.models import User

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FAKE_USER = User(id="test123", email="user@example.com", name="Test User")


def _make_conn_mock(fetchone_return=None):
    """Build a nested context-manager mock that looks like:

        with get_conn() as c:
            with c.cursor() as cur:
                cur.fetchone() -> fetchone_return
    """
    mock_cur = MagicMock()
    mock_cur.fetchone.return_value = fetchone_return

    # cursor() must work as a context manager
    mock_cursor_cm = MagicMock()
    mock_cursor_cm.__enter__ = MagicMock(return_value=mock_cur)
    mock_cursor_cm.__exit__ = MagicMock(return_value=False)

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor_cm

    # get_conn() itself is a context manager
    mock_conn_cm = MagicMock()
    mock_conn_cm.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn_cm.__exit__ = MagicMock(return_value=False)

    # get_conn is called as a function; make it return the context-manager obj
    mock_get_conn = MagicMock(return_value=mock_conn_cm)
    return mock_get_conn, mock_cur


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _fake_database_url(monkeypatch):
    """Prevent api.db from raising RuntimeError on import / pool creation."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://fake/db")


@pytest.fixture
def client():
    """TestClient with get_current_user overridden via dependency_overrides."""
    from api.main import create_app
    from api import auth as api_auth

    app = create_app()
    app.dependency_overrides[api_auth.get_current_user] = lambda: FAKE_USER
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture
def unauthed_client():
    """TestClient WITHOUT overriding get_current_user — real 401 path."""
    from api.main import create_app

    app = create_app()
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


# ---------------------------------------------------------------------------
# GET /api/preferences
# ---------------------------------------------------------------------------


class TestGetPreferences:
    ENDPOINT = "/api/preferences"

    def test_returns_defaults_when_no_db_row(self, client):
        mock_get_conn, _ = _make_conn_mock(fetchone_return=None)
        with patch("api.routes.preferences.get_conn", mock_get_conn):
            r = client.get(self.ENDPOINT)
        assert r.status_code == 200
        body = r.json()
        assert body["digest_frequency"] == "none"

    def test_returns_stored_values_when_db_has_row(self, client):
        # Row: (digest_frequency, digest_email, last_sent_at)
        mock_get_conn, _ = _make_conn_mock(fetchone_return=("daily", "other@example.com", None))
        with patch("api.routes.preferences.get_conn", mock_get_conn):
            r = client.get(self.ENDPOINT)
        assert r.status_code == 200
        body = r.json()
        assert body["digest_frequency"] == "daily"
        assert body["digest_email"] == "other@example.com"

    def test_no_auth_returns_401(self, unauthed_client):
        # With no session cookie and real auth logic, must get 401.
        with patch("api.db.get_conn"):  # prevent any real DB call
            r = unauthed_client.get(self.ENDPOINT)
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /api/preferences
# ---------------------------------------------------------------------------


class TestPatchPreferences:
    ENDPOINT = "/api/preferences"

    def test_valid_payload_returns_200_with_updated_values(self, client):
        # RETURNING row from INSERT … ON CONFLICT
        mock_get_conn, _ = _make_conn_mock(fetchone_return=("weekly", None, None))
        with patch("api.routes.preferences.get_conn", mock_get_conn):
            r = client.patch(self.ENDPOINT, json={"digest_frequency": "weekly"})
        assert r.status_code == 200
        body = r.json()
        assert body["digest_frequency"] == "weekly"

    def test_valid_payload_with_email_returns_updated_email(self, client):
        mock_get_conn, _ = _make_conn_mock(
            fetchone_return=("daily", "custom@example.com", None)
        )
        with patch("api.routes.preferences.get_conn", mock_get_conn):
            r = client.patch(
                self.ENDPOINT,
                json={"digest_frequency": "daily", "digest_email": "custom@example.com"},
            )
        assert r.status_code == 200
        body = r.json()
        assert body["digest_email"] == "custom@example.com"

    def test_invalid_email_returns_422(self, client):
        r = client.patch(
            self.ENDPOINT,
            json={"digest_frequency": "daily", "digest_email": "not-an-email"},
        )
        assert r.status_code == 422

    def test_invalid_frequency_returns_422(self, client):
        r = client.patch(
            self.ENDPOINT,
            json={"digest_frequency": "monthly"},  # not in Literal["none","daily","weekly"]
        )
        assert r.status_code == 422
