"""Pure-logic unit tests for api/news_provider.py.

No real database or network calls are made. All external dependencies
(yfinance, psycopg2 connection pool) are replaced with unittest.mock stubs.
"""
from __future__ import annotations

import json
from contextlib import contextmanager
from unittest.mock import MagicMock, patch, call

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_NEWS_LEGACY = [
    {
        "title": "Market rallies on Fed pause",
        "publisher": "Reuters",
        "link": "https://reuters.com/1",
        "providerPublishTime": 1_700_000_100,
        "thumbnail": {"resolutions": [{"url": "https://img.com/a.jpg"}]},
    },
    {
        "title": "Tech stocks surge",
        "publisher": "Bloomberg",
        "link": "https://bloomberg.com/2",
        "providerPublishTime": 1_700_000_200,
        "thumbnail": None,
    },
]

_FAKE_NEWS_WRAPPED = [
    {
        "content": {
            "title": "Wrapped format headline",
            "provider": {"displayName": "CNBC"},
            "clickThroughUrl": {"url": "https://cnbc.com/3"},
            "providerPublishTime": 1_700_000_300,
        }
    }
]

_EXPECTED_KEYS = {"title", "publisher", "link", "published_at", "thumbnail"}


def _make_mock_conn(cached_row=None):
    """Return a mock connection context manager whose cursor returns cached_row."""
    mock_cursor = MagicMock()
    mock_cursor.__enter__ = lambda s: s
    mock_cursor.__exit__ = MagicMock(return_value=False)
    mock_cursor.fetchone.return_value = cached_row

    mock_conn = MagicMock()
    mock_conn.__enter__ = lambda s: s
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value = mock_cursor

    @contextmanager
    def _get_conn(*args, **kwargs):
        yield mock_conn

    return _get_conn, mock_cursor


# ---------------------------------------------------------------------------
# get_ticker_news
# ---------------------------------------------------------------------------

class TestGetTickerNews:
    def test_returns_list_of_dicts_with_expected_keys(self):
        """get_ticker_news returns normalized dicts with the right shape."""
        get_conn_ctx, _ = _make_mock_conn(cached_row=None)  # cache miss

        mock_ticker = MagicMock()
        mock_ticker.news = _FAKE_NEWS_LEGACY

        with patch("api.news_provider.get_conn", get_conn_ctx), \
             patch("api.news_provider.yf.Ticker", return_value=mock_ticker):
            from api.news_provider import get_ticker_news
            result = get_ticker_news("AAPL")

        assert isinstance(result, list)
        assert len(result) <= 10
        for item in result:
            assert _EXPECTED_KEYS == set(item.keys()), f"Missing keys in {item}"

    def test_returns_correct_titles(self):
        """Title strings from the raw feed survive normalization."""
        get_conn_ctx, _ = _make_mock_conn(cached_row=None)

        mock_ticker = MagicMock()
        mock_ticker.news = _FAKE_NEWS_LEGACY

        with patch("api.news_provider.get_conn", get_conn_ctx), \
             patch("api.news_provider.yf.Ticker", return_value=mock_ticker):
            from api.news_provider import get_ticker_news
            result = get_ticker_news("AAPL")

        titles = [item["title"] for item in result]
        assert "Market rallies on Fed pause" in titles
        assert "Tech stocks surge" in titles

    def test_normalizes_wrapped_content_format(self):
        """New yfinance 'content'-wrapped format is handled correctly."""
        get_conn_ctx, _ = _make_mock_conn(cached_row=None)

        mock_ticker = MagicMock()
        mock_ticker.news = _FAKE_NEWS_WRAPPED

        with patch("api.news_provider.get_conn", get_conn_ctx), \
             patch("api.news_provider.yf.Ticker", return_value=mock_ticker):
            from api.news_provider import get_ticker_news
            result = get_ticker_news("GOOG", force=True)

        assert len(result) == 1
        assert result[0]["title"] == "Wrapped format headline"
        assert result[0]["publisher"] == "CNBC"
        assert result[0]["link"] == "https://cnbc.com/3"

    def test_limit_is_respected(self):
        """The limit parameter caps the result list."""
        get_conn_ctx, _ = _make_mock_conn(cached_row=None)

        mock_ticker = MagicMock()
        mock_ticker.news = _FAKE_NEWS_LEGACY * 10  # 20 items

        with patch("api.news_provider.get_conn", get_conn_ctx), \
             patch("api.news_provider.yf.Ticker", return_value=mock_ticker):
            from api.news_provider import get_ticker_news
            result = get_ticker_news("AAPL", limit=3)

        assert len(result) <= 3

    def test_graceful_fallback_when_yfinance_raises(self):
        """When yfinance raises, get_ticker_news returns [] without re-raising."""
        get_conn_ctx, _ = _make_mock_conn(cached_row=None)

        with patch("api.news_provider.get_conn", get_conn_ctx), \
             patch("api.news_provider.yf.Ticker", side_effect=RuntimeError("network error")):
            from api.news_provider import get_ticker_news
            result = get_ticker_news("BADTICKER", force=True)

        assert result == []

    def test_returns_empty_list_when_yfinance_returns_none(self):
        """yf.Ticker().news = None is treated as an empty feed."""
        get_conn_ctx, _ = _make_mock_conn(cached_row=None)

        mock_ticker = MagicMock()
        mock_ticker.news = None

        with patch("api.news_provider.get_conn", get_conn_ctx), \
             patch("api.news_provider.yf.Ticker", return_value=mock_ticker):
            from api.news_provider import get_ticker_news
            result = get_ticker_news("EMPTY", force=True)

        assert result == []

    def test_cache_hit_skips_yfinance(self):
        """When the cache has a fresh row, yf.Ticker should NOT be called."""
        cached_payload = json.dumps([
            {"title": "Cached headline", "publisher": "AP", "link": "https://ap.com/1",
             "published_at": None, "thumbnail": None}
        ])
        get_conn_ctx, _ = _make_mock_conn(cached_row=(cached_payload,))

        mock_yf = MagicMock()

        with patch("api.news_provider.get_conn", get_conn_ctx), \
             patch("api.news_provider.yf.Ticker", mock_yf):
            from api.news_provider import get_ticker_news
            result = get_ticker_news("AAPL", force=False)

        mock_yf.assert_not_called()
        assert result[0]["title"] == "Cached headline"

    def test_force_bypasses_cache(self):
        """force=True ignores the cached row and calls yfinance."""
        cached_payload = json.dumps([
            {"title": "Stale cached headline", "publisher": "AP",
             "link": "https://ap.com/old", "published_at": None, "thumbnail": None}
        ])
        get_conn_ctx, _ = _make_mock_conn(cached_row=(cached_payload,))

        mock_ticker = MagicMock()
        mock_ticker.news = _FAKE_NEWS_LEGACY

        with patch("api.news_provider.get_conn", get_conn_ctx), \
             patch("api.news_provider.yf.Ticker", return_value=mock_ticker):
            from api.news_provider import get_ticker_news
            result = get_ticker_news("AAPL", force=True)

        # Should return fresh data, not the cached stale headline
        titles = [item["title"] for item in result]
        assert "Market rallies on Fed pause" in titles


# ---------------------------------------------------------------------------
# get_trending_news
# ---------------------------------------------------------------------------

class TestGetTrendingNews:
    def test_returns_list(self):
        """get_trending_news always returns a list (possibly empty)."""
        get_conn_ctx, _ = _make_mock_conn(cached_row=None)

        mock_ticker = MagicMock()
        mock_ticker.news = []

        with patch("api.news_provider.get_conn", get_conn_ctx), \
             patch("api.news_provider.yf.Ticker", return_value=mock_ticker):
            from api.news_provider import get_trending_news
            result = get_trending_news(force=True)

        assert isinstance(result, list)

    def test_deduplicates_by_title(self):
        """Duplicate titles across indices are merged to one item."""
        get_conn_ctx, _ = _make_mock_conn(cached_row=None)

        dup_item = {
            "title": "Same headline everywhere",
            "publisher": "Reuters",
            "link": "https://reuters.com/dup",
            "providerPublishTime": 1_700_000_500,
        }

        mock_ticker = MagicMock()
        mock_ticker.news = [dup_item]  # same response for every index

        with patch("api.news_provider.get_conn", get_conn_ctx), \
             patch("api.news_provider.yf.Ticker", return_value=mock_ticker):
            from api.news_provider import get_trending_news
            result = get_trending_news(force=True)

        titles = [item["title"] for item in result]
        assert titles.count("Same headline everywhere") == 1

    def test_queries_all_three_indices(self):
        """Three separate Ticker objects are created (one per index)."""
        get_conn_ctx, _ = _make_mock_conn(cached_row=None)

        mock_ticker = MagicMock()
        mock_ticker.news = []
        mock_yf_cls = MagicMock(return_value=mock_ticker)

        with patch("api.news_provider.get_conn", get_conn_ctx), \
             patch("api.news_provider.yf.Ticker", mock_yf_cls):
            from api.news_provider import get_trending_news, _TRENDING_INDICES
            get_trending_news(force=True)

        called_symbols = [c.args[0] for c in mock_yf_cls.call_args_list]
        for sym in _TRENDING_INDICES:
            assert sym in called_symbols, f"{sym} was not queried"

    def test_cache_hit_skips_yfinance(self):
        """A warm cache entry prevents any yfinance call."""
        cached = [
            {"title": "Trending cached", "publisher": "WS", "link": "https://ws.com/1",
             "published_at": None, "thumbnail": None}
        ]
        get_conn_ctx, _ = _make_mock_conn(cached_row=(json.dumps(cached),))

        mock_yf = MagicMock()

        with patch("api.news_provider.get_conn", get_conn_ctx), \
             patch("api.news_provider.yf.Ticker", mock_yf):
            from api.news_provider import get_trending_news
            result = get_trending_news(force=False)

        mock_yf.assert_not_called()
        assert result[0]["title"] == "Trending cached"

    def test_graceful_fallback_when_yfinance_raises(self):
        """Exception from yfinance on any index is swallowed; returns []."""
        get_conn_ctx, _ = _make_mock_conn(cached_row=None)

        with patch("api.news_provider.get_conn", get_conn_ctx), \
             patch("api.news_provider.yf.Ticker", side_effect=ConnectionError("timeout")):
            from api.news_provider import get_trending_news
            result = get_trending_news(force=True)

        assert result == []

    def test_limit_parameter_is_respected(self):
        """Returned list has at most `limit` items."""
        many_items = [
            {
                "title": f"Headline {i}",
                "publisher": "Pub",
                "link": f"https://news.com/{i}",
                "providerPublishTime": 1_700_000_000 + i,
            }
            for i in range(20)
        ]
        get_conn_ctx, _ = _make_mock_conn(cached_row=None)

        mock_ticker = MagicMock()
        mock_ticker.news = many_items

        with patch("api.news_provider.get_conn", get_conn_ctx), \
             patch("api.news_provider.yf.Ticker", return_value=mock_ticker):
            from api.news_provider import get_trending_news
            result = get_trending_news(limit=3, force=True)

        assert len(result) <= 3

    def test_sorts_newest_first(self):
        """After dedup, items are ordered newest-first by publish time."""
        old_item = {
            "title": "Old news",
            "publisher": "Reuters",
            "link": "https://reuters.com/old",
            "providerPublishTime": 1_700_000_100,
        }
        new_item = {
            "title": "Breaking news",
            "publisher": "Reuters",
            "link": "https://reuters.com/new",
            "providerPublishTime": 1_700_000_999,
        }
        get_conn_ctx, _ = _make_mock_conn(cached_row=None)

        mock_ticker = MagicMock()
        mock_ticker.news = [old_item, new_item]

        with patch("api.news_provider.get_conn", get_conn_ctx), \
             patch("api.news_provider.yf.Ticker", return_value=mock_ticker):
            from api.news_provider import get_trending_news
            result = get_trending_news(limit=5, force=True)

        assert len(result) >= 2
        assert result[0]["title"] == "Breaking news"


# ---------------------------------------------------------------------------
# _normalize_item (internal helper, tested via public interface)
# ---------------------------------------------------------------------------

class TestNormalizeItem:
    """Edge-case tests for field extraction within a normalized item."""

    def test_thumbnail_url_extracted_from_resolutions(self):
        raw = {
            "title": "T",
            "publisher": "P",
            "link": "https://x.com",
            "providerPublishTime": 1_700_000_000,
            "thumbnail": {"resolutions": [{"url": "https://img.com/t.jpg"}, {"url": "https://img.com/t2.jpg"}]},
        }
        get_conn_ctx, _ = _make_mock_conn(cached_row=None)
        mock_ticker = MagicMock()
        mock_ticker.news = [raw]

        with patch("api.news_provider.get_conn", get_conn_ctx), \
             patch("api.news_provider.yf.Ticker", return_value=mock_ticker):
            from api.news_provider import get_ticker_news
            result = get_ticker_news("TEST", force=True)

        assert result[0]["thumbnail"] == "https://img.com/t.jpg"

    def test_missing_thumbnail_is_none(self):
        raw = {
            "title": "No thumb",
            "publisher": "P",
            "link": "https://x.com",
            "providerPublishTime": 1_700_000_000,
        }
        get_conn_ctx, _ = _make_mock_conn(cached_row=None)
        mock_ticker = MagicMock()
        mock_ticker.news = [raw]

        with patch("api.news_provider.get_conn", get_conn_ctx), \
             patch("api.news_provider.yf.Ticker", return_value=mock_ticker):
            from api.news_provider import get_ticker_news
            result = get_ticker_news("TEST", force=True)

        assert result[0]["thumbnail"] is None

    def test_published_at_is_iso_string_from_epoch(self):
        raw = {
            "title": "T",
            "publisher": "P",
            "link": "https://x.com",
            "providerPublishTime": 1_700_000_000,
        }
        get_conn_ctx, _ = _make_mock_conn(cached_row=None)
        mock_ticker = MagicMock()
        mock_ticker.news = [raw]

        with patch("api.news_provider.get_conn", get_conn_ctx), \
             patch("api.news_provider.yf.Ticker", return_value=mock_ticker):
            from api.news_provider import get_ticker_news
            result = get_ticker_news("TEST", force=True)

        pub = result[0]["published_at"]
        assert isinstance(pub, str)
        assert "2023" in pub  # epoch 1_700_000_000 falls in 2023
