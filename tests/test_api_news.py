"""News API: caching prevents repeat yfinance calls within TTL."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_db_path):
    from api.main import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c


_FAKE_NEWS = [
    {
        "title": "Apple soars",
        "publisher": "Reuters",
        "link": "https://example.com/a1",
        "providerPublishTime": 1_700_000_000,
        "thumbnail": {"resolutions": [{"url": "https://example.com/t.jpg"}]},
    },
    {
        "title": "Apple holds steady",
        "publisher": "Bloomberg",
        "link": "https://example.com/a2",
        "providerPublishTime": 1_700_000_500,
    },
]


def test_ticker_news_caches(client):
    fake_ticker = MagicMock()
    fake_ticker.news = _FAKE_NEWS

    with patch("api.news_provider.yf.Ticker", return_value=fake_ticker) as ticker_cls:
        r1 = client.get("/api/news/ticker/AAPL")
        r2 = client.get("/api/news/ticker/AAPL")

    assert r1.status_code == 200
    assert r2.status_code == 200
    items = r1.json()
    assert len(items) == 2
    assert items[0]["title"] == "Apple soars"
    assert items[0]["publisher"] == "Reuters"
    assert items[0]["thumbnail"] == "https://example.com/t.jpg"
    assert items[0]["published_at"] is not None

    # Second call should hit cache, not yfinance.
    assert ticker_cls.call_count == 1
    assert r1.json() == r2.json()


def test_market_news_caches(client):
    fake_ticker = MagicMock()
    fake_ticker.news = _FAKE_NEWS

    with patch("api.news_provider.yf.Ticker", return_value=fake_ticker) as ticker_cls:
        r1 = client.get("/api/news/market")
        r2 = client.get("/api/news/market")

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert ticker_cls.call_count == 1
    assert ticker_cls.call_args.args == ("^GSPC",)


def test_ticker_news_handles_yfinance_error(client):
    failing = MagicMock()
    type(failing).news = property(lambda self: (_ for _ in ()).throw(RuntimeError("boom")))
    with patch("api.news_provider.yf.Ticker", return_value=failing):
        r = client.get("/api/news/ticker/XYZ")
    assert r.status_code == 200
    assert r.json() == []
