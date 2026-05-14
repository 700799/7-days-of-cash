"""Unit tests for technical indicator computations."""
import numpy as np
import pandas as pd
import pytest

from screener.metrics import compute_metrics, _linreg_slope, _rsi, _atr, _macd_histogram


def _fake_ohlcv(n: int = 40, trend: float = 0.005, seed: int = 42) -> pd.DataFrame:
    """Generate fake OHLCV with a tunable upward drift."""
    rng = np.random.default_rng(seed)
    rets = rng.normal(loc=trend, scale=0.015, size=n)
    close = 100 * np.exp(np.cumsum(rets))
    high = close * (1 + np.abs(rng.normal(0, 0.008, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.008, n)))
    open_ = close * (1 + rng.normal(0, 0.003, n))
    volume = rng.integers(500_000, 5_000_000, n).astype(float)
    return pd.DataFrame({
        "Open": open_, "High": high, "Low": low,
        "Close": close, "Volume": volume,
    }, index=pd.date_range("2025-01-01", periods=n, freq="D"))


def test_compute_metrics_returns_required_fields():
    df = _fake_ohlcv()
    m = compute_metrics("TEST", df)
    assert m is not None
    required = {"ticker", "price", "change_7d", "rsi_14", "macd_hist",
                "ma_20", "ma_50", "atr_14", "pct_from_52w_high"}
    assert required.issubset(m.keys())


def test_compute_metrics_returns_none_for_too_few_bars():
    df = _fake_ohlcv(n=5)
    assert compute_metrics("TEST", df) is None


def test_uptrend_produces_positive_change_7d():
    df = _fake_ohlcv(n=30, trend=0.02)  # 2% daily drift
    m = compute_metrics("UP", df)
    assert m["change_7d"] > 0


def test_downtrend_produces_negative_change_7d():
    df = _fake_ohlcv(n=30, trend=-0.02)
    m = compute_metrics("DN", df)
    assert m["change_7d"] < 0


def test_rsi_bounded_0_100():
    df = _fake_ohlcv(n=60)
    r = _rsi(df["Close"])
    assert 0 <= r <= 100


def test_rsi_extreme_uptrend_near_100():
    close = pd.Series(np.linspace(100, 200, 50))
    r = _rsi(close)
    assert r > 80


def test_rsi_extreme_downtrend_near_0():
    close = pd.Series(np.linspace(200, 100, 50))
    r = _rsi(close)
    assert r < 30


def test_linreg_slope_positive_for_rising_series():
    assert _linreg_slope(np.array([1, 2, 3, 4, 5])) > 0


def test_linreg_slope_negative_for_falling_series():
    assert _linreg_slope(np.array([5, 4, 3, 2, 1])) < 0


def test_linreg_slope_zero_for_constant():
    assert _linreg_slope(np.array([3, 3, 3, 3, 3])) == 0


def test_atr_positive_and_finite():
    df = _fake_ohlcv()
    a = _atr(df["High"], df["Low"], df["Close"])
    assert a > 0 and np.isfinite(a)


def test_macd_finite():
    df = _fake_ohlcv(n=60)
    h = _macd_histogram(df["Close"])
    assert np.isfinite(h)
