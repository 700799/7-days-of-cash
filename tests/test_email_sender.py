"""Tests for api/email_sender.py — no DATABASE_URL required.

All external I/O (httpx.post, smtplib.SMTP) is mocked so no network or
SMTP server is needed. Environment variables are monkeypatched per-test.
"""
import smtplib
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TO = "user@example.com"
SUBJECT = "Test subject"
HTML = "<p>Hello</p>"
TEXT = "Hello"


def _import():
    """Import lazily so env-var monkeypatching is in place before import side-effects."""
    from api.email_sender import send_email
    return send_email


# ---------------------------------------------------------------------------
# Resend (httpx) path
# ---------------------------------------------------------------------------


def test_resend_path_success(monkeypatch):
    """When RESEND_API_KEY is set and httpx returns 200, returns True."""
    monkeypatch.setenv("RESEND_API_KEY", "re_testkey")
    monkeypatch.delenv("SMTP_USER", raising=False)

    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("httpx.post", return_value=mock_response) as mock_post:
        send_email = _import()
        result = send_email(TO, SUBJECT, HTML, TEXT)

    assert result is True
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    assert call_kwargs[0][0] == "https://api.resend.com/emails"


def test_resend_path_called_with_correct_payload(monkeypatch):
    """Verifies the JSON body sent to Resend contains the expected fields."""
    monkeypatch.setenv("RESEND_API_KEY", "re_testkey")
    monkeypatch.delenv("SMTP_USER", raising=False)

    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("httpx.post", return_value=mock_response) as mock_post:
        send_email = _import()
        send_email(TO, SUBJECT, HTML, TEXT)

    _, kwargs = mock_post.call_args
    payload = kwargs["json"]
    assert payload["to"] == [TO]
    assert payload["subject"] == SUBJECT
    assert payload["html"] == HTML
    assert payload["text"] == TEXT


def test_resend_status_300_returns_false(monkeypatch):
    """When Resend returns status >= 300, send_email returns False."""
    monkeypatch.setenv("RESEND_API_KEY", "re_testkey")
    monkeypatch.delenv("SMTP_USER", raising=False)

    mock_response = MagicMock()
    mock_response.status_code = 422
    mock_response.text = "Unprocessable Entity"

    with patch("httpx.post", return_value=mock_response):
        send_email = _import()
        result = send_email(TO, SUBJECT, HTML, TEXT)

    assert result is False


def test_resend_status_exactly_300_returns_false(monkeypatch):
    """Boundary: status == 300 should also return False (>= 300)."""
    monkeypatch.setenv("RESEND_API_KEY", "re_testkey")
    monkeypatch.delenv("SMTP_USER", raising=False)

    mock_response = MagicMock()
    mock_response.status_code = 300
    mock_response.text = "Multiple Choices"

    with patch("httpx.post", return_value=mock_response):
        send_email = _import()
        result = send_email(TO, SUBJECT, HTML, TEXT)

    assert result is False


def test_resend_httpx_exception_returns_false(monkeypatch):
    """When httpx.post raises any exception, send_email returns False (no raise)."""
    monkeypatch.setenv("RESEND_API_KEY", "re_testkey")
    monkeypatch.delenv("SMTP_USER", raising=False)

    with patch("httpx.post", side_effect=Exception("network error")):
        send_email = _import()
        result = send_email(TO, SUBJECT, HTML, TEXT)

    assert result is False


# ---------------------------------------------------------------------------
# SMTP fallback path
# ---------------------------------------------------------------------------


def _make_smtp_mock():
    """Return a MagicMock that acts as smtplib.SMTP context manager."""
    smtp_instance = MagicMock()
    smtp_instance.__enter__ = MagicMock(return_value=smtp_instance)
    smtp_instance.__exit__ = MagicMock(return_value=False)
    smtp_cls = MagicMock(return_value=smtp_instance)
    return smtp_cls, smtp_instance


def test_smtp_path_used_when_no_resend_key(monkeypatch):
    """When RESEND_API_KEY is absent but SMTP_USER is set, uses SMTP path."""
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.setenv("SMTP_USER", "user@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")

    smtp_cls, smtp_instance = _make_smtp_mock()

    with patch("smtplib.SMTP", smtp_cls):
        send_email = _import()
        result = send_email(TO, SUBJECT, HTML, TEXT)

    assert result is True
    smtp_instance.starttls.assert_called_once()
    smtp_instance.login.assert_called_once_with("user@gmail.com", "secret")
    smtp_instance.sendmail.assert_called_once()


def test_smtp_raises_returns_false(monkeypatch):
    """When smtplib.SMTP raises, send_email returns False (no re-raise)."""
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.setenv("SMTP_USER", "user@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")

    with patch("smtplib.SMTP", side_effect=smtplib.SMTPException("conn refused")):
        send_email = _import()
        result = send_email(TO, SUBJECT, HTML, TEXT)

    assert result is False


def test_smtp_login_raises_returns_false(monkeypatch):
    """When SMTP login raises, send_email returns False."""
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.setenv("SMTP_USER", "user@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "wrong")

    smtp_cls, smtp_instance = _make_smtp_mock()
    smtp_instance.login.side_effect = smtplib.SMTPAuthenticationError(535, b"auth failed")

    with patch("smtplib.SMTP", smtp_cls):
        send_email = _import()
        result = send_email(TO, SUBJECT, HTML, TEXT)

    assert result is False


# ---------------------------------------------------------------------------
# No-provider path
# ---------------------------------------------------------------------------


def test_no_provider_returns_false(monkeypatch):
    """When neither RESEND_API_KEY nor SMTP_USER is set, returns False without raising."""
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.delenv("SMTP_USER", raising=False)

    send_email = _import()
    result = send_email(TO, SUBJECT, HTML, TEXT)

    assert result is False


# ---------------------------------------------------------------------------
# RESEND_API_KEY takes precedence over SMTP_USER
# ---------------------------------------------------------------------------


def test_resend_takes_priority_over_smtp(monkeypatch):
    """When both RESEND_API_KEY and SMTP_USER are set, httpx path is used (not SMTP)."""
    monkeypatch.setenv("RESEND_API_KEY", "re_testkey")
    monkeypatch.setenv("SMTP_USER", "user@gmail.com")

    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("httpx.post", return_value=mock_response) as mock_post, \
         patch("smtplib.SMTP") as mock_smtp:
        send_email = _import()
        result = send_email(TO, SUBJECT, HTML, TEXT)

    assert result is True
    mock_post.assert_called_once()
    mock_smtp.assert_not_called()
