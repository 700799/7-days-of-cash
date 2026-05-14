"""Mover summaries combining recent OHLCV with the freshest headlines.

A "mover" is a one-shot snapshot for a ticker: ~7-day % change, latest price,
and a one-line text summary that the digest email + watchlist sidebar can
display verbatim. Reads OHLCV from the cache (warming it via fetch_batch on a
miss) and news from the existing news_provider cache.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from . import news_provider


def _arrow_for(change: float) -> str:
    if change > 0.5:
        return "▲"  # ▲
    if change < -0.5:
        return "▼"  # ▼
    return "▬"      # ▬


def _format_change(change: float) -> str:
    """Pretty-print +/-12.3% style strings."""
    sign = "+" if change >= 0 else ""
    return f"{sign}{change:.1f}%"


def _pct_change(latest: float, prior: float) -> float:
    if prior <= 0:
        return 0.0
    return (latest / prior - 1.0) * 100.0


def _load_ohlcv(symbol: str, period: str = "10d") -> Optional[pd.DataFrame]:
    """Pull OHLCV from cache, fall back to a one-shot yfinance fetch on miss."""
    from screener.cache import OHLCVCache
    from screener.data_fetcher import fetch_batch

    cache = OHLCVCache()
    df = cache.get(symbol, period)
    if df is not None and not df.empty:
        return df

    fetched = fetch_batch([symbol], period=period, cache=cache, use_cache=True)
    return fetched.get(symbol)


def build_mover(symbol: str) -> Dict[str, Any]:
    """Return a mover snapshot dict for ``symbol``.

    Shape:
      {symbol, price, change_7d, change_1d, summary, headlines: [...]}.
    Always returns a dict — the ``summary`` text encodes the fallback story
    (no OHLCV, no news, both).
    """
    symbol = symbol.upper()
    df = _load_ohlcv(symbol)
    headlines_raw = news_provider.get_ticker_news(symbol, limit=2)
    headlines: List[Dict[str, Any]] = [
        {
            "title": h.get("title"),
            "link": h.get("link"),
            "publisher": h.get("publisher"),
            "published_at": h.get("published_at"),
        }
        for h in headlines_raw[:2]
    ]

    if df is None or df.empty or "Close" not in df.columns:
        return {
            "symbol": symbol,
            "price": None,
            "change_7d": None,
            "change_1d": None,
            "summary": f"{symbol}: No recent activity.",
            "headlines": headlines,
        }

    close = df["Close"].dropna().astype(float)
    if close.empty:
        return {
            "symbol": symbol,
            "price": None,
            "change_7d": None,
            "change_1d": None,
            "summary": f"{symbol}: No recent activity.",
            "headlines": headlines,
        }

    price = float(close.iloc[-1])
    n = len(close)

    # 7-day lookback by trading days; fall back to oldest available bar if we
    # don't have 7 yet.
    lookback_7 = min(7, n - 1) if n > 1 else 0
    base_7 = float(close.iloc[-1 - lookback_7]) if lookback_7 else price
    change_7d = _pct_change(price, base_7)

    base_1 = float(close.iloc[-2]) if n >= 2 else price
    change_1d = _pct_change(price, base_1)

    arrow = _arrow_for(change_7d)
    change_str = _format_change(change_7d)

    if headlines:
        h1 = (headlines[0].get("title") or "").strip()
        h2 = (headlines[1].get("title") or "").strip() if len(headlines) >= 2 else ""
        if h1 and h2:
            summary = (
                f"{symbol} {arrow} {change_str} over 7d (${price:.2f}). "
                f"Headlines: '{h1}'. '{h2}'."
            )
        elif h1:
            summary = (
                f"{symbol} {arrow} {change_str} over 7d (${price:.2f}). "
                f"Headlines: '{h1}'."
            )
        else:
            summary = (
                f"{symbol} {arrow} {change_str} over 7d (${price:.2f}). "
                f"No recent headlines."
            )
    else:
        summary = (
            f"{symbol} {arrow} {change_str} over 7d (${price:.2f}). "
            f"No recent headlines."
        )

    return {
        "symbol": symbol,
        "price": round(price, 2),
        "change_7d": round(change_7d, 2),
        "change_1d": round(change_1d, 2),
        "summary": summary,
        "headlines": headlines,
    }
