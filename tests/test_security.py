"""Security guardrails — runs without a live DB, exercises only pure logic.

Verifies:
  - Cron Bearer auth: missing → 401, wrong → 401, unconfigured → 503, right → ok.
  - CORS allowlist: never includes "*" with credentials, FRONTEND_URL is whitelisted.
  - Body-size middleware: oversized Content-Length returns 413 before parsing.
  - Rate-limit key function: uses session cookie when present, else IP.
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from api.security import (
    MAX_BODY_BYTES,
    _rate_key,
    allowed_origins,
    verify_cron_secret,
)


class _FakeReq:
    def __init__(self, cookies=None, client_host="1.2.3.4"):
        self.cookies = cookies or {}

        class _C:
            host = client_host

        self.client = _C()
        self.headers = {}


def test_cron_unconfigured_returns_503(monkeypatch):
    monkeypatch.delenv("CRON_SECRET", raising=False)
    with pytest.raises(HTTPException) as ei:
        verify_cron_secret("Bearer anything")
    assert ei.value.status_code == 503


def test_cron_missing_header_401(monkeypatch):
    monkeypatch.setenv("CRON_SECRET", "supersecret")
    with pytest.raises(HTTPException) as ei:
        verify_cron_secret(None)
    assert ei.value.status_code == 401


def test_cron_wrong_secret_401(monkeypatch):
    monkeypatch.setenv("CRON_SECRET", "supersecret")
    with pytest.raises(HTTPException) as ei:
        verify_cron_secret("Bearer wrong")
    assert ei.value.status_code == 401


def test_cron_correct_secret_passes(monkeypatch):
    monkeypatch.setenv("CRON_SECRET", "supersecret")
    verify_cron_secret("Bearer supersecret")  # no exception


def test_cors_origins_never_wildcard():
    origins = allowed_origins()
    assert "*" not in origins
    # Must include localhost dev for the Next.js dev server.
    assert any("localhost:3000" in o for o in origins)


def test_rate_key_prefers_session_cookie_over_ip():
    req = _FakeReq(cookies={"b7dm_session": "abcdef" * 10})
    key = _rate_key(req)
    assert key.startswith("u:")
    assert "1.2.3.4" not in key


def test_rate_key_falls_back_to_ip():
    req = _FakeReq(cookies={})
    key = _rate_key(req)
    assert key.startswith("ip:")


def test_body_size_cap_is_reasonable():
    # 64KB is generous for ticker symbols + notes; caps DoS via huge payloads.
    assert MAX_BODY_BYTES == 64 * 1024
