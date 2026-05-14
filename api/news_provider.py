"""yfinance news fetcher with a 15-minute DuckDB-backed cache."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import yfinance as yf

from .config import get_settings
from .db import get_conn, get_write_conn


def _normalize_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a raw yfinance news item.

    yfinance returns either the legacy flat dict (`title`, `publisher`, `link`,
    `providerPublishTime`, `thumbnail.resolutions[]`) or the new wrapped form
    `{"content": {"title": ..., "provider": {"displayName": ...}, ...}}`.
    """
    src = item.get("content", item)

    title = src.get("title") or item.get("title")

    publisher = (
        src.get("publisher")
        or (src.get("provider") or {}).get("displayName")
        or item.get("publisher")
    )

    link = (
        src.get("link")
        or (src.get("clickThroughUrl") or {}).get("url")
        or (src.get("canonicalUrl") or {}).get("url")
        or item.get("link")
    )

    published_at: Optional[str] = None
    pt = src.get("providerPublishTime") or item.get("providerPublishTime")
    if isinstance(pt, (int, float)):
        published_at = datetime.fromtimestamp(int(pt), tz=timezone.utc).isoformat()
    else:
        pd = src.get("pubDate") or src.get("displayTime")
        if isinstance(pd, str):
            published_at = pd

    thumbnail: Optional[str] = None
    thumb = src.get("thumbnail") or item.get("thumbnail")
    if isinstance(thumb, dict):
        resolutions = thumb.get("resolutions") or []
        if resolutions and isinstance(resolutions, list):
            thumbnail = resolutions[0].get("url")
        else:
            thumbnail = thumb.get("url")

    return {
        "title": title or "",
        "publisher": publisher,
        "link": link,
        "published_at": published_at,
        "thumbnail": thumbnail,
    }


def _read_cache(key: str, ttl_sec: int) -> Optional[List[Dict[str, Any]]]:
    cutoff = datetime.utcnow() - timedelta(seconds=ttl_sec)
    with get_conn() as c:
        row = c.execute(
            "SELECT payload FROM news_cache WHERE cache_key=? AND fetched_at>=?",
            [key, cutoff],
        ).fetchone()
    if not row:
        return None
    try:
        return json.loads(row[0])
    except Exception:
        return None


def _write_cache(key: str, items: List[Dict[str, Any]]) -> None:
    with get_write_conn() as c:
        c.execute(
            """INSERT INTO news_cache(cache_key, payload, fetched_at)
               VALUES (?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT (cache_key) DO UPDATE SET payload=excluded.payload,
                                                    fetched_at=excluded.fetched_at""",
            [key, json.dumps(items)],
        )


def get_ticker_news(symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
    settings = get_settings()
    key = f"ticker:{symbol.upper()}"
    cached = _read_cache(key, settings.NEWS_TTL_SEC)
    if cached is not None:
        return cached[:limit]

    try:
        raw = yf.Ticker(symbol).news or []
    except Exception:
        raw = []

    items = [_normalize_item(it) for it in raw[:limit]]
    _write_cache(key, items)
    return items


def get_market_news(limit: int = 10) -> List[Dict[str, Any]]:
    settings = get_settings()
    key = "market"
    cached = _read_cache(key, settings.NEWS_TTL_SEC)
    if cached is not None:
        return cached[:limit]

    try:
        raw = yf.Ticker("^GSPC").news or []
    except Exception:
        raw = []

    items = [_normalize_item(it) for it in raw[:limit]]
    _write_cache(key, items)
    return items
