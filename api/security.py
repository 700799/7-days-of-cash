"""Abuse protection: rate limiter, CORS hardening, cron auth, request size caps.

Centralized so every route applies the same defaults. Limits below are tuned for
Vercel Hobby (free) — they keep yfinance/Neon/Resend usage well under free tier
caps even under sustained scraping attempts.
"""
from __future__ import annotations

import hmac
import os
from typing import Callable, Optional

from fastapi import HTTPException, Request, status
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse


# ---- Rate limits (per source IP) -----------------------------------------------
# Sane defaults: enough for legit interactive usage, hostile to scrapers.
DEFAULT_LIMIT = "60/minute"          # GET endpoints (cached, cheap)
WRITE_LIMIT = "20/minute"            # POST/PATCH/DELETE on user data
EXPENSIVE_LIMIT = "5/minute"         # /screener/run — actually hits yfinance
AUTH_LIMIT = "10/minute"             # /auth/* — slow brute force
NEWS_LIMIT = "30/minute"             # /news/* — cached but still gated


def _rate_key(request: Request) -> str:
    """Per-user when authenticated (cookie), else per-IP.

    This means a single hostile IP can't burn budget across many users, but a
    legit logged-in user behind NAT isn't sharing a limit with their office.
    """
    cookie = request.cookies.get("b7dm_session")
    if cookie:
        return f"u:{cookie[:32]}"  # truncate to avoid unbounded keys
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(key_func=_rate_key, default_limits=[DEFAULT_LIMIT])


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Return JSON 429 (not the default text). Frontend reads .detail."""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "detail": "Too many requests. Slow down.",
            "retry_after_seconds": 60,
        },
        headers={"Retry-After": "60"},
    )


# ---- Cron auth -----------------------------------------------------------------
def verify_cron_secret(authorization: Optional[str]) -> None:
    """Vercel Cron sends `Authorization: Bearer ${CRON_SECRET}` if you set the env.

    Timing-safe compare so attackers can't probe via response-time differences.
    Raises 401 if header missing or wrong.
    """
    expected = os.environ.get("CRON_SECRET", "").strip()
    if not expected:
        # No secret configured — refuse rather than allow open access.
        raise HTTPException(status_code=503, detail="Cron not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Cron auth required")
    provided = authorization[len("Bearer ") :].strip()
    if not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="Invalid cron token")


# ---- Request body cap ----------------------------------------------------------
MAX_BODY_BYTES = 64 * 1024  # 64 KB — tickers/notes are tiny; nothing legit needs more


async def body_size_limit_middleware(request: Request, call_next: Callable):
    """Reject oversized bodies before they hit pydantic / DB."""
    cl = request.headers.get("content-length")
    if cl and cl.isdigit() and int(cl) > MAX_BODY_BYTES:
        return JSONResponse(
            status_code=413, content={"detail": f"Request body too large (>{MAX_BODY_BYTES} bytes)"}
        )
    return await call_next(request)


# ---- Allowed CORS origins ------------------------------------------------------
def allowed_origins() -> list[str]:
    """Strict allowlist — never `*` with `allow_credentials=True` (browser blocks it).

    Returns FRONTEND_URL + dev-localhost. Vercel preview domains can be added by
    setting FRONTEND_URL_PREVIEWS as a comma-separated env value.
    """
    from .config import get_settings

    s = get_settings()
    origins = {"http://localhost:3000", s.FRONTEND_URL}
    extra = os.environ.get("FRONTEND_URL_PREVIEWS", "")
    for url in (u.strip() for u in extra.split(",") if u.strip()):
        origins.add(url)
    return sorted(origins)
