"""yfinance news fetcher with a Postgres-backed cache."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import yfinance as yf

from .config import get_settings
from .db import get_conn


# Indices used to seed the "market trending" mix. These three together give us a
# reasonably broad cross-section of US large-cap / tech / industrial coverage.
_TRENDING_INDICES = ("^GSPC", "^IXIC", "^DJI")


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


def _publish_epoch(item: Dict[str, Any]) -> int:
    """Best-effort sort key — older items go to the end."""
    src = item.get("content", item)
    pt = src.get("providerPublishTime") or item.get("providerPublishTime")
    if isinstance(pt, (int, float)):
        return int(pt)
    return 0


def _read_cache(key: str, ttl_sec: int) -> Optional[List[Dict[str, Any]]]:
    with get_conn() as c:
        with c.cursor() as cur:
            cur.execute(
                """SELECT payload FROM news_cache
                   WHERE cache_key=%s
                     AND fetched_at >= now() - (%s || ' seconds')::interval""",
                [key, str(ttl_sec)],
            )
            row = cur.fetchone()
    if not row:
        return None
    try:
        return json.loads(row[0])
    except Exception:
        return None


def _write_cache(key: str, items: List[Dict[str, Any]]) -> None:
    with get_conn() as c:
        with c.cursor() as cur:
            cur.execute(
                """INSERT INTO news_cache(cache_key, payload, fetched_at)
                   VALUES (%s, %s, now())
                   ON CONFLICT (cache_key) DO UPDATE SET payload=EXCLUDED.payload,
                                                        fetched_at=EXCLUDED.fetched_at""",
                [key, json.dumps(items)],
            )


def get_ticker_news(symbol: str, limit: int = 10, force: bool = False) -> List[Dict[str, Any]]:
    settings = get_settings()
    key = f"ticker:{symbol.upper()}"
    if not force:
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


def get_market_news(limit: int = 10, force: bool = False) -> List[Dict[str, Any]]:
    settings = get_settings()
    key = "market"
    if not force:
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


# Trending news has its own TTL (1 hour) — the underlying index data doesn't move
# as quickly as ticker-specific news.
TRENDING_TTL_SEC = 60 * 60


def get_trending_news(limit: int = 5, force: bool = False) -> List[Dict[str, Any]]:
    """Top market news drawn from the three major US indices.

    Dedupes by URL/title (case-insensitive), then sorts by publish time
    (newest first) and trims to `limit`. Cached for 1h under the key
    ``trending`` in `news_cache`.
    """
    key = "trending"
    if not force:
        cached = _read_cache(key, TRENDING_TTL_SEC)
        if cached is not None:
            return cached[:limit]

    raw_pool: List[Dict[str, Any]] = []
    for sym in _TRENDING_INDICES:
        try:
            raw = yf.Ticker(sym).news or []
        except Exception:
            raw = []
        raw_pool.extend(raw)

    # Sort by publish time DESC before dedupe so the newest copy survives.
    raw_pool.sort(key=_publish_epoch, reverse=True)

    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    deduped: List[Dict[str, Any]] = []
    for it in raw_pool:
        norm = _normalize_item(it)
        url_key = (norm.get("link") or "").strip().lower()
        title_key = (norm.get("title") or "").strip().lower()
        if not title_key:
            continue
        if url_key and url_key in seen_urls:
            continue
        if title_key in seen_titles:
            continue
        if url_key:
            seen_urls.add(url_key)
        seen_titles.add(title_key)
        deduped.append(norm)

    items = deduped[:limit]
    _write_cache(key, items)
    return items
