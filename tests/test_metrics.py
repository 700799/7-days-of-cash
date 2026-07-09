"""Unit tests for technical indicator computations."""

import numpy as np
import pandas as pd
import pytest

from screener.metrics import (
    _acc_dist_days,
    _atr,
    _cmf,
    _linreg_slope,
    _macd_histogram,
    _mfi,
    _obv,
    _obv_divergence,
    _rsi,
    _updown_vol_ratio,
    _vol_climax,
    compute_metrics,
)


def _fake_ohlcv(n: int = 40, trend: float = 0.005, seed: int = 42) -> pd.DataFrame:
    """Generate fake OHLCV with a tunable upward drift."""
    rng = np.random.default_rng(seed)
    rets = rng.normal(loc=trend, scale=0.015, size=n)
    close = 100 * np.exp(np.cumsum(rets))
    high = close * (1 + np.abs(rng.normal(0, 0.008, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.008, n)))
    open_ = close * (1 + rng.normal(0, 0.003, n))
    volume = rng.integers(500_000, 5_000_000, n).astype(float)
    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": volume,
        },
        index=pd.date_range("2025-01-01", periods=n, freq="D"),
    )


def test_compute_metrics_returns_required_fields():
    df = _fake_ohlcv()
    m = compute_metrics("TEST", df)
    assert m is not None
    required = {
        "ticker",
        "price",
        "change_7d",
        "rsi_14",
        "macd_hist",
        "ma_20",
        "ma_50",
        "atr_14",
        "pct_from_52w_high",
    }
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


# --- Herd / volume-flow metrics ---


def _flat_frame(close_vals, vol_vals) -> pd.DataFrame:
    """OHLCV frame with High/Low straddling each close by 1."""
    close = np.asarray(close_vals, dtype=float)
    vol = np.asarray(vol_vals, dtype=float)
    return pd.DataFrame(
        {
            "Open": close,
            "High": close + 1,
            "Low": close - 1,
            "Close": close,
            "Volume": vol,
        },
        index=pd.date_range("2025-01-01", periods=len(close), freq="D"),
    )


def test_obv_signs_volume_by_close_direction():
    close = pd.Series([10.0, 11.0, 10.0, 12.0])  # up, down, up
    vol = pd.Series([100.0, 200.0, 300.0, 400.0])
    obv = _obv(close, vol)
    # day0 contributes 0 (no diff), then +200, -300, +400
    assert obv.tolist() == [0.0, 200.0, -100.0, 300.0]


def test_obv_divergence_detected():
    # Price makes a new high in the last 5 bars, but the fresh high comes on
    # tiny volume after heavy down days, so OBV cannot make a new high.
    close = pd.Series([100, 102, 104, 106, 108, 106, 104, 102, 100, 109, 110], dtype=float)
    vol = pd.Series([1e6, 1e6, 1e6, 1e6, 1e6, 5e6, 5e6, 5e6, 5e6, 1e3, 1e3], dtype=float)
    obv = _obv(close, vol)
    assert _obv_divergence(close, obv) is True


def test_obv_divergence_absent_when_flow_confirms():
    close = pd.Series(np.linspace(100, 120, 12))
    vol = pd.Series(np.linspace(1e6, 2e6, 12))  # rising volume with rising price
    obv = _obv(close, vol)
    assert _obv_divergence(close, obv) is False


def test_obv_divergence_short_series_false():
    close = pd.Series([1.0, 2.0, 3.0])
    obv = _obv(close, pd.Series([1.0, 1.0, 1.0]))
    assert _obv_divergence(close, obv) is False


def test_mfi_all_up_is_100():
    df = _flat_frame(np.linspace(100, 130, 20), [1e6] * 20)
    assert _mfi(df["High"], df["Low"], df["Close"], df["Volume"]) == 100.0


def test_mfi_all_down_is_0():
    df = _flat_frame(np.linspace(130, 100, 20), [1e6] * 20)
    assert _mfi(df["High"], df["Low"], df["Close"], df["Volume"]) == pytest.approx(0.0, abs=1e-9)


def test_mfi_short_series_neutral_50():
    df = _flat_frame([100.0] * 10, [1e6] * 10)
    assert _mfi(df["High"], df["Low"], df["Close"], df["Volume"]) == 50.0


def test_cmf_positive_when_closes_near_high():
    n = 25
    close = pd.Series([109.0] * n)
    df = pd.DataFrame(
        {
            "Open": close,
            "High": pd.Series([110.0] * n),
            "Low": pd.Series([100.0] * n),
            "Close": close,  # closes in the top of the range
            "Volume": pd.Series([1e6] * n),
        }
    )
    assert _cmf(df["High"], df["Low"], df["Close"], df["Volume"]) > 0.5


def test_cmf_negative_when_closes_near_low():
    n = 25
    close = pd.Series([101.0] * n)
    df = pd.DataFrame(
        {
            "Open": close,
            "High": pd.Series([110.0] * n),
            "Low": pd.Series([100.0] * n),
            "Close": close,
            "Volume": pd.Series([1e6] * n),
        }
    )
    assert _cmf(df["High"], df["Low"], df["Close"], df["Volume"]) < -0.5


def test_cmf_zero_range_bars_are_safe():
    n = 25
    close = pd.Series([100.0] * n)
    df = pd.DataFrame(
        {
            "Open": close,
            "High": close,  # H == L == C on every bar
            "Low": close,
            "Close": close,
            "Volume": pd.Series([1e6] * n),
        }
    )
    assert _cmf(df["High"], df["Low"], df["Close"], df["Volume"]) == 0.0


def test_updown_ratio_hand_computed():
    # Last 10 diffs alternate up/down with known volumes.
    close = pd.Series([100, 101, 100, 102, 101, 103, 102, 104, 103, 105, 104], dtype=float)
    vol = pd.Series([0, 100, 200, 100, 200, 100, 200, 100, 200, 100, 200], dtype=float)
    # up days carry 100 each (5 of them) = 500; down days carry 200 each (5) = 1000
    assert _updown_vol_ratio(close, vol) == pytest.approx(0.5)


def test_updown_ratio_caps_at_5_when_no_down_volume():
    close = pd.Series(np.linspace(100, 120, 12))
    vol = pd.Series([1e6] * 12)
    assert _updown_vol_ratio(close, vol) == 5.0


def test_updown_ratio_short_series_neutral():
    assert _updown_vol_ratio(pd.Series([1.0, 2.0]), pd.Series([1.0, 1.0])) == 1.0


def test_acc_dist_day_counts():
    # 5 moves: +1%, -1%, +1%, -1%, +1%; volume rises every day (all qualify).
    close = pd.Series([100, 101, 99.99, 100.99, 99.98, 100.98], dtype=float)
    vol = pd.Series([100, 200, 300, 400, 500, 600], dtype=float)
    acc, dist = _acc_dist_days(close, vol)
    assert acc == 3 and dist == 2


def test_acc_dist_requires_rising_volume():
    close = pd.Series([100, 101, 102, 103], dtype=float)
    vol = pd.Series([400, 300, 200, 100], dtype=float)  # volume falls every day
    acc, dist = _acc_dist_days(close, vol)
    assert acc == 0 and dist == 0


def test_vol_climax_requires_all_three():
    df = _fake_ohlcv(n=30)
    high, low, close = df["High"], df["Low"], df["Close"]
    # rel_vol below 3 -> False regardless of range
    assert _vol_climax(high, low, close, rel_vol=2.9) is False
    # Wide-range up day with rel_vol >= 3 -> True
    close2 = close.copy()
    high2 = high.copy()
    low2 = low.copy()
    close2.iloc[-1] = close2.iloc[-2] * 1.10
    high2.iloc[-1] = close2.iloc[-1] * 1.08
    low2.iloc[-1] = close2.iloc[-2] * 0.99
    assert _vol_climax(high2, low2, close2, rel_vol=3.5) is True
    # Same range but a down day -> False
    close3 = close2.copy()
    close3.iloc[-1] = close3.iloc[-2] * 0.90
    low3 = low2.copy()
    low3.iloc[-1] = close3.iloc[-1] * 0.92
    assert _vol_climax(high2, low3, close3, rel_vol=3.5) is False


def test_compute_metrics_includes_flow_keys_with_plain_types():
    m = compute_metrics("TEST", _fake_ohlcv(n=60))
    assert m is not None
    flow_keys = {
        "change_3d",
        "obv_slope_10d",
        "obv_divergence",
        "mfi_14",
        "cmf_20",
        "updown_vol_ratio_10d",
        "acc_days_25d",
        "dist_days_25d",
        "ext_atr",
        "vol_climax",
    }
    assert flow_keys.issubset(m.keys())
    for k in flow_keys:
        assert not isinstance(m[k], np.generic), f"numpy leaked from {k}: {m[k]!r}"
    assert isinstance(m["obv_divergence"], bool)
    assert isinstance(m["vol_climax"], bool)
    assert isinstance(m["acc_days_25d"], int)


def test_flow_metrics_neutral_defaults_on_short_series():
    m = compute_metrics("TINY", _fake_ohlcv(n=10))
    assert m is not None  # 10 bars passes the gate
    assert m["mfi_14"] == 50.0
    assert m["updown_vol_ratio_10d"] == 1.0
    assert m["obv_divergence"] is False
    assert m["vol_climax"] is False
