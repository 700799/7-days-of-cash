"""Tickers (watchlist) API: add, list, duplicate (409), invalid symbol, delete."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_db_path):
    from api.main import create_app
    from api import auth as api_auth
    from api.db import get_write_conn
    from api.models import User

    app = create_app()

    # Override auth dependencies — pretend user is logged in.
    fake_user = User(id="g-test", email="test@example.com", name="Test", picture=None)
    app.dependency_overrides[api_auth.get_current_user] = lambda: fake_user
    app.dependency_overrides[api_auth.get_current_user_optional] = lambda: fake_user

    # Make sure the user row exists (for FK-ish consistency, though no FK constraint).
    api_auth.upsert_user(fake_user.id, fake_user.email, fake_user.name, None)
    # The upsert seeds DEFAULT_TICKERS; clear them so each test starts from a known-empty
    # watchlist (individual default-seed behavior is exercised in test_defaults.py).
    with get_write_conn() as c:
        c.execute("DELETE FROM watchlists WHERE user_id=?", [fake_user.id])

    with TestClient(app) as c:
        yield c


@pytest.fixture
def anon_client(tmp_db_path):
    from api.main import create_app
    from api import auth as api_auth

    app = create_app()
    app.dependency_overrides[api_auth.get_current_user_optional] = lambda: None
    with TestClient(app) as c:
        yield c


def test_list_empty(client):
    r = client.get("/api/tickers")
    assert r.status_code == 200
    assert r.json() == []


def test_list_anonymous_returns_empty(anon_client):
    r = anon_client.get("/api/tickers")
    assert r.status_code == 200
    assert r.json() == []


def test_add_and_list(client):
    with patch("api.routes.tickers._validate_symbol_exists", return_value=True):
        r = client.post("/api/tickers", json={"symbol": "aapl", "note": "fav"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["symbol"] == "AAPL"
    assert body["note"] == "fav"

    r = client.get("/api/tickers")
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["symbol"] == "AAPL"


def test_add_duplicate_returns_409(client):
    with patch("api.routes.tickers._validate_symbol_exists", return_value=True):
        client.post("/api/tickers", json={"symbol": "AAPL"})
        r = client.post("/api/tickers", json={"symbol": "AAPL"})
    assert r.status_code == 409


def test_add_invalid_symbol_format_returns_422(client):
    r = client.post("/api/tickers", json={"symbol": "not a symbol!"})
    assert r.status_code == 422


def test_add_unresolvable_symbol_returns_422(client):
    with patch("api.routes.tickers._validate_symbol_exists", return_value=False):
        r = client.post("/api/tickers", json={"symbol": "ZZZZZZ"})
    assert r.status_code == 422


def test_patch_note(client):
    with patch("api.routes.tickers._validate_symbol_exists", return_value=True):
        client.post("/api/tickers", json={"symbol": "AAPL", "note": "old"})
    r = client.patch("/api/tickers/AAPL", json={"note": "new"})
    assert r.status_code == 200
    assert r.json()["note"] == "new"


def test_delete(client):
    with patch("api.routes.tickers._validate_symbol_exists", return_value=True):
        client.post("/api/tickers", json={"symbol": "MSFT"})
    r = client.delete("/api/tickers/MSFT")
    assert r.status_code == 204
    assert client.get("/api/tickers").json() == []
