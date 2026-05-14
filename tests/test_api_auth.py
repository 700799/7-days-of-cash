"""Auth API: session creation, /me, logout, mocked OAuth callback."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_db_path):
    from api.main import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c


def test_me_unauthenticated_returns_401(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_session_flow_via_direct_helpers(client):
    """Use the lower-level helpers (mocking Authlib end-to-end is brittle).

    The OAuth callback's only DB-touching steps are upsert_user + create_session,
    so we verify those plus the resulting cookie-based /me lookup.
    """
    from api.auth import create_session, upsert_user
    from api.config import get_settings

    upsert_user("g-42", "u@example.com", "User", "https://pic")
    token = create_session("g-42")

    cookie_name = get_settings().SESSION_COOKIE_NAME
    client.cookies.set(cookie_name, token)

    r = client.get("/api/auth/me")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "g-42"
    assert body["email"] == "u@example.com"

    r = client.post("/api/auth/logout")
    assert r.status_code == 200

    # After logout the session row is gone — cookie alone is no longer valid.
    client.cookies.set(cookie_name, token)
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_callback_upserts_and_sets_cookie(client):
    """Mock Authlib's authorize_access_token to simulate a successful Google return."""
    from api.config import get_settings
    from api.db import get_conn

    fake_token = {
        "userinfo": {
            "sub": "g-callback",
            "email": "cb@example.com",
            "name": "CB User",
            "picture": "https://pic",
        }
    }

    fake_google = MagicMock()
    fake_google.authorize_access_token = AsyncMock(return_value=fake_token)
    fake_oauth = MagicMock()
    fake_oauth.google = fake_google

    with patch("api.routes.auth.get_oauth", return_value=fake_oauth):
        r = client.get("/api/auth/callback", follow_redirects=False)

    assert r.status_code in (302, 307)
    cookie_name = get_settings().SESSION_COOKIE_NAME
    assert cookie_name in r.cookies

    with get_conn() as c:
        row = c.execute("SELECT email FROM users WHERE id=?", ["g-callback"]).fetchone()
    assert row is not None
    assert row[0] == "cb@example.com"


def test_login_redirects_to_google(client, monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "fake-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "fake-secret")

    from api import auth as api_auth
    from api import config as api_config

    api_config.get_settings.cache_clear()  # type: ignore[attr-defined]
    api_auth.reset_oauth_cache()

    fake_google = MagicMock()
    from starlette.responses import RedirectResponse

    async def fake_redirect(request, redirect_uri):
        return RedirectResponse(
            url=f"https://accounts.google.com/o/oauth2/v2/auth?redirect_uri={redirect_uri}"
        )

    fake_google.authorize_redirect = fake_redirect
    fake_oauth = MagicMock()
    fake_oauth.google = fake_google

    with patch("api.routes.auth.get_oauth", return_value=fake_oauth):
        r = client.get("/api/auth/login/google", follow_redirects=False)

    assert r.status_code in (302, 307)
    assert "accounts.google.com" in r.headers["location"]
