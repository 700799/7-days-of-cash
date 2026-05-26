"""Tests for api/defaults.py — pure data validation, no I/O required."""
from api.defaults import DEFAULT_TICKERS


def test_has_at_least_ten_items():
    assert len(DEFAULT_TICKERS) >= 10


def test_all_items_are_uppercase_strings():
    for ticker in DEFAULT_TICKERS:
        assert isinstance(ticker, str), f"{ticker!r} is not a str"
        assert ticker == ticker.upper(), f"{ticker!r} is not fully uppercase"


def test_contains_known_tickers():
    assert "NVDA" in DEFAULT_TICKERS
    assert "AAPL" in DEFAULT_TICKERS
    assert "GOOG" in DEFAULT_TICKERS


def test_no_duplicates():
    assert len(DEFAULT_TICKERS) == len(set(DEFAULT_TICKERS)), (
        "DEFAULT_TICKERS contains duplicate entries"
    )


def test_all_tickers_are_short():
    for ticker in DEFAULT_TICKERS:
        assert len(ticker) <= 6, f"{ticker!r} exceeds 6-character ticker limit"


def test_no_empty_strings():
    for ticker in DEFAULT_TICKERS:
        assert ticker.strip() != "", "DEFAULT_TICKERS contains an empty or whitespace-only entry"
