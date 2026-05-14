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
    """Every 4 hours: warm the news cache and precompute screener results.

    Runs the full screener pipeline and caches results. Also refreshes news
    cache for trending + all user watchlist symbols.
    """
    verify_cron_secret(authorization)
    started = datetime.now(timezone.utc)
    warmed = 0
    screener_ok = False
    screener_results = 0
    error_msg = None

    try:
        from ..defaults import DEFAULT_TICKERS
        from ..news_provider import get_ticker_news, get_trending_news
        from ..precompute import run_full_screener

        # Warm trending news first (single call, used by every page load).
        try:
            get_trending_news(force=True)
        except Exception as e:  # pragma: no cover - external API
            log.warning("trending warm failed: %s", e)

        # Warm ticker news for all DEFAULT_TICKERS
        for sym in DEFAULT_TICKERS:
            try:
                get_ticker_news(sym, force=True)
                warmed += 1
            except Exception as e:  # pragma: no cover
                log.warning("ticker news warm failed for %s: %s", sym, e)

        # Run screener precompute
        try:
            screener_payload = run_full_screener()
            screener_ok = screener_payload.get("error") is None
            screener_results = screener_payload.get("results_count", 0)
        except Exception as e:
            log.exception("Screener precompute failed: %s", e)
            error_msg = str(e)

    except Exception as e:
        # Don't 500 the cron — Vercel will keep retrying and burn invocations.
        log.exception("cron refresh outer failure: %s", e)
        error_msg = str(e)

    return {
        "ok": True,
        "warmed_tickers": warmed,
        "screener_ok": screener_ok,
        "screener_results": screener_results,
        "error": error_msg,
        "started_at": started.isoformat(),
        "duration_sec": (datetime.now(timezone.utc) - started).total_seconds(),
    }


@router.post("/digest")
def cron_digest(authorization: Optional[str] = Header(default=None)):
    """Daily at 13:00 UTC: send digests to opted-in users.

    Single endpoint handles both daily + weekly (checks day-of-week and each
    user's frequency internally).
    """
    verify_cron_secret(authorization)
    started = datetime.now(timezone.utc)
    is_monday = started.weekday() == 0

    sent = 0
    skipped = 0
    errors = 0

    try:
        from ..db import get_conn
        from ..digest import build_digest
        from ..email_sender import send_email

        with get_conn() as c:
            with c.cursor() as cur:
                cur.execute(
                    """SELECT u.id, u.email, up.digest_frequency, up.digest_email, array_agg(w.ticker) as tickers
                       FROM users u
                       LEFT JOIN user_preferences up ON u.id = up.user_id
                       LEFT JOIN watchlists w ON u.id = w.user_id
                       WHERE up.digest_frequency IS NOT NULL
                         AND up.digest_frequency != 'none'
                       GROUP BY u.id, u.email, up.digest_frequency, up.digest_email"""
                )
                rows = cur.fetchall()

        for row in rows:
            user_id, user_email, freq, pref_email, tickers = row
            if freq is None or freq == "none":
                skipped += 1
                continue

            # Check if this run should send to this user
            should_send = False
            if freq == "daily":
                should_send = True
            elif freq == "weekly" and is_monday:
                should_send = True

            if not should_send:
                skipped += 1
                continue

            # Build and send digest
            try:
                to_addr = pref_email or user_email
                watchlist = tickers or []
                subject, html, text = build_digest(user_id, watchlist, freq)
                success = send_email(to_addr, subject, html, text)
                if success:
                    sent += 1
                    # Update last_sent_at
                    with get_conn() as c:
                        with c.cursor() as cur:
                            cur.execute(
                                """UPDATE user_preferences
                                   SET last_sent_at = now()
                                   WHERE user_id = %s""",
                                [user_id],
                            )
                else:
                    errors += 1
            except Exception as e:
                log.warning(f"Failed to build/send digest for user {user_id}: {e}")
                errors += 1

    except Exception as e:
        log.exception("Cron digest outer failure")

    return {
        "ok": True,
        "sent": sent,
        "skipped": skipped,
        "errors": errors,
        "is_monday_utc": is_monday,
        "started_at": started.isoformat(),
        "duration_sec": (datetime.now(timezone.utc) - started).total_seconds(),
    }
