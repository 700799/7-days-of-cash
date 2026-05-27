"""Pure-logic unit tests for api/digest.py — build_digest().

No real database or network calls are made. All external dependencies
(get_trending_news, build_mover, get_conn / DB) are replaced with
unittest.mock stubs.
"""
from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Shared fake data
# ---------------------------------------------------------------------------

_FAKE_NEWS = [
    {
        "title": f"Market headline {i}",
        "publisher": f"Publisher{i}",
        "link": f"https://news.example.com/{i}",
        "published_at": "2026-05-26T10:00:00+00:00",
        "thumbnail": None,
    }
    for i in range(1, 6)  # 5 items
]

_FAKE_MOVER_TEMPLATE = {
    "symbol": "NVDA",
    "price": 950.12,
    "change_7d": 8.4,
    "change_1d": 1.2,
    "summary": "NVDA ▲ +8.4% over 7d ($950.12). Headlines: 'AI chip demand soars'.",
    "headlines": [
        {"title": "AI chip demand soars", "link": "https://example.com/ai", "publisher": "Reuters", "published_at": None}
    ],
}


def _make_fake_mover(symbol: str) -> dict:
    """Return a mover dict with the given symbol."""
    m = dict(_FAKE_MOVER_TEMPLATE)
    m["symbol"] = symbol
    m["summary"] = f"{symbol} ▲ +8.4% over 7d ($950.12). Headlines: 'Fake headline for {symbol}'."
    return m


def _make_mock_conn(row=None):
    """Return a get_conn context-manager mock whose cursor.fetchone returns row."""
    mock_cursor = MagicMock()
    mock_cursor.__enter__ = lambda s: s
    mock_cursor.__exit__ = MagicMock(return_value=False)
    mock_cursor.fetchone.return_value = row

    mock_conn = MagicMock()
    mock_conn.__enter__ = lambda s: s
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value = mock_cursor

    @contextmanager
    def _get_conn(*args, **kwargs):
        yield mock_conn

    return _get_conn


# ---------------------------------------------------------------------------
# Helper: run build_digest with all externals mocked
# ---------------------------------------------------------------------------

def _run_build_digest(
    user_id: str = "user123",
    watchlist: list | None = None,
    frequency: str = "daily",
    screener_row=None,
):
    """Invoke build_digest with controlled mocks; return (subject, html, text)."""
    if watchlist is None:
        watchlist = ["NVDA", "AAPL"]

    fake_movers = {sym: _make_fake_mover(sym) for sym in watchlist}

    with (
        patch("api.digest.get_trending_news", return_value=_FAKE_NEWS),
        patch("api.digest.build_mover", side_effect=lambda sym: fake_movers.get(sym, _make_fake_mover(sym))),
        patch("api.db.get_conn", _make_mock_conn(row=screener_row)),
    ):
        from api.digest import build_digest
        return build_digest(user_id, watchlist, frequency)


# ---------------------------------------------------------------------------
# Return shape tests
# ---------------------------------------------------------------------------

class TestBuildDigestReturnShape:
    def test_returns_three_tuple(self):
        result = _run_build_digest()
        assert isinstance(result, tuple), "build_digest must return a tuple"
        assert len(result) == 3, "build_digest must return a 3-tuple"

    def test_all_three_elements_are_strings(self):
        subject, html, text = _run_build_digest()
        assert isinstance(subject, str), "subject must be a str"
        assert isinstance(html, str), "html body must be a str"
        assert isinstance(text, str), "text body must be a str"

    def test_subject_contains_digest(self):
        subject, _, _ = _run_build_digest()
        assert "Digest" in subject

    def test_subject_contains_frequency_for_daily(self):
        subject, _, _ = _run_build_digest(frequency="daily")
        # Subject format: "Best7DaysMula Daily Digest — Mon, May 26"
        lower = subject.lower()
        assert "daily" in lower, f"'daily' not found in subject: {subject!r}"

    def test_subject_contains_frequency_for_weekly(self):
        subject, _, _ = _run_build_digest(frequency="weekly")
        lower = subject.lower()
        assert "weekly" in lower, f"'weekly' not found in subject: {subject!r}"

    def test_subject_contains_date_string(self):
        """Subject should include a date-like substring (e.g. 'May', a month name)."""
        import calendar
        subject, _, _ = _run_build_digest()
        months = list(calendar.month_abbr)[1:]  # Jan..Dec
        assert any(m in subject for m in months), (
            f"No month abbreviation found in subject: {subject!r}"
        )


# ---------------------------------------------------------------------------
# HTML content tests
# ---------------------------------------------------------------------------

class TestBuildDigestHtml:
    def test_html_has_doctype(self):
        _, html, _ = _run_build_digest()
        assert "<!DOCTYPE html>" in html or "<!doctype html>" in html.lower()

    def test_html_has_body_tag(self):
        _, html, _ = _run_build_digest()
        assert "<body" in html and "</body>" in html

    def test_html_contains_trending_news_titles(self):
        _, html, _ = _run_build_digest()
        for item in _FAKE_NEWS:
            assert item["title"] in html, (
                f"Trending news title {item['title']!r} missing from HTML"
            )

    def test_html_contains_trending_section_header(self):
        _, html, _ = _run_build_digest()
        assert "MARKET TRENDING" in html

    def test_html_contains_watchlist_section_header(self):
        _, html, _ = _run_build_digest(watchlist=["NVDA", "AAPL"])
        assert "WATCHLIST" in html

    def test_html_contains_mover_summaries(self):
        watchlist = ["NVDA", "AAPL"]
        _, html, _ = _run_build_digest(watchlist=watchlist)
        for sym in watchlist:
            assert sym in html, f"Symbol {sym} not found in HTML"

    def test_html_contains_anchor_tags(self):
        _, html, _ = _run_build_digest()
        assert "<a href=" in html

    def test_html_contains_news_publisher(self):
        _, html, _ = _run_build_digest()
        # At least one publisher from _FAKE_NEWS should appear
        assert any(item["publisher"] in html for item in _FAKE_NEWS)


# ---------------------------------------------------------------------------
# Plain-text content tests
# ---------------------------------------------------------------------------

class TestBuildDigestText:
    def test_text_contains_trending_news_titles(self):
        _, _, text = _run_build_digest()
        for item in _FAKE_NEWS:
            assert item["title"] in text, (
                f"Trending news title {item['title']!r} missing from plain text"
            )

    def test_text_contains_watchlist_mover_symbols(self):
        watchlist = ["NVDA", "AAPL"]
        _, _, text = _run_build_digest(watchlist=watchlist)
        for sym in watchlist:
            assert sym in text, f"Symbol {sym} missing from plain text"

    def test_text_is_shorter_than_html(self):
        """Plain text should be more compact than the HTML version."""
        _, html, text = _run_build_digest()
        assert len(text) < len(html), (
            f"Expected text ({len(text)} chars) to be shorter than html ({len(html)} chars)"
        )

    def test_text_has_no_html_tags(self):
        """Plain text should not contain angle-bracket HTML tags."""
        _, _, text = _run_build_digest()
        import re
        html_tags = re.findall(r"<[a-zA-Z/][^>]*>", text)
        assert html_tags == [], f"HTML tags found in plain text: {html_tags}"

    def test_text_contains_section_header(self):
        _, _, text = _run_build_digest()
        assert "MARKET TRENDING" in text


# ---------------------------------------------------------------------------
# Weekly frequency variant
# ---------------------------------------------------------------------------

class TestWeeklyDigest:
    def test_weekly_subject_differs_from_daily(self):
        subj_daily, _, _ = _run_build_digest(frequency="daily")
        subj_weekly, _, _ = _run_build_digest(frequency="weekly")
        assert subj_daily != subj_weekly

    def test_weekly_html_and_text_still_contain_news(self):
        _, html, text = _run_build_digest(frequency="weekly")
        assert _FAKE_NEWS[0]["title"] in html
        assert _FAKE_NEWS[0]["title"] in text

    def test_weekly_subject_not_contain_daily(self):
        subject, _, _ = _run_build_digest(frequency="weekly")
        assert "daily" not in subject.lower()


# ---------------------------------------------------------------------------
# Empty watchlist falls back to DEFAULT_TICKERS
# ---------------------------------------------------------------------------

class TestEmptyWatchlist:
    def test_empty_watchlist_uses_default_tickers(self):
        """When user_watchlist is [], the digest uses DEFAULT_TICKERS instead."""
        from api.defaults import DEFAULT_TICKERS

        # Capture the symbols passed to build_mover
        called_symbols: list[str] = []

        def _fake_build_mover(sym):
            called_symbols.append(sym)
            return _make_fake_mover(sym)

        with (
            patch("api.digest.get_trending_news", return_value=_FAKE_NEWS),
            patch("api.digest.build_mover", side_effect=_fake_build_mover),
            patch("api.db.get_conn", _make_mock_conn(row=None)),
        ):
            from api.digest import build_digest
            subject, html, text = build_digest("user456", [], "daily")

        assert len(called_symbols) > 0, "build_mover should be called for default tickers"
        # All called symbols must come from DEFAULT_TICKERS (capped at 25)
        for sym in called_symbols:
            assert sym in DEFAULT_TICKERS, f"{sym} is not in DEFAULT_TICKERS"

    def test_empty_watchlist_result_is_valid_tuple(self):
        with (
            patch("api.digest.get_trending_news", return_value=_FAKE_NEWS),
            patch("api.digest.build_mover", side_effect=lambda sym: _make_fake_mover(sym)),
            patch("api.db.get_conn", _make_mock_conn(row=None)),
        ):
            from api.digest import build_digest
            result = build_digest("user456", [], "daily")

        assert len(result) == 3
        assert all(isinstance(r, str) for r in result)


# ---------------------------------------------------------------------------
# No screener results (DB returns None) — graceful degradation
# ---------------------------------------------------------------------------

class TestNoScreenerResults:
    def test_build_succeeds_with_no_screener_cache(self):
        """When screener_results table has no rows, digest still builds cleanly."""
        subject, html, text = _run_build_digest(screener_row=None)
        # Core sections should still be present
        assert "Digest" in subject
        assert "<!DOCTYPE html>" in html or "<!doctype html>" in html.lower()
        assert isinstance(text, str) and len(text) > 0

    def test_screener_section_absent_when_no_results(self):
        """SCREENER LEADERS section should not appear when there is no cached result."""
        _, html, text = _run_build_digest(screener_row=None)
        # Screener section is only rendered when screener_leaders is non-empty
        assert "SCREENER LEADERS" not in html
        assert "SCREENER LEADERS" not in text
