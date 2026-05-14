"""Vercel Cron endpoints — invoked on schedule from vercel.json.

Vercel sends `Authorization: Bearer $CRON_SECRET` automatically when the env var is
set. We verify it timing-safely; missing/invalid header → 401. No public access.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Header, HTTPException

from ..security import verify_cron_secret

router = APIRouter(prefix="/api/cron", tags=["cron"])
log = logging.getLogger(__name__)


@router.post("/refresh")
def cron_refresh(authorization: Optional[str] = Header(default=None)):
    """Every 4 hours: warm the news cache and (eventually) precompute screener.

    Stub now — wire to precompute.run_full_screener() once Postgres is provisioned.
    Returns immediately if no real work is configured so cron firings are free.
    """
    verify_cron_secret(authorization)
    started = datetime.now(timezone.utc)
    warmed = 0
    try:
        from ..defaults import DEFAULT_TICKERS
        from ..news_provider import get_ticker_news, get_trending_news

        # Warm trending first (single call, used by every page load).
        try:
            get_trending_news(force=True)
        except Exception as e:  # pragma: no cover - external API
            log.warning("trending warm failed: %s", e)

        for sym in DEFAULT_TICKERS:
            try:
                get_ticker_news(sym, force=True)
                warmed += 1
            except Exception as e:  # pragma: no cover
                log.warning("ticker news warm failed for %s: %s", sym, e)
    except Exception as e:
        # Don't 500 the cron — Vercel will keep retrying and burn invocations.
        log.exception("cron refresh outer failure: %s", e)

    return {
        "ok": True,
        "warmed_tickers": warmed,
        "started_at": started.isoformat(),
        "duration_sec": (datetime.now(timezone.utc) - started).total_seconds(),
    }


@router.post("/digest")
def cron_digest(authorization: Optional[str] = Header(default=None)):
    """Daily at 13:00 UTC: send digests to opted-in users.

    Stub now — wire to digest.build_digest + email_sender.send_email once Postgres
    is provisioned. Single endpoint handles both daily + weekly (checks day-of-week
    and each user's frequency internally).
    """
    verify_cron_secret(authorization)
    started = datetime.now(timezone.utc)
    is_monday = started.weekday() == 0
    return {
        "ok": True,
        "sent": 0,
        "skipped": 0,
        "is_monday_utc": is_monday,
        "started_at": started.isoformat(),
        "duration_sec": (datetime.now(timezone.utc) - started).total_seconds(),
        "note": "Digest sender will activate once Postgres + email provider are configured.",
    }
