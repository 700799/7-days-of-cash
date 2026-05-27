"""Email digest builder: subject + HTML + plain text for daily/weekly opt-in.

Sections:
  1. MARKET TRENDING — top 5 news items
  2. YOUR WATCHLIST MOVERS — one bullet per user ticker
  3. SCREENER LEADERS — top 5 from cached pre-computed results
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .defaults import DEFAULT_TICKERS
from .movers import build_mover
from .news_provider import get_trending_news


def _html_header() -> str:
    """Top of HTML email."""
    return """<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body { font-family: "Courier New", monospace; background: #000; color: #22ff88; }
    .container { max-width: 800px; margin: 0 auto; padding: 20px; }
    .section { margin: 30px 0; border-top: 1px solid #00d65a; padding-top: 20px; }
    .section-title { font-size: 14px; font-weight: bold; color: #22ff88; margin-bottom: 15px; }
    .mover-bullet { margin: 10px 0; line-height: 1.6; color: #8aff9f; }
    .mover-symbol { color: #22ff88; font-weight: bold; }
    .news-item { margin: 10px 0; padding: 10px; background: #0a2a0a; border-left: 2px solid #00d65a; }
    .news-title { color: #22ff88; margin: 5px 0; }
    .news-source { color: #6acc7e; font-size: 12px; }
    a { color: #22ff88; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .footer { margin-top: 40px; color: #6acc7e; font-size: 12px; border-top: 1px solid #00d65a; padding-top: 20px; }
  </style>
</head>
<body>
<div class="container">
  <div style="font-size: 12px; color: #6acc7e; margin-bottom: 30px;">
    📈 Best7DaysMula Market Digest
  </div>
"""


def _html_footer() -> str:
    """Bottom of HTML email."""
    return """
  <div class="footer">
    <p>This is an automated digest. <a href="https://best7daysmula.vercel.app">Manage preferences</a></p>
    <p>Screener runs every 4 hours. News cached for 4 hours.</p>
  </div>
</div>
</body>
</html>
"""


def _text_header() -> str:
    """Top of plain-text email."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""
📈 BEST7DAYSMULA MARKET DIGEST
Generated: {ts}

"""


def _text_footer() -> str:
    """Bottom of plain-text email."""
    return """

---
This is an automated digest. Manage preferences at: https://best7daysmula.vercel.app
Screener runs every 4 hours. News cached for 4 hours.
"""


def build_digest(
    user_id: str,
    user_watchlist: List[str],
    digest_frequency: str,
) -> Tuple[str, str, str]:
    """Build email subject + HTML + plain-text body.

    Args:
        user_id: user's unique ID (for personalization)
        user_watchlist: list of ticker symbols the user watches
        digest_frequency: "daily" or "weekly" (affects subject line)

    Returns:
        (subject, html_body, text_body)
    """
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%a, %b %-d" if sys.platform != "win32" else "%a, %b %#d")

    # Build subject
    subject = f"Best7DaysMula {digest_frequency.capitalize()} Digest — {date_str}"

    # --- Trending news (top 5) ---
    trending_items = []
    try:
        trending = get_trending_news(force=False)
        trending_items = trending[:5]
    except Exception:
        pass

    # --- Watchlist movers ---
    watchlist = user_watchlist if user_watchlist else DEFAULT_TICKERS
    watchlist_movers = []
    for sym in watchlist[:25]:  # Cap at 25 tickers per email
        try:
            mover = build_mover(sym)
            watchlist_movers.append(mover)
        except Exception:
            pass

    # --- Screener leaders (cached pre-computed) ---
    screener_leaders = []
    try:
        from .db import get_conn

        with get_conn() as c:
            with c.cursor() as cur:
                cur.execute(
                    """SELECT payload FROM screener_results
                       ORDER BY ran_at DESC LIMIT 1"""
                )
                row = cur.fetchone()
        if row:
            payload = json.loads(row[0])
            # Expect payload to be {'results': [...]} with at least 5 items
            screener_leaders = payload.get("results", [])[:5]
    except Exception:
        pass

    # --- Build HTML ---
    html_parts = [_html_header()]

    # Trending section
    if trending_items:
        html_parts.append("""
  <div class="section">
    <div class="section-title">> MARKET TRENDING</div>
""")
        for item in trending_items:
            title = item.get("title", "")
            link = item.get("link", "#")
            pub = item.get("publisher", "Unknown")
            html_parts.append(f"""
    <div class="news-item">
      <div class="news-title"><a href="{link}">{title}</a></div>
      <div class="news-source">{pub}</div>
    </div>
""")
        html_parts.append("  </div>")

    # Watchlist movers section
    if watchlist_movers:
        html_parts.append("""
  <div class="section">
    <div class="section-title">> YOUR WATCHLIST MOVERS</div>
""")
        for mover in watchlist_movers:
            summary = mover.get("summary", "")
            link = f"https://finance.yahoo.com/quote/{mover.get('symbol', '')}"
            html_parts.append(f"""
    <div class="mover-bullet">
      <a href="{link}">{summary}</a>
    </div>
""")
        html_parts.append("  </div>")

    # Screener leaders section
    if screener_leaders:
        html_parts.append("""
  <div class="section">
    <div class="section-title">> SCREENER LEADERS</div>
""")
        for leader in screener_leaders[:5]:
            symbol = leader.get("symbol", "")
            change_7d = leader.get("7d%", 0)
            summary = f"{symbol}: +{change_7d}% 7d"
            link = f"https://finance.yahoo.com/quote/{symbol}"
            html_parts.append(f"""
    <div class="mover-bullet">
      <a href="{link}">{summary}</a>
    </div>
""")
        html_parts.append("  </div>")

    html_parts.append(_html_footer())
    html_body = "".join(html_parts)

    # --- Build plain text ---
    text_parts = [_text_header()]

    if trending_items:
        text_parts.append("> MARKET TRENDING\n")
        for item in trending_items:
            title = item.get("title", "")
            pub = item.get("publisher", "Unknown")
            text_parts.append(f"  • {title} ({pub})\n")
        text_parts.append("\n")

    if watchlist_movers:
        text_parts.append("> YOUR WATCHLIST MOVERS\n")
        for mover in watchlist_movers:
            summary = mover.get("summary", "")
            text_parts.append(f"  • {summary}\n")
        text_parts.append("\n")

    if screener_leaders:
        text_parts.append("> SCREENER LEADERS\n")
        for leader in screener_leaders[:5]:
            symbol = leader.get("symbol", "")
            change_7d = leader.get("7d%", 0)
            text_parts.append(f"  • {symbol}: +{change_7d}% 7d\n")
        text_parts.append("\n")

    text_parts.append(_text_footer())
    text_body = "".join(text_parts)

    return subject, html_body, text_body
