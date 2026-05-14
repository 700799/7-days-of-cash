"""Email sender supporting Resend (preferred on Vercel) or SMTP fallback.

Picks the provider from env at call time so tests can monkeypatch without
re-importing the module. Always returns a bool — failures are logged but never
raised so cron loops don't abort on a single transient bounce.
"""
from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage
from typing import Optional

import httpx


log = logging.getLogger("best7days.email")


def _send_via_resend(to: str, subject: str, html: str, text: str, sender: Optional[str]) -> bool:
    api_key = os.environ.get("RESEND_API_KEY", "")
    from_addr = sender or os.environ.get("SMTP_FROM") or "noreply@best7daysmula.dev"
    try:
        resp = httpx.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": from_addr,
                "to": [to],
                "subject": subject,
                "html": html,
                "text": text,
            },
            timeout=15.0,
        )
        if resp.status_code >= 300:
            log.warning("Resend send failed status=%s body=%s", resp.status_code, resp.text[:200])
            return False
        return True
    except Exception as e:
        log.warning("Resend send raised: %s", e)
        return False


def _send_via_smtp(to: str, subject: str, html: str, text: str, sender: Optional[str]) -> bool:
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASSWORD", "")
    from_addr = sender or os.environ.get("SMTP_FROM") or user

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")

    try:
        with smtplib.SMTP(host, port, timeout=15) as srv:
            srv.starttls()
            srv.login(user, password)
            srv.sendmail(from_addr, [to], msg.as_string())
        return True
    except Exception as e:
        log.warning("SMTP send failed: %s", e)
        return False


def send_email(to: str, subject: str, html: str, text: str, sender: Optional[str] = None) -> bool:
    """Send one email. Returns True on success, False (logged) on failure."""
    if os.environ.get("RESEND_API_KEY"):
        return _send_via_resend(to, subject, html, text, sender)
    if os.environ.get("SMTP_USER"):
        return _send_via_smtp(to, subject, html, text, sender)
    log.warning("No email provider configured (RESEND_API_KEY / SMTP_USER); skipping send to %s", to)
    return False
