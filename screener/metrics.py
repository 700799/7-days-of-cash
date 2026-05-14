"""Technical indicator computations: RSI, MACD, MAs, ATR, volume trend."""
from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd


def compute_metrics(ticker: str, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """Compute the full metric dict for one ticker, or None if insufficient data."""
    try:
        df = df.sort_index()
        close = df["Close"].astype(float)
        volume = df["Volume"].astype(float)
        high = df["High"].astype(float)
        low = df["Low"].astype(float)
        open_ = df["Open"].astype(float)

        n = len(close)
        if n < 10:
            return None

        price = float(close.iloc[-1])

        # Price changes
        lookback_7 = min(7, n - 1)
        lookback_5 = min(5, n - 1)
        lookback_20 = min(20, n - 1)
        change_5d = (close.iloc[-1] / close.iloc[-1 - lookback_5] - 1) * 100
        change_7d = (close.iloc[-1] / close.iloc[-1 - lookback_7] - 1) * 100
        change_20d = (close.iloc[-1] / close.iloc[-1 - lookback_20] - 1) * 100

        # Volume metrics
        avg_vol_20d = float(volume.iloc[-20:].mean()) if n >= 20 else float(volume.mean())
        today_vol = float(volume.iloc[-1])
        rel_vol = today_vol / avg_vol_20d if avg_vol_20d > 0 else 0.0
        vol_trend_5d = _linreg_slope(volume.iloc[-5:].values) if n >= 5 else 0.0
        vol_trend_7d = _linreg_slope(volume.iloc[-7:].values) if n >= 7 else 0.0
        dollar_vol_20d = avg_vol_20d * price

        # Moving averages
        ma_20 = float(close.iloc[-20:].mean()) if n >= 20 else float(close.mean())
        ma_50 = float(close.iloc[-50:].mean()) if n >= 50 else ma_20
        ma_200 = float(close.iloc[-200:].mean()) if n >= 200 else ma_50
        pct_from_ma20 = (price / ma_20 - 1) * 100 if ma_20 > 0 else 0.0
        pct_from_ma50 = (price / ma_50 - 1) * 100 if ma_50 > 0 else 0.0

        # 52-week high distance
        high_52w = float(high.iloc[-252:].max()) if n >= 60 else float(high.max())
        pct_from_52w_high = (price / high_52w - 1) * 100 if high_52w > 0 else 0.0

        # RSI, ATR, MACD
        rsi = _rsi(close, period=14)
        atr_14 = _atr(high, low, close, period=14)
        atr_pct = (atr_14 / price * 100) if price > 0 else 0.0
        macd_hist = _macd_histogram(close)

        # Intraday volatility
        avg_range_pct = float(((high - low) / close).iloc[-10:].mean()) * 100

        # Gap up today
        if n >= 2:
            prev_close = float(close.iloc[-2])
            gap_pct = (float(open_.iloc[-1]) / prev_close - 1) * 100 if prev_close > 0 else 0.0
        else:
            gap_pct = 0.0

        return {
            "ticker": ticker,
            "price": round(price, 2),
            "change_5d": round(float(change_5d), 2),
            "change_7d": round(float(change_7d), 2),
            "change_20d": round(float(change_20d), 2),
            "avg_vol_20d": int(avg_vol_20d),
            "rel_vol": round(rel_vol, 2),
            "vol_trend_5d": round(vol_trend_5d, 0),
            "vol_trend_7d": round(vol_trend_7d, 0),
            "dollar_vol_20d": int(dollar_vol_20d),
            "ma_20": round(ma_20, 2),
            "ma_50": round(ma_50, 2),
            "ma_200": round(ma_200, 2),
            "pct_from_ma20": round(pct_from_ma20, 2),
            "pct_from_ma50": round(pct_from_ma50, 2),
            "pct_from_52w_high": round(pct_from_52w_high, 2),
            "rsi_14": round(rsi, 1),
            "atr_14": round(atr_14, 2),
            "atr_pct": round(atr_pct, 2),
            "macd_hist": round(macd_hist, 3),
            "avg_range_pct": round(avg_range_pct, 1),
            "gap_pct": round(gap_pct, 2),
        }
    except Exception:
        return None


def _linreg_slope(values: np.ndarray) -> float:
    if len(values) < 2:
        return 0.0
    x = np.arange(len(values), dtype=float)
    x -= x.mean()
    y = values - values.mean()
    denom = float(np.dot(x, x))
    if denom == 0:
        return 0.0
    return float(np.dot(x, y) / denom)


def _rsi(close: pd.Series, period: int = 14) -> float:
    delta = close.diff().dropna()
    if len(delta) < period:
        return 50.0
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean().iloc[-1]
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean().iloc[-1]
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100 - 100 / (1 + rs))


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> float:
    if len(close) < 2:
        return 0.0
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    if atr.empty or pd.isna(atr.iloc[-1]):
        return 0.0
    return float(atr.iloc[-1])


def _macd_histogram(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> float:
    if len(close) < slow + signal:
        return 0.0
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return float(hist.iloc[-1])
